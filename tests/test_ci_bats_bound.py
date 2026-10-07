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


# Each shard's cap (2026-10-04; its rule 2026-10-05): ci.yml's Linux Python cells run as SHARD_COUNT (tests/conftest.py)
# one-worker jobs, one for each shard of the test files, since one worker running the whole suite does not fit the private
# runner's 8 GB (a local run of the Run pytest step's command on 2026-10-04, under a CPUQuota of 200 percent and an 8 GiB
# memory cap with no swap, had its one worker killed by the memory cap once on 3.12 and twice on 3.14t). Each shard's cap
# is ruled_cap's figure for the shard's governing phase (governing_phase, below), held against ci.yml by PythonJobCeiling
# below: T230b's rule (the pytest phase plus the per-test timeout plus the time before the step, rounded up to a multiple
# of 5 minutes; rule_minutes), then 5 minutes more when that leaves less than MARGIN_FLOOR_S between the sum and the cap.
# The governing phase is the largest of every measured run of the shard and of each run's projections (below). Both were
# decided on 2026-10-05: each cap comes from its shard's slowest measured run, and a margin under a minute is far inside
# the run-to-run variation measured (shard 2's two 3.12 runs over the same files differ by 21 percent); a higher cap costs
# nothing on a normal run and about 5 billed minutes on a wedged one, where a timeout shows as a cancelled, red job and
# costs a rerun.
# MEASURED_RUNS holds every measured run of the shards at SHARD_COUNT, by round and interpreter: each the shard's
# one-worker pytest phase in seconds under the private runner's shape (a CPUQuota of 200 percent, an 8 GiB memory cap,
# no swap; ci.yml's python job comment has the runs), read from pytest's summary line and rounded up to the second.
# None marks a shard whose phase is not measured (a shard SHARD_COUNT adds), and
# test_each_shards_cap_is_the_ruled_figure_for_its_slowest_run is red while any entry is None. The earlier counts'
# phases (two and three shards) are a record in ci.yml's comment, not entries here: a file's shard moved with the count.
# A new measurement is a new round here, with ci.yml's figures and comment set to match.
# The interpreters of the matrix not measured locally (UNMEASURED; with MEASURED, every interpreter of the matrix, which
# test_every_interpreter_of_the_matrix_is_measured_or_projected holds) each have a projected phase for each shard in each
# round (projected_phase): the round's 3.12 phase times that shard's ratio of the interpreter to 3.12 in run
# UNMEASURED_RATIO_RUN (UNMEASURED_RATIO_STEP_S, one ratio for each shard and interpreter), rounded up to the second. A
# projection, not a measurement. Each cap is re-derived from the first run on the private repository's 2-CPU runners;
# the fork's public runners have more CPUs, so their times are not that measurement.
HASH_ALONE = "hash-alone"
WEIGHTED = "weighted"
MERGED_MAIN = "merged-main"
# the run of four shards by the hash alone (2026-10-05; logs measure4-shard<k>-312-c.log and measure4-shard<k>-314t-c.log)
SHARD_PHASE_312_HASH_ALONE_S = {1: 553, 2: 1482, 3: 661, 4: 1145}
SHARD_PHASE_314T_HASH_ALONE_S = {1: 559, 2: 1438, 3: 466, 4: 1222}
# the run of four shards at the weighted rule, the rule CI runs (2026-10-05; logs measure4-shard<k>-312-w.log and
# measure4-shard<k>-314t-w.log); tests/test_ci_cost_estimate.py bills these phases
SHARD_PHASE_312_WEIGHTED_S = {1: 529, 2: 1220, 3: 614, 4: 1237}
SHARD_PHASE_314T_WEIGHTED_S = {1: 679, 2: 1451, 3: 409, 4: 1204}
# the run of four shards at the weighted rule after main was merged into this branch, over the files CI runs (shard 2 on
# 2026-10-05, shards 1, 3 and 4 on 2026-10-06; logs measure5-shard<k>-312-m.log and measure5-shard<k>-314t-m.log)
SHARD_PHASE_312_MERGED_MAIN_S = {1: 519, 2: 1293, 3: 554, 4: 1066}
SHARD_PHASE_314T_MERGED_MAIN_S = {1: 543, 2: 1361, 3: 466, 4: 1143}
# {round: {interpreter: {shard: seconds}}}, the rounds in the order they ran
MEASURED_RUNS = {
    HASH_ALONE: {"3.12": SHARD_PHASE_312_HASH_ALONE_S, "3.14t": SHARD_PHASE_314T_HASH_ALONE_S},
    WEIGHTED: {"3.12": SHARD_PHASE_312_WEIGHTED_S, "3.14t": SHARD_PHASE_314T_WEIGHTED_S},
    MERGED_MAIN: {"3.12": SHARD_PHASE_312_MERGED_MAIN_S, "3.14t": SHARD_PHASE_314T_MERGED_MAIN_S},
}
# each round's logs (<k> the shard, <py> 312 or 314t), and its name in ci.yml's cap comment
ROUND_LOG = {HASH_ALONE: "measure4-shard<k>-<py>-c.log", WEIGHTED: "measure4-shard<k>-<py>-w.log",
             MERGED_MAIN: "measure5-shard<k>-<py>-m.log"}
ROUND_NAME = {HASH_ALONE: "the hash-alone run", WEIGHTED: "the weighted run", MERGED_MAIN: "the merged-main run"}
# the round whose files are the ones CI runs, the last: ci.yml's comment says what that round alone would give the caps
CURRENT_ROUND = MERGED_MAIN
# the shards whose files the hash-alone round assigned by another rule than CI's, each with that round:
# tests/test_thread_stop_census.py ran in shard 4 by the hash alone and runs in shard 1 at the weighted rule (on 3.12, shard
# 1 ran 4761 tests and then 4837, and shard 4 ran 5189 and then 5113). Shard 2 ran the same 5318 tests in those two rounds;
# shard 3 ran the same files, and 3 more tests in the weighted round, which tests/test_ci_shards.py, a shard 3 file, added
# between the two. The merged-main round shards the files by the weighted round's rule, and every shard of it also ran the
# test files main's merge added and changed (ci.yml's comment gives the counts).
OTHER_COMPOSITION = {1: HASH_ALONE, 4: HASH_ALONE}
# the module whose move made that difference, and its shard in each round
MOVED_MODULE = ("tests/test_thread_stop_census.py", {HASH_ALONE: 4, WEIGHTED: 1, MERGED_MAIN: 1})
# the cap comment's word for how many rounds there are, by their count
ROUND_COUNT_WORD = {2: "both", 3: "the three"}
ALL_ROUNDS_WORD = {2: "both", 3: "all three"}
MEASURED = ("3.12", "3.14t")
# the Run pytest step's seconds in each Linux shard job of run 37415499848 (a dispatch of this branch on 2026-10-06, one
# worker a job on the public runner; the jobs API's step start to step end), {shard: {interpreter: seconds}}: each
# unmeasured interpreter's ratio to 3.12 on each shard. Each shard takes its own ratio (the review's first round,
# 2026-10-06), since the ratio varies by shard: shard 2's 3.10 ratio is 1883/1204, about 1.56, where the whole suite's,
# the one ratio the caps took until then (SUITE_RATIO_STEP_S), is 1639/1248, about 1.31.
UNMEASURED_RATIO_RUN = 37415499848
UNMEASURED_RATIO_STEP_S = {
    1: {"3.10": 523, "3.11": 580, "3.12": 581, "3.13": 556},
    2: {"3.10": 1883, "3.11": 1219, "3.12": 1204, "3.13": 1417},
    3: {"3.10": 633, "3.11": 560, "3.12": 663, "3.13": 572},
    4: {"3.10": 1146, "3.11": 890, "3.12": 1104, "3.13": 1067},
}
UNMEASURED = ("3.10", "3.11", "3.13")
# a record: the Run pytest step's seconds in each Linux cell of run 37212676524 (batch/2026-10-04b, two workers on the
# public runner; the jobs API), the one ratio for the whole suite each shard's projection took until 2026-10-06, and the
# caps it gave; ci.yml's cap comment states both, and test_the_cap_comment_records_the_caps_the_suite_wide_ratio_gave holds
# them to the rule
SUITE_RATIO_RUN = 37212676524
SUITE_RATIO_STEP_S = {"3.10": 1639, "3.11": 1554, "3.12": 1248, "3.13": 1422}
# the longest and shortest time before the Run pytest step in run UNMEASURED_RATIO_RUN's twenty Linux shard jobs (the jobs
# API's job start to the step's start; the longest in the 3.14t shard 2 job, 112113103527): the caps take SETUP_S, from
# CELL_EDGE_RUN, and the cap comment says the longest of these changes no cap, and names the lowest time in this range
# at which every cap is the same and the figure below it, which
# test_the_time_before_the_step_is_the_longest_cells_and_the_comment_names_it derives
RATIO_RUN_BEFORE_S = (16, 33)
# the margin rule (2026-10-05): a cap that T230b's rule leaves less than this many seconds above the sum goes up 5 minutes
MARGIN_FLOOR_S = 60
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
# each Linux cell's seconds before and after its Run pytest step in run CELL_EDGE_RUN (batch/2026-10-04b, on the public
# runner; the jobs API's job start to the step's start, and the step's end to the job's end), and each cell's job id in
# that run. tests/test_ci_cost_estimate.py charges every shard job of an interpreter its cell's two figures beside its
# phase, and reads them from here.
CELL_EDGE_RUN = 37212676524
CELL_EDGE_S = {"3.10": (25, 2), "3.11": (18, 3), "3.12": (18, 2), "3.13": (19, 3), "3.14t": (27, 3)}
CELL_JOB = {"3.10": 111476090366, "3.11": 111476091642, "3.12": 111476073561, "3.13": 111476073413, "3.14t": 111476102341}
# the time before the step the caps take: the longest of CELL_EDGE_S's, and its cell; the private runner's is read from
# its first run
SETUP_CELL = max(CELL_EDGE_S, key=lambda py: CELL_EDGE_S[py][0])
SETUP_S = CELL_EDGE_S[SETUP_CELL][0]
# the steps before Run pytest in the 3.10 cell of run 37208049133 (job 111453304880), the setup the whole suite's
# estimate used
WHOLE_SUITE_SETUP_S = 25


def rule_minutes(phase_s, per_test_s, setup_s):
    """T230b's rule: the job cap in minutes is the pytest phase plus the per-test timeout plus the time before the step,
    in seconds, rounded up to a multiple of 5 minutes (300 s)."""
    total = phase_s + per_test_s + setup_s
    return 5 * ((total + 299) // 300)


def ruled_cap(phase_s, per_test_s, setup_s, floor_s=MARGIN_FLOOR_S):
    """(cap, rule, margin) for a pytest phase in seconds: rule is T230b's rule's figure (rule_minutes), margin the seconds
    between that figure and the sum it rounds up (phase plus per-test timeout plus the time before the step), and cap the
    figure, or 5 minutes more when the margin is under floor_s (the margin rule, 2026-10-05). Once raised the margin is at
    least 300 s, past any floor under 5 minutes, so the rule raises once."""
    total = phase_s + per_test_s + setup_s
    rule = rule_minutes(phase_s, per_test_s, setup_s)
    margin = rule * 60 - total
    return (rule + 5 if margin < floor_s else rule), rule, margin


def projected_phase(k, py, base, steps=None):
    """Shard k's projected one-worker phase on the unmeasured interpreter py, in seconds: the shard's 3.12 phase in one
    round (base, {shard: seconds}) times shard k's Run pytest seconds on py over its seconds on 3.12 in run
    UNMEASURED_RATIO_RUN (steps, {shard: {interpreter: seconds}}, UNMEASURED_RATIO_STEP_S by default), rounded up to the
    second. Each shard by its own ratio, never another shard's. A projection, not a measurement. Raises LookupError when
    the shard's 3.12 phase, the shard's step times or either of its step times is missing."""
    steps = UNMEASURED_RATIO_STEP_S if steps is None else steps
    if base is None or base.get(k) is None:
        raise LookupError("shard %d has no 3.12 phase to project %s's from" % (k, py))
    by_py = steps.get(k)
    if by_py is None:
        raise LookupError("no Run pytest seconds for shard %d in run %d, so no ratio to project its %s phase by"
                          % (k, UNMEASURED_RATIO_RUN, py))
    for name in (py, "3.12"):
        if by_py.get(name) is None:
            raise LookupError("no Run pytest seconds for shard %d on %s in run %d, so no ratio to project its %s phase by"
                              % (k, name, UNMEASURED_RATIO_RUN, py))
    return -(-base[k] * by_py[py] // by_py["3.12"])


def ratio_record(k, steps=None):
    """The cap comment's record of shard k's step times in run UNMEASURED_RATIO_RUN and its ratios: "shard k, <s> s on
    3.10, ..., <s> s on 3.13, ratios to 3.12 of <r>, <r> and <r>", the interpreters in version order, each ratio of
    UNMEASURED's to two decimals in UNMEASURED's order."""
    by_py = (UNMEASURED_RATIO_STEP_S if steps is None else steps)[k]
    times = english(["%d s on %s" % (by_py[py], py) for py in sorted(UNMEASURED + ("3.12",))])
    ratios = english(["%.2f" % (by_py[py] / by_py["3.12"]) for py in UNMEASURED])
    return "shard %d, %s, ratios to 3.12 of %s" % (k, times, ratios)


def governing_phase(k, runs=None, unmeasured=None, steps=None):
    """(seconds, round, interpreter) of the phase shard k's cap is ruled_cap's figure for: the largest of every measured
    run of the shard (runs, MEASURED_RUNS by default, {round: {interpreter: {shard: seconds}}}) and, in every round, the
    projected_phase of that round's 3.12 phase on each interpreter of unmeasured (UNMEASURED by default). interpreter is
    the measured one for a measured run and the projected one for a projection. Every measured run is read before any
    projection, so a projection must pass each measured run to govern; within each kind the rounds go in runs' order and
    the interpreters in theirs, and on a tie the first governs. Raises LookupError when runs is empty, a round has no
    interpreter, any round lacks shard k's phase on any of its interpreters, or a projection's data is missing."""
    runs = MEASURED_RUNS if runs is None else runs
    unmeasured = UNMEASURED if unmeasured is None else unmeasured
    if not runs:
        raise LookupError("no measured run to take shard %d's phase from" % k)
    best = None
    for rnd, by_py in runs.items():
        if not by_py:
            raise LookupError("the %s round has no measured interpreter" % rnd)
        for py, phases in by_py.items():
            if phases.get(k) is None:
                raise LookupError("shard %d's phase on %s in the %s round is missing or a placeholder" % (k, py, rnd))
            if best is None or phases[k] > best[0]:
                best = (phases[k], rnd, py)
    for rnd, by_py in runs.items():
        for py in unmeasured:
            p = projected_phase(k, py, by_py.get("3.12"), steps)
            if p > best[0]:
                best = (p, rnd, py)
    return best


def cap_clause(k, runs=None, unmeasured=None, steps=None):
    """The cap comment's clause for shard k: the run that governs (a measured run, or an unmeasured interpreter's
    projection of a round's 3.12 phase with its arithmetic), the sum, the rule's figure, the margin under it and, when the
    margin rule raises it, the cap. The rounds are named by ROUND_NAME."""
    runs = MEASURED_RUNS if runs is None else runs
    steps_s = UNMEASURED_RATIO_STEP_S if steps is None else steps
    gov, rnd, py = governing_phase(k, runs, unmeasured, steps)
    cap, rule, margin = ruled_cap(gov, PER_TEST_TIMEOUT_S, SETUP_S)
    if py in runs[rnd]:
        head = "shard %d, measured, %s's %d s on %s" % (k, ROUND_NAME[rnd], gov, py)
    else:
        head = "shard %d, %s projected from %s's %d s on 3.12, times %d/%d is %d s" % (
            k, py, ROUND_NAME[rnd], runs[rnd]["3.12"][k], steps_s[k][py], steps_s[k]["3.12"], gov)
    if cap == rule:
        tail = ", a margin of %d s" % margin
    else:
        tail = " by the rule, a margin of %d s, under %d s, so %d" % (margin, MARGIN_FLOOR_S, cap)
    return "%s, and %d + %d + %d = %d s, so %d%s" % (head, gov, PER_TEST_TIMEOUT_S, SETUP_S,
                                                    gov + PER_TEST_TIMEOUT_S + SETUP_S, rule, tail)


def english(items):
    """'a', 'a and b', or 'a, b and c': items listed as the cap comment lists them."""
    items = [str(i) for i in items]
    return items[0] if len(items) == 1 else "%s and %s" % (", ".join(items[:-1]), items[-1])


def governing_summary(count, runs=None, unmeasured=None, steps=None):
    """The cap comment's sentence on what governs each shard: for each kind of governing phase (governing_phase), a
    measured run or one unmeasured interpreter's projection, the shards it governs, the kinds in the order of the first
    shard each governs: "a measured run governs shards 1 and 3, and 3.10's projection governs shards 2 and 4"."""
    groups = {}
    for k in range(1, count + 1):
        _gov, _rnd, py = governing_phase(k, runs, unmeasured, steps)
        groups.setdefault("a measured run" if py in MEASURED else "%s's projection" % py, []).append(k)
    parts = ["%s governs %s" % (kind, "shard %d" % ks[0] if len(ks) == 1 else "shards %s" % english(ks))
             for kind, ks in groups.items()]
    return parts[0] if len(parts) == 1 else "%s, and %s" % (", ".join(parts[:-1]), parts[-1])


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
    the expression: ruled_cap of governing_phase(k), the slowest of every measured run of the shard in MEASURED_RUNS and
    of each unmeasured interpreter's projection of each round's 3.12 phase, with PER_TEST_TIMEOUT_S (600, read back from
    the Run pytest step's --timeout) and SETUP_S; that is T230b's rule's figure, raised 5 minutes when it leaves less than
    MARGIN_FLOOR_S under the cap (both decided 2026-10-05, when the slowest runs and the margin rule took shard 2 from 40
    to 45 and shard 3 from 25 to 30). Since 2026-10-06 each shard's projections take that shard's own ratio of each
    unmeasured interpreter to 3.12 (UNMEASURED_RATIO_STEP_S, run 37415499848), where they took one ratio for the whole
    suite (SUITE_RATIO_STEP_S, run 37212676524); that took shard 2 from 45 to 55, shard 3 from 30 to 25 and shard 4 from
    40 to 35. The pin is equality, so a cap above the ruled figure is red as well as one below
    it: past the figure a hung cell holds its run's verdict for nothing, and short of it a stall that begins late in the
    run on the slowest interpreter is cancelled before the per-test timeout names it. While a shard's phase is a
    placeholder (None in any round), its cap must be PLACEHOLDER_CAP, ci.yml's comment must carry PLACEHOLDER_MARK, and
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
        job = re.search(r"^  python:\n((?:(?:    .*)?\n)+?)(?=  \S)", src, re.M)
        self.assertTrue(job, "the python job's end moved: re-anchor this pin")
        self.job = job.group(1)

    def test_macos_cells_get_sixty_minutes_and_do_not_revert_below_their_floor(self):
        self.assertGreaterEqual(self.macos, 54, "the macOS cells need the margin: on run 35976250043 (2026-09-24) the 3.13 cell "
                                "was green at 38 min 52 s and the 3.10 cell cancelled at 40 min 20 s by the 40-minute cap, at 90 "
                                "percent 36 min 40 s into its pytest step, so its suite sits near 42 to 43 minutes; that plus the "
                                "600 s per-test timeout plus setup is 53 to 54, so a cap below 54 cuts a green run")
        self.assertLessEqual(self.macos, 60, "past an hour a hung macOS cell eats the dispatch")

    def test_every_shard_has_a_cap_and_a_phase_in_every_run(self):
        self.assertEqual(sorted(self.caps), list(range(1, self.count + 1)), "a cap for each shard, 1 to SHARD_COUNT")
        self.assertTrue(MEASURED_RUNS, "no measured run: each shard's cap comes from its measured runs")
        self.assertEqual(sorted(ROUND_LOG), sorted(MEASURED_RUNS), "a log for each round")
        self.assertEqual(sorted(ROUND_NAME), sorted(MEASURED_RUNS), "a name in the cap comment for each round")
        for rnd, by_py in MEASURED_RUNS.items():
            with self.subTest(round=rnd):
                self.assertEqual(sorted(by_py), sorted(MEASURED), "the %s round has phases on each measured interpreter"
                                 % rnd)
                for py, phases in sorted(by_py.items()):
                    self.assertEqual(sorted(phases), list(range(1, self.count + 1)), "the %s round's %s phases name each "
                                     "shard, 1 to SHARD_COUNT" % (rnd, py))

    def test_a_placeholder_cap_is_named_one(self):
        placeholders = sorted({k for by_py in MEASURED_RUNS.values() for phases in by_py.values()
                               for k, phase in phases.items() if phase is None})
        for k in placeholders:
            with self.subTest(shard=k):
                self.assertEqual(self.caps[k], PLACEHOLDER_CAP, "shard %d's phase is a placeholder, so its cap is the "
                                 "placeholder figure %d" % (k, PLACEHOLDER_CAP))
                self.assertIn(PLACEHOLDER_MARK, self.joined, "while a shard's phase is a placeholder the cap's comment "
                              "says so")
        if not placeholders:
            self.assertNotIn(PLACEHOLDER_MARK, self.joined, "every shard's phase is measured: the cap's comment no longer "
                             "calls them placeholders")

    def test_each_shards_cap_is_the_ruled_figure_for_its_slowest_run(self):
        # the candidates are built here from MEASURED_RUNS directly, not through governing_phase, and counted, so a
        # governing_phase that skipped the run or projection that governs on MEASURED_RUNS is red, and so is an empty
        # population. A skip of an input that does not govern on this data is not red here: on this data a measured
        # run governs shards 1 and 3 and 3.10's projection shards 2 and 4 (ci.yml's cap comment; the summary case below
        # holds the sentence), so 3.11's and 3.13's projections govern no shard. GoverningPhase holds those skips over
        # synthetic data, and that each shard projects by its own ratio.
        self.assertTrue(MEASURED_RUNS, "no measured run: each shard's cap comes from its measured runs")
        self.assertEqual(sorted(UNMEASURED_RATIO_STEP_S), list(range(1, self.count + 1)), "Run pytest seconds in run %d "
                         "for each shard, 1 to SHARD_COUNT: each shard's projections take its own ratio"
                         % UNMEASURED_RATIO_RUN)
        for k in range(1, self.count + 1):
            for py in UNMEASURED + ("3.12",):
                self.assertIsNotNone(UNMEASURED_RATIO_STEP_S[k].get(py), "no Run pytest seconds for shard %d on %s in run "
                                     "%d: an unmeasured interpreter's projection of a shard needs that shard's ratio to "
                                     "3.12" % (k, py, UNMEASURED_RATIO_RUN))
        for k in range(1, self.count + 1):
            with self.subTest(shard=k):
                runs = [(rnd, py, phases.get(k)) for rnd, by_py in MEASURED_RUNS.items() for py, phases in by_py.items()]
                for rnd, py, phase in runs:
                    self.assertIsNotNone(phase, "PLACEHOLDER: shard %d's one-worker pytest phase on %s in the %s round, "
                                         "under the private runner's shape (2 CPUs, 8 GB), is not measured. ci.yml's cap "
                                         "for it is %d, the placeholder figure, not a measurement. Measure the phase, set "
                                         "MEASURED_RUNS[%r][%r][%d] to its seconds, and set the cap and ci.yml's comment "
                                         "to ruled_cap(governing_phase(%d)[0], %d, %d)[0]"
                                         % (k, py, rnd, self.caps[k], rnd, py, k, k, PER_TEST_TIMEOUT_S, SETUP_S))
                    self.assertIsNotNone(MEASURED_RUNS[rnd].get("3.12"), "the %s round has no 3.12 phases, the base each "
                                         "unmeasured interpreter's projection of it scales" % rnd)
                candidates = [phase for _rnd, _py, phase in runs]
                candidates += [projected_phase(k, py, by_py["3.12"]) for by_py in MEASURED_RUNS.values()
                               for py in UNMEASURED]
                self.assertEqual(len(candidates), len(MEASURED_RUNS) * (len(MEASURED) + len(UNMEASURED)), "every "
                                 "measured run of the shard, and each unmeasured interpreter's projection of each round's "
                                 "3.12 phase")
                gov, rnd, py = governing_phase(k)
                self.assertEqual(gov, max(candidates), "the governing phase is the slowest of every measured run and "
                                 "every projection")
                cap, rule, margin = ruled_cap(gov, PER_TEST_TIMEOUT_S, SETUP_S)
                label = ("measured on %s in %s" % (py, ROUND_NAME[rnd]) if py in MEASURED
                         else "%s projected from %s" % (py, ROUND_NAME[rnd]))
                self.assertEqual(self.caps[k], cap, "shard %d's cap must be the ruled figure for its governing phase "
                                 "(%s): %d s plus the %d s per-test timeout plus %d s before the step, rounded up to a "
                                 "multiple of 5 minutes, is %d, a margin of %d s, and 5 minutes more when that margin is "
                                 "under %d s, so %d; ci.yml has %d" % (k, label, gov, PER_TEST_TIMEOUT_S, SETUP_S, rule,
                                                                      margin, MARGIN_FLOOR_S, cap, self.caps[k]))
                self.assertIn("%d s" % gov, self.head, "the cap's comment states shard %d's governing phase, %d s" % (k, gov))

    def test_every_interpreter_of_the_matrix_is_measured_or_projected(self):
        # the governing phase takes the max over every unmeasured interpreter, so UNMEASURED is the matrix's interpreters
        # less the measured ones, read from the matrix: an interpreter the matrix adds is projected (or measured) before
        # its cells are capped. Since the shape switch (2026-10-06) the python-version axis is an expression whose list
        # depends on the event and the shape, so the matrix's interpreters are every one it gives in any run under either
        # shape (tests/test_ci_workflow_concurrency.py's every_python; the caps are keyed on the shard alone, so they hold
        # for 3.10 wherever it runs: on every batch push under full, on the weekly run and a dispatch under smaller). The
        # import is here, not at the top: tests/test_bats_bare_negation.py imports this module under a python with no pytest.
        import sys
        root = os.path.dirname(HERE)
        if root not in sys.path:
            sys.path.insert(0, root)
        from tests.test_ci_workflow_concurrency import every_python
        versions = every_python(self.src)
        self.assertTrue(versions, "the python-version axis names no interpreter: re-anchor this pin")
        self.assertFalse(set(MEASURED) & set(UNMEASURED), "an interpreter is measured or projected, not both")
        self.assertEqual(sorted(MEASURED + UNMEASURED), sorted(versions), "MEASURED and UNMEASURED together are the "
                         "matrix's interpreters: one the matrix adds needs a measured phase or a ratio to 3.12")
        self.assertIn("3.12", MEASURED, "the projections scale 3.12's measured phases")

    def test_the_cap_comment_states_the_rule_and_its_reason(self):
        # the rule as ruled on 2026-10-05: T230b's rule, then 5 minutes more under the margin floor, with the reason in a
        # clause: the run-to-run variation (shard 2's two 3.12 phases over the same files), and what a cap and a timeout
        # each cost
        rule = ("rounded up to a multiple of 5 minutes, and then 5 minutes more when that leaves less than %d s between "
                "the sum and the cap" % MARGIN_FLOOR_S)
        self.assertTrue(rule in self.joined, "the cap's comment states T230b's rule and the margin rule (%r)" % rule)
        lo, hi = sorted((SHARD_PHASE_312_HASH_ALONE_S[2], SHARD_PHASE_312_WEIGHTED_S[2]))
        variation = "shard 2's two 3.12 phases over the same files differ by %d percent" % round(100 * (hi - lo) / lo)
        self.assertTrue(variation in self.joined, "the cap's comment gives the variation the margin rule answers (%r)"
                        % variation)
        self.assertTrue("shard 2 on 3.12 took %d s in the hash-alone run and %d s in this one, over the same files"
                        % (SHARD_PHASE_312_HASH_ALONE_S[2], SHARD_PHASE_312_WEIGHTED_S[2]) in self.joined, "the "
                        "measurement paragraph states shard 2's two 3.12 phases")
        for piece in ("a higher cap costs nothing on a normal run", "about 5 billed minutes on a wedged one",
                      "a timeout shows as a cancelled, red job"):
            with self.subTest(piece=piece):
                self.assertTrue(piece in self.joined, "the cap's comment gives the rule's reason (%r)" % piece)
        count = ROUND_COUNT_WORD.get(len(MEASURED_RUNS))
        self.assertIsNotNone(count, "re-anchor: no word for %d rounds in ROUND_COUNT_WORD" % len(MEASURED_RUNS))
        slowest = "the largest of every measured run of the shard above, in %s runs of four shards, %s, on %s" % (
            count, english([ROUND_NAME[r] for r in MEASURED_RUNS]), english(MEASURED))
        self.assertTrue(slowest in self.joined, "the cap's comment says the governing phase takes every measured run "
                        "(%r)" % slowest)
        self.assertTrue("each interpreter not measured locally, %s" % english(UNMEASURED) in self.joined, "the cap's "
                        "comment names the interpreters it projects")

    def test_the_cap_comment_records_each_rounds_phases(self):
        # each round's record in the measurement paragraphs: "shard k, <3.12> s and <3.14t> s"
        for rnd, by_py in MEASURED_RUNS.items():
            for k in range(1, self.count + 1):
                with self.subTest(round=rnd, shard=k):
                    record = "shard %d, %s" % (k, english(["%d s" % by_py[py][k] for py in MEASURED]))
                    self.assertTrue(record in self.joined, "ci.yml's record of the %s round states shard %d's phases "
                                    "(%r)" % (rnd, k, record))

    def test_the_cap_comment_states_each_shards_governing_run_projection_sum_margin_and_cap(self):
        # For each shard, cap_clause's text: the run that governs (a measured run, or an unmeasured interpreter's
        # projection of a round's 3.12 phase, named with the phase and the step times it scales by), the sum, the rule's
        # figure, the margin under it, and the cap when the margin rule raises it; no other run named as the shard's
        # basis; the step times of every interpreter the projections scale by, and their run; that a projection is not
        # a measurement; and the re-derivation from the private repository's first run. A text pin over figures this
        # file derives (test_each_shards_cap_is_the_ruled_figure_for_its_slowest_run holds the caps).
        projected = False
        for k in range(1, self.count + 1):
            gov, rnd, py = governing_phase(k)
            with self.subTest(shard=k):
                clause = cap_clause(k)
                self.assertTrue(clause in self.joined, "the cap's comment states shard %d's governing run, projection, "
                                "sum, margin and cap (%r)" % (k, clause))
                self.assertEqual(ruled_cap(gov, PER_TEST_TIMEOUT_S, SETUP_S)[0], self.caps[k], "the clause's cap is the "
                                 "expression's")
                if py in MEASURED:
                    self.assertTrue("shard %d, measured" % k in self.joined)
                else:
                    projected = True
                    self.assertFalse("shard %d, measured" % k in self.joined, "shard %d's governing phase is a "
                                     "projection: the cap's comment does not call it measured" % k)
                for r in MEASURED_RUNS:
                    for p in UNMEASURED:
                        if (r, p) != (rnd, py):
                            self.assertFalse("shard %d, %s projected from %s's" % (k, p, ROUND_NAME[r]) in self.joined,
                                             "%s's projection of %s does not govern shard %d: the cap's comment does "
                                             "not name it as the basis" % (p, ROUND_NAME[r], k))
        for k in range(1, self.count + 1):
            with self.subTest(ratios=k):
                record = ratio_record(k)
                self.assertTrue(record in self.joined, "the cap's comment states shard %d's Run pytest seconds on each "
                                "interpreter in run %d and its ratios to 3.12 (%r)" % (k, UNMEASURED_RATIO_RUN, record))
        self.assertTrue("run %d" % UNMEASURED_RATIO_RUN in self.joined, "the cap's comment names the run its ratios come from")
        summary = "So %s" % governing_summary(self.count)
        self.assertTrue(summary in self.joined, "the cap's comment says what governs each shard (%r)" % summary)
        if projected:
            self.assertTrue("A projection, not a measurement" in self.joined, "a projection governs a cap: the cap's "
                            "comment says a projection is not a measurement")
        # the summary: the interpreter whose projection is the largest on every shard (over every round's projections,
        # the first in the rounds' and then UNMEASURED's order on a tie, the order governing_phase breaks ties in), and
        # whether that projection passes each measured run, so that it governs every shard
        largest = set()
        for k in range(1, self.count + 1):
            phases = [(projected_phase(k, py, by_py["3.12"]), py) for by_py in MEASURED_RUNS.values() for py in UNMEASURED]
            if phases:
                top = max(p for p, _py in phases)
                largest.add(next(py for p, py in phases if p == top))
        single = next(iter(largest)) if len(largest) == 1 else None
        for py in UNMEASURED:
            phrase = "so %s's projection is the largest on every shard" % py
            with self.subTest(largest=py):
                if py == single:
                    self.assertTrue(phrase in self.joined, "%s's projection is the largest on every shard: the cap's "
                                    "comment says so (%r)" % (py, phrase))
                else:
                    self.assertFalse(phrase in self.joined, "%s's projection is not the largest on every shard: the "
                                     "cap's comment does not say it is" % py)
        if single is None:
            self.assertFalse("is the largest on every shard" in self.joined, "no one interpreter's projection is the "
                             "largest on every shard: the cap's comment does not say one is")
        # "it" is the one interpreter the summary names, so the clause stands only beside that name
        passes = single is not None and all(governing_phase(k)[2] == single for k in range(1, self.count + 1))
        if passes:
            self.assertTrue("and it passes each measured run" in self.joined, "%s's projection passes every measured "
                            "run of every shard: the cap's comment says so" % single)
        else:
            self.assertFalse("and it passes each measured run" in self.joined, "the largest projection does not pass "
                             "every shard's measured runs, or no one interpreter's is the largest: the cap's comment "
                             "does not say it passes each one")
        self.assertTrue("re-derived from the first run on the private repository's 2-CPU runners" in self.joined,
                        "the cap's comment says the caps are re-derived from the private repository's first run")
        self.assertTrue("the fork's public runners have more CPUs, so the fork's CI times are not that measurement"
                        in self.joined, "the cap's comment says why the fork's CI times are not the re-derivation's "
                        "measurement")

    def test_the_cap_comment_says_whether_the_other_composition_changes_a_cap(self):
        # Shards 1 and 4 ran other files in the hash-alone round than CI's rule gives them (OTHER_COMPOSITION). The caps
        # count every round, as ruled; the comment says whether counting only the rounds that follow CI's rule would
        # change either cap, and each such shard's figures that way. Red, to be reworded, if it would change one.
        P, S = PER_TEST_TIMEOUT_S, SETUP_S
        self.assertTrue(OTHER_COMPOSITION, "re-anchor: no shard ran other files in any round, so the composition "
                        "sentence goes")
        module, where = MOVED_MODULE
        self.assertEqual(sorted(where), sorted(MEASURED_RUNS), "the moved module's shard in each round")
        self.assertEqual(sorted(set(where.values())), sorted(OTHER_COMPOSITION), "the shards whose files differ are the "
                         "moved module's shards")
        others = set(OTHER_COMPOSITION.values())
        self.assertEqual(len(others), 1, "re-anchor: the shards ran other files in different rounds")
        other = next(iter(others))
        kept = {r: v for r, v in MEASURED_RUNS.items() if r != other}
        self.assertTrue(kept, "re-anchor: no round follows CI's rule")
        kept_shards = {where[r] for r in kept}
        self.assertEqual(len(kept_shards), 1, "re-anchor: the moved module's shard differs between the rounds that follow "
                         "CI's rule")
        shards = sorted(OTHER_COMPOSITION)
        self.assertEqual(len(shards), 2, "re-anchor: the sentence speaks of two shards ('neither cap')")
        kept_name = english([ROUND_NAME[r] for r in kept])
        moved = ("Shards %s ran other files in %s than the rule CI runs gives them: %s ran in shard %d there and in shard "
                 "%d in %s, which follow that rule" % (english(shards), ROUND_NAME[other], module, where[other],
                                                        next(iter(kept_shards)), kept_name))
        self.assertTrue(moved in self.joined, "the cap's comment says which shards ran other files, and why (%r)" % moved)
        every = ALL_ROUNDS_WORD.get(len(MEASURED_RUNS))
        self.assertIsNotNone(every, "re-anchor: no word for %d rounds in ALL_ROUNDS_WORD" % len(MEASURED_RUNS))
        counted = "The caps count %s runs; counting %s alone would change neither cap" % (every, kept_name)
        for k in shards:
            with self.subTest(shard=k):
                gx, rx, px = governing_phase(k, kept)
                capx, rulex, _mx = ruled_cap(gx, P, S)
                self.assertEqual(capx, self.caps[k], "re-anchor: counting %s alone changes shard %d's cap from %d to %d, "
                                 "so the cap's comment must say so" % (kept_name, k, self.caps[k], capx))
                self.assertEqual(capx, rulex, "re-anchor: counting %s alone, shard %d's cap comes from the margin rule"
                                 % (kept_name, k))
                gov, rnd, _py = governing_phase(k)
                if rnd == other:
                    desc = ("measured on %s" % px if px in MEASURED else
                            "%s projected from %s's %d s on 3.12" % (px, ROUND_NAME[rx], kept[rx]["3.12"][k]))
                    phrase = "shard %d's governing phase would be %d s (%s), and %d + %d + %d = %d s, still %d" % (
                        k, gx, desc, gx, P, S, gx + P + S, capx)
                else:
                    self.assertEqual(gx, gov, "the governing run is in a kept round, so it governs there too")
                    phrase = "shard %d's cap already comes from %s" % (k, ROUND_NAME[rnd])
                self.assertTrue(phrase in self.joined, "the cap's comment states shard %d's figures counting %s alone "
                                "(%r)" % (k, kept_name, phrase))
        self.assertTrue(counted in self.joined, "the cap's comment says the caps count every run and that counting the "
                        "runs that follow CI's rule alone changes neither cap (%r)" % counted)

    def test_the_cap_comment_says_what_the_current_round_alone_would_give(self):
        # The round over the files CI runs (CURRENT_ROUND, the last to run) governs no cap while an older round's run or
        # projection is slower, and the comment says so with the caps that round alone would give, so a reader sees how
        # much of each cap the older rounds hold. Red, to be reworded, once that round governs a cap.
        self.assertEqual(CURRENT_ROUND, list(MEASURED_RUNS)[-1], "the round over the files CI runs is the last to run")
        governs = [k for k in range(1, self.count + 1) if governing_phase(k)[1] == CURRENT_ROUND]
        self.assertEqual(governs, [], "re-anchor: %s governs shard(s) %r, so the comment's sentence that it governs no "
                         "cap is false" % (ROUND_NAME[CURRENT_ROUND], governs))
        alone = {CURRENT_ROUND: MEASURED_RUNS[CURRENT_ROUND]}
        caps = [ruled_cap(governing_phase(k, alone)[0], PER_TEST_TIMEOUT_S, SETUP_S)[0] for k in range(1, self.count + 1)]
        name = ROUND_NAME[CURRENT_ROUND]
        phrase = "%s%s governs no cap: counted alone it would give %s" % (name[0].upper(), name[1:], english(caps))
        self.assertTrue(phrase in self.joined, "the cap's comment says what the round over the files CI runs would give "
                        "alone (%r)" % phrase)

    def test_the_cap_comment_records_the_caps_the_suite_wide_ratio_gave(self):
        # Until 2026-10-06 every shard's projections took one ratio for the whole suite (SUITE_RATIO_STEP_S); the comment
        # records that ratio's step times and run, the caps it gave by the same rule over the same runs, and each cap the
        # per-shard ratios moved, so a reader sees what changed and why.
        suite = {k: SUITE_RATIO_STEP_S for k in range(1, self.count + 1)}
        old = [ruled_cap(governing_phase(k, steps=suite)[0], PER_TEST_TIMEOUT_S, SETUP_S)[0]
               for k in range(1, self.count + 1)]
        times = english(["%d s on %s" % (SUITE_RATIO_STEP_S[py], py) for py in sorted(UNMEASURED + ("3.12",))])
        record = ("Until 2026-10-06 the caps were %s, by one ratio for the whole suite, from run %d (%s), in which 3.10's "
                  "ratio to 3.12 was %.2f" % (english(old), SUITE_RATIO_RUN, times,
                                               SUITE_RATIO_STEP_S["3.10"] / SUITE_RATIO_STEP_S["3.12"]))
        self.assertTrue(record in self.joined, "the cap's comment records the caps the suite-wide ratio gave (%r)" % record)
        moved = [(k, old[k - 1], self.caps[k]) for k in range(1, self.count + 1) if old[k - 1] != self.caps[k]]
        self.assertTrue(moved, "re-anchor: the per-shard ratios moved no cap, so the record's sentence on the moves goes")
        moves = ("each shard's own ratio took %s" % english(["shard %d from %d to %d" % m for m in moved]))
        self.assertTrue(moves in self.joined, "the cap's comment names every cap the per-shard ratios moved (%r)" % moves)

    def test_the_time_before_the_step_is_the_longest_cells_and_the_comment_names_it(self):
        self.assertEqual(sorted(CELL_EDGE_S), sorted(MEASURED + UNMEASURED), "the times before and after the Run pytest "
                         "step for each Linux interpreter of the matrix, measured or projected")
        self.assertEqual(sorted(CELL_JOB), sorted(CELL_EDGE_S), "a job id for each cell whose times CELL_EDGE_S holds")
        befores = [before for before, _after in CELL_EDGE_S.values()]
        self.assertEqual(SETUP_S, max(befores), "the caps take the longest time before the step of the run's Linux cells")
        self.assertEqual(befores.count(SETUP_S), 1, "two cells share the longest time before the step, %d s: 'the longest "
                         "of its Linux cells' names one cell, so reword the cap comment and this pin" % SETUP_S)
        # the ratios come from another run (UNMEASURED_RATIO_RUN) since 2026-10-06, so the sentence names this one's
        setup = "the %d s in the %s cell of run %d (" % (SETUP_S, SETUP_CELL, CELL_EDGE_RUN)
        tail = "job %d), the longest of its %s Linux cells" % (CELL_JOB[SETUP_CELL], {5: "five"}[len(CELL_EDGE_S)])
        m = re.search(re.escape(setup) + r"[^()]*?" + re.escape(tail), self.joined)
        self.assertTrue(m, "the cap's comment names the time before the step, its cell, its run and job, and that it is the "
                        "longest (%r ... %r)" % (setup, tail))
        # the ratio run's own times before the step: the longest of them changes no cap, and the comment says so
        lo, hi = RATIO_RUN_BEFORE_S
        self.assertGreater(hi, SETUP_S, "re-anchor: the ratio run's longest time before the step is not past SETUP_S, so "
                           "the sentence on it says nothing")
        for k in range(1, self.count + 1):
            with self.subTest(shard=k):
                self.assertEqual(ruled_cap(governing_phase(k)[0], PER_TEST_TIMEOUT_S, hi)[0], self.caps[k], "re-anchor: "
                                 "at run %d's longest time before the step, %d s, shard %d's cap is not %d, so the cap "
                                 "comment's sentence that it changes no cap is false" % (UNMEASURED_RATIO_RUN, hi, k,
                                                                                         self.caps[k]))
        jobs = {20: "twenty"}.get(len(CELL_EDGE_S) * self.count)
        self.assertIsNotNone(jobs, "re-anchor: no word for %d Linux shard jobs" % (len(CELL_EDGE_S) * self.count))
        same = ("in run %d the time before the step was %d to %d s in its %s Linux shard jobs, and at %d s each cap is "
                "the same" % (UNMEASURED_RATIO_RUN, lo, hi, jobs, hi))
        self.assertTrue(same in self.joined, "the cap's comment says the ratio run's longest time before the step changes "
                        "no cap (%r)" % same)
        # a shorter time only lowers a figure, and the comment names the lowest time in the range at which every cap is
        # the same, and the figure below it (round 2 of fork PR 986's review, 2026-10-06): both derived here, never
        # written as a literal, so a new phase or ratio that moves them is red until the comment follows. The pin above
        # stays at the range's top: below the lowest time a shard's figure is under its cap, so the whole range would be
        # red there.
        figures = {s: {k: ruled_cap(governing_phase(k)[0], PER_TEST_TIMEOUT_S, s)[0] for k in range(1, self.count + 1)}
                   for s in range(hi + 1)}
        for s in range(hi + 1):
            for k in range(1, self.count + 1):
                self.assertLessEqual(figures[s][k], self.caps[k], "at %d s before the step shard %d's figure is %d, past "
                                     "its cap of %d, so the comment's sentence that a shorter time never gives a higher "
                                     "cap is false" % (s, k, figures[s][k], self.caps[k]))
        matching = [s for s in range(lo, hi + 1) if figures[s] == self.caps]
        low = matching[0]
        self.assertEqual(matching, list(range(low, hi + 1)), "the times in run %d's range at which every cap is the same "
                         "are not one run of seconds up to %d s: reword the comment and this pin" % (UNMEASURED_RATIO_RUN,
                                                                                                   hi))
        self.assertGreater(low, lo, "re-anchor: every time in run %d's range gives each shard its cap, so the comment's "
                           "sentence on a lower figure says nothing" % UNMEASURED_RATIO_RUN)
        below = {s: {k: f for k, f in figures[s].items() if f != self.caps[k]} for s in range(lo, low)}
        lowered = sorted({k for by_k in below.values() for k in by_k})
        self.assertEqual(len(lowered), 1, "re-anchor: below %d s shards %r get a lower figure, where the comment names "
                         "one shard" % (low, lowered))
        k = lowered[0]
        figure = {by_k.get(k) for by_k in below.values()}
        self.assertEqual(len(figure), 1, "re-anchor: from %d to %d s shard %d's figure is not one value (%r), where the "
                         "comment names one" % (lo, low - 1, k, figure))
        figure = figure.pop()
        lower = ("A shorter time before the step never gives a higher cap: from %d to %d s the rule and the margin rule "
                 "give each shard its cap, and from %d to %d s they give shard %d %d, under its cap of %d"
                 % (low, hi, lo, low - 1, k, figure, self.caps[k]))
        self.assertTrue(lower in self.joined, "the cap's comment names the lowest time in run %d's range at which every "
                        "cap is the same, %d s, and the figure below it (%r)" % (UNMEASURED_RATIO_RUN, low, lower))

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
        self.assertEqual([rule_minutes(p, 600, 27) for p in (678, 981, 2459)], [25, 30, 55], "the three shards' measured "
                         "figures: 1305 s, 1608 s and 3086 s, so 25, 30 and 55")
        self.assertEqual([rule_minutes(p, 600, 27) for p in (679, 1451, 614, 1237)], [25, 35, 25, 35], "the four "
                         "shards' measured figures at the weighted rule: 1306 s, 2078 s, 1241 s and 1864 s, so 25, 35, 25 "
                         "and 35, the caps until 2026-10-05")
        self.assertEqual([rule_minutes(p, 600, 27) for p in (695, 1603, 807, 1625)], [25, 40, 25, 40], "3.10's projected "
                         "phases of the weighted run: 1322 s, 2230 s, 1434 s and 2252 s, so 25, 40, 25 and 40, the caps "
                         "before the slowest run and the margin rule")
        self.assertEqual([ruled_cap(p, 600, 27) for p in (727, 1947, 869, 1625)],
                         [(25, 25, 146), (45, 45, 126), (30, 25, 4), (40, 40, 148)], "3.10's projected phases of each "
                         "shard's slowest run: 1354 s, 2574 s, 1496 s and 2252 s, so 25, 45, 25 and 40 by the rule, with "
                         "margins of 146, 126, 4 and 148 s, and shard 3's under 60 s, so 25, 45, 30 and 40")
        self.assertEqual([ruled_cap(p, 600, 27) for p in (682, 1699, 728, 1400)],
                         [(25, 25, 191), (40, 40, 74), (25, 25, 145), (35, 35, 73)], "3.10's projected phases of the "
                         "merged-main run alone: 1309 s, 2326 s, 1355 s and 2027 s, so 25, 40, 25 and 35, each margin at "
                         "least 60 s, what that run alone would give while the older runs govern")
        suite = {k: SUITE_RATIO_STEP_S for k in (1, 2, 3, 4)}
        self.assertEqual([projected_phase(k, "3.10", SHARD_PHASE_312_MERGED_MAIN_S, suite) for k in (1, 2, 3, 4)],
                         [682, 1699, 728, 1400], "the merged-main run's 3.12 phases, 519, 1293, 554 and 1066 s, times "
                         "1639/1248, rounded up")
        self.assertEqual([projected_phase(k, "3.10", base, suite) for k, base in
                          ((1, SHARD_PHASE_312_HASH_ALONE_S), (2, SHARD_PHASE_312_HASH_ALONE_S),
                           (3, SHARD_PHASE_312_HASH_ALONE_S), (4, SHARD_PHASE_312_WEIGHTED_S))],
                         [727, 1947, 869, 1625], "3.10's projections of each shard's slowest 3.12 run by the suite-wide "
                         "ratio, 1639/1248: 553, 1482, 661 and 1237 s become 727, 1947, 869 and 1625 s, the caps' basis "
                         "until 2026-10-06")
        self.assertEqual([projected_phase(k, "3.10", base) for k, base in
                          ((2, SHARD_PHASE_312_HASH_ALONE_S), (4, SHARD_PHASE_312_WEIGHTED_S))],
                         [2318, 1285], "3.10's projections by each shard's own ratio in run 37415499848: shard 2's "
                         "1482 s times 1883/1204 is 2318 s, shard 4's 1237 s times 1146/1104 is 1285 s")
        self.assertEqual([ruled_cap(p, 600, 27) for p in (679, 2318, 661, 1285)],
                         [(25, 25, 194), (55, 50, 55), (25, 25, 212), (35, 35, 188)], "each shard's governing phase by "
                         "its own ratios: 1306 s, 2945 s, 1288 s and 1912 s, so 25, 50, 25 and 35 by the rule, with "
                         "margins of 194, 55, 212 and 188 s, and shard 2's under 60 s, so 25, 55, 25 and 35")
        self.assertEqual([ruled_cap(p, 600, 27) for p in (543, 2023, 554, 1143)],
                         [(25, 20, 30), (50, 45, 50), (25, 20, 19), (35, 30, 30)], "the merged-main run alone by each "
                         "shard's own ratios: 1170 s, 2650 s, 1181 s and 1770 s, so 20, 45, 20 and 30 by the rule, each "
                         "margin under 60 s, so 25, 50, 25 and 35")
        self.assertEqual([ruled_cap(p, 600, 33)[0] for p in (679, 2318, 661, 1285)], [25, 55, 25, 35], "at run "
                         "37415499848's longest time before the step, 33 s, each cap is the same")
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


class GoverningPhase(unittest.TestCase):
    """projected_phase, governing_phase, ruled_cap and cap_clause over synthetic data: the projection rounds up, the
    largest phase governs over every round and interpreter: the slowest measured run governs whether it is in the first
    round or a later one, and each unmeasured interpreter's projection governs when it is the largest, a projection that
    only ties a measured run does not, a tie between two projections goes to the first in order, the margin rule raises
    a cap whose margin is under the floor and only then, each shard projects by its own ratio, and missing data is
    refused. The step times are {shard: {interpreter: seconds}}, as UNMEASURED_RATIO_STEP_S."""
    STEPS = {1: {"3.10": 130, "3.11": 100, "3.12": 100}}

    def test_the_projection_rounds_up_to_the_second(self):
        self.assertEqual(projected_phase(1, "3.10", {1: 100}, self.STEPS), 130)
        self.assertEqual(projected_phase(1, "3.10", {1: 101}, self.STEPS), 132, "131.3 s rounds up to 132")

    def test_the_largest_phase_governs(self):
        one = {"a": {"3.12": {1: 100}, "3.14t": {1: 120}}}
        self.assertEqual(governing_phase(1, one, ("3.10", "3.11"), self.STEPS), (130, "a", "3.10"))
        low = {"a": {"3.12": {1: 100}, "3.14t": {1: 90}}}
        self.assertEqual(governing_phase(1, low, ("3.11", "3.10"), self.STEPS), (130, "a", "3.10"),
                         "every unmeasured interpreter is read, not the first: a later one's larger projection governs")
        tie = {1: {"3.10": 130, "3.11": 100, "3.12": 100, "3.13": 130}}
        self.assertEqual(governing_phase(1, low, ("3.11", "3.10", "3.13"), tie), (130, "a", "3.10"),
                         "two projections tie: the first in unmeasured's order is the basis")
        high = {"a": {"3.12": {1: 100}, "3.14t": {1: 140}}}
        self.assertEqual(governing_phase(1, high, ("3.10", "3.11"), self.STEPS), (140, "a", "3.14t"))
        even = {"a": {"3.12": {1: 100}, "3.14t": {1: 130}}}
        self.assertEqual(governing_phase(1, even, ("3.10",), self.STEPS), (130, "a", "3.14t"),
                         "a projection must pass the measured run to govern")
        self.assertEqual(governing_phase(1, low, (), self.STEPS), (100, "a", "3.12"))

    def test_the_slowest_run_governs_when_it_is_the_first(self):
        first = {"a": {"3.12": {1: 100}, "3.14t": {1: 200}}, "b": {"3.12": {1: 90}, "3.14t": {1: 95}}}
        self.assertEqual(governing_phase(1, first, ("3.10",), self.STEPS), (200, "a", "3.14t"),
                         "the first round's 3.14t run is the slowest, past the second round's runs and each projection")

    def test_each_unmeasured_interpreters_projection_governs_when_it_is_the_largest(self):
        self.assertTrue(UNMEASURED, "no unmeasured interpreter to project")
        for py in UNMEASURED:
            by_py = dict.fromkeys(UNMEASURED, 110)
            by_py.update({"3.12": 100, py: 150})
            with self.subTest(interpreter=py):
                self.assertEqual(governing_phase(1, {"a": {"3.12": {1: 100}}}, UNMEASURED, {1: by_py}), (150, "a", py))

    def test_the_slowest_run_governs_when_it_is_not_the_first(self):
        later_314t = {"a": {"3.12": {1: 100}, "3.14t": {1: 110}}, "b": {"3.12": {1: 90}, "3.14t": {1: 150}}}
        self.assertEqual(governing_phase(1, later_314t, (), self.STEPS), (150, "b", "3.14t"),
                         "the second round's 3.14t run is the slowest")
        later_312 = {"a": {"3.12": {1: 100}, "3.14t": {1: 110}}, "b": {"3.12": {1: 160}, "3.14t": {1: 120}}}
        self.assertEqual(governing_phase(1, later_312, (), self.STEPS), (160, "b", "3.12"),
                         "the second round's 3.12 run is the slowest")
        later_projection = {"a": {"3.12": {1: 100}, "3.14t": {1: 140}}, "b": {"3.12": {1: 120}, "3.14t": {1: 100}}}
        self.assertEqual(governing_phase(1, later_projection, ("3.10",), self.STEPS), (156, "b", "3.10"),
                         "the second round's 3.12 phase projects to 156 s, past the first round's 140 s and 130 s")
        self.assertEqual(governing_phase(1, {"b": later_projection["b"]}, ("3.10",), self.STEPS), (156, "b", "3.10"))
        self.assertEqual(governing_phase(1, {"a": later_projection["a"]}, ("3.10",), self.STEPS), (140, "a", "3.14t"),
                         "without the second round the first round's measured run governs")

    def test_missing_data_is_refused(self):
        with self.assertRaises(LookupError):
            governing_phase(1, {}, ("3.10",), self.STEPS)
        with self.assertRaises(LookupError):
            governing_phase(1, {"a": {}}, ("3.10",), self.STEPS)
        with self.assertRaises(LookupError):
            governing_phase(1, {"a": {"3.12": {1: None}, "3.14t": {1: 100}}}, ("3.10",), self.STEPS)
        with self.assertRaises(LookupError, msg="a shard missing from the second round alone is refused"):
            governing_phase(1, {"a": {"3.12": {1: 100}, "3.14t": {1: 100}}, "b": {"3.12": {1: 100}, "3.14t": {2: 100}}},
                            (), self.STEPS)
        with self.assertRaises(LookupError, msg="a round with no 3.12 phase has nothing to project"):
            governing_phase(1, {"a": {"3.12": {1: 100}}, "b": {"3.14t": {1: 100}}}, ("3.10",), self.STEPS)
        with self.assertRaises(LookupError):
            governing_phase(1, {"a": {"3.12": {1: 100}}}, ("3.13",), self.STEPS)
        with self.assertRaises(LookupError):
            projected_phase(1, "3.10", {1: 100}, {1: {"3.10": 130}})
        with self.assertRaises(LookupError, msg="a shard with no step times has no ratio of its own"):
            projected_phase(2, "3.10", {2: 100}, self.STEPS)
        with self.assertRaises(LookupError, msg="another shard's ratio is not this shard's"):
            governing_phase(2, {"a": {"3.12": {1: 100, 2: 100}}}, ("3.10",), self.STEPS)
        with self.assertRaises(LookupError):
            projected_phase(1, "3.10", None, self.STEPS)

    def test_the_margin_rule(self):
        self.assertEqual(ruled_cap(727, 600, 27), (25, 25, 146), "1354 s: 25 by the rule, 146 s under, so 25")
        self.assertEqual(ruled_cap(869, 600, 27), (30, 25, 4), "1496 s: 25 by the rule, 4 s under, so 30")
        self.assertEqual(ruled_cap(813, 600, 27), (25, 25, 60), "a margin of exactly 60 s is not under 60 s")
        self.assertEqual(ruled_cap(814, 600, 27), (30, 25, 59), "a margin of 59 s raises the cap")
        self.assertEqual(ruled_cap(873, 600, 27), (30, 25, 0), "a sum exactly at the cap raises it")
        self.assertEqual(ruled_cap(874, 600, 27), (30, 30, 299), "a second past 25 minutes is 30 by the rule, 299 s under")
        self.assertEqual(ruled_cap(727, 600, 27, floor_s=150), (30, 25, 146), "the floor is the argument's")

    def test_cap_clause(self):
        measured = {HASH_ALONE: {"3.12": {1: 100}, "3.14t": {1: 90}}, WEIGHTED: {"3.12": {1: 110}, "3.14t": {1: 1000}}}
        self.assertEqual(cap_clause(1, measured), "shard 1, measured, the weighted run's 1000 s on 3.14t, and "
                         "1000 + 600 + 27 = 1627 s, so 30, a margin of 173 s")
        raised = {HASH_ALONE: {"3.12": {1: 661}, "3.14t": {1: 466}}, WEIGHTED: {"3.12": {1: 614}, "3.14t": {1: 409}}}
        self.assertEqual(cap_clause(1, raised, steps={1: SUITE_RATIO_STEP_S}), "shard 1, 3.10 projected from the "
                         "hash-alone run's 661 s on 3.12, times 1639/1248 is 869 s, and 869 + 600 + 27 = 1496 s, so 25 by "
                         "the rule, a margin of 4 s, under 60 s, so 30")

    def test_each_shard_projects_by_its_own_ratio(self):
        # three shards with the same 3.12 phase and different ratios: red for a projected_phase that reads one shard's
        # ratio for every shard, the largest ratio for every shard, or one ratio for the whole suite
        steps = {1: {"3.10": 100, "3.12": 100}, 2: {"3.10": 160, "3.12": 100}, 3: {"3.10": 90, "3.12": 120}}
        runs = {HASH_ALONE: {"3.12": {1: 100, 2: 100, 3: 100}, "3.14t": {1: 95, 2: 95, 3: 95}}}
        self.assertEqual([projected_phase(k, "3.10", runs[HASH_ALONE]["3.12"], steps) for k in (1, 2, 3)], [100, 160, 75])
        self.assertEqual([governing_phase(k, runs, ("3.10",), steps) for k in (1, 2, 3)],
                         [(100, HASH_ALONE, "3.12"), (160, HASH_ALONE, "3.10"), (100, HASH_ALONE, "3.12")],
                         "shard 2's ratio governs shard 2 alone; shards 1 and 3 keep their measured runs")
        self.assertEqual(cap_clause(2, runs, ("3.10",), steps), "shard 2, 3.10 projected from the hash-alone run's 100 s "
                         "on 3.12, times 160/100 is 160 s, and 160 + 600 + 27 = 787 s, so 15, a margin of 113 s")
        self.assertEqual(governing_summary(3, runs, ("3.10",), steps), "a measured run governs shards 1 and 3, and "
                         "3.10's projection governs shard 2")
        self.assertEqual(ratio_record(3, {3: {"3.10": 90, "3.11": 130, "3.12": 120, "3.13": 121}}), "shard 3, 90 s on "
                         "3.10, 130 s on 3.11, 120 s on 3.12 and 121 s on 3.13, ratios to 3.12 of 0.75, 1.08 and 1.01")

    def test_english(self):
        self.assertEqual(english([25]), "25")
        self.assertEqual(english([25, 40]), "25 and 40")
        self.assertEqual(english([25, 40, 25, 40]), "25, 40, 25 and 40")


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
