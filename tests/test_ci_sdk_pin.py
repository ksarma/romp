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
   steps do. And a POPULATION CHECK over the workflow's pytest invocations (PytestPopulation, ListedInvocations and
   PopulationCheckReds below; round 3's ruling, 2026-09-20, replacing two pins on the Run pytest step's text alone):
   every command that runs pytest in ci.yml passes `-p no:anyio`, and either sets ROMP_SDK_REQUIRE=1 in the environment
   GitHub Actions merges for it (the workflow's env, the job's, the step's, a VAR=value prefix on the command; later
   scopes override earlier) or is listed in SWITCH_LISTED by (job, step name) with a reason whose premises the test
   checks; an invocation that does neither is named with its job, step and file line. The population is derived from
   the file's text by pytest_invocations (its docstring is the rule: `python -m pytest`, a bare `pytest` or `py.test`
   at command position, in a named or unnamed step, in a single-line, quoted, continued, `run: |` or `run: >` scalar,
   backslash continuations joined, comment and pip lines excluded), and the two invocations the file is known to
   hold, the Python matrix step's Run pytest (the switch and the flag) and the vscode-extension job's served-page
   step (the flag; listed for the switch, since its job installs no SDK), are asserted present, so an empty read is
   red. The flag has no list: the constant pins the SDK alone, its dependency closure resolves fresh on every run (26
   packages on 2026-09-20, the 3.12 cell of run 35518107329), and one of them, anyio, registers a pytest plugin that
   every cell would otherwise auto-load across the whole suite, which the box's default run never does and
   tests/README.md's PYTHONPATH recipe would, so the recipe passes the same flag (the SDK step's comment states the
   decision, why, and the measurement behind it); pytest accepts the flag where anyio is absent, so an invocation
   whose interpreter has no anyio today (the served-page step: pip, pytest, pytest-timeout, cryptography) passes it
   too rather than carrying a reason about a pip line that a later package on that line would silently make false.
   The check reads ci.yml's text, and that is its residual: a pytest run by a script or action the workflow calls is
   outside it, as is a run line that never spells pytest; a run line that spells pytest in a form the parser does not
   read as a command (a wrapper such as `uvx pytest`, a `$PYTEST` variable, an indentation indicator on a block, a
   more-indented line in a folded block) is red as `unparsed` until the parser reads it, never green. The flag half
   keys on the spelling `-p no:anyio` with one space, the switch half on the merged value reading 1, and their
   messages say so. The pin below does not
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
   not checked on this road; under ROMP_SDK_REQUIRE=1, which the workflow's Run pytest step sets (the population check
   holds it there; the file's precedent is ROMP_SERVED_TESTS_REQUIRE), the same road is a FAILURE naming the interpreter: the
   run declared that its interpreter has the SDK the step above installed, and one without it is a cell whose SDK
   checks are all silently on the no-SDK road. The switch, not GITHUB_ACTIONS: a platform variable infers the
   requirement, the switch declares it, and a CI step that runs pytest without the SDK on purpose (the served-page
   step installs none, and the population check lists it for the switch with that reason, checked) would red for
   the wrong reason under the former. Off the switch a box's bare road warns and never fails. RequireSwitch runs
   that refusing road by execution: pytest in a child over
   InstalledVersion's class node id with tests/sdk_blocker.py's sitecustomize prepended to the PYTHONPATH it inherits,
   so the child's interpreter cannot import the SDK whichever venv runs this module; the child is red with the
   switch's message under ROMP_SDK_REQUIRE=1 and one passed test with the warning once the variable is removed from
   the environment the child inherits (before that case the fail branch was a non-red mutant: deleted, every test in
   the repo stayed green under the switch, 2026-09-20). So a box's full run and a CI cell both go red the moment the
   installed SDK and the constant disagree, and the bump stays the act the constant's comment describes: install the
   new version, run the host tests on it, move the number. The residual is stated here because nothing else states it:
   nothing polls PyPI, a person notices a release; the trigger for the bump is a red from this module on a box whose
   venv moved or a red cell on a release that the pin refuses.
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
import glob
import importlib.metadata
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from unittest import mock
from romp_load import load_source
import sdk_blocker   # noqa: E402  the shared test helper, registered by name in tests/__init__.py like romp_load

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

    def test_the_comment_states_the_pin_source_the_bump_and_the_residual(self):
        # "pytest plugin" and "transitive release" (2026-09-20): the constant pins the SDK alone and its dependency closure
        # resolves fresh on every run; one of those packages, anyio, registers a pytest plugin, and a comment that stops
        # saying so lets the pytest environment change again without a word (the line below holds the block itself)
        for phrase in ("SDK_TESTED_VERSION", "kernel/session_host.py", "bin/romp-sdk-setup", "not PyPI's latest",
                       "run the host tests on it, move the number", "nothing polls PyPI", "continue-on-error", "cryptography",
                       "pytest plugin", "transitive release"):
            self.assertIn(phrase, self.comment, "the step's comment lost the sentence about %r" % phrase)


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
    running pytest has the SDK the install step put there (the workflow's Run pytest step sets the switch, and the
    population check, PytestPopulation, holds it), so an interpreter without it is a cell whose SDK checks are all silently on the no-SDK
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


class RequireSwitch(unittest.TestCase):
    """The ROMP_SDK_REQUIRE=1 switch run against what it refuses: InstalledVersion in a child pytest whose interpreter
    cannot import the SDK. tests/sdk_blocker.py's sitecustomize, in a scratch directory PREPENDED to whatever PYTHONPATH
    the child inherits, hides an installed claude_agent_sdk (find_spec answers None for a module set to None in
    sys.modules), so the child takes the no-SDK road on a venv with the SDK as on one without. On the switch the run is
    red with the switch's own message and the FAILED line names InstalledVersion's node id; off it, with the variable
    REMOVED from the inherited environment (the workflow's Run pytest step sets it in the parent this module runs
    under, so leaving it out of a child's env would not turn it off), the same road is one passed test carrying the
    warning. The child selects the CLASS node id, never the file: the file would collect this class too and spawn
    grandchildren without end. It passes no -p tests.conftest: the module lives under tests/, whose conftest pytest
    loads on its own, and registering it a second time is pluggy's "Plugin already registered" error (run 2026-09-20).
    The message texts witness that the blocker took effect where there is an SDK to hide: an unloaded blocker on such a
    venv reads as a pass under the switch and as a pass without the warning off it, and both are red here.
    Before this case the fail branch was a non-red mutant: with its four lines deleted this module read 22 passed,
    1 warning under the switch on a venv without the SDK, and 22 passed in CI's shape on one with it (2026-09-20)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sdk-require-")
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        with open(os.path.join(self.d, "sitecustomize.py"), "w") as f:
            f.write(sdk_blocker.SITECUSTOMIZE)
        self.node = "%s::%s" % (os.path.relpath(os.path.realpath(__file__), ROOT), InstalledVersion.__name__)

    def _run_installed_version(self, require):
        """pytest in a child over InstalledVersion's class node id with the blocker's directory prepended to the
        inherited PYTHONPATH; `require` sets ROMP_SDK_REQUIRE=1, else the variable is popped from the child's env."""
        env = dict(os.environ)
        env.pop("ROMP_SDK_REQUIRE", None)
        if require:
            env["ROMP_SDK_REQUIRE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join([self.d] + [p for p in (env.get("PYTHONPATH", ""),) if p])
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:anyio", self.node],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
        return p.returncode, p.stdout + p.stderr

    def test_on_the_switch_an_interpreter_without_the_sdk_fails_the_run_naming_the_switch(self):
        rc, out = self._run_installed_version(require=True)
        self.assertNotEqual(rc, 0, "ROMP_SDK_REQUIRE=1 on an interpreter without the SDK must fail the run, not warn: " + out[-3000:])
        self.assertIn("ROMP_SDK_REQUIRE=1: this run requires the SDK", out, "the red must carry the switch's own message: " + out[-3000:])
        self.assertIn("FAILED %s::" % self.node, out, "the red must be InstalledVersion's own test: " + out[-3000:])
        self.assertIn("1 failed", out, "one test, failed, nothing skipped: " + out[-3000:])

    def test_off_the_switch_the_same_interpreter_passes_with_the_warning(self):
        rc, out = self._run_installed_version(require=False)
        self.assertEqual(rc, 0, "off the switch the no-SDK road warns and never fails: " + out[-3000:])
        self.assertIn("1 passed, 1 warning", out, "one test, passed, with the warning pytest lists under -q: " + out[-3000:])
        self.assertIn("claude_agent_sdk does not import in this interpreter", out, "the warning must say what was not checked: " + out[-3000:])


# ---------------------------------------------------------------------------------------------------------------------
# The population check (round 3's ruling, 2026-09-20): every pytest invocation in the workflow, not one step's text.
# Until this round two pins read the Run pytest step alone, and ci.yml's OTHER pytest invocation, the vscode-extension
# job's served-page step, set neither the switch nor the flag without a word; a third step added anywhere would have
# opted out the same way, and so would a step without a name or a run block spelled `|-` or `>`, which the first cut
# of this parser did not read at all (probed by execution before this landed: no invocation read, module green). The
# rule now: every command that runs pytest in ci.yml passes -p no:anyio (no list: pytest accepts the flag where anyio
# is absent, so there is no interpreter on which a pytest line has a reason to lack it), and either sets
# ROMP_SDK_REQUIRE=1 or is in SWITCH_LISTED with a reason whose premises ListedInvocations checks.
# What the parser reads, and its limits, are stated in pytest_invocations' docstring; a form it does not read is red.
# ---------------------------------------------------------------------------------------------------------------------
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):", re.M)                # a column-0 key of the workflow's mapping
JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]*(?:#.*)?\n", re.M)           # a job: a key at indent 2 under jobs:
STEP_START_RE = re.compile(r"^      - ", re.M)                                # a step: a list item at indent 6
STEP_KEY_PAD = "        "                                                     # step keys sit at indent 8 once `- ` is spaced
RUN_RE = re.compile(r"^        run:(.*)$", re.M)
BLOCK_INDICATOR_RE = re.compile(r"^[ \t]*([|>])([+-]?)([0-9]?)[ \t]*(#.*)?$")
UNNAMED = "(unnamed step)"
# a command that runs pytest: `python -m pytest`, `python3.12 -m pytest`, a bare `pytest` or `py.test`, at command
# position (the start of a command, or after `;`, `&`, `|`, `(`, so `&&` and `||` too), after any inline VAR=value
# prefixes (read into the invocation's env). A `$PYTEST` variable, `uvx pytest`, `tox`, `uv run pytest` or a wrapper
# script is NOT read as a command; a run line that mentions pytest and is neither a match nor a pip install line is
# reported as `unparsed` and reds the population test until the parser reads it (or the mention moves to a comment),
# so the parser's limits fail loud rather than green.
PYTEST_CMD_RE = re.compile(r"(?:^[ \t]*|[;&|(][ \t]*)(?P<env>(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*)"
                           r"(?:\S*/)?(?:python[0-9.]*[ \t]+-m[ \t]+pytest|pytest|py\.test)(?=\s|$)(?P<args>[^\n]*)")
# a mention: the word in any case (so `$PYTEST` and `${PYTEST_CMD}` count), or py.test; a mention that is not a command
# hit and not a pip line is `unparsed`
PYTEST_WORD_RE = re.compile(r"\bpytest\b|\bpy\.test\b|\$\{?pytest", re.I)
PIP_INSTALL_RE = re.compile(r"\bpipx?\b.*\binstall\b")
SHELL_SPLIT_RE = re.compile(r"[ \t](?:&&|\|\||[;|&])(?:[ \t]|$)")           # where a command's own arguments end
INLINE_ENV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S*)")
SWITCH = "ROMP_SDK_REQUIRE"
FLAG_SPELLING = "-p no:anyio"
FLAG_RE = re.compile(r"(?:^|\s)-p\s+no:anyio(?=\s|$)")

# Invocations that pass the flag and do NOT set the switch, each with the reason that makes that right, keyed (job,
# step name). The reason's premises are CHECKED by ListedInvocations below, not read: a listing whose premise stops
# holding goes red there, so the list stays a rule and not a roster. A step without a name cannot be listed: the
# stale-entry check needs a name to find.
SWITCH_LISTED = {
    ("vscode-extension", "Browser-backed served-page tests (pytest)"): (
        "the switch declares that the interpreter running pytest has the SDK the Python job's install step put there, "
        "and this job installs none (its pip line names pip, pytest, pytest-timeout and cryptography; run 35535192879's "
        "served step installed nine packages, no SDK), so setting it would declare something untrue; and its two globs "
        "collect no module that reads the switch, nor does any helper module under tests/ they could import, so the "
        "switch would change nothing there today. Premises checked: no SDK install in the job's run blocks; no "
        "collected or helper file under tests/ spells the switch's name."),
}
# names an SDK install would carry in a run block
SDK_INSTALL_TOKENS = ("claude-agent-sdk", "claude_agent_sdk", "romp-sdk-setup")


def _top_sections(src):
    """The workflow's top-level mapping: {key: [(offset, text)]}, each section running from its column-0 key line to
    the next column-0 key. Block scalars and mappings under a key are indented, so a column-0 key is never inside one;
    a column-0 comment is not a key."""
    keys = list(TOP_KEY_RE.finditer(src))
    out = {}
    for i, km in enumerate(keys):
        end = keys[i + 1].start() if i + 1 < len(keys) else len(src)
        out.setdefault(km.group(1), []).append((km.start(), src[km.start():end]))
    return out


def _env_block(text, env_indent):
    """The `env:` mapping whose `env:` line sits at `env_indent` spaces: {name: value}, the value's surrounding quotes
    stripped (`"1"` reads as `1`) and a trailing ` # comment` dropped. Comment and blank lines inside the block are
    skipped. A value that is a `${{ }}` expression is kept as its text, which is never `1`: the safe side."""
    pad = " " * env_indent
    m = re.search(r"^%senv:[ \t]*(?:#.*)?\n((?:%s .*\n|[ \t]*\n)+)" % (pad, pad), text, re.M)
    out = {}
    if m:
        for line in m.group(1).splitlines():
            km = re.match(r"""^\s*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(?:"([^"]*)"|'([^']*)'|([^#]*?))[ \t]*(?:#.*)?$""", line)
            if km:
                out[km.group(1)] = next(v for v in km.groups()[1:] if v is not None).strip()
    return out


def _line_of(src, offset):
    return src.count("\n", 0, offset) + 1


def _paragraphs(raw):
    """Fold [(offset, line)] the way YAML folds a plain or `>` scalar: consecutive non-blank lines join with one
    space, a blank line ends the paragraph. Returns [(offset of the first line, joined text)]."""
    out, cur = [], None
    for off, line in raw:
        if line.strip() == "":
            if cur:
                out.append(cur)
            cur = None
        elif cur is None:
            cur = (off, line.strip())
        else:
            cur = (cur[0], cur[1] + " " + line.strip())
    if cur:
        out.append(cur)
    return out


def _step_run(stext):
    """The step's `run:` scalar as shell lines [(offset in stext, text)] and an `unreadable` reason (None when the
    form is one this parser reads). Read: a single-line plain or quoted scalar, with continuation lines indented past
    the key folded onto it; a `run: |` literal (with a `-` or `+` chomping indicator: the indicator changes trailing
    newlines only); a `run: >` folded block, each paragraph one command. Not read, and reported so an invocation in
    the block is `unparsed`: an indentation indicator on the block (`|2`), or a line indented deeper than the block's
    first line inside a folded block (YAML keeps its line breaks, which this fold would not). No `run:`: (None, None)."""
    m = RUN_RE.search(stext)
    if not m:
        return None, None
    rest = m.group(1)
    after_off = m.end() + 1
    raw, pos = [], 0
    for line in stext[after_off:].splitlines(keepends=True):
        if line.strip() == "" or line.startswith(STEP_KEY_PAD + " "):
            raw.append((after_off + pos, line))
            pos += len(line)
        else:
            break
    while raw and raw[-1][1].strip() == "":
        raw.pop()
    bm = BLOCK_INDICATOR_RE.match(rest)
    if bm:
        style, indent_indicator = bm.group(1), bm.group(3)
        content = [(o, l) for o, l in raw if l.strip() != ""]
        if not content:
            return [], None
        if indent_indicator:
            return [(o, l.strip()) for o, l in content], "an indentation indicator (%s) on the block" % bm.group(0).strip()
        indent = len(content[0][1]) - len(content[0][1].lstrip(" "))
        if style == "|":
            return [(o, l[indent:].rstrip("\n")) for o, l in raw], None
        if any(len(l) - len(l.lstrip(" ")) > indent for o, l in content):
            return [(o, l.strip()) for o, l in content], "a line indented deeper than the block's first line in a folded block"
        return _paragraphs(raw), None
    first = rest.strip()
    first_off = m.start(1) + (len(rest) - len(rest.lstrip()))
    paras = _paragraphs([(first_off, first)] + raw) if first else _paragraphs(raw)
    if paras and len(paras[0][1]) >= 2 and paras[0][1][0] in "\"'" and paras[0][1][-1] == paras[0][1][0]:
        paras[0] = (paras[0][0], paras[0][1][1:-1])
    return paras, None


def pytest_invocations(src):
    """Every pytest invocation in a workflow's text, as dicts: job, step (the `name:`, else "(unnamed step)"), line (in
    the file), env (the workflow's env updated by the job's, by the step's, then by VAR=value prefixes on the command
    itself: the scopes GitHub Actions merges, later overriding earlier), args (the command's own arguments, cut at the
    next shell operator), run (the step's whole run text), job_run (every run text in the job) and cwd (the step's
    working-directory, else the job's default, else None); plus, for a run line that mentions pytest without being a
    command the parser reads or a pip install line, a dict with `unparsed` set to the reason and args None.
    A text parse over the file's own indentation (top-level keys at column 0, jobs at 2, job keys at 4, steps at 6,
    step keys at 8, env keys and run block lines at 10), the way this file's other pins and tests/test_ci_bats_bound.py
    read it: no YAML library in the test deps. The run forms read are _step_run's; comment lines are skipped; a line
    ending in a backslash is joined with the next. Outside this parser by construction: a pytest run by a script or
    action the workflow calls, and a run line that never spells pytest (a `$PYTEST` variable set elsewhere)."""
    sections = _top_sections(src)
    assert "jobs" in sections, "ci.yml has no jobs: mapping at column 0: re-anchor this parser"
    wf_env = {}
    for _off, text in sections.get("env", []):
        wf_env.update(_env_block(text, 0))
    jobs_at, body = sections["jobs"][0]
    found = []
    jobs = list(JOB_RE.finditer(body))
    for i, jm in enumerate(jobs):
        job = jm.group(1)
        jend = jobs[i + 1].start() if i + 1 < len(jobs) else len(body)
        jtext = body[jm.end():jend]
        jbase = jobs_at + jm.end()
        job_env = dict(wf_env)
        job_env.update(_env_block(jtext, 4))
        dm = re.search(r"^    defaults:\n      run:\n        working-directory: (.*)$", jtext, re.M)
        job_wd = dm.group(1).strip() if dm else None
        steps = list(STEP_START_RE.finditer(jtext))
        parsed = []
        job_runs = []
        for k, sm in enumerate(steps):
            send = steps[k + 1].start() if k + 1 < len(steps) else len(jtext)
            # the `- ` of the list item spaced out, so every step key, the first included, sits at indent 8 and a
            # step that opens with `- run:` is read like one that opens with `- name:`; same length, offsets kept
            stext = STEP_KEY_PAD + jtext[sm.end():send]
            sbase = jbase + sm.start()
            nm = re.search(r"^        name: (.*)$", stext, re.M)
            step = nm.group(1).strip() if nm else UNNAMED
            wm = re.search(r"^        working-directory: (.*)$", stext, re.M)
            cwd = wm.group(1).strip() if wm else job_wd
            env = dict(job_env)
            env.update(_env_block(stext, 8))
            lines, unreadable = _step_run(stext)
            if lines is None:
                continue
            run_text = "".join(t + "\n" for _o, t in lines)
            job_runs.append(run_text)
            j = 0
            while j < len(lines):
                off, cmd = lines[j]
                while cmd.rstrip().endswith("\\") and j + 1 < len(lines):
                    j += 1
                    cmd = cmd.rstrip()[:-1].rstrip() + " " + lines[j][1].strip()
                j += 1
                at = _line_of(src, sbase + off)
                if cmd.lstrip().startswith("#"):
                    continue
                if not PYTEST_WORD_RE.search(cmd):
                    continue
                base = {"job": job, "step": step, "line": at, "run": run_text, "cwd": cwd, "cmd": cmd}
                hits = [] if unreadable else list(PYTEST_CMD_RE.finditer(cmd))
                for hit in hits:
                    inv_env = dict(env)
                    inv_env.update(INLINE_ENV_RE.findall(hit.group("env")))
                    parsed.append(dict(base, env=inv_env, args=SHELL_SPLIT_RE.split(hit.group("args"), 1)[0], unparsed=None))
                if not hits and not PIP_INSTALL_RE.search(cmd):
                    parsed.append(dict(base, env=dict(env), args=None,
                                       unparsed=unreadable or "a form the parser does not read as a command"))
        for inv in parsed:
            inv["job_run"] = "".join(job_runs)
        found.extend(parsed)
    return found


def verdict(inv):
    """'ok': the args carry -p no:anyio and the env sets ROMP_SDK_REQUIRE to 1; 'listed': the flag, no switch, and
    (job, step) in SWITCH_LISTED; 'unparsed': a pytest mention the parser did not read as a command; 'unlisted':
    anything else, the failure this check exists for (the flag missing has no listing that excuses it)."""
    if inv["unparsed"]:
        return "unparsed"
    if not FLAG_RE.search(inv["args"]):
        return "unlisted"
    if inv["env"].get(SWITCH) == "1":
        return "ok"
    if (inv["job"], inv["step"]) in SWITCH_LISTED:
        return "listed"
    return "unlisted"


def _describe(inv):
    """The offender, named: job, step, file line, and what it lacks. The flag half keys on the SPELLING `-p no:anyio`
    (one space) in the command's own arguments; the switch half on the merged env reading exactly 1."""
    if inv["unparsed"]:
        return "%s / %r (ci.yml line %d): mentions pytest in a run line the parser does not read as a command (%s): %r" % (
            inv["job"], inv["step"], inv["line"], inv["unparsed"], inv["cmd"].strip())
    lacks = [w for w, ok in (("%s (keyed on that spelling, one space, in the command's arguments)" % FLAG_SPELLING,
                              bool(FLAG_RE.search(inv["args"]))),
                             ("%s=1 (keyed on the merged workflow, job, step and inline env reading 1)" % SWITCH,
                              inv["env"].get(SWITCH) == "1")) if not ok]
    return "%s / %r (ci.yml line %d): env %s=%r, args %r; lacks %s" % (
        inv["job"], inv["step"], inv["line"], SWITCH, inv["env"].get(SWITCH), inv["args"].strip(), " and ".join(lacks) or "nothing")


def _positional_paths(inv):
    """The path arguments of the invocation (tokens that are not an option or an option's value), resolved against its
    working directory, `${{ github.workspace }}` and no directory both reading as the repo root."""
    cwd = inv["cwd"]
    base = ROOT if cwd in (None, "${{ github.workspace }}") else os.path.join(ROOT, cwd)
    toks, paths, skip = shlex.split(inv["args"]), [], False
    for t in toks:
        if skip:
            skip = False
            continue
        if t in ("-p", "-k", "-m", "-o", "-c", "-W"):
            skip = True
            continue
        if t.startswith("-"):
            continue
        paths.append(os.path.join(base, t))
    return paths


MATRIX_STEP = ("python", "Run pytest")
SERVED_STEP = ("vscode-extension", "Browser-backed served-page tests (pytest)")


class PytestPopulation(unittest.TestCase):
    """Every pytest invocation in .github/workflows/ci.yml passes -p no:anyio and either declares the SDK requirement or
    is listed for the switch with a reason whose premises hold (round 3's ruling, 2026-09-20). The population is
    DERIVED from the file by pytest_invocations (the rule is its docstring; `python -c` over it lists the members), and
    the two invocations the file is known to hold, the Python matrix step and the vscode-extension job's served-page
    step, are asserted present, so an empty or partial derivation is red, not green. A pin on one step's text let the
    other set neither the switch nor the flag without a word, and a third step added tomorrow would have opted out the
    same way. The check reads the file's text: a pytest run by a script or action the workflow calls is outside it,
    and a run line that spells pytest in a form the parser does not read is red as unparsed until it is read."""
    def setUp(self):
        self.src = open(WF).read()
        self.found = pytest_invocations(self.src)

    def test_the_population_is_derived_and_holds_the_two_known_invocations(self):
        keys = {(i["job"], i["step"]) for i in self.found}
        self.assertIn(MATRIX_STEP, keys, "the Python matrix step's pytest line was not found (keyed on the job key at "
                      "indent 2 and the step's name: line): %r" % keys)
        self.assertIn(SERVED_STEP, keys, "the served-page step's pytest line was not found (keyed on the job key at "
                      "indent 2 and the step's name: line): %r" % keys)

    def test_every_invocation_passes_the_flag_and_sets_the_switch_or_is_listed_with_its_reason(self):
        bad = [_describe(i) for i in self.found if verdict(i) in ("unlisted", "unparsed")]
        self.assertEqual(bad, [], "pytest invocations in ci.yml that lack %s (keyed on that spelling), or set no %s=1 in "
                         "the env Actions merges for them (workflow, job, step, inline) without an entry in SWITCH_LISTED, "
                         "or that the parser could not read as a command (red until read):\n  " % (FLAG_SPELLING, SWITCH)
                         + "\n  ".join(bad))

    def test_the_python_matrix_step_is_compliant_not_listed(self):
        # the cells' whole-suite process: the switch is what makes a cell whose interpreter lost the SDK red, and the flag
        # what keeps anyio's plugin out of its pytest; neither may move to the list
        inv = [i for i in self.found if (i["job"], i["step"]) == MATRIX_STEP]
        self.assertEqual(len(inv), 1, inv)
        self.assertEqual(verdict(inv[0]), "ok", _describe(inv[0]))
        self.assertNotIn(MATRIX_STEP, SWITCH_LISTED, "the matrix step is listed: a cell without the SDK would read green")

    def test_every_listed_entry_names_an_invocation_that_exists(self):
        # a stale entry is a reason with no subject: the step was renamed or removed and the list did not follow; and a
        # listing needs a name to be found by, so the unnamed placeholder is refused as a key
        keys = {(i["job"], i["step"]) for i in self.found}
        for key in SWITCH_LISTED:
            self.assertNotEqual(key[1], UNNAMED, "SWITCH_LISTED lists an unnamed step: give the step a name: to list it by")
            self.assertIn(key, keys, "SWITCH_LISTED names %r, which is not a pytest invocation in the workflow (keyed on "
                          "the job key and the step's name: line)" % (key,))


class ListedInvocations(unittest.TestCase):
    """The premises of each SWITCH_LISTED reason, checked against the tree, so the list stays a rule and not a roster."""
    def setUp(self):
        self.found = {(i["job"], i["step"]): i for i in pytest_invocations(open(WF).read()) if not i["unparsed"]}
        self.served = self.found[SERVED_STEP]

    def test_the_served_step_passes_the_flag_its_listing_excuses_only_the_switch(self):
        self.assertTrue(FLAG_RE.search(self.served["args"]), "the served step's pytest line lacks %s (keyed on that "
                        "spelling): the listing covers the switch alone; the flag is accepted where anyio is absent and "
                        "has no exemption" % FLAG_SPELLING)

    def test_the_served_steps_job_installs_no_sdk(self):
        # keyed on the install's names in the job's run blocks; an install by a `uses:` action is outside this read
        for token in SDK_INSTALL_TOKENS:
            self.assertNotIn(token, self.served["job_run"], "a run block of the vscode-extension job names %r: the job's "
                             "interpreter may now have the SDK, so the served step's listing for the switch is no longer "
                             "true; set %s=1 there and drop the entry" % (token, SWITCH))

    def test_the_served_step_does_not_set_the_switch(self):
        # a listed step that sets the switch is a contradiction: either it is compliant, or it is listed
        self.assertNotIn(SWITCH, self.served["env"], "the served step sets %s: it declares an SDK it does not install" % SWITCH)

    def test_the_served_steps_globs_collect_no_module_that_reads_the_switch(self):
        # keyed on the switch's name spelled in the file's text: the modules the step's globs collect, plus every
        # non-test module under tests/ (conftest, __init__, the helpers a collected module may import); a reader that
        # spells the name indirectly is outside this read
        readers = set()
        for path in glob.glob(os.path.join(HERE, "*.py")):
            with open(path, encoding="utf-8") as f:
                if SWITCH in f.read():
                    readers.add(os.path.realpath(path))
        self.assertIn(os.path.realpath(__file__), readers, "the census missed this file, which reads the switch")
        helpers = {os.path.realpath(p) for p in glob.glob(os.path.join(HERE, "*.py")) if not os.path.basename(p).startswith("test_")}
        self.assertIn(os.path.realpath(os.path.join(HERE, "conftest.py")), helpers, "the helper census missed conftest.py")
        collected = set()
        for pattern in _positional_paths(self.served):
            collected.update(os.path.realpath(p) for p in glob.glob(pattern))
        self.assertTrue(collected, "the served step's globs resolve to no file at the repo root: %r" % self.served["args"])
        hit = sorted(os.path.relpath(p, ROOT) for p in readers & (collected | helpers))
        self.assertEqual(hit, [], "the served step collects or could load a module that reads %s, and it runs without the "
                         "switch: %s" % (SWITCH, hit))


THIRD_STEP = ("      - name: Kernel smoke (pytest)\n"
              "        run: python -m pytest tests/test_kernel_smoke.py -q\n")
# read forms, each a step spliced into the shell job: (label, step text, the offset of the pytest command's line from
# the step's first line, the arguments the parser must read from it)
READ_FORMS = (
    ("single line", "      - name: Form (pytest)\n        run: python -m pytest tests/test_a.py -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("literal block", "      - name: Form (pytest)\n        run: |\n          set -e\n          python -m pytest tests/test_a.py -q -p no:anyio\n",
     3, "tests/test_a.py -q -p no:anyio"),
    ("literal block, strip chomping", "      - name: Form (pytest)\n        run: |-\n          python -m pytest tests/test_a.py -q -p no:anyio\n",
     2, "tests/test_a.py -q -p no:anyio"),
    ("literal block, keep chomping", "      - name: Form (pytest)\n        run: |+\n          pytest tests/test_a.py -q -p no:anyio\n",
     2, "tests/test_a.py -q -p no:anyio"),
    ("folded block, one command over two lines", "      - name: Form (pytest)\n        run: >\n          python -m pytest tests/test_a.py\n          -q -p no:anyio\n",
     2, "tests/test_a.py -q -p no:anyio"),
    ("folded block, strip chomping, second paragraph", "      - name: Form (pytest)\n        run: >-\n          echo start\n\n          python -m pytest tests/test_a.py\n          -q -p no:anyio\n",
     4, "tests/test_a.py -q -p no:anyio"),
    ("plain scalar continued on the next line", "      - name: Form (pytest)\n        run: python -m pytest tests/test_a.py\n          -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("double-quoted scalar", "      - name: Form (pytest)\n        run: \"python -m pytest tests/test_a.py -q -p no:anyio\"\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("after && on one line", "      - name: Form (pytest)\n        run: echo start && python -m pytest tests/test_a.py -q -p no:anyio && echo done\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("interpreter by path and version", "      - name: Form (pytest)\n        run: /opt/py/bin/python3.12 -m pytest tests/test_a.py -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("py.test spelling", "      - name: Form (pytest)\n        run: py.test tests/test_a.py -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("backslash continuation in a literal block", "      - name: Form (pytest)\n        run: |\n          python -m pytest tests/test_a.py \\\n            -q -p no:anyio\n",
     2, "tests/test_a.py -q -p no:anyio"),
)


class PopulationCheckReds(unittest.TestCase):
    """The check names a new or changed pytest invocation: a scratch copy of the workflow text, edited into each shape
    the rule refuses, is judged and the offender is 'unlisted' (or 'unparsed') with its job, name and line. The
    copies are cut from the live file, so the parser is exercised on the real file's shape. The read forms are each
    proved twice: read with the right line and arguments, and 'ok' once a job-level env supplies the switch, so the
    form and the env merge are both exercised (the first cut of the parser read none of the unnamed, `|-` and `>`
    forms, and a step in any of them was green; probed by execution, 2026-09-20)."""
    def setUp(self):
        self.src = open(WF).read()
        self.base = {(i["job"], i["step"]) for i in pytest_invocations(self.src)}
        self.assertNotIn(("shell", UNNAMED), self.base, "the live shell job holds an unnamed pytest step: the cases below "
                         "splice their own into that job and would not tell them apart")

    def _with_step_in_shell_job(self, step_text, src=None):
        # appended as the shell job's last step: before the `  secrets:` job line
        src = self.src if src is None else src
        at = src.index("\n  secrets:\n") + 1
        return src[:at] + step_text + src[at:], _line_of(src, at)

    def _with_shell_job_env(self, src, value='"1"'):
        out = src.replace("\n  shell:\n    name: Shell", '\n  shell:\n    env:\n      %s: %s\n    name: Shell' % (SWITCH, value), 1)
        self.assertNotEqual(out, src, "the shell job's header moved: re-anchor this case")
        return out

    def _new_bad(self, src):
        return [i for i in pytest_invocations(src) if verdict(i) in ("unlisted", "unparsed") and (i["job"], i["step"]) not in self.base]

    def _new(self, src):
        return [i for i in pytest_invocations(src) if (i["job"], i["step"]) not in self.base]

    def test_a_third_pytest_step_with_neither_switch_nor_flag_is_unlisted_and_named(self):
        src, first = self._with_step_in_shell_job(THIRD_STEP)
        bad = self._new_bad(src)
        self.assertEqual([(i["job"], i["step"], verdict(i)) for i in bad], [("shell", "Kernel smoke (pytest)", "unlisted")])
        self.assertEqual(bad[0]["line"], first + 1)
        self.assertEqual(src.splitlines()[bad[0]["line"] - 1].strip(), "run: python -m pytest tests/test_kernel_smoke.py -q")
        self.assertIn("lacks -p no:anyio", _describe(bad[0]))
        self.assertIn("and ROMP_SDK_REQUIRE=1", _describe(bad[0]))
        self.assertEqual(len(pytest_invocations(src)), len(pytest_invocations(self.src)) + 1)

    def test_an_unnamed_run_step_is_read_attributed_to_itself_and_named_at_its_line(self):
        # a `- run:` step with no name: line is a step of its own, not a tail of the named step before it; the first
        # cut of the parser looked for `run:` at indent 8 only and read nothing from such a step (probed, 2026-09-20)
        single, first = self._with_step_in_shell_job("      - run: python -m pytest tests/test_a.py -q\n")
        bad = self._new_bad(single)
        self.assertEqual([(i["job"], i["step"], i["line"], verdict(i)) for i in bad], [("shell", UNNAMED, first, "unlisted")])
        self.assertIn("shell / '(unnamed step)' (ci.yml line %d)" % first, _describe(bad[0]))
        block, first = self._with_step_in_shell_job("      - run: |\n          set -e\n          python -m pytest tests/test_a.py -q\n")
        bad = self._new_bad(block)
        self.assertEqual([(i["step"], i["line"], verdict(i)) for i in bad], [(UNNAMED, first + 2, "unlisted")])
        # with the env and the flag it is compliant, so the read is the whole step and not its first line alone
        ok, first = self._with_step_in_shell_job('      - env:\n          %s: "1"\n        run: python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        new = self._new(ok)
        self.assertEqual([(i["step"], i["line"], verdict(i)) for i in new], [(UNNAMED, first + 2, "ok")])

    def test_every_read_form_is_read_at_its_line_with_its_arguments_and_the_job_env_makes_it_ok(self):
        for label, step, offset, args in READ_FORMS:
            with self.subTest(form=label):
                src, first = self._with_step_in_shell_job(step)
                new = self._new(src)
                self.assertEqual(len(new), 1, "%s: expected one invocation read from the step, got %r" % (label, [_describe(i) for i in new]))
                inv = new[0]
                self.assertIsNone(inv["unparsed"], "%s: read as unparsed: %s" % (label, _describe(inv)))
                self.assertEqual(inv["line"], first + offset, "%s: the command's line: %s" % (label, _describe(inv)))
                self.assertEqual(inv["args"].strip(), args, "%s: the command's arguments: %s" % (label, _describe(inv)))
                self.assertEqual(verdict(inv), "unlisted", "%s: no switch in any scope, so unlisted: %s" % (label, _describe(inv)))
                self.assertIn("lacks ROMP_SDK_REQUIRE=1", _describe(inv))
                with_env = self._new(self._with_shell_job_env(src))
                self.assertEqual([verdict(i) for i in with_env], ["ok"], "%s: a job-level env must supply the switch: %r" % (label, [_describe(i) for i in with_env]))

    def test_an_inline_env_prefix_on_the_command_sets_the_switch_for_that_command(self):
        # `ROMP_SDK_REQUIRE=1 python -m pytest ...` sets the variable for that process, as an env: block would
        src, first = self._with_step_in_shell_job('      - name: Prefixed (pytest)\n        run: %s=1 python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        new = self._new(src)
        self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + 1, "ok")], [_describe(i) for i in new])
        other, first = self._with_step_in_shell_job('      - name: Prefixed (pytest)\n        run: PYTHONWARNINGS=error python -m pytest tests/test_a.py -q -p no:anyio\n')
        new = self._new(other)
        self.assertEqual([verdict(i) for i in new], ["unlisted"], "another variable's prefix is not the switch")
        self.assertEqual(new[0]["args"].strip(), "tests/test_a.py -q -p no:anyio")
        # an export earlier in the block is not read into the env: the safe side, red rather than assumed
        export, first = self._with_step_in_shell_job('      - name: Exported (pytest)\n        run: |\n          export %s=1\n          python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        self.assertEqual([verdict(i) for i in self._new(export)], ["unlisted"])

    def test_the_switch_without_the_flag_and_the_flag_without_the_switch_are_both_unlisted(self):
        half_a = ('      - name: Half A (pytest)\n        env:\n          ROMP_SDK_REQUIRE: "1"\n'
                  '        run: python -m pytest tests/ -q\n')
        half_b = '      - name: Half B (pytest)\n        run: python -m pytest tests/ -q -p no:anyio\n'
        bad = {i["step"]: _describe(i) for i in self._new_bad(self._with_step_in_shell_job(half_a + half_b)[0])}
        self.assertEqual(sorted(bad), ["Half A (pytest)", "Half B (pytest)"])
        self.assertIn("lacks -p no:anyio", bad["Half A (pytest)"])
        self.assertIn("lacks ROMP_SDK_REQUIRE=1", bad["Half B (pytest)"])

    def test_the_flag_check_is_a_spelling_check_and_says_so(self):
        # `-pno:anyio` is the same flag to pytest; this check keys on the spelling with one space and its message says so
        src, first = self._with_step_in_shell_job('      - name: Nospace (pytest)\n        env:\n          %s: "1"\n        run: python -m pytest tests/ -q -pno:anyio\n' % SWITCH)
        bad = self._new_bad(src)
        self.assertEqual([verdict(i) for i in bad], ["unlisted"])
        self.assertIn("lacks -p no:anyio (keyed on that spelling, one space, in the command's arguments)", _describe(bad[0]))

    def test_the_served_step_without_the_flag_is_unlisted_and_named_at_its_line(self):
        # the listing excuses the switch alone: the flag off that line is red even with the entry in place
        served_line = [l for l in self.src.splitlines() if l.startswith("          python -m pytest tests/test_*_browser.py")]
        self.assertEqual(len(served_line), 1, served_line)
        src = self.src.replace(served_line[0], served_line[0].replace(" -p no:anyio", ""), 1)
        served = [i for i in pytest_invocations(src) if (i["job"], i["step"]) == SERVED_STEP]
        self.assertEqual(len(served), 1, served)
        self.assertEqual(verdict(served[0]), "unlisted", _describe(served[0]))
        self.assertIn("lacks -p no:anyio", _describe(served[0]))
        self.assertEqual(src.splitlines()[served[0]["line"] - 1].strip(), served_line[0].strip().replace(" -p no:anyio", ""))

    def test_the_matrix_step_without_the_switch_is_unlisted(self):
        src = self.src.replace('          ROMP_SDK_REQUIRE: "1"\n', "", 1)
        self.assertNotEqual(src, self.src, "the matrix step's switch line moved: re-anchor this case")
        matrix = [i for i in pytest_invocations(src) if (i["job"], i["step"]) == MATRIX_STEP]
        self.assertEqual(len(matrix), 1, matrix)
        self.assertEqual(verdict(matrix[0]), "unlisted", _describe(matrix[0]))
        self.assertIn("lacks ROMP_SDK_REQUIRE=1", _describe(matrix[0]))

    def test_the_served_step_with_its_entry_removed_is_unlisted(self):
        # what the list buys: an entry gone, the step is named; what it costs: the premises above
        served = [i for i in pytest_invocations(self.src) if (i["job"], i["step"]) == SERVED_STEP]
        self.assertEqual(len(served), 1, served)
        self.assertEqual(verdict(served[0]), "listed", _describe(served[0]))
        with mock.patch.dict(SWITCH_LISTED, clear=True):
            self.assertEqual(verdict(served[0]), "unlisted", _describe(served[0]))

    def test_a_job_level_env_a_workflow_level_env_and_their_precedence_are_read(self):
        lit = ('      - name: Literal (pytest)\n        run: |\n          set -e\n          # pytest in a comment is not a call\n'
               '          pytest tests/test_a.py -q \\\n            -p no:anyio\n')
        src, first = self._with_step_in_shell_job(lit)
        # a job-level env satisfies the switch half for every step of the job
        job_env = self._with_shell_job_env(src)
        found = {i["step"]: i for i in pytest_invocations(job_env)}
        self.assertIn("Literal (pytest)", found)
        self.assertEqual(verdict(found["Literal (pytest)"]), "ok", _describe(found["Literal (pytest)"]))
        self.assertEqual(job_env.splitlines()[found["Literal (pytest)"]["line"] - 1].strip(), "pytest tests/test_a.py -q \\")
        # a workflow-level env does the same for every job, wherever the top-level env: mapping sits (before jobs: or
        # after it: the first cut read the text before jobs: alone); the job's and the step's override it
        for wf_env in (src.replace("\njobs:\n", '\nenv:\n  ROMP_SDK_REQUIRE: "1"   # a trailing comment\n\njobs:\n', 1),
                       src + '\nenv:\n  ROMP_SDK_REQUIRE: "1"\n'):
            found = {i["step"]: i for i in pytest_invocations(wf_env)}
            self.assertEqual(verdict(found["Literal (pytest)"]), "ok", _describe(found["Literal (pytest)"]))
            found = {i["step"]: i for i in pytest_invocations(self._with_shell_job_env(wf_env, '"0"'))}
            self.assertEqual(verdict(found["Literal (pytest)"]), "unlisted", "the job's env must override the workflow's")
        # an expression-valued switch is never read as 1: the safe side
        found = {i["step"]: i for i in pytest_invocations(self._with_shell_job_env(src, "${{ matrix.require }}"))}
        self.assertEqual(verdict(found["Literal (pytest)"]), "unlisted", _describe(found["Literal (pytest)"]))

    def test_a_pytest_mention_the_parser_does_not_read_as_a_command_is_unparsed_and_named(self):
        # the parser's limits fail loud: each form it does not read is red until it is read (or moved to a comment)
        for label, step, reason in (
                ("a wrapper", "      - name: Wrapped (pytest)\n        run: uvx --with pytest pytest tests/ -q -p no:anyio\n",
                 "a form the parser does not read as a command"),
                ("a variable", "      - name: Variable (pytest)\n        run: $PYTEST tests/ -q -p no:anyio\n",
                 "a form the parser does not read as a command"),
                ("an indentation indicator", "      - name: Indented (pytest)\n        run: |2\n            python -m pytest tests/ -q -p no:anyio\n",
                 "an indentation indicator (|2) on the block"),
                ("a more-indented line in a folded block", "      - name: Folded (pytest)\n        run: >\n          echo start\n            python -m pytest tests/ -q -p no:anyio\n",
                 "a line indented deeper than the block's first line in a folded block")):
            with self.subTest(form=label):
                bad = self._new_bad(self._with_step_in_shell_job(step)[0])
                self.assertEqual([verdict(i) for i in bad], ["unparsed"], "%s: %r" % (label, [_describe(i) for i in bad]))
                self.assertIn("does not read as a command (%s)" % reason, _describe(bad[0]))
        # a pip line that names the package is not a mention the parser owes: the live file has two
        pip = "      - name: Pip (pytest)\n        run: python -m pip install --upgrade pip pytest pytest-timeout\n"
        self.assertEqual(self._new_bad(self._with_step_in_shell_job(pip)[0]), [])

if __name__ == "__main__":
    unittest.main()
