#!/usr/bin/env python3
"""POST /flag, /views and /order (2026-09-08): the Obsidian timeline panel's three state writes as
kernel routes. The panel runs in Obsidian's Electron with Node's fs and the state dir and has no
socket to the kernel, so it used to write session-flags.json, timeline-views.json and
session-order.json itself -- a second writer beside the kernel, bypassing the views judge and its
stale-writer guard, the flags setter's lock, and the order merge. Each route lands through the SAME
setter its socket op calls (setSessionFlag / setTimelineViews / reorderTabs in _dispatch_ws), with
that op's validation, and refuses the way it refuses; the tests here drive the REAL Handler over
HTTP (the test_tag_route.py pattern) and, where a refusal is claimed to match the socket op's, drive
the socket op too and compare. Synthetic only."""
import ast
import base64
import contextlib
import errno
import gc
import inspect
import io
import json
import os
import re
import socket
import struct
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import weakref
from collections import Counter, namedtuple
from http.server import ThreadingHTTPServer
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads -- they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_osr", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
OTHER = "99999999-8888-7777-6666-555555555555"
A, B, C, D = ("aaaaaaaa-1111-2222-3333-444444444444", "bbbbbbbb-1111-2222-3333-444444444444",
              "cccccccc-1111-2222-3333-444444444444", "dddddddd-1111-2222-3333-444444444444")


@contextlib.contextmanager
def _reads_fault(target):
    """Fail every byte read of ONE path with an EIO for the duration of the block (the
    tests/test_kernel_session_flags.py injector); everything else reads normally."""
    real_rb, real_rt = Path.read_bytes, Path.read_text
    tgt = str(target)

    def rb(self, *a, **k):
        if str(self) == tgt:
            raise OSError(errno.EIO, "injected EIO")
        return real_rb(self, *a, **k)

    def rt(self, *a, **k):
        if str(self) == tgt:
            raise OSError(errno.EIO, "injected EIO")
        return real_rt(self, *a, **k)
    Path.read_bytes, Path.read_text = rb, rt
    try:
        yield
    finally:
        Path.read_bytes, Path.read_text = real_rb, real_rt


class _Server(ThreadingHTTPServer):
    request_queue_size = 128   # socketserver's default backlog is 5; the concurrent-writer tests below open 32 at once


class _Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _Server(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = km.jd.STATE
        # _rebind_state, not STATE alone: the kernel's judge is one module object shared by every test module in the process (each kernel load re-executes bin/romp-judge into the same sys.modules entry); a store written at its import-bound GOALDIR is read by every later module's feed (T281). Assigning STATE left GOALDIR at the run-wide root, so every
        # goal store these routes saved for the placeholder sid outlived this module.
        km.jd._rebind_state(Path(self.td.name))
        km._flags_cache.clear()
        self._saved = (km._mark_views_dirty, km._sync_notice)
        self.dirty, self.notices = [], []
        km._mark_views_dirty = lambda: self.dirty.append(1)
        km._sync_notice = lambda text, ok=True, **kw: self.notices.append((text, ok))

    def tearDown(self):
        km._mark_views_dirty, km._sync_notice = self._saved
        km.jd._rebind_state(self._state)
        km._flags_cache.clear()
        self.td.cleanup()

    def test_the_stores_these_routes_write_do_not_outlive_the_module(self):
        # The residue pin (T281): a store saved through the kernel's judge lands under THIS test's root, and the
        # run-wide root (what every later module's feed reads) is left exactly as it was.
        shared = Path(self._state) / "goals" / (SID + ".json")
        before = (shared.exists(), shared.stat().st_mtime_ns if shared.exists() else None)
        km.jd.save_goals(SID, {"nodes": {SID + ":t281": {"id": SID + ":t281", "text": "a note", "parentId": None, "t": 1, "mt": 1}}})
        self.assertTrue((Path(self.td.name) / "goals" / (SID + ".json")).exists(), "the store lives under this module's root")
        self.assertEqual((shared.exists(), shared.stat().st_mtime_ns if shared.exists() else None), before,
                         "the run-wide goals directory is untouched by this module")

    def _post(self, path, body=None, raw=None, token=os.environ["ROMP_SERVE_TOKEN"]):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-Romp-Token"] = token
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     data=(raw if raw is not None else json.dumps(body).encode()),
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            text = e.read().decode()
            try:
                return e.code, json.loads(text)
            except ValueError:
                return e.code, text

    def _ws(self, msg):
        """The socket op, through the real dispatcher; the frames it answered on the poster's socket."""
        sent = []
        client = {"app": "timeline", "wid": "w-obs", "alive": True,
                  "send": lambda raw: sent.append(json.loads(raw))}
        km.Handler._dispatch_ws(object.__new__(km.Handler), msg, client)
        return sent


class FlagRoute(_Routes):

    def _flags_file(self):
        p = km.jd.STATE / "session-flags.json"
        return json.loads(p.read_text()) if p.exists() else None

    def test_a_toggle_lands_through_the_setter_and_unsets_the_way_it_does(self):
        st, r = self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": True})
        self.assertEqual((st, r), (200, {"ok": True, "id": SID, "flag": "hideFromFeed", "value": True}))
        self.assertEqual(self._flags_file(), {SID: {"hideFromFeed": True}}, "the store the kernel reads holds it")
        self.assertTrue(km._session_flag(SID, "hideFromFeed"))
        self.assertEqual(self.dirty, [1], "the views push is poked, as after the socket op")
        st, r = self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": False})
        self.assertEqual((st, r["ok"]), (200, True))
        self.assertEqual(self._flags_file(), {}, "off drops the entry -- _set_session_flag's pop, not a stored false")

    def test_the_bell_rides_its_own_tri_state_setter(self):
        st, r = self._post("/flag", {"id": SID, "flag": "notify", "value": True})
        self.assertEqual((st, r["ok"]), (200, True))
        self.assertIs(km._session_flag_raw(SID, "notify"), True, "an override on the (off) master is stored")
        st, r = self._post("/flag", {"id": SID, "flag": "notify", "value": False})
        self.assertEqual((st, r["ok"]), (200, True))
        self.assertIsNone(km._session_flag_raw(SID, "notify"), "back to the master's value: the override is dropped, not stored as false")

    def test_a_non_boolean_or_missing_value_is_a_400_that_writes_nothing(self):
        for value, needle in (("false", "'value' must be true or false"), (0, "'value' must be true or false"),
                              (None, "value (true or false) required")):
            body = {"id": SID, "flag": "hideFromFeed"}
            if value is not None:
                body["value"] = value
            st, r = self._post("/flag", body)
            self.assertEqual(st, 400, (value, r))
            self.assertFalse(r["ok"])
            self.assertIn(needle, r["error"])
        st, r = self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": None})
        self.assertEqual((st, r["error"]), (400, "value (true or false) required"), "an explicit null is not a value either")
        self.assertIsNone(self._flags_file(), "bool('false') must never UNDO a mute -- nothing was written")
        self.assertEqual(self.dirty, [])

    def test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it(self):
        st, r = self._post("/flag", {"id": SID, "flag": "autoNudgeOff", "value": True})
        self.assertEqual(st, 400)
        self.assertEqual(r["error"], 'flag must be one of hideFromFeed, postalServiceOff, notify, got "autoNudgeOff"')
        st, r = self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": True, "target": "web"})
        self.assertEqual(st, 400)
        self.assertEqual(r["error"], "unknown key(s) 'target' — this route reads only 'id', 'flag', 'value'")
        st, r = self._post("/flag", {"flag": "hideFromFeed", "value": True})
        self.assertEqual((st, r["error"]), (400, "id (the session's id) required"))
        self.assertIsNone(self._flags_file())

    def test_a_store_fault_answers_the_socket_ops_refusal_and_leaves_the_file_alone(self):
        km._set_session_flag(OTHER, "postalServiceOff", True)     # a populated store: a safety boundary
        km._flags_cache.clear()
        p = km.jd.STATE / "session-flags.json"
        before = p.read_bytes()
        with _reads_fault(p):
            st, r = self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": True})
            ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": "hideFromFeed", "value": True})
        self.assertEqual(st, 200, "the kernel's own refusal is a 200 with ok:false, like every route's")
        self.assertFalse(r["ok"])
        self.assertIn("couldn't save that setting", r["error"])
        self.assertIn("session-flags.json could not be read", r["error"])
        self.assertIs(r["value"], False, "the value the display path still paints rides along (the settingRefused field)")
        self.assertEqual(len(ws), 1)
        self.assertEqual(ws[0]["type"], "settingRefused")
        self.assertEqual(ws[0]["text"], r["error"], "word for word the socket op's refusal")
        self.assertEqual(ws[0]["value"], r["value"])
        self.assertEqual(p.read_bytes(), before, "the flags file is byte-for-byte unchanged")
        self.assertEqual(self.dirty, [], "a refused write marks nothing dirty")


def _client_frame(text):
    """One masked client text frame, as a browser sends it (the tests/test_feed_delta.py helper)."""
    data = text.encode("utf-8"); n = len(data); mask = os.urandom(4)
    if n < 126:
        hdr = bytes([0x81, 0x80 | n])
    elif n < 65536:
        hdr = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
    else:
        hdr = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
    return hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _ping_frame(data):
    """One masked client ping (the tests/test_feed_delta.py helper). The kernel's reader thread answers it inline
    after dispatching every message read before it, so its pong says those dispatches are done."""
    mask = os.urandom(4)
    return bytes([0x89, 0x80 | len(data)]) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _read_frame(s, buf):
    """One server frame (unmasked) -> (opcode, payload, leftover) (the tests/test_feed_delta.py helper)."""
    def need(n):
        nonlocal buf
        while len(buf) < n:
            chunk = s.recv(1 << 20)
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
    need(2)
    ln = buf[1] & 0x7F; off = 2
    if ln == 126:
        need(4); ln = struct.unpack(">H", buf[2:4])[0]; off = 4
    elif ln == 127:
        need(10); ln = struct.unpack(">Q", buf[2:10])[0]; off = 10
    need(off + ln)
    return buf[0] & 0x0F, buf[off:off + ln], buf[off + ln:]


class SocketFlagWhitelist(_Routes):
    """The setSessionFlag socket op applies the SAME whitelist as POST /flag (the reviewer's ruling in the
    round-3 review of fork PR #897). Before it the arm wrote ANY name an authenticated dashboard client sent,
    while the route refused an unlisted one with a 400: a client could set `threadMail` on a comment thread
    (the key that turns its mail on; fork PR #897 discloses what follows, the deadness mirror's roster then
    omitting comment-thread sids that relay) or the legacy `postalOff`, which the kernel and the bus both
    read as isolation. Both doors now ask one predicate over the one list (_lane_flag_refusal over
    _LANE_FLAGS). The socket answers an unlisted name on the settingRefused frame (the lane gear's refusal,
    which the timeline page repaints from; a `warn` never reaches it) with the route's own sentence inside,
    `value` null since no pane paints an unlisted flag, and writes nothing. Every name a frame carries meets the
    predicate, a falsy one (null, "", 0, 0.0, false, [] and {}) included, since the arm keys on the flag key's
    presence (the reviewer's ruling on round 1 of fork PR #909, kernel-2). A frame with NO flag key is where the doors
    still differ, in the answer only: the socket op draws the terminal arm's unknownOp, the kernel's answer for a known
    op missing a field its arm requires (_note_unknown_op), and POST /flag its 400 ("got null"); neither writes.
    Driven through the real dispatcher, and end to end over a real socket to the served Handler."""

    UNLISTED = ("threadMail", "postalOff", "someFutureFlag", "hideFromFeed ", "HIDEFROMFEED",
                7, True, ["hideFromFeed"], {"hideFromFeed": True},
                None, "", 0, 0.0, False, [], {})   # the falsy names: each reaches the predicate, as a truthy one does

    def setUp(self):
        super().setUp()
        # this class's state root is minted here, outside the conftest belt: no per-session host from it (T348)
        (km.jd.STATE / "session-hosts").write_text("off\n")

    def _flags_file(self):
        p = km.jd.STATE / "session-flags.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _wrapped(self, route_error):
        """The socket's refusal text for a sentence the route answers bare: _refuse_setting's wrapping."""
        return "couldn't save that setting \u2014 %s; try again" % route_error

    def test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing(self):
        km._set_session_flag(OTHER, "postalServiceOff", True)     # a populated store: an isolation boundary
        km._flags_cache.clear()
        p = km.jd.STATE / "session-flags.json"
        before = p.read_bytes()
        answers = []
        for name in self.UNLISTED:
            ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": name, "value": True})
            km._flags_cache.clear()
            self.assertEqual(p.read_bytes(), before, "%r: the socket op wrote the flags store: %s"
                             % (name, p.read_text()))
            answers.append((name, ws))
        # every name's answer by its type first, before any other field is read: a name the arm never hands the
        # predicate draws the terminal arm's unknownOp, which carries no gesture
        self.assertEqual([(name, ws) for name, ws in answers if [fr.get("type") for fr in ws] != ["settingRefused"]], [],
                         "names whose answer is not one settingRefused frame on the delivering socket")
        for name, ws in answers:
            st, r = self._post("/flag", {"id": SID, "flag": name, "value": True})
            self.assertEqual(st, 400, (name, r))
            self.assertEqual(r["error"], "flag must be one of %s, got %s" % (", ".join(km._LANE_FLAGS), json.dumps(name)))
            fr = ws[0]
            self.assertEqual((fr["type"], fr["gesture"], fr["sid"], fr["itemId"]), ("settingRefused", "flag", SID, ""), fr)
            self.assertIsNone(fr["value"], "%r: no pane paints an unlisted flag, so there is no toggle to repaint" % (name,))
            self.assertEqual(fr["text"], self._wrapped(r["error"]), "%r: the route's sentence, wrapped as the socket's refusals are" % (name,))
            self.assertIsInstance(fr["flag"], str)
            if isinstance(name, str) or not name:
                self.assertEqual(fr["flag"], name or "", "%r: addressed to the name the client sent, as str() spells it, "
                                 "the empty string for a falsy one" % (name,))
        st, r = self._post("/flag", {"id": SID, "flag": "threadMail", "value": True})
        self.assertEqual(r["error"], 'flag must be one of hideFromFeed, postalServiceOff, notify, got "threadMail"')
        self.assertEqual(self._ws({"type": "setSessionFlag", "id": SID, "flag": "threadMail", "value": True})[0]["text"],
                         "couldn't save that setting \u2014 flag must be one of hideFromFeed, postalServiceOff, notify, "
                         'got "threadMail"; try again')
        self.assertEqual(self._flags_file(), {OTHER: {"postalServiceOff": True}})
        self.assertEqual(self.dirty, [], "a refused write marks nothing dirty")

    def test_a_frame_with_no_flag_key_draws_unknown_op_where_the_route_answers_its_400(self):
        """A witness, green before the arm keyed on the flag key's presence and after, by design: a frame with an id
        and a value and no flag key falls to the terminal arm, whose answer is exactly unknownOp (_note_unknown_op, the
        kernel's contract for a known op missing a field its arm requires; tests/test_tag_edit_ack.py pins it for an
        empty id), while POST /flag answers the same request with its whitelist 400, "got null". The doors differ here
        in the answer only: neither writes."""
        km._set_session_flag(OTHER, "postalServiceOff", True)
        km._flags_cache.clear()
        p = km.jd.STATE / "session-flags.json"
        before = p.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):     # the terminal arm logs a type once per process
            ws = self._ws({"type": "setSessionFlag", "id": SID, "value": True})
        self.assertEqual(ws, [{"type": "unknownOp", "op": "setSessionFlag"}])
        st, r = self._post("/flag", {"id": SID, "value": True})
        self.assertEqual((st, r), (400, {"ok": False, "error": "flag must be one of hideFromFeed, postalServiceOff, "
                                                               "notify, got null"}))
        km._flags_cache.clear()
        self.assertEqual(p.read_bytes(), before, "neither door wrote the flags store")
        self.assertEqual(self.dirty, [], "nothing marked dirty")

    def test_a_bad_value_beside_an_unlisted_name_is_refused_for_the_name(self):
        # the route checks the name before the value; so does the socket
        ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": "threadMail", "value": "yes"})
        st, r = self._post("/flag", {"id": SID, "flag": "threadMail", "value": "yes"})
        self.assertEqual(st, 400)
        self.assertEqual(len(ws), 1)
        self.assertEqual(ws[0]["text"], self._wrapped(r["error"]))
        self.assertIn("flag must be one of", r["error"])
        self.assertIsNone(self._flags_file())

    def test_the_log_names_the_field_and_its_type_never_the_name_sent(self):
        # the kernel's log rule (_flag_type_note): the echo belongs in the frame the sender gets
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": "threadMail-TESTHOST", "value": True})
        self.assertEqual(len(ws), 1)
        line = err.getvalue()
        self.assertIn("romp-kernel: refused setSessionFlag: 'flag' is a string, not one of hideFromFeed, "
                      "postalServiceOff, notify", line)
        self.assertNotIn("threadMail-TESTHOST", line, "the client's name stays out of the kernel's log")
        self.assertIn("threadMail-TESTHOST", ws[0]["text"], "the sender still sees what it sent")

    def test_every_listed_name_is_accepted_on_the_socket_and_lands(self):
        for flag in km._LANE_FLAGS:
            ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": flag, "value": True})
            self.assertEqual(ws, [], "%s: no frame on success -- the next push carries the value" % flag)
        km._flags_cache.clear()
        self.assertEqual(self._flags_file(), {SID: {"hideFromFeed": True, "postalServiceOff": True, "notify": True}})
        self.assertEqual(self.dirty, [1, 1, 1])

    def _dial(self, wid):
        """A browser-style socket to the served Handler's /ws as the timeline page, announcing READY_GATE_CAP so no
        push reaches it before a `ready` it never sends: every frame it hears answers what it posted (the
        tests/test_feed_delta.py handshake)."""
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /ws?app=timeline&wid=%s&caps=%s&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
               "Origin: http://127.0.0.1:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (
                   wid, km.READY_GATE_CAP, km.TOKEN, self.port, self.port, key)
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                raise RuntimeError("closed during the handshake")
            buf += chunk
        head, buf = buf.split(b"\r\n\r\n", 1)
        self.assertTrue(head.startswith(b"HTTP/1.1 101"), head[:80])
        return s, buf

    def _gone(self, wid, deadline_s=5):
        """Wait until the kernel has torn the client down, so no handler thread writes under this test's root after
        its cleanup (the event is the client leaving _clients)."""
        deadline = time.time() + deadline_s
        while time.time() < deadline:
            with km._clients_lock:
                if not any(c.get("wid") == wid for c in km._clients):
                    return
            time.sleep(0.005)
        self.fail("the socket %s was never torn down" % wid)

    def _frames_until(self, s, buf, want):
        """Text frames off the socket until one satisfies `want`; (frames, leftover). A frame that never comes is
        the socket's 10 s timeout, raised."""
        got = []
        while True:
            op, payload, buf = _read_frame(s, buf)
            if op == 0x1:
                got.append(json.loads(payload.decode("utf-8")))
                if want(got[-1]):
                    return got, buf

    def _dispatched(self, s, buf, tag):
        """Ping, and read to its pong: every message sent before it has been dispatched. The text frames read on
        the way, and the leftover."""
        s.sendall(_ping_frame(tag))
        got = []
        while True:
            op, payload, buf = _read_frame(s, buf)
            if op == 0x1:
                got.append(json.loads(payload.decode("utf-8")))
            elif op == 0xA and payload == tag:
                return got, buf

    def test_a_real_socket_to_the_served_handler_is_refused_the_same_way(self):
        km._set_session_flag(OTHER, "postalServiceOff", True)
        km._flags_cache.clear()
        p = km.jd.STATE / "session-flags.json"
        before = p.read_bytes()
        refused = lambda fr: fr.get("type") == "settingRefused" and fr.get("flag") == "threadMail"
        frame = json.dumps({"type": "setSessionFlag", "id": SID, "flag": "threadMail", "value": True})
        wid = "w-wsflag"
        s, buf = self._dial(wid)
        try:
            s.sendall(_client_frame(frame))
            got, buf = self._dispatched(s, buf, b"one")      # the op has run: the store is final
            self.assertEqual(p.read_bytes(), before, "the socket op wrote the flags store: %s" % p.read_text())
            if not any(map(refused, got)):                   # the answer is queued; the pong may overtake it
                later, buf = self._frames_until(s, buf, refused)
                got += later
            st, r = self._post("/flag", {"id": SID, "flag": "threadMail", "value": True})
            self.assertEqual([fr for fr in got if refused(fr)], [{"type": "settingRefused", "gesture": "flag", "sid": SID,
                             "itemId": "", "flag": "threadMail", "value": None, "text": self._wrapped(r["error"])}])
            # a listed name lands over the same socket. Its answer, if it drew one, is queued ahead of the next
            # refusal's (one reader thread dispatches in order, one queue sends in order), so that refusal bounds the wait
            s.sendall(_client_frame(json.dumps({"type": "setSessionFlag", "id": SID, "flag": "hideFromFeed", "value": True})))
            s.sendall(_client_frame(frame))
            got, buf = self._frames_until(s, buf, refused)
            self.assertEqual([fr for fr in got if fr.get("type") == "settingRefused"], [got[-1]], "hideFromFeed drew no refusal")
            self.assertEqual(json.loads(p.read_text()), {OTHER: {"postalServiceOff": True}, SID: {"hideFromFeed": True}})
        finally:
            s.close()
            self._gone(wid)


_KERNEL_DIR = os.path.join(os.path.dirname(HERE), "kernel")


def _kernel_modules():
    """Every Python module in the kernel's directory, the directory the kernel loads its own modules from by file name
    (`load_source("romp_judge", HERE / "judge.py")`)."""
    return sorted(f for f in os.listdir(_KERNEL_DIR) if f.endswith(".py"))


_PARSES = {}   # kernel module file name -> how many times this module parsed it (_parse_kernel_module) in the process,
               # read by setUpModule (none before the module's first test) and by pin (3)


def _parse_kernel_module(name):
    """kernel/<name>'s tree, parsed here and counted in _PARSES: the census's OWN parse, made inside its build, held in
    the census and dropped with it, never through tests/parse_cache.py (_flag_census says why). READ-ONLY all the same:
    no attribute is written on a node (the parser shares its singleton nodes, a Load or an operator, with every tree in
    the process) and no node is copied; per-node data a test derives lives in a table keyed by id(node) that the test
    owns."""
    path = os.path.join(_KERNEL_DIR, name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    _PARSES[name] = _PARSES.get(name, 0) + 1
    return ast.parse(text, filename=path)


def _module_qual(module, name):
    """A function's key in the census: kernel.py's bare (`_set_session_flag`, `Handler._dispatch_ws`), another module's
    by its file (`judge.py:_hidden_from_feed`)."""
    return name if module == "kernel.py" else "%s:%s" % (module, name)


def _short(qual):
    """The name a function is mentioned by in code: `_set_session_flag` for itself, `_dispatch_ws` for
    Handler._dispatch_ws, `_hidden_from_feed` for judge.py:_hidden_from_feed (the kernel calls it as jd._hidden_from_feed)."""
    return qual.rsplit(":", 1)[-1].rsplit(".", 1)[-1]


def _source_functions(trees):
    """Every module of the kernel's directory, from its tree in `trees` ({module: tree}, the census's own parse, in
    _kernel_modules' order): {qualified name (_module_qual): def} for every module-level function and every method of a
    module-level class, and [(module, statement)] for the other top-level and class-level statements. Read-only: the
    tests read these, never change them. Called once per build of the census, and the census is built once per module
    run (_flag_census)."""
    fns, rest = {}, []
    for module, tree in trees.items():
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fns[_module_qual(module, node.name)] = node
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fns[_module_qual(module, "%s.%s" % (node.name, sub.name))] = sub
                    else:
                        rest.append((module, sub))
            else:
                rest.append((module, node))
    return fns, rest


def _callee(call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


_DOTTED = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


def _text_of(value):
    """A str or bytes constant's value as text (bytes read as latin-1, which maps every byte to one character, so an
    ASCII name reads the same either way); None for any other constant. The census reads a name spelled whole in either
    kind of literal alike: `b"session-flags.json".decode()` names the store as surely as the str does."""
    if type(value) is bytes:
        return value.decode("latin-1")
    return value if type(value) is str else None


def _mentioned(node):
    """The names a node mentions as code: a Name's id, an Attribute's attr, every part of a string or bytes constant
    that is an identifier or a dotted chain of them (_text_of), and every dotted part of an import alias's imported
    name. A string reaches a function as surely as its name does (`globals()["_set_session_flag"](...)`,
    `getattr(self, "_dispatch_ws")`, `attrgetter("Handler._dispatch_ws")`, the same with a bytes literal decoded), and
    so does an import (`from M import _set_session_flag as w` mentions _set_session_flag, the name it binds to w; the
    reviewer's ruling on round 1 of fork PR #909, fresh-2). A star import spells no name, and a name inside a longer
    string (source text handed to eval) or built from pieces is outside, as FlagWriterPopulation's docstring says.
    _facts reads the same four spellings."""
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Constant):
        text = _text_of(node.value)
        return set(text.split(".")) if text is not None and _DOTTED.fullmatch(text) else set()
    if isinstance(node, ast.alias) and node.name != "*":
        return set(node.name.split("."))
    return set()


def _mentions(node, names):
    """Every node under `node` that mentions a name in `names` as code (_mentioned): a call by name, and equally a setter
    bound to a local, bound by an import alias, put in a table, given as a default, handed on as a callback, or named
    by a string."""
    return [n for n in ast.walk(node) if _mentioned(n) & names]


def _door_names(test):
    """The doors an `if` test selects: ("socket op", name) where it compares the frame's type (msg.get("type") or
    msg["type"]) and ("route", path) where it compares a request path (`path` or `u.path`), by == a string or by
    membership in a literal tuple, list or set of strings, anywhere under an and/or."""
    out = set()
    for n in ast.walk(test):
        if not (isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Eq, ast.In))):
            continue
        left, right = n.left, n.comparators[0]
        if (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute) and left.func.attr == "get"
                and left.args and isinstance(left.args[0], ast.Constant) and left.args[0].value == "type") or (
                isinstance(left, ast.Subscript) and isinstance(left.slice, ast.Constant) and left.slice.value == "type"):
            kind = "socket op"
        elif (isinstance(left, ast.Name) and left.id == "path") or (isinstance(left, ast.Attribute) and left.attr == "path"):
            kind = "route"
        else:
            continue
        vals = [right] if isinstance(right, ast.Constant) else list(right.elts) if isinstance(right, (ast.Tuple, ast.List, ast.Set)) else []
        out.update((kind, v.value) for v in vals if isinstance(v, ast.Constant) and isinstance(v.value, str))
    return out


def _door_walk(fn, qual):
    """[(door, node)] for every node in `fn`, the door being the innermost `if` arm whose test selects one (_door_names),
    as a frozenset of its (kind, name) pairs; a node under no such arm is keyed {("no door", qual)}, which no expected
    population holds, so a setter call there reds loudly. An arm's test and its else branch belong to the enclosing door.
    The def's decorators, parameter defaults and annotations are walked too, under no door, so every node _mentions finds
    in `fn` is keyed. In pre-order (a node, then each child's whole subtree in turn), from an explicit stack: no closure
    that refers to itself, so the census's build (_derive_flag_census) leaves no cycle behind and dropping the census
    frees it by reference count, with no collection (_flag_census)."""
    out = []
    top = frozenset({("no door", qual)})
    roots = list(fn.decorator_list) + [fn.args] + ([fn.returns] if fn.returns is not None else []) + list(fn.body)
    stack = [(st, top) for st in reversed(roots)]
    while stack:
        node, door = stack.pop()
        out.append((door, node))
        if isinstance(node, ast.If):
            names = _door_names(node.test)
            arm = frozenset(names) if names else door
            stack.extend(reversed([(node.test, door)] + [(st, arm) for st in node.body]
                                  + [(st, door) for st in node.orelse]))
            continue
        stack.extend(reversed([(child, door) for child in ast.iter_child_nodes(node)]))
    return out


def _doors_reaching(walk, targets):
    """{door: [line of each call]} for every call in a function's door walk (_door_walk) to a name in `targets`. The ask
    of the predicate is read this way: a door asks only by calling it."""
    found = {}
    for door, node in walk:
        if isinstance(node, ast.Call) and _callee(node) in targets:
            found.setdefault(door, []).append(node.lineno)
    return found


def _doors_naming(walk, targets):
    """{door: [line of each mention]} for every node in a function's door walk (_door_walk) that mentions a name in
    `targets` (_mentioned). The setters are read this way: an arm that binds a setter to a local, imports it under an
    alias, picks it from a table, hands it on or names it by a string writes through it as surely as one that calls it
    by name, so the mention makes the door."""
    found = {}
    for door, node in walk:
        if _mentioned(node) & targets:
            found.setdefault(door, []).append(node.lineno)
    return found


_STORE_NEEDLE = "session-flags"   # how the kernel's source names the flags store: STATE / "session-flags.json"


def _store_seeds(node):
    """The str or bytes constants under `node` that name the flags store in CODE: any constant whose text (_text_of)
    contains "session-flags" (a whole file name, a piece of an f-string, an implicitly joined literal, a bytes literal
    decoded). A docstring, or any constant standing as a statement of its own, is text about the code and is left
    out."""
    text = {id(n.value) for n in ast.walk(node)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and _text_of(n.value.value) is not None}
    return [n for n in ast.walk(node) if isinstance(n, ast.Constant) and _STORE_NEEDLE in (_text_of(n.value) or "")
            and id(n) not in text]


_NESTED = frozenset({ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef})   # the scopes a def holds


def _holds(node, seeds, names):
    """Whether a def, lambda or class holds what it mentions: a seed, or a name in `names` loaded, anywhere in it (its
    body, a parameter's default, a decorator, a class attribute), whatever it does there, a comparison included. Its
    object keeps the value in a closure cell, a default or its namespace, or builds it again when called, so the object
    itself carries it and goes wherever a value goes: returned, kept, or handed to a call."""
    return any(id(m) in seeds or (type(m) is ast.Name and m.id in names and isinstance(m.ctx, ast.Load))
               for m in ast.walk(node))


def _carries(node, seeds, tainted):
    """Whether `node` can hand on the store's path: a seed or a tainted name under it. A comparison is skipped, since its
    value is a bool: `p.name == "session-flags.json"` hands nothing on. A def, lambda or class under it carries what it
    holds (_holds), a comparison inside it included, since its closure keeps the name whatever its body computes."""
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Compare):
            continue
        if type(n) in _NESTED:
            if _holds(n, seeds, tainted):
                return True
            continue
        if id(n) in seeds or (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in tainted):
            return True
        stack.extend(ast.iter_child_nodes(n))
    return False


def _root_name(node):
    """The name at the root of a subscript or attribute chain (`msg` for msg["flag"], `cache` for cache[k].x), else None."""
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _call_spelling(call, modules, misbound=frozenset()):
    """A call's name in the census below: the name for a bare call (`open`, `_read_state_json`); the dotted chain when the
    receiver is rooted at a module the kernel imports (`os.replace`, `os.path.join`); `.attr` for a method of any other
    value (`.stat`, `.write_text`), so os.replace and a value's .replace stay apart; `<Subscript>` and the like for a
    callee this cannot name, which no expected set holds (a call's result called, `<Call>`); and `<bound NAME>` when the
    name, or the module at the root of the chain, is one the calling function does not see bound as READS read it
    (`misbound`, _misbound), so a nested `def sorted(q)` that writes q, `str = lambda q: ...` or `Path =
    shutil.copyfile` is a call no set holds, not the read its spelling names."""
    return _callee_spelling(call.func, modules, misbound)


def _callee_spelling(f, modules, misbound=frozenset()):
    """_call_spelling's name for the callee expression `f` itself, which is also how a decorator, a class's base and a
    metaclass are spelled: each is called with the def or class it applies to (_store_flow). A decorator that is a
    call (`@register("k")`) applies the call's result, so it spells `<Call>`, a name no set holds."""
    if isinstance(f, ast.Name):
        return "<bound %s>" % f.id if f.id in misbound else f.id
    if isinstance(f, ast.Attribute):
        chain, v = [f.attr], f.value
        while isinstance(v, ast.Attribute):
            chain.append(v.attr)
            v = v.value
        if isinstance(v, ast.Name) and v.id in modules:
            return "<bound %s>" % v.id if v.id in misbound else ".".join([v.id] + chain[::-1])
        return "." + f.attr
    return "<%s>" % type(f).__name__


_PATH_EXIT = "<path exit>"       # _store_flow's key for a return or yield of the store's path itself
_PATH_STORED = "<path stored>"   # _store_flow's key for the path, or an object that holds it, kept where another
                                 # function can read it
_PATH_KEYED = "<path as a key of> "   # _store_flow's key prefix for the path stored as a subscript's index, then its root
# the calls whose value is never the path they read (the receiver, or the first argument) but what they read from the
# file or a fact about it: a stat, the parsed content, an identity key built from a stat. These are the ONLY calls the
# path stops at (_path_valued), and only at what they read: a path-valued second argument or keyword (a callback such
# as json.loads' object_hook, whose return becomes the call's value) is handed back. Any other call is taken to hand
# back its receiver and its arguments, so a call missing here makes a false path exit, a red that asks for it to be
# classed, never a missed one. Each was read in the kernel: _read_state_json returns the parsed file or None, _stat_key
# and _chat_ident a tuple of stat fields or None. A name among them is a stop only where it is bound as it was read
# (_READ_BINDINGS, _misbound); .stat, a method, is read by its name alone, and so is the .get rule's .get.
_PATH_STOPS = frozenset({".stat", "os.stat", "_read_state_json", "json.loads", "_stat_key", "_chat_ident"})
# the binding each name READS and _PATH_STOPS spell was read against, for a bare name and for the module at the root of
# a dotted one, so that such a call is resolved by what its name is bound to, not by its spelling (_misbound): None for
# a builtin (bound nowhere in the function or its module), an import for a module or a name brought in from one, and a
# def or class at kernel.py's top level, bound there once, for the kernel's own. A method (.get, .stat, .read_text,
# .append, .items) is named by its attribute on a value whose type the census does not know, so it has no entry here and
# is read by its name alone, FlagWriterPopulation's stated limit
_READ_BINDINGS = {
    "bool": None, "dict": None, "isinstance": None, "str": None, "sorted": None, "tuple": None,
    "Path": ("from", "pathlib", "Path"), "os": ("import", "os"), "json": ("import", "json"),
    "_read_state_json": ("def", "kernel.py"), "_flags_quarantined": ("def", "kernel.py"),
    "_flags_exit_text": ("def", "kernel.py"), "_StateUnreadable": ("class", "kernel.py"),
    "_note_state_fault": ("def", "kernel.py"), "_clear_state_fault": ("def", "kernel.py"),
    "_retire_flags_quarantine": ("def", "kernel.py"), "_stat_key": ("def", "kernel.py"),
    "_chat_ident": ("def", "kernel.py"), "_files_stat_observe_sig": ("def", "kernel.py")}
# the str fields of the syntax tree that never bind a name where they stand: an attribute's name, a keyword argument's
# name, the module a from-import reads, a class pattern's attribute names (and every type_comment). Every other str
# field of a node binds its value (a parameter, a def's or class's name, an except target, a match capture, a global or
# nonlocal declaration, a type parameter), so a field this list lacks, one a later Python adds among them, counts as a
# binding: the gap falls on the safe side, a read's name taken as bound otherwise, a false refusal
_NOT_BINDING = frozenset({("Attribute", "attr"), ("keyword", "arg"), ("ImportFrom", "module"),
                          ("MatchClass", "kwd_attrs")})
_BODIES = ("body", "orelse", "finalbody", "handlers", "cases")   # the fields of a statement holding a block of them


def _import_binding(node, alias):
    """(the name an import binds, how): ("import", M) for `import M` and `import M.x` (both bind M) and for
    `import M.x as n` (n bound to M.x); ("from", M, x) for `from M import x`, under its alias if it has one; and
    ("star", M) under the name "*" for a star import, which binds names the source does not spell."""
    if isinstance(node, ast.Import):
        if alias.asname:
            return alias.asname, ("import", alias.name)
        return alias.name.split(".")[0], ("import", alias.name.split(".")[0])
    module = "." * node.level + (node.module or "")
    if alias.name == "*":
        return "*", ("star", module)
    return alias.asname or alias.name, ("from", module, alias.name)


def _merge_bindings(out, found):
    """Add `found`'s bindings ({name: [how, ...]}) into `out`."""
    for name, hows in found.items():
        out.setdefault(name, []).extend(hows)


def _scope_bindings(node, skip=None):
    """{name: [how, ...]} for every name bound anywhere under `node`, a nested def's, lambda's or comprehension's own
    scope included (on the safe side: a name bound only there counts as bound in `node`'s): an import as _import_binding
    reads it, and ("other", line) for any other binding, a Name stored or deleted or a str field that _NOT_BINDING does
    not list (a parameter, a def's or class's name, an except target, a match capture, a global declaration). `skip` is
    the def being read, whose own name is bound in its module, not in itself."""
    out = {}
    for n in ast.walk(node):
        t = type(n)
        if t is ast.Name:
            if not isinstance(n.ctx, ast.Load):
                out.setdefault(n.id, []).append(("other", n.lineno))
        elif t is ast.Import or t is ast.ImportFrom:
            for a in n.names:
                name, how = _import_binding(n, a)
                out.setdefault(name, []).append(how)
        elif t is not ast.alias and t is not ast.Constant:
            kind = t.__name__
            for field, v in ast.iter_fields(n):
                if field == "type_comment" or (kind, field) in _NOT_BINDING or (n is skip and field == "name"):
                    continue
                for x in (v if type(v) is list else [v]):
                    if type(x) is str:
                        out.setdefault(x, []).append(("other", getattr(n, "lineno", 0)))
    return out


def _module_bindings(tree, module):
    """{name: [how, ...]} for every name `module` (its tree) binds in its own scope: each def or class of that scope as
    ("def", module) or ("class", module), and what its header binds, since the decorators, the defaults and annotations
    and a class's bases and keywords run in the module's scope (the body is its own); each import as _import_binding
    reads it; every other binding of a statement of that scope as _scope_bindings reads it, the blocks under an if, a
    try, a with or a loop included, an except target and a match capture among them; and ("global", line) for a global
    declaration anywhere in the module, since a function that declares a name global binds the module's. One walk of
    the module's statements; an expression is walked only where it stands in the module's own scope."""
    out = {}
    stack = [(s, True) for s in tree.body]
    while stack:
        s, top = stack.pop()
        t = type(s)
        if t is ast.Global:
            for name in s.names:
                out.setdefault(name, []).append(("global", s.lineno))
            continue
        if not top:
            # a statement of a def's or class's own scope: only a global declaration there binds the module's name
            for f in _BODIES:
                v = getattr(s, f, None)
                if type(v) is list:
                    stack.extend((x, False) for x in v)
            continue
        if t is ast.FunctionDef or t is ast.AsyncFunctionDef or t is ast.ClassDef:
            out.setdefault(s.name, []).append(("class" if t is ast.ClassDef else "def", module))
            if t is ast.ClassDef:
                header = s.decorator_list + s.bases + s.keywords
            else:
                a = s.args
                params = a.posonlyargs + a.args + a.kwonlyargs + [p for p in (a.vararg, a.kwarg) if p is not None]
                header = (s.decorator_list + a.defaults + [d for d in a.kw_defaults if d is not None]
                          + [p.annotation for p in params if p.annotation is not None]
                          + ([s.returns] if s.returns is not None else []))
            for h in header:
                _merge_bindings(out, _scope_bindings(h))
            stack.extend((x, False) for x in s.body)
            continue
        if t is ast.Import or t is ast.ImportFrom:
            for a in s.names:
                name, how = _import_binding(s, a)
                out.setdefault(name, []).append(how)
            continue
        for field, v in ast.iter_fields(s):
            if field in _BODIES:
                for x in v:
                    if isinstance(x, ast.stmt):
                        stack.append((x, True))
                        continue
                    if isinstance(x, ast.ExceptHandler):   # its target is the module's, its body a block of the module
                        if x.name:
                            out.setdefault(x.name, []).append(("other", x.lineno))
                        if x.type is not None:
                            _merge_bindings(out, _scope_bindings(x.type))
                    else:                                   # a match case: its captures and its guard are the module's
                        _merge_bindings(out, _scope_bindings(x.pattern))
                        if x.guard is not None:
                            _merge_bindings(out, _scope_bindings(x.guard))
                    stack.extend((y, True) for y in x.body)
                continue
            for x in (v if type(v) is list else [v]):
                if isinstance(x, ast.AST):
                    _merge_bindings(out, _scope_bindings(x))
                elif type(x) is str and field != "type_comment" and (t.__name__, field) not in _NOT_BINDING:
                    out.setdefault(x, []).append(("other", s.lineno))
    return out


def _misbound(fn, outer=None):
    """The names in _READ_BINDINGS that do not name, in `fn`, what READS and _PATH_STOPS were read against, so a call of
    one is not that read (_callee_spelling spells it `<bound NAME>`, a name no set holds, a write until classed). A name
    `fn` binds anywhere (_scope_bindings: a parameter, an assignment, a nested def or lambda, an import) is resolved
    there and is misbound unless every binding is the same import _READ_BINDINGS names; a name `fn` does not bind is
    resolved in its module's scope (`outer`, _module_bindings) and is misbound unless it is bound there as
    _READ_BINDINGS says: a builtin not at all, a module or an imported name only by that import, a def or class once, at
    kernel.py's top level. A star import in the module counts as a binding of every name. With no module scope given
    (`outer` None, StoreFlowReach's snippets) the function's own bindings alone decide."""
    local = _scope_bindings(fn, skip=fn)
    out = set()
    for name, want in _READ_BINDINGS.items():
        hows = local.get(name)
        if hows is None:
            if outer is None:
                continue
            hows = outer.get(name, []) + outer.get("*", [])
        if want is None:
            ok = not hows
        elif want[0] in ("def", "class"):
            ok = hows == [want]
        else:
            ok = bool(hows) and all(h == want for h in hows)
        if not ok:
            out.add(name)
    return frozenset(out)


def _module_of(qual):
    """The file of the module a census function lives in: `judge.py` for judge.py:_hidden_from_feed, kernel.py for a
    bare name (_module_qual)."""
    return qual.split(":", 1)[0] if ":" in qual else "kernel.py"


def _split(target, value):
    """[(target, value)] with a tuple or list target matched element by element against a tuple or list display of the
    same length with no starred element, recursively, so `p, k = (path, "name")` binds p from the path and k from the
    name; any other shape stays whole, every name in the target bound from the whole value, on the safe side."""
    if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)
            and not any(isinstance(e, ast.Starred) for e in target.elts + value.elts)):
        return [pair for t, v in zip(target.elts, value.elts) for pair in _split(t, v)]
    return [(target, value)]


def _bindings(fn):
    """[(target, value)] for every binding in `fn`: =, :=, an augmented or annotated assignment, a for, with or
    comprehension target, a match statement's captures, an import (its alias is both the target and the value, so an
    alias of a path helper is bound from the helper's name), each def, async def or class nested in it (the node is
    both the target and the value: its name is bound from what it holds, _holds), and each parameter that has a
    default, for the def and for every def, async def or lambda under it. A parameter's target is its ast.arg: the
    positional-only and positional parameters zipped from the tail with the defaults (which cover both kinds), the
    keyword-only ones with their kw_defaults that are not None. An assignment's tuple target is matched to a tuple
    display element by element (_split), and so is a for target to each element of a displayed iterable
    (`for p, k in ((path, "name"), ...)`)."""
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            out.extend(pair for t in n.targets for pair in _split(t, n.value))
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            if n.value is not None:
                out.append((n.target, n.value))
        elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
            if isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                out.extend(pair for e in n.iter.elts for pair in _split(n.target, e))
            else:
                out.append((n.target, n.iter))
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            out.extend((i.optional_vars, i.context_expr) for i in n.items if i.optional_vars is not None)
        elif isinstance(n, ast.Match):
            out.extend((case.pattern, n.subject) for case in n.cases)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            out.extend((a, a) for a in n.names)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = n.args
            pos = a.posonlyargs + a.args
            out.extend(zip(pos[len(pos) - len(a.defaults):], a.defaults))
            out.extend((k, d) for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None)
            if n is not fn and not isinstance(n, ast.Lambda):
                out.append((n, n))
        elif isinstance(n, ast.ClassDef):
            out.append((n, n))
    return out


def _bound_names(target):
    """The names a binding's target binds: a parameter's own name, the name an import binds (`fp` for `import h as fp`,
    `os` for `import os.path`), a nested def's or class's own name, the captures of a match pattern, or every Name
    stored under the target."""
    if isinstance(target, ast.arg):
        return {target.arg}
    if isinstance(target, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {target.name}
    if isinstance(target, ast.alias):
        return {(target.asname or target.name).split(".")[0]}
    out = set()
    for m in ast.walk(target):
        if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store):
            out.add(m.id)
        elif isinstance(m, (ast.MatchAs, ast.MatchStar)) and m.name:
            out.add(m.name)
        elif isinstance(m, ast.MatchMapping) and m.rest:
            out.add(m.rest)
    return out


def _path_valued(node, seeds, pathy, modules, misbound=frozenset()):
    """Whether `node` can be the store's path itself rather than a value read from the file: it reaches a seed
    (_store_flow's: a constant naming the store, or a mention of a path helper) or a name bound from a path-valued
    expression (`pathy`) through any expression but these, where the path STOPS: a comparison (a bool), an if-else's
    test (never its value), a subscript's index and a .get's first argument (a key looked up, not a value handed back),
    and what a call in _PATH_STOPS reads, its receiver and its first argument (what was read from the file, or a fact
    about it; its other arguments and keywords are not read, so a callback there hands back what it returns), a call
    whose name the function or its module binds otherwise (`misbound`, _misbound) stopping nothing. So
    `return p`, `return str(p)`, `return alt or p`, `return (q := p)`, `return [p][0]`, `return {"p": p}`,
    `return f"{p}"`, `return cache.get(k, p)` and `return json.loads(s, object_hook=lambda d: p)` hand the path back,
    while `return json.loads(p.read_text())` and `return cache.get(str(p))` hand back what was read or looked up. A
    def, lambda or class is path-valued when it holds the path (_holds: it mentions a seed or a path-valued name
    anywhere in it, a comparison included), since its object keeps the path in a closure, a default or a class
    attribute, or builds it when called; so `return lambda: p`, `REG.append(g)` for a nested `def g(): return p`, and a
    returned class whose body binds the path each hand it on. The rule lists where the path stops, not the ways it goes
    through: a list of the ways through missed the next spelling (an `or`, a walrus, a subscript of a display, a dict
    and a .get's default each got past one, and then a nested def, a class body, a closure kept in a list), where a
    stop missing here makes a false exit, which the role check reds."""
    stack = [node]
    while stack:
        n = stack.pop()
        if id(n) in seeds:
            return True
        t = type(n)
        if t is ast.Name:
            if n.id in pathy and isinstance(n.ctx, ast.Load):
                return True
        elif t is ast.Compare:
            pass
        elif t in _NESTED:
            if _holds(n, seeds, pathy):
                return True
        elif t is ast.IfExp:
            stack += [n.body, n.orelse]
        elif t is ast.Subscript:
            stack.append(n.value)
        elif t is ast.Call and _call_spelling(n, modules, misbound) in _PATH_STOPS:
            stack += n.args[1:] + [k.value for k in n.keywords]
        elif t is ast.Call and _call_spelling(n, modules, misbound) == ".get":
            stack += [n.func.value] + n.args[1:] + [k.value for k in n.keywords]
        else:
            stack.extend(ast.iter_child_nodes(n))
    return False


def _store_flow(fn, modules, helpers=frozenset(), outer=None):
    """{where the flags store's path goes: [line, ...]} for `fn`: each call handed the path, or anything computed from
    it, by its spelling (_call_spelling); _PATH_EXIT, a return or yield of the path itself; and _PATH_STORED, the path
    kept where another function can read it.
    Seeded at the constants naming the store (_store_seeds) and at each mention of a path helper (`helpers`, their short
    names, which _derive_namers finds; a mention as _mentioned reads it: a call, a reference bound to a local as in
    `get = _flags_path`, an import of it, a name in a string), so the caller of a helper is traced from there. A name
    bound from an expression that carries a seed (_bindings) carries it on, to a fixpoint, and so does the root of a
    subscript or attribute assigned such a value (`cache[k] = p` taints `cache`). A call is handed it when an argument,
    a keyword's value or its receiver carries it. Over-approximate on purpose: a value computed from the path (its
    stat, a cache entry keyed by it) carries too, so the reads a reader is pinned to list a few calls that only ever see
    such a value.
    A def, async def, lambda or class nested in `fn` is a value like any other: it holds what it mentions (_holds), so
    a nested def or class binds its name from itself (_bindings), a lambda is path-valued where it stands, and each goes
    wherever a value goes. So `open(fp(), "w")` for a nested `def fp(): return <the path>` is a call handed the path,
    and a closure over the path appended to a list, or a class holding it returned, is kept or handed back. Its own
    calls, open() inside a lambda among them, are read as `fn`'s. Over-approximate here too: a nested def that only
    reads the path still holds it, so what a call of it returns counts as the path, and a reader whose nested def
    reads the file reds as returning the path until the read moves into its own body.
    The exits are keyed on the path itself (_path_valued), not on anything computed from it, since the readers return
    values read from the file (keyed on carrying, seven of the nine readers would have one). A Return, Yield or
    YieldFrom of `fn`'s own body whose value is the path is a _PATH_EXIT: the function hands the path to its caller, a
    path helper (NAMERS' "path" role), and _derive_namers makes every function that mentions it a namer in turn. A
    return inside a nested def or lambda is that scope's, not `fn`'s: the scope's object carries the path instead.
    The path, or an object that holds it, kept anywhere but a plain local name is a _PATH_STORED, which the role check
    refuses under every role: a subscript or attribute assigned it, whatever its root (a module-level table, `self`, a
    parameter, or a local, which may alias either), a name the function declares global, and a call of a method of a
    value (not of a module the kernel imports) handed it as an argument, `.append(p)` among them, since the receiver
    may keep it; .get is the one method left out, its arguments a key it looks up and a default it hands back. An
    augmented assignment of it to a name (`out += [p]`) is one too: a list, dict or set takes it in place, and the
    object a parameter or an alias names keeps it. Tracing a kept path would need every reader of what keeps it (the
    reviewer's ruling on round 1 of fork PR #909, extra6-1 and fresh-1, refused the module-level store; a store on
    `self` and an append got past a refusal keyed on a module-level root). The path stored as a subscript's index
    (`cache[str(p)] = v`) keeps it as a key, which whoever iterates the container reads: keyed _PATH_KEYED plus the
    subscript's root, and refused by the role check but at a site FlagWriterPopulation.KEYED classes by reading it.
    The implicit calls count as calls: a decorator is called with the def or class it decorates, and a class's bases
    and metaclass with the class (a base's __init_subclass__). So each decorator of a nested def or class that
    carries the path, each base and metaclass of such a class, and each decorator of `fn` itself when `fn` is a path
    helper, is handed it by its spelling (_callee_spelling), and one that is a method of a value (`@REG.append`) keeps
    it.
    It judges no WRITE by its spelling: FlagWriterPopulation.READS lists what a reader may hand the path to, and any
    other call is a write until someone classes it. Nor a READ by its spelling alone: a bare name, or the module at the
    root of a dotted one, that `fn` binds, or that its module (`outer`, _module_bindings) binds otherwise than it was
    read against, is spelled `<bound NAME>` (_misbound), so it is neither a read nor a stop; a method is read by its
    name alone, FlagWriterPopulation's stated limit."""
    misbound = _misbound(fn, outer)
    seeds = {id(n) for n in _store_seeds(fn)}
    if helpers:
        seeds |= {id(n) for n in ast.walk(fn) if _mentioned(n) & helpers}
    pairs = _bindings(fn)
    tainted, pathy = set(), set()
    while True:
        grown, grown_pathy = set(tainted), set(pathy)
        for target, value in pairs:
            if _carries(value, seeds, tainted):
                grown |= _bound_names(target)
                if isinstance(target, ast.expr):
                    grown |= {r for m in ast.walk(target) if isinstance(m, (ast.Subscript, ast.Attribute))
                              and isinstance(m.ctx, ast.Store) for r in [_root_name(m)] if r}
            if _path_valued(value, seeds, pathy, modules, misbound):
                grown_pathy |= _bound_names(target)
        if grown == tainted and grown_pathy == pathy:
            break
        tainted, pathy = grown, grown_pathy
    handed = {}
    declared = {name for n in ast.walk(fn) if isinstance(n, ast.Global) for name in n.names}
    scopes = [n for n in ast.walk(fn) if n is not fn and type(n) in _NESTED]
    inner = {id(m) for s in scopes if not isinstance(s, ast.ClassDef)
             for part in (s.body if isinstance(s.body, list) else [s.body]) for m in ast.walk(part)}
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            spelled = _call_spelling(n, modules, misbound)
            given = list(n.args) + [k.value for k in n.keywords]
            receiver = [n.func.value] if isinstance(n.func, ast.Attribute) else []
            if any(_carries(x, seeds, tainted) for x in given + receiver):
                handed.setdefault(spelled, []).append(n.lineno)
            if spelled.startswith(".") and spelled != ".get" and any(
                    _path_valued(x, seeds, pathy, modules, misbound) for x in given):
                handed.setdefault(_PATH_STORED, []).append(n.lineno)
        elif isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom)) and id(n) not in inner:
            if n.value is not None and _path_valued(n.value, seeds, pathy, modules, misbound):
                handed.setdefault(_PATH_EXIT, []).append(n.lineno)
        elif (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and n.target.id not in declared
              and _path_valued(n.value, seeds, pathy, modules, misbound)):
            handed.setdefault(_PATH_STORED, []).append(n.lineno)
    # the implicit calls: each decorator is called with the def or class it decorates, and a class's bases and
    # metaclass with the class; the def itself when it is a path helper, a nested one when it holds the path
    for s in [fn] + [s for s in scopes if not isinstance(s, ast.Lambda)]:
        if s is fn:
            carried = kept = _PATH_EXIT in handed
        else:
            carried, kept = s.name in tainted, s.name in pathy
        if not carried:
            continue
        called = list(s.decorator_list)
        if isinstance(s, ast.ClassDef):
            called += list(s.bases) + [k.value for k in s.keywords]
        for c in called:
            spelled = _callee_spelling(c, modules, misbound)
            handed.setdefault(spelled, []).append(c.lineno)
            if kept and spelled.startswith(".") and spelled != ".get":
                handed.setdefault(_PATH_STORED, []).append(c.lineno)
    for target, value in pairs:
        if not isinstance(target, ast.expr):
            continue
        whole = _path_valued(value, seeds, pathy, modules, misbound)
        for m in ast.walk(target):
            if not isinstance(getattr(m, "ctx", None), ast.Store):
                continue
            if whole and (
                    isinstance(m, (ast.Subscript, ast.Attribute)) or (isinstance(m, ast.Name) and m.id in declared)):
                handed.setdefault(_PATH_STORED, []).append(m.lineno)
            elif isinstance(m, ast.Subscript) and _path_valued(m.slice, seeds, pathy, modules, misbound):
                handed.setdefault(_PATH_KEYED + (_root_name(m) or "<%s>" % type(m.value).__name__), []).append(m.lineno)
    return handed


def _unwrap_str(node):
    """`x` for str(x), str(str(x)), and `node` itself otherwise: str() of the name a door was asked about is that name."""
    while (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str"
           and len(node.args) == 1 and not node.keywords):
        node = node.args[0]
    return node


_LOADERS = ("load_source", "spec_from_file_location")   # the calls a module loads a sibling module by, naming its file
_NO_CHILD = {"ctx", "op", "ops"}   # the fields holding an expression context or an operator, neither with a child node
_CHILD_FIELDS = {}                 # node class -> its fields but those (_facts); keyed by class, never by a node
_Facts = namedtuple("_Facts", "names callees seeded lane loads")
_WALKS = None                      # {id(unit): _facts walks} while a build of the census runs (_flag_census), else None


def _facts(node):
    """Everything the census reads from one unit (a def or a statement, _unit_facts), from ONE walk of it. names:
    {name: the number of nodes under the unit that mention it as code (_mentioned)}, so its keys are every name the unit
    mentions and a count is how many nodes _mentions(node, {name}) finds, an import alias counted by the parts of the
    name it imports, as _mentioned reads it. callees: _callee of every call under it.
    seeded: whether it names the flags store in code (_store_seeds(node) is not empty). lane: whether a comparison
    under it tests membership in _LANE_FLAGS (one of its operators `in` or `not in`, the name one of its comparators).
    loads: the file names it loads a sibling module by, each ".py" string constant inside a call in _LOADERS
    (`load_source("romp_judge", HERE / "judge.py")`). It visits every node ast.walk(node) visits except an expression
    context or an operator (no child, no name, no call; a comparison's operators are read on the comparison), in a
    stack's order rather than a queue's, which no fact depends on: each is a count, a set or a flag. A type test
    stands for isinstance, since the parser builds each node as its exact class. Read-only, as the trees must be
    (_parse_kernel_module). One walk per unit is round 1's cost cut on fork PR #909, the reviewer's ask after the PR's
    own Python 3.10 cell hit CI's 25-minute wall: the census had walked every function once per fact and once per round
    of _derive_roads, about 5 s of the module's run on 3.10. While a build of the census runs, each call is counted in
    the build's walk table (_WALKS, keyed by id(node)), which the mechanism pin reads: each unit walked exactly once."""
    if _WALKS is not None:
        _WALKS[id(node)] = _WALKS.get(id(node), 0) + 1
    Name, Attribute, Constant, Alias, Call, Expr, Compare, AST = (ast.Name, ast.Attribute, ast.Constant, ast.alias,
                                                                  ast.Call, ast.Expr, ast.Compare, ast.AST)
    # locals: the loop runs once per node
    names, callees, loads, text, needles, lane = {}, set(), set(), set(), [], False
    count, dotted = names.get, _DOTTED.fullmatch
    stack = [node]
    pop, push, extend = stack.pop, stack.append, stack.extend
    while stack:
        n = pop()
        t = type(n)
        if t is Name:                      # id and ctx: no child to walk
            names[n.id] = count(n.id, 0) + 1
            continue
        if t is Attribute:                 # value, attr and ctx: value is the one child
            names[n.attr] = count(n.attr, 0) + 1
            push(n.value)
            continue
        if t is Constant:                  # value and kind: no child
            v = n.value
            if type(v) is bytes:           # a bytes literal read as text, as _text_of reads it
                v = v.decode("latin-1")
            if isinstance(v, str):
                if dotted(v):
                    for m in set(v.split(".")):
                        names[m] = count(m, 0) + 1
                if _STORE_NEEDLE in v:
                    needles.append(id(n))
            continue
        if t is Alias:                     # name and asname, both strings: no child
            if n.name != "*":
                for m in set(n.name.split(".")):
                    names[m] = count(m, 0) + 1
            continue
        if t is Call:
            c = _callee(n)
            callees.add(c)
            if c in _LOADERS:
                loads.update(x.value for x in ast.walk(n)
                             if isinstance(x, Constant) and isinstance(x.value, str) and x.value.endswith(".py"))
        elif t is Expr:
            if isinstance(n.value, Constant) and isinstance(n.value.value, (str, bytes)):
                text.add(id(n.value))      # a constant standing as a statement is text about the code (_store_seeds)
        elif t is Compare:
            lane = lane or (any(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops)
                            and any(isinstance(c, Name) and c.id == "_LANE_FLAGS" for c in n.comparators))
        fields = _CHILD_FIELDS.get(t)
        if fields is None:
            fields = _CHILD_FIELDS[t] = tuple(f for f in t._fields if f not in _NO_CHILD)
        for f in fields:
            v = getattr(n, f, None)
            if isinstance(v, AST):
                push(v)
            elif isinstance(v, list):
                extend([x for x in v if isinstance(x, AST)])
    return _Facts(names, frozenset(callees), bool(set(needles) - text), lane, frozenset(loads))


def _unit_facts(tree):
    """({id(unit): _facts(unit)}, loads) for one module's tree. The units are the pieces _source_functions splits a
    module into, each top-level statement but a class and each statement of a class's body, so every def in fns and
    every statement in rest is one; the table is keyed by id(unit), the census's own, never an attribute on a node.
    loads is the union of every unit's and of each class's parts outside its body (decorators, bases, keywords): every
    node ast.walk(tree) visits but the module and the classes themselves, neither of them a call."""
    table, loads = {}, set()
    for node in tree.body:
        units = [node]
        if isinstance(node, ast.ClassDef):
            body = {id(st) for st in node.body}
            for part in ast.iter_child_nodes(node):
                if id(part) not in body:
                    loads |= _facts(part).loads
            units = node.body
        for st in units:
            table[id(st)] = f = _facts(st)
            loads |= f.loads
    return table, frozenset(loads)


_CENSUS_BUILDS = 0   # the censuses _flag_census has built in this PROCESS, counted when a build returns (one that
                     # raises made no census); setUpModule reads it before the module's first test, so the mechanism
                     # pin can tell a build in the module's run from one at import; tearDownModule reads it for pin (2)


class _Census(dict):
    """The census's facts as ONE object that takes a weak reference (a plain dict cannot), so tearDownModule can read
    that the facts are gone once FlagWriterPopulation drops them (pin 2 there)."""
    __slots__ = ("__weakref__",)


def _flag_census():
    """Build FlagWriterPopulation's census (_derive_flag_census) from the class's sets and the kernel directory's trees,
    which the build parses itself (_parse_kernel_module), and count the build (_CENSUS_BUILDS) and its _facts walks
    (_WALKS, kept in the census as "walks"). The class's setUpClass calls it once per module run and holds the one
    reference; its tearDownClass drops it, so the facts and the trees are freed before the next module's first test.
    No test instance keeps a reference of its own.
    WHY NOT tests/parse_cache.py's derived(): derived() memoises the value for the whole process and calls gc.freeze()
    after a build, and the freeze is process-global. In CI's serial run this module sorts at about 61 percent, so its
    build was the run's first freeze, and every later read of the kernel's perf snapshot (_PerfStats.snapshot reads
    gc.get_freeze_count(), which walks the permanent generation on every call) paid per read for everything frozen here.
    Measured at round 1 of fork PR #909 from the PR's own Python 3.10 cell: 58 s over main's cell at the same base,
    most of it in the snapshot readers that sort after this module and in the thread-stop census, which reads the
    frozen count itself (the reviewer's ruling of that round). So the module changes no collector state at all: no
    gc.freeze, gc.disable or gc.collect, since the first is process-global and the other two walk every tracked object.
    WHY NOT THE CACHE'S SHARED PARSE EITHER, this census's exception to tests/parse_cache.py's one-cache rule: read
    through source_and_tree, which freezes nothing, the trees stayed in the cache, tracked, from this module until the
    thread-stop census froze them, and every full collection in between walked them. Measured at round 2 of fork PR
    #909 on Python 3.10, the 14 snapshot readers after this module, run in one process after it, took 34.5 to 41.2 s
    with the trees read through the cache (16 full collections took 10.5 to 14.5 s of that) against main's 23.6 to
    29.0 s; with the census's own parse, released with its facts, they took 25.3 to 27.2 s, inside main's run-to-run
    spread, and Python 3.12 gave the same picture. What the exception costs: the thread-stop census, which sorts after
    this module, parses the kernel's files itself, as it did before this census existed.
    THE RULE FOR THE BUILD: it leaves no cycle behind, so that dropping the one reference frees the facts and the trees
    by reference count, with no collection. Its value is plain data (dicts, sets, tuples, the trees and their nodes, and
    tables keyed by id(node)) and it makes no closure or object that refers back to itself. A cycle through the held
    object is pinned (tearDownModule's weak reference, pin 2). A cycle among the inner containers that does not pass
    through the held object, or an inner container kept by another name, would leave the held object free and that pin
    green, so that half is a measurement: with the collector off, a collection right after this build found nothing
    unreachable when the census adopted tests/parse_cache.py, again after round 1's one-walk cut on fork PR #909, and
    again at round 2 of that PR, where a collection right after dropping the census found nothing unreachable either."""
    global _CENSUS_BUILDS, _WALKS
    _WALKS = walks = {}
    try:
        census = _derive_flag_census(FlagWriterPopulation)
    finally:
        _WALKS = None
    census["walks"] = walks
    _CENSUS_BUILDS += 1
    return census


_FROZEN_BEFORE = None   # gc.get_freeze_count() before the module's first test (setUpModule), pin (1)'s first read
_BUILT_BEFORE = None    # (censuses built, kernel modules parsed) before the module's first test (setUpModule), which
                        # the mechanism pin requires to be (0, 0)
_CENSUS_REF = None      # a weak reference to the census FlagWriterPopulation holds (its setUpClass), pin (2)'s subject


def setUpModule():
    """The first reads, before the module's first test and not at import (pytest imports every module at collection,
    before any test runs). Pin (1)'s: gc.get_freeze_count(), which tearDownModule reads again; two reads only, since
    each walks the permanent generation. The mechanism pin's: how many censuses _flag_census has built and how many
    kernel modules _parse_kernel_module has parsed so far in the process (_CENSUS_BUILDS, _PARSES), both counted per
    process, so a build at import would count as the module's one build. That pin requires both to be 0 here: a census
    or a tree made at import would be held, tracked, through every module that sorts before this one, the retention
    that ruled out the cache's shared parse (_flag_census), over the first 61 percent of CI's serial run."""
    global _FROZEN_BEFORE, _BUILT_BEFORE
    _FROZEN_BEFORE = gc.get_freeze_count()
    _BUILT_BEFORE = (_CENSUS_BUILDS, sum(_PARSES.values()))


def tearDownModule():
    """The census's two pins on what the module leaves behind, read after its last test, and so after
    FlagWriterPopulation's tearDownClass dropped the census, in the same process as setUpModule.
    (1) The module froze nothing: gc.get_freeze_count() is not above what setUpModule read. The count is live and falls
    when a frozen object dies, so an object an earlier module froze can lower it in between, while nothing but a freeze
    inside the module raises it. Red under a build through tests/parse_cache.py's derived(), which freezes every object
    tracked when its build returns (about 1.16 million in the module's own process at round 1 of fork PR #909).
    (2) The census is gone: the weak reference setUpClass took is dead, read with no gc.collect(), since with no cycle
    reference counting has already freed it, and a collection walks every tracked object (seconds at a serial cell's
    heap). Red under a module-scope cache that keeps the census and under a build whose value refers back to itself. It
    does not see a cycle among the inner containers that does not pass through the held object, or an inner container
    kept by another name (_flag_census states that half as a measurement). Not read through gc.get_objects(), which
    does not list frozen objects, so under a derived() build it would find nothing and pass for the wrong reason.
    Neither pin skips without a word: a census built (_CENSUS_BUILDS above 0) with no weak reference taken reds pin
    (2), and a missing first read reds pin (1). The one silent case is pin (2) when no census was built at all (every
    FlagWriterPopulation test deselected), where there is nothing to be gone."""
    problems = []
    if _CENSUS_REF is None:
        if _CENSUS_BUILDS:
            problems.append("pin (2): %d census(es) built in this process but no weak reference was taken to the one "
                            "FlagWriterPopulation holds (its setUpClass takes it), so this pin cannot read that the "
                            "census is gone" % _CENSUS_BUILDS)
    elif _CENSUS_REF() is not None:
        problems.append("pin (2): the census FlagWriterPopulation held is alive after its tearDownClass dropped it: "
                        "something else keeps it (a module-scope cache, a test's own reference) or it refers back to "
                        "itself, a cycle that only a collection frees, and this module runs none")
    frozen = gc.get_freeze_count()
    if _FROZEN_BEFORE is None:
        problems.append("pin (1): setUpModule took no first read of gc.get_freeze_count(), so this pin cannot compare")
    elif frozen > _FROZEN_BEFORE:
        problems.append("pin (1): gc.get_freeze_count() rose from %d before the module's first test to %d after its "
                        "last: something in the module froze the heap (tests/parse_cache.py's derived() freezes after "
                        "a build), and every later read of the kernel's perf snapshot walks what is frozen"
                        % (_FROZEN_BEFORE, frozen))
    if problems:
        raise AssertionError("; ".join(problems))


def _unit_names_the_store(facts, helpers):
    """Whether a unit (a def or a statement, as _facts read it) reaches the flags store by a name it spells: its code
    names the store (seeded), or it mentions a path helper in `helpers`, called or not (`get = _flags_path`, or
    `_GET = _flags_path` at module level, reaches the file as surely as a call). The one predicate for both uses:
    _derive_namers grows the namers by it, and the role check refuses a module-level statement it holds for."""
    return facts.seeded or bool(facts.names.keys() & helpers)


def _derive_namers(fns, of, modules, trees=None):
    """(namers, flows, helpers): the functions that name the flags store, where each sends its path (_store_flow), and
    the path helpers among them by short name. A function names the store when its own code spells it (_facts'
    seeded) or when it mentions a path helper, a namer whose flow has a _PATH_EXIT, by that helper's short name (_facts'
    names: a call, and equally a reference bound to a local, an import of it or its name in a string, since each
    reaches the helper), grown to a fixpoint, so helpers chain: a function that returns a helper's result is a helper in
    turn. Each namer's flow is read with every mention of a helper as a seed, so a caller that hands a helper's result
    to open(), however it reached the helper, is handed the path there. Without this step a caller of a helper would
    name no store, and the setter derivations, which read the namers only, would never trace it (the reviewer's ruling
    on round 1 of fork PR #909, fresh-1). Each flow resolves the names READS spells through the namer's own bindings
    and then its module's scope (_misbound), read from `trees` ({module file: tree}) by _module_bindings once for each
    module that holds a namer; with no trees, through the namer's own bindings alone."""
    namers, helpers, scopes = {q for q, f in of.items() if f.seeded}, frozenset(), {}
    while True:
        if trees is not None:
            for m in {_module_of(q) for q in namers} - scopes.keys():
                scopes[m] = _module_bindings(trees[m], m)
        flows = {q: _store_flow(fns[q], modules, helpers, scopes.get(_module_of(q))) for q in namers}
        found = frozenset(_short(q) for q, flow in flows.items() if _PATH_EXIT in flow)
        grown = namers | {q for q, f in of.items() if _unit_names_the_store(f, found)}
        if grown == namers and found == helpers:
            return namers, flows, helpers
        namers, helpers = grown, found


def _derive_flag_census(cls):
    """The census, from the source: every function and statement (_source_functions); the names bound to a module in
    the kernel and in its judge (the other module that names the store), so a call spells as os.replace, not .replace
    (_call_spelling; an unknown spelling is outside READS, a write, and so is a read's name bound otherwise than it
    was read against, _misbound, in the function or in its module's scope); the functions that name the store, in
    code or by mentioning a path helper (namers, with each one's flow and the helpers, _derive_namers); the setters of
    session-flags.json, three ways: the functions that name the file and call a store write (the one door
    _write_state_json, its _atomic_write, a Path write), the functions that call the clean-write hook every landed
    write of that store runs (_flags_written), and the functions that hand the store's path to a call outside READS
    (_store_flow), whatever the call is spelled (a path exit and a kept path are not calls: a helper's callers are
    namers, traced in turn, and the role check refuses a kept path); every setter any of them finds with
    WRITERS (setters, and shorts, the names code mentions them by); the functions other than a setter that mention one
    (callers); and the roads (_derive_roads). Every unit of every module (each def and statement) is walked ONCE
    (_facts), and what the sets above and the tests read of a unit comes from that one walk: facts, keyed by id(unit),
    and loads, each module's files loaded by name. Each caller's door walk (_door_walk) is walked once here too, as
    door_walks, for the five tests that key a caller's nodes to its doors. trees holds each module's tree, the build's
    own parse (_parse_kernel_module), so the mechanism pin enumerates the units of the very trees the build walked and
    the trees go when the census goes. It returns one _Census; the build leaves no cycle behind, so dropping that
    object frees everything here by reference count (_flag_census)."""
    trees = {module: _parse_kernel_module(module) for module in _kernel_modules()}
    fns, rest = _source_functions(trees)
    modules = frozenset(n for m in (km, km.jd) for n, v in vars(m).items() if isinstance(v, type(os)))
    facts, loads = {}, {}
    for module, tree in trees.items():
        table, loads[module] = _unit_facts(tree)
        facts.update(table)
    of = {q: facts[id(fn)] for q, fn in fns.items()}
    namers, flows, helpers = _derive_namers(fns, of, modules, trees)
    writes = {"_write_state_json", "_atomic_write", "write_text", "write_bytes"}
    by_write = {q for q in namers if of[q].callees & writes}
    by_hook = {q for q, f in of.items() if "_flags_written" in f.callees}
    by_flow = {q for q in namers
               if {c for c in flows[q] if not c.startswith(_PATH_KEYED)} - cls.READS - {_PATH_EXIT, _PATH_STORED}}
    setters = cls.WRITERS.union(by_write, by_hook, by_flow)
    shorts = {_short(q) for q in setters}
    callers = {q for q, f in of.items() if q not in setters and f.names.keys() & shorts}
    return _Census(fns=fns, rest=rest, modules=modules, namers=namers, flows=flows, helpers=helpers,
                   writers=(by_write, by_hook, by_flow), setters=setters, shorts=shorts, callers=callers,
                   roads=_derive_roads({q: f.names for q, f in of.items()}, setters), facts=facts, loads=loads,
                   door_walks={q: _door_walk(fns[q], q) for q in callers}, trees=trees)


def _derive_roads(names, setters):
    """{(function, target): mentions} for every function that mentions a setter, then every function that mentions one
    of those, to a fixpoint, over every module of the kernel's directory (a mention as _mentioned reads it; a function
    matched by its bare name, so two sharing a name both count, on the safe side). A function's mentions of itself are
    left out. `names` is {function: {name: the number of its nodes that mention the name}} (_facts), so a round reads
    each function's counts instead of walking it: a node counts once toward each target it mentions, and a target
    matches exactly one name (_short), so a road's mentions are the count of that name."""
    on_road = set(setters)
    frontier, roads = set(on_road), {}
    while frontier:
        short = {}
        for t in frontier:
            short.setdefault(_short(t), set()).add(t)
        grown = set()
        for q, counts in names.items():
            for m in short.keys() & counts.keys():
                for t in short[m] - {q}:
                    roads[(q, t)] = roads.get((q, t), 0) + counts[m]
                    if q not in on_road:
                        grown.add(q)
        on_road |= grown
        frontier = grown
    return roads


class FlagWriterPopulation(unittest.TestCase):
    """The doors that write a session flag, derived from the kernel's source and pinned as a set (the reviewer's
    ruling in the round-3 review of fork PR #897): the setSessionFlag socket op and POST /flag, nothing else. Each asks
    the one predicate, _lane_flag_refusal, before its setter, returns on its answer before any setter runs, hands
    _set_session_flag as its flag argument the expression it asked the predicate about, with nothing rebinding that
    expression's root name in between, and calls each setter with exactly its pinned parameters (SIGNATURES). A new
    door (a socket op arm, a route, or a helper that calls a setter of session-flags.json) reds here until it is added
    on purpose. An arm is a door when it MENTIONS a setter (_doors_naming), so an arm that calls it by name, binds it to
    a local, imports it under an alias (`from M import _set_session_flag as w`), picks it from a table or names it by a
    string (`globals()["_set_session_flag"]`) is a door. Every road from a request to a setter is pinned (ROADS),
    derived upward from the setters by mention, so a new function or arm that hands a door function a client's input
    (a socket op forwarding to _state_write_route("/flag", ...), a second POST path onto it) reds as well. The setters
    are found without trusting how a function writes: every function that names the store in code (in a str or bytes
    literal) is pinned by role (NAMERS), and one that hands the store's path to anything but a read (READS) is a
    writer, so a writer spelled with open(), os.replace or a helper of its own reds as surely as one that calls
    _write_state_json, the path reaching it through an assignment or a parameter's default alike. A read is one by what
    its name is bound to, not by its spelling: a bare name in READS or the stops, or the module at the root of a dotted
    one, counts only where it is bound as it was read (_READ_BINDINGS: a builtin bound nowhere in the function or its
    module, a module or a name by its import, a kernel read by its one def or class at kernel.py's top level), so a
    nested `def sorted(q)` that writes q, `str = lambda q: ...`, `Path = shutil.copyfile`, a parameter named like a
    read, or a module that binds a read's name otherwise makes the call a write (_misbound). A helper that returns
    the path (a path helper, the kernel's own idiom for other stores, _views_path among them) passes the path on: it
    holds the "path" role, and every function that mentions it (a call, a reference bound to a local, an import of it)
    names the store in turn and is classed the same way, so a writer through it reds too. A def, lambda or class
    nested in a function is a value that holds whatever it mentions, in a closure, a default or a class attribute: a
    nested def that builds the path is followed to every call of it, and a closure or a class holding the path goes
    wherever a value goes, handed back, kept or handed to a call, its decorators, bases and metaclass included, since
    each is called with it. What a function hands back counts as the path unless it passes through a read of the file
    or a fact about it (_path_valued lists where the path stops, not the ways it goes through, so an `or`, a walrus, a
    subscript, a dict, a .get's default or a closure carries it), and a namer that keeps the path, or an object that
    holds it, anywhere but a plain local name (a subscript or attribute, whatever its root, `self` included; a name it
    declares global; a method call such as .append handed it, or a decorator that is one; a subscript's index, but at a
    site KEYED classes) is refused by the role check, not traced. The census reads every module in the kernel's
    directory, which holds every module the kernel loads (LOADED), so a writer in the judge or another loaded module
    counts as one in kernel.py does. It keys on names the source spells in code, which a docstring is not: a function
    that reached the file through a name it did not spell (a file name a client sent, as the saveFile op writes any
    text file under the file-editing consent; a path read back out of _flags_cache's keys, the one site KEYED allows,
    whose every use is a lookup; or what a call in READS keeps, each of those calls classed by reading it), a function
    that read a name or the path back by reflection (a frame's locals through locals(), vars() or a frame object, a
    top-level function's __defaults__ or __code__, a __doc__, the collector's referents), or one that reached a setter
    or a door function by reflection, by a name built from pieces, buried in source text handed to eval or brought in
    by a star import, would be outside it, and so is a module loaded by a path that names no ".py" file. A call in
    READS or the stops is taken to do what it did when it was classed by reading it, and a method among them (.get,
    .stat, .read_text, .append, .items) is read by its name alone, on a value whose type the census does not know: a
    .get of another object that writes the file, or one that returns its key and so hides the path a helper hands back,
    passes as the read its name promises (the witnesses are the two cases of
    StoreFlowReach.test_a_method_is_read_by_its_name_alone), and so does a read's name rebound from outside its module
    (another module's attribute, the builtins module, globals(), setattr). The stdlib's
    handler enters do_GET and do_POST by a name it builds, which is where the roads end. These read WHERE the code
    lives, so they guard the population and the arms' shape, not the behaviour; the behaviour is executed in
    SocketFlagWhitelist (the socket op, in process and over a real socket) and in
    FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (the route).

    WHAT THE NAME PINS READ, AND WHAT THEY DO NOT (the reviewer's disposition of the fourth re-verify's V4a and V4b:
    disclosed here, not chased with more rules). test_every_setter_writes_the_name_its_door_asked_about reads, as
    source text, the one expression each door asks the predicate about, the setter call's flag argument, and, for a
    rebind between the ask and the setter, that expression's own root name (`msg` for msg["flag"]);
    test_each_setter_takes_and_is_handed_exactly_its_pinned_parameters reads the setters' parameter lists and each
    door's setter calls. They do NOT read an alias of the frame (`fr = msg`, then `fr["flag"] = ...` after the gate,
    V4a), a name built from pieces, or the setters' bodies, so what a setter writes from the parameters it is handed is
    outside them (V4b's second name parameter is closed by SIGNATURES, which pins the parameters, not by reading the
    body). The reason: these are text-keyed guards, which can follow only the names the source spells, and each road
    around them has so far meant another rule. The behaviour is pinned by execution instead, in SocketFlagWhitelist's
    test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing,
    test_every_listed_name_is_accepted_on_the_socket_and_lands and
    test_a_real_socket_to_the_served_handler_is_refused_the_same_way. Those send the frames a client sends today, so a
    rewrite keyed on a field they do not send (V4a reads one) is outside them as well."""

    WRITERS = {"_set_session_flag", "_set_notify_session"}
    DOORS = {("socket op", "setSessionFlag"), ("route", "/flag")}
    # every function that names the store in code (_store_seeds) or mentions a path helper (_derive_namers), by role: a
    # "reader" hands the path only to READS; a "writer" writes it through _write_state_json and runs _flags_written; a
    # "path" helper returns or yields the path itself from its own body, or a def, lambda or class that holds it
    # (_store_flow's _PATH_EXIT), and hands it to nothing outside READS, its own decorators included, and every
    # function that mentions it is a namer, classed here in turn. No role may keep the path or an object that holds it
    # (_PATH_STORED). No function holds the "path" role today.
    # _state_quarantine compares a torn file's name with the store's to word its notice, and hands the path on to nothing
    NAMERS = {"_set_session_flag": "writer", "_set_notify_session": "writer",
              "_session_flags_proved": "reader", "_session_flags": "reader", "_flags_unknown_cold": "reader",
              "_thread_rows_key": "reader", "_chat_sig_shared": "reader", "_dead_lane_key": "reader",
              "_fleet_view_sig": "reader", "_state_quarantine": "reader", "judge.py:_hidden_from_feed": "reader"}
    # the sites that keep the store's path as a key (_store_flow's _PATH_KEYED), as (function, the container's root),
    # each read by hand: _session_flags keys the flags cache by str(path), and every use of _flags_cache in the kernel
    # looks that key up, pops it or sets it, none iterates the cache, so no function reads the path back out of it
    KEYED = {("_session_flags", "_flags_cache")}
    # what a reader hands the store's path, or a value computed from it, to (_store_flow): a stat, the strict reader
    # _read_state_json (which may move torn bytes aside, never write a flag), the judge's read of the text and its
    # parse (_hidden_from_feed), the quarantine bookkeeping (a mark retired, a fault noted or cleared, the refusal's
    # text), a cache lookup, plain value handling, and the calls that build a path from it (os.path.join, Path, str,
    # os.fspath: a path helper returns what they build). Each bare name and each module at a dotted name's root is
    # resolved by the binding it was read against (_READ_BINDINGS, one entry each); a method by its name alone
    READS = {".get", ".stat", "os.stat", "_read_state_json", ".read_text", "json.loads", "_flags_quarantined",
             "_flags_exit_text", "_StateUnreadable", "_note_state_fault", "_clear_state_fault", "_retire_flags_quarantine",
             "_stat_key", "_chat_ident", "_files_stat_observe_sig", ".append", ".items", "bool", "dict", "isinstance",
             "str", "sorted", "tuple", "os.path.join", "Path", "os.fspath"}
    # the modules the kernel loads by file name, from kernel.py to a fixpoint (_facts' loads): every one lives in the
    # kernel's directory, and the census reads that whole directory
    LOADED = {"kernel.py", "loadsource.py", "event_model.py", "judge.py", "colormap.py", "palette.py",
              "session_backend.py", "logins.py", "credentials.py", "sdk_backend.py", "host_transport.py",
              "session_host.py", "codex_backend.py", "codex_events.py", "codex_runtime.py"}
    SETTER_CALLS = {"_set_session_flag": 1, "_set_notify_session": 1}   # per door: each setter called once
    # each setter's parameters, exactly: what every door's call of it must bind, and all the setter is handed
    SIGNATURES = {"_set_session_flag": ("sid", "flag", "value"), "_set_notify_session": ("sid", "value")}
    # every road from a request to a setter, as {(function, a function on the way it mentions): mentions} (_roads): the two
    # door functions mention each setter once, do_POST hands _state_write_route the request, the socket's receive loop
    # (_ws) hands _dispatch_ws each client frame, and do_GET upgrades a request to that loop. The stdlib's handler enters
    # do_GET and do_POST by a name it builds, so nothing in the source mentions them and the walk ends there
    ROADS = {("_state_write_route", "_set_session_flag"): 1, ("_state_write_route", "_set_notify_session"): 1,
             ("Handler._dispatch_ws", "_set_session_flag"): 1, ("Handler._dispatch_ws", "_set_notify_session"): 1,
             ("Handler.do_POST", "_state_write_route"): 1, ("Handler._ws", "Handler._dispatch_ws"): 1,
             ("Handler.do_GET", "Handler._ws"): 1}
    # do_POST's arm that hands _state_write_route the request: one arm for the route function's three paths
    ROUTE_ARMS = {frozenset({("route", "/flag"), ("route", "/views"), ("route", "/order")})}

    census = None   # the census (_flag_census), the ONE reference to it: set by setUpClass, dropped by tearDownClass

    @classmethod
    def setUpClass(cls):
        """Build the census once for the class's run and hold it here; the weak reference is tearDownModule's pin
        (2)."""
        global _CENSUS_REF
        super().setUpClass()
        cls.census = _flag_census()
        _CENSUS_REF = weakref.ref(cls.census)

    @classmethod
    def tearDownClass(cls):
        """Drop the one reference, so reference counting frees the facts and the trees before the next module's first
        test."""
        cls.census = None
        super().tearDownClass()

    # the tests read the facts through the held census, never a copy of their own on the test instance
    @property
    def fns(self):
        return self.census["fns"]

    @property
    def rest(self):
        return self.census["rest"]

    @property
    def modules(self):
        return self.census["modules"]

    def _namers(self):
        return self.census["namers"]

    def _writers(self):
        """The setters of session-flags.json, three ways (_derive_flag_census): by a store write, by the clean-write
        hook, by where the store's path flows."""
        return self.census["writers"]

    def _setters(self):
        """Every setter any derivation finds, so a new one is also a name the doors below are derived against."""
        return self.census["setters"]

    def _shorts(self):
        """The setters as code mentions them (_short): a judge setter is called jd.<name> from the kernel."""
        return self.census["shorts"]

    def _callers(self):
        return self.census["callers"]

    def _roads(self):
        """{(function, target): mentions} for every road from a request to a setter (_derive_roads)."""
        return self.census["roads"]

    def _facts_of(self, unit):
        """What the census's one walk read from a def in fns or a statement in rest (_facts)."""
        return self.census["facts"][id(unit)]

    def _door_walk_of(self, q):
        """The door walk of a function that mentions a setter (_door_walk), walked once in the census and read by every
        test below that keys a caller's nodes to its doors."""
        return self.census["door_walks"][q]

    def test_the_census_is_one_derivation_over_one_parse_per_module(self):
        """The census's mechanism, read from counts. It is built once in this module's run however many tests read it
        (_CENSUS_BUILDS, which _flag_census keeps; a build per test reds here, and so that this holds whatever order the
        tests run in, a second test of the class is run from here first, its whole run with setUp and tearDown). Of that
        run this pin reads only that the test ran: its verdict belongs to that test's own run in the module, not to this
        pin, so under a kernel change that reds it (a new setter) this pin still runs its build, walk and parse checks
        below, and a build per test made in the same change reds here on the count. Nothing of the census is made before
        the module's first test: setUpModule read no census built and no kernel module
        parsed (_BUILT_BEFORE), since both counts are the process's and a census built at import would otherwise pass
        as the module's one build while held through every module that sorts before this one. That
        build walks each unit with _facts exactly once: each def in fns, each statement in rest, and each class's parts
        outside its body, read from the build's walk table (a walk outside _facts, such as an ast.walk per fact, is
        outside this count, and the module's measured time is the guard for it). And each module of the kernel's
        directory is parsed once in this module's run, by the build's own parse (_PARSES, which _parse_kernel_module
        keeps; the trees are the census's and go with it, _flag_census says why they are not the cache's). That the
        module froze nothing and that the census is gone once the class drops it are read in tearDownModule (pins 1
        and 2)."""
        other = unittest.TestResult()
        FlagWriterPopulation("test_the_setters_of_the_flags_store_are_the_two_the_doors_call").run(other)
        self.assertEqual(other.testsRun, 1, "a second test of the class ran beside this one")
        self.assertEqual(_BUILT_BEFORE, (0, 0), "(censuses built, kernel modules parsed) before the module's first "
                         "test, as setUpModule read them: none, since a census or a tree made at import is held, "
                         "tracked, through every module that sorts before this one")
        self.assertEqual(_CENSUS_BUILDS, 1, "the census is built once in this module's run, however many tests read it")
        units = {}
        for module, tree in self.census["trees"].items():
            for node in tree.body:
                parts = [node]
                if isinstance(node, ast.ClassDef):
                    body = {id(st) for st in node.body}
                    parts = [p for p in ast.iter_child_nodes(node) if id(p) not in body] + node.body
                for unit in parts:
                    units[id(unit)] = (module, unit)
        walks = self.census["walks"]
        wrong = sorted("%s:%d %s walked %d times" % (m, getattr(u, "lineno", 0), type(u).__name__, walks.get(i, 0))
                       for i, (m, u) in units.items() if walks.get(i, 0) != 1)
        self.assertEqual(len(wrong), 0, "%d units of the kernel's directory not walked by _facts exactly once in the "
                         "build, for example %s" % (len(wrong), wrong[:10]))
        self.assertEqual(len(walks.keys() - units.keys()), 0,
                         "_facts walked nodes that are not units of the kernel's trees")
        self.assertEqual({m: _PARSES.get(m, 0) for m in _kernel_modules()}, {m: 1 for m in _kernel_modules()},
                         "each module of the kernel's directory, parsed once in this module's run, by the census's "
                         "build")

    def test_the_census_reads_every_module_the_kernel_loads(self):
        """A writer in the judge, called from a socket op on a client's field, writes a flag as surely as one in
        kernel.py. So the census reads every module in the kernel's directory, and this pins that the modules the kernel
        loads, by file name and to a fixpoint, all live there; the executed refusal is SocketFlagWhitelist."""
        scanned = set(_kernel_modules())
        loads = self.census["loads"]   # each module's files loaded by name, from the census's one walk (_facts)
        loaded, frontier = {"kernel.py"}, {"kernel.py"}
        while frontier:
            new = set().union(*(loads[f] for f in frontier)) - loaded
            self.assertLessEqual(new, scanned, "a module the kernel loads lives outside kernel/, out of this census's sight")
            loaded |= new
            frontier = new
        self.assertEqual(loaded, self.LOADED, "the modules the kernel loads by file name, each read by the census. A "
                         "change that makes the kernel load a new module by file name adds it to LOADED once the "
                         "assertion above holds, that is, once the module lives in kernel/ and the census reads it")
        self.assertEqual({q.split(":", 1)[0] if ":" in q else "kernel.py" for q in self.fns} | {m for m, _ in self.rest},
                         scanned, "the census holds the functions and statements of every module of the kernel's directory")

    def test_the_functions_that_name_the_flags_store_are_pinned_by_role(self):
        """Each namer's role, read from where it sends the store's path (_store_flow, with every mention of a path
        helper as a seed; _derive_namers): a reader, a writer, or a path helper, and the path, or an object that holds
        it, kept where another function can read it refused under every role, as a key of a container too, but at the
        sites KEYED classes. The reach of _store_flow itself is pinned over synthetic source in StoreFlowReach."""
        self.assertEqual(self._namers(), set(self.NAMERS),
                         "the functions that name session-flags.json in code or mention a path helper. A new one reds here "
                         "whatever it does with the file: class it in NAMERS, a reader handing the path only to READS, a "
                         "path helper returning it, or a writer, a setter whose doors must ask _lane_flag_refusal and "
                         "refuse threadMail by execution (SocketFlagWhitelist)")
        helpers = self.census["helpers"]
        self.assertEqual(["%s:%d" % (m, getattr(st, "lineno", 0)) for m, st in self.rest
                          if _unit_names_the_store(self._facts_of(st), helpers)], [],
                         "no module-level statement, in any module of the kernel's directory, names the store or mentions "
                         "a path helper: a constant there would let a function reach the file without naming it, out of "
                         "this census's sight")
        for q, role in sorted(self.NAMERS.items()):
            flow = self.census["flows"][q]
            self.assertNotIn(_PATH_STORED, flow, "%s keeps the store's path, or a def, lambda or class that holds it, "
                             "where another function can read it (a subscript or attribute assigned it, whatever its root, "
                             "a name it declares global, or a method call handed it, such as .append, a decorator among "
                             "them), line %s, out of this census's sight: tracing it would need every reader of what keeps "
                             "it. Hand the path back by return instead, a path helper (role \"path\"), whose callers are "
                             "traced" % (q, flow.get(_PATH_STORED)))
            outside = {c: ln for c, ln in flow.items() if c not in self.READS and not c.startswith(_PATH_KEYED)}
            if role == "reader":
                self.assertEqual(outside, {}, "%s is pinned a reader but hands the store's path to calls outside READS "
                                 "(a write, until classed; a nested def, lambda or class that holds the path is handed "
                                 "wherever it goes, a decorator or a base included) or returns the path itself, or an "
                                 "object that holds it (a path helper, role \"path\"); a new way to write the store is a "
                                 "new setter" % q)
            elif role == "path":
                self.assertEqual(set(outside), {_PATH_EXIT}, "%s is pinned a path helper: it returns or yields the "
                                 "store's path, or an object that holds it, and hands it to nothing outside READS, its "
                                 "decorators included; a call outside READS makes it a writer" % q)
            else:
                self.assertEqual(role, "writer", "%s: a role is reader, path or writer" % q)
                self.assertEqual(set(outside), {"_write_state_json", "_flags_written"},
                                 "%s writes the store through the one write door and runs its clean-write hook" % q)
        keyed = {(q, c[len(_PATH_KEYED):]): ln for q in self.NAMERS for c, ln in self.census["flows"][q].items()
                 if c.startswith(_PATH_KEYED)}
        self.assertEqual(set(keyed), self.KEYED, "the sites that keep the store's path as a key of a container, as "
                         "(function, the container), by line %s: whoever iterates the container reads the path, out of "
                         "this census's sight. Hand the path back by return instead, or, for a cache read only by lookup, "
                         "class the site in KEYED after reading every use of it" % keyed)

    def test_each_name_a_read_spells_is_resolved_by_its_binding(self):
        """READS and _PATH_STOPS name a call by its spelling, and for a bare name and for the module at the root of a
        dotted one the census resolves the spelling by its binding (_misbound) against the one it was read with
        (_READ_BINDINGS), so each such name has one entry there, and a namer's call of one bound otherwise is spelled
        `<bound NAME>`, which the role check refuses as a call outside READS; this names that cause where it applies.
        A method has no entry: it is read by its name alone, the stated limit whose witnesses are the two cases of
        StoreFlowReach.test_a_method_is_read_by_its_name_alone. The resolution itself is pinned over synthetic source
        in StoreFlowReach (a name the function binds, a name its module binds otherwise)."""
        spelled = {c.split(".", 1)[0] for c in self.READS | _PATH_STOPS if not c.startswith(".")}
        self.assertEqual(set(_READ_BINDINGS), spelled, "each bare name and module root READS and _PATH_STOPS "
                         "spell, and nothing else, has in _READ_BINDINGS the binding it was read against: a read "
                         "added by name adds its binding with it")
        rebound = {q: sorted(c for c in flow if c.startswith("<bound ")) for q, flow in self.census["flows"].items()}
        self.assertEqual({q: c for q, c in rebound.items() if c}, {}, "no namer calls a read's name that it or its "
                         "module binds otherwise than the read was read against (_misbound); such a call is no read")

    def test_the_setters_of_the_flags_store_are_the_two_the_doors_call(self):
        by_write, by_hook, by_flow = self._writers()
        self.assertEqual(by_write, self.WRITERS, "the functions that write session-flags.json; a new one is a new "
                         "setter every door below must be re-derived against")
        self.assertEqual(by_hook, self.WRITERS, "the functions that run the store's clean-write hook agree")
        self.assertEqual(by_flow, self.WRITERS, "the functions that hand the store's path to anything but a read agree, "
                         "however the write is spelled (open(), os.replace, a helper); the executed refusal is "
                         "SocketFlagWhitelist")

    def test_the_doors_that_write_a_session_flag_are_the_socket_op_and_the_route(self):
        callers = self._callers()
        self.assertEqual(callers, {"Handler._dispatch_ws", "_state_write_route"},
                         "the functions that call a setter of session-flags.json. A new one is a new way for a client to "
                         "write a flag: route it through _lane_flag_refusal, prove it refuses threadMail by execution "
                         "(SocketFlagWhitelist is the model), and add it here")
        shorts = self._shorts()
        self.assertEqual(["%s:%d" % (m, getattr(st, "lineno", 0)) for m, st in self.rest
                          if self._facts_of(st).names.keys() & shorts], [],
                         "no module-level table hands a setter on")
        doors = {}
        for q in callers:
            named = _doors_naming(self._door_walk_of(q), shorts)
            self.assertEqual(sum(len(v) for v in named.values()), len(_mentions(self.fns[q], shorts)),
                             "%s: every mention of a setter is keyed to a door (_door_walk walks the whole def)" % q)
            doors.update(named)
        population = set().union(*doors)
        self.assertEqual(population, self.DOORS,
                         "the doors whose arm mentions a setter of session-flags.json (a call by name, or the setter "
                         "bound to a local, picked from a table, handed on, named by a string): the setSessionFlag socket "
                         "op and POST /flag. "
                         "A new door reds here until it applies the one whitelist (_lane_flag_refusal) and an executed "
                         "test proves its refusal, as SocketFlagWhitelist does for the socket op")

    def test_every_road_from_a_request_to_a_setter_is_pinned(self):
        """A door function is reached by the functions that hand it a client's input, and a new one is a new way in
        that adds no door of its own: a socket op that forwards to _state_write_route("/flag", ...) writes a flag
        through the route's arm, and so does a second POST path handed to it. So the roads are derived upward from
        the setters by mention and pinned whole, with the count of mentions on each (ROADS); do_POST's one arm onto
        _state_write_route is pinned as ROUTE_ARMS, handing the request's own path, so only POST /flag reaches the
        /flag arm. Read from the source, so it guards the roads, not the behaviour; the executed refusals are
        SocketFlagWhitelist (socket op) and FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (route)."""
        roads = self._roads()
        self.assertEqual(roads, self.ROADS,
                         "every road from a request to a setter of session-flags.json, with its mentions. A new function "
                         "on one, or a new mention on a pinned one, is a new way for a client to reach a flag write: "
                         "route it through a door that asks _lane_flag_refusal, prove it refuses threadMail by execution "
                         "(SocketFlagWhitelist is the model), and add it here")
        on_road = {_short(t) for road in roads for t in road}
        self.assertEqual(["%s:%d" % (m, getattr(st, "lineno", 0)) for m, st in self.rest
                          if self._facts_of(st).names.keys() & on_road], [],
                         "no module-level or class-level statement mentions a function on these roads: a table there "
                         "would hand one on out of this walk's sight")
        post = self.fns["Handler.do_POST"]
        arms = _doors_naming(_door_walk(post, "Handler.do_POST"), {"_state_write_route"})
        self.assertEqual(set(arms), self.ROUTE_ARMS,
                         "do_POST hands _state_write_route the request from one arm, for /flag, /views and /order; the "
                         "route's executed refusal is FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it")
        handed = [n.args[0] if n.args else None for n in ast.walk(post)
                  if isinstance(n, ast.Call) and _callee(n) == "_state_write_route"]
        self.assertEqual([ast.unparse(a) if a is not None else None for a in handed], ["u.path"],
                         "do_POST calls _state_write_route once, by name, handing it the request's own path, so only a "
                         "POST to /flag reaches the route function's /flag arm")

    def test_every_door_asks_the_one_predicate_before_its_setter(self):
        shorts = self._shorts()
        for q in self._callers():
            writes = _doors_naming(self._door_walk_of(q), shorts)
            asks = _doors_reaching(self._door_walk_of(q), {"_lane_flag_refusal"})
            for door, lines in writes.items():
                self.assertIn(door, asks, "%s: the %s arm mentions a setter without asking _lane_flag_refusal; the executed "
                              "proof that it refuses an unlisted name is SocketFlagWhitelist (socket op) and "
                              "FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (route)"
                              % (q, sorted(door)))
                self.assertLess(min(asks[door]), min(lines), "%s %s: the predicate is asked before the first setter mention"
                                % (q, sorted(door)))

    def test_the_predicates_answer_gates_every_setter(self):
        """Asking is not refusing: the answer has to stop the write. In each door the ask is the whole value of an
        assignment to one name (`err = _lane_flag_refusal(flag)`); the very next statement is `if <that name>:`, with no
        else, whose body ends in a return; and every setter call sits in a statement after that `if` in the same block,
        so a setter call runs only once the answer has let the request pass. An ask made conditional on a client's field
        (`... if msg.get("strict", True) else None`), a gate that tests more than the answer, the answer rebound before
        its gate, a gate nested under another condition, or a refusal that falls through all red here. It reads the
        order of the statements, not which name reaches the setter: that is
        test_every_setter_writes_the_name_its_door_asked_about's rule, whose limits the class docstring states (an alias
        of the frame that rewrites the name after the gate, the fourth re-verify's V4a, is outside both, since a
        text-keyed guard follows only the names the source spells). Read from the source, so it guards the arm's
        shape; the executed refusal is SocketFlagWhitelist (socket op) and
        FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (route)."""
        shorts = self._shorts()
        checked = set()
        for q in sorted(self._callers()):
            fn = self.fns[q]
            blocks = [getattr(n, f) for n in ast.walk(fn) for f in ("body", "orelse", "finalbody")
                      if isinstance(getattr(n, f, None), list)]
            by_door = {}
            for door, node in self._door_walk_of(q):
                by_door.setdefault(door, []).append(node)
            for door, nodes in by_door.items():
                sets = [n for n in nodes if isinstance(n, ast.Call) and _callee(n) in shorts]
                if not sets:
                    continue
                where = "%s %s" % (q, sorted(door))
                asks = [n for n in nodes if isinstance(n, ast.Call) and _callee(n) == "_lane_flag_refusal"]
                self.assertEqual(len(asks), 1, "%s: one ask of the predicate" % where)
                held = [(b, i) for b in blocks for i, st in enumerate(b) if isinstance(st, ast.Assign) and st.value is asks[0]]
                self.assertEqual(len(held), 1, "%s line %d: the ask is the whole value of an assignment, so nothing decides "
                                 "whether it is made" % (where, asks[0].lineno))
                block, i = held[0]
                targets = block[i].targets
                self.assertTrue(len(targets) == 1 and isinstance(targets[0], ast.Name),
                                "%s line %d: the answer is bound to one name" % (where, block[i].lineno))
                answer = targets[0].id
                gate = block[i + 1] if i + 1 < len(block) else None
                self.assertTrue(
                    isinstance(gate, ast.If) and isinstance(gate.test, ast.Name) and gate.test.id == answer
                    and not gate.orelse and isinstance(gate.body[-1], ast.Return),
                    "%s line %d: the statement after the ask is `if %s:` with no else, ending in a return, got %s"
                    % (where, block[i].lineno, answer, ast.unparse(gate).splitlines()[0] if gate is not None else None))
                after = {id(n) for st in block[i + 2:] for n in ast.walk(st)}
                self.assertEqual([c.lineno for c in sets if id(c) not in after], [],
                                 "%s: setter calls not in a statement after the gate, in the gate's own block" % where)
                checked.add(door)
        self.assertEqual(checked, {frozenset({d}) for d in self.DOORS}, "both doors were read")

    def test_every_setter_writes_the_name_its_door_asked_about(self):
        """Asking the predicate proves nothing unless the setter writes the name it was asked about. What this reads,
        in each door, all as source text: one ask, of one expression; a setter mentioned only as the callee of a call by
        name, since the rules below read calls and a setter bound to a local or picked from a table writes a name they
        cannot see; each setter called once (SETTER_CALLS); _set_session_flag's flag argument, which must be that same
        expression (str() of it counts as it); _set_notify_session, which writes the `notify` key, only under an `if`
        that compares that expression with "notify", a listed name; and, between the ask and a setter, no statement
        that rebinds the expression's own root name (`msg` for msg["flag"]), writes through it, or hands it to a call
        that may change it. What it does NOT read: an alias of the frame (`fr = msg`, through which the name can be
        rewritten after the gate: the fourth re-verify's V4a), a name built from pieces, and the setters' bodies and any
        parameter beyond the flag argument (what a setter writes from what it is handed; the parameters themselves are
        pinned by test_each_setter_takes_and_is_handed_exactly_its_pinned_parameters). The reason: this is a text-keyed
        guard, which follows only the names the source spells; the behaviour is executed by SocketFlagWhitelist
        (test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing,
        test_every_listed_name_is_accepted_on_the_socket_and_lands, test_a_real_socket_to_the_served_handler_is_refused_the_same_way)
        and, for the route, FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it, within the limit the
        class docstring states."""
        setters, shorts = self._setters(), self._shorts()
        self.assertEqual(set(self.SETTER_CALLS), setters, "every setter has a rule below")
        self.assertIn("notify", km._LANE_FLAGS)
        flag_at = list(inspect.signature(km._set_session_flag).parameters).index("flag")
        mutators = {"update", "setdefault", "pop", "popitem", "clear", "__setitem__", "__delitem__"}
        checked = set()
        for q in sorted(self._callers()):
            fn = self.fns[q]
            parents = {id(c): p for p in ast.walk(fn) for c in ast.iter_child_nodes(p)}   # a side table: the tree is read-only
            by_door = {}
            for door, node in self._door_walk_of(q):
                by_door.setdefault(door, []).append(node)
            for door, nodes in by_door.items():
                calls = [n for n in nodes if isinstance(n, ast.Call)]
                sets = [c for c in calls if _callee(c) in shorts]
                named = [n for n in nodes if _mentioned(n) & shorts]
                if not named:
                    continue
                where = "%s %s" % (q, sorted(door))
                self.assertEqual(sorted(n.lineno for n in named if all(n is not c.func for c in sets)), [],
                                 "%s: lines where a setter is mentioned other than as the callee of a call by name (bound "
                                 "to a local, picked from a table, handed on, named by a string), so the rules below cannot "
                                 "read what it writes"
                                 % where)
                asks = [c for c in calls if _callee(c) == "_lane_flag_refusal"]
                self.assertEqual(len(asks), 1, "%s: one ask of the predicate, so there is one name the setters must write" % where)
                ask = asks[0]
                self.assertEqual((len(ask.args), ask.keywords), (1, []), "%s: the predicate is asked about one name" % where)
                asked = _unwrap_str(ask.args[0])
                self.assertEqual(Counter(_callee(c) for c in sets), Counter(self.SETTER_CALLS),
                                 "%s: each setter called once; a second call is a second write the ask may not cover" % where)
                for c in sets:
                    self.assertLess((ask.lineno, ask.col_offset), (c.lineno, c.col_offset), "%s: asked before it writes" % where)
                    if _callee(c) == "_set_session_flag":
                        self.assertFalse(any(isinstance(a, ast.Starred) for a in c.args) or any(k.arg is None for k in c.keywords),
                                         "%s line %d: a setter call whose flag this cannot read" % (where, c.lineno))
                        given = c.args[flag_at] if len(c.args) > flag_at else next(
                            (k.value for k in c.keywords if k.arg == "flag"), None)
                        self.assertIsNotNone(given, "%s line %d: the setter's flag argument" % (where, c.lineno))
                        self.assertEqual(ast.dump(_unwrap_str(given)), ast.dump(asked),
                                         "%s line %d: _set_session_flag writes %s, but the predicate was asked about %s"
                                         % (where, c.lineno, ast.unparse(given), ast.unparse(asked)))
                    else:
                        node, guard = c, None
                        while id(node) in parents and guard is None:
                            up = parents[id(node)]
                            if isinstance(up, ast.If) and node in up.body:
                                guard = up
                            node = up
                        test = guard.test if guard is not None else None
                        self.assertTrue(
                            isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                            and {ast.dump(_unwrap_str(test.left)), ast.dump(_unwrap_str(test.comparators[0]))}
                            == {ast.dump(asked), ast.dump(ast.Constant("notify"))},
                            "%s line %d: _set_notify_session writes the notify key, so it sits under `if %s == \"notify\"`, "
                            "got %s" % (where, c.lineno, ast.unparse(asked), ast.unparse(test) if test is not None else None))
                last = max((c.lineno, c.col_offset) for c in sets)
                root = _root_name(asked)
                bare = isinstance(asked, ast.Name)
                for n in nodes:
                    pos = (getattr(n, "lineno", 0), getattr(n, "col_offset", 0))
                    if not ((ask.lineno, ask.col_offset) < pos <= last):
                        continue
                    rebinds = (isinstance(n, ast.Name) and n.id == root and isinstance(n.ctx, (ast.Store, ast.Del))) or (
                        isinstance(n, (ast.Subscript, ast.Attribute)) and isinstance(n.ctx, (ast.Store, ast.Del))
                        and _root_name(n) == root)
                    if not bare and isinstance(n, ast.Call):
                        rebinds = rebinds or (isinstance(n.func, ast.Attribute) and n.func.attr in mutators
                                              and _root_name(n.func.value) == root) or any(
                            isinstance(a, ast.Name) and a.id == root for a in list(n.args) + [k.value for k in n.keywords])
                    self.assertFalse(rebinds, "%s line %d: `%s` rebinds %s, or hands it to a call that may change it, between "
                                     "the ask and the setter, so the setter may write a name the predicate never saw"
                                     % (where, pos[0], ast.unparse(n), root))
                checked.add(door)
        self.assertEqual(checked, {frozenset({d}) for d in self.DOORS}, "both doors were read")

    def test_each_setter_takes_and_is_handed_exactly_its_pinned_parameters(self):
        """What this reads: each setter's parameter list, from the loaded function (inspect.signature, so a default, an
        annotation, *args or **kwargs shows; the module is loaded from bin/romp-kernel, a link to the kernel/kernel.py
        the census parses), against SIGNATURES, `(sid, flag, value)` and `(sid, value)`; and, from the source, every
        setter call in each door, which must bind exactly those parameters, positionally or by keyword, each once, with
        no * or ** spread. A setter given a second name parameter, or a door handing it one
        (`_set_session_flag(sid, flag, value, also=msg.get("also"))`, the fourth re-verify's V4b), reds here. What
        it does NOT read: the setters' bodies, so what a setter writes from the parameters it has is outside it, and an
        alias of the frame or a name built from pieces in the arguments (the class docstring states both limits). The
        reason: this is a text-keyed guard over the parameter lists and the calls, and a write traced through a body's
        logic is past what one can follow; the behaviour is executed by SocketFlagWhitelist
        (test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing,
        test_every_listed_name_is_accepted_on_the_socket_and_lands, test_a_real_socket_to_the_served_handler_is_refused_the_same_way)."""
        setters, shorts = self._setters(), self._shorts()
        self.assertEqual(set(self.SIGNATURES), setters, "every setter has a pinned signature")
        for name, params in sorted(self.SIGNATURES.items()):
            self.assertEqual(str(inspect.signature(getattr(km, name))), "(%s)" % ", ".join(params),
                             "%s's parameters: a new one is a new input the doors' checks do not read" % name)
        checked = set()
        for q in sorted(self._callers()):
            by_door = {}
            for door, node in self._door_walk_of(q):
                if isinstance(node, ast.Call) and _callee(node) in shorts:
                    by_door.setdefault(door, []).append(node)
            for door, calls in by_door.items():
                for c in calls:
                    params = self.SIGNATURES[_callee(c)]
                    spread = any(isinstance(a, ast.Starred) for a in c.args) or any(k.arg is None for k in c.keywords)
                    bound = list(params[:len(c.args)]) + ["<extra positional>"] * max(0, len(c.args) - len(params)) + [
                        k.arg for k in c.keywords if k.arg is not None]
                    self.assertTrue(not spread and Counter(bound) == Counter(params),
                                    "%s %s line %d: `%s` does not pass exactly %s's parameters (%s), each once, with no * "
                                    "or ** spread" % (q, sorted(door), c.lineno, ast.unparse(c), _callee(c), ", ".join(params)))
                checked.add(door)
        self.assertEqual(checked, {frozenset({d}) for d in self.DOORS}, "both doors were read")

    def test_the_list_is_a_whitelist_in_one_place(self):
        # a membership test against _LANE_FLAGS outside the predicate is a second whitelist that can drift from it: a
        # comparison, anywhere in a def or a statement, one of whose operators is `in` or `not in` and one of whose
        # comparators is the name _LANE_FLAGS (read by the census's one walk, _facts' lane)
        where = {q for q, fn in list(self.fns.items()) + [("<module %s>" % m, st) for m, st in self.rest]
                 if self._facts_of(fn).lane}
        self.assertEqual(where, {"_lane_flag_refusal"}, "the one predicate both doors ask; the executed proof is "
                         "SocketFlagWhitelist.test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing")



class StoreFlowReach(unittest.TestCase):
    """_store_flow's seeds, exits, stops and kept paths, and the namers they grow, over synthetic source: a snippet
    parsed here and its defs handed to the census's functions; no file written, no kernel copy (the reviewer's ruling
    on round 1 of fork PR #909, extra6-1, fresh-1 and fresh-2). FlagWriterPopulation reads what they make of the
    kernel's own tree; these pin how far they reach, so a writer spelled a new way reds there, within the stated limits
    FlagWriterPopulation's docstring names (a method read by its name alone among them). The verdicts are read as
    the role check reads them, what a function sends the path to outside FlagWriterPopulation.READS."""

    MODULES = frozenset({"os", "json"})
    maxDiff = None   # a red names every case that differs, not the first 640 characters of the diff

    def _fn(self, src, name):
        return next(n for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and n.name == name)

    def _outside(self, src, name, helpers=None):
        """What `name`'s flow sends the path to outside READS, as the role check reads it; a reader has none."""
        fn = self._fn(src, name)
        flow = _store_flow(fn, self.MODULES) if helpers is None else _store_flow(fn, self.MODULES, helpers)
        return {c: ln for c, ln in flow.items() if c not in FlagWriterPopulation.READS}

    def test_a_positional_parameters_default_hands_its_parameter_the_path(self):
        src = 'def f(sid, path=jd.STATE / "session-flags.json"):\n    with open(path, "w") as out:\n        out.write(sid)\n'
        self.assertEqual(self._outside(src, "f").get("open"), [2], "open() is handed the path a positional parameter's "
                         "default names, so the function is a writer, not a reader")

    def test_a_positional_only_parameters_default_hands_its_parameter_the_path(self):
        # the defaults cover the positional-only parameters too: slicing args.args by the defaults' count misses this
        src = 'def f(path=jd.STATE / "session-flags.json", /):\n    open(path, "w").write("{}")\n'
        self.assertEqual(self._outside(src, "f").get("open"), [2], "open() is handed the path a positional-only "
                         "parameter's default names")

    def test_a_keyword_only_parameters_default_hands_its_parameter_the_path(self):
        src = 'def f(sid, *, path=jd.STATE / "session-flags.json"):\n    open(path, "w").write(sid)\n'
        self.assertEqual(self._outside(src, "f").get("open"), [2], "open() is handed the path a keyword-only "
                         "parameter's default names")

    def test_a_nested_lambdas_default_hands_its_parameter_the_path(self):
        src = 'def f(sid):\n    poke = lambda name="session-flags.json": open(jd.STATE / name, "w")\n    poke().write(sid)\n'
        self.assertEqual(self._outside(src, "f").get("open"), [2], "open() is handed the path the default of a lambda "
                         "inside the def names")

    def test_a_helper_that_returns_the_stores_path_is_no_reader(self):
        """Read through the role check's verdict, so that without the exit rule the red is the helper accepted as a
        reader: then a writer through it would name no store and pass every setter derivation."""
        src = 'def _flags_path():\n    return jd.STATE / "session-flags.json"\n'
        outside = self._outside(src, "_flags_path")
        self.assertNotEqual(outside, {}, "a helper returning the store's path passes the role check as a reader")
        self.assertEqual(outside, {_PATH_EXIT: [2]}, "the path leaves by the return and by nothing else: the path role")

    def test_every_path_valued_spelling_of_a_return_or_yield_is_an_exit(self):
        """The path goes through every expression but a stop (_path_valued), so each spelling below hands it back. The
        f-string of a bound name is the only case that reaches the path through the f-string's formatted value alone."""
        cases = [
            ("a name bound from the path, through str()", 'def h():\n    p = jd.STATE / "session-flags.json"\n'
                                                          '    return str(p)\n', 3),
            ("os.path.join, yielded", 'def h():\n    yield os.path.join(jd.STATE, "session-flags.json")\n', 2),
            ("an f-string", 'def h():\n    return f"{jd.STATE}/session-flags.json"\n', 2),
            ("an f-string of a name bound from the path", 'def h():\n    p = jd.STATE / "session-flags.json"\n'
                                                          '    return f"{p}"\n', 3),
            ("an if-else", 'def h(ok):\n    return (jd.STATE / "session-flags.json") if ok else None\n', 2),
            ("a list", 'def h():\n    return [jd.STATE / "session-flags.json"]\n', 2),
            ("a tuple, yielded from", 'def h():\n    yield from (jd.STATE / "session-flags.json",)\n', 2),
            ("a parameter's default", 'def h(p=jd.STATE / "session-flags.json"):\n    return p\n', 2),
            ("Path() and os.fspath()", 'def h():\n    return os.fspath(Path(jd.STATE, "session-flags.json"))\n', 2),
            ("a lambda's body", 'def h():\n    return sorted([1], key=lambda x: jd.STATE / "session-flags.json")\n', 2),
            ("an or", 'def h(alt=None):\n    return alt or jd.STATE / "session-flags.json"\n', 2),
            ("a walrus", 'def h():\n    return (p := jd.STATE / "session-flags.json")\n', 2),
            ("a subscript of a list", 'def h():\n    return [jd.STATE / "session-flags.json"][0]\n', 2),
            ("a dict's value", 'def h():\n    return {"p": jd.STATE / "session-flags.json"}\n', 2),
            ("a dict's key", 'def h():\n    return {jd.STATE / "session-flags.json": 1}\n', 2),
            ("a set", 'def h():\n    return {jd.STATE / "session-flags.json"}\n', 2),
            ("a .get's default", 'def h():\n    return PATHS.get("flags", jd.STATE / "session-flags.json")\n', 2),
            ("a call's keyword", 'def h():\n    return dict(p=jd.STATE / "session-flags.json")\n', 2),
            ("a starred list", 'def h():\n    return [*[jd.STATE / "session-flags.json"]]\n', 2),
        ]
        got = {what: self._outside(src, "h") for what, src, line in cases}
        self.assertEqual(got, {what: {_PATH_EXIT: [line]} for what, src, line in cases},
                         "each hands the path itself back to its caller, and to no call outside READS")

    def test_a_call_outside_the_stops_hands_the_path_back(self):
        """A call the rule does not list as a stop hands back its receiver and its arguments, whatever it is: a method
        of the path, a constructor, an attribute of what it returns. Read on the exit alone, since these calls are
        outside READS as well (a writer until classed)."""
        cases = [
            ("a method of the path", 'def h():\n    return (jd.STATE / "session-flags.json").with_suffix(".json")\n', 2),
            ("a constructor's keyword", 'def h():\n    return SimpleNamespace(p=jd.STATE / "session-flags.json")\n', 2),
            ("an attribute of a call's result", 'def h():\n    return SimpleNamespace(p=jd.STATE / "session-flags.json").p\n',
             2),
        ]
        got = {what: self._outside(src, "h").get(_PATH_EXIT) for what, src, line in cases}
        self.assertEqual(got, {what: [line] for what, src, line in cases}, "each hands the path back to its caller")

    def test_a_reader_that_returns_what_it_parsed_has_no_path_exit(self):
        """A control, green with the exit rule and without it, by design: the _session_flags shape returns a value
        read from the file, which carries the path in _store_flow's over-approximate sense but is not the path. Keyed
        on carrying, the exit rule would make seven of the nine readers path helpers."""
        src = ('def _session_flags(sid):\n    p = jd.STATE / "session-flags.json"\n'
               '    data = json.loads(p.read_text())\n    return data.get(sid, {})\n')
        self.assertEqual(self._outside(src, "_session_flags"), {}, "a reader of the store: every call it hands the path "
                         "to is in READS, and it returns what it read, not the path")

    def test_the_path_stops_at_a_read_a_comparison_a_test_and_a_key(self):
        """Controls, one per stop, each red when its stop is dropped: the readers hand back what they read, a
        comparison, or a value looked up by the path, never the path. Each call in _PATH_STOPS has its own case."""
        p = '    p = jd.STATE / "session-flags.json"\n'
        cases = [
            ("the path as a .get's key", 'def r():\n' + p + '    hit = CACHE.get(str(p))\n    return dict(hit[1])\n'),
            ("the path as a subscript's index", 'def r():\n' + p + '    return CACHE[str(p)]\n'),
            ("a comparison", 'def r(q):\n    return q == jd.STATE / "session-flags.json"\n'),
            ("an if-else's test", 'def r():\n' + p + '    return 1 if p else 0\n'),
            ("a stat", 'def r():\n' + p + '    return p.stat().st_size\n'),
            ("os.stat", 'def r():\n' + p + '    return os.stat(p).st_mtime\n'),
            ("the strict reader", 'def r():\n' + p + '    return _read_state_json(p, expect=dict)\n'),
            ("a stat key", 'def r():\n' + p + '    return _stat_key(p)\n'),
            ("a file identity", 'def r():\n' + p + '    return _chat_ident(p)\n'),
            ("a parse", 'def r():\n' + p + '    return json.loads(p.read_text())\n'),
        ]
        got = {what: self._outside(src, "r") for what, src in cases}
        self.assertEqual(got, {what: {} for what, src in cases}, "each hands back a value read from the file, a bool or a "
                         "value looked up by the path, not the path, and hands the path only to READS")

    def test_a_match_capture_binds_the_path(self):
        src = 'def f(sid):\n    match jd.STATE / "session-flags.json":\n        case p:\n            open(p, "w").write(sid)\n'
        self.assertEqual(self._outside(src, "f").get("open"), [4], "open() is handed the path a match statement captured")

    def test_a_path_helpers_call_is_a_seed_in_its_caller(self):
        helpers = frozenset({"_flags_path"})
        w = 'def w(sid):\n    open(_flags_path(), "w").write(sid)\n'
        self.assertEqual(self._outside(w, "w", helpers).get("open"), [2], "open() is handed the helper's result")
        h = 'def _flags_file():\n    return os.fspath(_flags_path())\n'
        self.assertEqual(self._outside(h, "_flags_file", helpers), {_PATH_EXIT: [2]},
                         "returning a helper's result, through a call the path passes through, makes a helper")

    def test_a_path_helper_reached_without_a_call_by_its_name_is_a_seed_too(self):
        """Every mention of a helper seeds its caller's flow (_mentioned): a reference bound to a local, an import of it
        under another name, and its name in a string reach the helper as a call does."""
        helpers = frozenset({"_flags_path"})
        cases = [
            ("a reference bound to a local", 'def w(sid):\n    get = _flags_path\n    open(get(), "w").write(sid)\n', [3]),
            ("an import alias", 'def w(sid):\n    from kernel import _flags_path as fp\n    open(fp(), "w").write(sid)\n',
             [3]),
            ("its name in a string", 'def w(sid):\n    open(globals()["_flags_path"](), "w").write(sid)\n', [2]),
        ]
        got = {what: self._outside(src, "w", helpers).get("open") for what, src, lines in cases}
        self.assertEqual(got, {what: lines for what, src, lines in cases}, "open() is handed the helper's result")

    def test_a_caller_of_a_path_helper_names_the_store_and_helpers_chain(self):
        src = ('def _flags_path():\n    return jd.STATE / "session-flags.json"\n'
               'def _flags_file():\n    return str(_flags_path())\n'
               'def w(sid):\n    open(_flags_file(), "w").write(sid)\n'
               'def r():\n    return json.loads(jd.STATE.joinpath("views.json").read_text())\n'
               'def w2(sid):\n    get = _flags_file\n    open(get(), "w").write(sid)\n')
        fns = {n.name: n for n in ast.parse(src).body}
        namers, flows, helpers = _derive_namers(fns, {q: _facts(fn) for q, fn in fns.items()}, self.MODULES)
        self.assertEqual((namers, helpers), ({"_flags_path", "_flags_file", "w", "w2"}, {"_flags_path", "_flags_file"}),
                         "the helper, the helper that returns its result, and the writers through that one, called or "
                         "bound to a local, all name the store; the function that names another file does not")
        self.assertEqual((flows["w"].get("open"), flows["w2"].get("open")), ([6], [11]),
                         "each writer's open() is handed the path, so each is a setter by flow")

    def test_the_path_kept_where_another_function_can_read_it_is_refused(self):
        """_PATH_STORED, by line: the path assigned to a subscript or attribute whatever its root, to a name declared
        global, or handed to a method of a value other than .get. The controls keep it in a plain local, look it up,
        hand it to a module's function, or store a value read from the file."""
        cases = [
            ("a name declared global", 'def f():\n    global P\n    P = jd.STATE / "session-flags.json"\n', [3]),
            ("a subscript of a module-level name", 'def f():\n    PATHS["flags"] = jd.STATE / "session-flags.json"\n', [2]),
            ("an attribute of a module-level name", 'def f():\n    jd.FLAGS = jd.STATE / "session-flags.json"\n', [2]),
            ("a subscript of a local", 'def f():\n    paths = {}\n    paths["flags"] = jd.STATE / "session-flags.json"\n'
                                       '    return len(paths)\n', [3]),
            ("an attribute of self", 'def f(self):\n    self.p = jd.STATE / "session-flags.json"\n', [2]),
            ("a subscript under a call", 'def f():\n    globals()["P"] = jd.STATE / "session-flags.json"\n', [2]),
            ("an append onto a module-level list", 'def f():\n    PATHS.append(jd.STATE / "session-flags.json")\n', [2]),
            ("an append onto a local list", 'def f():\n    out = []\n    out.append(jd.STATE / "session-flags.json")\n'
                                            '    return len(out)\n', [3]),
            ("an augmented assignment to a parameter", 'def f(out):\n    out += [jd.STATE / "session-flags.json"]\n', [2]),
            ("an augmented assignment to a global", 'def f():\n    global OUT\n    OUT += [jd.STATE / "session-flags.json"]\n',
             [3]),
            ("a plain local (not one)", 'def f():\n    p = jd.STATE / "session-flags.json"\n    return p.stat().st_size\n',
             None),
            ("a .get keyed by the path (not one)", 'def f():\n    return CACHE.get(str(jd.STATE / "session-flags.json"))\n',
             None),
            ("a module's function handed it (not one)", 'def f():\n    return os.stat(jd.STATE / "session-flags.json")\n',
             None),
            ("a value read from the file stored (not one)",
             'def f():\n    CACHE["k"] = os.stat(jd.STATE / "session-flags.json").st_size\n', None),
        ]
        got = {what: _store_flow(self._fn(src, "f"), self.MODULES).get(_PATH_STORED) for what, src, lines in cases}
        self.assertEqual(got, {what: lines for what, src, lines in cases}, "the keeps the role check refuses, by line")

    def test_the_path_kept_as_a_key_is_keyed_by_its_container(self):
        """_PATH_KEYED plus the subscript's root, by line: the path stored as an index, which whoever iterates the
        container reads back. The role check refuses it but at a site FlagWriterPopulation.KEYED classes. The controls
        key by a value read from the file, or look the path up."""
        cases = [
            ("a module-level cache", 'def f():\n    p = jd.STATE / "session-flags.json"\n    CACHE[str(p)] = 1\n',
             {"CACHE": [3]}),
            ("a local dict, returned", 'def f():\n    seen = {}\n    seen[jd.STATE / "session-flags.json"] = 1\n'
                                       '    return seen\n', {"seen": [3]}),
            ("an augmented store", 'def f():\n    COUNTS[jd.STATE / "session-flags.json"] += 1\n', {"COUNTS": [2]}),
            ("a key under a call", 'def f():\n    globals()[str(jd.STATE / "session-flags.json")] = 1\n', {"<Call>": [2]}),
            ("a key read from the file (not one)",
             'def f():\n    CACHE[os.stat(jd.STATE / "session-flags.json").st_mtime] = 1\n', {}),
            ("a lookup by the path (not one)", 'def f():\n    return CACHE[str(jd.STATE / "session-flags.json")]\n', {}),
            ("the path unpacked beside a name", 'def f():\n    k, p = "flags", jd.STATE / "session-flags.json"\n'
                                                '    CACHE[p] = 1\n', {"CACHE": [3]}),
            ("a name unpacked beside the path (not one)",
             'def f():\n    for p, k in ((jd.STATE / "session-flags.json", "flags"), (jd.STATE / "views.json", "views")):\n'
             '        SIG[k] = os.stat(p).st_mtime\n', {}),
        ]

        def keyed(src):
            flow = _store_flow(self._fn(src, "f"), self.MODULES)
            return {c[len(_PATH_KEYED):]: ln for c, ln in flow.items() if c.startswith(_PATH_KEYED)}
        got = {what: keyed(src) for what, src, want in cases}
        self.assertEqual(got, {what: want for what, src, want in cases}, "the keys the role check refuses but at a "
                         "site KEYED classes, by container and line")

    def test_a_statement_that_mentions_a_path_helper_names_the_store(self):
        """The one predicate the namers grow by and the module-level check refuses by (_unit_names_the_store): a
        mention of a helper, called or not, or a constant naming the store; a statement with neither is not one."""
        cases = [("a reference at module level", "_GET = _flags_path\n", True),
                 ("a call at module level", "P = _flags_path()\n", True),
                 ("the store's name", 'P = STATE / "session-flags.json"\n', True),
                 ("neither (not one)", 'P = STATE / "views.json"\n', False)]
        got = {what: _unit_names_the_store(_facts(ast.parse(src).body[0]), frozenset({"_flags_path"}))
               for what, src, want in cases}
        self.assertEqual(got, {what: want for what, src, want in cases}, "a unit reaches the store by a name it spells")

    def test_an_import_alias_mentions_the_name_it_imports(self):
        tree = ast.parse("def f():\n    from m import _set_session_flag as w\n    import os.path as osp\n"
                         "    from n import *\n")
        self.assertEqual([_mentioned(a) for a in ast.walk(tree) if isinstance(a, ast.alias)],
                         [{"_set_session_flag"}, {"os", "path"}, set()], "_mentioned: the imported name's parts, never "
                         "the local name it binds, and nothing for a star import")
        names = _facts(tree.body[0]).names
        self.assertEqual({k: names.get(k, 0) for k in ("_set_session_flag", "os", "path", "w", "osp", "*")},
                         {"_set_session_flag": 1, "os": 1, "path": 1, "w": 0, "osp": 0, "*": 0},
                         "_facts counts the same mentions _mentioned reads")

    def test_a_def_lambda_or_class_nested_in_a_function_carries_what_it_holds(self):
        """A nested def, lambda or class holds whatever it mentions (_holds), so its object goes where a value goes:
        a nested def that builds the path is handed to open() through every call of it, and a closure or a class
        holding the path is kept, handed back, or handed to a call, its decorators, bases and metaclass included (each
        is called with it); a return inside the nested scope is its own, and a callback a stop call hands back is not
        read by the stop. One case pins the stated over-approximation (a nested def that only reads the path still
        holds it, so its call counts as the path). The controls hold nothing, or hand the nested def's result to the
        strict reader. Each case reads one key of what the function sends outside READS; a control (key None) reads all
        of it."""
        p = '    p = jd.STATE / "session-flags.json"\n'
        fp = '    def fp():\n        return jd.STATE / "session-flags.json"\n'
        cases = [
            ("a nested def that builds the path, called and opened", 'def f(sid):\n' + fp + '    open(fp(), "w").write(sid)\n',
             "open", [4]),
            ("that nested def's return is its own, not the function's exit",
             'def f(sid):\n' + fp + '    open(fp(), "w").write(sid)\n', _PATH_EXIT, None),
            ("a closure over the path appended to a list", 'def f():\n' + p + '    def g():\n        return p\n'
                                                            '    REG.append(g)\n', _PATH_STORED, [5]),
            ("a lambda over the path appended to a list", 'def f():\n' + p + '    REG.append(lambda: p)\n', _PATH_STORED, [3]),
            ("a nested class whose body binds the path, returned",
             'def f():\n    class K:\n        P = jd.STATE / "session-flags.json"\n    return K\n', _PATH_EXIT, [4]),
            ("a closure over the path, returned", 'def f():\n' + p + '    def g():\n        return p\n    return g\n',
             _PATH_EXIT, [5]),
            ("a closure that only compares the path, handed to a call", 'def f():\n' + p + '    register(lambda q: q == p)\n',
             "register", [3]),
            ("a nested def holding the path in a default, appended",
             'def f():\n    def g(q=jd.STATE / "session-flags.json"):\n        return 1\n    REG.append(g)\n', _PATH_STORED, [4]),
            ("a method of a value decorating a closure over the path",
             'def f():\n' + p + '    @REG.append\n    def g():\n        return p\n', _PATH_STORED, [3]),
            ("a call decorating a closure over the path", 'def f():\n' + p + '    @register("k")\n    def g():\n        return p\n',
             "<Call>", [3]),
            ("the base of a class holding the path", 'def f():\n' + p + '    class K(Base):\n        def get(self):\n'
                                                     '            return p\n', "Base", [3]),
            ("the metaclass of a class holding the path", 'def f():\n' + p + '    class K(metaclass=Meta):\n'
                                                          '        def get(self):\n            return p\n', "Meta", [3]),
            ("a callback returning the path, handed back by a stop call",
             'def f(s):\n' + p + '    return json.loads(s, object_hook=lambda d: p)\n', _PATH_EXIT, [3]),
            ("a nested def that only reads the path: its call still counts as the path (over-approximate)",
             'def f():\n' + p + '    def rd():\n        return json.loads(p.read_text())\n    return rd().get("k")\n',
             _PATH_EXIT, [5]),
            ("a nested def whose path the strict reader reads (not one)", 'def f():\n' + fp + '    return _read_state_json(fp())\n',
             None, None),
            ("a nested def that holds nothing, appended (not one)", 'def f():\n' + p + '    def g():\n        return 1\n'
                                                                    '    REG.append(g)\n    return p.stat().st_size\n',
             None, None),
            ("a decorated nested def that holds nothing (not one)", 'def f():\n' + p + '    @REG.append\n    def g():\n'
                                                                    '        return 1\n    return p.stat().st_size\n',
             None, None),
        ]
        got = {}
        for what, src, key, lines in cases:
            outside = self._outside(src, "f")
            got[what] = outside if key is None else outside.get(key)
        self.assertEqual(got, {what: ({} if key is None else lines) for what, src, key, lines in cases},
                         "each nested scope's object carries what it holds, by line")

    def test_a_path_helpers_own_decorators_are_handed_the_helper(self):
        """A decorator is called with the def it decorates, so a path helper's decorators are handed the path: a method
        of a value keeps it (`@REG.append` stores the helper where a caller reaches it by no name), and any other is a
        call outside READS, a writer until classed. A reader's decorator is handed nothing: its object returns what it
        read, not the path."""
        helper = 'def _flags_path():\n    return jd.STATE / "session-flags.json"\n'
        cases = [
            ("a method of a value", "@REG.append\n" + helper, {_PATH_EXIT: [3], _PATH_STORED: [1]}),
            ("a function", "@register\n" + helper, {_PATH_EXIT: [3], "register": [1]}),
            ("no decorator (the helper alone)", helper, {_PATH_EXIT: [2]}),
        ]
        got = {what: self._outside(src, "_flags_path") for what, src, want in cases}
        self.assertEqual(got, {what: want for what, src, want in cases}, "a path helper's decorators, by line")
        reader = '@register\ndef r():\n    return json.loads((jd.STATE / "session-flags.json").read_text())\n'
        self.assertEqual(self._outside(reader, "r"), {}, "a reader's decorator is handed nothing")

    def test_a_bytes_literal_names_the_store_and_a_function(self):
        """The census reads a name spelled whole in a bytes literal as it reads the str (_text_of): the store's name
        seeds the flow and makes a namer, at module level too, and a function's name is a mention. A bytes constant
        standing as a statement of its own is text about the code, as a docstring is."""
        w = 'def f(sid):\n    open(jd.STATE / b"session-flags.json".decode(), "w").write(sid)\n'
        stmt = self._fn('def f():\n    b"session-flags.json"\n    return 1\n', "f")
        self.assertEqual(self._outside(w, "f").get("open"), [2], "open() is handed the path a bytes literal names")
        self.assertEqual((_facts(self._fn(w, "f")).seeded, _facts(stmt).seeded, len(_store_seeds(stmt)),
                          _unit_names_the_store(_facts(ast.parse('P = b"session-flags.json"\n').body[0]), frozenset())),
                         (True, False, 0, True), "a bytes literal naming the store seeds a def and a module-level "
                         "statement; one standing as a statement does not, in _facts or in _store_seeds")
        call = ast.parse('globals()[b"_set_session_flag".decode()](sid, flag, True)\n')
        self.assertEqual(([_mentioned(n) for n in ast.walk(call) if isinstance(n, ast.Constant) and type(n.value) is bytes],
                          _facts(call.body[0]).names.get("_set_session_flag", 0)),
                         ([{"_set_session_flag"}], 1),
                         "_mentioned and _facts read a function's name in a bytes literal as a mention")

    def test_a_reads_name_the_function_binds_is_not_that_read(self):
        """A call is a read (READS) or a stop (_PATH_STOPS) only where its name, or the module at the root of its
        dotted name, is bound as those were read against (_misbound): a name the function binds anywhere, a parameter,
        a nested def, a lambda, an import, a loop or except target, is its own, so the call is spelled `<bound NAME>`,
        a write until classed, and a stop that is rebound stops nothing. The first three cases are the shapes of three
        writers that passed the whole module while writing threadMail through their socket op (a nested
        `def sorted(q)` that writes q, `str = lambda q: ...`, `Path = shutil.copyfile`). The controls import the very
        binding a read was read against, spell a read's name where nothing is bound (an attribute, a keyword), or are a
        read that calls itself by name (its def binds that name in its module, not in itself). Each case reads one key
        of what the function sends outside READS; a control (key None) reads all of it."""
        s = 'jd.STATE / "session-flags.json"'
        cases = [
            ("a nested def named like a read, writing what it is handed",
             'def f(sid):\n    def sorted(q):\n        with open(q, "w") as fh:\n            fh.write(sid)\n'
             '    sorted(%s)\n' % s, "<bound sorted>", [5]),
            ("a lambda bound to a read's name",
             'def f(sid):\n    str = lambda q: open(q, "w").write(sid)\n    str(%s)\n' % s, "<bound str>", [3]),
            ("a read's name bound to another callable",
             'def f(tmp):\n    Path = shutil.copyfile\n    Path(tmp, %s)\n' % s, "<bound Path>", [3]),
            ("a parameter named like a read", 'def f(sid, sorted=None):\n    sorted(%s)\n' % s, "<bound sorted>", [2]),
            ("an import that binds a read's name to something else",
             'def f(tmp):\n    from shutil import copyfile as Path\n    Path(tmp, %s)\n' % s, "<bound Path>", [3]),
            ("a loop target named like a read", 'def f(ws):\n    for str in ws:\n        str(%s)\n' % s, "<bound str>",
             [3]),
            ("an except target named like a read",
             'def f():\n    try:\n        pass\n    except Exception as isinstance:\n'
             '        isinstance(%s, dict)\n' % s,
             "<bound isinstance>", [5]),
            ("a module's name rebound, so its dotted read is not that module's",
             'def f(w):\n    os = w\n    os.stat(%s)\n' % s, "<bound os>", [3]),
            ("a stop's name rebound: the path it would stop at is handed back",
             'def h():\n    _read_state_json = lambda q, **k: q\n    return _read_state_json(%s)\n' % s,
             _PATH_EXIT, [3]),
            ("a stop's module rebound: the path is handed back",
             'def h(j):\n    json = j\n    return json.loads(%s)\n' % s, _PATH_EXIT, [3]),
            ("the function imports the bindings its reads were read against (not one)",
             'def f():\n    import json\n    from pathlib import Path\n    return json.loads(Path(%s).read_text())\n' % s,
             None, None),
            ("a read's name spelled where nothing is bound, an attribute and a keyword (not one)",
             'def f(o):\n    o.str = sorted\n    return dict(str=1).get(str(%s))\n' % s, None, None),
            ("a read that calls itself by its own name, which its module binds (not one)",
             'def _stat_key(q=None):\n    return _stat_key(%s) if q is None else q.stat()\n' % s, None, None),
        ]
        got = {}
        for what, src, key, lines in cases:
            outside = self._outside(src, ast.parse(src).body[0].name)
            got[what] = outside if key is None else outside.get(key)
        self.assertEqual(got, {what: ({} if key is None else lines) for what, src, key, lines in cases},
                         "a read's name the function binds is spelled <bound NAME>, by line")

    def test_a_reads_name_its_module_binds_otherwise_is_not_that_read(self):
        """A name the function does not bind is resolved in its module's scope (_module_bindings, read by
        _derive_namers from the module's tree): a builtin read's name must be bound nowhere there, a module or an
        imported name only by the import _READ_BINDINGS names, and a kernel read only by its one def or class at
        kernel.py's top level. So a top-level def or import of a read's name, one under an if or as an except
        target, a global declaration in another function, a walrus in a def's default, a star import, a second def
        of a kernel read and a kernel read's name defined in another module each make the namer's call
        `<bound NAME>`. The controls bind exactly what READS was read against, in kernel.py and in a module that
        imports only what it reads."""
        s = 'jd.STATE / "session-flags.json"'
        w = '    open(q, "w").write("{}")\n'
        cases = [
            ("a top-level def named like a builtin read", "kernel.py",
             'def sorted(q):\n' + w + 'def f():\n    sorted(%s)\n' % s, "<bound sorted>", [4]),
            ("a top-level import binding a read's name to something else", "kernel.py",
             'from shutil import copyfile as Path\ndef f(tmp):\n    Path(tmp, %s)\n' % s, "<bound Path>", [3]),
            ("an assignment under a top-level if", "kernel.py",
             'if True:\n    str = print\ndef f():\n    str(%s)\n' % s, "<bound str>", [4]),
            ("an except target at the top level", "kernel.py",
             'try:\n    pass\nexcept ImportError as dict:\n    pass\ndef f():\n    dict(p=%s)\n' % s, "<bound dict>", [6]),
            ("a global declaration in another function", "kernel.py",
             'def install(w):\n    global isinstance\n    isinstance = w\ndef f():\n    isinstance(%s, dict)\n' % s,
             "<bound isinstance>", [5]),
            ("a walrus in a top-level def's default", "kernel.py",
             'def g(x=(tuple := list)):\n    return x\ndef f():\n    tuple(%s)\n' % s, "<bound tuple>", [4]),
            ("a star import", "kernel.py", 'from helpers import *\ndef f():\n    sorted(%s)\n' % s, "<bound sorted>", [3]),
            ("a module a dotted read names, imported otherwise", "kernel.py",
             'import simplejson as json\ndef f():\n    return json.loads(%s)\n' % s, "<bound json>", [3]),
            ("a kernel read defined twice in kernel.py", "kernel.py",
             'def _stat_key(q):\n    return None\ndef _stat_key(q):\n' + w + 'def f():\n    _stat_key(%s)\n' % s,
             "<bound _stat_key>", [6]),
            ("a kernel read's name defined in another module", "judge.py",
             'def _stat_key(q):\n' + w + 'def f():\n    _stat_key(%s)\n' % s, "<bound _stat_key>", [4]),
            ("kernel.py binding what READS was read against (not one)", "kernel.py",
             'import json\nimport os.path\nfrom pathlib import Path\ndef _stat_key(q):\n    return None\n'
             'def f():\n    p = Path(%s)\n    _stat_key(p)\n    os.stat(p)\n    return json.loads(p.read_text())\n' % s,
             None, None),
            ("a module importing only what it reads (not one)", "judge.py",
             'import json\nfrom pathlib import Path\ndef f():\n    return json.loads(Path(%s).read_text())\n' % s,
             None, None),
        ]
        got = {}
        for what, module, src, key, lines in cases:
            tree = ast.parse(src)
            fns = {_module_qual(module, n.name): n for n in tree.body if isinstance(n, ast.FunctionDef)}
            namers, flows, helpers = _derive_namers(fns, {q: _facts(fn) for q, fn in fns.items()}, self.MODULES,
                                                    {module: tree})
            outside = {c: ln for c, ln in flows[_module_qual(module, "f")].items() if c not in FlagWriterPopulation.READS}
            got[what] = outside if key is None else outside.get(key)
        self.assertEqual(got, {what: ({} if key is None else lines) for what, module, src, key, lines in cases},
                         "a read's name its module binds otherwise is spelled <bound NAME>, by line")

    def test_a_method_is_read_by_its_name_alone(self):
        """The stated limit, pinned by its witnesses (FlagWriterPopulation's docstring names them): a method in READS or
        a stop (.get, .stat, .read_text, .append, .items) is spelled by its attribute on a value whose type the census
        does not know, so it is taken for the read it names on a dict, a Path or a list, whatever object it is called
        on (the kernel's own classes define .get and .append methods, so no rule over their names can tell). A .get of
        an object whose class writes the file passes as a reader; a .get that returns its key hides the path its helper
        hands back, so the helper is no path helper and a writer through it names no store. Green by design: a change
        that closes either road reds here, and the stated limit moves with it."""
        s = 'jd.STATE / "session-flags.json"'
        getwrite = ('class _F:\n    def get(self, q, sid=None):\n        open(q, "w").write(sid)\n        return {}\n'
                    '_FF = _F()\ndef r(sid):\n    return _FF.get(%s, sid)\n' % s)
        self.assertEqual(self._outside(getwrite, "r"), {}, "a .get of an object that writes the file passes as a reader")
        getkey = ('class _I:\n    def get(self, k, default=None):\n        return k\n_ID = _I()\n'
                  'def h():\n    return _ID.get(%s)\n'
                  'def w(sid):\n    open(h(), "w").write(sid)\n' % s)
        fns = {n.name: n for n in ast.parse(getkey).body if isinstance(n, ast.FunctionDef)}
        namers, flows, helpers = _derive_namers(fns, {q: _facts(fn) for q, fn in fns.items()}, self.MODULES)
        self.assertEqual((namers, helpers, flows["h"]), ({"h"}, frozenset(), {".get": [6]}),
                         "a .get that returns its key hides the path: the helper passes as a reader and the writer "
                         "through it names no store")


class ViewsRoute(_Routes):

    def setUp(self):
        super().setUp()
        try:
            km._views_path().unlink()
        except OSError:
            pass

    def _seed(self):
        t, err = km._edit_tag("web", add=[SID])
        self.assertIsNone(err)
        self.dirty.clear()
        return km._views_client()

    def test_a_clean_write_lands_through_the_judge_and_answers_the_viewsack_document(self):
        served = self._seed()
        nv = json.loads(json.dumps(served))
        nv["actives"] = {"timeline": {"tags": ["web"]}}                # a lens edit, built from the echo
        st, r = self._post("/views", {"views": nv, "edited": [], "writeId": "w1"})
        self.assertEqual(st, 200)
        self.assertEqual((r["type"], r["writeId"], r["ok"], r["refused"]), ("viewsAck", "w1", True, []))
        self.assertEqual(r["views"]["actives"]["timeline"], {"tags": ["web"]})
        self.assertIsInstance(r["seq"], int)
        self.assertNotIn("error", r)
        stored = json.loads(km._views_path().read_text())
        self.assertEqual(stored["seq"], r["seq"], "the store carries the judge's stamp -- the write went through the one door")
        self.assertEqual(stored["actives"]["timeline"], {"tags": ["web"]})
        self.assertEqual(self.dirty, [1])
        self.assertEqual(self.notices, [])

    def test_a_stale_copy_is_refused_exactly_as_the_socket_op_refuses_it(self):
        served = self._seed()
        tid = served["tags"][0]["id"]
        stale = json.loads(json.dumps(served))                           # this panel's copy...
        time.sleep(1.1)                                                  # int-second stamps: land in a later second
        t, err = km._edit_tag("web", add=[SID2])                         # ...then another writer adds a member
        self.assertIsNone(err)
        stale["actives"] = {"timeline": {"tags": ["web"]}}               # the stale panel changes its lens...
        stale["tags"][0]["members"] = []                                 # ...and its copy of web has no members
        st, r = self._post("/views", {"views": stale, "edited": [tid], "writeId": "w2"})
        self.assertEqual((st, r["type"], r["writeId"], r["ok"]), (200, "viewsAck", "w2", False))
        self.assertEqual([x["name"] for x in r["refused"]], ["web"])
        self.assertIn("predates", r["refused"][0]["reason"])
        self.assertIn('"web"', r["error"], "one plain sentence the dialog shows as-is")
        v = r["views"]
        self.assertEqual(sorted(next(x for x in v["tags"] if x["id"] == tid)["members"]), sorted([SID, SID2]),
                         "the store's newer members stand -- the guard judged this write")
        self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]}, "the rest of the write (the lens) landed")
        # the SAME stale copy through the socket op: the same verdict, the same words, the same document
        ws = self._ws({"type": "setTimelineViews", "writeId": "w3", "views": stale, "edited": [tid]})
        self.assertEqual(len(ws), 1)
        a = ws[0]
        self.assertEqual((a["type"], a["ok"]), ("viewsAck", False))
        self.assertEqual(a["error"], r["error"])
        self.assertEqual([x["name"] for x in a["refused"]], [x["name"] for x in r["refused"]])
        self.assertEqual(set(a) - {"writeId"}, set(r) - {"writeId"}, "one document, whichever door it came through")

    def test_a_setter_exception_is_the_socket_arms_refusal_word_for_word(self):
        self._seed()
        real = km._set_timeline_views

        def boom(blob, **kw):
            raise RuntimeError("disk on fire")
        km._set_timeline_views = boom
        try:
            st, r = self._post("/views", {"views": {"active": "all", "tags": []}, "writeId": "w1"})
            ws = self._ws({"type": "setTimelineViews", "writeId": "w1", "views": {"active": "all", "tags": []}})
        finally:
            km._set_timeline_views = real
        self.assertEqual((st, r["ok"], r["refused"]), (200, False, []))
        self.assertEqual(r["error"], "the write failed on the kernel: disk on fire")
        self.assertEqual(ws[0]["error"], r["error"])
        self.assertIsInstance(r["views"], dict, "the store's blob rides the refusal, for the panel to revert to")

    def test_a_non_object_views_field_or_an_unknown_key_is_a_400(self):
        st, r = self._post("/views", {"views": "not-a-dict"})
        self.assertEqual((st, r["error"]), (400, 'views (an object) required, got "not-a-dict"'))
        st, r = self._post("/views", {"views": {"active": "all", "tags": []}, "target": "x"})
        self.assertEqual(st, 400)
        self.assertEqual(r["error"], "unknown key(s) 'target' — this route reads only 'views', 'edited', 'writeId'")
        self.assertFalse(km._views_path().exists(), "nothing was written")
        self.assertEqual(self.dirty, [])


class OrderRoute(_Routes):

    def _order_file(self):
        return json.loads((km.jd.STATE / "session-order.json").read_text())

    def test_the_merge_keeps_the_slots_of_lanes_the_drag_did_not_carry(self):
        km._write_session_order([A, B, C])
        st, r = self._post("/order", {"order": [C, A]})
        self.assertEqual((st, r), (200, {"ok": True, "order": [C, B, A]}))
        self.assertEqual(self._order_file(), [C, B, A], "B kept its slot -- the merge, never the whole-file overwrite")
        self.assertEqual(self.dirty, [1])

    def test_a_sid_the_store_does_not_know_lands_where_the_merge_puts_it(self):
        km._write_session_order([A, B, C])
        st, r = self._post("/order", {"order": [D, A]})
        self.assertEqual((st, r["order"]), (200, [D, B, C, A]))
        self.assertEqual(self._order_file(), [D, B, C, A], "the new sid takes the dragged slot; the displaced one appends")

    def test_a_non_list_a_non_string_entry_or_an_unknown_key_is_a_400(self):
        km._write_session_order([A, B, C])
        self.dirty.clear()
        st, r = self._post("/order", {"order": "abc"})
        self.assertEqual((st, r["error"]), (400, 'order (a list of session ids) required, got "abc"'))
        st, r = self._post("/order", {"order": [A, 7]})
        self.assertEqual(st, 400)
        self.assertIn("order (a list of session ids) required", r["error"])
        st, r = self._post("/order", {"order": [A], "surface": "lanes"})
        self.assertEqual((st, r["error"]), (400, "unknown key(s) 'surface' — this route reads only 'order'"))
        self.assertEqual(self._order_file(), [A, B, C], "nothing was written")
        self.assertEqual(self.dirty, [])

    def test_a_store_fault_answers_the_socket_ops_refusal_and_leaves_the_file_alone(self):
        km._write_session_order([A, B, C])
        p = km.jd.STATE / "session-order.json"
        before = p.read_bytes()
        self.dirty.clear()
        with _reads_fault(p):
            st, r = self._post("/order", {"order": [C, A]})
            ws = self._ws({"type": "reorderTabs", "order": [C, A]})
        self.assertEqual((st, r["ok"]), (200, False))
        self.assertIn("couldn't save the new order", r["error"])
        self.assertIn("session-order.json could not be read", r["error"])
        self.assertEqual(ws[0]["type"], "settingRefused")
        self.assertEqual(ws[0]["text"], r["error"], "word for word the socket op's refusal")
        self.assertEqual(p.read_bytes(), before, "never spliced against a fabricated [] and persisted")
        self.assertEqual(self.dirty, [])


class BodiesAndAuth(_Routes):

    def test_a_non_object_body_is_the_typed_400_on_every_route(self):
        for path in ("/flag", "/views", "/order"):
            st, r = self._post(path, raw=b"[1]")
            self.assertEqual((st, r), (400, {"ok": False, "error": "body must be a JSON object, got [1]"}), path)
            st, r = self._post(path, raw=b"nope")
            self.assertEqual((st, r), (400, {"ok": False, "error": "body is not JSON"}), path)

    def test_a_missing_or_wrong_token_is_refused_before_the_body_is_read(self):
        for path, body in (("/flag", {"id": SID, "flag": "hideFromFeed", "value": True}),
                           ("/views", {"views": {"active": "all", "tags": []}}),
                           ("/order", {"order": [A]})):
            for tok in (None, "not-the-token"):
                st, r = self._post(path, body, token=tok)
                self.assertEqual(st, 403, (path, tok, r))
                self.assertIn("forbidden", r)
        self.assertFalse((km.jd.STATE / "session-flags.json").exists())
        self.assertFalse(km._views_path().exists())
        self.assertFalse((km.jd.STATE / "session-order.json").exists())


class PortRecord(unittest.TestCase):
    """The panel learns the kernel's port from the kernel's OWN record, written once the socket is
    bound -- never from a guess (an Electron app launched from the dock sees no shell's
    ROMP_KERNEL_PORT) -- and beside the serve-token file it already reads."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = km.jd.STATE
        km.jd.STATE = Path(self.td.name)

    def tearDown(self):
        km.jd.STATE = self._state
        self.td.cleanup()

    def test_the_record_is_the_bound_port_one_line(self):
        km._persist_serve_port(12345)
        self.assertEqual((km.jd.STATE / "serve-port").read_text(), "12345\n")
        km._persist_serve_port(29855)
        self.assertEqual((km.jd.STATE / "serve-port").read_text(), "29855\n", "a restart on another port rewrites it")

    def test_main_writes_it_right_after_the_bind_succeeds(self):
        src = inspect.getsource(km.main)
        bind = src.index("srv = _LoopbackServer((BIND, PORT), Handler)")   # the kernel's server class (its bind skips the reverse lookup)
        rec = src.index("_persist_serve_port(srv.server_address[1])")
        self.assertLess(bind, rec, "the record follows the bind")
        between = src[bind:rec].split("\n")[1:]
        self.assertTrue(all(not ln.strip() or ln.strip().startswith("#") for ln in between),
                        "...immediately: a failed bind leaves no record that lies")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class _LockSpy:
    """Stands in for one store's lock (_flags_lock / _order_lock / _ncards_lock) for the duration of a test and says,
    without a timer, when a second writer is WAITING on it: the interleaving tests below release the
    first writer on exactly that event (or on the second writer having landed, when there is no lock to
    wait on). Delegates the lock itself."""

    def __init__(self, lock, progressed):
        self._lock, self._progressed = lock, progressed

    def __enter__(self):
        if self._lock.locked():
            self._progressed.set()                   # a writer is queued behind the one holding the store
        return self._lock.__enter__()

    def __exit__(self, *a):
        return self._lock.__exit__(*a)


class ConcurrentWriters(_Routes):
    """Two writers of one store, at once (review find, 2026-09-08, on #1078). The route and the socket
    arm land through the same setters, and those setters are read-modify-writes of a whole JSON file:
    unlocked, two writers that read the same store both publish, the later publish drops the earlier
    one's change, and BOTH are acked ok:true -- the probe that found it kept 8 to 13 of 40 concurrent
    route writes. The setters now hold a per-store lock across the read and the publish (_flags_lock,
    _order_lock), so every writer's change survives and the acks stay truthful.

    The interleaving tests force the lost-update ORDER rather than hoping for it: the first writer is
    held after its proved read (the read patched to wait on an event), the second writer is started,
    and the first is released only once the second has either LANDED (no lock: it read the same
    snapshot and published) or is WAITING on the store's lock (_LockSpy) -- both events, no timers --
    so without the lock the loss is certain, and with it the test never waits on a clock."""

    def _interleave(self, lock_name, read_name, first, second):
        """Run `first` up to and through its proved read, start `second`, wait for it to land or to
        queue on the lock, release `first`, join both. Returns their results."""
        read_done, go, progressed = threading.Event(), threading.Event(), threading.Event()
        real_read = getattr(km, read_name)
        real_lock = getattr(km, lock_name, None)      # absent on a kernel without the lock: nothing waits

        def patched_read():
            # the FIRST proved read is the first writer's (the second is not started until it has read);
            # it runs on the server's handler thread for a route write, on the test's thread for a socket
            # write, so the call order, not the thread, names it
            r = real_read()
            if not read_done.is_set():
                read_done.set()
                self.assertTrue(go.wait(20), "the first writer was never released")
            return r

        setattr(km, read_name, patched_read)
        setattr(km, lock_name, _LockSpy(real_lock or threading.Lock(), progressed))
        res = [None, None]
        try:
            t1 = threading.Thread(target=lambda: res.__setitem__(0, first()))
            t1.start()
            self.assertTrue(read_done.wait(20), "the first writer never read the store")

            def run_second():
                res[1] = second()
                progressed.set()                     # landed (no lock) -- the other way to progress
            t2 = threading.Thread(target=run_second)
            t2.start()
            self.assertTrue(progressed.wait(20), "the second writer neither landed nor queued on the lock")
            go.set()
            t1.join(20); t2.join(20)
            self.assertFalse(t1.is_alive() or t2.is_alive(), "a writer hung")
        finally:
            setattr(km, read_name, real_read)
            if real_lock is None:
                delattr(km, lock_name)
            else:
                setattr(km, lock_name, real_lock)
        return res

    def _flags_file(self):
        p = km.jd.STATE / "session-flags.json"
        return json.loads(p.read_text()) if p.exists() else None

    def _order_file(self):
        return json.loads((km.jd.STATE / "session-order.json").read_text())

    def _ncards_file(self):
        return json.loads((km.jd.STATE / "notify-cards.json").read_text())

    def test_n_concurrent_flag_posts_through_the_route_all_survive_and_every_ack_is_true(self):
        n = 32
        sids = ["%08x-1111-2222-3333-444444444444" % i for i in range(n)]
        gate = threading.Barrier(n)
        acks = [None] * n

        def post(i):
            gate.wait(20)                            # every request in flight together, then the handler threads race
            try:
                acks[i] = self._post("/flag", {"id": sids[i], "flag": "hideFromFeed", "value": True})
            except Exception as e:                   # a transport failure is a finding too, said as such
                acks[i] = ("EXC", repr(e))
        ts = [threading.Thread(target=post, args=(i,)) for i in range(n)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        self.assertFalse(any(t.is_alive() for t in ts))
        flags = self._flags_file() or {}
        self.assertEqual(sorted(flags), sorted(sids),
                         "%d of %d writes survive -- an ack must mean the toggle is in the store; acks: %s"
                         % (len(flags), n, sorted(set(str(a[0]) for a in acks))))
        self.assertTrue(all(flags[s] == {"hideFromFeed": True} for s in sids))
        self.assertEqual([a[0] for a in acks], [200] * n, acks)
        self.assertTrue(all(a[1].get("ok") is True for a in acks), "every writer was acked ok")

    def test_a_route_write_and_a_socket_write_interleaved_both_survive(self):
        r = self._interleave(
            "_flags_lock", "_session_flags_proved",
            lambda: self._post("/flag", {"id": SID, "flag": "hideFromFeed", "value": True}),
            lambda: self._ws({"type": "setSessionFlag", "id": SID2, "flag": "postalServiceOff", "value": True}))
        self.assertEqual(r[0], (200, {"ok": True, "id": SID, "flag": "hideFromFeed", "value": True}))
        self.assertEqual(r[1], [], "the socket arm sent no refusal")
        self.assertEqual(self._flags_file(), {SID: {"hideFromFeed": True}, SID2: {"postalServiceOff": True}},
                         "both acked toggles are in the store; neither writer's publish dropped the other's")

    def test_two_flag_posts_interleaved_both_survive(self):
        r = self._interleave(
            "_flags_lock", "_session_flags_proved",
            lambda: self._post("/flag", {"id": SID, "flag": "notify", "value": True}),
            lambda: self._post("/flag", {"id": SID2, "flag": "hideFromFeed", "value": True}))
        self.assertTrue(r[0][1]["ok"] and r[1][1]["ok"])
        self.assertEqual(self._flags_file(), {SID: {"notify": True}, SID2: {"hideFromFeed": True}})

    def test_an_order_post_and_a_socket_drag_interleaved_both_survive(self):
        (km.jd.STATE / "session-order.json").write_text(json.dumps([A, B, C, D]))
        r = self._interleave(
            "_order_lock", "_session_order_proved",
            lambda: self._post("/order", {"order": [B, A]}),           # the Obsidian panel swaps the first two lanes
            lambda: self._ws({"type": "reorderTabs", "order": [D, C]}))   # a dashboard swaps the last two tabs
        self.assertEqual(r[0][1]["ok"], True)
        self.assertEqual(r[1], [], "the socket arm sent no refusal")
        self.assertEqual(self._order_file(), [B, A, D, C], "both drags are in the store, each in the slots it touched")
        self.assertEqual(r[0][1]["order"], [B, A, C, D],
                         "the route's ack is the order it published: its own swap on the store it read, the queued drag landing after")

    def test_a_prune_and_a_card_bell_click_interleaved_the_click_survives(self):
        # The bells store's own lost update (round-3 review find; the sibling stores got their locks
        # 2026-09-08 and this one was left out): the pusher's prune reads the store as a card leaves the
        # feed, a card-bell click lands on a dashboard's socket thread and is acked (no refusal frame),
        # and the prune then publishes the `kept` it built from its pre-click snapshot -- the click is
        # gone, and the next push echoes the old bell.
        (km.jd.STATE / "notify-cards.json").write_text(json.dumps({SID + ":g2": False}))   # a mute whose card then leaves
        r = self._interleave(
            "_ncards_lock", "_notify_cards_proved",
            lambda: km._prune_notify_cards({SID + ":g1"}),                # the feed diff: g2 left, g1 is live
            lambda: self._ws({"type": "cardNotify", "itemId": SID + ":g1", "value": True, "sid": SID}))
        self.assertEqual(r[1], [], "the socket arm sent no refusal")
        self.assertEqual(self._ncards_file(), {SID + ":g1": True},
                         "the acked click is in the store and the departed card's mute is pruned; the prune's publish did not erase the click")

    def test_a_master_bell_post_and_a_card_bell_click_interleaved_both_survive(self):
        # The master flipped on through its route while a card is muted on a socket: unlocked, the
        # click was judged against the master it read (off), matched it, and was DELETED as a
        # restated default -- then the master's publish landed and the card follows it, unmuted,
        # after an ok ack. Under the lock the click queues, reads the master on, and stores the mute.
        r = self._interleave(
            "_ncards_lock", "_notify_cards_proved",
            lambda: self._post("/notify-all", {"on": True}),
            lambda: self._ws({"type": "cardNotify", "itemId": SID + ":g1", "value": False, "sid": SID}))
        self.assertEqual(r[0], (200, {"ok": True, "on": True}))
        self.assertEqual(r[1], [], "the socket arm sent no refusal")
        self.assertEqual(self._ncards_file(), {km.NOTIFY_ALL_KEY: True, SID + ":g1": False},
                         "the master is on and the card's mute is stored against it; neither writer's publish dropped the other's")

    def test_the_locks_are_per_store_and_taken_by_every_writer_of_the_store(self):
        src = inspect.getsource(km)
        self.assertIsInstance(km._flags_lock, type(threading.Lock()))
        self.assertIsInstance(km._order_lock, type(threading.Lock()))
        self.assertIsInstance(km._ncards_lock, type(threading.Lock()))
        for fn in (km._set_session_flag, km._set_notify_session):
            self.assertIn("with _flags_lock:", inspect.getsource(fn), fn.__name__)
        for fn in (km._reorder_session_order, km._gc_session_order, km._ordered):
            self.assertIn("with _order_lock:", inspect.getsource(fn), fn.__name__)
        for fn in (km._set_notify_all, km._set_notify_turns, km._set_notify_card, km._prune_notify_cards):
            self.assertIn("with _ncards_lock:", inspect.getsource(fn), fn.__name__)
        route = inspect.getsource(km._state_write_route)
        self.assertIn("_reorder_session_order(order)", route, "the route lands the drag through the locked step")
        self.assertNotIn("_write_session_order(merged)", route)
        arm = src[src.index('msg.get("type") in ("reorderTabs", "writeOrder")'):][:1500]
        self.assertIn('_reorder_session_order(msg["order"])', arm, "so does the socket arm")
        self.assertNotIn("_write_session_order(_merged)", arm)
