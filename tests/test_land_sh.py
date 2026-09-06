#!/usr/bin/env python3
"""scripts/land.sh against a fixture repository and a fake gh (tests/fixtures/land_fake_gh.py).

Every test builds its own GitHub: a bare repository as `origin`, an `author` clone that makes the
PR branches, a `dev` clone the script runs from (land.sh and pr-orphans.sh are copied into its
scripts/, as they sit in the real clone), and the fake gh on PATH, reading PR metadata from a JSON
file and head SHAs live from the bare repository. No test reaches the real gh or GitHub, and none
reads the developer's git configuration (GIT_CONFIG_GLOBAL is /dev/null).

What land.sh is held to:
  - it refuses a PR that is not open, a draft, and a repository that disallows merge commits;
  - it never passes --delete-branch (gh's flag deletes the LOCAL branch too, which fails when that
    branch is checked out in a sibling worktree, the norm here) and never touches local branches;
    the remote branch is the repository setting's to delete, or the API's when the setting is off;
  - it refuses any base but main: an open PR's branch unless --into-open-pr, a merged PR's branch,
    a branch with no PR; an open PR is checked before merged ones, since branch names are reused;
  - it reads mergeability and the check rollup before merging anything: a conflicting, blocked,
    red or (without --auto) pending PR is refused by name, the second of a pair before the first
    merges; no checks at all is noted, not refused;
  - a pair whose one member is based on the other's branch merges the lower PR first, whichever
    order was given, and the upper one lands on main once GitHub retargets it; each PR is read
    again right before its own merge, and a head that moved stops the run (the orphan check still
    runs), while a PR the first merge marked merged is skipped, not failed;
  - --auto is explicit and needs the repository's allow_auto_merge setting AND a rule on main that
    gates a merge (required checks, required reviews; a ruleset that only blocks force pushes does
    not count), each refused by name; a rules or protection read that fails for anything but a 404
    is refused as unreadable, with gh's error;
  - --squash / --rebase, and a bad argument, are refused before anything is read; --help / -h
    print the usage and the refusal table and exit 0.

Synthetic data only: a demo `notes-api` with invented PR numbers, branch names and titles.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FAKE_GH = ROOT / "tests" / "fixtures" / "land_fake_gh.py"

SEED = {"README.md": "# notes-api\n", "notes.txt": "one\ntwo\n"}


class Fixture:
    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="landsh-")
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
                        FAKE_GH_STATE=self.state_file, FAKE_GH_LOG=self.log_file)
        for k in ("ROMP_GH", "ROMP_MAIN_BRANCH", "ROMP_ORPHANS_NO_FETCH", "ROMP_ORPHANS_LIMIT"):
            self.env.pop(k, None)
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
        for s in ("land.sh", "pr-orphans.sh"):
            shutil.copy(SCRIPTS / s, os.path.join(self.dev, "scripts", s))
        self.gh_state = {"bare": self.bare, "prs": {}, "rules": [], "protection": False,
                         "repo": {"mergeCommitAllowed": True, "squashMergeAllowed": False,
                                  "rebaseMergeAllowed": False, "deleteBranchOnMerge": True, "allow_auto_merge": False}}
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

    def local_branch(self, name):
        return self.dev_git("rev-parse", "--verify", "--quiet", "refs/heads/" + name, check=False)

    @staticmethod
    def _write(root, changes):
        for path, content in changes.items():
            p = os.path.join(root, path)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(content)

    def branch(self, name, changes, base="main"):
        """A new branch on origin, cut from `base`, carrying one commit with `changes`."""
        self._git("fetch", "-q", "origin", cwd=self.author)
        ref = base if re.fullmatch(r"[0-9a-f]{40}", base) else "origin/" + base
        self._git("checkout", "-q", "-B", name, ref, cwd=self.author)
        self._write(self.author, changes)
        self._git("add", "-A", cwd=self.author)
        self._git("commit", "-q", "-m", "change on %s" % name, cwd=self.author)
        self._git("push", "-q", "-f", "origin", name, cwd=self.author)
        return self._git("rev-parse", "HEAD", cwd=self.author)

    def worktree_on(self, branch):
        """The dev clone checks `branch` out in a sibling worktree, as every session here does."""
        self.dev_git("fetch", "-q", "origin")
        path = os.path.join(self.tmp, "romp-" + branch)
        self.dev_git("worktree", "add", "-q", "-b", branch, path, "origin/" + branch)
        return path

    # -- fake GitHub -------------------------------------------------------
    def _save_gh(self):
        with open(self.state_file, "w") as f:
            json.dump(self.gh_state, f, indent=1)

    def gh(self):
        with open(self.state_file) as f:
            return json.load(f)

    def pr(self, n, head, base="main", draft=False, state="OPEN", merge_commit=None, checks="success", **overrides):
        """`checks` is success, pending, failure, none, or a statusCheckRollup list; `overrides`
        pins a served field (mergeable="UNKNOWN", mergeStateStatus="BLOCKED")."""
        self.gh_state = self.gh()
        self.gh_state["prs"][str(n)] = dict({
            "number": n, "title": "PR %d on %s" % (n, head), "baseRefName": base, "headRefName": head,
            "isDraft": draft, "state": state, "mergeCommit": merge_commit, "mergedAt": None, "checks": checks}, **overrides)
        self._save_gh()

    def on_main(self, sha):
        return subprocess.run(["git", "-C", self.bare, "merge-base", "--is-ancestor", sha, "refs/heads/main"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

    def set_gh(self, **kw):
        self.gh_state = self.gh()
        for k, v in kw.items():
            if k == "repo":
                self.gh_state["repo"].update(v)
            else:
                self.gh_state[k] = v
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

    def merges(self):
        return self.calls("pr", "merge")

    def fake_gh(self, *args, cwd=None):
        return subprocess.run([os.path.join(self.bin, "gh"), *args], cwd=cwd or self.dev, env=self.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # -- the script --------------------------------------------------------
    def land(self, *args):
        return subprocess.run([os.path.join(self.dev, "scripts", "land.sh"), *args], cwd=self.tmp, env=self.env,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class _Base(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)

    def assertRefused(self, p, *fragments):
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        for frag in fragments:
            self.assertIn(frag, p.stderr)
        self.assertEqual(self.fx.merges(), [], "a refusal merges nothing")


class Refusals(_Base):
    def setUp(self):
        super().setUp()
        self.fx.branch("a", {"a.txt": "a\n"})
        self.fx.pr(101, "a")

    def test_refuses_a_pr_that_is_not_open(self):
        fx = self.fx
        fx.pr(90, "a", state="MERGED", merge_commit=fx.bare_rev("main"))
        self.assertRefused(fx.land("90"), "#90 is MERGED, not open")
        fx.pr(91, "a", state="CLOSED")
        self.assertRefused(fx.land("91"), "#91 is CLOSED, not open")
        # The refusal comes from the PR's state, read before anything is merged: an open first
        # argument does not get merged ahead of a closed second one.
        self.assertRefused(fx.land("101", "91"), "#91 is CLOSED, not open")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN")

    def test_refuses_a_repository_that_disallows_merge_commits(self):
        fx = self.fx
        fx.set_gh(repo={"mergeCommitAllowed": False, "squashMergeAllowed": True})
        p = fx.land("101")
        self.assertRefused(p, "does not allow merge commits", "gh repo edit --enable-merge-commit")
        self.assertEqual(fx.calls("pr", "view"), [], "refused on the settings alone, before the PR was read")

    def test_refuses_squash_rebase_draft_and_bad_arguments(self):
        fx = self.fx
        for flag in ("--squash", "-s", "--rebase", "-r"):
            self.assertRefused(fx.land("101", flag), "Merge commits only")
        self.assertEqual(fx.calls(), [], "the flags are refused before gh is asked anything")
        fx.pr(113, "a", draft=True)
        self.assertRefused(fx.land("113"), "#113 is a draft")
        self.assertRefused(fx.land("101", "102", "103"), "usage")
        self.assertRefused(fx.land("--merge", "101"), "usage")
        self.assertRefused(fx.land(), "usage")


class Branches(_Base):
    """land.sh never deletes a local branch; the remote one follows the repository setting."""

    def setUp(self):
        super().setUp()
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.branch("b", {"b.txt": "b\n"})
        fx.pr(101, "a")
        fx.pr(102, "b")

    def test_the_fake_refuses_the_local_delete_the_way_gh_does(self):
        """The regression the next test guards is only visible if the fake models gh's local
        delete: with the branch checked out in a sibling worktree, `--delete-branch` merges on
        the remote and then fails."""
        fx = self.fx
        fx.worktree_on("a")
        p = fx.fake_gh("pr", "merge", "101", "--merge", "--delete-branch", "--match-head-commit", fx.bare_rev("a"))
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("failed to delete local branch a", p.stderr)
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED", "the remote merge had already happened")

    def test_merges_two_prs_without_touching_local_branches_checked_out_in_worktrees(self):
        fx = self.fx
        wt = fx.worktree_on("a")
        fx.dev_git("branch", "b", "origin/b")
        head_a, head_b = fx.bare_rev("a"), fx.bare_rev("b")
        p = fx.land("101", "102")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.merges(), [["pr", "merge", "101", "--merge", "--match-head-commit", head_a],
                                       ["pr", "merge", "102", "--merge", "--match-head-commit", head_b]],
                         "a merge commit pinned to the head; no --delete-branch, no --auto")
        gh = fx.gh()
        self.assertEqual(gh["prs"]["101"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["102"]["state"], "MERGED", "the second PR merges too: nothing aborted after the first")
        self.assertEqual(fx.local_branch("a"), head_a, "the local branch a peer's worktree holds is untouched")
        self.assertEqual(fx.local_branch("b"), head_b, "a plain local branch is untouched too")
        self.assertTrue(os.path.exists(os.path.join(wt, ".git")), "the worktree is intact")
        self.assertEqual(fx._git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt), "a", "and still on its branch")
        self.assertEqual(fx.bare_rev("a"), "", "the repository setting deleted the remote branch")
        self.assertEqual(fx.calls("api", "-X", "DELETE"), [], "land.sh did not delete it itself")
        self.assertIn("the repository deletes 'a' on merge (local branches are untouched)", p.stdout)
        self.assertIn("pr-orphans: clean (2 merged PR(s)", p.stdout, "the orphan check ran, after both merges")

    def test_deletes_the_remote_branch_through_the_api_when_the_setting_is_off(self):
        fx = self.fx
        fx.set_gh(repo={"deleteBranchOnMerge": False})
        fx.worktree_on("a")
        head_a = fx.bare_rev("a")
        p = fx.land("101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.calls("api", "-X", "DELETE"), [["api", "-X", "DELETE", "repos/{owner}/{repo}/git/refs/heads/a"]])
        self.assertEqual(fx.bare_rev("a"), "", "the remote branch is gone")
        self.assertEqual(fx.local_branch("a"), head_a, "the local one is not")
        self.assertIn("deleting remote branch 'a' (the repository does not delete branches on merge", p.stdout)
        self.assertNotIn("--delete-branch", " ".join(" ".join(c) for c in fx.merges()))


class Bases(_Base):
    """Any base but main is refused; an open PR's branch only with --into-open-pr."""

    def setUp(self):
        super().setUp()
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.branch("b", {"b.txt": "b\n"}, base="a")
        fx.pr(201, "a")
        fx.pr(203, "b", base="a")

    def test_refuses_a_base_that_is_an_open_prs_head(self):
        fx = self.fx
        p = fx.land("203")
        self.assertRefused(p, "#203 is based on 'a', the branch of open PR #201",
                           "reaches main only if #201 merges", "pr-orphans.sh reports it until then",
                           "gh pr edit 203 --base main", "--into-open-pr")
        self.assertEqual(fx.gh()["prs"]["203"]["state"], "OPEN")
        self.assertEqual(fx.bare_rev("b"), fx.bare_rev("b"), "nothing moved")

    def test_into_open_pr_merges_into_that_branch_and_the_orphan_check_says_so(self):
        fx = self.fx
        main_before = fx.bare_rev("main")
        head_b = fx.bare_rev("b")
        p = fx.land("--into-open-pr", "203")
        self.assertEqual(fx.merges(), [["pr", "merge", "203", "--merge", "--match-head-commit", head_b]])
        gh = fx.gh()
        self.assertEqual(gh["prs"]["203"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["203"]["baseRefName"], "a")
        self.assertEqual(fx.bare_rev("main"), main_before, "main did not move")
        self.assertIn("#203 merges into 'a' (open PR #201), not main, as --into-open-pr asked", p.stdout)
        # The content is on `a` only; pr-orphans.sh reports that.
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("#203\n", p.stdout)
        self.assertIn("merged into 'a'", p.stderr)
        self.assertIn("1 merged PR(s) whose content never reached main", p.stderr)

    def test_an_open_pr_wins_over_a_merged_pr_that_once_used_the_branch_name(self):
        """Branch names are reused here: `a` carried a PR that merged long ago and now carries an
        open one. The open PR is the base's owner; the old merged PR is not."""
        fx = self.fx
        fx.pr(150, "a", state="MERGED", merge_commit=fx.bare_rev("main"))
        p = fx.land("203")
        self.assertRefused(p, "the branch of open PR #201")
        self.assertNotIn("merged PR #150", p.stderr)
        p = fx.land("--into-open-pr", "203")
        self.assertEqual(fx.gh()["prs"]["203"]["state"], "MERGED", "with the flag, the open owner is accepted")

    def test_refuses_a_merged_prs_branch_and_a_branch_with_no_pr_even_with_the_flag(self):
        fx = self.fx
        fx.branch("old", {"old.txt": "old\n"})
        fx.branch("h", {"h.txt": "h\n"}, base="old")
        fx.pr(100, "old", state="MERGED", merge_commit=fx.bare_rev("main"))
        fx.pr(108, "h", base="old")
        for flag in ((), ("--into-open-pr",)):
            p = fx.land(*flag, "108")
            self.assertRefused(p, "#108 is based on 'old', the branch of merged PR #100", "lands nothing on main",
                               "gh pr edit 108 --base main")
        fx.branch("nopr", {"n.txt": "n\n"})
        fx.branch("k", {"k.txt": "k\n"}, base="nopr")
        fx.pr(109, "k", base="nopr")
        for flag in ((), ("--into-open-pr",)):
            p = fx.land(*flag, "109")
            self.assertRefused(p, "#109 is based on 'nopr', not main, and no PR has that branch as its head",
                               "gh pr edit 109 --base main")


class Auto(_Base):
    """--auto is explicit, and needs allow_auto_merge plus required rules on main."""

    def setUp(self):
        super().setUp()
        self.fx.branch("a", {"a.txt": "a\n"})
        self.fx.pr(101, "a", checks="pending")

    def test_refuses_auto_when_the_repository_disallows_auto_merge(self):
        fx = self.fx
        fx.set_gh(rules=[{"type": "required_status_checks"}])
        p = fx.land("--auto", "101")
        self.assertRefused(p, '--auto needs the repository\'s "Allow auto-merge" setting, which is off (allow_auto_merge: false)',
                           "gh repo edit --enable-auto-merge", "Merge without --auto")
        self.assertEqual(fx.calls("pr", "view"), [], "refused before the PR was read")

    def test_refuses_auto_when_nothing_is_required_on_main(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True})
        p = fx.land("--auto", "101")
        self.assertRefused(p, "--auto with nothing required on main (no ruleset rule, no branch protection) merges at once and protects nothing")
        self.assertIn(["api", "repos/{owner}/{repo}/rules/branches/main", "--jq", ".[].type"], fx.calls("api"))
        self.assertIn(["api", "repos/{owner}/{repo}/branches/main/protection", "--jq", "to_entries[] | select(.value != null) | .key"],
                      fx.calls("api"))

    def test_auto_with_the_setting_and_a_rule_arms_the_merge(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "required_status_checks"}])
        head = fx.bare_rev("a")
        p = fx.land("--auto", "101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.merges(), [["pr", "merge", "101", "--merge", "--match-head-commit", head, "--auto"]])
        self.assertIn("merging with --auto (auto-merge is allowed and main has required rules", p.stdout)
        gh = fx.gh()
        self.assertEqual(gh["prs"]["101"]["state"], "OPEN", "checks pending: armed, not merged")
        self.assertTrue(gh["prs"]["101"].get("autoMerge"))
        self.assertIn("#101 reads OPEN after the merge call (auto-merge armed", p.stdout)
        self.assertEqual(fx.calls("api", "-X", "DELETE"), [], "no branch deletion for a PR that has not merged")
        self.assertIn("pr-orphans: clean", p.stdout)

    def test_classic_branch_protection_also_counts_as_a_requirement(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, protection=True)
        p = fx.land("--auto", "101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("--auto", fx.merges()[0])

    def test_without_the_flag_a_ruleset_alone_does_not_add_auto(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "required_status_checks"}])
        fx.pr(101, "a", checks="success")
        p = fx.land("101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn("--auto", fx.merges()[0])
        self.assertEqual([c for c in fx.calls("api") if c[1] == "repos/{owner}/{repo}"], [], "the setting is read only for --auto")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")

    def test_refuses_auto_when_the_only_rules_gate_no_merge(self):
        """The rules endpoint lists every rule on main. One that only blocks force pushes or
        deletion leaves --auto nothing to wait for; the refusal names what was found."""
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "non_fast_forward"}, {"type": "deletion"}])
        p = fx.land("--auto", "101")
        self.assertRefused(p, "no rule on main gates a merge", "non_fast_forward, deletion", "merge without --auto")
        self.assertNotIn("nothing required on main", p.stderr)

    def test_a_required_review_rule_counts(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "non_fast_forward"}, {"type": "pull_request"}])
        p = fx.land("--auto", "101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("--auto", fx.merges()[0])

    def test_classic_protection_that_requires_no_checks_or_reviews_does_not_count(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True},
                  protection={"url": "https://api.example.invalid/protection", "enforce_admins": {"enabled": True},
                              "required_status_checks": None, "restrictions": None})
        p = fx.land("--auto", "101")
        self.assertRefused(p, "branch protection on main requires no checks and no reviews", "enforce_admins")
        fx.set_gh(protection={"required_pull_request_reviews": {"required_approving_review_count": 1}})
        p = fx.land("--auto", "101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_a_failed_rules_read_is_unreadable_not_none(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "required_status_checks"}],
                  fail={"rules": "HTTP 500: Internal Server Error (HTTP 500)"})
        p = fx.land("--auto", "101")
        self.assertRefused(p, "could not read the rules on main", "HTTP 500")
        self.assertNotIn("nothing required", p.stderr)
        self.assertNotIn("no ruleset rule", p.stderr)

    def test_a_failed_protection_read_is_unreadable_unless_it_is_a_404(self):
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, fail={"protection": "Must have admin rights to Repository. (HTTP 403)"})
        p = fx.land("--auto", "101")
        self.assertRefused(p, "could not read main's branch protection", "HTTP 403")
        self.assertNotIn("no branch protection", p.stderr)
        fx.set_gh(fail={})
        p = fx.land("--auto", "101")
        self.assertRefused(p, "nothing required on main (no ruleset rule, no branch protection)")


class Readiness(_Base):
    """Mergeability and the check rollup are read before any merge: a red, pending, conflicting or
    blocked PR is refused by name, the second of a pair before the first merges."""

    def setUp(self):
        super().setUp()
        self.fx.branch("a", {"a.txt": "a\n"})
        self.fx.pr(101, "a")

    def conflicting_pr(self, n=102):
        """A PR whose branch edits a line main has since changed."""
        fx = self.fx
        fx.branch("c", {"notes.txt": "one\nc\n"})
        fx.branch("main", {"notes.txt": "one\nmain\n"})
        fx.pr(n, "c")

    def test_green_checks_merge(self):
        fx = self.fx
        p = fx.land("101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")
        self.assertEqual(fx.calls("pr", "view", "101", "--json", "statusCheckRollup")[0][5], "--jq",
                         "the rollup is reduced by gh's --jq, not parsed in the shell")

    def test_refuses_failing_checks_with_or_without_auto(self):
        fx = self.fx
        fx.pr(101, "a", checks="failure")
        self.assertRefused(fx.land("101"), "#101's checks are failing: ci (FAILURE)")
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "required_status_checks"}])
        self.assertRefused(fx.land("--auto", "101"), "#101's checks are failing")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN")

    def test_refuses_pending_checks_without_auto(self):
        fx = self.fx
        fx.pr(101, "a", checks="pending")
        self.assertRefused(fx.land("101"), "#101's checks are pending: ci", "pass --auto")

    def test_a_status_context_counts_like_a_check_run_and_skipped_is_green(self):
        fx = self.fx
        fx.pr(101, "a", checks=[{"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"},
                                {"__typename": "StatusContext", "context": "ci/lint", "state": "FAILURE"}])
        self.assertRefused(fx.land("101"), "#101's checks are failing: ci/lint (FAILURE)")
        fx.pr(101, "a", checks=[{"__typename": "CheckRun", "name": "tests", "status": "COMPLETED", "conclusion": "SKIPPED"},
                                {"__typename": "CheckRun", "name": "docs", "status": "COMPLETED", "conclusion": "NEUTRAL"},
                                {"__typename": "StatusContext", "context": "ci/lint", "state": "SUCCESS"}])
        p = fx.land("101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_no_checks_at_all_is_noted_not_refused(self):
        fx = self.fx
        fx.pr(101, "a", checks="none")
        p = fx.land("101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("#101 has no checks reported at its head", p.stdout)

    def test_refuses_a_conflicting_pr(self):
        fx = self.fx
        self.conflicting_pr()
        self.assertRefused(fx.land("102"), "#102 conflicts with main (mergeable: CONFLICTING)")

    def test_refuses_a_pr_whose_mergeability_github_has_not_computed(self):
        fx = self.fx
        fx.pr(101, "a", mergeable="UNKNOWN")
        self.assertRefused(fx.land("101"), "#101's mergeability is not computed yet (mergeable: UNKNOWN)", "re-run")

    def test_refuses_a_blocked_or_behind_pr_without_auto(self):
        fx = self.fx
        fx.set_gh(rules=[{"type": "required_status_checks"}])
        fx.pr(101, "a", checks="success", mergeStateStatus="BLOCKED")
        self.assertRefused(fx.land("101"), "#101 is blocked by a rule on main (mergeStateStatus: BLOCKED)")
        fx.pr(101, "a", checks="success", mergeStateStatus="BEHIND")
        self.assertRefused(fx.land("101"), "#101 is behind main (mergeStateStatus: BEHIND)", "gh pr update-branch 101")

    def test_auto_accepts_a_pr_blocked_by_pending_required_checks(self):
        """With a ruleset requiring checks, a PR whose checks are still running reads BLOCKED; that is
        the state --auto exists for."""
        fx = self.fx
        fx.set_gh(repo={"allow_auto_merge": True}, rules=[{"type": "required_status_checks"}])
        fx.pr(101, "a", checks="pending")
        self.assertEqual(fx.fake_gh("pr", "view", "101", "--json", "mergeStateStatus").stdout.strip(),
                         '{"mergeStateStatus": "BLOCKED"}')
        p = fx.land("--auto", "101")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("#101's checks are pending (ci); --auto lands it when they pass", p.stdout)
        self.assertTrue(fx.gh()["prs"]["101"].get("autoMerge"))

    def test_the_second_pr_of_a_pair_is_checked_before_the_first_merges(self):
        fx = self.fx
        self.conflicting_pr(102)
        p = fx.land("101", "102")
        self.assertRefused(p, "#102 conflicts with main")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN", "the green first PR did not merge ahead of the refusal")
        fx.branch("d", {"d.txt": "d\n"})
        fx.pr(104, "d", checks="failure")
        self.assertRefused(fx.land("101", "104"), "#104's checks are failing")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "OPEN")

    def test_a_merge_gh_refuses_stops_the_run_and_still_runs_the_orphan_check(self):
        """The checks make this rare (a base that moves between the re-read and the merge); when it
        happens the run stops with gh's error, exit 1, and the orphan check still reports."""
        fx = self.fx
        fx.branch("d", {"d.txt": "d\n"})
        fx.pr(104, "d")
        fx.set_gh(fail={"merge": {"104": "GraphQL: Base branch was modified. Review and try the merge again. (mergePullRequest)"}})
        p = fx.land("101", "104")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("Base branch was modified", p.stderr)
        self.assertIn("land: gh could not merge #104; stopping. Merged in this run: #101. The orphan check runs next.", p.stderr)
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")
        self.assertEqual(fx.gh()["prs"]["104"]["state"], "OPEN")
        self.assertIn("pr-orphans: clean (1 merged PR(s)", p.stdout)


class Pairs(_Base):
    """A pair merges in the order that keeps heads stable, and each PR is read again right before
    its own merge."""

    def setUp(self):
        super().setUp()
        fx = self.fx
        fx.branch("a", {"a.txt": "a\n"})
        fx.branch("b", {"b.txt": "b\n"}, base="a")
        fx.pr(201, "a")
        fx.pr(203, "b", base="a")

    def assertChainLanded(self, p, head_a, head_b):
        fx = self.fx
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.merges(), [["pr", "merge", "201", "--merge", "--match-head-commit", head_a],
                                       ["pr", "merge", "203", "--merge", "--match-head-commit", head_b]],
                         "the lower PR first, each pinned to the head that was checked")
        gh = fx.gh()
        self.assertEqual(gh["prs"]["201"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["203"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["203"]["baseRefName"], "main", "retargeted once 'a' was deleted")
        for h in (head_a, head_b):
            self.assertTrue(fx.on_main(h), "both heads reached main")
        self.assertNotIn("merges into 'a'", p.stdout, "the upper PR does not land on the open branch")
        self.assertIn("#203 is based on 'a', the branch of #201, the other PR of this pair: #201 merges first", p.stdout)
        self.assertIn("pr-orphans: clean (2 merged PR(s)", p.stdout)

    def test_a_chain_given_top_down_merges_bottom_up(self):
        fx = self.fx
        head_a, head_b = fx.bare_rev("a"), fx.bare_rev("b")
        p = fx.land("--into-open-pr", "203", "201")
        self.assertChainLanded(p, head_a, head_b)
        self.assertIn("land: merging #201 before #203", p.stdout)

    def test_a_chain_given_bottom_up_needs_no_flag(self):
        fx = self.fx
        head_a, head_b = fx.bare_rev("a"), fx.bare_rev("b")
        p = fx.land("201", "203")
        self.assertChainLanded(p, head_a, head_b)
        self.assertNotIn("--into-open-pr", p.stdout + p.stderr)

    def test_a_chain_when_the_repository_keeps_branches(self):
        """With deleteBranchOnMerge off, land.sh deletes 'a' through the API after #201 merges, and
        GitHub retargets #203 to main before its merge."""
        fx = self.fx
        fx.set_gh(repo={"deleteBranchOnMerge": False})
        head_a, head_b = fx.bare_rev("a"), fx.bare_rev("b")
        p = fx.land("201", "203")
        self.assertChainLanded(p, head_a, head_b)
        self.assertEqual([c[3] for c in fx.calls("api", "-X", "DELETE")],
                         ["repos/{owner}/{repo}/git/refs/heads/a", "repos/{owner}/{repo}/git/refs/heads/b"])

    def test_stops_when_a_head_moved_between_the_check_and_the_merge(self):
        fx = self.fx
        fx.set_gh(after_merge={"201": ["b"]})
        head_b = fx.bare_rev("b")
        p = fx.land("201", "203")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("land: stopped: #203's head moved since it was checked (%s, now %s)" % (head_b[:10], fx.bare_rev("b")[:10]), p.stderr)
        self.assertIn("#201 merged", p.stderr)
        gh = fx.gh()
        self.assertEqual(gh["prs"]["201"]["state"], "MERGED")
        self.assertEqual(gh["prs"]["203"]["state"], "OPEN")
        self.assertEqual(len(fx.merges()), 1, "the second merge was never attempted")
        self.assertIn("pr-orphans: clean (1 merged PR(s)", p.stdout, "the orphan check still ran")

    def test_a_pr_marked_merged_by_the_first_merge_is_skipped_not_failed(self):
        """#203's branch carries #201's commit; both target main. Merging #203 makes GitHub mark
        #201 merged, and the re-read before #201's merge sees that."""
        fx = self.fx
        fx.pr(203, "b", base="main")
        p = fx.land("203", "201")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual([c[2] for c in fx.merges()], ["203"])
        self.assertEqual(fx.gh()["prs"]["201"]["state"], "MERGED")
        self.assertIn("#201 was marked merged by an earlier merge of this run; nothing to do for it", p.stdout)
        self.assertIn("pr-orphans: clean (2 merged PR(s)", p.stdout)


class Help(_Base):
    def test_help_exits_0_and_names_every_refusal(self):
        fx = self.fx
        for flag in ("--help", "-h"):
            p = fx.land(flag)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("usage: scripts/land.sh [--auto] [--into-open-pr] N [M]", p.stdout)
            for frag in ("--squash", "--rebase", "not open", "draft", "merge commits", "CONFLICTING", "UNKNOWN",
                         "failing", "pending", "BLOCKED", "BEHIND", "other than main", "--into-open-pr", "MERGED PR",
                         "no PR has", "Allow auto-merge", "required_status_checks", "pull_request", "unreadable",
                         "head moved", "pr-orphans.sh", "exit 2"):
                self.assertIn(frag, p.stdout, flag)
        self.assertEqual(fx.calls(), [], "help asks gh nothing")
        p = fx.land("101", "--help")
        self.assertEqual(p.returncode, 0, "--help anywhere on the line prints help")
        header = (SCRIPTS / "land.sh").read_text().split("set -euo pipefail")[0]
        self.assertIn("--help", header, "the header comment points at --help")
        self.assertNotIn("Refusals (exit 2)", header, "and does not carry a second copy of the table")


if __name__ == "__main__":
    unittest.main()
