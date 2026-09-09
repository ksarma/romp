"""The served labs' one door to the built bundles (2026-09-09).

The browser-driven test classes serve the dashboard from a PRIVATE copy of vscode-extension/dist: run
`node esbuild.js`, then copytree(dist, <lab>/dist). Each class used to do both itself, so under
`pytest -n 8` two classes on two workers built the one dist at the same time, and each copied it while
the other's build was still landing. esbuild.js stages every output as a hidden sibling of its served
name (`.<name>.tmp-<pid>-<n>`) and then renames it over that name, so a copy that listed dist during a
peer's staging phase found staging names that were gone by the time it reached them: shutil.Error with
"[Errno 2] No such file or directory: .../dist/.pdf-worker.js.tmp-...", and the class ERRORed at setup
(green alone, red only beside another served class). The cause is ownership, not timing: two builders
of one directory with no shared owner of the build, so no retry or pause would close it.

This module owns the build. The rules:
- ONE build per checkout state. A marker inside dist records two things: the state the current bundles
  were built FROM and the state the build left dist IN. The build state (`key`) digests the build command
  line, every source's path, mtime and size over the trees esbuild reads, and the dependency state (the
  content of npm's two lock files). The output state digests every served file's path, mtime and size
  under dist. A caller whose build state matches the marker, over a dist nobody has written since, copies
  without building; anything else builds: a missing or stale marker, an edited or added source, a
  dependency change, a build by another command (`node esbuild.js --production` by hand, or the kernel's
  in-place rebuild, leaves minified bundles under a marker whose inputs still match; the output state is
  what shows it). The marker is rewritten, atomically (write a sibling, rename), only AFTER the build
  exits 0, and the build state is computed BEFORE the build and recorded after it, so the marker never
  claims inputs newer than what the build read: a source edited mid-build is caught by the next call.
- The trees the build state covers are DERIVED from esbuild.js, not listed here, by a rule that reads no
  array or object out of the config: every quoted string literal in the file that names a file or
  directory on disk inside the checkout contributes the top-level tree that holds it (ui/ and
  vscode-extension/ today; one under node_modules is a dependency, keyed by the lock files; one naming
  nothing on disk contributes nothing), and then, to a fixed point, the top-level tree of every relative
  import a keyed source makes out of the keyed trees (vendor/ today: ui/webview/anchor-map.ts imports
  vendor/track-changents/engine.js). Over-approximation is safe for a staleness key (more files keyed
  means a rebuild more often, never less); under-approximation is guarded by the kernel's
  `_bundle_inputs`, which reads the same trees: tests/test_kernel_bundle_staleness.py pins that every file
  it reads is keyed here. node_modules and out-tests (the test build's output) are pruned at any depth,
  and the dist being built is pruned at the top level only: a source directory named dist at depth is
  keyed like any other.
- Every build and every copy holds the same file lock (fcntl.flock: xdist workers are separate
  processes, so a threading lock would see one worker at a time). The lock is exclusive for readers
  too: flock's shared-to-exclusive upgrade is not atomic (the lock is dropped and retaken, and a
  waiting builder can slip into that gap), so a reader would have to re-check the marker after
  upgrading, and the copy it protects is short (33 MB, well under the build). One mode, one check.
- The build is bounded: BUILD_TIMEOUT seconds, the kernel's own bound for the same command (180 s in
  `_rebuild_dist`; `_ensure_bundles` uses 120 s). A build that does not finish raises BuildTimeout
  naming the command and the elapsed time, and the lock goes with it, so a wedged esbuild in one worker
  cannot hold every served class in flock with nothing said. Each waiter that then takes the lock finds
  the marker stale and tries the build itself, so a wedge that persists costs each served class its own
  bound, in sequence; a failure recorded in the marker would remove those retries but would also outlive
  a transient wedge until some input changed, so none is recorded.
- The lock file and the marker live INSIDE dist, not in a temp root or a cache dir: dist is the thing
  being protected, so the lock is per-dist by construction (two checkouts never share it, two pytest
  runs on one checkout do, and xdist workers with distinct temp roots do), and removing dist removes
  the marker with it, so a fresh dist is always built (a marker beside dist would survive `rm -rf dist`,
  match the key, and let copy_to copy an empty dist). Three readers of dist must leave both alone: git
  ignores dist/ whole; vsce packages dist and is governed by .vscodeignore, not .gitignore, so
  vscode-extension/.vscodeignore names both files (tests/test_lab_dist.py pins both rules); and the
  kernel's `_dist_ver` token globs bundle suffixes (`*.js` in its code; its docstring names `*.css` too),
  and neither harness name, nor the marker's staging name, ends in either
  (tests/test_kernel_bundle_staleness.py runs the token over a dist holding all three and pins that it
  does not move). The copy's ignore filter leaves both behind.
- Defence in depth: the copy ignores esbuild's staging names (`*.tmp-*`) and the harness's own files.
  The lock is what makes a copy correct against a build THIS harness ran. The ignore covers a STAGED
  build that did not take the lock (`node esbuild.js`, with or without --production, `npm run build`,
  the kernel's in-place rebuild: all through esbuild.js's buildAll), which can still rename a staging
  file out from under the listing; a staging name is never a served output, so leaving it out loses
  nothing, and the output state then shows the foreign build to the next caller, which redoes it. Watch
  mode (`npm run watch`, `node esbuild.js --watch`) is outside this contract: it writes each output in
  place, truncating the served file first, with no staging name and no lock, so neither the ignore nor
  the lock protects a copy from it. Do not run the served labs beside a watch loop in the same checkout.

`copy_dist(dest)` is the served modules' call: lock, build if stale, copy, unlock. `DistBuild` takes an
alternative extension dir, build command, input list, bound and build runner so tests/test_lab_dist.py
can exercise the ownership against a synthetic checkout and a fake builder.
"""
import contextlib
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
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

# The bound on one build, in seconds: the kernel's for the same command (kernel/kernel.py: `_rebuild_dist` runs
# `node esbuild.js` under timeout=180, `_ensure_bundles` under 120, both its first call and its retry after
# `npm install`), the larger of the two figures. A real build takes about a second, so only a wedge reaches it.
# tests/test_kernel_bundle_vendor_inputs.py pins it to the kernel's figures by RUNNING all three of the kernel's
# esbuild calls over a recording fake (the retry by making the first build fail), never by reading the kernel's
# text.
BUILD_TIMEOUT = 180

# The suffixes esbuild bundles from the input trees: the kernel's `_bundle_inputs` set (.ts, .js, .mjs, .css)
# plus the data and markup files a webview module can import.
_SOURCE_SUFFIXES = (".ts", ".js", ".mjs", ".css", ".json", ".html")
# Pruned at any depth: node_modules is the dependency state (keyed by the lock files below), out-tests is the
# test build's output. The dist being built is pruned by PATH in _sources, at the top level only, so a source
# directory named dist at depth (a vendored package's own dist/) is keyed like any other.
_SKIP_DIRS = {"node_modules", "out-tests", "__pycache__"}
# The suffixes whose imports esbuild follows, and the two halves of a relative specifier in them: the string
# literal (matched first: a literal-anchored scan is ten times cheaper over these trees than a shape-first
# one) and the import shape in the bytes before it (ES `from`, a bare `import`, `require(`, CSS `@import`).
_IMPORTING_SUFFIXES = (".ts", ".js", ".mjs", ".css")
_RELATIVE_LITERAL = re.compile(r"""["'](\.\.?/[^"'\n]*)["']""")
_IMPORT_SHAPE = re.compile(r"""(?:\bfrom|\bimport|\brequire\s*\(|@import(?:\s+url\()?)\s*\(?\s*$""")
# A single- or double-quoted string literal in esbuild.js, escapes kept whole, on one line (a JS string cannot
# span lines). Template literals are not read: one that named a path would be computed, and none does today.
_STRING_LITERAL = re.compile(r'"((?:[^"\\\n]|\\.)*)"' r"|'((?:[^'\\\n]|\\.)*)'")
# The dependency state, relative to the extension dir. package-lock.json moves at checkout time (a merge, a
# pull); node_modules/.package-lock.json is npm's hidden lockfile, rewritten by every `npm install` and `npm
# ci`, and it is the one that moves when the installed tree changes AFTER the checkout did (the pull moves the
# first, the install that follows moves the second). Here node_modules is one tree shared across worktrees by
# symlink, so an install under any worktree changes every worktree's dependencies. Both are keyed by CONTENT,
# never by stat: a no-op `npm install` rewrites the same bytes under a new mtime, and that is not a change.
_DEPENDENCY_FILES = ("package-lock.json", os.path.join("node_modules", ".package-lock.json"))


class BuildTimeout(RuntimeError):
    """The build did not finish inside its bound. Raised after the lock is released, naming the command,
    the directory, the elapsed time and the bound."""


def _under(path, directory):
    """Is `path` `directory` or inside it (textually: no symlinks resolved)?"""
    rel = os.path.relpath(path, directory)
    return rel != os.pardir and not rel.startswith(os.pardir + os.sep)


def _top_tree(path, root):
    """The top-level entry of `root` that holds `path` (root/ui for root/ui/webview/x.ts, root/x.js for a
    file at the top), or None when `path` is `root` itself or outside it."""
    if path == root or not _under(path, root):
        return None
    return os.path.join(root, os.path.relpath(path, root).split(os.sep)[0])


def _sources(tree, skip=()):
    """Every source-suffixed file under `tree`, in a stable order. `skip` holds directory paths to prune (the
    dist being built); _SKIP_DIRS and hidden directories are pruned at any depth."""
    for dirpath, dirnames, filenames in os.walk(tree):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _SKIP_DIRS and not d.startswith(".") and os.path.join(dirpath, d) not in skip)
        for name in sorted(filenames):
            if name.endswith(_SOURCE_SUFFIXES):
                yield os.path.join(dirpath, name)


def esbuild_roots(root=ROOT, ext=EXT):
    """The top-level trees of the checkout `root` that esbuild.js names, as absolute paths, sorted.

    The rule is deliberately conservative and reads no array or object out of the config: EVERY single- or
    double-quoted string literal in the file, comments included, is joined to the extension dir and
    normalized, and one that names a file or directory on disk inside the checkout contributes the
    top-level tree that holds it ("src/extension.ts" and "dist" contribute vscode-extension,
    "../ui/webview/render.ts" contributes ui). Everything else contributes nothing: a literal naming nothing
    on disk (a format, a target, a loader key, a URL, a glob, a message, a path in a comment that no longer
    exists), an empty or absolute literal, one under node_modules (a dependency, keyed by the lock files),
    and one that resolves to the checkout root itself (a top-level tree is the unit this key walks).

    Over-approximation is SAFE for a staleness key: a tree named only in a comment is keyed too, and more
    files keyed means a rebuild more often, never less. Under-approximation is the failure this module
    exists to prevent, and the parity test in tests/test_kernel_bundle_staleness.py is the guard against
    it: on the real tree, every file the kernel's `_bundle_inputs` reads must be keyed here. The one shape
    neither sees is an input named by no literal at all (a computed path); none exists today.

    Loud in two cases: a literal that names an existing path OUTSIDE the checkout, which no top-level tree
    can key and the parity test cannot see either; and a config naming no path inside the checkout at all,
    which means the wrong file was read."""
    config = os.path.join(ext, "esbuild.js")
    with open(config, encoding="utf-8") as f:
        src = f.read()
    node_modules = os.path.join(ext, "node_modules")
    roots = set()
    for m in _STRING_LITERAL.finditer(src):
        literal = m.group(1) if m.group(1) is not None else m.group(2)
        if not literal or os.path.isabs(literal):
            continue
        path = os.path.normpath(os.path.join(ext, literal))
        if path == root or _under(path, node_modules) or not os.path.exists(path):
            continue
        top = _top_tree(path, root)
        if top is None:
            raise ValueError("%s names %r, an existing path outside the checkout %s, which cannot be keyed"
                             % (config, literal, root))
        roots.add(top)
    if not roots:
        raise ValueError("%s names no path inside the checkout %s: the build's inputs cannot be keyed" % (config, root))
    return sorted(roots)


def _relative_imports(path):
    """The relative specifiers (./x, ../y) one source imports."""
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    for m in _RELATIVE_LITERAL.finditer(text):
        if _IMPORT_SHAPE.search(text, max(0, m.start() - 40), m.start()):
            yield m.group(1)


def default_inputs(root=ROOT, ext=EXT):
    """What the bundles are built from, as (path, recurse) pairs derived from esbuild.js: the top-level tree
    of every path the config names (esbuild_roots), then, to a fixed point, the top-level tree of every
    relative import a keyed source makes out of the keyed trees (esbuild bundles what the entries import).
    Today that is ui/ and vscode-extension/ from the config and vendor/ from ui/webview/anchor-map.ts's
    import of vendor/track-changents/engine.js. A top-level FILE (root/x.js) is keyed as one file, not
    walked."""
    dist = os.path.join(ext, "dist")
    inputs = {top: os.path.isdir(top) for top in esbuild_roots(root, ext)}
    pending = [p for p, recurse in inputs.items() if recurse]
    while pending:
        tree = pending.pop()
        for path in _sources(tree, skip=(dist,)):
            if not path.endswith(_IMPORTING_SUFFIXES):
                continue
            for spec in _relative_imports(path):
                top = _top_tree(os.path.normpath(os.path.join(os.path.dirname(path), spec)), root)
                if top is None or top in inputs or not os.path.exists(top):
                    continue
                inputs[top] = os.path.isdir(top)
                if inputs[top]:
                    pending.append(top)
    return sorted(inputs.items())


def copy_ignore(_dirpath, names):
    """copytree `ignore`: the staging names of a build in flight and the harness's own files."""
    return {n for n in names if fnmatch.fnmatch(n, _STAGING_GLOB) or n in _HARNESS_OWN}


def _text(b):
    """A subprocess stream as text: TimeoutExpired carries bytes even under text=True."""
    if b is None:
        return ""
    return b.decode(errors="replace") if isinstance(b, bytes) else b


class DistBuild:
    """The build of one dist directory: `cmd` run in `ext` by `run` within `timeout` seconds, keyed on `inputs`,
    serialized by the lock. `run(cmd, cwd, timeout)` returns a CompletedProcess or raises TimeoutExpired; the
    default runs the command as a subprocess, and the tests inject one."""

    def __init__(self, ext=EXT, cmd=("node", "esbuild.js"), inputs=None, root=ROOT, timeout=BUILD_TIMEOUT, run=None):
        self.ext = ext
        self.dist = os.path.join(ext, "dist")
        self.cmd = list(cmd)
        self.inputs = default_inputs(root, ext) if inputs is None else list(inputs)
        self.timeout = timeout
        self.run = run or self._run
        self.builds = 0            # builds THIS object ran; the unit test reads it

    @staticmethod
    def _run(cmd, cwd, timeout):
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)

    # ---- the build state ----
    def _dependency_paths(self):
        return [os.path.join(self.ext, rel) for rel in _DEPENDENCY_FILES]

    def _input_files(self):
        """Every stat-keyed source: the recursive inputs walked (the dist being built pruned at the top), the
        listed files that exist, the content-keyed dependency files left out."""
        deps = set(self._dependency_paths())
        for path, recurse in self.inputs:
            if not recurse:
                if os.path.isfile(path) and path not in deps:
                    yield path
                continue
            for p in _sources(path, skip=(self.dist,)):
                if p not in deps:
                    yield p

    def key(self):
        """A digest of the build command line, of every input's path, mtime (ns) and size, and of the content
        of the dependency lock files. Paths relative to the extension dir so a checkout moved as a whole keeps
        its marker; a stat sweep of about a thousand files and two small files read, cheap."""
        h = hashlib.sha256()
        h.update(("cmd\t%s\n" % json.dumps(self.cmd)).encode())
        for path in self._input_files():
            try:
                st = os.stat(path)
            except OSError:
                continue
            h.update(("src\t%s\t%d\t%d\n" % (os.path.relpath(path, self.ext), st.st_mtime_ns, st.st_size)).encode())
        for path in self._dependency_paths():
            try:
                with open(path, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                digest = "absent"
            h.update(("dep\t%s\t%s\n" % (os.path.relpath(path, self.ext), digest)).encode())
        return h.hexdigest()

    def output_state(self):
        """A digest of every served file's path, mtime (ns) and size under dist, staging names and the harness's
        own files left out: the state a build leaves dist in, so a write by anyone else (another command's
        build, a build of another mode) shows as a mismatch on the next check."""
        h = hashlib.sha256()
        for dirpath, dirnames, filenames in os.walk(self.dist):
            dirnames.sort()
            for name in sorted(filenames):
                if name in _HARNESS_OWN or fnmatch.fnmatch(name, _STAGING_GLOB):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                h.update(("%s\t%d\t%d\n" % (os.path.relpath(path, self.dist), st.st_mtime_ns, st.st_size)).encode())
        return h.hexdigest()

    # ---- the marker ----
    def _marker_path(self):
        return os.path.join(self.dist, MARKER_NAME)

    def _read_marker(self):
        """(build key, output state) as the marker names them, or None without a marker."""
        try:
            with open(self._marker_path()) as f:
                lines = [l.strip() for l in f]
        except OSError:
            return None
        return (lines[0] if lines else "", lines[1] if len(lines) > 1 else "")

    def read_marker(self):
        """The build key the marker names, or None."""
        m = self._read_marker()
        return m[0] if m else None

    def is_current(self, key=None):
        """Does the marker name `key` (the build state, computed here when not given) AND dist as it stands?"""
        m = self._read_marker()
        return m is not None and m[0] == (self.key() if key is None else key) and m[1] == self.output_state()

    def _write_marker(self, key, outputs):
        tmp = os.path.join(self.dist, ".%s.tmp-%d-0" % (MARKER_NAME.lstrip("."), os.getpid()))
        with open(tmp, "w") as f:
            f.write(key + "\n" + outputs + "\n")
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
        key = self.key()                        # BEFORE the build: the state the build is about to read
        if self.is_current(key):
            return False
        started = time.monotonic()
        try:
            r = self.run(self.cmd, self.ext, self.timeout)
        except subprocess.TimeoutExpired as e:
            raise BuildTimeout("esbuild did not finish: `%s` in %s ran %.1f s, the bound is %g s (BUILD_TIMEOUT, the "
                               "kernel's own bound for this command); output tail: %s"
                               % (shlex.join(self.cmd), self.ext, time.monotonic() - started, self.timeout,
                                  (_text(e.stderr) or _text(e.stdout))[-300:].strip())) from e
        if r.returncode != 0:
            # the served labs' standing behaviour: a checkout that cannot build skips loudly, never fails
            raise unittest.SkipTest("esbuild failed here: " + (r.stderr or r.stdout)[-200:])
        self._write_marker(key, self.output_state())
        self.builds += 1
        return True

    def ensure_built(self):
        """Build unless the marker names the current inputs over an unwritten dist. True when a build ran."""
        with self.locked():
            return self._ensure_built_locked()

    def copy_to(self, dest):
        """A serve-ready copy of dist at `dest` (which must not exist): build if stale, then copy, both under
        the lock, so the copy sees a complete build and never a build in flight."""
        with self.locked():
            self._ensure_built_locked()
            shutil.copytree(self.dist, dest, ignore=copy_ignore)


_DEFAULT = None


def default():
    """The checkout's own DistBuild, made on first use: deriving its inputs reads esbuild.js and scans the
    keyed trees for imports (about a tenth of a second), which every process that imports this module need
    not pay (tests/__init__.py imports it to register the name)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = DistBuild()
    return _DEFAULT


def copy_dist(dest):
    """The served labs' call: a private, serve-ready copy of the checkout's bundles at `dest`."""
    default().copy_to(dest)
