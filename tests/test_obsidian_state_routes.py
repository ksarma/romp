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
from collections import Counter
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
    `value` null since no pane paints an unlisted flag, and writes nothing. Driven through the real
    dispatcher, and end to end over a real socket to the served Handler."""

    UNLISTED = ("threadMail", "postalOff", "someFutureFlag", "hideFromFeed ", "HIDEFROMFEED",
                7, True, ["hideFromFeed"], {"hideFromFeed": True})

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
        for name in self.UNLISTED:
            ws = self._ws({"type": "setSessionFlag", "id": SID, "flag": name, "value": True})
            km._flags_cache.clear()
            self.assertEqual(p.read_bytes(), before, "%r: the socket op wrote the flags store: %s"
                             % (name, p.read_text()))
            st, r = self._post("/flag", {"id": SID, "flag": name, "value": True})
            self.assertEqual(st, 400, (name, r))
            self.assertEqual(r["error"], "flag must be one of %s, got %s" % (", ".join(km._LANE_FLAGS), json.dumps(name)))
            self.assertEqual(len(ws), 1, "%r: one answer, on the delivering socket: %r" % (name, ws))
            fr = ws[0]
            self.assertEqual((fr["type"], fr["gesture"], fr["sid"], fr["itemId"]), ("settingRefused", "flag", SID, ""), fr)
            self.assertIsNone(fr["value"], "%r: no pane paints an unlisted flag, so there is no toggle to repaint" % (name,))
            self.assertEqual(fr["text"], self._wrapped(r["error"]), "%r: the route's sentence, wrapped as the socket's refusals are" % (name,))
            self.assertIsInstance(fr["flag"], str)
            if isinstance(name, str):
                self.assertEqual(fr["flag"], name, "addressed to the name the client sent")
        st, r = self._post("/flag", {"id": SID, "flag": "threadMail", "value": True})
        self.assertEqual(r["error"], 'flag must be one of hideFromFeed, postalServiceOff, notify, got "threadMail"')
        self.assertEqual(self._ws({"type": "setSessionFlag", "id": SID, "flag": "threadMail", "value": True})[0]["text"],
                         "couldn't save that setting \u2014 flag must be one of hideFromFeed, postalServiceOff, notify, "
                         'got "threadMail"; try again')
        self.assertEqual(self._flags_file(), {OTHER: {"postalServiceOff": True}})
        self.assertEqual(self.dirty, [], "a refused write marks nothing dirty")

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


def _kernel_functions():
    """The kernel's source, parsed: {qualified name: def} for every module-level function and every method of a
    module-level class, plus the module's other top-level statements."""
    tree = ast.parse(open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read())
    fns, rest = {}, []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fns[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fns["%s.%s" % (node.name, sub.name)] = sub
                else:
                    rest.append(sub)
        else:
            rest.append(node)
    return fns, rest


def _callee(call):
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def _refs(node):
    """Every name `node` mentions as code, a call or a bare reference (a setter handed on as a callback counts)."""
    return ({n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)})


def _mention(node):
    """The name a node mentions as _refs reads it: a Name's id or an Attribute's attr, else None."""
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else None


def _mentions(node, names):
    """Every node under `node` that mentions a name in `names` as code (_mention): a call by name, and equally a setter
    bound to a local, put in a table, given as a default or handed on as a callback."""
    return [n for n in ast.walk(node) if _mention(n) in names]


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
    in `fn` is keyed."""
    out = []

    def visit(node, door):
        out.append((door, node))
        if isinstance(node, ast.If):
            names = _door_names(node.test)
            visit(node.test, door)
            for st in node.body:
                visit(st, frozenset(names) if names else door)
            for st in node.orelse:
                visit(st, door)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, door)
    for st in list(fn.decorator_list) + [fn.args] + ([fn.returns] if fn.returns is not None else []) + list(fn.body):
        visit(st, frozenset({("no door", qual)}))
    return out


def _doors_reaching(fn, qual, targets):
    """{door: [line of each call]} for every call in `fn` to a name in `targets`, keyed as _door_walk keys it. The ask of
    the predicate is read this way: a door asks only by calling it."""
    found = {}
    for door, node in _door_walk(fn, qual):
        if isinstance(node, ast.Call) and _callee(node) in targets:
            found.setdefault(door, []).append(node.lineno)
    return found


def _doors_naming(fn, qual, targets):
    """{door: [line of each mention]} for every node in `fn` that mentions a name in `targets` (_mention), keyed as
    _door_walk keys it. The setters are read this way: an arm that binds a setter to a local, picks it from a table or
    hands it on writes through it as surely as one that calls it by name, so the mention makes the door."""
    found = {}
    for door, node in _door_walk(fn, qual):
        if _mention(node) in targets:
            found.setdefault(door, []).append(node.lineno)
    return found


_STORE_NEEDLE = "session-flags"   # how the kernel's source names the flags store: STATE / "session-flags.json"


def _store_seeds(node):
    """The string constants under `node` that name the flags store in CODE: any constant containing "session-flags" (a
    whole file name, a piece of an f-string, an implicitly joined literal). A docstring, or any string standing as a
    statement of its own, is text about the code and is left out."""
    text = {id(n.value) for n in ast.walk(node)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}
    return [n for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and _STORE_NEEDLE in n.value and id(n) not in text]


def _carries(node, seeds, tainted):
    """Whether `node` can hand on the store's path: a seed or a tainted name under it. A comparison is skipped, since its
    value is a bool: `p.name == "session-flags.json"` hands nothing on."""
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Compare):
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


def _call_spelling(call, modules):
    """A call's name in the census below: the name for a bare call (`open`, `_read_state_json`); the dotted chain when the
    receiver is rooted at a module the kernel imports (`os.replace`, `os.path.join`); `.attr` for a method of any other
    value (`.stat`, `.write_text`), so os.replace and a value's .replace stay apart; `<Subscript>` and the like for a
    callee this cannot name, which no expected set holds."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        chain, v = [f.attr], f.value
        while isinstance(v, ast.Attribute):
            chain.append(v.attr)
            v = v.value
        if isinstance(v, ast.Name) and v.id in modules:
            return ".".join([v.id] + chain[::-1])
        return "." + f.attr
    return "<%s>" % type(f).__name__


def _store_flow(fn, modules):
    """{call spelling: [line, ...]} for the calls in `fn` handed the flags store's path, or anything computed from it.
    Seeded at the constants naming the store (_store_seeds). A name bound from an expression that carries it (=, :=, an
    augmented or annotated assignment, a for, with or comprehension target) carries it on, to a fixpoint, and so does
    the root of a subscript or attribute assigned such a value (`cache[k] = p` taints `cache`). A call is handed it when
    an argument, a keyword's value or its receiver carries it. Over-approximate on purpose: a value computed from the
    path (its stat, a cache entry keyed by it) carries too, so the reads a reader is pinned to list a few calls that only
    ever see such a value. It judges no WRITE by its spelling: FlagWriterPopulation.READS lists what a reader may hand the
    path to, and any other call is a write until someone classes it."""
    seeds = {id(n) for n in _store_seeds(fn)}
    tainted = set()
    while True:
        grown = set(tainted)
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                pairs = [(t, n.value) for t in n.targets]
            elif isinstance(n, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                pairs = [(n.target, n.value)] if n.value is not None else []
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)):
                pairs = [(n.target, n.iter)]
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                pairs = [(i.optional_vars, i.context_expr) for i in n.items if i.optional_vars is not None]
            else:
                pairs = []
            for target, value in pairs:
                if _carries(value, seeds, tainted):
                    grown |= {m.id for m in ast.walk(target) if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Store)}
                    grown |= {r for m in ast.walk(target) if isinstance(m, (ast.Subscript, ast.Attribute))
                              and isinstance(m.ctx, ast.Store) for r in [_root_name(m)] if r}
        if grown == tainted:
            break
        tainted = grown
    handed = {}
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            parts = list(n.args) + [k.value for k in n.keywords] + ([n.func.value] if isinstance(n.func, ast.Attribute) else [])
            if any(_carries(x, seeds, tainted) for x in parts):
                handed.setdefault(_call_spelling(n, modules), []).append(n.lineno)
    return handed


def _unwrap_str(node):
    """`x` for str(x), str(str(x)), and `node` itself otherwise: str() of the name a door was asked about is that name."""
    while (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str"
           and len(node.args) == 1 and not node.keywords):
        node = node.args[0]
    return node


class FlagWriterPopulation(unittest.TestCase):
    """The doors that write a session flag, derived from the kernel's source and pinned as a set (the reviewer's
    ruling in the round-3 review of fork PR #897): the setSessionFlag socket op and POST /flag, nothing else, and
    each asks the one predicate, _lane_flag_refusal, before its setter, and hands each setter the name it asked about.
    A new door (a socket op arm, a route, or a helper that calls a setter of session-flags.json) reds here until it is
    added on purpose. An arm is a door when it MENTIONS a setter (_doors_naming), called by name or not, so an arm that
    binds a setter to a local or picks it from a table is a door too. Every road from a request to a setter is pinned
    (ROADS), derived upward from the setters by mention, so a new function or arm that hands a door function a client's
    input (a socket op forwarding to _state_write_route("/flag", ...), a second POST path onto it) reds as well. The
    setters are found without trusting how a function writes: every function that names the store in code is pinned
    by role (NAMERS), and one that hands the store's path to anything but a read (READS) is a writer, so a writer
    spelled with open(), os.replace or a helper of its own reds as surely as one that calls _write_state_json. The
    census keys on the store's name in the kernel's source: a function that reached the file through a name it did not
    spell (a file name a client sent) would be outside it, and so would a function reached by a name built as a string
    (getattr), the way the stdlib's handler enters do_GET and do_POST. These read WHERE the code lives,
    so they guard the population and the predicate's place, not the behaviour; the behaviour is executed in
    SocketFlagWhitelist (the socket op, in process and over a real socket) and in
    FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (the route)."""

    WRITERS = {"_set_session_flag", "_set_notify_session"}
    DOORS = {("socket op", "setSessionFlag"), ("route", "/flag")}
    # every function that names the store in code (_store_seeds), by role. _state_quarantine compares a torn file's name
    # with the store's to word its notice, and hands the path on to nothing
    NAMERS = {"_set_session_flag": "writer", "_set_notify_session": "writer",
              "_session_flags_proved": "reader", "_session_flags": "reader", "_flags_unknown_cold": "reader",
              "_thread_rows_key": "reader", "_chat_sig_shared": "reader", "_dead_lane_key": "reader",
              "_fleet_view_sig": "reader", "_state_quarantine": "reader"}
    # what a reader hands the store's path, or a value computed from it, to (_store_flow): a stat, the strict reader
    # _read_state_json (which may move torn bytes aside, never write a flag), the quarantine bookkeeping (a mark
    # retired, a fault noted or cleared, the refusal's text), a cache lookup, and plain value handling
    READS = {".get", ".stat", "os.stat", "_read_state_json", "_flags_quarantined", "_flags_exit_text", "_StateUnreadable",
             "_note_state_fault", "_clear_state_fault", "_retire_flags_quarantine", "_stat_key", "_chat_ident",
             "_files_stat_observe_sig", ".append", ".items", "dict", "isinstance", "str", "sorted", "tuple"}
    SETTER_CALLS = {"_set_session_flag": 1, "_set_notify_session": 1}   # per door: each setter called once
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

    def setUp(self):
        self.fns, self.rest = _kernel_functions()
        self.modules = {n for n, v in vars(km).items() if isinstance(v, type(os))}

    def _namers(self):
        return {q for q, fn in self.fns.items() if _store_seeds(fn)}

    def _writers(self):
        """The setters of session-flags.json, three ways: the functions that name the file and call a store write
        (the one door _write_state_json, its _atomic_write, a Path write); the functions that call the clean-write hook
        every landed write of that store runs (_flags_written); and the functions that hand the store's path to
        anything outside READS (_store_flow), whatever the call is spelled."""
        writes = {"_write_state_json", "_atomic_write", "write_text", "write_bytes"}
        named = self._namers()
        by_write = {q for q in named if {_callee(n) for n in ast.walk(self.fns[q]) if isinstance(n, ast.Call)} & writes}
        by_hook = {q for q, fn in self.fns.items()
                   if "_flags_written" in {_callee(n) for n in ast.walk(fn) if isinstance(n, ast.Call)}}
        by_flow = {q for q in named if set(_store_flow(self.fns[q], self.modules)) - self.READS}
        return by_write, by_hook, by_flow

    def _setters(self):
        """Every setter any derivation finds, so a new one is also a name the doors below are derived against."""
        return self.WRITERS.union(*self._writers())

    def _callers(self):
        setters = self._setters()
        return {q for q, fn in self.fns.items() if q not in setters and _refs(fn) & setters}

    def _roads(self):
        """{(function, target): mentions} for every function that mentions a setter, then every function that mentions
        one of those, to a fixpoint (a mention as _mention reads it; a method matched by its bare name, so two methods
        sharing a name both count, on the safe side). A function's mentions of itself are left out."""
        on_road = set(self._setters())
        frontier, roads = set(on_road), {}
        while frontier:
            short = {}
            for t in frontier:
                short.setdefault(t.rsplit(".", 1)[-1], set()).add(t)
            grown = set()
            for q, fn in self.fns.items():
                for n in _mentions(fn, set(short)):
                    for t in short[_mention(n)] - {q}:
                        roads[(q, t)] = roads.get((q, t), 0) + 1
                        if q not in on_road:
                            grown.add(q)
            on_road |= grown
            frontier = grown
        return roads

    def test_the_functions_that_name_the_flags_store_are_pinned_by_role(self):
        self.assertEqual(self._namers(), set(self.NAMERS),
                         "the functions that name session-flags.json in code. A new one reds here whatever it does with "
                         "the file: class it in NAMERS, a reader handing the path only to READS, or a writer, a setter "
                         "whose doors must ask _lane_flag_refusal and refuse threadMail by execution (SocketFlagWhitelist)")
        self.assertEqual([getattr(st, "lineno", 0) for st in self.rest if _store_seeds(st)], [],
                         "no module-level statement names the store: a constant there would let a function reach the file "
                         "without naming it, out of this census's sight")
        for q, role in sorted(self.NAMERS.items()):
            outside = {c: ln for c, ln in _store_flow(self.fns[q], self.modules).items() if c not in self.READS}
            if role == "reader":
                self.assertEqual(outside, {}, "%s is pinned a reader but hands the store's path to calls outside READS "
                                 "(a write, until classed); a new way to write the store is a new setter" % q)
            else:
                self.assertEqual(set(outside), {"_write_state_json", "_flags_written"},
                                 "%s writes the store through the one write door and runs its clean-write hook" % q)

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
        setters = self._setters()
        self.assertEqual([getattr(st, "lineno", 0) for st in self.rest if _refs(st) & setters], [],
                         "no module-level table hands a setter on")
        doors = {}
        for q in callers:
            named = _doors_naming(self.fns[q], q, setters)
            self.assertEqual(sum(len(v) for v in named.values()), len(_mentions(self.fns[q], setters)),
                             "%s: every mention of a setter is keyed to a door (_door_walk walks the whole def)" % q)
            doors.update(named)
        population = set().union(*doors)
        self.assertEqual(population, self.DOORS,
                         "the doors whose arm mentions a setter of session-flags.json (a call by name, or the setter "
                         "bound to a local, picked from a table, handed on): the setSessionFlag socket op and POST /flag. "
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
        on_road = {t.rsplit(".", 1)[-1] for road in roads for t in road}
        self.assertEqual([getattr(st, "lineno", 0) for st in self.rest if _refs(st) & on_road], [],
                         "no module-level or class-level statement mentions a function on these roads: a table there "
                         "would hand one on out of this walk's sight")
        post = self.fns["Handler.do_POST"]
        arms = _doors_naming(post, "Handler.do_POST", {"_state_write_route"})
        self.assertEqual(set(arms), self.ROUTE_ARMS,
                         "do_POST hands _state_write_route the request from one arm, for /flag, /views and /order; the "
                         "route's executed refusal is FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it")
        handed = [n.args[0] if n.args else None for n in ast.walk(post)
                  if isinstance(n, ast.Call) and _callee(n) == "_state_write_route"]
        self.assertEqual([ast.unparse(a) if a is not None else None for a in handed], ["u.path"],
                         "do_POST calls _state_write_route once, by name, handing it the request's own path, so only a "
                         "POST to /flag reaches the route function's /flag arm")

    def test_every_door_asks_the_one_predicate_before_its_setter(self):
        setters = self._setters()
        for q in self._callers():
            writes = _doors_naming(self.fns[q], q, setters)
            asks = _doors_reaching(self.fns[q], q, {"_lane_flag_refusal"})
            for door, lines in writes.items():
                self.assertIn(door, asks, "%s: the %s arm mentions a setter without asking _lane_flag_refusal; the executed "
                              "proof that it refuses an unlisted name is SocketFlagWhitelist (socket op) and "
                              "FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (route)"
                              % (q, sorted(door)))
                self.assertLess(min(asks[door]), min(lines), "%s %s: the predicate is asked before the first setter mention"
                                % (q, sorted(door)))

    def test_every_setter_writes_the_name_its_door_asked_about(self):
        """Asking the predicate proves nothing unless the setter writes the name it was asked about. In each door: one
        ask, of one expression; a setter mentioned only as the callee of a call by name, since the rules below read calls
        and a setter bound to a local or picked from a table writes a name they cannot see; each setter called once
        (SETTER_CALLS); _set_session_flag handed that same expression as its flag (str() of it counts as it);
        _set_notify_session, which writes the `notify` key, only under an `if` that compares that expression with
        "notify", a listed name; and nothing between the ask and a setter rebinds the expression or changes the
        container it is read from. Read from the source, so it guards the arm's shape; the
        executed refusal is SocketFlagWhitelist (socket op) and
        FlagRoute.test_an_unknown_flag_key_or_a_missing_id_is_a_400_naming_it (route)."""
        setters = self._setters()
        self.assertEqual(set(self.SETTER_CALLS), setters, "every setter has a rule below")
        self.assertIn("notify", km._LANE_FLAGS)
        flag_at = list(inspect.signature(km._set_session_flag).parameters).index("flag")
        mutators = {"update", "setdefault", "pop", "popitem", "clear", "__setitem__", "__delitem__"}
        checked = set()
        for q in sorted(self._callers()):
            fn = self.fns[q]
            parents = {c: p for p in ast.walk(fn) for c in ast.iter_child_nodes(p)}
            by_door = {}
            for door, node in _door_walk(fn, q):
                by_door.setdefault(door, []).append(node)
            for door, nodes in by_door.items():
                calls = [n for n in nodes if isinstance(n, ast.Call)]
                sets = [c for c in calls if _callee(c) in setters]
                named = [n for n in nodes if _mention(n) in setters]
                if not named:
                    continue
                where = "%s %s" % (q, sorted(door))
                self.assertEqual(sorted(n.lineno for n in named if all(n is not c.func for c in sets)), [],
                                 "%s: lines where a setter is mentioned other than as the callee of a call by name (bound "
                                 "to a local, picked from a table, handed on), so the rules below cannot read what it writes"
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
                        while node in parents and guard is None:
                            up = parents[node]
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

    def test_the_list_is_a_whitelist_in_one_place(self):
        # a membership test against _LANE_FLAGS outside the predicate is a second whitelist that can drift from it
        where = set()
        for q, fn in list(self.fns.items()) + [("<module>", st) for st in self.rest]:
            for n in ast.walk(fn):
                if (isinstance(n, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in n.ops)
                        and any(isinstance(c, ast.Name) and c.id == "_LANE_FLAGS" for c in n.comparators)):
                    where.add(q)
        self.assertEqual(where, {"_lane_flag_refusal"}, "the one predicate both doors ask; the executed proof is "
                         "SocketFlagWhitelist.test_an_unlisted_name_is_refused_on_the_socket_in_the_routes_words_and_writes_nothing")


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
