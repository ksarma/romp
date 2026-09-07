#!/usr/bin/env python3
"""One encode per payload per build, and a pusher thread that survives a serializer's raise (2026-09-06, PLAN-2 P5/P8).

Each rebuild used to serialize the feed and the bars THREE times on the pusher thread: the whole body
(_feed_body, json.dumps(bars)), the dedup signature (_dedup_sig: a sort_keys re-dump of the stripped
payload) and the per-entry pass the delta paths need (_feed_parts, _delta_parts). The 2026-09-06 GIL
profile put the two redundant encodes at about 0.6 s of a 1.6 s rebuild cycle. Now the per-entry pass is
the only encode: the signature is a tuple of its strings (_feed_sig, _bars_sig), and the whole frame is a
_LazyWire cell made on the first send that actually needs one — a client without the delta cap, a fresh
socket, a delta past the size guard — and kept in the wire tuple (_feed_wire, _bars_wire) for the next.
The per-card encode is memoized on the build's asks list, so a ledgers-only refill re-encodes no card.

The pusher's wire section runs AFTER _push's build try, and _push_all and _pusher had no except: a raise
there killed the pusher thread for the life of the process (every dashboard frozen until a restart), and
HEAD already had one such raise waiting (a card without an itemId). The section now stands a raising fill's
slot down for the cycle and skips a client whose send raised, loudly; _pusher_cycle_jobs has a belt.

Synthetic only: placeholder ids, the notes-api demo world, TESTHOST.
"""
import collections
import io
import json
import os
import tempfile
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
    return {"type": "timeline", "sessions": [{"id": SID, "name": "web"}],
            "turns": {SID: [{"id": "b%d" % i, "t": i, "end": i + 1, "open": False} for i in range(nbars)]},
            "judging": [], "messages": None if unkeyable else [], "now": now}   # None where a list belongs: unkeyable


def _bars_of(tl, warming=False):
    return {"type": "bars", "turns": tl["turns"], "judging": tl["judging"], "messages": tl["messages"],
            "now": tl["now"], "warming": warming}


def _client(app, caps=(), delta=True):
    c = {"app": app, "alive": True, "wid": "w-" + app, "qbytes": 0, "sent": {}, "delta": delta, "caps": set(caps),
         "frames": []}
    c["send"] = lambda s: c["frames"].append(json.loads(s))
    return c


class _RaisingLock:
    """A client slot lock whose acquire raises, so the send path fails inside its `with _client_lock(c)` and
    the test asserts on THIS message. An `object()` in the slot raises there too, but as AttributeError
    on 3.10 and TypeError from 3.11 (bpo-12022), so the interpreter's wording is not a stable marker."""

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
        saved_wire = (km._feed_wire, km._bars_wire, km._skel_wire, km._feed_cards_memo, dict(km._delta_parts_cache))
        saved_built = (list(km._built_feed), list(km._built_timeline))
        km._cached_feed = lambda now, tmux, sig, connect=False: self.feed
        km._cached_timeline = lambda now, tmux, sig, connect=False: self.timeline
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: self.timeline
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        km._DELTA_MAX_FRACTION = 10.0        # synthetic payloads are tiny: the size guard would send wholes
        km._feed_wire = km._bars_wire = km._skel_wire = None
        km._feed_cards_memo = None
        km._delta_parts_cache.clear()
        km._built_timeline[:] = [None, timeline, time.time(), time.time()]   # warmed: a connect push serves the cache

        def restore():
            for n, v in saved.items():
                setattr(km, n, v)
            km._feed_wire, km._bars_wire, km._skel_wire, km._feed_cards_memo = saved_wire[:4]
            km._delta_parts_cache.clear(); km._delta_parts_cache.update(saved_wire[4])
            km._built_feed[:] = saved_built[0]; km._built_timeline[:] = saved_built[1]
        test.addCleanup(restore)


class OneEncodePerBuild(unittest.TestCase):

    def test_a_rebuild_encodes_each_payload_once_and_whole_frames_only_where_one_goes(self):
        w = _World(self, feed=_feed(), timeline=_timeline())
        cap = _client("feed", caps=(km.FEED_DELTA_CAP,))          # the kernel-served panes: feed deltas
        legacy = _client("feed", delta=False)                     # a pipe, a relay: whole frames
        tl = _client("timeline")                                  # every timeline pane: slot deltas
        calls = collections.Counter()
        real_parts, real_body, real_strip = km._feed_parts, km._feed_body, km._strip_trgb
        with mock.patch.object(km, "_feed_parts", side_effect=lambda f: calls.update(["parts"]) or real_parts(f)), \
             mock.patch.object(km, "_feed_body", side_effect=lambda f: calls.update(["body"]) or real_body(f)), \
             mock.patch.object(km, "_strip_trgb", side_effect=lambda a: calls.update(["strip"]) or real_strip(a)):
            s0 = dict(km._wire_stats)
            km._push([cap, legacy, tl])
            self.assertEqual(calls["parts"], 1, "one per-entry pass")
            self.assertEqual(calls["strip"], 5, "each card encoded once")
            self.assertEqual(calls["body"], 1, "one whole feed frame, shared by the legacy client and the cap client's first frame")
            self.assertEqual([f["type"] for f in cap["frames"]], ["feed"])
            self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"])
            self.assertIn("trgb", legacy["frames"][0]["asks"][0])
            self.assertIn("trgb", cap["frames"][0]["asks"][0], "every whole frame is the tinted legacy body")
            self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"])
            self.assertIn("_keys", tl["frames"][1])
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "feed_body": 1, "bars_body": 1})
            self.assertEqual(km._feed_wire[4], km._feed_sig(km._feed_wire[5]), "the feed's signature is P5's tuple")
            self.assertEqual(km._bars_wire[4], km._bars_sig(km._bars_wire[5]), "so is the bars'")
            self.assertEqual(legacy["sent"][("feed",)][0], km._feed_wire[4])
            # a second cycle over the same builds: nothing encoded, nothing made, nothing sent
            calls.clear(); s0 = dict(km._wire_stats); n = [len(c["frames"]) for c in (cap, legacy, tl)]
            km._push([cap, legacy, tl])
            self.assertEqual(dict(calls), {})
            self.assertEqual(_delta(km._wire_stats, s0), {})
            self.assertEqual([len(c["frames"]) for c in (cap, legacy, tl)], n)
            # a rebuild seen only by delta clients: the per-entry pass runs, no whole frame is ever made
            w.feed = _feed(build_id=2, asks=[_card(i, text="changed" if i == 2 else None) for i in range(5)])
            w.timeline = _timeline(nbars=3, now=2)
            calls.clear(); s0 = dict(km._wire_stats)
            km._push([cap, tl])
            self.assertEqual(calls["parts"], 1); self.assertEqual(calls["strip"], 5); self.assertEqual(calls["body"], 0)
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1})
            self.assertEqual(cap["frames"][-1]["type"], "feedDelta")
            self.assertEqual([a["itemId"] for a in cap["frames"][-1]["asks"]], ["%s:g2" % SID])
            self.assertEqual(tl["frames"][-1]["type"], "delta")
            self.assertFalse(km._feed_wire[3].materialized(), "no client took a whole feed frame")
            self.assertFalse(km._bars_wire[3].materialized(), "…or a whole bars frame")
            # the legacy client joins the next cycle: this build's whole frame is made now, once
            calls.clear(); s0 = dict(km._wire_stats)
            km._push([cap, legacy, tl])
            self.assertEqual(dict(calls), {"body": 1})
            self.assertEqual(_delta(km._wire_stats, s0), {"feed_body": 1})
            self.assertEqual(legacy["frames"][-1]["buildId"], 2)
            self.assertTrue(km._feed_wire[3].materialized())
            self.assertEqual(km._feed_wire[3].size(), len(km._feed_body(w.feed)), "size() is exact once made")

    def test_the_bars_split_made_at_the_fill_is_the_one_the_delta_path_records(self):
        _World(self, timeline=_timeline())
        tl = _client("timeline")
        km._push([tl])
        parts = km._bars_wire[5]
        self.assertIsNotNone(parts)
        self.assertIs(tl["dstate"]["bars"]["parts"], parts,
                      "handed down, not re-split (single-threaded here; the hand-down is what makes it hold under a "
                      "concurrent connect push, which can evict _delta_parts_cache's single slot)")
        self.assertEqual(km._bars_wire[4], km._bars_sig(parts))
        km._delta_parts_cache.clear()                 # a connect push on another thread evicted the slot
        with mock.patch.object(km, "_delta_parts", side_effect=AssertionError("re-split")):
            km._push([tl])                            # the wire hit hands the split down: no re-split, nothing sent
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"])

    def test_an_unkeyable_bars_build_takes_whole_frames_and_the_string_signature(self):
        w = _World(self, timeline=_timeline(unkeyable=True))   # messages None where a list belongs: _delta_parts gives None
        tl = _client("timeline")
        km._delta_unkeyable_said.clear()
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([tl]); km._push([tl])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"], "the whole frame went once; the repeat deduped")
        self.assertNotIn("_keys", tl["frames"][1])
        self.assertIsNone(tl["frames"][1]["messages"])
        self.assertIsInstance(km._bars_wire[4], str, "the sort_keys fallback signature, as before")
        self.assertIsNone(km._bars_wire[5])
        self.assertTrue(km._bars_wire[3].materialized(), "the whole dump the signature needed pre-fills the cell")
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_sig_fallback": 1})
        self.assertEqual(err.getvalue().count("cannot be keyed"), 1, "said once, as before")
        w.timeline = _timeline(unkeyable=True, now=2, nbars=3)   # a real change: the whole frame goes again
        with redirect_stderr(err):
            km._push([tl])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars", "data", "bars"],
                         "a rebuild: its lanes frame once, and the whole bars frame again")

    def test_a_ledgers_only_refill_re_encodes_no_card(self):
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

    def test_perf_reports_the_wire_counters(self):
        snap = km._PERF_STATS.snapshot()
        self.assertEqual(snap["memos"]["wire"], dict(km._wire_stats))
        self.assertEqual(set(snap["memos"]["wire"]),
                         {"feed_cards_hit", "feed_cards_miss", "feed_body", "bars_body", "bars_sig_fallback", "default_str"})


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

    def test_the_estimates_sit_under_the_whole_frame_but_not_far(self):
        f = _feed(n=40); parts = km._feed_parts(f); body = km._feed_body(f)
        self.assertLess(km._feed_est(parts), len(body))
        self.assertGreater(km._feed_est(parts), 0.7 * len(body))
        bars = _bars_of(_timeline(nbars=30))
        bp = km._delta_parts("bars", bars); whole = json.dumps(bars)
        self.assertLess(km._bars_est(bp), len(whole))
        self.assertGreater(km._bars_est(bp), 0.7 * len(whole))



class ANonJsonValueOnTheWireIsCountedAndSaidOnce(unittest.TestCase):
    """The wire encoders carried a bare `default=str`, which turned a value json cannot encode into a silent str()
    on the wire (review nit, 2026-09-06). _wire_default keeps the bytes and adds the evidence: memos.wire
    default_str counts each value per encode, and stderr names the type once. Every encoder on the path is
    driven through the REAL _push here — the per-entry pass, the whole frame, the delta frame."""

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

    def test_a_bars_payload_carrying_a_set_ships_the_string_to_a_legacy_timeline_client(self):
        tl_build = _timeline(); tl_build["turns"][SID][0]["tags"] = {"a"}
        _World(self, timeline=tl_build)
        legacy = _client("timeline", delta=False)
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([legacy])
        self.assertEqual([f["type"] for f in legacy["frames"]], ["data", "bars"])
        self.assertEqual(legacy["frames"][1]["turns"][SID][0]["tags"], "{'a'}", "shipped as str(), as before")
        self.assertNotIn("_keys", legacy["frames"][1])
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_body": 1, "default_str": 2},
                         "one per encode of the value: the per-entry pass (_delta_split) and the whole frame (_push)")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _delta_split"],
                         "said once, naming the encoder that met it first; the whole frame's encode adds no line")
        s0 = dict(km._wire_stats)
        with redirect_stderr(err):
            km._push([legacy])                                   # an unchanged cycle: nothing encoded, nothing said
        self.assertEqual(_delta(km._wire_stats, s0), {})
        self.assertEqual(len(_wire_lines(err)), 1)

    def test_a_feed_card_carrying_a_set_ships_the_string_to_a_legacy_feed_client(self):
        odd = _feed(n=2); odd["asks"][0]["when"] = {1, 2}
        _World(self, feed=odd)
        legacy = _client("feed", delta=False)
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([legacy])
        self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"])
        self.assertEqual(legacy["frames"][0]["asks"][0]["when"], "{1, 2}", "shipped as str(), as before")
        self.assertIn('"when": "{1, 2}"', km._feed_wire[5][0]["%s:g0" % SID], "the per-card string carries the same bytes")
        self.assertEqual(_delta(km._wire_stats, s0), {"feed_cards_miss": 1, "feed_body": 1, "default_str": 2},
                         "one per encode of the value: the per-card pass (_feed_parts) and the whole frame (_feed_body)")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _feed_parts"])

    def test_a_delta_frame_re_encodes_the_changed_entry_and_counts_it(self):
        tl_build = _timeline(); tl_build["turns"][SID][0]["tags"] = {"a"}
        w = _World(self, timeline=tl_build)
        tl = _client("timeline")                                 # a delta client: keyed full first, then deltas
        s0 = dict(km._wire_stats); err = io.StringIO()
        with redirect_stderr(err):
            km._push([tl])
        self.assertIn("_keys", tl["frames"][1])
        self.assertEqual(tl["frames"][1]["turns"][SID][0]["tags"], "{'a'}")
        self.assertEqual(_delta(km._wire_stats, s0), {"bars_body": 1, "default_str": 2}, "the split and the keyed full")
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
        self.assertEqual(_delta(km._wire_stats, s0), {"default_str": 3},
                         "two sets in the per-entry pass, and the changed entry's set again in the delta frame; no whole frame")
        self.assertEqual(_wire_lines(err), ["wire: set serialized via str() in _delta_split"], "still said once")


class ARaisingSerializerLeavesThePusherAlive(unittest.TestCase):

    def test_a_fill_that_raises_stands_its_slot_down_for_the_cycle_and_the_other_slot_is_served(self):
        w = _World(self, feed=_feed(), timeline=_timeline())
        bad = _feed(); del bad["asks"][2]["itemId"]              # HEAD's own exposure: _feed_parts raises KeyError
        w.feed = bad
        cap, cap2, tl = _client("feed", caps=(km.FEED_DELTA_CAP,)), _client("feed", caps=(km.FEED_DELTA_CAP,)), _client("timeline")
        err = io.StringIO()
        with redirect_stderr(err):
            km._push([cap, tl, cap2])                            # returns: nothing escapes
        self.assertEqual(err.getvalue().count("push send feed (feed)"), 1,
                         "one traceback for the fill; the slot's other client is skipped without another")
        self.assertIn("KeyError", err.getvalue())
        self.assertEqual(cap["frames"], []); self.assertEqual(cap2["frames"], [])
        self.assertEqual([f["type"] for f in tl["frames"]], ["data", "bars"], "the bars slot is unaffected")
        self.assertIsNone(km._feed_wire, "a fill that raised cached nothing")
        w.feed = _feed(build_id=2)                               # the next build is sound: served
        with redirect_stderr(err):
            km._push([cap, tl, cap2])
        self.assertEqual([f["type"] for f in cap["frames"]], ["feed"]); self.assertEqual([f["type"] for f in cap2["frames"]], ["feed"])

    def test_a_send_that_raises_skips_that_client_and_the_next_is_served(self):
        _World(self, feed=_feed())
        c1, c2 = _client("feed", caps=(km.FEED_DELTA_CAP,)), _client("feed", caps=(km.FEED_DELTA_CAP,))
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
        legacy, cap = _client("feed", delta=False), _client("feed", caps=(km.FEED_DELTA_CAP,))
        err = io.StringIO()
        with mock.patch.object(km, "_feed_body", side_effect=ValueError("synthetic encode failure")), redirect_stderr(err):
            km._push([legacy, cap])
        self.assertEqual(err.getvalue().count("synthetic encode failure"), 2, "each whole-frame client's send raised, was logged, skipped")
        self.assertEqual(legacy["frames"], []); self.assertEqual(cap["frames"], [])
        self.assertNotIn(("feed",), legacy["sent"], "the dedup slot was not written: the next cycle retries")
        self.assertNotIn("efeed", cap)
        km._push([legacy, cap])                                  # the encode works again: the same build's frame goes
        self.assertEqual([f["type"] for f in legacy["frames"]], ["feed"]); self.assertEqual([f["type"] for f in cap["frames"]], ["feed"])
        self.assertTrue(km._feed_wire[3].materialized())

    def test_the_cycle_loop_survives_a_push_all_that_raises(self):
        err = io.StringIO()
        with mock.patch.object(km, "_push_all", side_effect=RuntimeError("synthetic push failure")), redirect_stderr(err):
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
