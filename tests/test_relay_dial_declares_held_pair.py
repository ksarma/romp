"""The relay shape of a declaring dial, through the kernel's handler (2026-09-19): a dial stating relay=1 and delta=1, an
iid holding a ':' (federation.ts writes iidNamespace() + ":" + the page's iid; no local page's iid holds one) and
caps=feedDelta,held:feed:<gen>.<rev> with no readyGate, for the pair a first dial of that shape carrying caps=feedDelta
alone was served under. Against one hermetic kernel (a subprocess: tests/test_federated_dial_terms_served._kernel) and a
raw socket, the way a hub's splice reaches the remote: the first dial receives the feed full (ready from accept, since a
relay dial announces no hold), and a second dial then states the pair that full and its deltas left, once with
reconnect=1&proto=1 and once without. Under a kernel that stamps its frames the declaring dial is served one composed
feedDelta stamped base rev and no {type:"feed"}, and the kernel counts one adopt per dial and no undeclared eviction.

The pair is derived from the drive (held_pair over the first socket's frames). A kernel whose full carries no gen (every
kernel in this repo today) leaves no pair to declare, so this leg has no drive and SKIPS, saying so; a first dial that
receives no full at all is an empty drive and fails. The leg rides whichever of the client change and the kernel's
generation stamp lands second, and runs then; the client half's own pins are the federation tests under ui/webview.

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
IID = "hubwid:aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"   # the iid a hub's page sends: namespaced by its wid (federation.ts iidNamespace)


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
    """A frame as a driver hook records it: type, slot and the stamp fields, no content."""
    f = {"t": str(m.get("type")), "slot": str(m.get("slot") or "")}
    for k in _dial.STAMP_FIELDS:
        if isinstance(m.get(k), int) and not isinstance(m.get(k), bool):
            f[k] = m[k]
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

    def test_a_declaring_relay_dial_is_composed_from_the_declared_rev_and_counted_adopted(self):
        # the first dial of the relay shape, the decoder word alone: served the feed full, ready from accept
        s, buf = _connect(self.port, self.token, "app=fleet&wid=w1&relay=1&delta=1&iid=%s&caps=feedDelta" % quote(IID, safe=""))
        try:
            frames, buf = _frames_until(s, buf, lambda m: m.get("type") == "feed", 20)
        finally:
            s.close()
        self.assertIn("feed", [f["t"] for f in frames], "the first relay dial was served the feed full (the drive): %r" % (frames,))
        pair = _dial.held_pair(frames, "feed")
        if pair is None:
            raise unittest.SkipTest("the attached kernel's fulls carry no gen at this base, so the first dial left no pair to declare and the "
                                    "declaring relay dial has no drive; the leg runs once the kernel stamps its frames")
        wire0 = self._wire()
        for extra in ("&reconnect=1&proto=1", ""):
            caps = quote("feedDelta,held:feed:%d.%d" % pair, safe="")
            s2, buf2 = _connect(self.port, self.token, "app=fleet&wid=w2&relay=1&delta=1&iid=%s&caps=%s%s" % (quote(IID, safe=""), caps, extra))
            try:
                got, _buf2 = _frames_until(s2, buf2, lambda m: m.get("type") in ("feed", "feedDelta"), 20)
            finally:
                s2.close()
            kinds = [(f["t"], f.get("base"), f.get("through")) for f in got]
            self.assertNotIn("feed", [k[0] for k in kinds], "a declaring dial is composed, never served whole (%r): %r" % (extra, kinds))
            composed = [k for k in kinds if k[0] == "feedDelta" and k[2] is not None]
            self.assertEqual(len(composed), 1, "one composed feedDelta (%r): %r" % (extra, kinds))
            self.assertEqual(composed[0][1], pair[1], "stamped base r, the declared rev")
        wire = self._wire()
        self.assertEqual((wire.get("resume.feed.adopt") or 0) - (wire0.get("resume.feed.adopt") or 0), 2, "one adopt per declaring dial: %r" % (wire,))
        self.assertEqual(wire.get("stash.evict.undeclared") or 0, 0, "nothing evicted as undeclared: %r" % (wire,))


if __name__ == "__main__":
    unittest.main()
