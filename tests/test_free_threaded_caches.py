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

SID = "11111111-2222-3333-4444-555555555555"
PEER = "22222222-3333-4444-5555-666666666666"
WAIT = 5            # every gate in this file: a stuck thread fails the test, never hangs the run
SETTLE = 0.3        # how long the second arriver gets to reach the shared step (or block on the lock)


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
        self._saved = (km._sessions, km._msg_sum_scan_session)
        km._msg_sum_cache.clear()

    def tearDown(self):
        km._sessions, km._msg_sum_scan_session = self._saved
        km._msg_sum_cache.clear()

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
        self._saved = (jd.STATE, jd.PROJECTS)
        self.td = tempfile.mkdtemp()
        jd._rebind_state(Path(self.td))
        jd.PROJECTS = Path(self.td) / "projects"
        jd._namefp_memo.clear()
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        cdir = str(Path(self.td) / "work")
        jd._proj_dir(cdir).mkdir(parents=True, exist_ok=True)
        (jd.NAMES / SID).write_text("web\t%s" % cdir)

    def tearDown(self):
        jd._rebind_state(self._saved[0])
        jd.PROJECTS = self._saved[1]
        jd._namefp_memo.clear()

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


# ── race 4: the tmux echo store's compound steps against a concurrent add ──
class TmuxEchoStore(unittest.TestCase):
    def setUp(self):
        km._tmux_echo.pop(SID, None)
        self._saved = km.sb.echo_text_key

    def tearDown(self):
        km.sb.echo_text_key = self._saved
        km._tmux_echo.pop(SID, None)

    def test_a_send_landing_during_a_prune_survives_it(self):
        km._tmux_echo_add(SID, "first")
        first_key = next(iter(km._tmux_echo[SID]))
        orig = self._saved
        writer = {}

        def staged(text):
            if not writer:               # the peer's send arrives mid-walk: it lands now (old) or waits for the lock (new)
                writer["t"] = _run(km._tmux_echo_add, SID, "second")
                writer["t"].join(SETTLE)
            return orig(text)
        km.sb.echo_text_key = staged
        km._tmux_echo_prune(SID, {first_key}, set())     # was: RuntimeError, dictionary changed size during iteration
        writer["t"].join(WAIT)
        self.assertIsNone(writer["t"].box["exc"])
        self.assertEqual([a["_echo_text"] for a in km._tmux_echo_atoms(SID)], ["second"],
                         "the landed echo is pruned, the concurrent send is kept")


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
        self.assertTrue(entered.wait(WAIT))
        t2 = _run(km._retry_parked_creates)               # the connect push's pass, mid-cycle
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
        self._saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])

    def tearDown(self):
        jd.STATE = self._saved
        km._JUDGE_USAGE_CACHE.update(path=None, size=-1, mtime=0.0, rows=[])
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
            self.assertTrue(entered.wait(WAIT))
            t2 = _run(lambda: got.__setitem__(2, km._judge_usage_rows()))
            time.sleep(SETTLE)
            gate.set()
            t1.join(WAIT); t2.join(WAIT)
        self.assertIsNone(t1.box["exc"]); self.assertIsNone(t2.box["exc"])
        self.assertEqual((len(got[1]), len(got[2])), (5, 5), "was: 10 — the chunk appended twice")
        self.assertEqual(len(km._JUDGE_USAGE_CACHE["rows"]), 5)


# ── race 7: the postal sender memo is one tuple, rebound whole ──
class PostalRowMemo(unittest.TestCase):
    def setUp(self):
        self._saved = jd.STATE
        self.td = tempfile.mkdtemp()
        jd._rebind_state(Path(self.td))
        jd._postal_from_memo[0] = (None, {})

    def tearDown(self):
        jd._rebind_state(self._saved)
        jd._postal_from_memo[0] = (None, {})

    def test_key_and_map_are_published_as_one_value(self):
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        jd.MESSAGES.write_text(json.dumps({"ev": "sent", "id": "m1", "from": "web", "body": "please review"}) + "\n")
        self.assertEqual(jd._postal_row("m1")[0], "web")
        self.assertEqual(len(jd._postal_from_memo), 1, "one slot")
        key, mp = jd._postal_from_memo[0]
        self.assertIsInstance(key, tuple)
        self.assertIn("m1", mp, "the key and the map it was built with travel together")
        jd.MESSAGES.write_text(json.dumps({"ev": "sent", "id": "m2", "from": "api", "body": "done"}) + "\n")
        os.utime(jd.MESSAGES, (time.time() + 10, time.time() + 10))
        self.assertEqual(jd._postal_row("m2")[0], "api")
        self.assertNotIn("m1", jd._postal_from_memo[0][1], "a new key brings its own map, never the old one")


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
                       km._retry_gate_state, dict(km._auto_retried))
        km._path_of = lambda sid, now=None: "/TESTDIR/x.jsonl"
        km._retry_paused_on = lambda: False
        km._session_retry_suppressed = lambda sid: False
        km._api_error = lambda path: {"text": "500 server_error", "status": 500, "uuid": "err-1"}
        km._auto_retried.clear()
        km._auto_retry_state.clear()

    def tearDown(self):
        (km._api_error, km._path_of, km._retry_paused_on, km._session_retry_suppressed,
         km._retry_gate_state, saved) = self._saved
        km._auto_retried.clear(); km._auto_retried.update(saved)
        km._auto_retry_state.clear()

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
        self.assertTrue(entered.wait(WAIT))
        t2 = _run(km._fire_api_retry, SID, self.be)   # the pusher's tick against the client's ask
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
        self._saved = (jd.STATE, km._tag_name_basis)
        jd.STATE = Path(self.td.name)
        with km._PENDING_TAG_LOCK:
            km._PENDING_TAG_CACHE["rows"] = None
        with km._remotes_lock:
            km._remotes["ft-test"] = {"host": self.HOST, "views": {"tags": []}}

    def tearDown(self):
        with km._remotes_lock:
            km._remotes.pop("ft-test", None)
        jd.STATE, km._tag_name_basis = self._saved
        with km._PENDING_TAG_LOCK:
            km._PENDING_TAG_CACHE["rows"] = None
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
        now = int(time.time())
        km._mark_interrupt_clicked(SID)
        t0 = km._interrupt_clicked[SID]
        stop = _Hooked({"type": "user", "t": now,
                        "message": {"role": "user", "content": "[Request interrupted by user]"}},
                       "t", lambda: km._mark_interrupt_clicked(SID))     # a second stop, mid-ruling
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
        km._PIN_ASSOC_MEMO.clear()
        self.path = km._pin_assoc_dir() / (SID + ".jsonl")
        self.path.write_text(json.dumps({"u": "u1", "t": "/x/a.png", "p": "pinA"}) + "\n")

    def tearDown(self):
        km._PIN_ASSOC_MEMO.clear()
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
def _hammer(fn, threads=8, n=5000):
    ts = [_run(lambda: [fn() for _ in range(n)]) for _ in range(threads)]
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
            total = _hammer(take)
            self.assertEqual(len(set(seen)), total)
            self.assertEqual(km._nonce[0], total)
        finally:
            km._nonce[0] = saved

    def test_models_rev_advances_once_per_change(self):
        before = km._models_rev[0]
        total = _hammer(km._models_changed, n=1000)
        self.assertEqual(km._models_rev[0] - before, total)

    def test_drain_refusals_are_counted_exactly(self):
        saved = dict(km._DRAIN_REFUSED)
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                total = _hammer(km._note_drain_refused, n=2000)
            self.assertEqual(km._DRAIN_REFUSED["count"], total)
            self.assertEqual(km._DRAIN_REFUSED["episodeCount"], total)
        finally:
            km._DRAIN_REFUSED.update(saved)

    def test_assembly_stats_count_exactly(self):
        em._ASM_STATS.pop("ft-test", None)
        em._ASM_STATS.pop("g:ft-test", None)
        try:
            total = _hammer(lambda: em._asm_count("ft-test"))
            self.assertEqual(em._ASM_STATS["ft-test"], total)
            demoted = _hammer(lambda: em._asm_demote("ft-test"), n=2000)
            self.assertEqual(em._ASM_STATS["g:ft-test"], demoted)
        finally:
            em._ASM_STATS.pop("ft-test", None)
            em._ASM_STATS.pop("g:ft-test", None)


if __name__ == "__main__":
    unittest.main()
