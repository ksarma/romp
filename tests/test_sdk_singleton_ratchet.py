#!/usr/bin/env python3
"""The suite's backend-singleton ratchet (tests/conftest.py, _sdk_singleton_restored), tested by running pytest in
a child over scratch modules that load the real kernel under this checkout's conftest, the way
tests/test_tempdir_hygiene.py's RunLeavesNothing tests the temp-root floors: each scratch case takes one of the
roads the suite takes to km._sdk_backend, and the outer test reads what the ratchet said about it.

The defect the ratchet guards (2026-09-19): kernel.py builds its SdkBackend lazily, the first km._sdk() call
constructing it over jd.STATE as it stands and caching it in km._sdk_backend for the life of the process.
tests/test_kernel.py::ViewBuilder pointed jd.STATE at a sandbox, its card builds reached km._sdk() and built the
singleton over the sandbox, and its tearDown restored jd.STATE and removed the directory without touching the
singleton; a later module's chat signature consulted that backend, whose fork_children statted the removed
registry, answered {} on the OSError and scanned no registry, so a derivation counting registry stats read 0
against 39 in a test that did nothing wrong, and only under an order that ran ViewBuilder first. The ratchet
reads the singleton before each test and after its teardown and fails the test that left a different object
there, or one over a path that is no longer a directory. Its one allowance is derived from the transition, never
from a list of test names: None before and a backend over jd.STATE with that directory present after is a
worker's lazy first build under the run root, the kernel's own design. WHICH test builds first depends on the run
(the xdist scheduler, the subset, the module order), so a name list could never be right: the census that found
ViewBuilder saw a different first builder on each of three workers. A kernel re-execution inside a test replaces
the marker function and resets the singleton, so identities are not compared for that test; a backend present
after the reload is that test's own build, and a state_dir that is not a directory is still named.

Two scratch modules, one nested run each, the cases in method order (unittest runs a class's methods
alphabetically, and each case's `before` is what the previous case left):
  A, the singleton built under the run root first:
    a. the worker's lazy first build (None before; after, a backend over jd.STATE, present) passes;
    b. ViewBuilder's fixed shape (save km._sdk_backend, sandbox jd.STATE, build, put both back, remove the
       sandbox) passes;
    c. a kernel re-execution inside the test, the singleton reset and rebuilt over jd.STATE, is not judged;
    d. a rebuild over the SAME root left in place fails: another object under an equal state_dir;
    e. ViewBuilder's original leak with the sandbox kept fails, naming the change and no gone directory;
    f. ViewBuilder's original leak with the sandbox removed fails, naming the change, the gone directory
       and the remedy.
  B, the leak as the worker's first build:
    a. None before and, after, a backend over a removed sandbox: the allowance does not cover it;
    b. a kernel re-execution that then builds over a removed sandbox: identities are not compared and the
       gone directory is still named.
  C, the first build over a sandbox that stands:
    a. None before and, after, a backend over a kept sandbox, jd.STATE elsewhere: the allowance does not
       cover it either (it asks for jd.STATE, not for any directory that exists).

Mutations of the fixture run against this module, each landed and reverted (2026-09-19): the fixture removed
(the six failing cases show PASSED with no ERROR at teardown and the three runs exit 0: 9 tests here red); the
allowance widened to any None-to-backend transition (C.a passes silently, and B.a is named for the directory
alone and not as a change: 3 red); the same-object check replaced by equality of state_dir (A.d passes silently
and run A counts two errors, not three: 2 red).
"""
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from romp_load import load_source  # noqa: F401  a direct run's floor lands with this import (tests/romp_load.py)

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE any load: romp modules resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

RATCHET = "left the kernel's backend singleton (km._sdk_backend)"
REMEDY = "save km._sdk_backend before the sandbox and put it back in tearDown"
GONE = "no longer a directory"
SHARED_STATE = "left shared state changed"     # the judge fixture's text: quiet in every case here, so the ratchet's is the only red

SCRATCH_HEAD = textwrap.dedent('''\
    import os, shutil, sys, tempfile, unittest
    from pathlib import Path
    from romp_load import load_source     # the suite's loader (tests/__init__.py registers it under tests.conftest)
    os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
    os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
    os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
    os.environ.pop("ROMP_STATE_DIR", None)
    KERNEL = os.path.join(os.environ["ROMP_RATCHET_BIN"], "romp-kernel")
    km = load_source("romp_kernel", KERNEL)
    jd = km.jd

    def sandbox():
        """A state root of the test's own, hosts off: the runner's belt covers the run root only (CLAUDE.md, Testing)."""
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\\n")
        return root

    def build_over(root):
        """ViewBuilder's road to the singleton: jd.STATE at a sandbox and the lazy build reached through km._sdk()."""
        jd.STATE = root
        km._sdk_backend = None
        return km._sdk()
''')

SCRATCH_A = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_lazy_first_build_under_the_run_root_passes(self):
            assert km._sdk_backend is None
            be = km._sdk()
            assert be is not None and be.state_dir == jd.STATE and jd.STATE.is_dir()

        def test_b_a_saved_and_restored_singleton_passes(self):
            saved = (jd.STATE, km._sdk_backend)
            root = sandbox()
            assert build_over(root).state_dir == root
            jd.STATE, km._sdk_backend = saved
            shutil.rmtree(root)

        def test_c_a_kernel_reexecution_inside_the_test_is_not_judged(self):
            before = km._sdk_backend
            load_source("romp_kernel", KERNEL)
            assert km._sdk_backend is None            # the reload's module-level reset
            be = km._sdk()
            assert be is not before and be.state_dir == jd.STATE

        def test_d_a_rebuilt_singleton_over_the_same_root_fails(self):
            before = km._sdk_backend
            km._sdk_backend = None
            rebuilt = km._sdk()
            assert rebuilt is not before and rebuilt.state_dir == before.state_dir

        def test_e_the_leak_with_the_sandbox_kept_fails(self):
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved                          # the sandbox stands; the singleton stays over it

        def test_f_the_leak_with_the_sandbox_removed_fails(self):
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)
''')

SCRATCH_B = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_leak_as_the_first_build_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            root = sandbox()
            jd.STATE = root
            km._sdk()                                 # the worker's lazy first build, over the sandbox
            jd.STATE = saved
            shutil.rmtree(root)

        def test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails(self):
            load_source("romp_kernel", KERNEL)
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)
''')


SCRATCH_C = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_over_a_kept_sandbox_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            jd.STATE = sandbox()
            km._sdk()                                 # the worker's lazy first build, over a sandbox that stands
            jd.STATE = saved
''')


def nested_run(text):
    """pytest in a child over one scratch module written to a fresh directory, under this checkout's conftest
    (loaded as a plugin: the module sits outside tests/, where no conftest is discovered), verbose and with the
    all-outcomes summary, so the outer test reads each case's outcome and the ratchet's text. The child's
    environment is the precedent's (tests/test_tempdir_hygiene.py, RunLeavesNothing): a fresh TMPDIR, the
    parent's pytest variables dropped so the child records its own run, and the bin directory the scratch
    module loads the kernel from. Returns (returncode, stdout and stderr)."""
    fresh = tempfile.mkdtemp()
    case = os.path.join(fresh, "case")
    os.makedirs(case)
    path = os.path.join(case, "test_scratch.py")
    with open(path, "w") as f:
        f.write(text)
    env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1", ROMP_RATCHET_BIN=BIN)
    for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "ROMP_TESTS_SYSTEM_TMPDIR"):
        env.pop(var, None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider",
                        "-v", "-rA", "--tb=short", path],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def outcomes(out):
    """{method: set of the phase outcomes pytest printed for it} from the verbose lines: a case the ratchet
    fails shows PASSED for its call and ERROR for its teardown."""
    seen = {}
    for m, o in re.findall(r"test_scratch\.py::Cases::(test_\w+) (PASSED|FAILED|ERROR)\b", out):
        seen.setdefault(m, set()).add(o)
    return seen


def verdict(out, method):
    """The ratchet's description of what `method` left, from its message: the text between the nodeid's
    method name and the remedy sentence; None when the ratchet said nothing about it."""
    m = re.search(r"::Cases::%s %s (.*?)\. A test that reaches km\._sdk\(\)" % (re.escape(method), re.escape(RATCHET)),
                  out, re.DOTALL)
    return m.group(1) if m else None


class _NestedRun:
    """The shared half of a scratch run's tests; a mixin, so the runner collects only the two runs below."""
    SCRATCH = ""
    ERRORS = 0

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out = nested_run(cls.SCRATCH)

    def assertRatchetPassed(self, method):
        self.assertEqual(outcomes(self.out).get(method), {"PASSED"}, self.out)
        self.assertIsNone(verdict(self.out, method), self.out)

    def assertRatchetFailed(self, method):
        got = outcomes(self.out).get(method, set())
        self.assertIn("PASSED", got, "the case's own asserts held; the ratchet is the only red: %s" % self.out)
        self.assertIn("ERROR", got, "the ratchet fails the case at its teardown: %s" % self.out)
        self.assertNotIn("FAILED", got, self.out)
        text = verdict(self.out, method)
        self.assertIsNotNone(text, "the ratchet's message names the case's nodeid: %s" % self.out)
        self.assertIn(REMEDY, self.out)
        return text

    def test_the_judge_fixture_is_quiet_and_the_run_reds_only_on_the_ratchet(self):
        self.assertNotEqual(self.rc, 0, self.out)
        self.assertNotIn(SHARED_STATE, self.out, "every case puts jd.STATE back; the ratchet's text is the only red")
        self.assertRegex(self.out, r"\d+ passed, %d errors? in" % self.ERRORS, self.out)


class LeakAfterFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_A
    ERRORS = 3

    def test_the_lazy_first_build_under_the_run_root_passes(self):
        self.assertRatchetPassed("test_a_the_lazy_first_build_under_the_run_root_passes")

    def test_a_saved_and_restored_singleton_passes(self):
        self.assertRatchetPassed("test_b_a_saved_and_restored_singleton_passes")

    def test_a_kernel_reexecution_inside_the_test_is_not_judged(self):
        self.assertRatchetPassed("test_c_a_kernel_reexecution_inside_the_test_is_not_judged")

    def test_a_rebuilt_singleton_over_the_same_root_is_a_change(self):
        text = self.assertRatchetFailed("test_d_a_rebuilt_singleton_over_the_same_root_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after SdkBackend over ", text)
        before, after = re.findall(r"SdkBackend over ([^\s,]+)", text)
        self.assertEqual(before, after, "the same root under both objects: identity, not the path, is the check")
        self.assertNotIn(GONE, text)

    def test_the_leak_with_the_sandbox_kept_names_the_change_and_no_gone_directory(self):
        text = self.assertRatchetFailed("test_e_the_leak_with_the_sandbox_kept_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_leak_with_the_sandbox_removed_names_the_change_the_gone_directory_and_the_remedy(self):
        text = self.assertRatchetFailed("test_f_the_leak_with_the_sandbox_removed_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", whose state_dir is no longer a directory"), text)


class LeakAsFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_B
    ERRORS = 2

    def test_the_leak_as_the_first_build_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("test_a_the_leak_as_the_first_build_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", whose state_dir is no longer a directory"), text)

    def test_a_reexecution_that_builds_over_a_removed_sandbox_is_named_for_the_directory_alone(self):
        text = self.assertRatchetFailed("test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails")
        self.assertTrue(text.startswith("over a directory that no longer exists: SdkBackend over "), text)
        self.assertNotIn("changed", text)


class FirstBuildOverAKeptSandbox(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_C
    ERRORS = 1

    def test_the_first_build_over_a_kept_sandbox_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("test_a_the_first_build_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)


if __name__ == "__main__":
    unittest.main()
