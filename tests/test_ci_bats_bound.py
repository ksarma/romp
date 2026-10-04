#!/usr/bin/env python3
"""The bats step of CI carries a per-test bound from bats itself (.github/workflows/ci.yml, 2026-09-16).

The macOS bats leg (a manual dispatch) was cancelled at the job's 35-minute ceiling on every run, nameless:
the job annotation says only that the maximum execution time was exceeded, and the TAP stream stops at the
last test that finished. BATS_TEST_TIMEOUT is bats-core's own bound (since 1.8, in the pinned 1.11.1 and in
Homebrew's 1.14.0 alike): a background sleep, then pkill or ps on the test's children, and the test's TAP
line ends "# timeout after Ns", so a hung test fails in minutes and is named. No coreutils timeout, which the
macOS image lacks. Source pins, as tests/test_ci_workflow_concurrency.py: no YAML library in the test deps."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "ci.yml")


def run_bats_step(path=WF):
    """(the step's lines between its name and its run line, its run command) of the shell job's Run bats step, read off the
    workflow text at path: what BatsStepBound pins, and the reading tests/test_bats_bare_negation.py derives its population of
    suites from (the command's glob), imported from here so the two read one text one way. Raises LookupError when the step moved
    or was renamed."""
    src = open(path).read()
    m = re.search(r"^      - name: Run bats\n((?:        .*\n)*?)        run: (bats .*)\n", src, re.M)   # zero lines between: the step without an env
    if not m:
        raise LookupError("the Run bats step moved or was renamed (%s): re-anchor this pin" % path)
    return m.group(1), m.group(2)


class BatsStepBound(unittest.TestCase):
    def setUp(self):
        self.head, self.cmd = run_bats_step()

    def test_the_step_sets_bats_own_per_test_timeout(self):
        m = re.search(r'^          BATS_TEST_TIMEOUT: "?(\d+)"?$', self.head, re.M)
        self.assertTrue(m, "no BATS_TEST_TIMEOUT in the step's env: a hung test would eat the job's whole budget, nameless")
        secs = int(m.group(1))
        self.assertGreaterEqual(secs, 120, "below two minutes the slowest legitimate macOS test (the 60 s romp-serve probes) is at risk")
        self.assertLessEqual(secs, 600, "above ten minutes a hang still eats most of the Shell job's margin under its cap (55 "
                             "minutes on Linux and 60 on macOS; a flat 35 when this bound was set, and on main until fork PR "
                             "940 landed on 2026-10-04 with 50 and 60, the figures its branch had held since 2026-10-02, after "
                             "45 and 55 from 2026-09-30; fork PR 926, merging main after 940 landed, set the Linux figure to 55 "
                             "by the rule)")

    def test_the_step_still_runs_every_bats_file(self):
        self.assertIn("tests/*.bats", self.cmd)
        self.assertIn("--print-output-on-failure", self.cmd)


# The Linux cap's three inputs, each a literal, for T230b's rule (the pytest phase plus the per-test timeout plus the time
# before the step, rounded up to a multiple of 5 minutes; rule_minutes), held against ci.yml by PythonJobCeiling below.
# PLACEHOLDER: the one-worker pytest phase on the private runner's shape (2 CPUs, 8 GB) is not measured yet. None marks it
# unmeasured, and test_the_linux_cap_is_the_rules_figure_for_one_worker is red until the measured seconds replace it, here
# and in ci.yml's comment, with the cap set to rule_minutes of the three.
ONE_WORKER_PHASE_S = None
# the Run pytest step's --timeout, read back from its run line by test_the_per_test_timeout_input_is_the_steps
PER_TEST_TIMEOUT_S = 600
# the steps before Run pytest in the 3.14t cell of run 37158350467 (job 111306365110), on the public runner, the jobs
# API's figure; the private runner's is read from its first run
SETUP_S = 32
# The Linux figure ci.yml carries while ONE_WORKER_PHASE_S is unmeasured: an estimate, the slowest finished two-worker
# Linux cell's pytest step (2276 s, that same job) scaled by the serial ratio measured on four CPUs (1437 s against 739 s)
# to about 4426 s, then rule_minutes(4426, 600, 32), 85. Not a measurement; the placeholder test names it.
ESTIMATED_PHASE_S = 4426
PLACEHOLDER_LINUX_CAP = 85


def rule_minutes(phase_s, per_test_s, setup_s):
    """T230b's rule: the job cap in minutes is the pytest phase plus the per-test timeout plus the time before the step,
    in seconds, rounded up to a multiple of 5 minutes (300 s)."""
    total = phase_s + per_test_s + setup_s
    return 5 * ((total + 299) // 300)


class PythonJobCeiling(unittest.TestCase):
    """The python job's ceiling is per cell (2026-09-16): the macOS cells run the same suite on the image's slower
    runners, and the 3.10 cell was cancelled at the job's 25-minute ceiling after 25 min 27 s on one dispatch having
    completed in 24 min 43 s on the one before, so the release's combined proof could die on a minute's margin. Forty
    minutes then; sixty since 2026-09-24, when the release dispatch (run 35976250043) had the 3.13 macOS cell green in
    38 min 52 s and the 3.10 macOS cell cancelled at 40 min 20 s with no failure in its log, the same cells having taken
    33 to 35 minutes on the dispatch five hours before. The 3.10 cell reached 90 percent 36 min 40 s into its pytest
    step and the 3.13 cell's pytest step ended about 5.5 minutes after its own 90 percent, so the 3.10 suite sits near
    42 to 43 minutes; the rule (the suite plus the 600 s per-test timeout plus setup) gives 53 to 54, the floor is 54
    and the ceiling 60, so a revert to 40 goes red.
    Linux, by the same rule: 25 to 35 on 2026-09-24 (the 3.10 Linux cell took 19 min 34 s on run 35952964334); on fork PR
    926's branch, with two workers on the public runner, 40 on 2026-09-30 (run 36664031774's slowest pytest step 1572 s)
    and 50 on 2026-10-02 (the slowest finished two-worker cell, the 3.14t cell of run 37158350467, 2276 s in its pytest
    step and 32 s before it: 2908 s, about 48 min 28 s). Since 2026-10-04 the Linux cells run one worker each on the
    private runner (2 CPUs and 8 GB; tests/test_ci_pytest_workers.py), and the cap is the rule's figure for that shape,
    computed here from three literals: ONE_WORKER_PHASE_S, the one-worker phase as measured; PER_TEST_TIMEOUT_S, 600,
    read back from the Run pytest step's --timeout; and SETUP_S, the 32 s before the step. The pin is equality with
    rule_minutes of the three, so a cap above the rule's figure is red as well as one below it: past the figure a hung
    cell holds its run's verdict for nothing, and short of it a stall that begins late in the run is cancelled before the
    per-test timeout names it. While the phase is unmeasured (ONE_WORKER_PHASE_S None) the cap is PLACEHOLDER_LINUX_CAP,
    the estimate, and the equality test is red, naming the placeholder: a guessed figure cannot ship as a measured one."""
    def setUp(self):
        src = open(WF).read()
        m = re.search(r"^  python:\n((?:    .*\n|\n)+?)    strategy:\n", src, re.M)
        self.assertTrue(m, "the python job's head moved: re-anchor this pin")
        self.head = m.group(1)
        m = re.search(r"^    timeout-minutes: \$\{\{ matrix\.os == 'macos-latest' && (\d+) \|\| (\d+) \}\}$", self.head, re.M)
        self.assertTrue(m, "the python job's timeout-minutes is not the per-cell expression (macos-latest && N || M)")
        self.macos, self.linux = int(m.group(1)), int(m.group(2))
        self.src = src

    def test_macos_cells_get_sixty_minutes_and_do_not_revert_below_their_floor(self):
        self.assertGreaterEqual(self.macos, 54, "the macOS cells need the margin: on run 35976250043 (2026-09-24) the 3.13 cell "
                                "was green at 38 min 52 s and the 3.10 cell cancelled at 40 min 20 s by the 40-minute cap, at 90 "
                                "percent 36 min 40 s into its pytest step, so its suite sits near 42 to 43 minutes; that plus the "
                                "600 s per-test timeout plus setup is 53 to 54, so a cap below 54 cuts a green run")
        self.assertLessEqual(self.macos, 60, "past an hour a hung macOS cell eats the dispatch")

    def test_the_linux_cap_is_the_rules_figure_for_one_worker(self):
        if ONE_WORKER_PHASE_S is None:
            # the placeholder's own consistency first, so the red below is the placeholder's and nothing else's
            self.assertEqual(rule_minutes(ESTIMATED_PHASE_S, PER_TEST_TIMEOUT_S, SETUP_S), PLACEHOLDER_LINUX_CAP)
            self.assertEqual(self.linux, PLACEHOLDER_LINUX_CAP, "while the phase is unmeasured ci.yml carries the "
                             "placeholder, the estimate's figure, and no other number")
            self.assertIn("PLACEHOLDER", self.head, "the cap's comment names its figure a placeholder while it is one")
            self.fail("PLACEHOLDER: the one-worker pytest phase on the private runner's shape (2 CPUs, 8 GB) is not measured. "
                      "ci.yml's Linux cap is %d, where the placeholder figure is %d, rule_minutes(%d, %d, %d), an estimate "
                      "and not a measurement. Measure the phase, set ONE_WORKER_PHASE_S to its seconds, and set the cap and "
                      "ci.yml's comment to rule_minutes(ONE_WORKER_PHASE_S, %d, %d)"
                      % (self.linux, PLACEHOLDER_LINUX_CAP, ESTIMATED_PHASE_S, PER_TEST_TIMEOUT_S, SETUP_S,
                         PER_TEST_TIMEOUT_S, SETUP_S))
        want = rule_minutes(ONE_WORKER_PHASE_S, PER_TEST_TIMEOUT_S, SETUP_S)
        self.assertEqual(self.linux, want, "the Linux cap must be T230b's rule for one worker on the private runner: %d s of "
                         "pytest phase plus the %d s per-test timeout plus %d s before the step, rounded up to a multiple of 5 "
                         "minutes, is %d; ci.yml has %d" % (ONE_WORKER_PHASE_S, PER_TEST_TIMEOUT_S, SETUP_S, want, self.linux))
        for figure in (ONE_WORKER_PHASE_S, SETUP_S):
            self.assertIn("%d s" % figure, self.head, "the cap's comment states the input %d s" % figure)

    def test_the_per_test_timeout_input_is_the_steps(self):
        m = re.search(r"^  python:\n(?:    .*\n|\n)+?        run: python -m pytest .*--timeout=(\d+)", self.src, re.M)
        self.assertTrue(m, "the Run pytest line's --timeout moved: re-anchor this pin")
        self.assertEqual(int(m.group(1)), PER_TEST_TIMEOUT_S, "the rule's per-test input is the Run pytest step's --timeout")

    def test_the_rules_arithmetic(self):
        self.assertEqual(rule_minutes(2276, 600, 32), 50, "the two-worker figure the cap had: 2908 s, about 48 min 28 s, so 50")
        self.assertEqual(rule_minutes(1572, 600, 30), 40, "run 36664031774's figure: 2202 s, about 36 min 42 s, so 40")
        self.assertEqual(rule_minutes(3000 - 632, 600, 32), 50, "exactly 50 minutes stays 50")
        self.assertEqual(rule_minutes(3001 - 632, 600, 32), 55, "a second past 50 minutes is 55")


class ExtensionJobCeiling(unittest.TestCase):
    """The vscode-extension job ran the served labs until 2026-09-28, and they set its cap: PR 1790's run was cancelled at
    the job's 25-minute ceiling after 25 min 04 s mid lab on a slow runner, every step green up to the cut (2026-09-16), so
    forty minutes, the served step's twenty-odd minutes on a slow runner plus the 600 s per-test timeout plus setup. The
    labs now run in the served-pages job (tests/test_ci_served_job.py holds both jobs equal to literals, caps included).
    Without them the job took 4 min 45 s on main's run 36555049532 at 6dd80a6e7, and its cap is 17 minutes, sized in the
    job's comment in ci.yml for a head that rosters the legs open PRs are known to add, with a Browser legs bound of about
    that step's time and half again. The floor is that 17: a lower cap is sized again in the same change, and
    tools/ci-browser-legs.test.mjs derives the Browser legs step's margin from that step's record and this cap."""
    def test_the_extension_job_gets_seventeen_minutes(self):
        src = open(WF).read()
        m = re.search(r"^  vscode-extension:\n((?:    .*\n|\n)+?)    defaults:\n", src, re.M)
        self.assertTrue(m, "the extension job's head moved: re-anchor this pin")
        t = re.search(r"^    timeout-minutes: (\d+)$", m.group(1), re.M)
        self.assertTrue(t, "the extension job has no plain timeout-minutes line")
        self.assertGreaterEqual(int(t.group(1)), 17, "the cap is sized in the job's ci.yml comment from main's run "
                                "36555049532 and the legs open PRs are known to add, with a Browser legs bound of about "
                                "that step's time and half again: a lower cap is sized again in the same change")
        self.assertLessEqual(int(t.group(1)), 60, "past an hour a hung job eats the run")


if __name__ == "__main__":
    unittest.main()
