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


def _record(m):
    """A frame as a driver hook records it: type, slot and the stamp fields (the gens as the kernel's strings, the revs as
    numbers: _stamp_field's form, the client's), no content."""
    f = {"t": str(m.get("type")), "slot": str(m.get("slot") or "")}
    for k in _dial.STAMP_FIELDS:
        v = _dial._stamp_field(m, k)
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


if __name__ == "__main__":
    unittest.main()
