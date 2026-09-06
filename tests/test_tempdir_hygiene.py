"""The suite removes every temp directory it makes (tests/__init__.py + tests/conftest.py, 2026-09-06).

Three checks. In-process: the package's mkdtemp hook is installed, so a directory a test makes is
recorded for the exit sweep. Two subprocess checks run this same module's in-process test as a child,
once under pytest (conftest's session-end sweep) and once under unittest (the package's atexit sweep),
with ROMP_HYGIENE_MARKER naming a file where the child writes the directory it made and its
XDG_STATE_HOME root; the parent asserts both are gone once the child exits. That is the behaviour
that ends the leak (over a million stale fixture directories on one machine before this)."""
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER_ENV = "ROMP_HYGIENE_MARKER"


class Hygiene(unittest.TestCase):
    def test_mkdtemp_is_tracked_in_process(self):
        self.assertTrue(getattr(tempfile.mkdtemp, "romp_tracked", False),
                        "the tests package's mkdtemp hook is not installed")
        marker = os.environ.get(MARKER_ENV)
        if marker:                                   # child mode: leave the evidence the parent checks
            d = tempfile.mkdtemp(prefix="romp-hygiene-child-")
            self.assertTrue(os.path.isdir(d))
            with open(marker, "w") as fh:
                fh.write(d + "\n" + os.environ["XDG_STATE_HOME"] + "\n")

    def _run_child(self, argv):
        scratch = tempfile.mkdtemp(prefix="romp-hygiene-")      # tracked: swept when THIS session ends
        marker = os.path.join(scratch, "paths.txt")
        env = dict(os.environ, **{MARKER_ENV: marker})
        r = subprocess.run(argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(marker) as fh:
            made, state_root = fh.read().split("\n")[:2]
        self.assertTrue(made and state_root, "the child left no evidence")
        self.assertFalse(os.path.exists(made), "the child's mkdtemp directory survived: " + made)
        self.assertFalse(os.path.exists(state_root), "the child's state root survived: " + state_root)

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_pytest_child_session_removes_its_dirs_and_state_root(self):
        self._run_child([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                         "tests/test_tempdir_hygiene.py::Hygiene::test_mkdtemp_is_tracked_in_process"])

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_unittest_child_run_removes_its_dirs_and_state_root(self):
        self._run_child([sys.executable, "-m", "unittest", "-q",
                         "tests.test_tempdir_hygiene.Hygiene.test_mkdtemp_is_tracked_in_process"])


if __name__ == "__main__":
    unittest.main()
