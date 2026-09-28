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
import glob, json, os, shutil, subprocess, sys, time
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
# The control and log paths are written into this file when the World makes it, never read from the environment:
# the runner's leg environment is an allowlist that drops every name a test would set.
CTL, LOG = %(ctl)r, %(log)r
ctl = json.load(open(CTL)) if os.path.exists(CTL) else {}
if name == "python" and args[:1] == ["-c"]:
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
        "ROMP_POSTAL_PORT")
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
# What each test leg's real tool prints at the end of a run (pytest -q's summary, bats' TAP, node's TAP summary):
# the runner counts the tests a leg ran from its log, and a test leg with rc 0 and no test counted is red.
out = {"pytest": "3 passed in 0.01s\n", "bats": "1..1\nok 1 a\n", "manager": "# pass 1\n# fail 0\n",
       "tools": "# pass 2\n# fail 0\n", "npm-test": "# pass 4\n# fail 0\n"}
sys.stdout.write(ctl.get("out", {}).get(leg, out.get(leg, "")))
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
        os.makedirs(self.bin)
        fake = FAKE % {"python": sys.executable, "ctl": self.ctl_path, "log": self.log_path}
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

    def test_a_pytest_interpreter_without_the_plugins_is_refused(self):
        w = self.w
        w.ctl({"missing": ["xdist"]})
        p = w.run(check=2)
        self.assertIn("lacks xdist", p.stderr)
        self.assertFalse(os.path.exists(w.result_path()))

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
CTX_SHAPE = {k: "/nonexistent/" + k for k in ("tmpdir", "home", "xdg", "npm_cache", "browsers", "path")}


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
                   BATS_TEST_TIMEOUT="5", ROMP_GITLEAKS_REQUIRE="0", ROMP_SERVED_TESTS_ENGINES="chromium,firefox")
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
                path = v["PATH"].split(os.pathsep)
                self.assertEqual(path[0], w.bin, "the pytest interpreter's directory leads PATH")
                tool_dirs = {os.path.dirname(shutil.which(t, path=env["PATH"]) or "") for t in sweep.PATH_TOOLS} - {""}
                self.assertEqual(sorted(set(path) - {w.bin} - tool_dirs - set(sweep.PATH_FLOOR)), [])
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
    leg or named as CI-only, so a new step reds until it is placed."""

    CI_ONLY = {
        # setup that installs the tools the runner finds on the batcher's machine instead
        ("python", "Install pytest"), ("python", "Install cryptography"), ("shell", "Install bats (Linux)"),
        ("shell", "Install bats (macOS)"), ("shell", "Install gitleaks (Linux)"), ("secrets", "Install gitleaks"),
        ("vscode-extension", "Cache Playwright's browsers"), ("vscode-extension", "Install the pinned Playwright Chromium"),
        # the history and tree scans: the pre-push hook scans what a push publishes; CI scans all of history
        ("secrets", "Scan every commit"), ("secrets", "Scan the tree as it stands"),
        # the pane bench runs only in CI (the runner's docstring and docs/batching.md say so)
        ("vscode-extension", "Dashboard pane bench (node --test)"),
    }

    def setUp(self):
        self.jobs = {j: ci_steps(j) for j in ("python", "shell", "secrets", "vscode-extension")}
        self.legs = sweep.plan_legs(str(ROOT), "python", 2)

    def test_every_named_step_is_compared_or_named_as_ci_only(self):
        compared = {("python", "Run pytest"), ("shell", "Run bats"), ("shell", "Manager handshake tests (node --test)"),
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
                 ("-p", "no:cacheprovider"),              # nothing written to a .pytest_cache in the checkout
                 ("-p", "no:anyio")]                      # PR 872
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
        self.assertEqual(sorted(sweep.LEG_ENV[PYTEST_LEG]), sorted(served), "the pytest leg's switches are the served step's")

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
            run["runner"] = {"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()}}
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
