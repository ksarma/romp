#!/usr/bin/env python3
"""The served-page tests run in a CI job of their own, with their own cap (.github/workflows/ci.yml, 2026-09-28).

The step "Browser-backed served-page tests (pytest)" ran last in the vscode-extension job. At the fork's main 1d591384e
(run 36388144219) that job took 36 min 22 s of its 40-minute cap: the served step 1930 s, the steps before it 250 s. Fork
PRs 821, 857 and 860 each add served labs (about 205 s, 90 s and 34 s; 860's figure is the own times of the three
kernel-backed tests it adds, on a development box, and its served step took 11 s more than main's, 32 min 21 s on its run
36519655646 against 32 min 10 s on the run above): 821 with 857 in one batch would have run the job about 77 s past its
cap, and 821 with 860 about 21 s past it by 860's first figure (2 s under it by the second), and 857 with 860 would have
left it 94 s. Raising the cap was declined, since it would hide the growth; the step moved to a job of its own,
served-pages, with the setup it needs (the checkout, node with its npm cache, npm ci, the Playwright browser cache and the
pinned Chromium, Python) and a cap sized for it alone, the vendored tooling job's structural fix (tests/test_ci_vendored_job.py)
applied a second time. The job runs beside the vscode-extension job, so a red step there no longer skips the served labs.

THE PIN IS EXACT EQUALITY, read as text, the mechanism tests/test_ci_vendored_job.py uses for the vendored-tooling job, whose
readers this module imports (lines, job_block, content, check_name_once, workflow_texts), so the two modules read the file
one way. It is a module of its own because its jobs, figures and reasons are the served move's, not the vendored move's,
and its two literals would double the other module's length. The whole-file checks stay there and cover this module's jobs
too: the file holds no line break but LF, its top-level keys (no workflow env: or defaults: reaches a job) and its on: block
equal their literals. The checks here:

1. The served-pages job's block, with its comment-only lines removed and nothing else changed (indentation, trailing blanks
   and every value stay as written), EQUALS EXPECTED_SERVED_JOB: every key, step and field, the served step's env, flags and
   run block, and the cap (80). The block runs from the job's key line to the next line that starts, after none or two
   spaces, with a character other than a blank or `#`, or to the end of the file: this job is the file's last, as
   tests/test_ci_sdk_pin.py requires (it appends synthetic steps at the end of the file and reads them as the served step's
   job's), so its block ends with the empty text after the file's last line feed, and a second trailing line feed is red.
   The served step's run block is a block scalar; content() keeps every line inside one, a `#` line included, since YAML
   reads it as the scalar's text.
2. The vscode-extension job's block, read the same way, EQUALS EXPECTED_EXTENSION_JOB: the steps it kept (Install deps
   through the Dashboard pane bench) and its cap (17), so the served step put back, or any field of any of its steps
   changed, is red.
3. The served-pages job's name up to its runner label, `Served pages (pytest, `, is held by exactly one content line, in
   any case, across every *.yml and *.yaml file under .github/workflows, read from its bytes (check 6 of the other module,
   whose docstring states the read and its limits): a second job of that name, written bare, quoted, in another case or
   with its runner slot as an expression, would put a second check of that name beside the real one. The count reads one
   line's text, and the other module's name-line check (check_name_lines, in its check 6) covers this name too: it
   refuses, in every workflow file, a name: line whose name YAML would assemble from later lines or from an anchor, or
   decode from an escape (an empty value, a block indicator, a backslash, a value that starts with a tag or an anchor, an
   alias, a quoted value left open, a value continued on the next line), so a twin whose name is folded over lines
   (`name: >-`, one of the three twins the fork PR's re-check planted) or spelled through an escape is red there. It reads
   a name key after the indicator `-`, `?` or `:` (a list item, an explicit key, an explicit key's value), and reads no
   name key inside a flow mapping, written as an explicit key itself (`? name`, its value on the next line's `:`),
   through an escape in a quoted key, after a tag or an anchor on the key, or as an alias (the other module's check 6
   lists these forms; that check is closed, so a form found later joins that list). The count still reds a twin under
   such a key whose name is whole on one line, but a twin whose name is split over lines or spelled through an escape is
   read by neither check. tests/test_ci_sdk_pin.py refuses those
   five forms in ci.yml, and in the other workflow files no tests/test_ci_*.py module refuses them.
4. The served-pages job's cap meets the rule that sized it, so a cap lowered in ci.yml and in EXPECTED_SERVED_JOB
   together, which check 1 cannot see, is red. The cap is the block's one line at four spaces that holds `timeout`, with
   its comment-only lines removed (the read the other module's check_shell_cap makes of the Shell job's cap), and it must
   be `    timeout-minutes: ` and digits alone: no such line, two of them, or any other value is red, not skipped. Its
   minutes must be at least SERVED_CAP_FLOOR, SLOWEST_SERVED_JOB_S and half again, rounded up to a multiple of 5 minutes,
   where SLOWEST_SERVED_JOB_S is the slowest of SERVED_RUNS over every job, a job cancelled at the cap counted at its
   cancel time as a lower bound (the ruling of 2026-10-06: leaving such a job out reads the rule on the miss side).
   SERVED_RUNS is read whole first: no job, a record short of a field, a field that is not a positive integer, a way of
   counting other than MEASURED or LOWER_BOUND, or a job given twice is red with the reason (SERVED_RUNS itself, read so,
   is refused when the module loads), never a job left out of the floor. The job's comment-only lines before the cap
   line, each with its `#` marker and the blanks around it dropped and joined with one space, hold exactly one sentence
   `<m> min <s> s and half again is <m> min <s> s, so <N>.`, whose first time is SLOWEST_SERVED_JOB_S, whose second is
   exactly that time and half again (its seconds end in .5 when the first time's seconds are odd), and whose N is the
   cap: a cap changed without its sentence is red, and so is a newly measured slowest job written into the comment but
   not into SERVED_RUNS. The same comment names each measured job of SERVED_RUNS as `run <id>, <s> s` and each lower
   bound as `job <id> (run <id>, attempt <n>), at least <s> s` (BOUND_FORM), the measurements the cap is sized from, so a
   job's figures changed in the comment alone, or a job dropped from it, is red; and each job the comment names in that
   second form must be a lower bound of SERVED_RUNS with the same figures, so a cancelled job dropped from SERVED_RUNS
   while the comment still names it is red, with the floor over SERVED_RUNS and the floor with that job counted. The
   floor is a lower bound, as the extension job's is (tests/test_ci_bats_bound.py::ExtensionJobCeiling): a cap above the
   rule's figure, with its sentence saying so, is green.
A job's key written twice is refused by job_block with the reason (the other module's check 2 states which spellings it
reads).

The caps in the literals. The served job, 80 minutes since 2026-10-06: the slowest job and half again, rounded up to a
multiple of 5, the rule ci.yml's comment states for this job (the expected time and half again, the vendored tooling
job's rule, with the slowest job as the expected time), read over every job, a job cancelled at the cap counted at its
cancel time as a lower bound on its true duration, since leaving it out reads the rule on the miss side (the ruling of
2026-10-06); SERVED_CAP_FLOOR is that rule's figure for SLOWEST_SERVED_JOB_S, and check 4 holds the cap at or above it.
SERVED_RUNS are the jobs the cap was sized from, on the public runner, each with its job id, run, attempt, the seconds
counted and how they are counted. The evidence is the first attempt of run 37390122873 (fork PR 968's checks):
job 112032952459, cancelled at the 50-minute cap, started 23:48:18 UTC on 2026-10-05 and completed 00:38:34 UTC on
2026-10-06, 3016 s, its served step cancelled at 00:38:31; 3016 s and half again is 4524 s, 75 min 24 s, so 80. Two more
were cancelled at that cap: job 110492093901 (run 36898691471, attempt 1) and job 111708325878 (run 37293073638,
attempt 1, fork PR 978's checks). Their records run 3300 s and 3301 s, ending 300 s and 301 s after the cap fired, and
carry no step times and no log: GitHub cancels a job at its timeout-minutes and forcibly terminates a job still running
5 minutes after a cancellation (its documented cancellation timeout), so those five minutes are that wait, which the
records do not show the job running in, and each job is counted at the cap's 3000 s (75 by the rule; at 3300 s it would
give 85). The measured jobs, each the jobs API's startedAt to completedAt: main's push run after batch 970,
run 37340134888, 2991 s, 49 min 51 s (it concluded success); fork PR 977's checks, run 37389629730, 2949 s, 49 min 9 s
(success); and the weekly scheduled run at the same main commit, run 37360905751, 2876 s, 47 min 56 s (the job
succeeded; the run concluded failure for another job). Read at 01:28 UTC on 2026-10-06, ci.yml's runs since the job's
first, on 2026-09-28, hold 265 completed jobs of this name (the jobs API lists 278 records across every run attempt,
filter=all, 13 of them copies of a finished job that a re-run of the run's failed jobs lists again in the later attempt
with the same times and runner; each run's latest attempt alone, the API's default, gives 260): the slowest that
finished is run 37340134888's, which alone would give 75, and of their 24 cancelled jobs the three above were cancelled
at the cap and the others ended sooner, the longest at 2266 s, so none of those moves the floor. The python job's rule
for run 37340134888, its step's 2973 s plus the 600 s per-test timeout plus the 16 s before the step, is 3589 s, about
59 min 49 s, 1211 s under 80. Until 2026-10-05 the cap was 50, the expected time and half again from the step's own
time: the step's 1930 s in run 36388144219 and about 16 s of setup were about 32 min 30 s, and half again about
49 minutes; 50 then also covered the phase plus the 600 s per-test timeout plus setup (about 42 min 30 s) and the three
PRs above together (about 329 s more, a job of about 37 min 55 s). On 2026-10-05 it was set to 60, the slowest job then
measured, 49 min 11 s in run 37212676524, plus 10 minutes (the Shell job's rule); on 2026-10-06 to 75 for a few hours,
the slowest job that finished and half again, since 60 left too little room as the suite grows, and then to 80, when the
rule came to read the cancelled jobs too. The vscode-extension job, 17 minutes: without
the served step it took 4 min 45 s on main's run 36555049532 at 6dd80a6e7, the first run on main after the move (about
4 min 12 s was expected from the steps before the served step at 1d591384e). The job's comment in ci.yml sizes the cap for
a head that rosters the legs open PRs are known to add, with a Browser legs bound of about that step's time and half
again; the Browser legs step's comment recorded the same run when the cap was sized, and tools/ci-browser-legs.test.mjs
derives that step's margin from the step's record and this cap.

Not held here: the served step's pytest invocation is also read by tests/test_ci_sdk_pin.py (the flag, the switch's
listing and its premises, keyed on this job and the step's name) and its globs, the module its pytest line names by file
and the two-host lab's knob in its env by tests/test_served_labs_under_ci.py; the Browser legs step's margin by
tools/ci-browser-legs.test.mjs; the extension job's cap floor by tests/test_ci_bats_bound.py::ExtensionJobCeiling.

EachCheckRedsOnItsDefect runs every check against a synthetic workflow built from the same constants: green as built, and red
on each change it plants, so a check that stopped reading would be red there."""
import collections
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the one import from a sibling module, as tests/test_bats_bare_negation.py does
sys.path.insert(0, ROOT)
from tests.test_ci_vendored_job import (WorkflowShape, _diff, check_name_once, content, job_block, lines, raw,  # noqa: E402
                                        workflow_texts)

SERVED_JOB = "served-pages"
EXTENSION_JOB = "vscode-extension"
SERVED_STEP = "Browser-backed served-page tests (pytest)"
# The served-pages job's name up to its runner label: the text check 3 finds on one content line, so a twin that writes the
# runner slot as an expression (`Served pages (pytest, ${{ matrix.os }})`, the vendored-tooling job's style), which GitHub
# shows under the same check name, is read too.
SERVED_NAME_TEXT = "Served pages (pytest, "
# One served-pages job the cap's rule reads: its job id, its run, the run's attempt, the seconds the rule counts, and how
# they are counted. MEASURED: the job finished (success or failure), and its seconds are the jobs API's startedAt to
# completedAt. LOWER_BOUND: the job was cancelled at the cap, and its seconds are the run time its record supports, a lower
# bound on how long the job would have taken.
ServedJob = collections.namedtuple("ServedJob", "job run attempt secs counted")
MEASURED, LOWER_BOUND = "measured", "lower bound"
# The jobs the served-pages job's cap is sized from, all on the public runner. The rule reads every job, a cancelled one at
# its counted time (the ruling of 2026-10-06: a job left out because it was cancelled reads the rule on the miss side).
SERVED_RUNS = (
    # main's push run after batch 970 (it concluded success), the slowest of the jobs of this name that finished in
    # ci.yml's runs from the job's first, on 2026-09-28, to 01:28 UTC on 2026-10-06
    ServedJob(111864826682, 37340134888, 1, 2991, MEASURED),
    # fork PR 977's checks (success)
    ServedJob(112031359744, 37389629730, 1, 2949, MEASURED),
    # the weekly scheduled run at main's same commit (the job succeeded; the run concluded failure for another job)
    ServedJob(111934957877, 37360905751, 1, 2876, MEASURED),
    # fork PR 968's checks, cancelled at the 50-minute cap: started 23:48:18 UTC on 2026-10-05, completed 00:38:34 UTC on
    # 2026-10-06, its served step cancelled at 00:38:31; counted at its cancel time, startedAt to completedAt
    ServedJob(112032952459, 37390122873, 1, 3016, LOWER_BOUND),
    # cancelled at the 50-minute cap; the record runs 3300 s, 300 s past the cap, GitHub's documented 5-minute cancellation
    # timeout, with no step times and no log, so it is counted at the cap's 3000 s
    ServedJob(110492093901, 36898691471, 1, 3000, LOWER_BOUND),
    # fork PR 978's checks, the same: its record runs 3301 s, and it is counted at the cap's 3000 s
    ServedJob(111708325878, 37293073638, 1, 3000, LOWER_BOUND),
)


def served_runs_faults(runs):
    """The reasons `runs` cannot be read as the jobs the rule reads, or none: no job at all, a record that is not five
    fields (job, run, attempt, seconds, how counted), a job id, run id, attempt or seconds that is not a positive integer,
    a way of counting that is neither MEASURED nor LOWER_BOUND, or a job id given twice. Missing data is red, never a job
    left out of the floor."""
    if not runs:
        return ["no served-pages job is recorded, so the rule has no time to read: SERVED_RUNS holds the jobs the cap is "
                "sized from"]
    faults, seen = [], set()
    for r in runs:
        if not isinstance(r, tuple) or len(r) != 5:
            faults.append("the record %r is not five fields (job, run, attempt, seconds, how counted)" % (r,))
            continue
        job, run, attempt, secs, counted = r
        for field, value in (("job id", job), ("run id", run), ("attempt", attempt), ("seconds", secs)):
            if type(value) is not int or value < 1:
                faults.append("the record %r has a %s that is not a positive integer (%r)" % (r, field, value))
        if counted not in (MEASURED, LOWER_BOUND):
            faults.append("the record %r is counted as %r, where the rule reads %r or %r" % (r, counted, MEASURED,
                                                                                        LOWER_BOUND))
        if job in seen:
            faults.append("the job %r is recorded twice" % (job,))
        seen.add(job)
    return faults


_RUNS_FAULTS = served_runs_faults(SERVED_RUNS)
if _RUNS_FAULTS:
    raise ValueError("SERVED_RUNS cannot be read: " + "; ".join(_RUNS_FAULTS))


def slowest_counted(runs):
    """The longest time among `runs`, every job, a cancelled one at its counted time."""
    return max(r[3] for r in runs)


# The slowest time the rule counts, 50 min 16 s, the cancelled job of run 37390122873's first attempt, a lower bound: the
# expected time the rule takes.
SLOWEST_SERVED_JOB_S = slowest_counted(SERVED_RUNS)


def rule_floor(secs):
    """The rule's figure in minutes for a job of `secs` seconds: that time and half again, rounded up to a multiple of 5
    minutes (300 s), the rule ci.yml's comment states for this job. Three times the seconds over 600 is the same quotient
    as one and a half times them over 300, kept in integers: 3016 s gives 4524 s, so 80."""
    return 5 * -(-(secs * 3) // 600)


# The rule's figure for the slowest time it counts, over every job, the floor check 4 holds the cap to: 80.
SERVED_CAP_FLOOR = rule_floor(SLOWEST_SERVED_JOB_S)
# The sentence of the job's comment that works the rule's arithmetic: the slowest job's time, that time and half again
# (whose seconds end in .5 when the first time's seconds are odd), and the cap after "so".
RULE_SENTENCE = re.compile(r"(\d+) min (\d+) s and half again is (\d+) min (\d+)(\.5)? s, so (\d+)\.")
# How the job's comment names a job counted as a lower bound: `job <id> (run <id>, attempt <n>), at least <s> s`. Check 4
# reads it both ways: each LOWER_BOUND record named so, and each job named so recorded in SERVED_RUNS with those figures.
BOUND_FORM = re.compile(r"job (\d+) \(run (\d+), attempt (\d+)\), at least (\d+) s")


def name_in_comment(r):
    """A record as the job's comment names it: a measured job as `run <id>, <s> s`, a lower bound as BOUND_FORM writes it."""
    if r[4] == MEASURED:
        return "run %d, %d s" % (r[1], r[3])
    return "job %d (run %d, attempt %d), at least %d s" % (r[0], r[1], r[2], r[3])


def half_seconds_text(halves):
    """A time given in half seconds as the comment writes it, `<m> min <s> s`, its seconds ending in .5 when the count is
    odd: 8973 half seconds (2991 s and half again) is `74 min 46.5 s`."""
    m, rest = divmod(halves, 120)
    return "%d min %d%s s" % (m, rest // 2, ".5" if rest % 2 else "")
# The setup both jobs run before their own steps: the checkout and node with its npm cache, then npm ci.
_SETUP = (
    "    defaults:",
    "      run:",
    "        working-directory: vscode-extension",
    "    steps:",
    "      - uses: actions/checkout@v4",
    "      - uses: actions/setup-node@v4",
    "        with:",
    "          node-version: '22'",
    "          cache: npm",
    "          cache-dependency-path: vscode-extension/package-lock.json",
    "      - name: Install deps",
    "        run: npm ci",
)
# The Playwright browser cache and the pinned Chromium, in both jobs.
_CHROMIUM = (
    "      - name: Cache Playwright's browsers",
    "        uses: actions/cache@v4",
    "        with:",
    "          path: ~/.cache/ms-playwright",
    "          key: playwright-chromium-${{ runner.os }}-${{ hashFiles('vscode-extension/package-lock.json') }}",
    "      - name: Install the pinned Playwright Chromium",
    "        timeout-minutes: 5",
    "        run: npx playwright install chromium",
)
# The served-pages job as ci.yml writes it, comment-only lines removed and nothing else changed, one line per item: the key
# line, the job's keys, its steps, and the empty text after the file's last line feed (the job is the file's last).
EXPECTED_SERVED_JOB = (
    "  served-pages:",
    "    name: " + SERVED_NAME_TEXT + "ubuntu-latest)",
    "    runs-on: ubuntu-latest",
    "    timeout-minutes: 80",
) + _SETUP + _CHROMIUM + (
    "      - uses: actions/setup-python@v5",
    "        with:",
    "          python-version: '3.12'",
    "      - name: " + SERVED_STEP,
    "        working-directory: ${{ github.workspace }}",
    "        env:",
    '          ROMP_SERVED_TESTS_REQUIRE: "1"',
    "          ROMP_SERVED_TESTS_ENGINES: chromium",
    '          ROMP_CORNER_TWO_HOSTS: "1"',
    "        run: |",
    "          python -m pip install --upgrade pip pytest pytest-timeout cryptography",
    "          python -m pytest tests/test_*_browser.py tests/test_*_served.py tests/test_relay_dial_declares_held_pair.py "
    "-q -rs -p no:cacheprovider -p no:anyio --durations=20 --timeout=600 --timeout-method=thread",
    "",
)
# The vscode-extension job as ci.yml writes it, read the same way, down to the blank line before the served-pages job.
EXPECTED_EXTENSION_JOB = (
    "  vscode-extension:",
    "    name: vscode-extension (typecheck + test + build)",
    "    runs-on: ubuntu-latest",
    "    timeout-minutes: 17",
) + _SETUP + (
    "      - name: Typecheck",
    "        run: npm run typecheck",
    "      - name: Test",
    "        run: npm test",
    "      - name: PDF renderer dependency smoke test (node --test)",
    "        working-directory: ${{ github.workspace }}",
    "        run: node --test tools/pdf-smoke.test.mjs",
    "      - name: Build",
    "        run: npm run build",
) + _CHROMIUM + (
    "      - name: Browser legs (node --test over ci-browser-legs.txt)",
    "        timeout-minutes: 5",
    "        env:",
    '          ROMP_BROWSER_LEGS_REQUIRE: "1"',
    "        run: bash scripts/ci-browser-legs.sh",
    "      - name: Dashboard pane bench (node --test)",
    "        working-directory: ${{ github.workspace }}",
    "        env:",
    '          ROMP_UI_BENCH_REQUIRE: "1"',
    "        run: node --test tests/ui-bench.test.mjs",
    "",
)


def _job_equals(key, want, name, src):
    """A job's block, comment-only lines removed, against the literal `want` (its constant's `name`)."""
    try:
        block = content(job_block(key, lines(src)))
    except WorkflowShape as e:
        return [str(e)]
    return [] if block == list(want) else _diff(want, block, name)


def check_served_job(src):
    """Check 1: the served-pages job's block against EXPECTED_SERVED_JOB."""
    return _job_equals(SERVED_JOB, EXPECTED_SERVED_JOB, "EXPECTED_SERVED_JOB", src)


def check_extension_job(src):
    """Check 2: the vscode-extension job's block against EXPECTED_EXTENSION_JOB."""
    return _job_equals(EXTENSION_JOB, EXPECTED_EXTENSION_JOB, "EXPECTED_EXTENSION_JOB", src)


def check_served_name_once_in(src):
    """Check 3 over one workflow text, the synthetic workflow's form of it."""
    return check_name_once(SERVED_NAME_TEXT, [("ci.yml", src)])


def check_served_cap_floor(src, runs=SERVED_RUNS):
    """Check 4: `runs` (SERVED_RUNS but in this module's plants) whole; the served-pages job's one plain cap line at or above
    the rule's figure for the slowest of `runs`, every job, a cancelled one at its counted time; the one RULE_SENTENCE in
    the job's comment before that line naming that time, that time and half again, and the cap; each of `runs` named in
    that comment (name_in_comment); and each job the comment names in BOUND_FORM recorded in `runs` with its figures."""
    faults = served_runs_faults(runs)
    if faults:
        return faults
    slowest = slowest_counted(runs)
    floor = rule_floor(slowest)
    try:
        block = job_block(SERVED_JOB, lines(src))
    except WorkflowShape as e:
        return [str(e)]
    caps = [l for l in content(block) if re.match(r"    [^ \t]", l) and "timeout" in l.lower()]
    m = re.fullmatch(r"    timeout-minutes: (\d+)", caps[0]) if len(caps) == 1 else None
    if not m:
        return ["the served-pages job's cap lines are %r, where check 4 reads one line, `    timeout-minutes: ` and digits "
                "alone" % (caps,)]
    cap = int(m.group(1))
    if cap < floor:
        faults.append("the served-pages job's cap is %d minutes, under the rule's %d for the slowest time it counts over "
                      "every job, a cancelled one at its counted time (%d s and half again, rounded up to a multiple of 5 "
                      "minutes)" % (cap, floor, slowest))
    comment = " ".join(l.strip(" \t")[1:].strip(" \t") for l in block[:block.index(caps[0])]
                       if l.lstrip(" \t").startswith("#"))
    for r in runs:
        if name_in_comment(r) not in comment:
            faults.append("the served-pages job's comment before its cap line does not name the %s job %d of run %d as "
                          "`%s`: a job the cap is sized from is stated in the comment, with SERVED_RUNS' figures"
                          % (r[4], r[0], r[1], name_in_comment(r)))
    recorded = {(r[0], r[1], r[2], r[3]) for r in runs if r[4] == LOWER_BOUND}
    for named in BOUND_FORM.findall(comment):
        job, run, attempt, secs = (int(x) for x in named)
        if (job, run, attempt, secs) not in recorded:
            with_it = rule_floor(max(slowest, secs))
            faults.append("the served-pages job's comment names job %d (run %d, attempt %d), at least %d s, a lower bound "
                          "the rule reads, and the jobs check 4 reads do not record it with those figures: the floor over "
                          "them is %d minutes, and %d with that job counted" % (job, run, attempt, secs, floor, with_it))
    said = RULE_SENTENCE.findall(comment)
    if len(said) != 1:
        faults.append("the served-pages job's comment before its cap line holds %d sentences `<m> min <s> s and half again "
                      "is <m> min <s> s, so <N>.`, where check 4 reads one" % len(said))
        return faults
    m1, s1, m2, s2, half, n = said[0]
    first, second = int(m1) * 60 + int(s1), (int(m2) * 60 + int(s2)) * 2 + (1 if half else 0)
    if first != slowest:
        faults.append("the comment's slowest time is %s min %s s, not the slowest of SERVED_RUNS, every job, a cancelled "
                      "one at its counted time (%d s): a job measured or cancelled since changes SERVED_RUNS too"
                      % (m1, s1, slowest))
    if second != first * 3:
        faults.append("the comment's product is %s min %s%s s, not %s min %s s and half again (%s)"
                      % (m2, s2, half, m1, s1, half_seconds_text(first * 3)))
    if int(n) != cap:
        faults.append("the comment's sentence ends `so %s.`, and the cap line says %d" % (n, cap))
    return faults


class ServedPagesJob(unittest.TestCase):
    def assertNoFaults(self, faults, why):
        if faults:
            self.fail("%s\n%s" % ("\n".join(faults), why))

    def test_1_the_served_job_equals_the_expected_literal(self):
        self.assertNoFaults(check_served_job(raw()), (
            "The served-pages job in ci.yml, comment-only lines aside, is not EXPECTED_SERVED_JOB (above: the diff and the job "
            "as ci.yml has it, or the reason the job could not be read). Any field of the job can turn a failing or unrun "
            "served suite green (a step's working-directory:, env: or shell:, a step writing GITHUB_ENV before the tests, a "
            "second setup-node or setup-python, a job-level env:, if: or continue-on-error:), so the whole job is held. If the "
            "change is meant, replace EXPECTED_SERVED_JOB in tests/test_ci_served_job.py with the lines printed above and say "
            "in the commit why the job changed."))

    def test_2_the_extension_job_equals_the_expected_literal(self):
        self.assertNoFaults(check_extension_job(raw()), (
            "The vscode-extension job in ci.yml, comment-only lines aside, is not EXPECTED_EXTENSION_JOB (above: the diff and "
            "the job as ci.yml has it, or the reason the job could not be read). The served-page step left this job for a job "
            "of its own (at 1d591384e it took 1930 s of this job's 36 min 22 s under its 40-minute cap); it belongs in the "
            "served-pages job, and a change to any of this job's own steps or its cap changes the literal on purpose: replace "
            "EXPECTED_EXTENSION_JOB in tests/test_ci_served_job.py with the lines printed above and say in the commit why."))

    def test_3_the_served_jobs_name_is_on_one_line_of_the_workflow_files(self):
        self.assertNoFaults(check_name_once(SERVED_NAME_TEXT, workflow_texts()), (
            "The served-pages job's name is not held by exactly one content line of the workflow files (above). A second job "
            "of that name, in ci.yml or in another workflow file, puts a second check of that name beside the job's own, and "
            "one that runs true under it reads green. Rename the other job; if the name itself changed on purpose, update "
            "SERVED_NAME_TEXT, which EXPECTED_SERVED_JOB reads."))

    def test_4_the_served_cap_meets_the_rule_for_the_slowest_job_counted(self):
        self.assertNoFaults(check_served_cap_floor(raw()), (
            "The served-pages job's cap in ci.yml does not meet the rule that sized it, or its comment's arithmetic or its "
            "jobs do not match the cap and SERVED_RUNS (above). The cap is the slowest job and half again, rounded up to a "
            "multiple of 5 (the expected time and half again, the rule ci.yml's comment states for this job), read over "
            "every job, a job cancelled at the cap counted at its cancel time as a lower bound: a cap under it leaves a job "
            "that runs as long as one already did less room than the rule gives. A cap lowered on purpose (the step made "
            "faster, say) measures the job again from runs at the faster head and changes SERVED_RUNS with it, said in the "
            "commit; a slower job measured since, or one cancelled at the cap, joins SERVED_RUNS, and the comment's jobs, "
            "its sentence and the cap change together."))


class EachCheckRedsOnItsDefect(unittest.TestCase):
    """Every check against a synthetic workflow built from the module's constants: green as built, red on each change planted
    into it: a one-field edit in each job, the served step put back in the extension job, a second setup-node in the served
    job, an env on the served step, a step writing GITHUB_ENV before it, a working-directory change, a cap and its comment's
    sentence lowered together under the rule, a job the cap is sized from changed or dropped in the comment, the cancelled
    jobs dropped from the jobs check 4 reads, missing data in them, and the rest below."""
    CHECKS = (check_served_job, check_extension_job, check_served_name_once_in, check_served_cap_floor)
    # The served job's cap line as the literal writes it, and its minutes.
    CAP_LINE = [l for l in EXPECTED_SERVED_JOB if l.startswith("    timeout-minutes: ")][0]
    CAP = int(CAP_LINE.rsplit(" ", 1)[1])
    # The rule's sentence in the synthetic job's comment, folded over two lines as ci.yml's comment may fold it: the
    # slowest job's time, that time and half again, and the cap.
    RULE_LINES = ("    # the rule's arithmetic: %d min %d s and half again is" % divmod(SLOWEST_SERVED_JOB_S, 60),
                  "    #   %s, so %d." % (half_seconds_text(SLOWEST_SERVED_JOB_S * 3), CAP))
    # The jobs the cap is sized from, as the synthetic job's comment names them (name_in_comment), one line each: the
    # measured ones first, the run id and its seconds folded apart on the first as ci.yml's comment may fold them, then
    # the lower bounds, the first folded inside its parenthesis.
    MEASURED_RUNS = tuple(r for r in SERVED_RUNS if r.counted == MEASURED)
    BOUND_RUNS = tuple(r for r in SERVED_RUNS if r.counted == LOWER_BOUND)
    RUN_LINES = (("    # sized from run %d," % MEASURED_RUNS[0].run, "    #   %d s; it concluded success" % MEASURED_RUNS[0].secs)
                 + tuple("    # and run %d, %d s;" % (r.run, r.secs) for r in MEASURED_RUNS[1:]))
    BOUND_LINES = (("    # cancelled at the cap: job %d (run %d," % BOUND_RUNS[0][:2],
                    "    #   attempt %d), at least %d s;" % BOUND_RUNS[0][2:4])
                   + tuple("    # and job %d (run %d, attempt %d), at least %d s;" % r[:4] for r in BOUND_RUNS[1:]))

    @classmethod
    def synthetic(cls):
        ext = list(EXPECTED_EXTENSION_JOB)
        ext[1:1] = ["# a comment at the top level's column", "  # a comment at a job key's column", "    # a comment"]
        ext[-1:-1] = ["        # a comment deeper than the step"]
        served = list(EXPECTED_SERVED_JOB)
        served[4:4] = ["    # a comment before the cap's neighbours"]
        at = served.index(cls.CAP_LINE)
        served[at:at] = list(cls.RUN_LINES + cls.BOUND_LINES + cls.RULE_LINES)
        at = served.index("      - name: " + SERVED_STEP)
        served[at + 1:at + 1] = ["        # the step's own comment"]
        return "\n".join(["name: CI", "on: [push]", "jobs:", "  python:", "    runs-on: ubuntu-latest", ""] + ext + served)

    def plant(self, src, where, anchor, new):
        """src with the one line `anchor` inside `where` (ext, the vscode-extension job's lines, or served, the served-pages
        job's) replaced by the lines `new`; anchor None appends `new` at the end of the file. Fails unless the anchor is
        there exactly once."""
        ls = src.split("\n")
        if anchor is None:
            return "\n".join(ls[:-1] + new + ls[-1:])
        lo, hi = {"ext": (ls.index("  vscode-extension:"), ls.index("  served-pages:")),
                  "served": (ls.index("  served-pages:"), len(ls))}[where]
        at = [i for i in range(lo, hi) if ls[i] == anchor]
        self.assertEqual(len(at), 1, "the plant's anchor %r is in the %s part once" % (anchor, where))
        return "\n".join(ls[:at[0]] + new + ls[at[0] + 1:])

    def test_the_synthetic_workflow_passes_every_check(self):
        src = self.synthetic()
        for check in self.CHECKS:
            self.assertEqual(check(src), [], check.__name__)

    def test_each_plant_reds_its_check(self):
        src = self.synthetic()
        step = "      - name: " + SERVED_STEP
        served_run = [l for l in EXPECTED_SERVED_JOB if l.startswith("          python -m pytest ")][0]
        served_env = "          ROMP_SERVED_TESTS_ENGINES: chromium"
        served_wd = "        working-directory: ${{ github.workspace }}"
        moved = list(EXPECTED_SERVED_JOB[EXPECTED_SERVED_JOB.index("      - uses: actions/setup-python@v5"):-1])
        bench = "        run: node --test tests/ui-bench.test.mjs"
        cap, cap_line = self.CAP, self.CAP_LINE
        rule_1, rule_2 = self.RULE_LINES
        product_min = SLOWEST_SERVED_JOB_S * 3 // 120
        run_secs_line = self.RUN_LINES[1]
        bound_secs_line = self.BOUND_LINES[1]
        first_measured, second_measured = self.MEASURED_RUNS[:2]
        first_bound, second_bound = self.BOUND_RUNS[:2]
        plants = (
            (check_served_cap_floor, "the cap line dropped", "served", cap_line, []),
            (check_served_cap_floor, "the cap quoted, not a plain integer", "served", cap_line,
             ["    timeout-minutes: '%d'" % cap]),
            (check_served_cap_floor, "the cap as an expression", "served", cap_line, ["    timeout-minutes: ${{ %d }}" % cap]),
            (check_served_cap_floor, "the cap with a comment on its line", "served", cap_line, [cap_line + "  # minutes"]),
            (check_served_cap_floor, "a second cap line", "served", "    runs-on: ubuntu-latest",
             ["    runs-on: ubuntu-latest", "    timeout-minutes: %d" % (cap + 30)]),
            (check_served_cap_floor, "the cap lowered alone, under the rule", "served", cap_line,
             ["    timeout-minutes: %d" % (SERVED_CAP_FLOOR - 5)]),
            (check_served_cap_floor, "the cap raised alone, its sentence left behind", "served", cap_line,
             ["    timeout-minutes: %d" % (cap + 5)]),
            (check_served_cap_floor, "the sentence's cap changed alone", "served", rule_2,
             [rule_2.replace("so %d." % cap, "so %d." % (cap + 5))]),
            (check_served_cap_floor, "the sentence's product changed alone, a minute more", "served", rule_2,
             [rule_2.replace("#   %d min" % product_min, "#   %d min" % (product_min + 1))]),
            (check_served_cap_floor, "the sentence's product changed alone, half a second off", "served", rule_2,
             [rule_2.replace(".5 s, so ", " s, so ") if ".5 s, so " in rule_2 else rule_2.replace(" s, so ", ".5 s, so ")]),
            (check_served_cap_floor, "the first measured run's seconds changed in the comment alone", "served",
             run_secs_line, [run_secs_line.replace("#   %d s;" % first_measured.secs, "#   %d s;" % (first_measured.secs + 1))]),
            (check_served_cap_floor, "a run the cap is sized from dropped from the comment", "served", self.RUN_LINES[-1],
             []),
            (check_served_cap_floor, "a run's id changed in the comment alone", "served", self.RUN_LINES[2],
             [self.RUN_LINES[2].replace("run %d" % second_measured.run, "run %d" % (second_measured.run + 1))]),
            (check_served_cap_floor, "the slowest lower bound's seconds changed in the comment alone", "served", bound_secs_line,
             [bound_secs_line.replace("at least %d s;" % first_bound.secs, "at least %d s;" % (first_bound.secs + 1))]),
            (check_served_cap_floor, "a lower bound dropped from the comment", "served", self.BOUND_LINES[-1], []),
            (check_served_cap_floor, "a lower bound's attempt changed in the comment alone", "served", self.BOUND_LINES[2],
             [self.BOUND_LINES[2].replace("attempt %d)" % second_bound.attempt, "attempt %d)" % (second_bound.attempt + 1))]),
            (check_served_cap_floor, "a lower bound's job id changed in the comment alone", "served", self.BOUND_LINES[2],
             [self.BOUND_LINES[2].replace("job %d " % second_bound.job, "job %d " % (second_bound.job + 1))]),
            (check_served_cap_floor, "a lower bound named as a measured job in the comment", "served", self.BOUND_LINES[2],
             ["    # and run %d, %d s;" % (second_bound.run, second_bound.secs)]),
            (check_served_cap_floor, "a job named as a lower bound in the comment and not recorded", "served",
             self.BOUND_LINES[2], [self.BOUND_LINES[2], "    # and job 11 (run 22, attempt 1), at least 3100 s;"]),
            (check_served_cap_floor, "the sentence's slowest job changed alone", "served", rule_1,
             [rule_1.replace(" min ", "0 min ", 1)]),
            (check_served_cap_floor, "the sentence's first half dropped", "served", rule_1, []),
            (check_served_cap_floor, "the sentence written twice", "served", rule_2, [rule_2, rule_1, rule_2]),
            (check_served_cap_floor, "the job's key renamed", "served", "  served-pages:", ["  served-page:"]),
            (check_served_job, "the served cap 80 to 81, a one-field edit", "served", "    timeout-minutes: 80",
             ["    timeout-minutes: 81"]),
            (check_extension_job, "the extension cap 17 to 18, a one-field edit", "ext", "    timeout-minutes: 17",
             ["    timeout-minutes: 18"]),
            (check_extension_job, "the served step put back in the extension job", "ext", bench, [bench] + moved),
            (check_served_job, "a second setup-node in the served job, before the tests", "served", step,
             ["      - uses: actions/setup-node@v4", "        with:", "          node-version: '20'", step]),
            (check_served_job, "an env on the served step", "served", served_env,
             [served_env, "          PYTEST_ADDOPTS: --collect-only"]),
            (check_served_job, "a step writing GITHUB_ENV before the served step", "served", step,
             ['      - run: echo "PYTEST_ADDOPTS=--collect-only" >> "$GITHUB_ENV"', step]),
            (check_served_job, "the served step's working-directory changed", "served", served_wd,
             ["        working-directory: vscode-extension"]),
            (check_served_job, "the served step's working-directory dropped (the job's default then applies)", "served",
             served_wd, []),
            (check_served_job, "the job's default working-directory changed", "served",
             "        working-directory: vscode-extension", ["        working-directory: ."]),
            (check_served_job, "a flag dropped from the pytest line", "served", served_run,
             [served_run.replace(" -p no:anyio", "")]),
            (check_served_job, "a -k added to the pytest line", "served", served_run, [served_run + " -k nothing"]),
            (check_served_job, "the switch dropped from the step's env", "served", '          ROMP_SERVED_TESTS_REQUIRE: "1"', []),
            (check_served_job, "a job-level env:", "served", "    runs-on: ubuntu-latest",
             ["    runs-on: ubuntu-latest", "    env:", "      PYTEST_ADDOPTS: --collect-only"]),
            (check_served_job, "a job-level if: after the steps", "served", served_run, [served_run, "    if: false"]),
            (check_served_job, "a job-level continue-on-error:", "served", "    runs-on: ubuntu-latest",
             ["    runs-on: ubuntu-latest", "    continue-on-error: true"]),
            (check_served_job, "the step's shell:", "served", served_wd, [served_wd, "        shell: true {0}"]),
            (check_served_job, "a step-level continue-on-error:", "served", served_wd, [served_wd, "        continue-on-error: true"]),
            (check_served_job, "a `#` line inside the run block (YAML reads it as text)", "served", served_run,
             ["          # " + served_run.strip()]),
            (check_served_job, "a second trailing line feed", None, None, [""]),
            (check_served_job, "a strategy with fail-fast: true", "served", "    runs-on: ubuntu-latest",
             ["    runs-on: ubuntu-latest", "    strategy:", "      fail-fast: true"]),
            (check_served_job, "the job's key renamed", "served", "  served-pages:", ["  served-page:"]),
            (check_served_job, "the job's key written twice", "ext", "  vscode-extension:",
             ["  'Served-Pages' :", "    runs-on: ubuntu-latest", "  vscode-extension:"]),
            (check_extension_job, "the Browser legs step's env widened", "ext", '          ROMP_BROWSER_LEGS_REQUIRE: "1"',
             ['          ROMP_BROWSER_LEGS_REQUIRE: "1"', "          NODE_OPTIONS: --test-skip-pattern=."]),
            (check_extension_job, "the Test step's working-directory changed", "ext", "        run: npm test",
             ["        working-directory: ${{ github.workspace }}", "        run: npm test"]),
            (check_extension_job, "a step dropped from the extension job", "ext", "        run: npm run build", []),
            (check_extension_job, "a job-level env: in the extension job", "ext", "    runs-on: ubuntu-latest",
             ["    runs-on: ubuntu-latest", "    env:", "      NODE_OPTIONS: --test-skip-pattern=."]),
            (check_served_name_once_in, "a second job named like the served job, before it", "ext", "  vscode-extension:",
             ["  twin:", "    name: Served pages (pytest, ubuntu-latest)", "    runs-on: ubuntu-latest", "    steps:",
              "      - run: true", "", "  vscode-extension:"]),
            (check_served_name_once_in, "a twin whose name is quoted and in another case", "ext", "  vscode-extension:",
             ["  twin:", '    name: "served pages (pytest, ubuntu-latest)"', "    runs-on: ubuntu-latest", "    steps:",
              "      - run: true", "", "  vscode-extension:"]),
            (check_served_name_once_in, "the served job's own name changed", "served", "    name: " + SERVED_NAME_TEXT + "ubuntu-latest)",
             ["    name: Served pages (pytest)"]),
            (check_served_name_once_in, "a twin whose runner slot is an expression", "ext", "  vscode-extension:",
             ["  twin:", "    name: Served pages (pytest, ${{ matrix.os }})", "    runs-on: ubuntu-latest", "    steps:",
              "      - run: true", "", "  vscode-extension:"]),
        )
        for check, label, where, anchor, new in plants:
            with self.subTest(label):
                out = self.plant(src, where, anchor, new)
                self.assertNotEqual(out, src, "the plant landed")
                self.assertNotEqual(check(out), [], "%s: %s is red" % (label, check.__name__))

    def test_check_4_reds_a_cap_lowered_with_its_sentence_on_the_floor_alone(self):
        """The defect check 4 exists for: the cap line and the comment's sentence lowered together, the synthetic form of
        ci.yml and EXPECTED_SERVED_JOB edited together, which check 1 reads as green. The one fault is the floor's, so the
        floor is what reds it: a minute under the floor is red, the floor and a cap above it, each with its sentence, are
        green."""
        rule_2 = self.RULE_LINES[1]
        for minutes, faults in ((SERVED_CAP_FLOOR - 1, 1), (SERVED_CAP_FLOOR - 5, 1), (SERVED_CAP_FLOOR - 15, 1),
                                (SERVED_CAP_FLOOR, 0), (SERVED_CAP_FLOOR + 5, 0)):
            with self.subTest(minutes=minutes):
                out = self.plant(self.synthetic(), "served", self.CAP_LINE, ["    timeout-minutes: %d" % minutes])
                out = self.plant(out, "served", rule_2, [rule_2.replace("so %d." % self.CAP, "so %d." % minutes)])
                got = check_served_cap_floor(out)
                self.assertEqual(len(got), faults, got)
                if faults:
                    self.assertIn("under the rule's %d" % SERVED_CAP_FLOOR, got[0])

    def test_check_4_reds_the_rule_read_on_finished_jobs_alone(self):
        """The defect the 2026-10-06 ruling corrected: the rule read on the jobs that finished, the cancelled ones left
        out, which gave 75 where every job, a cancelled one at its counted time, gives 80. Two plants. The cancelled jobs
        dropped from the jobs check 4 reads, the comment unchanged: red, on the floor's population (each lower bound the
        comment names is missing from them, and the floor over them is 75, under the 80 with them counted) and on the
        sentence's slowest time. The cap and its sentence written for the finished jobs alone (49 min 51 s, so 75), the
        jobs whole: red on the floor, under the rule's 80."""
        finished = tuple(r for r in SERVED_RUNS if r.counted != LOWER_BOUND)
        self.assertEqual(rule_floor(slowest_counted(finished)), 75, "the finished jobs alone give 75")
        self.assertEqual(SERVED_CAP_FLOOR, 80, "every job, a cancelled one at its counted time, gives 80")
        got = check_served_cap_floor(self.synthetic(), runs=finished)
        for r in self.BOUND_RUNS:
            with self.subTest(job=r.job):
                self.assertTrue(any(("names job %d (run %d, attempt %d), at least %d s" % r[:4]) in f
                                    and "the floor over them is 75 minutes" in f for f in got), got)
        self.assertTrue(any("the comment's slowest time is 50 min 16 s" in f for f in got), got)
        rule_1, rule_2 = self.RULE_LINES
        out = self.plant(self.synthetic(), "served", self.CAP_LINE, ["    timeout-minutes: 75"])
        out = self.plant(out, "served", rule_1, ["    # the rule's arithmetic: 49 min 51 s and half again is"])
        out = self.plant(out, "served", rule_2, ["    #   74 min 46.5 s, so 75."])
        got = check_served_cap_floor(out)
        self.assertTrue(any("cap is 75 minutes, under the rule's 80" in f for f in got), got)

    def test_check_4_is_loud_on_missing_data(self):
        """The jobs check 4 reads, whole or red with the reason, never a record skipped or the floor read without it:
        none at all, a record short of a field, a field missing or not a positive integer, a way of counting the rule does
        not know, a job given twice. Each is red from served_runs_faults and from check 4 itself, before the workflow is
        read."""
        whole = list(SERVED_RUNS)
        bound = self.BOUND_RUNS[0]
        broken = (
            ("no job", ()),
            ("a record of four fields", whole[:-1] + [tuple(whole[-1][:4])]),
            ("the seconds missing", whole[:-1] + [whole[-1]._replace(secs=None)]),
            ("the seconds zero", whole[:-1] + [whole[-1]._replace(secs=0)]),
            ("the seconds as text", whole[:-1] + [whole[-1]._replace(secs="3000")]),
            ("the job id missing", whole[:-1] + [whole[-1]._replace(job=None)]),
            ("the attempt zero", whole[:-1] + [whole[-1]._replace(attempt=0)]),
            ("the attempt as a boolean", whole[:-1] + [whole[-1]._replace(attempt=True)]),
            ("the run id missing", whole[:-1] + [whole[-1]._replace(run=None)]),
            ("the way of counting missing", whole[:-1] + [whole[-1]._replace(counted=None)]),
            ("an unknown way of counting", whole[:-1] + [whole[-1]._replace(counted="estimated")]),
            ("a job given twice", whole + [bound]),
        )
        self.assertEqual(served_runs_faults(SERVED_RUNS), [])
        for label, runs in broken:
            with self.subTest(label):
                self.assertNotEqual(served_runs_faults(runs), [], label)
                self.assertEqual(check_served_cap_floor(self.synthetic(), runs=runs), served_runs_faults(runs), label)

    def test_the_rule_floor_and_the_half_seconds(self):
        """The floor's integer arithmetic at its edges: half again landing exactly on a multiple of 5 minutes stays there,
        a second past it moves to the next 5; the ruled figure, 3016 s, gives 80, and 2991 s, the slowest job that
        finished, 75; 3300 s, the record of the two cancelled jobs without step times, would give 85. The comment's
        product reads half seconds."""
        for secs, floor in ((3016, 80), (2991, 75), (3300, 85), (3000, 75), (3001, 80), (2800, 70), (2801, 75), (1, 5),
                            (0, 0)):
            with self.subTest(secs=secs):
                self.assertEqual(rule_floor(secs), floor)
        self.assertEqual(SLOWEST_SERVED_JOB_S, 3016)
        self.assertEqual(SERVED_CAP_FLOOR, rule_floor(SLOWEST_SERVED_JOB_S))
        self.assertEqual(half_seconds_text(3016 * 3), "75 min 24 s")
        self.assertEqual(half_seconds_text(2991 * 3), "74 min 46.5 s")
        self.assertEqual(half_seconds_text(2990 * 3), "74 min 45 s")

    def test_check_4_reads_the_sentence_before_the_cap_line_only(self):
        rule_1, rule_2 = self.RULE_LINES
        out = self.plant(self.synthetic(), "served", rule_1, [])
        out = self.plant(out, "served", rule_2, [])
        self.assertNotEqual(check_served_cap_floor(out), [], "no sentence is red")
        moved = self.plant(out, "served", self.CAP_LINE, [self.CAP_LINE, rule_1, rule_2])
        self.assertIn("holds 0 sentences", " ".join(check_served_cap_floor(moved)), "a sentence after the cap line is not read")

    def test_a_twin_in_another_workflow_file_reds_check_3(self):
        src = self.synthetic()
        other = "\n".join(["name: CI", "on: [push, pull_request]", "jobs:", "  served-pages:", "    name: " + SERVED_NAME_TEXT + "ubuntu-latest)",
                           "    runs-on: ubuntu-latest", "    steps:", "      - run: true", ""])
        self.assertEqual(check_name_once(SERVED_NAME_TEXT, [("ci.yml", src), ("docs.yml", "name: Docs\non: [push]\n")]), [])
        for label, texts in (("a same-named job in a second workflow file", [("ci.yml", src), ("twin.yml", other)]),
                             ("the same, in a .yaml file", [("ci.yml", src), ("twin.yaml", other)])):
            with self.subTest(label):
                self.assertNotEqual(check_name_once(SERVED_NAME_TEXT, texts), [], label)

    def test_each_foreign_line_break_reds_every_check(self):
        src = self.synthetic()
        for ch, name in (("\r", "CR"), ("\x85", "U+0085"), ("\u2028", "U+2028"), ("\u2029", "U+2029")):
            out = src.replace("    # a comment before the cap's neighbours\n",
                              "    # a comment before the cap's neighbours%s    if: false\n" % ch, 1)
            with self.subTest(name):
                self.assertNotEqual(out, src, "the plant landed")
                for check in self.CHECKS:
                    self.assertNotEqual(check(out), [], check.__name__)

    def test_the_block_reading(self):
        ls = self.synthetic().split("\n")
        self.assertEqual(content(job_block(SERVED_JOB, ls)), list(EXPECTED_SERVED_JOB),
                         "comments removed; the run block's lines kept; the block ends with the empty text after the last "
                         "line feed")
        self.assertEqual(content(job_block(EXTENSION_JOB, ls)), list(EXPECTED_EXTENSION_JOB),
                         "the extension block ends at the served job's key line, with the blank line before it")
        self.assertEqual(EXPECTED_SERVED_JOB[-1], "", "the served job's literal ends with the empty text after the file's "
                         "last line feed")


if __name__ == "__main__":
    unittest.main()
