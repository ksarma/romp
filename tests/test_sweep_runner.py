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
import ast
import fcntl
import glob
import importlib.util
import json
import os
import re
import shlex
import shutil
import stat
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
# Read from PYTEST_LEGS, the legs pytest runs, whose first is the pytest leg whatever LEGS' order.
PYTEST_LEG = sweep.PYTEST_LEGS[0]
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
                                home=os.environ.get("HOME"), pythonpath=os.environ.get("PYTHONPATH"),
                                pip_env={k: v for k, v in os.environ.items() if k.startswith("PIP_")})) + "\n")


if name == "python" and args[:2] == ["-m", "venv"]:
    setup("venv", target=args[-1])
    if ctl.get("venv_rc"):
        sys.exit(ctl["venv_rc"])
    os.makedirs(os.path.join(args[-1], "bin"))
    os.makedirs(os.path.join(args[-1], "lib", "python3.99", "site-packages"))
    shutil.copy(here, os.path.join(args[-1], "bin", "python"))
    os.chmod(os.path.join(args[-1], "bin", "python"), 0o755)
    if not ctl.get("venv_no_python3"):                 # a venv's bin holds python3 beside python, as `python -m venv` makes it
        os.symlink("python", os.path.join(args[-1], "bin", "python3"))
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
        missing = set(ctl.get("missing", [])) if in_venv else set(ctl.get("base_missing", []))
        if in_venv:
            missing |= {m for m, d in MODULE_DISTS.items() if d not in installs}
        asked = [a for a in args[2:] if not a.startswith("import:") and a != "all:"]
        modules = [a[len("import:"):] for a in args[2:] if a.startswith("import:")]
        if in_venv:
            dists = {d: ctl.get("sdk_reports") or installs.get(norm(d)) for d in asked}
            found = {m: any(norm(d).replace("-", "_") == m.lower() for d in installs) for m in modules}
        else:
            # --python outside any venv (the served leg's interpreter): it has every distribution asked for but the ones
            # ctl says it lacks (by default the SDK, as CI's served step has none), at the versions ctl gives
            base_dists, lacks = ctl.get("base_dists", {}), ctl.get("base_lacks", ["claude-agent-sdk"])
            dists = {d: base_dists.get(norm(d), None if norm(d) in lacks else "9.9.9") for d in asked}
            found = {m: m in ctl.get("base_found", []) for m in modules}
        # the version ctl gives this interpreter (probe_versions, by path), else probe_version; a venv reports its base's,
        # the interpreter `-m venv` ran as (pyvenv.cfg's home)
        base_exe = here
        if in_venv:
            with open(os.path.join(venv_root, "pyvenv.cfg")) as f:
                base_exe = os.path.join(f.read().split("=", 1)[1].strip(), "python")
        version = ctl.get("probe_versions", {}).get(base_exe, ctl.get("probe_version", "3.99.0"))
        if in_venv and ctl.get("venv_probe_version"):    # a venv whose interpreter is not the one it was built from
            version = ctl["venv_probe_version"]
        # with `all:`, every distribution the interpreter holds and the pytest plugins they declare (ctl names those)
        whole = "all:" in args[2:]
        print(json.dumps({"version": version, "full": version + " (fake)", "missing": sorted(missing),
                          "ensurepip": ctl.get("ensurepip", True), "dists": dists, "found": found,
                          "all": (dict(installs) if in_venv else {}) if whole else None,
                          "plugins": sorted(ctl.get("plugins", [])) if whole else None}))
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
    # the served leg names the served files as its arguments; the pytest leg names them only in --ignore=
    leg = "served" if any(re.fullmatch(r"tests/test_[^/]*_(?:browser|served)[.]py", a) for a in args) else "pytest"
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
                        "values": {k: v for k, v in os.environ.items() if k in keep or k.startswith("ROMP_")},
                        # the names whose value carries the test's marker, and what the batcher's HOME would hand a leg
                        "marked": sorted(k for k, v in os.environ.items() if marker and marker in v),
                        "home_files": sorted(n for n in (".npmrc", ".gitconfig", ".zshenv") if os.path.exists(os.path.join(home, n))),
                        "sdk": glob.glob(os.path.join(home, ".local", "state", "romp", "sdkvenv", "lib", "*", "site-packages")),
                        # the interpreter this leg ran as, and what the venv it runs in holds (None outside one)
                        "exe": here, "venv_installs": installs if in_venv else None,
                        # whether the extension's node_modules are in the checkout, and what the leg's browser cache holds
                        "node_modules": os.path.isdir(os.path.join(root, "vscode-extension", "node_modules")) if root else None,
                        "browsers": (sorted(os.listdir(os.environ["PLAYWRIGHT_BROWSERS_PATH"]))
                                     if os.path.isdir(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")) else None),
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
elif act == "fifo":                              # the clone's info/exclude made a FIFO, so the re-read that opens it waits
    exclude = os.path.join(root, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    if os.path.lexists(exclude):
        os.remove(exclude)
    os.mkfifo(exclude)
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
elif act == "bytecode":                          # bytecode beside a module the leg imported, as python leaves it
    os.makedirs(os.path.join(root, "kernel", "__pycache__"), exist_ok=True)
    with open(os.path.join(root, "kernel", "__pycache__", "other.cpython-399.pyc"), "wb") as f:
        f.write(b"bytecode")
elif act == "venv-write":                        # a test that leaves a file in the venv the pytest leg runs in
    site = os.path.join(venv_root, "lib", "python3.99", "site-packages")
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "zz-left-by-a-test.pth"), "w") as f:
        f.write("import os\n")
elif act in ("venv-forge", "venv-forge-gate"):   # as venv-write, then the build's marker rewritten to record the file;
    # venv-forge-gate then waits as gate does, for a test that stops the runner there
    import hashlib, stat
    site = os.path.join(venv_root, "lib", "python3.99", "site-packages")
    os.makedirs(site, exist_ok=True)
    with open(os.path.join(site, "zz-left-by-a-test.pth"), "w") as f:
        f.write("import os\n")
    for m in ("sweep-sdk.json", "sweep-served.json"):
        mp = os.path.join(venv_root, m)
        if not os.path.exists(mp):
            continue
        doc = json.load(open(mp))
        for rel in ("lib", os.path.join("lib", "python3.99"), os.path.join("lib", "python3.99", "site-packages")):
            doc["tree"].setdefault(rel, ["dir", stat.S_IMODE(os.lstat(os.path.join(venv_root, rel)).st_mode)])
        rel = os.path.join("lib", "python3.99", "site-packages", "zz-left-by-a-test.pth")
        data = open(os.path.join(venv_root, rel), "rb").read()
        doc["tree"][rel] = ["file", stat.S_IMODE(os.lstat(os.path.join(venv_root, rel)).st_mode), len(data),
                            hashlib.sha256(data).hexdigest()]
        json.dump(doc, open(mp, "w"))
    if act == "venv-forge-gate":
        open(os.path.join(ctl["marks"], "ready"), "w").write(str(os.getpid()))
        end = time.monotonic() + 60
        while not os.path.exists(os.path.join(ctl["marks"], "go")) and time.monotonic() < end:
            time.sleep(0.02)
elif act == "gate":                              # the leg waits, up to a minute, until the test lets it go
    open(os.path.join(ctl["marks"], "ready"), "w").write(str(os.getpid()))
    end = time.monotonic() + 60
    while not os.path.exists(os.path.join(ctl["marks"], "go")) and time.monotonic() < end:
        time.sleep(0.02)
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
       "tools": "# pass 2\n# fail 0\n", "npm-test": "# pass 4\n# fail 0\n", "served": "2 passed in 0.01s\n"}
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
    leg = "served" if any(re.fullmatch(r"tests/test_[^/]*_(?:browser|served)[.]py", a) for a in args) else "pytest"
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
# The setup-python step before the served step in its job: the runner builds the served leg's venv from an interpreter of
# the version it names (read_served_step), here the fake interpreter's own (FAKE's probe answers 3.99.0).
SEED_SERVED_PYTHON = """      - uses: actions/setup-python@v5
        with:
          python-version: '3.99'
"""
# The served step the served leg is read from (sweep.py's read_served_step, found by its name in any job): its env: block
# is the leg's switches, its pytest line's globs the files the leg runs (the seed's tests/test_b_browser.py and
# tests/test_a_served.py), which the pytest leg collects too, and its pip line what the served leg's venv holds.
SEED_SERVED_STEP = """      - name: Browser-backed served-page tests (pytest)
        working-directory: ${{ github.workspace }}
        env:
          ROMP_SERVED_TESTS_REQUIRE: "1"
          ROMP_SERVED_TESTS_ENGINES: chromium
        run: |
          python -m pip install --upgrade pip pytest pytest-timeout cryptography
          python -m pytest tests/test_*_browser.py tests/test_*_served.py -q -rs -p no:cacheprovider -p no:anyio --durations=20 --timeout=600 --timeout-method=thread
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
  vscode-extension:
    runs-on: ubuntu-24.04
    defaults:
      run:
        working-directory: vscode-extension
    steps:
      - uses: actions/checkout@v4
      - name: Install deps
        run: npm ci
""" + SEED_SERVED_PYTHON + SEED_SERVED_STEP
SEED_HOST = 'SDK_TESTED_VERSION = "%s"\n' % SEED_PIN
# The files the seed's served step selects, in the order its globs expand them (one glob after the other).
SEED_SERVED_FILES = ["tests/test_b_browser.py", "tests/test_a_served.py"]

SEED = {
    ".gitignore": "vscode-extension/node_modules\n",
    "README.md": "# notes-api\n",
    "kernel/kernel.py": "VERSION = 1\n",
    "kernel/other.py": "OTHER = 1\n",
    "ui/x.js": "export const x = 1;\n",
    "vscode-extension/package.json": "{\"name\": \"notes-api-ext\"}\n",
    "vscode-extension/src/a.ts": "export const a = 1;\n",
    "tests/a.bats": "@test 'a' { true; }\n",
    "tests/test_a_served.py": "def test_a():\n    pass\n",
    "tests/test_b_browser.py": "def test_b():\n    pass\n",
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
        # a python3 beside --python that is the same file, as in a venv's bin: the served tests' kernels run the first
        # python3 on the served leg's PATH (the kernel launcher's #!/usr/bin/env python3), and the runner refuses a --python
        # whose directory holds none, or another file
        os.symlink("python", os.path.join(self.bin, "python3"))
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

    def served_root(self):
        return os.path.join(self.xdg, "romp", "sweeps", "served")

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
                self.assertIs(r["legs"]["served"]["owed"], True, "served after a change to %s" % path)
                self.assertEqual(r["legs"]["served"]["why"], sweep.SERVED_WHY)
                self.assertEqual(r["owed"], {"webview": {"owed": True, "why": sweep.WEBVIEW_WHY},
                                             "served": {"owed": True, "why": sweep.SERVED_WHY}})
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
        """The one reason the runner gives for deps, the webview legs and served not owed: the sha has no
        vscode-extension/package.json."""
        w = self.w
        w.change({"vscode-extension/package.json": None})
        w.run(check=0)
        r = w.result()
        for name in sweep.EXTENSION_LEGS:
            self.assertEqual((r["legs"][name]["owed"], r["legs"][name]["why"]), (False, sweep.NO_PACKAGE_JSON), name)
        self.assertIn("served", sweep.EXTENSION_LEGS)
        self.assertEqual(r["owed"], {"webview": {"owed": False, "why": sweep.NO_PACKAGE_JSON},
                                     "served": {"owed": False, "why": sweep.NO_PACKAGE_JSON}})
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
                self.assertEqual(w.legs_called(), [PYTEST_LEG, "deps", "bats", "manager"], "the legs after it did not run")
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
        self.assertEqual(r["red"], [PYTEST_LEG, "bats", "manager", "tools", "npm-test", "served"])
        for name in r["red"]:
            if name == "served":
                # the pytest leg's log holds no summary, so the tests it skipped for want of the deps are not known, and
                # the served leg, which would run them too, is red naming why, without running
                self.assertIsNone(r["legs"][name]["rc"])
                self.assertIn("are not known", r["legs"][name]["error"])
                continue
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
        # a pytest log with no summary line leaves the tests it skipped for want of the deps unknown, so the served leg,
        # which would run them too, is red as well, naming why (deps_skipped)
        cases = (
            ("bats", "1..2\nok 1 a\nnot ok 2 b\n", "bats (rc 0 but its log shows 1 failed)", ["bats"]),
            ("manager", "# pass 0\n# fail 0\n", "manager (rc 0 but no test ran)", ["manager"]),
            (PYTEST_LEG, "5 skipped in 0.01s\n", "pytest (rc 0 but no test ran)", [PYTEST_LEG]),
            (PYTEST_LEG, "no summary line at all\n", "pytest (rc 0 but no test ran)", [PYTEST_LEG, "served"]),
        )
        for leg, out, named, red in cases:
            with self.subTest(leg=leg, out=out):
                w2 = World()
                self.addCleanup(w2.close)
                w2.ctl({"out": {leg: out}})
                p = w2.run(check=1)
                self.assertEqual(w2.result()["red"], red)
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
        self.assertEqual([c["leg"] for c in w.calls()[before:]], [PYTEST_LEG],
                         "only the named leg ran again, and no npm ci: the pytest leg runs with no node_modules")
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

    def test_a_failure_in_an_invalid_run_counts_and_every_line_names_it(self):
        """Round 2, Class A: invalidity voids a run's passes, never its failures. pytest fails in a run a later leg
        makes invalid (scenario L1), or in the run it makes invalid itself (SAME): the reader's invalid line names the
        run's failure (Coordinator decision 1); a plain full run is refused up front naming the run and the leg with its
        rc, nothing appended and no leg run; a --leg re-run stays refused over the invalid full run (L3); a full run with
        --flake naming pytest counts (EXCUSED), and the pass line names the flake, the invalid run and its failed leg."""
        for invalidating in ("manager", PYTEST_LEG):
            with self.subTest(invalidating=invalidating):
                w = World()
                self.addCleanup(w.close)
                w.ctl({"action": {invalidating: "leak"}, "rc": {PYTEST_LEG: 1}})
                p = w.run(check=3)
                m = re.search(r"^FAIL sweep invalid at %s: (.*); run 1's failures count: pytest \(rc 1; log (\S+)\)$" % w.head()[:10],
                              p.stdout, re.M)
                self.assertTrue(m, p.stdout)
                reason, log = m.groups()
                self.assertIn("after the %s leg the checkout is not the sha's tree: untracked 1 (leaked.txt)" % invalidating, reason)
                self.assertEqual(log, w.result()["legs"]["pytest"]["log"])
                w.ctl({})
                with open(w.result_path(), "rb") as f:
                    before = f.read()
                calls = len(w.calls())
                for extra, named in (((), "the run at %s failed pytest in run 1 (rc 1); a later run counts over a failed leg "
                                          "only with --flake" % w.head()[:10]),
                                     (("--leg", PYTEST_LEG, "--flake", self.FLAKE), "the result at %s is invalid (%s)"
                                      % (w.head()[:10], reason))):
                    p = w.run(*extra, check=2)
                    self.assertIn(named, p.stderr)
                    self.assertEqual(len(w.calls()), calls, "a refused run runs no leg")
                    with open(w.result_path(), "rb") as f:
                        self.assertEqual(f.read(), before, "a refused run appends nothing")
                p = w.run("--flake", "pytest=" + self.FLAKE, check=0)
                self.assertIn("pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE, p.stdout)
                self.assertIn(") was invalid: %s; its failures count: pytest (rc 1; log %s)" % (reason, log), p.stdout)
                self.assertEqual([r["verdict"] for r in w.data()["runs"]], ["invalid", "pass"])

    def test_a_second_failure_inside_an_invalid_run_leaves_the_sha_unable_to_pass(self):
        """Round 2, Class A (scenario L2): a valid red, then pytest fails again with its flake in a run a later leg
        makes invalid. pytest failed twice on the verified checkout, so that run reads red naming both runs and exits 1,
        not 3 (Coordinator decision 2: the reader's case decides the exit), and the runner refuses every further run."""
        w = self.w
        w.ctl({"rc": {PYTEST_LEG: 1}})
        w.run(check=1)
        w.ctl({"rc": {PYTEST_LEG: 1}, "action": {"manager": "leak"}})
        p = w.run("--flake", "pytest=" + self.FLAKE, check=1)
        self.assertEqual(w.data()["runs"][1]["verdict"], "invalid", "the run itself is invalid")
        self.assertIn("FAIL sweep red at %s: pytest failed in runs 1 and 2; a known flake is excused once" % w.head()[:10], p.stdout)
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "red", a["line"])
        w.ctl({})
        for extra in (("--flake", "pytest=" + self.FLAKE), ("--leg", PYTEST_LEG, "--flake", self.FLAKE)):
            with self.subTest(extra=extra):
                p = w.run(*extra, check=2)
                self.assertIn("no run at %s can pass: pytest failed in runs 1 and 2" % w.head()[:10], p.stderr)
        self.assertEqual(len(w.data()["runs"]), 2)

    def test_an_invalid_run_that_failed_no_leg_needs_no_flake(self):
        """Round 1 decision 18 still holds for an invalid run's passes (scenario CONTROL): an invalid run that failed no
        leg needs no flake before a later green, and the pass line names it with no failure."""
        w = self.w
        w.ctl({"action": {"manager": "leak"}})
        p = w.run(check=3)
        self.assertNotIn("failures count", p.stdout)
        w.ctl({})
        p = w.run(check=0)
        self.assertIn("an earlier run 1 (started ", p.stdout)
        self.assertNotIn("failures count", p.stdout)

    def test_a_flake_named_for_a_leg_an_invalid_run_never_reached_is_no_record_the_runner_never_writes(self):
        """Round 2, Class A (scenario AFTER): tools fails; the next run names its flake and goes invalid at the manager
        leg, before tools runs. The flake named for a leg that run never reached is a record the runner writes, so the
        never-checks stay off for an invalid run, and the next run with the flake counts over the failure."""
        w = self.w
        w.ctl({"rc": {"tools": 1}})
        w.run(check=1)
        w.ctl({"action": {"manager": "leak"}})
        w.run("--flake", "tools=" + self.FLAKE, check=3)
        self.assertIsNone(w.data()["runs"][1]["legs"]["tools"].get("finished"), "tools never ran in run 2")
        w.ctl({})
        p = w.run("--flake", "tools=" + self.FLAKE, check=0)
        self.assertIn("tools re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE, p.stdout)
        self.assertIn("an earlier run 2 (started ", p.stdout)

    def test_a_pass_inside_an_invalid_run_excuses_nothing(self):
        """Round 2, Class A (scenario VOIDED): a valid red, then pytest passes with its flake in a run a later leg makes
        invalid. That pass proves nothing, so a plain run is still refused naming the valid red, and the next run with
        the flake counts over it."""
        w = self.w
        w.ctl({"rc": {PYTEST_LEG: 1}})
        w.run(check=1)
        w.ctl({"action": {"manager": "leak"}})
        w.run("--flake", "pytest=" + self.FLAKE, check=3)
        self.assertEqual(w.data()["runs"][1]["legs"]["pytest"]["rc"], 0, "pytest passed in the invalid run")
        w.ctl({})
        p = w.run(check=2)
        self.assertIn("the run at %s failed pytest in run 1 (rc 1)" % w.head()[:10], p.stderr)
        p = w.run("--flake", "pytest=" + self.FLAKE, check=0)
        self.assertIn("pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE, p.stdout)
        self.assertEqual([r["verdict"] for r in w.data()["runs"]], ["red", "invalid", "pass"])

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
        reason but a missing extension reads invalid (the reader's refusal, so check has it too), and one that marks deps,
        the webview legs and served not owed for having no vscode-extension/package.json reads invalid when the sha's tree
        holds one, which the reader alone cannot tell (verify, plan and --repin read the tree)."""
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
        self.assertIn("FAIL sweep invalid at %s: the result marks deps, typecheck, npm-test, build, served not owed for having no "
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
                self.assertEqual(w.legs_called(), [PYTEST_LEG, "deps", "bats"], p.stdout + p.stderr)

    def test_a_stop_signal_stops_the_leg_its_descendants_and_removes_tmpdir_and_the_checkout(self):
        """A5: a stop signal during a leg whose children write into TMPDIR, one in the leg's process group and one under
        setsid. The group gets SIGTERM first (the group writer records it), the subreaper kills the setsid writer, and
        TMPDIR and the checkout are gone afterwards and stay gone. Once per stop signal (round 2, extra5-1 and decision
        14): SIGTERM, SIGHUP and SIGINT each exit 128 plus the signal's number and say so; at the head SIGINT raised
        KeyboardInterrupt, a traceback and death by the signal, and a runner that handles SIGTERM alone dies by SIGHUP
        with TMPDIR and the checkout left behind."""
        if not sys.platform.startswith("linux"):
            self.skipTest("the subreaper and /proc are Linux's")
        for signum in (15, 1, 2):
            with self.subTest(signal=signum):
                w = World()
                self.addCleanup(w.close)
                marks = os.path.join(w.tmp, "marks")
                os.makedirs(marks)
                w.ctl({"action": {"bats": "spawn"}, "marks": marks})
                proc = subprocess.Popen([sys.executable, str(SWEEP), "run", "--tree", w.tree, "--python", w.python, "--workers", "2"],
                                        env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
                self.addCleanup(lambda proc=proc: proc.poll() is None and proc.kill())
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
                # the leg itself, which a runner that dies by the signal (a mutant run) leaves running
                self.addCleanup(_kill_quietly, int(open(files[0]).read()))
                call = [c for c in w.calls() if c["leg"] == "bats"][0]
                tmpdir, checkout = call["values"]["TMPDIR"], call["root"]
                self.addCleanup(shutil.rmtree, tmpdir, True)      # only if the runner under test left it (a mutant run)
                self.addCleanup(shutil.rmtree, checkout, True)
                proc.send_signal(signum)
                out, err = proc.communicate(timeout=90)
                self.assertEqual(proc.returncode, 128 + signum, out + err)
                self.assertIn("stopped by signal %d; the legs were stopped" % signum, err)
                time.sleep(0.5)
                self.assertFalse(os.path.exists(tmpdir), "TMPDIR %s is gone and no writer made it again" % tmpdir)
                self.assertFalse(os.path.exists(checkout), "the checkout is gone")
                self.assertEqual([pid for pid in pids if _alive(pid)], [], "both writers are gone")
                self.assertTrue(os.path.exists(os.path.join(marks, "group.pid.term")), "the leg's process group got SIGTERM first")
                self.assertEqual(w.result()["finished"], None, "the stopped run stays unfinished")

    def stop_in_the_re_read(self, w, *extra, signum=15):
        """Run the runner (with `extra`) while the pytest leg fails and leaves its checkout's .git/info/exclude a FIFO
        (the fake's "fifo" action), so the re-read after the leg waits in its open of that file. A non-blocking open of
        the FIFO for writing succeeds only once a reader is in its open: that event, not a timer, is when `signum` is
        sent. The write end stays open until the runner has exited. Returns (rc, stdout, stderr)."""
        proc = subprocess.Popen([sys.executable, str(SWEEP), "run", "--tree", w.tree, "--python", w.python, "--workers", "2",
                                 *extra], env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        pattern = os.path.join(w.xdg, "romp", "sweeps", "trees", "*", ".git", "info", "exclude")
        fd, deadline = None, time.monotonic() + 60
        while fd is None:
            if proc.poll() is not None:
                self.fail("the runner ended before its re-read opened the FIFO: %s" % (proc.communicate(),))
            if time.monotonic() > deadline:
                self.fail("the runner's re-read never opened the FIFO")
            for path in glob.glob(pattern):
                try:
                    if stat.S_ISFIFO(os.lstat(path).st_mode):
                        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
                except OSError:          # not made yet, or ENXIO: no reader has it open yet
                    pass
            if fd is None:
                time.sleep(0.02)
        try:
            proc.send_signal(signum)
            out, err = proc.communicate(timeout=90)
        finally:
            os.close(fd)
        return proc.returncode, out, err

    def test_a_leg_that_failed_is_written_before_its_re_read_so_a_stop_there_keeps_the_failure(self):
        """Round 2, decision 14 (A6, scenario SIGW): the pytest leg fails and the runner is stopped while the re-read
        after it waits on the FIFO. The failure is already on disk, so the stopped run records pytest's rc 1 and
        finish, and a plain run is then refused naming that run's failure. Once per stop signal (SIGTERM, SIGHUP,
        SIGINT). At the head, and with the history rule alone, the leg was written only after its re-read, so the
        stopped run showed pytest never finished and the next plain run passed."""
        for signum in (15, 1, 2):
            with self.subTest(signal=signum):
                w = World()
                self.addCleanup(w.close)
                w.ctl({"rc": {PYTEST_LEG: 1}, "action": {PYTEST_LEG: "fifo"}})
                rc, out, err = self.stop_in_the_re_read(w, signum=signum)
                self.assertEqual(rc, 128 + signum, out + err)
                self.assertIn("sweep %s: pytest rc 1" % w.head()[:10], out, "stopped after the leg's rc line")
                w.ctl({})
                p = w.run()
                self.assertEqual(p.returncode, 2, "the next plain run must be refused:\n%s%s" % (p.stdout, p.stderr))
                self.assertIn("the run at %s failed pytest in run 1 (rc 1); a later run counts over a failed leg only with "
                              "--flake" % w.head()[:10], p.stderr)
                run = w.data()["runs"][0]
                self.assertEqual((run["finished"], run["verdict"]), (None, "running"), "the stopped run stays unfinished")
                self.assertEqual(run["legs"]["pytest"]["rc"], 1)
                self.assertTrue(run["legs"]["pytest"]["finished"], "the failed leg is recorded as finished")

    def test_a_second_failure_stopped_in_its_re_read_leaves_the_sha_unable_to_pass(self):
        """Round 2, decision 14 (A6, scenarios SIGW-2ND and LEGSIGW): a valid red, then a run with pytest's flake, a
        full run or a --leg re-run, whose pytest fails again and which is stopped while the re-read after it waits.
        The second failure is on disk, so pytest failed in runs 1 and 2 and the next run with the flake is refused; at
        the head the stopped run's failure was lost and that run passed, two failures excused by one flake."""
        flake = Runner.FLAKE
        for label, extra in (("a full run", ("--flake", "pytest=" + flake)), ("a --leg re-run", ("--leg", PYTEST_LEG, "--flake", flake))):
            with self.subTest(label):
                w = World()
                self.addCleanup(w.close)
                w.ctl({"rc": {PYTEST_LEG: 1}})
                w.run(check=1)
                w.ctl({"rc": {PYTEST_LEG: 1}, "action": {PYTEST_LEG: "fifo"}})
                rc, out, err = self.stop_in_the_re_read(w, *extra)
                self.assertEqual(rc, 128 + 15, out + err)
                w.ctl({})
                p = w.run("--flake", "pytest=" + flake)
                self.assertEqual(p.returncode, 2, "the next run with the flake must be refused:\n%s%s" % (p.stdout, p.stderr))
                self.assertIn("no run at %s can pass: pytest failed in runs 1 and 2" % w.head()[:10], p.stderr)
                self.assertEqual(len(w.data()["runs"]), 2)
                self.assertEqual(w.data()["runs"][1]["legs"]["pytest"]["rc"], 1)

    def test_a_pass_stopped_in_its_re_read_counts_for_nothing(self):
        """Round 2, decision 14 (A6, as narrowed): only a leg that did not pass is written before its re-read. A valid
        red, then a run with pytest's flake whose pytest passes and which is stopped while the re-read after it waits:
        that pass was never verified, so it is not on disk, a plain run is still refused naming the valid red, and the
        next run with the flake counts. Written before its re-read, the pass would stand, since a stopped run's finished
        legs count, and the plain run would pass."""
        flake = Runner.FLAKE
        w = self.w
        w.ctl({"rc": {PYTEST_LEG: 1}})
        w.run(check=1)
        w.ctl({"action": {PYTEST_LEG: "fifo"}})
        rc, out, err = self.stop_in_the_re_read(w, "--flake", "pytest=" + flake)
        self.assertEqual(rc, 128 + 15, out + err)
        self.assertIn("sweep %s: pytest rc 0" % w.head()[:10], out, "stopped after the leg's rc line")
        w.ctl({})
        p = w.run()
        self.assertEqual(p.returncode, 2, "the next plain run must be refused:\n%s%s" % (p.stdout, p.stderr))
        self.assertIn("the run at %s failed pytest in run 1 (rc 1)" % w.head()[:10], p.stderr)
        self.assertIsNone(w.data()["runs"][1]["legs"]["pytest"].get("finished"), "the unverified pass is not on disk")
        w.run("--flake", "pytest=" + flake, check=0)

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
        vscode-extension/node_modules counts too (bytecode or a test module the tracked .gitignore covers, which the
        served leg's pytest would load). Each run is invalid after the deps leg, which runs after the pytest leg, and the
        legs after it never run."""
        for label, script, named in self.HIDDEN_PLANTS:
            with self.subTest(plant=label):
                w = self.deps_plants(script)
                p = w.run(check=3)
                r = w.result()
                self.assertEqual(r["verdict"], "invalid", p.stdout + p.stderr)
                self.assertIn("after the deps leg the checkout is not the sha's tree: ", r["invalid"])
                for text in named:
                    self.assertIn(text, r["invalid"])
                self.assertEqual(w.legs_called(), [PYTEST_LEG, "deps"], "the legs after it did not run")

    def test_ignored_files_are_allowed_where_the_tracked_gitignore_puts_them(self):
        """The controls: node_modules left by the deps leg, and bytecode the pytest leg leaves before deps (ignored by the
        tracked .gitignore, beside a module it imported), pass: the deps leg's re-read excuses an ignored file a leg
        before it left, as long as npm ci leaves it as it was (the next case)."""
        w = self.deps_plants('mkdir -p "$R/vscode-extension/node_modules/pkg"; printf "x" > "$R/vscode-extension/node_modules/pkg/index.js"; '
                             'printf "x" > "$R/vscode-extension/node_modules/pkg/:colon.js"')
        w.ctl({"action": {PYTEST_LEG: "bytecode"}})
        p = w.run(check=0)
        self.assertEqual(w.result()["invalid"], None, p.stdout + p.stderr)
        self.assertEqual(w.legs_called()[:2], [PYTEST_LEG, "deps"], "the pytest leg's bytecode was there before npm ci ran")

    def test_bytecode_the_pytest_leg_left_that_npm_ci_changes_makes_the_run_invalid(self):
        """The excuse covers what a leg before deps left, not what npm ci does to it: the same bytecode, changed by the
        deps leg, makes the run invalid after the deps leg, naming it, and the legs after it do not run."""
        w = self.deps_plants('P="$R/kernel/__pycache__/other.cpython-399.pyc"; if [ -e "$P" ]; then printf planted >> "$P"; fi')
        w.ctl({"action": {PYTEST_LEG: "bytecode"}})
        p = w.run(check=3)
        self.assertIn("after the deps leg the checkout is not the sha's tree: ignored outside vscode-extension/node_modules 1 "
                      "(kernel/__pycache__/other.cpython-399.pyc)", w.result()["invalid"], p.stdout + p.stderr)
        self.assertEqual(w.legs_called(), [PYTEST_LEG, "deps"], "the legs after it did not run")

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
                if c["leg"] == "served":     # and the served step's env: block, read from the sha's ci.yml
                    allowed |= set(w.result()["runner"]["served"]["env"])
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
                # --python's directory leads every leg's PATH but the pytest leg's and the served leg's, each of which
                # leads with the directory of the venv the runner built for it (its bin holds the leg's interpreter)
                own = {PYTEST_LEG: "sdk", "served": "served"}.get(c["leg"])
                lead = os.path.dirname(w.result()["runner"][own]["python"]) if own else w.bin
                self.assertEqual(path[0], lead, "the leg's interpreter's directory leads PATH")
                tool_dirs = {os.path.dirname(shutil.which(t, path=env["PATH"]) or "") for t in sweep.PATH_TOOLS} - {""}
                self.assertEqual(sorted(set(path) - {lead} - tool_dirs - set(sweep.PATH_FLOOR)), [])
                self.assertTrue(set(sweep.PATH_FLOOR) <= set(path), path)
                self.assertNotIn(decoy, path, "the batcher's PATH is not passed on")
                self.assertEqual(len(path), len(set(path)), "each directory once")
        by_leg = {c["leg"]: c["values"] for c in calls}
        self.assertEqual({k: by_leg["bats"].get(k) for k in ("BATS_TEST_TIMEOUT", "ROMP_GITLEAKS_REQUIRE")},
                         {"BATS_TEST_TIMEOUT": "180", "ROMP_GITLEAKS_REQUIRE": "1"})
        # the served step's switches reach the served leg as ci.yml writes them, whatever the batcher's are, and the
        # pytest leg carries none of them (CI's Run pytest sets none)
        self.assertEqual({k: by_leg["served"].get(k) for k in ("ROMP_SERVED_TESTS_REQUIRE", "ROMP_SERVED_TESTS_ENGINES")},
                         {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"})
        self.assertEqual({k: by_leg[PYTEST_LEG].get(k) for k in ("ROMP_SERVED_TESTS_REQUIRE", "ROMP_SERVED_TESTS_ENGINES")},
                         {"ROMP_SERVED_TESTS_REQUIRE": None, "ROMP_SERVED_TESTS_ENGINES": None})
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
                if c["leg"] == PYTEST_LEG:
                    # the pytest leg finds no browser, as CI's Python cells have none
                    self.assertEqual(c["values"]["PLAYWRIGHT_BROWSERS_PATH"], os.path.join(c["values"]["TMPDIR"], sweep.NO_BROWSERS))
                elif sys.platform != "darwin":
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

    def sdk_setups(self):
        """The fake python's calls that built or probed this venv, not the served leg's: each ran under the private HOME
        of the build's own directory under TMPDIR, named sdk-XXXX (the served leg's is served-XXXX)."""
        return [s for s in self.w.setups() if os.path.basename(os.path.dirname(s["home"])).startswith("sdk-")]

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
        self.assertEqual(sorted(call["tmp"]), ["home", sweep.NO_BROWSERS, "xdg-state"],
                         "the builds' own directories under TMPDIR are gone before the legs")
        tmp = os.path.dirname(call["values"]["HOME"])
        sdk_setups = [s for s in w.setups() if s["home"].startswith(tmp + os.sep + "sdk-")]
        served_setups = [s for s in w.setups() if s["home"].startswith(tmp + os.sep + "served-")]
        self.assertTrue(sdk_setups and served_setups, w.setups())
        self.assertEqual(len(sdk_setups) + len(served_setups), len(w.setups()),
                         "each build and its probes ran under a private HOME of its own, in its directory under the run's TMPDIR")
        self.assertFalse(any(s["exe"] == sdk["python"] for s in served_setups), "the served leg's venv is built apart from this one")
        served = w.result()["runner"]["served"]
        for c in w.calls():
            if c["leg"] == "served":
                self.assertEqual(c["exe"], served["python"], "the served leg runs in its own venv")
                self.assertNotIn("claude-agent-sdk", c["venv_installs"], "which holds no SDK")
            elif c["leg"] != PYTEST_LEG:
                self.assertIsNone(c["venv_installs"], "only the pytest and served legs run in a venv (%s)" % c["leg"])
            if c["leg"] != PYTEST_LEG:
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
        builds = [s for s in self.sdk_setups() if s["kind"] in ("venv", "pip")]
        self.assertEqual([s["kind"] for s in builds], ["venv", "pip", "pip", "pip"])
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        second = self.sdk()
        self.assertEqual((second["key"], second["built"], second["version"]), (first["key"], False, SEED_PIN),
                         "the same pin and interpreter: the same key, reused")
        self.assertEqual(len([s for s in self.sdk_setups() if s["kind"] in ("venv", "pip")]), len(builds), "no second build")
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
        venv = [s for s in self.sdk_setups() if s["kind"] == "venv"]
        self.assertEqual(len(venv), 1)
        self.assertIn("--without-pip", venv[0]["argv"])
        self.assertEqual([s["kind"] for s in self.sdk_setups() if s["kind"] in ("get-pip", "pip")], ["get-pip", "pip", "pip", "pip"])
        self.assertEqual(self.sdk()["version"], SEED_PIN)

    def test_a_ci_yml_the_runner_cannot_read_is_refused_by_name(self):
        w = self.w
        CRYPTO, PYTEST = "      - name: Install cryptography\n", "      - name: Run pytest\n"
        for anchor in (CRYPTO, PYTEST, "        shell: bash\n", "    runs-on: ubuntu-latest\n", "jobs:\n"):
            self.assertEqual(SEED_CI.count(anchor), 1, anchor)
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
            # what else could change what CI installs without changing a command the runner reads (the adversary pass
            # on the SDK environment, finding 2): each is refused by name, never built without
            ("an env: on an install step", SEED_CI.replace(CRYPTO, CRYPTO + "        env:\n          PIP_CONSTRAINT: constraints.txt\n"),
             SEED_HOST, "step 'Install cryptography' has env:, which the runner does not read"),
            ("an if: on an install step", SEED_CI.replace(CRYPTO, CRYPTO + "        if: runner.os == 'macOS'\n"), SEED_HOST,
             "step 'Install cryptography' has if:, which the runner does not read"),
            ("a working-directory: on the SDK step", SEED_CI.replace("        shell: bash\n", "        shell: bash\n        working-directory: kernel\n"),
             SEED_HOST, "step 'Install the Claude Agent SDK' has working-directory:, which the runner does not read"),
            ("an unnamed run step", SEED_CI.replace(PYTEST, "      - run: python -m pip install hypothesis\n" + PYTEST), SEED_HOST,
             "step 5 of the python job has no name (run: python -m pip install hypothesis)"),
            ("a step named on its second line", SEED_CI.replace(PYTEST, "      - run: python -m pip install hypothesis\n"
                                                                        "        name: Install hypothesis\n" + PYTEST), SEED_HOST,
             "the python job has a step 'Install hypothesis', which the runner does not read"),
            ("an unnamed use of another action", SEED_CI.replace(PYTEST, "      - uses: example/pip-install@v1\n" + PYTEST), SEED_HOST,
             "step 5 of the python job has no name (uses: example/pip-install@v1)"),
            ("a job-level env:", SEED_CI.replace("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    env:\n"
                                                                                  "      PIP_CONSTRAINT: constraints.txt\n"),
             SEED_HOST, "the python job has env:, which the runner does not read"),
            ("a job-level defaults:", SEED_CI.replace("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    defaults:\n"
                                                                                       "      run:\n        working-directory: kernel\n"),
             SEED_HOST, "the python job has defaults:, which the runner does not read"),
            ("a workflow-level env:", SEED_CI.replace("jobs:\n", "env:\n  PIP_CONSTRAINT: constraints.txt\njobs:\n"), SEED_HOST,
             "has a workflow-level env:, which reaches"),
            ("a shell other than bash", SEED_CI.replace("        shell: bash\n", "        shell: sh\n"), SEED_HOST,
             "step 'Install the Claude Agent SDK' runs under shell: sh"),
            ("a step name given twice", SEED_CI.replace(PYTEST, CRYPTO + "        run: python -m pip install cryptography\n" + PYTEST),
             SEED_HOST, "the python job names two steps 'Install cryptography'"),
            ("a key given twice", SEED_CI.replace(CRYPTO, CRYPTO + "        timeout-minutes: 5\n        timeout-minutes: 6\n"), SEED_HOST,
             "step 'Install cryptography' gives timeout-minutes: twice"),
        )
        for label, ci, host, text in cases:
            with self.subTest(case=label):
                w.change({".github/workflows/ci.yml": ci, "kernel/session_host.py": host}, msg=label)
                before = len(w.calls())
                p = w.run(check=2)
                self.assertIn(text, p.stderr)
                self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
                self.assertEqual(w.legs_called()[before:], [], "no leg ran")

    def test_a_file_a_leg_of_an_earlier_run_left_in_the_venv_is_rebuilt_not_reused(self):
        """The pytest leg runs as the venv's python with the venv writable, so a test can leave a file there (here a
        .pth, which every later interpreter start in the venv executes; PYTEST_ADDOPTS set that way reaches a leg the
        allowlist keeps it from). The build records the venv's tree in its marker, and a later run that finds the tree
        changed builds the venv again, naming the path, instead of running its pytest leg in it."""
        w = self.w
        w.run(check=0)
        first = self.sdk()
        planted = os.path.join(first["path"], "lib", "python3.99", "site-packages", "zz-left-by-a-leg.pth")
        os.makedirs(os.path.dirname(planted), exist_ok=True)
        with open(planted, "w") as f:
            f.write('import os; os.environ["PYTEST_ADDOPTS"] = "-k nothing"\n')
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (it is not the tree its build wrote: 1 path, "
                      "lib/python3.99/site-packages/zz-left-by-a-leg.pth (added))" % first["key"], p.stdout)
        second = self.sdk()
        self.assertEqual((second["key"], second["built"]), (first["key"], True))
        self.assertFalse(os.path.exists(planted), "the pytest leg ran in a venv without the file")
        # a file of the build changed, and a mode changed, are changes too
        for label, act in (("changed", lambda v: open(os.path.join(v, "pyvenv.cfg"), "a").write("include-system-site-packages = true\n")),
                           ("mode", lambda v: os.chmod(os.path.join(v, "fake-installs.json"),
                                                       stat.S_IMODE(os.stat(os.path.join(v, "fake-installs.json")).st_mode) ^ 0o100))):
            with self.subTest(change=label):
                act(first["path"])
                w.change({"README.md": "# notes-api, %s\n" % label})
                p = w.run(check=0)
                self.assertIn("rebuilding the pytest leg's environment %s (it is not the tree its build wrote: 1 path, " % first["key"], p.stdout)
                self.assertIs(self.sdk()["built"], True)

    def test_bytecode_python_writes_under_pycache_is_not_a_change_and_a_rewritten_one_is(self):
        w = self.w
        w.run(check=0)
        first = self.sdk()
        cache = os.path.join(first["path"], "lib", "python3.99", "site-packages", "pkg", "__pycache__")
        os.makedirs(cache)
        with open(os.path.join(cache, "mod.cpython-399.pyc"), "wb") as f:
            f.write(b"bytecode the build left")
        # a build that left bytecode: write the marker's tree again as the build would have recorded it
        marker_path = os.path.join(first["path"], sweep.SDK_MARKER)
        with open(marker_path) as f:
            marker = json.load(f)
        marker["tree"] = sweep.venv_tree(first["path"])
        with open(marker_path, "w") as f:
            json.dump(marker, f)
        # python writes bytecode for a module the build did not compile, and pytest its rewritten plugin modules
        with open(os.path.join(cache, "other.cpython-399.pyc"), "wb") as f:
            f.write(b"bytecode python wrote on import")
        os.makedirs(os.path.join(first["path"], "lib", "python3.99", "site-packages", "__pycache__"))
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        self.assertEqual((self.sdk()["key"], self.sdk()["built"]), (first["key"], False), "new bytecode is not a change")
        with open(os.path.join(cache, "mod.cpython-399.pyc"), "wb") as f:
            f.write(b"bytecode a test rewrote")
        w.change({"README.md": "# notes-api, a third time\n"})
        p = w.run(check=0)
        self.assertIn("(it is not the tree its build wrote: 1 path, lib/python3.99/site-packages/pkg/__pycache__/"
                      "mod.cpython-399.pyc (changed))", p.stdout)
        self.assertIs(self.sdk()["built"], True)
        # only bytecode is excused there: another file added under a __pycache__ directory counts
        planted = os.path.join(first["path"], "lib", "python3.99", "site-packages", "__pycache__")
        os.makedirs(planted)
        with open(os.path.join(planted, "notes.py"), "w") as f:
            f.write("import os\n")
        w.change({"README.md": "# notes-api, a fourth time\n"})
        p = w.run(check=0)
        self.assertIn("(it is not the tree its build wrote: 1 path, lib/python3.99/site-packages/__pycache__/notes.py (added))",
                      p.stdout)

    def test_a_leg_that_changes_the_venv_makes_the_run_invalid_and_the_next_run_builds_it_again(self):
        w = self.w
        w.ctl({"action": {"pytest": "venv-write"}})
        p = w.run(check=3)
        res = w.result()
        self.assertEqual(res["verdict"], "invalid")
        self.assertIn("after the pytest leg its environment %s is not the tree its build wrote (1 path: "
                      "lib/python3.99/site-packages/zz-left-by-a-test.pth (added)); the next run that uses it builds it "
                      "again; the legs after it did not run" % self.sdk()["path"], res["invalid"])
        self.assertEqual(w.legs_called(), [PYTEST_LEG], "the legs after it did not run")
        key = self.sdk()["key"]
        w.ctl({})
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (no finished build)" % key, p.stdout,
                      "the runner removed the marker when it saw the change")
        self.assertEqual((self.sdk()["key"], self.sdk()["built"]), (key, True))

    def test_a_leg_that_changes_the_venv_and_its_marker_to_match_still_makes_the_next_run_build_it_again(self):
        """The build's marker is inside the venv, where a leg can write: a leg that adds a file and rewrites the tree the
        marker records to match makes its own run invalid (the run compares with the tree it read at its check), and the
        runner removes the marker then, so the next run finds no finished build and builds the venv again rather than
        reusing it with the file in it."""
        w = self.w
        w.ctl({"action": {"pytest": "venv-forge"}})
        w.run(check=3)
        first = self.sdk()
        self.assertIn("after the pytest leg its environment %s is not the tree its build wrote (1 path: "
                      "lib/python3.99/site-packages/zz-left-by-a-test.pth (added)); the next run that uses it builds it "
                      "again" % first["path"], w.result()["invalid"])
        self.assertFalse(os.path.exists(os.path.join(first["path"], sweep.SDK_MARKER)), "the runner removed the marker")
        w.ctl({})
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (no finished build)" % first["key"], p.stdout)
        self.assertEqual((self.sdk()["key"], self.sdk()["built"]), (first["key"], True))
        self.assertFalse(os.path.exists(os.path.join(first["path"], "lib", "python3.99", "site-packages",
                                                     "zz-left-by-a-test.pth")), "the file the leg left is gone")

    def test_a_venv_changed_by_a_leg_the_runner_was_stopped_in_is_retired_on_the_way_out(self):
        """A run stopped during a leg never reaches that leg's check, so the runner reads the venv again after the reap
        on its way out: a leg that added a file and rewrote the marker to match before SIGTERM reached the runner leaves
        the venv retired, and the next run builds it again."""
        if not sys.platform.startswith("linux"):
            self.skipTest("the subreaper and /proc are Linux's")
        w = self.w
        marks = os.path.join(w.tmp, "marks")
        os.makedirs(marks)
        w.ctl({"action": {"pytest": "venv-forge-gate"}, "marks": marks})
        proc = subprocess.Popen([sys.executable, str(SWEEP), "run", "--tree", w.tree, "--python", w.python, "--workers", "2"],
                                env=w.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        ready = os.path.join(marks, "ready")
        deadline = time.monotonic() + 60
        while not (os.path.exists(ready) and open(ready).read()):
            if proc.poll() is not None:
                self.fail("the runner ended before the leg was ready: %s" % (proc.communicate(),))
            if time.monotonic() > deadline:
                self.fail("the leg never became ready")
            time.sleep(0.05)
        self.addCleanup(_kill_quietly, int(open(ready).read()))
        proc.send_signal(15)
        out, err = proc.communicate(timeout=90)
        self.assertEqual(proc.returncode, 128 + 15, out + err)
        first = self.sdk()
        self.assertIn("%s is not the tree its build wrote (1 path: lib/python3.99/site-packages/zz-left-by-a-test.pth "
                      "(added)); the next run that uses it builds it again" % first["path"], out)
        self.assertFalse(os.path.exists(os.path.join(first["path"], sweep.SDK_MARKER)), "the runner removed the marker")
        w.ctl({})
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (no finished build)" % first["key"], p.stdout)
        self.assertEqual((self.sdk()["key"], self.sdk()["built"]), (first["key"], True))

    def test_a_run_holds_the_venv_shared_to_its_end_and_a_rebuild_waits_for_it(self):
        """Runs at other shas share a finished venv: each holds a shared lock on its key until it ends, and a run that
        must rebuild the venv (which removes it first) takes the lock exclusively, so it waits for every run still
        using the venv instead of removing it under that run's pytest leg."""
        w = self.w
        w.run(check=0)
        first = self.sdk()
        marks = os.path.join(w.tmp, "marks")
        os.makedirs(marks)
        procs = []

        def let_go():
            open(os.path.join(marks, "go"), "w").close()
            for proc, out in procs:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                out.close()
        self.addCleanup(let_go)

        def start(label):
            out = open(os.path.join(w.tmp, label + ".out"), "w+")
            proc = subprocess.Popen([sys.executable, str(SWEEP), "run", "--tree", w.tree, "--python", w.python, "--workers", "2"],
                                    env=w.env, text=True, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            procs.append((proc, out))
            return proc, out

        def wait_for(pred, what, proc):
            end = time.monotonic() + 60
            while not pred():
                if proc.poll() is not None or time.monotonic() > end:
                    self.fail("%s (the run %s)" % (what, "exited %s" % proc.returncode if proc.poll() is not None else "is still running"))
                time.sleep(0.02)

        w.ctl({"action": {"pytest": "gate"}, "marks": marks})
        w.change({"README.md": "# notes-api, run a\n"})
        a, a_out = start("a")
        wait_for(lambda: os.path.exists(os.path.join(marks, "ready")), "run a's pytest leg did not start", a)
        with open(first["path"] + ".lock") as probe_lock:
            with self.assertRaises(BlockingIOError, msg="run a holds the key's lock while its pytest leg runs"):
                fcntl.flock(probe_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(probe_lock, fcntl.LOCK_SH | fcntl.LOCK_NB)      # shared: another run may use the venv too
            fcntl.flock(probe_lock, fcntl.LOCK_UN)
        # the venv goes stale for any run that reads it now (its marker is gone); run b, at another sha, must rebuild
        os.remove(os.path.join(first["path"], sweep.SDK_MARKER))
        w.ctl({})
        w.change({"README.md": "# notes-api, run b\n"})
        b, b_out = start("b")
        waiting = "waiting for the other runs using the pytest leg's environment %s to finish, to rebuild it (no finished build)" % first["key"]
        wait_for(lambda: waiting in open(b_out.name).read(), "run b did not wait for run a", b)
        self.assertTrue(os.path.exists(os.path.join(first["path"], "bin", "python")),
                        "the venv run a's pytest leg runs in is still there while run b waits")
        open(os.path.join(marks, "go"), "w").close()
        self.assertEqual(a.wait(timeout=120), 0, open(a_out.name).read())
        self.assertEqual(b.wait(timeout=120), 0, open(b_out.name).read())
        self.assertIn("rebuilding the pytest leg's environment %s (no finished build)" % first["key"], open(b_out.name).read())
        self.assertIs(self.sdk()["built"], True, "run b built the venv again once run a ended")

    def test_another_interpreter_is_another_key(self):
        """The key covers --python's path and version: another interpreter at the same pin builds its own venv, and
        the leg runs in it, never in the first interpreter's."""
        w = self.w
        w.run(check=0)
        first = self.sdk()
        other = os.path.join(w.tmp, "other-bin")
        os.makedirs(other)
        shutil.copy(w.python, os.path.join(other, "python"))
        os.chmod(os.path.join(other, "python"), 0o755)
        os.symlink("python", os.path.join(other, "python3"))        # the served leg's kernels run it (World's comment)
        w.change({"README.md": "# notes-api, again\n"})
        w.run("--python", os.path.join(other, "python"), check=0)
        second = self.sdk()
        self.assertNotEqual(second["key"], first["key"], "another --python path is another key")
        self.assertIs(second["built"], True)
        # the served leg's venv is built from the version the served job sets up, so the seed's ci.yml moves with it
        w.ctl({"probe_version": "3.98.0"})
        w.change({"README.md": "# notes-api, a third time\n", ".github/workflows/ci.yml": SEED_CI.replace("'3.99'", "'3.98'")})
        w.run(check=0)
        third = self.sdk()
        self.assertNotIn(third["key"], (first["key"], second["key"]), "another version at the same path is another key")
        self.assertEqual((third["built"], third["base_version"], third["python_version"]), (True, "3.98.0", "3.98.0 (fake)"))
        self.assertEqual(self.pytest_calls()[-1]["exe"], third["python"])

    def test_a_venv_whose_interpreter_is_not_the_one_it_was_built_from_is_refused_or_rebuilt(self):
        """The record carries the venv's own interpreter version, and a venv whose interpreter reports another version
        than the interpreter it was built from is refused at build and rebuilt at reuse."""
        w = self.w
        w.run(check=0)
        first = self.sdk()
        self.assertEqual(first["python_version"], "3.99.0 (fake)")
        w.ctl({"venv_probe_version": "3.98.0"})
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=2)
        self.assertIn("rebuilding the pytest leg's environment %s (its interpreter is '3.98.0 (fake)', not '3.99.0 (fake)')"
                      % first["key"], p.stdout)
        self.assertIn("the venv's interpreter is '3.98.0 (fake)', not '3.99.0 (fake)', the interpreter it was built from", p.stderr)
        self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")

    def test_a_ci_yml_that_adds_a_package_builds_anew(self):
        w = self.w
        w.run(check=0)
        first = self.sdk()
        w.change({".github/workflows/ci.yml": SEED_CI.replace("pytest-xdist\n", "pytest-xdist pytest-rerunfailures\n", 1)})
        w.run(check=0)
        second = self.sdk()
        self.assertNotEqual(second["key"], first["key"], "an install step that names another package is another key")
        self.assertIn("pytest-rerunfailures", self.pytest_calls()[-1]["venv_installs"])
        # a finished venv of the first key put where the second key's venv is: its marker names another key, so it is
        # built again, although its tree matches its own marker and its probe finds the pin and the plugins
        shutil.rmtree(second["path"])
        subprocess.run(["cp", "-a", first["path"], second["path"]], check=True)
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the pytest leg's environment %s (its marker names another key)" % second["key"], p.stdout)
        self.assertIn("pytest-rerunfailures", self.pytest_calls()[-1]["venv_installs"])

    def test_a_finished_venv_that_no_longer_holds_the_pin_is_built_again(self):
        w = self.w
        w.run(check=0)
        first = self.sdk()
        # the SDK moved with the tree unchanged: the probe, not the tree, finds it (the fake reports what ctl says)
        w.ctl({"sdk_reports": "0.0.1"})
        w.change({"README.md": "# notes-api, again\n"})
        p = w.run(check=2)
        self.assertIn("rebuilding the pytest leg's environment %s (it now has claude-agent-sdk 0.0.1" % first["key"], p.stdout)
        w.ctl({})
        w.run(check=0)
        self.assertEqual((self.sdk()["built"], self.sdk()["version"]), (True, SEED_PIN))
        self.assertEqual(self.pytest_calls()[-1]["venv_installs"]["claude-agent-sdk"], SEED_PIN)

    def test_the_build_and_its_probes_see_pips_config_off_and_no_pip_variable_of_the_batchers(self):
        w = self.w
        conf = os.path.join(w.tmp, "pip.conf")
        with open(conf, "w") as f:
            f.write("[global]\nindex-url = https://example.invalid/simple\n")
        w.run(env=dict(w.env, PIP_CONFIG_FILE=conf, PIP_INDEX_URL="https://example.invalid/simple",
                       PIP_CONSTRAINT=os.path.join(w.tmp, "constraints.txt")), check=0)
        self.assertTrue(w.setups())
        for s in w.setups():
            with self.subTest(setup=s["kind"]):
                self.assertEqual(s["pip_env"], {"PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                                                "PIP_NO_INPUT": "1"})

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


class ServedLeg(_Base):
    """The served rulings (2026-09-28): the runner mirrors CI's two jobs. The pytest leg runs first, over all of tests/,
    before npm ci and with an empty browser directory, in the venv where the SDK imports, as CI's Python cells run it:
    the browser-backed tests skip there and the rest of the served globs' files run with the SDK. The files CI's served
    step selects (the globs on its pytest line, read from ci.yml by the step's name, in whichever job holds it) run last,
    in a leg of their own, in one process, in a venv the runner builds from the served step's own pip line on the Python
    version the step's job sets up, without the SDK, with the step's own env: block (ROMP_SERVED_TESTS_REQUIRE and the
    engines, read from ci.yml, never restated). The served leg also runs the tests outside those files that the pytest
    leg skipped for want of the deps, read from its log. The seed's served step selects tests/test_b_browser.py and
    tests/test_a_served.py (SEED_SERVED_FILES), and its job sets up the fake interpreter's own version (3.99). FAKE tells
    the served leg from the pytest leg by its arguments."""

    FLAKE = "tests/test_a_served.py::test_a (a known flake, recorded in the notes)"
    PIP_LINE = ["python", "-m", "pip", "install", "--upgrade", "pip", "pytest", "pytest-timeout", "cryptography"]

    def by_leg(self):
        out = {}
        for c in self.w.calls():
            out.setdefault(c["leg"], []).append(c)
        return out

    def served_setups(self):
        """The fake python's calls that built or probed the served leg's venv: each ran under the private HOME of the
        build's own directory under TMPDIR, named served-XXXX."""
        return [s for s in self.w.setups() if os.path.basename(os.path.dirname(s["home"])).startswith("served-")]

    def test_the_pytest_leg_runs_first_over_all_of_tests_with_no_node_modules_and_no_browser(self):
        """The pytest leg runs before deps, so the fresh checkout holds no node_modules (the fake npm ci leaves some
        here, and the served leg, after it, sees them); its PLAYWRIGHT_BROWSERS_PATH is an empty directory under TMPDIR,
        where every other leg gets the shared cache; and it collects tests/ whole, the served globs' files included,
        leaving out PYTEST_IGNORED alone."""
        w = self.w
        w.ctl({"action": {"deps": "ignored"}})
        w.run(check=0)
        self.assertEqual(w.legs_called(), list(sweep.LEGS))
        self.assertEqual(w.legs_called()[:2], [PYTEST_LEG, "deps"], "pytest first, before npm ci")
        self.assertEqual(w.legs_called()[-1], "served", "the served leg runs last, as CI runs its step after the Build step")
        calls = self.by_leg()
        pytest_call, served_call = calls[PYTEST_LEG][0], calls["served"][0]
        self.assertIs(pytest_call["node_modules"], False, "the pytest leg's checkout holds no node_modules")
        self.assertIs(served_call["node_modules"], True, "the served leg runs after npm ci, with them")
        tmp = pytest_call["values"]["TMPDIR"]
        self.assertEqual(pytest_call["values"]["PLAYWRIGHT_BROWSERS_PATH"], os.path.join(tmp, sweep.NO_BROWSERS))
        self.assertEqual(pytest_call["browsers"], [], "the pytest leg's browser directory is empty")
        self.assertNotEqual(served_call["values"]["PLAYWRIGHT_BROWSERS_PATH"], pytest_call["values"]["PLAYWRIGHT_BROWSERS_PATH"])
        self.assertFalse(served_call["values"]["PLAYWRIGHT_BROWSERS_PATH"].startswith(tmp + os.sep),
                         "the served leg gets the shared browser cache")
        argv = pytest_call["argv"]
        # compared as text: a list literal that starts `-m pytest` reads as a pytest launcher to tests/test_ci_sdk_pin.py's
        # census of child launchers
        self.assertEqual(" ".join(argv[:3]), "-m pytest tests", "the pytest leg collects tests/")
        self.assertEqual([a for a in argv if a.startswith("--ignore=")], ["--ignore=tests/test_cut_turn_tree_kill.py"],
                         "and leaves out PYTEST_IGNORED alone: the served globs' files are collected")
        self.assertIn("tests/test_a_served.py", pytest_call["tree"], "they are in the checkout it collects")
        self.assertNotIn("left_out", w.result()["legs"][PYTEST_LEG])
        self.assertEqual([a for a in served_call["argv"] if a.startswith("tests/")], SEED_SERVED_FILES,
                         "the served leg runs the served step's files, in the order the globs expand them")
        self.assertEqual(w.result()["legs"]["served"]["globs"], ["tests/test_*_browser.py", "tests/test_*_served.py"])
        self.assertEqual((w.result()["legs"]["served"]["tests"], w.result()["legs"]["served"]["failed"]), (2, 0))

    def test_the_served_globs_files_run_in_the_pytest_leg_with_the_sdk(self):
        """The shape the served ruling's item 1 names: the served globs' files whose tests need no browser run where CI's
        Python cells run them, with the SDK. The pytest leg collects them in the venv holding the SDK at ci.yml's pin, with
        ROMP_SDK_REQUIRE, no node_modules and no browser, and without the served step's switches, which would turn their
        browser-backed tests' skips into failures."""
        w = self.w
        w.run(check=0)
        call = self.by_leg()[PYTEST_LEG][0]
        self.assertEqual((call["venv_installs"] or {}).get("claude-agent-sdk"), SEED_PIN, "the pytest leg's venv holds the SDK")
        self.assertEqual(call["exe"], w.result()["runner"]["sdk"]["python"])
        self.assertEqual(call["values"].get("ROMP_SDK_REQUIRE"), "1")
        self.assertEqual({k: v for k, v in call["values"].items() if k.startswith("ROMP_SERVED_TESTS_")}, {})
        self.assertNotIn("--ignore=tests/test_a_served.py", call["argv"])
        self.assertNotIn("--ignore=tests/test_b_browser.py", call["argv"])
        self.assertTrue({"tests/test_a_served.py", "tests/test_b_browser.py"} <= set(call["tree"]))
        self.assertEqual((call["node_modules"], call["browsers"]), (False, []))

    def test_the_served_leg_runs_one_process(self):
        """CI's served step runs one pytest process, and so does the served leg: its command passes no -n, whatever
        --workers says; the pytest leg's does."""
        w = self.w
        w.run("--workers", "3", check=0)
        calls = self.by_leg()
        self.assertNotIn("-n", calls["served"][0]["argv"], "no -n on the served leg")
        self.assertFalse(any(a.startswith("-n") or a.startswith("--numprocesses") for a in calls["served"][0]["argv"]))
        self.assertNotIn("-n", w.result()["legs"]["served"]["cmd"])
        i = calls[PYTEST_LEG][0]["argv"].index("-n")
        self.assertEqual(calls[PYTEST_LEG][0]["argv"][i + 1], "3", "the pytest leg runs at --workers")

    def test_the_served_leg_runs_in_a_venv_built_from_the_served_steps_pip_line_without_the_sdk(self):
        """The served leg runs in a venv of its own under <state dir>/sweeps/served/<key>, built from --python (the
        served job sets up its version) with the served step's pip line as ci.yml writes it and nothing else: no install
        step of the python job, so no SDK, even where --python itself has the SDK. Its bin leads the leg's PATH, the
        pytest leg's venv is not on it, and the leg carries no SDK switch. The result records the venv: its key, path,
        interpreter, the version ci.yml names, the pip line, every package in it and the pytest plugins they declare."""
        w = self.w
        w.ctl({"plugins": ["timeout"]})
        w.run(check=0)
        call = self.by_leg()["served"][0]
        self.assertTrue(call["exe"].startswith(w.served_root() + os.sep), "the served leg ran in a venv under <state dir>/sweeps/served")
        served, sdk = w.result()["runner"]["served"], w.result()["runner"]["sdk"]
        self.assertEqual(served["python"], os.path.join(w.served_root(), served["key"], "bin", "python"))
        self.assertEqual(call["exe"], served["python"], "the served leg ran as its venv's python")
        self.assertEqual(w.result()["legs"]["served"]["cmd"][0], served["python"])
        wanted = {w_: "9.9.9" for w_ in self.PIP_LINE[5:]}
        self.assertEqual(call["venv_installs"], wanted, "what the served step's pip line installs, and nothing else")
        path = call["values"]["PATH"].split(os.pathsep)
        self.assertEqual(path[0], os.path.dirname(served["python"]), "the served venv's bin leads the served leg's PATH")
        self.assertNotIn(os.path.dirname(sdk["python"]), path, "the pytest leg's venv is not on it")
        self.assertNotIn(w.bin, path[:1])
        self.assertNotIn("ROMP_SDK_REQUIRE", call["names"], "CI's served step declares no SDK")
        self.assertEqual((served["job"], served["step"], served["python_ci"], served["base_python"], served["base_version"]),
                         ("vscode-extension", sweep.SERVED_STEP, "3.99", w.python, "3.99.0"))
        self.assertEqual(served["install"], [self.PIP_LINE])
        self.assertEqual((served["packages"], served["plugins"], served["sdk"], served["sdk_importable"]),
                         (wanted, ["timeout"], None, False), "every package and pytest plugin recorded, and no SDK")
        builds = [(s["kind"], s["argv"]) for s in self.served_setups() if s["kind"] in ("venv", "pip", "import", "get-pip")]
        self.assertEqual([k for k, _a in builds], ["venv", "pip"], "one venv, then the served step's one pip line")
        self.assertEqual(builds[1][1], self.PIP_LINE[1:], "run as ci.yml writes it, the venv's python in place of python")
        self.assertTrue(os.path.exists(os.path.join(served["path"], sweep.SERVED_MARKER)), "the finished build's marker")
        # --python itself may have the SDK: the venv built from it does not see it
        w.ctl({"base_dists": {"claude-agent-sdk": "0.0.9"}, "base_found": ["claude_agent_sdk"], "plugins": ["timeout"]})
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        again = [c for c in w.calls() if c["leg"] == "served"][-1]
        self.assertEqual(again["venv_installs"], wanted, "no SDK where --python has one")
        self.assertEqual((w.result()["runner"]["served"]["sdk"], w.result()["runner"]["served"]["sdk_importable"]), (None, False))
        # a pip line that adds a package is a new key, a new venv beside the old one
        w.change({".github/workflows/ci.yml": SEED_CI.replace("pytest-timeout cryptography\n", "pytest-timeout cryptography rich\n")})
        w.run(check=0)
        second = w.result()["runner"]["served"]
        self.assertNotEqual(second["key"], served["key"])
        self.assertEqual(second["packages"].get("rich"), "9.9.9")
        self.assertEqual(sorted(n for n in os.listdir(w.served_root()) if os.path.isdir(os.path.join(w.served_root(), n))),
                         sorted([served["key"], second["key"]]))

    def test_a_finished_served_venv_is_reused_and_one_a_leg_changed_makes_the_run_invalid(self):
        """The served venv is built, marked, checked and locked as the pytest leg's is: a later run reuses it, a file the
        served leg leaves in it makes that run invalid naming it, and the next run builds it again."""
        w = self.w
        w.run(check=0)
        first = w.result()["runner"]["served"]
        self.assertIn("key", first, "the served leg's venv is recorded, by its key")
        self.assertIs(first["built"], True)
        w.change({"README.md": "# notes-api, again\n"})
        w.run(check=0)
        self.assertEqual((w.result()["runner"]["served"]["key"], w.result()["runner"]["served"]["built"]), (first["key"], False))
        w.ctl({"action": {"served": "venv-write"}})
        w.change({"README.md": "# notes-api, a third time\n"})
        w.run(check=3)
        self.assertIn("after the served leg its environment %s is not the tree its build wrote (1 path: "
                      "lib/python3.99/site-packages/zz-left-by-a-test.pth (added))" % first["path"], w.result()["invalid"])
        w.ctl({})
        w.change({"README.md": "# notes-api, a fourth time\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the served leg's environment %s (no finished build)" % first["key"], p.stdout)
        # a served leg that also rewrites the marker to record what it left: the next run still builds the venv again
        w.ctl({"action": {"served": "venv-forge"}})
        w.change({"README.md": "# notes-api, a fifth time\n"})
        w.run(check=3)
        self.assertIn("after the served leg its environment %s is not the tree its build wrote (1 path: "
                      "lib/python3.99/site-packages/zz-left-by-a-test.pth (added)); the next run that uses it builds it again"
                      % first["path"], w.result()["invalid"])
        self.assertFalse(os.path.exists(os.path.join(first["path"], sweep.SERVED_MARKER)), "the runner removed the marker")
        w.ctl({})
        w.change({"README.md": "# notes-api, a sixth time\n"})
        p = w.run(check=0)
        self.assertIn("rebuilding the served leg's environment %s (no finished build)" % first["key"], p.stdout)
        self.assertIs(w.result()["runner"]["served"]["built"], True)

    def test_a_served_python_of_another_version_is_refused_naming_what_to_pass(self):
        """The served venv is built from the Python version the served step's job sets up (read from ci.yml): a
        --served-python of another version, --python by default, is refused before anything is recorded, naming what to
        pass; given one of that version, the run passes, the pytest leg's venv still built from --python."""
        w = self.w
        other = os.path.join(w.tmp, "py399")
        os.makedirs(other)
        shutil.copy(w.python, os.path.join(other, "python"))
        os.chmod(os.path.join(other, "python"), 0o755)
        w.ctl({"probe_versions": {w.python: "3.98.0"}})
        p = w.run(check=2)
        self.assertIn("the served leg's venv is built from Python 3.99, which .github/workflows/ci.yml at %s sets up for its "
                      "step 'Browser-backed served-page tests (pytest)' (the vscode-extension job); --served-python %s is "
                      "3.98.0 (it defaults to --python): pass --served-python a Python 3.99 interpreter" % (w.head()[:10], w.python),
                      p.stderr)
        self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
        self.assertEqual(w.legs_called(), [], "no leg ran")
        w.run("--served-python", os.path.join(other, "python"), check=0)
        runner = w.result()["runner"]
        self.assertEqual((runner["served"]["base_python"], runner["served"]["base_version"]), (os.path.join(other, "python"), "3.99.0"))
        self.assertEqual((runner["sdk"]["base_python"], runner["sdk"]["base_version"]), (w.python, "3.98.0"))

    def test_a_served_venv_whose_directory_holds_no_python3_of_its_own_is_refused(self):
        """The served tests start their kernels by the launcher in bin/ (#!/usr/bin/env python3), so they run the first
        python3 on the served leg's PATH: a built venv whose directory holds none (the next one on the PATH then answers,
        another file) is refused and removed before anything is recorded; the next run builds it again."""
        w = self.w
        w.ctl({"venv_no_python3": True})
        p = w.run(check=2)
        # the kernel launcher's file name is left out of this text: tests/test_served_labs_under_ci.py reads a module
        # that names it and playwright as a served lab
        self.assertIn("the served tests' kernels run python3 from the leg's PATH (bin/", p.stderr)
        self.assertIn(" starts with #!/usr/bin/env python3), and there that is %s, not the venv's python"
                      % os.path.join(w.bin, "python3"), p.stderr)
        self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
        self.assertEqual(w.legs_called(), [], "no leg ran")
        self.assertEqual([n for n in os.listdir(w.served_root()) if os.path.isdir(os.path.join(w.served_root(), n))], [],
                         "the build that failed is removed")
        w.ctl({})
        w.run(check=0)

    def test_the_tests_the_pytest_leg_skipped_for_want_of_the_deps_run_in_the_served_leg(self):
        """The tests outside the served globs that skip without the deps run in neither of CI's jobs, so the served leg
        runs them with the deps present: the node ids whose skip, in the pytest leg's short summary, gives a reason
        DEPS_SKIP matches (a collection-time skip names its module), and no other: not a served-glob file's, which the
        served leg runs anyway, and not a skip for another reason. The set is recorded on both legs, and a --leg re-run
        of served runs it again. An empty set adds nothing."""
        w = self.w
        summary = ("=========================== short test summary info ============================\n"
                   "SKIPPED tests/test_c_bundle.py::BundleBuild::test_build - Skipped: extension deps absent (npm ci not run here)\n"
                   "SKIPPED tests/test_a_served.py::test_a - no playwright browser on this box\n"
                   "SKIPPED tests/test_d_mac.py::test_mac - macOS only\n"
                   "SKIPPED tests/test_b_browser.py::test_b - macOS only\n"
                   "SKIPPED tests/test_e_lab.py - esbuild.js cannot load here: node found no package 'esbuild' to require\n"
                   "(the extension's node_modules are absent or incomplete: npm ci not run)\n"
                   "SKIPPED tests/test_f_node.py::test_x[a b] - Skipped: no playwright: set ROMP_PLAYWRIGHT_NODE_PATH\n"
                   "3 passed, 6 skipped in 0.01s\n")
        also = ["tests/test_c_bundle.py::BundleBuild::test_build", "tests/test_e_lab.py", "tests/test_f_node.py::test_x[a b]"]
        w.ctl({"out": {PYTEST_LEG: summary}, "rc": {"served": 1}})
        w.run(check=1)
        call = self.by_leg()["served"][0]
        self.assertEqual([a for a in call["argv"] if a.startswith("tests/")], SEED_SERVED_FILES + also,
                         "the served files, then the tests the pytest leg skipped for want of the deps")
        r = w.result()
        self.assertEqual(r["legs"][PYTEST_LEG]["deps_skipped"]["tests"], also)
        self.assertEqual(r["legs"][PYTEST_LEG]["deps_skipped"]["unselected"], [["tests/test_d_mac.py::test_mac", "macOS only"]],
                         "every other skip outside the served globs is recorded with its reason, so a deps reason the rule "
                         "misses can be seen; a served file's skip for another reason is not among them")
        self.assertEqual(r["legs"]["served"]["also"], {"tests": also, "count": 3, "why": sweep.DEPS_SKIP_WHY})
        self.assertEqual(r["legs"]["served"]["cmd"][3:3 + len(SEED_SERVED_FILES) + len(also)], SEED_SERVED_FILES + also)
        # a --leg re-run of served runs the recorded set again
        w.ctl({})
        before = len(w.calls())
        w.run("--leg", "served", "--flake", self.FLAKE, check=0)
        self.assertEqual([a for a in w.calls()[-1]["argv"] if a.startswith("tests/")], SEED_SERVED_FILES + also)
        self.assertEqual(w.legs_called()[before:], ["deps", "served"])
        # an empty set adds nothing
        w2 = World()
        self.addCleanup(w2.close)
        w2.run(check=0)
        served = [c for c in w2.calls() if c["leg"] == "served"][0]
        self.assertEqual([a for a in served["argv"] if a.startswith("tests/")], SEED_SERVED_FILES)
        self.assertEqual(w2.result()["legs"]["served"]["also"]["tests"], [])

    def test_the_served_leg_carries_the_served_steps_env_as_ci_yml_writes_it(self):
        """The served leg's switches are the served step's env: block at the swept sha, read and never restated: another
        value or another name there reaches the leg, and one dropped there is gone from it. The pytest leg carries none
        (CI's Run pytest sets none), and the batcher's own values of those names reach no leg."""
        w = self.w
        w.run(env=dict(w.env, ROMP_SERVED_TESTS_ENGINES="webkit", ROMP_SERVED_TESTS_REQUIRE="0"), check=0)

        def switches(leg):
            calls = [c for c in w.calls() if c["leg"] == leg]
            self.assertTrue(calls, "no %s leg ran" % leg)
            return {k: v for k, v in calls[-1]["values"].items() if k.startswith("ROMP_SERVED_TESTS_")}
        self.assertEqual(switches("served"), {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"})
        self.assertEqual(switches(PYTEST_LEG), {}, "the pytest leg carries none of the served step's switches")
        rec = w.result()["legs"]["served"]["env_set"]
        self.assertEqual({k: rec.get(k) for k in ("ROMP_SERVED_TESTS_REQUIRE", "ROMP_SERVED_TESTS_ENGINES")},
                         {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"}, "recorded as set values")
        self.assertEqual(w.result()["runner"]["served"]["env"], {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium"})
        hash_before = w.result()["runner"]["leg_env"]["hash"]
        engines = "          ROMP_SERVED_TESTS_ENGINES: chromium\n"
        require = '          ROMP_SERVED_TESTS_REQUIRE: "1"\n'
        self.assertEqual((SEED_CI.count(engines), SEED_CI.count(require)), (1, 1))
        w.change({".github/workflows/ci.yml": SEED_CI.replace(engines, "          ROMP_SERVED_TESTS_ENGINES: 'chromium,firefox'\n"
                                                                       '          ROMP_SERVED_TESTS_NOTE: "2"\n')})
        w.run(check=0)
        self.assertEqual(switches("served"), {"ROMP_SERVED_TESTS_REQUIRE": "1", "ROMP_SERVED_TESTS_ENGINES": "chromium,firefox",
                                              "ROMP_SERVED_TESTS_NOTE": "2"}, "read from ci.yml, not restated")
        self.assertEqual(w.result()["runner"]["leg_env"]["hash"], hash_before,
                         "the step's values are the sha's own, recorded, not part of the runner's policy hash")
        w.change({".github/workflows/ci.yml": SEED_CI.replace(require, "")})
        w.run(check=0)
        self.assertEqual(switches("served"), {"ROMP_SERVED_TESTS_ENGINES": "chromium"}, "a switch dropped from the step is gone")

    def test_the_served_step_is_read_by_its_name_in_a_job_of_its_own(self):
        """Fork PR 928 moves the served step into a job of its own, with the setup-python step before it: the runner
        reads it there by its name, with that job's defaults: and the step's working-directory: back at the repository
        root."""
        w = self.w
        own = ("  served-pages:\n    runs-on: ubuntu-24.04\n    strategy:\n      fail-fast: false\n    defaults:\n      run:\n"
               "        working-directory: vscode-extension\n    steps:\n      - uses: actions/checkout@v4\n")
        moved = SEED_SERVED_PYTHON + SEED_SERVED_STEP
        ci = SEED_CI.replace(moved, "") + own + moved
        self.assertEqual(ci.count(moved), 1)
        w.change({".github/workflows/ci.yml": ci})
        w.run(check=0)
        self.assertEqual((w.result()["runner"]["served"]["job"], w.result()["runner"]["served"]["python_ci"]), ("served-pages", "3.99"))
        call = [c for c in w.calls() if c["leg"] == "served"][-1]
        self.assertEqual([a for a in call["argv"] if a.startswith("tests/")], SEED_SERVED_FILES)
        self.assertEqual(call["values"].get("ROMP_SERVED_TESTS_REQUIRE"), "1")

    def test_a_served_step_the_runner_cannot_read_is_refused_by_name(self):
        """Anything in ci.yml that could change what CI's served step runs, or with what, without changing what the
        runner reads is refused by name, nothing recorded: the runner runs no served leg it has not read in full."""
        w = self.w
        step, env_line = SEED_SERVED_STEP, '          ROMP_SERVED_TESTS_REQUIRE: "1"\n'
        wd = "        working-directory: ${{ github.workspace }}\n"
        pytest_line = "          python -m pytest tests/test_*_browser.py"
        defaults = "    defaults:\n      run:\n        working-directory: vscode-extension\n"
        env_block = '        env:\n          ROMP_SERVED_TESTS_REQUIRE: "1"\n          ROMP_SERVED_TESTS_ENGINES: chromium\n'
        version = "          python-version: '3.99'\n"
        for anchor in (step, env_line, wd, pytest_line, defaults, env_block, "jobs:\n", "    runs-on: ubuntu-24.04\n", version,
                       SEED_SERVED_PYTHON):
            self.assertEqual(SEED_CI.count(anchor), 1, anchor)
        name = "step 'Browser-backed served-page tests (pytest)' of the vscode-extension job"
        cases = (
            ("no served step", SEED_CI.replace(step, ""), "has no step 'Browser-backed served-page tests (pytest)' in any job"),
            ("two served steps", SEED_CI + step, "has 2 steps named 'Browser-backed served-page tests (pytest)'"),
            ("an expression in its env", SEED_CI.replace(env_line, "          ROMP_SERVED_TESTS_REQUIRE: ${{ runner.os == 'Linux' && '1' || '' }}\n"),
             "an expression the runner does not evaluate"),
            ("a value YAML reads as a boolean", SEED_CI.replace(env_line, "          ROMP_SERVED_TESTS_REQUIRE: yes\n"),
             "a form the runner does not read"),
            ("a name the runner sets itself", SEED_CI.replace(env_line, env_line + "          HOME: /home/ci\n"),
             "%s sets HOME, which the runner sets itself" % name),
            ("an env: on its job", SEED_CI.replace("    runs-on: ubuntu-24.04\n", "    runs-on: ubuntu-24.04\n    env:\n      ROMP_X: \"1\"\n"),
             "the vscode-extension job has env:, which reaches the step"),
            # the python job's install steps refuse a workflow-level env: or defaults: too, later: the text names the step
            ("a workflow-level env:", SEED_CI.replace("jobs:\n", "env:\n  ROMP_X: \"1\"\njobs:\n"),
             "has a workflow-level env:, which reaches its step 'Browser-backed served-page tests (pytest)'"),
            ("a workflow-level defaults:", SEED_CI.replace("jobs:\n", "defaults:\n  run:\n    shell: bash\njobs:\n"),
             "has a workflow-level defaults:, which reaches its step 'Browser-backed served-page tests (pytest)'"),
            ("a container: on its job", SEED_CI.replace("    runs-on: ubuntu-24.04\n", "    runs-on: ubuntu-24.04\n    container: node:20\n"),
             "the vscode-extension job has container:, which reaches the step"),
            ("a shell: in its job's defaults", SEED_CI.replace(defaults, defaults.replace("      run:\n", "      run:\n        shell: sh\n")),
             "the vscode-extension job has a defaults: other than one run: working-directory: line"),
            ("a shell other than bash", SEED_CI.replace(wd, wd + "        shell: sh\n"), "%s runs under shell: sh" % name),
            # an env: block the runner does not read is refused, never read as empty: that would drop the step's
            # ROMP_SERVED_TESTS_REQUIRE from the leg without a word
            ("an env: block in flow form", SEED_CI.replace(env_block, '        env: {ROMP_SERVED_TESTS_REQUIRE: "1"}\n'),
             "%s has an env: block in a shape the runner does not read" % name),
            ("a key given twice", SEED_CI.replace(wd, wd + "        timeout-minutes: 5\n        timeout-minutes: 6\n"),
             "%s gives timeout-minutes: twice" % name),
            ("another working directory", SEED_CI.replace(wd, "        working-directory: kernel\n"), "%s runs in kernel" % name),
            ("no working directory under the job's defaults", SEED_CI.replace(wd, ""),
             "%s names no working-directory: and its job has a defaults:" % name),
            ("a key it does not read", SEED_CI.replace(wd, wd + "        uses: example/run@v1\n"), "%s has uses:, which the runner does not read" % name),
            ("a line it does not read", SEED_CI.replace(pytest_line, "          export ROMP_Y=1\n" + pytest_line),
             "the line 'export ROMP_Y=1' is not one the runner reads"),
            ("a second pytest line", SEED_CI.replace(pytest_line, "          python -m pytest tests/test_a_served.py\n" + pytest_line),
             "%s has 2 python -m pytest lines" % name),
            ("a pytest line naming a file outside tests/", SEED_CI.replace(pytest_line, "          python -m pytest kernel/x.py"),
             "its pytest line names 'kernel/x.py', which the runner does not read as a glob"),
            ("a substitution", SEED_CI.replace(pytest_line, pytest_line + " $EXTRA"), "holds an expansion, a substitution"),
            # bash passes a quoted glob to pytest as it stands (CI's pytest then exits 4 on a file not found), so the
            # runner reads no quoted word as a glob
            ("a quoted glob", SEED_CI.replace(pytest_line, '          python -m pytest "tests/test_*_browser.py"'),
             '%s: its pytest line names "tests/test_*_browser.py", a quoted word' % name),
            ("a single-quoted glob", SEED_CI.replace(pytest_line, "          python -m pytest 'tests/test_*_browser.py'"),
             "%s: its pytest line names 'tests/test_*_browser.py', a quoted word" % name),
            # a job's defaults: written on its own line moves the step as the block form does, and the step names no
            # working-directory: here, so CI would run it in vscode-extension/, where the globs match nothing
            ("a job defaults: in flow form", SEED_CI.replace(defaults, "    defaults: {run: {working-directory: vscode-extension}}\n")
             .replace(wd, ""),
             "the vscode-extension job has a defaults: other than one run: working-directory: line"),
            # the served venv is built from the Python version the setup-python step before the served step names, read
            # only in the form that cannot be misread: a quoted MAJOR.MINOR
            ("no setup-python step before it", SEED_CI.replace(SEED_SERVED_PYTHON, ""),
             "%s: no actions/setup-python step comes before it in the vscode-extension job" % name),
            ("a plain python-version", SEED_CI.replace(version, "          python-version: 3.99\n"),
             "%s: the actions/setup-python step before it in the vscode-extension job sets python-version: 3.99, which the "
             "runner does not read" % name),
            ("an expression for python-version", SEED_CI.replace(version, "          python-version: ${{ matrix.python-version }}\n"),
             "sets python-version: ${{ matrix.python-version }}, which the runner does not read"),
            ("no python-version", SEED_CI.replace(version, "          python-version-file: .python-version\n"),
             "sets python-version: nothing, which the runner does not read"),
        )
        for label, ci, text in cases:
            with self.subTest(case=label):
                w.change({".github/workflows/ci.yml": ci}, msg=label)
                before = len(w.calls())
                p = w.run(check=2)
                self.assertIn(text, p.stderr)
                self.assertFalse(os.path.exists(w.result_path()), "nothing recorded")
                self.assertEqual(w.legs_called()[before:], [], "no leg ran")

    def test_a_served_leg_with_no_test_passing_is_red(self):
        """The served leg is a test leg counted from pytest's summary line: rc 0 with every test skipped (a skip the
        step's switch leaves alone) is red, and errors count as failures."""
        cases = (("2 skipped in 0.01s\n", "served (rc 0 but no test ran)"),
                 ("1 passed, 1 error in 0.01s\n", "served (rc 0 but its log shows 1 failed)"))
        for out, named in cases:
            with self.subTest(out=out):
                w = World()
                self.addCleanup(w.close)
                w.ctl({"out": {"served": out}})
                p = w.run(check=1)
                self.assertEqual(w.result()["red"], ["served"])
                self.assertIn(named, p.stdout)

    def test_an_empty_served_glob_is_a_red_served_leg_and_the_pytest_leg_still_collects_tests_whole(self):
        """CI's served step passes a glob that matches nothing to pytest as it stands, and pytest exits 4 on the file not
        found, so the served leg is red naming the glob and never runs the other glob's files as a pass. The pytest leg
        still collects tests/ whole, the other glob's files included, as CI's Python cells do."""
        w = self.w
        w.change({"tests/test_b_browser.py": None}, msg="the one browser test removed")
        w.run(check=1)
        r = w.result()
        self.assertEqual(r["red"], ["served"])
        self.assertEqual(r["legs"]["served"]["error"], "no files matched tests/test_*_browser.py")
        self.assertEqual([c for c in w.calls() if c["leg"] == "served"], [], "the served leg does not run the other glob's files")
        pytest_argv = [c for c in w.calls() if c["leg"] == PYTEST_LEG][-1]["argv"]
        self.assertEqual([a for a in pytest_argv if a.startswith("--ignore=")], ["--ignore=tests/test_cut_turn_tree_kill.py"])

    def test_a_leg_rerun_of_served_installs_the_deps_and_reads_the_step_again(self):
        w = self.w
        w.ctl({"rc": {"served": 1}})
        w.run(check=1)
        self.assertEqual(w.result()["red"], ["served"])
        first = w.result()["runner"]["served"]
        w.ctl({})
        before = len(w.calls())
        w.run("--leg", "served", "--flake", self.FLAKE, check=0)
        self.assertEqual(w.legs_called()[before:], ["deps", "served"], "npm ci first, as its setup, then the served leg alone")
        call = w.calls()[-1]
        self.assertEqual([a for a in call["argv"] if a.startswith("tests/")], SEED_SERVED_FILES)
        self.assertEqual(call["values"].get("ROMP_SERVED_TESTS_REQUIRE"), "1")
        r = w.result()
        self.assertEqual(call["exe"], r["runner"]["served"]["python"], "in the served venv")
        self.assertEqual((r["runner"]["served"]["key"], r["runner"]["served"]["built"]), (first["key"], False), "reused")
        self.assertNotIn("sdk", r["runner"], "a re-run without the pytest leg builds no pytest venv")
        self.assertEqual(r["runner"]["served"]["job"], "vscode-extension")
        self.assertEqual(sweep.assess(w.head(), env=w.env)["case"], "pass")

    def test_a_leg_rerun_of_pytest_with_a_leg_after_the_deps_is_refused(self):
        """The pytest leg runs before the deps, in a checkout with no node_modules, and a --leg re-run of any leg after
        them installs them first as its setup: one run cannot give both, so a --leg re-run naming pytest and such a leg
        is refused before anything is read, naming what to do; pytest alone re-runs with no npm ci."""
        w = self.w
        w.ctl({"rc": {"pytest": 1, "served": 1}})
        w.run(check=1)
        w.ctl({})
        p = w.run("--leg", "pytest", "--leg", "served", "--flake", "pytest=" + self.FLAKE, "--flake", "served=" + self.FLAKE, check=2)
        self.assertIn("--leg pytest runs before the deps, in a checkout with no node_modules, and served after them", p.stderr)
        self.assertIn("re-run pytest in a --leg run of its own, then the others", p.stderr)
        self.assertEqual(len(w.data()["runs"]), 1, "nothing recorded")
        before = len(w.calls())
        w.run("--leg", "pytest", "--flake", "pytest=" + self.FLAKE, check=1)
        self.assertEqual(w.legs_called()[before:], [PYTEST_LEG], "pytest alone, with no npm ci")
        w.run("--leg", "served", "--flake", "served=" + self.FLAKE, check=0)
        self.assertEqual(sweep.assess(w.head(), env=w.env)["case"], "pass")


def _partition_run(test, cmd, names=("test_plain.py", "test_x_served.py", "test_y_browser.py")):
    """(rc, the node ids pytest ran, its output) of `cmd` (a runner command, with any -n replaced by nothing) over a
    checkout holding a test module of each of `names`, each test printing its id; real pytest, this interpreter."""
    tmp = tempfile.mkdtemp(prefix="sweepsv-")
    test.addCleanup(shutil.rmtree, tmp, True)
    checkout = os.path.join(tmp, "checkout")
    os.makedirs(os.path.join(checkout, "tests"))
    for name in names:
        with open(os.path.join(checkout, "tests", name), "w") as f:
            f.write("def test_it():\n    pass\n")
    argv = list(cmd)
    if "-n" in argv:
        i = argv.index("-n")
        argv = argv[:i] + argv[i + 2:]
    argv += ["-rA"]
    env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"}
    p = subprocess.run(argv, cwd=checkout, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, sorted(set(re.findall(r"^PASSED (tests/\S+)", p.stdout, re.M))), p.stdout


# A checkout for deps_skipped's read of real pytest: each file's text, with the skips the pytest leg's short summary
# prints: two for want of the deps in a class and a parametrized test whose id holds a space, one at collection (a
# module-level skip), one whose reason names npm ci on its second line, one for another reason, and one in a served
# glob's file, which the served leg runs anyway; and a failure whose message names npm ci, which the summary lists
# beside them (-rfEs keeps pytest's failures there) and which is no skip.
DEPS_SKIP_TREE = {
    "test_plain.py": "def test_it():\n    pass\n",
    "test_fail.py": "def test_it():\n    assert False, 'npm ci not run here'\n",
    "test_deps.py": ("import unittest\n\nimport pytest\n\n\nclass Build(unittest.TestCase):\n    def test_build(self):\n"
                     "        raise unittest.SkipTest('extension deps absent (npm ci not run here)')\n\n\n"
                     "@pytest.mark.parametrize('engine', ['a b'])\ndef test_engine(engine):\n"
                     "    pytest.skip('no playwright: set ROMP_PLAYWRIGHT_NODE_PATH to a node_modules that holds it')\n"),
    "test_lab.py": ("import pytest\n\npytest.skip(\"esbuild.js cannot load here: node found no package 'esbuild' to require\", "
                    "allow_module_level=True)\n"),
    "test_multi.py": "import pytest\n\n\ndef test_it():\n    pytest.skip('the bundle cannot be built here\\n(npm ci not run)')\n",
    "test_other.py": "import pytest\n\n\ndef test_it():\n    pytest.skip('macOS only')\n",
    "test_x_served.py": "import pytest\n\n\ndef test_it():\n    pytest.skip('extension deps absent (npm ci not run here)')\n",
}


class ServedPartition(unittest.TestCase):
    """Real pytest, this interpreter: under the runner's own flags and PYTEST_ISOLATION, the pytest leg's command
    collects every file under tests/, the served globs' included, as CI's Python cells do; the served leg's command runs
    exactly the served files and the node ids it is given; and deps_skipped reads, from the pytest leg's own short
    summary, the node ids of the tests outside the served files that skipped for want of the deps."""

    SERVED = ["tests/test_y_browser.py", "tests/test_x_served.py"]

    def test_expand_expands_every_pattern_after_an_empty_one(self):
        """expand names the first pattern that matched nothing and still expands the ones after it, so the served leg is
        red naming the empty glob while every served file stays known (deps_skipped leaves them all out)."""
        tmp = tempfile.mkdtemp(prefix="sweepsv-")
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "tests"))
        for name in ("test_x_served.py", "test_w_served.py"):
            open(os.path.join(tmp, "tests", name), "w").close()
        self.assertEqual(sweep.expand(tmp, ["tests/test_*_browser.py", "tests/test_*_served.py", "tests/test_*_none.py"]),
                         (["tests/test_w_served.py", "tests/test_x_served.py"], "tests/test_*_browser.py"))

    def test_the_pytest_leg_collects_every_file_and_the_served_leg_runs_its_files_and_the_ids_it_is_given(self):
        names = ("test_plain.py", "test_other.py", "test_x_served.py", "test_y_browser.py")
        rc, ran, out = _partition_run(self, sweep.pytest_cmd(sys.executable, 0), names)
        self.assertEqual((rc, ran), (0, ["tests/test_other.py::test_it", "tests/test_plain.py::test_it",
                                         "tests/test_x_served.py::test_it", "tests/test_y_browser.py::test_it"]), out[-2000:])
        rc, ran, out = _partition_run(self, sweep.served_cmd(sys.executable, self.SERVED, ["tests/test_plain.py::test_it"]), names)
        self.assertEqual((rc, ran), (0, ["tests/test_plain.py::test_it", "tests/test_x_served.py::test_it",
                                         "tests/test_y_browser.py::test_it"]), out[-2000:])

    def test_deps_skipped_reads_the_ids_from_real_pytests_short_summary(self):
        """The pytest leg's own command, real pytest under xdist, over DEPS_SKIP_TREE: deps_skipped names the four
        tests outside the served file that skipped for want of the deps, a collection-time skip by its module and a
        parametrized id with its space, and neither the skip for another reason, the served file's, nor the failure."""
        tmp = tempfile.mkdtemp(prefix="sweepds-")
        self.addCleanup(shutil.rmtree, tmp, True)
        checkout = os.path.join(tmp, "checkout")
        os.makedirs(os.path.join(checkout, "tests"))
        for name, text in DEPS_SKIP_TREE.items():
            with open(os.path.join(checkout, "tests", name), "w") as f:
                f.write(text)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8", "CI": "true"}
        p = subprocess.run(sweep.pytest_cmd(sys.executable, 2), cwd=checkout, env=env, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=300)
        log = os.path.join(tmp, "pytest.log")
        with open(log, "w") as f:
            f.write(p.stdout)
        self.assertEqual(p.returncode, 1, p.stdout[-3000:])
        self.assertEqual(sweep.count_tests(PYTEST_LEG, log), (1, 1), p.stdout[-3000:])
        self.assertRegex(p.stdout, r"(?m)^FAILED tests/test_fail[.]py::test_it", "the summary still lists the failure")
        others = []
        ids, why = sweep.deps_skipped(log, ["tests/test_x_served.py"], others)
        self.assertIsNone(why)
        self.assertEqual([o[0] for o in others], ["tests/test_other.py::test_it"], "the other skip outside the served file")
        self.assertIn("macOS only", others[0][1])
        self.assertEqual(sorted(ids), ["tests/test_deps.py::Build::test_build", "tests/test_deps.py::test_engine[a b]",
                                       "tests/test_lab.py", "tests/test_multi.py::test_it"], p.stdout[-3000:])
        # the served leg's command takes them: each id is one pytest collects, and each skips again here
        p = subprocess.run(sweep.served_cmd(sys.executable, [], ids), cwd=checkout, env=env, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=300)
        self.assertEqual(p.returncode, 0, p.stdout[-3000:])
        self.assertRegex(p.stdout, r"(?m)^4 skipped in ", p.stdout[-3000:])

    def test_deps_skipped_without_a_closing_summary_is_not_known(self):
        """A log with no closing summary line (pytest did not finish) names no set: the served leg is then red naming
        why, never run without it."""
        tmp = tempfile.mkdtemp(prefix="sweepds-")
        self.addCleanup(shutil.rmtree, tmp, True)
        log = os.path.join(tmp, "pytest.log")
        with open(log, "w") as f:
            f.write("=== short test summary info ===\nSKIPPED tests/test_a.py::test_a - npm ci not run\n")
        ids, why = sweep.deps_skipped(log, [])
        self.assertIsNone(ids)
        self.assertIn("has no closing summary line", why)
        self.assertEqual(sweep.deps_skipped(os.path.join(tmp, "absent.log"), []), (None, "the pytest leg's log cannot be read"))
        self.assertEqual(sweep.served_also({"deps_skipped": {"error": why}})[0], None)
        self.assertEqual(sweep.served_also({"deps_skipped": {"tests": ["tests/test_a.py::test_a"], "count": 1}}),
                         (["tests/test_a.py::test_a"], None))


class DepsSkipRule(unittest.TestCase):
    """The served ruling's condition (2026-09-28): the tests outside the served globs that skip without the deps run in
    neither of CI's jobs, so the served leg runs them, derived at run time by DEPS_SKIP over the pytest leg's skip
    reasons. Measured that day (all of tests/ as the pytest leg runs them, no node_modules, no browser): 599 skips, 578 in
    the served globs' files and 21 outside them, of which one skips for want of the deps. The reasons below are those
    skips' own texts from this tree's tests (one checkout path written as <tree>): the rule matches every deps reason, in
    the served files or not, and none of the other outside reasons, so it names exactly the measured set. The count
    measured is MEASURED_DEPS_SKIPS, which the docstring, the run help and docs/batching.md name."""

    DEPS_REASONS = (
        "Skipped: extension deps absent (npm ci not run here): the build guard needs them",
        "Skipped: extension deps absent (npm ci not run here) \u2014 the served guard needs them",
        "Skipped: extension deps absent (npm ci not run here), the served lab needs them",
        "Skipped: extension deps absent",
        "Skipped: extension deps absent (npm ci not run here): the served hover needs a browser",
        "Skipped: extension deps absent (npm ci not run here): the browser legs need playwright",
        "Skipped: <tree>/vscode-extension/esbuild.js cannot load here: node found no package 'esbuild' to require (the "
        "extension's node_modules are absent or incomplete: npm ci not run), the same precondition a failed build skips on",
        "Skipped: no playwright: set ROMP_PLAYWRIGHT_NODE_PATH to a node_modules that holds it and esbuild",
        "Skipped: extension deps not installed here (npm ci in vscode-extension)",
    )
    OTHER_REASONS = (
        "Skipped: cleanplots, matplotlib and pandas are not importable here; run under uvx --with cleanplots --with "
        "matplotlib --with pandas",
        "Skipped: macOS-only derivation",
        "Skipped: set ROMP_CLI_PROBE_LIVE=1 to run against the installed Claude Code CLI",
        "Skipped: no SDK venv on this machine, or no python of its tag on PATH for the probe",
        "Skipped: no SDK venv (or no matching python) on this machine; the served host test needs the real SDK client in "
        "the kernel",
        "Skipped: the PR body lives outside the repository; ROMP_TESTS_PR_BODY names its file for a run that reads it",
        "Skipped: matplotlib not installed",
        "Skipped: this interpreter runs the callback of a weak reference a finalizer creates to an object the same "
        "collection frees (among them CPython 3.10 to 3.12, 3.13 before 3.13.13 and 3.14 before 3.14.4)",
        "Skipped: the runner's floor (tests/conftest.py) is not in play",
        "Skipped: the fixture root is not under $HOME",
        "Skipped: macOS-only default opener",
        "Skipped: the real Mach reader answers on a Mac only",
        "Skipped: no SDK venv on this machine",
        "Skipped: live move test is opt-in (ROMP_MOVE_LIVE=1): it bills two model turns against a real CLI",
    )

    def test_the_rule_matches_the_deps_reasons_and_no_other(self):
        for reason in self.DEPS_REASONS:
            with self.subTest(reason=reason):
                self.assertTrue(sweep.DEPS_SKIP.search(reason), "a skip for want of the deps the served leg must run")
        for reason in self.OTHER_REASONS:
            with self.subTest(reason=reason):
                self.assertIsNone(sweep.DEPS_SKIP.search(reason), "a skip no deps install changes")

    def test_the_measured_set_is_in_this_tree_outside_the_served_globs(self):
        m = sweep.MEASURED_DEPS_SKIPS
        served = expand_globs(str(ROOT), ("tests/test_*_browser.py", "tests/test_*_served.py"))
        self.assertGreaterEqual(m["tests"], len(m["files"]))
        for f in m["files"]:
            with self.subTest(file=f):
                self.assertTrue((ROOT / f).is_file(), "a measured file this tree no longer holds: measure again")
                self.assertNotIn(f, served, "outside the served globs")
                text = (ROOT / f).read_text(encoding="utf-8")
                self.assertTrue(any(sweep.DEPS_SKIP.search(r) for r in re.findall(r"SkipTest\(\s*\"([^\"]*)\"", text)),
                                "the file still skips for want of the deps, in words the rule reads")

    SKIP_CALLS = ("SkipTest", "skipTest", "skip", "skipIf", "skipUnless", "importorskip")

    def test_the_measured_files_are_the_trees_census_of_deps_skips_outside_the_served_globs(self):
        """MEASURED_DEPS_SKIPS names its files by hand; this derives them. The census: every tests/test_*.py outside the
        served globs with a skip call (SKIP_CALLS, by name or attribute) one of whose arguments holds a string DEPS_SKIP
        matches, a literal (an f-string's literal parts among them) or a module-level name bound to one. A new test that
        skips for want of the deps in words the rule reads changes the census, so this reds until the measurement is
        taken again and every text names the new count (test_every_text_names_the_measured_count). A skip whose reason
        is built any other way is outside the census, as it is outside the rule's reach until its log is read."""
        served = set(expand_globs(str(ROOT), ("tests/test_*_browser.py", "tests/test_*_served.py")))
        self.assertTrue(served, "the served globs select files here")
        census = []
        for path in sorted((ROOT / "tests").glob("test_*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in served:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            bound = {t.id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
                     and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                     for t in n.targets if isinstance(t, ast.Name)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else None
                if name not in self.SKIP_CALLS:
                    continue
                texts = []
                for arg in list(node.args) + [k.value for k in node.keywords]:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            texts.append(sub.value)
                        elif isinstance(sub, ast.Name) and sub.id in bound:
                            texts.append(bound[sub.id])
                if any(sweep.DEPS_SKIP.search(t) for t in texts):
                    census.append(rel)
                    break
        self.assertTrue(census, "the census found no deps skip at all: it cannot be reading the tree")
        self.assertEqual(tuple(census), tuple(sweep.MEASURED_DEPS_SKIPS["files"]),
                         "the files outside the served globs that skip for want of the deps are not the measured ones: "
                         "measure again and update MEASURED_DEPS_SKIPS and every text that names the count")

    def test_every_text_names_the_measured_count(self):
        """The runner's docstring, its run help and docs/batching.md say the served leg also runs these tests and
        name the count measured, so a new measurement that changes it reds here until each text says it."""
        m = sweep.MEASURED_DEPS_SKIPS
        count = "%d test%s in %d file%s when measured on %s" % (m["tests"], "" if m["tests"] == 1 else "s", len(m["files"]),
                                                                "" if len(m["files"]) == 1 else "s", m["date"])
        self.assertEqual(sweep.MEASURED_TEXT, count)
        env = dict(os.environ, COLUMNS="100")
        help_text = subprocess.run([sys.executable, str(SWEEP), "run", "--help"], env=env, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=True).stdout
        texts = {"the docstring": sweep.__doc__, "the run help": help_text,
                 "docs/batching.md": (ROOT / "docs" / "batching.md").read_text(encoding="utf-8")}
        for name, text in texts.items():
            with self.subTest(text=name):
                flat = " ".join(text.split())
                self.assertIn(count, flat)
                self.assertIn("skipped for want of", flat, "and says what the tests are")


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


def ci_job(job, src=None):
    """One ci.yml job read by line shape (no YAML library in the test deps, as tests/test_ci_bats_bound.py): {"keys":
    [the job's own `    KEY:` keys], "steps": {label: {"keys", "env", "run"}}}. A step is a `      - KEY:` line under
    the job's steps: key, whatever its first key, and the lines under it; its label is its name, or for a step without
    one its first key and value (a uses: value without its @version), so an unnamed step or one whose name is not its
    first key is read too; its keys are its `KEY:` keys in order, its env the `env:` block's KEY: value lines, its run
    the `run:` value or `run: |` block. Raises LookupError when the job is gone."""
    src = CI_YML.read_text(encoding="utf-8") if src is None else src
    m = re.search(r"^  %s:\n((?:    .*\n|\n)+)" % re.escape(job), src, re.M)
    if not m:
        raise LookupError("ci.yml has no %s job: re-anchor CiParity" % job)
    keys, raw, in_steps = [], [], False
    for line in m.group(1).split("\n"):
        k = re.match(r"^    ([a-z-]+):", line)
        if k:
            keys.append(k.group(1))
            in_steps = k.group(1) == "steps"
            continue
        if not in_steps:
            continue
        d = re.match(r"^      - ([a-z-]+):(.*)$", line)
        if d:
            raw.append(["        %s:%s" % (d.group(1), d.group(2))])
        elif raw:
            raw[-1].append(line)
    steps = {}
    for lines in raw:
        st = {"keys": [], "values": {}, "env": {}, "run": None, "name": None, "first": None}
        cur, i = None, 0
        while i < len(lines):
            line = lines[i]
            k = re.match(r"^        ([a-z-]+):(.*)$", line)
            if k:
                cur, val = k.group(1), k.group(2).strip()
                st["keys"].append(cur)
                st["values"][cur] = val
                st["first"] = st["first"] or (cur, val)
                if cur == "name":
                    st["name"] = val
                if cur == "run" and val == "|":
                    block = []
                    i += 1
                    while i < len(lines) and (lines[i].startswith(" " * 10) or not lines[i].strip()):
                        block.append(lines[i][10:])
                        i += 1
                    st["run"] = "\n".join(block).strip()
                    continue
                if cur == "run":
                    st["run"] = val
            elif cur == "env":
                e = re.match(r"^          ([A-Za-z_][A-Za-z0-9_]*): (.*)$", line)
                if e:
                    st["env"][e.group(1)] = e.group(2).strip().strip("\"'")
            i += 1
        first_key, first_val = st["first"]
        label = st["name"] or "%s: %s" % (first_key, first_val.partition("@")[0] if first_key == "uses" else first_val)
        if label in steps:
            raise AssertionError("ci.yml's %s job has two steps read as %r: re-anchor CiParity" % (job, label))
        steps[label] = st
    return {"keys": keys, "steps": steps}


def ci_steps(job, src=None):
    """{label: (env, run)} of one ci.yml job's steps (ci_job)."""
    return {label: (st["env"], st["run"]) for label, st in ci_job(job, src)["steps"].items()}


def ci_jobs(src=None):
    """The ids of ci.yml's jobs, in order: every `  ID:` line under the top-level jobs: key, up to the next top-level
    key. Read here on its own, not through the runner's workflow_jobs."""
    src = CI_YML.read_text(encoding="utf-8") if src is None else src
    lines = src.split("\n")
    out = []
    for line in lines[lines.index("jobs:") + 1:]:
        if re.match(r"[A-Za-z_]", line):
            break
        m = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):", line)
        if m:
            out.append(m.group(1))
    return out


# The served step's name. The runner reads the served leg from the step of this name wherever ci.yml holds it
# (sweep.py's SERVED_STEP, held equal to this below), and CiParity finds it the same way, by name, in any job.
SERVED_LABEL = "Browser-backed served-page tests (pytest)"
VENDORED_LABEL = "Vendored tooling and host-script tests (node --test)"


def served_pytest_line(run):
    """(the words of the one `python -m pytest` line of the served step's run text, its globs: the words after
    `python -m pytest` that name files under tests/). Read here on its own, not through the runner's read_served_step."""
    lines = [line.strip() for line in run.splitlines() if line.strip().startswith("python -m pytest")]
    if len(lines) != 1:
        raise AssertionError("the served step has %d pytest lines: re-anchor CiParity" % len(lines))
    words = shlex.split(lines[0])
    return words, [w for w in words[3:] if w.startswith("tests/")]


def expand_globs(root, globs):
    """What bash expands `globs` to in `root`: each glob in turn, its matches sorted (C.UTF-8 sorts by bytes, as Python
    sorts these names), read here with glob on its own."""
    import glob
    out = []
    for g in globs:
        out += sorted(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, g)))
    return out


def served_python_version(src, job):
    """The MAJOR.MINOR the setup-python step nearest before the served step in `job` names (its with: python-version:,
    a quoted version), read here on its own from ci.yml's lines, not through the runner's read_served_step."""
    lines = src.split("\n")
    start, _end = _step_span(lines, job, SERVED_LABEL)
    j_start, _j_end = _job_span(lines, job)
    setup = [i for i in range(j_start, start) if lines[i].startswith("      - uses: actions/setup-python@")]
    if not setup:
        raise AssertionError("no setup-python step before the served step in the %s job: re-anchor CiParity" % job)
    i = setup[-1] + 1
    while i < start and not lines[i].startswith("      - "):
        m = re.fullmatch(r"          python-version: '([0-9]+\.[0-9]+)'", lines[i])
        if m:
            return m.group(1)
        i += 1
    raise AssertionError("the setup-python step before the served step names no quoted python-version: re-anchor CiParity")


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
    them with what the runner builds (pytest_cmd, served_cmd, plan_legs' commands, LEG_ENV). Every difference is named
    here with its reason; a change to either side that adds one reds. Every step of every job is either compared with a
    leg or named as CI-only, by its name wherever it stands, so a new step reds until it is placed, and a step that
    moves to another job is still read (fork PR 928 moves the served step and the vendored tooling step into jobs of
    their own; CiParityServedJobOfItsOwn runs every case here over ci.yml as 928 leaves it). The python job's install
    steps are not hand copies: the runner reads them from ci.yml and builds the pytest leg's venv with them (the SDK
    ruling), and the cases below hold that read to the file and run it. Nor is the served step: the runner reads its
    env: block, its globs, its pip line and the Python version its job sets up from ci.yml by its name (the served
    rulings, 2026-09-28), and the cases below hold that read to the file, run it, and compare the served leg's command
    (one process) with the step, and the pytest leg (all of tests/, before the deps and with no browser) with CI's
    Python cells, which collect the served files and skip their browser-backed tests for want of a browser."""

    CI_ONLY = {
        # the unnamed setup steps: the checkout (the runner makes its own) and the toolchains (the runner uses the
        # batcher's; the pytest leg's venv is built from --python, and the served leg's from --served-python, which must
        # be the version the setup-python step before the served step names: the runner reads that one's python-version)
        "uses: actions/checkout", "uses: actions/setup-python", "uses: actions/setup-node",
        # setup that installs the tools the runner finds on the batcher's machine instead
        "Install bats (Linux)", "Install bats (macOS)", "Install gitleaks (Linux)", "Install gitleaks",
        "Cache Playwright's browsers", "Install the pinned Playwright Chromium",
        # the history and tree scans: the pre-push hook scans what a push publishes; CI scans all of history
        "Scan every commit", "Scan the tree as it stands",
        # the pane bench runs only in CI (the runner's docstring and docs/batching.md say so)
        "Dashboard pane bench (node --test)",
        # the rostered browser legs' run under ROMP_BROWSER_LEGS_REQUIRE=1 after CI's Chromium install (PR 887): the
        # sweep's npm-test leg runs the same bundles in its npm test with this machine's Playwright browsers, without
        # the switch, so a launch that fails there skips, as in CI's Test step, instead of failing (the runner's
        # docstring and docs/batching.md say so)
        "Browser legs (node --test over ci-browser-legs.txt)",
    }
    COMPARED = {"Install pytest", "Install cryptography", "Install the Claude Agent SDK", "Run pytest", "Run bats",
                "Manager handshake tests (node --test)", VENDORED_LABEL, "Install deps", "Typecheck", "Test", "Build",
                "PDF renderer dependency smoke test (node --test)", SERVED_LABEL}
    # The steps a job of the served step's own repeats from the extension job (its own checkout, node, npm ci, build and
    # Chromium install, as PR 928's ruling describes that job) and the unnamed setup every job has: each may stand in
    # more than one job, and every copy of a compared one is compared. Every other placed step stands in one job, since
    # a comparison reads it by name and a copy elsewhere would be a step no comparison reads.
    SHARED = {"uses: actions/checkout", "uses: actions/setup-python", "uses: actions/setup-node", "Install deps", "Build",
              "Cache Playwright's browsers", "Install the pinned Playwright Chromium"}

    def ci_text(self):
        """The workflow every case reads: this tree's ci.yml (a subclass gives another)."""
        return CI_YML.read_text(encoding="utf-8")

    def setUp(self):
        self.text = self.ci_text()
        self.jobs = {j: ci_steps(j, self.text) for j in ci_jobs(self.text)}
        # a directory holding this ci.yml and the file its SDK step reads its pin from, for the runner's own reads
        self.ci_tree = tempfile.mkdtemp(prefix="ciparity-")
        self.addCleanup(shutil.rmtree, self.ci_tree, True)
        os.makedirs(os.path.join(self.ci_tree, ".github", "workflows"))
        os.makedirs(os.path.join(self.ci_tree, "kernel"))
        with open(os.path.join(self.ci_tree, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
            f.write(self.text)
        shutil.copy(ROOT / "kernel" / "session_host.py", os.path.join(self.ci_tree, "kernel", "session_host.py"))
        self.served = sweep.read_served_step(self.ci_tree, "HEAD")
        self.legs = sweep.plan_legs(str(ROOT), "python", 2, served=self.served)

    def found(self, label):
        """[(job, env, run)] of every step read as `label`, in whichever jobs hold it."""
        return [(j, steps[label][0], steps[label][1]) for j, steps in self.jobs.items() if label in steps]

    def step(self, label):
        """(job, env, run) of the one step read as `label`, wherever ci.yml holds it."""
        hits = self.found(label)
        self.assertEqual(len(hits), 1, "ci.yml holds %d steps read as %r (%s): re-anchor CiParity"
                         % (len(hits), label, ", ".join(h[0] for h in hits)))
        return hits[0]

    def served_globs(self):
        """The globs on the served step's pytest line (CiParity's own read)."""
        return served_pytest_line(self.step(SERVED_LABEL)[2])[1]

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

    def test_every_step_is_compared_or_named_as_ci_only(self):
        """Every step of every job, named or not and whatever key comes first (ci_job reads each), placed by its name
        wherever it stands: a step that installs something (an unnamed `- run: python -m pip install ...`, or one whose
        name is its second key) reds here until it is placed, a placed step that moves to another job stays placed, and a
        step a comparison reads by name stands in one job (SHARED aside)."""
        seen = [(j, n) for j, steps in self.jobs.items() for n in steps]
        placed = self.COMPARED | self.CI_ONLY
        self.assertEqual(sorted((j, n) for j, n in seen if n not in placed), [],
                         "a ci.yml step neither compared with a leg nor named CI-only")
        self.assertIn(("python", "uses: actions/setup-python"), seen, "ci_job reads the unnamed steps")
        self.assertEqual(sorted(placed - {n for _j, n in seen}), [], "a step this pin names is gone from ci.yml")
        self.assertLessEqual(self.SHARED, placed)
        jobs_of = {n: [j for j, m in seen if m == n] for n in sorted(placed - self.SHARED)}
        self.assertEqual({n: js for n, js in jobs_of.items() if len(js) != 1}, {},
                         "a step a comparison reads by name stands in one job")

    def test_the_pytest_command_differs_from_run_pytest_only_as_named(self):
        job, env, run = self.step("Run pytest")
        self.assertEqual(job, "python", "the runner reads the python job's steps by the job's name")
        ci = shlex.split(_expr(run))
        ours = sweep.pytest_cmd("python", "<expr>")
        self.assertEqual(self.legs[PYTEST_LEG]["cmd"], sweep.pytest_cmd("python", 2), "the planned command is this one")
        self.assertEqual(ci[:3], ours[:3], "python -m pytest")
        ci_units, our_units = _units(ci[3:]), _units(ours[3:])
        named = [("tests",),                              # CI collects from the root; test modules live only under tests/
                 ("-p", "no:cacheprovider")]              # nothing written to a .pytest_cache in the checkout
        named += _units(sweep.PYTEST_ISOLATION)           # B4: no ini or conftest above the checkout
        named += [("--ignore=%s" % p,) for p in sorted(sweep.PYTEST_IGNORED)]   # Q6
        # every skip printed with its node id and reason beside pytest's default failures and errors, where the runner
        # reads the tests the leg skipped for want of the deps, which the served leg then runs (deps_skipped); output only
        named += [("-rfEs",), ("--no-fold-skipped",)]
        for u in named:
            self.assertIn(u, our_units, "a named difference the runner no longer has: %r" % (u,))
        # the -n count: CI's expression (2 or 0 by runner) against the runner's idle cores
        self.assertIn(("-n", "<expr>"), ci_units)
        self.assertEqual(sorted(u for u in our_units if u not in named), sorted(ci_units))

    def test_the_pytest_leg_runs_what_the_python_cells_run_with_what_they_have(self):
        """The pytest leg runs as CI's Python cells do: over all of tests/, the served step's files included (it leaves
        out PYTEST_IGNORED alone), with no node dependencies and no browser. The python job installs neither (no
        setup-node step, and no step of it runs npm, npx, node or playwright, or installs playwright), and its Run pytest
        sets no switch that would turn the served files' skips into failures; the leg runs before the deps leg, in a
        checkout with no node_modules, and its PLAYWRIGHT_BROWSERS_PATH is an empty directory. The served leg runs those
        files again with a browser (the cases after this one)."""
        files = expand_globs(str(ROOT), self.served_globs())
        self.assertGreater(len(files), 50, "the served globs select the served labs in this tree")
        self.assertEqual([a for a in self.legs[PYTEST_LEG]["cmd"] if a.startswith("--ignore=")],
                         ["--ignore=%s" % p for p in sorted(sweep.PYTEST_IGNORED)], "the served files are collected")
        self.assertNotIn("left_out", self.legs[PYTEST_LEG])
        self.assertLess(sweep.LEGS.index(PYTEST_LEG), sweep.LEGS.index("deps"), "the pytest leg runs before npm ci")
        tmp = os.path.join(os.sep + "nonexistent", "sweep-000000")
        ctx = sweep.leg_context(tmp, "python", env={"PATH": ""})
        self.assertEqual(sweep.leg_sets(PYTEST_LEG, ctx)["PLAYWRIGHT_BROWSERS_PATH"], os.path.join(tmp, sweep.NO_BROWSERS),
                         "no browser for the pytest leg")
        self.assertEqual(sweep.leg_sets(sweep.SERVED_LEG, ctx)["PLAYWRIGHT_BROWSERS_PATH"], ctx["browsers"])
        python_job = self.jobs["python"]
        self.assertNotIn("uses: actions/setup-node", python_job, "the Python cells install no node")
        for label, (env, run) in python_job.items():
            with self.subTest(step=label):
                self.assertNotRegex(run or "", r"\b(?:npm|npx|node|playwright)\b", "the Python cells install no browser or node deps")
        self.assertEqual([k for k in python_job["Run pytest"][0] if k.startswith("ROMP_SERVED_TESTS_")], [],
                         "the Python cells' skips of the served files stay skips")

    def test_the_runner_reads_the_served_step_as_written(self):
        """The runner's read of the served step (read_served_step) against CiParity's own: the step's job, its env:
        block, which is the served leg's switches, its globs, its pip lines, which the served leg's venv holds, and the
        Python version the setup-python step before it in its job names, which that venv is built from. The served leg's
        environment carries every one of those switches, its PATH leads with its own venv's directory and never the
        pytest leg's venv, and it carries no SDK switch, since CI's served step installs none."""
        job, env, run = self.step(SERVED_LABEL)
        self.assertEqual(sweep.SERVED_STEP, SERVED_LABEL)
        self.assertEqual((self.served["job"], self.served["env"], self.served["globs"]), (job, env, self.served_globs()))
        self.assertTrue({"install", "python"} <= set(self.served), "the runner reads the step's pip lines and its job's Python")
        self.assertEqual(self.served["install"], [shlex.split(line) for line in run.splitlines()
                                                  if line.strip().startswith("python -m pip install")])
        self.assertEqual(len(self.served["install"]), 1, "the step's one pip line")
        self.assertEqual(self.served["python"], served_python_version(self.text, job), "the version its job sets up")
        self.assertEqual(env.get("ROMP_SERVED_TESTS_REQUIRE"), "1", "the switch that turns a skip in the served files into a failure")
        self.assertIn("ROMP_SERVED_TESTS_ENGINES", env, "the engines the step's job installs")
        ctx = sweep.leg_context(os.path.join(os.sep + "nonexistent", "sweep-000000"), os.path.join(os.sep + "nonexistent", "base", "python"),
                                env={"PATH": ""}, pytest_python=os.path.join(os.sep + "nonexistent", "venv", "bin", "python"),
                                served_env=self.served["env"],
                                served_python=os.path.join(os.sep + "nonexistent", "served", "bin", "python"))
        sets = sweep.leg_sets(sweep.SERVED_LEG, ctx)
        self.assertEqual({k: sets.get(k) for k in env}, env, "the served leg carries the step's env: block as written")
        path = sets["PATH"].split(os.pathsep)
        self.assertEqual(path[0], os.path.join(os.sep + "nonexistent", "served", "bin"), "its venv's directory leads the served leg's PATH")
        self.assertNotIn(os.path.join(os.sep + "nonexistent", "venv", "bin"), path, "the pytest leg's venv is not on it")
        self.assertNotIn("ROMP_SDK_REQUIRE", sets, "CI's served step declares no SDK: its job installs none")
        self.assertEqual(self.legs[sweep.SERVED_LEG]["cmd"][0], "python", "the served leg's command runs --python itself")

    def test_the_served_command_differs_from_the_served_step_only_as_named(self):
        """One process, as CI's served step runs it: no -n. The differences are the globs' expansion, PYTEST_ISOLATION
        and, at run time, the tests the pytest leg skipped for want of the deps (here a stand-in id)."""
        _job, _env, run = self.step(SERVED_LABEL)
        words, globs = served_pytest_line(run)
        files = expand_globs(str(ROOT), globs)
        also = ["tests/test_stand_in.py::test_it"]
        ours = sweep.served_cmd("python", files, also)
        self.assertEqual(self.legs[sweep.SERVED_LEG]["cmd"], sweep.served_cmd("python", files), "the planned command is this one")
        self.assertEqual(words[:3], ours[:3], "python -m pytest")
        self.assertNotIn("-n", words, "CI's served step runs one process")
        ci_units = [u for u in _units(words[3:]) if u[0] not in globs]
        our_units = _units(ours[3:])
        named = [(f,) for f in files]                     # the runner passes the globs' expansion, CI the globs
        named += [(t,) for t in also]                     # the tests the pytest leg skipped for want of the deps
        named += _units(sweep.PYTEST_ISOLATION)           # B4: no ini or conftest above the checkout
        for u in named:
            self.assertIn(u, our_units, "a named difference the runner no longer has: %r" % (u,))
        self.assertEqual(sorted(u for u in our_units if u not in named), sorted(ci_units))
        self.assertFalse(any(u[0] == "-n" for u in our_units), "no -n on the served leg")

    def test_the_served_leg_runs_the_served_steps_files_in_its_env_in_its_own_venv(self):
        """Run: the runner over a world holding this ci.yml and kernel/session_host.py, FAKE standing in for every
        tool and answering as the version the served job sets up. The served leg runs the files the served step's globs
        select in that world (CiParity's own expansion), in one process, with every variable of the step's env: block at
        its value, in a venv built from the step's pip line (CiParity's own read) and nothing else, so without the SDK,
        whose directory leads its PATH; the pytest leg collects those files too, in its own venv, and carries none of
        those variables."""
        real = {".github/workflows/ci.yml": self.text,
                "kernel/session_host.py": (ROOT / "kernel" / "session_host.py").read_text(encoding="utf-8")}
        w = World(dict(SEED, **real))
        self.addCleanup(w.close)
        job, env, run = self.step(SERVED_LABEL)
        w.ctl({"probe_version": served_python_version(self.text, job) + ".0"})
        w.run(check=0)
        files = expand_globs(w.tree, self.served_globs())
        self.assertEqual(files, SEED_SERVED_FILES)
        calls = {c["leg"]: c for c in w.calls()}
        served, pytest_call = calls[sweep.SERVED_LEG], calls[PYTEST_LEG]
        self.assertEqual([a for a in served["argv"] if a.startswith("tests/")], files, "the files the step's globs select")
        self.assertNotIn("-n", served["argv"], "one process")
        self.assertEqual([a for a in pytest_call["argv"] if a.startswith("--ignore=")],
                         ["--ignore=%s" % p for p in sorted(sweep.PYTEST_IGNORED)], "the pytest leg collects them too")
        self.assertEqual({k: served["values"].get(k) for k in env}, env, "the served leg carries the step's env: block")
        self.assertEqual([k for k in env if k in pytest_call["names"]], [], "the pytest leg carries none of it")
        rec = w.result()["runner"]["served"]
        self.assertEqual(served["exe"], rec["python"], "the served leg runs in its own venv, never in the pytest leg's")
        pip = [shlex.split(line) for line in run.splitlines() if line.strip().startswith("python -m pip install")]
        self.assertEqual(served["venv_installs"], {w_: "9.9.9" for line in pip for w_ in line[4:] if not w_.startswith("-")},
                         "the venv holds what the step's pip line installs, and nothing else")
        self.assertNotIn("claude-agent-sdk", served["venv_installs"])
        self.assertEqual(served["values"]["PATH"].split(os.pathsep)[0], os.path.dirname(rec["python"]), "its venv's directory leads its PATH")
        self.assertNotIn(os.path.dirname(w.result()["runner"]["sdk"]["python"]), served["values"]["PATH"].split(os.pathsep))
        self.assertEqual((rec["job"], rec["python_ci"]), (job, served_python_version(self.text, job)))

    def test_the_run_pytest_steps_env_is_the_pytest_legs_but_the_gil_setting(self):
        job, env, _run = self.step("Run pytest")
        self.assertEqual(sorted(env), ["PYTHON_GIL", "ROMP_SDK_REQUIRE"])
        self.assertEqual(sorted(sweep.LEG_ENV[PYTEST_LEG]), ["ROMP_SDK_REQUIRE"], "the pytest leg's switches are the Run pytest step's")
        self.assertEqual(sweep.LEG_ENV[PYTEST_LEG]["ROMP_SDK_REQUIRE"], env["ROMP_SDK_REQUIRE"])
        # PYTHON_GIL, the named difference: CI's free-threaded cell alone sets it (to 0); the runner runs the one --python
        # and sets nothing, so a free-threaded --python runs with its own default
        self.assertEqual(env["PYTHON_GIL"], "${{ endsWith(matrix.python-version, 't') && '0' || '' }}")
        self.assertNotIn("PYTHON_GIL", sweep.LEG_ENV[PYTEST_LEG])
        self.assertNotIn(sweep.SERVED_LEG, sweep.LEG_ENV, "the served leg's switches are read from ci.yml, never restated")

    def pin(self):
        """kernel/session_host.py's SDK_TESTED_VERSION, read by this test on its own (ci.yml's SDK step reads the same
        line with sed)."""
        hits = re.findall(r'(?m)^SDK_TESTED_VERSION = "([^"]*)"', (ROOT / "kernel" / "session_host.py").read_text(encoding="utf-8"))
        self.assertEqual(len(hits), 1, hits)
        return hits[0]

    def test_the_install_steps_carry_only_what_the_runner_reads(self):
        """The runner builds the pytest leg's venv from the install steps' commands alone, so what else could change
        what those steps install is held off here, read from ci.yml on its own: each install step's keys are ones the
        runner reads (no env:, if: or working-directory:) and its env is empty, a shell: is bash, the python job's keys
        are the runner's, and the workflow has no top-level env: or defaults:. The runner refuses each of them too
        (read_install_plan; the next case runs that over this ci.yml)."""
        job = ci_job("python", self.text)
        self.assertEqual([k for k in job["keys"] if k not in sweep.PYTHON_JOB_KEYS], [], "a python job key the runner does not read")
        for name in sweep.INSTALL_STEPS:
            st = job["steps"][name]
            with self.subTest(step=name):
                self.assertEqual([k for k in st["keys"] if k not in sweep.INSTALL_STEP_KEYS], [])
                self.assertEqual(st["env"], {}, "an install step's env changes what it installs")
                self.assertIn(st["values"].get("shell", "bash"), ("bash",), "the runner reads a step bash runs")
        self.assertEqual(re.findall(r"(?m)^(env|defaults):", self.text), [], "a workflow-level env: or defaults: reaches every step")

    def test_the_runner_refuses_what_it_does_not_read_in_this_workflow(self):
        """The adversary pass's five ci.yml mutants (finding 2), applied to this ci.yml: each passed every reader of the
        file before the runner read a step's keys and every step. Each is refused by name now."""
        src = self.text
        crypto = "        run: python -m pip install cryptography\n"
        sdk = "        shell: bash\n        run: |\n          set -euo pipefail\n          pin="
        pytest_step = "      - name: Run pytest\n"
        for anchor in (crypto, sdk, pytest_step):
            self.assertEqual(src.count(anchor), 1, "re-anchor: %r" % anchor)
        n = len(ci_job("python", src)["steps"])      # the added step's number: it goes in just before Run pytest, the last
        cases = (("C1 an env: on Install cryptography", src.replace(crypto, "        env:\n          PIP_ONLY_BINARY: \":none:\"\n" + crypto),
                  "step 'Install cryptography' has env:, which the runner does not read"),
                 ("C2 an if: on Install cryptography", src.replace(crypto, "        if: runner.os == 'macOS'\n" + crypto),
                  "step 'Install cryptography' has if:, which the runner does not read"),
                 ("C3 a working-directory: on the SDK step", src.replace(sdk, sdk.replace("shell: bash\n", "shell: bash\n        working-directory: kernel\n")),
                  "step 'Install the Claude Agent SDK' has working-directory:, which the runner does not read"),
                 ("C4 an unnamed install step", src.replace(pytest_step, "      - run: python -m pip install hypothesis\n" + pytest_step),
                  "step %d of the python job has no name (run: python -m pip install hypothesis)" % n),
                 ("C5 an install step named on its second line", src.replace(pytest_step, "      - run: python -m pip install hypothesis\n"
                                                                                         "        name: Install hypothesis\n" + pytest_step),
                  "the python job has a step 'Install hypothesis', which the runner does not read"))
        tmp = tempfile.mkdtemp(prefix="ciparity-")
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, ".github", "workflows"))
        os.makedirs(os.path.join(tmp, "kernel"))
        shutil.copy(ROOT / "kernel" / "session_host.py", os.path.join(tmp, "kernel", "session_host.py"))
        for label, text, refusal in cases:
            with self.subTest(mutant=label):
                with open(os.path.join(tmp, ".github", "workflows", "ci.yml"), "w", encoding="utf-8") as f:
                    f.write(text)
                with self.assertRaises(sweep.Refused) as cm:
                    sweep.read_install_plan(tmp, "HEAD")
                self.assertIn(refusal, str(cm.exception))
                if label[:2] in ("C4", "C5"):
                    self.assertEqual(sorted(set(ci_job("python", text)["steps"]) - set(ci_job("python", src)["steps"])),
                                     ["run: python -m pip install hypothesis" if label[:2] == "C4" else "Install hypothesis"],
                                     "CiParity's own read sees the added step, so the every-step case reds on it too")

    def test_the_runner_reads_every_install_step_of_the_python_job_as_written(self):
        """Every named step of the python job before Run pytest is an install step the runner reads, in CI's order
        (INSTALL_STEPS), and it reads each as written: the two pip lines as they stand, and the SDK step as its pip line
        with the pin its sed read gives, then its import check."""
        self.assertEqual([n for n in self.jobs["python"] if n != "Run pytest" and not n.startswith("uses: ")],
                         list(sweep.INSTALL_STEPS),
                         "the runner reads every install step of the python job, and only those")
        plan = sweep.read_install_plan(self.ci_tree, "HEAD")
        pin = self.pin()
        self.assertEqual((plan["dist"], plan["pin"], plan["module"]), ("claude-agent-sdk", pin, "claude_agent_sdk"))
        by_step = {step["step"]: step["commands"] for step in plan["steps"]}
        for name in ("Install pytest", "Install cryptography"):
            self.assertEqual(by_step[name], [("pip", shlex.split(self.jobs["python"][name][1]))], name)
        self.assertEqual(by_step[sweep.SDK_STEP], [("pip", ["python", "-m", "pip", "install", "claude-agent-sdk==" + pin]),
                                                   ("check", ["python", "-c", "import claude_agent_sdk"])])

    def test_the_runners_environment_holds_what_the_install_steps_install(self):
        """Run: the runner over a world holding this ci.yml and kernel/session_host.py, FAKE standing in for
        pip. The venv the pytest leg runs in holds every requirement the python job's install steps name, the SDK at
        the pin the SDK step reads, and nothing else; the population is read from ci.yml here, not from the runner."""
        real = {".github/workflows/ci.yml": self.text,
                "kernel/session_host.py": (ROOT / "kernel" / "session_host.py").read_text(encoding="utf-8")}
        w = World(dict(SEED, **real))
        self.addCleanup(w.close)
        # FAKE answers as the version the served job sets up, which the served leg's venv is built from
        w.ctl({"probe_version": served_python_version(self.text, self.step(SERVED_LABEL)[0]) + ".0"})
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
        _job, env, run = self.step("Run bats")
        self.assertEqual(shlex.split(run), self.legs["bats"]["cmd"][:2] + list(sweep.GLOBS["bats"]),
                         "the runner passes the glob's expansion, CI the glob")
        # ROMP_GITLEAKS_REQUIRE is CI's Linux value: the Linux cell installs the pinned gitleaks
        self.assertEqual(env.get("ROMP_GITLEAKS_REQUIRE"), "${{ runner.os == 'Linux' && '1' || '' }}")
        self.assertEqual({"BATS_TEST_TIMEOUT": env["BATS_TEST_TIMEOUT"], "ROMP_GITLEAKS_REQUIRE": "1"}, sweep.LEG_ENV["bats"])
        for step, leg in (("Manager handshake tests (node --test)", "manager"), (VENDORED_LABEL, "tools")):
            _job, _env, run = self.step(step)
            self.assertEqual(shlex.split(run), self.legs[leg]["cmd"][:2] + list(sweep.GLOBS[leg]))
        # tools/pdf-smoke.test.mjs, its own step in the extension job, is in the tools leg's glob
        _job, _env, run = self.step("PDF renderer dependency smoke test (node --test)")
        self.assertEqual(shlex.split(run), ["node", "--test", "tools/pdf-smoke.test.mjs"])
        self.assertIn("tools/pdf-smoke.test.mjs", self.legs["tools"]["cmd"])

    def test_the_webview_legs_run_the_extension_jobs_commands(self):
        """Typecheck and Test stand in the extension job alone; npm ci and the build stand there and in any job of the
        served step's own (SHARED), and every copy runs the leg's command."""
        for _job, _env, run in self.found("Install deps"):
            self.assertEqual(shlex.split(run), list(sweep.DEPS_CMD[:2]),
                             "npm ci; the runner adds --no-audit --no-fund, which change what npm prints, not what it installs")
        self.assertEqual(list(sweep.DEPS_CMD[2:]), ["--no-audit", "--no-fund"])
        for step, leg in (("Typecheck", "typecheck"), ("Test", "npm-test"), ("Build", "build")):
            hits = self.found(step)
            self.assertTrue(hits, step)
            for job, _env, run in hits:
                self.assertEqual(shlex.split(run), self.legs[leg]["cmd"], "%s in the %s job" % (step, job))
            self.assertEqual(self.legs[leg]["cwd"], "vscode-extension")
        self.assertEqual([j for j, _e, _r in self.found("Typecheck") + self.found("Test")], ["vscode-extension"] * 2)


def _job_span(lines, job):
    """[start, end) of `job` in ci.yml's lines: its `  <job>:` line up to the next job's line, the next top-level key or
    the end, trailing blank lines left out."""
    start = lines.index("  %s:" % job)
    end = start + 1
    while end < len(lines) and not re.match(r"(?:  )?[A-Za-z_]", lines[end]):
        end += 1
    while lines[end - 1].strip() == "":
        end -= 1
    return start, end


def _step_span(lines, job, label):
    """[start, end) of the step named `label` in `job`: its `      - name: <label>` line up to the job's next step or
    the job's end."""
    start, end = _job_span(lines, job)
    hits = [i for i in range(start, end) if lines[i] == "      - name: %s" % label]
    if len(hits) != 1:
        raise AssertionError("ci.yml's %s job holds %d steps named %r: re-anchor served_job_of_its_own" % (job, len(hits), label))
    i = hits[0] + 1
    while i < end and not lines[i].startswith("      - "):
        i += 1
    return hits[0], i


def _step_in(lines, job, label):
    """Whether `job` holds a step named `label` (a job the file lacks holds none)."""
    if "  %s:" % job not in lines:
        return False
    start, end = _job_span(lines, job)
    return any(lines[i] == "      - name: %s" % label for i in range(start, end))


def served_job_of_its_own(src):
    """ci.yml as fork PR 928 leaves it, built from `src` (this tree's ci.yml) as 928's round-1 rulings describe it: the
    served step moves out of the extension job, with the setup-python step before it, into a job of its own with its own
    setup (the checkout, node, npm ci, the build, and the extension job's Playwright cache and Chromium install, copied)
    and fail-fast off; and the vendored tooling step moves out of the Shell job into a job of its own. Each block is cut
    from the real file by its anchors, each held to one occurrence, so a change to ci.yml that this construction no
    longer reads reds here by name. Each move is made only while its step still stands in its old job: once 928 has
    landed, ci.yml already has that shape and comes back as it is, and CiParityServedJobOfItsOwn reads the real file."""
    lines = src.split("\n")
    cut, vendored, served, setup = [], None, None, []
    if _step_in(lines, "shell", VENDORED_LABEL):
        v_start, v_end = _step_span(lines, "shell", VENDORED_LABEL)
        if v_end != _job_span(lines, "shell")[1]:
            raise AssertionError("the vendored tooling step is not the Shell job's last step: re-anchor served_job_of_its_own")
        vendored = lines[v_start:v_end]
        cut.append((v_start, v_end))
    if _step_in(lines, "vscode-extension", SERVED_LABEL):
        ext_start, ext_end = _job_span(lines, "vscode-extension")
        s_start, s_end = _step_span(lines, "vscode-extension", SERVED_LABEL)
        if s_end != ext_end:
            raise AssertionError("the served step is not the extension job's last step: re-anchor served_job_of_its_own")
        py = [i for i in range(ext_start, s_start) if lines[i] == "      - uses: actions/setup-python@v5"]
        if len(py) != 1 or any(lines[i].startswith("      - ") for i in range(py[0] + 1, s_start)):
            raise AssertionError("the extension job's setup-python step does not come right before the served step: "
                                 "re-anchor served_job_of_its_own")
        setup = (lines[slice(*_step_span(lines, "vscode-extension", "Cache Playwright's browsers"))] +
                 lines[slice(*_step_span(lines, "vscode-extension", "Install the pinned Playwright Chromium"))])
        served = lines[py[0]:s_end]
        cut.append((py[0], s_end))
    out, at = [], 0
    for start, end in sorted(cut):
        out += lines[at:start]
        at = end
    out += lines[at:]
    while out and out[-1] == "":
        out.pop()
    if vendored:
        out += ["", "  vendored-tooling:", "    name: Vendored tooling (node --test)", "    runs-on: ubuntu-latest",
                "    timeout-minutes: 30", "    steps:", "      - uses: actions/checkout@v4", "      - uses: actions/setup-node@v4",
                "        with:", "          node-version: '22'"] + vendored
    if served:
        out += ["", "  served-pages:", "    name: Browser-backed served-page tests", "    runs-on: ubuntu-latest",
                "    timeout-minutes: 40", "    strategy:", "      fail-fast: false", "    defaults:", "      run:",
                "        working-directory: vscode-extension", "    steps:", "      - uses: actions/checkout@v4",
                "      - uses: actions/setup-node@v4", "        with:", "          node-version: '22'", "      - name: Install deps",
                "        run: npm ci", "      - name: Build", "        run: npm run build"] + setup + served
    return "\n".join(out) + "\n"


class CiParityServedJobOfItsOwn(CiParity):
    """Every CiParity case over ci.yml as fork PR 928 leaves it (served_job_of_its_own): the served step in a job of its
    own, and the vendored tooling step in another. The runner finds the served step by its name there and nothing in
    CiParity reads a compared step by its job, so this branch holds when 928 lands (the served ruling, 2026-09-28)."""

    def ci_text(self):
        return served_job_of_its_own(CI_YML.read_text(encoding="utf-8"))

    def test_the_construction_moves_both_steps(self):
        """The served step and the vendored tooling step each stand in a job of their own, not in their old ones, and
        the runner read the served step in its job. Before 928 lands the construction moved them (the jobs it names);
        after, the real file already stands so, and the construction changes nothing."""
        served_job, vendored_job = self.step(SERVED_LABEL)[0], self.step(VENDORED_LABEL)[0]
        self.assertNotIn(served_job, ("vscode-extension", "python", "shell", "secrets"))
        self.assertNotIn(vendored_job, ("vscode-extension", "python", "shell", "secrets", served_job))
        self.assertEqual(self.served["job"], served_job, "the runner read the step in its new job")
        self.assertEqual(served_job_of_its_own(self.text), self.text, "a file already in 928's shape comes back as it is")
        real = CI_YML.read_text(encoding="utf-8")
        if _step_in(real.split("\n"), "vscode-extension", SERVED_LABEL):
            self.assertEqual((served_job, vendored_job), ("served-pages", "vendored-tooling"), "the construction moved both")


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
        is always owed, and the ledger, run with rc 0 (or `rcs`), and deps, the webview legs and served not owed for
        that reason alone."""
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
                      "not owed: deps, typecheck, npm-test, build, served)", line)

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
        """The runner always owes pytest, bats, manager and tools, marks deps, the webview legs and served not owed only
        when the sha has no vscode-extension/package.json (round 1, decision 11: every head owes the webview legs, whatever
        it changed, and the served ruling: the served leg on the same terms), and the ledger only with a reason. A record that says otherwise did not come from the runner (or
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
        legs = self.legs()
        legs["served"] = {"owed": False, "rc": None, "why": untouched}
        cases.append(("the served leg by the changed-path rule", legs,
                      "served marked not owed for a reason other than 'no vscode-extension/package.json' ('%s')" % untouched))
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

    def test_a_failure_in_an_invalid_run_counts_and_the_line_names_it(self):
        """Round 2, Class A: a leg that failed in an invalid run counts as a failure (the invalidating leg's own failure
        included), so a later green needs --flake naming it, a second failure leaves the sha red naming both runs (read
        before the newest run's invalid), the reader's invalid line and the pass line name the invalid run's failed leg,
        and a pass inside an invalid run excuses nothing; an invalid run that failed no leg still needs no flake. An
        invalid run's flakes are read, so they must be a mapping."""
        reason = "after the pytest leg the checkout is not the sha's tree: changed kernel/kernel.py"
        invalid_red = self.run_rec(invalid=reason, legs=self.legs(pytest=1))
        cases = (
            ("the invalidating leg failed, then a plain green", [invalid_red, self.run_rec(started="2026-01-01T00:02:00Z")],
             "red", "run 1 failed pytest (rc 1; log logs/pytest.log), and run 2 passed it with no --flake naming it"),
            ("the invalidating leg failed, then a green with its flake",
             [invalid_red, self.run_rec(flakes={PYTEST_LEG: self.FLAKE}, started="2026-01-01T00:02:00Z")], "pass",
             "an earlier run 1 (started 2026-01-01T00:00:00Z) was invalid: %s; its failures count: pytest (rc 1; log "
             "logs/pytest.log)" % reason),
            ("the invalidating leg failed, the newest run", [invalid_red], "invalid",
             "sweep invalid at 1234567890: %s; run 1's failures count: pytest (rc 1; log logs/pytest.log)" % reason),
            ("a red, then a second failure inside an invalid run, the newest",
             self.red_then(self.run_rec(invalid=reason, legs=self.legs(pytest=1), flakes={PYTEST_LEG: self.FLAKE},
                                        started="2026-01-01T00:02:00Z"))["runs"],
             "red", "pytest failed in runs 1 and 2; a known flake is excused once"),
            ("a red, then a pass with its flake inside an invalid run, then a plain green",
             self.red_then(self.run_rec(invalid=reason, flakes={PYTEST_LEG: self.FLAKE}, started="2026-01-01T00:02:00Z"),
                           self.run_rec(started="2026-01-01T00:04:00Z"))["runs"],
             "red", "run 1 failed pytest (rc 1; log logs/pytest.log), and run 3 passed it with no --flake naming it"),
            ("an invalid run that failed no leg, then a green", [self.run_rec(invalid=reason),
                                                                 self.run_rec(started="2026-01-01T00:02:00Z")],
             "pass", "was invalid: %s);" % reason),
            ("a red before an invalid run still needs the flake",
             self.red_then(self.run_rec(invalid=reason, started="2026-01-01T00:02:00Z"),
                           self.run_rec(started="2026-01-01T00:04:00Z"))["runs"],
             "red", "run 1 failed pytest (rc 1; log logs/pytest.log), and run 3 passed it with no --flake naming it"),
            ("an invalid run whose flakes are not a mapping", [self.run_rec(invalid=reason, flakes=[PYTEST_LEG]),
                                                               self.run_rec(started="2026-01-01T00:02:00Z")],
             "invalid", "run 1's flakes are not a mapping of leg to known flake"),
        )
        for label, runs, want, named in cases:
            with self.subTest(label):
                self.write(self.result(runs=runs))
                case, line = self.case()
                self.assertEqual(case, want, line)
                self.assertIn(named, line)

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
