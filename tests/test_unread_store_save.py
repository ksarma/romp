#!/usr/bin/env python3
"""A goals file that exists and cannot be read is never published over, and never answered as an empty store.

Under upstream #1019 (adopted as the base in the 2026-09-08 fold, steer 1) load_goals RAISES on a read fault
(EIO, EACCES, a directory at the path) and QUARANTINES bytes that do not parse: they are moved aside to
<file>.corrupt-<utc stamp> (one store-quarantined row, one stderr line) and the session legitimately starts
fresh, the evidence kept. The per-session boundary (jd.load_goals_or_fault / load_goals_shared_or_fault /
save_goals_or_fault) turns the raise into (None, exc) and files ONE store-unreadable (or store-unwritable) row
per fault EPISODE; a good read or publish through it ends the episode. That replaces this fork's earlier
mechanism for the live store (a fallback store marked `_unread` == "store" that save_goals refused with
UnreadStoreError). The data-loss shape it closed (2026-09-07: an empty fallback whose _baseRev 0 matched the 0
that _disk_rev answered for an unparseable file, so the grouper's, consolidator's, planner's, closer's and
undo-clear's saves each replaced the file with the fallback) is closed the same way: the save path's own
readers raise on a file they cannot read or parse, so nothing is published over it. The fork's mark and
refusal survive where #1019 leaves a gap: the cleared-card ARCHIVE (`_unread` == "archive",
save_goal_archive's refusal, the sweep and the undo standing down) and a store loaded WITHOUT its override
journal (`_unread` == "journal", which still publishes: the journal replays on every load).

Pinned here: the quarantine and the fresh start; a first mint over an ABSENT file still saving; the journal
shape still publishing; _disk_rev telling absent from unreadable by raising; the CAS refusing a file it cannot
read at publish time with the holder's base left intact; one store-unreadable row per fault episode, shared
by both loaders; the kernel's undo-clear restore skipping a session whose store does not read (the batch stays
owed) and landing into the fresh store after a quarantine; the kernel's once-per-episode warn frame and the
/perf gauge reading the boundary's episodes; the un-mute fast-forward raising instead of sealing over a store
it could not read; the archive twin. The stages' stand-down and the courier's are pinned beside their
fixtures (tests/test_judge_stage_gate.py, tests/test_courier_kind_demote_only.py). Synthetic fixtures only: a
sid private to this module, invented goal text."""
import contextlib
import errno
import inspect
import io
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

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


@contextlib.contextmanager
def _fault_on(path):
    """Every read of `path` raises EIO; every other read is untouched. Two seams, because this fork reads a
    store two ways: Path.read_text (load_goals via _read_store_json) and the descriptor reader
    jd._disk_read(fd, path_s) behind load_goals_shared, _disk_rev and _disk_entry (the shared read-only cache
    and the disk-side memo, 2026-09-06). The same error text at both, so the two loaders share one episode."""
    orig, orig_disk = Path.read_text, jd._disk_read

    def faulting(p, *a, **kw):
        if p == path:
            raise OSError(errno.EIO, "Input/output error", str(p))
        return orig(p, *a, **kw)

    def faulting_disk(fd, path_s):
        if str(path_s) == str(path):
            raise OSError(errno.EIO, "Input/output error", str(path))
        return orig_disk(fd, path_s)
    with mock.patch.object(Path, "read_text", faulting), mock.patch.object(jd, "_disk_read", faulting_disk):
        yield


class _Store(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = jd.STATE
        jd._rebind_state(Path(self.td.name))         # clears the memos, the caches and the fault episodes
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

    def _rows(self):
        try:
            return [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()]
        except FileNotFoundError:
            return []

    def _errs(self):
        return [r["err"] for r in self._rows()]

    def _journal_ops(self):
        p = jd._overrides_dir() / (SID + ".jsonl")
        if not p.exists():
            return []
        return [json.loads(l)["op"] for l in p.read_text().splitlines() if l.strip()]

    def _aside(self):
        """The quarantine sidecars for this module's store: <sid>.json.corrupt-<utc stamp>[-n]."""
        return sorted(p for p in jd.GOALDIR.iterdir() if p.name.startswith(SID + ".json.corrupt-"))


class Refusal(_Store):
    """The loader refuses to ANSWER for a file it cannot read: a fault raises, the boundary files it, and
    bytes that do not parse are moved aside before the fresh store is handed out."""

    def test_an_unparseable_store_is_quarantined_and_the_session_starts_fresh(self):
        # this fork's fallback-and-refuse over unparseable bytes is superseded by upstream #1019's quarantine
        # (steer 1, 2026-09-08): the bytes are preserved aside, the fresh store is the legitimate answer, and a
        # save over the now-absent path is a create, never a publish over what did not read
        self._seed()
        self.gp.write_text(CORRUPT)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            s = jd.load_goals(SID)
        self.assertNotIn("_unread", s, "no fallback: the fresh store IS what the path now holds")
        self.assertEqual(s["nodes"], {})
        self.assertFalse(self.gp.exists(), "the corrupt file is out of the way")
        aside = self._aside()
        self.assertEqual(len(aside), 1, "evidence kept, never deleted")
        self.assertRegex(aside[0].name, r"\.json\.corrupt-\d{8}T\d{6}Z$")
        self.assertEqual(aside[0].read_text(), CORRUPT)
        self.assertIn("moved aside", err.getvalue(), "one stderr line naming the move")
        self.assertEqual(self._errs(), ["store-quarantined"], "one row for the move, none for a refusal")
        self._mint(s, 2)
        jd.save_goals(SID, s)                                            # a create over the absent path
        raw = json.loads(self.gp.read_text())
        self.assertEqual((raw["rev"], sorted(raw["nodes"])), (1, [SID + ":g2"]))
        self.assertEqual(self._errs(), ["store-quarantined"], "the publish refuses nothing: the file it replaces is absent")

    def test_a_store_that_does_not_read_raises_and_the_boundary_files_it(self):
        # the read FAULT is the shape the refusal was for, and the one left: load_goals raises (never an empty
        # store), nothing is published, and the per-session boundary answers (None, exc) with one row
        good = self._seed()
        with _fault_on(self.gp):
            with self.assertRaises(OSError):
                jd.load_goals(SID)
            with self.assertRaises(OSError):
                jd.load_goals_shared(SID)
            self.assertEqual(self._errs(), [], "a bare raise files nothing: the boundary that catches it does")
            store, fault = jd.load_goals_or_fault(SID)
            self.assertIsNone(store, "never an empty store for a file that exists")
            self.assertIn("Input/output error", str(fault))
        self.assertEqual(self.gp.read_text(), good, "byte-identical: nothing was published")
        rows = self._rows()
        self.assertEqual([r["err"] for r in rows], ["store-unreadable"])
        self.assertIn("Input/output error", rows[0]["note"], "the note carries the fault itself")

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
        # 0 only for an ABSENT file (a create's base); a file that exists and does not read or parse RAISES
        # (upstream #1019's save-path rule, steer 1): read as 0 it matched a fresh store's base and let save_goals
        # publish an empty store over bytes it never read. This fork's None answer went with the fallback it served
        self.assertEqual(jd._disk_rev(SID), 0, "absent: a create's base")
        self._seed()
        self.assertEqual(jd._disk_rev(SID), 1)
        self.gp.write_text(CORRUPT)
        with self.assertRaises(ValueError, msg="exists and does not parse: not a create"):
            jd._disk_rev(SID)
        self.gp.write_text("[]")
        with self.assertRaises(ValueError, msg="exists and is not a store document"):
            jd._disk_rev(SID)
        self.gp.write_text('{"rev": 3}')
        with _fault_on(self.gp):
            with self.assertRaises(OSError, msg="exists and cannot be read"):
                jd._disk_rev(SID)
        self.assertEqual(jd._disk_rev(SID), 3, "readable again")

    def test_the_cas_refuses_a_file_it_cannot_read_at_publish_time(self):
        # a store loaded from a GOOD file whose file stops reading before the publish: _disk_rev answered 0,
        # the writer took the file for gone, rebased onto nothing and wrote itself at rev 1 over whatever a
        # concurrent writer had published since. The save path's readers now RAISE (upstream #1019: ValueError
        # for bytes that do not parse, the OSError for a read fault) and leave the holder's base alone; behind
        # the boundary (jd.save_goals_or_fault, a user gesture's publish) that is one store-unwritable row and
        # the fault handed back to the caller, which answers the user
        good = self._seed()
        s = jd.load_goals(SID)
        self.assertEqual(s["_baseRev"], 1)
        self._mint(s, 2)
        self.gp.write_text(CORRUPT)
        with self.assertRaises(ValueError):
            jd.save_goals(SID, s)
        self.assertEqual(self.gp.read_text(), CORRUPT, "byte-identical: nothing was published over bytes the save could not read")
        self.assertEqual(s["_baseRev"], 1, "the base survives the refusal: the holder's next save is CAS-checked")
        self.assertNotIn("_unread", s)
        self.assertEqual(self._errs(), [], "a bare save_goals files nothing: its caller's boundary does")
        fault = jd.save_goals_or_fault(SID, s)
        self.assertIsInstance(fault, ValueError)
        self.assertEqual(self._errs(), ["store-unwritable"], "the boundary files the refused publish, once per episode")
        self.assertIsInstance(jd.save_goals_or_fault(SID, s), ValueError)
        self.assertEqual(self._errs(), ["store-unwritable"], "a repeat of the same fault files nothing new")
        self.assertEqual(self.gp.read_text(), CORRUPT)
        self.gp.write_text(good)                                         # the file reads again: the same holder publishes
        self.assertIsNone(jd.save_goals_or_fault(SID, s))
        raw = json.loads(self.gp.read_text())
        self.assertEqual(raw["rev"], 2)
        self.assertEqual(sorted(raw["nodes"]), [NID, SID + ":g2"])
        self.assertEqual(self._errs(), ["store-unwritable"], "the good publish ends the episode: no new row")

    def test_load_goals_logs_one_row_per_failure_episode(self):
        # the episode is the boundary's (jd._STORE_FAULTS, upstream #1019): a bare raise is not listed, a repeat
        # of the same fault files nothing, a good read ends the episode, and both loaders share the one table
        good = self._seed()
        with _fault_on(self.gp):
            for _ in range(3):
                self.assertIsNone(jd.load_goals_or_fault(SID)[0])
            self.assertEqual(self._errs(), ["store-unreadable"], "three loads, one episode, one row")
            self.assertEqual(jd.unreadable_store_sids(), [SID], "the episode stands")
        self.assertIsNone(jd.load_goals_or_fault(SID)[1], "readable again")
        self.assertEqual(jd.unreadable_store_sids(), [], "a good read ends the episode")
        with _fault_on(self.gp):
            self.assertIsNone(jd.load_goals_or_fault(SID)[0])
            self.assertEqual(self._errs(), ["store-unreadable"] * 2, "the next failure is a new episode and files again")
            self.assertIsNone(jd.load_goals_shared_or_fault(SID)[0], "the shared loader raises the same fault")
            self.assertEqual(self._errs(), ["store-unreadable"] * 2, "and shares the episode: no third row")
        self.assertEqual(self.gp.read_text(), good, "nothing was published through any of it")


class KernelWriter(_Store):
    def _archived(self):
        """The seeded goal's node held in the archive too, the shape an undo-clear restore reaches into."""
        self._seed()
        node = jd.load_goals(SID)["nodes"][NID]
        jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {NID: node}, "status": {NID: "working"}})

    def test_the_undo_clear_restore_over_a_store_that_does_not_read_skips_it_before_its_journal_row(self):
        # the one kernel.py writer that reached save_goals with a fallback (every other gesture returns early on
        # an empty node map): the user's undo-clear pulled the archived nodes into the fallback and published it
        # over the file. It reads through the boundary now (upstream #1019, steer 1): a store that does not read
        # is SKIPPED and named in the answer ({sid: fault}) before its journal row, so a restore that cannot land
        # leaves no row for the replay to carry, the archive keeps the node, and the boundary's row is the signal
        self._archived()
        good = self.gp.read_text()
        with _fault_on(self.gp):
            skipped = km._restore_goal_archive([NID])
        self.assertEqual(list(skipped), [SID], "the session is skipped and named, nothing raised")
        self.assertIn("Input/output error", skipped[SID])
        self.assertEqual(self.gp.read_text(), good, "the live file is left as it is")
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"], "the archive keeps the node: the restore did not half-land")
        self.assertEqual(self._journal_ops(), [], "no restore row for a restore that did not land")
        self.assertEqual(self._errs(), ["store-unreadable"], "the load's row; no save was attempted")

    def test_the_undo_clear_restore_over_an_unparseable_store_lands_in_the_fresh_store(self):
        # bytes that do not parse are quarantined (upstream #1019): the evidence is preserved aside and the
        # restore lands into the fresh store, journal row first, so nothing durable is lost either way
        self._archived()
        self.gp.write_text(CORRUPT)
        with contextlib.redirect_stderr(io.StringIO()):
            skipped = km._restore_goal_archive([NID])
        self.assertEqual(skipped, {}, "nothing to skip: the fresh store is legitimate")
        self.assertEqual([p.read_text() for p in self._aside()], [CORRUPT], "the bytes that did not parse are kept aside")
        self.assertIn(NID, jd.load_goals(SID)["nodes"], "restored into the fresh store")
        self.assertNotIn(NID, jd.load_goal_archive(SID)["nodes"])
        self.assertEqual(self._journal_ops(), ["restore"])
        self.assertEqual(self._errs(), ["store-quarantined"])


class UndoClear(_Store):
    """The review's reproduction, landed: an Undo over a session whose goals file did not read consumed the batch
    (the undo rows were written before the restore that then could not land) and stranded the card: the node
    stayed archived behind an orphan restore row, a second click found nothing to undo, and load_goals' replay
    defers to an archive that still holds the node. Under upstream #1019's owed/skip shape (steer 1 of the
    2026-09-08 fold, replacing this fork's UnreadStoreError raise) the session is skipped and named, its ids
    stay the newest batch, and nothing raises. The same at an archive that did not read."""

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
        self.assertEqual(km._undo_clear(), {}, "no session skipped")
        self.assertEqual(km._cleared_ids(), {}, "the batch is consumed")
        s = jd.load_goals(SID)
        self.assertIn(NID, s["nodes"])
        self.assertFalse(s["nodes"][NID].get("cleared"))
        self.assertNotIn(NID, jd.load_goal_archive(SID)["nodes"])

    def test_undo_lands_on_a_readable_store(self):
        self._cleared_and_compacted()
        self._undo_lands()

    def test_undo_over_a_store_that_does_not_read_stands_down_and_keeps_the_batch(self):
        good = self._cleared_and_compacted()
        with _fault_on(self.gp):
            skipped = km._undo_clear()                                   # no raise: the session is skipped and named
        self.assertEqual(list(skipped), [SID], "nothing was undone for it, and the answer says so")
        self.assertIn("Input/output error", skipped[SID])
        self.assertEqual(set(km._cleared_ids()), {NID}, "the batch is still undoable")
        self.assertIn(NID, jd.load_goal_archive(SID)["nodes"], "the node is still archived")
        self.assertEqual(self._journal_ops(), [], "no orphan restore row")
        self.assertEqual(self.gp.read_text(), good)
        self.assertEqual(self._errs(), ["store-unreadable"])
        self._undo_lands()                                               # the file reads again: the same click lands

    def test_undo_over_an_unparseable_store_lands_in_the_fresh_store(self):
        # (upstream #1019: the bytes are quarantined, the restore lands, the batch is consumed; nothing is lost)
        self._cleared_and_compacted()
        self.gp.write_text(CORRUPT)
        with contextlib.redirect_stderr(io.StringIO()):
            self._undo_lands()
        self.assertEqual([p.read_text() for p in self._aside()], [CORRUPT], "the bytes that did not parse are kept aside")
        self.assertEqual(self._errs(), ["store-quarantined"])

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_undo_over_an_unreadable_archive_stands_down(self):
        # pre-existing at the same site: load_goal_archive answered an empty archive for a file it could not read,
        # and the undo consumed the batch with no raise and nothing restored. The archive keeps this fork's mark
        # (#1019 does not touch it): the restore skips the session and names it, the batch stays owed
        self._cleared_and_compacted()
        ap = jd.GOALARCHDIR / (SID + ".json")
        os.chmod(ap, 0)
        try:
            skipped = km._undo_clear()
            self.assertEqual(list(skipped), [SID])
            self.assertIn("did not read", skipped[SID])
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
    holds for a listed session, the kernel says so to the chat clients once, and the /perf goals gauge counts it.
    The episode is the boundary's (jd.unreadable_store_sids reads jd._STORE_FAULTS, upstream #1019): what the
    pusher's reads of a live store meet every cycle, driven here through jd.load_goals_or_fault under a read
    fault, the one shape a standing fault has now (bytes that do not parse are quarantined, not an episode)."""

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
        self._seed()
        km._unreadable_store_warns(T0)
        self.assertEqual((self.sent, self._gauge()), ([], 0), "a readable store: nothing to say")
        with _fault_on(self.gp):
            jd.load_goals_or_fault(SID)
            jd.load_goals_or_fault(SID)
            km._unreadable_store_warns(T0 + 1)
            km._unreadable_store_warns(T0 + 2)
        self.assertEqual(len(self.sent), 1, "one warn frame per episode, not per pass")
        app, msg = self.sent[0]
        self.assertEqual((app, msg["type"]), ("chat", "warn"))
        self.assertIn("web", msg["text"])
        self.assertIn("goals/%s.json" % SID, msg["text"])
        self.assertEqual(self._gauge(), 1)
        jd.load_goals_or_fault(SID)                                      # a good read ends the episode
        km._unreadable_store_warns(T0 + 3)
        self.assertEqual((len(self.sent), self._gauge(), km._UNREADABLE_WARNED), (1, 0, set()),
                         "the episode's end clears the gauge and the said set")
        with _fault_on(self.gp):
            jd.load_goals_or_fault(SID)                                  # a new episode is said again
            km._unreadable_store_warns(T0 + 4)
        self.assertEqual(len(self.sent), 2)

    def test_an_unlisted_session_is_said_once_it_is_listed(self):
        self._seed()
        with _fault_on(self.gp):
            jd.load_goals_or_fault(SID)
        km._sessions = lambda now, window=None, forks=True: []
        km._unreadable_store_warns(T0)
        self.assertEqual(self.sent, [], "nothing shows the session: nothing to explain yet")
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "name": "web", "anchor": "", "path": "", "mtime": 0}]
        km._unreadable_store_warns(T0 + 1)
        self.assertEqual(len(self.sent), 1, "said once it is listed")


class UnmuteFastForward(_Store):
    def test_the_un_mute_fast_forward_raises_on_a_store_that_does_not_read(self):
        # the un-mute's fast-forward seals the muted stretch so the planner does not backfill it; over this fork's
        # fallback it sealed nothing real and its save was refused. Under upstream #1019 (steer 1) the load RAISES
        # instead: nothing is sealed, nothing is saved, the file is left as it is, and the kernel's un-mute wrapper
        # (its except: a stderr line) lets the flag change stand while the fast-forward waits for a readable store
        good = self._seed()
        with _fault_on(self.gp):
            with self.assertRaises(OSError):
                jd.fast_forward_placements(SID, path=str(Path(self.td.name) / "no-such-transcript.jsonl"))
        self.assertEqual(self.gp.read_text(), good, "nothing sealed, nothing saved")
        self.assertEqual(self._errs(), [], "the raise is the caller's to file")
        src = inspect.getsource(km._set_session_flag)
        i = src.index("jd.fast_forward_placements(sid)")
        self.assertIn("except Exception", src[i:i + 200], "the un-mute wrapper catches the raise: a stderr line, no crash")


class Archive(_Store):
    def test_an_unparseable_archive_is_marked_refused_and_left_by_the_sweep(self):
        # the archive twin of the live-store shape, and this fork's mark and refusal kept whole (#1019 does not touch
        # the archive): the compaction sweep loads the archive, adds the tops it moves and publishes; over a file that
        # did not read it published the empty fallback plus the moved tops
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
        # the sweep stands down BEFORE its save (the 2026-09-08 fold): _compact_goal_store answers None over an archive
        # that carries the mark, nothing moves, and the store is not marked seen, so the next sweep retries it
        self.assertIsNone(km._compact_goal_store(SID))
        km._compact_goal_stores()                                        # no raise out of the sweep
        self.assertNotIn(SID, km._compact_seen, "not recorded as seen: retried next sweep")
        self.assertEqual((ap.read_text(), self.gp.read_text()), (CORRUPT, live),
                         "neither file touched: the move did not half-land")
        self.assertEqual(self._errs(), ["archive-unreadable", "unread-store-save"],
                         "the read's row and the refusal this test asked for; the sweep never reaches the save")
        self.assertNotIn("_unread", jd.load_goal_archive(SID.replace("d", "e")), "an absent archive is not marked")


if __name__ == "__main__":
    unittest.main()
