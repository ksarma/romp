#!/usr/bin/env python3
"""The served-page tests run in a CI job of their own, with their own cap (.github/workflows/ci.yml, 2026-09-28).

The step "Browser-backed served-page tests (pytest)" ran last in the vscode-extension job. At the fork's main 1d591384e
(run 36388144219) that job took 36 min 22 s of its 40-minute cap: the served step 1930 s, the steps before it 250 s. Fork
PRs 821, 857 and 860 each add served labs (about 205 s, 90 s and 90 s): 821 with either of the others in one batch would
have run the job past its cap, and 857 with 860 would have left it 38 s. Raising the cap was declined, since it would hide the growth; the step moved to a job of its own,
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
   run block, and the cap (50). The block runs from the job's key line to the next line that starts, after none or two
   spaces, with a character other than a blank or `#`, or to the end of the file: this job is the file's last, as
   tests/test_ci_sdk_pin.py requires (it appends synthetic steps at the end of the file and reads them as the served step's
   job's), so its block ends with the empty text after the file's last line feed, and a second trailing line feed is red.
   The served step's run block is a block scalar; content() keeps every line inside one, a `#` line included, since YAML
   reads it as the scalar's text.
2. The vscode-extension job's block, read the same way, EQUALS EXPECTED_EXTENSION_JOB: the steps it kept (Install deps
   through the Dashboard pane bench) and its cap (40), so the served step put back, or any field of any of its steps
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
A job's key written twice is refused by job_block with the reason (the other module's check 2 states which spellings it
reads).

The caps in the literals. The served job, 50 minutes: the expected time and half again, the vendored tooling job's rule.
The step took 1930 s at 1d591384e (1899 s on the fork's run 36425690821 of 2026-09-28, still in the extension job then),
and the setup the job repeats took about 16 s on main's run (the checkout 6 s, node 1 s, npm ci 3 s, the cache 3 s, Chromium
1 s, and the job's own set-up and post steps; 22 s on run 36425690821), so the job is about 32 min 30 s and half again about
49 minutes. 50 also covers the step's other rule, the phase plus the 600 s per-test timeout plus setup (about 42 min 30 s), and
the three PRs above together (about 385 s more, a job of about 38 min 50 s). The vscode-extension job, 40 minutes, kept: the
job without the served step is about 4 min 12 s (the steps before it took 250 s at 1d591384e and its post steps about 2 s;
4 min 18 s on run 36425690821), but the Browser legs step's
comment records the job at a head where it still ran the served step, and tools/ci-browser-legs.test.mjs derives that
step's margin from that record and this cap, so the cap is re-read once a run on main of the job without the served step
measures it, and the literal changes with it.

Not held here: the served step's pytest invocation is also read by tests/test_ci_sdk_pin.py (the flag, the switch's
listing and its premises, keyed on this job and the step's name) and its globs, the module its pytest line names by file
and the two-host lab's knob in its env by tests/test_served_labs_under_ci.py; the Browser legs step's margin by
tools/ci-browser-legs.test.mjs; the extension job's cap floor by tests/test_ci_bats_bound.py::ExtensionJobCeiling.

EachCheckRedsOnItsDefect runs every check against a synthetic workflow built from the same constants: green as built, and red
on each change it plants, so a check that stopped reading would be red there."""
import os
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
    "    timeout-minutes: 50",
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
    "    timeout-minutes: 40",
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


class EachCheckRedsOnItsDefect(unittest.TestCase):
    """Every check against a synthetic workflow built from the module's constants: green as built, red on each change planted
    into it: a one-field edit in each job, the served step put back in the extension job, a second setup-node in the served
    job, an env on the served step, a step writing GITHUB_ENV before it, a working-directory change, and the rest below."""
    CHECKS = (check_served_job, check_extension_job, check_served_name_once_in)

    @staticmethod
    def synthetic():
        ext = list(EXPECTED_EXTENSION_JOB)
        ext[1:1] = ["# a comment at the top level's column", "  # a comment at a job key's column", "    # a comment"]
        ext[-1:-1] = ["        # a comment deeper than the step"]
        served = list(EXPECTED_SERVED_JOB)
        served[4:4] = ["    # a comment before the cap's neighbours"]
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
        plants = (
            (check_served_job, "the served cap 50 to 51, a one-field edit", "served", "    timeout-minutes: 50",
             ["    timeout-minutes: 51"]),
            (check_extension_job, "the extension cap 40 to 41, a one-field edit", "ext", "    timeout-minutes: 40",
             ["    timeout-minutes: 41"]),
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
