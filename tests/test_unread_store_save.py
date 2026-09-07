#!/usr/bin/env python3
"""save_goals never publishes a store that loaded as a fallback for a goals file that exists and did not
read or parse (a data-loss shape found by the P2 gate's build and confirmed pre-existing by three
independent refuters, 2026-09-07). Before this, load_goals answered an EMPTY store (marked `_unread`) and
save_goals took it for a create: its _baseRev 0 matched the 0 that _disk_rev answered for the unparseable
file, so the grouper's and consolidator's signature write, the planner's and closer's whole pass and the
kernel's undo-clear restore each replaced the file with the fallback, after which the file read again,
empty.

Pinned here: the refusal and its row, the file left byte-identical, a first mint over an ABSENT file still
saving, a store whose JOURNAL did not read still publishing (nothing durable is lost: the journal replays on
every load), _disk_rev telling absent from unreadable, the CAS refusing a file it cannot read at publish
time with the holder's base left intact, one store-unreadable row per failure episode, and the kernel's
undo-clear restore over the unparseable store logging and leaving the file. The stages' stand-down and the
courier's are pinned beside their fixtures (tests/test_judge_stage_gate.py, tests/test_courier_kind_demote_only.py).
Synthetic fixtures only: a sid private to this module, invented goal text."""
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_unread_store", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "dddddddd-1111-2222-3333-444444444444"      # private to this module: a shared sid's journal replays here
NID = SID + ":g1"
T0 = 1781100000
CORRUPT = "{ not the store"                        # a goals file that exists and does not parse


class _Store(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = jd.STATE
        jd._rebind_state(Path(self.td.name))         # clears the memos, the caches and the read-failure episodes
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        self.gp = jd.GOALDIR / (SID + ".json")

    def tearDown(self):
        jd._rebind_state(self._saved)
        self.td.cleanup()

    def _node(self, n, text):
        nid = "%s:g%d" % (SID, n)
        return nid, {"id": nid, "text": text, "parentId": None, "nodeComplete": False, "cleared": False,
                     "t": T0 + n, "mt": T0 + 60 + n, "trail": [], "log": []}

    def _mint(self, store, n, text="Add the api tests"):
        nid, nd = self._node(n, text)
        store["nodes"][nid] = nd
        store["status"][nid] = "working"
        return nid

    def _seed(self):
        """One working top goal, published; returns the file's good bytes."""
        store = jd.load_goals(SID)
        self._mint(store, 1, "Ship the search endpoint")
        jd.save_goals(SID, store)
        return self.gp.read_text()

    def _errs(self):
        try:
            return [r["err"] for r in (json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip())]
        except FileNotFoundError:
            return []


class Refusal(_Store):
    def test_a_fallback_store_is_refused_and_the_file_is_left_as_it_is(self):
        self._seed()
        self.gp.write_text(CORRUPT)
        s = jd.load_goals(SID)
        self.assertEqual(s.get("_unread"), "store", "the file exists and did not parse: a fallback, marked with its reason")
        self.assertEqual(s["nodes"], {})
        self._mint(s, 2)                                                 # what a stage would decide over the empty view
        with self.assertRaises(jd.UnreadStoreError):
            jd.save_goals(SID, s)
        self.assertEqual(self.gp.read_text(), CORRUPT, "byte-identical: nothing was published")
        self.assertEqual((s["_baseRev"], s.get("_unread")), (0, "store"), "the holder is left as it was")
        self.assertEqual(self._errs(), ["store-unreadable", "unread-store-save"],
                         "one row for the failed read, one for the refused publish")

    def test_an_absent_file_still_mints_and_saves(self):
        s = jd.load_goals(SID)
        self.assertNotIn("_unread", s, "no file: the empty store IS its content")
        self._mint(s, 1)
        jd.save_goals(SID, s)
        raw = json.loads(self.gp.read_text())
        self.assertIn(NID, raw["nodes"])
        self.assertEqual(raw["rev"], 1)
        self.assertEqual(self._errs(), [])

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_a_store_whose_journal_did_not_read_still_publishes(self):
        # the OTHER fallback: the store parsed, the journal did not. Its content is the file's, and the rows
        # it lacks replay on the next load, so a publish loses nothing durable; refusing it would block every
        # writer, the kernel's gesture exports included, over a file the store's content does not depend on
        self._seed()
        jd.append_override(SID, NID, "resolve", T0 + 70)
        jp = jd._overrides_dir() / (SID + ".jsonl")
        os.chmod(jp, 0)
        try:
            s = jd.load_goals(SID)
            self.assertEqual(s.get("_unread"), "journal")
            self.assertIn(NID, s["nodes"], "the store itself parsed: its nodes are intact")
            self._mint(s, 2)
            jd.save_goals(SID, s)                                        # allowed
        finally:
            os.chmod(jp, 0o644)
        raw = json.loads(self.gp.read_text())
        self.assertIn(SID + ":g2", raw["nodes"], "published")
        self.assertNotIn("_unread", raw, "the mark is never written to disk")
        self.assertEqual(self._errs(), ["history-unreadable"], "the journal's own row; no refusal")
        self.assertNotIn("_unread", jd.load_goals(SID), "readable again: the journal replays, nothing was lost")

    def test_disk_rev_tells_absent_from_unreadable(self):
        self.assertEqual(jd._disk_rev(SID), 0, "absent: a create's base")
        self._seed()
        self.assertEqual(jd._disk_rev(SID), 1)
        self.gp.write_text(CORRUPT)
        self.assertIsNone(jd._disk_rev(SID), "exists and does not parse: not a create")
        self.gp.write_text("[]")
        self.assertIsNone(jd._disk_rev(SID), "exists and is not a store document")
        if os.geteuid() != 0:
            self.gp.write_text('{"rev": 3}')
            os.chmod(self.gp, 0)
            try:
                self.assertIsNone(jd._disk_rev(SID), "exists and cannot be opened")
            finally:
                os.chmod(self.gp, 0o644)

    def test_the_cas_refuses_a_file_it_cannot_read_at_publish_time(self):
        # a store loaded from a GOOD file whose file stops reading before the publish: _disk_rev answered 0,
        # the writer took the file for gone, rebased onto nothing and wrote itself at rev 1 over whatever a
        # concurrent writer had published since. The CAS now refuses and leaves the holder's base alone
        good = self._seed()
        s = jd.load_goals(SID)
        self.assertEqual(s["_baseRev"], 1)
        self._mint(s, 2)
        self.gp.write_text(CORRUPT)
        with self.assertRaises(jd.UnreadStoreError):
            jd.save_goals(SID, s)
        self.assertEqual(self.gp.read_text(), CORRUPT)
        self.assertEqual(s["_baseRev"], 1, "the base survives the refusal: the holder's next save is CAS-checked")
        self.assertNotIn("_unread", s)
        self.assertEqual(self._errs(), ["unread-store-save"])
        self.gp.write_text(good)                                         # the file reads again: the same holder publishes
        jd.save_goals(SID, s)
        raw = json.loads(self.gp.read_text())
        self.assertEqual(raw["rev"], 2)
        self.assertEqual(sorted(raw["nodes"]), [NID, SID + ":g2"])

    def test_load_goals_logs_one_row_per_failure_episode(self):
        good = self._seed()
        self.gp.write_text(CORRUPT)
        for _ in range(3):
            self.assertEqual(jd.load_goals(SID).get("_unread"), "store")
        self.assertEqual(self._errs(), ["store-unreadable"], "three loads, one episode, one row")
        self.gp.write_text(good)
        self.assertNotIn("_unread", jd.load_goals(SID))
        self.gp.write_text(CORRUPT)
        jd.load_goals(SID)
        self.assertEqual(self._errs(), ["store-unreadable"] * 2, "a good read ends the episode; the next failure is a new one")
        self.assertEqual(jd.load_goals_shared(SID).get("_unread"), "store", "the shared loader marks the same reason")
        self.assertEqual(self._errs(), ["store-unreadable"] * 2, "and shares the episode: no third row")


class KernelWriter(_Store):
    def test_the_undo_clear_restore_over_an_unparseable_store_logs_and_leaves_the_file(self):
        # the one kernel.py writer that reaches save_goals with a fallback (every other gesture returns early on
        # an empty node map): the user's undo-clear pulled the archived nodes into the fallback and published
        # it over the file. The refusal reaches the WebSocket handler's except; the row is the loud signal
        self._seed()
        node = jd.load_goals(SID)["nodes"][NID]
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {NID: node}, "status": {NID: "working"}})
        self.gp.write_text(CORRUPT)
        with self.assertRaises(jd.UnreadStoreError):
            km._restore_goal_archive([NID])
        self.assertEqual(self.gp.read_text(), CORRUPT, "the live file is left as it is")
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"], "the archive keeps the node: the restore did not half-land")
        self.assertEqual(self._errs(), ["store-unreadable", "unread-store-save"])


if __name__ == "__main__":
    unittest.main()
