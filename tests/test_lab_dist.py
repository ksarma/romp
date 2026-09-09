#!/usr/bin/env python3
"""tests/lab_dist.py owns the served labs' build of vscode-extension/dist (2026-09-09).

The race it retires: two served-lab classes on two xdist workers each ran `node esbuild.js` into the one
dist and copied it, and a copy that listed dist during the other build's staging phase failed on staging
names (`.pdf-worker.js.tmp-<pid>-<n>`) that were renamed away before it reached them. The properties
pinned here, against a synthetic checkout and a fake builder that stages and renames the way esbuild.js
does (holding the staging window open long enough to matter):
  1. concurrent callers produce ONE build, and every caller's copy is a complete, single-build dist;
  2. a copy waits for a held lock, and the copy itself runs INSIDE the lock, not after it;
  3. a marker that names the current inputs skips the build; a changed input, a removed dist, a dependency
     change, a build by another command or a change of build command rebuilds; the marker records the key
     computed BEFORE the build, so a source edited mid-build is caught by the next call;
  4. the inputs are derived from esbuild.js (entry points in both forms, then the trees their relative
     imports reach), the dist being built is left out at the top level only, and on the real config the
     derivation yields the kernel's trees (tests/test_kernel_bundle_staleness.py pins file-level parity);
  5. a build that fails skips the caller (the served labs' standing behaviour) and leaves no marker; a
     build that exceeds its bound fails loudly, releases the lock, and the bound is the kernel's;
  6. the copy leaves out a staging file the harness did not write, and survives a staged builder running
     outside the lock (the defence-in-depth half);
  7. the lock and the marker are left out of a VSIX (.vscodeignore) and of git (.gitignore);
  8. no test module builds or copies dist on its own any more (a text ratchet over tests/*.py).
Hermetic: the fake checkout lives under the run's temp root and no real esbuild runs. Synthetic names only.
"""
import fcntl
import fnmatch
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL = os.path.join(ROOT, "kernel", "kernel.py")

# The fake builder: appends its pid to builds.log, then writes every output to a hidden staging sibling
# (`.<name>.tmp-<pid>-<n>`, esbuild.js's shape), holds that window open for FAKE_HOLD seconds, and renames
# each over its served name. Every output carries the same build id so a copy that mixed two builds shows.
# `--production` writes a shorter render.js that says so, the way the real flag minifies. Exits 1 when a
# `fail` file sits beside it.
FAKE_BUILDER = r'''
import os, sys, time, random
ext = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(ext, "fail")):
    sys.stderr.write("fake esbuild: refusing to build\n")
    sys.exit(1)
dist = os.path.join(ext, "dist")
os.makedirs(os.path.join(dist, "fonts"), exist_ok=True)
build_id = "%d-%06d" % (os.getpid(), random.randrange(10 ** 6))
mode = "production" if "--production" in sys.argv else "dev"
with open(os.path.join(ext, "builds.log"), "a") as f:
    f.write(build_id + "\n")
outputs = {"render.js": "// render " + build_id + " mode=" + mode + "\n" + "x" * (1024 if mode == "production" else 4096),
           "styles.css": "/* styles " + build_id + " */\n" + "y" * 4096,
           os.path.join("fonts", "a.woff2"): "font " + build_id}
staged = []
for n, (name, body) in enumerate(outputs.items()):
    final = os.path.join(dist, name)
    tmp = os.path.join(os.path.dirname(final), "." + os.path.basename(final) + ".tmp-%d-%d" % (os.getpid(), n))
    with open(tmp, "w") as f:
        f.write(body)
    staged.append((tmp, final))
time.sleep(float(os.environ.get("FAKE_HOLD", "0")))
for tmp, final in staged:
    os.replace(tmp, final)
'''

CALLER = r'''
import sys
sys.path.insert(0, %(here)r)
import lab_dist
b = lab_dist.DistBuild(ext=%(ext)r, cmd=[sys.executable, "fake_esbuild.py"], inputs=[(%(src)r, True)])
b.copy_to(%(dest)r)
'''

_ID = re.compile(r"(\d+-\d{6})")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def _read(path):
    with open(path) as f:
        return f.read()


def _bump(path):
    """A second newer, whatever the clock: the changed-input idiom (an edit inside one mtime tick is still a change)."""
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


def _flock_waiters(path):
    """The /proc/locks lines of tasks blocked on the flock of `path` (the `->` lines under its holder), or
    None where /proc/locks cannot be read. A waiter is the kernel's own word that a caller is in flock."""
    try:
        ino = os.stat(path).st_ino
        with open("/proc/locks") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    return [l for l in lines if "->" in l and " FLOCK " in l and l.split()[-3].endswith(":%d" % ino)]


class _Checkout(unittest.TestCase):
    """A synthetic checkout: one source tree, one extension dir with the fake builder."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lab-dist-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.src = os.path.join(self.root, "ui")
        os.makedirs(os.path.join(self.src, "webview"))
        self.source = os.path.join(self.src, "webview", "render.ts")
        _write(self.source, "export const a = 1;\n")
        self.ext = os.path.join(self.root, "ext")
        os.makedirs(self.ext)
        _write(os.path.join(self.ext, "fake_esbuild.py"), FAKE_BUILDER)
        self.log = os.path.join(self.ext, "builds.log")
        self.build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "fake_esbuild.py"],
                                        inputs=[(self.src, True)])

    def builds(self):
        try:
            with open(self.log) as f:
                return [l.strip() for l in f if l.strip()]
        except OSError:
            return []

    def dist_file(self, rel):
        return _read(os.path.join(self.build.dist, rel))

    def assert_complete_copy(self, dest):
        """Every output present, every byte from one build, nothing of the staging or the harness."""
        names = sorted(os.listdir(dest))
        self.assertEqual(names, ["fonts", "render.js", "styles.css"], "a served copy holds the outputs only: %r" % names)
        self.assertEqual(os.listdir(os.path.join(dest, "fonts")), ["a.woff2"])
        ids = set()
        for rel in ("render.js", "styles.css", os.path.join("fonts", "a.woff2")):
            m = _ID.search(_read(os.path.join(dest, rel)))
            self.assertIsNotNone(m, "%s is whole" % rel)
            ids.add(m.group(1))
        return ids


class OneBuildShared(_Checkout):

    def test_concurrent_callers_produce_one_build_and_complete_copies(self):
        """Four processes call copy_to at once on an unbuilt dist. The staging window is held open for
        half a second, so without the lock the later callers would copy through it (or list staging
        names that vanish, the original failure). With it: one line in builds.log, four copies each
        holding every output from that one build."""
        dests = [os.path.join(self.root, "lab%d" % i, "dist") for i in range(4)]
        env = dict(os.environ, FAKE_HOLD="0.5")
        procs = [subprocess.Popen([sys.executable, "-c", CALLER % dict(here=HERE, ext=self.ext, src=self.src, dest=d)],
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) for d in dests]
        for p in procs:
            out, _ = p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0, out)
        self.assertEqual(len(self.builds()), 1, "one build for four callers: %r" % self.builds())
        ids = set()
        for d in dests:
            ids |= self.assert_complete_copy(d)
        self.assertEqual(ids, set(self.builds()), "every copy is the one build")
        self.assertEqual(self.build.read_marker(), self.build.key(), "the marker names the inputs the build read")
        self.assertIn(lab_dist.LOCK_NAME, os.listdir(self.build.dist))

    def test_two_threads_in_one_process_share_the_build(self):
        """The lock is per open file description, so two threads of one process exclude each other too
        (a threading lock would not reach another xdist worker; this checks the file lock covers both)."""
        os.environ["FAKE_HOLD"] = "0.3"
        self.addCleanup(os.environ.pop, "FAKE_HOLD", None)
        dests = [os.path.join(self.root, "t%d" % i, "dist") for i in range(3)]
        errors = []

        def run(d):
            try:
                lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs).copy_to(d)
            except Exception as e:      # noqa: BLE001  surfaced below
                errors.append(e)
        threads = [threading.Thread(target=run, args=(d,)) for d in dests]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        self.assertEqual(errors, [])
        self.assertEqual(len(self.builds()), 1)
        for d in dests:
            self.assert_complete_copy(d)

    def test_a_copy_waits_for_a_held_lock(self):
        """The test holds the lock; a copy started meanwhile does not run until it is released. The wait is
        observed, not timed: /proc/locks lists the copy's thread as a waiter on the lock file (the deadline
        on that observation is the failure bound, never the assertion)."""
        self.build.ensure_built()
        lock = os.path.join(self.build.dist, lab_dist.LOCK_NAME)
        if _flock_waiters(lock) is None:
            self.skipTest("/proc/locks is not readable here, so a waiter is not observable")
        fd = os.open(lock, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        dest = os.path.join(self.root, "lab", "dist")
        done = threading.Event()

        def copy():
            self.build.copy_to(dest)
            done.set()
        t = threading.Thread(target=copy)
        t.start()
        try:
            deadline = time.monotonic() + 30
            while not _flock_waiters(lock) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(_flock_waiters(lock), "the copy is blocked in flock on the harness lock")
            self.assertFalse(done.is_set(), "no copy runs while the lock is held elsewhere")
            self.assertFalse(os.path.exists(dest), "nothing of the copy exists while the lock is held")
        finally:
            os.close(fd)                    # releases the lock
        t.join(30)
        self.assertTrue(done.is_set(), "the copy completes once the lock is released")
        self.assert_complete_copy(dest)

    def test_the_copy_itself_runs_under_the_lock(self):
        """copytree runs INSIDE the lock, not after it. While a copy is listing dist (copytree parked on its
        first call), a non-blocking flock from a fresh descriptor is refused, so the lock is held by the
        copy; a builder that arrives meanwhile waits, so the copy carries the earlier build whole and the
        later build lands after it. Moving copytree below the `with self.locked()` block fails the probe."""
        self.build.ensure_built()
        parked, release = threading.Event(), threading.Event()
        real = shutil.copytree
        first = [True]

        def parking(*a, **kw):              # copytree recurses through the module name with 7 positional args
            if first[0]:
                first[0] = False
                parked.set()
                release.wait(30)            # failure bound only; the test releases it
            return real(*a, **kw)
        dest = os.path.join(self.root, "lab", "dist")
        errors, result = [], []

        def copy():
            try:
                self.build.copy_to(dest)
            except Exception as e:          # noqa: BLE001  surfaced below
                errors.append(e)
        with patch.object(lab_dist.shutil, "copytree", parking):
            t = threading.Thread(target=copy)
            t.start()
            self.assertTrue(parked.wait(30), "the copy started")
            fd = os.open(os.path.join(self.build.dist, lab_dist.LOCK_NAME), os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError, msg="the copy holds the lock while it lists dist"):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)
            _write(self.source, "export const a = 2;\n")
            _bump(self.source)
            b = threading.Thread(target=lambda: result.append(self.build.ensure_built()))
            b.start()                       # a builder arriving mid-copy: it waits for the copy
            release.set()
            t.join(30)
            b.join(30)
        self.assertEqual(errors, [])
        self.assertFalse(t.is_alive() or b.is_alive(), "both finished")
        self.assertEqual(result, [True], "the builder built once the copy released the lock")
        self.assertEqual(len(self.builds()), 2)
        self.assertEqual(self.assert_complete_copy(dest), {self.builds()[0]}, "the copy is the first build, whole")


class MarkerKeysOnInputs(_Checkout):

    def test_matching_marker_skips_and_a_changed_input_rebuilds(self):
        self.assertTrue(self.build.ensure_built(), "an unbuilt dist builds")
        self.assertFalse(self.build.ensure_built(), "unchanged inputs: no second build")
        self.assertEqual(len(self.builds()), 1)
        _write(self.source, "export const a = 2;\n")
        _bump(self.source)
        self.assertTrue(self.build.ensure_built(), "a changed input is a stale marker: rebuild")
        self.assertFalse(self.build.ensure_built())
        self.assertEqual(len(self.builds()), 2)

    def test_a_new_source_file_is_a_changed_input(self):
        self.build.ensure_built()
        _write(os.path.join(self.src, "webview", "extra.css"), "a{}\n")
        self.assertTrue(self.build.ensure_built(), "the key covers the file set, not one newest mtime")

    def test_a_removed_dist_rebuilds(self):
        self.build.ensure_built()
        shutil.rmtree(self.build.dist)
        self.assertTrue(self.build.ensure_built(), "the marker went with dist")
        self.assertEqual(len(self.builds()), 2)

    def test_a_stale_marker_written_by_hand_rebuilds(self):
        self.build.ensure_built()
        _write(os.path.join(self.build.dist, lab_dist.MARKER_NAME), "0000\n")
        self.assertTrue(self.build.ensure_built())

    def test_a_failed_build_skips_and_leaves_no_marker(self):
        open(os.path.join(self.ext, "fail"), "w").close()
        with self.assertRaises(unittest.SkipTest) as cm:
            self.build.ensure_built()
        self.assertIn("esbuild failed here", str(cm.exception))
        self.assertIn("refusing to build", str(cm.exception))
        self.assertIsNone(self.build.read_marker(), "no marker for a build that did not land")
        os.remove(os.path.join(self.ext, "fail"))
        self.assertTrue(self.build.ensure_built(), "the next call builds")

    def test_the_key_is_computed_before_the_build_and_recorded_after_it(self):
        """A source saved while the build runs (after esbuild read it) is caught by the NEXT call: the marker
        records the state computed BEFORE the build, never the state after it, which would claim the edit was
        built. The injected runner makes the edit mid-build; recomputing the key at marker time fails this."""
        edits = []

        def editing_run(cmd, cwd, timeout):
            with open(self.source, "a") as f:
                f.write("export const late = 1;\n")
            _bump(self.source)
            edits.append(True)
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        build = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs, run=editing_run)
        self.assertTrue(build.ensure_built())
        self.assertEqual(edits, [True])
        self.assertNotEqual(build.read_marker(), build.key(), "the marker names the pre-build state, not the edit")
        self.assertTrue(self.build.ensure_built(), "the mid-build edit is a stale marker: rebuild")
        self.assertEqual(len(self.builds()), 2)
        self.assertFalse(self.build.ensure_built())

    def test_a_build_by_another_command_is_redone(self):
        """A `node esbuild.js --production` run by hand (or by install.sh on a box with no editor CLI, where
        nothing after the build touches a keyed file) leaves minified, sourcemap-less bundles under a marker
        whose inputs still match. The marker also names the output state the harness left, so the foreign
        write shows and the labs rebuild in their own mode before copying."""
        self.assertTrue(self.build.ensure_built())
        self.assertIn("mode=dev", self.dist_file("render.js"))
        subprocess.run([sys.executable, "fake_esbuild.py", "--production"], cwd=self.ext, check=True)
        self.assertIn("mode=production", self.dist_file("render.js"))
        self.assertEqual(self.build.read_marker(), self.build.key(), "no input changed")
        self.assertTrue(self.build.ensure_built(), "a dist written by another command is rebuilt")
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assertIn("mode=dev", _read(os.path.join(dest, "render.js")), "the copy is the harness's own build")
        self.assertEqual(len(self.builds()), 3)
        self.assertFalse(self.build.ensure_built(), "and current again")

    def test_the_build_command_line_is_part_of_the_key(self):
        """Two harnesses configured with different command lines (mode flags) never share a marker."""
        self.assertTrue(self.build.ensure_built())
        other = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd + ["--production"], inputs=self.build.inputs)
        self.assertNotEqual(other.key(), self.build.key(), "the command line is keyed")
        self.assertTrue(other.ensure_built(), "another command line builds its own")
        self.assertIn("mode=production", self.dist_file("render.js"))
        self.assertFalse(other.ensure_built())
        self.assertTrue(self.build.ensure_built(), "and the first builds back")

    def test_dependency_lock_files_are_keyed_by_content(self):
        """package-lock.json moves at checkout time; node_modules/.package-lock.json moves when npm installs
        (a pull moves the first, the `npm ci` after it the second). Either is a dependency change the bundles
        must be rebuilt from, whatever the sources did. Content, not stat: a no-op `npm install` rewrites both
        with a new mtime and the same bytes, and that must not rebuild."""
        lock = os.path.join(self.ext, "package-lock.json")
        hidden = os.path.join(self.ext, "node_modules", ".package-lock.json")
        _write(lock, '{"a": 1}\n')
        _write(hidden, '{"a": 1}\n')
        self.assertTrue(self.build.ensure_built())
        self.assertFalse(self.build.ensure_built())
        _write(hidden, '{"a": 2}\n')                       # same size: the installed tree changed
        self.assertTrue(self.build.ensure_built(), "the hidden lockfile changed: the installed tree did")
        _write(lock, '{"a": 2}\n')
        self.assertTrue(self.build.ensure_built(), "the checkout's lock file changed")
        for p in (lock, hidden):
            _bump(p)
        self.assertFalse(self.build.ensure_built(), "same bytes under a new mtime (a no-op install): no rebuild")
        os.remove(hidden)
        self.assertTrue(self.build.ensure_built(), "a removed node_modules is a dependency change")


class InputsDeriveFromEsbuild(unittest.TestCase):
    """The keyed trees come from esbuild.js, never from a list kept here: the top-level tree of every entry
    point (both forms), then the trees their relative imports reach."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lab-dist-inputs-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.ext = os.path.join(self.root, "ext")
        self.config = os.path.join(self.ext, "esbuild.js")
        _write(os.path.join(self.ext, "src", "extension.ts"), "export const host = 1;\n")
        _write(os.path.join(self.ext, "dist", "render.js"), "// an OUTPUT, never keyed\n")
        _write(os.path.join(self.ext, "node_modules", "pkg", "build", "worker.mjs"), "// a dependency\n")
        _write(os.path.join(self.root, "ui", "webview", "render.ts"),
               'import engine from "../../vendor/pkg/engine.js";\nexport const a = 1;\n')
        _write(os.path.join(self.root, "vendor", "pkg", "engine.js"), "module.exports = 1;\n")
        _write(os.path.join(self.root, "tools", "extra", "thing.ts"), "export const t = 1;\n")
        _write(self.config, '''
const extension = { entryPoints: ["src/extension.ts"], outfile: "dist/extension.js" };
const webview = {
  entryPoints: [
    "../ui/webview/render.ts",   // the shared UI: "quoted" words in a comment are not entries
    { in: "node_modules/pkg/build/worker.mjs", out: "worker" },
    "../tools/extra/thing.ts",
  ],
  outdir: "dist",
};
function testBuild() { const entries = []; return { entryPoints: entries, outdir: "out-tests" }; }
''')

    def rel(self, pairs):
        return [(os.path.relpath(p, self.root), r) for p, r in pairs]

    def test_entry_points_parse_in_both_forms(self):
        got = sorted(os.path.relpath(p, self.root) for p in lab_dist.esbuild_entry_points(self.ext))
        self.assertEqual(got, ["ext/node_modules/pkg/build/worker.mjs", "ext/src/extension.ts",
                               "tools/extra/thing.ts", "ui/webview/render.ts"])

    def test_roots_are_the_entry_points_trees_plus_the_trees_their_imports_reach(self):
        self.assertEqual(self.rel(lab_dist.default_inputs(self.root, self.ext)),
                         [("ext", True), ("tools", True), ("ui", True), ("vendor", True)],
                         "ext and ui and tools from the entries, vendor from render.ts's import; node_modules never")

    def test_the_keyed_files_follow_the_derivation(self):
        build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "x"], root=self.root)
        files = {os.path.relpath(p, self.root) for p in build._input_files()}
        for keyed in ("ext/src/extension.ts", "ext/esbuild.js", "ui/webview/render.ts", "vendor/pkg/engine.js",
                      "tools/extra/thing.ts"):
            self.assertIn(keyed, files)
        self.assertNotIn("ext/dist/render.js", files, "the output being built is not an input")
        self.assertFalse([f for f in files if "node_modules" in f], "dependencies are keyed by the lock files")
        before = build.key()
        _bump(os.path.join(self.root, "tools", "extra", "thing.ts"))
        self.assertNotEqual(build.key(), before, "an edit under a derived root changes the key")

    def test_a_source_directory_named_dist_at_depth_is_keyed(self):
        """Only the top-level dist is the output. A vendored package that ships its sources under its own
        dist/ is bundled by esbuild and must be keyed, so pruning every `dist` by name would miss an edit."""
        nested = os.path.join(self.root, "vendor", "pkg", "dist", "a.js")
        _write(nested, "module.exports = 2;\n")
        build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "x"], root=self.root)
        self.assertIn(nested, set(build._input_files()))
        before = build.key()
        _bump(nested)
        self.assertNotEqual(build.key(), before)

    def test_an_entry_point_outside_the_checkout_is_an_error(self):
        _write(self.config, 'const x = { entryPoints: ["../../elsewhere/x.ts"] };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.default_inputs(self.root, self.ext)
        self.assertIn("outside the checkout", str(cm.exception))

    def test_a_config_with_no_entry_points_is_an_error(self):
        _write(self.config, "const x = 1;\n")
        with self.assertRaises(ValueError):
            lab_dist.esbuild_entry_points(self.ext)

    def test_the_real_config_derives_the_kernel_trees(self):
        """On this checkout: render.ts (string form) and pdf.worker.mjs (object form) parse; the roots are
        ui/, vendor/ and vscode-extension/, the trees the kernel's _bundle_inputs reads (file-level parity is
        pinned in tests/test_kernel_bundle_staleness.py, where the kernel is already loaded); the config and
        package files are keyed, the lock file is content-keyed instead, and nothing under the extension's
        dist, node_modules or out-tests is."""
        entries = lab_dist.esbuild_entry_points()
        self.assertTrue(any(e.endswith(os.path.join("ui", "webview", "render.ts")) for e in entries))
        self.assertTrue(any(e.endswith(os.path.join("pdfjs-dist", "build", "pdf.worker.mjs")) for e in entries),
                        "the object-form entry parses")
        self.assertEqual([(os.path.relpath(p, lab_dist.ROOT), r) for p, r in lab_dist.default_inputs()],
                         [("ui", True), ("vendor", True), ("vscode-extension", True)])
        files = set(lab_dist.default()._input_files())
        for name in ("esbuild.js", "package.json", "tsconfig.json"):
            self.assertIn(os.path.join(lab_dist.EXT, name), files)
        self.assertNotIn(os.path.join(lab_dist.EXT, "package-lock.json"), files, "content-keyed, not stat-keyed")
        for sub in ("dist", "node_modules", "out-tests"):
            self.assertFalse([f for f in files if f.startswith(os.path.join(lab_dist.EXT, sub) + os.sep)], sub)
        self.assertGreater(len(files), 50)


class BuildBounded(_Checkout):

    def test_a_build_past_its_bound_fails_loudly_and_releases_the_lock(self):
        def wedged(cmd, cwd, timeout):
            raise subprocess.TimeoutExpired(cmd, timeout, output=b"", stderr=b"esbuild: still bundling\n")
        build = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs, timeout=7, run=wedged)
        with self.assertRaises(lab_dist.BuildTimeout) as cm:
            build.ensure_built()
        msg = str(cm.exception)
        self.assertIn("fake_esbuild.py", msg, "names the command")
        self.assertIn(self.ext, msg, "and where it ran")
        self.assertRegex(msg, r"ran \d+\.\d s, the bound is 7 s", "and the elapsed time against the bound")
        self.assertIn("still bundling", msg, "and the output tail")
        self.assertIsNone(build.read_marker(), "no marker for a build that did not finish")
        self.assertEqual(self.builds(), [])
        result = []                         # the lock went with the error: a caller with a working builder proceeds
        t = threading.Thread(target=lambda: result.append(self.build.ensure_built()))
        t.start()
        t.join(30)
        self.assertEqual(result, [True], "the next caller took the lock and built")

    def test_the_default_runner_enforces_the_bound(self):
        """The real path: the subprocess is killed at the bound, the staged files it left are not served."""
        os.environ["FAKE_HOLD"] = "30"
        self.addCleanup(os.environ.pop, "FAKE_HOLD", None)
        build = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs, timeout=0.5)
        started = time.monotonic()
        with self.assertRaises(lab_dist.BuildTimeout):
            build.ensure_built()
        self.assertLess(time.monotonic() - started, 20, "the bound cut the build, not the fake's own 30 s hold")
        self.assertIsNone(build.read_marker())
        self.assertTrue([n for n in os.listdir(build.dist) if ".tmp-" in n], "the killed build left its staging files")
        os.environ.pop("FAKE_HOLD")
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assert_complete_copy(dest)

    def test_the_bound_is_the_kernels(self):
        """The kernel bounds the same command in two places; the harness uses the larger, so a build the
        kernel would still wait for is never cut here first."""
        src = _read(KERNEL)
        bounds = []
        for fn, call in (("_rebuild_dist", r'subprocess\.run\(\["node", "esbuild\.js"\]'), ("_ensure_bundles", r"subprocess\.run\(argv")):
            body = re.search(r"def %s\(\):.*?(?=\ndef )" % fn, src, re.S)
            self.assertIsNotNone(body, fn)
            found = [int(x) for x in re.findall(call + r".*?timeout=(\d+)", body.group(0), re.S)]
            self.assertTrue(found, "%s bounds its esbuild run" % fn)
            bounds += found
        self.assertEqual(lab_dist.BUILD_TIMEOUT, max(bounds), "the kernel's bounds: %r" % bounds)


class CopyIgnoresForeignStaging(_Checkout):

    def test_a_staging_file_from_outside_the_harness_is_left_out(self):
        self.build.ensure_built()
        for name in (".pdf-worker.js.tmp-99999-0", os.path.join("fonts", ".b.woff2.tmp-99999-1")):
            open(os.path.join(self.build.dist, name), "w").close()
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assert_complete_copy(dest)
        self.assertEqual(len(self.builds()), 1, "a staging name is not a foreign write of the served outputs")

    def test_copies_survive_a_staged_builder_running_outside_the_lock(self):
        """A STAGED build that does not take the harness lock (a developer's `node esbuild.js`) renames
        staging files out from under a listing, which is exactly what broke the copy before; the ignore
        filter keeps the copy whole, and each served output is read whole (a rename is atomic, so old bytes
        or new). The fake models a stage-and-rename writer, esbuild.js's buildAll; watch mode writes in
        place and is outside the contract (the module docstring says so)."""
        self.build.ensure_built()
        loop = ("import subprocess, sys\n"
                "for _ in range(40): subprocess.run([sys.executable, 'fake_esbuild.py'], cwd=%r, check=True)\n" % self.ext)
        foreign = subprocess.Popen([sys.executable, "-c", loop], env=dict(os.environ, FAKE_HOLD="0.005"))
        try:
            deadline = time.time() + 60
            while len(self.builds()) < 2 and time.time() < deadline:     # the foreign builder has started
                time.sleep(0.01)
            i = 0
            while foreign.poll() is None and i < 400:                  # copy for as long as it runs
                dest = os.path.join(self.root, "f%d" % i, "dist")
                self.build.copy_to(dest)
                for rel in ("render.js", "styles.css", os.path.join("fonts", "a.woff2")):
                    self.assertIsNotNone(_ID.search(_read(os.path.join(dest, rel))), "%s whole in copy %d" % (rel, i))
                self.assertFalse([n for n in os.listdir(dest) if ".tmp-" in n or n.startswith(".lab-")])
                i += 1
        finally:
            foreign.wait(timeout=60)
        self.assertEqual(foreign.returncode, 0)
        self.assertGreater(i, 5, "copies overlapped the foreign builds: %d copies, %d builds" % (i, len(self.builds())))


class Packaging(unittest.TestCase):
    """The lock and the marker sit inside dist, which two packagers read: vsce reads dist for the VSIX and
    is governed by .vscodeignore (not .gitignore; a VSIX packaged from a checkout where the labs ran shipped
    both files before the rules), and git ignores dist whole."""

    def test_the_lock_and_marker_are_vscodeignored(self):
        with open(os.path.join(lab_dist.EXT, ".vscodeignore")) as f:
            patterns = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
        for name in (lab_dist.LOCK_NAME, lab_dist.MARKER_NAME):
            rel = "dist/" + name
            self.assertTrue(any(fnmatch.fnmatchcase(rel, p) for p in patterns),
                            "%s would ship in the VSIX: name it in vscode-extension/.vscodeignore" % rel)

    def test_the_lock_and_marker_are_gitignored(self):
        for name in (lab_dist.LOCK_NAME, lab_dist.MARKER_NAME):
            r = subprocess.run(["git", "check-ignore", "-q", "--", "vscode-extension/dist/" + name],
                               cwd=lab_dist.ROOT, capture_output=True, text=True)
            if r.returncode == 128:
                self.skipTest("not a git checkout: " + r.stderr.strip())
            self.assertEqual(r.returncode, 0, "vscode-extension/dist/%s is not gitignored" % name)


# The text ratchet's allowlists, each a deliberate exemption with its reason. A new module that legitimately
# reads esbuild.js as text, or copies a tree that is not the extension's dist, is added here on purpose.
_ESBUILD_TEXT_READERS = {"test_lab_dist.py", "test_bundle_build_mode.py", "test_kernel_bundle_staleness.py",
                         "test_kernel_bundle_vendor_inputs.py"}        # source pins over esbuild.js; none runs it
_TREE_COPIERS = {"test_lab_dist.py", "test_github_repo.py"}            # test_github_repo copies a repo, never dist
_KEY_READERS = {"test_kernel_bundle_staleness.py"}                     # imports lab_dist for the input parity pin


def offences(name, src):
    """What the ratchet holds against one test module's text: any mention of esbuild.js (a build by any
    argv shape, a prebuilt variable included) outside the text readers; any copytree outside the tree
    copiers; and, for every module but the harness's own test, a copytree whose source names dist."""
    found = []
    if "esbuild.js" in src and name not in _ESBUILD_TEXT_READERS:
        found.append("esbuild.js")
    if re.search(r"\bcopytree\s*\(", src) and name not in _TREE_COPIERS:
        found.append("copytree(")
    if name != "test_lab_dist.py" and re.search(r"\bcopytree\s*\([^,]*\b(dist|DIST|EXT)\b", src):
        found.append("copytree(dist")
    return found


class ServedModulesUseTheHelper(unittest.TestCase):

    def test_no_test_module_builds_or_copies_dist_on_its_own(self):
        """The ownership holds only while every served lab goes through the helper. This is a TEXT ratchet
        over tests/*.py (the guarantee itself lives in lab_dist): a module that mentions esbuild.js or calls
        copytree, in any spelling, is an offender unless the allowlists above name it and say why."""
        offenders = []
        for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            name = os.path.basename(path)
            if name == "lab_dist.py" or os.path.realpath(path) == os.path.realpath(__file__):
                continue
            found = offences(name, _read(path))
            if found:
                offenders.append((name, found))
        self.assertEqual(offenders, [], "build and copy dist through lab_dist.copy_dist; a module that reads "
                                        "esbuild.js as text or copies a tree that is not dist is added to the "
                                        "allowlists in test_lab_dist.py, with its reason")

    def test_the_ratchet_catches_every_shape_of_the_old_block(self):
        """The shapes a copy-paste or a rewrite could take, each flagged: the base shape the thirteen modules
        had, a mode flag, single quotes, a prebuilt argv (the kernel's own shape), a constant for dist."""
        shapes = [
            'subprocess.run(["node", "esbuild.js"], cwd=EXT, check=True)\nshutil.copytree(os.path.join(EXT, "dist"), dist)\n',
            'subprocess.run(["node", "esbuild.js", "--production"], cwd=EXT)\nshutil.copytree(DIST, dist)\n',
            "subprocess.run(['node', 'esbuild.js'], cwd=EXT)\n",
            'cmd = ["node", "esbuild.js"]\nsubprocess.check_call(cmd, cwd=EXT)\nshutil.copytree(EXT + "/dist", dest)\n',
            'argv = ["node", "esbuild.js"] + ([] if dev else ["--production"])\n',
            "shutil.copytree(os.path.join(EXT, 'dist'), lab)\n",
        ]
        for shape in shapes:
            self.assertTrue(offences("test_synthetic_served.py", shape), shape)
        self.assertEqual(offences("test_synthetic_served.py", "import lab_dist\nlab_dist.copy_dist(dist)\n"), [])
        self.assertEqual(offences("test_github_repo.py", "shutil.copytree(main, backup, symlinks=True)\n"), [])
        self.assertEqual(offences("test_github_repo.py", "shutil.copytree(os.path.join(EXT, 'dist'), lab)\n"), ["copytree(dist"],
                         "a tree copier is still refused the extension's dist")

    def test_every_served_module_calls_copy_dist(self):
        served = []
        for p in glob.glob(os.path.join(HERE, "test_*.py")):
            name = os.path.basename(p)
            if os.path.realpath(p) == os.path.realpath(__file__) or name in _KEY_READERS:
                continue
            if "\nimport lab_dist\n" in _read(p):
                served.append(p)
        self.assertGreaterEqual(len(served), 13, "the served labs import the helper")
        for p in served:
            self.assertIn("lab_dist.copy_dist(", _read(p), os.path.basename(p))


if __name__ == "__main__":
    unittest.main()
