#!/usr/bin/env python3
"""The /file preview endpoint (the user 2026-07-08): chat path-thumbnails
load real bytes from `GET /file?path=…`, existence- and extension-gated.

Drives the REAL Handler over HTTP (the test_kernel_ws_auth.py pattern). Synthetic only — temp files,
no session state touched.
"""
import html
import os
import re
import tempfile
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

TOKEN = os.environ["ROMP_SERVE_TOKEN"]

# a 1x1 transparent PNG — real image bytes so the mime/type path is exercised end-to-end
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082")


class FilePreviewEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.png = os.path.join(cls.tmp.name, "plot.png")
        with open(cls.png, "wb") as f:
            f.write(PNG)
        cls.txt = os.path.join(cls.tmp.name, "notes.txt")
        with open(cls.txt, "w") as f:
            f.write("not renderable")
        # a synthetic SVG — XML on disk, but SERVED as an image (an <img> never runs its scripts)
        cls.svg = os.path.join(cls.tmp.name, "diagram.svg")
        with open(cls.svg, "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
        # a minimal synthetic PDF — the media contract's OTHER half (the viewer's isPdf branch)
        cls.pdf = os.path.join(cls.tmp.name, "report.pdf")
        with open(cls.pdf, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")
        # …and something served NEITHER as media nor as text, which is what "off the allowlist" means
        # now that source/text is ON it (2026-08-08 — see tests/test_file_view.py)
        cls.bin = os.path.join(cls.tmp.name, "archive.zip")
        with open(cls.bin, "wb") as f:
            f.write(b"PK\x03\x04not renderable, not text")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _req(self, path, method="GET", headers=None):
        url = "http://127.0.0.1:%d%s%stoken=%s" % (self.port, path, "&" if "?" in path else "?", TOKEN)
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_serves_an_existing_image_with_its_mime(self):
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.png))
        self.assertEqual(code, 200)
        self.assertEqual(hdrs.get("Content-Type"), "image/png")
        self.assertEqual(body, PNG)

    def test_a_pdf_is_served_inline_with_its_name_so_its_own_tab_is_titled_and_a_save_names_it(self):
        # a PDF opens in its OWN browser tab on a Cmd/Ctrl- or middle-click (ui/webview/preview.ts openPdfTab, the user 2026-09-06/07);
        # the browser titles that tab and names a Save from Content-Disposition — inline, never
        # attachment, so the tab renders it instead of downloading. Images carry none: an <img> reads
        # no disposition, and the header set they always had stays byte-for-byte.
        code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(self.pdf))
        self.assertEqual(code, 200)
        self.assertEqual(hdrs.get("Content-Type"), "application/pdf")
        self.assertEqual(hdrs.get("Content-Disposition"), 'inline; filename="report.pdf"')
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.pdf), method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(hdrs.get("Content-Disposition"), 'inline; filename="report.pdf"', "the probe agrees")
        self.assertEqual(body, b"")
        for p in (self.png, self.svg):
            code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(p))
            self.assertEqual(code, 200)
            self.assertIsNone(hdrs.get("Content-Disposition"), p)

    def test_an_oversize_pdf_navigated_to_in_its_own_tab_gets_a_page_with_the_download_as_the_way_out(self):
        # a modified click opens a PDF in its own tab, decided by extension inside the click — so a PDF over the cap lands
        # its whole tab on the 413, with no viewer around it to offer the Download button the in-pane path
        # used to (review find 2026-09-06). A refusal to render is never a dead end: a NAVIGATION
        # (Sec-Fetch-Dest: document) gets a page with the sentence and a link to the download half; a fetch,
        # an <iframe>/<img> load or a HEAD probe keeps the plain text they parse.
        big = os.path.join(self.tmp.name, "thesis <draft> & \"final\".pdf")
        with open(big, "wb") as f:
            f.truncate(km._MEDIA_MAX_BYTES + 1)           # sparse: no bytes written, the cap is on st_size
        try:
            sid = "11111111-2222-3333-4444-555555555555"
            qp = "/file?path=" + urllib.parse.quote(big) + "&sid=" + sid
            code, hdrs, body = self._req(qp, headers={"Sec-Fetch-Dest": "document"})
            self.assertEqual(code, 413)
            self.assertTrue(hdrs.get("Content-Type", "").startswith("text/html"), hdrs.get("Content-Type"))
            self.assertEqual(hdrs.get("X-Content-Type-Options"), "nosniff")
            page = body.decode("utf-8")
            self.assertIn("too large to show:", page)
            self.assertNotIn("<draft>", page, "the path is escaped — it names a file, never markup")
            self.assertIn("&lt;draft&gt; &amp; &quot;final&quot;.pdf", page)
            dq = urllib.parse.urlencode({"path": big, "download": "1", "sid": sid})
            self.assertIn('href="' + km._html_esc("/file?" + dq) + '"', page, "the way out: this route's download half, same path and sid")
            self.assertNotIn("<script", page.lower())
            # the same request without the navigation marker: the plain text the viewer's catch parses, unchanged
            code, hdrs, body = self._req(qp)
            self.assertEqual(code, 413)
            self.assertEqual(hdrs.get("Content-Type"), "text/plain")
            self.assertTrue(body.startswith(b"too large to show:"), body[:40])
            code, hdrs, body = self._req(qp, method="HEAD", headers={"Sec-Fetch-Dest": "document"})
            self.assertEqual((code, body), (413, b""), "a HEAD carries the verdict, never a page")
            # the lightbox's <iframe> fallback (popup blocked) is shown too, so it gets the page as well
            code, hdrs, body = self._req(qp, headers={"Sec-Fetch-Dest": "iframe"})
            self.assertEqual(code, 413)
            self.assertTrue(hdrs.get("Content-Type", "").startswith("text/html"), "an iframe load is shown, not parsed")
            self.assertIn('href="' + km._html_esc("/file?" + dq) + '"', body.decode("utf-8"))
            # Fetch Metadata rides only to trustworthy origins (https, localhost): a dashboard on plain http
            # sends no Sec-Fetch-Dest, so the Accept header decides — a navigation asks for text/html first
            # (review find on #959, 2026-09-07), a fetch() sends */* and keeps the text
            code, hdrs, body = self._req(qp, headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
            self.assertEqual(code, 413)
            self.assertTrue(hdrs.get("Content-Type", "").startswith("text/html"), "no Sec-Fetch-Dest, Accept text/html → the page")
            code, hdrs, body = self._req(qp, headers={"Accept": "*/*"})
            self.assertEqual((code, hdrs.get("Content-Type")), (413, "text/plain"), "a fetch() keeps the text")
            code, hdrs, body = self._req(qp, headers={"Sec-Fetch-Dest": "empty", "Accept": "text/html"})
            self.assertEqual((code, hdrs.get("Content-Type")), (413, "text/plain"), "a present non-shown dest wins over Accept")
            # an oversize IMAGE navigated to keeps the text — only a PDF can open in its own tab
            bigpng = os.path.join(self.tmp.name, "huge.png")
            with open(bigpng, "wb") as f:
                f.truncate(km._MEDIA_MAX_BYTES + 1)
            code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(bigpng), headers={"Sec-Fetch-Dest": "document"})
            self.assertEqual((code, hdrs.get("Content-Type")), (413, "text/plain"))
            os.unlink(bigpng)
        finally:
            os.unlink(big)

    def test_a_media_200_carries_its_mime_and_no_text_utf8_marker(self):
        # The viewer's media branches (ui/webview/file-view.ts) key on exactly this contract: a media
        # 200 wears its locally-derived mime — image/* for the isImage branch, application/pdf for
        # the isPdf one — and NOT the text pipeline's X-Romp-Text-Utf8 marker; that header belongs
        # to the text branch alone, and its absence tells the client no text decode happened. SVG is
        # the load-bearing image case: XML on disk, image on the wire, nosniff so the browser never
        # reinterprets it as a document. The PDF trio (mime + marker absence + nosniff) is what the
        # viewer's iframe arm believes without a client-side extension re-test.
        for p, mime in ((self.png, "image/png"), (self.svg, "image/svg+xml"),
                        (self.pdf, "application/pdf")):
            code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(p))
            self.assertEqual(code, 200)
            self.assertEqual(hdrs.get("Content-Type"), mime)
            self.assertIsNone(hdrs.get("X-Romp-Text-Utf8"),
                              "the text marker must never ride a media response")
            self.assertEqual(hdrs.get("X-Content-Type-Options"), "nosniff")
        code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(self.txt))
        self.assertEqual(code, 200)
        self.assertEqual(hdrs.get("X-Romp-Text-Utf8"), "1",
                         "…while the text branch carries its marker — the asymmetry is the signal")

    def _req_range(self, path, rng):
        url = "http://127.0.0.1:%d%s&token=%s" % (self.port, path, TOKEN)
        req = urllib.request.Request(url, headers={"Range": rng})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_a_suffix_range_resumes_mid_file(self):
        # the resumable preview retry (the user 2026-08-16, flaky wifi): bytes already received are
        # never re-sent — the client asks for the rest and stitches the picture across attempts
        code, hdrs, body = self._req_range("/file?path=" + urllib.parse.quote(self.png), "bytes=10-")
        self.assertEqual(code, 206)
        self.assertEqual(body, PNG[10:])
        self.assertEqual(hdrs.get("Content-Range"), "bytes 10-%d/%d" % (len(PNG) - 1, len(PNG)))
        self.assertEqual(hdrs.get("Content-Type"), "image/png")

    def test_a_range_past_the_end_416s_so_the_client_restarts(self):
        code, _, _ = self._req_range("/file?path=" + urllib.parse.quote(self.png), "bytes=%d-" % (len(PNG) + 5))
        self.assertEqual(code, 416)

    def test_a_non_suffix_range_is_served_whole(self):
        # only the one suffix form is honored; anything else means a plain 200 the client treats as a restart
        code, _, body = self._req_range("/file?path=" + urllib.parse.quote(self.png), "bytes=0-5")
        self.assertEqual(code, 200)
        self.assertEqual(body, PNG)

    def test_text_ignores_range(self):
        # the viewer slurps text; a range on it is served whole
        code, _, body = self._req_range("/file?path=" + urllib.parse.quote(self.txt), "bytes=3-")
        self.assertEqual(code, 200)
        self.assertEqual(body, b"not renderable")

    def test_missing_file_404s(self):
        # The 404 names its cause in one word, X-Romp-Reason (Slice 6 of plans/markdown-viewer.md, the PR review's
        # round 2): the viewer's focus HEAD reads a 404 as a deletion only for `missing`, the word for an absolute
        # path with no regular file at it; the GET body still names the resolved path, the HEAD has none.
        gone = os.path.join(self.tmp.name, "gone.png")
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(gone))
        self.assertEqual(code, 404)
        self.assertEqual(hdrs.get("X-Romp-Reason"), "missing")
        self.assertEqual(body, ("not found: %s" % km._tilde(gone)).encode("utf-8"))
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(gone), method="HEAD")
        self.assertEqual((code, body), (404, b""))
        self.assertEqual(hdrs.get("X-Romp-Reason"), "missing")

    def test_a_file_deleted_after_a_successful_get_heads_404_missing_for_a_tilde_path_too(self):
        # the viewer's shape: a GET showed the file, the disk lost it, the focus HEAD asks the same URL. A `~` path is
        # the person's own absolute path once expanded, so its 404 is `missing` like a bare absolute one's.
        doomed = os.path.join(self.tmp.name, "doomed.md")
        with open(doomed, "w") as f:
            f.write("# soon gone\n")
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(doomed), method="HEAD")
        self.assertEqual(code, 200)
        os.unlink(doomed)
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(doomed), method="HEAD")
        self.assertEqual((code, body), (404, b""))
        self.assertEqual(hdrs.get("X-Romp-Reason"), "missing")
        with mock.patch.dict(os.environ, {"HOME": self.tmp.name}):
            code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote("~/doomed.md"), method="HEAD")
        self.assertEqual(code, 404)
        self.assertEqual(hdrs.get("X-Romp-Reason"), "missing", "a ~ path expands to an absolute one: the file is gone")

    def test_a_relative_path_after_a_session_move_404s_as_relative_never_as_missing(self):
        # A relative path resolves against the session's CURRENT cwd, the names registry's second field, which a move
        # (the CLI's set_cwd, SdkBackend._finish_move) rewrites. The viewer showed `notes/todo.md` from the old cwd;
        # after the move the same path names a file that is not there, while the shown file still exists. The kernel
        # cannot tell that from a deletion, so the reason is `relative`, and the viewer keeps the deletion words for
        # `missing` alone (Slice 6 of plans/markdown-viewer.md, the PR review's round 2).
        sid = "11111111-2222-3333-4444-888888888888"      # a private synthetic sid: this test alone writes its entry
        old = os.path.join(self.tmp.name, "repo-a")
        new = os.path.join(self.tmp.name, "repo-b")
        os.makedirs(os.path.join(old, "notes"))
        os.makedirs(new)
        shown = os.path.join(old, "notes", "todo.md")
        with open(shown, "w") as f:
            f.write("- [ ] write the test\n")
        km.NAMES.mkdir(parents=True, exist_ok=True)
        entry = km.NAMES / sid
        qp = "/file?path=notes%2Ftodo.md&sid=" + sid
        try:
            entry.write_text("web\t%s\t\t\n" % old)
            code, hdrs, body = self._req(qp)
            self.assertEqual((code, body), (200, b"- [ ] write the test\n"))
            entry.write_text("web\t%s\t\t\n" % new)             # the move: the registry's cwd rewritten
            code, hdrs, body = self._req(qp, method="HEAD")
            self.assertEqual((code, body), (404, b""))
            self.assertEqual(hdrs.get("X-Romp-Reason"), "relative")
            self.assertTrue(os.path.isfile(shown), "the file the viewer shows is still on disk")
            code, hdrs, body = self._req(qp)
            self.assertEqual(code, 404)
            self.assertEqual(hdrs.get("X-Romp-Reason"), "relative")
            self.assertEqual(body, ("not found: %s" % km._tilde(os.path.join(new, "notes", "todo.md"))).encode("utf-8"),
                             "the GET body still names the path the kernel resolved, unchanged")
            # a relative path whose file really was deleted reads the same: the kernel does not certify a deletion
            # it cannot tell from a move
            entry.write_text("web\t%s\t\t\n" % old)
            os.unlink(shown)
            code, hdrs, _ = self._req(qp, method="HEAD")
            self.assertEqual(code, 404)
            self.assertEqual(hdrs.get("X-Romp-Reason"), "relative")
        finally:
            try:
                entry.unlink()
            except OSError:
                pass

    def test_an_absolute_path_the_kernel_cannot_stat_404s_as_unreadable_never_as_missing(self):
        # The route's isfile() swallows every OSError alike, so a file under a directory the kernel may not search
        # (EACCES on the parent) had read as `missing`, and the viewer said the file was deleted over a file that
        # exists (the PR review's round 3). `missing` is for ENOENT and ENOTDIR alone; any other stat failure is the
        # fourth word, `unreadable`, which the viewer reads like every word but `missing`: its change words, Reload
        # painting the kernel's own pane for what the GET answers. The kernel serves in this process, so the mode
        # the test takes off the directory is the mode the handler's stat meets.
        if os.geteuid() == 0:
            self.skipTest("EACCES cannot be produced as root: the search bit is never checked for uid 0")
        locked = os.path.join(self.tmp.name, "locked")
        os.mkdir(locked)
        kept = os.path.join(locked, "kept.md")
        with open(kept, "w") as f:
            f.write("# still here\n")
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(kept), method="HEAD")
        self.assertEqual(code, 200)
        self.addCleanup(os.chmod, locked, 0o700)      # tearDown restores the mode; the class's tmp dir is removed after
        os.chmod(locked, 0)
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(kept), method="HEAD")
        self.assertEqual((code, body), (404, b""))
        self.assertEqual(hdrs.get("X-Romp-Reason"), "unreadable")
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(kept))
        self.assertEqual(code, 404)
        self.assertEqual(hdrs.get("X-Romp-Reason"), "unreadable")
        self.assertEqual(body, ("not found: %s" % km._tilde(kept)).encode("utf-8"), "the GET body is as it was")
        os.chmod(locked, 0o700)
        self.assertTrue(os.path.isfile(kept), "the file the viewer shows was on disk the whole time")
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(kept), method="HEAD")
        self.assertEqual(code, 200, "with the directory searchable again the same URL serves the file")

    def test_missing_is_the_word_for_a_gone_path_or_parent_and_for_a_directory_at_the_name(self):
        # The other side of the round-3 line: `missing` stays the word when the stat says ENOENT (the file gone) or
        # ENOTDIR (a parent gone: a regular file stands where a directory was), when a directory stands at the name
        # (no regular file there), and for a path with a NUL byte, which no file can carry (the route must answer
        # it, not fall over: isfile() swallows the ValueError, and so does the reason).
        folder = os.path.join(self.tmp.name, "folder.md")
        os.mkdir(folder)
        for tag, given in (("ENOENT", os.path.join(self.tmp.name, "nowhere", "gone.md")),
                           ("ENOTDIR", os.path.join(self.txt, "inner.md")),
                           ("a directory at the name", folder),
                           ("a NUL byte", os.path.join(self.tmp.name, "odd\x00name.md"))):
            for method in ("GET", "HEAD"):
                code, hdrs, _ = self._req("/file?path=" + urllib.parse.quote(given), method=method)
                self.assertEqual(code, 404, (tag, method))
                self.assertEqual(hdrs.get("X-Romp-Reason"), "missing", (tag, method))

    def test_an_extension_on_neither_allowlist_415s_as_exists_but_unviewable(self):
        # the VIEW allowlist is renderable media PLUS source/text; a .zip is neither — but it EXISTS,
        # which is a different truth from 404's "no such file", and the client acts on the difference
        # (415 → offer the ?download=1 the route serves; 404 → nothing to offer). The user 2026-08-09.
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(self.bin))
        self.assertEqual(code, 415)

    def test_text_is_served_so_a_remote_dashboard_can_actually_show_it(self):
        # widened 2026-08-08: a file link is only followable if the bytes reach the browser, since the
        # kernel-side opener draws on the kernel's screen — the wrong machine when you are remote
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.txt))
        self.assertEqual(code, 200)
        self.assertTrue(hdrs.get("Content-Type", "").startswith("text/plain"), hdrs.get("Content-Type"))
        self.assertEqual(body, b"not renderable")

    def test_relative_path_without_sid_404s(self):
        # unresolvable relative path (no session cwd) must not fall back to the kernel's own cwd; its reason is
        # `unresolved`, not `missing`: nothing was looked up on disk, so the file is not known to be gone. The same
        # for a sid with no names entry.
        for qp in ("/file?path=plot.png", "/file?path=plot.png&sid=11111111-2222-3333-4444-777777777777"):
            code, hdrs, _ = self._req(qp)
            self.assertEqual(code, 404, qp)
            self.assertEqual(hdrs.get("X-Romp-Reason"), "unresolved", qp)
            code, hdrs, body = self._req(qp, method="HEAD")
            self.assertEqual((code, body), (404, b""), qp)
            self.assertEqual(hdrs.get("X-Romp-Reason"), "unresolved", qp)

    def test_oversize_413s_rather_than_truncating(self):
        old = km._MEDIA_MAX_BYTES
        km._MEDIA_MAX_BYTES = len(PNG) - 1
        try:
            code, _, _ = self._req("/file?path=" + urllib.parse.quote(self.png))
            self.assertEqual(code, 413)
        finally:
            km._MEDIA_MAX_BYTES = old

    def test_head_probe_reports_existence_without_the_bytes(self):
        # the client's PDF-chip probe: headers only (real Content-Length), no body download
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.png), method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(hdrs.get("Content-Length"), str(len(PNG)))
        self.assertEqual(body, b"")
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(self.bin), method="HEAD")
        self.assertEqual(code, 415, "HEAD carries the same exists-but-unviewable verdict as GET")

    def test_record_pin_a_latin1_text_file_is_served_re_encoded_with_the_utf8_marker_zero_and_its_head_carries_no_marker(self):
        # A record pin (plans/markdown-viewer.md, Slice 7, item 5): the viewer's line saying why Edit is off on such
        # a file rests on two header facts the route already had. A file that is not UTF-8 on disk is served through
        # _decode_text's latin-1 fallback, so the body is the text RE-ENCODED as UTF-8 (the byte E9 becomes C3 A9) with
        # X-Romp-Text-Utf8 "0", the value the viewer's verdict keys on; its HEAD carries no X-Romp-Text-Utf8 at all
        # (the header rides the text branch's GET alone), and its Content-Length is the size on disk, not the body's.
        lp = os.path.join(self.tmp.name, "legacy.log")
        with open(lp, "wb") as f:
            f.write(b"caf\xe9 line\n")
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(lp))
        self.assertEqual(code, 200)
        self.assertTrue(hdrs.get("Content-Type", "").startswith("text/plain"), hdrs.get("Content-Type"))
        self.assertEqual(body, "café line\n".encode("utf-8"), "the latin-1 decode, re-encoded as UTF-8 on the wire")
        self.assertEqual(body, b"caf\xc3\xa9 line\n")
        self.assertEqual(hdrs.get("X-Romp-Text-Utf8"), "0", "the decode branch travels with the text")
        self.assertEqual(hdrs.get("Content-Length"), str(len(body)))
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(lp), method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(body, b"")
        self.assertIsNone(hdrs.get("X-Romp-Text-Utf8"), "a HEAD decodes nothing, so it carries no marker")
        self.assertEqual(hdrs.get("Content-Length"), str(len(b"caf\xe9 line\n")), "the size on disk, one byte short of the GET's body")
        self.assertIsNotNone(hdrs.get("X-Romp-Mtime-Ns"))

    def test_record_pin_a_zero_byte_text_file_is_served_200_with_an_empty_body_and_the_utf8_marker(self):
        # A record pin (plans/markdown-viewer.md, Slice 7, item 6): the viewer's line saying a file is empty rests on
        # the route serving such a file as text, never as a refusal. A zero-byte .md answers 200 with an empty body,
        # X-Romp-Text-Utf8 "1" (b"" decodes as UTF-8) and Content-Length 0; its HEAD answers 200 with length 0.
        ep = os.path.join(self.tmp.name, "empty.md")
        with open(ep, "wb"):
            pass
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(ep))
        self.assertEqual(code, 200)
        self.assertEqual(body, b"")
        self.assertTrue(hdrs.get("Content-Type", "").startswith("text/plain"), hdrs.get("Content-Type"))
        self.assertEqual(hdrs.get("X-Romp-Text-Utf8"), "1")
        self.assertEqual(hdrs.get("Content-Length"), "0")
        self.assertIsNotNone(hdrs.get("X-Romp-Mtime-Ns"), "an empty file is a text landing like any other: Edit arms on it")
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(ep), method="HEAD")
        self.assertEqual((code, hdrs.get("Content-Length"), body), (200, "0", b""))


class FileDownloadEndpoint(unittest.TestCase):
    """/file?download=1 (the user 2026-08-09): anything on disk is downloadable — the view allowlists
    are a rendering choice, not a security boundary (the OS still guards execution, and the dashboard's
    owner can already read any file through an agent). Served as an attachment the browser saves, never
    interprets, and STREAMED so a multi-GB file cannot OOM the kernel that self-hosts the sessions."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        # NUL bytes up front: off both view allowlists AND would fail the text sniff — the exact
        # kind of file the download path exists for
        cls.blob = os.path.join(cls.tmp.name, "model.bin")
        cls.blob_bytes = b"\x00\x7fELF binary-ish payload\x00" * 40
        with open(cls.blob, "wb") as f:
            f.write(cls.blob_bytes)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _req(self, path, method="GET", headers=None):
        url = "http://127.0.0.1:%d%s%stoken=%s" % (self.port, path, "&" if "?" in path else "?", TOKEN)
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def test_an_off_allowlist_binary_downloads_as_an_attachment(self):
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.blob) + "&download=1")
        self.assertEqual(code, 200)
        self.assertEqual(body, self.blob_bytes)
        self.assertEqual(hdrs.get("Content-Type"), "application/octet-stream")
        self.assertEqual(hdrs.get("Content-Disposition"), 'attachment; filename="model.bin"')
        self.assertEqual(hdrs.get("Content-Length"), str(len(self.blob_bytes)))
        self.assertEqual(hdrs.get("X-Content-Type-Options"), "nosniff")

    def test_the_view_path_is_unchanged_without_the_param(self):
        # same file, no download=1 → the exists-but-unviewable 415, exactly as before this route
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(self.blob))
        self.assertEqual(code, 415)

    def test_a_missing_file_still_404s_naming_the_path(self):
        gone = os.path.join(self.tmp.name, "gone.bin")
        code, _, body = self._req("/file?path=" + urllib.parse.quote(gone) + "&download=1")
        self.assertEqual(code, 404)
        self.assertIn(km._tilde(gone).encode(), body, "every /file error names the resolved path")

    def test_the_text_cap_gates_the_view_but_not_the_download(self):
        big = os.path.join(self.tmp.name, "huge.log")
        data = b"x" * (km._TEXT_MAX_BYTES + 1)
        with open(big, "wb") as f:
            f.write(data)
        code, _, _ = self._req("/file?path=" + urllib.parse.quote(big))
        self.assertEqual(code, 413, "the VIEW keeps its cap")
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(big) + "&download=1")
        self.assertEqual(code, 200, "the download has none")
        self.assertEqual(len(body), len(data))
        self.assertEqual(hdrs.get("Content-Length"), str(len(data)))

    def test_head_reports_the_attachment_without_the_bytes(self):
        code, hdrs, body = self._req("/file?path=" + urllib.parse.quote(self.blob) + "&download=1",
                                     method="HEAD")
        self.assertEqual(code, 200)
        self.assertEqual(body, b"")
        self.assertEqual(hdrs.get("Content-Disposition"), 'attachment; filename="model.bin"')
        self.assertEqual(hdrs.get("Content-Length"), str(len(self.blob_bytes)))


class _StreamSink:
    def __init__(self, sink):
        self.sink = sink

    def write(self, b):
        self.sink.append(bytes(b))


class _DownloadRecorder:
    """Just enough Handler surface for a direct _file_download call: records every wfile.write, so the
    test can see the CHUNKING itself — the over-HTTP tests above only see the reassembled body."""

    def __init__(self):
        self.writes, self.headers, self.status = [], {}, None
        self.close_connection = False
        self.wfile = _StreamSink(self.writes)

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass

    _send = km.Handler._send      # the 404 path routes through the real _send, captured by the fakes


class DownloadStreams(unittest.TestCase):
    """The body is streamed in fixed chunks, never slurped. _send reads whole files into memory, and a
    multi-GB download through it would OOM the kernel — which self-hosts the very sessions using it.
    This pins the chunked WRITES, not just the reassembled bytes."""

    def test_the_body_arrives_as_bounded_chunks_never_one_slurp(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = os.path.join(tmp, "big.dat")
            data = bytes(range(256)) * ((3 * km._DOWNLOAD_CHUNK) // 256) + b"tail"
            with open(fp, "wb") as f:
                f.write(data)
            rec = _DownloadRecorder()
            km.Handler._file_download(rec, fp)
        self.assertEqual(rec.status, 200)
        self.assertGreater(len(rec.writes), 1, "one write means the file was slurped")
        self.assertTrue(all(len(w) <= km._DOWNLOAD_CHUNK for w in rec.writes),
                        "every write is bounded by the chunk size, whatever the file size")
        self.assertEqual(b"".join(rec.writes), data, "…and the chunks reassemble to the exact file")
        self.assertEqual(rec.headers.get("Content-Length"), str(len(data)))

    def test_a_file_truncated_mid_stream_closes_rather_than_hanging(self):
        # the promised Content-Length can no longer be honored → close, a visibly failed download
        rec = _DownloadRecorder()
        with tempfile.TemporaryDirectory() as tmp:
            fp = os.path.join(tmp, "shrinks.dat")
            with open(fp, "wb") as f:
                f.write(b"x" * 64)
            real_getsize = os.path.getsize
            with mock.patch.object(km.os.path, "getsize", lambda p: real_getsize(p) + 1000):
                km.Handler._file_download(rec, fp)
        self.assertTrue(rec.close_connection, "short bytes must close the connection, not hang it")


class AttachmentDisposition(unittest.TestCase):
    """The basename lands inside a header's quoted-string, so header-hostile characters are replaced;
    a mangled name also rides the RFC 5987 filename* form so capable browsers save the real one."""

    def test_a_plain_name_passes_through(self):
        self.assertEqual(km._attachment_disposition("model.bin"), 'attachment; filename="model.bin"')

    def test_header_hostile_characters_cannot_escape_the_quoted_string(self):
        d = km._attachment_disposition('a"b\\c\r\nSet-Cookie: x=y.bin')
        header_value = d.split("filename=")[1]
        self.assertNotIn("\r", d)
        self.assertNotIn("\n", d)
        self.assertNotIn('"', header_value[1:].split('"')[0], "no quote survives inside the quotes")
        self.assertIn('filename="a_b_c__Set-Cookie: x=y.bin"', d)

    def test_a_non_ascii_name_keeps_its_real_form_in_filename_star(self):
        d = km._attachment_disposition("données.csv")
        self.assertIn('filename="donn_es.csv"', d, "the ASCII fallback is mangled but present")
        self.assertIn("filename*=UTF-8''donn%C3%A9es.csv", d, "the real name rides RFC 5987")

    def test_an_empty_name_still_yields_a_usable_filename(self):
        self.assertIn('filename="download"', km._attachment_disposition(""))

# The policy every image/svg+xml success carries, written out here and never read from the kernel: a pin that
# compared the response with the kernel's own value would move with it (the 2026-09-23 policy, kernel.py
# _media_policy_headers).
SVG_DOCUMENT_POLICY = "sandbox; default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:"

# a synthetic SVG that carries the payload the hole is about: markup on disk, a page when a tab navigates
# to it, and its <script> would run wherever the document lands
SVG_WITH_SCRIPT = (b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
                   b'<script>document.title = "ran at the kernel origin"</script></svg>')


class SvgSandboxPolicy(unittest.TestCase):
    """An SVG on the media allowlist is ALSO a document: a tab that navigated to /file?path=x.svg parsed it
    as a page and ran its inline <script> at the kernel's origin. The own-tab opener (ui/webview/preview.ts
    openFileTab) hands the route ANY path on a modified click since the PDF-only gate came off, so an
    agent-written .svg gets there in one gesture (the 1204 review, 2026-09-10). nosniff cannot help: the
    type is declared, and image/svg+xml is the scriptable one. Since 2026-09-23 such a tab gets the
    image-mode page instead (SvgImageMode below), and the bytes keep SVG_DOCUMENT_POLICY on all three
    success shapes (200, HEAD, 206) as a second layer, for a road that still makes them a document:
    `sandbox` (a sandboxed document runs no script and has an opaque origin) and four fetch directives in
    the same value, because `sandbox` stops scripts and not loads. default-src 'none' refuses those
    fetches, and img-src data: blob:, style-src 'unsafe-inline' and font-src data: keep an exported
    figure's inline raster, styles and fonts. The pins compare the whole list of policies the response
    carries, so a weakened value (`sandbox allow-scripts`, a dropped directive, a host added) fails. An
    <img> load creates no document and reads no policy, so the chat's thumbnails, the viewer's inline
    preview and the lightbox keep rendering. Ordinary media and text carry no sandbox and no fetch
    directive."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.svg = os.path.join(cls.tmp.name, "chart.svg")
        with open(cls.svg, "wb") as f:
            f.write(SVG_WITH_SCRIPT)
        cls.png = os.path.join(cls.tmp.name, "plot.png")
        with open(cls.png, "wb") as f:
            f.write(PNG)
        cls.md = os.path.join(cls.tmp.name, "notes.md")
        with open(cls.md, "w") as f:
            f.write("# notes\n\nplain text, never a document with script\n")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _req(self, path, method="GET", headers=None):
        # returns the raw header MESSAGE, not a dict: a dict keeps one value per name, and the sandbox
        # policy rides BESIDE _send's frame-ancestors one under the same header name on the 200 branch
        url = "http://127.0.0.1:%d/file?path=%s&token=%s" % (self.port, urllib.parse.quote(path), TOKEN)
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    @staticmethod
    def _csp(msg):
        # every Content-Security-Policy header the response carries, joined: a browser enforces them all
        return "; ".join(msg.get_all("Content-Security-Policy") or [])

    def test_a_get_of_an_svg_is_a_sandboxed_document(self):
        code, msg, body = self._req(self.svg)
        self.assertEqual(code, 200)
        self.assertEqual(msg.get("Content-Type"), "image/svg+xml")
        self.assertEqual(body, SVG_WITH_SCRIPT, "the bytes are untouched: the policy, not a rewrite, disarms them")
        # the whole list, exactly: the document policy beside _send's framing policy, which still rides the 200
        self.assertEqual(sorted(msg.get_all("Content-Security-Policy") or []),
                         sorted([SVG_DOCUMENT_POLICY, "frame-ancestors 'self'"]), self._csp(msg))
        self.assertEqual(msg.get("X-Content-Type-Options"), "nosniff")

    def test_the_head_probe_carries_the_same_policy(self):
        code, msg, body = self._req(self.svg, method="HEAD")
        self.assertEqual((code, body), (200, b""))
        self.assertEqual(msg.get("Content-Type"), "image/svg+xml")
        self.assertEqual(msg.get_all("Content-Security-Policy") or [], [SVG_DOCUMENT_POLICY], self._csp(msg))   # the one policy, exactly

    def test_a_resumed_range_carries_the_same_policy(self):
        # the resumable retry's 206 is a response a tab can be handed too: the tail of the document
        code, msg, body = self._req(self.svg, headers={"Range": "bytes=1-"})
        self.assertEqual(code, 206)
        self.assertEqual(body, SVG_WITH_SCRIPT[1:])
        self.assertEqual(msg.get("Content-Range"), "bytes 1-%d/%d" % (len(SVG_WITH_SCRIPT) - 1, len(SVG_WITH_SCRIPT)))
        self.assertEqual(msg.get("Content-Type"), "image/svg+xml")
        self.assertEqual(msg.get_all("Content-Security-Policy") or [], [SVG_DOCUMENT_POLICY], self._csp(msg))   # the one policy, exactly

    def test_ordinary_media_and_text_carry_no_sandbox(self):
        # a PNG is never a document; text is served as text/plain, which never executes — neither is sandboxed,
        # so a policy meant for SVG cannot leak onto the viewer's other branches (its fetch directives included)
        for method, headers in (("GET", None), ("HEAD", None), ("GET", {"Range": "bytes=1-"})):
            code, msg, _ = self._req(self.png, method=method, headers=headers)
            self.assertIn(code, (200, 206), (method, headers))
            self.assertNotIn("sandbox", self._csp(msg), (method, headers, self._csp(msg)))
            self.assertNotIn("default-src", self._csp(msg), (method, headers, self._csp(msg)))
        code, msg, _ = self._req(self.md)
        self.assertEqual(code, 200)
        self.assertTrue(msg.get("Content-Type", "").startswith("text/plain"), msg.get("Content-Type"))
        self.assertNotIn("sandbox", self._csp(msg), self._csp(msg))
        self.assertNotIn("default-src", self._csp(msg), self._csp(msg))


# The image-mode page's policy and the Vary every svg answer carries, written out like SVG_DOCUMENT_POLICY above
# (kernel.py _SVG_IMAGE_PAGE_POLICY and _SVG_VARY), and the Accept values two engines send: Firefox's navigation and
# image load, which carry text/html and do not.
SVG_IMAGE_PAGE_POLICY = ("sandbox allow-same-origin; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
                         "base-uri 'none'; form-action 'none'")
SVG_VARY = "Sec-Fetch-Dest, Accept"
NAV_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
IMG_ACCEPT = "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"


class SvgImageMode(unittest.TestCase):
    """Image mode (2026-09-23, kernel.py _svg_image_page and _svg_as_document): a request that would make an svg a
    DOCUMENT gets a small page that holds the file in an <img> of the same route with raw=1, since an svg drawn as an
    image loads nothing external and the policy on the bytes cannot stop every load a document makes (a data: SVG paint
    document's @import in Firefox, a preconnect in WebKit: tests/test_svg_tab_policy_browser.py). Sec-Fetch-Dest decides
    when present (document, iframe, frame, object, embed, fencedframe); without it an Accept naming text/html does, the
    road of a dashboard on plain http, which sends no Sec-Fetch-* header. Every other request keeps today's bytes and
    headers, and every svg answer, page or bytes, carries Vary on the two deciding headers. The page is built from the
    parsed query: the path, sid and pin, never the token, every value escaped. The relay's arm is
    tests/test_kernel_remote_file_relay.py's."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.svg = os.path.join(cls.tmp.name, "chart.svg")
        with open(cls.svg, "wb") as f:
            f.write(SVG_WITH_SCRIPT)
        cls.odd = os.path.join(cls.tmp.name, 'q"><b>x&y.svg')   # a file name that is markup, for the page's escaping
        with open(cls.odd, "wb") as f:
            f.write(SVG_WITH_SCRIPT)
        cls.png = os.path.join(cls.tmp.name, "plot.png")
        with open(cls.png, "wb") as f:
            f.write(PNG)
        cls.md = os.path.join(cls.tmp.name, "notes.md")
        with open(cls.md, "w") as f:
            f.write("# notes\n\nplain text\n")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _req(self, path, headers=None, method="GET", extra=""):
        url = "http://127.0.0.1:%d/file?path=%s&sid=%s&token=%s%s" % (
            self.port, urllib.parse.quote(path, safe=""), "11111111-2222-3333-4444-555555555555", TOKEN, extra)
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def _img(self, body):
        """The page's <img> sources, unescaped: the page runs no script, so its markup is what the browser loads."""
        return [html.unescape(m) for m in re.findall(r'<img\b[^>]*\bsrc="([^"]*)"', body.decode("utf-8"))]

    def _assert_page(self, code, msg, body, where, path=None, pin=None):
        path = self.svg if path is None else path
        self.assertEqual((code, msg.get("Content-Type")), (200, "text/html; charset=utf-8"),
                         "%s: the image-mode page, not the svg as a document" % where)
        self.assertEqual(sorted(msg.get_all("Content-Security-Policy") or []), sorted([SVG_IMAGE_PAGE_POLICY, "frame-ancestors 'self'"]),
                         "%s: the page's policy beside _send's framing one, exactly" % where)
        self.assertEqual(msg.get_all("Vary"), [SVG_VARY], where)
        self.assertEqual(msg.get("Cache-Control"), "no-cache", where)
        self.assertEqual(msg.get("X-Content-Type-Options"), "nosniff", where)
        self.assertNotIn(b"<script", body, "%s: the svg's markup never reaches the page" % where)
        self.assertNotIn(TOKEN.encode(), body, "%s: the page carries no token" % where)
        self.assertNotIn(b"token", body, where)
        srcs = self._img(body)
        self.assertEqual(len(srcs), 1, "%s: one <img>: %r" % (where, srcs))
        u = urllib.parse.urlsplit(srcs[0])
        want = {"path": [path], "sid": ["11111111-2222-3333-4444-555555555555"], "raw": ["1"]}
        if pin:
            want["pin"] = [pin]
        self.assertEqual((u.scheme, u.netloc, u.path, urllib.parse.parse_qs(u.query)), ("", "", "/file", want),
                         "%s: the <img> reads this route for the same path, sid and pin, plus raw=1: %r" % (where, srcs[0]))

    def test_a_request_that_makes_the_svg_a_document_gets_the_page(self):
        for how, headers, extra in (
                ("a navigation (Sec-Fetch-Dest document)", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}, ""),
                ("a navigation to the raw=1 URL: raw is no way around the page", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}, "&raw=1"),
                ("a plain-http navigation (no Sec-Fetch-Dest, text/html Accept)", {"Accept": NAV_ACCEPT}, ""),
                ("an iframe", {"Sec-Fetch-Dest": "iframe", "Accept": NAV_ACCEPT}, ""),
                ("a frame", {"Sec-Fetch-Dest": "frame"}, ""),
                ("an object", {"Sec-Fetch-Dest": "object"}, ""),
                ("an embed", {"Sec-Fetch-Dest": "embed"}, ""),
                ("a fenced frame", {"Sec-Fetch-Dest": "fencedframe"}, "")):
            with self.subTest(how):
                code, msg, body = self._req(self.svg, headers, extra=extra)
                self._assert_page(code, msg, body, how)

    def test_the_page_escapes_the_name_and_carries_the_pin(self):
        code, msg, body = self._req(self.odd, {"Sec-Fetch-Dest": "document"})
        self._assert_page(code, msg, body, "a file name that is markup", path=self.odd)
        self.assertIn(b"<title>q&quot;&gt;&lt;b&gt;x&amp;y.svg</title>", body, "the title is the escaped basename")
        self.assertNotIn(b'"><b>', body, "no markup of the name's own reaches the page")
        pin = "0" * 64 + ".svg"      # shape-valid; no blob behind it, so the live file answers, as for an evicted pin
        code, msg, body = self._req(self.svg, {"Sec-Fetch-Dest": "document"}, extra="&pin=" + pin)
        self._assert_page(code, msg, body, "a pinned mention", pin=pin)

    def test_every_other_request_keeps_the_svg_bytes(self):
        # the controls: what the page's <img>, the viewer's fetch, the chip's HEAD, a Range retry and curl get, unchanged
        # but for Vary (pinned on its own below)
        for how, headers, method, want in (
                ("an image load", {"Sec-Fetch-Dest": "image", "Accept": IMG_ACCEPT}, "GET", 200),
                ("an image load with a navigation's Accept: the destination decides", {"Sec-Fetch-Dest": "image", "Accept": NAV_ACCEPT}, "GET", 200),
                ("a fetch()", {"Sec-Fetch-Dest": "empty", "Accept": "*/*"}, "GET", 200),
                ("a plain-http image load", {"Accept": IMG_ACCEPT}, "GET", 200),
                ("a plain-http fetch()", {"Accept": "*/*"}, "GET", 200),
                ("no headers at all (curl)", {}, "GET", 200),
                ("a HEAD a navigation would send", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}, "HEAD", 200),
                ("a Range retry", {"Sec-Fetch-Dest": "image", "Range": "bytes=1-"}, "GET", 206)):
            with self.subTest(how):
                code, msg, body = self._req(self.svg, headers, method=method)
                self.assertEqual((code, msg.get("Content-Type")), (want, "image/svg+xml"), how)
                self.assertEqual(body, {"HEAD": b"", "GET": SVG_WITH_SCRIPT[1:] if want == 206 else SVG_WITH_SCRIPT}[method], how)
                self.assertIn(SVG_DOCUMENT_POLICY, msg.get_all("Content-Security-Policy") or [], "%s: the bytes keep their policy" % how)

    def test_every_svg_answer_varies_on_the_deciding_headers(self):
        for how, headers, method in (("the page", {"Sec-Fetch-Dest": "document"}, "GET"),
                                     ("the bytes", {"Sec-Fetch-Dest": "image"}, "GET"),
                                     ("the HEAD", {}, "HEAD"),
                                     ("the 206", {"Range": "bytes=1-"}, "GET")):
            with self.subTest(how):
                _, msg, _ = self._req(self.svg, headers, method=method)
                self.assertEqual(msg.get_all("Vary"), [SVG_VARY], how)

    def test_no_other_type_gets_a_page_or_a_vary(self):
        # a PNG is never a document; text is served as text/plain; a missing svg is the 404 prose
        nav = {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}
        for how, path, want, ctype in (("a PNG", self.png, 200, "image/png"),
                                       ("a markdown file", self.md, 200, "text/plain; charset=utf-8"),
                                       ("a missing svg", os.path.join(self.tmp.name, "gone.svg"), 404, "text/plain")):
            with self.subTest(how):
                code, msg, _ = self._req(path, nav)
                self.assertEqual((code, msg.get("Content-Type"), msg.get_all("Vary")), (want, ctype, None), how)


if __name__ == "__main__":
    unittest.main()
