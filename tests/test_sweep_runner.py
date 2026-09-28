#!/usr/bin/env python3
"""scripts/sweep.py, the local sweep runner whose result file is the landing gate (2026-09-27).

scripts/batch.py verify and land read a result keyed by the batch head's full sha (tests/test_batch_tool.py
holds that side). This module holds the writer: every leg's rc is recorded under the full sha of a clean
tree, every leg runs after a red one, the webview legs follow CLAUDE.md's rule, a dirty tree is refused and a
tree that changes during the run is recorded invalid, the leg environment carries no session, hook or
credential variables, and nothing is written in the working tree.

Every test builds its own world: a bare origin, a clone holding a tiny tree, and fakes for npm, bats, node
and the pytest interpreter (one script, told apart by its name) that record their argv, cwd and environment
variable NAMES and exit with the code the test sets. Each fake carries its world's control and log paths in its
own text, since no variable a test sets is sure to reach a leg. The real suite never runs. Synthetic data only.
"""
import fcntl
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
import json, os, shutil, subprocess, sys
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
keep = ("TMPDIR", "SWEEP_WRAPPED", "ROMP_SERVED_TESTS_REQUIRE", "ROMP_GITLEAKS_REQUIRE", "BATS_TEST_TIMEOUT")
with open(LOG, "a") as f:
    f.write(json.dumps({"leg": leg, "argv": args, "cwd": os.getcwd(), "names": sorted(os.environ),
                        "values": {k: os.environ[k] for k in keep if k in os.environ}}) + "\n")
act = ctl.get("action", {}).get(leg)
if act == "commit":
    subprocess.run(["git", "-C", ctl["tree"], "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
                    "commit", "-q", "--allow-empty", "-m", "moved during the sweep"], check=True,
                   env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
elif act == "copy-result":
    shutil.copy(ctl["result"], ctl["copy_to"])
elif act == "leak":
    with open(os.path.join(ctl["tree"], "leaked.txt"), "w") as f:
        f.write("a test that wrote into the tree\n")
# What each test leg's real tool prints at the end of a run (pytest -q's summary, bats' TAP, node's TAP summary):
# the runner counts the tests a leg ran from its log, and a test leg with rc 0 and no test counted is red.
out = {"pytest": "3 passed in 0.01s\n", "bats": "1..1\nok 1 a\n", "manager": "# pass 1\n# fail 0\n",
       "tools": "# pass 2\n# fail 0\n", "npm-test": "# pass 4\n# fail 0\n"}
sys.stdout.write(ctl.get("out", {}).get(leg, out.get(leg, "")))
sys.exit(ctl.get("rc", {}).get(leg, 0))
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
        os.makedirs(self.bin)
        fake = FAKE % {"python": sys.executable, "ctl": self.ctl_path, "log": self.log_path}
        for name in ("python", "npm", "node", "bats"):
            with open(os.path.join(self.bin, name), "w") as f:
                f.write(fake)
            os.chmod(os.path.join(self.bin, name), 0o755)
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

    def run(self, *extra, env=None, check=None):
        p = subprocess.run([sys.executable, str(SWEEP), "run", "--tree", self.tree, "--python", self.python, "--workers", "2", *extra],
                           env=env or self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        if check is not None and p.returncode != check:
            raise AssertionError("sweep run exited %d, expected %d:\n%s%s" % (p.returncode, check, p.stdout, p.stderr))
        return p

    def result_path(self, sha=None):
        return os.path.join(self.xdg, "romp", "sweeps", (sha or self.head()) + ".json")

    def result(self, sha=None):
        with open(self.result_path(sha)) as f:
            return json.load(f)


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
        self.assertEqual([n for n in sweep.LEGS if r["legs"][n]["owed"] is not False],
                         ["deps", "pytest", "bats", "manager", "tools", "ledger"],
                         "untouched webview paths owe no webview leg; an absent node_modules owes deps")
        self.assertEqual(w.legs_called(), ["deps", "pytest", "bats", "manager", "tools", "ledger"], "run in roster order")
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
        self.assertEqual(w.legs_called(), ["deps", "pytest", "bats", "manager", "tools", "ledger"], "the legs after the red one ran too")
        self.assertIn("sweep red at %s: bats (rc 1)" % w.head()[:10], p.stdout)

    def test_the_webview_legs_follow_the_rule(self):
        cases = (("kernel/kernel.py", True), ("ui/x.js", True), ("vscode-extension/src/a.ts", True),
                 ("README.md", False), ("kernel/other.py", False))
        for path, owed in cases:
            with self.subTest(path=path):
                w = World()
                self.addCleanup(w.close)
                w.change({path: "changed\n"})
                w.run(check=0)
                r = w.result()
                for name in sweep.WEBVIEW_LEGS:
                    self.assertIs(r["legs"][name]["owed"], owed, "%s after a change to %s" % (name, path))
                called = w.legs_called()
                for name in sweep.WEBVIEW_LEGS:
                    self.assertEqual(name in called, owed, "the npm fake ran %s: %r" % (name, called))
                self.assertEqual(r["owed"]["webview"]["paths"], [path] if owed else [])
                self.assertEqual(r["base"], w.git("rev-parse", "origin/main"))

    def test_no_origin_main_owes_the_webview_legs(self):
        w = self.w
        w.git("update-ref", "-d", "refs/remotes/origin/main")
        w.run(check=0)
        r = w.result()
        for name in sweep.WEBVIEW_LEGS:
            self.assertIs(r["legs"][name]["owed"], True, name)
        self.assertIn("no origin/main", r["owed"]["webview"]["why"])
        self.assertIsNone(r["base"])

    def test_a_dirty_tree_is_refused_and_nothing_is_written(self):
        w = self.w
        for label, files in (("modified", {"README.md": "# edited\n"}), ("untracked", {"notes/new.txt": "new\n"})):
            with self.subTest(label):
                w.write(files)
                p = w.run(check=2)
                self.assertIn("is not clean", p.stderr)
                self.assertIn(list(files)[0], p.stderr, "the refusal names the path")
                self.assertFalse(os.path.exists(w.result_path()), "no result for a dirty tree")
                self.assertEqual(w.calls(), [])
                w.git("checkout", "-q", "--", ".")
                w.git("clean", "-q", "-fd")

    def test_the_runner_writes_nothing_in_the_tree(self):
        w = self.w
        before = w.git("status", "--porcelain", "--ignored", "--untracked-files=all")
        w.run(check=0)
        self.assertEqual(w.git("status", "--porcelain", "--ignored", "--untracked-files=all"), before)
        self.assertTrue(w.result()["legs"]["pytest"]["log"].startswith(os.path.join(w.xdg, "romp", "sweeps", "logs", w.head())),
                        "logs live under the state dir")

    def test_head_moving_during_the_run_is_invalid(self):
        w = self.w
        start = w.head()
        w.ctl({"action": {"bats": "commit"}})
        p = w.run(check=3)
        r = w.result(start)
        self.assertEqual(r["verdict"], "invalid")
        self.assertIn(start[:10], r["invalid"])
        self.assertIn(w.head()[:10], r["invalid"], "the reason names where HEAD went")
        self.assertNotEqual(w.head(), start)
        self.assertIn("sweep invalid at %s" % start[:10], p.stdout)

    def test_a_file_a_leg_leaves_in_the_tree_is_invalid(self):
        w = self.w
        w.ctl({"action": {"manager": "leak"}})
        w.run(check=3)
        r = w.result()
        self.assertEqual(r["verdict"], "invalid")
        self.assertIn("leaked.txt", r["invalid"])

    def test_the_file_says_running_until_the_end(self):
        w = self.w
        copy = os.path.join(w.tmp, "mid-run.json")
        w.ctl({"action": {"bats": "copy-result"}, "result": w.result_path(), "copy_to": copy})
        w.run(check=0)
        with open(copy) as f:
            mid = json.load(f)
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

    def test_the_pytest_leg_drops_session_git_and_credential_variables(self):
        w = self.w
        env = dict(w.env, ROMP_SID=SID, CLAUDE_CODE_SESSION_ID=SID, GIT_DIR=os.path.join(w.tmp, "no-such-git-dir"),
                   SWEEP_PROBE_TOKEN="plain")
        w.run(env=env, check=0)
        call = [c for c in w.calls() if c["leg"] == "pytest"][0]
        for name in ("ROMP_SID", "CLAUDE_CODE_SESSION_ID", "GIT_DIR", "SWEEP_PROBE_TOKEN", "GIT_CONFIG_GLOBAL"):
            self.assertNotIn(name, call["names"], "the pytest leg inherits %s" % name)
        self.assertFalse([n for n in call["names"] if sweep.DROP_CREDENTIAL.search(n)], "a credential-shaped name reaches pytest")
        ledger = [c for c in w.calls() if c["leg"] == "ledger"][0]
        self.assertIn("SWEEP_PROBE_TOKEN", ledger["names"], "only the test legs drop credential-shaped names")
        self.assertNotIn("ROMP_SID", ledger["names"])
        tmpdir = call["values"]["TMPDIR"]
        self.assertLessEqual(len(os.fsencode(tmpdir)), len(BOX_TMPDIR_TEMPLATE), tmpdir)
        self.assertNotRegex(tmpdir, r"-[A-Za-z]", "a letter after the dash spells a short option")
        self.assertFalse(os.path.exists(tmpdir), "the runner removes its TMPDIR")
        self.assertEqual(call["values"]["ROMP_SERVED_TESTS_REQUIRE"], "1")
        argv = call["argv"]
        self.assertEqual(" ".join(argv[:4]), "-m pytest tests -n")
        self.assertIn("no:anyio", argv)
        self.assertIn("--ignore=tests/test_cut_turn_tree_kill.py", argv)
        r = w.result()
        rec = r["legs"]["pytest"]
        self.assertIn("ROMP_SID", rec["env_dropped"])
        self.assertIn("SWEEP_PROBE_TOKEN", rec["env_dropped"])
        self.assertNotIn(SID, json.dumps(r), "the result records variable names, never values")
        self.assertNotIn("plain", json.dumps(rec["env_dropped"]))
        self.assertEqual(r["sha"], w.head(), "an inherited GIT_DIR does not move the runner's own git calls")

    def test_a_wrap_prefixes_one_leg_and_its_rc_is_the_legs(self):
        w = self.w
        w.run("--wrap", "pytest=env SWEEP_WRAPPED=1", check=0)
        by_leg = {c["leg"]: c for c in w.calls()}
        self.assertEqual(by_leg["pytest"]["values"].get("SWEEP_WRAPPED"), "1")
        self.assertNotIn("SWEEP_WRAPPED", by_leg["bats"]["values"])
        r = w.result()
        self.assertEqual(r["legs"]["pytest"]["wrap"], ["env", "SWEEP_WRAPPED=1"])
        self.assertIsNone(r["legs"]["bats"]["wrap"])
        w2 = World()
        self.addCleanup(w2.close)
        w2.run("--wrap", "*=env SWEEP_WRAPPED=star", "--wrap", 'bats=sh -c "exit 7" --', check=1)
        r2 = w2.result()
        self.assertEqual(r2["legs"]["bats"]["rc"], 7, "the recorded rc is the wrapper's")
        self.assertEqual(r2["red"], ["bats"])
        self.assertEqual({c["leg"]: c["values"].get("SWEEP_WRAPPED") for c in w2.calls()}.get("pytest"), "star",
                         "* applies to a leg with no prefix of its own")
        self.assertNotIn("bats", w2.legs_called(), "the leg's own prefix replaced *")

    def test_a_wrap_that_runs_nothing_is_red_not_a_pass(self):
        """A wrapper that exits 0 without running its command (`true`; `systemd-run --user` without --wait, which
        returns once the unit has started) gives every leg rc 0. A test leg with rc 0 and no test counted in its
        log is red, named, so such a run can never be recorded as a pass."""
        w = self.w
        p = w.run("--wrap", "*=true", check=1)
        r = w.result()
        self.assertEqual(r["verdict"], "red", p.stdout + p.stderr)
        self.assertEqual(r["red"], [PYTEST_LEG, "bats", "manager", "tools"])
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

    def test_a_leg_rerun_after_a_named_flake_keeps_both_runs(self):
        """A --leg re-run counts only over the first run's recorded failure, named as a known flake, at the same full
        sha (pre-round ruling Q11): the leg's record holds the re-run's attempt and, under `rerun`, the first failure,
        the flake and the sha each ran at; the history keeps the first attempt too, and the pass line names both."""
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        first = w.result()
        self.assertEqual(first["red"], [PYTEST_LEG])
        w.ctl({})
        before = len(w.calls())
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=0)
        r = w.result()
        self.assertEqual(r["verdict"], "pass", p.stdout + p.stderr)
        self.assertEqual([c["leg"] for c in w.calls()[before:]], [PYTEST_LEG], "only the named leg ran again")
        self.assertEqual([(h["leg"], h["rc"]) for h in r["history"]], [(PYTEST_LEG, 1)], "the red attempt is kept")
        leg = r["legs"]["pytest"]
        self.assertEqual(leg["rc"], 0)
        self.assertEqual(leg["rerun"]["flake"], self.FLAKE)
        self.assertEqual(leg["rerun"]["sha"], w.head())
        self.assertEqual(leg["rerun"]["first"]["sha"], w.head())
        self.assertEqual((leg["rerun"]["first"]["rc"], leg["rerun"]["first"]["started"]),
                         (1, first["legs"]["pytest"]["started"]), "the first failure is the first run's own attempt")
        for name in ("bats", "manager", "tools", "ledger"):
            self.assertEqual(r["legs"][name]["started"], first["legs"][name]["started"], "%s was not touched" % name)
        a = sweep.assess(w.head(), env=w.env)
        self.assertEqual(a["case"], "pass", a["line"])
        self.assertIn("pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE, a["line"])
        self.assertIn("pytest re-run after a known flake", p.stdout)
        w.change({"README.md": "moved on\n"})
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("no result at %s to re-run a leg in; run the full sweep" % w.head()[:10], p.stderr)

    def test_a_leg_rerun_is_refused_without_a_flake_over_a_pass_twice_or_before_the_sweep_finished(self):
        w = self.w
        w.ctl({"rc": {"pytest": 1}})
        w.run(check=1)
        path = w.result_path()
        with open(path) as f:
            red = f.read()
        w.ctl({})
        before = len(w.calls())
        for extra, named in ((("--leg", "pytest"), "--leg re-runs a leg only after a known flake: name it with --flake"),
                             (("--leg", "pytest", "--flake", "  "), "--leg re-runs a leg only after a known flake"),
                             (("--flake", self.FLAKE), "--flake names the flake a --leg re-run is for; it takes --leg"),
                             (("--leg", "bats", "--flake", self.FLAKE), "bats passed at %s; there is no failure to re-run" % w.head()[:10])):
            with self.subTest(extra=extra):
                p = w.run(*extra, check=2)
                self.assertIn(named, p.stderr)
                with open(path) as f:
                    self.assertEqual(f.read(), red, "a refused re-run leaves the result as it was")
        self.assertEqual(len(w.calls()), before, "nothing ran")
        w.run("--leg", "pytest", "--flake", self.FLAKE, check=0)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("pytest was already re-run at %s, and a re-run counts once; run the full sweep" % w.head()[:10], p.stderr)
        data = json.loads(red)
        data.update(finished=None, verdict="running")
        sweep.write_result(path, data)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("the sweep at %s has not finished" % w.head()[:10], p.stderr)
        data = json.loads(red)
        data["legs"]["pytest"]["finished"] = None
        sweep.write_result(path, data)
        p = w.run("--leg", "pytest", "--flake", self.FLAKE, check=2)
        self.assertIn("pytest has no finished first run at %s to re-run" % w.head()[:10], p.stderr)

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

    def test_deps_never_runs_npm_ci_through_a_symlinked_node_modules(self):
        w = self.w
        shared = os.path.join(w.tmp, "shared-node_modules")
        os.makedirs(shared)
        os.symlink(shared, os.path.join(w.tree, "vscode-extension", "node_modules"))
        w.run(check=0)
        r = w.result()
        self.assertIs(r["legs"]["deps"]["owed"], False)
        self.assertIn("a symlink", r["legs"]["deps"]["why"])
        self.assertNotIn("deps", w.legs_called())

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


class Reader(unittest.TestCase):
    """assess, the reader scripts/batch.py verify calls: each case by name, over files written the way the runner
    writes them. The batch side of the same cases is tests/test_batch_tool.py, VerifyReadsTheSweep."""

    SHA = "1234567890" + "a" * 30
    OTHER = "1234567890" + "b" * 30      # same 10-character prefix, another commit

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sweepread-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = {"XDG_STATE_HOME": self.tmp, "HOME": self.tmp}

    def result(self, sha=None, **over):
        sha = sha or self.SHA
        legs = {n: {"owed": True, "rc": 0, "started": "2026-01-01T00:00:01Z", "finished": "2026-01-01T00:00:02Z"} for n in sweep.LEGS}
        for n in sweep.TEST_LEGS:
            legs[n].update(tests=1, failed=0)
        for n in sweep.WEBVIEW_LEGS + ("deps",):
            legs[n] = {"owed": False, "rc": None, "why": "not owed here"}
        data = {"schema": sweep.SCHEMA, "sha": sha, "branch": "batch/b1", "started": "2026-01-01T00:00:00Z",
                "finished": "2026-01-01T00:01:00Z", "legs": legs, "verdict": "pass", "red": [], "invalid": None}
        data.update(over)
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
        legs = self.result()["legs"]
        legs["bats"]["rc"] = 1
        self.write(self.result(legs=legs, verdict="red", red=["bats"]))
        cases.append(("red", self.case()))
        self.write(self.result(legs=legs, verdict="pass"))       # a recorded pass over a red leg
        cases.append(("invalid", self.case()))
        self.write(self.result(invalid="HEAD moved to 0000000000 during the run", verdict="invalid"))
        cases.append(("invalid", self.case()))
        legs = self.result()["legs"]
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
        """The runner always owes pytest, bats, manager and tools, and marks deps, ledger and the webview legs not
        owed only with a reason. A record that says otherwise did not come from the runner (or came from a runner
        with another roster), and a leg it marks not owed ran nothing, so the reader refuses it by name."""
        cases = []
        legs = self.result()["legs"]
        for n in sweep.LEGS:
            legs[n] = {"owed": False}
        cases.append(("every leg not owed", legs, "pytest, bats, manager, tools marked not owed"))
        legs = self.result()["legs"]
        legs["pytest"] = {"owed": False, "rc": None, "why": "skipped by hand"}
        cases.append(("pytest alone", legs, "pytest marked not owed"))
        legs = self.result()["legs"]
        legs["deps"] = {"owed": False, "rc": None}
        cases.append(("deps with no reason", legs, "deps marked not owed with no reason"))
        legs = self.result()["legs"]
        legs["build"] = {"owed": False, "rc": None, "why": "  "}
        cases.append(("a blank reason", legs, "build marked not owed with no reason"))
        for label, legs, named in cases:
            with self.subTest(label):
                self.write(self.result(legs=legs))
                case, line = self.case()
                self.assertEqual(case, "invalid", line)
                self.assertIn(named, line)
                self.assertEqual(sweep.verdict_of(self.result(legs=legs)), "red", "the verdict rule owes such a leg too")

    def rerun(self, **mark):
        """A result whose pytest leg the runner re-ran after a known flake: the re-run passed, the first run failed with
        rc 1, both at SHA; `mark` replaces keys of the rerun record (None deletes one)."""
        data = self.result()
        first = {"rc": 1, "started": "2026-01-01T00:00:01Z", "finished": "2026-01-01T00:00:02Z", "tests": 3, "failed": 1}
        data["history"] = [dict(first, leg="pytest")]
        rec = {"flake": "tests/test_notes.py::test_order (known)", "sha": self.SHA, "first": dict(first, sha=self.SHA)}
        for k, v in mark.items():
            if v is None:
                rec.pop(k, None)
            else:
                rec[k] = v
        data["legs"]["pytest"]["rerun"] = rec
        return data

    def test_a_counted_rerun_passes_and_the_line_names_both_runs(self):
        self.write(self.rerun())
        case, line = self.case()
        self.assertEqual(case, "pass", line)
        self.assertIn("pytest re-run after a known flake (first run rc 1; flake: tests/test_notes.py::test_order (known))", line)

    def test_a_rerun_the_runner_never_writes_is_invalid(self):
        """The reader refuses a re-run that lacks the recorded first failure, names no flake, or ran at another sha
        (pre-round ruling Q11), each by name; a leg counts as re-run when its record carries `rerun` or the history
        holds an earlier attempt of it."""
        passing_first = {"rc": 0, "started": "s", "finished": "f", "tests": 3, "failed": 0, "sha": self.SHA}
        unfinished_first = {"rc": 1, "started": "s", "finished": None, "tests": 3, "failed": 1, "sha": self.SHA}
        no_mark = self.rerun()
        del no_mark["legs"]["pytest"]["rerun"]
        twice = self.rerun()
        twice["history"].append(dict(twice["history"][0]))
        cases = (
            ("history with no mark", no_mark, "pytest was re-run with no first failure recorded and no flake named"),
            ("an empty mark", self.rerun(first=None, flake=None, sha=None), "pytest's re-run records no first failure"),
            ("no first failure", self.rerun(first=None), "pytest's re-run records no first failure"),
            ("a first run that passed", self.rerun(first=passing_first), "pytest's re-run records no first failure"),
            ("a first run that never finished", self.rerun(first=unfinished_first), "pytest's re-run records no first failure"),
            ("no flake", self.rerun(flake=None), "pytest's re-run names no known flake"),
            ("a blank flake", self.rerun(flake="  "), "pytest's re-run names no known flake"),
            ("the re-run at another sha", self.rerun(sha=self.OTHER), "pytest: the re-run ran at %s, not at %s" % (self.OTHER, self.SHA)),
            ("the first run at another sha", self.rerun(first=dict(self.rerun()["legs"]["pytest"]["rerun"]["first"], sha=self.OTHER)),
             "pytest: the first run ran at %s, not at %s" % (self.OTHER, self.SHA)),
            ("the re-run at no sha", self.rerun(sha=None), "pytest: the re-run ran at None, not at %s" % self.SHA),
            ("re-run twice", twice, "pytest was re-run 2 times, and a re-run counts once"),
        )
        for label, data, named in cases:
            with self.subTest(label):
                self.write(data)
                case, line = self.case()
                self.assertEqual(case, "invalid", line)
                self.assertIn(named, line)
                self.assertIn("a --leg re-run counts only over a recorded first failure named as a known flake, at the same "
                              "full sha", line)
        bare = self.rerun()
        bare["legs"]["pytest"]["rerun"] = "yes"
        self.write(bare)
        self.assertEqual(self.case()[0], "invalid", "a rerun key whose value is not a record is refused too")

    def test_the_schema_must_be_the_integer(self):
        self.write(self.result(schema=True))
        case, line = self.case()
        self.assertEqual(case, "unreadable", "True equals 1 in Python and must not read as schema 1: %s" % line)


class Rules(unittest.TestCase):
    def test_the_verdict_rule(self):
        v = sweep.verdict_of

        def result(finished="2026-01-01T00:00:00Z", invalid=None, **legs):
            base = {n: {"owed": False, "rc": None, "why": "not owed here"} for n in sweep.LEGS}
            for n in sweep.ALWAYS_OWED:
                base[n] = {"owed": True, "rc": 0, "tests": 1}
            base.update(legs)
            return {"finished": finished, "invalid": invalid, "legs": base}
        self.assertEqual(v(result(finished=None)), "running")
        self.assertEqual(v(result(invalid="HEAD moved")), "invalid")
        self.assertEqual(v(result(bats={"owed": True, "rc": 1})), "red")
        self.assertEqual(v(result(bats={"owed": True, "rc": None})), "red", "an owed leg with no rc is red")
        self.assertEqual(v(result(bats={"owed": True, "rc": False})), "red", "rc must be the integer 0")
        self.assertEqual(v(result(bats={"rc": 0, "tests": 1})), "pass", "a leg that does not say it is not owed is owed")
        self.assertEqual(v(result(bats={"owed": "no", "rc": None})), "red", "only owed: false excuses a leg")
        self.assertEqual(v(result(pytest={"owed": True, "rc": 0, "tests": 1})), "pass", "a not-owed leg's empty rc is fine")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0})), "red", "a test leg with rc 0 and no count ran nothing")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": 0})), "red", "a count of 0 is no test run")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": True})), "red", "a count must be an int")
        self.assertEqual(v(result(bats={"owed": True, "rc": 0, "tests": 3, "failed": 1})), "red", "a failed test is red at rc 0")
        self.assertEqual(v(result(ledger={"owed": True, "rc": 0})), "pass", "the ledger check is not a test leg")
        self.assertEqual(v(result()), "pass")
        self.assertEqual(v(result(pytest={"owed": False, "rc": None, "why": "skipped"})), "red", "pytest is always owed")
        self.assertEqual(v(result(deps={"owed": False, "rc": None})), "red", "not owed takes a reason")
        missing = result(pytest={"owed": True, "rc": 0, "tests": 1})
        del missing["legs"]["bats"]
        self.assertEqual(v(missing), "red", "a leg absent from the record is owed")

    def test_webview_owed_is_the_claude_md_rule(self):
        w = sweep.webview_owed
        self.assertEqual(w(["kernel/kernel.py", "kernel/other.py", "ui/a/b.ts", "vscode-extension/x", "uix/y", "README.md"]),
                         ["kernel/kernel.py", "ui/a/b.ts", "vscode-extension/x"])
        self.assertEqual(w([]), [])

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
