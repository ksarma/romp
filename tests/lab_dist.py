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
  dependency change, a build by another command under a marker whose inputs still match (a `node esbuild.js
  --production` by hand, or the kernel's boot build in `_ensure_bundles`, which minifies unless
  ROMP_EXT_DEV_BUILD is set, leaves minified bundles; the kernel's in-place `_rebuild_dist` runs the same
  command line as this harness and leaves dev bundles under new mtimes; the output state is what shows
  either). The marker is rewritten, atomically (write a sibling, rename), only AFTER the build
  exits 0, and the build state is computed BEFORE the build and recorded after it, so the marker never
  claims inputs newer than what the build read: a source edited mid-build is caught by the next call.
- The trees the build state covers are DERIVED from esbuild.js, not listed here, and read from what the
  config EXPORTS, never from its text (review round 6, the repo's authoritative-source rule). esbuild.js
  exports its configs for the extension's own tests (`module.exports = { extension, webview, testBuild,
  ... }`) and builds only under `require.main === module`, so node can require the module and write
  module.exports as JSON without building (esbuild_exports). The JSON goes to a file whose path node gets
  as an argument, never to stdout, so a config that logs at require time cannot corrupt the read; both
  streams are captured and attached to every error instead. Every string value in the exported objects,
  at any depth (the values of an object, never its keys), is resolved against the extension dir, relative
  or absolute (`path.join(__dirname, ...)`, the idiom the real config uses), and one that names a file or
  directory on disk inside the checkout contributes the top-level tree that holds it (ui/ and
  vscode-extension/ today; a directory contributes its whole tree). One under the extension's
  node_modules is a dependency, keyed by the lock files below and pruned from every walk by _SKIP_DIRS;
  one naming nothing on disk (a format, a glob) contributes nothing; an absolute one outside the checkout
  is noise too (`/` as a publicPath, a system path, a path node resolved to its realpath on a checkout
  reached through a symlink: none is a source here); a RELATIVE one that reaches outside the checkout is
  loud, because the config then points out of the repo at something no tree here can key. The config's
  own tree (esbuild.js, package.json, tsconfig.json) is keyed unconditionally: those are inputs of the
  build whether or not an exported value happens to resolve inside it. Then, to a fixed point, the
  top-level tree of every relative import a keyed source makes out of the keyed trees (vendor/ today:
  ui/webview/anchor-map.ts imports vendor/track-changents/engine.js). Five rounds of text scans (quoted
  literals, then path tokens, then their union) each missed a quoting corner the next review found; the
  export has no quoting to get wrong, and a value built at require time is plain data. Its one limit: a
  path that stands only in code (a plugin's body) is not exported data and is not keyed (a comment is
  never a build input, so a path in one is harmless). The kernel's hand-maintained `_bundle_inputs` list
  names vscode-extension/src, ui/webview, ui/romp-timeline-view.js and vendor/, and
  tests/test_kernel_bundle_staleness.py pins that every file that list reads is keyed here; that catches
  drift inside the trees the kernel's list names and nothing else: a tree reached only through code in
  esbuild.js (tools/, docs/) is keyed by nothing and pinned by no test until someone adds it to the
  kernel's list by hand (none today: esbuild.js has no plugins). Over-approximation is safe for a
  staleness key (more files keyed means a rebuild more often, never less). The read needs node on PATH;
  without it, when the module does not load, when it exports nothing, or when the require does not
  finish inside _EXPORTS_TIMEOUT, esbuild_exports raises with node's stderr and stdout, and nothing falls
  back to the text: a silent fallback would hide the breakage it papers over. One failure is a skip, not
  an error (review round 7): a bare package the config requires that node cannot find (`require("esbuild")`
  on a checkout without the extension's node_modules) is the environment, the precondition the build half
  already skips on, so the served labs skip with the reason. The two real-tree pins run there all the
  same, through a node preload that stands in for every bare package node cannot resolve
  (tests/lab_dist_stub.py; the stand-in throws on any read at require time): the require is a dependency
  of the build, not of the exported data. node_modules and out-tests (the test build's output)
  are pruned at any depth, and the dist being built is pruned at the top level only: a source directory
  named dist at depth is keyed like any other.
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
import tempfile
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
# The reader of esbuild.js's exports, run as `node -e <reader> <config> <out>` from the extension dir: it requires
# the module and writes module.exports as JSON to the file <out>, never to stdout, so a config that logs at require
# time cannot corrupt the read (both streams are captured and attached to every error instead). The module builds
# only under `require.main === module` (the guard at the end of esbuild.js), which is false under -e, so the require
# builds nothing. Functions are not JSON and drop out of the print, which is the point: no exported function is
# called (buildAll would build; testBuild's entries are the test files beside the sources, in trees the two configs
# name). A module.exports that is not an object (a bare function) drops out whole, and esbuild_exports reads that as
# null, the exports-nothing error in esbuild_roots. One require error is classified here, so esbuild_exports can
# tell the environment from the config (review round 7, decision 2): a MODULE_NOT_FOUND for a BARE package name
# (`esbuild`, `@scope/pkg`; not `./x`, not an absolute path) is the shape of a checkout without the extension's
# node_modules, the precondition the build half skips on, so the reader records the package name in the file and
# exits 0; every other error (a syntax error, a throw at load, a missing relative module) propagates and exits 1
# with node's diagnosis on stderr.
_EXPORTS_READER = """
const fs = require("fs"), path = require("path");
const [config, out] = process.argv.slice(1);
let m;
try {
  m = require(config);
} catch (e) {
  const hit = e && e.code === "MODULE_NOT_FOUND" && /^Cannot find module '([^']+)'/.exec(String(e.message));
  if (hit && !hit[1].startsWith(".") && !path.isAbsolute(hit[1])) {
    fs.writeFileSync(out, JSON.stringify({ missing: hit[1] }));
    process.exit(0);
  }
  throw e;
}
fs.writeFileSync(out, JSON.stringify({ exports: m }));
"""
# The bound on the require, in seconds: the kernel's bound for running this same file (BUILD_TIMEOUT above; a require
# runs the file's top level, a prefix of what the build runs, so the build's bound holds it too). The two move
# together, and tests/test_kernel_bundle_vendor_inputs.py pins both to the kernel's figures at once. A config module
# loads in well under a second, so only a wedge reaches it.
_EXPORTS_TIMEOUT = BUILD_TIMEOUT
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


def _exported_strings(value):
    """Every string value in a JSON-shaped export, at any depth: a string itself, the items of an array, the
    values of an object (never its keys, which are option names: a loader suffix, an alias, a define name)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _exported_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _exported_strings(item)


def esbuild_exports(ext=EXT):
    """module.exports of `ext`/esbuild.js as node sees it, decoded from JSON, as (config path, exports); exports is
    None when module.exports is not JSON (a bare function). `ext` is made absolute first: node runs with `ext` as
    its cwd and would resolve a relative config path against that, one level too deep. Loud, never falling back to
    the file's text, in five cases, each error carrying node's stderr tail and stdout head: `ext` is not a
    directory (node has nowhere to run; checked before the call, so a FileNotFoundError from the call itself can
    only be node); node is not on PATH; the module does not load (a syntax error, a throw at load, a missing
    RELATIVE module) or the reader finds no file to read (the module ended the process before module.exports was
    written); and the require does not finish inside _EXPORTS_TIMEOUT. One require failure is a skip instead
    (review round 7, decision 2): a MODULE_NOT_FOUND for a bare package name (`require("esbuild")` on a checkout
    without the extension's node_modules) is the environment, not the config, and the precondition the build half
    skips on, so it raises unittest.SkipTest naming the package and the config, as the build half does when the
    build fails. The reader tells the two apart by the require error's code and request (a bare name against
    `./x` or an absolute path), never by reading the config's text."""
    ext = os.path.abspath(ext)
    config = os.path.join(ext, "esbuild.js")
    if not os.path.isdir(ext):
        raise ValueError("%s cannot be read: %s is not a directory, so node has nowhere to run (the build's inputs are "
                         "derived from the config's exports, never from its text)" % (config, ext))
    out_dir = tempfile.mkdtemp(prefix="lab-dist-exports-")
    out = os.path.join(out_dir, "exports.json")
    try:
        try:
            r = subprocess.run(["node", "-e", _EXPORTS_READER, config, out], cwd=ext, capture_output=True, text=True,
                               timeout=_EXPORTS_TIMEOUT)
        except FileNotFoundError as e:      # the cwd exists (checked above), so the file not found is node itself
            raise ValueError("%s cannot be read: node is not on PATH (%s); the build's inputs are derived from the "
                             "config's exports, never from its text" % (config, e)) from e
        except subprocess.TimeoutExpired as e:
            raise ValueError("%s did not finish loading under node in %g s (_EXPORTS_TIMEOUT); %s"
                             % (config, _EXPORTS_TIMEOUT, _node_output(e.stdout, e.stderr))) from e
        if r.returncode != 0:
            raise ValueError("%s did not load under node (exit %d), so the build's inputs cannot be keyed (nothing "
                             "falls back to the file's text); %s" % (config, r.returncode, _node_output(r.stdout, r.stderr, 2000)))
        try:
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise ValueError("%s: the exports reader wrote no JSON to its file (the module ended the process before "
                             "module.exports was written); %s" % (config, _node_output(r.stdout, r.stderr))) from e
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
    if "missing" in data:
        raise unittest.SkipTest("%s cannot load here: node found no package %r to require (the extension's node_modules "
                                "are absent or incomplete: npm ci not run), the same precondition a failed build skips "
                                "on; %s" % (config, data["missing"], _node_output(r.stdout, r.stderr)))
    return config, data.get("exports")


def esbuild_roots(root=ROOT, ext=EXT):
    """The top-level trees of the checkout `root` that esbuild.js's exported configs name, as absolute paths,
    sorted.

    The source is the config's EXPORT, not its text. esbuild.js exports its configs for the extension's own
    tests (`module.exports = { buildAll, failureSummary, extension, webview, testBuild, oneCodeMirror }`) and
    runs its build only under `require.main === module`, the guard at the end of the file, so a `node -e`
    script that requires the module and writes module.exports as JSON to a file (_EXPORTS_READER, run from
    the extension dir) reads the objects the build reads and builds nothing. Functions are not JSON and drop
    out; none is called (buildAll would build; testBuild's entries are the test files beside the sources, in
    trees the two configs name). The exported objects are walked recursively (_exported_strings: the values
    of an object, never its keys; the items of an array; a string itself), and every string value is joined
    to the extension dir and normalized; an absolute value comes through the join unchanged, so the
    `path.join(__dirname, ...)` idiom resolves like a relative one. One that names a file or directory on
    disk inside the checkout contributes the top-level tree that holds it ("src/extension.ts" and "dist"
    contribute vscode-extension, "../ui/webview/render.ts" contributes ui, and a directory value, an
    outbase, an absWorkingDir, a nodePaths entry or a tsconfig dir, contributes the tree that holds it).
    Everything else contributes nothing: a value naming nothing on disk (a format, a target, a loader, a
    glob, a define value, an empty string); one under the extension's node_modules (the real config's
    nodePaths entry and its CodeMirror aliases, all absolute: a dependency, keyed by the lock files, its
    files pruned from every walk by _SKIP_DIRS); one that resolves to the checkout root itself (a top-level
    tree is the unit this key walks); and an ABSOLUTE one outside the checkout (`/` as a publicPath, a
    system path, a path node resolved to its realpath on a checkout reached through a symlink: none is a
    source of this checkout, and a raise on `/` would make every served lab error on a legitimate config).
    A RELATIVE value that resolves to an existing path outside the checkout is the suspicious shape and is
    loud: the config reaches out of the repo to something no top-level tree here can key.

    Reading the export replaced five rounds of text scans (round 6): a quoted-literal scan, then a path-token
    scan, then their union, each missed a quoting corner the next review found (a stray quote before a path,
    a path with a space, an escaped quote, a backtick pairing across lines), and a value built at require
    time (`${dir}/x.ts`) was beyond all of them; through the export those are plain data. The one limit of
    the export: a path that stands only in code (a plugin's body) is not exported data and is not keyed (a
    comment is never a build input, so a path in one is harmless). The parity pin in
    tests/test_kernel_bundle_staleness.py checks on the real tree that every file the kernel's
    hand-maintained `_bundle_inputs` list reads is keyed here, which catches drift inside the trees that list
    names (vscode-extension/src, ui/webview, ui/romp-timeline-view.js, vendor/) and nothing else: a tree
    reached only through code in esbuild.js (tools/, docs/) is keyed by nothing and pinned by no test until
    someone adds it to the kernel's list by hand (none today: esbuild.js has no plugins). Over-approximation
    is SAFE for a staleness key (more files keyed means a rebuild more often, never less);
    under-approximation is the failure this module exists to prevent.

    Loud, with no fallback to the file's text, in eight cases. Five are esbuild_exports's, each carrying
    node's stderr tail and stdout head: the extension dir is not a directory; node is not on PATH; the
    module does not load (a syntax error, a throw at load, a missing relative module); the module ends the
    process before the reader writes its file; the require does not finish inside _EXPORTS_TIMEOUT. Three
    are here: module.exports holds no string value (nothing exported, or only functions); a relative value
    names an existing path OUTSIDE the checkout, which no top-level tree can key and the parity pin cannot
    see; a config names no path inside the checkout at all, which means the wrong file was read. One
    failure is a skip instead (esbuild_exports raises unittest.SkipTest, as the build half does on a failed
    build): a bare package the config requires that node cannot find, the environment's state and the
    precondition every served lab skips on (review round 7, decision 2)."""
    root, ext = os.path.abspath(root), os.path.abspath(ext)
    config, exports = esbuild_exports(ext)
    candidates = set(_exported_strings(exports))
    if not candidates:
        raise ValueError("%s exports no string value (module.exports prints as %s): the build's inputs are derived "
                         "from the config's exports, never from its text, so they cannot be keyed"
                         % (config, json.dumps(exports)[:200]))
    node_modules = os.path.join(ext, "node_modules")
    roots = set()
    for candidate in sorted(candidates):
        if not candidate:
            continue
        path = os.path.normpath(os.path.join(ext, candidate))      # an absolute candidate comes through unchanged
        if path == root or _under(path, node_modules) or not os.path.exists(path):
            continue
        top = _top_tree(path, root)
        if top is None:
            if os.path.isabs(candidate):
                continue
            raise ValueError("%s exports %r, an existing path outside the checkout %s, which cannot be keyed"
                             % (config, candidate, root))
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
    of every path the config names (esbuild_roots), the config's own tree (esbuild.js, package.json and
    tsconfig.json are inputs of the build whether or not an exported value resolves inside it, so it is
    seeded here, after esbuild_roots has had its say: a config naming no path inside the checkout is still
    the wrong file), then, to a fixed point, the top-level tree of every relative import a keyed source
    makes out of the keyed trees (esbuild bundles what the entries import). Today that is ui/ and
    vscode-extension/ from the config and vendor/ from ui/webview/anchor-map.ts's import of
    vendor/track-changents/engine.js. A top-level FILE (root/x.js) is keyed as one file, not walked."""
    root, ext = os.path.abspath(root), os.path.abspath(ext)
    dist = os.path.join(ext, "dist")
    inputs = {top: os.path.isdir(top) for top in esbuild_roots(root, ext)}
    own = _top_tree(os.path.join(ext, "esbuild.js"), root)
    if own is None:
        raise ValueError("%s is not inside the checkout %s, so the config's own tree cannot be keyed" % (ext, root))
    inputs.setdefault(own, os.path.isdir(own))
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


def _node_output(stdout, stderr, tail=500):
    """Both streams of a node run, for an error or skip message: the stderr tail (node's diagnosis ends there)
    and the stdout head (what a config printed at require time; the reader itself prints nothing)."""
    return "stderr tail: %s; stdout head: %s" % (_text(stderr)[-tail:].strip(), _text(stdout)[:200].strip())


class DistBuild:
    """The build of one dist directory: `cmd` run in `ext` by `run` within `timeout` seconds, keyed on `inputs`,
    serialized by the lock. `run(cmd, cwd, timeout)` returns a CompletedProcess or raises TimeoutExpired; the
    default runs the command as a subprocess, and the tests inject one."""

    def __init__(self, ext=EXT, cmd=("node", "esbuild.js"), inputs=None, root=ROOT, timeout=BUILD_TIMEOUT, run=None):
        # absolute first, as the three derivation functions make theirs: the dist prune in _input_files and the
        # dependency filter compare paths textually against the walk's absolute paths, so a relative `ext` kept
        # dist's outputs in the key (every build changed them, so every call rebuilt) and stat-keyed package-lock.json
        ext = os.path.abspath(ext)
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
            # the served labs' standing behaviour: a checkout whose environment cannot build skips with the reason,
            # here and in esbuild_exports (a package the config requires that node cannot find); every other
            # failure of the harness raises
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
    """The checkout's own DistBuild, made on first use: deriving its inputs starts node to read esbuild.js's
    exports and scans the keyed trees for imports (a node start and about a tenth of a second), which every
    process that imports this module need not pay (tests/__init__.py imports it to register the name)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = DistBuild()
    return _DEFAULT


def copy_dist(dest):
    """The served labs' call: a private, serve-ready copy of the checkout's bundles at `dest`."""
    default().copy_to(dest)
