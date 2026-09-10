"""A NODE_PATH stub of the esbuild package, so the two real-tree pins run on a checkout without the extension's
node_modules (review round 7 of the served labs' build harness, decision 1).

The harness (tests/lab_dist.py) derives the build's inputs by requiring the extension's build config under node
and reading what it exports. The config's first line requires esbuild, a dependency of the BUILD and not of the
exported data: nothing the config exports is read from that module, and nothing touches it at require time
(the build functions use it; the guard at the end keeps them from running on require). On a checkout without
node_modules the require fails, and the harness skips the served labs there, as it does on a failed build.
The two pins that compare the derivation against the real tree (`test_the_real_config_derives_the_kernel_trees`
in tests/test_lab_dist.py and the kernel parity pin in tests/test_kernel_bundle_staleness.py) are the only check
that the harness keys what the kernel rebuilds for, and CI's Python job runs no `npm ci`, so until this stub
they skipped there and ran only where a developer had installed the extension's dependencies (round 6 of the
review).

This module stands the package in, test-side only: `esbuild_stub()` writes a directory holding
`esbuild/index.js` and puts it on NODE_PATH for the duration of the block. Node consults NODE_PATH after the
node_modules walk fails, so the stub is inert wherever the real package resolves (the pins run the same code
on both kinds of checkout, and the run with node_modules present reads the real package). The harness itself
stays strict: nothing in tests/lab_dist.py knows this module exists, so a served lab on a checkout without
node_modules still skips, and a derivation that fails still raises.

The stub exports the names the config touches at require time, which is none, and refuses every other read:
module.exports is a Proxy whose property reads throw. A plain empty object would answer a read such as
`esbuild.version` at load with undefined and let it flow into the exported data as the string "undefined", in
silence; under the Proxy such a config fails to load, the pin fails loudly, and the failure names this stub, so
the day the config starts reading esbuild at require time the stub is the first thing to change. Synthetic
paths only: the directory lives under the process temp dir and is removed when the block ends."""
import contextlib
import os
import shutil
import tempfile
import unittest
from unittest import mock

STUB = r'''
// The served labs' test-side stand-in for the esbuild package (tests/lab_dist_stub.py): a dependency of the
// BUILD, never of the exported data. Any read of it at require time is a bug in the stub's premise, so it throws.
module.exports = new Proxy({}, {
  get(_target, name) {
    if (typeof name === "symbol") return undefined;
    throw new Error("esbuild stub (tests/lab_dist_stub.py): the config read esbuild." + String(name) +
                    " at require time; the stub stands in for a dependency of the build, not of the exported data");
  },
});
'''


@contextlib.contextmanager
def esbuild_stub():
    """A block in which `require("esbuild")` resolves to the stub wherever the real package does not: NODE_PATH
    gains a fresh directory holding esbuild/index.js, ahead of whatever NODE_PATH already named. Raises
    unittest.SkipTest when node is not on PATH, the one precondition a stub cannot supply. Yields the stub
    directory."""
    if shutil.which("node") is None:
        raise unittest.SkipTest("node is not on PATH: the derivation cannot require the config here")
    d = tempfile.mkdtemp(prefix="lab-dist-esbuild-stub-")
    try:
        os.makedirs(os.path.join(d, "esbuild"))
        with open(os.path.join(d, "esbuild", "index.js"), "w", encoding="utf-8") as f:
            f.write(STUB)
        existing = os.environ.get("NODE_PATH", "")
        with mock.patch.dict(os.environ, {"NODE_PATH": d + (os.pathsep + existing if existing else "")}):
            yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)
