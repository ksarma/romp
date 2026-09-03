#!/usr/bin/env python3
"""Static bundles carry a validator and a gzip, so `no-cache` can do the revalidation it asks for.

The bundles were served with Cache-Control: no-cache and NO ETag/Last-Modified. no-cache means
"revalidate", but with nothing to revalidate against the browser had no conditional to send, so every
dashboard open re-downloaded the whole of dist — measured at 2.2MB uncompressed (render.js alone 773,663
bytes), and the server offered no compression at any Accept-Encoding. Over a tailnet that was the load time.

The freshness rule is deliberately unchanged: the tag is (mtime_ns, size), which moves on every rebuild
exactly like the ?v= stamp the urls carry, so a same-name rebuild still can never serve a stale body.
Synthetic only — files this test writes itself."""
import gzip as gziplib
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # isolate: importing the kernel must not touch live state
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
km = SourceFileLoader("romp_kernel_dist_etag", os.path.join(BIN, "romp-kernel")).load_module()

JS = (b"// a bundle-shaped blob that gzips like real code\n"
      b"function render(state){return state.sessions.map(function(s){return s.name;});}\n" * 400)


class DistBody(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        km._dist_body_cache.clear()

    def _write(self, name, data):
        p = self.dir / name
        p.write_bytes(data)
        return p

    def test_plain_when_the_client_offers_no_gzip(self):
        p = self._write("render.js", JS)
        body, enc, tag = km._dist_body(p, "")
        self.assertEqual(body, JS)
        self.assertEqual(enc, "")
        self.assertTrue(tag.startswith('"') and tag.endswith('"'), tag)

    def test_gzip_when_offered_and_it_round_trips(self):
        p = self._write("render.js", JS)
        body, enc, tag = km._dist_body(p, "gzip, br")
        self.assertEqual(enc, "gzip")
        self.assertEqual(gziplib.decompress(body), JS, "the compressed body must be the same asset")
        self.assertLess(len(body), len(JS) // 2, "a code-shaped bundle should compress well past 2x")

    def test_the_two_forms_carry_different_etags(self):
        p = self._write("render.js", JS)
        _, _, plain_tag = km._dist_body(p, "")
        _, _, gz_tag = km._dist_body(p, "gzip")
        self.assertNotEqual(plain_tag, gz_tag,
                            "one etag across both encodings lets a cache hand a gzip body to a client "
                            "that never asked for one")

    def test_the_etag_moves_when_the_file_changes(self):
        p = self._write("render.js", JS)
        _, _, first = km._dist_body(p, "")
        p.write_bytes(JS + b"// rebuilt\n")
        os.utime(p, (1, 1))                      # a rebuild that also moves mtime
        _, _, second = km._dist_body(p, "")
        self.assertNotEqual(first, second, "a rebuild must invalidate — this IS the no-cache guarantee")

    def test_a_rebuilt_file_serves_the_new_bytes(self):
        p = self._write("render.js", JS)
        km._dist_body(p, "gzip")                 # prime the cache
        p.write_bytes(b"// totally different\n" * 200)
        body, enc, _ = km._dist_body(p, "gzip")
        self.assertEqual(gziplib.decompress(body), p.read_bytes(), "the cache must not pin the old body")

    def test_small_files_are_not_compressed(self):
        p = self._write("tiny.js", b"var a=1;\n")
        body, enc, _ = km._dist_body(p, "gzip")
        self.assertEqual(enc, "", "under the floor the framing costs more than it saves")
        self.assertEqual(body, b"var a=1;\n")

    def test_already_compressed_types_are_not_recompressed(self):
        for name in ("logo.png", "font.woff2", "font.ttf"):
            p = self._write(name, os.urandom(4096))
            _, enc, _ = km._dist_body(p, "gzip")
            self.assertEqual(enc, "", "%s is already compressed" % name)

    def test_the_gzip_is_made_once_per_version(self):
        p = self._write("render.js", JS)
        first, _, _ = km._dist_body(p, "gzip")
        second, _, _ = km._dist_body(p, "gzip")
        self.assertIs(first, second, "the kernel is one process for every pane — compress once, not per request")

    def test_a_compression_failure_still_serves_the_asset(self):
        p = self._write("render.js", JS)
        saved = km.gzip.compress
        km.gzip.compress = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            km._dist_body_cache.clear()
            body, enc, _ = km._dist_body(p, "gzip")
        finally:
            km.gzip.compress = saved
        self.assertEqual(enc, "", "fail toward serving the bundle, never toward a broken dashboard")
        self.assertEqual(body, JS)


class RouteWiring(unittest.TestCase):
    """The /dist route's half of the contract, asserted on the source the way the judge-billing tests do:
    a conditional request must answer 304, and both responses must carry the tag and Vary."""

    def setUp(self):
        with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
            self.src = f.read()

    def test_the_route_answers_a_matching_conditional_with_304(self):
        self.assertIn('if (self.headers.get("If-None-Match") or "") == tag:', self.src)
        self.assertIn('return self._send(304, b"", ct + "; charset=utf-8", cache="no-cache", headers=hdrs)',
                      self.src)

    def test_both_responses_carry_the_validator_and_vary(self):
        self.assertIn('hdrs = {"ETag": tag, "Vary": "Accept-Encoding"}', self.src)

    def test_no_cache_is_retained(self):
        # the point is to make revalidation cheap, NOT to let a tab run a stale bundle
        self.assertIn('cache="no-cache", headers=hdrs)', self.src)


if __name__ == "__main__":
    unittest.main()
