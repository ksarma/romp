#!/usr/bin/env python3
"""scripts/sweep.py: run the local test sweep at one commit and record every leg's exit status against
that commit's full sha. scripts/batch.py verify and land read the record: a batch lands only on a passing
sweep of its exact head (docs/batching.md).

  run    [--tree DIR] [--python PATH] [--served-python PATH] [--workers N] [--wrap LEG=PREFIX]... [--leg NAME...]
         [--flake [LEG=]TEXT]...
         sweep the commit the tree's HEAD names, in a private checkout of it; exit 0 pass, 1 red (a run that
         is itself invalid but leaves the sha unable to pass included), 2 refused to start, 3 invalid
  check  [SHA|HEAD] [--tree DIR] [--branch BR]
         read the result for a commit as batch.py verify does; exit 0 on a pass, 1 otherwise

The result is `<state dir>/sweeps/<full sha>.json`, the state dir resolved as bin/romp resolves it
(ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp); leg logs go under
`<state dir>/sweeps/logs/<full sha>/`. Nothing is written in the batcher's tree, and a result names no
secret: of the leg environment it records the names it dropped and the values it set itself, never an
inherited value, and a leg log's header shows each variable by its name only.

The legs run in private checkouts of the exact sha, never in the batcher's tree, one checkout per CI job (below): a
`git clone --shared --no-checkout` of the batcher's repository under <state dir>/sweeps/trees, checked out at the sha
with hooks off, every runner git call made with GIT_* removed, git's global and system configuration off and
refs/replace ignored. A clone copies none of the batcher's repository config, attributes, excludes, hooks,
sparse patterns, index flags or replace refs, so the legs see the sha's tree plus the tool installs, and
nothing from the checkout's parents. Before any leg the runner verifies the first checkout against `git ls-tree -r
<sha>` (every path, executable bit, symlink target and blob), and refuses (exit 2, nothing recorded) on a
difference or on node_modules, package.json, tsconfig.json or jsconfig.json in any ancestor directory, which
node, tsc and esbuild would read; each later checkout is verified the same way before its first leg, and one that is
not the sha's tree (a leg that rewrote one of the sha's objects in the batcher's repository, whose objects every clone
reads, and git checks a loose object out without checking its hash) records the run invalid. After every leg it reads
that leg's checkout again with its own directory walk,
and records the run invalid, naming the paths and the leg, when a tracked path changed or is gone; when any
other file exists that no rule of a tracked .gitignore ignores (a .gitignore a leg wrote, the clone's
info/exclude or a commit made in the clone excuses nothing); after the deps leg, when an ignored file exists
outside vscode-extension/node_modules that the legs before it in its checkout did not leave as it now is (a later leg
there would read it: bytecode, which python loads in place of a source when it is a timestamp pyc whose stamp matches
or an unchecked hash-based one, or a node_modules or dist tree that node, tsc or esbuild resolve from; the deps leg is
its job's first, so in practice nothing is excused); when the clone's .git was replaced or its HEAD, config or
info/exclude changed; or when one of those names is now in an ancestor directory. After the pytest leg and the served
leg it also reads that leg's environment (the venvs below) against the tree its build left, and records the run
invalid, naming the paths, when a file there was added, changed or is gone. That re-read after each leg, and the
verification of each later checkout, are the runner's producers of invalid, and the legs after either do not run.
The batcher's tree is read for its HEAD sha and branch only, so it need not be clean: the runner prints how many uncommitted edits it holds, which are not swept, and nothing done there
during a run reaches a leg. Nor do its ignored files: a stale dist/ or out-tests/, bytecode, node_modules, or an
untracked test the tracked .gitignore covers. The checkout's path is longer than a batch worktree's; TMPDIR, whose
length the deepest session-host socket path depends on, is unchanged, the run's and each leg's own. Each checkout is
removed when its job's legs end, and TMPDIR (the run's, and the running leg's) and the checkout in use are removed on
every exit path: SIGTERM, SIGHUP and SIGINT (Ctrl-C) stop each leg's process group, the runner exiting 128 plus the signal's
number, and on Linux the runner is a child subreaper that kills whatever a leg left
running, a descendant that left the group included. A stop signal that arrives during that cleanup does not cut it
short: the step it interrupted runs again from its start and the steps after it run too (round 2, correctness-3; a
venv whose tree changed is still retired), and one that arrives while a checkout is being made removes what was made
of it, its marker included (extra5-2). Each checkout records its sha beside it, and every run
removes the checkouts of runs that are no longer running. Every orphaned descendant of a leg, in its process group
or not, is reparented to the runner and reaped as soon as it exits while the leg runs, so it does not stay in the
leg's group as a defunct process.

The legs (LEGS) are pytest (all of tests/, below), deps (`npm ci` from the sha's lockfile), bats, manager and tools
(node --test), ledger (scripts/upstream-ledger.py check), the three webview legs (typecheck, npm-test, build), and
served (the browser-backed served-page tests, below). They are grouped as CI's jobs group their steps (round 2, the
coordinator's decision 13; leg_groups). Each leg mirrors one step of the swept sha's ci.yml, found by its name
(LEG_STEPS). The legs whose steps one job holds run in one fresh checkout, in that job's step order, as CI's steps in
one job share its checkout, and each such group starts from a checkout of its own, as each of CI's jobs does. The
grouping is read from ci.yml, never restated here; the result records each group's job, legs, checkout and setup
(runner.checkout.groups) and the order the legs ran in (order). The ledger's check is in no job of ci.yml (CI runs it
in a workflow of its own), so the ledger leg runs in a checkout of its own, after the ci.yml groups. The groups run in
ci.yml's job order, except that the pytest leg's job runs first, since the pytest leg's skips decide what the served
leg also runs. npm ci runs where the group's job runs it: as the deps leg in the first job that holds that step
(DEPS_STEP), and as the setup of any other group whose job runs it before one of the group's legs. A job that runs no
npm ci gets none. So the pytest leg runs as CI's Python cells run it, with no node dependencies
and no browser: in a checkout where npm ci never runs, with PLAYWRIGHT_BROWSERS_PATH at an empty directory, so the
browser-backed tests skip there as they do in CI, and the other tests in the served globs' files (63 in six files when
the served rulings were made) run with the SDK, as CI runs them; and the bats, manager and tools legs, whose CI jobs
run no npm ci, run with no node_modules, as there. Each group runs in its job's step order, so the npm-test leg runs
over a checkout holding no bundle a served test built, as CI's Test step does. Every head owes every leg, a member's
head included, whatever its diff: the webview legs read files outside kernel/kernel.py, ui/ and vscode-extension/ (tests, other kernel
modules, docs), and the served tests boot the kernel and serve the webview bundle, so no set of changed paths shows
either may be skipped. deps, the webview legs and served are marked not owed only when the sha has no
vscode-extension/package.json, and the ledger only when it has no ledger script; a reader refuses any other not-owed
mark, and batch.py's verify, plan and --repin and `check` refuse either reason when the sha's tree holds the file it
names (round 2, correctness-4, for the ledger). Every leg runs even after an earlier one is red, so the result carries every leg's status.

The pytest leg runs over all of tests/ (PYTEST_IGNORED aside), in a venv the runner builds, not in --python itself
(sdk_environment): `python -m venv` from
--python under <state dir>/sweeps/sdk/<key>, then the install steps of the python job in the swept sha's ci.yml
(INSTALL_STEPS: pytest and its plugins, cryptography, and the Claude Agent SDK at the pin its SDK step reads from
kernel/session_host.py), each run with the venv's python in place of `python`, as CI's Python cells run them. The
runner reads those steps in a few line shapes (read_run) and restates nothing they install; a line it does not read,
or a head whose ci.yml lacks one of the steps, is refused. So is anything else in the file that could change what CI
installs without changing a command the runner reads: a key on an install step other than name, run, shell (bash),
timeout-minutes and continue-on-error (an env: such as PIP_CONSTRAINT, an if:, a working-directory:), a key of the
python job other than the ones it has today (an env:, defaults: or container: among them), a workflow-level env: or
defaults:, and a step of the job other than the install steps, Run pytest, and the unnamed checkout and setup-python
steps (an unnamed run step, or a named one the runner does not read). The key covers the SDK's pin, --python's path
and version and the install commands, so a pin change builds a new venv beside the old one (an old one stays until
removed by hand), and a finished build is reused; unlike CI, which resolves the unpinned packages fresh on every run,
a reused venv keeps the versions it resolved when it was built. The build runs with a private HOME and pip's
configuration files off, so no index, PYTHONPATH or SDK of the batcher's reaches it; an interpreter without ensurepip
gets pip from PyPA's get-pip.py (ROMP_GET_PIP_URL overrides where from). A build that fails refuses the run (exit 2,
nothing recorded, the venv removed), naming the step and its log, <key>.log beside the venv. The build's marker
records the venv's tree (every path's mode, and each file's size and sha256), and a run uses a finished venv only when
its tree still matches that record (bytecode python adds under __pycache__ aside) and the venv's interpreter reports
the version of the one it was built from: the pytest leg runs as the venv's python with the venv writable, so a file a
test left there (a .pth file, which every later interpreter start executes) would otherwise reach every later sweep
under the same key. A venv that does not match is built again, naming what differs. Each run holds a shared lock on
the key until it ends, and a rebuild, which removes the venv first, takes the lock exclusively, so it waits for every
run still using the venv. The result records the key, the SDK's version as the venv's own metadata reports it, the
venv's interpreter version and a digest of its tree (runner.sdk). The pytest leg's PATH leads
with the venv's bin, and the leg gets ROMP_SDK_REQUIRE=1 as CI's Run pytest step does, so the SDK-gated tests run and
the pin test fails where the SDK does not import.

The served leg mirrors CI's served step (SERVED_STEP, read by its name in whichever job of the swept sha's ci.yml holds
it; read_served_step). It runs the files the globs on that step's pytest line select, in one pytest process, as CI's
served step runs them (SERVED_FLAGS, which CiParity compares with the step, with the globs' expansion in their place,
and PYTEST_ISOLATION; no -n). It runs in a venv the runner builds for it (served_environment), never in the pytest
leg's: `python -m venv` from --served-python (default --python) under <state dir>/sweeps/served/<key>, then the served
step's own pip lines as ci.yml writes them, each with the venv's python in place of `python`, and nothing else. So the
venv holds no SDK, as CI's served step installs none, while a served test's kernel takes the SDK backend wherever the
SDK imports. --served-python must be the MAJOR.MINOR the actions/setup-python step before the served step in its job
names (3.12 today, read from ci.yml, never restated), or the run is refused naming what to pass: an explicit
interpreter, not one searched for on PATH, and --python by default, since the box's --python is that version. The key
covers the pip lines and --served-python's path and whole version; the build, its marker (SERVED_MARKER), the tree
check before each use and after the leg, the shared and exclusive locks and the refusals on a failed build are the
pytest leg's venv's (_venv_environment). A built venv is refused too when its directory does not hold python3 as the
same file as its python: the served tests' kernels are started as bin/romp-kernel (#!/usr/bin/env python3), so they
run the first python3 on the leg's PATH, which leads with the venv's directory. The leg's environment is the
allowlist's plus the served step's own env: block as ci.yml writes it at the swept sha (ROMP_SERVED_TESTS_REQUIRE,
which turns a skip in those files into a failure, and ROMP_SERVED_TESTS_ENGINES), read and never restated here; a
served step the runner does not read in full (a value holding an expression, a name the runner sets itself, an env:
on its job or the workflow, a line of its run text other than a pip install and the one pytest line, a python-version:
other than a quoted MAJOR.MINOR) is refused by name. The result records the step's job, env, globs, pip lines and
Python version, and the venv's key, path, interpreter and version, every distribution in it with its version, and the
pytest plugins they declare, which pytest loads on its own (runner.served).

The served leg also runs, with the deps present, the tests outside the served globs that the pytest leg skipped for
want of the extension's node_modules or a browser (DEPS_SKIP). Neither of CI's jobs runs them (the Python cells have
neither; the served step runs only the globs), and the sweep before the served rulings ran them in its pytest leg,
after npm ci, so every test the rule selects still runs with the deps. They are derived at run time, not listed: the
pytest leg prints every skip with its node id and reason (-rfEs --no-fold-skipped), and deps_skipped reads, from its
log's short summary, each SKIPPED line and each SUBSKIPPED line (pytest 9's subtests; the line names the test the
subtest belongs to, which the served leg runs whole) outside the served globs whose reason DEPS_SKIP matches; the node
ids join the served leg's command after the globs' files, and both legs' records name them. The reader is closed
(round 2, Class C): a pytest leg whose log has no closing summary line, or whose short summary holds a line the reader
does not read (a line shaped like a kind that is none of pytest's kinds, a skip line that does not name exactly one
test, a non-blank line before any kind line), leaves the set unknown, and the served leg is then red naming why and the
lines, never run without it. The count when the served rulings' condition was measured: 1 test in 1 file when
measured on 2026-09-28 (tests/test_landing_bundles_built.py, whose build guard needs the extension's deps). The claim
covers what the rule selects in a summary the reader reads. Two summaries pytest writes correctly leave the set
unknown, so the served leg is red, never a skip dropped: a subtest message holding a newline splits its SUBSKIPPED
line; and a node id is read up to its first " - ", so a parametrize id holding one is read short, refused when that
leaves a bracket open (a node id's brackets must balance), while one read short that closes its brackets (a parametrize
id holding "] - ") is handed to the served leg's pytest, which exits 4 unless a test has exactly that id. A SUBSKIPPED
line whose node id could start at more than one place (a subtest's description holding "] tests/" or ") tests/") is
refused too. Under pytest 8 a subtest's skip prints as a SKIPPED line of its whole test, the same node id. And three
cases fall outside the claim. A skip for want of the deps whose reason DEPS_SKIP does not match runs in no leg; the
pytest leg's record lists every other skip outside the served globs with its reason (deps_skipped.unselected), so such
a miss can be seen. A test that does not skip without node_modules but takes another road runs there on that road
only: two real-tree pins, in tests/test_lab_dist.py and tests/test_kernel_bundle_staleness.py, read esbuild.js under tests/lab_dist_stub.py's stand-in for a missing package,
where the sweep before ran them after npm ci with the real one (the build leg still loads the real one). And the
tests the served leg adds run in the served venv, with no SDK, where before they ran in the pytest leg's venv, so a
test outside the globs that needs both the deps and the SDK would skip there, and no switch makes that skip a
failure.

The leg environment is an allowlist (LEG_ALLOW, leg_sets): USER and LOGNAME pass when set, and the runner
sets everything else. PATH is the directory of --python (for the pytest and served legs, of its venv's python) and
those of node, npm, bats, git and gitleaks, then /usr/bin and /bin; TMPDIR is a fresh short directory under /tmp that
each leg gets for itself, made when the leg starts and removed when it ends, and HOME (empty when the leg starts) and
XDG_STATE_HOME (a private state root, session hosts off) are under it, so nothing one leg leaves in its HOME, state
root or TMPDIR reaches a later leg (round 2, Class B: an .npmrc whose node-options would replace npm test's heap cap, a
.gitconfig, a session-hosts file flipped on); the npm ci setup of a --leg re-run gets its own the same way, and the
run keeps a TMPDIR of its own for what is not a leg (the venv builds and the tool-version probe);
npm_config_cache and PLAYWRIGHT_BROWSERS_PATH point at the shared caches the batcher's environment names, but the
pytest leg's PLAYWRIGHT_BROWSERS_PATH, an empty directory under TMPDIR (NO_BROWSERS), as CI's Python cells have no
browser; SHELL=/bin/bash,
LANG=C.UTF-8 and CI=true, as CI's runner has them; npm's global config and git's system config, which live
outside HOME, are off (npm_config_globalconfig=/dev/null, GIT_CONFIG_NOSYSTEM=1); every ROMP_*_PORT the tree reads is a dead port (a box
floor CI does not need); and each leg gets the switches CI sets on the matching step (LEG_ENV; the served leg's
are read from ci.yml's served step), plus the box rule's 8 GB heap cap for npm test (NODE_OPTIONS), which CI does not
set. So no credential, session identity or
test-narrowing variable (PYTEST_ADDOPTS, PYTHONPATH, NODE_OPTIONS) of the batcher's shell reaches a leg, and
no dotfile of the batcher's HOME does (an .npmrc, a git config and its hooks, a shell rc, the live
deployment's SDK), nor the global npmrc of a node installed under it (<prefix>/etc/npmrc, turned off). npm's builtin
config file (npmrc in npm's package root), which npm reads before any other and nothing turns off, is read by the runner:
one that sets any key but prefix refuses the run, naming the file (round 2, extra6-2), and the result records its
presence and sha256 (runner.npm_builtin); an npm whose package root the runner cannot find above its real path (a shim,
such as volta's) records none, and its builtin file is not read. pytest also runs with `-c /dev/null --rootdir=. --confcutdir=.`, so no pytest.ini or
conftest.py above the tree configures it. --wrap prefixes run with the runner's environment, and the
allowlist applies after them (`env -i`), so nothing a wrap sets reaches the leg. What the allowlist does not
govern: files stay readable at their absolute paths (a credential file, an agent's socket), and every leg can
read /proc/<pid>/environ of the runner and of every other process of the batcher's user, since the legs run
as that user. The result records the allowlist's hash (runner.leg_env), and a reader refuses a result
recorded under another; the hash covers what the runner itself sets, that the served leg adds its step's env:
block, and the shape each leg runs in (its own TMPDIR, HOME and state root; one checkout per ci.yml job, the steps it
groups by), so a result written before round 2's fixes, whose legs shared one TMPDIR, HOME, state root and checkout,
reads as recorded under another (decision 15); not the values of that env: block, which are the swept sha's own (as the SDK's pin is) and are recorded
in the leg's env_set, nor the job grouping, which is the sha's ci.yml's and is recorded (runner.checkout.groups).
The result also records the versions of node, npm, bats, git and gitleaks the legs found, and, per
leg, the names it left in its private HOME (runner.home_left, {leg: names}; a setup's are in its own record), with
home_empty true when no leg and no setup left anything; recorded only.

What a leg leaves, and what of it reaches the legs after it (round 2, Class B and the coordinator's decision 13).
Closed: a leg's TMPDIR, private HOME and private state root are its own and are removed when it ends, so nothing it
leaves there reaches a later leg. Nothing it leaves in its checkout reaches a leg of another job, since each job's
legs start from a fresh clone verified against the sha's tree: no file in the clone's .git (a hook, info/attributes,
info/exclude, config, a ref or refs/replace, packed-refs, objects/info/alternates) and no ignored file (bytecode,
node_modules, dist). Shared: the legs of one job share its checkout, as CI's steps in one job do. The re-read after
each leg makes the run invalid when it finds one of the changes it checks for (above); anything else a leg leaves in
that checkout (a hook or an attributes file in the clone's .git, a replace ref, an ignored file other than one the
deps leg adds outside vscode-extension/node_modules) reaches the later legs of its job, as it would reach CI's later
steps. Open, because the runner runs on the batcher's machine as the batcher's user (the stated outside): /tmp outside
each TMPDIR, /dev/shm, /run/user/<uid>, the shared npm and Playwright caches, the passwd home (the home directory the
password database names, which is not HOME and which a leg can write to), tmux's socket directory (tmux ignores
TMPDIR), --python's directory, which leads the PATH of every leg outside the two venvs, and the batcher's repository,
whose objects every clone reads (a rewritten object of the sha fails the next job's verification). A leg can leave a
file in any of these that a later leg reads.

The pane bench (tests/ui-bench.test.mjs), the Browser legs step (scripts/ci-browser-legs.sh: its roster checks, and
the rostered browser tests run with ROMP_BROWSER_LEGS_REQUIRE=1; the npm-test leg runs the same tests without that
switch, so a Chromium that fails to launch there skips instead of failing), the PDF renderer smoke step (CI's
extension job runs tools/pdf-smoke.test.mjs after its npm ci; the tools leg runs that file with no node_modules, as
CI's job for the tools step does, where it skips), the Python versions other than --python's, and macOS run only in the
batch's CI. CI's free-threaded cell also runs pytest with PYTHON_GIL=0, which the
runner does not set, so a free-threaded --python runs with its own default.

The result is append-only (schema 2): `runs` keeps every run at the sha, oldest first, and a run is never
rewritten once it has finished. Every run records the private checkout it ran in (runner.checkout); a reader
reads a result holding a run without one as unreadable, and the runner moves such a file aside, as it moves a
schema-1 file: both came from a runner that swept the batcher's own tree. The verdict is read from the newest full run with any later --leg re-run's legs
laid over it, and the whole history is read too: a run that failed a leg counts as excused only when the next
run of that leg carries --flake naming it and its known-flake entry, once per leg, whether that run is a --leg
re-run or a full run (`--flake LEG=TEXT`). A leg that failed twice, or that a later run passed without --flake
naming it, leaves no run at that sha able to pass; the runner refuses such a run up front, and the reader reads
the result red, naming the failed run and its logs. Invalidity voids a run's passes, never its failures (round 2,
Class A): a leg that failed in an invalid run counts as a failure, the leg whose re-read made the run invalid included,
so it blocks a plain full run and uses that leg's one flake, and a second failure inside an invalid run leaves the sha
unable to pass (the reader reads it red, and the runner exits 1 for such a run, not 3); a pass in an invalid run counts
for nothing, since its checkout or venv changed. An invalid run that failed no leg needs no flake. The pass line,
verify's record and the reader's invalid line name each invalid run with the legs it failed. A leg that did not pass
is written to the result as soon as it exits, before the re-read after it, so a stop during that re-read keeps its
failure; a pass is written after its re-read, which could void it. A stop in the moments between a leg's exit and the
runner filling in its record (the reap of what the leg left running, up to about five seconds, then its log's summary
and test count) still loses the rc: the run records that leg as never finished, and the next run needs no flake for
it. Writing the rc before the record is whole would not close this, since a stop of the runner's whole scope kills the
leg with the same signal, and its rc would then read as a failure.
A --leg re-run refuses unless the newest run finished, is valid, and failed that leg, so the flake a failure in an
invalid full run needs is spent on a full run. A --leg re-run runs each leg it names in a fresh checkout of that leg's
job, grouped as a full run groups them, so it may name legs of several jobs (pytest with a leg after deps included),
with npm ci first where that job runs it before the leg and deps is not re-run with it (round 2, decision 13): a
re-run of pytest, or of a leg whose job runs no npm ci, has no setup, and deps named with a later leg of its own job
runs as a leg, not a setup. A setup that fails, or changes the checkout, refuses the run when nothing is recorded yet
(the run's first group), and otherwise blocks its group's legs after it, each red naming the setup, or makes the run
invalid. A --leg re-run of served also runs the tests the newest pytest leg at the sha skipped for want of the deps.

The runner calls no nice, ionice, systemd-run, flock or slot script itself: a machine that runs legs
under such wrappers passes them with --wrap. It imports nothing beyond the standard library.
"""
import argparse
import datetime as _dt
import fcntl
import hashlib
import json
import os
import random
import re
import shlex
import shutil
import signal
import stat
import string
import subprocess
import sys
import tempfile
import time

SCHEMA = 2
# The legs a result records. They run grouped by the ci.yml job that holds each one's step (leg_groups, round 2's
# decision 13), not in this order: the pytest leg's job first, in a checkout where npm ci never runs and with no browser,
# as CI's Python cells run pytest over all of tests/ (the served ruling's item 1, 2026-09-28).
LEGS = ("pytest", "deps", "bats", "manager", "tools", "ledger", "typecheck", "npm-test", "build", "served")
WEBVIEW_LEGS = ("typecheck", "npm-test", "build")
# The browser-backed served-page tests, the files CI's served step selects: a leg of their own, as CI runs them in a
# step of their own (the served ruling, 2026-09-28). Last in LEGS; it runs in the job that holds its step, after that
# job's steps before it (leg_groups). It also runs the tests outside those files that the pytest leg skipped for want of the deps (DEPS_SKIP).
SERVED_LEG = "served"
TEST_LEGS = ("pytest", "bats", "manager", "tools", "npm-test", "served")
# The test legs pytest runs, whose tests are counted from pytest's summary line.
PYTEST_LEGS = ("pytest", "served")
# The legs the runner owes at every head; the others it marks not owed only with a reason (`why`): deps, the webview
# legs and served (EXTENSION_LEGS) only when the sha has no vscode-extension/package.json (NO_PACKAGE_JSON), and the
# ledger only when it has no ledger script.
ALWAYS_OWED = ("pytest", "bats", "manager", "tools")
# The legs owed wherever the sha has vscode-extension/package.json. The webview legs are owed at every such head,
# a member's included, whatever its diff (round 1, decision 11): they read files outside kernel/kernel.py, ui/ and
# vscode-extension/ (a census of their reads found 82 such tracked files), so a rule over the changed paths passes
# heads that turn them red. The served leg is owed on the same terms: its tests boot the kernel and serve the webview
# bundle, whose inputs lie outside those three as well, and they need the extension's node_modules (playwright,
# esbuild), which deps installs from the same package.json.
EXTENSION_LEGS = ("deps",) + WEBVIEW_LEGS + (SERVED_LEG,)
WEBVIEW_WHY = "owed at every head: the webview legs read files outside kernel/kernel.py, ui/ and vscode-extension/"
SERVED_WHY = ("owed at every head: the served tests boot the kernel and serve the webview bundle, which reads files "
              "outside kernel/kernel.py, ui/ and vscode-extension/")
VERDICTS = ("pass", "red", "running", "invalid")
# The one reason the runner gives for deps, the webview legs and served not owed: the sha's tree has no extension. A
# result that marks one of them not owed for any other reason did not come from this runner (every checkout is fresh,
# so it never holds node_modules, and no diff excuses a webview leg or the served leg), and batch.py and `check` accept
# this one only when the sha's tree really has no such file (excuse_contradiction).
NO_PACKAGE_JSON = "no vscode-extension/package.json"
# The one reason the runner gives for the ledger not owed: the sha's tree has no ledger script (round 2, correctness-4).
# The reader refuses any other reason for it, and batch.py and `check` accept this one only when the sha's tree really
# has no such file (excuse_contradiction), as for NO_PACKAGE_JSON.
LEDGER_SCRIPT = "scripts/upstream-ledger.py"
NO_LEDGER_SCRIPT = "no %s in the tree" % LEDGER_SCRIPT
# Each leg the runner may mark not owed, with the one reason it gives, and the file whose absence each reason names.
NOT_OWED_WHY = dict([(n, NO_PACKAGE_JSON) for n in EXTENSION_LEGS] + [("ledger", NO_LEDGER_SCRIPT)])
NOT_OWED_FILE = {NO_PACKAGE_JSON: "vscode-extension/package.json", NO_LEDGER_SCRIPT: LEDGER_SCRIPT}
EXIT_PASS, EXIT_RED, EXIT_REFUSED, EXIT_INVALID = 0, 1, 2, 3

# The pytest command the runner builds (pytest_cmd): `<python> -m pytest tests -n <workers>`, then these flags, then
# PYTEST_ISOLATION and one --ignore per PYTEST_IGNORED entry. Against CI's Run pytest step (.github/workflows/ci.yml,
# `python -m pytest -q -n <2 or 0> -p no:anyio --durations=10 --timeout=600 --timeout-method=thread`, collecting from
# the root, where test modules live only under tests/) the differences are: -n at this machine's idle cores; -p
# no:cacheprovider, so nothing is written to a .pytest_cache in the checkout; -rfEs --no-fold-skipped, which print
# every skip with its node id and reason in the short summary beside pytest's default failures and errors (a bare -rs
# would replace those), a subtest's skip as a SUBSKIPPED line naming its test, where the runner reads, closed, the tests
# the leg skipped for want of the deps (deps_skipped); PYTEST_ISOLATION; and the PYTEST_IGNORED list. The served globs'
# files are collected, as CI's Python cells collect them: the leg runs with no node_modules and no browser, so the
# browser-backed tests skip there as in CI and the others in those files run with the SDK. tests/test_sweep_runner.py
# (CiParity) holds the two sides to exactly these differences.
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-p", "no:anyio", "--durations=10", "--timeout=600", "--timeout-method=thread",
                "-rfEs", "--no-fold-skipped")
# No pytest.ini or conftest.py above the checkout configures the leg: an empty inifile, the rootdir pinned to the
# checkout (a bare `-c /dev/null` would move it to /dev), and conftest.py files read from the checkout down only.
PYTEST_ISOLATION = ("-c", os.devnull, "--rootdir=.", "--confcutdir=.")
PYTEST_MODULES = ("pytest", "xdist", "pytest_timeout")
# The pytest leg's interpreter is a venv the runner builds from --python and ci.yml's install steps (sdk_environment):
# the workflow file, its job, and the job's steps the runner reads, in the order CI runs them. What they install (pytest
# and its plugins, cryptography, the Claude Agent SDK at its pin) is read from the swept sha's ci.yml, never restated
# here; tests/test_sweep_runner.py (CiParity) holds this list to every install step of the job.
CI_WORKFLOW = os.path.join(".github", "workflows", "ci.yml")
CI_PYTHON_JOB = "python"
INSTALL_STEPS = ("Install pytest", "Install cryptography", "Install the Claude Agent SDK")
# The step whose one pinned requirement is the SDK: its name and version are the pin the result records.
SDK_STEP = INSTALL_STEPS[-1]
# The python job as the runner reads it (read_install_plan), and nothing else: the job's own keys; its steps, which are
# the INSTALL_STEPS, the pytest step, and unnamed setup steps that use one of SETUP_ACTIONS; and the keys an install
# step may carry. Anything outside these could change what CI installs without changing a command the runner reads (an
# env: such as PIP_CONSTRAINT, an if:, a working-directory: that moves the pin's sed read, a job's container: or
# defaults:, a workflow-level env:), so it is refused by name rather than built without.
PYTEST_STEP = "Run pytest"
PYTHON_JOB_KEYS = ("name", "runs-on", "timeout-minutes", "strategy", "steps")
SETUP_ACTIONS = ("actions/checkout", "actions/setup-python")
INSTALL_STEP_KEYS = ("name", "run", "shell", "timeout-minutes", "continue-on-error")
WORKFLOW_KEYS_REFUSED = ("env", "defaults")
# Where pip comes from for an interpreter without ensurepip (Debian's and Ubuntu's system python split it into a
# package of its own), as bin/romp-sdk-setup does; ROMP_GET_PIP_URL overrides it, as it does there.
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
# The file a finished build writes last in the venv; a venv without it is a build that did not finish. It records the
# venv's tree as the build left it (venv_tree), which every later use compares with the venv's tree then. One name for
# the pytest leg's venv, one for the served leg's.
SDK_MARKER = "sweep-sdk.json"
SERVED_MARKER = "sweep-served.json"
# How many times one run reads the venv under a shared lock before it refuses: each read that finds it stale is
# followed by a build under the exclusive lock, so a venv that still does not match its build on the last read is
# refused rather than built again.
SDK_ATTEMPTS = 3
# The most one command of the build may take (a pip install that downloads the SDK's wheel of about 100 MB included).
SDK_STEP_TIMEOUT = 900
# Test modules the pytest leg never collects, each with its reason (recorded in the result).
PYTEST_IGNORED = {
    "tests/test_cut_turn_tree_kill.py": ("it runs the real cut-turn reaper on a child of pytest, which inside a romp "
                                         "session can stop the session's own process tree; CI covers it once per batch"),
}
# The served leg's step in ci.yml, read by its name in whichever job holds it (read_served_step): the extension job
# today; fork PR 928 moves it into a job of its own. Its env: block is the served leg's switches, the globs on its
# pytest line are the files the served leg runs, its pip lines are what the served leg's venv holds, and the
# actions/setup-python step before it in its job names the Python version that venv is built from.
SERVED_STEP = "Browser-backed served-page tests (pytest)"
SETUP_PYTHON = "actions/setup-python"
# The ci.yml step each leg mirrors, by its name (round 2, the coordinator's decision 13). CI runs each job in a fresh
# checkout of its own, and a job's steps share it; so the runner reads, in the swept sha's ci.yml, which job holds each
# leg's step, and the legs whose steps one job holds run in one fresh verified checkout, in that job's step order, while
# each such group starts from a checkout of its own (leg_groups). The grouping is read from the file, never restated
# here: fork PR 928 moves the tools leg's step and the served step into jobs of their own, and the groups follow.
# npm ci runs where the group's job runs it (DEPS_STEP): as the deps leg in the first job that holds that step, and as
# the group's setup in any other job whose legs come after it. CiParity holds each name to the step whose command the
# leg runs.
DEPS_STEP = "Install deps"
LEG_STEPS = {"pytest": PYTEST_STEP, "deps": DEPS_STEP, "bats": "Run bats", "manager": "Manager handshake tests (node --test)",
             "tools": "Vendored tooling and host-script tests (node --test)", "typecheck": "Typecheck", "npm-test": "Test",
             "build": "Build", SERVED_LEG: SERVED_STEP}
# The legs whose check is in no job of ci.yml, each run in a fresh checkout of its own after the ci.yml groups: CI runs
# scripts/upstream-ledger.py check in a workflow of its own (.github/workflows/ledger.yml).
OWN_CHECKOUT_LEGS = ("ledger",)
# A python-version: the runner reads on that step: a quoted MAJOR.MINOR (YAML reads a plain 3.10 as the number 3.1).
_PYTHON_VERSION = re.compile(r"""(['"])([0-9]+\.[0-9]+)\1""")
# The keys the served step may carry. env: and run: are read; working-directory: must leave the step at the repository
# root, where its globs resolve; shell: must be bash, which reads the run text the runner reads. if:, continue-on-error:
# and timeout-minutes: change only whether CI runs the step or counts its red, and the leg runs and counts it always.
SERVED_STEP_KEYS = ("name", "working-directory", "env", "run", "shell", "if", "continue-on-error", "timeout-minutes")
SERVED_ROOT = "${{ github.workspace }}"
# The served leg's command (served_cmd): `<python> -m pytest <the globs' expansion> <the deps-skipped tests>`, then
# these flags, which are the served step's pytest line's as ci.yml writes them, then PYTEST_ISOLATION. One process, as
# CI's served step runs it: -n can pass what one process catches (a thread outliving its module, the first bundle
# build). Against that line the differences are the expansion in place of the globs, the tests the pytest leg skipped
# for want of the deps (DEPS_SKIP), and PYTEST_ISOLATION; CiParity holds the two sides to exactly these differences.
SERVED_FLAGS = ("-q", "-rs", "-p", "no:cacheprovider", "-p", "no:anyio", "--durations=20", "--timeout=600",
                "--timeout-method=thread")
# pytest's options that take the next word as their value when written apart from it (read_served_step skips the
# value, so a word after one of them is never read as a glob).
PYTEST_VALUE_OPTIONS = ("-p", "-n", "-c", "-k", "-m", "-o", "-r", "-W", "--rootdir", "--confcutdir", "--basetemp",
                        "--ignore", "--ignore-glob", "--deselect", "--durations", "--timeout", "--timeout-method",
                        "--maxfail", "--dist")
# A glob on the served step's pytest line: a relative pattern for .py files directly under tests/, the form the step
# writes; anything else there is refused rather than read.
_SERVED_GLOB = re.compile(r"tests/[A-Za-z0-9_.*?\[\]-]+\.py")
# The tests outside the served globs that skip without the extension's node_modules or a browser run in neither of CI's
# jobs: CI's Python cells have neither, and CI's served step runs only the globs. The sweep before the served ruling ran
# them, in its pytest leg after npm ci, so the served leg runs them now, with the deps present (the served ruling's
# condition, 2026-09-28; the module docstring names what falls outside it). They are derived at run time from the
# pytest leg's own log: every skip its short summary prints (`SKIPPED <node id> - <reason>`, or for a subtest
# `SUBSKIPPED<description> <node id> - <reason>`, naming the test it belongs to; PYTEST_FLAGS' -rfEs --no-fold-skipped)
# whose node id is outside the served globs and whose reason matches DEPS_SKIP, read by a closed reader that leaves
# the set unknown on any line it does not read (deps_skipped).
# DEPS_SKIP is read off the reasons the tree's tests give when they skip without the deps: every one of the 578 skips in
# the served globs' files and the one outside them, measured on 2026-09-28, names one of these words, and none of the
# other 20 skips outside them does (tests/test_sweep_runner.py, DepsSkipRule, holds it to those reasons). A reason it
# matches that is not about the deps costs one more test the served leg runs, which skips there again; a deps reason it
# misses is a test no leg runs,
# which the pytest leg's record shows among the skips the rule did not select (deps_skipped.unselected).
DEPS_SKIP = re.compile(r"node_modules|npm ci|extension deps|playwright|chromium|esbuild|\bbrowser", re.I)
DEPS_SKIP_WHY = ("the tests outside the served globs that the pytest leg skipped for want of the extension's node_modules "
                 "or a browser: they run in neither of CI's jobs, so the served leg runs them with the deps present")
# What the served ruling's condition measured on 2026-09-28 (all of tests/ run as the pytest leg runs them, in the SDK
# venv, with no node_modules and no browser: 18428 passed, 599 skipped, 21 of the skips outside the served globs): the
# tests outside the served globs that skip for want of the deps or a browser, and the files they are in. The run itself
# derives the set (deps_skipped); this is the count the docstring, the help and docs/batching.md name. The files are
# held to a census of the tree's skip calls (tests/test_sweep_runner.py, DepsSkipRule), so a new file that skips for
# want of the deps in words DEPS_SKIP reads reds there until this is measured again.
MEASURED_DEPS_SKIPS = {"date": "2026-09-28", "tests": 1, "files": ("tests/test_landing_bundles_built.py",)}
MEASURED_TEXT = "%d test%s in %d file%s when measured on %s" % (
    MEASURED_DEPS_SKIPS["tests"], "" if MEASURED_DEPS_SKIPS["tests"] == 1 else "s", len(MEASURED_DEPS_SKIPS["files"]),
    "" if len(MEASURED_DEPS_SKIPS["files"]) == 1 else "s", MEASURED_DEPS_SKIPS["date"])
# The pytest leg's PLAYWRIGHT_BROWSERS_PATH: an empty directory of this name under TMPDIR, so no browser is found there,
# as none is on CI's Python cells; every other leg gets the shared cache.
NO_BROWSERS = "no-browsers"
# The commands of the deps leg and the three webview legs, all run in vscode-extension/ (CI's extension job runs
# the same commands there; deps adds --no-audit --no-fund, which change what npm prints, not what it installs).
DEPS_CMD = ("npm", "ci", "--no-audit", "--no-fund")
NPM_CMDS = {"typecheck": ("npm", "run", "typecheck"), "npm-test": ("npm", "test"), "build": ("npm", "run", "build")}
GLOBS = {
    "bats": ("tests/*.bats",),
    "manager": ("tests/manager-*.test.js",),
    "tools": ("tools/*.test.mjs", "vendor/track-changents/hooks/*.test.mjs"),
}
# The leg environment is an allowlist (leg_env). A leg inherits these names from the runner's environment when they
# are set, and nothing else: every other variable it sees is one the runner sets (leg_sets), so no credential, session
# identity, hook variable or test-narrowing name (PYTEST_ADDOPTS, PYTEST_PLUGINS, PYTHONPATH, NODE_OPTIONS) the
# batcher's shell holds reaches a leg.
LEG_ALLOW = ("USER", "LOGNAME")
# The leg's PATH: the directory of the pytest leg's interpreter, then the directory of each of these tools as the
# runner's PATH finds it, then PATH_FLOOR. The batcher's PATH is not passed on (on a self-hosting box it leads with the
# live deployment's bin directory and holds a vault tool, neither of which a leg needs).
PATH_TOOLS = ("node", "npm", "bats", "git", "gitleaks")
PATH_FLOOR = ("/usr/bin", "/bin")
# Fixed values, as GitHub's ubuntu runner has them, whatever the batcher's are. CI=true because that runner sets it
# and pytest reads it (with CI set, its short summary prints each error's message whole).
LEG_FIXED = {"SHELL": "/bin/bash", "LANG": "C.UTF-8", "CI": "true"}
# The tools' configuration files that live outside HOME, so the private HOME does not replace them, each turned off:
# npm's global config, <prefix>/etc/npmrc, where <prefix> is the node install's own directory (user-writable when
# node comes from nvm, fnm, volta or a ~/.local prefix; its node-options would reach every npm leg as NODE_OPTIONS,
# replacing npm test's heap cap), and git's system config (user-writable under a Homebrew git; a core.hooksPath there
# would run in the fixture repos of the bats files that set neither GIT_CONFIG_GLOBAL nor HOME).
TOOL_CONFIG_OFF = {"npm_config_globalconfig": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
# npm's builtin config file, <npm's package root>/npmrc, is read before the user and global files and neither the private
# HOME nor npm_config_globalconfig turns it off (round 2, extra6-2): it is as user-writable as the global one under nvm,
# fnm, volta or a ~/.local prefix, and a node-options line there reaches every npm leg. Homebrew's node writes one that
# sets prefix alone. The runner reads the file of the npm the legs find on their PATH, refuses the run when it sets any
# key but prefix, and records its presence and sha256 (npm_builtin).
NPM_BUILTIN = "npmrc"
NPM_BUILTIN_KEYS = ("prefix",)
# The box floor, which CI does not need: every port variable the tree reads is set to a dead port, so leg code its own
# suite does not floor cannot reach a live manager, kernel, dashboard or postal bus on this machine (each falls back to
# the live deployment's port when unset). XDG_STATE_HOME, the state root, is private per run (leg_sets).
# tests/test_sweep_runner.py's census derives the port names from the tree: each is here or in PORT_DEFAULTS.
PORT_FLOOR = {"ROMP_MANAGER_PORT": "1", "ROMP_KERNEL_PORT": "1", "ROMP_SERVE_PORT": "1", "ROMP_POSTAL_PORT": "1"}
# Port variables the floor need not set, each with the floored variable it defaults to.
PORT_DEFAULTS = {"ROMP_REMOTE_KERNEL_PORT": "ROMP_KERNEL_PORT"}
# Per leg: the switches CI sets on the matching steps (the Run pytest step's SDK switch for pytest, the Run bats step's
# two for bats), so a skip that CI would count as a failure counts here too; and the box rule's heap cap for npm test, a
# difference from CI, which sets none. The served leg's switches are not here: they are read from ci.yml's served step
# at the swept sha (read_served_step), never restated.
LEG_ENV = {
    # ROMP_SDK_REQUIRE is the Run pytest step's: the leg's interpreter has the SDK at ci.yml's pin, so the pin test
    # fails, naming the interpreter, where it does not import.
    "pytest": {"ROMP_SDK_REQUIRE": "1"},
    "bats": {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"},
    "npm-test": {"NODE_OPTIONS": "--max-old-space-size=8192"},
}
# The allowlist applies after --wrap: argv is the wrap, then `env -i NAME=VALUE ...`, then the leg's command, so the
# wrap runs with the runner's environment and nothing it sets reaches the leg.
ENV_BIN = "/usr/bin/env"
# The tools whose versions a result records (found on the leg's PATH), with the argument that prints the version.
TOOL_VERSION_ARGS = (("node", "--version"), ("npm", "--version"), ("bats", "--version"), ("git", "--version"),
                     ("gitleaks", "version"))
# The box rule's TMPDIR shape (tests/test_tempdir_hygiene.py, SWEEP_TMPDIR_TEMPLATE): short, because the deepest
# session-host socket path the harness mints under it must fit sun_path.
TMPDIR_PARENT, TMPDIR_PREFIX, TMPDIR_TAIL = "/tmp", "sweep-", 6
WORKERS_MIN, WORKERS_MAX = 2, 10


class Refused(Exception):
    """The runner refuses to start: exit 2, and no result is written."""


# ── where results live ───────────────────────────────────────────────────────

def state_dir(env=None):
    """ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp; an empty value reads as unset, as in
    bin/romp's ${ROMP_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/romp}."""
    env = os.environ if env is None else env
    if env.get("ROMP_STATE_DIR"):
        return env["ROMP_STATE_DIR"]
    base = env.get("XDG_STATE_HOME") or os.path.join(env.get("HOME") or os.path.expanduser("~"), ".local", "state")
    return os.path.join(base, "romp")


def state_dir_source(env=None):
    """The variable state_dir took the state dir from, for a message: ROMP_STATE_DIR, XDG_STATE_HOME, or HOME
    when neither is set."""
    env = os.environ if env is None else env
    if env.get("ROMP_STATE_DIR"):
        return "ROMP_STATE_DIR"
    if env.get("XDG_STATE_HOME"):
        return "XDG_STATE_HOME"
    return "HOME, with ROMP_STATE_DIR and XDG_STATE_HOME unset"


def sweeps_dir(env=None):
    return os.path.join(state_dir(env), "sweeps")


def result_path(sha, env=None):
    return os.path.join(sweeps_dir(env), sha + ".json")


def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short(sha):
    return (sha or "")[:10]


def write_result(path, data):
    """Through a temp file and os.replace, so a reader never sees half a file."""
    d = os.path.dirname(path)
    os.makedirs(d, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".sweep-", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=1, sort_keys=True)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ── the rules: which legs are owed, and the verdict ─────────────────────────

def excuse_fault(name, leg):
    """Why a leg's not-owed mark is one the runner never writes, or None: a leg of ALWAYS_OWED marked not
    owed, another leg marked not owed with no reason, or marked not owed for any reason but the one the runner gives for
    it (NOT_OWED_WHY): deps, a webview leg or served (EXTENSION_LEGS) for any reason but NO_PACKAGE_JSON (every checkout
    is fresh, so deps is owed wherever the sha has vscode-extension/package.json, and every head owes the webview legs
    and served whatever its diff), and the ledger for any reason but NO_LEDGER_SCRIPT (round 2, correctness-4)."""
    if not (isinstance(leg, dict) and leg.get("owed") is False):
        return None
    if name in ALWAYS_OWED:
        return "%s marked not owed" % name
    why = leg.get("why")
    if not (isinstance(why, str) and why.strip()):
        return "%s marked not owed with no reason" % name
    own = NOT_OWED_WHY.get(name)
    if own is not None and why != own:
        return "%s marked not owed for a reason other than %r (%r)" % (name, own, why)
    return None


def is_owed(name, leg):
    """A leg counts as not owed only when its record says so in as many words, with a reason, and it is not one
    of ALWAYS_OWED; anything else is owed."""
    return not (isinstance(leg, dict) and leg.get("owed") is False) or excuse_fault(name, leg) is not None


def _count(value):
    """A recorded count as an int, or None (a bool is not a count)."""
    return value if type(value) is int else None


def passed(name, leg):
    """rc is the integer 0, and for a test leg (TEST_LEGS) its log showed at least one test passing and none
    failing: an rc of 0 alone is also what a wrapper that never ran its command returns. Both counts must be
    integers, and the failed count is required whenever the leg has a test count (the runner writes the two
    together): a failed count that is missing, not an int (a string, a float, a bool) or negative reads as not
    passed, never as zero failures (round 1, extra5-6)."""
    rc = leg.get("rc") if isinstance(leg, dict) else None
    if not (type(rc) is int and rc == 0):
        return False
    if name in TEST_LEGS:
        tests, failed = _count(leg.get("tests")), _count(leg.get("failed"))
        return tests is not None and tests > 0 and failed is not None and failed == 0
    return True


def verdict_of(result):
    """The one verdict rule, for the writer and the reader alike: running until finished, invalid when the run
    says so, red when an owed leg of LEGS has an rc other than 0 or none, or is a test leg whose log counted no
    passing test or a failing one; pass otherwise."""
    if not result.get("finished"):
        return "running"
    if result.get("invalid"):
        return "invalid"
    legs = result.get("legs") or {}
    if any(is_owed(name, legs.get(name)) and not passed(name, legs.get(name)) for name in LEGS):
        return "red"
    return "pass"


def run_verdict(run):
    """One run's own verdict over its own legs: running until finished, invalid when the run says so, else red when
    an owed leg of it did not pass (a full run's roster is LEGS, so a leg it lacks is owed; a --leg re-run's is the
    legs it ran), else pass."""
    if not run.get("finished"):
        return "running"
    if run.get("invalid"):
        return "invalid"
    legs = run.get("legs") or {}
    names = LEGS if run.get("kind") == "full" else [n for n in LEGS if n in legs]
    return "red" if any(is_owed(n, legs.get(n)) and not passed(n, legs.get(n)) for n in names) else "pass"


def effective(data):
    """(the record the verdict is read from, or None, and the reason when it is None). The file keeps every run at the
    sha, oldest first (`runs`, append-only); the record is the newest full run with every later --leg re-run's legs
    laid over it. It carries the result's sha, branch and tree, the full run's start, the newest run's finish (None
    while that run is still going), the first invalid reason among those runs, and the newest run's runner."""
    runs = data.get("runs") or []
    fulls = [i for i, r in enumerate(runs) if r.get("kind") == "full"]
    if not fulls:
        return None, "it records no full run"
    for i, r in enumerate(runs):
        if r.get("kind") not in ("full", "leg"):
            return None, "run %d is of no kind the runner writes (%r)" % (i + 1, r.get("kind"))
    f = fulls[-1]
    legs = {n: dict(rec) for n, rec in (runs[f].get("legs") or {}).items()}
    for r in runs[f + 1:]:
        for n, rec in (r.get("legs") or {}).items():
            legs[n] = dict(rec)
    invalid = next((r.get("invalid") for r in runs[f:] if r.get("invalid")), None)
    return {"sha": data.get("sha"), "branch": data.get("branch"), "tree": data.get("tree"), "started": runs[f].get("started"),
            "finished": runs[-1].get("finished"), "legs": legs, "invalid": invalid, "runner": runs[-1].get("runner"),
            "runs": runs, "full_run": f + 1}, None


def read_history(runs):
    """What the whole history at one sha says, read over every finished leg attempt of every run. Invalidity voids a
    run's passes, never its failures (round 2, Class A): in an invalid run each finished, owed leg that did not pass is
    an attempt, a failure, whatever else happened in the run, the leg whose re-read made the run invalid included, and
    the run's passes are dropped, since its checkout or a venv changed and a pass there proves nothing. An invalid run
    that failed no leg needs no flake and is only named (round 1 decision 18 stands for it). The never-checks stay off
    for an invalid run: a flake it names for a leg after the invalidating one, which never ran, is a record the runner
    does write. A leg is read by its own finished stamp, not its run's, so a stopped run's finished legs count too.
      never    the records no runner writes: a --leg re-run with no known flake named for a leg it ran, a flake
               named for a leg the run did not run or that had no failed run before it at this sha;
      dead     why no run at this sha can pass any more: a leg that failed in two runs (a known flake is excused once),
               or a failed run whose leg a later run passed without --flake naming it;
      need     {leg: (run number, record)} for each leg whose newest attempt failed: the next run that runs it counts
               only with --flake naming it and its known-flake entry;
      flaked   [(leg, failed run number, failed record, flake)] for each failure a later run's flake excused;
      invalid  [(run number, started, reason, [(leg, record)])] for each invalid run, with the legs it failed."""
    out = {"never": [], "dead": None, "need": {}, "flaked": [], "invalid": []}
    attempts = {n: [] for n in LEGS}
    for i, run in enumerate(runs):
        num = i + 1
        legs = run.get("legs") or {}
        flakes = run.get("flakes") or {}
        if not isinstance(flakes, dict):
            out["never"].append("run %d's flakes are not a mapping of leg to known flake" % num)
            flakes = {}
        ran = [n for n in LEGS if n in legs and is_owed(n, legs[n]) and legs[n].get("finished")]
        if run.get("invalid"):
            failed = [n for n in ran if not passed(n, legs[n])]
            out["invalid"].append((num, run.get("started"), run.get("invalid"), [(n, legs[n]) for n in failed]))
            for n in failed:
                flake = flakes.get(n)
                attempts[n].append((num, False, flake if isinstance(flake, str) and flake.strip() else None, legs[n]))
            continue
        for n in flakes if run.get("finished") else ():
            if n not in ran:
                out["never"].append("run %d names a known flake for %s, which it did not run" % (num, n))
        if run.get("kind") == "leg":
            for n in [n for n in LEGS if n in legs]:
                if not (isinstance(flakes.get(n), str) and flakes[n].strip()):
                    out["never"].append("run %d re-ran %s with no known flake named" % (num, n))
        for n in ran:
            flake = flakes.get(n)
            attempts[n].append((num, passed(n, legs[n]), flake if isinstance(flake, str) and flake.strip() else None, legs[n]))
    for n in LEGS:
        seq = attempts[n]
        fails = [a for a in seq if not a[1]]
        if len(fails) >= 2 and not out["dead"]:
            out["dead"] = ("%s failed in runs %s; a known flake is excused once (--flake), so no run at this sha can pass "
                           "(logs: %s)" % (n, " and ".join(str(a[0]) for a in fails), ", ".join(str(a[3].get("log")) for a in fails)))
        for k, (num, ok, flake, rec) in enumerate(seq):
            if flake is not None and (k == 0 or seq[k - 1][1]):
                out["never"].append("run %d names a known flake for %s, but %s has no failed run before it at this sha"
                                    % (num, n, n))
            if not ok and k + 1 < len(seq):
                nnum, nok, nflake, _nrec = seq[k + 1]
                if nok and nflake is not None:
                    out["flaked"].append((n, num, rec, nflake))
                elif nok and not out["dead"]:
                    out["dead"] = ("run %d failed %s (%s; log %s), and run %d passed it with no --flake naming it; a later run "
                                   "turns a failed leg green only with --flake naming the leg and its known-flake entry"
                                   % (num, n, _rc_text(n, rec), rec.get("log"), nnum))
        if seq and not seq[-1][1]:
            out["need"][n] = (seq[-1][0], seq[-1][3])
    return out


def flake_notes(history):
    """The pass line's words for each failure a later run's flake excused: the failed run and the flake."""
    return ["%s re-run after a known flake (first run %s; flake: %s)" % (n, _rc_text(n, rec), flake.strip())
            for n, _num, rec, flake in history["flaked"]]


def failures_text(failed):
    """[(leg, record)] of the legs an invalid run failed, in words: each leg with its rc and its log."""
    return ", ".join("%s (%s; log %s)" % (n, _rc_text(n, rec), rec.get("log")) for n, rec in failed)


def invalid_notes(history):
    """The pass line's words for each invalid run in the history, naming each leg it failed, whose failure counts (an
    invalid run that failed no leg needs no flake, but it is named)."""
    return ["run %d (started %s) was invalid: %s%s" % (num, started, reason,
                                                       ("; its failures count: " + failures_text(failed)) if failed else "")
            for num, started, reason, failed in history["invalid"]]


def red_legs(result):
    legs = result.get("legs") or {}
    return [name for name in LEGS if is_owed(name, legs.get(name)) and not passed(name, legs.get(name))]


def _rc_text(name, leg):
    rc = leg.get("rc") if isinstance(leg, dict) else None
    if rc is None:
        err = leg.get("error") if isinstance(leg, dict) else None
        return "no rc" + (": %s" % err if err else "")
    if type(rc) is int and rc == 0 and name in TEST_LEGS and not passed(name, leg):
        tests, failed = leg.get("tests"), leg.get("failed")
        if tests is not None and not (type(tests) is int and tests >= 0):
            return "rc 0 but its test count is malformed (tests %r)" % (tests,)
        if not (type(tests) is int and tests > 0):
            return "rc 0 but no test ran"
        if failed is None:
            return "rc 0 but it records no failed count"
        if not (type(failed) is int and failed >= 0):
            return "rc 0 but its failed count is malformed (failed %r)" % (failed,)
        return "rc 0 but its log shows %d failed" % failed
    return "rc %s" % rc


# ── the reader (scripts/batch.py calls assess) ───────────────────────────────

SCHEMA_1_TEXT = "recorded by a runner that swept the batcher's own tree"


def checkout_recorded(run):
    """Whether a run records the private clone its legs ran in (runner.checkout, form "clone"), as every run of this
    runner does before its first write. A schema-2 run without one came from a runner that swept the batcher's own tree
    (this branch's intermediate runners wrote schema 2 before the private checkout existed), so no reader counts it."""
    runner = run.get("runner") if isinstance(run, dict) else None
    co = runner.get("checkout") if isinstance(runner, dict) else None
    return isinstance(co, dict) and co.get("form") == "clone"


def no_checkout_runs(runs):
    """The numbers of the runs that record no private checkout (checkout_recorded)."""
    return [i + 1 for i, r in enumerate(runs) if not checkout_recorded(r)]


def _load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    if not isinstance(data.get("legs", {}), dict) or not all(isinstance(v, dict) for v in data.get("legs", {}).values()):
        raise ValueError("its legs are not a mapping of leg records")
    if "runs" in data or data.get("schema") == SCHEMA:
        runs = data.get("runs")
        if not isinstance(runs, list) or not runs or not all(isinstance(r, dict) for r in runs):
            raise ValueError("its runs are not a list of run records")
        for i, r in enumerate(runs):
            legs = r.get("legs", {})
            if not isinstance(legs, dict) or not all(isinstance(v, dict) for v in legs.values()):
                raise ValueError("run %d's legs are not a mapping of leg records" % (i + 1))
    return data


def _started_finished(data):
    """(started, finished) of a result's newest run (schema 2), or of the result itself (an older schema)."""
    runs = data.get("runs")
    if isinstance(runs, list) and runs and isinstance(runs[-1], dict):
        return runs[-1].get("started"), runs[-1].get("finished")
    return data.get("started"), data.get("finished")


def newest_for_branch(branch, env=None):
    """(path, result) of the newest readable result recorded for `branch`, by its newest run's start stamp;
    (None, None)."""
    d = sweeps_dir(env)
    best = (None, None)
    try:
        names = os.listdir(d)
    except OSError:
        return best
    for name in names:
        if not re.fullmatch(r"[0-9a-f]{40}\.json", name):
            continue
        try:
            data = _load(os.path.join(d, name))
        except (OSError, ValueError):
            continue
        if data.get("branch") == branch and (best[1] is None or str(_started_finished(data)[0]) > str(_started_finished(best[1])[0])):
            best = (os.path.join(d, name), data)
    return best


def assess(sha, subject="the batch head", branch=None, tree_hint=None, env=None):
    """Read the result for `sha` and name its case: {"case", "line", "path", "result"}. The case is pass, or one of
    missing, stale, unfinished, red, invalid, incomplete, unreadable; `line` is the text a caller prints after
    "ok   " or "FAIL ". Stale is decided on the full sha only; `branch` lets a missing result for sha be told apart
    from a stale one recorded for the same branch at another sha. `result` is the record the verdict was read from
    (effective(): the newest full run with its later --leg re-runs laid over it), with `flake_notes` and
    `invalid_notes` naming what the whole history excused and what it held invalid."""
    path = result_path(sha, env)
    out = {"case": None, "line": None, "path": path, "result": None}

    def done(case, line, result=None):
        out.update(case=case, line=line, result=result)
        return out

    if not os.path.exists(path):
        if branch:
            opath, other = newest_for_branch(branch, env)
            if other is not None and other.get("sha") != sha:
                return done("stale", "sweep stale: the newest result for %s is at %s (finished %s), %s is at %s; sweep again "
                                     "at %s" % (branch, short(other.get("sha")), _started_finished(other)[1] or "never", subject,
                                                short(sha), subject))
        # The directory read is named with where it came from: the runner writes under the state dir ITS environment
        # names, so a result written with another ROMP_STATE_DIR or XDG_STATE_HOME is missing here.
        hint = " --tree %s" % tree_hint if tree_hint else ""
        d = sweeps_dir(env)
        return done("missing", "sweep missing: no result for %s %s in %s (the state dir from %s%s); run `scripts/sweep.py "
                               "run%s` with the same ROMP_STATE_DIR and XDG_STATE_HOME as this reader, or its result goes to "
                               "another directory" % (subject, sha, d, state_dir_source(env),
                                                      "" if os.path.isdir(d) else "; the directory does not exist", hint))
    try:
        data = _load(path)
    except (OSError, ValueError) as e:
        return done("unreadable", "sweep unreadable: %s: %s; sweep again" % (path, e))
    if type(data.get("schema")) is int and data.get("schema") == 1:
        return done("unreadable", "sweep unreadable: %s: schema 1, %s; sweep again with this checkout's scripts/sweep.py"
                    % (path, SCHEMA_1_TEXT), data)
    if type(data.get("schema")) is not int or data.get("schema") != SCHEMA:
        return done("unreadable", "sweep unreadable: %s: schema %r, and this reader reads schema %d; sweep again with this "
                                  "checkout's scripts/sweep.py" % (path, data.get("schema"), SCHEMA), data)
    if data.get("sha") != sha:
        return done("stale", "sweep stale: %s records sha %s, not %s %s; sweep again at %s"
                    % (path, short(str(data.get("sha"))), subject, short(sha), subject), data)
    rec, why = effective(data)
    never = "sweep invalid at %s: %s, which the runner never records; sweep again with this checkout's scripts/sweep.py"
    if rec is None:
        return done("invalid", never % (short(sha), why), data)
    runs = data["runs"]
    at = [(i + 1, r.get("sha")) for i, r in enumerate(runs) if r.get("sha") != sha]
    if at:
        return done("invalid", never % (short(sha), "; ".join("run %d was recorded at %s" % (n, s if isinstance(s, str) else repr(s))
                                                              for n, s in at)), rec)
    legs = rec["legs"]
    absent = [name for name in LEGS if name not in (runs[rec["full_run"] - 1].get("legs") or {})]
    if absent:
        return done("incomplete", "sweep incomplete at %s: no %s leg in %s; sweep again with this checkout's scripts/sweep.py"
                    % (short(sha), ", ".join(absent), path), rec)
    faulty = [name for name in LEGS if excuse_fault(name, legs[name])]
    if faulty:
        # One clause for the legs of ALWAYS_OWED, one per reason for the others (the three webview legs marked not owed
        # for one reason read as one clause naming the three), each naming the one reason the runner gives for those
        # legs (NOT_OWED_WHY; round 2, correctness-4), and each leg with no reason on its own.
        always = [n for n in faulty if n in ALWAYS_OWED]
        text = ["%s marked not owed" % ", ".join(always)] if always else []
        by_why = {}
        for n in faulty:
            why = legs[n].get("why")
            if n in ALWAYS_OWED:
                continue
            if isinstance(why, str) and why.strip():
                by_why.setdefault((NOT_OWED_WHY[n], why), []).append(n)
            else:
                text.append(excuse_fault(n, legs[n]))
        text += ["%s marked not owed for a reason other than %r (%r)" % (", ".join(names), own, why)
                 for (own, why), names in by_why.items()]
        return done("invalid", "sweep invalid at %s: %s, which the runner never records (%s always run; deps, the webview "
                               "legs and served are owed at every head that has vscode-extension/package.json, whatever its "
                               "diff, and the ledger at every head that has %s); sweep again with this checkout's "
                               "scripts/sweep.py" % (short(sha), "; ".join(text), ", ".join(ALWAYS_OWED), LEDGER_SCRIPT), rec)
    history = read_history(runs)
    rec.update(flake_notes=flake_notes(history), invalid_notes=invalid_notes(history))
    if history["never"]:
        return done("invalid", "sweep invalid at %s: %s; a later run counts over a failed one only with --flake naming the "
                               "leg and its known-flake entry, once per leg; the runner adds no run to a result holding such "
                               "records (results are append-only): move it aside to sweep this sha again"
                    % (short(sha), "; ".join(history["never"])), rec)
    stray = sorted(set(recorded_hash(r) for r in runs[rec["full_run"] - 1:]) - {policy_hash()}, key=str)
    if stray:
        recorded = stray[0]
        return done("invalid", "sweep invalid at %s: recorded under another leg environment (hash %s; this reader's is %s: "
                               "another scripts/sweep.py's allowlist or set values), so it is not this gate; sweep again with "
                               "this checkout's scripts/sweep.py" % (short(sha), str(recorded)[:12] if recorded else "none",
                                                                     policy_hash()[:12]), rec)
    blind = no_checkout_runs(runs)
    if blind:
        return done("unreadable", "sweep unreadable: %s: run %s records no private checkout, so it was %s; sweep again with "
                                  "this checkout's scripts/sweep.py, which moves the file aside"
                    % (path, ", ".join(str(n) for n in blind), SCHEMA_1_TEXT), rec)
    recomputed = verdict_of(rec)
    if recomputed == "running":
        ran = [name for name in LEGS if (runs[-1].get("legs") or {}).get(name, {}).get("finished")]
        return done("unfinished", "sweep unfinished: the sweep at %s started %s and has not finished (running, or its runner "
                                  "died; done: %s); wait for it or sweep again" % (short(sha), runs[-1].get("started"),
                                                                                    ", ".join(ran) or "none"), rec)
    for i, r in enumerate(runs):
        if r.get("finished") and r.get("verdict") != run_verdict(r):
            return done("invalid", "sweep invalid at %s: the recorded verdict %s disagrees with its legs (%s) in run %d"
                        % (short(sha), r.get("verdict"), run_verdict(r), i + 1), rec)
    logs = os.path.join(sweeps_dir(env), "logs", sha)
    # Round 2, Class A: a history that leaves the sha unable to pass reads red before the newest run's invalid, so a
    # second failure inside an invalid run reads red naming both runs, and the runner exits 1 for such a run.
    if history["dead"]:
        return done("red", "sweep red at %s: %s; fix it and sweep the new head; logs under %s" % (short(sha), history["dead"], logs), rec)
    if recomputed == "invalid":
        # the run the record's invalid reason came from (effective(): the first invalid run from the newest full run
        # on), with every leg it failed, since those failures count
        num = next(i + 1 for i in range(rec["full_run"] - 1, len(runs)) if runs[i].get("invalid"))
        failed = next(f for n, _s, _r, f in history["invalid"] if n == num)
        counted = "; run %d's failures count: %s" % (num, failures_text(failed)) if failed else ""
        return done("invalid", "sweep invalid at %s: %s%s" % (short(sha), rec.get("invalid"), counted), rec)
    if recomputed == "red":
        return done("red", "sweep red at %s: %s; logs under %s" % (
            short(sha), ", ".join("%s (%s)" % (n, _rc_text(n, legs[n])) for n in red_legs(rec)), logs), rec)
    unrun = sorted(n for n in history["need"] if not is_owed(n, legs[n]))
    if unrun:
        return done("red", "sweep red at %s: %s; logs under %s" % (short(sha), "; ".join(
            "%s failed in run %d (%s) and no later run ran it" % (n, history["need"][n][0], _rc_text(n, history["need"][n][1]))
            for n in unrun), logs), rec)
    ran = ["%s %s" % (n, legs[n]["rc"]) for n in LEGS if is_owed(n, legs[n])]
    skipped = [n for n in LEGS if not is_owed(n, legs[n])]
    notes = rec["flake_notes"] + (["an earlier " + t for t in rec["invalid_notes"]])
    return done("pass", "sweep at %s: pass, finished %s (%s%s%s); %s" % (
        short(sha), rec.get("finished"), ", ".join(ran), ("; not owed: " + ", ".join(skipped)) if skipped else "",
        ("; " + "; ".join(notes)) if notes else "", path), rec)


def excuse_contradiction(tree, result, sha, subject="HEAD"):
    """The legs a result marks not owed for the one reason the runner gives for them (NOT_OWED_WHY: deps, the webview
    legs and served for having no vscode-extension/package.json, round 1's excuse rule, and the ledger for having no
    scripts/upstream-ledger.py, round 2's correctness-4) while the sha's tree does hold the file that reason names, as a
    line naming them and the file; None when none is so marked or the tree really has no such file. Read with the
    runner's own git hygiene (no inherited GIT_*, no global or system config, refs/replace ignored). batch.py's verify,
    plan and --repin and this script's check apply it after a pass."""
    legs = (result or {}).get("legs") or {}
    clauses = []
    for why, rel in NOT_OWED_FILE.items():
        excused = [n for n in LEGS if not is_owed(n, legs.get(n)) and (legs.get(n) or {}).get("why") == why]
        if not excused:
            continue
        p = subprocess.run(["git", "-C", tree, "cat-file", "-e", "%s:%s" % (sha, rel)], env=_git_env(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if p.returncode == 0:
            clauses.append("marks %s not owed for having %s, but %s's tree holds %s" % (", ".join(excused), why, subject, rel))
    if not clauses:
        return None
    return ("sweep invalid at %s: the result %s; sweep again with this checkout's scripts/sweep.py"
            % (short(sha), "; and it ".join(clauses)))


# ── the runner ────────────────────────────────────────────────────────────────

# Every git call the runner makes (the sha read, the uncommitted-edits notice's git status in the batcher's tree, the
# clone, the checkout, the verification) runs with every GIT_* variable of its environment removed and git's global and
# system configuration off, so no inherited GIT_DIR, GIT_CONFIG_*, GIT_TEMPLATE_DIR or config file changes what it
# reads; refs/replace is ignored; and the per-user attributes and excludes files git reads by default
# (~/.config/git/attributes and ignore) are pointed at an empty file, since a global `* text eol=crlf` there would change
# what a checkout writes, and a directory rule in the ignore file would shadow a tracked .gitignore's rule in the re-read
# after a leg. fsmonitor and the untracked cache are off, over the repository's own config too: the notice's git status
# runs in the batcher's repository, whose config could name an fsmonitor hook or turn the untracked cache on.
GIT_NEUTRAL = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1"}
GIT_NEUTRAL_CONFIG = (("core.attributesFile", os.devnull), ("core.excludesFile", os.devnull), ("core.fsmonitor", "false"),
                      ("core.untrackedCache", "false"))


def _git_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_NEUTRAL)
    env["GIT_CONFIG_COUNT"] = str(len(GIT_NEUTRAL_CONFIG))
    for i, (key, value) in enumerate(GIT_NEUTRAL_CONFIG):
        env["GIT_CONFIG_KEY_%d" % i], env["GIT_CONFIG_VALUE_%d" % i] = key, value
    return env


def git(tree, *args, check=True):
    p = subprocess.run(["git", "-C", tree, *args], env=_git_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise Refused("git %s failed in %s: %s" % (" ".join(args), tree, (p.stderr or p.stdout).strip()))
    return p.stdout.strip() if check else p


def uncommitted_count(tree):
    """How many entries `git status --porcelain=v1 --untracked-files=all` lists in the batcher's tree, or None when git
    status fails. Only a notice reads it: the legs run in a private checkout of the sha, so these edits are not swept.
    It runs with the runner's neutral git like every other runner git call (_git_env; round 2, fresh-4), so no
    core.fsmonitor hook or untracked-cache setting of the batcher's configuration runs or writes in their repository;
    with the per-user excludes file off, the count includes files only the batcher's global excludes hide, which are
    not swept either."""
    p = subprocess.run(["git", "-C", tree, "status", "--porcelain=v1", "-z", "--untracked-files=all"], env=_git_env(),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        return None
    return len(_status_entries(p.stdout))


def _status_entries(out):
    """[(XY, path bytes)] of `git status --porcelain=v1 -z` output; a rename's or copy's source path is skipped."""
    parts, entries, i = out.split(b"\0"), [], 0
    while i < len(parts):
        chunk = parts[i]
        i += 1
        if len(chunk) < 4:
            continue
        xy = chunk[:2].decode("ascii", "replace")
        entries.append((xy, chunk[3:]))
        if xy[0] in "RC":
            i += 1
    return entries


# -- the checkout: a private clone of the exact sha (round 1, Class A) --

def trees_dir(env=None):
    return os.path.join(sweeps_dir(env), "trees")


def _random_tail(n=8):
    rng = random.SystemRandom()
    return "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def make_checkout(tree, sha):
    """(path, marker, seconds): `git clone -q --shared --no-checkout` of the batcher's repository (its common dir) into
    <state dir>/sweeps/trees/<sha12>-<random>, then `checkout -q --detach <sha>` there with hooks off. A clone copies
    none of the batcher's repository config, info/attributes, info/exclude, hooks, sparse patterns, index flags or
    refs/replace, and a leg's git writes land in the clone. The marker beside it, written first, holds the full sha,
    so a later run can tell whether that sha's lock is held (sweep_stale_checkouts). Any exception between the marker's
    create and the end of the checkout, the Stopped of a stop signal included, removes the partial checkout and its
    marker before it propagates (round 2, extra5-2)."""
    parent = trees_dir()
    os.makedirs(parent, mode=0o700, exist_ok=True)
    common = git(tree, "rev-parse", "--git-common-dir")
    common = common if os.path.isabs(common) else os.path.abspath(os.path.join(tree, common))
    t0 = time.monotonic()
    path = marker = None
    try:
        # Round 2, extra5-2: from the marker's exclusive create to the end of the checkout, any exception, a stop signal's
        # Stopped included, removes the partial checkout and its marker before it propagates; the caller holds neither
        # until this returns.
        for _ in range(100):
            name = "%s-%s" % (sha[:12], _random_tail())
            candidate = os.path.join(parent, name + ".sha")
            try:
                fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                continue
            marker = candidate
            with os.fdopen(fd, "w") as f:
                f.write(sha + "\n")
            break
        else:
            raise Refused("could not name a checkout under %s" % parent)
        path = os.path.join(parent, name)
        p = subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", common, path], env=_git_env(), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode == 0:
            p = git(path, "-c", "core.hooksPath=" + os.devnull, "checkout", "-q", "--detach", sha, check=False)
        if p.returncode != 0:
            raise Refused("could not check %s out into a private clone: %s" % (short(sha), (p.stderr or p.stdout).strip()))
    except BaseException:
        remove_checkout(path, marker)
        raise
    return path, marker, round(time.monotonic() - t0, 2)


def remove_checkout(path, marker):
    if path:
        shutil.rmtree(path, ignore_errors=True)
    if marker:
        try:
            os.remove(marker)
        except OSError:
            pass


def _lock_held(sha, own_sha):
    """Whether a run of `sha` holds its per-sha lock now. This run holds its own, so an earlier checkout of the same sha
    is a dead run's."""
    if sha == own_sha:
        return False
    path = os.path.join(sweeps_dir(), sha + ".lock")
    if not os.path.exists(path):
        return False
    with open(path) as f:
        try:
            fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


def sweep_stale_checkouts(own_sha):
    """Remove every checkout under <state dir>/sweeps/trees whose sha's lock no run holds, whatever its sha (a killed
    run's checkout is several hundred MB), and name each one; [(path, sha)] removed. A checkout with no readable
    marker is judged by the locks of every sha its 12-character prefix names."""
    parent = trees_dir()
    try:
        names = sorted(os.listdir(parent))
    except OSError:
        return []
    removed = []
    for name in names:
        full = os.path.join(parent, name)
        if name.endswith(".sha"):
            if not os.path.isdir(full[:-len(".sha")]) and not _lock_held(_read_marker(full) or "", own_sha):
                remove_checkout(None, full)
            continue
        if os.path.islink(full) or not os.path.isdir(full):
            continue
        sha = _read_marker(full + ".sha")
        if sha:
            held = _lock_held(sha, own_sha)
        else:
            prefix = name.split("-", 1)[0]
            locks = [n[:-len(".lock")] for n in _listdir(sweeps_dir()) if n.endswith(".lock") and n.startswith(prefix)]
            held = any(_lock_held(s, own_sha) for s in locks)
        if held:
            continue
        remove_checkout(full, full + ".sha")
        removed.append((full, sha))
        print("sweep: removed a stale checkout %s (%s), left by a run that is no longer running"
              % (full, short(sha) if sha else "no sha recorded"), flush=True)
    return removed


def _listdir(d):
    try:
        return os.listdir(d)
    except OSError:
        return []


def _read_marker(path):
    try:
        with open(path) as f:
            text = f.read().strip()
    except OSError:
        return None
    return text if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", text) else None


def tree_entries(path, sha):
    """{path bytes: (mode, oid)} of every entry `git ls-tree -r -z <sha>` lists (files, symlinks, gitlinks)."""
    p = subprocess.run(["git", "-C", path, "ls-tree", "-r", "-z", sha], env=_git_env(), stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise Refused("git ls-tree failed in the checkout of %s: %s" % (short(sha), p.stderr.decode("utf-8", "replace").strip()))
    entries = {}
    for rec in p.stdout.split(b"\0"):
        if rec:
            meta, name = rec.split(b"\t", 1)
            mode, _typ, oid = meta.split()
            entries[name] = (mode, oid.decode("ascii"))
    return entries


def _blob_id(data, oid):
    """The git blob id of `data` in the object format `oid` is written in (40 hex digits sha1, 64 sha256): what
    `git hash-object --no-filters` gives for a file holding those bytes."""
    h = hashlib.new("sha1" if len(oid) == 40 else "sha256")
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def _entry_faults(path, entries):
    """{class: [paths]} for the tracked entries: missing (absent, or a gitlink that is not a directory), content (a
    regular file whose bytes are not the blob's, or a path that is no longer a file), mode (the executable bit), symlink
    (a symlink whose target differs, or one checked out as anything else, or a file that became a symlink)."""
    root = os.fsencode(path)
    out = {"missing": [], "content": [], "mode": [], "symlink": []}
    for name, (mode, oid) in entries.items():
        full = os.path.join(root, name)
        try:
            st = os.lstat(full)
        except OSError:
            out["missing"].append(name)
            continue
        if mode == b"160000":
            if not stat.S_ISDIR(st.st_mode):
                out["missing"].append(name)
            continue
        if mode == b"120000":
            if not stat.S_ISLNK(st.st_mode) or _blob_id(os.readlink(full), oid) != oid:
                out["symlink"].append(name)
            continue
        if not stat.S_ISREG(st.st_mode):
            out["symlink" if stat.S_ISLNK(st.st_mode) else "content"].append(name)
            continue
        if bool(st.st_mode & 0o100) != (mode == b"100755"):
            out["mode"].append(name)
        with open(full, "rb") as f:
            if _blob_id(f.read(), oid) != oid:
                out["content"].append(name)
    return out


def _disk_paths(path):
    """Every file and symlink under the checkout (the clone's own .git excluded), as path bytes relative to it."""
    root = os.fsencode(path)
    found = set()
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root)
        if rel == b".":
            dirs[:] = [x for x in dirs if x != b".git"]
            files = [x for x in files if x != b".git"]
        for x in list(dirs):
            if os.path.islink(os.path.join(d, x)):
                files.append(x)
                dirs.remove(x)
        for x in files:
            found.add(os.path.normpath(os.path.join(rel, x)))
    return found


def verify_checkout(path, sha, entries):
    """[(class, [paths])] where the fresh checkout differs from the sha's tree: every tracked entry as _entry_faults
    reads it, and any file on disk that is not a tracked entry (extra). Empty: the checkout is the sha's tree."""
    faults = _entry_faults(path, entries)
    faults["extra"] = sorted(_disk_paths(path) - {n for n, (mode, _oid) in entries.items() if mode != b"160000"})
    return [(k, sorted(faults[k])) for k in ("missing", "extra", "content", "mode", "symlink") if faults[k]]


# After the deps leg (npm ci, whose dependencies' install scripts run), the one place an ignored file may appear: every
# other ignored path it could leave would be read by a later leg in its checkout (round 2, extra5-4): bytecode, which
# python loads in place of a source when it is a timestamp pyc whose stamp matches or an unchecked hash-based one, and
# a node_modules or dist tree that node, tsc or esbuild resolve from. An ignored file a leg before deps in its checkout
# left is excused when the deps leg left it as it was (ignored_now); the deps leg is its job's first leg in ci.yml, so
# in its fresh checkout there is none.
DEPS_PRODUCTS = b"vscode-extension/node_modules/"
# The files in the private clone's .git that decide what the runner's own git reads there (its HEAD, its repository
# config, its excludes): a leg that changes one, or replaces .git itself, changes the re-read's verdict.
GIT_STATE_FILES = ("HEAD", "config", os.path.join("info", "exclude"))


def git_state(path):
    """{name: value} for the private clone's .git: its identity (a directory, its device and inode) and the bytes of each
    GIT_STATE_FILES file (None when absent). The re-read after every leg compares it with the one taken before the
    first leg."""
    g = os.path.join(path, ".git")
    try:
        st = os.lstat(g)
    except OSError:
        return {".git": None}
    out = {".git": (stat.S_ISDIR(st.st_mode), st.st_dev, st.st_ino)}
    for name in GIT_STATE_FILES:
        try:
            with open(os.path.join(g, name), "rb") as f:
                out[os.path.join(".git", name)] = f.read()
        except OSError:
            out[os.path.join(".git", name)] = None
    return out


def tracked_ignored(path, entries, paths):
    """(the subset of `paths` a rule of a TRACKED .gitignore ignores, or None when git failed, and git's error). Read with
    `git check-ignore -v -z --no-index --stdin` in the private clone (the runner's git hygiene, per-user excludes off),
    and a match counts only when the rule's source file is a .gitignore the sha tracks (its bytes checked by
    _entry_faults) and the rule is not a negation: a .gitignore a leg wrote, the clone's info/exclude, or a commit made
    in the clone excuses nothing."""
    if not paths:
        return set(), None
    sources = {n for n, (mode, _oid) in entries.items() if mode in (b"100644", b"100755") and os.path.basename(n) == b".gitignore"}
    # A path that starts with ":" reads to git as pathspec magic, which check-ignore refuses; "./" in front keeps it a
    # path, and the name git echoes back is mapped to the path walked.
    asked = {(b"./" + n if n.startswith(b":") else n): n for n in paths}
    p = subprocess.run(["git", "-C", path, "check-ignore", "-v", "-z", "--no-index", "--stdin"], env=_git_env(),
                       input=b"".join(n + b"\0" for n in asked), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode not in (0, 1):
        return None, p.stderr.decode("utf-8", "replace").strip()
    fields = p.stdout.split(b"\0")
    out = set()
    for i in range(0, len(fields) - 3, 4):
        source, _line, pattern, name = fields[i:i + 4]
        if source in sources and not pattern.startswith(b"!"):
            out.add(asked.get(name, name))
    return out, None


def _file_digest(path, rel):
    """What a file under the checkout holds, to tell one a leg changed: a symlink's target, a file's sha256, or None."""
    full = os.path.join(os.fsencode(path), rel)
    try:
        if os.path.islink(full):
            return "link:" + os.fsdecode(os.readlink(full))
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def ignored_now(path, entries):
    """{path: digest} of every ignored file on disk in the checkout now (a file no tracked entry names that a rule of a
    tracked .gitignore ignores, tracked_ignored): read before the deps leg (and a group's npm ci setup), so the re-read
    after it excuses what a leg before it in its checkout left and still counts what npm ci added or changed. Empty
    when git's read fails, which excuses nothing."""
    tracked = {n for n, (mode, _oid) in entries.items() if mode != b"160000"}
    ignored, _err = tracked_ignored(path, entries, sorted(_disk_paths(path) - tracked))
    return {n: _file_digest(path, n) for n in ignored or ()}


def recheck_checkout(path, sha, entries, before, only_under=None, known=None):
    """[(class, [paths])] where the checkout differs from the sha's tree after a leg, read without trusting any state a
    leg could have written: every tracked entry as _entry_faults reads it; every other file on disk, found by the
    runner's own walk (_disk_paths), that no rule of a tracked .gitignore ignores (untracked: a root conftest.py, which
    pytest loads, or a file hidden by a .gitignore a leg wrote, by the clone's info/exclude or by a commit in the
    clone); with `only_under`, an ignored file outside it too (after deps: bytecode, which python loads in place of a
    source, or a node_modules or dist tree that node, tsc or esbuild resolve from), less one `known` (ignored_now before
    the leg) holds as it is now; the
    clone's .git replaced or its HEAD, config or info/exclude changed since
    `before` (git_state); and a name of ANCESTOR_NAMES in an ancestor directory (ancestor). Ignored build products
    (node_modules, dist/, out-tests/, bytecode) are otherwise allowed."""
    faults = _entry_faults(path, entries)
    tracked = {n for n, (mode, _oid) in entries.items() if mode != b"160000"}
    extra = sorted(_disk_paths(path) - tracked)
    ignored, err = tracked_ignored(path, entries, extra)
    if ignored is None:
        faults["untracked"] = [b"(git check-ignore failed: %s)" % os.fsencode(err)] + extra
        ignored = set()
    else:
        faults["untracked"] = [n for n in extra if n not in ignored]
    if only_under is not None:
        faults["ignored outside " + os.fsdecode(only_under).rstrip("/")] = sorted(
            n for n in ignored if not n.startswith(only_under)
            and not (known is not None and n in known and known[n] is not None and known[n] == _file_digest(path, n)))
    now_state = git_state(path)
    faults["git"] = sorted(os.fsencode(k) for k in set(before) | set(now_state) if before.get(k) != now_state.get(k))
    # A name of ANCESTOR_NAMES that appeared above the checkout during the leg (the refusal before the first leg saw
    # none) would reach the legs after it.
    faults["ancestor"] = [os.fsencode(a) for a in ancestor_hits(path)]
    order = ["missing", "content", "mode", "symlink", "untracked"] + [k for k in faults if k.startswith("ignored outside ")] + ["git", "ancestor"]
    return [(k, sorted(faults[k])) for k in order if faults.get(k)]


def describe_faults(faults, shown=3):
    return "; ".join("%s %d (%s%s)" % (k, len(v), ", ".join(os.fsdecode(x) for x in v[:shown]),
                                       ", ..." if len(v) > shown else "") for k, v in faults)


# The names a leg's tools look up in every ancestor directory of the file they work on, so one above the checkout would
# reach a leg from outside the sha: node_modules (node's require() and tsc's default typeRoots, node_modules/@types),
# package.json (node reads the nearest one for a .js file's module type, and esbuild for its fields), tsconfig.json and
# jsconfig.json (esbuild, which vscode-extension/esbuild.js runs with no tsconfig option, takes the nearest one above
# each file it bundles; ui/ has none of its own, so for ui/ files that search leaves the checkout).
ANCESTOR_NAMES = ("node_modules", "package.json", "tsconfig.json", "jsconfig.json")


def ancestor_hits(path):
    """Each path in an ancestor directory of `path` (its real path, up to /) named in ANCESTOR_NAMES, nearest first."""
    hits, d = [], os.path.dirname(os.path.realpath(path))
    while True:
        hits += [os.path.join(d, n) for n in ANCESTOR_NAMES if os.path.lexists(os.path.join(d, n))]
        up = os.path.dirname(d)
        if up == d:
            return hits
        d = up


def _plant_for_tests(path):
    """The test seam round 1 rules for the verification's refusal classes: SWEEP_TEST_PLANT, a JSON list of
    [op, relative path], changes the fresh checkout between its creation and its verification (op: byte, extra,
    missing, mode, symlink-to-file). Whatever it plants, the verification that follows refuses. Every path is read
    before any is applied, and one that resolves outside the checkout (a `..` path, an absolute path, or a symlink that
    leads out), followed through its symlinks or through its directory's alone, is refused, naming it, with nothing
    planted (round 2, extra6-4): outside the checkout the verification cannot see it."""
    spec = os.environ.get("SWEEP_TEST_PLANT")
    if not spec:
        return
    plan = json.loads(spec)
    root = os.path.realpath(path)
    for _op, rel in plan:
        full = os.path.join(path, rel)
        for where in (os.path.realpath(full), os.path.join(os.path.realpath(os.path.dirname(full)), os.path.basename(full))):
            if not where.startswith(root + os.sep):
                raise Refused("SWEEP_TEST_PLANT names %r, which resolves outside the checkout (%s); nothing was planted, run "
                              "or recorded" % (rel, where))
    for op, rel in plan:
        full = os.path.join(path, rel)
        if op == "byte":
            with open(full, "ab") as f:
                f.write(b"!")
        elif op == "extra":
            with open(full, "w") as f:
                f.write("planted\n")
        elif op == "missing":
            os.remove(full)
        elif op == "mode":
            os.chmod(full, os.stat(full).st_mode ^ 0o111)
        elif op == "symlink-to-file":
            target = os.readlink(full)
            os.remove(full)
            with open(full, "w") as f:
                f.write(target)


# -- stopping: signals, process groups and the subreaper (round 1, A5) --

# The signals that stop a run (STOP_SIGNALS): each raises Stopped, so every exit path runs the cleanup and main prints
# "stopped by signal N" and exits 128 + N. SIGINT is one of them (round 2, decision 14), so Ctrl-C stops a run the same
# way instead of raising KeyboardInterrupt, which main does not catch.
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)


class Stopped(BaseException):
    """A stop signal (STOP_SIGNALS) reached the runner: its legs are stopped and TMPDIR and the checkout removed on the
    way out."""

    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def _on_stop(signum, _frame):
    # the first stop signal wins: a second one during the cleanup is ignored
    for s in STOP_SIGNALS:
        signal.signal(s, signal.SIG_IGN)
    raise Stopped(signum)


# Whether install_stop_handlers made this process a child subreaper; wait_leg reads it.
_subreaper = False


def install_stop_handlers():
    """SIGTERM, SIGHUP and SIGINT (STOP_SIGNALS) raise Stopped, so every exit path runs the cleanup, whether or not
    the runner's parent left the signal ignored (nohup ignores SIGHUP, a non-interactive shell's background job
    SIGINT): each of the three stops a run. SIGCHLD gets its default action; and on Linux the runner becomes a child
    subreaper (PR_SET_CHILD_SUBREAPER), so every orphaned descendant of a leg, in its process group or not (setsid:
    Playwright's browsers, the kernel's session scopes), is reparented to the runner instead of to init: the runner
    reaps it as soon as it exits while the leg runs (wait_leg), so it does not stay in the leg's group as a defunct
    process, and kills it if it is still running when the leg ends (reap_descendants).

    An ignored SIGCHLD survives exec, so a parent that ignores it hands the runner a disposition under which the kernel
    reaps every child itself: every exit status, the leg's and each subprocess.run's, would read 0, and wait_leg, which
    blocks until some child is waitable, would wait until the runner had no child left (a leg's daemon kept it waiting
    until it exited). The default action is set here, before the runner starts any child, and the legs inherit it."""
    global _subreaper
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    for s in STOP_SIGNALS:
        signal.signal(s, _on_stop)
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            _subreaper = ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
        except (OSError, AttributeError):
            pass


def _children():
    """The pids whose parent is this process now, read from /proc (Linux); [] where there is none."""
    me, out = os.getpid(), []
    for name in _listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open("/proc/%s/stat" % name, "rb") as f:
                data = f.read()
        except OSError:
            continue
        rest = data[data.rfind(b")") + 2:].split()
        if len(rest) > 1 and rest[1] == str(me).encode():
            out.append(int(name))
    return out


def reap_descendants(timeout=30.0):
    """Kill and reap every child this runner has now (a leg's leftover, or a descendant the subreaper reparented here),
    again and again until none is left or `timeout` passes; the number killed."""
    killed, end = set(), time.monotonic() + timeout
    while True:
        kids = _children()
        for pid in kids:
            try:
                os.kill(pid, signal.SIGKILL)
                killed.add(pid)
            except ProcessLookupError:
                pass
        while True:
            try:
                pid, _status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                pid = 0
            if not pid:
                break
        if not kids or time.monotonic() > end:
            return len(killed)
        time.sleep(0.05)


def wait_leg(p):
    """Wait for the leg `p` to exit and return its exit status, as Popen.wait does, reaping every reparented descendant
    that exits meanwhile; None when the leg's status was lost.

    A subreaper adopts each orphaned descendant of a leg, and an adopted process that exits stays a zombie until the
    runner reaps it. Left for the leg's end, it shows in the leg's process group as a defunct process (the watchdog
    tests in tests/romp-node-launch.bats and tests/romp-service.bats list their group and fail on one), and the
    zombies pile up until the leg ends. So the runner blocks until some child of its has exited, reads which one
    without reaping it (waitid with WNOWAIT), and reaps it unless it is the leg, whose status Popen reads. The leg is
    the one child here that the runner will wait for: legs run one at a time on the runner's one thread, and every
    other child the runner starts comes from subprocess.run, which reaps it before returning (ReapWhileLegRuns in
    tests/test_sweep_runner.py holds that census). So every other child that exits here was reparented to the
    runner, and nothing else will wait for it. Without the subreaper nothing is adopted and Popen.wait is exact."""
    if not _subreaper:
        return p.wait()
    while True:
        try:
            info = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOWAIT)
        except ChildProcessError:
            # No child at all: something reaped the leg, and Popen would read its status as 0.
            return None
        if info is None or info.si_pid == p.pid:
            return p.wait()
        try:
            os.waitpid(info.si_pid, 0)
        except ChildProcessError:
            pass


def stop_leg(p):
    """A leg's process group gets SIGTERM, five seconds, then SIGKILL; then its reparented descendants are killed."""
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            p.wait(timeout=wait)
        except subprocess.TimeoutExpired:
            pass
    reap_descendants()


def npm_cache(env):
    """The npm cache as the batcher's environment resolves it: npm_config_cache (either case), else ~/.npm."""
    for k in ("npm_config_cache", "NPM_CONFIG_CACHE"):
        if env.get(k):
            return env[k]
    return os.path.join(env.get("HOME") or os.path.expanduser("~"), ".npm")


def browsers_path(env):
    """Playwright's browser cache as the batcher's environment resolves it: PLAYWRIGHT_BROWSERS_PATH, else the
    platform's default (~/Library/Caches on macOS, XDG_CACHE_HOME or ~/.cache elsewhere) plus ms-playwright."""
    if env.get("PLAYWRIGHT_BROWSERS_PATH"):
        return env["PLAYWRIGHT_BROWSERS_PATH"]
    home = env.get("HOME") or os.path.expanduser("~")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Caches", "ms-playwright")
    return os.path.join(env.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "ms-playwright")


def build_path(python, env):
    """The leg's PATH: the pytest interpreter's directory, each PATH_TOOLS tool's directory as the runner's PATH finds
    it (a tool not found adds nothing), then PATH_FLOOR, each directory once."""
    search = env.get("PATH", "")
    exe = python if os.sep in python else (shutil.which(python, path=search) or "")
    dirs = [os.path.dirname(os.path.abspath(exe))] if exe else []
    for tool in PATH_TOOLS:
        hit = shutil.which(tool, path=search)
        if hit:
            dirs.append(os.path.dirname(hit))
    return os.pathsep.join(dict.fromkeys(dirs + list(PATH_FLOOR)))


def leg_context(tmpdir, python, env=None, pytest_python=None, served_env=None, served_python=None):
    """The per-run values the leg environment is built from: TMPDIR, the private HOME and state root under it (both
    removed with it; each leg runs with its own three in their place, leg_scratch), the shared npm and Playwright caches
    as the batcher's environment resolves them, PATH (every leg's
    but the pytest leg's and the served leg's: it leads with --python's directory), the pytest leg's PATH, which leads
    with its own interpreter's directory (`pytest_python`, the venv sdk_environment builds; --python when the run has no
    pytest leg), the served leg's PATH, which leads with its venv's directory (`served_python`, the venv
    served_environment builds; --python when the run has no served leg), and the served step's env: block as
    read_served_step read it (`served_env`)."""
    env = os.environ if env is None else env
    return {"tmpdir": tmpdir, "home": os.path.join(tmpdir, "home"), "xdg": os.path.join(tmpdir, "xdg-state"),
            "npm_cache": npm_cache(env), "browsers": browsers_path(env), "path": build_path(python, env),
            "pytest_path": build_path(pytest_python or python, env),
            "served_path": build_path(served_python or python, env), "served_env": dict(served_env or {})}


# The names the runner sets in every leg's environment from the run's context (leg_sets), beside LEG_FIXED,
# TOOL_CONFIG_OFF and PORT_FLOOR: a served step that sets one of these, or one of those, is refused (read_served_step),
# since its value would replace the runner's floor (a private HOME, a dead port).
CTX_SETS = ("PATH", "HOME", "TMPDIR", "XDG_STATE_HOME", "npm_config_cache", "PLAYWRIGHT_BROWSERS_PATH")


def runner_set_names():
    """Every name the runner sets or passes in a leg's environment on its own account (CTX_SETS, LEG_FIXED,
    TOOL_CONFIG_OFF, PORT_FLOOR, LEG_ALLOW)."""
    return set(CTX_SETS) | set(LEG_FIXED) | set(TOOL_CONFIG_OFF) | set(PORT_FLOOR) | set(LEG_ALLOW)


def leg_sets(leg, ctx, from_ci=True):
    """{name: value} the runner sets for `leg`: PATH (the pytest leg's and the served leg's own), the private HOME and
    XDG_STATE_HOME, TMPDIR, the shared npm cache and the shared Playwright cache (a private HOME has neither; the pytest
    leg gets the empty NO_BROWSERS directory under TMPDIR instead, as CI's Python cells have no browser), LEG_FIXED,
    TOOL_CONFIG_OFF, PORT_FLOOR and the leg's LEG_ENV; for the served leg, also the served step's env: block read from
    the swept sha's ci.yml (ctx's served_env), unless `from_ci` is False (leg_env_hash, which hashes the runner's own
    policy, not the sha's values)."""
    path = {"pytest": ctx["pytest_path"], SERVED_LEG: ctx.get("served_path", ctx["path"])}.get(leg, ctx["path"])
    browsers = os.path.join(ctx["tmpdir"], NO_BROWSERS) if leg == "pytest" else ctx["browsers"]
    sets = {"PATH": path, "HOME": ctx["home"], "TMPDIR": ctx["tmpdir"], "XDG_STATE_HOME": ctx["xdg"],
            "npm_config_cache": ctx["npm_cache"], "PLAYWRIGHT_BROWSERS_PATH": browsers}
    sets.update(LEG_FIXED)
    sets.update(TOOL_CONFIG_OFF)
    sets.update(PORT_FLOOR)
    sets.update(LEG_ENV.get(leg, {}))
    if leg == SERVED_LEG and from_ci:
        sets.update(ctx.get("served_env") or {})
    return sets


def leg_env(leg, ctx, base=None):
    """(the environment for `leg`, the names dropped, the values set): LEG_ALLOW's names from `base` (the runner's
    environment) when set, then leg_sets. The result records the dropped names and the set values, never an
    inherited value."""
    base = dict(os.environ if base is None else base)
    env = {k: base[k] for k in LEG_ALLOW if base.get(k)}
    sets = leg_sets(leg, ctx)
    dropped = sorted(k for k in base if k not in env and k not in sets)
    env.update(sets)
    return env, dropped, sets


def _tokenized(name, leg, value, ctx):
    """A set value with its per-run and per-machine parts named instead: the leg's PATH (the pytest leg's own, the served
    leg's own, else the others') and the two caches whole, and every value under TMPDIR (TMPDIR, HOME, XDG_STATE_HOME,
    the pytest leg's empty browser directory) by its path below it."""
    if name == "PATH":
        own = {"pytest": ("pytest_path", "<PYTEST_PATH>"), SERVED_LEG: ("served_path", "<SERVED_PATH>")}.get(leg, ("path", "<PATH>"))
        if value == ctx.get(own[0]):
            return own[1]
    for key, token in (("npm_cache", "<NPM_CACHE>"), ("browsers", "<BROWSERS>")):
        if value == ctx[key]:
            return token
    t = ctx["tmpdir"]
    if value == t or value.startswith(t + os.sep):
        return "<TMPDIR>" + value[len(t):]
    return value


# Round 2, decision 15: the leg environment the hash names changed with round 2's fixes (each leg's own TMPDIR, HOME and
# state root, Class B; one fresh checkout per ci.yml job, decision 13), so the hash names both, and no result written by
# a runner before them, which shared one HOME, state root, TMPDIR and checkout across the legs, reads as recorded under
# the same leg environment (body item 9's rule: a leg-environment change changes the hash).
LEG_SCRATCH = "each leg: a fresh TMPDIR of its own, HOME and XDG_STATE_HOME under it, removed when the leg ends"
LEG_CHECKOUT = ("the legs whose steps one ci.yml job holds: one fresh verified clone, in the job's step order, npm ci "
                "where the job runs it; each job's legs their own")


def leg_env_doc(ctx):
    """What leg_env_hash hashes: the allowed names, per leg the sorted NAME=VALUE pairs the runner sets, each value
    tokenized (_tokenized), the step whose env: block the served leg adds, and the shape each leg runs in (LEG_SCRATCH,
    and LEG_CHECKOUT with the steps the legs are grouped by, LEG_STEPS, and the legs of a checkout of their own)."""
    return {"allow": sorted(LEG_ALLOW),
            "set": {leg: sorted("%s=%s" % (k, _tokenized(k, leg, v, ctx)) for k, v in leg_sets(leg, ctx, from_ci=False).items())
                    for leg in LEGS},
            "from_ci": {SERVED_LEG: "the env: block of %s's step %r" % (CI_WORKFLOW, SERVED_STEP)},
            "scratch": LEG_SCRATCH,
            "checkout": {"per": LEG_CHECKOUT, "steps": dict(LEG_STEPS), "own": list(OWN_CHECKOUT_LEGS)}}


def leg_env_hash(ctx):
    """sha256 over leg_env_doc: it identifies the runner's allowlist, set values and the shape the legs run in, which
    depend only on its code, and not on the machine, the batcher's environment or the run. The values of the served
    step's env: block are not hashed: they are the swept sha's own, read from its ci.yml as the SDK's pin is, and each
    run records them (the served leg's env_set, runner.served); nor is the job grouping, which is the sha's ci.yml's
    and each run records (runner.checkout.groups)."""
    return hashlib.sha256(json.dumps(leg_env_doc(ctx), sort_keys=True).encode("utf-8")).hexdigest()


def policy_doc():
    """leg_env_doc over placeholder values (policy_hash)."""
    t = os.path.join(os.sep + "nonexistent", TMPDIR_PREFIX + "0" * TMPDIR_TAIL)
    return leg_env_doc({"tmpdir": t, "home": os.path.join(t, "home"), "xdg": os.path.join(t, "xdg-state"),
                        "npm_cache": os.sep + "nonexistent-npm-cache", "browsers": os.sep + "nonexistent-browsers",
                        "path": os.sep + "nonexistent-path", "pytest_path": os.sep + "nonexistent-pytest-path",
                        "served_path": os.sep + "nonexistent-served-path"})


def policy_hash():
    """The leg environment hash this runner records, computed over placeholder values (policy_doc): what a reader
    compares a result's recorded hash with (a result made under another allowlist, other set values or another shape
    of leg is not the same gate)."""
    return hashlib.sha256(json.dumps(policy_doc(), sort_keys=True).encode("utf-8")).hexdigest()


def recorded_hash(result):
    """The leg environment hash a result records (runner.leg_env.hash), or None when it records none."""
    runner = result.get("runner")
    leg_env_rec = runner.get("leg_env") if isinstance(runner, dict) else None
    h = leg_env_rec.get("hash") if isinstance(leg_env_rec, dict) else None
    return h if isinstance(h, str) else None


def leg_scratch(ctx, tmpdir):
    """The context one leg runs in (round 2, Class B): the run's (leg_context), with the leg's own fresh TMPDIR and a
    private HOME and state root under it, so nothing an earlier leg left in any of the three reaches a later leg (an
    .npmrc whose node-options replace npm test's heap cap, a .gitconfig, a session-hosts file flipped on). It has the run
    context's shape, so leg_env_hash reads the same policy from either."""
    return dict(ctx, tmpdir=tmpdir, home=os.path.join(tmpdir, "home"), xdg=os.path.join(tmpdir, "xdg-state"))


def prepare_home(ctx):
    """The private HOME (empty), the pytest leg's empty browser directory (NO_BROWSERS), and the private state root, with
    session hosts off in its romp directory (the runner's own floor for leg code that starts a backend over the default
    state dir), all under ctx's TMPDIR: the run's, for the tool-version probe, and each leg's own (leg_scratch)."""
    os.mkdir(ctx["home"], 0o700)
    os.mkdir(os.path.join(ctx["tmpdir"], NO_BROWSERS), 0o700)
    os.makedirs(os.path.join(ctx["xdg"], "romp"), mode=0o700)
    with open(os.path.join(ctx["xdg"], "romp", "session-hosts"), "w") as f:
        f.write("off\n")


def home_left(ctx):
    """The names a leg left in its private HOME, sorted (empty: the HOME was empty when the leg ended)."""
    try:
        return sorted(os.listdir(ctx["home"]))
    except OSError:
        return []


def tool_versions(ctx):
    """{tool: {"path", "version"}} for TOOL_VERSION_ARGS, each found on the leg's PATH and run in a leg's environment;
    a tool not found records path None. Recorded only: versions differ by machine legitimately."""
    env, _dropped, _sets = leg_env("tools", ctx)
    out = {}
    for tool, arg in TOOL_VERSION_ARGS:
        path = shutil.which(tool, path=ctx["path"])
        rec = {"path": path, "version": None}
        if path:
            try:
                p = subprocess.run([path, arg], env=env, cwd=ctx["tmpdir"], text=True, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
                rec["version"] = (p.stdout.strip().splitlines() or [""])[0][:200]
            except (OSError, subprocess.SubprocessError) as e:
                rec["error"] = str(e)[:200]
        out[tool] = rec
    return out


def npm_builtin(ctx):
    """{"npm", "root", "path", "present", "sha256", "keys"}: the builtin config file of the npm the legs find on their
    PATH (NPM_BUILTIN under npm's package root, which npm reads before any other config file, round 2, extra6-2). The root
    is the directory above the npm's real path (its bin/npm-cli.js, where npm's installs link it) whose package.json names
    npm; an npm with no such directory above it (a shim, such as volta's, or no npm on the PATH) records root None, and
    the runner cannot read its builtin file. Raises Refused, naming the file and the keys, when the file sets any key but
    NPM_BUILTIN_KEYS: every line that is not blank or a comment (`;` or `#`) must be `prefix = <value>`, so a section, a
    bare key or any other key is refused."""
    npm = shutil.which("npm", path=ctx["path"])
    rec = {"npm": npm, "root": None, "path": None, "present": False, "sha256": None, "keys": []}
    if not npm:
        return rec
    d = os.path.dirname(os.path.realpath(npm))
    for cand in (d, os.path.dirname(d)):
        try:
            with open(os.path.join(cand, "package.json"), encoding="utf-8") as f:
                named = json.load(f).get("name") == "npm"
        except (OSError, ValueError, AttributeError):
            named = False
        if named:
            rec["root"] = cand
            break
    if rec["root"] is None:
        return rec
    path = os.path.join(rec["root"], NPM_BUILTIN)
    rec["path"] = path
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return rec
    except OSError as e:
        raise Refused("npm's builtin config file %s cannot be read (%s); npm reads it in every npm leg, so the runner reads "
                      "it first" % (path, e))
    rec.update(present=True, sha256=hashlib.sha256(data).hexdigest())
    keys = []
    for line in data.decode("utf-8", "replace").splitlines():
        text = line.strip()
        if not text or text[0] in ";#":
            continue
        keys.append(text.split("=", 1)[0].strip() if "=" in text and not text.startswith("[") else text)
    rec["keys"] = keys
    other = [k for k in keys if k not in NPM_BUILTIN_KEYS]
    if other:
        raise Refused("npm's builtin config file %s sets %s; npm reads it in every npm leg before any other config file, and "
                      "neither the private HOME nor npm_config_globalconfig turns it off (a node-options line there would "
                      "replace npm test's heap cap), so the runner refuses a builtin file that sets any key but %s: remove "
                      "the other keys, or put an npm whose builtin file holds none first on PATH"
                      % (path, ", ".join(repr(k) for k in other), " and ".join(NPM_BUILTIN_KEYS)))
    return rec


def expand(tree, patterns):
    """(every pattern's sorted matches relative to the tree, in the patterns' order, each file once; the first pattern
    that matched nothing, or None). Every pattern is expanded, an empty one included, so every served file stays known
    where one of the served globs is empty (deps_skipped leaves them all out of the tests the served leg also runs)."""
    import glob
    files, empty = [], None
    for pat in patterns:
        hits = sorted(os.path.relpath(p, tree) for p in glob.glob(os.path.join(tree, pat)))
        if not hits and empty is None:
            empty = pat
        files += hits
    return list(dict.fromkeys(files)), empty


def make_tmpdir():
    """A new directory named like the box rule's `mktemp -d /tmp/sweep-XXXXXX`, mode 0700. The tail starts with a
    digit: every path a test builds under TMPDIR carries the name, and a letter after the prefix's dash spells a
    short option (`-p`) that a test asserting its absence in a recorded command line then finds (one draw in 62
    with mktemp's alphabet, tests/romp-cli-scope.bats)."""
    rng = random.SystemRandom()
    alphabet = string.ascii_letters + string.digits
    for _ in range(100):
        tail = rng.choice(string.digits) + "".join(rng.choice(alphabet) for _ in range(TMPDIR_TAIL - 1))
        d = os.path.join(TMPDIR_PARENT, TMPDIR_PREFIX + tail)
        try:
            os.mkdir(d, 0o700)
            return d
        except FileExistsError:
            continue
    raise Refused("could not create a directory %s/%sXXXXXX" % (TMPDIR_PARENT, TMPDIR_PREFIX))


def default_workers():
    """The idle cores at launch, clamped to 2..10 (the box sweep's rule)."""
    try:
        cores = len(os.sched_getaffinity(0))
    except AttributeError:
        cores = os.cpu_count() or 2
    idle = cores - int(os.getloadavg()[0])
    return max(WORKERS_MIN, min(WORKERS_MAX, idle))


# -- the pytest leg's environment: a venv at ci.yml's install steps, the SDK at its pin (round 1, the SDK ruling) --

# What the runner asks of an interpreter (--python, and the venvs it builds), as one JSON line: its version, short and
# whole, which of PYTEST_MODULES it cannot find, whether it has ensurepip, the installed version of each distribution
# named on its command line (None for one it does not have), for each `import:NAME` argument whether the top-level
# module NAME can be found (find_spec, which imports nothing for a top-level name), and with the argument `all:` every
# distribution it holds with its version and the names of the pytest plugins they declare (the pytest11 entry points,
# which pytest loads on its own), None without it.
PROBE = ("# sweep probe\n"
         "import importlib.util, json, sys\n"
         "import importlib.metadata as md\n"
         "def ver(d):\n"
         "    try:\n"
         "        return md.version(d)\n"
         "    except md.PackageNotFoundError:\n"
         "        return None\n"
         "whole = 'all:' in sys.argv[1:]\n"
         "args = [a for a in sys.argv[1:] if a != 'all:']\n"
         "print(json.dumps({'version': sys.version.split()[0], 'full': sys.version, "
         "'missing': [m for m in %r if importlib.util.find_spec(m) is None], "
         "'ensurepip': importlib.util.find_spec('ensurepip') is not None, "
         "'dists': {d: ver(d) for d in args if not d.startswith('import:')}, "
         "'found': {m[7:]: importlib.util.find_spec(m[7:]) is not None for m in args if m.startswith('import:')}, "
         "'all': {str(x.metadata['Name']): x.version for x in md.distributions()} if whole else None, "
         "'plugins': sorted({e.name for e in md.entry_points(group='pytest11')}) if whole else None}))\n"
         % (PYTEST_MODULES,))


def probe(python, env, dists=(), what="the pytest interpreter", modules=(), whole=False):
    """The PROBE's answer from `python`, run in `env` (build_env), for the distributions `dists` and the top-level
    modules `modules`, and with `whole` every distribution and pytest plugin it holds; Refused when it cannot run or
    does not answer."""
    try:
        p = subprocess.run([python, "-c", PROBE, *dists, *("import:" + m for m in modules), *(["all:"] if whole else [])],
                           env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                           timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise Refused("%s %s cannot run: %s" % (what, python, e))
    if p.returncode != 0:
        raise Refused("%s %s failed its probe: %s" % (what, python, (p.stderr or p.stdout).strip()[:300]))
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        out = None
    if (not isinstance(out, dict) or not isinstance(out.get("missing"), list) or not isinstance(out.get("dists"), dict)
            or (modules and not isinstance(out.get("found"), dict))
            or (whole and not (isinstance(out.get("all"), dict) and isinstance(out.get("plugins"), list)))):
        raise Refused("%s %s answered its probe with %r" % (what, python, p.stdout.strip()[:300]))
    return out


def workflow_keys(text):
    """The top-level keys of a workflow file's text, each a `KEY:` line at column 0, in order."""
    return re.findall(r"(?m)^([A-Za-z_][A-Za-z0-9_-]*):", text)


def workflow_jobs(text):
    """The job ids of a workflow file's text, in order: each `  ID:` line under the top-level `jobs:` key, up to the next
    top-level key."""
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if re.fullmatch(r"jobs:\s*(?:#.*)?", line)), None)
    out = []
    for line in lines[start + 1:] if start is not None else ():
        if re.match(r"[A-Za-z_]", line):
            break
        m = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):\s*(?:#.*)?", line)
        if m:
            out.append(m.group(1))
    return out


def _comment_line(line):
    """A line YAML reads as a comment alone, at any indent: a block mapping or sequence skips it wherever it stands."""
    return line.lstrip().startswith("#")


def _job_end(line):
    """Whether a line under a job, indented fewer than four spaces, ends it: the next job's `  ID:` line or a top-level key.
    Comment and blank lines never end a job (round 2, correctness-2); any other such line is one the readers refuse."""
    return bool(re.fullmatch(r"  [A-Za-z_][A-Za-z0-9_-]*:\s*(?:#.*)?", line) or re.match(r"[A-Za-z_]", line))


def workflow_job(text, job, where=CI_WORKFLOW):
    """One job of a workflow file's text, read by line shape as CiParity reads it (the runner imports nothing beyond
    the standard library, so no YAML parser): {"keys": [the job's own keys, each a `    KEY:` line, in order], "steps":
    [step, ...]}, or None when the file has no `  <job>:` line. The job is that line and the lines under it up to the next
    job's `  ID:` line or a top-level key; a comment line, at any indent, is skipped wherever it stands, as YAML skips it
    (round 2, correctness-2: a comment at column 0 or 2 used to end the job, so a step or key after it was neither read nor
    refused), and any other line indented fewer than four spaces is refused, naming `where`, the job and the line. A
    step is a `      - KEY:` line under the job's `steps:` key, whatever its first key, and the
    lines under it indented eight spaces or more: {"keys": [its keys in order: the dash line's, then each key line
    eight spaces in], "values": {key: the text after the colon, stripped}, "name": its name: value or None,
    "run": its run text, "env": its env: block, "with": its with: block}. The run text is None with no run key, the value
    on the run line, or for `run: |` the block under it less ten spaces of indent; False for another block style (`|-`,
    `>`) or a run key given twice. The env: block is None with no env key, {NAME: the text after the colon, stripped} of
    the `NAME: VALUE` lines ten spaces in under an `env:` key with nothing after its colon, or False for any other shape
    (a value on the env: line, such as a flow mapping; a line in the block of another shape or depth; a name given twice;
    env: given twice). The with: block is read the same way, its names allowed a dash (python-version), and a comment
    line inside either block, at any indent, is skipped. A comment line is not a key."""
    lines = text.split("\n")
    if "  %s:" % job not in lines:
        return None
    body = []
    start = lines.index("  %s:" % job)
    for n, line in enumerate(lines[start + 1:], start + 2):
        if line.strip() and not _comment_line(line) and not line.startswith("    "):
            if _job_end(line):
                break
            raise Refused("%s: the %s job holds line %d (%r), indented fewer than four spaces, which is neither a comment, the "
                          "next job's line nor a top-level key; the runner reads a job whose lines under it are indented four "
                          "spaces or more" % (where, job, n, line))
        body.append(line)
    keys, steps, cur, in_steps, i = [], [], None, False, 0
    key_re = r"([A-Za-z_][A-Za-z0-9_-]*):(.*)"
    while i < len(body):
        line = body[i]
        i += 1
        m = re.fullmatch("    " + key_re, line)
        if m:
            keys.append(m.group(1))
            in_steps, cur = m.group(1) == "steps", None
            continue
        if not in_steps:
            continue
        m = re.fullmatch("      - " + key_re, line)
        if m:
            cur = {"keys": [], "values": {}, "name": None, "run": None, "env": None, "with": None}
            steps.append(cur)
        else:
            m = re.fullmatch("        " + key_re, line) if cur is not None else None
            if not m:
                continue
        key, value = m.group(1), m.group(2).strip()
        cur["keys"].append(key)
        cur["values"][key] = value
        if key == "name":
            cur["name"] = value
        if key in ("env", "with"):
            block = False if value or cur["keys"].count(key) > 1 else {}
            name_re = r"[A-Za-z_][A-Za-z0-9_]*" if key == "env" else r"[A-Za-z_][A-Za-z0-9_-]*"
            # a comment line at any indent stays inside the block, as YAML reads it (round 2, correctness-2: one between
            # the served env's two entries used to end the block, and the second entry was read by no one)
            while i < len(body) and (body[i].startswith(" " * 10) or not body[i].strip() or _comment_line(body[i])):
                entry = body[i]
                i += 1
                if not entry.strip() or _comment_line(entry):
                    continue
                em = re.fullmatch(" " * 10 + "(" + name_re + r"):(?: (.*))?", entry)
                if block is False or not em or em.group(1) in block:
                    block = False
                    continue
                block[em.group(1)] = (em.group(2) or "").strip()
            cur[key] = block
            continue
        if key != "run":
            continue
        if value == "|":
            block = []
            while i < len(body) and (body[i].startswith(" " * 10) or not body[i].strip()):
                block.append(body[i][10:])
                i += 1
            run = "\n".join(block).strip("\n")
        elif value[:1] in ("|", ">"):
            run = False
        else:
            run = value
        cur["run"] = False if cur["keys"].count("run") > 1 else run
    return {"keys": keys, "steps": steps}


# The line shapes read_run reads in an install step's run text, and no others.
_SET_LINE = re.compile(r"set -[euo]+(?: pipefail)?")
_SED_ASSIGN = re.compile(r"""([A-Za-z_][A-Za-z0-9_]*)="\$\(sed -n '([^']*)' ([A-Za-z0-9_./-]+)\)\"""")
_ERE_CHECK = re.compile(r"""\[\[ "\$([A-Za-z_][A-Za-z0-9_]*)" =~ (\S+) \]\] \|\| \{""")
_PIP_WORD = re.compile(r"-U|--upgrade|-q|--quiet|[A-Za-z0-9][A-Za-z0-9._-]*(?:\[[A-Za-z0-9._,-]+\])?"
                       r"(?:(?:==|>=|<=|~=|!=|<|>)[A-Za-z0-9.*+!_-]+)?")
_IMPORT_CODE = re.compile(r"import [A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_VAR_REF = re.compile(r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})")


def _bre(bre, where):
    r"""A POSIX basic regular expression as a Python one, for the shapes a sed pin read uses: \( \) a group, \{ \} an
    interval, bracket expressions (a backslash inside one is literal, as POSIX has it), . * and ^ at the start and $ at
    the end with their meaning; + ? | ( ) { } are literal in a BRE and escaped. A backslash before anything else (a GNU
    extension such as \+ or \w, a back-reference) and a character class such as [:digit:] are Refused, not guessed."""
    out, i, n = [], 0, len(bre)
    while i < n:
        c = bre[i]
        if c == "\\":
            nxt = bre[i + 1] if i + 1 < n else ""
            if nxt in ("(", ")", "{", "}"):
                out.append(nxt)
            elif nxt and nxt in ".*[]^$\\/":
                out.append("\\" + nxt)
            else:
                raise Refused("%s: the sed expression %r uses \\%s, which the runner does not read" % (where, bre, nxt))
            i += 2
            continue
        if c == "[":
            j = i + 1
            if j < n and bre[j] == "^":
                j += 1
            if j < n and bre[j] == "]":
                j += 1
            while j < n and bre[j] != "]":
                if bre[j] == "[" and j + 1 < n and bre[j + 1] in ":.=":
                    raise Refused("%s: the sed expression %r uses a character class, which the runner does not read"
                                  % (where, bre))
                j += 1
            if j >= n:
                raise Refused("%s: the sed expression %r has an unclosed [" % (where, bre))
            out.append("[" + bre[i + 1:j].replace("\\", "\\\\") + "]")
            i = j + 1
            continue
        if c == "^" and i != 0 or c == "$" and i != n - 1 or c in "+?|(){}" or c == "*" and i == 0:
            out.append("\\" + c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


def read_sed(checkout, script, rel, where):
    r"""What `sed -n SCRIPT FILE` prints, less its trailing newlines as $(...) takes it, for the one script shape
    read_run reads, s/RE/\1/p (RE by _bre), over FILE, a relative path that stays inside the checkout: every line RE
    matches, with the match replaced by its first group."""
    m = re.fullmatch(r"s/((?:[^/\\]|\\.)*)/\\1/p", script)
    if not m:
        raise Refused("%s: the sed script %r is not s/RE/\\1/p, the one form the runner reads" % (where, script))
    root = os.path.realpath(checkout)
    real = os.path.realpath(os.path.join(root, rel))
    if os.path.isabs(rel) or not real.startswith(root + os.sep) or not os.path.isfile(real):
        raise Refused("%s: sed reads %s, which is not a file in the checkout" % (where, rel))
    try:
        rx = re.compile(_bre(m.group(1), where))
    except re.error as e:
        raise Refused("%s: the sed expression %r does not compile (%s)" % (where, m.group(1), e))
    if rx.groups < 1:
        raise Refused("%s: the sed expression %r has no group for \\1" % (where, m.group(1)))
    with open(real, "rb") as f:
        lines = f.read().decode("utf-8", "surrogateescape").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    printed = []
    for line in lines:
        hit = rx.search(line)
        if hit:
            printed.append(line[:hit.start()] + (hit.group(1) or "") + line[hit.end():])
    return "\n".join(printed).rstrip("\n")


def _expand(word, variables, where, line):
    def value(m):
        name = m.group(1) or m.group(2)
        if name not in variables:
            raise Refused("%s: the line %r uses $%s, which no line before it reads" % (where, line, name))
        return variables[name]
    out = _VAR_REF.sub(value, word)
    if "$" in _VAR_REF.sub("", word):
        raise Refused("%s: the line %r holds an expansion the runner does not read" % (where, line))
    return out


def read_run(run, checkout, where):
    r"""[("pip" or "check", argv)] of one install step's run text, each argv starting with `python`, CI's name for the
    cell's interpreter, which the build replaces with the venv's. A line is read only in these shapes: `set -euo
    pipefail`; `NAME="$(sed -n 's/RE/\1/p' FILE)"`, which read_sed evaluates in the checkout; `[[ "$NAME" =~ ERE ]] ||
    {` with the lines to its closing `}` (the step's own refusal, which must hold an exit with a nonzero status), whose
    ERE is applied to NAME's value, so a value the step's check refuses is refused here as the step fails in CI; `python
    -m pip install WORD...`, each word a plain requirement or one of -U, --upgrade, -q, --quiet, after $NAME and ${NAME}
    are replaced with values read above; and `python -c "import MODULE"`. Blank and comment lines are skipped. Any other
    line is Refused, naming it: the runner runs nothing it has not read."""
    variables, out, lines, i = {}, [], run.split("\n"), 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#") or _SET_LINE.fullmatch(line):
            continue
        m = _SED_ASSIGN.fullmatch(line)
        if m:
            variables[m.group(1)] = read_sed(checkout, m.group(2), m.group(3), where)
            continue
        m = _ERE_CHECK.fullmatch(line)
        if m:
            end = next((j for j in range(i, len(lines)) if lines[j].strip() == "}"), None)
            if end is None or not any(re.fullmatch(r"exit [1-9][0-9]*", x.strip()) for x in lines[i:end]):
                raise Refused("%s: the check %r has no closing } after an exit with a nonzero status" % (where, line))
            i = end + 1
            name, ere = m.group(1), m.group(2)
            if name not in variables:
                raise Refused("%s: the check %r reads $%s, which no line before it reads" % (where, line, name))
            if not re.fullmatch(r"(?:[\^$.+*?\[\]0-9A-Za-z{},|()-]|\\[.\[\]()*+?{}|^$\\])+", ere):
                raise Refused("%s: the check's expression %r is not one the runner reads" % (where, ere))
            if not re.search(ere, variables[name]):
                raise Refused("%s reads %r into %s, which the step's own check (%s) refuses, as the step would fail in CI"
                              % (where, variables[name], name, ere))
            continue
        if "`" in line or "$(" in line or ("'" in line and "$" in line):
            raise Refused("%s: the line %r holds quoting or a substitution the runner does not read" % (where, line))
        try:
            words = [_expand(w, variables, where, line) for w in shlex.split(line)]
        except ValueError as e:
            raise Refused("%s: the line %r does not parse (%s)" % (where, line, e))
        if words[:4] == ["python", "-m", "pip", "install"] and len(words) > 4 and all(_PIP_WORD.fullmatch(w) for w in words[4:]):
            out.append(("pip", words))
        elif len(words) == 3 and words[:2] == ["python", "-c"] and _IMPORT_CODE.fullmatch(words[2]):
            out.append(("check", words))
        else:
            raise Refused("%s: the line %r is not one the runner reads (python -m pip install of plain requirements, a "
                          "python -c import, a pin read by sed and its check); it runs nothing it has not read" % (where, line))
    if not any(kind == "pip" for kind, _cmd in out):
        raise Refused("%s installs nothing the runner reads" % where)
    return out


def read_install_plan(checkout, sha):
    """What ci.yml at the swept sha installs for the pytest leg, read from the checkout: {"steps": [{"step", "commands"}],
    "dist", "pin", "module"}. Each INSTALL_STEPS step of CI_PYTHON_JOB is read by read_run; the SDK is the one
    NAME==VERSION requirement SDK_STEP installs, and its import check names the module. Refused, naming the file and the
    step, when the file, the job, a step or its run text is missing or a line is one read_run does not read: a head whose
    ci.yml predates one of the steps is not swept until it merges main. Refused as well, by name, for anything in the
    file that could change what CI installs without changing a command read here: a workflow-level key of
    WORKFLOW_KEYS_REFUSED, a job key outside PYTHON_JOB_KEYS, a step of the job other than the install steps, the pytest
    step and an unnamed use of one of SETUP_ACTIONS (an unnamed run step, or a named one the runner does not read), a
    step name given twice, and on an install step a key outside INSTALL_STEP_KEYS, a key given twice, or a shell other
    than bash; and a line under the job indented fewer than four spaces that is neither a comment, the next job's line
    nor a top-level key (workflow_job; a comment line, at any indent, is skipped)."""
    where = "%s at %s" % (CI_WORKFLOW, short(sha))
    try:
        with open(os.path.join(checkout, CI_WORKFLOW), encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Refused("%s cannot be read (%s); the pytest leg's environment is built from its %s job's install steps"
                      % (where, e, CI_PYTHON_JOB))
    for key in workflow_keys(text):
        if key in WORKFLOW_KEYS_REFUSED:
            raise Refused("%s has a workflow-level %s:, which reaches the install steps of its %s job; the runner builds the "
                          "pytest leg's environment from those steps' commands alone, so it does not read a ci.yml with one"
                          % (where, key, CI_PYTHON_JOB))
    job = workflow_job(text, CI_PYTHON_JOB, where)
    if job is None:
        raise Refused("%s has no %s job; the pytest leg's environment is built from its install steps" % (where, CI_PYTHON_JOB))
    extra = [k for k in job["keys"] if k not in PYTHON_JOB_KEYS]
    if extra:
        raise Refused("%s: the %s job has %s, which the runner does not read (it reads a job whose keys are %s); a job key "
                      "such as env:, defaults: or container: can change what the install steps install"
                      % (where, CI_PYTHON_JOB, ", ".join(k + ":" for k in extra), ", ".join(PYTHON_JOB_KEYS)))
    steps = {}
    for n, st in enumerate(job["steps"], 1):
        name = st["name"]
        if name is None:
            uses = st["values"].get("uses", "")
            if set(st["keys"]) <= {"uses", "with"} and uses.partition("@")[0] in SETUP_ACTIONS and "@" in uses:
                continue
            raise Refused("%s: step %d of the %s job has no name (%s); the runner reads the job's steps by name, and an "
                          "unnamed step other than a use of %s could install what the runner never sees"
                          % (where, n, CI_PYTHON_JOB, ", ".join("%s: %s" % (k, st["values"][k]) for k in st["keys"][:2]),
                             " or ".join(SETUP_ACTIONS)))
        if name not in INSTALL_STEPS and name != PYTEST_STEP:
            raise Refused("%s: the %s job has a step %r, which the runner does not read (it reads the install steps %s and "
                          "%r); a step it does not read could install what the pytest leg's environment lacks"
                          % (where, CI_PYTHON_JOB, name, ", ".join(repr(x) for x in INSTALL_STEPS), PYTEST_STEP))
        if name in steps:
            raise Refused("%s: the %s job names two steps %r" % (where, CI_PYTHON_JOB, name))
        steps[name] = st
    plan = []
    for name in INSTALL_STEPS:
        if name not in steps:
            raise Refused("%s has no step %r in its %s job; the pytest leg's environment is built from the steps %s, so a head "
                          "whose ci.yml predates one of them is not swept: merge main into it"
                          % (where, name, CI_PYTHON_JOB, ", ".join(repr(n) for n in INSTALL_STEPS)))
        st = steps[name]
        step_where = "%s, step %r" % (where, name)
        extra = [k for k in st["keys"] if k not in INSTALL_STEP_KEYS]
        if extra:
            raise Refused("%s has %s, which the runner does not read (an install step's keys are %s); a key such as env:, "
                          "if: or working-directory: changes what the step installs without changing its commands"
                          % (step_where, ", ".join(k + ":" for k in extra), ", ".join(INSTALL_STEP_KEYS)))
        twice = sorted({k for k in st["keys"] if st["keys"].count(k) > 1})
        if twice:
            raise Refused("%s gives %s twice" % (step_where, ", ".join(k + ":" for k in twice)))
        if "shell" in st["values"] and st["values"]["shell"] != "bash":
            raise Refused("%s runs under shell: %s; the runner reads a step run by bash, CI's default" % (step_where, st["values"]["shell"]))
        run = st["run"]
        if not run:
            raise Refused("%s: the step %r has %s" % (where, name, "no run line" if run is None else
                                                      "a run the runner does not read (a block style other than |)"))
        plan.append({"step": name, "commands": read_run(run, checkout, step_where)})
    sdk = plan[INSTALL_STEPS.index(SDK_STEP)]["commands"]
    pinned = [w for kind, cmd in sdk if kind == "pip" for w in cmd[4:] if "==" in w]
    if len(pinned) != 1:
        raise Refused("%s: the step %r installs %d requirements pinned with ==, and the runner reads the SDK's pin from "
                      "exactly one" % (where, SDK_STEP, len(pinned)))
    dist, pin = pinned[0].split("==", 1)
    checks = [cmd[2][len("import "):] for kind, cmd in sdk if kind == "check"]
    return {"steps": plan, "dist": re.sub(r"\[.*\]$", "", dist), "pin": pin, "module": checks[0] if checks else None}


# -- the served leg: CI's served step, read by its name wherever ci.yml holds it (the served ruling, 2026-09-28) --

# The plain values of an env: block the runner reads as YAML does: a decimal integer without a leading zero, or a word
# that starts with a letter and is none of YAML's boolean or null spellings (an older YAML reads yes, no, on and off as
# booleans too); anything else plain (a float, a hex number, a leading symbol) is refused rather than guessed.
_ENV_PLAIN = re.compile(r"0|[1-9][0-9]*|[A-Za-z][A-Za-z0-9_.,/+=:-]*")
_ENV_NOT_STRINGS = ("true", "false", "yes", "no", "on", "off", "null", "y", "n")


def _env_value(raw, name, where):
    """A value of the served step's env: block as YAML reads the forms the runner reads (_ENV_PLAIN, or text quoted
    with " holding no backslash or quote, or with ' holding no quote), or Refused naming the value: an expression, which
    only CI evaluates, and every other form."""
    shown = "%s: env: %s is %r" % (where, name, raw)
    if "${{" in raw:
        raise Refused("%s, an expression the runner does not evaluate; the served leg's environment is the step's env: "
                      "block as ci.yml writes it, so a value only CI computes is not swept" % shown)
    if len(raw) >= 2 and raw[0] == raw[-1] == '"' and not re.search(r'["\\]', raw[1:-1]):
        return raw[1:-1]
    if len(raw) >= 2 and raw[0] == raw[-1] == "'" and "'" not in raw[1:-1]:
        return raw[1:-1]
    if _ENV_PLAIN.fullmatch(raw) and raw.lower() not in _ENV_NOT_STRINGS:
        return raw
    raise Refused("%s, a form the runner does not read (it reads a quoted value without escapes, a decimal integer, or a "
                  "plain word that YAML does not read as a boolean or null)" % shown)


def _job_defaults(text, job):
    """The lines of `job`'s defaults: block (comment and blank lines dropped), or None when the job has no defaults:. A
    defaults: line with a value after its colon (a flow mapping such as `defaults: {run: {working-directory: x}}`) is
    returned as that one line, which no reader accepts, so a job whose defaults: the runner cannot read in block form
    is never read as a job without one. A comment line, at any indent, ends neither the job nor the block (round 2,
    correctness-2); the job ends at its first other line indented fewer than four spaces, and read_served_step reads the
    job with workflow_job first, which refuses such a line unless it is the next job's or a top-level key."""
    lines = text.split("\n")
    out = None
    for line in lines[lines.index("  %s:" % job) + 1:]:
        if not line.strip() or _comment_line(line):
            continue
        if not line.startswith("    "):
            break
        if out is None:
            if re.fullmatch(r"    defaults:\s*(?:#.*)?", line):
                out = []
            elif re.match(r"    defaults\s*:", line):
                return [line]
            continue
        if not line.startswith("      "):
            break
        out.append(line)
    return out


def read_served_step(checkout, sha):
    """The served leg's step in the swept sha's ci.yml (SERVED_STEP), found by its name in whichever job holds it and
    read from the checkout: {"job", "step", "env", "globs", "requirements", "install", "python"}. env is the step's env:
    block, {NAME: value}, each value as YAML reads it (_env_value); globs are the file patterns on its one pytest line, in
    order; requirements the distributions its pip install lines name, and install those lines as argvs (each starting
    `python`, CI's name for the step's interpreter, which the served venv's build replaces with the venv's); python the
    MAJOR.MINOR the nearest actions/setup-python step before it in its job sets up (its with: python-version:, a quoted
    version, _PYTHON_VERSION), the interpreter the served venv is built from. Refused, naming the file and the step,
    when that step or its python-version: is missing or not in that form; when ci.yml cannot be read; has
    a workflow-level env: or defaults: (either reaches the step); holds no step of that name, or two; the step's job has
    an env: (it reaches the step, and the runner reads the step's own env: alone) or a container:, a defaults: other
    than one run: working-directory: line in block form (_job_defaults), or a defaults: while the step names no
    working-directory:; the step has a
    key outside SERVED_STEP_KEYS or one given twice, a working-directory: other than the repository root, a shell: other
    than bash, an env: block in another shape, a value _env_value does not read, or a name the runner sets itself
    (runner_set_names: its value would replace the runner's floor); or its run text holds a line other than blank and
    comment lines, `set -euo pipefail`, `python -m pip install` of plain requirements, and exactly one `python -m
    pytest` line whose words are pytest options and globs of .py files directly under tests/, each glob written without
    quotes (bash passes a quoted one to pytest unexpanded) and the line splitting into the same words quoted and
    unquoted. A comment line, at any indent, is skipped, and a line under any job indented fewer than four spaces that is
    neither a comment, the next job's line nor a top-level key is refused (workflow_job)."""
    where = "%s at %s" % (CI_WORKFLOW, short(sha))
    try:
        with open(os.path.join(checkout, CI_WORKFLOW), encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Refused("%s cannot be read (%s); the served leg's files and switches are read from its step %r"
                      % (where, e, SERVED_STEP))
    for key in workflow_keys(text):
        if key in WORKFLOW_KEYS_REFUSED:
            raise Refused("%s has a workflow-level %s:, which reaches its step %r; the runner reads that step's own keys "
                          "alone, so it does not read a ci.yml with one" % (where, key, SERVED_STEP))
    hits = []
    for job in workflow_jobs(text):
        spec = workflow_job(text, job, where)
        hits += [(job, spec, st) for st in (spec or {}).get("steps", []) if st["name"] == SERVED_STEP]
    if not hits:
        raise Refused("%s has no step %r in any job; the served leg runs the files that step's globs select, with its env: "
                      "block, in a venv its pip line builds, so a head whose ci.yml lacks it is not swept: merge main into it"
                      % (where, SERVED_STEP))
    if len(hits) > 1:
        raise Refused("%s has %d steps named %r (in %s); the runner reads the served leg from one"
                      % (where, len(hits), SERVED_STEP, ", ".join("the %s job" % h[0] for h in hits)))
    job, spec, st = hits[0]
    step_where = "%s, step %r of the %s job" % (where, SERVED_STEP, job)
    for key in ("env", "container"):
        if key in spec["keys"]:
            raise Refused("%s: the %s job has %s:, which reaches the step; the runner reads the step's own env: alone"
                          % (step_where, job, key))
    defaults = _job_defaults(text, job)
    if defaults is not None and not (len(defaults) == 2 and defaults[0] == "      run:"
                                     and re.fullmatch(r"        working-directory: \S+", defaults[1])):
        raise Refused("%s: the %s job has a defaults: other than one run: working-directory: line, which the runner does "
                      "not read (a shell: there changes how the step's run text is read)" % (step_where, job))
    extra = [k for k in st["keys"] if k not in SERVED_STEP_KEYS]
    if extra:
        raise Refused("%s has %s, which the runner does not read (the served step's keys are %s)"
                      % (step_where, ", ".join(k + ":" for k in extra), ", ".join(SERVED_STEP_KEYS)))
    twice = sorted({k for k in st["keys"] if st["keys"].count(k) > 1})
    if twice:
        raise Refused("%s gives %s twice" % (step_where, ", ".join(k + ":" for k in twice)))
    wd = st["values"].get("working-directory")
    if wd is None and defaults is not None:
        raise Refused("%s names no working-directory: and its job has a defaults:, which moves where the step runs; the "
                      "runner reads a step run from the repository root, where its globs resolve" % step_where)
    if wd is not None and wd != SERVED_ROOT:
        raise Refused("%s runs in %s; the runner reads a step run from the repository root (working-directory: %s, or "
                      "none on a job without defaults:), where its globs resolve" % (step_where, wd, SERVED_ROOT))
    if "shell" in st["values"] and st["values"]["shell"] != "bash":
        raise Refused("%s runs under shell: %s; the runner reads a step run by bash" % (step_where, st["values"]["shell"]))
    if st["env"] is False:
        raise Refused("%s has an env: block in a shape the runner does not read (it reads NAME: VALUE lines under a bare "
                      "env:, each name once)" % step_where)
    env = {}
    taken = runner_set_names()
    for name, raw in (st["env"] or {}).items():
        if name in taken:
            raise Refused("%s sets %s, which the runner sets itself in every leg's environment; the served leg does not "
                          "take a value from ci.yml that replaces the runner's own" % (step_where, name))
        env[name] = _env_value(raw, name, step_where)
    run = st["run"]
    if not run:
        raise Refused("%s has %s" % (step_where, "no run line" if run is None else
                                     "a run the runner does not read (a block style other than |)"))
    setup = [x for x in spec["steps"][:spec["steps"].index(st)] if x["values"].get("uses", "").partition("@")[0] == SETUP_PYTHON]
    if not setup:
        raise Refused("%s: no %s step comes before it in the %s job, so the runner cannot tell which Python CI's served "
                      "step runs; the served leg's venv is built from that version" % (step_where, SETUP_PYTHON, job))
    version = (setup[-1]["with"] or {}).get("python-version") if setup[-1]["with"] is not False else None
    m = _PYTHON_VERSION.fullmatch(version or "")
    if not m:
        raise Refused("%s: the %s step before it in the %s job sets python-version: %s, which the runner does not read (it "
                      "reads a quoted MAJOR.MINOR, such as '3.12', under a with: block; YAML reads a plain 3.10 as 3.1)"
                      % (step_where, SETUP_PYTHON, job, "nothing" if version is None else version))
    globs, requirements, install, pytest_lines = [], [], [], 0
    for raw_line in run.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#") or _SET_LINE.fullmatch(line):
            continue
        if re.search(r"[`$;&|<>(){}\\]", line):
            raise Refused("%s: the line %r holds an expansion, a substitution, a redirection or a second command, which the "
                          "runner does not read" % (step_where, line))
        try:
            words = shlex.split(line)
            written = shlex.split(line, posix=False)
        except ValueError as e:
            raise Refused("%s: the line %r does not parse (%s)" % (step_where, line, e))
        if words[:4] == ["python", "-m", "pip", "install"] and len(words) > 4 and all(_PIP_WORD.fullmatch(w) for w in words[4:]):
            requirements += [re.split(r"[\[<>=!~]", w)[0] for w in words[4:] if not w.startswith("-")]
            install.append(words)
            continue
        if words[:3] != ["python", "-m", "pytest"]:
            raise Refused("%s: the line %r is not one the runner reads (python -m pip install of plain requirements, and one "
                          "python -m pytest line)" % (step_where, line))
        pytest_lines += 1
        # each word beside the text ci.yml writes for it: bash expands a glob written bare and passes a quoted one to
        # pytest as it stands, so a glob is read only where it is written without quotes
        if len(written) != len(words):
            raise Refused("%s: the line %r does not split into the same words quoted and unquoted, which the runner does not "
                          "read" % (step_where, line))
        rest = iter(zip(words[3:], written[3:]))
        for w, as_written in rest:
            if w.startswith("-"):
                if w in PYTEST_VALUE_OPTIONS:
                    next(rest, None)
                continue
            if as_written != w:
                raise Refused("%s: its pytest line names %s, a quoted word; bash passes it to pytest unexpanded, so the "
                              "runner does not read it as a glob" % (step_where, as_written))
            if not _SERVED_GLOB.fullmatch(w):
                raise Refused("%s: its pytest line names %r, which the runner does not read as a glob of .py files directly "
                              "under tests/" % (step_where, w))
            globs.append(w)
    if pytest_lines != 1:
        raise Refused("%s has %d python -m pytest lines; the runner reads the served leg's files from exactly one"
                      % (step_where, pytest_lines))
    if not globs:
        raise Refused("%s: its pytest line names no glob of test files" % step_where)
    return {"job": job, "step": SERVED_STEP, "env": env, "globs": globs, "requirements": list(dict.fromkeys(requirements)),
            "install": install, "python": m.group(2)}


def leg_groups(checkout, sha, legs, npm=True):
    """[{"job", "legs", "setup_before"}, ...]: the legs of `legs` in the order they run, grouped by the ci.yml job each
    runs in (round 2, the coordinator's decision 13), read from the swept sha's ci.yml in the checkout. A leg of LEG_STEPS
    runs in the job whose steps hold its step, found by the step's name, and in the first such job when more than one
    holds it (a job of the served step's own repeats npm ci and may repeat the build); the legs one job holds form one
    group, in that job's step order. Each leg of OWN_CHECKOUT_LEGS is a group of its own (job None). The groups run in
    ci.yml's job order, the pytest leg's first (its skips decide what the served leg also runs), then those of
    OWN_CHECKOUT_LEGS. setup_before names the leg of a group before which npm ci runs as the group's setup: set when
    `npm` (the sha has vscode-extension/package.json), the group's job holds DEPS_STEP before one of the group's legs, and
    the deps leg does not run in that group (it runs in the first job that holds the step; a --leg re-run that does not
    name it gets npm ci there as setup instead). No other step is run as a setup. Refused, naming the file, when ci.yml
    cannot be read or holds no job with a leg's step."""
    where = "%s at %s" % (CI_WORKFLOW, short(sha))
    try:
        with open(os.path.join(checkout, CI_WORKFLOW), encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        raise Refused("%s cannot be read (%s); the legs are grouped by the job that holds each one's step" % (where, e))
    jobs = workflow_jobs(text)
    steps = {job: [st["name"] for st in (workflow_job(text, job, where) or {"steps": []})["steps"]] for job in jobs}
    first = [job for job in jobs if LEG_STEPS["pytest"] in steps[job]][:1]
    order = first + [job for job in jobs if job not in first]
    owner = {}
    for leg in legs:
        if leg in OWN_CHECKOUT_LEGS:
            continue
        holders = [job for job in order if LEG_STEPS[leg] in steps[job]]
        if not holders:
            raise Refused("%s holds no step %r in any job; the %s leg runs in the job that holds its step, with that job's "
                          "other legs in one checkout, so a head whose ci.yml lacks it is not swept: merge main into it"
                          % (where, LEG_STEPS[leg], leg))
        owner[leg] = holders[0]
    groups = []
    for job in order:
        mine = sorted((leg for leg in legs if owner.get(leg) == job), key=lambda leg: steps[job].index(LEG_STEPS[leg]))
        if not mine:
            continue
        setup_before = None
        if npm and "deps" not in mine and DEPS_STEP in steps[job]:
            at = steps[job].index(DEPS_STEP)
            later = [leg for leg in mine if steps[job].index(LEG_STEPS[leg]) > at]
            setup_before = later[0] if later else None
        groups.append({"job": job, "legs": mine, "setup_before": setup_before})
    groups += [{"job": None, "legs": [leg], "setup_before": None} for leg in legs if leg in OWN_CHECKOUT_LEGS]
    return groups


def group_label(group):
    """How a message names a group of legs (leg_groups, or its record): its ci.yml job, or its one leg."""
    return "the %s job's legs" % group["job"] if group["job"] else "the %s leg" % group["legs"][0]


def _dist_key(dist):
    return re.sub(r"[-_.]+", "-", dist).lower()


def sdk_dir(env=None):
    return os.path.join(sweeps_dir(env), "sdk")


def served_dir(env=None):
    return os.path.join(sweeps_dir(env), "served")


def sdk_key(python, base, plan):
    """The pytest leg's environment's cache key: sha256 over the SDK's pin, --python's absolute path and whole
    sys.version, and every command the install steps give (so a ci.yml that adds or changes a package builds anew), in
    20 hex digits."""
    doc = {"pin": "%s==%s" % (plan["dist"], plan["pin"]), "python": os.path.abspath(python), "version": base.get("full"),
           "commands": [[s["step"], [cmd for _kind, cmd in s["commands"]]] for s in plan["steps"]]}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def served_key(python, base, served):
    """The served leg's environment's cache key: sha256 over --served-python's absolute path and whole sys.version and
    the served step's pip lines as ci.yml writes them (so a line that adds or changes a package builds anew), in 20 hex
    digits."""
    doc = {"python": os.path.abspath(python), "version": base.get("full"), "install": [list(cmd) for cmd in served["install"]]}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def build_env(python, tmpdir):
    """The environment of every command the build runs, and of each probe: LEG_ALLOW's names, a PATH of --python's
    directory and PATH_FLOOR, a private HOME under TMPDIR (pip's cache and user config are the build's own and go with
    it), TMPDIR, LANG=C.UTF-8, and pip's configuration files, version check and prompts off (PIP_CONFIG_FILE=/dev/null).
    No index, proxy or PYTHONPATH of the batcher's environment, and no SDK of theirs, reaches the build."""
    env = {k: os.environ[k] for k in LEG_ALLOW if os.environ.get(k)}
    home = os.path.join(tmpdir, "sdk-home")
    os.makedirs(home, mode=0o700, exist_ok=True)
    env.update(PATH=os.pathsep.join(dict.fromkeys([os.path.dirname(os.path.abspath(python))] + list(PATH_FLOOR))),
               HOME=home, TMPDIR=tmpdir, LANG="C.UTF-8", PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK="1",
               PIP_NO_INPUT="1")
    return env


def _build_venv(venv, python, base, steps, env, log, tmpdir, where):
    """Create the venv from `python` (with --without-pip and PyPA's get-pip.py when it has no ensurepip) and run every
    (label, argv) of `steps` with the venv's python in place of the argv's `python`, each logged to `log`; Refused,
    naming the step, the command and the log, on the first that fails or times out."""
    vpy = os.path.join(venv, "bin", "python")
    with open(log, "a") as out:
        out.write("# build: %s\n# key: %s\n# python: %s (%s)\n" % (now(), os.path.basename(venv), python, base.get("version")))
        out.flush()

        def step(label, argv):
            out.write("# %s: %s\n" % (label, " ".join(shlex.quote(a) for a in argv)))
            out.flush()
            try:
                p = subprocess.run(argv, env=env, cwd=tmpdir, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                   timeout=SDK_STEP_TIMEOUT)
            except subprocess.TimeoutExpired:
                raise Refused("%s: the step %r did not finish in %d s (%s); log %s" % (where, label, SDK_STEP_TIMEOUT, argv[-1], log))
            except OSError as e:
                raise Refused("%s: the step %r could not start: %s; log %s" % (where, label, e, log))
            out.write("# rc: %d\n" % p.returncode)
            out.flush()
            if p.returncode != 0:
                raise Refused("%s: the step %r, `%s`, exited %d; log %s" % (where, label, " ".join(argv[1:]), p.returncode, log))

        if base.get("ensurepip"):
            step("venv", [python, "-m", "venv", venv])
        else:
            step("venv", [python, "-m", "venv", "--without-pip", venv])
            url = os.environ.get("ROMP_GET_PIP_URL") or GET_PIP_URL
            dest = os.path.join(tmpdir, "get-pip.py")
            out.write("# get-pip.py from %s (%s has no ensurepip)\n" % (url, python))
            out.flush()
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
                    shutil.copyfileobj(r, f)
            except (OSError, ValueError) as e:
                raise Refused("%s: %s has no ensurepip, and get-pip.py could not be fetched from %s (%s); log %s"
                              % (where, python, url, e, log))
            step("get-pip", [vpy, dest, "-q"])
        for label, cmd in steps:
            step(label, [vpy] + cmd[1:])


def venv_tree(venv):
    """{relative path: entry} of every directory, file and symlink under the venv, links not followed, less the build's
    marker (SDK_MARKER, SERVED_MARKER): ["dir", mode], ["link", target], ["file", mode, size, sha256 of its bytes], or
    ["other", its file type]. OSError when a directory or file cannot be read."""
    def fail(e):
        raise e
    out = {}
    for d, dirs, files in os.walk(venv, onerror=fail):
        rel = os.path.relpath(d, venv)
        for x in dirs + files:
            full = os.path.join(d, x)
            key = os.path.normpath(os.path.join(rel, x))
            if key in (SDK_MARKER, SERVED_MARKER):
                continue
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                out[key] = ["link", os.readlink(full)]
            elif stat.S_ISDIR(st.st_mode):
                out[key] = ["dir", stat.S_IMODE(st.st_mode)]
            elif stat.S_ISREG(st.st_mode):
                h = hashlib.sha256()
                with open(full, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                out[key] = ["file", stat.S_IMODE(st.st_mode), st.st_size, h.hexdigest()]
            else:
                out[key] = ["other", stat.S_IFMT(st.st_mode)]
    return out


def venv_changes(built, now):
    """The paths whose entry in `now` (venv_tree) differs from `built`, the tree the build left, each with how: added,
    gone or changed. One kind of difference does not count: a __pycache__ directory, or a .pyc file under one, that was
    added or is gone. python and pytest write bytecode there in normal use (pytest's rewritten plugin modules among it),
    and pip compiles every module it installs, so an added .pyc can stand in only for a source the build left
    uncompiled, and one that is gone is compiled again from its source; a .pyc the build wrote that changed counts, since
    python would load it in place of its source."""
    out = []
    for path in sorted(set(built) | set(now)):
        a, b = built.get(path), now.get(path)
        if a == b:
            continue
        parts = path.split(os.sep)
        if (a is None or b is None) and "__pycache__" in parts and (parts[-1] == "__pycache__" or path.endswith(".pyc")):
            continue
        out.append("%s (%s)" % (path, "added" if a is None else "gone" if b is None else "changed"))
    return out


class VenvHold:
    """A venv the runner built (the pytest leg's, the served leg's) as one run holds it from its check to the end of the
    run: a shared lock on the key's lock file, so no other run rebuilds (which removes the venv) while this run's leg may
    be running in it, and the tree its build left, which changes() compares with the venv's tree now. retire() removes
    the build's marker, so the next run that reads the venv finds no finished build and builds it again: the marker is
    inside the venv, where a leg can write, so a leg that changed the venv can also have rewritten the tree the marker
    records to match, and the next run's check (_venv_check) would then pass it. The runner retires a venv whose tree
    changed on its way out, after the reap, while it still holds the shared lock: every other run holding it checked
    the venv before, and a rebuild waits for them all."""

    def __init__(self, lock, venv, built, marker):
        self.lock, self.venv, self.built, self.marker = lock, venv, built, marker

    def changes(self):
        try:
            return venv_changes(self.built, venv_tree(self.venv))
        except OSError as e:
            return ["%s cannot be read (%s)" % (self.venv, e)]

    def retire(self):
        """Remove the build's marker (a directory in its place too); None when it is gone, else why it could not be."""
        path = os.path.join(self.venv, self.marker)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            return "its marker %s could not be removed (%s)" % (path, e)
        return None

    def release(self):
        if self.lock is not None:
            fcntl.flock(self.lock, fcntl.LOCK_UN)
            self.lock.close()
            self.lock = None


def _flock(lock, how, sha, waiting):
    try:
        fcntl.flock(lock, how | fcntl.LOCK_NB)
    except BlockingIOError:
        print("sweep %s: %s" % (short(sha), waiting), flush=True)
        fcntl.flock(lock, how)


def sdk_environment(checkout, sha, python, tmpdir):
    """The pytest leg's interpreter and its record for the result, and the VenvHold the run keeps until it ends: a venv
    under <state dir>/sweeps/sdk/<key>, built from --python with the install steps ci.yml holds at the swept sha
    (read_install_plan: pytest and its plugins, cryptography, and the SDK at its pin), or the venv a finished build left
    under the same key (sdk_key: the pin, --python's path and version, the commands). The record: key, path, python (the
    venv's), dist and pin (as ci.yml reads them), version (the SDK's version as the venv's own metadata reports it),
    python_version (the venv's interpreter's whole sys.version), tree (sha256 of the tree its build left) and files (its
    entries), built (whether this run built it), build_s, log (the build's log beside the venv), base_python and
    base_version.

    A pin change is a new key, so a new venv beside the old one; an old one stays until it is removed by hand. A build
    writes SDK_MARKER last, recording the venv's tree as it left it (venv_tree). A run reads the venv under a shared lock
    on the key, which it holds until it ends, so runs at other shas share a finished venv: the venv is used only when its
    marker names its key, its tree matches the recorded one (venv_changes: so nothing a leg of an earlier run left in it,
    such as a .pth file, reaches this run), and its probe reports the pin's SDK, the modules the pytest leg needs, and
    the base interpreter's version. Anything else (no marker: a build that died) is rebuilt under the exclusive lock,
    which waits for every other run holding it, so a rebuild never removes a venv another run's pytest leg is running
    in. A build that fails (a command exits nonzero or times out, the venv's SDK is not the pin, a module the pytest leg
    needs is missing) removes the venv and is Refused, naming the step, the command and the log: exit 2, nothing
    recorded, as for a failed --leg setup."""
    # An absolute path: the build's commands run in a directory of their own under TMPDIR, removed when this returns,
    # so nothing the build leaves (pip's cache under its private HOME, get-pip.py) is in TMPDIR while the legs run.
    python = os.path.abspath(python) if os.sep in python else (shutil.which(python) or python)
    plan = read_install_plan(checkout, sha)
    work = tempfile.mkdtemp(prefix="sdk-", dir=tmpdir)
    try:
        return _venv_environment(_sdk_spec(sha, python, plan), sha, python, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _sdk_spec(sha, python, plan):
    """The pytest leg's environment as _venv_environment builds and checks it: the install steps' commands, the SDK at
    ci.yml's pin and the modules the pytest leg needs (PYTEST_MODULES)."""
    dist, pin = plan["dist"], plan["pin"]

    def stale(got, _vpy):
        if got["dists"].get(dist) != pin or got["missing"]:
            return "it now has %s %s and lacks %s" % (dist, got["dists"].get(dist), ", ".join(got["missing"]) or "nothing")
        return None

    def refuse(got, _vpy):
        if got["dists"].get(dist) != pin:
            return "after the install steps the venv's %s is %s, not ci.yml's pin %s" % (dist, got["dists"].get(dist), pin)
        if got["missing"]:
            return "after the install steps the venv lacks %s, which the pytest leg needs" % ", ".join(got["missing"])
        return None

    return {"what": "the pytest leg's environment", "base_what": "the pytest interpreter", "base_check": None,
            "root": sdk_dir(), "marker": SDK_MARKER, "key": lambda base: sdk_key(python, base, plan),
            "where": lambda key: "the pytest leg's environment %s (%s==%s at %s, from %s)" % (key, dist, pin, short(sha), python),
            "building": "%s==%s from %s" % (dist, pin, python),
            "steps": [(s["step"], cmd) for s in plan["steps"] for _kind, cmd in s["commands"]],
            "dists": [dist], "modules": [], "whole": False, "record": {"dist": dist, "pin": pin, "version": None},
            "stale": stale, "refuse": refuse, "fill": lambda rec, got: rec.update(version=got["dists"][dist]),
            "marker_doc": lambda got: {"dist": dist, "pin": pin, "version": got["dists"][dist]},
            "ready": lambda rec: "the pytest leg's environment: %s %s (ci.yml's pin) in %s" % (dist, rec["version"], rec["path"])}


def served_environment(checkout, sha, python, tmpdir, served):
    """The served leg's interpreter and its record for the result (runner.served), and the VenvHold the run keeps until
    it ends: a venv under <state dir>/sweeps/served/<key>, built from `python` (--served-python, default --python) with
    the served step's own pip lines as ci.yml writes them at the swept sha (read_served_step) and nothing else, so
    without the SDK, which the python job's install steps install and CI's served step does not; or the venv a finished
    build left under the same key (served_key: the pip lines, the interpreter's path and whole version). Built, marked,
    checked and locked as the pytest leg's venv is (_venv_environment). Refused before anything is recorded when `python`
    is not the MAJOR.MINOR the served step's job sets up (served["python"], read from ci.yml), and when the build fails,
    leaves the venv without a distribution its pip lines name, or leaves its directory without python3 as the same file
    as its python (the served tests' kernels run the first python3 on the leg's PATH, which leads with that directory);
    a finished venv found so is built again. The record: job, step, env, globs and python_ci (that version) as read_served_step read them, install
    (the pip lines), key, path, python (the venv's), python_version (its whole sys.version), base_python and
    base_version, packages ({distribution: version} of every distribution in the venv) and plugins (the pytest plugins
    they declare, which pytest loads on its own), sdk (the SDK's version there, None when it is not installed) and
    sdk_importable, tree, files, built, build_s and log."""
    python = os.path.abspath(python) if os.sep in python else (shutil.which(python) or python)
    plan = read_install_plan(checkout, sha)
    work = tempfile.mkdtemp(prefix="served-", dir=tmpdir)
    try:
        rec, hold = _venv_environment(_served_spec(sha, python, plan, served), sha, python, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    rec.update(job=served["job"], step=served["step"], env=dict(served["env"]), globs=list(served["globs"]),
               python_ci=served["python"], install=[list(cmd) for cmd in served["install"]])
    return rec, hold


def _served_spec(sha, python, plan, served):
    """The served leg's environment as _venv_environment builds and checks it: the served step's pip lines on the Python
    version its job sets up, every distribution they name present after the build, every distribution and pytest plugin
    in the venv recorded, and whether the SDK is there."""
    wanted = list(served["requirements"])
    module = plan["module"].split(".")[0] if plan.get("module") else None

    def base_check(base):
        got = ".".join(str(base.get("version") or "").split(".")[:2])
        if got != served["python"]:
            raise Refused("the served leg's venv is built from Python %s, which %s at %s sets up for its step %r (the %s job); "
                          "--served-python %s is %s (it defaults to --python): pass --served-python a Python %s interpreter "
                          "(nothing need be installed in it: the venv holds what the served step's pip line installs)"
                          % (served["python"], CI_WORKFLOW, short(sha), served["step"], served["job"], python,
                             base.get("version"), served["python"]))

    def lacking(got):
        return [d for d in wanted if got["dists"].get(d) is None]

    def python3_fault(vpy):
        # The served tests' kernels are started as bin/romp-kernel, whose first line is `#!/usr/bin/env python3`, so they
        # run the first python3 on the leg's PATH (build_path: the venv's directory first). What the venv holds is what
        # they run only when that python3 is the venv's python: in its directory (so it reads the same pyvenv.cfg) and
        # the same file.
        python3 = shutil.which("python3", path=build_path(vpy, os.environ))
        if (python3 is not None and os.path.dirname(os.path.abspath(python3)) == os.path.dirname(vpy)
                and os.path.samefile(python3, vpy)):
            return None
        return ("the served tests' kernels run python3 from the leg's PATH (bin/romp-kernel starts with #!/usr/bin/env "
                "python3), and there that is %s, not the venv's python, so what the venv holds does not hold for them"
                % (python3 or "not found"))

    def stale(got, vpy):
        return "it lacks %s" % ", ".join(lacking(got)) if lacking(got) else python3_fault(vpy)

    def refuse(got, vpy):
        if lacking(got):
            return "after the served step's pip line the venv lacks %s, which the line installs" % ", ".join(lacking(got))
        return python3_fault(vpy)

    def fill(rec, got):
        rec.update(packages=dict(sorted(got["all"].items())), plugins=list(got["plugins"]), sdk=got["dists"].get(plan["dist"]),
                   sdk_importable=bool(module and (got.get("found") or {}).get(module)))

    return {"what": "the served leg's environment", "base_what": "--served-python", "base_check": base_check,
            "root": served_dir(), "marker": SERVED_MARKER, "key": lambda base: served_key(python, base, served),
            "where": lambda key: "the served leg's environment %s (the served step's pip line at %s, Python %s from %s)"
                                 % (key, short(sha), served["python"], python),
            "building": "the served step's pip line on Python %s from %s" % (served["python"], python),
            "steps": [(served["step"], cmd) for cmd in served["install"]],
            "dists": wanted + [plan["dist"]], "modules": [module] if module else [], "whole": True,
            "record": {"packages": None, "plugins": None, "sdk": None, "sdk_importable": None},
            "stale": stale, "refuse": refuse, "fill": fill,
            "marker_doc": lambda got: {"install": [list(cmd) for cmd in served["install"]], "packages": got["all"],
                                       "plugins": got["plugins"]},
            "ready": lambda rec: "the served leg's environment: Python %s from the served step's pip line (%d packages, "
                                 "pytest plugins: %s) in %s" % (served["python"], len(rec["packages"]),
                                                                ", ".join(rec["plugins"]) or "none", rec["path"])}


def _venv_check(spec, venv, vpy, key, base, env):
    """(None, probe, tree) when the venv is a finished build of `key` that nothing has changed since, else (why, None,
    None)."""
    try:
        with open(os.path.join(venv, spec["marker"])) as f:
            marker = json.load(f)
    except (OSError, ValueError):
        return "no finished build", None, None
    if not isinstance(marker, dict) or marker.get("key") != key:
        return "its marker names another key", None, None
    if not isinstance(marker.get("tree"), dict):
        return "its marker records no tree", None, None
    try:
        tree = venv_tree(venv)
    except OSError as e:
        return "its tree cannot be read: %s" % e, None, None
    moved = venv_changes(marker["tree"], tree)
    if moved:
        return ("it is not the tree its build wrote: %d path%s, %s%s" % (len(moved), "" if len(moved) == 1 else "s",
                ", ".join(moved[:3]), ", ..." if len(moved) > 3 else "")), None, None
    try:
        got = probe(vpy, env, spec["dists"], what=spec["what"] + "'s interpreter", modules=spec["modules"], whole=spec["whole"])
    except Refused as e:
        return str(e), None, None
    why = spec["stale"](got, vpy)
    if why:
        return why, None, None
    if got.get("full") != base.get("full"):
        return "its interpreter is %r, not %r" % (got.get("full"), base.get("full")), None, None
    return None, got, tree


def _tree_digest(tree):
    return hashlib.sha256(json.dumps(tree, sort_keys=True).encode("utf-8")).hexdigest()


def _venv_environment(spec, sha, python, tmpdir):
    """A venv the runner builds from `python` as `spec` describes it (_sdk_spec, _served_spec), and its record, and the
    VenvHold the run keeps until it ends. The venv is <spec root>/<key>, its log <key>.log and its lock <key>.lock beside
    it. A run reads it under a shared lock on the key, which it holds until it ends, and uses it only when its marker
    names its key, its tree matches the one its build recorded (venv_changes), its probe passes the spec's check and it
    reports the base interpreter's version; anything else is built again under the exclusive lock, which waits for
    every other run holding it (_venv_build). Refused after SDK_ATTEMPTS reads that each find it stale."""
    env = build_env(python, tmpdir)
    base = probe(python, env, what=spec["base_what"])
    if spec["base_check"]:
        spec["base_check"](base)
    key = spec["key"](base)
    root = spec["root"]
    os.makedirs(root, mode=0o700, exist_ok=True)
    venv = os.path.join(root, key)
    vpy = os.path.join(venv, "bin", "python")
    log = venv + ".log"
    where = spec["where"](key)
    rec = {"key": key, "path": venv, "python": vpy}
    rec.update(spec["record"])
    rec.update({"python_version": None, "tree": None, "files": None, "built": False, "build_s": 0.0, "log": log,
                "base_python": os.path.abspath(python), "base_version": base.get("version")})
    lock = open(venv + ".lock", "a+")
    stale = None
    try:
        for _attempt in range(SDK_ATTEMPTS):
            _flock(lock, fcntl.LOCK_SH, sha, "waiting for another run's build of %s %s" % (spec["what"], key))
            stale, got, tree = _venv_check(spec, venv, vpy, key, base, env)
            if stale is None:
                spec["fill"](rec, got)
                rec.update(python_version=got.get("full"), tree=_tree_digest(tree), files=len(tree))
                print("sweep %s: %s, %s" % (short(sha), spec["ready"](rec), "built in %.0f s" % rec["build_s"] if rec["built"]
                                             else "built earlier"), flush=True)
                return rec, VenvHold(lock, venv, tree, spec["marker"])
            fcntl.flock(lock, fcntl.LOCK_UN)
            _flock(lock, fcntl.LOCK_EX, sha, "waiting for the other runs using %s %s to finish, to rebuild it (%s)"
                   % (spec["what"], key, stale))
            stale, got, tree = _venv_check(spec, venv, vpy, key, base, env)
            if stale is not None:
                _venv_build(spec, venv, vpy, python, base, env, log, tmpdir, where, sha, key, stale, rec)
            fcntl.flock(lock, fcntl.LOCK_UN)
        raise Refused("%s does not match its own build after %d builds (%s); log %s" % (where, SDK_ATTEMPTS, stale, log))
    except BaseException:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
        raise


def _venv_build(spec, venv, vpy, python, base, env, log, tmpdir, where, sha, key, stale, rec):
    """Remove whatever is at the venv's path and build it, under the exclusive lock; the marker, written last, records
    the tree the build left."""
    if os.path.lexists(venv):
        print("sweep %s: rebuilding %s %s (%s)" % (short(sha), spec["what"], key, stale), flush=True)
        shutil.rmtree(venv, ignore_errors=True)
        if os.path.lexists(venv):
            raise Refused("%s: the stale venv could not be removed (%s); remove it by hand" % (where, venv))
    print("sweep %s: building %s %s: %s; log %s" % (short(sha), spec["what"], key, spec["building"], log), flush=True)
    t0 = time.monotonic()
    try:
        _build_venv(venv, python, base, spec["steps"], env, log, tmpdir, where)
        got = probe(vpy, env, spec["dists"], what=spec["what"] + "'s interpreter", modules=spec["modules"], whole=spec["whole"])
        why = spec["refuse"](got, vpy)
        if why:
            raise Refused("%s: %s; log %s" % (where, why, log))
        if got.get("full") != base.get("full"):
            raise Refused("%s: the venv's interpreter is %r, not %r, the interpreter it was built from; log %s"
                          % (where, got.get("full"), base.get("full"), log))
        tree = venv_tree(venv)
        doc = {"key": key}
        doc.update(spec["marker_doc"](got))
        doc.update(python=os.path.abspath(python), python_version=base.get("full"), built=now(), tree=tree)
        write_result(os.path.join(venv, spec["marker"]), doc)
    except BaseException:
        shutil.rmtree(venv, ignore_errors=True)
        raise
    rec.update(built=True, build_s=round(time.monotonic() - t0, 2))


def parse_wraps(values):
    wraps = {}
    for v in values or []:
        leg, sep, prefix = v.partition("=")
        if not sep or (leg not in LEGS and leg != "*"):
            raise Refused("--wrap %r: expected LEG=PREFIX with LEG one of %s or *" % (v, ", ".join(LEGS)))
        argv = shlex.split(prefix)
        if not argv:
            raise Refused("--wrap %r: the prefix is empty" % v)
        wraps[leg] = argv
    return wraps


def pytest_cmd(python, workers):
    """The pytest leg's command: `<python> -m pytest tests -n <workers>`, PYTEST_FLAGS, PYTEST_ISOLATION and one --ignore
    per PYTEST_IGNORED entry. The served globs' files are collected, as CI's Python cells collect them."""
    return [python, "-m", "pytest", "tests", "-n", str(workers), *PYTEST_FLAGS, *PYTEST_ISOLATION,
            *("--ignore=%s" % p for p in sorted(PYTEST_IGNORED))]


def served_cmd(python, files, also=()):
    """The served leg's command, one process as CI's served step runs it: `<python> -m pytest <files> <also>`,
    SERVED_FLAGS, PYTEST_ISOLATION. `also` is the node ids the pytest leg skipped for want of the deps (deps_skipped)."""
    return [python, "-m", "pytest", *files, *also, *SERVED_FLAGS, *PYTEST_ISOLATION]


# The pytest leg's short summary (PYTEST_FLAGS' -rfEs --no-fold-skipped), read closed (round 2, Class C): the section's
# header, then one line per report, each starting with its kind. The kinds are derived from pytest's own source (8.4.2
# and 9.1.1: _pytest/terminal.py's short_test_summary and pytest_report_teststatus, _pytest/runner.py,
# _pytest/skipping.py, and 9.1.1's _pytest/subtests.py; pytest-xdist and pytest-timeout add none): PASSED FAILED SKIPPED
# ERROR XFAIL XPASS, then a space and the node id; and pytest 9's subtest kinds SUBPASSED SUBFAILED SUBSKIPPED SUBXFAIL,
# then with no space the subtest's description ([msg], (k=v, ...), both joined by a space, or (<subtest>)), a space and
# the node id of the test the subtest belongs to. Under -rfEs only SKIPPED, SUBSKIPPED, FAILED, SUBFAILED and ERROR
# appear. A skip is `SKIPPED <node id> - <reason>` (a collection-time skip names its module) or `SUBSKIPPED<description>
# <node id> - <reason>`, whose node id the served leg runs whole; a node id runs to the first ` - `, and a reason or a
# message can run on over more lines.
_SUMMARY_HEAD = re.compile(r"=+ short test summary info =+")
_SUMMARY_WORD = re.compile(r"(?:PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) |(?:SUBPASSED|SUBFAILED|SUBSKIPPED|SUBXFAIL)[\[(]")
_SKIP_KIND = re.compile(r"SKIPPED |SUBSKIPPED[\[(]")
_NODE_ID_REASON = re.compile(r"(tests/\S(?:.*?\S)?)(?: - (.*))?")
_SKIPPED_LINE = re.compile(r"SKIPPED " + _NODE_ID_REASON.pattern)
# What comes before a SUBSKIPPED line's node id: the word and a description, which ends in "] " or ") " right before the
# node id. A description can hold anything, "] tests/" and ") tests/" included, so a line whose node id could start at
# more than one such place is not read (round 2, decision 5), never anchored at the first.
_SUBSKIPPED_HEAD = re.compile(r"SUBSKIPPED(?:\[.*\](?: \(.*\))?|\(.*\)) ")
_SUBSKIPPED_ANCHOR = re.compile(r"(?<=[\])] )tests/")
# A line shaped like a kind: an upper-case word, a description as a subtest word has, and a node id (every node id the
# pytest leg collects starts with tests). One that is none of the kinds above is a kind this reader does not read, never
# a reason running on. (A bare upper-case first word is no test: a message running on over lines can start with one.)
_KIND_SHAPED = re.compile(r"[A-Z][A-Z_]+(?:\[.*?\])?(?: ?\(.*?\))? tests(?:/|\s|$)")


def _brackets_balance(nodeid):
    """Whether every [ in `nodeid` is closed by a later ] and no ] closes one it did not open. A node id read short, cut
    at a ` - ` inside its parametrize id (`tests/x.py::test_p[a - b]` read as `tests/x.py::test_p[a`), leaves one open."""
    depth = 0
    for ch in nodeid:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _skip_line(line):
    """(node id, reason, None) of a line of a skip kind (_SKIP_KIND), or (None, None, why) when this reader cannot tell
    which one test it names: no node id where one belongs (the folded form `SKIPPED [2] tests/x.py:3: ...`, which
    --no-fold-skipped rules out, or a SUBSKIPPED line that a description holding a newline split), a SUBSKIPPED node id
    that could start at more than one place or that holds " tests/", or a node id whose brackets do not balance."""
    if line.startswith("SKIPPED "):
        m = _SKIPPED_LINE.fullmatch(line)
        if not m:
            return None, None, "a skip whose node id this reader cannot find"
    else:
        found = [m for m in (_NODE_ID_REASON.fullmatch(line, a.start()) for a in _SUBSKIPPED_ANCHOR.finditer(line)
                             if _SUBSKIPPED_HEAD.fullmatch(line, 0, a.start()))
                 if m]
        if not found:
            return None, None, "a skip whose node id this reader cannot find"
        if len(found) > 1:
            return None, None, "a subtest skip whose node id could start at %d places" % len(found)
        m = found[0]
        if " tests/" in m.group(1):
            return None, None, "a subtest skip whose node id holds ' tests/', so it could start there"
    if not _brackets_balance(m.group(1)):
        return None, None, "a skip whose node id's brackets do not balance"
    return m.group(1), m.group(2) or "", None


def deps_skipped(path, served_files, others=None):
    """([node id, ...], None) of the tests outside `served_files` (the served globs' expansion) that the pytest leg's log
    at `path` shows skipped for want of the extension's node_modules or a browser: each SKIPPED and SUBSKIPPED line of
    its short summary whose reason DEPS_SKIP matches, in the log's order, each once (a subtest skip names the test it
    belongs to). `others`, a list when given, gets [node id, reason] of every other skip outside `served_files`, the ones
    DEPS_SKIP did not select, so a deps reason it misses can be seen in the record rather than run in no leg unnoticed.
    (None, why) when the set is not known, and the served leg, which would run it, is then red naming why rather than
    run without it: the log cannot be read; it holds no closing summary line (pytest did not finish, so its summary of
    skips is not whole); or its short summary holds a line this reader does not read, each named in why. The reader is
    closed: a line shaped like a kind that is none of the kinds, a skip line that does not name exactly one test
    (_skip_line), and a non-blank line before any kind line are not read. A line of no kind's shape after a kind line
    runs its reason or message on."""
    data = _read_log(path) if path else None
    if data is None:
        return None, "the pytest leg's log cannot be read"
    if not PYTEST_SUMMARY.findall(data):
        return None, ("the pytest leg's log has no closing summary line (it did not finish), so the tests it skipped for want "
                      "of the extension's node_modules or a browser are not known")
    lines = data.split("\n")
    heads = [i for i, line in enumerate(lines) if _SUMMARY_HEAD.fullmatch(line.strip())]
    skips, cur, seen, unread = [], None, False, []
    for line in lines[heads[-1] + 1:] if heads else ():
        if _SKIP_KIND.match(line):
            nodeid, reason, why = _skip_line(line)
            if why is None:
                cur = [nodeid, reason]
                skips.append(cur)
                seen = True
            else:
                unread.append((why, line))
                cur = None
        elif _SUMMARY_WORD.match(line):
            cur, seen = None, True
        elif line.startswith("=") or PYTEST_SUMMARY.fullmatch(line):
            cur = None
        elif line.strip() and (_KIND_SHAPED.match(line) or not seen):
            unread.append(("a kind this reader does not read" if _KIND_SHAPED.match(line) else "a line before any kind line",
                           line))
            cur = None
        elif cur is not None:
            cur[1] += "\n" + line
    if unread:
        return None, ("the pytest leg's short summary holds %d line%s this reader does not read (%s), so the tests it skipped "
                      "for want of the extension's node_modules or a browser are not known"
                      % (len(unread), "" if len(unread) == 1 else "s",
                         "; ".join("%s: %r" % (why, line[:200]) for why, line in unread[:3])))
    served = set(served_files)
    out = [nodeid for nodeid, reason in skips if nodeid.split("::")[0] not in served and DEPS_SKIP.search(reason)]
    if others is not None:
        others.extend([nodeid, reason] for nodeid, reason in skips
                      if nodeid.split("::")[0] not in served and not DEPS_SKIP.search(reason))
    return list(dict.fromkeys(out)), None


def served_also(pytest_rec):
    """([node id, ...], None): the tests the served leg also runs, the set the pytest leg's record names (its
    deps_skipped); (None, why) when the record names none, or names why it is not known."""
    d = pytest_rec.get("deps_skipped") if isinstance(pytest_rec, dict) else None
    if isinstance(d, dict) and isinstance(d.get("tests"), list) and all(isinstance(t, str) for t in d["tests"]):
        return list(d["tests"]), None
    known = d.get("error") if isinstance(d, dict) and isinstance(d.get("error"), str) else "the pytest leg records none"
    return None, ("the tests outside the served globs that the pytest leg skipped for want of the deps are not known (%s), "
                  "and the served leg does not run without them" % known)


def plan_legs(tree, python, workers, served=None):
    """{leg: record} with each leg's owed decision, command and cwd, planned over the fresh checkout; nothing runs
    here. deps (npm ci from the sha's lockfile) is owed whenever the sha has vscode-extension/package.json, since a
    fresh checkout never holds node_modules, and so are the webview legs and served, whatever the head changed
    (WEBVIEW_WHY, SERVED_WHY). The pytest leg collects all of tests/, the served globs' files included, as CI's Python
    cells do. `served` is ci.yml's served step as read_served_step reads it (read from the tree when not given): the
    served leg runs the files its globs select, in one process, and at run time also the tests the pytest leg skipped
    for want of the deps (deps_skipped), which join its command before it runs."""
    legs = {}
    package = os.path.exists(os.path.join(tree, "vscode-extension", "package.json"))
    served = read_served_step(tree, "HEAD") if served is None else served
    served_files, served_empty = expand(tree, served["globs"])
    for name in LEGS:
        rec = {"owed": True, "rc": None}
        if name == "deps":
            if not package:
                rec.update(owed=False, why=NO_PACKAGE_JSON)
            else:
                rec.update(cmd=list(DEPS_CMD), cwd="vscode-extension", why="a fresh checkout has no vscode-extension/node_modules")
        elif name == "pytest":
            rec.update(cmd=pytest_cmd(python, workers), cwd=".", ignored=dict(PYTEST_IGNORED))
        elif name == SERVED_LEG:
            if not package:
                rec.update(owed=False, why=NO_PACKAGE_JSON)
            else:
                rec.update(cmd=served_cmd(python, served_files), cwd=".", globs=list(served["globs"]), why=SERVED_WHY)
                if served_empty:
                    rec.update(empty_glob=served_empty)
        elif name in GLOBS:
            files, empty = expand(tree, GLOBS[name])
            tool = ["bats", "--print-output-on-failure"] if name == "bats" else ["node", "--test"]
            rec.update(cmd=tool + files, cwd=".", globs=list(GLOBS[name]))
            if empty:
                rec.update(empty_glob=empty)
        elif name == "ledger":
            if os.path.exists(os.path.join(tree, LEDGER_SCRIPT)):
                rec.update(cmd=[sys.executable, LEDGER_SCRIPT, "check"], cwd=".")
            else:
                rec.update(owed=False, why=NO_LEDGER_SCRIPT)
        else:
            npm = list(NPM_CMDS[name])
            if not package:
                rec.update(owed=False, why=NO_PACKAGE_JSON)
            else:
                rec.update(cmd=npm, cwd="vscode-extension", why=WEBVIEW_WHY)
        legs[name] = rec
    return legs


# What a leg's record holds from its plan (plan_legs, and for the served leg the tests it also runs, `also`, set before
# it runs, with `blocked` when that set is not known); the rest is the attempt, which a --leg re-run replaces. The
# pytest leg's attempt records the tests it skipped for want of the deps (`deps_skipped`, deps_skipped).
PLAN_KEYS = ("owed", "why", "cmd", "cwd", "ignored", "globs", "empty_glob", "also", "blocked")
ATTEMPT_KEYS = ("rc", "error", "started", "finished", "log", "summary", "tests", "failed", "wrap", "env_dropped", "env_set",
                "left_running", "deps_skipped")

PYTEST_SUMMARY = re.compile(r"^=*\s*(\d+ (?:failed|passed|skipped|errors?|deselected|xfailed|xpassed)\b[^\n]* in [0-9.]+s\b[^\n]*?)\s*=*$", re.M)
# node --test's closing counts: `# pass N` from the TAP reporter (the default when stdout is not a terminal on
# node 22), `\u2139 pass N` from the spec reporter (the default on later releases).
NODE_COUNT = re.compile(r"^(?:#|\u2139) (pass|fail) (\d+)\s*$", re.M)


def _read_log(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except OSError:
        return None


def count_tests(name, path):
    """(passed, failed) for a test leg, counted from its log: pytest's last summary line for the pytest and served legs
    (PYTEST_LEGS; failed counts failures and errors, so a skip the served step's switch turned into a failure counts),
    bats' `ok` and `not ok` lines, node's last `pass` and `fail` counts. (None, None) when the log holds no count, which
    the verdict reads as no test ran."""
    data = _read_log(path)
    if data is None:
        return None, None
    if name in PYTEST_LEGS:
        hits = PYTEST_SUMMARY.findall(data)
        if not hits:
            return None, None
        words = dict((w, int(n)) for n, w in re.findall(r"(\d+) (failed|passed|errors?)\b", hits[-1]))
        return words.get("passed", 0), words.get("failed", 0) + words.get("error", 0) + words.get("errors", 0)
    if name == "bats":
        return len(re.findall(r"^ok ", data, re.M)), len(re.findall(r"^not ok ", data, re.M))
    counts = {}
    for word, n in NODE_COUNT.findall(data):
        counts[word] = int(n)
    if "pass" not in counts:
        return None, None
    return counts["pass"], counts.get("fail", 0)


def summarize_log(name, path):
    """A display-only summary: pytest's last result line (the pytest and served legs), bats' ok and not-ok counts,
    node's pass and fail counts."""
    data = _read_log(path)
    if data is None:
        return None
    if name in PYTEST_LEGS:
        hits = PYTEST_SUMMARY.findall(data)
        return hits[-1].strip() if hits else None
    if name == "bats":
        ok = len(re.findall(r"^ok ", data, re.M))
        bad = len(re.findall(r"^not ok ", data, re.M))
        return "%d ok, %d not ok" % (ok, bad)
    counts = dict(NODE_COUNT.findall(data))
    if counts:
        return "pass %s, fail %s" % (counts.get("pass", "?"), counts.get("fail", "?"))
    return None


def leg_argv(wrap, env, cmd, shown=False):
    """The leg's argv: the wrap, then `env -i` with every pair of `env`, then the command. `shown` writes each pair as
    NAME=... for the log's header, which records no value of the leg's environment."""
    pairs = ["%s=..." % k if shown else "%s=%s" % (k, env[k]) for k in sorted(env)]
    return list(wrap or []) + [ENV_BIN, "-i"] + pairs + list(cmd)


def run_leg(tree, name, rec, wraps, ctx, logdir):
    """Run one owed leg and fill in its record. A glob that matched nothing, a set of tests it must also run that is
    not known (`blocked`), a cwd that does not exist or a command that cannot start leaves rc empty with the reason in
    `error`: the leg is red, never run bare."""
    env, dropped, extra = leg_env(name, ctx)
    wrap = wraps.get(name, wraps.get("*"))
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = os.path.join(logdir, "%s.%s.log" % (name, stamp))
    for k in ATTEMPT_KEYS:
        rec.pop(k, None)
    rec.update(started=now(), finished=None, rc=None, log=log, env_dropped=dropped, env_set=extra, wrap=wrap)
    cwd = os.path.join(tree, rec.get("cwd") or ".")
    if rec.get("empty_glob"):
        rec["error"] = "no files matched %s" % rec["empty_glob"]
    elif rec.get("blocked"):
        rec["error"] = rec["blocked"]
    elif not os.path.isdir(cwd):
        rec["error"] = "no directory %s in the tree" % rec.get("cwd")
    else:
        argv = leg_argv(wrap, env, rec["cmd"])
        try:
            with open(log, "w") as out:
                out.write("# leg: %s\n# cwd: %s\n# argv: %s\n" % (
                    name, rec.get("cwd") or ".", " ".join(shlex.quote(a) for a in leg_argv(wrap, env, rec["cmd"], shown=True))))
                out.flush()
                # The wrap (or env itself) runs with the runner's environment; the leg gets exactly `env`. The leg is
                # its own process group, so a stop reaches all of it (stop_leg).
                p = subprocess.Popen(argv, cwd=cwd, env=dict(os.environ), stdin=subprocess.DEVNULL, stdout=out,
                                     stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    rc = wait_leg(p)
                except BaseException:
                    stop_leg(p)
                    raise
                if rc is None:
                    rec["error"] = "its exit status was lost: something other than the runner reaped it"
                else:
                    rec["rc"] = rc
            # Whatever the leg left running (a daemon a test started, a detached browser) is killed before the next leg.
            rec["left_running"] = reap_descendants()
        except OSError as e:
            rec["error"] = "could not start: %s" % e
        rec["summary"] = summarize_log(name, log)
        if name in TEST_LEGS:
            rec["tests"], rec["failed"] = count_tests(name, log)
    rec["finished"] = now()


def script_blob():
    p = subprocess.run(["git", "hash-object", os.path.realpath(__file__)], env=_git_env(), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.strip() if p.returncode == 0 else None


def parse_flakes(values, only):
    """{leg: known-flake entry} from the --flake values. `LEG=TEXT` names its leg; a bare TEXT names every --leg leg
    that has no named one, and is refused on a full run, which must say which leg each flake is for."""
    named, bare = {}, []
    for v in values or []:
        leg, sep, text = v.partition("=")
        if sep and leg in LEGS:
            if not text.strip():
                raise Refused("--flake %s= names no known flake: give the test and where it is recorded as a known flake" % leg)
            if leg in named:
                raise Refused("--flake names %s twice" % leg)
            named[leg] = text.strip()
        elif v.strip():
            bare.append(v.strip())
    if len(bare) > 1:
        raise Refused("--flake: give one known flake per leg, as LEG=TEXT")
    if bare and not only:
        raise Refused("--flake on a full run names the leg it is for: --flake LEG=TEXT (the leg that failed, the test, and "
                      "where it is recorded as a known flake)")
    for leg in only:
        if leg not in named and bare:
            named[leg] = bare[0]
    return named


def cmd_run(args):
    # Before TMPDIR or the checkout exists, so every exit path removes both (A5).
    install_stop_handlers()
    tree = os.path.realpath(args.tree or git(os.getcwd(), "rev-parse", "--show-toplevel"))
    if git(tree, "rev-parse", "--is-inside-work-tree", check=False).stdout.strip() != "true":
        raise Refused("%s is not a git working tree" % tree)
    tree = git(tree, "rev-parse", "--show-toplevel")
    sha = git(tree, "rev-parse", "HEAD")
    branch = git(tree, "symbolic-ref", "--short", "-q", "HEAD", check=False).stdout.strip() or None
    wraps = parse_wraps(args.wrap)
    only = list(dict.fromkeys(args.leg or []))
    for name in only:
        if name not in LEGS:
            raise Refused("--leg %s: not a leg (%s)" % (name, ", ".join(LEGS)))
    flakes = parse_flakes(args.flake, only)
    if only and any(name not in flakes for name in only):
        raise Refused("--leg re-runs a leg only after a known flake: name it with --flake (the test and where it is recorded "
                      "as a known flake); anything else is a failure: fix it and sweep the new head")
    if only and set(flakes) - set(only):
        raise Refused("--flake names %s, which this --leg re-run does not run" % ", ".join(sorted(set(flakes) - set(only))))
    # The batcher's tree is read for its HEAD sha and its branch only: the legs run in a private checkout of the sha,
    # so uncommitted edits there are not swept, and the batcher is told so.
    dirty = uncommitted_count(tree)
    if dirty:
        print("sweep %s: %s has %d uncommitted edit%s (git status); they are not swept: the legs run in a private "
              "checkout of %s" % (short(sha), tree, dirty, "" if dirty == 1 else "s", short(sha)), flush=True)
    # The interpreter the pytest leg's environment is built from (sdk_environment), and by default the one the served
    # leg's is built from (served_environment, --served-python); each leg runs in the venv built for it.
    python = args.python or sys.executable
    d = sweeps_dir()
    os.makedirs(d, mode=0o700, exist_ok=True)
    path = result_path(sha)
    lock_path = os.path.join(d, sha + ".lock")
    lock = open(lock_path, "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise Refused("a sweep of %s is already running (%s)" % (short(sha), lock_path))
    try:
        return _run_locked(args, tree, sha, branch, python, wraps, only, path, flakes)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def load_history(path, sha, for_leg):
    """The result file at `path` to append a run to, or None when there is none. Results are append-only: a file
    this runner cannot read is kept and refused, never overwritten; a schema-1 file (the runner before round 1)
    is moved aside to <sha>.schema-1.json, named, since its runs swept the batcher's own tree and no reader counts
    them, and so is a schema-2 file holding a run that records no private checkout (to <sha>.no-checkout.json)."""
    try:
        data = _load(path)
    except FileNotFoundError:
        if for_leg:
            raise Refused("no result at %s to re-run a leg in; run the full sweep" % short(sha))
        return None
    except (OSError, ValueError) as e:
        raise Refused("the result at %s is unreadable (%s)%s" % (short(sha), e, "; run the full sweep" if for_leg else
                      "; it is kept, since results are append-only: move it aside to sweep this sha again"))
    if data.get("schema") == 1 and type(data.get("schema")) is int:
        if for_leg:
            raise Refused("the result at %s is unreadable (schema 1, %s); run the full sweep" % (short(sha), SCHEMA_1_TEXT))
        aside = path[:-len(".json")] + ".schema-1.json"
        os.replace(path, aside)
        print("sweep %s: moved the schema-1 result aside to %s (%s)" % (short(sha), aside, SCHEMA_1_TEXT), flush=True)
        return None
    if data.get("schema") != SCHEMA or type(data.get("schema")) is not int or data.get("sha") != sha:
        raise Refused("the result at %s is not a record of %s this runner writes (schema %r, sha %s)%s"
                      % (path, short(sha), data.get("schema"), short(str(data.get("sha"))), "; run the full sweep" if for_leg else
                         "; it is kept, since results are append-only: move it aside to sweep this sha again"))
    blind = no_checkout_runs(data["runs"])
    if blind:
        # A schema-2 file whose runs swept the batcher's own tree (no private checkout recorded) is treated as a
        # schema-1 file is: no reader counts it, so it is moved aside, named.
        what = "run %s records no private checkout, %s" % (", ".join(str(n) for n in blind), SCHEMA_1_TEXT)
        if for_leg:
            raise Refused("the result at %s is unreadable (%s); run the full sweep" % (short(sha), what))
        aside = path[:-len(".json")] + ".no-checkout.json"
        os.replace(path, aside)
        print("sweep %s: moved the result aside to %s (%s)" % (short(sha), aside, what), flush=True)
        return None
    return data


def _finish(step, stopped):
    """Run one cleanup step to its end (round 2, correctness-3): a stop signal that arrives during it raises Stopped, which
    is kept in `stopped`, and the step runs again from its start, now with the stop signals ignored (_on_stop ignores
    every one after the first), so the steps after it run too and the caller raises the stop once they are done."""
    try:
        step()
    except Stopped as e:
        stopped.append(e)
        step()


def _retire_if_changed(hold, sha):
    """Retire a venv whose tree is not the one its build wrote (VenvHold.retire), naming what differs."""
    late = hold.changes()
    if late:
        why = hold.retire()
        print("sweep %s: %s is not the tree its build wrote (%d path%s: %s%s); %s" % (
            short(sha), hold.venv, len(late), "" if len(late) == 1 else "s", ", ".join(late[:3]),
            ", ..." if len(late) > 3 else "", "the next run that uses it builds it again" if why is None
            else "%s, so remove the venv by hand" % why), flush=True)


def _run_locked(args, tree, sha, branch, python, wraps, only, path, flakes=None):
    flakes = dict(flakes or {})
    logdir = os.path.join(sweeps_dir(), "logs", sha)
    data = load_history(path, sha, bool(only))
    history = read_history(data["runs"]) if data else None
    if history and history["never"]:
        raise Refused("the result at %s holds records no runner writes (%s)%s" % (short(sha), "; ".join(history["never"]),
                      "; run the full sweep" if only else
                      "; it is kept, since results are append-only: move it aside to sweep this sha again"))
    if history and history["dead"]:
        raise Refused("no run at %s can pass: %s; fix it and sweep the new head" % (short(sha), history["dead"]))
    run = {"kind": "leg" if only else "full", "sha": sha, "branch": branch, "tree": tree, "started": now(), "finished": None,
           "flakes": flakes, "runner": {"script_blob": script_blob(), "python": python, "python_version": ""},
           "legs": {}, "verdict": "running", "red": [], "invalid": None}
    base_legs = {}
    if only:
        rec, why = effective(data)
        if rec is None or any(name not in (data["runs"][rec["full_run"] - 1].get("legs") or {}) for name in LEGS):
            raise Refused("the result at %s is not a complete record of %s; run the full sweep" % (path, short(sha)))
        if rec.get("invalid"):
            raise Refused("the result at %s is invalid (%s); run the full sweep" % (short(sha), rec["invalid"]))
        recorded = recorded_hash(data["runs"][-1])
        if recorded != policy_hash():
            raise Refused("the result at %s was recorded under another leg environment (hash %s, this runner's %s), so a "
                          "re-run here would mix two; run the full sweep" % (short(sha), str(recorded)[:12], policy_hash()[:12]))
        if not rec.get("finished"):
            raise Refused("the sweep at %s has not finished, so its first run's failures are not all recorded; wait for it or "
                          "run the full sweep" % short(sha))
        for name in only:
            old = rec["legs"][name]
            if not is_owed(name, old):
                raise Refused("%s is not owed at %s (%s); nothing to re-run" % (name, short(sha), old.get("why")))
            if not old.get("finished"):
                raise Refused("%s has no finished first run at %s to re-run; run the full sweep" % (name, short(sha)))
            if passed(name, old):
                raise Refused("%s passed at %s; there is no failure to re-run" % (name, short(sha)))
        workers = args.workers or (rec.get("runner") or {}).get("workers") or default_workers()
        # the served leg's re-run also runs the tests the newest pytest leg at this sha skipped for want of the deps
        base_legs = rec["legs"]
        for name in only:
            new = {k: rec["legs"][name][k] for k in PLAN_KEYS if k in rec["legs"][name]}
            if name == "pytest":
                new["cmd"] = pytest_cmd(python, workers)
            new["rc"] = None
            run["legs"][name] = new
    else:
        workers = args.workers or default_workers()
    run["runner"]["workers"] = workers
    # The legs run in private clones of the exact sha under the state dir (A1), one per CI job (round 2, decision 13):
    # the legs whose steps one job of ci.yml holds share one fresh checkout, in that job's step order, and each such group
    # starts from a checkout of its own (leg_groups), as CI's jobs each start from a checkout of their own. Each checkout
    # is verified against the sha's tree before its group's first leg (A2) and re-read after every leg (A4); each is
    # removed when its group ends, and TMPDIR, the running leg's TMPDIR and the checkout on every exit path (A5).
    sweep_stale_checkouts(sha)
    # leg_tmp: the TMPDIR of the leg (or setup) running now, made at its start and removed at its end (round 2, Class B)
    checkout = marker = tmpdir = hold = served_hold = leg_tmp = None
    served_python = getattr(args, "served_python", None) or python

    def scratch():
        """A leg's (or a setup's) own context: a fresh TMPDIR with its private HOME and state root (round 2, Class B)."""
        nonlocal leg_tmp
        leg_tmp = make_tmpdir()
        lctx = leg_scratch(ctx, leg_tmp)
        prepare_home(lctx)
        return lctx

    def scratch_end(lctx):
        """The names the leg left in its HOME (at most 20), and its TMPDIR removed, as the leg ends."""
        nonlocal leg_tmp
        left = home_left(lctx)[:20]
        shutil.rmtree(leg_tmp, ignore_errors=True)
        leg_tmp = None
        return left

    def run_setup(where, where_before, grec, known):
        """npm ci as the group's setup (leg_groups' setup_before), run as the deps leg runs, in the group's checkout and in
        a scratch of its own: its record goes in the group's (grec), and the faults the re-read after it finds, read as
        after the deps leg (an ignored file outside vscode-extension/node_modules counts), are returned."""
        setup = {"owed": True, "cmd": list(DEPS_CMD), "cwd": "vscode-extension", "rc": None}
        print("sweep %s: setup (npm ci) for %s ..." % (short(sha), group_label(grec)), flush=True)
        lctx = scratch()
        run_leg(where, "deps", setup, wraps, lctx, logdir)
        left = scratch_end(lctx)
        if left:
            setup["home_left"] = left
        grec["setup"] = setup
        return recheck_checkout(where, sha, entries, where_before, only_under=DEPS_PRODUCTS, known=known)

    try:
        checkout, marker, create_s = make_checkout(tree, sha)
        _plant_for_tests(checkout)
        t0 = time.monotonic()
        entries = tree_entries(checkout, sha)
        faults = verify_checkout(checkout, sha, entries)
        if faults:
            raise Refused("the checkout of %s is not the sha's tree (%s); it is removed, and nothing was run or recorded"
                          % (short(sha), describe_faults(faults)))
        above = ancestor_hits(checkout)
        if above:
            raise Refused("the checkout of %s has %s in an ancestor directory (%d: %s), which node, tsc or esbuild would read "
                          "from outside the sha; remove %s and sweep again" % (short(sha), " and ".join(sorted(set(
                              os.path.basename(a) for a in above))), len(above), ", ".join(above[:3]),
                              "it" if len(above) == 1 else "them"))
        before = git_state(checkout)
        verify_s = round(time.monotonic() - t0, 2)
        # ci.yml's served step, found by its name in whichever job holds it: the served leg's files, switches, pip lines
        # and Python version; a step the runner does not read in full is a refusal (read_served_step).
        served = read_served_step(checkout, sha)
        served_files, served_empty = expand(checkout, served["globs"])
        if not only:
            run["legs"] = plan_legs(checkout, python, workers, served=served)
            # Every head owes the webview legs (WEBVIEW_WHY) and the served leg (SERVED_WHY); the record says so, or
            # names the missing extension.
            typecheck, served_rec = run["legs"]["typecheck"], run["legs"][SERVED_LEG]
            run.update(owed={"webview": {"owed": typecheck["owed"], "why": typecheck["why"]},
                             SERVED_LEG: {"owed": served_rec["owed"], "why": served_rec["why"]}})
            need = (history or {}).get("need") or {}
            owed = [n for n in LEGS if is_owed(n, run["legs"][n])]
            unrun = sorted(set(need) - set(owed))
            if unrun:
                raise Refused("%s failed at %s and this run would not run %s (%s); fix it and sweep the new head"
                              % (", ".join(unrun), short(sha), "it" if len(unrun) == 1 else "them",
                                 "; ".join("%s: %s" % (n, run["legs"][n].get("why")) for n in unrun)))
            stray = sorted(set(flakes) - set(need))
            if stray:
                raise Refused("--flake names %s, which %s no failed run at %s to excuse" % (", ".join(stray),
                              "has" if len(stray) == 1 else "have", short(sha)))
            unnamed = [n for n in LEGS if n in need and n not in flakes]
            if unnamed:
                raise Refused("the run at %s failed %s; a later run counts over a failed leg only with --flake LEG=TEXT naming "
                              "each (the test, and where it is recorded as a known flake); for anything else, fix it and sweep "
                              "the new head (logs: %s)" % (short(sha), ", ".join("%s in run %d (%s)" % (n, need[n][0], _rc_text(n, need[n][1]))
                                                                                 for n in unnamed),
                                                           ", ".join(str(need[n][1].get("log")) for n in unnamed)))
        # Round 2, decision 13: the legs this run runs, grouped by the ci.yml job that holds each one's step, read from the
        # swept sha's ci.yml (leg_groups); a leg whose step is in no job is a refusal. The first group runs in the checkout
        # made above; each later one in a fresh checkout of its own, made when the group starts.
        package = os.path.exists(os.path.join(checkout, "vscode-extension", "package.json"))
        groups = leg_groups(checkout, sha, [n for n in LEGS if n in run["legs"] and is_owed(n, run["legs"][n])], npm=package)
        grecs = [{"job": g["job"], "legs": list(g["legs"]), "path": None, "create_s": None, "verify_s": None, "setup": None}
                 for g in groups]
        grecs[0].update(path=checkout, create_s=create_s, verify_s=verify_s)
        run["runner"]["checkout"] = {"form": "clone", "per": "ci.yml job", "files": len(entries), "groups": grecs}
        if not only:
            run["order"] = [n for g in groups for n in g["legs"]]
        os.makedirs(logdir, mode=0o700, exist_ok=True)
        tmpdir = make_tmpdir()
        run["runner"]["tmpdir"] = tmpdir
        pytest_python = python
        if "pytest" in run["legs"] and is_owed("pytest", run["legs"]["pytest"]):
            # The pytest leg runs in a venv at the sha's ci.yml install steps, the SDK at its pin, built or reused before
            # anything is recorded: a build that fails is a refusal (sdk_environment).
            sdk, hold = sdk_environment(checkout, sha, python, tmpdir)
            run["runner"].update(sdk=sdk, python_version=sdk["base_version"])
            pytest_python = sdk["python"]
            run["legs"]["pytest"]["cmd"] = pytest_cmd(pytest_python, workers)
        served_vpy = None
        if SERVED_LEG in run["legs"] and is_owed(SERVED_LEG, run["legs"][SERVED_LEG]):
            # The served leg runs in a venv built from --served-python and the served step's own pip lines, never in the
            # pytest leg's venv, where the SDK imports: built or reused before anything is recorded, and a build that
            # fails is a refusal (served_environment).
            served_rec, served_hold = served_environment(checkout, sha, served_python, tmpdir, served)
            run["runner"]["served"] = served_rec
            served_vpy = served_rec["python"]
            rec = run["legs"][SERVED_LEG]
            rec.update(cmd=served_cmd(served_vpy, served_files), globs=list(served["globs"]))
            rec.pop("empty_glob", None)
            if served_empty:
                rec["empty_glob"] = served_empty
        ctx = leg_context(tmpdir, python, pytest_python=pytest_python, served_env=served["env"], served_python=served_vpy)
        prepare_home(ctx)
        run["runner"]["leg_env"] = {"allow": list(LEG_ALLOW), "hash": leg_env_hash(ctx)}
        run["runner"]["tools"] = tool_versions(ctx)
        # npm's builtin config file, which nothing turns off: refused, before anything is recorded, when it sets any key but
        # prefix (round 2, extra6-2); its presence and sha256 are recorded either way
        run["runner"]["npm_builtin"] = npm_builtin(ctx)
        early = groups[0]["setup_before"] is not None and groups[0]["setup_before"] == groups[0]["legs"][0]
        if early:
            # The first group's job runs npm ci before its first leg (a --leg re-run of a leg its job runs after npm ci,
            # the deps leg not named): a fresh checkout has no node_modules, so the setup installs them from the sha's
            # lockfile first, as that job does; without them the served leg's tests cannot run. It runs before anything
            # is recorded, so a setup that fails, or changes the checkout, refuses the run.
            after = run_setup(checkout, before, grecs[0], ignored_now(checkout, entries))
            setup = grecs[0]["setup"]
            if not passed("deps", setup) or after:
                raise Refused("the setup of the checkout of %s (npm ci) %s, so the re-run would not run on the sha's tree with "
                              "its dependencies; nothing was recorded (log %s)" % (short(sha), _rc_text("deps", setup) if not
                              passed("deps", setup) else "changed it: " + describe_faults(after), setup.get("log")))
        data = data or {"schema": SCHEMA, "sha": sha, "runs": []}
        data.update(branch=branch, tree=tree)
        # Round 2, Class B: what each leg left in its private HOME, {leg: names}, recorded only.
        run["runner"]["home_left"] = home_left_by_leg = {}
        data["runs"].append(run)
        write_result(path, data)
        for gi, g in enumerate(groups):
            grec = grecs[gi]
            if gi:
                # Round 2, decision 13: a fresh checkout for this group, verified against the sha's tree as the first one
                # was. Something is already recorded, so one that cannot be made or is not the sha's tree (a leg that
                # rewrote an object of the sha in the batcher's repository, whose objects the clone reads) makes the run
                # invalid rather than refusing it.
                try:
                    checkout, marker, create_s = make_checkout(tree, sha)
                    t0 = time.monotonic()
                    faults = verify_checkout(checkout, sha, entries)
                    if faults:
                        raise Refused("it is not the sha's tree: %s" % describe_faults(faults))
                    above = ancestor_hits(checkout)
                    if above:
                        raise Refused("it has %s in an ancestor directory" % ", ".join(above[:3]))
                except Refused as e:
                    run["invalid"] = "the fresh checkout for %s cannot be used (%s); the legs after it did not run" % (
                        group_label(grec), e)
                    write_result(path, data)
                    break
                before = git_state(checkout)
                grec.update(path=checkout, create_s=create_s, verify_s=round(time.monotonic() - t0, 2))
            blocked_by_setup = None
            for name in g["legs"]:
                rec = run["legs"][name]
                if name == g["setup_before"] and not (gi == 0 and early):
                    # npm ci where this group's job runs it (leg_groups), after the run is recorded: a setup that fails
                    # blocks the group's legs after it, each red naming it; one that changes the checkout makes the run
                    # invalid, as the deps leg's re-read does.
                    after = run_setup(checkout, before, grec, ignored_now(checkout, entries))
                    setup = grec["setup"]
                    if after:
                        run["invalid"] = ("after the setup (npm ci) of %s the checkout is not the sha's tree: %s; the legs "
                                          "after it did not run" % (group_label(grec), describe_faults(after)))
                        write_result(path, data)
                        break
                    if not passed("deps", setup):
                        blocked_by_setup = ("its checkout's setup, npm ci as %s runs it, %s (log %s), so the leg did not run"
                                            % (group_label(grec), _rc_text("deps", setup), setup.get("log")))
                if name == SERVED_LEG:
                    # The tests outside the served globs that the pytest leg skipped for want of the deps join the served
                    # leg's command: this run's pytest leg, or for a --leg re-run the newest one recorded at this sha. A set
                    # that is not known blocks the leg, which is then red naming why (run_leg).
                    also, why = served_also(run["legs"]["pytest"] if "pytest" in run["legs"] else base_legs.get("pytest"))
                    rec.pop("blocked", None)
                    rec["cmd"] = served_cmd(served_vpy, served_files, also or ())
                    if why is None:
                        rec["also"] = {"tests": also, "count": len(also), "why": DEPS_SKIP_WHY}
                        print("sweep %s: served also runs %d test%s the pytest leg skipped for want of the deps"
                              % (short(sha), len(also), "" if len(also) == 1 else "s"), flush=True)
                    else:
                        rec["also"] = {"error": why}
                        rec["blocked"] = why
                if blocked_by_setup:
                    rec["blocked"] = blocked_by_setup
                # before deps, the ignored files the legs before it in its checkout left, which its re-read excuses as long
                # as it leaves them (none in a fresh checkout, where the deps leg is first)
                known = ignored_now(checkout, entries) if name == "deps" else None
                print("sweep %s: %s ..." % (short(sha), name), flush=True)
                # Round 2, Class B: each leg runs in a fresh TMPDIR of its own, with its private HOME and state root under
                # it (leg_scratch), removed when the leg ends, so nothing it leaves there reaches a later leg.
                lctx = scratch()
                run_leg(checkout, name, rec, wraps, lctx, logdir)
                if not passed(name, rec):
                    # Round 2, decision 14 (A6): a leg that did not pass is on disk as soon as run_leg returns, before
                    # deps_skipped, the re-read of the checkout and the venv's re-read below, so a stop during any of them
                    # keeps the failure and the next run needs --flake naming it; an invalid mark after the re-read
                    # rewrites the record. A pass is written only after its re-read, which could void it: read_history
                    # counts a stopped run's finished legs, so a pass written first and then stopped would stand unverified.
                    write_result(path, data)
                left = scratch_end(lctx)
                if left:
                    home_left_by_leg[name] = left
                if name == "pytest":
                    unselected = []
                    ids, why = deps_skipped(rec.get("log"), served_files, unselected)
                    rec["deps_skipped"] = ({"tests": ids, "count": len(ids), "rule": DEPS_SKIP.pattern, "unselected": unselected}
                                           if why is None else {"error": why})
                print("sweep %s: %s %s%s" % (short(sha), name, _rc_text(name, rec), (" (%s)" % rec["summary"]) if rec.get("summary") else ""), flush=True)
                changed = recheck_checkout(checkout, sha, entries, before, only_under=DEPS_PRODUCTS if name == "deps" else None,
                                           known=known)
                # A4 reads the pytest and served legs' environments too: a leg that changed its venv changed what it, or
                # another run's leg using the same venv, ran in, as a leg that changed the checkout changed the tree later
                # legs run on. The run ends here, and on its way out, after the reap, the runner removes the venv's marker
                # (VenvHold.retire), so the next run that uses it builds it again whatever the leg wrote into the marker.
                own = {"pytest": hold, SERVED_LEG: served_hold}.get(name)
                moved = own.changes() if own is not None else []
                if changed or moved:
                    # A4, the runner's producer of invalid: a leg changed the checkout, so later legs would not run on the
                    # sha's tree, or its own environment, so it may not have run in what its build installed.
                    parts = []
                    if changed:
                        parts.append("after the %s leg the checkout is not the sha's tree: %s" % (name, describe_faults(changed)))
                    if moved:
                        parts.append("after the %s leg its environment %s is not the tree its build wrote (%d path%s: %s%s); "
                                     "the next run that uses it builds it again" % (name, own.venv, len(moved), "" if len(moved) == 1
                                                                                     else "s", ", ".join(moved[:3]),
                                                                                     ", ..." if len(moved) > 3 else ""))
                    run["invalid"] = "; ".join(parts) + "; the legs after it did not run"
                    write_result(path, data)
                    break
                write_result(path, data)
            if run["invalid"]:
                break
            # the group's checkout goes when its legs end; the next group starts from a fresh one
            remove_checkout(checkout, marker)
            checkout = marker = None
        # whether no leg, and no setup (whose own record names what it left), left anything in its private HOME
        run["runner"]["home_empty"] = not home_left_by_leg and not any((gr["setup"] or {}).get("home_left") for gr in grecs)
    finally:
        # Round 2, correctness-3: a stop signal that arrives during this cleanup (the first one; the handler ignores the
        # rest) is kept, the step it cut short runs again from its start and the steps after it run, and the stop is raised
        # at the end, so every exit path removes TMPDIR, the running leg's TMPDIR and the checkout in use (_finish).
        stopped = []
        _finish(reap_descendants, stopped)
        # The shared locks on the legs' environments are held to here, after the reap, so no rebuild removes a venv while
        # anything this run started may still be running from it. A venv whose tree changed (seen after a leg, which ends
        # the run as invalid, or only now, when the run was stopped during a leg) is retired first, under the lock and after
        # the reap, so nothing this run started can write the marker again, and the next run that uses it builds it again.
        for h in (hold, served_hold):
            if h is None:
                continue
            try:
                _finish(lambda h=h: _retire_if_changed(h, sha), stopped)
            finally:
                _finish(h.release, stopped)
        for d in (leg_tmp, tmpdir):
            if d:
                _finish(lambda d=d: shutil.rmtree(d, ignore_errors=True), stopped)
        _finish(lambda: remove_checkout(checkout, marker), stopped)
        if stopped:
            raise stopped[0]
    run["finished"] = now()
    run["verdict"] = run_verdict(run)
    run["red"] = [n for n in red_legs(run) if run["kind"] == "full" or n in run["legs"]] if run["verdict"] == "red" else []
    write_result(path, data)
    a = assess(sha, subject="HEAD")
    print(("ok   " if a["case"] == "pass" else "FAIL ") + a["line"])
    return {"pass": EXIT_PASS, "red": EXIT_RED, "invalid": EXIT_INVALID}.get(a["case"], EXIT_RED)


def cmd_check(args):
    """What verify reads for the batch head, and plan and --repin for a member's head: the reader's case, the branch
    told apart from the sha (a result for the tree's branch at another sha reads stale, not missing), then the excuse
    rule against the sha's tree."""
    tree = os.path.realpath(args.tree or os.getcwd())
    sha = git(tree, "rev-parse", "--verify", (args.sha or "HEAD") + "^{commit}")
    subject = "HEAD" if not args.sha or args.sha == "HEAD" else sha[:10]
    branch = args.branch
    if branch is None and sha == git(tree, "rev-parse", "--verify", "HEAD^{commit}"):
        # verify names the batch branch and plan the member's head branch; for the tree's own HEAD that is its branch
        branch = git(tree, "symbolic-ref", "--short", "-q", "HEAD", check=False).stdout.strip() or None
    a = assess(sha, subject=subject, branch=branch, tree_hint=tree)
    line, ok = a["line"], a["case"] == "pass"
    if ok:
        fault = excuse_contradiction(tree, a["result"], sha, subject=subject)
        if fault:
            line, ok = fault, False
    print(("ok   " if ok else "FAIL ") + line)
    return EXIT_PASS if ok else EXIT_RED


def main(argv=None):
    doc = (__doc__ or "").strip().split("\n\n")
    ap = argparse.ArgumentParser(prog="scripts/sweep.py", description=doc[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(doc[1:]))
    sub = ap.add_subparsers(dest="subcommand", required=True, metavar="<subcommand>")
    p = sub.add_parser("run", help="sweep the tree's HEAD and record every leg's exit status",
                       description="Sweep the commit the tree's HEAD names: check it out into a private clone under the "
                                   "state dir and verify it against the sha's tree, build or reuse the pytest leg's venv at "
                                   "the install steps of the sha's ci.yml (the SDK at its pin) and the served leg's venv at "
                                   "the sha's ci.yml served step's pip line (no SDK), read the served leg's files and switches "
                                   "from that step, and run every owed leg (%s) as CI's jobs run them: the legs whose steps "
                                   "one ci.yml job holds in one fresh verified clone of their own, in that job's step order, "
                                   "each leg in a TMPDIR, HOME and state root of its own, npm ci where the job runs it, the "
                                   "pytest leg's job first: pytest over all of tests/ with no node_modules and no browser, as "
                                   "CI's Python cells run it, and served in one process, as CI's served step runs it, with "
                                   "the tests outside the served globs that the pytest leg skipped for want of the deps (%s); "
                                   "append the run to the sha's result after "
                                   "every leg, and record it invalid if a leg changed the checkout or its venv. The tree need "
                                   "not be clean; its uncommitted edits are not swept. Exit 0 pass, 1 red (a run that is "
                                   "itself invalid but leaves the sha unable to pass included), 2 refused to start, 3 "
                                   "invalid." % (", ".join(LEGS), MEASURED_TEXT))
    p.add_argument("--tree", metavar="DIR", help="the repository whose HEAD is swept (default: the one holding the current "
                                                 "directory); read for its HEAD sha and branch only")
    p.add_argument("--python", metavar="PATH", help="the interpreter the pytest leg's venv is built from (default: the one running "
                                                    "this script); the pytest leg runs in that venv, under <state "
                                                    "dir>/sweeps/sdk/<key>, which holds what the install steps of the sha's "
                                                    "ci.yml install (pytest and its plugins, cryptography, the Claude Agent SDK "
                                                    "at its pin); a build that fails refuses the run. Nothing need be "
                                                    "installed in it, and nothing should be: the legs outside the two venvs "
                                                    "(bats, manager, tools, ledger and the npm legs) have its directory first "
                                                    "on their PATH and run its python3, as CI's jobs other than the Python "
                                                    "cells run a python3 that holds none of the test dependencies")
    p.add_argument("--served-python", metavar="PATH",
                   help="the interpreter the served leg's venv is built from (default: --python); it must be the Python "
                        "version the sha's ci.yml sets up for its served step (3.12 today), or the run is refused naming "
                        "what to pass. The served leg runs in that venv, under <state dir>/sweeps/served/<key>, which "
                        "holds what the served step's pip line installs and nothing else, so not the Claude Agent SDK, as "
                        "CI's served step installs none; a build that fails refuses the run. Nothing need be installed "
                        "in it")
    p.add_argument("--workers", type=int, metavar="N", help="pytest -n for the pytest leg (default: the idle cores at launch, "
                                                            "clamped to %d..%d); the served leg runs one process, as CI's "
                                                            "served step does" % (WORKERS_MIN, WORKERS_MAX))
    p.add_argument("--wrap", action="append", metavar="LEG=PREFIX",
                   help="a command prefix for that leg's argv (shlex-split); * means every leg, and a leg's own prefix "
                        "replaces * for it; the recorded rc is the wrapper's. The prefix runs with this runner's "
                        "environment and the leg's allowlisted environment applies after it, so nothing it sets reaches "
                        "the leg")
    p.add_argument("--leg", action="append", metavar="NAME",
                   help="re-run only this leg at the same sha, after the result's newest run failed it on a known flake "
                        "(needs --flake; once per leg; the re-run is appended to the result's runs, which keep the failed "
                        "one); repeatable")
    p.add_argument("--flake", action="append", metavar="[LEG=]TEXT",
                   help="the known flake a failed leg's run was (the test, and where it is recorded as a known flake), "
                        "written into the new run: after a run at the same sha failed a leg, the next run that runs it "
                        "counts only with --flake LEG=TEXT naming it (once per leg); with --leg a bare TEXT names every "
                        "--leg leg; repeatable")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("check", help="read the result for a commit, as scripts/batch.py verify does",
                       description="Read the result recorded for a commit and name its case as scripts/batch.py verify "
                                   "reads it (and plan and assemble --repin for a member's head): pass, or missing, stale, "
                                   "unfinished, red, invalid, incomplete, unreadable; a pass that marks a leg not owed for "
                                   "having no vscode-extension/package.json while the sha's tree holds one reads invalid. "
                                   "Exit 0 on a pass, 1 otherwise.")
    p.add_argument("sha", nargs="?", metavar="SHA", help="the commit (default: HEAD of --tree)")
    p.add_argument("--tree", metavar="DIR", help="the repository to resolve SHA in (default: the current directory)")
    p.add_argument("--branch", metavar="BR", help="tell a missing result apart from a stale one recorded for this branch "
                                                  "(default, when SHA is the tree's HEAD: the branch the tree has checked out)")
    p.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Refused as e:
        print("sweep: %s" % e, file=sys.stderr)
        return EXIT_REFUSED
    except Stopped as e:
        print("sweep: stopped by signal %d; the legs were stopped and TMPDIR and the checkout removed" % e.signum, file=sys.stderr)
        return 128 + e.signum


if __name__ == "__main__":
    sys.exit(main())
