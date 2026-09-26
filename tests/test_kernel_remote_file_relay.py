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
import html
import os
import re
import socket
import threading
import unittest
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Mirror tests/test_kernel_ws_auth.py's load order. The token env keeps _load_token() away from
# the real state dir; NO_OPEN keeps the import from launching a browser.
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

REMOTE_TOKEN = "remote-token-DO-NOT-USE"
PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-png-bytes"
PDF_BYTES = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"   # a minimal synthetic PDF
PY_BYTES = b"print('hello from the remote box')\n"
SVG_BYTES = (b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
             b'<script>document.title = "ran at the local origin"</script></svg>')   # synthetic
# The policy the relay must put on every image/svg+xml success, written out and never read from the kernel (the
# local route's, tests/test_kernel_preview.py SVG_DOCUMENT_POLICY; kernel.py _media_policy_headers), and the
# weaker one the fake remote sends for its .svg, which a relay that mirrored the remote's header would pass on.
SVG_DOCUMENT_POLICY = "sandbox; default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:"
REMOTE_WEAK_POLICY = "sandbox allow-scripts; default-src *"
# Image mode's page policy and the Vary on every svg answer (kernel.py _SVG_IMAGE_PAGE_POLICY and _SVG_VARY, written out
# as tests/test_kernel_preview.py writes them), and the Accept values of Firefox's navigation and image load.
SVG_IMAGE_PAGE_POLICY = ("sandbox allow-same-origin; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
                         "base-uri 'none'; form-action 'none'")
SVG_VARY = "Sec-Fetch-Dest, Accept"
NAV_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
IMG_ACCEPT = "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"
SID = "11111111-2222-3333-4444-555555555555"
# the download fixture: NUL-ridden, off every view allowlist, and BIGGER than one relay stream chunk,
# so the pass-through provably crosses a chunk boundary intact
BIN_BYTES = bytes(range(256)) * ((km._DOWNLOAD_CHUNK // 256) + 60)


class _FakeRemoteFileHandler(BaseHTTPRequestHandler):
    """The attached host's kernel behind the ssh -L port, /file route only: serves PNG_BYTES for
    path=/tmp/plot.png and BIN_BYTES for path=/tmp/data.bin&download=1 (recording the request
    lines), 404s anything else."""
    requests = []               # class-level: the recorded request lines
    ranges = []                 # ...and the Range header each one carried (None when it carried none)
    ctype = "image/png"         # what this remote CLAIMS the bytes are (a hostile one lies)
    dl_ctype = "application/octet-stream"          # …and the download-side claims (a hostile one lies)
    dl_disp = 'attachment; filename="data.bin"'
    dl_truncate = False         # short body then a clean close, as _file_download sends when the file shrank
    nf_reason = None            # the X-Romp-Reason a newer remote puts on its 404 (None: a remote from before it)

    def _serve(self, head):
        _FakeRemoteFileHandler.requests.append(self.path)
        _FakeRemoteFileHandler.ranges.append(self.headers.get("Range"))
        if "download=1" in self.path and "data.bin" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", _FakeRemoteFileHandler.dl_ctype)
            self.send_header("Content-Disposition", _FakeRemoteFileHandler.dl_disp)
            self.send_header("Content-Length", str(len(BIN_BYTES)))
            self.end_headers()
            if not head:
                if _FakeRemoteFileHandler.dl_truncate:
                    # the remote kernel's own truncation path: a short body, then a clean close
                    self.wfile.write(BIN_BYTES[: len(BIN_BYTES) // 2])
                    self.close_connection = True
                else:
                    self.wfile.write(BIN_BYTES)
            return
        if "chart.svg" in self.path:
            # the remote's own .svg: whole, or the tail a suffix Range asks for (its _file_preview's 206 shape).
            # The remote CLAIMS image/svg+xml here, and sends a weaker policy of its own (scripts and every
            # host allowed); the relay derives its own type and policy regardless and must not mirror this one.
            rng = self.headers.get("Range") or ""
            start = int(rng[len("bytes="):-1]) if rng.startswith("bytes=") and rng.endswith("-") else 0
            body = SVG_BYTES[start:]
            self.send_response(206 if start else 200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Security-Policy", REMOTE_WEAK_POLICY)
            self.send_header("Content-Length", str(len(body)))
            if start:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, len(SVG_BYTES) - 1, len(SVG_BYTES)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        if "app.py" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", _FakeRemoteFileHandler.ctype)
            self.send_header("Content-Length", str(len(PY_BYTES)))
            self.end_headers()
            if not head:
                self.wfile.write(PY_BYTES)
            return
        if "big.pdf" in self.path or "boom.png" in self.path:
            # the remote's own size cap: its _file_preview's prose verdict, text/plain, no disposition; and a remote
            # kernel's 500, prose too. Either carries the 404's reason word when a test sets one, so the relay's
            # status guard on the mirror is pinned (the PR review's round 3).
            body = (b"too large to show: /tmp/big.pdf (95.4 MB, limit 47.7 MB)" if "big.pdf" in self.path
                    else b"the remote kernel fell over")
            self.send_response(413 if "big.pdf" in self.path else 500)
            self.send_header("Content-Type", "text/plain")
            if _FakeRemoteFileHandler.nf_reason is not None:
                self.send_header("X-Romp-Reason", _FakeRemoteFileHandler.nf_reason)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        if "paper.pdf" in self.path:
            # a (hostile) remote's own disposition — an instruction to this browser, which the relay must
            # never echo: ours is derived from the requested name
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="evil.pdf"')
            self.send_header("Content-Length", str(len(PDF_BYTES)))
            self.end_headers()
            if not head:
                self.wfile.write(PDF_BYTES)
            return
        if "plot.png" not in self.path:
            body = b"not found: /tmp/gone" if "download=1" in self.path else b""
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            if _FakeRemoteFileHandler.nf_reason is not None:
                self.send_header("X-Romp-Reason", _FakeRemoteFileHandler.nf_reason)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        self.send_response(200)
        self.send_header("Content-Type", _FakeRemoteFileHandler.ctype)
        self.send_header("Content-Length", str(len(PNG_BYTES)))
        if _FakeRemoteFileHandler.nf_reason is not None:
            # a (confused or hostile) remote putting a 404's word on its 200: the relay's mirror is guarded on the status
            self.send_header("X-Romp-Reason", _FakeRemoteFileHandler.nf_reason)
        self.end_headers()
        if not head:
            self.wfile.write(PNG_BYTES)

    def do_GET(self):
        self._serve(head=False)

    def do_HEAD(self):
        self._serve(head=True)

    def log_message(self, *a):  # keep the test output clean
        pass


class _RecorderSink:
    def __init__(self, sink):
        self.sink = sink

    def write(self, b):
        self.sink.append(bytes(b))


class _RelayRecorder:
    """Just enough Handler surface for a direct _relay_download call: records status, headers and
    every wfile.write, and starts with close_connection False — so a test can see the one thing an
    over-HTTP client cannot: whether the relay itself decided to close the connection."""

    def __init__(self):
        self.writes, self.headers, self.status = [], {}, None
        self.close_connection = False
        self.wfile = _RecorderSink(self.writes)

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass

    _send = km.Handler._send      # the error paths route through the real _send, captured by the fakes


class RemoteFileRelay(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.fake = ThreadingHTTPServer(("127.0.0.1", 0), _FakeRemoteFileHandler)
        threading.Thread(target=self.fake.serve_forever, daemon=True).start()
        _FakeRemoteFileHandler.requests = []
        _FakeRemoteFileHandler.ranges = []
        _FakeRemoteFileHandler.ctype = "image/png"
        _FakeRemoteFileHandler.dl_ctype = "application/octet-stream"
        _FakeRemoteFileHandler.dl_disp = 'attachment; filename="data.bin"'
        _FakeRemoteFileHandler.dl_truncate = False
        _FakeRemoteFileHandler.nf_reason = None
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

    def test_a_remote_pdf_is_served_inline_with_its_own_name_derived_here_never_the_remotes(self):
        # a remote session's PDF opens in its own browser tab too (2026-09-06): the tab's title and a Save's
        # name ride Content-Disposition, which the local route sends — so the relay must as well, from the
        # REQUESTED basename, on GET and on the HEAD probe. The remote's header is discarded like its
        # Content-Type: an instruction to this browser, not a fact about its disk.
        self._register("gpu1", self.fake.server_address[1])
        for method in ("GET", "HEAD"):
            status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fpaper.pdf", method=method)
            self.assertEqual(status, 200, method)
            self.assertEqual(headers.get("Content-Type"), "application/pdf")
            self.assertEqual(headers.get("Content-Disposition"), 'inline; filename="paper.pdf"', method)
            self.assertNotIn("evil", headers.get("Content-Disposition") or "")
            self.assertEqual(body, PDF_BYTES if method == "GET" else b"")
        # a remote 404 for a .pdf name carries no disposition — there is no file to name
        status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.pdf")
        self.assertEqual(status, 404)
        self.assertIsNone(headers.get("Content-Disposition"))
        # …and an image never gets one, exactly as locally
        status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(status, 200)
        self.assertIsNone(headers.get("Content-Disposition"))

    def test_a_remote_error_verdict_is_prose_and_an_oversize_pdf_tab_gets_the_relays_own_way_out(self):
        # a PDF opens in its own TAB now (2026-09-06): the remote's 413/404 prose used to come back labelled
        # with OUR media mime, which an <img> merely failed on but a tab shows as a corrupt-PDF error
        # (skeptic find). Every non-success verdict is text/plain; a navigation to an oversize PDF gets the
        # same way-out page the local route serves, linking THIS relay's download half.
        self._register("gpu1", self.fake.server_address[1])
        sid = "11111111-2222-3333-4444-555555555555"
        qp = "/remote/gpu1/file?path=%2Ftmp%2Fbig.pdf&sid=" + sid
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, qp),
                                     headers={"X-Romp-Token": km.TOKEN, "Sec-Fetch-Dest": "document"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                status, body, headers = r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            status, body, headers = e.code, e.read(), dict(e.headers)
        self.assertEqual(status, 413)
        self.assertTrue(headers.get("Content-Type", "").startswith("text/html"), headers.get("Content-Type"))
        page = body.decode("utf-8")
        self.assertIn("too large to show: /tmp/big.pdf", page)
        dq = urllib.parse.urlencode({"path": "/tmp/big.pdf", "download": "1", "sid": sid})
        self.assertIn('href="' + km._html_esc("/remote/gpu1/file?" + dq) + '"', page, "the relay's download half")
        # the same without the navigation marker: the remote's prose, labelled as prose
        status, body, headers = self._get(qp)
        self.assertEqual(status, 413)
        self.assertEqual(headers.get("Content-Type"), "text/plain")
        self.assertTrue(body.startswith(b"too large to show:"), body[:40])
        status, body, headers = self._get(qp, method="HEAD")
        self.assertEqual((status, body, headers.get("Content-Type")), (413, b"", "text/plain"))
        # a remote 404 for a .pdf name: prose too, never application/pdf
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.pdf")
        self.assertEqual((status, headers.get("Content-Type")), (404, "text/plain"))

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
        # a deleted/hallucinated path: the REMOTE's 404 reaches the <img> so it hides itself. Its one-word cause,
        # X-Romp-Reason (Slice 6 of plans/markdown-viewer.md, the PR review's round 2), is MIRRORED when it is a word
        # the local /file route itself sends (data about the remote's disk, like X-Romp-Mtime-Ns), and dropped
        # otherwise: prose from a lying remote never rides, and a remote from before the header sends none.
        self._register("gpu1", self.fake.server_address[1])
        status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.png")
        self.assertEqual(status, 404)
        self.assertNotIn("X-Romp-Reason", headers, "an older remote names no cause; the relay invents none")
        # ...the four words the local route sends: `unreadable`, the fourth, is the PR review's round 3 (an absolute
        # path the remote kernel could not stat, EACCES on a parent, which had read as `missing` there and here)
        for word in ("missing", "relative", "unresolved", "unreadable"):
            _FakeRemoteFileHandler.nf_reason = word
            for method in ("GET", "HEAD"):
                status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.png", method=method)
                self.assertEqual((status, body), (404, b""), (word, method))
                self.assertEqual(headers.get("X-Romp-Reason"), word, (word, method))
        for prose in ("the disk is gone", "detached", "MISSING", ""):
            _FakeRemoteFileHandler.nf_reason = prose
            status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.png", method="HEAD")
            self.assertEqual(status, 404, repr(prose))
            self.assertNotIn("X-Romp-Reason", headers, repr(prose))

    def test_a_remote_reason_word_rides_on_its_404_alone_never_on_a_200_413_or_500(self):
        # The mirror is guarded on the remote's STATUS as well as its word (the PR review's round 3 pinned the guard,
        # which no case had held): a reason word is data about a 404, and a remote that puts a known word on another
        # verdict, its 200 with the bytes, its own 413, a 500, is answered without it, GET and HEAD alike, the way its
        # Content-Type is dropped. Nothing reads the header off a non-404 today; the pin keeps that so.
        self._register("gpu1", self.fake.server_address[1])
        _FakeRemoteFileHandler.nf_reason = "missing"
        for name, want in (("plot.png", 200), ("big.pdf", 413), ("boom.png", 500)):
            for method in ("GET", "HEAD"):
                status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2F" + name, method=method)
                self.assertEqual(status, want, (name, method))
                self.assertNotIn("X-Romp-Reason", headers, (name, method))
        # ...while the same word on the remote's 404 rides: the guard is on the status, not on the word
        status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fgone.png", method="HEAD")
        self.assertEqual((status, headers.get("X-Romp-Reason")), (404, "missing"))

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

    def test_text_relays_with_a_locally_derived_type_the_remote_cannot_override(self):
        """The text half of /file relays too — this gate predated it, so a remote session's
        .py/.md 404'd here while the LOCAL route served the same file (the viewer just failed
        on every federated text file). The defense is unchanged and now covers text: the type
        is OURS — a lying remote's text/html arrives as inert text/plain + nosniff. (.html is
        on _TEXT_EXT, so it too relays as text/plain now — same inertness, matching the local
        route; the never-asked decline for off-every-allowlist extensions is pinned by the
        .bin test below.)"""
        self._register("gpu1", self.fake.server_address[1])
        _FakeRemoteFileHandler.ctype = "text/html"
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fapp.py")
        self.assertEqual(status, 200)
        self.assertEqual(body, PY_BYTES)
        self.assertEqual(headers.get("Content-Type"), "text/plain; charset=utf-8")
        self.assertNotIn("html", (headers.get("Content-Type") or "").lower())

    def test_responses_forbid_content_type_sniffing(self):
        # A declared type is only worth as much as the browser's willingness to believe it.
        self._register("gpu1", self.fake.server_address[1])
        _, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        _, _, hh = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", method="HEAD")
        self.assertEqual(hh.get("X-Content-Type-Options"), "nosniff")

    def test_unknown_host_404s(self):
        # ...naming the cause in X-Romp-Reason: `detached`, never `missing`, since no disk was consulted
        for method in ("GET", "HEAD"):
            status, body, headers = self._get("/remote/nosuch/file?path=%2Ftmp%2Fplot.png", method=method)
            self.assertEqual(status, 404, method)
            self.assertEqual(headers.get("X-Romp-Reason"), "detached", method)
            if method == "HEAD":
                self.assertEqual(body, b"")
        self.assertEqual(_FakeRemoteFileHandler.requests, [])

    def test_a_host_detached_after_a_successful_get_heads_404_detached(self):
        # the viewer's shape (Slice 6 of plans/markdown-viewer.md, the PR review's round 2): a remote session's file
        # was shown, the host's tunnel went away, the focus HEAD asks the same URL. The file is on the remote's disk
        # still; the 404 says `detached`, so the viewer does not call it deleted.
        self._register("gpu1", self.fake.server_address[1])
        status, body, _ = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual((status, body), (200, PNG_BYTES))
        with km._remotes_lock:
            km._remotes.pop("gpu1")
        asked = list(_FakeRemoteFileHandler.requests)
        status, body, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", method="HEAD")
        self.assertEqual((status, body), (404, b""))
        self.assertEqual(headers.get("X-Romp-Reason"), "detached")
        self.assertEqual(_FakeRemoteFileHandler.requests, asked, "nothing was dialed for the detached host")

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
        # without download=1 nothing changed: a .bin is off _PREVIEW_MIME, 404'd HERE, remote unasked; the cause word
        # is `unviewable`, the vocabulary's word for this side's own refusal
        self._register("gpu1", self.fake.server_address[1])
        status, _, headers = self._get("/remote/gpu1/file?path=%2Ftmp%2Fdata.bin")
        self.assertEqual(status, 404)
        self.assertEqual(headers.get("X-Romp-Reason"), "unviewable")
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

    def test_a_remote_that_truncates_cleanly_still_closes_this_connection_short(self):
        """The remote's own _file_download truncation path sends SHORT and then closes cleanly — on
        this side http.client's read() answers that with b'' and NO exception, so only counting the
        copied bytes against the Content-Length already forwarded can spot the broken promise.
        Without the close, this keep-alive (HTTP/1.1) connection leaves the browser waiting on
        bytes that will never come — a hung download instead of a visibly failed one. Pinned by a
        direct _relay_download call: over HTTP a test client's own Connection: close (urllib sends
        it always) would close the connection for the wrong reason and hide exactly this bug."""
        _FakeRemoteFileHandler.dl_truncate = True
        rec = _RelayRecorder()
        km.Handler._relay_download(rec, "gpu1", self.fake.server_address[1], REMOTE_TOKEN,
                                   {"path": ["/tmp/data.bin"], "download": ["1"]})
        self.assertEqual(rec.status, 200)
        self.assertEqual(rec.headers.get("Content-Length"), str(len(BIN_BYTES)),
                         "the remote's promised length went out before the truncation")
        self.assertEqual(b"".join(rec.writes), BIN_BYTES[: len(BIN_BYTES) // 2],
                         "the bytes that did arrive still pass through")
        self.assertTrue(rec.close_connection,
                        "short of the forwarded Content-Length must CLOSE, or the browser hangs")

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

    def _get_msg(self, path, method="GET", headers=None):
        # the raw header MESSAGE: a dict keeps one value per name, and the SVG sandbox policy rides beside
        # _send's frame-ancestors one under the same header name
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method,
                                     headers=headers or {})
        req.add_header("X-Romp-Token", km.TOKEN)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def test_a_remote_svg_is_a_sandboxed_document_by_the_relays_own_policy(self):
        # The relay derives every header that tells THIS browser how to interpret the bytes (the type, the
        # disposition) from the requested extension and discards the remote's, so the local route's SVG
        # defence (tests/test_kernel_preview.py SvgSandboxPolicy: a tab navigated to an SVG runs its inline
        # script at the serving origin, and loads every host its markup names) has to be restated here, from
        # OUR mime: the bytes a remote session's .svg is served as would be a document at this kernel's origin
        # wherever something still made them one (the 1204 review, 2026-09-10; the fetch directives, 2026-09-23;
        # a tab gets the image-mode page since, the tests below). The remote sends a weaker policy of its own
        # (REMOTE_WEAK_POLICY), so the whole list of policies is compared: a relay that mirrored the remote's
        # header, or restated a weakened one, fails. All three success shapes; a remote PNG carries none.
        # tests/test_svg_tab_policy_browser.py opens a tab on this arm in Chromium, and in Firefox and WebKit when
        # ROMP_BROWSER_ENGINES names them.
        self._register("gpu1", self.fake.server_address[1])
        csp = lambda msg: "; ".join(msg.get_all("Content-Security-Policy") or [])
        for method, headers, want, policies in (("GET", None, 200, [SVG_DOCUMENT_POLICY, "frame-ancestors 'self'"]),
                                                ("HEAD", None, 200, [SVG_DOCUMENT_POLICY]),
                                                ("GET", {"Range": "bytes=1-"}, 206, [SVG_DOCUMENT_POLICY])):
            status, body, msg = self._get_msg("/remote/gpu1/file?path=%2Ftmp%2Fchart.svg", method=method, headers=headers)
            self.assertEqual(status, want, (method, headers))
            self.assertEqual(msg.get("Content-Type"), "image/svg+xml", (method, headers))
            self.assertEqual(sorted(msg.get_all("Content-Security-Policy") or []), sorted(policies), (method, headers, csp(msg)))
            self.assertEqual(body, b"" if method == "HEAD" else SVG_BYTES[1 if headers else 0:], (method, headers))
        status, _, msg = self._get_msg("/remote/gpu1/file?path=%2Ftmp%2Fplot.png")
        self.assertEqual(status, 200)
        self.assertNotIn("sandbox", csp(msg), csp(msg))
        self.assertNotIn("default-src", csp(msg), csp(msg))


    def _page_img(self, body):
        return [html.unescape(m) for m in re.findall(r'<img\b[^>]*\bsrc="([^"]*)"', body.decode("utf-8"))]

    def test_a_navigation_to_a_remote_svg_gets_the_image_mode_page_built_before_the_token(self):
        # Image mode on the relay (kernel.py _svg_image_page): the remote never sees the browser's Sec-Fetch-Dest or
        # Accept, so this side decides, and builds the page from the BROWSER's query before it writes the remote's token
        # into that query: the page carries neither token, and its <img> is this relay's own route for the same path and
        # sid plus raw=1. The remote is still asked, once, with its own token and no Range (a page has no bytes to
        # resume), so a file it does not have stays its 404 (the next test).
        self._register("gpu1", self.fake.server_address[1])
        path = "/remote/gpu1/file?path=%2Ftmp%2Fchart.svg&sid=" + SID + "&token=whatever-the-browser-sent"
        for how, headers in (("a navigation (Sec-Fetch-Dest document)", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}),
                             ("a plain-http navigation (no Sec-Fetch-Dest, text/html Accept)", {"Accept": NAV_ACCEPT}),
                             ("a navigation that carries a Range", {"Sec-Fetch-Dest": "document", "Range": "bytes=1-"}),
                             ("an object", {"Sec-Fetch-Dest": "object"})):
            with self.subTest(how):
                _FakeRemoteFileHandler.requests, _FakeRemoteFileHandler.ranges = [], []
                status, body, msg = self._get_msg(path, headers=headers)
                self.assertEqual((status, msg.get("Content-Type")), (200, "text/html; charset=utf-8"),
                                 "%s: the image-mode page, not the remote's svg as a document" % how)
                self.assertEqual(sorted(msg.get_all("Content-Security-Policy") or []),
                                 sorted([SVG_IMAGE_PAGE_POLICY, "frame-ancestors 'self'"]), how)
                self.assertEqual(msg.get_all("Vary"), [SVG_VARY], how)
                for leak in (b"token", REMOTE_TOKEN.encode(), b"whatever-the-browser-sent", b"<script"):
                    self.assertNotIn(leak, body, "%s: %r is not in the page" % (how, leak))
                srcs = self._page_img(body)
                self.assertEqual(len(srcs), 1, (how, srcs))
                u = urllib.parse.urlsplit(srcs[0])
                self.assertEqual((u.scheme, u.netloc, u.path, urllib.parse.parse_qs(u.query)),
                                 ("", "", "/remote/gpu1/file", {"path": ["/tmp/chart.svg"], "sid": [SID], "raw": ["1"]}),
                                 "%s: the <img> reads this relay for the same path and sid, plus raw=1: %r" % (how, srcs[0]))
                self.assertEqual(len(_FakeRemoteFileHandler.requests), 1, how)
                self.assertIn("token=" + REMOTE_TOKEN, _FakeRemoteFileHandler.requests[0], "%s: the remote was asked with its own token" % how)
                self.assertEqual(_FakeRemoteFileHandler.ranges, [None], "%s: no Range is forwarded for a page" % how)

    def test_a_navigation_to_a_missing_remote_svg_gets_the_remotes_404(self):
        # a control: the page is served only when the remote has the file, so a missing one reaches the tab as the remote's
        # verdict, unchanged by image mode
        self._register("gpu1", self.fake.server_address[1])
        status, body, msg = self._get_msg("/remote/gpu1/file?path=%2Ftmp%2Fgone.svg&sid=" + SID,
                                          headers={"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT})
        self.assertEqual((status, msg.get("Content-Type")), (404, "text/plain"))
        self.assertNotIn(b"<img", body)

    def test_every_other_request_for_a_remote_svg_keeps_the_bytes(self):
        # the controls: the page's own <img> (raw=1), an image load, a navigation's HEAD and a Range retry get the remote's
        # bytes under the relay's own policy, as before image mode (Vary is pinned on its own, next)
        self._register("gpu1", self.fake.server_address[1])
        base = "/remote/gpu1/file?path=%2Ftmp%2Fchart.svg&sid=" + SID
        for how, extra, headers, method, want, body_want in (
                ("the page's <img>", "&raw=1", {"Sec-Fetch-Dest": "image", "Accept": IMG_ACCEPT}, "GET", 200, SVG_BYTES),
                ("an image load", "", {"Sec-Fetch-Dest": "image", "Accept": IMG_ACCEPT}, "GET", 200, SVG_BYTES),
                ("a HEAD a navigation would send", "", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}, "HEAD", 200, b""),
                ("a Range retry", "", {"Sec-Fetch-Dest": "image", "Range": "bytes=1-"}, "GET", 206, SVG_BYTES[1:])):
            with self.subTest(how):
                status, body, msg = self._get_msg(base + extra, method=method, headers=headers)
                self.assertEqual((status, msg.get("Content-Type"), body), (want, "image/svg+xml", body_want), how)
                self.assertIn(SVG_DOCUMENT_POLICY, msg.get_all("Content-Security-Policy") or [], how)

    def test_every_remote_svg_answer_varies_on_the_deciding_headers(self):
        self._register("gpu1", self.fake.server_address[1])
        base = "/remote/gpu1/file?path=%2Ftmp%2Fchart.svg&sid=" + SID
        for how, headers, method in (("the page", {"Sec-Fetch-Dest": "document"}, "GET"),
                                     ("the bytes", {"Sec-Fetch-Dest": "image"}, "GET"),
                                     ("the HEAD", {}, "HEAD"),
                                     ("the 206", {"Range": "bytes=1-"}, "GET")):
            with self.subTest(how):
                _, _, msg = self._get_msg(base, method=method, headers=headers)
                self.assertEqual(msg.get_all("Vary"), [SVG_VARY], how)
        _, _, msg = self._get_msg("/remote/gpu1/file?path=%2Ftmp%2Fplot.png", headers={"Sec-Fetch-Dest": "document"})
        self.assertEqual(msg.get_all("Vary"), None, "a PNG varies on nothing")


if __name__ == "__main__":
    unittest.main()
