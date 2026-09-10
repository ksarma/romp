#!/usr/bin/env python3
"""Postal isolation (the user 2026-06-23): a session with the timeline lane's mailbox toggled off
(postalServiceOff — legacy postalOff — in the kernel's session-flags.json) is invisible to list_agents, can't send, and can't receive —
for working privately. These pin the flag reader + the read_box RECEIVE gate at the unit level; the
end-to-end /send + /agents enforcement is in tests/romp-postal.bats.

Synthetic only — placeholder UUIDs, hermetic temp state dir, no real session data.
"""
import json
import os
import shutil
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()      # hermetic; constants resolve under here at import
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal", os.path.join(BIN, "romp-postal-service"))

SID = "11111111-2222-3333-4444-555555555555"
# The mailbox case drains a box of its OWN (2026-09-10). Every postal test module loads
# bin/romp-postal-service under the one name `romp_postal`, and load_source re-executes into the same
# module object, so under pytest they all share one MAILROOT, and most of them address the placeholder
# sid above. A sibling's case that leaves mail in that sid's new/ on purpose (the restore cases in
# tests/test_postal_deferred_push_identity.py put a message back) is drained by the sibling's later
# cases in serial order, but xdist hands cases to workers one at a time, so this case ran right after
# the leftover on one worker and read two bodies. Same rule as the goal-store fixtures (CLAUDE.md,
# Testing): a case that asserts the exact contents of a shared store uses a private synthetic sid. The
# flag cases keep SID: they read the flags file only, and clear it in tearDown.
BOX_SID = "12121212-3434-5656-7878-9a9a9a9a9a9a"


def _set_flag(sid, postal_off):
    pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(pm.SESSION_FLAGS.read_text()) if pm.SESSION_FLAGS.exists() else {}
    if postal_off:
        data[sid] = {"postalOff": True}     # legacy key on purpose: pins back-compat (reader honours old + new)
    else:
        data.pop(sid, None)
    pm.SESSION_FLAGS.write_text(json.dumps(data))


class PostalOff(unittest.TestCase):
    def tearDown(self):
        try:
            pm.SESSION_FLAGS.unlink()
        except OSError:
            pass

    def test_default_not_isolated(self):
        self.assertFalse(pm._postal_off(SID), "no flags file → on the Romp Postal Service")
        self.assertFalse(pm._postal_off(""), "empty sid → not isolated")

    def test_flag_toggles_isolation(self):
        _set_flag(SID, True)
        self.assertTrue(pm._postal_off(SID))
        _set_flag(SID, False)
        self.assertFalse(pm._postal_off(SID), "clearing the flag rejoins the Romp Postal Service")

    def test_other_flags_do_not_isolate(self):
        pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
        pm.SESSION_FLAGS.write_text(json.dumps({SID: {"hideFromFeed": True}}))   # muted from feed, NOT postal
        self.assertFalse(pm._postal_off(SID), "hideFromFeed alone must not isolate from postal")

    def test_malformed_flags_file_fails_open(self):
        # the flags dir is made HERE, not inherited from an earlier test: under pytest-xdist the
        # class's tests split across workers, and this one landed on a worker where no sibling had
        # created the dir yet (surfaced 2026-09-04 when the suite's test count shifted the split)
        pm.SESSION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
        pm.SESSION_FLAGS.write_text("{not valid json")
        self.assertFalse(pm._postal_off(SID), "a corrupt flags file must NOT wedge messaging (fail open)")

    def test_read_box_holds_mail_while_isolated(self):
        box = pm.MAILROOT / BOX_SID / "new"
        shutil.rmtree(box.parent, ignore_errors=True)               # nothing of an earlier run in it
        self.addCleanup(shutil.rmtree, box.parent, ignore_errors=True)
        box.mkdir(parents=True, exist_ok=True)
        (box / "msg1").write_text("From: peer\nFrom-Id: x\nDate: now\n\nhello\n")
        _set_flag(BOX_SID, True)
        self.assertEqual(pm.read_box(BOX_SID, consume=True), [],
                         "isolated → a drain delivers nothing")
        self.assertTrue((box / "msg1").exists(),
                        "the message stays in new/ (not consumed) until the session reconnects")
        _set_flag(BOX_SID, False)
        got = pm.read_box(BOX_SID, consume=True)
        self.assertEqual([m["body"] for m in got], ["hello"],
                         "reconnecting delivers the held mail")


class WiringAcrossSurfaces(unittest.TestCase):
    """The postalServiceOff flag spans three files (kernel boot exposure → timeline render/toggle → postal
    enforcement). Pin the cross-surface wiring by name so a rename can't silently disconnect a surface."""

    def test_kernel_boot_exposes_postaloff(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('"postalServiceOff": _session_flag(sid, "postalServiceOff")', src,
                      "the kernel must publish postalServiceOff in the session boot so the timeline can render it")

    def test_timeline_view_draws_and_toggles_the_mailbox(self):
        # Since 2026-07-28 the mailbox lives in the lane GEAR's drop-down (LANE_TOGGLES) rather than as
        # its own lane icon — the row still draws the mailboxIcon and toggles postalServiceOff through
        # the same _setSessionFlag persistence.
        src = open(os.path.join(os.path.dirname(BIN), "ui", "romp-timeline-view.js")).read()
        self.assertIn("mailboxIcon", src, "the gear menu draws the (monochrome) mailbox icon")
        self.assertIn("flag: 'postalServiceOff', label: 'Postal service', icon: mailboxIcon", src,
                      "the gear menu row toggles the postalServiceOff flag")
        self.assertIn("this._setSessionFlag(s, t.flag, next);", src, "menu rows persist via _setSessionFlag")


if __name__ == "__main__":
    unittest.main(verbosity=2)
