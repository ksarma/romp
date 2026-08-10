"""The kernel's WebSocket receiver reassembles fragmented client messages (RFC 6455 §5.4).

Browsers and proxies split large sends into continuation frames, and _ws_recv used to read exactly
one frame and hand it to json.loads alone — so every large client→kernel message evaporated with no
log and no reply. The visible casualty was the composer's 📎 on the web dashboard (the user
2026-08-10): the picker opened, a photo's dropFile bytes shipped as dozens of frames, and nothing
arrived — the state dir's drops/ had never even been created. Small messages ride a single frame,
which is why every other client message worked and the hole stayed invisible for so long.

Also pinned here: the two silences that hid it — an undecodable frame now logs to stderr, and a
failed attachment save now warns the client instead of replying nothing.
"""
import io
import json
import os
import struct
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

KERNEL_SRC = open(os.path.join(ROOT, "kernel", "kernel.py"), encoding="utf-8").read()

MASK = b"\x11\x22\x33\x44"


def frame(payload, opcode, fin=True, mask=MASK):
    """One client (masked) frame, wire-encoded."""
    b0 = (0x80 if fin else 0x00) | opcode
    ln = len(payload)
    if ln < 126:
        hdr = bytes([b0, 0x80 | ln])
    elif ln < 65536:
        hdr = bytes([b0, 0x80 | 126]) + struct.pack(">H", ln)
    else:
        hdr = bytes([b0, 0x80 | 127]) + struct.pack(">Q", ln)
    return hdr + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload))


def fragmented(payload, chunk, opcode=0x1):
    """A message split into continuation frames of `chunk` bytes, as a browser would send it."""
    parts = [payload[i:i + chunk] for i in range(0, len(payload), chunk)] or [b""]
    out = b""
    for i, p in enumerate(parts):
        out += frame(p, opcode if i == 0 else 0x0, fin=(i == len(parts) - 1))
    return out


class WsRecvReassembly(unittest.TestCase):
    def test_single_frame_message_unchanged(self):
        op, payload = km._ws_recv(io.BytesIO(frame(b'{"type":"ready"}', 0x1)))
        self.assertEqual((op, payload), (0x1, b'{"type":"ready"}'))

    def test_fragmented_text_message_reassembles(self):
        body = json.dumps({"type": "dropFile", "name": "photo.png", "b64": "A" * 500}).encode()
        op, payload = km._ws_recv(io.BytesIO(fragmented(body, chunk=64)))
        self.assertEqual(op, 0x1, "the message wears its FIRST frame's opcode, not 0x0")
        self.assertEqual(payload, body)
        self.assertEqual(json.loads(payload)["name"], "photo.png")

    def test_multi_megabyte_payload_round_trips(self):
        # a realistic attachment: ~3 MB of base64-ish bytes in browser-sized (~128 KB) fragments —
        # also exercises the big-int unmask fast path against the reference per-byte XOR the
        # frame() helper encodes with
        body = (b'{"type":"dropFile","b64":"' + os.urandom(3 * 1024 * 1024).hex().encode() + b'"}')
        op, payload = km._ws_recv(io.BytesIO(fragmented(body, chunk=128 * 1024)))
        self.assertEqual((op, payload), (0x1, body))

    def test_ping_interleaved_mid_message_is_answered_and_reading_continues(self):
        body = b'{"type":"ready"}'
        parts = [body[:5], body[5:]]
        wire = (frame(parts[0], 0x1, fin=False)
                + frame(b"hb", 0x9)                      # control frame between fragments (§5.5)
                + frame(parts[1], 0x0, fin=True))
        ponged = []
        op, payload = km._ws_recv(io.BytesIO(wire), pong=ponged.append)
        self.assertEqual((op, payload), (0x1, body))
        self.assertEqual(ponged, [b"hb"], "the mid-message ping must be answered in place")

    def test_ping_between_messages_still_returns_to_the_caller(self):
        op, payload = km._ws_recv(io.BytesIO(frame(b"hb", 0x9)), pong=lambda p: self.fail("not in place"))
        self.assertEqual((op, payload), (0x9, b"hb"), "the caller's own ping handling is unchanged")

    def test_close_mid_message_surfaces_the_close(self):
        wire = frame(b"partial", 0x1, fin=False) + frame(b"", 0x8)
        op, _ = km._ws_recv(io.BytesIO(wire))
        self.assertEqual(op, 0x8)

    def test_eof_mid_frame_reads_as_dead_connection(self):
        wire = fragmented(b'{"type":"ready"}', chunk=4)[:9]   # truncated mid-payload
        self.assertEqual(km._ws_recv(io.BytesIO(wire)), (None, None))

    def test_oversized_message_drops_the_link_not_the_process(self):
        old = km.WS_RECV_MAX
        km.WS_RECV_MAX = 100
        try:
            self.assertEqual(km._ws_recv(io.BytesIO(fragmented(b"x" * 500, chunk=64))), (None, None))
        finally:
            km.WS_RECV_MAX = old

    def test_the_cap_covers_the_composers_shipped_attachment_ceiling(self):
        # render.ts refuses attachments over SHIP_MAX_BYTES (50 MB); base64 inflates by 4/3, so the
        # receiver's ceiling must clear ~67 MB of payload plus JSON framing or the client-side cap lies
        self.assertGreater(km.WS_RECV_MAX, 50 * 1024 * 1024 * 4 // 3 + 4096)
        render = open(os.path.join(ROOT, "ui", "webview", "render.ts"), encoding="utf-8").read()
        self.assertIn("SHIP_MAX_BYTES = 50 * 1024 * 1024", render)


class TheSilencesArePinnedLoud(unittest.TestCase):
    def test_the_ws_loop_passes_pong_and_logs_undecodable_frames(self):
        self.assertIn("_ws_recv(self.rfile, pong=lambda p: _ws_pong(self.wfile, lock, p))", KERNEL_SRC)
        self.assertIn("ws: undecodable client frame dropped", KERNEL_SRC)

    def test_a_failed_attachment_save_warns_the_client(self):
        self.assertIn("Could not save the attachment", KERNEL_SRC)
        self.assertIn("drop save failed", KERNEL_SRC)

    def test_save_dropped_file_still_returns_none_on_bad_bytes(self):
        # the warn branch keys on None; base64 garbage must keep producing it (never raising)
        self.assertIsNone(km._save_dropped_file("x.png", "!!!not-base64!!!"))


if __name__ == "__main__":
    unittest.main()
