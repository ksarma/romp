#!/usr/bin/env python3
"""scripts/sweep.py: run the local test sweep at one commit and record every leg's exit status against
that commit's full sha. scripts/batch.py verify and land read the record: a batch lands only on a passing
sweep of its exact head (docs/batching.md).

  run    [--tree DIR] [--python PATH] [--workers N] [--wrap LEG=PREFIX]... [--leg NAME... --flake TEXT]
         sweep the tree's HEAD; exit 0 pass, 1 red, 2 refused to start, 3 invalid
  check  [SHA|HEAD] [--tree DIR] [--branch BR]
         read the result for a commit, as batch.py does; exit 0 on a pass, 1 otherwise

The result is `<state dir>/sweeps/<full sha>.json`, the state dir resolved as bin/romp resolves it
(ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp); leg logs go under
`<state dir>/sweeps/logs/<full sha>/`. Nothing is written in the working tree, and a result names no
secret: of the leg environment it records the names it dropped and the values it set itself, never an
inherited value, and a leg log's header shows each variable by its name only.

The legs, in order (LEGS): deps (`npm ci` when vscode-extension/node_modules is absent), pytest, bats,
manager and tools (node --test), ledger (scripts/upstream-ledger.py check), and the three webview legs
(typecheck, npm-test, build), owed when kernel/kernel.py, ui/ or vscode-extension/ changed since the
merge base with origin/main (CLAUDE.md's webview rule; with no origin/main they are owed). Every leg runs
even after an earlier one is red, so the result carries every leg's status. A result claims a sha only
when the tree was clean at the start and HEAD and the tree were unchanged at the end; otherwise the run
is refused (dirty at the start) or recorded invalid.

The leg environment is an allowlist (LEG_ALLOW, leg_sets): USER and LOGNAME pass when set, and the runner
sets everything else. PATH is the pytest interpreter's directory and those of node, npm, bats, git and
gitleaks, then /usr/bin and /bin; HOME is a private empty directory and XDG_STATE_HOME a private state root
(session hosts off) under TMPDIR, a fresh short directory under /tmp removed at the end; npm_config_cache and
PLAYWRIGHT_BROWSERS_PATH point at the shared caches the batcher's environment names; SHELL=/bin/bash,
LANG=C.UTF-8 and CI=true, as CI's runner has them; every ROMP_*_PORT the tree reads is a dead port (a box
floor CI does not need); and each leg gets the switches CI sets on the matching step (LEG_ENV), plus the box
rule's 8 GB heap cap for npm test (NODE_OPTIONS), which CI does not set. So no credential, session identity or
test-narrowing variable (PYTEST_ADDOPTS, PYTHONPATH, NODE_OPTIONS) of the batcher's shell reaches a leg, and
no dotfile of the batcher's HOME does (an .npmrc, a git config and its hooks, a shell rc, the live
deployment's SDK). pytest also runs with `-c /dev/null --rootdir=. --confcutdir=.`, so no pytest.ini or
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
rewritten once it has finished. The verdict is read from the newest full run with any later --leg re-run's legs
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
import string
import subprocess
import sys
import tempfile

SCHEMA = 2
LEGS = ("deps", "pytest", "bats", "manager", "tools", "ledger", "typecheck", "npm-test", "build")
WEBVIEW_LEGS = ("typecheck", "npm-test", "build")
TEST_LEGS = ("pytest", "bats", "manager", "tools", "npm-test")
# The legs the runner owes at every head; the others (deps, ledger, the webview legs) it marks not owed only
# with a reason (`why`).
ALWAYS_OWED = ("pytest", "bats", "manager", "tools")
VERDICTS = ("pass", "red", "running", "invalid")
EXIT_PASS, EXIT_RED, EXIT_REFUSED, EXIT_INVALID = 0, 1, 2, 3

# The webview rule (CLAUDE.md, "Any kernel/kernel.py change runs the webview tests"): a head owes the three
# webview legs unless all of these are untouched.
WEBVIEW_FILES = ("kernel/kernel.py",)
WEBVIEW_DIRS = ("ui/", "vscode-extension/")

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

def webview_owed(paths):
    """The changed paths that make a head owe the webview legs (empty: not owed)."""
    return [p for p in paths if p in WEBVIEW_FILES or p.startswith(WEBVIEW_DIRS)]


def excuse_fault(name, leg):
    """Why a leg's not-owed mark is one the runner never writes, or None: a leg of ALWAYS_OWED marked not
    owed, or another leg marked not owed with no reason."""
    if not (isinstance(leg, dict) and leg.get("owed") is False):
        return None
    if name in ALWAYS_OWED:
        return "%s marked not owed" % name
    why = leg.get("why")
    if not (isinstance(why, str) and why.strip()):
        return "%s marked not owed with no reason" % name
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
    failing: an rc of 0 alone is also what a wrapper that never ran its command returns."""
    rc = leg.get("rc") if isinstance(leg, dict) else None
    if not (type(rc) is int and rc == 0):
        return False
    if name in TEST_LEGS:
        tests, failed = _count(leg.get("tests")), _count(leg.get("failed"))
        return tests is not None and tests > 0 and not (failed or 0) > 0
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
                if nok and nflake is None and not out["dead"]:
                    out["dead"] = ("run %d failed %s (%s; log %s), and run %d passed it with no --flake naming it; a later run "
                                   "turns a failed leg green only with --flake naming the leg and its known-flake entry"
                                   % (num, n, _rc_text(n, rec), rec.get("log"), nnum))
                elif nok:
                    out["flaked"].append((n, num, rec, nflake))
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
        failed = _count(leg.get("failed"))
        if failed:
            return "rc 0 but its log shows %d failed" % failed
        return "rc 0 but no test ran"
    return "rc %s" % rc


# ── the reader (scripts/batch.py calls assess) ───────────────────────────────

SCHEMA_1_TEXT = "recorded by a runner that swept the batcher's own tree"


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
    faults = [f for f in (excuse_fault(name, legs[name]) for name in LEGS) if f]
    always = [name for name in ALWAYS_OWED if legs[name].get("owed") is False]
    if faults:
        text = [f for f in faults if not f.endswith(" marked not owed")]
        if always:
            text.insert(0, "%s marked not owed" % ", ".join(always))
        return done("invalid", "sweep invalid at %s: %s, which the runner never records (%s always run; the other legs are "
                               "marked not owed only with a reason); sweep again with this checkout's scripts/sweep.py"
                    % (short(sha), "; ".join(text), ", ".join(ALWAYS_OWED)), rec)
    history = read_history(runs)
    rec.update(flake_notes=flake_notes(history), invalid_notes=invalid_notes(history))
    if history["never"]:
        return done("invalid", "sweep invalid at %s: %s; a later run counts over a failed one only with --flake naming the "
                               "leg and its known-flake entry, once per leg; sweep again" % (short(sha), "; ".join(history["never"])), rec)
    stray = sorted(set(recorded_hash(r) for r in runs[rec["full_run"] - 1:]) - {policy_hash()}, key=str)
    if stray:
        recorded = stray[0]
        return done("invalid", "sweep invalid at %s: recorded under another leg environment (hash %s; this reader's is %s: "
                               "another scripts/sweep.py's allowlist or set values), so it is not this gate; sweep again with "
                               "this checkout's scripts/sweep.py" % (short(sha), str(recorded)[:12] if recorded else "none",
                                                                     policy_hash()[:12]), rec)
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


# ── the runner ────────────────────────────────────────────────────────────────

def _git_env():
    return {k: v for k, v in os.environ.items() if k not in GIT_LOCATION}


def git(tree, *args, check=True):
    p = subprocess.run(["git", "-C", tree, *args], env=_git_env(), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode != 0:
        raise Refused("git %s failed in %s: %s" % (" ".join(args), tree, (p.stderr or p.stdout).strip()))
    return p.stdout.strip() if check else p


def dirty_paths(tree):
    """What `git status --porcelain=v1 --untracked-files=all` lists: tracked changes and untracked, unignored
    files. Ignored build products (node_modules, out/, bytecode) do not count."""
    out = git(tree, "status", "--porcelain=v1", "--untracked-files=all", check=False)
    if out.returncode != 0:
        raise Refused("git status failed in %s: %s" % (tree, (out.stderr or out.stdout).strip()))
    return [line[3:] for line in out.stdout.splitlines() if line.strip()]


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
    (a private HOME has none), LEG_FIXED, PORT_FLOOR and the leg's LEG_ENV."""
    sets = {"PATH": ctx["path"], "HOME": ctx["home"], "TMPDIR": ctx["tmpdir"], "XDG_STATE_HOME": ctx["xdg"],
            "npm_config_cache": ctx["npm_cache"], "PLAYWRIGHT_BROWSERS_PATH": ctx["browsers"]}
    sets.update(LEG_FIXED)
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


def plan_legs(tree, python, workers, webview):
    """{leg: record} with each leg's owed decision, command and cwd; nothing runs here."""
    legs = {}
    node_modules = os.path.join(tree, "vscode-extension", "node_modules")
    package = os.path.join(tree, "vscode-extension", "package.json")
    for name in LEGS:
        rec = {"owed": True, "rc": None}
        if name == "deps":
            if not os.path.exists(package):
                rec.update(owed=False, why="no vscode-extension/package.json")
            elif os.path.lexists(node_modules):
                rec.update(owed=False, why="vscode-extension/node_modules present%s" % (" (a symlink)" if os.path.islink(node_modules) else ""))
            else:
                rec.update(cmd=list(DEPS_CMD), cwd="vscode-extension",
                           why="vscode-extension/node_modules absent")
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
            if webview["owed"]:
                rec.update(cmd=npm, cwd="vscode-extension", why=webview["why"])
            else:
                rec.update(owed=False, why=webview["why"])
        legs[name] = rec
    return legs


# What a leg's record holds from its plan (plan_legs); the rest is the attempt, which a --leg re-run replaces.
PLAN_KEYS = ("owed", "why", "cmd", "cwd", "ignored", "globs", "empty_glob")
ATTEMPT_KEYS = ("rc", "error", "started", "finished", "log", "summary", "tests", "failed", "wrap", "env_dropped", "env_set")

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
    elif name == "deps" and os.path.islink(os.path.join(tree, "vscode-extension", "node_modules")):
        rec["error"] = "vscode-extension/node_modules is a symlink, and npm ci through it would empty the deps it points at"
    elif not os.path.isdir(cwd):
        rec["error"] = "no directory %s in the tree" % rec.get("cwd")
    else:
        argv = leg_argv(wrap, env, rec["cmd"])
        try:
            with open(log, "w") as out:
                out.write("# leg: %s\n# cwd: %s\n# argv: %s\n" % (
                    name, rec.get("cwd") or ".", " ".join(shlex.quote(a) for a in leg_argv(wrap, env, rec["cmd"], shown=True))))
                out.flush()
                # The wrap (or env itself) runs with the runner's environment; the leg gets exactly `env`.
                p = subprocess.run(argv, cwd=cwd, env=dict(os.environ), stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
            rec["rc"] = p.returncode
        except OSError as e:
            rec["error"] = "could not start: %s" % e
        rec["summary"] = summarize_log(name, log)
        if name in TEST_LEGS:
            rec["tests"], rec["failed"] = count_tests(name, log)
    rec["finished"] = now()


def webview_state(tree):
    """{"owed", "why", "paths", "base"} from the merge base with origin/main; owed on the safe side without one."""
    if not git(tree, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/main", check=False).stdout.strip():
        return {"owed": True, "why": "no origin/main ref, so what changed is unknown: owed", "paths": [], "base": None}
    base = git(tree, "merge-base", "HEAD", "refs/remotes/origin/main", check=False)
    if base.returncode != 0 or not base.stdout.strip():
        return {"owed": True, "why": "no merge base with origin/main, so what changed is unknown: owed", "paths": [], "base": None}
    base = base.stdout.strip()
    changed = git(tree, "diff", "--no-renames", "--name-only", base, "HEAD").splitlines()
    hits = webview_owed(changed)
    if hits:
        shown = ", ".join(hits[:5]) + (" and %d more" % (len(hits) - 5) if len(hits) > 5 else "")
        return {"owed": True, "why": "changed since %s: %s" % (short(base), shown), "paths": hits, "base": base}
    return {"owed": False, "why": "kernel/kernel.py, ui/ and vscode-extension/ untouched since %s" % short(base),
            "paths": [], "base": base}


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
                      "as a known flake); anything else is a failure, and the full sweep runs again")
    if only and set(flakes) - set(only):
        raise Refused("--flake names %s, which this --leg re-run does not run" % ", ".join(sorted(set(flakes) - set(only))))
    dirty = dirty_paths(tree)
    if dirty:
        raise Refused("the tree %s is not clean, so a run would not be a run of %s: %s%s"
                      % (tree, short(sha), ", ".join(dirty[:5]), " and %d more" % (len(dirty) - 5) if len(dirty) > 5 else ""))
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
    them."""
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
        webview = webview_state(tree)
        run["legs"] = plan_legs(tree, python, workers, webview)
        run.update(base=webview["base"], owed={"webview": webview}, order=list(LEGS))
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
            raise Refused("the run at %s failed %s; a later run counts over a failed leg only with --flake LEG=TEXT naming each "
                          "(the test, and where it is recorded as a known flake); for anything else, fix it and sweep the new "
                          "head (logs: %s)" % (short(sha), ", ".join("%s in run %d (%s)" % (n, need[n][0], _rc_text(n, need[n][1]))
                                                                     for n in unnamed),
                                               ", ".join(str(need[n][1].get("log")) for n in unnamed)))
    run["runner"]["workers"] = workers
    data = data or {"schema": SCHEMA, "sha": sha, "runs": []}
    data.update(branch=branch, tree=tree)
    data["runs"].append(run)
    os.makedirs(logdir, mode=0o700, exist_ok=True)
    tmpdir = make_tmpdir()
    run["runner"]["tmpdir"] = tmpdir
    try:
        ctx = leg_context(tmpdir, python)
        prepare_home(ctx)
        run["runner"]["leg_env"] = {"allow": list(LEG_ALLOW), "hash": leg_env_hash(ctx)}
        run["runner"]["tools"] = tool_versions(ctx)
        write_result(path, data)
        for name in LEGS:
            rec = run["legs"].get(name)
            if rec is None or not is_owed(name, rec):
                continue
            print("sweep %s: %s ..." % (short(sha), name), flush=True)
            run_leg(tree, name, rec, wraps, ctx, logdir)
            print("sweep %s: %s %s%s" % (short(sha), name, _rc_text(name, rec), (" (%s)" % rec["summary"]) if rec.get("summary") else ""), flush=True)
            write_result(path, data)
        left = home_left(ctx)
        run["runner"].update(home_empty=not left, home_left=left[:20])
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    head = git(tree, "rev-parse", "HEAD")
    dirty = dirty_paths(tree)
    if head != sha:
        run["invalid"] = "HEAD moved to %s during the run (it started at %s)" % (short(head), short(sha))
    elif dirty:
        run["invalid"] = "the tree changed during the run: %s" % ", ".join(dirty[:10])
    run["finished"] = now()
    run["verdict"] = run_verdict(run)
    run["red"] = [n for n in red_legs(run) if run["kind"] == "full" or n in run["legs"]] if run["verdict"] == "red" else []
    write_result(path, data)
    a = assess(sha, subject="HEAD")
    print(("ok   " if a["case"] == "pass" else "FAIL ") + a["line"])
    return {"pass": EXIT_PASS, "red": EXIT_RED, "invalid": EXIT_INVALID}.get(a["case"], EXIT_RED)


def cmd_check(args):
    tree = os.path.realpath(args.tree or os.getcwd())
    sha = git(tree, "rev-parse", "--verify", (args.sha or "HEAD") + "^{commit}")
    a = assess(sha, subject="HEAD" if not args.sha or args.sha == "HEAD" else sha[:10], branch=args.branch, tree_hint=tree)
    print(("ok   " if a["case"] == "pass" else "FAIL ") + a["line"])
    return EXIT_PASS if a["case"] == "pass" else EXIT_RED


def main(argv=None):
    doc = (__doc__ or "").strip().split("\n\n")
    ap = argparse.ArgumentParser(prog="scripts/sweep.py", description=doc[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(doc[1:]))
    sub = ap.add_subparsers(dest="subcommand", required=True, metavar="<subcommand>")
    p = sub.add_parser("run", help="sweep the tree's HEAD and record every leg's exit status",
                       description="Sweep the tree's HEAD: refuse a dirty tree, run every owed leg in order (%s), write the "
                                   "result under the state dir after every leg, and mark it invalid if HEAD or the tree "
                                   "changed during the run. Exit 0 pass, 1 red, 2 refused to start, 3 invalid." % ", ".join(LEGS))
    p.add_argument("--tree", metavar="DIR", help="the worktree to sweep (default: the one holding the current directory)")
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
                       description="Read the result recorded for a commit and name its case: pass, or missing, stale, "
                                   "unfinished, red, invalid, incomplete, unreadable. Exit 0 on a pass, 1 otherwise.")
    p.add_argument("sha", nargs="?", metavar="SHA", help="the commit (default: HEAD of --tree)")
    p.add_argument("--tree", metavar="DIR", help="the repository to resolve SHA in (default: the current directory)")
    p.add_argument("--branch", metavar="BR", help="tell a missing result apart from a stale one recorded for this branch")
    p.set_defaults(func=cmd_check)
    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except Refused as e:
        print("sweep: %s" % e, file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
