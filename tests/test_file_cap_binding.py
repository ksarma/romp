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
that keys the cap by the serve token instead of the sign-in's page key (see build-checklist.md).
Synthetic only: an invented serve token, files under a temp dir, no session state touched. No cap,
session id or key VALUE is printed.
"""
import os
import socket
import threading
import unittest
import urllib.request
import urllib.error
import urllib.parse
from http.server import ThreadingHTTPServer
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
    """B11: the cap derivation (an injective length-prefixed input, HMAC-SHA256 under the page key, the
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
            self.assertEqual(km._file_cap(sess, h, p, s),
                             km._hmac_b64(km._page_key(sess), km._cap_input(h, p, s), 16))

    def test_the_input_is_injective_across_field_boundaries(self):
        self.assertNotEqual(km._cap_input("a", "bc", "d"), km._cap_input("ab", "c", "d"))
        self.assertNotEqual(km._cap_input("a\x00b", "c", "d"), km._cap_input("a", "b\x00c", "d"))


class PinContentAddressing(unittest.TestCase):
    """B12: the cap leaves `pin` outside its MAC because a pin id NAMES its content (the sha256 of the
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


if __name__ == "__main__":
    unittest.main()
