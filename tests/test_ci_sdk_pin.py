#!/usr/bin/env python3
"""CI installs the Claude Agent SDK at the session host's tested version (.github/workflows/ci.yml, 2026-09-20).

The 48 SDK-gated tests (43 in tests/test_sdk_backend.py, 5 in tests/test_host_transport.py) and the two SDK-transport
host tests in tests/test_session_host.py skipped in every CI cell, because no cell installed the SDK; the box that runs
the hosted sessions was the only place they ran. Now the Python job's "Install the Claude Agent SDK" step installs
`claude-agent-sdk==<pin>`, where the pin is read at run time from kernel/session_host.py's SDK_TESTED_VERSION, the
repo's one declaration of the version the host's private imports were verified against (bin/romp-sdk-setup reads the
same line with the same sed). The number appears nowhere in the workflow.

This module holds five things, and it never skips: a pin that skips reports green having checked nothing.
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
   checks over every pytest line of the step; an invocation that does neither is named with its job, step and file
   line, and so is one whose step name another pytest-running step of the job shares (`ambiguous`: the key would name
   two steps, and GitHub Actions does not require unique names). The population is derived from
   the file's text by pytest_invocations (its docstring is the rule: `python -m pytest`, a bare `pytest` or `py.test`
   at command position, in a named or unnamed step, in a single-line, quoted, continued, `run: |` or `run: >` scalar,
   backslash continuations joined, comment and pip lines excluded), and the two invocations the file is known to
   hold, the Python matrix step's Run pytest (the switch and the flag) and the vscode-extension job's served-page
   step (the flag; listed for the switch, since its job installs no SDK), are asserted present, so an empty read is
   red. The flag has no list: the constant pins the SDK alone, its dependency closure resolves fresh on every run (26
   packages on 2026-09-20, the 3.12 cell of run 35518107329), and one of them, anyio, registers a pytest plugin that
   every pytest process a cell runs would otherwise auto-load, the step's own process and every pytest child the
   suite spawns in the same interpreter (item 5 holds the flag on those), which the box's default run never does and
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
   pytest.importorskip reds as a collection error; one whose ONLY skip is an xfail fails the run by its exit status
   (a flipped xfail prints FAILED either way and counts toward the exit status only once the report's wasxfail is
   removed, which the flip in tests/conftest.py does; alone, so no other skip carries that exit for it); a
   plain-named twin of the first keeps skipping. Until 2026-09-20 the
   guard was a five-name list of unittest spellings read from this file's AST, which pytest.mark.skipif passed, and
   which a module-level importorskip removed from the run along with the rest of the module. What a report cannot
   show is a test that was never collected: renamed off the test_ prefix, deleted, or fenced behind an if, it reports
   nothing to flip and the module reads green with the version equality never checked (20 passed, exit 0, in CI's
   shape on a venv without the SDK, with InstalledVersion's method renamed). NeverSkips closes that road for the one
   test the belt exists for by asking pytest's own collector: a child `pytest --collect-only -q` over this module, run
   from the repo root, must list the test's node id (tests/test_ci_sdk_pin.py::InstalledVersion::<method>) as one
   whole line; keyed on that line's PRESENCE, never on a collected count, which would red on every test added here. A
   second, in-process case pins the method's name against unittest's loader over the class. The loader is not the
   collector: pytest's UnitTestCase.collect calls the loader and then drops the class, or the method, whose __test__
   is False, which the loader never reads, so the loader case alone read green with the test out of every run
   (2026-09-21: `__test__ = False` on the class or on the method, 48 of 49 collected and no InstalledVersion item, the
   loader case 1 passed, exit 0), and the collect-only case is red on both. What neither case can see is a road that
   drops this module from a RUN without touching the file, the residual stated here and above tests/conftest.py's
   tuple: a module-level __test__ = False empties the module's collection, this census with it (the child would list
   nothing, and never runs); the child hands pytest the file as an argument, and pytest asks pytest_ignore_collect
   only about paths it did not receive as arguments, so a collect_ignore, a collect_ignore_glob or a
   pytest_ignore_collect hook in a conftest is not asked in the child; a -k, -m or --deselect and an --ignore or
   --ignore-glob live on the run's own command line, not the child's; the module renamed or deleted takes the census
   with it (the rename reds the membership case below, the deletion the existence half in
   tests/test_served_tests_require.py). None of these is on ci.yml's Run pytest line (no path, no -k, no --ignore) and
   no conftest in the tree sets collect_ignore or the hook, as read on 2026-09-21; nothing pins that. The belt's
   subject is checked against the tree as well
   (2026-09-21): NeverSkips asserts this file's own basename is in _NEVER_SKIP_FILES as written in tests/conftest.py
   (never_skip_files_as_written there: ast.literal_eval over the text, so a tuple spelled any other way is reported
   as such rather than raising), and tests/test_served_tests_require.py, outside this module, asserts every entry names
   a file under tests/, so a rename of this file reds in both and a deletion reds there; before those two checks a
   copy renamed test_ci_sdk_pin_v2.py ran green with the belt inert, a skip in it a plain skip.
5. The launcher census (ChildPytestLaunchers; round 3's ruling, 2026-09-20). The workflow's flag blocks the plugin in
   the step's own process; a pytest child a test spawns is a new pytest process in the same interpreter, where the SDK
   step installed anyio, and without the flag it auto-loads the plugin (at round 3's head one of nine launchers passed
   it, while this docstring, ci.yml and tests/README.md said the cells' plugin set was the box's). The rule: every argv
   under tests/ that runs pytest passes -p no:anyio or is in LAUNCHERS_LISTED with a reason (empty: pytest accepts the
   flag where anyio is absent, so no launcher has had a reason to lack it), and the population is derived from the
   modules' syntax by child_pytest_launchers, keyed on the argv PROPERTY and not a spelling: a list or tuple literal,
   wherever it is built (in the call, in a helper that passes it on, in a variable extended later), whose command is
   pytest (`-m pytest`, or `-mpytest` as one token, after an interpreter head through interpreter options only, the
   head an expression or a python-named constant wherever it sits, so `python -B -m pytest`, the repo's own recipe,
   and `uv run python -m pytest` read; `-m pytest` as the first two elements; pytest or py.test by name or path as
   argv[0]; _argv_command's docstring is the rule). The flag check keys on the argv's constant elements (`-p` then `no:anyio`,
   or `-pno:anyio`), so a flag carried by a variable reads as absent, the safe side, and the message says so. The
   modules known to spawn pytest are asserted present, so an empty read is red, and there is no count to keep; the
   derivation case prints the listing (python -m pytest tests/test_ci_sdk_pin.py -q -p no:cacheprovider -p no:anyio
   -k ChildPytestLaunchers -rP). The census reads argv literals, and that is its residual: a pytest command inside a
   string handed to subprocess, os.system or shlex.split, or to a shell's -c (a `pytest.main(` call included), is
   `unparsed` and red until it is spelled as an argv, as is an argv that may run pytest and the census cannot tell (a
   `-m` whose module name is not a constant, an element that is not a constant right before `pytest`, after an
   interpreter head), and a module that does not parse under the running interpreter is red the same way; an argv
   assembled one element at a time (append calls) is outside the read. What the flag buys, in every pytest process a cell runs:
   anyio's plugin is absent from that process's plugin set as it is from the box's default run's. The sets are not
   equal, and nothing here says they are: the box's default run loads pytest-xdist's two plugins, which no cell
   installs. Verified by execution before this landed: a synthetic broken anyio/pytest_plugin.py in a CI-shaped venv
   (the SDK pinned, the parent under the flag) red tests in each of the six modules that spawned unflagged children,
   none of which imports the SDK, and the same six were green with the flag on every launcher (2026-09-20).

Hermetic: the run block executes in a scratch directory with its own copy of the constant's line, never at the repo
root, and its `python` is a shim that records its arguments; no network, no pip.
"""
import ast
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
from tests.conftest import never_skip_files_as_written
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
# An xfail that is the file's ONLY skip, under its own name and never bundled into SKIP_SPELLINGS: beside the other
# spellings, whose flips already make the run non-zero, the exit status is carried for it and the case proves nothing.
XFAIL_ONLY = '''
import unittest
import pytest
class OnlyXfail(unittest.TestCase):
    @pytest.mark.xfail(reason="synthetic xfail, the file's only skip")
    def test_xfail(self):
        self.fail("an xfail absorbs this")
'''


class NeverSkips(unittest.TestCase):
    """The never-skips belt in tests/conftest.py (_NEVER_SKIP_FILES), proved by execution the way
    tests/test_served_tests_require.py proves the served-tests switch: pytest in a child, tests/conftest.py loaded as a
    plugin, over scratch files in a temp directory. A scratch file of THIS module's name carries five skip spellings
    (two the old five-name list never covered, pytest.mark.skipif and an xfail; three it did) and every one is red,
    each naming the belt and quoting its reason; the same content under a plain name skips as pytest always let it;
    a scratch file of this name whose module level runs pytest.importorskip, which collects no items, is a collection
    error and the run stops red; a scratch file of this name whose ONLY skip is an xfail fails the RUN, its exit
    status the assertion (pytest prints FAILED for a flipped xfail either way and counts it toward the exit status
    only once the report's wasxfail attribute is removed, which the flip shared with the served switch does; bundled
    with the other spellings that exit was carried for it, so removing the delete red nothing until this case,
    2026-09-21). Synthetic files only; no SDK, no network. Two cases are in-process. The census, two cases: the belt
    reads reports, and a test that is never collected files none, so the one test the belt exists for is pinned in
    a child `pytest --collect-only -q` over this real module, pytest's own collector, whose listing must hold the
    test's node id (present, never a count), and in process by name against unittest's loader over the class. The
    loader is not the collector: UnitTestCase.collect calls it and then gates on __test__ on the class and on each
    method, which the loader never reads, so the in-process case pins the method's name and the child pins its
    collection. The collect-only child runs nothing, so it spawns no grandchild. The membership case: this file's
    own basename is in _NEVER_SKIP_FILES as written in tests/conftest.py, the literal every report is keyed on; the
    existence half of that check, every entry a file under tests/, lives in tests/test_served_tests_require.py,
    outside this module, where a deletion of this file can still red it. The children pass -p no:anyio, as
    every pytest the suite spawns does (ChildPytestLaunchers holds it on each launcher), so in a cell no child loads a
    plugin the box's default run does not (pytest accepts the flag where anyio is absent, as on the box venvs)."""
    INSTALLED_VERSION_TEST = "test_the_installed_sdk_is_the_pin_where_it_imports_and_the_pin_is_well_formed_where_it_does_not"
    INSTALLED_VERSION_NODE = "%s::%s::%s" % (os.path.relpath(os.path.realpath(__file__), ROOT), InstalledVersion.__name__,
                                             INSTALLED_VERSION_TEST)     # as pytest prints it from the repo root

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

    def test_an_xfail_that_is_the_files_only_skip_fails_the_run(self):
        # What this case guards is the EXIT STATUS, not the FAILED line: pytest prints FAILED for a flipped xfail whether
        # or not the report keeps its wasxfail attribute, and counts it toward the exit status only without it
        # (tests/conftest.py, _fail_skipped_report, the flip the belt shares with the served switch). Alone, under its
        # own name: with the delete removed and this file bundled into SKIP_SPELLINGS, the first case above read the
        # same counts line and the same non-zero exit, carried by the other spellings' flips (4 passed both ways,
        # 2026-09-21); alone, the same mutation reads "1 failed" and exit 0, and this case is red.
        rc, out = self._run(self._write("test_ci_sdk_pin.py", XFAIL_ONLY))
        self.assertNotEqual(rc, 0, "a flipped xfail must fail the RUN, not only print FAILED: " + out[-3000:])
        self.assertIn("1 failed", out, "the xfail is reported as the one failure: " + out[-3000:])
        self.assertIn("never-skips: test_ci_sdk_pin.py skipped (at call)", out, "the red names the belt and the file: " + out[-3000:])
        self.assertIn("xfail: synthetic xfail, the file's only skip", out, "...and carries the xfail's own reason: " + out[-3000:])

    def test_a_module_level_importorskip_under_a_plain_name_still_skips_the_module(self):
        rc, out = self._run(self._write("test_fake_plain.py", MODULE_LEVEL_SKIP))
        self.assertEqual(rc, 5, "no tests collected, nothing red: the belt reaches only the listed file: " + out[-3000:])
        self.assertIn("1 skipped", out, out[-3000:])
        self.assertNotIn("never-skips:", out, "the belt did not fire: " + out[-3000:])   # the colon: the scratch dir is named never-skips-

    def test_the_test_the_belt_exists_for_is_listed_by_unittests_loader_under_its_name(self):
        # the belt flips skipped REPORTS; a test that is never collected (renamed off the test_ prefix, deleted, fenced
        # behind an if) reports nothing, and the module read 20 passed, exit 0, in CI's shape on a venv without the SDK
        # with this method renamed (2026-09-20). Keyed on unittest's loader over the class listing exactly one method,
        # under this name: the METHOD's presence, in process. The loader is not pytest's collector, which calls it and
        # then drops a class or a method whose __test__ is False (this case stayed green under both, 2026-09-21); the
        # collector's answer is the next case's.
        self.assertEqual(unittest.defaultTestLoader.getTestCaseNames(InstalledVersion), [self.INSTALLED_VERSION_TEST],
                         "unittest's loader does not list InstalledVersion's one test under its name: the method the belt "
                         "guards is renamed, deleted or fenced (keyed on the loader's listing, not on pytest's collection)")

    def test_the_test_the_belt_exists_for_is_collected_by_pytest_under_its_node_id(self):
        # pytest's own collector, asked directly: a child `pytest --collect-only -q` over the real module, run from the
        # repo root (node ids rootdir-relative; tests/conftest.py loads for the path on its own, so no -p tests.conftest;
        # nothing runs, so no grandchild), must list the guarded test's node id as one whole line. Keyed on that line's
        # PRESENCE, never on a collected count: a count reds on every test added to this file. This is the road the
        # loader case above cannot see: with `__test__ = False` on InstalledVersion or on its method the collector
        # listed 48 of 49 and no InstalledVersion item while the loader case read 1 passed, exit 0 (2026-09-21). What
        # this case does not see is a road that drops the module from a RUN without touching the file, itself included
        # (a module-level `__test__ = False` empties the module's collection: the child would list nothing, and never
        # runs); the module docstring, item 4, and the comment above _NEVER_SKIP_FILES in tests/conftest.py state that
        # residual.
        p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-p", "no:anyio",
                            os.path.relpath(os.path.realpath(__file__), ROOT)],
                           cwd=ROOT, env=dict(os.environ), capture_output=True, text=True, timeout=240)
        out = p.stdout + p.stderr
        self.assertIn(self.INSTALLED_VERSION_NODE, out.splitlines(),
                      "pytest's collector does not list %s (keyed on that node id as one whole line of `pytest --collect-only -q` "
                      "run from the repo root; child exit %d): the test the belt guards is out of the run, whatever unittest's "
                      "loader lists: %s" % (self.INSTALLED_VERSION_NODE, p.returncode, out[-3000:]))

    def test_this_files_name_is_in_the_belts_tuple_as_written(self):
        # The belt keys every report on a basename literal in tests/conftest.py, and nothing else tied that literal
        # to this file: renamed test_ci_sdk_pin_v2.py, this module ran with the belt inert (a skip in it a plain
        # skip, exit 0) and every test here green, the scratch files above being written under the LISTED name
        # whatever this file is called (2026-09-21). Keyed on this file's basename against the tuple read from
        # tests/conftest.py's text, as written. The other half, that every entry names a file under tests/, is
        # tests/test_served_tests_require.py's, outside this module: a check in here cannot fire once this file is
        # deleted.
        names = never_skip_files_as_written()
        self.assertIn(os.path.basename(__file__), names,
                      "the never-skips belt does not name this file: _NEVER_SKIP_FILES in tests/conftest.py, as written, is %r" % (names,))


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
# a command that runs pytest: `python -m pytest`, `python3.12 -m pytest`, a bare `pytest` or `py.test`, at the START of a
# command (the run line is split into its commands first, _shell_commands: at `&&`, `||`, `;`, `|`, `&`, a subshell's
# parentheses, whatever the spacing, and cut at a comment), after any inline VAR=value prefixes (read into the
# invocation's env); the command's own arguments are the rest of that command and nothing after it. Until 2026-09-21 the
# regex took the rest of the LINE as the arguments and the split cut only at an operator with whitespace before it, so a
# second `python -m pytest` on the line was never read, and its flag, or one in a trailing comment, read as the first
# command's. A `$PYTEST` variable, `uvx pytest`, `tox`, `uv run pytest` or a wrapper script is NOT read as a command; a
# command that mentions pytest and is neither a match nor a pip install line is reported as `unparsed` and reds the
# population test until the parser reads it (a mention in a comment is cut with the comment), so the parser's limits
# fail loud rather than green.
PYTEST_CMD_RE = re.compile(r"^(?P<env>(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*)"
                           r"(?:\S*/)?(?:python[0-9.]*[ \t]+-m[ \t]+pytest|pytest|py\.test)(?=\s|$)(?P<args>.*)$")
# a mention: the word in any case (so `$PYTEST` and `${PYTEST_CMD}` count), or py.test; a mention that is not a command
# hit and not a pip line is `unparsed`
PYTEST_WORD_RE = re.compile(r"\bpytest\b|\bpy\.test\b|\$\{?pytest", re.I)
PIP_INSTALL_RE = re.compile(r"\bpipx?\b.*\binstall\b")
INLINE_ENV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S*)")
SWITCH = "ROMP_SDK_REQUIRE"
FLAG_SPELLING = "-p no:anyio"
FLAG_RE = re.compile(r"(?:^|\s)-p\s+no:anyio(?=\s|$)")

# Invocations that pass the flag and do NOT set the switch, each with the reason that makes that right, keyed (job,
# step name). The reason's premises are CHECKED by ListedInvocations below, not read: a listing whose premise stops
# holding goes red there, so the list stays a rule and not a roster. A step without a name cannot be listed: the
# stale-entry check needs a name to find. A name two pytest-running steps of one job share is `ambiguous` and red
# until one is renamed (2026-09-21; GitHub Actions does not require unique step names, and a second step of a listed
# name inherited the listing).
SWITCH_LISTED = {
    ("vscode-extension", "Browser-backed served-page tests (pytest)"): (
        "the switch declares that the interpreter running pytest has the SDK the Python job's install step put there, "
        "and this job installs none (its pip line names pip, pytest, pytest-timeout and cryptography; run 35535192879's "
        "served step installed nine packages, no SDK), so setting it would declare something untrue; and its two globs "
        "collect no module that spells the switch's name, nor does any helper module under tests/ they could import, so "
        "the switch would change nothing there today. Premises checked: no SDK install in the job's run blocks; no "
        "collected or helper file under tests/ spells the switch's name (keyed on the spelling in the file's text, not on "
        "an environment read)."),
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


def _shell_commands(text):
    """The commands of one shell line, in order, each stripped, empty ones dropped: the line split at its operators
    outside quotes (`&&`, `||`, `;`, `|`, a lone `&`; not the `&` of a redirection, `2>&1`, `>&2`, `&>`), at a `(` or
    `)` that is a subshell's own boundary (`$(...)` is kept whole, at any depth), and cut at an unquoted `#` at the
    start or after whitespace (a comment: what follows it is not a command's arguments, so a flag spelled in a comment
    is not passed). A single-quoted or double-quoted span holds no operator and no comment; a backslash outside single
    quotes escapes the next character. Word splitting is not attempted: the caller reads each command's text."""
    out, cur, i, n = [], [], 0, len(text)
    quote, depth = None, 0
    while i < n:
        ch = text[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                cur.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            cur.append(ch)
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            cur.append(text[i:i + 2])
            i += 2
            continue
        if ch == "#" and (i == 0 or text[i - 1] in " \t"):
            break
        if text.startswith("$(", i):
            depth += 1
            cur.append("$(")
            i += 2
            continue
        if depth:
            depth -= ch == ")"
            cur.append(ch)
            i += 1
            continue
        if text.startswith(("&&", "||"), i):
            out.append("".join(cur))
            cur = []
            i += 2
            continue
        if ch in ";|()" or (ch == "&" and (i == 0 or text[i - 1] not in "<>") and text[i + 1:i + 2] != ">"):
            out.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    out.append("".join(cur))
    return [c for c in (c.strip() for c in out) if c]


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
    itself: the scopes GitHub Actions merges, later overriding earlier), args (the command's own arguments: the rest
    of ITS command, the line split into commands at its operators and cut at a comment first by _shell_commands, so a
    line running two pytest commands is two invocations at one line and a flag in the next command or in a comment is
    not this one's), run (the step's whole run text), job_run (every run text in the job) and cwd (the step's
    working-directory, else the job's default, else None) and namesakes (the file lines of the pytest invocations in
    OTHER steps of the same job that carry this step's name: GitHub Actions does not require unique step names, and
    the listing and every report here key on (job, step name), so a shared name is `ambiguous` in verdict and red
    until one step is renamed; empty for a unique name and for an unnamed step, which cannot be listed); plus, for a
    command that mentions pytest without being one the parser reads or a pip install line, a dict with `unparsed` set
    to the reason and args None.
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
                base = {"job": job, "step": step, "line": at, "run": run_text, "cwd": cwd, "cmd": cmd, "step_index": k}
                if unreadable:
                    if not PIP_INSTALL_RE.search(cmd):
                        parsed.append(dict(base, env=dict(env), args=None, unparsed=unreadable))
                    continue
                for command in _shell_commands(cmd):
                    if not PYTEST_WORD_RE.search(command):
                        continue
                    hit = PYTEST_CMD_RE.match(command)
                    if hit:
                        inv_env = dict(env)
                        inv_env.update(INLINE_ENV_RE.findall(hit.group("env")))
                        parsed.append(dict(base, env=inv_env, args=hit.group("args"), unparsed=None))
                    elif not PIP_INSTALL_RE.search(command):
                        parsed.append(dict(base, env=dict(env), args=None, unparsed="a form the parser does not read as a command"))
        for inv in parsed:
            inv["job_run"] = "".join(job_runs)
            inv["namesakes"] = sorted(o["line"] for o in parsed if o["step"] == inv["step"] and o["step_index"] != inv["step_index"]
                                      and inv["step"] != UNNAMED)
        found.extend(parsed)
    return found


def invocations_by_key(found):
    """{(job, step name): [invocations, in file order]} over the parsed invocations (unparsed rows left out): every
    invocation under a key is kept, so a check over a listed key sees each pytest line of the step (until 2026-09-21
    ListedInvocations built a dict of one invocation per key, which kept the last and checked the premises on it alone)."""
    out = {}
    for inv in found:
        if not inv["unparsed"]:
            out.setdefault((inv["job"], inv["step"]), []).append(inv)
    return out


def verdict(inv):
    """'ok': the args carry -p no:anyio and the env sets ROMP_SDK_REQUIRE to 1; 'listed': the flag, no switch, and
    (job, step) in SWITCH_LISTED; 'unparsed': a pytest mention the parser did not read as a command; 'ambiguous': a
    named step whose name another pytest-running step of the job shares, so the (job, step name) key names two steps
    (red whatever the invocations carry: a listing under that key would excuse the other step too); 'unlisted':
    anything else, the failure this check exists for (the flag missing has no listing that excuses it)."""
    if inv["unparsed"]:
        return "unparsed"
    if inv["namesakes"]:
        return "ambiguous"
    if not FLAG_RE.search(inv["args"]):
        return "unlisted"
    if inv["env"].get(SWITCH) == "1":
        return "ok"
    if (inv["job"], inv["step"]) in SWITCH_LISTED:
        return "listed"
    return "unlisted"


def stale_listings(found, table=None):
    """The entries of `table` (SWITCH_LISTED by default) that name no pytest invocation among `found`, or name the
    unnamed placeholder, each described: a stale entry is a reason with no subject (the step renamed or removed and
    the list not following), and a listing needs a name to be found by. Keyed on (job, step name) against the
    invocations' keys. Run against what it refuses in PopulationCheckReds (2026-09-21; before that the check had no
    case supplying a stale or an unnamed key)."""
    table = SWITCH_LISTED if table is None else table
    keys = {(i["job"], i["step"]) for i in found}
    out = []
    for key in table:
        if key[1] == UNNAMED:
            out.append("%r: SWITCH_LISTED lists an unnamed step: give the step a name: to list it by" % (key,))
        elif key not in keys:
            out.append("%r: SWITCH_LISTED names a step that is not a pytest invocation in the workflow (keyed on the job key "
                       "and the step's name: line): renamed or removed, drop or fix the entry" % (key,))
    return out


def _describe(inv):
    """The offender, named: job, step, file line, and what it lacks. The flag half keys on the SPELLING `-p no:anyio`
    (one space) in the command's own arguments; the switch half on the merged env reading exactly 1."""
    if inv["unparsed"]:
        return "%s / %r (ci.yml line %d): mentions pytest in a run line the parser does not read as a command (%s): %r" % (
            inv["job"], inv["step"], inv["line"], inv["unparsed"], inv["cmd"].strip())
    if inv["namesakes"]:
        return ("%s / %r (ci.yml line %d): another step named %r in this job runs pytest too (ci.yml line%s %s); the listing "
                "and this report key on (job, step name), so the name is ambiguous: rename one" % (
                    inv["job"], inv["step"], inv["line"], inv["step"], "s" if len(inv["namesakes"]) > 1 else "",
                    ", ".join(str(l) for l in inv["namesakes"])))
    lacks = [w for w, ok in (("%s (keyed on that spelling, one space, in the command's arguments)" % FLAG_SPELLING,
                              bool(FLAG_RE.search(inv["args"]))),
                             ("%s=1 (keyed on the merged workflow, job, step and inline env reading 1)" % SWITCH,
                              inv["env"].get(SWITCH) == "1")) if not ok]
    return "%s / %r (ci.yml line %d): env %s=%r, args %r; lacks %s" % (
        inv["job"], inv["step"], inv["line"], SWITCH, inv["env"].get(SWITCH), inv["args"].strip(), " and ".join(lacks) or "nothing")


def switch_spellers(directory):
    """The *.py files directly under `directory` whose TEXT spells ROMP_SDK_REQUIRE, as realpaths: keyed on the
    spelling, docstrings and comments included, not on an environment read. A module that reads the switch under a
    name it assembles (os.environ.get("ROMP_" + "SDK_REQUIRE")) is outside this read, and the message that uses this
    says so; a module that only mentions the name is inside it, which is why tests/sdk_blocker.py's docstring does
    not spell it. Run against a docstring-only speller and an indirect reader in ListedInvocations (2026-09-21)."""
    out = set()
    for path in glob.glob(os.path.join(directory, "*.py")):
        with open(path, encoding="utf-8") as f:
            if SWITCH in f.read():
                out.add(os.path.realpath(path))
    return out


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
        bad = [_describe(i) for i in self.found if verdict(i) in ("unlisted", "unparsed", "ambiguous")]
        self.assertEqual(bad, [], "pytest invocations in ci.yml that lack %s (keyed on that spelling), or set no %s=1 in "
                         "the env Actions merges for them (workflow, job, step, inline) without an entry in SWITCH_LISTED, "
                         "or that the parser could not read as a command (red until read), or whose step name another "
                         "pytest-running step of the job shares (red until one is renamed):\n  " % (FLAG_SPELLING, SWITCH)
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
        # listing needs a name to be found by, so the unnamed placeholder is refused as a key (stale_listings; run
        # against a stale and an unnamed key in PopulationCheckReds)
        self.assertEqual(stale_listings(self.found), [], "SWITCH_LISTED carries an entry that names no pytest invocation "
                         "in the workflow, or an unnamed step (keyed on the job key and the step's name: line)")


class ListedInvocations(unittest.TestCase):
    """The premises of each SWITCH_LISTED reason, checked against the tree, so the list stays a rule and not a roster.
    Over EVERY invocation under the listed key (invocations_by_key): a step may run pytest on two lines, and each is
    the listing's subject; the key names one step, since a name two steps share is `ambiguous` in verdict and red in
    PytestPopulation."""
    def setUp(self):
        self.by_key = invocations_by_key(pytest_invocations(open(WF).read()))
        self.served = self.by_key[SERVED_STEP]
        self.assertTrue(self.served, "no invocation under the served step's key")

    def test_the_served_step_passes_the_flag_its_listing_excuses_only_the_switch(self):
        for inv in self.served:
            self.assertTrue(FLAG_RE.search(inv["args"]), "the served step's pytest line %d lacks %s (keyed on that "
                            "spelling): the listing covers the switch alone; the flag is accepted where anyio is absent and "
                            "has no exemption" % (inv["line"], FLAG_SPELLING))

    def test_the_served_steps_job_installs_no_sdk(self):
        # keyed on the install's names in the job's run blocks; an install by a `uses:` action is outside this read
        for token in SDK_INSTALL_TOKENS:
            self.assertNotIn(token, self.served[0]["job_run"], "a run block of the vscode-extension job names %r: the job's "
                             "interpreter may now have the SDK, so the served step's listing for the switch is no longer "
                             "true; set %s=1 there and drop the entry" % (token, SWITCH))

    def test_the_served_step_does_not_set_the_switch(self):
        # a listed step that sets the switch is a contradiction: either it is compliant, or it is listed
        for inv in self.served:
            self.assertNotIn(SWITCH, inv["env"], "the served step's pytest line %d sets %s: it declares an SDK it does not install" % (inv["line"], SWITCH))

    def test_the_served_steps_globs_collect_no_module_that_spells_the_switch(self):
        # keyed on the switch's name spelled in the file's text (switch_spellers), not on an environment read: the
        # modules the step's globs collect, plus every non-test module under tests/ (conftest, __init__, the helpers a
        # collected module may import); a reader that spells the name indirectly is outside this read, and the
        # message says what the check keys on (until 2026-09-21 it said the module "reads" the switch, which a
        # docstring that spells the name does not)
        readers = switch_spellers(HERE)
        self.assertIn(os.path.realpath(__file__), readers, "the census missed this file, which spells (and reads) the switch")
        helpers = {os.path.realpath(p) for p in glob.glob(os.path.join(HERE, "*.py")) if not os.path.basename(p).startswith("test_")}
        self.assertIn(os.path.realpath(os.path.join(HERE, "conftest.py")), helpers, "the helper census missed conftest.py")
        collected = set()
        for inv in self.served:
            for pattern in _positional_paths(inv):
                collected.update(os.path.realpath(p) for p in glob.glob(pattern))
        self.assertTrue(collected, "the served step's globs resolve to no file at the repo root: %r" % [i["args"] for i in self.served])
        hit = sorted(os.path.relpath(p, ROOT) for p in readers & (collected | helpers))
        self.assertEqual(hit, [], "the served step collects or could load a module that spells %s in its text (keyed on the "
                         "spelling, docstrings and comments included, not on an environment read; a reader that spells the "
                         "name indirectly is outside this read), and it runs without the switch: %s" % (SWITCH, hit))

    def test_the_spelling_check_names_a_docstring_that_spells_the_switch_and_misses_an_indirect_reader(self):
        # the check against what it refuses, and its stated limit, over a scratch directory: a served-named module whose
        # docstring alone spells the name is named (it reads nothing, which is why the message says "spells"); a module
        # that reads the switch under an assembled name is not, and the message says such a reader is outside the read
        d = tempfile.mkdtemp(prefix="switch-spellers-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "test_zz_synthetic_served.py"), "w") as f:
            f.write('"""A synthetic served module whose docstring spells %s and whose code reads no environment."""\n' % SWITCH)
        with open(os.path.join(d, "test_plain_served.py"), "w") as f:
            f.write("import os\nVALUE = os.environ.get('ROMP_SERVED_TESTS_REQUIRE')\n")
        with open(os.path.join(d, "conftest.py"), "w") as f:
            f.write("import os\nINDIRECT = os.environ.get('ROMP_' + 'SDK_' + 'REQUIRE')\n")
        self.assertEqual({os.path.basename(p) for p in switch_spellers(d)}, {"test_zz_synthetic_served.py"})


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
        return [i for i in pytest_invocations(src) if verdict(i) in ("unlisted", "unparsed", "ambiguous") and (i["job"], i["step"]) not in self.base]

    def found_live(self):
        return pytest_invocations(self.src)

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

    def test_a_stale_listing_and_an_unnamed_listing_are_named_by_the_stale_entry_check(self):
        # the check against what it refuses: a key naming a step the workflow no longer has (renamed), and the unnamed
        # placeholder as a key; the live entry beside them stays unnamed by the check
        found = self.found_live()
        self.assertEqual(stale_listings(found), [], "the live table has no stale entry")
        with mock.patch.dict(SWITCH_LISTED, {("vscode-extension", "Renamed (pytest)"): "synthetic stale entry",
                                             ("shell", UNNAMED): "synthetic unnamed entry"}):
            stale = stale_listings(found)
        self.assertEqual(len(stale), 2, stale)
        self.assertIn("('vscode-extension', 'Renamed (pytest)'): SWITCH_LISTED names a step that is not a pytest invocation", stale[0])
        self.assertIn("renamed or removed", stale[0])
        self.assertIn("('shell', '(unnamed step)'): SWITCH_LISTED lists an unnamed step", stale[1])
        # and with a scratch table alone, so the live entry is not what makes it green
        self.assertEqual(stale_listings(found, {SERVED_STEP: "x"}), [])
        self.assertEqual(len(stale_listings(found, {("python", "Renamed pytest"): "x"})), 1)

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

    def _with_step_in_last_job(self, step_text, src=None):
        # appended at the end of the file: the vscode-extension job is the file's last, so the step joins it
        src = self.src if src is None else src
        self.assertEqual(re.findall(JOB_RE, _top_sections(src)["jobs"][0][1])[-1], SERVED_STEP[0], "the last job moved: re-anchor this case")
        return src.rstrip("\n") + "\n" + step_text

    def test_a_second_step_of_a_listed_name_in_its_job_is_ambiguous_and_both_are_named(self):
        # GitHub Actions does not require unique step names, and the listing keys on (job, step name): until 2026-09-21 a
        # second step named like the served step, in its job, inherited the listing (verdict listed, flag on and no
        # switch, nothing red; probed in memory), and ListedInvocations' dict of invocations by key kept the last one
        # alone, so the premises were checked on it and never on the first. Now a name two steps of one job share
        # among the pytest invocations is `ambiguous`, red whatever else the invocations carry, and each is named with
        # the other's line: rename one.
        dup = "      - name: %s\n        run: python -m pytest tests/test_other.py -q -p no:anyio\n" % SERVED_STEP[1]
        src = self._with_step_in_last_job(dup)
        served = [i for i in pytest_invocations(src) if (i["job"], i["step"]) == SERVED_STEP]
        self.assertEqual([verdict(i) for i in served], ["ambiguous", "ambiguous"], [_describe(i) for i in served])
        self.assertEqual(sorted(i["line"] for i in served), sorted(served[0]["namesakes"] + served[1]["namesakes"]))
        for i in served:
            self.assertIn("another step named %r in this job runs pytest too" % SERVED_STEP[1], _describe(i))
            self.assertIn("rename one", _describe(i))
        bad = [i for i in pytest_invocations(src) if verdict(i) in ("unlisted", "unparsed", "ambiguous")]
        self.assertEqual([(i["job"], i["step"]) for i in bad], [SERVED_STEP, SERVED_STEP], "the population check names both")
        # the live file: the served step is the one step of its name, so it is listed, not ambiguous
        live = [i for i in self.found_live() if (i["job"], i["step"]) == SERVED_STEP]
        self.assertEqual([verdict(i) for i in live], ["listed"])
        # two pytest lines in ONE step's block are one step: read as two invocations, neither ambiguous
        two, first = self._with_step_in_shell_job("      - name: Two lines (pytest)\n        run: |\n          python -m pytest tests/test_a.py -q\n          python -m pytest tests/test_b.py -q -p no:anyio\n")
        new = self._new(two)
        self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + 2, "unlisted"), (first + 3, "unlisted")], [_describe(i) for i in new])
        self.assertEqual([i["namesakes"] for i in new], [[], []])
        # two unnamed steps are not namesakes: an unnamed step cannot be listed, and each is named at its own line
        unnamed, first = self._with_step_in_shell_job("      - run: python -m pytest tests/test_a.py -q\n      - run: python -m pytest tests/test_b.py -q\n")
        self.assertEqual([verdict(i) for i in self._new(unnamed)], ["unlisted", "unlisted"])

    def test_every_invocation_under_a_listed_key_is_kept_for_the_premise_checks(self):
        # the served step with a second pytest line in its run block, unflagged: the grouping ListedInvocations reads
        # (invocations_by_key) keeps both, so a premise checked over the key sees each, and the second is unlisted
        served_line = [l for l in self.src.splitlines() if l.startswith("          python -m pytest tests/test_*_browser.py")]
        self.assertEqual(len(served_line), 1, served_line)
        src = self.src.replace(served_line[0] + "\n", served_line[0] + "\n          python -m pytest tests/test_other_served.py -q\n", 1)
        by_key = invocations_by_key(pytest_invocations(src))
        self.assertEqual([verdict(i) for i in by_key[SERVED_STEP]], ["listed", "unlisted"], [_describe(i) for i in by_key[SERVED_STEP]])
        self.assertEqual([i["args"].strip() for i in by_key[SERVED_STEP]][1], "tests/test_other_served.py -q")

    def test_a_second_pytest_command_on_the_same_run_line_is_read_and_judged_on_its_own(self):
        # Until 2026-09-21 the command regex took the rest of the line as the first command's arguments, so a second
        # `python -m pytest` on the line was never an invocation, and with no whitespace before the operator (`-q;`,
        # `-q&&`) or with a `#` comment the split never cut, so a flag spelled in the NEXT command or in the comment
        # read as the first command's (probed by execution: `ok`, one invocation, where a red was owed). Now the line
        # is split at its operators first (_shell_commands) and each command is judged alone: two invocations at the
        # same line, the flagged one ok under the job's env and the unflagged one unlisted, whatever the spacing.
        for label, op in (("spaced &&", " && "), ("spaced ;", " ; "), ("unspaced ;", ";"), ("unspaced &&", "&&"),
                          ("spaced ||", " || "), ("a pipe", " | ")):
            with self.subTest(form=label):
                line = "python -m pytest tests/test_a.py -q -p no:anyio%spython -m pytest tests/test_b.py -q" % op
                src = self._with_shell_job_env(self._with_step_in_shell_job("      - name: Two (pytest)\n        run: %s\n" % line)[0])
                new = self._new(src)
                self.assertEqual([(verdict(i), i["args"].strip()) for i in new],
                                 [("ok", "tests/test_a.py -q -p no:anyio"), ("unlisted", "tests/test_b.py -q")],
                                 "%s: two commands on one line are two invocations, each with its own arguments: %r"
                                 % (label, [_describe(i) for i in new]))
                self.assertEqual({src.splitlines()[i["line"] - 1].strip() for i in new}, {"run: " + line}, "both at the line that holds them")
                self.assertIn("lacks -p no:anyio", _describe(new[1]))
        # the first command unflagged and the second flagged, unspaced: the flag is the second's, not the first's
        src, first = self._with_step_in_shell_job("      - name: Two (pytest)\n        run: python -m pytest tests/test_a.py -q;python -m pytest tests/test_b.py -q -p no:anyio\n")
        new = self._new(self._with_shell_job_env(src))
        self.assertEqual([(verdict(i), i["args"].strip()) for i in new], [("unlisted", "tests/test_a.py -q"), ("ok", "tests/test_b.py -q -p no:anyio")])

    def test_a_flag_spelled_in_a_trailing_comment_is_not_the_commands(self):
        line = "python -m pytest tests/test_a.py -q  # TODO pass -p no:anyio once anyio is installed"
        src, first = self._with_step_in_shell_job("      - name: Commented (pytest)\n        run: %s\n" % line)
        new = self._new(self._with_shell_job_env(src))
        self.assertEqual([(verdict(i), i["args"].strip()) for i in new], [("unlisted", "tests/test_a.py -q")],
                         "the comment is cut from the command's arguments: %r" % [_describe(i) for i in new])
        self.assertIn("lacks -p no:anyio", _describe(new[0]))
        # a `#` that is not preceded by whitespace is not a comment (an argument's own character)
        src, first = self._with_step_in_shell_job("      - name: Hash (pytest)\n        run: python -m pytest tests/test_a.py -q -k a#b -p no:anyio\n")
        self.assertEqual([(verdict(i), i["args"].strip()) for i in self._new(self._with_shell_job_env(src))], [("ok", "tests/test_a.py -q -k a#b -p no:anyio")])

    def test_a_redirection_a_quoted_operator_and_a_subshell_keep_the_command_whole(self):
        for label, line, args in (
                ("2>&1 then a pipe to tee", "python -m pytest tests/test_a.py -q -p no:anyio 2>&1 | tee log.txt", "tests/test_a.py -q -p no:anyio 2>&1"),
                ("a quoted ; inside -k", 'python -m pytest tests/test_a.py -q -k "a; b" -p no:anyio', 'tests/test_a.py -q -k "a; b" -p no:anyio'),
                ("a single-quoted && inside -k", "python -m pytest tests/test_a.py -q -k 'a && b' -p no:anyio", "tests/test_a.py -q -k 'a && b' -p no:anyio"),
                ("a subshell", "(cd tests && python -m pytest test_a.py -q -p no:anyio)", "test_a.py -q -p no:anyio"),
                ("a $( ) substitution in an argument", "python -m pytest tests/test_a.py -q --basetemp=$(mktemp -d) -p no:anyio", "tests/test_a.py -q --basetemp=$(mktemp -d) -p no:anyio")):
            with self.subTest(form=label):
                src, first = self._with_step_in_shell_job("      - name: Whole (pytest)\n        run: %s\n" % line)
                new = self._new(self._with_shell_job_env(src))
                self.assertEqual([(verdict(i), i["args"].strip()) for i in new], [("ok", args)],
                                 "%s: one command, its arguments whole: %r" % (label, [_describe(i) for i in new]))
        # the flag inside a quoted argument is not the flag: keyed on the spelling in the command's own arguments
        src, first = self._with_step_in_shell_job('      - name: Quoted (pytest)\n        run: python -m pytest tests/test_a.py -q -k "-p no:anyio"\n')
        self.assertEqual([verdict(i) for i in self._new(self._with_shell_job_env(src))], ["unlisted"])

    def test_the_command_split_reads_operators_quotes_comments_and_redirections(self):
        for line, segments in (
                ("a && b || c ; d | e & f", ["a", "b", "c", "d", "e", "f"]),
                ("a&&b;c|d", ["a", "b", "c", "d"]),
                ("a 2>&1 | b >&2 &> log", ["a 2>&1", "b >&2 &> log"]),
                ("a 'x; y' \"p && q\" ; b", ["a 'x; y' \"p && q\"", "b"]),
                ("a \\; b", ["a \\; b"]),
                ("a --x=$(b; c) ; d", ["a --x=$(b; c)", "d"]),
                ("(a && b) ; c", ["a", "b", "c"]),
                ("a -q  # b ; c", ["a -q"]),
                ("# a ; b", []),
                ("a -k x#y ; b", ["a -k x#y", "b"]),
                ("", [])):
            with self.subTest(line=line):
                self.assertEqual(_shell_commands(line), segments)

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


# ---------------------------------------------------------------------------------------------------------------------
# The launcher census (round 3's ruling, 2026-09-20; item 5 of the module docstring): every pytest the suite itself
# spawns passes -p no:anyio. The workflow's flag blocks anyio's plugin in the step's own process; a pytest child a test
# spawns is a new pytest process in the same interpreter, where the SDK step installed anyio, and without the flag it
# auto-loads the plugin. At round 3's head one of nine launchers passed the flag, and this module, ci.yml and
# tests/README.md said the cells' plugin set was the box's. The rule now: every argv under tests/ that runs pytest
# passes the flag or is in LAUNCHERS_LISTED with a reason. The population is derived from the modules' syntax by
# child_pytest_launchers (its docstring and _launchers_in's are the rule); the derivation case prints the listing:
#   python -m pytest tests/test_ci_sdk_pin.py -q -p no:cacheprovider -p no:anyio -k ChildPytestLaunchers -rP
# ---------------------------------------------------------------------------------------------------------------------
# a module whose text spells neither can name pytest in no argv and no string; no word boundaries, so the one token
# `-mpytest` counts (until 2026-09-21 the prefilter was `\bpytest\b`, which it does not match, and a module whose only
# spelling was that token was skipped without a parse while _launchers_in read it)
PYTEST_TEXT_RE = re.compile(r"pytest|py\.test")
# a pytest command inside ONE string: `python -m pytest` (any interpreter spelling), or pytest / py.test by name or path,
# at command position (the start of the string, or after whitespace, `;`, `&`, `|` or `(`); or a `pytest.main(` call, an
# in-process pytest inside a `-c` string or a shell string (2026-09-21)
PYTEST_IN_STRING_RE = re.compile(r"(?:^|[\s;&|(])(?:\S*python[0-9.]*\s+-m\s*pytest|(?:\S*/)?(?:pytest|py\.test))(?=\s|$)|\bpytest\.main\s*\(")
PYTHON_NAME_RE = re.compile(r"python[0-9.]*t?(?:\.exe)?")       # a python-named constant: python, python3, python3.12, python3.14t
INTERPRETER_OPTS_WITH_VALUE = ("-X", "-W")                         # CPython options whose value is the next element
SUBPROCESS_FUNCS = ("run", "Popen", "call", "check_call", "check_output")
SHELL_NAMES = ("sh", "bash", "dash", "zsh", "ksh")                 # an argv headed by one of these runs its -c string
FLAG_ARGV = ("-p", "no:anyio")
FLAG_ONE_TOKEN = "-pno:anyio"

# Launchers that lack the flag, each with the reason that makes that right, keyed (file relative to tests/, enclosing
# function name). EMPTY: pytest accepts the flag where anyio is absent, so no launcher has had a reason to lack it. An
# entry must name a live launcher that lacks the flag (ChildPytestLaunchers' stale-entry case), so the table cannot
# outlive its subject.
LAUNCHERS_LISTED = {}


def _str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _text(node):
    """A str constant's text, or an f-string's literal parts joined with its expressions dropped; None for anything else."""
    if isinstance(node, ast.Constant):
        return _str(node)
    if isinstance(node, ast.JoinedStr):
        return "".join(_str(v) or "" for v in node.values)
    return None


def _python_named(tok):
    return tok is not None and PYTHON_NAME_RE.fullmatch(os.path.basename(tok)) is not None


def _argv_command(elts):
    """How an argv literal names pytest: (kind, None) for a launcher, (None, reason) for an argv the census cannot read
    as one and reports unparsed, (None, None) for an argv that is not a pytest command. The property, not a spelling.
    A launcher: `-m pytest` as two elements, or `-mpytest` as one, after an INTERPRETER HEAD through interpreter options
    only. The head is any element that is not a constant (sys.executable, a name, a call, a starred tail) or a
    python-named constant (`python`, `python3.12`, a path to one), wherever it sits, so `uv run python -m pytest` reads;
    the elements between it and the `-m` are constants starting with `-` (-B, -u, -I, -E, -s), a value allowed after -X
    or -W (`-X dev`, `-W error`). Until 2026-09-21 the pair was read at indices 1 and 2 alone, and `python -B -m
    pytest`, the repo's own recipe, was outside the census with no red. Also a launcher: `-m pytest` as the first two
    elements (the interpreter joins the argv elsewhere, an extend), and pytest or py.test by name or path as argv[0].
    Unparsed, after such a head and its options: a `-m` whose next element is not a constant (a module name the census
    cannot read: it may be pytest), or an element that is not a constant right before the constant `pytest` (an option
    the census cannot read: it may be -m). Not a pytest command: a word that is not an option after the head (a script,
    which takes any later `-m pytest` as its own arguments) or another module after -m (`-m unittest`, `-m pip`); and
    `-m` under a head that is neither (`git commit -m msg`, with a constant or a variable for git)."""
    c = [_str(e) for e in elts]
    if len(c) >= 2 and c[0] == "-m" and c[1] == "pytest":
        return "-m pytest (the interpreter joins the argv elsewhere)", None
    if c and c[0] is not None and os.path.basename(c[0]) in ("pytest", "py.test"):
        return "pytest by name or path", None
    for i, head in enumerate(c):
        if not (head is None or _python_named(head)):
            continue
        j = i + 1
        while j < len(c):
            tok = c[j]
            if tok is None:
                if j + 1 < len(c) and c[j + 1] == "pytest":
                    return None, ("an element the census cannot read before `pytest`, after the interpreter at argv[%d] (it "
                                  "may be -m): not read as a launcher until the option is spelled as a constant" % i)
                break
            if tok == "-m":
                if j + 1 < len(c) and c[j + 1] == "pytest":
                    return "<interpreter> -m pytest", None
                if j + 1 < len(c) and c[j + 1] is None:
                    return None, ("a module name the census cannot read after -m, after the interpreter at argv[%d] (it may "
                                  "be pytest): not read as a launcher until the module is spelled as a constant" % i)
                break
            if tok == "-mpytest":
                return "<interpreter> -mpytest", None
            if tok in INTERPRETER_OPTS_WITH_VALUE:
                j += 2
                continue
            if tok.startswith("-"):
                j += 1
                continue
            break
    return None, None


def _passes_flag(elts):
    """Keyed on the argv's CONSTANT elements: `-p` followed by `no:anyio`, or the one token `-pno:anyio`. A flag that
    arrives through a variable or a starred tail is not read and reads as absent: the safe side, and the message says so."""
    c = [_str(e) for e in elts]
    return any((a, b) == FLAG_ARGV for a, b in zip(c, c[1:])) or FLAG_ONE_TOKEN in c


def _launchers_in(src, filename):
    """The launchers, and the pytest commands the census cannot read as an argv, in one module's source. Each is a dict:
    file (the basename; child_pytest_launchers rewrites it relative to tests/), line, func (the enclosing function, else
    '<module>'), kind (_argv_command's answer, "an argv literal" for a literal it reports unparsed, or the call that
    got a string), argv (the constant elements in order, None for an expression), flag (_passes_flag), unparsed (None,
    or why the command was not read as an argv).
    Read: every list or tuple literal in the module whose command is pytest (_argv_command: `-m pytest` after an
    interpreter head through interpreter options, pytest by name or path), wherever it is built: in the subprocess
    call, in a helper that passes it on, in a variable extended later, so a helper-built argv is counted.
    Unparsed, and red in ChildPytestLaunchers until spelled as an argv: a list or tuple literal that may run pytest and
    the census cannot tell (after an interpreter head, a -m whose module name is not a constant, or an element that is
    not a constant right before `pytest`; _argv_command's docstring); a string handed to subprocess.run, Popen, call,
    check_call or check_output (by the module's own names for them), to os.system or os.popen, or through shlex.split,
    whose text spells a pytest command or a `pytest.main(` call (PYTEST_IN_STRING_RE); and an argv handed to those
    calls whose command is not pytest but carries a pytest command inside one element: any element when the head is a
    shell (SHELL_NAMES) run with -c, else a multi-word element (a `-c` string running pytest.main; a lone `pytest`
    element is a package name on a pip line, or an argument). A module that does not parse is one unparsed row. A list
    or tuple on the right of an `in` test is a set of names, not an argv, and is not read. Not read, stated as the
    residual: an argv assembled one element at a time (append calls); a `-c` or shell string that is not a constant; a
    string that spells pytest anywhere else (the suite's synthetic tool-call fixtures spell `uv run pytest -q` by the
    dozen) is data, not a command."""
    base = os.path.basename(filename)
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError as e:
        return [{"file": base, "line": e.lineno or 1, "func": "<module>", "kind": "module", "argv": [], "flag": False,
                 "unparsed": "the module does not parse under this interpreter (%s), so nothing in it was read" % e.msg}]
    parents = {}
    membership = set()          # the right operands of `x in (...)` / `x not in [...]`: sets of names, never an argv
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
        if isinstance(parent, ast.Compare):
            membership.update(id(c) for c, op in zip(parent.comparators, parent.ops) if isinstance(op, (ast.In, ast.NotIn)))

    def func_of(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return node.name
        return "<module>"

    sp_mods, os_mods, shlex_mods, sp_names = {"subprocess"}, {"os"}, {"shlex"}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                {"subprocess": sp_mods, "os": os_mods, "shlex": shlex_mods}.get(a.name, set()).add(a.asname or a.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            sp_names.update(a.asname or a.name for a in node.names if a.name in SUBPROCESS_FUNCS)

    def call_kind(call):
        f = call.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id in sp_mods and f.attr in SUBPROCESS_FUNCS:
                return "subprocess." + f.attr
            if f.value.id in os_mods and f.attr in ("system", "popen"):
                return "os." + f.attr
        if isinstance(f, ast.Name) and f.id in sp_names:
            return "subprocess." + f.id
        return None

    def is_shlex_split(node):
        f = node.func if isinstance(node, ast.Call) else None
        return isinstance(f, ast.Attribute) and f.attr == "split" and isinstance(f.value, ast.Name) and f.value.id in shlex_mods

    out = []

    def row(node, kind, elts, unparsed=None):
        out.append({"file": base, "line": node.lineno, "func": func_of(node), "kind": kind, "argv": [_str(e) for e in elts],
                    "flag": _passes_flag(elts), "unparsed": unparsed})

    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            kind, unparsed = _argv_command(node.elts) if id(node) not in membership else (None, None)
            if kind:
                row(node, kind, node.elts)
            elif unparsed:
                row(node, "an argv literal", [], unparsed)
        elif isinstance(node, ast.Call):
            what = call_kind(node)
            if what is None:
                continue
            arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "args"), None)
            if arg is None:
                continue
            if isinstance(arg, (ast.List, ast.Tuple)):
                if _argv_command(arg.elts) == (None, None):      # a launcher or an unparsed argv has its row from the literal
                    c = [_str(e) for e in arg.elts]
                    shell = bool(c) and c[0] is not None and os.path.basename(c[0]) in SHELL_NAMES and "-c" in c
                    hit = [t for t in c if t and PYTEST_IN_STRING_RE.search(t) and (shell or re.search(r"\s", t))]
                    if hit:
                        row(node, what, [], "a pytest command inside one element of the argv (%r), not read as the command" % hit[0])
            elif is_shlex_split(arg):
                text = _text(arg.args[0]) if arg.args else None
                if text is not None and PYTEST_IN_STRING_RE.search(text):
                    row(node, what, [], "a pytest command in a shlex.split string, not read as an argv")
            else:
                text = _text(arg)
                if text is not None and PYTEST_IN_STRING_RE.search(text):
                    row(node, what, [], "a pytest command in a shell string, not read as an argv")
    return out


def child_pytest_launchers(directory=None):
    """Every launcher and unparsed pytest command under tests/ (every *.py below `directory`, subdirectories included,
    __pycache__ skipped), by _launchers_in; `file` is the path relative to the directory. A module whose text spells
    neither pytest nor py.test is skipped without a parse: it can name pytest in no argv and no string."""
    directory = HERE if directory is None else directory
    out = []
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                src = f.read()
            if not PYTEST_TEXT_RE.search(src):
                continue
            for r in _launchers_in(src, path):
                r["file"] = os.path.relpath(path, directory)
                out.append(r)
    return out


def _describe_launcher(r):
    where = "tests/%s:%d (%s)" % (r["file"], r["line"], r["func"])
    if r["unparsed"]:
        return "%s: %s: %s" % (where, r["kind"], r["unparsed"])
    return "%s: %s %r%s" % (where, r["kind"], r["argv"], "" if r["flag"] else
                            "  lacks -p no:anyio (keyed on the argv's constant elements: `-p` then `no:anyio`, or `-pno:anyio`)")


class ChildPytestLaunchers(unittest.TestCase):
    """Every pytest the suite itself spawns passes -p no:anyio, held on the population of launchers under tests/ (item
    5 of the module docstring). A child pytest is a new pytest process in the cell's interpreter, where the SDK step
    installed anyio; the workflow's flag reaches the step's own process alone, so a launcher without the flag auto-loads
    the plugin there (at round 3's head eight of nine did, and a synthetic broken anyio/pytest_plugin.py in a CI-shaped
    venv red tests in each of the six modules that spawned them, none of which imports the SDK; the same six were green
    with the flag on every launcher, 2026-09-20). The population is derived by child_pytest_launchers, keyed on the argv
    property; the flag check keys on the argv's constant elements and its message says so; a launcher without the flag
    is named with its file, line and enclosing function unless LAUNCHERS_LISTED carries it with a reason, and a listed
    entry whose key names no launcher, or names one that passes the flag, is stale and red. The modules known to spawn
    pytest are asserted present so an empty read is red; there is no count to keep. Red before the eight launchers
    gained the flag: the flag case named them (2026-09-20)."""
    KNOWN_MODULES = {"test_ci_sdk_pin.py", "test_claude_config_floor.py", "test_env_value_redaction.py",
                     "test_key_source_floor.py", "test_served_tests_require.py", "test_session_host.py",
                     "test_supervised_floor.py", "test_tempdir_hygiene.py"}
    _found = None

    @classmethod
    def found(cls):
        if cls._found is None:      # once per process: every module under tests/ that spells pytest is parsed
            cls._found = child_pytest_launchers()
        return cls._found

    def test_the_population_is_derived_and_holds_every_module_known_to_spawn_pytest(self):
        found = self.found()
        self.assertTrue(found, "the census read no launcher under tests/: the walk or its prefilter broke")
        modules = {r["file"] for r in found if not r["unparsed"]}
        self.assertTrue(self.KNOWN_MODULES <= modules, "a module known to spawn pytest was not read by the census (keyed on the "
                        "argv property: a list or tuple literal whose command is pytest): %r" % sorted(self.KNOWN_MODULES - modules))
        print("child pytest launchers under tests/: %d in %d modules" % (len(found), len(modules)))
        for r in found:
            print("  " + _describe_launcher(r))

    def test_every_launcher_passes_the_flag_or_is_listed_and_no_pytest_command_is_unparsed(self):
        bad = [r for r in self.found() if r["unparsed"] or (not r["flag"] and (r["file"], r["func"]) not in LAUNCHERS_LISTED)]
        self.assertEqual([_describe_launcher(r) for r in bad], [], "pytest children the suite spawns without -p no:anyio (in a "
                         "cell each auto-loads anyio's pytest plugin), or pytest commands the census could not read as an argv:\n  "
                         + "\n  ".join(_describe_launcher(r) for r in bad))

    @staticmethod
    def _stale(table, found):
        live = {}
        for r in found:
            if not r["unparsed"]:
                live.setdefault((r["file"], r["func"]), []).append(r["flag"])
        return sorted("%s / %s: %s" % (f, fn, "names no launcher" if (f, fn) not in live else "every launcher there passes the flag; drop the entry")
                      for f, fn in table if (f, fn) not in live or all(live[(f, fn)]))

    def test_a_listed_launcher_must_be_live_and_lack_the_flag(self):
        found = self.found()
        self.assertEqual(self._stale(LAUNCHERS_LISTED, found), [], "LAUNCHERS_LISTED carries an entry whose key (file, function) "
                         "names no launcher, or names launchers that all pass the flag")
        # the check against what it refuses: an entry that names nothing, and one that names a flagged launcher
        some = next(r for r in found if r["flag"] and not r["unparsed"])
        table = {("test_nowhere_synthetic.py", "nothing"): "synthetic stale entry", (some["file"], some["func"]): "synthetic entry on a flagged launcher"}
        self.assertEqual(self._stale(table, found), sorted([
            "test_nowhere_synthetic.py / nothing: names no launcher",
            "%s / %s: every launcher there passes the flag; drop the entry" % (some["file"], some["func"])]))

    def test_a_launcher_is_read_by_the_argv_property_not_by_its_spelling(self):
        cases = (
            ("sys.executable, the flag as two elements", 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:anyio"])\n',
             "<interpreter> -m pytest", True),
            ("a name for the interpreter, the flag as one token", 'import subprocess\npy = "/opt/venv/bin/python3.12"\nsubprocess.run([py, "-m", "pytest", "-pno:anyio", "-q"])\n',
             "<interpreter> -m pytest", True),
            ("a call for the interpreter, no flag", 'import subprocess\nsubprocess.run([str(exe), "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("a tuple argv, a function imported by name", 'import sys\nfrom subprocess import check_output\ncheck_output((sys.executable, "-m", "pytest", "-q"))\n',
             "<interpreter> -m pytest", False),
            ("a starred head", 'import subprocess\nsubprocess.run([*BASE, "-m", "pytest", "-q", "-p", "no:anyio"])\n', "<interpreter> -m pytest", True),
            ("-mpytest as one token", 'import subprocess, sys\nsubprocess.run([sys.executable, "-mpytest", "-q"])\n', "<interpreter> -mpytest", False),
            ("the interpreter joins the argv elsewhere", 'import subprocess, sys\ncmd = [sys.executable]\ncmd.extend(["-m", "pytest", "-q"])\nsubprocess.run(cmd)\n',
             "-m pytest (the interpreter joins the argv elsewhere)", False),
            ("the console script by name", 'import subprocess\nsubprocess.Popen(["pytest", "-q", "-p", "no:anyio"])\n', "pytest by name or path", True),
            ("the console script by path, py.test spelling", 'import subprocess\nsubprocess.call(["/opt/venv/bin/py.test", "-q"])\n', "pytest by name or path", False),
            ("a helper-built argv passed on by a name", 'import subprocess, sys\ndef _run(*a):\n    argv = [sys.executable, "-m", "pytest", "-q", *a]\n    return subprocess.run(argv)\n',
             "<interpreter> -m pytest", False),
            ("the argv built where no subprocess call is in sight", 'import sys\nEXPECTED = [sys.executable, "-m", "pytest", "-q"]\n', "<interpreter> -m pytest", False),
            # interpreter options between the head and -m (the box's own recipe runs `python -B -m pytest`): until
            # 2026-09-21 the pair was read at indices 1 and 2 alone, and each of these was outside the census with no red
            ("-B before -m", 'import subprocess, sys\nsubprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:anyio"])\n', "<interpreter> -m pytest", True),
            ("-X dev before -m", 'import subprocess, sys\nsubprocess.run([sys.executable, "-X", "dev", "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("-W error before -m", 'import subprocess, sys\nsubprocess.run([sys.executable, "-W", "error", "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("-u and -I before -m", 'import subprocess, sys\nsubprocess.run([sys.executable, "-u", "-I", "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("-B before -mpytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-B", "-mpytest", "-q"])\n', "<interpreter> -mpytest", False),
            # a python-named constant as the head, wherever it sits: a wrapper in front of it does not hide the command
            ("a python-named constant head", 'import subprocess\nsubprocess.run(["python3.12", "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("uv run python -m pytest", 'import subprocess\nsubprocess.run(["uv", "run", "python", "-m", "pytest", "-q"])\n', "<interpreter> -m pytest", False),
            ("uv run --python 3.12 python -m pytest", 'import subprocess\nsubprocess.run(["uv", "run", "--python", "3.12", "python", "-m", "pytest", "-q", "-p", "no:anyio"])\n', "<interpreter> -m pytest", True),
        )
        for label, src, kind, flag in cases:
            with self.subTest(form=label):
                rows = _launchers_in(src, "test_synthetic_launcher.py")
                self.assertEqual(len(rows), 1, "%s: one launcher expected, read %r" % (label, [_describe_launcher(r) for r in rows]))
                self.assertIsNone(rows[0]["unparsed"], _describe_launcher(rows[0]))
                self.assertEqual(rows[0]["kind"], kind, _describe_launcher(rows[0]))
                self.assertEqual(rows[0]["flag"], flag, _describe_launcher(rows[0]))
        rows = _launchers_in('import subprocess, sys\nclass T:\n    def _run(self, *a):\n        return subprocess.run([sys.executable, "-m", "pytest", "-q", *a])\n', "t.py")
        self.assertEqual((rows[0]["func"], rows[0]["line"]), ("_run", 4), "the enclosing function and the argv's own line")
        # a flag behind a variable reads as absent, the safe side, and the message says what the check keys on
        rows = _launchers_in('import subprocess, sys\nFLAGS = ["-p", "no:anyio"]\nsubprocess.run([sys.executable, "-m", "pytest", *FLAGS])\n', "t.py")
        self.assertEqual([r["flag"] for r in rows], [False])
        self.assertIn("lacks -p no:anyio (keyed on the argv's constant elements", _describe_launcher(rows[0]))

    def test_a_pytest_command_in_a_string_is_unparsed_and_a_string_elsewhere_is_data(self):
        for label, src, reason in (
                ("a shell string", 'import subprocess\nsubprocess.run("python -m pytest tests -q -p no:anyio", shell=True)\n', "a shell string"),
                ("an f-string", 'import subprocess, sys\nsubprocess.check_call(f"{sys.executable} -m pytest tests -q", shell=True)\n', "a shell string"),
                ("os.system", 'import os\nos.system("pytest tests/test_a.py -q")\n', "a shell string"),
                ("os aliased, a path", 'import os as o\no.popen("/opt/venv/bin/pytest -q")\n', "a shell string"),
                ("subprocess aliased, a shlex.split string", 'import shlex, subprocess as sp\nsp.run(shlex.split("py.test -q tests"))\n', "a shlex.split string"),
                ("a shell -c argv", 'from subprocess import Popen\nPopen(["bash", "-c", "cd /tmp && python3 -m pytest -q"])\n', "inside one element of the argv"),
                ("a shell -c argv, pytest alone", 'import subprocess\nsubprocess.run(["/bin/sh", "-c", "pytest"])\n', "inside one element of the argv"),
                ("a multi-word element under another head", 'import subprocess\nsubprocess.run(["ssh", "host", "python -m pytest -q"])\n', "inside one element of the argv"),
                ("the args keyword", 'import subprocess\nsubprocess.run(args="python3.12 -m pytest -q", shell=True)\n', "a shell string"),
                # pytest.main inside a -c string, and in a shell string: an in-process pytest in a child interpreter
                ("pytest.main in a -c element", 'import subprocess, sys\nsubprocess.run([sys.executable, "-c", "import pytest; pytest.main([\'-q\'])"])\n', "inside one element of the argv"),
                ("pytest.main in a shell string", 'import subprocess\nsubprocess.run("python -c \'import pytest; pytest.main()\'", shell=True)\n', "a shell string"),
                # after an interpreter head, a -m whose module is not a constant may be pytest, and an element that is not a
                # constant before `pytest` may be -m: the census cannot tell, so each is red until spelled (2026-09-21)
                ("-m then a name", 'import subprocess, sys\nmod = "pytest"\nsubprocess.run([sys.executable, "-m", mod, "-q"])\n', "a module name the census cannot read after -m"),
                ("-B, -m then a name", 'import subprocess, sys\nmod = "pytest"\nsubprocess.run([sys.executable, "-B", "-m", mod, "-q"])\n', "a module name the census cannot read after -m"),
                ("a name then pytest", 'import subprocess, sys\nflag = "-m"\nsubprocess.run([sys.executable, flag, "pytest", "-q"])\n', "an element the census cannot read before `pytest`")):
            with self.subTest(form=label):
                rows = _launchers_in(src, "t.py")
                self.assertEqual(len(rows), 1, "%s: one unparsed row expected, read %r" % (label, [_describe_launcher(r) for r in rows]))
                self.assertIn(reason, rows[0]["unparsed"] or "", _describe_launcher(rows[0]))
                self.assertIn("not read as", _describe_launcher(rows[0]))
        # data, not commands: a string that spells pytest outside a subprocess or os call (the suite's synthetic tool-call
        # fixtures spell `uv run pytest -q` by the dozen), a pip line, and a module that never spells pytest
        self.assertEqual(_launchers_in('turn = {"name": "Bash", "input": {"command": "uv run pytest -q"}}\nbash("uv run pytest -q")\n'
                                       'self._bash_turn(0, "pytest -q")\nnote = "run python -m pytest -q first"\n', "t.py"), [])
        self.assertEqual(_launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pip", "install", "pytest", "anyio"])\n', "t.py"), [])
        self.assertEqual(_launchers_in('import subprocess\nsubprocess.run(["ssh", "host", "pytest"])\n', "t.py"), [], "a lone element under a non-shell head is an argument")
        # -m under an interpreter head names another module; -m under any other head is that command's own option
        # (git commit -m, with a constant or a variable for git); a script after the head takes -m pytest as ITS arguments;
        # a variable package on a pip line before the word pytest is not an option the census owes
        self.assertEqual(_launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-m", "unittest", "-q"])\n', "t.py"), [], "-m unittest is another module")
        self.assertEqual(_launchers_in('import subprocess\nsubprocess.run(["git", "commit", "-q", "-m", msg])\n', "t.py"), [], "git commit -m is not an interpreter's -m")
        self.assertEqual(_launchers_in('import subprocess\nsubprocess.run([GIT, "commit", "-q", "-m", msg])\n', "t.py"), [], "a word that is not an option ends the interpreter's options")
        self.assertEqual(_launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "tool.py", "-m", "pytest"])\n', "t.py"), [], "a script's own -m pytest")
        self.assertEqual(_launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pip", "install", pkg, "pytest"])\n', "t.py"), [], "a pip line with a variable package")
        self.assertEqual(_launchers_in('import os\nname = "x"\nok = os.path.basename(name) in ("pytest", "py.test")\nbad = name not in ["pytest", "-q"]\n', "t.py"), [],
                         "the right operand of an in test is a set of names, not an argv")
        self.assertEqual(_launchers_in("def f():\n    return 1\n", "t.py"), [])
        # a module the interpreter cannot parse is one unparsed row, never a silent skip
        rows = _launchers_in("def f(:\n    pass\n", "t.py")
        self.assertEqual([(r["kind"], r["flag"]) for r in rows], [("module", False)])
        self.assertIn("does not parse under this interpreter", rows[0]["unparsed"])

    def test_the_walk_parses_a_module_whose_only_pytest_spelling_is_the_one_token_form(self):
        # child_pytest_launchers skips a module without a parse when its text spells no pytest; until 2026-09-21 that
        # prefilter was `\bpytest\b`, which `-mpytest` does not match (no word boundary between m and p), so a module
        # whose only spelling was the one token _argv_command reads was skipped whole: read by _launchers_in, unread by the
        # walk. Keyed on the walk over a scratch directory listing the launcher, with an option before the token too.
        d = tempfile.mkdtemp(prefix="census-walk-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "test_one_token.py"), "w") as f:
            f.write('import subprocess, sys\nsubprocess.run([sys.executable, "-B", "-mpytest", "-q"])\n')
        with open(os.path.join(d, "test_no_pytest.py"), "w") as f:
            f.write('def f():\n    return 1\n')
        rows = child_pytest_launchers(d)
        self.assertEqual([(r["file"], r["kind"], r["flag"], r["unparsed"]) for r in rows],
                         [("test_one_token.py", "<interpreter> -mpytest", False, None)],
                         "the walk must parse a module whose only spelling of pytest is the one token `-mpytest`: %r" % rows)

    def test_a_live_launcher_with_its_flag_removed_is_named_at_its_line(self):
        # the census against what it refuses, on a copy of a live launcher module's text: the flag removed from one
        # launcher's line, the copy names that launcher, at that line, as lacking the flag; the tree is untouched
        found = [r for r in self.found() if r["flag"] and not r["unparsed"] and os.path.basename(r["file"]) in self.KNOWN_MODULES
                 and r["file"] != os.path.basename(__file__)]
        self.assertTrue(found, "no flagged launcher outside this module to strip")
        target = found[0]
        path = os.path.join(HERE, target["file"])
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines(keepends=True)
        line = lines[target["line"] - 1]
        stripped = line.replace('"-p", "no:anyio", ', "", 1) if '"-p", "no:anyio", ' in line else line.replace(', "-p", "no:anyio"', "", 1)
        self.assertNotEqual(stripped, line, "the flag is not spelled on the launcher's own line (%s:%d); re-anchor this case" % (target["file"], target["line"]))
        lines[target["line"] - 1] = stripped
        copy = _launchers_in("".join(lines), path)
        hit = [r for r in copy if r["line"] == target["line"]]
        self.assertEqual([(r["kind"], r["flag"], r["func"]) for r in hit], [(target["kind"], False, target["func"])], [_describe_launcher(r) for r in copy])
        self.assertEqual(sum(1 for r in copy if not r["flag"]), 1 + sum(1 for r in self.found() if r["file"] == target["file"] and not r["flag"]))
        self.assertIn("tests/%s:%d (%s)" % (target["file"], target["line"], target["func"]), _describe_launcher(hit[0]))
        self.assertIn("lacks -p no:anyio", _describe_launcher(hit[0]))


if __name__ == "__main__":
    unittest.main()
