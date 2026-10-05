#!/usr/bin/env python3
"""The bats step of CI carries a per-test bound from bats itself (.github/workflows/ci.yml, 2026-09-16).

The macOS bats leg (a manual dispatch) was cancelled at the job's 35-minute ceiling on every run, nameless:
the job annotation says only that the maximum execution time was exceeded, and the TAP stream stops at the
last test that finished. BATS_TEST_TIMEOUT is bats-core's own bound (since 1.8, in the pinned 1.11.1 and in
Homebrew's 1.14.0 alike): a background sleep, then pkill or ps on the test's children, and the test's TAP
line ends "# timeout after Ns", so a hung test fails in minutes and is named. No coreutils timeout, which the
macOS image lacks. Source pins, as tests/test_ci_workflow_concurrency.py: no YAML library in the test deps."""
import ast
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "ci.yml")
CONFTEST = os.path.join(HERE, "conftest.py")


def shard_count_as_written(path=CONFTEST):
    """SHARD_COUNT as tests/conftest.py writes it, a whole-number literal at module level, read from the file's text and
    not imported: tests/test_bats_bare_negation.py imports this module, and the Shell job runs that module under a
    python with no pytest, which the conftest imports first. Raises LookupError unless there is one such assignment."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), path)
    found = [n.value.value for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "SHARD_COUNT"
             and isinstance(n.value, ast.Constant) and type(n.value.value) is int]
    if len(found) != 1:
        raise LookupError("tests/conftest.py has %d module-level SHARD_COUNT = <whole number> lines, not one: re-anchor "
                          "this pin" % len(found))
    return found[0]


SHARD_COUNT = shard_count_as_written()


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


# Each shard's cap (2026-10-04): ci.yml's Linux Python cells run as SHARD_COUNT (tests/conftest.py) one-worker jobs, one for
# each shard of the test files, since one worker running the whole suite does not fit the private runner's 8 GB (a local
# run of the Run pytest step's command on 2026-10-04, under a CPUQuota of 200 percent and an 8 GiB memory cap with no
# swap, had its one worker killed by the memory cap once on 3.12 and twice on 3.14t). Each shard's cap is T230b's rule
# (the pytest phase plus the per-test timeout plus the time before the step, rounded up to a multiple of 5 minutes;
# rule_minutes) for that shard's one-worker phase, held against ci.yml by PythonJobCeiling below.
# Each entry is the shard's one-worker pytest phase in seconds, measured on 2026-10-05 under the private runner's shape
# (a CPUQuota of 200 percent, an 8 GiB memory cap, no swap; ci.yml's python job comment has the run), the slower of
# 3.12 and 3.14t, read from pytest's summary line and rounded up: 3.14t's for each shard (3.12's were 661, 930 and
# 2348). None marks a shard whose phase is not measured (a shard SHARD_COUNT adds), and
# test_each_shards_cap_is_the_rules_figure_for_its_phase is red while any shard's phase is None. Each cap is confirmed
# on the new repo's first CI run.
SHARD_PHASE_S = {1: 678, 2: 981, 3: 2459}
# what ci.yml's cap for a shard holds while that shard's phase is a placeholder, and each shard held until the shards
# were measured: the cap the whole suite's estimated
# one-worker phase gave (WHOLE_SUITE_ESTIMATE_INPUTS: the slowest finished two-worker Linux cell, the 3.10 cell of run
# 37208049133, job 111453304880, 2312 s in its pytest step, scaled by the serial ratio measured on four CPUs, 1437 s against
# 739 s, to 4496 s; 4496 + 600 + 25 = 5121 s, so 90), which a shard, a part of that suite, is held under until measured
WHOLE_SUITE_ESTIMATE_INPUTS = (2312, 1437, 739)
WHOLE_SUITE_PHASE_S = 4496
PLACEHOLDER_CAP = 90
PLACEHOLDER_MARK = "PLACEHOLDER: no shard's phase is measured yet"
# the Run pytest step's --timeout, read back from its run line by test_the_per_test_timeout_input_is_the_steps
PER_TEST_TIMEOUT_S = 600
# the steps before Run pytest in the 3.14t cell of run 37212676524 (batch/2026-10-04b, job 111476102341), the slower
# interpreter's cell, on the public runner, the jobs API's figure; the private runner's is read from its first run
SETUP_S = 27
# the steps before Run pytest in the 3.10 cell of run 37208049133 (job 111453304880), the setup the whole suite's
# estimate used
WHOLE_SUITE_SETUP_S = 25


def rule_minutes(phase_s, per_test_s, setup_s):
    """T230b's rule: the job cap in minutes is the pytest phase plus the per-test timeout plus the time before the step,
    in seconds, rounded up to a multiple of 5 minutes (300 s)."""
    total = phase_s + per_test_s + setup_s
    return 5 * ((total + 299) // 300)


# the python job's cap expression: macOS's figure, then one `matrix.shard == '<k>' && <minutes> ||` clause for each shard
# but the last, then the last shard's figure
CAP_LINE = re.compile(r"^    timeout-minutes: \$\{\{ matrix\.os == 'macos-latest' && (\d+) \|\| "
                      r"((?:matrix\.shard == '\d+' && \d+ \|\| )*)(\d+) \}\}$", re.M)


def shard_caps(head, count):
    """(macOS's cap, {shard: cap}) from the python job's head, the shards read from the expression's clauses in order and
    the last figure given to shard `count`. Raises LookupError when the line is not that expression or its clauses do
    not name shards 1 to count - 1 in order."""
    m = CAP_LINE.search(head)
    if m is None:
        raise LookupError("the python job's timeout-minutes is not the per-shard expression (macos-latest && N || "
                          "matrix.shard == '1' && M || ... || L): re-anchor this pin")
    clauses = [(int(k), int(v)) for k, v in re.findall(r"matrix\.shard == '(\d+)' && (\d+) \|\| ", m.group(2))]
    if [k for k, _v in clauses] != list(range(1, count)):
        raise LookupError("the cap expression's shard clauses name shards %r, not 1 to %d in order, before the last "
                          "shard's figure" % ([k for k, _v in clauses], count - 1))
    caps = dict(clauses)
    caps[count] = int(m.group(3))
    return int(m.group(1)), caps


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
    step and 32 s before it: 2908 s, about 48 min 28 s). From 2026-10-04 the Linux cells ran one worker each on the
    private runner (2 CPUs and 8 GB; tests/test_ci_pytest_workers.py) under a cap of 90, the rule's figure for the whole
    suite's estimated one-worker phase, until a local run found that one worker does not fit 8 GB; since then each Linux
    interpreter runs as SHARD_COUNT (tests/conftest.py) one-worker jobs, one per shard, and each shard has its own cap in
    the expression, the rule's figure for that shard's phase: SHARD_PHASE_S[k], PER_TEST_TIMEOUT_S (600, read back from
    the Run pytest step's --timeout) and SETUP_S. The pin is equality with rule_minutes of the three, so a cap above the
    rule's figure is red as well as one below it: past the figure a hung cell holds its run's verdict for nothing, and
    short of it a stall that begins late in the run is cancelled before the per-test timeout names it. While a shard's
    phase is a placeholder (None), its cap must be PLACEHOLDER_CAP, ci.yml's comment must carry PLACEHOLDER_MARK, and
    the rule case is red, so a placeholder cannot ship as a measured figure."""
    def setUp(self):
        self.count = SHARD_COUNT
        src = open(WF).read()
        m = re.search(r"^  python:\n((?:    .*\n|\n)+?)    strategy:\n", src, re.M)
        self.assertTrue(m, "the python job's head moved: re-anchor this pin")
        self.head = m.group(1)
        self.macos, self.caps = shard_caps(self.head, self.count)
        self.joined = " ".join(l.strip()[1:].strip() for l in self.head.splitlines() if l.strip().startswith("#"))
        self.src = src

    def test_macos_cells_get_sixty_minutes_and_do_not_revert_below_their_floor(self):
        self.assertGreaterEqual(self.macos, 54, "the macOS cells need the margin: on run 35976250043 (2026-09-24) the 3.13 cell "
                                "was green at 38 min 52 s and the 3.10 cell cancelled at 40 min 20 s by the 40-minute cap, at 90 "
                                "percent 36 min 40 s into its pytest step, so its suite sits near 42 to 43 minutes; that plus the "
                                "600 s per-test timeout plus setup is 53 to 54, so a cap below 54 cuts a green run")
        self.assertLessEqual(self.macos, 60, "past an hour a hung macOS cell eats the dispatch")

    def test_every_shard_has_a_cap_and_a_phase_entry(self):
        self.assertEqual(sorted(self.caps), list(range(1, self.count + 1)), "a cap for each shard, 1 to SHARD_COUNT")
        self.assertEqual(sorted(SHARD_PHASE_S), list(range(1, self.count + 1)), "a phase entry for each shard, 1 to SHARD_COUNT")

    def test_a_placeholder_cap_is_named_one(self):
        for k, phase in sorted(SHARD_PHASE_S.items()):
            if phase is None:
                with self.subTest(shard=k):
                    self.assertEqual(self.caps[k], PLACEHOLDER_CAP, "shard %d's phase is a placeholder, so its cap is the "
                                     "placeholder figure %d" % (k, PLACEHOLDER_CAP))
                    self.assertIn(PLACEHOLDER_MARK, self.joined, "while a shard's phase is a placeholder the cap's comment "
                                  "says so")
        if all(phase is not None for phase in SHARD_PHASE_S.values()):
            self.assertNotIn(PLACEHOLDER_MARK, self.joined, "every shard's phase is measured: the cap's comment no longer "
                             "calls them placeholders")

    def test_each_shards_cap_is_the_rules_figure_for_its_phase(self):
        for k in range(1, self.count + 1):
            with self.subTest(shard=k):
                phase = SHARD_PHASE_S.get(k)
                self.assertIsNotNone(phase, "PLACEHOLDER: shard %d's one-worker pytest phase on the private runner's shape (2 "
                                     "CPUs, 8 GB) is not measured. ci.yml's cap for it is %d, the placeholder figure, not a "
                                     "measurement. Measure the phase, set SHARD_PHASE_S[%d] to its seconds, and set the cap "
                                     "and ci.yml's comment to rule_minutes(SHARD_PHASE_S[%d], %d, %d)"
                                     % (k, self.caps[k], k, k, PER_TEST_TIMEOUT_S, SETUP_S))
                want = rule_minutes(phase, PER_TEST_TIMEOUT_S, SETUP_S)
                self.assertEqual(self.caps[k], want, "shard %d's cap must be T230b's rule for its one-worker phase: %d s plus "
                                 "the %d s per-test timeout plus %d s before the step, rounded up to a multiple of 5 minutes, "
                                 "is %d; ci.yml has %d" % (k, phase, PER_TEST_TIMEOUT_S, SETUP_S, want, self.caps[k]))
                self.assertIn("%d s" % phase, self.head, "the cap's comment states shard %d's phase, %d s" % (k, phase))

    def test_the_placeholder_figure_is_the_whole_suites_estimate_and_its_comment_states_it(self):
        cell_s, serial_s, two_worker_s = WHOLE_SUITE_ESTIMATE_INPUTS
        self.assertEqual(WHOLE_SUITE_PHASE_S, round(cell_s * serial_s / two_worker_s), "the whole suite's estimate is the "
                         "slowest finished two-worker cell's phase scaled by the serial ratio, rounded to the second")
        self.assertEqual(PLACEHOLDER_CAP, rule_minutes(WHOLE_SUITE_PHASE_S, PER_TEST_TIMEOUT_S, WHOLE_SUITE_SETUP_S))
        for figure in WHOLE_SUITE_ESTIMATE_INPUTS + (WHOLE_SUITE_PHASE_S, WHOLE_SUITE_SETUP_S):
            self.assertIn("%d s" % figure, self.joined, "the cap's comment states the estimate's input %d s" % figure)
        self.assertIn("8 GB does not hold one worker of this suite", self.joined, "the cap's comment keeps the record that "
                      "one worker running the whole suite does not fit the private runner")

    def test_the_per_test_timeout_input_is_the_steps(self):
        m = re.search(r"^  python:\n(?:    .*\n|\n)+?        run: python -m pytest .*--timeout=(\d+)", self.src, re.M)
        self.assertTrue(m, "the Run pytest line's --timeout moved: re-anchor this pin")
        self.assertEqual(int(m.group(1)), PER_TEST_TIMEOUT_S, "the rule's per-test input is the Run pytest step's --timeout")

    def test_the_rules_arithmetic(self):
        self.assertEqual(rule_minutes(2276, 600, 32), 50, "the two-worker figure the cap had: 2908 s, about 48 min 28 s, so 50")
        self.assertEqual(rule_minutes(1572, 600, 30), 40, "run 36664031774's figure: 2202 s, about 36 min 42 s, so 40")
        self.assertEqual(rule_minutes(4426, 600, 32), 85, "the estimate the cap carried while the build awaited a measurement: "
                         "5058 s, about 84 min 18 s, so 85")
        self.assertEqual(rule_minutes(4496, 600, 25), 90, "the whole suite's one-worker estimate: 5121 s, about 85 min 21 s, "
                         "so 90, the placeholder each shard's cap held until the shards were measured")
        self.assertEqual([rule_minutes(p, 600, 27) for p in (678, 981, 2459)], [25, 30, 55], "each shard's measured "
                         "figure: 1305 s, 1608 s and 3086 s, so 25, 30 and 55")
        self.assertEqual(rule_minutes(3000 - 632, 600, 32), 50, "exactly 50 minutes stays 50")
        self.assertEqual(rule_minutes(3001 - 632, 600, 32), 55, "a second past 50 minutes is 55")


class ShardCapsReader(unittest.TestCase):
    """shard_caps over synthetic cap lines: each shard's literal read, and a line that drops or reorders a shard refused."""

    def test_each_shards_figure_is_read(self):
        head = "    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || matrix.shard == '1' && 45 || 50 }}\n"
        self.assertEqual(shard_caps(head, 2), (60, {1: 45, 2: 50}))
        head3 = ("    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || matrix.shard == '1' && 40 || "
                 "matrix.shard == '2' && 35 || 30 }}\n")
        self.assertEqual(shard_caps(head3, 3), (60, {1: 40, 2: 35, 3: 30}))

    def test_a_line_without_the_shard_clauses_is_refused(self):
        with self.assertRaises(LookupError):
            shard_caps("    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || 90 }}\n", 2)
        with self.assertRaises(LookupError):
            shard_caps("    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || matrix.shard == '2' && 45 || 50 }}\n", 2)


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
