#!/usr/bin/env python3
"""One encode per payload per build on the pusher thread, and a pusher thread that survives a serializer's raise.

Each rebuild used to serialize the feed and the bars THREE times on the pusher thread: the whole frame
(_feed_body, json.dumps in _push), the dedup signature (_dedup_sig: a sort_keys re-dump of the payload minus its
clock, which both frames carry) and the per-entry pass the delta paths need (_feed_parts for the feed's own itemId
protocol, _delta_parts for the bars and the view-delta slot path). Now the per-entry pass is the only encode: the
signature is a tuple of its strings (_feed_sig, _parts_sig), and the whole frame is a _LazyWire cell made on the
first send that actually needs one (a client without deltas, a fresh socket, a re-base, a delta past the size
guard) and kept in the wire tuple (_feed_wire, _bars_wire) for the next. The feed's cards are memoized on the
build's asks list and the slot path's split per collection on the collection object's identity, so a ledgers-only
refill re-encodes no card. The split is handed down to _send_feed / _send_slot, so a connect push on another thread
evicting _delta_parts_cache's single slot between the fill and the send costs no re-split.

The pusher's wire section runs AFTER _push's build try, and _push_all and _pusher had no except: a raise there
killed the pusher thread for the life of the process (every dashboard frozen until a restart). The section now
stands a raising fill's slot down for the cycle and skips a client whose send raised, loudly; _pusher_cycle_jobs
has a belt.

Synthetic only: placeholder ids, the notes-api demo world, TESTHOST.
"""
import collections
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from romp_load import load_source
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_wireonce", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
NOW = 1781100000


def _card(i, text=None):
    t = NOW - i * 60
    return {"itemId": "%s:g%d" % (SID, i), "sid": SID, "name": "web", "color": None,
            "text": text or "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
            "trgb": [10, 20, 30], "column": "working", "summary": "s" * 200,
            "tree": [{"id": "%s:g%d.%d" % (SID, i, j), "text": "step %d" % j, "status": "done", "t": t, "last": t,
                      "trgb": [10, 20, 30], "children": []} for j in range(4)]}


def _feed(n=5, build_id=1, now=NOW, asks=None):
    return {"type": "feed", "asks": asks if asks is not None else [_card(i) for i in range(n)], "now": now,
            "buildId": build_id, "order": [SID], "working": ["web"], "awaiting": [],
            "sessions": [{"sid": SID, "name": "web", "color": None}], "userTodos": {}, "views": {},
            "clearNotices": [], "syncNotices": [], "sdkNotices": [], "selfHost": "TESTHOST"}


def _timeline(nbars=2, now=1, unkeyable=False):
    turns = {SID: [{"id": "b%d" % i, "t": i, "end": i + 1, "open": False} for i in range(nbars)]}
    return {"type": "timeline", "sessions": [{"id": SID, "name": "web"}],
            "turns": None if unkeyable else turns,        # None where a dict belongs: _delta_parts cannot key it
            "judging": {}, "messages": [], "now": now}


def _bars_of(tl, warming=False):
    return {"type": "bars", "turns": tl["turns"], "judging": tl["judging"], "messages": tl["messages"],
            "now": tl["now"], "warming": warming}


def _client(app, caps=(), delta=True):
    """A ws client as _push sees it, its frames captured; `delta` is the ?delta=1 announcement every browser
    pane makes — False is a pipe or a relay that takes whole frames. `caps` is the ws ?caps= announcement: this
    fork's FEED_DELTA_CAP opts a feed pane into the feed's own itemId deltas (_send_feed); a feed client without
    it takes the view-delta slot path (_send_slot), the bars' path."""
    c = {"app": app, "alive": True, "wid": "w-" + app, "qbytes": 0, "sent": {}, "delta": delta, "caps": set(caps),
         "frames": []}
    c["send"] = lambda s: c["frames"].append(json.loads(s))
    return c


class _RaisingLock:
    """A client slot lock whose acquire raises, so a send fails inside _send_slot's `with _client_lock(c)` and the
    test asserts on THIS message. A bare object() in the slot raises there too, but as AttributeError before 3.11
    and TypeError from 3.11, so the interpreter's wording is not a stable marker across the CI matrix."""

    def __enter__(self):
        raise RuntimeError("synthetic send failure")

    def __exit__(self, *exc):
        return False


def _delta(after, before):
    return {k: after[k] - before[k] for k in after if after[k] != before[k]}


def _wire_lines(err):
    """_wire_default's stderr lines only: a process's first _push also writes the backends' start-up notices."""
    return [l for l in err.getvalue().splitlines() if l.startswith("wire: ")]


class _World:
    """Stub the builders so _push serves synthetic feed and timeline builds — the recipe
    tests/test_kernel_timeline_split.py uses, plus _cached_feed — with every wire cache emptied first and
    restored after. `feed`/`timeline` are what the next push builds; reassign them for a rebuild."""

    NAMES = ("_cached_feed", "_cached_timeline", "build_timeline", "_tmux_sessions", "_fleet_view_sig", "_DELTA_MAX_FRACTION")

    def __init__(self, test, feed=None, timeline=None):
        self.feed, self.timeline = feed, timeline
        saved = {n: getattr(km, n) for n in self.NAMES}
        saved_wire = (km._feed_wire, km._bars_wire, km._skel_wire, dict(km._delta_parts_cache), dict(km._delta_split_memo),
                      km._feed_cards_memo)
        saved_built = (list(km._built_feed), list(km._built_timeline))
        km._cached_feed = lambda now, tmux, sig, connect=False: self.feed
        km._cached_timeline = lambda now, tmux, sig, connect=False: self.timeline
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: self.timeline
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        km._DELTA_MAX_FRACTION = 10.0        # synthetic payloads are tiny: the size guard would send wholes
        km._feed_wire = km._bars_wire = km._skel_wire = None
        km._delta_parts_cache.clear(); km._delta_split_memo.clear(); km._feed_cards_memo = None
        km._built_timeline[:] = [None, timeline, time.time(), time.time()]   # warmed: a connect push serves the cache

        def restore():
            for n, v in saved.items():
                setattr(km, n, v)
            km._feed_wire, km._bars_wire, km._skel_wire = saved_wire[:3]
            km._delta_parts_cache.clear(); km._delta_parts_cache.update(saved_wire[3])
            km._delta_split_memo.clear(); km._delta_split_memo.update(saved_wire[4]); km._feed_cards_memo = saved_wire[5]
            km._built_feed[:] = saved_built[0]; km._built_timeline[:] = saved_built[1]
        test.addCleanup(restore)


class OneEncodePerBuild(unittest.TestCase):

    def test_a_rebuild_encodes_each_payload_once_and_whole_frames_only_where_one_goes(self):
        w = _World(self, feed=_feed(), timeline=_timeline())
        cap = _client("feed", caps=(km.FEED_DELTA_CAP,))          # the kernel-served feed pane: the feed's own itemId deltas
        dfeed = _client("feed")                                   # a ?delta=1 feed client without the cap: slot deltas
        legacy = _client("feed", delta=False)                     # a pipe, a relay: whole frames
        tl = _client("timeline")                                  # every timeline pane: slot deltas
        splits, calls = collections.Counter(), collections.Counter()
        real_split, real_parts, real_body = km._delta_split, km._feed_parts, km._feed_body
        with mock.patch.object(km, "_delta_split", side_effect=lambda kind, v, **kw: splits.update([kind]) or real_split(kind, v, **kw)), \
             mock.patch.object(km, "_feed_parts", side_effect=lambda f: calls.update(["parts"]) or real_parts(f)), \
             mock.patch.object(km, "_feed_body", side_effect=lambda f: calls.update(["body"]) or real_body(f)):
            s0 = dict(km._wire_stats)
            km._push([cap, dfeed, legacy, tl])
            self.assertEqual(calls["parts"], 1, "one per-card pass for the feed (this fork's _feed_parts)")
            self.assertEqual(sum(splits.values()), 4, "one per-entry pass per slot-path collection: the feed's one (the "
                                                      "cap-less client's slot path), the bars' three")
            self.assertEqual(calls["body"], 1, "one whole feed frame, shared by the legacy client and the cap client's first frame")
            self.assertEqual([f["type"] for f in cap["frames"]], ["feed"])
            self.assertIn("trgb", cap["frames"][0]["asks"][0], "every whole frame is the tinted legacy body")
            self.assertEqual([f["type"] for f in dfeed["frames"]], ["feed"]); self.assertNotIn("_keys", dfeed["frames"][0], "no full carries a key list (T278c)")
            self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"]); self.assertNotIn("_keys", legacy["frames"][0])
            self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"]); self.assertNotIn("_keys", tl["frames"][1], "no full carries a key list (T278c)")
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "feed_body": 1, "bars_body": 1, "split_miss": 4},
                             "one whole frame each, shared by the keyed full and the legacy client; the cards encoded once; "
                             "four collections split")
            self.assertEqual(km._feed_wire[4], km._feed_sig(km._feed_wire[5]), "the feed's signature is its per-card pass's tuple")
            self.assertEqual(km._bars_wire[4], km._parts_sig(km._bars_wire[5]), "the bars' is the split's tuple")
            self.assertEqual(legacy["sent"][("feed",)][0], km._feed_wire[4])
            self.assertEqual(dfeed["sent"][("feed",)][0], km._feed_wire[4])
            # a second cycle over the same builds: nothing encoded, nothing made, nothing sent
            splits.clear(); calls.clear(); s0 = dict(km._wire_stats); n = [len(c["frames"]) for c in (cap, dfeed, legacy, tl)]
            km._push([cap, dfeed, legacy, tl])
            self.assertEqual(dict(splits), {}); self.assertEqual(dict(calls), {})
            self.assertEqual(_delta(km._wire_stats, s0), {})
            self.assertEqual([len(c["frames"]) for c in (cap, dfeed, legacy, tl)], n)
            # a rebuild seen only by delta clients: the per-entry passes run, no whole frame is ever made
            w.feed = _feed(build_id=2, asks=[_card(i, text="changed" if i == 2 else None) for i in range(5)])
            w.timeline = _timeline(nbars=3, now=2)
            splits.clear(); calls.clear(); s0 = dict(km._wire_stats)
            km._push([cap, dfeed, tl])
            self.assertEqual(sum(splits.values()), 4); self.assertEqual(dict(calls), {"parts": 1})
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "split_miss": 4},
                             "a new asks list and new collection objects: every pass ran")
            self.assertEqual(cap["frames"][-1]["type"], "feedDelta")
            self.assertEqual([a["itemId"] for a in cap["frames"][-1]["asks"]], ["%s:g2" % SID])
            self.assertEqual(dfeed["frames"][-1]["type"], "delta")
            self.assertEqual(list(dfeed["frames"][-1]["coll"]["asks"]["set"]), ["%s:g2" % SID])
            self.assertEqual(tl["frames"][-1]["type"], "delta")
            self.assertFalse(km._feed_wire[3].materialized(), "no client took a whole feed frame")
            self.assertFalse(km._bars_wire[3].materialized(), "…or a whole bars frame")
            # the legacy client joins the next cycle: this build's whole frame is made now, once
            splits.clear(); calls.clear(); s0 = dict(km._wire_stats)
            km._push([cap, dfeed, legacy, tl])
            self.assertEqual(dict(splits), {}); self.assertEqual(dict(calls), {"body": 1})
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_body": 1})
            self.assertEqual(legacy["frames"][-1]["buildId"], 2)
            self.assertTrue(km._feed_wire[3].materialized())
            self.assertEqual(km._feed_wire[3].size(), len(km._feed_body(w.feed)), "size() is exact once made")

    def test_the_split_made_at_the_fill_is_the_one_the_delta_path_records(self):
        # the bars' split is handed down to _send_slot; the feed's per-card pass is handed to _send_feed (this fork's
        # itemId protocol), which records it as the cap client's held base
        _World(self, feed=_feed(), timeline=_timeline())
        cap, tl = _client("feed", caps=(km.FEED_DELTA_CAP,)), _client("timeline")
        km._push([cap, tl])
        fparts, bparts = km._feed_wire[5], km._bars_wire[5]
        self.assertIsNotNone(fparts); self.assertIsNotNone(bparts)
        self.assertIs(cap["efeed"], fparts, "handed down, not re-encoded")
        self.assertIs(tl["dstate"]["bars"]["parts"], bparts,
                      "handed down, not re-split (single-threaded here; the hand-down is what makes it hold under a "
                      "concurrent connect push, which can evict _delta_parts_cache's single slot)")
        self.assertEqual(km._feed_wire[4], km._feed_sig(fparts)); self.assertEqual(km._bars_wire[4], km._parts_sig(bparts))
        km._delta_parts_cache.clear()                 # a connect push on another thread evicted the slot
        with mock.patch.object(km, "_delta_parts", side_effect=AssertionError("re-split")), \
             mock.patch.object(km, "_feed_parts", side_effect=AssertionError("re-encoded")):
            km._push([cap, tl])                       # the wire hit hands both down: no re-split, no re-encode, nothing sent
        self.assertEqual([f["type"] for f in cap["frames"]], ["feed"])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"])

    def test_an_unkeyable_bars_build_takes_whole_frames_and_the_string_signature(self):
        w = _World(self, timeline=_timeline(unkeyable=True))   # turns None where a dict belongs: _delta_parts gives None
        tl = _client("timeline")
        km._delta_unkeyable_said.clear()
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([tl]); km._push([tl])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"], "the whole frame went once; the repeat deduped")
        self.assertNotIn("_keys", tl["frames"][1])
        self.assertIsNone(tl["frames"][1]["turns"])
        self.assertIsInstance(km._bars_wire[4], str, "the sort_keys fallback signature, as before")
        self.assertIsNone(km._bars_wire[5])
        self.assertTrue(km._bars_wire[3].materialized(), "the whole dump the signature needed pre-fills the cell")
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_sig_fallback": 1, "split_miss": 1},
                         "the turns split ran and raised; the collections after it were never reached")
        self.assertEqual(err.getvalue().count("cannot be keyed"), 1, "said once, as before")
        w.timeline = _timeline(unkeyable=True, now=2)            # a rebuild: the whole frame goes again
        w.timeline["judging"] = km._compact_judging([{"sid": SID, "judge": "closer", "t": 1, "t1": 2}])   # per lane, compact (T278c)
        with redirect_stderr(err):
            km._push([tl])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars", "bars"],
                         "a rebuild with unchanged lanes: no lanes frame, and the whole bars frame again")

    def test_perf_reports_the_wire_counters(self):
        snap = km._PERF_STATS.snapshot()
        self.assertEqual(snap["memos"]["wire"], dict(km._wire_stats))
        self.assertEqual(set(snap["memos"]["wire"]),
                         {"feed_cards_hit", "feed_cards_miss", "split_hit", "split_miss", "feed_body", "bars_body",
                          "bars_sig_fallback", "default_str"},
                         "the feed's per-card memo (this fork), the slot path's split memo, the two bodies, the fallback, str()")


class ALedgersOnlyRefillEncodesNoCard(unittest.TestCase):
    """_push copies the cached feed build (feed = dict(feed_src)) and attaches the cycle's ledgers to the copy, so a
    cycle whose ledgers moved but whose build did not misses the wire tuple and splits the payload again: a new dict
    around the SAME asks list. Two memos answer it: the feed's own per-card pass (_feed_parts, this fork's itemId
    protocol) memoizes the cards on the build's asks list (_feed_cards_memo), and _delta_parts memoizes each
    collection's split on the collection object's identity (_delta_split_memo), so that refill re-encodes the
    ledgers and the remainder and no card on either path."""

    def test_a_ledgers_only_refill_re_encodes_no_card(self):
        _World(self)
        f = _feed()
        led = lambda state: [{"sid": SID, "name": "web", "color": None, "status": {"state": state}, "ledger": {"tops": []}}]
        parts1 = km._feed_parts(dict(f, ledgers=led("working")))
        s0 = dict(km._wire_stats)
        with mock.patch.object(km, "_strip_trgb", side_effect=AssertionError("re-encoded a card")):
            parts2 = km._feed_parts(dict(f, ledgers=led("waiting")))   # the pusher's copy with a changed attach
        self.assertIs(parts2[0], parts1[0], "the cards dict is the memoized one")
        self.assertNotEqual(parts2[1], parts1[1])
        self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_hit": 1})
        self.assertNotEqual(km._feed_sig(parts1), km._feed_sig(parts2), "the ledgers moved the signature")
        self.assertIsNot(km._feed_parts(_feed(build_id=2))[0], parts1[0], "a new build's list is encoded afresh")
        self.assertEqual(km._feed_parts({"type": "feed", "asks": None, "now": 1})[0], {}, "a build without cards")

    def test_a_refill_with_the_same_asks_object_and_a_changed_remainder_makes_no_split(self):
        _World(self)                                              # empties the parts cache and the split memo; restores after
        src = _feed(n=6)
        first = dict(src, ledgers=[{"sid": SID, "name": "web", "status": "idle"}])
        refill = dict(src, ledgers=[{"sid": SID, "name": "web", "status": "working"}])   # the same asks list, another remainder
        splits = collections.Counter(); real_split = km._delta_split
        with mock.patch.object(km, "_delta_split", side_effect=lambda kind, v, **kw: splits.update([kind]) or real_split(kind, v, **kw)):
            s0 = dict(km._wire_stats)
            p1 = km._delta_parts("feed", first)
            self.assertEqual(dict(splits), {"byid:itemId": 1}); self.assertEqual(_delta(km._wire_stats, s0), {"split_miss": 1})
            splits.clear(); s0 = dict(km._wire_stats)
            p2 = km._delta_parts("feed", refill)
            self.assertEqual(dict(splits), {}, "the asks list is the same object: no card encoded")
            self.assertEqual(_delta(km._wire_stats, s0), {"split_hit": 1})
            self.assertIs(p2[0]["asks"], p1[0]["asks"], "the split is shared, not copied")
            self.assertEqual(p2[1]["ledgers"], refill["ledgers"]); self.assertNotEqual(p2[2], p1[2], "the remainder was re-encoded")
            self.assertNotEqual(km._parts_sig(p1), km._parts_sig(p2), "and the signature moves with it")
            # a new asks object (a rebuild, or any copy) splits again, and the memo follows it
            rebuilt = dict(refill, asks=list(src["asks"]))
            splits.clear(); s0 = dict(km._wire_stats)
            p3 = km._delta_parts("feed", rebuilt)
            self.assertEqual(dict(splits), {"byid:itemId": 1}); self.assertEqual(_delta(km._wire_stats, s0), {"split_miss": 1})
            self.assertEqual(km._parts_sig(p3), km._parts_sig(p2), "equal cards in a new list: an equal signature")
            self.assertIs(km._delta_split_memo[("feed", "asks")][0], rebuilt["asks"])
            splits.clear(); s0 = dict(km._wire_stats)
            km._delta_parts("feed", dict(rebuilt, now=NOW + 5))
            self.assertEqual(dict(splits), {}); self.assertEqual(_delta(km._wire_stats, s0), {"split_hit": 1})
            self.assertEqual(len(km._delta_split_memo), 1, "one entry per (frame type, collection): replaced, never grown")

    def test_through_push_a_refill_that_misses_the_wire_tuple_on_its_ledgers_re_encodes_no_card(self):
        w = _World(self, feed=_feed())
        board, dfeed = _client("fleet"), _client("feed")
        splits = collections.Counter(); real_split = km._delta_split
        with mock.patch.object(km, "_delta_split", side_effect=lambda kind, v, **kw: splits.update([kind]) or real_split(kind, v, **kw)):
            s0 = dict(km._wire_stats)
            km._push([board])                                     # an app="fleet" client: the cycle attaches ledgers to the copy
            self.assertEqual(dict(splits), {"byid:itemId": 1}); self.assertEqual(km._feed_wire[1], [])
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "feed_body": 1, "split_miss": 1},
                             "the feed's per-card pass and the slot path's split, each once")
            splits.clear(); s0 = dict(km._wire_stats)
            km._push([dfeed])                                     # the same build without the attach: the wire tuple misses on its ledgers
            self.assertEqual(dict(splits), {}, "the refill served the cards from the memo")
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_hit": 1, "feed_body": 1, "split_hit": 1},
                             "both memos hit on the same asks list: no card encoded on either path")
            self.assertIsNone(km._feed_wire[1]); self.assertIs(km._feed_wire[0], w.feed)
            self.assertEqual([f["type"] for f in dfeed["frames"]], ["feed"]); self.assertNotIn("ledgers", dfeed["frames"][0])
            self.assertEqual([f["type"] for f in board["frames"]], ["feed"]); self.assertEqual(board["frames"][0]["ledgers"], [])
            w.feed = _feed(build_id=2)                            # a rebuild: a new asks list, split again
            splits.clear(); s0 = dict(km._wire_stats)
            km._push([dfeed])
            self.assertEqual(dict(splits), {"byid:itemId": 1})
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "split_miss": 1})

    def test_a_bars_payload_around_unchanged_collections_splits_no_bar(self):
        # the same path for the bars: a new bars dict around the SAME turns/judging/messages objects (a warming flip, or
        # any other remainder) is a memo hit for all three collections; a rebuild's new lanes object splits alone
        _World(self)
        tl = _timeline(nbars=3)
        splits = collections.Counter(); real_split = km._delta_split
        with mock.patch.object(km, "_delta_split", side_effect=lambda kind, v, **kw: splits.update([kind]) or real_split(kind, v, **kw)):
            s0 = dict(km._wire_stats)
            p1 = km._delta_parts("bars", _bars_of(tl, warming=True))
            self.assertEqual(sum(splits.values()), 3); self.assertEqual(_delta(km._wire_stats, s0), {"split_miss": 3})
            splits.clear(); s0 = dict(km._wire_stats)
            p2 = km._delta_parts("bars", _bars_of(tl, warming=False))
            self.assertEqual(dict(splits), {}, "the same collection objects: no bar encoded")
            self.assertEqual(_delta(km._wire_stats, s0), {"split_hit": 3})
            for name in ("turns", "judging", "messages"):
                self.assertIs(p2[0][name], p1[0][name], name + ": the split is shared")
            self.assertIs(p2[1]["warming"], False); self.assertNotEqual(km._parts_sig(p1), km._parts_sig(p2), "the remainder moved the signature")
            nxt = dict(tl, turns={SID: [dict(b) for b in tl["turns"][SID]]}, now=2)   # a rebuild's lanes: split again; the rest hit
            splits.clear(); s0 = dict(km._wire_stats)
            km._delta_parts("bars", _bars_of(nxt))
            self.assertEqual(dict(splits), {"dictlist:id": 1}); self.assertEqual(_delta(km._wire_stats, s0), {"split_hit": 2, "split_miss": 1})
            self.assertEqual(len(km._delta_split_memo), 3, "one entry per (frame type, collection)")

    def test_split_hit_and_miss_are_exact_under_a_forced_interleaving(self):
        # the memo's counters go through _wire_bump like the rest: the pusher and a handler-thread connect push both
        # fill, so a bare `+= 1` would lose increments. A dict whose reads yield the thread forces the interleaving the
        # lock is for (under the GIL alone the race is rare enough to stay green without it).
        _World(self)
        src = _feed(n=3)

        class _Yielding(dict):
            def get(self, k, d=None):
                v = dict.get(self, k, d); time.sleep(0); return v

            def __getitem__(self, k):
                v = dict.__getitem__(self, k); time.sleep(0); return v
        saved = km._wire_stats
        km._wire_stats = _Yielding(saved)
        try:
            s0 = km._wire_stats["split_hit"] + km._wire_stats["split_miss"]

            def run():
                for i in range(300):
                    km._delta_parts("feed", dict(src, now=NOW + i))   # a new payload each: the asks list hits after the first miss
            ts = [threading.Thread(target=run, daemon=True) for _ in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(60)
            self.assertFalse(any(t.is_alive() for t in ts))
            self.assertEqual(km._wire_stats["split_hit"] + km._wire_stats["split_miss"] - s0, 8 * 300, "every fill bumped exactly one of the two")
        finally:
            km._wire_stats = saved


class LazyWireCell(unittest.TestCase):

    def test_text_once_size_estimate_then_exact_and_the_counter(self):
        calls = []
        cell = km._LazyWire(lambda: (calls.append(1), "x" * 100)[1], 90, "feed_body")
        s0 = dict(km._wire_stats)
        self.assertFalse(cell.materialized()); self.assertEqual(cell.size(), 90)
        self.assertEqual(cell.text(), "x" * 100); self.assertEqual(cell.text(), "x" * 100)
        self.assertEqual(calls, [1], "made once")
        self.assertEqual(cell.size(), 100); self.assertTrue(cell.materialized())
        self.assertEqual(_delta(km._wire_stats, s0), {"feed_body": 1})
        pre = km._LazyWire(None, 5, text="abc")
        self.assertTrue(pre.materialized()); self.assertEqual(pre.size(), 3); self.assertEqual(pre.text(), "abc")
        self.assertEqual(km._wire_text("s"), "s"); self.assertEqual(km._wire_len("abcd"), 4)
        self.assertEqual(km._wire_text(pre), "abc"); self.assertEqual(km._wire_len(cell), 100)

    def test_the_estimates_sit_under_the_whole_frame_but_within_ten_percent(self):
        f = _feed(n=40); fp = km._delta_parts("feed", f); whole = json.dumps(f)
        self.assertLess(km._parts_est(fp), len(whole))
        self.assertGreater(km._parts_est(fp), 0.9 * len(whole))
        bars = _bars_of(_timeline(nbars=60)); bp = km._delta_parts("bars", bars); whole = json.dumps(bars)
        self.assertLess(km._parts_est(bp), len(whole))
        self.assertGreater(km._parts_est(bp), 0.9 * len(whole))

    def test_feed_ms_lazy_splices_the_clock_exactly_as_feed_ms(self):
        f = _feed(); parts = km._feed_parts(f)
        body = km._LazyWire(lambda: km._feed_body(f), km._feed_est(parts))
        ms = km._feed_ms_lazy(body, 42)
        est = ms.size()
        self.assertFalse(body.materialized(), "nothing made until the text is asked for")
        self.assertEqual(ms.text(), km._feed_ms(km._feed_body(f), 42))
        self.assertEqual(json.loads(ms.text())["now"], 42)
        self.assertTrue(body.materialized()); self.assertEqual(ms.size(), len(ms.text()))
        self.assertLess(est, len(ms.text())); self.assertGreater(est, 0.7 * len(ms.text()))
        self.assertEqual(km._feed_ms_lazy("{}", 7).text(), '{"now": 7}')
        self.assertEqual(km._feed_ms_lazy(km._feed_body(f), 8).text(), km._feed_ms(km._feed_body(f), 8), "a str body too")

    def test_the_feed_estimate_sits_under_the_body_but_not_far(self):
        # the feed's own estimate (_feed_est, over _feed_parts' strings) beside the split's (_parts_est, above)
        f = _feed(n=40); parts = km._feed_parts(f); body = km._feed_body(f)
        self.assertLess(km._feed_est(parts), len(body))
        self.assertGreater(km._feed_est(parts), 0.7 * len(body))

    def test_wire_stats_count_exactly(self):
        # A cell is made by the pusher and materialized by whichever sender thread first needs the whole frame, so
        # its counter is bumped from many threads at once; a bare `+= 1` is a read-modify-write that drifts low
        # without the GIL, which is why the counters go through _wire_bump under a lock.
        s0 = km._wire_stats["feed_body"]
        errs = []

        def run():
            try:
                for _ in range(2000):
                    km._LazyWire(lambda: "{}", 2, "feed_body").text()
            except Exception as e:                     # noqa: BLE001 — surfaced below
                errs.append(e)
        ts = [threading.Thread(target=run, daemon=True) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        self.assertEqual(errs, [])
        self.assertFalse(any(t.is_alive() for t in ts))
        self.assertEqual(km._wire_stats["feed_body"] - s0, 8 * 2000)

    def test_wire_bump_is_exact_under_a_forced_interleaving(self):
        # the test above stays green without the lock: under the GIL a `+= 1` rarely loses its switch inside the
        # read-modify-write. A dict whose reads yield the thread forces that switch, so only the lock keeps the count.
        class _Yielding(dict):
            def get(self, k, d=None):
                v = dict.get(self, k, d); time.sleep(0); return v

            def __getitem__(self, k):
                v = dict.__getitem__(self, k); time.sleep(0); return v
        saved = km._wire_stats
        km._wire_stats = _Yielding(saved)
        try:
            s0 = km._wire_stats["feed_body"]

            def run():
                for _ in range(300):
                    km._wire_bump("feed_body")
            ts = [threading.Thread(target=run, daemon=True) for _ in range(8)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(60)
            self.assertFalse(any(t.is_alive() for t in ts))
            self.assertEqual(km._wire_stats["feed_body"] - s0, 8 * 300)
        finally:
            km._wire_stats = saved


class ANonJsonValueOnTheWireIsCountedAndSaidOnce(unittest.TestCase):
    """The delta paths' encoders carried a bare `default=str`, which turned a value json cannot encode into a
    silent str() on the wire, and the whole-frame dumps had no `default` at all and raised. _wire_default keeps
    the delta paths' bytes and adds the evidence: _wire_stats["default_str"] counts each value per encode, and
    stderr names the type once. Every encoder on the path is driven through the REAL _push here — the per-entry
    pass, the whole frame, the delta frame."""

    def setUp(self):
        saved = set(km._wire_default_said)
        km._wire_default_said.clear()
        self.addCleanup(lambda: (km._wire_default_said.clear(), km._wire_default_said.update(saved)))

    def test_wire_default_returns_str_counts_each_call_and_says_each_type_once(self):
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(json.dumps({"a": {1, 2}, "b": {3}}, default=km._wire_default_in("synthetic")),
                             '{"a": "{1, 2}", "b": "{3}"}', "the bytes default=str produced")
            self.assertEqual(km._wire_default(frozenset(), "synthetic"), "frozenset()")
        self.assertEqual(_delta(km._wire_stats, s0), {"default_str": 3}, "one per value encoded")
        self.assertEqual(err.getvalue(), "wire: set serialized via str() in synthetic\n"
                                         "wire: frozenset serialized via str() in synthetic\n",
                         "one line per type, naming the encoder")

    def test_the_first_sighting_of_a_type_files_one_refused_bell_row(self):
        # A counter and a stderr line reach nobody at the dashboard: the repo's convention for a fault the
        # user should see is one bell row of kind "refused" per distinct fault (#1020, the state readers).
        # The type name is the fault's identity, so the row files once per type, beside the stderr line
        # (review find, 2026-09-08).
        notices = []
        with mock.patch.object(km, "_sync_notice", lambda text, ok=True, kind="sync": notices.append((text, ok, kind))), \
                redirect_stderr(io.StringIO()):
            km._wire_default({1}, "synthetic"); km._wire_default({2}, "synthetic")
            km._wire_default(frozenset(), "bars.body")
        self.assertEqual([(ok, k) for _t, ok, k in notices], [(False, "refused"), (False, "refused")],
                         "one row per distinct type, none for a repeat")
        self.assertIn("set", notices[0][0]); self.assertIn("synthetic", notices[0][0])
        self.assertIn("frozenset", notices[1][0]); self.assertIn("bars.body", notices[1][0])

    def test_a_bars_payload_carrying_a_set_ships_the_string_to_a_legacy_timeline_client(self):
        tl_build = _timeline(); tl_build["turns"][SID][0]["tags"] = {"a"}
        _World(self, timeline=tl_build)
        legacy = _client("timeline", delta=False)
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([legacy])
        self.assertEqual([f["type"] for f in legacy["frames"]], ["data", "bars"])
        self.assertEqual(legacy["frames"][1]["turns"][SID][0]["tags"], "{'a'}", "shipped as str(), as the delta path did")
        self.assertNotIn("_keys", legacy["frames"][1])
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_body": 1, "default_str": 2, "split_miss": 3},
                         "one per encode of the value: the per-entry pass (_delta_split) and the whole frame (_push)")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _delta_split"],
                         "said once, naming the encoder that met it first; the whole frame's encode adds no line")
        s0 = dict(km._wire_stats)
        with redirect_stderr(err):
            km._push([legacy])                                   # an unchanged cycle: nothing encoded, nothing said
        self.assertEqual(_delta(km._wire_stats, s0), {})
        self.assertEqual(len(_wire_lines(err)), 1)

    def test_a_feed_card_carrying_a_set_ships_the_string_to_a_legacy_feed_client(self):
        # the whole-frame dump had no `default`: this raised inside _push, on the pusher thread
        odd = _feed(n=2); odd["asks"][0]["when"] = {1, 2}
        _World(self, feed=odd)
        legacy = _client("feed", delta=False)
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([legacy])
        self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"])
        self.assertEqual(legacy["frames"][0]["asks"][0]["when"], "{1, 2}", "shipped as str(), as the delta path did")
        self.assertIn('"when": "{1, 2}"', km._feed_wire[5][0]["%s:g0" % SID], "the per-card string carries the same bytes")
        self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "feed_body": 1, "default_str": 2},
                         "one per encode of the value: the per-card pass (_feed_parts) and the whole frame (_feed_body); a "
                         "whole-frame client splits nothing")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _feed_parts"])

    def test_a_delta_frame_re_encodes_the_changed_entry_and_counts_it(self):
        tl_build = _timeline(); tl_build["turns"][SID][0]["tags"] = {"a"}
        w = _World(self, timeline=tl_build)
        tl = _client("timeline")                                 # a delta client: keyed full first, then deltas
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([tl])
        self.assertNotIn("_keys", tl["frames"][1], "no full carries a key list (T278c)")
        self.assertEqual(tl["frames"][1]["turns"][SID][0]["tags"], "{'a'}")
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_body": 1, "default_str": 2, "split_miss": 3}, "the split and the keyed full")
        nxt = _timeline(nbars=3, now=2); nxt["turns"][SID][0]["tags"] = {"a"}; nxt["turns"][SID][1]["tags"] = {"b"}
        w.timeline = nxt
        s0 = dict(km._wire_stats)
        with redirect_stderr(err):
            km._push([tl])
        self.assertEqual(tl["frames"][-1]["type"], "delta")
        sent = tl["frames"][-1]["coll"]["turns"]["set"]
        self.assertEqual(sorted(sent), ["%s%sb1" % (SID, km._DELTA_SEP), "%s%sb2" % (SID, km._DELTA_SEP)],
                         "the unchanged bar (same entry string) does not ride")
        self.assertEqual(sent["%s%sb1" % (SID, km._DELTA_SEP)]["tags"], "{'b'}", "the delta frame ships the same str()")
        self.assertEqual(_delta(km._wire_stats, s0), {"default_str": 3, "split_miss": 3},
                         "two sets in the per-entry pass, and the changed entry's set again in the delta frame; no whole frame")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _delta_split"], "still said once")

    def test_a_set_in_the_remainder_is_counted_by_the_parts_encoder_and_named(self):
        # the remainder's dump (rest_sig) is a wire encoder too: a value outside every collection meets _wire_default
        # there, counted once and named for that encoder
        _World(self)
        p = _bars_of(_timeline()); p["extra"] = {"x"}
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            parts = km._delta_parts("bars", p)
        self.assertIsNotNone(parts, "the payload keys: the set is in the remainder, not a collection")
        self.assertEqual(_delta(km._wire_stats, s0)["default_str"], 1)
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _delta_parts"])
        self.assertIn('"extra": "{\'x\'}"', parts[2], "the remainder's signature carries the str() bytes")


class ARaisingSerializerLeavesThePusherAlive(unittest.TestCase):
    """The wire section of _push runs after its build try, and _push_all, _pusher_cycle_jobs, _pusher_cycle and
    _pusher have no except around it: a raise there used to end the pusher thread for the life of the process,
    every dashboard frozen until a restart. A fill that raises now stands its slot down for the cycle (one
    traceback; the slot's other clients skipped without another), a send that raises skips that client, and the
    next cycle retries; _pusher_cycle_jobs catches whatever escapes _push_all. Every raise here is synthetic and
    asserted on its own marker text, never the interpreter's."""

    TICK_JOBS = ("_apply_pending_ops", "_turn_notify_tick", "_lift_spent_awaiting", "_death_sweep_tick",
                 "_end_on_idle_sweep", "_deferral_sweep_tick", "_auto_nudge_tick", "_interrupt_block_tick",
                 "_auto_pause_on_limit", "_usage_poll_tick", "_auto_pause_on_spend_limit", "_auto_resume_retry",
                 "_auto_resume_session_retry", "_auto_retry_tick", "_idle_queue_drive_tick",
                 "_clear_done_working_notes")

    @staticmethod
    def _split_raising_for(ftype):
        real = km._delta_parts

        def split(kind, payload):
            if kind == ftype:
                raise KeyError("synthetic fill failure")
            return real(kind, payload)
        return split

    @staticmethod
    def _feed_fill_raising():
        """The feed's fill in this fork is its own per-card pass (_feed_parts); a raise there is the FEED slot's."""
        return mock.patch.object(km, "_feed_parts", side_effect=KeyError("synthetic fill failure"))

    def test_a_fill_that_raises_stands_its_slot_down_for_the_cycle_and_the_other_slot_is_served(self):
        w = _World(self, feed=_feed(), timeline=_timeline())
        dfeed, dfeed2, tl = _client("feed"), _client("feed"), _client("timeline")
        err = io.StringIO()
        with self._feed_fill_raising(), redirect_stderr(err):
            km._push([dfeed, tl, dfeed2])                        # returns: nothing escapes
        self.assertEqual(err.getvalue().count("push send feed (feed)"), 1,
                         "one traceback for the fill; the slot's other client is skipped without another")
        self.assertIn("synthetic fill failure", err.getvalue())
        self.assertEqual(dfeed["frames"], []); self.assertEqual(dfeed2["frames"], [])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"], "the bars slot is unaffected")
        self.assertIsNone(km._feed_wire, "a fill that raised cached nothing")
        w.feed = _feed(build_id=2)                               # the next build is sound: served
        with redirect_stderr(err):
            km._push([dfeed, tl, dfeed2])
        self.assertEqual([f["type"] for f in dfeed["frames"]], ["feed"]); self.assertEqual([f["type"] for f in dfeed2["frames"]], ["feed"])
        self.assertEqual(err.getvalue().count("push send"), 1, "the sound build logged nothing")

    def test_a_bars_fill_that_raises_stands_the_bars_slot_down_and_the_feed_is_served(self):
        w = _World(self, feed=_feed(), timeline=_timeline())
        tl, dfeed, tl2 = _client("timeline"), _client("feed"), _client("timeline")
        err = io.StringIO()
        with mock.patch.object(km, "_delta_parts", side_effect=self._split_raising_for("bars")), redirect_stderr(err):
            km._push([tl, dfeed, tl2])
        self.assertEqual(err.getvalue().count("push send bars (timeline)"), 1)
        self.assertIn("synthetic fill failure", err.getvalue())
        self.assertEqual([f["type"] for f in tl["frames"]], ["data"], "the lanes frame went from the build section; no bars")
        self.assertEqual([f["type"] for f in tl2["frames"]], ["data"])
        self.assertEqual([f["type"] for f in dfeed["frames"]], ["feed"], "the feed slot is unaffected")
        self.assertIsNone(km._bars_wire)
        w.timeline = _timeline(now=2)
        with redirect_stderr(err):
            km._push([tl, dfeed, tl2])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"]); self.assertEqual([f["type"] for f in tl2["frames"]], ["data", "bars"])

    def test_a_board_clients_failed_fill_stands_the_feed_slot_down_not_the_bars(self):
        # the sessions board (app "fleet", the pane's existing name) rides the feed payload: its fill's raise is the
        # FEED slot's, logged once as such, and stands that slot down for the cycle (the second board client skipped
        # without another traceback) while the bars slot is served
        w = _World(self, feed=_feed(), timeline=_timeline())
        board, tl, board2 = _client("fleet"), _client("timeline"), _client("fleet")
        err = io.StringIO()
        with self._feed_fill_raising(), redirect_stderr(err):
            km._push([board, tl, board2])
        self.assertEqual(err.getvalue().count("push send feed (fleet)"), 1, "logged as the feed slot, once")
        self.assertEqual(err.getvalue().count("push send"), 1)
        self.assertIn("synthetic fill failure", err.getvalue())
        self.assertEqual(board["frames"], []); self.assertEqual(board2["frames"], [])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"], "the bars slot is served")
        self.assertIsNone(km._feed_wire); self.assertIsNotNone(km._bars_wire)
        w.feed = _feed(build_id=2)
        with redirect_stderr(err):
            km._push([board, tl, board2])
        self.assertEqual([f["type"] for f in board["frames"]], ["feed"]); self.assertEqual([f["type"] for f in board2["frames"]], ["feed"])
        self.assertEqual(err.getvalue().count("push send"), 1, "the sound build logged nothing")

    def test_a_send_that_raises_skips_that_client_and_the_next_is_served(self):
        _World(self, feed=_feed())
        c1, c2 = _client("feed"), _client("feed")
        c1["dlock"] = _RaisingLock()                             # a synthetic raise inside this client's send path
        err = io.StringIO()
        with redirect_stderr(err):
            km._push([c1, c2])
        self.assertIn("push send feed (feed)", err.getvalue()); self.assertIn("synthetic send failure", err.getvalue())
        self.assertEqual(c1["frames"], [])
        self.assertEqual([f["type"] for f in c2["frames"]], ["feed"], "the next client is served")
        self.assertIsNotNone(km._feed_wire, "the fill stood: only the send failed")

    def test_a_whole_frame_whose_encode_raises_leaves_the_slot_for_a_retry(self):
        _World(self, feed=_feed())
        legacy, dfeed = _client("feed", delta=False), _client("feed")   # both take a whole frame on their first send

        def encode_raises(cell):
            raise ValueError("synthetic encode failure")
        err = io.StringIO()
        with mock.patch.object(km._LazyWire, "text", new=encode_raises), redirect_stderr(err):
            km._push([legacy, dfeed])
        self.assertEqual(err.getvalue().count("push send feed (feed)"), 2, "each whole-frame client's send raised, was logged, skipped")
        self.assertIn("synthetic encode failure", err.getvalue())
        self.assertEqual(err.getvalue().count("view-delta feed:"), 1,
                         "the delta client's own fallback (a whole frame) met the same raise; the belt caught it")
        self.assertEqual(legacy["frames"], []); self.assertEqual(dfeed["frames"], [])
        self.assertNotIn(("feed",), legacy["sent"], "the dedup slot was not written: the next cycle retries")
        self.assertNotIn(("feed",), dfeed["sent"]); self.assertNotIn("feed", dfeed.get("dstate", {}))
        self.assertIsNotNone(km._feed_wire, "the fill stood"); self.assertFalse(km._feed_wire[3].materialized())
        km._push([legacy, dfeed])                                # the encode works again: the same build's frame goes
        self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"]); self.assertEqual([f["type"] for f in dfeed["frames"]], ["feed"])
        self.assertNotIn("_keys", dfeed["frames"][0], "no full carries a key list (T278c)")
        self.assertTrue(km._feed_wire[3].materialized())

    def test_the_cycle_loop_survives_a_push_all_that_raises(self):
        err = io.StringIO()
        with mock.patch.multiple(km, **{nm: lambda *a, **k: None for nm in self.TICK_JOBS}), \
                mock.patch.object(km, "_push_all", side_effect=RuntimeError("synthetic push failure")), redirect_stderr(err):
            km._pusher_cycle_jobs(NOW, {}, True)                 # returns: the belt logged it
        self.assertIn("push: ", err.getvalue()); self.assertIn("synthetic push failure", err.getvalue())

    def test_the_wire_section_and_the_belt_are_in_the_source(self):
        src = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
        push = src[src.index("def _push(targets"):]; push = push[:push.index("\ndef ")]
        i = push.index("for c in targets:")
        self.assertIn("        try:\n            if c[\"app\"] in (\"feed\", \"fleet\", \"waiting\"):", push[i:])
        self.assertIn('sys.stderr.write("push send %s (%s): %s\\n"', push[i:])
        jobs = src[src.index("def _pusher_cycle_jobs("):]; jobs = jobs[:jobs.index("\ndef ")]
        i = jobs.index("_push_all(tmux=tmux)")
        self.assertLess(i, jobs.index("except Exception:", i)); self.assertLess(jobs.index("except Exception:", i), jobs.index("finally:", i))


if __name__ == "__main__":
    unittest.main()
