"""The served labs' one door to the built bundles (2026-09-09).

Thirteen browser-driven test classes serve the dashboard from a PRIVATE copy of vscode-extension/dist:
run `node esbuild.js`, then copytree(dist, <lab>/dist). Each class used to do both itself, so under
`pytest -n 8` two classes on two workers built the one dist at the same time, and each copied it while
the other's build was still landing. esbuild.js stages every output as a hidden sibling of its served
name (`.<name>.tmp-<pid>-<n>`) and then renames it over that name, so a copy that listed dist during a
peer's staging phase found staging names that were gone by the time it reached them: shutil.Error with
"[Errno 2] No such file or directory: .../dist/.pdf-worker.js.tmp-...", and the class ERRORed at setup
(green alone, red only beside another served class). The cause is ownership, not timing: two builders
of one directory with no shared owner of the build, so no retry or pause would close it.

This module owns the build. The rules:
- ONE build per checkout state. A marker inside dist records the inputs the current bundles were built
  from (a digest of every source's path, mtime and size, over the trees esbuild reads: the same set the
  kernel's `_dist_src_newest` watches, plus the extension host's sources and the package files). A
  caller whose inputs match the marker copies without building; a stale or missing marker means a
  build, and the marker is rewritten, atomically (write a sibling, rename), only AFTER the build exits 0.
  A key computed before the build and recorded after it never claims inputs newer than what the build
  read, so a source edited mid-build is caught by the next call.
- Every build and every copy holds the same file lock (fcntl.flock: xdist workers are separate
  processes, so a threading lock would see one worker at a time). The lock is exclusive for readers
  too: flock's shared-to-exclusive upgrade is not atomic (the lock is dropped and retaken, and a
  waiting builder can slip into that gap), so a reader would have to re-check the marker after
  upgrading, and the copy it protects is short (33 MB, well under the build). One mode, one check.
- The lock file and the marker live INSIDE dist, not in a temp root or a cache dir: dist is the thing
  being protected, so the lock is per-dist by construction (two checkouts never share it, two pytest
  runs on one checkout do, and xdist workers with distinct temp roots do); dist is already gitignored;
  and removing dist removes the marker with it, so a fresh dist is always built. Both are dotfiles
  whose names end in neither .js nor .css, so the kernel's `_dist_ver` token never counts them, and
  the copy's ignore filter leaves them behind.
- Defence in depth: the copy ignores esbuild's staging names (`*.tmp-*`) and the harness's own files.
  The lock is what makes the copy correct against a build THIS harness ran; the ignore covers a build
  it did not (a developer's `npm run build` or a watch mode in the same checkout), which can still
  rename a staging file out from under the listing. A staging name is never a served output, so
  leaving it out of the copy loses nothing. Both exist because they cover different writers.

`copy_dist(dest)` is the served modules' call: lock, build if stale, copy, unlock. `DistBuild` takes an
alternative extension dir, build command and input list so tests/test_lab_dist.py can exercise the
ownership against a synthetic checkout and a fake builder.
"""
import contextlib
import fcntl
import fnmatch
import hashlib
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(ROOT, "vscode-extension")

LOCK_NAME = ".lab-build.lock"
MARKER_NAME = ".lab-built"
# Names that never belong in a served copy: a staging file (esbuild.js writes each output to `.<name>.tmp-<pid>-<n>`
# and renames it over the served name; the marker below is written the same way, so esbuild's stale-staging
# sweep removes an interrupted marker write once its pid is gone) and the harness's own lock and marker.
_STAGING_GLOB = "*.tmp-*"
_HARNESS_OWN = {LOCK_NAME, MARKER_NAME}

# The suffixes esbuild bundles from the input trees: the kernel's `_dist_src_newest` set, plus the data
# and markup files a webview module can import.
_SOURCE_SUFFIXES = (".ts", ".js", ".mjs", ".css", ".json", ".html")
_SKIP_DIRS = {"node_modules", "dist", "out-tests", "__pycache__"}


def default_inputs(root=ROOT, ext=EXT):
    """What the bundles are built from, as (path, recurse) pairs: the ui/ and vendor/ trees the webview
    bundles import (the kernel's staleness scan reads the same two), the extension host's sources, the
    esbuild config and the package files (a dependency change shows up in the lock file)."""
    return [
        (os.path.join(root, "ui"), True),
        (os.path.join(root, "vendor"), True),
        (os.path.join(ext, "src"), True),
        (os.path.join(ext, "esbuild.js"), False),
        (os.path.join(ext, "package.json"), False),
        (os.path.join(ext, "package-lock.json"), False),
        (os.path.join(ext, "tsconfig.json"), False),
    ]


def copy_ignore(_dirpath, names):
    """copytree `ignore`: the staging names of a build in flight and the harness's own files."""
    return {n for n in names if fnmatch.fnmatch(n, _STAGING_GLOB) or n in _HARNESS_OWN}


class DistBuild:
    """The build of one dist directory: `cmd` run in `ext`, keyed on `inputs`, serialized by the lock."""

    def __init__(self, ext=EXT, cmd=("node", "esbuild.js"), inputs=None, root=ROOT):
        self.ext = ext
        self.dist = os.path.join(ext, "dist")
        self.cmd = list(cmd)
        self.inputs = default_inputs(root, ext) if inputs is None else list(inputs)
        self.builds = 0            # builds THIS object ran; the unit test reads it

    # ---- the key ----
    def _input_files(self):
        for path, recurse in self.inputs:
            if not recurse:
                if os.path.isfile(path):
                    yield path
                continue
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
                for name in sorted(filenames):
                    if name.endswith(_SOURCE_SUFFIXES):
                        yield os.path.join(dirpath, name)

    def key(self):
        """A digest of every input's path, mtime (ns) and size. Path-relative to the dist's parent so a
        checkout moved as a whole keeps its marker; a stat sweep of about a thousand files, cheap."""
        h = hashlib.sha256()
        base = os.path.dirname(self.dist)
        for path in self._input_files():
            try:
                st = os.stat(path)
            except OSError:
                continue
            h.update(("%s\t%d\t%d\n" % (os.path.relpath(path, base), st.st_mtime_ns, st.st_size)).encode())
        return h.hexdigest()

    # ---- the marker ----
    def _marker_path(self):
        return os.path.join(self.dist, MARKER_NAME)

    def read_marker(self):
        try:
            with open(self._marker_path()) as f:
                return f.read().strip()
        except OSError:
            return None

    def _write_marker(self, key):
        tmp = os.path.join(self.dist, ".%s.tmp-%d-0" % (MARKER_NAME.lstrip("."), os.getpid()))
        with open(tmp, "w") as f:
            f.write(key + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self._marker_path())

    # ---- the lock ----
    @contextlib.contextmanager
    def locked(self):
        """Exclusive flock on dist/.lab-build.lock. Per open file description, so two threads of one
        process exclude each other exactly as two processes do; closing the descriptor releases it."""
        os.makedirs(self.dist, exist_ok=True)
        fd = os.open(os.path.join(self.dist, LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    # ---- the operations ----
    def _ensure_built_locked(self):
        key = self.key()
        if self.read_marker() == key:
            return False
        r = subprocess.run(self.cmd, cwd=self.ext, capture_output=True, text=True)
        if r.returncode != 0:
            # the served labs' standing behaviour: a checkout that cannot build skips loudly, never fails
            raise unittest.SkipTest("esbuild failed here: " + (r.stderr or r.stdout)[-200:])
        self._write_marker(key)
        self.builds += 1
        return True

    def ensure_built(self):
        """Build unless the marker names the current inputs. True when a build ran."""
        with self.locked():
            return self._ensure_built_locked()

    def copy_to(self, dest):
        """A serve-ready copy of dist at `dest` (which must not exist): build if stale, then copy, both under
        the lock, so the copy sees a complete build and never a build in flight."""
        with self.locked():
            self._ensure_built_locked()
            shutil.copytree(self.dist, dest, ignore=copy_ignore)


DEFAULT = DistBuild()


def copy_dist(dest):
    """The served labs' call: a private, serve-ready copy of the checkout's bundles at `dest`."""
    DEFAULT.copy_to(dest)
