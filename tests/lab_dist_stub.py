"""A node preload that stands in for every bare package node cannot resolve, so the two real-tree pins run on a
checkout without the extension's node_modules (review round 7 of the served labs' build harness, decision 1; round 8
widened it from the one package esbuild to any bare specifier).

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
specifier at once.

This module stands the packages in, test-side only: `bare_package_stub()` writes a preload script and puts it on
NODE_OPTIONS (`--require <preload>`) for the duration of the block, so every node the block starts, the harness's
`node -e` reader included, loads it first. The preload wraps `Module._load`: a bare specifier that fails to resolve
(`esbuild`, `@scope/pkg`; never `./x`, never an absolute path, and never a miss nested inside a module that did
resolve, which names a different request) returns the throwing stand-in in place of the MODULE_NOT_FOUND, and
every specifier that resolves loads the real module untouched (tests/test_lab_dist.py pins both halves: a config
requiring two missing bare packages derives its trees; one requiring a package that IS installed reads the real
package's data). The pins run the same code on both kinds of checkout, and the run with node_modules present
reads the real package. The harness itself stays strict: nothing in tests/lab_dist.py knows this module exists, so
a served lab on a checkout without node_modules still skips, and a derivation that fails still raises.

The stand-in refuses every read: a Proxy trapping property reads, the `in` operator, enumeration (Object.keys, a
spread, for...in, Object.assign) and own-property lookup, each throwing an error that names this file, the package
and the read. A plain empty object would answer a read such as `esbuild.version` at load with undefined and let it
flow into the exported data as the string "undefined", in silence, and would answer `"context" in esbuild` with
false and let the config take a branch the real package never takes; under the Proxy such a config fails to load,
the pin fails loudly, and the failure names this module, so the day the config starts reading a package at require
time this stand-in is the first thing to change. A config that exports the module ITSELF fails from the reader's
JSON.stringify, which reads `toJSON` first; that read gets its own message, naming the reader (the real package
fails that shape too, with a circular-structure TypeError). A skip raised inside the block is re-raised as a
failure: the one skip the derivation raises is the missing-bare-package one, and under the preload it means the
stand-in did not take effect. Synthetic paths only: the preload lives under the process temp dir and is removed
when the block ends."""
import contextlib
import os
import shutil
import tempfile
import unittest
from unittest import mock

PRELOAD = r'''
// The served labs' test-side stand-in for the bare packages this checkout lacks (tests/lab_dist_stub.py), loaded
// through NODE_OPTIONS=--require ahead of the harness's reader. A bare specifier node cannot resolve returns the
// stand-in; everything that resolves loads the real module. The stand-in covers a dependency of the BUILD, never of
// the exported data, so any read of it at require time is a bug in the premise and throws, naming the read.
const Module = require("module");
const path = require("path");
const realLoad = Module._load;
const WHERE = "the served labs' package stand-in (tests/lab_dist_stub.py)";

function standIn(request) {
  const refuse = (what) => {
    throw new Error(WHERE + " for '" + request + "', which node could not resolve here: the config " + what +
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

Module._load = function (request, parent, isMain) {
  try {
    return realLoad.apply(this, arguments);
  } catch (e) {
    const bare = typeof request === "string" && !request.startsWith(".") && !path.isAbsolute(request);
    const hit = e && e.code === "MODULE_NOT_FOUND" && /^Cannot find module '([^']+)'/.exec(String(e.message));
    if (bare && hit && hit[1] === request) return standIn(request);   // a nested miss names another request: real
    throw e;
  }
};
'''


@contextlib.contextmanager
def bare_package_stub():
    """A block in which `require()` of a bare package node cannot resolve returns the throwing stand-in instead of
    failing, in every node the block starts: NODE_OPTIONS gains `--require <preload>` ahead of whatever it already
    held, so the harness's reader loads the preload first. Everything that resolves loads the real module. Raises
    unittest.SkipTest when node is not on PATH, the one precondition a stand-in cannot supply. A SkipTest raised
    INSIDE the block is re-raised as AssertionError: the only skip the derivation raises is the missing-bare-package
    one (esbuild_exports), and under the preload it means the stand-in did not take effect (a node wrapper or a
    policy dropped NODE_OPTIONS, or the preload's rule missed the request), the regression the real-tree pins
    exist to catch; a skip there would read as green. Keep only the derivation inside the block. Yields the
    preload's path."""
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
                                     "take effect (a node wrapper or a policy dropping NODE_OPTIONS?) or its rule missed "
                                     "the request: extend tests/lab_dist_stub.py; a skip here would hide the regression "
                                     "the real-tree pins guard against. The skip: %s" % e) from e
    finally:
        shutil.rmtree(d, ignore_errors=True)
