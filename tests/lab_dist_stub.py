"""A node preload that stands in for a bare package the build config itself requires and node cannot find, on a
checkout without the extension's node_modules, so the two real-tree pins run there (review round 7 of the served
labs' build harness, decision 1; round 8 widened it from the one package esbuild to any bare specifier; round 9
narrowed it to the config's own requires, to packages whose root is nowhere on the lookup paths, and to a checkout
with no node_modules beside the config; round 10 made the requirer test read the requirer's filename rather than
the depth of the load; round 11 made that test exact: the harness names the config to the preload; round 12 realpaths
the requirer's filename before the compare, tests the package's root ahead of a core module's name and excludes
package-imports specifiers; round 13 excludes a one-segment scoped name, `@scope` alone; round 14 reads the bare
shape and the package's name from one split of the request, and excludes an empty scope and any empty, `.` or `..`
segment; round 15 judges the name segments alone, so a subpath spelling node resolves to the installed package,
`pkg/`, `pkg/./index`, is that package's request and the miss of an absent one is the environment as `pkg` is).

The harness (tests/lab_dist.py) derives the build's inputs by requiring the extension's build config under node
and reading what it exports. The config's first line requires esbuild, a dependency of the BUILD and not of the
exported data: nothing the config exports is read from that module, and nothing touches it at require time
(the build functions use it; the guard at the end keeps them from running on require). On a checkout without
node_modules the require fails, and the harness skips the served labs there, as it does on a failed build.
The two pins that compare the derivation against the real tree (`test_the_real_config_derives_the_kernel_trees`
in tests/test_lab_dist.py and the kernel parity pin in tests/test_kernel_bundle_staleness.py) are the only check
that the harness keys what the kernel rebuilds for, and CI's Python job runs no `npm ci`, so until this module
they skipped there and ran only where a developer had installed the extension's dependencies (round 6 of the
review). Round 7 stood in for the one package by name (an `esbuild/index.js` on NODE_PATH), so the day esbuild.js
required a second bare package both pins went back to skipping in silence; the preload here covers every bare
package the config requires at once.

This module stands the packages in, test-side only: `bare_package_stub()` writes a preload script and puts it on
NODE_OPTIONS (`--require <preload>`) for the duration of the block, so every node the block starts, the harness's
`node -e` reader included, loads it first. The preload wraps `Module._load`, the door every `require()` takes, and a
specifier naming a package (`esbuild`, `@scope/pkg`, a subpath spelling of one, `pkg/sub`, `pkg/`; never `./x`, never
an absolute path, never `#x`, an imports-map specifier the nearest package.json resolves, which npm ci cannot
install, and never a request whose NAME segments, the first, two for a scoped request, name no package: a scoped
request with fewer than two segments or an empty scope, `@scope`, `@/x`, and a name segment that is empty, `.` or
`..`, `@scope/`, `@scope//pkg`, `@scope/./x`; npm installs packages under a scope directory and nothing at the
directory itself, and a dot or an empty segment names no package, so the miss is a typo in the requirer and node's
error stays, whatever is installed; the subpath after the name is not judged, since node resolves `pkg/`,
`pkg/./index` and `pkg/../pkg` to the installed package, so each is judged as `pkg` is; and the rule reads segments,
never a name's characters, so a name npm would refuse for its spelling, a space, a backslash, a drive letter, a
non-ASCII character, passes as a package and its miss is stood in or refused like any other bare name's, a
pre-existing bound; the name is read from the same split, so a scope directory is never a root) that fails to
resolve returns the throwing stand-in
in place of the MODULE_NOT_FOUND under three conditions, each of which tells the environment the
stand-in exists for, a checkout without node_modules, from a real error:
- the CONFIG itself made the require: the requirer's filename, realpathed, is the config's realpath, which the
  harness publishes to the reader's node run in the environment variable tests/lab_dist.py names in CONFIG_ENV (node
  names a loaded module by its realpath, except under `--preserve-symlinks`, which an inherited NODE_OPTIONS can carry
  and which keeps the textual path, so the preload realpaths the filename itself and a config reached through a
  symlinked directory compares equal either way; round 12, before which the compare was textual and the flag lost the
  stand-in. The flag also moves where node SEARCHES, to the textual path's chain, while the harness's reader computes
  every chain from realpaths, so under the flag a package present on one chain and not the other is judged
  differently by the two rules, a residual; the config's own miss, a package on neither chain, is judged alike). A
  require made from inside any other module stays node's error, at any depth and at any time:
  an installed package's optional-require probe (`try { require("pnpapi") } catch {}`) must throw as it does in the
  real environment, in the package's top level, in a function the config calls at load, or in a getter chain the
  reader's JSON.stringify triggers after the config's load returned; a package hard-requiring a missing dependency
  is a broken install; and a helper file the config requires relatively is a module of the checkout whose bare
  requires are its own to fix, not the environment (a subpath into a package on the helper's own chain is a typo in
  the helper, or an install at a version without that file, and the reader names the root; a package on no chain is
  one to move into the config or install). The config's own requires are
  stood in at any time too: one made after its load returned, from a getter on the exported object, is stood in
  and fails as the stand-in's refusal naming the read (both exit 1), whatever other module loaded in between.
  Round 10 inferred the config from the loads instead (the last module loaded outside any load in progress), which
  took a package a getter loaded for the config and stood in for that package's own misses, and lost the config's
  getter-time requires once another module had loaded at the same depth; round 9 read the depth of the load, and a
  require inside a function the config called at load arrived at the config's depth. With the variable absent the
  preload knows no config, stands in for nothing, and throws naming the variable on the first bare miss it would
  have judged, so a harness that stopped setting it, or a node the block never meant to cover, fails loudly rather
  than skipping or standing in;
- the package's ROOT is nowhere on the requirer's lookup paths (its node_modules chain plus node's global folders,
  the list `require.resolve.paths` reports for every bare request that is not a core module's name, read here for a
  fixed probe name) and its name is not a core module's: `esbuild/lib/nope` with esbuild installed is a typo in the
  requirer, the config or a helper of the checkout, or an install at a version without that file, never the
  environment, and stays node's error; so does `fs/nope`, a subpath into one of
  node's core modules, which is present in every node (what `Module.isBuiltin` reports; round 11, before which
  `resolve.paths`'s null for a core module's name read as an empty list and the miss was stood in). The root is
  tested first (round 12): a userland package named like a core module (punycode, events, buffer) resolves its
  subpaths from the chain, so its root on the chain is the evidence, and the reader words the miss as the installed
  package's, where reading `resolve.paths`'s null first called it a typo into the core module;
- no node_modules directory exists beside the config. One that exists and lacks the package is a stale install
  (node_modules predating a newly added dependency), and the preload THROWS there, naming this file, the package
  and the directory, instead of standing in; so the pins go red on a stale install where the served labs skip.
Every specifier that resolves loads the real module untouched. One door is outside the stand-in: `require.resolve()`
resolves through `Module._resolveFilename` and makes no load, so a config that resolves a bare package that way (the
real esbuild.js does not) fails as the environment where the stand-in would have covered a `require()` of the same
name: the reader files the miss as a skip, and inside `bare_package_stub`'s block that skip is the AssertionError,
which names this cause. A resolve wrapper is not worth its risk at this exposure: `Module._load`'s own resolution
passes through `_resolveFilename` too, one level deeper, and a wrapper throwing there would break the plain
`require()` stand-in. tests/test_lab_dist.py pins each edge: a config requiring three missing bare packages on a
checkout without node_modules derives its trees; one requiring a package that IS installed reads the real package's
data; a bare miss inside an installed package, hard or probed, in its top level, in a function the config calls at
load or in a getter chain the reader triggers, is the same result with and without the preload; a bare miss inside
a helper the config requires relatively is node's error both ways, the reader naming the helper; a subpath into an
installed package raises, and so does one into a core module; a node_modules lacking one package the config
requires is red under the preload; a `require.resolve` of a missing bare package skips plain and is the block's
AssertionError naming `require.resolve`; a getter's bare require is stood in after another module loaded at the same
depth; a module a pre-existing `--require` loaded before the config is not taken for it, and its own bare miss is
node's error; the variable absent is the refusal naming it, and the harness sets it to the config's realpath. The
pins run the same code on both kinds of checkout, and the run with node_modules present reads the real package. The
harness itself stays strict: nothing in tests/lab_dist.py knows this module exists (its reader classifies a miss by
the bare-shape, root and requirer tests, in that order, the order this preload applies them, and files the config's
own miss as a skip, never a
stand-in; it has no counterpart to the third condition above, so on a stale install it skips where this module
refuses, the one case the two rules answer differently, the reader quietly and the stand-in loudly; it publishes the
config's realpath for any preload and names none), so a served lab on a checkout without node_modules still skips,
and a derivation that fails still raises.

The stand-in refuses every read: a Proxy trapping property reads, the `in` operator, enumeration (Object.keys, a
spread, for...in, Object.assign) and own-property lookup, each throwing an error that names this file, the package,
the requiring file and the read. A plain empty object would answer a read such as `esbuild.version` at load with
undefined and let it flow into the exported data as the string "undefined", in silence, and would answer
`"context" in esbuild` with false and let the config take a branch the real package never takes; under the Proxy
such a config fails to load, the pin fails loudly, and the failure names this module, so the day the config starts
reading a package at require time this stand-in is the first thing to change. A config that exports the module
ITSELF fails from the reader's JSON.stringify, which reads `toJSON` first; that read gets its own message, naming
the reader (the real package fails that shape too, with a circular-structure TypeError). A skip raised inside the
block is re-raised as a failure: the one skip the derivation raises is the missing-bare-package one, and under the
preload it means the stand-in did not take effect. Synthetic paths only: the preload lives under the process temp
dir and is removed when the block ends."""
import contextlib
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from lab_dist import CONFIG_ENV     # the one spelling of the variable the harness sets and this preload reads

PRELOAD = r'''
// The served labs' test-side stand-in for the bare packages a checkout without node_modules lacks
// (tests/lab_dist_stub.py), loaded through NODE_OPTIONS=--require ahead of the harness's reader. The rule (review
// round 9; the requirer test corrected in round 10, made exact in round 11 and realpathed in round 12; a one-segment
// scoped name excluded in round 13; the bare shape and the package's name read from one split in round 14; the name
// segments alone judged in round 15): a specifier naming a package (never `./x`, an absolute path or `#x`, a
// package-imports specifier the nearest package.json resolves, which npm ci cannot install; never a request whose
// NAME segments name no package: a scoped request with fewer than two segments or an empty scope, `@scope`, `@/x`,
// or a name segment that is empty, `.` or `..`, `@scope/`, `@scope//pkg`, `@scope/./x`; the subpath after the name
// is not judged, so `pkg/` and `pkg/./index` are the package pkg's requests, and a name's characters are not read)
// node cannot resolve is stood in under three conditions, listed here by what each tells apart (the code below tests
// the bare shape first, then the root and the core module's name, then that the variable is set, then the requirer,
// then node_modules): only when the config itself required
// it (the requirer's filename, realpathed, is the config's realpath, which the harness publishes in the environment variable
// named below; a require made from inside any other module stays node's error at any depth and at any time, an
// installed package's probe or hard require, in its top level, in a function the config calls at load or in a getter
// the reader triggers, and a helper the config requires relatively alike), only when the package's root is nowhere on
// the requirer's lookup paths and its name is not a core module's (a subpath into an installed package is a typo in
// the requirer, the config or a helper of the checkout, or an install at a version without that file, never the
// environment, a userland package named like a core module included, and a subpath into one of node's
// core modules, `fs/nope`, names a package present in every node), and only when no node_modules directory exists
// beside the config (one that exists and lacks
// the package is a stale install: the preload throws, naming itself, instead of standing in). With the variable
// absent the preload stands in for nothing and throws, naming the variable, on the first bare miss it would have
// judged: the harness sets it on every reader run, so its absence means a node this block never meant to cover, or a
// harness that stopped setting it. Everything that resolves loads the real module. The stand-in covers a dependency
// of the BUILD, never of the exported data, so any read of it at require time is a bug in the premise and throws,
// naming the read. Only Module._load is wrapped, the door every require() takes; require.resolve() resolves through
// Module._resolveFilename with no load and is outside the stand-in (a config resolving a bare package that way fails
// as the environment: the reader's skip, and inside bare_package_stub's block the AssertionError naming this cause).
const Module = require("module");
const fs = require("fs");
const path = require("path");
const realLoad = Module._load;
const WHERE = "the served labs' package stand-in (tests/lab_dist_stub.py)";
// The config's realpath, as the harness publishes it for the reader's node run (tests/lab_dist.py, CONFIG_ENV): the
// requirer test below compares the requirer's filename, realpathed, with it (node names a loaded module by its
// realpath, except under --preserve-symlinks, which keeps the textual path)
const PROBE = "@lab-dist/probe";   // a bare request that is never a core module's name: the lookup chain, read for it, is the requirer's
const CONFIG_ENV = __CONFIG_ENV__;
const CONFIG = process.env[CONFIG_ENV];

function standIn(request, from) {
  const refuse = (what) => {
    throw new Error(WHERE + " for '" + request + "', which node could not resolve here: " + from + " " + what +
                    " at require time; the stand-in covers a dependency of the build, never of the exported data");
  };
  return new Proxy({}, {
    get(_target, name) {
      if (typeof name === "symbol") return undefined;
      if (name === "toJSON") {
        refuse("exported the " + request + " module itself, and the reader's JSON.stringify read " + request + ".toJSON");
      }
      refuse("read " + request + "." + String(name));
    },
    has(_target, name) {
      if (typeof name === "symbol") return false;
      refuse("tested '" + String(name) + "' in " + request);
    },
    ownKeys() {
      refuse("enumerated " + request + " (Object.keys, a spread, for...in, Object.assign)");
    },
    getOwnPropertyDescriptor(_target, name) {
      if (typeof name === "symbol") return undefined;
      refuse("looked up " + request + "'s own property '" + String(name) + "'");
    },
  });
}

// The package a request names, or null for a request that names no package, from ONE split of the request, the same
// rule spelled the same as the reader's (tests/lab_dist.py, packageOf; round 14: round 13 split twice, the bare test
// over the non-empty segments and packageName over all of them, so `@scope//pkg` passed as bare and named the scope
// directory as its root, `@/x` passed with an empty scope and was stood in, and `pkg/../x` and `@scope/./x` reached
// path.join, which folded the dot segment away and named the parent directory as the root). Null, so node's error
// stays whatever the requirer and whatever is installed, for `./x`, an absolute path, `#x` (a package-imports
// specifier the nearest package.json resolves, which npm ci cannot install) and a request whose NAME segments, the
// first one, two for a scoped request, name no package: a scoped request with fewer than two segments or a bare `@`
// for its scope (`@scope`, `@`, `@/x`), and a name segment that is empty, `.` or `..` (`@scope/`, `@scope//pkg`,
// `@scope/./x`; an unscoped request's one name segment can only be empty, the empty request): npm installs packages
// under a scope directory (`@scope/pkg`) and nothing at the directory itself, and no package is named through a dot or
// an empty segment, so each is a typo in the requirer (node itself folds a doubled slash or a dot segment away once
// the target exists, so `@scope//q` loads while `@scope/q` is installed; a miss spelled so is still the typo, never
// the environment). Otherwise the name is the first segment, two for a scoped one (`@scope/pkg/sub` names @scope/pkg),
// and the segments after it, the subpath, are not judged (round 15; round 14 refused any empty, `.` or `..` segment,
// so `pkg/` named no package and a config requiring it where no pkg resolves was node's error where `pkg` is stood
// in): node resolves `pkg/`, `pkg/./index` and `pkg/../pkg` to the installed package, so each is judged as `pkg` is,
// and rootPresent joins the name alone, never a segment path.join would fold. The rule reads segments, never a name's
// characters: a name npm would refuse for its spelling (a space, a backslash, a drive letter, a non-ASCII character)
// is a package here and its miss is stood in or refused like any other bare name's.
function packageOf(r) {
  if (r.startsWith(".") || r.startsWith("#") || path.isAbsolute(r)) return null;
  const parts = r.split("/"), scoped = r.startsWith("@");
  if (scoped && (parts[0] === "@" || parts.length < 2)) return null;
  const name = parts.slice(0, scoped ? 2 : 1);
  if (name.some((p) => p === "" || p === "." || p === "..")) return null;
  return name.join("/");
}

// Is the package `name`, packageOf's answer for a bare request, present for a require from `from`: its root directory on a path node searched
// from there (the requirer's node_modules chain plus node's global folders, NODE_PATH, $HOME/.node_modules,
// $HOME/.node_libraries, $PREFIX/lib/node, the same list require.resolve.paths reports for any bare request that is
// not a core module's name, read for PROBE so the list is the requirer's whatever the request), or, with no such root,
// one of node's core modules (what Module.isBuiltin reports), which every node has? Either way the miss is a subpath
// the package does not have, a typo, and never the environment. The root first (round 12): a userland package named
// like a core module (punycode, events) shadows it for subpaths, so the root on the chain is the evidence, and the
// reader (tests/lab_dist.py) words the miss by the same order.
function rootPresent(name, from) {
  const paths = Module.createRequire(from).resolve.paths(PROBE) || [];
  if (paths.some((p) => fs.existsSync(path.join(p, name)))) return true;
  return Module.isBuiltin(name);
}
// Is `from`, the requirer's filename as node names it, the config? By realpath: node names a loaded module by its
// realpath, except under --preserve-symlinks (an inherited NODE_OPTIONS can carry it), when it keeps the textual path
// and a config reached through a symlinked directory compared unequal (round 12); a filename the file system does not
// know is compared as it stands
function isConfig(from) {
  try { return fs.realpathSync(from) === CONFIG; } catch (_) { return from === CONFIG; }
}

Module._load = function (request, parent, isMain) {
  try {
    return realLoad.apply(this, arguments);
  } catch (e) {
    // name: the package the request names, null for a request that is not a package's (`./x`, an absolute path, `#x`,
    // a scoped request with fewer than two segments or an empty scope, a name segment that is empty, `.` or `..`; the
    // rule above packageOf), where node's error stays whatever is installed (round 13 excluded `@scope` alone, before
    // which rootPresent found the scope directory the sibling packages had created and rethrew, so the reader called
    // the typo a package that does not load, and with no node_modules the miss was stood in; round 14 the rest; round
    // 15 stopped judging the subpath, so `pkg/` is pkg's request again)
    const name = typeof request === "string" ? packageOf(request) : null;
    const hit = e && e.code === "MODULE_NOT_FOUND" && /^Cannot find module '([^']+)'/.exec(String(e.message));
    const from = parent && typeof parent.filename === "string" ? parent.filename : null;
    // hit[1] === request: a miss nested inside a module that did resolve names another request and is rethrown by
    // the frame that loaded it; from: a load with no requiring file (node's own preload parent has no filename) is
    // never the config's; rootPresent: a subpath into an installed package or into a core module is node's error
    if (!(name && hit && hit[1] === request && from) || rootPresent(name, from)) throw e;
    if (!CONFIG) {
      throw new Error(WHERE + " cannot judge the require of '" + request + "' by " + from + ": " + CONFIG_ENV + " is not " +
                      "set, so which file is the config is unknown here, and the preload stands in for nothing; the harness " +
                      "sets it to the config's realpath on every reader run");
    }
    if (!isConfig(from)) throw e;       // a miss inside any other module is node's error, at any depth and at any time
    const installed = path.join(path.dirname(from), "node_modules");
    if (fs.existsSync(installed)) {
      throw new Error(WHERE + " declines to stand in for '" + request + "', required by " + from + ": " +
                      installed + " exists and holds no such package, a stale install (node_modules predating a newly " +
                      "added dependency; run npm ci) or a package the lock files do not list; the stand-in covers a " +
                      "checkout without node_modules, never an incomplete one");
    }
    return standIn(request, from);
  }
};
'''.replace("__CONFIG_ENV__", json.dumps(CONFIG_ENV))


@contextlib.contextmanager
def bare_package_stub():
    """A block in which `require()` of a package (`esbuild`, `@scope/pkg`, a subpath spelling of one, `pkg/`; never
    `./x`, an absolute path, a `#x` package-imports specifier, or a request whose name segments name no package: a
    scoped request with fewer than two segments or an empty scope, `@scope`, `@/x`, and a name segment that is empty,
    `.` or `..`, `@scope/`, `@scope//pkg`, `@scope/./x`) that the config
    itself requires (the requirer's filename,
    realpathed, is the config's realpath, which
    the harness publishes to every reader run in the environment variable lab_dist.CONFIG_ENV names), that node
    cannot resolve, whose root is nowhere on the lookup paths and whose name is not a core module's returns the
    throwing stand-in instead of failing, in every node the block starts, on a checkout with no node_modules beside
    the config: NODE_OPTIONS gains `--require <preload>` ahead of whatever it already held (a `--preserve-symlinks`
    there is honoured: the realpath compare keeps the config's own miss stood in through a symlinked directory), so
    the harness's reader loads the preload first. Everything that resolves loads the real module; a require from
    inside any other module (an installed package, in its top level, in a function the config calls at load or in a
    getter the reader triggers; a helper the config requires relatively; a module a pre-existing `--require` loaded),
    a subpath into an installed package (one named like a core module included) or into one of node's core modules,
    a package-imports specifier, a request whose name segments name no package (the shapes above), and a node_modules that exists and lacks the package are
    errors (the last one thrown
    by the preload, naming this file). A node started inside the block without the
    variable (the harness sets it on the reader's run only) gets no stand-in: the preload throws on the first bare
    miss it would have judged, naming the variable. `require.resolve()` of a bare package is outside the stand-in (it
    makes no load, and only Module._load is wrapped), so a config resolving a missing package that way skips plain and
    fails inside the block, by the conversion below. Raises unittest.SkipTest when node is not on PATH, the one
    precondition a stand-in cannot supply. A SkipTest raised INSIDE the block is re-raised as AssertionError: the only
    skip the derivation raises is the missing-bare-package one (esbuild_exports), and under the preload it means the
    stand-in did not take effect (a node wrapper or a policy dropped NODE_OPTIONS, the reader filed as the environment
    a request the preload's rule declined, or the config resolved the package with require.resolve), the regression
    the real-tree pins exist to catch; a skip there would read as green. Keep only the derivation inside the block.
    Yields the preload's path."""
    if shutil.which("node") is None:
        raise unittest.SkipTest("node is not on PATH: the derivation cannot require the config here")
    d = tempfile.mkdtemp(prefix="lab-dist-package-stub-")
    try:
        preload = os.path.join(d, "preload.js")
        with open(preload, "w", encoding="utf-8") as f:
            f.write(PRELOAD)
        existing = os.environ.get("NODE_OPTIONS", "")
        option = '--require "%s"' % preload      # quoted: NODE_OPTIONS splits on whitespace, and a temp root may hold a space
        with mock.patch.dict(os.environ, {"NODE_OPTIONS": option + (" " + existing if existing else "")}):
            try:
                yield preload
            except unittest.SkipTest as e:
                raise AssertionError("a bare package went uncovered inside the stand-in's block, so the preload did not "
                                     "take effect (a node wrapper or a policy dropping NODE_OPTIONS?), or the reader filed "
                                     "as the environment a request the preload's rule declined (the two rules in "
                                     "tests/lab_dist_stub.py and tests/lab_dist.py must agree), or the config resolved the "
                                     "package with require.resolve, which the stand-in does not cover (only Module._load "
                                     "is wrapped); a skip here would hide the regression the real-tree pins guard "
                                     "against. The skip: %s" % e) from e
    finally:
        shutil.rmtree(d, ignore_errors=True)
