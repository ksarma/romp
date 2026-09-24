#!/usr/bin/env python3
"""The lazy assembly index's materialized-atom LRU holds each turn's atom list WEAKLY, and a dropped assembly entry releases
its index's entries at once (measured 2026-09-15). The LRU mapped (id(atoms), row) to (atoms, row): a strong reference to
the LazyAtoms, and through it to the LazyIndex, its rows and its document, for every materialized atom, evicted only past
the cap; every restore mints a new index, so 262 restores over 22 sessions sat the LRU exactly at its cap of 1,026,886
entries holding mostly superseded generations (about 1.2 GiB at 1.3 to 2.1 KB an atom), and live atoms evicted by stale
ones were rebuilt (7.4 M row decodes). Pinned here: a tree nobody holds is collected with its index and its entries leave
at the next registration or release; an assembly entry that is dropped or replaced (the whole parse's put over a full cache,
the demotion, the refused row) releases its index's entries and the current index's memo is untouched; a retained old view
rebuilds a released slot through its own index, registers again, and takes nothing with it when it goes; the eviction pass
tells a live entry (evictions) from a collected list's (expired) and touches no live slot for the latter; the LRU touch
still orders evictions; an atom handed out is a fixed value across an eviction and a release; two threads building one
slot share one object and one entry; a dead entry under a reused id is absent to the new list.

The collection event (2026-09-24, CollectionEvent below): entries registered after a release (a tree that outlived its
assembly entry reading a released slot again) belong to an index nothing releases again, so when that tree went they
stood dead until the cap, and the cap (MemTotal / 32 KiB) never came: 6.15 million entries against a 7.73 million cap after
73 hours, at least 87 percent of them for freed lists. Each list's own weak reference now queues itself when the list is
freed, and the next registration or release removes that list's entries, counted `collected` and `expired`. Synthetic
documents only."""
import copy
import gc
import json
import operator
import os
import sys
import threading
import unittest
import weakref
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import test_asm_checkpoint as T                                   # noqa: E402  the stage 4a harness: the state root is floored
em, G = T.em, T.G                                                 #             before the event model loads, no host is started
SID = T.SID


def _syn_rows(n, tag):
    """n synthesized atom rows (a `syn` row needs no record): the index builds each as its scalars plus its inline message."""
    return [json.dumps({"syn": True, "s": {"uuid": "11111111-2222-3333-4444-%04x%08d" % (ord(tag[0]), k), "type": "assistant",
                                           "t": 1000 + k, "author": "impl"},
                        "m": {"role": "assistant", "content": [{"type": "text", "text": "row %d of %s" % (k, tag)}]}}) for k in range(n)]


def _mint(n, tag):
    """A real LazyIndex over n synthetic rows and one LazyAtoms over all of them, the way a restore mints a pre-cut turn's."""
    ix = em.LazyIndex({"atoms": _syn_rows(n, tag), "records": [], "fsids": []}, SID, "/TESTDIR/%s.jsonl" % tag)
    return ix, em.LazyAtoms(ix, range(n))


def _entries(list_id=None):
    """(live, dead) over the LRU's entries, all of them or those keyed under one list's id."""
    with em._MAT_LOCK:
        ents = [(k, v) for k, v in em._MAT_LRU.items() if list_id is None or k[0] == list_id]
    def alive(v):                                       # (ref, row) on the branch; (list, row) on a source that held the list
        head = v[0]                                     #  strongly, so the module reds there on the retention assertions
        return (head() if isinstance(head, weakref.ref) else head) is not None
    live = sum(1 for _, v in ents if alive(v))
    return live, len(ents) - live


def _built(la):
    """Which slots of la hold a built atom, read through the list's storage (no build)."""
    return [i for i in range(len(la)) if list.__getitem__(la, i) is not em._UNMAT]


def _reset():
    with em._MAT_LOCK:                                             # the LRU and its counters are process-wide: per test
        em._MAT_LRU.clear()
        em._ASM_INDEX_STATS.update(materialized=0, materializedBy={}, materializedByStage={}, resident=0, evictions=0,
                                   released=0, expired=0, collected=0)
        q = getattr(em, "_MAT_COLLECTED", None)                    # getattr: this file run against a source without the queue
        if q is not None:                                          #  reds on behaviour, not at every setUp on the name
            q.clear()


class Synthetic(unittest.TestCase):
    def setUp(self):
        self._cap = em._MAT_CAP
        _reset()

    def tearDown(self):
        em._MAT_CAP = self._cap
        _reset()


class Retention(Synthetic):
    def test_a_tree_nobody_holds_is_collected_and_its_entries_expire_at_the_next_pass(self):
        """Red on main: the LRU's strong reference pinned the list, and the index behind it, past the last consumer."""
        k = 5
        ix, la = _mint(k, "a")
        held = [la[i] for i in range(k)]
        self.assertEqual(_entries(id(la)), (k, 0))
        wi, wl = weakref.ref(ix), weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl(), "the LRU held the list strongly")
        self.assertIsNone(wi(), "...and the index, its rows and its document behind it")
        self.assertEqual(_entries(), (0, k), "its entries stand dead until the next registration or release")
        self.assertEqual(em.asm_index_stats()["resident"], k, "resident counts them until then: the read drains nothing")
        self.assertEqual([a["t"] for a in held], [1000 + i for i in range(k)], "the atoms a consumer holds are values, whole")
        em._MAT_CAP = 1                                            # the next LRU operation, a live list building one atom, under a
        ix2, la2 = _mint(1, "b")                                   #  cap the dead entries are over too: they leave, and the live
        la2[0]                                                     #  entry is not evicted for them
        st = em.asm_index_stats()
        self.assertEqual(_entries(), (1, 0), "the dead entries left, the live one stands")
        self.assertEqual((st["expired"], st["evictions"], st["resident"]), (k, 0, 1))

    def test_release_pops_the_indexs_entries_and_a_second_release_is_a_no_op(self):
        ix, la = _mint(4, "a")
        for i in range(3):
            la[i]
        r0 = em.asm_index_stats()["resident"]
        self.assertEqual(ix.release(), 3)
        st = em.asm_index_stats()
        self.assertEqual((st["released"], st["resident"]), (3, r0 - 3))
        self.assertEqual(_entries(id(la)), (0, 0)); self.assertEqual(_built(la), [])
        self.assertEqual(ix.release(), 0); self.assertEqual(em.asm_index_stats()["released"], 3)
        em._asm_release(None); em._asm_release({"atoms": []})    # no entry, a whole parse's entry: nothing to release


class Accounting(Synthetic):
    def test_live_entries_are_evicted_and_collected_ones_expire_touching_no_live_slot(self):
        em._MAT_CAP = 4
        ixb, lb = _mint(2, "b")
        lb[0]; lb[1]                                               # B's two entries first: the old end
        ixa, la = _mint(6, "a")
        la[0]; la[1]                                               # then A's two: the LRU is exactly at its cap
        self.assertEqual(em.asm_index_stats()["resident"], 4)
        del ixb, lb
        gc.collect()
        self.assertEqual(_entries(), (2, 2), "B's entries stand dead at the old end until the next LRU operation")
        la[2]                                                      # the next LRU operation: both of B's dead entries leave at once,
        st = em.asm_index_stats()                                  #  at the drain before the registration, and no live entry is
        self.assertEqual((st["expired"], st["evictions"]), (2, 0))  #  evicted for them
        self.assertEqual(_built(la), [0, 1, 2], "no slot of the live list is touched for a dead entry")
        la[3]
        st = em.asm_index_stats()
        self.assertEqual((st["expired"], st["evictions"]), (2, 0)); self.assertEqual(_entries(), (4, 0))
        la[4]                                                      # the oldest is now A's own slot 0: a live eviction
        st = em.asm_index_stats()
        self.assertEqual((st["expired"], st["evictions"], st["resident"]), (2, 1, 4))
        self.assertIs(list.__getitem__(la, 0), em._UNMAT, "the evicted slot reads the placeholder through the storage")
        self.assertEqual(_built(la), [1, 2, 3, 4])
        la[1]                                                      # the LRU touch: slot 1 is young again
        la[5]                                                      # ...so the eviction takes slot 2, not 1
        self.assertEqual(_built(la), [1, 3, 4, 5]); self.assertEqual(em.asm_index_stats()["evictions"], 2)

    def test_a_dead_entry_the_queue_never_saw_is_expired_by_the_trim_and_not_counted_collected(self):
        """The trim's dead branch stays for an entry whose reference is dead but was never queued: a list freed on another
        thread in the moment between the collector clearing its reference and its callback queuing it, or an entry planted
        with another reference, as here. The trim drops it as `expired` without `collected`, which is why expired minus
        collected can rise without a missed callback once the cap binds."""
        gx, gone = _mint(1, "u")
        dead = weakref.ref(gone)                                   # a plain reference: no callback, never queued
        del gx, gone
        gc.collect()
        self.assertIsNone(dead())
        em._MAT_CAP = 2
        with em._MAT_LOCK:
            em._MAT_LRU[("TESTKEY", 0)] = (dead, 0)                # at the old end, under a key no list can hold
        ixa, la = _mint(2, "v")
        la[0]; la[1]                                               # the second build is one over the cap: the dead entry goes
        self.assertEqual(_entries(), (2, 0), "the dead entry left, both live ones stand")
        st = em.asm_index_stats()
        self.assertEqual((st["expired"], st["evictions"]), (1, 0), "dropped as dead, no live slot evicted for it")
        self.assertEqual(st["collected"], 0, "the trim counts it expired only: the drain never saw it")


class Values(Synthetic):
    def test_an_atom_handed_out_is_unchanged_by_an_eviction_and_by_a_release(self):
        em._MAT_CAP = 2
        ix, la = _mint(3, "a")
        a0 = la[0]; snap0 = copy.deepcopy(a0)
        la[1]; la[2]                                               # evicts slot 0
        self.assertIs(list.__getitem__(la, 0), em._UNMAT); self.assertEqual(a0, snap0)
        a1 = la[1]; snap1 = copy.deepcopy(a1)
        self.assertEqual(ix.release(), 2)
        self.assertEqual(a1, snap1, "release resets the slot, never the atom a consumer holds")
        self.assertEqual(_entries(id(la)), (0, 0))
        again = la[1]
        self.assertEqual(again, snap1, "a rebuilt atom equals the first build"); self.assertIsNot(again, a1)
        self.assertEqual(_entries(id(la)), (1, 0), "...and registers again under weak ownership")

    def test_two_threads_building_one_slot_share_one_object_and_one_entry(self):
        ix, la = _mint(1, "a")
        real, gate = ix.build, threading.Barrier(2)
        def slow(k):
            gate.wait(5)                                           # both threads inside the build before either takes the lock
            return real(k)
        ix.build = slow
        out = [None, None]
        ths = [threading.Thread(target=lambda n=n: out.__setitem__(n, la._at(0))) for n in range(2)]
        for t in ths:
            t.start()
        for t in ths:
            t.join(10)
        self.assertIsNotNone(out[0]); self.assertIs(out[0], out[1]); self.assertIs(list.__getitem__(la, 0), out[0])
        self.assertEqual(_entries(id(la)), (1, 0)); self.assertEqual(em.asm_index_stats()["materialized"], 1)


class IdReuse(Synthetic):
    def test_a_dead_entry_under_a_reused_id_is_absent_to_the_new_list(self):
        ix, la = _mint(2, "a")
        gx, gone = _mint(1, "g")
        dead = weakref.ref(gone)
        del gx, gone
        gc.collect()
        self.assertIsNone(dead())
        with em._MAT_LOCK:                                         # a collected list's entries under the NEW list's key, as an id
            em._MAT_LRU[(id(la), 0)] = (dead, 0)                   #  recycled after a collection leaves them
            em._MAT_LRU[(id(la), 1)] = (dead, 1)
        a0 = la[0]                                                 # the build road: the stale entry is absent, la registers itself
        ent = em._MAT_LRU[(id(la), 0)]
        self.assertIs(ent[0](), la)
        self.assertEqual(next(reversed(em._MAT_LRU)), (id(la), 0), "at the young end, not in the stale entry's old position")
        self.assertEqual(em.asm_index_stats()["expired"], 1)
        a1 = la[1]                                                 # a second build over a stale entry
        self.assertEqual(em.asm_index_stats()["expired"], 2)
        with em._MAT_LOCK:
            em._MAT_LRU[(id(la), 1)] = (dead, 1)                   # a stale entry over a BUILT slot: the hit road's defensive check
        self.assertIs(la[1], a1)
        self.assertIs(em._MAT_LRU[(id(la), 1)][0](), la, "the hit road registers its own live object and touches nothing foreign")
        self.assertEqual(em.asm_index_stats()["expired"], 3)
        self.assertIs(la[0], a0); self.assertEqual(_entries(id(la)), (2, 0))


class DroppedEntries(T.Harness):
    """The drop sites, driven through the assembly itself: a restored leaf's entry (its index in `index`) leaves the cache and
    its index's entries leave the LRU."""

    def setUp(self):
        super().setUp()
        self._cap, self._max = em._MAT_CAP, em._ASM_CACHE_MAX
        _reset()

    def tearDown(self):
        em._MAT_CAP, em._ASM_CACHE_MAX = self._cap, self._max
        _reset()
        super().tearDown()

    def documented(self, name, tag):
        """A compacting scenario written and parsed whole, its document written: ready for a restore."""
        records, sent = G.SINGLE_FILE[name]
        path = self.write("%s-%s" % (tag, name), records(), sent=sent)
        self.parse(path)
        self.assertTrue(self.doc(path), em.asm_checkpoint_stats())
        return path

    def restore(self, path):
        modes = []
        tree = self.parse(path, modes)
        self.assertEqual(modes, ["restore"])
        return tree

    @staticmethod
    def key(path):
        return (os.path.realpath(path), SID, False)

    def test_the_caches_eviction_of_its_oldest_entry_releases_that_index_and_leaves_the_current_one_alone(self):
        px = self.documented("compaction_atom", "x")
        py = self.documented("manual_compact_detached", "y")
        self.fresh()
        tx, ty = self.restore(px), self.restore(py)                # X's entry is the older of the two
        lx, ly = tx["turns"][0]["atoms"], ty["turns"][0]["atoms"]
        self.assertIsInstance(lx, em.LazyAtoms); self.assertIsInstance(ly, em.LazyAtoms)
        kx, ky = len(lx), len(ly)
        firsts = [dict(a) for a in lx]; [dict(a) for a in ly]      # every atom of both first turns built
        ex, ey = em._ASM_CACHE[self.key(px)], em._ASM_CACHE[self.key(py)]
        self.assertIs(ex["index"], lx._index, "the entry names the index its pre-turns build through")
        self.assertIs(ey["index"], ly._index)
        self.assertEqual(_entries(id(lx)), (kx, 0)); self.assertEqual(_entries(id(ly)), (ky, 0))
        r0 = em.asm_index_stats()["resident"]
        em._ASM_CACHE_MAX = 2                                      # the cache full: a third leaf's whole parse evicts its oldest
        records, sent = G.SINGLE_FILE["author_kinds"]
        pz = self.write("z-author_kinds", records(), sent=sent)
        modes = []
        self.parse(pz, modes)
        self.assertEqual(modes, ["full"])
        self.assertNotIn(self.key(px), em._ASM_CACHE); self.assertIn(self.key(py), em._ASM_CACHE)
        st = em.asm_index_stats()
        self.assertEqual(st["released"], kx, "the evicted entry's index gave every built atom back")
        self.assertEqual(st["resident"], r0 - kx)
        self.assertEqual(_entries(id(lx)), (0, 0)); self.assertEqual(_built(lx), [])
        self.assertEqual(_entries(id(ly)), (ky, 0), "the current index's memo is untouched")
        self.assertEqual(_built(ly), list(range(ky)))
        self.assertEqual([dict(a) for a in lx], firsts, "the retained old view rebuilds through its own index, equal to before")
        self.assertEqual(_entries(id(lx)), (kx, 0), "...and registers again")

    def test_a_demoted_entry_releases_its_index_and_a_retained_view_takes_nothing_with_it(self):
        records, _ = G.SINGLE_FILE["compaction_atom"]
        recs = records()
        path = self.write("compaction_atom", recs)
        self.parse(path); self.assertTrue(self.doc(path))
        self.fresh()
        tree = self.restore(path)
        la = tree["turns"][0]["atoms"]
        k = len(la); self.assertGreater(k, 1)
        first = [dict(a) for a in la]
        ix = em._ASM_CACHE[self.key(path)]["index"]
        self.assertIs(ix, la._index)
        wi, wl = weakref.ref(ix), weakref.ref(la)
        t1 = self.after(recs, 100)                                 # a compaction landing in the tail after the document: the
        with open(path, "a") as f:                                 #  entry is stale and demotes to a whole parse
            f.write(json.dumps(G.compact_line(t1, "b_new", recs[-1].get("uuid"))) + "\n")
            f.write(json.dumps(G.compact_summary_line(t1 + 1, "s_new", "b_new")) + "\n")
        modes = []
        self.parse(path, modes)
        self.assertEqual(modes, ["full"])
        st = em.asm_index_stats()
        self.assertEqual(st["released"], k, "the demoted entry's index gave its atoms back")
        self.assertEqual(_entries(id(la)), (0, 0)); self.assertEqual(_built(la), [])
        self.assertEqual(dict(la[0]), first[0], "the retained view rebuilds a released slot, equal to the first build")
        self.assertIs(em._MAT_LRU[(id(la), 0)][0](), la, "...registered again under weak ownership")
        self.assertEqual(_entries(), (1, 0), "the whole parse's tree has no lazy atoms: that entry is the one")
        del tree, la, ix
        self._trees.clear()
        gc.collect()
        self.assertIsNone(wl(), "the view dropped, nothing of the old generation stays alive")
        self.assertIsNone(wi())
        self.assertEqual(_entries(), (0, 1), "its entry stands dead...")
        em._MAT_CAP = 1
        ix2, la2 = _mint(1, "b")
        la2[0]
        st = em.asm_index_stats()
        self.assertEqual(_entries(), (1, 0), "...and leaves at the next registration")
        self.assertEqual((st["expired"], st["evictions"]), (1, 0))

    def test_a_demoted_entrys_retained_view_leaves_nothing_behind_once_collected_with_the_cap_at_its_default(self):
        """The collection event on the production road, through the assembly: a restore, a demotion (a compaction after the
        document) that releases the index, a retained view reading one released slot again (registered against an index
        nothing releases again), the view freed, then one registration with the cap untouched. Red before the collection
        event: the view's entry stood dead, since the cap it waited for never came."""
        records, _ = G.SINGLE_FILE["compaction_atom"]
        recs = records()
        path = self.write("compaction_atom", recs)
        self.parse(path); self.assertTrue(self.doc(path))
        self.fresh()
        tree = self.restore(path)
        la = tree["turns"][0]["atoms"]
        k = len(la); self.assertGreater(k, 1)
        [dict(a) for a in la]
        t1 = self.after(recs, 100)
        with open(path, "a") as f:
            f.write(json.dumps(G.compact_line(t1, "b_new", recs[-1].get("uuid"))) + "\n")
            f.write(json.dumps(G.compact_summary_line(t1 + 1, "s_new", "b_new")) + "\n")
        modes = []
        self.parse(path, modes)
        self.assertEqual(modes, ["full"])
        self.assertEqual(em.asm_index_stats()["released"], k, "the demotion released the index")
        la[0]                                                      # the retained view reads a released slot: registered again
        self.assertEqual(_entries(), (1, 0))
        wl = weakref.ref(la)
        del tree, la
        self._trees.clear()
        gc.collect()
        self.assertIsNone(wl(), "the view is freed")
        self.assertGreater(em._MAT_CAP, 1000, "the cap is far above this test's entries: no pass over it takes part")
        ix2, la2 = _mint(1, "g")
        la2[0]                                                     # the next registration
        self.assertEqual(_entries(), (1, 0), "the freed view's entry left at the registration after its collection")
        st = em.asm_index_stats()
        self.assertEqual((st["expired"], st["collected"], st["evictions"]), (1, 1, 0))

    def test_a_refused_row_drops_the_entry_and_releases_its_index(self):
        path = self.documented("compaction_atom", "r")
        self.fresh()
        tree = self.restore(path)
        la = tree["turns"][0]["atoms"]
        k = len(la); self.assertGreater(k, 1)
        for i in range(1, k):
            la[i]
        self.assertEqual(_entries(id(la)), (k - 1, 0))
        la._index.rowb[la._rows[0]] = b"{not json"
        with self.assertRaises(em.LazyIndexError):
            la[0]
        self.assertNotIn(self.key(path), em._ASM_CACHE, "the document's entry is dropped, as before")
        st = em.asm_index_stats()
        self.assertEqual(st["released"], k - 1, "...and its index's built atoms left the LRU with it")
        self.assertEqual(_entries(id(la)), (0, 0)); self.assertEqual(_built(la), [])


class CollectionEvent(Synthetic):
    """A freed list's entries leave the LRU at the next registration or release, whether it dies by its last decref or in
    a cycle, however it came to hold entries, and on whichever thread it dies. Each test asserts the LRU's (live, dead)
    first, so that on a source without the event its red is the dead entries themselves; `collected` follows."""

    def _read_after_release(self, k, tag):
        """An index and one list of k rows: every slot built, the index released (its assembly entry dropped), then every
        slot read again, as a tree that outlived the entry reads it. Returns (index, list)."""
        ix, la = _mint(k, tag)
        for i in range(k):
            la[i]
        self.assertEqual(ix.release(), k)
        for i in range(k):
            la[i]
        self.assertEqual(_entries(id(la)), (k, 0), "the rebuilt slots registered again, against a released index")
        return ix, la

    def test_a_list_read_after_its_release_takes_its_entries_with_it_when_it_is_freed(self):
        k = 5
        ix, la = self._read_after_release(k, "a")
        ix2, lb = _mint(1, "b")                                    # minted before the free: it cannot take the freed list's id
        wl = weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl(), "the list is freed")
        lb[0]                                                      # the next registration, the cap far above
        self.assertEqual(_entries(), (1, 0), "the freed list's entries left, the live one stands")
        st = em.asm_index_stats()
        self.assertEqual((st["resident"], st["expired"], st["collected"], st["evictions"]), (1, k, k, 0),
                         "removed by the collection event, none by the cap")

    def test_a_list_freed_without_any_release_takes_its_entries_with_it(self):
        """The other population: a tree nobody holds whose index was never released (no assembly entry dropped)."""
        k = 4
        ix, la = _mint(k, "w")
        for i in range(k):
            la[i]
        ix2, lb = _mint(1, "x")
        wl = weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl())
        lb[0]
        self.assertEqual(_entries(), (1, 0))
        st = em.asm_index_stats()
        self.assertEqual((st["released"], st["expired"], st["collected"], st["evictions"]), (0, k, k, 0))

    def test_a_list_freed_inside_a_reference_cycle_takes_its_entries_with_it(self):
        """The collector runs no callback for a weak reference that is itself garbage. The list's entries hold its
        reference, which keeps it reachable from the LRU while any entry stands; a reference kept only on the index would
        be garbage with a list and index collected together, and the entries would stay."""
        k = 4
        ix, la = self._read_after_release(k, "c")
        ix2, lb = _mint(1, "d")
        tree = {"atoms": la}
        tree["self"] = tree                                        # the holder is a cycle: no decref frees the list
        wl = weakref.ref(la)
        was = gc.isenabled()
        gc.disable()
        try:
            del ix, la, tree
            self.assertIsNotNone(wl(), "only the collector can free it")
        finally:
            if was:
                gc.enable()
        gc.collect()
        self.assertIsNone(wl())
        lb[0]
        self.assertEqual(_entries(), (1, 0))
        st = em.asm_index_stats()
        self.assertEqual((st["resident"], st["expired"], st["collected"], st["evictions"]), (1, k, k, 0))

    def test_a_list_freed_under_the_lock_by_the_thread_that_minted_it_queues_without_a_deadlock(self):
        """The callback can run at any decref, including one made while _MAT_LOCK is held, and the lock is not reentrant:
        it takes no lock and only queues. The worker thread mints the list and drops its last reference under the lock (a
        free-threaded build can hand a deallocation to the thread that owns the object, so a drop by a second thread may
        run the callback elsewhere), and the queue's growth is read inside the lock, so the test fails when its case did
        not run. A regression here, a callback that takes _MAT_LOCK, deadlocks the worker while it holds the lock; every
        later test in this worker then blocks on the lock, so the red shows as a pytest timeout, not as an assertion."""
        k = 3
        ixn, ln = _mint(1, "n")                                    # minted before the free: it cannot take the freed list's id
        seen, errors, done = {}, [], threading.Event()

        def mint_and_drop_under_the_lock():
            try:
                ix, la = self._read_after_release(k, "m")
                holder = [la]
                seen["wl"] = weakref.ref(la)
                own = getattr(la, "_ref", None)
                del ix, la
                q = getattr(em, "_MAT_COLLECTED", ())
                with em._MAT_LOCK:
                    seen["before"] = len(q)
                    holder.clear()                                 # the last reference goes while this thread holds the lock
                    seen["after"] = len(q)
                    seen["mine"] = own is not None and any(r is own for r in list(q))
            except BaseException as e:                             # noqa: BLE001  reported on the test's thread below
                errors.append(e)
            done.set()
        t = threading.Thread(target=mint_and_drop_under_the_lock, daemon=True)
        t.start(); t.join(10)
        self.assertTrue(done.is_set(), "the drop under the lock returned: the callback took no lock")
        self.assertEqual(errors, [])
        self.assertIsNone(seen["wl"](), "the list is freed")
        ln[0]
        self.assertEqual(_entries(), (1, 0))
        self.assertGreater(seen["after"], seen["before"], "the queue grew across the drop, read while the dropping thread held the lock")
        self.assertTrue(seen["mine"], "...by the freed list's own reference")
        st = em.asm_index_stats()
        self.assertEqual((st["resident"], st["expired"], st["collected"]), (1, k, k))

    def test_an_entry_a_live_list_holds_under_the_freed_lists_id_is_kept(self):
        """The drain removes an entry only when it holds the freed list's own reference, never by id alone: an entry a live
        list registered under the recycled id keeps its place, and its slot keeps its atom."""
        k = 3
        ix, la = self._read_after_release(k, "e")
        lid = id(la)
        ixl, live = _mint(1, "f")
        a = live[0]
        with em._MAT_LOCK:                                         # live's own entry moved under the freed list's key, as an id
            own = em._MAT_LRU.pop((id(live), 0))                   #  recycled before a drain would leave it
            em._MAT_LRU.pop((lid, 0))
            em._MAT_LRU[(lid, 0)] = own
        ixg, lg = _mint(1, "g")
        wl = weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl())
        lg[0]                                                      # the drain runs here
        self.assertEqual(_entries(), (2, 0), "the freed list's two other entries left; live's entry and lg's stand")
        with em._MAT_LOCK:
            kept = em._MAT_LRU.get((lid, 0))
        self.assertIsNotNone(kept)
        self.assertIs(kept[0](), live)
        self.assertIs(list.__getitem__(live, 0), a, "its slot is untouched")
        st = em.asm_index_stats()
        self.assertEqual((st["expired"], st["collected"]), (k - 1, k - 1), "only the freed list's own entries left")

    def test_a_freed_list_with_no_entry_changes_nothing(self):
        ix, la = _mint(6, "h")
        for i in range(6):
            la[i]
        ix.release()                                               # released and never read again: no entry stands
        ixb, lb = _mint(1, "i")
        del ix, la
        gc.collect()
        lb[0]
        self.assertEqual(_entries(), (1, 0))
        st = em.asm_index_stats()
        self.assertEqual((st["resident"], st["expired"], st["collected"]), (1, 0, 0))

    def test_a_freed_lists_entries_leave_at_the_next_release_with_no_registration(self):
        """release() drains first, so the freed lists' entries leave there too, and `resident` after it counts no dead
        entry."""
        k = 4
        ix, la = self._read_after_release(k, "p")
        ixb, lb = _mint(2, "q")
        lb[0]; lb[1]
        wl = weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl())
        self.assertEqual(ixb.release(), 2)                         # no registration: the release alone
        self.assertEqual(_entries(), (0, 0), "the freed list's entries left at the release")
        st = em.asm_index_stats()
        self.assertEqual((st["resident"], st["released"], st["expired"], st["collected"]), (0, k + 2, k, k))

    def test_a_freed_lists_entries_leave_when_a_built_slot_registers_again(self):
        """The hit road's re-registration (a built slot with no entry of its own) drains first too."""
        k = 3
        ixb, lb = _mint(1, "s")
        lb[0]
        ix, la = self._read_after_release(k, "r")
        with em._MAT_LOCK:
            em._MAT_LRU.pop((id(lb), 0))                           # lb's slot stays built with no entry
        wl = weakref.ref(la)
        del ix, la
        gc.collect()
        self.assertIsNone(wl())
        m0 = em.asm_index_stats()["materialized"]
        lb[0]                                                      # a hit: no build, the slot registers again
        self.assertEqual(_entries(), (1, 0), "the freed list's entries left at the re-registration")
        st = em.asm_index_stats()
        self.assertEqual(st["materialized"], m0, "nothing was built")
        self.assertEqual((st["expired"], st["collected"]), (k, k))

    def test_the_in_place_list_methods_are_refused_so_a_lists_length_stays_what_it_was_at_mint(self):
        """The drain visits rows 0 to n - 1, n taken at mint, so a list must not grow or reorder in place: +=, *=, clear and
        reverse are refused beside the mutators the list already refused."""
        ix, la = _mint(3, "t")
        a0 = la[0]
        for bad in (lambda: operator.iadd(la, [{}]), lambda: operator.imul(la, 2), la.clear, la.reverse):
            with self.assertRaises(TypeError):
                bad()
        self.assertEqual(len(la), 3)
        self.assertIs(la[0], a0)
        self.assertEqual(la._ref.n, len(la), "the reference's row count covers every slot")


if __name__ == "__main__":
    unittest.main()
