#!/usr/bin/env python3
"""The kernel's module-level caches under concurrent writers (the 2026-09-06 free-threading review).

The kernel runs its builders, judge tiers and request handlers on separate threads, and on a
free-threaded interpreter (CPython 3.14t, GIL off) they really do run at once. Every module-level cache
written from several threads was read; the ones under a lock were sound, and these were check-then-act
or read-modify-write sequences with nothing holding them together. Three were live races under the GIL
already (the feed slot read twice, the parked comment creates, the pending tag journal); the rest turn
from unlikely into likely without it.

Each test stages the interleaving that broke, deterministically: a dict or str subclass whose one
observable step runs the concurrent writer, a monkeypatched callee that parks the first thread while a
second one arrives, or a gated open(). A test that only checks lost increments runs eight threads and
asserts an exact count; on the GIL build that rarely fails without the fix, on the free-threaded build it
does. Synthetic fixtures only: placeholder ids, invented text, hermetic state.

The kernel here is a private module object (romp_kernel_ftcaches), so its caches are nobody else's; the
judge, the event model and the session backend are the shared fixed-name modules, and every value of
theirs a test touches (the state root and the paths derived from it, the memos, the counters, the echo
key) goes back in tearDown. One assertion pins the fixed tree's entry point rather than a race:
Counters.test_assembly_stats_count_exactly, second half (see its comment).
"""
import contextlib
import io
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_ftcaches", os.path.join(BIN, "romp-kernel"))
jd, em = km.jd, km.em

# Private synthetic sids (the repo's goal-store fixture rule): jd and em are shared with every module on
# the worker, and a click stamp, a names entry, a pin sidecar or a journaled row filed under the shared
# placeholder sid can land on another module's fixture mid-test. Nothing else uses these two.
SID = "44444444-5555-6666-7777-888888888888"
PEER = "55555555-6666-7777-8888-999999999999"
WAIT = 5            # every gate in this file: a stuck thread fails the test, never hangs the run
SETTLE = 0.3        # how long the second arriver gets to reach the shared step (or block on the lock)

_JD_PATHS = ("STATE", "NAMES", "CAPDIR", "ARCHDIR", "GOALDIR", "GOALARCHDIR", "STATESDIR", "PCACHE", "MESSAGES",
             "ERRORS", "USAGE", "SDKDIR", "EPIDIR", "GONEDIR", "JUDGE_AUTH", "CODEXDIR", "JUDGE_SCRATCH",
             "JUDGE_LIMIT", "PROJECTS")


def _jd_paths():
    """One snapshot of every path the judge derives from its state root (plus PROJECTS). A test that rebinds
    the root restores THESE, not STATE alone: a peer module may have aimed one of them elsewhere (a bare
    GOALDIR reassignment is the suite's other isolation style), and _rebind_state would re-derive it."""
    return {k: getattr(jd, k) for k in _JD_PATHS}


def _restore_jd(saved):
    jd._rebind_state(saved["STATE"])       # clears the per-root memos too
    for k, v in saved.items():
        setattr(jd, k, v)


def _run(fn, *a):
    """A thread whose exception is kept for the assertion instead of dying on stderr."""
    box = {"exc": None}

    def go():
        try:
            fn(*a)
        except BaseException as e:      # noqa: BLE001 — the test reports it
            box["exc"] = e
    t = threading.Thread(target=go)
    t.box = box
    t.start()
    return t


class _Hooked(dict):
    """A dict whose .get(<key>) runs a staged writer ONCE, then behaves as a dict: the concurrent
    writer landing between the reader's read and its act."""

    def __init__(self, d, key, writer):
        super().__init__(d)
        self._key, self._writer, self._fired = key, writer, False

    def get(self, k, default=None):
        if k == self._key and not self._fired:
            self._fired = True
            self._writer()
        return dict.get(self, k, default)


# ── race 1: _cached_feed read the payload slot twice; the parse-warm thread Nones it between ──
class _TornSlot(list):
    """_built_feed as the reader saw it: the build on the first read of slot 1, None on the second."""

    def __init__(self, rows):
        super().__init__(rows)
        self.payload_reads = 0

    def __getitem__(self, i):
        if i == 1:
            self.payload_reads += 1
            if self.payload_reads > 1:
                return None                # `_built_feed[1] = None` (warm thread) landed after the first read
        return list.__getitem__(self, i)


class FeedSlotReadOnce(unittest.TestCase):
    def setUp(self):
        self._saved = (km._built_feed, km._views_dirty[0], km._cached_feed)
        km._views_dirty[0] = 0.0

    def tearDown(self):
        km._built_feed, km._views_dirty[0], km._cached_feed = self._saved

    def test_a_warm_clear_between_the_reads_cannot_turn_a_hit_into_none(self):
        feed = {"type": "feed", "asks": [], "working": []}
        km._built_feed = _TornSlot([("SIG",), feed, time.time(), time.time()])
        got = km._cached_feed(0, {}, ("SIG",))
        self.assertIs(got, feed, "the hit returns the build it tested, not the slot re-read after a clear")
        self.assertEqual(km._built_feed.payload_reads, 1, "one read of the payload slot per call")

    def test_the_wire_loop_skips_feed_clients_when_no_build_came_back(self):
        # The loop sits outside the build try: a None here raised on feed.get and ended the pusher
        # thread for the rest of the process. Now a logged skip; the client simply gets nothing.
        km._cached_feed = lambda *a, **k: None
        sent = []
        c = {"app": "feed", "alive": True, "wid": "w1", "qbytes": 0, "send": sent.append, "caps": set()}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._push([c])                       # the real push, one feed client
        self.assertFalse([s for s in sent if '"type": "feed"' in s], "no feed frame from no build")
        self.assertIn("no feed build this cycle", err.getvalue())


# ── race 2: _msg_summaries iterated the shared per-session table while a peer builder wrote it ──
class _PeerWritesDuringUnion(dict):
    """A session's submap whose consumption by dict.update runs the staged writer: the peer builder
    inserting a session into the SHARED table while this builder unions the rows."""

    def __init__(self, d, writer):
        super().__init__(d)
        self._writer = writer

    def keys(self):
        self._writer()
        return dict.keys(self)

    def __iter__(self):                    # a dict subclass with its own __iter__ takes update()'s keys() path
        return iter(dict.keys(self))


class MsgSummariesPrivateTable(unittest.TestCase):
    def setUp(self):
        self._saved = (km._sessions, km._msg_sum_scan_session, dict(km._msg_sum_cache))
        km._msg_sum_cache.clear()

    def tearDown(self):
        km._sessions, km._msg_sum_scan_session = self._saved[:2]
        km._msg_sum_cache.clear()
        km._msg_sum_cache.update(self._saved[2])

    def test_a_peer_insert_mid_union_neither_aborts_nor_corrupts_the_build(self):
        def peer_insert():
            km._msg_sum_cache.setdefault("per", {})[PEER] = (1, {"peer:m": "cap"})
        km._sessions = lambda now: [{"sid": "A", "name": "a", "path": "/x/a", "mtime": 100},
                                    {"sid": "B", "name": "b", "path": "/x/b", "mtime": 100}]
        km._msg_sum_scan_session = lambda sid, path, now: (
            _PeerWritesDuringUnion({"A:m": "cap"}, peer_insert) if sid == "A" else {"B:m": "cap"})
        m = km._msg_summaries()              # was: RuntimeError, dictionary changed size during iteration
        self.assertEqual(m, {"A:m": "cap", "B:m": "cap"})
        m2 = km._msg_summaries()
        self.assertEqual(m2, m, "the published table serves the next build unchanged")


# ── race 3: the names-memo sweep iterated the memo while the peer tier inserted ──
class _PeerInsertsOnHash(str):
    """A stale memo key whose hash (taken when the sweep tests it against the live set) runs the staged
    writer once: the other tier inserting a fresh entry into the memo mid-walk. Built disarmed, since
    the insert into the memo hashes it too; the test arms it once the memo is seeded."""

    def __new__(cls, s, writer):
        o = str.__new__(cls, s)
        o._writer, o.armed = writer, False
        return o

    def __hash__(self):
        if self.armed:
            self.armed = False
            self._writer()
        return str.__hash__(self)


class NamesMemoSweep(unittest.TestCase):
    def setUp(self):
        self._saved = (_jd_paths(), dict(jd._namefp_memo))
        self.tdo = tempfile.TemporaryDirectory()
        self.td = self.tdo.name
        jd._rebind_state(Path(self.td))
        jd.PROJECTS = Path(self.td) / "projects"
        jd._namefp_memo.clear()
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        cdir = str(Path(self.td) / "work")
        jd._proj_dir(cdir).mkdir(parents=True, exist_ok=True)
        (jd.NAMES / SID).write_text("web\t%s" % cdir)

    def tearDown(self):
        _restore_jd(self._saved[0])
        jd._namefp_memo.clear()
        jd._namefp_memo.update(self._saved[1])
        self.tdo.cleanup()

    def test_a_peer_insert_mid_sweep_does_not_abort_the_fingerprint(self):
        def peer_insert():
            jd._namefp_memo["peer-new"] = (1.0, None)
        trigger = _PeerInsertsOnHash("stale-1", peer_insert)
        jd._namefp_memo[trigger] = (0.0, None)
        jd._namefp_memo["stale-2"] = (0.0, None)
        trigger.armed = True
        fp = jd._discover_fingerprint()      # was: RuntimeError out of the tier pass
        self.assertIsNotNone(fp)
        self.assertEqual(set(map(str, jd._namefp_memo)), {SID, "peer-new"},
                         "the retired entries are gone; the live one and the peer's insert stand")


# ── race 4: the subagents walk memo's forget walked the memo while a peer build inserted ──
class SubagentTreesForgetSweep(unittest.TestCase):
    """_subagent_trees_forget drops the walk memo's roots (_SUBAGENT_TREES) no alive session owns, under no lock, and the
    writer (_subagent_tree, from a build on another thread) takes none either, so a walk of the live dict would meet a
    peer's insert: RuntimeError, dictionary changed size during iteration, on 3.12 and 3.14t. The fork staged this race
    on its sid-keyed walk memo (_SUBAGENT_DIRS_MEMO, evicted by _feed_memo_forget; the pull-in review, round 1, item 5,
    with the 2026-09-16 snapshot fix); upstream's root-keyed memo (romp-on/romp pull 1788) replaced that memo, and its
    forget walks list(_SUBAGENT_TREES) and pops with a default, so the case re-aimed at it at the 2026-09-17 catch-up
    fold (ruling 9; the eviction rule itself is tests/test_subagent_tree_memo.py's). Staged the way race 3 is: a stale
    root's hash, taken when the sweep tests it against the owned set, inserts the peer's fresh root once."""

    def setUp(self):
        self._saved = (dict(km._SUBAGENT_TREES), dict(km._SUBAGENT_TREE_STATS))
        km._SUBAGENT_TREES.clear()
        km._SUBAGENT_TREE_STATS["evict"] = 0

    def tearDown(self):
        km._SUBAGENT_TREES.clear(); km._SUBAGENT_TREES.update(self._saved[0])
        km._SUBAGENT_TREE_STATS.clear(); km._SUBAGENT_TREE_STATS.update(self._saved[1])

    def test_a_peer_insert_mid_forget_neither_aborts_the_sweep_nor_spares_a_departed_root(self):
        live_path = "/x/live/%s.jsonl" % SID
        live, peer = str(km._subagents_dir(live_path)), str(km._subagents_dir("/x/peer/%s.jsonl" % PEER))

        def peer_insert():
            km._SUBAGENT_TREES[peer] = ((peer,), (None,))
        trigger = _PeerInsertsOnHash("/x/s1/stale-1/subagents", peer_insert)
        km._SUBAGENT_TREES[trigger] = ((str(trigger),), (None,))
        km._SUBAGENT_TREES["/x/s2/stale-2/subagents"] = (("/x/s2/stale-2/subagents",), (None,))
        km._SUBAGENT_TREES[live] = ((live,), (None,))
        trigger.armed = True
        km._subagent_trees_forget([{"sid": SID, "path": live_path}])   # over the live dict: RuntimeError, changed size
        self.assertFalse(trigger.armed, "the staged insert fired during the sweep")
        self.assertEqual(set(map(str, km._SUBAGENT_TREES)), {live, peer},
                         "the departed roots are gone; the owned one and the peer's insert stand")
        self.assertEqual(km._SUBAGENT_TREE_STATS["evict"], 2, "one evict per departed root")


# ── race 5: two passes over the parked comment creates ──
class ParkedCreates(unittest.TestCase):
    def setUp(self):
        self._saved = (km._comment_create, km._comments_frame, list(km._parked_creates))

    def tearDown(self):
        km._comment_create, km._comments_frame = self._saved[:2]
        km._parked_creates[:] = self._saved[2]

    def test_a_parked_create_is_retried_by_one_pass_only(self):
        entered, gate, calls = threading.Event(), threading.Event(), []

        def create(*a, **k):
            calls.append(1)
            entered.set()
            gate.wait(WAIT)
            return (None, "t1")
        km._comment_create = create
        km._comments_frame = lambda sid, tmux=None: None
        km._parked_creates[:] = [{"sid": SID, "uuid": "11111111-2222-3333-4444-777777777777", "exact": "the cap",
                                  "text": "Why?", "name": "", "model": "", "effort": "", "fast": "", "color": "",
                                  "tries": 0}]
        t1 = _run(km._retry_parked_creates)
        self.addCleanup(lambda: (gate.set(), t1.join(WAIT)))     # on every exit path: open the gate, wait for the pass
        self.assertTrue(entered.wait(WAIT))
        t2 = _run(km._retry_parked_creates)               # the connect push's pass, mid-cycle
        self.addCleanup(lambda: (gate.set(), t2.join(WAIT)))
        time.sleep(SETTLE)
        gate.set()
        t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])   # was: ValueError from .remove
        self.assertEqual(calls, [1], "one create, however many passes")
        self.assertEqual(km._parked_creates, [])


# ── race 6: the judge-usage incremental reader's seek-read-advance under two readers ──
class JudgeUsageReader(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = (jd.STATE, dict(km._JUDGE_USAGE_CACHE))
        jd.STATE = Path(self.td.name)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        jd.STATE = self._saved[0]
        km._JUDGE_USAGE_CACHE.update(self._saved[1])
        self.td.cleanup()

    def test_rows_are_counted_once_under_concurrent_readers(self):
        rows = [{"t": 1781100000 + i, "judge": "captioner", "in": 10, "out": 5, "cost": 0.01} for i in range(5)]
        (jd.STATE / "judge-usage.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        entered, gate, opened = threading.Event(), threading.Event(), []
        real_open = open

        class _ParkAfterRead:
            """The first reader's file: it seeks and reads normally, then parks with its chunk in hand —
            the second reader arrives at the same offset meanwhile."""

            def __init__(self, f):
                self.f = f

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return self.f.__exit__(*exc)

            def seek(self, *a):
                return self.f.seek(*a)

            def read(self, *a):
                chunk = self.f.read(*a)
                entered.set()
                gate.wait(WAIT)
                return chunk

        def gated_open(path, *a, **k):
            f = real_open(path, *a, **k)
            if str(path).endswith("judge-usage.jsonl"):
                opened.append(1)
                if len(opened) == 1:
                    return _ParkAfterRead(f)
            return f
        got = {}
        with mock.patch.object(km, "open", gated_open, create=True):
            t1 = _run(lambda: got.__setitem__(1, km._judge_usage_rows()))
            self.addCleanup(lambda: (gate.set(), t1.join(WAIT)))     # on every exit path: open the gate, wait for the reader
            self.assertTrue(entered.wait(WAIT))
            t2 = _run(lambda: got.__setitem__(2, km._judge_usage_rows()))
            self.addCleanup(lambda: (gate.set(), t2.join(WAIT)))
            time.sleep(SETTLE)
            gate.set()
            t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])
        self.assertEqual((len(got[1]), len(got[2])), (5, 5), "was: 10 — the chunk appended twice")
        self.assertEqual(len(km._JUDGE_USAGE_CACHE["rows"]), 5)


# ── race 6, the walkers: the roll-up's walk and the band's cursor slice against the reader's left prune ──
class JudgeUsageWalkers(unittest.TestCase):
    """Three consumers of the reader's LIVE rows list (returned without a copy since the judging band memo keys its cursor
    on the list's identity) against the reader's left prune, which shifts every index in place under _JUDGE_USAGE_LOCK on
    whichever thread reads the log. The /analytics roll-up walks a snapshot taken under the lock (the 2026-09-17 fold's
    kernel review, item 5: a walk over the live list counted 33 rows short when a prune landed under it), the timeline's
    attach walk (_attach_run_usage) walks the same snapshot (round 2 of that review, item 2: round 1 covered the roll-up
    alone, and a bare walk here matched 33 of 1,000 marks to a neighbour's call under the same prune), and the band's
    cursor takes the prune count, the boundary check and the slice under ONE hold (item 6: a prune landing between the
    check and the slice began the slice past the verified boundary, and one frame lost the rows in between). Each test
    parks the walker at the one step its race is about, runs the reader's prune from a second thread that takes the lock
    itself, and asserts the walk's result against the rows present when the walk began."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = (jd.STATE, dict(km._JUDGE_USAGE_CACHE), km._judging_band, jd.active_runs)
        jd.STATE = Path(self.td.name)
        jd.active_runs = lambda: []
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[], pruned=0)
        km._judging_band = None
        self.R = km._JUDGE_USAGE_RETAIN

    def tearDown(self):
        jd.STATE, saved, km._judging_band, jd.active_runs = self._saved
        km._JUDGE_USAGE_CACHE.update(saved)
        self.td.cleanup()

    @staticmethod
    def _row(t, **kw):
        r = {"judge": "captioner", "fsid": SID, "t": t, "sent": t - 5, "recv": t, "ms": 5000, "in": 10, "out": 5, "cost": 0.01}
        r.update(kw)
        return r

    def _write(self, rows, mode="w"):
        with open(jd.STATE / "judge-usage.jsonl", mode) as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def _prune_from_a_second_thread(self, row):
        """The reader's own prune, from another thread that takes _JUDGE_USAGE_LOCK itself: append `row` to the log (its t
        past the retention floor of the leading rows) and read. Returns the thread."""
        def go():
            self._write([row], mode="a")
            km._judge_usage_rows()
        t = _run(go)
        self.addCleanup(t.join, WAIT)         # on every exit path (the caller's join is the success path's)
        return t

    def test_the_roll_up_counts_the_rows_present_at_the_walks_start_under_a_prune(self):
        base = 1781100000
        self._write([self._row(base + i) for i in range(1000)])
        live = km._judge_usage_rows()
        self.assertEqual(len(live), 1000)
        entered, gate = threading.Event(), threading.Event()

        class _Parks(dict):
            """Row 500 of the walk: its first read parks the walker, with rows on either side of it still to count."""
            armed = True

            def get(self, *a):
                if _Parks.armed:
                    _Parks.armed = False
                    entered.set()
                    gate.wait(WAIT)
                return dict.get(self, *a)
        live[500] = _Parks(live[500])
        got = {}
        t1 = _run(lambda: got.__setitem__("u", km._judge_usage(0)))
        self.assertTrue(entered.wait(WAIT), "the walker reached row 500")
        t2 = self._prune_from_a_second_thread(self._row(base + 33 + self.R))    # newest - RETAIN passes the first 33 rows
        t2.join(WAIT)
        self.assertIsNone(t2.box["exc"])
        self.assertEqual((len(live), km._JUDGE_USAGE_CACHE["pruned"]), (1000 - 33 + 1, 33), "the prune and the append landed under the walk")
        gate.set()
        t1.join(WAIT)
        self.assertIsNone(t1.box["exc"])
        self.assertEqual(got["u"]["total"]["calls"], 1000, "was: 968, the walk skipped the 33 rows the prune shifted under its index")
        self.assertEqual(got["u"]["total"]["in"], 10 * 1000)
        self.assertEqual(got["u"]["byJudge"]["captioner"]["calls"], 1000)

    def test_the_attach_walk_matches_every_mark_to_its_own_call_under_a_prune(self):
        """The timeline's attach walk (_attach_run_usage): one mark per logged call, the walker parked at row 500 while the
        reader's prune drops the first 33 rows and appends one. Over the live list the walk resumed at its index and skipped
        the 33 rows the prune shifted under it, so 33 marks took a neighbour's call (the greedy match within 180s) and the last
        33 matched nothing; over the snapshot every mark carries its own call. The parked row is wrapped inside the cache's
        rows, not through a list the reader returned, so the case holds if the reader ever returns a copy."""
        base = 1781100000
        self._write([self._row(base + i) for i in range(1000)])
        self.assertEqual(len(km._judge_usage_rows()), 1000)
        entered, gate = threading.Event(), threading.Event()

        class _Parks(dict):
            """Row 500 of the walk: its first read parks the walker, with rows on either side of it still to attach."""
            armed = True

            def get(self, *a):
                if _Parks.armed:
                    _Parks.armed = False
                    entered.set()
                    gate.wait(WAIT)
                return dict.get(self, *a)
        c = km._JUDGE_USAGE_CACHE
        c["rows"][500] = _Parks(c["rows"][500])
        judging = [{"sid": SID, "judge": "captioner", "t": base + i, "kind": "segment", "text": "m%d" % i} for i in range(1000)]
        t1 = _run(lambda: km._attach_run_usage(judging, 0, {SID}))
        self.assertTrue(entered.wait(WAIT), "the walker reached row 500")
        t2 = self._prune_from_a_second_thread(self._row(base + 33 + self.R))    # newest - RETAIN passes the first 33 rows
        t2.join(WAIT)
        self.assertIsNone(t2.box["exc"])
        self.assertEqual((len(c["rows"]), c["pruned"]), (1000 - 33 + 1, 33), "the prune and the append landed under the walk")
        gate.set()
        t1.join(WAIT)
        self.assertIsNone(t1.box["exc"])
        self.assertEqual(sum(1 for mk in judging if mk["ms"] == 5000), 1000,
                         "was: 967, the walk skipped the 33 rows the prune shifted under its index and the last 33 marks matched nothing")
        self.assertEqual([mk["recv"] for mk in judging], [base + i for i in range(1000)],
                         "every mark carries its OWN call's response time, none a neighbour's")

    def test_the_bands_cursor_takes_the_count_the_check_and_the_slice_under_one_hold(self):
        R, NOW = self.R, 1_800_000_000
        base = NOW - R - 100                                      # three rows the next append pushes out of retention
        self._write([self._row(base + i) for i in range(3)] + [self._row(base + 50 + i) for i in range(40)]
                    + [self._row(NOW - 1000 + i) for i in range(5)])
        c = km._JUDGE_USAGE_CACHE
        km._judge_usage_rows()
        entered, gate = threading.Event(), threading.Event()

        class _ParksOnSlice(list):
            """The reader's live list whose one ARMED slice read (the band's `rows[skip:]`) parks the thread taking it; the
            reader's own reads (an index, an append, the left prune) run as on a plain list."""
            armed = False

            def __getitem__(self, i):
                if isinstance(i, slice) and _ParksOnSlice.armed:
                    _ParksOnSlice.armed = False
                    entered.set()
                    gate.wait(WAIT)
                return list.__getitem__(self, i)
        c["rows"] = live = _ParksOnSlice(c["rows"])              # the same object across builds: the memo keys on it
        t0 = NOW - 86400
        first = km._run_judging(t0, {SID}, [])
        self.assertEqual([e["t1"] for e in first], [NOW - 1000 + i for i in range(5)])
        mb = km._judging_band
        self.assertEqual((mb[0] is live, mb[1]), (True, 43), "the cursor covers the 43 leading pre-horizon rows")
        _ParksOnSlice.armed = True
        got = {}
        t1 = _run(lambda: got.__setitem__("out", km._run_judging(t0 + 1, {SID}, [])))
        self.assertTrue(entered.wait(WAIT), "the band passed its boundary check and reached its slice")
        t2 = self._prune_from_a_second_thread(self._row(base + 3 + R))    # newest - RETAIN passes the first three rows
        time.sleep(SETTLE)                                        # the writer's chance: the lock, or the unguarded live list
        gate.set()
        t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])
        self.assertEqual((len(live), c["pruned"]), (3 + 40 + 5 + 1 - 3, 3), "the prune and the append landed")
        self.assertEqual([e["t1"] for e in got["out"]], [NOW - 1000 + i for i in range(5)],
                         "the frame carries every horizon row present at the read: was three short, the slice begun past the boundary")


# ── race 7: the postal sender memo is one tuple, rebound whole ──
class PostalRowMemo(unittest.TestCase):
    def setUp(self):
        self._saved = (_jd_paths(), jd._postal_from_memo[0])
        self.tdo = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.tdo.name))
        jd._postal_from_memo[0] = (None, {})

    def tearDown(self):
        _restore_jd(self._saved[0])
        jd._postal_from_memo[0] = self._saved[1]
        self.tdo.cleanup()

    def test_key_and_map_are_published_as_one_value(self):
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        jd.MESSAGES.write_text(json.dumps({"ev": "sent", "id": "m1", "from": "web", "body": "please review"}) + "\n")
        self.assertEqual(jd._postal_row("m1")[0], "web")
        self.assertEqual(len(jd._postal_from_memo), 1, "one slot")
        # the payload is (mp, xcands) since J6, plus the returned-message ledger (upstream #1095, folded 2026-09-09)
        key, (mp, xcands, returned) = jd._postal_from_memo[0]
        self.assertIsInstance(key, tuple)
        self.assertIn("m1", mp, "the key and the map it was built with travel together")
        self.assertEqual(xcands, [], "no cross-host delegate row: no candidate")
        self.assertEqual(returned, {}, "no withdrawn or returned row: nothing in the ledger")
        jd.MESSAGES.write_text(json.dumps({"ev": "sent", "id": "m2", "from": "api", "body": "done"}) + "\n")
        os.utime(jd.MESSAGES, (time.time() + 10, time.time() + 10))
        self.assertEqual(jd._postal_row("m2")[0], "api")
        self.assertNotIn("m1", jd._postal_from_memo[0][1][0], "a new key brings its own map, never the old one")


# ── race 8: one retry per error episode, two askers at once ──
class _FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, sid, text):
        self.sent.append(text)
        return True

    def pending_queued(self, sid):
        return []


class RetryEpisodeGate(unittest.TestCase):
    def setUp(self):
        self.be = _FakeBackend()
        self._saved = (km._api_error, km._path_of, km._retry_paused_on, km._session_retry_suppressed,
                       km._retry_gate_state, dict(km._auto_retried), dict(km._auto_retry_state))
        km._path_of = lambda sid, now=None: "/TESTDIR/x.jsonl"
        km._retry_paused_on = lambda: False
        km._session_retry_suppressed = lambda sid: False
        km._api_error = lambda path: {"text": "500 server_error", "status": 500, "uuid": "err-1"}
        km._auto_retried.clear()
        km._auto_retry_state.clear()

    def tearDown(self):
        (km._api_error, km._path_of, km._retry_paused_on, km._session_retry_suppressed,
         km._retry_gate_state, retried, state) = self._saved
        km._auto_retried.clear(); km._auto_retried.update(retried)
        km._auto_retry_state.clear(); km._auto_retry_state.update(state)

    def test_two_concurrent_askers_inject_one_retry(self):
        entered, gate = threading.Event(), threading.Event()
        orig = self._saved[4]

        def parked_gate_state(sid):          # the backoff read inside the gate: park the first asker there,
            v = orig(sid)                    # holding the value it read (a real thread's read is not redone)
            entered.set()
            gate.wait(WAIT)
            return v
        km._retry_gate_state = parked_gate_state
        t1 = _run(km._fire_api_retry, SID, self.be)
        self.addCleanup(lambda: (gate.set(), t1.join(WAIT)))     # on every exit path: open the gate, wait for the asker
        self.assertTrue(entered.wait(WAIT))
        t2 = _run(km._fire_api_retry, SID, self.be)   # the pusher's tick against the client's ask
        self.addCleanup(lambda: (gate.set(), t2.join(WAIT)))
        time.sleep(SETTLE)
        gate.set()
        t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])
        self.assertEqual(self.be.sent, [km.RETRY_MSG], "was: two retries for one episode")


# ── race 9: two queued tag edits, read-modify-write against the journal ──
class PendingTagJournal(unittest.TestCase):
    HOST = "TESTHOST"

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        with km._PENDING_TAG_LOCK:
            self._saved = (jd.STATE, km._tag_name_basis, km._PENDING_TAG_CACHE["rows"])
            km._PENDING_TAG_CACHE["rows"] = None
        jd.STATE = Path(self.td.name)
        with km._remotes_lock:
            km._remotes["ft-test"] = {"host": self.HOST, "views": {"tags": []}}

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.pop("ft-test", None)
        jd.STATE, km._tag_name_basis = self._saved[:2]
        with km._PENDING_TAG_LOCK:
            km._PENDING_TAG_CACHE["rows"] = self._saved[2]
        self.td.cleanup()

    def test_both_edits_are_journaled(self):
        km._save_pending_tag_rows([{"host": self.HOST, "name": "seed", "tagId": "", "ruledAt": 1, "at": 1, "delete": True}])
        entered, gate, local = threading.Event(), threading.Event(), threading.local()
        orig = self._saved[1]

        def basis(n):                        # the first queuer parks after its read, before its save
            local.n = getattr(local, "n", 0) + 1
            if getattr(local, "trap", False) and local.n == 2:
                entered.set()
                gate.wait(WAIT)
            return orig(n)
        km._tag_name_basis = basis

        def queue(name, trap):
            local.trap = trap
            self.assertTrue(km._queue_pending_tag_edit(self.HOST, {"name": name, "delete": True}))
        t1 = _run(queue, "alpha", True)
        self.assertTrue(entered.wait(WAIT))
        t2 = _run(queue, "beta", False)
        time.sleep(SETTLE)
        gate.set()
        t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])
        names = sorted(r["name"] for r in km._pending_tag_rows())
        self.assertEqual(names, ["alpha", "beta", "seed"], "was: one edit overwritten after its client was told queued")
        on_disk = json.loads(km._pending_tag_path().read_text())
        self.assertEqual(sorted(r["name"] for r in on_disk), names)


# ── race 10: the click stamps — a builder's pop must not take a newer click with it ──
class ClickStamps(unittest.TestCase):
    def setUp(self):
        for d in (km._interrupt_clicked, km._compact_clicked, km._model_switch_pending):
            d.pop(SID, None)

    tearDown = setUp

    def test_interrupt_pop_keeps_a_click_that_landed_during_the_ruling(self):
        # Both clicks land through the stamp table itself, the write the WS op and the Ctrl+C relay made
        # before _mark_interrupt_clicked existed, so on the unfixed tree this fails on the pop, not on a name.
        now = int(time.time())
        km._interrupt_clicked[SID] = time.time()
        t0 = km._interrupt_clicked[SID]

        def reclick():
            km._interrupt_clicked[SID] = time.time()
        stop = _Hooked({"type": "user", "t": now,
                        "message": {"role": "user", "content": "[Request interrupted by user]"}},
                       "t", reclick)                                       # a second stop, mid-ruling
        session = {"turns": [{"atoms": [stop]}]}
        self.assertFalse(km._interrupting(SID, session, now, None), "the first click settled")
        self.assertIn(SID, km._interrupt_clicked, "was: the second click's cue popped with the first")
        self.assertIsNot(km._interrupt_clicked[SID], t0)

    def test_compact_pop_keeps_a_click_that_landed_during_the_ruling(self):
        now = int(time.time())
        km._mark_compacting(SID)
        t0 = km._compact_clicked[SID]
        boundary = _Hooked({"type": "system", "subtype": "compact_boundary", "t": now + 1},
                           "t", lambda: km._mark_compacting(SID))
        session = {"turns": [{"atoms": [boundary]}]}
        self.assertFalse(km._compacting_optimistic(SID, session, now))
        self.assertIn(SID, km._compact_clicked)
        self.assertIsNot(km._compact_clicked[SID], t0)

    def test_model_pending_pop_keeps_a_pick_that_landed_during_the_ruling(self):
        km._mark_model_pending(SID, "opus")
        tm = _Hooked({"model": "Opus 4.8"}, "model", lambda: km._mark_model_pending(SID, "sonnet"))
        self.assertFalse(km._model_pending_now(SID, tm), "the opus pick is reflected")
        self.assertEqual((km._model_switch_pending.get(SID) or {}).get("target"), "sonnet",
                         "was: the sonnet pick's dots popped with the opus ruling")


# ── race 10: the pin-association memo's load-then-store against a concurrent append ──
class _LinesThenWriter:
    """A read file whose iteration yields every line and then runs the staged writer: the peer's append
    landing after this reader consumed the sidecar and before it stored its copy."""

    def __init__(self, f, writer):
        self.f, self.writer = f, writer

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self.f.__exit__(*exc)

    def __iter__(self):
        yield from list(self.f)
        self.writer()


class PinAssociationMemo(unittest.TestCase):
    def setUp(self):
        self._saved = dict(km._PIN_ASSOC_MEMO)
        km._PIN_ASSOC_MEMO.clear()
        self.path = km._pin_assoc_dir() / (SID + ".jsonl")
        self.path.write_text(json.dumps({"u": "u1", "t": "/x/a.png", "p": "pinA"}) + "\n")

    def tearDown(self):
        km._PIN_ASSOC_MEMO.clear()
        km._PIN_ASSOC_MEMO.update(self._saved)
        self.path.unlink(missing_ok=True)

    def test_an_append_during_a_peer_load_is_not_displaced_by_the_peers_store(self):
        fired = []
        real_open = open

        def opener(path, *a, **k):
            f = real_open(path, *a, **k)
            mode = a[0] if a else k.get("mode", "r")
            if str(path) == str(self.path) and "r" in mode and not fired:
                fired.append(1)
                return _LinesThenWriter(f, lambda: km._pin_assoc_append(SID, "u2", "/x/plot.png", "pinB"))
            return f
        with mock.patch.object(km, "open", opener, create=True):
            got = km._pin_assoc(SID, "u2")
        self.assertEqual(got, {"/x/plot.png": "pinB"}, "was: {} — the loader's older copy replaced the appended memo")
        self.assertEqual(km._pin_assoc(SID, "u1"), {"/x/a.png": "pinA"})
        self.assertEqual(km._pin_assoc(SID, "u2"), {"/x/plot.png": "pinB"})
        rows = [json.loads(l) for l in self.path.read_text().splitlines()]
        self.assertEqual([r["u"] for r in rows], ["u1", "u2"], "the sidecar has both")


# ── race 10: the path-link cache's tuple is copied on write, never mutated in place ──
class PathLinkCacheCopyOnWrite(unittest.TestCase):
    def setUp(self):
        self._saved = (km._resolve_path_token, km._pin_for)
        self.key = (SID, "u9")
        km._PATH_LINK_CACHE.pop(self.key, None)

    def tearDown(self):
        km._resolve_path_token, km._pin_for = self._saved
        km._PATH_LINK_CACHE.pop(self.key, None)

    def test_a_resolve_publishes_a_new_tuple_and_leaves_the_cached_dicts_alone(self):
        links0, pins0 = {}, {}
        km._PATH_LINK_CACHE[self.key] = (links0, ("report.md",), pins0)
        km._resolve_path_token = lambda tok, sid, memo: "/x/report.md"
        km._pin_for = lambda target, sid: None
        got = km._path_links("see report.md", SID, "u9", {})
        self.assertEqual(got, {"report.md": "/x/report.md"})
        self.assertEqual((links0, pins0), ({}, {}), "the tuple other builders hold is unchanged")
        hit = km._PATH_LINK_CACHE[self.key]
        self.assertEqual(hit[0], {"report.md": "/x/report.md"})
        self.assertIsNot(hit[0], links0)


# ── counters: read-modify-write increments from eight threads land exactly ──
def _hammer(case, fn, threads=8, n=5000):
    """`threads` threads each call fn `n` times; `case` (the test) registers the joins as a cleanup right after the
    starts, so an assertion that fails in the caller leaves none of them behind (the joins below are the success path's)."""
    ts = [_run(lambda: [fn() for _ in range(n)]) for _ in range(threads)]
    case.addCleanup(lambda: [t.join(WAIT * 4) for t in ts if t.ident is not None])   # _run started each; the guard is the
    # list-join rule (Thread.join raises on a thread never started), so a later shape that builds first stays safe
    for t in ts:
        t.join(WAIT * 4)
    for t in ts:
        if t.box["exc"] is not None:
            raise t.box["exc"]
    return threads * n


class Counters(unittest.TestCase):
    def test_next_nonce_is_unique_and_gapless(self):
        saved = km._nonce[0]
        km._nonce[0] = 0
        try:
            seen = []
            lock = threading.Lock()

            def take():
                v = km._next_nonce()
                with lock:
                    seen.append(v)
            total = _hammer(self, take)
            self.assertEqual(len(set(seen)), total)
            self.assertEqual(km._nonce[0], total)
        finally:
            km._nonce[0] = saved

    def test_models_rev_advances_once_per_change(self):
        before = km._models_rev[0]
        total = _hammer(self, km._models_changed, n=1000)
        self.assertEqual(km._models_rev[0] - before, total)

    def test_drain_refusals_are_counted_exactly(self):
        saved = dict(km._DRAIN_REFUSED)
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                total = _hammer(self, km._note_drain_refused, n=2000)
            self.assertEqual(km._DRAIN_REFUSED["count"], total)
            self.assertEqual(km._DRAIN_REFUSED["episodeCount"], total)
        finally:
            km._DRAIN_REFUSED.update(saved)

    def test_assembly_stats_count_exactly(self):
        # _asm_demote first: it exists on both trees, so without the GIL the unfixed tree fails here, on the
        # lost increments. _asm_stat is the locked helper (upstream's, under _ASM_CKPT_LOCK, returning the new value), so its half pins the fixed tree's entry
        # point (an AttributeError before the fix, not a race).
        em._ASM_STATS.pop("ft-test", None)
        em._ASM_STATS.pop("g:ft-test", None)
        try:
            demoted = _hammer(self, lambda: em._asm_demote("ft-test"))
            self.assertEqual(em._ASM_STATS["g:ft-test"], demoted)
            total = _hammer(self, lambda: em._asm_stat("ft-test"), n=2000)
            self.assertEqual(em._ASM_STATS["ft-test"], total)
        finally:
            em._ASM_STATS.pop("ft-test", None)
            em._ASM_STATS.pop("g:ft-test", None)

    def test_wire_stats_count_exactly(self):
        # A _LazyWire cell is made by the pusher and materialized by whichever sender thread first needs the
        # whole frame, so its counter is bumped from many threads at once (the perf stack's serialize change,
        # audited when this branch was rebased onto it).
        saved = dict(km._wire_stats)
        km._wire_stats["feed_body"] = 0
        try:
            total = _hammer(self, lambda: km._LazyWire(lambda: "{}", 2, "feed_body").text(), n=2000)
            self.assertEqual(km._wire_stats["feed_body"], total)
        finally:
            km._wire_stats.clear()
            km._wire_stats.update(saved)

    def test_intr_marks_memo_stats_count_exactly(self):
        # The interrupt-marks memo is read by the interrupt and nudge ticks on the pusher and by connect-push
        # builds on WS threads; every call bumps hit or miss. The machine-cut read is stubbed so the test is
        # about the counter, not the states file.
        saved = (dict(km._intr_marks_memo_stats), km._last_machine_cut)
        km._intr_marks_memo_stats.update(hit=0, miss=0, evict=0)
        km._last_machine_cut = lambda sid: (0.0, "")
        turns = []
        try:
            total = _hammer(self, lambda: km._interrupt_marks(turns, sid=SID, family="display"), n=2000)
            st = km._intr_marks_memo_stats
            self.assertEqual(st["hit"] + st["miss"], total)
        finally:
            km._intr_marks_memo.pop((SID, "display"), None)
            km._last_machine_cut = saved[1]
            km._intr_marks_memo_stats.clear()
            km._intr_marks_memo_stats.update(saved[0])


if __name__ == "__main__":
    unittest.main()
