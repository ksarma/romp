"""A node preload that stands in for a bare package the build config itself requires and node cannot find, on a
checkout without the extension's node_modules, so the two real-tree pins run there (review round 7 of the served
labs' build harness, decision 1; round 8 widened it from the one package esbuild to any bare specifier; round 9
narrowed it to the config's own requires, to packages whose root is nowhere on the lookup paths, and to a checkout
with no node_modules beside the config).

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
`node -e` reader included, loads it first. The preload wraps `Module._load`, and a bare specifier (`esbuild`,
`@scope/pkg`; never `./x`, never an absolute path) that fails to resolve returns the throwing stand-in in place of
the MODULE_NOT_FOUND under three conditions, each of which tells the environment the stand-in exists for, a
checkout without node_modules, from a real error:
- the CONFIG itself made the require: the requirer is the module the reader's entry loaded (the outermost module
  node is loading; under the harness's `node -e` reader, whose script requires the config, that is the config). A
  require made from inside any other module stays node's error: an installed package's optional-require probe
  (`try { require("pnpapi") } catch {}`) must throw as it does in the real environment, and a package hard-requiring
  a missing dependency is a broken install, not the environment;
- the package's ROOT is nowhere on the requirer's lookup paths (its node_modules chain plus node's global folders,
  the list `require.resolve.paths` reports): `esbuild/lib/nope` with esbuild installed is a config typo, or an
  install at a version without that file, and stays node's error;
- no node_modules directory exists beside the config. One that exists and lacks the package is a stale install
  (node_modules predating a newly added dependency), and the preload THROWS there, naming this file, the package
  and the directory, instead of standing in; so the pins go red on a stale install where the served labs skip.
Every specifier that resolves loads the real module untouched. tests/test_lab_dist.py pins each edge: a config
requiring three missing bare packages on a checkout without node_modules derives its trees; one requiring a package
that IS installed reads the real package's data; a bare miss inside an installed package, hard or probed, is the
same result with and without the preload; a subpath into an installed package raises; a node_modules lacking one
package the config requires is red under the preload. The pins run the same code on both kinds of checkout, and
the run with node_modules present reads the real package. The harness itself stays strict: nothing in
tests/lab_dist.py knows this module exists (its reader classifies a miss by the same three tests, requirer, root and
bare shape, but files the config's own miss as a skip, never a stand-in), so a served lab on a checkout without
node_modules still skips, and a derivation that fails still raises.

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
import os
import shutil
import tempfile
import unittest
from unittest import mock

PRELOAD = r'''
// The served labs' test-side stand-in for the bare packages a checkout without node_modules lacks
// (tests/lab_dist_stub.py), loaded through NODE_OPTIONS=--require ahead of the harness's reader. The rule (review
// round 9): a bare specifier node cannot resolve is stood in only when the config itself required it (the outermost
// module node is loading; a require made from inside any other module stays node's error), only when the package's
// root is nowhere on the requirer's lookup paths (a subpath into an installed package is a config typo, not the
// environment), and only when no node_modules directory exists beside the config (one that exists and lacks the
// package is a stale install: the preload throws, naming itself, instead of standing in). Everything that resolves
// loads the real module. The stand-in covers a dependency of the BUILD, never of the exported data, so any read of
// it at require time is a bug in the premise and throws, naming the read.
const Module = require("module");
const fs = require("fs");
const path = require("path");
const realLoad = Module._load;
const WHERE = "the served labs' package stand-in (tests/lab_dist_stub.py)";

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

// The package a bare specifier names: its first segment, two for a scoped one (`@scope/pkg/sub` names @scope/pkg).
function packageName(request) {
  const parts = request.split("/");
  return (request.startsWith("@") ? parts.slice(0, 2) : parts.slice(0, 1)).join("/");
}

// Does the package's root directory exist on any path node searched from `from`? The list is the requirer's
// node_modules chain plus node's global folders (NODE_PATH, $HOME/.node_modules, $HOME/.node_libraries,
// $PREFIX/lib/node), the same one require.resolve.paths reports, so a subpath miss into an installed package is told
// from a package that is nowhere.
function rootInstalled(request, from) {
  const name = packageName(request);
  const paths = Module.createRequire(from).resolve.paths(name) || [];
  return paths.some((p) => fs.existsSync(path.join(p, name)));
}

// Loads in progress through this wrapper. The reader's entry (`node -e`) requires the config outside any load, so
// the config loads at depth 1 and a require the config makes arrives while the depth is 1; a require from inside a
// module the config loaded arrives at depth 2 or deeper. The requirer is the config exactly when the depth is 1.
let loading = 0;

Module._load = function (request, parent, isMain) {
  const fromConfig = loading === 1 && parent && typeof parent.filename === "string";
  loading += 1;
  try {
    return realLoad.apply(this, arguments);
  } catch (e) {
    const bare = typeof request === "string" && !request.startsWith(".") && !path.isAbsolute(request);
    const hit = e && e.code === "MODULE_NOT_FOUND" && /^Cannot find module '([^']+)'/.exec(String(e.message));
    // hit[1] === request: a miss nested inside a module that did resolve names another request and is rethrown
    // by the frame that loaded it; fromConfig: a miss inside any other module is node's error; rootInstalled: a
    // subpath into an installed package is node's error
    if (!(bare && hit && hit[1] === request && fromConfig) || rootInstalled(request, parent.filename)) throw e;
    const installed = path.join(path.dirname(parent.filename), "node_modules");
    if (fs.existsSync(installed)) {
      throw new Error(WHERE + " declines to stand in for '" + request + "', required by " + parent.filename + ": " +
                      installed + " exists and holds no such package, a stale install (node_modules predating a newly " +
                      "added dependency; run npm ci) or a package the lock files do not list; the stand-in covers a " +
                      "checkout without node_modules, never an incomplete one");
    }
    return standIn(request, parent.filename);
  } finally {
    loading -= 1;
  }
};
'''


@contextlib.contextmanager
def bare_package_stub():
    """A block in which `require()` of a bare package that the config itself requires, that node cannot resolve and
    whose root is nowhere on the lookup paths returns the throwing stand-in instead of failing, in every node the
    block starts, on a checkout with no node_modules beside the config: NODE_OPTIONS gains `--require <preload>`
    ahead of whatever it already held, so the harness's reader loads the preload first. Everything that resolves
    loads the real module; a require from inside any other module, a subpath into an installed package and a
    node_modules that exists and lacks the package are errors (the last one thrown by the preload, naming this file).
    Raises unittest.SkipTest when node is not on PATH, the one precondition a stand-in cannot supply. A SkipTest
    raised INSIDE the block is re-raised as AssertionError: the only skip the derivation raises is the
    missing-bare-package one (esbuild_exports), and under the preload it means the stand-in did not take effect (a
    node wrapper or a policy dropped NODE_OPTIONS, or the reader filed as the environment a request the preload's
    rule declined), the regression the real-tree pins exist to catch; a skip there would read as green. Keep only
    the derivation inside the block. Yields the preload's path."""
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
                                     "take effect (a node wrapper or a policy dropping NODE_OPTIONS?) or the reader filed "
                                     "as the environment a request the preload's rule declined: the two rules in "
                                     "tests/lab_dist_stub.py and tests/lab_dist.py must agree; a skip here would hide the "
                                     "regression the real-tree pins guard against. The skip: %s" % e) from e
    finally:
        shutil.rmtree(d, ignore_errors=True)
