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
included (an older bundle destructures it unguarded); deltas never carry `trgb`; `_strip_trgb` removes the
tint and nothing else; a page that announced READY_GATE_CAP is HELD — the real pusher cycle and every other
push path send it nothing — until its bundle's `ready`, which is served the cached full frame at once,
stamped with the clock as of the serve (a frame built hours earlier must not anchor the pane's ages hours
in the past); a socket that did not announce is ready from accept; needFullFeed re-bases; the ready handler
emits no tab order of its own (the connect push's guarded one is the only source); the Outline page (app=fleet)
announces the capability too (2026-09-05) and, on a real socket, hears every change after its first full frame
as a delta — federation.js applies them for fleet.ts, which keeps reading whole frames.

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
    # the {type:"caps"} frame the ready handler adds after its pushes (2026-09-05) is dropped here:
    # these tests count the FEED frames a `ready` serves, and that frame is neither a feed frame nor
    # a push. test_tag_edit_ack.py (Capability) pins the caps frame and its place in the order.
    def send(s):
        if not s.startswith('{"type": "caps"'):
            sent.append(s)
    c = {"app": app, "alive": True, "wid": "w1", "qbytes": 0, "send": send, "caps": set(caps)}
    return c, sent


def _send(c, feed):
    ms, sig, parts = _wire(feed)
    km._send_feed(c, feed, ms, sig, parts)
    return ms


def _warm(feed):
    """Install `feed` as the kernel's built + wire-cached frame (recent, so a pusher cycle serves it rather than
    rebuilding); returns the saved state for the finally."""
    saved = (km._feed_wire, list(km._built_feed))
    ms, sig, parts = _wire(feed)
    km._feed_wire = (feed, feed.get("ledgers"), feed, km._feed_body(feed), sig, parts)
    km._built_feed[:] = [None, feed, time.time(), time.time()]
    return saved, ms, parts


def _served_fresh(test, wire, feed, t0):
    """The served wire string is `feed` with its `now` replaced by the clock at the serve (t0 = just before)."""
    got = json.loads(wire)
    test.assertGreaterEqual(got["now"], int(t0), "the served `now` is the serve-time clock, not the build's")
    test.assertLessEqual(got["now"], int(time.time()) + 1)
    test.assertNotEqual(got["now"], feed["now"], "the fixture's build clock is far in the past")
    exp = dict(feed); del exp["now"]; del got["now"]
    test.assertEqual(got, exp, "…and every other byte of the frame is the cached one")


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


class LedgerRemovals(unittest.TestCase):
    """The ledger half of the delta contract, kernel side (the 2026-09-03 review found it unpinned, and
    found removals LOST across a ledger-less build: the pusher attaches `ledgers` only when a chat or
    Outline client is in the push, so a feed-only connect push — every page load, every shim reconnect's
    `ready` — carries none; recording that as 'holds no ledgers' made the next ledger-bearing build re-send
    the whole set and drop the removals in between)."""

    def test_a_ledger_that_left_rides_as_a_removal(self):
        c, sent = _client()
        _send(c, _feed(ledgers=[_ledger(), _ledger(SID_B, "api")]))
        _send(c, _feed(build_id=2, ledgers=[_ledger()]))
        d = json.loads(sent[-1])
        self.assertEqual(d["removeLedgers"], [SID_B])
        self.assertEqual(d["ledgers"], [], "the surviving ledger did not change, so it does not ride")
        self.assertNotIn("asks", d)

    def test_a_removal_survives_a_ledger_less_build_in_between(self):
        c, sent = _client()
        _send(c, _feed(ledgers=[_ledger(), _ledger(SID_B, "api")]))
        _send(c, _feed(build_id=2, ledgers=False))          # a feed-only connect push: says nothing about ledgers
        self.assertEqual(len(sent), 1, "a build with no `ledgers` key sends nothing when nothing else changed")
        self.assertEqual(sorted(c["efeed"][1]), sorted([SID, SID_B]),
                         "…and the recorded base keeps the ledgers the client still holds")
        _send(c, _feed(build_id=3, ledgers=[_ledger()]))     # session B ended meanwhile
        d = json.loads(sent[-1])
        self.assertEqual(d["removeLedgers"], [SID_B], "the removal is not lost across the ledger-less build")
        self.assertEqual(d["ledgers"], [], "and the whole set is NOT re-sent")

    def test_a_client_whose_full_frame_had_no_ledgers_gets_the_set_whole_once(self):
        c, sent = _client()
        _send(c, _feed(ledgers=False))                         # its full frame carried none: it holds none
        _send(c, _feed(build_id=2, ledgers=[_ledger(), _ledger(SID_B, "api")]))
        d = json.loads(sent[-1])
        self.assertEqual(sorted(l["sid"] for l in d["ledgers"]), sorted([SID, SID_B]))
        self.assertNotIn("removeLedgers", d)
        _send(c, _feed(build_id=3, ledgers=[_ledger(), _ledger(SID_B, "api")]))
        self.assertEqual(len(sent), 2, "unchanged after that → nothing")

    def test_a_deduped_ready_frame_leaves_the_base_alone(self):
        # the served frame is the delta base — and a frame the dedup swallowed served nothing
        f = _feed(ledgers=[_ledger(), _ledger(SID_B, "api")])
        saved, ms, parts = _warm(f)
        try:
            c, sent = _client()
            _send(c, f)                                       # the pusher's full frame, ledgers and all
            base = c["efeed"]
            self.assertFalse(km._send_feed_now(c), "the same frame again is deduped")
            self.assertIs(c["efeed"], base)
            self.assertEqual(len(sent), 1)
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


def _client_frame(text):
    """One masked client text frame, as a browser sends it."""
    data = text.encode("utf-8"); n = len(data); mask = os.urandom(4)
    if n < 126:
        hdr = bytes([0x81, 0x80 | n])
    elif n < 65536:
        hdr = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
    else:
        hdr = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
    return hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _ping_frame(data=b""):
    """One masked client ping (RFC 6455 §5.5.2). The kernel's reader thread answers it inline with a pong echoing
    the payload, after it has dispatched every message read before it — so a pong is proof that a `ready` sent
    ahead of the ping, and everything its handler ran synchronously (the connect push, the client's recorded
    delta base), are done. It orders nothing on the wire: the reader writes the pong itself (_ws_pong) while
    data frames are queued to the client's sender thread (_mk_ws_send → _ws_sender), so a frame the handler
    queued before the pong may still arrive after it."""
    mask = os.urandom(4)
    return bytes([0x89, 0x80 | len(data)]) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _read_frame(s, buf):
    """One server frame (unmasked) → (opcode, payload, leftover)."""
    def need(n):
        nonlocal buf
        while len(buf) < n:
            chunk = s.recv(1 << 20)
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
    need(2)
    ln = buf[1] & 0x7F; off = 2
    if ln == 126:
        need(4); ln = struct.unpack(">H", buf[2:4])[0]; off = 4
    elif ln == 127:
        need(10); ln = struct.unpack(">Q", buf[2:10])[0]; off = 10
    need(off + ln)
    return buf[0] & 0x0F, buf[off:off + ln], buf[off + ln:]


class ReadyHandshake(unittest.TestCase):
    """The first frame waits for the bundle's `ready` (2026-09-03 review): the shim connects before
    federation.js and feed.js have loaded and has no inbound buffer, so a frame pushed at socket accept
    could land on a page with nobody listening and be lost — and the later `ready` push then sent nothing,
    because the dedup believed the client had it (9 of 25 headless loads sat on the loader until the next
    board change). The ready handler serves the cached frame at once, with no build; the shim re-sends
    `ready` on a reconnect once the bundle has sent its own (before that, the bundle's own lifts the hold),
    and a `ready` on a client that is already ready is a re-base: the frame is served again."""

    def test_a_held_socket_hears_nothing_from_the_pusher_until_ready_then_the_cached_frame_at_once(self):
        f = _feed(n=40)
        saved, ms, parts = _warm(f)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = s2 = None
        try:
            s, buf = _connect(port, "app=feed&wid=w7&caps=feedDelta,readyGate")
            # the kernel has registered the client (it appends AFTER the handshake); give any accept-time
            # push a moment it does not need — the old code enqueued its frame right after the append
            client = _registered("w7")
            time.sleep(0.05)
            self.assertEqual(client["qbytes"], 0, "nothing is pushed at accept")
            self.assertFalse(client["ready"], "the page announced READY_GATE_CAP: held until its bundle says so")
            # The bundle is still loading; the pusher's cycles run meanwhile — the REAL _push_all → _push,
            # and the broadcast paths. The 2026-09-03 review reproduced the first frame lost to exactly
            # these cycles (real browsers, the bundle 350 ms slower) after the accept-time push was removed.
            for _ in range(3):
                km._push_all()
            km._send_to_app("feed", {"type": "syncNotice"})
            km._send_to_view("feed", {"type": "syncNotice"}, "w7")
            time.sleep(0.05)
            self.assertEqual(client["qbytes"], 0, "…and nothing from any push path: nobody is listening yet")
            self.assertNotIn("efeed", client)
            self.assertNotIn("sent", client)
            s.settimeout(0.3)
            with self.assertRaises((socket.timeout, TimeoutError)):
                s.recv(1)
            s.settimeout(10)
            self.assertEqual(buf, b"", "nothing arrived before `ready`")
            t0 = time.time()
            s.sendall(_client_frame(json.dumps({"type": "ready"})))
            op, payload, buf = _read_frame(s, buf)
            self.assertEqual(op, 0x1)
            self.assertTrue(client["ready"])
            _served_fresh(self, payload.decode("utf-8"), f, t0)   # the cached frame, no build, no wait
            self.assertIs(client["efeed"], parts, "…and it is the delta stream's base")
            # a socket that did NOT announce the hold — a relay, a pipe, an older page — is ready from accept
            s2, _ = _connect(port, "app=feed&wid=w8")
            c2 = _registered("w8")
            self.assertTrue(c2["ready"])
        finally:
            for sock in (s, s2):
                if sock is not None:
                    sock.close()
            srv.shutdown(); srv.server_close()
            _restore(saved)

    def _handler(self):
        class _FakeHandler:
            _dispatch_ws = km.Handler._dispatch_ws
            def __init__(self):
                self.pushed = []
            def _push_one(self, client):
                self.pushed.append(client)
        return _FakeHandler()

    def test_the_ready_handler_serves_a_feed_client_from_cache_and_skips_the_connect_push(self):
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            h = self._handler()
            c, sent = _client()
            c["ready"] = False                                   # held at accept (READY_GATE_CAP)
            t0 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertTrue(c["ready"], "the hold lifts on the bundle's own event")
            self.assertEqual(len(sent), 1)
            _served_fresh(self, sent[0], f, t0)
            self.assertIs(c["efeed"], parts)
            self.assertEqual(h.pushed, [], "the push could add nothing for this pane: its warmed cache IS what was served")
        finally:
            _restore(saved)

    def test_a_cold_kernel_falls_to_the_connect_push(self):
        saved = (km._feed_wire, list(km._built_feed))
        try:
            km._feed_wire = None; km._built_feed[:] = [None, None, 0.0, 0.0]
            h = self._handler()
            c, sent = _client()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(sent, [], "nothing cached to serve")
            self.assertEqual(h.pushed, [c], "so the connect push builds it")
        finally:
            _restore(saved)

    def test_an_outline_client_is_served_and_still_gets_its_connect_push(self):
        # the Outline pane needs `ledgers`, which only the connect push's session build attaches
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            h = self._handler()
            c, sent = _client(caps=(), app="fleet")
            t0 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(len(sent), 1)
            _served_fresh(self, sent[0], f, t0)
            self.assertEqual(h.pushed, [c])
        finally:
            _restore(saved)

    def test_an_outline_client_on_the_view_delta_protocol_is_served_once_as_the_slots_base(self):
        # The Outline page's shim announces ?delta=1 (upstream's view-delta slots) but not feedDelta. Served
        # through _send_client, its `ready` frame was unkeyed and left dstate["feed"] empty, so the connect
        # push's _send_slot sent the WHOLE frame again, keyed: two full frames per `ready`. Served through
        # _send_slot the frame is keyed, it is the slot's base, and the push that follows can delta.
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            h = self._handler()
            c, sent = _client(caps=("readyGate",), app="fleet")
            c["delta"] = True; c["ready"] = False
            t0 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(len(sent), 1)
            got = json.loads(sent[0])
            self.assertEqual(got["type"], "feed")
            self.assertIn("_keys", got, "served keyed: the frame is the slot's base")
            self.assertGreaterEqual(got["now"], int(t0), "…stamped with the clock of the serve")
            self.assertIn("feed", c.get("dstate") or {}, "…and the slot holds it")
            self.assertNotIn("efeed", c, "the feed-delta protocol's base is not this client's")
            self.assertEqual(h.pushed, [c], "the Outline still gets its connect push (for the ledgers)")
            km._push([c])                                       # the real push: it attaches ledgers (none here)
            self.assertEqual([json.loads(x)["type"] for x in sent], ["feed", "delta"],
                             "the push found the base held: what it adds rides as a delta, not a second full frame")
            d = json.loads(sent[1])
            self.assertEqual(d["slot"], "feed")
            self.assertIn("ledgers", d.get("rest") or {}, "the ledgers attach is the change that rode it")
            # a second `ready` is a re-base on this protocol too: the base is forgotten, the keyed full re-served
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual([json.loads(x)["type"] for x in sent], ["feed", "delta", "feed"])
            self.assertIn("_keys", json.loads(sent[2]))
        finally:
            _restore(saved)

    def test_an_outline_socket_announcing_delta_gets_one_full_frame_per_ready(self):
        # end to end over a real socket, with the REAL connect push (its ledgers attach changes the frame's
        # remainder, so what follows the full frame is a delta, never a second `feed`)
        f = _feed(n=40)
        saved, ms, parts = _warm(f)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = None
        try:
            s, buf = _connect(port, "app=fleet&wid=w9&caps=readyGate&delta=1")
            client = _registered("w9")
            self.assertTrue(client.get("delta"), "the shim's ?delta=1 was parsed")
            self.assertFalse(client["ready"])
            s.sendall(_client_frame(json.dumps({"type": "ready"})))
            frames = []
            s.settimeout(1.5)
            try:
                while True:
                    op, payload, buf = _read_frame(s, buf)
                    if op == 0x1:
                        frames.append(json.loads(payload.decode("utf-8")))
            except (socket.timeout, TimeoutError):
                pass
            frames = [fr for fr in frames if fr.get("type") != "caps"]   # the ready handler's caps frame: not a feed frame (test_tag_edit_ack.py pins it)
            types = [fr.get("type") for fr in frames]
            self.assertEqual(types.count("feed"), 1, "exactly one full frame per `ready`: %s" % types)
            self.assertIn("_keys", frames[types.index("feed")], "…the keyed one, the slot's base")
            self.assertTrue(set(types) <= {"feed", "delta"}, types)
            for fr in frames:
                if fr.get("type") == "delta":
                    self.assertEqual(fr.get("slot"), "feed")
        finally:
            if s is not None:
                s.close()
            srv.shutdown(); srv.server_close()
            _restore(saved)

    def test_the_ready_handler_emits_no_tab_order_of_its_own(self):
        # The connect push's tabOrder goes through the _tab_list_tmux collapse guard; the handler used to
        # send a SECOND one from a raw _tmux_sessions() read — an omitted id is an authoritative teardown
        # on the client (tabs, drafts) — and the shim now re-sends `ready` on a reconnect.
        h = self._handler()
        c, sent = _client(caps=(), app="chat")
        h._dispatch_ws({"type": "ready"}, c)
        self.assertEqual(h.pushed, [c], "the guarded push is the only tab-order source")
        self.assertEqual([json.loads(x).get("type") for x in sent], [], "no frame from the handler itself")
        i = KSRC.index('if msg and msg.get("type") == "ready":')
        handler = KSRC[i:KSRC.index("_consume_pending_reveal(client)", i)]
        self.assertNotIn('"tabOrder"', handler)
        self.assertNotIn("_ordered_alive(", handler)
        self.assertIn('served = client.get("app") in ("feed", "fleet", "waiting") and _send_feed_now(client)', handler)

    def test_a_second_ready_on_a_ready_client_re_serves_the_frame(self):
        # A `ready` on a client that is ALREADY ready is a re-base request, needFullFeed's twin. The 2026-09-03
        # review: a redial that completed before the bundle had loaded said `ready` for it, the frame went to a
        # page with no listener, and the bundle's own `ready` was then deduped against it (same signature, under
        # 60 s) — blank pane until the board changed. The shim no longer re-sends before the bundle's own; the
        # kernel no longer trusts the dedup slot across a second `ready` either.
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            h = self._handler()
            c, sent = _client(caps=("feedDelta", "readyGate"))
            c["ready"] = False                                    # held at accept
            t0 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(len(sent), 1)
            _served_fresh(self, sent[0], f, t0)
            t1 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(len(sent), 2, "the second `ready` re-serves the frame instead of deduping it")
            _served_fresh(self, sent[1], f, t1)
            self.assertIs(c["efeed"], parts, "…and the delta stream re-bases on what was served")
            self.assertEqual(h.pushed, [], "a served feed client skips the connect push both times")
            # a client that never announced the hold is READY FROM ACCEPT (the accept path's own
            # assignment, mirrored here) — the VS Code pipes, the Outline's among them. Its one ordinary `ready`
            # is the handshake, not a re-base: the frame the pusher already delivered is NOT re-served
            # (round 4 of the 2026-09-03 review caught the first cut re-basing on it, one redundant full
            # frame per connect). Only a SECOND `ready` on the same socket re-bases.
            c2, sent2 = _client(caps=())
            c2["ready"] = km.READY_GATE_CAP not in c2["caps"]
            self.assertIs(c2["ready"], True)
            km._send_feed(c2, f, ms, km._dedup_sig(f, ms), parts)   # the pusher's cycle landed first
            self.assertEqual(len(sent2), 1)
            h._dispatch_ws({"type": "ready"}, c2)
            self.assertEqual(len(sent2), 1, "the first `ready` of a never-announcing socket re-serves nothing")
            self.assertIs(c2["readySeen"], True)
            h._dispatch_ws({"type": "ready"}, c2)
            self.assertEqual(len(sent2), 2, "…its second `ready` is the re-base")
            i = KSRC.index('if msg and msg.get("type") == "ready":')
            handler = KSRC[i:KSRC.index("_consume_pending_reveal(client)", i)]
            self.assertLess(handler.index('if client.get("readySeen"):'), handler.index('client["ready"] = True'),
                            "the re-base is decided from the flag BEFORE the handler sets it")
        finally:
            _restore(saved)

    def test_the_ws_handler_pushes_nothing_at_accept_and_parses_caps(self):
        i = KSRC.index("    def _ws(self):")
        accept = KSRC[i:KSRC.index('while client["alive"]:', i)]
        self.assertNotIn("_send_feed_now(", accept, "the first frame waits for `ready`")
        self.assertIn("Nothing is pushed at accept", accept)
        self.assertIn('caps = (q.get("caps") or [""])[0]', accept)
        self.assertIn('client["caps"] = set(x for x in caps.split(",") if x)', accept)
        self.assertIn('client["ready"] = READY_GATE_CAP not in client["caps"]', accept, "the hold is decided at accept")
        self.assertIn('if msg and msg.get("type") == "needFullFeed":', KSRC)
        i = KSRC.index('if msg and msg.get("type") == "ready":')
        handler = KSRC[i:KSRC.index("_consume_pending_reveal(client)", i)]
        self.assertLess(handler.index('client["ready"] = True'), handler.index("_send_feed_now(client)"),
                        "the hold lifts BEFORE the frame is served")


class ConnectTimeFrame(unittest.TestCase):
    def test_a_fresh_socket_is_served_the_cached_frame_at_once(self):
        f = _feed()
        saved, ms, parts = _warm(f)
        try:
            c, sent = _client()
            t0 = time.time()
            self.assertTrue(km._send_feed_now(c))
            self.assertEqual(len(sent), 1)
            _served_fresh(self, sent[0], f, t0)   # the cached frame — no build, no wait
            self.assertIs(c["efeed"], parts, "…and it is the delta stream's base")
            # the pusher's next cycle then has nothing to add
            km._send_feed(c, f, ms, km._dedup_sig(f, ms), parts)
            self.assertEqual(len(sent), 1)
        finally:
            _restore(saved)

    def test_the_served_frame_carries_the_clock_of_the_serve_not_of_the_build(self):
        # The pusher builds only while a client is connected, so after a client-less stretch the cached
        # build's `now` is that stretch old — and the pane anchors every age and tint on the `now` it is
        # handed (feed-age.ts liveNow), with nothing to correct it on a board that then stays unchanged
        # (the 2026-09-03 review: a card last touched 11 h ago read "1h ago" all morning). The fixture's
        # build clock is 2026-06 (NOW); the serve is today.
        f = _feed(n=5)
        saved, ms, parts = _warm(f)
        try:
            c, sent = _client()
            t0 = time.time()
            self.assertTrue(km._send_feed_now(c))
            got = json.loads(sent[0])
            self.assertGreater(got["now"] - f["now"], 3600, "built at T, served much later: the frame says so")
            self.assertAlmostEqual(got["now"], t0, delta=2)
            card_t = got["asks"][3]["t"]                       # what the pane computes for the card's age…
            self.assertAlmostEqual(got["now"] - card_t, time.time() - card_t, delta=2,
                                   msg="…is the card's TRUE age, not its age as of the build")
            # the stamp is a splice, not a re-serialization: the cached body is `now`-less and reused
            body = km._feed_wire[3]
            self.assertNotIn('"now"', body)
            self.assertEqual(km._feed_ms(body, 7), '{"now": 7, ' + body[1:])
            self.assertEqual(json.loads(km._feed_ms(body, 7))["now"], 7)
            self.assertEqual(km._feed_ms("{}", 7), '{"now": 7}')
            # the dedup never compared `now`, so the stamp changes no dedup outcome: the same frame again
            # is swallowed whatever the clock says
            self.assertFalse(km._send_feed_now(c))
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
            km._feed_wire = (old, old.get("ledgers"), old, km._feed_body(old), sig, parts)
            km._built_feed[:] = [None, new, 0.0, 0.0]
            c, sent = _client()
            self.assertTrue(km._send_feed_now(c))
            self.assertEqual(json.loads(sent[-1])["buildId"], 2)
            self.assertIs(km._feed_wire[0], new, "…and cached for the next socket")
        finally:
            _restore(saved)


class ShimAnnouncesForTheFeedPage(unittest.TestCase):
    def test_every_feed_consumer_page_announces_the_delta_capability_and_every_pane_announces_the_hold(self):
        feed = km._shim("feed", 5, caps=km.FEED_DELTA_CAP + "," + km.READY_GATE_CAP)
        self.assertIn('var CAPS="feedDelta,readyGate";', feed)
        self.assertIn('+(CAPS?"&caps="+encodeURIComponent(CAPS):"")', feed)
        self.assertIn('var CAPS="readyGate";', km._shim("chat", 5, caps=km.READY_GATE_CAP))
        self.assertIn('var CAPS="";', km._shim("chat", 5), "the default announces nothing")
        # every kernel-served pane page opens its socket from the shim, before its bundle has loaded
        self.assertIn('_shim("feed", v, caps=FEED_DELTA_CAP + "," + READY_GATE_CAP)', KSRC)
        # the Waiting on you pane (2026-09-03) rides the feed frame with the feed page's caps: deltas + the hold
        self.assertIn('_shim("waiting", v, caps=FEED_DELTA_CAP + "," + READY_GATE_CAP)', KSRC)
        # the Outline pane (2026-09-05) too: on full frames alone, one browser's Outline client fell 12.7 MB
        # behind and was dropped seven times in a morning, each frame a multi-megabyte serialization on the
        # kernel's GIL. Its page loads federation.js before fleet.js; federation applies the deltas and
        # re-emits whole `feed` frames, so fleet.ts is unchanged (OutlineDeltaStream pins the wire).
        self.assertIn('_shim("fleet", v, caps=FEED_DELTA_CAP + "," + READY_GATE_CAP)', KSRC)
        self.assertNotIn('_shim("fleet", v, caps=READY_GATE_CAP)', KSRC)
        for app in ("chat", "timeline"):
            self.assertIn('_shim("%s", v, caps=READY_GATE_CAP)' % app, KSRC, app)
        # the Files pane (2026-09-03) is request/response, never a feed consumer: no deltas — the hold, plus
        # the stale opt-out (NO_STALE_CAP: no pushed view ever resyncs it, so its arm could only ever raise)
        self.assertIn('_shim("files", v, caps=READY_GATE_CAP + "," + NO_STALE_CAP)', KSRC)
        self.assertEqual(KSRC.count("_shim("), 7, "the definition and the six panes — a seventh caller must announce too")


class OutlineDeltaStream(unittest.TestCase):
    """The Outline page (app=fleet) announces FEED_DELTA_CAP (2026-09-05). It rode full frames until then: one
    browser's Outline client fell 12.7 MB behind and the kernel dropped it seven times in a morning (ws drop,
    slot=feed, 6.3 MB frames), every frame a multi-megabyte json.dumps on the kernel's GIL. The page loads
    federation.js before fleet.js, and federation applies each delta onto the full frame it holds and re-emits
    a whole `feed` frame, which is all fleet.ts reads (what fleet.ts gained is a live clock and the unapplied-
    delta guard: ui/webview/fleet-live-clock.test.ts). Pinned on a real socket: after its first full frame,
    an Outline client with the capability hears the board's changes as {type:"feedDelta"} — the changed card
    by itemId, tint-less — and never another full frame."""

    def test_an_outline_client_with_the_capability_streams_deltas_after_its_first_full_frame(self):
        f = _feed(n=40)
        saved, ms, parts = _warm(f)
        real_build = km.build_feed
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = None
        try:
            s, buf = _connect(port, "app=fleet&wid=w9&caps=feedDelta,readyGate")
            client = _registered("w9")
            self.assertEqual(client["app"], "fleet")
            self.assertIn(km.FEED_DELTA_CAP, client["caps"])
            self.assertFalse(client["ready"], "held until its bundle says so, like every pane")
            s.sendall(_client_frame(json.dumps({"type": "ready"})))
            op, payload, buf = _read_frame(s, buf)
            self.assertEqual(op, 0x1)
            first = json.loads(payload.decode("utf-8"))
            self.assertEqual(first["type"], "feed", "the first frame is full: the delta stream's base")
            self.assertEqual([a["itemId"] for a in first["asks"]], [a["itemId"] for a in f["asks"]])
            # The ready handler runs the Outline's connect push inline (the pane needs the session build's
            # ledgers, so unlike the feed pane it is not skipped), and the build below must not race that push
            # on the client's recorded delta base. The barrier: the reader thread answers a ping only after it
            # has dispatched every message read before it, so the pong means the handler is done. It says
            # nothing about the wire — the reader writes the pong itself while data frames go through the
            # client's sender thread — so whatever the connect push sent (a ledger reconciliation, or nothing)
            # may land on either side of the pong; the two drains take it in either position, and it must be
            # a delta too.
            s.sendall(_ping_frame(b"sync"))
            frames = []
            while True:
                op, payload, buf = _read_frame(s, buf)
                if op == 0xA:
                    self.assertEqual(payload, b"sync")
                    break
                frames.append(json.loads(payload.decode("utf-8")))
            # The board changes: the pusher's next BUILD renames one card. The kernel's own build path runs
            # (_cached_feed → build_feed, cold so it builds whatever the clock says) with the fixture as the
            # build's result. The first cut warmed the fixture instead and leaned on REBUILD_MIN_S for the
            # pusher to serve it: a 2 s window that the tmux probe and Sessions.live() between the warm and
            # the serve can exceed under load, after which the kernel built an empty board from the hermetic
            # state and the drain below timed out (the 2026-09-05 review).
            f2 = _feed(n=40, build_id=2, now=NOW + 10)
            f2["asks"][3]["text"] = "Synthetic goal 3 on the notes-api board, renamed"
            km.build_feed = lambda now, tmux: f2
            km._built_feed[:] = [None, None, 0.0, 0.0]            # cold: the next _cached_feed builds, whatever the clock
            km._push_all()                                         # the real pusher cycle
            s.settimeout(5)                                        # the drain's bound: the renamed card's delta, or fail
            try:
                while True:                                        # anything ahead of it is the connect push's late frame
                    op, payload, buf = _read_frame(s, buf)
                    self.assertEqual(op, 0x1)
                    d = json.loads(payload.decode("utf-8"))
                    frames.append(d)
                    if any("renamed" in (a.get("text") or "") for a in d.get("asks") or []):
                        break
            except (socket.timeout, TimeoutError):
                self.fail("no delta carrying the renamed card within 5 s; frames seen: %r"
                          % [(x.get("type"), x.get("buildId")) for x in frames])
            frames = [x for x in frames if x.get("type") != "caps"]   # the ready handler's caps frame is not a feed frame (test_tag_edit_ack.py pins it)
            self.assertEqual([d["type"] for d in frames], ["feedDelta"] * len(frames), "never another full frame")
            self.assertEqual(d["buildId"], f2["buildId"], "the build the pusher ran (the kernel mints its id at build start)")
            self.assertEqual([a["itemId"] for a in d["asks"]], ["%s:g3" % SID], "the one card that changed, by itemId")
            self.assertNotIn("trgb", d["asks"][0], "deltas never carry the tint")
            self.assertNotIn("removeAsks", d)
            self.assertLess(len(payload), len(ms) // 10, "a one-card change is a small fraction of the full frame")
        finally:
            if s is not None:
                s.close()
            srv.shutdown(); srv.server_close()
            km.build_feed = real_build
            _restore(saved)


def _connect(port, query):
    """A real browser-style client socket to the kernel's /ws?`query`; returns (socket, leftover bytes)."""
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws?%s&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nOrigin: http://127.0.0.1:%d\r\n"
           "Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n") % (query, km.TOKEN, port, port, key)
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            raise RuntimeError("closed during the handshake")
        buf += chunk
    head, buf = buf.split(b"\r\n\r\n", 1)
    if not head.startswith(b"HTTP/1.1 101"):
        raise RuntimeError(head[:80])
    return s, buf


def _registered(wid, deadline_s=5):
    """The kernel's client dict for the socket that connected with `wid` (it registers AFTER the handshake)."""
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        with km._clients_lock:
            client = next((c for c in km._clients if c.get("wid") == wid), None)
        if client is not None:
            return client
        time.sleep(0.005)
    raise AssertionError("the socket %s was not registered" % wid)


class ReadyGate(unittest.TestCase):
    """A page that announced READY_GATE_CAP is HELD: `ready` False at accept, and every push path skips it —
    the pusher's _push, the app/view broadcasts, a reveal — until the bundle's `ready` flips it. The
    2026-09-03 review found the first frame still lost after the accept-time push was removed: the pusher's
    next 0.5 s cycle sent the full frame to a socket whose page had not run feed.js yet, and the frame the
    bundle's `ready` then asked for was deduped against it, with no repost on the delta path."""

    def _handler(self):
        class _FakeHandler:
            _dispatch_ws = km.Handler._dispatch_ws
            def __init__(self):
                self.pushed = []
            def _push_one(self, client):
                self.pushed.append(client)
        return _FakeHandler()

    def test_every_push_path_skips_a_held_client_and_ready_serves_it(self):
        f = _feed()
        saved, ms, parts = _warm(f)
        c, sent = _client(caps=("feedDelta", "readyGate"))
        c["ready"] = False                                        # what accept records for the announcing page
        with km._clients_lock:
            km._clients.append(c)
        try:
            km._push([c])                                         # the pusher's cycle, through the real _push
            km._send_to_app("feed", {"type": "syncNotice"})
            km._send_to_view("feed", {"type": "syncNotice"}, "w1")
            self.assertEqual(sent, [], "nobody is listening on that page yet")
            self.assertNotIn("efeed", c); self.assertNotIn("sent", c)
            h = self._handler()
            t0 = time.time()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertTrue(c["ready"])
            self.assertEqual(len(sent), 1)
            _served_fresh(self, sent[0], f, t0)
            self.assertIs(c["efeed"], parts)
            km._send_to_app("feed", {"type": "syncNotice"})
            self.assertEqual(json.loads(sent[-1])["type"], "syncNotice", "…and the broadcasts reach it now")
            km._push([c])
            self.assertEqual(len(sent), 2, "the pusher's next cycle adds nothing: the served frame is its base")
        finally:
            with km._clients_lock:
                km._clients[:] = [x for x in km._clients if x is not c]
            _restore(saved)

    def test_a_reveal_aimed_at_a_held_chat_pane_parks_and_lands_at_its_ready(self):
        # a targeted send to a page that is not listening is lost the same way; the reveal already had a
        # parking slot for "its chat pane has not connected yet", and a held pane is exactly "not yet"
        saved = km._PENDING_REVEAL[0]
        c, sent = _client(caps=("readyGate",), app="chat")
        c["wid"] = "w5"; c["ready"] = False
        with km._clients_lock:
            km._clients.append(c)
        try:
            km._PENDING_REVEAL[0] = None
            self.assertFalse(km._reveal_request(SID, "w5"), "not delivered to a page with no listener…")
            self.assertEqual(sent, [])
            self.assertEqual(km._PENDING_REVEAL[0], {"sid": SID, "wid": "w5"}, "…parked")
            h = self._handler()
            h._dispatch_ws({"type": "ready"}, c)
            self.assertEqual(h.pushed, [c], "a chat pane gets its connect push")
            self.assertEqual([json.loads(x)["id"] for x in sent], [SID], "the parked reveal lands after it")
            self.assertIsNone(km._PENDING_REVEAL[0])
            c2, sent2 = _client(caps=(), app="chat"); c2["wid"] = "w6"
            with km._clients_lock:
                km._clients.append(c2)
            try:
                self.assertTrue(km._reveal_request(SID, "w6"), "a ready pane is delivered to at once, as before")
                self.assertEqual(len(sent2), 1)
            finally:
                with km._clients_lock:
                    km._clients[:] = [x for x in km._clients if x is not c2]
        finally:
            with km._clients_lock:
                km._clients[:] = [x for x in km._clients if x is not c]
            km._PENDING_REVEAL[0] = saved

    def test_the_ask_poll_and_the_parked_create_retry_skip_a_held_chat_pane(self):
        # The two pusher-side paths that reach chat clients outside _push — the live-ask poll and the
        # lag-parked comment creates — carry the same gate; the 2026-09-03 review found it unpinned on both
        # (and on _push_session_now: test_kernel_opening.py). A held pane gets nothing; a ready one gets it.
        held, sent_h = _client(caps=("readyGate",), app="chat"); held["ready"] = False; held["wid"] = "w8"
        live, sent_l = _client(caps=(), app="chat"); live["wid"] = "w9"
        class _Stub:
            def current_ask(self, sid):
                return {"kind": "single", "header": "Backend", "question": "Which backend?", "options": [{"label": "tmux"}]}
        saved = (km.Sessions.live, km.Sessions.backend_for, km._comment_create, km._comments_frame, list(km._parked_creates))
        with km._clients_lock:
            km._clients.extend([held, live])
        try:
            km.Sessions.live = lambda: [SID]
            km.Sessions.backend_for = lambda sid: _Stub()
            km._ask_poll_once()
            self.assertEqual(sent_h, [], "the live ask never reaches a page whose bundle is not listening")
            self.assertEqual([json.loads(x)["type"] for x in sent_l], ["askLive"], "…and reaches the one that is")
            km._parked_creates[:] = [{"sid": SID, "uuid": "11111111-2222-3333-4444-777777777777", "exact": "the cap", "text": "Why?",
                                      "name": "", "model": "", "effort": "", "fast": "", "color": "", "tries": 0}]
            km._comment_create = lambda *a, **k: (None, "t1")
            km._comments_frame = lambda sid, tmux=None: {"type": "comments", "id": sid, "threads": []}
            km._retry_parked_creates()
            self.assertEqual(km._parked_creates, [], "the create landed")
            self.assertEqual(sent_h, [], "nor does its ack")
            self.assertEqual([json.loads(x)["type"] for x in sent_l][1:], ["comments", "commentCreated"])
            held["ready"] = True                                  # the bundle's `ready`: the next tick lands
            km._ask_poll_once()
            self.assertEqual([json.loads(x)["type"] for x in sent_h], ["askLive"])
        finally:
            with km._clients_lock:
                km._clients[:] = [x for x in km._clients if x is not held and x is not live]
            km.Sessions.live, km.Sessions.backend_for, km._comment_create, km._comments_frame = saved[:4]
            km._parked_creates[:] = saved[4]

    def test_a_client_that_never_announced_is_ready_from_accept(self):
        # federation's remote relays (federation.ts routes `ready` to the local kernel only), the VS Code
        # extension's pipes, an older dashboard: none race the bundle, none send `ready` on this socket
        for c in ({"app": "feed", "alive": True, "wid": "", "qbytes": 0, "caps": set()},
                  {"app": "feed", "alive": True, "wid": "", "qbytes": 0, "caps": {"feedDelta"}, "ready": True},
                  {"app": "chat", "alive": True, "wid": "w1", "qbytes": 0}):
            self.assertTrue(km._client_ready(c), c)
        self.assertFalse(km._client_ready({"app": "feed", "ready": False, "caps": {"readyGate"}}))
        # the keepalive and the restart notice never ask: the shim consumes both without the bundle
        src = KSRC[KSRC.index("def _keepalive_all("):KSRC.index("def _heartbeat(")]
        self.assertNotIn("_client_ready", src)
        src = KSRC[KSRC.index("def _broadcast_restarting("):KSRC.index("def _push_all(")]
        self.assertNotIn("_client_ready", src)


class FeedStateUnderTheSlotLock(unittest.TestCase):
    """The feed's per-client state (efeed, the ("feed",) dedup slot, the slot's dstate) is read and written
    on two threads: the pusher's _send_feed / the handler's _send_feed_now, and the handler's needFullFeed /
    `ready` re-base pops. Like _send_slot and _send_chat, the read-decide-send-write runs under the client's
    slot lock, and the pops go through _client_reset_feed_base under the same lock — so a reset lands before
    or after a send as a whole, never inside it."""

    def test_the_send_paths_and_the_resets_share_the_clients_slot_lock(self):
        import inspect
        send = inspect.getsource(km._send_feed)
        self.assertIn("with _client_lock(c):", send)
        self.assertIn("return _send_feed_locked(c, feed, ms, sig, parts)", send)
        now = inspect.getsource(km._send_feed_now)
        i = now.index("with _client_lock(c):")
        self.assertLess(i, now.index('c["efeed"] = w[5]'), "the base is recorded inside the lock")
        self.assertLess(i, now.index('_send_slot(c, "feed", w[2], ms, w[4])'))
        self.assertLess(i, now.index('_send_client(c, ("feed",), w[2], pre=ms, sig=w[4])'))
        reset = inspect.getsource(km._client_reset_feed_base)
        self.assertLess(reset.index("with _client_lock(client):"), reset.index('client.pop("efeed", None)'))
        self.assertIn('client.get("dstate", {}).pop("feed", None)', reset, "the view-delta slot's base goes too")
        handler = KSRC[KSRC.index('msg.get("type") == "needFullFeed"'):KSRC.index('msg.get("type") == "loadOlder"')]
        self.assertIn("_client_reset_feed_base(client)", handler)
        self.assertNotIn('client.pop("efeed"', handler, "no unlocked pop on the handler thread")
        i = KSRC.index('if msg and msg.get("type") == "ready":')
        ready = KSRC[i:KSRC.index("_consume_pending_reveal(client)", i)]
        self.assertIn("_client_reset_feed_base(client)", ready)
        self.assertNotIn('client.pop("efeed"', ready)

    def test_a_reset_that_arrives_mid_send_lands_after_it_so_the_next_frame_is_full(self):
        # A hook inside the delta computation holds the send open while a second thread resets the client.
        # Unlocked, the reset landed between the read and the write-back, the write-back put efeed back, and
        # the client that had just declared it holds nothing got a delta next. Locked, the reset waits.
        f1 = _feed(n=30, build_id=1)
        cards = [_card(i) for i in range(30)]; cards[3]["text"] = "Synthetic goal 3, edited"
        f2 = _feed(n=30, build_id=2, asks=cards)
        c, sent = _client()
        c["dlock"] = threading.RLock()
        _send(c, f1)
        self.assertEqual(json.loads(sent[-1])["type"], "feed")
        entered, reset_done = threading.Event(), threading.Event()
        real = km._feed_delta
        def hooked(prev, cur, feed):
            entered.set()
            reset_done.wait(0.5)      # cannot complete while this thread holds the lock: times out
            return real(prev, cur, feed)
        km._feed_delta = hooked
        try:
            def resetter():
                entered.wait(5)
                km._client_reset_feed_base(c)
                reset_done.set()
            t = threading.Thread(target=resetter); t.start()
            _send(c, f2)
            t.join(5)
        finally:
            km._feed_delta = real
        self.assertTrue(reset_done.is_set())
        self.assertEqual(json.loads(sent[-1])["type"], "feedDelta", "the in-flight send finished as a whole")
        self.assertNotIn("efeed", c, "…and the reset landed after it, not under its write-back")
        _send(c, f2)
        self.assertEqual(json.loads(sent[-1])["type"], "feed", "a client that holds nothing gets the full frame")


class StripTrgbIsExact(unittest.TestCase):
    """`_strip_trgb` removes the tint and NOTHING else (the 2026-09-03 review: a strip that also dropped
    `summary` passed every test — a summary-only change then rode no delta and busted no dedup)."""

    def test_the_strip_removes_only_trgb_at_the_top_and_in_every_tree_node(self):
        card = _card(9)
        before = json.dumps(card, sort_keys=True)
        out = km._strip_trgb(card)
        self.assertEqual(json.dumps(card, sort_keys=True), before, "the input is not mutated")
        exp = dict(card); del exp["trgb"]
        exp["tree"] = [{k: v for k, v in n.items() if k != "trgb"} for n in card["tree"]]
        self.assertEqual(out, exp)
        self.assertEqual(sorted(out), sorted(k for k in card if k != "trgb"))
        for n, m in zip(out["tree"], card["tree"]):
            self.assertEqual(sorted(n), sorted(k for k in m if k != "trgb"))
        self.assertIs(km._strip_trgb("not a card"), "not a card")

    def test_every_other_field_moves_the_signature_and_the_parts(self):
        base = _feed(n=3)
        sig0 = km._dedup_sig(base, json.dumps(base))
        cards0, leds0, _rest0, rest_ms0 = km._feed_parts(base)
        def moved(f, what):
            self.assertNotEqual(km._dedup_sig(f, json.dumps(f)), sig0, what)
            return km._feed_parts(f)
        for k in _card(1):                                           # every top-level card field
            if k == "trgb":
                continue
            f = _feed(n=3); f["asks"][1][k] = [] if k == "tree" else "changed"
            self.assertNotEqual(moved(f, k)[0], cards0, "card field %r" % k)
        for k in _card(1)["tree"][0]:                                # every tree-node field
            if k == "trgb":
                continue
            f = _feed(n=3); f["asks"][1]["tree"][2][k] = [{"id": "x"}] if k == "children" else "changed"
            self.assertNotEqual(moved(f, k)[0], cards0, "node field %r" % k)
        for k in base:                                               # every top-level frame field
            if k in ("type", "asks", "ledgers") or k in km._DEDUP_VOLATILE:
                continue
            f = _feed(n=3); f[k] = "changed"
            self.assertNotEqual(moved(f, k)[3], rest_ms0, "frame field %r" % k)
        f = _feed(n=3); f["ledgers"][0]["status"] = {"state": "waiting"}
        self.assertNotEqual(moved(f, "ledgers")[1], leds0)
        # …and the tint alone, at the top or in a node, moves neither
        f = _feed(n=3); f["asks"][1]["trgb"] = [0, 0, 0]; f["asks"][1]["tree"][2]["trgb"] = [0, 0, 0]
        self.assertEqual(km._dedup_sig(f, json.dumps(f)), sig0)
        self.assertEqual(km._feed_parts(f)[0], cards0)


if __name__ == "__main__":
    unittest.main()
