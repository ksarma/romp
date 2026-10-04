"""The weekly macOS run is paused (.github/workflows/ci.yml, 2026-10-04) until the first month's bill on the private runner is
read; a manual dispatch still runs the macOS cells.

From 2026-09-16 the macOS cells ran on a weekly schedule as well as on a manual dispatch: with the manual switch alone the
release gate was the first macOS run in two weeks and found twenty-nine accumulated failures. On a private repository every
run is billed, and the scheduled run added its Linux jobs and the macOS cells, which bill at about ten times the Linux rate,
every week. So the schedule's two lines are commented out in the on: block, with the reason beside them, and every matrix
job's os: expression still names the schedule event, so un-commenting the two lines restores the run as it was.

Pins, each over ci.yml's text, read with tests/test_ci_workflow_concurrency.py's readers (no YAML library in the test deps):
1. PAUSED: the on: block, read as keys with its comment lines dropped (triggers), has no schedule key, and no line of the
   workflow is a live cron entry (`- cron:` after nothing but blanks). Both are red on the workflow before the pause.
2. DISPATCH KEPT: workflow_dispatch is a trigger, and each matrix job's os: expression, evaluated for a dispatch, gives
   macos-latest, so a dispatch still runs the macOS cells beside the Linux ones.
3. RESTORABLE: the on: block holds the schedule's two lines commented out, once each, and un-commented (restored: the `# `
   after their two blanks removed) they give one weekly cron at a quiet hour Pacific, and each matrix job's os: expression,
   evaluated for the schedule event, gives macos-latest as a dispatch's does. So the restore the comment promises is the
   old run, and the commented lines cannot drift into something else unread. Red before the pause, where there is nothing
   commented to restore.
4. The reason stands in the on: block's comments: the run is paused until the first month's bill is read (keyed on those
   words, a spelling pin on the comment; the decision itself is the user's of 2026-10-04)."""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# the checkout root on sys.path before the one import from a sibling module, as tests/test_ci_secret_scan.py does
sys.path.insert(0, ROOT)
from tests.test_ci_workflow_concurrency import MAIN, MATRIX_JOBS, SHA_A, matrix_os, os_list, run, triggers  # noqa: E402

WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
# The schedule's two lines as the on: block holds them commented out: the key and its one cron entry.
COMMENTED_KEY = "  # schedule:"
COMMENTED_CRON = re.compile(r'^  #   - cron: "[^"]+".*$')
LIVE_CRON = re.compile(r"^[ \t]*- cron:", re.M)


def on_text(src):
    """The on: block as written, comment lines kept: its top-level line to the next top-level line."""
    m = re.search(r"^on:[ \t]*\n(.*?)^(?=\S)", src, re.S | re.M)
    if m is None:
        raise LookupError("no top-level on: block in ci.yml; re-anchor this pin")
    return m.group(1)


def restored(src):
    """src with the on: block's two commented schedule lines un-commented: the line COMMENTED_KEY and the one line
    COMMENTED_CRON matches each lose the `# ` after their two blanks. Raises LookupError unless the block holds each once."""
    block = on_text(src)
    lines = block.split("\n")
    keys = [i for i, l in enumerate(lines) if l == COMMENTED_KEY]
    crons = [i for i, l in enumerate(lines) if COMMENTED_CRON.match(l)]
    if len(keys) != 1 or len(crons) != 1:
        raise LookupError("the on: block holds %d commented schedule key lines and %d commented cron lines, not one each: "
                          "nothing to restore" % (len(keys), len(crons)))
    for i in keys + crons:
        lines[i] = "  " + lines[i][len("  # "):]
    return src.replace(block, "\n".join(lines), 1)


def macos_on(src, event):
    """{matrix job: whether its os: expression, evaluated for `event` on main, gives macos-latest}."""
    out = {}
    for job in MATRIX_JOBS:
        expr, _includes = matrix_os(src, job)
        out[job] = "macos-latest" in os_list(expr, run(event, MAIN, SHA_A))
    return out


class MacosSchedulePaused(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WF, encoding="utf-8") as fh:
            cls.wf = fh.read()

    def test_1_no_schedule_trigger_and_no_live_cron(self):
        self.assertNotIn("schedule", triggers(self.wf), "ci.yml has a live schedule: trigger; the weekly run is paused until "
                                                        "the first month's bill on the private runner is read (2026-10-04)")
        self.assertEqual(LIVE_CRON.findall(self.wf), [], "ci.yml holds a live cron entry; the weekly run is paused")

    def test_2_a_dispatch_still_runs_the_macos_cells(self):
        self.assertIn("workflow_dispatch", triggers(self.wf), "the manual on-switch stays")
        self.assertEqual(macos_on(self.wf, "workflow_dispatch"), {job: True for job in MATRIX_JOBS},
                         "each matrix job selects macOS on a dispatch, the one road left to the macOS cells while the weekly "
                         "run is paused")

    def test_3_un_commenting_the_two_lines_restores_the_weekly_run(self):
        back = restored(self.wf)
        self.assertIn("schedule", triggers(back), "the restored block has a schedule: trigger")
        crons = re.findall(r'^    - cron: "([^"]+)"', on_text(back), re.M)
        self.assertEqual(len(crons), 1, "one scheduled run: %r" % crons)
        minute, hour, dom, month, dow = crons[0].split()
        self.assertEqual((dom, month), ("*", "*"), "weekly, not monthly")
        self.assertRegex(dow, r"^[0-6]$", "one day of the week")
        self.assertTrue(minute.isdigit() and hour.isdigit(), "a fixed minute and hour")
        self.assertIn(int(hour), range(8, 14), "a quiet hour Pacific: 08:00 to 13:00 UTC is midnight to 06:00 Pacific")
        self.assertEqual(macos_on(back, "schedule"), {job: True for job in MATRIX_JOBS},
                         "each matrix expression still selects macOS on the schedule event, so the restored run is the old one")

    def test_4_the_reason_stands_beside_the_commented_lines(self):
        comments = " ".join(l.strip().lstrip("#").strip() for l in on_text(self.wf).split("\n") if l.strip().startswith("#"))
        self.assertIn("paused", comments.lower(), "the on: block's comment says the weekly run is paused")
        self.assertIn("first month's bill", comments, "and until when: the first month's bill on the private runner")


class TheReadersThemselves(unittest.TestCase):
    """restored and the pins over a synthetic workflow: the block before the pause (a live schedule) is red on pins 1 and 3,
    and the paused block green."""

    LIVE = ('name: CI\non:\n  push:\n    branches: [\'batch/**\']\n  workflow_dispatch:\n  schedule:\n'
            '    - cron: "0 10 * * 1"   # weekly\njobs:\n')
    PAUSED = ('name: CI\non:\n  push:\n    branches: [\'batch/**\']\n  workflow_dispatch:\n  # paused until the first month\'s '
              'bill is read\n  # schedule:\n  #   - cron: "0 10 * * 1"   # weekly\njobs:\n')

    def test_the_live_block_is_red_and_the_paused_block_green(self):
        self.assertIn("schedule", triggers(self.LIVE))
        self.assertEqual(len(LIVE_CRON.findall(self.LIVE)), 1)
        with self.assertRaises(LookupError):
            restored(self.LIVE)
        self.assertNotIn("schedule", triggers(self.PAUSED))
        self.assertEqual(LIVE_CRON.findall(self.PAUSED), [])
        back = restored(self.PAUSED)
        self.assertIn("schedule", triggers(back))
        self.assertIn('\n    - cron: "0 10 * * 1"', back)

    def test_a_second_commented_cron_is_refused(self):
        twice = self.PAUSED.replace("jobs:\n", '  #   - cron: "0 11 * * 1"\njobs:\n')
        with self.assertRaises(LookupError):
            restored(twice)


if __name__ == "__main__":
    unittest.main()
