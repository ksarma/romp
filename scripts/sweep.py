#!/usr/bin/env python3
"""scripts/sweep.py: run the local test sweep at one commit and record every leg's exit status against
that commit's full sha. scripts/batch.py verify and land read the record: a batch lands only on a passing
sweep of its exact head (docs/batching.md).

  run    [--tree DIR] [--python PATH] [--workers N] [--wrap LEG=PREFIX]... [--leg NAME]...
         sweep the tree's HEAD; exit 0 pass, 1 red, 2 refused to start, 3 invalid
  check  [SHA|HEAD] [--tree DIR] [--branch BR]
         read the result for a commit, as batch.py does; exit 0 on a pass, 1 otherwise

The result is `<state dir>/sweeps/<full sha>.json`, the state dir resolved as bin/romp resolves it
(ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp); leg logs go under
`<state dir>/sweeps/logs/<full sha>/`. Nothing is written in the working tree, and a result names no
secret: the environment it records is variable NAMES only.

The legs, in order (LEGS): deps (`npm ci` when vscode-extension/node_modules is absent), pytest, bats,
manager and tools (node --test), ledger (scripts/upstream-ledger.py check), and the three webview legs
(typecheck, npm-test, build), owed when kernel/kernel.py, ui/ or vscode-extension/ changed since the
merge base with origin/main (CLAUDE.md's webview rule; with no origin/main they are owed). Every leg runs
even after an earlier one is red, so the result carries every leg's status. A result claims a sha only
when the tree was clean at the start and HEAD and the tree were unchanged at the end; otherwise the run
is refused (dirty at the start) or recorded invalid. The leg environment drops every ROMP_*, CLAUDE* and
GIT_* variable (a session's or a hook's, which CI does not have) and, for the test legs, every
credential-shaped name; TMPDIR is a fresh short directory under /tmp, removed at the end.

The runner calls no nice, ionice, systemd-run, flock or slot script itself: a machine that runs legs
under such wrappers passes them with --wrap. It imports nothing beyond the standard library.
"""
import argparse
import datetime as _dt
import fcntl
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

SCHEMA = 1
LEGS = ("deps", "pytest", "bats", "manager", "tools", "ledger", "typecheck", "npm-test", "build")
WEBVIEW_LEGS = ("typecheck", "npm-test", "build")
TEST_LEGS = ("pytest", "bats", "manager", "tools", "npm-test")
VERDICTS = ("pass", "red", "running", "invalid")
EXIT_PASS, EXIT_RED, EXIT_REFUSED, EXIT_INVALID = 0, 1, 2, 3

# The webview rule (CLAUDE.md, "Any kernel/kernel.py change runs the webview tests"): a head owes the three
# webview legs unless all of these are untouched.
WEBVIEW_FILES = ("kernel/kernel.py",)
WEBVIEW_DIRS = ("ui/", "vscode-extension/")

# CI's pytest flags (.github/workflows/ci.yml, the Run pytest step), plus -p no:anyio (PR 872 puts it on CI).
PYTEST_FLAGS = ("-q", "-p", "no:cacheprovider", "-p", "no:anyio", "--durations=10", "--timeout=600", "--timeout-method=thread")
PYTEST_MODULES = ("pytest", "xdist", "pytest_timeout")
# Test modules the pytest leg never collects, each with its reason (recorded in the result).
PYTEST_IGNORED = {
    "tests/test_cut_turn_tree_kill.py": ("it runs the real cut-turn reaper on a child of pytest, which inside a romp "
                                         "session can stop the session's own process tree; CI covers it once per batch"),
}
GLOBS = {
    "bats": ("tests/*.bats",),
    "manager": ("tests/manager-*.test.js",),
    "tools": ("tools/*.test.mjs", "vendor/track-changents/hooks/*.test.mjs"),
}
# The switches CI sets on the matching steps, so a skip that CI would count as a failure counts here too.
LEG_ENV = {
    "pytest": {"ROMP_SERVED_TESTS_REQUIRE": "1"},
    "bats": {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"},
}
DROP_ALWAYS = re.compile(r"^(ROMP_|CLAUDE|GIT_)")
DROP_CREDENTIAL = re.compile(r"key|token|secret", re.IGNORECASE)
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


def is_owed(leg):
    """A leg counts as not owed only when its record says so in as many words; anything else is owed."""
    return not (isinstance(leg, dict) and leg.get("owed") is False)


def passed(leg):
    rc = leg.get("rc") if isinstance(leg, dict) else None
    return type(rc) is int and rc == 0


def verdict_of(result):
    """The one verdict rule, for the writer and the reader alike: running until finished, invalid when the run
    says so, red when an owed leg of LEGS has an rc other than 0 or none, pass otherwise."""
    if not result.get("finished"):
        return "running"
    if result.get("invalid"):
        return "invalid"
    legs = result.get("legs") or {}
    if any(is_owed(legs.get(name)) and not passed(legs.get(name)) for name in LEGS):
        return "red"
    return "pass"


def red_legs(result):
    legs = result.get("legs") or {}
    return [name for name in LEGS if is_owed(legs.get(name)) and not passed(legs.get(name))]


def _rc_text(leg):
    rc = leg.get("rc") if isinstance(leg, dict) else None
    if rc is None:
        err = leg.get("error") if isinstance(leg, dict) else None
        return "no rc" + (": %s" % err if err else "")
    return "rc %s" % rc


# ── the reader (scripts/batch.py calls assess) ───────────────────────────────

def _load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    if not isinstance(data.get("legs", {}), dict) or not all(isinstance(v, dict) for v in data.get("legs", {}).values()):
        raise ValueError("its legs are not a mapping of leg records")
    return data


def newest_for_branch(branch, env=None):
    """(path, result) of the newest readable result recorded for `branch`, by its start stamp; (None, None)."""
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
        if data.get("branch") == branch and (best[1] is None or str(data.get("started")) > str(best[1].get("started"))):
            best = (os.path.join(d, name), data)
    return best


def assess(sha, subject="the batch head", branch=None, tree_hint=None, env=None):
    """Read the result for `sha` and name its case: {"case", "line", "path", "result"}. The case is pass, or one of
    missing, stale, unfinished, red, invalid, incomplete, unreadable; `line` is the text a caller prints after
    "ok   " or "FAIL ". Stale is decided on the full sha only; `branch` lets a missing result for sha be told apart
    from a stale one recorded for the same branch at another sha."""
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
                                     "at %s" % (branch, short(other.get("sha")), other.get("finished") or "never", subject,
                                                short(sha), subject))
        hint = " --tree %s" % tree_hint if tree_hint else ""
        return done("missing", "sweep missing: no result for %s %s at %s; run `scripts/sweep.py run%s`" % (subject, sha, path, hint))
    try:
        data = _load(path)
    except (OSError, ValueError) as e:
        return done("unreadable", "sweep unreadable: %s: %s; sweep again" % (path, e))
    if data.get("schema") != SCHEMA:
        return done("unreadable", "sweep unreadable: %s: schema %r, and this reader reads schema %d; sweep again with this "
                                  "checkout's scripts/sweep.py" % (path, data.get("schema"), SCHEMA), data)
    if data.get("sha") != sha:
        return done("stale", "sweep stale: %s records sha %s, not %s %s; sweep again at %s"
                    % (path, short(str(data.get("sha"))), subject, short(sha), subject), data)
    legs = data.get("legs") or {}
    absent = [name for name in LEGS if name not in legs]
    if absent:
        return done("incomplete", "sweep incomplete at %s: no %s leg in %s; sweep again with this checkout's scripts/sweep.py"
                    % (short(sha), ", ".join(absent), path), data)
    recomputed = verdict_of(data)
    if recomputed == "running":
        ran = [name for name in LEGS if legs[name].get("finished")]
        return done("unfinished", "sweep unfinished: the sweep at %s started %s and has not finished (running, or its runner "
                                  "died; done: %s); wait for it or sweep again" % (short(sha), data.get("started"), ", ".join(ran) or "none"), data)
    if recomputed == "invalid":
        return done("invalid", "sweep invalid at %s: %s" % (short(sha), data.get("invalid")), data)
    if data.get("verdict") != recomputed:
        return done("invalid", "sweep invalid at %s: the recorded verdict %s disagrees with its legs (%s)"
                    % (short(sha), data.get("verdict"), recomputed), data)
    if recomputed == "red":
        return done("red", "sweep red at %s: %s; logs under %s" % (
            short(sha), ", ".join("%s (%s)" % (n, _rc_text(legs[n])) for n in red_legs(data)),
            os.path.join(sweeps_dir(env), "logs", sha)), data)
    ran = ["%s %s" % (n, legs[n]["rc"]) for n in LEGS if is_owed(legs[n])]
    skipped = [n for n in LEGS if not is_owed(legs[n])]
    return done("pass", "sweep at %s: pass, finished %s (%s%s); %s" % (
        short(sha), data.get("finished"), ", ".join(ran), ("; not owed: " + ", ".join(skipped)) if skipped else "", path), data)


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


def leg_env(leg, tmpdir, base=None):
    """(the environment for `leg`, the names dropped, the values set). Names only are recorded, never values."""
    base = dict(os.environ if base is None else base)
    dropped = sorted(k for k in base if DROP_ALWAYS.match(k) or (leg in TEST_LEGS and DROP_CREDENTIAL.search(k)))
    env = {k: v for k, v in base.items() if k not in dropped}
    extra = dict(LEG_ENV.get(leg, {}))
    extra["TMPDIR"] = tmpdir
    env.update(extra)
    return env, dropped, extra


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
    return [python, "-m", "pytest", "tests", "-n", str(workers), *PYTEST_FLAGS, *("--ignore=%s" % p for p in sorted(PYTEST_IGNORED))]


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
                rec.update(cmd=["npm", "ci", "--no-audit", "--no-fund"], cwd="vscode-extension",
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
            npm = {"typecheck": ["npm", "run", "typecheck"], "npm-test": ["npm", "test"], "build": ["npm", "run", "build"]}[name]
            if webview["owed"]:
                rec.update(cmd=npm, cwd="vscode-extension", why=webview["why"])
            else:
                rec.update(owed=False, why=webview["why"])
        legs[name] = rec
    return legs


# What a leg's record holds from its plan (plan_legs); the rest is the attempt, which a --leg re-run replaces.
PLAN_KEYS = ("owed", "why", "cmd", "cwd", "ignored", "globs", "empty_glob")
ATTEMPT_KEYS = ("rc", "error", "started", "finished", "log", "summary", "wrap", "env_dropped", "env_set")


def summarize_log(name, path):
    """A display-only summary: pytest's last result line, bats' ok and not-ok counts, node's pass and fail counts."""
    try:
        with open(path, "rb") as f:
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    if name == "pytest":
        hits = re.findall(r"^=*\s*(\d+ (?:failed|passed|skipped|errors?|deselected|xfailed|xpassed)\b[^\n]* in [0-9.]+s\b[^\n]*?)\s*=*$",
                          data, re.M)
        return hits[-1].strip() if hits else None
    if name == "bats":
        ok = len(re.findall(r"^ok ", data, re.M))
        bad = len(re.findall(r"^not ok ", data, re.M))
        return "%d ok, %d not ok" % (ok, bad)
    counts = dict(re.findall(r"^# (pass|fail) (\d+)$", data, re.M))
    if counts:
        return "pass %s, fail %s" % (counts.get("pass", "?"), counts.get("fail", "?"))
    return None


def run_leg(tree, name, rec, wraps, tmpdir, logdir):
    """Run one owed leg and fill in its record. A glob that matched nothing, a cwd that does not exist or a
    command that cannot start leaves rc empty with the reason in `error`: the leg is red, never run bare."""
    env, dropped, extra = leg_env(name, tmpdir)
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
        argv = (wrap or []) + rec["cmd"]
        try:
            with open(log, "w") as out:
                out.write("# leg: %s\n# cwd: %s\n# argv: %s\n" % (name, cwd, " ".join(shlex.quote(a) for a in argv)))
                out.flush()
                p = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
            rec["rc"] = p.returncode
        except OSError as e:
            rec["error"] = "could not start: %s" % e
        rec["summary"] = summarize_log(name, log)
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
        return _run_locked(args, tree, sha, branch, python, version, wraps, only, path)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _run_locked(args, tree, sha, branch, python, version, wraps, only, path):
    logdir = os.path.join(sweeps_dir(), "logs", sha)
    if only:
        try:
            result = _load(path)
        except FileNotFoundError:
            raise Refused("no result at %s to re-run a leg in; run the full sweep" % short(sha))
        except (OSError, ValueError) as e:
            raise Refused("the result at %s is unreadable (%s); run the full sweep" % (short(sha), e))
        if result.get("sha") != sha or any(name not in (result.get("legs") or {}) for name in LEGS):
            raise Refused("the result at %s is not a complete record of %s; run the full sweep" % (path, short(sha)))
        if result.get("invalid"):
            raise Refused("the result at %s is invalid (%s); run the full sweep" % (short(sha), result["invalid"]))
        for name in only:
            if not is_owed(result["legs"][name]):
                raise Refused("%s is not owed at %s (%s); nothing to re-run" % (name, short(sha), result["legs"][name].get("why")))
        workers = args.workers or (result.get("runner") or {}).get("workers") or default_workers()
        for name in only:
            old = result["legs"][name]
            if old.get("started"):
                result.setdefault("history", []).append(dict({k: old.get(k) for k in ATTEMPT_KEYS if k in old}, leg=name))
            new = {k: old[k] for k in PLAN_KEYS if k in old}
            if name == "pytest":
                new["cmd"] = pytest_cmd(python, workers)
            new["rc"] = None
            result["legs"][name] = new
        runner = result.setdefault("runner", {})
        runner.update(python=python, python_version=version or runner.get("python_version"), workers=workers)
        result.update(finished=None, verdict="running", red=[], invalid=None)
    else:
        workers = args.workers or default_workers()
        webview = webview_state(tree)
        result = {
            "schema": SCHEMA, "sha": sha, "branch": branch, "tree": tree, "started": now(), "finished": None,
            "runner": {"script_blob": script_blob(), "python": python, "python_version": version, "workers": workers},
            "base": webview["base"], "owed": {"webview": webview}, "order": list(LEGS),
            "legs": plan_legs(tree, python, workers, webview), "history": [],
            "verdict": "running", "red": [], "invalid": None,
        }
    os.makedirs(logdir, mode=0o700, exist_ok=True)
    tmpdir = make_tmpdir()
    result["runner"]["tmpdir"] = tmpdir
    try:
        write_result(path, result)
        for name in LEGS:
            if only and name not in only:
                continue
            rec = result["legs"][name]
            if not is_owed(rec):
                continue
            print("sweep %s: %s ..." % (short(sha), name), flush=True)
            run_leg(tree, name, rec, wraps, tmpdir, logdir)
            print("sweep %s: %s %s%s" % (short(sha), name, _rc_text(rec), (" (%s)" % rec["summary"]) if rec.get("summary") else ""), flush=True)
            write_result(path, result)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    head = git(tree, "rev-parse", "HEAD")
    dirty = dirty_paths(tree)
    if head != sha:
        result["invalid"] = "HEAD moved to %s during the run (it started at %s)" % (short(head), short(sha))
    elif dirty:
        result["invalid"] = "the tree changed during the run: %s" % ", ".join(dirty[:10])
    result["finished"] = now()
    result["verdict"] = verdict_of(result)
    result["red"] = red_legs(result) if result["verdict"] == "red" else []
    write_result(path, result)
    a = assess(sha, subject="HEAD")
    print(("ok   " if a["case"] == "pass" else "FAIL ") + a["line"])
    return {"pass": EXIT_PASS, "red": EXIT_RED, "invalid": EXIT_INVALID}.get(result["verdict"], EXIT_RED)


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
                        "replaces * for it; the recorded rc is the wrapper's")
    p.add_argument("--leg", action="append", metavar="NAME",
                   help="re-run only this leg over the existing result at the same sha (the earlier attempt is kept in the "
                        "history); repeatable")
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
