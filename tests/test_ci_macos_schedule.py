"""The weekly macOS run stays paused (.github/workflows/ci.yml, 2026-10-04) until the first month's bill on the private
runner is read, in both shapes of the python job's matrix (2026-10-06); a manual dispatch with its macos input on still runs
the macOS cells (since 2026-10-05 a dispatch is Linux alone by default: tests/test_ci_macos_input.py).

From 2026-09-16 the macOS cells ran on a weekly schedule as well as on a manual dispatch: with the manual switch alone the
release gate was the first macOS run in two weeks and found twenty-nine accumulated failures. On a private repository every
run is billed, and the scheduled run added its Linux jobs and the macOS cells, which bill at about ten times the Linux rate,
every week, so on 2026-10-04 the schedule was commented out. On 2026-10-06 its two lines, the schedule: key and its cron
entry, became lines 1 and 2 of the shape switch (ci.yml's header, THE SHAPE SWITCH; tests/test_ci_shards.py's
ShapeSwitch): both commented under full, the shape as built, and both live under smaller, where the weekly run takes 3.10, 3.11
and 3.13 on Linux. No matrix job's os: expression names the schedule
event any more, so the weekly run, in either shape, takes none of the macOS cells; bringing them back is a change to the
three os: expressions, the user's call once the first month's bill is read.

Pins, each over ci.yml's text, read with tests/test_ci_workflow_concurrency.py's readers (no YAML library in the test deps):
1. NO WEEKLY MACOS: under each shape (with_shape), each matrix job's os: expression, evaluated for the schedule event, gives
   Linux alone. Red at the commit before the switch, whose expressions selected macOS on the schedule.
2. DISPATCH KEPT: workflow_dispatch is a trigger, and each matrix job's os: expression, evaluated for a dispatch with
   its macos input on, gives macos-latest, so such a dispatch still runs the macOS cells beside the Linux ones.
3. THE SCHEDULE LINES: the on: block's schedule: key and its one cron entry (the switch's lines 1 and 2, shape_lines),
   in block form, hold one weekly cron at a fixed minute and hour, the hour scheduled a quiet one Pacific (08:00 to
   13:59 UTC; the run can start hours later, ci.yml's on: block says how late) and the minute off the top of the hour,
   where GitHub delays and drops more scheduled runs. Under full both are commented, the
   on: block has no schedule trigger and no line of the workflow is a live cron entry; under smaller both are live, the
   schedule a trigger with that one entry. Red at the commit before the switch, whose two commented lines held minute 0
   and whose python-version axis had no shape literal for shape_lines to read.
4. The reason stands in the on: block's comments: the weekly macOS run is paused until the first month's bill is read
   (keyed on those words, a spelling pin on the comment; the decision itself is the user's of 2026-10-04)."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the one import from a sibling module, as tests/test_ci_secret_scan.py does
sys.path.insert(0, ROOT)
from tests.test_ci_workflow_concurrency import (  # noqa: E402
    MAIN, MATRIX_JOBS, SHA_A, SHAPES, dispatch_run, matrix_os, os_list, run, set_line, shape_lines, triggers, with_shape)

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
# a live cron entry in block form, anywhere in the workflow
LIVE_CRON = re.compile(r"^[ \t]*- cron:", re.M)
# the switch's lines 1 and 2 with their `# ` (if any) taken off: the schedule: key with nothing after it but a comment,
# and its one cron entry, a double-quoted cron string
SCHEDULE_KEY_LIVE = re.compile(r"^  schedule:(?:[ \t]+#.*)?$")
CRON_VALUE = re.compile(r'^    - cron: "([^"]+)"(?:[ \t]+#.*)?$')


def on_text(src):
    """The on: block as written, comment lines kept: its top-level line to the next top-level line."""
    m = re.search(r"^on:[ \t]*\n(.*?)^(?=\S)", src, re.S | re.M)
    if m is None:
        raise LookupError("no top-level on: block in ci.yml; re-anchor this pin")
    return m.group(1)


def schedule_cron(src):
    """(the cron string of the switch's line 2, "live" or "commented", the state of both schedule lines). Raises
    LookupError when the two lines are not a schedule: key with nothing after it but a comment and its one cron entry,
    `    - cron: "<cron>"`, or when one is live and the other commented."""
    lines = shape_lines(src)
    (kk, key_state), (kc, cron_state) = lines["schedule"], lines["cron"]
    if key_state != cron_state:
        raise LookupError("the schedule: key is %s and its cron entry %s; the two are commented or live together"
                          % (key_state, cron_state))
    ls = src.split("\n")
    live = [("  " + ls[k][len("  # "):]) if key_state == "commented" else ls[k] for k in (kk, kc)]
    m = CRON_VALUE.match(live[1])
    if SCHEDULE_KEY_LIVE.match(live[0]) is None or m is None:
        raise LookupError("the schedule lines %r are not `  schedule:` and `    - cron: \"<cron>\"`; re-anchor this pin"
                          % [ls[kk], ls[kc]])
    return m.group(1), key_state


def macos_on(src, event, **inputs):
    """{matrix job: whether its os: expression, evaluated for `event` on main, gives macos-latest}; a workflow_dispatch
    carries `inputs`, every other input at its declared default (dispatch_run)."""
    ctx = dispatch_run(src, MAIN, SHA_A, **inputs) if event == "workflow_dispatch" else run(event, MAIN, SHA_A)
    out = {}
    for job in MATRIX_JOBS:
        expr, _includes = matrix_os(src, job)
        out[job] = "macos-latest" in os_list(expr, ctx)
    return out


class MacosSchedulePaused(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WF, encoding="utf-8") as fh:
            cls.wf = fh.read()

    def test_1_the_schedule_selects_no_macos_cell_in_either_shape(self):
        for shape in SHAPES:
            with self.subTest(shape=shape):
                self.assertEqual(macos_on(with_shape(self.wf, shape), "schedule"), {job: False for job in MATRIX_JOBS},
                                 "a matrix job selects macOS on the schedule event under %s; the weekly macOS run is "
                                 "paused until the first month's bill on the private runner is read (2026-10-04)" % shape)

    def test_2_a_dispatch_with_macos_on_still_runs_the_macos_cells(self):
        self.assertIn("workflow_dispatch", triggers(self.wf), "the manual on-switch stays")
        self.assertEqual(macos_on(self.wf, "workflow_dispatch", macos=True), {job: True for job in MATRIX_JOBS},
                         "each matrix job selects macOS on a dispatch with the macos input on, the one road to the "
                         "macOS cells while the weekly macOS run is paused")

    def test_3_the_schedule_lines_hold_one_weekly_cron_at_a_quiet_hour_off_the_top_of_the_hour(self):
        cron, _state = schedule_cron(self.wf)
        minute, hour, dom, month, dow = cron.split()
        self.assertEqual((dom, month), ("*", "*"), "weekly, not monthly")
        self.assertRegex(dow, r"^[0-6]$", "one day of the week")
        self.assertTrue(minute.isdigit() and hour.isdigit(), "a fixed minute and hour")
        self.assertIn(int(hour), range(8, 14), "scheduled for a quiet hour Pacific: 08:00 to 13:59 UTC is about midnight "
                      "to 06:00 Pacific; the start can be hours later (ci.yml's on: block)")
        self.assertNotEqual(int(minute), 0, "off the top of the hour, when GitHub delays and drops more scheduled runs")
        for shape in SHAPES:
            src = with_shape(self.wf, shape)
            with self.subTest(shape=shape):
                self.assertEqual(schedule_cron(src), (cron, "commented" if shape == "full" else "live"))
                if shape == "full":
                    self.assertNotIn("schedule", triggers(src), "under full no scheduled run can start")
                    self.assertEqual(LIVE_CRON.findall(src), [], "under full no line is a live cron entry")
                else:
                    self.assertIn("schedule", triggers(src), "under smaller the weekly run is a trigger")
                    self.assertEqual(len(triggers(src)["schedule"]), 1, "with one cron entry, the switch's line 2")
                    self.assertEqual(len(LIVE_CRON.findall(src)), 1, "under smaller one line is a live cron entry")

    def test_4_the_reason_stands_in_the_on_blocks_comments(self):
        comments = " ".join(l.strip().lstrip("#").strip() for l in on_text(self.wf).split("\n") if l.strip().startswith("#"))
        self.assertIn("paused", comments.lower(), "the on: block's comment says the weekly macOS run is paused")
        self.assertIn("first month's bill", comments, "and until when: the first month's bill on the private runner")


class TheReadersThemselves(unittest.TestCase):
    """schedule_cron and the pins over synthetic workflows: the block before the switch (no shape literal) is refused, the
    switch's two schedule lines are read in each state, and the one-line flow form and a half-flipped pair are refused."""

    OLD = ('name: CI\non:\n  push:\n    branches: [\'batch/**\']\n  workflow_dispatch:\n  # paused until the first month\'s '
           'bill is read\n  # schedule:\n  #   - cron: "0 10 * * 1"   # weekly\njobs:\n  python:\n    strategy:\n      matrix:\n'
           '        python-version: [\'3.10\', \'3.12\']\n')
    NEW = OLD.replace('  # schedule:\n  #   - cron: "0 10 * * 1"   # weekly\n',
                      '  # schedule:   # line 1\n  #   - cron: "17 10 * * 1"   # line 2\n').replace(
        "python-version: ['3.10', '3.12']",
        "python-version: ${{ fromJSON('full' == 'smaller' && '[\"3.12\"]' || '[\"3.10\",\"3.12\"]') }}   # line 3")

    def test_the_old_block_is_refused_and_the_new_lines_read(self):
        with self.assertRaises(LookupError):
            schedule_cron(self.OLD)
        self.assertEqual(schedule_cron(self.NEW), ("17 10 * * 1", "commented"))
        small = with_shape(self.NEW, "smaller")
        self.assertEqual(schedule_cron(small), ("17 10 * * 1", "live"))
        self.assertEqual(triggers(small)["schedule"], ['    - cron: "17 10 * * 1"   # line 2'])
        self.assertEqual(len(LIVE_CRON.findall(small)), 1)
        self.assertEqual(LIVE_CRON.findall(self.NEW), [])

    def test_the_flow_form_and_a_half_flipped_pair_are_refused(self):
        flow = self.NEW.replace('  # schedule:   # line 1\n  #   - cron: "17 10 * * 1"   # line 2\n',
                                '  # schedule: [{cron: "17 10 * * 1"}]   # line 1\n')
        with self.assertRaises(LookupError):
            schedule_cron(flow)
        for which in ("schedule", "cron"):
            with self.subTest(live=which):
                with self.assertRaises(LookupError):
                    schedule_cron(set_line(self.NEW, which, "smaller"))
        unquoted = self.NEW.replace('"17 10 * * 1"', "17 10 * * 1")
        with self.assertRaises(LookupError):
            schedule_cron(unquoted)


if __name__ == "__main__":
    unittest.main()
