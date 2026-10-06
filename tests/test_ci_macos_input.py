#!/usr/bin/env python3
"""A manual run of CI is Linux alone unless its macos input is true (.github/workflows/ci.yml, 2026-10-05).

Until 2026-10-05 every manual run (workflow_dispatch) ran the macOS cells beside the Linux jobs. On the private
repository every run is billed, and the macOS cells bill at about ten times the Linux rate: about 8 dollars of macOS
minutes a dispatch by ci.yml's header figures, against about 3 dollars for a run's Linux jobs. So workflow_dispatch
declares a boolean input, macos, off by default, and each matrix job's os: expression selects macOS on a dispatch only
when the input is true. A batch push never selects it, and since 2026-10-06 neither does the schedule event, live under
the smaller shape alone (tests/test_ci_macos_schedule.py holds the weekly macOS run paused in both shapes). The reason is
cost control, as for the paused weekly macOS run; ci.yml's on: block says so and says how to ask for the macOS cells.

Pins, over ci.yml's text, read with tests/test_ci_workflow_concurrency.py's readers (no YAML library in the test deps):
1. THE INPUT: workflow_dispatch declares `macos`, with `type: boolean`, `default: false` (YAML's plain false; a quoted
   'false' is a string, which a GitHub expression reads as true) and a description (dispatch_inputs).
2. THE GATE: each matrix job's os: expression (MATRIX_JOBS), evaluated for a dispatch whose inputs are filled as
   GitHub fills them, each at its declared default (dispatch_run), gives Linux alone; with macos true, Linux and macOS;
   with macos false, Linux alone; and on a batch push, Linux alone. The default case reads the default from the file,
   so it is red on a default turned to true as well as on an expression that does not read the input.
3. THE RELEASE GATE: scripts/release.sh's macOS gate dispatches CI and refuses to tag unless that run passes. Without
   the input the run is Linux alone and the gate would pass with no macOS cell run, so the script's one dispatch
   passes `-f macos=true`, the input's name read from the declaration (tests/release-sh.bats holds the command the
   script runs, through its stubbed gh).
At the commit before the input, 1 and 3 are red (no input is declared, and the script passes none) and so is 2's
default case (a dispatch selected macOS); TheReadersThemselves runs the pins' readers over that workflow's shape."""
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the import from a sibling module, as tests/test_ci_macos_schedule.py does
sys.path.insert(0, ROOT)
from tests.test_ci_workflow_concurrency import (  # noqa: E402
    BATCH_X, MAIN, MATRIX_JOBS, SHA_A, dispatch_inputs, dispatch_run, matrix_os, os_list, run)

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
RELEASE = os.path.join(ROOT, "scripts", "release.sh")
INPUT = "macos"
LINUX = ["ubuntu-latest"]
BOTH = ["macos-latest", "ubuntu-latest"]


def runners(src, ctx):
    """{matrix job: its runner labels, sorted} for each of MATRIX_JOBS: the os: expression evaluated in ctx, joined with
    every include: entry's os."""
    out = {}
    for job in MATRIX_JOBS:
        expr, includes = matrix_os(src, job)
        out[job] = sorted(set(os_list(expr, ctx)) | set(includes))
    return out


def release_dispatch_lines(path=RELEASE):
    """The lines of the release script that dispatch a workflow through its gh ("$GH" workflow run), stripped, comment
    lines aside."""
    with open(path, encoding="utf-8") as fh:
        return [l.strip() for l in fh if not l.lstrip().startswith("#") and re.search(r'"\$GH" workflow run\b', l)]


def dispatches_with_input_on(line, name):
    """Whether a release script's dispatch line runs the CI workflow with the input `name` set to true."""
    return re.search(r'"\$GH" workflow run CI\b.* -f %s=true(?:\s|$)' % re.escape(name), line) is not None


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TheInput(unittest.TestCase):
    def test_the_dispatch_declares_a_boolean_macos_input_off_by_default(self):
        inputs = dispatch_inputs(_read(WF))
        self.assertIn(INPUT, inputs, "workflow_dispatch declares no %r input (it declares %r): a manual run would run the "
                                     "macOS cells on every dispatch, about 8 dollars of macOS minutes each"
                                     % (INPUT, sorted(inputs)))
        fields = inputs[INPUT]
        self.assertEqual(fields.get("type"), "boolean", "the %s input is a boolean, a box in the Run workflow form" % INPUT)
        self.assertIs(fields.get("default"), False, "the %s input defaults to YAML's plain false, so a dispatch that does "
                                                    "not ask for macOS runs Linux alone (a quoted 'false' is a string, "
                                                    "which an expression reads as true): %r" % (INPUT, fields.get("default")))
        self.assertTrue(fields.get("description"), "the %s input says what it does in the Run workflow form" % INPUT)


class TheGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = _read(WF)

    def test_a_dispatch_at_its_defaults_runs_linux_alone(self):
        for ref in (MAIN, BATCH_X):
            with self.subTest(ref=ref):
                self.assertEqual(runners(self.src, dispatch_run(self.src, ref, SHA_A)), {job: LINUX for job in MATRIX_JOBS},
                                 "a dispatch whose macos input is left at its default runs every matrix job on Linux alone")

    def test_a_dispatch_with_macos_on_adds_macos_to_every_matrix_job(self):
        for ref in (MAIN, BATCH_X):
            with self.subTest(ref=ref):
                self.assertEqual(runners(self.src, dispatch_run(self.src, ref, SHA_A, **{INPUT: True})),
                                 {job: BOTH for job in MATRIX_JOBS},
                                 "a dispatch with the macos input on runs each matrix job on Linux and macOS")

    def test_a_dispatch_with_macos_off_runs_linux_alone(self):
        self.assertEqual(runners(self.src, dispatch_run(self.src, MAIN, SHA_A, **{INPUT: False})),
                         {job: LINUX for job in MATRIX_JOBS})

    def test_a_batch_push_runs_linux_alone(self):
        self.assertEqual(runners(self.src, run("push", BATCH_X, SHA_A)), {job: LINUX for job in MATRIX_JOBS})


class TheReleaseGate(unittest.TestCase):
    def test_the_release_script_dispatches_with_the_input_on(self):
        self.assertIn(INPUT, dispatch_inputs(_read(WF)), "the input the release script names is the one ci.yml declares")
        lines = release_dispatch_lines()
        self.assertEqual(len(lines), 1, "scripts/release.sh dispatches CI once, its macOS gate: %r" % lines)
        self.assertTrue(dispatches_with_input_on(lines[0], INPUT),
                        "scripts/release.sh's macOS gate dispatches CI without -f %s=true, so the run it waits on is Linux "
                        "alone and the gate passes with no macOS cell run: %r" % (INPUT, lines[0]))


def _synthetic(dispatch, expr):
    """A workflow with a batch push trigger, the dispatch lines `dispatch` and each of MATRIX_JOBS on the os: expression
    `expr`."""
    jobs = "".join("  %s:\n    runs-on: ${{ matrix.os }}\n    strategy:\n      matrix:\n        os: %s\n    steps:\n"
                   "      - run: true\n" % (job, expr) for job in MATRIX_JOBS)
    return "name: CI\non:\n  push:\n    branches: ['batch/**']\n" + dispatch + "jobs:\n" + jobs


class TheReadersThemselves(unittest.TestCase):
    """The pins' readers over synthetic workflows: the shape before the input (no input, a dispatch selects macOS), the
    shape after it, a default of true, a quoted 'false', an undeclared input, and a release script that passes none."""
    BEFORE_EXPR = ("${{ fromJSON((github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && "
                   "'[\"ubuntu-latest\",\"macos-latest\"]' || '[\"ubuntu-latest\"]') }}")
    # the expression as ci.yml writes it since 2026-10-06, when the schedule clause left it
    AFTER_EXPR = ("${{ fromJSON((github.event_name == 'workflow_dispatch' && inputs.macos) && "
                  "'[\"ubuntu-latest\",\"macos-latest\"]' || '[\"ubuntu-latest\"]') }}")
    BEFORE_DISPATCH = "  workflow_dispatch:   # the manual on-switch for the macOS cells\n"
    AFTER_DISPATCH = ("  workflow_dispatch:\n    # a comment\n    inputs:\n      macos:\n        description: 'Also run the "
                      "macOS cells'\n        type: boolean\n        default: false\n")

    def test_the_shape_before_the_input_is_red_on_the_input_and_the_default_dispatch(self):
        src = _synthetic(self.BEFORE_DISPATCH, self.BEFORE_EXPR)
        self.assertEqual(dispatch_inputs(src), {})
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A)), {job: BOTH for job in MATRIX_JOBS})
        with self.assertRaises(LookupError):
            dispatch_run(src, MAIN, SHA_A, **{INPUT: True})

    def test_the_shape_after_it_reads_as_the_pins_want(self):
        src = _synthetic(self.AFTER_DISPATCH, self.AFTER_EXPR)
        self.assertEqual(dispatch_inputs(src), {INPUT: {"description": "Also run the macOS cells", "type": "boolean",
                                                        "default": False}})
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A)), {job: LINUX for job in MATRIX_JOBS})
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A, **{INPUT: True})), {job: BOTH for job in MATRIX_JOBS})

    def test_a_default_of_true_runs_macos_on_a_default_dispatch(self):
        src = _synthetic(self.AFTER_DISPATCH.replace("default: false", "default: true"), self.AFTER_EXPR)
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A)), {job: BOTH for job in MATRIX_JOBS})

    def test_an_expression_that_does_not_read_the_input_is_seen(self):
        src = _synthetic(self.AFTER_DISPATCH, self.BEFORE_EXPR)
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A)), {job: BOTH for job in MATRIX_JOBS})

    def test_a_quoted_false_is_a_string(self):
        src = _synthetic(self.AFTER_DISPATCH.replace("default: false", "default: 'false'"), self.AFTER_EXPR)
        self.assertEqual(dispatch_inputs(src)[INPUT]["default"], "false")
        self.assertEqual(runners(src, dispatch_run(src, MAIN, SHA_A)), {job: BOTH for job in MATRIX_JOBS},
                         "a non-empty string is true in an expression, so a quoted default turns the macOS cells on")

    def test_an_input_line_the_reader_does_not_read_is_refused(self):
        src = _synthetic(self.AFTER_DISPATCH + "        options:\n          - a\n", self.AFTER_EXPR)
        with self.assertRaises(LookupError):
            dispatch_inputs(src)

    def test_the_release_line_reader(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "release.sh")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('# "$GH" workflow run CI in a comment\n'
                         '    "$GH" workflow run CI --ref "$REF" || die "could not dispatch the CI workflow."\n')
            lines = release_dispatch_lines(path)
        self.assertEqual(lines, ['"$GH" workflow run CI --ref "$REF" || die "could not dispatch the CI workflow."'])
        self.assertFalse(dispatches_with_input_on(lines[0], INPUT))
        self.assertTrue(dispatches_with_input_on('"$GH" workflow run CI --ref "$REF" -f macos=true || die "x"', INPUT))
        self.assertFalse(dispatches_with_input_on('"$GH" workflow run CI --ref "$REF" -f macos=false', INPUT))
        self.assertFalse(dispatches_with_input_on('"$GH" workflow run CI --ref "$REF" -f macos=trueish', INPUT))


if __name__ == "__main__":
    unittest.main()
