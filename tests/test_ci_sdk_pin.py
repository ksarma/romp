#!/usr/bin/env python3
"""CI installs the Claude Agent SDK at the session host's tested version (.github/workflows/ci.yml, 2026-09-20).

The 48 SDK-gated tests (43 in tests/test_sdk_backend.py, 5 in tests/test_host_transport.py) and the two SDK-transport
host tests in tests/test_session_host.py skipped in every CI cell, because no cell installed the SDK; the box that runs
the hosted sessions was the only place they ran. Now the Python job's "Install the Claude Agent SDK" step installs
`claude-agent-sdk==<pin>`, where the pin is read at run time from kernel/session_host.py's SDK_TESTED_VERSION, the
repo's one declaration of the version the host's private imports were verified against (bin/romp-sdk-setup reads the
same line with the same sed). The number appears nowhere in the workflow.

This module holds four things, and it never skips: a pin that skips reports green having checked nothing.
1. Source pins on the step (no YAML library in the test deps, as tests/test_ci_bats_bound.py): it sits between
   "Install cryptography" and "Run pytest", carries no continue-on-error (the SDK requires cryptography through mcp's
   pyjwt[crypto]; a lagging cryptography wheel must red the cell, not skip 48 tests), carries no `if:` (the 3.14t cell
   installs it too: install, import with the GIL off and the gated and host test modules ran green on a free-threaded
   3.14.6 before this landed, the Verify 3.14t stage of 2026-09-20), names the constant and its file, and carries no
   literal `claude-agent-sdk==<digits>`, and bounds its download with a step timeout as the file's other fetching
   steps do; and the "Run pytest" line passes `-p no:anyio`: the constant pins the SDK alone, its dependency closure
   resolves fresh on every run (26 packages on 2026-09-20, the 3.12 cell of run 35518107329), and one of them, anyio,
   registers a pytest plugin that every cell would otherwise auto-load across the whole suite, which the box's default
   run never does and tests/README.md's PYTHONPATH recipe would, so the recipe passes the same flag (the step's
   comment states the decision, why, and the measurement behind it). The pin below does not
   catch a bad transitive release: a red that no commit explains is one, and the comment says so.
2. The derivation, executed rather than read: the step's own sed run at the repo root prints one well-formed version
   equal to the constant read as a regex over the file (the installer's and the bats test's read) and as the attribute
   of the loaded module (the host's read); and the step's whole run block, run under bash with a `python` shim in a
   scratch checkout, hands pip exactly `claude-agent-sdk==<pin>` against the real file, then imports the package in
   the same `python` (the step reds, with its name on it, when the install did not reach the interpreter on PATH; the
   shim case where that import exits 1 shows the block exits 1), and exits 1 without calling pip when the constant is
   missing, malformed (a token that is not x.y.z: the case reads "latest", and the refusal names it, where a guard
   loosened to any non-blank token would hand pip the unpinned latest) or duplicated. The composition is pinned, not
   the halves.
3. The installed version, on whichever road this interpreter is on. When claude_agent_sdk imports, the version the
   host would run (installed_sdk_version: the module's __version__, else the metadata) and the metadata both equal the
   pin; the failure message names the two roads that disagree here: a box whose SDK venv moved (re-run
   bin/romp-sdk-setup, which installs the tested version) or a CI cell whose install disagreed with the constant. When
   the SDK does not import (a plain venv), the same test asserts the pin's presence and form and WARNS (warnings.warn,
   which pytest lists in its summary under -q; a print is captured and shows only under -s or -rA) that the equality is
   not checked on this road; under ROMP_SDK_REQUIRE=1, which the workflow's Run pytest step sets (a source pin holds it
   there; the file's precedent is ROMP_SERVED_TESTS_REQUIRE), the same road is a FAILURE naming the interpreter: the
   run declared that its interpreter has the SDK the step above installed, and one without it is a cell whose SDK
   checks are all silently on the no-SDK road. The switch, not GITHUB_ACTIONS: a platform variable infers the
   requirement, the switch declares it, and a future CI step that runs pytest without the SDK on purpose (the
   served-page step installs none today) would red for the wrong reason under the former. Off the switch a box's bare
   road warns and never fails. So a box's full run and a CI cell both go red the moment the installed SDK and
   the constant disagree, and the bump stays the act the constant's comment describes: install the new version, run the
   host tests on it, move the number. The residual is stated here because nothing else states it: nothing polls PyPI,
   a person notices a release; the trigger for the bump is a red from this module on a box whose venv moved or a red
   cell on a release that the pin refuses.
4. The proof that this module cannot skip. The property is the OUTCOME, not a spelling: tests/conftest.py lists this
   file in _NEVER_SKIP_FILES and reports any skipped test report or skipped collection report for it as a failure
   carrying the skip's own reason, always, with no switch. NeverSkips proves that belt by execution, running pytest in
   a child over scratch files: a file of this name whose tests skip by every spelling (pytest.mark.skipif,
   unittest.skipIf, self.skipTest, SkipTest in setUpClass, an xfail) reds on each; one whose module level runs
   pytest.importorskip reds as a collection error; a plain-named twin of the first keeps skipping. Until 2026-09-20 the
   guard was a five-name list of unittest spellings read from this file's AST, which pytest.mark.skipif passed, and
   which a module-level importorskip removed from the run along with the rest of the module. What a report cannot
   show is a test that was never collected: renamed off the test_ prefix, deleted, or fenced behind an if, it reports
   nothing to flip and the module reads green with the version equality never checked (20 passed, exit 0, in CI's
   shape on a venv without the SDK, with InstalledVersion's method renamed). NeverSkips' census case closes that road
   for the one test the belt exists for: unittest's loader, which is pytest's collection of a TestCase, must find
   InstalledVersion's single test under its name.

Hermetic: the run block executes in a scratch directory with its own copy of the constant's line, never at the repo
root, and its `python` is a shim that records its arguments; no network, no pip.
"""
import importlib.metadata
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
HOST = os.path.join(ROOT, "kernel", "session_host.py")
# Hermetic state BEFORE the load: the host module resolves paths at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise reads REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sh = load_source("romp_session_host_ci_pin", HOST)   # a private copy: this module reads one attribute of it

STEP = "Install the Claude Agent SDK"
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CONSTANT_RE = re.compile(r'^SDK_TESTED_VERSION = "([^"]*)"', re.M)    # the installer's and the bats test's read
SED_RE = re.compile(r"sed -n '([^']+)' kernel/session_host\.py")


def python_job():
    src = open(WF).read()
    m = re.search(r"^  python:\n((?:    .*\n|\n)+?)(?=^  [a-z-]+:\n)", src, re.M)
    assert m, "the python job moved: re-anchor this pin"
    return m.group(1)


def step_block(job, name):
    """The lines of the step named `name`: from its `- name:` line to the next step's."""
    m = re.search(r"^      - name: %s\n((?:        .*\n)+)" % re.escape(name), job, re.M)
    return m.group(1) if m else None


def run_block(step):
    """The `run: |` block of a step, dedented to the shell's own text."""
    m = re.search(r"^        run: \|\n((?:          .*\n)+)", step, re.M)
    assert m, "the step's run block is not a `run: |` literal: re-anchor this pin"
    return "".join(line[10:] for line in m.group(1).splitlines(keepends=True))


class InstallStep(unittest.TestCase):
    def setUp(self):
        self.job = python_job()
        self.step = step_block(self.job, STEP)
        self.assertTrue(self.step, "no step named %r in the python job: the 48 SDK-gated tests skip in every cell again" % STEP)
        self.block = run_block(self.step)      # not self.run: that name is unittest.TestCase.run on the instance
        self.comment = " ".join(l.strip()[1:].strip() for l in self.step.splitlines() if l.strip().startswith("#"))

    def test_the_step_sits_between_cryptography_and_pytest(self):
        names = re.findall(r"^      - name: (.*)$", self.job, re.M)
        self.assertIn("Install cryptography", names)
        self.assertIn("Run pytest", names)
        self.assertLess(names.index("Install cryptography"), names.index(STEP),
                        "the SDK step must follow the cryptography step so pip finds cryptography installed")
        self.assertLess(names.index(STEP), names.index("Run pytest"), "the SDK step must precede the test run")

    def test_the_step_carries_no_continue_on_error(self):
        # the SDK requires cryptography (mcp's pyjwt[crypto]): a lagging wheel must be the cell's red, not 48 silent skips
        self.assertFalse(re.search(r"^        continue-on-error:", self.step, re.M),
                         "the step continues on error: a failed install would run the cell with 48 tests silently skipping")

    def test_the_step_runs_on_every_cell_including_3_14t(self):
        # the Verify 3.14t stage (2026-09-20): install, import with the GIL off, gated and host modules green under a
        # free-threaded 3.14.6, so the step has no `if:` and the comment says the cell installs it too. A future release
        # that breaks there shows as a red cell; excluding the cell would turn that into 50 silent skips.
        self.assertFalse(re.search(r"^        if:", self.step, re.M), "the step is gated by an if: clause; the 3.14t decision was INCLUDE")
        self.assertIn("3.14t cell installs it too", self.comment, "the comment no longer states the 3.14t decision")

    def test_the_step_bounds_its_download_with_a_step_timeout(self):
        # the file's convention for a step that fetches (bats, gitleaks, Playwright): a wedged download of the 102 MB
        # wheel fails in minutes with the step named, instead of eating the job's cap and dying nameless
        m = re.search(r"^        timeout-minutes: (\d+)$", self.step, re.M)
        self.assertTrue(m, "the step has no timeout-minutes: a wedged download would eat the job's cap")
        self.assertLessEqual(int(m.group(1)), 10, "the step timeout is a bound on a download, not a second job cap")

    def test_the_run_block_reads_the_constant_from_the_host_module(self):
        self.assertIn("SDK_TESTED_VERSION", self.block)
        self.assertIn("kernel/session_host.py", self.block)
        self.assertTrue(SED_RE.search(self.block), "the run block does not read the constant with a sed over kernel/session_host.py")
        self.assertRegex(self.block, r'pip install "claude-agent-sdk==\$pin"')

    def test_the_run_block_carries_no_literal_version(self):
        # one declaration: a literal here would be a second copy that a bump could leave behind
        self.assertFalse(re.search(r"claude-agent-sdk==\d", self.block), "the run block pins a literal version: read SDK_TESTED_VERSION instead")
        self.assertFalse(re.search(r"\b\d+\.\d+\.\d+\b", self.block), "the run block carries a version number: the constant is the one declaration")

    def test_the_run_block_checks_the_import_in_the_interpreter_it_installed_into(self):
        # correctness: pip and pytest share `python` on PATH, and the import in that same `python` is the step's own
        # check that the install reached it; without it an install into another interpreter is 48 skips and a warning
        lines = self.block.splitlines()
        pip = [i for i, l in enumerate(lines) if re.match(r'^python -m pip install "claude-agent-sdk==\$pin"$', l)]
        imp = [i for i, l in enumerate(lines) if l == 'python -c "import claude_agent_sdk"']
        self.assertEqual(len(pip), 1, "the run block's pip line moved: %r" % lines)
        self.assertEqual(len(imp), 1, "the run block does not import claude_agent_sdk after installing it: %r" % lines)
        self.assertLess(pip[0], imp[0], "the import must follow the install")

    def test_the_pytest_step_requires_the_sdk_the_step_installed(self):
        # the run declares that its interpreter has the SDK: tests/test_ci_sdk_pin.py's InstalledVersion fails rather
        # than warns on an interpreter without it, and tests/test_session_host.py's host case asserts the host a test
        # spawns imports it (the stance of ROMP_SERVED_TESTS_REQUIRE in this file)
        step = step_block(self.job, "Run pytest")
        self.assertTrue(step, "no step named 'Run pytest' in the python job: re-anchor this pin")
        self.assertTrue(re.search(r'^          ROMP_SDK_REQUIRE: "1"$', step, re.M),
                        "the Run pytest step does not set ROMP_SDK_REQUIRE=1: a cell whose interpreter lost the SDK reads green")

    def test_the_comment_states_the_pin_source_the_bump_and_the_residual(self):
        # "pytest plugin" and "transitive release" (2026-09-20): the constant pins the SDK alone and its dependency closure
        # resolves fresh on every run; one of those packages, anyio, registers a pytest plugin, and a comment that stops
        # saying so lets the pytest environment change again without a word (the line below holds the block itself)
        for phrase in ("SDK_TESTED_VERSION", "kernel/session_host.py", "bin/romp-sdk-setup", "not PyPI's latest",
                       "run the host tests on it, move the number", "nothing polls PyPI", "continue-on-error", "cryptography",
                       "pytest plugin", "transitive release"):
            self.assertIn(phrase, self.comment, "the step's comment lost the sentence about %r" % phrase)

    def test_the_pytest_step_blocks_the_plugin_the_sdk_closure_carries(self):
        # anyio, in the SDK's dependency closure, registers a pytest11 entry point: without the flag every cell's pytest
        # auto-loads a plugin the box's pytest never sees (the box venvs carry no anyio, and romp's SDK venv joins sys.path
        # after plugin autoload). The step's comment above states the decision and its measurement; this pin holds the flag.
        step = step_block(self.job, "Run pytest")
        self.assertTrue(step, "no step named 'Run pytest' in the python job: re-anchor this pin")
        m = re.search(r"^        run: (python -m pytest .*)$", step, re.M)
        self.assertTrue(m, "the Run pytest step's run line moved: re-anchor this pin")
        self.assertIn(" -p no:anyio", m.group(1),
                      "the Run pytest line does not pass -p no:anyio: every cell auto-loads anyio's pytest plugin across the whole suite")


class PinDerivation(unittest.TestCase):
    """The workflow's read of the constant equals the installer's read and the host's own attribute, shown by running it."""
    def setUp(self):
        self.block = run_block(step_block(python_job(), STEP) or "")
        self.expr = SED_RE.search(self.block).group(1)

    def test_the_constant_is_declared_exactly_once_and_well_formed(self):
        found = CONSTANT_RE.findall(open(HOST).read())
        self.assertEqual(len(found), 1, "kernel/session_host.py must declare SDK_TESTED_VERSION on exactly one line; found %d" % len(found))
        self.assertRegex(found[0], VERSION_RE, "SDK_TESTED_VERSION is not a bare x.y.z version")
        self.assertEqual(found[0], sh.SDK_TESTED_VERSION, "the regex read and the module attribute disagree")

    def test_the_steps_sed_run_at_the_root_prints_the_constant(self):
        out = subprocess.run(["sed", "-n", self.expr, "kernel/session_host.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        lines = out.splitlines()
        self.assertEqual(len(lines), 1, "the step's sed printed %d lines over kernel/session_host.py, not one: %r" % (len(lines), out))
        self.assertRegex(lines[0], VERSION_RE, "the step's sed printed something other than a version: %r" % lines[0])
        self.assertEqual(lines[0], sh.SDK_TESTED_VERSION, "the workflow would install %s; the host is written against %s" % (lines[0], sh.SDK_TESTED_VERSION))

    def _run_block(self, constant_lines, import_fails=False):
        """The step's run block under bash in a scratch checkout whose kernel/session_host.py holds `constant_lines`,
        with a `python` shim that records its arguments and installs nothing; with `import_fails` the shim exits 1 on
        `-c`, the interpreter whose import of the package the block runs after pip."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        os.makedirs(os.path.join(tmp, "kernel"))
        with open(os.path.join(tmp, "kernel", "session_host.py"), "w") as f:
            f.write("# a scratch copy of the constant's line for the step's sed\n" + constant_lines)
        shim = os.path.join(tmp, "bin")
        os.makedirs(shim)
        calls = os.path.join(tmp, "python-calls")
        with open(os.path.join(shim, "python"), "w") as f:
            f.write('#!/bin/sh\nprintf "%s\\n" "$*" >> "' + calls + '"\n' + ('if [ "$1" = -c ]; then exit 1; fi\n' if import_fails else ''))
        os.chmod(os.path.join(shim, "python"), 0o755)
        env = dict(os.environ, PATH=shim + os.pathsep + os.environ.get("PATH", ""))
        p = subprocess.run(["bash", "-c", self.block], cwd=tmp, env=env, capture_output=True, text=True)
        recorded = open(calls).read().splitlines() if os.path.exists(calls) else []
        return p, recorded

    def test_the_run_block_hands_pip_exactly_the_pinned_requirement_then_imports_the_package(self):
        p, calls = self._run_block('SDK_TESTED_VERSION = "%s"\n' % sh.SDK_TESTED_VERSION)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(calls, ["-m pip install claude-agent-sdk==%s" % sh.SDK_TESTED_VERSION, "-c import claude_agent_sdk"])

    def test_the_run_block_fails_when_the_interpreter_it_installed_into_cannot_import_the_package(self):
        # the import is load-bearing: a block that ran pip and stopped would exit 0 here
        p, calls = self._run_block('SDK_TESTED_VERSION = "%s"\n' % sh.SDK_TESTED_VERSION, import_fails=True)
        self.assertEqual(p.returncode, 1, "the block must fail when its own interpreter cannot import what pip installed: %r" % p.stderr)
        self.assertEqual(calls, ["-m pip install claude-agent-sdk==%s" % sh.SDK_TESTED_VERSION, "-c import claude_agent_sdk"])

    def test_the_run_block_refuses_a_missing_constant_without_installing(self):
        p, calls = self._run_block('SDK_DIST = "claude-agent-sdk"\n')
        self.assertEqual(p.returncode, 1, "the block must exit 1, never install the unpinned latest")
        self.assertIn("SDK_TESTED_VERSION", p.stderr)
        self.assertEqual(calls, [])

    def test_the_run_block_refuses_a_duplicated_constant_without_installing(self):
        p, calls = self._run_block('SDK_TESTED_VERSION = "0.2.1"\nSDK_TESTED_VERSION = "0.2.2"\n')
        self.assertEqual(p.returncode, 1, "two declarations are not one pin; the block must refuse")
        self.assertEqual(calls, [])

    def test_the_run_block_refuses_a_malformed_constant_without_installing(self):
        # one well-formed line is the guard's whole acceptance: a token that is not x.y.z (a channel name, a
        # range, a prerelease) must be named in the refusal and never reach pip, where "latest" would resolve
        p, calls = self._run_block('SDK_TESTED_VERSION = "latest"\n')
        self.assertEqual(p.returncode, 1, "a constant that is not x.y.z must be refused, never handed to pip: %r" % p.stderr)
        self.assertIn("latest", p.stderr, "the refusal must name what it read")
        self.assertEqual(calls, [])


class InstalledVersion(unittest.TestCase):
    """The SDK this interpreter imports is the pinned version, on the road where it imports; the pin's form on the other.

    Never a skip. In CI every cell installs the pin, so every cell takes the first road. On a box the full suite takes it
    in every worker where tests/test_host_transport.py has put the SDK venv's site on sys.path before this module ran,
    so a venv that moved past the constant (or a constant moved past the venv) reds there before a hosted session finds
    out; a worker on the other road checks the form and warns that it checked no more (a warning, because pytest prints
    the warnings summary under -q where a captured print never shows; no filter in the repo turns a UserWarning into an
    error). Under ROMP_SDK_REQUIRE=1 the other road is a failure, not a warning: the run declared that the interpreter
    running pytest has the SDK the install step put there (the workflow's Run pytest step sets the switch, and a source
    pin in InstallStep holds it), so an interpreter without it is a cell whose SDK checks are all silently on the no-SDK
    road. Off the switch, a box's bare road warns and never fails."""
    def test_the_installed_sdk_is_the_pin_where_it_imports_and_the_pin_is_well_formed_where_it_does_not(self):
        pin = sh.SDK_TESTED_VERSION
        self.assertRegex(pin, VERSION_RE, "SDK_TESTED_VERSION is not a bare x.y.z version: %r" % pin)
        try:
            spec = importlib.util.find_spec(sh.SDK_PACKAGE)
        except ValueError as e:
            # a fixture's stand-in module left in sys.modules has no __spec__, and find_spec raises rather than answers:
            # name the leak, which is a test-hygiene fault, not a pin verdict
            self.fail("sys.modules holds a %s that is not an installed package (%r: %s); a fixture's fake SDK leaked into "
                      "this process, so the pin cannot be judged here" % (sh.SDK_PACKAGE, sys.modules.get(sh.SDK_PACKAGE), e))
        if spec is None:
            # Where the run requires the SDK (ROMP_SDK_REQUIRE=1, set by the workflow's Run pytest step after the install
            # step put the pin into `python`), this road is a cell that lost the SDK between the step and pytest (an
            # install into another interpreter, a PYTHONPATH leak in the runner), and every SDK check in the run is
            # then reading the no-SDK road: the gated tests skip, the no-SDK controls pass on the pipe transport, and a
            # warning would be the only trace. That is a failure (2026-09-20). Off the switch, a box's bare road is
            # ordinary and the warning says what was not checked.
            if os.environ.get("ROMP_SDK_REQUIRE") == "1":
                self.fail("ROMP_SDK_REQUIRE=1: this run requires the SDK, and claude_agent_sdk does not import in the "
                          "interpreter running pytest (%s): the pinned version was not checked and the SDK-gated tests "
                          "are skipping in this run" % sys.executable)
            warnings.warn("claude_agent_sdk does not import in this interpreter (%s): the pin's form is checked, the installed "
                          "version is not; under ROMP_SDK_REQUIRE=1, which CI's pytest step sets, this road is a failure"
                          % sys.executable)
            return
        installed = sh.installed_sdk_version()
        try:
            metadata = importlib.metadata.version(sh.SDK_DIST)
        except importlib.metadata.PackageNotFoundError:
            metadata = None
        mod = importlib.import_module(sh.SDK_PACKAGE)
        where = os.path.dirname(getattr(mod, "__file__", "") or "")
        disagree = ("claude_agent_sdk imports at %s (metadata %s, from %s) but kernel/session_host.py is written against "
                    "SDK_TESTED_VERSION = %s. One of two roads disagrees: this machine's SDK venv moved (re-run "
                    "bin/romp-sdk-setup, which installs the tested version), or a CI cell's install step disagreed with the "
                    "constant. To move the pin: install the new version, run the host tests on it, then move the constant."
                    % (installed, metadata, where, pin))
        self.assertEqual(installed, pin, disagree)
        self.assertEqual(metadata, pin, disagree)


SKIP_SPELLINGS = '''
import unittest
import pytest
class Marked(unittest.TestCase):
    @pytest.mark.skipif(True, reason="synthetic skipif spelling")
    def test_skipif(self):
        pass
    @unittest.skipIf(True, "synthetic unittest.skipIf spelling")
    def test_unittest_skipif(self):
        pass
    @pytest.mark.xfail(reason="synthetic xfail spelling")
    def test_xfail(self):
        self.fail("an xfail absorbs this")
class InBody(unittest.TestCase):
    def test_skiptest(self):
        self.skipTest("synthetic skipTest spelling")
class InSetUpClass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raise unittest.SkipTest("synthetic SkipTest in setUpClass")
    def test_never_reached(self):
        pass
'''
MODULE_LEVEL_SKIP = '''
import unittest
import pytest
pytest.importorskip("no_such_module_synthetic_xyz")
class Unreachable(unittest.TestCase):
    def test_never_collected(self):
        pass
'''


class NeverSkips(unittest.TestCase):
    """The never-skips belt in tests/conftest.py (_NEVER_SKIP_FILES), proved by execution the way
    tests/test_served_tests_require.py proves the served-tests switch: pytest in a child, tests/conftest.py loaded as a
    plugin, over scratch files in a temp directory. A scratch file of THIS module's name carries five skip spellings
    (two the old five-name list never covered, pytest.mark.skipif and an xfail; three it did) and every one is red,
    each naming the belt and quoting its reason; the same content under a plain name skips as pytest always let it;
    a scratch file of this name whose module level runs pytest.importorskip, which collects no items, is a collection
    error and the run stops red. Synthetic files only; no SDK, no network. The census case is in-process: the belt
    reads reports, and a test that is never collected files none, so the one test the belt exists for is pinned by
    name against unittest's loader, the collection pytest performs on a TestCase. The children pass -p no:anyio as the
    workflow's pytest step does, so in a cell they run with the step's plugin set rather than the interpreter's default
    (pytest accepts the flag where anyio is absent, as on the box venvs)."""
    INSTALLED_VERSION_TEST = "test_the_installed_sdk_is_the_pin_where_it_imports_and_the_pin_is_well_formed_where_it_does_not"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="never-skips-")
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def _write(self, name, body):
        path = os.path.join(self.d, name)
        with open(path, "w") as f:
            f.write(body)
        return path

    def _run(self, *paths):
        p = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-p", "no:anyio", "-q", "-rs", *paths],
                           cwd=ROOT, env=dict(os.environ), capture_output=True, text=True, timeout=240)
        return p.returncode, p.stdout + p.stderr

    def test_every_skip_spelling_in_a_file_of_this_name_is_red_and_a_plain_twin_still_skips(self):
        rc, out = self._run(self._write("test_ci_sdk_pin.py", SKIP_SPELLINGS), self._write("test_fake_plain.py", SKIP_SPELLINGS))
        self.assertNotEqual(rc, 0, "a skip in a file of this name must fail the run: " + out[-3000:])
        # the listed file: a setup-phase skip (skipif, SkipTest in setUpClass) is filed as an error, a body skip and the
        # xfail as failures; the plain twin: four skips and one xfail, as pytest reports them without the belt
        self.assertIn("3 failed, 4 skipped, 1 xfailed, 2 errors", out, out[-3000:])
        self.assertEqual(out.count("never-skips: test_ci_sdk_pin.py skipped"), 5, "each red names the belt and the file: " + out[-3000:])
        for reason in ("synthetic skipif spelling", "synthetic unittest.skipIf spelling", "synthetic skipTest spelling",
                       "synthetic SkipTest in setUpClass", "xfail: synthetic xfail spelling"):
            self.assertIn("_NEVER_SKIP_FILES): %s" % reason, out.replace("_NEVER_SKIP_FILES): Skipped: ", "_NEVER_SKIP_FILES): "),
                          "the red carries the skip's own reason (%s): %s" % (reason, out[-3000:]))
        self.assertNotIn("never-skips: test_fake_plain.py", out, "the belt reaches only the listed file: " + out[-3000:])
        self.assertIn("test_fake_plain.py", out.split("short test summary info")[-1], "the plain twin's skips are reported as skips: " + out[-3000:])

    def test_a_module_level_importorskip_in_a_file_of_this_name_is_a_collection_error(self):
        rc, out = self._run(self._write("test_ci_sdk_pin.py", MODULE_LEVEL_SKIP))
        self.assertNotEqual(rc, 0, "a module that skips whole collects nothing and must still red the run: " + out[-3000:])
        self.assertIn("1 error during collection", out, out[-3000:])
        self.assertIn("never-skips: test_ci_sdk_pin.py skipped (at collection)", out, out[-3000:])
        self.assertIn("no_such_module_synthetic_xyz", out, "the collection error carries the skip's own reason: " + out[-3000:])
        self.assertNotIn("skipped", out.split("short test summary info")[-1].replace("never-skips: test_ci_sdk_pin.py skipped", ""),
                         "nothing in the run is reported as a skip: " + out[-3000:])

    def test_a_module_level_importorskip_under_a_plain_name_still_skips_the_module(self):
        rc, out = self._run(self._write("test_fake_plain.py", MODULE_LEVEL_SKIP))
        self.assertEqual(rc, 5, "no tests collected, nothing red: the belt reaches only the listed file: " + out[-3000:])
        self.assertIn("1 skipped", out, out[-3000:])
        self.assertNotIn("never-skips:", out, "the belt did not fire: " + out[-3000:])   # the colon: the scratch dir is named never-skips-

    def test_the_test_the_belt_exists_for_is_collected_under_its_name(self):
        # the belt flips skipped REPORTS; a test that is never collected (renamed off the test_ prefix, deleted, fenced
        # behind an if) reports nothing, and the module read 20 passed, exit 0, in CI's shape on a venv without the SDK
        # with this method renamed (2026-09-20). unittest's loader over the class is the collection pytest performs on
        # a TestCase: exactly one test, under this name.
        self.assertEqual(unittest.defaultTestLoader.getTestCaseNames(InstalledVersion), [self.INSTALLED_VERSION_TEST],
                         "InstalledVersion's test is not collected under its name: the pin the belt guards is not in the run")


if __name__ == "__main__":
    unittest.main()
