#!/usr/bin/env python3
"""scripts/sweep.py: run the local test sweep at one commit and record every leg's exit status against
that commit's full sha. scripts/batch.py verify and land read the record: a batch lands only on a passing
sweep of its exact head (docs/batching.md).

  run    [--tree DIR] [--python PATH] [--workers N] [--wrap LEG=PREFIX]... [--leg NAME...] [--flake [LEG=]TEXT]...
         sweep the commit the tree's HEAD names, in a private checkout of it; exit 0 pass, 1 red, 2 refused
         to start, 3 invalid
  check  [SHA|HEAD] [--tree DIR] [--branch BR]
         read the result for a commit as batch.py verify does; exit 0 on a pass, 1 otherwise

The result is `<state dir>/sweeps/<full sha>.json`, the state dir resolved as bin/romp resolves it
(ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp); leg logs go under
`<state dir>/sweeps/logs/<full sha>/`. Nothing is written in the batcher's tree, and a result names no
secret: of the leg environment it records the names it dropped and the values it set itself, never an
inherited value, and a leg log's header shows each variable by its name only.

The legs run in a private checkout of the exact sha, never in the batcher's tree: a `git clone --shared
--no-checkout` of the batcher's repository under <state dir>/sweeps/trees, checked out at the sha with hooks
off, every runner git call made with GIT_* removed, git's global and system configuration off and
refs/replace ignored. A clone copies none of the batcher's repository config, attributes, excludes, hooks,
sparse patterns, index flags or replace refs, so the legs see the sha's tree plus the tool installs, and
nothing from the checkout's parents. Before any leg the runner verifies the checkout against `git ls-tree -r
<sha>` (every path, executable bit, symlink target and blob), and refuses (exit 2, nothing recorded) on a
difference or on node_modules, package.json, tsconfig.json or jsconfig.json in any ancestor directory, which
node, tsc and esbuild would read. After every leg it reads the checkout again with its own directory walk,
and records the run invalid, naming the paths and the leg, when a tracked path changed or is gone; when any
other file exists that no rule of a tracked .gitignore ignores (a .gitignore a leg wrote, the clone's
info/exclude or a commit made in the clone excuses nothing); after the deps leg, when an ignored file exists
outside vscode-extension/node_modules (bytecode, or a test module the tracked .gitignore covers, which pytest
would load); when the clone's .git was replaced or its HEAD, config or info/exclude changed; or when one of
those names is now in an ancestor directory. That is the runner's one producer of invalid, and the legs after
it do not run. The batcher's tree is read for its HEAD sha and branch only, so it need not
be clean: the runner prints how many uncommitted edits it holds, which are not swept, and nothing done there
during a run reaches a leg. Nor do its ignored files: a stale dist/ or out-tests/, bytecode, node_modules, or an
untracked test the tracked .gitignore covers. The checkout's path is longer than a batch worktree's; TMPDIR, whose
length the deepest session-host socket path depends on, is unchanged. TMPDIR and the checkout are removed on every exit path: SIGTERM and SIGHUP stop
each leg's process group, and on Linux the runner is a child subreaper that kills whatever a leg left
running, a descendant that left the group included; each checkout records its sha beside it, and every run
removes the checkouts of runs that are no longer running. A descendant reparented to the runner that exits
while its leg runs is reaped then, so no test finds a defunct process in its own process group.

The legs, in order (LEGS): deps (`npm ci` from the sha's lockfile, in every checkout, since a fresh one has
no node_modules; a --leg re-run runs it first as its setup), pytest, bats, manager and tools (node --test),
ledger (scripts/upstream-ledger.py check), and the three webview legs (typecheck, npm-test, build). Every head
owes every leg, a member's head included, whatever its diff: the webview legs read files outside kernel/kernel.py,
ui/ and vscode-extension/ (tests, other kernel modules, docs), so no set of changed paths shows they may be
skipped. deps and the webview legs are marked not owed only when the sha has no vscode-extension/package.json,
and the ledger only when it has no ledger script; a reader refuses any other not-owed mark. Every leg runs even
after an earlier one is red, so the result carries every leg's status.

The leg environment is an allowlist (LEG_ALLOW, leg_sets): USER and LOGNAME pass when set, and the runner
sets everything else. PATH is the pytest interpreter's directory and those of node, npm, bats, git and
gitleaks, then /usr/bin and /bin; HOME is a private empty directory and XDG_STATE_HOME a private state root
(session hosts off) under TMPDIR, a fresh short directory under /tmp removed at the end; npm_config_cache and
PLAYWRIGHT_BROWSERS_PATH point at the shared caches the batcher's environment names; SHELL=/bin/bash,
LANG=C.UTF-8 and CI=true, as CI's runner has them; npm's global config and git's system config, which live
outside HOME, are off (npm_config_globalconfig=/dev/null, GIT_CONFIG_NOSYSTEM=1); every ROMP_*_PORT the tree reads is a dead port (a box
floor CI does not need); and each leg gets the switches CI sets on the matching step (LEG_ENV), plus the box
rule's 8 GB heap cap for npm test (NODE_OPTIONS), which CI does not set. So no credential, session identity or
test-narrowing variable (PYTEST_ADDOPTS, PYTHONPATH, NODE_OPTIONS) of the batcher's shell reaches a leg, and
no dotfile of the batcher's HOME does (an .npmrc, a git config and its hooks, a shell rc, the live
deployment's SDK), nor the npmrc of a node installed under it. pytest also runs with `-c /dev/null --rootdir=. --confcutdir=.`, so no pytest.ini or
conftest.py above the tree configures it. --wrap prefixes run with the runner's environment, and the
allowlist applies after them (`env -i`), so nothing a wrap sets reaches the leg. What the allowlist does not
govern: files stay readable at their absolute paths (a credential file, an agent's socket), and every leg can
read /proc/<pid>/environ of the runner and of every other process of the batcher's user, since the legs run
as that user. The result records the allowlist's hash (runner.leg_env), and a reader refuses a result
recorded under another; it also records the versions of node, npm, bats, git and gitleaks the legs found,
and whether the private HOME was empty at the end.

The pane bench (tests/ui-bench.test.mjs), the Python versions other than --python's, and macOS run only in
the batch's CI.

The result is append-only (schema 2): `runs` keeps every run at the sha, oldest first, and a run is never
rewritten once it has finished. Every run records the private checkout it ran in (runner.checkout); a reader
reads a result holding a run without one as unreadable, and the runner moves such a file aside, as it moves a
schema-1 file: both came from a runner that swept the batcher's own tree. The verdict is read from the newest full run with any later --leg re-run's legs
laid over it, and the whole history is read too: a run that failed a leg counts as excused only when the next
run of that leg carries --flake naming it and its known-flake entry, once per leg, whether that run is a --leg
re-run or a full run (`--flake LEG=TEXT`). A leg that failed twice, or that a later run passed without --flake
naming it, leaves no run at that sha able to pass; the runner refuses such a run up front, and the reader reads
the result red, naming the failed run and its logs. An invalid run needs no flake, but the pass line names it.
A --leg re-run refuses unless the newest run finished, is valid, and failed that leg.

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
LEGS = ("deps", "pytest", "bats", "manager", "tools", "ledger", "typecheck", "npm-test", "build")
WEBVIEW_LEGS = ("typecheck", "npm-test", "build")
TEST_LEGS = ("pytest", "bats", "manager", "tools", "npm-test")
# The legs the runner owes at every head; the others it marks not owed only with a reason (`why`): deps and the
# webview legs (EXTENSION_LEGS) only when the sha has no vscode-extension/package.json (NO_PACKAGE_JSON), and the
# ledger only when it has no ledger script.
ALWAYS_OWED = ("pytest", "bats", "manager", "tools")
# The legs owed wherever the sha has vscode-extension/package.json. The webview legs are owed at every such head,
# a member's included, whatever its diff (round 1, decision 11): they read files outside kernel/kernel.py, ui/ and
# vscode-extension/ (a census of their reads found 82 such tracked files), so a rule over the changed paths passes
# heads that turn them red.
EXTENSION_LEGS = ("deps",) + WEBVIEW_LEGS
WEBVIEW_WHY = "owed at every head: the webview legs read files outside kernel/kernel.py, ui/ and vscode-extension/"
VERDICTS = ("pass", "red", "running", "invalid")
# The one reason the runner gives for deps and the webview legs not owed: the sha's tree has no extension. A result
# that marks one of them not owed for any other reason did not come from this runner (every checkout is fresh, so it
# never holds node_modules, and no diff excuses a webview leg), and batch.py and `check` accept this one only when the
# sha's tree really has no such file (excuse_contradiction).
NO_PACKAGE_JSON = "no vscode-extension/package.json"
EXIT_PASS, EXIT_RED, EXIT_REFUSED, EXIT_INVALID = 0, 1, 2, 3

# The pytest command the runner builds (pytest_cmd): `<python> -m pytest tests -n <workers>`, then these flags, then
# PYTEST_ISOLATION and one --ignore per PYTEST_IGNORED entry. Against CI's Run pytest step (.github/workflows/ci.yml,
# `python -m pytest -q -n <2 or 0> --durations=10 --timeout=600 --timeout-method=thread`, collecting from the root,
# where test modules live only under tests/) the differences are: -n at this machine's idle cores; -p no:cacheprovider,
# so nothing is written to a .pytest_cache in the checkout; -p no:anyio (PR 872 puts it on CI); PYTEST_ISOLATION;
# and the --ignore list. tests/test_sweep_runner.py (CiParity) holds the two sides to exactly these differences.
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-p", "no:anyio", "--durations=10", "--timeout=600", "--timeout-method=thread")
# No pytest.ini or conftest.py above the checkout configures the leg: an empty inifile, the rootdir pinned to the
# checkout (a bare `-c /dev/null` would move it to /dev), and conftest.py files read from the checkout down only.
PYTEST_ISOLATION = ("-c", os.devnull, "--rootdir=.", "--confcutdir=.")
PYTEST_MODULES = ("pytest", "xdist", "pytest_timeout")
# Test modules the pytest leg never collects, each with its reason (recorded in the result).
PYTEST_IGNORED = {
    "tests/test_cut_turn_tree_kill.py": ("it runs the real cut-turn reaper on a child of pytest, which inside a romp "
                                         "session can stop the session's own process tree; CI covers it once per batch"),
}
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
# The box floor, which CI does not need: every port variable the tree reads is set to a dead port, so leg code its own
# suite does not floor cannot reach a live manager, kernel, dashboard or postal bus on this machine (each falls back to
# the live deployment's port when unset). XDG_STATE_HOME, the state root, is private per run (leg_sets).
# tests/test_sweep_runner.py's census derives the port names from the tree: each is here or in PORT_DEFAULTS.
PORT_FLOOR = {"ROMP_MANAGER_PORT": "1", "ROMP_KERNEL_PORT": "1", "ROMP_SERVE_PORT": "1", "ROMP_POSTAL_PORT": "1"}
# Port variables the floor need not set, each with the floored variable it defaults to.
PORT_DEFAULTS = {"ROMP_REMOTE_KERNEL_PORT": "ROMP_KERNEL_PORT"}
# Per leg: the switches CI sets on the matching steps (the served-page step's two for pytest, the Run bats step's two
# for bats), so a skip that CI would count as a failure counts here too; and the box rule's heap cap for npm test, a
# difference from CI, which sets none.
LEG_ENV = {
    "pytest": {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"},
    "bats": {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"},
    "npm-test": {"NODE_OPTIONS": "--max-old-space-size=8192"},
}
# The allowlist applies after --wrap: argv is the wrap, then `env -i NAME=VALUE ...`, then the leg's command, so the
# wrap runs with the runner's environment and nothing it sets reaches the leg.
ENV_BIN = "/usr/bin/env"
# The tools whose versions a result records (found on the leg's PATH), with the argument that prints the version.
TOOL_VERSION_ARGS = (("node", "--version"), ("npm", "--version"), ("bats", "--version"), ("git", "--version"),
                     ("gitleaks", "version"))
# git's repository-location variables: the runner's own git calls act on --tree, never on an inherited
# GIT_DIR (a hook's environment carries one).
GIT_LOCATION = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                "GIT_COMMON_DIR", "GIT_NAMESPACE", "GIT_PREFIX", "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM")
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
    owed, another leg marked not owed with no reason, or deps or a webview leg (EXTENSION_LEGS) marked not owed for
    any reason but NO_PACKAGE_JSON (every checkout is fresh, so deps is owed wherever the sha has
    vscode-extension/package.json, and every head owes the webview legs whatever its diff)."""
    if not (isinstance(leg, dict) and leg.get("owed") is False):
        return None
    if name in ALWAYS_OWED:
        return "%s marked not owed" % name
    why = leg.get("why")
    if not (isinstance(why, str) and why.strip()):
        return "%s marked not owed with no reason" % name
    if name in EXTENSION_LEGS and why != NO_PACKAGE_JSON:
        return "%s marked not owed for a reason other than %r (%r)" % (name, NO_PACKAGE_JSON, why)
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
    """What the whole history at one sha says, read over every finished leg attempt of every run that is not invalid
    (an invalid run is not a test failure and needs no flake, round 1 decision 18; it is only named):
      never    the records no runner writes: a --leg re-run with no known flake named for a leg it ran, a flake
               named for a leg the run did not run or that had no failed run before it at this sha;
      dead     why no run at this sha can pass any more: a leg that failed in two runs (a known flake is excused once),
               or a failed run whose leg a later run passed without --flake naming it;
      need     {leg: (run number, record)} for each leg whose newest attempt failed: the next run that runs it counts
               only with --flake naming it and its known-flake entry;
      flaked   [(leg, failed run number, failed record, flake)] for each failure a later run's flake excused;
      invalid  [(run number, started, reason)] for each invalid run."""
    out = {"never": [], "dead": None, "need": {}, "flaked": [], "invalid": []}
    attempts = {n: [] for n in LEGS}
    for i, run in enumerate(runs):
        num = i + 1
        if run.get("invalid"):
            out["invalid"].append((num, run.get("started"), run.get("invalid")))
            continue
        legs = run.get("legs") or {}
        flakes = run.get("flakes") or {}
        if not isinstance(flakes, dict):
            out["never"].append("run %d's flakes are not a mapping of leg to known flake" % num)
            flakes = {}
        ran = [n for n in LEGS if n in legs and is_owed(n, legs[n]) and legs[n].get("finished")]
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


def invalid_notes(history):
    """The pass line's words for each invalid run in the history (it needs no flake, but it is named)."""
    return ["run %d (started %s) was invalid: %s" % (num, started, reason) for num, started, reason in history["invalid"]]


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
        # for one reason read as one clause naming the three), and each leg with no reason on its own.
        always = [n for n in faulty if n in ALWAYS_OWED]
        text = ["%s marked not owed" % ", ".join(always)] if always else []
        by_why = {}
        for n in faulty:
            why = legs[n].get("why")
            if n in ALWAYS_OWED:
                continue
            if isinstance(why, str) and why.strip():
                by_why.setdefault(why, []).append(n)
            else:
                text.append(excuse_fault(n, legs[n]))
        text += ["%s marked not owed for a reason other than %r (%r)" % (", ".join(names), NO_PACKAGE_JSON, why)
                 for why, names in by_why.items()]
        return done("invalid", "sweep invalid at %s: %s, which the runner never records (%s always run; deps and the webview "
                               "legs are owed at every head that has vscode-extension/package.json, whatever its diff, and "
                               "the ledger is marked not owed only with a reason); sweep again with this checkout's "
                               "scripts/sweep.py" % (short(sha), "; ".join(text), ", ".join(ALWAYS_OWED)), rec)
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
    if recomputed == "invalid":
        return done("invalid", "sweep invalid at %s: %s" % (short(sha), rec.get("invalid")), rec)
    for i, r in enumerate(runs):
        if r.get("finished") and r.get("verdict") != run_verdict(r):
            return done("invalid", "sweep invalid at %s: the recorded verdict %s disagrees with its legs (%s) in run %d"
                        % (short(sha), r.get("verdict"), run_verdict(r), i + 1), rec)
    logs = os.path.join(sweeps_dir(env), "logs", sha)
    if history["dead"]:
        return done("red", "sweep red at %s: %s; fix it and sweep the new head; logs under %s" % (short(sha), history["dead"], logs), rec)
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
    """The legs a result marks not owed for having no vscode-extension/package.json (the one reason the runner gives
    for deps and the webview legs, round 1's excuse rule) while the sha's tree does hold that file, as a line naming
    them; None when none is so marked or the tree really has no such file. Read with the runner's own git hygiene (no
    inherited GIT_*, no global or system config, refs/replace ignored). batch.py's verify, plan and --repin and this
    script's check apply it after a pass."""
    legs = (result or {}).get("legs") or {}
    excused = [n for n in LEGS if not is_owed(n, legs.get(n)) and (legs.get(n) or {}).get("why") == NO_PACKAGE_JSON]
    if not excused:
        return None
    p = subprocess.run(["git", "-C", tree, "cat-file", "-e", "%s:vscode-extension/package.json" % sha], env=_git_env(),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        return None
    return ("sweep invalid at %s: the result marks %s not owed for having %s, but %s's tree holds vscode-extension/package.json; "
            "sweep again with this checkout's scripts/sweep.py" % (short(sha), ", ".join(excused), NO_PACKAGE_JSON, subject))


# ── the runner ────────────────────────────────────────────────────────────────

# Every git call the runner makes (the sha read, the clone, the checkout, the verification) runs with every GIT_*
# variable of its environment removed and git's global and system configuration off, so no inherited GIT_DIR,
# GIT_CONFIG_*, GIT_TEMPLATE_DIR or config file changes what it reads; refs/replace is ignored; and the per-user
# attributes and excludes files git reads by default (~/.config/git/attributes and ignore) are pointed at an empty
# file, since a global `* text eol=crlf` there would change what a checkout writes. fsmonitor and the untracked cache
# are off.
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
    """How many entries `git status --porcelain=v1 --untracked-files=all` lists in the batcher's tree, as the batcher's
    own git sees it (their configuration and excludes), or None when git status fails. Only a notice reads it: the
    legs run in a private checkout of the sha, so these edits are not swept."""
    env = {k: v for k, v in os.environ.items() if k not in GIT_LOCATION}
    p = subprocess.run(["git", "-C", tree, "status", "--porcelain=v1", "-z", "--untracked-files=all"], env=env,
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
    so a later run can tell whether that sha's lock is held (sweep_stale_checkouts)."""
    parent = trees_dir()
    os.makedirs(parent, mode=0o700, exist_ok=True)
    common = git(tree, "rev-parse", "--git-common-dir")
    common = common if os.path.isabs(common) else os.path.abspath(os.path.join(tree, common))
    t0 = time.monotonic()
    for _ in range(100):
        name = "%s-%s" % (sha[:12], _random_tail())
        marker = os.path.join(parent, name + ".sha")
        try:
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
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
        remove_checkout(path, marker)
        raise Refused("could not check %s out into a private clone: %s" % (short(sha), (p.stderr or p.stdout).strip()))
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
# other ignored path it could leave (bytecode in a __pycache__, a module the tracked .gitignore covers) would be read
# by the pytest leg after it.
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


def recheck_checkout(path, sha, entries, before, only_under=None):
    """[(class, [paths])] where the checkout differs from the sha's tree after a leg, read without trusting any state a
    leg could have written: every tracked entry as _entry_faults reads it; every other file on disk, found by the
    runner's own walk (_disk_paths), that no rule of a tracked .gitignore ignores (untracked: a root conftest.py, which
    pytest loads, or a file hidden by a .gitignore a leg wrote, by the clone's info/exclude or by a commit in the
    clone); with `only_under`, an ignored file outside it too (after deps, bytecode or a module the tracked .gitignore
    covers, which pytest would still load); the clone's .git replaced or its HEAD, config or info/exclude changed since
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
        faults["ignored outside " + os.fsdecode(only_under).rstrip("/")] = sorted(n for n in ignored if not n.startswith(only_under))
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
    missing, mode, symlink-to-file). Whatever it plants, the verification that follows refuses."""
    spec = os.environ.get("SWEEP_TEST_PLANT")
    if not spec:
        return
    for op, rel in json.loads(spec):
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

class Stopped(BaseException):
    """SIGTERM or SIGHUP reached the runner: its legs are stopped and TMPDIR and the checkout removed on the way out."""

    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def _on_stop(signum, _frame):
    for s in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, signal.SIG_IGN)
    raise Stopped(signum)


# Whether install_stop_handlers made this process a child subreaper; wait_leg reads it.
_subreaper = False


def install_stop_handlers():
    """SIGTERM and SIGHUP raise Stopped, so every exit path runs the cleanup; and on Linux the runner becomes a child
    subreaper (PR_SET_CHILD_SUBREAPER), so a leg's descendant that left its process group (setsid: Playwright's
    browsers, the kernel's session scopes) is reparented to the runner instead of to init: the runner reaps it if it
    exits while the leg runs (wait_leg) and kills it if it is still running when the leg ends (reap_descendants)."""
    global _subreaper
    for s in (signal.SIGTERM, signal.SIGHUP):
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


def leg_context(tmpdir, python, env=None):
    """The per-run values the leg environment is built from: TMPDIR, the private HOME and state root under it (both
    removed with it), the shared npm and Playwright caches as the batcher's environment resolves them, and PATH."""
    env = os.environ if env is None else env
    return {"tmpdir": tmpdir, "home": os.path.join(tmpdir, "home"), "xdg": os.path.join(tmpdir, "xdg-state"),
            "npm_cache": npm_cache(env), "browsers": browsers_path(env), "path": build_path(python, env)}


def leg_sets(leg, ctx):
    """{name: value} the runner sets for `leg`: PATH, the private HOME and XDG_STATE_HOME, TMPDIR, the two shared caches
    (a private HOME has none), LEG_FIXED, TOOL_CONFIG_OFF, PORT_FLOOR and the leg's LEG_ENV."""
    sets = {"PATH": ctx["path"], "HOME": ctx["home"], "TMPDIR": ctx["tmpdir"], "XDG_STATE_HOME": ctx["xdg"],
            "npm_config_cache": ctx["npm_cache"], "PLAYWRIGHT_BROWSERS_PATH": ctx["browsers"]}
    sets.update(LEG_FIXED)
    sets.update(TOOL_CONFIG_OFF)
    sets.update(PORT_FLOOR)
    sets.update(LEG_ENV.get(leg, {}))
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


def _tokenized(value, ctx):
    """A set value with its per-run and per-machine parts named instead: PATH and the two caches whole, and every
    value under TMPDIR (TMPDIR, HOME, XDG_STATE_HOME) by its path below it."""
    for key, token in (("path", "<PATH>"), ("npm_cache", "<NPM_CACHE>"), ("browsers", "<BROWSERS>")):
        if value == ctx[key]:
            return token
    t = ctx["tmpdir"]
    if value == t or value.startswith(t + os.sep):
        return "<TMPDIR>" + value[len(t):]
    return value


def leg_env_hash(ctx):
    """sha256 over the allowed names and, per leg, the sorted NAME=VALUE pairs the runner sets, each value
    tokenized (_tokenized): it identifies the runner's allowlist and set values, which depend only on its code, and
    not on the machine, the batcher's environment or the run."""
    doc = {"allow": sorted(LEG_ALLOW),
           "set": {leg: sorted("%s=%s" % (k, _tokenized(v, ctx)) for k, v in leg_sets(leg, ctx).items()) for leg in LEGS}}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()


def policy_hash():
    """The leg environment hash this runner records, computed over placeholder values: what a reader compares a
    result's recorded hash with (a result made under another allowlist or other set values is not the same gate)."""
    t = os.path.join(os.sep + "nonexistent", TMPDIR_PREFIX + "0" * TMPDIR_TAIL)
    return leg_env_hash({"tmpdir": t, "home": os.path.join(t, "home"), "xdg": os.path.join(t, "xdg-state"),
                         "npm_cache": os.sep + "nonexistent-npm-cache", "browsers": os.sep + "nonexistent-browsers",
                         "path": os.sep + "nonexistent-path"})


def recorded_hash(result):
    """The leg environment hash a result records (runner.leg_env.hash), or None when it records none."""
    runner = result.get("runner")
    leg_env_rec = runner.get("leg_env") if isinstance(runner, dict) else None
    h = leg_env_rec.get("hash") if isinstance(leg_env_rec, dict) else None
    return h if isinstance(h, str) else None


def prepare_home(ctx):
    """The private HOME (empty) and the private state root, with session hosts off in its romp directory (the
    runner's own floor for leg code that starts a backend over the default state dir)."""
    os.mkdir(ctx["home"], 0o700)
    os.makedirs(os.path.join(ctx["xdg"], "romp"), mode=0o700)
    with open(os.path.join(ctx["xdg"], "romp", "session-hosts"), "w") as f:
        f.write("off\n")


def home_left(ctx):
    """The names a run left in the private HOME, sorted (empty: the HOME was empty at the end)."""
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


def expand(tree, patterns):
    """(sorted matches relative to the tree, the first pattern that matched nothing, or None)."""
    import glob
    files = []
    for pat in patterns:
        hits = sorted(os.path.relpath(p, tree) for p in glob.glob(os.path.join(tree, pat)))
        if not hits:
            return files, pat
        files += hits
    return files, None


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


def probe_python(python):
    """(version, [missing modules]) of the pytest leg's interpreter."""
    code = ("import importlib.util, sys; print(sys.version.split()[0]); "
            "print(' '.join(m for m in %r if importlib.util.find_spec(m) is None))" % (PYTEST_MODULES,))
    try:
        p = subprocess.run([python, "-c", code], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
    except OSError as e:
        raise Refused("the pytest interpreter %s cannot run: %s" % (python, e))
    if p.returncode != 0:
        raise Refused("the pytest interpreter %s failed its module probe: %s" % (python, (p.stderr or p.stdout).strip()[:300]))
    lines = p.stdout.splitlines()
    return (lines[0].strip() if lines else ""), (lines[1].split() if len(lines) > 1 else [])


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
    return [python, "-m", "pytest", "tests", "-n", str(workers), *PYTEST_FLAGS, *PYTEST_ISOLATION,
            *("--ignore=%s" % p for p in sorted(PYTEST_IGNORED))]


def plan_legs(tree, python, workers):
    """{leg: record} with each leg's owed decision, command and cwd, planned over the fresh checkout; nothing runs
    here. deps (npm ci from the sha's lockfile) is owed whenever the sha has vscode-extension/package.json, since a
    fresh checkout never holds node_modules, and so are the webview legs, whatever the head changed (WEBVIEW_WHY)."""
    legs = {}
    package = os.path.exists(os.path.join(tree, "vscode-extension", "package.json"))
    for name in LEGS:
        rec = {"owed": True, "rc": None}
        if name == "deps":
            if not package:
                rec.update(owed=False, why=NO_PACKAGE_JSON)
            else:
                rec.update(cmd=list(DEPS_CMD), cwd="vscode-extension", why="a fresh checkout has no vscode-extension/node_modules")
        elif name == "pytest":
            rec.update(cmd=pytest_cmd(python, workers), cwd=".", ignored=dict(PYTEST_IGNORED))
        elif name in GLOBS:
            files, empty = expand(tree, GLOBS[name])
            tool = ["bats", "--print-output-on-failure"] if name == "bats" else ["node", "--test"]
            rec.update(cmd=tool + files, cwd=".", globs=list(GLOBS[name]))
            if empty:
                rec.update(empty_glob=empty)
        elif name == "ledger":
            if os.path.exists(os.path.join(tree, "scripts", "upstream-ledger.py")):
                rec.update(cmd=[sys.executable, "scripts/upstream-ledger.py", "check"], cwd=".")
            else:
                rec.update(owed=False, why="no scripts/upstream-ledger.py in the tree")
        else:
            npm = list(NPM_CMDS[name])
            if not package:
                rec.update(owed=False, why=NO_PACKAGE_JSON)
            else:
                rec.update(cmd=npm, cwd="vscode-extension", why=WEBVIEW_WHY)
        legs[name] = rec
    return legs


# What a leg's record holds from its plan (plan_legs); the rest is the attempt, which a --leg re-run replaces.
PLAN_KEYS = ("owed", "why", "cmd", "cwd", "ignored", "globs", "empty_glob")
ATTEMPT_KEYS = ("rc", "error", "started", "finished", "log", "summary", "tests", "failed", "wrap", "env_dropped", "env_set",
                "left_running")

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
    """(passed, failed) for a test leg, counted from its log: pytest's last summary line, bats' `ok` and
    `not ok` lines, node's last `pass` and `fail` counts. (None, None) when the log holds no count, which the
    verdict reads as no test ran."""
    data = _read_log(path)
    if data is None:
        return None, None
    if name == "pytest":
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
    """A display-only summary: pytest's last result line, bats' ok and not-ok counts, node's pass and fail counts."""
    data = _read_log(path)
    if data is None:
        return None
    if name == "pytest":
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
    """Run one owed leg and fill in its record. A glob that matched nothing, a cwd that does not exist or a
    command that cannot start leaves rc empty with the reason in `error`: the leg is red, never run bare."""
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
    python = args.python or sys.executable
    version, missing = ("", [])
    if not only or "pytest" in only:
        version, missing = probe_python(python)
        if missing:
            raise Refused("the pytest interpreter %s lacks %s; install it there or pass --python" % (python, ", ".join(missing)))
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
        return _run_locked(args, tree, sha, branch, python, version, wraps, only, path, flakes)
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


def _run_locked(args, tree, sha, branch, python, version, wraps, only, path, flakes=None):
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
           "flakes": flakes, "runner": {"script_blob": script_blob(), "python": python, "python_version": version},
           "legs": {}, "verdict": "running", "red": [], "invalid": None}
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
        for name in only:
            new = {k: rec["legs"][name][k] for k in PLAN_KEYS if k in rec["legs"][name]}
            if name == "pytest":
                new["cmd"] = pytest_cmd(python, workers)
            new["rc"] = None
            run["legs"][name] = new
    else:
        workers = args.workers or default_workers()
    run["runner"]["workers"] = workers
    # The legs run in a private clone of the exact sha under the state dir (A1), verified against the sha's tree before
    # any leg (A2) and re-read after every leg (A4); it and TMPDIR are removed on every exit path (A5).
    sweep_stale_checkouts(sha)
    checkout = marker = tmpdir = None
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
        run["runner"]["checkout"] = {"form": "clone", "path": checkout, "create_s": create_s,
                                     "verify_s": round(time.monotonic() - t0, 2), "files": len(entries), "setup": None}
        if not only:
            run["legs"] = plan_legs(checkout, python, workers)
            # Every head owes the webview legs (WEBVIEW_WHY); the record says so, or names the missing extension.
            typecheck = run["legs"]["typecheck"]
            run.update(owed={"webview": {"owed": typecheck["owed"], "why": typecheck["why"]}}, order=list(LEGS))
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
        os.makedirs(logdir, mode=0o700, exist_ok=True)
        tmpdir = make_tmpdir()
        run["runner"]["tmpdir"] = tmpdir
        ctx = leg_context(tmpdir, python)
        prepare_home(ctx)
        run["runner"]["leg_env"] = {"allow": list(LEG_ALLOW), "hash": leg_env_hash(ctx)}
        run["runner"]["tools"] = tool_versions(ctx)
        if only and "deps" not in only and os.path.exists(os.path.join(checkout, "vscode-extension", "package.json")):
            # A fresh checkout has no node_modules, so a --leg re-run installs them from the sha's lockfile first, as CI
            # does; without them the tools leg and the served tests run narrowed and can pass.
            setup = {"owed": True, "cmd": list(DEPS_CMD), "cwd": "vscode-extension", "rc": None}
            print("sweep %s: setup (npm ci) ..." % short(sha), flush=True)
            run_leg(checkout, "deps", setup, wraps, ctx, logdir)
            run["runner"]["checkout"]["setup"] = setup
            after = recheck_checkout(checkout, sha, entries, before, only_under=DEPS_PRODUCTS)
            if not passed("deps", setup) or after:
                raise Refused("the setup of the checkout of %s (npm ci) %s, so the re-run would not run on the sha's tree with "
                              "its dependencies; nothing was recorded (log %s)" % (short(sha), _rc_text("deps", setup) if not
                              passed("deps", setup) else "changed it: " + describe_faults(after), setup.get("log")))
        data = data or {"schema": SCHEMA, "sha": sha, "runs": []}
        data.update(branch=branch, tree=tree)
        data["runs"].append(run)
        write_result(path, data)
        for name in LEGS:
            rec = run["legs"].get(name)
            if rec is None or not is_owed(name, rec):
                continue
            print("sweep %s: %s ..." % (short(sha), name), flush=True)
            run_leg(checkout, name, rec, wraps, ctx, logdir)
            print("sweep %s: %s %s%s" % (short(sha), name, _rc_text(name, rec), (" (%s)" % rec["summary"]) if rec.get("summary") else ""), flush=True)
            changed = recheck_checkout(checkout, sha, entries, before, only_under=DEPS_PRODUCTS if name == "deps" else None)
            if changed:
                # A4, the runner's one producer of invalid: a leg changed the checkout, so later legs would not run on
                # the sha's tree.
                run["invalid"] = ("after the %s leg the checkout is not the sha's tree: %s; the legs after it did not run"
                                  % (name, describe_faults(changed)))
                write_result(path, data)
                break
            write_result(path, data)
        left = home_left(ctx)
        run["runner"].update(home_empty=not left, home_left=left[:20])
    finally:
        reap_descendants()
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        remove_checkout(checkout, marker)
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
                                   "state dir and verify it against the sha's tree, run every owed leg there in order (%s), "
                                   "append the run to the sha's result after every leg, and record it invalid if a leg "
                                   "changed the checkout. The tree need not be clean; its uncommitted edits are not swept. "
                                   "Exit 0 pass, 1 red, 2 refused to start, 3 invalid." % ", ".join(LEGS))
    p.add_argument("--tree", metavar="DIR", help="the repository whose HEAD is swept (default: the one holding the current "
                                                 "directory); read for its HEAD sha and branch only")
    p.add_argument("--python", metavar="PATH", help="the interpreter for the pytest leg (default: the one running this script); "
                                                    "it must import %s" % ", ".join(PYTEST_MODULES))
    p.add_argument("--workers", type=int, metavar="N", help="pytest -n (default: the idle cores at launch, clamped to %d..%d)"
                                                            % (WORKERS_MIN, WORKERS_MAX))
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
