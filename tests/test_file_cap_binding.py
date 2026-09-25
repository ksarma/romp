#!/usr/bin/env python3
"""A /file cap binds to exactly one (host, path, sid) (kernel/kernel.py _authorize, _file_cap).

A header-less /file load (an image, a PDF, a download) cannot send the X-Romp-Key header, so its URL
carries a per-file CAP instead: an HMAC under the session's page key of exactly the (host, path, sid)
the URL names, presented WITH the session cookie. This pins that the cap authenticates that one file
and no other: a different path, sid or host, or a differently-spelled path that resolves to the same
file (a trailing slash, a dot segment, a double slash, a symlink to it), each needs its own cap and
this one does not validate for it; and a cap made under another sign-in is refused beside this
sign-in's session cookie. The positive path (the cap for the exact spelling, with the cookie) is
served.

Green here; red under a mutant that drops the (host, path, sid) binding from the cap, and under one
that keys the cap by the serve token instead of the sign-in's page key. A URL that names the path, the
sid or the cap twice is refused rather than left to which occurrence each reader takes, and the download
link of the page an oversize PDF's own tab gets carries the request's cap, locally and through the relay.
Synthetic only: an invented serve token, files under a temp dir, no session state touched. No cap,
session id or key VALUE is printed.
"""
import html
import os
import re
import socket
import threading
import unittest
import urllib.request
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
km = load_source("romp_kernel_filecap", os.path.join(BIN, "romp-kernel"))

CN = km._SESSION_COOKIE
SESS = km._mint_session()
SID = "11111111-2222-3333-4444-555555555555"
SID2 = "99999999-8888-7777-6666-555555555555"


def _q(s):
    return urllib.parse.quote(s, safe="")


class CapBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.dir = tempfile.mkdtemp(prefix="cap-")
        cls.target = os.path.join(cls.dir, "target.png")
        with open(cls.target, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nsynthetic")
        cls.link = os.path.join(cls.dir, "link.png")
        try:
            os.symlink(cls.target, cls.link)
            cls.have_symlink = True
        except OSError:
            cls.have_symlink = False

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        import shutil
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _file_status(self, path, sid=None, cap=None, host="", download=False, sess=None):
        """GET a local /file (host="") or /remote/<host>/file with the session cookie (SESS unless
        `sess` names another sign-in's session) and the given cap; return the status. A 403 is an auth
        refusal; anything else means the cap authorized."""
        base = "/file" if not host else "/remote/%s/file" % _q(host)
        url = base + "?path=" + _q(path)
        if sid is not None:
            url += "&sid=" + _q(sid)
        if download:
            url += "&download=1"
        if cap is not None:
            url += "&cap=" + cap
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, url))
        req.add_header("Cookie", "%s=%s" % (CN, sess or SESS))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def _cap(self, path, sid, host=""):
        return km._file_cap(SESS, host, path, sid)

    def _get(self, target):
        """GET a raw /file target with the session cookie: (status, body)."""
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, target))
        req.add_header("Cookie", "%s=%s" % (CN, SESS))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_a_second_path_sid_or_cap_is_refused(self):
        # The cap binds one (host, path, sid) and the route resolves the first path and sid it reads, so a URL that
        # names any of the three twice is refused: whichever occurrence the gate and the resolver each took, a cap
        # for one file never reads another file's bytes.
        other = os.path.join(self.dir, "other.png")
        with open(other, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nthe-other-file")
        cap = self._cap(self.target, SID)
        t, o, sid, sid2 = _q(self.target), _q(other), _q(SID), _q(SID2)
        for target in ("/file?path=%s&path=%s&sid=%s&cap=%s" % (t, o, sid, cap),
                       "/file?path=%s&path=%s&sid=%s&cap=%s" % (o, t, sid, cap),
                       "/file?path=%s&sid=%s&sid=%s&cap=%s" % (t, sid, sid2, cap),
                       "/file?path=%s&sid=%s&cap=%s&cap=%s" % (t, sid, cap, cap)):
            status, body = self._get(target)
            shape = re.sub(r"=[^&]*", "=", target)      # the parameter names alone, for the message
            self.assertEqual(status, 403, "a repeated term is refused: %s" % shape)
            self.assertNotIn(b"the-other-file", body, "and no other file's bytes: %s" % shape)
        # a blank first value is no second value: parse_qs drops it, and the cap for the one path left serves
        self.assertEqual(self._get("/file?path=&path=%s&sid=%s&cap=%s" % (t, sid, cap))[0], 200)

    def test_a_cap_made_under_another_sign_in_is_refused(self):
        # the cap is an HMAC under the page key of the sign-in that made it, so it serves only beside
        # that sign-in's session cookie: another sign-in's cap for the very same (host, path, sid) is
        # refused, and the same cap serves beside its own sign-in's cookie (so the refusal is the binding)
        other = km._mint_session()
        cap = km._file_cap(other, "", self.target, SID)
        self.assertEqual(self._file_status(self.target, SID, cap), 403,
                         "a cap made under another sign-in is refused beside this sign-in's cookie")
        self.assertEqual(self._file_status(self.target, SID, cap, sess=other), 200,
                         "the same cap serves beside the cookie of the sign-in that made it")

    def test_the_exact_cap_with_the_cookie_serves_the_file(self):
        cap = self._cap(self.target, SID)
        self.assertEqual(self._file_status(self.target, SID, cap), 200, "the bound cap serves the file")

    def test_a_cap_without_the_cookie_is_refused(self):
        cap = self._cap(self.target, SID)
        req = urllib.request.Request("http://127.0.0.1:%d/file?path=%s&sid=%s&cap=%s"
                                     % (self.port, _q(self.target), _q(SID), cap))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                st = r.status
        except urllib.error.HTTPError as e:
            st = e.code
        self.assertEqual(st, 403, "a cap alone, without the session cookie, is refused")

    def test_a_cap_for_another_path_is_refused(self):
        other = os.path.join(self.dir, "other.png")
        cap = self._cap(other, SID)                       # a cap bound to a DIFFERENT path
        self.assertEqual(self._file_status(self.target, SID, cap), 403)

    def test_a_cap_for_another_sid_is_refused(self):
        cap = self._cap(self.target, SID2)                # a cap bound to a different sid
        self.assertEqual(self._file_status(self.target, SID, cap), 403)

    def test_a_cap_for_another_host_is_refused(self):
        cap_local = self._cap(self.target, SID, host="")  # a LOCAL cap on the remote route
        self.assertEqual(self._file_status(self.target, SID, cap_local, host="gpu1"), 403)
        cap_remote = self._cap(self.target, SID, host="gpu1")  # a REMOTE cap on the local route
        self.assertEqual(self._file_status(self.target, SID, cap_remote, host=""), 403)

    def test_the_correct_remote_host_cap_passes_the_gate(self):
        cap_remote = self._cap(self.target, SID, host="gpu1")
        # no host is attached, so the relay answers 404 (detached); the point is it is NOT a 403
        self.assertNotEqual(self._file_status(self.target, SID, cap_remote, host="gpu1"), 403)

    def test_a_cap_for_a_trailing_slash_spelling_is_refused(self):
        cap = self._cap(self.target, SID)
        self.assertEqual(self._file_status(self.target + "/", SID, cap), 403)

    def test_a_cap_for_a_dot_segment_spelling_is_refused(self):
        alt = os.path.join(self.dir, ".", "target.png")   # resolves to the same file, different string
        cap = self._cap(self.target, SID)
        self.assertEqual(self._file_status(alt, SID, cap), 403)

    def test_a_cap_for_a_double_slash_spelling_is_refused(self):
        alt = self.target.replace("/target.png", "//target.png")
        cap = self._cap(self.target, SID)
        self.assertEqual(self._file_status(alt, SID, cap), 403)

    def test_a_cap_for_a_symlink_to_the_file_is_refused(self):
        if not self.have_symlink:
            self.skipTest("no symlink support here")
        cap = self._cap(self.target, SID)                 # the target's cap
        self.assertEqual(self._file_status(self.link, SID, cap), 403, "does not validate for the symlink path")
        # the symlink's OWN cap serves it (same file, its own name): the cap binds the name, not the inode
        self.assertEqual(self._file_status(self.link, SID, self._cap(self.link, SID)), 200)

    def test_the_cap_covers_head_range_and_download(self):
        cap = self._cap(self.target, SID)
        # HEAD with the bound cap
        req = urllib.request.Request("http://127.0.0.1:%d/file?path=%s&sid=%s&cap=%s"
                                     % (self.port, _q(self.target), _q(SID), cap), method="HEAD")
        req.add_header("Cookie", "%s=%s" % (CN, SESS))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                head_status = r.status
        except urllib.error.HTTPError as e:
            head_status = e.code
        self.assertEqual(head_status, 200, "the cap covers HEAD")
        # download with the same cap
        self.assertEqual(self._file_status(self.target, SID, cap, download=True), 200, "the cap covers download")

    def test_a_cap_for_a_percent_encoded_dot_segment_is_refused(self):
        # the URL layer percent-DECODES `path` before both the cap check and the file resolution, so a
        # spelling that decodes to a dot-segment (%2E between slashes) resolves to the same file but is a
        # different decoded string; the plain cap does not validate for it. This exercises percent-
        # decoding, distinct from the already-covered literal dot-segment spelling.
        cap = self._cap(self.target, SID)
        d, base = os.path.dirname(self.target), os.path.basename(self.target)
        raw = ("/file?path=" + _q(d) + "%2F%2E%2F" + _q(base) + "&sid=" + _q(SID) + "&cap=" + cap)
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, raw))
        req.add_header("Cookie", "%s=%s" % (CN, SESS))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                st = r.status
        except urllib.error.HTTPError as e:
            st = e.code
        self.assertEqual(st, 403, "a percent-encoded dot-segment spelling needs its own cap")

    def test_a_cap_on_a_non_file_route_is_refused(self):
        # the cap query is read on the file class only; on a JSON route the cookie alone is not enough
        cap = self._cap(self.target, SID)
        req = urllib.request.Request("http://127.0.0.1:%d/sessions?cap=%s" % (self.port, cap))
        req.add_header("Cookie", "%s=%s" % (CN, SESS))
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                st = r.status
        except urllib.error.HTTPError as e:
            st = e.code
        self.assertEqual(st, 403)


class SharedCapVectors(unittest.TestCase):
    """The cap derivation (an injective length-prefixed input, HMAC-SHA256 under the page key, the
    first 16 bytes, base64url with no padding) is pinned to the SAME constant as ui/webview/file-cap.ts
    through tests/fixtures/file-cap-vectors.json, so the two implementations cannot drift."""

    def test_the_kernel_matches_the_shared_cross_language_vectors(self):
        import json as _json
        vec = _json.load(open(os.path.join(HERE, "fixtures", "file-cap-vectors.json")))
        self.assertTrue(vec["caps"], "the vector file has cases")
        for row in vec["caps"]:
            got = km._hmac_b64(vec["key"], km._cap_input(row["host"], row["path"], row["sid"]), 16)
            self.assertEqual(got, row["cap"], "the cap for %r drifted from the shared vector" % (row["path"],))

    def test_file_cap_is_the_page_key_over_the_injective_input(self):
        # tie _file_cap to that same algorithm at run time, so no page key is committed to the fixture
        sess = km._mint_session()
        for h, p, s in (("", "/x/y.png", "sid1"), ("gpu1", "/a b/ç.pdf", "sid2")):
            self.assertTrue(km._file_cap(sess, h, p, s) == km._hmac_b64(km._page_key(sess), km._cap_input(h, p, s), 16),
                            "the cap for %r is the page key over the injective input" % p)

    def test_the_input_is_injective_across_field_boundaries(self):
        self.assertNotEqual(km._cap_input("a", "bc", "d"), km._cap_input("ab", "c", "d"))
        self.assertNotEqual(km._cap_input("a\x00b", "c", "d"), km._cap_input("a", "b\x00c", "d"))


class PinContentAddressing(unittest.TestCase):
    """The cap leaves `pin` outside its MAC because a pin id NAMES its content (the sha256 of the
    bytes), so a cap plus a pin id reveals only content whose hash the holder already has. This pins the
    premise: the id a mention mints is sha256(bytes)+ext, stored under that name, and the route's id
    shape admits nothing else."""

    def test_a_pin_id_is_the_sha256_of_the_content_stored_under_that_name(self):
        import hashlib
        import shutil
        raw = b"\x89PNG\r\n\x1a\n" + os.urandom(64)
        d = tempfile.mkdtemp(prefix="pinc-")
        self.addCleanup(lambda: shutil.rmtree(d, ignore_errors=True))
        f = os.path.join(d, "img.png")
        with open(f, "wb") as fh:
            fh.write(raw)
        pid = km._pin_mention(f)
        self.assertEqual(pid, hashlib.sha256(raw).hexdigest() + ".png", "the id is sha256(content)+ext")
        self.assertTrue((km._pin_dir() / pid).is_file(), "the blob is stored under its content hash")
        self.assertIsNotNone(km._PIN_ID_RE.match(pid), "the route's id shape admits it")

    def test_the_pin_id_shape_admits_only_a_hex_hash_and_extension(self):
        self.assertIsNone(km._PIN_ID_RE.match("../etc/passwd"), "no traversal")
        self.assertIsNone(km._PIN_ID_RE.match("not-a-hash.png"), "not a sha256")
        self.assertIsNone(km._PIN_ID_RE.match("a" * 64), "a bare hash with no extension")
        self.assertIsNotNone(km._PIN_ID_RE.match("a" * 64 + ".png"), "a hash and its extension")
        self.assertIsNone(km._PIN_ID_RE.match("a" * 64 + ".png\n"), "nothing after the extension, a newline included")


class _PeerFile(BaseHTTPRequestHandler):
    """A peer kernel's /file, as far as the relay's oversize-PDF page needs one: the view of big.pdf is its own
    413 prose, the download half answers the bytes. Every request is recorded."""
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).seen.append(self.path)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        if q.get("download") == ["1"]:
            body, status, ctype = b"%PDF-1.4\nsynthetic", 200, "application/octet-stream"
        else:
            body, status, ctype = b"too large to show: /tmp/big.pdf (95.4 MB, limit 47.7 MB)", 413, "text/plain"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class WayOutLinkCarriesTheCap(unittest.TestCase):
    """The page an oversize PDF's own tab gets links the download half of the same route, and that link is a
    /file URL the kernel builds: it carries the cap the request presented, locally and through the relay (which
    strips the browser's cap before calling the peer and restores it for the page), so following it with the
    session cookie downloads the file."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.dir = tempfile.mkdtemp(prefix="cap413-")
        cls.big = os.path.join(cls.dir, "big.pdf")
        with open(cls.big, "wb") as f:
            f.truncate(km._MEDIA_MAX_BYTES + 1)          # sparse: past the view cap, no bytes written
        _PeerFile.seen = []
        cls.peer = ThreadingHTTPServer(("127.0.0.1", 0), _PeerFile)
        threading.Thread(target=cls.peer.serve_forever, daemon=True).start()
        cls._saved = dict(km._remotes)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": cls.peer.server_address[1],
                                       "token": "row-" + "token-" + "testhost", "status": "up"}

    @classmethod
    def tearDownClass(cls):
        with km._remotes_lock:
            km._remotes.clear()
            km._remotes.update(cls._saved)
        for s in (cls.srv, cls.peer):
            s.shutdown()
            s.server_close()
        import shutil
        shutil.rmtree(cls.dir, ignore_errors=True)

    def _nav(self, target):
        """A navigation (Sec-Fetch-Dest: document) with the session cookie: (status, body)."""
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, target),
                                     headers={"Cookie": "%s=%s" % (CN, SESS), "Sec-Fetch-Dest": "document"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                status, body = r.status, b""
                while True:                                  # the local download is 50 MB of zeros: read and drop
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    body = body or chunk[:256]
                return status, body
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def _link(self, page):
        m = re.search(r'href="([^"]+)"', page.decode("utf-8"))
        self.assertIsNotNone(m, "the page links a way out")
        return html.unescape(m.group(1))

    def _check(self, route, host, path):
        cap = km._file_cap(SESS, host, path, SID)
        status, page = self._nav("%s?path=%s&sid=%s&cap=%s" % (route, _q(path), _q(SID), cap))
        self.assertEqual(status, 413, "%s: the oversize PDF's own tab gets the way-out page" % route)
        link = self._link(page)
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
        self.assertEqual(urllib.parse.urlsplit(link).path, route, "the link is the same route's download half")
        self.assertEqual(q.get("download"), ["1"])
        self.assertTrue(q.get("cap") == [cap], "%s: the download link carries the request's own cap" % route)
        self.assertEqual(self._nav(link)[0], 200, "%s: following it with the session cookie downloads the file" % route)

    def test_the_local_way_out_link_carries_the_cap(self):
        self._check("/file", "", self.big)

    def test_the_relays_way_out_link_carries_the_cap_and_the_peer_never_sees_it(self):
        _PeerFile.seen = []
        self._check("/remote/TESTHOST/file", "TESTHOST", "/tmp/big.pdf")
        self.assertEqual(len(_PeerFile.seen), 2, "the peer was asked for the view, then the download")
        for path in _PeerFile.seen:
            self.assertNotIn("cap", urllib.parse.parse_qs(urllib.parse.urlsplit(path).query), "the browser's cap never reaches the peer")


if __name__ == "__main__":
    unittest.main()
