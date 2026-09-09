"""The bundle staleness check must watch every directory the bundles are BUILT FROM (the user
2026-08-08).

The bug: the check scanned only `vscode-extension/src`, but the browser UI is built from
`ui/webview` — where render.ts and styles.css live. So an edit there left `dist/render.js` stale and
the kernel served yesterday's dashboard, with the source correct and pushed the whole time. It
surfaced as a fast-mode badge that stayed blue in the chat while the timeline's star went orange: the
timeline pane is served VERBATIM from `ui/romp-timeline-view.js`, so it needed no build, while the
chat comes from dist and did.

It hid behind luck. Any change that happened to also touch `vscode-extension/src` — a test file was
enough — rebuilt everything, so the trigger looked like it worked.

These tests assert the check's inputs against esbuild.js's ACTUAL entry points, so a new entry point
added there without a matching watch root fails here rather than silently never shipping."""
import fnmatch
import os
import shutil
import tempfile
import re
import unittest
from pathlib import Path
from romp_load import load_source

import lab_dist   # the served labs' build harness (tests/lab_dist.py); the parity and token pins at the end read it

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE any romp code loads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_bundle", os.path.join(BIN, "romp-kernel"))


class BundleInputs(unittest.TestCase):
    def setUp(self):
        self.cv = km.ROOT / "vscode-extension"
        self.inputs = [str(p) for p in km._bundle_inputs(self.cv)]

    def test_the_shared_webview_sources_are_watched(self):
        # the regression: render.ts + styles.css live here, NOT under vscode-extension/src
        for name in ("render.ts", "styles.css"):
            self.assertTrue(any(p.endswith("ui/webview/" + name) for p in self.inputs),
                            "ui/webview/%s must be watched — the chat bundle is built from it" % name)

    def test_the_extension_source_is_still_watched(self):
        self.assertTrue(any(p.endswith("src/extension.ts") for p in self.inputs))

    def test_the_inlined_timeline_view_is_watched(self):
        # not under either directory, but timeline-main.ts inlines it, so editing it staleness the bundle
        self.assertTrue(any(p.endswith("ui/romp-timeline-view.js") for p in self.inputs))

    def test_webview_js_modules_required_by_the_bundles_are_watched(self):
        """The third recurrence (2026-08-09): gear.js is a plain-JS module feed.ts require()s into the
        chat bundle — not an esbuild entry point, so the entry-point-derived test below never saw it,
        and a gear-only change (the Fast judging checkbox) shipped dark through a kernel restart.
        Derive the requirement from the sources: every ./x.js a webview module require()s must be
        watched, so the next required js module is covered the day it is added."""
        import glob
        web = os.path.join(ROOT, "ui", "webview")
        mods = set()
        for ts in glob.glob(os.path.join(web, "*.ts")):
            mods.update(re.findall(r'require\("\./([\w-]+\.js)"\)', open(ts).read()))
        self.assertIn("gear.js", mods, "the require() scan went stale — gear.js is the known case")
        for m in sorted(mods):
            self.assertTrue(any(p.endswith("ui/webview/" + m) for p in self.inputs),
                            "ui/webview/%s is bundled via require() but the staleness check never "
                            "looks at it, so editing it would not trigger a rebuild" % m)

    def test_every_esbuild_entry_point_is_covered_by_a_watch_root(self):
        """The check is only as good as its list — so derive the requirement from the BUILD, not from
        a second hand-written list that can drift out of step with it."""
        src = open(os.path.join(ROOT, "vscode-extension", "esbuild.js")).read()
        # only the literal entryPoints ARRAYS — esbuild.js also mentions ".test.ts" in the unit-test
        # bundler's filter, which is not an entry point and must not be mistaken for one
        blocks = re.findall(r"entryPoints:\s*(\[[^\]]*\])", src)
        entries = [e for b in blocks for e in re.findall(r'"((?:\.\./)?[\w./-]+\.(?:ts|css))"', b)]
        self.assertTrue(entries, "found no entry points to check against — the regex went stale")
        watched = set(self.inputs)
        for e in entries:
            resolved = os.path.normpath(os.path.join(str(self.cv), e))
            self.assertIn(resolved, watched,
                          "esbuild builds %s but the staleness check never looks at it, so editing "
                          "it would not trigger a rebuild" % e)


class ServedLabsKeyTheSameInputs(unittest.TestCase):
    """tests/lab_dist.py keys the served labs' one build of dist on the sources it derives from esbuild.js
    (entry points, then the trees their relative imports reach), not on this list. The two must agree at
    the file level: an input the kernel would rebuild for that the labs' key does not cover leaves them
    asserting against stale bundles with nothing saying so. Here, where the kernel is already loaded under
    isolation, every path _bundle_inputs reads is checked against the harness's keyed set."""

    def test_every_kernel_bundle_input_is_keyed_by_the_served_labs_build(self):
        cv = km.ROOT / "vscode-extension"
        keyed = {os.path.realpath(p) for p in lab_dist.default()._input_files()}
        self.assertGreater(len(keyed), 100, "the harness keyed a real tree")
        missing = sorted(str(p) for p in km._bundle_inputs(cv) if os.path.realpath(str(p)) not in keyed)
        self.assertEqual(missing, [], "bundle inputs the kernel rebuilds for that tests/lab_dist.py does not key")


class HarnessFilesDoNotMoveTheCacheBustToken(unittest.TestCase):
    """tests/lab_dist.py keeps its lock and marker INSIDE dist, and writes the marker through a staging name
    there too. The kernel's _dist_ver token is the newest mtime over dist's bundles (`*.js` in its code; its
    docstring names `*.css` too), appended to every script and link url, so a harness file the glob counted
    would make every served lab run change the token the dashboard's clients see. Pinned by RUNNING the
    kernel's token over a temp dist: the three harness names, rewritten after the bundle, leave it where
    the bundle put it, and the control (a newer bundle) moves it, so a token that ignored dist entirely
    (the function returns 0 on a missing dir) cannot pass by accident."""

    def setUp(self):
        self.td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.td, True)
        self._saved = km.DIST
        km.DIST = Path(self.td)
        self.addCleanup(setattr, km, "DIST", self._saved)
        self.bundle = os.path.join(self.td, "render.js")
        with open(self.bundle, "w") as f:
            f.write("(()=>{})();")
        self.t0 = 1_700_000_000
        os.utime(self.bundle, (self.t0, self.t0))

    def test_the_lock_the_marker_and_the_markers_staging_name_leave_the_token_alone(self):
        self.assertEqual(km._dist_ver(), self.t0, "the token is the bundle's mtime (nonzero: dist is read)")
        names = [lab_dist.LOCK_NAME, lab_dist.MARKER_NAME, ".%s.tmp-%d-0" % (lab_dist.MARKER_NAME.lstrip("."), os.getpid())]
        for name in names:
            for suffix in ("*.js", "*.css"):
                self.assertFalse(fnmatch.fnmatchcase(name, suffix), "%s matches the token's glob %s" % (name, suffix))
            path = os.path.join(self.td, name)
            with open(path, "w") as f:
                f.write("x\n")
            os.utime(path, (self.t0 + 600, self.t0 + 600))    # newer than the bundle, as a real run leaves them
        self.assertEqual(km._dist_ver(), self.t0, "a harness file newer than the bundle does not move the token")
        os.utime(self.bundle, (self.t0 + 60, self.t0 + 60))     # the control: a rebuilt bundle moves it
        self.assertEqual(km._dist_ver(), self.t0 + 60)


if __name__ == "__main__":
    unittest.main()
