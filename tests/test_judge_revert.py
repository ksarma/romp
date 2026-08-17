#!/usr/bin/env python3
"""jd.drop_goals_after(fsid, cut_t): a chat delete/edit rolls the CONVERSATION back to just before cut_t; the
cards MINTED from the now-abandoned turns (node["t"] >= cut_t) are orphans, so they are archived out of the
live store — whole subtrees. Deliberately narrow: verdicts an abandoned turn applied to a PRE-EXISTING card
are left alone (the user chose this simpler shape over surgically reverting the append-only diary + the
durable override journal). All fixtures are SYNTHETIC (placeholder UUIDs, invented text).
"""
import os
import tempfile
import threading
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
NOW = 1781100000
T0 = NOW - 3600
CUT = T0 + 50          # everything minted at/after CUT is abandoned; T0..T0+49 survives


class RevertBase(unittest.TestCase):
    def setUp(self):
        self._saved_state = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))

    def tearDown(self):
        jd._rebind_state(self._saved_state)
        self.td.cleanup()

    def _store(self):
        return {"rompUuid": SID, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {},
                "placements": {}, "status": {}}

    def _nid(self, seq):
        return "%s:g%d" % (SID, seq)


class DropGoalsAfter(RevertBase):
    def test_a_card_minted_after_the_cut_is_archived_whole_subtree(self):
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Survivor"}], [])          # born < CUT
        jd.apply_plan(s, "s2", T0 + 100, [{"do": "mint", "why": "x", "text": "Born in range"}], jd.open_menu(s))
        jd.apply_plan(s, "s3", T0 + 110, [{"do": "sub", "why": "x", "under": 2, "text": "sub of born"}], jd.open_menu(s))
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        archived = jd.drop_goals_after(SID, CUT)
        self.assertEqual(archived, 2, "the born-in-range top AND its sub are archived")
        live = jd.load_goals(SID)["nodes"]
        self.assertIn(self._nid(1), live, "the survivor stays in the live store")
        self.assertNotIn(self._nid(2), live, "the born-in-range top is gone from the live store")
        self.assertNotIn(self._nid(3), live, "its sub goes with it")
        arch = jd.load_goal_archive(SID)["nodes"]
        self.assertIn(self._nid(2), arch, "the born-in-range top moved to the archive")
        self.assertIn(self._nid(3), arch, "the sub moved with it")

    def test_a_born_in_range_sub_under_a_surviving_parent_is_archived_alone(self):
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Survivor top"}], [])
        jd.apply_plan(s, "s2", T0 + 100, [{"do": "sub", "why": "x", "under": 1, "text": "late sub"}], jd.open_menu(s))
        jd.save_goals(SID, s)
        archived = jd.drop_goals_after(SID, CUT)
        self.assertEqual(archived, 1, "only the late sub is archived; its pre-cut parent survives")
        live = jd.load_goals(SID)["nodes"]
        self.assertIn(self._nid(1), live)
        self.assertNotIn(self._nid(2), live)

    def test_removing_a_born_in_range_blocked_sub_re_rolls_the_surviving_parents_status(self):
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Parent"}], [])
        jd.apply_plan(s, "s2", T0 + 100, [{"do": "sub", "why": "x", "under": 1, "text": "late blocked sub"}],
                      jd.open_menu(s))
        jd.apply_plan(s, "s3", T0 + 110, [{"do": "block", "why": "owed", "goal": 2}], jd.open_menu(s))  # block the sub
        jd.rollup_status(s, session_closed=False)
        self.assertEqual(s["status"][self._nid(1)], "blocked", "premise: the late sub's block rolls up to the parent")
        jd.save_goals(SID, s)
        jd.drop_goals_after(SID, CUT)
        n = jd.load_goals(SID)
        self.assertEqual(n["status"][self._nid(1)], "working",
                         "with the born-in-range blocked sub gone, the parent re-rolls to working")

    def test_nothing_in_range_is_a_noop(self):
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "G"}], [])
        jd.save_goals(SID, s)
        self.assertEqual(jd.drop_goals_after(SID, CUT), 0, "no card born at/after the cut → nothing archived")
        self.assertIn(self._nid(1), jd.load_goals(SID)["nodes"], "the pre-cut card is untouched")

    def test_a_pre_existing_cards_verdicts_are_left_alone(self):
        # deliberate scope: a verdict an abandoned turn applied to a card born BEFORE the cut is NOT reverted
        # (that would need diary + override-journal surgery). Only born-in-range cards are dropped.
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Pre-existing"}], [])
        jd.apply_plan(s, "s2", T0 + 100, [{"do": "block", "why": "owed", "goal": 1}], jd.open_menu(s))  # ev_t after CUT
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        self.assertEqual(jd.drop_goals_after(SID, CUT), 0, "the pre-existing card is not born-in-range → not archived")
        n = jd.load_goals(SID)
        self.assertTrue(n["nodes"][self._nid(1)]["blocked"],
                        "its block (from a now-abandoned turn) is intentionally left in place")

    def test_empty_store_is_a_noop(self):
        jd.save_goals(SID, self._store())
        self.assertEqual(jd.drop_goals_after(SID, CUT), 0)


class RebaseTombstones(RevertBase):
    """The sweep leaves a DURABLE deletion marker (store rewindSwept) that _rebase_onto_disk honors —
    the mergedFrom lesson applied to rewinds. Without it any one-shot sweep, however keyed, loses to
    the next concurrent save: presence-in-a-snapshot is not truth, and the adopt-wholesale branch
    republished swept nodes (proven five times in live stores — nodes resident in live AND archive
    at once, live twins gathering diary rows on a conversation that no longer exists)."""

    def _seed(self):
        s = self._store()
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Survivor"}], [])
        jd.apply_plan(s, "s2", T0 + 100, [{"do": "mint", "why": "x", "text": "Doomed"}], jd.open_menu(s))
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        return self._nid(2)

    def test_a_pre_sweep_loader_saving_post_sweep_does_not_republish(self):
        # ordering (i): writer A loads, the sweep archives + saves, A saves — A's rebase must read
        # the tombstone from DISK and drop its stale copy instead of adopting it back
        doomed = self._seed()
        a = jd.load_goals(SID)                        # writer A's pre-sweep snapshot (holds `doomed`)
        self.assertEqual(jd.drop_goals_after(SID, CUT), 1)
        a["nodes"][self._nid(1)]["mt"] = T0 + 5       # A did unrelated work, then publishes
        jd.save_goals(SID, a)
        live = jd.load_goals(SID)
        self.assertNotIn(doomed, live["nodes"], "the swept node stays swept through A's rebase")
        self.assertIn(doomed, jd.load_goal_archive(SID)["nodes"], "…and lives on in the archive only")
        self.assertIn(doomed, live.get("rewindSwept", {}), "the tombstone itself survived the rebase")

    def test_the_sweeps_own_save_rebasing_over_a_midflight_publish_does_not_readopt(self):
        # ordering (ii): a concurrent pass publishes between the sweep's load and its save — the
        # sweep's rebase must not adopt back from disk the very node it just popped
        doomed = self._seed()
        orig = jd.save_goal_archive
        def hijack(fsid, arch):                       # runs INSIDE drop_goals_after, between its load
            orig(fsid, arch)                          # and its save — the mid-flight window
            w = jd.load_goals(SID)                    # the concurrent writer still sees `doomed` live
            w["nodes"][doomed]["mt"] = T0 + 200
            jd.save_goals(SID, w)                     # …and publishes it (disk rev moves)
        jd.save_goal_archive = hijack
        try:
            self.assertEqual(jd.drop_goals_after(SID, CUT), 1)
        finally:
            jd.save_goal_archive = orig
        live = jd.load_goals(SID)
        self.assertNotIn(doomed, live["nodes"], "the sweep's rebase did not re-adopt its own pop")
        self.assertIn(doomed, jd.load_goal_archive(SID)["nodes"])

    def test_a_concurrent_archiver_cannot_drop_the_other_writers_payloads(self):
        """goals-archive is a blind RMW (save_goal_archive has none of save_goals' rev discipline),
        and the rewind work made concurrent same-fsid archivers routine with systematically
        DIFFERENT move sets (t-keyed sweep vs identity-keyed reconcile). Un-serialized, the writer
        holding a stale archive base dropped the other writer's nodes from the archive while the
        rewindSwept union kept them out of the live store — in NEITHER file, silent permanent loss.
        The whole RMW now holds jd._GOAL_ARCH_LOCK, so the second writer reloads a base that
        already carries the first writer's nodes. Orchestration: writer B starts first and its
        archive save stalls mid-window; writer A (the full t-keyed sweep) runs against it."""
        s = self._store()
        jd.apply_plan(s, "s1", T0 + 100, [{"do": "mint", "why": "x", "text": "Doomed one"}], [])
        jd.apply_plan(s, "s2", T0 + 110, [{"do": "mint", "why": "x", "text": "Doomed two"}], jd.open_menu(s))
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        n1, n2 = self._nid(1), self._nid(2)
        orig = jd.save_goal_archive
        main = threading.current_thread()
        b_at_save, a_done = threading.Event(), threading.Event()
        def stalling_save(fsid, arch):
            if threading.current_thread() is not main:
                b_at_save.set()          # B is mid-RMW: its base predates A's sweep
                a_done.wait(0.5)         # un-serialized, A's whole sweep lands inside this window
            orig(fsid, arch)
        b = threading.Thread(target=lambda: jd.archive_goal_nodes(
            SID, jd.load_goals(SID), {n2}, T0 + 200))
        jd.save_goal_archive = stalling_save
        try:
            b.start()
            b_at_save.wait(5)
            jd.drop_goals_after(SID, T0 + 90)          # writer A: the t-keyed sweep takes BOTH nodes
            a_done.set()
            b.join(10)
        finally:
            jd.save_goal_archive = orig
        self.assertFalse(b.is_alive(), "writer B finished")
        arch = jd.load_goal_archive(SID)["nodes"]
        live = jd.load_goals(SID)["nodes"]
        for nid in (n1, n2):
            self.assertIn(nid, arch, "every swept payload survives in the archive: %s" % nid)
            self.assertNotIn(nid, live)

    def test_an_undo_clear_journal_restore_pops_the_tombstone(self):
        # a user restore outranks the marker: the journal re-inserts the node AND clears its
        # tombstone — and STAMPS rewindRestored, so the next rebase (which re-unions the stale
        # disk marker) orders the two events and lets the restore win instead of re-deleting
        # what the user brought back. The row's t postdates the sweep, as any real restore does
        # (both are wall-clock event times; the ordering is exactly what the stamps encode).
        doomed = self._seed()
        jd.drop_goals_after(SID, CUT)
        arch = jd.load_goal_archive(SID)
        payload = dict(arch["nodes"].pop(doomed))     # the undo pulled it OUT of the archive…
        jd.save_goal_archive(SID, arch)
        rt = int(time.time()) + 10                    # …after the sweep, as restores always are
        jd.append_restore(SID, {doomed: payload}, {}, rt)   # …and journaled the payload
        live = jd.load_goals(SID)                     # replay re-inserts (in neither store nor archive)
        self.assertIn(doomed, live["nodes"])
        self.assertNotIn(doomed, live.get("rewindSwept", {}), "the restore popped the tombstone")
        self.assertEqual(live.get("rewindRestored", {}).get(doomed), rt,
                         "…and left the durable restore stamp in its place")
        jd.save_goals(SID, live)                      # a follow-on rebase cycle must not re-delete it
        again = jd.load_goals(SID)
        self.assertIn(doomed, again["nodes"])

    def test_a_stale_writer_cannot_resurrect_a_popped_tombstone_after_a_restore(self):
        # a pass holds a pre-restore snapshot (marker present, node swept) across a 30-80s model
        # call; the user restores; the pass publishes. Its stale marker re-unions — the restore
        # stamp must neutralize it, or the just-restored node is re-killed and ends in NEITHER
        # file (the review reproduced exactly that: marker back, node gone, archive empty).
        doomed = self._seed()
        jd.drop_goals_after(SID, CUT)
        stale = jd.load_goals(SID)                    # the pass's snapshot: marker present, node gone
        arch = jd.load_goal_archive(SID)              # the user restores via the journal (the
        payload = dict(arch["nodes"].pop(doomed))     # kernel undo-clear's exact moves)
        jd.save_goal_archive(SID, arch)
        jd.append_restore(SID, {doomed: payload}, {}, int(time.time()) + 10)
        live = jd.load_goals(SID)
        self.assertIn(doomed, live["nodes"], "premise: the restore landed")
        jd.save_goals(SID, live)                      # restored state published
        stale["nodes"][self._nid(1)]["mt"] = T0 + 5   # the stale pass did unrelated work…
        jd.save_goals(SID, stale)                     # …and publishes across the restore
        after = jd.load_goals(SID)
        self.assertIn(doomed, after["nodes"], "the stale marker lost to the restore stamp")
        # and the node is in exactly one place — never resident in live AND archive at once
        self.assertNotIn(doomed, jd.load_goal_archive(SID)["nodes"])


if __name__ == "__main__":
    unittest.main()
