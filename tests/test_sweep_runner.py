#!/usr/bin/env python3
"""scripts/sweep.py, the local sweep runner whose result file is the landing gate (2026-09-27).

scripts/batch.py verify and land read a result keyed by the batch head's full sha (tests/test_batch_tool.py
holds that side). This module holds the writer and the reader: the legs run in a private clone of the exact sha,
verified before any leg and re-read after every leg (a leg that changes it makes the run invalid), whatever the
batcher's tree holds or does meanwhile; every leg's rc is recorded, every leg runs after a red one, every head owes
every leg (the webview legs included, whatever the head changed); the leg environment is an allowlist (no credential, session, hook or narrowing
variable, no dotfile of the batcher's HOME); the result keeps every run at the sha (a later green counts over a
red one only with --flake naming the leg); and nothing is written in the batcher's tree.

Every test builds its own world: a bare origin, a clone holding a tiny tree, and fakes for npm, bats, node
and the pytest interpreter (one script, told apart by its name) that record their argv, cwd, environment
variable names and every file they can see in their checkout, and exit with the code the test sets. Each fake
carries its world's control and log paths in its own text, since no variable a test sets is sure to reach a
leg. The real suite never runs. Synthetic data only.
"""
import fcntl
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Hermetic state BEFORE the load below: the runner resolves its state dir from ROMP_STATE_DIR or XDG_STATE_HOME,
# and only pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "scripts" / "sweep.py"


def _load_sweep():
    spec = importlib.util.spec_from_file_location("sweep_runner", SWEEP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sweep = _load_sweep()

# The box rule's TMPDIR template (tests/test_tempdir_hygiene.py, SWEEP_TMPDIR_TEMPLATE): the runner's TMPDIR is no longer.
BOX_TMPDIR_TEMPLATE = "/tmp/sweep-XXXXXX"
SID = "11111111-2222-3333-4444-555555555555"
# The pytest LEG's name, held in a name: a list or tuple literal whose first element is the string "pytest" reads as a
# pytest command to tests/test_ci_sdk_pin.py's census of child launchers (PR 872), which would flag an expected value.
PYTEST_LEG = sweep.LEGS[1]
assert PYTEST_LEG == "pytest", sweep.LEGS

FAKE = r'''#!%(python)s
import glob, json, os, re, shutil, subprocess, sys, time
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
# The control and log paths are written into this file when the World makes it, never read from the environment:
# the runner's leg environment is an allowlist that drops every name a test would set.
CTL, LOG, SETUP = %(ctl)r, %(log)r, %(setup)r
ctl = json.load(open(CTL)) if os.path.exists(CTL) else {}
# The pytest leg's environment (sweep.py's sdk_environment): `python -m venv DIR` makes DIR a venv whose bin/python is a
# copy of this file; a copy running there is "in the venv", and its pip records each requirement in DIR's
# fake-installs.json, which its probe and its `-c "import X"` read. Every such call goes to SETUP, not to LOG, so the
# legs' record stays one entry per leg.
here = os.path.abspath(sys.argv[0])
venv_root = os.path.dirname(os.path.dirname(here))
in_venv = os.path.exists(os.path.join(venv_root, "pyvenv.cfg"))
installs_path = os.path.join(venv_root, "fake-installs.json")
installs = json.load(open(installs_path)) if in_venv and os.path.exists(installs_path) else {}
MODULE_DISTS = {"pytest": "pytest", "xdist": "pytest-xdist", "pytest_timeout": "pytest-timeout"}


def norm(dist):
    return re.sub(r"[-_.]+", "-", dist).lower()


def setup(kind, **extra):
    with open(SETUP, "a") as f:
        f.write(json.dumps(dict(extra, kind=kind, exe=here, argv=args, names=sorted(os.environ),
                                home=os.environ.get("HOME"), pythonpath=os.environ.get("PYTHONPATH"))) + "\n")


if name == "python" and args[:2] == ["-m", "venv"]:
    setup("venv", target=args[-1])
    if ctl.get("venv_rc"):
        sys.exit(ctl["venv_rc"])
    os.makedirs(os.path.join(args[-1], "bin"))
    shutil.copy(here, os.path.join(args[-1], "bin", "python"))
    os.chmod(os.path.join(args[-1], "bin", "python"), 0o755)
    with open(os.path.join(args[-1], "pyvenv.cfg"), "w") as f:
        f.write("home = %%s\n" %% os.path.dirname(here))
    sys.exit(0)
if name == "python" and args[:3] == ["-m", "pip", "install"]:
    setup("pip")
    if not in_venv:
        print("fake pip: refusing to install outside a venv")
        sys.exit(1)
    if any(bad in args for bad in ctl.get("pip_fail", [])):
        print("ERROR: fake pip failed on %%s" %% args[3:])
        sys.exit(1)
    for a in args[3:]:
        if not a.startswith("-"):
            dist, _eq, version = a.partition("==")
            installs[norm(dist)] = version or "9.9.9"
    with open(installs_path, "w") as f:
        json.dump(installs, f)
    sys.exit(0)
if name == "python" and args[:1] and args[0].endswith("get-pip.py"):
    setup("get-pip")
    installs["pip"] = "9.9.9"
    with open(installs_path, "w") as f:
        json.dump(installs, f)
    sys.exit(0)
if name == "python" and args[:1] == ["-c"]:
    code = args[1] if len(args) > 1 else ""
    if "sweep probe" in code:
        setup("probe")
        missing = set(ctl.get("missing", [])) if in_venv else set()
        if in_venv:
            missing |= {m for m, d in MODULE_DISTS.items() if d not in installs}
        dists = {d: (ctl.get("sdk_reports") or installs.get(norm(d))) if in_venv else None for d in args[2:]}
        version = ctl.get("probe_version", "3.99.0")
        print(json.dumps({"version": version, "full": version + " (fake)", "missing": sorted(missing),
                          "ensurepip": ctl.get("ensurepip", True), "dists": dists}))
        sys.exit(0)
    imported = re.fullmatch(r"import ([A-Za-z_][A-Za-z0-9_.]*)", code)
    if imported:
        setup("import", module=imported.group(1))
        if not any(norm(d).replace("-", "_") == imported.group(1).lower() for d in installs):
            print("ModuleNotFoundError: No module named %%r" %% imported.group(1))
            sys.exit(1)
        sys.exit(0)
    # any other -c: the two-line module probe of a runner before the venv (its version, then its missing modules)
    print(ctl.get("probe_version", "3.99.0"))
    print(" ".join(ctl.get("missing", [])))
    sys.exit(0)
if args in (["--version"], ["version"]):     # the runner's tool version record; not a leg
    print(name + " 0.0.0-fake")
    sys.exit(0)
if name == "python":
    leg = "pytest"
elif name == "npm":
    leg = {"ci": "deps", "test": "npm-test"}.get(args[0] if args else "") or {"typecheck": "typecheck", "build": "build"}.get(args[1] if len(args) > 1 else "", "npm?")
elif name == "node":
    leg = "manager" if any(a.startswith("tests/manager-") for a in args) else "tools"
elif name == "upstream-ledger.py":
    leg = "ledger"
else:
    leg = name
keep = ("TMPDIR", "HOME", "PATH", "SHELL", "LANG", "CI", "USER", "LOGNAME", "XDG_STATE_HOME", "npm_config_cache",
        "PLAYWRIGHT_BROWSERS_PATH", "NODE_OPTIONS", "SWEEP_WRAPPED", "ROMP_SERVED_TESTS_REQUIRE", "ROMP_SERVED_TESTS_ENGINES",
        "ROMP_GITLEAKS_REQUIRE", "BATS_TEST_TIMEOUT", "ROMP_MANAGER_PORT", "ROMP_KERNEL_PORT", "ROMP_SERVE_PORT",
        "ROMP_POSTAL_PORT", "npm_config_globalconfig", "GIT_CONFIG_NOSYSTEM", "ROMP_SDK_REQUIRE")
marker = ctl.get("marker")
home = os.path.expanduser("~")
# every file the runner put in the leg's private state root (names and contents), read without naming any
state_root = os.path.join(os.environ.get("XDG_STATE_HOME", "/nonexistent"), "romp")
state = ({n: open(os.path.join(state_root, n)).read() for n in sorted(os.listdir(state_root))
          if os.path.isfile(os.path.join(state_root, n))} if os.path.isdir(state_root) else None)


def checkout_root(d):
    while not os.path.exists(os.path.join(d, ".git")):
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)
    return d


def tree_of(root):
    """Every file and symlink the leg can see in its checkout ({path: [kind, digest or target, executable]})."""
    import hashlib
    out = {}
    for d, dirs, files in os.walk(root):
        rel = os.path.relpath(d, root)
        dirs[:] = [x for x in dirs if not (rel == "." and x == ".git") and x != "node_modules"]
        files = [x for x in files if not (rel == "." and x == ".git")]        # a worktree's .git is a file
        for x in [x for x in dirs if os.path.islink(os.path.join(d, x))] + files:
            full = os.path.join(d, x)
            key = os.path.normpath(os.path.join(rel, x))
            if os.path.islink(full):
                out[key] = ["link", os.readlink(full)]
            else:
                with open(full, "rb") as fh:
                    out[key] = ["file", hashlib.sha256(fh.read()).hexdigest(), bool(os.stat(full).st_mode & 0o100)]
    return out


root = checkout_root(os.getcwd())
with open(LOG, "a") as f:
    f.write(json.dumps({"leg": leg, "argv": args, "cwd": os.getcwd(), "names": sorted(os.environ), "root": root,
                        "tree": tree_of(root) if root else None,
                        "values": {k: os.environ[k] for k in keep if k in os.environ},
                        # the names whose value carries the test's marker, and what the batcher's HOME would hand a leg
                        "marked": sorted(k for k, v in os.environ.items() if marker and marker in v),
                        "home_files": sorted(n for n in (".npmrc", ".gitconfig", ".zshenv") if os.path.exists(os.path.join(home, n))),
                        "sdk": glob.glob(os.path.join(home, ".local", "state", "romp", "sdkvenv", "lib", "*", "site-packages")),
                        # the interpreter this leg ran as, and what the venv it runs in holds (None outside one)
                        "exe": here, "venv_installs": installs if in_venv else None,
                        "tmp": sorted(os.listdir(os.environ["TMPDIR"])) if os.path.isdir(os.environ.get("TMPDIR", "")) else None,
                        "state": state}) + "\n")
act = ctl.get("action", {}).get(leg)
if act == "commit":
    subprocess.run(["git", "-C", ctl["tree"], "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-q", "--allow-empty", "-m", "moved during the sweep"], check=True,
                   env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
elif act == "copy-result":
    shutil.copy(ctl["result"], ctl["copy_to"])
elif act == "leak":                              # an untracked, unignored file left in the leg's own checkout
    with open(os.path.join(root, "leaked.txt"), "w") as f:
        f.write("a test that wrote into the tree\n")
elif act == "edit":                              # a tracked file changed in the leg's own checkout
    with open(os.path.join(root, "README.md"), "a") as f:
        f.write("edited by a leg\n")
elif act == "delete":                            # a tracked file removed from the leg's own checkout
    os.remove(os.path.join(root, "kernel", "other.py"))
elif act == "ignored":                           # an ignored build product left in the checkout
    os.makedirs(os.path.join(root, "vscode-extension", "node_modules"), exist_ok=True)
    with open(os.path.join(root, "vscode-extension", "node_modules", "left.txt"), "w") as f:
        f.write("a build product\n")
elif act == "tree-edit":                         # a tracked file changed in the BATCHER's tree, not the checkout
    with open(os.path.join(ctl["tree"], "README.md"), "w") as f:
        f.write("changed in the batcher's tree during the sweep\n")
elif act == "tree-restore":
    subprocess.run(["git", "-C", ctl["tree"], "checkout", "-q", "--", "README.md"], check=True,
                   env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
elif act == "spawn":                             # two writers into TMPDIR, one in the leg's group, one under setsid
    writer = ("import os, signal, sys, time\n"
              "tmp, mark, tag = sys.argv[1:4]\n"
              "def term(*_):\n"
              "    open(mark + '.term', 'w').write(str(os.getpid()))\n"
              "    os._exit(0)\n"
              "signal.signal(signal.SIGTERM, term if tag == 'group' else signal.SIG_IGN)\n"
              "open(mark, 'w').write(str(os.getpid()))\n"
              "while True:\n"
              "    try:\n"
              "        os.makedirs(os.path.join(tmp, 'writer-' + tag), exist_ok=True)\n"
              "        open(os.path.join(tmp, 'writer-' + tag, 'x'), 'a').write('x')\n"
              "    except OSError:\n"
              "        pass\n"
              "    time.sleep(0.05)\n")
    tmp = os.environ["TMPDIR"]
    subprocess.Popen([sys.executable, "-c", writer, tmp, os.path.join(ctl["marks"], "group.pid"), "group"])
    subprocess.Popen([sys.executable, "-c", writer, tmp, os.path.join(ctl["marks"], "setsid.pid"), "setsid"], start_new_session=True)
    open(os.path.join(ctl["marks"], "ready"), "w").write(str(os.getpid()))
    time.sleep(120)
elif act == "home":
    with open(os.path.join(home, ".leftover"), "w") as f:
        f.write("a test that wrote into HOME\n")
elif act in ("orphan", "orphans"):
    # Grandchildren the runner adopts: each child of the leg forks one and exits, so the grandchild is reparented to the
    # runner (a child subreaper), reports its new parent and exits. "orphan": one grandchild, which exits while the leg
    # runs; the leg then reads its state and lists the defunct processes in its own process group, as the watchdog
    # tests in tests/romp-node-launch.bats do. "orphans": twenty, the even ones exiting while the leg runs (the leg
    # reads their state) and the odd ones at the leg's own exit (each waits on a pipe whose one writer is the leg).
    def proc_stat(pid):
        try:
            with open("/proc/%%d/stat" %% pid) as fh:
                rest = fh.read().rsplit(")", 1)[1].split()
            return rest[0], int(rest[1]), int(rest[2])        # state, parent, process group
        except (OSError, IndexError, ValueError):
            return None
    hold_r, hold_w = os.pipe()
    rep_r, rep_w = os.pipe()
    count = 1 if act == "orphan" else 20
    for i in range(count):
        child = os.fork()
        if child == 0:
            os.close(hold_w)
            os.close(rep_r)
            parent = os.getpid()
            if os.fork() == 0:
                end = time.monotonic() + 10
                while os.getppid() == parent and time.monotonic() < end:
                    time.sleep(0.005)
                os.write(rep_w, ("%%d %%d %%d\n" %% (i, os.getpid(), os.getppid())).encode())
                os.close(rep_w)
                if i %% 2:
                    os.read(hold_r, 1)
                os._exit(0)
            os._exit(0)
        os.waitpid(child, 0)
    os.close(hold_r)
    os.close(rep_w)
    reports = b""
    while True:
        chunk = os.read(rep_r, 4096)
        if not chunk:
            break
        reports += chunk
    adopted = sorted([int(x) for x in line.split()] for line in reports.decode().splitlines())
    end = time.monotonic() + 5
    early = [pid for i, pid, _parent in adopted if i %% 2 == 0]
    while any(proc_stat(pid) for pid in early) and time.monotonic() < end:
        time.sleep(0.01)
    seen = {"adopted": adopted, "runner": os.getppid(), "early": {str(pid): (proc_stat(pid) or [None])[0] for pid in early}}
    if act == "orphan":
        me, defunct = os.getpgrp(), []
        for n in os.listdir("/proc"):
            st = proc_stat(int(n)) if n.isdigit() else None
            if st and st[0] == "Z" and st[2] == me:
                defunct.append(int(n))
        seen["defunct_in_group"] = defunct
    with open(os.path.join(ctl["marks"], act + ".json"), "w") as f:
        json.dump(seen, f)
elif act == "daemon":                            # a daemon under setsid, still running when the leg exits
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(%%d)" %% ctl["daemon_seconds"]], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
elif act == "idle":
    # One grandchild the runner adopts stays running while the leg sleeps two seconds; the leg reads the runner's CPU
    # time (utime + stime in /proc/<runner>/stat) before and after. A runner that blocks until a child exits uses
    # almost none; one that polls for exited children spins.
    hold_r, hold_w = os.pipe()
    rep_r, rep_w = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(hold_w)
        os.close(rep_r)
        parent = os.getpid()
        if os.fork() == 0:
            end = time.monotonic() + 10
            while os.getppid() == parent and time.monotonic() < end:
                time.sleep(0.005)
            os.write(rep_w, str(os.getppid()).encode())
            os.close(rep_w)
            os.read(hold_r, 1)                   # until the leg, the one writer, exits
            os._exit(0)
        os._exit(0)
    os.waitpid(child, 0)
    os.close(hold_r)
    os.close(rep_w)
    adopted_parent = int(os.read(rep_r, 64) or 0)
    runner = os.getppid()

    def cpu():
        with open("/proc/%%d/stat" %% runner) as fh:
            rest = fh.read().rsplit(")", 1)[1].split()
        return (int(rest[11]) + int(rest[12])) / os.sysconf("SC_CLK_TCK")
    before = cpu()
    time.sleep(2)
    seen = {"runner": runner, "adopted_parent": adopted_parent, "cpu": cpu() - before}
    with open(os.path.join(ctl["marks"], act + ".json"), "w") as f:
        json.dump(seen, f)
# What each test leg's real tool prints at the end of a run (pytest -q's summary, bats' TAP, node's TAP summary):
# the runner counts the tests a leg ran from its log, and a test leg with rc 0 and no test counted is red.
out = {"pytest": "3 passed in 0.01s\n", "bats": "1..1\nok 1 a\n", "manager": "# pass 1\n# fail 0\n",
       "tools": "# pass 2\n# fail 0\n", "npm-test": "# pass 4\n# fail 0\n"}
sys.stdout.write(ctl.get("out", {}).get(leg, out.get(leg, "")))
if ctl.get("signal", {}).get(leg):                 # the leg dies by this signal instead of exiting
    sys.stdout.flush()
    os.kill(os.getpid(), ctl["signal"][leg])
sys.exit(ctl.get("rc", {}).get(leg, 0))
'''

# A --wrap prefix for the tests: records its tag, the leg it wraps (told apart as FAKE tells its legs apart) and its own
# environment's names, then runs the rest of its argv (`env -i ...` and the leg's command).
WRAPPER = r'''#!%(python)s
import json, os, re, sys
LOG = %(log)r
tag, rest = sys.argv[1], sys.argv[2:]
cmd = list(rest)
if cmd[:2] == ["/usr/bin/env", "-i"]:
    cmd = cmd[2:]
    while cmd and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", cmd[0]):
        cmd = cmd[1:]
name, args = (os.path.basename(cmd[0]), cmd[1:]) if cmd else ("", [])
if "scripts/upstream-ledger.py" in args:
    leg = "ledger"
elif name.startswith("python"):
    leg = "pytest"
elif name == "npm":
    leg = {"ci": "deps", "test": "npm-test", "run": {"typecheck": "typecheck", "build": "build"}.get(args[1] if len(args) > 1 else "")}.get(args[0] if args else "")
elif name == "node":
    leg = "manager" if any(a.startswith("tests/manager-") for a in args) else "tools"
else:
    leg = name
with open(LOG, "a") as f:
    f.write(json.dumps({"tag": tag, "leg": leg, "names": sorted(os.environ),
                        "values": {k: os.environ[k] for k in ("XDG_RUNTIME_DIR", "HOME") if k in os.environ}}) + "\n")
os.execvp(rest[0], rest)
'''

# The seed's ci.yml: a python job whose three install steps the runner reads to build the pytest leg's environment
# (sweep.py's INSTALL_STEPS), the SDK's pin read from kernel/session_host.py as the real workflow reads it. Synthetic;
# CiParity holds the runner to the real workflow.
SEED_PIN = "1.2.3"
SEED_SDK_STEP = """      - name: Install the Claude Agent SDK
        shell: bash
        run: |
          set -euo pipefail
          pin="$(sed -n 's/^SDK_TESTED_VERSION = "\\([^"]*\\)".*$/\\1/p' kernel/session_host.py)"
          [[ "$pin" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+$ ]] || {
            echo "kernel/session_host.py: expected exactly one line SDK_TESTED_VERSION = \\"<x.y.z>\\", read: '$pin'" >&2
            exit 1
          }
          python -m pip install "claude-agent-sdk==$pin"
          python -c "import claude_agent_sdk"
"""
SEED_CI = """name: CI
on:
  push:
    branches: ['batch/**']
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install pytest
        run: python -m pip install --upgrade pip pytest pytest-timeout pytest-xdist
      - name: Install cryptography
        run: python -m pip install cryptography
""" + SEED_SDK_STEP + """      - name: Run pytest
        run: python -m pytest -q
"""
SEED_HOST = 'SDK_TESTED_VERSION = "%s"\n' % SEED_PIN

SEED = {
    ".gitignore": "vscode-extension/node_modules\n",
    "README.md": "# notes-api\n",
    "kernel/kernel.py": "VERSION = 1\n",
    "kernel/other.py": "OTHER = 1\n",
    "ui/x.js": "export const x = 1;\n",
    "vscode-extension/package.json": "{\"name\": \"notes-api-ext\"}\n",
    "vscode-extension/src/a.ts": "export const a = 1;\n",
    "tests/a.bats": "@test 'a' { true; }\n",
    "tests/manager-a.test.js": "// manager\n",
    "tools/a.test.mjs": "// tools\n",
    "vendor/track-changents/hooks/a.test.mjs": "// hooks\n",
}


class World:
    def __init__(self, seed=None):
        self.tmp = tempfile.mkdtemp(prefix="sweeprun-")
        self.bare = os.path.join(self.tmp, "origin.git")
        self.tree = os.path.join(self.tmp, "tree")
        self.bin = os.path.join(self.tmp, "bin")
        self.xdg = os.path.join(self.tmp, "xdg")
        self.ctl_path = os.path.join(self.tmp, "ctl.json")
        self.log_path = os.path.join(self.tmp, "fake.log")
        self.wrap_log = os.path.join(self.tmp, "wrap.log")
        self.setup_path = os.path.join(self.tmp, "setup.log")
        os.makedirs(self.bin)
        fake = FAKE % {"python": sys.executable, "ctl": self.ctl_path, "log": self.log_path, "setup": self.setup_path}
        for name in ("python", "npm", "node", "bats"):
            with open(os.path.join(self.bin, name), "w") as f:
                f.write(fake)
            os.chmod(os.path.join(self.bin, name), 0o755)
        self.wrapper = os.path.join(self.bin, "wrapper")
        with open(self.wrapper, "w") as f:
            f.write(WRAPPER % {"python": sys.executable, "log": self.wrap_log})
        os.chmod(self.wrapper, 0o755)
        self.python = os.path.join(self.bin, "python")
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ.get("PATH", ""), XDG_STATE_HOME=self.xdg,
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="romp tests", GIT_AUTHOR_EMAIL="tests@example.invalid",
                        GIT_COMMITTER_NAME="romp tests", GIT_COMMITTER_EMAIL="tests@example.invalid")
        self.env.pop("ROMP_STATE_DIR", None)
        self.ctl({})
        self.git("init", "-q", "--bare", self.bare, cwd=self.tmp)
        self.git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.bare)
        os.makedirs(self.tree)
        self.git("init", "-q", cwd=self.tree)
        self.git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.tree)
        files = dict(SEED if seed is None else seed)
        files["scripts/upstream-ledger.py"] = fake
        # every head the runner sweeps holds the install steps its pytest leg's environment is built from
        files.setdefault(".github/workflows/ci.yml", SEED_CI)
        files.setdefault("kernel/session_host.py", SEED_HOST)
        self.write(files)
        os.chmod(os.path.join(self.tree, "scripts", "upstream-ledger.py"), 0o755)
        self.git("add", "-A", cwd=self.tree)
        self.git("commit", "-q", "-m", "seed", cwd=self.tree)
        self.git("remote", "add", "origin", self.bare, cwd=self.tree)
        self.git("push", "-q", "-u", "origin", "main", cwd=self.tree)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args, cwd=None):
        p = subprocess.run(["git", *args], cwd=cwd or self.tree, env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            raise AssertionError("git %s: %s" % (" ".join(args), p.stderr))
        return p.stdout.strip()

    def write(self, files):
        for path, content in files.items():
            p = os.path.join(self.tree, path)
            if content is None:
                os.remove(p)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(content)

    def change(self, files, msg="a change"):
        """One commit on a branch `work` cut from main, so origin/main is the merge base."""
        if self.git("rev-parse", "--abbrev-ref", "HEAD") != "work":
            self.git("checkout", "-q", "-b", "work")
        self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.head()

    def head(self):
        return self.git("rev-parse", "HEAD")

    def ctl(self, data):
        with open(self.ctl_path, "w") as f:
            json.dump(dict(data, tree=self.tree), f)

    def calls(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path) as f:
            return [json.loads(line) for line in f]

    def legs_called(self):
        return [c["leg"] for c in self.calls()]

    def setups(self):
        """The fake python's calls that build or probe the pytest leg's environment ({kind, exe, argv, names, home})."""
        if not os.path.exists(self.setup_path):
            return []
        with open(self.setup_path) as f:
            return [json.loads(line) for line in f]

    def sdk_root(self):
        return os.path.join(self.xdg, "romp", "sweeps", "sdk")

    def wraps(self):
        if not os.path.exists(self.wrap_log):
            return []
        with open(self.wrap_log) as f:
            return [json.loads(line) for line in f]

    def run(self, *extra, env=None, check=None):
        p = subprocess.run([sys.executable, str(SWEEP), "run", "--tree", self.tree, "--python", self.python, "--workers", "2", *extra],
                           env=env or self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        if check is not None and p.returncode != check:
            raise AssertionError("sweep run exited %d, expected %d:\n%s%s" % (p.returncode, check, p.stdout, p.stderr))
        return p

    def result_path(self, sha=None):
        return os.path.join(self.xdg, "romp", "sweeps", (sha or self.head()) + ".json")

    def data(self, sha=None):
        """The result file as written: {"schema", "sha", "branch", "tree", "runs"}."""
        with open(self.result_path(sha)) as f:
            return json.load(f)

    def result(self, sha=None):
        """The newest run's record (legs, verdict, red, invalid, runner, flakes...), with the file's sha, schema and runs."""
        data = self.data(sha)
        return dict(data["runs"][-1], schema=data["schema"], runs=data["runs"])


def expected_tree(w, sha):
    """What a leg must see in its checkout: every tracked entry of `sha` as FAKE's tree_of records it, read from git
    (before any road changes what the batcher's repository would check out)."""
    import hashlib
    out = {}
    env = dict(w.env, GIT_NO_REPLACE_OBJECTS="1")
    listing = subprocess.run(["git", "ls-tree", "-r", "-z", sha], cwd=w.tree, env=env, stdout=subprocess.PIPE, check=True).stdout
    for rec in listing.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, _typ, oid = meta.decode().split()
        data = subprocess.run(["git", "cat-file", "blob", oid], cwd=w.tree, env=env, stdout=subprocess.PIPE, check=True).stdout
        out[path.decode()] = ["link", data.decode()] if mode == "120000" else ["file", hashlib.sha256(data).hexdigest(), mode == "100755"]
    return out


class _Base(unittest.TestCase):
    seed = None

    def setUp(self):
        self.w = World(self.seed)
        self.addCleanup(self.w.close)


class Runner(_Base):
    def test_a_pass_writes_every_leg_under_the_full_sha(self):
        w = self.w
        sha = w.head()
        self.assertRegex(sha, r"^[0-9a-f]{40}$")
        w.run(check=0)
        self.assertTrue(os.path.exists(w.result_path(sha)), "the result is <state>/sweeps/<full sha>.json")
        r = w.result(sha)
        self.assertEqual(r["sha"], sha)
        self.assertEqual(r["verdict"], "pass")
        self.assertEqual(r["red"], [])
        self.assertEqual(sorted(r["legs"]), sorted(sweep.LEGS), "every leg of the roster is recorded")
        for name in sweep.LEGS:
            leg = r["legs"][name]
            if leg["owed"] is False:
                self.assertTrue(leg.get("why"), "%s is not owed and says why" % name)
                continue
            self.assertIn("cmd", leg, name)
            self.assertIs(type(leg["rc"]), int, name)
            self.assertEqual(leg["rc"], 0, name)
        self.assertEqual([n for n in sweep.LEGS if r["legs"][n]["owed"] is not False], list(sweep.LEGS),
                         "every head owes every leg: the webview legs whatever it changed, deps in every fresh checkout")
        self.assertEqual(w.legs_called(), list(sweep.LEGS), "run in roster order")
        self.assertTrue(r["finished"])
        self.assertIsNone(r["invalid"])

    def test_a_red_leg_is_named_and_every_later_leg_still_runs(self):
        w = self.w
        w.ctl({"rc": {"bats": 1}})
        p = w.run(check=1)
        r = w.result()
        self.assertEqual(r["verdict"], "red")
        self.assertEqual(r["red"], ["bats"])
        self.assertEqual(r["legs"]["bats"]["rc"], 1)
        self.assertEqual(w.legs_called(), list(sweep.LEGS), "the legs after the red one ran too")
        self.assertIn("sweep red at %s: bats (rc 1)" % w.head()[:10], p.stdout)

    def test_every_head_owes_the_webview_legs_whatever_it_changed(self):
        """Round 1, decision 11 (regression-1): the webview legs read files outside kernel/kernel.py, ui/ and
        vscode-extension/, so every head owes them, whatever its diff and whether or not origin/main exists; the result
        says so and records no base. The head's runner marked them not owed for a change to kernel/other.py or
        README.md alone."""
        cases = [(path, None) for path in ("kernel/kernel.py", "ui/x.js", "vscode-extension/src/a.ts", "README.md", "kernel/other.py")]
        cases.append(("kernel/other.py", "no origin/main"))
        for path, road in cases:
            with self.subTest(path=path, road=road):
                w = World()
                self.addCleanup(w.close)
                w.change({path: "changed\n"})
                if road:
                    w.git("update-ref", "-d", "refs/remotes/origin/main")
                w.run(check=0)
                self.assertEqual(w.legs_called(), list(sweep.LEGS), "the npm fake ran the webview legs")
                r = w.result()
                for name in sweep.WEBVIEW_LEGS:
                    self.assertIs(r["legs"][name]["owed"], True, "%s after a change to %s" % (name, path))
                    self.assertEqual(r["legs"][name]["why"], sweep.WEBVIEW_WHY)
                self.assertEqual(r["owed"], {"webview": {"owed": True, "why": sweep.WEBVIEW_WHY}})
                self.assertNotIn("base", r, "no leg is decided by a merge base, so none is recorded")

    def test_a_sweep_at_a_merge_commit_owes_the_webview_legs(self):
        """Round 1, C5 (regression-2): the remedy for a batch merged behind main sweeps a checkout at the merge commit M
        once origin/main holds M. M's second parent changed kernel/kernel.py; the head's runner took the merge base
        with origin/main, M itself, and marked the webview legs not owed. Every head owes them."""
        w = self.w
        w.change({"kernel/kernel.py": "VERSION = 2\n"})
        w.git("checkout", "-q", "main")
        w.git("merge", "-q", "--no-ff", "-m", "Merge the batch", "work")
        w.git("push", "-q", "origin", "main")
        self.assertEqual(w.head(), w.git("rev-parse", "origin/main"), "origin/main holds the merge commit")
        w.run(check=0)
        self.assertEqual(w.legs_called(), list(sweep.LEGS), "the webview legs ran at the merge commit")
        r = w.result()
        for name in sweep.WEBVIEW_LEGS:
            self.assertIs(r["legs"][name]["owed"], True, "%s at the merge commit" % name)

    def test_a_sha_without_the_extension_marks_deps_and_the_webview_legs_not_owed_for_that_alone(self):
        """The one reason the runner gives for deps and the webview legs not owed: the sha has no
        vscode-extension/package.json."""
        w = self.w
        w.change({"vscode-extension/package.json": None})
        w.run(check=0)
        r = w.result()
        for name in sweep.EXTENSION_LEGS:
            self.assertEqual((r["legs"][name]["owed"], r["legs"][name]["why"]), (False, sweep.NO_PACKAGE_JSON), name)
        self.assertEqual(r["owed"], {"webview": {"owed": False, "why": sweep.NO_PACKAGE_JSON}})
        self.assertEqual(w.legs_called(), [n for n in sweep.LEGS if n not in sweep.EXTENSION_LEGS])

    def test_a_dirty_tree_is_swept_at_its_sha_and_the_edits_named_as_not_swept(self):
        """Round 1, A3 and decision 17 (replacing the dirty-tree refusal): the batcher's tree is read for its HEAD sha
        and branch only, so it need not be clean. The runner prints one line naming how many uncommitted edits it holds
        and that they are not swept, and the legs read the sha's bytes, not the edits."""
        w = self.w
        sha = w.head()
        expected = expected_tree(w, sha)
        w.write({"README.md": "# edited, not committed\n", "notes/new.txt": "new\n"})
        p = w.run(check=0)
        self.assertIn("sweep %s: %s has 2 uncommitted edits (git status); they are not swept: the legs run in a private "
                      "checkout of %s" % (sha[:10], w.tree, sha[:10]), p.stdout)
        self.assertEqual(w.result()["verdict"], "pass")
        for c in w.calls():
            self.assertEqual(c["tree"], expected, "%s saw the sha's tree" % c["leg"])
        w.git("checkout", "-q", "--", ".")
        w.git("clean", "-q", "-fd")
        self.assertNotIn("uncommitted", w.run(check=0).stdout, "a clean tree prints no notice")

    def test_the_runner_writes_nothing_in_the_tree(self):
        w = self.w
        before = w.git("status", "--porcelain", "--ignored", "--untracked-files=all")
        w.run(check=0)
        self.assertEqual(w.git("status", "--porcelain", "--ignored", "--untracked-files=all"), before)
        self.assertTrue(w.result()["legs"]["pytest"]["log"].startswith(os.path.join(w.xdg, "romp", "sweeps", "logs", w.head())),
                        "logs live under the state dir")

    def test_what_a_leg_does_in_the_batchers_tree_reaches_no_leg(self):
        """Round 1, A3 (replacing the end comparison of HEAD and status): nothing done in the batcher's tree after the
        sha is read reaches a leg. A leg that commits there (HEAD moves) and legs that edit and restore a tracked file
        there leave the run passing, and every leg reads the sha's bytes."""
        w = self.w
        start = w.head()
        expected = expected_tree(w, start)
        w.ctl({"action": {"bats": "commit", "pytest": "tree-edit", "tools": "tree-restore"}})
        p = w.run(check=0)
        self.assertNotEqual(w.head(), start, "HEAD moved in the batcher's tree during the run")
        r = w.result(start)
        self.assertEqual((r["verdict"], r["invalid"]), ("pass", None), p.stdout + p.stderr)
        for c in w.calls():
            self.assertEqual(c["tree"], expected, "%s saw the sha's tree" % c["leg"])
            self.assertTrue(c["root"].startswith(os.path.join(w.xdg, "romp", "sweeps", "trees", start[:12] + "-")), c["root"])

    def test_a_leg_that_changes_its_checkout_makes_the_run_invalid(self):
        """Round 1, A4, the runner's one producer of invalid: after every leg the checkout is read again, and a tracked
        file changed or deleted, or an untracked file the tracked .gitignore does not ignore, records the run invalid
        naming the paths and the leg; the legs after it do not run. An ignored build product is allowed."""
        cases = (("edit", "content 1 (README.md)"), ("delete", "missing 1 (kernel/other.py)"), ("leak", "untracked 1 (leaked.txt)"))
        for act, named in cases:
            with self.subTest(act=act):
                w = World()
                self.addCleanup(w.close)
                w.ctl({"action": {"manager": act}})
                p = w.run(check=3)
                self.assertEqual(w.legs_called(), ["deps", PYTEST_LEG, "bats", "manager"], "the legs after it did not run")
                self.assertIn("sweep invalid at %s: after the manager leg" % w.head()[:10], p.stdout)
                r = w.result()
                self.assertEqual(r["verdict"], "invalid")
                self.assertIn("after the manager leg the checkout is not the sha's tree: %s" % named, r["invalid"])
                self.assertIn("the legs after it did not run", r["invalid"])
        w = World()
        self.addCleanup(w.close)
        w.ctl({"action": {"manager": "ignored"}})
        w.run(check=0)
        self.assertEqual(w.result()["invalid"], None, "an ignored build product left in the checkout is allowed")

    def test_the_file_says_running_until_the_end(self):
        w = self.w
        copy = os.path.join(w.tmp, "mid-run.json")
        w.ctl({"action": {"bats": "copy-result"}, "result": w.result_path(), "copy_to": copy})
        w.run(check=0)
        with open(copy) as f:
            mid = json.load(f)["runs"][-1]
        self.assertEqual(mid["verdict"], "running")
        self.assertIsNone(mid["finished"])
        self.assertEqual(mid["legs"]["pytest"]["rc"], 0, "written after every leg")
        self.assertIsNone(mid["legs"]["manager"]["rc"])
        self.assertEqual(w.result()["verdict"], "pass")

    def test_a_second_run_on_the_same_sha_is_refused(self):
        w = self.w
        d = os.path.join(w.xdg, "romp", "sweeps")
        os.makedirs(d)
        with open(os.path.join(d, w.head() + ".lock"), "a+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            p = w.run(check=2)
        self.assertIn("a sweep of %s is already running" % w.head()[:10], p.stderr)
        self.assertFalse(os.path.exists(w.result_path()))
        self.assertEqual(w.calls(), [])
        w.run(check=0)

    def test_the_pytest_leg_gets_the_short_tmpdir_and_its_command(self):
        """The pytest leg's TMPDIR is the box rule's short shape and is gone after the run; its command is CI's with the
        runner's named differences (CiParity holds the two to them); an inherited GIT_DIR does not move the runner's own
        git calls."""
        w = self.w
        env = dict(w.env, GIT_DIR=os.path.join(w.tmp, "no-such-git-dir"))
        w.run(env=env, check=0)
        call = [c for c in w.calls() if c["leg"] == "pytest"][0]
        tmpdir = call["values"]["TMPDIR"]
        self.assertLessEqual(len(os.fsencode(tmpdir)), len(BOX_TMPDIR_TEMPLATE), tmpdir)
        self.assertNotRegex(tmpdir, r"-[A-Za-z]", "a letter after the dash spells a short option")
        self.assertFalse(os.path.exists(tmpdir), "the runner removes its TMPDIR")
        argv = call["argv"]
        self.assertEqual(" ".join(argv[:4]), "-m pytest tests -n")
        self.assertIn("no:anyio", argv)
        self.assertIn("--ignore=tests/test_cut_turn_tree_kill.py", argv)
        self.assertEqual(w.result()["sha"], w.head(), "an inherited GIT_DIR does not move the runner's own git calls")

    def test_a_wrap_prefixes_one_leg_and_its_rc_is_the_legs(self):
        """A leg's own --wrap prefix replaces * for it, and the recorded rc is the wrapper's. The wrap runs with the
        runner's environment and the allowlist applies after it, so a variable the wrap sets does not reach the leg."""
        w = self.w
        w.run("--wrap", "pytest=%s pytest-only" % w.wrapper, "--wrap", "bats=env SWEEP_WRAPPED=1", check=0)
        self.assertEqual([c["tag"] for c in w.wraps()], ["pytest-only"], "the pytest prefix wrapped the pytest leg alone")
        by_leg = {c["leg"]: c for c in w.calls()}
        self.assertNotIn("SWEEP_WRAPPED", by_leg["bats"]["names"], "a variable the wrap sets does not reach the leg")
        r = w.result()
        self.assertEqual(r["legs"]["pytest"]["wrap"], [w.wrapper, "pytest-only"])
        self.assertIsNone(r["legs"]["manager"]["wrap"])
        w2 = World()
        self.addCleanup(w2.close)
        w2.run("--wrap", "*=%s star" % w2.wrapper, "--wrap", 'bats=sh -c "exit 7" --', check=1)
        r2 = w2.result()
        self.assertEqual(r2["legs"]["bats"]["rc"], 7, "the recorded rc is the wrapper's")
        self.assertEqual(r2["red"], ["bats"])
        self.assertIn("pytest", [c["leg"] for c in w2.calls()], "* applies to a leg with no prefix of its own")
        self.assertNotIn("bats", w2.legs_called(), "the leg's own prefix replaced *")
        self.assertNotIn("bats", [c["leg"] for c in w2.wraps()])

    def test_a_wrap_that_runs_nothing_is_red_not_a_pass(self):
        """A wrapper that exits 0 without running its command (`true`; `systemd-run --user` without --wait, which
        returns once the unit has started) gives every leg rc 0. A test leg with rc 0 and no test counted in its
        log is red, named, so such a run can never be recorded as a pass."""
        w = self.w
        p = w.run("--wrap", "*=true", check=1)
        r = w.result()
        self.assertEqual(r["verdict"], "red", p.stdout + p.stderr)
        self.assertEqual(r["red"], [PYTEST_LEG, "bats", "manager", "tools", "npm-test"])
        for name in r["red"]:
            self.assertEqual(r["legs"][name]["rc"], 0, name)
            self.assertIn(r["legs"][name].get("tests"), (None, 0), name)
        self.assertIn("pytest (rc 0 but no test ran), bats (rc 0 but no test ran)", p.stdout)
        self.assertEqual(w.calls(), [], "nothing ran: the wrapper swallowed every command")
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "red", a["line"])

    def test_the_tests_a_leg_ran_are_counted_from_its_log(self):
        w = self.w
        w.run(check=0)
        r = w.result()
        self.assertEqual({n: r["legs"][n].get("tests") for n in (PYTEST_LEG, "bats", "manager", "tools")},
                         {PYTEST_LEG: 3, "bats": 1, "manager": 1, "tools": 2})
        self.assertNotIn("tests", r["legs"]["ledger"], "the ledger check is not a test leg")
        cases = (
            ("bats", "1..2\nok 1 a\nnot ok 2 b\n", "bats (rc 0 but its log shows 1 failed)"),
            ("manager", "# pass 0\n# fail 0\n", "manager (rc 0 but no test ran)"),
            (PYTEST_LEG, "5 skipped in 0.01s\n", "pytest (rc 0 but no test ran)"),
            (PYTEST_LEG, "no summary line at all\n", "pytest (rc 0 but no test ran)"),
        )
        for leg, out, named in cases:
            with self.subTest(leg=leg, out=out):
                w2 = World()
                self.addCleanup(w2.close)
                w2.ctl({"out": {leg: out}})
                p = w2.run(check=1)
                self.assertEqual(w2.result()["red"], [leg])
                self.assertIn(named, p.stdout)
        w3 = World()
        self.addCleanup(w3.close)
        w3.ctl({"out": {"tools": "\u2139 tests 6\n\u2139 pass 6\n\u2139 fail 0\n"}})    # node's spec reporter
        w3.run(check=0)
        self.assertEqual(w3.result()["legs"]["tools"]["tests"], 6)

    FLAKE = "tests/test_notes.py::test_order (a known flake, recorded in the flake census)"

    def test_a_leg_rerun_after_a_named_flake_appends_a_run_and_keeps_the_failed_one(self):
        """A --leg re-run counts only over the newest run's recorded failure, named as a known flake, at the same full
        sha (pre-round ruling Q11). Results are append-only (frozen-head item 1): the re-run is a new run in the file
        (kind leg, the re-run legs, the flake), the failed run stays as it was, and the pass line names both."""
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        first = w.data()
        self.assertEqual(first["runs"][0]["red"], [PYTEST_LEG])
        w.ctl({})
        before = len(w.calls())
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=0)
        data = w.data()
        self.assertEqual(data["runs"][0], first["runs"][0], "the failed run is kept as it was")
        rerun = data["runs"][1]
        self.assertEqual((rerun["kind"], sorted(rerun["legs"]), rerun["flakes"], rerun["sha"], rerun["verdict"]),
                         ("leg", [PYTEST_LEG], {PYTEST_LEG: self.FLAKE}, w.head(), "pass"))
        self.assertEqual(rerun["legs"]["pytest"]["rc"], 0)
        self.assertEqual([c["leg"] for c in w.calls()[before:]], ["deps", PYTEST_LEG],
                         "only the named leg ran again, after the fresh checkout's npm ci")
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "pass", a["line"])
        self.assertIn("pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE, a["line"])
        self.assertIn("pytest re-run after a known flake", p.stdout)
        self.assertEqual(a["result"]["legs"]["bats"], first["runs"][0]["legs"]["bats"], "the other legs are the full run's")
        w.change({"README.md": "moved on\n"})
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("no result at %s to re-run a leg in; run the full sweep" % w.head()[:10], p.stderr)

    def test_a_leg_rerun_is_refused_without_a_flake_over_a_pass_or_before_the_sweep_finished(self):
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        path = w.result_path()
        with open(path) as f:
            red = f.read()
        w.ctl({})
        before = len(w.calls())
        # round 1, extra7-7: the remedy for a failure that is not a known flake is a fix and a new head, never a full sweep
        # at the same sha, which cannot count over the failed run without --flake
        for extra, named in ((("--leg", "pytest"), "--leg re-runs a leg only after a known flake: name it with --flake (the test "
                                                   "and where it is recorded as a known flake); anything else is a failure: fix "
                                                   "it and sweep the new head"),
                             (("--leg", "pytest", "--flake", "  "), "--leg re-runs a leg only after a known flake"),
                             (("--flake", self.FLAKE), "--flake on a full run names the leg it is for: --flake LEG=TEXT"),
                             (("--leg", "bats", "--flake", self.FLAKE), "bats passed at %s; there is no failure to re-run" % w.head()[:10])):
            with self.subTest(extra=extra):
                p = w.run(*extra, check=2)
                self.assertIn(named, p.stderr)
                with open(path) as f:
                    self.assertEqual(f.read(), red, "a refused re-run leaves the result as it was")
        self.assertEqual(len(w.calls()), before, "nothing ran")
        w.run("--leg", "pytest", "--flake", self.FLAKE, check=0)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("pytest passed at %s; there is no failure to re-run" % w.head()[:10], p.stderr)
        data = json.loads(red)
        data["runs"][-1].update(finished=None, verdict="running")
        sweep.write_result(path, data)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("the sweep at %s has not finished" % w.head()[:10], p.stderr)
        data = json.loads(red)
        data["runs"][-1]["legs"]["pytest"]["finished"] = None
        sweep.write_result(path, data)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("pytest has no finished first run at %s to re-run" % w.head()[:10], p.stderr)

    def test_a_leg_rerun_over_a_result_recorded_under_another_leg_environment_is_refused(self):
        """A re-run would mix two leg environments in one result (decision 10: a result made under another environment
        policy is not the same gate), so it is refused and the full sweep named."""
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        data = w.data()
        (data["runs"][-1] if "runs" in data else data)["runner"]["leg_env"] = {"allow": ["USER"], "hash": "0" * 64}
        sweep.write_result(w.result_path(), data)
        before = len(w.calls())
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("was recorded under another leg environment (hash 000000000000, this runner's %s)" % sweep.policy_hash()[:12],
                      p.stderr)
        self.assertEqual(len(w.calls()), before, "nothing ran")

    def test_a_leg_rerun_over_an_invalid_result_is_refused_and_changes_nothing(self):
        """Round 1, tests-1 and extra4-3: a --leg re-run over a result whose newest full run is invalid is refused before
        anything runs (no npm ci setup, no leg), the result file byte-identical and still read invalid. The invalid run
        is made the one way the runner makes one (A4: a leg changed its checkout), after pytest failed; without the
        guard, one re-run of pytest with a flake would be appended over the invalid run."""
        w = self.w
        w.ctl({"rc": {"pytest": 1}, "action": {"manager": "edit"}})
        w.run(check=3)
        path = w.result_path()
        with open(path, "rb") as f:
            before = f.read()
        self.assertEqual(sweep.assess(w.head(), env=w.env)["case"], "invalid")
        w.ctl({})
        calls = len(w.calls())
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("the result at %s is invalid (after the manager leg the checkout is not the sha's tree: content 1 "
                      "(README.md)" % w.head()[:10], p.stderr)
        self.assertEqual(len(w.calls()), calls, "no leg ran, the setup's npm ci included")
        with open(path, "rb") as f:
            self.assertEqual(f.read(), before, "the result file is byte-identical")
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "invalid", a["line"])

    def test_a_full_run_after_a_red_one_counts_only_with_a_flake_naming_each_failed_leg(self):
        """Frozen-head item 1: a finished red result is never overwritten. A full run at a sha whose newest run failed
        legs is refused up front, the file untouched, unless --flake LEG=TEXT names each failed leg (and no other);
        with them the run is appended, the red run kept, and the pass line names each failure and its flake."""
        w = self.w
        w.ctl({"rc": {"pytest": 1, "bats": 1}})
        w.run(check=1)
        path = w.result_path()
        with open(path) as f:
            red = f.read()
        w.ctl({})
        before = len(w.calls())
        flake = self.FLAKE
        for extra, named in (((), "the run at %s failed pytest in run 1 (rc 1), bats in run 1 (rc 1); a later run counts over a "
                                  "failed leg only with --flake LEG=TEXT naming each" % w.head()[:10]),
                             (("--flake", "pytest=" + flake), "failed bats in run 1 (rc 1)"),
                             (("--flake", "pytest=" + flake, "--flake", "bats=" + flake, "--flake", "tools=" + flake),
                              "--flake names tools, which has no failed run at %s to excuse" % w.head()[:10])):
            with self.subTest(extra=extra):
                p = w.run(*extra, check=2)
                self.assertIn(named, p.stderr)
                with open(path) as f:
                    self.assertEqual(f.read(), red, "a refused run leaves the result as it was")
        self.assertEqual(len(w.calls()), before, "nothing ran")
        w.run("--flake", "pytest=" + flake, "--flake", "bats=" + flake, check=0)
        data = w.data()
        self.assertEqual(data["runs"][0], json.loads(red)["runs"][0], "the red run is kept")
        self.assertEqual((len(data["runs"]), data["runs"][1]["kind"], data["runs"][1]["flakes"]),
                         (2, "full", {PYTEST_LEG: flake, "bats": flake}))
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "pass", a["line"])
        for n in (PYTEST_LEG, "bats"):
            self.assertIn("%s re-run after a known flake (first run rc 1; flake: %s)" % (n, flake), a["line"])

    def test_a_leg_that_fails_again_after_its_flake_leaves_the_sha_unable_to_pass(self):
        """A known flake is excused once: a leg that fails its re-run leaves no run at that sha able to pass. The result
        reads red naming both runs, and the runner refuses a further run of either kind up front."""
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        w.run("--leg", "pytest", "--flake", self.FLAKE, check=1)
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "red", a["line"])
        self.assertIn("pytest failed in runs 1 and 2; a known flake is excused once (--flake), so no run at this sha can pass", a["line"])
        self.assertIn("fix it and sweep the new head", a["line"])
        w.ctl({})
        for extra in (("--flake", "pytest=" + self.FLAKE), ("--leg", "pytest", "--flake", self.FLAKE)):
            with self.subTest(extra=extra):
                p = w.run(*extra, check=2)
                self.assertIn("no run at %s can pass: pytest failed in runs 1 and 2" % w.head()[:10], p.stderr)
        self.assertEqual(len(w.data()["runs"]), 2)

    def test_an_invalid_run_needs_no_flake_before_a_green_and_the_line_names_it(self):
        """Round 1, decision 18: an invalid run is not a test failure, so the next full run needs no --flake, even for a
        leg the invalid run failed, but the pass line names the invalid run."""
        w = self.w
        w.ctl({"action": {"manager": "leak"}, "rc": {"pytest": 1}})
        p = w.run(check=3)
        m = re.search(r"sweep invalid at %s: (.*)$" % w.head()[:10], p.stdout, re.M)
        self.assertTrue(m, p.stdout)
        reason = m.group(1)
        self.assertIn("leaked.txt", reason)
        w.ctl({})
        p = w.run(check=0)
        self.assertIn("an earlier run 1 (started ", p.stdout)
        self.assertIn(") was invalid: %s" % reason, p.stdout)
        self.assertEqual([r["verdict"] for r in w.data()["runs"]], ["invalid", "pass"])

    def test_a_schema_1_result_is_moved_aside_and_a_leg_rerun_over_one_refused(self):
        """A result of the runner before round 1 (schema 1) swept the batcher's own tree; no reader counts it. A full run
        moves it aside, named, and writes a new history; a --leg re-run over it is refused."""
        w = self.w
        path = w.result_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        old = {"schema": 1, "sha": w.head(), "branch": "main", "started": "s", "finished": "f", "legs": {}, "history": [],
               "verdict": "red", "red": [PYTEST_LEG], "invalid": None}
        sweep.write_result(path, old)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("schema 1, recorded by a runner that swept the batcher's own tree); run the full sweep", p.stderr)
        p = w.run(check=0)
        aside = path[:-len(".json")] + ".schema-1.json"
        self.assertIn("moved the schema-1 result aside to %s" % aside, p.stdout)
        with open(aside) as f:
            self.assertEqual(json.load(f), old)
        self.assertEqual((w.data()["schema"], len(w.data()["runs"])), (2, 1))

    def test_a_result_whose_runs_record_no_private_checkout_is_moved_aside_and_a_leg_rerun_over_one_refused(self):
        """A schema-2 result written by a runner that swept the batcher's own tree (no runner.checkout) is treated as a
        schema-1 one: a full run moves it aside, named, and writes a new history; a --leg re-run over it is refused."""
        w = self.w
        path = w.result_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        run = {"kind": "full", "sha": w.head(), "branch": "main", "started": "s", "finished": "f", "flakes": {}, "legs": {},
               "verdict": "red", "red": [PYTEST_LEG], "invalid": None,
               "runner": {"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()}}}
        old = {"schema": 2, "sha": w.head(), "branch": "main", "runs": [run]}
        sweep.write_result(path, old)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("run 1 records no private checkout, recorded by a runner that swept the batcher's own tree); run the "
                      "full sweep", p.stderr)
        p = w.run(check=0)
        aside = path[:-len(".json")] + ".no-checkout.json"
        self.assertIn("moved the result aside to %s" % aside, p.stdout)
        with open(aside) as f:
            self.assertEqual(json.load(f), old)
        self.assertEqual((w.data()["schema"], len(w.data()["runs"])), (2, 1))

    def test_an_empty_glob_is_a_red_leg_not_a_bare_run(self):
        seed = dict(SEED)
        del seed["tests/a.bats"]
        w = World(seed)
        self.addCleanup(w.close)
        w.run(check=1)
        r = w.result()
        self.assertEqual(r["red"], ["bats"])
        self.assertIsNone(r["legs"]["bats"]["rc"])
        self.assertIn("no files matched tests/*.bats", r["legs"]["bats"]["error"])
        self.assertNotIn("bats", w.legs_called(), "bats was never run with no file arguments")

    def test_deps_runs_npm_ci_in_the_fresh_checkout_whatever_the_batchers_tree_holds(self):
        """A fresh checkout never holds node_modules, so deps (npm ci from the sha's lockfile) is owed in every checkout,
        and a node_modules in the batcher's tree (a symlink to shared deps, which npm ci would have emptied) is neither
        read nor touched."""
        w = self.w
        shared = os.path.join(w.tmp, "shared-node_modules")
        os.makedirs(shared)
        with open(os.path.join(shared, "kept.txt"), "w") as f:
            f.write("shared\n")
        os.symlink(shared, os.path.join(w.tree, "vscode-extension", "node_modules"))
        w.run(check=0)
        self.assertIn("deps", w.legs_called(), "deps ran")
        deps = w.result()["legs"]["deps"]
        self.assertEqual((deps["owed"], deps["cmd"], deps["why"]), (True, list(sweep.DEPS_CMD), "a fresh checkout has no vscode-extension/node_modules"))
        call = [c for c in w.calls() if c["leg"] == "deps"][0]
        self.assertEqual(call["cwd"], os.path.join(call["root"], "vscode-extension"))
        self.assertNotEqual(os.path.realpath(call["root"]), os.path.realpath(w.tree))
        self.assertEqual(os.listdir(shared), ["kept.txt"], "the batcher's shared deps are untouched")

    def test_an_environment_without_the_pytest_plugins_is_refused(self):
        """The pytest leg's interpreter is the venv the runner builds at ci.yml's install steps: a venv that lacks a
        module the leg needs after them (here the probe says so; PytestEnvironment's case drops the plugin from ci.yml)
        is refused, nothing recorded, and the venv removed."""
        w = self.w
        w.ctl({"missing": ["xdist"]})
        p = w.run(check=2)
        self.assertIn("after the install steps the venv lacks xdist, which the pytest leg needs", p.stderr)
        self.assertFalse(os.path.exists(w.result_path()))
        self.assertEqual(sorted(n for n in os.listdir(w.sdk_root()) if not n.endswith((".log", ".lock"))), [],
                         "the failed build's venv is removed")

    def test_check_reads_the_result_as_batch_does(self):
        w = self.w
        cmd = [sys.executable, str(SWEEP), "check", "--tree", w.tree]
        p = subprocess.run(cmd, env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL sweep missing: no result for HEAD %s" % w.head(), p.stdout)
        w.run(check=0)
        p = subprocess.run(cmd, env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("ok   sweep at %s: pass" % w.head()[:10], p.stdout)

    def check(self, *extra):
        return subprocess.run([sys.executable, str(SWEEP), "check", "--tree", self.w.tree, *extra], env=self.w.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_check_tells_a_stale_result_for_the_trees_branch_from_a_missing_one(self):
        """Round 1, extra5-7: check reads the tree's HEAD as verify reads the batch head, with the branch: --branch
        defaults to the branch the tree has checked out, so a result recorded for that branch at an older sha reads
        stale, as verify and plan say, not missing. An explicit SHA other than HEAD is read without it."""
        w = self.w
        w.change({"README.md": "one\n"})
        old = w.head()
        w.run(check=0)
        w.change({"README.md": "two\n"})
        p = self.check()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL sweep stale: the newest result for work is at %s" % old[:10], p.stdout)
        p = self.check("--branch", "elsewhere")
        self.assertIn("FAIL sweep missing: no result for HEAD %s" % w.head(), p.stdout, "a --branch given is the one read")
        p = self.check(old)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("ok   sweep at %s: pass" % old[:10], p.stdout)
        seed = w.git("rev-parse", "main")
        p = self.check(seed)
        self.assertIn("FAIL sweep missing: no result for %s %s" % (seed[:10], seed), p.stdout,
                      "a SHA other than HEAD is not read against the tree's branch")

    def test_check_refuses_what_verify_refuses_after_a_pass(self):
        """Round 1, extra5-7 and C1: check prints what verify reads. A result that marks a webview leg not owed for any
        reason but a missing extension reads invalid (the reader's refusal, so check has it too), and one that marks deps
        and the webview legs not owed for having no vscode-extension/package.json reads invalid when the sha's tree holds
        one, which the reader alone cannot tell (verify, plan and --repin read the tree)."""
        w = self.w
        w.run(check=0)
        data = w.data()
        run = data["runs"][-1]
        run["legs"]["typecheck"] = {"owed": False, "rc": None, "why": "ui/ untouched"}
        run["verdict"] = sweep.run_verdict(run)
        sweep.write_result(w.result_path(), data)
        p = self.check()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL sweep invalid at %s: typecheck marked not owed for a reason other than "
                      "'no vscode-extension/package.json' ('ui/ untouched')" % w.head()[:10], p.stdout)
        for n in sweep.EXTENSION_LEGS:
            run["legs"][n] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
        run["verdict"] = sweep.run_verdict(run)
        sweep.write_result(w.result_path(), data)
        self.assertEqual(sweep.assess(w.head(), env=w.env)["case"], "pass", "the reader alone reads no tree")
        p = self.check()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL sweep invalid at %s: the result marks deps, typecheck, npm-test, build not owed for having no "
                      "vscode-extension/package.json, but HEAD's tree holds vscode-extension/package.json" % w.head()[:10], p.stdout)


def _kill_quietly(pid):
    """Cleanup for a writer pid a test recorded itself, in case the runner under test did not stop it."""
    try:
        os.kill(pid, 9)
    except (ProcessLookupError, PermissionError):
        pass


def _alive(pid):
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


class Checkout(_Base):
    """Round 1, Class A: the legs run in a private clone of the exact sha under the state dir, verified before any leg
    (A2), re-read after every leg (A4), and removed on every exit path with TMPDIR (A5); stale checkouts of runs that
    are gone are removed; a --leg re-run installs the deps first; the result records the checkout."""

    def trees(self):
        return os.path.join(self.w.xdg, "romp", "sweeps", "trees")

    def test_the_legs_run_in_a_private_clone_of_the_sha_that_is_gone_afterwards(self):
        w = self.w
        sha = w.head()
        expected = expected_tree(w, sha)
        p = w.run(check=0)
        r = w.result()
        co = r["runner"]["checkout"]
        self.assertEqual((co["form"], co["files"], co["setup"]), ("clone", len(expected), None))
        self.assertTrue(co["path"].startswith(os.path.join(self.trees(), sha[:12] + "-")), co["path"])
        for key in ("create_s", "verify_s"):
            self.assertIsInstance(co[key], (int, float))
        for c in w.calls():
            self.assertEqual(c["root"], co["path"], "%s ran in the checkout" % c["leg"])
            self.assertEqual(c["tree"], expected)
        self.assertFalse(os.path.exists(co["path"]), "the checkout is removed at the end")
        self.assertEqual(os.listdir(self.trees()), [], "and its sha marker with it")
        self.assertFalse(os.path.exists(r["runner"]["tmpdir"]))
        # the clone is the checkout's own repository: a leg's git writes land there, not in the batcher's
        self.assertEqual(w.git("worktree", "list", "--porcelain").count("worktree "), 1)
        self.assertIn("ok   sweep at %s: pass" % sha[:10], p.stdout)

    def test_a_checkout_that_is_not_the_shas_tree_is_refused_by_class(self):
        """A2: the five refusal classes, each planted between the checkout's creation and its verification (the
        SWEEP_TEST_PLANT seam): refused, exit 2, naming the class, count and path; nothing run or recorded, the checkout
        removed."""
        seed = dict(SEED)
        seed["bin/run.sh"] = "#!/bin/sh\nexit 0\n"
        cases = (("byte", "README.md", "content 1 (README.md)"), ("extra", "conftest.py", "extra 1 (conftest.py)"),
                 ("missing", "kernel/other.py", "missing 1 (kernel/other.py)"), ("mode", "bin/run.sh", "mode 1 (bin/run.sh)"),
                 ("symlink-to-file", "bin/kernel-link", "symlink 1 (bin/kernel-link)"))
        for op, rel, named in cases:
            with self.subTest(op=op):
                w = World(seed)
                self.addCleanup(w.close)
                os.chmod(os.path.join(w.tree, "bin", "run.sh"), 0o755)
                os.symlink("../kernel/kernel.py", os.path.join(w.tree, "bin", "kernel-link"))
                w.change({})
                p = w.run(env=dict(w.env, SWEEP_TEST_PLANT=json.dumps([[op, rel]])), check=2)
                self.assertIn("the checkout of %s is not the sha's tree (%s); it is removed, and nothing was run or recorded"
                              % (w.head()[:10], named), p.stderr)
                self.assertEqual(w.calls(), [])
                self.assertFalse(os.path.exists(w.result_path()))
                self.assertEqual(os.listdir(os.path.join(w.xdg, "romp", "sweeps", "trees")), [])

    # What each name in an ancestor directory does to a leg: node_modules/@types reaches tsc and require(); a
    # package.json's "type" changes how node loads a .js file with no nearer one; a tsconfig.json or jsconfig.json is the
    # nearest one esbuild finds above a ui/ file (its paths can map an import to a file outside the sha).
    ANCESTOR_PLANTS = (("node_modules", None), ("package.json", '{"type": "module"}\n'),
                       ("tsconfig.json", '{"compilerOptions": {"paths": {"marked": ["./planted.js"]}}}\n'),
                       ("jsconfig.json", '{"compilerOptions": {"paths": {"marked": ["./planted.js"]}}}\n'))

    @staticmethod
    def plant_above(d, name, text):
        full = os.path.join(d, name)
        os.makedirs(d, exist_ok=True)
        if text is None:
            os.makedirs(os.path.join(full, "@types", "planted"))
        else:
            with open(full, "w") as f:
                f.write(text)
        return full

    def test_a_tool_config_name_in_an_ancestor_of_the_checkout_is_refused(self):
        """A2: node_modules, package.json, tsconfig.json and jsconfig.json are each looked up in every ancestor directory
        by node, tsc or esbuild, so one above the checkout (here in the state root) would reach the legs from outside
        the sha: each refuses the run by name, one pin per name, nothing run or recorded, the checkout removed."""
        for name, text in self.ANCESTOR_PLANTS:
            with self.subTest(name=name):
                w = World()
                self.addCleanup(w.close)
                planted = self.plant_above(w.xdg, name, text)
                p = w.run(check=2)
                self.assertIn("has %s in an ancestor directory (1: %s), which node, tsc or esbuild would read from outside "
                              "the sha" % (name, planted), p.stderr)
                self.assertEqual(w.calls(), [])
                self.assertFalse(os.path.exists(w.result_path()))
                self.assertEqual(os.listdir(os.path.join(w.xdg, "romp", "sweeps", "trees")), [])
        self.assertEqual(tuple(n for n, _t in self.ANCESTOR_PLANTS), sweep.ANCESTOR_NAMES, "one pin per name the runner refuses")

    def test_a_tool_config_name_that_appears_above_the_checkout_during_a_leg_makes_the_run_invalid(self):
        """A4: the refusal before the first leg reads the ancestors once; one of the names made in an ancestor during a
        leg (here by the bats leg, standing for any process of the batcher's user) would reach the legs after it, so the
        re-read after every leg names it and the run is invalid, the legs after it not run."""
        for name, text in self.ANCESTOR_PLANTS:
            with self.subTest(name=name):
                w = World()
                self.addCleanup(w.close)
                real = os.path.join(w.tmp, "realbin")
                os.makedirs(real)
                os.rename(os.path.join(w.bin, "bats"), os.path.join(real, "bats"))
                target = os.path.join(w.xdg, name)
                make = ("mkdir -p '%s/@types/planted'" % target) if text is None else ("printf '%%s' '%s' > '%s'" % (text, target))
                with open(os.path.join(w.bin, "bats"), "w") as f:
                    # not on the runner's `bats --version` read, which comes before any leg
                    f.write("#!/bin/sh\n[ \"$1\" = --version ] || %s\nexec '%s' \"$@\"\n" % (make, os.path.join(real, "bats")))
                os.chmod(os.path.join(w.bin, "bats"), 0o755)
                p = w.run(check=3)
                self.assertTrue(os.path.lexists(target))
                r = w.result()
                self.assertEqual(r["verdict"], "invalid")
                self.assertIn("after the bats leg the checkout is not the sha's tree: ancestor 1 (%s)" % target, r["invalid"])
                self.assertEqual(w.legs_called(), ["deps", PYTEST_LEG, "bats"], p.stdout + p.stderr)

    def test_sigterm_stops_the_leg_its_descendants_and_removes_tmpdir_and_the_checkout(self):
        """A5: SIGTERM during a leg whose children write into TMPDIR, one in the leg's process group and one under
        setsid. The group gets SIGTERM first (the group writer records it), the subreaper kills the setsid writer, and
        TMPDIR and the checkout are gone afterwards and stay gone."""
        if not sys.platform.startswith("linux"):
            self.skipTest("the subreaper and /proc are Linux's")
        w = self.w
        marks = os.path.join(w.tmp, "marks")
        os.makedirs(marks)
        w.ctl({"action": {"bats": "spawn"}, "marks": marks})
        proc = subprocess.Popen([sys.executable, str(SWEEP), "run", "--tree", w.tree, "--python", w.python, "--workers", "2"],
                                env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        files = [os.path.join(marks, n) for n in ("ready", "group.pid", "setsid.pid")]
        deadline = time.monotonic() + 60
        while not all(os.path.exists(f) and open(f).read() for f in files):
            if proc.poll() is not None:
                self.fail("the runner ended before the leg was ready: %s" % (proc.communicate(),))
            if time.monotonic() > deadline:
                self.fail("the leg never became ready: %s" % sorted(os.listdir(marks)))
            time.sleep(0.05)
        pids = [int(open(f).read()) for f in files[1:]]
        for pid in pids:
            self.addCleanup(_kill_quietly, pid)
        call = [c for c in w.calls() if c["leg"] == "bats"][0]
        tmpdir, checkout = call["values"]["TMPDIR"], call["root"]
        self.addCleanup(shutil.rmtree, tmpdir, True)      # only if the runner under test left it (a mutant run)
        proc.send_signal(15)
        out, err = proc.communicate(timeout=90)
        self.assertEqual(proc.returncode, 128 + 15, out + err)
        self.assertIn("stopped by signal 15", err)
        time.sleep(0.5)
        self.assertFalse(os.path.exists(tmpdir), "TMPDIR %s is gone and no writer made it again" % tmpdir)
        self.assertFalse(os.path.exists(checkout), "the checkout is gone")
        self.assertEqual([pid for pid in pids if _alive(pid)], [], "both writers are gone")
        self.assertTrue(os.path.exists(os.path.join(marks, "group.pid.term")), "the leg's process group got SIGTERM first")
        self.assertEqual(w.result()["finished"], None, "the stopped run stays unfinished")

    def test_a_stale_checkout_of_a_run_that_is_gone_is_removed_and_named(self):
        """A5: every run removes the checkouts under <state dir>/sweeps/trees whose sha's lock no run holds, whatever
        the sha, and names each; one whose run still holds its lock is kept."""
        w = self.w
        trees = self.trees()
        os.makedirs(trees)
        made = {}
        for label, sha in (("stale", "ab" * 20), ("held", "cd" * 20)):
            d = os.path.join(trees, "%s-%s" % (sha[:12], label))
            os.makedirs(os.path.join(d, "tests"))
            with open(os.path.join(d, "tests", "left.txt"), "w") as f:
                f.write("a killed run's checkout\n")
            with open(d + ".sha", "w") as f:
                f.write(sha + "\n")
            made[label] = (d, sha)
        with open(os.path.join(w.xdg, "romp", "sweeps", made["held"][1] + ".lock"), "a+") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            p = w.run(check=0)
            self.assertIn("removed a stale checkout %s (%s), left by a run that is no longer running"
                          % (made["stale"][0], made["stale"][1][:10]), p.stdout)
            self.assertFalse(os.path.exists(made["stale"][0]))
            self.assertFalse(os.path.exists(made["stale"][0] + ".sha"))
            self.assertTrue(os.path.exists(made["held"][0]), "a checkout whose run holds its lock is kept")
            self.assertEqual(sorted(os.listdir(trees)), sorted([os.path.basename(made["held"][0]), os.path.basename(made["held"][0]) + ".sha"]))

    # What the deps leg (its npm ci, whose dependencies' install scripts run) could leave for the pytest leg, each hidden
    # from `git status` in the private clone one way, or ignored by the tracked .gitignore (round 1's verify of the
    # stage 1 to 3 head: every one of these passed, with the pytest leg seeing the planted file). $R is the checkout.
    HIDDEN_PLANTS = (
        ("a self-hiding untracked .gitignore", 'mkdir -p "$R/tests/zz"; printf "*\\n" > "$R/tests/zz/.gitignore"; '
                                               'printf "x = 1\\n" > "$R/tests/zz/conftest.py"',
         ["untracked 2 (tests/zz/.gitignore, tests/zz/conftest.py)"]),
        ("the clone's info/exclude", 'printf "conftest.py\\n" >> "$R/.git/info/exclude"; printf "x = 1\\n" > "$R/conftest.py"',
         ["untracked 1 (conftest.py)", "git 1 (.git/info/exclude)"]),
        ("a commit in the clone", 'printf "x = 1\\n" > "$R/conftest.py"; G="git -C $R -c user.name=t -c user.email=t@example.invalid '
                                  '-c core.hooksPath=/dev/null"; $G add conftest.py && $G commit -q -m planted',
         ["untracked 1 (conftest.py)", "git 1 (.git/HEAD)"]),
        ("a test module the tracked .gitignore covers", 'printf "def test_x():\\n    pass\\n" > "$R/tests/test_no_personal_identifiers.py"',
         ["ignored outside vscode-extension/node_modules 1 (tests/test_no_personal_identifiers.py)"]),
        ("bytecode in a __pycache__", 'mkdir -p "$R/kernel/__pycache__"; printf "planted" > "$R/kernel/__pycache__/other.cpython-399.pyc"',
         ["ignored outside vscode-extension/node_modules 1 (kernel/__pycache__/other.cpython-399.pyc)"]),
        ("a file a tracked .gitignore's negation keeps", 'printf "x = 1\\n" > "$R/keep.local"', ["untracked 1 (keep.local)"]),
        ("the clone's .git replaced by a copy", 'cp -a "$R/.git" "$R/.git-copy" && rm -rf "$R/.git" && mv "$R/.git-copy" "$R/.git"',
         ["git 1 (.git)"]),
    )
    HIDDEN_SEED_IGNORE = "vscode-extension/node_modules\ntests/test_no_personal_identifiers.py\n__pycache__/\n*.local\n!keep.local\n"

    def deps_plants(self, script):
        """A World whose deps leg (the fake npm ci) runs `script` in the checkout ($R) before the fake records it."""
        seed = dict(SEED)
        seed[".gitignore"] = self.HIDDEN_SEED_IGNORE
        w = World(seed)
        self.addCleanup(w.close)
        real = os.path.join(w.tmp, "realbin")
        os.makedirs(real)
        os.rename(os.path.join(w.bin, "npm"), os.path.join(real, "npm"))
        with open(os.path.join(w.bin, "npm"), "w") as f:
            f.write('#!/bin/sh\nif [ "$1" = ci ]; then R=$(cd .. && pwd); %s; fi\nexec \'%s\' "$@"\n' % (script, os.path.join(real, "npm")))
        os.chmod(os.path.join(w.bin, "npm"), 0o755)
        return w

    def test_a_file_the_deps_leg_hides_from_git_status_or_the_tracked_gitignore_covers_makes_the_run_invalid(self):
        """A4 by the runner's own walk: a file the deps leg leaves counts whatever git status would say of it (a
        .gitignore the leg wrote, the clone's info/exclude, a commit in the clone excuse nothing, and a replaced .git or a
        changed HEAD or info/exclude is a change of its own), and after deps an ignored file outside
        vscode-extension/node_modules counts too (bytecode or a test module the tracked .gitignore covers, which pytest
        would load). Each run is invalid after the deps leg, and the pytest leg never runs."""
        for label, script, named in self.HIDDEN_PLANTS:
            with self.subTest(plant=label):
                w = self.deps_plants(script)
                p = w.run(check=3)
                r = w.result()
                self.assertEqual(r["verdict"], "invalid", p.stdout + p.stderr)
                self.assertIn("after the deps leg the checkout is not the sha's tree: ", r["invalid"])
                for text in named:
                    self.assertIn(text, r["invalid"])
                self.assertEqual(w.legs_called(), ["deps"], "the pytest leg did not run")

    def test_ignored_files_are_allowed_where_the_tracked_gitignore_puts_them(self):
        """The controls: node_modules left by the deps leg, and bytecode left by the pytest leg (ignored by the tracked
        .gitignore, after deps), pass."""
        w = self.deps_plants('mkdir -p "$R/vscode-extension/node_modules/pkg"; printf "x" > "$R/vscode-extension/node_modules/pkg/index.js"; '
                             'printf "x" > "$R/vscode-extension/node_modules/pkg/:colon.js"')
        real = os.path.join(w.tmp, "realbin")
        os.rename(os.path.join(w.bin, "python"), os.path.join(real, "python"))
        with open(os.path.join(w.bin, "python"), "w") as f:
            f.write('#!/bin/sh\ncase "$1" in -c) ;; *) mkdir -p kernel/__pycache__; printf x > kernel/__pycache__/other.cpython-399.pyc;; esac\n'
                    'exec \'%s\' "$@"\n' % os.path.join(real, "python"))
        os.chmod(os.path.join(w.bin, "python"), 0o755)
        p = w.run(check=0)
        self.assertEqual(w.result()["invalid"], None, p.stdout + p.stderr)

    def test_a_leg_reruns_setup_that_leaves_bytecode_refuses_the_rerun(self):
        """The setup of a --leg re-run (npm ci) is read as the deps leg is: an ignored file outside
        vscode-extension/node_modules refuses the re-run, and nothing is recorded."""
        flag = "$R/../../plant-now"
        w = self.deps_plants('[ -e "%s" ] && mkdir -p "$R/kernel/__pycache__" && printf x > "$R/kernel/__pycache__/other.cpython-399.pyc"; true' % flag)
        w.ctl({"rc": {"tools": 1}})
        w.run(check=1)
        with open(w.result_path()) as f:
            red = f.read()
        w.ctl({})
        trees = os.path.join(w.xdg, "romp", "sweeps", "trees")
        os.makedirs(trees, exist_ok=True)
        with open(os.path.join(w.xdg, "romp", "sweeps", "plant-now"), "w") as f:
            f.write("1\n")
        p = w.run("--leg", "tools", "--flake", Runner.FLAKE, check=2)
        self.assertIn("(npm ci) changed it: ignored outside vscode-extension/node_modules 1 (kernel/__pycache__/other.cpython-399.pyc)",
                      p.stderr)
        with open(w.result_path()) as f:
            self.assertEqual(f.read(), red, "a refused re-run records nothing")

    def test_a_leg_rerun_runs_npm_ci_first_and_records_it_as_setup(self):
        """A fresh checkout has no node_modules, so a --leg re-run installs them from the sha's lockfile before its leg
        and records the install as the checkout's setup; a setup that fails refuses the re-run and records nothing."""
        w = self.w
        w.ctl({"rc": {"tools": 1}})
        w.run(check=1)
        w.ctl({})
        before = len(w.calls())
        w.run("--leg", "tools", "--flake", Runner.FLAKE, check=0)
        calls = w.calls()[before:]
        self.assertEqual([c["leg"] for c in calls], ["deps", "tools"])
        self.assertEqual(calls[0]["cwd"], os.path.join(calls[1]["root"], "vscode-extension"), "in the re-run's own checkout")
        setup = w.result()["runner"]["checkout"]["setup"]
        self.assertEqual((setup["cmd"], setup["cwd"], setup["rc"]), (list(sweep.DEPS_CMD), "vscode-extension", 0))
        w2 = World()
        self.addCleanup(w2.close)
        w2.ctl({"rc": {"tools": 1}})
        w2.run(check=1)
        with open(w2.result_path()) as f:
            red = f.read()
        w2.ctl({"rc": {"deps": 1}})
        p = w2.run("--leg", "tools", "--flake", Runner.FLAKE, check=2)
        self.assertIn("the setup of the checkout of %s (npm ci) rc 1" % w2.head()[:10], p.stderr)
        with open(w2.result_path()) as f:
            self.assertEqual(f.read(), red, "a refused re-run records nothing")


# Drives run_leg in a process of its own, which becomes a subreaper as the runner does: the leg's status is taken by
# another reaper (the stand-in wraps wait_leg and reaps the leg first) before the runner reads it.
LOST_STATUS_DRIVER = r"""
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location("sweep_runner", sys.argv[1])
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)
sweep.install_stop_handlers()
real = sweep.wait_leg


def reaped_first(p):
    os.waitpid(p.pid, 0)
    return real(p)


sweep.wait_leg = reaped_first
tmp = sys.argv[2]
ctx = sweep.leg_context(tmp, sys.executable)
rec = {"owed": True, "cmd": ["sh", "-c", "exit 3"]}
sweep.run_leg(tmp, "ledger", rec, {}, ctx, tmp)
print(json.dumps({"subreaper": sweep._subreaper, "rc": rec.get("rc"), "error": rec.get("error")}))
"""

# Runs the rest of its argv (an interpreter's arguments) with SIGCHLD ignored, which exec keeps.
IGNORE_SIGCHLD = ("import os, signal, sys; signal.signal(signal.SIGCHLD, signal.SIG_IGN); "
                  "os.execv(sys.executable, [sys.executable] + sys.argv[1:])")

# The modules whose launchers the census below reads, and the launchers whose child outlives the call that starts it
# (subprocess.run, call and check_output reap theirs). pty.spawn waits for its child, but it is listed too: no child
# but the leg is started outside subprocess.run.
LAUNCHER_MODULES = ("subprocess", "os", "pty")
NOWAIT = {("subprocess", "Popen"), ("os", "popen"), ("os", "fork"), ("os", "forkpty"), ("os", "posix_spawn"),
          ("os", "posix_spawnp"), ("pty", "fork"), ("pty", "spawn")}
THREAD_MODULES = {"threading", "_thread", "concurrent", "multiprocessing", "asyncio"}


def child_launchers(source):
    """What the census reads in `source`: (the thread modules it imports, [(launcher, the innermost enclosing function,
    None at module level)]). A launcher is a NOWAIT name or an os.spawn* name reached as an attribute of its module under
    any name the module is bound to (`import subprocess as sp`), imported by name (`from os import fork as f`), a star
    import from a LAUNCHER_MODULES module, or a getattr on one of those modules."""
    import ast
    tree = ast.parse(source)
    owner = {}  # each node's innermost enclosing function: ast.walk reaches an outer function before an inner one
    for f in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for n in ast.walk(f):
            owner[id(n)] = f.name
    bound, imported, launchers = {}, set(), []  # bound: a name an import binds -> the module it names

    def is_launcher(mod, name):
        return (mod, name) in NOWAIT or (mod == "os" and name.startswith("spawn"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imported.add(a.name.split(".")[0])
                if a.asname:
                    bound[a.asname] = a.name
                else:
                    bound[a.name.split(".")[0]] = a.name.split(".")[0]
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            imported.add(mod.split(".")[0])
            for a in n.names:
                if (a.name == "*" and mod in LAUNCHER_MODULES) or is_launcher(mod, a.name) or a.name.startswith("spawn"):
                    launchers.append(("from %s import %s" % (mod, a.name), owner.get(id(n))))
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            mod = bound.get(n.value.id, n.value.id)
            if is_launcher(mod, n.attr):
                launchers.append(("%s.%s" % (mod, n.attr), owner.get(id(n))))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and n.args
              and isinstance(n.args[0], ast.Name) and bound.get(n.args[0].id, n.args[0].id) in LAUNCHER_MODULES):
            launchers.append(("getattr(%s, ...)" % bound.get(n.args[0].id, n.args[0].id), owner.get(id(n))))
    return sorted(imported & THREAD_MODULES), launchers


class ReapWhileLegRuns(unittest.TestCase):
    """Round 1, A5, and the runner's own sweep: the runner is a child subreaper, so a leg's orphaned descendants are
    reparented to it. One that exits while its leg runs is reaped then (wait_leg), not left a zombie in the leg's
    process group until the leg ends: the watchdog tests in tests/romp-node-launch.bats and tests/romp-service.bats
    list their group and failed on such a zombie. The leg's own exit status, which only Popen may read, is recorded
    exactly while orphans exit around it; the kill and reap after the leg is held by Checkout's SIGTERM test."""

    def world(self):
        if not sys.platform.startswith("linux"):
            self.skipTest("the subreaper and /proc are Linux's")
        w = World()
        self.addCleanup(w.close)
        marks = os.path.join(w.tmp, "marks")
        os.makedirs(marks)
        return w, marks

    @staticmethod
    def seen(marks, act):
        with open(os.path.join(marks, act + ".json")) as f:
            return json.load(f)

    def test_an_adopted_orphan_that_exits_during_the_leg_is_reaped_while_the_leg_runs(self):
        """The bats leg forks a child that forks a grandchild and exits; the grandchild, reparented to the runner, exits
        while the leg runs. The leg waits up to five seconds for it to be reaped, then lists the defunct processes in
        its own process group: none, and nothing was left for the kill after the leg."""
        w, marks = self.world()
        w.ctl({"action": {"bats": "orphan"}, "marks": marks})
        p = w.run(check=0)
        seen = self.seen(marks, "orphan")
        ((_i, grandchild, parent),) = seen["adopted"]
        self.assertEqual(parent, seen["runner"], "premise: the grandchild was reparented to the runner, the subreaper")
        self.assertEqual(seen["early"], {str(grandchild): None},
                         "the grandchild exited during the leg and the runner reaped it then (Z: a zombie left for the "
                         "leg's end)")
        self.assertEqual(seen["defunct_in_group"], [], "no defunct process in the leg's process group")
        self.assertEqual(w.result()["legs"]["bats"]["left_running"], 0, p.stdout + p.stderr)

    def test_the_legs_own_exit_status_is_recorded_exactly_while_orphans_exit_around_it(self):
        """Twenty grandchildren of the bats leg are reparented to the runner: ten exit while the leg runs and are reaped
        then, ten exit at the leg's own exit. The leg's status is recorded exactly for exit codes 0, 1 and 2 and for a
        death by SIGKILL: a runner that reaped the leg itself would leave Popen reading 0, or nothing."""
        for rc, sig, expected in ((0, None, 0), (1, None, 1), (2, None, 2), (0, 9, -9)):
            with self.subTest(expected=expected):
                w, marks = self.world()
                w.ctl({"action": {"bats": "orphans"}, "marks": marks, "rc": {"bats": rc},
                       "signal": {"bats": sig} if sig else {}})
                p = w.run(check=0 if expected == 0 else 1)
                seen = self.seen(marks, "orphans")
                self.assertEqual(len(seen["adopted"]), 20)
                self.assertEqual({parent for _i, _pid, parent in seen["adopted"]}, {seen["runner"]},
                                 "premise: every grandchild was reparented to the runner")
                self.assertEqual(sorted(set(seen["early"].values()), key=str), [None],
                                 "premise: the ten that exited during the leg were reaped then, so orphans were being "
                                 "reaped around the leg's exit")
                bats = w.result()["legs"]["bats"]
                self.assertEqual((bats["rc"], bats.get("error")), (expected, None), p.stdout + p.stderr)

    def test_a_leg_whose_status_another_reaper_took_is_red_with_the_reason_never_rc_0(self):
        """If anything but Popen reaped the leg, Popen would read its status as 0 (ECHILD): run_leg records no rc and
        the reason instead, so the leg is red, never a silent pass."""
        if not sys.platform.startswith("linux"):
            self.skipTest("the subreaper is Linux's")
        tmp = tempfile.mkdtemp(prefix="sweep-lost-")
        self.addCleanup(shutil.rmtree, tmp, True)
        p = subprocess.run([sys.executable, "-c", LOST_STATUS_DRIVER, str(SWEEP), tmp], text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout.splitlines()[-1]),
                         {"subreaper": True, "rc": None,
                          "error": "its exit status was lost: something other than the runner reaped it"})

    def test_the_leg_is_the_one_child_the_runner_waits_for_while_a_leg_runs(self):
        """wait_leg reaps every child but the leg while a leg runs. That is right only while the leg is the one child
        the runner will wait for: the runner has no thread, and run_leg's Popen is its one launcher that returns before
        its child is reaped. A new such launcher, or a thread (whose subprocess.run child wait_leg could reap, leaving
        its status read as 0), makes this red: wait_leg must then leave that child alone."""
        threads, launchers = child_launchers(SWEEP.read_text())
        self.assertEqual(threads, [], "the runner has one thread")
        self.assertEqual(launchers, [("subprocess.Popen", "run_leg")],
                         "the one launcher whose child outlives the call is run_leg's Popen, the leg wait_leg waits for")

    def test_the_census_reads_a_launcher_however_it_is_spelled(self):
        """The census above is only as good as the spellings it reads: a module bound under another name, pty's forks,
        a star import and a getattr each start a child the census must see, and subprocess.run must stay unflagged."""
        cases = {
            "import subprocess as _sp\ndef f():\n    _sp.Popen(['true'])\n": [("subprocess.Popen", "f")],
            "import os as o\ndef f():\n    o.fork()\n": [("os.fork", "f")],
            "import pty\ndef f():\n    pty.fork()\n": [("pty.fork", "f")],
            "import pty\ndef f():\n    pty.spawn(['true'])\n": [("pty.spawn", "f")],
            "from subprocess import *\n": [("from subprocess import *", None)],
            "from os import *\n": [("from os import *", None)],
            "from pty import *\n": [("from pty import *", None)],
            "from os import fork as fk\n": [("from os import fork", None)],
            "import subprocess\ndef f():\n    getattr(subprocess, 'Popen')(['true'])\n": [("getattr(subprocess, ...)", "f")],
            "import os\ndef f():\n    os.spawnlp(os.P_NOWAIT, 'true', 'true')\n": [("os.spawnlp", "f")],
            "import subprocess\ndef f():\n    subprocess.run(['true'])\n": [],
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(child_launchers(source), ([], expected))
        for source in ("import threading as t\n", "from concurrent.futures import ThreadPoolExecutor\n", "import asyncio\n"):
            with self.subTest(source=source):
                self.assertEqual(len(child_launchers(source)[0]), 1)

    def test_a_runner_started_with_sigchld_ignored_records_the_legs_status_and_is_not_held_by_its_daemon(self):
        """An ignored SIGCHLD survives exec. The runner sets the default action first, so a leg that exits 3 and leaves a
        daemon under setsid is recorded as rc 3 at once, and the daemon is killed after the leg. Under an inherited
        ignore, the kernel would reap every child itself: the leg's status would read 0 (a silent pass), or the runner
        would wait in wait_leg until the daemon exited and then record the status as lost."""
        w, marks = self.world()
        probe = subprocess.run([sys.executable, "-c", IGNORE_SIGCHLD, "-c",
                                "import signal; print(signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN)"],
                               text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        self.assertEqual(probe.stdout.strip(), "True", "premise: the stand-in parent's ignore reaches the runner " + probe.stderr)
        daemon = 60
        w.ctl({"action": {"bats": "daemon"}, "rc": {"bats": 3}, "marks": marks, "daemon_seconds": daemon})
        start = time.monotonic()
        p = subprocess.run([sys.executable, "-c", IGNORE_SIGCHLD, str(SWEEP), "run", "--tree", w.tree, "--python", w.python,
                            "--workers", "2"], env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, timeout=daemon * 2)
        wall = time.monotonic() - start
        bats = w.result()["legs"]["bats"]
        self.assertEqual((bats["rc"], bats.get("error")), (3, None), p.stdout + p.stderr)
        self.assertEqual(bats["left_running"], 1, "the daemon was still running when the leg ended, and was killed")
        self.assertLess(wall, daemon * 0.75, "the runner did not wait for the leg's daemon to exit")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)

    def test_the_runner_blocks_while_it_waits_for_a_leg(self):
        """wait_leg blocks until some child exits; it never polls. The leg sleeps two seconds with an adopted grandchild
        running and reads the runner's CPU time before and after: a polling runner spins through those two seconds."""
        w, marks = self.world()
        w.ctl({"action": {"bats": "idle"}, "marks": marks})
        p = w.run(check=0)
        seen = self.seen(marks, "idle")
        self.assertEqual(seen["adopted_parent"], seen["runner"], "premise: the grandchild was reparented to the runner")
        self.assertLess(seen["cpu"], 0.5, "the runner used %.2f s of CPU in the leg's two idle seconds" % seen["cpu"])
        self.assertEqual(w.result()["legs"]["bats"]["rc"], 0, p.stdout + p.stderr)


# Each road sets one way a batcher's repository, git configuration or environment could make a checkout differ from
# the sha, in the batcher's own tree; under the private clone every road checks out exact.
ROADS = (
    ("skip-worktree and an edit", lambda w, env: (w.git("update-index", "--skip-worktree", "README.md"),
                                                 w.write({"README.md": "hidden edit\n"}))),
    ("assume-unchanged and an edit", lambda w, env: (w.git("update-index", "--assume-unchanged", "kernel/other.py"),
                                                    w.write({"kernel/other.py": "OTHER = 2\n"}))),
    ("a non-cone sparse checkout", lambda w, env: w.git("sparse-checkout", "set", "--no-cone", "/*", "!/tools/")),
    ("a conftest.py hidden by info/exclude", lambda w, env: (_append(os.path.join(w.tree, ".git", "info", "exclude"), "conftest.py\n"),
                                                           w.write({"conftest.py": "collect_ignore = ['tests']\n"}))),
    ("a smudge filter from info/attributes", lambda w, env: (_append(os.path.join(w.tree, ".git", "info", "attributes"), "*.md filter=road\n"),
                                                            w.git("config", "filter.road.smudge", "sed s/notes/SMUDGED/"),
                                                            w.git("config", "filter.road.clean", "cat"), _recheckout(w, "README.md"))),
    ("core.autocrlf and core.eol", lambda w, env: (w.git("config", "core.autocrlf", "true"), w.git("config", "core.eol", "crlf"),
                                                  _recheckout(w, "README.md"))),
    ("a post-checkout hook in the repository", lambda w, env: _hook(os.path.join(w.tree, ".git", "hooks"))),
    ("GIT_CONFIG_* in the runner's environment", lambda w, env: env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.autocrlf",
                                                                          GIT_CONFIG_VALUE_0="true")),
    ("GIT_CONFIG_PARAMETERS in the runner's environment", lambda w, env: env.update(GIT_CONFIG_PARAMETERS="'core.autocrlf'='true'")),
    ("refs/replace of the head by its parent", lambda w, env: w.git("replace", "HEAD", "HEAD~1")),
    ("core.symlinks=false", lambda w, env: (w.git("config", "core.symlinks", "false"), _recheckout(w, "bin/kernel-link"))),
    ("a core.fsmonitor hook that reports nothing", lambda w, env: (_script(os.path.join(w.tmp, "fsmonitor"), "#!/bin/sh\nexit 0\n"),
                                                                 w.git("config", "core.fsmonitor", os.path.join(w.tmp, "fsmonitor")),
                                                                 w.write({"README.md": "unreported edit\n"}))),
    ("core.fileMode=false hiding an exec bit", lambda w, env: (w.git("config", "core.fileMode", "false"),
                                                             os.chmod(os.path.join(w.tree, "README.md"), 0o755))),
    ("a file hidden by core.excludesFile", lambda w, env: (_append(os.path.join(w.tmp, "excludes"), "conftest.py\n"),
                                                         w.git("config", "core.excludesFile", os.path.join(w.tmp, "excludes")),
                                                         w.write({"conftest.py": "collect_ignore = ['tests']\n"}))),
    ("a self-hiding untracked .gitignore", lambda w, env: w.write({"tests/.gitignore": "*\n", "tests/conftest.py": "x = 1\n"})),
    ("a global config with core.autocrlf and a hooksPath", lambda w, env: env.update(GIT_CONFIG_GLOBAL=_global_config(w))),
    ("a global config through HOME", lambda w, env: (env.pop("GIT_CONFIG_GLOBAL", None), env.update(HOME=_home_config(w)))),
    ("per-user git attributes and excludes under XDG_CONFIG_HOME", lambda w, env: env.update(XDG_CONFIG_HOME=_xdg_config(w))),
)


def _append(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(text)


def _script(path, text):
    _append(path, text)
    os.chmod(path, 0o755)


def _recheckout(w, rel):
    os.remove(os.path.join(w.tree, rel))
    w.git("checkout", "--", rel)


def _hook(hooks):
    _script(os.path.join(hooks, "post-checkout"), "#!/bin/sh\necho hooked > hooked.txt\n")


def _global_config(w):
    hooks = os.path.join(w.tmp, "global-hooks")
    _hook(hooks)
    path = os.path.join(w.tmp, "global.gitconfig")
    _append(path, "[core]\n\tautocrlf = true\n\thooksPath = %s\n" % hooks)
    return path


def _home_config(w):
    home = os.path.join(w.tmp, "road-home")
    _hook(os.path.join(home, "hooks"))
    _append(os.path.join(home, ".gitconfig"), "[core]\n\tautocrlf = true\n\thooksPath = %s\n" % os.path.join(home, "hooks"))
    return home


def _xdg_config(w):
    d = os.path.join(w.tmp, "road-xdg")
    _append(os.path.join(d, "git", "attributes"), "* text eol=crlf\n")
    _append(os.path.join(d, "git", "ignore"), "conftest.py\n")
    return d


class CheckoutRoads(unittest.TestCase):
    """Round 1, Class A's roads: each sets one way the batcher's repository, git configuration or environment could
    make what the legs read differ from the sha, and each must check out EXACT: the fake legs record every file they
    can see in their checkout, and the pin compares that with the sha's tree read from git (never "exact or refused":
    a road moved from exact to refused would pass an either-or pin)."""

    def test_every_road_checks_out_the_shas_tree(self):
        seed = dict(SEED)
        seed["bin/run.sh"] = "#!/bin/sh\nexit 0\n"
        for label, road in ROADS:
            with self.subTest(road=label):
                w = World(seed)
                self.addCleanup(w.close)
                os.chmod(os.path.join(w.tree, "bin", "run.sh"), 0o755)
                os.symlink("../kernel/kernel.py", os.path.join(w.tree, "bin", "kernel-link"))
                w.change({"kernel/other.py": "OTHER = 3\n"})
                sha = w.head()
                expected = expected_tree(w, sha)
                env = dict(w.env)
                road(w, env)
                p = w.run(env=env)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                calls = w.calls()
                self.assertEqual(len(calls), len(sweep.LEGS))
                for c in calls:
                    self.assertEqual(c["tree"], expected, "%s did not see the sha's tree" % c["leg"])
                self.assertEqual(w.data()["sha"], sha)



# The keys of leg_context, with placeholder values: leg_sets' NAMES do not depend on them.
CTX_SHAPE = {k: "/nonexistent/" + k for k in ("tmpdir", "home", "xdg", "npm_cache", "browsers", "path", "pytest_path")}


class LegEnvironment(_Base):
    """Round 1, Class B: the leg environment is an allowlist. A leg inherits LEG_ALLOW's names and nothing else; the
    runner sets the rest (a built PATH, a private HOME and state root, the shared caches, CI's fixed values, the box
    floor's dead ports, the leg's CI switches). The wrap runs with the runner's environment and the allowlist applies
    after it; a log header names each variable without its value; the result records the allowlist's hash, which a
    reader compares with its own."""

    def all_legs_world(self):
        """A head on a branch of its own; every head owes every leg, so all nine legs run."""
        self.w.change({"kernel/kernel.py": "VERSION = 2\n"})
        return self.w

    def batcher_home(self):
        home = os.path.join(self.w.tmp, "batcher-home")
        os.makedirs(home)
        return home

    def test_no_credential_session_or_narrowing_name_reaches_any_leg(self):
        w = self.all_legs_world()
        marker = "-".join(("sweep", "mark"))
        names = ("OPENAI_API_KEY", "HF_TOKEN", "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY", "SWEEP_DB_PASSWORD", "PGPASSWORD",
                 "GITHUB_PAT", "NPM_CONFIG__AUTH", "OP_SESSION_sweep", "SSH_AUTH_SOCK", "AWS_SESSION_TOKEN", "ROMP_SID",
                 "CLAUDE_CODE_SESSION_ID", "GIT_SWEEP_MARK")
        planted = {n: "%s-%d" % (marker, i) for i, n in enumerate(names)}
        narrowing = {"PYTEST_ADDOPTS": "-k nothing_at_all", "PYTEST_PLUGINS": "no_such_plugin", "PYTEST_CURRENT_TEST": "t",
                     "PYTHONPATH": os.path.join(w.tmp, "shadow"), "NODE_OPTIONS": "--no-such-flag"}
        w.ctl({"marker": marker})
        w.run(env=dict(w.env, **planted, **narrowing), check=0)
        calls = w.calls()
        self.assertEqual(sorted(c["leg"] for c in calls), sorted(sweep.LEGS), "all nine legs ran")
        for c in calls:
            with self.subTest(leg=c["leg"]):
                self.assertEqual(c["marked"], [], "a planted value reached the leg")
                allowed = set(sweep.LEG_ALLOW) | set(sweep.leg_sets(c["leg"], CTX_SHAPE))
                self.assertEqual(sorted(set(c["names"]) - allowed), [], "only allowlisted and runner-set names reach a leg")
                for n in sorted(set(narrowing) - {"NODE_OPTIONS"}):
                    self.assertNotIn(n, c["names"])
                self.assertNotEqual(c["values"].get("NODE_OPTIONS"), narrowing["NODE_OPTIONS"])
                self.assertEqual("NODE_OPTIONS" in c["names"], c["leg"] == "npm-test", "only npm test gets the heap cap")
        r = w.result()
        self.assertIn("OPENAI_API_KEY", r["legs"]["deps"]["env_dropped"])
        self.assertIn("PYTEST_ADDOPTS", r["legs"]["pytest"]["env_dropped"])
        self.assertNotIn(marker, json.dumps(r), "the result records names, never an inherited value")

    def test_every_leg_carries_the_floor_and_the_fixed_values_whatever_the_runners(self):
        w = self.all_legs_world()
        # a directory ahead of the tools on the batcher's PATH, holding what a leg never needs (a live deployment's bin)
        decoy = os.path.join(w.tmp, "live-bin")
        os.makedirs(decoy)
        for name in ("romp", "vault-secret"):
            with open(os.path.join(decoy, name), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(os.path.join(decoy, name), 0o755)
        env = dict(w.env, PATH=decoy + os.pathsep + w.env["PATH"])
        env.update(HOME=self.batcher_home(), SHELL="/usr/bin/zsh", LANG="fr_FR.UTF-8", LC_ALL="fr_FR.UTF-8", CI="",
                   ROMP_MANAGER_PORT="29801", ROMP_KERNEL_PORT="29855", ROMP_SERVE_PORT="29855", ROMP_POSTAL_PORT="25302",
                   BATS_TEST_TIMEOUT="5", ROMP_GITLEAKS_REQUIRE="0", ROMP_SERVED_TESTS_ENGINES="chromium,firefox",
                   NPM_CONFIG_GLOBALCONFIG=os.path.join(w.tmp, "npmrc"), npm_config_globalconfig=os.path.join(w.tmp, "npmrc"),
                   GIT_CONFIG_SYSTEM=os.path.join(w.tmp, "gitconfig"))
        w.run(env=env, check=0)
        calls = w.calls()
        self.assertEqual(len(calls), len(sweep.LEGS))
        for c in calls:
            with self.subTest(leg=c["leg"]):
                v = c["values"]
                tmp = v["TMPDIR"]
                self.assertEqual(v["XDG_STATE_HOME"], os.path.join(tmp, "xdg-state"), "the state root is private")
                self.assertEqual(c["state"], {"session-hosts": "off\n"}, "session hosts are off in the private state root")
                self.assertEqual(v["HOME"], os.path.join(tmp, "home"), "HOME is private")
                self.assertEqual({p: v.get(p) for p in sweep.PORT_FLOOR}, dict.fromkeys(sweep.PORT_FLOOR, "1"))
                self.assertIn("ROMP_POSTAL_PORT", sweep.PORT_FLOOR, "the postal bus falls back to the live bus's port")
                self.assertEqual((v["CI"], v["SHELL"], v["LANG"]), ("true", "/bin/bash", "C.UTF-8"))
                self.assertNotIn("LC_ALL", c["names"])
                # npm's global config (<prefix>/etc/npmrc, beside a node the batcher installed) and git's system config
                # live outside HOME, so the private HOME does not replace them: both are off, whatever the runner names
                self.assertEqual((v.get("npm_config_globalconfig"), v.get("GIT_CONFIG_NOSYSTEM")), (os.devnull, "1"))
                self.assertNotIn("NPM_CONFIG_GLOBALCONFIG", c["names"])
                self.assertNotIn("GIT_CONFIG_SYSTEM", c["names"])
                path = v["PATH"].split(os.pathsep)
                # --python's directory leads every leg's PATH but the pytest leg's, which leads with the directory of
                # the venv the runner built from it (its bin holds pytest's interpreter; --python's does not)
                lead = os.path.dirname(w.result()["runner"]["sdk"]["python"]) if c["leg"] == PYTEST_LEG else w.bin
                self.assertEqual(path[0], lead, "the leg's interpreter's directory leads PATH")
                tool_dirs = {os.path.dirname(shutil.which(t, path=env["PATH"]) or "") for t in sweep.PATH_TOOLS} - {""}
                self.assertEqual(sorted(set(path) - {lead} - tool_dirs - set(sweep.PATH_FLOOR)), [])
                self.assertTrue(set(sweep.PATH_FLOOR) <= set(path), path)
                self.assertNotIn(decoy, path, "the batcher's PATH is not passed on")
                self.assertEqual(len(path), len(set(path)), "each directory once")
        by_leg = {c["leg"]: c["values"] for c in calls}
        self.assertEqual({k: by_leg["bats"].get(k) for k in ("BATS_TEST_TIMEOUT", "ROMP_GITLEAKS_REQUIRE")},
                         {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"})
        self.assertEqual({k: by_leg[PYTEST_LEG].get(k) for k in ("ROMP_SERVED_TESTS_REQUIRE", "ROMP_SERVED_TESTS_ENGINES")},
                         {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"})
        self.assertEqual(by_leg["npm-test"]["NODE_OPTIONS"], "--max-old-space-size=8192")
        rec = w.result()["legs"]["bats"]
        self.assertEqual({k: rec["env_set"][k] for k in ("BATS_TEST_TIMEOUT", "ROMP_GITLEAKS_REQUIRE")},
                         {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"}, "the set values are recorded")

    def test_the_batchers_home_reaches_no_leg(self):
        """An .npmrc (its node-options reach every npm-run leg as NODE_OPTIONS), a git config (its hooksPath runs in bats
        fixture repos), a .zshenv, and the live deployment's SDK venv (tests/test_host_transport.py puts it on sys.path)
        in the batcher's HOME: no leg sees any of them. The shared caches still resolve from the batcher's HOME."""
        w = self.all_legs_world()
        home = self.batcher_home()
        files = {".npmrc": "node-options=--require /nonexistent/hook.js\n", ".gitconfig": "[core]\n\thooksPath = /nonexistent\n",
                 ".zshenv": "export SWEEP_FROM_ZSHENV=1\n",
                 ".local/state/romp/sdkvenv/lib/python3.99/site-packages/claude_agent_sdk/__init__.py": "FAKE = 1\n"}
        for rel, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(home, rel)), exist_ok=True)
            with open(os.path.join(home, rel), "w") as f:
                f.write(text)
        env = dict(w.env, HOME=home)
        for k in ("npm_config_cache", "NPM_CONFIG_CACHE", "PLAYWRIGHT_BROWSERS_PATH", "XDG_CACHE_HOME"):
            env.pop(k, None)
        w.run(env=env, check=0)
        for c in w.calls():
            with self.subTest(leg=c["leg"]):
                self.assertEqual(c["home_files"], [])
                self.assertEqual(c["sdk"], [], "the live deployment's SDK venv is not in the leg's HOME")
                self.assertNotEqual(c["values"]["HOME"], home)
                self.assertEqual(c["values"]["npm_config_cache"], os.path.join(home, ".npm"))
                if sys.platform != "darwin":
                    self.assertEqual(c["values"]["PLAYWRIGHT_BROWSERS_PATH"], os.path.join(home, ".cache", "ms-playwright"))
        runner = w.result()["runner"]
        self.assertIs(runner.get("home_empty"), True, "the result records whether the private HOME was empty at the end")
        self.assertEqual(runner["home_left"], [])

    def test_a_file_a_leg_leaves_in_home_is_recorded(self):
        w = self.w
        w.ctl({"action": {"manager": "home"}})
        w.run(check=0)
        runner = w.result()["runner"]
        self.assertIs(runner.get("home_empty"), False, "the result records whether the private HOME was empty at the end")
        self.assertEqual(runner["home_left"], [".leftover"])

    def test_no_leg_log_header_holds_a_value_of_the_leg_environment(self):
        w = self.all_legs_world()
        user = "-".join(("sweep", "user", "mark"))
        home = self.batcher_home()
        w.run(env=dict(w.env, USER=user, LOGNAME=user, HOME=home), check=0)
        r = w.result()
        for c in w.calls():
            with self.subTest(leg=c["leg"]):
                self.assertEqual(c["values"]["USER"], user, "USER passes to the leg")
                with open(r["legs"][c["leg"]]["log"]) as f:
                    header = "".join(f.readline() for _ in range(3))
                for value in (c["values"]["PATH"], c["values"]["HOME"], c["values"]["TMPDIR"], user, home):
                    self.assertNotIn(value, header)
                self.assertTrue(header.startswith("# leg: %s\n# cwd: " % c["leg"]), header)
                self.assertIn("PATH=... ", header, "each pair is shown by its name")

    def test_the_recorded_hash_is_the_readers_constant_across_runs(self):
        w = self.w
        w.run(check=0)
        first = w.result()
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        second = w.result()
        self.assertNotEqual(first["runner"]["tmpdir"], second["runner"]["tmpdir"], "two runs, two TMPDIR tails")
        for r in (first, second):
            got = r["runner"].get("leg_env")
            self.assertIsNotNone(got, "the result records the leg environment's allowlist and hash")
            self.assertEqual(got, {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()})

    def test_the_tool_versions_are_recorded_and_run_no_leg(self):
        w = self.w
        w.run(check=0)
        tools = w.result()["runner"].get("tools")
        self.assertIsNotNone(tools, "the result records the tool versions the legs found")
        self.assertEqual(sorted(tools), sorted(t for t, _arg in sweep.TOOL_VERSION_ARGS))
        for name in ("node", "npm", "bats"):
            self.assertEqual(tools[name], {"path": os.path.join(w.bin, name), "version": name + " 0.0.0-fake"})
        self.assertTrue(tools["git"]["version"].startswith("git version"), tools["git"])
        self.assertEqual(w.legs_called(), list(sweep.LEGS))

    def test_a_wrap_sees_the_runners_environment_and_its_leg_does_not(self):
        w = self.w
        env = dict(w.env, XDG_RUNTIME_DIR=os.path.join(w.tmp, "runtime"))
        w.run("--wrap", "*=%s all" % w.wrapper, env=env, check=0)
        wraps = w.wraps()
        self.assertEqual([c["leg"] for c in wraps], w.legs_called())
        for c in wraps:
            self.assertEqual(c["values"].get("XDG_RUNTIME_DIR"), env["XDG_RUNTIME_DIR"], "the wrap reaches the user bus")
        for c in w.calls():
            self.assertNotIn("XDG_RUNTIME_DIR", c["names"])


class LegEnvironmentReader(unittest.TestCase):
    def test_the_floor_names_every_port_variable_the_tree_reads(self):
        """A census over the tree: every ROMP_*_PORT name it reads is in PORT_FLOOR, or in PORT_DEFAULTS with a default
        that is. A new port variable reds this until the floor names it. It reads the tree with git grep and fails when
        it cannot, rather than passing over an empty population."""
        p = subprocess.run(["git", "-C", str(ROOT), "grep", "-ohE", r"ROMP_[A-Z_]*PORT\b"], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(p.returncode, 0, "the census could not read the tree: %s" % p.stderr)
        names = sorted(set(p.stdout.split()))
        self.assertIn("ROMP_KERNEL_PORT", names, "the census found no port variable at all")
        for n in names:
            self.assertTrue(n in sweep.PORT_FLOOR or sweep.PORT_DEFAULTS.get(n) in sweep.PORT_FLOOR,
                            "%s is read in the tree and the sweep's box floor neither sets it nor defaults it to a floored port" % n)
        # The default the floor relies on is the tree's: the remote kernel port falls back to the kernel's own.
        src = (ROOT / "kernel" / "kernel.py").read_text(encoding="utf-8")
        self.assertRegex(src, r'(?m)^PORT = int\(os\.environ\.get\("ROMP_KERNEL_PORT", ')
        self.assertRegex(src, r'os\.environ\.get\("ROMP_REMOTE_KERNEL_PORT", str\(PORT\)\)')


class PytestEnvironment(_Base):
    """Round 1's SDK ruling (2026-09-28): the pytest leg runs in a venv the runner owns, built from --python with the
    install steps the swept sha's ci.yml holds (pytest and its plugins, cryptography, the Claude Agent SDK at its pin)
    and cached under <state dir>/sweeps/sdk/<key>, keyed by the pin, --python's path and version and the install
    commands. The pin is read from ci.yml, never restated; the result records the key and the SDK's version; the leg's
    private HOME keeps a live deployment's SDK venv out; a build that fails is a refusal, nothing recorded. FAKE makes
    the venv, records what pip installs in it, and answers the probe and the import check from that record."""

    FLAKE = "tests/test_a.py::test_a (a known flake, recorded in the notes)"

    def sdk(self, sha=None):
        return self.w.result(sha)["runner"]["sdk"]

    def pytest_calls(self):
        return [c for c in self.w.calls() if c["leg"] == PYTEST_LEG]

    def test_the_pin_is_read_from_ci_yml_and_another_pin_is_another_key_and_version(self):
        w = self.w
        w.run(check=0)
        first = self.sdk()
        self.assertEqual((first["dist"], first["pin"], first["version"]), ("claude-agent-sdk", SEED_PIN, SEED_PIN),
                         "the pin ci.yml's SDK step reads from kernel/session_host.py")
        # the pin moves where ci.yml reads it: a new key, a new venv beside the old one, the new version recorded
        w.change({"kernel/session_host.py": 'SDK_TESTED_VERSION = "1.2.4"\n'})
        w.run(check=0)
        second = self.sdk()
        self.assertEqual((second["pin"], second["version"]), ("1.2.4", "1.2.4"))
        self.assertNotEqual(second["key"], first["key"], "a pin change is a new key")
        # a ci.yml whose SDK step names its pin in the install line itself
        w.change({".github/workflows/ci.yml": SEED_CI.replace('"claude-agent-sdk==$pin"', "claude-agent-sdk==2.0.0")})
        w.run(check=0)
        third = self.sdk()
        self.assertEqual((third["pin"], third["version"]), ("2.0.0", "2.0.0"))
        self.assertEqual(len({first["key"], second["key"], third["key"]}), 3, "each pin its own key")
        self.assertEqual(sorted(n for n in os.listdir(w.sdk_root()) if os.path.isdir(os.path.join(w.sdk_root(), n))),
                         sorted([first["key"], second["key"], third["key"]]), "each key's venv stays in the cache")
        self.assertEqual(self.pytest_calls()[-1]["venv_installs"]["claude-agent-sdk"], "2.0.0")

    def test_the_pytest_leg_runs_in_the_venv_where_the_sdk_imports(self):
        w = self.w
        w.run(check=0)
        call = self.pytest_calls()[0]
        self.assertEqual((call["venv_installs"] or {}).get("claude-agent-sdk"), SEED_PIN,
                         "the pytest leg runs in a venv holding the SDK at ci.yml's pin")
        sdk = self.sdk()
        self.assertEqual(sdk["python"], os.path.join(w.sdk_root(), sdk["key"], "bin", "python"))
        self.assertEqual(call["exe"], sdk["python"], "the pytest leg ran as the venv's python")
        self.assertEqual(w.result()["legs"][PYTEST_LEG]["cmd"][0], sdk["python"])
        self.assertEqual(call["venv_installs"], {"pip": "9.9.9", "pytest": "9.9.9", "pytest-timeout": "9.9.9",
                                                 "pytest-xdist": "9.9.9", "cryptography": "9.9.9",
                                                 "claude-agent-sdk": SEED_PIN},
                         "what ci.yml's three install steps install, and nothing else")
        self.assertEqual(call["values"]["PATH"].split(os.pathsep)[0], os.path.dirname(sdk["python"]),
                         "the venv's bin leads the pytest leg's PATH")
        self.assertEqual(call["values"].get("ROMP_SDK_REQUIRE"), "1",
                         "the Run pytest step's switch: the pin test fails where the SDK does not import")
        self.assertEqual([(s["exe"], s["module"]) for s in w.setups() if s["kind"] == "import"],
                         [(sdk["python"], "claude_agent_sdk")], "the SDK step's own import check ran in the venv")
        self.assertEqual(sorted(call["tmp"]), ["home", "xdg-state"], "the build's own directory under TMPDIR is gone before the legs")
        self.assertTrue(all(s["home"].startswith(os.path.dirname(call["values"]["HOME"]) + os.sep + "sdk-") for s in w.setups()),
                        "the build ran under a private HOME of its own, in its directory under the run's TMPDIR")
        for c in w.calls():
            if c["leg"] != PYTEST_LEG:
                self.assertIsNone(c["venv_installs"], "only the pytest leg runs in the venv (%s)" % c["leg"])
                self.assertNotIn("ROMP_SDK_REQUIRE", c["names"], c["leg"])

    def test_the_result_records_the_sdk_version_and_the_key(self):
        w = self.w
        w.run(check=0)
        runner = w.result()["runner"]
        self.assertIn("sdk", runner, "the result records the pytest leg's environment")
        sdk = runner["sdk"]
        self.assertEqual(sdk["version"], SEED_PIN, "the SDK's version, as the venv reports it")
        self.assertRegex(sdk["key"], r"^[0-9a-f]{20}$")
        self.assertEqual(sdk["path"], os.path.join(w.sdk_root(), sdk["key"]))
        self.assertEqual((sdk["built"], sdk["base_python"], sdk["base_version"]), (True, w.python, "3.99.0"))
        self.assertEqual(sdk["log"], sdk["path"] + ".log")
        with open(os.path.join(sdk["path"], sweep.SDK_MARKER)) as f:
            marker = json.load(f)
        self.assertEqual((marker["key"], marker["pin"], marker["version"]), (sdk["key"], SEED_PIN, SEED_PIN))
        self.assertEqual(runner["python_version"], "3.99.0")

    def test_a_venv_whose_sdk_reports_another_version_is_refused(self):
        """The recorded version is the venv's own report, not the pin copied: a venv whose SDK reports another
        version after the install steps is refused, nothing recorded."""
        w = self.w
        w.ctl({"sdk_reports": "0.0.1"})
        p = w.run(check=2)
        self.assertIn("after the install steps the venv's claude-agent-sdk is 0.0.1, not ci.yml's pin %s" % SEED_PIN, p.stderr)
        self.assertFalse(os.path.exists(w.result_path()))

    def test_a_live_sdk_venv_on_the_batchers_machine_reaches_no_leg(self):
        """A live deployment's SDK venv under the batcher's HOME (tests/test_host_transport.py puts
        ~/.local/state/romp/sdkvenv on sys.path at import), named on PYTHONPATH and by ROMP_SDK_SITE as well: the pytest
        leg runs in the runner's venv at ci.yml's pin under a private HOME that holds no such venv, and neither variable
        reaches the leg or any command of the build."""
        w = self.w
        home = os.path.join(w.tmp, "batcher-home")
        site = os.path.join(home, ".local", "state", "romp", "sdkvenv", "lib", "python3.99", "site-packages")
        for rel, text in (("claude_agent_sdk/__init__.py", "__version__ = '0.0.9'\n"),
                          ("claude_agent_sdk-0.0.9.dist-info/METADATA", "Name: claude-agent-sdk\nVersion: 0.0.9\n")):
            os.makedirs(os.path.dirname(os.path.join(site, rel)), exist_ok=True)
            with open(os.path.join(site, rel), "w") as f:
                f.write(text)
        w.run(env=dict(w.env, HOME=home, PYTHONPATH=site, ROMP_SDK_SITE=site), check=0)
        call = self.pytest_calls()[0]
        self.assertEqual((call["venv_installs"] or {}).get("claude-agent-sdk"), SEED_PIN,
                         "the leg's SDK is the runner's venv's, at ci.yml's pin, not the live one")
        self.assertEqual(call["exe"], self.sdk()["python"])
        self.assertEqual(call["sdk"], [], "no SDK venv under the leg's HOME")
        self.assertNotEqual(call["values"]["HOME"], home)
        for name in ("PYTHONPATH", "ROMP_SDK_SITE"):
            self.assertNotIn(name, call["names"])
        self.assertTrue(w.setups(), "the build ran")
        for s in w.setups():
            with self.subTest(setup=s["kind"]):
                self.assertNotIn("PYTHONPATH", s["names"], "the build and its probes see no PYTHONPATH")
                self.assertNotIn("ROMP_SDK_SITE", s["names"])
                self.assertNotEqual(s["home"], home, "the build runs under a private HOME")

    def test_a_failed_build_is_refused_records_nothing_and_leaves_no_venv(self):
        w = self.w
        cases = (({"pip_fail": ["claude-agent-sdk==%s" % SEED_PIN]},
                  "the step 'Install the Claude Agent SDK', `-m pip install claude-agent-sdk==%s`, exited 1; log " % SEED_PIN),
                 ({"venv_rc": 3}, "the step 'venv', `-m venv %s" % w.sdk_root()))
        for ctl, text in cases:
            with self.subTest(ctl=ctl):
                w.ctl(ctl)
                before = len(w.calls())
                p = w.run(check=2)
                self.assertIn(text, p.stderr)
                self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
                self.assertEqual(w.legs_called()[before:], [], "no leg ran")
                left = os.listdir(w.sdk_root())
                self.assertEqual(sorted(n for n in left if not n.endswith((".log", ".lock"))), [], "the venv is removed")
                with open(os.path.join(w.sdk_root(), [n for n in left if n.endswith(".log")][0])) as f:
                    self.assertIn("# rc: ", f.read(), "the build's log keeps what failed")
                self.assertEqual(os.listdir(os.path.join(w.xdg, "romp", "sweeps", "trees")), [], "the checkout is removed")
        w.ctl({})
        w.run(check=0)
        self.assertIs(self.sdk()["built"], True, "the next run builds it again")

    def test_a_finished_build_is_reused_and_an_unfinished_one_built_again(self):
        w = self.w
        w.run(check=0)
        first = self.sdk()
        builds = [s for s in w.setups() if s["kind"] in ("venv", "pip")]
        self.assertEqual([s["kind"] for s in builds], ["venv", "pip", "pip", "pip"])
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        second = self.sdk()
        self.assertEqual((second["key"], second["built"], second["version"]), (first["key"], False, SEED_PIN),
                         "the same pin and interpreter: the same key, reused")
        self.assertEqual(len([s for s in w.setups() if s["kind"] in ("venv", "pip")]), len(builds), "no second build")
        self.assertEqual(self.pytest_calls()[-1]["exe"], first["python"])
        # a build that died left no marker: the next run removes that venv and builds it again
        os.remove(os.path.join(first["path"], sweep.SDK_MARKER))
        w.change({"README.md": "# notes-api, a third time\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (no finished build)" % first["key"], p.stdout)
        self.assertIs(self.sdk()["built"], True)

    def test_an_interpreter_without_ensurepip_gets_pip_from_get_pip(self):
        w = self.w
        getpip = os.path.join(w.tmp, "get-pip.py")
        with open(getpip, "w") as f:
            f.write("# a stand-in for PyPA's get-pip.py\n")
        w.ctl({"ensurepip": False})
        w.run(env=dict(w.env, ROMP_GET_PIP_URL="file://" + getpip), check=0)
        venv = [s for s in w.setups() if s["kind"] == "venv"]
        self.assertEqual(len(venv), 1)
        self.assertIn("--without-pip", venv[0]["argv"])
        self.assertEqual([s["kind"] for s in w.setups() if s["kind"] in ("get-pip", "pip")], ["get-pip", "pip", "pip", "pip"])
        self.assertEqual(self.sdk()["version"], SEED_PIN)

    def test_a_ci_yml_the_runner_cannot_read_is_refused_by_name(self):
        w = self.w
        cases = (
            ("no SDK step", SEED_CI.replace(SEED_SDK_STEP, ""), SEED_HOST,
             "has no step 'Install the Claude Agent SDK' in its python job"),
            ("a line it does not read", SEED_CI.replace('python -c "import claude_agent_sdk"', "curl -fsSL https://example.invalid | sh"),
             SEED_HOST, "the line 'curl -fsSL https://example.invalid | sh' is not one the runner reads"),
            ("a pin the step's own check refuses", SEED_CI, 'SDK_TESTED_VERSION = "1.2"\n',
             "reads '1.2' into pin, which the step's own check (^[0-9]+\\.[0-9]+\\.[0-9]+$) refuses"),
            ("the pin given twice", SEED_CI, 'SDK_TESTED_VERSION = "1.2.3"\nSDK_TESTED_VERSION = "1.2.4"\n',
             "reads '1.2.3\\n1.2.4' into pin, which the step's own check"),
            ("an install step without a plugin", SEED_CI.replace(" pytest-xdist", ""), SEED_HOST,
             "after the install steps the venv lacks xdist, which the pytest leg needs"),
        )
        for label, ci, host, text in cases:
            with self.subTest(case=label):
                w.change({".github/workflows/ci.yml": ci, "kernel/session_host.py": host}, msg=label)
                before = len(w.calls())
                p = w.run(check=2)
                self.assertIn(text, p.stderr)
                self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
                self.assertEqual(w.legs_called()[before:], [], "no leg ran")

    def test_a_leg_rerun_of_pytest_runs_in_the_venv_and_one_of_another_leg_builds_none(self):
        w = self.w
        w.ctl({"rc": {"pytest": 1, "bats": 1}})
        w.run(check=1)
        key = self.sdk()["key"]
        w.ctl({})
        setups = len(w.setups())
        w.run("--leg", "bats", "--flake", self.FLAKE, check=1)
        self.assertNotIn("sdk", w.result()["runner"], "a re-run without the pytest leg builds no environment")
        self.assertEqual(len(w.setups()), setups, "and probes none")
        w.run("--leg", "pytest", "--flake", self.FLAKE, check=0)
        sdk = self.sdk()
        self.assertEqual((sdk["key"], sdk["built"]), (key, False), "the full run's venv, reused")
        self.assertEqual(self.pytest_calls()[-1]["exe"], sdk["python"])
        self.assertEqual(w.result()["legs"][PYTEST_LEG]["cmd"][0], sdk["python"])


class ReadSed(unittest.TestCase):
    r"""read_sed evaluates the pin read in ci.yml's SDK step (`sed -n 's/RE/\1/p' FILE`) without running sed. Held to
    the sed on this machine over the real line and cases around it; a shape it does not read is refused, not guessed."""

    SCRIPTS = (r's/^SDK_TESTED_VERSION = "\([^"]*\)".*$/\1/p', r's/VERSION = \(.*\)/\1/p', r's/^\([0-9]*\)\..*$/\1/p',
               r's/a+\(b\)?/\1/p', r's/[.]\(x\)/\1/p', r's/x\{2\}\(y\)/\1/p')
    TEXT = ('SDK_TESTED_VERSION = "0.2.156"\n# SDK_TESTED_VERSION = "9"\nSDK_TESTED_VERSION = "1.0" # two\nOTHER_VERSION = 7\n'
            '12.4 and more\na+b? xa+b?y .x x.x xxy\nno newline at the end')

    def test_it_prints_what_sed_prints(self):
        sed = shutil.which("sed")
        if not sed:
            self.skipTest("no sed on PATH to compare with")
        tmp = tempfile.mkdtemp(prefix="readsed-")
        self.addCleanup(shutil.rmtree, tmp, True)
        with open(os.path.join(tmp, "f.txt"), "w") as f:
            f.write(self.TEXT)
        for script in self.SCRIPTS:
            with self.subTest(script=script):
                p = subprocess.run([sed, "-n", script, "f.txt"], cwd=tmp, text=True, stdout=subprocess.PIPE, check=True,
                                   env={"PATH": os.environ.get("PATH", ""), "LC_ALL": "C"})
                self.assertEqual(sweep.read_sed(tmp, script, "f.txt", "t"), p.stdout.rstrip("\n"))
        self.assertEqual(sweep.read_sed(tmp, self.SCRIPTS[0], "f.txt", "t"), "0.2.156\n1.0",
                         "the population is not empty: two lines match")

    def test_a_shape_it_does_not_read_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="readsed-")
        self.addCleanup(shutil.rmtree, tmp, True)
        with open(os.path.join(tmp, "f.txt"), "w") as f:
            f.write("x\n")
        outside = os.path.join(tmp, "..", os.path.basename(tmp) + "-outside")
        for script, rel, text in ((r"s/\(x\)/\1/g", "f.txt", "is not s/RE/\\1/p"), (r"s/\w\(x\)/\1/p", "f.txt", "uses \\w"),
                                  (r"s/[[:digit:]]\(x\)/\1/p", "f.txt", "character class"), (r"s/x/\1/p", "f.txt", "no group"),
                                  (r"s/\(x\)/\1/p", "../f.txt", "not a file in the checkout"),
                                  (r"s/\(x\)/\1/p", outside, "not a file in the checkout")):
            with self.subTest(script=script, rel=rel):
                with self.assertRaises(sweep.Refused) as cm:
                    sweep.read_sed(tmp, script, rel, "t")
                self.assertIn(text, str(cm.exception))


def _pytest_counts(test, ini=None, conftest=None):
    """(rc, failed) of the runner's real pytest command over a checkout holding one passing and one failing test,
    with `ini` and `conftest` (texts) written in the checkout's PARENT directory."""
    tmp = tempfile.mkdtemp(prefix="sweepb4-")
    test.addCleanup(shutil.rmtree, tmp, True)
    checkout = os.path.join(tmp, "checkout")
    os.makedirs(os.path.join(checkout, "tests"))
    with open(os.path.join(checkout, "tests", "test_b4.py"), "w") as f:
        f.write("def test_pass():\n    pass\n\n\ndef test_fail():\n    assert False\n")
    if ini is not None:
        with open(os.path.join(tmp, "pytest.ini"), "w") as f:
            f.write(ini)
    if conftest is not None:
        with open(os.path.join(tmp, "conftest.py"), "w") as f:
            f.write(conftest)
    env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    p = subprocess.run(sweep.pytest_cmd(sys.executable, 0), cwd=checkout, env=env, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=300)
    log = os.path.join(tmp, "pytest.log")
    with open(log, "w") as f:
        f.write(p.stdout)
    return p.returncode, sweep.count_tests(PYTEST_LEG, log)[1], p.stdout


class PytestIsolation(unittest.TestCase):
    """B4: the pytest leg's `-c /dev/null --rootdir=. --confcutdir=.`: no pytest.ini or conftest.py above the checkout
    narrows the leg. Real pytest over a two-test checkout; each case asserts the failing test RAN (failed >= 1), since
    a nonzero rc alone is also what collecting nothing gives."""

    DESELECT = "def pytest_collection_modifyitems(config, items):\n    items[:] = [i for i in items if i.name != 'test_fail']\n"

    def check(self, **kw):
        rc, failed, out = _pytest_counts(self, **kw)
        self.assertEqual((rc, failed), (1, 1), "the failing test must run and fail:\n" + out[-2000:])

    def test_a_narrowing_parent_ini(self):
        self.check(ini='[pytest]\naddopts = -k "not test_fail"\n')

    def test_a_deselecting_parent_conftest_alone(self):
        self.check(conftest=self.DESELECT)

    def test_an_empty_parent_ini_and_a_deselecting_conftest(self):
        self.check(ini="[pytest]\n", conftest=self.DESELECT)


CI_YML = ROOT / ".github" / "workflows" / "ci.yml"


def ci_steps(job):
    """{name: (env, run)} of one ci.yml job's named steps, read by line shape (no YAML library in the test deps, as
    tests/test_ci_bats_bound.py): a step is a `      - name:` line and the lines under it; its env is the `env:`
    block's KEY: value lines, its run the `run:` value or `run: |` block. Raises LookupError when the job is gone."""
    src = CI_YML.read_text(encoding="utf-8")
    m = re.search(r"^  %s:\n((?:    .*\n|\n)+)" % re.escape(job), src, re.M)
    if not m:
        raise LookupError("ci.yml has no %s job: re-anchor CiParity" % job)
    steps = {}
    for s in re.finditer(r"^      - name: (.*)\n((?:        .*\n|\n)*)", m.group(1), re.M):
        env, run, cur = {}, None, None
        lines = s.group(2).split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            k = re.match(r"^        ([a-z-]+):(.*)$", line)
            if k:
                cur, val = k.group(1), k.group(2).strip()
                if cur == "run" and val == "|":
                    block = []
                    i += 1
                    while i < len(lines) and (lines[i].startswith(" " * 10) or not lines[i].strip()):
                        block.append(lines[i][10:])
                        i += 1
                    run = "\n".join(block).strip()
                    continue
                if cur == "run":
                    run = val
            elif cur == "env":
                e = re.match(r"^          ([A-Za-z_][A-Za-z0-9_]*): (.*)$", line)
                if e:
                    env[e.group(1)] = e.group(2).strip().strip("\"'")
            i += 1
        steps[s.group(1).strip()] = (env, run)
    return steps


def _expr(text):
    """A GitHub expression as one token."""
    return re.sub(r"\$\{\{.*?\}\}", "<expr>", text)


def _units(tokens):
    """pytest options as units: a flag that takes the next token (-n, -p, -c) paired with it, every other token alone."""
    out, it = [], iter(tokens)
    for t in it:
        out.append((t, next(it, None)) if t in ("-n", "-p", "-c") else (t,))
    return out


class CiParity(unittest.TestCase):
    """B6 (fresh-1): the legs' commands are hand copies of ci.yml's, so this reads ci.yml's steps by name and compares
    them with what the runner builds (pytest_cmd, plan_legs' commands, LEG_ENV). Every difference is named here with
    its reason; a change to either side that adds one reds. Every named step of the four jobs is either compared with a
    leg or named as CI-only, so a new step reds until it is placed. The python job's install steps are not hand copies:
    the runner reads them from ci.yml and builds the pytest leg's venv with them (the SDK ruling), and the cases below
    hold that read to the file and run it."""

    CI_ONLY = {
        # setup that installs the tools the runner finds on the batcher's machine instead
        ("shell", "Install bats (Linux)"),
        ("shell", "Install bats (macOS)"), ("shell", "Install gitleaks (Linux)"), ("secrets", "Install gitleaks"),
        ("vscode-extension", "Cache Playwright's browsers"), ("vscode-extension", "Install the pinned Playwright Chromium"),
        # the history and tree scans: the pre-push hook scans what a push publishes; CI scans all of history
        ("secrets", "Scan every commit"), ("secrets", "Scan the tree as it stands"),
        # the pane bench runs only in CI (the runner's docstring and docs/batching.md say so)
        ("vscode-extension", "Dashboard pane bench (node --test)"),
        # the rostered browser legs' run under ROMP_BROWSER_LEGS_REQUIRE=1 after CI's Chromium install (PR 887): the
        # sweep's npm-test leg runs the same bundles in its npm test with this machine's Playwright browsers, without
        # the switch, so a launch that fails there skips, as in CI's Test step, instead of failing
        ("vscode-extension", "Browser legs (node --test over ci-browser-legs.txt)"),
    }

    def setUp(self):
        self.jobs = {j: ci_steps(j) for j in ("python", "shell", "secrets", "vscode-extension")}
        self.legs = sweep.plan_legs(str(ROOT), "python", 2)

    def test_the_tree_holds_nothing_the_pytest_legs_two_differences_would_hide(self):
        """Two of the pytest leg's named differences hold only while the tree keeps two properties, read here from the
        tree the leg itself runs in (so a change that breaks one turns the leg red): CI's Run pytest collects from the
        root and the leg from tests/, which differ only if a test module lives outside tests/; and the leg's `-c
        /dev/null` drops any pytest configuration in the checkout's root, which CI honours, so the root holds none."""
        listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], stdout=subprocess.PIPE, check=True).stdout
        tracked = [os.fsdecode(n) for n in listing.split(b"\0") if n]
        self.assertIn("tests/test_sweep_runner.py", tracked, "git ls-files read this tree")
        outside = [n for n in tracked if not n.startswith("tests/") and re.fullmatch(r"test_[^/]*\.py|[^/]*_test\.py",
                                                                                      os.path.basename(n))]
        self.assertEqual(outside, [], "a test module outside tests/ runs in CI's Run pytest (which collects from the root) and "
                                      "not in the sweep's pytest leg (which collects tests/)")
        sections = {"pytest.ini": None, "tox.ini": "[pytest]", "setup.cfg": "[tool:pytest]", "pyproject.toml": "[tool.pytest"}
        for name, marker in sections.items():
            path = ROOT / name
            if name in tracked and (marker is None or marker in path.read_text(encoding="utf-8")):
                self.fail("%s configures pytest at the root: CI's Run pytest honours it and the sweep's `-c /dev/null` drops "
                          "it; name the difference in PYTEST_ISOLATION's comment or pass it to the leg" % name)

    def test_every_named_step_is_compared_or_named_as_ci_only(self):
        compared = {("python", "Install pytest"), ("python", "Install cryptography"), ("python", "Install the Claude Agent SDK"),
                    ("python", "Run pytest"), ("shell", "Run bats"), ("shell", "Manager handshake tests (node --test)"),
                    ("shell", "Vendored tooling and host-script tests (node --test)"), ("vscode-extension", "Install deps"),
                    ("vscode-extension", "Typecheck"), ("vscode-extension", "Test"), ("vscode-extension", "Build"),
                    ("vscode-extension", "PDF renderer dependency smoke test (node --test)"),
                    ("vscode-extension", "Browser-backed served-page tests (pytest)")}
        seen = {(j, n) for j, steps in self.jobs.items() for n in steps}
        self.assertEqual(sorted(seen - compared - self.CI_ONLY), [], "a ci.yml step neither compared with a leg nor named CI-only")
        self.assertEqual(sorted((compared | self.CI_ONLY) - seen), [], "a step this pin names is gone from ci.yml")

    def test_the_pytest_command_differs_from_run_pytest_only_as_named(self):
        env, run = self.jobs["python"]["Run pytest"]
        ci = shlex.split(_expr(run))
        ours = sweep.pytest_cmd("python", "<expr>")
        self.assertEqual(ci[:3], ours[:3], "python -m pytest")
        ci_units, our_units = _units(ci[3:]), _units(ours[3:])
        named = [("tests",),                              # CI collects from the root; test modules live only under tests/
                 ("-p", "no:cacheprovider")]              # nothing written to a .pytest_cache in the checkout
        named += _units(sweep.PYTEST_ISOLATION)           # B4: no ini or conftest above the checkout
        named += [("--ignore=%s" % p,) for p in sorted(sweep.PYTEST_IGNORED)]   # Q6
        for u in named:
            self.assertIn(u, our_units, "a named difference the runner no longer has: %r" % (u,))
        # the -n count: CI's expression (2 or 0 by runner) against the runner's idle cores
        self.assertIn(("-n", "<expr>"), ci_units)
        self.assertEqual(sorted(u for u in our_units if u not in named), sorted(ci_units))

    def test_the_served_steps_switches_are_the_pytest_legs(self):
        env, _run = self.jobs["vscode-extension"]["Browser-backed served-page tests (pytest)"]
        served = {k: v for k, v in env.items() if k.startswith("ROMP_SERVED_TESTS_")}
        self.assertEqual(served, {k: v for k, v in sweep.LEG_ENV[PYTEST_LEG].items() if k.startswith("ROMP_SERVED_TESTS_")})
        self.assertEqual(sorted(sweep.LEG_ENV[PYTEST_LEG]), sorted(set(served) | {"ROMP_SDK_REQUIRE"}),
                         "the pytest leg's switches are the served step's and the Run pytest step's SDK switch")

    def test_the_run_pytest_steps_env_is_the_pytest_legs_but_the_gil_setting(self):
        env, _run = self.jobs["python"]["Run pytest"]
        self.assertEqual(sorted(env), ["PYTHON_GIL", "ROMP_SDK_REQUIRE"])
        self.assertEqual(sweep.LEG_ENV[PYTEST_LEG]["ROMP_SDK_REQUIRE"], env["ROMP_SDK_REQUIRE"])
        # PYTHON_GIL, the named difference: CI's free-threaded cell alone sets it (to 0); the runner runs the one --python
        # and sets nothing, so a free-threaded --python runs with its own default
        self.assertEqual(env["PYTHON_GIL"], "${{ endsWith(matrix.python-version, 't') && '0' || '' }}")
        self.assertNotIn("PYTHON_GIL", sweep.LEG_ENV[PYTEST_LEG])

    def pin(self):
        """kernel/session_host.py's SDK_TESTED_VERSION, read by this test on its own (ci.yml's SDK step reads the same
        line with sed)."""
        hits = re.findall(r'(?m)^SDK_TESTED_VERSION = "([^"]*)"', (ROOT / "kernel" / "session_host.py").read_text(encoding="utf-8"))
        self.assertEqual(len(hits), 1, hits)
        return hits[0]

    def test_the_runner_reads_every_install_step_of_the_python_job_as_written(self):
        """Every named step of the python job before Run pytest is an install step the runner reads, in CI's order
        (INSTALL_STEPS), and it reads each as written: the two pip lines as they stand, and the SDK step as its pip line
        with the pin its sed read gives, then its import check."""
        self.assertEqual([n for n in self.jobs["python"] if n != "Run pytest"], list(sweep.INSTALL_STEPS),
                         "the runner reads every install step of the python job, and only those")
        plan = sweep.read_install_plan(str(ROOT), "HEAD")
        pin = self.pin()
        self.assertEqual((plan["dist"], plan["pin"], plan["module"]), ("claude-agent-sdk", pin, "claude_agent_sdk"))
        by_step = {step["step"]: step["commands"] for step in plan["steps"]}
        for name in ("Install pytest", "Install cryptography"):
            self.assertEqual(by_step[name], [("pip", shlex.split(self.jobs["python"][name][1]))], name)
        self.assertEqual(by_step[sweep.SDK_STEP], [("pip", ["python", "-m", "pip", "install", "claude-agent-sdk==" + pin]),
                                                   ("check", ["python", "-c", "import claude_agent_sdk"])])

    def test_the_runners_environment_holds_what_the_install_steps_install(self):
        """Run: the runner over a world holding this tree's ci.yml and kernel/session_host.py, FAKE standing in for
        pip. The venv the pytest leg runs in holds every requirement the python job's install steps name, the SDK at
        the pin the SDK step reads, and nothing else; the population is read from ci.yml here, not from the runner."""
        real = {".github/workflows/ci.yml": CI_YML.read_text(encoding="utf-8"),
                "kernel/session_host.py": (ROOT / "kernel" / "session_host.py").read_text(encoding="utf-8")}
        w = World(dict(SEED, **real))
        self.addCleanup(w.close)
        w.run(check=0)
        pin, expected = self.pin(), {}
        for name, (_env, run) in self.jobs["python"].items():
            for line in (run or "").splitlines():
                words = shlex.split(line) if line.strip().startswith("python -m pip install") else []
                for word in words[4:]:
                    if not word.startswith("-"):
                        dist, _eq, version = word.replace("$pin", pin).partition("==")
                        expected[dist.lower()] = version or "9.9.9"
        self.assertEqual(expected.get("claude-agent-sdk"), pin, "the SDK step's requirement is in the population read")
        call = [c for c in w.calls() if c["leg"] == PYTEST_LEG][0]
        self.assertEqual(call["venv_installs"], expected, "the pytest leg's venv holds what ci.yml installs")
        self.assertEqual(w.result()["runner"]["sdk"]["version"], pin)

    def test_bats_and_the_node_legs_run_ci_s_commands(self):
        env, run = self.jobs["shell"]["Run bats"]
        self.assertEqual(shlex.split(run), self.legs["bats"]["cmd"][:2] + list(sweep.GLOBS["bats"]),
                         "the runner passes the glob's expansion, CI the glob")
        # ROMP_GITLEAKS_REQUIRE is CI's Linux value: the Linux cell installs the pinned gitleaks
        self.assertEqual(env.get("ROMP_GITLEAKS_REQUIRE"), "${{ runner.os == 'Linux' && '1' || '' }}")
        self.assertEqual({"BATS_TEST_TIMEOUT": env["BATS_TEST_TIMEOUT"], "ROMP_GITLEAKS_REQUIRE": "1"}, sweep.LEG_ENV["bats"])
        for step, leg in (("Manager handshake tests (node --test)", "manager"),
                          ("Vendored tooling and host-script tests (node --test)", "tools")):
            _env, run = self.jobs["shell"][step]
            self.assertEqual(shlex.split(run), self.legs[leg]["cmd"][:2] + list(sweep.GLOBS[leg]))
        # tools/pdf-smoke.test.mjs, its own step in the extension job, is in the tools leg's glob
        _env, run = self.jobs["vscode-extension"]["PDF renderer dependency smoke test (node --test)"]
        self.assertEqual(shlex.split(run), ["node", "--test", "tools/pdf-smoke.test.mjs"])
        self.assertIn("tools/pdf-smoke.test.mjs", self.legs["tools"]["cmd"])

    def test_the_webview_legs_run_the_extension_jobs_commands(self):
        steps = self.jobs["vscode-extension"]
        self.assertEqual(shlex.split(steps["Install deps"][1]), list(sweep.DEPS_CMD[:2]),
                         "npm ci; the runner adds --no-audit --no-fund, which change what npm prints, not what it installs")
        self.assertEqual(list(sweep.DEPS_CMD[2:]), ["--no-audit", "--no-fund"])
        for step, leg in (("Typecheck", "typecheck"), ("Test", "npm-test"), ("Build", "build")):
            self.assertEqual(shlex.split(steps[step][1]), self.legs[leg]["cmd"], step)
            self.assertEqual(self.legs[leg]["cwd"], "vscode-extension")


# The private-checkout record every run of the runner carries (runner.checkout); a reader refuses a run without one.
CHECKOUT_REC = {"form": "clone", "path": "/nonexistent/trees/1234567890ab-test", "create_s": 0.1, "verify_s": 0.1, "files": 1,
                "setup": None}


class Reader(unittest.TestCase):
    """assess, the reader scripts/batch.py verify calls: each case by name, over files written the way the runner
    writes them. The batch side of the same cases is tests/test_batch_tool.py, VerifyReadsTheSweep."""

    SHA = "1234567890" + "a" * 30
    OTHER = "1234567890" + "b" * 30      # same 10-character prefix, another commit

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sweepread-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = {"XDG_STATE_HOME": self.tmp, "HOME": self.tmp}

    TOP = ("schema", "sha", "branch", "tree")

    def legs(self, **rcs):
        """A full run's legs as the runner writes them at a sha with no vscode-extension/package.json: every leg that
        is always owed, and the ledger, run with rc 0 (or `rcs`), and deps and the webview legs not owed for that
        reason alone."""
        legs = {n: {"owed": True, "rc": rcs.get(n, 0), "started": "2026-01-01T00:00:01Z", "finished": "2026-01-01T00:00:02Z",
                    "log": "logs/%s.log" % n} for n in sweep.LEGS}
        for n in sweep.TEST_LEGS:
            legs[n].update(tests=1, failed=1 if rcs.get(n) else 0)
        for n in sweep.EXTENSION_LEGS:
            legs[n] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
        return legs

    def run_rec(self, kind="full", **over):
        """One run record as the runner writes it; `over` replaces its keys. Its recorded verdict is its own legs'
        unless given. (Not named `run`: that is unittest.TestCase's own method, which runs the test.)"""
        run = {"kind": kind, "sha": self.SHA, "branch": "batch/b1", "started": "2026-01-01T00:00:00Z",
               "finished": "2026-01-01T00:01:00Z", "flakes": {}, "legs": self.legs(), "red": [], "invalid": None}
        run.update(over)
        if "runner" not in over:
            run["runner"] = {"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()}, "checkout": CHECKOUT_REC}
        if "verdict" not in over:
            run["verdict"] = sweep.run_verdict(run)
        return run

    def result(self, sha=None, runs=None, **over):
        """A result file: {"schema", "sha", "branch", "runs"}, by default one full run. Keys of TOP in `over` go to the
        file, the rest to its one run."""
        sha = sha or self.SHA
        top = {k: over.pop(k) for k in self.TOP if k in over}
        if runs is None:
            runs = [self.run_rec(**dict({"sha": sha}, **over))]
        data = {"schema": sweep.SCHEMA, "sha": sha, "branch": "batch/b1", "runs": runs}
        data.update(top)
        return data

    def write(self, data, sha=None):
        sweep.write_result(sweep.result_path(sha or data["sha"], self.env), data)

    def case(self, sha=None, branch=None):
        a = sweep.assess(sha or self.SHA, branch=branch, env=self.env)
        return a["case"], a["line"]

    def test_pass(self):
        self.write(self.result())
        case, line = self.case()
        self.assertEqual(case, "pass")
        self.assertIn("sweep at 1234567890: pass, finished 2026-01-01T00:01:00Z (pytest 0, bats 0, manager 0, tools 0, ledger 0; "
                      "not owed: deps, typecheck, npm-test, build)", line)

    def test_a_malformed_failed_count_reads_red_and_is_named(self):
        """Round 1, extra5-6: a test leg at rc 0 whose failed count is not an int of 0 or more (a string, a float, a bool,
        negative, null or absent) is red through the reader, the line naming the count; at the frozen head each read
        pass, as zero failures."""
        absent = object()
        for bad, named in (("1", "its failed count is malformed (failed '1')"),
                           (1.0, "its failed count is malformed (failed 1.0)"),
                           (True, "its failed count is malformed (failed True)"),
                           (-1, "its failed count is malformed (failed -1)"),
                           (None, "it records no failed count"), (absent, "it records no failed count")):
            with self.subTest(failed="absent" if bad is absent else repr(bad)):
                legs = self.legs()
                if bad is absent:
                    del legs["bats"]["failed"]
                else:
                    legs["bats"]["failed"] = bad
                self.write(self.result(legs=legs))
                case, line = self.case()
                self.assertEqual(case, "red", line)
                self.assertIn("bats (rc 0 but %s)" % named, line)

    def test_missing_names_the_full_sha_the_directory_read_and_where_it_came_from(self):
        """The runner and the reader share the state dir only when their environments agree (ROMP_STATE_DIR, else
        XDG_STATE_HOME, else HOME), so a missing result names the directory the reader read and the variable it
        came from, and says when that directory does not exist at all."""
        case, line = self.case()
        self.assertEqual(case, "missing")
        self.assertIn(self.SHA, line)
        d = sweep.sweeps_dir(self.env)
        self.assertIn("in %s (the state dir from XDG_STATE_HOME; the directory does not exist)" % d, line)
        self.assertIn("with the same ROMP_STATE_DIR and XDG_STATE_HOME as this reader", line)
        os.makedirs(d)
        line = self.case()[1]
        self.assertIn("in %s (the state dir from XDG_STATE_HOME)" % d, line, "an existing directory is named without the clause")
        for env, source in (({"ROMP_STATE_DIR": os.path.join(self.tmp, "s"), "XDG_STATE_HOME": self.tmp}, "ROMP_STATE_DIR"),
                            ({"HOME": self.tmp}, "HOME, with ROMP_STATE_DIR and XDG_STATE_HOME unset")):
            with self.subTest(source=source):
                a = sweep.assess(self.SHA, env=env)
                self.assertEqual(a["case"], "missing")
                self.assertIn("in %s (the state dir from %s" % (sweep.sweeps_dir(env), source), a["line"])

    def test_stale_by_branch_and_by_the_recorded_sha(self):
        self.write(self.result(sha=self.OTHER))
        case, line = self.case(branch="batch/b1")
        self.assertEqual(case, "stale")
        self.assertIn("the newest result for batch/b1 is at 1234567890", line)
        self.assertEqual(self.case()[0], "missing", "without the branch a result at another sha is not found")
        self.write(self.result(sha=self.OTHER), sha=self.SHA)    # the file named for SHA records OTHER
        case, line = self.case()
        self.assertEqual(case, "stale", "the full sha decides, not its 10-character prefix")
        self.assertIn("records sha", line)

    def test_unfinished_red_invalid_incomplete_unreadable(self):
        cases = []
        self.write(self.result(finished=None, verdict="running"))
        cases.append(("unfinished", self.case()))
        legs = self.legs()
        legs["bats"]["rc"] = 1
        self.write(self.result(legs=legs, verdict="red", red=["bats"]))
        cases.append(("red", self.case()))
        self.write(self.result(legs=legs, verdict="pass"))       # a recorded pass over a red leg
        cases.append(("invalid", self.case()))
        self.write(self.result(invalid="HEAD moved to 0000000000 during the run", verdict="invalid"))
        cases.append(("invalid", self.case()))
        legs = self.legs()
        del legs["bats"]
        self.write(self.result(legs=legs))
        cases.append(("incomplete", self.case()))
        self.write(self.result(schema=0))
        cases.append(("unreadable", self.case()))
        os.makedirs(os.path.dirname(sweep.result_path(self.SHA, self.env)), exist_ok=True)
        with open(sweep.result_path(self.SHA, self.env), "w") as f:
            f.write("{")
        cases.append(("unreadable", self.case()))
        for expected, (case, line) in cases:
            with self.subTest(expected=expected, line=line):
                self.assertEqual(case, expected)
                self.assertTrue(line.startswith("sweep %s" % expected), line)
        self.assertIn("bats (rc 1)", cases[1][1][1])
        self.assertIn("disagrees with its legs", cases[2][1][1])
        self.assertIn("HEAD moved", cases[3][1][1])
        self.assertIn("no bats leg", cases[4][1][1])
        self.assertIn("schema 0", cases[5][1][1])


    def test_a_not_owed_mark_the_runner_never_writes_is_invalid(self):
        """The runner always owes pytest, bats, manager and tools, marks deps and the webview legs not owed only when
        the sha has no vscode-extension/package.json (round 1, decision 11: every head owes the webview legs, whatever
        it changed), and the ledger only with a reason. A record that says otherwise did not come from the runner (or
        came from a runner with another roster), and a leg it marks not owed ran nothing, so the reader refuses it by
        name: verify, plan, --repin and check read through it."""
        cases = []
        legs = self.legs()
        for n in sweep.LEGS:
            legs[n] = {"owed": False}
        cases.append(("every leg not owed", legs, "pytest, bats, manager, tools marked not owed"))
        legs = self.legs()
        legs["pytest"] = {"owed": False, "rc": None, "why": "skipped by hand"}
        cases.append(("pytest alone", legs, "pytest marked not owed"))
        legs = self.legs()
        legs["deps"] = {"owed": False, "rc": None}
        cases.append(("deps with no reason", legs, "deps marked not owed with no reason"))
        legs = self.legs()
        legs["build"] = {"owed": False, "rc": None, "why": "  "}
        cases.append(("a blank reason", legs, "build marked not owed with no reason"))
        legs = self.legs()
        legs["deps"] = {"owed": False, "rc": None, "why": "vscode-extension/node_modules present"}
        cases.append(("deps for a reason the runner no longer gives", legs,
                      "deps marked not owed for a reason other than 'no vscode-extension/package.json' "
                      "('vscode-extension/node_modules present')"))
        # the head's runner marked the webview legs not owed by a changed-path rule, with this reason
        untouched = "kernel/kernel.py, ui/ and vscode-extension/ untouched since 1234567890"
        legs = self.legs()
        for n in sweep.WEBVIEW_LEGS:
            legs[n] = {"owed": False, "rc": None, "why": untouched}
        cases.append(("the webview legs by the changed-path rule", legs,
                      "typecheck, npm-test, build marked not owed for a reason other than 'no vscode-extension/package.json' "
                      "('%s')" % untouched))
        legs = self.legs()
        legs["npm-test"] = {"owed": False, "rc": None, "why": "skipped on this box"}
        cases.append(("one webview leg", legs, "npm-test marked not owed for a reason other than 'no vscode-extension/package.json' "
                                               "('skipped on this box')"))
        for label, legs, named in cases:
            with self.subTest(label):
                self.write(self.result(legs=legs))
                case, line = self.case()
                self.assertEqual(case, "invalid", line)
                self.assertIn(named, line)
                self.assertEqual(sweep.verdict_of(self.run_rec(legs=legs)), "red", "the verdict rule owes such a leg too")

    FLAKE = "tests/test_notes.py::test_order (known)"

    def red_then(self, *later):
        """A history: a full run that failed pytest (rc 1), then the runs in `later`."""
        return self.result(runs=[self.run_rec(legs=self.legs(pytest=1), started="2026-01-01T00:00:00Z")] + list(later))

    def rerun(self, rc=0, flake=FLAKE, **over):
        """A --leg re-run of pytest, as the runner appends it after a failed run."""
        legs = {PYTEST_LEG: dict(self.legs(pytest=rc)[PYTEST_LEG], log="logs/pytest.rerun.log")}
        kw = dict(legs=legs, flakes={PYTEST_LEG: flake} if flake is not None else {}, started="2026-01-01T00:02:00Z",
                  finished="2026-01-01T00:03:00Z")
        kw.update(over)
        return self.run_rec(kind="leg", **kw)

    def test_a_counted_rerun_passes_and_the_line_names_both_runs(self):
        """Pre-round Q11 and frozen-head item 1: a failed run is excused when the next run of that leg carries --flake
        naming it, whether that run is a --leg re-run or a full run; the pass line names the failure and the flake."""
        note = "pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE
        for label, later in (("a --leg re-run", self.rerun()),
                             ("a full run", self.run_rec(flakes={PYTEST_LEG: self.FLAKE}, started="2026-01-01T00:02:00Z"))):
            with self.subTest(label):
                self.write(self.red_then(later))
                case, line = self.case()
                self.assertEqual(case, "pass", line)
                self.assertIn(note, line)
                self.assertIn("finished 2026-01-01T0", line)

    def test_a_later_green_without_a_flake_or_a_second_failure_leaves_the_sha_red(self):
        """Frozen-head item 1: a red run is not erased by a later run. A later run that passes the failed leg without
        --flake naming it, or a second failure of the leg (a flake is excused once), reads red naming the runs and
        their logs, and says a fix and a new head is the way on."""
        cases = (
            ("a full run passes it with no flake", [self.run_rec(started="2026-01-01T00:02:00Z")],
             "run 1 failed pytest (rc 1; log logs/pytest.log), and run 2 passed it with no --flake naming it"),
            ("a --leg re-run passes it with no flake", [self.rerun(flake=None, verdict="pass")], None),
            ("the flake fails again", [self.rerun(rc=1)], "pytest failed in runs 1 and 2; a known flake is excused once"),
            ("a full run with the flake fails again", [self.run_rec(legs=self.legs(pytest=1), flakes={PYTEST_LEG: self.FLAKE})],
             "pytest failed in runs 1 and 2"),
            ("excused, then failed again", [self.rerun(), self.run_rec(legs=self.legs(pytest=1), started="2026-01-01T00:04:00Z")],
             "pytest failed in runs 1 and 3"),
        )
        for label, later, named in cases:
            with self.subTest(label):
                self.write(self.red_then(*later))
                case, line = self.case()
                if named is None:       # the runner never writes a --leg re-run with no flake: invalid, not red
                    self.assertEqual(case, "invalid", line)
                    self.assertIn("run 2 re-ran pytest with no known flake named", line)
                    continue
                self.assertEqual(case, "red", line)
                self.assertIn(named, line)
                self.assertIn("fix it and sweep the new head; logs under %s" % os.path.join(sweep.sweeps_dir(self.env), "logs", self.SHA),
                              line)

    def test_a_failed_leg_no_later_run_ran_stays_red(self):
        """A leg that failed and that a later full run marks not owed (for a missing extension, a record no runner
        writes at one sha) is not excused by not running: the result reads red naming the failed run."""
        failed = self.legs()
        failed["npm-test"] = {"owed": True, "rc": 1, "tests": 3, "failed": 1, "started": "s", "finished": "f", "log": "logs/n.log"}
        self.write(self.result(runs=[self.run_rec(legs=failed), self.run_rec(started="2026-01-01T00:02:00Z")]))
        case, line = self.case()
        self.assertEqual(case, "red", line)
        self.assertIn("npm-test failed in run 1 (rc 1) and no later run ran it", line)

    def test_an_invalid_run_needs_no_flake_and_the_line_names_it(self):
        """Round 1, decision 18: an invalid run is not a test failure, so a later green counts over it with no flake,
        but the pass line names it. A red before an invalid run still needs the flake."""
        reason = "after the pytest leg the checkout is not the sha's tree: changed kernel/kernel.py"
        # the invalid run failed pytest too: a failure in an invalid run needs no flake either
        self.write(self.result(runs=[self.run_rec(invalid=reason, legs=self.legs(pytest=1)), self.run_rec(started="2026-01-01T00:02:00Z")]))
        case, line = self.case()
        self.assertEqual(case, "pass", line)
        self.assertIn("an earlier run 1 (started 2026-01-01T00:00:00Z) was invalid: %s" % reason, line)
        self.write(self.red_then(self.run_rec(invalid=reason), self.run_rec(started="2026-01-01T00:04:00Z")))
        case, line = self.case()
        self.assertEqual(case, "red", line)
        self.assertIn("run 1 failed pytest (rc 1; log logs/pytest.log), and run 3 passed it with no --flake naming it", line)

    def test_a_history_the_runner_never_writes_is_invalid(self):
        """The records no runner writes, each refused by name: a --leg re-run that names no flake (or a blank one), a
        flake for a leg with no failed run before it, a flake for a leg the run did not run, a run recorded at another
        sha, and a --leg re-run with no full run before it."""
        leg_only = self.rerun()
        cases = (
            ("a re-run with no flake", self.red_then(self.rerun(flake=None)), "run 2 re-ran pytest with no known flake named"),
            ("a blank flake", self.red_then(self.rerun(flake="  ")), "run 2 re-ran pytest with no known flake named"),
            ("a flake with no failure before it", self.result(runs=[self.run_rec(), self.run_rec(flakes={PYTEST_LEG: self.FLAKE})]),
             "run 2 names a known flake for pytest, but pytest has no failed run before it at this sha"),
            ("a flake for a leg the run did not run", self.red_then(self.rerun(flakes={PYTEST_LEG: self.FLAKE, "bats": self.FLAKE})),
             "run 2 names a known flake for bats, which it did not run"),
            ("a run at another sha", self.red_then(self.rerun(sha=self.OTHER)), "run 2 was recorded at %s" % self.OTHER),
            ("a re-run with no full run", self.result(runs=[leg_only]), "it records no full run"),
            # extra4-7: a --leg re-run recorded before any run of its leg, a full run after it: nothing before the re-run
            # failed, so its flake excuses nothing
            ("a re-run before any run of its leg", self.result(runs=[self.rerun(started="2026-01-01T00:00:00Z"),
                                                                     self.run_rec(started="2026-01-01T00:04:00Z")]),
             "run 1 names a known flake for pytest, but pytest has no failed run before it at this sha"),
        )
        for label, data, named in cases:
            with self.subTest(label):
                self.write(data)
                case, line = self.case()
                self.assertEqual(case, "invalid", line)
                self.assertIn(named, line)

    def test_the_runs_are_the_history_and_a_schema_1_result_is_refused(self):
        """Round 1, A6: SCHEMA is 2, and a schema-1 result (the runner that swept the batcher's own tree) reads
        unreadable, so no result of the old runner passes verify, plan or --repin."""
        self.assertEqual(sweep.SCHEMA, 2)
        old = {"schema": 1, "sha": self.SHA, "branch": "batch/b1", "started": "s", "finished": "f", "legs": self.legs(),
               "history": [], "verdict": "pass", "red": [], "invalid": None}
        self.write(old)
        case, line = self.case()
        self.assertEqual(case, "unreadable", line)
        self.assertIn("schema 1, recorded by a runner that swept the batcher's own tree; sweep again", line)

    def test_a_run_that_records_no_private_checkout_is_unreadable(self):
        """Round 1, A6's aim: no result of a runner that swept the batcher's own tree passes. This branch's intermediate
        runners wrote schema 2, with the allowlist's hash, before the private checkout existed, so the schema alone does
        not tell them apart: a run with no runner.checkout of form clone reads unreadable, whichever run it is."""
        ok = self.run_rec()
        bare = self.run_rec(runner={"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()}})
        worktree = self.run_rec(runner={"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()},
                                        "checkout": dict(CHECKOUT_REC, form="worktree")})
        for label, runs, named in (("the only run", [bare], "run 1"), ("an earlier run", [bare, ok], "run 1"),
                                   ("a later full run", [ok, bare], "run 2"), ("another form", [worktree], "run 1")):
            with self.subTest(runs=label):
                self.write(self.result(runs=runs))
                case, line = self.case()
                self.assertEqual(case, "unreadable", line)
                self.assertIn("%s records no private checkout, so it was recorded by a runner that swept the batcher's own "
                              "tree; sweep again" % named, line)
        self.write(self.result(runs=[ok]))
        self.assertEqual(self.case()[0], "pass")

    def test_a_result_recorded_under_another_leg_environment_is_refused(self):
        """Round 1, decision 10: a result made under another environment policy is not the same gate."""
        self.write(self.result(runner={"leg_env": {"allow": ["USER"], "hash": "0" * 64}}))
        case, line = self.case()
        self.assertEqual(case, "invalid", line)
        self.assertIn("recorded under another leg environment (hash 000000000000; this reader's is %s" % sweep.policy_hash()[:12], line)
        self.write(self.result(runner={}))
        case, line = self.case()
        self.assertEqual(case, "invalid", line)
        self.assertIn("(hash none;", line)

    def test_a_result_that_is_not_the_runners_shape_is_unreadable_by_name(self):
        """Round 1, extra4-5: the reader's named refusals in _load, each read as unreadable with its reason rather than
        raised: a file that is not a JSON object, runs that are not a list of run records, a run whose legs are not a
        mapping of leg records (a list of names, a record that is a number), and an older file whose top-level legs are
        a list. A missing sha read with its branch skips such a file for another sha instead of failing the read."""
        run = self.run_rec()
        cases = (
            ("a JSON list", [], "not a JSON object"),
            ("runs not a list", dict(self.result(), runs="x"), "its runs are not a list of run records"),
            ("a run that is a number", dict(self.result(), runs=[5]), "its runs are not a list of run records"),
            ("a run's legs a list", self.result(runs=[dict(run, legs=[PYTEST_LEG])]), "run 1's legs are not a mapping of leg records"),
            ("a leg record 5", self.result(runs=[dict(run, legs=dict(run["legs"], **{PYTEST_LEG: 5}))]),
             "run 1's legs are not a mapping of leg records"),
            ("an older file's legs a list", {"schema": 1, "sha": self.SHA, "legs": [PYTEST_LEG]},
             "its legs are not a mapping of leg records"),
        )
        path = sweep.result_path(self.SHA, self.env)
        for label, data, named in cases:
            with self.subTest(label):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    json.dump(data, f)
                case, line = self.case()
                self.assertEqual(case, "unreadable", line)
                self.assertIn("sweep unreadable: %s: %s; sweep again" % (path, named), line)
        os.remove(path)
        other = sweep.result_path(self.OTHER, self.env)
        with open(other, "w") as f:
            json.dump([], f)
        case, line = self.case(branch="batch/b1")
        self.assertEqual(case, "missing", "a non-object file for another sha is skipped, not raised: %s" % line)

    def test_the_schema_must_be_the_integer(self):
        self.write(self.result(schema=True))
        case, line = self.case()
        self.assertEqual(case, "unreadable", "True equals 1 in Python and must not read as schema 1: %s" % line)


class Rules(unittest.TestCase):
    def test_the_verdict_rule(self):
        v = sweep.verdict_of

        def result(finished="2026-01-01T00:00:00Z", invalid=None, **legs):
            base = {n: {"owed": False, "rc": None, "why": "not owed here"} for n in sweep.LEGS}
            for n in sweep.EXTENSION_LEGS:
                base[n] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
            for n in sweep.ALWAYS_OWED:
                base[n] = {"owed": True, "rc": 0, "tests": 1, "failed": 0}
            base.update(legs)
            return {"finished": finished, "invalid": invalid, "legs": base}
        self.assertEqual(v(result(finished=None)), "running")
        self.assertEqual(v(result(invalid="HEAD moved")), "invalid")
        self.assertEqual(v(result(bats={"owed": True, "rc": 1})), "red")
        self.assertEqual(v(result(bats={"owed": True, "rc": None})), "red", "an owed leg with no rc is red")
        self.assertEqual(v(result(bats={"owed": True, "rc": False})), "red", "rc must be the integer 0")
        # extra4-6: the ledger is not a test leg, so a bool rc is the one reason this case is red (False == 0 in Python)
        self.assertEqual(v(result(ledger={"owed": True, "rc": False})), "red", "rc must be the integer 0, not False")
        self.assertEqual(v(result(bats={"rc": 0, "tests": 1, "failed": 0})), "pass", "a leg that does not say it is not owed is owed")
        self.assertEqual(v(result(bats={"owed": "no", "rc": None})), "red", "only owed: false excuses a leg")
        self.assertEqual(v(result(pytest={"owed": True, "rc": 0, "tests": 1, "failed": 0})), "pass",
                         "a not-owed leg's empty rc is fine")
        # extra5-6: a test leg's failed count is required beside its test count and must be an int of 0 or more; one that
        # is missing, a string, a float, a bool or negative reads not passed, never as zero failures
        absent = object()
        for leg in (PYTEST_LEG, "bats", "npm-test"):
            for bad in ("1", 1.0, True, -1, None, absent):
                rec = {"owed": True, "rc": 0, "tests": 3}
                if bad is not absent:
                    rec["failed"] = bad
                with self.subTest(leg=leg, failed="absent" if bad is absent else repr(bad)):
                    self.assertFalse(sweep.passed(leg, rec))
                    self.assertEqual(v(result(**{leg: rec})), "red")
        self.assertTrue(sweep.passed("bats", {"owed": True, "rc": 0, "tests": 3, "failed": 0}))
        self.assertEqual(v(result(bats={"owed": True, "rc": 0})), "red", "a test leg with rc 0 and no count ran nothing")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": 0})), "red", "a count of 0 is no test run")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": True})), "red", "a count must be an int")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": 3, "failed": 1})), "red", "a failed test is red at rc 0")
        self.assertEqual(v(result(ledger={"owed": True, "rc": 0})), "pass", "the ledger check is not a test leg")
        self.assertEqual(v(result()), "pass")
        self.assertEqual(v(result(pytest={"owed": False, "rc": None, "why": "skipped"})), "red", "pytest is always owed")
        self.assertEqual(v(result(deps={"owed": False, "rc": None})), "red", "not owed takes a reason")
        self.assertEqual(v(result(build={"owed": False, "rc": None, "why": "ui/ untouched"})), "red",
                         "a webview leg is not owed only for a missing extension")
        missing = result(pytest={"owed": True, "rc": 0, "tests": 1, "failed": 0})
        del missing["legs"]["bats"]
        self.assertEqual(v(missing), "red", "a leg absent from the record is owed")

    def test_the_rc_text_names_a_malformed_count(self):
        """Round 1, extra5-6: a test leg at rc 0 that did not pass says why, and a malformed count is named as one,
        not as "no test ran"."""
        t = sweep._rc_text
        self.assertEqual(t("bats", {"rc": 0, "tests": 3, "failed": "1"}), "rc 0 but its failed count is malformed (failed '1')")
        self.assertEqual(t("bats", {"rc": 0, "tests": 3, "failed": -1}), "rc 0 but its failed count is malformed (failed -1)")
        self.assertEqual(t("bats", {"rc": 0, "tests": 3, "failed": True}), "rc 0 but its failed count is malformed (failed True)")
        self.assertEqual(t("bats", {"rc": 0, "tests": 3}), "rc 0 but it records no failed count")
        self.assertEqual(t("bats", {"rc": 0, "tests": True, "failed": 0}), "rc 0 but its test count is malformed (tests True)")
        self.assertEqual(t("bats", {"rc": 0, "tests": 0, "failed": 0}), "rc 0 but no test ran")
        self.assertEqual(t("bats", {"rc": 0}), "rc 0 but no test ran")
        self.assertEqual(t("bats", {"rc": 0, "tests": 3, "failed": 2}), "rc 0 but its log shows 2 failed")
        self.assertEqual(t("bats", {"rc": 0, "tests": 3, "failed": 0}), "rc 0")

    def test_the_state_dir_resolves_as_bin_romp_does(self):
        sd = sweep.state_dir
        self.assertEqual(sd({"ROMP_STATE_DIR": "/s", "XDG_STATE_HOME": "/x", "HOME": "/h"}), "/s")
        self.assertEqual(sd({"ROMP_STATE_DIR": "", "XDG_STATE_HOME": "/x", "HOME": "/h"}), "/x/romp")
        self.assertEqual(sd({"XDG_STATE_HOME": "", "HOME": "/h"}), "/h/.local/state/romp")

    def test_every_flag_has_help(self):
        bare = re.compile(r"^  (-{1,2}[\w-]+(?: [\w|<>=.-]+)?|[a-z]+)\s*$")
        run = lambda *a: subprocess.run([sys.executable, str(SWEEP), *a], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        top = run("--help")
        self.assertEqual(top.returncode, 0, top.stderr)
        for sub in ("run", "check"):
            p = run(sub, "--help")
            self.assertEqual(p.returncode, 0, p.stderr)
            for line in p.stdout.splitlines():
                self.assertIsNone(bare.match(line), "%s --help: %r has no help text" % (sub, line.strip()))


if __name__ == "__main__":
    unittest.main()
