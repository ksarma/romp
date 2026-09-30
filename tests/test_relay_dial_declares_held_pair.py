"""The relay shape of a declaring dial, through the kernel's handler (2026-09-19): a dial stating relay=1 and delta=1, an
iid holding a ':' (federation.ts writes iidNamespace() + ":" + the page's iid; no local page's iid holds one) and
caps=feedDelta,held:feed:<gen>.<rev> with no readyGate, for the pair a first dial of that shape carrying caps=feedDelta
alone was served under. Against one hermetic kernel (a subprocess: tests/test_federated_dial_terms_served._kernel) and a
raw socket, the way a hub's splice reaches the remote: the first dial receives the feed full (ready from accept, since a
relay dial announces no hold), and a second dial then states the pair that full and its deltas left, once with
reconnect=1&proto=1 and once without, each variant on its OWN drive (a fresh iid and a first dial of its own: a second
dial declaring a pair the first declaring dial already adopted would be a repeat of that entry, which the kernel counts
adoptRepeat, not adopt). Under a kernel that stamps its frames the declaring dial is served one composed feedDelta stamped
base rev and no {type:"feed"}, the kernel counts one adopt per declaring dial and no undeclared eviction, and its wsopen
row (client-diag.jsonl, surface kernel: _note_ws_open's record of every accept) classes the dial a relay (client["kind"],
from the relay=1 term) and reads its reconnect term.

The pair is derived from the drive (drive_pair over the first socket's frames; the gen is the kernel's string). The leg
skips only when no served frame carried a gen key (every kernel in this repo today stamps none), saying so, after the
executed part: a first dial that receives no full at all is an empty drive and fails, the first dials' wsopen rows are read
(kind relay, no reconnect, an iid stated), and a gen key present with no pair parsed FAILS (a kernel stamping a gen the
client reads as none would otherwise skip for good). The leg lives in PR C in skip-and-branch form and runs whole under a
kernel that stamps its frames (the design's sequencing item (iii), as the design's author edits it); the client half's own
pins are the federation tests under ui/webview.

CI's served step names this module by file (its name is plain on purpose, so tests/conftest.py's ROMP_SERVED_TESTS_REQUIRE
rule, which reads served file names, leaves the gen-key skip a skip). The module therefore holds its own preconditions
under that switch: with ROMP_SERVED_TESTS_REQUIRE=1 a skip raised by lab_dist.copy_dist (no built dist: node_modules
incomplete, esbuild failing) or by the hermetic kernel boot (never served /healthz) is a FAILURE carrying the skip's reason,
so the executed part cannot go unrun with the job green (the maintainer's round 1, 2026-09-20); the gen-key skip is the one skip
that stays a skip there. PreconditionSkipsUnderRequire below drives that.

Loads no romp code in-process (the kernel is a subprocess), so this module carries no state-isolation preamble and is not
scanned by tests/test_state_isolation_order.py. Synthetic only: placeholder uuids, hostname TESTHOST, the notes-api demo's
session name.
"""
import base64
import json
import os
import shutil
import socket
import struct
import sys
import tempfile
import time
import unittest
import urllib.request
from urllib.parse import quote

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_federated_dial_terms_served as _dial   # noqa: E402  the hermetic kernel boot and the held-pair rule

SID = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST
IID_BASE = "hubwid:aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeee"   # the iid a hub's page sends: namespaced by its wid (federation.ts iidNamespace); one per drive, a digit appended


def _connect(port, token, query):
    """One raw WebSocket upgrade to the kernel's /ws?`query`, the splice's shape (no Origin: relay=1 is read first); returns
    (socket, leftover bytes)."""
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws?%s&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (query, token, port, key)
    s = socket.create_connection(("127.0.0.1", port), timeout=15)
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            raise RuntimeError("closed during the handshake")
        buf += chunk
    head, buf = buf.split(b"\r\n\r\n", 1)
    if not head.startswith(b"HTTP/1.1 101"):
        raise RuntimeError(head[:80])
    return s, buf


def _read_frame(s, buf):
    """One server frame (unmasked) -> (opcode, payload, leftover)."""
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


def _rev_as_js(v):
    """A rev field as a JS hook keeps it off the parsed wire (`typeof m[k] === "number"`, the value as the client's Number): any
    JSON number that is not a bool, an integral float read as the int JavaScript reads it (the wire text 1.0 or 2e0 is the number
    1 or 2 there, where Python's json gives a float), a non-integral float as itself; anything else none. The author's fixer pass
    after the maintainer's round 4: this recorder had kept _stamp_field's parsed form, so a negative base the feed gate applies, and a base, rev or
    through written 1.0 or 2e0, which the client reads as a safe integer, were dropped here and read as absent, where the four JS
    hooks keep the number; the held-pair rule then read the same wire frame two ways, by recorder."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if isinstance(v, float) and v.is_integer() and abs(v) < 2 ** 63:
        return int(v)
    return v


def _record(m):
    """A frame as the JS driver hooks record it: type and slot as the client reads them (a string, else none: a non-string type or
    slot moves nothing on either side), the stamp fields (the gens through _stamp_field, the kernel's string form parsed, so a gen
    the client cannot read is dropped here and told from an absent one by the presence flag; the revs as the hooks keep them,
    _rev_as_js, any number), no content. What this recorder drops that a JS hook keeps: a gen or newGen string the client cannot
    read (a number, an empty string, a separator, one over GEN_MAX); held_pair reads such a gen as a refusal from the flag alone,
    so the pair it reads is the same either way."""
    f = {"t": m.get("type") if isinstance(m.get("type"), str) else "", "slot": m.get("slot") if isinstance(m.get("slot"), str) else ""}
    for k in _dial.STAMP_FIELDS:
        v = _dial._stamp_field(m, k) if k in _dial.GEN_FIELDS else _rev_as_js(m.get(k))
        if v is not None:
            f[k] = v
    if "gen" in m:
        f["genKey"] = True   # the key's presence, whatever its value (no content): drive_pair tells an unreadable gen from none
    if "newGen" in m:
        f["newGenKey"] = True   # the same for newGen, so a red shows a composed frame whose newGen the client reads as none apart from a per-cycle delta (diagnostic only)
    return f


def _frames_until(s, buf, stop, timeout_s):
    """The text frames received on `s` (recorded, no content) until one satisfies `stop` or the timeout passes."""
    out = []
    deadline = time.time() + timeout_s
    s.settimeout(timeout_s)
    while time.time() < deadline:
        try:
            op, payload, buf = _read_frame(s, buf)
        except (socket.timeout, TimeoutError):
            break
        if op != 0x1:
            continue
        try:
            m = json.loads(payload.decode("utf-8"))
        except ValueError:
            continue
        if not isinstance(m, dict) or m.get("type") == "ka":
            continue
        out.append(_record(m))
        if stop(m):
            break
    return out, buf


class RelayDialDeclaresHeldPair(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.procs = []
        cls.lab = tempfile.mkdtemp(prefix="relay-dial-declares-")
        try:
            lab_dist.copy_dist(os.path.join(cls.lab, "dist"))
            cls.port, cls.token = _dial._free_port(), "testtok-remote-rd"
            proc, cls.log = _dial._kernel(cls.lab, "testhost", cls.port, cls.token, [(SID, "api", 1)])
            cls.procs.append(proc)
        except unittest.SkipTest as e:
            cls.tearDownClass()
            if os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1":
                # the conftest's REQUIRE rule reads served file names and this module's is plain (the module docstring), so the
                # precondition skips are made failures here: the served job has the deps and a kernel that boots, and a skip
                # there would leave the executed part unrun with the job green (the maintainer's round 1, 2026-09-20)
                raise AssertionError("ROMP_SERVED_TESTS_REQUIRE=1: a precondition of this module skipped where it must hold "
                                     "(the module holds its own preconditions under the switch; only the gen-key skip stays a skip): %s" % e) from e
            raise
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "procs", []):
            try:
                p.kill(); p.wait()
            except Exception:
                pass
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _wire(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (self.port, self.token), timeout=5) as r:
            perf = json.loads(r.read().decode())
        return ((perf.get("memos") or {}).get("wire")) or {}

    def _wsopen_rows(self, wid):
        """The kernel's wsopen rows for dashboard id `wid` (surface kernel, what wsopen: _note_ws_open's record of each accept, its
        data app, kind, reconnect, iid as a bool and cid), read from the lab kernel's client-diag.jsonl within a bounded wait;
        guarded non-empty, so no assertion below rests on an absent file."""
        path = os.path.join(self.lab, "testhost", "xdg", "romp", "client-diag.jsonl")
        rows = []
        for _ in range(40):
            rows = []
            try:
                with open(path) as fh:
                    for ln in fh:
                        try:
                            r = json.loads(ln)
                        except ValueError:
                            continue
                        if r.get("surface") == "kernel" and r.get("what") == "wsopen" and r.get("wid") == wid:
                            rows.append(r.get("data") or {})
            except OSError:
                rows = []
            if rows:
                break
            time.sleep(0.25)
        self.assertTrue(rows, "the kernel filed a wsopen row for dashboard id %s (client-diag.jsonl under the lab's state root)" % wid)
        return rows

    def _first_dial(self, iid, wid):
        """The first dial of the relay shape for `iid`, the decoder word alone: served the feed full, ready from accept. Returns
        the frames it received (the drive), after asserting the full arrived and the kernel's wsopen row classed the dial a
        relay with no reconnect term and an iid stated (the executed part of this leg at a base whose fulls carry no gen)."""
        s, buf = _connect(self.port, self.token, "app=fleet&wid=%s&relay=1&delta=1&iid=%s&caps=feedDelta" % (wid, quote(iid, safe="")))
        try:
            frames, buf = _frames_until(s, buf, lambda m: m.get("type") == "feed", 20)
        finally:
            s.close()
        self.assertIn("feed", [f["t"] for f in frames], "the first relay dial was served the feed full (the drive): %r" % (frames,))
        rows = self._wsopen_rows(wid)
        self.assertEqual([(r.get("kind"), r.get("reconnect"), r.get("iid"), r.get("app")) for r in rows], [("relay", False, True, "fleet")],
                         "one accept for the first dial, classed a relay by its relay=1 term, no reconnect term, an iid stated: %r" % (rows,))
        return frames

    def test_a_declaring_relay_dial_is_composed_from_the_declared_rev_and_counted_adopted(self):
        # one drive per variant (a fresh iid, its own first dial): the design counts adopt once per entry's first compose and a
        # second declaration of the same pair adoptRepeat, so two declaring dials on one drive would count one adopt, not two
        drives = []
        for tag, extra in (("1", "&reconnect=1&proto=1"), ("2", "")):
            iid = IID_BASE + tag
            frames = self._first_dial(iid, "w1" + tag)
            drives.append((tag, extra, iid, _dial.drive_pair(self, frames, "feed")))
        if all(pair is None for _tag, _extra, _iid, pair in drives):
            raise unittest.SkipTest("no frame carried a gen key: the attached kernel's fulls carry no gen at this base, so the first dials left no "
                                    "pair to declare and the declaring relay dial has no drive; the leg runs whole once the kernel stamps its frames")
        for tag, extra, iid, pair in drives:
            self.assertIsNotNone(pair, "every first dial was served under a stamped full, or none was: %r" % (drives,))
            wire0 = self._wire()
            wid = "w2" + tag
            caps = quote("feedDelta,held:feed:%s.%d" % pair, safe="")
            s2, buf2 = _connect(self.port, self.token, "app=fleet&wid=%s&relay=1&delta=1&iid=%s&caps=%s%s" % (wid, quote(iid, safe=""), caps, extra))
            try:
                got, _buf2 = _frames_until(s2, buf2, lambda m: m.get("type") in ("feed", "feedDelta"), 20)
            finally:
                s2.close()
            kinds = [(f["t"], f.get("base"), f.get("through"), f.get("newGen")) for f in got]
            self.assertNotIn("feed", [k[0] for k in kinds], "a declaring dial is composed, never served whole (%r): %r" % (extra, kinds))
            composed = _dial.composed_frames(got, "feed")
            self.assertEqual(len(composed), 1, "one composed feedDelta, the frame carrying newGen; a per-cycle delta carries through and no "
                                               "newGen and is not counted (%r): %r" % (extra, kinds))
            self.assertEqual(composed[0].get("base"), pair[1], "stamped base r, the declared rev")
            wire = self._wire()
            self.assertEqual((wire.get("resume.feed.adopt") or 0) - (wire0.get("resume.feed.adopt") or 0), 1,
                             "one adopt for the one declaring dial of this drive (%r): %r" % (extra, wire))
            self.assertEqual(wire.get("stash.evict.undeclared") or 0, 0, "nothing evicted as undeclared: %r" % (wire,))
            rows = self._wsopen_rows(wid)
            self.assertEqual([(r.get("kind"), r.get("reconnect")) for r in rows], [("relay", bool(extra))],
                             "the declaring dial is classed a relay (the relay class this leg closes) and its reconnect term is read (%r): %r" % (extra, rows))


class PreconditionSkipsUnderRequire(unittest.TestCase):
    """RelayDialDeclaresHeldPair.setUpClass under the served step's switch: a precondition skip (lab_dist.copy_dist raising
    SkipTest, stubbed here; the kernel boot's skip takes the same road) is a failure carrying the skip's reason with
    ROMP_SERVED_TESTS_REQUIRE=1, and stays a skip without it (the Python matrix runners' road). No dist, no kernel: the stub
    raises before either. The class's tearDownClass runs on both roads, so the lab directory it minted is removed."""

    def _stub(self, require):
        saved = os.environ.get("ROMP_SERVED_TESTS_REQUIRE")
        def restore():
            if saved is None:
                os.environ.pop("ROMP_SERVED_TESTS_REQUIRE", None)
            else:
                os.environ["ROMP_SERVED_TESTS_REQUIRE"] = saved
        self.addCleanup(restore)
        if require is None:
            os.environ.pop("ROMP_SERVED_TESTS_REQUIRE", None)
        else:
            os.environ["ROMP_SERVED_TESTS_REQUIRE"] = require
        real = lab_dist.copy_dist
        def skipping(dest):
            raise unittest.SkipTest("esbuild failed here: the stub's reason")
        lab_dist.copy_dist = skipping
        self.addCleanup(setattr, lab_dist, "copy_dist", real)

    @staticmethod
    def _setup_outcome():
        # the outcome as a word, so a skip cannot end THIS test as a skip (a pin that skips reports green)
        try:
            RelayDialDeclaresHeldPair.setUpClass()
        except unittest.SkipTest as e:
            return "skip", str(e)
        except AssertionError as e:
            return "fail", str(e)
        return "ran", ""

    def test_a_precondition_skip_is_a_failure_carrying_its_reason_under_the_switch(self):
        self._stub("1")
        outcome, text = self._setup_outcome()
        self.assertEqual(outcome, "fail", "under ROMP_SERVED_TESTS_REQUIRE=1 the precondition skip must be a failure: %s %r" % (outcome, text))
        self.assertIn("the stub's reason", text, "the failure carries the skip's own reason")
        self.assertIn("ROMP_SERVED_TESTS_REQUIRE=1", text)
        self.assertFalse(os.path.exists(RelayDialDeclaresHeldPair.lab), "the minted lab directory is removed on the failure road")

    def test_a_precondition_skip_stays_a_skip_without_the_switch(self):
        self._stub(None)
        outcome, text = self._setup_outcome()
        self.assertEqual(outcome, "skip", "without the switch the matrix runners skip as before: %s %r" % (outcome, text))
        self.assertIn("the stub's reason", text)
        self.assertFalse(os.path.exists(RelayDialDeclaresHeldPair.lab), "the minted lab directory is removed on the skip road")


if __name__ == "__main__":
    unittest.main()
