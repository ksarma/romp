#!/usr/bin/env python3
"""ROMP_SERVED_TESTS_REQUIRE=1 turns a skip inside a browser-backed served-page test file into a failure (T308,
2026-09-10). The files tests/test_*_browser.py and tests/test_*_served.py boot a hermetic kernel and drive the real
dashboard pages in playwright's Chromium; without the extension's node deps or a browser they skip, and say why. CI's
Python jobs are such machines, so a served-page regression never turned them red (the deep-link landing pin, T307,
red on main for a day while CI stayed green). The extension job installs that browser and runs these files with the
switch set, the stance the pane bench takes with ROMP_UI_BENCH_REQUIRE: a runner that cannot run them fails, loudly,
with the skip's own reason, rather than passing with the coverage gone.

Pinned here by running pytest in a child on three synthetic files outside tests/ (tests/conftest.py loaded as a
plugin with -p, the way it would load for files under tests/): a served-named file whose class skips in setUpClass
and a plain-named file that skips the same way, run together; and a second served-named file whose ONLY skip is an
xfail, run alone. Off, the pair's four skips stay skips. On, the served file's two skips become red, each with its
reason quoted (a skip raised in setUpClass is a setup-phase report, which pytest counts as an error; one raised in
the test body counts as a failure; both turn the run red), a skip whose reason begins with "optional:" stays a skip
(a leg the runner declared it does not carry), and the plain file's still skips: the switch reaches only the files
it names. The xfail-only file runs alone because the exit STATUS is its assertion: pytest records an xfail as a
skipped report carrying a `wasxfail` attribute, prints FAILED for the flipped report either way, and counts it
toward the exit status only once that attribute is gone (tests/conftest.py, _fail_skipped_report, the flip the
served switch and the never-skips belt share); beside the pair's other skips, whose flips already make the run
non-zero, that exit would be carried for it and the case would prove nothing. Red before the flip was shared: the
switch flipped the outcome and left the attribute, so the child printed "1 failed" and exited 0 (2026-09-21). Off,
the same file is one xfailed test and exit 0. Synthetic fixtures only; no browser, no kernel, no network.

This module also holds the existence half of the never-skips belt's subject check (tests/conftest.py,
_NEVER_SKIP_FILES; NeverSkipFilesExist below), placed here because it must live OUTSIDE the module that belt guards:
every entry in the tuple, read from the conftest's text as written, names a file under tests/, and the tuple is not
empty. The membership half, that the guarded module's own basename is in the tuple, is NeverSkips' in
tests/test_ci_sdk_pin.py; a check inside that module cannot fire once the file is deleted, and this one does. Before
the pair (2026-09-21) a stale second entry and a module renamed test_ci_sdk_pin_v2.py both read green, the belt inert.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.conftest import never_skip_files_as_written

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

SERVED = '''
import unittest
class ServedClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise unittest.SkipTest("no browser on this synthetic box")
    def test_lands(self):
        pass
class ServedMethod(unittest.TestCase):
    def test_drives(self):
        self.skipTest("no playwright browser here, synthetic")
class ServedOptional(unittest.TestCase):
    def test_other_engine(self):
        self.skipTest("optional: this synthetic runner declares no webkit")
'''
PLAIN = '''
import unittest
class Plain(unittest.TestCase):
    def test_something(self):
        self.skipTest("a plain skip stays a skip")
'''
# The file's ONLY skip is an xfail: run alone, so nothing but the flipped xfail can carry the run's exit status.
SERVED_XFAIL_ONLY = '''
import unittest
import pytest
class ServedXfail(unittest.TestCase):
    @pytest.mark.xfail(reason="synthetic xfail, the file's only skip")
    def test_xfail(self):
        self.fail("an xfail absorbs this")
'''


class ServedTestsRequire(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="served-require-")
        for name, body in (("test_fake_served.py", SERVED), ("test_fake_plain.py", PLAIN), ("test_fake_xfail_served.py", SERVED_XFAIL_ONLY)):
            with open(os.path.join(self.d, name), "w") as f:
                f.write(body)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, require, names=("test_fake_served.py", "test_fake_plain.py")):
        """pytest in a child over the named scratch files (the served-and-plain pair by default); `require` sets the
        switch, else the variable is removed from the child's environment."""
        env = {k: v for k, v in os.environ.items() if k != "ROMP_SERVED_TESTS_REQUIRE"}
        if require:
            env["ROMP_SERVED_TESTS_REQUIRE"] = "1"
        p = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-p", "no:anyio", "-q", "-rs",
                            *(os.path.join(self.d, name) for name in names)],
                           cwd=REPO, env=env, capture_output=True, text=True, timeout=240)
        return p.returncode, p.stdout + p.stderr

    def test_off_all_skip_as_before(self):
        rc, out = self._run(require=False)
        self.assertEqual(rc, 0, out[-2000:])
        self.assertIn("4 skipped", out, out[-2000:])
        self.assertNotIn("failed", out, out[-2000:])
        self.assertNotIn("error", out, out[-2000:])

    def test_on_the_served_file_fails_with_the_skip_reason_and_the_plain_file_still_skips(self):
        rc, out = self._run(require=True)
        self.assertNotEqual(rc, 0, "the served skip must fail the run: " + out[-2000:])
        self.assertIn("1 failed, 2 skipped, 1 error", out, out[-2000:])
        self.assertIn("optional: this synthetic runner declares no webkit", out, "the optional leg is reported as the skip it is: " + out[-2000:])
        self.assertEqual(out.count("ROMP_SERVED_TESTS_REQUIRE=1"), 2, "each red names the switch: " + out[-2000:])
        self.assertIn("no browser on this synthetic box", out, "…and carries the skip's own reason (the class-level one): " + out[-2000:])
        self.assertIn("no playwright browser here, synthetic", out, "…and the method-level one: " + out[-2000:])
        self.assertIn("a plain skip stays a skip", out, "the plain file's skip is reported as a skip: " + out[-2000:])

    def test_on_an_xfail_that_is_the_served_files_only_skip_fails_the_run(self):
        # The exit code is the assertion, not the "1 failed" line: pytest prints FAILED for a flipped xfail whether or
        # not the report keeps its wasxfail attribute, and counts it toward the exit status only without it. Alone: the
        # pair's other skips already make the run non-zero and would carry this file's exit for it. Red before the
        # switch used the shared flip (tests/conftest.py, _fail_skipped_report): "1 failed", exit 0 (2026-09-21).
        rc, out = self._run(require=True, names=("test_fake_xfail_served.py",))
        self.assertNotEqual(rc, 0, "a flipped xfail must fail the RUN, not only print FAILED: " + out[-2000:])
        self.assertIn("1 failed", out, "the xfail is reported as the one failure: " + out[-2000:])
        self.assertIn("ROMP_SERVED_TESTS_REQUIRE=1", out, "the red names the switch: " + out[-2000:])
        self.assertIn("xfail: synthetic xfail, the file's only skip", out, "...and carries the xfail's own reason: " + out[-2000:])

    def test_off_the_served_files_only_xfail_stays_an_xfail(self):
        rc, out = self._run(require=False, names=("test_fake_xfail_served.py",))
        self.assertEqual(rc, 0, "off the switch an xfail is pytest's xfail: " + out[-2000:])
        self.assertIn("1 xfailed", out, out[-2000:])
        self.assertNotIn("ROMP_SERVED_TESTS_REQUIRE", out, "the switch's message does not appear off the switch: " + out[-2000:])


class NeverSkipFilesExist(unittest.TestCase):
    """Every file the never-skips belt names exists: the existence half of the check on tests/conftest.py's
    _NEVER_SKIP_FILES, outside the module the belt guards (the module docstring says why here). Keyed on the tuple
    as written in the conftest's text (never_skip_files_as_written: ast.literal_eval, so a tuple spelled any other way
    is reported as such rather than raising), each entry a bare basename, since the belt compares a report's file BASENAME to
    the entries, that names a file under tests/."""

    def test_every_name_the_belt_lists_is_a_file_under_tests(self):
        names = never_skip_files_as_written()
        self.assertTrue(names, "the never-skips belt names no file: an empty _NEVER_SKIP_FILES flips no report")
        not_basenames = [n for n in names if os.path.basename(n) != n]
        self.assertEqual(not_basenames, [], "the belt compares a report's file basename to each entry, so an entry with a "
                         "directory part never matches: %r" % (not_basenames,))
        missing = [n for n in names if not os.path.isfile(os.path.join(REPO, "tests", n))]
        self.assertEqual(missing, [], "an entry of _NEVER_SKIP_FILES names no file under tests/ (the module renamed or "
                         "deleted, or a stale entry): %r; as written the tuple is %r" % (missing, names))

    def test_the_reader_reports_a_tuple_not_written_as_a_literal_and_reads_one_that_is(self):
        # the reader run against what it refuses, over scratch copies of the assignment: a value ast.literal_eval
        # cannot read (a call), a literal that is not a tuple (a list), and no assignment at all each raise an
        # AssertionError that names the shape and the line; a literal tuple is returned as written
        d = tempfile.mkdtemp(prefix="never-skip-reader-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        def scratch(body):
            path = os.path.join(d, "conftest.py")
            with open(path, "w") as f:
                f.write(body)
            return path
        self.assertEqual(never_skip_files_as_written(scratch('import os\n_NEVER_SKIP_FILES = ("test_a.py", "test_b.py")\n')),
                         ("test_a.py", "test_b.py"))
        with self.assertRaisesRegex(AssertionError, r"conftest.py:2: _NEVER_SKIP_FILES is not a literal tuple \(a Call\)"):
            never_skip_files_as_written(scratch('NAMES = ["test_a.py"]\n_NEVER_SKIP_FILES = tuple(NAMES)\n'))
        with self.assertRaisesRegex(AssertionError, r"conftest.py:1: _NEVER_SKIP_FILES is a literal list, not a tuple"):
            never_skip_files_as_written(scratch('_NEVER_SKIP_FILES = ["test_a.py"]\n'))
        with self.assertRaisesRegex(AssertionError, r"assigns no _NEVER_SKIP_FILES at module level"):
            never_skip_files_as_written(scratch('def f():\n    _NEVER_SKIP_FILES = ("test_a.py",)\n'))


if __name__ == "__main__":
    unittest.main()
