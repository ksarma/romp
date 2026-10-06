#!/usr/bin/env python3
"""scripts/land.sh: it runs `scripts/batch.py land` with its own arguments (it execs it) and has no merge logic of its
own (pre-round ruling, item 2), so a batch has one gated merge path: the one tests/test_batch_tool.py holds batch.py
land to (the sweep result at the verified head, the batch push's CI run, main read again right before the merge, and
finish).

What land.sh is held to:
  - Delegation (Delegates, against a stand-in batch.py beside a copy of land.sh that records its argv): every argument
    reaches `batch.py land` in order and verbatim (a value holding spaces, quotes or `=` included), batch.py's output
    and exit status pass through (0, 1, 2 and 3), no argument check of land.sh's own stands in front of it, and land.sh
    calls no gh itself; --help prints land.sh's usage, then batch.py land's help.
  - End to end (EndToEnd, the real batch.py and sweep.py in tests/test_batch_tool.py's Fixture, with its fake gh):
    land.sh lands a ready batch as batch.py land does (a merge commit pinned to the verified head, then finish), and
    refuses what batch.py land refuses: a batch behind main, with verify's remedy (`assemble <name> --merge-main`, then
    sweep and verify again; never `gh pr update-branch`, which puts a merge commit no sweep ran on onto the batch
    branch, round 1 extra7-8), a red batch CI run, a missing sweep result, and a PR number given for a batch name.
  - Its own text (Text): no gh call, no merge, no remedy of its own, nothing but the exec; the pin names the executed
    tests above that prove the behaviour, since a pin on where code lives is the weaker guarantee.

Retired with land.sh's own merge path (pre-round items 2 and 3); the suite at the frozen head held them: the refusal
table (not open, a draft, not a batch PR, merge commits off, conflicting, mergeability not computed, checks failing,
pending or none, blocked, behind, the three base cases and --into-open-pr), the pair ordering and its stops, --auto's
two preconditions and the --auto pair stops, the batch CI run read, the remote branch deletion, and the reads of a
branch name holding a comma or a brace. batch.py land's own tests cover what it keeps of them (LandAndFinish,
LandReadsTheCI, LandReadsTheSweep and VerifyBehind in tests/test_batch_tool.py); a member PR, a stacked pair merged by
hand and a merge into an open PR's branch no longer arise, since every PR lands through a batch. Among them were the
three land.sh tests that failed on macOS (BatchCIRun's newest-run and read-before-each-merge tests, BatchPRsOnly's
label-removed stop). tests/fixtures/land_fake_gh.py, the fake gh that suite used, retired with it.

Synthetic data only: the demo `notes-api` world of tests/test_batch_tool.py.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Hermetic state BEFORE tests/test_batch_tool.py loads scripts/batch.py and scripts/sweep.py: only pytest runs
# conftest's floor (a bare unittest or script run otherwise resolves REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

ROOT = Path(__file__).resolve().parents[1]
LAND_SH = ROOT / "scripts" / "land.sh"
# The checkout root on the path, so `python3 tests/test_land_sh.py` (the road the shebang and __main__ advertise)
# imports the sibling module as pytest does.
sys.path.insert(0, str(ROOT))
from tests.test_batch_tool import TRAILER, Fixture  # noqa: E402

# A stand-in for scripts/batch.py: it records its argv in argv.jsonl beside itself, prints one line to each stream, and
# exits with the status written in rc beside itself.
STAND_IN = r'''#!%(python)s
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "argv.jsonl"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
print("stand-in batch.py: out")
print("stand-in batch.py: err", file=sys.stderr)
with open(os.path.join(here, "rc")) as f:
    sys.exit(int(f.read()))
'''

# A gh that records every call, to show land.sh makes none of its own.
RECORDING_GH = r'''#!%(python)s
import json, os, sys
with open(os.environ["LANDSH_GH_LOG"], "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
sys.exit(1)
'''


class Delegates(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="landsh-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.scripts = os.path.join(self.tmp, "scripts")
        os.makedirs(self.scripts)
        shutil.copy(LAND_SH, os.path.join(self.scripts, "land.sh"))
        os.chmod(os.path.join(self.scripts, "land.sh"), 0o755)
        self.write("batch.py", STAND_IN % {"python": sys.executable}, 0o755)
        self.write("rc", "0")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        gh = os.path.join(self.bin, "gh")
        with open(gh, "w") as f:
            f.write(RECORDING_GH % {"python": sys.executable})
        os.chmod(gh, 0o755)
        self.gh_log = os.path.join(self.tmp, "gh.jsonl")
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ.get("PATH", ""), ROMP_GH=gh, LANDSH_GH_LOG=self.gh_log)

    def write(self, name, text, mode=None):
        path = os.path.join(self.scripts, name)
        with open(path, "w") as f:
            f.write(text)
        if mode is not None:
            os.chmod(path, mode)

    def land(self, *args):
        return subprocess.run([os.path.join(self.scripts, "land.sh"), *args], cwd=self.tmp, env=self.env, text=True,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def argvs(self):
        path = os.path.join(self.scripts, "argv.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(line) for line in f]

    def test_every_argument_reaches_batch_py_land_in_order_and_verbatim(self):
        args = ["b1", "--auto", "--flake", "12/1=tests/test_x.py::t (known-flakes.md, 'single' and \"double\" = quoted)",
                "--no-notify", "--no-fetch", "two words", ""]
        p = self.land(*args)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.argvs(), [["land", *args]])

    def test_batch_py_output_and_exit_status_pass_through(self):
        for rc in (0, 1, 2, 3):
            with self.subTest(rc=rc):
                self.write("rc", str(rc))
                p = self.land("b1")
                self.assertEqual(p.returncode, rc, p.stdout + p.stderr)
                self.assertEqual(p.stdout, "stand-in batch.py: out\n")
                self.assertEqual(p.stderr, "stand-in batch.py: err\n")

    def test_no_check_of_its_own_stands_in_front_of_batch_py(self):
        """land.sh once refused a squash flag, a count of PR numbers and an unknown flag itself; batch.py land's parser
        answers each now, so what land.sh is given always reaches it."""
        for args in ([], ["--squash", "900"], ["900", "901"], ["--into-open-pr", "b1"]):
            with self.subTest(args=args):
                open(os.path.join(self.scripts, "argv.jsonl"), "w").close()
                p = self.land(*args)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertEqual(self.argvs(), [["land", *args]])

    def test_land_sh_calls_no_gh_itself(self):
        p = self.land("b1", "--auto")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(self.gh_log), "land.sh made a gh call of its own")

    def test_help_prints_its_usage_then_batch_py_land_help(self):
        for flag in ("--help", "-h"):
            with self.subTest(flag=flag):
                open(os.path.join(self.scripts, "argv.jsonl"), "w").close()
                p = self.land(flag)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                self.assertTrue(p.stdout.startswith("usage: scripts/land.sh <name> [--auto] [--flake RUN/ATTEMPT=TEXT]... "
                                                    "[--no-notify] [--no-fetch]\n"), p.stdout)
                self.assertIn("runs `scripts/batch.py land` with the same arguments and has no merge logic of its\nown", p.stdout)
                self.assertIn("not a PR number", p.stdout)
                self.assertEqual(self.argvs(), [["land", "--help"]])


class EndToEnd(unittest.TestCase):
    """land.sh over the real batch.py and sweep.py, in tests/test_batch_tool.py's world (a bare origin, the fake gh)."""

    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.close)
        shutil.copy(LAND_SH, os.path.join(self.fx.dev, "scripts", "land.sh"))
        os.chmod(os.path.join(self.fx.dev, "scripts", "land.sh"), 0o755)
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

    def land(self, *args):
        return self.fx.run(*args, script="land.sh")

    def test_land_sh_lands_a_ready_batch_as_batch_py_land_does(self):
        fx = self.fx
        tip = fx.state("b1")["assembly"]["head"]
        before = fx.bare_rev("main")
        p = self.land("b1")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [["pr", "merge", "900", "--merge", "--match-head-commit", tip]])
        after = fx.bare_rev("main")
        self.assertEqual(fx._git("rev-list", "--parents", "-n1", after, cwd=fx.bare).split()[1:], [before, tip])
        self.assertIn("ok   CI: the run of the push to batch/b1 at %s is green" % tip[:10], p.stdout)
        self.assertIn("merged batch PR #900", p.stdout)
        self.assertIn("batch #900 landed, 1 member(s) marked merged", p.stdout, "finish ran")
        self.assertEqual(fx.gh()["prs"]["101"]["state"], "MERGED")

    def test_a_batch_behind_main_is_refused_with_verifys_remedy_never_update_branch(self):
        """Round 1, extra7-8, re-aimed at the delegation: land.sh's own behind refusal named `gh pr update-branch N`,
        which has GitHub put a merge commit no sweep ran on onto batch/<name>. The refusal is verify's now, naming
        `assemble <name> --merge-main`, then a sweep and verify, and nothing moves on origin."""
        fx = self.fx
        batch_before = fx.bare_rev("batch/b1")
        moved = fx.commit_main({"README.md": "# notes-api\n\nmoved\n"}, "main moved")
        p = self.land("b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertNotIn("update-branch", p.stdout + p.stderr)
        self.assertIn("FAIL behind: origin/main is at %s" % moved[:10], p.stdout)
        self.assertIn("`scripts/batch.py assemble b1 --merge-main`, then sweep and verify again", p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [], "nothing merged")
        self.assertEqual(fx.calls("pr", "update-branch"), [])
        self.assertEqual(fx.bare_rev("batch/b1"), batch_before, "the batch branch did not move")

    def test_a_red_batch_ci_run_is_refused(self):
        fx = self.fx
        fx.set_gh(runs=[])
        url = fx.ci("b1", conclusion="failure")
        p = self.land("b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("the batch head's CI run is red (conclusion failure): %s" % url, p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_a_missing_sweep_result_is_refused(self):
        fx = self.fx
        tip = fx.state("b1")["assembly"]["head"]
        os.remove(fx.sweep("b1"))
        p = self.land("b1")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL sweep missing: no result for the batch head %s" % tip, p.stdout)
        self.assertEqual(fx.calls("pr", "merge"), [])

    def test_a_pr_number_is_not_a_batch_name(self):
        """land.sh took PR numbers before it ran batch.py land; a number now reads as a batch name, and there is no plan
        by that name, so nothing is read from GitHub or merged."""
        fx = self.fx
        p = self.land("900")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("no plan named 900", p.stderr)
        self.assertEqual(fx.calls("pr", "merge"), [])


class Text(unittest.TestCase):
    def test_the_script_holds_nothing_but_the_exec(self):
        """Guards pre-round item 2 where the code lives: outside its comments and its --help text, land.sh is the
        strict-mode line, the path of the batch.py beside it, the --help branch and one exec of `batch.py land "$@"`; no
        gh call, no merge, no remedy of its own can come back unseen. The behaviour is proved by execution in
        Delegates (every argument reaches batch.py land verbatim, no gh call) and EndToEnd (the behind refusal is
        verify's, never update-branch)."""
        code, in_heredoc = [], False
        for line in LAND_SH.read_text().splitlines():
            s = line.strip()
            if in_heredoc:
                in_heredoc = s != "EOF"
                continue
            if s.startswith("cat <<'EOF'"):
                in_heredoc = True
                continue
            if s and not s.startswith("#"):
                code.append(s)
        self.assertEqual(code, [
            "set -euo pipefail",
            'BATCH="$(cd "$(dirname "$0")" && pwd)/batch.py"',
            'if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then',
            'exec "$BATCH" land --help',
            "fi",
            'exec "$BATCH" land "$@"',
        ])


if __name__ == "__main__":
    unittest.main()
