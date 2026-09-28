#!/usr/bin/env python3
"""The /remote/<host>/ws mirror rebuilds the peer's head from a handshake allowlist (kernel _remote_ws).

The federated-dashboard socket relay splices the browser to an attached host's kernel and mirrors that
kernel's handshake head back to the browser. The head is REBUILT from an allowlist (the status line plus
the WebSocket handshake headers), so anything the peer sets beyond the handshake (a Set-Cookie, a
Clear-Site-Data, a cache directive) is dropped: the browser talks to THIS kernel's origin, so such a
header would act here, not on the peer. This drives the real _remote_ws against a fake peer that answers
the upgrade with a Set-Cookie and a Clear-Site-Data, and asserts the browser receives neither while the
handshake headers and the peer's first frames still pass.

The other direction too: what the hub sends the peer carries none of the browser's credentials. Both
relays (this socket splice, and /remote/<host>/file) present the peer's own token and pass on no page
key (k), cap or one-time code (c) from the browser's query, and no Cookie or X-Romp-Key header.

The head is READ the way a browser reads one, and refused whole when it cannot be rebuilt
(RemoteWsHeadRefused, and the helper's own cases in AllowlistHelper): a header or status line split by
a bare LF or a bare CR, a NUL or another control byte, a status other than HTTP/1.1 101, and a head with
no blank line within the relay's byte or time bound (padded past 64 KiB, stalled, sent a byte at a time,
silent, or closed early) each get this kernel's own 502, and none of the peer's bytes, its later frames
included, reach the browser. A clean handshake still relays as its handshake headers and its frames.

The file relay mirrors five of the peer's header values (RemoteFileRelayHeaderValues): Content-Length,
Last-Modified, X-Romp-Mtime-Ns, X-Romp-Text-Utf8 and Content-Range. http.client keeps a folded line's
CRLF inside the value it returns and send_header writes a value as it is given, so the relay checks each
one: a value holding a line break or another control byte gets a 502, and never reaches the browser
inside a header of this kernel's response.

RemoteWsSetCookieStrip and RemoteFileRelayCredentials name no session-cookie helper, so they run against
a kernel before or after the login cookie split; RemoteWsHeadRefused's case beside a session signs in with
one. Synthetic only: host TESTHOST, invented cookie and credential strings, no session state touched.
"""
import http.client
import io
import os
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from urllib.parse import parse_qs, urlsplit
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
        self.got = b""                    # the upgrade request the hub forwarded, as the peer received it

    def run(self):
        try:
            self.sock.settimeout(10)
            conn, _ = self.sock.accept()
            try:
                conn.settimeout(5)
                self.got = conn.recv(65536)   # the hub's forwarded upgrade request
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

    def test_the_browsers_credentials_never_reach_the_peer(self):
        # The browser authenticates to THIS kernel; the hub dials the peer with the peer's own token (the
        # row token) and nothing of the browser's: no page key (k), cap, one-time code (c) or token of its
        # query, and no Cookie or X-Romp-Key header (only the handshake headers are copied).
        row_token = "row-" + "token-" + "testhost"
        with km._remotes_lock:
            km._remotes["TESTHOST"]["token"] = row_token
        browser, hub_side = socket.socketpair()
        try:
            h = km.Handler.__new__(km.Handler)
            h.headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                         "Upgrade": "websocket", "Connection": "Upgrade",
                         "Sec-WebSocket-Version": "13",
                         "Cookie": "browser-cookie-name=browser-cookie-value",
                         "X-Romp-Key": "browser-page-key-value"}
            h.connection = hub_side
            h.rfile = io.BytesIO(b"")
            h.close_connection = False
            h.client_address = ("127.0.0.1", 0)
            h.command = "GET"
            h._remote_ws("TESTHOST", "app=chat&k=browser-k-value&cap=browser-cap-value"
                                     "&c=browser-code-value&token=browser-token-value")
        finally:
            browser.close()
            hub_side.close()
            self.peer.join(timeout=5)
        head = self.peer.got.split(b"\r\n\r\n", 1)[0].decode("latin-1")
        self.assertTrue(head.startswith("GET "), "the peer received the forwarded upgrade")
        target = head.split("\r\n", 1)[0].split(" ")[1]
        q = parse_qs(urlsplit(target).query)
        self.assertEqual(q.get("app"), ["chat"], "the page's own dial terms pass through")
        for k in ("k", "cap", "c"):
            self.assertNotIn(k, q, "the browser's %s= never reaches the peer" % k)
        self.assertEqual(q.get("token"), [row_token], "the peer is dialled with its own token, never the browser's")
        names = {ln.split(":", 1)[0].strip().lower() for ln in head.split("\r\n")[1:] if ":" in ln}
        self.assertNotIn("cookie", names, "no browser Cookie reaches the peer")
        self.assertNotIn("x-romp-key", names, "no browser page key header reaches the peer")
        for v in ("browser-cookie-value", "browser-page-key-value", "browser-k-value", "browser-cap-value",
                  "browser-code-value", "browser-token-value"):
            self.assertNotIn(v, head, "no browser credential value reaches the peer")


class _PeerFileHandler(BaseHTTPRequestHandler):
    """A peer kernel's /file, as far as the relay needs one: record the request, answer a small PNG."""
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).seen.append((self.path, {k.lower(): v for k, v in self.headers.items()}))
        body = b"\x89PNG\r\n\x1a\nsynthetic"
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class RemoteFileRelayCredentials(unittest.TestCase):
    """The /remote/<host>/file relay forwards none of the browser's credentials: the hub authorizes the
    request here and fetches the peer's /file with the peer's own token. Authorized with the serve token,
    so it runs against a kernel before or after the change; the browser's k, cap and c ride the query and
    a Cookie and an X-Romp-Key header ride the request, as a signed-in page's would."""

    def setUp(self):
        _PeerFileHandler.seen = []
        self.peer = ThreadingHTTPServer(("127.0.0.1", 0), _PeerFileHandler)
        threading.Thread(target=self.peer.serve_forever, daemon=True).start()
        self.hub = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        threading.Thread(target=self.hub.serve_forever, daemon=True).start()
        self.row_token = "row-" + "token-" + "testhost"
        self._saved = dict(km._remotes)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": self.peer.server_address[1],
                                       "token": self.row_token, "status": "up"}

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(self._saved)
        for s in (self.hub, self.peer):
            s.shutdown()
            s.server_close()

    def test_the_browsers_credentials_never_reach_the_peer(self):
        c = http.client.HTTPConnection("127.0.0.1", self.hub.server_address[1], timeout=15)
        c.request("GET", "/remote/TESTHOST/file?path=%2Fproj%2Ffigure.png&sid=11111111-2222-3333-4444-555555555555"
                         "&k=browser-k-value&cap=browser-cap-value&c=browser-code-value",
                  headers={"X-Romp-Token": km.TOKEN, "Cookie": "browser-cookie-name=browser-cookie-value",
                           "X-Romp-Key": "browser-page-key-value"})
        r = c.getresponse()
        r.read()
        c.close()
        self.assertEqual(r.status, 200, "the relay served the peer's file")
        self.assertEqual(len(_PeerFileHandler.seen), 1, "the peer was asked once")
        path, hdrs = _PeerFileHandler.seen[0]
        q = parse_qs(urlsplit(path).query)
        self.assertEqual(q.get("path"), ["/proj/figure.png"], "the file's own terms pass through")
        for k in ("k", "cap", "c"):
            self.assertNotIn(k, q, "the browser's %s= never reaches the peer" % k)
        self.assertEqual(q.get("token"), [self.row_token], "the peer is asked with its own token")
        self.assertNotIn("cookie", hdrs, "no browser Cookie reaches the peer")
        self.assertNotIn("x-romp-key", hdrs, "no browser page key header reaches the peer")
        self.assertNotIn("x-romp-token", hdrs, "this kernel's own token never reaches the peer")

    def test_with_no_row_token_the_relay_forwards_no_token(self):
        # A host attached with no token of its own (its row token empty): the relay still strips the token this
        # kernel was asked with, so a request authorized here by ?token= never hands this kernel's token to the
        # peer, on the view and on the download half alike.
        with km._remotes_lock:
            km._remotes["TESTHOST"]["token"] = ""
        for extra in ("", "&download=1"):
            _PeerFileHandler.seen = []
            c = http.client.HTTPConnection("127.0.0.1", self.hub.server_address[1], timeout=15)
            c.request("GET", "/remote/TESTHOST/file?path=%2Fproj%2Ffigure.png&sid=11111111-2222-3333-4444-555555555555"
                             "&token=" + km.TOKEN + extra)
            r = c.getresponse()
            r.read()
            c.close()
            self.assertEqual(r.status, 200, "the relay served the peer's answer%s" % extra)
            self.assertEqual(len(_PeerFileHandler.seen), 1, "the peer was asked once%s" % extra)
            path, _hdrs = _PeerFileHandler.seen[0]
            q = parse_qs(urlsplit(path).query)
            self.assertFalse("token" in q, "no token reaches a peer that has none of its own%s" % extra)   # a boolean: no value printed
            self.assertFalse(km.TOKEN in path, "this kernel's token is nowhere in the peer's request%s" % extra)


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

    def test_the_helper_refuses_a_head_it_cannot_rebuild(self):
        # None, so the relay forwards none of it: a line split by a bare LF or a bare CR (the status line too), a
        # control byte, no blank line (or none within the byte bound), a status other than HTTP/1.1 101
        tail = b"\r\nConnection: Upgrade\r\n\r\nBODY"
        cases = {
            "a bare LF inside a header line": b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\n" + PEER_COOKIE + tail,
            "a bare CR inside a header line": b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r" + PEER_COOKIE + tail,
            "a bare LF inside the status line": b"HTTP/1.1 101 Switching Protocols\n" + PEER_COOKIE + tail,
            "a bare CR inside the status line": b"HTTP/1.1 101 Switching Protocols\r" + PEER_COOKIE + tail,
            "a NUL inside a header line": b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\x00" + PEER_COOKIE + tail,
            "a DEL inside the status line": b"HTTP/1.1 101 Switching\x7fProtocols" + tail,
            "a head with no blank line": b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n",
            "an empty head": b"",
            "a status of 401": b"HTTP/1.1 401 Unauthorized" + tail,
            "a status of 1010": b"HTTP/1.1 1010 Switching Protocols" + tail,
            "an HTTP/1.0 status line": b"HTTP/1.0 101 Switching Protocols" + tail,
        }
        for what, head in cases.items():
            with self.subTest(what):
                self.assertIsNone(km._ws_head_allowlist(head), "refused: %s" % what)

    def test_the_blank_line_must_end_within_the_byte_bound(self):
        # the head through its blank line fits in 64 KiB (65536 bytes) or is refused, one byte past included
        start, end = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nX-Pad: ", b"\r\n\r\nBODY"
        at = start + b"a" * (65536 - len(start) - len(end) + len(b"BODY")) + end
        self.assertEqual(len(at) - len(b"BODY"), 65536)
        self.assertEqual(km._ws_head_allowlist(at),
                         b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\nBODY", "a head of 65536 bytes is rebuilt")
        self.assertIsNone(km._ws_head_allowlist(start + b"a" + at[len(start):]), "a head of 65537 bytes is refused")

    def test_the_helper_writes_each_kept_header_in_its_own_spelling(self):
        # the rebuilt head is this kernel's writing, not the peer's bytes: its own status line, `Name: value` in its
        # own spelling, and a line that starts with whitespace (a folded continuation) or puts a space before its
        # colon is dropped, whatever name it looks like
        out = km._ws_head_allowlist(b"HTTP/1.1 101 whatever the peer says\r\nupgrade:websocket\r\nCONNECTION:   Upgrade  \r\n"
                                    b" upgrade: folded\r\nSec-WebSocket-Accept : spaced\r\n\r\nBODY")
        self.assertEqual(out, b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\nBODY")

    def test_the_lines_this_kernel_adds_go_inside_the_head(self):
        # the legacy cookie's clear rides as a line this kernel writes, before the blank line and the peer's frames
        out = km._ws_head_allowlist(CLEAN_HEAD + b"BODY", [b"Set-Cookie: ours=1"])
        self.assertEqual(out, CLEAN_HEAD[:-2] + b"Set-Cookie: ours=1\r\n\r\nBODY")


# A 101 head carrying only the handshake headers, in the spelling this kernel writes (RFC 6455's published example
# Sec-WebSocket-Accept value, allowlisted in .gitleaks.toml), and the two headers a peer could try to add.
CLEAN_HEAD = (b"HTTP/1.1 101 Switching Protocols\r\n"
              b"Upgrade: websocket\r\n"
              b"Connection: Upgrade\r\n"
              b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
              b"\r\n")
PEER_COOKIE = b"Set-Cookie: romp_token=peer-set-value; Path=/"
PEER_CLEAR = b'Clear-Site-Data: "cookies"'


class _ScriptedPeer(threading.Thread):
    """A one-shot peer kernel: accept one connection, read the upgrade the hub sends on, then play its script (byte strings
    to send, and numbers of seconds to wait between them) and close. A send after the hub has closed its end fails
    and ends the script."""
    daemon = True

    def __init__(self, script):
        super().__init__()
        self.script = list(script)
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
                conn.recv(65536)              # the upgrade the hub sends on
                for step in self.script:
                    if isinstance(step, bytes):
                        conn.sendall(step)
                    else:
                        time.sleep(step)
            finally:
                conn.close()
        except OSError:
            pass


class RemoteWsHeadRefused(unittest.TestCase):
    """The browser's side of the socket relay, end to end: a hub (the real Handler, its auth gate included) relays an
    upgrade to a scripted peer, and the test reads every byte the hub sends the browser until it closes. A head the
    relay cannot rebuild is this kernel's own 502, and none of the peer's bytes (its header lines, its body, its
    later frames) reach the browser."""

    def setUp(self):
        self.hub = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        threading.Thread(target=self.hub.serve_forever, daemon=True).start()
        self.port = self.hub.server_address[1]
        self._saved = dict(km._remotes)

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(self._saved)
        self.hub.shutdown()
        self.hub.server_close()

    def _bound(self):
        """The relay's time bound on the head, lowered to half a second for this test. On a kernel without the
        constant, a stall outlasts its fixed 15 s bound instead."""
        if not hasattr(km, "_WS_HEAD_TIMEOUT_S"):
            return 15.0
        p = mock.patch.object(km, "_WS_HEAD_TIMEOUT_S", 0.5)
        p.start()
        self.addCleanup(p.stop)
        return 0.5

    def _relay(self, script, cookies=None, query="app=chat", wait=10.0):
        """Every byte the hub sent the browser for one upgrade relayed to a peer that plays `script`. Authorized by
        the serve token, or by `cookies` (a session) with the page key in `query`."""
        peer = _ScriptedPeer(script)
        peer.start()
        self.addCleanup(peer.join, 30)
        self.addCleanup(peer.sock.close)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": peer.port,
                                       "token": "", "status": "up"}
        lines = ["GET /remote/TESTHOST/ws?%s HTTP/1.1" % query, "Host: 127.0.0.1:%d" % self.port,
                 "Upgrade: websocket", "Connection: Upgrade", "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
                 "Sec-WebSocket-Version: 13", ("Cookie: " + cookies) if cookies else ("X-Romp-Token: " + km.TOKEN)]
        got = b""
        s = socket.create_connection(("127.0.0.1", self.port), timeout=wait)
        try:
            s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
            while True:
                b = s.recv(65536)
                if not b:
                    break
                got += b
        except OSError:
            pass
        finally:
            s.close()
        return got

    def _assert_refused(self, got, what):
        self.assertTrue(got.startswith(b"HTTP/1.1 502 "), "%s: this kernel answers 502: %r" % (what, got[:60]))
        head = got.split(b"\r\n\r\n", 1)[0]
        self.assertIn(b"\r\nX-Content-Type-Options: nosniff\r\n", head, "%s: with this kernel's own headers" % what)
        low = got.lower()
        for word in (b"set-cookie", b"clear-site-data", b"peer-set-value", b"peerframebytes", b"x-pad"):
            self.assertNotIn(word, low, "%s: none of the peer's bytes reach the browser (%s)" % (what, word.decode()))

    def test_a_clean_handshake_is_relayed_as_its_handshake_headers_and_its_frames(self):
        got = self._relay([CLEAN_HEAD + b"PEERFRAMEBYTES", 0.05, b"LATERFRAME"])
        self.assertEqual(got, CLEAN_HEAD + b"PEERFRAMEBYTES" + b"LATERFRAME",
                         "the handshake headers, the first frames in the head's read and a later frame, nothing else")

    def test_a_header_line_split_by_a_bare_lf_is_refused(self):
        for what, line in (("a Set-Cookie", PEER_COOKIE), ("a Clear-Site-Data", PEER_CLEAR)):
            with self.subTest(what):
                got = self._relay([b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\n" + line
                                   + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
                self._assert_refused(got, "%s after a bare LF inside the Upgrade line" % what)

    def test_a_header_line_split_by_a_bare_cr_is_refused(self):
        got = self._relay([b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r" + PEER_COOKIE
                           + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
        self._assert_refused(got, "a Set-Cookie after a bare CR inside the Upgrade line")

    def test_a_status_line_split_by_a_bare_lf_or_a_bare_cr_is_refused(self):
        for what, brk in (("a bare LF", b"\n"), ("a bare CR", b"\r")):
            with self.subTest(what):
                got = self._relay([b"HTTP/1.1 101 Switching Protocols" + brk + PEER_COOKIE
                                   + b"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
                self._assert_refused(got, "a Set-Cookie after %s in the status line" % what)

    def test_a_head_holding_a_nul_or_another_control_byte_is_refused(self):
        for byte in (b"\x00", b"\x0b", b"\x0c", b"\x1b", b"\x7f", b"\t"):
            with self.subTest(byte=byte):
                got = self._relay([b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket" + byte + PEER_COOKIE
                                   + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
                self._assert_refused(got, "a Set-Cookie after the byte %r inside the Upgrade line" % byte)
        got = self._relay([b"HTTP/1.1 101 Switching\x00Protocols\r\nUpgrade: websocket\r\n" + PEER_COOKIE
                           + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
        self._assert_refused(got, "a NUL inside the status line")

    def test_a_head_with_no_blank_line_within_the_byte_bound_is_refused(self):
        got = self._relay([b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nX-Pad: " + b"a" * 70000
                           + b"\r\n" + PEER_COOKIE + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"])
        self._assert_refused(got, "a well-formed head of more than 64 KiB")

    def test_a_peer_that_closes_before_its_blank_line_is_refused(self):
        for what, script in (("a partial head, then the peer closes",
                              [b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n" + PEER_COOKIE + b"\r\n"]),
                             ("no answer at all, then the peer closes", [])):
            with self.subTest(what):
                self._assert_refused(self._relay(script), what)

    def test_a_head_stalled_past_the_time_bound_is_refused(self):
        bound = self._bound()
        got = self._relay([b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n", bound + 1.5,
                           PEER_COOKIE + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"], wait=bound + 10)
        self._assert_refused(got, "a head stalled past the bound, then finished")

    def test_a_peer_silent_past_the_time_bound_then_a_full_head_is_refused(self):
        bound = self._bound()
        got = self._relay([bound + 1.5, b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n" + PEER_COOKIE
                           + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES"], wait=bound + 10)
        self._assert_refused(got, "a full head after a silence past the bound")

    def test_a_head_dribbled_past_the_time_bound_is_refused(self):
        # one deadline for the whole read, not one per read: a byte at a time, each well inside the bound, still gets
        # a 502 once the bound has passed since the relay began to read
        bound = self._bound()
        full = (b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n" + PEER_COOKIE
                + b"\r\nConnection: Upgrade\r\n\r\nPEERFRAMEBYTES")
        step, script = (bound + 3.0) / len(full), []
        for i in range(len(full)):
            script += [full[i:i + 1], step]
        got = self._relay(script, wait=bound + 10)
        self._assert_refused(got, "a head sent a byte at a time past the bound")

    def test_a_status_other_than_101_is_this_kernels_own_502(self):
        for status in (b"HTTP/1.1 401 Unauthorized", b"HTTP/1.1 200 OK", b"HTTP/1.0 101 Switching Protocols"):
            with self.subTest(status=status):
                got = self._relay([status + b"\r\nContent-Type: text/plain\r\n" + PEER_COOKIE
                                   + b"\r\nContent-Length: 14\r\n\r\nPEERFRAMEBYTES"])
                self._assert_refused(got, "a peer head whose status line is %r" % status)

    def test_a_refused_socket_beside_a_session_carries_this_kernels_legacy_cookie_clear(self):
        # the 502 is written through this kernel's own headers, so the clear of the legacy cookie that every other
        # response to a signed-in request carries (end_headers) is on it, and it is the only Set-Cookie
        sess = km._mint_session()
        got = self._relay([b"HTTP/1.1 401 Unauthorized\r\n" + PEER_COOKIE + b"\r\nContent-Length: 14\r\n\r\nPEERFRAMEBYTES"],
                          cookies="%s=%s; romp_token=%s" % (km._SESSION_COOKIE, sess, km.TOKEN),
                          query="app=chat&k=" + km._page_key(sess))
        self.assertTrue(got.startswith(b"HTTP/1.1 502 "), "this kernel answers 502: %r" % got[:60])
        head = got.split(b"\r\n\r\n", 1)[0]
        sets = [ln for ln in head.split(b"\r\n")[1:] if ln.lower().startswith(b"set-cookie:")]
        self.assertEqual(sets, [b"Set-Cookie: " + km._LEGACY_COOKIE_CLEAR.encode("ascii")],
                         "the one Set-Cookie is this kernel's clear of the legacy cookie")
        self.assertNotIn(b"peer-set-value", got, "the peer's cookie never reaches the browser")
        self.assertNotIn(b"PEERFRAMEBYTES", got, "nor its body")


class _PeerValueHandler(BaseHTTPRequestHandler):
    """A peer kernel's /file whose reply carries one header value the test sets (`inject`: a name and a value),
    written as given: send_header checks no value, so a folded line (CRLF, then a space) or a NUL goes out as it
    is. A suffix Range gets the 206 shape of the peer's own route."""
    inject = ("X-Romp-Mtime-Ns", "1700000000000000000")
    BODY = b"\x89PNG\r\n\x1a\nsynthetic-png"

    def log_message(self, *a):
        pass

    def _serve(self, head):
        name, value = type(self).inject
        rng = self.headers.get("Range") or ""
        start = int(rng[len("bytes="):-1]) if rng.startswith("bytes=") and rng.endswith("-") else 0
        body = self.BODY[start:]
        self.send_response(206 if start else 200)
        self.send_header("Content-Type", "image/png")
        if name != "Content-Length":
            self.send_header("Content-Length", str(len(body)))
        if start and name != "Content-Range":
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, len(self.BODY) - 1, len(self.BODY)))
        self.send_header(name, value)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):
        self._serve(head=True)


class RemoteFileRelayHeaderValues(unittest.TestCase):
    """The /remote/<host>/file relay mirrors five of the peer's header values: Content-Length (a probe, a download),
    Last-Modified, X-Romp-Mtime-Ns and X-Romp-Text-Utf8 (a success), Content-Range (a partial read). One that carries a
    line break or another control byte is refused with a 502, so the peer's bytes never reach the browser inside a
    header of this kernel's response. Read over a raw socket, so the bytes are what the browser would get."""

    FOLD = "\r\n Set-Cookie: romp_token=peer-set-value; Path=/"     # a folded line: http.client keeps its CRLF
    VIEW = "/remote/TESTHOST/file?path=%2Fproj%2Ffigure.png&sid=11111111-2222-3333-4444-555555555555"
    DOWNLOAD = "/remote/TESTHOST/file?path=%2Fproj%2Fdata.bin&download=1&sid=11111111-2222-3333-4444-555555555555"

    def setUp(self):
        self.peer = ThreadingHTTPServer(("127.0.0.1", 0), _PeerValueHandler)
        threading.Thread(target=self.peer.serve_forever, daemon=True).start()
        self.hub = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        threading.Thread(target=self.hub.serve_forever, daemon=True).start()
        self._saved = dict(km._remotes)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": self.peer.server_address[1],
                                       "token": "row-" + "token-" + "testhost", "status": "up"}

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(self._saved)
        _PeerValueHandler.inject = ("X-Romp-Mtime-Ns", "1700000000000000000")
        for s in (self.hub, self.peer):
            s.shutdown()
            s.server_close()

    def _raw(self, method, path, extra=()):
        lines = ["%s %s HTTP/1.1" % (method, path), "Host: 127.0.0.1:%d" % self.hub.server_address[1],
                 "X-Romp-Token: " + km.TOKEN, "Connection: close"] + list(extra)
        got = b""
        s = socket.create_connection(("127.0.0.1", self.hub.server_address[1]), timeout=15)
        try:
            s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
            while True:
                b = s.recv(65536)
                if not b:
                    break
                got += b
        except OSError:
            pass
        finally:
            s.close()
        return got

    def test_a_clean_mirrored_value_still_relays(self):
        got = self._raw("GET", self.VIEW)
        self.assertTrue(got.startswith(b"HTTP/1.1 200 "), "the relay serves the peer's file: %r" % got[:60])
        self.assertIn(b"\r\nX-Romp-Mtime-Ns: 1700000000000000000\r\n", got.split(b"\r\n\r\n", 1)[0])

    def test_a_mirrored_value_carrying_a_line_break_or_a_control_byte_is_refused(self):
        date = "Mon, 01 Jan 2024 00:00:00 GMT"
        cases = [
            ("Last-Modified on a view", "GET", self.VIEW, (), "Last-Modified", date + self.FOLD),
            ("X-Romp-Mtime-Ns on a view", "GET", self.VIEW, (), "X-Romp-Mtime-Ns", "1700000000000000000" + self.FOLD),
            ("X-Romp-Text-Utf8 on a view", "GET", self.VIEW, (), "X-Romp-Text-Utf8", "1" + self.FOLD),
            ("a NUL in Last-Modified on a view", "GET", self.VIEW, (), "Last-Modified",
             date + "\x00Set-Cookie: romp_token=peer-set-value"),
            ("Content-Length on a probe", "HEAD", self.VIEW, (), "Content-Length", "21" + self.FOLD),
            ("Last-Modified on a probe", "HEAD", self.VIEW, (), "Last-Modified", date + self.FOLD),
            ("X-Romp-Mtime-Ns on a probe", "HEAD", self.VIEW, (), "X-Romp-Mtime-Ns", "1700000000000000000" + self.FOLD),
            # the 206 arm's own shape check (bytes N-M/L) refuses this one as well
            ("Content-Range on a partial read", "GET", self.VIEW, ("Range: bytes=4-",), "Content-Range",
             "bytes 4-20/21" + self.FOLD),
            ("Content-Length on a download", "GET", self.DOWNLOAD, (), "Content-Length", "21" + self.FOLD),
            ("Content-Length on a download probe", "HEAD", self.DOWNLOAD, (), "Content-Length", "21" + self.FOLD),
        ]
        for what, method, path, extra, name, value in cases:
            with self.subTest(what):
                _PeerValueHandler.inject = (name, value)
                got = self._raw(method, path, extra)
                self.assertTrue(got.startswith(b"HTTP/1.1 502 "), "%s: the relay refuses the reply: %r" % (what, got[:60]))
                low = got.lower()
                self.assertNotIn(b"set-cookie", low, "%s: no header line of the peer's reaches the browser" % what)
                self.assertNotIn(b"peer-set-value", low, "%s: nor its value" % what)


if __name__ == "__main__":
    unittest.main()
