#!/usr/bin/env python3
"""The /remote/<host>/file relay — previews for a FEDERATED session's mentioned paths.

A remote session's chat mentions paths on the REMOTE machine's disk, but a preview <img> can only
dial the origin that served the page — its /file hit the local kernel, read the local disk, 404'd,
and every mentioned plot/screenshot on a federated session silently hid itself (2026-07-31). The
kernel now relays: GET/HEAD /remote/<host>/file forwards the one request to the attached host's
kernel through the same ssh -L tunnel the /remote/<host>/ws splice uses, after the normal local
auth gate, rewriting the remote kernel's own token into the forwarded query so the per-host trust
boundary is unchanged (THAT kernel still runs its allowlist, size cap and path resolution).

These tests run the real Handler against a fake "remote kernel" (an HTTP server that answers
/file and records what it was asked). Synthetic only: host name `gpu1`, invented tokens, no
session state touched.
"""
import os
import socket
import threading
import unittest
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Mirror tests/test_kernel_ws_auth.py's load order. The token env keeps _load_token() away from
# the real state dir; NO_OPEN keeps the import from launching a browser.
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

REMOTE_TOKEN = "remote-token-DO-NOT-USE"
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-bytes"
# the download fixture: NUL-ridden, off every view allowlist, and BIGGER than one relay stream chunk,
# so the pass-through provably crosses a chunk boundary intact
BIN_BYTES = bytes(range(256)) * ((km._DOWNLOAD_CHUNK // 256) + 60)


class _FakeRemoteFileHandler(BaseHTTPRequestHandler):
    """The attached host's kernel behind the ssh -L port, /file route only: serves PNG_BYTES for
    path=/tmp/plot.png and BIN_BYTES for path=/tmp/data.bin&download=1 (recording the request
    lines), 404s anything else."""
    requests = []               # class-level: the recorded request lines
    ctype = "image/png"         # what this remote CLAIMS the bytes are (a hostile one lies)
    dl_ctype = "application/octet-stream"          # …and the download-side claims (a hostile one lies)
    dl_disp = 'attachment; filename="data.bin"'

    def _serve(self, head):
        _FakeRemoteFileHandler.requests.append(self.path)
        if "download=1" in self.path and "data.bin" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", _FakeRemoteFileHandler.dl_ctype)
            self.send_header("Content-Disposition", _FakeRemoteFileHandler.dl_disp)
            self.send_header("Content-Length", str(len(BIN_BYTES)))
            self.end_headers()
            if not head:
                self.wfile.write(BIN_BYTES)
            return
        if "plot.png" not in self.path:
            body = b"not found: /tmp/gone" if "download=1" in self.path else b""
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Type", _FakeRemoteFileHandler.ctype)
        self.send_header("Content-Length", str(len(PNG_BYTES)))
        self.end_headers()
        if not head:
            self.wfile.write(PNG_BYTES)

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):
        self._serve(head=True)

    def log_message(self, *a):  # keep the test output clean
        pass


class RemoteFileRelay(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.fake = ThreadingHTTPServer(("127.0.0.1", 0), _FakeRemoteFileHandler)
        threading.Thread(target=self.fake.serve_forever, daemon=True).start()
        _FakeRemoteFileHandler.requests = []
        _FakeRemoteFileHandler.ctype = "image/png"
        _FakeRemoteFileHandler.dl_ctype = "application/octet-stream"
        _FakeRemoteFileHandler.dl_disp = 'attachment; filename="data.bin"'
        self._saved_remotes = dict(km._remotes)

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(self._saved_remotes)
        for s in (self.srv, self.fake):
            s.shutdown()
            s.server_close()

    def _register(self, host, local_port, token=REMOTE_TOKEN):
        with km._remotes_lock:
            km._remotes[host] = {"host": host, "kernel_port": 29855, "local_port": local_port,
                                 "token": token, "status": "up"}

    def _get(self, path, token=True, method="GET"):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method)
        if token:
            req.add_header("X-Romp-Token", km.TOKEN)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def test_relays_the_bytes_and_rewrites_the_token(self):
        self._register("gpu1", self.fake.server_address[1])
        status, body, headers = self._get(
            "/remote/gpu1/file?path=%2Ftmp%2Fplot.png&sid=11111111-2222-3333-4444-555555555555"
            "&token=whatever-the-browser-sent")
        self.assertEqual(status, 200)
        self.assertEqual(body, PNG_BYTES, "the remote's bytes must pass through unmodified")
        self.assertEqual(headers.get("Content-Type"), "image/png")
        # the forwarded request: path /file, the REMOTE's token (not what the browser sent, and
        # never the local serve token), the sid + path intact
        (req,) = _FakeRemoteFileHandler.requests
        self.assertTrue(req.startswith("/file?"), req)
        self.assertIn("token=" + REMOTE_TOKEN, req)
        self.assertNotIn("whatever-the-browser-sent", req)
        self.assertNotIn(km.TOKEN, req)
        self.assertIn("path=%2Ftmp%2Fplot.png", req)
        self.assertIn("sid=11111111-2222-3333-4444-555555555555", req)

    def test_head_relays_the_verdict_without_a_body(self):
        # the PDF chip's existence probe: headers only, the remote's real length
        self._register("gpu1", self.fake.server_address[1])
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers.get("Content-Length"), str(len(PNG_BYTES)))
        (req,) = _FakeRemoteFileHandler.requests
        self.assertTrue(req.startswith("/file?"), req)

    def test_remote_404_passes_through(self):
        # a deleted/hallucinated path: the REMOTE's 404 reaches the <img> so it hides itself
        self._register("gpu1", self.fake.server_address[1])
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.png")
        self.assertEqual(status, 404)

    def test_a_lying_remote_cannot_choose_the_content_type(self):
        """An attached host is trusted to serve its own files, not to decide how this browser
        interprets them. Mirroring its Content-Type let a compromised remote answer text/html for
        a path the preview lightbox opens in a SAME-ORIGIN, unsandboxed iframe — script on the
        dashboard's origin, with the token cookie attached. The extension decides the type here."""
        self._register("gpu1", self.fake.server_address[1])
        _FakeRemoteFileHandler.ctype = "text/html"
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(status, 200)
        self.assertEqual(body, PNG_BYTES)
        self.assertEqual(headers.get("Content-Type"), "image/png")
        self.assertNotIn("html", (headers.get("Content-Type") or "").lower())

    def test_the_relay_declines_an_extension_the_local_route_would_decline(self):
        # The relay must never widen what a preview may render: an extension outside
        # _PREVIEW_MIME 404s HERE, and the remote is not even asked.
        self._register("gpu1", self.fake.server_address[1])
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fevil.html")
        self.assertEqual(status, 404)
        self.assertEqual(_FakeRemoteFileHandler.requests, [],
                         "an unpreviewable extension must not reach the remote at all")

    def test_responses_forbid_content_type_sniffing(self):
        # A declared type is only worth as much as the browser's willingness to believe it.
        self._register("gpu1", self.fake.server_address[1])
        _, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        _, _, hh = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", method="HEAD")
        self.assertEqual(hh.get("X-Content-Type-Options"), "nosniff")

    def test_unknown_host_404s(self):
        status, _, _ = self._get("/remote/nosuch/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(status, 404)
        self.assertEqual(_FakeRemoteFileHandler.requests, [])

    def test_unauthorized_403s_before_any_dial(self):
        self._register("gpu1", self.fake.server_address[1])
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", token=False)
        self.assertEqual(status, 403, "the local auth gate must run before the relay")
        self.assertEqual(_FakeRemoteFileHandler.requests, [],
                         "an unauthorized request must never touch the tunnel")

    # ── the download half (the user 2026-08-09): /remote/<host>/file?download=1 relays ANY file the
    # remote will serve, streamed through, with the attachment headers derived on THIS side ──

    def test_download_relays_any_extension_and_the_disposition_survives(self):
        self._register("gpu1", self.fake.server_address[1])
        status, body, headers = self._get(
            "/remote/gpu1/file?path=%2Ftmp%2Fdata.bin&download=1&token=whatever-the-browser-sent")
        self.assertEqual(status, 200)
        self.assertEqual(body, BIN_BYTES,
                         "bigger than one stream chunk, so the pass-through crossed a boundary intact")
        self.assertEqual(headers.get("Content-Disposition"), 'attachment; filename="data.bin"')
        self.assertEqual(headers.get("Content-Type"), "application/octet-stream")
        self.assertEqual(headers.get("Content-Length"), str(len(BIN_BYTES)))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        # forwarded intact: download=1 rides through, the REMOTE's token replaces the browser's
        (req,) = _FakeRemoteFileHandler.requests
        self.assertIn("download=1", req)
        self.assertIn("token=" + REMOTE_TOKEN, req)
        self.assertNotIn("whatever-the-browser-sent", req)

    def test_download_headers_are_derived_locally_never_mirrored_from_the_remote(self):
        # the lying-remote rule, download edition: an attached host serves its own bytes but never
        # chooses how this browser handles them — a hostile Content-Type/Disposition is discarded
        self._register("gpu1", self.fake.server_address[1])
        _FakeRemoteFileHandler.dl_ctype = "text/html"
        _FakeRemoteFileHandler.dl_disp = "inline"
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fdata.bin&download=1")
        self.assertEqual(status, 200)
        self.assertEqual(body, BIN_BYTES)
        self.assertEqual(headers.get("Content-Type"), "application/octet-stream")
        self.assertEqual(headers.get("Content-Disposition"), 'attachment; filename="data.bin"')

    def test_the_view_relay_still_declines_that_same_extension(self):
        # without download=1 nothing changed: a .bin is off _PREVIEW_MIME, 404'd HERE, remote unasked
        self._register("gpu1", self.fake.server_address[1])
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fdata.bin")
        self.assertEqual(status, 404)
        self.assertEqual(_FakeRemoteFileHandler.requests, [])

    def test_a_remote_download_404_passes_through(self):
        self._register("gpu1", self.fake.server_address[1])
        status, body, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.bin&download=1")
        self.assertEqual(status, 404)
        self.assertIn(b"not found", body, "the remote's own verdict, which names the path IT resolved")

    def test_head_download_relays_the_attachment_without_a_body(self):
        self._register("gpu1", self.fake.server_address[1])
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fdata.bin&download=1",
                                          method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers.get("Content-Disposition"), 'attachment; filename="data.bin"')
        self.assertEqual(headers.get("Content-Length"), str(len(BIN_BYTES)))

    def test_a_dead_tunnel_502s_the_download_too(self):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
        probe.close()
        self._register("gpu1", dead_port)
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fdata.bin&download=1")
        self.assertEqual(status, 502)

    def test_dead_tunnel_502s(self):
        # a registered host whose forwarded port has no listener (the ssh died mid-flight)
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
        probe.close()
        self._register("gpu1", dead_port)
        status, _, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(status, 502)


if __name__ == "__main__":
    unittest.main()
