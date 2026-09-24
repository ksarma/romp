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
   `pytest` or `py.test` at command position, in a named or unnamed step in the file's own layout, in a one-line plain
   or quoted scalar or a `run: |` literal block, backslash continuations joined as the shell joins them, comment lines
   and pip installs excluded), and the two invocations the file is known to
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
   The check reads ci.yml's text, and that is its residual. The YAML it reads is held to an allowlist (the owner's
   allowlist design, 2026-09-24): every line of ci.yml is in a form the real file uses, or the scan (yaml_line_forms,
   run in PytestPopulation) refuses it by name at its line. The accepted forms, YAML_FORMS_ACCEPTED, are derived from
   the file by the scan itself (CI's shape installs no YAML library), and PytestPopulation asserts that the file uses
   every one and that each of its lines is in one: blank and comment lines; block mappings and block sequences, each
   nested block two columns past its parent key, a sequence's entries opening with a key, the keys spelled as ci.yml
   spells them and none twice in one mapping; on a key's line, a plain scalar that opens with no YAML indicator and
   holds no `: `, a single-quoted scalar without `''`, a double-quoted scalar without a backslash, or a flow sequence of
   such scalars, each closed on that line and followed by nothing but a trailing comment (on a name: or a
   working-directory: key, whose values the parser reads as the text after the key, the plain scalar alone, with no
   comment); and a `|` literal block as a step's run. Every other line is refused by name, valid YAML included: among
   them a quoted value or a trailing comment on a name: or working-directory: key, an anchor, an alias, a tag, a merge
   key, an explicit key, a flow mapping, a flow collection nested or continued past its line, a quoted scalar continued
   past its line, an escape in a quoted scalar, a folded block, a chomping or indentation indicator, a literal block
   anywhere but a step's run, a header or a value on the line after its key, a plain scalar continued past its line, a
   directive, a document marker, a quoted, spaced or otherwise spelled key, a key twice in one mapping, a list at its
   key's indent, another indentation, a tab or other control character, a character outside ASCII outside a comment
   line, and a last line with no newline after it. A form the scan does not accept is refused by name; reword the step
   in an accepted form. Until the
   allowlist the scan refused named forms one at a time, and each of three verify passes found forms the line reading
   half-modelled; the parser and the censuses read the accepted forms and nothing else. Every line of ci.yml that
   spells pytest (the word in any case ending at a word boundary, py.test, or a `$PYTEST` expansion), outside a comment
   or a name: key's own line and other than a pip install, is read as an invocation or is red (round 4's ruling,
   2026-09-23): the line census in PytestPopulation holds each such line to the span of lines the parser read for a
   row, so a pytest line outside every run (an action's input) or in a layout the parser does not read is red at its
   line (a line joined to the next by a backslash counts when the joined text spells pytest, joined as the shell joins
   it); a mention the parser reads but not as a command (a wrapper such as `uvx pytest`, a `$PYTEST` variable, an
   option cluster such as `python -Impytest`) is red as `unparsed` until the parser reads it; and a line where a job
   key goes that the parser does not read as one (a key carrying its value) is red, so no step is read under the job
   above it. Outside the check: a run line that never spells pytest (a `$RUNNER` set elsewhere, `make test`), a pytest
   run by a script or action a step calls, and every other workflow file under .github/workflows/. The flag half keys
   on the words `-p` and `no:anyio`, consecutive in the command's arguments as the shell splits them (so the spelling
   inside a quoted argument is not the flag), the switch half on the merged value reading exactly 1 (a quoted value
   read verbatim, so `"1 "` is not 1, and a plain value to YAML's comment, so `1#x` is not 1), and their messages say
   so. Both read the run text as written, and GitHub substitutes a `${{ }}` expression into that text before the
   shell reads it (`${{ '#' }}` before the flag, or a matrix value '#' there, cuts the flag off as a comment), so a
   step whose run text holds `${{` and spells pytest anywhere in it, in a comment line or a trailing comment too, is
   `unparsed`, red until the value moves to an env: key and the run text reads it as a shell variable (the
   allowlist's second verify pass, 2026-09-24: such a step read ok, or listed, while pytest ran without the flag; round
   5's ruling A, 2026-09-24: a step whose only pytest spelling sat in a comment gave no row, and the substituted text
   can end the comment with a newline and run pytest, so such a step now gives an unparsed row at its first line that
   spells pytest). Outside the flag half's read: anything that rewrites a pytest command's arguments after the run
   text is read, among them a shell function or alias the run text defines, a python earlier on PATH, and a step's
   shell: or a job's defaults; on the Run pytest step the check below refuses those it can see (a function or alias is
   a second command there, and its shell:, its job's defaults: and a $GITHUB_PATH write spelled in a run text of its
   job are refused), and a write to $GITHUB_PATH that does not spell the name stays outside. Nothing here held that
   pytest's failure reaches the cell until round 5's ruling C (2026-09-24; with an if:, a continue-on-error, `|| true`
   or --collect-only on the Run pytest step the module read green): run_pytest_status, whose docstring is the rule,
   holds the Run pytest step's exit status to pytest's and the cell's to the step's, and refuses at its line, among
   others, an if: or a continue-on-error on the step or its job, the command followed by `||`, a pipe or a trailing
   `&`, a second command or command line (an earlier `trap 'exit 0' EXIT` among them), an argument word outside
   RUN_PYTEST_OPTIONS (--collect-only, --co and --setup-plan among the refused), a step's shell: or a job's or the
   workflow's defaults:, a key of the step's merged env outside RUN_PYTEST_ENV (PYTEST_ADDOPTS and BASH_ENV among
   them), and a run text of the job that spells GITHUB_ENV, GITHUB_PATH or BASH_ENV; its residual is a write that does
   not spell those names, such as one by a script or action a step calls. The switch half
   reads what the run text does to the variable only by its spelling (round 4's ruling, 2026-09-23): a step whose run text spells ROMP_SDK_REQUIRE anywhere other than as a VAR=value prefix on
   its pytest command (an unset, export, declare, env -u or assignment, on an earlier line or before the command on
   its own line; a comment too), or whose job's other run texts spell it (a write to $GITHUB_ENV sets it for the steps
   after), is `unparsed`, red until read, since the parser does not run the shell. And every line of ci.yml that spells
   the switch, outside a comment, is an env: key line the merge read (a bare key at its block's first key indent, its
   value on that line) or lies in a run text the parser read, or the switch census in PytestPopulation names it
   (review round 4's verify, 2026-09-23): an env: written as an alias or a flow mapping, a quoted or spaced key, a
   key-shaped line deeper than its block's keys (inside another key's block scalar, that key's text to YAML), and a
   step's shell: or a job's defaults that spells the switch are each red at their line, and the forms among them the
   scan does not accept are refused as well; the switch's value continued past its line or written as a block scalar,
   and a key-shaped line inside another key's quoted scalar over several lines, are refused by the scan. Outside
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
   tests/test_served_tests_require.py). As read on 2026-09-24: none of these is on ci.yml's Run pytest line (no path,
   no -k, no --ignore) or in its env (no PYTEST_ADDOPTS), and those two are held since round 5's ruling C:
   run_pytest_status (item 1) refuses a word on that line outside RUN_PYTEST_OPTIONS and a key of its merged env
   outside RUN_PYTEST_ENV; no conftest in the tree sets collect_ignore or collect_ignore_glob or defines a collection
   hook (tests/conftest.py, the only one, implements two reporting hooks, pytest_make_collect_report and
   pytest_collectreport, which drop nothing); and the repo has no pytest.ini, .pytest.ini, pytest.toml, .pytest.toml,
   pyproject.toml, setup.cfg or tox.ini. Nothing pins the rest of that read, the conftest and the ini files. The belt's
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
   that passes it on, in a variable extended later), whose command is pytest, among them `-m pytest`, or `-mpytest` as
   one token, after an interpreter head through interpreter options the census takes apart one at a time, the head an
   expression or a python-named constant wherever it sits, so `python -B -m pytest`, the repo's own recipe, and `uv
   run python -m pytest` read; `-m pytest` as the first two elements; and pytest or py.test by name or path as argv[0]
   (_argv_command's docstring states the rule in full). The
   positional arguments of asyncio.create_subprocess_exec and of the os.exec and os.spawn l forms (execl, execle,
   execlp, execlpe, spawnl, spawnle, spawnlp, spawnlpe; a spawn form's mode and an e form's env set aside), read as
   that argv. And a call of pytest.main or pytest.console_main, or of _pytest.config's main or console_main, by a name
   the census resolves for it (an import from the module that defines the call, an alias, a star import from such a
   module, a name assigned from one; looked up by scope, as Python looks it up: the call's own scope (for a call in a
   decorator, a default, an annotation, a return annotation or a type parameter of a def or lambda, or in a class's
   decorators, bases or keywords, the scope around that def or class, where Python evaluates it; an annotation deferred
   from 3.14 and a type parameter's lazy bound are read too, a row where they may never run), the functions around it
   with class bodies skipped, their global declarations with them, the module; a binding under a global declaration
   counted at the module and one under a nonlocal declaration in the enclosing function that binds the name): a pytest
   session in the calling process, where plugin autoload runs again whatever flag the outer run was given, so its argv,
   the first positional argument or args=, carries the flag itself. The flag check keys on the argv's constant elements
   (`-p` then `no:anyio`, or `-pno:anyio`), so a flag carried by a variable reads as absent, the safe side, and the
   message says so. The modules known to spawn pytest are asserted present, so an empty read is red, and there is no
   count to keep; the derivation case prints the listing (python -m pytest tests/test_ci_sdk_pin.py -q -p
   no:cacheprovider -p no:anyio
   -k ChildPytestLaunchers -rP). What the census leaves unread is its residual. A pytest command in a constant string
   or f-string written at the call and handed to subprocess (run, Popen, call, check_call, check_output, getoutput,
   getstatusoutput), os.system or os.popen, asyncio.create_subprocess_shell, shlex.split or a shell's -c (a
   `pytest.main(` call included) is `unparsed` and red until it is spelled as an argv, as is an argv that may run
   pytest and the census cannot tell, among them, after an interpreter head, a `-m` whose module name is not a
   constant, an element that is not a constant right before `pytest`, a `-m` of a module in the pytest package such as
   pytest.__main__, and an option element the census does not take apart (a cluster such as `-Bm` or `-Impytest`, a
   long option, a letter it does not know) before an element that spells pytest (round 5's ruling B, 2026-09-24;
   _argv_command's docstring states the rule, its over-read included), and, in an argv written at a call the census
   reads whose command it does not read, a constant element named pytest or py.test after argv[0] (a wrapper's, as in
   `env pytest`, or a pip line's); an in-process call whose argv is not a literal (a name, or no argument, which reads
   sys.argv); and a module that does not parse under the running interpreter. Unparsed the same
   way (the owner's fail-closed design, 2026-09-23), a call whose callee's name the resolution cannot resolve: one
   inside a comprehension or generator expression in a class body that binds the name or declares it global (Python
   looks it up past the class there, a scope the census does not model); and, in a module with a star import from a
   module whose calls the census does not read, one through a name the lookup takes to the module, since the census
   takes only a function scope that binds the name as proof that the star import cannot reach it: a name the module
   binds (the star import may rebind it, and the census follows no order; the first verify pass, 2026-09-23, found such
   a binding read as the module's
   own and passed) or a name no scope binds and no builtin names (the name may come from it); and one through a name a
   function binds by a plain or annotated assignment from a name or an attribute whose root name is one of those,
   followed along a chain of such assignments (the second verify pass, 2026-09-23, found `run = main` in a function,
   main from the star import, read as the function's own and passed). A string anywhere else, or one held in a
   variable or built with %, + or .format, is outside the read, as is an argv assembled one element at a time (append
   calls), an option element the census does not take apart that no element spelling pytest follows (`-BW error -m
   <name>`), a wrapper-headed argv built away from the call that runs it, and any call, string or in process, reached
   through a name the census does not resolve (a name bound other
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
# The YAML the parser and the censuses read is held to an allowlist (yaml_line_forms, the owner's allowlist design,
# 2026-09-24): every line of ci.yml is in a form the real file uses, or it is refused by name at its line, valid YAML
# included (a form the scan does not accept is refused by name; reword the step in an accepted form). The readers below
# read the accepted forms and nothing else.
# ---------------------------------------------------------------------------------------------------------------------
TOP_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):", re.M)                # a column-0 key of the workflow's mapping
JOB_RE = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]*(?:#.*)?\n", re.M)           # a job: a bare key at indent 2 under jobs:
STEP_START_RE = re.compile(r"^      - ", re.M)                                # a step: a list item at indent 6
STEP_KEY_PAD = "        "                                                     # step keys sit at indent 8 once `- ` is spaced
STEPS_END_RE = re.compile(r"^ {0,4}[^ \n#]", re.M)                           # a line past the steps: indented 4 or less, not blank or a comment
RUN_RE = re.compile(r"^        run:(.*)$", re.M)
BLOCK_INDICATOR_RE = re.compile(r"^[ \t]*\|[ \t]*(#.*)?$")      # a literal block header, the one block form yaml_line_forms accepts
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
# a line whose key is `name` (`name:` or `- name:`, the value after a space or nothing): the census's first exclusion. A
# line that merely contains "name:" (a flow mapping `- {name: ..., run: ...}`) is not one. The name key is the line's
# only key in every form the scan accepts (yaml_line_forms: a plain value holds no `: `, a quoted one is followed by
# nothing but a comment); a flow mapping over several lines whose name line carries a run, excused here, is refused by
# the scan at its opening line (until the allowlist, 2026-09-24, _name_key_alone read the rest of such a line for a key)
NAME_KEY_RE = re.compile(r"^[ \t]*(?:-[ \t]+)?name:(?:[ \t]|$)")


# the census's split of a line the parser did not read, for the pip exclusion: at every operator character whatever the
# quoting, so the commands of a YAML-quoted scalar are judged one by one (a split finer than the shell's never hides a
# mention: it can only stand a piece of a pip command alone)
CENSUS_SPLIT_RE = re.compile(r"&&|\|\||[;|&()]")
# what a raw YAML line opens with before its value, stripped from each piece of that split before the pip test: the
# indentation, a list dash, one plain key and its colon, and an opening quote (a flow mapping's brace and a quoted key,
# stripped until the allowlist, 2026-09-24, are forms the scan refuses, and a line holding one is no longer excused)
YAML_KEY_PREFIX_RE = re.compile(r"""^[ \t]*(?:-[ \t]+)?(?:[A-Za-z0-9_-]+[ \t]*:[ \t]+)?["']?""")
INLINE_ENV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(\S*)")
SWITCH = "ROMP_SDK_REQUIRE"
FLAG_SPELLING = "-p no:anyio"


def passes_flag(args):
    """True when a pytest command's arguments, split into words as the shell splits them (shlex, POSIX rules: quotes
    and backslashes read), hold `-p` then `no:anyio` as two consecutive words, the flag's spelling (FLAG_SPELLING). A
    spelling inside a quoted argument (`-k 'x -p no:anyio y'`) is that argument's text, not the flag: until the
    allowlist build (2026-09-24; the pre-push closer's C01) a regex read the spelling anywhere in the text after a
    space, and pytest ran without the flag while the step read ok. `-pno:anyio`, one word, is the same flag to pytest
    and not this spelling, the safe side; arguments the split refuses (a quote left open) read as not passing it."""
    try:
        words = shlex.split(args, posix=True)
    except ValueError:
        return False
    return any(words[i] == "-p" and words[i + 1] == "no:anyio" for i in range(len(words) - 1))

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
    """The `env:` mapping whose `env:` line sits at `env_indent` spaces: {name: value}, read in the forms the scan
    accepts (yaml_line_forms): a key at the block's first key indent, its value on the key's line. A quoted value is
    kept verbatim inside its quotes, whitespace included, as YAML keeps it (`"1 "` reads as `1 `, which is not 1; both
    runtime readers of the switch compare with == "1"; review round 4, 2026-09-23: the strip reached inside quotes, and
    `"1 "` read as the switch on), and one followed by anything but a spaced comment is kept whole, quotes and all,
    which is never `1`. A plain value runs to YAML's comment, a `#` after a space or a tab, and is stripped, so `1#x`
    reads `1#x`, not 1 (until the allowlist, 2026-09-24, the value stopped at any `#`, and `1#x` read as the switch on
    while YAML holds the string `1#x`). A value that is a `${{ }}` expression is kept as its text, which is never `1`:
    the safe side. Comment and blank lines are skipped, and so is every line deeper than the key indent: the accepted
    forms have none (a value continued past its line, a block scalar and a key-shaped line inside one are refused by the
    scan), and a mapping nested under a key is that key's value, not keys of this block. `keys_out`, when a list is
    given, receives (offset of the key's line in `text`, name) for every key line read (the switch census,
    switch_line_census, counts those lines as read). Not read: an `env:` line that carries anything after the colon but
    a comment (an alias, an anchor, a flow mapping: forms the scan refuses), a line at the key indent this regex does
    not read as a key (a quoted or spaced key, refused by the scan; a hyphenated name, which is not the switch), and a
    key on a last line with no newline after it, which the pattern needs (refused by the scan)."""
    pad = " " * env_indent
    # the block's lines: those indented past `env:`, blank lines, and comment lines at any indent, which YAML skips
    # wherever they sit (until the allowlist build, 2026-09-24, a comment line indented no further than `env:` ended the
    # block here, and the keys after it went unread: a spurious red, found by mutating the real file)
    m = re.search(r"^%senv:[ \t]*(?:#.*)?\n((?:%s .*\n|[ \t]*\n|[ \t]*#.*\n)+)" % (pad, pad), text, re.M)
    out = {}
    keys = [] if keys_out is None else keys_out
    if m:
        pos, key_indent = m.start(1), None
        for line in m.group(1).splitlines(keepends=True):
            off, pos = pos, pos + len(line)
            body = line.rstrip("\n")
            if not body.strip() or body.lstrip().startswith("#"):
                continue
            indent = len(body) - len(body.lstrip(" "))
            if key_indent is None:
                key_indent = indent
            km = re.match(r"([A-Za-z_][A-Za-z0-9_]*):(?=[ \t]|$)", body[indent:])
            if indent != key_indent or not km:
                continue
            v = body[indent + km.end():].strip(" \t")
            close = v.find(v[:1], 1) if v[:1] in ("'", '"') else -1
            if close > 0 and re.match(r"(?:[ \t]+#.*)?$", v[close + 1:]):
                value = v[1:close]
            elif v[:1] in ("'", '"'):
                value = v
            else:
                value = re.split(r"[ \t]#", " " + v, maxsplit=1)[0].strip()
            out[km.group(1)] = value
            keys.append((off, km.group(1)))
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


def _step_run(stext):
    """The step's `run:` scalar as shell lines [(offset in stext, text, offset of its last line)], read in the forms the
    scan accepts (yaml_line_forms): a plain or quoted scalar on the key's line, one line (a quoted one read inside its
    quotes; a plain one cut at YAML's comment, a `#` after a space, as YAML cuts it, inside shell quotes too: until the
    allowlist build, 2026-09-24, the cut was left to _shell_commands, which keeps a quoted `#`, so `-k "a #b" -p
    no:anyio` read the flag that YAML's value `... -k "a` never passes), and a `run: |` literal block, each of its lines
    one shell line with the block's indentation, the first text line's, removed. Every other form is refused by the scan
    at its line and not read here: until the allowlist (2026-09-24) this split read a tag through, reported an anchor or
    an indentation indicator as unparsed, folded a `>` block and a plain scalar continued on later lines, and read a
    chomping indicator, and each of those forms is refused now. No `run:`: None."""
    m = RUN_RE.search(stext)
    if not m:
        return None
    rest = m.group(1)
    if BLOCK_INDICATOR_RE.match(rest):
        after_off, raw, pos = m.end() + 1, [], 0
        for line in stext[after_off:].splitlines(keepends=True):
            if line.strip() == "" or line.startswith(STEP_KEY_PAD + " "):
                raw.append((after_off + pos, line))
                pos += len(line)
            else:
                break
        while raw and raw[-1][1].strip() == "":
            raw.pop()
        content = [(o, l) for o, l in raw if l.strip() != ""]
        if not content:
            return []
        indent = len(content[0][1]) - len(content[0][1].lstrip(" "))
        return [(o, l[indent:].rstrip("\n"), o) for o, l in raw]
    first = rest.strip()
    off = m.start(1) + len(rest) - len(rest.lstrip())
    close = first.find(first[0], 1) if first[:1] in ("'", '"') else -1
    if close > 0:
        first = first[1:close]
    else:
        first = re.split(r"[ \t]#", " " + first, maxsplit=1)[0].strip()
    return [(off, first, off)] if first else []


EXPRESSION_UNPARSED = ("the step's run text holds a ${{ }} expression, which GitHub substitutes before the shell reads the "
                       "text, so the text read here is not the text the shell runs: move the value to an env: key and read it "
                       "in the run text as a shell variable")
EXPRESSION_NO_ROW = (" (the step gave no pytest command the parser reads: its pytest spelling sits where the parser reads no "
                     "command, a shell comment among them, and the substituted text can end a comment with a newline and make "
                     "what follows a command)")


def workflow_steps(src):
    """The jobs of a workflow's text and their steps, split the way pytest_invocations reads them: [{job, text, base,
    steps}], text the job's text after its key line and base its offset in the file; each step {index, text, base, name}.
    A step's text runs from its dash to the next step's dash or to the end of the steps sequence, the first line after
    its dash, other than a blank or comment line, indented 4 or less (STEPS_END_RE), with the `- ` of the list item
    spaced out (STEP_KEY_PAD, the same length, so offsets hold) so every step key sits at indent 8; base is the dash's
    offset in the file, name the step's `name:`, else UNNAMED. The population check and the Run pytest step's check
    (run_pytest_status) share this split."""
    sections = _top_sections(src)
    assert "jobs" in sections, "ci.yml has no jobs: mapping at column 0: re-anchor this parser"
    jobs_at, body = sections["jobs"][0]
    jobs = list(JOB_RE.finditer(body))
    out = []
    for i, jm in enumerate(jobs):
        jend = jobs[i + 1].start() if i + 1 < len(jobs) else len(body)
        jtext = body[jm.end():jend]
        jbase = jobs_at + jm.end()
        starts = list(STEP_START_RE.finditer(jtext))
        steps = []
        for k, sm in enumerate(starts):
            send = starts[k + 1].start() if k + 1 < len(starts) else len(jtext)
            # the step ends at the end of the steps sequence too: the first line after its dash, other than a blank or
            # comment line, indented 4 or less, the job's next key. Until the allowlist's first verify pass
            # (2026-09-24) the last step ran to the end of the job, and a job key after the steps nested at indent 8
            # (services.<id>.env, strategy.matrix.name) was read as the step's own env or name: a service's env set the
            # switch for the parser, and pytest ran without it
            em = STEPS_END_RE.search(jtext, sm.end(), send)
            send = em.start() if em else send
            # the `- ` of the list item spaced out, so every step key, the first included, sits at indent 8 and a
            # step that opens with `- run:` is read like one that opens with `- name:`; same length, offsets kept
            stext = STEP_KEY_PAD + jtext[sm.end():send]
            nm = re.search(r"^        name: (.*)$", stext, re.M)
            steps.append({"index": k, "text": stext, "base": jbase + sm.start(), "name": nm.group(1).strip() if nm else UNNAMED})
        out.append({"job": jm.group(1), "text": jtext, "base": jbase, "steps": steps})
    return out


def pytest_invocations(src, read=None, switch_read=None):
    """Every pytest invocation in a workflow's text, as dicts: job, step (the `name:`, else "(unnamed step)"), line (in
    the file) and last_line (the last file line of the command as read: its last backslash continuation; the span
    line..last_line is what the line census counts as read), env (the
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
    starts with), and for a pytest command in a step whose run text holds a `${{ }}` expression (keyed on the
    spelling, comments included: GitHub substitutes the expression before the shell reads the text, so the text read
    here is not the text the shell runs), a dict with `unparsed` set to the reason and args None; and a step whose run
    text holds `${{` and spells pytest anywhere in it (PYTEST_WORD_RE), a comment line or a trailing shell comment
    included, that gave none of these gets one such dict at its first line that spells pytest (round 5's ruling A,
    2026-09-24: the substituted text can end a comment with a newline and make what follows a command; the population
    is the run text as read, so an expression in a YAML comment after a plain one-line run, which YAML drops before
    GitHub substitutes anything, is outside it). `read`, when a list is given, receives {first, last, text} for every command line the
    parser read in a step's run, row or not (pytest_line_census judges the pip exclusion on that text; the switch
    census counts those lines as run text read). `switch_read`, when a list is given, receives {line, job, step, scope}
    for every ROMP_SDK_REQUIRE key line _env_block read in a scope the merge reads (the workflow's env, a job's env, a
    step's env; job and step None where the scope is wider).
    A text parse over the file's own indentation (top-level keys at column 0, jobs at 2, job keys at 4, steps at 6,
    step keys at 8, env keys and run block lines at 10), the way this file's other pins and tests/test_ci_bats_bound.py
    read it: no YAML library in the test deps. A step's text runs from its dash to the next step's dash or to the end of
    the steps sequence, the first line after it indented 4 or less that is not blank or a comment, so a job key after
    the steps (services.<id>.env, strategy.matrix.name) is never read as the last step's own. The YAML it reads is the forms the allowlist scan accepts
    (yaml_line_forms, the owner's allowlist design, 2026-09-24), whose two-column nesting is this layout; every other
    form is refused by the scan at its line and not read here, so the parser models no YAML beyond the accepted forms (a
    form the scan does not accept is refused by name; reword the step in an accepted form). A step in any other layout
    (steps at indent 4 or 8, `-   name:`, a flow mapping, a quoted or spaced `run` key) gives no row here; the scan
    refuses it, pytest_line_census reds its pytest line, and unread_job_keys a job key this parser does not read. The
    run forms read are _step_run's; comment lines are skipped (the expression rule above aside); a line ending in an
    unescaped backslash is joined with the next the way the shell joins it (_continues, _join_continuation: nothing inserted).
    Outside this parser by construction: a pytest run by a
    script or action the workflow calls, a run line that never spells pytest (a `$RUNNER` variable set elsewhere, or
    `make test`), and anything that rewrites a pytest command's arguments after the run text is read (a shell function
    or alias the run text defines, a python earlier on PATH, a step's shell: or a job's defaults; run_pytest_status
    refuses those it can see on the Run pytest step)."""
    sections = _top_sections(src)

    def env_of(text, indent, base, scope, job=None, step=None):
        keys = []
        out = _env_block(text, indent, keys)
        if switch_read is not None:
            switch_read.extend({"line": _line_of(src, base + off), "job": job, "step": step, "scope": scope}
                               for off, name in keys if name == SWITCH)
        return out

    wf_env = {}
    for off, text in sections.get("env", []):
        wf_env.update(env_of(text, 0, off, "workflow"))
    found = []
    for jb in workflow_steps(src):
        job, jtext, jbase = jb["job"], jb["text"], jb["base"]
        job_env = dict(wf_env)
        job_env.update(env_of(jtext, 4, jbase, "job", job))
        dm = re.search(r"^    defaults:\n      run:\n        working-directory: (.*)$", jtext, re.M)
        job_wd = dm.group(1).strip() if dm else None
        parsed = []
        job_runs = []
        run_spellings, prefix_spellings, step_names = {}, {}, {}
        for st in jb["steps"]:
            k, stext, sbase, step = st["index"], st["text"], st["base"], st["name"]
            wm = re.search(r"^        working-directory: (.*)$", stext, re.M)
            cwd = wm.group(1).strip() if wm else job_wd
            env = dict(job_env)
            env.update(env_of(stext, 8, sbase, "step", job, step))
            lines = _step_run(stext)
            if lines is None:
                continue
            run_text = "".join(t + "\n" for _o, t, _e in lines)
            job_runs.append(run_text)
            run_spellings[k], prefix_spellings[k], step_names[k] = run_text.count(SWITCH), 0, step
            spelled = None          # the first command line that spells pytest, a comment line included
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
                if spelled is None and PYTEST_WORD_RE.search(cmd):
                    spelled = (at, last_at, cmd)
                if cmd.lstrip().startswith("#"):
                    continue
                if not PYTEST_WORD_RE.search(cmd):
                    continue
                base = {"job": job, "step": step, "line": at, "last_line": last_at, "run": run_text, "cwd": cwd, "cmd": cmd,
                        "step_index": k}
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
            # a step whose run text holds an expression and spells pytest anywhere, in a comment line or a trailing
            # comment too, and that gave no row above (round 5's ruling A, 2026-09-24): GitHub substitutes the
            # expression before the shell reads the text, so `# ${{ fromJSON('"\n"') }}python -m pytest` ends the
            # comment and runs pytest with neither the flag nor the switch, where the parser skipped the comment line
            # and the shell split cut the trailing comment. The row sits at the step's first line that spells pytest
            # (keyed on the spelling, on the joined command line or on a raw line of the run text)
            if "${{" in run_text and not any(p["step_index"] == k for p in parsed):
                if spelled is None:
                    spelled = next(((_line_of(src, sbase + o), _line_of(src, sbase + o), t) for o, t, _e in lines
                                    if PYTEST_WORD_RE.search(t)), None)
                if spelled is not None:
                    parsed.append({"job": job, "step": step, "line": spelled[0], "last_line": spelled[1], "run": run_text,
                                   "cwd": cwd, "cmd": spelled[2], "step_index": k, "env": dict(env), "args": None,
                                   "unparsed": EXPRESSION_UNPARSED + EXPRESSION_NO_ROW})
        for inv in parsed:
            # what the run block does to the switch (review round 4, 2026-09-23): the env merge above reads the declared
            # scopes alone, so a step whose run text spells the switch anywhere but as a VAR=value prefix on its pytest
            # command (an unset, export, declare, env -u or assignment, on an earlier line or before the command on its
            # own line), or whose job's other run texts spell it (a write to $GITHUB_ENV reaches the steps after it), is
            # unparsed: the parser does not run the shell, so it cannot say what value pytest starts with
            k = inv["step_index"]
            # an expression in the run text (the allowlist's second verify pass, 2026-09-24): GitHub substitutes it
            # into the text before the shell reads it, so the text read here is not the text the shell runs, and
            # `${{ '#' }}` before the flag, or a matrix value '#' there, cut the flag off as a comment while the step
            # read ok; keyed on the spelling, comments included, wherever in the step's run text it sits
            if inv["unparsed"] is None and "${{" in inv["run"]:
                inv["unparsed"] = EXPRESSION_UNPARSED
                inv["args"] = None
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
    it), unless one of two exclusions, and no others, applies: its key is `name` (NAME_KEY_RE: `name:` or `- name:`,
    never a line that merely contains "name:", so a one-line flow mapping carrying a run counts; in the forms the scan
    accepts the name key is its line's only key, and a flow mapping over several lines is refused by the scan; the
    exclusion is the key's own line, so a name folded or continued onto a line that spells pytest reds there, beside
    the scan's refusal of the fold); or it is a pip install, judged
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
        if NAME_KEY_RE.match(line):
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
    _env_block read in a scope the merge reads (the workflow's env, a job's, a step's: a bare key at the block's first
    key indent, its value on that line), or when it lies in the run text of a step the parser read, whose every spelling
    of the switch the switch half reads as `unparsed` (pytest_invocations). Anything else sets or clears the switch
    where the merge does not look and reds here: an `env:` written as an alias (`env: *x`, the anchored mapping's key
    line unread) or a flow mapping, a quoted or spaced key, a key-shaped line deeper than its block's keys (inside
    another key's block scalar, that key's text to YAML), a step's `shell:` or a job's `defaults: run: shell:` that
    spells the name, a line in a layout the parser does not read. Read here as a key line, and refused by the allowlist
    scan instead (yaml_line_forms): the switch's key line when its value is continued past the line or is a block scalar
    (until the allowlist, 2026-09-24, this census read such a key as not clean and named it), and a key-shaped switch
    line at the key indent inside another key's quoted scalar over several lines. Until 2026-09-23 each of these read ok
    beside a pytest step that ran with the switch at 0, `1 0` or unset. Keyed on the spelling over the whole file, so a
    name: or an if: that spells the switch reds too: rename it. What this census cannot see is a write that does not
    spell the name (module docstring, item 1)."""
    read, switch_read = [], []
    pytest_invocations(src, read, switch_read)
    covered = {e["line"] for e in switch_read}
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


# The allowlist (the owner's allowlist design, 2026-09-24): the YAML forms the scan accepts are the forms the real
# ci.yml uses, derived from the file by the scan itself (PytestPopulation asserts that the file uses every form listed
# here and that each of its lines is in one; PyYAML's event stream read the same forms from the head's file, a scratch
# read, since CI's shape installs no PyYAML). A line in any other form is refused by name at its line, valid YAML
# included: a form the scan does not accept is refused by name; reword the step in an accepted form. Until 2026-09-24
# the scan refused named forms one at a time, and each of three verify passes found forms the line reading half-modelled
# (a plain scalar carried onto a line that opens with a quote, a key-shaped line inside a quoted scalar over several
# lines, a `\n` escape in a double-quoted run starting a second command).
YAML_FORMS_ACCEPTED = (
    "a blank line",
    "a comment line",
    "a trailing comment",
    "a block mapping key",
    "a block sequence entry",
    "a plain scalar on one line",
    "a single-quoted scalar on one line",
    "a double-quoted scalar on one line",
    "a flow sequence of scalars on one line",
    "a literal block scalar as a step's run",
    "a line of a literal block's text",
)
YAML_INDENT_STEP = 2                                              # every nested block sits two columns past its parent key
YAML_KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*):(?= |$)")    # a key as ci.yml spells every key: plain, then `: `
# a tab, a carriage return, any other C0 control or line-break character YAML or str.splitlines reads, and a BOM
YAML_REFUSED_CHAR_RE = re.compile("[\x00-\x09\x0b-\x1f\x7f\x85\u2028\u2029\ufeff]")
# a character outside ASCII: ci.yml holds one only in comment lines, and a line of any other form holding one is
# refused, since Python's str.strip and `\s` read a no-break space or another Unicode space as whitespace where YAML and
# the shell read a word's character (the switch's value `1` then a no-break space read as 1, where the step's
# environment holds the character and the runtime readers compare with == "1"; at the end of a pytest command,
# `-p no:anyio` then a no-break space reads as the flag, and pytest 9.1.1 strips its -p argument the same way, probed
# 2026-09-24, so there the two agree)
YAML_NON_ASCII_RE = re.compile("[^\x00-\x7f]")
LITERAL_HEADER_RE = re.compile(r"\|((?: +#.*)?) *$")              # `|` with nothing after it but a spaced comment
_INDICATOR_WHAT = "a block scalar header with a chomping or indentation indicator, or text after it"
YAML_CONTINUED = ("a line indented past the block it belongs to: a scalar continued past its line, or an indent no key "
                  "above it opens")
# the refusals whose construct YAML carries on to later lines at any indent past its parent's, its own included: the
# lines at the refused line's indent or deeper are read as part of it and not scanned
YAML_CARRIED = ("a quoted scalar continued past its line", "a flow collection continued past its line")
YAML_QUOTED_FORM = {"'": "a single-quoted scalar on one line", '"': "a double-quoted scalar on one line"}
# the keys whose value the parser reads as the text after `key: ` (a step's name and working directory, the job's
# default directory; pytest_invocations, and InstallStep's name reads): on these the scan accepts a plain scalar with no
# trailing comment and nothing else, the one form ci.yml writes them in (the allowlist's second verify pass,
# 2026-09-24: a quoted name or directory, or a name with a trailing comment, valid YAML, read with its quotes or its
# comment, and the module was red for a reason other than a refusal)
YAML_PLAIN_KEYS = ("name", "working-directory")
YAML_PLAIN_KEY_WHAT = ("a %s: value other than a plain scalar with no trailing comment (the parser reads a step's "
                       "name: and working-directory: values as the text after the key)")
YAML_PROPERTY_NAMES = {"&": "an anchor", "*": "an alias", "!": "a tag"}


def _yaml_token(text):
    return text.split(" ", 1)[0].split(",", 1)[0].split("]", 1)[0]


def _yaml_quoted(text, i):
    """The quoted scalar opening at text[i] in an accepted form: (the index just past its closing quote, None), or
    (None, the refusal): a backslash in a double-quoted scalar, `''` in a single-quoted one (ci.yml's quoted scalars
    hold neither escape), or no closing quote on the line."""
    q = text[i]
    j = text.find(q, i + 1)
    if q == '"' and "\\" in (text[i + 1:j] if j >= 0 else text[i + 1:]):
        return None, "a backslash escape in a double-quoted scalar (ci.yml's double-quoted scalars hold none)"
    if q == "'" and j >= 0 and text[j + 1:j + 2] == "'":
        return None, "the '' escape in a single-quoted scalar (ci.yml's single-quoted scalars hold none)"
    if j < 0:
        return None, "a quoted scalar continued past its line"
    return j + 1, None


def _yaml_tail(tail, what):
    """What may follow a closed value on its line: nothing, or a trailing comment after a space. ([forms], None) or
    ([], the refusal)."""
    if not tail.strip():
        return [], None
    if re.match(r" +#", tail):
        return ["a trailing comment"], None
    return [], "text after %s" % what


def _yaml_flow_sequence(v):
    """A key's value that opens with `[`, in the accepted form: a flow sequence of plain or quoted scalars closed on the
    line, nothing but a trailing comment after it. ([forms], None) or ([], the refusal)."""
    i, n, out = 1, len(v), []
    while True:
        while i < n and v[i] == " ":
            i += 1
        if i >= n:
            return [], "a flow collection continued past its line"
        c = v[i]
        if c in ",]":
            return [], "an empty entry in a flow sequence"
        if c in "[{":
            return [], "a flow collection inside a flow sequence"
        if c in YAML_PROPERTY_NAMES:
            return [], "%s (%s)" % (YAML_PROPERTY_NAMES[c], _yaml_token(v[i:]))
        if c == "#":
            return [], "a comment inside a flow sequence"
        if c in "'\"":
            end, what = _yaml_quoted(v, i)
            if what:
                return [], what
            out.append(YAML_QUOTED_FORM[c])
            i = end
        else:
            if c in "-?:%@`|>":
                return [], "a plain scalar opening with an indicator character (%s)" % c
            j = i
            while j < n and v[j] not in ",]":
                j += 1
            # PyYAML ends a plain scalar in a flow collection at `?` as well as at `:`, `,` and a bracket, and then
            # refuses the file (found by mutating the real file: `[m?ain]` was accepted); the real file's entries hold
            # none of these
            if any(ch in v[i:j] for ch in ":#?[{}"):
                return [], "a plain scalar in a flow sequence holding :, #, ?, [, { or }"
            out.append("a plain scalar on one line")
            i = j
        while i < n and v[i] == " ":
            i += 1
        if i >= n:
            return [], "a flow collection continued past its line"
        if v[i] == ",":
            i += 1
            continue
        if v[i] == "]":
            break
        return [], "text between the entries of a flow sequence"
    tail, what = _yaml_tail(v[i + 1:], "a flow sequence")
    return ([] if what else out + ["a flow sequence of scalars on one line"] + tail), what


def _yaml_inline_value(v):
    """A key's value written on the key's line (v: the text after the colon and its spaces, not empty, not a comment,
    not a block scalar header), in an accepted form: ([forms], None), or ([], the refusal)."""
    c = v[0]
    if c in YAML_PROPERTY_NAMES:
        return [], "%s (%s)" % (YAML_PROPERTY_NAMES[c], _yaml_token(v))
    if c == "{":
        return [], "a flow mapping"
    if c == "[":
        return _yaml_flow_sequence(v)
    if c in "'\"":
        end, what = _yaml_quoted(v, 0)
        if what:
            return [], what
        tail, what = _yaml_tail(v[end:], "a quoted scalar")
        return ([] if what else [YAML_QUOTED_FORM[c]] + tail), what
    if c in "-?:,]}%@`":
        return [], "a plain scalar opening with an indicator character (%s)" % c
    text, comment, _rest = v.partition(" #")
    if ": " in text or text.rstrip().endswith(":"):
        return [], "a plain scalar holding ': ' or ending in ':' (a mapping YAML refuses there)"
    return ["a plain scalar on one line"] + (["a trailing comment"] if comment else []), None


def _yaml_unkeyed(rest, after_key):
    """Why a line where a mapping key goes is not one in the accepted form (YAML_KEY_RE), by name."""
    c = rest[0]
    if after_key and c in "|>":
        return "a block scalar header on the line after its key"
    if c in YAML_PROPERTY_NAMES:
        return "%s (%s)" % (YAML_PROPERTY_NAMES[c], _yaml_token(rest))
    if rest.startswith("<<"):
        return "a merge key (<<)"
    if c == "{":
        return "a flow mapping"
    if c == "[":
        return "a flow sequence where a key goes"
    if c == "?" and rest[1:2] in ("", " "):
        return "an explicit key (?)"
    if c == ":" and rest[1:2] in ("", " "):
        return "an explicit key's value (:)"
    if c in "'\"":
        end, what = _yaml_quoted(rest, 0)
        if what:
            return what
        if rest[end:].lstrip(" ").startswith(":"):
            return "a quoted key"
        return "a quoted scalar on the line after its key" if after_key else "a quoted scalar where a key goes"
    if c in "%@`":
        return "a reserved indicator (%s)" % c
    if re.match(r"[^\s:#][^:#]*? +:(?= |$)", rest):
        return "a key with a space before its colon"
    if re.match(r"[^\s:#]+:(?= |$)", rest):
        return "a key spelled with a character ci.yml's keys do not use (%s)" % rest.split(":", 1)[0]
    if re.match(r"[A-Za-z_][A-Za-z0-9_-]*:\S", rest):
        return "a key with no space after its colon"
    if after_key:
        return "a value on the line after its key"
    return "a line that is not a key, a sequence entry, a comment or a blank line"


def yaml_line_forms(src):
    """The allowlist scan of a workflow's text (the owner's allowlist design, 2026-09-24): ({form: [line, ...]} for the
    forms of YAML_FORMS_ACCEPTED the accepted lines use, [(line, text, what)] for every refused line), file lines
    1-based. A line is accepted only in a form the real ci.yml uses: a blank line; a comment line; a block mapping key
    spelled as ci.yml spells every key (letters, digits, `_` and `-`, then `:` and a space or the end of the line), no
    key twice in one mapping; a block sequence entry `- ` whose node is such a key one space past the dash; each nested
    block two columns past its parent key (a sequence's dashes included, and an entry's keys two past its dash); as a
    key's value on the key's line, a plain scalar that opens with no YAML indicator and holds no `: `, a single-quoted
    scalar without `''`, a double-quoted scalar without a backslash, or a flow sequence of such scalars (a plain one
    holding no `:`, `#`, `?` or bracket), each closed on that line and followed by nothing but a spaced trailing
    comment, and on a name: or working-directory: key (YAML_PLAIN_KEYS) the plain scalar alone, with no comment; and a
    literal block header `|` as the value of a step's run (jobs, a job, steps, an entry), whose text is the lines
    indented past the key, each at least as far as the first, which are not scanned as YAML. Every other line is
    refused by name, among them a quoted value or a trailing comment on a name: or working-directory: key, an anchor,
    an alias, a tag, a merge key, an explicit key, a flow mapping, a flow collection inside a flow sequence or
    continued past its line, a quoted scalar continued past its line, a backslash in a double-quoted scalar, `''` in a
    single-quoted one, a folded block, a chomping or indentation indicator, a literal block anywhere but a step's run,
    a header or a value on the line after its key, a plain scalar continued past its line, a directive, a document
    marker, a quoted, spaced or otherwise spelled key, a key twice in one mapping, a sequence at its parent key's
    indent (YAML's compact style), an indentation other than two columns past the parent, a tab or any other control
    character, a character outside ASCII outside a comment line, and a last line with no newline after it (the real
    file ends in one, and _env_block's and JOB_RE's patterns need one). After a
    refused line, the lines that belong to what it opened are not scanned, so a construct is named once, at its first
    line: the lines indented past it (past its key, for a refused value; past its parent key, for the first line of a
    nested value), or, for a quoted scalar or flow collection that YAML carries on, every line from its key's column in;
    scanning resumes at the next line indented no further. Keyed on the text, not on a YAML parser, and its error runs
    one way: a valid line in a form the scan does not accept is refused (a form the scan does not accept is refused by
    name; reword the step in an accepted form)."""
    forms, refused = {}, []
    lines = src.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    stack = [[0, "map", (), set()]]   # the open blocks, outermost first: [indent, "map" or "seq", key path, keys held]
    pending = None                    # a key whose value starts on a later line: (the key's column, the value's key path)
    block = None                      # inside a literal block: [the key's column, the first text line's indent, the widest leading blank]
    skip = None                       # after a refusal: lines indented past this column are not scanned

    def use(names, n):
        for name in names:
            forms.setdefault(name, []).append(n)

    for idx, raw in enumerate(lines):
        n = idx + 1
        indent = len(raw) - len(raw.lstrip(" "))
        body = raw[indent:]
        bad = YAML_REFUSED_CHAR_RE.search(raw)
        wide = YAML_NON_ASCII_RE.search(raw)
        if block is not None:
            if bad or wide:
                refused.append((n, raw.strip(), "a tab or other control character (%r)" % bad.group(0) if bad else
                                "a character outside ASCII outside a comment line (%r)" % wide.group(0)))
                continue
            if not body:
                if block[1] is None:
                    block[2] = max(block[2], len(raw))
                use(["a blank line"], n)
                continue
            if indent > block[0]:
                if block[1] is None:
                    block[1] = indent
                    if block[2] > indent:
                        refused.append((n, raw.strip(), "a literal block whose leading blank line holds more spaces than its first text line"))
                elif indent < block[1]:
                    refused.append((n, raw.strip(), "a line of a literal block indented less than its first text line"))
                    continue
                use(["a line of a literal block's text"], n)
                continue
            block = None
        if skip is not None:
            if not body or body.startswith("#") or indent > skip:
                continue
            skip = None
        after_key, pending = pending, None
        what, new_skip, pushed = None, indent, False
        if bad:
            what = "a tab or other control character (%r)" % bad.group(0)
        elif not body:
            use(["a blank line"], n)
            pending = after_key
            continue
        elif body.startswith("#"):
            use(["a comment line"], n)
            pending = after_key
            continue
        elif wide:
            what = "a character outside ASCII outside a comment line (%r)" % wide.group(0)
        elif indent == 0 and body[:3] in ("---", "...") and body[3:4] in ("", " "):
            what = "a document marker (%s)" % body[:3]
        elif indent == 0 and body.startswith("%"):
            what = "a directive"
        elif after_key is not None and indent > after_key[0] and indent != after_key[0] + YAML_INDENT_STEP:
            what, new_skip = "a block nested %d columns past its key, not %d" % (indent - after_key[0], YAML_INDENT_STEP), after_key[0]
        if what:
            refused.append((n, raw.strip(), what))
            skip = new_skip
            continue
        entry = body == "-" or body.startswith("- ")
        if after_key is not None and indent > after_key[0]:
            stack.append([indent, "seq" if entry else "map", after_key[1], set()])
            pushed = True
        while stack[-1][0] > indent:
            stack.pop()
        top = stack[-1]
        line_forms = []
        if top[0] != indent:
            # the blocks deeper than the line are closed above, so the line sits past the block it belongs to
            what, new_skip = YAML_CONTINUED, top[0]
        elif entry and top[1] != "seq":
            what = ("a sequence entry where a mapping key goes (a list at its parent key's indent, YAML's compact style, or at "
                    "the top level)")
        elif not entry and top[1] == "seq":
            what = "a key or a scalar where a sequence entry goes"
        elif entry and (not body[2:].strip() or body[2:3] == " "):
            what = "a sequence entry whose node is not a key one space past its dash"
        if what:
            refused.append((n, raw.strip(), what))
            if pushed and not entry:
                stack.pop()
                new_skip = after_key[0]
            skip = new_skip
            continue
        if entry:
            line_forms.append("a block sequence entry")
            col, rest = indent + YAML_INDENT_STEP, body[2:]
            stack.append([col, "map", top[2] + ("[]",), set()])
        else:
            col, rest = indent, body
        mapping = stack[-1]
        km = YAML_KEY_RE.match(rest)
        if not km:
            what = _yaml_unkeyed(rest, after_key is not None and pushed)
        elif km.group(1) in mapping[3]:
            what = "a key its mapping already holds (%s)" % km.group(1)
        if what:
            refused.append((n, raw.strip(), what))
            if entry:
                stack.pop()
            elif pushed:
                stack.pop()
                new_skip = after_key[0]
            skip = min(new_skip, indent - 1) if what in YAML_CARRIED else new_skip
            continue
        key = km.group(1)
        mapping[3].add(key)
        line_forms.append("a block mapping key")
        v = rest[km.end():].lstrip(" ")
        if not v or v.startswith("#"):
            use(line_forms + (["a trailing comment"] if v else []), n)
            pending = (col, mapping[2] + (key,))
            continue
        if v[0] in "|>":
            header = LITERAL_HEADER_RE.match(v)
            if v[0] == ">":
                what = "a folded block scalar (ci.yml's blocks are literal)"
            elif not header:
                what = _INDICATOR_WHAT
            elif not (key == "run" and len(mapping[2]) == 4 and mapping[2][0] == "jobs" and mapping[2][2:] == ("steps", "[]")):
                what = "a literal block scalar outside a step's run"
            else:
                use(line_forms + ["a literal block scalar as a step's run"] + (["a trailing comment"] if header.group(1) else []), n)
                block = [col, None, 0]
                continue
        else:
            value_forms, what = _yaml_inline_value(v)
            if not what and key in YAML_PLAIN_KEYS and value_forms != ["a plain scalar on one line"]:
                what = YAML_PLAIN_KEY_WHAT % key
        if what:
            # a refused value's own lines are those indented past its key (an entry's first key sits past the dash, and
            # the entry's later keys are scanned); one YAML carries on is followed from the key's column
            refused.append((n, raw.strip(), what))
            skip = col - 1 if what in YAML_CARRIED else col
            continue
        use(line_forms + value_forms, n)
    if src and not src.endswith("\n"):
        # the allowlist's first verify pass: an env key on a last line with no newline after it was unread by
        # _env_block, whose pattern needs one, and the file was red for the wrong reason
        refused.append((len(lines), lines[-1].strip(), "a last line with no newline after it"))
    return forms, refused


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
    step spells the switch in its run text other than as a prefix on it, or whose job's other steps spell it in theirs,
    or whose step's run text holds a `${{ }}` expression (pytest_invocations); 'ambiguous': a
    named step whose name another pytest-running step of the job shares, so the (job, step name) key names two steps
    (red whatever the invocations carry: a listing under that key would excuse the other step too); 'unlisted':
    anything else, the failure this check exists for (the flag missing has no listing that excuses it)."""
    if inv["unparsed"]:
        return "unparsed"
    if inv["namesakes"]:
        return "ambiguous"
    if not passes_flag(inv["args"]):
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
    """The offender, named: job, step, file line, and what it lacks. The flag half keys on the words `-p` and
    `no:anyio` in the command's own arguments as the shell splits them (passes_flag); the switch half on the merged env
    reading exactly 1."""
    if inv["unparsed"]:
        return "%s / %r (ci.yml line %d): mentions pytest in a run line the parser does not read as a command (%s): %r" % (
            inv["job"], inv["step"], inv["line"], inv["unparsed"], inv["cmd"].strip())
    if inv["namesakes"]:
        return ("%s / %r (ci.yml line %d): another step named %r in this job runs pytest too (ci.yml line%s %s); the listing "
                "and this report key on (job, step name), so the name is ambiguous: rename one" % (
                    inv["job"], inv["step"], inv["line"], inv["step"], "s" if len(inv["namesakes"]) > 1 else "",
                    ", ".join(str(l) for l in inv["namesakes"])))
    lacks = [w for w, ok in (("%s (keyed on the words -p and no:anyio in the command's arguments as the shell splits "
                              "them)" % FLAG_SPELLING, passes_flag(inv["args"])),
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

# The Run pytest step's two allowlists (round 5's ruling C, 2026-09-24; run_pytest_status's docstring is the rule). Every
# argument word of its command is an entry of the first, keyed on its full spelling (a new value is a new entry, with its
# reason), and every key of its merged env an entry of the second; every exception lives in one of the two
RUN_PYTEST_OPTIONS = {
    "-q": "quieter output: it changes what pytest prints, not what it runs or its exit status",
    "-p no:anyio": ("the flag (FLAG_SPELLING), which blocks anyio's plugin; keyed on both words, since -p with another value "
                    "loads or blocks another plugin, which can change what runs and what the run returns"),
    "--durations=10": "prints the ten slowest tests after the run: every test still runs, and the exit status is the run's",
    "--timeout=600": ("pytest-timeout fails a test that runs past 600 s (the step's comment, T230b): it adds a failure and "
                      "discards none"),
    "--timeout-method=thread": ("how pytest-timeout ends a stalled test: the process ends with a failing status (the step's "
                                "comment); it adds a failure and discards none"),
}
RUN_PYTEST_ENV = {
    SWITCH: ("the switch: under it InstalledVersion fails, naming the interpreter, where the SDK does not import; it adds a "
             "failure and discards none"),
    "PYTHON_GIL": ("the free-threaded cell's GIL setting (0 there, empty on every other cell): it changes how the interpreter "
                   "runs threads, not what pytest runs or its exit status"),
}
RUN_PYTEST_WRITE_NAMES = ("GITHUB_ENV", "GITHUB_PATH", "BASH_ENV")
_STATUS_KEY_WHY = {
    "if": "an if: can skip it, and a skipped step or job reports success",
    "continue-on-error": "a continue-on-error: lets the job, or the run, pass over a failure",
    "shell": "a shell: sets the shell the run text runs under, which this check does not read (the default is bash -e)",
    "defaults": "a defaults: can set the shell the run text runs under, which this check does not read (the default is bash -e)",
}


def _env_key_lines(text, env_indent):
    """Every line of the `env:` mapping at `env_indent` spaces in `text` other than a blank or comment line, as
    [(offset in text, line, key)]: key is the name before the colon when the line is a key at the block's first key
    indent (YAML_KEY_RE, the scan's spelling of a key), else None. When the `env:` line carries anything after its colon
    but a comment (a value on the key's own line, an expression or a flow mapping, whose keys cannot be read here), that
    line alone, key None. The block ends at the first such line indented no deeper than `env:`."""
    head = re.search(r"^%senv:(.*)$" % (" " * env_indent), text, re.M)
    if head is None:
        return []
    if not re.fullmatch(r"[ \t]*(?:#.*)?", head.group(1)):
        return [(head.start(), head.group(0), None)]
    out, pos, key_indent = [], head.end() + 1, None
    for line in text[pos:].splitlines(keepends=True):
        body = line.rstrip("\n")
        if body.strip() and not body.lstrip().startswith("#"):
            indent = len(body) - len(body.lstrip(" "))
            if indent <= env_indent:
                break
            key_indent = indent if key_indent is None else key_indent
            km = YAML_KEY_RE.match(body, indent) if indent == key_indent else None
            out.append((pos, body, km.group(1) if km else None))
        pos += len(line)
    return out


def run_pytest_status(src):
    """What holds pytest's failure to the cell (round 5's ruling C, 2026-09-24; this docstring is the rule, in full): the
    Run pytest step's (MATRIX_STEP) exit status is pytest's, and the cell's is the step's. Anything on that step, its job
    or the workflow that can discard pytest's failure, or let pytest exit 0 without running the suite, is refused by name
    at its line. Its examples: an if: or a continue-on-error: on the step or the job (a skipped step or job reports
    success, and continue-on-error passes over the failure); the command followed by `||`, a pipe (a step with no shell:
    runs under GitHub's default bash -e, without pipefail, so a pipe's status is its last command's) or a trailing `&`,
    each of which drops pytest's status. Until the ruling nothing held this: with any of those on the step the module read
    green (the refuter's mutants, 89 passed). The check reads five parts:
    1. no if:, continue-on-error: or shell: key on the step; no if:, continue-on-error: or defaults: key on the job; and
       no defaults: at the top level, since a shell: or a defaults: sets the shell the run text runs under.
    2. The run text is one command line (blank lines and comment lines aside, a backslash continuation joined as the
       shell joins it) whose one shell command (_shell_commands) is the whole line with its comment cut, read by
       PYTEST_CMD_RE. So `||`, a pipe and a trailing `&` are refused, and so are a `;`, a second command and a second
       command line, whether or not they discard the status: an earlier `trap 'exit 0' EXIT` makes a failing run exit
       0, and `; exit 0`, which under bash -e does not, is refused all the same.
    3. Every argument word of that command, as the shell splits it, is an entry of RUN_PYTEST_OPTIONS, keyed on its full
       spelling, each entry with its reason; any other word is refused: among them flags that run no tests (--collect-only,
       --co, --setup-plan), a path, a -k, -m or --deselect that narrows what runs, and a redirection.
    4. Every key of the step's merged env (the workflow's env, the job's, the step's, and a VAR=value prefix on the
       command) is an entry of RUN_PYTEST_ENV, each entry with its reason, so PYTEST_ADDOPTS (options pytest reads from
       the environment), BASH_ENV (a file bash sources before the run text: one holding `trap 'exit 0' EXIT` makes a
       failing run exit 0) and every other key are refused at their line, and so is an env: line of those scopes with
       a value on its own line, whose keys cannot be read.
    5. A run text of the python job that spells GITHUB_ENV, GITHUB_PATH or BASH_ENV is refused at its line, keyed on the
       spelling with comments included, since a `${{ }}` expression can end a comment with a newline and make what
       follows it a command (pytest_invocations' expression rule): a write to $GITHUB_ENV sets a variable for the steps
       after, PYTEST_ADDOPTS or BASH_ENV among them, and a write to $GITHUB_PATH puts another python first on PATH for
       them.
    The residual: a write to those files that does not spell their names, such as one by a script or action a step
    calls (actions/setup-python writes both) or one through `${{ github.env }}`; and a command that names its
    interpreter or pytest by a path, which may be a script. Returns (the file line of the step's command line that
    PYTEST_CMD_RE reads as pytest, whatever else is refused on it, [(line, text, reason)] refused); a missing job, step
    or run text is a refusal."""
    lines_of = src.splitlines()
    read, refused = [], []

    def refuse(offset, reason):
        n = _line_of(src, offset)
        refused.append((n, lines_of[n - 1].strip(), reason))

    sections = _top_sections(src)
    for off, _text in sections.get("defaults", []):
        refuse(off, "a defaults: at the top level: " + _STATUS_KEY_WHY["defaults"])
    jobs = [jb for jb in workflow_steps(src) if jb["job"] == MATRIX_STEP[0]]
    if not jobs:
        refused.append((0, "", "no job %r in the workflow: re-anchor this check" % MATRIX_STEP[0]))
    for jb in jobs:
        for km in re.finditer(r"^    (if|continue-on-error|defaults):", jb["text"], re.M):
            refuse(jb["base"] + km.start(), "a %s: key on the Run pytest step's job: %s" % (km.group(1), _STATUS_KEY_WHY[km.group(1)]))
        for st in jb["steps"]:
            for o, text, _e in _step_run(st["text"]) or []:
                names = [n for n in RUN_PYTEST_WRITE_NAMES if n in text]
                if names:
                    refuse(st["base"] + o, "a run text of the Run pytest step's job spells %s (keyed on the spelling, comments "
                                           "included): a write to $GITHUB_ENV sets a variable for the steps after, and one to "
                                           "$GITHUB_PATH puts another program first on PATH for them" % ", ".join(names))
        steps = [st for st in jb["steps"] if st["name"] == MATRIX_STEP[1]]
        if not steps:
            refused.append((0, "", "no step %r in the job %r: re-anchor this check" % (MATRIX_STEP[1], MATRIX_STEP[0])))
        for st in steps:
            stext, sbase = st["text"], st["base"]
            for km in re.finditer(r"^        (if|continue-on-error|shell):", stext, re.M):
                refuse(sbase + km.start(), "a %s: key on the Run pytest step: %s" % (km.group(1), _STATUS_KEY_WHY[km.group(1)]))
            scopes = [(off, text, 0) for off, text in sections.get("env", [])] + [(jb["base"], jb["text"], 4), (sbase, stext, 8)]
            for base, text, indent in scopes:
                for o, _line, key in _env_key_lines(text, indent):
                    if key is None:
                        refuse(base + o, "an env: line of the Run pytest step's merged env whose key this check cannot read, "
                                         "so it is not an entry of RUN_PYTEST_ENV")
                    elif key not in RUN_PYTEST_ENV:
                        refuse(base + o, "the env key %s in the Run pytest step's merged env, not an entry of RUN_PYTEST_ENV "
                                         "(an entry needs its reason: PYTEST_ADDOPTS hands pytest options, BASH_ENV runs a "
                                         "file before the run text)" % key)
            run = _step_run(stext)
            if run is None:
                refuse(sbase, "the Run pytest step has no run: key")
                continue
            commands, j = [], 0
            while j < len(run):
                off, cmd, _last = run[j]
                while _continues(cmd) and j + 1 < len(run):
                    j += 1
                    cmd = _join_continuation(cmd, run[j][1])
                j += 1
                if cmd.strip() and not cmd.lstrip().startswith("#"):
                    commands.append((off, cmd))
            if not commands:
                refuse(sbase, "the Run pytest step's run text holds no command")
                continue
            target = next(((o, c) for o, c in commands if PYTEST_CMD_RE.match(_comment_cut(c).strip())), None)
            if target is not None:
                read.append(_line_of(src, sbase + target[0]))
            target = target or commands[0]
            for o, _c in commands:
                if o != target[0]:
                    refuse(sbase + o, "a second command line in the Run pytest step's run text: the step runs one command, "
                                      "since another (an earlier trap 'exit 0' EXIT among them) can set its exit status")
            off, cmd = target
            parts = _shell_commands(cmd)
            if len(parts) != 1 or parts[0] != _comment_cut(cmd).strip():
                refuse(sbase + off, "the Run pytest command line holds more than its one shell command (an operator: ||, a "
                                    "pipe, a trailing &, a ;): the step's exit status must be pytest's")
                continue
            hit = PYTEST_CMD_RE.match(parts[0])
            if not hit:
                refuse(sbase + off, "the Run pytest command line is not a command PYTEST_CMD_RE reads as pytest")
                continue
            for name, _value in INLINE_ENV_RE.findall(hit.group("env")):
                if name not in RUN_PYTEST_ENV:
                    refuse(sbase + off, "the env key %s, a prefix on the Run pytest command, not an entry of RUN_PYTEST_ENV" % name)
            try:
                words = shlex.split(hit.group("args"), posix=True)
            except ValueError:
                refuse(sbase + off, "the Run pytest command's arguments do not split as the shell splits them")
                continue
            entries = sorted((tuple(k.split(" ")) for k in RUN_PYTEST_OPTIONS), key=len, reverse=True)
            i = 0
            while i < len(words):
                entry = next((e for e in entries if tuple(words[i:i + len(e)]) == e), None)
                if entry is None:
                    refuse(sbase + off, "the argument %r on the Run pytest command, not an entry of RUN_PYTEST_OPTIONS (an "
                                        "entry needs its reason: --collect-only, --co and --setup-plan run no tests, and a "
                                        "path or a -k narrows what runs)" % words[i])
                    i += 1
                else:
                    i += len(entry)
    return read, refused


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
    goes is a job the parser reads, so no step is read under the job above it; and every line of the file is in a YAML
    form the file itself uses (the allowlist, yaml_line_forms, the owner's allowlist design, 2026-09-24), the forms
    derived from the file, so the parser and the censuses read no YAML they do not model; and the Run pytest step's exit
    status is pytest's and the cell's the step's (run_pytest_status, round 5's ruling C, 2026-09-24). Outside the check:
    a run line that never spells pytest, a pytest run by a script or action a step calls, anything that rewrites a
    pytest command's arguments after the run text is read (a shell function or alias, a python earlier on PATH, a
    step's shell:; on the Run pytest step run_pytest_status refuses those it can see), and any other workflow file."""
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
        matrix = [e["line"] for e in switch_read if (e["job"], e["step"]) == MATRIX_STEP]
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

    def test_every_line_of_ci_yml_is_in_a_form_the_allowlist_accepts(self):
        # the owner's allowlist design (2026-09-24): the parser and the two censuses read the YAML forms the real file
        # uses and nothing else, and the scan refuses every other line by name (yaml_line_forms; its rows in
        # PopulationCheckReds). Until then the scan refused named forms one at a time and three verify passes found
        # forms it half-modelled
        refused = yaml_line_forms(self.src)[1]
        self.assertEqual(refused, [], "lines of ci.yml in a YAML form the scan does not accept (the forms the file uses, "
                         "YAML_FORMS_ACCEPTED). A form the scan does not accept is refused by name; reword the step in an "
                         "accepted form:\n  " + "\n  ".join("line %d: %s (%s)" % f for f in refused))
        # the scan reads to the end of the real file: an alias appended as its last line is named there (a scan left
        # inside a literal block, or stopped early, would read nothing after the point it stopped)
        last = len(self.src.rstrip("\n").splitlines()) + 1
        self.assertEqual(yaml_line_forms(self.src.rstrip("\n") + "\nzz-alias: *nowhere\n")[1],
                         [(last, "zz-alias: *nowhere", "an alias (*nowhere)")])

    def test_the_forms_the_allowlist_accepts_are_the_forms_ci_yml_uses(self):
        # the allowlist is derived from the file, by the scan itself (CI's shape installs no YAML library): every form
        # YAML_FORMS_ACCEPTED lists is one the real file uses, and every line of the file is in one. A form the file
        # stops using leaves the list; a form it starts to use is refused until the scan reads it and a row pins it
        forms, _refused = yaml_line_forms(self.src)
        self.assertEqual(sorted(forms), sorted(YAML_FORMS_ACCEPTED), "the forms the scan accepted in ci.yml are not the "
                         "forms YAML_FORMS_ACCEPTED lists: drop a form the file no longer uses from the list")
        lines = len(self.src.splitlines())
        self.assertEqual(sorted(set().union(*forms.values())), list(range(1, lines + 1)), "a line of ci.yml the scan "
                         "neither accepted in a form nor refused")

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

    def test_nothing_on_the_run_pytest_step_its_job_or_the_workflow_can_discard_pytests_failure(self):
        # round 5's ruling C (2026-09-24): the check held the flag and the switch on the Run pytest command, and nothing
        # held that pytest's failure reaches the cell; an if:, a continue-on-error, `|| true`, a pipe, a trailing `&` or
        # --collect-only on the step each left the module green (the refuter's mutants). The step's exit status is
        # pytest's and the cell's is the step's (run_pytest_status; its cases in PopulationCheckReds). The read must hold
        # the matrix step's own pytest line, so an empty read is red, not green
        read, refused = run_pytest_status(self.src)
        self.assertEqual(refused, [], "on the Run pytest step, its job or the workflow, something that can discard pytest's "
                         "failure or let it exit 0 without running the suite (run_pytest_status's docstring is the rule; "
                         "RUN_PYTEST_OPTIONS and RUN_PYTEST_ENV are its two allowlists, each entry with its reason):\n  "
                         + "\n  ".join("line %d: %s (%s)" % r for r in refused))
        matrix = [i["line"] for i in self.found if (i["job"], i["step"]) == MATRIX_STEP]
        self.assertEqual(read, matrix, "the check read no Run pytest command, or another line than the population's: an empty "
                         "or partial read is red, not green")

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
            self.assertTrue(passes_flag(inv["args"]), "the served step's pytest line %d lacks %s (keyed on those "
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
# the step's first line, the arguments the parser must read from it). Each is in the forms the allowlist accepts
# (yaml_line_forms); the chomping indicators, the folded block and the plain scalar continued on the next line, read
# here until the allowlist (2026-09-24), are refused by the scan now, and their rows are in YAML_REFUSED_ROWS
READ_FORMS = (
    ("single line", "      - name: Form (pytest)\n        run: python -m pytest tests/test_a.py -q -p no:anyio\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("literal block", "      - name: Form (pytest)\n        run: |\n          set -e\n          python -m pytest tests/test_a.py -q -p no:anyio\n",
     3, "tests/test_a.py -q -p no:anyio"),
    ("double-quoted scalar", "      - name: Form (pytest)\n        run: \"python -m pytest tests/test_a.py -q -p no:anyio\"\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("single-quoted scalar, a trailing comment", "      - name: Form (pytest)\n        run: 'python -m pytest tests/test_a.py -q -p no:anyio'  # c\n",
     1, "tests/test_a.py -q -p no:anyio"),
    ("plain scalar, a trailing comment", "      - name: Form (pytest)\n        run: python -m pytest tests/test_a.py -q -p no:anyio  # c\n",
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
# The allowlist's refusals (the owner's allowlist design, 2026-09-24), a row per refused form, each spliced into a
# scratch copy of the live file: (label, where, text, ((line in the text, what the scan names), ...), alone). `where`:
# "first" opens the shell job's steps, "last" ends them, "job" is a job before the shell job, "start" and "end" open and
# end the file, "+env" sets the switch in the shell job's env first. `alone`: nothing but the scan names a line (the
# population check, the two censuses, the job-key check), so the refusal is what reds the plant. The pre-push lenses'
# and the three verify passes' plants are named by their ids (the round-4 takes record); this build's own by AL-; the
# allowlist's first verify pass's plants and mutants by that pass and their ids.
RUN_OK = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
_SW_JOB = '    runs-on: ubuntu-latest\n    env:\n      %s: "1"\n' % SWITCH
_TWO = "          python -m pytest -q tests/test_a.py\n          python -m pytest -q -p no:anyio tests/test_b.py\n"
_ESCAPE = "a backslash escape in a double-quoted scalar (ci.yml's double-quoted scalars hold none)"
_INDICATOR = _INDICATOR_WHAT
_ENTRY = "a sequence entry whose node is not a key one space past its dash"
# a job appended at the file's end: its env sets the switch to 1, and after its flagged pytest step's run line comes one
# line (line 8 of the text) that opens as a comment and holds, in order, `# note`, the planted character, `env:`, the
# character again, and a double-quoted key that spells the switch through a \x52 escape, set to 0
_HIDDEN_ENV = ("  zz-hidden:\n" + _SW_JOB + "    steps:\n      - name: Hidden env (pytest)\n" + RUN_OK +
               '        # note%s        env:%s          "ROMP_SDK_\\x52EQUIRE": "0"\n')
YAML_REFUSED_ROWS = (
    # node properties and the other YAML-only constructs
    ("an anchor on a name: value, aliased by a run (N06)", "first",
     "      - name: &cmd python -m pytest tests/test_a.py -q\n        run: *cmd\n",
     ((1, "an anchor (&cmd)"), (2, "an alias (*cmd)")), True),
    ("an anchored step aliased into a job without the switch (A01b)", "job",
     "  anch:\n" + _SW_JOB + "    steps:\n      - &pystep\n        name: Anchored step (pytest)\n" + RUN_OK +
     "  alias:\n    runs-on: ubuntu-latest\n    steps:\n      - *pystep\n",
     ((6, "an anchor (&pystep)"), (12, "an alias (*pystep)")), True),
    ("an anchored steps list aliased into a job without the switch (A02b)", "job",
     "  anch:\n" + _SW_JOB + "    steps: &st\n      - name: In anchored list (pytest)\n" + RUN_OK +
     "  copy:\n    runs-on: ubuntu-latest\n    steps: *st\n",
     ((5, "an anchor (&st)"), (10, "an alias (*st)")), True),
    ("env: *x, its anchor on a line of its own, the switch 0 in it (B08)", "job",
     "  setter:\n" + _SW_JOB + "    steps:\n      - name: Env anchor\n        env:\n          &zeroenv\n"
     '          %s: "0"\n        run: echo anchor\n      - name: Env alias (pytest)\n        env: *zeroenv\n' % SWITCH + RUN_OK,
     ((8, "an anchor (&zeroenv)"), (12, "an alias (*zeroenv)")), True),
    ("a tag on a run's literal block, two pytest commands, the first unflagged (review round 4's M1)", "first+env",
     "      - name: Tagged (pytest)\n        run: !!str |\n" + _TWO, ((2, "a tag (!!str)"),), False),
    ("a merge key bringing a run into a step", "first",
     "      - &base\n        name: Base\n        run: echo base\n      - <<: *base\n        name: Merged\n",
     ((1, "an anchor (&base)"), (4, "a merge key (<<)")), True),
    ("an explicit key and its value, an anchor after the ? and its alias (Y21)", "first",
     "      - name: Explicit key\n        ? &rk run\n        : echo one\n      - name: Explicit alias (pytest)\n        ? *rk\n"
     "        : python -m pytest tests/test_a.py -q\n",
     ((2, "an explicit key (?)"), (3, "an explicit key's value (:)"), (5, "an explicit key (?)"), (6, "an explicit key's value (:)")), False),
    ("a document start marker carrying an anchor (Y22)", "start", "--- &doc\n", ((1, "a document marker (---)"),), True),
    ("a directive", "start", "%YAML 1.2\n", ((1, "a directive"),), True),
    ("a document end marker", "end", "...\n", ((1, "a document marker (...)"),), False),
    # flow collections
    ("a one-line flow-mapping step (N01)", "first", "      - {name: Flow step, run: python -m pytest tests/test_a.py -q}\n",
     ((1, "a flow mapping"),), False),
    ('a flow mapping over several lines, a JSON-style "run": after the name (N04)', "first",
     '      - {\n          name: FlowAdj, "run":python -m pytest tests/test_a.py -q\n        }\n', ((1, "a flow mapping"),), True),
    ("a flow env on a step, the switch 0 in it", "first+env", '      - name: Flow env (pytest)\n        env: {%s: "0"}\n' % SWITCH + RUN_OK,
     ((2, "a flow mapping"),), False),
    ("a flow mapping inside a flow sequence", "first", "      - uses: ./a\n        with: [{shell: bash}]\n",
     ((2, "a flow collection inside a flow sequence"),), True),
    ("a flow sequence continued past its line", "first", "      - uses: ./a\n        with:\n          list: ['3.10',\n            main]\n",
     ((3, "a flow collection continued past its line"),), True),
    ("a comment right after a flow sequence's bracket, a double-quoted run behind it (D02)", "job",
     "  hid:\n    runs-on: ubuntu-latest\n    steps: [#]\n"
     '      {uses: actions/checkout@v4}, {run: "true; pip install pytest\\npytest tests/test_a.py -q"} ]\n',
     ((3, "a comment inside a flow sequence"),), True),
    ("an empty entry in a flow sequence", "first", "      - uses: ./a\n        with:\n          list: [a, , b]\n",
     ((3, "an empty entry in a flow sequence"),), True),
    ("a plain scalar holding # in a flow sequence (close 2's B6, valid YAML)", "first",
     "      - uses: ./a\n        with:\n          list: [a#b, c]\n", ((3, "a plain scalar in a flow sequence holding :, #, ?, [, { or }"),), True),
    ("a plain scalar holding ? in a flow sequence, which PyYAML refuses", "first",
     "      - uses: ./a\n        with:\n          list: [m?ain]\n", ((3, "a plain scalar in a flow sequence holding :, #, ?, [, { or }"),), True),
    ("text after a flow sequence", "first", "      - uses: ./a\n        with:\n          list: [a] b\n",
     ((3, "text after a flow sequence"),), True),
    ("two entries of a flow sequence without a comma", "first", "      - uses: ./a\n        with:\n          list: ['a' 'b']\n",
     ((3, "text between the entries of a flow sequence"),), True),
    ("a flow sequence where a key goes", "first", "      - [python -m pytest tests/test_a.py -q]\n",
     ((1, "a flow sequence where a key goes"),), False),
    # inside a flow sequence, each a refusal whose deletion left every test green (the allowlist's first verify pass,
    # M22, M24 and M25)
    ("an anchor inside a flow sequence (M22)", "first", "      - uses: ./a\n        with:\n          list: [&a main]\n",
     ((3, "an anchor (&a)"),), True),
    ("a tag inside a flow sequence (M22)", "first", "      - uses: ./a\n        with:\n          list: [!!str main]\n",
     ((3, "a tag (!!str)"),), True),
    ("a plain scalar opening with an indicator character inside a flow sequence (M24)", "first",
     "      - uses: ./a\n        with:\n          list: [-main]\n", ((3, "a plain scalar opening with an indicator character (-)"),), True),
    ("a flow sequence left open after an entry, its comma on the next line (M25)", "first",
     "      - uses: ./a\n        with:\n          list: ['3.10'\n            , main]\n", ((3, "a flow collection continued past its line"),), True),
    # quoted scalars
    ("the switch line inside a step env's double-quoted scalar over several lines (Z01)", "last",
     '      - name: Quoted text (pytest)\n        env:\n          NOTES: "first line\n          %s: \'1\'\n          end"\n' % SWITCH + RUN_OK,
     ((3, "a quoted scalar continued past its line"),), True),
    ("the switch line inside a step name's quoted scalar over the env lines (Z04b)", "last",
     '      - name: "Quoted name\n        env:\n          %s: \'1\'\n        tail"\n' % SWITCH + RUN_OK,
     ((1, "a quoted scalar continued past its line"),), True),
    ("a double-quoted run whose \\n escape starts a second, unflagged pytest (Q01)", "last+env",
     '      - name: Escaped newline (pytest)\n        run: "python -m pytest tests/test_a.py -q -p no:anyio \\npytest tests/test_b.py -q"\n',
     ((2, _ESCAPE),), True),
    ("a double-quoted env key whose \\x escape spells the switch, set to 0 (Q03)", "last+env",
     '      - name: Escaped key (pytest)\n        env:\n          "ROMP_SDK_\\x52EQUIRE": "0"\n' + RUN_OK, ((3, _ESCAPE),), True),
    ("the '' escape in a single-quoted run (Y14)", "first", "      - name: Single escape\n        run: 'echo ''a'''\n",
     ((2, "the '' escape in a single-quoted scalar (ci.yml's single-quoted scalars hold none)"),), True),
    ("a comment right after a quoted run's closing quote (close 2's B1)", "last+env",
     '      - name: Quoted then hash (pytest)\n        run: "python -m pytest tests/test_a.py -q -p no:anyio"#c\n',
     ((2, "text after a quoted scalar"),), True),
    ("a quoted run key", "first+env", '      - name: Quoted run key (pytest)\n        "run": python -m pytest tests/test_a.py -q -p no:anyio\n',
     ((2, "a quoted key"),), False),
    ("a quoted run on the line after its key", "first+env", '      - name: Quoted next (pytest)\n        run:\n          "python -m pytest tests/test_a.py -q"\n',
     ((3, "a quoted scalar on the line after its key"),), False),
    # block scalars
    ("a folded run block (read as paragraphs until the allowlist)", "first+env",
     "      - name: Folded (pytest)\n        run: >\n          python -m pytest tests/test_a.py\n          -q -p no:anyio\n",
     ((2, "a folded block scalar (ci.yml's blocks are literal)"),), False),
    ("a literal run block with strip chomping", "first+env",
     "      - name: Strip (pytest)\n        run: |-\n          python -m pytest tests/test_a.py -q -p no:anyio\n", ((2, _INDICATOR),), False),
    ("a literal run block with an indentation indicator", "first+env",
     "      - name: Indented (pytest)\n        run: |2\n            python -m pytest tests/test_a.py -q -p no:anyio\n", ((2, _INDICATOR),), False),
    ("a literal block as an env value, its text spelling the switch (S10)", "last",
     '      - name: Block text (pytest)\n        env:\n          NOTES: |\n            %s: "1"\n' % SWITCH + RUN_OK,
     ((3, "a literal block scalar outside a step's run"),), False),
    # each clause of the literal block's place, a step's run (the allowlist's second verify pass, N01 to N03: with one
    # clause taken out every test stayed green; the plant of each read red through a census, or PyYAML refused it)
    ("a step's name: as a literal block (N01)", "first", "      - name: |\n          Block name\n        run: echo hi\n",
     ((1, "a literal block scalar outside a step's run"),), True),
    ("a steps entry's run: as a literal block under a top-level key other than jobs (N02)", "end",
     "zz:\n  a:\n    steps:\n      - run: |\n          echo hi\n", ((4, "a literal block scalar outside a step's run"),), True),
    ("a service's run: as a literal block, four keys deep under jobs (N03)", "job",
     "  svc:\n    runs-on: ubuntu-latest\n    services:\n      db:\n        run: |\n          echo hi\n    steps:\n"
     "      - run: echo ok\n", ((5, "a literal block scalar outside a step's run"),), True),
    ("an empty folded block as the switch's value, in a job with no pytest step (E35)", "job",
     "  nopy:\n    runs-on: ubuntu-latest\n    env:\n      %s: >-\n      OTHER: x\n    steps:\n      - run: echo hi\n" % SWITCH,
     ((4, "a folded block scalar (ci.yml's blocks are literal)"),), True),
    ("a run's literal block header on the line after its key, two pytest commands (H01)", "first+env",
     "      - name: Header next (pytest)\n        run:\n          |\n" + _TWO, ((3, "a block scalar header on the line after its key"),), False),
    ("a run's value on the line after its key", "first+env",
     "      - name: Value next (pytest)\n        run:\n          python -m pytest tests/test_a.py -q -p no:anyio\n",
     ((3, "a value on the line after its key"),), False),
    ("a line of a literal run block less indented than its first, an unflagged pytest (AL-08)", "first+env",
     "      - name: Ragged (pytest)\n        run: |\n            echo a\n          python -m pytest tests/test_a.py -q\n",
     ((4, "a line of a literal block indented less than its first text line"),), False),
    ("a literal run block whose leading blank line holds more spaces than its first line (AL-09)", "first+env",
     "      - name: Wide blank (pytest)\n        run: |\n              \n          python -m pytest tests/test_a.py -q -p no:anyio\n",
     ((4, "a literal block whose leading blank line holds more spaces than its first text line"),), True),
    # plain scalars
    ("a plain run continued on the next line (read as one folded command until the allowlist)", "first+env",
     "      - name: Continued (pytest)\n        run: python -m pytest tests/test_a.py\n          -q -p no:anyio\n", ((3, YAML_CONTINUED),), False),
    ("the switch's plain value continued on the next line, `1 0` to YAML", "last",
     "      - name: Continued value (pytest)\n        env:\n          %s: 1\n            0\n" % SWITCH + RUN_OK, ((4, YAML_CONTINUED),), True),
    ("a name continued onto a line that opens with a quote, a name anchor and its alias behind it (W02)", "first",
     '      - name: Prior step\n          "x\n        run: echo prior\n      - name: &cmd python -m pytest tests/test_a.py -q\n        run: *cmd\n',
     ((2, YAML_CONTINUED), (4, "an anchor (&cmd)"), (5, "an alias (*cmd)")), True),
    ("a plain scalar holding ': ' (Y01, which PyYAML refuses)", "first", '      - name: Quoted amp\n        run: echo "&foo *bar <<: baz"\n',
     ((2, "a plain scalar holding ': ' or ending in ':' (a mapping YAML refuses there)"),), True),
    ("a plain scalar opening with an indicator character", "first", "      - name: Dash\n        run: -x\n",
     ((2, "a plain scalar opening with an indicator character (-)"),), True),
    # the value ending in ':' (the allowlist's second verify pass, N07: with that clause taken out every test stayed
    # green); the parser reads the switch as `1:`, which is not 1, and PyYAML refuses the line
    ("the switch's plain value ending in ':' (N07)", "last",
     "      - name: Colon value (pytest)\n        env:\n          %s: 1:\n" % SWITCH + RUN_OK,
     ((3, "a plain scalar holding ': ' or ending in ':' (a mapping YAML refuses there)"),), False),
    ("a line that is no key: a plain scalar at the top level", "end", "stray text\n",
     ((1, "a line that is not a key, a sequence entry, a comment or a blank line"),), False),
    # structure and keys
    ("steps at their key's indent, YAML's compact list style (A01)", "job",
     "  compact:\n    runs-on: ubuntu-latest\n    steps:\n    - name: Compact (pytest)\n      run: python -m pytest tests/test_a.py -q\n",
     ((4, "a sequence entry where a mapping key goes (a list at its parent key's indent, YAML's compact style, or at the top level)"),), False),
    ("steps nested four columns past their key (A03)", "job",
     "  deep:\n    runs-on: ubuntu-latest\n    steps:\n        - name: Deep (pytest)\n          run: python -m pytest tests/test_a.py -q\n",
     ((4, "a block nested 4 columns past its key, not 2"),), False),
    ("step env keys nested four columns past env: (Z08, valid YAML)", "last",
     '      - name: Deep env keys (pytest)\n        env:\n            %s: "1"\n' % SWITCH + RUN_OK,
     ((3, "a block nested 4 columns past its key, not 2"),), True),
    ("`-   name:`, the key three columns past the dash (A04)", "first",
     "      -   name: Wide dash (pytest)\n          run: python -m pytest tests/test_a.py -q\n", ((1, _ENTRY),), False),
    ("a sequence entry whose node is on the next line", "first", "      -\n        name: Next line\n        run: echo hi\n", ((1, _ENTRY),), True),
    # the allowlist's first verify pass's M31 scans a carried construct's lines at its own column, which changes only
    # what the scan reports after a refusal that already stands, so it affects naming only; this row pins the naming (a
    # construct is named once, at its first line)
    ("a sequence entry that is a quoted scalar continued at its dash's column (M31)", "first",
     '      - "a step written\n      as a quoted string"\n', ((1, "a quoted scalar continued past its line"),), True),
    ("a key or a scalar where a sequence entry goes", "first", "      - uses: ./a\n      name: stray\n",
     ((2, "a key or a scalar where a sequence entry goes"),), True),
    ("a key with a space before its colon (A08)", "first+env",
     "      - name: Spaced run key (pytest)\n        run : python -m pytest tests/test_a.py -q -p no:anyio\n",
     ((2, "a key with a space before its colon"),), False),
    ("a key with no space after its colon", "first+env", "      - name: Tight (pytest)\n        run:python -m pytest tests/test_a.py -q -p no:anyio\n",
     ((2, "a key with no space after its colon"),), True),
    ("a key spelled with a character ci.yml's keys do not use", "first", "      - uses: ./a\n        with:\n          a.b: c\n",
     ((3, "a key spelled with a character ci.yml's keys do not use (a.b)"),), True),
    ("a step holding env: twice, the second without the switch (AL-04)", "first",
     '      - name: Two envs (pytest)\n        env:\n          %s: "1"\n        env:\n          OTHER: x\n' % SWITCH + RUN_OK,
     ((4, "a key its mapping already holds (env)"),), True),
    # the two keys the parser reads as the text after the key (YAML_PLAIN_KEYS; the allowlist's second verify pass, W1,
    # W2b and W3: each valid YAML, read with its quotes or its comment, and red for another reason than a refusal)
    ("a step's name double-quoted (W1)", "first", '      - name: "Quoted name"\n        run: echo hi\n',
     ((1, YAML_PLAIN_KEY_WHAT % "name"),), True),
    ("a step's name single-quoted", "first", "      - name: 'Quoted name'\n        run: echo hi\n",
     ((1, YAML_PLAIN_KEY_WHAT % "name"),), True),
    ("a step's name with a trailing comment (W3)", "first", "      - name: Commented name # the step\n        run: echo hi\n",
     ((1, YAML_PLAIN_KEY_WHAT % "name"),), True),
    ("a step's working-directory double-quoted (W2b)", "first",
     '      - name: Quoted dir\n        working-directory: "${{ github.workspace }}"\n        run: echo hi\n',
     ((2, YAML_PLAIN_KEY_WHAT % "working-directory"),), True),
    ("a step's working-directory with a trailing comment", "first",
     "      - name: Commented dir\n        working-directory: vscode-extension # the extension\n        run: echo hi\n",
     ((2, YAML_PLAIN_KEY_WHAT % "working-directory"),), True),
    ("a job's default working-directory single-quoted", "job",
     "  wd:\n    runs-on: ubuntu-latest\n    defaults:\n      run:\n        working-directory: 'sub'\n    steps:\n      - run: echo hi\n",
     ((5, YAML_PLAIN_KEY_WHAT % "working-directory"),), True),
    # characters
    ("a tab after the switch key's colon (AL-18)", "last", '      - name: Tab (pytest)\n        env:\n          %s:\t"1"\n' % SWITCH + RUN_OK,
     ((3, "a tab or other control character ('\\t')"),), True),
    ("the switch's value 1 then a no-break space, which str.strip drops and YAML keeps (AL-02)", "last",
     "      - name: Nbsp value (pytest)\n        env:\n          %s: 1\xa0\n" % SWITCH + RUN_OK,
     ((3, "a character outside ASCII outside a comment line ('\\xa0')"),), True),
    # inside a literal block (the allowlist's first verify pass, M02: with the block's character refusal deleted every
    # test stayed green). A no-break space after the flag at the end of the line reads as the flag, str.strip dropping
    # it; bash hands pytest the character, and pytest 9.1.1 strips its -p argument and blocks the plugin (probed
    # 2026-09-24). A CR before the newline is part of YAML's line break. Neither is a form ci.yml uses, and each is
    # refused by name
    ("a no-break space after the flag at the end of a literal run block's line",
     "first+env", "      - name: Nbsp in block (pytest)\n        run: |\n          python -m pytest tests/test_a.py -q -p no:anyio\xa0\n",
     ((3, "a character outside ASCII outside a comment line ('\\xa0')"),), True),
    ("a CR after the flag at the end of a literal run block's line (YAML reads the CR and the newline as one line break)",
     "first+env", "      - name: CR in block (pytest)\n        run: |\n          python -m pytest tests/test_a.py -q -p no:anyio\r\n",
     ((3, "a tab or other control character ('\\r')"),), True),
    # a line break YAML 1.1 reads (NEL, LS, PS) in a comment line (the allowlist's second verify pass, N31: with the
    # three dropped from the refused set every test stayed green, and each plant below read ok). PyYAML ends the comment
    # at the character and reads the step env behind it, whose double-quoted key spells the switch through a \x52
    # escape and sets it to 0, while the scan, the parser and the censuses read one comment line; the job's env sets
    # the switch to 1. Whether GitHub's parser breaks the line there was not measured; each is refused by name
    ("NEL in a comment line, a step env setting the switch to 0 behind it (N31h)", "end", _HIDDEN_ENV % ("\x85", "\x85"),
     ((8, "a tab or other control character ('\\x85')"),), True),
    ("LS in a comment line, a step env setting the switch to 0 behind it (N31g)", "end", _HIDDEN_ENV % ("\u2028", "\u2028"),
     ((8, "a tab or other control character ('\\u2028')"),), True),
    ("PS in a comment line, a step env setting the switch to 0 behind it (N31i)", "end", _HIDDEN_ENV % ("\u2029", "\u2029"),
     ((8, "a tab or other control character ('\\u2029')"),), True),
    # the other refused characters no row held (the allowlist's second verify pass, N30, N33 and N36: with each dropped
    # from the refused set every test stayed green; PyYAML refuses each as an unacceptable character). U+001C, VT and
    # FF are line breaks to str.splitlines, so they take the shape above; DEL is not, and sits in a comment line alone
    ("U+001C in a comment line, a step env setting the switch to 0 behind it (N30)", "end", _HIDDEN_ENV % ("\x1c", "\x1c"),
     ((8, "a tab or other control character ('\\x1c')"),), True),
    ("VT in a comment line, a step env setting the switch to 0 behind it (N36)", "end", _HIDDEN_ENV % ("\x0b", "\x0b"),
     ((8, "a tab or other control character ('\\x0b')"),), True),
    ("FF in a comment line, a step env setting the switch to 0 behind it (N36)", "end", _HIDDEN_ENV % ("\x0c", "\x0c"),
     ((8, "a tab or other control character ('\\x0c')"),), True),
    ("DEL in a comment line after a step's run (N33)", "last", "      - name: Del comment\n        run: echo hi\n"
     "        # a comment holding DEL \x7f\n", ((3, "a tab or other control character ('\\x7f')"),), True),
    # the file's end (the allowlist's first verify pass, X10: a step env's switch key on a last line with no newline
    # after it was unread, and the file, which PyYAML and actionlint accept, was red for another reason than a refusal)
    ("a last line with no newline after it, a step env's switch key on it (X10)", "end",
     "  extra2:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Extra tests 2 (pytest)\n" + RUN_OK + '        env:\n          %s: "1"' % SWITCH,
     ((7, "a last line with no newline after it"),), False),
)
# accepted: each shape a form the real file uses, spliced as the first step of the shell job; the scan refuses none
YAML_ACCEPTED_ROWS = (
    ("operators and a glob in a plain run", "      - name: Plain\n        run: make a && ls tests/*.py 2>&1 | tee log\n"),
    ("a literal block's lines opening with *), &>, -, [, a key and an anchor, --- and ?",
     "      - name: Block\n        run: |\n          case $x in\n            *) echo other ;;\n          esac\n          &>/dev/null true\n"
     "          - item\n          [ -n x ]\n          key: &x\n          ---\n          ? q\n"),
    # (a quoted name, this row's first key until the allowlist's second verify pass, is refused now: YAML_PLAIN_KEYS)
    ("quoted scalars holding *, & and #", '      - name: Quoted\n        env:\n          NOTE: "* & # *"\n        run: echo \'&x *y #z\'\n'),
    ("a flow sequence of plain, single-quoted and double-quoted scalars", "      - uses: ./a\n        with:\n          list: ['3.10', \"3.13\", main]\n"),
    ("trailing comments after a key with no value, a plain value, a quoted value and a flow sequence",
     "      - uses: ./a  # c\n        with:   # c\n          a: x # c\n          b: 'y' # c\n          c: [z] # c\n"),
    ("comment lines at any indent, holding &, *, <<: and a character outside ASCII (the file's comments hold one)",
     "# top &x *y <<: z\n      # step \xe9 note\n      - name: Commented\n          # deeper\n        run: echo a#b\n"),
    ("an expression holding quotes, brackets and ==", "      - name: Expr\n        if: ${{ github.event_name == 'push' && '[a]' != 'b' }}\n        run: echo ok\n"),
    ("a literal run block with a blank line inside and a trailing comment on its header",
     "      - name: Block ok\n        run: |  # c\n          set -e\n\n          echo done\n"),
    # the allowlist's first verify pass's M33 dropped the pending key at a blank line and refused this valid shape (the
    # safe side), with every test green
    ("a key, a blank line, then its nested block", "      - uses: ./a\n        with:\n\n          a: x\n"),
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
                # a form the parser reads is covered by the line census and accepted by the scan: no false red on any
                self.assertEqual(pytest_line_census(src)[1], [], "%s: the line census reds a form the parser reads" % label)
                self.assertEqual(yaml_line_forms(src)[1], [], "%s: the scan refuses a form the parser reads" % label)

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
        for value in ('"1"', "'1'", "1", "1   # a trailing comment", '"1"   # a trailing comment'):
            with self.subTest(value=value):
                src, first = self._with_step_in_shell_job('      - name: Quoted switch (pytest)\n        env:\n          %s: %s\n'
                                                          '        run: python -m pytest tests/test_a.py -q -p no:anyio\n' % (SWITCH, value))
                self.assertEqual([verdict(i) for i in self._new(src)], ["ok"], "the control: %s reads 1" % value)
        # a plain value runs to YAML's comment, a `#` after a space: `1#x` is the string 1#x, which is not 1. Until the
        # allowlist build (2026-09-24) the env reader stopped at any `#`, and this step read ok while pytest ran with
        # the switch at 1#x (this build's AL-01; a form the scan accepts, so this reader is the one check that sees it)
        src, first = self._with_step_in_shell_job('      - name: Hash value (pytest)\n        env:\n          %s: 1#x\n'
                                                  '        run: python -m pytest tests/test_a.py -q -p no:anyio\n' % SWITCH)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1#x", "unlisted")])
        self.assertEqual(yaml_line_forms(src)[1], [], "a plain scalar holding # is a form the scan accepts")

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

    def test_a_pytest_step_whose_run_text_holds_an_expression_is_unparsed(self):
        # the allowlist's second verify pass (S08, S09, S10, 2026-09-24): GitHub substitutes a `${{ }}` expression into
        # the run text before the shell reads it, and the parser reads the text as written. `${{ '#' }}` before the flag
        # on either of the file's pytest lines, or a matrix value '#' there, read ok (or listed, on the served step)
        # while pytest got no flag (the pass's substitution by string replacement, then bash with a python shim that
        # printed its argv). A pytest command in a step whose run text holds `${{`, wherever it sits, is unparsed now;
        # neither of the file's pytest steps holds one, and each case is in the forms the scan accepts
        expr = "${{ '#' }}"
        run_line = [l for l in self.src.splitlines() if l.startswith("        run: python -m pytest -q -p no:anyio ")]
        served_line = [l for l in self.src.splitlines() if l.startswith("          python -m pytest tests/test_*_browser.py")]
        self.assertEqual((len(run_line), len(served_line)), (1, 1), "the two pytest lines moved: re-anchor this case")
        s08 = self.src.replace(run_line[0], run_line[0].replace(" -q -p no:anyio ", " -q %s -p no:anyio " % expr), 1)
        s09 = self.src.replace(served_line[0], served_line[0].replace(" -p no:anyio ", " %s -p no:anyio " % expr), 1)
        s10 = self._with_job_before_shell(
            "  mx:\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n        x: ['#']\n"
            '    env:\n      %s: "1"\n    steps:\n      - name: Matrix hash (pytest)\n' % SWITCH +
            "        run: python -m pytest -q ${{ matrix.x }} -p no:anyio tests/test_a.py\n")[0]
        earlier = self._with_shell_job_env(self._with_step_in_shell_job(
            "      - name: Expression on an earlier line (pytest)\n        run: |\n          ${{ matrix.setup }}\n"
            "          python -m pytest tests/test_a.py -q -p no:anyio\n")[0])
        # round 5's tests-2 (2026-09-24): the expression on a comment line before a flagged pytest command. A value
        # holding a newline ends the comment there and makes what follows it a command; with the scan kept to the lines
        # that are not comments this read ok and the module stayed green (the refuter's mutant, 89 passed)
        on_comment = self._with_shell_job_env(self._with_step_in_shell_job(
            "      - name: Expression on a comment line (pytest)\n        run: |\n          # ${{ matrix.note }}\n"
            "          python -m pytest tests/test_a.py -q -p no:anyio\n")[0])
        for label, src, key in (("the Run pytest line, an expression before the flag (S08)", s08, MATRIX_STEP),
                                ("the served step's pytest line, an expression before the flag (S09)", s09, SERVED_STEP),
                                ("a matrix value '#' before the flag (S10)", s10, ("mx", "Matrix hash (pytest)")),
                                ("an expression on an earlier line of the run text", earlier,
                                 ("shell", "Expression on an earlier line (pytest)")),
                                ("an expression on a comment line", on_comment, ("shell", "Expression on a comment line (pytest)"))):
            with self.subTest(form=label):
                self.assertNotEqual(src, self.src, "%s: the splice changed nothing: re-anchor this case" % label)
                inv = [i for i in pytest_invocations(src) if (i["job"], i["step"]) == key]
                self.assertEqual([verdict(i) for i in inv], ["unparsed"], "%s: %r" % (label, [_describe(i) for i in inv]))
                self.assertIn("run text holds a ${{ }} expression, which GitHub substitutes before the shell reads the text",
                              _describe(inv[0]))
                self.assertIn("python -m pytest", src.splitlines()[inv[0]["line"] - 1], _describe(inv[0]))
                self.assertEqual(yaml_line_forms(src)[1], [], "%s: in the forms the scan accepts" % label)
        # the control: the value in an env: key, read in the run text as a shell variable, is not re-read by the shell as
        # text, and the step reads ok
        via_env, first = self._with_step_in_shell_job('      - name: Expression through env (pytest)\n        env:\n          '
                                                      '%s: "1"\n          EXTRA: ${{ matrix.extra }}\n' % SWITCH +
                                                      '        run: python -m pytest tests/test_a.py -q -p no:anyio $EXTRA\n')
        self.assertEqual([verdict(i) for i in self._new(via_env)], ["ok"])
        # the stated residual, held by execution: a shell function the run text defines rewrites the flag's word before
        # pytest gets it (S07; bash hands pytest no:cacheprovider in its place), and the step reads ok, since anything
        # that rewrites a pytest command's arguments after the run text is read is outside the read
        rewrite, first = self._with_step_in_shell_job(
            '      - name: Rewritten by a function (pytest)\n        env:\n          %s: "1"\n        run: |\n' % SWITCH +
            '          python() { local a=() x; for x in "$@"; do [ "$x" = no:anyio ] && x=no:cacheprovider; a+=("$x"); '
            'done; command python "${a[@]}"; }\n          python -m pytest tests/test_a.py -q -p no:anyio\n')
        self.assertEqual([verdict(i) for i in self._new(rewrite)], ["ok"])

    def test_a_step_whose_pytest_spelling_sits_in_a_comment_after_an_expression_is_unparsed_at_its_line(self):
        # round 5's ruling A (tests-1, 2026-09-24): the expression refusal read only the rows the parser built, and a step
        # whose only pytest spelling sits in a shell comment gave none (a comment line is skipped, a trailing comment cut
        # by the shell split and by the line census). GitHub substitutes the expression first, so a value holding a
        # newline ends the comment and bash runs the rest: pytest with neither the flag nor the switch (both refuters:
        # no row, no census line, 89 passed; the substituted text run under bash ran pytest). Each route now gives an
        # unparsed row at its line, and the red comes from that row: the scan accepts each form, and the line census has
        # nothing to name
        nl = "${{ fromJSON('\"\\n\"') }}"          # the YAML text fromJSON('"\n"'): a JSON string holding a newline
        routes = (("a comment line, fromJSON", "          echo start\n          # %spython -m pytest tests/test_a.py -q\n" % nl, 3),
                  ("a comment line, a variable", "          echo start\n          # ${{ vars.NL }}python -m pytest tests/test_a.py -q\n", 3),
                  ("a trailing comment", "          echo start  # %spython -m pytest tests/test_a.py -q\n" % nl, 2))
        for label, block, offset in routes:
            with self.subTest(route=label):
                src, first = self._with_step_in_shell_job("      - name: Comment after an expression\n        run: |\n" + block)
                self.assertIn("${{", src.splitlines()[first + offset - 1], label)
                new = self._new(src)
                self.assertEqual([(i["step"], i["line"], verdict(i)) for i in new],
                                 [("Comment after an expression", first + offset, "unparsed")], [_describe(i) for i in new])
                self.assertIn("run text holds a ${{ }} expression, which GitHub substitutes before the shell reads the text",
                              _describe(new[0]))
                self.assertIn("ci.yml line %d" % (first + offset), _describe(new[0]))
                self.assertEqual(yaml_line_forms(src)[1], [], "%s: in the forms the scan accepts" % label)
                self.assertEqual(pytest_line_census(src)[1], [], "%s: the red is the row's, not the line census's" % label)
        # the single-quoted one-line route: the quote-aware census counted its line before the ruling; now the row covers it
        quoted, first = self._with_step_in_shell_job("      - name: Quoted comment after an expression\n"
                                                     "        run: 'echo start # ${{ vars.NL }}python -m pytest tests/test_a.py -q'\n")
        self.assertEqual([(i["line"], verdict(i)) for i in self._new(quoted)], [(first + 1, "unparsed")])
        # outside the population, correctly: after a plain one-line run the expression sits in a YAML comment, which YAML
        # drops before GitHub substitutes anything, so the run text is `echo start` and nothing spells pytest in it
        plain, first = self._with_step_in_shell_job("      - name: YAML comment after a plain run\n"
                                                    "        run: echo start # ${{ vars.NL }}python -m pytest tests/test_a.py -q\n")
        self.assertEqual((self._new(plain), pytest_line_census(plain)[1], yaml_line_forms(plain)[1]), ([], [], []))
        # the control: a pytest spelling in a comment with no expression in the run text never runs, and gives no row
        quiet, first = self._with_step_in_shell_job("      - name: Comment alone\n        run: |\n          echo start\n"
                                                    "          # python -m pytest tests/test_a.py -q\n")
        self.assertEqual((self._new(quiet), pytest_line_census(quiet)[1]), ([], []))

    def test_what_can_discard_pytests_failure_on_the_run_pytest_step_is_refused_at_its_line(self):
        # round 5's ruling C (2026-09-24): each plant below, spliced into the live file, left the module green at the
        # ruling's head (the refuter's mutants and the ruling's two more, BASH_ENV on the step and an earlier step's
        # write of PYTEST_ADDOPTS to $GITHUB_ENV, under which a failing pytest exits 0 or never runs the suite), and each
        # is refused at its line by run_pytest_status. The population check reads each as before: it holds the flag
        # and the switch, not the exit status, so the refusal is this check's alone
        run = "        run: python -m pytest -q -p no:anyio --durations=10 --timeout=600 --timeout-method=thread\n"
        name, switch = "      - name: Run pytest\n", '          %s: "1"\n' % SWITCH
        job = "  python:\n    name: Python ${{ matrix.python-version }} (${{ matrix.os }})\n"

        def splice(old, new, k=0):
            # `old` replaced by `new` in the live text; the file line of `new`'s k-th line
            self.assertEqual(self.src.count(old), 1, "%r moved: re-anchor this case" % old)
            at = self.src.index(old)
            out = self.src[:at] + new + self.src[at + len(old):]
            return out, _line_of(out, at) + k

        plants = (
            ("an if: on the step", splice(name, name + "        if: false\n", 1), "an if: can skip it"),
            ("a continue-on-error on the step", splice(name, name + "        continue-on-error: true\n", 1), "continue-on-error"),
            ("an if: on the job", splice(job, job + "    if: false\n", 2), "an if: can skip it"),
            ("a continue-on-error on the job", splice(job, job + "    continue-on-error: true\n", 2), "continue-on-error"),
            ("|| true", splice(run, run[:-1] + " || true\n"), "more than its one shell command"),
            ("| tee log.txt", splice(run, run[:-1] + " | tee log.txt\n"), "more than its one shell command"),
            ("a trailing &", splice(run, run[:-1] + " &\n"), "more than its one shell command"),
            ("; exit 0", splice(run, run[:-1] + "; exit 0\n"), "more than its one shell command"),
            ("a literal block with a trap first", splice(run, "        run: |\n          trap 'exit 0' EXIT\n          "
                                                             + run[len("        run: "):], 1), "a second command line"),
            ("--collect-only", splice(run, run[:-1] + " --collect-only\n"), "the argument '--collect-only'"),
            ("--co", splice(run, run[:-1] + " --co\n"), "the argument '--co'"),
            ("--setup-plan", splice(run, run[:-1] + " --setup-plan\n"), "the argument '--setup-plan'"),
            ("a path that narrows the run", splice(run, run[:-1] + " tests/test_ci_sdk_pin.py\n"), "the argument 'tests/test_ci_sdk_pin.py'"),
            ("a shell: on the step", splice(name, name + "        shell: bash\n", 1), "a shell: sets the shell"),
            ("a defaults: on the job", splice(job, job + "    defaults:\n      run:\n        shell: bash\n", 2), "a defaults: can set"),
            ("a defaults: at the top level", splice("\njobs:\n", "\ndefaults:\n  run:\n    shell: bash\n\njobs:\n", 1),
             "a defaults: at the top level"),
            ("PYTEST_ADDOPTS in the step's env", splice(switch, switch + '          PYTEST_ADDOPTS: "--co"\n', 1),
             "the env key PYTEST_ADDOPTS"),
            ("BASH_ENV in the step's env", splice(switch, switch + "          BASH_ENV: pre.sh\n", 1), "the env key BASH_ENV"),
            ("PYTEST_ADDOPTS in the workflow's env", splice("\njobs:\n", '\nenv:\n  PYTEST_ADDOPTS: "--co"\n\njobs:\n', 2),
             "the env key PYTEST_ADDOPTS"),
            ("PYTEST_ADDOPTS as a prefix on the command", splice(run, "        run: PYTEST_ADDOPTS=--co " + run[len("        run: "):]),
             "the env key PYTEST_ADDOPTS, a prefix"),
            ("an earlier step's write of PYTEST_ADDOPTS to $GITHUB_ENV",
             splice(name, '      - name: Set options\n        run: echo PYTEST_ADDOPTS=--co >> "$GITHUB_ENV"\n' + name, 1),
             "spells GITHUB_ENV"),
            ("an earlier step's write to $GITHUB_PATH",
             splice(name, '      - name: Put a tool first\n        run: echo "$HOME/fake" >> "$GITHUB_PATH"\n' + name, 1),
             "spells GITHUB_PATH"),
        )
        for label, (src, line), why in plants:
            with self.subTest(plant=label):
                read, refused = run_pytest_status(src)
                self.assertEqual([r[0] for r in refused], [line], "%s: %r" % (label, refused))
                self.assertEqual(read, [i["line"] for i in pytest_invocations(src) if (i["job"], i["step"]) == MATRIX_STEP], label)
                self.assertIn(why, refused[0][2], label)
                self.assertEqual(refused[0][1], src.splitlines()[line - 1].strip(), label)
                self.assertEqual([verdict(i) for i in pytest_invocations(src) if (i["job"], i["step"]) == MATRIX_STEP], ["ok"], label)
                self.assertEqual(yaml_line_forms(src)[1], [], "%s: in the forms the scan accepts" % label)
        # the live file is read and refuses nothing
        self.assertEqual(run_pytest_status(self.src)[1], [])

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
        # a plain value continued on the next line (YAML folds it to `1 0`) was named here until the allowlist
        # (2026-09-24); the scan refuses the continued line now, and its row is in YAML_REFUSED_ROWS
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
        # `-pno:anyio` is the same flag to pytest; this check keys on the two words -p and no:anyio and its message says
        # so
        src, first = self._with_step_in_shell_job('      - name: Nospace (pytest)\n        env:\n          %s: "1"\n        run: python -m pytest tests/ -q -pno:anyio\n' % SWITCH)
        bad = self._new_bad(src)
        self.assertEqual([verdict(i) for i in bad], ["unlisted"])
        self.assertIn("lacks -p no:anyio (keyed on the words -p and no:anyio in the command's arguments as the shell splits "
                      "them)", _describe(bad[0]))

    def test_the_flag_spelled_inside_a_quoted_argument_is_that_arguments_text(self):
        # the pre-push closer's C01 (silent until the allowlist build, 2026-09-24): `-k 'x -p no:anyio y'` hands pytest
        # the flag's spelling as -k's value, and pytest runs with anyio's plugin, while the regex the flag half keyed on
        # read the spelling after a space inside the quotes and the step read ok. The words are split as the shell
        # splits them (passes_flag), on one line and over a backslash continuation inside the quote, where the shell
        # keeps the backslash and the newline as the argument's text
        env = '        env:\n          %s: "1"\n' % SWITCH
        for label, run, args in (
                ("single quotes on one line", "        run: python -m pytest tests/test_a.py -q -k 'x -p no:anyio y'\n",
                 "tests/test_a.py -q -k 'x -p no:anyio y'"),
                ("double quotes on one line", '        run: python -m pytest tests/test_a.py -q -k "x -p no:anyio"\n',
                 'tests/test_a.py -q -k "x -p no:anyio"'),
                ("single quotes over a continuation (C01)", "        run: |\n          python -m pytest tests/test_a.py -q -k 'x \\\n"
                 "          -p no:anyio y'\n", "tests/test_a.py -q -k 'x -p no:anyio y'")):
            with self.subTest(form=label):
                src, first = self._with_step_in_shell_job("      - name: Quoted flag (pytest)\n" + env + run)
                new = self._new(src)
                self.assertEqual([(verdict(i), i["args"].strip()) for i in new], [("unlisted", args)], [_describe(i) for i in new])
                self.assertIn("lacks -p no:anyio", _describe(new[0]))
        # the controls: the two words outside every quote, after a quoted argument, read as the flag, and a quote left
        # open reads as no flag
        self.assertTrue(passes_flag("tests/ -q -k 'x y' -p no:anyio"))
        self.assertTrue(passes_flag('tests/ -p  no:anyio -k "a b"'))
        self.assertFalse(passes_flag("tests/ -q -k 'x -p no:anyio"))

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
        # a plain run is cut at YAML's comment, a `#` after a space, inside shell quotes too: YAML's value here ends at
        # `-k "a`, and the flag after it never reaches the shell. Until the allowlist build (2026-09-24) the cut was the
        # shell split's, which keeps a quoted `#`, and the step read ok (this build's AL-12)
        src, first = self._with_step_in_shell_job('      - name: Quoted hash (pytest)\n        run: python -m pytest tests/test_a.py -q -k "a #b" -p no:anyio\n')
        self.assertEqual([(verdict(i), i["args"].strip()) for i in self._new(self._with_shell_job_env(src))], [("unlisted", 'tests/test_a.py -q -k "a')])

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
        # the parser's limits fail loud: each form it does not read is red until it is read (or moved to a comment). An
        # indentation indicator and a more-indented line in a folded block were unparsed here until the allowlist
        # (2026-09-24); both are YAML forms the scan refuses now (YAML_REFUSED_ROWS)
        for label, step, reason in (
                ("a wrapper", "      - name: Wrapped (pytest)\n        run: uvx --with pytest pytest tests/ -q -p no:anyio\n",
                 "a form the parser does not read as a command"),
                ("a variable", "      - name: Variable (pytest)\n        run: $PYTEST tests/ -q -p no:anyio\n",
                 "a form the parser does not read as a command"),
                # a pip install is keyed on the command's program: until 2026-09-23 the words pip and install in a
                # pytest command's arguments excused it as one
                ("a wrapper whose arguments spell pip and install", '      - name: Pip words (pytest)\n        run: uvx pytest tests/ -q -k "pip and install"\n',
                 "a form the parser does not read as a command")):
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

    def test_a_job_key_after_the_steps_is_not_read_as_the_last_steps_own(self):
        # the allowlist's first verify pass (2026-09-24; its S01, S02, S06, S03 and X09): the last step's text ran to
        # the end of the job, so a job key after the steps whose nested keys sit at the step keys' indent was read as
        # that step's own. services.<id>.env set the switch for the parser, while GitHub Actions hands a service's env
        # to the service container alone and pytest ran without it; the module was silent and the scan refused nothing.
        # A step's text now ends at the end of the steps sequence: the first line after its dash, other than a blank or
        # comment line, indented 4 or less. The step reads unlisted at its pytest line, and the switch census names the
        # service's switch line, a spelling of the switch where the merge does not look
        services = '    services:\n      cache:\n        image: redis:7\n        env:\n          %s: "1"\n' % SWITCH
        pytest_line = "python -m pytest -q -p no:anyio tests/test_a.py"
        for label, steps in (
                ("a named step after another", "      - uses: actions/checkout@v4\n      - name: Extra tests\n        run: %s\n" % pytest_line),
                ("a literal block run", "      - name: Extra tests\n        run: |\n          %s\n" % pytest_line),
                ("an unnamed step opening with run:", "      - run: %s\n" % pytest_line)):
            with self.subTest(form=label):
                job = "  extra:\n    runs-on: ubuntu-latest\n    steps:\n" + steps + services
                src, first = self._with_job_before_shell(job)
                rows = job.splitlines()
                at = first + next(k for k, l in enumerate(rows) if l.endswith(pytest_line))
                sw_at = first + rows.index('          %s: "1"' % SWITCH)
                new = self._new(src)
                self.assertEqual([(i["line"], i["env"].get(SWITCH), verdict(i)) for i in new], [(at, None, "unlisted")],
                                 "%s: the service's env is not the step's: %r" % (label, [_describe(i) for i in new]))
                self.assertEqual(switch_line_census(src)[1], [(sw_at, '%s: "1"' % SWITCH)], label)
                self.assertEqual(yaml_line_forms(src)[1], [], "%s: every line is in an accepted form; the reader is the check" % label)
        # the Run pytest step's own env moved under a services: key after the python job's steps (S03)
        lines = self.src.split("\n")
        i_env = lines.index("        env:", lines.index("      - name: Run pytest"))
        i_gil = next(k for k in range(i_env, len(lines)) if lines[k].startswith("          PYTHON_GIL: "))
        i_run = next(k for k in range(i_gil, len(lines)) if lines[k].startswith("        run: python -m pytest"))
        moved = (lines[:i_env] + lines[i_gil + 1:i_run + 1] + ["    services:", "      cache:", "        image: redis:7", "        env:"]
                 + lines[i_env + 1:i_gil + 1] + lines[i_run + 1:])
        src = "\n".join(moved)
        rows = [(i["line"], i["env"].get(SWITCH), verdict(i)) for i in pytest_invocations(src) if (i["job"], i["step"]) == MATRIX_STEP]
        self.assertEqual(rows, [(i_env + i_run - i_gil, None, "unlisted")], "the Run pytest step's env moved under services:")
        self.assertEqual([t for _n, t in switch_line_census(src)[1]], ['%s: "1"' % SWITCH])
        self.assertEqual(yaml_line_forms(src)[1], [])
        # a key name: under strategy.matrix after the steps is not the unnamed last step's name (X09)
        src, first = self._with_job_before_shell("  extra:\n    runs-on: ubuntu-latest\n    steps:\n      - run: %s\n"
                                                 "    strategy:\n      matrix:\n        name: [a]\n" % pytest_line)
        self.assertEqual([(i["line"], i["step"], verdict(i)) for i in self._new(src)], [(first + 3, UNNAMED, "unlisted")])

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
        # it reds this compliant step at its continuation lines (round 4's tests-1 refuters, probed; the folded
        # paragraph and the plain scalar continued are forms the scan refuses since the allowlist, 2026-09-24)
        env = '        env:\n          %s: "1"\n' % SWITCH
        for label, run, offset in (
                ("backslash continuations", "        run: |\n          python -m \\\n            pytest tests/test_a.py -q -p no:anyio \\\n"
                                            "            --junitxml=pytest-report.xml\n", 4),):
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
        # verify, 2026-09-23): the line's key is name, the parser gives the step no row, and a pytest with neither the
        # switch nor the flag was silent until the census read the rest of the line for a key. The scan refuses the
        # flow mapping at its opening line since the allowlist (2026-09-24), and the census excuses the name line again
        # (NAME_KEY_RE alone), so the refusal is this step's one red
        for label, text in (("the run after a comma", "      - {\n          name: FlowMulti, run: python -m pytest tests/test_k.py\n        }\n"),
                            ("the run after the name's quoted value", '      - {\n          name: "Flow, quoted", run: python -m pytest tests/test_k.py\n        }\n'),
                            ("the run after a comma with no space", "      - {\n          name: FlowMulti,run: python -m pytest tests/test_k.py\n        }\n")):
            with self.subTest(form=label):
                src, first = self._with_first_step_in_shell_job(text)
                self.assertEqual(yaml_line_forms(src)[1], [(first, "- {", "a flow mapping")], label)
                self.assertEqual((self._new_bad(src), pytest_line_census(src)[1]), ([], []), label)
        # the exclusion is the name key's own line and no other: a name folded onto a second line that spells pytest
        # reds there, beside the scan's refusal of the folded block (the pre-push lenses' N07 and B46)
        src, first = self._with_first_step_in_shell_job("      - name: >-\n          Smoke pytest\n          on Linux\n        run: echo hi\n")
        self.assertEqual(pytest_line_census(src)[1], [(first + 1, "Smoke pytest")])
        self.assertEqual(yaml_line_forms(src)[1], [(first, "- name: >-", "a folded block scalar (ci.yml's blocks are literal)")])
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

    def test_a_key_shaped_line_deeper_than_an_env_blocks_keys_is_not_read_and_is_named(self):
        # the owner's fail-closed design (2026-09-23; the pre-push lenses' S10, S11 and S12): _env_block read a key at
        # any depth, so `ROMP_SDK_REQUIRE: "1"` written as a line of another key's `|` or `>` block read as the switch
        # on and the switch census counted it a key line, while YAML held it as that key's text and pytest ran without
        # the switch. A key is read at the block's first key indent only, and a deeper line is never a key here: the
        # step reads unlisted and the switch census names the line. The block scalar itself is refused by the scan
        # (a literal block outside a step's run, a folded block); until the allowlist (2026-09-24) _env_block read such
        # a value's key as not clean, and the census named a switch key whose own value was a block scalar or ran on
        run = "        run: python -m pytest tests/test_a.py -q -p no:anyio\n"
        for label, indicator, what in (("a literal block", "|", "a literal block scalar outside a step's run"),
                                       ("a folded block", ">", "a folded block scalar (ci.yml's blocks are literal)"),
                                       ("a literal block, strip chomping", "|-", "a block scalar header with a chomping or "
                                        "indentation indicator, or text after it")):
            with self.subTest(form=label, scope="step"):
                src, first = self._with_step_in_shell_job("      - name: Block text (pytest)\n        env:\n          NOTES: %s\n"
                                                          '            %s: "1"\n' % (indicator, SWITCH) + run)
                new = self._new(src)
                self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [(None, "unlisted")], [_describe(i) for i in new])
                self.assertEqual(switch_line_census(src)[1], [(first + 3, '%s: "1"' % SWITCH)], label)
                self.assertEqual(yaml_line_forms(src)[1], [(first + 2, "NOTES: %s" % indicator, what)], label)
        with self.subTest(scope="job"):
            src = self.src.replace("\n  shell:\n    name: Shell", '\n  shell:\n    env:\n      NOTES: |\n        %s: "1"\n    name: Shell' % SWITCH, 1)
            self.assertNotEqual(src, self.src, "the shell job's header moved: re-anchor this case")
            src, first = self._with_step_in_shell_job("      - name: Job block text (pytest)\n" + run, src)
            new = self._new(src)
            self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in new], [(None, "unlisted")], [_describe(i) for i in new])
            at = [n + 1 for n, l in enumerate(src.splitlines()) if l == '        %s: "1"' % SWITCH]
            self.assertEqual(switch_line_census(src)[1], [(at[0], '%s: "1"' % SWITCH)])
        # a mapping nested under an env key (valid YAML the scan accepts, an env value the runner refuses): the deeper
        # switch line is that key's value, not read, and named (this build's AL-10)
        src, first = self._with_step_in_shell_job('      - name: Nested env (pytest)\n        env:\n          NOTES:\n            %s: "1"\n' % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [(None, "unlisted")])
        self.assertEqual(switch_line_census(src)[1], [(first + 3, '%s: "1"' % SWITCH)])
        self.assertEqual(yaml_line_forms(src)[1], [])
        # the switch's own value as a block scalar (`|-` then 1 is "1" to YAML) reads as its indicator, never 1, and the
        # scan refuses it; the census counts the key line as read (the E35 case, an empty `>-` in a job with no pytest
        # step, is a scan refusal too, YAML_REFUSED_ROWS)
        src, first = self._with_step_in_shell_job("      - name: Block switch (pytest)\n        env:\n          %s: |-\n            1\n" % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("|-", "unlisted")])
        self.assertEqual(switch_line_census(src)[1], [])
        self.assertEqual([n - first for n, _t, _w in yaml_line_forms(src)[1]], [2])
        # the controls: a real switch key at the block's key indent after another key and its nested lines reads, and a
        # line deeper than the keys that spells the switch is named at its own line
        src, first = self._with_step_in_shell_job("      - name: After a nested key (pytest)\n        env:\n          NOTES:\n"
                                                  "            OTHER: x\n          %s: \"1\"\n" % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")])
        self.assertEqual((switch_line_census(src)[1], yaml_line_forms(src)[1]), ([], []))
        src, first = self._with_step_in_shell_job("      - name: Switch under a nested key (pytest)\n        env:\n          %s: \"1\"\n"
                                                  '          NOTES:\n            %s: "0"\n' % (SWITCH, SWITCH) + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")])
        self.assertEqual(switch_line_census(src)[1], [(first + 4, '%s: "0"' % SWITCH)])
        # a comment line indented no further than `env:` sits inside the block to YAML, which skips comment lines
        # wherever they are: the switch after it is read, and nothing is named (until the allowlist build, 2026-09-24,
        # such a line ended the block here, and the switch after it read unset; found by mutating the real file)
        src, first = self._with_step_in_shell_job("      - name: Comment in env (pytest)\n        env:\n          OTHER: x\n"
                                                  "# a comment at column 0\n      # and one at the steps' indent\n"
                                                  "          %s: \"1\"\n" % SWITCH + run)
        self.assertEqual([(i["env"].get(SWITCH), verdict(i)) for i in self._new(src)], [("1", "ok")])
        self.assertEqual((switch_line_census(src)[1], yaml_line_forms(src)[1]), ([], []))

    def _splice(self, where, text):
        # a row's text at its place in a copy of the live file (YAML_REFUSED_ROWS' `where`): (src, the text's first
        # line)
        src = self._with_shell_job_env(self.src) if where.endswith("+env") else self.src
        where = where.replace("+env", "")
        if where == "first":
            return self._with_first_step_in_shell_job(text, src)
        if where == "last":
            return self._with_step_in_shell_job(text, src)
        if where == "job":
            return self._with_job_before_shell(text, src)
        if where == "start":
            return text + src, 1
        head = src.rstrip("\n") + "\n"
        return head + text, len(head.splitlines()) + 1

    def test_every_form_outside_the_allowlist_is_refused_by_name_at_its_line(self):
        # the owner's allowlist design (2026-09-24): the scan accepts the forms the real file uses and refuses every
        # other line by name. Until then it refused named forms one at a time, and the pre-push lenses and three verify
        # passes planted a pytest run without the switch or the flag behind forms the line reading half-modelled; each
        # row is one of those plants or a form of its own, refused at exactly the lines it names. A row marked alone is
        # red for nothing else here (no population verdict, no census line, no job key), so the refusal is what reds it.
        # After a refused line the lines indented past it are its own and not scanned, so a construct is named once.
        # The lines are the file's, split at its newlines as the scan splits them: str.splitlines also breaks at NEL,
        # LS, PS, VT, FF and U+001C to U+001E, which some rows plant inside a comment line
        for label, where, text, named, alone in YAML_REFUSED_ROWS:
            with self.subTest(form=label):
                src, first = self._splice(where, text)
                want = [(first + k - 1, src.split("\n")[first + k - 2].strip(), what) for k, what in named]
                self.assertEqual(yaml_line_forms(src)[1], want, label)
                if alone:
                    self.assertEqual((self._new_bad(src), pytest_line_census(src)[1], switch_line_census(src)[1], unread_job_keys(src)[1]),
                                     ([], [], [], []), "%s: the refusal is the one red" % label)

    def test_every_form_the_real_file_uses_is_accepted_in_a_step(self):
        # the controls: shapes in the forms the real file uses, the file's own among them (`&&`, `2>&1` and a glob in a
        # run, a literal block's lines that open with YAML indicators, quoted scalars holding them, a flow sequence of
        # scalars, trailing comments, a comment line holding a character outside ASCII); the scan refuses none, and
        # after a literal block the scan reads the next step's keys again
        for label, text in YAML_ACCEPTED_ROWS:
            with self.subTest(form=label):
                self.assertEqual(yaml_line_forms(self._with_first_step_in_shell_job(text)[0])[1], [], label)
        src, first = self._with_first_step_in_shell_job("      - name: Block\n        run: |\n          echo b\n        env: *e\n")
        self.assertEqual(yaml_line_forms(src)[1], [(first + 3, "env: *e", "an alias (*e)")])


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
INTERPRETER_OPTS_WITH_VALUE = ("-X", "-W")                         # CPython options whose value is the next element, or attached
# CPython's options that take no value, one letter each (python --help on 3.10 to 3.14, and -R, which CPython accepts and
# ignores): the letters _argv_command takes apart as options; any other option-shaped element is not taken apart
INTERPRETER_NO_VALUE_LETTERS = frozenset("bBdEhiIOPqRsSuvVx")
OPTION_SHAPED_RE = re.compile(r"-[A-Za-z]\S*|--[A-Za-z]\S*")       # a dash and a letter, or two dashes and a name, no whitespace
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
    as one and reports unparsed, (None, None) for an argv that is not a pytest command. The property, not a spelling;
    this docstring is the census's argv rule in full, and the other texts that state it give examples and point here.
    A launcher: `-m pytest` as two elements, or `-mpytest` as one, after an INTERPRETER HEAD through interpreter options
    only. The head is any element that is not a constant (sys.executable, a name, a call, a starred tail) or a
    python-named constant (`python`, `python3.12`, a path to one), wherever it sits, so `uv run python -m pytest` reads.
    Until 2026-09-21 the pair was read at indices 1 and 2 alone, and `python -B -m pytest`, the repo's own recipe, was
    outside the census with no red. Also a launcher: `-m pytest` as the first two elements (the interpreter joins the
    argv elsewhere, an extend), and pytest or py.test by name or path as argv[0].
    The options between the head and the -m (round 5's ruling B, 2026-09-24): an option element is read only where the
    census takes it apart one option at a time: a single letter that takes no value (INTERPRETER_NO_VALUE_LETTERS, the
    letters CPython documents: -B, -u, -I and the rest), -X or -W with its value (the next element, or attached, as in
    `-Werror`), -m with its module (the next element, or attached, as in `-mpytest`), and -c, which ends the options. An
    element that starts with a dash and is not option-shaped (`-` or `--` alone, or an element holding whitespace, which
    is no option) is passed over, as every element starting with a dash was before the ruling.
    Unparsed, after such a head and its options: a `-m` whose next element is not a constant (a module name the census
    cannot read: it may be pytest); an element that is not a constant right before the constant `pytest` (an option the
    census cannot read: it may be -m); -m, attached or not, with a module in the pytest package other than pytest
    itself (`pytest.__main__`, any `pytest.<name>`), since pytest.__main__ runs pytest and the census reads only -m
    pytest; every other option-shaped element (a dash and a letter, or two dashes and a name, with no whitespace:
    OPTION_SHAPED_RE) that itself spells pytest (PYTEST_TEXT_RE) or comes before an element that spells pytest, named,
    until the options are spelled one per element: among them a cluster (`-Bm`, `-Impytest`, `-BW`), a long option
    (`--check-hash-based-pycs`) and a letter the census does not know; and such an element made of letters and ending
    in m (a cluster whose last option is -m) right before an element that is not a constant, as `-m` before one is.
    Until the ruling every element starting with a dash read as an option with no value, so `-Bm pytest`, `-Impytest`
    and `-BW error -m pytest` gave no row while each ran pytest. The refusal over-reads, on the safe side: a flagged
    `-Bm pytest ... -p no:anyio` is red until it is spelled `-B -m pytest` (as the population check reds `python
    -Impytest`), and so is a cluster followed by any element that spells pytest, a test path among them. The residual,
    pinned in OUTSIDE_THE_READ: an option element the census does not take apart, followed by no element that spells
    pytest and not a cluster ending in m right before an element that is not a constant, is passed over as an option
    with no value, so `-BW error -m <name>` gives no row where the name may be pytest.
    Not a pytest command: a word that is not an option after the head (a script, which takes any later `-m pytest` as its
    own arguments); another module after -m (`-m unittest`, `-m pip`); a -c, whose string element_command reads where the
    argv is written at a call; and `-m` under a head that is neither (`git commit -m msg`, with a constant or a variable
    for git). pytest by name after argv[0] under a head this rule does not read (a wrapper such as env, nice or timeout;
    a pip line) is not a command here either: element_command refuses it where the argv is written at a call the census
    reads, and such a literal built anywhere else gives no row (OUTSIDE_THE_READ holds one held in a variable)."""
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
            spaced = re.search(r"\s", tok) is not None
            if not spaced and tok[:2] == "-m":
                if tok == "-m":
                    if j + 1 < len(c) and c[j + 1] is None:
                        return None, ("a module name the census cannot read after -m, after the interpreter at argv[%d] (it "
                                      "may be pytest): not read as a launcher until the module is spelled as a constant" % i)
                    module = c[j + 1] if j + 1 < len(c) else None
                else:
                    module = tok[2:]
                if module == "pytest":
                    return ("<interpreter> -m pytest" if tok == "-m" else "<interpreter> -mpytest"), None
                if module is not None and module.startswith("pytest."):
                    return None, ("-m %s, a module in the pytest package, after the interpreter at argv[%d]: pytest.__main__ "
                                  "runs pytest, and the census reads only -m pytest, so it is not read as a launcher until "
                                  "spelled -m pytest" % (module, i))
                break
            if not spaced and tok[:2] == "-c":
                break
            if tok in INTERPRETER_OPTS_WITH_VALUE:
                j += 2
                continue
            if not spaced and tok[:2] in INTERPRETER_OPTS_WITH_VALUE:
                j += 1
                continue
            if len(tok) == 2 and tok[0] == "-" and tok[1] in INTERPRETER_NO_VALUE_LETTERS:
                j += 1
                continue
            if OPTION_SHAPED_RE.fullmatch(tok):
                later = next((t for t in c[j + 1:] if t is not None and PYTEST_TEXT_RE.search(t)), None)
                if PYTEST_TEXT_RE.search(tok) or later is not None:
                    return None, ("an option element %r after the interpreter at argv[%d] that the census does not take apart "
                                  "one option at a time (a cluster, a long option or a letter it does not know), %s: not "
                                  "read as a launcher until its options are spelled one per element"
                                  % (tok, i, "which itself spells pytest" if PYTEST_TEXT_RE.search(tok)
                                     else "before an element that spells pytest (%r)" % later))
                if re.fullmatch(r"-[A-Za-z]+m", tok) and j + 1 < len(c) and c[j + 1] is None:
                    return None, ("an option cluster %r ending in m after the interpreter at argv[%d], right before an element "
                                  "the census cannot read (the module may be pytest): not read as a launcher until the options "
                                  "are spelled one per element and the module as a constant" % (tok, i))
                j += 1
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
    Read: every list or tuple literal in the module whose command is pytest (_argv_command, whose docstring is the
    rule: among them `-m pytest` after an interpreter head through the options it takes apart, and pytest by name or
    path as argv[0]), wherever it is built: in the subprocess call, in a helper that passes it on, in a variable
    extended later, so a helper-built argv is counted.
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
    binds (a star import may have brought it) reads as itself. Unparsed, and red in ChildPytestLaunchers until spelled
    as an argv or rewritten: a call whose callee's name this resolution cannot resolve (the owner's fail-closed design,
    2026-09-23; unresolved): one inside a comprehension or generator expression, outside its first iterable, in a class
    body that binds the name or declares it global, where Python looks the name up past the class and the census does
    not model that scope; and, in a module with a star import from a module outside CENSUS_STAR_MODULES (or a relative
    one), whose names the census does not read, one through a name the lookup takes to the module: a name the module
    binds, which the star import may rebind, or a name no scope binds and no builtin names, which it may bring; and one
    through a name a function binds by a plain or annotated assignment from a name or an attribute whose root name is
    one of those, along a chain of such assignments (from_star). A star import binds at the module, so only a function
    scope on the lookup that binds the name, other than by such an assignment, is taken as proof that the call does not
    reach it; a class body's binding is not, since the body reads the name past the class until its own binding runs.
    Unparsed too: a list or tuple literal that may run pytest and
    the census cannot tell (among them, after an interpreter head, a -m whose module name is not a constant, an element
    that is not a constant right before `pytest`, a -m of a module in the pytest package, and an option element the
    census does not take apart before an element that spells pytest; _argv_command's docstring states the rule); a
    constant string or f-string, written at the
    call, handed to subprocess.run, Popen, call, check_call, check_output, getoutput or getstatusoutput, to os.system
    or os.popen, or to asyncio.create_subprocess_shell (FIRST_ARG_CALLS, by position or by the call's own keyword), or
    through shlex.split, whose text spells a pytest command or a `pytest.main(` call (PYTEST_IN_STRING_RE); an argv
    handed to those calls, or given as the positional arguments above, whose command _argv_command does not read but
    that carries pytest (element_command): a pytest command inside one element (any element when the head is a shell,
    SHELL_NAMES, run with -c, else a multi-word element, a `-c` string running pytest.main among them), or a constant
    element named pytest or py.test by basename after argv[0], a wrapper's (`env pytest`, `timeout 60 py.test`) and a
    pip line's alike, with no exemption (round 5's ruling B, 2026-09-24); and an in-process call whose argv is not a
    list or tuple literal (a name, or no argument at all, which reads sys.argv). A module that does not parse is one
    unparsed row. A list or tuple on the right of an `in` test is a set of names, not an argv, and is not read. Not read, stated as the residual and each pinned by a case with no
    row (test_each_form_outside_the_read_gives_no_row): an argv assembled one element at a time (append calls); an
    option element _argv_command does not take apart that no element spelling pytest follows (its docstring); an argv
    whose pytest follows a wrapper, built away from the call that runs it; a command string held in a variable or
    built with %, + or .format, a `-c` string held in a variable among them; any
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
        """An argv written at a call the census reads whose command _argv_command does not read, and that carries
        pytest anyway: a pytest command inside one element (any element when the head is a shell run with -c, else a
        multi-word element, a `-c` string running pytest.main among them); or a constant element named pytest or py.test
        by basename after argv[0] (round 5's ruling B, 2026-09-24: a wrapper such as env, nice, timeout or xargs runs
        it as the command, and `env pytest` gave no row while it ran pytest). The second has no exemption, a pip install
        included: a pip line that ever needs one gets an entry in one visible allowlist with its reason."""
        c = [_str(e) for e in elts]
        shell = bool(c) and c[0] is not None and os.path.basename(c[0]) in SHELL_NAMES and "-c" in c
        hit = [t for t in c if t and PYTEST_IN_STRING_RE.search(t) and (shell or re.search(r"\s", t))]
        if hit:
            row(node, what, [], "a pytest command inside one element of the argv (%r), not read as the command" % hit[0])
            return
        named = [t for t in c[1:] if t is not None and os.path.basename(t) in ("pytest", "py.test")]
        if named:
            row(node, what, [], "a constant element named %r after argv[0] of an argv whose command the census does not read "
                                "(a wrapper such as env, nice or timeout runs it as a command; a pip line gets no exemption): "
                                "not read as a launcher until pytest is the command, as argv[0] or after an interpreter head"
                                % named[0])

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
        # fixtures spell `uv run pytest -q` by the dozen), and a module that never spells pytest. A lone `pytest` element
        # after argv[0] at a call the census reads, a pip line's included, is refused since round 5's ruling B (the
        # cases in test_an_option_or_a_wrapper_the_census_does_not_read_before_pytest_is_unparsed_naming_it)
        self.assertEqual(_launchers_in('turn = {"name": "Bash", "input": {"command": "uv run pytest -q"}}\nbash("uv run pytest -q")\n'
                                       'self._bash_turn(0, "pytest -q")\nnote = "run python -m pytest -q first"\n', "t.py"), [])
        # -m under an interpreter head names another module; -m under any other head is that command's own option
        # (git commit -m, with a constant or a variable for git); a script after the head takes -m pytest as ITS arguments
        self.assertEqual(_launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-m", "unittest", "-q"])\n', "t.py"), [], "-m unittest is another module")
        self.assertEqual(_launchers_in('import subprocess\nsubprocess.run(["git", "commit", "-q", "-m", msg])\n', "t.py"), [], "git commit -m is not an interpreter's -m")
        self.assertEqual(_launchers_in('import subprocess\nsubprocess.run([GIT, "commit", "-q", "-m", msg])\n', "t.py"), [], "a word that is not an option ends the interpreter's options")
        self.assertEqual(_launchers_in('import subprocess, sys\nargv = [sys.executable, "tool.py", "-m", "pytest"]\n', "t.py"), [], "a script's own -m pytest")
        # at a call the census reads, the same argv's `pytest` element is refused since round 5's ruling B: the script
        # may run it, as a wrapper does
        rows = _launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "tool.py", "-m", "pytest"])\n', "t.py")
        self.assertEqual([r["kind"] for r in rows], ["subprocess.run"], [_describe_launcher(r) for r in rows])
        self.assertIn("a constant element named 'pytest' after argv[0]", rows[0]["unparsed"])
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

    def test_an_option_or_a_wrapper_the_census_does_not_read_before_pytest_is_unparsed_naming_it(self):
        # round 5's ruling B (extra4-1 and extra4-2, 2026-09-24): every element starting with a dash after an interpreter
        # head read as an option with no value, so a cluster ending in m read its module as a script and a cluster or
        # long option taking a value read that value as one; pytest by name was read at argv[0] alone, and -m took
        # pytest by that name alone. Each form below gave no row while it ran pytest with anyio's plugin loaded (both
        # refuters, a uv venv with pytest and anyio); each is unparsed now, naming its element
        for label, src, reason in (
                ("-Bm pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Bm", "pytest", "-q"])\n', "'-Bm' after the interpreter"),
                ("-Im pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Im", "pytest"])\n', "'-Im' after the interpreter"),
                ("-Impytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Impytest", "-q"])\n', "'-Impytest' after the interpreter"),
                ("-BW error -m pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-BW", "error", "-m", "pytest"])\n',
                 "'-BW' after the interpreter"),
                ("-BX dev -m pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-BX", "dev", "-m", "pytest"])\n',
                 "'-BX' after the interpreter"),
                ("--check-hash-based-pycs always -m pytest",
                 'import subprocess, sys\nsubprocess.run([sys.executable, "--check-hash-based-pycs", "always", "-m", "pytest"])\n',
                 "'--check-hash-based-pycs' after the interpreter"),
                ("a letter the census does not know", 'import subprocess, sys\nsubprocess.run([sys.executable, "-J", "-m", "pytest"])\n',
                 "'-J' after the interpreter"),
                ("-Bm pytest through asyncio.create_subprocess_exec",
                 'import asyncio, sys\nasyncio.create_subprocess_exec(sys.executable, "-Bm", "pytest")\n', "'-Bm' after the interpreter"),
                ("-Impytest through os.execl", 'import os, sys\nos.execl(sys.executable, sys.executable, "-Impytest")\n',
                 "'-Impytest' after the interpreter"),
                ("a cluster ending in m before a name", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Bm", mod, "-q"])\n',
                 "an option cluster '-Bm' ending in m"),
                ("-m pytest.__main__", 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pytest.__main__", "-q"])\n',
                 "-m pytest.__main__, a module in the pytest package"),
                ("-mpytest.__main__ as one element", 'import subprocess, sys\nsubprocess.run([sys.executable, "-B", "-mpytest.__main__"])\n',
                 "-m pytest.__main__, a module in the pytest package"),
                ("env pytest", 'import subprocess\nsubprocess.run(["env", "pytest", "-q"])\n', "a constant element named 'pytest' after argv[0]"),
                ("env with a variable, pytest by path", 'import subprocess\nsubprocess.run(["env", "A=1", "/opt/venv/bin/pytest"])\n',
                 "a constant element named '/opt/venv/bin/pytest' after argv[0]"),
                ("nice pytest, the args keyword", 'import subprocess\nsubprocess.run(args=["nice", "pytest"])\n',
                 "a constant element named 'pytest' after argv[0]"),
                ("timeout 60 py.test", 'import subprocess\nsubprocess.check_call(["timeout", "60", "py.test"])\n',
                 "a constant element named 'py.test' after argv[0]"),
                ("a lone pytest under a non-shell head", 'import subprocess\nsubprocess.run(["ssh", "host", "pytest"])\n',
                 "a constant element named 'pytest' after argv[0]"),
                ("a pip line, which gets no exemption", 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pip", "install", "pytest"])\n',
                 "a constant element named 'pytest' after argv[0]"),
                ("a pip line with a variable package", 'import subprocess, sys\nsubprocess.run([sys.executable, "-m", "pip", "install", pkg, "pytest"])\n',
                 "a constant element named 'pytest' after argv[0]"),
                ("nice pytest through asyncio.create_subprocess_exec", 'import asyncio\nasyncio.create_subprocess_exec("nice", "pytest")\n',
                 "a constant element named 'pytest' after argv[0]"),
                ("env pytest through os.execlp", 'import os\nos.execlp("env", "env", "pytest", "-q")\n',
                 "a constant element named 'pytest' after argv[0]")):
            with self.subTest(form=label):
                rows = _launchers_in(src, "t.py")
                self.assertEqual(len(rows), 1, "%s: one unparsed row expected, read %r" % (label, [_describe_launcher(r) for r in rows]))
                self.assertIn(reason, rows[0]["unparsed"] or "", _describe_launcher(rows[0]))
                self.assertIn("not read as a launcher until", _describe_launcher(rows[0]))
        # read as before: options the census takes apart, -c, git's own -C, and a cluster whose module is another module
        for label, src, kinds in (
                ("-B -m pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-B", "-m", "pytest", "-q"])\n', ["<interpreter> -m pytest"]),
                ("-Werror -m pytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Werror", "-m", "pytest"])\n', ["<interpreter> -m pytest"]),
                ("-Xdev -mpytest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Xdev", "-mpytest"])\n', ["<interpreter> -mpytest"]),
                ("git -C <dir>", 'import subprocess\nsubprocess.run(["git", "-C", d, "commit", "-qm", "msg"])\n', []),
                ("-Bm unittest", 'import subprocess, sys\nsubprocess.run([sys.executable, "-Bm", "unittest", "-q"])\n', [])):
            with self.subTest(read_as_before=label):
                rows = _launchers_in(src, "t.py")
                self.assertEqual([r["kind"] for r in rows], kinds, [_describe_launcher(r) for r in rows])
                self.assertTrue(all(r["unparsed"] is None for r in rows), [_describe_launcher(r) for r in rows])
        rows = _launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-c", "import pytest; pytest.main([\'-q\'])"])\n', "t.py")
        self.assertEqual([r["kind"] for r in rows], ["subprocess.run"], [_describe_launcher(r) for r in rows])
        self.assertIn("a pytest command inside one element of the argv", rows[0]["unparsed"])
        # the over-read, disclosed in _argv_command's docstring: a flagged cluster is red until it is spelled one option
        # per element
        rows = _launchers_in('import subprocess, sys\nsubprocess.run([sys.executable, "-Bm", "pytest", "-q", "-p", "no:anyio"])\n', "t.py")
        self.assertEqual([(r["kind"], r["flag"]) for r in rows], [("an argv literal", False)], [_describe_launcher(r) for r in rows])

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
        # round 5's ruling B (2026-09-24): an option element the census does not take apart, followed by no element that
        # spells pytest and not a cluster ending in m before a name, is passed over as an option with no value, and a -m
        # whose module is a name after it is never reached (a wider refusal refused live sites); and pytest after a
        # wrapper is refused only in an argv written at a call the census reads, so one held in a variable gives no row
        ("an option the census does not take apart before -m and a name", 'import subprocess, sys\n'
         'subprocess.run([sys.executable, "-BW", "error", "-m", mod])\n'),
        ("a wrapper-headed argv held in a variable", 'import subprocess\ncmd = ["env", "pytest", "-q"]\nsubprocess.run(cmd)\n'),
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
