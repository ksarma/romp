#!/usr/bin/env python3
"""The bundle staleness scans must read vendor/ — the fourth root the served bundles are built from
(the review of plans/file-review.md Slice 1, 2026-09-06).

ui/webview/anchor-map.ts imports vendor/track-changents/engine.js, so the render, feed and files
bundles carry the vendored engine. Both staleness scans — _bundle_inputs (the boot-time
_ensure_bundles check) and _dist_src_newest (the T119 converge check) — read only ui/,
vscode-extension/src and esbuild.js, so a re-vendor or a new patch under vendor/track-changents/patches/
that changed engine.js with nothing under ui/ touched marked nothing stale: a restart found dist
current, every browser kept the old anchor algorithm, and the host script (which loads engine.js from
disk) ran the new one — the panel and the host disagreeing on where a comment sits, with nothing on
screen saying why. The same class as the three recurrences _bundle_inputs's docstring records.

Two kinds of pin. The requirement DERIVED from the sources: every vendor import a webview module makes
must resolve to a watched file, so the next vendored module is covered the day it is imported. And the
two scans driven over a SYNTHETIC checkout where ONLY a vendored file is newer than dist, with the
control case (a vendored file older than dist) proving the harness can tell the difference. The
synthetic checkout relocates UI, CHAT_VIEW, DIST and ROOT to a temp dir, the tests/test_dist_converge.py
idiom; the vendor tree follows UI (_vendor_tree), which is what keeps that suite hermetic too.
Synthetic paths in a temp dir only."""
import glob
import os
import re
import tempfile
import time
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE any romp code loads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_bundle_vendor", os.path.join(BIN, "romp-kernel")).load_module()

# the import shapes esbuild follows out of ui/webview into vendor/: an ES import and a require()
_VENDOR_IMPORT_RE = re.compile(r'''(?:from\s+|import\s+|require\()\s*["'](\.\./\.\./vendor/[^"']+)["']''')


class VendorImportsAreWatched(unittest.TestCase):
    """Derived from the sources, not a hand-written list: every ../../vendor/... a webview module
    imports must be a file the boot-time scan reads, and the vendor tree must be where the converge
    scan looks."""

    def setUp(self):
        self.web = os.path.join(ROOT, "ui", "webview")
        self.imports = set()
        for ts in glob.glob(os.path.join(self.web, "*.ts")):
            if ts.endswith(".test.ts"):
                continue
            with open(ts, encoding="utf-8") as f:
                self.imports.update(_VENDOR_IMPORT_RE.findall(f.read()))

    def test_the_derivation_still_sees_the_known_case(self):
        self.assertTrue(any(p.endswith("/engine.js") for p in self.imports),
                        "anchor-map.ts imports the vendored engine — the scan of the sources went stale")

    def test_every_vendored_module_the_webview_imports_is_a_bundle_input(self):
        watched = {str(p) for p in km._bundle_inputs(km.ROOT / "vscode-extension")}
        for rel in sorted(self.imports):
            resolved = os.path.normpath(os.path.join(self.web, rel))
            self.assertTrue(os.path.isfile(resolved), "%s is imported but does not exist" % rel)
            self.assertIn(resolved, watched,
                          "%s is bundled into the webview but the staleness check never looks at it, so a "
                          "re-vendor or a new patch would ship dark through every kernel restart" % rel)

    def test_the_vendor_tree_is_the_checkouts_and_follows_ui(self):
        self.assertEqual(km._vendor_tree(), km.ROOT / "vendor", "in production the vendor tree is ROOT/vendor")
        saved = km.UI
        try:
            km.UI = Path("/synthetic/checkout/ui")
            self.assertEqual(km._vendor_tree(), Path("/synthetic/checkout/vendor"),
                             "a relocated UI relocates the vendor tree with it — what keeps the dist-converge "
                             "tests' synthetic checkout hermetic")
        finally:
            km.UI = saved

    def test_the_converge_scan_reads_the_vendored_module(self):
        # the real checkout: the newest input is at least as new as the vendored engine, and the scan
        # accepts its suffix — the synthetic test below proves the vendored file alone can move it
        engine = next(p for p in self.imports if p.endswith("/engine.js"))
        st = os.stat(os.path.normpath(os.path.join(self.web, engine)))
        self.assertGreaterEqual(km._dist_src_newest(), st.st_mtime)


class _SyntheticCheckout(unittest.TestCase):
    """A checkout in a temp dir: ui/webview/render.ts, vendor/track-changents/engine.js,
    vscode-extension/{src/extension.ts, esbuild.js, node_modules/, dist/render.js}. Every source is
    OLDER than dist except where a test says otherwise, so a rebuild verdict is the vendored file's."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self._saved = (km.ROOT, km.UI, km.CHAT_VIEW, km.DIST)
        km.ROOT = td
        km.UI = td / "ui"
        km.CHAT_VIEW = td / "vscode-extension"
        km.DIST = km.CHAT_VIEW / "dist"
        for d in (km.UI / "webview", td / "vendor" / "track-changents", km.CHAT_VIEW / "src",
                  km.CHAT_VIEW / "node_modules", km.DIST):
            d.mkdir(parents=True)
        self.now = time.time()
        self.render_ts = self._file(km.UI / "webview" / "render.ts", "export {};", age=300)
        self.ext_ts = self._file(km.CHAT_VIEW / "src" / "extension.ts", "export {};", age=300)
        self.esbuild = self._file(km.CHAT_VIEW / "esbuild.js", "// build", age=300)
        self.engine = self._file(td / "vendor" / "track-changents" / "engine.js", "module.exports = {};", age=300)
        self.dist = self._file(km.DIST / "render.js", "(()=>{})();", age=200)

    def tearDown(self):
        (km.ROOT, km.UI, km.CHAT_VIEW, km.DIST) = self._saved
        self.td.cleanup()

    def _file(self, p, text, age):
        p.write_text(text)
        t = self.now - age
        os.utime(p, (t, t))
        return p

    def _touch(self, p, age):
        t = self.now - age
        os.utime(p, (t, t))


class TheBootScanSeesAVendoredChange(_SyntheticCheckout):
    """_ensure_bundles, with the build call recorded instead of run."""

    def setUp(self):
        super().setUp()
        self.builds = []
        real = km.subprocess

        def fake_run(argv, **kw):
            self.builds.append(list(argv))
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        km.subprocess = types.SimpleNamespace(run=fake_run, TimeoutExpired=real.TimeoutExpired,
                                              CalledProcessError=real.CalledProcessError)
        self._real_subprocess = real

    def tearDown(self):
        km.subprocess = self._real_subprocess
        super().tearDown()

    def test_a_vendored_file_newer_than_dist_alone_triggers_the_rebuild(self):
        self._touch(self.engine, age=100)                # the re-vendor: engine.js moved, nothing under ui/ did
        km._ensure_bundles()
        self.assertEqual(len(self.builds), 1, "the vendored engine is a bundle input: dist is stale")
        self.assertEqual(self.builds[0][:2], ["node", "esbuild.js"])

    def test_a_vendored_file_older_than_dist_leaves_dist_alone(self):
        km._ensure_bundles()                             # the control: every source predates dist
        self.assertEqual(self.builds, [])

    def test_a_ui_change_still_triggers_it(self):
        self._touch(self.render_ts, age=100)             # the harness tells a real staleness from none
        km._ensure_bundles()
        self.assertEqual(len(self.builds), 1)


class TheConvergeScanSeesAVendoredChange(_SyntheticCheckout):
    """_dist_src_newest and _dist_converge_check (T119), with the rebuild recorded instead of run."""

    def setUp(self):
        super().setUp()
        self._saved2 = (km._rebuild_dist, km._sync_notice)
        self.rebuilds, self.notices = [], []

        def fake_rebuild():
            self.rebuilds.append(1)
            fresh = time.time() + 5
            os.utime(self.dist, (fresh, fresh))
            return True, ""
        km._rebuild_dist = fake_rebuild
        km._sync_notice = lambda text, ok=True: self.notices.append((ok, text))
        km._DIST_CONVERGE_TRIED[0] = 0.0

    def tearDown(self):
        (km._rebuild_dist, km._sync_notice) = self._saved2
        km._DIST_CONVERGE_TRIED[0] = 0.0
        super().tearDown()

    def test_the_newest_input_is_the_vendored_file_when_it_alone_moved(self):
        self._touch(self.engine, age=100)
        self.assertAlmostEqual(km._dist_src_newest(), os.stat(self.engine).st_mtime, places=3)

    def test_a_vendored_file_newer_than_dist_alone_rebuilds_in_place(self):
        self._touch(self.engine, age=100)
        km._dist_converge_check()
        self.assertEqual(len(self.rebuilds), 1, "the served bundles predate the vendored engine they carry")
        self.assertTrue(self.notices and self.notices[0][0] is True)

    def test_a_vendored_file_older_than_dist_is_no_staleness(self):
        km._dist_converge_check()                        # the control
        self.assertEqual(self.rebuilds, [])
        self.assertEqual(self.notices, [])

    def test_a_vendored_mjs_counts_too(self):
        # store-io.mjs is node-only today, but the scan reads the whole tree: a bundled .mjs tomorrow is
        # covered the day it is imported, and the cost of the widening is one extra esbuild run
        mjs = self._file(Path(self.td.name) / "vendor" / "track-changents" / "store-io.mjs", "export {};", age=100)
        self.assertAlmostEqual(km._dist_src_newest(), os.stat(mjs).st_mtime, places=3)


if __name__ == "__main__":
    unittest.main()
