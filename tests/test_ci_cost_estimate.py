#!/usr/bin/env python3
"""ci.yml's cost estimate (its header comment, 2026-10-05): every workflow the private repository bills is counted, the
sums follow from inputs held here, the dollars are the list price, at which every minute here would be billed since the
owner's other repositories use the plan's included minutes up, and the jobs whose caps the private runner's shape was not
measured for are named for the first private batch run to confirm.

The repository moves to a private one (approved 2026-10-04), where every run is billed by the job-minute, each job rounded
up to a whole minute. A review on 2026-10-05 found three gaps in the header's estimate. Its total "in all" counted ci.yml's
runs and secret-scan.yml's copy on a batch push but none of the repository's other workflows (about 5,200 minutes a month
at the pace of the week to 2026-10-04 by the rates taken then, about 4,200 by the rates measured since: item 6). It priced
every minute at the list rate without saying how the plan's included minutes bear on the bill. And it called the other
Linux jobs' public-runner times a floor on the private runner's 2 CPUs, where a local measurement found their longest
steps barely slower, and named no job whose cap the first private run must confirm.

Pins over ci.yml's header comment (its comment lines before `on:`, joined into one line):
1. EVERY WORKFLOW IS COUNTED (EveryWorkflowIsCounted): each file in .github/workflows, read from the directory, is named in
   the header, so a workflow added later is priced there or stated free.
2. THE SUMS (TheSums): the header states the figures this file derives from inputs of its own, each a literal here (the
   jobs API's seconds and minutes and the runs, pulls, issue-events and activity APIs' counts, read on 2026-10-05 and
   2026-10-06): a batch run's and a manual run's minutes, the batch runs' dollars, ci.yml's minutes and dollars a month and
   the totals in all at 30 and 58 batch runs, each other workflow's minutes, their sum and its dollars, and the minutes the
   allowance sentence quotes. Each stated figure must be within its rounding of the derived one.
3. THE ALLOWANCE (TheAllowance): the header says its dollars are the list price and that every minute here would be billed
   at it, states the included minutes GitHub documents for the plan (50,000 a month for Enterprise Cloud, read
   2026-10-05), and says the owner's other repositories use them up in about the first week of each month, with the
   minutes one of them used on 1 to 4 October 2026 and the days 50,000 last at that pace.
4. THE CAPS THE FIRST PRIVATE RUN CONFIRMS (CapsTheFirstPrivateRunConfirms): each Linux job other than the python shards
   whose time in run 37212676524 was more than half its cap is named in the header's sentence on the first private batch
   run. On 2 CPUs where the public runner has 4, a job bound by the CPUs takes at most about twice as long, so a job under
   half its cap does not reach it by the CPU count alone, and one over half can.
At the commit before these pins, all four are red: the header named secret-scan.yml alone of the other workflows, stated
161 and 238 dollars as the total in all, said nothing of an allowance, and had no sentence on the first private batch run.
5. THE TWO PREMISES (TheTwoPremises, 2026-10-05): the python job's shard caps take each unmeasured interpreter's projected
   phase where it is the largest (tests/test_ci_bats_bound.py, governing_phase), and since the slowest-run rule of the
   same day those are the projections of each shard's slower 3.12 run of the two runs of four shards (the hash-alone run
   and the weighted run), where this estimate bills those interpreters' shard jobs at the weighted run's slower measured
   phase. The caps also read both runs' measured phases on 3.12 and 3.14t, where the estimate bills the weighted run's
   alone. Caps do not bill, so the estimate's figures stand, but the header says in one sentence what each of the two
   takes, and what a batch run would bill at the caps' projected ones, by the estimate's own method, with 3.12 and 3.14t
   held at the weighted run's phases, as the estimate bills them. The shard jobs' 337 is derived here too, from the same
   phases and the cells' times. Red at the commit before it: the header had no such sentence. The figures moved with the
   caps' basis: 482 minutes, 26 more than the estimate, at the weighted run's projections, the caps' basis until the
   slowest-run rule. Red at the commit before the sentence named 3.12 and 3.14t: it said the two take different phases
   for 3.10, 3.11 and 3.13 alone, and did not say where the figure holds 3.12 and 3.14t.
6. THE MEASURED RATES (2026-10-05, within TheSums and TheAllowance): a measurement of the fork's activity on 2026-10-05,
   re-derived from the APIs on 2026-10-06, replaced three inputs, and the header states each rate with its week and what
   was counted. pr-tier.yml is priced at its four trigger events, 152 in the week to 2026-10-04, where the earlier 534
   counted every run of that week, when main's copy also ran on each push to a pull request and each edit; secret-scan.yml
   at the pushes the activity API lists, 238, where the earlier 212 counted ci.yml's runs on pull requests and on main;
   manual runs at the normal pace, one or two a month, counted at two, where the earlier 29 were last month's, 28 of them
   CI-infrastructure work. The merge of main brought docs.yml's pull_request trigger, priced at that week's pace: the
   openings of and pushes to the pull requests touching the site's inputs that started a run of pr-tier.yml then. Its 4
   pull-request runs of that week move out of the pushes to main. The allowance sentence says the owner's other
   repositories use the included minutes up, so every minute here is billed, where it said this repository would use a
   large part of them. Red at the commit before it: these inputs and figures changed first, and TheSums and TheAllowance
   failed against the unchanged header.
Text pins: they hold what the header says and that its sums agree with the inputs here, not what GitHub bills; the first
private batch run's billed minutes are the measurement."""
import math
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the import from a sibling module, as tests/test_ci_macos_schedule.py does
sys.path.insert(0, ROOT)
from tests.test_ci_workflow_concurrency import JOBS, job_lines, job_value  # noqa: E402
from tests import test_ci_bats_bound as bound  # noqa: E402

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
WORKFLOWS = os.path.dirname(WF)

# ---- the inputs, each a literal of this file ---------------------------------------------------------------------------
# a batch run: the twenty shard jobs (the header's derivation from the python job's cap comment, which shard_jobs_total
# repeats), each other Linux job at its
# seconds in run 37212676524 (batch/2026-10-04b, on the public runner; the jobs API), each rounded up to a whole minute, and
# secret-scan.yml's copy on the push, about 3 minutes (that file's header); a manual run is the same Linux jobs without it
SHARD_JOBS_MIN = 337
OTHER_JOB_S = {"served-pages": 2951, "shell": 2426, "vendored-tooling": 845, "vscode-extension": 370, "secrets": 167}
SECRET_SCAN_RUN_MIN = 3   # also each push's run in the week to 2026-10-04: 75 billed minutes over its 25 runs
RATE = 0.006   # dollars a minute, GitHub's posted rate for its Linux 2-core x64 runner (read 2026-10-05)
BATCH_RUNS = (30, 58)   # a month: the 30 days to 2026-10-04, and the rate since 2026-09-21
MANUAL_RUNS = 2         # a month: the normal pace, one or two, counted at two (2026-10-05). Of the 29 in the 30 days to
                        # 2026-10-04, 28 came from 2026-09-27 on, on four branches of CI-infrastructure work, and one
                        # in the 22 days before (the runs API)
# the other workflows at the pace of the week to 2026-10-04 (runs, pull requests, events and pushes created 2026-09-28 to
# 2026-10-04), scaled to 30 days; measured on 2026-10-05 and re-derived on 2026-10-06, these supersede the estimate's
# earlier rates (item 6 of the docstring)
WEEK_TO_MONTH = 30 / 7
WEEK_PUSHES = 187 + 35 + 3 + 13     # secret-scan.yml: the pushes the activity API lists, branch pushes, branch creations,
                                    # force-pushes and merges to main; pushes to batch branches (the batch figure counts
                                    # the copy on those) and branch deletions not counted
PR_TIER_WEEK_RUNS = 47 + 95 + 10 + 0    # pr-tier.yml at its four trigger events: pull requests opened (the pulls API),
                                        # labels added and removed, and pull requests reopened (the issue-events API)
PR_TIER_RUN_MIN = 535 / 534     # pr-tier.yml's billed minutes a run: 535 over all 534 of its runs that week, one of them 2
MAIN_PUSH_WEEK_MIN = 13 + 20 + 6    # ledger.yml, pr-orphans.yml and docs.yml on pushes to main: the billed minutes of their
                                    # 13, 13 and 6 runs that week (the jobs API)
DOCS_PR_WEEK_RUNS = 78          # docs.yml on a pull request touching the site's inputs (on main since 2026-10-05): the
                                # openings of and pushes to such pull requests that week, each a new head in a run of
                                # pr-tier.yml, whose copy on main then ran on both; the files read on 2026-10-06
DOCS_PR_RUN_MIN = 1             # each of docs.yml's 4 pull-request runs that week billed 1 minute
INCLUDED_MIN = 50000            # GitHub's documented included minutes for Enterprise Cloud (read 2026-10-05)
OTHER_REPO_MIN_OCT_1_4 = 27993  # one of the owner's other repositories, in its runs created on 1 to 4 October 2026: each
                                # job on a runner rounded up (the jobs API), a re-run attempt's copied records dropped
OTHER_REPO_DAYS = 4             # the days that figure spans

# ---- the stated figures, each held to its derivation within its rounding (TheSums) -------------------------------------
STATED = {
    "batch run minutes": (456, 1), "manual run minutes": (453, 1),
    "batch dollars at 30": (82, 1), "batch dollars at 58": (159, 1),
    "secret-scan pushes": (1020, 10), "secret-scan minutes": (3060, 10), "pr-tier minutes": (650, 10),
    "main-push minutes": (170, 10), "docs pull-request minutes": (330, 10),
    "other minutes": (4200, 100), "other dollars": (25, 1),
    "ci minutes at 30": (14600, 100), "ci minutes at 58": (27400, 100), "ci dollars at 30": (88, 1),
    "ci dollars at 58": (164, 1),
    "all minutes at 30": (18800, 100), "all minutes at 58": (31600, 100), "all dollars at 30": (113, 1),
    "all dollars at 58": (189, 1),
    "other repository minutes on 1 to 4 October": (28000, 1000),
}


def derived():
    """{figure name: value} for each of STATED, from the inputs above."""
    other_jobs = sum(math.ceil(s / 60) for s in OTHER_JOB_S.values())
    batch = SHARD_JOBS_MIN + other_jobs + SECRET_SCAN_RUN_MIN
    manual = SHARD_JOBS_MIN + other_jobs
    pushes = WEEK_PUSHES * WEEK_TO_MONTH
    scan = pushes * SECRET_SCAN_RUN_MIN
    tier = PR_TIER_WEEK_RUNS * PR_TIER_RUN_MIN * WEEK_TO_MONTH
    main = MAIN_PUSH_WEEK_MIN * WEEK_TO_MONTH
    docs = DOCS_PR_WEEK_RUNS * DOCS_PR_RUN_MIN * WEEK_TO_MONTH
    other = scan + tier + main + docs
    ci = {n: n * batch + MANUAL_RUNS * manual for n in BATCH_RUNS}
    lo, hi = BATCH_RUNS
    return {
        "batch run minutes": batch, "manual run minutes": manual,
        "batch dollars at 30": lo * batch * RATE, "batch dollars at 58": hi * batch * RATE,
        "secret-scan pushes": pushes, "secret-scan minutes": scan, "pr-tier minutes": tier,
        "main-push minutes": main, "docs pull-request minutes": docs,
        "other minutes": other, "other dollars": other * RATE,
        "ci minutes at 30": ci[lo], "ci minutes at 58": ci[hi], "ci dollars at 30": ci[lo] * RATE,
        "ci dollars at 58": ci[hi] * RATE,
        "all minutes at 30": ci[lo] + other, "all minutes at 58": ci[hi] + other,
        "all dollars at 30": (ci[lo] + other) * RATE, "all dollars at 58": (ci[hi] + other) * RATE,
        "other repository minutes on 1 to 4 October": OTHER_REPO_MIN_OCT_1_4,
    }


# ---- the phases the caps take, against the estimate's (TheTwoPremises) -------------------------------------------------
# each Linux cell's seconds before and after its Run pytest step in run 37212676524, which every shard job of that
# interpreter is charged beside its phase: tests/test_ci_bats_bound.py's CELL_EDGE_S, where the caps' time before the
# step is derived from the same figures
CELL_EDGE_S = bound.CELL_EDGE_S
# the stated figures: a batch run's minutes with each unmeasured interpreter's shard jobs at its own projected phases, the
# ones the caps take (the projections of each shard's slower 3.12 run of the two rounds), and that figure less the
# estimate's batch run; exact, since each job is rounded up to a whole minute before the sum
PROJECTED_STATED = {"projected batch run minutes": 500, "projected difference": 44}


def shard_job_minutes(phases, py):
    """[minutes] of interpreter py's shard jobs, one per shard of phases ({shard: seconds}) in shard order: each phase plus
    the cell's seconds before and after the Run pytest step (CELL_EDGE_S), rounded up to a whole minute."""
    before, after = CELL_EDGE_S[py]
    return [math.ceil((phases[k] + before + after) / 60) for k in sorted(phases)]


def caps_projection_base():
    """{shard: seconds}: each shard's slower 3.12 phase of the measured rounds (tests/test_ci_bats_bound.py's
    MEASURED_RUNS), the 3.12 phase whose projection is the largest of the shard's projections the caps take."""
    rounds = list(bound.MEASURED_RUNS.values())
    return {k: max(r["3.12"][k] for r in rounds) for k in rounds[0]["3.12"]}


def shard_jobs_total(projected):
    """The shard jobs' minutes for one batch run: 3.12 and 3.14t at their own phases in the weighted run, and each
    unmeasured interpreter at the weighted run's slower phase of the two (the estimate; projected False) or at its own
    projected phase as the caps take it, the projection of each shard's slower 3.12 run (projected True), the phases
    tests/test_ci_bats_bound.py holds."""
    w312, w314t = bound.SHARD_PHASE_312_WEIGHTED_S, bound.SHARD_PHASE_314T_WEIGHTED_S
    total = sum(shard_job_minutes(w312, "3.12")) + sum(shard_job_minutes(w314t, "3.14t"))
    base = caps_projection_base()
    for py in bound.UNMEASURED:
        if projected:
            phases = {k: bound.projected_phase(k, py, base) for k in base}
        else:
            phases = {k: max(w312[k], w314t[k]) for k in w312}
        total += sum(shard_job_minutes(phases, py))
    return total


def projected_derived():
    """{figure name: value} for each of PROJECTED_STATED: the estimate's batch run with its shard jobs at the projected
    phases, and the difference from the estimate's batch run."""
    batch = derived()["batch run minutes"]
    projected = batch - SHARD_JOBS_MIN + shard_jobs_total(True)
    return {"projected batch run minutes": projected, "projected difference": projected - batch}


def header(path=WF):
    """ci.yml's header comment: its comment lines before the `on:` line, each without its `#` and its surrounding spaces,
    the empty ones dropped, joined with single spaces. Raises LookupError when the file has no top-level `on:` line."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    if "on:" not in lines:
        raise LookupError("ci.yml has no top-level on: line: re-anchor this pin")
    head = lines[:lines.index("on:")]
    return " ".join(t for t in (l[1:].strip() for l in head if l.startswith("#")) if t)


def linux_cap(src, job):
    """A job's Linux cap in minutes: its job-level timeout-minutes, a whole number or the `matrix.os == 'macos-latest' &&
    N || M` expression's M. Raises LookupError for any other shape."""
    for line in job_lines(src, job):
        m = re.match(r"^    timeout-minutes: (?:(\d+)|\$\{\{ matrix\.os == 'macos-latest' && \d+ \|\| (\d+) \}\})$", line)
        if m:
            return int(m.group(1) or m.group(2))
    raise LookupError("the %s job has no job-level timeout-minutes this pin reads: re-anchor it" % job)


CONFIRM = "first private batch run"


def confirming_sentences(text):
    """The sentences of text (split after a period and a space) that name the first private batch run."""
    return [s for s in re.split(r"(?<=\.) ", text) if CONFIRM in s]


class EveryWorkflowIsCounted(unittest.TestCase):
    def test_each_workflow_file_is_named_in_the_header(self):
        files = sorted(f for f in os.listdir(WORKFLOWS) if f.endswith((".yml", ".yaml")))
        self.assertIn("ci.yml", files, "the directory listing is not the workflows directory: re-anchor this pin")
        text = header()
        for f in files:
            if f == "ci.yml":
                continue
            with self.subTest(workflow=f):
                self.assertTrue(f in text, "%s is not named in ci.yml's header: on a private repository every workflow's "
                                "runs are billed, so the cost estimate prices it or says why it bills nothing" % f)


def states(text, phrase):
    """True when text holds phrase with no further digit of a number after it: "about 25" is not in "about 25,000" or
    "about 250"."""
    return re.search(re.escape(phrase) + r"(?![0-9]|,[0-9])", text) is not None


class TheSums(unittest.TestCase):
    def setUp(self):
        self.text = header()
        self.d = derived()

    def test_each_stated_figure_is_its_derivation_within_its_rounding(self):
        self.assertEqual(sorted(STATED), sorted(self.d), "a stated figure for each derived one")
        for name, (figure, unit) in sorted(STATED.items()):
            with self.subTest(figure=name):
                self.assertLessEqual(abs(figure - self.d[name]), unit / 2, "%s: the header's %s is not %.2f rounded to "
                                     "the nearest %s" % (name, format(figure, ","), self.d[name], unit))

    def test_the_header_states_each_figure(self):
        # each figure as "about <figure>", with no further digit after it ("about 25" is not stated by "about 25,000")
        for name, (figure, _unit) in sorted(STATED.items()):
            want = "about %s" % format(figure, ",")
            with self.subTest(figure=name):
                self.assertTrue(states(self.text, want), "ci.yml's header does not state %s as %r" % (name, want))

    def test_this_workflow_and_in_all_each_state_minutes_and_dollars_at_both_batch_paces(self):
        lo, hi = BATCH_RUNS

        def pair(kind, n):
            return "about %s minutes and about %d dollars" % (format(STATED["%s minutes at %d" % (kind, n)][0], ","),
                                                               STATED["%s dollars at %d" % (kind, n)][0])
        ci = "%s a month for this workflow at %d batch runs, and %s at %d" % (pair("ci", lo), lo, pair("ci", hi), hi)
        every = "%s a month in all at %d batch runs, and %s at %d" % (pair("all", lo), lo, pair("all", hi), hi)
        self.assertTrue(states(self.text, ci), "the header names ci.yml's own figures as this workflow's (%r)" % ci)
        self.assertTrue(states(self.text, every), "the header's total in all counts the other workflows (%r)" % every)
        self.assertEqual(len(re.findall(r"a month in all", self.text)), 1, "one total in all")
        self.assertTrue("one or two a month" in self.text, "the header says manual runs are counted at the normal pace, "
                        "one or two a month")


class TheAllowance(unittest.TestCase):
    def test_the_header_says_every_minute_would_be_billed_at_the_list_price(self):
        text = header()
        self.assertTrue("list price" in text, "the header says its dollars are the list price of every minute")
        self.assertTrue("every minute here would be billed at list price" in text, "the header says every minute here "
                        "would be billed at the list price")
        self.assertTrue("%s included minutes a month" % format(INCLUDED_MIN, ",") in text, "the header states the "
                        "included minutes GitHub documents for the plan, %s a month" % format(INCLUDED_MIN, ","))
        self.assertTrue("the owner's other repositories use them up in about the first week of each month" in text,
                        "the header says the owner's other repositories use the included minutes up in about the first "
                        "week of each month")
        want = "about %s on 1 to 4 October 2026" % format(STATED["other repository minutes on 1 to 4 October"][0], ",")
        self.assertTrue(want in text, "the header gives the minutes behind that (%r)" % want)

    def test_the_included_minutes_last_the_days_the_header_says_at_that_pace(self):
        days = INCLUDED_MIN / (OTHER_REPO_MIN_OCT_1_4 / OTHER_REPO_DAYS)
        words = {5: "five", 6: "six", 7: "seven", 8: "eight"}
        self.assertIn(round(days), words, "at %s minutes in %d days the %s included minutes last %.1f days, not about "
                      "the first week the header says" % (format(OTHER_REPO_MIN_OCT_1_4, ","), OTHER_REPO_DAYS,
                                                          format(INCLUDED_MIN, ","), days))
        want = "a pace that spends the %s in about %s days" % (format(INCLUDED_MIN, ","), words[round(days)])
        self.assertTrue(want in header(), "the header states the days the included minutes last at that pace (%r, %.2f "
                        "days)" % (want, days))


class CapsTheFirstPrivateRunConfirms(unittest.TestCase):
    def test_each_job_past_half_its_cap_is_named_for_the_first_private_batch_run(self):
        with open(WF, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(sorted(OTHER_JOB_S), sorted(j for j in JOBS if j != "python"), "a time in run 37212676524 for "
                         "each Linux job but the python shards: a job added to ci.yml needs its time here")
        sentences = confirming_sentences(header())
        self.assertTrue(sentences, "the header has no sentence on the %s" % CONFIRM)
        self.assertTrue(any("the shard caps are re-derived from its times" in s for s in sentences), "the header's "
                        "sentence on the %s says the shard caps are re-derived from its times" % CONFIRM)
        due = []
        for job, secs in sorted(OTHER_JOB_S.items()):
            cap = linux_cap(src, job)
            if secs * 2 > cap * 60:
                due.append(job)
                display = job_value(src, job, "name").split(" (")[0]
                with self.subTest(job=job):
                    self.assertTrue(any(display in s for s in sentences), "the %s job took %d s of its %d-minute cap in "
                                    "run 37212676524 on 4 CPUs, past half of it, so on 2 it can reach the cap: the header's "
                                    "sentence on the %s names it (%r)" % (job, secs, cap, CONFIRM, display))
        self.assertTrue(due, "no job is past half its cap: re-read the population (the served-pages job took 2951 s in "
                        "run 37212676524, past half of its cap, 50 minutes then and 60 since 2026-10-05)")


class TheTwoPremises(unittest.TestCase):
    def test_every_linux_interpreter_has_its_cells_times(self):
        self.assertEqual(sorted(CELL_EDGE_S), sorted(bound.MEASURED + bound.UNMEASURED), "the times before and after the "
                         "Run pytest step for each Linux interpreter of the matrix, measured or projected")

    def test_the_header_states_the_cells_times_before_and_after_the_step(self):
        befores = [before for before, _after in CELL_EDGE_S.values()]
        afters = [after for _before, after in CELL_EDGE_S.values()]
        text = header()
        cell = "in that interpreter's cell of run %d" % bound.CELL_EDGE_RUN
        self.assertTrue(cell in text, "the header names the run the cells' times come from (%r)" % cell)
        span = "%d to %d s before and %d to %d s after" % (min(befores), max(befores), min(afters), max(afters))
        self.assertTrue(span in text, "the header states the range of the cells' times before and after the Run pytest "
                        "step (%r)" % span)

    def test_the_caps_projection_base_is_each_shards_slower_312_run(self):
        # the base the projected figure scales: the slowest 3.12 run of each shard over every round, which is what the
        # caps' governing phase projects (the largest projection of a shard is that of its largest 3.12 phase)
        base = caps_projection_base()
        self.assertEqual(sorted(base), sorted(bound.SHARD_PHASE_312_WEIGHTED_S), "a base for each shard")
        self.assertEqual(len(bound.MEASURED_RUNS), 2, "re-anchor: the header's sentence speaks of two runs")
        for k, s in sorted(base.items()):
            with self.subTest(shard=k):
                self.assertEqual(s, max(bound.SHARD_PHASE_312_HASH_ALONE_S[k], bound.SHARD_PHASE_312_WEIGHTED_S[k]))
                for py in bound.UNMEASURED:
                    self.assertEqual(bound.projected_phase(k, py, base),
                                     max(bound.projected_phase(k, py, r["3.12"]) for r in bound.MEASURED_RUNS.values()),
                                     "the projection of the slower 3.12 run is the largest of the rounds' projections")

    def test_the_shard_jobs_figure_is_its_derivation(self):
        self.assertEqual(shard_jobs_total(False), SHARD_JOBS_MIN, "the estimate's twenty shard jobs: 3.12 and 3.14t at "
                         "their own phases in the weighted run and 3.10, 3.11 and 3.13 at its slower measured phase, each "
                         "job with its cell's times before and after the step, rounded up to a whole minute")

    def test_each_projected_figure_is_its_derivation(self):
        d = projected_derived()
        self.assertEqual(sorted(PROJECTED_STATED), sorted(d), "a stated figure for each derived one")
        for name, figure in sorted(PROJECTED_STATED.items()):
            with self.subTest(figure=name):
                self.assertEqual(figure, d[name], "%s: stated %d, derived %d" % (name, figure, d[name]))

    def test_the_header_says_so_in_one_sentence(self):
        # the sentence that names the projected phases states that the caps take each shard's slower measured run of
        # the two runs on 3.12 and 3.14t and, for the unmeasured interpreters, the projections of each shard's slower
        # 3.12 run, and the estimate the weighted run's measured phases; the minutes a batch run would bill with the
        # unmeasured interpreters at the caps' projected phases and 3.12 and 3.14t at the weighted run's, the basis the
        # figure holds; and the difference from the estimate's batch run
        text = header()
        sentences = [x for x in re.split(r"(?<=\.) ", text) if "projected phases" in x]
        self.assertEqual(len(sentences), 1, "one sentence of the header names the projected phases: %r" % sentences)
        sentence = sentences[0]
        n = PROJECTED_STATED["projected batch run minutes"]
        diff = PROJECTED_STATED["projected difference"]
        batch = STATED["batch run minutes"][0]
        want = (
            "take different phases: the caps take each shard's slower measured run of the two runs of four shards "
            "on %s," % bound.english(bound.MEASURED),
            "and for %s their projected phases of each shard's slower 3.12 run" % bound.english(bound.UNMEASURED),
            "the estimate the weighted run's measured ones",
            "with %s at those projected phases and %s at the weighted run's, a batch run would bill about %d minutes, "
            "%d %s than the estimate's %d" % (bound.english(bound.UNMEASURED), bound.english(bound.MEASURED), n,
                                              abs(diff), "more" if diff >= 0 else "fewer", batch),
        )
        for piece in want:
            with self.subTest(piece=piece):
                self.assertTrue(piece in sentence, "the header's sentence on the two premises states %r" % piece)


class TheReadersThemselves(unittest.TestCase):
    """The readers over synthetic text: header() stops at `on:`, linux_cap reads both cap shapes and refuses another, and
    confirming_sentences picks the sentence that names the run."""

    def test_header_reads_only_the_comment_before_on(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ci.yml")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("name: CI\n\n# one\n# two\n#\non:\n  push:\n# after\n")
            self.assertEqual(header(p), "one two")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("name: CI\n# one\n")
            with self.assertRaises(LookupError):
                header(p)

    def test_linux_cap_reads_both_shapes(self):
        src = ("jobs:\n  a:\n    timeout-minutes: 50\n  b:\n    timeout-minutes: ${{ matrix.os == 'macos-latest' && 60 || 55 }}\n"
               "  c:\n    timeout-minutes: ${{ inputs.x && 5 || 6 }}\n")
        self.assertEqual(linux_cap(src, "a"), 50)
        self.assertEqual(linux_cap(src, "b"), 55)
        with self.assertRaises(LookupError):
            linux_cap(src, "c")

    def test_states_refuses_a_longer_number(self):
        self.assertTrue(states("about 25 dollars", "about 25"))
        self.assertTrue(states("about 25. Next", "about 25"))
        self.assertFalse(states("about 25,000 minutes", "about 25"))
        self.assertFalse(states("about 250 minutes", "about 25"))

    def test_confirming_sentences(self):
        text = "A floor. The first private batch run confirms the Served pages and Shell caps. Another."
        self.assertEqual(confirming_sentences(text), ["The first private batch run confirms the Served pages and Shell caps."])


if __name__ == "__main__":
    unittest.main()
