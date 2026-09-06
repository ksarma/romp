#!/usr/bin/env python3
"""save_goals SKIPS a publish that would rewrite the file with identical content (the user 2026-07-22).

Callers save unconditionally by design: _plan_session ends every pass with a rollup + save whether or not
the pass placed anything. On an idle fleet that rewrote ~24 goal stores with byte-identical content roughly
ten times a second, with `rev` counters past 10,000 as the receipt.

The write itself is cheap; the damage is downstream. The kernel's _compact_goal_stores skips any store whose
mtime hasn't moved ("the steady state is just stats"), so a no-op republish moved every mtime every pass and
kept the sweep re-processing the whole live fleet forever. Skipping is safe BECAUSE nothing changed: a writer
with no events to contribute can neither lose its own work nor clobber a concurrent writer's.

All fixtures SYNTHETIC: placeholder UUID, invented goal text.
"""
import json
import os
import tempfile
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


class NoOpPublish(unittest.TestCase):
    def setUp(self):
        self._saved = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))

    def tearDown(self):
        jd._rebind_state(self._saved)
        self.td.cleanup()

    def _file(self):
        return jd.GOALDIR / (SID + ".json")

    def _seed(self):
        s = {"rompUuid": SID, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {},
             "placements": {}, "status": {}}
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "A goal"}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)

    # ── the fix ─────────────────────────────────────────────────────────────
    def test_an_unchanged_store_is_not_republished(self):
        self._seed()
        rev, mt = jd._disk_rev(SID), os.stat(self._file()).st_mtime_ns
        jd.save_goals(SID, jd.load_goals(SID))
        self.assertEqual(jd._disk_rev(SID), rev, "a no-op publish does not advance the revision")
        self.assertEqual(os.stat(self._file()).st_mtime_ns, mt,
                         "...and does not touch the file, so the compaction sweep can skip it")

    def test_a_storm_of_no_op_passes_leaves_the_store_alone(self):
        """The reported symptom: pass after pass rewriting the same bytes."""
        self._seed()
        rev, mt = jd._disk_rev(SID), os.stat(self._file()).st_mtime_ns
        for _ in range(10):
            jd.save_goals(SID, jd.load_goals(SID))
        self.assertEqual(jd._disk_rev(SID), rev, "ten idle passes, zero publications")
        self.assertEqual(os.stat(self._file()).st_mtime_ns, mt)

    # ── what must still happen ──────────────────────────────────────────────
    def test_a_changed_store_is_published(self):
        self._seed()
        rev = jd._disk_rev(SID)
        s = jd.load_goals(SID)
        jd.apply_plan(s, "s2", T0 + 60, [{"do": "mint", "why": "y", "text": "A second goal"}],
                      jd.open_menu(s) if hasattr(jd, "open_menu") else [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        self.assertGreater(jd._disk_rev(SID), rev, "a real change still advances the revision")
        self.assertEqual(len(json.loads(self._file().read_text())["nodes"]), 2,
                         "...and the new node is on disk")

    def test_a_first_publish_creates_the_file(self):
        self.assertFalse(self._file().exists())
        self._seed()
        self.assertTrue(self._file().exists(), "an absent file is a publish, never a no-op")

    def test_a_store_built_without_load_goals_still_publishes(self):
        """No _baseRev means no known base to compare against — keep the old unconditional behaviour."""
        self._seed()
        rev = jd._disk_rev(SID)
        raw = json.loads(self._file().read_text())      # hand-built store, never through load_goals
        self.assertNotIn("_baseRev", raw)
        jd.save_goals(SID, raw)
        self.assertGreater(jd._disk_rev(SID), rev)

    def test_a_no_op_save_cannot_clobber_a_concurrent_writer(self):
        """Pass A loads and changes nothing; writer B publishes a real event meanwhile. The skip compares
        against DISK, and disk has moved, so A does NOT skip here — it takes the rebase path and folds B's
        event in. That is the correct outcome and the guarantee that matters: an empty-handed writer never
        rolls a concurrent one back. (The storm this fix targets is the single-writer case below, where disk
        is unchanged too.)"""
        self._seed()
        a = jd.load_goals(SID)                          # A's snapshot, held across its model call
        b = jd.load_goals(SID)
        gid = "%s:g1" % SID
        jd.record_verdict(b, b["nodes"][gid], "romp", "block", T0 + 30, why="needs a decision")
        jd.rollup_status(b, session_closed=False)
        jd.save_goals(SID, b)
        jd.save_goals(SID, a)                           # A has nothing of its own to add
        disk = json.loads(self._file().read_text())
        self.assertTrue(any(r.get("kind") == "block" for r in disk["nodes"][gid].get("log", [])),
                        "B's block survives A's save")

    def test_content_signature_ignores_rev_and_the_transient_base(self):
        s = {"rompUuid": SID, "nodes": {}, "rev": 7, "_baseRev": 7}
        t = {"nodes": {}, "rompUuid": SID, "rev": 999}
        self.assertEqual(jd._store_content(s), jd._store_content(t),
                         "same content, different revision + key order → the same publish")

    def test_an_unreadable_file_falls_through_to_a_real_write(self):
        self._seed()
        self._file().write_text("{not json")
        s = jd.load_goals(SID)                          # load recovers a fresh store
        jd.save_goals(SID, s)
        self.assertEqual(json.loads(self._file().read_text())["rompUuid"], SID,
                         "an unparseable file is republished, never mistaken for a match")


class DiskMemo(unittest.TestCase):
    """The disk side of the no-op check is memoized by file identity (2026-09-06).

    Every save asked "does the file already hold exactly this?" by re-reading and re-parsing the file and
    serializing both sides, then the CAS parsed the file twice more for its revision: about 20 ms per save
    of a large store, most saves being no-ops. Now _disk_entry keys the file's canonical-content hash on
    (inode, mtime_ns, size), taken from the same descriptor the bytes are read from; a save whose file
    identity still matches serializes only its own side. Every publish is a rename of a fresh temp, so a
    changed file is a new identity and the memo can never answer True where the full compare would answer
    False. The CAS's revision is read from the file, never the memo (the tests under "the CAS reads the
    file" say why). Synthetic fixtures only; a private sid, so no other module's journal reaches it.
    """
    SID = "0b400000-1111-2222-3333-444444444444"

    def setUp(self):
        self._saved = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))
        self.reads = []                                  # store paths the memo read
        self._orig_read = jd._disk_read
        self._orig_content = jd._store_content
        self.content_calls = [0]

        def counting_read(fd, path_s):
            if path_s.endswith(self.SID + ".json"):
                self.reads.append(path_s)
            return self._orig_read(fd, path_s)

        def counting_content(store):
            self.content_calls[0] += 1
            return self._orig_content(store)
        jd._disk_read = counting_read
        jd._store_content = counting_content

    def tearDown(self):
        jd._disk_read = self._orig_read
        jd._store_content = self._orig_content
        jd._rebind_state(self._saved)
        self.td.cleanup()

    def _file(self):
        return jd.GOALDIR / (self.SID + ".json")

    def _seed(self):
        s = {"rompUuid": self.SID, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {},
             "placements": {}, "status": {}}
        jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "A goal"}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(self.SID, s)                        # no _baseRev: an unconditional publish, no memo entry
        jd._disk_forget(str(self._file()))

    def _foreign_replace(self, disk):
        """A writer outside this process publishes `disk` the way every writer does: a fresh temp renamed
        over the store. Also moves the mtime by a whole second, because a CI filesystem's timestamp tick
        can be coarser than the gap between two statements."""
        tmp = self._file().with_suffix(".json.foreign")
        tmp.write_text(json.dumps(disk))
        st = os.stat(self._file())
        os.utime(tmp, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        os.replace(tmp, self._file())

    def _ident(self, path):
        st = os.stat(path)
        return (st.st_ino, st.st_mtime_ns, st.st_size)

    # ── the saving ───────────────────────────────────────────────────────────
    def test_a_warm_no_op_save_reads_nothing_and_serializes_only_its_own_side(self):
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm-up: one read and parse of the file
        self.assertEqual(len(self.reads), 1, "the first check after a foreign publish parses the file once")
        del self.reads[:]
        self.content_calls[0] = 0
        before = jd.goal_io_stats()
        for _ in range(5):
            jd.save_goals(self.SID, s)
        self.assertEqual(self.reads, [], "a warm no-op save performs zero reads of the store path")
        self.assertEqual(self.content_calls[0], 5, "one serialization per save: the in-memory side only")
        after = jd.goal_io_stats()
        self.assertEqual(after["disk_hits"], before["disk_hits"] + 5)
        self.assertEqual(after["disk_misses"], before["disk_misses"])
        self.assertEqual(after["writes"], before["writes"], "and still no write")

    def test_a_real_publish_reads_the_file_once_for_the_cas(self):
        """The check is served by the memo when warm; the CAS reads the file every time (its revision must be
        the file's: test_a_stale_memo_identity_never_passes_the_cas). So a real publish on a warm memo is one
        read, one hit and no miss; on a cold memo two reads and one miss. Both the read seam and the counters
        are asserted: a _disk_rev served from the memo shows as a second hit and no read, and one reading by a
        path of its own shows as no read at all."""
        self._seed()
        gid = "%s:g1" % self.SID
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm the memo (one miss)
        jd.record_verdict(s, s["nodes"][gid], "planner", "block", T0 + 30, why="needs a decision")
        jd.rollup_status(s, session_closed=False)
        del self.reads[:]
        before = jd.goal_io_stats()
        jd.save_goals(self.SID, s)
        after = jd.goal_io_stats()
        self.assertEqual(len(self.reads), 1, "warm: the check hit, the CAS read the file")
        self.assertEqual(after["disk_hits"], before["disk_hits"] + 1)
        self.assertEqual(after["disk_misses"], before["disk_misses"])
        self.assertEqual(after["writes"], before["writes"] + 1)
        self.assertEqual(json.loads(self._file().read_text())["rev"], 2)
        disk = json.loads(self._file().read_text())
        disk["nodes"][gid]["summary"] = "Written by another process."
        disk["rev"] = 5
        self._foreign_replace(disk)                       # the memo is cold again
        s = jd.load_goals(self.SID)
        jd.record_verdict(s, s["nodes"][gid], "closer", "done", T0 + 40, why="shipped")
        del self.reads[:]
        before = jd.goal_io_stats()
        jd.save_goals(self.SID, s)
        after = jd.goal_io_stats()
        self.assertEqual(len(self.reads), 2, "cold: the check missed and read, then the CAS read")
        self.assertEqual(after["disk_misses"], before["disk_misses"] + 1)
        self.assertEqual(after["disk_hits"], before["disk_hits"])
        self.assertEqual(json.loads(self._file().read_text())["rev"], 6)

    def test_a_publish_seeds_the_memo_so_the_next_check_reads_nothing(self):
        self._seed()
        s = jd.load_goals(self.SID)
        gid = "%s:g1" % self.SID
        jd.record_verdict(s, s["nodes"][gid], "planner", "block", T0 + 30, why="needs a decision")
        jd.rollup_status(s, session_closed=False)
        before = jd.goal_io_stats()
        jd.save_goals(self.SID, s)                        # a real publish, no rebase: seeds from its temp
        self.assertEqual(jd.goal_io_stats()["disk_seeds"], before["disk_seeds"] + 1)
        ent = jd._DISK_CONTENT[str(self._file())]
        self.assertEqual(ent[0], self._ident(self._file()),
                         "the temp's identity survives the rename: inode, mtime_ns and size all match the destination")
        del self.reads[:]
        jd.save_goals(self.SID, jd.load_goals(self.SID))  # the next no-op check
        self.assertEqual(self.reads, [], "served from the seed: no read")

    def test_the_seed_is_taken_from_the_temp_before_the_rename(self):
        """Pins the order _disk_seed's docstring states: the identity recorded is the TEMP's, read while the
        temp still exists and before it is renamed over the destination. A seed taken from the destination
        after the rename would record whatever file is there by then, a concurrent publisher's included, and
        pair it with our hash. The spy asserts at call time."""
        self._seed()
        dest = self._file()
        s = jd.load_goals(self.SID)
        gid = "%s:g1" % self.SID
        jd.record_verdict(s, s["nodes"][gid], "planner", "block", T0 + 30, why="needs a decision")
        jd.rollup_status(s, session_closed=False)
        dest_before = self._ident(dest)
        orig = jd._disk_seed
        calls = []

        def spy(path, tmp, canon_hash):
            calls.append(str(tmp))
            self.assertEqual(str(path), str(dest))
            self.assertNotEqual(str(tmp), str(dest), "seeded from the temp, not the destination")
            self.assertTrue(os.path.exists(tmp), "the temp still exists: it has not been renamed yet")
            self.assertEqual(self._ident(dest), dest_before, "the destination is still the old file")
            recorded = self._ident(tmp)
            self.assertNotEqual(recorded, dest_before)
            orig(path, tmp, canon_hash)
            self.assertEqual(jd._DISK_CONTENT[str(dest)][0], recorded, "what went into the memo is the temp's identity")
        jd._disk_seed = spy
        try:
            jd.save_goals(self.SID, s)
        finally:
            jd._disk_seed = orig
        self.assertEqual(len(calls), 1)
        self.assertEqual(jd._DISK_CONTENT[str(dest)][0], self._ident(dest), "which the rename carried to the destination")

    def test_a_rebased_publish_does_not_seed(self):
        """After a rebase the store no longer has the content the pre-rebase hash describes."""
        self._seed()
        gid = "%s:g1" % self.SID
        a, b = jd.load_goals(self.SID), jd.load_goals(self.SID)
        jd.record_verdict(b, b["nodes"][gid], "closer", "done", T0 + 60, why="b's done")
        jd.save_goals(self.SID, b)
        jd.record_verdict(a, a["nodes"][gid], "planner", "block", T0 + 50, why="a's block")
        seeds = jd.goal_io_stats()["disk_seeds"]
        jd.save_goals(self.SID, a)                        # base moved: rebases, then publishes
        self.assertEqual(jd.goal_io_stats()["disk_seeds"], seeds, "no seed after a rebase")
        ent = jd._DISK_CONTENT.get(str(self._file()))
        self.assertTrue(ent is None or ent[0] != self._ident(self._file()),
                        "the memo holds no entry claiming the rebased file's identity")
        del self.reads[:]
        jd.save_goals(self.SID, jd.load_goals(self.SID))
        self.assertEqual(len(self.reads), 1, "so the next check parses the file (and finds a no-op)")

    # ── what a changed file must still do ────────────────────────────────────
    def test_a_foreign_atomic_replace_with_different_content_is_detected(self):
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm
        disk = json.loads(self._file().read_text())
        disk["nodes"]["%s:g1" % self.SID]["summary"] = "Written by another process."
        self._foreign_replace(disk)
        self.assertFalse(jd._matches_disk(self.SID, s), "a changed file is never mistaken for the memoized one")
        self.assertEqual(len(self.reads), 2, "the new identity misses and is parsed")

    def test_a_same_size_replace_inside_the_same_mtime_tick_is_told_apart_by_its_inode(self):
        """The inode carries the headline invariant. Every publish is a rename of a fresh temp, and on kernels
        with coarse file timestamps two publishes of a same-size store can share an mtime_ns; the new file is
        then a different inode and nothing else. Staged with the temp's mtime pinned to the destination's."""
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm
        dest = self._file()
        st = os.stat(dest)
        raw = dest.read_text()
        self.assertIn('"text": "A goal"', raw)
        tmp = dest.with_suffix(".json.foreign")
        tmp.write_text(raw.replace('"text": "A goal"', '"text": "B goal"'))    # same length
        os.utime(tmp, ns=(st.st_atime_ns, st.st_mtime_ns))                   # same tick, staged
        os.replace(tmp, dest)
        new = os.stat(dest)
        self.assertEqual((new.st_mtime_ns, new.st_size), (st.st_mtime_ns, st.st_size), "only the inode differs")
        self.assertNotEqual(new.st_ino, st.st_ino)
        self.assertFalse(jd._matches_disk(self.SID, s), "a new inode is a new file")
        self.assertEqual(jd._DISK_CONTENT[str(dest)][0][0], new.st_ino, "and the memo now records it")
        self.assertNotEqual(jd._DISK_CONTENT[str(dest)][0][0], st.st_ino)

    def test_a_different_length_in_place_rewrite_inside_the_same_mtime_tick_is_told_apart_by_its_size(self):
        """The size twin: same inode, same mtime_ns, different length. No writer here rewrites a store in
        place, so this is defence in depth for the key's third component."""
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)
        dest = self._file()
        st = os.stat(dest)
        raw = dest.read_text()
        dest.write_text(raw.replace('"text": "A goal"', '"text": "A longer goal"'))   # in place: the inode stays
        os.utime(dest, ns=(st.st_atime_ns, st.st_mtime_ns))
        new = os.stat(dest)
        self.assertEqual((new.st_ino, new.st_mtime_ns), (st.st_ino, st.st_mtime_ns), "only the size differs")
        self.assertNotEqual(new.st_size, st.st_size)
        self.assertFalse(jd._matches_disk(self.SID, s))

    def test_a_same_size_in_place_rewrite_with_a_new_mtime_is_detected(self):
        """The mtime part of the key: same inode, same size, different bytes."""
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)
        raw = self._file().read_text()
        self.assertIn('"text": "A goal"', raw)
        changed = raw.replace('"text": "A goal"', '"text": "B goal"')     # same length
        self.assertEqual(len(changed), len(raw))
        st = os.stat(self._file())
        self._file().write_text(changed)                  # in place: the inode stays
        os.utime(self._file(), ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        self.assertFalse(jd._matches_disk(self.SID, s))

    def test_a_replace_landing_between_the_open_and_the_stat_cannot_pair_the_new_identity_with_the_old_bytes(self):
        """The identity is fstat of the descriptor the bytes are read from. A publisher landing between the
        open and the stat is the case a stat by path gets wrong: it records the NEW file's identity with the
        OLD file's content, and every later check of the new file hits that entry and answers for content the
        file does not hold. Staged inside the identity seam itself, so the order is open, replace, stat, read."""
        self._seed()
        s = jd.load_goals(self.SID)
        old_ident = self._ident(self._file())
        old_disk = json.loads(self._file().read_text())
        new_disk = json.loads(self._file().read_text())
        new_disk["nodes"]["%s:g1" % self.SID]["summary"] = "Landed between the open and the stat."
        inner = jd._disk_ident
        fired = []

        def racing_ident(fd):
            if not fired:
                fired.append(1)
                self._foreign_replace(new_disk)           # a new inode, mtime and size while the fd is open
            return inner(fd)
        jd._disk_ident = racing_ident
        try:
            ent = jd._disk_entry(self.SID)                # cold memo: open, the race, then stat and read
        finally:
            jd._disk_ident = inner
        self.assertEqual(len(fired), 1)
        new_ident = self._ident(self._file())
        self.assertNotEqual(old_ident, new_ident)
        self.assertEqual(ent[0], old_ident, "the identity is the opened file's")
        self.assertEqual(ent[1], jd._content_hash(jd._store_content(old_disk)), "and so are the bytes")
        self.assertFalse(jd._matches_disk(self.SID, s), "the next check misses on the new identity, parses, and says no")
        self.assertEqual(jd._DISK_CONTENT[str(self._file())][0], new_ident)

    def test_a_same_size_different_store_under_a_bare_goaldir_reassignment_answers_false(self):
        """Keyed on the full path: a test that reassigns jd.GOALDIR (not _rebind_state) must not be served
        the other root's entry."""
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm under root A
        raw = self._file().read_text()
        other = Path(self.td.name) / "other-goals"
        other.mkdir()
        (other / (self.SID + ".json")).write_text(raw.replace('"text": "A goal"', '"text": "B goal"'))
        st = os.stat(self._file())
        os.utime(other / (self.SID + ".json"), ns=(st.st_atime_ns, st.st_mtime_ns))   # same mtime and size
        saved = jd.GOALDIR
        try:
            jd.GOALDIR = other
            self.assertFalse(jd._matches_disk(self.SID, s))
        finally:
            jd.GOALDIR = saved
        self.assertTrue(jd._matches_disk(self.SID, s), "root A's entry still answers for root A")

    # ── the CAS reads the file, never the memo ───────────────────────────────
    def test_disk_rev_reads_the_file_even_when_the_memo_identity_matches(self):
        """The CAS's revision comes from the file. With a staged identity collision (same inode, size and
        mtime_ns, different bytes) the memo may still serve the no-op check, whose worst case is a skipped
        publish of content the file once held; _disk_rev must report what the file holds now."""
        self._seed()
        dest = self._file()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)                        # warm: the memo describes revision 1
        raw = dest.read_text()
        self.assertEqual(raw.count('"rev": 1'), 1)
        st = os.stat(dest)
        dest.write_text(raw.replace('"rev": 1', '"rev": 7'))       # in place: same inode, same size
        os.utime(dest, ns=(st.st_atime_ns, st.st_mtime_ns))          # same tick: the collision, staged
        self.assertEqual(self._ident(dest), jd._DISK_CONTENT[str(dest)][0], "the memo's identity matches the file")
        self.assertEqual(jd._disk_rev(self.SID), 7, "and the CAS still sees the file's revision")

    def test_a_stale_memo_identity_never_passes_the_cas(self):
        """Found in review (2026-09-06). Three publishes of one store inside one mtime tick can leave the
        memo's identity on a file the memo does not describe: K publishes and seeds; B and C, holding older
        snapshots, both check and pass the CAS against K's file, rebase, and publish in turn; C's temp is
        created after B's rename freed K's inode and gets it back, at K's size, in K's tick. The memo still
        says K; the file is C's. A writer E that loaded K's file now hits the memo, and a CAS served from the
        memo would see K's revision, skip the rebase and write over C's event. So the CAS reads the file.
        Staged here: the inode by a kept hard link, the tick by os.utime, the size by padding C's JSON with
        trailing spaces; the interleaving is real save_goals calls, B's run from inside C's _publish_tmp."""
        self._seed()                                      # revision 1
        gid = "%s:g1" % self.SID
        dest = self._file()
        b, c = jd.load_goals(self.SID), jd.load_goals(self.SID)      # revision-1 snapshots
        k = jd.load_goals(self.SID)
        k["nodes"][gid]["text"] = "A goal, restated at length " + "x" * 600
        jd.save_goals(self.SID, k)                        # revision 2; seeds the memo with K's temp identity
        k_st = os.stat(dest)
        k_ident = (k_st.st_ino, k_st.st_mtime_ns, k_st.st_size)
        self.assertEqual(jd._DISK_CONTENT[str(dest)][0], k_ident)
        e = jd.load_goals(self.SID)                       # E holds K's revision
        keep = jd.GOALDIR / (self.SID + ".keep")          # K's inode stays allocated across B's rename
        os.link(dest, keep)
        jd.record_verdict(b, b["nodes"][gid], "planner", "note", T0 + 50, why="b's note")
        jd.record_verdict(c, c["nodes"][gid], "nudge", "block", T0 + 60, why="c's block")
        orig = jd._publish_tmp
        fired = []

        class PinnedTemp(type(Path())):
            """C's temp: written in place into K's inode, padded to K's size, stamped with K's mtime."""
            def write_text(self_, data, *a, **kw):
                pad = k_st.st_size - len(data.encode("utf-8"))
                assert pad >= 0, "fixture: C's rebased store must not outgrow K's"
                n = super().write_text(data + " " * pad, *a, **kw)
                os.utime(self_, ns=(k_st.st_atime_ns, k_st.st_mtime_ns))
                return n

        def hooked(dirpath, fsid):
            jd._publish_tmp = orig
            jd.save_goals(self.SID, b)                    # B lands first: K's inode leaves the path
            tmp = PinnedTemp(orig(dirpath, fsid))
            os.rename(keep, tmp)                          # and is handed to C's temp
            fired.append(tmp)
            return tmp
        jd._publish_tmp = hooked
        try:
            jd.save_goals(self.SID, c)                    # C: check and CAS against K's file, then the hook
        finally:
            jd._publish_tmp = orig
        self.assertEqual(len(fired), 1)
        self.assertEqual(json.loads(dest.read_text())["rev"], 3)
        self.assertEqual(self._ident(dest), k_ident, "staged: C's file carries K's identity")
        self.assertEqual(jd._DISK_CONTENT[str(dest)][0], k_ident, "and the memo still describes K")
        jd.record_verdict(e, e["nodes"][gid], "planner", "note", T0 + 70, why="e's note")
        jd.save_goals(self.SID, e)                        # base 2; the file holds 3
        disk = json.loads(dest.read_text())
        kinds = {(x.get("src"), x.get("kind")) for x in disk["nodes"][gid].get("log") or []}
        self.assertIn(("nudge", "block"), kinds, "C's event survives E's publish")
        self.assertEqual(disk["rev"], 4, "E rebased onto the file's revision, not the memo's")

    def test_a_concurrent_publish_between_a_publish_and_a_save_is_detected_and_rebased(self):
        self._seed()
        gid = "%s:g1" % self.SID
        a = jd.load_goals(self.SID)
        jd.save_goals(self.SID, a)                        # A warms the memo with the seeded file
        b = jd.load_goals(self.SID)
        jd.record_verdict(b, b["nodes"][gid], "nudge", "block", T0 + 100, why="owed")
        jd.rollup_status(b, session_closed=False)
        jd.save_goals(self.SID, b)                        # the concurrent publish (rev 2)
        jd.record_verdict(a, a["nodes"][gid], "planner", "note", T0 + 110, why="a's own event")
        jd.save_goals(self.SID, a)                        # A: content differs, base 1 != disk 2 -> rebase
        disk = json.loads(self._file().read_text())
        kinds = {(e.get("src"), e.get("kind")) for e in disk["nodes"][gid].get("log") or []}
        self.assertIn(("nudge", "block"), kinds, "the concurrent writer's event survives")
        self.assertIn(("planner", "note"), kinds, "and so does A's")
        self.assertEqual(disk["rev"], 3)

    def test_disk_rev_follows_a_publish_and_a_foreign_write(self):
        self._seed()
        self.assertEqual(jd._disk_rev(self.SID), 1)
        s = jd.load_goals(self.SID)
        jd.record_verdict(s, s["nodes"]["%s:g1" % self.SID], "planner", "block", T0 + 30, why="x")
        jd.save_goals(self.SID, s)
        self.assertEqual(jd._disk_rev(self.SID), 2, "the revision after our own publish")
        disk = json.loads(self._file().read_text())
        disk["rev"] = 42
        self._foreign_replace(disk)
        self.assertEqual(jd._disk_rev(self.SID), 42, "the revision after a foreign write")
        self._file().unlink()
        self.assertEqual(jd._disk_rev(self.SID), 0, "absent: 0")
        self.assertIsNone(jd._disk_entry(self.SID), "and the no-op check finds nothing")
        self.assertNotIn(str(self._file()), jd._DISK_CONTENT, "the entry is gone")

    def test_an_unreadable_file_drops_the_entry_and_answers_false(self):
        self._seed()
        s = jd.load_goals(self.SID)
        jd.save_goals(self.SID, s)
        self.assertIn(str(self._file()), jd._DISK_CONTENT)
        st = os.stat(self._file())
        self._file().write_text("{not json")
        os.utime(self._file(), ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        self.assertFalse(jd._matches_disk(self.SID, s))
        self.assertNotIn(str(self._file()), jd._DISK_CONTENT, "nothing to remember about a non-store")

    # ── housekeeping ─────────────────────────────────────────────────────────
    def test_rebind_state_clears_the_memo(self):
        self._seed()
        jd.save_goals(self.SID, jd.load_goals(self.SID))
        self.assertTrue(jd._DISK_CONTENT)
        jd._rebind_state(Path(self.td.name) / "elsewhere")
        self.assertEqual(jd._DISK_CONTENT, {})

    def test_evict_absent_drops_removed_stores_and_keeps_present_ones(self):
        self._seed()
        jd.save_goals(self.SID, jd.load_goals(self.SID))
        other = "0b400000-aaaa-bbbb-cccc-dddddddddddd"
        s2 = {"rompUuid": other, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {}, "placements": {}, "status": {}}
        jd.save_goals(other, s2)
        jd.save_goals(other, jd.load_goals(other))
        self.assertEqual(set(jd._DISK_CONTENT), {str(self._file()), str(jd.GOALDIR / (other + ".json"))})
        (jd.GOALDIR / (other + ".json")).unlink()
        self.assertEqual(jd._disk_memo_evict_absent(), 1)
        self.assertEqual(set(jd._DISK_CONTENT), {str(self._file())})


if __name__ == "__main__":
    unittest.main()
