#!/usr/bin/env python3
"""The batch tooling (scripts/batch.py, scripts/land.sh) against a fixture repository.

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
  - the body stays under 65,536 characters with details truncated first;
  - land.sh refuses --squash and a base belonging to a merged PR.
Plus the conflict paths (hold back and tell the owner once; --resolve/--continue records the
resolution; a straggler UPSTREAM.md row is converted inside the merge), land and finish end to end,
and the computed "Read these first" rule.

Synthetic data only: a demo `notes-api` with invented PR numbers, branch names and titles.
"""
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

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FAKE_GH = ROOT / "tests" / "fixtures" / "fake_gh.py"

TRAILER = ('<!-- romp-pr: {"tier":"fix","rounds":3,"sweep":{"pytest":"12 passed","bats":4,"npm":2,'
           '"typecheck":"clean"},"sweep_head":"0123456789abcdef","flakes":[]} -->')

SEED = {
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


def _load_batch_module():
    spec = importlib.util.spec_from_file_location("batch_tool", SCRIPTS / "batch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


batch = _load_batch_module()


class Fixture:
    """A bare origin, an author clone, the tool's clone, and the fake gh, all under one temp dir."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="batchtool-")
        self.bare = os.path.join(self.tmp, "origin.git")
        self.author = os.path.join(self.tmp, "author")
        self.dev = os.path.join(self.tmp, "dev")
        self.bin = os.path.join(self.tmp, "bin")
        self.state_file = os.path.join(self.tmp, "gh-state.json")
        self.log_file = os.path.join(self.tmp, "gh.log")
        os.makedirs(self.bin)
        shutil.copy(FAKE_GH, os.path.join(self.bin, "gh"))
        os.chmod(os.path.join(self.bin, "gh"), 0o755)
        self.env = dict(os.environ,
                        PATH=self.bin + os.pathsep + os.environ.get("PATH", ""),
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                        GIT_AUTHOR_NAME="romp tests", GIT_AUTHOR_EMAIL="tests@example.invalid",
                        GIT_COMMITTER_NAME="romp tests", GIT_COMMITTER_EMAIL="tests@example.invalid",
                        FAKE_GH_STATE=self.state_file, FAKE_GH_LOG=self.log_file, ROMP_BATCH_POLL="0")
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
        for s in ("batch.py", "land.sh", "pr-orphans.sh"):
            shutil.copy(SCRIPTS / s, os.path.join(self.dev, "scripts", s))
        self.gh_state = {"bare": self.bare, "next_number": 900, "prs": {}, "rulesets": [],
                         "repo": {"mergeCommitAllowed": True, "squashMergeAllowed": False,
                                  "rebaseMergeAllowed": False, "deleteBranchOnMerge": True}}
        self._save_gh()

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- git ---------------------------------------------------------------
    def _git(self, *args, cwd, check=True):
        proc = subprocess.run(["git", *args], cwd=cwd, env=self.env, text=True,
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

    def branch(self, name, changes, base="origin/main", msg=None):
        """A new branch on origin, cut from `base`, carrying one commit with `changes`."""
        self._git("fetch", "-q", "origin", cwd=self.author)
        ref = base if ("/" in base or re.fullmatch(r"[0-9a-f]{40}", base)) else "origin/" + base
        self._git("checkout", "-q", "-B", name, ref, cwd=self.author)
        return self.commit(name, changes, msg or "change on %s" % name, _new=True)

    def commit(self, name, changes, msg="another commit", _new=False):
        """One more commit on an existing branch, pushed."""
        if not _new:
            self._git("fetch", "-q", "origin", cwd=self.author)
            self._git("checkout", "-q", "-B", name, "origin/" + name, cwd=self.author)
        self._write(self.author, changes)
        self._git("add", "-A", cwd=self.author)
        self._git("commit", "-q", "-m", msg, cwd=self.author)
        self._git("push", "-q", "-f", "origin", name, cwd=self.author)
        return self._git("rev-parse", "HEAD", cwd=self.author)

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
           state="OPEN", merge_commit=None, mergeable="MERGEABLE"):
        self.gh_state = self.gh()
        self.gh_state["prs"][str(n)] = {
            "number": n, "title": title or "PR %d on %s" % (n, head), "body": body, "labels": list(labels),
            "baseRefName": base, "headRefName": head, "isDraft": draft, "state": state,
            "mergeCommit": merge_commit, "mergedAt": None, "mergeable": mergeable, "checks": checks,
            "comments": [], "url": "https://example.invalid/pull/%d" % n}
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
    def run(self, *args, script="batch.py", cwd=None):
        cmd = [sys.executable, os.path.join(self.dev, "scripts", script)] if script.endswith(".py") \
            else [os.path.join(self.dev, "scripts", script)]
        return subprocess.run([*cmd, *args], cwd=cwd or self.tmp, env=self.env, text=True,
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
        self.assertEqual(m["101"]["ci"], "success")
        self.assertEqual(st["base"], fx.bare_rev("main"))

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
        p = fx.run("verify", "b1", "--sweep", "x")
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
        self.assertIn("- #108 g: conflict resolved in notes.txt (1 hunk); one review round: subagent: fine. [combined diff below]", body)
        self.assertIn("### #108", body)
        self.assertIn("two-a-g", body, "the combined diff of the resolved merge is in the details")
        p = fx.ok("verify", "b1", "--sweep", "pytest 1 passed")
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
        p = fx.ok("verify", "b1", "--sweep", "pytest 1 passed")
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
        p = fx.run("verify", "b1", "--sweep", "pytest 1 passed")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("undeclared commit", p.stdout)
        fx._git("commit", "-q", "--amend", "-m", "batch: tweak", cwd=wt)
        p = fx.ok("verify", "b1", "--sweep", "pytest 1 passed")
        self.assertIn("ok   provenance: 2 member merge(s), 1 declared batch: commit(s), nothing else", p.stdout)
        self.assertTrue(fx.state("b1")["verified"]["ok"])

    def test_fails_when_a_pinned_head_moved(self):
        fx = self.fx
        self.assembled()
        fx.commit("a", {"kernel/kernel.py": "VERSION = 3\n"})
        p = fx.run("verify", "b1", "--sweep", "pytest 1 passed")
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
        p = fx.run("verify", "b1", "--sweep", "pytest 1 passed")
        self.assertEqual(p.returncode, 1)
        self.assertIn("undeclared change", p.stdout)

    def test_the_sweep_must_be_recorded_at_the_batch_head(self):
        fx = self.fx
        self.assembled()
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("sweep: none recorded", p.stdout)
        fx.ok("verify", "b1", "--sweep", "pytest 1 passed, bats 2")
        wt = fx.wt("b1")
        with open(os.path.join(wt, "t.txt"), "w") as f:
            f.write("t\n")
        fx._git("add", "t.txt", cwd=wt)
        fx._git("commit", "-q", "-m", "batch: t", cwd=wt)
        p = fx.run("verify", "b1")
        self.assertEqual(p.returncode, 1)
        self.assertIn("sweep: recorded at", p.stdout)
        self.assertIn("sweep again", p.stdout)

    def test_a_member_merged_alone_fails_verify(self):
        fx = self.fx
        self.assembled()
        fx.fake_gh("pr", "merge", "101", "--merge")
        p = fx.run("verify", "b1", "--sweep", "x")
        self.assertEqual(p.returncode, 1)
        self.assertIn("state: #101 is MERGED", p.stdout)


class Pull(_Base):
    def test_pull_drops_the_member_and_its_dependents_and_rebuilds(self):
        fx = self.fx
        self.two_members()
        fx.branch("k", {"k.txt": "k\n"})
        fx.pr(111, "k", title="k alone", labels=["fix"], body=TRAILER)
        fx.ok("plan", "--name", "b1")
        fx.ok("assemble", "b1")
        fx.push_batch("b1")
        fx.ok("verify", "b1", "--sweep", "pytest 3 passed")
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
        fx.ok("verify", "b1", "--sweep", "pytest 2 passed, bats 1, npm 1, typecheck clean")
        fx.ok("summarize", "b1")

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
        self.assertIn("batch #900 landed, 2 member(s) marked merged", p.stdout)
        self.assertIn("retargeted to main: #112", p.stdout)
        self.assertIn("pr-orphans.sh: clean", p.stdout)
        rep = fx.state("b1")["finished"]["report"]
        self.assertEqual(rep["merged"], [101, 102])
        self.assertEqual(rep["deleted"], ["a", "b"], "the fake keeps indirectly merged heads, so finish deleted them and said so")
        self.assertTrue(any("finish deleted head branches" in o for o in rep["observations"]))
        self.assertIn("postal (kind: coordinate) to the owners of #101, #102", p.stdout)

    def test_land_uses_auto_only_when_a_ruleset_exists(self):
        fx = self.fx
        self.ready()
        p = fx.run("land", "b1", "--auto")
        self.assertEqual(p.returncode, 1)
        self.assertIn("needs a ruleset", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])
        fx.set_gh(rulesets=[{"id": 1, "name": "main"}])
        fx.ok("land", "b1", "--auto")
        self.assertIn("--auto", fx.calls("pr", "merge")[0])

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


class LandSh(_Base):
    def setUp(self):
        super().setUp()
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.branch("old", {"old.txt": "old\n"})
        fx.branch("h", {"h.txt": "h\n"}, base="old")
        fx.pr(101, "a", labels=["fix"])
        fx.pr(100, "old", state="MERGED", merge_commit=fx.bare_rev("main"))
        fx.pr(108, "h", base="old", labels=["fix"])

    def test_refuses_squash_and_rebase(self):
        for flag in ("--squash", "-s", "--rebase", "-r"):
            p = self.fx.run("101", flag, script="land.sh")
            self.assertEqual(p.returncode, 2, flag)
            self.assertIn("Merge commits only", p.stderr)
        self.assertEqual(self.fx.calls("pr", "merge"), [])

    def test_refuses_a_base_belonging_to_a_merged_pr(self):
        p = self.fx.run("108", script="land.sh")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("merged PR #100", p.stderr)
        self.assertIn("gh pr edit 108 --base main", p.stderr)
        self.assertEqual(self.fx.calls("pr", "merge"), [])
        self.assertEqual(self.fx.gh()["prs"]["108"]["state"], "OPEN")

    def test_merges_one_pr_with_a_merge_commit_and_checks_orphans(self):
        fx = self.fx
        head = fx.bare_rev("a")
        p = fx.run("101", script="land.sh")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [["pr", "merge", "101", "--merge", "--delete-branch", "--match-head-commit", head]])
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")
        self.assertIn("pr-orphans: clean", p.stdout)

    def test_auto_only_with_a_ruleset(self):
        fx = self.fx
        fx.set_gh(rulesets=[{"id": 1}])
        p = fx.run("101", script="land.sh")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("--auto", fx.calls("pr", "merge")[0])
        self.assertIn("a ruleset exists", p.stdout)

    def test_refuses_a_draft_and_a_bad_argument(self):
        fx = self.fx
        fx.pr(113, "a", draft=True)
        p = fx.run("113", script="land.sh")
        self.assertEqual(p.returncode, 2)
        self.assertIn("draft", p.stderr)
        p = fx.run("101", "102", "103", script="land.sh")
        self.assertEqual(p.returncode, 2)
        self.assertIn("usage", p.stderr)


class Body(unittest.TestCase):
    """The generated body, as a pure function of the state: the cap and the "Read these first" rule."""

    @staticmethod
    def member(n, title="t", tier="fix", touches=("docs/x.md",), trailer="yes", ci="success", head_ref=None):
        t = {"tier": tier, "rounds": 2, "sweep": {"pytest": "1 passed", "bats": 1, "npm": 1, "typecheck": "clean"},
             "sweep_head": "abcdef0123456789"} if trailer == "yes" else None
        return {"n": n, "title": title, "url": "", "head": "%040x" % n, "head_ref": head_ref or "br%d" % n, "base_ref": "main",
                "labels": [tier] if tier else [], "tier": tier, "depends_on": [], "trailer": t, "trailer_error": None,
                "mergeable": "MERGEABLE", "ci": ci, "touches": list(touches), "predicted_conflict": None}

    @classmethod
    def state(cls, members, log_lines=0, resolved=(), held=(), pulled=()):
        merged = [{"n": m["n"], "merge": "%040x" % (m["n"] + 5000),
                   "resolved": ({"files": ["f.txt"], "how": "resolved by the batcher, per hunk", "hunks": 2, "review": "ok"}
                                if m["n"] in resolved else None)} for m in members]
        return {"name": "2026-01-01a", "base": "0" * 40, "order": [m["n"] for m in members],
                "members": {str(m["n"]): m for m in members}, "pulled": list(pulled),
                "assembly": {"merged": merged, "held": list(held), "head": "f" * 40,
                             "log": ["2026-01-01T00:00:00Z line %d" % i for i in range(log_lines)]},
                "sweep": {"text": "pytest 1 passed", "head": "f" * 40}, "ledger": "clean",
                "verified": {"ok": True, "head": "f" * 40, "lines": []}, "pr": None, "commented": {}}

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
        self.assertIn('Merge with "Create a merge commit". Verified at ffffffffff: pytest 1 passed; provenance clean; ledger check clean.', body)

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
        self.assertEqual(r(self.member(6, trailer=None), None), ["trailer not stated"])
        self.assertEqual(r(self.member(7, ci="none (was conflicting)"), None), ["own CI: none (was conflicting)"])
        self.assertEqual(r(self.member(8), {"files": ["a.py", "b.py"], "how": "x", "hunks": 3, "review": "one round by a subagent: ok"}),
                         ["conflict resolved in a.py, b.py (3 hunks); one review round: one round by a subagent: ok. [combined diff below]"])
        self.assertEqual(r(self.member(9), {"files": ["a.py"], "how": "x", "hunks": 1, "review": None}),
                         ["conflict resolved in a.py (1 hunk); review round NOT recorded. [combined diff below]"])
        st = self.state([self.member(10, tier=None, trailer=None, touches=("kernel/k.py",))])
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("- #10 br10: unlabeled; touches kernel/; trailer not stated.", body)
        self.assertIn("| #10 | t | unlabeled | not stated | not stated | success | unlabeled, kernel/, no trailer | - |", body)

    def test_held_back_lines_follow_the_template(self):
        st = self.state([self.member(1)], held=[{"n": 7, "reason": "conflicts with #1 in x.py", "files": ["x.py"], "with": [1]},
                                                {"n": 8, "reason": "depends on #7 (not in this batch)", "files": [], "with": []}], pulled=[9])
        body = batch.render_body(st, {"resolutions": [], "entries": []})
        self.assertIn("# Batch 2026-01-01a: 1 PR (2 held back, 1 pulled)", body)
        self.assertIn("- #7: conflicts with #1 in x.py; owner told.", body)
        self.assertIn("- #8: depends on #7 (not in this batch).", body)
        self.assertIn("- #9: pulled; the PR stays open against main.", body)


class Helpers(unittest.TestCase):
    def test_ci_reads_both_rollup_shapes(self):
        ci = batch.ci_of
        self.assertEqual(ci({"statusCheckRollup": [], "mergeable": "CONFLICTING"}), "none (was conflicting)")
        self.assertEqual(ci({"statusCheckRollup": [], "mergeable": "MERGEABLE"}), "none")
        self.assertEqual(ci({"statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"}]}), "success")
        self.assertEqual(ci({"statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"},
                                                   {"__typename": "CheckRun", "status": "IN_PROGRESS", "conclusion": None}]}), "pending")
        self.assertEqual(ci({"statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "FAILURE"},
                                                   {"__typename": "StatusContext", "state": "SUCCESS"}]}), "failure")
        self.assertEqual(ci({"statusCheckRollup": [{"__typename": "StatusContext", "state": "PENDING"}]}), "pending")

    def test_trailer_parsing(self):
        t, err = batch.parse_trailer("body\n" + TRAILER)
        self.assertEqual(t["rounds"], 3)
        self.assertIsNone(err)
        self.assertEqual(batch.parse_trailer("no trailer"), (None, None))
        t, err = batch.parse_trailer("<!-- romp-pr: {not json} -->")
        self.assertIsNone(t)
        self.assertIn("not JSON", err)

    def test_ordering_is_dependencies_first_then_by_number(self):
        cands = {5: {"depends_on": [9]}, 9: {"depends_on": []}, 7: {"depends_on": []}, 8: {"depends_on": [5]}}
        self.assertEqual(batch.order_members(cands), [7, 9, 5, 8])
        with self.assertRaises(batch.Fail):
            batch.order_members({1: {"depends_on": [2]}, 2: {"depends_on": [1]}})


if __name__ == "__main__":
    unittest.main()
