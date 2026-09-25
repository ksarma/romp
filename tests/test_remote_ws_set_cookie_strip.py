#!/usr/bin/env python3
"""The /remote/<host>/ws mirror rebuilds the peer's head from a handshake allowlist (kernel _remote_ws).

The federated-dashboard socket relay splices the browser to an attached host's kernel and mirrors that
kernel's handshake head back to the browser. The head is REBUILT from an allowlist (the status line plus
the WebSocket handshake headers), so anything the peer sets beyond the handshake (a Set-Cookie, a
Clear-Site-Data, a cache directive) is dropped: the browser talks to THIS kernel's origin, so such a
header would act here, not on the peer. This drives the real _remote_ws against a fake peer that answers
the upgrade with a Set-Cookie and a Clear-Site-Data, and asserts the browser receives neither while the
handshake headers and the peer's first frames still pass.

Self-contained (it names no session-cookie helper) so it runs against a kernel before OR after the
change. Synthetic only: host TESTHOST, an invented cookie, no session state touched.
"""
import io
import os
import socket
import threading
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_wsstrip", os.path.join(BIN, "romp-kernel"))

# a 101 head a peer kernel might answer with, carrying a Set-Cookie and a Clear-Site-Data of its own
# (RFC 6455's published example Sec-WebSocket-Accept value, allowlisted in .gitleaks.toml)
PEER_HEAD = (b"HTTP/1.1 101 Switching Protocols\r\n"
             b"Upgrade: websocket\r\n"
             b"Connection: Upgrade\r\n"
             b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
             b"Set-Cookie: romp_token=peer-set-value; Path=/\r\n"
             b"Clear-Site-Data: \"cookies\"\r\n"
             b"\r\n"
             b"PEERFRAMEBYTES")   # the peer's first frames ride past the blank line


class _FakePeer(threading.Thread):
    """A one-shot TCP server: accept a connection, read its request, answer PEER_HEAD, close."""
    daemon = True

    def __init__(self):
        super().__init__()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]

    def run(self):
        try:
            self.sock.settimeout(10)
            conn, _ = self.sock.accept()
            try:
                conn.settimeout(5)
                conn.recv(65536)          # drain the hub's forwarded upgrade request
                conn.sendall(PEER_HEAD)
            finally:
                conn.close()
        except OSError:
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class RemoteWsSetCookieStrip(unittest.TestCase):
    def setUp(self):
        self.peer = _FakePeer()
        self.peer.start()
        self._saved = dict(km._remotes)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855,
                                       "local_port": self.peer.port, "token": "", "status": "up"}

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(self._saved)
        self.peer.close()

    def test_a_peers_set_cookie_never_reaches_the_browser(self):
        browser, hub_side = socket.socketpair()
        try:
            h = km.Handler.__new__(km.Handler)
            h.headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                         "Upgrade": "websocket", "Connection": "Upgrade",
                         "Sec-WebSocket-Version": "13"}
            h.connection = hub_side
            h.rfile = io.BytesIO(b"")          # the browser sends nothing, then EOF, so the splice ends
            h.close_connection = False
            h.client_address = ("127.0.0.1", 0)
            h.command = "GET"
            h._remote_ws("TESTHOST", "app=chat")
            # what the hub wrote to the browser
            browser.settimeout(5)
            got = b""
            try:
                while True:
                    b = browser.recv(65536)
                    if not b:
                        break
                    got += b
            except OSError:
                pass
            self.assertTrue(got.startswith(b"HTTP/1.1 101"), "the 101 status line is mirrored")
            self.assertNotIn(b"Set-Cookie", got, "no peer Set-Cookie reaches the browser")
            self.assertNotIn(b"peer-set-value", got, "and not its value either")
            self.assertNotIn(b"Clear-Site-Data", got, "no peer Clear-Site-Data reaches the browser")
            self.assertIn(b"PEERFRAMEBYTES", got, "the peer's frames past the head still pass through")
            self.assertIn(b"Sec-WebSocket-Accept", got, "the handshake headers are kept")
        finally:
            browser.close()
            hub_side.close()
            self.peer.join(timeout=5)


class AllowlistHelper(unittest.TestCase):
    def test_the_helper_keeps_only_the_handshake_headers(self):
        # unit cover of _ws_head_allowlist: it rebuilds the head from the handshake allowlist, dropping
        # every other header (any case), and keeps the body past the blank line. Skipped on a kernel
        # that predates the helper.
        allow = getattr(km, "_ws_head_allowlist", None)
        if allow is None:
            self.skipTest("this kernel predates the allowlist helper")
        out = allow(PEER_HEAD)
        self.assertNotIn(b"Set-Cookie", out)
        self.assertNotIn(b"Clear-Site-Data", out)
        self.assertIn(b"Upgrade: websocket", out)
        self.assertIn(b"Sec-WebSocket-Accept", out)
        self.assertIn(b"PEERFRAMEBYTES", out)
        self.assertTrue(out.startswith(b"HTTP/1.1 101"))
        # a mixed-case non-handshake header is dropped too; only the allowlisted handshake header stays
        mixed = (b"HTTP/1.1 101 Switching Protocols\r\nset-cookie: a=b\r\nx-peer-junk: 1\r\n"
                 b"Connection: Upgrade\r\n\r\nBODY")
        out2 = allow(mixed)
        self.assertNotIn(b"a=b", out2)
        self.assertNotIn(b"x-peer-junk", out2)
        self.assertIn(b"Connection: Upgrade", out2)
        self.assertIn(b"BODY", out2)


if __name__ == "__main__":
    unittest.main()
