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
  4. the inputs are derived from esbuild.js's EXPORTS, never from its text (review round 6): node requires the
     module (which builds only as a script) and writes module.exports as JSON to a file, never to stdout, so a
     config that logs at require time is read whole; every string value in the exported objects, at any depth, is
     a candidate (the values of an object, never its keys), and a candidate naming a path on disk inside the
     checkout contributes its top-level tree, relative or absolute (one naming nothing on disk contributes
     nothing; a directory value contributes its tree; an entry built from a template literal at require time is
     keyed, a shape no text scan could see; a path in a comment or a code body is not exported data; a relative
     value that reaches an existing path outside the checkout is an error, and so is an absolute one naming an
     existing source file outside it that is not under node_modules' realpath, while an absolute outside
     directory, a non-source file and a dependency's realpath are silent; a module that
     exports nothing, a module node cannot load, a module that ends the process before the file is written, a
     missing extension dir, a missing node and a require past its bound are errors with no fallback to the text,
     the three raised after node ran (does not load, ends the process, past its bound) carrying its stderr and
     stdout and the others naming the path, node or the exports' JSON head; a top-level file is keyed as one file; the config's own tree is keyed
     with no exported value inside it; then the trees their relative imports reach, one executed test per import
     shape the scan follows), the dist being built is left out at the top level only, and on the real config the
     derivation yields the kernel's trees, on a checkout without the extension's node_modules too, through a
     node preload that stands in for a bare package the config itself requires and node cannot find, on a
     checkout without node_modules beside the config (tests/lab_dist_stub.py;
     tests/test_kernel_bundle_staleness.py pins file-level parity the same way);
  5. the two environment failures skip the caller, with the reason, and every other failure raises: a build that
     fails skips and leaves no marker, and a bare package the config requires that node cannot find skips from
     the served modules' own call (review round 7, decision 2), while a config that does not load (a syntax
     error, a missing relative module) raises from that call; a build that exceeds its bound raises BuildTimeout,
     a RuntimeError and never a SkipTest, and releases the lock (the bound itself, and the bound on the require,
     are pinned to the kernel's figures in tests/test_kernel_bundle_vendor_inputs.py, by running all three of
     the kernel's esbuild calls over a recording fake);
  6. the copy leaves out a staging file the harness did not write, and survives a staged builder running
     outside the lock (the defence-in-depth half);
  7. the lock and the marker are left out of a VSIX (.vscodeignore) and of git (.gitignore);
  8. no test module builds or copies dist on its own any more (a text ratchet over tests/*.py).
Hermetic: the fake checkout lives under the run's temp root and no real esbuild runs. Synthetic names only.
"""
import contextlib
import fcntl
import fnmatch
import functools
import glob
import json
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
import lab_dist_stub

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

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

    def test_a_relative_extension_dir_keys_the_same_files_as_the_absolute_one(self):
        """`DistBuild(ext="ext")` from the checkout root: the dist prune and the dependency filter compare paths
        textually against the walk's absolute paths, so a relative dir left dist's outputs in the key (every
        build changed them, so every call rebuilt) and stat-keyed package-lock.json. The dir is made absolute
        first, as the derivation functions make theirs; every caller passes an absolute dir today (latent)."""
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.root)
        _write(os.path.join(self.ext, "package-lock.json"), '{"a": 1}\n')
        build = lab_dist.DistBuild(ext="ext", cmd=self.build.cmd, inputs=[(self.src, True), (self.ext, True)])
        self.assertTrue(build.ensure_built(), "an unbuilt dist builds")
        self.assertFalse(build.ensure_built(), "unchanged inputs: no second build")
        self.assertFalse(build.ensure_built())
        self.assertEqual(len(self.builds()), 1, "a build does not invalidate its own marker")
        files = list(build._input_files())
        self.assertFalse([f for f in files if os.sep + "dist" + os.sep in f], "dist's outputs are not inputs: %r" % files)
        self.assertNotIn(os.path.join(self.ext, "package-lock.json"), files, "content-keyed, not stat-keyed")
        self.assertIn(self.source, files, "the absolute inputs are still keyed")


class InputsDeriveFromEsbuild(unittest.TestCase):
    """The keyed trees come from esbuild.js, never from a list kept here, and from what it EXPORTS, never from
    its text (the round-6 ruling, the repo's authoritative-source rule): node requires the config and prints
    module.exports as JSON, every string value in the exported objects that names a path on disk contributes
    its top-level tree, then the trees their relative imports reach. Every fixture is a requireable module
    exporting plain config objects, with no esbuild import (the real module's require of esbuild is a
    dependency of the build, not of the data). Retired with the text scans, by that ruling: the quoting-corner
    tests of rounds 4 and 5 (an apostrophe in a comment before a path, a double quote in a regex literal before
    a path, a template-literal path, a quoted path with a space and one with an @ inside a component) and the
    header's claim that a stray quote before a path hides nothing; through the export there is no quoting to
    get wrong, and a path is a value or it is not. The checkout is `base/checkout`, so a path OUTSIDE the
    checkout can exist inside the cleaned temp dir; the base is a realpath, because node's __dirname is one and
    the absolute-value tests compare the two textually. Round 7 added the served-shaped caller (`served_call`:
    the served modules' own `copy_dist`, with the harness's DistBuild bound to this checkout), over which the
    environment skips and the config errors, and the stand-in for the esbuild package the two real-tree pins
    run under (tests/lab_dist_stub.py); round 8 made the stand-in a node preload covering every bare package
    node cannot resolve, and isolated the served caller from node's global folders (NODE_PATH dropped, HOME
    bound to this test's temp base) so its premise, that no esbuild resolves, holds on a developer's box too;
    round 9 narrowed the stand-in to the config's own requires, to packages whose root is nowhere on the lookup
    paths, and to a checkout with no node_modules beside the config (`no_install`, the CI shape), and the reader
    files a miss as the environment by the same three tests; round 10 made the requirer test read the requirer's
    filename (a require inside a package function the config calls at load had passed the depth test), worded the
    reader's line for a non-config requirer by where the requirer lies (a helper of the checkout is not an install),
    named the `require.resolve` limit, and had every derivation error carry the head of node's stderr beside its
    tail (`pad_checkout`: the headline was lost once the config's path grew long enough); round 11 made the
    requirer test exact (the harness names the config's realpath to the preload in `lab_dist.CONFIG_ENV`, where
    round 10 inferred it from the loads), computed every lookup chain from its module's realpath and judged an
    installed requirer against the chain of every module above it in the require stack, and took a subpath into
    one of node's core modules out of the environment in the reader and the preload alike; round 12 ordered the
    evidence in both (the package's root on the requirer's chain first, then a core module's name, so a userland
    package named like one, punycode, keeps the install wording), added the config's chain to the requirer's whatever
    the require stack holds (node fills it with each module's first loader), took package-imports specifiers (`#x`)
    out of the environment, and had the preload realpath the requirer's filename before comparing it with the
    config's (an inherited `--preserve-symlinks` on NODE_OPTIONS makes node keep the textual path); round 13 gave the
    root on the requirer's chain its wording for any requirer (a helper of the checkout with the package installed on
    its own chain was told to install it) and took a one-segment scoped name (`@scope` alone, which npm installs
    nothing under) out of the bare shapes in both rules; round 14 reads the bare shape and the package's name from one
    split of the request in both rules, so an empty scope (`@/x`) and an empty, `.` or `..` segment (`@scope//pkg`,
    `pkg/../x`, `@scope/./x`) are node's error alone, never a root, an install or the environment; round 15 judges the
    NAME segments alone (the first, two for a scoped request) and not the subpath after them, so `pkg/`, `pkg/./index`,
    `pkg/../pkg` and `@scope/q/`, which node resolves to the installed package, are that package's requests, judged
    by its root and its name as the bare name is (the environment where none resolves, where round 14 was node's
    error alone), while `@/x`, `@scope//pkg`, `@scope/./x` and `@scope/../x` stay node's error alone."""

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="lab-dist-inputs-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.root = os.path.join(self.base, "checkout")
        self.ext = os.path.join(self.root, "ext")
        self.config = os.path.join(self.ext, "esbuild.js")
        _write(os.path.join(self.ext, "src", "extension.ts"), "export const host = 1;\n")
        _write(os.path.join(self.ext, "dist", "render.js"), "// an OUTPUT, never keyed\n")
        _write(os.path.join(self.ext, "node_modules", "pkg", "build", "worker.mjs"), "// a dependency\n")
        _write(os.path.join(self.root, "ui", "webview", "render.ts"),
               'import engine from "../../vendor/pkg/engine.js";\nexport const a = 1;\n')
        _write(os.path.join(self.root, "vendor", "pkg", "engine.js"), "module.exports = 1;\n")
        _write(os.path.join(self.root, "tools", "extra", "thing.ts"), "export const t = 1;\n")
        # the other import shapes the scan follows, each reaching a top-level tree of its own (tA to tE), so a
        # shape the scan stopped following shows as a missing root; every target is a real file (a root that
        # does not exist is skipped by design)
        _write(os.path.join(self.root, "ui", "webview", "plain.js"),
               'import "../../tA/a.js";\nconst b = import("../../tB/b.js");\nconst c = require("../../tC/c.js");\n'
               'const p = "../data/x.json";\n')
        _write(os.path.join(self.root, "ui", "webview", "styles.css"),
               '@import "../../tD/d.css";\n@import url("../../tE/e.css");\n')
        for t, name in (("tA", "a.js"), ("tB", "b.js"), ("tC", "c.js"), ("tD", "d.css"), ("tE", "e.css")):
            _write(os.path.join(self.root, t, name), "/* %s */\n" % t)
        _write(os.path.join(self.root, "data", "x.json"), "{}\n")
        # the real module's shape: two config objects and a function, exported together; the function drops out
        # of the JSON print and is never called
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
module.exports = { extension, webview, testBuild };
''')

    def rel(self, pairs):
        return [(os.path.relpath(p, self.root), r) for p, r in pairs]

    def roots(self):
        """The trees the config's exported values name, before the import follow, relative to the checkout."""
        return [os.path.relpath(p, self.root) for p in lab_dist.esbuild_roots(self.root, self.ext)]

    def imports_of(self, name, text):
        """The relative specifiers the scan reads out of one synthetic webview source holding `text`."""
        path = os.path.join(self.root, "ui", "webview", name)
        _write(path, text)
        return list(lab_dist._relative_imports(path))

    def served_call(self):
        """The served modules' own call, lab_dist.copy_dist, over this synthetic checkout: default() builds its
        DistBuild on first use, so the derivation runs inside the call, where a served class's setUpClass meets
        it. DistBuild is bound to this checkout for the call; _DEFAULT is cleared and restored around it. The
        environment is isolated from node's global folders for the call, test-side only (the harness passes its
        environment through, and the real-tree pins rely on that): NODE_PATH is dropped and HOME is bound to this
        test's temp base, which holds no .node_modules, so a developer's global esbuild cannot resolve the bare
        require the skip tests plant. $PREFIX/lib/node cannot be scrubbed and stays the premise."""
        bound = functools.partial(lab_dist.DistBuild, ext=self.ext, root=self.root, cmd=[sys.executable, "x"])
        with patch.dict(os.environ, {"HOME": self.base}), \
                patch.object(lab_dist, "_DEFAULT", None), patch.object(lab_dist, "DistBuild", bound):
            os.environ.pop("NODE_PATH", None)
            lab_dist.copy_dist(os.path.join(self.base, "lab", "dist"))

    def no_install(self):
        """The CI shape, no node_modules beside the config: setUp plants one holding `pkg`, and the stand-in
        declines a node_modules that exists and lacks the package (a stale install), so the tests that want a
        stand-in remove it first."""
        shutil.rmtree(os.path.join(self.ext, "node_modules"), ignore_errors=True)

    def pad_checkout(self, length):
        """Re-roots this test's checkout under nested padding directories inside self.base, so the config's path is
        at least `length` chars long whatever TMPDIR the run has (round 10: node's stderr repeats the config's path
        once per stack frame, so the tail alone of a long enough stream lost node's headline; the tests that pin
        the head use this to make the stream long at any TMPDIR), and plants the one source the padded configs
        name. Rebinds self.root, self.ext and self.config; the old checkout stays under self.base, unused."""
        root = self.base
        while len(os.path.join(root, "checkout", "ext", "esbuild.js")) < length:
            root = os.path.join(root, "padding-" + "x" * 24)
        self.root = os.path.join(root, "checkout")
        self.ext = os.path.join(self.root, "ext")
        self.config = os.path.join(self.ext, "esbuild.js")
        _write(os.path.join(self.ext, "src", "extension.ts"), "export const host = 1;\n")
        self.assertGreaterEqual(len(self.config), length, "the fixture holds: a long config path")

    def derivation_error(self, under_stub):
        """The ValueError esbuild_roots raises over this checkout, plain or inside the stand-in's block. A
        SkipTest fails (the shapes these tests plant are errors, never the environment), and so does the block's
        own AssertionError (a skip the block converted) and a derivation that succeeds."""
        block = lab_dist_stub.bare_package_stub() if under_stub else contextlib.nullcontext()
        try:
            with block:
                roots = lab_dist.esbuild_roots(self.root, self.ext)
        except unittest.SkipTest as e:
            self.fail("an error read as the environment (under_stub=%r): %r" % (under_stub, e))
        except ValueError as e:
            return str(e)
        except AssertionError as e:
            self.fail("the block converted a skip instead of the error reaching the reader (under_stub=%r): %r" % (under_stub, e))
        self.fail("the derivation succeeded (under_stub=%r): %r" % (under_stub, roots))

    def test_the_exported_configs_name_two_trees_and_both_are_keyed(self):
        """The export shape: module.exports holds two configs and a function (dropped, never called), their
        entryPoints reach two trees, and both are keyed with the extension's own. This one also held under the
        round-5 text scans, which found the same paths in the text; the tests below it are the ones only the
        export read passes."""
        self.assertEqual(self.roots(), ["ext", "tools", "ui"],
                         "ext from src/extension.ts and dist, ui and tools from the webview entries; the object-form "
                         "entry under node_modules is a dependency (keyed by the lock files, its files pruned from "
                         "every walk); outfile, outdir and the names in the comment resolve to nothing on disk or "
                         "are not exported")

    def test_an_entry_point_built_from_a_template_literal_at_require_time_is_keyed_a_shape_no_text_scan_could_see(self):
        """`../lib${major}/entry.ts` stands in the file in no piece a text scan could resolve (`../lib` and
        `/entry.ts` name nothing on disk, and the literal as written is not a path); through the export it is
        the plain string "../lib2/entry.ts". The round-5 scans answered ['ext'] here."""
        _write(os.path.join(self.root, "lib2", "entry.ts"), "export const v = 2;\n")
        _write(self.config, 'const major = 2;\n'
                            'module.exports = { webview: { entryPoints: [`../lib${major}/entry.ts`, "src/extension.ts"] } };\n')
        self.assertEqual(self.roots(), ["ext", "lib2"])

    def test_an_object_form_entry_point_inside_the_array_is_keyed(self):
        """esbuild's `{ in, out }` entry (the real config's pdf-worker entry has this shape, under node_modules):
        an object inside the entryPoints array, so the walk must recurse through the array into the object. The
        only mutant of _exported_strings the other fixtures miss (arrays yielding their strings and skipping
        their objects) fails here. A text scan also found this path, so this one held at round 5 too."""
        _write(self.config, 'module.exports = { webview: { entryPoints: [{ in: "../tools/extra/thing.ts", out: "thing" }, '
                            '"src/extension.ts"] } };\n')
        self.assertEqual(self.roots(), ["ext", "tools"])

    def test_a_path_in_key_position_is_not_a_candidate(self):
        """The walk yields the VALUES of an object, never its keys (option names: a loader suffix, an alias, a
        define name). A mutant yielding keys too passes every other fixture and the real-config pin (none of the
        real config's keys resolves on disk), so this one puts a real path in a key, an alias FROM a source path,
        a shape no esbuild option takes in practice (invented for the mutant), and the tree it names stays out."""
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], '
                            'alias: { "../tools/extra/thing.ts": "nowhere" } } };\n')
        self.assertEqual(self.roots(), ["ext"])

    def test_an_absolute_value_inside_the_checkout_is_keyed(self):
        """The `path.join(__dirname, ...)` idiom the real config uses for its node_modules paths, pointed at a
        source tree instead: an inject file under checkout/shims, named by an absolute path. The round-6 code
        dropped every absolute value before looking at it, so a tree reached only this way was keyed by nothing
        (the parity pin sees the kernel's list alone). node's __dirname is a realpath, and so is this checkout
        (setUp), so the textual comparison holds."""
        _write(os.path.join(self.root, "shims", "p.js"), "globalThis.p = 1;\n")
        _write(self.config, 'const path = require("path");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"], '
                            'inject: [path.join(__dirname, "..", "shims", "p.js")] } };\n')
        self.assertEqual(self.roots(), ["ext", "shims"])

    def test_an_absolute_source_file_outside_the_checkout_is_an_error_like_the_relative_spelling(self):
        """`path.join(__dirname, "..", "..", "elsewhere", "x.ts")`: an existing source file outside the checkout,
        named absolutely (an inject shim beside the repo), is a build input no top-level tree here can key, so it
        raises naming the path, as the relative spelling of the same file does (the loud cases below). Round 7
        dropped every absolute outside value as noise and this test pinned the asymmetry; the file went unkeyed in
        silence. A file with NO source suffix stays silent (process.execPath, a binary the config exports, cannot
        be told from a system path by shape); the directory and dependency exemptions are the two tests below."""
        outside = os.path.join(self.base, "elsewhere", "x.ts")
        _write(outside, "export const e = 1;\n")
        _write(self.config, 'const path = require("path");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"], '
                            'inject: [path.join(__dirname, "..", "..", "elsewhere", "x.ts")] } };\n')
        with self.assertRaises(ValueError) as cm:
            self.roots()
        self.assertIn("source file outside the checkout", str(cm.exception))
        self.assertIn(outside, str(cm.exception))
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts", %s] } };\n' % json.dumps(outside))
        with self.assertRaises(ValueError, msg="the plain absolute string takes the same door as the path.join"):
            self.roots()
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], nodeBinary: process.execPath } };\n')
        self.assertEqual(self.roots(), ["ext"], "an absolute outside file with no source suffix is silent")

    def test_an_absolute_directory_outside_the_checkout_is_silent_as_a_system_path(self):
        """An existing DIRECTORY outside the checkout named absolutely (`/` as a publicPath, a nodePaths resolution
        root, an absWorkingDir) cannot be told from a system path by shape, so it is silent even when it holds
        sources; a raise on `/` would error every served lab on a legitimate config. The relative spelling of the
        same directory raises. The residual, stated in the docstrings: an outside directory that IS a build input
        goes unkeyed in silence."""
        elsewhere = os.path.join(self.base, "elsewhere")
        _write(os.path.join(elsewhere, "x.ts"), "export const e = 1;\n")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], publicPath: "/", absWorkingDir: "/usr", '
                            'nodePaths: [%s] } };\n' % json.dumps(elsewhere))
        self.assertEqual(self.roots(), ["ext"])
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], outbase: "../../elsewhere" } };\n')
        with self.assertRaises(ValueError) as cm:
            self.roots()
        self.assertIn("outside the checkout", str(cm.exception))

    def test_a_dependency_resolved_to_its_realpath_outside_the_checkout_is_silent(self):
        """This checkout's own layout: the extension's node_modules is a symlink to a tree outside the checkout,
        and node's require.resolve answers the realpath, an absolute source file outside the textual checkout. It
        is under the realpath of node_modules, so it is a dependency (keyed by the lock files, pruned from every
        walk) and silent, where the file rule above would raise. A raise here would fail the real config the day
        it exports a resolved dependency path on a symlinked node_modules."""
        shutil.rmtree(os.path.join(self.ext, "node_modules"))
        store = os.path.join(self.base, "store")
        _write(os.path.join(store, "pkg", "index.js"), "module.exports = 1;\n")
        os.symlink(store, os.path.join(self.ext, "node_modules"))
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], inject: [require.resolve("pkg")] } };\n')
        self.assertEqual(self.roots(), ["ext"])
        _, exports = lab_dist.esbuild_exports(self.ext)
        self.assertEqual(exports["x"]["inject"], [os.path.join(store, "pkg", "index.js")],
                         "the fixture holds: node answered the realpath outside the checkout")

    def test_a_directory_valued_export_contributes_its_tree(self):
        """A value naming a DIRECTORY on disk (an outbase, a nodePaths entry, an absWorkingDir, a tsconfig dir)
        contributes the tree that holds it, as a file does. The tree here is reachable no other way, so the
        one-token mutant `exists` to `isfile` fails this test (the only directory value on the real tree is dist,
        whose tree src/extension.ts keys anyway)."""
        _write(os.path.join(self.root, "assets", "a.css"), "a{}\n")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"], outbase: "../assets" } };\n')
        self.assertEqual(self.roots(), ["assets", "ext"])

    def test_the_configs_own_tree_is_keyed_without_an_exported_value_inside_it(self):
        """esbuild.js, package.json and tsconfig.json are inputs of the build whether or not the config names a
        path in its own tree. A config naming only a ../ui entry, over an extension dir with no dist yet (setUp
        writes ext/dist/render.js, which would key ext by accident through "dist"): the roots are ui alone, the
        derived inputs still hold ext, esbuild.js is a keyed file, and an edit to it changes the key. Before the
        seed, the key stood still through edits to all three config files in this shape, and a process that
        started after dist existed keyed ext through "dist" while an earlier one had not."""
        shutil.rmtree(os.path.join(self.ext, "dist"))
        _write(self.config, 'module.exports = { webview: { entryPoints: ["../ui/webview/render.ts"], outdir: "dist" } };\n')
        self.assertEqual(self.roots(), ["ui"])
        self.assertEqual(self.rel(lab_dist.default_inputs(self.root, self.ext)),
                         [("ext", True), ("tA", True), ("tB", True), ("tC", True), ("tD", True), ("tE", True),
                          ("ui", True), ("vendor", True)])
        build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "x"], root=self.root)
        self.assertIn(self.config, list(build._input_files()), "the config is a keyed input of its own build")
        before = build.key()
        _bump(self.config)
        self.assertNotEqual(build.key(), before, "an edit to esbuild.js changes the key")

    def test_every_shape_that_broke_the_text_parsers_is_plain_data_through_the_export(self):
        """The shapes that made an array parser return a shorter list, or a text scan miss a path: a `//` inside
        a string on the line that opens the array, the record form of entryPoints (no array at all), a URL entry,
        a comment naming a path that does not exist, a trailing comma, a single-quoted entry, a spread of a
        ternary, an apostrophe in a comment and a regex literal holding double quotes before a path on the same
        line. Node evaluates the file, the export holds the values, and the roots are the trees the real paths
        reach."""
        _write(self.config, '''
const production = false;
const m = /^Could not resolve "([^"]+)"/;   // the extension's own regex, with "quotes" before the entries
const banner = { js: "// built by esbuild.js" }, entryPoints = [
    "../ui/webview/render.ts",   // see "../plans/render.md" and "../gone/x.ts": neither exists
    { in: "node_modules/pkg/build/worker.mjs", out: "worker" },
    'https://cdn.invalid/webview/x.ts',
    /* the extension's own entry */ '../tools/extra/thing.ts',   // don't drop it
    ...(production ? ["src/extension.ts"] : []),
  ];
const record = { entryPoints: { host: "src/extension.ts" }, outdir: "dist" };
const picked = production ? ["src/extension.ts"] : ["src/extension.ts"];
module.exports = { banner, entryPoints, record, picked, filter: m.source };
''')
        self.assertEqual(self.roots(), ["ext", "tools", "ui"])

    def test_a_path_only_in_a_comment_or_a_code_body_is_not_exported_data(self):
        """The limit of the export, pinned so it is not mistaken for a drop: a comment naming a tree, and a plugin
        whose setup body returns a path, are code, not exported data (JSON.stringify drops the function), so
        neither tree is keyed (a comment is never a build input, so its path is harmless; the plugin's is the
        real limit). The parity pin against the kernel's hand-maintained _bundle_inputs list catches drift inside
        the trees that list names and nothing else, so a tree reached only through code (tools/ here) is pinned
        by no test until someone adds it to the kernel's list by hand. The round-5 scans keyed both here
        (['data', 'ext', 'tools'])."""
        _write(self.config, '''
// the fixtures under "../data" are read by the tests, not bundled
const relay = { name: "relay", setup(build) { build.onResolve({ filter: /^x$/ }, () => ({ path: "../tools/extra/thing.ts" })); } };
module.exports = { extension: { entryPoints: ["src/extension.ts"], plugins: [relay] } };
''')
        self.assertEqual(self.roots(), ["ext"])

    def test_a_top_level_file_the_config_names_is_keyed_as_one_file(self):
        """A path whose top-level tree is a FILE (root/top.js) is keyed as that one file, not walked: it is
        an input like any other (an edit to it changes the key), and a walk of a file would key nothing."""
        top = os.path.join(self.root, "top.js")
        _write(top, "module.exports = 1;\n")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts", "../top.js"] } };\n')
        self.assertEqual(self.rel(lab_dist.default_inputs(self.root, self.ext)), [("ext", True), ("top.js", False)])
        build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "x"], root=self.root)
        self.assertIn(top, list(build._input_files()), "the file itself is the keyed input")
        before = build.key()
        _bump(top)
        self.assertNotEqual(build.key(), before, "an edit to a top-level file input changes the key")

    def test_a_value_naming_nothing_on_disk_contributes_nothing(self):
        """Noise a config is full of: formats, targets, a loader, globs, a message, an empty string, an absolute
        path outside the checkout (`/`, the shape of a publicPath; the real config's absolute values are under
        node_modules and skipped as dependencies), the checkout root itself (".."), a template literal computed to
        nothing on disk, a spread, a define value, and the non-strings around them (a boolean, null, a number).
        None names a tree; the one real path does."""
        _write(self.config, '''
const more = ["../nowhere/x.ts"], dir = "gone", name = "x";
module.exports = { x: { entryPoints: ["src/extension.ts", ...more, `${dir}/${name}.ts`], format: "cjs", target: "node18",
            loader: { ".woff2": "file" }, external: ["*.png", "../media/*.woff2"], empty: "", abs: "/", up: "..",
            msg: "esbuild.js: build failed: ", assetNames: "fonts/[name]-[hash]", define: { __BUILD__: "1" },
            bundle: true, sourcemap: null, port: 8080 } };
''')
        self.assertEqual(self.roots(), ["ext"])

    def test_roots_are_the_entry_points_trees_plus_the_trees_their_imports_reach(self):
        self.assertEqual(self.rel(lab_dist.default_inputs(self.root, self.ext)),
                         [("ext", True), ("tA", True), ("tB", True), ("tC", True), ("tD", True), ("tE", True),
                          ("tools", True), ("ui", True), ("vendor", True)],
                         "ext and ui and tools from the entries, vendor from render.ts's `from` import, tA to tE "
                         "from the other four import shapes; data (a string that is not an import) never, and "
                         "node_modules never (a dependency: keyed by the lock files, pruned from every walk)")

    # One executed test per import shape _IMPORT_SHAPE follows, so the shape a regression stopped following is
    # the test that names it (the real trees' cross-tree imports are all `from`-shaped today, so the real-config
    # test below cannot tell).
    def test_an_es_from_import_is_followed(self):
        self.assertEqual(self.imports_of("s1.ts", 'import { x } from "../../vendor/pkg/engine.js";\n'),
                         ["../../vendor/pkg/engine.js"])

    def test_a_bare_side_effect_import_is_followed(self):
        self.assertEqual(self.imports_of("s2.js", 'import "../../tA/a.js";\n'), ["../../tA/a.js"])

    def test_a_dynamic_import_is_followed(self):
        self.assertEqual(self.imports_of("s3.js", 'const b = import("../../tB/b.js");\n'), ["../../tB/b.js"])
        self.assertEqual(self.imports_of("s3b.js", 'const b = import( "../../tB/b.js" );\n'), ["../../tB/b.js"])

    def test_a_require_is_followed(self):
        self.assertEqual(self.imports_of("s4.js", 'const c = require("../../tC/c.js");\n'), ["../../tC/c.js"])
        self.assertEqual(self.imports_of("s4b.js", "const c = require ('./local.js');\n"), ["./local.js"])

    def test_a_css_import_is_followed(self):
        self.assertEqual(self.imports_of("s5.css", '@import "../../tD/d.css";\n'), ["../../tD/d.css"])

    def test_a_css_import_url_is_followed(self):
        self.assertEqual(self.imports_of("s6.css", '@import url("../../tE/e.css");\n'), ["../../tE/e.css"])

    def test_a_relative_string_that_is_not_an_import_is_not_followed(self):
        self.assertEqual(self.imports_of("s7.js", 'const p = "../data/x.json";\nconst q = fetch("./api/x");\n'), [])

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

    # The loud cases. Each fixture's TEXT names src/extension.ts, so a fallback to the text would answer ['ext']
    # instead of raising; the round-5 scans did exactly that on the first three.
    def test_an_exported_path_outside_the_checkout_is_an_error_naming_the_path(self):
        """No top-level tree of the checkout can key it, and the kernel parity pin cannot see it either, so it
        is loud. A path outside the checkout that does not exist is noise like any other."""
        _write(os.path.join(self.base, "elsewhere", "x.ts"), "export const e = 1;\n")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts", "../../elsewhere/x.ts"] } };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.default_inputs(self.root, self.ext)
        self.assertIn("outside the checkout", str(cm.exception))
        self.assertIn("../../elsewhere/x.ts", str(cm.exception))
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts", "../../nowhere/x.ts"] } };\n')
        self.assertEqual(self.roots(), ["ext"])

    def test_a_module_that_exports_nothing_is_an_error(self):
        """No module.exports at all, and an export holding only a function (JSON drops it; it is not called):
        both raise, naming what module.exports printed as."""
        _write(self.config, 'const x = { entryPoints: ["src/extension.ts"] };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("exports no string value", str(cm.exception))
        self.assertIn("{}", str(cm.exception))
        _write(self.config, 'module.exports = { build() { return ["src/extension.ts"]; } };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("exports no string value", str(cm.exception))
        self.assertIn("prints as {}", str(cm.exception))
        _write(self.config, 'module.exports = function () { return ["src/extension.ts"]; };\n')   # not JSON at all
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("prints as null", str(cm.exception))

    def test_a_module_node_cannot_load_is_an_error_carrying_the_stderr(self):
        """A syntax error, and a missing RELATIVE module (`require("./gone")`: MODULE_NOT_FOUND too, but for a
        file of this checkout, so the config is what is wrong, not the environment): node exits nonzero and the
        error carries its stderr and the config's path. The bare-package shape of the same error code is the
        environment's and skips instead (the served-caller tests below); the relative half here catches SkipTest
        first and fails on it, so a reader that skipped every MODULE_NOT_FOUND fails here instead of skipping (a
        SyntaxError has no such code and cannot take that door)."""
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\nconst broken = [;\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("SyntaxError", str(cm.exception))
        self.assertIn(self.config, str(cm.exception))
        _write(self.config, 'const gone = require("./gone");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        try:
            lab_dist.esbuild_roots(self.root, self.ext)
        except unittest.SkipTest as e:
            self.fail("a missing relative module is an error, never a skip: %r" % e)
        except ValueError as e:
            self.assertIn("Cannot find module './gone'", str(e))
        else:
            self.fail("a missing relative module raised nothing")

    def test_a_config_that_logs_at_require_time_is_read_whole(self):
        """The reader writes the JSON to a file node is handed, never to stdout, so a console.log in the config
        cannot corrupt the read (round 6 read stdout, and a logging config would have been "printed no JSON"). On
        the real config nothing logs at require; this pins the day one starts to."""
        _write(self.config, 'console.log("loading the config");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        self.assertEqual(self.roots(), ["ext"])

    def test_a_config_that_ends_the_process_before_the_file_is_written_is_an_error_carrying_both_streams(self):
        """The wrote-no-file branch: a config that calls process.exit(0) at require time leaves node's exit at 0 and
        no file for the reader to have written. The error names the config and carries the stdout head and the
        stderr, whole (it fits in head plus tail, so it is emitted once), the two streams every derivation error
        attaches."""
        _write(self.config, 'console.log("bye from the config");\nprocess.stderr.write("and on stderr\\n");\nprocess.exit(0);\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        msg = str(cm.exception)
        self.assertIn("wrote no JSON", msg)
        self.assertIn(self.config, msg)
        self.assertIn("stdout head: bye from the config", msg)
        self.assertIn("stderr: and on stderr", msg)
        self.assertNotIn("stderr head:", msg, "a stream that fits is emitted once, not as a head and a tail")

    def test_a_require_past_its_bound_is_an_error_naming_the_bound_and_the_stderr(self):
        """A config that wedges at require time (a BOUNDED busy loop: 4 s, then a valid export, so a mutant that
        dropped the timeout finishes instead of hanging the run) under a 1 s bound injected for the test: a
        ValueError, never a SkipTest, naming the config, the bound and the stderr node had written before the
        loop, raised from the TimeoutExpired, whose `timeout` is the bound as handed to subprocess.run (an
        exact pin: a bound dropped, tripled or padded by a second shows there, where a wall-clock assertion let a
        2 s bound through and added load sensitivity)."""
        _write(self.config, 'process.stderr.write("spinning\\n");\nconst end = Date.now() + 4000;\nwhile (Date.now() < end) {}\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with patch.object(lab_dist, "_EXPORTS_TIMEOUT", 1):
            try:
                lab_dist.esbuild_roots(self.root, self.ext)
            except unittest.SkipTest as e:
                self.fail("a require past its bound is a hard error, never a skip: %r" % e)
            except ValueError as e:
                msg = str(e)
                self.assertIn(self.config, msg)
                self.assertIn("in 1 s", msg)
                self.assertIn("stderr: spinning", msg)
                self.assertIsInstance(e.__cause__, subprocess.TimeoutExpired)
                self.assertEqual(e.__cause__.timeout, 1, "the bound handed to subprocess.run is _EXPORTS_TIMEOUT itself")
            else:
                self.fail("a require past its bound raised nothing")

    def test_a_missing_extension_dir_is_an_error_naming_it_not_node(self):
        """A missing cwd raises the same FileNotFoundError as a missing node, and round 6 reported both as "node is
        not on PATH". The directory is checked before node runs, so the message names it, and an extension dir
        that is a FILE takes the same door (it raised NotADirectoryError, uncaught)."""
        for ext in (os.path.join(self.root, "nope"), self.config):
            with self.assertRaises(ValueError) as cm:
                lab_dist.esbuild_roots(self.root, ext)
            self.assertIn("%s is not a directory" % ext, str(cm.exception))
            self.assertNotIn("node is not on PATH", str(cm.exception))
        os.remove(self.config)              # the dir exists and holds no config: loud, naming the absolute path,
        try:                                # never the missing-package skip (the request is absolute, not bare)
            lab_dist.esbuild_roots(self.root, self.ext)
        except unittest.SkipTest as e:
            self.fail("a missing config is an error, never a skip: %r" % e)
        except ValueError as e:
            self.assertIn("Cannot find module '%s'" % self.config, str(e))
        else:
            self.fail("a missing config raised nothing")

    def test_a_relative_extension_dir_is_resolved_before_node_runs(self):
        """node runs with the extension dir as its cwd, so a relative config path handed to require resolved
        against that dir, one level too deep, and an existing config failed with "Cannot find module". The path
        is made absolute first, in esbuild_exports itself (esbuild_roots does the same for its own joins, so the
        read is called directly here too, or its own abspath would be masked): from the checkout, "ext" derives
        the same trees as the absolute dir, and the config path the read returns is absolute."""
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.root)
        try:
            config, exports = lab_dist.esbuild_exports("ext")
        except unittest.SkipTest as e:      # a relative config path reaches node as a bare specifier and reads as a
            self.fail("a relative extension dir must not read as a missing package: %r" % e)   # missing package
        self.assertEqual(config, self.config)
        self.assertIn("extension", exports)
        self.assertEqual([os.path.relpath(p, self.root) for p in lab_dist.esbuild_roots(self.root, "ext")],
                         ["ext", "tools", "ui"])

    # Decision 2 of review round 7, over the served modules' own call: the environment skips, the config errors.
    def test_a_served_caller_skips_when_node_finds_no_package_the_config_requires(self):
        """The real config's first line, `require("esbuild")`, on a checkout without the extension's node_modules:
        the same precondition the build half skips on (esbuild cannot build there either), so copy_dist raises
        SkipTest naming the package and the config, and no served class errors at setUpClass over an environment
        it could not have built in. Round 6 raised ValueError here, and every served class ERRORed where it used
        to skip. A scoped package takes the same door."""
        _write(self.config, 'const esbuild = require("esbuild");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with self.assertRaises(unittest.SkipTest) as cm:
            self.served_call()
        self.assertIn("no package 'esbuild'", str(cm.exception))
        self.assertIn(self.config, str(cm.exception))
        _write(self.config, 'const s = require("@scope/pkg");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with self.assertRaises(unittest.SkipTest) as cm:
            self.served_call()
        self.assertIn("no package '@scope/pkg'", str(cm.exception))

    def test_the_served_callers_premise_holds_against_nodes_global_folders(self):
        """The test above assumes no esbuild resolves. Node consults its global folders after the node_modules
        walk fails: NODE_PATH, then $HOME/.node_modules and $HOME/.node_libraries, then $PREFIX/lib/node. A
        developer with an esbuild in any of the first three would have seen the derivation succeed, the fake
        builder fail, and the test fail on the builder's message instead of the premise (round 8). served_call
        drops NODE_PATH and binds HOME to this test's base for the call, so an esbuild planted on NODE_PATH, and one
        under $HOME/.node_modules, both leave the served skip naming the package. $PREFIX/lib/node cannot be
        scrubbed and stays the premise."""
        _write(self.config, 'const esbuild = require("esbuild");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        planted = os.path.join(self.base, "global")
        _write(os.path.join(planted, "esbuild", "index.js"), "module.exports = { version: '0.0.0' };\n")
        with patch.dict(os.environ, {"NODE_PATH": planted}):
            with self.assertRaises(unittest.SkipTest) as cm:
                self.served_call()
        self.assertIn("no package 'esbuild'", str(cm.exception))
        home = os.path.join(self.base, "home")
        _write(os.path.join(home, ".node_modules", "esbuild", "index.js"), "module.exports = { version: '0.0.0' };\n")
        with patch.dict(os.environ, {"HOME": home}):
            with self.assertRaises(unittest.SkipTest) as cm:
                self.served_call()
        self.assertIn("no package 'esbuild'", str(cm.exception))
        # the control: the planted packages DO resolve when the environment reaches node unscrubbed
        with patch.dict(os.environ, {"NODE_PATH": planted}):
            self.assertEqual(self.roots(), ["ext"], "NODE_PATH resolves the planted esbuild for a plain derivation")

    def test_a_served_caller_errors_when_the_config_itself_does_not_load(self):
        """Everything but the missing bare package stays loud from the served call: a syntax error, and a missing
        relative module (MODULE_NOT_FOUND for a file of this checkout). SkipTest is caught first and fails, so a
        harness that mapped every load failure to a skip fails here instead of skipping."""
        for text, expect in (('module.exports = { x: { entryPoints: ["src/extension.ts"] } };\nconst broken = [;\n', "SyntaxError"),
                             ('const gone = require("./gone");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n',
                              "Cannot find module './gone'")):
            _write(self.config, text)
            try:
                self.served_call()
            except unittest.SkipTest as e:
                self.fail("a config that does not load is an error, never a skip: %r" % e)
            except ValueError as e:
                self.assertIn(expect, str(e))
            else:
                self.fail("a config that does not load raised nothing")

    # tests/lab_dist_stub.py, the node preload the two real-tree pins run under where the extension's node_modules are
    # absent. setUp plants a node_modules holding `pkg`; the tests that want a stand-in remove it (no_install), since
    # a node_modules that exists and lacks the package is a stale install the preload declines (tested below).
    def test_the_package_stand_in_covers_every_bare_package_node_cannot_resolve(self):
        """Under the preload, a config that requires bare packages node cannot find, and reads nothing from them,
        derives its trees on a checkout without node_modules, where without it the same config skips (the
        served-caller test above). Three misses at once, one scoped, one a subpath of an ABSENT scoped package:
        round 7 stood in for the one name esbuild, so the day esbuild.js required a second package both real-tree
        pins went back to skipping on CI in silence; SkipTest is caught first and fails, so that shape is red here,
        never a skip."""
        self.no_install()
        _write(self.config, 'const esbuild = require("esbuild");\nconst other = require("other");\nconst s = require("@scope/pkg/sub");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with lab_dist_stub.bare_package_stub():
            try:
                roots = self.roots()
            except unittest.SkipTest as e:
                self.fail("a bare package the stand-in did not cover skipped the derivation: %r" % e)
        self.assertEqual(roots, ["ext"])

    def test_the_package_stand_in_is_inert_where_the_real_package_resolves(self):
        """The other half of the preload's rule: a specifier that resolves loads the REAL module, untouched. An
        esbuild installed under this ext's node_modules exports a version the config folds into an entry path
        (`../tools/<version>.ts`, on disk), so the derived roots prove the real package's data flowed through; a
        stand-in that shadowed every bare name would throw on `esbuild.version` here, and a softened one answering
        undefined would resolve nothing under tools/."""
        _write(os.path.join(self.ext, "node_modules", "esbuild", "index.js"), 'module.exports = { version: "9.9.9" };\n')
        _write(os.path.join(self.root, "tools", "9.9.9.ts"), "export const v = 9;\n")
        _write(self.config, 'const esbuild = require("esbuild");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts", "../tools/" + esbuild.version + ".ts"] } };\n')
        with lab_dist_stub.bare_package_stub():
            self.assertEqual(self.roots(), ["ext", "tools"])
            _, exports = lab_dist.esbuild_exports(self.ext)
        self.assertIn("../tools/9.9.9.ts", exports["x"]["entryPoints"], "the real package's version, not a stand-in's")

    def test_the_package_stand_in_refuses_every_read_at_load_naming_the_read(self):
        """A stand-in is a dependency of the BUILD, not of the exported data, so every read of it at require time
        fails loudly, the error naming tests/lab_dist_stub.py, the package and the read: a property (a plain empty
        object would have answered undefined and let "undefined" flow into the exported data), the `in` operator
        and enumeration (Object.keys, a spread: an empty object would answer false and [] and let the config take
        a branch the real package never takes), an own-property lookup, and the module exported whole, which the
        READER's JSON.stringify reads (toJSON first), named as the reader's read, not the config's. The message
        names the requiring file (round 9: only the config's own requires are stood in, and the file is named
        rather than assumed)."""
        self.no_install()
        cases = (
            ('const v = esbuild.version;\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], banner: { js: "// " + v } } };\n',
             "read esbuild.version"),
            ('const e = "context" in esbuild ? ["src/extension.ts"] : ["../tools/extra/thing.ts"];\n'
             'module.exports = { x: { entryPoints: e } };\n', "tested 'context' in esbuild"),
            ('const k = Object.keys(esbuild);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], keys: k } };\n',
             "enumerated esbuild"),
            ('const copy = { ...esbuild };\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], copy } };\n',
             "enumerated esbuild"),
            ('const own = Object.prototype.hasOwnProperty.call(esbuild, "build");\n'
             'module.exports = { x: { entryPoints: ["src/extension.ts"], own } };\n', "looked up esbuild's own property 'build'"),
            ('module.exports = { x: { entryPoints: ["src/extension.ts"] }, esbuild };\n',
             "the reader's JSON.stringify read esbuild.toJSON"),
        )
        with lab_dist_stub.bare_package_stub():
            for body, expect in cases:
                _write(self.config, 'const esbuild = require("esbuild");\n' + body)
                with self.assertRaises(ValueError, msg=body) as cm:
                    lab_dist.esbuild_roots(self.root, self.ext)
                self.assertIn("tests/lab_dist_stub.py", str(cm.exception), body)
                self.assertIn("for 'esbuild'", str(cm.exception), body)
                self.assertIn(expect, str(cm.exception), body)
                self.assertIn("here: " + self.config + " ", str(cm.exception), "the requiring file is named")

    def test_a_skip_inside_the_stand_ins_block_is_a_failure_naming_the_package(self):
        """The one skip the derivation raises is the missing-bare-package one, and inside the stand-in's block it
        means the preload did not take effect (NODE_OPTIONS dropped by a node wrapper), the reader filed as the
        environment a request the preload's rule declined, or the config resolved the package with require.resolve,
        which the stand-in does not cover (only Module._load is wrapped): the block re-raises it as AssertionError
        naming tests/lab_dist_stub.py and the package, so the
        real-tree pins go red there instead of skipping. Driven with a config that throws the reader's own
        classification shape by hand (a MODULE_NOT_FOUND naming a bare package the preload never saw, with the
        requireStack node sets, starting at the config), since under the preload no real bare miss reaches the
        reader. SkipTest is caught first and fails: before the conversion this test reported as skipped, not red."""
        _write(self.config, 'const e = new Error("Cannot find module \'ghost\'");\ne.code = "MODULE_NOT_FOUND";\n'
                            'e.requireStack = [__filename];\nthrow e;\n')
        try:
            with lab_dist_stub.bare_package_stub():
                lab_dist.esbuild_roots(self.root, self.ext)
        except unittest.SkipTest as e:
            self.fail("a skip escaped the stand-in's block: %r" % e)
        except AssertionError as e:
            self.assertIn("tests/lab_dist_stub.py", str(e))
            self.assertIn("'ghost'", str(e))
            self.assertIsInstance(e.__cause__, unittest.SkipTest)
        else:
            self.fail("the skip inside the block raised nothing")

    # Round 9: the three tests that gate the stand-in, and the reader's classification, agree; each edge is pinned
    # plain and under the preload.
    def test_a_bare_miss_inside_an_installed_package_is_the_same_error_with_and_without_the_stand_in(self):
        """A package that IS installed under this ext's node_modules hard-requires a bare package that is not: the
        requirer is the package, not the config, so the miss is node's error both ways (a broken install, a
        dependency of a dependency missing), never the environment and never a stand-in. Plain, the round-8 reader
        skipped here naming 'b'; under the round-8 preload the package got a stand-in and the derivation went
        through. Both messages carry node's diagnosis, the require stack naming the package's file, and the
        reader's line saying why."""
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"), 'const b = require("b");\nmodule.exports = { version: b.version };\n')
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'b'", msg, under_stub)
            self.assertIn(os.path.join(self.ext, "node_modules", "a", "index.js"), msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_an_installed_packages_optional_require_probe_sees_the_real_miss_under_the_stand_in(self):
        """The reason the requirer matters: an installed package that probes for an optional peer
        (`try { require("pnp-probe") } catch {}`, esbuild's own pnpapi probe is this shape) takes the catch branch
        in the real environment. Under the round-8 preload the probe received a truthy stand-in and the package took
        the other branch, so the derivation diverged from the real one in silence (here: the entry path built from
        the package's answer named a file that does not exist, and the tools tree dropped out). Now the probe
        throws inside the package under the preload as it does without, and the two derivations are equal."""
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"),
               'let pnp = null;\ntry { pnp = require("pnp-probe"); } catch (e) { if (e.code !== "MODULE_NOT_FOUND") throw e; }\n'
               'module.exports = { flavor: pnp ? "plugnplay" : "plain" };\n')
        _write(os.path.join(self.root, "tools", "plain.ts"), "export const p = 1;\n")
        _write(self.config, 'const a = require("a");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts", "../tools/" + a.flavor + ".ts"] } };\n')
        plain = self.roots()
        with lab_dist_stub.bare_package_stub():
            under = self.roots()
        self.assertEqual(plain, ["ext", "tools"], "the probe took the catch branch and the package answered plain")
        self.assertEqual(under, plain, "the same derivation under the preload")

    def test_a_subpath_into_an_installed_package_is_an_error_not_the_environment(self):
        """`require("esbuild/lib/nope")` with esbuild installed (a package.json main and its file; the real esbuild
        has no exports field, so this is its path) and `require("@scope/pkg/sub")` with @scope/pkg installed: the
        package root is on the lookup paths, so the miss is a config typo, or an install at a version without that
        file, and both the reader (plain) and the preload (under the stand-in) treat it as node's error. Round 8
        filed both as the environment: a skip plain, a stand-in under the preload, so a typo skipped every served
        lab with a misleading reason on a box with node_modules and the real-tree pins passed green. The
        covering test above keeps `@scope/pkg/sub` with the package ABSENT standing in."""
        _write(os.path.join(self.ext, "node_modules", "esbuild", "package.json"), '{"name": "esbuild", "main": "lib/main.js"}\n')
        _write(os.path.join(self.ext, "node_modules", "esbuild", "lib", "main.js"), 'module.exports = { version: "9.9.9" };\n')
        _write(os.path.join(self.ext, "node_modules", "@scope", "pkg", "index.js"), "module.exports = {};\n")
        for request, root in (("esbuild/lib/nope", "esbuild"), ("@scope/pkg/sub", os.path.join("@scope", "pkg"))):
            _write(self.config, 'const e = require("esbuild");\nconst s = require("%s");\n'
                                'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n' % request)
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn("Cannot find module '%s'" % request, msg, (request, under_stub))
                self.assertIn("a subpath of a package that IS installed (%s)" % os.path.join(self.ext, "node_modules", root),
                              msg, (request, under_stub))
                self.assertNotIn("tests/lab_dist_stub.py", msg, (request, under_stub))

    def test_a_node_modules_lacking_a_package_the_config_requires_is_red_under_the_stand_in(self):
        """The staleness pin's docstring claim, made true: a node_modules that exists beside the config and lacks
        one package the config requires (node_modules predating a newly added dependency) is a stale install, not
        the checkout without node_modules the stand-in exists for. Plain, the served labs skip there as they do
        without node_modules; under the preload the stand-in DECLINES, throwing an error that names
        tests/lab_dist_stub.py, the package, the requiring file and the directory, so the real-tree pins go red
        there instead of running green through a stand-in (round 8) or skipping (round 6). Not a converted skip:
        the error reaches the reader and exits node, and the block sees a ValueError."""
        _write(os.path.join(self.ext, "node_modules", "esbuild", "index.js"), 'module.exports = { version: "9.9.9" };\n')
        _write(self.config, 'const esbuild = require("esbuild");\nconst fresh = require("newdep");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with self.assertRaises(unittest.SkipTest) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("no package 'newdep'", str(cm.exception), "plain, the served labs skip on a stale install")
        msg = self.derivation_error(under_stub=True)
        self.assertIn("tests/lab_dist_stub.py", msg)
        self.assertIn("declines to stand in for 'newdep'", msg)
        self.assertIn("required by " + self.config, msg)
        self.assertIn(os.path.join(self.ext, "node_modules") + " exists and holds no such package", msg)
        self.assertIn("npm ci", msg)

    # Round 10: the requirer test reads the requirer's filename, the reader words a non-config requirer's miss by
    # where the requirer lies, require.resolve is named as outside the stand-in, and every error carries the head of
    # node's stderr beside its tail.
    def test_a_probe_inside_an_installed_packages_function_called_at_load_sees_the_real_miss_under_the_stand_in(self):
        """The round-9 gate read the DEPTH of the load, not the requirer: a bare require executed inside an installed
        package's FUNCTION that the config calls at load time (`const a = require("a"); a.detect()`) arrived at the
        config's depth with the package's file as its parent and was stood in, so the probe here took the other
        branch under the preload and the tools tree dropped out of the derivation in silence (['ext'] under the
        stand-in, ['ext', 'tools'] plain). The gate now compares the requirer's filename with the module the reader's
        entry loaded, so the probe throws inside the package under the preload as it does without, and the two
        derivations are equal. The top-level twin of this shape is the probe test above."""
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"),
               'module.exports = { detect() { try { require("pnp-probe"); return "plugnplay"; } catch (e) { '
               'if (e.code !== "MODULE_NOT_FOUND") throw e; return "plain"; } } };\n')
        _write(os.path.join(self.root, "tools", "plain.ts"), "export const p = 1;\n")
        _write(self.config, 'const a = require("a");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts", "../tools/" + a.detect() + ".ts"] } };\n')
        plain = self.roots()
        with lab_dist_stub.bare_package_stub():
            under = self.roots()
        self.assertEqual(plain, ["ext", "tools"], "the probe took the catch branch and the package answered plain")
        self.assertEqual(under, plain, "the same derivation under the preload")

    def test_a_hard_require_inside_an_installed_packages_function_called_at_load_is_nodes_error_under_the_stand_in(self):
        """The hard twin of the probe: an installed package whose function, called by the config at load, requires a
        bare package that is not installed. Under the round-9 preload the require was stood in and the function's
        read of the stand-in failed with the stand-in's refusal, naming tests/lab_dist_stub.py, where the real
        environment fails with node's error; now both ways carry node's headline, the require stack naming the
        package's file and the reader's line, with the stand-in named nowhere."""
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"),
               'module.exports = { version() { return require("b").version; } };\n')
        _write(self.config, 'const a = require("a");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts", "../tools/" + a.version() + ".ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'b'", msg, under_stub)
            self.assertIn(os.path.join(self.ext, "node_modules", "a", "index.js"), msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_bare_miss_inside_a_module_the_config_loaded_from_the_checkout_names_the_module_not_an_install(self):
        """A helper file the config requires relatively (`../tools/helper.js`, outside the extension dir on purpose:
        "under the config's directory" would misclassify it) requires a bare package that is not installed, on a
        checkout without node_modules. The requirer is not the config, so the miss is node's error plain and under
        the stand-in (the preload's requirer test fails it); the reader's line used to call every non-config requirer
        an installed package and tell the developer to run npm ci, which changes nothing here. The line now says the
        helper is a module the config loaded and that only the config's own requires are filed as the environment or
        stood in: move the require to esbuild.js, or install the package. That line is for a root ABSENT from the
        helper's chain (`ghost3` is installed nowhere); with the root present the miss is a subpath the installed
        package does not have, and the line names the root (the round-13 test below)."""
        self.no_install()
        helper = os.path.join(self.root, "tools", "helper.js")
        _write(helper, 'const g = require("ghost3");\nmodule.exports = { version: g.version };\n')
        _write(self.config, 'const h = require("../tools/helper.js");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"], banner: { js: "// " + h.version } } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'ghost3'", msg, under_stub)
            self.assertIn(helper + " requires 'ghost3'", msg, under_stub)
            self.assertIn(helper + " is a module the config loaded, and only the config's own requires are filed as the "
                          "environment or stood in; move the require to esbuild.js or install the package", msg, under_stub)
            self.assertNotIn("run npm ci", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_an_installed_requirer_reached_through_a_symlinked_node_modules_keeps_the_install_wording(self):
        """The discriminator behind the test above is the realpath: a requirer is installed when its realpath lies
        under the realpath of an entry of the lookup chain of a module above it in the require stack, the config's
        chain added (the list `require.resolve.paths` reports for each, from its realpath; round 10 read the config's
        chain alone, and the helper-sibling test below is the shape that needed the others; round 12 adds the config's
        chain outright, since the stack holds each module's first loader and can lack the config). A
        node_modules that is a symlink to a store whose directory is not itself named node_modules (this checkout's
        own layout, with the store renamed) keeps the installed wording, which a node_modules path-segment test over
        node's realpath would lose; the requiring file is named by its realpath, as node reports it."""
        shutil.rmtree(os.path.join(self.ext, "node_modules"))
        store = os.path.join(self.base, "store")
        _write(os.path.join(store, "a", "index.js"), 'const b = require("b");\nmodule.exports = { version: b.version };\n')
        os.symlink(store, os.path.join(self.ext, "node_modules"))
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'b'", msg, under_stub)
            self.assertIn(os.path.join(store, "a", "index.js") + " requires 'b'", msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertNotIn("is a module the config loaded", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_require_resolve_of_a_bare_package_is_outside_the_stand_in_and_the_blocks_failure_says_so(self):
        """The preload wraps Module._load, the door every require() takes; require.resolve() resolves through
        Module._resolveFilename and makes no load, so a config that resolves a missing bare package that way is not
        stood in: plain, the reader files the miss as the environment (the error's requireStack starts at the config
        and the root is nowhere), a skip naming the package; inside the block that skip is the AssertionError, which
        names this cause beside the other two (round 10; before, the message named only NODE_OPTIONS and the two rules
        disagreeing, both false for this shape). The real esbuild.js has no require.resolve. The control: a require()
        of the same name in the same block is stood in."""
        self.no_install()
        _write(self.config, 'const p = require.resolve("ghostr");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"], inject: [p] } };\n')
        with self.assertRaises(unittest.SkipTest) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("no package 'ghostr'", str(cm.exception), "plain, the reader files the miss as the environment")
        try:
            with lab_dist_stub.bare_package_stub():
                lab_dist.esbuild_roots(self.root, self.ext)
        except unittest.SkipTest as e:
            self.fail("a skip escaped the stand-in's block: %r" % e)
        except AssertionError as e:
            self.assertIn("require.resolve, which the stand-in does not cover", str(e))
            self.assertIn("'ghostr'", str(e))
            self.assertIn("tests/lab_dist_stub.py", str(e))
        else:
            self.fail("require.resolve of a missing bare package raised nothing inside the block")
        _write(self.config, 'const g = require("ghostr");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with lab_dist_stub.bare_package_stub():
            self.assertEqual(self.roots(), ["ext"], "the control: require() of the same name is stood in")

    def test_node_output_carries_a_short_stream_once_and_both_ends_of_a_long_one(self):
        """The surface itself, over synthetic streams: a stderr that fits in head plus tail is emitted once, whole,
        under the label "stderr: " (no head, no tail, nothing counted as omitted); one that does not fit is emitted
        as its first _STDERR_HEAD chars, the count of chars left out and its last `tail` chars, the two segments
        never overlapping and never sharing a char; the stdout head is 200 chars either way. The count is exactly
        the chars between the two shown pieces (round 11): whitespace at the inner cuts is shown, not dropped, so the
        shown head, the count and the shown tail add up to the stream, and only the stream's outer ends are trimmed
        (before, each piece was stripped at both ends, and a newline at a cut left the sum short of the stream)."""
        head = lab_dist._STDERR_HEAD
        fits = "a" * head + "z" * 500
        msg = lab_dist._node_output("out", fits)
        self.assertIn("stderr: " + fits + "; stdout head: out", msg)
        self.assertNotIn("stderr head:", msg)
        self.assertNotIn("omitted", msg)
        long = "a" * head + "b" * 77 + "z" * 500
        msg = lab_dist._node_output("o" * 300, long, tail=500)
        self.assertIn("stderr head: " + "a" * head + " [77 chars omitted]; stderr tail: " + "z" * 500 + "; stdout head: " + "o" * 200,
                      msg)
        self.assertNotIn("b", msg.split("stderr head: ")[1].split("; stdout head")[0], "the 77 chars between the ends are the omitted ones")
        msg = lab_dist._node_output("", "n" * (head + 2000 + 1), 2000)
        self.assertIn("[1 chars omitted]", msg, "the exit-1 caller's tail is 2000, and one char over the budget parts the stream")
        # newlines at both inner cuts (the head's last ten chars, the tail's first ten): shown, and the sum is the stream
        cut = "H" * (head - 10) + "\n" * 10 + "M" * 100 + "\n" * 10 + "T" * 490
        msg = lab_dist._node_output("", cut, tail=500)
        shown_head = msg.split("stderr head: ")[1].split(" [100 chars omitted]; stderr tail: ")[0]
        shown_tail = msg.split("; stderr tail: ")[1].split("; stdout head: ")[0]
        self.assertEqual(shown_head, "H" * (head - 10) + "\n" * 10, "the head is shown whole to the cut")
        self.assertEqual(shown_tail, "\n" * 10 + "T" * 490, "the tail is shown whole from the cut")
        self.assertEqual(len(shown_head) + 100 + len(shown_tail), len(cut),
                         "the omitted count is exactly the chars between the two shown pieces")
        # the outer ends are trimmed and not counted: a leading and a trailing newline around a parted stream
        outer = "\n" + "a" * (head - 1) + "b" * 21 + "z" * 499 + "\n"
        msg = lab_dist._node_output("", outer, tail=500)
        self.assertIn("stderr head: " + "a" * (head - 1) + " [21 chars omitted]; stderr tail: " + "z" * 499 + "; stdout head: ", msg)

    def test_a_long_config_path_keeps_nodes_headline_and_the_readers_line_in_the_error(self):
        """The bare-miss shape (an installed package requires a missing `b`) over a config path of 500 chars or more,
        whatever TMPDIR the run has: node's stderr starts with the headline and ends with the reader's line, and its
        stack and requireStack dump between them repeat the config's path eight times (nine under the preload), so
        the stream ran to 1038 + 8 x len(ext) chars and the 2000-char tail alone lost the headline once the ext path
        passed about 121 chars. xdist nests the conftest's temp root one level deeper and a sweep's TMPDIR is longer
        still, so the same-error and subpath tests above went red under `-n` at a TMPDIR of about 60 chars and alone
        at about 80 while CI's /tmp stayed green: deterministic on path length, not on order or fan-out. The message
        now carries the head of the stream as well, so both the headline and the reader's line are in it at this
        length, as a head and a tail (the stream does not fit whole here), plain and under the stand-in."""
        self.pad_checkout(500)
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"), 'const b = require("b");\nmodule.exports = { version: b.version };\n')
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'b'", msg, under_stub)
            self.assertIn(os.path.join(self.ext, "node_modules", "a", "index.js") + " requires 'b'", msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertIn("stderr head: ", msg, under_stub)
            self.assertIn("chars omitted]; stderr tail: ", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_long_config_path_keeps_an_uncaught_errors_headline_in_the_error(self):
        """The uncaught-throw shape: the preload's refusal to stand in for `newdep` beside a node_modules that lacks it
        is thrown, rethrown by the reader (no MODULE_NOT_FOUND code) and left to node, which prints the rethrow's
        location (`[eval]:NN`), its source line, a caret and a blank line BEFORE the headline, so a one-line head
        would have carried the location and missed the stand-in's name; the tail alone lost it once the stream passed
        2000 chars. The message names the config and its node_modules, so the stream grows three chars per char of
        config path here (two in the message, one in the stack), and 800 puts it past the head-plus-tail budget at
        any TMPDIR: the head, a run of chars, carries the preamble and the stand-in's name, and the stream is emitted
        as a head and a tail. The pins are the head's: at this length the tail's reach into the message depends on
        the run's TMPDIR (the preload's path is in two stack frames), which the test above pins instead."""
        self.pad_checkout(800)
        _write(os.path.join(self.ext, "node_modules", "esbuild", "index.js"), 'module.exports = { version: "9.9.9" };\n')
        _write(self.config, 'const esbuild = require("esbuild");\nconst fresh = require("newdep");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        msg = self.derivation_error(under_stub=True)
        self.assertIn("stderr head: [eval]:", msg, "the stream parted, and the head starts at the rethrow's location")
        self.assertIn("tests/lab_dist_stub.py", msg)
        self.assertIn("declines to stand in for 'newdep'", msg)
        self.assertIn("required by " + self.config, msg, "the head reaches past the config's path")

    # Round 11: every lookup chain is computed from its module's realpath and an installed requirer is judged against
    # the chain of every module above it in the require stack; the harness names the config's realpath to the preload
    # in lab_dist.CONFIG_ENV, so the requirer test is exact at any depth and at any time; a subpath into one of node's
    # core modules is never the environment and never stood in.
    def test_a_config_reached_through_a_symlinked_extension_dir_is_judged_by_its_realpath_chain(self):
        """The extension dir is a symlink into a store outside the checkout whose ancestor holds a node_modules (a
        package `a` there). node resolved the config to its realpath and searched from there, so `require("a/nope")`
        is a subpath typo into an installed package; the round-10 reader built the config's chain from the TEXTUAL
        path, found no `a` along it, and filed the typo as the environment (a skip plain; under the stand-in, which
        already read the realpath, the block's AssertionError), and called an installed requirer reached through the
        link a module of the checkout. Now every chain is the realpath's: the typo is the subpath error and the
        requirer keeps the install wording, plain and under the stand-in; and with no node_modules beside the config
        the stand-in still covers the config's own miss through the link, which holds only because the harness
        publishes the config's REALPATH (the requirer's filename, as node reports it), not the path it was given."""
        store = os.path.join(self.base, "store")
        real_ext = os.path.join(store, "ext")
        os.makedirs(store)
        shutil.move(self.ext, real_ext)
        os.symlink(real_ext, self.ext)
        _write(os.path.join(store, "node_modules", "a", "index.js"), "module.exports = { v: 1 };\n")
        _write(self.config, 'const s = require("a/nope");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'a/nope'", msg, under_stub)
            self.assertIn("a subpath of a package that IS installed (%s)" % os.path.join(store, "node_modules", "a"), msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        _write(os.path.join(store, "node_modules", "c", "index.js"), 'const b = require("b");\nmodule.exports = { v: b.v };\n')
        _write(self.config, 'const c = require("c");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'b'", msg, under_stub)
            self.assertIn(os.path.join(store, "node_modules", "c", "index.js") + " requires 'b'", msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertNotIn("is a module the config loaded", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        self.no_install()
        _write(self.config, 'const g = require("ghost");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with lab_dist_stub.bare_package_stub():
            try:
                roots = self.roots()
            except unittest.SkipTest as e:
                self.fail("the config's own miss through the link was filed as the environment: %r" % e)
        self.assertEqual(roots, ["ext"], "the stand-in covers the config through the link: the realpath is what is named")

    def test_a_package_installed_beside_a_helper_of_the_checkout_keeps_the_install_wording(self):
        """The config requires `../tools/helper.js`; the helper requires `x`, installed in the helper's own
        `tools/node_modules` (a per-directory install, off the config's chain); `x` hard-requires a missing `y`. The
        requirer `x` lies under an entry of the HELPER's lookup chain, not the config's, so the round-10 rule (the
        config's chain alone) called it a module of the checkout and said to move the require to esbuild.js, where
        the fix is `npm ci` in tools/. The requirer is now judged against the chain of every module above it in the
        require stack (the helper, then the config), so it keeps the install wording, plain and under the stand-in;
        the helper's own miss (the test above this block's round-10 twin) keeps the checkout wording."""
        self.no_install()
        helper = os.path.join(self.root, "tools", "helper.js")
        x = os.path.join(self.root, "tools", "node_modules", "x", "index.js")
        _write(helper, 'const x = require("x");\nmodule.exports = { version: x.version };\n')
        _write(x, 'const y = require("y");\nmodule.exports = { version: y.version };\n')
        _write(self.config, 'const h = require("../tools/helper.js");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"], banner: { js: "// " + h.version } } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'y'", msg, under_stub)
            self.assertIn(x + " requires 'y'", msg, under_stub)
            self.assertIn("a dependency of an installed package is missing", msg, under_stub)
            self.assertNotIn("is a module the config loaded", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_getter_time_require_by_the_config_is_stood_in_after_another_module_loaded_at_the_same_depth(self):
        """The config's own requires are stood in at any time, the reader's JSON.stringify included, whatever loaded
        in between: getter `a` calls a helper the config loaded, and the helper requires "path" (a load outside any
        load in progress, by a module that is not the config); getter `b` then requires a missing `ghost`. The
        round-10 preload took the last such load for the config, so after the helper's require the config was no
        longer the config and `ghost` was node's error with the stand-in named nowhere; the harness now names the
        config's realpath to the preload, and the requirer test is a comparison against it, so `ghost` is stood in
        and the read of its version fails as the stand-in's refusal naming the read (the shape the round-10
        docstring promised). The control is the getter alone, which round 10 also stood in. Plain, both shapes are
        node's error from the getter, outside the reader's classification, and exit 1."""
        self.no_install()
        helper = os.path.join(self.root, "tools", "helper.js")
        _write(helper, 'module.exports = { touch() { return require("path").sep; } };\n')
        shapes = (
            'const h = require("../tools/helper.js");\n'
            'module.exports = { x: { entryPoints: ["src/extension.ts"] }, get a() { return h.touch(); }, '
            'get b() { return require("ghost").version; } };\n',
            'module.exports = { x: { entryPoints: ["src/extension.ts"] }, get b() { return require("ghost").version; } };\n',
        )
        for text in shapes:
            _write(self.config, text)
            msg = self.derivation_error(under_stub=True)
            self.assertIn("tests/lab_dist_stub.py", msg, text)
            self.assertIn("for 'ghost'", msg, text)
            self.assertIn("read ghost.version", msg, text)
            self.assertIn("here: " + self.config + " ", msg, text)
            msg = self.derivation_error(under_stub=False)
            self.assertIn("Cannot find module 'ghost'", msg, text)
            self.assertNotIn("tests/lab_dist_stub.py", msg, text)

    def test_a_package_a_getter_loaded_is_not_stood_in_for_its_own_misses(self):
        """The other direction of the same defect: a getter on the config's export requires an installed package
        `a`, whose own getter requires an installed `c`, whose top level hard-requires a missing `zeta`. `c` loaded
        outside any load in progress with `a` as its parent, so the round-10 preload recorded it as the config and
        stood in for `zeta`; the derivation then failed as the stand-in's refusal naming `c`, where the real
        environment fails with node's error. Now `c` is not the config and `zeta` is node's error both ways, the
        stand-in named nowhere. The twin with an optional probe in `c` (`try { require("zeta-probe") } catch {}`)
        derived a different tree under the round-10 preload in silence (the probe got a stand-in and `c` answered
        the other flavor, so the tools entry named a file that does not exist); the two derivations are equal now."""
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"), 'module.exports = { get v() { return require("c").v; } };\n')
        _write(os.path.join(self.ext, "node_modules", "c", "index.js"), 'const z = require("zeta");\nmodule.exports = { v: z.v };\n')
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"] }, get v() { return require("a").v; } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'zeta'", msg, under_stub)
            self.assertIn(os.path.join(self.ext, "node_modules", "c", "index.js"), msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        _write(os.path.join(self.ext, "node_modules", "a", "index.js"),
               'module.exports = { get flavor() { return require("c").flavor; } };\n')
        _write(os.path.join(self.ext, "node_modules", "c", "index.js"),
               'let p = null;\ntry { p = require("zeta-probe"); } catch (e) { if (e.code !== "MODULE_NOT_FOUND") throw e; }\n'
               'module.exports = { flavor: p ? "plugnplay" : "plain" };\n')
        _write(os.path.join(self.root, "tools", "plain.ts"), "export const p = 1;\n")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"] }, '
                            'get tool() { return "../tools/" + require("a").flavor + ".ts"; } };\n')
        plain = self.roots()
        with lab_dist_stub.bare_package_stub():
            under = self.roots()
        self.assertEqual(plain, ["ext", "tools"], "the probe took the catch branch and the package answered plain")
        self.assertEqual(under, plain, "the same derivation under the preload")

    def test_a_module_a_pre_existing_require_loaded_before_the_config_is_not_taken_for_it(self):
        """NODE_OPTIONS already holds a `--require <file>` when the block starts (the block keeps it, after its own):
        that file loads before the reader's script, outside any load in progress, with node's preload parent (no
        filename). A preload that latched the first such load as the config would have taken this file for it and
        stood in for nothing the config requires; the round-10 preload stood in for the file's OWN bare miss instead
        (its requires arrived at depth 1 under the record it had just made). With the config named by the harness,
        neither: the config's miss is stood in and the derivation goes through, and the file's own probe of a missing
        bare package sees node's error."""
        self.no_install()
        probe = os.path.join(self.base, "pre-require-saw.txt")
        pre = os.path.join(self.base, "pre.js")
        _write(pre, 'let code = "resolved";\ntry { require("ghostp"); } catch (e) { code = e.code; }\n'
                    'require("fs").writeFileSync(%s, code);\n' % json.dumps(probe))
        _write(self.config, 'const g = require("ghost");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with patch.dict(os.environ, {"NODE_OPTIONS": '--require "%s"' % pre}):
            with lab_dist_stub.bare_package_stub():
                try:
                    roots = self.roots()
                except unittest.SkipTest as e:
                    self.fail("the config's own miss went uncovered with a module loaded before it: %r" % e)
        self.assertEqual(roots, ["ext"], "the config is stood in with a pre-existing --require ahead of it")
        self.assertEqual(_read(probe), "MODULE_NOT_FOUND", "the module loaded before the config saw node's error for its own miss")

    def test_the_harness_names_the_config_to_the_preload_and_without_the_name_it_stands_in_for_nothing(self):
        """The contract between the two files, executed: the reader's node run carries the config's REALPATH in the
        environment variable lab_dist.CONFIG_ENV names, plain and under the stand-in (a config that exports the
        variable's value shows it). The extension dir is reached through a symlink here, so the realpath and the path
        the harness was given differ and a textual publish fails the assertions (round 12; before, the fixture's config
        was its own realpath and a publish of the path as given passed). The reader run by hand inside the block with
        the variable removed gets no stand-in for the config's bare miss and fails from the preload's own refusal,
        which names this file and the variable, so a harness that stopped setting it, or a node the block never meant
        to cover, fails loudly; the same command with the variable set is the block's normal run and writes the
        exports."""
        self.no_install()
        store = os.path.join(self.base, "store")
        real_ext = os.path.join(store, "ext")
        os.makedirs(store)
        shutil.move(self.ext, real_ext)
        os.symlink(real_ext, self.ext)
        real = os.path.realpath(self.config)
        self.assertNotEqual(real, self.config, "the fixture holds: the config's realpath is not the path the harness is given")
        _write(self.config, 'module.exports = { x: { entryPoints: ["src/extension.ts"] }, named: process.env[%s] || null };\n'
                            % json.dumps(lab_dist.CONFIG_ENV))
        _, exports = lab_dist.esbuild_exports(self.ext)
        self.assertEqual(exports["named"], real, "plain: the run carries the config's realpath")
        self.assertNotEqual(exports["named"], self.config, "the realpath, not the path the harness was given")
        with lab_dist_stub.bare_package_stub():
            _, exports = lab_dist.esbuild_exports(self.ext)
        self.assertEqual(exports["named"], real, "and under the stand-in")
        self.assertNotEqual(exports["named"], self.config, "the realpath under the stand-in too")
        _write(self.config, 'const g = require("ghost");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        out = os.path.join(self.base, "by-hand.json")
        with lab_dist_stub.bare_package_stub():
            env = {k: v for k, v in os.environ.items() if k != lab_dist.CONFIG_ENV}
            cmd = ["node", "-e", lab_dist._EXPORTS_READER, self.config, out]
            r = subprocess.run(cmd, cwd=self.ext, capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn("tests/lab_dist_stub.py", r.stderr)
            self.assertIn(lab_dist.CONFIG_ENV + " is not set", r.stderr)
            self.assertIn("'ghost'", r.stderr)
            self.assertNotIn("Cannot find module", r.stderr, "the preload's refusal, not node's error")
            self.assertFalse(os.path.exists(out), "nothing was derived")
            env[lab_dist.CONFIG_ENV] = real
            r = subprocess.run(cmd, cwd=self.ext, capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            self.assertIn("exports", json.load(f), "the control: the same run with the variable set is the stand-in's")

    def test_a_subpath_into_a_core_module_is_an_error_not_the_environment(self):
        """`require("fs/nope")`: `resolve.paths` answers null for a core module's name, and the round-9 `|| []` made
        that an empty lookup list, so "root nowhere on the lookup paths" held for a package present in every node:
        the reader filed the typo as the environment (a skip naming `fs/nope` as a package npm ci would install) and
        the preload stood in for it (the derivation went through in silence on a checkout without node_modules).
        Now a core module's name is never the environment and never stood in: node's error stays, with the reader's
        line naming the core module, plain and under the stand-in (round 12 tests the package's root on the chain
        first, so this wording is for a core module no installed package shadows; the shadowed one is the round-12
        test below). `require("node:fs/nope")` is a different code
        (ERR_UNKNOWN_BUILTIN_MODULE) and was node's error already; pinned beside it. From an installed requirer the
        line is the same, naming the package's file, never `npm ci`."""
        self.no_install()
        for request, headline in (("fs/nope", "Cannot find module 'fs/nope'"), ("node:fs/nope", "No such built-in module: node:fs/nope")):
            _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                % json.dumps(request))
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn(headline, msg, (request, under_stub))
                self.assertNotIn("tests/lab_dist_stub.py", msg, (request, under_stub))
                self.assertNotIn("npm ci", msg, (request, under_stub))
                if request == "fs/nope":
                    self.assertIn(self.config + " requires 'fs/nope', a subpath that node's core module fs does not have", msg, under_stub)
        a = os.path.join(self.ext, "node_modules", "a", "index.js")
        _write(a, 'const s = require("fs/nope");\nmodule.exports = {};\n')
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'fs/nope'", msg, under_stub)
            self.assertIn(a + " requires 'fs/nope', a subpath that node's core module fs does not have", msg, under_stub)
            self.assertNotIn("npm ci", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    # Round 12: the reader and the preload judge a miss by the evidence in order (the package's root on the requirer's
    # chain, then a core module's name), the config's chain is added to the requirer's whatever the require stack
    # holds, a package-imports specifier is never the environment, and the preload realpaths the requirer's filename.
    def test_a_subpath_into_an_installed_package_named_like_a_core_module_keeps_the_install_wording(self):
        """`punycode`, `events`, `buffer`, `util`, `url` and `assert` are core modules AND real npm packages. With
        node_modules/punycode installed, node resolves `punycode/sub` from the chain, and `punycode/nope` is a subpath
        the installed package does not have; the round-11 reader tested the core module's name first (`resolve.paths`
        answers null for it) and called the typo a subpath into node's core module although the package is installed,
        so the installed-subpath line was unreachable for these names. Now the root on the requirer's chain is the
        first evidence: the config gets the installed-subpath wording naming the root, and an installed requirer keeps
        the install wording, plain and under the stand-in, with the core module named nowhere and nothing skipped or
        stood in. The control: `fs/nope` with no `fs` package on the chain keeps the core-module wording. The judgment
        call for `require("punycode/")`, by round: round 12 judged it, with nothing installed, a core-module typo (no
        root, a core module's name) in the reader and the preload alike; round 14 read a trailing slash as an empty
        segment naming no package, so it was node's error alone, no reader line and no stand-in; round 15 judges the
        name segments alone, so `punycode/` is the package punycode's request and judged as `punycode` is: with the
        package installed node resolves it to the package and the derivation loads, with nothing installed the
        core-module line, plain and under the stand-in (both pinned here; no skip is hidden either way). The shapes
        whose NAME segments name no package are
        test_an_empty_scope_or_an_empty_or_dot_name_segment_names_no_package_never_a_root_an_install_or_the_environment;
        the subpath spellings node resolves are
        test_a_subpath_spelling_node_resolves_is_judged_by_its_package_never_by_the_subpath."""
        root = os.path.join(self.ext, "node_modules", "punycode")
        _write(os.path.join(root, "package.json"), '{"name": "punycode", "main": "index.js"}\n')
        _write(os.path.join(root, "index.js"), "module.exports = { v: 1 };\n")
        _write(os.path.join(root, "sub.js"), "module.exports = { s: 1 };\n")
        _write(self.config, 'const s = require("punycode/sub");\nconst n = require("punycode/nope");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'punycode/nope'", msg, under_stub)
            self.assertIn(self.config + " requires 'punycode/nope', a subpath of a package that IS installed (%s)" % root, msg, under_stub)
            self.assertNotIn("core module", msg, under_stub)
            self.assertNotIn("npm ci", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        _write(self.config, 'const p = require("punycode/");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], v: p.v } };\n')
        for under_stub in (False, True):
            with lab_dist_stub.bare_package_stub() if under_stub else contextlib.nullcontext():
                self.assertEqual(self.roots(), ["ext"], (under_stub, "`punycode/` with punycode installed is the package, and loads"))
        a = os.path.join(self.ext, "node_modules", "a", "index.js")
        _write(a, 'const n = require("punycode/nope");\nmodule.exports = {};\n')
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'punycode/nope'", msg, under_stub)
            self.assertIn(a + " requires 'punycode/nope', which node cannot find: a dependency of an installed package is missing",
                          msg, under_stub)
            self.assertNotIn("core module", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        _write(self.config, 'const s = require("fs/nope");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn(self.config + " requires 'fs/nope', a subpath that node's core module fs does not have", msg, under_stub)
            self.assertNotIn("IS installed", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)
        self.no_install()
        _write(self.config, 'const p = require("punycode/");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn("Cannot find module 'punycode/'", msg, under_stub)
            self.assertIn(self.config + " requires 'punycode/', a subpath that node's core module punycode does not have", msg, under_stub)
            self.assertNotIn("IS installed", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_package_a_pre_existing_require_loaded_first_and_the_config_called_into_keeps_the_install_wording(self):
        """node fills a MODULE_NOT_FOUND's requireStack with each module's FIRST loader. A `--require <file>` already on
        NODE_OPTIONS loads the installed package `a` by absolute path before the reader runs; the config then requires
        `a` (the cached module) and calls a function of it that requires a missing `b`. The stack is `a`, the
        pre-required file and node's internal/preload, with the config absent, so the round-11 reader, judging `a`
        against the chains of the modules above it in the stack alone, found none holding `a` and said `a` is a module
        the config loaded and to move the require, where the same disk state without the pre-require says a dependency
        of an installed package is missing, run npm ci. The config's chain is now added to the stack's, so the wording
        is the install's both ways, plain and under the stand-in (which rethrows the miss: `a` is not the config)."""
        a = os.path.join(self.ext, "node_modules", "a", "index.js")
        _write(a, 'module.exports = { version() { return require("b").version; } };\n')
        pre = os.path.join(self.base, "pre.js")
        _write(pre, "require(%s);\n" % json.dumps(os.path.join(self.ext, "node_modules", "a")))
        _write(self.config, 'const a = require("a");\n'
                            'module.exports = { x: { entryPoints: ["src/extension.ts", "../tools/" + a.version() + ".ts"] } };\n')
        with patch.dict(os.environ, {"NODE_OPTIONS": '--require "%s"' % pre}):
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn("Cannot find module 'b'", msg, under_stub)
                self.assertIn(a + " requires 'b'", msg, under_stub)
                self.assertIn("a dependency of an installed package is missing", msg, under_stub)
                self.assertNotIn("is a module the config loaded", msg, under_stub)
                self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_package_imports_specifier_is_never_the_environment_and_never_stood_in(self):
        """`require("#missing/thing")` is a package-imports specifier, which the nearest package.json's `imports` map
        resolves and npm ci cannot install. The round-11 bare test accepted it (not `./x`, not absolute), so with no
        imports map the reader filed the miss as the environment (a skip naming `#missing/thing` as a package npm ci
        would install) and the preload stood in for it; with an imports map sending it to a package that is not
        installed node's error carries no requireStack, so the reader rethrew while the preload still stood in, and the
        two rules disagreed. Now a request starting with `#` is node's error, plain and under the stand-in, in every
        shape: no package.json, one mapping it to a missing package, and an imports map lacking the entry (a different
        code, ERR_PACKAGE_IMPORT_NOT_DEFINED, and node's error already; pinned beside the others)."""
        self.no_install()
        _write(self.config, 'const t = require("#missing/thing");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        package_json = os.path.join(self.ext, "package.json")
        for shape, headline in ((None, "Cannot find module '#missing/thing'"),
                                ({"imports": {"#missing/thing": "ghost-target"}}, "Cannot find module '#missing/thing'"),
                                ({"imports": {"#other": "./esbuild.js"}}, 'Package import specifier "#missing/thing" is not defined')):
            if shape is None:
                self.assertFalse(os.path.exists(package_json), "the fixture holds: no package.json beside the config")
            else:
                _write(package_json, json.dumps(shape) + "\n")
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn(headline, msg, (shape, under_stub))
                self.assertNotIn("npm ci", msg, (shape, under_stub))
                self.assertNotIn("tests/lab_dist_stub.py", msg, (shape, under_stub))

    def test_the_stand_in_covers_the_config_through_a_symlinked_extension_dir_under_preserve_symlinks(self):
        """NODE_OPTIONS already carries `--preserve-symlinks` when the block starts (the block keeps it): node then
        names a module by the path it was reached through, so a config reached through a symlinked extension dir has
        the textual path as its filename while the harness publishes its realpath. The round-11 preload compared the
        two as strings, found them unequal and rethrew the config's own bare miss: the reader filed it as the
        environment and the block failed with its AssertionError, none of whose causes was the flag. The preload now
        realpaths the requirer's filename before the compare, so the config's miss is stood in through the link under
        the flag, and a helper's miss (not the config, by realpath either) stays node's error with the stand-in named
        nowhere. The default symlink mode's twin is the symlinked-extension-dir test above."""
        self.no_install()
        store = os.path.join(self.base, "store")
        real_ext = os.path.join(store, "ext")
        os.makedirs(store)
        shutil.move(self.ext, real_ext)
        os.symlink(real_ext, self.ext)
        _write(self.config, 'const g = require("ghost");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with patch.dict(os.environ, {"NODE_OPTIONS": "--preserve-symlinks"}):
            with lab_dist_stub.bare_package_stub():
                try:
                    roots = self.roots()
                except unittest.SkipTest as e:
                    self.fail("the config's own miss through the link was filed as the environment under the flag: %r" % e)
            self.assertEqual(roots, ["ext"], "the stand-in covers the config through the link under --preserve-symlinks")
            helper = os.path.join(self.root, "tools", "helper.js")
            _write(helper, 'const g = require("ghost3");\nmodule.exports = { version: g.version };\n')
            _write(self.config, 'const h = require("../tools/helper.js");\n'
                                'module.exports = { x: { entryPoints: ["src/extension.ts"], banner: { js: "// " + h.version } } };\n')
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn("Cannot find module 'ghost3'", msg, under_stub)
                self.assertIn(helper + " requires 'ghost3'", msg, under_stub)
                self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_without_the_variable_a_miss_whose_root_is_present_is_nodes_error_and_a_bare_miss_the_refusal(self):
        """The order of the preload's tests, pinned: with the variable absent, the refusal fires only for a miss the
        preload would otherwise have judged, after the root and core-module test and before the requirer test. The
        reader run by hand inside the block with the variable removed, on `fs/nope` (a core module's subpath) and on
        `pkg/nope` (a subpath into the package setUp installs), exits 1 with node's headline and the reader's own line
        and never the refusal, so node's error reached the reader; the same run on a bare miss with no root, `ghost`
        on a checkout without node_modules, is the refusal naming the variable and this file. A preload that tested
        the variable first would refuse all three and hide the reader's classification behind its own message. The
        shipped order was already this one; the pin is what was missing."""
        out = os.path.join(self.base, "by-hand.json")
        with lab_dist_stub.bare_package_stub():
            env = {k: v for k, v in os.environ.items() if k != lab_dist.CONFIG_ENV}
            cmd = ["node", "-e", lab_dist._EXPORTS_READER, self.config, out]
            for request, line in (("fs/nope", "a subpath that node's core module fs does not have"),
                                  ("pkg/nope", "a subpath of a package that IS installed (%s)" % os.path.join(self.ext, "node_modules", "pkg"))):
                _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                    % json.dumps(request))
                r = subprocess.run(cmd, cwd=self.ext, capture_output=True, text=True, env=env, timeout=60)
                self.assertEqual(r.returncode, 1, (request, r.stderr))
                self.assertIn("Cannot find module '%s'" % request, r.stderr, request)
                self.assertIn(self.config + " requires '%s', %s" % (request, line), r.stderr, request)
                self.assertNotIn("tests/lab_dist_stub.py", r.stderr, request)
                self.assertNotIn("is not set", r.stderr, request)
                self.assertFalse(os.path.exists(out), request)
            self.no_install()
            _write(self.config, 'const g = require("ghost");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
            r = subprocess.run(cmd, cwd=self.ext, capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 1, r.stderr)
            self.assertIn("tests/lab_dist_stub.py", r.stderr)
            self.assertIn(lab_dist.CONFIG_ENV + " is not set", r.stderr)
            self.assertNotIn("Cannot find module", r.stderr, "the preload's refusal, not node's error")
            self.assertFalse(os.path.exists(out), "nothing was derived")

    # Round 13: the root on the requirer's chain gives the installed-subpath wording for any requirer, and a one-segment
    # scoped name is bare in neither rule. Round 14: one segment rule in both, for the bare shape and the package's name.
    def test_a_subpath_typo_in_a_helper_with_the_package_on_its_chain_names_the_root_not_a_package_to_install(self):
        """A helper the config requires relatively requires `pkg/nope` with `pkg` installed on the HELPER's chain, in two
        layouts: the helper inside the extension dir (`ext/tools/helper.js`, setUp's `ext/node_modules/pkg` on its chain)
        and the helper beside its own install (`tools/helper.js` with `tools/node_modules/pkg2`, off the config's chain).
        The reader found the root on the requirer's chain and, the requirer being neither the config nor installed, fell
        through to the round-10 line telling the developer to move the require or install the package, which is
        installed. Now the root present is the evidence for any requirer: the line names the root as installed and the
        miss as a subpath it does not have, a typo in the helper or an install at a version without that file, plain and
        under the stand-in (which rethrows: the helper is not the config), with nothing to install and no npm ci. The
        control: `require("pkg")` from the same helper loads. The round-10 test above keeps the move-or-install line for
        a root ABSENT from the helper's chain. The third leg: an installed requirer with the root on its chain keeps its
        line, a dependency of an installed package is missing, run npm ci, and names the root beside it."""
        _write(os.path.join(self.ext, "node_modules", "pkg", "index.js"), "module.exports = { v: 1 };\n")
        _write(os.path.join(self.root, "tools", "node_modules", "pkg2", "index.js"), "module.exports = { v: 2 };\n")
        inside, beside = os.path.join(self.ext, "tools", "helper.js"), os.path.join(self.root, "tools", "helper.js")
        for helper, spec, request, root in (
                (inside, "./tools/helper.js", "pkg/nope", os.path.join(self.ext, "node_modules", "pkg")),
                (beside, "../tools/helper.js", "pkg2/nope", os.path.join(self.root, "tools", "node_modules", "pkg2"))):
            _write(helper, 'const p = require(%s);\nmodule.exports = { version: p.v };\n' % json.dumps(request))
            _write(self.config, 'const h = require(%s);\n'
                                'module.exports = { x: { entryPoints: ["src/extension.ts"], banner: { js: "// " + h.version } } };\n'
                                % json.dumps(spec))
            for under_stub in (False, True):
                msg = self.derivation_error(under_stub)
                self.assertIn("Cannot find module '%s'" % request, msg, (helper, under_stub))
                self.assertIn(helper + " requires '%s', a subpath of a package that IS installed (%s): a typo in %s, or an install "
                              "at a version without that file" % (request, root, helper), msg, (helper, under_stub))
                self.assertNotIn("install the package", msg, (helper, under_stub))
                self.assertNotIn("is a module the config loaded", msg, (helper, under_stub))
                self.assertNotIn("npm ci", msg, (helper, under_stub))
                self.assertNotIn("tests/lab_dist_stub.py", msg, (helper, under_stub))
            # the control: the package itself loads from the helper, so it is installed where the helper looks
            _write(helper, 'const p = require(%s);\nmodule.exports = { version: p.v };\n' % json.dumps(request.split("/")[0]))
            self.assertEqual(self.roots(), ["ext"], (helper, "the package resolves from the helper"))
        a = os.path.join(self.ext, "node_modules", "a", "index.js")
        _write(a, 'const n = require("pkg/nope");\nmodule.exports = {};\n')
        _write(self.config, 'const a = require("a");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        for under_stub in (False, True):
            msg = self.derivation_error(under_stub)
            self.assertIn(a + " requires 'pkg/nope', which node cannot find: a dependency of an installed package is missing", msg, under_stub)
            self.assertIn("IS installed (%s)" % os.path.join(self.ext, "node_modules", "pkg"), msg, under_stub)
            self.assertIn("npm ci", msg, under_stub)
            self.assertNotIn("install the package", msg, under_stub)
            self.assertNotIn("tests/lab_dist_stub.py", msg, under_stub)

    def test_a_one_segment_scoped_request_is_a_typo_never_an_install_and_never_the_environment(self):
        """`require("@scope")` and `require("@scope/")` name a scope, not a package: npm installs packages under a scope
        directory (`node_modules/@scope/q`) and nothing at the directory itself, so a miss on a one-segment scoped name
        is a typo in the requirer whatever is installed (node itself would load a hand-made `node_modules/@scope/index.js`,
        so the premise is npm's layout, not node's resolver). Both rules took the name as bare and packageName answered
        the scope directory: with a sibling `@scope/q` installed the directory existed, so the reader called the typo a
        package that IS installed and does not load, run npm ci, and the preload rethrew the same; with no node_modules
        the reader filed the typo as the environment (a skip) and the preload stood in for it, so the typo read green in
        the real-tree pins. Now a scoped request with fewer than two non-empty segments is bare in neither file, like
        `./x` and `#x`: node's error stands, with no reader line and no stand-in, plain and under the stand-in, with
        and without node_modules. The control: the two-segment sibling `@scope/q` loads. The empty scope and the
        empty and dot name segments are the round-14 test below."""
        _write(os.path.join(self.ext, "node_modules", "@scope", "q", "index.js"), "module.exports = { q: 1 };\n")
        _write(self.config, 'const q = require("@scope/q");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], q: q.q } };\n')
        self.assertEqual(self.roots(), ["ext"], "the control: the two-segment sibling resolves")
        for with_install in (True, False):
            if not with_install:
                self.no_install()
            for request in ("@scope", "@scope/"):
                _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                    % json.dumps(request))
                for under_stub in (False, True):
                    msg = self.derivation_error(under_stub)
                    self.assertIn("Cannot find module '%s'" % request, msg, (with_install, request, under_stub))
                    self.assertNotIn(" requires '", msg, (with_install, request, under_stub, "no reader line: node's error alone"))
                    self.assertNotIn("IS installed", msg, (with_install, request, under_stub))
                    self.assertNotIn("npm ci", msg, (with_install, request, under_stub))
                    self.assertNotIn("tests/lab_dist_stub.py", msg, (with_install, request, under_stub))

    def test_an_empty_scope_or_an_empty_or_dot_name_segment_names_no_package_never_a_root_an_install_or_the_environment(self):
        """Round 13 read the request's segments twice: the bare test counted the NON-EMPTY ones and packageName sliced
        the raw split, so `@scope//pkg` passed as bare and packageName answered `@scope/`, which path.join made the
        scope directory, answered as the package's root (the reader's "IS installed (.../node_modules/@scope/)" line
        with `@scope/q` installed, the shape the round-13 comments said could not happen); `@/x`, an empty scope npm
        cannot install, passed both tests and was filed as the environment (a skip plain, a stand-in under the
        preload); and a `.` or `..` segment reached path.join, which folded it away, so `pkg/../x` named `pkg` and
        `@scope/./x` named the scope directory as the installed root, and with no node_modules every one was the
        environment. Round 14 read the bare shape and the package's name from ONE split (packageOf) and refused any
        empty, `.` or `..` segment; round 15 narrowed the refusal to the NAME segments, the first, two for a scoped
        request: a request with an empty scope or with a name segment that is empty, `.` or `..` names no package, so
        node's error stands alone, no reader line, no root, no npm ci, no stand-in, plain and under the stand-in, with
        `@scope/q` and setUp's `pkg` installed and with no node_modules. Each shape is a subtest, so a fails-before
        names every red one. The trade the rule makes, stated: node folds a doubled slash or a dot segment away once
        the target exists (`@scope//q` loads with `@scope/q` installed, the control here), so a miss spelled that way
        in the NAME is judged a typo to fix in the requirer rather than a package to install; the same spellings AFTER
        the name (`pkg/`, `pkg/./index`, `pkg/../x`) are the package's subpath, which the rule does not judge, so they
        are judged by the package as `pkg` is (the next test; round 14 refused them too, and a `pkg/` the config
        required where no pkg resolves was node's error, an ERROR from the served modules' call, where `pkg` skips)."""
        _write(os.path.join(self.ext, "node_modules", "@scope", "q", "index.js"), "module.exports = { q: 1 };\n")
        _write(self.config, 'const q = require("@scope//q");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"], q: q.q } };\n')
        self.assertEqual(self.roots(), ["ext"], "the control: node folds the doubled slash and the installed sibling loads")
        for with_install in (True, False):
            if not with_install:
                self.no_install()
            for request in ("@/x", "@scope//pkg", "@scope/./x", "@scope/../x"):
                _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                    % json.dumps(request))
                for under_stub in (False, True):
                    with self.subTest(request=request, with_install=with_install, under_stub=under_stub):
                        msg = self.derivation_error(under_stub)
                        self.assertIn("Cannot find module '%s'" % request, msg)
                        self.assertNotIn(" requires '", msg, "no reader line: node's error alone")
                        self.assertNotIn("IS installed", msg)
                        self.assertNotIn("node_modules/@scope", msg, "the scope directory is named nowhere")
                        self.assertNotIn("npm ci", msg)
                        self.assertNotIn("tests/lab_dist_stub.py", msg)

    def test_a_subpath_spelling_node_resolves_is_judged_by_its_package_never_by_the_subpath(self):
        """Round 14 refused any empty, `.` or `..` segment, the subpath's included, so `pkg/`, `pkg/./index`,
        `pkg/../pkg` and `@scope/q/` named no package and a config requiring one of them where no such package
        resolves was node's error alone: a ValueError from the served modules' call, an ERROR at setUpClass, where the
        same config spelled `pkg` skips as the environment, and no stand-in under the preload where `pkg` is stood in.
        node resolves every one of the four to the installed package (the CJS resolver folds the trailing slash and
        the dot segments once the target exists; an exports map or an ESM import would refuse `pkg/`, and the real
        config's `require("esbuild")` spells none of them), so round 15 judges the NAME segments alone and leaves the
        subpath unjudged: each is the package's request, judged by its root and then its name as `pkg` is. Pinned in
        both install states, plain and under the stand-in: installed, every shape loads (roots `['ext']`) with the
        stand-in inert; with no node_modules, plain is the skip naming the request (and `pkg/` through the served
        modules' own call is that skip too) and under the stand-in the derivation goes through, stood in. The
        subpath stays unjudged the other way too: `pkg/../x`, which node resolves to node_modules/x and does not find,
        is with pkg installed a subpath of a package that IS installed (the reader's line naming pkg's root, plain and
        under the stand-in) and with no node_modules the environment, as any subpath of an absent package is."""
        _write(os.path.join(self.ext, "node_modules", "pkg", "index.js"), "module.exports = { p: 1 };\n")
        _write(os.path.join(self.ext, "node_modules", "@scope", "q", "index.js"), "module.exports = { q: 1 };\n")
        shapes = ("pkg/", "pkg/./index", "pkg/../pkg", "@scope/q/")
        for request in shapes:
            _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                % json.dumps(request))
            for under_stub in (False, True):
                with self.subTest(request=request, with_install=True, under_stub=under_stub):
                    with lab_dist_stub.bare_package_stub() if under_stub else contextlib.nullcontext():
                        self.assertEqual(self.roots(), ["ext"], "node resolves the spelling to the installed package")
        _write(self.config, 'const s = require("pkg/../x");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        root = os.path.join(self.ext, "node_modules", "pkg")
        for under_stub in (False, True):
            with self.subTest(request="pkg/../x", with_install=True, under_stub=under_stub):
                msg = self.derivation_error(under_stub)
                self.assertIn("Cannot find module 'pkg/../x'", msg)
                self.assertIn(self.config + " requires 'pkg/../x', a subpath of a package that IS installed (%s)" % root, msg)
                self.assertNotIn("tests/lab_dist_stub.py", msg)
        self.no_install()
        for request in shapes + ("pkg/../x",):
            _write(self.config, 'const s = require(%s);\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n'
                                % json.dumps(request))
            with self.subTest(request=request, with_install=False, under_stub=False):
                with self.assertRaises(unittest.SkipTest) as cm:
                    self.roots()
                self.assertIn("no package %r" % request, str(cm.exception))
            with self.subTest(request=request, with_install=False, under_stub=True):
                with lab_dist_stub.bare_package_stub():
                    try:
                        roots = self.roots()
                    except unittest.SkipTest as e:
                        self.fail("the stand-in did not cover %r: %r" % (request, e))
                self.assertEqual(roots, ["ext"], "stood in, as `pkg` is")
        _write(self.config, 'const s = require("pkg/");\nmodule.exports = { x: { entryPoints: ["src/extension.ts"] } };\n')
        with self.assertRaises(unittest.SkipTest) as cm:
            self.served_call()
        self.assertIn("no package 'pkg/'", str(cm.exception))

    def test_the_reader_and_the_preload_name_the_same_package_for_every_request_shape(self):
        """packageOf is spelled twice, in the reader's JS (tests/lab_dist.py) and in the preload's (tests/lab_dist_stub.py),
        and a miss the reader files as the environment must be one the preload stands in for, or the real-tree pins
        fail with the block's AssertionError. Both functions are cut from their source text and run under one node over
        the same requests, and their answers are compared with each other and with the rule (round 15): null for a
        relative or absolute request, a hash request, the empty request, and a scoped request with a bare `@` for its
        scope, fewer than two segments, or a name segment that is empty, `.` or `..`; otherwise the first segment, two
        for a scoped request, the subpath after them unjudged and a name's characters unread (a space, a backslash, a
        drive letter on this posix node, a non-ASCII name, an underscore-led name and `node_modules` itself are
        packages here, names npm refuses that the rule does not read). Each request is a subtest."""
        expected = {
            "pkg": "pkg", "pkg/": "pkg", "pkg/./index": "pkg", "pkg/../pkg": "pkg", "pkg/../x": "pkg", "pkg/sub/deep": "pkg",
            "@scope/q": "@scope/q", "@scope/q/": "@scope/q", "@scope/q/sub": "@scope/q", "punycode/": "punycode",
            "@scope": None, "@scope/": None, "@": None, "@/x": None, "@scope//q": None, "@scope/./x": None, "@scope/../x": None,
            "./x": None, "../x": None, ".": None, "/abs": None, "#hash": None, "": None,
            "pkg name": "pkg name", "C:\\x": "C:\\x", "pkg\u00e9": "pkg\u00e9", "_pkg": "_pkg", "node_modules": "node_modules",
        }
        reader = re.search(r"const packageOf = \(r\) => \{\n.*?\n\};", lab_dist._EXPORTS_READER, re.S)
        preload = re.search(r"function packageOf\(r\) \{\n.*?\n\}", lab_dist_stub.PRELOAD, re.S)
        self.assertTrue(reader and preload, "both sources spell packageOf")
        requests = sorted(expected)
        answers = []
        for source in (reader.group(0), preload.group(0)):
            script = ('const path = require("path");\n%s\nconst requests = JSON.parse(process.argv[1]);\n'
                      'process.stdout.write(JSON.stringify(requests.map((r) => packageOf(r))));\n' % source)
            r = subprocess.run(["node", "-e", script, json.dumps(requests)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            answers.append(json.loads(r.stdout))
        for i, request in enumerate(requests):
            with self.subTest(request=request):
                self.assertEqual(answers[0][i], answers[1][i], "the reader and the preload disagree")
                self.assertEqual(answers[0][i], expected[request])

    def test_a_missing_node_is_an_error(self):
        """Without node on PATH nothing is derived: the error names node and the config."""
        with patch.dict(os.environ, {"PATH": self.base}):
            with self.assertRaises(ValueError) as cm:
                lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("node is not on PATH", str(cm.exception))
        self.assertIn(self.config, str(cm.exception))

    def test_a_config_naming_no_path_inside_the_checkout_is_an_error(self):
        _write(self.config, 'const dir = "nowhere", name = "x";\n'
                            'module.exports = { x: { format: "cjs", entryPoints: [`${dir}/${name}.ts`] } };\n')
        with self.assertRaises(ValueError) as cm:
            lab_dist.esbuild_roots(self.root, self.ext)
        self.assertIn("names no path inside the checkout", str(cm.exception))

    def test_the_real_config_derives_the_kernel_trees(self):
        """On this checkout: the exported configs name ui/ and vscode-extension/ (the object-form entry under
        node_modules is a dependency, and so are the absolute nodePaths entry and the CodeMirror aliases), the
        import follow adds vendor/, and the three are the trees the kernel's _bundle_inputs reads (file-level
        parity, the guard against under-approximation inside those trees and nothing else, is pinned in
        tests/test_kernel_bundle_staleness.py, where the kernel is already loaded); the config and package files
        are keyed, the lock file is content-keyed instead, and nothing under the extension's dist, node_modules
        or out-tests is. esbuild.js requires esbuild at its top, a dependency of the build and not of the
        exported data, so the read runs under tests/lab_dist_stub.py's preload, which stands in for a bare
        package the config itself requires and node cannot find where no node_modules exists beside the config,
        and this pin runs on a checkout without the extension's node_modules too
        (CI's Python job; round 6 skipped there, and round 7's stand-in for the one name esbuild would have
        skipped again on the first added dependency). Where a package is installed the real one is read; where
        node_modules exists and lacks a package the config requires, the preload throws and this pin is red. A skip
        inside the block is a failure (the block converts it), so the only skip left is node missing from PATH."""
        with lab_dist_stub.bare_package_stub():
            self.assertEqual([os.path.relpath(p, lab_dist.ROOT) for p in lab_dist.esbuild_roots()], ["ui", "vscode-extension"])
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
    """A build past its bound is a HARD error: BuildTimeout, a RuntimeError, never a SkipTest (a skip would
    report a wedged esbuild as a checkout that cannot build and leave the module green). The two pins
    below catch unittest.SkipTest FIRST and fail on it, so a BuildTimeout re-based on SkipTest, or a
    `raise SkipTest` in the timeout branch, fails here instead of skipping. The bound's VALUE is pinned to
    the kernel's figures in tests/test_kernel_bundle_vendor_inputs.py, where the kernel is loaded."""

    def build_past_the_bound(self, build):
        """Runs `build.ensure_built()` and returns the BuildTimeout it raised; a SkipTest, or no error, fails."""
        self.assertTrue(issubclass(lab_dist.BuildTimeout, RuntimeError), "BuildTimeout is an error, not a skip")
        self.assertFalse(issubclass(lab_dist.BuildTimeout, unittest.SkipTest))
        try:
            build.ensure_built()
        except unittest.SkipTest as e:
            self.fail("a build past its bound is a hard error, never a skip: %r" % e)
        except lab_dist.BuildTimeout as e:
            self.assertIs(type(e), lab_dist.BuildTimeout)
            return e
        self.fail("a build past its bound raised nothing")

    def assert_lock_free(self):
        """The lock went with the error: a non-blocking exclusive flock from a fresh descriptor succeeds."""
        fd = os.open(os.path.join(self.build.dist, lab_dist.LOCK_NAME), os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.fail("the harness lock is still held after the bound cut the build")
        finally:
            os.close(fd)

    def test_a_build_past_its_bound_fails_loudly_and_releases_the_lock(self):
        def wedged(cmd, cwd, timeout):
            raise subprocess.TimeoutExpired(cmd, timeout, output=b"", stderr=b"esbuild: still bundling\n")
        build = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs, timeout=7, run=wedged)
        msg = str(self.build_past_the_bound(build))
        self.assertIn("fake_esbuild.py", msg, "names the command")
        self.assertIn(self.ext, msg, "and where it ran")
        self.assertRegex(msg, r"ran \d+\.\d s, the bound is 7 s", "and the elapsed time against the bound")
        self.assertIn("still bundling", msg, "and the output tail")
        self.assertIsNone(build.read_marker(), "no marker for a build that did not finish")
        self.assertEqual(self.builds(), [])
        self.assert_lock_free()
        result = []                         # and a caller with a working builder proceeds
        t = threading.Thread(target=lambda: result.append(self.build.ensure_built()))
        t.start()
        t.join(30)
        self.assertEqual(result, [True], "the next caller took the lock and built")

    def test_the_default_runner_enforces_the_bound(self):
        """The real path: the subprocess is killed at the bound (the fake would hold for 30 s), BuildTimeout is
        raised, no marker is written, the lock is free, and the next copy builds and is whole. Only what
        the kill makes certain is asserted: whether the killed fake got as far as staging its outputs
        before the bound depends on the machine's load, so the staging leftovers are not asserted here;
        CopyIgnoresForeignStaging plants staging names and pins that the copy leaves them out."""
        os.environ["FAKE_HOLD"] = "30"
        self.addCleanup(os.environ.pop, "FAKE_HOLD", None)
        build = lab_dist.DistBuild(ext=self.ext, cmd=self.build.cmd, inputs=self.build.inputs, timeout=0.5)
        started = time.monotonic()
        e = self.build_past_the_bound(build)
        self.assertLess(time.monotonic() - started, 20, "the bound cut the build, not the fake's own 30 s hold")
        self.assertIsInstance(e.__cause__, subprocess.TimeoutExpired, "raised from the runner's TimeoutExpired")
        self.assertIsNone(build.read_marker())
        self.assert_lock_free()
        os.environ.pop("FAKE_HOLD")
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assert_complete_copy(dest)


class CopyIgnoresForeignStaging(_Checkout):

    # staging names as esbuild.js and the harness's own marker write shape them, at the top and in a subdirectory
    PLANTED = (".pdf-worker.js.tmp-99999-0", os.path.join("fonts", ".b.woff2.tmp-99999-1"),
               ".%s.tmp-99999-0" % lab_dist.MARKER_NAME.lstrip("."))

    def test_a_staging_file_from_outside_the_harness_is_left_out(self):
        self.build.ensure_built()
        for name in self.PLANTED:
            open(os.path.join(self.build.dist, name), "w").close()
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assert_complete_copy(dest)
        self.assertEqual(len(self.builds()), 1, "a staging name is not a foreign write of the served outputs")

    def test_copy_dist_leaves_planted_staging_names_out(self):
        """The served modules' own call, `lab_dist.copy_dist(dest)`, over a dist holding staging names planted
        before the call (a build killed at its bound, or a staged builder outside the lock, leaves exactly
        these): the copy holds the served outputs only, whole, and neither the lock nor the marker."""
        self.build.ensure_built()
        for name in self.PLANTED:
            open(os.path.join(self.build.dist, name), "w").close()
        dest = os.path.join(self.root, "lab", "dist")
        with patch.object(lab_dist, "_DEFAULT", self.build):
            lab_dist.copy_dist(dest)
        self.assert_complete_copy(dest)
        copied = {os.path.relpath(os.path.join(d, f), dest) for d, _, fs in os.walk(dest) for f in fs}
        for name in self.PLANTED + (lab_dist.LOCK_NAME, lab_dist.MARKER_NAME):
            self.assertNotIn(name, copied, "%s was copied into the served tree" % name)
        self.assertEqual(len(self.builds()), 1)

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
# names esbuild.js, or copies a tree that is not the extension's dist, is added here on purpose. Three files upstream
# carries trip the ratchet when the inbound fold brings them, and the plan for each is fixed here and in the ledger
# entry (upstream/2026-09-09-lab-dist-copy-race.md): tests/test_perf_bench.py (romp-on/romp#1057) copies kernel/ into
# a scratch checkout to plant one line in kernel.py, never dist, and is in _TREE_COPIERS already (the fork's copy calls
# no copytree, so the entry is a no-op until the fold, which meets that file as an add/add conflict); tests/dist_copy.py
# (upstream's copy_dist(src, dst), a lock-free copytree ignoring the staging names, whose docstring names esbuild.js)
# and its guard tests/test_dist_copy_staging.py (a copytree over a scratch tree, never dist) are allowlisted by the fold
# slice that brings them, in _ESBUILD_TEXT_READERS and _TREE_COPIERS, with the reason "upstream's copy primitive and
# its guard, called by no fork class, kept side by side so later folds of both merge clean". lab_dist keeps its own
# copy step (shutil.copytree with copy_ignore, which leaves out the lock and the marker as well as the staging names;
# upstream's copy_dist takes no ignore and would copy both into every lab) and does not call the twin; a later offer
# may add an ignore parameter to upstream's copy_dist, after which lab_dist can call it and the twin stops being a twin.
_ESBUILD_TEXT_READERS = {
    # these two drive the harness, which requires the config under node through lab_dist (the reader writes
    # module.exports to a file; require.main is not the module, so nothing builds): the derivation tests and the
    # real-config pin here, the kernel parity pin there, the two real-config reads under the package stand-in
    "test_lab_dist.py", "test_kernel_bundle_staleness.py",
    # test_bundle_build_mode.py, a source pin over esbuild.js's and the kernel's text;
    # test_kernel_bundle_vendor_inputs.py, a kernel pin over a synthetic checkout (a stand-in esbuild.js written
    # there, the argv the kernel passes to a recording fake matched); neither reads the real file past build_mode,
    # neither runs it
    "test_bundle_build_mode.py", "test_kernel_bundle_vendor_inputs.py",
}
_TREE_COPIERS = {"test_lab_dist.py", "test_github_repo.py",             # test_github_repo copies a repo, never dist
                 "test_perf_bench.py"}                                  # upstream's copies kernel/ into a scratch checkout, never dist
_KEY_READERS = {"test_kernel_bundle_staleness.py",                     # imports lab_dist for the input parity pin
                "test_kernel_bundle_vendor_inputs.py"}                 # and for the BUILD_TIMEOUT pin; neither serves


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
        copytree, in any spelling, is an offender unless the allowlists above name it and say why.

        The rule it holds: EVERY served module goes through lab_dist.copy_dist, including a module that
        arrives from upstream through a fold still carrying the old `node esbuild.js` + copytree block.
        Such a module is converted on the merge that brings it and this harness together (whichever of the
        two lands second, in a commit on top of that merge): the fold branch cannot convert it (lab_dist does
        not exist there), and this branch cannot convert a file it does not have. The ratchet turns red until
        that conversion, on the batch that holds both before it reaches main, which is the point: the
        conversion is not optional."""
        offenders = []
        for path in sorted(glob.glob(os.path.join(HERE, "*.py"))):
            name = os.path.basename(path)
            # the harness and its package stand-in are what the ratchet points test modules at: neither is a test
            # module, and neither builds or copies dist (the stand-in's docstring names the config it covers)
            if name in ("lab_dist.py", "lab_dist_stub.py") or os.path.realpath(path) == os.path.realpath(__file__):
                continue
            found = offences(name, _read(path))
            if found:
                offenders.append((name, found))
        self.assertEqual(offenders, [], "build and copy dist through lab_dist.copy_dist; a module that names "
                                        "esbuild.js or copies a tree that is not dist is added to the allowlists "
                                        "in test_lab_dist.py, with its reason")

    def test_the_ratchet_catches_every_shape_of_the_old_block(self):
        """The shapes a copy-paste or a rewrite could take, each flagged: the base shape the served modules
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
        # upstream's test_perf_bench.py (romp-on/romp#1057: a copytree of kernel/ into a scratch checkout) is allowlisted
        # ahead of the fold that brings it, and refused the extension's dist like every tree copier
        self.assertEqual(offences("test_perf_bench.py", 'shutil.copytree(os.path.join(ROOT, "kernel"), os.path.join(scratch, "kernel"), '
                                                        'ignore=shutil.ignore_patterns("__pycache__"))\n'), [])
        self.assertEqual(offences("test_perf_bench.py", "shutil.copytree(os.path.join(EXT, 'dist'), lab)\n"), ["copytree(dist"])

    def test_every_served_module_calls_copy_dist(self):
        served = []
        for p in glob.glob(os.path.join(HERE, "test_*.py")):
            name = os.path.basename(p)
            if os.path.realpath(p) == os.path.realpath(__file__) or name in _KEY_READERS:
                continue
            if "\nimport lab_dist\n" in _read(p):
                served.append(p)
        self.assertGreaterEqual(len(served), 15, "the served labs import the helper")
        for p in served:
            self.assertIn("lab_dist.copy_dist(", _read(p), os.path.basename(p))


if __name__ == "__main__":
    unittest.main()
