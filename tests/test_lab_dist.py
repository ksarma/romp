#!/usr/bin/env python3
"""tests/lab_dist.py owns the served labs' build of vscode-extension/dist (2026-09-09).

The race it retires: two served-lab classes on two xdist workers each ran `node esbuild.js` into the one
dist and copied it, and a copy that listed dist during the other build's staging phase failed on staging
names (`.pdf-worker.js.tmp-<pid>-<n>`) that were renamed away before it reached them. The properties
pinned here, against a synthetic checkout and a fake builder that stages and renames the way esbuild.js
does (holding the staging window open long enough to matter):
  1. concurrent callers produce ONE build, and every caller's copy is a complete, single-build dist;
  2. a marker that names the current inputs skips the build; a changed input, or a removed dist, rebuilds;
  3. a build that fails skips the caller (the served labs' standing behaviour) and leaves no marker;
  4. the copy leaves out a staging file the harness did not write, and survives a builder running outside
     the lock (the defence-in-depth half);
  5. no served module builds or copies dist on its own any more.
Hermetic: the fake checkout lives under the run's temp root and no real esbuild runs. Synthetic names only.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))

# The fake builder: appends its pid to builds.log, then writes every output to a hidden staging sibling
# (`.<name>.tmp-<pid>-<n>`, esbuild.js's shape), holds that window open for FAKE_HOLD seconds, and renames
# each over its served name. Every output carries the same build id so a copy that mixed two builds shows.
# Exits 1 when a `fail` file sits beside it.
FAKE_BUILDER = r'''
import os, sys, time, random
ext = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(ext, "fail")):
    sys.stderr.write("fake esbuild: refusing to build\n")
    sys.exit(1)
dist = os.path.join(ext, "dist")
os.makedirs(os.path.join(dist, "fonts"), exist_ok=True)
build_id = "%d-%06d" % (os.getpid(), random.randrange(10 ** 6))
with open(os.path.join(ext, "builds.log"), "a") as f:
    f.write(build_id + "\n")
outputs = {"render.js": "// render " + build_id + "\n" + "x" * 4096,
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


class _Checkout(unittest.TestCase):
    """A synthetic checkout: one source tree, one extension dir with the fake builder."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lab-dist-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.src = os.path.join(self.root, "ui")
        os.makedirs(os.path.join(self.src, "webview"))
        self.source = os.path.join(self.src, "webview", "render.ts")
        with open(self.source, "w") as f:
            f.write("export const a = 1;\n")
        self.ext = os.path.join(self.root, "ext")
        os.makedirs(self.ext)
        with open(os.path.join(self.ext, "fake_esbuild.py"), "w") as f:
            f.write(FAKE_BUILDER)
        self.log = os.path.join(self.ext, "builds.log")
        self.build = lab_dist.DistBuild(ext=self.ext, cmd=[sys.executable, "fake_esbuild.py"],
                                        inputs=[(self.src, True)])

    def builds(self):
        try:
            with open(self.log) as f:
                return [l.strip() for l in f if l.strip()]
        except OSError:
            return []

    def assert_complete_copy(self, dest):
        """Every output present, every byte from one build, nothing of the staging or the harness."""
        names = sorted(os.listdir(dest))
        self.assertEqual(names, ["fonts", "render.js", "styles.css"], "a served copy holds the outputs only: %r" % names)
        self.assertEqual(os.listdir(os.path.join(dest, "fonts")), ["a.woff2"])
        ids = set()
        for rel in ("render.js", "styles.css", os.path.join("fonts", "a.woff2")):
            with open(os.path.join(dest, rel)) as f:
                m = _ID.search(f.read())
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
        import threading
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


class MarkerKeysOnInputs(_Checkout):

    def test_matching_marker_skips_and_a_changed_input_rebuilds(self):
        self.assertTrue(self.build.ensure_built(), "an unbuilt dist builds")
        self.assertFalse(self.build.ensure_built(), "unchanged inputs: no second build")
        self.assertEqual(len(self.builds()), 1)
        with open(self.source, "w") as f:
            f.write("export const a = 2;\n")
        st = os.stat(self.source)
        os.utime(self.source, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))   # a second newer, whatever the clock
        self.assertTrue(self.build.ensure_built(), "a changed input is a stale marker: rebuild")
        self.assertFalse(self.build.ensure_built())
        self.assertEqual(len(self.builds()), 2)

    def test_a_new_source_file_is_a_changed_input(self):
        self.build.ensure_built()
        with open(os.path.join(self.src, "webview", "extra.css"), "w") as f:
            f.write("a{}\n")
        self.assertTrue(self.build.ensure_built(), "the key covers the file set, not one newest mtime")

    def test_a_removed_dist_rebuilds(self):
        self.build.ensure_built()
        shutil.rmtree(self.build.dist)
        self.assertTrue(self.build.ensure_built(), "the marker went with dist")
        self.assertEqual(len(self.builds()), 2)

    def test_a_stale_marker_written_by_hand_rebuilds(self):
        self.build.ensure_built()
        with open(os.path.join(self.build.dist, lab_dist.MARKER_NAME), "w") as f:
            f.write("0000\n")
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

    def test_the_real_inputs_resolve(self):
        """The default input list points at trees this checkout has, so the real key digests sources."""
        n = sum(1 for _ in lab_dist.DEFAULT._input_files())
        self.assertGreater(n, 50, "ui/, vendor/ and the extension sources: %d files" % n)
        self.assertTrue(any(p.endswith("esbuild.js") for p in lab_dist.DEFAULT._input_files()))


class CopyIgnoresForeignStaging(_Checkout):

    def test_a_staging_file_from_outside_the_harness_is_left_out(self):
        self.build.ensure_built()
        for name in (".pdf-worker.js.tmp-99999-0", os.path.join("fonts", ".b.woff2.tmp-99999-1")):
            open(os.path.join(self.build.dist, name), "w").close()
        dest = os.path.join(self.root, "lab", "dist")
        self.build.copy_to(dest)
        self.assert_complete_copy(dest)

    def test_copies_survive_a_builder_running_outside_the_lock(self):
        """A developer's build or a watch mode does not take the harness lock. It renames staging files out
        from under a listing, which is exactly what broke the copy before; the ignore filter keeps the copy
        whole, and each served output is read whole (a rename is atomic, so old bytes or new)."""
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
                    with open(os.path.join(dest, rel)) as f:
                        self.assertIsNotNone(_ID.search(f.read()), "%s whole in copy %d" % (rel, i))
                self.assertFalse([n for n in os.listdir(dest) if ".tmp-" in n or n.startswith(".lab-")])
                i += 1
        finally:
            foreign.wait(timeout=60)
        self.assertEqual(foreign.returncode, 0)
        self.assertGreater(i, 5, "copies overlapped the foreign builds: %d copies, %d builds" % (i, len(self.builds())))


class ServedModulesUseTheHelper(unittest.TestCase):

    def test_no_test_module_builds_or_copies_dist_on_its_own(self):
        """The ownership holds only while every served lab goes through the helper. A module that runs
        esbuild itself, or copies the extension's dist itself, is the race coming back."""
        offenders = []
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            if os.path.realpath(path) == os.path.realpath(__file__):     # this scan names the patterns it looks for
                continue
            src = open(path).read()
            if 'subprocess.run(["node", "esbuild.js"]' in src or 'copytree(os.path.join(EXT, "dist")' in src:
                offenders.append(os.path.basename(path))
        self.assertEqual(offenders, [], "build and copy dist through lab_dist.copy_dist")

    def test_every_served_module_calls_copy_dist(self):
        users = [p for p in glob.glob(os.path.join(HERE, "test_*.py")) if "\nimport lab_dist\n" in open(p).read()]
        self.assertGreaterEqual(len(users), 13, "the served labs import the helper")
        for p in users:
            self.assertIn("lab_dist.copy_dist(", open(p).read(), os.path.basename(p))


if __name__ == "__main__":
    unittest.main()
