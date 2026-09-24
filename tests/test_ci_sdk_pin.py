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
   GitHub Actions merges for it, as the file writes it (an env: key line of the workflow's env, the job's or the
   step's, in the file's own layout, or a VAR=value prefix on the command; later scopes override earlier; any other
   line that spells the switch is red, below) or is listed in SWITCH_LISTED by (job, step name) with a reason whose premises the test
   checks over every pytest line of the step; an invocation that does neither is named with its job, step and file
   line, and so is one whose step name another pytest-running step of the job shares (`ambiguous`: the key would name
   two steps, and GitHub Actions does not require unique names). The population is derived from
   the file's text by pytest_invocations (its docstring is the rule: `python -m pytest`, `python -mpytest`, a bare
   `pytest` or `py.test` at command position, in a named or unnamed step in the file's own layout, in a single-line,
   quoted (closed on its line), continued, `run: |` or `run: >` scalar, a tag before it read through, backslash
   continuations joined as
   the shell joins them, comment lines and pip installs excluded), and the two invocations the file is known to
   hold, the Python matrix step's Run pytest (the switch and the flag) and the vscode-extension job's served-page
   step (the flag; listed for the switch, since its job installs no SDK), are asserted present, so an empty read is
   red. The flag has no list: the constant pins the SDK alone, its dependency closure resolves fresh on every run (26
   packages on 2026-09-20, the 3.12 cell of run 35518107329), and one of them, anyio, registers a pytest plugin that
   every pytest process a cell runs would otherwise auto-load, the step's own process and every pytest child the
   suite spawns in the same interpreter (item 5 holds the flag on those in the forms its launcher census reads), which
   the box's default run never does and
   tests/README.md's PYTHONPATH recipe would, so the recipe passes the same flag (the SDK step's comment states the
   decision, why, and the measurement behind it); pytest accepts the flag where anyio is absent, so an invocation
   whose interpreter has no anyio today (the served-page step: pip, pytest, pytest-timeout, cryptography) passes it
   too rather than carrying a reason about a pip line that a later package on that line would silently make false.
   The check reads ci.yml's text, and that is its residual. Every line of ci.yml that spells pytest (the word in any
   case ending at a word boundary, py.test, or a `$PYTEST` expansion), outside a comment or a name: key and other than
   a pip install, is read as an invocation or is red, whatever its layout (round 4's ruling, 2026-09-23): the line
   census in PytestPopulation holds each such line to the span of lines the parser read for a row, so a step in a
   layout the parser does not read (steps at indent 4 or 8, `-   name:`, a flow mapping, a quoted or spaced `run` key)
   is red at its pytest line (a line joined to the next by a backslash counts when the joined text spells pytest, joined
   as the shell joins it); a mention the parser reads but not as a command (a wrapper such as `uvx pytest`, a
   `$PYTEST` variable, an option cluster such as `python -Impytest`, an indentation indicator on a block, a
   more-indented line in a folded block, an anchor on the run) is red as `unparsed` until the parser reads it; and a
   line where a job key goes that the parser does not read as one (a quoted key) is red, so no step is read under the
   job above it. A name: key's own line is excused, and nothing else of the name: a name folded or continued onto a
   second line that spells pytest there is red on valid YAML, and the message says to reword it. The check does not
   read YAML anchors, aliases or merge keys, a step written as a flow mapping or flow sequence, a quoted scalar or a
   flow collection continued past the line it opens on, a double-quoted scalar holding a backslash escape, or a block
   scalar header on the line after its key, and fails closed on them rather than model them (the owner's fail-closed
   design, 2026-09-23, and its first verify pass; ci.yml uses none): every anchor (`&cmd`), alias (`*cmd`) and merge
   key (`<<:`) anywhere in ci.yml, every flow mapping or flow sequence holding a run, env or shell key or a name key
   beside another key, every quoted scalar and flow collection that does not close on the line it opens, every
   double-quoted scalar holding a backslash (an escape the parser does not decode: `\n` in a run starts a second
   command), and every `|` or `>` header on the line after its key (the parser folds that block as one command) is red
   at its line (unread_yaml_forms),
   so a run, a step, a steps list or an env reached through an alias is red where it is written, and a key-shaped line
   inside another key's quoted scalar over several lines is red at that scalar's opening line. Outside the check: a
   run line that
   never spells pytest (a `$RUNNER` set elsewhere, `make test`), a pytest run by a script or action a step calls, and
   every other workflow file under .github/workflows/. The flag half
   keys on the spelling `-p no:anyio` with one space, the switch half on the merged value reading exactly 1 (a quoted
   value read verbatim, so `"1 "` is not 1, and a plain value continued on the next line folded as YAML folds it), and
   their messages say so. The switch half reads what the run text does to the variable only by its spelling (round
   4's ruling, 2026-09-23): a step whose run text spells ROMP_SDK_REQUIRE anywhere other than as a VAR=value prefix on
   its pytest command (an unset, export, declare, env -u or assignment, on an earlier line or before the command on
   its own line; a comment too), or whose job's other run texts spell it (a write to $GITHUB_ENV sets it for the steps
   after), is `unparsed`, red until read, since the parser does not run the shell. And every line of ci.yml that spells
   the switch, outside a comment, is an env: key line the merge read (a bare key at its block's first key indent, its
   value on that line and not a block scalar) or lies in a run text the parser read, or the switch census in
   PytestPopulation names it (review round 4's verify, 2026-09-23): an env: written as an alias or a flow mapping, a
   quoted or spaced key, a value continued on the next line or written as a block scalar, a key-shaped line inside
   another key's block scalar (that key's text to YAML), and a step's shell: or a job's defaults that spells the
   switch are each red at their line; a key-shaped line inside another key's quoted scalar over several lines is red
   at that scalar's opening line (unread_yaml_forms, above). Outside
   that read: any write of the switch that does not spell its name, wherever it is written. Among them: one in a
   step's own run text (`env -i`, sudo's reset of the environment, an indirect unset such as `unset "${!ROMP_@}"`, a
   loop over the environment), one in a step's shell: or a job's defaults (`shell: env -i bash -e {0}`), one by a
   script or action a step calls, and one to $GITHUB_ENV (a dump of the environment, a file copied in). The pin below does not
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
   pytest.importorskip reds as a collection error; one whose ONLY skip is an xfail, with a reason or bare, fails the
   run by its exit status (a flipped xfail prints FAILED either way and counts toward the exit status only once the
   report's wasxfail is removed, which the flip in tests/conftest.py does by hasattr, since a bare xfail's is empty;
   alone, so no other skip carries that exit for it); a
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
   (2026-09-21: `__test__ = False` on the class or on the method, the collector listed one item fewer and no
   InstalledVersion item, the loader case 1 passed, exit 0), and the collect-only case is red on both. What neither
   case can be relied on to see is a road that changes what a RUN collects without touching the file, the residual
   stated here and above tests/conftest.py's tuple. The road is a class, and no list closes it: anything that changes
   what the run collects, among them a collect_ignore or collect_ignore_glob, a collection hook in a conftest or plugin
   (pytest_ignore_collect, pytest_collection_modifyitems), an ini file's test-file pattern, testpaths or addopts,
   PYTEST_ADDOPTS, --ignore or --ignore-glob, -k, -m or --deselect, and a module-level __test__ = False. A road that
   drops the whole module takes this census with it (a module-level __test__ = False empties the module's
   collection; the child would list nothing, and never runs); one that drops InstalledVersion and keeps this census
   acts on the run, and the child sees only what reaches it: handed the file as an argument, it collects the file
   whatever python_files says and asks neither collect_ignore nor pytest_ignore_collect about it (2026-09-23, pytest
   9.1.1), and a selection on the run's command line never reaches it. The module renamed or deleted takes the
   census with it (the rename reds the membership case below, the deletion the existence half in
   tests/test_served_tests_require.py). As read on 2026-09-23: none of these is on ci.yml's Run pytest line (no path,
   no -k, no --ignore) or in its env (no PYTEST_ADDOPTS); no conftest in the tree sets collect_ignore or
   collect_ignore_glob or defines a collection hook (tests/conftest.py, the only one, implements two reporting hooks,
   pytest_make_collect_report and pytest_collectreport, which drop nothing); and the repo has no pytest.ini,
   .pytest.ini, pytest.toml, .pytest.toml, pyproject.toml, setup.cfg or tox.ini. Nothing pins that. The belt's
   subject is checked against the tree as well
   (2026-09-21): NeverSkips asserts this file's own basename is in _NEVER_SKIP_FILES as written in tests/conftest.py
   (never_skip_files_as_written there: ast.literal_eval over the text, so a tuple spelled any other way is reported
   as such rather than raising), and tests/test_served_tests_require.py, outside this module, asserts every entry names
   a file under tests/, so a rename of this file reds in both and a deletion reds there; before those two checks a
   copy renamed test_ci_sdk_pin_v2.py ran green with the belt inert, a skip in it a plain skip.
5. The launcher census (ChildPytestLaunchers; round 3's ruling, 2026-09-20). The workflow's flag blocks the plugin in
   the step's own process; a pytest child a test spawns is a new pytest process in the same interpreter, where the SDK
   step installed anyio, and without the flag it auto-loads the plugin (on 2026-09-20, before the launchers gained the
   flag, one of nine passed it, while this docstring, ci.yml and tests/README.md said the cells' plugin set was the
   box's). The rule: every argv
   under tests/ that runs pytest, and every call under tests/ that runs pytest in the calling process, passes
   -p no:anyio or is in LAUNCHERS_LISTED with a reason (empty: pytest accepts the flag where anyio is absent, so no
   launcher has had a reason to lack it), and the population is derived from the modules' syntax by
   child_pytest_launchers, keyed on the argv PROPERTY and not a spelling. It reads three forms (round 4's ruling,
   2026-09-23, added the second and third). A list or tuple literal, wherever it is built (in the call, in a helper
   that passes it on, in a variable extended later), whose command is pytest (`-m pytest`, or `-mpytest` as one token,
   after an interpreter head through interpreter options only, the head an expression or a python-named constant
   wherever it sits, so `python -B -m pytest`, the repo's own recipe, and `uv run python -m pytest` read; `-m pytest`
   as the first two elements; pytest or py.test by name or path as argv[0]; _argv_command's docstring is the rule). The
   positional arguments of asyncio.create_subprocess_exec and of the os.exec and os.spawn l forms (execl, execle,
   execlp, execlpe, spawnl, spawnle, spawnlp, spawnlpe; a spawn form's mode and an e form's env set aside), read as
   that argv. And a call of pytest.main or pytest.console_main, or of _pytest.config's main or console_main, by a name
   the census resolves for it (an import from the module that defines the call, an alias, a star import from such a
   module, a name assigned from one; looked up by scope, as Python looks it up: the call's own scope (for a call in a decorator, a
   default, an annotation, a return annotation or a type parameter of a def or lambda, or in a class's decorators,
   bases or keywords, the scope around that def or class, where Python evaluates it; an annotation deferred from 3.14
   and a type parameter's lazy bound are read too, a row where they may never run), the functions around it with class
   bodies skipped, their global declarations with them, the module; a binding under a global declaration counted at the
   module and one under a nonlocal declaration in the enclosing function that binds the name): a pytest session in the
   calling process, where plugin autoload runs again whatever flag the outer run was given, so its argv, the first
   positional argument or args=, carries the flag itself. The flag check keys on the argv's constant elements (`-p` then
   `no:anyio`, or `-pno:anyio`), so a flag carried by a variable reads as absent, the safe side, and the message says
   so. The modules known to spawn pytest are asserted present, so an empty read is red, and there is no count to keep;
   the derivation case prints the listing (python -m pytest tests/test_ci_sdk_pin.py -q -p no:cacheprovider -p no:anyio
   -k ChildPytestLaunchers -rP). What the census leaves unread is its residual. A pytest command in a constant string
   or f-string written at the call and handed to subprocess (run, Popen, call, check_call, check_output, getoutput,
   getstatusoutput), os.system or os.popen, asyncio.create_subprocess_shell, shlex.split or a shell's -c (a
   `pytest.main(` call included) is `unparsed` and red until it is spelled as an argv, as is an argv that may run
   pytest and the census cannot tell (a `-m` whose module name is not a constant, an element that is not a constant
   right before `pytest`, after an interpreter head), an in-process call whose argv is not a literal (a name, or no
   argument, which reads sys.argv), and a module that does not parse under the running interpreter. Unparsed the same
   way (the owner's fail-closed design, 2026-09-23), a call whose callee's name the resolution cannot resolve: one
   inside a comprehension or generator expression in a class body that binds the name or declares it global (Python
   looks it up past the class there, a scope the census does not model); and, in a module with a star import from a module whose calls the census
   does not read, one through a name the lookup takes to the module, since the census takes only a function scope that
   binds the name as proof that the star import cannot reach it: a name the module binds (the star import may rebind
   it, and the census follows no order; the first verify pass, 2026-09-23, found such a binding read as the module's
   own and passed) or a name no scope binds and no builtin names (the name may come from it); and one through a name a
   function binds by a plain or annotated assignment from a name or an attribute whose root name is one of those,
   followed along a chain of such assignments (the second verify pass, 2026-09-23, found `run = main` in a function,
   main from the star import, read as the function's own and passed). A string anywhere else, or one held in a
   variable or built with %, + or .format, is outside the read, as is an argv assembled one element at a time (append
   calls) and any call, string or in process, reached through a name the census does not resolve (a name bound other
   than by an import or a plain or annotated assignment: tuple unpacking, a walrus, a conditional expression, a
   parameter default; a name imported by name from a module that does not define the call, a helper that re-exports
   pytest.main among them, which the census reads as no launcher, or by a relative import, which binds nothing it reads;
   an attribute of a class or an instance, `T.m` or `self.m`; getattr, importlib or runpy; beside a star import from a
   module the census does not read, a builtin name, read as the builtin, or a module name no scope binds, read as that
   module (subprocess, os, shlex, asyncio, pytest, _pytest), which the star import may rebind, and a name a function
   binds from such a star import's name other than by a plain or annotated assignment from a name or an attribute (from
   a call's result or a subscript, as a parameter or a loop target), read as the function's own; a call in a class body
   through a name the class binds, which the census reads as the class's binding, where the body reads the name past the
   class until that binding runs; among others); and so is every module whose text spells neither pytest nor py.test and
   holds no star import, which the census skips without a parse, so nothing above is read or refused in it (an argv
   there whose -m module name is a name, or whose pytest is spelled through adjacent string literals or an escape, gives
   no row; the second verify pass, 2026-09-23, found the prefilter skipping a star import too, and it now parses one);
   each of those named here has a case holding its outcome, no row. What the flag
   buys, in every pytest process the census and the population check read in which nothing loads the plugin again by its
   entry-point name or its module name (`-p anyio` or `-p anyio.pytest_plugin` after the flag on the line,
   PYTEST_PLUGINS in the environment, plugins= handed to pytest.main; both checks key on the flag's spelling and read
   none of these): anyio's plugin is absent from that process's plugin set as it is from the box's default run's. The
   sets are not equal, and nothing here says they are: the box's default run loads pytest-xdist's two plugins, which no
   cell installs. Verified by execution before this landed: a synthetic broken anyio/pytest_plugin.py in a CI-shaped
   venv (the SDK pinned, the parent under the flag) red tests in each of the six modules that spawned unflagged
   children, none of which imports the SDK, and the same six were green with the flag on every launcher (2026-09-20).

Hermetic: the run block executes in a scratch directory with its own copy of the constant's line, never at the repo
root, and its `python` is a shim that records its arguments; no network, no pip.
"""
import ast
import builtins
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
        # "transitive release" and the anyio plugin (2026-09-20): the constant pins the SDK alone and its dependency closure
        # resolves fresh on every run; one of those packages, anyio, registers a pytest plugin, and a comment that stops
        # saying so lets the pytest environment change again without a word (the line below holds the block itself).
        # The count rule (review round 4, 2026-09-23): each phrase is a spelling unique to the sentence it guards and
        # occurs EXACTLY ONCE in the comment. A phrase that occurs twice lets its sentence go with the pin green: "pytest
        # plugin" gained a second occurrence, and round 1's sentence on anyio's plugin and the flag could be deleted with
        # this case passing. So that sentence is keyed on two spellings of its own, the pin source on its sed and the
        # no-continue-on-error reason on its cryptography clause, in place of the bare words bin/romp-sdk-setup and
        # cryptography, which the comment spells more than once.
        for phrase in ("SDK_TESTED_VERSION", "kernel/session_host.py", "the sed bin/romp-sdk-setup runs over the same line",
                       "not PyPI's latest", "run the host tests on it, move the number", "nothing polls PyPI",
                       "continue-on-error", "the SDK requires cryptography (through mcp's pyjwt[crypto])",
                       "registers a pytest plugin (a pytest11 entry point)", "passes -p no:anyio so it does not",
                       "transitive release"):
            self.assertEqual(self.comment.count(phrase), 1, "the step's comment spells %r %d times, not once (keyed on "
                             "that spelling; each phrase guards one sentence and must be unique to it): a sentence was "
                             "lost, or a second copy of the phrase lets it go unseen" % (phrase, self.comment.count(phrase)))


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
# Its bare twin: @pytest.mark.xfail with no reason sets the report's wasxfail to "", which a truthiness test reads as
# absent. The case over it is what makes the flip's hasattr load-bearing (review round 4, 2026-09-23).
BARE_XFAIL_ONLY = '''
import unittest
import pytest
class OnlyBareXfail(unittest.TestCase):
    @pytest.mark.xfail
    def test_xfail(self):
        self.fail("a bare xfail absorbs this, synthetic")
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
    2026-09-21), and so does its bare twin, whose wasxfail is empty (a delete by truthiness kept it, and only the bare
    case reds on that, 2026-09-23). Synthetic files only; no SDK, no network. Two cases are in-process. The census, two cases: the belt
    reads reports, and a test that is never collected files none, so the one test the belt exists for is pinned in
    a child `pytest --collect-only -q` over this real module, pytest's own collector, whose listing must hold the
    test's node id (present, never a count), and in process by name against unittest's loader over the class. The
    loader is not the collector: UnitTestCase.collect calls it and then gates on __test__ on the class and on each
    method, which the loader never reads, so the in-process case pins the method's name and the child pins its
    collection. The collect-only child runs nothing, so it spawns no grandchild. The membership case: this file's
    own basename is in _NEVER_SKIP_FILES as written in tests/conftest.py, the literal every report is keyed on; the
    existence half of that check, every entry a file under tests/, lives in tests/test_served_tests_require.py,
    outside this module, where a deletion of this file can still red it. The children pass -p no:anyio, as
    every pytest the suite spawns in a form the launcher census reads does (ChildPytestLaunchers holds it on each
    launcher it reads), so in a cell these children leave anyio's plugin out, as the box's default run does, and load
    it again by neither its entry-point name nor its module name (pytest accepts the flag where anyio is absent, as on
    the box venvs)."""
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

    def test_a_bare_xfail_that_is_the_files_only_skip_fails_the_run(self):
        # The case above with no reason on the xfail (review round 4, 2026-09-23). A bare @pytest.mark.xfail sets the
        # report's wasxfail to "", so a flip that deleted it by truthiness kept it, and the run printed FAILED and exited
        # 0 while the reasoned case above, whose wasxfail is non-empty, passed. The exit status is the assertion. With
        # wasxfail empty, _skip_reason falls back to str(longrepr), so the red carries the failure the xfail absorbed.
        rc, out = self._run(self._write("test_ci_sdk_pin.py", BARE_XFAIL_ONLY))
        self.assertNotEqual(rc, 0, "a flipped bare xfail must fail the RUN, not only print FAILED: " + out[-3000:])
        self.assertIn("1 failed", out, "the bare xfail is reported as the one failure: " + out[-3000:])
        self.assertIn("never-skips: test_ci_sdk_pin.py skipped (at call)", out, "the red names the belt and the file: " + out[-3000:])
        self.assertIn("a bare xfail absorbs this, synthetic", out, "...and carries the failure the xfail absorbed, read off "
                      "the longrepr: " + out[-3000:])

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
        # listed one item fewer and no InstalledVersion item while the loader case read 1 passed, exit 0 (2026-09-21). What
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
        # the refusal names the interpreter (review round 4, 2026-09-23: ci.yml, the docstring, tests/README.md and the
        # ledger say so, and with sys.executable dropped from the fail text this module stayed green). The child runs as
        # sys.executable -m pytest, so its sys.executable is this process's
        self.assertIn("(%s)" % sys.executable, out, "the refusal must name the interpreter running pytest: " + out[-3000:])
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
# What the parser reads, and its limits, are stated in pytest_invocations' docstring. A pytest mention it reads but not
# as a command is red as `unparsed`; a pytest mention in a layout it does not read at all gives no row, and the line
# census (pytest_line_census, run in PytestPopulation) reds it: every line of the file that spells pytest, outside a
# comment or a name: key, lies in the span of lines the parser read for a row, or the census names it. A line at the
# jobs' indent that is not a job the parser reads is red too (unread_job_keys), so no step is read under the job above
# it. Until 2026-09-23 the parser's limits were claimed red and a step in YAML's compact list style gave no row at all.
# YAML anchors, aliases and merge keys, a step in flow style, a quoted scalar or flow collection continued past its
# line, a double-quoted scalar holding a backslash escape and a block scalar header on the line after its key are not
# read at all: every one is red at its line
# (unread_yaml_forms, the owner's fail-closed design, 2026-09-23, and its first verify pass), since the real file uses
# none.
# ---------------------------------------------------------------------------------------------------------------------
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):", re.M)                # a column-0 key of the workflow's mapping
JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]*(?:#.*)?\n", re.M)           # a job: a bare key at indent 2 under jobs:
STEP_START_RE = re.compile(r"^      - ", re.M)                                # a step: a list item at indent 6
STEP_KEY_PAD = "        "                                                     # step keys sit at indent 8 once `- ` is spaced
RUN_RE = re.compile(r"^        run:(.*)$", re.M)
BLOCK_INDICATOR_RE = re.compile(r"^[ \t]*([|>])([+-]?)([0-9]?)[ \t]*(#.*)?$")
# YAML node properties before a scalar: an anchor (`&cmd`) and a tag (`!!str`, `!local`, `!<...>`), in either order. A
# plain scalar cannot begin with `&` or `!`, so a leading one is a property; neither changes the scalar's text, and until
# 2026-09-23 one before a block indicator (`run: &cmd |`) kept the block from being read as a block (review round 4's
# verify: it was folded into one command). _step_run sets them aside to split the scalar, reads through a tag, and
# reports a run that carries an anchor as unparsed
NODE_PROPERTIES_RE = re.compile(r"^[ \t]*(?:(?:&[^ \t]+|![^ \t]*)(?:[ \t]+|$))+")
# an env: key's value that is a block scalar: node properties, then `|` or `>` with its chomping and indentation
# indicators; its lines are the key's text, and _env_block reads the key as not clean
ENV_BLOCK_SCALAR_RE = re.compile(r"^(?:(?:&[^ \t]+|![^ \t]*)[ \t]+)*[|>](?:[1-9]?[+-]?|[+-]?[1-9]?)$")
UNNAMED = "(unnamed step)"
# a command that runs pytest: `python -m pytest`, `python3.12 -m pytest`, `python -mpytest` (one token), a bare `pytest`
# or `py.test`, at the START of a command (the run line is split into its commands first, _shell_commands: at `&&`,
# `||`, `;`, `|`, `&`, a subshell's parentheses, whatever the spacing, and cut at a comment), after any inline VAR=value
# prefixes (read into the invocation's env); the command's own arguments are the rest of that command and nothing after
# it. Until 2026-09-21 the regex took the rest of the LINE as the arguments and the split cut only at an operator with
# whitespace before it, so a second `python -m pytest` on the line was never read, and its flag, or one in a trailing
# comment, read as the first command's. A `$PYTEST` variable, `uvx pytest`, `uv run pytest`, an option cluster before
# the module (`python -Impytest`, `python -I -m pytest`) or a wrapper script that spells pytest is NOT read as a
# command; a command that mentions pytest and is neither a match nor a pip install is reported as `unparsed` and reds
# the population test until the parser reads it (a mention in a comment is cut with the comment), so the parser's
# limits fail loud rather than green. A command that never spells pytest (`tox`, `make test`) is no mention at all.
PYTEST_CMD_RE = re.compile(r"^(?P<env>(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*)"
                           r"(?:\S*/)?(?:python[0-9.]*[ \t]+-m[ \t]*pytest|pytest|py\.test)(?=\s|$)(?P<args>.*)$")
# a mention: the word in any case, ending at a word boundary, or py.test, or `$PYTEST...`/`${PYTEST...}`; no boundary
# BEFORE the word, so `-mpytest` and an option cluster such as `-Impytest` count (until 2026-09-23 a leading `\b` kept
# both out: `python -mpytest`, which runs pytest, was neither read nor reported; PYTEST_TEXT_RE below had dropped it on
# 2026-09-21). An identifier that runs on past the word (an env: key PYTEST_ADDOPTS, pytest_args) is no mention unless
# a `$` expands it. A mention that is not a command hit and not a pip install is `unparsed`.
PYTEST_WORD_RE = re.compile(r"pytest\b|\bpy\.test\b|\$\{?pytest", re.I)
# a pip install, keyed on the command's program: pip or pipx (by path, with a version suffix, as `python -m pip` or
# `uv pip`), then `install` after the program's own options, matched at the start of one command. Until 2026-09-23 it
# matched pip and install as words anywhere in the command, so a pytest command whose arguments spelled both (`uvx
# pytest -k "pip and install"`) read as a pip install and gave no row, and the census excused its line (probed).
PIP_INSTALL_RE = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*(?:\S*/)?(?:python[0-9.]*t?[ \t]+-m[ \t]*|uv[ \t]+)?"
                            r"pipx?[0-9.]*(?:[ \t]+-\S+)*[ \t]+install(?=\s|$)")
# a line whose key is `name` (`name:` or `- name:`, the value after a space or nothing): the census's first exclusion,
# applied only when no other key follows on the line (_name_key_alone). A line that merely contains "name:" (a flow
# mapping `- {name: ..., run: ...}`) is not one, and neither is a line of a flow mapping over several lines that opens
# with `name:` and carries `run:` after it (until 2026-09-23 this regex alone excused that line; review round 4's verify)
NAME_KEY_RE = re.compile(r"^[ \t]*(?:-[ \t]+)?name:(?:[ \t]|$)")


def _name_key_alone(line):
    """True when the line's key is `name` (NAME_KEY_RE) and no other key follows on it: after the name, no `:` followed
    by whitespace or the end of the line, and no `:` right after a closed quoted scalar, outside a YAML-quoted scalar
    and a trailing comment. In a block mapping a plain scalar cannot hold `: ` (a `${{ }}` expression is plain text to
    YAML, so not there either), so one after the name is the next key of a flow mapping (`name: x, run: y` on one line
    of a `{ }` written over several), or YAML the runner refuses; and a `:` right after a quoted scalar is YAML's
    JSON-style key (`name: x, "run":y`, whatever follows the colon). A quote opens a quoted scalar only where a scalar
    starts (the value's first character, or the first after `,`, `{` or `[`); elsewhere it is the plain scalar's own
    character (`Don't`), and a `#` after whitespace outside a quoted scalar starts a comment. Keyed on that text, not
    on YAML structure: a name whose quoted value is unterminated on its line reads as alone, since YAML carries the
    value on to the next line."""
    m = NAME_KEY_RE.match(line)
    if not m:
        return False
    rest = line[m.end():]
    i, n, at_start = 0, len(rest), True
    while i < n:
        ch = rest[i]
        if ch in " \t":
            i += 1
            continue
        if ch == "#" and (i == 0 or rest[i - 1] in " \t"):
            break
        if at_start and ch in "'\"":
            j = i + 1
            while j < n:
                if ch == '"' and rest[j] == "\\":
                    j += 2
                    continue
                if rest[j] == ch:
                    if ch == "'" and rest.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            if rest[j + 1:j + 2] == ":":
                return False
            i, at_start = j + 1, False
            continue
        if ch == ":" and (i + 1 == n or rest[i + 1] in " \t"):
            return False
        at_start = ch in ",{["
        i += 1
    return True
# the census's split of a line the parser did not read, for the pip exclusion: at every operator character whatever the
# quoting, so the commands of a YAML-quoted scalar are judged one by one (a split finer than the shell's never hides a
# mention: it can only stand a piece of a pip command alone)
CENSUS_SPLIT_RE = re.compile(r"&&|\|\||[;|&()]")
# what a raw YAML line opens with before its value, stripped from each piece of that split before the pip test: the
# indentation, a list dash or a flow mapping's brace, one key (plain or quoted) and its colon, and an opening quote
YAML_KEY_PREFIX_RE = re.compile(r"""^[ \t]*(?:-[ \t]+)?\{?[ \t]*(?:(?:"[^"]*"|'[^']*'|[A-Za-z0-9_-]+)[ \t]*:[ \t]+)?["']?""")
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
        "served step installed nine packages, no SDK), so setting it would declare something untrue; and no module its "
        "two globs collect spells the switch's name, nor does any non-test module under tests/ or any module those "
        "import (their import statements followed transitively, test_ modules included), so the switch would change "
        "nothing there today. Premises checked: no SDK install in the job's run blocks; no collected, non-test or "
        "imported file under tests/ spells the switch's name (served_load_set; keyed on the spelling in the file's text, "
        "not on an environment read; a module loaded by path or by a computed name is outside the import walk)."),
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


def _env_block(text, env_indent, keys_out=None):
    """The `env:` mapping whose `env:` line sits at `env_indent` spaces: {name: value}, the value's surrounding quotes
    stripped (`"1"` reads as `1`) and a trailing ` # comment` dropped. A quoted value is kept verbatim inside its quotes,
    whitespace included, as YAML keeps it (`"1 "` reads as `1 `, which is not 1; both runtime readers of the switch
    compare with == "1"); only an unquoted plain value is stripped (review round 4, 2026-09-23: the strip reached inside
    quotes, and `"1 "` read as the switch on). Comment and blank lines inside the block are skipped. A value that is a
    `${{ }}` expression is kept as its text, which is never `1`: the safe side. A key is read only at the block's first
    key indent (the owner's fail-closed design, 2026-09-23: until then a key-shaped line at any depth was read as a key,
    so `ROMP_SDK_REQUIRE: "1"` written as a line of another key's `|` block read as the switch on while YAML held it as
    that key's text). A deeper line continues the key above it, and that key is marked as not read clean: a plain
    value's lines are folded with one space, as YAML folds them (`1` then `0` reads `1 0`; until review round 4's
    verify, 2026-09-23, it read `1`); a block scalar's lines (a `|` or `>` value, node properties before it and a
    chomping or indentation indicator after it included: ENV_BLOCK_SCALAR_RE) are its text, never keys, and the
    block-scalar value itself (its indicator, never `1`) makes its key unclean, whatever its lines hold. `keys_out`,
    when a list is given, receives [offset of the key's line in `text`, name, clean] for every key line read, clean
    False for a key whose value runs on past its line or is a block scalar (the switch census, switch_line_census,
    counts only a clean key line as read). Not read at all: an `env:` line that carries anything after the colon but a
    comment (an alias `env: *x`, an anchor, a flow mapping), a line at the key indent this regex does not read as a key
    (a quoted or spaced key), a line less indented than the first key, and the deeper lines after either of those,
    which are that line's value and continue no key read here. A quoted value that runs on past its line
    is not followed, so a key-shaped line inside it reads here as a key; unread_yaml_forms refuses such a value at its
    opening line (the fail-closed design's first verify pass, 2026-09-23)."""
    pad = " " * env_indent
    m = re.search(r"^%senv:[ \t]*(?:#.*)?\n((?:%s .*\n|[ \t]*\n)+)" % (pad, pad), text, re.M)
    out = {}
    keys = [] if keys_out is None else keys_out
    if m:
        pos, last, key_indent = m.start(1), None, None   # last: [name, its entry in keys, a plain value to fold]
        for line in m.group(1).splitlines(keepends=True):
            off, pos = pos, pos + len(line)
            body = line.rstrip("\n")
            if not body.strip():
                continue
            indent = len(body) - len(body.lstrip(" "))
            if body.lstrip().startswith("#"):
                continue
            if key_indent is None:
                key_indent = indent
            km = re.match(r"""^\s*([A-Za-z_][A-Za-z0-9_]*):[ \t]*(?:"([^"]*)"|'([^']*)'|([^#]*?))[ \t]*(?:#.*)?$""", body)
            if km and indent == key_indent:
                double, single, plain = km.group(2), km.group(3), km.group(4)
                out[km.group(1)] = double if double is not None else single if single is not None else plain.strip()
                block = plain is not None and ENV_BLOCK_SCALAR_RE.match(plain.strip()) is not None
                keys.append([off, km.group(1), not block])
                last = [km.group(1), keys[-1], plain is not None and not block]
            elif indent > key_indent:
                if last is not None:
                    if last[2]:
                        out[last[0]] = (out[last[0]] + " " + _comment_cut(body).strip()).strip()
                    last[1][2] = False
            else:
                # a line at the key indent that the regex does not read as a key (a quoted or spaced key, a hyphenated
                # name), or one less indented: the deeper lines after it are its value, not the last key's (the
                # fail-closed design's third verify pass, 2026-09-24: attributed to the key above, `"OTHER-X": |` and
                # its text made a clean `ROMP_SDK_REQUIRE: "1"` above it unclean, and the switch census named that line
                # on valid YAML)
                last = None
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


def _continues(text):
    """True when the shell joins the next line onto this one: the line's last character is a backslash that is not
    itself escaped (an odd run of backslashes at its end). A backslash followed by a space escapes the space and joins
    nothing, and an even run is escaped backslashes (until 2026-09-23 the parser stripped trailing whitespace first and
    joined both). Quotes are not tracked across the line: inside a quote left open, where the shell keeps the backslash
    and the newline as the argument's text, the next line is the same command's either way."""
    return (len(text) - len(text.rstrip("\\"))) % 2 == 1


def _join_continuation(head, tail):
    """The shell's join of a backslash-newline: the backslash and the newline removed and nothing inserted, so
    `no:anyio\\` then `--durations=10` is the one word `no:anyio--durations=10`, and `py\\` then `test` is pytest.
    Where either side has whitespace at the join the words stay apart, and that boundary is written as one space (the
    command's arguments are read as words). Until 2026-09-23 every join inserted a space (review round 4's verify)."""
    head = head[:-1]
    if head[-1:].isspace() or tail[:1].isspace():
        return head.rstrip() + " " + tail.lstrip()
    return head + tail


def _paragraphs(raw):
    """Fold [(offset, line)] the way YAML folds a plain or `>` scalar: consecutive non-blank lines join with one
    space, a blank line ends the paragraph. Returns [(offset of the first line, joined text, offset of the last line)]:
    the last line bounds the span the line census counts as read for a row."""
    out, cur = [], None
    for off, line in raw:
        if line.strip() == "":
            if cur:
                out.append(cur)
            cur = None
        elif cur is None:
            cur = (off, line.strip(), off)
        else:
            cur = (cur[0], cur[1] + " " + line.strip(), off)
    if cur:
        out.append(cur)
    return out


def _step_run(stext):
    """The step's `run:` scalar as shell lines [(offset in stext, text, offset of its last line)] and an `unreadable`
    reason (None when the form is one this parser reads); the last line differs from the first for a folded paragraph
    or a plain scalar continued on later lines. Read: a single-line plain or quoted scalar, with continuation lines
    indented past the key folded onto it (a quoted scalar that runs on past its line, a double-quoted one holding a
    backslash escape, which this split does not decode, and a block header on the line after `run:`, which this split
    would fold as such a continuation, are refused by unread_yaml_forms); a `run: |` literal (with a `-` or `+` chomping indicator: the indicator
    changes trailing newlines only); a `run: >` folded block, each paragraph one command. Node properties before any of
    these (NODE_PROPERTIES_RE) are set aside, since they change no text of the scalar, so the scalar is split into its
    lines as the same scalar without them is: a tag (`!!str`) is read through. Not read, and reported so an invocation
    in the block is `unparsed`: an anchor on the run (`&cmd`: an alias of it, `run: *cmd`, runs the same text in
    another step under that step's env and name, and the alias line never spells pytest, so this parser would read the
    text once, under the wrong step; unread_yaml_forms reds the anchor and every alias at their lines as well); an
    indentation indicator on the block (`|2`); or a line indented deeper than the
    block's first line inside a folded block (YAML keeps its line breaks, which this fold would not). Until 2026-09-23
    a property before a block indicator kept the block from being read as a block, and it was folded into one command
    (review round 4's verify). No `run:`: (None, None)."""
    m = RUN_RE.search(stext)
    if not m:
        return None, None
    props = NODE_PROPERTIES_RE.match(m.group(1))
    lines, unreadable = _run_scalar(stext, m, props.end() if props else 0)
    anchors = re.findall(r"&([^ \t]+)", props.group(0)) if props else []
    if anchors and lines and unreadable is None:
        unreadable = ("an anchor (&%s) on the run: an alias of it elsewhere (*%s) runs this text in another step, under "
                      "that step's env, which the parser does not follow" % (anchors[0], anchors[0]))
    return lines, unreadable


def _run_scalar(stext, m, skip):
    """_step_run's split of the run scalar that RUN_RE matched at `m` into its lines, `skip` characters of node
    properties set aside: (lines, unreadable), as _step_run returns them."""
    rest = m.group(1)[skip:]
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
            return [(o, l.strip(), o) for o, l in content], "an indentation indicator (%s) on the block" % bm.group(0).strip()
        indent = len(content[0][1]) - len(content[0][1].lstrip(" "))
        if style == "|":
            return [(o, l[indent:].rstrip("\n"), o) for o, l in raw], None
        if any(len(l) - len(l.lstrip(" ")) > indent for o, l in content):
            return [(o, l.strip(), o) for o, l in content], "a line indented deeper than the block's first line in a folded block"
        return _paragraphs(raw), None
    first = rest.strip()
    first_off = m.start(1) + skip + (len(rest) - len(rest.lstrip()))
    paras = _paragraphs([(first_off, first)] + raw) if first else _paragraphs(raw)
    if paras and len(paras[0][1]) >= 2 and paras[0][1][0] in "\"'" and paras[0][1][-1] == paras[0][1][0]:
        paras[0] = (paras[0][0], paras[0][1][1:-1], paras[0][2])
    return paras, None


def pytest_invocations(src, read=None, switch_read=None):
    """Every pytest invocation in a workflow's text, as dicts: job, step (the `name:`, else "(unnamed step)"), line (in
    the file) and last_line (the last file line of the command as read: its last backslash continuation, or the last
    line of its folded paragraph; the span line..last_line is what the line census counts as read), env (the
    workflow's env updated by the job's, by the step's, then by VAR=value prefixes on the command
    itself: the scopes GitHub Actions merges, later overriding earlier, each read by _env_block from its env: key
    lines in the file's own layout; switch_line_census reds a spelling of the switch anywhere else), args (the command's own arguments: the rest
    of ITS command, the line split into commands at its operators and cut at a comment first by _shell_commands, so a
    line running two pytest commands is two invocations at one line and a flag in the next command or in a comment is
    not this one's), run (the step's whole run text), job_run (every run text in the job) and cwd (the step's
    working-directory, else the job's default, else None) and namesakes (the file lines of the pytest invocations in
    OTHER steps of the same job that carry this step's name: GitHub Actions does not require unique step names, and
    the listing and every report here key on (job, step name), so a shared name is `ambiguous` in verdict and red
    until one step is renamed; empty for a unique name and for an unnamed step, which cannot be listed); plus, for a
    command that mentions pytest without being one the parser reads or a pip install, and for a pytest command in a
    step whose run text spells ROMP_SDK_REQUIRE other than as a VAR=value prefix on its pytest command, or whose job's
    other run texts spell it (keyed on the spelling, comments included; the env merge reads the declared scopes, and
    an unset, export or assignment in the shell, or a write to $GITHUB_ENV in an earlier step, changes what pytest
    starts with), a dict with `unparsed` set to the reason and args None. `read`, when a list is given, receives {first, last, text} for every command line the
    parser read in a step's run, row or not (pytest_line_census judges the pip exclusion on that text; the switch
    census counts those lines as run text read). `switch_read`, when a list is given, receives {line, job, step, scope,
    clean} for every ROMP_SDK_REQUIRE key line _env_block read in a scope the merge reads (the workflow's env, a job's
    env, a step's env; job and step None where the scope is wider), clean False where the value runs on past the line.
    A text parse over the file's own indentation (top-level keys at column 0, jobs at 2, job keys at 4, steps at 6,
    step keys at 8, env keys and run block lines at 10), the way this file's other pins and tests/test_ci_bats_bound.py
    read it: no YAML library in the test deps. A step in any other layout (steps at indent 4 or 8, `-   name:`, a flow
    mapping, a quoted or spaced `run` key) gives no row here; pytest_line_census reds its pytest line, and
    unread_job_keys a job key this parser does not read. The run forms read are _step_run's; comment lines are skipped;
    a line ending in an unescaped backslash is joined with the next the way the shell joins it (_continues,
    _join_continuation: nothing inserted). Not read, and red at their lines by unread_yaml_forms instead: an anchor,
    an alias, a merge key, a step in flow style, a quoted scalar or flow collection continued past its line, a
    double-quoted scalar holding a backslash escape (this parser reads a quoted run's text as written, and decodes no
    escape), and a block scalar header on the line after its key (this parser would fold the block as a plain scalar).
    Outside this parser by construction: a pytest run by a
    script or action the workflow calls, and a run line that never spells pytest (a `$RUNNER` variable set elsewhere,
    or `make test`)."""
    sections = _top_sections(src)
    assert "jobs" in sections, "ci.yml has no jobs: mapping at column 0: re-anchor this parser"

    def env_of(text, indent, base, scope, job=None, step=None):
        keys = []
        out = _env_block(text, indent, keys)
        if switch_read is not None:
            switch_read.extend({"line": _line_of(src, base + off), "job": job, "step": step, "scope": scope, "clean": clean}
                               for off, name, clean in keys if name == SWITCH)
        return out

    wf_env = {}
    for off, text in sections.get("env", []):
        wf_env.update(env_of(text, 0, off, "workflow"))
    jobs_at, body = sections["jobs"][0]
    found = []
    jobs = list(JOB_RE.finditer(body))
    for i, jm in enumerate(jobs):
        job = jm.group(1)
        jend = jobs[i + 1].start() if i + 1 < len(jobs) else len(body)
        jtext = body[jm.end():jend]
        jbase = jobs_at + jm.end()
        job_env = dict(wf_env)
        job_env.update(env_of(jtext, 4, jbase, "job", job))
        dm = re.search(r"^    defaults:\n      run:\n        working-directory: (.*)$", jtext, re.M)
        job_wd = dm.group(1).strip() if dm else None
        steps = list(STEP_START_RE.finditer(jtext))
        parsed = []
        job_runs = []
        run_spellings, prefix_spellings, step_names = {}, {}, {}
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
            env.update(env_of(stext, 8, sbase, "step", job, step))
            lines, unreadable = _step_run(stext)
            if lines is None:
                continue
            run_text = "".join(t + "\n" for _o, t, _e in lines)
            job_runs.append(run_text)
            run_spellings[k], prefix_spellings[k], step_names[k] = run_text.count(SWITCH), 0, step
            j = 0
            while j < len(lines):
                off, cmd, last = lines[j]
                while _continues(cmd) and j + 1 < len(lines):
                    j += 1
                    cmd = _join_continuation(cmd, lines[j][1])
                    last = lines[j][2]
                j += 1
                at = _line_of(src, sbase + off)
                last_at = _line_of(src, sbase + last)
                if read is not None:
                    read.append({"first": at, "last": last_at, "text": cmd})
                if cmd.lstrip().startswith("#"):
                    continue
                if not PYTEST_WORD_RE.search(cmd):
                    continue
                base = {"job": job, "step": step, "line": at, "last_line": last_at, "run": run_text, "cwd": cwd, "cmd": cmd,
                        "step_index": k}
                if unreadable:
                    # the pip exclusion per command, never per line: `pip install pytest && pytest` in such a block is a
                    # pytest command after a pip one (until 2026-09-23 the whole line was excused by its pip half)
                    if any(PYTEST_WORD_RE.search(c) and not PIP_INSTALL_RE.match(c) for c in _shell_commands(cmd)):
                        parsed.append(dict(base, env=dict(env), args=None, unparsed=unreadable))
                    continue
                for command in _shell_commands(cmd):
                    if not PYTEST_WORD_RE.search(command):
                        continue
                    hit = PYTEST_CMD_RE.match(command)
                    if hit:
                        inv_env = dict(env)
                        prefixes = INLINE_ENV_RE.findall(hit.group("env"))
                        inv_env.update(prefixes)
                        prefix_spellings[k] += sum(1 for name, _value in prefixes if name == SWITCH)
                        parsed.append(dict(base, env=inv_env, args=hit.group("args"), unparsed=None))
                    elif not PIP_INSTALL_RE.match(command):
                        parsed.append(dict(base, env=dict(env), args=None, unparsed="a form the parser does not read as a command"))
        for inv in parsed:
            # what the run block does to the switch (review round 4, 2026-09-23): the env merge above reads the declared
            # scopes alone, so a step whose run text spells the switch anywhere but as a VAR=value prefix on its pytest
            # command (an unset, export, declare, env -u or assignment, on an earlier line or before the command on its
            # own line), or whose job's other run texts spell it (a write to $GITHUB_ENV reaches the steps after it), is
            # unparsed: the parser does not run the shell, so it cannot say what value pytest starts with
            k = inv["step_index"]
            if inv["unparsed"] is None:
                others = [step_names[j] for j in sorted(run_spellings) if j != k and run_spellings[j]]
                if run_spellings[k] > prefix_spellings[k]:
                    inv["unparsed"] = ("the step's run text spells %s other than as a VAR=value prefix on its pytest command "
                                       "(keyed on the spelling, comments included): an unset, export, declare, env -u or "
                                       "assignment there sets what pytest runs with, whatever the env: scopes say" % SWITCH)
                    inv["args"] = None
                elif others:
                    inv["unparsed"] = ("another step of the job spells %s in its run text (%s; keyed on the spelling, "
                                       "comments included): a write to $GITHUB_ENV there sets it for the steps after, "
                                       "whatever the env: scopes say" % (SWITCH, ", ".join(repr(o) for o in others)))
                    inv["args"] = None
            inv["job_run"] = "".join(job_runs)
            inv["namesakes"] = sorted(o["line"] for o in parsed if o["step"] == inv["step"] and o["step_index"] != inv["step_index"]
                                      and inv["step"] != UNNAMED)
        found.extend(parsed)
    return found


def _comment_cut(line):
    """The line up to an unquoted `#` at its start or after whitespace: the comment rule _shell_commands applies (a
    quoted span and a backslash-escaped character hold no comment). Quote-aware, so it only ever keeps more text than
    a blind cut would, the safe side for a census that reds on what remains."""
    quote, i, n = None, 0, len(line)
    while i < n:
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < n:
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "\\" and i + 1 < n:
            i += 2
            continue
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
        i += 1
    return line


def pytest_line_census(src):
    """The line census (round 4's ruling A, 2026-09-23): (the lines that spell pytest and count, [(line, text) of the
    counted lines no row covers]), file lines 1-based. A line counts when PYTEST_WORD_RE matches it with a trailing
    comment cut as _shell_commands cuts one (_comment_cut; a comment line is then empty and never counts), or matches
    one of the commands it belongs to (below: a pytest word split over a backslash continuation counts on each line of
    it), unless one of two exclusions, and no others, applies: its key is `name` and no other key follows on it
    (_name_key_alone: `name:` or `- name:`; never a line that merely contains "name:", nor one that opens with `name:`
    and carries another key after it, a JSON-style `"run":` included, so a flow mapping carrying a run counts on
    whichever line it spells pytest; the exclusion is the key's own line, so a name folded or continued onto a line
    that spells pytest reds there on valid YAML, and the message says to reword it); or it is a pip install, judged
    per shell command and never per line: the line is excused only when every command it belongs to that spells pytest
    is a pip install, so a line that installs pytest and then runs it counts. The commands a line belongs to are the
    text the parser read for it when the parser read it (pytest_invocations' `read`: a pip install continued over two
    lines is one command), else the line itself with its backslash continuations joined as the shell joins them
    (_continues, _join_continuation: nothing inserted, a backslash followed by a space or an escaped backslash joining
    nothing; each continuation line loses up to the first line's indentation, the block indentation YAML strips from a
    literal block's lines), split at every operator character (CENSUS_SPLIT_RE), each piece with a YAML key's prefix
    stripped (YAML_KEY_PREFIX_RE); a pip install is a command whose program is pip (PIP_INSTALL_RE, at the start of
    the command). A counted line is covered when it lies in the
    span of lines the parser read for a row, parsed or unparsed: the row's first line through its last joined
    continuation (line..last_line). Keyed on the span, never the first line alone, which would red a compliant command
    whose pytest word sits on a continuation line. The census keys on the spelling over the whole file, not on YAML
    structure, so a line outside any run that spells pytest (an artifact path, an action's input) counts and reds too:
    the census cannot tell it from a command."""
    read = []
    found = pytest_invocations(src, read)
    covered = set()
    for inv in found:
        covered.update(range(inv["line"], inv["last_line"] + 1))
    read_text = {}
    for entry in read:
        for n in range(entry["first"], entry["last"] + 1):
            read_text[n] = entry["text"]
    lines = src.splitlines()
    cut = [_comment_cut(line) for line in lines]
    counted, uncovered = [], []
    for idx, line in enumerate(lines):
        if _name_key_alone(line):
            continue
        if idx + 1 in read_text:
            commands = _shell_commands(read_text[idx + 1])
        else:
            # the shell's join (_continues, _join_continuation), the parser's own: until the owner's fail-closed design
            # (2026-09-23) this join stripped trailing whitespace and joined after an escaped backslash too, so a pip
            # line ending in `\ ` or `\\` swallowed the pytest line after it, and it joined with a space, so a pytest
            # word split by a continuation was never read. A continuation line loses up to the indentation of the
            # group's first line, the block indentation YAML strips from a literal block's lines
            lo = hi = idx
            while lo > 0 and _continues(cut[lo - 1]):
                lo -= 1
            while hi + 1 < len(lines) and _continues(cut[hi]):
                hi += 1
            pad = len(cut[lo]) - len(cut[lo].lstrip(" "))
            joined = cut[lo]
            for tail in cut[lo + 1:hi + 1]:
                joined = _join_continuation(joined, tail[min(pad, len(tail) - len(tail.lstrip(" "))):])
            commands = [YAML_KEY_PREFIX_RE.sub("", c, count=1).strip() for c in CENSUS_SPLIT_RE.split(joined)]
        mentions = [c for c in commands if PYTEST_WORD_RE.search(c)]
        if not (PYTEST_WORD_RE.search(cut[idx]) or mentions):
            continue
        if mentions and all(PIP_INSTALL_RE.match(c) for c in mentions):
            continue
        counted.append(idx + 1)
        if idx + 1 not in covered:
            uncovered.append((idx + 1, line.strip()))
    return counted, uncovered


def switch_line_census(src):
    """The switch census (review round 4's verify, 2026-09-23; ruling A's shape applied to the switch): (the lines that
    spell ROMP_SDK_REQUIRE and count, [(line, text) of the counted lines the parser read neither as an env: key nor as
    run text]), file lines 1-based. A line counts when it spells the switch's name with a trailing comment cut
    (_comment_cut; a comment line never counts). A counted line is read when it is an env: key line of the switch that
    _env_block read clean in a scope the merge reads (the workflow's env, a job's, a step's: a bare key at the block's
    first key indent, its value on that line and not a block scalar), or when it lies in the run text of a step the
    parser read, whose every spelling of the switch the switch half reads as `unparsed` (pytest_invocations). Anything
    else sets or clears the switch where the merge does not look and reds here: an `env:` written as an alias (`env:
    *x`) or a flow mapping, a quoted or spaced key, a value continued on the next line or written as a block scalar, a
    key-shaped line inside another key's block scalar (that key's text to YAML), a step's `shell:` or a job's `defaults:
    run: shell:` that spells the name, a line in a layout the parser does not read. A key-shaped line inside another
    key's quoted scalar over several lines is read here as a key line, and unread_yaml_forms refuses that scalar at its
    opening line (the fail-closed design's first verify pass). Until 2026-09-23 each of these read
    ok beside a pytest step that ran with the switch at 0, `1 0` or unset. Keyed on the spelling over the whole file, so
    a name: or an if: that spells the switch reds too: rename it. What this census cannot see is a write that does not
    spell the name (module docstring, item 1)."""
    read, switch_read = [], []
    pytest_invocations(src, read, switch_read)
    covered = {e["line"] for e in switch_read if e["clean"]}
    for entry in read:
        covered.update(range(entry["first"], entry["last"] + 1))
    counted, uncovered = [], []
    for idx, line in enumerate(src.splitlines()):
        if SWITCH not in _comment_cut(line):
            continue
        counted.append(idx + 1)
        if idx + 1 not in covered:
            uncovered.append((idx + 1, line.strip()))
    return counted, uncovered


def unread_job_keys(src):
    """(the job keys JOB_RE reads, [(line, text) of the lines where a job key goes that JOB_RE does not read]), file
    lines 1-based. Every line of the first jobs: mapping indented less than four spaces, other than a blank or comment
    line, must be a bare job key at indent 2 with nothing after its colon but a comment (round 4's ruling A (3): the
    ruling's keys at indent 2, and a line at indent 0 to 3 that no column-0 key ends the section at). A quoted key
    (`"build":`), a key carrying its value or an anchor on its line, or a job at another indent is no job to JOB_RE,
    and pytest_invocations reads its steps as the job above's, under that job's name and env: after a job whose env
    sets the switch, a flagged step with no switch of its own read ok (probed, 2026-09-23). Keyed on the line's
    indentation and JOB_RE, not on YAML structure, so a scalar continued at indent 3 or less inside the mapping reds
    too."""
    jobs_at, body = _top_sections(src)["jobs"][0]
    read, unread, pos = [], [], 0
    for k, line in enumerate(body.splitlines(keepends=True)):
        off, pos = pos, pos + len(line)
        text = line.rstrip("\n")
        if k == 0 or not text.strip() or text.lstrip().startswith("#"):
            continue
        if len(text) - len(text.lstrip(" ")) >= 4:
            continue
        jm = JOB_RE.match(text + "\n")
        if jm:
            read.append(jm.group(1))
        else:
            unread.append((_line_of(src, jobs_at + off), text))
    return read, unread


STEP_FLOW_KEYS = ("run", "env", "shell")     # keys that make a flow collection a step's to this check
YAML_FORMS_UNREAD = ("this check does not read YAML anchors, aliases or merge keys, a step written in flow style, a quoted "
                     "scalar or flow collection continued past its line, a double-quoted scalar holding a backslash escape, "
                     "nor a block scalar header on the line after its key")


def _yaml_quote_end(line, i, quote):
    """The index just past the quote that closes a YAML quoted scalar opened before `i`, or None when the line ends
    inside it: a double-quoted scalar's backslash escapes the next character, a single-quoted one's `''` is a quote."""
    n = len(line)
    while i < n:
        ch = line[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            if quote == "'" and line.startswith("''", i):
                i += 2
                continue
            return i + 1
        i += 1
    return None


def unread_yaml_forms(src):
    """The YAML constructs this check refuses rather than reads (the owner's fail-closed design, 2026-09-23): [(line,
    text, what)], file lines 1-based, over every line of ci.yml outside a block scalar's text. Refused: every anchor
    (`&name`), alias (`*name`) and merge key (`<<:`), wherever it sits (a step, a steps list, an env, a run, a name:
    value, a line of its own); and every flow mapping or flow sequence, on one line or over several, holding a key a
    step can carry: `run`, `env` or `shell` (in any case, plain or quoted, a plain key read up to its first colon), or
    `name` beside any other key of its mapping. Until then the parser read none of them and the two censuses excused
    some: an anchor on a name: value aliased by `run: *cmd`, an anchored step or steps list aliased into a job without
    the switch, `env: *x` with its anchor on a line of its own, and a flow mapping over several lines whose name line
    carried a JSON-style `"run":` each read green beside a pytest run without the switch or the flag (the pre-push
    lenses' plants). Refused as well, since the scan reads one line at a time (the fail-closed design's first verify
    pass, 2026-09-23): every quoted scalar and every flow collection that does not close on the line it opens, and
    every double-quoted scalar holding a backslash escape. Until then a plain scalar continued onto a line that opens
    with a quote made the scan read a quoted scalar YAML never opened, so the lines up to the next such quote went
    unread and an anchor or alias there read green (the lenses' env alias, name anchor and anchored step plants each
    behind such a line); a key-shaped line inside another env key's quoted scalar over several lines read as the
    switch on; and a double-quoted run's `\\n` escape started a second pytest command, without the flag, that the
    parser read as part of the first. Refused too, found closing that pass: a block scalar header (`|` or `>`) on the
    line after its key, which the parser folded as a plain scalar, one command, so a first pytest without the flag
    took the second's. The real ci.yml uses none of these, so each is red at its line and never modelled. Keyed on a
    line scan, not a YAML parser: a node starts at a line's first character, after a sequence's `- `, after an explicit
    key's `? ` and a document start marker's `---` (the first verify pass: an anchor or alias after either was not
    read), after a key's colon, and after `[`, `{` or `,` inside a flow collection; a block scalar's lines (every line
    indented past the key, dash or `?` that opened it, on the header's line or, for a header on the next line, the
    line before) are text and are not read, and a refused quoted scalar or flow collection is followed to its close,
    so its later lines are not read as nodes. A `#` inside a flow collection with no space before it (after `[`, `{`,
    `,` or a closing quote) is refused, and the rest of its line is read as a comment, as PyYAML and yaml.v3 read it,
    so the collection is refused as continued past its line and its later lines are read as flow content (the
    fail-closed design's second verify pass, 2026-09-23: until then the scan read that `#` as a scalar and closed the
    collection on its line, and behind it an anchored flow step and its alias, a flow mapping's anchored key and its
    alias, and a flow step whose double-quoted run started a second pytest without the switch or the flag each read
    green). The scan's error runs one way: a line that continues a plain scalar is
    read as if it began a node, so one that opens with `&`, `*`, `<<:`, `|` or `>`, or with a quote or a bracket that
    does not close on the line, is red on valid YAML; reword it."""
    out = []
    block_at = None       # inside a block scalar: its lines are those indented past this column
    quote = None          # a quoted scalar open at the end of the previous line: (quote character, its opening line)
    flow = []             # the open flow collections, outermost first: [bracket, opening line, own keys [(key, line)]]
    expect_key = False    # inside a flow mapping, the next scalar is an entry's key (after `{` or `,`)
    pending = None        # the column of the key, dash or `?` whose node the last content line left to a later line

    def refuse(n, what):
        if (n, what) not in {(o[0], o[2]) for o in out}:
            out.append((n, lines[n - 1].strip(), what))

    def key(text, n, quoted):
        name = (text if quoted else text.split(":")[0]).strip()
        if name == "<<":
            refuse(n, "a merge key (<<)")
        if flow:
            flow[-1][2].append((name.lower(), n))

    def close():
        # each collection is judged on its own keys when it closes, so one nested at any depth is judged too; the
        # name rule is a mapping's (a flow sequence's `name: x` entries are one-pair mappings of their own)
        bracket, _opened, keys = flow.pop()
        kind = "mapping" if bracket == "{" else "sequence"
        steps = [(k, n) for k, n in keys if k in STEP_FLOW_KEYS]
        for k, n in steps:
            refuse(n, "a flow %s holding the key %r" % (kind, k))
        if not steps and bracket == "{" and len(keys) > 1:
            for k, n in keys:
                if k == "name":
                    refuse(n, "a flow mapping holding a name key beside another key")

    lines = src.splitlines()
    for idx, raw in enumerate(lines):
        n = idx + 1
        indent = len(raw) - len(raw.lstrip(" "))
        if block_at is not None:
            if not raw.strip() or indent > block_at:
                continue
            block_at = None
        i, size, start, col, own = 0, len(raw), True, indent, True    # own: no key, dash, `?` or `---` on this line yet
        if quote:
            end = _yaml_quote_end(raw, 0, quote[0])
            if end is None:
                continue
            quote, i, start = None, end, False
        while i < size:
            ch = raw[i]
            if ch in " \t":
                i += 1
                continue
            if ch == "#" and (i == 0 or raw[i - 1] in " \t"):
                break
            if ch == "#" and flow:
                # the loop lands on a `#` in a flow collection only where a node or an indicator goes (a plain scalar
                # holding one is read whole below), and PyYAML and yaml.v3 read it there as a comment though no space
                # precedes it: the rest of the line is that comment, so the collection stays open onto the next lines
                # (the fail-closed design's second verify pass, 2026-09-23)
                refuse(n, "a comment in a flow collection with no space before it")
                break
            if flow and ch in "]}":
                close()
                i, start = i + 1, False
                continue
            if flow and ch == ",":
                i, start, expect_key = i + 1, True, flow[-1][0] == "{"
                continue
            if flow and ch == ":":
                i, start, expect_key = i + 1, True, False
                continue
            if not start:
                if not flow:
                    break                 # the rest of a block-context line after its value: nothing a node starts in
                i += 1
                continue
            if not flow and ch == "-" and raw[i + 1:i + 2] in ("", " ", "\t"):
                col, i, own = i, i + 1, False    # a sequence entry: a block scalar here is text past the dash's column
                continue
            if ch == "?" and raw[i + 1:i + 2] in ("", " ", "\t"):
                col, i, own = i, i + 1, False    # an explicit key: its node starts after the `?`, as a sequence entry's does
                continue
            if not flow and i == 0 and raw.startswith("---") and raw[3:4] in ("", " ", "\t"):
                i, own = 3, False         # a document start marker: a node may start after it on its line
                continue
            if ch in "&*!":
                j = i + 1
                while j < size and raw[j] not in " \t" and not (flow and raw[j] in ",[]{}"):
                    j += 1
                if ch == "&":
                    refuse(n, "an anchor (%s)" % raw[i:j])
                elif ch == "*":
                    refuse(n, "an alias (%s)" % raw[i:j])
                    start = False
                i = j
                continue
            if ch in "[{":
                flow.append([ch, n, []])
                i, start, expect_key = i + 1, True, ch == "{"
                continue
            if ch in "\"'":
                end = _yaml_quote_end(raw, i + 1, ch)
                if end is None:
                    refuse(n, "a quoted scalar continued past its line")
                    quote = (ch, n)
                    break
                if ch == '"' and "\\" in raw[i:end]:
                    refuse(n, "a double-quoted scalar holding a backslash escape")
                opened, text, i, start = i, raw[i + 1:end - 1], end, False
                j = i
                while j < size and raw[j] in " \t":
                    j += 1
                if raw[j:j + 1] == ":" and (flow or raw[j + 1:j + 2] in ("", " ", "\t")):
                    key(text, n, True)
                    i, start, expect_key, col, own = j + 1, True, False, opened, False
                elif flow and expect_key:
                    key(text, n, True)
                    expect_key = False
                continue
            if not flow and ch in "|>":
                if own:
                    # a header on the line after its key: the parser folds such a block as a plain scalar, one command
                    # (the fail-closed design's first verify pass, 2026-09-23), so it is refused; its lines are the
                    # text of the key the last content line left open, past that key's column
                    refuse(n, "a block scalar header on the line after its key")
                    if pending is not None and indent > pending:
                        col = pending
                block_at = col            # a block scalar: its lines are its text
                break
            # a plain scalar: to a key's colon (`: `, or `:` at the end of the line or, in a flow, before an indicator),
            # a comment, the end of the line, or, in a flow, the next indicator
            j = i
            while j < size:
                c = raw[j]
                if c == ":" and (raw[j + 1:j + 2] in ("", " ", "\t") or (flow and raw[j + 1:j + 2] in (",", "[", "]", "{", "}"))):
                    break
                if c == "#" and raw[j - 1] in " \t":
                    break
                if flow and c in ",[]{}":
                    break
                j += 1
            text = raw[i:j]
            if raw[j:j + 1] == ":":
                key(text, n, False)
                i, start, expect_key, col, own = j + 1, True, False, i, False
            else:
                if flow and expect_key and text.strip():
                    key(text, n, False)
                    expect_key = False
                i, start = j, False
        for bracket, opened, _keys in flow:
            refuse(opened, "a flow collection (%s) continued past its line" % bracket)
        if raw.strip() and not raw.lstrip().startswith("#"):
            pending = col if start and not flow and block_at is None and quote is None else None
    return sorted(out)


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
    (job, step) in SWITCH_LISTED; 'unparsed': a pytest mention the parser did not read as a command, or a command whose
    step spells the switch in its run text other than as a prefix on it, or whose job's other steps spell it in theirs
    (pytest_invocations); 'ambiguous': a
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


def _imported_names(tree, package):
    """The module names a parsed file imports that could name a file directly under its directory: every `import` and
    `from ... import` statement anywhere in the tree (a function body included), with `package` (the directory's own
    name, `tests`) taken off the front, so `import name`, `import tests.name`, `from name import x`, `from tests.name
    import x`, `from tests import name`, `from . import name` and `from .name import x` each give `name`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                yield parts[1] if parts[0] == package and len(parts) > 1 else parts[0]
        elif isinstance(node, ast.ImportFrom):
            parts = node.module.split(".") if node.module else []
            if node.level == 0 and parts and parts[0] == package:
                parts = parts[1:]
            if parts:
                yield parts[0]
            elif node.level or node.module:          # `from . import name`, `from tests import name`
                for alias in node.names:
                    yield alias.name


def imported_modules(directory, roots):
    """The files directly under `directory` that the files in `roots` import, followed transitively, as realpaths (the
    import walk, review round 4, 2026-09-23): each file is parsed with ast and every name _imported_names gives is
    resolved to `<directory>/<name>.py` when that file exists; the files found are walked in turn. A test_ module
    counts like any other (a served module imports test_spend_detail as a helper). Outside this read: a module loaded
    by path (load_source over a file) or under a name assembled at run time (importlib.import_module over a computed
    string). A file that does not parse raises, and the check reds on it."""
    package = os.path.basename(os.path.realpath(directory))
    seen, todo = set(), [os.path.realpath(p) for p in roots]
    found = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), path)
        for name in _imported_names(tree, package):
            target = os.path.realpath(os.path.join(directory, name + ".py"))
            if os.path.isfile(target):
                found.add(target)
                todo.append(target)
    return found


def served_load_set(directory, collected):
    """The files directly under `directory` a pytest run over `collected` may load: the collected files; every module
    there not named test_* (conftest.py and __init__.py, which pytest loads, and the helpers); and every module those
    import, test_ modules included, followed transitively (imported_modules). Until 2026-09-23 the set was the first
    two alone, so a test_ module a served module imports (tests/test_spend_modal_headless_served.py imports
    test_spend_detail) was never read for the switch."""
    non_test = {os.path.realpath(p) for p in glob.glob(os.path.join(directory, "*.py"))
                if not os.path.basename(p).startswith("test_")}
    roots = {os.path.realpath(p) for p in collected} | non_test
    return roots | imported_modules(directory, roots)


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
    same way. The check reads the file's text, and proves it read all of it (round 4's ruling A, 2026-09-23): every
    line that spells pytest (PYTEST_WORD_RE), outside a comment or a name: key and other than a pip install, lies in
    the span of lines the parser read for a row, parsed or unparsed, whatever its layout, or the line census names it;
    a mention the parser reads but not as a command is red as unparsed until it is read; every line where a job key
    goes is a job the parser reads, so no step is read under the job above it; and no YAML anchor, alias, merge key,
    step in flow style, quoted scalar or flow collection continued past its line, double-quoted scalar holding a
    backslash escape, or block scalar header on the line after its key appears in the file, each red at its line,
    since the check does not read them (the owner's
    fail-closed design, 2026-09-23, and its first verify pass). Outside the check: a run line that never spells pytest,
    a pytest run by a script or action a step calls, and any other workflow file."""
    def setUp(self):
        self.src = open(WF).read()
        self.found = pytest_invocations(self.src)

    def test_the_population_is_derived_and_holds_the_two_known_invocations(self):
        keys = {(i["job"], i["step"]) for i in self.found}
        self.assertIn(MATRIX_STEP, keys, "the Python matrix step's pytest line was not found (keyed on the job key at "
                      "indent 2 and the step's name: line): %r" % keys)
        self.assertIn(SERVED_STEP, keys, "the served-page step's pytest line was not found (keyed on the job key at "
                      "indent 2 and the step's name: line): %r" % keys)

    def test_every_line_that_spells_pytest_lies_in_a_row_the_parser_read(self):
        # the line census (round 4's ruling A, 2026-09-23): the check proves it read the file, not the layouts it knows.
        # Until then a pytest step in a layout the parser does not read (steps at indent 4, YAML's compact list style
        # and GitHub's starter layout; steps at indent 8; `-   name:`; a flow mapping; a quoted or spaced run key) gave
        # no row, parsed or unparsed, and this module read green with it in the file (probed at the round-4 head).
        # The census's population is derived from the file and must hold the two known invocations' lines, so a census
        # that counts nothing is red, not green.
        counted, uncovered = pytest_line_census(self.src)
        known = sorted(i["line"] for i in self.found if (i["job"], i["step"]) in (MATRIX_STEP, SERVED_STEP))
        self.assertTrue(known and set(known) <= set(counted), "the census does not count the known invocations' lines %r "
                        "among the lines it counts %r: an empty or partial census is red, not green" % (known, counted))
        self.assertEqual(uncovered, [], "lines of ci.yml that spell pytest (keyed on the spelling, PYTEST_WORD_RE, with a "
                         "trailing comment cut, or on the command a backslash continuation joins them into) outside every "
                         "span of lines the parser read for a row, parsed or unparsed; only a name: key's own line with no "
                         "other key after it and a line whose every pytest-spelling command is a pip install are excused. "
                         "Such a line is in a layout the parser does not read (steps at another indent, a flow mapping, a "
                         "quoted or spaced run key), outside any run (an artifact path, an action input), or the second "
                         "line of a folded or continued name: red until the parser reads it or the line is reworded:\n  "
                         + "\n  ".join("line %d: %s" % u for u in uncovered))

    def test_every_line_that_spells_the_switch_is_an_env_key_or_a_run_text_the_parser_read(self):
        # the switch census (review round 4's verify, 2026-09-23): the switch half reads the env: key lines of the file's
        # own layout and the run texts, and until then an env: written as an alias or a flow mapping, a quoted or spaced
        # key, a value continued on the next line, or a shell: or defaults key that set or cleared the switch read ok
        # beside a pytest that ran without it. Every line that spells the switch is one the parser read, or it is named.
        # The census's population is derived and must hold the matrix step's own switch line, so an empty census is red
        switch_read = []
        pytest_invocations(self.src, switch_read=switch_read)
        matrix = [e["line"] for e in switch_read if (e["job"], e["step"]) == MATRIX_STEP and e["clean"]]
        counted, uncovered = switch_line_census(self.src)
        self.assertTrue(matrix and set(matrix) <= set(counted), "the switch census does not count the matrix step's switch "
                        "line %r among the lines it counts %r: an empty or partial census is red, not green" % (matrix, counted))
        self.assertEqual(uncovered, [], "lines of ci.yml that spell %s (keyed on the spelling, with a trailing comment cut) "
                         "that the parser read neither as an env: key line (a bare key at its block's first key indent, its "
                         "value on that line and not a block scalar) nor as run text: such a line sets or clears the switch "
                         "where the env merge does not look (an env: alias or flow mapping, a quoted or spaced key, a "
                         "continued or block-scalar value, a key-shaped line in another key's block scalar, a step's shell: "
                         "or a job's defaults, a name: or if: that spells it). Red until it is an env: key the parser reads, "
                         "moves into a run text, or stops spelling the name:\n  " % SWITCH
                         + "\n  ".join("line %d: %s" % u for u in uncovered))

    def test_every_line_where_a_job_key_goes_is_a_job_the_parser_reads(self):
        # round 4's ruling A (3): a quoted job key, a key carrying its value or an anchor, or a job at another indent is
        # no job to JOB_RE, and the parser read its steps under the job above, with that job's name and env
        read, unread = unread_job_keys(self.src)
        self.assertTrue({MATRIX_STEP[0], SERVED_STEP[0]} <= set(read), "the job-key check read no job for the known "
                        "invocations' jobs: %r" % read)
        self.assertEqual(unread, [], "lines of ci.yml's jobs: mapping indented less than four spaces that are not a bare "
                         "job key at indent 2 (keyed on the indentation and JOB_RE): the parser reads the steps under "
                         "such a line as the job above's, with that job's name and env. Rewrite the key bare:\n  "
                         + "\n  ".join("line %d: %s" % u for u in unread))

    def test_ci_yml_holds_no_yaml_form_the_check_refuses(self):
        # the owner's fail-closed design (2026-09-23): the parser and the two censuses read no YAML anchor, alias or
        # merge key and no step written in flow style, and the pre-push lenses planted each beside a pytest run
        # without the switch or the flag and read green; its first verify pass found the same behind a quoted scalar
        # or flow collection carried to the next line, and in a double-quoted run's escape. The real file uses none of
        # them, so each is refused at its line (unread_yaml_forms; its cases in PopulationCheckReds) and none is modelled
        found = unread_yaml_forms(self.src)
        self.assertEqual(found, [], "lines of ci.yml in a YAML form " + YAML_FORMS_UNREAD + " (a flow mapping or sequence "
                         "holding a run, env or shell key, or a name key beside another key). Keyed on a line scan outside "
                         "block scalars: rewrite the line in the file's block layout without the anchor, alias, merge key "
                         "or flow collection, each quoted scalar closed on its line, a double-quoted one without a "
                         "backslash, and each block scalar header on its key's line (a plain scalar continued onto a line "
                         "that begins with &, *, <<:, | or >, or with a quote or bracket that does not close there, reads "
                         "as one: reword it):\n  "
                         + "\n  ".join("line %d: %s (%s)" % f for f in found))
        # the scan reads to the end of the real file: an alias appended as its last line is named there (a scan left
        # inside a block scalar, or stopped early, would read nothing after the point it stopped)
        last = len(self.src.rstrip("\n").splitlines()) + 1
        self.assertEqual(unread_yaml_forms(self.src.rstrip("\n") + "\nzz-alias: *nowhere\n"),
                         [(last, "zz-alias: *nowhere", "an alias (*nowhere)")])

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
        # keyed on the switch's name spelled in the file's text (switch_spellers), not on an environment read, over
        # served_load_set: the modules the step's globs collect, every non-test module under tests/ (conftest, __init__,
        # the helpers), and every module those import, followed through their import statements (the import walk,
        # review round 4, 2026-09-23: a test_ module a served module imports was outside the set until then, and a
        # switch-spelling comment appended to tests/test_spend_detail.py left this case green). A reader that spells
        # the name indirectly, and a module loaded by path or by a computed name, are outside this read, and the
        # message says what the check keys on (until 2026-09-21 it said the module "reads" the switch, which a
        # docstring that spells the name does not)
        readers = switch_spellers(HERE)
        self.assertIn(os.path.realpath(__file__), readers, "the census missed this file, which spells (and reads) the switch")
        collected = set()
        for inv in self.served:
            for pattern in _positional_paths(inv):
                collected.update(os.path.realpath(p) for p in glob.glob(pattern))
        self.assertTrue(collected, "the served step's globs resolve to no file at the repo root: %r" % [i["args"] for i in self.served])
        loaded = served_load_set(HERE, collected)
        self.assertIn(os.path.realpath(os.path.join(HERE, "conftest.py")), loaded, "the load set missed conftest.py")
        # the walk's non-vacuity: a test_ module outside the globs reaches the set only through a served module's import
        spend_detail = os.path.realpath(os.path.join(HERE, "test_spend_detail.py"))
        self.assertNotIn(spend_detail, collected, "test_spend_detail.py is collected by the globs now: pick another witness")
        self.assertIn(spend_detail, loaded, "the import walk did not reach test_spend_detail.py, which "
                      "tests/test_spend_modal_headless_served.py imports (keyed on that one import)")
        hit = sorted(os.path.relpath(p, ROOT) for p in readers & loaded)
        self.assertEqual(hit, [], "the served step collects or could load a module that spells %s in its text (keyed on the "
                         "spelling, docstrings and comments included, not on an environment read; a reader that spells the "
                         "name indirectly, or a module loaded by path or by a computed name, is outside this read), and it "
                         "runs without the switch: %s" % (SWITCH, hit))

    def test_a_test_module_a_served_module_imports_is_read_for_the_switch(self):
        # the import walk against what it refuses, over a scratch directory: a served-named module imports a test_
        # helper inside a function, that helper imports a second one by a from-import, and the second spells the
        # switch. served_load_set reaches both through the imports, and the speller is named; the non-test set alone,
        # the helper set before 2026-09-23, misses it. A module loaded by path is outside the walk, and stays out.
        d = tempfile.mkdtemp(prefix="switch-walk-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        files = {
            "test_zz_synthetic_served.py": "def test_page():\n    import test_zz_imported_helper\n",
            "test_zz_imported_helper.py": "from test_zz_deeper import VALUE\n",
            "test_zz_deeper.py": "VALUE = 1   # a synthetic helper that spells %s\n" % SWITCH,
            "test_zz_loaded_by_path.py": "# loaded by path, and spells %s too\n" % SWITCH,
            "conftest.py": "import os\nLOADER = os.path.join(os.path.dirname(__file__), 'test_zz_loaded_by_path.py')\n",
        }
        for name, body in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(body)
        served = {os.path.realpath(os.path.join(d, "test_zz_synthetic_served.py"))}
        loaded = served_load_set(d, served)
        names = lambda paths: sorted(os.path.basename(p) for p in paths)
        self.assertEqual(names(loaded), ["conftest.py", "test_zz_deeper.py", "test_zz_imported_helper.py", "test_zz_synthetic_served.py"])
        self.assertEqual(names(switch_spellers(d) & loaded), ["test_zz_deeper.py"], "the walk must name the imported speller")
        non_test = {os.path.realpath(p) for p in glob.glob(os.path.join(d, "*.py")) if not os.path.basename(p).startswith("test_")}
        self.assertEqual(names(switch_spellers(d) & (served | non_test)), [], "the set before the walk missed the speller")

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
    ("python -mpytest, one token", "      - name: Form (pytest)\n        run: python -mpytest tests/test_a.py -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("backslash continuation in a literal block", "      - name: Form (pytest)\n        run: |\n          python -m pytest tests/test_a.py \\\n            -q -p no:anyio\n",
     2, "tests/test_a.py -q -p no:anyio"),
)
# layouts the parser does not read (round 4's ruling A, 2026-09-23), each a step or a job that PyYAML and actionlint read
# as a pytest step (the round's refuters' runs): (label, where, text, the offset of the line the census must name from
# the plant's first line). "job" plants go between the python and shell jobs, "step" plants open the shell job's steps:
# away from the `  secrets:` anchor the other cases splice at and from the last job, so none reds for another reason.
# The findings named overlapping shapes: correctness-1's template-style job is tests-1's compact style, and its
# three-space dash is tests-1's `-   name:`; each label is carried here in a shape of its own.
UNREAD_LAYOUTS = (
    ("steps at indent 4, YAML's compact list style", "job",
     "  compact:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v4\n"
     "    - name: Compact (pytest)\n      run: python -m pytest tests/test_a.py -q\n", 5),
    ("a template-style job, GitHub's starter layout", "job",
     "  template:\n\n    runs-on: ubuntu-latest\n\n    steps:\n    - uses: actions/checkout@v4\n"
     "    - name: Test with pytest\n      run: |\n        pytest tests/test_a.py -q\n", 8),
    ("a job with steps at indent 8", "job",
     "  deep:\n    runs-on: ubuntu-latest\n    steps:\n        - name: Deep (pytest)\n"
     "          run: python -m pytest tests/test_a.py -q\n", 4),
    ("`-   name:`, keys at indent 10", "step",
     "      -   name: Wide dash (pytest)\n          run: python -m pytest tests/test_a.py -q\n", 1),
    ("a three-space dash, the step opening with run:", "step",
     "      -   run: python -m pytest tests/test_a.py -q\n", 0),
    ("a flow-mapping step", "step",
     "      - {name: Flow step, run: python -m pytest tests/test_a.py -q}\n", 0),
    ("a quoted run key", "step",
     "      - name: Quoted run key (pytest)\n        \"run\": python -m pytest tests/test_a.py -q\n", 1),
    ("run : with a space before the colon", "step",
     "      - name: Spaced run key (pytest)\n        run : python -m pytest tests/test_a.py -q\n", 1),
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

    def _with_job_before_shell(self, job_text, src=None):
        # a whole job spliced between the python and shell jobs: away from the `  secrets:` anchor and from the last job
        src = self.src if src is None else src
        at = src.index("\n  shell:\n") + 1
        return src[:at] + job_text + src[at:], _line_of(src, at)

    def _with_first_step_in_shell_job(self, step_text, src=None):
        # a step spliced as the shell job's first step: away from the `  secrets:` anchor the other cases append at
        src = self.src if src is None else src
        at = src.index("\n    steps:\n", src.index("\n  shell:\n")) + len("\n    steps:\n")
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
                # a form the parser reads is covered by the line census: no false red on any read form
                self.assertEqual(pytest_line_census(src)[1], [], "%s: the line census reds a form the parser reads" % label)

    def test_an_inline_env_prefix_on_the_command_sets_the_switch_for_that_command(self):
        # `ROMP_SDK_REQUIRE=1 python -m pytest ...` sets the variable for that process, as an env: block would
        src, first = self._with_step_in_shell_job('      - name: Prefixed (pytest)\n        run: %s=1 python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        new = self._new(src)
        self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + 1, "ok")], [_describe(i) for i in new])
        other, first = self._with_step_in_shell_job('      - name: Prefixed (pytest)\n        run: PYTHONWARNINGS=error python -m pytest tests/test_a.py -q -p no:anyio\n')
        new = self._new(other)
        self.assertEqual([verdict(i) for i in new], ["unlisted"], "another variable's prefix is not the switch")
        self.assertEqual(new[0]["args"].strip(), "tests/test_a.py -q -p no:anyio")
        # an export earlier in the block is unparsed, not unlisted (review round 4, 2026-09-23): the parser does not run
        # the shell, and an export writes whatever value it names, so the step reads red until the switch moves to an
        # env: key or a prefix on the command. Until then an export of 1 read unlisted and called that the safe side,
        # which held for 1 and not for an export of 0 after a step env of 1, which read ok
        export, first = self._with_step_in_shell_job('      - name: Exported (pytest)\n        run: |\n          export %s=1\n          python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        self.assertEqual([verdict(i) for i in self._new(export)], ["unparsed"])

    def test_a_quoted_switch_value_is_read_verbatim_so_one_with_a_space_is_not_1(self):
        # both runtime readers compare with == "1", and YAML keeps a quoted scalar's spaces: `"1 "` and `' 1'` reach
        # pytest as "1 " and " 1", which turn the switch off. Until 2026-09-23 _env_block stripped inside the quotes and
        # read both as 1, ok. An unquoted plain value is stripped, as YAML strips it, and still reads 1.
        for value, read in (('"1 "', "1 "), ("' 1'", " 1")):
            with self.subTest(value=value):
                src, first = self._with_step_in_shell_job('      - name: Quoted switch (pytest)\n        env:\n          %s: %s\n'
                                                          '        run: python -m pytest tests/test_a.py -q -p no:anyio\n' % (SWITCH, value))
                new = self._new(src)
                self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [(read, "unlisted")], [_describe(i) for i in new])
                self.assertIn("lacks ROMP_SDK_REQUIRE=1", _describe(new[0]))
        for value in ('"1"', "'1'", "1", "1   # a trailing comment"):
            with self.subTest(value=value):
                src, first = self._with_step_in_shell_job('      - name: Quoted switch (pytest)\n        env:\n          %s: %s\n'
                                                          '        run: python -m pytest tests/test_a.py -q -p no:anyio\n' % (SWITCH, value))
                self.assertEqual([verdict(i) for i in self._new(src)], ["ok"], "the control: %s reads 1" % value)

    def test_a_run_block_that_unsets_exports_or_assigns_the_switch_is_unparsed(self):
        # tests-3 and extra4-3 (review round 4, 2026-09-23): with a step env of "1", an unset, an export of 0 or a bare
        # assignment of 0 in the run text, on an earlier line or before the pytest command on its own line, read ok
        # while the shell handed pytest no switch or 0. The switch spelled in the run text anywhere but as a prefix on
        # the pytest command is unparsed now, and the message says it keys on the spelling
        env = '        env:\n          %s: "1"\n' % SWITCH
        for label, earlier, same_line in (
                ("unset", "unset %s" % SWITCH, "unset %s && " % SWITCH),
                ("an export of 0", "export %s=0" % SWITCH, "export %s=0; " % SWITCH),
                ("a bare assignment of 0", "%s=0" % SWITCH, "%s=0 && " % SWITCH)):
            for where, run in (("on an earlier line", "        run: |\n          %s\n          python -m pytest tests/test_a.py -q -p no:anyio\n" % earlier),
                               ("on the pytest line", "        run: %spython -m pytest tests/test_a.py -q -p no:anyio\n" % same_line)):
                with self.subTest(form=label, where=where):
                    src, first = self._with_step_in_shell_job("      - name: Rewritten switch (pytest)\n" + env + run)
                    new = self._new(src)
                    self.assertEqual([verdict(i) for i in new], ["unparsed"], "%s %s: %r" % (label, where, [_describe(i) for i in new]))
                    self.assertIn("spells ROMP_SDK_REQUIRE other than as a VAR=value prefix on its pytest command (keyed on "
                                  "the spelling", _describe(new[0]))
                    self.assertIn("python -m pytest tests/test_a.py", src.splitlines()[new[0]["line"] - 1], _describe(new[0]))
        # the prefix on the command itself is read, and stays the one spelling that is not unparsed
        src, first = self._with_step_in_shell_job("      - name: Prefixed switch (pytest)\n" + env +
                                                  "        run: %s=0 python -m pytest tests/test_a.py -q -p no:anyio\n" % SWITCH)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("0", "unlisted")])

    def test_a_pytest_step_after_a_step_that_writes_the_switch_to_github_env_is_unparsed(self):
        # a write to $GITHUB_ENV sets the variable for the steps after it, so a pytest step whose job's other run texts
        # spell the switch is unparsed: here the job's env sets it to 1 and an earlier step writes 0, and the step read
        # ok until 2026-09-23. The message names the step that spells it
        setter = '      - name: Write the switch\n        run: echo "%s=0" >> "$GITHUB_ENV"\n' % SWITCH
        runner = "      - name: After the write (pytest)\n        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        src, first = self._with_step_in_shell_job(setter + runner)
        src = self._with_shell_job_env(src)
        new = self._new(src)
        self.assertEqual([(i["step"], verdict(i)) for i in new], [("After the write (pytest)", "unparsed")], [_describe(i) for i in new])
        self.assertEqual(src.splitlines()[new[0]["line"] - 1].strip(), "run: python -m pytest tests/test_a.py -q -p no:anyio")
        self.assertIn("another step of the job spells ROMP_SDK_REQUIRE in its run text ('Write the switch'; keyed on the "
                      "spelling", _describe(new[0]))
        # the control: without the writing step the same job env makes it ok
        control = self._with_shell_job_env(self._with_step_in_shell_job(runner)[0])
        self.assertEqual([verdict(i) for i in self._new(control)], ["ok"])

    def test_a_switch_written_where_the_env_merge_does_not_look_is_named_by_the_switch_census(self):
        # review round 4's verify (attacks, M2, and prose-records, 2026-09-23): with the shell job's env setting the switch
        # to "1", which the merge reads, each shape below read ok while pytest ran with the switch at 0 or unset (PyYAML
        # and a shim, the lens's runs): the merge reads env: key lines in the file's own layout and nothing else. The
        # switch census names the line that sets or clears it; the row's own verdict is the misread it exists for
        run = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        for label, step, text in (
                ("a flow-mapping env", '      - name: Flow env (pytest)\n        env: {%s: "0"}\n' % SWITCH + run, 'env: {%s: "0"}' % SWITCH),
                ("a quoted key", '      - name: Quoted key (pytest)\n        env:\n          "%s": "0"\n' % SWITCH + run, '"%s": "0"' % SWITCH),
                ("a spaced key", '      - name: Spaced key (pytest)\n        env:\n          %s : "0"\n' % SWITCH + run, '%s : "0"' % SWITCH),
                ("an env: alias, its anchor on another step's env",
                 '      - name: Setup\n        env: &offenv\n          %s: "0"\n        run: make setup\n'
                 '      - name: Aliased env (pytest)\n        env: *offenv\n' % SWITCH + run, '%s: "0"' % SWITCH),
                ("a step's shell: that sets it", "      - name: Shell template (pytest)\n        shell: env %s=0 bash -e {0}\n" % SWITCH + run,
                 "shell: env %s=0 bash -e {0}" % SWITCH)):
            with self.subTest(form=label):
                src = self._with_shell_job_env(self._with_step_in_shell_job(step)[0])
                at = [n + 1 for n, l in enumerate(src.splitlines()) if l.strip() == text]
                self.assertEqual(len(at), 1, "%s: the planted line is not unique: re-anchor this case" % label)
                self.assertEqual([verdict(i) for i in self._new(src)], ["ok"], "%s: the merge alone reads the job's switch" % label)
                self.assertEqual(switch_line_census(src)[1], [(at[0], text)], label)
        # a job's defaults: run: shell: that clears it, over the shell job's own header
        src = self._with_shell_job_env(self._with_step_in_shell_job("      - name: Defaults (pytest)\n" + run)[0])
        text = "shell: env -u %s bash -e {0}" % SWITCH
        src = src.replace("\n  shell:\n    env:", "\n  shell:\n    defaults:\n      run:\n        %s\n    env:" % text, 1)
        at = [n + 1 for n, l in enumerate(src.splitlines()) if l.strip() == text]
        self.assertEqual(len(at), 1, "the shell job's header moved: re-anchor this case")
        self.assertEqual([verdict(i) for i in self._new(src)], ["ok"])
        self.assertEqual(switch_line_census(src)[1], [(at[0], text)])
        # a plain value continued on the next line: YAML folds it to `1 0`, which is not 1, and the key line is named
        src, first = self._with_step_in_shell_job("      - name: Continued value (pytest)\n        env:\n          %s: 1\n"
                                                  "            0\n" % SWITCH + run)
        new = self._new(src)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [("1 0", "unlisted")], [_describe(i) for i in new])
        self.assertEqual(switch_line_census(src)[1], [(first + 2, "%s: 1" % SWITCH)])
        # the controls: the switch as a step env key, a job env key with a trailing comment, and spelled in run text (the
        # switch half reads that as unparsed) are each read, and the census names nothing
        for label, src in (("a step env key", self._with_step_in_shell_job('      - name: Keyed (pytest)\n        env:\n          %s: "1"\n' % SWITCH + run)[0]),
                           ("a job env key with a comment", self._with_shell_job_env(self._with_step_in_shell_job("      - name: Job keyed (pytest)\n" + run)[0], '"1"   # a trailing comment')),
                           ("run text", self._with_step_in_shell_job("      - name: In the run text (pytest)\n        run: |\n          export %s=1\n"
                                                                     "          python -m pytest tests/test_a.py -q -p no:anyio\n" % SWITCH)[0])):
            with self.subTest(control=label):
                self.assertEqual(switch_line_census(src)[1], [], label)

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
        self.assertEqual([verdict(i) for i in self._new(unnamed)], ["unlisted", "unlisted"],
                         "keyed on the verdict: two unnamed steps share the placeholder, not a name, so neither is ambiguous")

    def test_every_invocation_under_a_listed_key_is_kept_for_the_premise_checks(self):
        # the served step with a second pytest line in its run block, unflagged: the grouping ListedInvocations reads
        # (invocations_by_key) keeps both, so a premise checked over the key sees each, and the second is unlisted
        served_line = [l for l in self.src.splitlines() if l.startswith("          python -m pytest tests/test_*_browser.py")]
        self.assertEqual(len(served_line), 1, served_line)
        src = self.src.replace(served_line[0] + "\n", served_line[0] + "\n          python -m pytest tests/test_other_served.py -q\n", 1)
        by_key = invocations_by_key(pytest_invocations(src))
        self.assertEqual([verdict(i) for i in by_key[SERVED_STEP]], ["listed", "unlisted"], [_describe(i) for i in by_key[SERVED_STEP]])
        self.assertEqual([i["args"].strip() for i in by_key[SERVED_STEP]][1], "tests/test_other_served.py -q",
                         "keyed on the grouping keeping the second pytest line's own arguments under the listed key")

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
                self.assertEqual(_shell_commands(line), segments, "keyed on the split at &&, ||, ;, |, a lone &, a subshell's "
                                 "parentheses and an unquoted comment, with quotes, $( ) and redirections kept whole")

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
                 "a line indented deeper than the block's first line in a folded block"),
                # a pip install is keyed on the command's program: until 2026-09-23 the words pip and install in a
                # pytest command's arguments excused it as one
                ("a wrapper whose arguments spell pip and install", '      - name: Pip words (pytest)\n        run: uvx pytest tests/ -q -k "pip and install"\n',
                 "a form the parser does not read as a command"),
                # the pip exclusion is per command in such a block too: until 2026-09-23 the pip half excused the line
                ("pip then pytest in an indentation-indicator block", "      - name: Indented pip (pytest)\n        run: |2\n            python -m pip install pytest && python -m pytest tests/ -q -p no:anyio\n",
                 "an indentation indicator (|2) on the block")):
            with self.subTest(form=label):
                bad = self._new_bad(self._with_step_in_shell_job(step)[0])
                self.assertEqual([verdict(i) for i in bad], ["unparsed"], "%s: %r" % (label, [_describe(i) for i in bad]))
                self.assertIn("does not read as a command (%s)" % reason, _describe(bad[0]))
        # a pip line that names the package is not a mention the parser owes: the live file has two
        pip = "      - name: Pip (pytest)\n        run: python -m pip install --upgrade pip pytest pytest-timeout\n"
        self.assertEqual(self._new_bad(self._with_step_in_shell_job(pip)[0]), [])

    def test_a_pytest_step_in_a_layout_the_parser_does_not_read_is_named_by_the_line_census(self):
        # round 4's ruling A: each layout gave no row, parsed or unparsed, and the module read green with it in the file
        # (probed at the round-4 head); the census names the step's pytest line, the one red, since the job key is read
        for label, where, text, offset in UNREAD_LAYOUTS:
            with self.subTest(layout=label):
                src, first = (self._with_job_before_shell if where == "job" else self._with_first_step_in_shell_job)(text)
                self.assertEqual(self._new(src), [], "%s: the parser now reads this layout; move the case to READ_FORMS" % label)
                line = first + offset
                self.assertEqual(pytest_line_census(src)[1], [(line, src.splitlines()[line - 1].strip())], label)
                self.assertEqual(unread_job_keys(src)[1], [], "%s: reds for the census's reason alone" % label)

    def test_a_quoted_job_key_after_a_switch_setting_job_is_red_at_its_line(self):
        # round 4's extra4-2: a quoted job key is no job to JOB_RE, so the parser reads its step as the job above's,
        # under that job's name and with its env; after a job whose env sets the switch, a flagged step with no switch
        # of its own reads ok and nothing is red (probed at the round-4 head). The job-key check names the key's line.
        envjob = ('  envjob:\n    runs-on: ubuntu-latest\n    env:\n      %s: "1"\n    steps:\n'
                  '      - uses: actions/checkout@v4\n' % SWITCH)
        for key in ('  "quoted-job":', "  'quoted-job':"):
            with self.subTest(key=key):
                quoted = ("%s\n    runs-on: ubuntu-latest\n    steps:\n      - name: Quoted job (pytest)\n"
                          "        run: python -m pytest tests/test_a.py -q -p no:anyio\n" % key)
                src, first = self._with_job_before_shell(envjob + quoted)
                self.assertEqual([(i["job"], i["step"], verdict(i)) for i in self._new(src)], [("envjob", "Quoted job (pytest)", "ok")],
                                 "the parser alone reads the step as the job above's, with its switch: the misread this check exists for")
                self.assertEqual(unread_job_keys(src)[1], [(first + envjob.count("\n"), key)])
                self.assertEqual(pytest_line_census(src)[1], [], "the step's line is in a row's span: the job-key check is the red")
        # a key carrying an anchor, or its value on the line, is no job to JOB_RE either
        for key in ("  anchored: &job", "  inline: {runs-on: ubuntu-latest}"):
            with self.subTest(key=key):
                src, first = self._with_job_before_shell(key + "\n")
                self.assertEqual(unread_job_keys(src)[1], [(first, key)])

    def test_python_mpytest_is_read_as_a_command_and_an_option_cluster_is_unparsed(self):
        # round 4's extra4-1: `python -mpytest` runs pytest; until 2026-09-23 PYTEST_WORD_RE's leading word boundary kept
        # it, and an option cluster such as `-Impytest`, out of every read (no row, module green; probed)
        src, first = self._with_first_step_in_shell_job("      - name: One token (pytest)\n        run: python -mpytest tests/test_a.py -q\n")
        bad = self._new_bad(src)
        self.assertEqual([(i["step"], i["line"], verdict(i)) for i in bad], [("One token (pytest)", first + 1, "unlisted")],
                         [_describe(i) for i in bad])
        self.assertEqual(bad[0]["args"].strip(), "tests/test_a.py -q")
        self.assertIn("lacks -p no:anyio", _describe(bad[0]))
        self.assertIn("and ROMP_SDK_REQUIRE=1", _describe(bad[0]))
        src, first = self._with_first_step_in_shell_job("      - name: Cluster (pytest)\n        run: python -Impytest tests/test_a.py -q\n")
        bad = self._new_bad(src)
        self.assertEqual([(i["step"], i["line"], verdict(i)) for i in bad], [("Cluster (pytest)", first + 1, "unparsed")],
                         [_describe(i) for i in bad])
        self.assertIn("does not read as a command (a form the parser does not read as a command)", _describe(bad[0]))

    def test_a_compliant_command_whose_pytest_word_sits_on_a_continuation_line_is_covered(self):
        # the census keys on the span the parser read for a row, line through last_line: keyed on the first line alone
        # it reds these compliant steps at their continuation lines (round 4's tests-1 refuters, probed)
        env = '        env:\n          %s: "1"\n' % SWITCH
        for label, run, offset in (
                ("backslash continuations", "        run: |\n          python -m \\\n            pytest tests/test_a.py -q -p no:anyio \\\n"
                                            "            --junitxml=pytest-report.xml\n", 4),
                ("a folded paragraph", "        run: >\n          python -m\n          pytest tests/test_a.py -q -p no:anyio\n", 4),
                ("a plain scalar continued", "        run: python -m\n          pytest tests/test_a.py -q -p no:anyio\n", 3)):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job("      - name: Continued\n" + env + run)
                new = self._new(src)
                self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + offset, "ok")], [_describe(i) for i in new])
                self.assertGreater(new[0]["last_line"], new[0]["line"], "%s: the row's span runs past its first line" % label)
                self.assertEqual(pytest_line_census(src)[1], [], "%s: a compliant command's continuation line is read" % label)

    def test_a_flow_mapping_step_whose_name_half_spells_pytest_is_red(self):
        # the name exclusion is a line whose KEY is name (`name:` or `- name:`), never a line that merely contains
        # "name:": a flow mapping carries a run on the same line, and the census cannot read what runs
        src, first = self._with_first_step_in_shell_job("      - {name: Flow (pytest), run: make test}\n")
        self.assertEqual(pytest_line_census(src)[1], [(first, "- {name: Flow (pytest), run: make test}")])
        # a true name key in a layout the parser does not read is excused, its run line judged on its own
        src, first = self._with_first_step_in_shell_job("      -   name: Wide name only (pytest)\n          run: make test\n")
        self.assertEqual(pytest_line_census(src)[1], [])
        # a flow mapping over several lines whose line OPENS with name: and carries the run after it (review round 4's
        # verify, 2026-09-23): the line's key is name, and until then NAME_KEY_RE excused it whole while the parser gave
        # the step no row, so a pytest with neither the switch nor the flag was silent. A name key is excused only when
        # no other key follows on its line (NAME_KEY_RE); here `run:` does, so the census names the line
        for label, text in (("the run after a comma", "      - {\n          name: FlowMulti, run: python -m pytest tests/test_k.py\n        }\n"),
                            ("the run after the name's quoted value", '      - {\n          name: "Flow, quoted", run: python -m pytest tests/test_k.py\n        }\n'),
                            ("the run after a comma with no space", "      - {\n          name: FlowMulti,run: python -m pytest tests/test_k.py\n        }\n"),
                            # an apostrophe inside a plain name opens no quoted scalar, so the run after it is still seen
                            ("the run after a plain name holding an apostrophe", "      - {\n          name: Don't skip, run: python -m pytest tests/test_k.py\n        }\n")):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text)
                want = [(n, src.splitlines()[n - 1].strip()) for n in range(first, first + text.count("\n"))
                        if "python -m pytest" in src.splitlines()[n - 1]]
                self.assertEqual(len(want), 1, label)
                self.assertEqual(pytest_line_census(src)[1], want, label)
        # the exclusion is the name key's own line and no other: a name folded onto a second line that spells pytest
        # reds there, a red on valid YAML whose message says to reword the line (the pre-push lenses' N07 and B46)
        src, first = self._with_first_step_in_shell_job("      - name: >-\n          Smoke pytest\n          on Linux\n        run: echo hi\n")
        self.assertEqual(pytest_line_census(src)[1], [(first + 1, "Smoke pytest")])
        # the controls: a name key that spells pytest with no key after it is still excused, whether its value holds a
        # comma, brackets and an expression, a `: ` inside its quoted scalar, or a `: ` in a trailing comment (in block
        # context a plain scalar cannot hold `: `, so an unquoted one outside a comment is the test)
        for label, name in (("a comma, brackets and an expression", "Run pytest (3.12, linux) [fast] ${{ matrix.os }}"),
                            ("a colon inside the quoted value", '"Run pytest: the suite"'),
                            ("a colon in a trailing comment", "Run pytest  # note: later")):
            with self.subTest(control=label):
                src, first = self._with_first_step_in_shell_job("      - name: %s\n        run: make test\n" % name)
                self.assertEqual(pytest_line_census(src)[1], [], label)

    def test_a_quoted_hash_before_the_pytest_word_does_not_cut_the_line(self):
        # the census cuts a trailing comment the way _shell_commands does (_comment_cut): a `#` inside quotes is no
        # comment. A cut blind to quotes (review round 4's verify, mutant M5, 2026-09-23) cut each of these lines
        # before its pytest word, so an unread line escaped the census while every test stayed green. Each is a road
        # PyYAML reads as a step that runs pytest: the `#` sits inside a YAML-quoted scalar, where YAML sees no comment
        # (in a plain scalar ` #` does start a YAML comment, whatever shell quotes surround it; the census keeps that
        # text too, a count on the safe side)
        for label, text in (("a flow mapping whose quoted name holds a #", '      - {name: "Build #1", run: python -m pytest tests/test_m3.py}\n'),
                            ("a double-quoted run scalar, a single-quoted # before && pytest",
                             "      - name: Hash then pytest\n        run : \"echo 'a #b' && pytest tests/test_m.py\"\n"),
                            ("a single-quoted run scalar, a double-quoted # before ; python -m pytest",
                             "      - name: Hash then pytest\n        run : 'echo \"x #y\" ; python -m pytest tests/test_m2.py'\n")):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text)
                line = first + text.count("\n") - 1
                self.assertEqual(pytest_line_census(src)[1], [(line, src.splitlines()[line - 1].strip())], label)
        # the control: an unquoted ` #` is a comment, and a pytest word after it is cut with it
        src, first = self._with_first_step_in_shell_job("      - name: Commented\n        run : make test  # pytest later\n")
        self.assertEqual(pytest_line_census(src)[1], [])

    def test_a_tagged_run_block_is_read_through_and_an_anchored_run_is_unparsed(self):
        # review round 4's verify (attacks, M1, 2026-09-23): a node property before the block indicator (`run: &cmd |`,
        # `run: !!str |`) kept BLOCK_INDICATOR_RE from matching, so the literal block was folded into one command: the
        # second command's -p no:anyio was credited to the first, and a bare ROMP_SDK_REQUIRE=1 line, a shell variable
        # that is not exported, read as a prefix on the pytest command after it; both read ok. The properties are set
        # aside to split the scalar into its lines, as the same block without them is. A tag is read through; a run that
        # carries an anchor is unparsed at each pytest line, since an alias of it (`run: *cmd`, a line that never spells
        # pytest) runs the same text under another step's env, which the parser does not follow
        env = '        env:\n          %s: "1"\n' % SWITCH
        two = "          python -m pytest -q tests/test_a.py\n          python -m pytest -q -p no:anyio tests/test_b.py\n"
        bare = "          %s=1\n          python -m pytest -q -p no:anyio tests/test_a.py\n" % SWITCH
        for label, head in (("a tag", "        run: !!str |\n"), ("a tag, strip chomping", "        run: !!str |-\n")):
            with self.subTest(form=label, block="two commands, the first unflagged"):
                src, first = self._with_first_step_in_shell_job("      - name: Tagged (pytest)\n" + env + head + two)
                new = self._new(src)
                self.assertEqual([(i["line"], verdict(i), i["args"].strip()) for i in new],
                                 [(first + 4, "unlisted", "-q tests/test_a.py"), (first + 5, "ok", "-q -p no:anyio tests/test_b.py")],
                                 "%s: %r" % (label, [_describe(i) for i in new]))
                self.assertIn("lacks -p no:anyio", _describe(new[0]))
                self.assertEqual(pytest_line_census(src)[1], [], label)
            with self.subTest(form=label, block="a bare assignment of the switch, then a flagged pytest"):
                src, first = self._with_first_step_in_shell_job("      - name: Tagged (pytest)\n" + head + bare)
                new = self._new(src)
                self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + 3, "unparsed")], "%s: %r" % (label, [_describe(i) for i in new]))
                self.assertIn("spells ROMP_SDK_REQUIRE other than as a VAR=value prefix", _describe(new[0]))
        for label, head in (("an anchor on a block", "        run: &cmd |\n"), ("an anchor and a tag", "        run: &cmd !!str |\n"),
                            ("a tag and an anchor", "        run: !!str &cmd |\n")):
            for block, text, lines in (("two commands", env + head + two, (4, 5)), ("a bare assignment", head + bare, (3,))):
                with self.subTest(form=label, block=block):
                    src, first = self._with_first_step_in_shell_job("      - name: Anchored (pytest)\n" + text)
                    new = self._new(src)
                    self.assertEqual([(i["line"], verdict(i)) for i in new], [(first + n, "unparsed") for n in lines],
                                     "%s, %s: %r" % (label, block, [_describe(i) for i in new]))
                    for i in new:
                        self.assertIn("an anchor (&cmd) on the run: an alias of it elsewhere (*cmd)", _describe(i))
                    self.assertEqual(pytest_line_census(src)[1], [], "%s, %s: the rows cover the block's lines" % (label, block))
        # on a one-line plain scalar too, and on a run whose text never spells pytest the anchor gives no row
        src, first = self._with_first_step_in_shell_job("      - name: Anchored line (pytest)\n" + env +
                                                        "        run: &cmd python -m pytest -q -p no:anyio tests/test_a.py\n")
        self.assertEqual([(i["line"], verdict(i)) for i in self._new(src)], [(first + 3, "unparsed")])
        src, first = self._with_first_step_in_shell_job("      - name: Anchored make\n        run: &cmd make test\n")
        self.assertEqual(self._new(src), [])

    def test_a_backslash_continuation_is_joined_the_way_the_shell_joins_it(self):
        # review round 4's verify (attacks, M3, 2026-09-23): the parser joined a backslash continuation with a space, and
        # the shell removes the backslash and the newline and inserts nothing, so `-p no:anyio\` followed by an unindented
        # `--durations=10` is the one word `no:anyio--durations=10` to pytest (anyio's plugin stays registered) and read
        # as the flag; and `python -m py\` followed by `test ...` runs pytest while the parser read `py test` and gave no
        # row. A backslash followed by a space escapes the space and joins nothing, and so does an escaped backslash
        env = '        env:\n          %s: "1"\n' % SWITCH
        for label, block, offset, args in (
                ("the flag fused with the next word", "          python -m pytest -q -p no:anyio\\\n          --durations=10\n", 4, "-q -p no:anyio--durations=10"),
                ("a backslash, then a space", "          python -m pytest -q tests/test_a.py \\ \n            -p no:anyio\n", 4, "-q tests/test_a.py \\"),
                ("an escaped backslash", "          python -m pytest -q tests/test_a.py \\\\\n            -p no:anyio\n", 4, "-q tests/test_a.py \\\\")):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job("      - name: Continued (pytest)\n" + env + "        run: |\n" + block)
                new = self._new(src)
                self.assertEqual([(i["line"], verdict(i), i["args"].strip()) for i in new], [(first + offset, "unlisted", args)],
                                 "%s: %r" % (label, [_describe(i) for i in new]))
                self.assertIn("lacks -p no:anyio", _describe(new[0]))
        # the word split over two lines of a heredoc is one word to the shell that reads it: a row, named at its first line
        src, first = self._with_first_step_in_shell_job("      - name: Split word\n        run: |\n          bash <<EOF\n"
                                                        "          python -m py\\\n          test -q tests/test_a.py\n          EOF\n")
        new = self._new(src)
        self.assertEqual([(i["line"], i["last_line"], verdict(i), i["args"].strip()) for i in new],
                         [(first + 3, first + 4, "unlisted", "-q tests/test_a.py")], [_describe(i) for i in new])
        # the control: whitespace on either side of the join is one word boundary, as the READ_FORMS continuation reads
        src, first = self._with_first_step_in_shell_job("      - name: Continued (pytest)\n" + env + "        run: |\n"
                                                        "          python -m pytest -q \\\n            -p no:anyio\n")
        self.assertEqual([(verdict(i), i["args"].strip()) for i in self._new(src)], [("ok", "-q -p no:anyio")])

    def test_an_unread_line_that_installs_pytest_and_then_runs_it_is_red(self):
        # the pip exclusion is judged per shell command, never per line: in a layout the parser does not read, a line
        # whose commands install pytest and then run it counts; one that only installs it is excused
        for label, step, red in (
                ("run : , pip then pytest", "      - name: Pip then run\n        run : python -m pip install pytest && python -m pytest tests/test_a.py -q\n", True),
                ("quoted run key and scalar, pip then pytest",
                 '      - name: Pip then run\n        "run": "python -m pip install pytest && python -m pytest tests/test_a.py -q"\n', True),
                ("run : , pip alone", "      - name: Pip only\n        run : python -m pip install --upgrade pip pytest pytest-timeout\n", False),
                ("run : , pip alone over a backslash continuation",
                 "      - name: Pip only\n        run : python -m pip install --upgrade pip \\\n          pytest-timeout\n", False),
                # a pip install is keyed on the command's program, not on the words pip and install anywhere in it
                ("run : , a pytest command whose arguments spell pip and install",
                 "      - name: Pip words\n        run : pytest tests/pip/install -q\n", True)):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(step)
                want = [(first + 1, src.splitlines()[first].strip())] if red else []
                self.assertEqual(pytest_line_census(src)[1], want, label)
        # in a step the parser reads, a pip install continued over lines is one command, judged on the text it read
        src, first = self._with_first_step_in_shell_job("      - name: Pip over two lines\n        run: |\n"
                                                         "          python -m pip install --upgrade pip pytest \\\n            pytest-timeout\n")
        self.assertEqual(pytest_line_census(src)[1], [])

    def test_the_census_joins_an_unread_line_the_way_the_shell_joins_it(self):
        # the owner's fail-closed design (2026-09-23; the pre-push lenses' C03, C04 and C05): the census's own join for
        # a line the parser did not read stripped trailing whitespace first and joined with a space, so a pip line
        # ending in a backslash and a space, or in an escaped backslash, took the pytest line after it as one pip
        # command and excused it (bash runs the two apart), and a pytest word split by a continuation was never counted.
        # It joins as the parser does now (_continues, _join_continuation), and PYTEST_WORD_RE reads the joined text
        # too. Steps at indent 4, a layout the parser does not read
        head = "  compact:\n    runs-on: ubuntu-latest\n    steps:\n    - name: Compact\n      shell: bash {0}\n      run: |\n"
        for label, block, named in (
                ("a pip line ending in a backslash and a space", "        pip install foo \\ \n        python -m pytest tests/test_a.py -q\n", (8,)),
                ("a pip line ending in an escaped backslash", "        pip install foo \\\\\n        python -m pytest tests/test_a.py -q\n", (8,)),
                ("the pytest word split by a continuation", "        python -m py\\\n        test tests/test_a.py -q\n", (7, 8)),
                # the forward join (the fail-closed design's third verify pass, 2026-09-24: the join after the line
                # returned to the old rule was a non-red mutant): a line that spells no pytest and ends in a backslash
                # and a space joins nothing, so it is not counted; under the old rule it took the pytest line after it
                ("a line spelling no pytest ending in a backslash and a space", "        echo a \\ \n        python -m pytest tests/test_a.py -q\n", (8,))):
            with self.subTest(form=label):
                src, first = self._with_job_before_shell(head + block)
                self.assertEqual(self._new(src), [], "%s: the parser does not read this layout" % label)
                self.assertEqual(pytest_line_census(src)[1], [(first + k - 1, src.splitlines()[first + k - 2].strip()) for k in named], label)
        # the controls: a pip install continued onto the next line is one command and excused, and a continuation whose
        # next line is indented past the first keeps its words apart, so `python -m py \` then `test` spells no pytest
        for label, block in (("a pip install continued", "        pip install --upgrade pip \\\n        pytest pytest-timeout\n"),
                             ("a continuation with whitespace at the join", "        python -m py \\\n          test tests/test_a.py\n")):
            with self.subTest(control=label):
                src, first = self._with_job_before_shell(head + block)
                self.assertEqual(pytest_line_census(src)[1], [], label)

    def test_a_key_shaped_line_in_an_env_block_scalar_is_its_text_and_the_key_is_unclean(self):
        # the owner's fail-closed design (2026-09-23; the pre-push lenses' S10, S11 and S12): _env_block read a key at
        # any depth, so `ROMP_SDK_REQUIRE: "1"` written as a line of another key's `|` or `>` block read as the switch
        # on and the switch census counted it a clean key line, while YAML held it as that key's text and pytest ran
        # without the switch. A key is read at the block's first key indent only, a block scalar's lines are its text,
        # and a block-scalar value makes its key unclean: the step reads unlisted and the switch census names the line
        run = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        for label, indicator in (("a literal block", "|"), ("a folded block", ">"), ("a literal block, strip chomping", "|-")):
            with self.subTest(form=label, scope="step"):
                src, first = self._with_step_in_shell_job("      - name: Block text (pytest)\n        env:\n          NOTES: %s\n"
                                                          '            %s: "1"\n' % (indicator, SWITCH) + run)
                new = self._new(src)
                self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [(None, "unlisted")], [_describe(i) for i in new])
                self.assertEqual(switch_line_census(src)[1], [(first + 3, '%s: "1"' % SWITCH)], label)
        with self.subTest(scope="job"):
            src = self.src.replace("\n  shell:\n    name: Shell", '\n  shell:\n    env:\n      NOTES: |\n        %s: "1"\n    name: Shell' % SWITCH, 1)
            self.assertNotEqual(src, self.src, "the shell job's header moved: re-anchor this case")
            src, first = self._with_step_in_shell_job("      - name: Job block text (pytest)\n" + run, src)
            new = self._new(src)
            self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [(None, "unlisted")], [_describe(i) for i in new])
            at = [n + 1 for n, l in enumerate(src.splitlines()) if l == '        %s: "1"' % SWITCH]
            self.assertEqual(switch_line_census(src)[1], [(at[0], '%s: "1"' % SWITCH)])
        # the switch's own value as a block scalar (`|-` then 1 is "1" to YAML): its key line is not read clean, the
        # value read is the indicator, never 1, and the census names the key line
        src, first = self._with_step_in_shell_job("      - name: Block switch (pytest)\n        env:\n          %s: |-\n            1\n" % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("|-", "unlisted")])
        self.assertEqual(switch_line_census(src)[1], [(first + 2, "%s: |-" % SWITCH)])
        # an empty block scalar (`>-` with no lines, "" to YAML) in a job with no pytest step: no invocation reads the
        # value, so the switch census is the one check that sees it, and the block-scalar value alone makes the key
        # unclean (the fail-closed design's third verify pass, 2026-09-24: E35, the one plant a mutant reading a
        # block-scalar value as clean changed; the module stayed green under that mutant until this case)
        src, first = self._with_job_before_shell("  nopy:\n    runs-on: ubuntu-latest\n    env:\n      %s: >-\n      OTHER: x\n"
                                                 "    steps:\n      - run: echo hi\n" % SWITCH)
        self.assertEqual(self._new(src), [], "the job runs no pytest")
        self.assertEqual(switch_line_census(src)[1], [(first + 3, "%s: >-" % SWITCH)])
        # the controls: a real switch key at the block's key indent after another key's block scalar reads, and a `#`
        # line inside the block scalar is its text; the census names nothing
        src, first = self._with_step_in_shell_job("      - name: After a block (pytest)\n        env:\n          NOTES: |\n"
                                                  "            # a line of text\n            more text\n          %s: \"1\"\n" % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")])
        self.assertEqual(switch_line_census(src)[1], [])
        # a line at the key indent the regex does not read as a key holds the deeper lines after it: they are its value,
        # so the clean switch above it stays read and the census names nothing (the fail-closed design's third verify
        # pass, 2026-09-24: E29, E32 and E33, each named at the switch's line on valid YAML until then, the deeper line
        # counted against the switch). A deeper line that spells the switch is still named, at its own line
        for label, other in (("a quoted key's block scalar (E29)", '          "OTHER-X": |\n            text\n'),
                             ("a hyphenated key's block scalar (E32)", "          OTHER-X: |\n            text\n"),
                             ("a quoted key's plain value continued (E33)", '          "OTHER": a\n            b\n')):
            with self.subTest(control=label):
                src, first = self._with_step_in_shell_job("      - name: After an unread key (pytest)\n        env:\n          %s: \"1\"\n"
                                                          % SWITCH + other + run)
                self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")], label)
                self.assertEqual(switch_line_census(src)[1], [], label)
        src, first = self._with_step_in_shell_job("      - name: Switch text under an unread key (pytest)\n        env:\n          %s: \"1\"\n"
                                                  '          "OTHER-X": |\n            %s: "0"\n' % (SWITCH, SWITCH) + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")])
        self.assertEqual(switch_line_census(src)[1], [(first + 4, '%s: "0"' % SWITCH)])

    def test_a_yaml_anchor_alias_or_merge_key_anywhere_is_refused_at_its_line(self):
        # the owner's fail-closed design (2026-09-23): the parser reads no anchor, alias or merge key, and the pre-push
        # lenses planted the first four of these beside a pytest run without the switch or the flag and read green,
        # since no other check here names them (asserted per plant: nothing else is red). unread_yaml_forms refuses each
        # at its line; a merge key, which GitHub's runner refuses, is refused the same way
        sw_job = '    runs-on: ubuntu-latest\n    env:\n      %s: "1"\n' % SWITCH
        run_ok = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        for label, where, text, named in (
                ("an anchor on a name: value, aliased by a run (N06)", "first",
                 "      - name: &cmd python -m pytest tests/test_a.py -q\n        run: *cmd\n",
                 ((1, "an anchor (&cmd)"), (2, "an alias (*cmd)"))),
                ("an anchored step aliased into a job without the switch (A01b)", "job",
                 "  anch:\n" + sw_job + "    steps:\n      - &pystep\n        name: Anchored step (pytest)\n" + run_ok +
                 "  alias:\n    runs-on: ubuntu-latest\n    steps:\n      - *pystep\n",
                 ((6, "an anchor (&pystep)"), (12, "an alias (*pystep)"))),
                ("an anchored steps list aliased into a job without the switch (A02b)", "job",
                 "  anch:\n" + sw_job + "    steps: &st\n      - name: In anchored list (pytest)\n" + run_ok +
                 "  copy:\n    runs-on: ubuntu-latest\n    steps: *st\n",
                 ((5, "an anchor (&st)"), (10, "an alias (*st)"))),
                ("env: *x, its anchor on a line of its own (the env alias plant)", "job",
                 "  setter:\n" + sw_job + "    steps:\n      - name: Env anchor\n        env:\n          &zeroenv\n"
                 '          %s: "0"\n        run: echo anchor\n      - name: Env alias (pytest)\n        env: *zeroenv\n' % SWITCH + run_ok,
                 ((8, "an anchor (&zeroenv)"), (12, "an alias (*zeroenv)"))),
                # a tag is a node property like an anchor, so an anchor after it is read (the first verify pass's Y26: the
                # anchor after a tag had no case, and the scan reading a tag as a plain scalar missed it)
                ("an anchor after a tag on a name: value, aliased by a run (Y26)", "first",
                 "      - name: !!str &tn python -m pytest tests/test_a.py -q\n        run: *tn\n",
                 ((1, "an anchor (&tn)"), (2, "an alias (*tn)"))),
                ("a merge key bringing a run into a step", "first",
                 "      - &base\n        name: Base\n        run: echo base\n      - <<: *base\n        name: Merged\n",
                 ((1, "an anchor (&base)"), (4, "a merge key (<<)"), (4, "an alias (*base)"))),
                # a block scalar's text runs only to the lines indented past the key that opened it, never the dash's
                # column: the alias on the step's next key is read
                ("an alias on the key after a `- run: |` block", "first",
                 "      - name: Anchor\n        env: &e\n          A: b\n        run: echo a\n      - run: |\n          echo b\n"
                 "        env: *e\n", ((2, "an anchor (&e)"), (7, "an alias (*e)")))):
            with self.subTest(form=label):
                src, first = (self._with_job_before_shell if where == "job" else self._with_first_step_in_shell_job)(text)
                want = [(first + k - 1, src.splitlines()[first + k - 2].strip(), what) for k, what in named]
                self.assertEqual(unread_yaml_forms(src), sorted(want), label)
                self.assertEqual((self._new_bad(src), pytest_line_census(src)[1], switch_line_census(src)[1], unread_job_keys(src)[1]),
                                 ([], [], [], []), "%s: the refusal is the one red" % label)
        # an anchor or alias after an explicit key's `?`, and an anchor after the document start marker, are refused
        # at their lines too (the first verify pass's Y21 and Y22: neither line was named; Y21's pytest value line is
        # also named by the line census, a layout the parser does not read)
        src, first = self._with_first_step_in_shell_job("      - name: Explicit key\n        ? &rk run\n        : echo one\n"
                                                        "      - name: Explicit alias (pytest)\n        ? *rk\n"
                                                        "        : python -m pytest tests/test_a.py -q\n")
        self.assertEqual([(n - first + 1, w) for n, _t, w in unread_yaml_forms(src)], [(2, "an anchor (&rk)"), (5, "an alias (*rk)")])
        self.assertEqual([n - first + 1 for n, _t in pytest_line_census(src)[1]], [6])
        self.assertEqual(unread_yaml_forms("--- &doc\n" + self.src), [(1, "--- &doc", "an anchor (&doc)")])
        # the controls, the real file's own shapes: `&&`, `2>&1` and a `*` glob in a run; a literal block whose lines
        # open with `*)` and `&>`; a quoted scalar holding `*` and `&`; each reads as text
        for label, text in (("operators and a glob in a plain run", "      - name: Plain\n        run: make a && ls tests/*.py 2>&1 | tee log\n"),
                            ("a literal block's lines", "      - name: Block\n        run: |\n          case $x in\n            *) echo other ;;\n"
                                                        "          esac\n          &>/dev/null true\n"),
                            ("a quoted scalar", '      - name: "* & *"\n        run: echo \'&x *y\'\n')):
            with self.subTest(control=label):
                self.assertEqual(unread_yaml_forms(self._with_first_step_in_shell_job(text)[0]), [], label)

    def test_a_step_or_env_written_as_a_flow_collection_is_refused_at_its_line(self):
        # the owner's fail-closed design (2026-09-23; the pre-push lenses' N04 and N05): the parser reads no step in
        # flow style, and a flow mapping over several lines whose name line carried a JSON-style `"run":` key read
        # green, the census excusing the line as a lone name key. A flow mapping or sequence holding a run, env or shell
        # key, or a name key beside another key, is refused at the key's line; one written over several lines is
        # refused at its opening line as well (the fail-closed design's first verify pass: no scan state crosses a line)
        over_lines = (1, "a flow collection ({) continued past its line")
        for label, text, named in (
                ('a JSON-style "run": after the name, over several lines (N04)',
                 '      - {\n          name: FlowAdj, "run":python -m pytest tests/test_a.py -q\n        }\n',
                 [over_lines, (2, "a flow mapping holding the key 'run'")]),
                ("the same with 'run': (N05)",
                 "      - {\n          name: FlowAdj, 'run':python -m pytest tests/test_a.py -q\n        }\n",
                 [over_lines, (2, "a flow mapping holding the key 'run'")]),
                ("a one-line flow step", "      - {name: Flow step, run: python -m pytest tests/test_a.py -q}\n", [(1, "a flow mapping holding the key 'run'")]),
                ("a flow env on a flow step", '      - {name: Flow env, env: {%s: "0"}, uses: ./a}\n' % SWITCH, [(1, "a flow mapping holding the key 'env'")]),
                ("a shell key in a flow sequence's mapping", "      - uses: ./a\n        with: [{shell: bash}]\n", [(2, "a flow mapping holding the key 'shell'")]),
                ("a name beside another key", "      - {name: Flow action, uses: ./.github/actions/a}\n", [(1, "a flow mapping holding a name key beside another key")]),
                # an entry of a flow mapping is a key whatever follows it, read up to its first colon
                ("a plain run key with no space after its colon", "      - {name: Tight, run:python -m pytest tests/test_a.py -q}\n",
                 [(1, "a flow mapping holding the key 'run'")])):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text)
                self.assertEqual([(n, w) for n, _t, w in unread_yaml_forms(src)], [(first + k - 1, what) for k, what in named], label)
        # a flow collection or a quoted scalar left open at the end of the file is refused at the line that opened it
        for label, tail, what in (("a flow sequence", "zz-open: [a, b\n", "a flow collection ([) continued past its line"),
                                  ("a quoted scalar", 'zz-open: "text\n', "a quoted scalar continued past its line")):
            with self.subTest(open=label):
                src = self.src.rstrip("\n") + "\n" + tail
                self.assertEqual(unread_yaml_forms(src), [(len(src.splitlines()), tail.strip(), what)], label)
        # the N04 line is named by the census as well: a `:` right after a quoted scalar is a key, so the line is not a
        # lone name key (_name_key_alone)
        src, first = self._with_first_step_in_shell_job('      - {\n          name: FlowAdj, "run":python -m pytest tests/test_a.py -q\n        }\n')
        self.assertEqual([n for n, _t in pytest_line_census(src)[1]], [first + 1])
        # the controls: a flow sequence of values (the file's `branches: [main]` and its matrix lists), a flow mapping
        # of an action's inputs, and a flow mapping holding a name alone
        for label, text in (("a flow sequence of values", "      - uses: ./a\n        with:\n          list: ['3.10', \"3.13\", main]\n"),
                            ("a flow mapping of inputs", "      - uses: actions/setup-python@v5\n        with: {python-version: '3.12', cache: pip}\n"),
                            ("a name alone", "      - uses: ./a\n        with: {name: only}\n")):
            with self.subTest(control=label):
                self.assertEqual(unread_yaml_forms(self._with_first_step_in_shell_job(text)[0]), [], label)

    def test_a_quoted_scalar_or_flow_collection_continued_past_its_line_and_a_double_quoted_escape_are_refused(self):
        # the fail-closed design's first verify pass (2026-09-23): the scan carried a quoted scalar or flow collection
        # to the next line as YAML does, and a plain scalar continued onto a line that opens with a quote or a bracket
        # carried one YAML never opened, so the lines up to the next such quote or bracket were not read as nodes: the
        # env alias, name anchor and anchored step plants behind such a line (W01 to W03) each read green beside a
        # pytest run without the switch or the flag. A key-shaped switch line inside another env key's quoted scalar
        # over several lines (Z01 to Z04b, Z14) read as the switch on, and a double-quoted run's \n escape started a
        # second pytest command without the flag that the parser read as part of the first (Q01; a \x escape spells
        # pytest or the switch in text the checks read without it, Q02 and Q03). Each was silent at the round-4 takes
        # head and at the owner's fail-closed head. Each is refused at the line that opens it, and nothing else here is
        # red (asserted per plant), so the refusal is what reds it
        sw_job = '    runs-on: ubuntu-latest\n    env:\n      %s: "1"\n' % SWITCH
        run_ok = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        quote = "a quoted scalar continued past its line"
        escape = "a double-quoted scalar holding a backslash escape"
        for label, where, text, named in (
                ("an env alias, each name continued onto a line opening with a double quote (W01)", "job",
                 "  setter:\n" + sw_job + '    steps:\n      - name: Env anchor\n          "x\n        env:\n          &zeroenv\n'
                 '          %s: "0"\n        run: echo anchor\n      - name: Env alias (pytest)\n          "y\n        env: *zeroenv\n' % SWITCH + run_ok,
                 ((7, quote), (13, quote))),
                ("a name anchor aliased by a run, behind a name continued onto a line opening with a double quote (W02)", "first",
                 '      - name: Prior step\n          "x\n        run: echo prior\n      - name: &cmd python -m pytest tests/test_a.py -q\n'
                 "        run: *cmd\n", ((2, quote),)),
                ("an anchored step aliased into a switchless job, behind a single quote (W03)", "job",
                 "  anch:\n" + sw_job + "    steps:\n      - name: Prior\n          'x\n        run: echo prior\n      - &pystep\n"
                 "        name: Anchored step (pytest)\n" + run_ok + "  alias:\n    runs-on: ubuntu-latest\n    steps:\n      - *pystep\n",
                 ((7, quote),)),
                ("the switch line inside a step env's double-quoted scalar (Z01)", "last",
                 '      - name: Quoted text (pytest)\n        env:\n          NOTES: "first line\n          %s: \'1\'\n          end"\n' % SWITCH + run_ok,
                 ((3, quote),)),
                ("the same in a single-quoted scalar (Z02)", "last",
                 "      - name: Single quoted text (pytest)\n        env:\n          NOTES: 'first line\n          %s: \"1\"\n          end'\n" % SWITCH + run_ok,
                 ((3, quote),)),
                ("the switch line inside a step name's quoted scalar over the env: lines (Z04b)", "last",
                 '      - name: "Quoted name\n        env:\n          %s: \'1\'\n        tail"\n' % SWITCH + run_ok, ((1, quote),)),
                ("a quoted scalar opened on a later key's line (Z14)", "last",
                 '      - name: Quoted text two (pytest)\n        env:\n          A: plain\n          B: "open\n          %s: \'1\'\n'
                 '          "\n' % SWITCH + run_ok, ((4, quote),)),
                ("a double-quoted run whose \\n escape starts a second, unflagged pytest (Q01)", "last, switch",
                 '      - name: Escaped newline (pytest)\n        run: "python -m pytest tests/test_a.py -q -p no:anyio \\npytest tests/test_b.py -q"\n',
                 ((2, escape),)),
                ("a double-quoted run whose \\x escape spells pytest (Q02)", "last",
                 '      - name: Escaped word\n        run: "python -m py\\x74est tests/test_a.py -q"\n', ((2, escape),)),
                ("a double-quoted env key whose \\x escape spells the switch, set to 0 (Q03)", "last, switch",
                 '      - name: Escaped key (pytest)\n        env:\n          "ROMP_SDK_\\x52EQUIRE": "0"\n' + run_ok, ((3, escape),))):
            with self.subTest(form=label):
                if where == "job":
                    src, first = self._with_job_before_shell(text)
                elif where == "first":
                    src, first = self._with_first_step_in_shell_job(text)
                else:
                    src, first = self._with_step_in_shell_job(text, self._with_shell_job_env(self.src) if "switch" in where else None)
                want = [(first + k - 1, src.splitlines()[first + k - 2].strip(), what) for k, what in named]
                self.assertEqual(unread_yaml_forms(src), want, label)
                self.assertEqual((self._new_bad(src), pytest_line_census(src)[1], switch_line_census(src)[1], unread_job_keys(src)[1]),
                                 ([], [], [], []), "%s: the refusal is the one red" % label)
        # a job env's quoted scalar over several lines holding the switch line (Z03): refused at its opening line
        src = self.src.replace("\n  shell:\n    name: Shell", '\n  shell:\n    env:\n      NOTES: "first\n      %s: \'1\'\n      end"\n    name: Shell' % SWITCH, 1)
        self.assertNotEqual(src, self.src, "the shell job's header moved: re-anchor this case")
        src, _first = self._with_step_in_shell_job("      - name: Job quoted text (pytest)\n" + run_ok, src)
        at = [n + 1 for n, l in enumerate(src.splitlines()) if l == '      NOTES: "first']
        self.assertEqual(unread_yaml_forms(src), [(at[0], 'NOTES: "first', quote)])
        # a flow collection continued past its line is refused at its opening line, and the lines inside it are read as
        # flow content: an alias after a dash there was not named (an anchored step aliased behind a name continued onto
        # a line opening with `[`); and a flow sequence of values over two lines is refused alone
        src, first = self._with_job_before_shell("  anch:\n" + sw_job + "    steps:\n      - &pystep\n        name: Anchored step (pytest)\n" + run_ok +
                                                 "  alias:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Prior\n          [y\n      - *pystep\n"
                                                 "      - name: Closer y]\n")
        self.assertEqual([(n - first + 1, w) for n, _t, w in unread_yaml_forms(src)],
                         [(6, "an anchor (&pystep)"), (13, "a flow collection ([) continued past its line")])
        src, first = self._with_first_step_in_shell_job("      - uses: ./a\n        with:\n          list: ['3.10',\n            main]\n")
        self.assertEqual(unread_yaml_forms(src), [(first + 2, "list: ['3.10',", "a flow collection ([) continued past its line")])
        # a refused quoted scalar is followed to its close: its later lines are its text, never nodes, so a second line
        # opening with `&` is not also an anchor
        src, first = self._with_first_step_in_shell_job('      - name: "Build\n          &x and *y test"\n        run: echo hi\n')
        self.assertEqual(unread_yaml_forms(src), [(first, '- name: "Build', quote)])
        # a double-quoted scalar's escaped quote does not close it, so the text after the escape is its text: the value
        # below is refused once, for the escape, and its `*y` is not an alias (the first verify pass's Y27: the escape
        # rule had no case)
        src, first = self._with_first_step_in_shell_job('      - uses: ./a\n        with: {a: "x\\", *y"}\n')
        self.assertEqual(unread_yaml_forms(src), [(first + 1, 'with: {a: "x\\", *y"}', escape)])
        # the controls: quoted scalars closed on their line, a single-quoted one holding `''`, and a double-quoted one
        # without a backslash, in a run, a name and an action's inputs
        for label, text in (("closed quoted scalars", '      - name: "Quoted (x)"\n        run: \'echo \'\'a\'\' "b"\'\n'),
                            ("a double-quoted value in a flow mapping", '      - uses: ./a\n        with: {a: "x, *y", b: \'z\'}\n')):
            with self.subTest(control=label):
                self.assertEqual(unread_yaml_forms(self._with_first_step_in_shell_job(text)[0]), [], label)

    def test_a_comment_in_a_flow_collection_with_no_space_before_it_is_refused_and_the_collection_read_as_open(self):
        # the fail-closed design's second verify pass (2026-09-23): PyYAML and yaml.v3 read a `#` right after `[`, `{`,
        # `,` or a closing quote inside a flow collection as a comment, so the collection stays open onto the next lines;
        # the scan read it as a scalar, closed the collection on its line and read only the first node of each line
        # after it. Behind such a `#` an anchored flow step and its alias (D01), a flow step whose double-quoted run
        # holds `\n` and a second pytest without the switch or the flag (D02, which the census excused as a pip
        # install), and a flow mapping's anchored key and its alias (D04) each read green at the round-4 takes head and
        # at the fail-closed head. The `#` is refused, the collection is refused as continued past its line, and its
        # later lines are read as flow content, so each form behind it is named; nothing else here is red
        comment = "a comment in a flow collection with no space before it"
        open_seq = "a flow collection ([) continued past its line"
        open_map = "a flow collection ({) continued past its line"
        for label, where, text, named in (
                ("an anchored flow step and its alias, each behind `[#` (D01)", "job",
                 "  anch:\n    runs-on: ubuntu-latest\n    steps: [#]\n"
                 "      {uses: actions/checkout@v4}, &hidstep {name: Hidden, run: echo hidden} ]\n"
                 "  alias:\n    runs-on: ubuntu-latest\n    steps: [#]\n      {uses: actions/checkout@v4}, *hidstep ]\n",
                 ((3, comment), (3, open_seq), (4, "a flow mapping holding the key 'run'"), (4, "an anchor (&hidstep)"),
                  (7, comment), (7, open_seq), (8, "an alias (*hidstep)"))),
                ("a flow step whose double-quoted run starts a second, unflagged pytest, behind `[#` (D02)", "job",
                 "  hid:\n    runs-on: ubuntu-latest\n    steps: [#]\n"
                 '      {uses: actions/checkout@v4}, {run: "true; pip install pytest\\npytest tests/test_a.py -q"} ]\n',
                 ((3, comment), (3, open_seq), (4, "a double-quoted scalar holding a backslash escape"),
                  (4, "a flow mapping holding the key 'run'"))),
                ("a flow mapping's anchored key and its alias, each behind a closing quote's `#` (D04)", "first",
                 '      - uses: ./.github/actions/x\n        with: {a: "b"#}\n          , &hidkey c: e}\n'
                 '      - uses: ./.github/actions/y\n        with: {a: "b"#}\n          , *hidkey : f}\n',
                 ((2, comment), (2, open_map), (3, "an anchor (&hidkey)"), (5, comment), (5, open_map), (6, "an alias (*hidkey)")))):
            with self.subTest(form=label):
                src, first = (self._with_job_before_shell if where == "job" else self._with_first_step_in_shell_job)(text)
                want = [(first + k - 1, src.splitlines()[first + k - 2].strip(), what) for k, what in named]
                self.assertEqual(unread_yaml_forms(src), want, label)
                self.assertEqual((self._new_bad(src), pytest_line_census(src)[1], switch_line_census(src)[1], unread_job_keys(src)[1]),
                                 ([], [], [], []), "%s: the refusal is the one red" % label)
        # the controls: a `#` inside a plain scalar in a flow collection is the scalar's text, and a spaced comment
        # after a flow collection that closes on its line is a comment; neither is refused
        for label, text in (("a plain scalar holding #", "      - uses: ./a\n        with: {pattern: a#b, list: [c#d]}\n"),
                            ("a spaced comment after a closed collection", "      - uses: ./a\n        with: {a: b} # c\n")):
            with self.subTest(control=label):
                self.assertEqual(unread_yaml_forms(self._with_first_step_in_shell_job(text)[0]), [], label)

    def test_a_block_scalar_header_on_the_line_after_its_key_is_refused_and_its_lines_are_text(self):
        # found closing the fail-closed design's first verify pass (2026-09-23): YAML reads `run:` with its `|` header on
        # the next line as a literal block, and the parser folded it as a plain scalar, one command, so a first pytest
        # without the flag took the flag of the second and read ok (H01, and H02 with a tag on the key's line; silent at
        # the round-4 takes head and at the owner's fail-closed head). The scan refuses such a header, and takes the
        # block's column from the key the last content line left open, so the block's lines are its text: a `*)` line
        # there was refused as an alias (the first verify pass's Y13, a red on valid YAML for the wrong reason)
        two = "          python -m pytest -q tests/test_a.py\n          python -m pytest -q -p no:anyio tests/test_b.py\n"
        header = "a block scalar header on the line after its key"
        for label, text in (("a literal block (H01)", "      - name: Header next (pytest)\n        run:\n          |\n" + two),
                            ("a tag on the key's line (H02)", "      - name: Header next tagged (pytest)\n        run: !!str\n          |\n" + two)):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text, self._with_shell_job_env(self.src))
                self.assertEqual(unread_yaml_forms(src), [(first + 2, "|", header)], label)
                self.assertEqual((self._new_bad(src), pytest_line_census(src)[1], switch_line_census(src)[1], unread_job_keys(src)[1]),
                                 ([], [], [], []), "%s: the refusal is the one red" % label)
        for label, text in (("a case statement's `*)` line (Y13)", "      - name: Header next line\n        run:\n          |\n"
                                                                    "          case \"$x\" in\n          *) echo other ;;\n          esac\n"),
                            ("a comment line between the key and the header", "      - name: Header after a comment\n        run:\n"
                                                                               "          # the block below\n          |\n          *) echo other ;;\n")):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text)
                at = first + text.splitlines().index("          |")
                self.assertEqual(unread_yaml_forms(src), [(at, "|", header)], label)


# ---------------------------------------------------------------------------------------------------------------------
# The launcher census (round 3's ruling, 2026-09-20; item 5 of the module docstring): every pytest the suite itself
# starts, in a form _launchers_in reads, passes -p no:anyio. The workflow's flag blocks anyio's plugin in the step's own process; a pytest child a test
# spawns is a new pytest process in the same interpreter, where the SDK step installed anyio, and without the flag it
# auto-loads the plugin, as an in-process pytest.main does. On 2026-09-20, before the launchers gained the flag, one of
# nine passed it, and this module, ci.yml and tests/README.md said the cells' plugin set was the box's. The rule now:
# every argv under tests/ that runs pytest, and every in-process pytest.main (round 4's ruling, 2026-09-23), passes the
# flag or is in LAUNCHERS_LISTED with a reason, in the forms _launchers_in reads; its docstring states what it leaves
# unread. The population is derived from the modules' syntax by
# child_pytest_launchers (its docstring and _launchers_in's are the rule); the derivation case prints the listing:
#   python -m pytest tests/test_ci_sdk_pin.py -q -p no:cacheprovider -p no:anyio -k ChildPytestLaunchers -rP
# ---------------------------------------------------------------------------------------------------------------------
# the text prefilter (child_pytest_launchers): a module is parsed when its text spells pytest or py.test, or holds a star
# import, and is skipped without a parse otherwise. No word boundaries, so the one token `-mpytest` counts (until
# 2026-09-21 the prefilter was `\bpytest\b`, which it does not match, and a module whose only spelling was that token was
# skipped without a parse while _launchers_in read it). A star import counts whatever its module (the fail-closed design's
# second verify pass, 2026-09-23: a module that star-imported a helper re-exporting pytest.main, and never spelled
# pytest, was skipped, so the refusal beside such a star import never ran there). What the prefilter skips is the
# census's residual, and the key is not a proof that the module runs no pytest: an argv whose -m module name is a name,
# or whose pytest is spelled through adjacent string literals or an escape, reads as a launcher or is refused in a
# parsed module and gives no row in a skipped one
PYTEST_TEXT_RE = re.compile(r"pytest|py\.test")
STAR_IMPORT_TEXT_RE = re.compile(r"import[\s\\]*\*")    # `import *`, `import*`, or the star after a backslash continuation
# a pytest command inside ONE string: `python -m pytest` (any interpreter spelling), or pytest / py.test by name or path,
# at command position (the start of the string, or after whitespace, `;`, `&`, `|` or `(`); or a `pytest.main(` call, an
# in-process pytest inside a `-c` string or a shell string (2026-09-21)
PYTEST_IN_STRING_RE = re.compile(r"(?:^|[\s;&|(])(?:\S*python[0-9.]*\s+-m\s*pytest|(?:\S*/)?(?:pytest|py\.test))(?=\s|$)|\bpytest\.main\s*\(")
PYTHON_NAME_RE = re.compile(r"python[0-9.]*t?(?:\.exe)?")       # a python-named constant: python, python3, python3.12, python3.14t
INTERPRETER_OPTS_WITH_VALUE = ("-X", "-W")                         # CPython options whose value is the next element
SUBPROCESS_FUNCS = ("run", "Popen", "call", "check_call", "check_output")
# The calls the census reads, by their qualified names (a module's own import and assignment names resolve to these):
# a first argument that is an argv or a command string, with the keyword that argument may be passed by; the calls whose
# positional arguments are the argv, with the slice of them that is (a spawn form's mode first and an e form's env last
# are not); and the calls that run pytest in the calling process (round 4's ruling, 2026-09-23, F). The os v forms
# (execv, spawnv, posix_spawn) take their argv as one list, which the literal walk reads wherever it is built.
FIRST_ARG_CALLS = dict([("subprocess." + f, "args") for f in SUBPROCESS_FUNCS]
                       + [("subprocess.getoutput", "cmd"), ("subprocess.getstatusoutput", "cmd"), ("os.system", "command"),
                          ("os.popen", "cmd"), ("asyncio.create_subprocess_shell", "cmd"),
                          ("asyncio.subprocess.create_subprocess_shell", "cmd")])
POSITIONAL_ARGV_CALLS = {"asyncio.create_subprocess_exec": (0, None), "asyncio.subprocess.create_subprocess_exec": (0, None),
                         "os.execl": (0, None), "os.execlp": (0, None), "os.execle": (0, -1), "os.execlpe": (0, -1),
                         "os.spawnl": (1, None), "os.spawnlp": (1, None), "os.spawnle": (1, -1), "os.spawnlpe": (1, -1)}
IN_PROCESS_CALLS = ("pytest.main", "pytest.console_main", "_pytest.config.main", "_pytest.config.console_main")
# every call the census reads, and every dotted prefix of one: the only paths a name's binding keeps (_launchers_in), since
# a path outside this set can reach none of those calls by an attribute
CENSUS_CALLS = tuple(FIRST_ARG_CALLS) + tuple(POSITIONAL_ARGV_CALLS) + IN_PROCESS_CALLS + ("shlex.split",)
CENSUS_PATHS = frozenset(".".join(c.split(".")[:k]) for c in CENSUS_CALLS for k in range(1, c.count(".") + 2))
CENSUS_STAR_MODULES = frozenset(c.rpartition(".")[0] for c in CENSUS_CALLS)   # a star import the census reads comes from one
# what a refusal beside a star import from a module the census does not read asks for, and what it does not read (the
# fail-closed design's third verify pass, 2026-09-24: the message said a name imported by name would be read, and an
# import by name from a module other than one of these binds a name the census reads as no launcher, so it gives no row)
STAR_REFUSAL_REMEDY = ("not read as a launcher until the star import is replaced by imports by name from the modules that "
                       "define the calls the census reads (%s); a name imported by name from any other module, a relative "
                       "one included, is read as no launcher and gives no row" % ", ".join(sorted(CENSUS_STAR_MODULES)))
BUILTIN_NAMES = frozenset(dir(builtins))
UNBOUND_MODULES = ("subprocess", "os", "shlex", "asyncio", "pytest", "_pytest")   # a bare name the module never binds reads as itself
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
    '<module>'), kind (_argv_command's answer, after the call's name for positional arguments; "an argv literal" for a
    literal it reports unparsed; the call that got a string; "<call> (in process)"; or "a call the census cannot
    resolve"), argv (the constant elements in order, None for an expression), flag (_passes_flag), unparsed (None, or
    why the command was not read as an argv).
    Read: every list or tuple literal in the module whose command is pytest (_argv_command: `-m pytest` after an
    interpreter head through interpreter options, pytest by name or path), wherever it is built: in the subprocess
    call, in a helper that passes it on, in a variable extended later, so a helper-built argv is counted.
    Also read (round 4's ruling, 2026-09-23): the positional arguments of asyncio.create_subprocess_exec and of the
    os.exec and os.spawn l forms, as an argv (POSITIONAL_ARGV_CALLS: a spawn form's mode and an e form's env set
    aside), and a call that runs pytest in this process (IN_PROCESS_CALLS: pytest.main, pytest.console_main and
    _pytest.config's two), a launcher whose argv is its first positional argument or args= and must carry the flag
    itself. A call is known by its qualified name through the module's own names for it that the census resolves: an
    absolute import (an alias, and a star import from a module whose calls it reads, CENSUS_STAR_MODULES, included),
    whose name stands for the call only when the import names the module that defines it, and a plain or annotated
    assignment from such a name, each binding placed where Python places it (home: in its own scope, at the module under
    a global declaration, in the enclosing function that binds the name under a nonlocal one) and looked up in the
    scopes Python looks it up in (chain: the call's own scope, which for a header expression, a decorator, a default, an
    annotation, a return annotation, a class's bases and keywords or a type parameter, is the scope around its def,
    lambda or class (scope_of), the functions around it with class bodies skipped, their global declarations with them,
    the module; straight to the module under a global declaration of the call's own scope or a function around it), a
    name bound more than once there standing for every path it is bound to; a module name that no scope on that chain
    binds (a star import may have brought it) reads as itself. Unparsed, and red in
    ChildPytestLaunchers until spelled as an argv or rewritten: a call
    whose callee's name this resolution cannot resolve (the owner's fail-closed design, 2026-09-23; unresolved): one
    inside a comprehension or generator expression, outside its first iterable, in a class body that binds the name
    or declares it global, where Python looks the name up past the class and the census does not model that scope; and, in a module with a
    star import from a module outside CENSUS_STAR_MODULES (or a relative one), whose names the census does not read,
    one through a name the lookup takes to the module: a name the module binds, which the star import may rebind, or a
    name no scope binds and no builtin names, which it may bring; and one through a name a function binds by a plain
    or annotated assignment from a name or an attribute whose root name is one of those, along a chain of such
    assignments (from_star). A star import binds at the module, so only a function scope on the lookup that binds the
    name, other than by such an assignment, is taken as proof that the call does not reach it; a class body's binding
    is not, since the body reads the name past the class until its own binding runs. Unparsed too: a list or tuple literal that may run pytest and
    the census cannot tell (after an interpreter head, a -m whose module name is not a constant, or an element that is
    not a constant right before `pytest`; _argv_command's docstring); a constant string or f-string, written at the
    call, handed to subprocess.run, Popen, call, check_call, check_output, getoutput or getstatusoutput, to os.system
    or os.popen, or to asyncio.create_subprocess_shell (FIRST_ARG_CALLS, by position or by the call's own keyword), or
    through shlex.split, whose text spells a pytest command or a `pytest.main(` call (PYTEST_IN_STRING_RE); an argv
    handed to those calls, or given as the positional arguments above, whose command is not pytest but carries a
    pytest command inside one element: any element when the head is a shell (SHELL_NAMES) run with -c, else a
    multi-word element (a `-c` string running pytest.main; a lone `pytest` element is a package name on a pip line, or
    an argument); and an in-process call whose argv is not a list or tuple literal (a name, or no argument at all, which
    reads sys.argv). A module that does not parse is one unparsed row. A list or tuple on the right of an `in` test is
    a set of names, not an argv, and is not read. Not read, stated as the residual and each pinned by a case with no
    row (test_each_form_outside_the_read_gives_no_row): an argv assembled one element at a time (append calls); a
    command string held in a variable or built with %, + or .format, a `-c` string held in a variable among them; any
    call, string or in process, reached through a name this resolution does not reach and does not refuse, among them
    one bound other than by an import or a plain or annotated assignment (tuple unpacking, a walrus, a conditional
    expression, a parameter default), one imported by name from a module that does not define the call (a helper that
    re-exports pytest.main; the census reads the name as no launcher) or by a relative import (which binds nothing the
    census reads), an attribute of a class or an instance (`T.m`, `self.m`), one reached through getattr, importlib or
    runpy, beside a star import from a module the census does not read, a builtin name or a module name no scope binds
    (UNBOUND_MODULES), read as the builtin or the module, which the star import may rebind, a name a function binds from
    such a star import's name other than by a plain or annotated assignment from a name or an attribute (from a call's
    result or a subscript, as a parameter or a loop target), read as the function's own, and a call in a class body
    through a name the class binds, read as the class's binding, where the body reads the name past the class until that
    binding runs (a class body's call of the module's pytest.main before the class binds the name to something else
    gives no row; found closing the first verify pass, 2026-09-23); and a string that spells pytest anywhere else (a
    script written to a file, an exec; the suite's synthetic tool-call fixtures spell `uv run pytest -q` by the dozen),
    which is data, not a command."""
    base = os.path.basename(filename)
    try:
        tree = ast.parse(src, filename=filename)
    except SyntaxError as e:
        return [{"file": base, "line": e.lineno or 1, "func": "<module>", "kind": "module", "argv": [], "flag": False,
                 "unparsed": "the module does not parse under this interpreter (%s), so nothing in it was read" % e.msg}]
    parents = {}
    membership = set()          # the right operands of `x in (...)` / `x not in [...]`: sets of names, never an argv
    # gathered in this walk, not walks of their own (walking every module is most of the census's cost): the imports,
    # the assignments from a name, the global and nonlocal statements, and the header expressions: each expression
    # Python evaluates where a def, lambda or class stands rather than in its body (a decorator, a default, an
    # annotation, a return annotation, a class's bases and keywords, a type parameter), mapped to that def or class
    imports, assigns, decls, header = [], [], [], {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
        if isinstance(parent, ast.Compare):
            membership.update(id(c) for c, op in zip(parent.comparators, parent.ops) if isinstance(op, (ast.In, ast.NotIn)))
        elif isinstance(parent, (ast.Import, ast.ImportFrom)):
            imports.append(parent)
        elif isinstance(parent, (ast.Assign, ast.AnnAssign)) and isinstance(parent.value, (ast.Name, ast.Attribute)):
            assigns.append((parent, parent.targets if isinstance(parent, ast.Assign) else [parent.target], parent.value))
        elif isinstance(parent, (ast.Global, ast.Nonlocal)):
            decls.append(parent)
        elif isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.arguments, ast.arg)):
            if isinstance(parent, ast.arg):
                if parent.annotation is not None:
                    header[parent.annotation] = parents[parents[parent]]
            elif isinstance(parent, ast.arguments):
                header.update((h, parents[parent]) for h in parent.defaults + parent.kw_defaults if h is not None)
            else:
                parts = parent.decorator_list + list(getattr(parent, "type_params", ()))
                parts += parent.bases + parent.keywords if isinstance(parent, ast.ClassDef) else [parent.returns]
                header.update((h, parent) for h in parts if h is not None)

    def func_of(node):
        while node in parents:
            node = parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return node.name
        return "<module>"

    scopes = {}

    def scope_of(node):
        """The scope a node is evaluated or bound in: the nearest function, lambda or class around it, None for the
        module; a header expression (a decorator, a default, an annotation, a return annotation, a class's bases and
        keywords, a type parameter) and everything in it is in the scope around its def, lambda or class, where Python
        evaluates it (the fail-closed design's third verify pass, 2026-09-24: in the def's own scope, `main(["-q"])` as
        a default, a decorator's argument, a base or an annotation beside the def's own binding of main read that
        binding and gave no row where the module's pytest.main ran; LD1 to LD5). Memoized along the walk up, since
        every name in every call is resolved through it; the walk from a header expression jumps to its def or class,
        so the nodes between them (a parameter, the arguments node) keep the def's own scope."""
        path, found = [], None
        while node not in scopes:
            up = parents.get(node)
            if up is None:
                break
            path.append(node)
            owner = header.get(node)
            if owner is not None:
                node = owner
                continue
            if isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                found = up
                break
            node = up
        else:
            found = scopes[node]
        for n in path:
            scopes[n] = found
        return found

    declared = {}               # {scope: {name: "global" or "nonlocal"}}, as the scope's own statements declare it
    for node in decls:
        where = scope_of(node)
        for name in node.names:
            declared.setdefault(where, {})[name] = "global" if isinstance(node, ast.Global) else "nonlocal"
    bound_cache = []

    def bound_by_any():
        """{scope: the names a statement in that scope binds}, before a global or nonlocal declaration moves them: an
        assignment, deletion or loop target, a def or class name, a parameter, an import, an except or match capture. A
        comprehension's own targets are left out, since they bind in the comprehension. Built on first use, since only
        a nonlocal declaration and a star import from a module the census does not read need it."""
        if not bound_cache:
            table, own = {}, set()
            for node in ast.walk(tree):
                if isinstance(node, ast.comprehension):
                    own.update(id(t) for t in ast.walk(node.target))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and id(node) not in own:
                    names = [node.id]
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names = [node.name]
                elif isinstance(node, ast.arg):
                    names = [node.arg]
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.asname or a.name.split(".")[0] for a in node.names if a.name != "*"]
                elif isinstance(node, ast.ExceptHandler) or type(node).__name__ in ("MatchAs", "MatchStar"):
                    names = [node.name] if node.name else []
                elif type(node).__name__ == "MatchMapping":
                    names = [node.rest] if node.rest else []
                else:
                    continue
                for name in names:
                    table.setdefault(scope_of(node), set()).add(name)
            bound_cache.append(table)
        return bound_cache[0]

    def home(scope, name):
        """The scope a binding of `name` made in `scope` lands in, as Python places it (the owner's fail-closed design,
        2026-09-23): the module for a name `scope` declares global; for one it declares nonlocal, the nearest function
        around it that binds the name itself, class bodies skipped; else `scope`. Until then a binding stayed in its own
        scope, so `global run` then `from subprocess import run` in a setup function, called from a test, gave the
        test's call no row, where the module-wide read before round 4's verify had read it."""
        kind = declared.get(scope, {}).get(name)
        if kind == "global":
            return None
        if kind == "nonlocal":
            up = scope_of(scope)
            while up is not None:
                if not isinstance(up, ast.ClassDef):
                    outer = declared.get(up, {}).get(name)
                    if outer == "global":
                        return None
                    if outer is None and name in bound_by_any().get(up, ()):
                        return up
                up = scope_of(up)
        return scope

    def chain(name, scope, first=True):
        """The scopes Python looks `name` up in from `scope`, in order: `scope` itself (a class body only when `first`,
        the use sitting in it), each function around it with class bodies skipped, then the module (None); a scope that
        declares the name global sends the lookup straight to the module, past the functions around it. A class body the
        use does not sit in is passed before its declarations are read, since a class body's global statement governs
        that body alone, as Python applies it (the fail-closed design's third verify pass, 2026-09-24: read first, `global
        m` in a class body sent a method's lookup to the module, past the enclosing function's `m = pytest.main`, and the
        call gave no row). (A scope that declares it nonlocal holds no binding of it, since home moves each one out, so
        the lookup passes it by.)"""
        while scope is not None:
            if not first and isinstance(scope, ast.ClassDef):
                scope = scope_of(scope)
                continue
            if declared.get(scope, {}).get(name) == "global":
                break
            yield scope
            scope, first = scope_of(scope), False
        yield None

    # What each name stands for, as dotted paths, scope by scope (review round 4's verify, 2026-09-23: until then one
    # dict held the whole module and the last binding won, so a launcher's name rebound in another function, `from json
    # import loads as run` beside `from subprocess import run`, read as the other binding and its launcher gave no
    # row). A scope's bindings: `import a.b` binds a, `import a.b as x` and `from a import b as x` bind x to a.b, a star
    # import from a module whose calls the census reads binds each of those calls' names, and `m = pytest.main` binds m
    # to what the right side names. A name bound more than once in one scope stands for every path it is bound to (no
    # flow is followed: a false row, never a lost one). Only the paths that can reach a call the census reads are kept
    # (CENSUS_PATHS), so a name bound to anything else is bound and stands for nothing, and `p = p.parent` cannot grow.
    # A binding lands where Python puts it (home): the module for a name declared global, the enclosing function for
    # one declared nonlocal
    bindings = {}

    def bind(scope, name, paths):
        names = bindings.setdefault(home(scope, name), {})
        fresh = name not in names
        cur = names.setdefault(name, set())
        grow = {p for p in paths if p in CENSUS_PATHS} - cur
        cur |= grow
        return fresh or bool(grow)

    for node in imports:
        scope = scope_of(node)
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    bind(scope, a.asname, {a.name})
                else:
                    top = a.name.split(".")[0]
                    bind(scope, top, {top})
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                if a.name == "*":
                    for call in CENSUS_CALLS:
                        if call.rpartition(".")[0] == node.module:
                            bind(scope, call.rpartition(".")[2], {call})
                else:
                    bind(scope, a.asname or a.name, {node.module + "." + a.name})

    def resolve(name_node, skip_class=False):
        """The paths a name stands for where it is used: the innermost scope that binds it, looked up as Python looks
        it up (chain: the use's own scope, then each function around it, a class body skipped, then the module; global
        and nonlocal declarations followed); a module name that no scope on that chain binds stands for itself (a star
        import from a module whose calls the census reads may have brought it). `skip_class` skips the use's own class
        body too, as Python does for a use inside a comprehension there."""
        name = name_node.id
        for scope in chain(name, scope_of(name_node), not skip_class):
            if name in bindings.get(scope, {}):
                return bindings[scope][name]
        return {name} if name in UNBOUND_MODULES else set()

    def dotted(expr):
        attrs = []
        while isinstance(expr, ast.Attribute):
            attrs.append(expr.attr)
            expr = expr.value
        if not isinstance(expr, ast.Name):
            return set()
        return {".".join([root] + attrs[::-1]) for root in resolve(expr)}

    # a chain of names resolves in as many passes as it has links; the sets only grow, so the passes end
    for _ in range(len(assigns)):
        changed = False
        for node, targets, value in assigns:
            paths = dotted(value)
            if paths:
                for t in targets:
                    if isinstance(t, ast.Name) and bind(scope_of(node), t.id, paths):
                        changed = True
        if not changed:
            break

    def is_shlex_split(node):
        return isinstance(node, ast.Call) and "shlex.split" in dotted(node.func)

    # the refusals (the owner's fail-closed design, 2026-09-23): a name in a call's callee position that this resolution
    # cannot resolve is named, never passed. Until then a comprehension in a class body, whose names Python looks up
    # past the class, read the class's binding, and a name a star import from an unread module brought read as unbound:
    # each gave no row where pytest.main ran. Its first verify pass found the same for a module binding such a star
    # import rebinds (S4, S5), and closing that pass found it for a module binding to a launcher the census reads (S9)
    # and for a class body's binding (K5)
    unread_stars = sorted({"." * node.level + (node.module or "") for node in imports if isinstance(node, ast.ImportFrom)
                           and any(a.name == "*" for a in node.names) and (node.level or node.module not in CENSUS_STAR_MODULES)})

    def in_class_comprehension(node):
        """True when `node` sits in a comprehension or generator expression whose scope is a class body, outside its
        first iterable (which Python evaluates in the class body itself)."""
        crossed, first_iter = False, None
        while node in parents:
            if node in header:          # a header expression is evaluated where its def, lambda or class stands
                node, first_iter = header[node], None
                continue
            up = parents[node]
            if isinstance(up, ast.comprehension):
                first_iter = up if node is up.iter else None
            elif isinstance(up, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                crossed = crossed or not (first_iter is not None and up.generators[0] is first_iter)
                first_iter = None
            elif isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return False
            elif isinstance(up, ast.ClassDef):
                return crossed
            node = up
        return False

    def homes_of(name):
        """The scopes a statement binds `name` in, each moved where a global or nonlocal declaration puts it."""
        return {home(where, name) for where, names in bound_by_any().items() if name in names}

    def star_lands(name, scope):
        """Where the lookup of `name` from `scope` lands beside a star import from a module the census does not read: the
        function scope on the lookup that binds the name, None for the module, or "unbound". A class body's binding is
        passed by: the body reads the module's name until its own binding runs."""
        homes = homes_of(name)
        return next((s for s in chain(name, scope) if s in homes and not isinstance(s, ast.ClassDef)), "unbound")

    assigned_from = []

    def from_star(name, scope, seen):
        """True when `name`, looked up from `scope` beside such a star import, may hold a name the star import brings or
        rebinds (the fail-closed design's second verify pass, 2026-09-23): the lookup lands at the module, or at no
        binding for a name that is neither a builtin nor a module name the census reads as itself (UNBOUND_MODULES), or
        at a function scope where a plain or annotated assignment binds it from a name or an attribute whose root name is
        itself from the star import, followed along a chain of such assignments. Until then a function's binding was
        proof, so `run = main` in a test, main from the star import, then `run(["-q"])`, gave no row where pytest.main
        ran. A function binding made any other way (an import, a def, a parameter, a loop target, an assignment from a
        call or a subscript) is read as the function's own."""
        lands = star_lands(name, scope)
        if lands is None:
            return True
        if lands == "unbound":
            return name not in BUILTIN_NAMES and name not in UNBOUND_MODULES
        if not assigned_from:
            table = {}          # (the scope a binding lands in, name) -> [(the value's root name, the assignment's scope)]
            for node, targets, value in assigns:
                vroot = value
                while isinstance(vroot, ast.Attribute):
                    vroot = vroot.value
                if isinstance(vroot, ast.Name):
                    where = scope_of(node)
                    for t in targets:
                        if isinstance(t, ast.Name):
                            table.setdefault((home(where, t.id), t.id), []).append((vroot.id, where))
            assigned_from.append(table)
        if (lands, name) in seen:
            return False
        seen.add((lands, name))
        return any(from_star(vname, where, seen) for vname, where in assigned_from[0].get((lands, name), ()))

    def unresolved(func):
        """Why the census refuses to read a call through `func` (its root name), or None."""
        root = func
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        if isinstance(scope_of(root), ast.ClassDef) and in_class_comprehension(root) and resolve(root) != resolve(
                root, skip_class=True):          # a comprehension's scope_of is the class around it: the cheap test first
            return ("a call through %r inside a comprehension or generator expression in a class body that binds the name "
                    "or declares it global: Python looks the name up past the class there, and the census does not resolve "
                    "that scope, so it is not read as a launcher until the call moves out of the comprehension" % root.id)
        if unread_stars:
            # a star import binds at the module, so only a function scope on the lookup that binds the name proves the
            # call does not reach the star import's names; a class body's binding does not, since the body reads the
            # module's name until its own binding runs (the fail-closed design's first verify pass, 2026-09-23: a
            # module binding, `main = None` or `from json import loads as run`, that the star import then rebinds was
            # read as the module's own and gave no row where pytest ran)
            lands = star_lands(root.id, scope_of(root))
            if lands is None:
                return ("a call through %r, a name the module binds, in a module with a star import from %s, which the census "
                        "does not read (the star import may rebind it, and the census follows no order): %s"
                        % (root.id, ", ".join(unread_stars), STAR_REFUSAL_REMEDY))
            if lands == "unbound" and not resolve(root) and root.id not in BUILTIN_NAMES:
                return ("a call through %r, a name no scope here binds, in a module with a star import from %s, which the census "
                        "does not read (the name may come from it): %s" % (root.id, ", ".join(unread_stars), STAR_REFUSAL_REMEDY))
            if lands != "unbound" and from_star(root.id, scope_of(root), set()):
                return ("a call through %r, a name the function %s binds from a name the star import from %s may bring or "
                        "rebind (the census does not read that module): %s"
                        % (root.id, getattr(lands, "name", "<lambda>"), ", ".join(unread_stars), STAR_REFUSAL_REMEDY))
        return None

    out = []

    def row(node, kind, elts, unparsed=None):
        out.append({"file": base, "line": node.lineno, "func": func_of(node), "kind": kind, "argv": [_str(e) for e in elts],
                    "flag": _passes_flag(elts), "unparsed": unparsed})

    def element_command(node, what, elts):
        """An argv whose command is not pytest but that carries a pytest command inside one element: any element when
        the head is a shell run with -c, else a multi-word element (a `-c` string running pytest.main; a lone `pytest`
        element is a package name on a pip line, or an argument)."""
        c = [_str(e) for e in elts]
        shell = bool(c) and c[0] is not None and os.path.basename(c[0]) in SHELL_NAMES and "-c" in c
        hit = [t for t in c if t and PYTEST_IN_STRING_RE.search(t) and (shell or re.search(r"\s", t))]
        if hit:
            row(node, what, [], "a pytest command inside one element of the argv (%r), not read as the command" % hit[0])

    def call_row(node, what):
        """The row a call gives when its callee stands for `what` (every path it stands for is judged)."""
        if what in IN_PROCESS_CALLS:
            # a pytest session in this process: plugin autoload runs again inside it, whatever flag the outer run had,
            # so its own argv must carry the flag (tests-4's refuter's probe: -p no:anyio inside the call blocked it)
            arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "args"), None)
            kind = what + " (in process)"
            if isinstance(arg, (ast.List, ast.Tuple)):
                row(node, kind, arg.elts)
            elif arg is None:
                row(node, kind, [], "called with no argument, so its argv is sys.argv, which the census cannot read: not read "
                                    "as a launcher until its argv is a list or tuple literal")
            else:
                row(node, kind, [], "its argv is not a list or tuple literal, so the census cannot read the flag: not read as a "
                                    "launcher until it is one")
        elif what in POSITIONAL_ARGV_CALLS:
            lo, hi = POSITIONAL_ARGV_CALLS[what]
            elts = node.args[lo:hi]
            kind, unparsed = _argv_command(elts)
            if kind:
                row(node, "%s: %s" % (what, kind), elts)
            elif unparsed:
                row(node, "%s positional arguments" % what, [], unparsed)
            else:
                element_command(node, what, elts)
        elif what in FIRST_ARG_CALLS:
            arg = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == FIRST_ARG_CALLS[what]), None)
            if arg is None:
                return
            if isinstance(arg, (ast.List, ast.Tuple)):
                if _argv_command(arg.elts) == (None, None):      # a launcher or an unparsed argv has its row from the literal
                    element_command(node, what, arg.elts)
            elif is_shlex_split(arg):
                text = _text(arg.args[0]) if arg.args else None
                if text is not None and PYTEST_IN_STRING_RE.search(text):
                    row(node, what, [], "a pytest command in a shlex.split string, not read as an argv")
            else:
                text = _text(arg)
                if text is not None and PYTEST_IN_STRING_RE.search(text):
                    row(node, what, [], "a pytest command in a shell string, not read as an argv")

    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            kind, unparsed = _argv_command(node.elts) if id(node) not in membership else (None, None)
            if kind:
                row(node, kind, node.elts)
            elif unparsed:
                row(node, "an argv literal", [], unparsed)
            continue
        if not isinstance(node, ast.Call):
            continue
        refused = unresolved(node.func)
        if refused:
            row(node, "a call the census cannot resolve", [], refused)
            continue
        for what in sorted(dotted(node.func)):
            call_row(node, what)
    return out


def child_pytest_launchers(directory=None):
    """Every launcher and unparsed pytest command under tests/ (every *.py below `directory`, subdirectories included,
    __pycache__ skipped), by _launchers_in; `file` is the path relative to the directory. A module whose text spells
    neither pytest nor py.test and holds no star import (PYTEST_TEXT_RE, STAR_IMPORT_TEXT_RE) is skipped without a parse,
    and nothing in it is read: that is a residual, not a proof, since an argv there whose -m module name is a name, or
    whose pytest is spelled through adjacent string literals or an escape, runs pytest and gives no row. Parsing every
    module instead reds git commit-tree argv literals in tests/fixtures/, whose -m takes a message built with %, on
    valid code (2026-09-23)."""
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
            if not (PYTEST_TEXT_RE.search(src) or STAR_IMPORT_TEXT_RE.search(src)):
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
    """Every pytest the suite itself starts in a form _launchers_in reads, as a child or in its own process, passes
    -p no:anyio, held on the population of launchers under tests/ in those forms (item 5 of the module docstring). A child
    pytest is a new pytest process in the cell's interpreter, where the SDK step installed anyio, and an in-process
    pytest.main runs plugin autoload again; the workflow's flag reaches the step's own session alone, so a launcher
    without the flag auto-loads the plugin there (on 2026-09-20, before the launchers gained the flag, eight of nine did, and a synthetic broken
    anyio/pytest_plugin.py in a CI-shaped venv red tests in each of the six modules that spawned them, none of which imports the SDK; the same six were green
    with the flag on every launcher, 2026-09-20). The population is derived by child_pytest_launchers, keyed on the argv
    property; the flag check keys on the argv's constant elements and its message says so; a launcher without the flag
    is named with its file, line and enclosing function unless LAUNCHERS_LISTED carries it with a reason, and a listed
    entry whose key names no launcher, or names one that passes the flag, is stale and red. The modules known to spawn
    pytest are asserted present so an empty read is red; there is no count to keep. Red before the eight launchers
    gained the flag: the flag case named them (2026-09-20)."""
    KNOWN_MODULES = {"test_bats_bare_negation.py", "test_ci_sdk_pin.py", "test_claude_config_floor.py",
                     "test_env_value_redaction.py", "test_key_source_floor.py","test_served_tests_require.py", "test_session_host.py",
                     "test_supervised_floor.py", "test_tempdir_hygiene.py"}
    _found = None

    @classmethod
    def found(cls):
        if cls._found is None:      # once per process: every module under tests/ that spells pytest or holds a star import is parsed
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
        # a name a function binds itself is that function's, as Python looks it up: a local assignment or import of the
        # same name hides the module's launcher there, so the call runs something else and gives no row (the scope
        # lookup, review round 4's verify, 2026-09-23)
        self.assertEqual(_launchers_in('import os\nfrom subprocess import run\n\ndef helper():\n    run = os.getcwd\n'
                                       '    return run("pytest -q")\n', "t.py"), [], "a local assignment hides the module's name")
        self.assertEqual(_launchers_in('from subprocess import run\n\ndef helper():\n    from json import loads as run\n'
                                       '    return run("pytest -q")\n', "t.py"), [], "a local import hides the module's name")
        # a module the interpreter cannot parse is one unparsed row, never a silent skip
        rows = _launchers_in("def f(:\n    pass\n", "t.py")
        self.assertEqual([(r["kind"], r["flag"]) for r in rows], [("module", False)])
        self.assertIn("does not parse under this interpreter", rows[0]["unparsed"])

    # round 4's ruling (2026-09-23, F): the calls that start a pytest process beside subprocess's five and os.system and
    # os.popen, and the calls that run one in process. Until then each form below gave no row, parsed or unparsed, and the
    # census read green over it (the refuters' synthetic sources); the four controls at the end had a row then and keep it.
    STARTING_FORMS = (
        # a command string, run through a shell: read as the string calls are
        ("subprocess.getoutput", 'import subprocess\nsubprocess.getoutput("python -m pytest -q")\n', "unparsed", "a pytest command in a shell string"),
        ("subprocess.getstatusoutput", 'import subprocess\nsubprocess.getstatusoutput("pytest tests -q")\n', "unparsed", "a pytest command in a shell string"),
        ("getoutput imported by name, its cmd keyword", 'from subprocess import getoutput as out\nout(cmd="py.test -q")\n', "unparsed", "a pytest command in a shell string"),
        ("asyncio.create_subprocess_shell", 'import asyncio\nasyncio.create_subprocess_shell("python3 -m pytest -q")\n', "unparsed", "a pytest command in a shell string"),
        ("asyncio.subprocess.create_subprocess_shell", 'import asyncio.subprocess\nasyncio.subprocess.create_subprocess_shell("pytest -q")\n', "unparsed",
         "a pytest command in a shell string"),
        ("os.system imported by name, its command keyword", 'from os import system\nsystem(command="pytest -q")\n', "unparsed", "a pytest command in a shell string"),
        # an argv passed as positional arguments: read as an argv literal is
        ("asyncio.create_subprocess_exec", 'import asyncio, sys\nasyncio.create_subprocess_exec(sys.executable, "-m", "pytest", "-q")\n', False, "<interpreter> -m pytest"),
        ("asyncio.create_subprocess_exec with the flag, aliased", 'import asyncio as aio, sys\naio.create_subprocess_exec(sys.executable, "-m", "pytest", "-p", "no:anyio")\n',
         True, "<interpreter> -m pytest"),
        ("create_subprocess_exec imported by name", 'import sys\nfrom asyncio import create_subprocess_exec as spawn\nspawn(sys.executable, "-B", "-mpytest")\n',
         False, "<interpreter> -mpytest"),
        ("asyncio.subprocess.create_subprocess_exec", 'import asyncio.subprocess, sys\nasyncio.subprocess.create_subprocess_exec(sys.executable, "-m", "pytest")\n',
         False, "<interpreter> -m pytest"),
        ("os.execl", 'import os, sys\nos.execl(sys.executable, sys.executable, "-m", "pytest", "-q")\n', False, "<interpreter> -m pytest"),
        ("os.execlp, the console script by name, with the flag", 'import os\nos.execlp("pytest", "pytest", "-q", "-p", "no:anyio")\n', True, "pytest by name or path"),
        ("os.execle, its env last", 'import os, sys\nos.execle(sys.executable, "python", "-m", "pytest", {"A": "1"})\n', False, "<interpreter> -m pytest"),
        ("os.execlpe, its env last, the flag in one token", 'import os\nos.execlpe("python3", "python3", "-m", "pytest", "-pno:anyio", env)\n', True, "<interpreter> -m pytest"),
        ("os.spawnl, its mode first", 'import os, sys\nos.spawnl(os.P_WAIT, sys.executable, sys.executable, "-m", "pytest")\n', False, "<interpreter> -m pytest"),
        ("os.spawnlp", 'import os\nos.spawnlp(os.P_NOWAIT, "py.test", "py.test", "-q")\n', False, "pytest by name or path"),
        ("os.spawnle, mode first and env last", 'import os, sys\nos.spawnle(os.P_WAIT, sys.executable, "python", "-m", "pytest", env)\n', False, "<interpreter> -m pytest"),
        ("os.spawnlpe", 'import os\nos.spawnlpe(os.P_WAIT, "python3.12", "python3.12", "-m", "pytest", env)\n', False, "<interpreter> -m pytest"),
        ("positional arguments whose -m module is a name", 'import asyncio, sys\nasyncio.create_subprocess_exec(sys.executable, "-m", mod)\n', "unparsed",
         "a module name the census cannot read after -m"),
        ("positional arguments running a shell's -c", 'import asyncio\nasyncio.create_subprocess_exec("bash", "-c", "pytest -q")\n', "unparsed",
         "a pytest command inside one element of the argv"),
        ("os.execl running a shell's -c", 'import os\nos.execl("/bin/sh", "sh", "-c", "python -m pytest")\n', "unparsed", "a pytest command inside one element of the argv"),
        # in process: pytest.main or pytest.console_main by name, alias or import, and _pytest.config's main (tests-4's refuter)
        ("pytest.main, the flag in its list", 'import pytest\npytest.main(["-q", "-p", "no:anyio"])\n', True, "pytest.main (in process)"),
        ("pytest.main without the flag", 'import pytest\npytest.main(["-q", "tests/test_a.py"])\n', False, "pytest.main (in process)"),
        ("pytest.main under an alias, args=", 'import pytest as pt\npt.main(args=["-q", "-pno:anyio"])\n', True, "pytest.main (in process)"),
        ("from pytest import main, a tuple", 'from pytest import main\nmain(("-q",))\n', False, "pytest.main (in process)"),
        ("from pytest import main as a name", 'from pytest import main as run_tests\nrun_tests(["-q", "-p", "no:anyio"])\n', True, "pytest.main (in process)"),
        ("a name bound to pytest.main", 'import pytest\nm = pytest.main\nm(["-q"])\n', False, "pytest.main (in process)"),
        ("a chain of names, bound in reverse order", 'import pytest\nb = a\na = pytest.main\nb(["-q"])\n', False, "pytest.main (in process)"),
        ("_pytest.config.main", 'import _pytest.config\n_pytest.config.main(["-q"])\n', False, "_pytest.config.main (in process)"),
        ("from _pytest import config", 'from _pytest import config\nconfig.main(["-q"])\n', False, "_pytest.config.main (in process)"),
        ("from _pytest.config import main", 'from _pytest.config import main as cmain\ncmain(["-q", "-p", "no:anyio"])\n', True, "_pytest.config.main (in process)"),
        ("pytest.main with a list the census cannot read", 'import pytest\npytest.main(argv)\n', "unparsed", "its argv is not a list or tuple literal"),
        ("pytest.main with no argument", 'import pytest\npytest.main()\n', "unparsed", "no argument, so its argv is sys.argv"),
        ("pytest.console_main", 'import pytest\npytest.console_main()\n', "unparsed", "no argument, so its argv is sys.argv"),
        ("console_main imported by name", 'from pytest import console_main\nconsole_main()\n', "unparsed", "no argument, so its argv is sys.argv"),
        ("_pytest.config.console_main", 'from _pytest.config import console_main\nconsole_main()\n', "unparsed", "no argument, so its argv is sys.argv"),
        # a module name the module never binds reads as itself (a star import, a name injected), as before the ruling
        ("subprocess never imported by name", 'from helpers import *\nsubprocess.run("pytest -q", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        # names resolved by scope (review round 4's verify, attacks M4, 2026-09-23): until then one dict held the module and
        # the last binding won, so each launcher below, whose name another function rebinds, gave no row; so did a star
        # import from pytest, and a name bound twice in one scope read as its last binding alone
        ("a string call through a name rebound in another function",
         'from subprocess import run\n\ndef suite():\n    return run("python -m pytest -q", shell=True)\n\n'
         'def helper():\n    from json import loads as run\n    return run("{}")\n', "unparsed", "a pytest command in a shell string"),
        ("os.execl through a name rebound in another function",
         'import sys\nfrom os import execl as start\n\ndef suite():\n    start(sys.executable, sys.executable, "-m", "pytest", "-q")\n\n'
         'def helper():\n    from json import loads as start\n    return start("{}")\n', False, "<interpreter> -m pytest"),
        ("pytest.main imported, rebound in another function",
         'from pytest import main as run_tests\n\ndef suite():\n    return run_tests(["-q"])\n\n'
         'def helper():\n    from json import loads as run_tests\n    return run_tests("{}")\n', False, "pytest.main (in process)"),
        ("pytest.main assigned, rebound in another function",
         'import os\nimport pytest\n\ndef suite():\n    go = pytest.main\n    return go(["-q"])\n\ndef helper():\n    go = os.getcwd\n    return go()\n',
         False, "pytest.main (in process)"),
        ("pytest.main by a star import", 'from pytest import *\n\ndef suite():\n    return main(["-q"])\n', False, "pytest.main (in process)"),
        ("subprocess.run by a star import", 'from subprocess import *\nrun("pytest -q", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        ("a name bound twice in one scope, the launcher first",
         'import os, subprocess\nrun = subprocess.run\nrun = os.getcwd\nrun("pytest -q", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        # a method does not see its class body's names, as Python looks them up: a class attribute of the same name does
        # not hide the module's launcher from a method
        ("a class attribute does not hide the module's name from a method",
         'import os\nfrom subprocess import run\n\nclass T:\n    run = os.getcwd\n\n    def go(self):\n        return run("pytest -q", shell=True)\n',
         "unparsed", "a pytest command in a shell string"),
        # a binding lands where Python puts it (the owner's fail-closed design, 2026-09-23; the pre-push lenses' L03,
        # L04, L12 and the regression): a name a function declares global binds at the module, one it declares nonlocal
        # in the enclosing function that binds it. Until then each binding stayed in its own function and each call gave
        # no row; the regression's call had a row before round 4's verify made the resolution scoped
        ("the regression: a setup function's global import of subprocess.run, called from a test",
         'def _setup():\n    global run\n    from subprocess import run\ndef test_x():\n    _setup()\n'
         '    run("python -m pytest -q tests/test_a.py", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        ("pytest.main imported under a global declaration (L03)",
         'main = None\ndef setup():\n    global main\n    from pytest import main\ndef test():\n    return main(["-q", "tests/x.py"])\n',
         False, "pytest.main (in process)"),
        ("pytest.main imported under a nonlocal declaration, called by a sibling (L04)",
         'def outer():\n    main = print\n    def setup():\n        nonlocal main\n        from pytest import main\n'
         '    def go():\n        return main(["-q"])\n    setup()\n    return go()\n', False, "pytest.main (in process)"),
        ("a use under a global declaration reads the module's name, past an enclosing function's",
         'from subprocess import run\ndef outer():\n    from json import loads as run\n    def f():\n        global run\n'
         '        return run("pytest -q", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        ("a global assignment of pytest.main, the call in a nested function",
         'import pytest\ndef setup():\n    global go\n    go = pytest.main\ndef outer():\n    def inner():\n        return go(["-q"])\n',
         False, "pytest.main (in process)"),
        # a class body's global declaration governs that body alone: a method of the class looks the name up in the
        # function around the class (the fail-closed design's third verify pass, 2026-09-24: LG1, which had a row before
        # the scoped lookup and none after it until chain passed the class before reading its declarations)
        ("a method's call through a name its class declares global reads the enclosing function's binding (LG1)",
         'import pytest\ndef outer():\n    m = pytest.main\n    class C:\n        global m\n        def go(self):\n'
         '            return m(["-q"])\n    return C().go()\n', False, "pytest.main (in process)"),
        ("a class body's own call under its global declaration reads the module's binding, past the function's",
         'import pytest\nm = pytest.main\ndef outer():\n    from json import loads as m\n'
         '    class C:\n        global m\n        r = m(["-q"])\n    return C.r\n', False, "pytest.main (in process)"),
        # the refusals: a name in a call's callee position the resolution cannot resolve is named, never passed (the
        # pre-push lenses' L07, L14 and L09, each silent until then)
        ("a comprehension in a class body that binds the name (L07)",
         'from pytest import main as m\nclass T:\n    from json import loads as m\n    out = [m(["-q"]) for _ in (1,)]\n',
         "unparsed", "inside a comprehension or generator expression in a class body that binds the name"),
        ("a generator expression in a class body that binds the name (L14)",
         'from pytest import main as m\nclass T:\n    from json import loads as m\n    out = list(m(["-q"]) for _ in (1,))\n',
         "unparsed", "inside a comprehension or generator expression in a class body that binds the name"),
        ("a class body binding pytest.main, called in its comprehension",
         'import pytest\nclass T:\n    m = pytest.main\n    out = {k: m([k]) for k in ("-q",)}\n',
         "unparsed", "inside a comprehension or generator expression in a class body that binds the name"),
        # the class body's own lookup goes to the module under its global declaration, and its comprehension's goes to
        # the function around the class, which binds pytest.main (found closing the third verify pass, 2026-09-24: with
        # the declaration read on the lookup past the class, both read the module's json.loads and the call gave no row)
        ("a comprehension in a class body that declares the name global, the function around the class binding it (LG3)",
         'import pytest\nfrom json import loads as m\ndef outer():\n    m = pytest.main\n    class C:\n        global m\n'
         '        r = [m(["-q"]) for _ in (1,)]\n    return C.r\n',
         "unparsed", "inside a comprehension or generator expression in a class body that binds the name or declares it global"),
        ("a name no scope binds beside a star import from a module the census does not read (L09)",
         'from helpers_x import *\ndef go():\n    return main(["-q"])\n',
         "unparsed", "a name no scope here binds, in a module with a star import from helpers_x"),
        ("an attribute of such a name", 'from .helpers import *\nsp.run("pytest -q", shell=True)\n',
         "unparsed", "a name no scope here binds, in a module with a star import from .helpers"),
        # a comprehension's own target binds in the comprehension, not in the function around it, so it proves nothing
        # about the call beside it (the fail-closed design's first verify pass, 2026-09-23: S7; counted as the
        # function's binding, the call gave no row)
        ("a name the calling function binds only as a comprehension target, beside such a star import (S7)",
         'from helpers_x import *\ndef go():\n    [0 for main in ()]\n    return main(["-q"])\n',
         "unparsed", "a name no scope here binds, in a module with a star import from helpers_x"),
        # a module binding does not hide the star import's names: the star import may rebind it (the first verify
        # pass's S4 and S5, each silent until then; closing that pass, S9, a binding to a launcher the census reads,
        # called with an argv that is not pytest, gave no row either while the star import's pytest.main ran), and
        # neither does a class body's binding, which the body reads past until it runs (K5, found closing the pass)
        ("a module default rebound by such a star import (S4)", 'main = None\nfrom helpers_x import *\ndef go():\n    return main(["-q"])\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a module import rebound by such a star import (S5)",
         'from json import loads as run\nfrom helpers_x import *\ndef go():\n    return run("python -m pytest -q", shell=True)\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a module binding to subprocess.run beside such a star import, an argv that is not pytest (S9)",
         'from subprocess import run\nfrom helpers_x import *\ndef go():\n    return run(["-q"])\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a def beside such a star import", 'from helpers_x import *\ndef local():\n    pass\ndef go():\n    local()\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a module import beside such a star import", 'import os\nfrom helpers_x import *\nos.getcwd()\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a class body's call before its own binding, beside such a star import (K5)",
         'from helpers_x import *\nclass T:\n    out = main(["-q"])\n    main = None\n',
         "unparsed", "a name no scope here binds, in a module with a star import from helpers_x"),
        # the fail-closed design's second verify pass (2026-09-23) found two refusals no case held: a module binding made
        # by a method under a global declaration, the method called through a subscript at module level before the star
        # import (the lookup finds the module's binding only where homes_of moves it there), and a relative star import
        # from a module named like one the census reads, which is not that module and whose names the census does not
        # read (under each mutant the module stayed green and the case gave no row)
        ("a module binding made under a global declaration in a method, before such a star import (X-L11d)",
         'class K:\n    def arm(self):\n        global run\n        from subprocess import run\n[K][0]().arm()\n'
         'from helpers_x import *\ndef go():\n    return run(["-q"])\n',
         "unparsed", "a name the module binds, in a module with a star import from helpers_x"),
        ("a relative star import from a module named subprocess (X-L10a)",
         'from .subprocess import *\ndef go():\n    return run("python -m pytest -q", shell=True)\n',
         "unparsed", "a name no scope here binds, in a module with a star import from .subprocess"),
        # nor does a function's binding made from a name the star import may bring or rebind: `run = main` in a
        # function, main from the star import, gave no row where pytest.main ran (the fail-closed design's second verify
        # pass, 2026-09-23: LA1 to LA4 and LA17). A plain or annotated assignment from a name or an attribute is followed
        # along its chain to the module, and the call through it is refused
        ("a function's binding from a name such a star import brings (LA1)",
         'from helpers_x import *\ndef go():\n    run = main\n    return run(["-q"])\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("an attribute of a function's binding from such a name, called with a pytest string (LA2)",
         'from helpers_x import *\ndef go():\n    m = sp\n    return m.run("python -m pytest -q", shell=True)\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("such a binding called from a nested function (LA3)",
         'from helpers_x import *\ndef go():\n    run = main\n    def inner():\n        return run(["-q"])\n    return inner()\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("such a binding called under a nonlocal declaration (LA4)",
         'from helpers_x import *\ndef go():\n    m = main\n    def inner():\n        nonlocal m\n        return m(["-q"])\n'
         '    return inner()\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("a function's binding from an attribute of such a name (LA17)",
         'from helpers_x import *\ndef go():\n    run = main.__call__\n    return run(["-q"])\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("a chain of two such bindings, one annotated",
         'from helpers_x import *\ndef go():\n    a: object = main\n    b = a\n    return b(["-q"])\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        # an assignment under a nonlocal declaration binds in the enclosing function, so it is that function's binding
        # the call reads (found by a mutant of this pass's own fix: keyed on the assigning function, the case gave no row)
        ("such a binding made by a nested function under nonlocal, the outer function calling",
         'from helpers_x import *\ndef go():\n    m = print\n    def arm():\n        nonlocal m\n        m = main\n    arm()\n'
         '    return m(["-q"])\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        ("a function's binding from an attribute of a module import such a star import may rebind, the flag passed",
         'import pytest\nfrom helpers_x import *\ndef go():\n    run = pytest.main\n    return run(["-q", "-p", "no:anyio"])\n',
         "unparsed", "a name the function go binds from a name the star import from helpers_x may bring or rebind"),
        # a header expression (a decorator, a default, an annotation, a return annotation, a class's bases and keywords,
        # a type parameter) is looked up in the scope around its def, lambda or class, where Python evaluates it, not in
        # the def's own scope (the fail-closed design's third verify pass, 2026-09-24: LD1 to LD5 and LS5, each beside a
        # binding of the name in the def or class itself, gave no row where pytest.main ran; found closing that pass,
        # LD7, LD8, LD9, LD10 and LD13 were silent the same way, and LD11 had its row through a lookup that skipped the
        # class its default is evaluated in). An annotation deferred from 3.14 is read too: a row where it may never
        # run, the safe side
        ("a function default beside the function's own import of the name (LD1)",
         'from pytest import main\ndef test_a(rc=main(["-q"])):\n    from json import loads as main\n    return rc\n',
         False, "pytest.main (in process)"),
        ("a method default, evaluated in the class body that binds the name (LD2)",
         'import pytest\nclass TestT:\n    m = pytest.main\n    def test_x(self, rc=m(["-q"])):\n        return rc\n',
         False, "pytest.main (in process)"),
        ("a decorator's argument beside the decorated function's own import of the name (LD3)",
         'from pytest import main\ndef deco(_):\n    return lambda f: f\n@deco(main(["-q"]))\ndef test_a():\n'
         '    from json import loads as main\n    return main\n', False, "pytest.main (in process)"),
        ("a class base beside the class body's own import of the name (LD4)",
         'from pytest import main\nclass TestT(type(main(["-q"]))):\n    from json import loads as main\n',
         False, "pytest.main (in process)"),
        ("a parameter annotation beside the function's own import of the name (LD5)",
         'from pytest import main\ndef test_a(x: main(["-q"]) = 0):\n    from json import loads as main\n    return x\n',
         False, "pytest.main (in process)"),
        ("a return annotation beside the function's own import of the name (LD7)",
         'from pytest import main\ndef test_a() -> main(["-q"]):\n    from json import loads as main\n    return main\n',
         False, "pytest.main (in process)"),
        ("a keyword-only default beside the function's own import of the name (LD8)",
         'from pytest import main\ndef test_a(*, rc=main(["-q"])):\n    from json import loads as main\n    return rc\n',
         False, "pytest.main (in process)"),
        ("a class keyword beside the class body's own import of the name (LD10)",
         'from pytest import main\nclass TestT(object, flag=main(["-q"])):\n    from json import loads as main\n',
         False, "pytest.main (in process)"),
        ("a class decorator's argument beside the class body's own import of the name (LD13)",
         'from pytest import main\ndef deco(_):\n    return lambda c: c\n@deco(main(["-q"]))\nclass TestT:\n'
         '    from json import loads as main\n', False, "pytest.main (in process)"),
        # the header's scope decides the refusals too: a comprehension in a method default is a class body's
        # comprehension, and beside a star import from a module the census does not read, a default of a def or lambda
        # that binds the name is a lookup the star import can reach
        ("a comprehension in a method default, the class binding the name (LD11)",
         'from pytest import main as m\nclass TestT:\n    from json import loads as m\n'
         '    def test_x(self, rc=[m(["-q"]) for _ in (1,)]):\n        return rc\n',
         "unparsed", "inside a comprehension or generator expression in a class body that binds the name"),
        ("a nested function's default beside such a star import, the nested function binding the name (LS5)",
         'from helpers_x import *\ndef test_a():\n    def inner(rc=main(["-q"])):\n        from json import loads as main\n'
         '        return rc\n    return inner()\n',
         "unparsed", "a name no scope here binds, in a module with a star import from helpers_x"),
        ("a lambda's default beside such a star import, the lambda binding the name as a parameter (LD9)",
         'from helpers_x import *\nf = lambda main=0, rc=main(["-q"]): rc\n',
         "unparsed", "a name no scope here binds, in a module with a star import from helpers_x"),
    )
    # the argv each positional form reads, its elements joined by spaces (None for an expression): a spawn form's mode
    # and an e form's env are not argv elements. Strings, not lists: a list here would be an argv literal this census reads.
    POSITIONAL_ARGV = {"os.execle, its env last": "None python -m pytest",
                       "os.execlpe, its env last, the flag in one token": "python3 python3 -m pytest -pno:anyio",
                       "os.spawnl, its mode first": "None None -m pytest",
                       "os.spawnle, mode first and env last": "None python -m pytest",
                       "os.spawnlpe": "python3.12 python3.12 -m pytest"}
    CONTROLS = (      # correctness-3's refuter's four, each read before the ruling
        ("os.system", 'import os\nos.system("pytest -q")\n', "unparsed", "a pytest command in a shell string"),
        ("subprocess.run of a string", 'import subprocess\nsubprocess.run("python -m pytest -q", shell=True)\n', "unparsed", "a pytest command in a shell string"),
        ("an unflagged argv literal", 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pytest", "-q"])\n', False, "<interpreter> -m pytest"),
        ("create_subprocess_exec of a starred list literal", 'import asyncio, sys\nasyncio.create_subprocess_exec(*[sys.executable, "-m", "pytest"])\n',
         False, "<interpreter> -m pytest"),
    )

    def _assert_one_row(self, label, src, want, what):
        rows = _launchers_in(src, "test_synthetic_launcher.py")
        self.assertEqual(len(rows), 1, "%s: one row expected, read %r" % (label, [_describe_launcher(r) for r in rows]))
        r = rows[0]
        if want == "unparsed":
            self.assertIn(what, r["unparsed"] or "", _describe_launcher(r))
            self.assertIn("not read as", _describe_launcher(r))
        else:
            self.assertIsNone(r["unparsed"], _describe_launcher(r))
            self.assertIn(what, r["kind"], _describe_launcher(r))
            self.assertEqual(r["flag"], want, _describe_launcher(r))
            if label in self.POSITIONAL_ARGV:
                self.assertEqual(" ".join(str(a) for a in r["argv"]), self.POSITIONAL_ARGV[label], _describe_launcher(r))

    def test_every_call_that_starts_or_runs_pytest_is_read_in_each_form(self):
        for label, src, want, what in self.STARTING_FORMS + self.CONTROLS:
            with self.subTest(form=label):
                self._assert_one_row(label, src, want, what)
        self.assertEqual(set(self.POSITIONAL_ARGV) - {t[0] for t in self.STARTING_FORMS}, set(), "an argv expectation names no form")
        # the star refusals ask for imports by name from the modules that define the calls the census reads, and say that an
        # import by name from any other module gives no row (the fail-closed design's third verify pass, 2026-09-24: the
        # message asked for the name imported by name, which from another module the census reads as no launcher; LS1 to
        # LS3 in OUTSIDE_THE_READ)
        remedy = ("not read as a launcher until the star import is replaced by imports by name from the modules that define "
                  "the calls the census reads (_pytest.config, asyncio, asyncio.subprocess, os, pytest, shlex, subprocess); a "
                  "name imported by name from any other module, a relative one included, is read as no launcher and gives no row")
        for label, src in (("a name no scope binds", 'from helpers_x import *\ndef go():\n    return main(["-q"])\n'),
                           ("a name the module binds", 'main = None\nfrom helpers_x import *\ndef go():\n    return main(["-q"])\n'),
                           ("a function's binding from such a name", 'from helpers_x import *\ndef go():\n    run = main\n    return run(["-q"])\n')):
            with self.subTest(refusal=label):
                rows = _launchers_in(src, "t.py")
                self.assertEqual([r["kind"] for r in rows], ["a call the census cannot resolve"], [_describe_launcher(r) for r in rows])
                self.assertTrue(rows[0]["unparsed"].endswith(": " + remedy), _describe_launcher(rows[0]))
        # a type parameter is 3.12 syntax: its bound is read in the scope around the def there (LD14; evaluated lazily, so
        # a row where it may never run, the safe side), and before 3.12 the module is one unparsed row
        rows = _launchers_in('from pytest import main\ndef test_a[T: main(["-q"])]():\n    from json import loads as main\n'
                             '    return main\n', "t.py")
        self.assertEqual([(r["kind"], r["flag"], r["unparsed"] is None or "does not parse under this interpreter" in r["unparsed"])
                          for r in rows], [("pytest.main (in process)" if sys.version_info >= (3, 12) else "module", False, True)],
                         [_describe_launcher(r) for r in rows])
        self.assertEqual(rows[0]["unparsed"] is None, sys.version_info >= (3, 12), _describe_launcher(rows[0]))
        # the name resolution runs one pass per assignment at most: a name assigned from itself terminates, with no row
        self.assertEqual(_launchers_in('import os\np = os.path\np = p.parent\np = p.parent\n', "t.py"), [])
        # the census against what it refuses, through the walk: an unflagged in-process pytest.main in a test module is
        # named at its line as lacking the flag, and so would red test_every_launcher_passes_the_flag_or_is_listed...
        d = tempfile.mkdtemp(prefix="census-walk-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "test_in_process.py"), "w") as f:
            f.write('import pytest\n\ndef test_nested():\n    assert pytest.main(["-q", "sub"]) == 0\n')
        rows = child_pytest_launchers(d)
        self.assertEqual([_describe_launcher(r) for r in rows],
                         ["tests/test_in_process.py:4 (test_nested): pytest.main (in process) ['-q', 'sub']  lacks -p no:anyio (keyed on the "
                          "argv's constant elements: `-p` then `no:anyio`, or `-pno:anyio`)"])

    # the residual, pinned by execution: each form outside the read gives no row (at the ruling's head and after it)
    OUTSIDE_THE_READ = (
        ("a command string held in a variable", 'import subprocess\ncmd = "python -m pytest -q"\nsubprocess.run(cmd, shell=True)\n'),
        ("an f-string held in a variable", 'import subprocess, sys\ncmd = f"{sys.executable} -m pytest -q"\nsubprocess.run(cmd, shell=True)\n'),
        ("a command built with %", 'import subprocess, sys\nsubprocess.run("%s -m pytest -q" % sys.executable, shell=True)\n'),
        ("a command built with +", 'import os, sys\nos.system(sys.executable + " -m pytest -q")\n'),
        ("a command built with .format", 'import subprocess, sys\nsubprocess.getoutput("{} -m pytest -q".format(sys.executable))\n'),
        ("a shlex.split string held in a variable", 'import shlex, subprocess\ncmd = "pytest -q"\nsubprocess.run(shlex.split(cmd))\n'),
        ("a shell's -c string held in a variable", 'import subprocess\nsubprocess.run(["bash", "-c", script])\n'),
        ("a python -c string held in a variable", 'import subprocess, sys\ncode = "import pytest; pytest.main([])"\nsubprocess.run([sys.executable, "-c", code])\n'),
        ("a string anywhere else: a script written to a file and run", 'import subprocess\nopen("run.sh", "w").write("pytest -q\\n")\nsubprocess.run(["bash", "run.sh"])\n'),
        ("a string anywhere else: exec", 'exec("import pytest; pytest.main([])")\n'),
        ("an argv assembled one element at a time", 'import subprocess, sys\nargv = [sys.executable]\nargv.append("-m")\nargv.append("pytest")\nsubprocess.run(argv)\n'),
        ("pytest.main reached through getattr", 'import pytest\ngetattr(pytest, "main")(["-q"])\n'),
        ("pytest.main reached through importlib", 'import importlib\nimportlib.import_module("pytest").main(["-q"])\n'),
        ("pytest run in process by runpy", 'import runpy\nrunpy.run_module("pytest", run_name="__main__")\n'),
        ("pytest.main bound to a parameter default", 'import pytest\ndef nested(run=pytest.main):\n    return run(["-q"])\n'),
        # a call, string or in process, reached through a name the census does not resolve (review round 4's verify,
        # prose-records, 2026-09-23): the census resolves a name bound by an import or by a plain or annotated assignment
        ("a string call through a tuple-unpacked name", 'import subprocess\nrun, _ = subprocess.run, None\nrun("python -m pytest -q", shell=True)\n'),
        ("a string call through a conditional alias", 'import os\nsh = os.system if os.name else os.popen\nsh("pytest -q")\n'),
        ("a string call through a parameter default", 'import os\ndef go(sh=os.system):\n    sh("pytest -q")\n'),
        ("pytest.main through tuple unpacking", 'import pytest\nm, _ = pytest.main, None\nm(["-q"])\n'),
        ("pytest.main through a walrus", 'import pytest\nif (m := pytest.main):\n    m(["-q"])\n'),
        # an attribute of a class or an instance (the pre-push lenses' L05 and L06)
        ("pytest.main as a class attribute reached through the class", 'import pytest\nclass T:\n    m = pytest.main\n'
         '    def go(self):\n        return T.m(["-q"])\n'),
        ("pytest.main as a class attribute reached through self", 'import pytest\nclass T:\n    m = staticmethod(pytest.main)\n'
         '    def go(self):\n        return self.m(["-q"])\n'),
        # beside a star import from a module the census does not read, a builtin name is read as the builtin and a
        # module name no scope binds as that module, and the star import may rebind either (found closing the first
        # verify pass)
        ("a builtin name a star import from an unread module may rebind", 'from helpers_x import *\ndef go():\n    return print(["-q"])\n'),
        ("a module name a star import from an unread module may rebind", 'from helpers_x import *\nsubprocess.run(["-q"])\n'),
        # beside such a star import, a function's binding from one of its names other than by a plain or annotated
        # assignment from a name or an attribute is read as the function's own (the second verify pass's fix follows
        # those assignments alone)
        ("a function's binding from a subscript of such a star import's name", 'from helpers_x import *\ndef go():\n'
         '    run = [main][0]\n    return run(["-q"])\n'),
        # a class body reads a name past the class until the class binds it, and the census reads the class's binding
        # (K1, found closing the first verify pass; reading both, or refusing the call, reds the first-iterable case
        # in test_a_name_the_resolution_reads_is_not_refused)
        ("a class body's call before the class binds the name", 'from pytest import main\nclass T:\n    out = main(["-q"])\n'
         '    from json import loads as main\n'),
        # an import by name from a module that does not define the call, which may re-export pytest.main, binds a name the
        # census reads as no launcher, and a relative one binds none it reads (the fail-closed design's third verify pass,
        # 2026-09-24: LS1 to LS3, each running pytest.main unflagged when the module re-exports it)
        ("an import by name from a module the census does not read (LS1)", 'from helpers_x import main\ndef test_a():\n    main(["-q"])\n'),
        ("a launcher's name imported again by name from a module the census does not read (LS2)",
         'from subprocess import run\nfrom helpers_x import run\ndef test_a():\n    run(["-q"])\n'),
        ("a relative import by name (LS3)", 'import pytest\nfrom .helpers_x import main\ndef test_a():\n    main(["-q"])\n'),
    )

    def test_each_form_outside_the_read_gives_no_row(self):
        for label, src in self.OUTSIDE_THE_READ:
            with self.subTest(form=label):
                self.assertEqual(_launchers_in(src, "test_synthetic_launcher.py"), [], label)

    def test_a_name_the_resolution_reads_is_not_refused(self):
        # the refusals' edges (the owner's fail-closed design, 2026-09-23): a comprehension in a class body is refused
        # only where the class binds the callee's name, so the lookup past the class could differ, and outside its first
        # iterable, which Python evaluates in the class body; a star import from an unread module refuses every name the
        # lookup takes to the module (bound there, or bound nowhere and no builtin: the first verify pass, 2026-09-23,
        # found the module's own bindings passed), and not a name a function scope on the lookup binds, which the star
        # import cannot reach. Each of these is read as Python reads it
        for label, src, rows in (
                ("a class-body comprehension whose class does not bind the name reads the module's",
                 'from pytest import main as m\nclass T:\n    out = [m(["-q"]) for _ in (1,)]\n', ["pytest.main (in process)"]),
                ("the first iterable is the class body's own",
                 'from pytest import main as m\nclass T:\n    from json import loads as m\n    out = [x for x in m("[1]")]\n', []),
                ("a lambda in a class body skips the class, and is read",
                 'from pytest import main as m\nclass T:\n    from json import loads as m\n    f = lambda self: m(["-q"])\n', ["pytest.main (in process)"]),
                ("a star import from an unread module beside builtins, a parameter and names the calling function binds",
                 'from helpers_x import *\ndef go(cb):\n    import os\n    def local(): pass\n    local()\n    print(len([]))\n    cb()\n'
                 '    os.getcwd()\n', []),
                ("a name the enclosing function binds, beside such a star import",
                 'from helpers_x import *\ndef outer():\n    from json import loads as main\n    def go():\n        return main("[1]")\n', []),
                ("a function's binding from a name the function imports by name, beside such a star import",
                 'from helpers_x import *\ndef go():\n    from pytest import main\n    run = main\n    return run(["-q", "-p", "no:anyio"])\n',
                 ["pytest.main (in process)"]),
                ("a function's bindings from each other alone, beside such a star import",
                 'from helpers_x import *\ndef go():\n    a = b\n    b = a\n    return a()\n', []),
                ("a star import from a module the census reads refuses nothing",
                 'from subprocess import *\ndef go():\n    return helper()\n', []),
                ("a name declared global and bound nowhere else is unbound, with no star import to refuse it",
                 'def go():\n    global main\n    return main(["-q"])\n', []),
                ("a class body's own call under its global declaration reads the module's json.loads, past the function's "
                 "pytest.main (LG2)",
                 'import pytest\nfrom json import loads as m\ndef outer():\n    m = pytest.main\n    class C:\n        global m\n'
                 '        r = m("[1]")\n    return C.r\n', [])):
            with self.subTest(form=label):
                got = _launchers_in(src, "test_synthetic_launcher.py")
                self.assertEqual([r["kind"] for r in got], rows, [_describe_launcher(r) for r in got])
                self.assertTrue(all(r["unparsed"] is None for r in got), [_describe_launcher(r) for r in got])

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

    def test_the_walk_parses_a_module_holding_a_star_import_and_what_it_skips_gives_no_row(self):
        # the fail-closed design's second verify pass (2026-09-23): the prefilter skipped a module that star-imported a
        # helper re-exporting pytest.main and never spelled pytest, so the refusal beside such a star import never ran
        # there, and executed the module ran pytest.main(["-q"]). A star import now lets a module through, by its text,
        # the star after a backslash continuation included. What the prefilter still skips is the residual, pinned here:
        # a module that spells no pytest and holds no star import gives no row through the walk, though _launchers_in
        # reads or refuses each of these, and each runs pytest without the flag
        d = tempfile.mkdtemp(prefix="census-walk-")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        refused = "a name no scope here binds, in a module with a star import from helpers_zz"
        skipped = {"test_concat.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "py" "test", "-q"])\n',
                   "test_escape.py": 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "py\\x74est", "-q"])\n',
                   "test_modvar.py": 'import subprocess, sys\nfrom helpers_zz import MOD\nsubprocess.run([sys.executable, "-m", MOD, "-q"])\n'}
        files = dict(skipped, **{"helpers_zz.py": 'from pytest import main\n__all__ = ["main"]\n',
                                 "test_star_silent.py": 'from helpers_zz import *\n\n\ndef test_child():\n    return main(["-q"])\n',
                                 "test_star_continued.py": 'from helpers_zz import \\\n    *\n\ndef test_child():\n    return main(["-q"])\n'})
        for name, text in files.items():
            with open(os.path.join(d, name), "w") as f:
                f.write(text)
        rows = child_pytest_launchers(d)
        self.assertEqual([(r["file"], r["line"], r["kind"]) for r in rows],
                         [("test_star_continued.py", 5, "a call the census cannot resolve"),
                          ("test_star_silent.py", 5, "a call the census cannot resolve")], [_describe_launcher(r) for r in rows])
        self.assertTrue(all(refused in r["unparsed"] for r in rows), [_describe_launcher(r) for r in rows])
        for name, text in skipped.items():
            with self.subTest(skipped=name):
                self.assertFalse(PYTEST_TEXT_RE.search(text) or STAR_IMPORT_TEXT_RE.search(text), name)
                self.assertEqual(len(_launchers_in(text, name)), 1, "%s: _launchers_in reads it, so its missing row is the "
                                 "prefilter's residual" % name)

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
