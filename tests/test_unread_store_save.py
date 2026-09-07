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
import inspect
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
        km._compact_seen.clear()

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

    def _journal_ops(self):
        p = jd._overrides_dir() / (SID + ".jsonl")
        if not p.exists():
            return []
        return [json.loads(l)["op"] for l in p.read_text().splitlines() if l.strip()]


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
    def test_the_undo_clear_restore_over_an_unparseable_store_raises_before_its_journal_row(self):
        # the one kernel.py writer that reached save_goals with a fallback (every other gesture returns early on
        # an empty node map): the user's undo-clear pulled the archived nodes into the fallback and published it
        # over the file. It now stands down before its journal row, so a restore that cannot land leaves no row
        # for the replay to carry, and the row from the load is the loud signal
        self._seed()
        node = jd.load_goals(SID)["nodes"][NID]
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {NID: node}, "status": {NID: "working"}})
        self.gp.write_text(CORRUPT)
        with self.assertRaises(jd.UnreadStoreError):
            km._restore_goal_archive([NID])
        self.assertEqual(self.gp.read_text(), CORRUPT, "the live file is left as it is")
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"], "the archive keeps the node: the restore did not half-land")
        self.assertEqual(self._journal_ops(), [], "no restore row for a restore that did not land")
        self.assertEqual(self._errs(), ["store-unreadable"], "the load's row; no save was attempted")


class UndoClear(_Store):
    """The review's reproduction, landed: an Undo over a session whose goals file did not read consumed the batch
    (the undo rows were written before the restore that then could not land) and stranded the card: the node
    stayed archived behind an orphan restore row, a second click found nothing to undo, and load_goals' replay
    defers to an archive that still holds the node. The same at an archive that did not read, with no raise."""

    def _cleared_and_compacted(self):
        """One top goal, cleared (the view row and the durable flag, as _clear_all writes them) and compacted
        into the archive; returns the live file's good bytes."""
        store = jd.load_goals(SID)
        nid, nd = self._node(1, "Ship the search endpoint")
        nd["cleared"] = True
        store["nodes"][nid] = nd
        store["status"][nid] = "cleared"
        jd.save_goals(SID, store)
        with (jd.STATE / "cleared.jsonl").open("a") as f:
            f.write(json.dumps({"id": NID, "t": 1781100500.5, "op": "clear"}) + "\n")
        self.assertEqual(km._compact_goal_store(SID), 1)
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"])
        self.assertNotIn(NID, jd.load_goals(SID)["nodes"])
        self.assertEqual(set(km._cleared_ids()), {NID})
        return self.gp.read_text()

    def _undo_lands(self):
        km._undo_clear()
        self.assertEqual(km._cleared_ids(), {}, "the batch is consumed")
        s = jd.load_goals(SID)
        self.assertIn(NID, s["nodes"])
        self.assertFalse(s["nodes"][NID].get("cleared"))
        self.assertNotIn(NID, jd.load_goal_archive(SID)["nodes"])

    def test_undo_lands_on_a_readable_store(self):
        self._cleared_and_compacted()
        self._undo_lands()

    def test_undo_over_an_unparseable_store_stands_down_and_keeps_the_batch(self):
        good = self._cleared_and_compacted()
        self.gp.write_text(CORRUPT)
        with self.assertRaises(jd.UnreadStoreError) as cm:
            km._undo_clear()
        self.assertIn("nothing was undone", str(cm.exception))
        self.assertEqual(set(km._cleared_ids()), {NID}, "the batch is still undoable")
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"], "the node is still archived")
        self.assertEqual(self._journal_ops(), [], "no orphan restore row")
        self.assertEqual(self.gp.read_text(), CORRUPT)
        self.assertEqual(self._errs(), ["store-unreadable"])
        self.gp.write_text(good)                                         # the file reads again: the same click lands
        self._undo_lands()

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_undo_over_an_unreadable_archive_stands_down(self):
        # pre-existing at the same site: load_goal_archive answered an empty archive for a file it could not read,
        # and the undo consumed the batch with no raise and nothing restored
        self._cleared_and_compacted()
        ap = jd.GOALARCHDIR / (SID + ".json")
        os.chmod(ap, 0)
        try:
            with self.assertRaises(jd.UnreadStoreError):
                km._undo_clear()
            self.assertEqual(set(km._cleared_ids()), {NID})
            self.assertEqual(self._journal_ops(), [])
            self.assertEqual(self._errs(), ["archive-unreadable"])
        finally:
            os.chmod(ap, 0o644)
        self._undo_lands()

    def test_the_undo_handler_reports_a_refusal_to_the_pane(self):
        src = inspect.getsource(km.Handler._dispatch_ws)
        i = src.index('msg.get("type") == "undoClear"')
        block = src[i:i + 900]
        self.assertIn("_undo_clear()", block)
        self.assertIn('"undoClearResult"', block)
        self.assertIn('"ok": False', block)


class Warns(_Store):
    """The row is file-level (no goal, so no card warn holds it) and `romp judges` is retired: while the episode
    holds for a listed session, the kernel says so to the chat clients once, and the /perf goals gauge counts it."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self._saved_k = (km._sessions, km._send_to_app)
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "name": "web", "anchor": "", "path": "", "mtime": 0}]
        km._send_to_app = lambda app, msg: self.sent.append((app, msg))
        km._UNREADABLE_WARNED.clear()

    def tearDown(self):
        km._sessions, km._send_to_app = self._saved_k
        km._UNREADABLE_WARNED.clear()
        super().tearDown()

    def _gauge(self):
        return km._PERF_STATS.snapshot()["goals"]["unreadable_stores"]

    def test_the_app_is_warned_once_per_episode_and_the_gauge_counts_it(self):
        good = self._seed()
        km._unreadable_store_warns(T0)
        self.assertEqual((self.sent, self._gauge()), ([], 0), "a readable store: nothing to say")
        self.gp.write_text(CORRUPT)
        jd.load_goals(SID)
        jd.load_goals(SID)
        km._unreadable_store_warns(T0 + 1)
        km._unreadable_store_warns(T0 + 2)
        self.assertEqual(len(self.sent), 1, "one warn frame per episode, not per pass")
        app, msg = self.sent[0]
        self.assertEqual((app, msg["type"]), ("chat", "warn"))
        self.assertIn("web", msg["text"])
        self.assertIn("goals/%s.json" % SID, msg["text"])
        self.assertEqual(self._gauge(), 1)
        self.gp.write_text(good)
        jd.load_goals(SID)                                               # a good read ends the episode
        km._unreadable_store_warns(T0 + 3)
        self.assertEqual((len(self.sent), self._gauge(), km._UNREADABLE_WARNED), (1, 0, set()),
                         "the episode's end clears the gauge and the said set")
        self.gp.write_text(CORRUPT)
        jd.load_goals(SID)                                               # a new episode is said again
        km._unreadable_store_warns(T0 + 4)
        self.assertEqual(len(self.sent), 2)

    def test_an_unlisted_session_is_said_once_it_is_listed(self):
        self._seed()
        self.gp.write_text(CORRUPT)
        jd.load_goals(SID)
        km._sessions = lambda now, window=None, forks=True: []
        km._unreadable_store_warns(T0)
        self.assertEqual(self.sent, [], "nothing shows the session: nothing to explain yet")
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "name": "web", "anchor": "", "path": "", "mtime": 0}]
        km._unreadable_store_warns(T0 + 1)
        self.assertEqual(len(self.sent), 1, "said once it is listed")


class UnmuteFastForward(_Store):
    def test_the_un_mute_fast_forward_stands_down_on_a_fallback_store(self):
        # the un-mute's fast-forward seals the muted stretch so the planner does not backfill it; over a fallback
        # it sealed nothing real and its save was refused. It stands down at the load now, with the stages' mark
        self._seed()
        self.gp.write_text(CORRUPT)
        jd._judge_ctx.stage_incomplete = False
        n = jd.fast_forward_placements(SID, path=str(Path(self.td.name) / "no-such-transcript.jsonl"))
        self.assertEqual(n, 0)
        self.assertTrue(jd._judge_ctx.stage_incomplete, "the same incomplete mark as the stages")
        self.assertEqual(self.gp.read_text(), CORRUPT)
        self.assertEqual(self._errs(), ["store-unreadable"], "no refused save: it stood down at the load")


class Archive(_Store):
    def test_an_unparseable_archive_is_marked_refused_and_left_by_the_sweep(self):
        # the archive twin of the live-store shape: the compaction sweep loads the archive, adds the tops it
        # moves and publishes; over a file that did not read it published the empty fallback plus the moved tops
        store = jd.load_goals(SID)
        nid, nd = self._node(1, "Ship the search endpoint")
        nd["cleared"] = True
        store["nodes"][nid] = nd
        store["status"][nid] = "cleared"
        jd.save_goals(SID, store)
        live = self.gp.read_text()
        ap = jd.GOALARCHDIR / (SID + ".json")
        ap.parent.mkdir(parents=True, exist_ok=True)
        ap.write_text(CORRUPT)
        arch = jd.load_goal_archive(SID)
        self.assertEqual((arch["nodes"], arch.get("_unread")), ({}, "archive"))
        with self.assertRaises(jd.UnreadStoreError):
            jd.save_goal_archive(SID, arch)
        self.assertEqual(ap.read_text(), CORRUPT)
        km._compact_goal_stores()                                        # no raise out of the sweep
        self.assertEqual((ap.read_text(), self.gp.read_text()), (CORRUPT, live),
                         "neither file touched: the move did not half-land")
        self.assertEqual(self._errs(), ["archive-unreadable", "unread-store-save", "unread-store-save"])
        self.assertNotIn("_unread", jd.load_goal_archive(SID.replace("d", "e")), "an absent archive is not marked")


if __name__ == "__main__":
    unittest.main()
