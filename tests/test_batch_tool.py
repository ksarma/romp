#!/usr/bin/env python3
"""scripts/batch.py against a fixture repository (scripts/land.sh has its own suite in
tests/test_land_sh.py).

Every test builds its own GitHub: a bare repository as `origin`, an `author` clone that makes the
member branches, a `dev` clone the tool acts on (the scripts are copied into its scripts/, as they
sit in the real clone), and tests/fixtures/fake_gh.py on PATH as `gh`, reading PR metadata from a
JSON file and head SHAs live from the bare repository. No test reaches the real gh or GitHub, and
none touches the live kernel or the developer's git configuration (GIT_CONFIG_GLOBAL is /dev/null).

What the plan holds the tool to (next-batch-process, "What the guard tests check"):
  - plan orders dependents after bases and excludes drafts, major-feature and hold;
  - assemble refuses when a batch/* ref exists on the remote;
  - provenance fails on an undeclared commit and passes on a `batch:` commit;
  - verify fails when a pinned head moved;
  - pull N drops N's dependents;
  - the body stays under 65,536 characters with details truncated first.
Plus the conflict paths (hold back and tell the owner once; --resolve/--continue records the
resolution; a straggler UPSTREAM.md row is converted inside the merge), land and finish end to end,
the computed "Read these first" rule, and the landing gate since 2026-09-27: verify and land read the
result scripts/sweep.py wrote for the batch head's full sha (VerifyReadsTheSweep, LandReadsTheSweep,
SweepThenVerify) and refuse a batch head that does not contain main (VerifyBehind); land requires the batch
head's CI run green (LandReadsTheCI); plan and assemble --repin read each member's own sweep result at its
head (PlanReadsTheMemberSweep).

Synthetic data only: a demo `notes-api` with invented PR numbers, branch names and titles.
"""
import ast
import importlib.util
import json
import os
import re
import resource
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

# The batch tool reads sweep results under the state root (each Fixture points XDG_STATE_HOME at a
# directory of its own), and every test module that loads romp code through a loader isolates the
# state root first (tests/test_state_isolation_order.py enforces the order).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FAKE_GH = ROOT / "tests" / "fixtures" / "fake_gh.py"

TRAILER = ('<!-- romp-pr: {"tier":"fix","rounds":3,"sweep":{"pytest":"12 passed","bats":4,"npm":2,'
           '"typecheck":"clean"},"sweep_head":"0123456789abcdef","flakes":[]} -->')

# The seed's ci.yml, the workflow whose run land reads: the coordinator's decision 18 reads a run green only when every
# job of ci.yml at the head has a job run in it that passed, told by the name GitHub renders (a matrix job's name with its
# expression filled in, a job with no name: by its id). SEED_CI_JOBS are the job runs a green run of it lists, which
# Fixture.ci records unless a test gives others.
SEED_CI = """name: CI
on:
  push:
    branches: ['batch/**']
jobs:
  python:
    name: Python ${{ matrix.python-version }} (ubuntu-latest)
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.12', '3.13']
    steps:
      - run: python -m pytest -q
  secrets:
    runs-on: ubuntu-latest
    steps:
      - run: gitleaks detect
"""
SEED_CI_JOBS = [{"name": "Python 3.12 (ubuntu-latest)", "status": "completed", "conclusion": "success"},
                {"name": "Python 3.13 (ubuntu-latest)", "status": "completed", "conclusion": "success"},
                {"name": "secrets", "status": "completed", "conclusion": "success"}]

SEED = {
    ".github/workflows/ci.yml": SEED_CI,
    "README.md": "# notes-api\n",
    "kernel/kernel.py": "VERSION = 1\n",
    "postal/postal_service.py": "def send():\n    return 1\n",
    "notes.txt": "one\ntwo\nthree\n",
    "UPSTREAM.md": "# Upstream\n\nProse.\n\n| What | Where it lives here | Status | Notes |\n|---|---|---|---|\n"
                   "| row one | here | candidate | n1 |\n\nWhen offering: tail.\n",
}

# A stand-in for the sibling branch's scripts/upstream-ledger.py, with the two commands the batch
# tool calls and the interface the plan specifies for them: `import --row '<row>'` writes one entry
# file, `check` refuses a table row in UPSTREAM.md.
FAKE_LEDGER = r'''#!/usr/bin/env python3
import os, re, sys
if sys.argv[1:3] == ["import", "--row"]:
    cells = [c.strip() for c in sys.argv[3].strip().strip("|").split("|")]
    slug = re.sub(r"[^a-z0-9]+", "-", cells[0].lower()).strip("-")
    os.makedirs("upstream", exist_ok=True)
    with open(os.path.join("upstream", "2026-01-01-%s.md" % slug), "w") as f:
        f.write("---\ntitle: %s\nstatus: %s\nwhere: %s\nadded: 2026-01-01\n---\n%s\n" % (cells[0], cells[2], cells[1], cells[3]))
    print("upstream/2026-01-01-%s.md" % slug)
elif sys.argv[1:2] == ["check"]:
    for i, line in enumerate(open("UPSTREAM.md"), 1):
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            print("UPSTREAM.md:%d: a table row; entries live in upstream/ now" % i)
            sys.exit(1)
else:
    sys.exit(2)
'''


def _load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


batch = _load_script("batch_tool", "batch.py")
sweep = _load_script("batch_tool_sweep", "sweep.py")


# A row field Fixture.ci leaves out.
MISSING = object()


class Fixture:
    """A bare origin, an author clone, the tool's clone, and the fake gh, all under one temp dir."""

    def __init__(self):
        # Resolved once, here: batch.py names paths under its repository's real path (git's show-toplevel follows
        # symlinks), so a root under a symlinked TMPDIR (macOS's /var -> /private/var) must be compared resolved.
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="batchtool-"))
        self.bare = os.path.join(self.tmp, "origin.git")
        self.author = os.path.join(self.tmp, "author")
        self.dev = os.path.join(self.tmp, "dev")
        self.bin = os.path.join(self.tmp, "bin")
        self.state_file = os.path.join(self.tmp, "gh-state.json")
        self.log_file = os.path.join(self.tmp, "gh.log")
        # Sweep results live under the state root, keyed by sha; two fixtures can mint the same sha in
        # the same second (same content, same author, same stamp), so each gets a root of its own.
        self.xdg = os.path.join(self.tmp, "xdg")
        os.makedirs(self.bin)
        shutil.copy(FAKE_GH, os.path.join(self.bin, "gh"))
        os.chmod(os.path.join(self.bin, "gh"), 0o755)
        self.env = dict(os.environ,
                        PATH=self.bin + os.pathsep + os.environ.get("PATH", ""),
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="romp tests", GIT_AUTHOR_EMAIL="tests@example.invalid",
                        GIT_COMMITTER_NAME="romp tests", GIT_COMMITTER_EMAIL="tests@example.invalid",
                        FAKE_GH_STATE=self.state_file, FAKE_GH_LOG=self.log_file, ROMP_BATCH_POLL="0",
                        XDG_STATE_HOME=self.xdg)
        self.env.pop("ROMP_STATE_DIR", None)
        self.env.pop("ROMP_GH", None)
        self.env.pop("FAKE_GH_DELETE_INDIRECT", None)
        self._git("init", "-q", "--bare", self.bare, cwd=self.tmp)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.bare)
        os.makedirs(self.author)
        self._git("init", "-q", cwd=self.author)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.author)
        self._write(self.author, SEED)
        self._git("add", "-A", cwd=self.author)
        self._git("commit", "-q", "-m", "seed", cwd=self.author)
        self._git("remote", "add", "origin", self.bare, cwd=self.author)
        self._git("push", "-q", "-u", "origin", "main", cwd=self.author)
        self._git("clone", "-q", self.bare, self.dev, cwd=self.tmp)
        os.makedirs(os.path.join(self.dev, "scripts"), exist_ok=True)
        for s in ("batch.py", "sweep.py", "pr-orphans.sh"):
            shutil.copy(SCRIPTS / s, os.path.join(self.dev, "scripts", s))
        self.gh_state = {"bare": self.bare, "next_number": 900, "prs": {}, "rulesets": [],
                         "repo": {"mergeCommitAllowed": True, "squashMergeAllowed": False,
                                  "rebaseMergeAllowed": False, "deleteBranchOnMerge": True}}
        self._save_gh()

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- git ---------------------------------------------------------------
    def _git(self, *args, cwd, check=True, input=None):
        proc = subprocess.run(["git", *args], cwd=cwd, env=self.env, text=True, input=input,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and proc.returncode != 0:
            raise AssertionError("git %s failed in %s:\n%s%s" % (" ".join(args), cwd, proc.stdout, proc.stderr))
        return proc.stdout.strip()

    def dev_git(self, *args, check=True):
        return self._git(*args, cwd=self.dev, check=check)

    def bare_rev(self, ref):
        return self._git("rev-parse", "--verify", "--quiet", "refs/heads/" + ref, cwd=self.bare, check=False)

    @staticmethod
    def _write(root, changes):
        for path, content in changes.items():
            p = os.path.join(root, path)
            if content is None:
                if os.path.exists(p):
                    os.remove(p)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(content)

    def branch(self, name, changes, base="origin/main", msg=None, swept=True):
        """A new branch on origin, cut from `base`, carrying one commit with `changes`."""
        self._git("fetch", "-q", "origin", cwd=self.author)
        ref = base if ("/" in base or re.fullmatch(r"[0-9a-f]{40}", base)) else "origin/" + base
        self._git("checkout", "-q", "-B", name, ref, cwd=self.author)
        return self.commit(name, changes, msg or "change on %s" % name, _new=True, swept=swept)

    def commit(self, name, changes, msg="another commit", _new=False, swept=True):
        """One more commit on an existing branch, pushed. The author sweeps what they push: a passing sweep result for
        the new head is recorded (every leg run and rc 0, the webview legs included), unless `swept` is False; plan
        and assemble --repin read it for a member's head (pre-round ruling Q7)."""
        if not _new:
            self._git("fetch", "-q", "origin", cwd=self.author)
            self._git("checkout", "-q", "-B", name, "origin/" + name, cwd=self.author)
        self._write(self.author, changes)
        self._git("add", "-A", cwd=self.author)
        self._git("commit", "-q", "-m", msg, cwd=self.author)
        self._git("push", "-q", "-f", "origin", name, cwd=self.author)
        sha = self._git("rev-parse", "HEAD", cwd=self.author)
        if swept:
            self.swept(name, sha)
        return sha

    def swept(self, name, sha=None):
        """The author's passing sweep of branch `name` at `sha` (default: its head on origin), as commit records it."""
        return self.result(sha or self.bare_rev(name), name, webview=True, tree=self.author)

    def commit_main(self, changes, msg="on main"):
        return self.commit("main", changes, msg)

    # -- fake GitHub -------------------------------------------------------
    def _save_gh(self):
        with open(self.state_file, "w") as f:
            json.dump(self.gh_state, f, indent=1)

    def gh(self):
        with open(self.state_file) as f:
            return json.load(f)

    def pr(self, n, head, base="main", title=None, body="", labels=(), draft=False, checks="success",
           state="OPEN", merge_commit=None, mergeable="MERGEABLE", head_oid=None):
        """`head_oid` pins a MERGED or CLOSED PR's head at that moment (the fake reads an OPEN PR's
        head live from its branch); without it the fake reads the branch once."""
        self.gh_state = self.gh()
        self.gh_state["prs"][str(n)] = {
            "number": n, "title": title or "PR %d on %s" % (n, head), "body": body, "labels": list(labels),
            "baseRefName": base, "headRefName": head, "isDraft": draft, "state": state,
            "mergeCommit": merge_commit, "mergedAt": None, "mergeable": mergeable, "checks": checks,
            "comments": [], "url": "https://example.invalid/pull/%d" % n}
        if head_oid:
            self.gh_state["prs"][str(n)]["headRefOid"] = head_oid
        self._save_gh()

    def set_repo(self, **kw):
        self.gh_state = self.gh()
        self.gh_state["repo"].update(kw)
        self._save_gh()

    def set_gh(self, **kw):
        self.gh_state = self.gh()
        self.gh_state.update(kw)
        self._save_gh()

    def calls(self, *prefix):
        out = []
        if os.path.exists(self.log_file):
            with open(self.log_file) as f:
                for line in f:
                    argv = json.loads(line)
                    if argv[:len(prefix)] == list(prefix):
                        out.append(argv)
        return out

    def fake_gh(self, *args):
        return subprocess.run([os.path.join(self.bin, "gh"), *args], cwd=self.dev, env=self.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # -- the tool ----------------------------------------------------------
    def run(self, *args, script="batch.py", cwd=None, gh_fail=None, env=None):
        """`gh_fail` is a FAKE_GH_FAIL spec for this one call: `|`-separated argv prefixes the fake
        gh answers with an HTTP 502. `env`, when given, is the call's whole environment in place of the fixture's."""
        cmd = [sys.executable, os.path.join(self.dev, "scripts", script)] if script.endswith(".py") \
            else [os.path.join(self.dev, "scripts", script)]
        env = env or self.env
        env = dict(env, FAKE_GH_FAIL=gh_fail) if gh_fail else env
        return subprocess.run([*cmd, *args], cwd=cwd or self.tmp, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def ok(self, *args, **kw):
        p = self.run(*args, **kw)
        if p.returncode != 0:
            raise AssertionError("%s exited %d:\n%s%s" % (" ".join(args), p.returncode, p.stdout, p.stderr))
        return p

    def state(self, name):
        with open(os.path.join(self.dev, ".git", "batch", name + ".json")) as f:
            return json.load(f)

    def wt(self, name):
        return os.path.join(self.tmp, "romp-batch-" + name)

    def chain(self, name):
        """Subjects on the first-parent chain from origin/main to the batch tip, oldest first."""
        out = self.dev_git("log", "--first-parent", "--reverse", "--format=%s", "origin/main..batch/" + name)
        return out.splitlines() if out else []

    def push_batch(self, name):
        self.dev_git("push", "-q", "-u", "origin", "batch/" + name)

    def ci(self, name, conclusion="success", status="completed", sha=None, event="push", branch=None, workflow="ci.yml",
           **fields):
        """A GitHub Actions run the fake gh lists: by default the batch head's run, ci.yml from a push to batch/<name>
        at its current head, completed green, on its first attempt, its latest attempt's job runs SEED_CI_JOBS (the seed's
        ci.yml's jobs, each passed). Each new run is newer than the last (databaseId and createdAt). `fields` replaces row
        fields (databaseId, createdAt, attempt, ...; `attempts`, the earlier attempts' records the fake's attempts endpoint
        serves; `jobs`, the latest attempt's job runs, or `jobs_doc`, the whole jobs answer); one given as MISSING is left
        out of the row."""
        self.gh_state = self.gh()
        runs = self.gh_state.setdefault("runs", [])
        n = len(runs) + 1
        row = {"databaseId": n, "workflow": workflow, "workflowName": {"ci.yml": "CI"}.get(workflow, "PR tier"), "event": event,
               "headBranch": branch or "batch/" + name, "headSha": sha or self.dev_git("rev-parse", "batch/" + name),
               "status": status, "conclusion": conclusion, "createdAt": "2026-01-01T00:%02d:00Z" % n,
               "url": "https://example.invalid/actions/runs/%d" % n, "attempt": 1, "jobs": [dict(j) for j in SEED_CI_JOBS]}
        for key, value in fields.items():
            if value is MISSING:
                row.pop(key, None)
            else:
                row[key] = value
        runs.append(row)
        self._save_gh()
        return row["url"]

    def sweep(self, name, sha=None, webview=False, **over):
        """A sweep result for batch/<name>'s current head (or `sha`), written through scripts/sweep.py's own
        writer where the runner writes it: every leg rc 0 but deps, the webview legs, pdf-smoke and served, not owed for
        the one reason the runner gives (the fixture's worlds have no vscode-extension/package.json), unless `webview` is
        True, which records the webview legs, pdf-smoke and served owed and rc 0; `over` replaces top-level keys, and the verdict is the
        runner's rule over the result unless given."""
        sha = sha or self.dev_git("rev-parse", "batch/" + name)
        return self.result(sha, "batch/" + name, webview=webview, tree=self.wt(name), **over)

    def result(self, sha, branch, webview, tree, runs=None, **over):
        """The result the runner would write for `sha`, recorded for `branch`: one full run (schema 2 keeps every run
        at the sha in `runs`), every leg rc 0 but deps, not owed, and the webview legs, pdf-smoke and served owed and rc 0
        when `webview`, else not owed; deps, the webview legs, pdf-smoke and served are marked not owed for the one reason the runner
        gives, a sha with no vscode-extension/package.json. `over` replaces keys of that run, `runs` the whole history; a run's verdict is
        its own legs' unless given."""
        if runs is None:
            stamp = sweep.now()
            legs = {n: {"owed": True, "rc": 0, "cmd": ["true"], "started": stamp, "finished": stamp} for n in sweep.LEGS}
            for n in sweep.TEST_LEGS:
                legs[n].update(tests=1, failed=0)
            for n in () if webview else sweep.EXTENSION_LEGS[1:]:      # the webview legs, pdf-smoke and served
                legs[n] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
            # the fixture's worlds have no vscode-extension/, and this is the one reason the runner gives for deps
            legs["deps"] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
            run = {"kind": "full", "sha": sha, "branch": branch, "tree": tree, "started": stamp, "finished": stamp,
                   "flakes": {}, "legs": legs, "red": [], "invalid": None}
            run.update(over)
            runs = [self.run_record(**run)]
        data = {"schema": sweep.SCHEMA, "sha": sha, "branch": branch, "tree": tree, "runs": runs}
        path = sweep.result_path(sha, env=self.env)
        sweep.write_result(path, data)
        return path

    @staticmethod
    def run_record(**run):
        """A run as the runner writes it: the leg environment's hash the reader compares (round 1, decision 10) and the
        private checkout it ran in (a reader refuses a run without one) unless `runner` is given, and the run's own
        verdict unless `verdict` is."""
        run.setdefault("runner", {"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()},
                                  "checkout": {"form": "clone", "per": "ci.yml job", "files": 1, "groups": [
                                      {"job": "python", "legs": [sweep.PYTEST_LEGS[0]], "path": "/nonexistent/trees/test",
                                       "create_s": 0.1, "verify_s": 0.1, "setup": None}]}})
        run.setdefault("verdict", sweep.run_verdict(run))
        return run


class _Base(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def two_members(self):
        """#101 on `a` (fix, trailer) and #102 on `b`, stacked on `a`."""
        fx = self.fx
        fx.branch("a", {"kernel/kernel.py": "VERSION = 2\n"})
        fx.branch("b", {"postal/postal_service.py": "def send():\n    return 2\n"}, base="a")
        fx.pr(101, "a", title="kernel: bump the version", labels=["fix"], body="Body.\n\n" + TRAILER)
        fx.pr(102, "b", base="a", title="postal: send two", labels=["feature"], body=TRAILER)


class Plan(_Base):
    def test_orders_dependents_after_bases_and_excludes_drafts_major_feature_and_hold(self):
        fx = self.fx
        self.two_members()
        for name in "cdef":
            fx.branch(name, {name + ".txt": name + "\n"})
        fx.pr(103, "c", draft=True)
        fx.pr(104, "d", labels=["major-feature"])
        fx.pr(105, "e", labels=["hold"])
        fx.pr(106, "f", title="depends on 101 by body", body="Depends-on: #101\n\nmore")
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [101, 102, 106])
        excluded = {row["n"]: row["reason"] for row in st["excluded"]}
        self.assertEqual(set(excluded), {103, 104, 105})
        self.assertIn("draft", excluded[103])
        self.assertIn("major-feature", excluded[104])
        self.assertIn("hold", excluded[105])
        m = st["members"]
        self.assertEqual(m["102"]["depends_on"], [101], "a base that is another candidate's branch is a dependency")
        self.assertEqual(m["106"]["depends_on"], [101], "Depends-on: #N in the body is a dependency")
        self.assertEqual(m["101"]["head"], fx.bare_rev("a"), "heads are pinned at plan time")
        self.assertEqual(m["101"]["trailer"]["tier"], "fix")
        self.assertIsNone(m["106"]["trailer"])
        self.assertIsNone(m["106"]["tier"])
        self.assertIn("kernel/kernel.py", m["101"]["touches"])
        self.assertNotIn("ci", m["101"], "a member runs no ci.yml of its own, so plan records none")
        self.assertEqual(st["base"], fx.bare_rev("main"))

    def test_docs_and_tests_only_are_tiers_a_member_can_carry(self):
        """`docs` is upstream's name for tier 0 (renamed from tests-only on 2026-09-08; the old spelling
        stays accepted as an alias), so a member labeled either way is planned with that tier and
        never listed as unlabeled (2026-09-07 sync; the fork's pr-tier.yml counts the same labels)."""
        fx = self.fx
        fx.branch("a", {"docs/a.md": "a\n"})
        fx.branch("b", {"docs/b.md": "b\n"})
        fx.pr(101, "a", labels=["docs"])
        fx.pr(102, "b", labels=["tests-only"])
        p = fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [101, 102])
        self.assertEqual(st["excluded"], [])
        self.assertEqual(st["members"]["101"]["tier"], "docs")
        self.assertEqual(st["members"]["102"]["tier"], "tests-only")
        self.assertNotIn("unlabeled", p.stdout)
        self.assertIn("[docs]", p.stdout)

    def test_a_dependent_of_an_excluded_pr_is_excluded_with_it(self):
        fx = self.fx
        fx.branch("e", {"e.txt": "e\n"})
        fx.branch("g", {"g.txt": "g\n"}, base="e")
        fx.pr(105, "e", labels=["hold"])
        fx.pr(107, "g", base="e", labels=["fix"])
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [])
        reasons = {row["n"]: row["reason"] for row in st["excluded"]}
        self.assertIn("depends on #105", reasons[107])
        self.assertIn("hold", reasons[107])

    def test_labeled_takes_only_prs_labeled_land(self):
        fx = self.fx
        self.two_members()
        fx.pr(101, "a", labels=["fix", "land"], body=TRAILER)
        fx.ok("plan", "--labeled", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [101])
        self.assertTrue(st["labeled"])
        reasons = {row["n"]: row["reason"] for row in st["excluded"]}
        self.assertIn("not labeled land", reasons[102])

    def test_a_base_that_belongs_to_a_merged_pr_is_excluded_with_the_fix(self):
        fx = self.fx
        fx.branch("old", {"old.txt": "old\n"})
        fx.branch("h", {"h.txt": "h\n"}, base="old")
        fx.pr(100, "old", state="MERGED", merge_commit=fx.bare_rev("main"))
        fx.pr(108, "h", base="old", labels=["fix"])
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [])
        reasons = {row["n"]: row["reason"] for row in st["excluded"]}
        self.assertIn("merged PR #100", reasons[108])
        self.assertIn("gh pr edit 108 --base main", reasons[108])

    def test_only_plans_a_single_pr_as_a_one_member_batch(self):
        """A single PR lands through batch.py as a one-member batch (pre-round ruling Q8; scripts/land.sh runs batch.py
        land): plan --only N plans N alone; a dependency not named is not taken in, so its dependent is left out
        with it; a number that is not an open PR is refused."""
        fx = self.fx
        self.two_members()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", title="k alone", labels=["fix"], body=TRAILER)
        p = fx.ok("plan", "--only", "111", "--name", "one")
        st = fx.state("one")
        self.assertEqual(st["order"], [111])
        self.assertEqual({e["n"]: e["reason"] for e in st["excluded"]},
                         {101: "not named by plan --only", 102: "not named by plan --only"})
        self.assertIn("excluded, not named by plan --only: #101, #102", p.stdout)
        fx.ok("plan", "--only", "102", "--name", "two")
        st = fx.state("two")
        self.assertEqual(st["order"], [])
        self.assertEqual({e["n"]: e["reason"] for e in st["excluded"]}[102], "depends on #101 (not named by plan --only)")
        fx.ok("plan", "--only", "101", "--only", "102", "--name", "pair")
        self.assertEqual(fx.state("pair")["order"], [101, 102])
        p = fx.run("plan", "--only", "999", "--name", "three")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("--only #999: not an open PR", p.stderr)

    def test_a_name_holding_an_equals_sign_is_refused_by_plan(self):
        """plan refuses a --name that holds '=' (the closing check at round 3 of PR 959, cc959-r3-n1), naming it and
        why, and writes no state: the batch's two merges pass git -c branch.batch/<name>.mergeOptions= (merge_settings),
        and git splits a -c pair at its first '=', so for x=y it reads the key branch.batch/x, refuses it and starts no
        merge (the premise, run here under the git on PATH). pick_name never makes such a name. Red at round 3's head:
        plan exited 0 and wrote the state, and assemble then exited 1 at its first merge with git's "invalid key". plan
        refuses before its fetch, so the clone's FETCH_HEAD stays absent (the check of the closing check's fix,
        chk-r3e-2); red when plan fetches first, as it did at that check's head."""
        fx = self.fx
        self.two_members()
        premise = subprocess.run(["git", "-c", "branch.batch/x=y.mergeOptions=", "config", "--get-regexp", "^branch"],
                                 cwd=fx.dev, env=fx.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(premise.returncode, 128, premise)
        self.assertIn("invalid key: branch.batch/x\n", premise.stderr, "premise: git splits the -c pair at its first '='")
        fetch_head = os.path.join(fx.dev, ".git", "FETCH_HEAD")
        self.assertFalse(os.path.lexists(fetch_head), "premise: the clone has never fetched")
        p = fx.run("plan", "--name", "x=y")
        self.assertFalse(os.path.lexists(fetch_head), "plan refused before its fetch")
        self.assertEqual((p.returncode, p.stdout, p.stderr), (2, "", (
            "batch: --name x=y holds '=', which a batch name cannot: the batch's merges pass git -c "
            "branch.batch/x=y.mergeOptions=, and git splits a -c pair at its first '=', so it would read the key "
            "branch.batch/x and refuse it; pass a name without '=', or no --name for today's date and a letter\n")))
        self.assertFalse(os.path.lexists(os.path.join(fx.dev, ".git", "batch", "x=y.json")), "no state was written")

    def test_a_state_named_with_an_equals_sign_is_refused_by_assemble_and_pull_before_any_write(self):
        """A state whose name holds '=' can still be on disk from a plan that did not refuse it (fork main's plan wrote
        one), so assemble refuses it too, right after it loads the state and before any write, naming the batch and
        asking for a new plan, since assemble and pull take the name as an argument and have no --name (chk-r3e-3);
        pull reaches the refusal through assemble (the check of the closing check at round 3 of PR 959, chk-r3c-1). The
        state is planted as such a plan leaves it: planned as xy, then renamed to x=y.json with its name set to x=y.
        origin's main then moves, so a fetch would move refs/remotes/origin/main, and the pin asserts that it did not:
        the refusal comes before assemble's fetch (the check of that check's fix, chk-r3e-1; red when the refusal and
        the fetch swap places, the mutant mFetchFirst, at the assemble leg). Red before: assemble made the batch/x=y
        branch and the romp-batch-x=y worktree and then exited 1 at its first merge with git's "invalid key:
        branch.batch/x"."""
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "xy")
        sdir = os.path.join(fx.dev, ".git", "batch")
        st = fx.state("xy")
        self.assertEqual(st["order"], [101, 102], "premise: both members are planned")
        st["name"] = "x=y"
        with open(os.path.join(sdir, "x=y.json"), "w") as f:
            json.dump(st, f, indent=1, sort_keys=True)
            f.write("\n")
        os.remove(os.path.join(sdir, "xy.json"))
        with open(os.path.join(sdir, "x=y.json"), "rb") as f:
            planted = f.read()
        fx.commit_main({"moved.txt": "main moved after the plan\n"})
        tracking = fx.dev_git("rev-parse", "refs/remotes/origin/main")
        self.assertNotEqual(tracking, fx.bare_rev("main"), "premise: origin's main moved past the tracking ref")
        refusal = ("batch: the batch x=y holds '=', which a batch name cannot: the batch's merges pass git -c "
                   "branch.batch/x=y.mergeOptions=, and git splits a -c pair at its first '=', so it would read the key "
                   "branch.batch/x and refuse it; plan it again under a name without '='\n")
        for argv in (("assemble", "x=y"), ("pull", "x=y", "102")):
            p = fx.run(*argv)
            self.assertEqual((p.returncode, p.stdout, p.stderr), (2, "", refusal), argv)
            self.assertEqual(fx.dev_git("rev-parse", "--verify", "--quiet", "refs/heads/batch/x=y", check=False), "",
                             "%s made no batch/x=y branch" % (argv,))
            self.assertFalse(os.path.lexists(fx.wt("x=y")), "%s made no romp-batch-x=y worktree" % (argv,))
            with open(os.path.join(sdir, "x=y.json"), "rb") as f:
                self.assertEqual(f.read(), planted, "%s left the state as planted" % (argv,))
            self.assertEqual(fx.dev_git("rev-parse", "refs/remotes/origin/main"), tracking,
                             "%s refused before its fetch: origin/main did not move" % (argv,))

    def test_a_one_member_batch_lands_through_the_whole_route(self):
        fx = self.fx
        self.two_members()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", title="k alone", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--only", "111", "--name", "one")
        fx.ok("assemble", "one")
        fx.push_batch("one")
        fx.sweep("one")
        fx.ok("verify", "one")
        fx.ok("summarize", "one")
        fx.ci("one")
        fx.ok("land", "one")
        gh = fx.gh()
        self.assertEqual(gh["prs"]["111"]["state"], "MERGED", "marked merged by the batch PR's merge")
        self.assertEqual((gh["prs"]["101"]["state"], gh["prs"]["102"]["state"]), ("OPEN", "OPEN"))
        self.assertEqual([c[2] for c in fx.calls("pr", "merge")], [str(gh["next_number"] - 1)], "the one merge is the batch PR's")

    def test_a_batch_pr_is_never_a_member_of_the_next_batch(self):
        fx = self.fx
        fx.branch("batch/2020-01-01a", {"x.txt": "x\n"})
        fx.pr(120, "batch/2020-01-01a", labels=["batch"])
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.state("b1")["order"], [])

    def test_predicts_a_conflict_against_the_accumulating_tree(self):
        fx = self.fx
        fx.branch("a2", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("a3", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a2", labels=["fix"], body=TRAILER)
        fx.pr(108, "a3", labels=["fix"], body=TRAILER)
        p = fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertIsNone(st["members"]["101"]["predicted_conflict"])
        self.assertEqual(st["members"]["108"]["predicted_conflict"]["files"], ["notes.txt"])
        self.assertEqual(st["members"]["108"]["predicted_conflict"]["with"], [101])
        self.assertIn("PREDICTED CONFLICT in notes.txt with #101", p.stdout)
        self.assertEqual(fx.dev_git("status", "--porcelain", "--untracked-files=no"), "", "the prediction touches no worktree")
        self.assertEqual(fx.dev_git("for-each-ref", "--format=%(refname)", "refs/heads/"), "refs/heads/main", "and writes no ref")

    def test_a_dependency_that_already_merged_counts_as_satisfied(self):
        """`Depends-on: #N` stays in a body after #N lands alone (the docs ask for it there); the
        dependent must not be stranded out of every batch for it. A closed, unmerged dependency
        still excludes, by name."""
        fx = self.fx
        fx.branch("done", {"done.txt": "d\n"})
        fx.fake_gh("pr", "create", "--head", "done", "--title", "landed alone")     # #900
        fx.fake_gh("pr", "merge", "900", "--merge")
        fx.branch("h", {"h.txt": "h\n"})
        fx.pr(108, "h", labels=["fix"], body="Depends-on: #900\n\nmore", title="after the landed one")
        fx.branch("j", {"j.txt": "j\n"})
        fx.pr(109, "j", labels=["fix"], body="Depends-on: #300\n")
        fx.pr(300, "nowhere", state="CLOSED")
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [108])
        self.assertEqual(st["members"]["108"]["depends_on"], [])
        self.assertEqual(st["members"]["108"]["depends_on_merged"], [900])
        reasons = {row["n"]: row["reason"] for row in st["excluded"]}
        self.assertEqual(reasons[109], "depends on #300 (closed, not merged)")

    def test_a_dependency_cycle_excludes_its_members_and_plans_the_rest(self):
        """A `Depends-on:` typo (a PR naming itself, two PRs naming each other) used to abort the whole
        plan; the PRs in the cycle are excluded with the cycle named, their dependents with them, and
        the innocent members are planned."""
        fx = self.fx
        for br in ("a", "k", "x", "y", "z"):
            fx.branch(br, {br + ".txt": br + "\n"})
        fx.pr(101, "a", labels=["fix"], body="Depends-on: #101\n\n" + TRAILER)
        fx.pr(111, "k", labels=["fix"], body=TRAILER)
        fx.pr(120, "x", labels=["fix"], body="Depends-on: #121\n\n" + TRAILER)
        fx.pr(121, "y", labels=["fix"], body="Depends-on: #120\n\n" + TRAILER)
        fx.pr(125, "z", labels=["fix"], body="Depends-on: #120\n\n" + TRAILER)
        p = fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [111])
        excluded = {e["n"]: e["reason"] for e in st["excluded"]}
        self.assertEqual(excluded[101], "depends on itself (Depends-on: #101)")
        self.assertEqual(excluded[120], "in a dependency cycle with #121")
        self.assertEqual(excluded[121], "in a dependency cycle with #120")
        self.assertEqual(excluded[125], "depends on #120 (in a dependency cycle with #121)")
        self.assertIn("excluded #120: in a dependency cycle with #121", p.stdout)
        self.assertIn("1 member(s), 4 excluded", p.stdout)

    def test_a_reused_base_branch_name_is_an_open_prs_branch_not_the_merged_prs(self):
        """Branch names recur on the fork. A base that is an open PR's head is a dependency even if a
        merged PR once used the name; a base whose branch moved on with no open PR is excluded by
        that reason, not as the merged PR's branch."""
        fx = self.fx
        old_head = fx.branch("old", {"old.txt": "old\n"})
        fx.pr(100, "old", state="MERGED", merge_commit=fx.bare_rev("main"), head_oid=old_head)
        fx.commit("old", {"old.txt": "old again\n"}, "the name is reused for new work")
        fx.branch("h", {"h.txt": "h\n"}, base="old")
        fx.pr(109, "old", labels=["fix"], body=TRAILER, title="new work on a reused name")
        fx.pr(108, "h", base="old", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [109, 108])
        self.assertEqual(st["members"]["108"]["depends_on"], [109])
        fx.ok("assemble", "b1")
        st = fx.state("b1")
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [109, 108], "assemble does not hold the stacked member back")
        self.assertEqual(st["assembly"]["held"], [])
        # The same reused name with NO open PR on it: excluded for that, not as merged PR #100's branch.
        fx.pr(109, "old", state="CLOSED")
        fx.ok("plan", "--name", "b2")
        reasons = {row["n"]: row["reason"] for row in fx.state("b2")["excluded"]}
        self.assertIn("was merged PR #100's branch and now holds other commits with no open PR", reasons[108])


class PlanReadsTheMemberSweep(_Base):
    """A member PR owes a passing sweep of its own head before its review round and before its closing check
    (pre-round ruling Q7). The steps that take a member in read it through the reader verify uses: plan leaves out
    a candidate without a passing result at its pinned head, naming the case (and its dependents with it), and
    assemble --repin refuses a re-read head without one. The Fixture records a passing result for every head an
    author pushes unless told `swept=False`."""

    def test_a_member_without_a_passing_sweep_at_its_head_is_left_out_and_its_dependents_with_it(self):
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.branch("c", {"c.txt": "c\n"}, swept=False)
        fx.branch("d", {"d.txt": "d\n"}, base="c")
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(103, "c", labels=["fix"], body=TRAILER)
        fx.pr(104, "d", base="c", labels=["fix"], body=TRAILER)
        p = fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [101])
        excl = {e["n"]: e["reason"] for e in st["excluded"]}
        self.assertIn("no passing sweep at its head (sweep missing: no result for #103's head %s in %s (the state dir from "
                      "XDG_STATE_HOME)" % (fx.bare_rev("c"), sweep.sweeps_dir(env=fx.env)), excl[103])
        self.assertEqual(excl[104], "depends on #103 (%s)" % excl[103], "the dependent goes with it")
        self.assertIn("excluded #103: no passing sweep at its head (sweep missing", p.stdout)

    def test_the_members_table_shows_the_pass_plan_read_at_each_head_not_the_trailer(self):
        """Round 1, fresh-3, end to end: #101 has no trailer and #102 a trailer whose sweep_head is another sha. plan
        records the pass it read at each pinned head, the body's column shows it, and assemble --repin records the pass
        at the new head. At the frozen head the column read "not stated" for #101 and the trailer's sha for #102."""
        fx = self.fx
        a = fx.branch("a", {"a.txt": "a\n"})
        b = fx.branch("b", {"b.txt": "b\n"})
        fx.pr(101, "a", labels=["fix"])
        fx.pr(102, "b", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        legs = ("pytest rc 0, bats rc 0, manager rc 0, tools rc 0, ledger rc 0, typecheck rc 0, npm-test rc 0, pdf-smoke rc 0, "
                "build rc 0, served rc 0; not owed: deps")
        self.assertIn("| #101 | PR 101 on a | fix | not stated | pass @%s: %s |" % (a[:10], legs), body)
        self.assertIn("| #102 | PR 102 on b | fix | 3 | pass @%s: %s |" % (b[:10], legs), body)
        self.assertNotIn("@0123456789", body, "the trailer's sweep_head, another sha, is not shown")
        self.assertNotIn("12 passed", body, "nor its self-reported counts")
        rec = fx.state("b1")["members"]["101"]["sweep"]
        self.assertEqual((rec["head"], rec["path"]), (a, sweep.result_path(a, env=fx.env)))
        new = fx.commit("b", {"b.txt": "b two\n"}, "a fix after review")
        fx.ok("assemble", "b1", "--repin", "102")
        self.assertEqual(fx.state("b1")["members"]["102"]["sweep"]["head"], new, "--repin records the pass at the new head")

    def test_a_member_whose_result_excuses_deps_for_a_package_json_its_head_holds_is_left_out(self):
        """Round 1's excuse rule: the runner marks deps not owed only for having no vscode-extension/package.json, and
        plan accepts that reason only when the member's head really has no such file."""
        fx = self.fx
        head = fx.branch("x", {"vscode-extension/package.json": "{}\n"}, swept=False)
        fx.result(head, "x", webview=True, tree=fx.author)        # deps marked not owed for having no package.json
        fx.pr(112, "x", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        excl = {e["n"]: e["reason"] for e in fx.state("b1")["excluded"]}
        self.assertIn("no passing sweep at its head (sweep invalid at %s: the result marks deps not owed for having no "
                      "vscode-extension/package.json, but #112's head's tree holds vscode-extension/package.json" % head[:10], excl[112])

    def test_a_red_a_stale_and_a_webview_skipping_result_are_each_named(self):
        """A member's head owes every leg, the webview legs included, as a batch head does (round 1, decision 11): a
        result that marks them not owed by a changed-path rule is refused at a head that changed only an unread path,
        where the head's plan took it."""
        fx = self.fx
        red_head = fx.branch("e", {"e.txt": "e\n"}, swept=False)
        with open(fx.swept("e")) as f:
            legs = json.load(f)["runs"][-1]["legs"]
        legs["bats"]["rc"] = 1
        fx.result(red_head, "e", webview=True, tree=fx.author, legs=legs)
        old = fx.branch("f", {"f.txt": "f\n"})
        fx.commit("f", {"f.txt": "f2\n"}, swept=False)
        g_head = fx.branch("g", {"g.txt": "g\n"})
        untouched = "kernel/kernel.py, ui/ and vscode-extension/ untouched since %s" % fx.bare_rev("main")[:10]
        with open(sweep.result_path(g_head, env=fx.env)) as f:
            legs = json.load(f)["runs"][-1]["legs"]
        for n in sweep.WEBVIEW_LEGS:
            legs[n] = {"owed": False, "rc": None, "why": untouched}
        fx.result(g_head, "g", webview=True, tree=fx.author, legs=legs)
        fx.pr(105, "e", labels=["fix"], body=TRAILER)
        fx.pr(106, "f", labels=["fix"], body=TRAILER)
        fx.pr(107, "g", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        st = fx.state("b1")
        self.assertEqual(st["order"], [])
        excl = {e["n"]: e["reason"] for e in st["excluded"]}
        self.assertIn("no passing sweep at its head (sweep red at %s: bats (rc 1)" % red_head[:10], excl[105])
        self.assertIn("no passing sweep at its head (sweep stale: the newest result for f is at %s" % old[:10], excl[106])
        self.assertIn("no passing sweep at its head (sweep invalid at %s: typecheck, npm-test, build marked not owed for a reason "
                      "other than 'no vscode-extension/package.json' ('%s')" % (g_head[:10], untouched), excl[107])

    def test_repin_refuses_a_new_head_without_a_passing_sweep(self):
        fx = self.fx
        first = fx.branch("a", {"a.txt": "a\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        new = fx.commit("a", {"a.txt": "a2\n"}, swept=False)
        p = fx.run("assemble", "b1", "--repin", "101")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("#101's head %s has no passing sweep of its own (sweep stale: the newest result for a is at %s"
                      % (new[:10], first[:10]), p.stderr)
        self.assertIn("nothing re-pinned", p.stderr)
        self.assertEqual(fx.state("b1")["members"]["101"]["head"], first, "the pin did not move")
        fx.swept("a", new)
        fx.ok("assemble", "b1", "--repin", "101")
        self.assertEqual(fx.state("b1")["members"]["101"]["head"], new)


# A git first on PATH for the stale-record cases of the merges pin (round 3 of PR 959, tests-1): it adds -Xours after the
# subcommand of a git merge whose words hold ROAD_ON (an id), so that git merge resolves by itself a conflict merge-tree
# reports, as an option of the user's did before batch.py's merges read the options merge-tree reads (MERGE_STRATEGY's
# comment in scripts/batch.py); it runs every other call, and every word it is given, through ROAD_REAL_GIT unchanged.
ROAD_GIT = r"""#!/bin/sh
case " $* " in
  *" merge "*"$ROAD_ON"*) ;;
  *) exec "$ROAD_REAL_GIT" "$@" ;;
esac
started= added=
for a in "$@"; do
  if [ -z "$started" ]; then started=1; set --; fi
  if [ -z "$added" ] && [ "$a" = merge ]; then set -- "$@" merge -Xours; added=1; else set -- "$@" "$a"; fi
done
exec "$ROAD_REAL_GIT" "$@"
"""


class Assemble(_Base):
    def test_refuses_when_another_batch_ref_exists_on_origin(self):
        fx = self.fx
        fx.branch("batch/2020-01-01a", {"x.txt": "x\n"})
        fx.branch("a", {"a.txt": "a\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("origin/batch/2020-01-01a", p.stderr)
        self.assertFalse(os.path.exists(fx.wt("b1")))
        # The batch's OWN branch on origin is not a refusal: a rebuild after a push is normal.
        fx.dev_git("push", "-q", "origin", "--delete", "batch/2020-01-01a")
        fx.branch("batch/b1", {"y.txt": "y\n"})
        fx.ok("assemble", "b1")

    def test_merges_the_pinned_heads_in_order_with_no_ff_merges(self):
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        self.assertEqual(fx.chain("b1"), ["Merge #101: kernel: bump the version", "Merge #102: postal: send two"])
        st = fx.state("b1")
        merged = st["assembly"]["merged"]
        self.assertEqual([e["n"] for e in merged], [101, 102])
        for e in merged:
            parents = fx.dev_git("rev-list", "--parents", "-n1", e["merge"]).split()[1:]
            self.assertEqual(len(parents), 2)
            self.assertEqual(parents[1], st["members"][str(e["n"])]["head"], "second parent is the pinned head")
            self.assertIsNone(e["resolved"])
        self.assertTrue(os.path.isdir(fx.wt("b1")))
        self.assertEqual(fx.dev_git("config", "rerere.enabled"), "true")
        self.assertEqual(fx.dev_git("config", "rerere.autoUpdate"), "true")
        self.assertEqual(st["assembly"]["head"], fx.dev_git("rev-parse", "batch/b1"))
        self.assertEqual(fx.dev_git("rev-parse", "--abbrev-ref", "HEAD"), "main", "the tool's own checkout is untouched")

    def test_a_conflict_holds_the_member_back_and_tells_the_owner_once(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        st = fx.state("b1")
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101])
        held = st["assembly"]["held"]
        self.assertEqual(len(held), 1)
        self.assertEqual(held[0]["n"], 108)
        self.assertEqual(held[0]["files"], ["notes.txt"])
        self.assertEqual(held[0]["with"], [101])
        self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a"])
        comments = fx.gh()["prs"]["108"]["comments"]
        self.assertEqual(len(comments), 1)
        self.assertIn("#101", comments[0])
        self.assertIn("notes.txt", comments[0])
        self.assertIn("Merge origin/main", comments[0], "tells the owner what to do")
        fx.ok("assemble", "b1")
        self.assertEqual(len(fx.gh()["prs"]["108"]["comments"]), 1, "a rebuild does not repeat the comment")

    def test_resolve_stops_for_a_hand_resolution_and_continue_records_it(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        wt = fx.wt("b1")
        self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "MERGE_HEAD")))
        self.assertEqual(fx.gh()["prs"]["108"]["comments"], [], "a stopped merge is not a hold-back")
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertNotEqual(p.returncode, 0, "verify refuses while a member is stopped")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        st = fx.state("b1")
        rec = [e for e in st["assembly"]["merged"] if e["n"] == 108][0]
        self.assertEqual(rec["resolved"]["files"], ["notes.txt"])
        self.assertEqual(rec["resolved"]["hunks"], 1)
        self.assertEqual(rec["resolved"]["review"], "subagent: fine")
        self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a", "Merge #108: notes: the g version"])
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); one review round: subagent: fine. [diff from the clean merge below]", body)
        self.assertIn("### #108", body)
        self.assertIn("two-a-g", body, "the combined diff of the resolved merge is in the details")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("#108 merge carries a recorded resolution", p.stdout)

    def test_abort_drops_the_stopped_member_and_goes_on(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", labels=["fix"], body=TRAILER)
        fx.pr(111, "k", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        fx.ok("assemble", "b1", "--abort")
        st = fx.state("b1")
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101, 111])
        self.assertEqual([h["n"] for h in st["assembly"]["held"]], [108])

    def test_a_straggler_upstream_row_is_converted_inside_the_merge(self):
        fx = self.fx
        pre_migration = fx.bare_rev("main")
        # The member was cut before the migration and appends a row to the old table.
        member_md = SEED["UPSTREAM.md"].replace("|---|---|---|---|\n", "|---|---|---|---|\n| row two | fork PR #110 | candidate | why |\n")
        fx.branch("s", {"UPSTREAM.md": member_md}, base=pre_migration)
        # The migration lands on main: the table is gone and the ledger script exists.
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": FAKE_LEDGER}, "ledger migration")
        fx.pr(110, "s", title="a straggler row", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        st = fx.state("b1")
        merged = st["assembly"]["merged"]
        self.assertEqual([e["n"] for e in merged], [110])
        self.assertIn("converted", merged[0]["resolved"]["how"])
        self.assertEqual(fx.dev_git("show", "batch/b1:UPSTREAM.md"), prose_only.strip(), "the table hunk is dropped")
        entry = fx.dev_git("show", "batch/b1:upstream/2026-01-01-row-two.md")
        self.assertIn("title: row two", entry)
        self.assertIn("status: candidate", entry)
        self.assertEqual(fx.chain("b1"), ["Merge #110: a straggler row"], "the conversion is inside the member's merge commit")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   ledger: check clean", p.stdout)

    def test_without_drops_a_member_and_its_dependents(self):
        fx = self.fx
        self.two_members()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1", "--without", "101")
        st = fx.state("b1")
        self.assertEqual(st["pulled"], [101, 102])
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [111])
        self.assertTrue(any("#102 dropped with #101" in l for l in st["assembly"]["log"]))

    def test_repin_takes_a_members_new_head(self):
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        old = fx.state("b1")["members"]["101"]["head"]
        new = fx.commit("a", {"a.txt": "a2\n"})
        fx.ok("assemble", "b1", "--repin", "101")
        st = fx.state("b1")
        self.assertNotEqual(old, new)
        self.assertEqual(st["members"]["101"]["head"], new)
        self.assertEqual(fx.dev_git("rev-parse", "batch/b1^2"), new)

    def conflict_pair(self):
        """#101 on `a` and #108 on `g`, both editing notes.txt line two."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)

    def test_continue_refuses_a_non_conflicted_file_staged_into_the_resolved_merge(self):
        """The subset rule: a resolution may change only the files that conflicted. A file staged
        alongside it would otherwise ride inside the member's merge commit, pass verify as 'carries
        a recorded resolution', and never appear in the body."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        with open(os.path.join(wt, "kernel", "kernel.py"), "w") as f:
            f.write("VERSION = 1\nSMUGGLED = True\n")
        fx._git("add", "notes.txt", "kernel/kernel.py", cwd=wt)
        p = fx.run("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("also changes kernel/kernel.py, outside the conflicted files (notes.txt)", p.stderr)
        self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "MERGE_HEAD")), "the merge is left in progress to fix")
        self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a"], "nothing was committed")
        m = re.search(r"git restore --source=([0-9a-f]{40}) --staged --worktree -- kernel/kernel.py", p.stderr)
        self.assertIsNotNone(m, "the refusal names the tree holding the merge's own content: %s" % p.stderr)
        fx._git("restore", "--source=" + m.group(1), "--staged", "--worktree", "--", "kernel/kernel.py", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        self.assertEqual(fx.dev_git("show", "batch/b1:kernel/kernel.py"), "VERSION = 1")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("#108 merge carries a recorded resolution (resolved by the batcher, per hunk) in notes.txt", p.stdout)

    def test_a_stray_staged_path_holding_a_marker_line_is_refused_as_stray_not_as_a_marker(self):
        """The two refusals at --continue have different advice: a stray path is restored from the
        merge's own tree, a staged marker is resolved and re-added. The marker scan used to run over
        every differing path BEFORE the subset rule, so a fixture about conflict markers staged
        alongside the resolution was refused as 'a conflict marker is still staged', with advice that
        cannot be followed; the stray refusal comes first, and markers are looked for only in the
        conflicted files and the paths the subset rule allows."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        os.makedirs(os.path.join(wt, "tests", "fixtures"))
        with open(os.path.join(wt, "tests", "fixtures", "markers.txt"), "w") as f:
            f.write("<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> theirs\n")
        fx._git("add", "notes.txt", "tests/fixtures/markers.txt", cwd=wt)
        p = fx.run("assemble", "b1", "--continue", "--reviewed", "r")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("also changes tests/fixtures/markers.txt, outside the conflicted files (notes.txt)", p.stderr)
        self.assertNotIn("conflict marker", p.stderr)
        m = re.search(r"git restore --source=([0-9a-f]{40}) --staged --worktree -- tests/fixtures/markers.txt", p.stderr)
        self.assertIsNotNone(m, p.stderr)
        self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a"], "nothing was committed")
        # The advice works: the tree has no such path, so the restore is a removal from the index.
        fx._git("rm", "-q", "--cached", "--", "tests/fixtures/markers.txt", cwd=wt)
        os.remove(os.path.join(wt, "tests", "fixtures", "markers.txt"))
        fx.ok("assemble", "b1", "--continue", "--reviewed", "r")
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree")

    def test_verify_catches_a_stray_file_amended_into_a_resolved_merge_and_the_body_shows_it(self):
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        with open(os.path.join(wt, "kernel", "kernel.py"), "w") as f:
            f.write("VERSION = 1\nSMUGGLED = True\n")
        fx._git("add", "kernel/kernel.py", cwd=wt)
        fx._git("commit", "-q", "--amend", "--no-edit", cwd=wt)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL provenance: #108 merge", p.stdout)
        self.assertIn("changes kernel/kernel.py outside its recorded resolution (notes.txt)", p.stdout)
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("SMUGGLED", body, "the combined diff covers every path that differs from the clean merge")
        self.assertIn("NOT VERIFIED", body)

    def test_a_failed_hold_back_comment_is_reported_not_recorded_as_told(self):
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        p = fx.ok("assemble", "b1", gh_fail="pr comment")
        st = fx.state("b1")
        held = st["assembly"]["held"][0]
        self.assertEqual(held["n"], 108)
        self.assertIs(held["told"], False)
        self.assertIn("comment failed: fake gh: HTTP 502", held["told_why"])
        self.assertNotIn("108", st.get("held_notified", {}), "not recorded as told, so the rebuild retries")
        self.assertIn("gh pr comment failed", p.stdout)
        self.assertIn("postal (kind: coordinate) to the owner of #108", p.stdout)
        self.assertEqual(fx.gh()["prs"]["108"]["comments"], [])
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108: conflicts with #101 in notes.txt; owner NOT told (comment failed: fake gh: HTTP 502", body)
        fx.ok("assemble", "b1")
        self.assertEqual(len(fx.gh()["prs"]["108"]["comments"]), 1, "the rebuild posts the comment")
        self.assertIs(fx.state("b1")["assembly"]["held"][0]["told"], True)

    def test_a_member_conflicting_with_main_is_told_so_not_blamed_on_a_member(self):
        fx = self.fx
        old_main = fx.bare_rev("main")
        fx.branch("s", {"notes.txt": "one\ntwo-s\nthree\n"}, base=old_main)
        fx.commit_main({"notes.txt": "one\ntwo-m\nthree\n"}, "main moved on")
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", labels=["fix"], body=TRAILER)
        fx.pr(110, "s", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        st = fx.state("b1")
        held = st["assembly"]["held"]
        self.assertEqual([h["n"] for h in held], [110])
        self.assertEqual(held[0]["reason"], "conflicts with origin/main in notes.txt")
        self.assertEqual(held[0]["with"], [])
        comment = fx.gh()["prs"]["110"]["comments"][0]
        self.assertIn("This PR conflicts with origin/main in notes.txt", comment)
        self.assertNotIn("earlier member", comment)
        self.assertNotIn("that PR's branch", comment)
        self.assertIn("Merge origin/main into yours", comment)

    def test_a_rerere_replay_after_pull_keeps_the_recorded_review(self):
        fx = self.fx
        self.conflict_pair()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        fx.ok("pull", "b1", "111")
        st = fx.state("b1")
        rec = [e for e in st["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertTrue(rec["replayed"])
        self.assertEqual(rec["review"], "subagent: fine", "the review carries over with the identical resolution")
        self.assertEqual(rec["hunks"], 1)
        self.assertIn("earlier assembly", rec["how"])
        body = fx.gh()["prs"]["900"]["body"]
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); one review round in the earlier assembly, replayed by rerere: subagent: fine. [diff from the clean merge below].", body)
        self.assertNotIn("NOT recorded", body)
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree")

    def test_a_partial_rerere_replay_lists_both_files_and_continue_keeps_the_replayed_content(self):
        """rerere replays one file's resolution from the earlier assembly while a second file conflicts
        anew (main moved under the member). The stop must list BOTH files: with only the new one
        recorded, --continue read the replayed file as a stray change and advised restoring it from
        the conflicted merge-tree, which wrote conflict markers that the next --continue committed."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n", "README.md": "# notes-api\n\ng's line\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round one")
        # main edits README.md where #108 does, so the rebuild conflicts there too; rerere replays notes.txt.
        fx.commit_main({"README.md": "# notes-api\n\nmain's line\n"}, "main moved on")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        cur = fx.state("b1")["assembly"]["cursor"]
        self.assertEqual(cur["files"], ["README.md", "notes.txt"], "the replayed file is part of the stop")
        self.assertEqual(cur["replayed"], ["notes.txt"])
        self.assertEqual(fx._git("show", ":notes.txt", cwd=wt), "one\ntwo-a-g\nthree", "rerere staged the earlier resolution")
        self.assertIn("rerere replayed notes.txt", p.stdout)
        with open(os.path.join(wt, "README.md"), "w") as f:
            f.write("# notes-api\n\nmain's line\ng's line\n")
        fx._git("add", "README.md", cwd=wt)
        p = fx.ok("assemble", "b1", "--continue", "--reviewed", "round two")
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree", "the replayed content, no markers")
        self.assertEqual(fx.dev_git("show", "batch/b1:README.md"), "# notes-api\n\nmain's line\ng's line")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["files"], ["README.md", "notes.txt"])
        self.assertEqual(rec["replayed_files"], ["notes.txt"])
        self.assertEqual(rec["review"], "round two")
        self.assertIn("rerere replayed", rec["how"])
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("#108 merge carries a recorded resolution", p.stdout)
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("conflict resolved in README.md, notes.txt", body)
        self.assertIn("two-a-g", body)
        self.assertIn("main's line", body)

    def test_a_conflicted_path_with_glob_characters_is_matched_literally(self):
        """`git ls-files -- <path>` reads the path as a pathspec, so `a[1].txt` also matched `a1.txt`,
        and the stop, cursor, record and digest said rerere had replayed a file it never touched."""
        fx = self.fx
        fx.branch("a", {"a[1].txt": "two-a\n", "a1.txt": "plain\n"})
        fx.branch("g", {"a[1].txt": "two-g\n", "README.md": "# notes-api\n\ng's line\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(fx.state("b1")["assembly"]["cursor"], {"n": 108, "files": ["a[1].txt"], "replayed": []})
        wt = fx.wt("b1")
        with open(os.path.join(wt, "a[1].txt"), "w") as f:
            f.write("two-a-g\n")
        fx._git("add", "--", "a[1].txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round one")
        fx.commit_main({"README.md": "# notes-api\n\nmain's line\n"}, "main moved on")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        # The index now holds a1.txt and the replayed a[1].txt at stage 0 and README.md unmerged.
        self.assertEqual(batch.staged_paths(wt, ["a[1].txt"]), ["a[1].txt"])
        self.assertEqual(batch.staged_paths(wt, ["README.md", "a[1].txt"]), ["a[1].txt"])
        self.assertEqual(batch.staged_paths(wt, ["a1.txt", "a[1].txt"]), ["a1.txt", "a[1].txt"])
        cur = fx.state("b1")["assembly"]["cursor"]
        self.assertEqual(cur["files"], ["README.md", "a[1].txt"])
        self.assertEqual(cur["replayed"], ["a[1].txt"], "a1.txt did not conflict")
        self.assertIn("rerere replayed a[1].txt from the earlier assembly", p.stdout)
        self.assertNotIn("a1.txt", p.stdout)
        with open(os.path.join(wt, "README.md"), "w") as f:
            f.write("# notes-api\n\nmain's line\ng's line\n")
        fx._git("add", "--", "README.md", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round two")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["replayed_files"], ["a[1].txt"])
        self.assertNotIn("a1.txt", rec["how"])
        self.assertEqual(rec["review"], "round two")
        self.assertEqual(fx.dev_git("show", "batch/b1:a[1].txt"), "two-a-g")
        self.assertEqual(fx.dev_git("show", "batch/b1:a1.txt"), "plain")

    def test_a_rerere_replay_of_part_of_an_earlier_resolution_keeps_its_review(self):
        """After a two-file resolution was reviewed, main takes one of the files as resolved, so the
        next assembly conflicts in the other file alone and rerere replays it with the bytes that
        were reviewed. The earlier record was matched only on an equal file list, so this read
        'rerere replayed a recorded resolution' with no review and the digest said NOT recorded. A
        replay of a subset of a recorded resolution, blob for blob, carries that review."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n", "README.md": "# notes-api\n\ng's line\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round one")
        fx.commit_main({"README.md": "# notes-api\n\nmain's line\n"}, "main moved on")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        with open(os.path.join(wt, "README.md"), "w") as f:
            f.write("# notes-api\n\nmain's line\ng's line\n")
        fx._git("add", "README.md", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round two")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["files"], ["README.md", "notes.txt"])
        self.assertEqual(rec["blobs"], {"README.md": fx.dev_git("rev-parse", "batch/b1:README.md"),
                                        "notes.txt": fx.dev_git("rev-parse", "batch/b1:notes.txt")},
                         "the record names the bytes it covers")
        # main takes #108's README as is: the third assembly conflicts in notes.txt alone.
        fx.commit_main({"README.md": "# notes-api\n\ng's line\n"}, "main takes g's README")
        p = fx.ok("assemble", "b1", "--resolve", "108")
        self.assertIn("rerere replayed the resolution recorded in the earlier assembly", p.stdout)
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["files"], ["notes.txt"])
        self.assertTrue(rec["replayed"])
        self.assertEqual(rec["review"], "round two", "the same bytes were reviewed in round two")
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); one review round in the earlier assembly, replayed by rerere: round two.", body)
        self.assertNotIn("NOT recorded", body)

    def test_a_rerere_replay_into_a_file_main_changed_elsewhere_keeps_its_review(self):
        """Between assemblies main appends lines to notes.txt after the conflict. The second assembly's
        merge of #108 conflicts on the same hunk, rerere replays the reviewed resolution, and the
        staged file's blob differs from the record's. The record was matched blob for blob, so this
        read 'rerere replayed a recorded resolution' with no review and the digest said NOT recorded
        for reviewed bytes. The carry is keyed on the resolution of the hunks, which is the same."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round one")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(list(rec["hunk_hashes"]), ["notes.txt"], "the record names the resolution of each file's hunks")
        self.assertRegex(rec["hunk_hashes"]["notes.txt"], r"^[0-9a-f]{64}$")
        blob1, hash1 = rec["blobs"]["notes.txt"], rec["hunk_hashes"]["notes.txt"]
        fx.commit_main({"notes.txt": "one\ntwo\nthree\nfour\nfive\nsix\nseven\n"}, "main appends after the conflict")
        p = fx.ok("assemble", "b1", "--resolve", "108")
        self.assertIn("rerere replayed the resolution recorded in the earlier assembly", p.stdout)
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertTrue(rec["replayed"])
        self.assertEqual(rec["review"], "round one", "the same hunk resolution was reviewed")
        self.assertNotEqual(rec["blobs"]["notes.txt"], blob1, "the file differs outside the hunk")
        self.assertEqual(rec["hunk_hashes"]["notes.txt"], hash1)
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree\nfour\nfive\nsix\nseven")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); one review round in the earlier assembly, replayed by rerere: round one.", body)
        self.assertNotIn("NOT recorded", body)

    def test_a_rerere_replay_of_other_bytes_in_the_hunk_carries_no_review(self):
        """rerere keeps the resolution it recorded first. A replayed file the batcher edits before
        --continue is committed and reviewed with the new bytes, but the next assembly's replay
        produces the old ones: the record names the reviewed bytes, so that replay carries no review
        and the digest says so."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n", "README.md": "# notes-api\n\ng's line\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round one")
        fx.commit_main({"README.md": "# notes-api\n\nmain's line\n"}, "main moved on")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        self.assertEqual(fx.state("b1")["assembly"]["cursor"]["replayed"], ["notes.txt"])
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g-x\nthree\n")   # the batcher changes the replayed resolution
        with open(os.path.join(wt, "README.md"), "w") as f:
            f.write("# notes-api\n\nmain's line\ng's line\n")
        fx._git("add", "notes.txt", "README.md", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "round two")
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g-x\nthree")
        fx.commit_main({"README.md": "# notes-api\n\ng's line\n"}, "main takes g's README")
        fx.ok("assemble", "b1", "--resolve", "108")
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a-g\nthree", "rerere replayed its first resolution")
        st = fx.state("b1")
        rec = [e for e in st["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        reviewed = st["assembly"]["previous_resolutions"]["108"]["hunk_hashes"]["notes.txt"]
        self.assertIsNotNone(reviewed)
        self.assertNotEqual(rec["hunk_hashes"]["notes.txt"], reviewed, "the replayed hunk is not the reviewed one")
        self.assertTrue(rec["replayed"])
        self.assertIsNone(rec["review"], "round two reviewed other bytes")
        self.assertEqual(rec["how"], "rerere replayed a recorded resolution")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); review round NOT recorded.", body)

    def test_hunk_lines_identify_a_resolution_without_line_numbers_context_or_marker_labels(self):
        """The identity prior_resolution compares when the blobs differ: the same hunk resolution in a
        file with other lines around it, under markers labeled with other parents, reads the same;
        other bytes in the hunk, or a dropped final newline, do not; a binary file has no identity."""
        fx = self.fx

        def tree(content):
            blob = fx._git("hash-object", "-w", "--stdin", cwd=fx.dev, input=content)
            return fx._git("mktree", cwd=fx.dev, input="100644 blob %s\tnotes.txt\n" % blob)

        m1 = tree("one\n<<<<<<< %s\ntwo-a\n=======\ntwo-g\n>>>>>>> %s\nthree\n" % ("1" * 40, "2" * 40))
        r1 = tree("one\ntwo-a-g\nthree\n")
        m2 = tree("zero\none\n<<<<<<< %s\ntwo-a\n=======\ntwo-g\n>>>>>>> %s\nthree\nfour\nfive\nsix\n" % ("3" * 40, "4" * 40))
        r2 = tree("zero\none\ntwo-a-g\nthree\nfour\nfive\nsix\n")
        lines = batch.hunk_lines(fx.dev, m1, r1, "notes.txt")
        self.assertEqual(lines, [b"-<<<<<<<", b"-two-a", b"-=======", b"-two-g", b"->>>>>>>", b"+two-a-g"])
        self.assertEqual(batch.hunk_lines(fx.dev, m2, r2, "notes.txt"), lines, "other surroundings and labels: the same resolution")
        self.assertEqual(batch.hunk_hash(fx.dev, m2, r2, "notes.txt"), batch.hunk_hash(fx.dev, m1, r1, "notes.txt"))
        self.assertNotEqual(batch.hunk_lines(fx.dev, m2, tree("zero\none\ntwo-a-x\nthree\nfour\nfive\nsix\n"), "notes.txt"), lines,
                            "other bytes in the hunk")
        self.assertNotEqual(batch.hunk_lines(fx.dev, m1, tree("one\ntwo-a-g\nthree"), "notes.txt"), lines,
                            "a missing final newline is a byte difference")
        self.assertIsNone(batch.hunk_lines(fx.dev, m1, m1, "notes.txt"), "no change")
        self.assertIsNone(batch.hunk_lines(fx.dev, tree("a\0b\n"), tree("a\0c\n"), "notes.txt"), "binary: no text hunk")

    def test_prior_resolution_matches_a_subset_blob_for_blob_and_a_legacy_record_on_its_file_list(self):
        """The rule behind the replays above, on a bare index: a record covers a replay when every
        replayed path is among its files AND the blob staged for it equals the record's, or the
        hunks resolve as recorded (a merge in progress is needed to compare them; the replay tests
        cover that). Different bytes under the same name (rerere's cache is shared across batches)
        carry no review. A record written before blobs were recorded matches on an equal file list
        only, as it did."""
        fx = self.fx
        wt = fx.dev
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx.dev_git("add", "notes.txt")
        staged = fx.dev_git("rev-parse", ":notes.txt")
        readme = fx.dev_git("rev-parse", ":README.md")
        rec = {"files": ["README.md", "notes.txt"], "review": "r", "blobs": {"README.md": readme, "notes.txt": staged}}
        state = {"assembly": {"previous_resolutions": {"108": rec}}}
        self.assertIs(batch.prior_resolution(state, "108", ["notes.txt"], wt), rec, "a subset, same bytes")
        self.assertIs(batch.prior_resolution(state, "108", ["README.md", "notes.txt"], wt), rec)
        self.assertIsNone(batch.prior_resolution(state, "108", ["notes.txt", "other.txt"], wt), "not a subset")
        self.assertIsNone(batch.prior_resolution(state, "101", ["notes.txt"], wt), "another member's record")
        self.assertIsNone(batch.prior_resolution(state, "108", [], wt))
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-other\nthree\n")
        fx.dev_git("add", "notes.txt")
        self.assertIsNone(batch.prior_resolution(state, "108", ["notes.txt"], wt), "same name, different bytes")
        hashed = dict(rec, hunk_hashes={"README.md": "0" * 64, "notes.txt": "0" * 64})
        state = {"assembly": {"previous_resolutions": {"108": hashed}}}
        self.assertIsNone(batch.prior_resolution(state, "108", ["notes.txt"], wt), "different bytes and no merge to compare hunks in")
        legacy = {"files": ["README.md", "notes.txt"], "review": "r"}
        state = {"assembly": {"previous_resolutions": {"108": legacy}}}
        self.assertIs(batch.prior_resolution(state, "108", ["notes.txt", "README.md"], wt), legacy)
        self.assertIsNone(batch.prior_resolution(state, "108", ["notes.txt"], wt), "no blobs to compare a subset by")

    def test_continue_never_commits_a_conflict_marker_even_when_the_file_equals_the_conflicted_merge_tree(self):
        """The marker scan must read the files themselves: a file byte-identical to what merge-tree
        left for it (markers included) does not differ from that tree, so a scan of the differing
        paths alone would miss it; and the file as git left it in the worktree, just `git add`ed."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        head, other = fx._git("rev-parse", "HEAD", cwd=wt), fx._git("rev-parse", "MERGE_HEAD", cwd=wt)
        mt = fx._git("merge-tree", "--write-tree", "--no-messages", head, other, cwd=wt, check=False).splitlines()[0]
        marked = fx._git("show", mt + ":notes.txt", cwd=wt) + "\n"
        self.assertIn("<<<<<<< ", marked)
        for content in (marked, None):
            if content is None:
                fx._git("checkout", "--merge", "--", "notes.txt", cwd=wt)   # the conflict as git wrote it
            else:
                with open(os.path.join(wt, "notes.txt"), "w") as f:
                    f.write(content)
            fx._git("add", "notes.txt", cwd=wt)
            p = fx.run("assemble", "b1", "--continue", "--reviewed", "x")
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
            self.assertIn("conflict marker", p.stderr)
            self.assertIn("notes.txt", p.stderr)
            self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a"], "nothing was committed")
            self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "MERGE_HEAD")))

    def test_a_take_theirs_resolution_says_which_side_won_and_shows_the_diff_from_the_clean_merge(self):
        """`git show --cc` omits hunks equal to one parent, so a resolution that took one side wholesale
        rendered as '0 hunks' over an empty diff block. The diff is from the merge-tree of the parents
        to the merge (the conflict text turning into the chosen text), and the line says whose version
        was taken."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        fx._git("checkout", "--theirs", "--", "notes.txt", cwd=wt)
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "took g's side")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["hunks"], 1)
        self.assertEqual(rec["choices"], {"notes.txt": "took #108's version"})
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (took #108's version; 1 hunk); one review round: took g's side. [diff from the clean merge below].", body)
        self.assertIn("### #108", body)
        self.assertIn("- notes.txt: took #108's version", body)
        self.assertIn("-two-a", body, "the diff shows #101's line going out of the conflict block")
        self.assertIn(" two-g", body)
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("#108 merge carries a recorded resolution (resolved by the batcher, per hunk) in notes.txt", p.stdout)

    def test_a_modify_delete_resolution_that_keeps_the_file_says_so_and_verify_checks_the_conflicted_path(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": None})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", title="notes: drop the file", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        wt = fx.wt("b1")
        self.assertEqual(fx.state("b1")["assembly"]["cursor"]["files"], ["notes.txt"])
        fx._git("add", "notes.txt", cwd=wt)    # keep #108's file
        fx.ok("assemble", "b1", "--continue", "--reviewed", "keep g's file")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertEqual(rec["choices"], {"notes.txt": "took #108's version, which the batch deleted"})
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-g\nthree")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- #108 g: conflict resolved in notes.txt (took #108's version, which the batch deleted); one review round: keep g's file.", body)
        self.assertIn("- notes.txt: took #108's version, which the batch deleted", body)
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   provenance: #108 merge carries a recorded resolution (resolved by the batcher, per hunk) in notes.txt", p.stdout)
        self.assertFalse([l for l in p.stdout.splitlines() if "#108" in l and "equals the clean merge" in l],
                         "a resolved merge is not reported as the clean merge")
        # The kept file equals what merge-tree left for it, so it does not differ from that tree; verify
        # must still see that merge-tree calls it conflicted and demand the recorded resolution cover it.
        path = os.path.join(fx.dev, ".git", "batch", "b1.json")
        with open(path) as f:
            st = json.load(f)
        [e for e in st["assembly"]["merged"] if e["n"] == 108][0]["resolved"]["files"] = ["README.md"]
        with open(path, "w") as f:
            json.dump(st, f)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL provenance: #108 merge", p.stdout)
        self.assertIn("notes.txt", p.stdout)
        self.assertIn("not cover", p.stdout)

    def test_a_file_vs_symlink_conflict_claims_no_rerere_replay(self):
        """A distinct-types conflict: merge-tree names the aside copy `notes.txt~<HEAD sha>` (its parents
        are given by SHA) while `git merge` names it `notes.txt~HEAD`, so the merge-tree path is neither
        unmerged nor in the index. Every conflicted path that was not unmerged used to count as a
        rerere replay, so a FIRST assembly said rerere had replayed that phantom path, and the record
        and the digest repeated it. A replayed path is one the index holds at stage 0."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx._git("fetch", "-q", "origin", cwd=fx.author)
        fx._git("checkout", "-q", "-B", "g", "origin/main", cwd=fx.author)
        os.remove(os.path.join(fx.author, "notes.txt"))
        os.symlink("README.md", os.path.join(fx.author, "notes.txt"))
        fx._git("add", "-A", cwd=fx.author)
        fx._git("commit", "-q", "-m", "notes.txt becomes a link", cwd=fx.author)
        fx._git("push", "-q", "-f", "origin", "g", cwd=fx.author)
        fx.swept("g")
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: a link", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertNotIn("rerere replayed", p.stdout, "nothing was replayed on a first assembly")
        cur = fx.state("b1")["assembly"]["cursor"]
        self.assertEqual(cur["replayed"], [])
        self.assertIn("notes.txt", cur["files"])
        wt = fx.wt("b1")
        self.assertEqual(fx._git("diff", "--name-only", "--diff-filter=U", cwd=wt).split(), ["notes.txt", "notes.txt~HEAD"],
                         "git's own names for the conflict")
        # Keep #101's file: drop the aside copy git wrote, put the file back under its name.
        fx._git("rm", "-q", "--", "notes.txt~HEAD", cwd=wt)
        os.remove(os.path.join(wt, "notes.txt"))
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a\nthree\n")
        fx._git("add", "--", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "kept the file")
        rec = [e for e in fx.state("b1")["assembly"]["merged"] if e["n"] == 108][0]["resolved"]
        self.assertNotIn("rerere", rec["how"])
        self.assertNotIn("replayed_files", rec)
        self.assertEqual(fx.dev_git("show", "batch/b1:notes.txt"), "one\ntwo-a\nthree")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("#108 merge carries a recorded resolution (resolved by the batcher, per hunk)", p.stdout)
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertNotIn("rerere", body)
        self.assertIn("one review round: kept the file", body)

    def test_a_member_already_contained_by_an_earlier_member_is_recorded_as_contained(self):
        """Ordering missed a dependency: #101's branch was built on #102's. `git merge` says
        'Already up to date' and makes no commit, which must not be recorded as a merge."""
        fx = self.fx
        fx.branch("a", {"kernel/kernel.py": "VERSION = 2\n"})
        fx.branch("b", {"postal/postal_service.py": "def send():\n    return 2\n"}, base="a")
        fx.pr(101, "b", title="postal: send two", labels=["fix"], body=TRAILER)
        fx.pr(102, "a", title="kernel: bump the version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.state("b1")["order"], [101, 102])
        p = fx.ok("assemble", "b1")
        self.assertIn("#102 is already contained by #101", p.stdout)
        st = fx.state("b1")
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101])
        self.assertEqual(st["assembly"]["contained"], [{"n": 102, "contained_by": "#101"}])
        self.assertEqual(fx.chain("b1"), ["Merge #101: postal: send two"])
        fx.push_batch("b1")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   head: #102 at %s (already contained by #101, no merge of its own)" % st["members"]["102"]["head"][:10], p.stdout)
        self.assertIn("ok   provenance: 1 member merge(s), 0 declared batch: commit(s), nothing else", p.stdout)
        fx.ok("summarize", "b1")
        gh = fx.gh()
        body = gh["prs"]["900"]["body"]
        self.assertTrue(body.startswith("# Batch b1: 2 PRs\n"), body.splitlines()[0])
        self.assertIn("- #102 a: already contained by #101: no merge commit of its own (add `Depends-on` or reorder next time); touches kernel/.", body)
        self.assertIn("| #102 | kernel: bump the version | fix | 3 |", body)
        self.assertIn("contained by #101", body)
        self.assertEqual(gh["prs"]["102"]["comments"], ["in batch b1 at %s" % st["assembly"]["head"]], "a contained member hears the cut too")
        # Contained by main (it merged alone): recorded as such; verify then says pull it.
        fx.fake_gh("pr", "merge", "101", "--merge")
        fx.ok("assemble", "b1")
        st = fx.state("b1")
        self.assertEqual([c["n"] for c in st["assembly"]["contained"]], [101, 102])
        self.assertEqual(st["assembly"]["contained"][0]["contained_by"], "origin/main")
        self.assertEqual(st["assembly"]["merged"], [])
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL state: #101 is MERGED (pull it", p.stdout)

    def test_merge_main_records_a_clean_merge_and_a_resolved_one(self):
        """When main moves under an open batch, `assemble --merge-main` merges origin/main into the
        batch and records it; a conflict stops for a hand resolution the way --resolve does, and the
        resolution is recorded, shown in the body and checked by provenance."""
        fx = self.fx
        self.conflict_pair()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        head0 = fx.state("b1")["assembly"]["head"]
        fx.commit_main({"README.md": "# notes-api\n\nmain moved\n"}, "main moved")
        p = fx.ok("assemble", "b1", "--merge-main")
        st = fx.state("b1")
        self.assertEqual(len(st["assembly"]["main_merges"]), 1)
        self.assertIsNone(st["assembly"]["main_merges"][0]["resolved"])
        self.assertNotEqual(st["assembly"]["head"], head0)
        self.assertEqual(st["assembly"]["head"], fx.dev_git("rev-parse", "batch/b1"))
        self.assertIsNone(st["verified"])
        self.assertEqual(fx.chain("b1"), ["Merge #101: PR 101 on a", "Merge origin/main into batch/b1"])
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   provenance: the origin/main merge %s equals the clean merge of its parents" % st["assembly"]["head"][:10], p.stdout)
        self.assertEqual(fx.ok("assemble", "b1", "--merge-main").stdout.strip(), "origin/main (%s) is already in batch/b1" % fx.bare_rev("main")[:10])
        # main now conflicts with #101 in notes.txt: stop, resolve, continue.
        fx.commit_main({"notes.txt": "one\ntwo-m\nthree\n"}, "main edits notes")
        p = fx.run("assemble", "b1", "--merge-main")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("stopped for resolution in notes.txt", p.stdout)
        st = fx.state("b1")
        self.assertEqual(st["assembly"]["cursor"], {"n": None, "main": fx.bare_rev("main"), "files": ["notes.txt"], "replayed": []})
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("the merge of origin/main is still stopped", p.stderr)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-m\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: ok")
        st = fx.state("b1")
        self.assertIsNone(st["assembly"]["cursor"])
        self.assertEqual(len(st["assembly"]["main_merges"]), 2)
        self.assertEqual(st["assembly"]["main_merges"][1]["resolved"]["review"], "subagent: ok")
        self.assertEqual(st["assembly"]["head"], fx.dev_git("rev-parse", "batch/b1"))
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101], "no member was merged twice")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   provenance: the origin/main merge carries a recorded resolution (resolved by the batcher, per hunk) in notes.txt", p.stdout)
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- merge of origin/main (%s): conflict resolved in notes.txt (1 hunk); one review round: subagent: ok. [diff from the clean merge below]." % st["assembly"]["head"][:10], body)
        self.assertIn("### merge of origin/main (%s)" % st["assembly"]["head"][:10], body)
        self.assertIn("two-a-m", body)

    def test_pull_of_a_member_that_merged_alone_keeps_its_dependents_and_repin_refreshes_the_base(self):
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.fake_gh("pr", "merge", "101", "--merge")     # merged alone; GitHub deletes `a` and retargets #102 to main
        self.assertEqual(fx.gh()["prs"]["102"]["baseRefName"], "main")
        p = fx.ok("assemble", "b1", "--repin", "102", "--without", "101")
        st = fx.state("b1")
        self.assertEqual(st["pulled"], [101], "#102 is not dropped: its dependency is in main")
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [102])
        self.assertEqual(st["members"]["102"]["base_ref"], "main", "--repin refreshes the base")
        self.assertTrue(any("#101 is pulled but already in origin/main; its dependents stay" in l for l in st["assembly"]["log"]))
        self.assertTrue(any("re-pinned #102: base a -> main" in l for l in st["assembly"]["log"]))
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")


    def test_a_merge_the_pre_merge_commit_hook_refuses_fails_the_command_and_is_not_committed(self):
        """When the clone's pre-merge-commit hook refuses a merge, git leaves MERGE_HEAD with nothing unmerged, as a merge
        that rerere resolved whole leaves it, and assemble read it as one: it committed the merge with git commit, which
        runs pre-commit, not pre-merge-commit, so the hook's refusal was passed over, and the batch log said rerere had
        replayed a recorded resolution. A merge that stops with nothing unmerged and nothing rerere replayed is now
        aborted, and the command fails quoting what git printed, where the hook's text is; no call passes --no-verify.
        Here, each case in a fixture of its own, a pre-merge-commit hook prints a refusal and exits 1: assemble
        --no-fetch of a member that merges cleanly, and assemble --merge-main after origin's main moved, each exit 1
        with the hook's line in what they print, no merge made (the chain empty; no merge of main recorded and the head
        unchanged) and no merge left in progress. Red before (at the head of round 2 and at its build head): each
        exited 0, the merge committed "with rerere replayed a recorded resolution"."""
        refusal = "pre-merge-commit: this merge is refused by the clone's own check"
        for n, case in enumerate(("a member's merge", "the merge of origin's main")):
            with self.subTest(case=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
                fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
                fx.ok("plan", "--name", "b1")
                if case == "a member's merge":
                    args = ("assemble", "b1", "--no-fetch")
                else:
                    fx.ok("assemble", "b1")
                    fx.commit_main({"README.md": "# notes-api\n\nmain moved\n"}, "main moved")
                    head = fx.state("b1")["assembly"]["head"]
                    args = ("assemble", "b1", "--merge-main")
                hook = os.path.join(fx.dev, ".git", "hooks", "pre-merge-commit")
                os.makedirs(os.path.dirname(hook), exist_ok=True)
                with open(hook, "w") as f:
                    f.write("#!/bin/sh\necho \"%s\" >&2\nexit 1\n" % refusal)
                os.chmod(hook, 0o755)
                p = fx.run(*args)
                self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
                self.assertIn(refusal, p.stdout + p.stderr)
                self.assertIn("stopped with nothing in conflict (a hook refused it?)", p.stderr)
                wt = fx.wt("b1")
                self.assertEqual(fx._git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt, check=False), "",
                                 "no merge left in progress")
                st = fx.state("b1")
                if case == "a member's merge":
                    self.assertEqual(fx.chain("b1"), [])
                    self.assertFalse((st.get("assembly") or {}).get("merged"), st.get("assembly"))
                else:
                    self.assertFalse(st["assembly"].get("main_merges"), st["assembly"].get("main_merges"))
                    self.assertEqual(st["assembly"]["head"], head)
                    self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), head)

    # A three-way merge of one file that merge-tree's ort, whose content merges use the histogram diff, conflicts on, and
    # that a myers diff merges cleanly (found by search with git merge-file --diff-algorithm, git 2.55.0, 2026-10-04): the
    # merge base's text, the batch side's (#101's) and the other side's (#102's, or main's). git 2.43.0's merge-recursive,
    # which pull.twohead=recursive makes git merge run, merges with myers, and git 2.55.0's merge reads diff.algorithm.
    MYERS_CLEAN = "notes/format.c"
    MYERS_BASE = ("return x;\nif (a)\nx++;\n}\nfoo();\nif (a)\nfoo();\n{\n{\n}\nfoo();\n}\n}\n\n\nif (a)\nreturn x;\n"
                  "foo();\nreturn x;\nbar();\n")
    MYERS_OURS = ("return x;\nif (a)\nx++;\n}\nfoo();\nif (a)\nfoo();\n{\n{\nif (a)\nif (a)\n{\n{\n}\nfoo();\n}\n}\n"
                  "\n\nif (a)\nreturn x;\nfoo();\nreturn x;\nbar();\n")
    MYERS_THEIRS = ("return x;\nif (a)\nx++;\n}\nfoo();\nif (a)\nx++;\n{\nbar();\n\nfoo();\n{\n{\n}\nfoo();\n}\n}\n\n"
                    "if (a)\nreturn x;\nfoo();\nreturn x;\nbar();\n")

    def refusing_hook(self, fx, refused, refusal):
        """A pre-merge-commit hook in `fx`'s clone that appends GIT_REFLOG_ACTION to a log, and, for a merge whose
        GIT_REFLOG_ACTION holds `refused`, writes the index's resolve-undo record as git merge left it to a file, prints
        `refusal` and exits 1: (the log's path, the record's path)."""
        log, record = os.path.join(fx.tmp, "hook.log"), os.path.join(fx.tmp, "hook-record.txt")
        hook = os.path.join(fx.dev, ".git", "hooks", "pre-merge-commit")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, "w") as f:
            f.write('#!/bin/sh\necho "$GIT_REFLOG_ACTION" >> "%s"\ncase "$GIT_REFLOG_ACTION" in *%s*)\n'
                    '  git ls-files --resolve-undo > "%s"; echo "%s" >&2; exit 1;;\nesac\nexit 0\n'
                    % (log, refused, record, refusal))
        os.chmod(hook, 0o755)
        return log, record

    def test_merges_read_the_options_merge_tree_reads_and_a_refused_merge_is_not_read_as_a_replay(self):
        """Round 3 of PR 959, correctness-1 and tests-1. batch.py's two merges, a member's and the merge of origin's
        main, read the merge options merge-tree reads (MERGE_STRATEGY's comment): the batch branch's mergeOptions
        emptied, -s ort, diff.algorithm=histogram. So an option the user set that git merge reads and merge-tree does
        not resolves no conflict merge-tree reports: the conflict is a real one, the member is held back and the merge of
        main stops for a hand resolution, and the clone's pre-merge-commit hook, which refuses that merge, never runs
        (its log never names it). Four options, each in both shapes, a fixture each: -Xours in
        branch.batch/b1.mergeOptions and '-s recursive -Xours' there, #101 and #102 (or main) changing line two of
        notes.txt; pull.twohead=recursive and diff.algorithm=myers, #101 and #102 (or main) changing MYERS_CLEAN, which
        merge-tree conflicts on (asserted) and a myers diff merges cleanly. The member shape (assemble --no-fetch) exits
        0 with #102 held back on that file and the chain #101's merge alone; the merge of main (assemble --merge-main,
        after #101 is assembled) exits 3, stopped for resolution in the file with nothing replayed, the merge in
        progress and the head where it was. Red at the head before this change: -Xours exited 1 in both shapes, the
        hook's refusal, under git 2.43.0 and 2.55.0; '-s recursive -Xours' under git 2.43.0 exited 0 with the refused
        merge committed "with rerere replayed a recorded resolution" (merge-recursive wrote a resolve-undo entry for the
        file), and under 2.55.0, where recursive is ort, exited 1; pull.twohead=recursive under git 2.43.0 exited 0, the
        refused merge committed as a replay, the same way (under 2.55.0 it was already the real conflict); and
        diff.algorithm=myers under git 2.55.0 exited 1, git merge having merged the file cleanly (git 2.43.0's merge reads
        no diff.algorithm, so it was already the real conflict).
        Then the premise the resolve-undo check rests on (undone_paths), with a stale record present before the refused
        merge (tests-1): git commit keeps the record, so after #102's hand resolution is committed it still lists
        notes.txt, and git merge clears it as it starts. A git first on PATH (ROAD_GIT) stands in for a road by which
        git merge resolves a conflict merge-tree reports with no rerere, which the options were the known roads to and
        which none is known to be now: it adds -Xours to the one merge it names. In the member shape #101, #102 and #103
        change line two of notes.txt, #102 stops (--resolve 102) and is resolved by hand, the record lists notes.txt
        (asserted after git add), and assemble --continue commits it and merges #103, which the road resolves and the
        hook refuses; in the shape of the merge of main, --continue ends the assembly, the record lists notes.txt
        (asserted), main changes the line, and the road resolves the merge of main, which the hook refuses. Each exits 1
        with the hook's line and "stopped with nothing in conflict (a hook refused it?)", nothing of the refused merge
        recorded or on the branch, no merge left in progress, and the record the hook read empty: git merge cleared it.
        Red under a mutant that keeps the record across git merge (batch.py lists it before each of its two merges and
        undone_paths adds those paths back): exit 0, the refused merge committed "with rerere replayed a recorded
        resolution"."""
        refusal = "pre-merge-commit: this merge is refused by the clone's own check"
        options = (("-Xours", ("branch.batch/b1.mergeOptions", "-Xours"), "notes.txt"),
                   ("-s recursive -Xours", ("branch.batch/b1.mergeOptions", "-s recursive -Xours"), "notes.txt"),
                   ("pull.twohead=recursive", ("pull.twohead", "recursive"), self.MYERS_CLEAN),
                   ("diff.algorithm=myers", ("diff.algorithm", "myers"), self.MYERS_CLEAN))
        first = True
        for label, (key, value), path in options:
            for shape in ("a member's merge", "the merge of origin's main"):
                with self.subTest(option=label, shape=shape):
                    if not first:
                        self.fx = Fixture()
                        self.addCleanup(self.fx.close)
                    first = False
                    fx = self.fx
                    if path == "notes.txt":
                        base, ours, theirs = None, "one\ntwo-a\nthree\n", "one\ntwo-b\nthree\n"
                    else:
                        base, ours, theirs = self.MYERS_BASE, self.MYERS_OURS, self.MYERS_THEIRS
                        fx.commit_main({path: base}, "main adds the file the merges disagree on")
                    fx.branch("a", {path: ours})
                    fx.pr(101, "a", title="notes: the a version", labels=["fix"], body=TRAILER)
                    if shape == "a member's merge":
                        fx.branch("b", {path: theirs})
                        fx.pr(102, "b", title="notes: the b version", labels=["fix"], body=TRAILER)
                        fx.ok("plan", "--name", "b1")
                        refused = fx.dev_git("rev-parse", "origin/b")
                        sides = (fx.dev_git("rev-parse", "origin/a"), refused)
                        args = ("assemble", "b1", "--no-fetch")
                    else:
                        fx.ok("plan", "--name", "b1")
                        fx.ok("assemble", "b1")
                        refused = fx.commit_main({path: theirs}, "main changes what #101 changed")
                        fx.dev_git("fetch", "-q", "origin")
                        head = fx.state("b1")["assembly"]["head"]
                        sides = (head, refused)
                        args = ("assemble", "b1", "--merge-main")
                    self.assertIn(path, fx.dev_git("merge-tree", "--write-tree", "--name-only", "--no-messages", *sides,
                                                   check=False).splitlines()[1:],
                                  "premise: merge-tree names the file conflicted")
                    fx.dev_git("config", key, value)
                    log, _record = self.refusing_hook(fx, refused, refusal)
                    p = fx.run(*args)
                    said = p.stdout + p.stderr
                    self.assertNotIn("rerere replayed", said)
                    self.assertNotIn("stopped with nothing in conflict", said)
                    self.assertNotIn(refusal, said)
                    with open(log) if os.path.exists(log) else open(os.devnull) as f:
                        self.assertNotIn(refused, f.read(), "the hook never ran for the merge it refuses")
                    st = fx.state("b1")
                    wt = fx.wt("b1")
                    if shape == "a member's merge":
                        self.assertEqual(p.returncode, 0, said)
                        self.assertEqual(fx.chain("b1"), ["Merge #101: notes: the a version"])
                        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101])
                        self.assertEqual([(h["n"], h.get("files")) for h in st["assembly"]["held"]], [(102, [path])])
                        self.assertEqual(fx._git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt, check=False), "",
                                         "no merge left in progress")
                    else:
                        self.assertEqual(p.returncode, 3, said)
                        self.assertIn("stopped for resolution in %s" % path, p.stdout)
                        self.assertEqual(st["assembly"]["cursor"], {"n": None, "main": refused, "files": [path],
                                                                    "replayed": []})
                        self.assertEqual(fx._git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt, check=False),
                                         refused, "the merge of main is stopped for resolution")
                        self.assertFalse(st["assembly"].get("main_merges"), st["assembly"].get("main_merges"))
                        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), head)
        for shape in ("a member's merge", "the merge of origin's main"):
            with self.subTest(case="a stale resolve-undo record before the refused merge", shape=shape):
                self.fx = Fixture()
                self.addCleanup(self.fx.close)
                fx = self.fx
                fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
                fx.pr(101, "a", title="notes: the a version", labels=["fix"], body=TRAILER)
                fx.branch("b", {"notes.txt": "one\ntwo-b\nthree\n"})
                fx.pr(102, "b", title="notes: the b version", labels=["fix"], body=TRAILER)
                if shape == "a member's merge":
                    fx.branch("c", {"notes.txt": "one\ntwo-c\nthree\n"})
                    fx.pr(103, "c", title="notes: the c version", labels=["fix"], body=TRAILER)
                fx.ok("plan", "--name", "b1")
                p = fx.run("assemble", "b1", "--resolve", "102")
                self.assertEqual(p.returncode, 3, "premise: #102 stops for a hand resolution\n%s%s" % (p.stdout, p.stderr))
                wt = fx.wt("b1")
                with open(os.path.join(wt, "notes.txt"), "w") as f:
                    f.write("one\ntwo-a-b\nthree\n")
                fx._git("add", "notes.txt", cwd=wt)
                stale = "premise: the resolve-undo record lists notes.txt before the refused merge"
                if shape == "a member's merge":
                    self.assertIn("\tnotes.txt", fx._git("ls-files", "--resolve-undo", cwd=wt), stale)
                    refused = fx.dev_git("rev-parse", "origin/c")
                    args = ("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
                else:
                    fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
                    self.assertIn("\tnotes.txt", fx._git("ls-files", "--resolve-undo", cwd=wt), stale)
                    refused = fx.commit_main({"notes.txt": "one\ntwo-m\nthree\n"}, "main changes line two")
                    args = ("assemble", "b1", "--merge-main")
                chain = ["Merge #101: notes: the a version", "Merge #102: notes: the b version"]
                _log, record = self.refusing_hook(fx, refused, refusal)
                road = os.path.join(fx.tmp, "road-bin")
                os.makedirs(road)
                with open(os.path.join(road, "git"), "w") as f:
                    f.write(ROAD_GIT)
                os.chmod(os.path.join(road, "git"), 0o755)
                env = dict(fx.env, PATH=road + os.pathsep + fx.env["PATH"], ROAD_ON=refused,
                           ROAD_REAL_GIT=shutil.which("git", path=fx.env["PATH"]))
                p = fx.run(*args, env=env)
                said = p.stdout + p.stderr
                self.assertEqual(p.returncode, 1, said)
                self.assertIn(refusal, said)
                self.assertIn("stopped with nothing in conflict (a hook refused it?)", p.stderr)
                self.assertNotIn("rerere replayed", said)
                with open(record) as f:
                    self.assertEqual(f.read(), "", "git merge cleared the stale record as it started")
                self.assertEqual(fx._git("rev-parse", "-q", "--verify", "MERGE_HEAD", cwd=wt, check=False), "",
                                 "no merge left in progress")
                self.assertEqual(fx.chain("b1"), chain)
                st = fx.state("b1")
                self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [101, 102])
                self.assertFalse(st["assembly"].get("main_merges"), st["assembly"].get("main_merges"))

class Verify(_Base):
    def assembled(self):
        self.two_members()
        self.fx.ok("plan", "--name", "b1")
        self.fx.ok("assemble", "b1")

    def test_provenance_fails_on_an_undeclared_commit_and_passes_on_a_batch_commit(self):
        fx = self.fx
        self.assembled()
        wt = fx.wt("b1")
        with open(os.path.join(wt, "tweak.txt"), "w") as f:
            f.write("t\n")
        fx._git("add", "tweak.txt", cwd=wt)
        fx._git("commit", "-q", "-m", "tweak", cwd=wt)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("undeclared commit", p.stdout)
        fx._git("commit", "-q", "--amend", "-m", "batch: tweak", cwd=wt)
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   provenance: 2 member merge(s), 1 declared batch: commit(s), nothing else", p.stdout)
        self.assertTrue(fx.state("b1")["verified"]["ok"])

    def test_fails_when_a_pinned_head_moved(self):
        fx = self.fx
        self.assembled()
        fx.commit("a", {"kernel/kernel.py": "VERSION = 3\n"})
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("head moved: #101", p.stdout)
        self.assertIn("--repin 101", p.stdout)
        self.assertFalse(fx.state("b1")["verified"]["ok"])

    def test_an_edit_hidden_in_a_merge_commit_is_caught(self):
        fx = self.fx
        self.assembled()
        wt = fx.wt("b1")
        with open(os.path.join(wt, "evil.txt"), "w") as f:
            f.write("e\n")
        fx._git("add", "evil.txt", cwd=wt)
        fx._git("commit", "-q", "--amend", "--no-edit", cwd=wt)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("undeclared change", p.stdout)

    def test_a_member_merged_alone_fails_verify(self):
        fx = self.fx
        self.assembled()
        fx.fake_gh("pr", "merge", "101", "--merge")
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("state: #101 is MERGED", p.stdout)

    def test_an_edit_hidden_in_a_merge_of_main_is_caught(self):
        """A first-parent merge of origin/main is checked like a member merge: its tree must equal
        the clean merge of its parents unless a resolution was recorded through --merge-main."""
        fx = self.fx
        self.assembled()
        fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        wt = fx.wt("b1")
        fx._git("fetch", "-q", "origin", cwd=wt)
        fx._git("merge", "--no-ff", "--no-edit", "origin/main", cwd=wt)
        with open(os.path.join(wt, "kernel", "kernel.py"), "w") as f:
            f.write("VERSION = 2\nBACKDOOR = True\n")
        fx._git("add", "kernel/kernel.py", cwd=wt)
        fx._git("commit", "-q", "--amend", "--no-edit", cwd=wt)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL provenance: the origin/main merge", p.stdout)
        self.assertIn("differs from the clean merge of its parents (undeclared change in kernel/kernel.py)", p.stdout)
        self.assertFalse(fx.state("b1")["verified"]["ok"])
        # An unrecorded hand resolution while merging main in fails too, naming the file.
        fx._git("reset", "-q", "--hard", "HEAD^", cwd=wt)
        fx.commit_main({"kernel/kernel.py": "VERSION = 9\n"}, "main edits the kernel")
        fx._git("fetch", "-q", "origin", cwd=wt)
        fx._git("merge", "--no-ff", "--no-edit", "origin/main", cwd=wt, check=False)
        self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "MERGE_HEAD")), "main conflicts with #101 in kernel.py")
        with open(os.path.join(wt, "kernel", "kernel.py"), "w") as f:
            f.write("VERSION = 9\n")
        fx._git("add", "kernel/kernel.py", cwd=wt)
        fx._git("commit", "-q", "--no-edit", cwd=wt)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("resolved a conflict that is not recorded (in kernel/kernel.py)", p.stdout)

    def test_verify_fails_when_an_assembly_did_not_finish(self):
        """An assembly that dies half-way (a gh error on a later member) leaves `pending` non-empty
        and no head; verify must not adopt the branch tip and pass with the members missing."""
        fx = self.fx
        self.assembled()
        path = os.path.join(fx.dev, ".git", "batch", "b1.json")
        with open(path) as f:
            st = json.load(f)
        st["assembly"]["merged"] = st["assembly"]["merged"][:1]
        st["assembly"]["pending"] = [102]
        st["assembly"]["head"] = None
        with open(path, "w") as f:
            json.dump(st, f)
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("assembly incomplete: #102 never merged; run assemble again", p.stderr)
        self.assertIsNone(fx.state("b1")["verified"])

    def test_a_resolved_merge_that_equals_the_conflicted_merge_tree_fails_verify_on_its_markers(self):
        """A resolution amended back to the marker text byte for byte (the labels merge-tree uses)
        does not differ from the merge-tree of its parents, so the subset rule alone saw 'equals the
        clean merge'. verify reads the conflicted paths for markers whatever the trees say."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        self.assertEqual(fx.run("assemble", "b1", "--resolve", "108").returncode, 3)
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx.ok("assemble", "b1", "--continue", "--reviewed", "ok")
        p1, p2 = fx.dev_git("rev-list", "--parents", "-n1", "batch/b1").split()[1:]
        mt = fx.dev_git("merge-tree", "--write-tree", "--no-messages", p1, p2, check=False).splitlines()[0]
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write(fx.dev_git("show", mt + ":notes.txt") + "\n")
        fx._git("add", "notes.txt", cwd=wt)
        fx._git("commit", "-q", "--amend", "--no-edit", cwd=wt)
        self.assertEqual(fx.dev_git("rev-parse", "batch/b1^{tree}"), mt, "the merge now IS the conflicted merge-tree")
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL provenance: #108 merge", p.stdout)
        self.assertIn("conflict marker", p.stdout)
        self.assertIn("notes.txt", p.stdout)

    def test_a_declared_batch_commit_is_listed_under_read_these_first(self):
        fx = self.fx
        self.assembled()
        wt = fx.wt("b1")
        with open(os.path.join(wt, "hotfix.py"), "w") as f:
            f.write("FIX = 1\n")
        fx._git("add", "hotfix.py", cwd=wt)
        fx._git("commit", "-q", "-m", "batch: hotfix for the integrated tree", cwd=wt)
        sha = fx._git("rev-parse", "HEAD", cwd=wt)
        fx.sweep("b1")
        fx.ok("verify", "b1")
        self.assertEqual(fx.state("b1")["assembly"]["declared"][0]["subject"], "batch: hotfix for the integrated tree")
        body = fx.ok("summarize", "b1", "--print-only").stdout
        self.assertIn("- `batch:` commit %s by the batcher: batch: hotfix for the integrated tree; 1 file changed, 1 insertion(+); touches hotfix.py." % sha[:10], body)
        self.assertTrue(body.splitlines()[1].startswith("Land with `scripts/batch.py land b1`: it reads main again right before "
                                                         "the merge and refuses if the batch head no longer contains it. "
                                                         "Verified at"), body.splitlines()[1])

    def test_a_verify_that_dies_half_way_leaves_no_green_verification(self):
        fx = self.fx
        self.assembled()
        fx.sweep("b1")
        fx.ok("verify", "b1")
        self.assertTrue(fx.state("b1")["verified"]["ok"])
        p = fx.run("verify", "b1", gh_fail="pr view 102")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("HTTP 502", p.stderr)
        self.assertIsNone(fx.state("b1")["verified"], "the earlier green verdict is gone")
        self.assertIn("NOT VERIFIED", fx.ok("summarize", "b1", "--print-only").stdout)

    def test_the_ledger_check_reads_the_branch_not_the_worktree_directory(self):
        fx = self.fx
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": FAKE_LEDGER}, "ledger migration")
        # Cut after the migration, so the merge is clean and the row lands on the branch unconverted.
        fx.branch("s", {"UPSTREAM.md": prose_only + "\n| row two | fork PR #110 | candidate | why |\n"})
        fx.pr(110, "s", title="a straggler row after the migration", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("FAIL ledger: UPSTREAM.md:", p.stdout)
        fx.dev_git("worktree", "remove", "--force", fx.wt("b1"))
        self.assertFalse(os.path.isdir(fx.wt("b1")))
        fx.sweep("b1")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, "a missing worktree does not turn FAIL into OK:\n" + p.stdout + p.stderr)
        self.assertIn("FAIL ledger: UPSTREAM.md:", p.stdout)
        self.assertNotIn("pre-migration", p.stdout)
        self.assertEqual(fx.dev_git("worktree", "list", "--porcelain").count("worktree "), 1, "the temporary checkout is gone")


# Runs a batch.py (argv[2], then its argv) with a short GIT_BOUND on the planted calls alone: the 02:43Z ruling's pins
# (BatchGitBound), whose planted files a git waits on, end at that bound rather than batch.py's. argv[1] is bound_spec's
# JSON, {"bound": seconds, "on": [a call's leading words, ...], "log": a path or null}: a run_git call whose arguments,
# joined by spaces, start with one of those, or a run_tool call whose command does, has `bound` seconds, and every other
# call keeps batch.py's GIT_BOUND as the module set it when loaded (the 22:21Z ruling on the merge of fork main, item 1:
# a bound on every call ended a normal call that took longer under load, so the pin read the load, not the planted
# event). That full bound is read once, at the load, not at each call: a call made inside a planted one (run_tool's
# repo_for, whose rev-parse runs before the tool starts) read the planted call's short bound as its own and ran at it
# (the verify pass at the closing check wf_fb19febe-36b's build, its code finding 1). Each call restores the bound it
# found, so the planted call waits at its short bound after the call inside it returns. With "memory" in the JSON, the
# planted calls run under that memory limit too, set as scripts/sweep.py's GIT_MEMORY in the module batch.py reads its
# limits from (git_limits; a batch.py without it sets none), so a pin keys on the planted call and no xdist worker holds
# batch.py's own figure. With a log, each call appends the bound it ran at, how it ended ("memory" for GitMemory,
# "bound" for any other GitBound, "ended" for a return, "raised" for any other exception), the largest resident size in
# bytes of any child the process had reaped when it ended (RUSAGE_CHILDREN; Linux reports it in KiB) and the call, a
# line of four tab-separated fields.
BATCH_BOUND_DRIVER = r"""
import importlib.util, json, resource, sys
spec_, path, argv = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3:]
spec = importlib.util.spec_from_file_location("batch_tool_bounded", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
short, planted, log, memory = spec_["bound"], spec_["on"], spec_.get("log"), spec_.get("memory")
def planted_bound(module, full, call, start, *args, **kwargs):
    hit = any(call.startswith(words) for words in planted)
    found, bound = module.GIT_BOUND, short if hit else full
    module.GIT_BOUND, ended = bound, "raised"
    limits = module.git_limits() if memory and hit and hasattr(module, "git_limits") else None
    if limits is not None:
        found_memory, limits.GIT_MEMORY = limits.GIT_MEMORY, memory
    try:
        result = start(*args, **kwargs)
        ended = "ended"
        return result
    except module.GitBound as e:
        ended = "memory" if type(e).__name__ == "GitMemory" else "bound"
        raise
    finally:
        module.GIT_BOUND = found
        if limits is not None:
            limits.GIT_MEMORY = found_memory
        if log:
            peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
            with open(log, "a") as f:
                f.write("%s\t%s\t%d\t%s\n" % (bound, ended, peak, call))
full = mod.GIT_BOUND
if spec_.get("git_memory"):
    mod.git_limits().GIT_MEMORY = spec_["git_memory"]
if spec_.get("hook_memory"):
    mod.HOOK_MEMORY = spec_["hook_memory"]
run_git, run_tool = mod.run_git, mod.run_tool
mod.run_git = lambda args, *a, **k: planted_bound(mod, full, " ".join(args), run_git, args, *a, **k)
mod.run_tool = lambda cmd, *a, **k: planted_bound(mod, full, " ".join(cmd), run_tool, cmd, *a, **k)
sys.exit(mod.main(argv))
"""
# BATCH_BOUND_DRIVER with the planted calls of scripts/sweep.py's run_git at the same bound in every copy of it batch.py
# loads (sweep_reader), every other call at that copy's GIT_BOUND as loaded: the excuse rule's git call is sweep.py's,
# bounded by that script's GIT_BOUND (120 s), not batch.py's.
BATCH_SWEEP_BOUND_DRIVER = BATCH_BOUND_DRIVER.replace("sys.exit(mod.main(argv))\n", """read_sweep = mod.sweep_reader
def sweep_reader():
    reader = read_sweep()
    sweep_git, sweep_full = reader.run_git, reader.GIT_BOUND
    reader.run_git = lambda repo, *args, **k: planted_bound(reader, sweep_full, " ".join(args), sweep_git, repo, *args, **k)
    return reader
mod.sweep_reader = sweep_reader
sys.exit(mod.main(argv))
""")
assert BATCH_SWEEP_BOUND_DRIVER != BATCH_BOUND_DRIVER
# BATCH_BOUND_DRIVER with SIGHUP at its default action and SIGINT's handler Python's own first, as a process started from
# a terminal has them, so a case that sends either signal does not depend on how the test run itself was started: a
# non-interactive shell starts a background job with SIGINT ignored, and batch.py keeps a SIGINT it was started with
# ignored (IGNORE_INHERITED).
BATCH_TERMINAL_DRIVER = BATCH_BOUND_DRIVER.replace("sys.exit(mod.main(argv))\n", """import signal
signal.signal(signal.SIGHUP, signal.SIG_DFL)
signal.signal(signal.SIGINT, signal.default_int_handler)
sys.exit(mod.main(argv))
""")
assert BATCH_TERMINAL_DRIVER != BATCH_BOUND_DRIVER


def bound_spec(bound, *on, log=None, memory=None, git_memory=None, hook_memory=None):
    """BATCH_BOUND_DRIVER's argv[1]: `bound` seconds for the calls whose leading words `on` gives, and with `memory` that
    many bytes of address space for them; every other call keeps the script's GIT_BOUND and memory limit, which
    `git_memory` and `hook_memory` set in place of GIT_MEMORY (in the module batch.py reads it from) and HOOK_MEMORY.
    With `log`, the driver appends a line per call to that path."""
    return json.dumps({"bound": bound, "on": list(on), "log": log, "memory": memory, "git_memory": git_memory,
                       "hook_memory": hook_memory})


def _descendants(pid):
    """Every descendant of `pid` alive now, read from /proc/<pid>/task/*/children and down (Linux); [] where /proc has no
    such file. The same helper as tests/test_sweep_runner.py's, which pins the pair's behaviour there too."""
    found, todo = [], [pid]
    while todo:
        p = todo.pop()
        try:
            tasks = os.listdir("/proc/%d/task" % p)
        except OSError:
            continue
        for t in tasks:
            try:
                with open("/proc/%d/task/%s/children" % (p, t)) as f:
                    kids = [int(x) for x in f.read().split()]
            except (OSError, ValueError):
                continue
            for k in kids:
                if k not in found:
                    found.append(k)
                    todo.append(k)
    return found


def kill_tree(pid):
    """SIGKILL the watched process `pid` (a batch.py the watchdog gave up on), its process group, and every descendant of
    it with that descendant's own process group, the descendants read before any kill: each git run_git starts is in a
    session of its own, so killing the watched group alone left those waiting (the verify pass at PR 926's build head,
    its code finding 4). The test's own process group is never signalled, and off Linux, with no /proc to read, the
    watched group alone is."""
    own = os.getpgrp()
    for target in [pid] + _descendants(pid):
        try:
            group = os.getpgid(target)
        except OSError:
            continue
        if group > 1 and group != own:
            try:
                os.killpg(group, 9)
            except OSError:
                pass
        if target != os.getpid():
            try:
                os.kill(target, 9)
            except OSError:
                pass


# The states /proc/<pid>/stat gives a process that has exited: Z, a zombie its parent has not reaped, and X, dead while
# its reaper releases it (tests/test_sweep_runner.py's DEAD_STATES, where a check that read X as alive turned its
# watchdog pin red).
DEAD_STATES = ("Z", "X")


def _proc_alive(pid):
    """Whether the process `pid` is alive, read from /proc (Linux): one in DEAD_STATES has exited. False where there is
    no such file."""
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().rsplit(")", 1)[1].split()[0] not in DEAD_STATES
    except (OSError, IndexError):
        return False


def _kill_alive(pids):
    """SIGKILL each of `pids` (processes a case recorded itself) that /proc says is alive, so a case that goes red still
    leaves nothing it started running; off Linux, with no /proc to tell a live process from a reused pid, none is
    signalled."""
    for pid in pids:
        if _proc_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def _groups_of(pids):
    """The process groups of `pids`, read now, but the test's own and any group at or below 1. Each git batch.py starts
    leads a group of its own (a session of its own), and a process that git starts later joins that group: git worktree
    add's git reset --hard, started after a stop pin had read the descendants, ran on in that group once the add was
    killed by its pid (StopPinsLeaveNothing red under load in the build of the closing check wf_fb19febe-36b's rulings)."""
    own, groups = os.getpgrp(), []
    for pid in pids:
        try:
            group = os.getpgid(pid)
        except OSError:
            continue
        if group > 1 and group != own and group not in groups:
            groups.append(group)
    return groups


def _release_fifo(path):
    """Open the FIFO `path` for writing without waiting, and close it, so a reader blocked on it (a hook or a child a red
    case left waiting) reads its end; nothing happens when no reader is waiting (ENXIO) or the FIFO is gone."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        return
    os.close(fd)


def _recorded_pids(path):
    """The pids a fake git wrote to `path` (its own and its child's), or [] when it never wrote them."""
    try:
        with open(path) as f:
            return [int(x) for x in f.read().split()]
    except (OSError, ValueError):
        return []


# A git first on PATH for BatchGitBound's commit-read pins: it runs the real git (PLANT_REAL_GIT), except that just before
# the first call whose argv, joined by spaces, holds PLANT_ON it makes PLANT_FIFO a FIFO, so that call, and no
# earlier one, meets it, as a FIFO swapped in at the batcher's shallow file by a process outside the tool would be met.
PLANT_GIT = r"""#!/bin/sh
case " $* " in
  *"$PLANT_ON"*) [ -e "$PLANT_FIFO" ] || mkfifo "$PLANT_FIFO" ;;
esac
exec "$PLANT_REAL_GIT" "$@"
"""


# Starts a program with its address-space limit (RLIMIT_AS), soft and hard, at the number of bytes in its first argument
# (or the inherited hard limit, where that is lower), then execs the rest of its arguments in its own process, as
# tests/test_sweep_runner.py's CAP_SHIM does: the hard limit holds for every descendant, so a git that reads a symlink
# to /dev/zero fails at the cap, on Linux, which enforces RLIMIT_AS, instead of taking the machine's memory.
CAP_SHIM = ("import os, resource, sys\n"
            "cap, hard = int(sys.argv[1]), resource.getrlimit(resource.RLIMIT_AS)[1]\n"
            "cap = cap if hard == resource.RLIM_INFINITY else min(cap, hard)\n"
            "resource.setrlimit(resource.RLIMIT_AS, (cap, cap))\n"
            "os.execv(sys.argv[2], sys.argv[2:])\n")
# The cap the batch pins that plant a read without end run under: 2 GiB, as tests/test_sweep_runner.py's MEMORY_PIN_CAP,
# since free-threaded 3.14 reserves about 1 GiB of address space as it starts.
PLANT_CAP = 2 << 30
# The memory limit the planted calls of the batch memory pins run under (BATCH_BOUND_DRIVER's "memory"): far below
# batch.py's own GIT_MEMORY, so a pin's git reads a planted /dev/zero to no more than this, and above what any call the
# fixture makes needs, so a reaped child's resident size above it is the planted call's.
PLANT_MEMORY = 128 << 20
# A sparse file the batch memory pins plant (made with truncate, no byte of it written): larger than PLANT_MEMORY and
# than REF_FILE_MAX, and under the 1 GiB file size limit a capped run sets (ulimit -f), as tests/test_sweep_runner.py's
# SPARSE_SIZE.
PLANT_SPARSE = 512 << 20
# The end of the list of places a GitMemory's remedy names (_limit_met), as the pins quote it: the state files of
# GIT_DIR_STATE_FILES since round 3 of PR 959 (extra4-1).
REMEDY_PLACES = ("objects/info/alternates or the shallow file, or a state file in the git dir that a commit, a merge or a "
                 "bisect reads whole, COMMIT_EDITMSG, MERGE_MSG, MERGE_MODE, SQUASH_MSG, MERGE_AUTOSTASH or BISECT_START)")
# The HOOK_MEMORY the listing pin sets (BATCH_BOUND_DRIVER's "hook_memory"): above PLANT_MEMORY, so the two limits are
# told apart, and below PLANT_SPARSE, so a push that reads the planted file whole fails at it, far from 16 GiB.
PLANT_HOOK_MEMORY = 384 << 20
# origin/main's full ref, and its short name under refs/tags, a name git's rev-parse rules try before refs/remotes: the
# two places the batch memory pins plant a symlink to /dev/zero.
ORIGIN_MAIN_REF = "refs/remotes/origin/main"
TAG_OF_ORIGIN_MAIN = "refs/tags/origin/main"
# git's rev-parse rules, ref_rev_parse_rules in git's refs.c (git 2.43), as tests/test_sweep_runner.py's REV_PARSE_RULES: the
# names a short name is tried as, in order. BATCH_SHADOWS are those tried before refs/heads/<name>, made of the fixture's
# batch branch, batch/b1: the names a read of that branch by its short name opens first, the first of them beside the batch
# state (<common dir>/batch/b1, next to <common dir>/batch/b1.json); the batch pins of the 22:25Z ruling of
# 2026-10-03 on PR 959, item 1, plant a symlink to /dev/zero at each.
REV_PARSE_RULES = ("%s", "refs/%s", "refs/tags/%s", "refs/heads/%s", "refs/remotes/%s", "refs/remotes/%s/HEAD")
BATCH_SHADOWS = tuple(rule % "batch/b1" for rule in REV_PARSE_RULES[:REV_PARSE_RULES.index("refs/heads/%s")])
# The file git checkout -B batch/<name> <start point> opens for its start point, ORIGIN_MAIN_REF, as a local branch
# (refs/heads/<start point>) before it resets the branch (git 2.43.0, traced on 2026-10-04): beside BATCH_SHADOWS, a
# file the short-name witness plants at, in its case of a reused batch worktree.
START_AS_A_BRANCH = REV_PARSE_RULES[REV_PARSE_RULES.index("refs/heads/%s")] % ORIGIN_MAIN_REF
# PLANT_GIT's twin for a read without end: just before the first call whose argv holds PLANT_ON it replaces PLANT_ZERO
# with a symlink to /dev/zero, so that call, and no earlier one, reads it.
PLANT_ZERO_GIT = r"""#!/bin/sh
case " $* " in
  *"$PLANT_ON"*) [ -L "$PLANT_ZERO" ] || ln -sfn /dev/zero "$PLANT_ZERO" ;;
esac
exec "$PLANT_REAL_GIT" "$@"
"""


# The hook-memory pin's figures (round 2 of PR 959, ruling C, item 1): the bytes of address space RESERVING_HOOK
# reserves, more than the GIT_MEMORY the pin sets and less than its HOOK_MEMORY less the most an interpreter the suite
# runs reserves as it starts (free-threaded 3.14 reserved about 1060 MiB, 3.12 about 18 MiB, on 2026-10-04,
# MALLOC_ARENA_MAX unset; the same with it at 2), so the hook runs under the one and not under the other whatever
# interpreter runs it; neither limit is a real 16 GiB.
HOOK_RESERVE = 640 << 20
HOOK_PIN_GIT_MEMORY = 512 << 20
HOOK_PIN_HOOK_MEMORY = 2 << 30
# A hook that reserves HOOK_RESERVE bytes of address space with one anonymous map it never touches, as gitleaks reserves
# its own as it starts, appends its name, the soft RLIMIT_AS it ran under and what came of the map to the file named
# here, and fails, saying so on stderr, when it could not reserve them. %-formatted with python, size and log.
RESERVING_HOOK = r"""#!%(python)s
import mmap, os, resource, sys
soft = resource.getrlimit(resource.RLIMIT_AS)[0]
try:
    mmap.mmap(-1, %(size)d, flags=mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS)
    said = "reserved"
except OSError as e:
    said = "could not reserve: %%s" %% e.strerror
    print("%%s: %%s" %% (os.path.basename(sys.argv[0]), said), file=sys.stderr)
with open(%(log)r, "a") as f:
    f.write("%%s %%d %%s\n" %% (os.path.basename(sys.argv[0]), soft, said))
sys.exit(0 if said == "reserved" else 1)
"""


class BatchGitBound(_Base):
    """The 02:43Z ruling on PR 926, item 1, in batch.py: every git it starts goes through run_git, which has a bounded wait
    (GIT_BOUND; each pin runs batch.py with a bound of BOUND seconds on the call that meets its plant alone,
    BATCH_BOUND_DRIVER, and batch.py's own on every other call) and names the repository it
    means (GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE explicit, GIT_CEILING_DIRECTORIES above it). Each pin runs batch.py
    in a process group of its own under a 60 s watchdog, so a regression fails by name instead of hanging."""

    BOUND = 3

    def bounded(self, *args, env=None, driver=BATCH_BOUND_DRIVER, bound=None, planted=(), cap=None, memory=None,
                git_memory=None, hook_memory=None):
        """(rc, stdout, stderr) of batch.py `args`, run through `driver` with the calls `planted` names (their leading
        words) at `bound` seconds (default BOUND), so the case keys on the call that meets its plant, not on how long a
        normal call takes under load. Every call that ran at that bound must have ended at it (GitBound), or the case
        fails naming the call: the short bound then reached a call that met no plant, a call made inside a planted one
        or a planted call whose case planted nothing, and that call ends early under load (the 22:21Z ruling on the
        merge of fork main, item 1; the verify pass at the closing check wf_fb19febe-36b's build, its code finding
        1). With `cap`, batch.py runs under CAP_SHIM with its address space capped at that many bytes, soft and hard, so
        every git it starts has the cap too. With `memory`, the planted calls run under that memory limit as well
        (BATCH_BOUND_DRIVER), and with `git_memory` and `hook_memory` every other call under those in place of
        GIT_MEMORY and HOOK_MEMORY (bound_spec). The calls the driver logged are left in self.calls, each [bound, how it
        ended, the largest resident size of a reaped child then, the call]."""
        fx = self.fx
        short = bound or self.BOUND
        fd, log = tempfile.mkstemp(prefix="bound-calls-", suffix=".log", dir=fx.tmp)
        os.close(fd)
        capped = [] if cap is None else [sys.executable, "-c", CAP_SHIM, str(cap)]
        spec = bound_spec(short, *planted, log=log, memory=memory, git_memory=git_memory, hook_memory=hook_memory)
        proc = subprocess.Popen(capped + [sys.executable, "-c", driver, spec,
                                 os.path.join(fx.dev, "scripts", "batch.py"), *args], cwd=fx.tmp, env=env or fx.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)

        # kill_tree: batch.py's group and each of its descendants with its own group, so no git it started in a session
        # of its own outlives the case (the verify pass at PR 926's build head, its code finding 4)
        self.addCleanup(lambda: proc.poll() is None and kill_tree(proc.pid))
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("batch.py %s was still running after 60 s, waiting without end on a file a git it started opened:\n%s%s"
                      % (" ".join(args), out, err))
        with open(log) as f:
            calls = [line.rstrip("\n").split("\t", 3) for line in f]
        self.calls = calls
        self.assertEqual([c for c in calls if c[0] == str(short) and c[1] not in ("bound", "memory")], [],
                         "a call at the short bound that did not end at it: the bound reached a call that met no plant, "
                         "or one that met its plant with no bound to end it; batch.py printed:\n%s%s" % (out, err))
        return proc.returncode, out, err

    def assembled(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.sweep("b1")

    def test_a_fifo_at_the_shallow_file_refuses_verify_and_plan_naming_the_call(self):
        """The 02:43Z ruling's fifth road: the batcher's .git/shallow is a FIFO (a leg reaches it through its clone's
        alternates). verify's first git call that reads it, the fetch, or with --no-fetch the provenance check's rev-list,
        and plan's fetch, wait until the bound, are killed, and each is refused (exit 1) naming the call. Before this
        change each waited without end."""
        fx = self.fx
        self.assembled()
        os.mkfifo(os.path.join(fx.dev, ".git", "shallow"))
        for args, call in ((("verify", "b1"), "fetch --quiet --prune origin"),
                           (("verify", "b1", "--no-fetch"), "rev-list refs/heads/batch/b1 ^refs/remotes/origin/main ^"),
                           (("plan", "--name", "b2"), "fetch --quiet --prune origin")):
            with self.subTest(args=args):
                rc, out, err = self.bounded(*args, planted=[call])
                self.assertEqual(rc, 1, out + err)
                self.assertIn("batch: git %s" % call, err)
                self.assertIn(" in %s did not end within 3 s and was killed" % fx.dev, err)

    def test_a_fifo_at_the_clones_index_or_info_exclude_stops_verify_and_plan_only_where_their_git_reads_it(self):
        """The closing check wf_3b100f5e-b38, its item 8, as docs/batching.md states it for batch.py: a leg plants a FIFO
        at the clone's own .git/index or .git/info/exclude (it reaches the clone's common dir through its checkout's
        alternates). verify and plan run their git in the clone's own work tree. git fetch and git diff-tree read that
        work tree's index, so with a FIFO there plan stops at its fetch, and verify at its fetch or, with --no-fetch, at the
        diff-tree of its check of the member's merge, each at the bound, naming the call. git worktree add reads
        info/exclude, so with a FIFO there verify, fetching or not, stops at its ledger check's worktree add (the branch
        carries the ledger script, as every batch cut from main does), while plan, which adds no worktree, ends as it ends
        without the FIFO (git 2.43, 2026-10-01). Each case runs at the bound, under BatchGitBound's watchdog."""
        fx = self.fx
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": FAKE_LEDGER}, "ledger migration")
        self.assembled()
        rc_plan, out, err = self.bounded("plan", "--name", "b2")
        self.assertNotIn("did not end within", out + err, "premise: plan ends without the FIFO")
        cases = (("index", ("verify", "b1"), "fetch --quiet --prune origin"),
                 ("index", ("verify", "b1", "--no-fetch"), "diff-tree --name-only -r "),
                 ("index", ("plan", "--name", "b2"), "fetch --quiet --prune origin"),
                 ("info/exclude", ("verify", "b1"), "worktree add --quiet --detach "),
                 ("info/exclude", ("verify", "b1", "--no-fetch"), "worktree add --quiet --detach "),
                 ("info/exclude", ("plan", "--name", "b2"), None))
        for where, args, call in cases:
            with self.subTest(where=where, args=" ".join(args)):
                path = os.path.join(fx.dev, ".git", where)
                saved = None
                if os.path.lexists(path):
                    with open(path, "rb") as f:
                        saved = f.read()
                    os.remove(path)
                os.mkfifo(path)
                try:
                    rc, out, err = self.bounded(*args, planted=[call] if call else [])
                finally:
                    os.remove(path)
                    if saved is not None:
                        with open(path, "wb") as f:
                            f.write(saved)
                if call is None:
                    self.assertEqual(rc, rc_plan, out + err)
                    self.assertNotIn("did not end within", out + err)
                else:
                    self.assertEqual(rc, 1, out + err)
                    self.assertIn("batch: git %s" % call, err)
                    self.assertIn(" in %s did not end within 3 s and was killed" % fx.dev, err)

    def test_verifys_own_commit_reads_on_a_fifo_shallow_file_end_at_the_bound_naming_the_call(self):
        """The 02:43Z ruling's fifth road as the verify pass measured it: batch.py verify's own git calls that parse a
        commit, merge-base --is-ancestor (whether the batch head contains main as origin has it) and cat-file -e
        <main>^{commit} (whether that commit is here, asked when the head does not contain it), each meeting a FIFO at
        the batcher's shallow file. The FIFO is planted by a git first on PATH just before the call named (PLANT_GIT), so
        the calls before it, the fetch and the provenance check's reads among them, meet none, and that one does, as it
        would meet a FIFO a process outside the tool swapped in. Each waits until the bound, is killed, and verify is
        refused (exit 1) naming it. Before this change each waited without end (the case then fails at the watchdog)."""
        fx = self.fx
        self.assembled()
        head = fx.dev_git("rev-parse", "batch/b1")
        plant = os.path.join(fx.tmp, "plant-bin")
        os.makedirs(plant)
        with open(os.path.join(plant, "git"), "w") as f:
            f.write(PLANT_GIT)
        os.chmod(os.path.join(plant, "git"), 0o755)
        shallow = os.path.join(fx.dev, ".git", "shallow")
        env = dict(fx.env, PATH=plant + os.pathsep + fx.env["PATH"], PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]),
                   PLANT_FIFO=shallow)
        for read in ("merge-base", "cat-file"):
            with self.subTest(call=read):
                if os.path.lexists(shallow):
                    os.remove(shallow)
                if read == "cat-file":
                    fx.commit_main({"README.md": "main moved on after the assembly\n"})
                main = fx.bare_rev("main")
                call = ("merge-base --is-ancestor %s %s" % (main, head) if read == "merge-base"
                        else "cat-file -e %s^{commit}" % main)
                rc, out, err = self.bounded("verify", "b1", env=dict(env, PLANT_ON=call), planted=[call])
                self.assertEqual(rc, 1, out + err)
                self.assertTrue(stat.S_ISFIFO(os.lstat(shallow).st_mode), "premise: the FIFO was planted")
                self.assertIn("batch: git %s in %s did not end within 3 s and was killed" % (call, fx.dev), err)

    def test_a_batchers_clone_git_does_not_recognize_inside_an_enclosing_repository_is_refused_and_left_alone(self):
        """The 02:43Z ruling, item 1(b), in batch.py: the clone it lives in sits inside an enclosing repository and its
        .git/HEAD is gone. find_repo reads the clone's .git with the ceiling at its parent, so verify is refused naming
        the clone, and nothing is read from or written to the enclosing repository. Before this change git walked up: the
        enclosing repository was taken for the batcher's, its common dir got a batch/ directory, and verify said it had no
        plan named b1."""
        fx = self.fx
        self.assembled()
        with open(os.path.join(fx.tmp, ".gitignore"), "w") as f:
            f.write("*\n")
        for args in (["init", "-q"], ["add", "-f", ".gitignore"], ["commit", "-q", "-m", "an enclosing repository"]):
            fx._git(*args, cwd=fx.tmp)
        os.remove(os.path.join(fx.dev, ".git", "HEAD"))
        rc, out, err = self.bounded("verify", "b1", "--no-fetch")
        self.assertEqual(rc, 1, out + err)
        self.assertIn("batch: %s is not a git working tree that git recognizes (fatal: not a git repository" % fx.dev, err)
        self.assertFalse(os.path.exists(os.path.join(fx.tmp, ".git", "batch")), "the enclosing repository is left alone")

    def test_a_batch_worktree_whose_git_file_is_gone_is_not_read_as_its_parent(self):
        """The 02:43Z ruling, item 1(b), at a batch worktree: its .git file is gone and its parent directory is inside an
        enclosing repository. bisect's reads there fail naming the worktree, and nothing is read from the enclosing
        repository. Before this change git walked up and bisect read the enclosing repository's branches ("batch/b1" there is
        no revision, an error about another repository)."""
        fx = self.fx
        self.assembled()
        with open(os.path.join(fx.tmp, ".gitignore"), "w") as f:
            f.write("*\n")
        for args in (["init", "-q"], ["add", "-f", ".gitignore"], ["commit", "-q", "-m", "an enclosing repository"]):
            fx._git(*args, cwd=fx.tmp)
        os.remove(os.path.join(fx.wt("b1"), ".git"))
        rc, out, err = self.bounded("bisect", "b1", "--", "true")
        self.assertEqual(rc, 1, out + err)
        self.assertIn("batch: %s is not a git working tree: no .git in it" % fx.wt("b1"), err)

    # A git first on PATH that appends each call's working directory and GIT_DIR to TRACE_LOG, then runs the real git.
    TRACE_GIT = r"""#!/bin/sh
printf '%s\t%s\n' "$(pwd -P)" "${GIT_DIR-}" >> "$TRACE_LOG"
exec "$TRACE_REAL_GIT" "$@"
"""

    def test_a_removed_batch_worktree_is_refused_naming_it_and_nothing_outside_the_clone_is_read(self):
        """The closing check wf_fb19febe-36b, its item 6: the batch worktree's directory is removed (its registration in
        the clone left as a removal by hand leaves it), and the directory that held it, the fixture's temp dir, is an
        enclosing repository. bisect and assemble --merge-main are each refused
        naming the worktree's path, and repo_for of that path, called directly in a child, is a Fail naming it ("there is
        no such directory") before any git call. A git first on PATH records every call: each runs in the clone, with no
        GIT_DIR or the clone's own, so none reads the enclosing repository or looks at the removed path, and the
        enclosing repository's HEAD and refs are as they were. This predates the explicit-start change (the closing
        check wf_3b100f5e-b38, its item 1): the head before it refused these the same way, since bisect and merge_main
        test the directory first and repo_for read a batch worktree without a walk; only repo_for's reason changed, from
        "no .git in it". The pin keeps it so."""
        fx = self.fx
        self.assembled()
        head = self.enclose()
        encl_refs = fx._git("for-each-ref", "--format=%(refname) %(objectname)", cwd=fx.tmp)
        wt = fx.wt("b1")
        shutil.rmtree(wt)
        trace = os.path.join(fx.tmp, "trace-bin")
        os.makedirs(trace)
        with open(os.path.join(trace, "git"), "w") as f:
            f.write(self.TRACE_GIT)
        os.chmod(os.path.join(trace, "git"), 0o755)
        log = os.path.join(fx.tmp, "git-calls.log")
        env = dict(fx.env, PATH=trace + os.pathsep + fx.env["PATH"], TRACE_LOG=log,
                   TRACE_REAL_GIT=shutil.which("git", path=fx.env["PATH"]))
        clone = os.path.realpath(fx.dev)
        for args, text in ((("bisect", "b1", "--", "true"), "batch: no batch worktree at %s\n" % wt),
                           (("assemble", "b1", "--merge-main", "--no-fetch"),
                            "batch: no batch worktree at %s; run assemble first\n" % wt)):
            with self.subTest(args=" ".join(args)):
                if os.path.exists(log):
                    os.remove(log)
                rc, out, err = self.bounded(*args, env=env)
                self.assertEqual((rc, err), (1, text), out + err)
                with open(log) as f:
                    calls = [line.rstrip("\n").split("\t") for line in f]
                self.assertNotEqual(calls, [], "premise: the traced git ran")
                self.assertEqual([c for c in calls if c[0] != clone or c[1] not in ("", os.path.join(clone, ".git"))], [],
                                 "every git call ran in the clone and named no other repository")
        if os.path.exists(log):
            os.remove(log)
        code = ("import importlib.util, sys\n"
                "spec = importlib.util.spec_from_file_location('batch_tool', sys.argv[1])\n"
                "mod = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(mod)\n"
                "try:\n"
                "    print('accepted', mod.repo_for(sys.argv[2]).work_tree)\n"
                "except mod.Fail as e:\n"
                "    print('failed', e)\n")
        try:
            p = subprocess.run([sys.executable, "-c", code, os.path.join(fx.dev, "scripts", "batch.py"), wt], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, env=env, timeout=60)
        except subprocess.TimeoutExpired:
            self.fail("repo_for was still running after 60 s")
        self.assertEqual((p.returncode, p.stdout), (0, "failed %s is not a git working tree: there is no such directory\n" % wt),
                         p.stdout + p.stderr)
        self.assertFalse(os.path.exists(log), "repo_for started no git")
        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=fx.tmp), head)
        self.assertEqual(fx._git("for-each-ref", "--format=%(refname) %(objectname)", cwd=fx.tmp), encl_refs)
        self.assertFalse(os.path.lexists(wt), "the removed path was not made again")

    def enclose(self):
        """Make the fixture's temp dir, which holds the clone, a repository whose root .gitignore is '*'; its head."""
        fx = self.fx
        with open(os.path.join(fx.tmp, ".gitignore"), "w") as f:
            f.write("*\n")
        for args in (["init", "-q"], ["add", "-f", ".gitignore"], ["commit", "-q", "-m", "an enclosing repository"]):
            fx._git(*args, cwd=fx.tmp)
        return fx._git("rev-parse", "HEAD", cwd=fx.tmp)

    def test_a_clone_whose_git_is_gone_inside_an_enclosing_repository_is_refused_naming_it(self):
        """The closing check wf_3b100f5e-b38, its item 1, first face, in batch.py: the clone it lives in (the directory
        above its scripts/) sits inside an enclosing repository and its .git is gone. The clone is not walked up from
        (find_repo has no walk), so verify is refused naming the clone, and nothing is read from or written to the
        enclosing repository. Before this change find_repo walked up to the enclosing repository: verify said it had no
        plan named b1 there and made a batch/ directory in its common dir."""
        fx = self.fx
        self.assembled()
        self.enclose()
        shutil.rmtree(os.path.join(fx.dev, ".git"))
        rc, out, err = self.bounded("verify", "b1", "--no-fetch")
        self.assertEqual((rc, out), (1, ""), out + err)
        self.assertEqual(err, "batch: %s is not a git working tree: no .git in it\n" % fx.dev)
        self.assertFalse(os.path.exists(os.path.join(fx.tmp, ".git", "batch")), "the enclosing repository is left alone")

    def test_a_mistyped_romp_batch_repo_is_refused_naming_it(self):
        """The closing check wf_3b100f5e-b38, its item 1, second face (a regression at its head): ROMP_BATCH_REPO names a
        path that does not exist, inside the clone and inside an enclosing repository. verify is refused naming the path
        given, and neither repository gets a batch/ directory it did not have. Before this change find_repo walked up
        from the missing path: inside the clone verify read the clone's plan as if it were named, and inside the
        enclosing repository it said it had no plan named b1 there and made a batch/ directory in its common dir."""
        fx = self.fx
        self.assembled()
        for where in ("clone", "enclosing"):
            with self.subTest(where=where):
                if where == "enclosing":
                    self.enclose()
                missing = os.path.join(fx.dev if where == "clone" else fx.tmp, "no-such-dir")
                rc, out, err = self.bounded("verify", "b1", "--no-fetch", env=dict(fx.env, ROMP_BATCH_REPO=missing))
                self.assertEqual((rc, out), (1, ""), out + err)
                self.assertEqual(err, "batch: %s is not a git working tree: there is no such directory\n" % missing)
                self.assertFalse(os.path.exists(os.path.join(fx.tmp, ".git", "batch")),
                                 "the enclosing repository is left alone")

    def test_a_clone_whose_config_names_another_work_tree_is_refused(self):
        """The closing check wf_3b100f5e-b38, its item 1, the discovery's refusal: the clone's config has core.worktree
        naming another directory, which a sweep's leg can write through its checkout's alternates. find_repo refuses a
        directory whose work tree, as git reads it there, is not that directory, so verify is refused naming both.
        Before this change git's show-toplevel there became the clone's work tree for every later call."""
        fx = self.fx
        self.assembled()
        other = os.path.join(fx.tmp, "another-work-tree")
        os.makedirs(other)
        fx.dev_git("config", "core.worktree", other)
        rc, out, err = self.bounded("verify", "b1", "--no-fetch")
        self.assertEqual((rc, out), (1, ""), out + err)
        self.assertEqual(err, "batch: %s is not the work tree git reads for the .git in it: git's work tree there is %s (a "
                              "core.worktree in the repository's config names it); give the directory that holds .git and "
                              "is its work tree\n" % (fx.dev, other))

    # find_repo, loaded in a child with a 60 s bound, given the clone, whose git reports its work tree as the text TOP
    # (each line of git's answer but the first kept), on a filesystem where the clone's name in its other letter case
    # names the clone, as on a case-insensitive filesystem (os.stat maps that spelling, and only that one, to the clone;
    # os.lstat, and so os.path.realpath, is left as it is, which keeps a path's case as given on such a filesystem too).
    # Prints, for each TOP, whether find_repo accepted the clone (and the work tree it returned) or failed it (and why).
    IDENTITY_DRIVER = (
        "import importlib.util, json, os, sys\n"
        "spec = importlib.util.spec_from_file_location('batch_tool', sys.argv[1])\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "clone, other = os.path.realpath(sys.argv[2]), os.path.realpath(sys.argv[3])\n"
        "variant = os.path.join(os.path.dirname(clone), os.path.basename(clone).swapcase())\n"
        "assert variant != clone, 'premise: the clone has a letter in its name'\n"
        "assert not os.path.lexists(variant) or os.path.samefile(variant, clone), 'premise: the other case names no other'\n"
        "real_stat = os.stat\n"
        "def case_blind_stat(path, *a, **k):\n"
        "    if isinstance(path, str) and (path == variant or path.startswith(variant + os.sep)):\n"
        "        path = clone + path[len(variant):]\n"
        "    return real_stat(path, *a, **k)\n"
        "os.stat = case_blind_stat\n"
        "real_run_git, top = mod.run_git, None\n"
        "def run_git(args, cwd, *a, **kw):\n"
        "    p = real_run_git(args, cwd, *a, **kw)\n"
        "    if '--show-toplevel' in args and p.returncode == 0:\n"
        "        p.stdout = '\\n'.join([top] + p.stdout.split('\\n')[1:])\n"
        "    return p\n"
        "mod.run_git = run_git\n"
        "out = {}\n"
        "for label, top in (('the other case', variant), ('another directory', other)):\n"
        "    try:\n"
        "        out[label] = ['accepted', mod.find_repo(clone).work_tree]\n"
        "    except mod.Fail as e:\n"
        "        out[label] = ['failed', str(e)]\n"
        "print(json.dumps({'variant': variant, 'found': out}))\n")

    def test_a_clone_named_through_a_symlink_or_in_another_spelling_is_accepted_and_another_directory_refused(self):
        """The closing check wf_fb19febe-36b, its item 9, in batch.py: find_repo compares git's work tree with the
        directory holding .git by identity (same_dir, os.path.samefile), not by their real paths' text. ROMP_BATCH_REPO
        naming the clone through a symlink is the clone: verify prints and exits as it does with no ROMP_BATCH_REPO.
        Then, by IDENTITY_DRIVER, git's work tree reported in the clone's other letter case, on a filesystem where that
        names the clone, is accepted, and the work tree returned is git's spelling; git's work tree reported as another
        directory that exists is a Fail naming both. The case-insensitive filesystem is simulated, so the case reads the
        same on a case-sensitive one: on a real one, git prints the work tree as getcwd gives it, in the case on disk,
        and os.path.realpath keeps the case a path was given in. Before this change find_repo compared
        os.path.realpath(top) with the directory, so the other case failed, blaming a core.worktree that does not
        exist; the symlink and another directory read as now."""
        fx = self.fx
        self.assembled()
        direct = self.bounded("verify", "b1", "--no-fetch")
        link = os.path.join(fx.tmp, "clone-link")
        os.symlink(fx.dev, link)
        self.assertEqual(self.bounded("verify", "b1", "--no-fetch", env=dict(fx.env, ROMP_BATCH_REPO=link)), direct)
        self.assertEqual(direct[0], 0, direct[1] + direct[2])
        other = os.path.join(fx.tmp, "another-work-tree")
        os.makedirs(other)
        try:
            p = subprocess.run([sys.executable, "-c", self.IDENTITY_DRIVER, os.path.join(fx.dev, "scripts", "batch.py"), fx.dev,
                                other], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                               env=fx.env, timeout=60)
        except subprocess.TimeoutExpired:
            self.fail("find_repo was still running after 60 s")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        got = json.loads(p.stdout)
        clone, other = os.path.realpath(fx.dev), os.path.realpath(other)
        self.assertEqual(got["found"], {
            "the other case": ["accepted", got["variant"]],
            "another directory": ["failed", "%s is not the work tree git reads for the .git in it: git's work tree there is "
                                            "%s (a core.worktree in the repository's config names it); give the directory "
                                            "that holds .git and is its work tree" % (clone, other)]})

    def test_bisect_runs_its_command_without_the_bound_and_names_the_member(self):
        """bisect takes the steps `git bisect run` would, with its exit rules, so the command runs outside git, without
        the bound, as at the tip and the base, while each git step has it: a command that takes longer than the bound
        (BOUND 3 s, on a `git bisect run`, the one git call that would carry the command; the command 4 s) still names
        the member. A `git bisect run` started through run_git would bound the command with it: killed at the bound,
        bisect would name nothing (the mutant gb-bisect-run-bounded)."""
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c", "sleep 4; grep -q 'return 1' postal/postal_service.py",
                                    planted=["bisect run"])
        self.assertEqual(rc, 0, out + err)
        self.assertIn("first bad: #102 postal: send two", out)

    # A bisect command over the two-member chain: it fails at the tip (#102's postal/postal_service.py returns 2), passes at
    # the base, and at the one commit bisect tests between them, #101's merge (kernel/kernel.py at VERSION = 2, #102 not yet
    # merged), runs the shell text given, so each of git bisect run's exit rules is met there.
    BISECT_CMD = ("if grep -q 'return 2' postal/postal_service.py; then exit 1; fi; "
                  "if grep -q 'VERSION = 2' kernel/kernel.py; then %s; fi; exit 0")

    def bisect_chain(self):
        """The two-member chain (two_members) planned and assembled as batch b1: (the tip, #101's merge)."""
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        tip = fx.dev_git("rev-parse", "batch/b1")
        merge_101 = fx.dev_git("rev-parse", "batch/b1^1")
        self.assertEqual(fx.dev_git("log", "-1", "--format=%s", merge_101), fx.chain("b1")[0],
                         "premise: the tip's first parent is the chain's first merge, #101's")
        return tip, merge_101

    def bisect_with(self, middle, env=None, driver=BATCH_BOUND_DRIVER):
        """bisect b1 over bisect_chain's chain with BISECT_CMD running `middle` at #101's merge, under the watchdog, in
        `env` (default the fixture's), through `driver`: (rc, stdout, stderr). No call has the short bound: the git
        steps are not what these cases test."""
        return self.bounded("bisect", "b1", "--", "sh", "-c", self.BISECT_CMD % middle, env=env, driver=driver)

    def bisected(self, middle):
        """bisect_with(`middle`) over a fresh bisect_chain: (rc, stdout, stderr, the tip, #101's merge)."""
        tip, merge_101 = self.bisect_chain()
        rc, out, err = self.bisect_with(middle)
        return rc, out, err, tip, merge_101

    def assert_reset_at_the_tip(self, tip):
        """bisect is reset in the batch worktree (no BISECT_START in its git dir), which is on batch/b1 at `tip`."""
        fx = self.fx
        wt = fx.wt("b1")
        self.assertFalse(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "BISECT_START")),
                         "bisect is reset")
        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), tip, "HEAD is at the tip")
        self.assertEqual(fx._git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt), "batch/b1", "the worktree is on the branch")

    def test_bisects_checkout_of_the_base_reads_a_ref_named_by_its_id_and_stops_at_the_memory_limit(self):
        """Round 1 of PR 959, V5: git checkout <sha> looks the id up as a ref name under every rule of git's rev-parse rules
        first, whatever core.warnAmbiguousRefs says, so bisect's checkout of the base reads a symlink to /dev/zero a leg
        left at refs/tags/<base> in the clone, whose refs the batch worktree shares. Under the memory limit every git
        batch.py starts has (V1; PLANT_MEMORY on that call) bisect stops (exit 1) with GitMemory naming the checkout, the
        call held no more than the limit, and the cleanup leaves the worktree on the branch at the tip. Before V1 the
        checkout read the symlink until PLANT_CAP and died with "fatal: Out of memory, realloc failed", reported as a plain
        git failure."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        tip, _merge_101 = self.bisect_chain()
        wt = fx.wt("b1")
        base = fx._git("merge-base", ORIGIN_MAIN_REF, tip, cwd=wt)
        planted = os.path.join(fx.dev, ".git", "refs", "tags", base)
        os.symlink("/dev/zero", planted)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        call = "checkout --quiet --detach %s" % base
        rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c", self.BISECT_CMD % "exit 1", cap=PLANT_CAP, bound=60,
                                    planted=[call], memory=PLANT_MEMORY)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("batch: git %s in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and failed "
                      "(fatal: Out of memory, " % (call, wt, PLANT_MEMORY >> 20), err)
        ended = [c for c in self.calls if c[3] == call]
        self.assertEqual([c[1] for c in ended], ["memory"], "bisect's checkout of the base ended at the memory limit")
        self.assertLessEqual(int(ended[0][2]), PLANT_MEMORY, "the checkout held more than its limit: %s" % ended)
        os.remove(planted)
        self.assert_reset_at_the_tip(tip)

    def plant_batch_shadows(self, fx=None):
        """A symlink to /dev/zero at each of BATCH_SHADOWS in `fx`'s clone (default the test's fixture), removed on the way
        out; returns their paths."""
        fx = fx or self.fx
        paths = []
        for name in BATCH_SHADOWS:
            path = os.path.join(fx.dev, ".git", *name.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.symlink("/dev/zero", path)
            self.addCleanup(lambda p=path: os.path.lexists(p) and os.remove(p))
            paths.append(path)
        return paths

    def test_bisects_cleanups_read_no_name_the_batch_branchs_short_name_would_open(self):
        """The 22:25Z ruling of 2026-10-03 on PR 959, item 1, at bisect: its cleanups (after the run at the base, and
        after the steps) name the batch branch by its full ref alone (restore_branch_tree, attach_to_branch) and end the
        bisect with a plain git bisect reset, which checks nothing out (the bisect runs with --no-checkout from HEAD
        detached at the tip, so git bisect start records the tip's id, not the short name), so a symlink to /dev/zero at
        each name git's rev-parse rules try before refs/heads/batch/b1 (BATCH_SHADOWS), which a leg can leave in the
        clone through its checkout's alternates, is never read. bisect, run under PLANT_CAP, exits and prints as it does
        with nothing planted and leaves the worktree on batch/b1 at the tip with no bisect in progress, both when the
        worktree has no changes to tracked files (each cleanup's restore forced) and when it has one, which the cleanups
        keep (unforced); each case in a fixture of its own. Red at the head before the ruling, where the cleanup's git
        checkout of batch/b1 read the first of them and bisect stopped with GitMemory naming that checkout; and red with
        HEAD left on the branch as the bisect starts (the mutant mNoDetach), where git bisect start --no-checkout looks
        up the short name it records and fails at the memory limit, and the plain git bisect reset, with no BISECT_HEAD
        written, checks that name out and fails the same way."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        self.maxDiff = None
        for n, case in enumerate(("forced", "unforced")):
            with self.subTest(cleanup=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                tip, _merge_101 = self.bisect_chain()
                wt = fx.wt("b1")
                notes = os.path.join(wt, "notes.txt")
                with open(notes) as f:
                    text = f.read()
                if case == "unforced":
                    text += "a change the cleanups keep\n"
                    with open(notes, "w") as f:
                        f.write(text)
                args = ("bisect", "b1", "--", "sh", "-c", self.BISECT_CMD % "exit 1")

                def left():
                    # assert_reset_at_the_tip without its rev-parse --abbrev-ref, which shortens the branch's name by
                    # trying the names the planted symlinks are at, and would read one without end: a plain symbolic-ref
                    # prints HEAD's target and reads no other name
                    self.assertFalse(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1",
                                                                 "BISECT_START")), "bisect is reset")
                    self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), tip, "HEAD is at the tip")
                    self.assertEqual(fx._git("symbolic-ref", "HEAD", cwd=wt), "refs/heads/batch/b1",
                                     "the worktree is on the branch")
                    with open(notes) as f:
                        self.assertEqual(f.read(), text, "the worktree's notes.txt, as it was before bisect")
                want = self.bounded(*args, cap=PLANT_CAP)
                self.assertEqual((want[0], want[2]), (0, ""), "premise: bisect with nothing planted:\n%s%s" % want[1:])
                self.assertIn("first bad: #101 ", want[1])
                left()
                planted = self.plant_batch_shadows()
                self.assertEqual(self.bounded(*args, cap=PLANT_CAP), want, "bisect with a symlink to /dev/zero at each "
                                 "of %s" % ", ".join(BATCH_SHADOWS))
                left()
                self.assertTrue(all(os.path.islink(p) for p in planted), "premise: the symlinks are still there")

    def test_bisects_cleanup_after_the_steps_reads_no_name_a_plant_left_during_the_steps_would_open(self):
        """The 22:25Z ruling of 2026-10-03 on PR 959, item 1, and the verify pass at this pass's build, its F1: bisect's
        cleanup after its steps reads neither the batch branch's short name nor the tip's id. The command, at the one
        commit bisect tests (#101's merge), plants a symlink to /dev/zero in the clone, as a leg can through its
        checkout's alternates: at refs/tags/<tip>, a name git's rules make of the tip's id, or at each of BATCH_SHADOWS,
        the names they try for batch/b1 before refs/heads/batch/b1; each case in a fixture of its own. bisect, run under
        PLANT_CAP, names #101, exits 0 with nothing on stderr, and leaves the worktree on batch/b1 at the tip with no
        bisect in progress. The bisect runs with --no-checkout from HEAD detached at the tip, so git bisect start records
        the tip's id rather than the short name, and the cleanup restores the branch's tree, ends the bisect with a
        plain git bisect reset, which checks nothing out while BISECT_HEAD exists, and points HEAD at the branch; the
        driver's log shows that git bisect reset with no argument, so it names no commit for git to look up. Red for
        the tip's id under git 2.43.0 at the head before this change, where the cleanup's git bisect reset <tip> looked
        the id up by git's rev-parse rules and stopped at the memory limit: git 2.43.0's git bisect looks a full id up
        that way whatever core.warnAmbiguousRefs says, and batch.py turns that setting off on every call (QUIET_NAMES).
        git 2.55.0's git bisect reads the setting and then looks a full id up as no ref name (without the setting it
        reads the symlink there too). So with the cleanup's git bisect reset given the tip's id (the mutant mResetTip),
        under git 2.55.0 the exit, the output and the worktree's state are as they are without it, and the assertion
        on the driver's log is what is red: under the mutant both subtests are red under both gits, on that assertion,
        but for the tip's id under git 2.43.0, which is red first on its exit, at the memory limit (the verify pass at
        round 3's build, its v-2; measured 2026-10-04). Red for the short name at the head before the ruling, where the
        cleanup's git checkout --force batch/b1 read the first of them, which git 2.55.0 reads as well."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        self.maxDiff = None
        for n, case in enumerate(("the tip's id", "the branch's short name")):
            with self.subTest(plant=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                tip, merge_101 = self.bisect_chain()
                wt = fx.wt("b1")
                names = ["refs/tags/" + tip] if case == "the tip's id" else list(BATCH_SHADOWS)
                paths = [os.path.join(fx.dev, ".git", *name.split("/")) for name in names]
                for path in paths:
                    self.addCleanup(lambda p=path: os.path.lexists(p) and os.remove(p))
                plant = "".join("mkdir -p '%s' && ln -s /dev/zero '%s' && " % (os.path.dirname(p), p) for p in paths)
                rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c", self.BISECT_CMD % (plant + "exit 1"),
                                            cap=PLANT_CAP)
                self.assertTrue(all(os.path.islink(p) for p in paths), "premise: the command planted each symlink")
                self.assertEqual((rc, err), (0, ""), out + err)
                self.assertEqual(out, "first bad: #101 kernel: bump the version (merge %s); pull it and say why in the "
                                      "body\n" % merge_101[:10])
                self.assertFalse(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1",
                                                             "BISECT_START")), "bisect is reset")
                self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), tip, "HEAD is at the tip")
                # a plain symbolic-ref, which prints HEAD's target and reads no other name (rev-parse --abbrev-ref would
                # try the names the symlinks are at)
                self.assertEqual(fx._git("symbolic-ref", "HEAD", cwd=wt), "refs/heads/batch/b1",
                                 "the worktree is on the branch")
                # the driver's log: git 2.55.0 honours QUIET_NAMES for a full id, so on CI's git the plant at
                # refs/tags/<tip> alone cannot see a cleanup that names the tip
                self.assertEqual([c[3] for c in self.calls if c[3].split()[:2] == ["bisect", "reset"]], ["bisect reset"],
                                 "the cleanup ends the bisect with one git bisect reset that names no commit")

    def test_a_refused_restore_after_the_steps_fails_bisect_with_its_answer_and_leaves_head_detached(self):
        """The verify pass at this pass's build, its F6 and F5's first part: when the cleanup after the steps cannot put
        the branch's tree back, bisect fails (exit 1) rather than reporting success over a worktree left off the
        branch, and still gives its answer. The worktree has a change to notes.txt before bisect, so the cleanup is
        unforced, and the command appends to postal/postal_service.py at the one commit bisect tests (#101's merge),
        a file that commit and the tip hold differently: the cleanup's two-way merge refuses in git read-tree's words.
        bisect prints its first-bad line for #101, then fails naming the refusal, the commit HEAD is left detached at
        and the bisect still in progress, which is what it leaves: HEAD detached at #101's merge, nothing staged
        (the move of HEAD to the branch never ran over that commit's tree), and BISECT_START still there. Red at the
        head before this change (exit 0, nothing on stderr: git bisect reset <tip> was refused and the refusal
        ignored); red when the restore's refusal is ignored and HEAD is pointed at the branch anyway (the mutant
        mRestoreUnchecked: bisect exits 0, HEAD on batch/b1 over #101's tree)."""
        self.maxDiff = None
        fx = self.fx
        tip, merge_101 = self.bisect_chain()
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "a") as f:
            f.write("a change the cleanup keeps\n")
        rc, out, err = self.bisect_with("echo '# mid' >> postal/postal_service.py; exit 1")
        self.assertEqual((rc, out), (1, "first bad: #101 kernel: bump the version (merge %s); pull it and say why in the "
                                        "body\n" % merge_101[:10]), out + err)
        self.assertIn("batch: bisect named the first bad commit, %s (printed above), but its cleanup did not finish: "
                      % merge_101[:10], err)
        self.assertIn("error: Entry 'postal/postal_service.py' not uptodate. Cannot merge.", err)
        self.assertIn("The batch worktree %s is left detached at %s, with the bisect in progress." % (wt, merge_101[:10]),
                      err)
        self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "BISECT_START")),
                        "the bisect is still in progress, as the message says")
        self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=wt, check=False), "", "HEAD is detached")
        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), merge_101, "HEAD is at #101's merge")
        self.assertEqual(fx._git("diff", "--cached", "--name-only", cwd=wt), "", "nothing staged")
        self.assertEqual(fx._git("diff", "--name-only", cwd=wt).splitlines(), ["notes.txt", "postal/postal_service.py"],
                         "both changes kept in the files")

    def test_a_bisect_stopped_before_its_answer_names_why_first_when_the_cleanup_then_fails(self):
        """Round 3 of PR 959, correctness-2: when bisect stops before it names a first bad commit (a step's command exits
        128 or more, or a stop signal arrives) and the cleanup's restore of the branch's tree then fails, bisect says
        first why it stopped, then the cleanup's error, the state the batch worktree is left in and the commands that put
        it back (bisect_unfinished, bisect_cleanup_failed); a stop exits 128 plus the signal's number and says the
        cleanup did not finish, where it says the cleanup ran when it did. The worktree has a change to notes.txt before
        bisect, so each cleanup is unforced, and the command appends to postal/postal_service.py, a file the base,
        #101's merge and the tip hold differently, so the restore's two-way merge refuses in git read-tree's words. Each
        case in a fixture of its own: at the one commit bisect tests (#101's merge) the command exits 139 (exit 1:
        "bisect stopped at <commit>: the command exited 139", then "Then bisect's cleanup did not finish: <read-tree's
        error>", HEAD left detached there with the bisect in progress, and the remedy's git bisect reset), or sends
        SIGTERM to batch.py (exit 143: the signal, then the same error and state); and in the run at the base the command
        sends SIGTERM to batch.py (exit 143, HEAD left detached at the base with no bisect in progress, and a remedy with
        no git bisect reset, since none was started), or exits 1, or exits 139 (exit 1 for both: "the command fails at
        the base <base> (<remote main>) too", then the same error, state and remedy). Red at the round's head: each
        printed read-tree's error alone, "batch: git read-tree -m -u HEAD refs/heads/batch/b1 failed (128): ...", with
        no reason before it, and exited 1; at the step that is a regression of round 2, whose cleanup after the steps
        ignored the refused move and printed the reason (exit 1 for the 139, 143 for the stop), and at the base the same
        masking predates round 2. The two cases of a command that fails at the base are the verify pass at round 3's
        build, its v-1: red at that build's head, where the reason was raised only after the cleanup had finished, so
        the cleanup's Fail replaced it and bisect printed read-tree's error alone (git 2.43.0 and git 2.55.0,
        2026-10-04)."""
        self.maxDiff = None
        at_the_base = ("if grep -q 'return 2' postal/postal_service.py; then exit 1; fi; "
                       "echo '# base' >> postal/postal_service.py; %s")
        cases = (("a step's command exits 139", "echo '# mid' >> postal/postal_service.py; exit 139"),
                 ("a stop at a step", "echo '# mid' >> postal/postal_service.py; kill -TERM $PPID; sleep 30"),
                 ("a stop in the run at the base", at_the_base % "kill -TERM $PPID; sleep 30"),
                 ("the command exits 1 at the base", at_the_base % "exit 1"),
                 ("the command exits 139 at the base", at_the_base % "exit 139"))
        refused = ("git read-tree -m -u HEAD refs/heads/batch/b1 failed (128):\n"
                   "error: Entry 'postal/postal_service.py' not uptodate. Cannot merge.\n")
        for n, (case, middle) in enumerate(cases):
            with self.subTest(case=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                tip, merge_101 = self.bisect_chain()
                wt = fx.wt("b1")
                base = fx._git("merge-base", ORIGIN_MAIN_REF, tip, cwd=wt)
                with open(os.path.join(wt, "notes.txt"), "a") as f:
                    f.write("a change the cleanup keeps\n")
                bisecting = not case.endswith("at the base")
                if bisecting:
                    rc, out, err = self.bisect_with(middle)
                else:
                    rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c", middle)
                at = merge_101 if bisecting else base
                self.assertEqual(out, "", "no first bad commit is named")
                self.assertNotIn("its cleanup ran", err)
                if case == "a step's command exits 139":
                    self.assertEqual(rc, 1, err)
                    first = ("batch: bisect stopped at %s: the command exited 139, and git bisect run stops on an exit "
                             "of 128 or more, or a signal\nThen bisect's cleanup did not finish: " % merge_101[:10])
                elif case.startswith("the command exits"):
                    self.assertEqual(rc, 1, err)
                    first = ("batch: the command fails at the base %s (%s) too; no member made it fail. Check the "
                             "command and the environment before blaming a member\nThen bisect's cleanup did not "
                             "finish: " % (base[:10], batch.remote_main()))
                else:
                    self.assertEqual(rc, 128 + signal.SIGTERM, err)
                    first = ("batch: stopped by signal %d; any process it was waiting on was killed, but its cleanup "
                             "did not finish: " % signal.SIGTERM)
                state = "The batch worktree %s is left detached at %s, with %s." % (
                    wt, at[:10], "the bisect in progress" if bisecting else "no bisect in progress")
                steps = ["`git -C %s checkout --detach refs/heads/batch/b1`" % wt]
                if bisecting:
                    steps.append("`git -C %s bisect reset`" % wt)
                remedy = ("To put it back on batch/b1 at the tip, commit or discard any change git names above, then "
                          "run %s and `git -C %s symbolic-ref HEAD refs/heads/batch/b1`." % (", ".join(steps), wt))
                self.assertEqual(err, first + refused + state + " " + remedy + "\n")
                self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=wt, check=False), "", "HEAD is detached")
                self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), at)
                self.assertEqual(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1",
                                                             "BISECT_START")), bisecting, "the bisect state, as said")

    def other_worktree_on_the_branch(self):
        """A second worktree of the fixture's clone, on batch/b1, after the batch worktree is detached at the tip (git
        keeps a branch in one worktree at a time): its path."""
        fx = self.fx
        fx._git("checkout", "--quiet", "--detach", cwd=fx.wt("b1"))
        other = os.path.join(fx.tmp, "other-b1")
        fx.dev_git("worktree", "add", "--quiet", other, "batch/b1")
        return other

    def on_the_batch_branch(self):
        """How many worktrees of the fixture's clone git lists on refs/heads/batch/b1."""
        listing = self.fx.dev_git("worktree", "list", "--porcelain")
        return listing.splitlines().count("branch refs/heads/batch/b1")

    def test_bisect_refuses_a_batch_branch_another_worktree_holds_and_moves_nothing(self):
        """The verify pass at the build of the 22:25Z ruling of 2026-10-03 on PR 959, its F4: bisect's cleanups point HEAD
        at the batch branch with git symbolic-ref, which skips the rule git checkout applies first, that a branch is in
        one worktree at a time, so bisect applies it (held_elsewhere). With the batch worktree detached at the tip and
        batch/b1 held by another worktree, which is on it, or is detached mid-bisect started from it, or is detached
        mid-rebase of it (an interactive rebase whose todo is a single break, its rebase-merge/head-name reading
        refs/heads/batch/b1), or is the clone's main worktree detached mid-bisect started from it (each case in a
        fixture of its own), bisect refuses (exit 1) before it runs the command, naming that worktree, and moves
        nothing: the batch worktree stays detached at the tip and the other as it was. Red without the check (the head
        before it: exit 0, the batch worktree put on batch/b1 beside the other); red with the check only at the move
        of HEAD (the mutant mNoStartCheck: the refusal comes after the command ran, at the first cleanup, with the batch
        worktree left detached at the base). Red in the rebasing case without the rules for a rebase in _started_from,
        or with names() reading head-name without removing its leading refs/heads/ (exit 0, bisect names #101); red in
        the main worktree's case with the main worktree's git dir looked up as a linked one's (held_elsewhere's `if i:`
        always true: exit 0)."""
        for n, case in enumerate(("on the branch", "bisecting from the branch", "rebasing the branch",
                                  "main worktree bisecting from the branch")):
            with self.subTest(other=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                tip, _merge_101 = self.bisect_chain()
                wt = fx.wt("b1")
                if case == "main worktree bisecting from the branch":
                    fx._git("checkout", "--quiet", "--detach", cwd=wt)
                    fx.dev_git("checkout", "--quiet", "batch/b1")
                    other = fx.dev
                else:
                    other = self.other_worktree_on_the_branch()
                if case in ("bisecting from the branch", "main worktree bisecting from the branch"):
                    fx._git("bisect", "start", "--first-parent", tip, fx.dev_git("merge-base", ORIGIN_MAIN_REF, tip),
                            cwd=other)
                    self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=other, check=False), "",
                                     "premise: the other worktree is detached mid-bisect")
                if case == "main worktree bisecting from the branch":
                    with open(os.path.join(fx.dev, ".git", "BISECT_START")) as f:
                        self.assertEqual(f.read(), "batch/b1\n", "premise: the main worktree bisects from batch/b1")
                if case == "rebasing the branch":
                    p = subprocess.run(["git", "rebase", "-i", "HEAD"], cwd=other, text=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       env=dict(fx.env, GIT_SEQUENCE_EDITOR="sh -c 'echo break > \"$1\"' -"))
                    self.assertEqual(p.returncode, 0, p)
                    self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=other, check=False), "",
                                     "premise: the other worktree is detached mid-rebase")
                    with open(os.path.join(fx.dev, ".git", "worktrees", "other-b1", "rebase-merge", "head-name")) as f:
                        self.assertEqual(f.read(), "refs/heads/batch/b1\n", "premise: it rebases refs/heads/batch/b1")
                rc, out, err = self.bisect_with("exit 1")
                self.assertEqual((rc, out), (1, ""), out + err)
                head = "batch: batch/b1 is checked out in another worktree at "
                self.assertTrue(err.startswith(head), err)
                named = err[len(head):].split(";", 1)[0]
                self.assertTrue(os.path.samefile(named, other), "the refusal names the other worktree: %s" % err)
                self.assertTrue(err.endswith("; git allows a branch in one worktree at a time. Take it off that worktree "
                                             "(git checkout --detach there, or end its bisect or rebase), then run bisect "
                                             "again.\n"), err)
                self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=wt, check=False), "",
                                 "the batch worktree is still detached")
                self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), tip, "the batch worktree is still at the tip")
                if case == "on the branch":
                    self.assertEqual(self.on_the_batch_branch(), 1, "only the other worktree is on batch/b1")
                else:
                    self.assertEqual(self.on_the_batch_branch(), 0, "no worktree is on batch/b1")
                    still = {"bisecting from the branch": ("worktrees", "other-b1", "BISECT_START"),
                             "rebasing the branch": ("worktrees", "other-b1", "rebase-merge", "head-name"),
                             "main worktree bisecting from the branch": ("BISECT_START",)}[case]
                    self.assertTrue(os.path.exists(os.path.join(fx.dev, ".git", *still)),
                                    "the other worktree still bisects or rebases")

    def test_a_worktree_that_takes_the_batch_branch_while_bisects_command_runs_stops_the_move_of_head(self):
        """The verify pass at the build of the 22:25Z ruling of 2026-10-03 on PR 959, its F4, at the move of HEAD: the
        command, in its run at the base, puts another worktree on batch/b1 (git allows it, the batch worktree being
        detached then). The first cleanup restores the branch's tree and then, before it points HEAD at the branch,
        finds the branch held (held_elsewhere): bisect fails (exit 1) naming that worktree, and the batch worktree is
        left detached at the base with the branch's tree, as the message says, while only the other is on batch/b1.
        Red without the check at the move (the mutant mNoAttachCheck: exit 0, both worktrees on batch/b1)."""
        fx = self.fx
        tip, _merge_101 = self.bisect_chain()
        wt = fx.wt("b1")
        base = fx.dev_git("merge-base", ORIGIN_MAIN_REF, tip)
        other = os.path.join(fx.tmp, "other-b1")
        rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c",
                                    "if grep -q 'return 2' postal/postal_service.py; then exit 1; fi; "
                                    "if grep -q 'VERSION = 1' kernel/kernel.py; then "
                                    "git -C '%s' worktree add --quiet '%s' batch/b1; fi; exit 0" % (fx.dev, other))
        self.assertEqual((rc, out), (1, ""), out + err)
        head = "batch: batch/b1 is checked out in another worktree at "
        self.assertTrue(err.startswith(head), err)
        self.assertTrue(os.path.samefile(err[len(head):].split(";", 1)[0], other), err)
        self.assertIn("; git allows a branch in one worktree at a time, so %s is left detached at %s, with the branch's "
                      "tree. Take the branch off that worktree (git checkout --detach there, or end its bisect or "
                      "rebase), then run `git -C %s symbolic-ref HEAD refs/heads/batch/b1`.\n" % (wt, base[:10], wt), err)
        self.assertEqual(fx._git("symbolic-ref", "-q", "HEAD", cwd=wt, check=False), "", "the batch worktree is detached")
        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), base, "at the base")
        self.assertEqual(fx._git("diff", "--cached", "--name-only", tip, cwd=wt), "", "with the branch's tree")
        self.assertEqual(self.on_the_batch_branch(), 1, "only the other worktree is on batch/b1")
        self.assertEqual(fx._git("symbolic-ref", "HEAD", cwd=other), "refs/heads/batch/b1")

    def test_bisects_unforced_restore_refreshes_the_index_before_its_two_way_merge(self):
        """restore_branch_tree's unforced restore refreshes the index (git update-index -q --refresh) before its two-way
        merge, as git checkout does, so a file whose content is the same but whose stat data changed is not read as a
        change. The worktree has a change to notes.txt before bisect, so the cleanups are unforced, and the command, at
        the base (VERSION = 1), sets kernel/kernel.py's mtime to a fixed past time with touch -t, the form GNU's and
        Apple's touch both take (Apple's -d takes a date only with a time of day, so it refuses -d 2001-01-01; the
        closing check at round 3 of PR 959, N4, and chk-r3e-4), since a plain touch in the second of the checkout could
        go unseen, git comparing the mtime to the second, on a file the base and the tip hold differently: bisect names
        #102, the worktree is on batch/b1 at the tip with no bisect in progress, and notes.txt keeps its change. Red
        without the refresh (the mutant mNoRefresh): the first cleanup's git read-tree -m -u refuses with "Entry
        'kernel/kernel.py' not uptodate. Cannot merge." and bisect exits 1."""
        fx = self.fx
        tip, _merge_101 = self.bisect_chain()
        notes = os.path.join(fx.wt("b1"), "notes.txt")
        with open(notes, "a") as f:
            f.write("a change the cleanups keep\n")
        with open(notes) as f:
            text = f.read()
        rc, out, err = self.bounded("bisect", "b1", "--", "sh", "-c",
                                    "if grep -q 'return 2' postal/postal_service.py; then exit 1; fi; "
                                    "if grep -q 'VERSION = 1' kernel/kernel.py; then "
                                    "touch -t 200101010000 kernel/kernel.py; "
                                    "fi; exit 0")
        self.assertEqual((rc, err), (0, ""), out + err)
        self.assertIn("first bad: #102 ", out)
        self.assert_reset_at_the_tip(tip)
        with open(notes) as f:
            self.assertEqual(f.read(), text, "the worktree's notes.txt keeps its change")

    def test_assembles_branch_reset_reads_the_branchs_short_name_and_stops_at_the_memory_limit(self):
        """The witness of the reads of the batch branch by its short name left after the 22:25Z ruling of 2026-10-03 on
        PR 959, item 1 (scripts/batch.py's module docstring and docs/batching.md name this test), and of what their
        GitMemory names (round 2 of PR 959, ruling D, fresh-2): assemble makes the branch at MAIN_REF with git worktree
        add -B batch/<name> when the batch worktree is not there, and resets it with git checkout -B batch/<name>
        MAIN_REF when it reuses the worktree, and each looks the branch's short name up by git's rules once it has set
        the branch, opening each of BATCH_SHADOWS, under the common dir, before refs/heads/batch/<name>; git checkout -B
        first looks its start point up as a local branch, START_AS_A_BRANCH (git 2.43.0, traced on 2026-10-04). So a
        symlink to /dev/zero at any one of those files, planted alone, each case in a fixture of its own, makes that call
        meet the memory limit (PLANT_MEMORY on it, BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX unset), the call holding no more
        than the limit, and assemble stops (exit 1) with a GitMemory naming the call and that file, as a symlink, and no
        other file. Red at the round's head, whose GitMemory named the files of the call's two full refs, regular files,
        and not the one planted; red at the build head before fresh-2 for each plant at <common dir>/batch/b1, which is
        outside refs/, so ruling C's walk of refs/ did not name it and the GitMemory named no file. Red too once either
        call names the branch otherwise: then this witness, and the texts that cite it, are to change."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        cases = ([("a fresh worktree", name) for name in BATCH_SHADOWS]
                 + [("the worktree reused", name) for name in BATCH_SHADOWS + (START_AS_A_BRANCH,)])
        for n, (case, name) in enumerate(cases):
            with self.subTest(case=case, planted=name):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                if case == "a fresh worktree":
                    fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
                    fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
                    fx.ok("plan", "--name", "b1")
                    self.assertFalse(os.path.isdir(fx.wt("b1")), "premise: no batch worktree yet")
                    call, where = "worktree add --quiet -B batch/b1 %s %s" % (fx.wt("b1"), ORIGIN_MAIN_REF), fx.dev
                else:
                    self.assembled()
                    self.assertTrue(os.path.isdir(fx.wt("b1")), "premise: the batch worktree is there to reuse")
                    call, where = "checkout --quiet -B batch/b1 %s" % ORIGIN_MAIN_REF, fx.wt("b1")
                planted = os.path.join(fx.dev, ".git", *name.split("/"))
                os.makedirs(os.path.dirname(planted), exist_ok=True)
                os.symlink("/dev/zero", planted)
                self.addCleanup(lambda p=planted: os.path.lexists(p) and os.remove(p))
                env = dict(fx.env)
                env.pop("MALLOC_ARENA_MAX", None)
                rc, out, err = self.bounded("assemble", "b1", "--no-fetch", env=env, cap=PLANT_CAP, bound=60,
                                            planted=[call], memory=PLANT_MEMORY)
                self.assertEqual(rc, 1, out + err)
                self.assertIn("batch: git %s in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and "
                              "failed (fatal: Out of memory, " % (call, where, PLANT_MEMORY >> 20), err)
                ended = [c for c in self.calls if c[3] == call]
                self.assertEqual([c[1] for c in ended], ["memory"], "the call ended at the memory limit")
                self.assertLessEqual(int(ended[0][2]), PLANT_MEMORY, "the call held more than its limit: %s" % ended)
                self.assertIn(REMEDY_PLACES + "; of the files of the repository git reads "
                              "whole, these are not regular files or hold more than a file of their kind does, now (an "
                              "lstat each after the call, so one can have changed since): %s (a symlink, not a regular "
                              "file), and run the command again" % planted, err, "the planted file is named, and no other")

    def test_a_git_memory_from_the_listing_of_the_remote_batch_branches_names_their_directory_as_one(self):
        """Round 2 of PR 959, ruling D, extra4-3: pick_name (plan with no --name) and other_remote_batches (assemble) list
        the remote batch branches with git for-each-ref over the prefix refs/remotes/origin/batch/, which is not a ref
        but the directory whose loose refs the call reads, so a GitMemory from that call names it as a directory, "the
        loose refs under <dir>/", beside the planted file _odd_files names. Here a sparse file of PLANT_SPARSE bytes is
        planted at refs/remotes/origin/batch/planted once b1 is planned, and plan --no-fetch and assemble b1 --no-fetch
        each run with that call under PLANT_MEMORY (BATCH_BOUND_DRIVER), MALLOC_ARENA_MAX unset: each stops (exit 1) at
        the call, at the limit, naming the directory so and the planted file. Red at the round's head, whose text read
        "the call reads <dir>", the directory without its trailing separator, as if it were a ref's file (and named no
        planted file); red at the build head before this change, which named the planted file and not the directory."""
        if not sys.platform.startswith("linux"):
            self.skipTest("batch.py sets the memory limit on Linux alone")
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        listed = os.path.join(fx.dev, ".git", "refs", "remotes", "origin", "batch") + os.sep
        planted = os.path.join(listed, "planted")
        os.makedirs(listed, exist_ok=True)
        with open(planted, "w") as f:
            f.truncate(PLANT_SPARSE)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        call = "for-each-ref --format=%(refname:short) refs/remotes/origin/batch/"
        for reader, args in (("pick_name", ("plan", "--no-fetch")), ("other_remote_batches", ("assemble", "b1", "--no-fetch"))):
            with self.subTest(reader=reader):
                rc, out, err = self.bounded(*args, env=env, cap=PLANT_CAP, bound=60, planted=[call], memory=PLANT_MEMORY)
                self.assertEqual(rc, 1, out + err)
                self.assertIn("batch: git %s in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and "
                              "failed (fatal: Out of memory, " % (call, fx.dev, PLANT_MEMORY >> 20), err)
                self.assertIn(REMEDY_PLACES + "; the call reads the loose refs under %s; of "
                              "the files of the repository git reads whole, these are not regular files or hold more than "
                              "a file of their kind does, now (an lstat each after the call, so one can have changed "
                              "since): %s (%d bytes, more than the 4096 a loose ref file holds), and run the command again"
                              % (listed, planted, PLANT_SPARSE), err)
                ended = [c for c in self.calls if c[3] == call]
                self.assertEqual([c[1] for c in ended], ["memory"], "the listing ended at the memory limit")
                self.assertFalse(os.path.isdir(fx.wt("b1")), "assemble stopped before the batch worktree was made")

    def test_the_listing_of_the_remote_batch_branches_opens_the_names_of_each_ones_short_name(self):
        """The witness of the third kind of read that reaches a name git's rev-parse rules make (scripts/batch.py's
        module docstring and docs/batching.md name this test): pick_name and other_remote_batches list the remote batch
        branches with git for-each-ref --format=%(refname:short), which shortens each refs/remotes/origin/batch/<x> to
        origin/batch/<x> and, to tell whether that short name is ambiguous, opens each name the rules try for it before
        refs/remotes/ (REV_PARSE_RULES up to refs/heads/), under the common dir, with core.warnAmbiguousRefs off as
        every call of batch.py runs (git 2.43.0, 2026-10-04). Here origin/batch/other is a remote batch branch, and a
        symlink to /dev/zero at one of those names at a time, planted after every git call of the case's own, makes
        plan --no-fetch's listing meet the memory limit (PLANT_MEMORY on it, BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX unset):
        plan stops (exit 1) with a GitMemory naming the call and the directory it lists; it names the planted file for
        the three names under refs/ (_odd_files' walk), and no file for <common dir>/origin/batch/other, which is
        outside refs/, as the texts say. Red once the listing reads the branches by their full names (then it opens none
        of these, and this witness and the texts that cite it are to change), or once the GitMemory names the file
        outside refs/ (the last case, then to be turned around)."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        remote = "refs/remotes/origin/batch/other"
        fx.dev_git("update-ref", remote, fx.dev_git("rev-parse", ORIGIN_MAIN_REF))
        listed = os.path.join(fx.dev, ".git", "refs", "remotes", "origin", "batch") + os.sep
        call = "for-each-ref --format=%(refname:short) refs/remotes/origin/batch/"
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        names = tuple(rule % "origin/batch/other" for rule in REV_PARSE_RULES[:REV_PARSE_RULES.index("refs/remotes/%s")])
        self.assertEqual(len(names), 4, "premise: the four names the rules try before refs/remotes/")
        for name in names:
            with self.subTest(planted=name):
                planted = os.path.join(fx.dev, ".git", *name.split("/"))
                os.makedirs(os.path.dirname(planted), exist_ok=True)
                os.symlink("/dev/zero", planted)
                try:
                    rc, out, err = self.bounded("plan", "--no-fetch", env=env, cap=PLANT_CAP, bound=60, planted=[call],
                                                memory=PLANT_MEMORY)
                finally:
                    os.remove(planted)
                self.assertEqual(rc, 1, out + err)
                self.assertIn("batch: git %s in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and "
                              "failed (fatal: Out of memory, " % (call, fx.dev, PLANT_MEMORY >> 20), err)
                ended = [c for c in self.calls if c[3] == call]
                self.assertEqual([c[1] for c in ended], ["memory"], "the listing ended at the memory limit")
                odd = ("; of the files of the repository git reads whole, these are not regular files or hold more than "
                       "a file of their kind does, now (an lstat each after the call, so one can have changed since): %s "
                       "(a symlink, not a regular file)" % planted) if name.startswith("refs/") else ""
                self.assertIn(REMEDY_PLACES + "; the call reads the loose refs under %s%s, and "
                              "run the command again" % (listed, odd), err)

    def test_assembles_merges_under_merge_log_read_no_name_the_merged_commits_id_would_open(self):
        """Round 2 of PR 959, ruling D, fresh-3: with merge.log set (here in the clone's config), git merge appends a
        shortlog of the merged commits to the message even under -m, and to describe the commit it merges it looks the
        full id up as a ref name under every rule, whatever core.warnAmbiguousRefs says, so a symlink to /dev/zero at
        refs/tags/<id>, which a leg can leave through its checkout's alternates, was read until the call's limit.
        assemble's merge of a member and merge_main's merge pass --no-log. Here, each case in a fixture of its own, with
        merge.log=true, a symlink to /dev/zero at refs/tags/<id> of the commit the merge takes in (#101's head; origin's
        main once it moved), planted after every git call of the case's own, and every merge under HOOK_MEMORY lowered to
        PLANT_HOOK_MEMORY (BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX unset, so no call has a real 16 GiB): assemble, and
        assemble --merge-main, exit 0 with the merge on the chain, its message the subject alone (the shortlog merge.log
        would add is dropped; batch.py reads only the subject), and the symlink still there. Red without the flag: the
        merge read the symlink and met its limit, and assemble stopped (exit 1) with GitMemory naming it, at the build
        head before this change and under the flag removed from either merge alone (PLANT_HOOK_MEMORY, in that merge's
        case only), and at the round's head, where a merge ran under GIT_MEMORY (1024 MiB)."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        for n, case in enumerate(("a member's merge", "the merge of origin's main")):
            with self.subTest(case=case):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
                fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
                fx.ok("plan", "--name", "b1")
                if case == "a member's merge":
                    taken, args = fx.state("b1")["members"]["101"]["head"], ("assemble", "b1", "--no-fetch")
                    subject, chain = "Merge #101: notes: a fourth line", ["Merge #101: notes: a fourth line"]
                else:
                    fx.ok("assemble", "b1")
                    fx.commit_main({"README.md": "# notes-api\n\nmain moved\n"}, "main moved")
                    fx.dev_git("fetch", "-q", "origin")
                    taken, args = fx.dev_git("rev-parse", ORIGIN_MAIN_REF), ("assemble", "b1", "--merge-main", "--no-fetch")
                    subject = "Merge origin/main into batch/b1"
                    chain = ["Merge #101: notes: a fourth line", subject]
                fx.dev_git("config", "merge.log", "true")
                planted = os.path.join(fx.dev, ".git", "refs", "tags", taken)
                os.makedirs(os.path.dirname(planted), exist_ok=True)
                os.symlink("/dev/zero", planted)
                self.addCleanup(lambda p=planted: os.path.lexists(p) and os.remove(p))
                env = dict(fx.env)
                env.pop("MALLOC_ARENA_MAX", None)
                rc, out, err = self.bounded(*args, env=env, cap=PLANT_CAP, bound=60, hook_memory=PLANT_HOOK_MEMORY)
                self.assertEqual(rc, 0, out + err)
                self.assertEqual(fx.chain("b1"), chain)
                self.assertEqual(fx.dev_git("log", "-1", "--format=%B", "refs/heads/batch/b1"), subject,
                                 "the merge's message is the subject alone")
                self.assertTrue(os.path.islink(planted), "the symlink is still there")

    def test_a_sparse_loose_ref_planted_before_a_no_fetch_push_path_is_refused_by_the_listing_at_git_memory(self):
        """Round 2 of PR 959, ruling C, items 2 and 4: a push reads every loose ref of the clone whole as it lists the
        local refs, under HOOK_MEMORY, and on a path with no fetch before it (--no-fetch) no call under GIT_MEMORY had
        read them first, so a sparse file a leg planted at a loose ref held the push near HOOK_MEMORY before it failed.
        Each call that runs the clone's hooks now comes after a listing of the refs under GIT_MEMORY (_refs_listed).
        Here a sparse file of PLANT_SPARSE bytes is planted at refs/tags/planted once the batch is assembled and pushed,
        and pull --no-fetch rebuilds the batch (a merge, then the push) with GIT_MEMORY lowered to PLANT_MEMORY and
        HOOK_MEMORY to PLANT_HOOK_MEMORY (BATCH_BOUND_DRIVER), MALLOC_ARENA_MAX unset: pull stops (exit 1) at the
        listing before the first such call, the merge, at GIT_MEMORY, naming the planted file; the merge made no commit
        and nothing was pushed. This is the named witness of the residual the listing leaves (_refs_listed and
        GIT_SETTINGS' comment): a file planted after the listing, or one the call reads and the listing does not, fails
        at HOOK_MEMORY. Red without the listing: the merge, which reads no loose ref it does not name, ran, and the
        push met PLANT_HOOK_MEMORY reading the planted file ("git push --quiet --force-with-lease -u origin
        refs/heads/batch/b1 ... reached the 384 MiB memory limit (HOOK_MEMORY)", naming it); and at the round's head,
        where the push had PUSH_MEMORY, 16 GiB, the push read the whole file and pull exited 0."""
        if not sys.platform.startswith("linux"):
            self.skipTest("batch.py sets the memory limit on Linux alone")
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        pushed = fx.bare_rev("batch/b1")
        planted = os.path.join(fx.dev, ".git", "refs", "tags", "planted")
        os.makedirs(os.path.dirname(planted), exist_ok=True)
        with open(planted, "w") as f:
            f.truncate(PLANT_SPARSE)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        rc, out, err = self.bounded("pull", "b1", "102", "--no-fetch", "--reason", "the maintainer asked", env=env,
                                    bound=60, git_memory=PLANT_MEMORY, hook_memory=PLANT_HOOK_MEMORY)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("batch: batch.py lists the refs under GIT_MEMORY before git merge -s ort --no-ff --no-edit --no-log "
                      "-m Merge #101: kernel: bump the version %s, which runs the clone's hooks under HOOK_MEMORY: git "
                      "for-each-ref "
                      "--format= in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and failed (fatal: "
                      "Out of memory, " % (fx.bare_rev("a"), fx.wt("b1"), PLANT_MEMORY >> 20), err)
        self.assertIn("(an lstat each after the call, so one can have changed since): %s (%d bytes, more than the 4096 a "
                      "loose ref file holds), and run the command again" % (planted, PLANT_SPARSE), err)
        self.assertEqual(fx.chain("b1"), [], "the merge made no commit")
        self.assertEqual(fx.bare_rev("batch/b1"), pushed, "nothing was pushed")

    def test_a_hook_that_reserves_more_than_git_memory_runs_under_hook_memory_at_a_push_a_commit_and_a_merge(self):
        """Round 2 of PR 959, ruling C, item 1: every call that runs the clone's hooks, a push, a commit and a merge, gets
        HOOK_MEMORY, not a push alone: a pre-commit hook a user sets for every clone can start gitleaks, which reserves
        more than 4 GiB as it starts, and under GIT_MEMORY assemble --continue's git commit failed through it. Here the
        hook reserves HOOK_RESERVE bytes of address space itself (RESERVING_HOOK, one anonymous map, never touched; no
        gitleaks), more than the GIT_MEMORY the case sets and less than its HOOK_MEMORY (HOOK_PIN_GIT_MEMORY and
        HOOK_PIN_HOOK_MEMORY, through BATCH_BOUND_DRIVER, so no call has a real 16 GiB), and records the limit it ran
        under: pre-push at pull's push of the rebuilt branch, pre-commit at assemble --continue's commit of a hand
        resolution, and pre-merge-commit at assemble's merge of a member, each case in a fixture of its own. Each
        command exits 0 with the batch's merges in place (and the pull's push on the remote), and the hook ran once,
        under HOOK_PIN_HOOK_MEMORY, and reserved its bytes. Red at the round's head, where only a push had the larger
        limit: the commit ran under GIT_MEMORY, where the hook could not reserve and git refused the commit (assemble
        exit 1); the merge too, its hook recording GIT_MEMORY and the failed reservation (git left the merge
        uncommitted, and assemble, which then read a merge a hook refused as one rerere had replayed, committed it with
        git commit; a defect since fixed, so a refused merge now fails the command:
        test_a_merge_the_pre_merge_commit_hook_refuses_fails_the_command_and_is_not_committed); and the push, under
        PUSH_MEMORY, recorded 16 GiB, not the case's HOOK_MEMORY (red there by its limit's figure alone; a predicate
        that leaves the push out turns it red as the commit is)."""
        if not sys.platform.startswith("linux"):
            self.skipTest("batch.py sets the memory limit on Linux alone")
        for n, hook in enumerate(("pre-push", "pre-commit", "pre-merge-commit")):
            with self.subTest(hook=hook):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                if hook == "pre-push":
                    self.two_members()
                    fx.ok("plan", "--name", "b1")
                    fx.ok("assemble", "b1")
                    fx.push_batch("b1")
                    args = ("pull", "b1", "102", "--reason", "the maintainer asked")
                    chain = ["Merge #101: kernel: bump the version"]
                elif hook == "pre-commit":
                    fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
                    fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
                    fx.pr(101, "a", labels=["fix"], body=TRAILER)
                    fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
                    fx.ok("plan", "--name", "b1")
                    p = fx.run("assemble", "b1", "--resolve", "108")
                    self.assertEqual(p.returncode, 3, "premise: the merge of #108 stops for a hand resolution\n%s%s"
                                     % (p.stdout, p.stderr))
                    with open(os.path.join(fx.wt("b1"), "notes.txt"), "w") as f:
                        f.write("one\ntwo-a-g\nthree\n")
                    fx._git("add", "notes.txt", cwd=fx.wt("b1"))
                    args = ("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
                    chain = ["Merge #101: PR 101 on a", "Merge #108: notes: the g version"]
                else:
                    fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
                    fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
                    fx.ok("plan", "--name", "b1")
                    args = ("assemble", "b1")
                    chain = ["Merge #101: notes: a fourth line"]
                log = os.path.join(fx.tmp, "hook.log")
                path = os.path.join(fx.dev, ".git", "hooks", hook)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(RESERVING_HOOK % {"python": sys.executable, "size": HOOK_RESERVE, "log": log})
                os.chmod(path, 0o755)
                env = dict(fx.env)
                env.pop("MALLOC_ARENA_MAX", None)
                rc, out, err = self.bounded(*args, env=env, bound=60, git_memory=HOOK_PIN_GIT_MEMORY,
                                            hook_memory=HOOK_PIN_HOOK_MEMORY)
                self.assertEqual(rc, 0, out + err)
                self.assertEqual(fx.chain("b1"), chain, out + err)
                if hook == "pre-push":
                    self.assertEqual(fx.bare_rev("batch/b1"), fx.state("b1")["assembly"]["head"], "the push landed")
                with open(log) as f:
                    self.assertEqual(f.read(), "%s %d reserved\n" % (hook, HOOK_PIN_HOOK_MEMORY))

    def test_a_merge_abort_runs_under_git_memory_with_no_listing_before_it(self):
        """git merge --abort runs none of the hooks a merge runs (git 2.43.0 ran post-index-change and
        reference-transaction alone, as a checkout does), so it is not a call that runs the clone's hooks (_runs_hooks):
        it runs under GIT_MEMORY with no listing of the refs before it, and its own whole-file reads with it, such as
        its read of MERGE_AUTOSTASH. Here #108 stops for a hand resolution, MERGE_AUTOSTASH in the batch worktree's git
        dir is made a symlink to /dev/zero, and assemble --abort runs with GIT_MEMORY lowered to PLANT_MEMORY and
        HOOK_MEMORY to PLANT_HOOK_MEMORY (BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX unset, under PLANT_CAP, so no call has a
        real 16 GiB): it stops (exit 1) with GitMemory naming git merge --abort and GIT_MEMORY, and the call the driver
        logged before the merge --abort is not the listing (git for-each-ref --format=); the remedy's list of places
        names MERGE_AUTOSTASH, and the GitMemory names the planted file as a symlink (_odd_files' lstat of each of
        GIT_DIR_STATE_FILES). Red with git merge --abort among the calls that run hooks (the build head of round 2's
        rulings, whose _runs_hooks read the first word alone): the merge --abort came after a listing and met
        PLANT_HOOK_MEMORY ("reached the 384 MiB memory limit (HOOK_MEMORY)"); at the remedy's list of places, with a
        remedy that named no state file of a merge (no "MERGE_AUTOSTASH"); and at the planted file, with the lstat of
        MERGE_MSG, MERGE_AUTOSTASH and BISECT_START skipped and the remedy kept (the closing check at round 3 of PR
        959, NEW-3, its mutant m5g): the remedy named it, the files named did not."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, "premise: the merge of #108 stops for a hand resolution\n%s%s"
                         % (p.stdout, p.stderr))
        wt = fx.wt("b1")
        planted = os.path.join(wt, fx._git("rev-parse", "--git-path", "MERGE_AUTOSTASH", cwd=wt))
        self.assertTrue(os.path.isdir(os.path.dirname(planted)), "premise: the batch worktree's git dir")
        os.symlink("/dev/zero", planted)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        rc, out, err = self.bounded("assemble", "b1", "--abort", env=env, cap=PLANT_CAP, bound=60,
                                    git_memory=PLANT_MEMORY, hook_memory=PLANT_HOOK_MEMORY)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("git merge --abort in %s reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and "
                      "failed (fatal: Out of memory, " % (wt, PLANT_MEMORY >> 20), err)
        self.assertIn(REMEDY_PLACES, err)
        self.assertIn("%s (a symlink, not a regular file)" % planted, err)
        calls = [c[3] for c in self.calls]
        self.assertIn("merge --abort", calls, self.calls)
        at = calls.index("merge --abort")
        self.assertNotEqual(calls[at - 1] if at else None, "for-each-ref --format=",
                            "a listing came right before the merge --abort: %s" % self.calls)

    def test_a_merge_msg_read_without_end_at_continues_commit_is_named_in_the_remedy(self):
        """A merge or a commit reads MERGE_MSG whole (git writes it and reads it back), a file the listing of the refs
        before a call that runs the clone's hooks does not read, so a symlink to /dev/zero there holds the call to
        HOOK_MEMORY; the remedy's list of places names it. Here #108 stops for a hand resolution, the resolution is
        staged, MERGE_MSG in the batch worktree's git dir is made a symlink to /dev/zero, and assemble --continue runs
        with GIT_MEMORY lowered to PLANT_MEMORY and HOOK_MEMORY to PLANT_HOOK_MEMORY (BATCH_BOUND_DRIVER,
        MALLOC_ARENA_MAX unset, under PLANT_CAP, so no call has a real 16 GiB): it stops (exit 1) with GitMemory naming
        the commit and HOOK_MEMORY, the remedy names MERGE_MSG, and the GitMemory names the planted file as a symlink
        (_odd_files' lstat of each of GIT_DIR_STATE_FILES). Red before the remedy named it: the same GitMemory, its
        list of places ending at the shallow file, with no "MERGE_MSG"; and at the planted file, with the lstat of
        MERGE_MSG, MERGE_AUTOSTASH and BISECT_START skipped and the remedy kept (the closing check at round 3 of PR
        959, NEW-3, its mutant m5g): the remedy named it, the files named did not."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, "premise: the merge of #108 stops for a hand resolution\n%s%s"
                         % (p.stdout, p.stderr))
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        planted = os.path.join(wt, fx._git("rev-parse", "--git-path", "MERGE_MSG", cwd=wt))
        self.assertTrue(os.path.isfile(planted), "premise: the stopped merge left MERGE_MSG")
        os.remove(planted)
        os.symlink("/dev/zero", planted)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        rc, out, err = self.bounded("assemble", "b1", "--continue", "--reviewed", "subagent: fine", env=env,
                                    cap=PLANT_CAP, bound=60, git_memory=PLANT_MEMORY, hook_memory=PLANT_HOOK_MEMORY)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("git commit --quiet --no-edit in %s reached the %d MiB memory limit (HOOK_MEMORY) batch.py sets on "
                      "it and failed (fatal: Out of memory, " % (wt, PLANT_HOOK_MEMORY >> 20), err)
        self.assertIn(REMEDY_PLACES, err)
        self.assertIn("%s (a symlink, not a regular file)" % planted, err)

    def stopped_at_108(self):
        """#101 and #108 changing line two of notes.txt, planned as b1, and #108 stopped for a hand resolution (assemble
        --resolve 108), its resolution written and staged: the batch worktree."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo-a\nthree\n"})
        fx.branch("g", {"notes.txt": "one\ntwo-g\nthree\n"})
        fx.pr(101, "a", labels=["fix"], body=TRAILER)
        fx.pr(108, "g", title="notes: the g version", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        p = fx.run("assemble", "b1", "--resolve", "108")
        self.assertEqual(p.returncode, 3, "premise: the merge of #108 stops for a hand resolution\n%s%s"
                         % (p.stdout, p.stderr))
        wt = fx.wt("b1")
        with open(os.path.join(wt, "notes.txt"), "w") as f:
            f.write("one\ntwo-a-g\nthree\n")
        fx._git("add", "notes.txt", cwd=wt)
        return wt

    def plant_zero_at_git_path(self, wt, name):
        """A symlink to /dev/zero at `name` in the batch worktree's git dir, in place of the file there, if one is: its
        path, as git rev-parse --git-path gives it."""
        planted = os.path.join(wt, self.fx._git("rev-parse", "--git-path", name, cwd=wt))
        self.assertTrue(os.path.isdir(os.path.dirname(planted)), "premise: the batch worktree's git dir")
        if os.path.lexists(planted):
            os.remove(planted)
        os.symlink("/dev/zero", planted)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        return planted

    def assert_commit_names(self, rc, out, err, wt, planted):
        """`assemble`'s (rc, stdout, stderr) is a stop (exit 1) at git commit's GitMemory under HOOK_MEMORY lowered to
        PLANT_HOOK_MEMORY, naming `planted` as a symlink among the files git reads whole, with the remedy's list of
        places."""
        self.assertEqual(rc, 1, out + err)
        self.assertIn("git commit --quiet --no-edit in %s reached the %d MiB memory limit (HOOK_MEMORY) batch.py sets on "
                      "it and failed (fatal: Out of memory, " % (wt, PLANT_HOOK_MEMORY >> 20), err)
        self.assertIn("; of the files of the repository git reads whole, these are not regular files or hold more than a "
                      "file of their kind does, now (an lstat each after the call, so one can have changed since): ", err)
        self.assertIn("%s (a symlink, not a regular file)" % planted, err)
        self.assertIn(REMEDY_PLACES, err)

    def test_a_commit_editmsg_planted_before_a_rebuild_is_named_by_the_replay_commits_git_memory(self):
        """Round 3 of PR 959, extra4-1: git commit reads COMMIT_EDITMSG whole (it writes it and reads it back), and the
        file outlives prepare_worktree's git checkout -B, so one planted in the batch worktree's git dir before a rebuild
        is read by the rebuild's commit of a rerere replay; its GitMemory names the file (_odd_files lstats each of
        GIT_DIR_STATE_FILES in the call's git dir) and the remedy lists it. Here #108 stops, its hand resolution is
        committed with --continue (rerere records it), COMMIT_EDITMSG is made a symlink to /dev/zero, and assemble b1
        rebuilds the batch with GIT_MEMORY lowered to PLANT_MEMORY and HOOK_MEMORY to PLANT_HOOK_MEMORY
        (BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX unset, under PLANT_CAP): rerere replays #108's resolution and the commit
        stops (exit 1) with GitMemory naming git commit, HOOK_MEMORY and the planted file as a symlink, and the remedy
        names COMMIT_EDITMSG; the symlink is still there. Red at the round's head: the same GitMemory, naming no file and
        no COMMIT_EDITMSG in its remedy."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        wt = self.stopped_at_108()
        fx.ok("assemble", "b1", "--continue", "--reviewed", "subagent: fine")
        planted = self.plant_zero_at_git_path(wt, "COMMIT_EDITMSG")
        env = dict(fx.env)
        env.pop("MALLOC_ARENA_MAX", None)
        rc, out, err = self.bounded("assemble", "b1", env=env, cap=PLANT_CAP, bound=60, git_memory=PLANT_MEMORY,
                                    hook_memory=PLANT_HOOK_MEMORY)
        self.assertIn("merged #101", out, "premise: the rebuild got as far as #108's merge")
        self.assert_commit_names(rc, out, err, wt, planted)
        self.assertTrue(os.path.islink(planted), "the plant outlived the rebuild's git checkout -B")

    def test_a_merge_mode_or_squash_msg_planted_after_a_stop_is_named_by_continues_git_memory(self):
        """Round 3 of PR 959, extra4-1: git commit of a merge reads MERGE_MODE and SQUASH_MSG whole, so one planted in
        the batch worktree's git dir after a stop is read by assemble --continue's commit; its GitMemory names the file
        and the remedy lists it (each is removed by git checkout, so only a plant after a stop is read). Here, each case
        in a fixture of its own, #108 stops, its resolution is staged, the file is made a symlink to /dev/zero
        (MERGE_MODE, which the stopped merge wrote, replaced; SQUASH_MSG, absent, made), and --continue runs with
        GIT_MEMORY lowered to PLANT_MEMORY and HOOK_MEMORY to PLANT_HOOK_MEMORY (BATCH_BOUND_DRIVER, MALLOC_ARENA_MAX
        unset, under PLANT_CAP): it stops (exit 1) with GitMemory naming git commit, HOOK_MEMORY and the planted file as
        a symlink, and the remedy names the file. Red at the round's head: the same GitMemory, naming no file and neither
        file in its remedy."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        for n, name in enumerate(("MERGE_MODE", "SQUASH_MSG")):
            with self.subTest(file=name):
                if n:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                wt = self.stopped_at_108()
                there = os.path.lexists(os.path.join(wt, fx._git("rev-parse", "--git-path", name, cwd=wt)))
                self.assertEqual(there, name == "MERGE_MODE", "premise: the stopped merge wrote MERGE_MODE alone")
                planted = self.plant_zero_at_git_path(wt, name)
                env = dict(fx.env)
                env.pop("MALLOC_ARENA_MAX", None)
                rc, out, err = self.bounded("assemble", "b1", "--continue", "--reviewed", "subagent: fine", env=env,
                                            cap=PLANT_CAP, bound=60, git_memory=PLANT_MEMORY,
                                            hook_memory=PLANT_HOOK_MEMORY)
                self.assert_commit_names(rc, out, err, wt, planted)

    def landed(self, fx):
        """The two members (two_members) planned, assembled, pushed, swept, verified and summarized as batch b1 in `fx`,
        its CI run green, and batch PR #900 merged with a merge commit: finish has its whole cleanup to do."""
        saved, self.fx = self.fx, fx
        try:
            self.two_members()
        finally:
            self.fx = saved
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        fx.ci("b1")
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)

    def test_finishs_check_for_the_local_batch_branch_reads_no_name_its_short_name_would_open(self):
        """The 22:25Z ruling of 2026-10-03 on PR 959, item 1, at finish: its check that the local batch branch is still
        there, before it deletes it, names the branch by its full ref (batch_ref), so a symlink to /dev/zero at each name
        git's rev-parse rules try before refs/heads/batch/b1 (BATCH_SHADOWS), which a leg can leave in the clone through
        its checkout's alternates, is never read: finish, run under PLANT_CAP, exits and prints as it does in a twin
        fixture with nothing planted (each fixture's directory and every commit id written alike), the local branch is
        deleted, and each symlink is still there. Red at the head before the ruling, where the check named batch/b1, read
        the first of them, and finish stopped with GitMemory naming that check."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        self.maxDiff = None
        twin = Fixture()
        self.addCleanup(twin.close)

        def finished(fx):
            saved, self.fx = self.fx, fx
            try:
                rc, out, err = self.bounded("finish", "b1", cap=PLANT_CAP)
            finally:
                self.fx = saved
            alike = lambda text: re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", text.replace(fx.tmp, "<fixture>"))
            return rc, alike(out), alike(err)

        def deleted(fx):
            # the full ref, absent once deleted: its rules' names are made of refs/heads/batch/b1, none of them planted
            self.assertEqual(fx.dev_git("rev-parse", "--verify", "--quiet", "refs/heads/batch/b1", check=False), "",
                             "finish deleted the local batch branch")
        self.landed(twin)
        want = finished(twin)
        self.assertEqual((want[0], want[2]), (0, ""), "premise: finish with nothing planted:\n%s%s" % want[1:])
        self.assertIn("batch #900 landed, ", want[1])
        deleted(twin)
        self.landed(self.fx)
        planted = self.plant_batch_shadows()
        self.assertEqual(finished(self.fx), want, "finish with a symlink to /dev/zero at each of %s"
                         % ", ".join(BATCH_SHADOWS))
        deleted(self.fx)
        self.assertTrue(all(os.path.islink(p) for p in planted), "premise: the symlinks are still there")

    def test_finishs_check_reads_only_the_full_ref_once_the_local_batch_branch_is_gone(self):
        """The 22:25Z ruling of 2026-10-03 on PR 959, item 1, at finish, where the local batch branch is already gone, as a
        finish that died past its git branch -D leaves it: finish's check names the branch by its full ref with git
        show-ref --verify, which reads that one ref, loose or packed, and no other name. So a symlink to /dev/zero at
        each name git's rev-parse rules make of the absent full ref (refs/<ref>, refs/tags/<ref>, refs/heads/<ref> and
        refs/remotes/<ref>), which a leg can leave in the clone through its checkout's alternates, is never read:
        finish, run again under PLANT_CAP, exits 0 with its report and nothing on stderr, and each symlink is still
        there. Red with the check as git rev-parse --verify --quiet of the full ref, which walks those names when the
        ref is absent and stopped finish with GitMemory naming the check."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        self.landed(fx)
        if os.path.isdir(fx.wt("b1")):
            fx.dev_git("worktree", "remove", "--force", fx.wt("b1"))
        fx.dev_git("branch", "-D", "batch/b1")
        self.assertEqual(fx.dev_git("rev-parse", "--verify", "--quiet", "refs/heads/batch/b1", check=False), "",
                         "premise: the local batch branch is gone")
        planted = []
        for rule in REV_PARSE_RULES[1:5]:
            path = os.path.join(fx.dev, ".git", *(rule % "refs/heads/batch/b1").split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.symlink("/dev/zero", path)
            self.addCleanup(lambda p=path: os.path.lexists(p) and os.remove(p))
            planted.append(path)
        rc, out, err = self.bounded("finish", "b1", cap=PLANT_CAP)
        self.assertEqual((rc, err), (0, ""), out + err)
        self.assertIn("batch #900 landed, ", out)
        self.assertTrue(all(os.path.islink(p) for p in planted), "premise: the symlinks are still there")

    def test_bisect_takes_an_exit_of_125_as_a_skip_and_names_the_commit_it_skipped(self):
        """The closing check wf_3b100f5e-b38, its item 6, bisect's exit rules: 125 is git bisect run's skip. The command
        exits 125 at the one commit between the base and the tip, so no first bad commit can be named: bisect fails with
        its own line, and the skipped commit is in the output of git's that it passes on after that line, and it is reset
        with HEAD at the tip. A loop that read 125 as bad (the mutant mBisect125Bad) named #101 as the first bad member.
        What is held is what batch.py prints and the commit it names, not git's sentences around that commit, which
        batch.py never parses and which change between git versions (the closing check wf_fb19febe-36b, its item 1: this
        pin held git 2.43's "The first bad commit could be any of:", and CI's git 2.55 writes "first 'bad' commit", so it
        failed every Linux Python cell of run 36934414430). Red when the Fail drops the output it passes on (the mutant
        mBisectDropsOutput); test_bisect_reads_both_of_gits_wordings holds both wordings on any git."""
        rc, out, err, tip, merge_101 = self.bisected("exit 125")
        self.assertEqual((rc, out), (1, ""), out + err)
        line = "batch: bisect did not name a first bad commit:\n"
        self.assertTrue(err.startswith(line), err)
        self.assertIn(merge_101 + "\n", err[len(line):], "the skipped commit, in the output passed on")
        self.assert_reset_at_the_tip(tip)

    def test_bisects_moves_of_head_write_the_reflog_lines_git_checkout_writes(self):
        """bisect detaches HEAD at the tip with git update-ref --no-deref -m, and its cleanup points HEAD back at the
        batch branch with git symbolic-ref -m (attach_to_branch), each with the reflog line git checkout writes for the
        same move: "checkout: moving from batch/b1 to <tip>" as HEAD leaves the branch, and "checkout: moving from <the
        commit HEAD was at> to batch/b1" as the cleanup puts it back. Here the command passes at #101's merge, so bisect
        names #102, and the batch worktree's HEAD reflog, newest first, starts with the move back to batch/b1 from
        #101's merge, the last commit the steps checked out, and holds the move from batch/b1 to the tip. Red with
        symbolic-ref's message changed (its -m kept, so no case keyed on the call's words reds instead) and with
        update-ref's -m dropped."""
        fx = self.fx
        rc, out, err, tip, merge_101 = self.bisected("exit 0")
        self.assertEqual(rc, 0, out + err)
        self.assertTrue(out.startswith("first bad: #102 "), out + err)
        self.assert_reset_at_the_tip(tip)
        log = fx._git("reflog", "-n", "20", "--format=%gs", cwd=fx.wt("b1")).splitlines()
        self.assertEqual(log[0], "checkout: moving from %s to batch/b1" % merge_101, log)
        self.assertIn("checkout: moving from batch/b1 to %s" % tip, log)

    # A git first on PATH for test_bisect_reads_both_of_gits_wordings: it runs the real git (PLANT_REAL_GIT), and the
    # output of a `git bisect` call (bisect among its arguments, after the -c run_git puts first), its stdout and stderr
    # together, is passed on with git's sentence about the first bad commit written as BISECT_WORDING, whichever of the
    # two wordings that git wrote (git 2.43 "first bad commit", git 2.55 "first 'bad' commit"), and appended to
    # BISECT_SEEN; the call's exit status is the real git's.
    WORDING_GIT = r"""#!/bin/sh
case " $* " in
*" bisect "*)
  out=$("$PLANT_REAL_GIT" "$@" 2>&1)
  rc=$?
  printf '%s\n' "$out" | sed -e "s/first 'bad' commit/first bad commit/" -e "s/first bad commit/$BISECT_WORDING/" \
    | tee -a "$BISECT_SEEN"
  exit $rc ;;
esac
exec "$PLANT_REAL_GIT" "$@"
"""

    def test_bisect_reads_both_of_gits_wordings(self):
        """The closing check wf_fb19febe-36b, its item 1: git 2.43 writes "first bad commit" where git 2.55 writes "first
        'bad' commit", and a git first on PATH (WORDING_GIT) writes each into the real git's bisect output, so both are
        read on any git. With the command's exit 125 at the one commit between the base and the tip (a skip), bisect
        fails with its own line and the skipped commit in the output it passes on, whichever wording that output
        carries; with exit 1 there (bad), bisect names #101 from the wording's "<sha> is the first ... commit" line
        (_FIRST_BAD), which the fake's record shows it was given. Reset with HEAD at the tip after each. Red when the
        Fail drops the output it passes on (mBisectDropsOutput: the skip case of each wording)."""
        fx = self.fx
        tip, merge_101 = self.bisect_chain()
        d = os.path.join(fx.tmp, "wording-bin")
        os.makedirs(d)
        with open(os.path.join(d, "git"), "w") as f:
            f.write(self.WORDING_GIT)
        os.chmod(os.path.join(d, "git"), 0o755)
        line = "batch: bisect did not name a first bad commit:\n"
        for wording in ("first bad commit", "first 'bad' commit"):
            for middle in ("exit 125", "exit 1"):
                with self.subTest(wording=wording, middle=middle):
                    seen = os.path.join(d, "seen-%d" % len(os.listdir(d)))
                    env = dict(fx.env, PATH=d + os.pathsep + fx.env["PATH"], BISECT_WORDING=wording, BISECT_SEEN=seen,
                               PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]))
                    rc, out, err = self.bisect_with(middle, env=env)
                    if middle == "exit 125":
                        self.assertEqual((rc, out), (1, ""), out + err)
                        self.assertTrue(err.startswith(line), err)
                        self.assertIn(merge_101 + "\n", err[len(line):], "the skipped commit, in the output passed on")
                    else:
                        with open(seen) as f:
                            self.assertIn("%s is the %s" % (merge_101, wording), f.read(),
                                          "premise: bisect's output named #101's merge in this wording")
                        self.assertEqual((rc, err), (0, ""), out + err)
                        self.assertEqual(out, "first bad: #101 kernel: bump the version (merge %s); pull it and say why in "
                                              "the body\n" % merge_101[:10])
                    self.assert_reset_at_the_tip(tip)

    def test_bisect_stops_on_an_exit_of_128_or_more(self):
        """bisect's exit rules: an exit of 128 or more stops the bisect, as it stops git bisect run. The command exits
        128 at the commit between the base and the tip: bisect fails naming that commit and the exit, and is reset with
        HEAD at the tip. A loop that read 128 as bad (mBisect128Bad, the boundary moved by one, or mBisectNoStop, no stop
        at all) named #101; one with no reset (mBisectNoReset) left the worktree mid-bisect at #101's merge."""
        rc, out, err, tip, merge_101 = self.bisected("exit 128")
        self.assertEqual((rc, out), (1, ""), out + err)
        self.assertEqual(err, "batch: bisect stopped at %s: the command exited 128, and git bisect run stops on an exit of "
                              "128 or more, or a signal\n" % merge_101[:10])
        self.assert_reset_at_the_tip(tip)

    def test_bisect_takes_an_exit_of_127_as_bad(self):
        """bisect's exit rules, the boundary from below: 127, like every exit from 1 to 127 but 125, is bad, so the commit
        between the base and the tip is the first bad one and bisect names #101, reset with HEAD at the tip."""
        rc, out, err, tip, merge_101 = self.bisected("exit 127")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(out, "first bad: #101 kernel: bump the version (merge %s); pull it and say why in the body\n"
                         % merge_101[:10])
        self.assert_reset_at_the_tip(tip)

    def test_bisect_stops_when_the_command_is_ended_by_a_signal(self):
        """bisect's exit rules: a command ended by a signal stops the bisect, as it stops git bisect run. The command's
        shell sends itself SIGTERM at the commit between the base and the tip: bisect fails naming that commit and the
        signal (subprocess's exit -15), and is reset with HEAD at the tip. A loop with no stop (mBisectNoStop) read the
        signal as bad and named #101."""
        rc, out, err, tip, merge_101 = self.bisected("kill -TERM $$")
        self.assertEqual((rc, out), (1, ""), out + err)
        self.assertEqual(err, "batch: bisect stopped at %s: the command exited -15, and git bisect run stops on an exit of "
                              "128 or more, or a signal\n" % merge_101[:10])
        self.assert_reset_at_the_tip(tip)

    # A git first on PATH for the cleanup stop pins: it runs the real git (PLANT_REAL_GIT), except the first call whose
    # argv, joined by spaces, holds STOP_ON (it takes the file STOP_ARM, so no later call does): that one sends the signal
    # STOP_SIG names (TERM, or INT as Ctrl-C sends it) to the process that started it, batch.py, and waits to be ended
    # with its group, as a stop that lands as a cleanup git starts. A later call with the same argv runs the real git.
    # With STOP_PASS set, the first such call takes that file instead and runs the real git, so the second is the one
    # stopped (the forced restore of the branch's tree and the git symbolic-ref that points HEAD at the branch, which
    # bisect's two cleanups both run).
    STOP_AT_GIT = r"""#!/bin/sh
case " $* " in
  *"$STOP_ON"*) if [ -n "$STOP_PASS" ] && mv "$STOP_PASS" "$STOP_PASS.taken" 2>/dev/null; then
      :
    elif mv "$STOP_ARM" "$STOP_ARM.taken" 2>/dev/null; then
      kill -"$STOP_SIG" $PPID
      sleep 30
      exit 1
    fi ;;
esac
exec "$PLANT_REAL_GIT" "$@"
"""

    def stop_at_git(self, call, sig=signal.SIGTERM, second=False):
        """fx.env with STOP_AT_GIT first on PATH, armed to send `sig` to batch.py at the first git call holding `call`, or
        with `second` at the second one; and a function saying whether that call was met (the arm taken). Once per
        fixture: the git lives in its temp dir."""
        fx = self.fx
        d = os.path.join(fx.tmp, "stop-at-git")
        os.makedirs(d)
        with open(os.path.join(d, "git"), "w") as f:
            f.write(self.STOP_AT_GIT)
        os.chmod(os.path.join(d, "git"), 0o755)
        arm, first = os.path.join(d, "arm"), os.path.join(d, "pass")
        open(arm, "w").close()
        env = dict(fx.env, PATH=d + os.pathsep + fx.env["PATH"], STOP_ON=call, STOP_ARM=arm,
                   STOP_SIG=signal.Signals(sig).name[3:], PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]))
        if second:
            open(first, "w").close()
            env["STOP_PASS"] = first
        return env, lambda: os.path.exists(arm + ".taken")

    def test_a_stop_as_bisects_cleanup_git_starts_still_leaves_the_worktree_on_the_branch_and_reset(self):
        """The verify pass at the closing check wf_fb19febe-36b's build, its code finding 4, in bisect: SIGTERM, or SIGINT
        as Ctrl-C sends it, reaches batch.py just as a cleanup git starts (STOP_AT_GIT; batch.py started with SIGINT's
        handler Python's own, BATCH_TERMINAL_DRIVER): a step of the cleanup after the run at the base (its restore of the
        branch's tree, forced since the fixture's worktree has no changes, or the git symbolic-ref that then points HEAD
        at the branch), or of the cleanup after the steps (the same restore, the second call with that argv; the plain
        git bisect reset; the second git symbolic-ref). The stop ends that git, and the step runs again with the stop
        signals ignored (_cleanup_steps), and so do the steps after it, so batch.py exits 128 plus the signal's number
        naming it, with the worktree on batch/b1 at the tip and no bisect in progress, and the next bisect names #101.
        Before this change the stop ended the cleanup there: the worktree was
        left detached at the base (the next bisect refused it) or mid-bisect. SIGINT is a stop like SIGTERM (the 05:30Z
        ruling of 2026-10-02 on PR 926, its item 3): with it left as Python's KeyboardInterrupt (the mutant
        mIntDefault), which _cleanup_steps does not catch, a Ctrl-C there ended the cleanup the same way and batch.py
        died of the signal."""
        n = 0
        for sig in (signal.SIGTERM, signal.SIGINT):
            for call, second in (("read-tree --reset -u refs/heads/batch/b1", False), ("symbolic-ref -m", False),
                                 ("read-tree --reset -u refs/heads/batch/b1", True), ("bisect reset", False),
                                 ("symbolic-ref -m", True)):
                with self.subTest(signal=sig, call=call, second=second):
                    if n:
                        self.fx = Fixture()
                        self.addCleanup(self.fx.close)
                    n += 1
                    tip, merge_101 = self.bisect_chain()
                    env, met = self.stop_at_git(call, sig, second)
                    rc, out, err = self.bisect_with("exit 1", env=env, driver=BATCH_TERMINAL_DRIVER)
                    self.assertTrue(met(), "premise: the stop landed as `git %s` started" % call)
                    self.assertEqual((rc, out), (128 + sig, ""), out + err)
                    self.assertTrue(err.startswith("batch: stopped by signal %d;" % sig), err)
                    self.assert_reset_at_the_tip(tip)
                    rc, out, err = self.bisect_with("exit 1")
                    self.assertEqual((rc, err), (0, ""), out + err)
                    self.assertIn("first bad: #101 ", out)

    # A post-checkout hook for the bisect setup pins, inert unless SETUP_AT is set: the first checkout whose new HEAD is
    # SETUP_AT (it takes the file SETUP_ARM, so no later one does) waits on the FIFO SETUP_FIFO, which only the test opens
    # for writing, until it is ended; the step's git is then still running with HEAD already moved. Every other checkout
    # passes at once.
    SETUP_HOOK = r"""#!/bin/sh
if [ -n "$SETUP_AT" ] && [ "$2" = "$SETUP_AT" ] && mv "$SETUP_ARM" "$SETUP_ARM.taken" 2>/dev/null; then
  cat "$SETUP_FIFO" >/dev/null
fi
exit 0
"""

    def setup_hook(self, at):
        """SETUP_HOOK as the fixture clone's post-checkout hook (the batch worktree runs its common dir's hooks), and
        fx.env armed for the first checkout to `at`; returns (that env, the path that exists once that checkout has taken
        the arm). On the way out the FIFO is opened for writing without waiting, so a hook a red case left waiting reads
        its end and exits (_release_fifo)."""
        fx = self.fx
        d = os.path.join(fx.tmp, "setup-hook")
        os.makedirs(d)
        arm, fifo = os.path.join(d, "arm"), os.path.join(d, "fifo")
        os.mkfifo(fifo)
        self.addCleanup(_release_fifo, fifo)
        hooks = os.path.join(fx.dev, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        with open(os.path.join(hooks, "post-checkout"), "w") as f:
            f.write(self.SETUP_HOOK)
        os.chmod(os.path.join(hooks, "post-checkout"), 0o755)
        open(arm, "w").close()
        return dict(fx.env, SETUP_AT=at, SETUP_ARM=arm, SETUP_FIFO=fifo), arm + ".taken"

    def test_a_stop_during_bisects_setup_steps_leaves_the_worktree_on_the_branch_and_reset(self):
        """The 13:24Z ruling of 2026-10-02 on PR 926, its item 1: SIGTERM, or SIGINT as Ctrl-C sends it (batch.py started
        with SIGINT's handler Python's own, BATCH_TERMINAL_DRIVER), reaches batch.py while one of bisect's two setup
        checkouts is still running with HEAD already moved: its post-checkout hook (SETUP_HOOK) waits on a FIFO the test
        controls, in the detach checkout to the base, or in the checkout of the midpoint, #101's merge, which bisect
        makes after git bisect start (the bisect runs with --no-checkout). The stop ends that git with its group, the
        hook included, and the cleanup the step needs runs (the restore of the branch's tree and the move of HEAD to the
        branch; after the steps, the bisect reset between them), so batch.py exits 128 plus the signal's number naming
        it, with the worktree on batch/b1 at the tip and no bisect in progress, and the next bisect names #101. Before
        this change both steps came before the try whose finally cleans up: the stop left the worktree detached at the
        base, or mid-bisect at the midpoint (the next bisect refused it, naming HEAD), while batch.py said its cleanup
        ran (the focused re-check wf_e3f48b16-6ec)."""
        n = 0
        for sig in (signal.SIGTERM, signal.SIGINT):
            for step in ("the checkout of the base", "the checkout of the midpoint"):
                with self.subTest(signal=sig, step=step):
                    if n:
                        self.fx = Fixture()
                        self.addCleanup(self.fx.close)
                    n += 1
                    fx = self.fx
                    tip, merge_101 = self.bisect_chain()
                    base = fx.dev_git("merge-base", "origin/main", tip)
                    env, taken = self.setup_hook(base if step == "the checkout of the base" else merge_101)
                    rc, out, err = self.stop_when(lambda: os.path.exists(taken), "bisect", "b1", "--", "sh", "-c",
                                                  self.BISECT_CMD % "exit 1", env=env, sig=sig,
                                                  driver=BATCH_TERMINAL_DRIVER)
                    self.assertEqual((rc, out), (128 + sig, ""), out + err)
                    self.assertTrue(err.startswith("batch: stopped by signal %d;" % sig), err)
                    self.assert_reset_at_the_tip(tip)
                    rc, out, err = self.bisect_with("exit 1")
                    self.assertEqual((rc, err), (0, ""), out + err)
                    self.assertIn("first bad: #101 ", out)

    # A reference-transaction hook for the window pins, inert unless WINDOW_AT is set: in the first transaction git
    # prepares that moves HEAD to WINDOW_AT (it takes the file WINDOW_ARM, so no later one does) it waits on the FIFO
    # WINDOW_FIFO, which only the test opens for writing, until it is ended. A checkout runs that hook after it has written
    # the commit's files and the index and before HEAD moves, so the step's git is held there with HEAD not yet moved.
    # Every other transaction passes at once.
    WINDOW_HOOK = r"""#!/bin/sh
while read -r old new ref; do
  if [ "$1" = prepared ] && [ -n "$WINDOW_AT" ] && [ "$ref" = HEAD ] && [ "$new" = "$WINDOW_AT" ] &&
     mv "$WINDOW_ARM" "$WINDOW_ARM.taken" 2>/dev/null; then
    cat "$WINDOW_FIFO" >/dev/null
  fi
done
exit 0
"""

    def window_hook(self, at):
        """WINDOW_HOOK as the fixture clone's reference-transaction hook, and fx.env armed for the first move of HEAD to
        `at`; returns (that env, the path that exists once that move has taken the arm). On the way out the FIFO is
        opened for writing without waiting, so a hook a red case left waiting reads its end and exits (_release_fifo)."""
        fx = self.fx
        d = os.path.join(fx.tmp, "window-hook")
        os.makedirs(d)
        arm, fifo = os.path.join(d, "arm"), os.path.join(d, "fifo")
        os.mkfifo(fifo)
        self.addCleanup(_release_fifo, fifo)
        hooks = os.path.join(fx.dev, ".git", "hooks")
        os.makedirs(hooks, exist_ok=True)
        with open(os.path.join(hooks, "reference-transaction"), "w") as f:
            f.write(self.WINDOW_HOOK)
        os.chmod(os.path.join(hooks, "reference-transaction"), 0o755)
        open(arm, "w").close()
        return dict(fx.env, WINDOW_AT=at, WINDOW_ARM=arm, WINDOW_FIFO=fifo), arm + ".taken"

    def test_a_stop_after_a_setup_checkout_wrote_the_tree_and_before_head_moved_leaves_the_branchs_tree(self):
        """The verify pass at the build of the 13:24Z ruling of 2026-10-02 on PR 926, its code finding 1: SIGTERM, or
        SIGINT as Ctrl-C sends it (BATCH_TERMINAL_DRIVER), reaches batch.py while one of bisect's two setup checkouts
        (the detach checkout to the base; the checkout of the midpoint, #101's merge, which bisect makes after git
        bisect start) has written that commit's files and index and has not moved HEAD: git's reference-transaction
        hook (WINDOW_HOOK) waits there on a FIFO the test controls, as git waits on a FIFO planted at the worktree's
        logs/HEAD, which it writes between the two. HEAD is then still at the tip (on batch/b1 at the checkout of the
        base; detached there, by its id, at the checkout of the midpoint, since the bisect starts from HEAD detached at
        the tip), with the other commit's tree staged (the premise, read while the hook waits). The stop ends that git
        with its group, and the cleanup's restore of the branch's tree, forced since the worktree had no changes to
        tracked files, puts it back: batch.py exits 128 plus the signal's number naming it, with the worktree on batch/b1
        at the tip, no changes to tracked files and no bisect in progress, and the next bisect names #101. With that
        restore unforced (mBisectCleanupUnforced: the
        unforced checkout of the branch the cleanup had, or now its unforced two-way merge), the base's or the
        midpoint's tree stayed staged and the next bisect refused, saying the command passes at the tip."""
        n = 0
        for sig in (signal.SIGTERM, signal.SIGINT):
            for step in ("the checkout of the base", "the checkout of the midpoint"):
                with self.subTest(signal=sig, step=step):
                    if n:
                        self.fx = Fixture()
                        self.addCleanup(self.fx.close)
                    n += 1
                    fx = self.fx
                    tip, merge_101 = self.bisect_chain()
                    base = fx.dev_git("merge-base", "origin/main", tip)
                    env, taken = self.window_hook(base if step == "the checkout of the base" else merge_101)
                    wt, seen = fx.wt("b1"), {}

                    def ready():
                        # read once, while the hook waits: plumbing only, which writes neither the index nor a ref
                        if not seen and os.path.exists(taken):
                            seen.update(head=fx._git("rev-parse", "HEAD", cwd=wt),
                                        staged=fx._git("diff-index", "--cached", "--name-only", "HEAD", cwd=wt))
                        return bool(seen)
                    rc, out, err = self.stop_when(ready, "bisect", "b1", "--", "sh", "-c", self.BISECT_CMD % "exit 1",
                                                  env=env, sig=sig, driver=BATCH_TERMINAL_DRIVER)
                    self.assertEqual(seen["head"], tip, "premise: HEAD had not moved when the stop came")
                    self.assertNotEqual(seen["staged"], "", "premise: the step had written the other commit's tree")
                    self.assertEqual((rc, out), (128 + sig, ""), out + err)
                    self.assertTrue(err.startswith("batch: stopped by signal %d;" % sig), err)
                    self.assert_reset_at_the_tip(tip)
                    self.assertEqual(fx._git("status", "--porcelain", "--untracked-files=no", cwd=wt), "",
                                     "the worktree holds the branch's tree")
                    rc, out, err = self.bisect_with("exit 1")
                    self.assertEqual((rc, err), (0, ""), out + err)
                    self.assertIn("first bad: #101 ", out)

    def test_a_stop_as_the_ledger_checks_worktree_remove_starts_still_removes_the_worktree(self):
        """The verify pass at the closing check wf_fb19febe-36b's build, its code finding 4, in verify's ledger check:
        SIGTERM, or SIGINT as Ctrl-C sends it, reaches batch.py just as the git worktree remove of the check's temporary
        worktree starts (STOP_AT_GIT; batch.py started with SIGINT's handler Python's own, BATCH_TERMINAL_DRIVER). The
        stop ends that git, and the removal runs again with the stop signals ignored, then the removal of the directory
        holding it (_cleanup_steps), so batch.py exits 128 plus the signal's number naming it, with the worktree neither
        registered nor on disk. Before this change the stop ended the cleanup there: the worktree stayed registered and
        on disk. SIGINT is a stop like SIGTERM (the 05:30Z ruling of 2026-10-02 on PR 926, its item 3): with it left as
        Python's KeyboardInterrupt (the mutant mIntDefault), which _cleanup_steps does not catch, a Ctrl-C there left the
        worktree the same way and batch.py died of the signal."""
        for i, sig in enumerate((signal.SIGTERM, signal.SIGINT)):
            with self.subTest(signal=sig):
                if i:
                    self.fx = Fixture()
                    self.addCleanup(self.fx.close)
                fx = self.fx
                out = self.assembled_with_a_probe_ledger()
                env, met = self.stop_at_git("worktree remove -f -f", sig)
                rc, stdout, err = self.bounded("verify", "b1", "--no-fetch", env=dict(env, PROBE_OUT=out),
                                               driver=BATCH_TERMINAL_DRIVER)
                self.assertTrue(met(), "premise: the stop landed as `git worktree remove` started")
                [rec] = [r for r in self.probe_records(out) if r["argv"] == ["check"]]
                self.assertEqual(rc, 128 + sig, stdout + err)
                self.assertTrue(err.startswith("batch: stopped by signal %d;" % sig), err)
                self.assertNotIn(os.path.realpath(rec["cwd"]), fx.dev_git("worktree", "list", "--porcelain"),
                                 "the temporary worktree is no longer registered")
                self.assertFalse(os.path.lexists(os.path.dirname(rec["cwd"])),
                                 "the temporary worktree and its directory are gone")

    # A git first on PATH for the excuse rule's pin: it runs the real git (PLANT_REAL_GIT), except the call whose argv,
    # joined by spaces, holds WAIT_ON: that one starts a child (sleep 300), writes its own pid and the child's to WAIT_PIDS
    # (whole, by a rename) and waits for the child, so the call never ends on its own.
    WAIT_ON_GIT = r"""#!/bin/sh
case " $* " in
  *"$WAIT_ON"*) sleep 300 &
    echo $$ $! > "$WAIT_PIDS.tmp" && mv "$WAIT_PIDS.tmp" "$WAIT_PIDS"
    wait
    exit 1 ;;
esac
exec "$PLANT_REAL_GIT" "$@"
"""

    def test_a_bound_in_the_excuse_rules_read_is_a_fail_naming_the_rule(self):
        """The closing check wf_3b100f5e-b38, its item 6: batch.py's excuse_contradiction turns a refusal from
        scripts/sweep.py's excuse rule (its Refused, GitBound included) into a Fail naming the rule. The fixture's result
        marks deps not owed for having no vscode-extension/package.json, so verify reads `git cat-file -e
        <head>:vscode-extension/package.json` through sweep.py's run_git; a git first on PATH waits on that one call
        (WAIT_ON_GIT), and the driver lowers sweep.py's GIT_BOUND to BOUND (BATCH_SWEEP_BOUND_DRIVER). verify exits 1 with
        the Fail naming the rule and the call, and prints no traceback. With the wrapper removed (the mutant
        mExcuseUnwrapped) the GitBound went up uncaught and batch.py ended in a traceback."""
        fx = self.fx
        self.assembled()
        head = fx.dev_git("rev-parse", "batch/b1")
        d = os.path.join(fx.tmp, "excuse-bin")
        os.makedirs(d)
        with open(os.path.join(d, "git"), "w") as f:
            f.write(self.WAIT_ON_GIT)
        os.chmod(os.path.join(d, "git"), 0o755)
        pids = os.path.join(d, "pids")
        recorded = []
        self.addCleanup(lambda: _kill_alive(recorded))
        call = "cat-file -e %s:vscode-extension/package.json" % head
        env = dict(fx.env, PATH=d + os.pathsep + fx.env["PATH"], PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]),
                   WAIT_ON=call, WAIT_PIDS=pids)
        rc, out, err = self.bounded("verify", "b1", "--no-fetch", env=env, driver=BATCH_SWEEP_BOUND_DRIVER, planted=[call])
        recorded.extend(_recorded_pids(pids))
        self.assertEqual(len(recorded), 2, "premise: the excuse rule's read met the waiting git:\n" + out + err)
        self.assertEqual(rc, 1, out + err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(err, "batch: the sweep result's excuse rule could not be read: git %s in %s did not end within %d s "
                              "and was killed\n" % (call, fx.dev, self.BOUND))

    def test_a_ref_named_by_the_batch_head_that_git_reads_without_end_is_not_read_by_verify(self):
        """Round 1 of PR 959's spot-check, S4, on verify's path: batch.py's own git calls name the batch head by its full
        object id (its provenance check's rev-list and merge-base among them), and so does the excuse rule's git cat-file
        -e <head>:vscode-extension/package.json through scripts/sweep.py's run_git; each runs with core.warnAmbiguousRefs
        off (batch.py's run_git passes it; sweep.py's GIT_NEUTRAL_CONFIG holds it), so none opens a ref of that name. A
        symlink to /dev/zero at each of <git dir>/<head>, refs/tags/<head>, refs/heads/<head> and
        refs/remotes/<head>/HEAD in the clone, planted after assembly and the sweep, is never read: verify --no-fetch, run
        under PLANT_CAP on batch.py and every git it starts, exits and prints as it does with none planted. Before S4
        every one of those gits ran with the setting on and tried each name to warn of an ambiguous one: batch.py's own,
        which had no memory limit of their own then (round 1 of PR 959, V1, gave them one), read the symlink until the
        cap, and the excuse rule's until sweep.py's GIT_MEMORY, and verify failed."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        self.assembled()
        head = fx.dev_git("rev-parse", "batch/b1")
        want = self.bounded("verify", "b1", "--no-fetch", cap=PLANT_CAP)
        self.assertNotIn("memory", want[1] + want[2], "premise: verify with nothing planted")
        for rule in ("%s", "refs/tags/%s", "refs/heads/%s", "refs/remotes/%s/HEAD"):
            planted = os.path.join(fx.dev, ".git", *(rule % head).split("/"))
            os.makedirs(os.path.dirname(planted), exist_ok=True)
            os.symlink("/dev/zero", planted)
            try:
                with self.subTest(planted=rule):
                    got = self.bounded("verify", "b1", "--no-fetch", cap=PLANT_CAP)
                    self.assertEqual(got, want, "verify with the symlink planted: %r" % (got,))
            finally:
                os.remove(planted)

    def test_a_symlink_to_dev_zero_at_the_tag_of_origin_mains_name_is_never_read(self):
        """Round 1 of PR 959, V1: git's rev-parse rules try refs/tags/<name> before refs/remotes/<name>, whatever
        core.warnAmbiguousRefs says, so batch.py's reads of origin/main by its short name opened a symlink to /dev/zero
        a leg left at TAG_OF_ORIGIN_MAIN and read it without end. batch.py names it by its full ref wherever it needs only
        its commit, and a fetch reads no tag of that name, so with that symlink in the clone verify, fetching or not, and
        plan end as they end with none, and assemble assembles, each run under PLANT_CAP with no memory error. Before
        V1 each failed: its rev-parse, rev-list and merge-base of origin/main read the symlink until the cap and
        died with "fatal: Out of memory, realloc failed"."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        self.assembled()
        runs = (("verify", "b1"), ("verify", "b1", "--no-fetch"), ("plan", "--name", "b2"))
        want = {args: self.bounded(*args, cap=PLANT_CAP)[0] for args in runs}
        planted = os.path.join(fx.dev, ".git", *TAG_OF_ORIGIN_MAIN.split("/"))
        os.makedirs(os.path.dirname(planted), exist_ok=True)
        os.symlink("/dev/zero", planted)
        self.addCleanup(lambda: os.path.lexists(planted) and os.remove(planted))
        for args in runs + (("assemble", "b2"),):
            with self.subTest(args=" ".join(args)):
                rc, out, err = self.bounded(*args, cap=PLANT_CAP)
                self.assertNotIn("memory", (out + err).lower(), "a git read the symlink: %s%s" % (out, err))
                self.assertEqual(rc, want.get(args, 0), out + err)
                self.assertTrue(os.path.islink(planted), "premise: the symlink is still there")
        self.assertTrue(os.path.isdir(os.path.join(os.path.dirname(fx.dev), "romp-batch-b2")), "assemble made its worktree")

    def test_a_symlink_to_dev_zero_at_origin_mains_own_file_is_refused_within_the_memory_limit_naming_it(self):
        """Round 1 of PR 959, V1: a symlink to /dev/zero at origin/main's loose file (ORIGIN_MAIN_REF), which git reads
        whole by that exact name too, is read by the first git call that reads the ref: verify's fetch, or with
        --no-fetch its provenance check's rev-list, plan's fetch, and, planted just before it (PLANT_ZERO_GIT), assemble's
        worktree add of the batch branch at origin/main. Each meets the memory limit batch.py sets on every git call,
        here PLANT_MEMORY on the planted call (BATCH_BOUND_DRIVER), and the command stops (exit 1) with GitMemory,
        naming the call, the limit, git's line and the ref's file as a symlink (_odd_files, since round 2's ruling C);
        the call held no more than the limit. Before V1
        batch.py's git had no memory limit: each read the symlink until PLANT_CAP, died with "fatal: Out of memory,
        realloc failed", and was reported as a plain git failure."""
        if not sys.platform.startswith("linux"):
            self.skipTest("a symlink to /dev/zero is planted only where RLIMIT_AS, the cap on a read without end, is "
                          "enforced: Linux")
        fx = self.fx
        self.assembled()
        ref = os.path.join(fx.dev, ".git", *ORIGIN_MAIN_REF.split("/"))
        main = fx.dev_git("rev-parse", ORIGIN_MAIN_REF)
        fx.dev_git("update-ref", "-d", ORIGIN_MAIN_REF)     # a loose file, where the clone had packed the ref
        fx.dev_git("update-ref", ORIGIN_MAIN_REF, main)
        self.assertTrue(os.path.isfile(ref) and not os.path.islink(ref), "premise: the ref is a loose regular file")
        plant = os.path.join(fx.tmp, "plant-zero-bin")
        os.makedirs(plant)
        with open(os.path.join(plant, "git"), "w") as f:
            f.write(PLANT_ZERO_GIT)
        os.chmod(os.path.join(plant, "git"), 0o755)
        fx.ok("plan", "--name", "b2")
        cases = ((("verify", "b1"), "fetch --quiet --prune origin", None),
                 (("verify", "b1", "--no-fetch"), "rev-list refs/heads/batch/b1 ^refs/remotes/origin/main ^", None),
                 (("plan", "--name", "b3"), "fetch --quiet --prune origin", None),
                 (("assemble", "b2", "--no-fetch"), "worktree add --quiet -B batch/b2 ", "worktree add --quiet -B batch/b2"))
        for args, call, swap_on in cases:
            with self.subTest(args=" ".join(args)):
                env = None
                if swap_on is None:
                    os.remove(ref)
                    os.symlink("/dev/zero", ref)
                else:
                    env = dict(fx.env, PATH=plant + os.pathsep + fx.env["PATH"], PLANT_ON=swap_on, PLANT_ZERO=ref,
                               PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]))
                try:
                    rc, out, err = self.bounded(*args, env=env, cap=PLANT_CAP, bound=60, planted=[call],
                                                memory=PLANT_MEMORY)
                    self.assertTrue(os.path.islink(ref), "premise: the symlink was planted")
                finally:
                    if os.path.lexists(ref):
                        os.remove(ref)
                    fx.dev_git("update-ref", ORIGIN_MAIN_REF, main)
                self.assertEqual(rc, 1, out + err)
                self.assertIn("reached the %d MiB memory limit (GIT_MEMORY) batch.py sets on it and failed (fatal: Out of "
                              "memory, " % (PLANT_MEMORY >> 20), err)
                self.assertIn("batch: git %s" % call, err)
                self.assertIn("(an lstat each after the call, so one can have changed since): %s (a symlink, not a regular "
                              "file), and run the command again" % ref, err)
                ended = [c for c in self.calls if c[3].startswith(call)]
                self.assertEqual([c[1] for c in ended], ["memory"], "the planted call ended at the memory limit")
                self.assertLessEqual(int(ended[0][2]), PLANT_MEMORY, "the planted call held more than its limit: %s"
                                     % ended)

    def test_a_linked_worktree_clone_whose_git_file_is_swapped_after_discovery_is_still_the_one_read(self):
        """The 02:43Z ruling, item 1(b), its GIT_DIR (the verify pass at PR 926's build head, its code finding 3): the clone
        batch.py acts on is a linked worktree (ROMP_BATCH_REPO), whose .git file names its git dir under the common dir's
        worktrees/. repo_root reads the repository once, with the ceiling alone, and every later call names it explicitly
        (GIT_DIR, GIT_COMMON_DIR, GIT_WORK_TREE), so git does not read that .git file again. Here a git first on PATH
        rewrites it, just before verify's first rev-list and after the discovery, to name another repository's git dir
        (as a process outside the tool could): verify still reads the clone it found, and passes. A call that named only
        the ceiling and left git to find the repository from its cwd (the mutant gb-batch-nodir) followed the rewritten
        file to the other repository, where batch/b1 is no revision, and verify failed there."""
        fx = self.fx
        self.assembled()
        clone = os.path.join(fx.tmp, "dev-linked")
        fx.dev_git("worktree", "add", "--quiet", "--detach", clone, "main")
        other = os.path.join(fx.tmp, "other-repository")
        fx._git("init", "-q", other, cwd=fx.tmp)
        fx._git("commit", "-q", "--allow-empty", "-m", "another repository", cwd=other)
        plant = os.path.join(fx.tmp, "plant-gitfile-bin")
        os.makedirs(plant)
        with open(os.path.join(plant, "git"), "w") as f:
            f.write("#!/bin/sh\ncase \" $* \" in\n  *\"$PLANT_ON\"*) printf 'gitdir: %s\\n' \"$PLANT_GITDIR\" > \"$PLANT_GITFILE\" ;;\n"
                    "esac\nexec \"$PLANT_REAL_GIT\" \"$@\"\n")
        os.chmod(os.path.join(plant, "git"), 0o755)
        gitfile = os.path.join(clone, ".git")
        env = dict(fx.env, PATH=plant + os.pathsep + fx.env["PATH"], PLANT_REAL_GIT=shutil.which("git", path=fx.env["PATH"]),
                   PLANT_ON="rev-list", PLANT_GITFILE=gitfile, PLANT_GITDIR=os.path.join(other, ".git"),
                   ROMP_BATCH_REPO=clone)
        rc, out, err = self.bounded("verify", "b1", "--no-fetch", env=env)
        with open(gitfile) as f:
            self.assertEqual(f.read(), "gitdir: %s\n" % os.path.join(other, ".git"), "premise: the .git file was rewritten")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("ok   provenance", out)

    def test_a_fifo_or_a_symlink_at_the_batch_state_refuses_verify_and_assemble_naming_it(self):
        """The verify pass at PR 926's build head, its code finding 1: the batch's state file, <common dir>/batch/b1.json,
        which a sweep's leg reaches through its checkout's alternates, is replaced by a FIFO, or by a symlink to a copy of
        itself. load_state reads it as read_state reads (os.lstat, then an open that neither waits nor follows a
        symlink, then fstat), so verify and assemble each refuse (exit 1) naming the file and what it is, with no wait.
        At the build head both opened the FIFO by name and waited without end, and both read the symlink's target."""
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        state = os.path.join(fx.dev, ".git", "batch", "b1.json")
        copy = state + ".copy"
        shutil.copy(state, copy)
        for kind, word in (("fifo", "a FIFO"), ("link", "a symlink")):
            os.remove(state)
            if kind == "fifo":
                os.mkfifo(state)
            else:
                os.symlink(copy, state)
            for args in (("verify", "b1", "--no-fetch"), ("assemble", "b1", "--no-fetch")):
                with self.subTest(kind=kind, args=args):
                    rc, out, err = self.bounded(*args)
                    self.assertEqual(rc, 1, out + err)
                    self.assertIn("batch: the batch state %s cannot be read (%s, not a regular file); move it aside and plan "
                                  "again" % (state, word), err)

    def test_the_watchdog_kills_what_batch_py_started_in_a_session_of_its_own(self):
        """kill_tree, the kill bounded makes when its 60 s run out, takes a process the watched one started in a session of
        its own, as run_git starts each git: a stand-in for batch.py, in a group of its own, starts such a child and
        waits; kill_tree ends both. The watchdog before this change killed the watched group alone, and the child ran on
        (the verify pass at PR 926's build head, its code finding 4)."""
        if not os.path.isdir("/proc"):
            self.skipTest("kill_tree reads descendants from /proc; off Linux it kills the watched group alone")
        code = ("import subprocess, sys, time\n"
                "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'], start_new_session=True,\n"
                "                     stdin=subprocess.DEVNULL)\n"
                "print(p.pid, flush=True)\n"
                "time.sleep(300)\n")
        proc = subprocess.Popen([sys.executable, "-c", code], text=True, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                start_new_session=True)
        self.addCleanup(proc.stdout.close)
        self.addCleanup(lambda: proc.poll() is None and os.kill(proc.pid, 9))
        child = int(proc.stdout.readline())
        self.addCleanup(lambda: _proc_alive(child) and os.kill(child, 9))
        self.assertNotEqual(os.getpgid(child), os.getpgid(proc.pid), "premise: the child is in a group of its own")
        kill_tree(proc.pid)
        proc.wait(timeout=30)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and _proc_alive(child):
            time.sleep(0.05)
        self.assertFalse(_proc_alive(child), "the child in a session of its own outlived the watchdog's kill")

    def test_a_process_that_is_dead_or_a_zombie_reads_as_not_alive(self):
        """_proc_alive, which the watchdog pin and the stop pins read: a stat line whose state is Z (a zombie) or X (dead,
        as its reaper releases it) reads as exited, any other state as alive, with a command name holding a parenthesis.
        With Z alone (the mutant mAliveZOnly) X read as alive, as it turned tests/test_sweep_runner.py's watchdog pin red
        (DEAD_STATES)."""
        for state, alive in (("R", True), ("S", True), ("D", True), ("T", True), ("Z", False), ("X", False)):
            with self.subTest(state=state):
                stat = "4242 (a (b) c) %s 1 4242 4242 0 -1 4194304\n" % state
                with unittest.mock.patch.object(sys.modules[__name__], "open", unittest.mock.mock_open(read_data=stat),
                                                create=True):
                    self.assertEqual(_proc_alive(4242), alive)

    def test_a_git_the_tool_starts_is_killed_with_its_process_group_at_the_bound(self):
        """run_git itself, through a git on PATH that starts a child and waits: at the bound GitBound, a Fail, names the
        call, and neither the git nor its child is left running. The case cleans up when it goes red too (the closing
        check wf_3b100f5e-b38, its item 6): the driver runs in a session of its own under a 60 s watchdog that kills its
        whole tree (kill_tree), and the git and its child, by the pids the git recorded, are killed on the way out when
        they are alive. Under a run_git that killed the git alone (mPgKillBatch) the case went red and the child ran on,
        and under one with no bound (mNoBoundBatch) the driver's own timeout killed only the driver."""
        tmp = tempfile.mkdtemp(prefix="batchgb-")
        self.addCleanup(shutil.rmtree, tmp, True)
        pids = os.path.join(tmp, "pids")
        with open(os.path.join(tmp, "git"), "w") as f:
            f.write("#!/bin/sh\nsleep 300 &\necho $$ $! > %s.tmp && mv %s.tmp %s\nwait\n" % (pids, pids, pids))
        os.chmod(os.path.join(tmp, "git"), 0o755)
        code = ("import importlib.util, os, sys\n"
                "spec = importlib.util.spec_from_file_location('batch_tool_gb', sys.argv[1])\n"
                "mod = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(mod)\n"
                "mod.GIT_BOUND = 2\n"
                "try:\n"
                "    mod.run_git(['status'], sys.argv[2], repo=mod.GitRepo(sys.argv[2], None, None, os.path.dirname(sys.argv[2])))\n"
                "except mod.Fail as e:\n"
                "    print('%s: %s' % (type(e).__name__, e))\n")
        env = dict(os.environ, PATH=tmp + os.pathsep + os.environ.get("PATH", ""))
        p = subprocess.Popen([sys.executable, "-c", code, str(SCRIPTS / "batch.py"), tmp], env=env, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(lambda: p.poll() is None and kill_tree(p.pid))
        recorded = []
        self.addCleanup(lambda: _kill_alive(recorded))
        try:
            out, err = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            recorded.extend(_recorded_pids(pids))
            kill_tree(p.pid)
            out, err = p.communicate()
            self.fail("run_git was still waiting 60 s after its 2 s bound:\n%s%s" % (out, err))
        recorded.extend(_recorded_pids(pids))
        self.assertEqual(p.returncode, 0, out + err)
        self.assertIn("GitBound: git status in %s did not end within 2 s and was killed" % tmp, out)
        if not os.path.isdir("/proc"):
            return                               # no /proc to tell a live process by (macOS): the bound alone is pinned
        self.assertEqual(len(recorded), 2, "premise: the git recorded its pid and its child's")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and any(_proc_alive(x) for x in recorded):
            time.sleep(0.05)
        self.assertEqual([x for x in recorded if _proc_alive(x)], [], "the git and its child are gone")

    # A git first on PATH for the stop pins: every call starts a child (sleep 300), writes its own pid and the child's to
    # STOP_PIDS (whole, by a rename), and waits for the child, so the call never ends on its own.
    WAITING_GIT = '#!/bin/sh\nsleep 300 &\necho $$ $! > "$STOP_PIDS.tmp" && mv "$STOP_PIDS.tmp" "$STOP_PIDS"\nwait\n'

    def stopped(self, signals, ignored=()):
        """batch.py verify (BATCH_BOUND_DRIVER with no call at a short bound, so batch.py's 600 s does not end the wait
        here) with WAITING_GIT first on PATH, started in a session of its own with SIGHUP and SIGINT at their default
        action (so SIGINT's handler is Python's own, as for a process started from a terminal), or ignored for those in
        `ignored`. Once the git it is waiting on has written its pids (its first git call, repo_root's discovery), each
        of `signals` is sent to batch.py alone, in order. Returns (rc, stderr, [the git and its child, those still alive 10
        s after batch.py ended]). The git and its child are SIGKILLed on the way out when they are still alive, and
        batch.py's whole tree too (kill_tree), so a red case leaves nothing running."""
        fx = self.fx
        n = 0
        while os.path.exists(os.path.join(fx.tmp, "stop-bin-%d" % n)):    # one per call: a case can stop more than once
            n += 1
        d = os.path.join(fx.tmp, "stop-bin-%d" % n)
        os.makedirs(d)
        with open(os.path.join(d, "git"), "w") as f:
            f.write(self.WAITING_GIT)
        os.chmod(os.path.join(d, "git"), 0o755)
        pids = os.path.join(d, "pids")
        env = dict(fx.env, PATH=d + os.pathsep + fx.env["PATH"], STOP_PIDS=pids)
        driver = [sys.executable, "-c", BATCH_BOUND_DRIVER, bound_spec(600), os.path.join(fx.dev, "scripts", "batch.py"), "verify", "b1",
                  "--no-fetch"]
        shim = "import os, signal, sys\n" + "".join(
            "signal.signal(signal.%s, signal.%s)\n" % (signal.Signals(s).name, "SIG_IGN" if s in ignored else "SIG_DFL")
            for s in (signal.SIGHUP, signal.SIGINT)) + "os.execv(sys.argv[1], sys.argv[1:])\n"
        driver = [sys.executable, "-c", shim, *driver]
        proc = subprocess.Popen(driver, cwd=fx.tmp, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and kill_tree(proc.pid))
        recorded = []

        def kill_recorded():
            for pid in recorded:
                if _proc_alive(pid):
                    try:
                        os.kill(pid, 9)
                    except OSError:
                        pass
        self.addCleanup(kill_recorded)
        deadline = time.monotonic() + 60
        while not os.path.exists(pids) and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if not os.path.exists(pids):
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("premise: the waiting git never started (rc %s):\n%s%s" % (proc.returncode, out, err))
        with open(pids) as f:
            recorded.extend(int(x) for x in f.read().split())
        for sig in signals:
            os.kill(proc.pid, sig)
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("batch.py was still running 60 s after %s:\n%s%s" % (signals, out, err))
        if not os.path.isdir("/proc"):
            return proc.returncode, err, None    # no /proc to tell a live process by (macOS): the exit alone is pinned
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and any(_proc_alive(x) for x in recorded):
            time.sleep(0.05)
        return proc.returncode, err, [x for x in recorded if _proc_alive(x)]

    def test_sigterm_sighup_and_sigint_stop_the_tool_and_kill_the_git_it_waits_on_with_its_child(self):
        """The closing check wf_3b100f5e-b38, its item 4: batch.py installs SIGTERM and SIGHUP handlers that raise
        Stopped, a BaseException as scripts/sweep.py's is, so run_git's except path kills the git it is waiting on, which
        runs in a session of its own, with that git's process group, and the tool exits 128 plus the signal's number
        naming it. Before this change batch.py had no handler: each signal killed batch.py alone, and the git and its
        child ran on, unbounded, since the bound lived in the dead parent. SIGINT (Ctrl-C) raises Stopped too (the
        05:30Z ruling of 2026-10-02 on PR 926, its item 3), so it exits 130 the same way; before, it raised
        KeyboardInterrupt and batch.py died of the signal after killing the git."""
        fx = self.fx
        self.assembled()
        for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            with self.subTest(signal=sig):
                rc, err, left = self.stopped([sig])
                self.assertEqual(rc, 128 + sig, err)
                self.assertIn("batch: stopped by signal %d; any process it was waiting on was killed and its cleanup ran\n" % sig,
                              err)
                self.assertIn(left, ([], None), "the git and its child are gone")

    # The no-process stop pin's driver: BATCH_BOUND_DRIVER with load_state sending SIGTERM to this process before it
    # reads the plan, so the stop lands in verify after repo_root's git has ended and before the next process starts.
    STOP_IN_LOAD_STATE_DRIVER = BATCH_BOUND_DRIVER.replace("sys.exit(mod.main(argv))\n", """import os, signal
load_state = mod.load_state
def stopping_load_state(*args, **kwargs):
    os.kill(os.getpid(), signal.SIGTERM)
    return load_state(*args, **kwargs)
mod.load_state = stopping_load_state
sys.exit(mod.main(argv))
""")

    def test_a_stop_with_no_process_running_does_not_claim_one_was_killed(self):
        """The verify pass at the closing check wf_fb19febe-36b's build, the class of its code finding 3 in batch.py: a
        stop that lands between two processes (STOP_IN_LOAD_STATE_DRIVER) kills none, and the line batch.py prints says
        any process it was waiting on was killed, not that one was. Before this change it said the process it was
        waiting on was killed whether one was running or not."""
        self.assembled()
        rc, out, err = self.bounded("verify", "b1", "--no-fetch", driver=self.STOP_IN_LOAD_STATE_DRIVER)
        self.assertEqual((rc, err), (128 + signal.SIGTERM, "batch: stopped by signal %d; any process it was waiting on was "
                                                           "killed and its cleanup ran\n" % signal.SIGTERM), out)

    def test_a_sighup_or_sigint_the_tool_was_started_with_ignored_stays_ignored(self):
        """A SIGHUP batch.py was started with ignored (nohup), or a SIGINT (a non-interactive shell's background job),
        stays ignored, as in scripts/sweep.py (IGNORE_INHERITED): that signal and then SIGTERM sent to it end it with
        SIGTERM's exit (143), the git it waits on and its child killed. Had it caught the first signal, that one would
        have won and it would exit 129 or 130; before the closing check wf_3b100f5e-b38's item 4 it had no handler,
        SIGTERM killed it alone (exit -15), and the git and its child ran on."""
        fx = self.fx
        self.assembled()
        for sig in (signal.SIGHUP, signal.SIGINT):
            with self.subTest(signal=sig):
                rc, err, left = self.stopped([sig, signal.SIGTERM], ignored=(sig,))
                self.assertEqual(rc, 128 + signal.SIGTERM, err)
                self.assertIn("batch: stopped by signal %d;" % signal.SIGTERM, err)
                self.assertIn(left, ([], None), "the git and its child are gone")

    # The prelude of the probes for the two processes batch.py starts that run git in the clone (the closing check
    # wf_3b100f5e-b38, its item 5): each appends one JSON line to PROBE_OUT, written whole, holding the repository
    # variables it was started with, its first argument and its cwd, and with PROBE_WAIT set starts a child (sleep
    # 300), records both pids in that line, and waits for the child, so it never ends on its own.
    PROBE_PRELUDE = r'''import json, os, subprocess, sys
_rec = {k: os.environ.get(k) for k in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_CEILING_DIRECTORIES")}
_rec.update(argv=sys.argv[1:2], cwd=os.getcwd())
_child = None
if os.environ.get("PROBE_WAIT"):
    _child = subprocess.Popen(["sleep", "300"], stdin=subprocess.DEVNULL)
    _rec["pids"] = [os.getpid(), _child.pid]
_fd = os.open(os.environ["PROBE_OUT"], os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
os.write(_fd, (json.dumps(_rec) + "\n").encode())
os.close(_fd)
if _child is not None:
    _child.wait()
'''

    def probe_records(self, path):
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(line) for line in f.read().splitlines()]

    def assert_named(self, rec, work_tree, git_dir, common_dir):
        """`rec` (a probe's line) was started with the repository at `work_tree` named explicitly, as run_git names it."""
        real = os.path.realpath
        self.assertEqual({k: rec[k] and real(rec[k]) for k in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE",
                                                                 "GIT_CEILING_DIRECTORIES")},
                         {"GIT_DIR": real(git_dir), "GIT_COMMON_DIR": real(common_dir), "GIT_WORK_TREE": real(work_tree),
                          "GIT_CEILING_DIRECTORIES": real(os.path.dirname(work_tree))}, rec)

    def kill_probe_pids_on_the_way_out(self, out):
        """SIGKILL, when the case ends, every pid a probe line at `out` recorded that is still alive, so a red case leaves
        neither the probe nor its child running."""
        def kill():
            for rec in self.probe_records(out):
                for pid in rec.get("pids") or []:
                    if _proc_alive(pid):
                        try:
                            os.kill(pid, 9)
                        except OSError:
                            pass
        self.addCleanup(kill)

    def test_the_ledger_script_runs_with_the_trees_repository_named_explicitly(self):
        """The closing check wf_3b100f5e-b38, its item 5, the ledger script: assemble runs it in the batch worktree to
        convert a straggler UPSTREAM.md row (import --row), and verify runs its check in a temporary detached worktree of
        the batch branch. Each starts through run_tool, with that worktree's repository named in its environment (GIT_DIR
        its git dir under the clone's worktrees/, GIT_COMMON_DIR the clone's .git, GIT_WORK_TREE the worktree,
        GIT_CEILING_DIRECTORIES above it), so the git it runs (git -C <root> log, git -C <root> config) reads that
        repository. Before this change each inherited the environment, with none of the four set."""
        fx = self.fx
        out = os.path.join(fx.tmp, "ledger-probe.jsonl")
        fx.env["PROBE_OUT"] = out
        pre_migration = fx.bare_rev("main")
        member_md = SEED["UPSTREAM.md"].replace("|---|---|---|---|\n", "|---|---|---|---|\n| row two | fork PR #110 | candidate | why |\n")
        fx.branch("s", {"UPSTREAM.md": member_md}, base=pre_migration)
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        probe = "#!/usr/bin/env python3\n" + self.PROBE_PRELUDE + FAKE_LEDGER.split("\n", 1)[1]
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": probe}, "ledger migration")
        fx.pr(110, "s", title="a straggler row", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        self.assertIn("converted", fx.state("b1")["assembly"]["merged"][0]["resolved"]["how"], "premise: the row was imported")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   ledger: check clean", p.stdout)
        recs = self.probe_records(out)
        self.assertEqual([r["argv"] for r in recs], [["import"], ["check"]], recs)
        common = os.path.join(fx.dev, ".git")
        wt = fx.wt("b1")
        self.assertEqual(os.path.realpath(recs[0]["cwd"]), os.path.realpath(wt))
        self.assert_named(recs[0], wt, os.path.join(common, "worktrees", os.path.basename(wt)), common)
        tree = recs[1]["cwd"]
        self.assertNotEqual(os.path.realpath(tree), os.path.realpath(wt), "premise: the check ran in a worktree of its own")
        self.assert_named(recs[1], tree, os.path.join(common, "worktrees", os.path.basename(tree)), common)

    def test_a_ledger_check_that_does_not_end_is_killed_at_the_bound_and_its_worktree_removed(self):
        """The closing check wf_3b100f5e-b38, its item 5, the bound: the batch branch's ledger script starts a child and
        waits. verify's check runs it through run_tool, so at the bound (3 s here) it is killed with its process group,
        the child included, verify is refused (exit 1) naming the call, and the temporary worktree it ran in is removed
        on the way out. Before this change the script had no bound: verify waited without end (the case then fails at
        the 60 s watchdog)."""
        fx = self.fx
        out = self.assembled_with_a_probe_ledger()
        rc, stdout, err = self.bounded("verify", "b1", "--no-fetch", env=dict(fx.env, PROBE_OUT=out, PROBE_WAIT="1"),
                                       planted=["%s %s check" % (sys.executable, os.path.join("scripts", "upstream-ledger.py"))])
        [rec] = self.probe_records(out)
        self.assertEqual(rec["argv"], ["check"], "premise: the check ran")
        self.assertEqual(rc, 1, stdout + err)
        m = re.search(r"^batch: %s %s check in (\S+) did not end within 3 s and was killed$"
                      % (re.escape(sys.executable), re.escape(os.path.join("scripts", "upstream-ledger.py"))), err, re.M)
        self.assertIsNotNone(m, err)
        self.assertEqual(os.path.realpath(m.group(1)), os.path.realpath(rec["cwd"]), "the call names the tree it ran in")
        self.assertFalse(os.path.exists(m.group(1)), "the temporary worktree was removed")
        self.assertFalse(os.path.exists(os.path.dirname(m.group(1))), "and the directory holding it")
        if os.path.isdir("/proc"):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and any(_proc_alive(x) for x in rec["pids"]):
                time.sleep(0.05)
            self.assertEqual([x for x in rec["pids"] if _proc_alive(x)], [], "the script and its child are gone")

    def assembled_with_a_probe_ledger(self):
        """Batch b1 assembled from one member whose branch carries a probe (PROBE_PRELUDE) as scripts/upstream-ledger.py,
        swept; returns the probe's PROBE_OUT path, whose recorded pids are killed when the case ends."""
        fx = self.fx
        out = os.path.join(fx.tmp, "ledger-probe.jsonl")
        self.kill_probe_pids_on_the_way_out(out)
        probe = "#!/usr/bin/env python3\n" + self.PROBE_PRELUDE + FAKE_LEDGER.split("\n", 1)[1]
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n", "scripts/upstream-ledger.py": probe})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.sweep("b1")
        return out

    def test_a_stop_during_the_ledger_check_kills_the_script_and_removes_its_worktree(self):
        """The closing check wf_3b100f5e-b38, its items 4 and 5 together: SIGTERM reaches batch.py while verify's ledger
        check waits on a script that started a child. Stopped kills the script with its process group, the child
        included (run_tool's except path), the finally of the check removes the temporary worktree and the directory
        holding it, and batch.py exits 143 naming the signal. Before these changes SIGTERM killed batch.py alone: the
        script and its child ran on, and the worktree stayed registered in the clone."""
        fx = self.fx
        out = self.assembled_with_a_probe_ledger()
        env = dict(fx.env, PROBE_OUT=out, PROBE_WAIT="1")
        proc = subprocess.Popen([sys.executable, "-c", BATCH_BOUND_DRIVER, bound_spec(600), os.path.join(fx.dev, "scripts", "batch.py"),
                                 "verify", "b1", "--no-fetch"], cwd=fx.tmp, env=env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and kill_tree(proc.pid))
        deadline = time.monotonic() + 60
        while not self.probe_records(out) and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        recs = self.probe_records(out)
        if not recs:
            kill_tree(proc.pid)
            stdout, err = proc.communicate()
            self.fail("premise: the ledger check never started (rc %s):\n%s%s" % (proc.returncode, stdout, err))
        [rec] = recs
        os.kill(proc.pid, signal.SIGTERM)
        try:
            stdout, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            stdout, err = proc.communicate()
            self.fail("batch.py was still running 60 s after SIGTERM:\n%s%s" % (stdout, err))
        self.assertEqual(proc.returncode, 128 + signal.SIGTERM, stdout + err)
        self.assertIn("batch: stopped by signal %d;" % signal.SIGTERM, err)
        self.assertFalse(os.path.exists(os.path.dirname(rec["cwd"])), "the temporary worktree and its directory were removed")
        listed = fx.dev_git("worktree", "list", "--porcelain")
        self.assertNotIn(os.path.realpath(rec["cwd"]), listed, "the worktree is no longer registered in the clone")
        if os.path.isdir("/proc"):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and any(_proc_alive(x) for x in rec["pids"]):
                time.sleep(0.05)
            self.assertEqual([x for x in rec["pids"] if _proc_alive(x)], [], "the script and its child are gone")

    def finished_with_a_probe_for_pr_orphans(self, wait):
        """A batch landed by hand (LandAndFinish.ready, then the fake gh's merge) and the clone's scripts/pr-orphans.sh a
        probe (PROBE_PRELUDE) that prints a clean line; finish run under bounded, with PROBE_WAIT when `wait`, and the
        probe the planted call then alone (with no wait nothing is planted, and the probe keeps batch.py's bound).
        Returns (rc, stdout, stderr, the probe's lines)."""
        fx = self.fx
        LandAndFinish.ready(self)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        out = os.path.join(fx.tmp, "orphans-probe.jsonl")
        self.kill_probe_pids_on_the_way_out(out)
        script = os.path.join(fx.dev, "scripts", "pr-orphans.sh")
        with open(script, "w") as f:
            f.write("#!%s\n%sprint('pr-orphans: none stranded')\n" % (sys.executable, self.PROBE_PRELUDE))
        os.chmod(script, 0o755)
        env = dict(fx.env, PROBE_OUT=out, **({"PROBE_WAIT": "1"} if wait else {}))
        rc, stdout, err = self.bounded("finish", "b1", env=env, planted=[script] if wait else [])
        return rc, stdout, err, self.probe_records(out)

    def test_pr_orphans_runs_with_the_clones_repository_named_explicitly(self):
        """The closing check wf_3b100f5e-b38, its item 5, scripts/pr-orphans.sh: finish runs it in the clone through
        run_tool, with the clone named in its environment (GIT_DIR and GIT_COMMON_DIR its .git, GIT_WORK_TREE the
        clone, GIT_CEILING_DIRECTORIES above it), so its git fetch, rev-parse and merge-base read the clone. Before this
        change it inherited the environment, with none of the four set."""
        fx = self.fx
        rc, stdout, err, recs = self.finished_with_a_probe_for_pr_orphans(wait=False)
        self.assertEqual(rc, 0, stdout + err)
        self.assertIn("pr-orphans.sh: clean", stdout)
        [rec] = recs
        self.assertEqual(os.path.realpath(rec["cwd"]), os.path.realpath(fx.dev))
        self.assert_named(rec, fx.dev, os.path.join(fx.dev, ".git"), os.path.join(fx.dev, ".git"))

    def test_a_pr_orphans_that_does_not_end_is_reported_unread_and_finish_carries_on(self):
        """The closing check wf_3b100f5e-b38, its item 5, the bound at finish: pr-orphans.sh starts a child and waits. At
        the bound (3 s here) run_tool kills it with its process group, the child included; the merge having happened,
        finish reports it as unread, naming the call, reads the batch head's CI run and exits 0, as it does when that
        read fails. Before this change the script had no bound: finish waited without end (the case then fails at the
        60 s watchdog)."""
        fx = self.fx
        rc, stdout, err, recs = self.finished_with_a_probe_for_pr_orphans(wait=True)
        [rec] = recs
        self.assertEqual(rc, 0, stdout + err)
        self.assertIn("pr-orphans.sh: unread: %s in %s did not end within 3 s and was killed\n"
                      % (os.path.join(fx.dev, "scripts", "pr-orphans.sh"), fx.dev), stdout)
        self.assertIn("the batch head's CI run: green", stdout)
        self.assertEqual(fx.state("b1")["finished"]["report"]["orphans"]["exit"], None)
        if os.path.isdir("/proc"):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and any(_proc_alive(x) for x in rec["pids"]):
                time.sleep(0.05)
            self.assertEqual([x for x in rec["pids"] if _proc_alive(x)], [], "the script and its child are gone")


    # The verify pass at the wf_3b100f5e-b38 build, its code finding 1: a git worktree add ended at the bound or on a
    # stop gets SIGTERM with its process group first (_end_group), so git removes the worktree it was adding, that
    # worktree's registration and the index.lock its checkout held; a SIGKILL left the registration locked
    # ("initializing"), which neither git worktree prune nor git worktree remove --force clears, with the index.lock in
    # it. Each case below plants a FIFO at the clone's info/exclude, which the add's checkout reads, so the add waits
    # there.

    def fifo_at(self, rel):
        """Make the clone's .git/`rel` a FIFO until the returned function is called (and when the case ends), keeping what
        was there and putting it back."""
        path = os.path.join(self.fx.dev, ".git", rel)
        saved = None
        if os.path.lexists(path):
            with open(path, "rb") as f:
                saved = f.read()
            os.remove(path)
        os.mkfifo(path)
        done = []

        def restore():
            if done:
                return
            done.append(True)
            os.remove(path)
            if saved is not None:
                with open(path, "wb") as f:
                    f.write(saved)
        self.addCleanup(restore)
        return restore

    def registrations(self):
        """{name: the text of its locked file, or None when it has none} for each worktree registered in the clone."""
        d = os.path.join(self.fx.dev, ".git", "worktrees")
        out = {}
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            lock = os.path.join(d, name, "locked")
            if os.path.exists(lock):
                with open(lock) as f:
                    out[name] = f.read().strip()
            else:
                out[name] = None
        return out

    def stop_when(self, ready, *args, env=None, sig=signal.SIGTERM, driver=BATCH_BOUND_DRIVER):
        """batch.py `args` (through `driver`, BATCH_BOUND_DRIVER or one of its variants, with no call at a short bound,
        so batch.py's 600 s does not end the wait here), started in a session of its own; once `ready()` is true, `sig`
        (SIGTERM unless given) is sent to batch.py alone. Returns (rc, stdout, stderr). batch.py's whole tree is killed
        on the way out when it is still running (kill_tree), and every descendant of it read just before the signal,
        with that descendant's process group as read then, is killed on the way out when it is still alive
        (_kill_groups, _kill_alive), so a red case leaves nothing running: a batch.py the signal ended outright (a
        regression to no handler) has already exited by then, and the git it was waiting on, in a session of its own, is
        no longer in the tree kill_tree walks, nor is a process that git started after the read, which is in its group
        (_groups_of; the closing check wf_fb19febe-36b, its item 5; StopPinsLeaveNothing holds it). The case fails by
        name if `ready()` is not true within 60 s or batch.py runs on 60 s after the signal."""
        fx = self.fx
        proc = subprocess.Popen([sys.executable, "-c", driver, bound_spec(600), os.path.join(fx.dev, "scripts", "batch.py"),
                                 *args], cwd=fx.tmp, env=env or fx.env, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and kill_tree(proc.pid))
        recorded, groups = [], []
        self.addCleanup(lambda: _kill_alive(recorded))
        self.addCleanup(lambda: _kill_groups(groups))
        deadline = time.monotonic() + 60
        while not ready() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        if not ready():
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("premise: batch.py %s never reached the point the case stops it at (rc %s):\n%s%s"
                      % (" ".join(args), proc.returncode, out, err))
        recorded.extend(_descendants(proc.pid))
        groups.extend(_groups_of(recorded))
        os.kill(proc.pid, sig)
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("batch.py was still running 60 s after signal %d:\n%s%s" % (sig, out, err))
        return proc.returncode, out, err

    def planned(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")

    def test_assembles_worktree_add_killed_at_the_bound_leaves_nothing_and_the_next_assemble_passes(self):
        """assemble's git worktree add -B of the batch branch waits on the FIFO until the bound (3 s here) and is ended
        with SIGTERM to its group: assemble is refused (exit 1) naming the call, no worktree is left registered and the
        half-made worktree is gone, and once the FIFO is gone the next assemble passes. Before this change the group got
        SIGKILL: the registration stayed locked ("initializing") with an index.lock in it, and the next assemble failed
        on that lock (probe p8 of the verify pass at the wf_3b100f5e-b38 build)."""
        fx = self.fx
        self.planned()
        restore = self.fifo_at("info/exclude")
        rc, out, err = self.bounded("assemble", "b1", planted=["worktree add --quiet -B batch/b1 "])
        restore()
        self.assertEqual(rc, 1, out + err)
        self.assertIn("batch: git worktree add --quiet -B batch/b1 %s " % fx.wt("b1"), err)
        self.assertIn(" in %s did not end within 3 s and was killed" % fx.dev, err)
        self.assertEqual(self.registrations(), {}, "no worktree registration is left, locked or not")
        self.assertFalse(os.path.lexists(fx.wt("b1")), "the half-made worktree is gone")
        fx.ok("assemble", "b1")

    def test_a_stop_during_assembles_worktree_add_leaves_nothing_and_the_next_assemble_passes(self):
        """SIGTERM reaches batch.py once assemble's git worktree add has made the batch worktree's registration (its
        locked file is there) and waits on the FIFO: Stopped ends the add with SIGTERM to its group, git removes the
        registration and the half-made worktree, batch.py exits 143, and once the FIFO is gone the next assemble passes.
        Before this change the group got SIGKILL: the registration stayed locked with an index.lock in it, and the next
        assemble failed on that lock (probe p9 of the verify pass at the wf_3b100f5e-b38 build, there with SIGTERM
        during a slow checkout)."""
        fx = self.fx
        self.planned()
        locked = os.path.join(fx.dev, ".git", "worktrees", os.path.basename(fx.wt("b1")), "locked")
        restore = self.fifo_at("info/exclude")
        rc, out, err = self.stop_when(lambda: os.path.exists(locked), "assemble", "b1")
        restore()
        self.assertEqual(rc, 128 + signal.SIGTERM, out + err)
        self.assertIn("batch: stopped by signal %d;" % signal.SIGTERM, err)
        self.assertEqual(self.registrations(), {}, "no worktree registration is left, locked or not")
        self.assertFalse(os.path.lexists(fx.wt("b1")), "the half-made worktree is gone")
        fx.ok("assemble", "b1")

    def with_a_ledger(self):
        """Batch b1 assembled and swept from a main that carries the ledger script, so verify runs its ledger check in a
        temporary worktree; returns the registrations then (the batch worktree's alone)."""
        fx = self.fx
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": FAKE_LEDGER}, "ledger migration")
        self.assembled()
        before = self.registrations()
        self.assertEqual(before, {os.path.basename(fx.wt("b1")): None}, "premise: the batch worktree alone is registered")
        return before

    def test_the_ledger_checks_worktree_add_killed_at_the_bound_leaves_no_registration(self):
        """verify's ledger check adds a detached worktree of the batch branch, and the add waits on the FIFO until the
        bound (3 s here): verify is refused (exit 1) naming the add, whose group got SIGTERM first, so git removed its
        registration; the check's finally removes the directory holding the tree, and only the batch worktree stays
        registered. Before this change the group got SIGKILL, the finally's git worktree remove --force refused the
        locked registration (its check=False hid the refusal), and the registration stayed locked ("initializing"; probe
        p4 of the verify pass at the wf_3b100f5e-b38 build)."""
        fx = self.fx
        before = self.with_a_ledger()
        restore = self.fifo_at("info/exclude")
        rc, out, err = self.bounded("verify", "b1", "--no-fetch", planted=["worktree add --quiet --detach "])
        restore()
        self.assertEqual(rc, 1, out + err)
        m = re.search(r"^batch: git worktree add --quiet --detach (\S+) refs/heads/batch/b1 in %s did not end within 3 s and was "
                      r"killed$" % re.escape(fx.dev), err, re.M)
        self.assertIsNotNone(m, err)
        self.assertFalse(os.path.lexists(os.path.dirname(m.group(1))), "the directory holding the tree is gone")
        self.assertEqual(self.registrations(), before, "the add's registration is gone, locked or not")

    def test_a_stop_during_the_ledger_checks_worktree_add_leaves_no_registration(self):
        """SIGTERM reaches batch.py once the ledger check's worktree add has made its registration (its locked file is
        there) and waits on the FIFO: Stopped ends the add with SIGTERM to its group, git removes the registration,
        batch.py exits 143, and only the batch worktree stays registered. Before this change the group got SIGKILL and
        the registration stayed locked ("initializing"; probe p5 of the verify pass at the wf_3b100f5e-b38 build)."""
        fx = self.fx
        before = self.with_a_ledger()
        d = os.path.join(fx.dev, ".git", "worktrees")
        restore = self.fifo_at("info/exclude")
        rc, out, err = self.stop_when(lambda: any(n not in before and os.path.exists(os.path.join(d, n, "locked"))
                                                  for n in os.listdir(d)), "verify", "b1", "--no-fetch")
        restore()
        self.assertEqual(rc, 128 + signal.SIGTERM, out + err)
        self.assertIn("batch: stopped by signal %d;" % signal.SIGTERM, err)
        self.assertEqual(self.registrations(), before, "the add's registration is gone, locked or not")

    def test_a_registration_left_locked_by_a_kill_is_removed_by_the_ledger_checks_cleanup(self):
        """The ledger check's finally removes its worktree with git worktree remove -f -f, which removes a registration a
        killed add left locked, where one --force refuses it: a git that did not end within GIT_TERM_GRACE of the SIGTERM
        gets SIGKILL and leaves its registration locked. Here the SIGTERM is not sent and GIT_TERM_GRACE is 0 (the driver
        below), so the add waiting on the FIFO is ended by SIGKILL at the bound, as such a git would be; verify is
        refused naming the add, and only the batch worktree stays registered. With --force once the registration stayed
        locked ("initializing")."""
        fx = self.fx
        before = self.with_a_ledger()
        driver = BATCH_BOUND_DRIVER.replace("sys.exit(mod.main(argv))\n", """mod.GIT_TERM_GRACE = 0
signal_group = mod._signal_group
mod._signal_group = lambda pgid, sig: None if sig == mod.signal.SIGTERM else signal_group(pgid, sig)
sys.exit(mod.main(argv))
""")
        self.assertNotEqual(driver, BATCH_BOUND_DRIVER, "premise: the driver changed")
        restore = self.fifo_at("info/exclude")
        rc, out, err = self.bounded("verify", "b1", "--no-fetch", driver=driver, planted=["worktree add --quiet --detach "])
        restore()
        self.assertEqual(rc, 1, out + err)
        self.assertRegex(err, r"batch: git worktree add --quiet --detach \S+ refs/heads/batch/b1 in %s did not end within 3 s and was "
                              r"killed" % re.escape(fx.dev))
        self.assertEqual(self.registrations(), before, "the locked registration the SIGKILL left is removed")


    # The start-window pins' driver (the verify pass at the wf_3b100f5e-b38 build, its code finding 2): it loads
    # batch.py (argv[1]), installs its stop handlers as main does (SIGHUP's handler set to the default and SIGINT's to
    # Python's own first, as a process started from a terminal has them), and makes subprocess.Popen send the signal
    # argv[3] to this process right after a process it starts is started (each one, or with argv[5] only one whose
    # program's name is that), so the signal arrives after the start and before the call is inside the try that ends the
    # process: the window the verify pass measured. The call (argv[2]) is run_git or run_tool, _run (gh's runner, over
    # sleepy), excuse_contradiction (scripts/sweep.py's git, through sweep_reader's module), or main with the rest of
    # argv (bisect's command; the closing check wf_fb19febe-36b, its item 4). It prints the started process's pid, then
    # what the call raised (or main's exit status).
    START_WINDOW_DRIVER = r"""
import importlib.util, os, signal, subprocess, sys
spec = importlib.util.spec_from_file_location("batch_tool_window", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
which, sig, where = sys.argv[2], int(sys.argv[3]), sys.argv[4]
only = sys.argv[5] if len(sys.argv) > 5 else ""
signal.signal(signal.SIGHUP, signal.SIG_DFL)
signal.signal(signal.SIGINT, signal.default_int_handler)
if which != "main":
    mod.install_stop_handlers({})
real = subprocess.Popen
class SignalledPopen(real):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        argv = args[0] if args else kwargs["args"]
        if not only or os.path.basename(argv[0]) == only:
            print("started %d" % self.pid, flush=True)
            os.kill(os.getpid(), sig)
subprocess.Popen = SignalledPopen
repo = mod.GitRepo(where, None, None, os.path.dirname(where))
try:
    if which == "run_git":
        mod.run_git(["status"], where, repo=repo)
    elif which == "run_tool":
        mod.run_tool(["git", "status"], where, repo=repo)
    elif which == "_run":
        mod._run([os.path.join(where, "bin", "sleepy")], cwd=where)
    elif which == "excuse":
        mod.excuse_contradiction(where, mod.sweep_reader(), {}, "HEAD")
    else:
        print("main %d" % mod.main(sys.argv[6:]), flush=True)
        sys.exit(0)
    print("returned", flush=True)
except mod.Stopped as e:
    print("Stopped %d" % e.signum, flush=True)
except KeyboardInterrupt:
    print("KeyboardInterrupt", flush=True)
"""

    def window(self, which, sig, where, env, only="", argv=(), pids=None):
        """START_WINDOW_DRIVER over `which` in `where` with `env`, under a 60 s watchdog: (the output's lines, the pids it
        started and the fake recorded in `pids`, stdout and stderr). The pids are killed on the way out when still alive."""
        if pids and os.path.exists(pids):
            os.remove(pids)
        script = os.path.join(self.fx.dev, "scripts", "batch.py") if which == "main" else str(SCRIPTS / "batch.py")
        p = subprocess.Popen([sys.executable, "-c", self.START_WINDOW_DRIVER, script, which, str(int(sig)), where, only,
                              *argv], cwd=self.fx.tmp, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(lambda: p.poll() is None and kill_tree(p.pid))
        recorded = []
        self.addCleanup(lambda: _kill_alive(recorded))
        try:
            out, err = p.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            out, err = p.communicate()
            self.fail("the driver was still running after 60 s:\n%s%s" % (out, err))
        lines = out.splitlines()
        recorded.extend([int(x.split()[1]) for x in lines if x.startswith("started ")] + (_recorded_pids(pids) if pids else []))
        return lines, recorded, out, err

    def assert_gone(self, pids, what):
        """Every one of `pids` has exited within 10 s (Linux; off it, with no /proc to read, nothing is checked)."""
        if not os.path.isdir("/proc"):
            return
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and any(_proc_alive(x) for x in pids):
            time.sleep(0.05)
        self.assertEqual([x for x in pids if _proc_alive(x)], [], what)

    def test_a_stop_that_arrives_as_gh_or_the_excuse_rules_git_starts_ends_that_process(self):
        """The closing check wf_fb19febe-36b, its item 4(a) and (b): SIGTERM, SIGHUP or SIGINT arrives right after _run
        has started its process (gh's runner; here sleepy, which execs sleep 300) or the excuse rule's git has started
        (scripts/sweep.py's run_git, in the module sweep_reader loads; a git first on PATH that starts a child and
        waits), before the call is inside the try that ends it (START_WINDOW_DRIVER). The stop is held until that try
        and raised there as Stopped: _run's process is ended with its group (a session of its own since the 13:24Z
        ruling of 2026-10-02 on PR 926, its item 2), and the git with its group, its child included. Before this change
        _run started gh through subprocess.run, which raised the stop inside the start and never killed the process, and
        the excuse rule's run_git held under sweep.py's own hold, which batch.py's handlers do not read, so the stop was
        raised inside the start there too: each process ran on after the call (the closing check's lens 2 and critic
        findings). Red under mRunUnheld and mNoBind."""
        tmp = tempfile.mkdtemp(prefix="batchwin-")
        self.addCleanup(shutil.rmtree, tmp, True)
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        os.makedirs(os.path.join(tmp, ".git"))              # find_repo's discovery is the excuse rule's first git
        pids = os.path.join(tmp, "pids")
        with open(os.path.join(bindir, "git"), "w") as f:
            f.write("#!/bin/sh\nsleep 300 &\necho $$ $! > %s.tmp && mv %s.tmp %s\nwait\n" % (pids, pids, pids))
        with open(os.path.join(bindir, "sleepy"), "w") as f:
            f.write("#!/bin/sh\nexec sleep 300\n")
        for name in ("git", "sleepy"):
            os.chmod(os.path.join(bindir, name), 0o755)
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
        for which in ("_run", "excuse"):
            for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
                raised = "Stopped %d" % sig
                with self.subTest(call=which, signal=sig):
                    lines, recorded, out, err = self.window(which, sig, tmp, env, pids=pids)
                    if which == "excuse":
                        deadline = time.monotonic() + 10    # the git's pids, written once it runs
                        while time.monotonic() < deadline and not _recorded_pids(pids) and any(_proc_alive(x) for x in recorded):
                            time.sleep(0.05)
                        recorded.extend(_recorded_pids(pids))
                    self.assertEqual(len([x for x in lines if x.startswith("started ")]), 1, out + err)
                    self.assertEqual(lines[-1], raised, out + err)
                    self.assert_gone(recorded, "the process the call started, and any child of it, are gone")

    def test_a_stop_that_arrives_as_bisects_command_starts_ends_that_command(self):
        """The closing check wf_fb19febe-36b, its item 4(a), through main: bisect b1 over the two-member chain, with a
        command that waits (sleepy, which execs sleep 300, its output to /dev/null); SIGTERM, SIGHUP or SIGINT arrives right after the command
        has started at the tip (START_WINDOW_DRIVER, only for sleepy's start). The stop is held until run_command is
        inside the try that ends the command and raised there: the command is killed, and batch.py exits 128 plus the
        signal's number, as for any stop. Before this change bisect started its
        command through subprocess.run, which raised the stop inside the start and never killed the command: batch.py
        exited 143 and the command ran on. Red under mBisectUnheld."""
        fx = self.fx
        tip, _merge_101 = self.bisect_chain()
        bindir = os.path.join(fx.tmp, "window-bin")
        os.makedirs(bindir)
        with open(os.path.join(bindir, "sleepy"), "w") as f:
            # its output away from the driver's pipes, which a command left running would otherwise hold open
            f.write("#!/bin/sh\nexec sleep 300 >/dev/null 2>&1\n")
        os.chmod(os.path.join(bindir, "sleepy"), 0o755)
        env = dict(fx.env, PATH=bindir + os.pathsep + fx.env["PATH"])
        for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            said = "main %d" % (128 + sig)
            with self.subTest(signal=sig):
                lines, recorded, out, err = self.window("main", sig, fx.tmp, env, only="sleepy",
                                                        argv=("bisect", "b1", "--", "sleepy"))
                self.assertEqual(len(recorded), 1, "premise: the command started once:\n" + out + err)
                self.assertEqual(lines[-1], said, out + err)
                self.assert_gone(recorded, "the command bisect started is gone")
                self.assertEqual(fx._git("rev-parse", "HEAD", cwd=fx.wt("b1")), tip, "the batch worktree is still at the tip")

    # The group pin's driver (the 13:24Z ruling of 2026-10-02 on PR 926, its item 2): it loads batch.py (argv[1]),
    # installs its stop handlers as main does (SIGHUP's handler set to the default and SIGINT's to Python's own first, as
    # a process started from a terminal has them), and runs _run (gh's runner) or run_command (bisect's command), argv[2],
    # over the program argv[3] in the directory argv[4]. It prints what the call raised, or "returned".
    GROUP_DRIVER = r"""
import importlib.util, signal, sys
spec = importlib.util.spec_from_file_location("batch_tool_group", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
which, prog, where = sys.argv[2:5]
signal.signal(signal.SIGHUP, signal.SIG_DFL)
signal.signal(signal.SIGINT, signal.default_int_handler)
mod.install_stop_handlers({})
try:
    if which == "_run":
        mod._run([prog], cwd=where)
    else:
        mod.run_command([prog], where)
    print("returned", flush=True)
except mod.Stopped as e:
    print("Stopped %d" % e.signum, flush=True)
except KeyboardInterrupt:
    print("KeyboardInterrupt", flush=True)
"""
    # The program the group pin runs as gh or as bisect's command: it starts a git that reads the configuration of the
    # repository GROUP_REPO, whose config is a FIFO no process writes, so that git waits, as gh's own git reading the
    # clone's remotes waits on a FIFO planted there; then it writes its own pid and that git's to GROUP_PIDS and waits for
    # the git. Its own output and the git's go to /dev/null, so neither, left running, holds the driver's pipes:
    # run_command's process inherits the driver's stdout and stderr, and with a stop that no longer ended that process
    # (_held_wait catching Exception alone) the waiter held them after the driver exited, so the watchdog's last read of
    # the driver's output never ended (the verify pass at the build of the 13:24Z ruling, its code finding 2).
    GROUP_WAITER = r"""#!/bin/sh
exec >/dev/null 2>&1
git -C "$GROUP_REPO" config --get remote.origin.url >/dev/null 2>&1 &
echo $$ $! > "$GROUP_PIDS.tmp" && mv "$GROUP_PIDS.tmp" "$GROUP_PIDS"
wait
"""

    def test_a_stop_while_gh_or_bisects_command_waits_ends_its_group_the_git_it_started_included(self):
        """The 13:24Z ruling of 2026-10-02 on PR 926, its item 2: _run (gh's runner) and run_command (bisect's command)
        start their process in a session of its own and, on a stop, end it with its process group (_held_wait,
        _end_group), as run_tool does. The process (GROUP_WAITER) has started a git that waits on the FIFO at its
        repository's config; once both have started, SIGTERM, SIGHUP or SIGINT reaches the driver (GROUP_DRIVER), the
        call raises Stopped, and within 10 s neither the process nor its git is left. Before this change both calls
        started their process in batch.py's own group and killed it alone: the git ran on after the driver exited,
        blocked on the FIFO (the focused re-check wf_e3f48b16-6ec, 12 of 12 cases). Neither call has a bound, so a stop
        is the one way either is ended early. Each driver runs in a session of its own under a 60 s watchdog, and the
        pids the waiter recorded are killed when still alive before the watchdog's last read of the driver's output, and
        again on the way out, since a driver that has exited has no descendants left for kill_tree to find."""
        tmp = tempfile.mkdtemp(prefix="batchgroup-")
        self.addCleanup(shutil.rmtree, tmp, True)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        repo = os.path.join(tmp, "repo")
        subprocess.run(["git", "init", "-q", repo], env=env, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        config = os.path.join(repo, ".git", "config")
        os.remove(config)
        os.mkfifo(config)
        self.addCleanup(_release_fifo, config)
        waiter = os.path.join(tmp, "waiter")
        with open(waiter, "w") as f:
            f.write(self.GROUP_WAITER)
        os.chmod(waiter, 0o755)
        pids = os.path.join(tmp, "pids")
        env.update(GROUP_REPO=repo, GROUP_PIDS=pids)
        for which in ("_run", "run_command"):
            for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
                with self.subTest(call=which, signal=sig):
                    if os.path.exists(pids):
                        os.remove(pids)
                    p = subprocess.Popen([sys.executable, "-c", self.GROUP_DRIVER, str(SCRIPTS / "batch.py"), which, waiter,
                                          tmp], cwd=tmp, env=env, text=True, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
                    self.addCleanup(lambda p=p: p.poll() is None and kill_tree(p.pid))
                    recorded = []
                    self.addCleanup(_kill_alive, recorded)
                    deadline = time.monotonic() + 60
                    while not _recorded_pids(pids) and p.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.01)
                    recorded.extend(_recorded_pids(pids))
                    if len(recorded) != 2:
                        kill_tree(p.pid)
                        _kill_alive(recorded)
                        out, err = p.communicate()
                        self.fail("premise: the waiter never recorded itself and its git (rc %s):\n%s%s"
                                  % (p.returncode, out, err))
                    os.kill(p.pid, sig)
                    try:
                        out, err = p.communicate(timeout=60)
                    except subprocess.TimeoutExpired:
                        kill_tree(p.pid)
                        _kill_alive(recorded)
                        out, err = p.communicate()
                        self.fail("the driver was still running 60 s after signal %d:\n%s%s" % (sig, out, err))
                    self.assertEqual(out.splitlines()[-1:], ["Stopped %d" % sig], out + err)
                    self.assert_gone(recorded, "the process the call started, and the git it started, are gone")

    # The terminal pin's driver: started in a session of its own with a pty's slave as its stdin, stdout and stderr, it
    # makes that pty its controlling terminal with its own group in the foreground, as a shell does for a command typed
    # at it, and writes to argv[4] + ".premise" whether it is; then it loads batch.py (argv[1]), installs its stop
    # handlers as main does, runs run_command over the shell text argv[3] in argv[2], and writes the exit status to
    # argv[4] (whole, by a rename).
    PTY_DRIVER = r"""
import fcntl, importlib.util, os, signal, sys, termios
fcntl.ioctl(0, termios.TIOCSCTTY, 0)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
os.tcsetpgrp(0, os.getpgrp())
signal.signal(signal.SIGTTOU, signal.SIG_DFL)
signal.signal(signal.SIGTTIN, signal.SIG_DFL)
with open(sys.argv[4] + ".premise", "w") as f:
    f.write("%s\n" % (os.tcgetpgrp(0) == os.getpgrp()))
spec = importlib.util.spec_from_file_location("batch_tool_pty", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.install_stop_handlers({})
rc = mod.run_command(["sh", "-c", sys.argv[3]], sys.argv[2])
with open(sys.argv[4] + ".tmp", "w") as f:
    f.write("%d\n" % rc)
os.replace(sys.argv[4] + ".tmp", sys.argv[4])
"""
    # The command the terminal pin runs: it writes its pid to PTY_PIDS (whole, by a rename), reads a line from its stdin,
    # the terminal, and writes that line to PTY_GOT.
    PTY_COMMAND = ('echo $$ > "$PTY_PIDS.tmp" && mv "$PTY_PIDS.tmp" "$PTY_PIDS"; read line; '
                   'printf "%s\\n" "$line" > "$PTY_GOT"')

    def test_bisects_command_reads_the_terminal_batch_py_runs_in_without_being_stopped(self):
        """The 13:24Z ruling of 2026-10-02 on PR 926, its item 2, as run_command has it: bisect's command starts in a
        session of its own, not only in a process group of its own (the verify pass at the build of that ruling, its
        code finding 3). batch.py runs here with a pty as its controlling terminal and its group in the foreground
        (PTY_DRIVER), and the command's stdin is that terminal; the command reads a line from it, which the test types
        once the command has started, and run_command returns 0 with the line read. In a group of its own in batch.py's
        session (the mutant mRunCommandGroupOnly, process_group=0 for start_new_session=True) the command is a
        background job of that terminal: its read stops it (SIGTTIN), batch.py's wait never returns, and this case
        fails after 30 s, killing the command while batch.py, its parent, has not reaped it (so the pid is still the
        command's), then batch.py."""
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="batchpty-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        pids, got, rc_file = (os.path.join(tmp, x) for x in ("pids", "got", "rc"))
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        try:
            p = subprocess.Popen([sys.executable, "-c", self.PTY_DRIVER, str(SCRIPTS / "batch.py"), tmp, self.PTY_COMMAND,
                                  rc_file], env=dict(os.environ, PTY_PIDS=pids, PTY_GOT=got), stdin=slave, stdout=slave,
                                 stderr=slave, start_new_session=True)
        finally:
            os.close(slave)
        self.addCleanup(lambda: p.poll() is None and (p.kill(), p.wait()))
        recorded = []
        self.addCleanup(_kill_alive, recorded)
        said = []

        def drain(seconds, until):
            """Read what the terminal shows (the driver's output and the echo of what is typed) until `until()` holds or
            `seconds` pass; whether it holds."""
            deadline = time.monotonic() + seconds
            while not until() and time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:              # EIO once no process holds the slave (Linux)
                        chunk = b""
                    said.append(chunk.decode(errors="replace"))
                    if not chunk:
                        time.sleep(0.05)
            return until()

        if not drain(60, lambda: os.path.exists(pids) or p.poll() is not None) or not os.path.exists(pids):
            self.fail("premise: the command never started (driver rc %s):\n%s" % (p.poll(), "".join(said)))
        recorded.extend(_recorded_pids(pids))
        with open(rc_file + ".premise") as f:
            self.assertEqual(f.read(), "True\n", "premise: the pty is batch.py's controlling terminal, its group in the "
                             "foreground")
        os.write(master, b"hello\n")
        if not drain(30, lambda: os.path.exists(rc_file)):
            state = "unknown"
            try:
                with open("/proc/%d/stat" % recorded[0]) as f:
                    state = f.read().rsplit(")", 1)[1].split()[0]
            except (OSError, IndexError):
                pass
            if p.poll() is None:
                os.kill(recorded[0], signal.SIGKILL)
            self.fail("bisect's command had not read the terminal 30 s after the line was typed (its state %s; T is "
                      "stopped, as by SIGTTIN):\n%s" % (state, "".join(said)))
        p.wait(timeout=60)
        with open(got) as f, open(rc_file) as g:
            self.assertEqual((f.read(), g.read()), ("hello\n", "0\n"), "".join(said))

    def test_a_stop_that_arrives_as_run_git_or_run_tool_starts_its_process_ends_that_process(self):
        """The verify pass at the wf_3b100f5e-b38 build, its code finding 2: SIGTERM, SIGHUP or SIGINT arrives right
        after run_git or run_tool has started its process (a git first on PATH that starts a child and waits) and before
        the call is inside the try that ends it (START_WINDOW_DRIVER). The stop is held until that try, raised there,
        and the process and its child are ended with its group; the call raises Stopped. Before this change the stop was
        raised as it arrived, outside that try: the call raised it with the git and its child still running, and they
        ran on after the tool exited (9 of 60 SIGTERMs in the verify pass's measurement)."""
        tmp = tempfile.mkdtemp(prefix="batchwin-")
        self.addCleanup(shutil.rmtree, tmp, True)
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        pids = os.path.join(tmp, "pids")
        with open(os.path.join(bindir, "git"), "w") as f:
            f.write("#!/bin/sh\nsleep 300 &\necho $$ $! > %s.tmp && mv %s.tmp %s\nwait\n" % (pids, pids, pids))
        os.chmod(os.path.join(bindir, "git"), 0o755)
        env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""))
        cases = (("run_git", signal.SIGTERM, "Stopped %d" % signal.SIGTERM),
                 ("run_git", signal.SIGHUP, "Stopped %d" % signal.SIGHUP),
                 ("run_git", signal.SIGINT, "Stopped %d" % signal.SIGINT),
                 ("run_tool", signal.SIGTERM, "Stopped %d" % signal.SIGTERM),
                 ("run_tool", signal.SIGINT, "Stopped %d" % signal.SIGINT))
        for which, sig, raised in cases:
            with self.subTest(call=which, signal=sig):
                if os.path.exists(pids):
                    os.remove(pids)
                p = subprocess.Popen([sys.executable, "-c", self.START_WINDOW_DRIVER, str(SCRIPTS / "batch.py"), which,
                                      str(int(sig)), tmp], env=env, text=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
                self.addCleanup(lambda p=p: p.poll() is None and kill_tree(p.pid))
                recorded = []
                self.addCleanup(lambda r=recorded: _kill_alive(r))
                try:
                    out, err = p.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    kill_tree(p.pid)
                    out, err = p.communicate()
                    self.fail("the driver was still running after 60 s:\n%s%s" % (out, err))
                lines = out.splitlines()
                started = [int(x.split()[1]) for x in lines if x.startswith("started ")]
                recorded.extend(started + _recorded_pids(pids))
                self.assertEqual(len(started), 1, out + err)
                self.assertEqual(lines[-1], raised, out + err)
                if not os.path.isdir("/proc"):
                    continue                     # no /proc to tell a live process by (macOS): what the call raised alone
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and any(_proc_alive(x) for x in started + _recorded_pids(pids)):
                    time.sleep(0.05)
                recorded.extend(_recorded_pids(pids))
                self.assertEqual([x for x in started + _recorded_pids(pids) if _proc_alive(x)], [],
                                 "the process the call started, and its child, are gone")


    # The TERM grace pins' git, first on PATH: it logs each SIGTERM it gets, with the time (python3's: macOS's date has
    # no %N), to TRAP_LOG and keeps running, and its child ignores SIGTERM (trap '' TERM, kept across the exec), so only
    # a SIGKILL ends either; it writes its pid and the child's to TRAP_PIDS (whole, by a rename) and waits for the child
    # for as long as the child lives.
    TERM_IGNORING_GIT = r"""#!/bin/sh
trap 'echo "TERM $(python3 -c "import time; print(time.time())")" >> "$TRAP_LOG"' TERM
(trap '' TERM; exec sleep 300) &
child=$!
echo $$ $child > "$TRAP_PIDS.tmp" && mv "$TRAP_PIDS.tmp" "$TRAP_PIDS"
while kill -0 $child 2>/dev/null; do wait $child; done
"""
    # The TERM grace pins' driver: it loads batch.py (argv[1]), sets GIT_BOUND and GIT_TERM_GRACE to argv[3] and argv[4]
    # seconds, calls run_git or run_tool (argv[2]) in argv[5] and prints what it raised, with the times the call started
    # and ended.
    TERM_GRACE_DRIVER = r"""
import importlib.util, os, sys, time
spec = importlib.util.spec_from_file_location("batch_tool_grace", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
which, where = sys.argv[2], sys.argv[5]
mod.GIT_BOUND, mod.GIT_TERM_GRACE = int(sys.argv[3]), int(sys.argv[4])
repo = mod.GitRepo(where, None, None, os.path.dirname(where))
t0 = time.time()
try:
    if which == "run_git":
        mod.run_git(["status"], where, repo=repo)
    else:
        mod.run_tool(["git", "status"], where, repo=repo)
    print("returned", flush=True)
except mod.GitBound as e:
    print("GitBound %.3f %.3f %s" % (t0, time.time(), e), flush=True)
"""

    def test_a_process_that_ignores_sigterm_is_killed_after_the_term_grace(self):
        """The closing check wf_fb19febe-36b, its item 3: a process run_git or run_tool ends at the bound gets SIGTERM with
        its group, and what is left of the group GIT_TERM_GRACE seconds later gets SIGKILL (_end_group). Here GIT_BOUND
        is 2 s and the grace 2 s (TERM_GRACE_DRIVER), and the process (TERM_IGNORING_GIT, as git for run_git and as the
        command for run_tool) logs the SIGTERM and keeps running, with a child that ignores it: GitBound is raised
        between 4 s and 9 s after the call started, the SIGTERM was logged after the bound and before the raise, and the
        process and its child are both gone. With the SIGKILL dropped (the mutant mNoGraceKillBatch, `pass` in its place)
        the call waited without end on the process, and the case fails at its 30 s watchdog, by name, with the recorded
        pids killed. Before this pin only test_a_registration_left_locked_by_a_kill_is_removed_by_the_ledger_checks_cleanup
        reached the SIGKILL, with the SIGTERM suppressed and no grace."""
        bound, grace, slack = 2, 2, 5
        tmp = tempfile.mkdtemp(prefix="batchgrace-")
        self.addCleanup(shutil.rmtree, tmp, True)
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        with open(os.path.join(bindir, "git"), "w") as f:
            f.write(self.TERM_IGNORING_GIT)
        os.chmod(os.path.join(bindir, "git"), 0o755)
        for which in ("run_git", "run_tool"):
            with self.subTest(call=which):
                log, pids = os.path.join(tmp, which + ".log"), os.path.join(tmp, which + ".pids")
                env = dict(os.environ, PATH=bindir + os.pathsep + os.environ.get("PATH", ""), TRAP_LOG=log, TRAP_PIDS=pids)
                p = subprocess.Popen([sys.executable, "-c", self.TERM_GRACE_DRIVER, str(SCRIPTS / "batch.py"), which,
                                      str(bound), str(grace), tmp], env=env, text=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
                self.addCleanup(lambda p=p: p.poll() is None and kill_tree(p.pid))
                recorded = []
                self.addCleanup(lambda r=recorded: _kill_alive(r))
                try:
                    out, err = p.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    recorded.extend(_recorded_pids(pids))
                    kill_tree(p.pid)
                    _kill_alive(recorded)
                    out, err = p.communicate()
                    self.fail("%s was still waiting 30 s after its call: the process that ignores SIGTERM was not killed "
                              "after the grace:\n%s%s" % (which, out, err))
                recorded.extend(_recorded_pids(pids))
                self.assertEqual(len(recorded), 2, "premise: the process started its child and recorded both:\n" + out + err)
                last = (out.splitlines() or [""])[-1].split(" ", 3)
                self.assertEqual(last[0], "GitBound", out + err)
                t0, t1 = float(last[1]), float(last[2])
                self.assertIn("did not end within %d s and was killed" % bound, last[3])
                self.assertGreaterEqual(t1 - t0, bound + grace, out)
                self.assertLessEqual(t1 - t0, bound + grace + slack, out)
                with open(log) as f:
                    terms = [float(x.split()[1]) for x in f.read().splitlines()]
                self.assertEqual(len(terms), 1, "one SIGTERM, logged by the process that kept running")
                self.assertTrue(t0 + bound <= terms[0] <= t1, (t0, terms, t1))
                if not os.path.isdir("/proc"):
                    continue                     # no /proc to tell a live process by (macOS): what the call raised alone
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and any(_proc_alive(x) for x in recorded):
                    time.sleep(0.05)
                self.assertEqual([x for x in recorded if _proc_alive(x)], [], "the process and its child are gone")


# StopPinsLeaveNothing's mutant of batch.py, written over the fixture's copy: main installs no stop handlers, so SIGTERM
# ends batch.py outright and the process it waits on, in a session of its own, runs on (batch.py before the closing check
# wf_3b100f5e-b38's item 4); and every process batch.py starts is logged by its pid, its group's id for one started in a
# session of its own, to the file STOP_PINS_LOG names.
NO_HANDLER_MUTATION = (("        install_stop_handlers(replaced)\n", "        pass\n"),
                       ('\n\nif __name__ == "__main__":\n', '''


class _LoggedPopen(subprocess.Popen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open(os.environ["STOP_PINS_LOG"], "a") as f:
            f.write("%d\\n" % self.pid)


subprocess.Popen = _LoggedPopen


if __name__ == "__main__":
'''))


def _group_alive(pgid):
    """Whether any process of the process group `pgid` is left."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _kill_groups(pgids):
    for g in pgids:
        if _group_alive(g):
            try:
                os.killpg(g, signal.SIGKILL)
            except OSError:
                pass


# A git first on PATH for BatchGitLimits: past run_git's -c pairs, it leaves the file $SHIM_RAN when set, appends its
# subcommand and the soft address-space limit /proc gives it to the file $SHIM_LOG when set, prints $SHIM_OUT bytes on
# its stdout, or else that limit's line, and, when $SHIM_ON is unset or is its subcommand, what the file $SHIM_SAYS
# holds on its stderr, then exits as $SHIM_ENDS says (any other subcommand exits 0).
LIMITS_GIT = r"""#!/bin/sh
while [ "$1" = "-c" ]; do shift 2; done
if [ -n "$SHIM_RAN" ]; then : > "$SHIM_RAN"; fi
if [ -n "$SHIM_LOG" ]; then
  printf '%s %s\n' "$1" "$(sed -n 's/^Max address space *\([0-9a-z]*\).*/\1/p' /proc/$$/limits)" >> "$SHIM_LOG"
fi
if [ -n "$SHIM_OUT" ]; then head -c "$SHIM_OUT" /dev/zero; else grep '^Max address space' /proc/$$/limits; fi
if [ -n "$SHIM_ON" ] && [ "$1" != "$SHIM_ON" ]; then exit 0; fi
if [ -n "$SHIM_SAYS" ]; then cat "$SHIM_SAYS" >&2; fi
exit ${SHIM_ENDS:-0}
"""


class BatchGitLimits(unittest.TestCase):
    """Round 1 of PR 959, V1, at run_git and run_tool: every git batch.py starts, and every process run_tool starts, runs
    under a memory limit set by the shell that execs it, GIT_MEMORY (1 GiB) or for a call that runs the clone's hooks (a
    push, a commit or a merge) HOOK_MEMORY (16 GiB), or the test process's own lower limit; a shell that cannot set it starts nothing; a failure at it is GitMemory, read as
    scripts/sweep.py reads one (git's own line, first); and output past GIT_OUTPUT_MAX ends the call with GitOutput. A git
    first on PATH (LIMITS_GIT) stands in for git and for a tool. Linux only, where the limit is set."""

    def setUp(self):
        if not sys.platform.startswith("linux"):
            self.skipTest("batch.py sets the memory limit on Linux alone")
        self.tmp = tempfile.mkdtemp(prefix="batch-limits-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        self.git = os.path.join(self.bin, "git")
        with open(self.git, "w") as f:
            f.write(LIMITS_GIT)
        os.chmod(self.git, 0o755)
        self.said = os.path.join(self.tmp, "said")
        self.repo = batch.GitRepo(self.tmp, os.path.join(self.tmp, ".git"), os.path.join(self.tmp, ".git"),
                                  os.path.dirname(self.tmp))

    def env(self, **extra):
        return unittest.mock.patch.dict(os.environ, dict(extra, PATH=self.bin + os.pathsep + os.environ["PATH"]))

    @staticmethod
    def expected(figure):
        """`figure` bytes, or this process's own lower soft or hard RLIMIT_AS, which a child inherits."""
        return min([figure] + [n for n in resource.getrlimit(resource.RLIMIT_AS) if n != resource.RLIM_INFINITY])

    def limit_of(self, said):
        line = next(x for x in said.splitlines() if x.startswith("Max address space"))
        return line.split()[3:5]

    def test_each_git_and_each_tool_process_starts_under_its_memory_limit(self):
        """A git call gets 1 GiB of address space, soft and hard, a push, a commit and a merge 16 GiB (each runs the
        clone's hooks, and a pre-push or pre-commit hook can start gitleaks, which reserves more than 4 GiB as it starts:
        round 2 of PR 959, ruling C, where before only a push had it), a git merge --abort 1 GiB (it runs none of a
        merge's hooks), and a run_tool process 1 GiB, each read from /proc by the process itself; git_memory gives git
        merge --abort what it gives git status, and a merge that is not an abort the hook-sized limit. Before V1 each
        started with no limit ("unlimited"); with git merge --abort among the calls that run hooks, it started under
        16 GiB."""
        with self.env():
            plain = batch.run_git(["status"], self.tmp, repo=self.repo)
            push = batch.run_git(["push", "--quiet", "-u", "origin", "refs/heads/batch/b1"], self.tmp, repo=self.repo)
            commit = batch.run_git(["commit", "--quiet", "--no-edit"], self.tmp, repo=self.repo)
            merge = batch.run_git(["merge", "--no-ff", "--no-edit", "-m", "Merge #1: x", "1" * 40], self.tmp, repo=self.repo)
            abort = batch.run_git(["merge", "--abort"], self.tmp, repo=self.repo)
            tool = batch.run_tool([self.git, "check"], self.tmp, repo=self.repo)
        for what, p, figure in (("git status", plain, 1 << 30), ("git push", push, 16 << 30), ("git commit", commit, 16 << 30),
                                ("git merge", merge, 16 << 30), ("git merge --abort", abort, 1 << 30),
                                ("a tool", tool, 1 << 30)):
            with self.subTest(what=what):
                self.assertEqual(p.returncode, 0, p)
                self.assertEqual(self.limit_of(p.stdout), [str(self.expected(figure))] * 2, p.stdout)
        self.assertEqual(batch.git_memory(["merge", "--abort"]), batch.git_memory(["status"]))
        self.assertEqual(batch.git_memory(["merge", "--no-ff"]), self.expected(16 << 30))

    def test_each_call_that_runs_hooks_comes_after_a_listing_of_the_refs_under_git_memory(self):
        """Round 2 of PR 959, ruling C, item 2: before each call that runs the clone's hooks (a push, a commit, a merge),
        run_git lists the refs with git for-each-ref --format= under GIT_MEMORY (_refs_listed), and a call that runs
        none, git status and git merge --abort among them, comes after nothing; the git first on PATH logs each call's
        subcommand and limit. A listing that fails at the limit is GitMemory naming it and the call it came before,
        which never runs. Red without the listing: each hook-running call was logged alone, and with the failure
        planted on the listing the push ran and nothing was raised. Red with git merge --abort among the calls that run
        hooks: it came after a listing, under 16 GiB."""
        log = os.path.join(self.tmp, "calls")
        plain, hooked = self.expected(1 << 30), self.expected(16 << 30)
        calls = ((["status"], []), (["push", "--quiet", "-u", "origin", "refs/heads/batch/b1"], [("for-each-ref", plain)]),
                 (["commit", "--quiet", "--no-edit"], [("for-each-ref", plain)]),
                 (["merge", "--no-ff", "--no-edit", "-m", "Merge #1: x", "1" * 40], [("for-each-ref", plain)]),
                 (["merge", "--abort"], []))
        for args, before in calls:
            with self.subTest(args=" ".join(args)), self.env(SHIM_LOG=log):
                if os.path.exists(log):
                    os.remove(log)
                batch.run_git(args, self.tmp, repo=self.repo)
                with open(log) as f:
                    got = [tuple(line.split()) for line in f]
                own = hooked if before else plain
                self.assertEqual(got, [(c, str(n)) for c, n in before] + [(args[0], str(own))])
        os.remove(log)
        with open(self.said, "w") as f:
            f.write("fatal: Out of memory, realloc failed\n")
        args = ["push", "--quiet", "-u", "origin", "refs/heads/batch/b1"]
        with self.env(SHIM_LOG=log, SHIM_SAYS=self.said, SHIM_ENDS="128", SHIM_ON="for-each-ref"), \
                self.assertRaises(batch.GitMemory) as cm:
            batch.run_git(args, self.tmp, repo=self.repo)
        size = "%d MiB" % (plain >> 20) if plain % (1 << 20) == 0 else "%d KiB" % (plain >> 10)
        self.assertTrue(str(cm.exception).startswith(
            "batch.py lists the refs under GIT_MEMORY before git %s, which runs the clone's hooks under HOOK_MEMORY: git "
            "for-each-ref --format= in %s reached the %s memory limit (GIT_MEMORY) batch.py sets on it and failed "
            "(fatal: Out of memory, realloc failed)" % (" ".join(args), self.tmp, size)), str(cm.exception))
        with open(log) as f:
            self.assertEqual([line.split()[0] for line in f], ["for-each-ref"], "the push never ran")

    def test_a_shell_that_cannot_set_the_limit_starts_nothing_and_is_a_fail_naming_it(self):
        """A shell whose ulimit -v fails (handed a value it cannot read) execs no git and no tool: run_git and run_tool
        raise a Fail naming the call and LIMIT_FAILED, and the git first on PATH, which leaves a file when run, never
        ran."""
        limits = batch.git_limits()
        broken = limits._LIMITED.replace("ulimit -v %d", "ulimit -v x%d")
        self.assertNotEqual(broken, limits._LIMITED, "premise: the shell's ulimit is the planted text")
        ran = os.path.join(self.tmp, "ran")
        for what, call in (("git", lambda: batch.run_git(["status"], self.tmp, repo=self.repo)),
                           ("tool", lambda: batch.run_tool([self.git, "check"], self.tmp, repo=self.repo))):
            with self.subTest(what=what), self.env(SHIM_RAN=ran), \
                    unittest.mock.patch.object(limits, "_LIMITED", broken):
                with self.assertRaises(batch.Fail) as cm:
                    call()
                self.assertNotIsInstance(cm.exception, batch.GitBound)
                self.assertIn(" in %s did not run: %s, so batch.py did not start it without one" % (self.tmp, limits.LIMIT_FAILED),
                              str(cm.exception))
                self.assertFalse(os.path.exists(ran), "nothing ran")

    def test_a_failure_at_the_limit_is_git_memory_naming_no_regular_ref_file_and_a_quoted_path_is_not(self):
        """A git that dies (128) with git's own out-of-memory line first is GitMemory, naming the call, the limit
        (GIT_MEMORY, or HOOK_MEMORY for a call that runs the clone's hooks) and git's line, and no file of the
        repository that is a regular file of a ref's size: here the loose files of ORIGIN_MAIN_REF and of the batch branch,
        at a rev-list that names both, a fetch from origin and a push of the branch, which until round 2 of PR 959
        (ruling C, item 3) the text named as the files the call read, whatever it had read (_odd_files names the files
        that are not regular or are oversized, pinned by the test after this one); one whose first line quotes a path a
        leg chose, with that line after a newline in it, is a plain failure, as scripts/sweep.py reads it (round 1 of
        PR 959, V2); and a run_tool process that dies so is GitMemory too. Before V1 every one was a plain failure."""
        common = os.path.join(self.tmp, ".git")
        for ref in ("refs/heads/batch/b1", ORIGIN_MAIN_REF):
            path = os.path.join(common, *ref.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("1" * 40 + "\n")
        oom = "fatal: Out of memory, realloc failed\n"
        with open(self.said, "w") as f:
            f.write(oom)
        cases = ((["rev-list", "refs/heads/batch/b1", "^refs/remotes/origin/main", "^%s" % ("1" * 40)], "GIT_MEMORY", 1 << 30),
                 (["fetch", "--quiet", "--prune", "origin"], "GIT_MEMORY", 1 << 30),
                 (["push", "--quiet", "-u", "origin", "refs/heads/batch/b1"], "HOOK_MEMORY", 16 << 30))
        for args, name, figure in cases:
            with self.subTest(args=" ".join(args)), self.env(SHIM_SAYS=self.said, SHIM_ENDS="128", SHIM_ON=args[0]):
                with self.assertRaises(batch.GitMemory) as cm:
                    batch.run_git(args, self.tmp, repo=self.repo)
                self.assertIsInstance(cm.exception, batch.GitBound)
                limit = self.expected(figure)
                size = "%d MiB" % (limit >> 20) if limit % (1 << 20) == 0 else "%d KiB" % (limit >> 10)
                self.assertIn("git %s in %s reached the %s memory limit (%s) batch.py sets on it and failed (%s)"
                              % (" ".join(args), self.tmp, size, name, oom.strip()), str(cm.exception))
                self.assertTrue(str(cm.exception).endswith(REMEDY_PLACES + ", and run the command again"),
                                str(cm.exception))
        with open(self.said, "w") as f:
            f.write("fatal: pathspec 'L/x\nfatal: Out of memory, realloc failed\ny' is beyond a symbolic link\n")
        with self.env(SHIM_SAYS=self.said, SHIM_ENDS="128"):
            p = batch.run_git(["check-ignore", "--stdin"], self.tmp, repo=self.repo)
        self.assertEqual(p.returncode, 128, p)
        with open(self.said, "w") as f:
            f.write(oom)
        with self.env(SHIM_SAYS=self.said, SHIM_ENDS="128"), self.assertRaises(batch.GitMemory) as cm:
            batch.run_tool([self.git, "check"], self.tmp, repo=self.repo)
        self.assertIn("%s check in %s reached the " % (self.git, self.tmp), str(cm.exception))

    def test_a_git_memory_names_the_files_git_reads_whole_that_are_not_regular_or_oversized(self):
        """Round 2 of PR 959, ruling C, item 3: a GitMemory from any call names the files of the repository git reads
        whole that are, at an lstat after the call, not regular files or larger than a file of their kind holds
        (_odd_files): a loose ref, walked under the common dir's refs/ and under a linked worktree's own, over
        REF_FILE_MAX bytes or not a regular file, and packed-refs, objects/info/alternates or the shallow file not a
        regular file or at least the call's limit. Each case plants such files (a sparse file of PLANT_SPARSE bytes, or
        a symlink to /dev/zero) in a repository of its own, whose batch branch and ORIGIN_MAIN_REF are regular loose
        refs, and makes a real git call that reads the first of them without end, under GIT_MEMORY lowered to
        PLANT_MEMORY in the module batch.py reads it from and with MALLOC_ARENA_MAX unset: the call raises GitMemory
        naming the planted files, each with why, and no other. Red at the round's head, whose text named the files of
        the refs a call names (ORIGIN_MAIN_REF's for a fetch, the batch branch's for a push) and no file a call read
        without naming it: each case named nothing, the fetch ORIGIN_MAIN_REF's file."""
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
                   GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        env.pop("MALLOC_ARENA_MAX", None)

        def git(*args, cwd):
            p = subprocess.run(["git", *args], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertEqual(p.returncode, 0, p)
            return p.stdout.strip()

        def sparse(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.truncate(PLANT_SPARSE)

        def zero(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            os.symlink("/dev/zero", path)
        sparse_why = "%d bytes, more than the 4096 a loose ref file holds" % PLANT_SPARSE
        link_why = "a symlink, not a regular file"
        whole_why = "%d bytes, at least the %d MiB limit the call ran under, and git reads it whole" % (
            PLANT_SPARSE, PLANT_MEMORY >> 20)
        listing, history = ["for-each-ref", "--format=%(refname)"], ["rev-list", "-1", "refs/heads/batch/b1"]
        # (case, [(file, plant, why)], the call): the first file is the one the call reads without end; a second is one
        # it does not read, named all the same (git 2.43 dies on a shallow file of zeros, "bad shallow line", and
        # for-each-ref passes over a loose ref that leads to a device, so neither is read without end)
        cases = (("a sparse loose ref", [("refs/tags/planted", sparse, sparse_why)], listing),
                 ("a loose ref that is a symlink to /dev/zero, read by its name",
                  [("refs/tags/planted", zero, link_why)], ["rev-parse", "--verify", "--quiet", "refs/tags/planted"]),
                 ("a sparse packed-refs", [("packed-refs", sparse, whole_why)], listing),
                 ("objects/info/alternates as a symlink to /dev/zero",
                  [("objects/info/alternates", zero, link_why)], history),
                 ("the shallow file as a symlink to /dev/zero, beside a sparse loose ref",
                  [("refs/tags/planted", sparse, sparse_why), ("shallow", zero, link_why)], listing),
                 ("a sparse loose ref of a linked worktree's own", [("refs/bisect/planted", sparse, sparse_why)], listing),
                 ("a sparse loose ref, met by a fetch", [("refs/tags/planted", sparse, sparse_why)],
                  ["fetch", "--quiet", "--prune", "origin"]))
        limits = batch.git_limits()
        for n, (case, plants, args) in enumerate(cases):
            with self.subTest(case=case):
                d = os.path.join(self.tmp, "repo-%d" % n)
                git("init", "-q", d, cwd=self.tmp)
                git("commit", "-q", "--allow-empty", "-m", "seed", cwd=d)
                git("update-ref", "refs/heads/batch/b1", "HEAD", cwd=d)
                git("update-ref", ORIGIN_MAIN_REF, "HEAD", cwd=d)
                common = os.path.join(d, ".git")
                repo, where, gd = batch.GitRepo(d, common, common, self.tmp), d, common
                if "worktree" in case:
                    where = os.path.join(self.tmp, "worktree-%d" % n)
                    git("worktree", "add", "-q", "--detach", where, cwd=d)
                    gd = os.path.join(common, "worktrees", os.path.basename(where))
                    repo = batch.GitRepo(where, gd, common, self.tmp)
                if args[0] == "fetch":
                    git("clone", "-q", "--bare", d, os.path.join(self.tmp, "origin-%d.git" % n), cwd=self.tmp)
                    git("remote", "add", "origin", os.path.join(self.tmp, "origin-%d.git" % n), cwd=d)
                named = []
                for rel, plant, why in plants:
                    planted = os.path.join(gd if rel.startswith("refs/bisect/") else common, *rel.split("/"))
                    plant(planted)
                    named.append("%s (%s)" % (planted, why))
                with unittest.mock.patch.dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"), \
                        unittest.mock.patch.object(limits, "GIT_MEMORY", PLANT_MEMORY), \
                        self.assertRaises(batch.GitMemory) as cm:
                    os.environ.pop("MALLOC_ARENA_MAX", None)
                    batch.run_git(args, where, repo=repo)
                self.assertIn("git %s in %s reached the %d MiB memory limit (GIT_MEMORY)" % (" ".join(args), where,
                                                                                         PLANT_MEMORY >> 20),
                              str(cm.exception))
                self.assertTrue(str(cm.exception).endswith(
                    "; of the files of the repository git reads whole, these are not regular files or hold more than a "
                    "file of their kind does, now (an lstat each after the call, so one can have changed since): %s, "
                    "and run the command again" % ", ".join(named)), str(cm.exception))

    def test_a_git_memory_names_at_most_odd_files_shown_files_and_counts_the_rest(self):
        """A GitMemory names at most ODD_FILES_SHOWN of the files _odd_files gives, in its order, and then how many more
        there are ("and <n> more"), so a clone with many planted files gives an error of bounded length. Here
        _odd_files gives ODD_FILES_SHOWN + 5 files and the git first on PATH dies with git's out-of-memory line: the
        text names the first ODD_FILES_SHOWN, then "and 5 more", and none past the cutoff. Red without the cutoff
        (_limit_met naming every file): all of them named, and no count."""
        shown = batch.ODD_FILES_SHOWN
        odd = ["%s/odd-%02d (a symlink, not a regular file)" % (self.tmp, i) for i in range(shown + 5)]
        with open(self.said, "w") as f:
            f.write("fatal: Out of memory, realloc failed\n")
        with self.env(SHIM_SAYS=self.said, SHIM_ENDS="128", SHIM_ON="status"), \
                unittest.mock.patch.object(batch, "_odd_files", return_value=list(odd)), \
                self.assertRaises(batch.GitMemory) as cm:
            batch.run_git(["status"], self.tmp, repo=self.repo)
        text = str(cm.exception)
        self.assertTrue(text.endswith("(an lstat each after the call, so one can have changed since): %s, and 5 more, "
                                      "and run the command again" % ", ".join(odd[:shown])), text)
        for past in odd[shown:]:
            self.assertNotIn(past, text)

    def test_a_directory_at_a_file_git_reads_whole_is_named_and_one_at_a_loose_refs_path_is_not(self):
        """A directory at one of the files git reads whole for a call (packed-refs, objects/info/alternates and shallow
        in the common dir, and each of GIT_DIR_STATE_FILES in the git dir) is named by _odd_files as a directory, as its
        docstring and docs/batching.md say of a file there that is not a regular file (the closing check at round 3 of
        PR 959, NEW-2). git never reads a directory without end, so one cannot cause a GitMemory, but one beside the
        file that did is named. A directory at the path of a loose ref the call names (refs/heads/batch/b1) is still
        passed over, since the walk of refs/ reads what it holds. Here each of the nine is a directory, written as
        literals, and so is refs/heads/batch/b1: the nine are named, in _odd_files' order, and the loose ref's path is
        not. Red at round 3's head, which passed over a directory at every one of these paths: nothing named. Red too
        with the directory test dropped for every path: the loose ref's directory named as well."""
        gd = os.path.join(self.tmp, ".git")
        whole = ("packed-refs", "objects/info/alternates", "shallow", "COMMIT_EDITMSG", "MERGE_MSG", "MERGE_MODE",
                 "SQUASH_MSG", "MERGE_AUTOSTASH", "BISECT_START")
        for rel in whole + ("refs/heads/batch/b1",):
            os.makedirs(os.path.join(gd, *rel.split("/")))
        self.assertEqual(batch._odd_files(["rev-parse", "--verify", "refs/heads/batch/b1"], self.repo, 1 << 30),
                         ["%s (a directory, not a regular file)" % os.path.join(gd, *rel.split("/")) for rel in whole])

    def test_each_state_file_in_the_git_dir_is_named_when_it_is_not_a_regular_file(self):
        """_odd_files lstats each of GIT_DIR_STATE_FILES in the call's git dir and names one that is not a regular file,
        BISECT_START among them, which no end-to-end test plants (the closing check at round 3 of PR 959, NEW-3; the
        MERGE_AUTOSTASH and MERGE_MSG plant tests check those two through a real GitMemory). Here each of the six,
        written as literals, is a symlink to /dev/zero: each is named as a symlink, in the tuple's order. Red with the
        lstat of MERGE_MSG, MERGE_AUTOSTASH and BISECT_START skipped and the remedy kept (the closing check's mutant
        m5g): those three not named."""
        gd = os.path.join(self.tmp, ".git")
        os.makedirs(gd)
        names = ("COMMIT_EDITMSG", "MERGE_MSG", "MERGE_MODE", "SQUASH_MSG", "MERGE_AUTOSTASH", "BISECT_START")
        for n in names:
            os.symlink("/dev/zero", os.path.join(gd, n))
        self.assertEqual(batch._odd_files([], self.repo, 1 << 30),
                         ["%s (a symlink, not a regular file)" % os.path.join(gd, n) for n in names])

    def test_every_git_call_reads_the_settings_that_keep_its_need_flat_over_the_repositorys_own(self):
        """GIT_SETTINGS on every run_git call, over the repository's own config: the pack window caps, the index read on
        one thread, index-pack and pack-objects on one thread, and no gc or maintenance started on its own (GIT_SETTINGS'
        comment has why each keeps a call's need under the limit). The real git reads each key back through run_git, the
        repository's config setting it otherwise."""
        repo_dir = os.path.join(self.tmp, "repo")
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        subprocess.run(["git", "init", "-q", repo_dir], env=env, check=True)
        want = {"core.packedGitWindowSize": "32m", "core.packedGitLimit": "128m", "core.preloadIndex": "false",
                "index.threads": "false", "pack.threads": "1", "gc.auto": "0", "maintenance.auto": "false"}
        for key in want:
            subprocess.run(["git", "-C", repo_dir, "config", key, "7"], env=env, check=True)
        repo = batch.GitRepo(repo_dir, os.path.join(repo_dir, ".git"), os.path.join(repo_dir, ".git"), self.tmp)
        with unittest.mock.patch.dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"):
            got = {key: batch.run_git(["config", "--get", key], repo_dir, repo=repo).stdout.strip() for key in want}
        self.assertEqual(got, want)

    def test_git_settings_comment_names_batch_pys_own_keys_apart_from_the_sweeps(self):
        """Round 3 of PR 959, regression-1: GIT_SETTINGS' comment says which of its keys are scripts/sweep.py's
        GIT_NEUTRAL_CONFIG's and which are batch.py's own, keys the sweep does not set. Its sentence naming batch.py's
        own ("keys of batch.py's own, which GIT_NEUTRAL_CONFIG does not hold: <key=value>, ... and <key=value>.") lists
        exactly the GIT_SETTINGS pairs whose key GIT_NEUTRAL_CONFIG does not hold, with their values, and every other
        GIT_SETTINGS pair is one of GIT_NEUTRAL_CONFIG's, value and all. Red at the round's head, whose comment put
        pack.threads=1 in its list of GIT_NEUTRAL_CONFIG's keys and named no keys as batch.py's own (the sentence
        absent); red too when a key is added to GIT_SETTINGS that the sweep does not hold and the sentence does not
        name."""
        lines = (SCRIPTS / "batch.py").read_text().splitlines()
        at = next(i for i, line in enumerate(lines) if line.startswith("GIT_SETTINGS = ("))
        block = []
        for line in reversed(lines[:at]):
            if not line.startswith("#"):
                break
            block.insert(0, line[1:].strip())
        comment = " ".join(block)
        m = re.search(r"keys of batch\.py's own, which GIT_NEUTRAL_CONFIG does not hold: (.*?)\.\s", comment)
        self.assertIsNotNone(m, "GIT_SETTINGS' comment names no keys as batch.py's own")
        named = re.split(r",\s*|\s+and\s+", m.group(1))
        pairs = [batch.GIT_SETTINGS[i + 1] for i in range(0, len(batch.GIT_SETTINGS), 2)]
        neutral = dict(sweep.GIT_NEUTRAL_CONFIG)
        own = [p for p in pairs if p.split("=", 1)[0] not in neutral]
        self.assertEqual(named, own)
        self.assertEqual([p for p in pairs if p not in own],
                         ["%s=%s" % (k, neutral[k]) for k in (p.split("=", 1)[0] for p in pairs if p not in own)],
                         "every other GIT_SETTINGS pair is GIT_NEUTRAL_CONFIG's, with its value")

    def test_a_git_a_tool_process_starts_reads_the_settings_after_the_pairs_batch_py_inherited(self):
        """Round 2 of PR 959, ruling B: run_tool's environment carries GIT_SETTINGS as git's environment config, pairs
        numbered after the GIT_CONFIG_COUNT pairs batch.py inherited, which stay (_tool_env), so a git that a run_tool
        process starts reads each setting over the repository's own config and still reads the inherited pairs, a
        setting winning where an inherited pair sets the same key. A shell script stands in for the tool and asks git
        for each key, the repository's config setting each to 7 and two inherited pairs setting test.inherited=yes and
        gc.auto=50: each setting reads back as GIT_SETTINGS has it, written here as literals, and test.inherited reads
        yes, with the inherited count written as 2 and, in subtests, as " 2" and "+2", which git reads as 2 as well. An
        inherited count git refuses as a number ("two", "2 ") is a Fail naming it, and the tool never starts. Red
        without the environment (run_tool at the round's head): every setting read back 7, and the refused count
        started the tool; red under a count pattern without its leading blanks and sign: " 2" and "+2" refused."""
        repo_dir = os.path.join(self.tmp, "repo")
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        subprocess.run(["git", "init", "-q", repo_dir], env=env, check=True)
        want = {"core.packedGitWindowSize": "32m", "core.packedGitLimit": "128m", "core.preloadIndex": "false",
                "index.threads": "false", "pack.threads": "1", "gc.auto": "0", "maintenance.auto": "false"}
        for key in want:
            subprocess.run(["git", "-C", repo_dir, "config", key, "7"], env=env, check=True)
        repo = batch.GitRepo(repo_dir, os.path.join(repo_dir, ".git"), os.path.join(repo_dir, ".git"), self.tmp)
        reader = os.path.join(self.tmp, "read-back.sh")
        with open(reader, "w") as f:
            f.write('#!/bin/sh\nfor k in "$@"; do printf \'%s=%s\\n\' "$k" "$(git config --get "$k")"; done\n')
        os.chmod(reader, 0o755)
        for count in ("2", " 2", "+2"):
            with self.subTest(count=count):
                inherited = dict(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_COUNT=count,
                                 GIT_CONFIG_KEY_0="test.inherited", GIT_CONFIG_VALUE_0="yes",
                                 GIT_CONFIG_KEY_1="gc.auto", GIT_CONFIG_VALUE_1="50")
                with unittest.mock.patch.dict(os.environ, inherited):
                    p = batch.run_tool([reader, *want, "test.inherited"], repo_dir, repo=repo)
                self.assertEqual(p.returncode, 0, p)
                self.assertEqual(dict(line.split("=", 1) for line in p.stdout.splitlines()),
                                 {**want, "test.inherited": "yes"})
        ran = os.path.join(self.tmp, "ran")
        for count in ("two", "2 "):
            with self.subTest(refused=count):
                with unittest.mock.patch.dict(os.environ, GIT_CONFIG_COUNT=count), self.assertRaises(batch.Fail) as cm:
                    batch.run_tool(["/bin/sh", "-c", ': > "$0"', ran], repo_dir, repo=repo)
                self.assertNotIsInstance(cm.exception, batch.GitBound)
                self.assertIn("GIT_CONFIG_COUNT in batch.py's environment is %r, which git refuses as a count" % count,
                              str(cm.exception))
                self.assertFalse(os.path.exists(ran), "nothing ran")

    def test_a_fetch_that_runs_index_pack_does_so_on_one_thread_within_a_limit_its_threads_would_exceed(self):
        """Round 2 of PR 959, ruling A: GIT_SETTINGS' pack.threads=1 holds index-pack, which a fetch of 100 objects or
        more runs (git's fetch.unpackLimit), to one thread. git's own count is one thread per two CPUs, at most 20, which
        it reaches at 40 CPUs, and each thread maps a stack and a malloc arena, so without the setting a fetch's need grew
        with the machine (GIT_SETTINGS' comment has the figures for a stale clone of this project). Here batch.py's own
        fetch brings 120 commits of a rewritten file, 360 objects, most of them deltas, from an origin on disk, under
        the memory limit lowered to PLANT_MEMORY in the module batch.py reads it from, with MALLOC_ARENA_MAX unset (a
        shell can inherit it, and a cap on the arenas hides the cost of the threads): once with the clone's config as
        git leaves it, so index-pack would start git's own count on this machine, and once with the clone's own
        pack.threads at 20, git's count from 40 CPUs, which GIT_SETTINGS overrides. Each fetch writes the origin's tip
        at ORIGIN_MAIN_REF, through one pack, so index-pack ran. Red without the setting: index-pack failed at the lowered
        limit (its first line "fatal: unable to create thread: Resource temporarily unavailable", the fetch exiting 128,
        a Fail) in the second case on any machine, and in the first on a machine of 40 or more CPUs; on a 60-CPU machine
        this fetch needed 364 MiB with the clone's 20 and 368 MiB with git's own count, and 24 MiB with the setting
        (the smallest limit it passed at, to 4 MiB; git 2.43.0, 2026-10-04)."""
        if not sys.platform.startswith("linux"):
            self.skipTest("batch.py sets the memory limit on Linux alone")
        work = os.path.join(self.tmp, "fetch")
        os.makedirs(work)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        env.pop("MALLOC_ARENA_MAX", None)

        def git(*args, cwd=work, data=None):
            p = subprocess.run(["git", *args], cwd=cwd, env=env, input=data, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
            self.assertEqual(p.returncode, 0, p)
            return p.stdout.decode().strip()
        author, bare, stale = (os.path.join(work, d) for d in ("author", "origin.git", "stale"))
        git("init", "-q", author)
        lines = ["line %04d %s" % (i, "abcdefghij" * 6) for i in range(1000)]
        stream = []
        for c in range(121):
            for k in range(5):
                lines[(c * 37 + k * 211) % len(lines)] = "edit %03d %d %s" % (c, k, "klmnop" * 10)
            body, message = ("\n".join(lines) + "\n").encode(), b"c%d" % c
            stream += [b"commit refs/heads/main\n", b"committer t <t@example.invalid> %d +0000\n" % (1700000000 + c),
                       b"data %d\n%s\n" % (len(message), message), b"M 100644 inline data.txt\n",
                       b"data %d\n%s\n" % (len(body), body)]
        git("fast-import", "--quiet", cwd=author, data=b"".join(stream))
        first = git("rev-list", "--max-parents=0", "refs/heads/main", cwd=author)
        git("clone", "-q", "--bare", author, bare)
        git("config", "pack.threads", "1", cwd=bare)      # the origin's own pack-objects, on the same limit here
        git("repack", "-q", "-a", "-d", "-f", cwd=bare)
        tip = git("rev-parse", "refs/heads/main", cwd=bare)
        self.assertGreaterEqual(len(git("rev-list", "--objects", "%s..%s" % (first, tip), cwd=bare).splitlines()), 100,
                                "premise: the fetch brings 100 objects or more, so git runs index-pack")
        git("init", "-q", stale)
        git("update-ref", "refs/heads/first", first, cwd=bare)
        git("fetch", "-q", bare, "refs/heads/first:" + ORIGIN_MAIN_REF, cwd=stale)
        git("update-ref", "-d", "refs/heads/first", cwd=bare)
        git("remote", "add", "origin", bare, cwd=stale)
        limits = batch.git_limits()
        for case, threads in (("git's own count on this machine", None), ("the clone's own pack.threads=20", "20")):
            with self.subTest(case=case):
                clone = os.path.join(work, "clone-%s" % (threads or "own"))
                shutil.copytree(stale, clone, symlinks=True)
                if threads:
                    git("config", "pack.threads", threads, cwd=clone)
                with unittest.mock.patch.dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"), \
                        unittest.mock.patch.object(limits, "GIT_MEMORY", PLANT_MEMORY):
                    os.environ.pop("MALLOC_ARENA_MAX", None)
                    batch.fetch(clone, False)
                self.assertEqual(git("rev-parse", ORIGIN_MAIN_REF, cwd=clone), tip, "the fetch brought the origin's tip")
                packs = [f for f in os.listdir(os.path.join(clone, ".git", "objects", "pack")) if f.endswith(".pack")]
                self.assertEqual(len(packs), 1, "premise: index-pack wrote the fetch's pack (unpack-objects writes none)")

    def test_output_past_the_limit_ends_the_call_with_git_output(self):
        """A git, or a run_tool process, that prints more than GIT_OUTPUT_MAX bytes on its stdout (lowered here to 4096 in
        the module batch.py reads its limits from) is killed with its process group, and GitOutput, a GitBound, names the
        call, the stream and the limit. One that prints exactly the limit is read whole. Before V1 batch.py read any
        amount."""
        limits = batch.git_limits()
        with unittest.mock.patch.object(limits, "GIT_OUTPUT_MAX", 4096):
            with self.env(SHIM_OUT="4096"):
                p = batch.run_git(["log"], self.tmp, repo=self.repo)
            self.assertEqual(len(p.stdout), 4096)
            for what, call in (("git", lambda: batch.run_git(["log"], self.tmp, repo=self.repo)),
                               ("tool", lambda: batch.run_tool([self.git, "check"], self.tmp, repo=self.repo))):
                with self.subTest(what=what), self.env(SHIM_OUT="4097"):
                    with self.assertRaises(batch.GitOutput) as cm:
                        call()
                    self.assertIsInstance(cm.exception, batch.GitBound)
                    self.assertIn("printed more than 4 KiB on its stdout, the most batch.py reads of one call "
                                  "(GIT_OUTPUT_MAX), and was killed", str(cm.exception))


class ToolGitStartsNoGc(_Base):
    """Round 2 of PR 959, ruling B, the scene of the round's regression-1, through batch.py's run_tool."""

    def test_pr_orphans_fetch_in_a_clone_past_the_pack_limit_starts_no_gc_and_writes_no_gc_log(self):
        """finish runs scripts/pr-orphans.sh through run_tool, and the script's git fetch runs git's automatic
        maintenance after it, which in a clone of more packs than gc.autoPackLimit (50) starts git gc --auto under
        run_tool's memory limit, with a need nobody measured; one that fails there in the background writes the gc.log
        that stops the clone's automatic gc until someone removes it, while the script still reports clean. run_tool's
        environment carries GIT_SETTINGS' gc.auto=0 and maintenance.auto=false (_tool_env), so the fetch starts none.
        The clone here holds more than 50 packs, a pre-auto-gc hook that records each gc git decides to start (git runs
        it then, before the gc), and gc.autoDetach=false, so a gc would run inside the call and not outlive the test (a
        git gc --auto in a copy of the clone, outside run_tool, runs the hook and repacks: the scene's premise).
        pr-orphans.sh then runs through run_tool, with MALLOC_ARENA_MAX unset, and reads the fake gh's merged PRs (none):
        it reports clean, the hook never ran and the packs are as they were. The hook's marker carries both halves of
        ruling B, that the fetch starts no gc and writes no gc.log: git writes gc.log only from a gc --auto it has
        decided to start and has detached, it decides after running pre-auto-gc, and this pin sets gc.autoDetach=false,
        so no gc here could write one (an assertion that none was written could not fail). The marker is git 2.43's road:
        its fetch's automatic maintenance is git gc --auto, which runs pre-auto-gc first. git 2.55's automatic
        maintenance is a geometric repack by default (git maintenance run --auto, its geometric strategy), which runs no
        pre-auto-gc hook and writes no gc.log, so there the marker stays absent with or without the environment and the
        pack count is the assertion that sees a repack (round 3 of PR 959, the census of the round-2 pins' git premises,
        2026-10-04). Red without the environment (run_tool at the round's head): under git 2.43.0 the hook ran, git
        having decided to start a gc under run_tool's limit; under git 2.55.0 the fetch's maintenance merged the 51 packs
        into two."""
        fx = self.fx
        git_dir = os.path.join(fx.dev, ".git")
        marker = os.path.join(fx.tmp, "gc-started")
        hook = os.path.join(git_dir, "hooks", "pre-auto-gc")
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, "w") as f:
            f.write('#!/bin/sh\necho "$PWD" >> "%s"\n' % marker)
        os.chmod(hook, 0o755)
        fx.dev_git("config", "gc.autoDetach", "false")
        # 51 packs of one blob each: git fast-import ends a pack at each checkpoint, and with fastimport.unpackLimit=0
        # keeps it as a pack, not as loose objects
        fx._git("-c", "fastimport.unpackLimit=0", "fast-import", "--quiet", cwd=fx.dev,
                input="".join("blob\ndata %d\n%s\ncheckpoint\n\n" % (len(b), b) for b in ("blob %d\n" % i for i in range(51))))

        def packs(d):
            return sorted(f for f in os.listdir(os.path.join(d, "objects", "pack")) if f.endswith(".pack"))
        before = packs(git_dir)
        self.assertGreater(len(before), 50, "premise: more packs than gc.autoPackLimit")
        copy = os.path.join(fx.tmp, "premise-copy")
        shutil.copytree(fx.dev, copy, symlinks=True)
        fx._git("gc", "--auto", "--quiet", cwd=copy)
        self.assertTrue(os.path.exists(marker), "premise: git decides to start a gc in this clone and runs the hook")
        self.assertLess(len(packs(os.path.join(copy, ".git"))), len(before), "premise: the gc runs inside the call")
        os.remove(marker)
        with unittest.mock.patch.dict(os.environ, fx.env):
            os.environ.pop("MALLOC_ARENA_MAX", None)
            p = batch.run_tool([os.path.join(fx.dev, "scripts", "pr-orphans.sh")], fx.dev)
        self.assertEqual(p.returncode, 0, p)
        self.assertIn("pr-orphans: clean (0 merged PR(s) checked", p.stdout)
        self.assertFalse(os.path.exists(marker), "pr-orphans.sh's fetch started a gc under run_tool's limit")
        self.assertEqual(packs(git_dir), before, "the packs are as they were")


# Runs the rest of its argv (an interpreter's arguments) with SIGCHLD ignored, which exec keeps (the same driver as
# tests/test_sweep_runner.py's IGNORE_SIGCHLD).
IGNORE_SIGCHLD = ("import os, signal, sys; signal.signal(signal.SIGCHLD, signal.SIG_IGN); "
                  "os.execv(sys.executable, [sys.executable] + sys.argv[1:])")
# A git first on PATH for the SIGCHLD pin: it prints what git's rev-parse --show-toplevel --absolute-git-dir
# --git-common-dir prints in a work tree, for the directory it runs in, and exits 1, so its exit status alone says
# that the call failed.
FAILING_GIT = r"""#!/bin/sh
d=$(pwd -P)
printf '%s\n%s\n%s\n' "$d" "$d/.git" "$d/.git"
echo "planted failure" >&2
exit 1
"""


class StartedWithSigchldIgnored(unittest.TestCase):
    """The 13:24Z ruling of 2026-10-02 on PR 926, its item 3: an ignored SIGCHLD survives exec, and under it the kernel
    reaps each child as it exits, so a wait finds no exit status to read and subprocess reports 0, whatever the process
    returned. batch.py's main gives SIGCHLD its default action before any command runs (install_stop_handlers), as
    scripts/sweep.py's does. Each run here starts batch.py with SIGCHLD ignored (IGNORE_SIGCHLD), in a session of its
    own under a 60 s watchdog that kills its whole tree. Red at the head before this change, which had no reset: every
    exit status read 0."""

    # It prints whether SIGCHLD was ignored when this process started, loads batch.py (argv[1]), and runs its main as
    # bisect, with cmd_bisect replaced by a probe that starts a process through each of the four runners in the
    # directory argv[2] (run_git's git and run_tool's process, the FAILING_GIT first on PATH, which exits 1; _run's and
    # run_command's, a shell that exits 4 and 3) and prints the exit status each returned and whether SIGCHLD was
    # ignored when they ran.
    DRIVER = r"""
import importlib.util, json, os, signal, sys
print(json.dumps({"started_ignored": signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN}), flush=True)
spec = importlib.util.spec_from_file_location("batch_tool_sigchld", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
where = sys.argv[2]
def probe(args):
    repo = mod.GitRepo(where, None, None, os.path.dirname(where))
    print(json.dumps({"run_git": mod.run_git(["status"], where, repo=repo).returncode,
                      "run_tool": mod.run_tool(["git", "status"], where, repo=repo).returncode,
                      "_run": mod._run(["sh", "-c", "exit 4"], cwd=where, check=False).returncode,
                      "run_command": mod.run_command(["sh", "-c", "exit 3"], where),
                      "ignored_at_call": signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN}), flush=True)
mod.cmd_bisect = probe
sys.exit(mod.main(["bisect", "b1", "--", "true"]))
"""

    def started_ignored(self, argv, env):
        """(rc, stdout, stderr) of the interpreter run over `argv` with SIGCHLD ignored, under the watchdog."""
        proc = subprocess.Popen([sys.executable, "-c", IGNORE_SIGCHLD, *argv], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and kill_tree(proc.pid))
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(proc.pid)
            out, err = proc.communicate()
            self.fail("the run was still going after 60 s:\n%s%s" % (out, err))
        return proc.returncode, out, err

    def test_batch_started_with_sigchld_ignored_reads_a_failing_git_as_failing(self):
        """Started with SIGCHLD ignored, each runner returns its process's real exit status (DRIVER): run_git's and
        run_tool's git, a FAILING_GIT that exits 1, return 1, and _run's and run_command's shells 4 and 3, with SIGCHLD
        at its default when they ran. And batch.py run whole over a clone (ROMP_BATCH_REPO) whose git is FAILING_GIT is
        refused at its first git call, the discovery, naming the failure: the git printed a work tree's three lines, so
        the exit status is the one thing that tells the failure. With the reset dropped each runner returned 0, and the
        discovery took the failing git's lines as the clone's."""
        tmp = os.path.realpath(tempfile.mkdtemp(prefix="batchsigchld-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        bindir, repo = os.path.join(tmp, "bin"), os.path.join(tmp, "repo")
        os.makedirs(bindir)
        os.makedirs(os.path.join(repo, ".git"))
        with open(os.path.join(bindir, "git"), "w") as f:
            f.write(FAILING_GIT)
        os.chmod(os.path.join(bindir, "git"), 0o755)
        env = {k: v for k, v in os.environ.items() if k not in ("ROMP_STATE_DIR", "ROMP_BATCH_REPO")}
        env.update(PATH=bindir + os.pathsep + env.get("PATH", ""), XDG_STATE_HOME=os.path.join(tmp, "state"))
        with self.subTest(case="the four runners"):
            rc, out, err = self.started_ignored(["-c", self.DRIVER, str(SCRIPTS / "batch.py"), repo], env)
            lines = [json.loads(x) for x in out.splitlines()]
            self.assertEqual(lines[:1], [{"started_ignored": True}],
                             "premise: the process started with SIGCHLD ignored:\n" + out + err)
            self.assertEqual(lines[1:], [{"run_git": 1, "run_tool": 1, "_run": 4, "run_command": 3,
                                          "ignored_at_call": False}], out + err)
            self.assertEqual(rc, 0, out + err)
        with self.subTest(case="batch.py whole"):
            rc, out, err = self.started_ignored([str(SCRIPTS / "batch.py"), "bisect", "b1", "--", "true"],
                                                dict(env, ROMP_BATCH_REPO=repo))
            self.assertEqual((rc, out, err), (1, "", "batch: %s is not a git working tree that git recognizes (planted "
                                                     "failure)\n" % repo))


class StopPinsLeaveNothing(unittest.TestCase):
    """The closing check wf_fb19febe-36b, its item 5: a stop pin that a mutant turns red leaves no process of it running.
    Each of BatchGitBound's stop_when pins below is run whole (its setUp, its body and its cleanups) against
    NO_HANDLER_MUTATION written over the fixture's batch.py, so the SIGTERM the pin sends ends batch.py outright and the
    pin is red; once the pin's run is done, no process group batch.py started (the mutant logs each) has a process left.
    Without stop_when's own recording, batch.py's descendants and their process groups read before the signal and
    killed on the way out (the mutant mStopPinsNoRecord drops it), the git worktree add each pin stops, and its child,
    ran on after the pin, blocked on the FIFO the pin had removed (the closing check's evidence: four processes from
    these two pins); with the descendants alone, a git reset --hard the add started after the read ran on in the add's
    group (3 of 20 runs under load), which the groups close (_groups_of). The other stop
    pins over a git or a script wait already kill the pids they record on the way out (stopped, and the ledger and
    pr-orphans probes' kill_probe_pids_on_the_way_out)."""

    PINS = ("test_a_stop_during_assembles_worktree_add_leaves_nothing_and_the_next_assemble_passes",
            "test_a_stop_during_the_ledger_checks_worktree_add_leaves_no_registration")

    @unittest.skipUnless(os.path.isdir("/proc"), "the pins record the descendants they kill from /proc (Linux); off it "
                                                   "their watchdog kills the watched group alone")
    def test_a_stop_pin_a_mutant_turns_red_leaves_no_process_of_it_running(self):
        tmp = tempfile.mkdtemp(prefix="stoppins-")
        self.addCleanup(shutil.rmtree, tmp, True)
        for name in self.PINS:
            with self.subTest(pin=name):
                log = os.path.join(tmp, name + ".pids")
                open(log, "w").close()

                class Mutated(BatchGitBound):
                    def setUp(inner):
                        super().setUp()
                        path = os.path.join(inner.fx.dev, "scripts", "batch.py")
                        with open(path) as f:
                            src = f.read()
                        for old, new in NO_HANDLER_MUTATION:
                            self.assertEqual(src.count(old), 1, "premise: the mutation's text is in batch.py once")
                            src = src.replace(old, new)
                        with open(path, "w") as f:
                            f.write(src)
                        inner.fx.env["STOP_PINS_LOG"] = log

                result = unittest.TestResult()
                Mutated(name).run(result)
                with open(log) as f:
                    groups = [int(x) for x in f.read().split()]
                self.addCleanup(_kill_groups, groups)       # this pin leaves nothing running either
                self.assertEqual((len(result.failures), len(result.errors), result.testsRun), (1, 0, 1),
                                 "premise: the mutant turned the stop pin red: %s" % (result.failures + result.errors))
                self.assertIn("-15", result.failures[0][1], "premise: red because SIGTERM ended batch.py outright")
                self.assertTrue(groups, "premise: batch.py started processes and the mutant logged them")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and any(_group_alive(g) for g in groups):
                    time.sleep(0.05)
                self.assertEqual([g for g in groups if _group_alive(g)], [],
                                 "no process group batch.py started has a process left once the red pin is done")


class VerifyReadsTheSweep(_Base):
    """verify reads the result scripts/sweep.py wrote for the batch head's full sha, through sweep.py's own
    reader, and names every case but a pass (2026-09-27; before, the batcher passed free text with
    --sweep and verify checked only that some text had been given at this head). The other checks still
    print, so one run reports everything; a failing case clears the recorded sweep."""

    def assembled(self):
        self.fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        self.fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        self.fx.ok("plan", "--name", "b1")
        self.fx.ok("assemble", "b1")
        return self.fx.dev_git("rev-parse", "batch/b1")

    def refused(self, needle):
        p = self.fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn(needle, p.stdout)
        self.assertIn("ok   provenance", p.stdout, "the other checks still run and print")
        st = self.fx.state("b1")
        self.assertFalse(st["verified"]["ok"])
        self.assertIsNone(st["sweep"], "a failing case leaves no recorded sweep for the body")
        return p

    def test_no_result_is_missing_and_names_the_full_sha_and_the_directory_it_read(self):
        fx = self.fx
        head = self.assembled()
        p = self.refused("FAIL sweep missing: no result for the batch head %s in %s (the state dir from XDG_STATE_HOME"
                         % (head, sweep.sweeps_dir(env=fx.env)))
        self.assertIn("run `scripts/sweep.py run --tree %s --python <python>` (%s) with the same ROMP_STATE_DIR and XDG_STATE_HOME"
                      % (fx.wt("b1"), sweep.PYTHON_REMEDY), p.stdout)

    def test_the_no_result_case_compares_the_same_under_a_linked_temp_dir(self):
        """Frozen-head ruling 5: the no-result case above failed on macOS, where the temp dir is reached through a link
        (/var is /private/var): batch.py names the worktree under its repository's real path (git's show-toplevel
        resolves links), and the test built the path it expected from the unresolved temp dir. The Fixture resolves its
        root once, so every path it hands out is in the form batch.py prints. This runs the same case on any OS with
        the temp dir reached through a link, and shows the comparison does not depend on the path's form."""
        real = os.path.realpath(tempfile.mkdtemp(prefix="batchtool-linked-"))
        self.addCleanup(shutil.rmtree, real, True)
        link = real + "-link"
        os.symlink(real, link)
        self.addCleanup(os.unlink, link)
        self.assertNotEqual(os.path.realpath(link), link, "premise: the temp dir is reached through a link")
        with unittest.mock.patch.object(tempfile, "tempdir", link):
            self.fx = fx = Fixture()
        self.addCleanup(fx.close)
        head = self.assembled()
        p = self.refused("FAIL sweep missing: no result for the batch head %s in %s (the state dir from XDG_STATE_HOME"
                         % (head, sweep.sweeps_dir(env=fx.env)))
        self.assertIn("run `scripts/sweep.py run --tree %s --python <python>` (%s) with the same ROMP_STATE_DIR and XDG_STATE_HOME"
                      % (fx.wt("b1"), sweep.PYTHON_REMEDY), p.stdout)
        self.assertEqual(os.path.realpath(fx.wt("b1")), fx.wt("b1"), "the Fixture hands out resolved paths")
        self.assertTrue(fx.tmp.startswith(real + os.sep), fx.tmp)

    def test_a_pass_at_the_head_is_ok_and_recorded(self):
        fx = self.fx
        head = self.assembled()
        path = fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   sweep at %s: pass, finished " % head[:10], p.stdout)
        self.assertIn("(pytest 0, bats 0, manager 0, tools 0, ledger 0; not owed: deps, typecheck, npm-test, pdf-smoke, build, served); %s" % path,
                      p.stdout)
        st = fx.state("b1")
        self.assertTrue(st["verified"]["ok"])
        self.assertEqual(st["sweep"]["head"], head)
        self.assertEqual(st["sweep"]["verdict"], "pass")
        # compared as a mapping plus the order: a list literal whose first element is "pytest" reads as a pytest command
        # to tests/test_ci_sdk_pin.py's census of child launchers (PR 872)
        self.assertEqual([n for n, _rc in st["sweep"]["legs"]], list(sweep.LEGS))
        self.assertEqual(dict(st["sweep"]["legs"]), {"deps": "not owed", "pytest": 0, "bats": 0, "manager": 0, "tools": 0, "ledger": 0,
                                                     "typecheck": "not owed", "npm-test": "not owed", "pdf-smoke": "not owed",
                                                     "build": "not owed", "served": "not owed"})

    def test_a_result_at_the_old_head_is_stale_after_a_batch_commit(self):
        fx = self.fx
        old = self.assembled()
        fx.sweep("b1")
        wt = fx.wt("b1")
        with open(os.path.join(wt, "t.txt"), "w") as f:
            f.write("t\n")
        fx._git("add", "t.txt", cwd=wt)
        fx._git("commit", "-q", "-m", "batch: t", cwd=wt)
        new = fx.dev_git("rev-parse", "batch/b1")
        self.refused("FAIL sweep stale: the newest result for batch/b1 is at %s (finished " % old[:10])
        p = fx.run("verify", "b1")
        self.assertIn("the batch head is at %s; sweep again at the batch head" % new[:10], p.stdout)

    def test_a_file_that_records_another_sha_is_stale_even_with_the_same_prefix(self):
        fx = self.fx
        head = self.assembled()
        path = fx.sweep("b1")
        with open(path) as f:
            data = json.load(f)
        data["sha"] = head[:10] + "0" * 30       # the file named for the head records another commit
        sweep.write_result(path, data)
        # the remedy is run's, since run keeps this file and refuses the sha (the verify pass at the closing check
        # wf_fb19febe-36b's build, its code finding 2)
        self.refused("FAIL sweep stale: %s records sha %s, not the batch head %s; it is kept, since results are append-only, "
                     "and a run at this sha is refused while it is there: move it aside to sweep this sha again\n"
                     % (sweep.result_path(head, env=fx.env), head[:10], head[:10]))

    def test_a_red_leg_is_named_and_a_recorded_pass_over_it_is_invalid(self):
        fx = self.fx
        head = self.assembled()
        fx.sweep("b1")
        fx.ok("verify", "b1")
        self.assertEqual(fx.state("b1")["sweep"]["verdict"], "pass")
        legs = self.legs(bats=1)
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep red at %s: bats (rc 1); logs under " % head[:10])
        fx.sweep("b1", legs=legs, verdict="pass")
        self.refused("FAIL sweep invalid at %s: the recorded verdict pass disagrees with its legs (red)" % head[:10])

    def test_an_unfinished_an_incomplete_and_an_unreadable_result_each_say_so(self):
        fx = self.fx
        head = self.assembled()
        fx.sweep("b1", finished=None)
        self.refused("FAIL sweep unfinished: the sweep at %s started " % head[:10])
        legs = self.legs()
        del legs["bats"]
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep incomplete at %s: no bats leg in " % head[:10])
        with open(sweep.result_path(head, env=fx.env), "w") as f:
            f.write("{")
        self.refused("FAIL sweep unreadable: %s: " % sweep.result_path(head, env=fx.env))

    def test_a_dangling_symlink_at_the_batch_heads_result_reads_unreadable_naming_it(self):
        """The closing check wf_3b100f5e-b38, its item 3, in verify: the batch head's result file is a symlink to a path
        that does not exist. The reader tests the path with os.path.lexists, so verify fails it as unreadable, naming the
        file, as check does. At the head before it, verify said the result was missing. Since the closing check
        wf_fb19febe-36b, its item 8, the line names run's remedy, moving the file aside, where it said "sweep again"."""
        fx = self.fx
        head = self.assembled()
        path = sweep.result_path(head, env=fx.env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.symlink(os.path.join(fx.tmp, "no-such-result.json"), path)
        self.refused("FAIL sweep unreadable: %s: a symlink, not a regular file; it is kept, since results are append-only, "
                     "and a run at this sha is refused while it is there: move it aside to sweep this sha again\n" % path)

    def test_a_result_that_excuses_deps_for_a_package_json_the_head_holds_fails(self):
        """Round 1's excuse rule at the batch head: a result marking deps not owed for having no
        vscode-extension/package.json fails verify when the head's tree holds one, and passes once deps ran."""
        fx = self.fx
        head = fx.branch("a", {"vscode-extension/package.json": "{}\n"}, swept=False)
        legs = self.legs()
        legs["deps"] = {"owed": True, "rc": 0, "started": sweep.now(), "finished": sweep.now()}
        for n in sweep.EXTENSION_LEGS[1:]:          # the webview legs, pdf-smoke and served
            legs[n] = {"owed": True, "rc": 0, "tests": 1, "failed": 0, "started": sweep.now(), "finished": sweep.now()}
        fx.result(head, "a", webview=True, tree=fx.author, legs=legs)
        fx.pr(101, "a", title="the extension's manifest", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        bhead = fx.dev_git("rev-parse", "batch/b1")
        fx.sweep("b1", webview=True)                  # deps not owed for having no package.json: false at this head
        self.refused("FAIL sweep invalid at %s: the result marks deps not owed for having no vscode-extension/package.json, but "
                     "the batch head's tree holds vscode-extension/package.json" % bhead[:10])
        fx.sweep("b1", legs=legs)
        fx.ok("verify", "b1")

    def test_a_member_based_on_a_branch_in_neither_the_batch_nor_main_fails_verify(self):
        """Round 2, extra8-2: the analogue of the retired land.sh's three base cases. A member whose base is a pushed
        branch that is neither a member's head nor in main fails verify with FAIL base and exit 1 (the exit asserted:
        a verify that printed the line and still exited 0 would pass a text check alone)."""
        fx = self.fx
        self.assembled()
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.branch("elsewhere", {"elsewhere.txt": "a branch no member carries\n"}, swept=False)
        fx.gh_state = fx.gh()
        fx.gh_state["prs"]["101"]["baseRefName"] = "elsewhere"
        fx._save_gh()
        p = fx.run("verify", "b1")
        self.assertIn("FAIL base: #101 is based on elsewhere, which is neither in the batch nor in main", p.stdout)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertFalse(fx.state("b1")["verified"]["ok"])

    def test_a_result_that_excuses_the_ledger_at_a_head_that_holds_its_script_fails(self):
        """Round 2, correctness-4: the ledger is marked not owed only when the head has no ledger script. A result that
        gives the runner's own reason for it fails verify at a batch head whose tree holds scripts/upstream-ledger.py,
        naming the file; one that gives any other reason reads invalid through the reader; once the ledger ran, verify
        passes. Before round 2 both marks passed."""
        fx = self.fx
        prose_only = "# Upstream\n\nProse.\n\nEntries live in upstream/.\n\nWhen offering: tail.\n"
        fx.commit_main({"UPSTREAM.md": prose_only, "scripts/upstream-ledger.py": FAKE_LEDGER}, "ledger migration")
        head = self.assembled()
        legs = self.legs()
        legs["ledger"] = {"owed": False, "rc": None, "why": "no scripts/upstream-ledger.py in the tree"}
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep invalid at %s: the result marks ledger not owed for having no scripts/upstream-ledger.py in "
                     "the tree, but the batch head's tree holds scripts/upstream-ledger.py" % head[:10])
        legs["ledger"]["why"] = "skipped by hand"
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep invalid at %s: ledger marked not owed for a reason other than 'no scripts/upstream-ledger.py "
                     "in the tree' ('skipped by hand')" % head[:10])
        fx.sweep("b1", legs=self.legs())
        fx.ok("verify", "b1")

    def test_a_result_recorded_under_another_leg_environment_fails(self):
        """The allowlist hash is verified (round 1, decision 10): a result recorded under another leg environment policy
        is not the same gate, so verify fails it by name, as it fails one with no hash at all."""
        fx = self.fx
        head = self.assembled()
        fx.sweep("b1", runner={"leg_env": {"allow": ["USER"], "hash": "0" * 64}})
        self.refused("FAIL sweep invalid at %s: recorded under another leg environment (hash 000000000000; this reader's is %s"
                     % (head[:10], sweep.policy_hash()[:12]))
        fx.sweep("b1", runner={})
        self.refused("FAIL sweep invalid at %s: recorded under another leg environment (hash none;" % head[:10])
        fx.sweep("b1")
        fx.ok("verify", "b1")

    def test_a_result_whose_run_records_no_private_checkout_fails(self):
        """A run that records no private checkout was swept in the batcher's own tree (this branch's intermediate
        runners wrote schema 2, with the allowlist's hash, before the checkout existed), so verify fails it as it fails a
        schema-1 result."""
        fx = self.fx
        head = self.assembled()
        fx.sweep("b1", runner={"leg_env": {"allow": list(sweep.LEG_ALLOW), "hash": sweep.policy_hash()}})
        self.refused("FAIL sweep unreadable: %s: run 1 records no private checkout, so it was recorded by a runner that swept "
                     "the batcher's own tree" % sweep.result_path(head, env=fx.env))
        fx.sweep("b1")
        fx.ok("verify", "b1")

    def test_without_sweep_py_beside_it_verify_refuses_by_name(self):
        fx = self.fx
        self.assembled()
        fx.sweep("b1")
        os.remove(os.path.join(fx.dev, "scripts", "sweep.py"))
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("scripts/sweep.py is missing beside batch.py", p.stderr)
        self.assertNotIn("ok   sweep", p.stdout)

    def test_a_result_that_skips_a_webview_leg_fails_whatever_the_diff(self):
        """Round 1, C1 and decision 11: every head owes the webview legs, so verify refuses a batch-head result that
        marks any of them not owed for any reason but a missing extension, whatever the batch changed. Here it changed
        notes.txt alone, where the head's verify re-derived the changed-path rule and passed; one that ran them passes."""
        fx = self.fx
        head = self.assembled()
        untouched = "kernel/kernel.py, ui/ and vscode-extension/ untouched since %s" % fx.bare_rev("main")[:10]
        legs = self.legs()
        for n in sweep.WEBVIEW_LEGS:
            legs[n] = {"owed": False, "rc": None, "why": untouched}
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep invalid at %s: typecheck, npm-test, build marked not owed for a reason other than "
                     "'no vscode-extension/package.json' ('%s')" % (head[:10], untouched))
        legs["build"] = {"owed": True, "rc": 0, "started": sweep.now(), "finished": sweep.now()}
        fx.sweep("b1", legs=legs)
        self.refused("FAIL sweep invalid at %s: typecheck, npm-test marked not owed for a reason other than" % head[:10])
        legs = self.legs()
        for n in sweep.WEBVIEW_LEGS:
            legs[n] = {"owed": True, "rc": 0, "tests": 1, "failed": 0, "started": sweep.now(), "finished": sweep.now()}
        fx.sweep("b1", legs=legs)
        p = fx.ok("verify", "b1")
        self.assertIn("ok   sweep at %s: pass" % head[:10], p.stdout)
        self.assertIn("typecheck 0, npm-test 0, build 0", p.stdout)

    FLAKE = "tests/test_notes.py::test_order (known)"

    def history(self, head, *later):
        """A history at `head`: a full run that failed pytest (rc 1, log logs/pytest.log), then the runs `later` gives
        as (kind, legs, flakes) or a run record."""
        stamp = sweep.now()
        failed = self.legs()
        failed[sweep.PYTEST_LEGS[0]].update(rc=1, failed=1, log="logs/pytest.log")      # the pytest leg
        runs = [self.fx.run_record(kind="full", sha=head, started=stamp, finished=stamp, flakes={}, legs=failed, invalid=None)]
        for item in later:
            if isinstance(item, dict):
                runs.append(self.fx.run_record(**dict({"sha": head, "started": stamp, "finished": stamp, "flakes": {}, "invalid": None}, **item)))
                continue
            kind, legs, flakes = item
            runs.append(self.fx.run_record(kind=kind, sha=head, started=stamp, finished=stamp, flakes=flakes, legs=legs, invalid=None))
        return runs

    def test_a_leg_rerun_counts_only_with_its_first_failure_and_flake_and_the_body_names_both(self):
        """A leg the runner re-ran after a known flake (pre-round ruling Q11, frozen-head item 1): the result keeps both
        runs, verify accepts the pair through the reader and records it, and the body's first block names the first
        failure and the flake; a re-run that names no flake is refused as invalid."""
        fx = self.fx
        head = self.assembled()
        pytest_leg = sweep.PYTEST_LEGS[0]
        self.assertEqual(pytest_leg, "pytest")
        rerun = {pytest_leg: self.legs()[pytest_leg]}
        fx.sweep("b1", runs=self.history(head, ("leg", rerun, {pytest_leg: self.FLAKE})))
        p = fx.ok("verify", "b1")
        note = "pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE
        self.assertIn(note, p.stdout)
        self.assertEqual(fx.state("b1")["sweep"]["reruns"], [note])
        body = fx.ok("summarize", "b1", "--print-only").stdout
        first_block = next(b for b in body.split("\n\n") if "Verified at %s" % head[:10] in b)
        self.assertIn(note, first_block, "the first block names both runs")
        fx.sweep("b1", runs=self.history(head, ("leg", rerun, {})))
        self.refused("FAIL sweep invalid at %s: run 2 re-ran pytest with no known flake named" % head[:10])

    def test_a_red_run_a_later_green_did_not_excuse_is_refused_by_name(self):
        """Frozen-head item 1: a later green counts over a red run only with --flake naming the failed leg, so verify
        refuses a history whose second full run passed pytest with no flake, naming the red run and its log."""
        fx = self.fx
        head = self.assembled()
        fx.sweep("b1", runs=self.history(head, ("full", self.legs(), {})))
        self.refused("FAIL sweep red at %s: run 1 failed pytest (rc 1; log logs/pytest.log), and run 2 passed it with no "
                     "--flake naming it" % head[:10])

    def test_an_invalid_run_in_the_history_is_named_by_verify_and_the_body(self):
        """Round 1, decision 18, which stands for an invalid run that failed no leg: it needs no flake before a later
        green counts, but verify and the body name it."""
        fx = self.fx
        head = self.assembled()
        stamp = sweep.now()
        reason = "after the manager leg the checkout is not the sha's tree: untracked leaked.txt"
        runs = [fx.run_record(kind="full", sha=head, started=stamp, finished=stamp, flakes={}, legs=self.legs(), invalid=reason),
                fx.run_record(kind="full", sha=head, started=stamp, finished=stamp, flakes={}, legs=self.legs(), invalid=None)]
        fx.sweep("b1", runs=runs)
        p = fx.ok("verify", "b1")
        note = "run 1 (started %s) was invalid: %s" % (stamp, reason)
        self.assertIn("an earlier " + note, p.stdout)
        self.assertEqual(fx.state("b1")["sweep"]["invalid_runs"], [note])
        body = fx.ok("summarize", "b1", "--print-only").stdout
        first_block = next(b for b in body.split("\n\n") if "Verified at %s" % head[:10] in b)
        self.assertIn("an earlier " + note, first_block)

    def test_a_failure_in_an_invalid_run_counts_and_verify_and_the_body_name_it(self):
        """Round 2, Class A: invalidity voids a run's passes, never its failures. A history whose invalid run failed
        pytest passes only when a later run names pytest's known flake, and verify records the invalid run with its
        failed leg in state['sweep']['invalid_runs'], which the body's first block shows; a later green without the
        flake is refused naming the invalid run's failure."""
        fx = self.fx
        head = self.assembled()
        stamp = sweep.now()
        pytest_leg = sweep.PYTEST_LEGS[0]
        reason = "after the manager leg the checkout is not the sha's tree: untracked leaked.txt"
        failed = self.legs()
        failed[pytest_leg].update(rc=1, failed=1, log="logs/pytest.log")
        invalid = fx.run_record(kind="full", sha=head, started=stamp, finished=stamp, flakes={}, legs=failed, invalid=reason)
        fx.sweep("b1", runs=[invalid, fx.run_record(kind="full", sha=head, started=stamp, finished=stamp, flakes={},
                                                     legs=self.legs(), invalid=None)])
        self.refused("FAIL sweep red at %s: run 1 failed pytest (rc 1; log logs/pytest.log), and run 2 passed it with no "
                     "--flake naming it" % head[:10])
        fx.sweep("b1", runs=[invalid, fx.run_record(kind="full", sha=head, started=stamp, finished=stamp,
                                                     flakes={pytest_leg: self.FLAKE}, legs=self.legs(), invalid=None)])
        p = fx.ok("verify", "b1")
        note = "run 1 (started %s) was invalid: %s; its failures count: pytest (rc 1; log logs/pytest.log)" % (stamp, reason)
        self.assertIn("an earlier " + note, p.stdout)
        self.assertEqual(fx.state("b1")["sweep"]["invalid_runs"], [note])
        self.assertEqual(fx.state("b1")["sweep"]["reruns"],
                         ["pytest re-run after a known flake (first run rc 1; flake: %s)" % self.FLAKE])
        body = fx.ok("summarize", "b1", "--print-only").stdout
        first_block = next(b for b in body.split("\n\n") if "Verified at %s" % head[:10] in b)
        self.assertIn("an earlier " + note, first_block)

    def test_the_free_text_flag_is_gone(self):
        fx = self.fx
        self.assembled()
        p = fx.run("verify", "b1", "--sweep", "pytest 1 passed")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("unrecognized arguments: --sweep", p.stderr)

    def legs(self, **rcs):
        out = {n: {"owed": True, "rc": rcs.get(n, 0), "started": sweep.now(), "finished": sweep.now()} for n in sweep.LEGS}
        for n in sweep.TEST_LEGS:
            out[n].update(tests=1, failed=0)
        for n in sweep.EXTENSION_LEGS:          # the fixture's worlds have no vscode-extension/package.json
            out[n] = {"owed": False, "rc": None, "why": sweep.NO_PACKAGE_JSON}
        return out


# Calls batch.py's read_state (scripts/batch.py at argv[1]) on the batch state file argv[2], a sparse file of argv[3]
# bytes it makes with truncate (no byte of it written), under an address cap set soft AND hard at what the child maps
# then plus 256 MiB, which bounds the memory a read of the whole file can take; with argv[4] "grew", os.fstat first gives
# every regular file's size as 0, as for a file that grew after the fstat. Prints JSON: [how it ended, what it gave, the
# bytes read], the bytes counted as each read of the file object read_state opens returns them. On CPython 3.10, 3.12
# and 3.13 the cap binds first, so a whole read ends in a MemoryError at it. Free-threaded 3.14 starts with about 1 GiB
# of address space its allocator has already reserved, so there the cap leaves room for a 768 MiB plant and a whole read
# of it succeeds; the bytes read tell a bounded read from a whole one on every interpreter.
STATE_DRIVER = r"""
import importlib.util, json, os, resource, stat, sys
spec = importlib.util.spec_from_file_location("batch_state_reader", sys.argv[1])
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
path, size, mode = sys.argv[2], int(sys.argv[3]), sys.argv[4]
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "wb"):
    pass
os.truncate(path, size)
if mode == "grew":
    real_fstat = os.fstat
    def emptied_fstat(fd):
        st = real_fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return st
        fields = list(st)
        fields[stat.ST_SIZE] = 0
        return os.stat_result(fields)
    os.fstat = emptied_fstat
read = {"bytes": 0}
real_fdopen = os.fdopen
class Counting:
    def __init__(self, f):
        self.f = f
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.f.close()
        return False
    def read(self, n=-1):
        data = self.f.read(n)
        read["bytes"] += len(data)
        return data
os.fdopen = lambda *args, **kwargs: Counting(real_fdopen(*args, **kwargs))
with open("/proc/self/status") as f:
    vm = int([line.split()[1] for line in f if line.startswith("VmSize:")][0]) << 10
cap = vm + (256 << 20)
resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
try:
    data = batch.read_state(path)
    got = ["returned", None if data is None else len(data)]
except MemoryError:
    got = ["MemoryError"]
except Exception as e:
    got = [type(e).__name__, str(e)]
print(json.dumps(got + [read["bytes"]]))
"""


class BatchStateLimit(unittest.TestCase):
    """Round 1 of PR 959, ruling A's class: the batch state file lives in the clone's common dir, which a sweep's leg
    reaches through its checkout's alternates, so a leg can leave a sparse file of any size there, and read_state reads
    at most STATE_MAX (1 MiB) of it, enforced by fstat before the read and by reading no more than the limit and a byte."""

    SIZE = 768 << 20

    def state(self, mode, size=None):
        if not sys.platform.startswith("linux"):
            self.skipTest("the driver sets its address cap from /proc/self/status, which only Linux has, and only Linux "
                          "enforces RLIMIT_AS; the cap bounds the memory a whole read of the plant can take")
        tmp = tempfile.mkdtemp(prefix="batchstate-")
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, ".git", "batch", "b1.json")
        size = self.SIZE if size is None else size
        p = subprocess.run([sys.executable, "-c", STATE_DRIVER, str(SCRIPTS / "batch.py"), path, str(size), mode],
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return path, json.loads(p.stdout)

    def test_a_batch_state_over_the_limit_is_refused_naming_its_size(self):
        """A sparse state file of 768 MiB is a Fail naming the file, its size and the limit, with the remedy read_state
        gives a state file it cannot read, and no byte of it is read. Before this pass read_state read it whole: on
        CPython 3.10, 3.12 and 3.13 a MemoryError at the child's address cap here, and on free-threaded 3.14, where the
        cap does not bind first, all 805306368 bytes of it; red on each for that reason, and any size a leg chose was
        read without the cap."""
        path, got = self.state("whole")
        self.assertEqual(got, ["Fail", "the batch state %s cannot be read (%d bytes, more than the %d batch.py reads); move "
                                       "it aside and plan again" % (path, self.SIZE, 1 << 20), 0])
        self.assertEqual(getattr(batch, "STATE_MAX", None), 1 << 20, "batch.py's limit is the one pinned")

    def test_a_batch_state_of_exactly_the_limit_is_read_whole_and_one_byte_more_is_refused(self):
        """The other side of the limit: a state file of exactly STATE_MAX bytes is read whole, all of it, so a comparison
        that refused it (fstat's size at the limit taken as over it) is red here, where the 768 MiB plant passes under
        it; one of STATE_MAX + 1 bytes is the Fail naming its size and the limit, with nothing read. read_regular's own
        comparison, in scripts/sweep.py, is pinned at its limit by tests/test_sweep_runner.py's ShallowBatcher case of
        a shallow file at the bound
        (test_a_shallow_file_larger_than_the_runner_reads_is_refused_naming_its_size_and_never_read)."""
        limit = 1 << 20
        path, got = self.state("whole", limit)
        self.assertEqual(got, ["returned", limit, limit])
        path, got = self.state("whole", limit + 1)
        self.assertEqual(got, ["Fail", "the batch state %s cannot be read (%d bytes, more than the %d batch.py reads); move "
                                       "it aside and plan again" % (path, limit + 1, limit), 0])

    def test_a_batch_state_that_grew_after_the_fstat_stops_at_the_limit(self):
        """The second half of the bound: with os.fstat giving every regular file's size as 0, as for a file that grew
        after it, read_state reads 1 MiB and a byte of the 768 MiB plant, the bytes read the pin expects, and is a Fail
        naming the limit. Before this pass it read the whole file: on CPython 3.10, 3.12 and 3.13 a MemoryError at the cap
        here, and on free-threaded 3.14, where the cap does not bind first, all 805306368 bytes of it, returned; red on
        each for that reason. A read_state that kept the fstat check but read the file whole gives the expected Fail on
        3.14, after reading all of it, so there only the bytes read make the pin red."""
        path, got = self.state("grew")
        self.assertEqual(got, ["Fail", "the batch state %s cannot be read (more than the %d bytes batch.py reads); move it "
                                       "aside and plan again" % (path, 1 << 20), (1 << 20) + 1])


def _ci_workflow_readers():
    """tests/test_ci_workflow_concurrency.py, the ci.yml readers (the shape switch's among them), imported with the checkout
    root on sys.path as the CI test modules import it."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests import test_ci_workflow_concurrency
    return test_ci_workflow_concurrency


class CiJobs(unittest.TestCase):
    """The coordinator's decision 18, the half that reads ci.yml: batch.ci_jobs reads, at a head, each job of ci.yml and
    the name GitHub renders for its job runs (its name: with each expression matching any text, or its id), and refuses a
    ci.yml it cannot read that way. Synthetic workflow text in a repository of its own."""

    def jobs(self, ci):
        d = os.path.realpath(tempfile.mkdtemp(prefix="cijobs-"))
        self.addCleanup(shutil.rmtree, d, True)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        subprocess.run(["git", "init", "-q", d], check=True, env=env)
        if ci is not None:
            os.makedirs(os.path.join(d, ".github", "workflows"))
            with open(os.path.join(d, ".github", "workflows", "ci.yml"), "w") as f:
                f.write(ci)
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write("x\n")
        subprocess.run(["git", "-C", d, "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x"],
                       check=True, env=env)
        return batch.ci_jobs(d, "HEAD", "")

    def matches(self, ci, rendered):
        return {job: [n for n in rendered if rx.fullmatch(n)] for job, _name, rx in self.jobs(ci)}

    def test_each_job_is_told_by_the_name_github_renders(self):
        ci = ("name: CI\njobs:\n"
              "  python:\n    name: Python ${{ matrix.python-version }} (${{ matrix.os }})\n    strategy:\n      matrix:\n"
              "        os: [ubuntu-latest]\n    steps:\n      - run: x\n"
              "  build:\n    strategy:\n      matrix:\n        os: [a, b]\n    steps:\n      - run: x\n"
              "  quoted:\n    name: \"Secret scan (gitleaks)\"\n    steps:\n      - run: x\n"
              "  commented:\n    name: vscode-extension (typecheck + test + build)  # the extension\n    steps:\n      - run: x\n"
              "  plain:\n    runs-on: ubuntu-latest\n    steps:\n      - run: x\n")
        rendered = ["Python 3.12 (ubuntu-latest)", "build (a)", "build", "Secret scan (gitleaks)",
                    "vscode-extension (typecheck + test + build)", "plain", "plain (x)", "Exactly one tier label"]
        self.assertEqual(self.matches(ci, rendered),
                         {"python": ["Python 3.12 (ubuntu-latest)"], "build": ["build (a)", "build"],
                          "quoted": ["Secret scan (gitleaks)"], "commented": ["vscode-extension (typecheck + test + build)"],
                          "plain": ["plain"]})

    # The expressions a job name in ci.yml may hold, and what each renders to on a batch push: the Linux cells alone run
    # there (the matrices' os: evaluates to ubuntu-latest for a push; CiMatrixRunners in
    # tests/test_ci_workflow_concurrency.py), and a python-version runs once per version the job's matrix lists.
    RENDERED = {"matrix.os": ["ubuntu-latest"]}
    # The python job's shard clause (2026-10-04): every cell of a batch push is an ubuntu-latest one, so it renders as
    # ", shard <k>" once for each value the job's matrix lists on its shard axis (tests/test_ci_shards.py holds the axis
    # and the names per cell).
    SHARD_CLAUSE = "matrix.os == 'ubuntu-latest' && format(', shard {0}', matrix.shard) || ''"

    def batch_push_checks(self, text):
        """{job id: [the name GitHub renders for each of its job runs on a batch push]}, derived from ci.yml's job ids, so
        a job added later is read with no change here (the focused re-check at the round-2 fix head, ruling 5: the list
        this replaced named four of the six jobs). Each job's name is the one ci_jobs reads; ${{ matrix.os }} renders as
        RENDERED gives it, and ${{ matrix.python-version }} as each version the job's matrix lists, its include entries'
        among them. A name holding any other expression, or a job with a matrix and no name, is refused here, so a job
        written another way is read rather than passed over."""
        out = {}
        for job, name, _rx in self.jobs(text):
            block = re.search(r"^  %s:[ \t]*(?:#.*)?\n(.*?)(?=^  [A-Za-z_][\w-]*:[ \t]*(?:#.*)?$|^[A-Za-z_]|\Z)" % re.escape(job),
                              text, re.M | re.S).group(1)
            exprs = set(re.findall(r"\$\{\{\s*(.*?)\s*\}\}", name))
            self.assertFalse(exprs - set(self.RENDERED) - {"matrix.python-version", self.SHARD_CLAUSE},
                             "the %s job's name %r holds an expression this does not render: render it here" % (job, name))
            self.assertFalse(name == job and re.search(r"^    strategy:", block, re.M),
                             "the %s job has a matrix and no name: render GitHub's (<values>) here" % job)
            names = [name]
            if "matrix.python-version" in exprs and job == "python":
                # the python job's python-version axis is the shape switch's expression (2026-10-06): the versions a batch
                # push runs are the axis evaluated for a push to a batch branch, under the shape the file's three lines say
                # (tests/test_ci_workflow_concurrency.py; its excludes drop macOS cells alone, and a push has none)
                wf = _ci_workflow_readers()
                versions = wf.python_versions(wf.python_version_axis(text), wf.run("push", wf.BATCH_X, wf.SHA_A))
            elif "matrix.python-version" in exprs:
                # an exclude: entry names a cell the matrix drops (the python job's macOS exclusions, 2026-10-04), so its
                # versions are not read; the list and the include: entries are
                kept = re.sub(r"^(\s*)exclude:[ \t]*\n(?:\1\s+.*\n|\s*\n)*", "", block, flags=re.M)
                versions = [v.strip().strip("'\"") for group in re.findall(r"python-version:[ \t]*\[([^\]]*)\]", kept)
                            for v in group.split(",")]
                versions += re.findall(r"python-version:[ \t]*['\"]([^'\"]+)['\"]", kept)
            if "matrix.python-version" in exprs:
                self.assertTrue(versions, "the %s job's matrix lists no python-version" % job)
                names = [re.sub(r"\$\{\{\s*matrix\.python-version\s*\}\}", v, name) for v in versions]
            if self.SHARD_CLAUSE in exprs:
                shards = [v.strip().strip("'\"") for group in re.findall(r"shard:[ \t]*\[([^\]]*)\]", block)
                          for v in group.split(",")]
                self.assertTrue(shards, "the %s job's matrix lists no shard" % job)
                clause = r"\$\{\{\s*%s\s*\}\}" % re.escape(self.SHARD_CLAUSE)
                names = [re.sub(clause, lambda _m, k=k: ", shard %s" % k, n) for n in names for k in shards]
            for expr, (value,) in self.RENDERED.items():
                names = [re.sub(r"\$\{\{\s*%s\s*\}\}" % re.escape(expr), value, n) for n in names]
            out[job] = names
        return out

    def test_the_real_ci_yml_names_every_job_a_batch_push_runs(self):
        """ci.yml as this checkout holds it (committed in a repository of its own, so the tree needs no git): each job
        is read, the name each of its job runs renders on a batch push (batch_push_checks, derived from the file's job
        ids) matches that job and no other, and the tier-label check matches none."""
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        expected = {job: rx for job, _name, rx in self.jobs(text)}
        checks = self.batch_push_checks(text)
        self.assertEqual(sorted(expected), sorted(sweep.workflow_jobs(text)))
        self.assertEqual(sorted(checks), sorted(expected), "every job is rendered")
        for job, names in checks.items():
            for name in names:
                with self.subTest(job=job, name=name):
                    self.assertNotIn("${{", name, "rendered whole")
                    self.assertEqual([j for j, rx in expected.items() if rx.fullmatch(name)], [job])
        self.assertFalse(any(rx.fullmatch("Exactly one tier label") for rx in expected.values()))

    def test_the_maintainer_steps_name_every_check_a_batch_push_reports(self):
        """docs/batching.md's maintainer section lists the checks to require; it names every one a batch push reports, as
        batch_push_checks derives them from ci.yml: each job's rendered name in backticks, and for the python job its
        name with <version> for the version and <shard> for the shard, the shards and, for each shape of ci.yml's shape
        switch (2026-10-06), the Linux cells' versions listed after it (the shards since 2026-10-04). Both shapes are read
        whichever the file's three lines say (wf.with_shape), so the doc holds for either and a switch of the shape needs no
        edit here. At the round-2 fix head it named four of the six jobs, not the vendored-tooling and served-pages jobs
        PR 928 added."""
        wf = _ci_workflow_readers()
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        doc = (ROOT / "docs" / "batching.md").read_text(encoding="utf-8")
        start = doc.index("## If you are the maintainer")
        section = doc[start:doc.index("\n## ", start + 1)]
        para = re.sub(r"\s+", " ", section)
        m = re.search(r"`Python <version> \(ubuntu-latest, shard <shard>\)` for each shard \(([^)]*)\) and each Linux cell a "
                      r"batch push runs: under ci\.yml's full shape, the default \(([^)]*)\), and under its smaller shape "
                      r"\(([^)]*)\)", para)
        self.assertIsNotNone(m, "the python job's checks are named as `Python <version> (ubuntu-latest, shard <shard>)` with "
                                "the shards and each shape's versions")

        def words(group):
            return [w.strip() for w in re.split(r",|\band\b", group) if w.strip()]
        shards = words(m.group(1))
        for shape, group in zip(wf.SHAPES, (m.group(2), m.group(3))):
            listed = sorted("%s (ubuntu-latest, shard %s)" % (v, k) for v in words(group) for k in shards)
            for job, names in self.batch_push_checks(wf.with_shape(text, shape)).items():
                with self.subTest(shape=shape, job=job):
                    if job == "python":
                        self.assertEqual(listed, sorted(n[len("Python "):] for n in names))
                    else:
                        for name in names:
                            self.assertTrue("`%s`" % name in para, "docs/batching.md's maintainer section does not name %s"
                                            % name)

    def test_lands_gate_reads_a_batch_run_of_either_shape_as_complete(self):
        """land's CI gate (batch.ci_jobs and batch.unmet_ci_jobs, read by batch_ci_run) holds a batch run to one passing
        job run for each job of ci.yml, matched by its rendered name, so a batch push under the smaller shape, eight
        Python jobs (3.12 and 3.14t, four shards each) where full runs twenty, meets it as full's does (2026-10-06; no
        change to batch.py). It is no stronger than that: a run whose Python jobs are 3.12's alone meets it too, and the
        per-shape cells are held by tests/test_ci_shards.py's ShapeSwitch, which the sweep runs at every batch head. A run
        with no Python job, or a failed one only, does not meet it."""
        wf = _ci_workflow_readers()
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for shape in wf.SHAPES:
            src = wf.with_shape(text, shape)
            expected = self.jobs(src)
            checks = self.batch_push_checks(src)
            runs = [{"name": n, "status": "completed", "conclusion": "success"} for names in checks.values() for n in names]
            with self.subTest(shape=shape):
                self.assertEqual(len(checks["python"]), {"full": 20, "smaller": 8}[shape])
                self.assertEqual(batch.unmet_ci_jobs(expected, runs), [])
                no_python = [r for r in runs if not r["name"].startswith("Python ")]
                self.assertEqual([job for job, _name in batch.unmet_ci_jobs(expected, no_python)], ["python"])
                failed = [dict(r, conclusion="failure") if r["name"].startswith("Python ") else r for r in runs]
                self.assertEqual([job for job, _name in batch.unmet_ci_jobs(expected, failed)], ["python"])

    def test_a_ci_yml_it_cannot_read_that_way_is_refused(self):
        for label, ci, text in (("no ci.yml", None, "could not read .github/workflows/ci.yml at"),
                                ("no job", "name: CI\njobs:\n", "holds no job, so no CI run of it tested the batch head"),
                                ("a block scalar name", "name: CI\njobs:\n  a:\n    name: >\n      A\n    steps:\n      - run: x\n",
                                 "names its a job '>', a form this read does not take"),
                                ("a shallow line in a job", "name: CI\njobs:\n  a:\n    steps:\n      - run: x\n   stray: 1\n",
                                 "the a job holds line 6 ('   stray: 1'), indented fewer than four spaces")):
            with self.subTest(case=label):
                with self.assertRaises(batch.Fail) as cm:
                    self.jobs(ci)
                self.assertIn(text, str(cm.exception))


class PythonRemedy(unittest.TestCase):
    """Round 2, extra9-8: the reader's missing line (sweep.py) and finish's merge-commit remedies (batch.py) name
    `--python <python>` with one explanation, kept as one text in both scripts."""

    def test_the_two_scripts_explain_python_in_one_text(self):
        self.assertEqual(batch.PYTHON_REMEDY, sweep.PYTHON_REMEDY)
        self.assertIn("--served-python", batch.PYTHON_REMEDY)


class VerifyBehind(_Base):
    """ci.yml does not run on the merge to main (2026-09-27), so a batch should land only when its head contains main
    as origin has it at that moment: then the merge commit's tree is the batch head's, the tree the sweep and the
    batch branch's CI ran on. verify refuses a batch head that does not contain main, reading main with ls-remote,
    so a stale tracking ref (land --no-fetch) cannot hide a move; land, which re-runs verify, refuses before it
    merges anything, and reads main again right before the merge call (round 1, extra7-4: what these tests show is
    that check, not that the merged tree is always the batch head's). A move between that last read and GitHub's
    merge is not stopped; finish reports it loudly from the merge commit's first parent (LandAndFinish)."""

    def ready(self, summarize=False):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   main: origin/main at %s is in the batch head" % fx.bare_rev("main")[:10], p.stdout)
        if summarize:
            fx.push_batch("b1")
            fx.ok("summarize", "b1")
            fx.ci("b1")

    def test_verify_refuses_a_batch_behind_main_until_main_is_merged_in(self):
        fx = self.fx
        self.ready()
        head = fx.dev_git("rev-parse", "batch/b1")
        moved = fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin/main is at %s, which the batch head %s does not contain" % (moved[:10], head[:10]), p.stdout)
        self.assertIn("`scripts/batch.py assemble b1 --merge-main`, then sweep and verify again", p.stdout)
        self.assertIn("ok   sweep at %s: pass" % head[:10], p.stdout, "the sweep at the head is fine; main moved")
        fx.ok("assemble", "b1", "--merge-main")
        fx.sweep("b1")
        p = fx.ok("verify", "b1")
        self.assertIn("ok   main: origin/main at %s is in the batch head" % moved[:10], p.stdout)

    def test_verify_refuses_when_origin_has_no_main(self):
        """Round 1, extra4-8: with no main on origin there is nothing to compare the batch head with, and verify fails by
        name, with --no-fetch too (a plain fetch would drop the tracking ref and fail earlier, in provenance)."""
        fx = self.fx
        self.ready()
        fx._git("update-ref", "-d", "refs/heads/main", cwd=fx.bare)
        self.assertTrue(fx.dev_git("rev-parse", "origin/main"), "the dev clone keeps its stale tracking ref")
        p = fx.run("verify", "b1", "--no-fetch")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin has no main branch to compare the batch head with", p.stdout)
        self.assertFalse(fx.state("b1")["verified"]["ok"])

    def test_land_refuses_a_batch_behind_main_and_merges_nothing(self):
        fx = self.fx
        self.ready(summarize=True)
        fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin/main is at", p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN")

    def test_land_without_a_fetch_still_reads_main_on_origin(self):
        fx = self.fx
        self.ready(summarize=True)
        moved = fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        self.assertNotEqual(fx.dev_git("rev-parse", "origin/main"), moved, "the dev clone has not fetched the move")
        p = fx.run("land", "b1", "--no-fetch")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin/main is at %s (not fetched here), which the batch head" % moved[:10], p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")


    def test_land_refuses_when_main_moves_after_its_verify(self):
        """land's verify passes, then main moves (a merge by hand) before the merge call: the last read
        of main, right before `gh pr merge`, sees it and nothing is merged. The move is made by a gh
        wrapper on the settings read, which land makes after its verify."""
        fx = self.fx
        self.ready(summarize=True)
        wrapper = os.path.join(fx.tmp, "gh-moves-main")
        with open(wrapper, "w") as f:
            f.write(MOVE_MAIN_GH % {"python": sys.executable})
        os.chmod(wrapper, 0o755)
        fx.env["ROMP_GH"] = wrapper
        fx.env["MOVE_MAIN_AUTHOR"] = fx.author
        fx.env["MOVE_MAIN_FAKE_GH"] = os.path.join(fx.bin, "gh")
        before = fx.bare_rev("main")
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("ok   main: origin/main at %s is in the batch head" % before[:10], p.stdout, "verify passed first")
        moved = fx.bare_rev("main")
        self.assertNotEqual(moved, before, "the wrapper moved main")
        self.assertIn("main moved on origin to %s after verify read %s; nothing merged" % (moved[:10], before[:10]), p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")

    def test_main_is_read_by_its_exact_ref_name(self):
        """`git ls-remote origin refs/heads/main` matches the pattern against the tail of every ref name, so a
        branch named aaa/refs/heads/main answers it too, and sorts first. A decoy there at the old main (which
        the batch contains) must not stand in for main after main moves."""
        fx = self.fx
        self.ready()
        old = fx.bare_rev("main")
        fx._git("update-ref", "refs/heads/aaa/refs/heads/main", old, cwd=fx.bare)
        moved = fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin/main is at %s" % moved[:10], p.stdout)

    def test_land_reads_the_batch_branch_by_its_exact_ref_name(self):
        """The same tail match on land's read of the batch branch: with the branch gone from origin and a decoy
        aaa/refs/heads/batch/b1 at the verified head, land must say the batch is not pushed, not merge."""
        fx = self.fx
        self.ready(summarize=True)
        head = fx.dev_git("rev-parse", "batch/b1")
        fx._git("update-ref", "refs/heads/aaa/refs/heads/batch/b1", head, cwd=fx.bare)
        fx._git("update-ref", "-d", "refs/heads/batch/b1", cwd=fx.bare)
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("batch/b1 on origin is at nothing, verified %s; push the batch first" % head[:10], p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")


# A gh for one test: on the first call that starts with MOVE_MAIN_ON (default the repository-settings read, which land
# makes after its verify) it pushes one commit to main from the author clone, once, then hands every call to the fake gh.
MOVE_MAIN_GH = r"""#!%(python)s
import os, subprocess, sys
flag = os.environ["MOVE_MAIN_AUTHOR"] + ".moved"
on = os.environ.get("MOVE_MAIN_ON", "repo view").split()
if sys.argv[1:1 + len(on)] == on and not os.path.exists(flag):
    open(flag, "w").close()
    a = os.environ["MOVE_MAIN_AUTHOR"]
    run = lambda *c: subprocess.run(["git", *c], cwd=a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run("fetch", "-q", "origin")
    run("checkout", "-q", "-B", "main", "origin/main")
    with open(os.path.join(a, "moved.txt"), "w") as f:
        f.write("moved after verify\n")
    run("add", "moved.txt")
    run("commit", "-q", "-m", "a merge by hand after verify")
    run("push", "-q", "origin", "main")
os.execv(sys.executable, [sys.executable, os.environ["MOVE_MAIN_FAKE_GH"], *sys.argv[1:]])
"""


class LandReadsTheSweep(_Base):
    """land re-runs verify, so it refuses on the sweep result at the verified head the way verify does,
    and merges on a pass with no free text ever given."""

    def ready(self):
        fx = self.fx
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        fx.ci("b1")

    def test_a_red_result_at_the_head_stops_land_before_the_merge(self):
        fx = self.fx
        self.ready()
        legs = {n: {"owed": True, "rc": 0, "tests": 1, "failed": 0} for n in sweep.LEGS}
        legs["pytest"]["rc"] = 1
        fx.sweep("b1", legs=legs)
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL sweep red at", p.stdout)
        self.assertIn("pytest (rc 1)", p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_a_pass_lands(self):
        fx = self.fx
        self.ready()
        p = fx.ok("land", "b1")
        self.assertEqual(len(fx.calls("pr", "merge")), 1)
        self.assertIn("ok   sweep at", p.stdout)
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")


class LandReadsTheCI(_Base):
    """land requires the batch head's one GitHub run green, as well as the local sweep (pre-round ruling Q3): the
    newest run of ci.yml from a push to the batch branch at exactly the verified head, read from GitHub when land
    runs, before it retargets or merges anything. Missing, pending and red are refused by name, and so is a read
    that fails; a run at another sha, from another event or on another branch is not that run."""

    def ready(self):
        fx = self.fx
        self.head = None
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n"})
        fx.branch("b", {"b.txt": "b\n"}, base="a")
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.pr(102, "b", base="a", title="b on a", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        self.head = fx.dev_git("rev-parse", "batch/b1")

    def refused(self, *needles, args=("land", "b1"), gh_fail=None):
        fx = self.fx
        p = fx.run(*args, gh_fail=gh_fail)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        for needle in needles:
            self.assertIn(needle, p.stderr)
        self.assertIn("nothing merged", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")
        self.assertEqual(fx.calls("pr", "edit"), [], "nothing retargeted: the run is read before anything changes")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN")
        return p

    def test_a_missing_run_is_refused_and_the_read_is_made_at_land_time(self):
        fx = self.fx
        self.ready()
        before = len(fx.calls("run", "list"))
        self.refused("the batch head's CI run is missing: GitHub lists no run of ci.yml from a push to batch/b1 at %s" % self.head)
        self.assertEqual(fx.calls("run", "list")[before:],
                         [["run", "list", "--workflow", "ci.yml", "--branch", "batch/b1", "--event", "push", "--commit", self.head,
                           "--limit", "20", "--json", "databaseId,status,conclusion,headSha,headBranch,event,workflowName,url,createdAt,attempt"]],
                         "land itself asked GitHub for the run of the verified head")

    def test_a_pending_run_is_refused_with_or_without_auto(self):
        fx = self.fx
        self.ready()
        url = fx.ci("b1", status="in_progress", conclusion="")
        self.refused("the batch head's CI run is pending (status in_progress): %s" % url)
        fx.set_repo(allowAutoMerge=True)
        fx.set_gh(rulesets=[{"type": "required_status_checks"}])
        self.refused("the batch head's CI run is pending (status in_progress)", args=("land", "b1", "--auto"))

    def test_a_red_or_cancelled_run_is_refused(self):
        fx = self.fx
        self.ready()
        url = fx.ci("b1", conclusion="failure")
        self.refused("the batch head's CI run is red (conclusion failure): %s" % url, "scripts/batch.py bisect b1")
        fx.ci("b1", conclusion="cancelled")
        self.refused("the batch head's CI run is red (conclusion cancelled)")

    def test_a_run_at_another_sha_from_another_event_or_on_another_branch_is_not_the_run(self):
        fx = self.fx
        self.ready()
        fx.ci("b1", sha=fx.bare_rev("a"))                    # a green run, but of another commit
        fx.ci("b1", event="workflow_dispatch")               # the head, but a manual run
        fx.ci("b1", branch="batch/b0")                       # the head, but pushed to another branch
        fx.ci("b1", workflow="pr-tier.yml")                  # the head and the push, but another workflow
        self.refused("the batch head's CI run is missing")

    def test_a_fake_that_ignores_the_filters_still_cannot_stand_in(self):
        """gh's filters are asked for and then checked on every row: a gh that answered with runs of other commits,
        events or branches (an older gh that ignored --commit, say) still reads as missing."""
        fx = self.fx
        self.ready()
        wrapper = os.path.join(fx.tmp, "gh-ignores-filters")
        with open(wrapper, "w") as f:
            f.write(IGNORES_FILTERS_GH % {"python": sys.executable})
        os.chmod(wrapper, 0o755)
        fx.env["ROMP_GH"] = wrapper
        fx.env["IGNORES_FILTERS_FAKE_GH"] = os.path.join(fx.bin, "gh")
        fx.env["IGNORES_FILTERS_HEAD"] = self.head
        self.refused("the batch head's CI run is missing")

    def test_a_created_time_tie_is_decided_by_the_run_id_whatever_the_order_gh_lists(self):
        """Round 1, extra4-4: the newest run is the latest createdAt, then the highest databaseId. Two runs at the head
        created in the same second, served oldest first: the newer, red, decides."""
        fx = self.fx
        self.ready()
        fx.set_gh(runs_as_recorded=True)
        fx.ci("b1", createdAt="2026-01-01T00:05:00Z")
        url = fx.ci("b1", conclusion="failure", createdAt="2026-01-01T00:05:00Z")
        self.refused("the batch head's CI run is red (conclusion failure): %s" % url)

    def test_a_matching_row_that_cannot_be_ordered_is_refused_by_name(self):
        """Round 1, extra4-4 (decision 14): a matching row with no valid createdAt (none, null, the zero time gh renders
        for a missing time, the Unix epoch, not RFC 3339) or no valid databaseId would sort oldest or not at all, and an
        older green run would decide over it. Served newest first as a red run, with a dated green run after it: land
        refuses by name, where the head merged on the green."""
        cases = (("no createdAt", {"createdAt": MISSING}, "no createdAt"),
                 ("a null createdAt", {"createdAt": None}, "no createdAt"),
                 ("the zero time", {"createdAt": "0001-01-01T00:00:00Z"},
                  "createdAt '0001-01-01T00:00:00Z', a placeholder before 2000 (the zero time 0001-01-01T00:00:00Z is one)"),
                 ("the Unix epoch", {"createdAt": "1970-01-01T00:00:00Z"}, "createdAt '1970-01-01T00:00:00Z', a placeholder"),
                 ("not RFC 3339", {"createdAt": "2026-01-01 00:09:00"}, "createdAt '2026-01-01 00:09:00', not an RFC 3339 time"),
                 # an RFC 3339 form that names no real date is not a placeholder: its own reason, not the zero time's
                 ("an impossible date", {"createdAt": "2026-02-30T00:09:00Z"},
                  "createdAt '2026-02-30T00:09:00Z', RFC 3339 in form but not a real date and time"),
                 ("an impossible offset", {"createdAt": "2026-01-01T00:09:00+24:00"},
                  "createdAt '2026-01-01T00:09:00+24:00', RFC 3339 in form but not a real date and time"),
                 ("no databaseId", {"databaseId": MISSING}, "no databaseId"),
                 ("a databaseId string", {"databaseId": "9"}, "databaseId '9', not a positive integer"),
                 ("a databaseId bool", {"databaseId": True}, "databaseId True, not a positive integer"),
                 # decision 13: the attempt decides which earlier attempts land reads, so it is read as strictly
                 ("no attempt", {"attempt": MISSING}, "no attempt"),
                 ("attempt 0", {"attempt": 0}, "attempt 0, not a positive integer"),
                 ("an attempt string", {"attempt": "2"}, "attempt '2', not a positive integer"))
        for label, fields, named in cases:
            with self.subTest(label):
                self.setUp()
                fx = self.fx
                self.ready()
                fx.set_gh(runs_as_recorded=True)
                url = fx.ci("b1", conclusion="failure", **dict({"databaseId": 9, "createdAt": "2026-01-01T00:09:00Z"}, **fields))
                fx.ci("b1", databaseId=5, createdAt="2026-01-01T00:05:00Z")
                p = self.refused("the batch head's CI run cannot be chosen: gh run list gave a matching run (%s) with %s" % (url, named))
                self.assertNotIn("ok   CI", p.stdout)

    FLAKE = "tests/test_notes.py::test_order (a known flake, recorded in the flake census)"

    def test_an_earlier_failed_attempt_is_refused_unless_flake_names_it(self):
        """Round 1, fresh-2 under decision 13: a red is not erased by a re-run on GitHub either. A run green on attempt 2
        whose attempt 1 failed is refused, naming the attempt and the --flake that excuses it; with --flake naming it,
        land merges, its ok line names the excused attempt, the state records it, and finish reports it. The head
        merged such a run with nothing recorded."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        before = len(fx.calls("api"))
        self.refused("the batch head's CI run %s is green on attempt 2, but attempt 1 concluded failure (%s/attempts/1), and a "
                     "red is not erased by a re-run: if that attempt failed on a known flake, land again with --flake 1/1="
                     % (url, url))
        self.assertEqual([c[1] for c in fx.calls("api")[before:]], ["repos/{owner}/{repo}/actions/runs/1/attempts/2/jobs?per_page=100",
                                                                    "repos/{owner}/{repo}/actions/runs/1/attempts/1"],
                         "land read the latest attempt's jobs (decision 18) and the earlier attempt from GitHub")
        p = fx.ok("land", "b1", "--flake", "1/1=" + self.FLAKE)
        self.assertIn("ok   CI: the run of the push to batch/b1 at %s is green: %s; attempt 1 concluded failure and is excused "
                      "as a known flake (%s/attempts/1): %s" % (self.head[:10], url, url, self.FLAKE), p.stdout)
        self.assertEqual(len(fx.calls("pr", "merge")), 1)
        st = fx.state("b1")
        self.assertEqual(st["ci"], {"run": url, "id": 1, "attempt": 2, "head": self.head, "excused": [
            {"run": 1, "attempt": 1, "status": "completed", "conclusion": "failure", "url": url + "/attempts/1", "flake": self.FLAKE}]})
        self.assertIn("observed: the batch head's CI run was green on a re-run: attempt 1 concluded failure (%s/attempts/1) and "
                      "land excused it as a known flake: %s" % (url, self.FLAKE), p.stdout)

    def land_refused_after_the_ci_read(self, *args):
        """land with `args`, main moved on the repository-settings read: land reads the CI run, records it, then refuses on
        its own read of main."""
        fx = self.fx
        wrapper = os.path.join(fx.tmp, "gh-moves-main")
        with open(wrapper, "w") as f:
            f.write(MOVE_MAIN_GH % {"python": sys.executable})
        os.chmod(wrapper, 0o755)
        env = dict(fx.env)
        fx.env.update(ROMP_GH=wrapper, MOVE_MAIN_AUTHOR=fx.author, MOVE_MAIN_FAKE_GH=os.path.join(fx.bin, "gh"), MOVE_MAIN_ON="repo view")
        p = fx.run("land", "b1", *args)
        fx.env = env
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("after verify read", p.stderr)
        return p

    def test_finish_reports_an_excused_attempt_only_for_the_run_it_read(self):
        """land's CI record in the state names the run and the head it read, and verify (or a new assembly) clears it:
        after a land that excused attempt 1 of run 1 and was then refused (main moved), a merge of main, a new sweep and
        verify, a green run 2 at the new head and a merge by hand, finish names run 2 and reports no excused attempt.
        The stage 1 to 3 head reported run 1's excuse as the landed head's. A merge by hand of the same head, with the
        state's record still land's, reports it."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        self.land_refused_after_the_ci_read("--flake", "1/1=" + self.FLAKE)
        self.assertEqual(fx.state("b1")["ci"]["head"], self.head)
        fx.ok("assemble", "b1", "--merge-main")
        self.assertIsNone(fx.state("b1")["ci"], "a new assembly clears land's record")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.push_batch("b1")
        url2 = fx.ci("b1")
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.ok("finish", "b1")
        self.assertIn("the batch head's CI run: green, %s" % url2, p.stdout)
        self.assertNotIn("land excused it", p.stdout)
        self.assertNotIn(url + "/attempts/1", p.stdout)

    def test_finish_reports_the_excused_attempt_of_the_run_it_read(self):
        """The same record, with the head unchanged and merged by hand after land's refusal: it is the run finish reads,
        so finish reports the excused attempt; a verify alone clears the record too."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        self.land_refused_after_the_ci_read("--flake", "1/1=" + self.FLAKE)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.run("finish", "b1")
        self.assertIn("observed: the batch head's CI run was green on a re-run: attempt 1 concluded failure (%s/attempts/1) and "
                      "land excused it as a known flake: %s" % (url, self.FLAKE), p.stdout)
        path = os.path.join(fx.dev, ".git", "batch", "b1.json")
        with open(path) as f:
            st = json.load(f)
        st["ci"] = {"run": url, "id": 1, "attempt": 2, "head": self.head, "excused": []}
        st["verified"] = dict(st["verified"], ok=True)
        with open(path, "w") as f:
            json.dump(st, f)
        fx.run("verify", "b1")
        self.assertIsNone(fx.state("b1")["ci"], "verify clears land's record")
        with open(path) as f:
            st = json.load(f)
        st["ci"] = {"run": url, "id": 1, "attempt": 2, "head": self.head, "excused": []}
        with open(path, "w") as f:
            json.dump(st, f)
        fx.ok("assemble", "b1", "--without", "102")
        self.assertIsNone(fx.state("b1")["ci"], "so does a rebuild")

    def test_finish_reports_no_excuse_of_a_run_it_did_not_read(self):
        """With land's record still in the state (refused after its CI read, no new verify), a later push run at the same
        head is the run finish reads, so the record's excused attempt, run 1's, is not reported as that run's."""
        fx = self.fx
        self.ready()
        fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        self.land_refused_after_the_ci_read("--flake", "1/1=" + self.FLAKE)
        url2 = fx.ci("b1")
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.run("finish", "b1")
        self.assertIn("the batch head's CI run: green, %s" % url2, p.stdout)
        self.assertNotIn("land excused it", p.stdout)

    def test_every_earlier_attempt_that_did_not_pass_counts(self):
        """A cancelled earlier attempt did not pass either, and two earlier attempts that did not pass are refused
        whatever --flake says (a known flake is excused once, as the local sweep's is); a green re-run of a green
        attempt needs no flake."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "cancelled"}])
        self.refused("is green on attempt 2, but attempt 1 concluded cancelled (%s/attempts/1)" % url)
        fx.set_gh(runs=[])              # each case alone at the head: an older run at the head is read too (below)
        url = fx.ci("b1", attempt=3, attempts=[{"conclusion": "failure"}, {"conclusion": "timed_out"}])
        self.refused("the batch head's CI run %s is green on attempt 3, but attempt 1 concluded failure (%s/attempts/1) and "
                     "attempt 2 concluded timed_out (%s/attempts/2); a known flake is excused once" % (url, url, url),
                     args=("land", "b1", "--flake", "1/1=" + self.FLAKE, "--flake", "1/2=" + self.FLAKE))
        fx.set_gh(runs=[])
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "success"}])
        p = fx.ok("land", "b1")
        self.assertIn("ok   CI: the run of the push to batch/b1 at %s is green: %s\n" % (self.head[:10], url), p.stdout)
        self.assertEqual(fx.state("b1")["ci"]["excused"], [])

    def test_a_flake_that_names_no_failed_attempt_is_refused(self):
        """--flake must name a failed earlier attempt of the run land read: one of a green first attempt, of an attempt
        that passed, or of another run is refused, and a malformed value is a usage refusal before anything is read."""
        fx = self.fx
        self.ready()
        fx.ci("b1")
        self.refused("--flake names run 1 attempt 1, which is no failed attempt of a run at the batch head (its CI run",
                     args=("land", "b1", "--flake", "1/1=" + self.FLAKE))
        fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        self.refused("--flake names run 9 attempt 1, which is no failed attempt of a run at the batch head",
                     args=("land", "b1", "--flake", "9/1=" + self.FLAKE))
        # run 1, older and green on its one attempt, has no failed attempt to excuse either
        self.refused("--flake names run 1 attempt 1, which is no failed attempt of a run at the batch head (its CI run "
                     "https://example.invalid/actions/runs/2, attempt 2, run 2, and run 1)",
                     args=("land", "b1", "--flake", "1/1=" + self.FLAKE, "--flake", "2/1=" + self.FLAKE))
        for bad in ("1=" + self.FLAKE, "2/1=  ", "2/1"):
            with self.subTest(bad=bad):
                p = fx.run("land", "b1", "--flake", bad)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn("--flake %r: expected RUN/ATTEMPT=TEXT" % bad, p.stderr)
                self.assertEqual(fx.calls("pr", "merge"), [])

    def test_an_attempt_that_cannot_be_read_is_refused(self):
        """An earlier attempt read that fails, or that answers with another record, is refused: an attempt not read is
        not one that passed."""
        fx = self.fx
        self.ready()
        fx.ci("b1", attempt=2, attempts=[{"conclusion": "success"}])
        self.refused("could not read attempt 1 of the batch head's CI run", "HTTP 502",
                     gh_fail="api repos/{owner}/{repo}/actions/runs/1/attempts/1")
        fx.ci("b1", attempt=2, attempts=[{"conclusion": "success", "run_attempt": 2}])
        self.refused("attempt 1 of the batch head's CI run https://example.invalid/actions/runs/2 read as another record "
                     "(id 2, run_attempt 2)")
        fx.ci("b1", attempt=3, attempts=[{"conclusion": "success"}])
        self.refused("could not read attempt 2 of the batch head's CI run", "HTTP 404")

    def test_a_run_list_that_is_not_json_is_refused_by_name(self):
        """Round 1, extra4-8: a `gh run list` that answers with something that is not JSON (an HTML error page) is
        refused by name, not read as a missing run, and nothing is merged or retargeted."""
        fx = self.fx
        self.ready()
        fx.ci("b1")
        wrapper = os.path.join(fx.tmp, "gh-not-json")
        with open(wrapper, "w") as f:
            f.write(NOT_JSON_GH % {"python": sys.executable})
        os.chmod(wrapper, 0o755)
        fx.env["ROMP_GH"] = wrapper
        fx.env["NOT_JSON_FAKE_GH"] = os.path.join(fx.bin, "gh")
        p = self.refused("gh run list returned something that is not JSON")
        self.assertNotIn("is missing", p.stderr)

    def shape_gh(self, answer):
        fx = self.fx
        wrapper = os.path.join(fx.tmp, "gh-shape")
        if not os.path.exists(wrapper):
            with open(wrapper, "w") as f:
                f.write(SHAPE_GH % {"python": sys.executable})
            os.chmod(wrapper, 0o755)
        fx.env.update(ROMP_GH=wrapper, SHAPE_FAKE_GH=os.path.join(fx.bin, "gh"), SHAPE_GH_ANSWER=answer)

    SHAPES = (("an object", '{"message": "Bad credentials"}',
               'gh run list returned JSON that is not a list of runs (dict: {"message": "Bad credentials"})'),
              ("a string", '"a string"', 'gh run list returned JSON that is not a list of runs (str: "a string")'),
              ("null", "null", "gh run list returned JSON that is not a list of runs (NoneType: null)"),
              ("a list holding a non-object", '["not a run", {"databaseId": 1}]',
               'gh run list returned 1 row that is not a run record ("not a run")'),
              ("nothing", "", "gh run list returned nothing, not a JSON list of runs"))

    def test_a_run_list_that_is_json_but_not_a_list_of_runs_is_refused_by_name(self):
        """Round 2, extra8-3: a `gh run list` answer that is JSON but not a list (an error object, a string, null), a
        list holding a row that is not an object, and an empty answer are each refused naming the shape, never read as a
        missing run, and nothing is merged or retargeted. Before round 2 each read as no run: land refused it as missing,
        "push the batch and wait for its run"."""
        fx = self.fx
        self.ready()
        fx.ci("b1")
        for label, answer, named in self.SHAPES:
            with self.subTest(shape=label):
                self.shape_gh(answer)
                p = self.refused(named, "a read that returns no run records is not a missing run")
                self.assertNotIn("is missing", p.stderr)

    def test_finish_reports_a_run_list_of_another_shape_as_unread(self):
        """finish reads the same run after the merge: an answer of another shape is reported as unread, naming it, not as
        a missing run, and the cleanup still runs."""
        fx = self.fx
        self.ready()
        fx.ci("b1")
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        self.shape_gh('{"message": "Bad credentials"}')
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("the batch head's CI run: unread after the merge: gh run list returned JSON that is not a list of runs",
                      p.stdout)
        self.assertEqual(fx.state("b1")["finished"]["report"]["ci"]["case"], "unread")

    LABEL_CHECKS = [{"name": "Exactly one tier label", "status": "completed", "conclusion": "success"},
                    {"name": "Tier policy", "status": "completed", "conclusion": "skipped"}]

    PYTHON_UNMET = "the python job (Python ${{ matrix.python-version }} (ubuntu-latest))"

    def incomplete(self, jobs, unmet, listed):
        """The coordinator's decision 18: land refuses a run of ci.yml that concluded success unless every job of the
        head's ci.yml has a job run in its latest attempt that passed, naming each job with none and the job runs the
        attempt lists; nothing is merged."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", jobs=jobs)
        self.refused("the batch head's CI run %s concluded success, but .github/workflows/ci.yml at the head has %s with no "
                     "job run that passed in it (%s)" % (url, unmet, listed), "a success is read only over ci.yml's own jobs")

    def test_a_success_over_label_checks_alone_is_not_a_green_run(self):
        """Decision 18's ruled pin: a success whose latest attempt lists only the label checks (the tier-label check and
        Tier policy's skipped row, what a read of the checks on a fork head holds) is refused as incomplete. Before
        round 2 it merged on the run's conclusion alone."""
        self.incomplete(self.LABEL_CHECKS, "%s, the secrets job" % self.PYTHON_UNMET,
                        "its job runs: Exactly one tier label: success; Tier policy: skipped")

    def test_a_success_over_no_job_run_is_not_a_green_run(self):
        """A success whose latest attempt lists no job run at all is refused as incomplete. Before round 2 it merged."""
        self.incomplete([], "%s, the secrets job" % self.PYTHON_UNMET, "it lists no job run")

    def test_a_success_with_one_of_cis_jobs_skipped_is_not_a_green_run(self):
        """A skipped job reports success, so a success in which one of ci.yml's jobs was skipped is refused as
        incomplete, naming that job. Before round 2 it merged."""
        skipped = [dict(j) for j in SEED_CI_JOBS]
        skipped[2]["conclusion"] = "skipped"
        self.incomplete(skipped, "the secrets job", "its job runs: Python 3.12 (ubuntu-latest): success; "
                                                    "Python 3.13 (ubuntu-latest): success; secrets: skipped")

    def test_a_success_over_cis_jobs_lands_one_passing_run_per_job(self):
        """Each job of ci.yml needs one job run that passed: a matrix job whose other cell failed (a cell that may fail,
        such as a continue-on-error one, leaves the run's conclusion success) still has one, and the run lands; the
        label checks listed beside ci.yml's jobs change nothing."""
        fx = self.fx
        self.ready()
        jobs = [dict(j) for j in SEED_CI_JOBS] + self.LABEL_CHECKS
        jobs[1]["conclusion"] = "failure"
        fx.ci("b1", jobs=jobs)
        p = fx.ok("land", "b1")
        self.assertIn("ok   CI: the run of the push to batch/b1", p.stdout)
        self.assertEqual(len(fx.calls("pr", "merge")), 1)

    def test_a_jobs_read_that_fails_or_is_cut_is_refused_by_name(self):
        """The jobs listing is read as the attempts are: a read that fails, an answer that is not a listing, and a listing
        shorter than its total_count are each refused by name, never read as a green run."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1")
        self.refused("could not read the jobs of the batch head's CI run %s (attempt 1) (gh api)" % url,
                     gh_fail="api repos/{owner}/{repo}/actions/runs/1/attempts/1/jobs?per_page=100")
        fx.set_gh(runs=[])
        url = fx.ci("b1", jobs_doc=[])
        self.refused("the jobs of the batch head's CI run %s (attempt 1) read as something that is not a jobs listing" % url)
        fx.set_gh(runs=[])
        url = fx.ci("b1", jobs_doc={"total_count": 5, "jobs": SEED_CI_JOBS})
        self.refused("the jobs of the batch head's CI run %s (attempt 1) listed 3 of 5 jobs, so the rest may be cut" % url)

    def test_finish_reports_a_success_over_label_checks_alone_as_incomplete(self):
        """finish reads the same run after the merge: a success over the label checks alone is reported as incomplete,
        naming what it lacks, and the cleanup still runs."""
        fx = self.fx
        self.ready()
        url = fx.ci("b1", jobs=self.LABEL_CHECKS)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("the batch head's CI run: incomplete: it concluded success, but .github/workflows/ci.yml at the head "
                      "has the python job (Python ${{ matrix.python-version }} (ubuntu-latest)), the secrets job with no job "
                      "run that passed in it (its job runs: Exactly one tier label: success; Tier policy: skipped), %s" % url,
                      p.stdout)
        self.assertEqual(fx.state("b1")["finished"]["report"]["ci"]["case"], "incomplete")

    def test_the_newest_run_at_the_head_decides_and_an_older_red_one_is_not_erased(self):
        """The newest push run at the head is the one required green; an older push run at the same head (the same sha
        pushed again: the branch deleted and pushed back, or pushed elsewhere and back) is read as an earlier attempt is
        (round 1, decision 13: a red is not erased by a re-run, locally or on GitHub). Its red is refused, naming it
        and the --flake that excuses it; with that --flake land merges and records the excused run. The stage 1 to 3
        head merged green, red, green at one head with nothing refused or recorded."""
        fx = self.fx
        self.ready()
        fx.ci("b1")
        red = fx.ci("b1", conclusion="failure")
        self.refused("the batch head's CI run is red (conclusion failure)")
        url = fx.ci("b1")
        self.refused("the batch head's CI run %s is green on attempt 1, but an earlier run at this head, %s, attempt 1, "
                     "concluded failure (%s), and a red is not erased by a re-run: if that attempt failed on a known flake, "
                     "land again with --flake 2/1=" % (url, red, red))
        p = fx.ok("land", "b1", "--flake", "2/1=" + self.FLAKE)
        self.assertIn("ok   CI: the run of the push to batch/b1 at %s is green: %s; an earlier run's attempt 1 concluded failure "
                      "and is excused as a known flake (%s): %s" % (self.head[:10], url, red, self.FLAKE), p.stdout)
        self.assertEqual(len(fx.calls("pr", "merge")), 1)
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")
        self.assertEqual(fx.state("b1")["ci"]["excused"], [
            {"run": 2, "attempt": 1, "status": "completed", "conclusion": "failure", "url": red, "flake": self.FLAKE}])
        self.assertIn("observed: the batch head's CI run was green after an earlier run at the same head: attempt 1 of run 2 "
                      "concluded failure (%s) and land excused it as a known flake: %s" % (red, self.FLAKE), p.stdout)

    def test_every_older_run_at_the_head_is_read_like_an_earlier_attempt(self):
        """An older run's own earlier attempts are read too, a cancelled older run did not pass either, and one excuse
        covers every run at the head: two failures across two runs are refused whatever --flake says. Older runs that
        passed need nothing."""
        fx = self.fx
        self.ready()
        older = fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        url = fx.ci("b1")
        self.refused("the batch head's CI run %s is green on attempt 1, but an earlier run at this head, %s, attempt 1, "
                     "concluded failure (%s/attempts/1)" % (url, older, older))
        fx.set_gh(runs=[])
        older = fx.ci("b1", conclusion="cancelled")
        url = fx.ci("b1")
        self.refused("but an earlier run at this head, %s, attempt 1, concluded cancelled (%s)" % (older, older))
        fx.set_gh(runs=[])
        first = fx.ci("b1", conclusion="failure")
        url = fx.ci("b1", attempt=2, attempts=[{"conclusion": "failure"}])
        self.refused("the batch head's CI run %s is green on attempt 2, but attempt 1 concluded failure (%s/attempts/1) and an "
                     "earlier run at this head, %s, attempt 1, concluded failure (%s); a known flake is excused once"
                     % (url, url, first, first), args=("land", "b1", "--flake", "1/1=" + self.FLAKE, "--flake", "2/1=" + self.FLAKE))
        fx.set_gh(runs=[])
        fx.ci("b1")
        fx.ci("b1", attempt=2, attempts=[{"conclusion": "success"}])
        url = fx.ci("b1")
        p = fx.ok("land", "b1")
        self.assertIn("ok   CI: the run of the push to batch/b1 at %s is green: %s\n" % (self.head[:10], url), p.stdout)
        self.assertEqual(fx.state("b1")["ci"]["excused"], [])

    def test_a_run_list_as_long_as_its_limit_is_refused(self):
        """Every run at the head is read, so a `gh run list` that returns as many rows as land asked for (it may have cut
        the older runs) is refused by name, not read short."""
        fx = self.fx
        self.ready()
        for _ in range(batch.RUN_LIST_LIMIT):
            fx.ci("b1")
        self.refused("gh run list returned %d rows, its limit, so older runs at the batch head may be cut" % batch.RUN_LIST_LIMIT)
        fx.set_gh(runs=[])
        for _ in range(batch.RUN_LIST_LIMIT - 1):
            fx.ci("b1")
        fx.ok("land", "b1")

    def test_the_workflow_name_land_matches_is_ci_yml_s(self):
        with open(ROOT / ".github" / "workflows" / batch.CI_WORKFLOW) as f:
            first = f.readline().strip()
        self.assertEqual(first, "name: %s" % batch.CI_WORKFLOW_NAME, "land matches a run's workflowName against ci.yml's name")

    def test_a_failed_read_is_refused_not_read_as_missing(self):
        fx = self.fx
        self.ready()
        fx.ci("b1")
        p = self.refused("could not read the batch head's CI run (gh run list)", "HTTP 502", gh_fail="run list")
        self.assertNotIn("is missing", p.stderr)


# A gh for one test: `run list` answers with every recorded run whatever the filters, the way a gh that ignored them
# would, plus four green runs that each miss one filter (another commit, a manual run, another branch, another
# workflow); every other call goes to the fake gh.
IGNORES_FILTERS_GH = r"""#!%(python)s
import json, os, subprocess, sys
fake = os.environ["IGNORES_FILTERS_FAKE_GH"]
if sys.argv[1:3] == ["run", "list"]:
    out = subprocess.run([sys.executable, fake, "run", "list", "--limit", "100", "--json",
                          "databaseId,status,conclusion,headSha,headBranch,event,workflowName,url,createdAt,attempt"], text=True, stdout=subprocess.PIPE).stdout
    rows = json.loads(out or "[]")
    head = os.environ["IGNORES_FILTERS_HEAD"]
    for n, sha, branch, event, name in ((90, "0" * 40, "batch/b1", "push", "CI"), (91, head, "batch/b1", "workflow_dispatch", "CI"),
                                        (92, head, "batch/b9", "push", "CI"), (93, head, "batch/b1", "push", "Docs")):
        rows.append({"databaseId": n, "status": "completed", "conclusion": "success", "headSha": sha, "headBranch": branch,
                     "event": event, "workflowName": name, "url": "https://example.invalid/actions/runs/%%d" %% n,
                     "createdAt": "2026-02-01T00:00:%%02dZ" %% n})
    print(json.dumps(rows))
    sys.exit(0)
os.execv(sys.executable, [sys.executable, fake, *sys.argv[1:]])
"""


# A gh for one test: `run list` answers with SHAPE_GH_ANSWER as it stands (valid JSON of another shape, or nothing);
# every other call goes to the fake gh.
SHAPE_GH = r"""#!%(python)s
import os, sys
fake = os.environ["SHAPE_FAKE_GH"]
if sys.argv[1:3] == ["run", "list"]:
    sys.stdout.write(os.environ["SHAPE_GH_ANSWER"])
    sys.exit(0)
os.execv(sys.executable, [sys.executable, fake, *sys.argv[1:]])
"""


# A gh for one test: `run list` answers with an HTML error page, as a proxy in the way would; every other call goes to
# the fake gh.
NOT_JSON_GH = r"""#!%(python)s
import os, sys
fake = os.environ["NOT_JSON_FAKE_GH"]
if sys.argv[1:3] == ["run", "list"]:
    print("<html><body>502 Bad Gateway</body></html>")
    sys.exit(0)
os.execv(sys.executable, [sys.executable, fake, *sys.argv[1:]])
"""


FAKE_TOOL = r"""#!%(python)s
import json, os, shutil, sys
# a stand-in for npm, bats, node and the pytest interpreter. As the interpreter the pytest leg's environment is built
# from: `-m venv DIR` makes DIR a venv whose python is a copy of this file, pip records each requirement there, and the
# runner's probe and the SDK step's import check read that record. Every leg passes and prints the closing counts its
# real tool prints, which the runner reads to know that tests ran.
here, args = os.path.abspath(sys.argv[0]), sys.argv[1:]
record = os.path.join(os.path.dirname(os.path.dirname(here)), "fake-installs.json")
installs = json.load(open(record)) if os.path.exists(record) else {}
if args[:2] == ["-m", "venv"]:
    os.makedirs(os.path.join(args[-1], "bin"))
    shutil.copy(here, os.path.join(args[-1], "bin", "python"))
    open(os.path.join(args[-1], "pyvenv.cfg"), "w").close()
    sys.exit(0)
if args[:3] == ["-m", "pip", "install"]:
    for a in args[3:]:
        if not a.startswith("-"):
            dist, _eq, version = a.partition("==")
            installs[dist.lower()] = version or "9.9.9"
    with open(record, "w") as f:
        json.dump(installs, f)
    sys.exit(0)
if args[:1] == ["-c"]:
    if "sweep probe" in args[1]:
        needs = (("pytest", "pytest"), ("xdist", "pytest-xdist"), ("pytest_timeout", "pytest-timeout"))
        print(json.dumps({"version": "3.99.0", "full": "3.99.0 (fake)", "ensurepip": True,
                          "missing": [m for m, d in needs if d not in installs], "dists": {d: installs.get(d) for d in args[2:]}}))
        sys.exit(0)
    sys.exit(0 if args[1] != "import claude_agent_sdk" or "claude-agent-sdk" in installs else 1)
print({"fakepython": "1 passed in 0.01s", "python": "1 passed in 0.01s", "bats": "1..1\nok 1 a",
       "node": "# pass 1\n# fail 0"}.get(os.path.basename(here), ""))
sys.exit(0)
"""


class SweepThenVerify(_Base):
    """The composition: the real scripts/sweep.py runs in the batch worktree (fakes for the tools it calls),
    and verify reads what it wrote, with no path handed from one to the other. Both resolve the result
    from the state root and the full sha; a batch.py that looked anywhere else would say missing."""

    def test_the_runner_writes_what_verify_reads(self):
        fx = self.fx
        # the runner builds the pytest leg's environment from ci.yml's install steps (this tree's workflow), the SDK
        # at the pin its SDK step reads from kernel/session_host.py (a synthetic pin here)
        fx.branch("a", {"notes.txt": "one\ntwo\nthree\nfour\n", "tests/a.bats": "@test 'a' { true; }\n",
                        "tests/manager-a.test.js": "// manager\n", "tools/a.test.mjs": "// tools\n",
                        "vendor/track-changents/hooks/a.test.mjs": "// hooks\n",
                        ".github/workflows/ci.yml": (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"),
                        "kernel/session_host.py": 'SDK_TESTED_VERSION = "1.2.3"\n'})
        fx.pr(101, "a", title="notes: a fourth line", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        tools = os.path.join(fx.tmp, "tools-bin")
        os.makedirs(tools)
        for name in ("fakepython", "bats", "node"):
            with open(os.path.join(tools, name), "w") as f:
                f.write(FAKE_TOOL % {"python": sys.executable})
            os.chmod(os.path.join(tools, name), 0o755)
        # npm as npm's installs lay it out (bin/npm a link into npm's package, beside its package.json): the runner refuses
        # an npm whose package root it cannot find, since it reads npm's builtin config file there
        pkg = os.path.join(fx.tmp, "npm-install", "lib", "node_modules", "npm")
        os.makedirs(os.path.join(pkg, "bin"))
        with open(os.path.join(pkg, "package.json"), "w") as f:
            json.dump({"name": "npm", "version": "0.0.0-fake"}, f)
        with open(os.path.join(pkg, "bin", "npm-cli.js"), "w") as f:
            f.write(FAKE_TOOL % {"python": sys.executable})
        os.chmod(os.path.join(pkg, "bin", "npm-cli.js"), 0o755)
        os.symlink(os.path.join(pkg, "bin", "npm-cli.js"), os.path.join(tools, "npm"))
        env = dict(fx.env, PATH=tools + os.pathsep + fx.env["PATH"])
        p = subprocess.run([sys.executable, os.path.join(fx.dev, "scripts", "sweep.py"), "run", "--tree", fx.wt("b1"),
                            "--python", os.path.join(tools, "fakepython"), "--workers", "2"],
                           env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        head = fx.dev_git("rev-parse", "batch/b1")
        self.assertTrue(os.path.exists(os.path.join(fx.xdg, "romp", "sweeps", head + ".json")))
        p = fx.ok("verify", "b1")
        self.assertIn("ok   sweep at %s: pass" % head[:10], p.stdout)
        self.assertIn("pytest 0, bats 0, manager 0, tools 0; not owed: deps, ledger, typecheck, npm-test, pdf-smoke, build, served", p.stdout)
        with open(os.path.join(fx.xdg, "romp", "sweeps", head + ".json")) as f:
            sdk = json.load(f)["runs"][-1]["runner"]["sdk"]
        self.assertEqual((sdk["dist"], sdk["pin"], sdk["version"]), ("claude-agent-sdk", "1.2.3", "1.2.3"),
                         "the pytest leg ran in the environment built at ci.yml's pin")


class Pull(_Base):
    def test_pull_drops_the_member_and_its_dependents_and_rebuilds(self):
        fx = self.fx
        self.two_members()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", title="k alone", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        st = fx.state("b1")
        self.assertEqual(st["pr"]["number"], 900)
        gh = fx.gh()
        self.assertIn("batch", gh["prs"]["900"]["labels"])
        self.assertTrue(gh["prs"]["900"]["body"].startswith("# Batch b1: 3 PRs\n"))
        for n in ("101", "102", "111"):
            self.assertEqual(gh["prs"][n]["comments"], ["in batch b1 at %s" % st["assembly"]["head"]])
        before = fx.bare_rev("batch/b1")

        fx.ok("pull", "b1", "101", "--reason", "the maintainer asked")
        st = fx.state("b1")
        self.assertEqual(st["pulled"], [101, 102])
        self.assertEqual([e["n"] for e in st["assembly"]["merged"]], [111])
        self.assertNotEqual(fx.bare_rev("batch/b1"), before, "the rebuilt branch was pushed")
        self.assertEqual(fx.bare_rev("batch/b1"), st["assembly"]["head"])
        self.assertEqual(fx.chain("b1"), ["Merge #111: k alone"])
        gh = fx.gh()
        body = gh["prs"]["900"]["body"]
        self.assertTrue(body.startswith("# Batch b1: 1 PR (2 pulled)\n"), body.splitlines()[0])
        self.assertIn("- #101: pulled; the PR stays open against main.", body)
        self.assertIn("- #102: pulled; the PR stays open against main.", body)
        self.assertTrue(any(c.startswith("Pulled from batch b1 (the maintainer asked)") for c in gh["prs"]["101"]["comments"]))
        self.assertTrue(any(c.startswith("Dropped from batch b1 with #101") for c in gh["prs"]["102"]["comments"]))
        self.assertEqual(gh["prs"]["101"]["state"], "OPEN")
        self.assertIn("in batch b1 at %s" % st["assembly"]["head"], gh["prs"]["111"]["comments"], "the surviving member hears the new cut")
        self.assertIsNone(st["verified"], "a rebuild invalidates the verification")


class LandAndFinish(_Base):
    def ready(self):
        fx = self.fx
        self.two_members()
        fx.branch("m", {"m.txt": "m\n"}, base="a")
        fx.pr(112, "m", base="a", title="waits on hold, stacked on a", labels=["hold"])
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.sweep("b1")
        fx.ok("verify", "b1")
        fx.ok("summarize", "b1")
        fx.ci("b1")

    def test_land_refuses_a_repository_that_disallows_merge_commits(self):
        """Round 2, extra8-2: batch.py land keeps the retired land.sh refusal of a repository whose settings disallow
        merge commits (a batch lands as one merge commit, or its members stay open), and calls no merge."""
        fx = self.fx
        self.ready()
        fx.set_repo(mergeCommitAllowed=False)
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("the repository does not allow merge commits; a batch must land as one (repo settings)", p.stdout + p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_land_merges_with_a_merge_commit_and_finish_cleans_up(self):
        fx = self.fx
        self.ready()
        main_before = fx.bare_rev("main")
        tip = fx.state("b1")["assembly"]["head"]
        p = fx.ok("land", "b1")
        merges = fx.calls("pr", "merge")
        self.assertEqual(merges, [["pr", "merge", "900", "--merge", "--match-head-commit", tip]], "a merge commit, pinned to the verified head, no --auto without a ruleset")
        self.assertIn(["pr", "edit", "102", "--base", "main"], fx.calls("pr", "edit"), "the stacked member is retargeted before the merge")
        edits = [i for i, c in enumerate(fx.calls()) if c[:3] == ["pr", "edit", "102"]]
        merge_at = [i for i, c in enumerate(fx.calls()) if c[:2] == ["pr", "merge"]]
        self.assertLess(edits[0], merge_at[0], "retargeted BEFORE the merge, so GitHub's own marking applies")
        main_after = fx.bare_rev("main")
        parents = fx._git("rev-list", "--parents", "-n1", main_after, cwd=fx.bare).split()[1:]
        self.assertEqual(parents, [main_before, tip])
        gh = fx.gh()
        self.assertEqual(gh["prs"]["900"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["101"]["state"], "MERGED", "indirect merge marking")
        self.assertEqual(gh["prs"]["102"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["112"]["baseRefName"], "main", "a still-open dependent is retargeted")
        self.assertEqual(gh["prs"]["112"]["state"], "OPEN")
        for br in ("a", "b", "batch/b1"):
            self.assertEqual(fx.bare_rev(br), "", "%s is deleted on origin" % br)
        self.assertNotEqual(fx.bare_rev("m"), "", "the dependent's branch stays")
        self.assertFalse(os.path.exists(fx.wt("b1")))
        self.assertEqual(fx.dev_git("rev-parse", "--verify", "--quiet", "batch/b1", check=False), "")
        self.assertIn("batch #900 landed, 2 member(s) marked merged; no ci.yml run follows the merge to main; "
                      "the batch head's CI run: green, https://example.invalid/actions/runs/1", p.stdout)
        # Round 1, correctness-7: finish reads the run with land's own filtered read (batch_ci_run), not the newest run of
        # any event at the commit.
        self.assertEqual(fx.calls("run", "list")[-1], ["run", "list", "--workflow", "ci.yml", "--branch", "batch/b1", "--event", "push",
                                                       "--commit", tip, "--limit", "20", "--json", batch.CI_RUN_FIELDS],
                         "finish names the CI run of the push to the batch branch at the head, the one land gated on")
        self.assertEqual(len(fx.calls("run", "list")), 2, "land's read before the merge and finish's after it")
        # Pre-round item 4: the merge commit's first parent is the main verify read, so finish reports nothing loud.
        self.assertNotIn("FIRST PARENT", p.stdout + p.stderr)
        self.assertEqual(fx.state("b1")["finished"]["report"]["first_parent"], {"merge": main_after, "first_parent": main_before, "verified_main": main_before, "ok": True})
        self.assertEqual(fx.state("b1")["finished"]["report"]["landed_head"], {"merge": main_after, "second_parent": tip, "verified_head": tip, "ok": True})
        self.assertIn("retargeted to main: #112", p.stdout)
        self.assertIn("pr-orphans.sh: clean", p.stdout)
        rep = fx.state("b1")["finished"]["report"]
        self.assertEqual(rep["merged"], [101, 102])
        self.assertEqual(rep["deleted"], ["a", "b"], "the fake keeps indirectly merged heads, so finish deleted them and said so")
        self.assertTrue(any("finish deleted head branches" in o for o in rep["observations"]))
        self.assertIn("postal (kind: coordinate) to the owners of #101, #102", p.stdout)

    def test_finish_names_the_push_run_land_gated_on_not_a_later_manual_run_at_the_head(self):
        """Round 1, correctness-7, regression-3 and extra7-9: finish named the newest ci.yml run of any event at the batch
        head, so a manual run started after land's green push run (a macOS dispatch, red) was reported as the batch head's
        run. It reads the run land gated on, and prints its case."""
        fx = self.fx
        self.ready()
        tip = fx.state("b1")["assembly"]["head"]
        fx.ci("b1", event="workflow_dispatch", conclusion="failure", sha=tip)
        p = fx.ok("land", "b1")
        self.assertNotIn("actions/runs/2", p.stdout, "the later manual run is not the batch head's run")
        self.assertIn("the batch head's CI run: green, https://example.invalid/actions/runs/1", p.stdout)
        self.assertEqual(fx.state("b1")["finished"]["report"]["ci"],
                         {"case": "green", "url": "https://example.invalid/actions/runs/1", "status": "completed",
                          "conclusion": "success", "error": None})

    def test_finish_reports_the_ci_run_unread_after_the_merge_and_carries_on(self):
        """finish runs after the merge, so a run list that fails there is reported as unread, with gh's error, and never
        as "nothing merged"; the cleanup still runs and finish exits 0. A missing run is named as missing."""
        fx = self.fx
        self.ready()
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.run("finish", "b1", gh_fail="run list")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("the batch head's CI run: unread after the merge: could not read the batch head's CI run (gh run list): "
                      "fake gh: HTTP 502", p.stdout)
        self.assertNotIn("nothing merged", p.stdout + p.stderr)
        self.assertEqual(fx.bare_rev("batch/b1"), "", "the cleanup ran")
        self.assertEqual(fx.state("b1")["finished"]["report"]["ci"]["case"], "unread")
        fx.set_gh(runs=[])
        tip = fx.state("b1")["assembly"]["head"]
        p = fx.ok("finish", "b1")
        self.assertIn("the batch head's CI run: missing: GitHub lists no run of ci.yml from a push to batch/b1 at %s" % tip, p.stdout)

    def move_main_on(self, call):
        """Hand the tool a gh that pushes one commit to main from the author clone on the first call starting with `call`,
        then goes on to the fake gh."""
        fx = self.fx
        wrapper = os.path.join(fx.tmp, "gh-moves-main")
        with open(wrapper, "w") as f:
            f.write(MOVE_MAIN_GH % {"python": sys.executable})
        os.chmod(wrapper, 0o755)
        fx.env.update(ROMP_GH=wrapper, MOVE_MAIN_AUTHOR=fx.author, MOVE_MAIN_FAKE_GH=os.path.join(fx.bin, "gh"), MOVE_MAIN_ON=call)

    def test_land_refuses_a_main_move_before_it_retargets_anything(self):
        """Round 1, correctness-6 and extra4-9: land retargeted a stacked member to main before its last read of main, so a
        move already made refused with "nothing merged" while #102's base had been changed on GitHub. land reads main
        before the retarget too, so a move seen by then refuses with nothing on GitHub changed (the move is made on the
        repository-settings read, after land's verify)."""
        fx = self.fx
        self.ready()
        before = fx.bare_rev("main")
        self.move_main_on("repo view")
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        moved = fx.bare_rev("main")
        self.assertNotEqual(moved, before, "the wrapper moved main")
        self.assertEqual(fx.calls("pr", "edit"), [], "no member was retargeted")
        self.assertIn("main moved on origin to %s after verify read %s; nothing merged, and nothing on GitHub was changed"
                      % (moved[:10], before[:10]), p.stderr)
        self.assertEqual(fx.gh()["prs"]["102"]["baseRefName"], "a")
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_a_main_move_after_the_retarget_names_each_retargeted_member_and_how_to_restore_it(self):
        """The last read stays right before the merge call; a move it sees after the retarget (made on the first pr edit
        call) refuses naming #102, its old base and the command that restores it, and the state keeps the old base, so
        the next land retargets #102 again."""
        fx = self.fx
        self.ready()
        before = fx.bare_rev("main")
        self.move_main_on("pr edit")
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        moved = fx.bare_rev("main")
        self.assertIn("main moved on origin to %s after verify read %s; nothing merged, but land had already retargeted #102 "
                      "from a to main on GitHub: restore it with `gh pr edit 102 --base a`, or run land again, which retargets "
                      "it again" % (moved[:10], before[:10]), p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        self.assertEqual(fx.gh()["prs"]["102"]["baseRefName"], "main", "the retarget had happened on GitHub")
        self.assertEqual(fx.state("b1")["members"]["102"]["base_ref"], "a", "the state keeps the old base")

    def test_finish_reports_loudly_a_merge_whose_first_parent_is_not_the_main_verify_read(self):
        """Pre-round item 4: a batch merged by hand after main moved lands a tree no sweep or CI run tested. finish does its
        cleanup, then fails naming the merge commit, its first parent, the main verify read, and the remedy (a sweep at
        the merge commit)."""
        fx = self.fx
        self.ready()
        seen = fx.bare_rev("main")
        moved = fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0, "the button reads nothing")
        merge = fx.bare_rev("main")
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FIRST PARENT MISMATCH: batch PR #900's merge commit %s has first parent %s, not %s, the main verify read"
                      % (merge, moved, seen), p.stderr)
        self.assertIn("so the tree on main is not the batch head's tree, and no sweep or CI run tested it", p.stderr)
        self.assertIn("`git worktree add --detach ../romp-merge-b1 %s`, then `scripts/sweep.py run --tree ../romp-merge-b1 "
                      "--python <python>` (%s; it owes every leg there)" % (merge, batch.PYTHON_REMEDY), p.stderr)
        self.assertIn("batch #900 landed, ", p.stdout, "the cleanup ran first")
        self.assertEqual(fx.bare_rev("batch/b1"), "")
        self.assertEqual(fx.state("b1")["finished"]["report"]["first_parent"], {"merge": merge, "first_parent": moved, "verified_main": seen, "ok": False})
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, "a re-run reports it again")
        self.assertIn("FIRST PARENT MISMATCH", p.stderr)

    def test_land_reports_a_main_move_its_last_read_could_not_catch(self):
        """The Q1 residual as finish's loud report: main moves after land's last read, on the merge call itself, so the
        merge lands on the moved main. land merges (the merge pins the head, not the base), and its finish fails naming
        both shas."""
        fx = self.fx
        self.ready()
        seen = fx.bare_rev("main")
        self.move_main_on("pr merge")
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("merged batch PR #900", p.stdout)
        merge = fx.bare_rev("main")
        parents = fx._git("rev-list", "--parents", "-n1", merge, cwd=fx.bare).split()[1:]
        self.assertNotEqual(parents[0], seen, "the wrapper moved main before the merge")
        self.assertIn("FIRST PARENT MISMATCH: batch PR #900's merge commit %s has first parent %s, not %s" % (merge, parents[0], seen),
                      p.stderr)

    def test_finish_reports_loudly_a_merge_whose_second_parent_is_not_the_head_verify_read(self):
        """A commit pushed to the batch branch after verify, then the batch PR merged by the button (which pins no head):
        the head that landed is not the one the sweep read. finish does its cleanup, reads the CI run at the head that
        landed (the merge's second parent), then fails naming both shas and the sweep owed at the merge commit. The stage
        1 to 3 head exited 0 there and named the verified head's run as the one that tested the tree."""
        fx = self.fx
        self.ready()
        verified = fx.state("b1")["verified"]["head"]
        wt = fx.wt("b1")
        with open(os.path.join(wt, "late.txt"), "w") as f:
            f.write("pushed after verify\n")
        fx._git("add", "late.txt", cwd=wt)
        fx._git("commit", "-q", "-m", "batch: a late commit no sweep or verify read", cwd=wt)
        fx._git("push", "-q", "origin", "batch/b1", cwd=wt)
        late = fx._git("rev-parse", "HEAD", cwd=wt)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0, "the button reads nothing")
        merge = fx.bare_rev("main")
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("HEAD MISMATCH: batch PR #900's merge commit %s has second parent %s, not %s, the batch head verify read: "
                      "a commit reached batch/b1 after verify, so the tree on main is not the tree the sweep read" % (merge, late, verified),
                      p.stderr)
        self.assertIn("`git worktree add --detach ../romp-merge-b1 %s`, then `scripts/sweep.py run --tree ../romp-merge-b1 "
                      "--python <python>` (%s; it owes every leg there)" % (merge, batch.PYTHON_REMEDY), p.stderr)
        self.assertNotIn("FIRST PARENT", p.stderr, "main did not move")
        self.assertEqual(fx.calls("run", "list")[-1][fx.calls("run", "list")[-1].index("--commit") + 1], late,
                         "the CI run is read at the head that landed")
        self.assertIn("the batch head's CI run: missing: GitHub lists no run of ci.yml from a push to batch/b1 at %s" % late, p.stdout)
        self.assertEqual(fx.bare_rev("batch/b1"), "", "the cleanup ran first")
        self.assertEqual(fx.state("b1")["finished"]["report"]["landed_head"],
                         {"merge": merge, "second_parent": late, "verified_head": verified, "ok": False})

    def test_finish_with_no_merge_commit_reported_says_it_could_not_check(self):
        """Pre-round item 4's third branch: GitHub reports the batch PR MERGED with no merge commit, so finish cannot read
        either parent: it exits 1 saying the first parent was not checked (and adds no head line, which needs the same
        merge commit)."""
        fx = self.fx
        self.ready()
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        st = fx.gh()
        st["prs"]["900"]["mergeCommit"] = None
        fx.gh_state = st
        fx._save_gh()
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FIRST PARENT NOT CHECKED: GitHub reports no merge commit for batch PR #900, so finish cannot say that the "
                      "tree on main is the batch head's", p.stderr)
        self.assertNotIn("HEAD MISMATCH", p.stderr)
        self.assertEqual(fx.state("b1")["finished"]["report"]["first_parent"]["ok"], False)

    def test_finish_with_no_main_recorded_by_verify_says_it_could_not_check(self):
        fx = self.fx
        self.ready()
        path = os.path.join(fx.dev, ".git", "batch", "b1.json")
        with open(path) as f:
            st = json.load(f)
        st["verified"]["main"] = None
        with open(path, "w") as f:
            json.dump(st, f)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FIRST PARENT NOT CHECKED: batch PR #900's merge commit %s has first parent" % fx.bare_rev("main"), p.stderr)
        self.assertIn("verify recorded no main for batch b1", p.stderr)

    def test_land_auto_needs_the_setting_and_rules_on_main_and_says_which(self):
        """--auto is refused by name until the repository allows auto-merge AND something is required
        on main: a ruleset rule (read from the rules that apply to main, not the repository-wide
        list) or classic branch protection. The refusal and the go-ahead both say what was found."""
        fx = self.fx
        self.ready()
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1)
        self.assertIn('"Allow auto-merge" setting, which is off', p.stderr)
        self.assertIn("gh repo edit --enable-auto-merge", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        fx.set_repo(allowAutoMerge=True)
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1)
        self.assertIn("needs a ruleset or branch protection on main", p.stderr)
        self.assertIn("no rules apply to main, and it has no classic protection", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        # Classic protection alone satisfies it, and is named.
        fx.set_gh(protection={"required_status_checks": {"contexts": ["ci"]}})
        p = fx.ok("land", "b1", "--auto")
        self.assertIn("--auto", fx.calls("pr", "merge")[0])
        self.assertIn("merging with --auto: auto-merge is allowed and classic branch protection on main", p.stdout)

    def test_land_auto_names_a_ruleset_that_applies_to_main(self):
        fx = self.fx
        self.ready()
        fx.set_repo(allowAutoMerge=True)
        fx.set_gh(rulesets=[{"type": "non_fast_forward"}, {"type": "required_status_checks"}])
        p = fx.ok("land", "b1", "--auto")
        self.assertIn("--auto", fx.calls("pr", "merge")[0])
        self.assertIn("merging with --auto: auto-merge is allowed and rules on main gate a merge (required_status_checks)", p.stdout,
                      "the go-ahead names the gating rule, not a count of every rule")
        paths = [c[1] for c in fx.calls("api")]
        self.assertIn("repos/{owner}/{repo}/rules/branches/main", paths, "the rules that apply to main, not the repository-wide list")
        self.assertNotIn("repos/{owner}/{repo}/rulesets", paths)

    def test_land_auto_refuses_rules_that_gate_no_merge(self):
        """The rules endpoint lists every rule on main, the protective ones included. A ruleset that
        only blocks force pushes and deletion leaves --auto nothing to wait for, so it is refused
        naming what was found; a pull_request rule (required reviews) counts like required checks
        (scripts/land.sh runs this land, so the same gate)."""
        fx = self.fx
        self.ready()
        fx.set_repo(allowAutoMerge=True)
        fx.set_gh(rulesets=[{"type": "non_fast_forward"}, {"type": "deletion"}])
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("ruleset rules non_fast_forward, deletion, which protect the branch and gate no merge", p.stderr)
        self.assertIn("Merge without --auto", p.stderr)
        self.assertNotIn("no rules apply to main", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        self.assertNotIn(["pr", "edit", "102", "--base", "main"], fx.calls("pr", "edit"), "refused before any member was retargeted")
        fx.set_gh(rulesets=[{"type": "non_fast_forward"}, {"type": "pull_request"}])
        p = fx.ok("land", "b1", "--auto")
        self.assertIn("--auto", fx.calls("pr", "merge")[0])
        self.assertIn("rules on main gate a merge (pull_request)", p.stdout)

    def test_land_auto_classic_protection_must_require_checks_or_reviews(self):
        fx = self.fx
        self.ready()
        fx.set_repo(allowAutoMerge=True)
        fx.set_gh(protection={"url": "https://api.example.invalid/protection", "enforce_admins": {"enabled": True},
                              "required_status_checks": None, "restrictions": None})
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("branch protection on main requires no checks and no reviews (set: enforce_admins, url)", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        fx.set_gh(protection={"required_pull_request_reviews": {"required_approving_review_count": 1}})
        p = fx.ok("land", "b1", "--auto")
        self.assertIn("--auto", fx.calls("pr", "merge")[0])
        self.assertIn("merging with --auto: auto-merge is allowed and classic branch protection on main requires reviews", p.stdout)

    def test_land_auto_refuses_when_the_rules_or_protection_cannot_be_read(self):
        """A failed read is not "none": with the rules unreadable --auto is refused with gh's error
        even though a gating rule is set, and so is a protection read that fails with anything but
        the 404 GitHub gives an unprotected branch."""
        fx = self.fx
        self.ready()
        fx.set_repo(allowAutoMerge=True)
        fx.set_gh(rulesets=[{"type": "required_status_checks"}])
        p = fx.run("land", "b1", "--auto", gh_fail="api repos/{owner}/{repo}/rules/branches/main")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("could not read the rules on main", p.stderr)
        self.assertIn("HTTP 502", p.stderr, "gh's error is printed")
        self.assertNotIn("no rules apply", p.stderr)
        self.assertNotIn("merging with --auto", p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [])
        fx.set_gh(rulesets=[], fail={"protection": "Must have admin rights to Repository. (HTTP 403)"})
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("could not read main's branch protection", p.stderr)
        self.assertIn("HTTP 403", p.stderr)
        self.assertNotIn("no classic protection", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        fx.set_gh(fail={})
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("no rules apply to main, and it has no classic protection", p.stderr, "the 404 alone reads as none")
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_land_stops_when_verify_fails(self):
        fx = self.fx
        self.ready()
        fx.commit("a", {"kernel/kernel.py": "VERSION = 3\n"})
        p = fx.run("land", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("head moved: #101", p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [])
        self.assertEqual(fx.gh()["prs"]["900"]["state"], "OPEN")

    def test_finish_reports_a_member_whose_head_moved_after_the_cut(self):
        fx = self.fx
        self.ready()
        pinned = fx.state("b1")["members"]["102"]["head"]
        fx.commit("b", {"postal/postal_service.py": "def send():\n    return 3\n"}, "after the cut")
        # The maintainer clicks "Create a merge commit" himself; the batcher runs finish alone.
        p = fx.fake_gh("pr", "merge", "900", "--merge")
        self.assertEqual(p.returncode, 0, p.stderr)
        p = fx.ok("finish", "b1")
        gh = fx.gh()
        self.assertEqual(gh["prs"]["101"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["102"]["state"], "OPEN")
        self.assertIn("STILL OPEN (told on the PR): #102", p.stdout)
        self.assertIn("batch #900 landed, 1 member(s) marked merged", p.stdout)
        told = gh["prs"]["102"]["comments"][-1]
        self.assertIn("not marked merged", told)
        self.assertIn("head moved", told)
        self.assertIn(pinned[:10], told)
        self.assertEqual(gh["prs"]["102"]["baseRefName"], "main", "finish retargets a stacked member the hand merge left behind")
        self.assertTrue(any("#102 was still based on a member branch" in o for o in fx.state("b1")["finished"]["report"]["observations"]))
        self.assertEqual(fx.bare_rev("a"), "", "the merged member's branch is deleted")
        self.assertNotEqual(fx.bare_rev("b"), "", "the open member's branch is kept")

    def test_finish_refuses_before_the_batch_pr_is_merged(self):
        fx = self.fx
        self.ready()
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("not MERGED", p.stderr)

    def test_finish_refuses_a_state_whose_last_assembly_did_not_finish_and_names_the_pending_members(self):
        """A rebuild that died part-way after a complete assembly was pushed and summarized leaves
        `pending` non-empty; the branch on origin still holds the earlier head, and a maintainer can
        merge it by hand. finish must not act on the partial member list as if it were the batch."""
        fx = self.fx
        self.ready()
        path = os.path.join(fx.dev, ".git", "batch", "b1.json")
        with open(path) as f:
            st = json.load(f)
        st["assembly"]["merged"] = st["assembly"]["merged"][:1]
        st["assembly"]["pending"] = [102]
        st["assembly"]["head"] = None
        with open(path, "w") as f:
            json.dump(st, f)
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        comments_before = fx.gh()["prs"]["102"]["comments"]
        p = fx.run("finish", "b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("assembly incomplete: #102 never merged", p.stderr)
        self.assertIn("#900", p.stderr)
        self.assertIn("`gh pr view 102`", p.stderr)
        self.assertNotEqual(fx.bare_rev("a"), "", "no branch was deleted")
        self.assertNotIn("finished", fx.state("b1"))
        self.assertEqual(fx.gh()["prs"]["102"]["comments"], comments_before, "no member was told anything")
        self.assertEqual(fx.calls("pr", "edit"), [], "nothing was retargeted")

    def test_bisect_names_the_member(self):
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        p = fx.ok("bisect", "b1", "--", "sh", "-c", "grep -q 'return 1' postal/postal_service.py")
        self.assertIn("first bad: #102 postal: send two", p.stdout)
        wt = fx.wt("b1")
        self.assertFalse(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "BISECT_START")), "bisect is reset")
        self.assertEqual(fx._git("rev-parse", "HEAD", cwd=wt), fx.dev_git("rev-parse", "batch/b1"))

    def test_bisect_says_so_when_the_command_never_fails_or_fails_at_the_base(self):
        fx = self.fx
        self.two_members()
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        wt = fx.wt("b1")
        p = fx.run("bisect", "b1", "--", "sh", "-c", "true")
        self.assertEqual(p.returncode, 1)
        self.assertIn("passes at the batch tip", p.stderr)
        self.assertNotIn("first bad", p.stdout)
        p = fx.run("bisect", "b1", "--", "sh", "-c", "false")
        self.assertEqual(p.returncode, 1)
        self.assertIn("fails at the base", p.stderr)
        self.assertNotIn("first bad", p.stdout)
        self.assertEqual(fx._git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt), "batch/b1", "the worktree is back on the branch")
        self.assertFalse(os.path.exists(os.path.join(fx.dev, ".git", "worktrees", "romp-batch-b1", "BISECT_START")))

    def test_finish_keeps_its_first_observations_across_a_re_run(self):
        """A finish that dies after deleting branches and is run again must not attribute its own
        deletions to GitHub, forget that #102 was stacked, or comment on #102 twice."""
        fx = self.fx
        self.ready()
        self.assertEqual(fx.fake_gh("pr", "merge", "900", "--merge").returncode, 0)
        # The post-deletion recheck of the retargeted #112 fails on the first run.
        p = fx.run("finish", "b1", gh_fail="pr view 112 --json baseRefName,state")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertEqual(fx.bare_rev("a"), "", "finish had deleted `a` before it died")
        self.assertNotIn("finished", fx.state("b1"))
        prog = fx.state("b1")["finish_progress"]
        self.assertEqual(prog["branches"]["a"], "deleted by finish")
        self.assertEqual(prog["members"]["102"]["base"], "a", "recorded before the retarget")
        p = fx.ok("finish", "b1")
        rep = fx.state("b1")["finished"]["report"]
        self.assertEqual(rep["deleted"], ["a"])
        self.assertEqual(rep["already_gone"], [])
        self.assertTrue(any("finish deleted head branches GitHub left: a" in o for o in rep["observations"]), rep["observations"])
        self.assertFalse(any("GitHub deleted the head branch" in o for o in rep["observations"]), rep["observations"])
        self.assertTrue(any("#102 was still based on a member branch; retargeted to main" in o for o in rep["observations"]), rep["observations"])
        comments = [c for c in fx.gh()["prs"]["102"]["comments"] if "not marked merged" in c]
        self.assertEqual(len(comments), 1, "told once across both runs")
        self.assertIn("it was based on another PR's branch", comments[0])
        self.assertEqual(rep["retargeted"], [112])
        self.assertIn("retargeted to main: #112", p.stdout)


class Body(unittest.TestCase):
    """The generated body, as a pure function of the state: the cap and the "Read these first" rule."""

    @staticmethod
    def member(n, title="t", tier="fix", touches=("docs/x.md",), trailer="yes", head_ref=None):
        t = {"tier": tier, "rounds": 2, "sweep": {"pytest": "1 passed", "bats": 1, "npm": 1, "typecheck": "clean"},
             "sweep_head": "abcdef0123456789"} if trailer == "yes" else None
        return {"n": n, "title": title, "url": "", "head": "%040x" % n, "head_ref": head_ref or "br%d" % n, "base_ref": "main",
                "labels": [tier] if tier else [], "tier": tier, "depends_on": [], "trailer": t, "trailer_error": None,
                "mergeable": "MERGEABLE", "touches": list(touches), "predicted_conflict": None}

    @classmethod
    def state(cls, members, log_lines=0, resolved=(), held=(), pulled=()):
        merged = [{"n": m["n"], "merge": "%040x" % (m["n"] + 5000),
                   "resolved": ({"files": ["f.txt"], "how": "resolved by the batcher, per hunk", "hunks": 2, "review": "ok"}
                                if m["n"] in resolved else None)} for m in members]
        return {"name": "2026-01-01a", "base": "0" * 40, "order": [m["n"] for m in members],
                "members": {str(m["n"]): m for m in members}, "pulled": list(pulled),
                "assembly": {"merged": merged, "held": list(held), "head": "f" * 40,
                             "log": ["2026-01-01T00:00:00Z line %d" % i for i in range(log_lines)]},
                "sweep": {"head": "f" * 40, "verdict": "pass", "finished": "2026-01-01T00:00:00Z",
                          "legs": [[n, "not owed" if n in sweep.EXTENSION_LEGS else 0] for n in sweep.LEGS],
                          "summary": {"pytest": "1 passed in 0.1s", "bats": "1 ok, 0 not ok"}}, "ledger": "clean",
                "verified": {"ok": True, "head": "f" * 40, "lines": [], "main": "e" * 40}, "pr": None, "commented": {}}

    def test_stays_under_the_cap_with_details_truncated_first(self):
        members = [self.member(n, title="member %d" % n) for n in range(1, 26)]
        st = self.state(members, log_lines=2000, resolved={1, 2, 3})
        big = "\n".join("++ line %d of a resolution diff that goes on" % i for i in range(5000))
        inputs = {"resolutions": [{"n": n, "diff": big} for n in (1, 2, 3)],
                  "entries": [{"path": "upstream/2026-01-01-e%d.md" % n, "title": "e%d" % n, "status": "candidate", "change": "added", "members": [n]} for n in range(1, 26)]}
        body = batch.render_body(st, inputs)
        self.assertLessEqual(len(body), batch.BODY_CAP)
        for n in range(1, 26):
            self.assertIn("| #%d | member %d |" % (n, n), body, "the members table is never cut")
        self.assertIn("## Upstream entries this batch adds or changes (25)", body)
        self.assertIn("| `upstream/2026-01-01-e25.md` |", body, "the ledger table survives when the details give enough")
        self.assertLess(body.count("line 4999 of a resolution"), 1, "the resolution diffs are cut")
        self.assertIn("more lines)", body)
        m = re.search(r"<!-- romp-batch: (\{.*\}) -->", body)
        self.assertIsNotNone(m, "the machine-readable trailer survives")
        trailer = json.loads(m.group(1))
        self.assertEqual(sorted(trailer), ["base", "members", "name"], "exactly the template's keys")
        self.assertEqual(len(trailer["members"]), 25)
        self.assertEqual(trailer["members"][0], {"n": 1, "head": "%040x" % 1})
        self.assertTrue(body.endswith("-->\n"))

    def test_a_body_too_big_even_without_details_is_refused_not_cut(self):
        members = [self.member(n, title="a long title " * 30) for n in range(1, 400)]
        st = self.state(members)
        with self.assertRaises(batch.Fail) as cm:
            batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("Split the batch", str(cm.exception))

    def test_a_small_body_keeps_every_detail(self):
        st = self.state([self.member(1)], log_lines=5)
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("line 4", body)
        self.assertIn("(none)", body)
        self.assertIn("## To pull a member\nComment `pull #N`.", body)
        self.assertIn("Land with `scripts/batch.py land %s`: it reads main again right before the merge and refuses if the "
                      "batch head no longer contains it. "
                      "Verified at ffffffffff: sweep pass: pytest rc 0 (1 passed in 0.1s), "
                      "bats rc 0 (1 ok, 0 not ok), manager rc 0, tools rc 0, ledger rc 0; not owed: deps, typecheck, npm-test, "
                      "pdf-smoke, build, served; "
                      "provenance clean; main at %s contained at verify time; ledger check clean. " % (st["name"], "e" * 10), body)
        self.assertIn("No ci.yml run follows the merge to main, so if main has moved past %s, do not merge with the button or "
                      "`gh pr merge`: the batch needs main merged in, a new sweep and verify first." % ("e" * 10), body)
        # round 1, extra7-5: the push run's checks on the PR's head are an expectation the first batch confirms
        self.assertIn("CI on this PR: the run of the push to batch/%s, expected among the checks on its head (the first batch "
                      "confirms that)." % st["name"], body)
        self.assertNotIn('Merge with "Create a merge commit"', body, "the body does not send the reader to the button")
        self.assertNotIn("sweep not recorded", body)
        self.assertIn("- none: every member is labeled, carries a trailer, touches no sensitive path and merged clean; "
                      "the batch adds no commit of its own.", body)
        self.assertNotIn("own CI", body, "a member runs no ci.yml of its own, so the none line claims none")

    def test_a_record_from_before_the_result_file_shows_its_text(self):
        # a batch verified by an older batch.py recorded the batcher's free text; the body shows it as written
        st = self.state([self.member(1)])
        st["sweep"] = {"text": "pytest 1 passed", "head": "f" * 40, "at": "2026-01-01T00:00:00Z"}
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("Verified at ffffffffff: pytest 1 passed; provenance clean;", body)

    def test_an_unverified_batch_says_so_in_the_first_block(self):
        st = self.state([self.member(1)])
        st["verified"] = None
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("NOT VERIFIED", body)
        st["verified"] = {"ok": True, "head": "e" * 40, "lines": []}
        self.assertIn("verification is stale", batch.render_body(st, {"resolutions": [], "entries": []}))

    def test_read_these_first_is_computed_not_chosen(self):
        r = batch.read_first_reasons
        self.assertEqual(r(self.member(1), None), [], "labeled fix, trailer, safe paths, CI ran: not listed")
        self.assertEqual(r(self.member(2, touches=("kernel/kernel.py",)), None), ["touches kernel/"])
        self.assertEqual(r(self.member(3, touches=(".github/workflows/ci.yml", ".githooks/pre-push", "install.sh")), None),
                         ["touches .github/, .githooks/, install.sh"])
        self.assertEqual(r(self.member(4, tier=None), None), ["unlabeled"])
        self.assertEqual(r(self.member(5, tier="feature"), None), ["feature"])
        self.assertEqual(r(self.member(11, tier="docs"), None), [], "docs is tier 0, like tests-only: not listed")
        self.assertEqual(r(self.member(12, tier="tests-only"), None), [])
        self.assertEqual(r(self.member(6, trailer=None), None), ["trailer not stated"])
        self.assertEqual(r(dict(self.member(7), ci="none (was conflicting)", mergeable="CONFLICTING"), None), [],
                         "a member runs no ci.yml of its own: an older plan's CI word gives no reason")
        self.assertEqual(r(self.member(8), {"files": ["a.py", "b.py"], "how": "x", "hunks": 3, "review": "one round by a subagent: ok"}),
                         ["conflict resolved in a.py, b.py (3 hunks); one review round: one round by a subagent: ok. [diff from the clean merge below]"])
        self.assertEqual(r(self.member(9), {"files": ["a.py"], "how": "x", "hunks": 1, "review": None}),
                         ["conflict resolved in a.py (1 hunk); review round NOT recorded. [diff from the clean merge below]"])
        st = self.state([self.member(10, tier=None, trailer=None, touches=("kernel/k.py",))])
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("- #10 br10: unlabeled; touches kernel/; trailer not stated.", body)
        self.assertIn("| #10 | t | unlabeled | not stated | not recorded | unlabeled, kernel/, no trailer | - |", body)
        self.assertIn("| # | Title | Tier | Rounds | Sweep at own head | Flags | Ledger |", body)
        self.assertNotIn("Own CI", body)
        self.assertNotIn("own CI", body)

    def test_the_sweep_column_is_the_pass_recorded_at_the_members_head_never_the_trailer(self):
        """Round 1, fresh-3: the column rendered the author's trailer (self-reported, and its sweep_head may be another
        sha) while plan had read the result at the member's pinned head. It renders the record plan or --repin wrote on
        the member; a member with no record (a plan from before it) or a record for another head reads "not recorded",
        never the trailer."""
        recorded = self.member(1)
        recorded["sweep"] = {"head": recorded["head"], "verdict": "pass", "legs": [[n, "not owed" if n == "deps" else 0] for n in sweep.LEGS],
                             "summary": {"bats": "4 ok, 0 not ok"}, "reruns": [], "invalid_runs": []}
        older = self.member(2)                                   # a trailer, and no record: an older plan
        other = self.member(3)
        other["sweep"] = dict(recorded["sweep"], head="ab" * 20)
        body = batch.render_body(self.state([recorded, older, other]), {"resolutions": [], "entries": []})
        self.assertIn("| #1 | t | fix | 2 | pass @%s: pytest rc 0, bats rc 0 (4 ok, 0 not ok), manager rc 0, tools rc 0, ledger rc 0, "
                      "typecheck rc 0, npm-test rc 0, pdf-smoke rc 0, build rc 0, served rc 0; not owed: deps |" % recorded["head"][:10],
                      body)
        self.assertIn("| #2 | t | fix | 2 | not recorded |", body)
        self.assertIn("| #3 | t | fix | 2 | not recorded (the pass read was at %s, the pinned head is %s) |"
                      % ("ab" * 5, other["head"][:10]), body)
        self.assertNotIn("abcdef0123", body, "the trailer's sweep_head is never shown")
        self.assertNotIn("1 passed, bats 1", body, "nor its sweep counts")

    def test_held_back_lines_follow_the_template(self):
        """Whether the owner was told is what hold_back RECORDED, never assumed."""
        st = self.state([self.member(1)], held=[{"n": 7, "reason": "conflicts with #1 in x.py", "files": ["x.py"], "with": [1], "told": True},
                                                {"n": 8, "reason": "depends on #7 (not in this batch)", "files": [], "with": []},
                                                {"n": 11, "reason": "conflicts with origin/main in y.py", "files": ["y.py"], "with": [],
                                                 "told": False, "told_why": "comment failed: HTTP 502"},
                                                {"n": 12, "reason": "conflicts with the batch in z.py", "files": ["z.py"], "with": []}],
                        pulled=[9])
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("# Batch 2026-01-01a: 1 PR (4 held back, 1 pulled)", body)
        self.assertIn("- #7: conflicts with #1 in x.py; owner told.", body)
        self.assertIn("- #8: depends on #7 (not in this batch).", body)
        self.assertIn("- #11: conflicts with origin/main in y.py; owner NOT told (comment failed: HTTP 502).", body)
        self.assertIn("- #12: conflicts with the batch in z.py; owner not told.", body)
        self.assertIn("- #9: pulled; the PR stays open against main.", body)

    def test_the_cap_keeps_the_resolution_and_cuts_the_log_that_overflows(self):
        """A 3000-line assembly log is what pushes this body over the cap; the one resolution (the
        code nobody else reviewed) keeps all its lines and the log gives up only what does not fit."""
        members = [self.member(n, title="member %d" % n) for n in range(1, 8)]
        st = self.state(members, log_lines=3000, resolved={3})
        res = "\n".join("++ line %d of the resolution diff, kept whole" % i for i in range(300))
        body = batch.render_body(st, {"resolutions": [{"n": 3, "diff": res}], "entries": []})
        self.assertLessEqual(len(body), batch.BODY_CAP)
        self.assertGreater(len(body), batch.BODY_CAP - 200, "the budget is filled, not left unused")
        self.assertIn("++ line 299 of the resolution diff", body)
        self.assertNotIn("more lines)", body, "no resolution line was cut")
        m = re.search(r"\((\d+) earlier lines omitted\)", body)
        self.assertIsNotNone(m)
        self.assertLess(int(m.group(1)), 3000 - 100, "far more than the old fixed 40 log lines survive")
        # A log alone that overflows is cut only as far as needed.
        body = batch.render_body(self.state([self.member(1)], log_lines=3000), {"resolutions": [], "entries": []})
        self.assertLessEqual(len(body), batch.BODY_CAP)
        self.assertGreater(len(body), batch.BODY_CAP - 200)
        # A resolution is still capped at RESOLUTION_LINES per merge even with room to spare.
        big = "\n".join("++ line %d" % i for i in range(1000))
        body = batch.render_body(self.state([self.member(1)], resolved={1}), {"resolutions": [{"n": 1, "diff": big}], "entries": []})
        self.assertIn("(700 more lines)", body)

    def test_read_these_first_lists_batch_commits_contained_members_and_main_merge_resolutions(self):
        st = self.state([self.member(1), self.member(2)])
        st["assembly"]["contained"] = [{"n": 2, "contained_by": "#1"}]
        st["assembly"]["merged"] = st["assembly"]["merged"][:1]
        st["assembly"]["declared"] = [{"sha": "a" * 40, "subject": "batch: hotfix for the integrated tree",
                                       "files": ["hotfix.py"], "stat": "1 file changed, 1 insertion(+)"}]
        st["assembly"]["main_merges"] = [{"merge": "b" * 40, "main": "c" * 40,
                                          "resolved": {"files": ["notes.txt"], "how": "resolved by the batcher, per hunk", "hunks": 1, "review": "subagent: ok"}}]
        body = batch.render_body(st, {"resolutions": [{"n": None, "merge": "b" * 40, "diff": "++ main merge diff"}], "entries": []})
        self.assertIn("# Batch 2026-01-01a: 2 PRs", body, "a contained member lands too")
        self.assertIn("- #2 br2: already contained by #1: no merge commit of its own (add `Depends-on` or reorder next time).", body)
        self.assertIn("| #2 | t | fix | 2 |", body)
        self.assertIn("| contained by #1 |", body)
        self.assertIn("- `batch:` commit aaaaaaaaaa by the batcher: batch: hotfix for the integrated tree; 1 file changed, 1 insertion(+); touches hotfix.py.", body)
        self.assertIn("- merge of origin/main (bbbbbbbbbb): conflict resolved in notes.txt (1 hunk); one review round: subagent: ok. [diff from the clean merge below].", body)
        self.assertIn("### merge of origin/main (bbbbbbbbbb)", body)
        self.assertIn("++ main merge diff", body)
        replayed = {"files": ["a.py"], "how": "rerere replayed the resolution recorded in the earlier assembly", "hunks": 1,
                    "review": "subagent: fine", "replayed": True}
        self.assertEqual(batch.read_first_reasons(self.member(9), replayed),
                         ["conflict resolved in a.py (1 hunk); one review round in the earlier assembly, replayed by rerere: subagent: fine. [diff from the clean merge below]"])


class Helpers(unittest.TestCase):
    def test_trailer_parsing(self):
        t, err = batch.parse_trailer("body\n" + TRAILER)
        self.assertEqual(t["rounds"], 3)
        self.assertIsNone(err)
        self.assertEqual(batch.parse_trailer("no trailer"), (None, None))
        t, err = batch.parse_trailer("<!-- romp-pr: {not json} -->")
        self.assertIsNone(t)
        self.assertIn("not JSON", err)

    def test_docs_define_the_trailers_rounds_once_beside_the_trailer(self):
        """docs/batching.md says once, right after the trailer's example, what `rounds` counts: the review rounds whose
        reviewer has reported, not the round a push answers. Nothing defined it before a fork PR's review found its
        trailer's count unreadable by rule (fork PR #780, round 6, rules-1)."""
        doc = (ROOT / "docs" / "batching.md").read_text(encoding="utf-8")
        flat = " ".join(doc.split())
        sentence = ("`rounds` counts the review rounds whose reviewer has reported, so a push that answers round 5's "
                    "findings still says 5, and the count moves to 6 when round 6's report comes in.")
        example = '"rounds":8,"flakes":[]} -->`.'
        self.assertIn(example + " " + sentence, flat, "the definition follows the trailer's example")
        self.assertEqual(flat.count("`rounds` counts"), 1, "and is written once")
        self.assertIn('"rounds":', flat[:flat.index(sentence)], "the example it follows carries the key")

    def test_every_comment_batch_py_cites_by_a_name_is_one_of_its_names(self):
        """A cross-reference in scripts/batch.py's comments and docstrings of the form "<NAME>'s comment" or "<NAME>'
        comment" (the word comment after the possessive, with only spaces, line breaks and comment marks between them)
        names a function, class or assignment at the module's top level, so a reader can find the comment it means;
        the names read are those with an underscore, as batch.py's own are. Red at the build of round 3 of PR 959,
        where run_git's docstring cited MERGE_SETTINGS' comment, a name batch.py does not have; the comment it meant
        is MERGE_STRATEGY's (the verify pass at that build, its v-3)."""
        src = (SCRIPTS / "batch.py").read_text(encoding="utf-8")
        top = set()
        for node in ast.parse(src).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                top.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    top.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        cited = [m.group(1) for m in re.finditer(r"\b([A-Za-z0-9]*_[A-Za-z0-9_]*)(?:'s|')(?:\s|#)+comment\b", src)]
        self.assertIn("GIT_SETTINGS", cited, "premise: the census reads the citations batch.py has")
        self.assertIn("MERGE_STRATEGY", cited, "premise: the census reads the citations batch.py has")
        self.assertEqual(sorted({name for name in cited if name not in top}), [],
                         "a comment cited by a name batch.py does not define at its top level")

    def test_ordering_is_dependencies_first_then_by_number(self):
        cands = {5: {"depends_on": [9]}, 9: {"depends_on": []}, 7: {"depends_on": []}, 8: {"depends_on": [5]}}
        self.assertEqual(batch.order_members(cands), ([7, 9, 5, 8], []))
        cyclic = {1: {"depends_on": [2]}, 2: {"depends_on": [1]}, 3: {"depends_on": [1]}, 4: {"depends_on": [4]}, 6: {"depends_on": []}}
        self.assertEqual(batch.order_members(cyclic), ([6], [1, 2, 3, 4]), "the cycles' members and their dependents are left out, not ordered")
        self.assertEqual([n for n in (1, 2, 3, 4) if batch.reaches(cyclic, n, n)], [1, 2, 4], "#3 only depends on the cycle")

    def test_depends_on_parsing(self):
        d = batch.parse_depends_on
        self.assertEqual(d("Depends-on: #101\n\nmore"), [101])
        self.assertEqual(d("Summary.\nDepends-on: #101, #102\nDepends-on: #7"), [7, 101, 102], "a comma list and one per line")
        self.assertEqual(d("Depends-on: 5, 7"), [5, 7], "a bare number list")
        self.assertEqual(d("Depends-on: #101 (merged 2026-09-06)"), [101], "only # tokens when any are present")
        self.assertEqual(d("intro\n```\nDepends-on: #5\n```\nDepends-on: #6\n~~~\nDepends-on: #8\n~~~\n"), [6], "fenced blocks are skipped")
        late = "\n".join(["line %d" % i for i in range(batch.DEPENDS_ON_LINES)] + ["Depends-on: #9"])
        self.assertEqual(d(late), [], "only the body's first lines are read")
        self.assertEqual(d(None), [])

    def test_stray_resolution_paths(self):
        s = batch.stray_resolution_paths
        self.assertEqual(s(["notes.txt"], ["notes.txt"]), [])
        self.assertEqual(s(["notes.txt"], ["kernel/kernel.py", "notes.txt"]), ["kernel/kernel.py"])
        self.assertEqual(s(["UPSTREAM.md"], ["UPSTREAM.md", "upstream/2026-01-01-x.md"]), [], "a row conversion writes entries")
        self.assertEqual(s(["notes.txt"], ["upstream/2026-01-01-x.md"]), ["upstream/2026-01-01-x.md"], "but only when UPSTREAM.md conflicted")

    def test_help_names_every_argument_and_describes_every_subcommand(self):
        """docs/batching.md promises `--help` on each subcommand: every positional and flag carries
        help text, every subcommand a description, and the top level the subcommand table."""
        bare = re.compile(r"^  (-{1,2}[\w-]+(?: [\w|<>-]+)?|[a-z]+)\s*$")
        run = lambda *a: subprocess.run([sys.executable, str(SCRIPTS / "batch.py"), *a], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        top = run("--help")
        self.assertEqual(top.returncode, 0, top.stderr)
        self.assertIn("in the order a batch goes through them", top.stdout)
        expect = {"plan": "Nothing is merged", "assemble": "the branch is the mutex", "verify": "The gate `land` re-runs",
                  "summarize": "Render the body", "pull": "regenerate the body", "land": "Never squash or rebase",
                  "finish": "Safe to re-run", "bisect": "never fails, or fails everywhere"}
        for sub, phrase in expect.items():
            p = run(sub, "--help")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(phrase, " ".join(p.stdout.split()), "%s --help has its description" % sub)
            for line in p.stdout.splitlines():
                self.assertIsNone(bare.match(line), "%s --help: %r has no help text" % (sub, line.strip()))
        p = run("pull", "--help")
        self.assertIn("the member PR's number", p.stdout)
        self.assertIn("--reason TEXT", p.stdout)
        # round 2, extra9-7: finish's help names both parent checks, in the contracts' words, and the cases it cannot tell
        p = " ".join(run("finish", "--help").stdout.split())
        self.assertIn("checks that the merge commit's first parent is the main verify read, and its second parent the batch "
                      "head verify read (a commit pushed after verify and merged by the button)", p)
        self.assertIn("It exits 1 too when it cannot tell: no merge commit reported, or no main or head recorded by verify", p)


if __name__ == "__main__":
    unittest.main()


class BisectMessageForms(unittest.TestCase):
    """`git bisect run` names the first bad commit with two spellings across git versions: 2.43 prints
    "is the first bad commit", newer releases quote the term ("is the first 'bad' commit"). CI's git
    used the quoted form and bisect reported "did not name a first bad commit" on a run that had."""

    def test_both_spellings_of_the_first_bad_line_parse(self):
        sha = "b7f4db786e3a83216254c8e9118fc50ca671f8be"
        for line in ("%s is the first bad commit" % sha, "%s is the first 'bad' commit" % sha):
            with self.subTest(line=line):
                m = batch._FIRST_BAD.search("running 'sh' '-c' 'true'\n%s\ncommit %s\n" % (line, sha))
                self.assertIsNotNone(m, line)
                self.assertEqual(m.group(1), sha)

    def test_a_line_that_names_no_commit_does_not_parse(self):
        self.assertIsNone(batch._FIRST_BAD.search("bisect found first 'bad' commit\nbisect run success\n"))



class PrTierWorkflow(unittest.TestCase):
    """The fork's copy of .github/workflows/pr-tier.yml, upstream's check that every PR carries exactly
    one tier label, also counts `batch` and `docs` (2026-09-07 sync). A batch PR carries `batch` and no
    tier, so upstream's list would hold every batch PR red; `docs` is upstream's name for tier 0 (renamed
    from tests-only on 2026-09-08, the old spelling still accepted). The workflow's jq filter is run here
    as the workflow runs it, so the labels it counts and the labels batch.py knows stay in step."""

    WORKFLOW = ROOT / ".github" / "workflows" / "pr-tier.yml"

    @classmethod
    def setUpClass(cls):
        assert shutil.which("jq"), "jq is needed: the workflow runs its filter through jq"
        text = cls.WORKFLOW.read_text(encoding="utf-8")
        m = re.search(r"count=\$\(jq '([^']*)' <<<\"\$LABELS\"\)", text)
        assert m, "the workflow's `count=$(jq '...' <<<\"$LABELS\")` line is what this test reads"
        cls.filter = m.group(1)

    def count(self, labels):
        p = subprocess.run(["jq", self.filter], input=json.dumps(list(labels)), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return int(p.stdout.strip())

    def test_every_tier_batch_py_knows_and_the_batch_label_count_as_the_one_label(self):
        self.assertIn("docs", batch.TIERS)
        for label in (*batch.TIERS, batch.LABEL_BATCH):
            self.assertEqual(self.count([label]), 1, label)

    def test_no_tier_two_tiers_and_a_label_that_is_not_a_tier_are_not_one(self):
        self.assertEqual(self.count([]), 0)
        self.assertEqual(self.count([batch.LABEL_HOLD]), 0)
        self.assertEqual(self.count([batch.LABEL_LAND]), 0)
        self.assertEqual(self.count(["fix", "tests-only"]), 2)
        self.assertEqual(self.count([batch.LABEL_BATCH, "fix"]), 2, "a batch PR carries no tier of its own")

    def test_the_divergence_is_named_where_the_next_sync_will_read_it(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Fork divergence", text)
        self.assertIn("scripts/batch.py", text)

    def test_the_tier_policy_job_is_gated_to_the_upstream_repository_and_the_header_says_so(self):
        """The fork's copy of .github/workflows/tier-policy.yml, upstream's second check, carries a
        job-level `if:` that runs the Tier policy job only on the upstream repository: on the fork the
        job evaluates nothing and posts no Tier policy verdict, so a batch PR with no tier label is not
        marked failing. The guard is the fork's one functional change to upstream's file (the header
        paragraph explaining it is the other addition), and this pin exists so a future fold that takes
        upstream's workflow whole fails here instead of silently dropping it. The pattern tolerates
        GitHub's `${{ }}` wrapper, either quote style and extra spaces; the four-space indent keeps the
        guard job-level."""
        text = (ROOT / ".github" / "workflows" / "tier-policy.yml").read_text(encoding="utf-8")
        self.assertIn("\njobs:", text, "the jobs block is what this test slices")
        head, jobs = text.split("\njobs:", 1)
        self.assertRegex(
            jobs, r"\n    if:\s*(\$\{\{\s*)?github\.repository\s*==\s*['\"]romp-on/romp['\"]",
            "the job-level `if:` guard is the fork's divergence from upstream's workflow; a fold that takes "
            "upstream's file whole must put it back")
        self.assertIn("Fork divergence", head)
        self.assertIn("scripts/batch.py", head)
