#!/usr/bin/env python3
"""The feed streams as DELTAS to a caught-up client that asked for them; everyone else keeps full frames.

Measured on a live kernel 2026-09-02: every feed push was the whole frame — 5.76 MB for a board of ~660
cards (asks 4.8 MB, ledgers 0.95 MB, all else ~13 KB), re-sent every few seconds during activity, when only
0-21 cards and 0-1 ledgers differed between consecutive pushes. Worse, each card carried a server-computed
age colour (`trgb`) that stepped with the clock, so a colour step anywhere on the board re-sent the whole
frame with nothing having happened. Three frames (16 MB, WS_QUEUE_BYTES) put a client behind enough to be
dropped, the drop was silent, the reconnect resynced with another full frame, and the shim's stale banner
flashed on every cycle — ~300 raises a day, almost all on the feed pane.

Pinned here: a client that announced FEED_DELTA_CAP gets a {type:"feedDelta"} once it holds a full frame;
a clock-only tick (a `now` step, a `trgb` step) sends nothing on EITHER path; removals ride the delta —
cards and ledgers, including a ledger removed across a ledger-less build in between; a 2-card change is a
small fraction of the full frame; a client that did not announce keeps receiving full frames, `trgb`
included (an older bundle destructures it unguarded); deltas never carry `trgb`; the `ready` handshake is
served the cached full frame at once, and nothing arrives before it; needFullFeed re-bases; the ready
handler emits no tab order of its own (the connect push's guarded one is the only source).

Synthetic only: the notes-api demo world, TESTHOST, placeholder ids.
"""
import base64
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_feeddelta", os.path.join(BIN, "romp-kernel")).load_module()

KSRC = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
SID = "11111111-2222-3333-4444-555555555555"
SID_B = "11111111-2222-3333-4444-666666666666"
NOW = 1781100000


def _card(i, now=NOW, **over):
    # `trgb` is the kernel's age tint for the card at build time `now` — it STEPS with the clock, which is
    # exactly what the dedup and the delta path must see through
    t = NOW - i * 60
    c = {"itemId": "%s:g%d" % (SID, i), "sid": SID, "name": "web", "color": {"bg": "#123456", "fg": "#ffffff"},
         "text": "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
         "trgb": list(km.cm.age_rgb(now - t)),
         "turnId": "%s:g%d" % (SID, i), "column": "working", "summary": "s" * 400, "blockSummary": None,
         "tree": [{"id": "%s:g%d.%d" % (SID, i, j), "text": "step %d" % j, "status": "done",
                   "t": t, "last": t, "trgb": list(km.cm.age_rgb(now - t)), "children": []} for j in range(6)]}
    c.update(over)
    return c


def _ledger(sid=SID, name="web", state="working"):
    return {"sid": sid, "name": name, "color": None, "status": {"state": state}, "ledger": {"tops": ["t" * 3000]}}


def _feed(n=300, now=NOW, build_id=1, asks=None, ledgers=True):
    f = {"type": "feed", "asks": asks if asks is not None else [_card(i, now=now) for i in range(n)],
         "now": now, "buildId": build_id, "order": [SID], "working": ["web"], "awaiting": [],
         "sessions": [{"sid": SID, "name": "web", "color": None}], "userTodos": {}, "views": {},
         "clearNotices": [], "syncNotices": [], "sdkNotices": [], "selfHost": "TESTHOST"}
    if ledgers is True:
        f["ledgers"] = [_ledger()]
    elif ledgers:
        f["ledgers"] = list(ledgers)
    return f


def _wire(feed):
    ms = json.dumps(feed)
    return ms, km._dedup_sig(feed, ms), km._feed_parts(feed)


def _client(caps=("feedDelta",), app="feed"):
    sent = []
    c = {"app": app, "alive": True, "wid": "w1", "qbytes": 0, "send": sent.append, "caps": set(caps)}
    return c, sent


def _send(c, feed):
    ms, sig, parts = _wire(feed)
    km._send_feed(c, feed, ms, sig, parts)
    return ms


def _warm(feed):
    """Install `feed` as the kernel's built + wire-cached frame; returns the saved state for the finally."""
    saved = (km._feed_wire, list(km._built_feed))
    ms, sig, parts = _wire(feed)
    km._feed_wire = (feed, feed.get("ledgers"), feed, ms, sig, parts)
    km._built_feed[:] = [None, feed, 0.0, 0.0]
    return saved, ms, parts


def _restore(saved):
    km._feed_wire = saved[0]
    km._built_feed[:] = saved[1]


class DeltaStream(unittest.TestCase):
    def test_first_frame_is_full_then_changes_arrive_as_a_delta(self):
        c, sent = _client()
        _send(c, _feed())
        self.assertEqual(json.loads(sent[-1])["type"], "feed", "a client with no base gets the full frame")
        asks = [_card(i) for i in range(300)]
        asks[3] = _card(3, text="a changed title")
        asks[7] = _card(7, column="needs_input")
        _send(c, _feed(asks=asks, now=NOW + 5, build_id=2))
        d = json.loads(sent[-1])
        self.assertEqual(d["type"], "feedDelta")
        self.assertEqual(sorted(a["itemId"] for a in d["asks"]), ["%s:g3" % SID, "%s:g7" % SID])
        self.assertEqual((d["now"], d["buildId"]), (NOW + 5, 2), "the clock fields ride every delta")
        self.assertNotIn("removeAsks", d)
        self.assertNotIn("ledgers", d, "unchanged ledgers do not ride")
        self.assertNotIn("top", d, "unchanged top-level fields do not ride")

    def test_a_clock_only_tick_sends_nothing(self):
        c, sent = _client()
        _send(c, _feed())
        # an hour later every card's tint has stepped and `now` moved — nothing else did
        _send(c, _feed(now=NOW + 3600, build_id=2))
        self.assertEqual(len(sent), 1, "nothing changed but the clock → nothing on the wire")
        # …and the client's held base advanced anyway, so the next change diffs against the newest build
        asks = [_card(i, now=NOW + 7200) for i in range(300)]
        asks[0] = _card(0, now=NOW + 7200, text="moved on")
        _send(c, _feed(asks=asks, now=NOW + 7200, build_id=3))
        self.assertEqual([a["itemId"] for a in json.loads(sent[-1])["asks"]], ["%s:g0" % SID])

    def test_removals_and_ledger_changes_ride_the_delta(self):
        c, sent = _client()
        _send(c, _feed())
        f = _feed(build_id=2)
        del f["asks"][5]
        f["ledgers"][0]["status"] = {"state": "waiting"}
        _send(c, f)
        d = json.loads(sent[-1])
        self.assertEqual(d["removeAsks"], ["%s:g5" % SID])
        self.assertNotIn("asks", d, "a removal alone upserts nothing")
        self.assertEqual([l["sid"] for l in d["ledgers"]], [SID])
        self.assertEqual(d["ledgers"][0]["status"], {"state": "waiting"})
        self.assertNotIn("removeLedgers", d)

    def test_top_level_fields_ride_whole_when_any_changed(self):
        c, sent = _client()
        _send(c, _feed())
        _send(c, dict(_feed(build_id=2), working=[]))
        d = json.loads(sent[-1])
        top = d["top"]
        self.assertEqual(top["working"], [])
        for k in ("order", "sessions", "userTodos", "views", "clearNotices", "syncNotices", "selfHost"):
            self.assertIn(k, top, "top is the COMPLETE set of non-keyed fields, so the client replaces them whole")
        for k in ("asks", "ledgers", "now", "buildId", "type"):
            self.assertNotIn(k, top)

    def test_a_delta_for_two_cards_is_a_small_fraction_of_the_full_frame(self):
        c, sent = _client()
        full = _send(c, _feed(n=400))
        asks = [_card(i) for i in range(400)]
        asks[10] = _card(10, text="changed")
        asks[20] = _card(20, column="completed")
        _send(c, _feed(asks=asks, build_id=2))
        delta = sent[-1]
        self.assertGreater(len(full), 500_000, "the synthetic board is frame-sized (%d B)" % len(full))
        self.assertLess(len(delta) / len(full), 0.02,
                        "2 of 400 cards: delta %d B vs full %d B" % (len(delta), len(full)))

    def test_a_client_that_did_not_announce_keeps_getting_full_frames(self):
        for caps, app in (((), "feed"), ((), "fleet"), (("somethingElse",), "feed")):
            c, sent = _client(caps=caps, app=app)
            _send(c, _feed())
            asks = [_card(i) for i in range(300)]
            asks[1] = _card(1, text="changed")
            _send(c, _feed(asks=asks, build_id=2))
            self.assertEqual([json.loads(s)["type"] for s in sent], ["feed", "feed"], (caps, app))
            # …with the per-client dedup intact: the same frame again is not re-sent
            _send(c, _feed(asks=asks, build_id=3))
            self.assertEqual(len(sent), 2)

    def test_a_client_announcing_after_its_first_frame_rebases_from_what_it_holds(self):
        # the base is recorded on every full send, so the cap may arrive late (it does not today — the
        # shim announces on the URL — but the delta path must never assume the order)
        c, sent = _client(caps=())
        _send(c, _feed())
        c["caps"] = {"feedDelta"}
        asks = [_card(i) for i in range(300)]
        asks[2] = _card(2, text="changed")
        _send(c, _feed(asks=asks, build_id=2))
        self.assertEqual(json.loads(sent[-1])["type"], "feedDelta")

    def test_needfullfeed_rebases_with_the_cached_full_frame(self):
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            c, sent = _client()
            _send(c, f)
            c.pop("efeed", None); c["sent"].pop(("feed",), None)   # what the needFullFeed handler does
            self.assertTrue(km._send_feed_now(c))
            self.assertEqual(json.loads(sent[-1])["type"], "feed")
            asks = [_card(i) for i in range(300)]; asks[4] = _card(4, text="x")
            _send(c, _feed(asks=asks, build_id=2))
            self.assertEqual(json.loads(sent[-1])["type"], "feedDelta", "the stream re-bases from the full frame")
        finally:
            _restore(saved)


class TintOnFullFramesOnly(unittest.TestCase):
    """`trgb` stays on FULL frames — an older bundle (a stale tab; a federated dashboard on a host running
    the previous build) destructures `it.trgb` unguarded and would throw on the first card without it — but
    it is a function of the clock, so it is excluded from the dedup signature and from deltas: a colour
    step is not a change and never re-sends the board (it did, on every step: 5.76 MB a push)."""

    def test_full_frames_carry_trgb_and_deltas_never_do(self):
        legacy, lsent = _client(caps=())
        _send(legacy, _feed())
        full = json.loads(lsent[-1])
        self.assertEqual(full["asks"][5]["trgb"], list(km.cm.age_rgb(NOW - full["asks"][5]["t"])))
        self.assertIn("trgb", full["asks"][5]["tree"][0], "tree nodes too, as before")
        delta, dsent = _client()
        _send(delta, _feed())
        asks = [_card(i) for i in range(300)]
        asks[5] = _card(5, text="changed")
        _send(delta, _feed(asks=asks, build_id=2))
        d = json.loads(dsent[-1])
        self.assertEqual(d["type"], "feedDelta")
        self.assertNotIn("trgb", d["asks"][0])
        self.assertTrue(all("trgb" not in n for n in d["asks"][0]["tree"]))

    def test_a_colour_step_alone_sends_nothing_on_either_path(self):
        for caps in ((), ("feedDelta",)):
            c, sent = _client(caps=caps)
            _send(c, _feed())
            _send(c, _feed(now=NOW + 3600, build_id=2))        # every tint stepped, nothing else
            self.assertEqual(len(sent), 1, "caps=%r: a colour step is not a change" % (caps,))

    def test_the_dedup_signature_ignores_the_tint_and_nothing_else(self):
        a = _feed(); b = _feed(now=NOW + 3600, build_id=2)
        self.assertNotEqual(a["asks"][9]["trgb"], b["asks"][9]["trgb"], "the fixture steps the tint")
        self.assertEqual(km._dedup_sig(a, json.dumps(a)), km._dedup_sig(b, json.dumps(b)))
        c = _feed(build_id=3); c["asks"][9]["tree"][0]["text"] = "a real change"
        self.assertNotEqual(km._dedup_sig(a, json.dumps(a)), km._dedup_sig(c, json.dumps(c)))
        self.assertNotIn('"trgb"', km._feed_parts(a)[0]["%s:g9" % SID])

    def test_every_builder_still_ships_the_tint_on_full_frames(self):
        self.assertEqual(KSRC.count('"trgb": list(cm.age_rgb('), 8,
                         "the eight card/node builders compute it as before (build_feed, the placeholders, quarantine)")


class ConnectTimeFrame(unittest.TestCase):
    def test_a_fresh_socket_is_served_the_cached_frame_at_once(self):
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            c, sent = _client()
            self.assertTrue(km._send_feed_now(c))
            self.assertEqual(sent, [ms], "the cached wire form, byte for byte — no build, no wait")
            self.assertIs(c["efeed"], parts, "…and it is the delta stream's base")
            # the pusher's next cycle then has nothing to add
            km._send_feed(c, f, ms, km._dedup_sig(f, ms), parts)
            self.assertEqual(len(sent), 1)
        finally:
            _restore(saved)

    def test_a_cold_kernel_has_nothing_cached_and_says_so(self):
        saved = (km._feed_wire, list(km._built_feed))
        try:
            km._feed_wire = None
            km._built_feed[:] = [None, None, 0.0, 0.0]
            c, sent = _client()
            self.assertFalse(km._send_feed_now(c))
            self.assertEqual(sent, [])
        finally:
            _restore(saved)

    def test_a_newer_build_than_the_wire_cache_is_serialized_fresh(self):
        # with no feed pane open the pusher never refreshes _feed_wire; chat clients keep _built_feed warm
        saved = (km._feed_wire, list(km._built_feed))
        try:
            old = _feed(build_id=1); new = _feed(build_id=2, asks=[_card(0, text="newest")])
            ms, sig, parts = _wire(old)
            km._feed_wire = (old, old.get("ledgers"), old, ms, sig, parts)
            km._built_feed[:] = [None, new, 0.0, 0.0]
            c, sent = _client()
            self.assertTrue(km._send_feed_now(c))
            self.assertEqual(json.loads(sent[-1])["buildId"], 2)
            self.assertIs(km._feed_wire[0], new, "…and cached for the next socket")
        finally:
            _restore(saved)


class ShimAnnouncesForTheFeedPage(unittest.TestCase):
    def test_only_the_feed_page_announces_the_capability(self):
        feed = km._shim("feed", 5, caps=km.FEED_DELTA_CAP)
        self.assertIn('var CAPS="feedDelta";', feed)
        self.assertIn('+(CAPS?"&caps="+encodeURIComponent(CAPS):"")', feed)
        for app in ("chat", "fleet", "timeline"):
            self.assertIn('var CAPS="";', km._shim(app, 5), app)
        self.assertIn('_shim("feed", v, caps=FEED_DELTA_CAP)', KSRC)


if __name__ == "__main__":
    unittest.main()
