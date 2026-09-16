#!/usr/bin/env python3
"""Cards first on a cold kernel (2026-09-12): the first push after a boot sends the feed frame to the feed panes before
it builds the chat pages and the timeline; a warm kernel takes no extra step. Hermetic: a temp state root, stubbed
builders, fake clients; no kernel, no sessions."""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from romp_load import load_source   # noqa: E402
_tmp_state = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _tmp_state
os.environ["ROMP_STATE_DIR"] = os.path.join(_tmp_state, "romp")

BIN = os.path.join(os.path.dirname(HERE), "bin")
km = load_source("romp_kernel_feed_first", os.path.join(BIN, "romp-kernel"))

S1 = "77777777-1111-2222-3333-444444444401"
S2 = "77777777-1111-2222-3333-444444444402"
FEED = {"type": "feed", "asks": [{"itemId": "g1", "sid": S1, "title": "a card"}], "working": ["web"], "awaiting": []}


def _sess(sid, state):
    """A synthetic build_session payload in the shape the push's chat send expects (the skeleton test's stub)."""
    return {"type": "session", "id": sid, "name": "web" if sid == S1 else "api",
            "events": [{"kind": "assistant", "uuid": "u%d" % i, "md": "m%d" % i} for i in range(3)],
            "status": {"state": state, "sinceEpoch": None}, "ledger": None}


class FeedFirstColdPush(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.paths = {}
        for sid in (S1, S2):
            p = os.path.join(self.tmp, sid + ".jsonl"); open(p, "w").write("x" * 10); self.paths[sid] = p
        self._saved = (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session, km._comments_frame,
                       km._push_subagents, km.NAMES, km.jd.STATE, list(km._clients), list(km._built_feed), km._feed_wire,
                       dict(km._wire_stats))
        km._chat_tab_sessions = lambda now, live_map: [{"sid": s, "name": _sess(s, "working")["name"], "path": self.paths[s], "anchor": s} for s in (S1, S2)]
        km._live_map = lambda: {}
        self.seq = []                                        # every frame every client receives, in send order
        self.feed_calls = []
        def cached_feed(now, live_map, sig, connect=False):
            self.feed_calls.append(connect)
            return json.loads(json.dumps(FEED))
        km._cached_feed = cached_feed
        def build(sid, now, live_map=None, **kw):
            self.seq.append(("build", sid))
            return json.loads(json.dumps(_sess(sid, "working")))
        km.build_session = build
        km._comments_frame = lambda sid, live_map: None
        km._push_subagents = lambda clients, now, live_map: None
        km.NAMES = Path(self.tmp) / "names"; km.NAMES.mkdir()
        km.jd.STATE = Path(self.tmp) / "state"; km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._built_chat.clear(); del km._clients[:]
        km._built_feed[:] = [None, None, 0.0, 0.0]
        km._feed_wire = None
        self._marks, self._cycles = dict(km._BOOT_MARKS), km._PERF_STATS.pusher.get("cycles", 0)
        km._BOOT_MARKS["firstServe"] = 1.0                   # a kernel that is serving, in its first pusher cycle
        with km._PERF_STATS.lock:
            km._PERF_STATS.pusher["cycles"] = 0
        for k in km._wire_stats:
            km._wire_stats[k] = 0

    def tearDown(self):
        (km._chat_tab_sessions, km._live_map, km._cached_feed, km.build_session, km._comments_frame, km._push_subagents,
         km.NAMES, km.jd.STATE, clients, built_feed, km._feed_wire, stats) = self._saved
        del km._clients[:]; km._clients.extend(clients)
        km._built_feed[:] = built_feed
        km._wire_stats.update(stats)
        km._built_chat.clear()
        km._BOOT_MARKS.clear(); km._BOOT_MARKS.update(self._marks)
        with km._PERF_STATS.lock:
            km._PERF_STATS.pusher["cycles"] = self._cycles

    def _client(self, app):
        c = {"app": app, "alive": True, "sent": {}}
        c["send"] = lambda s, c=c: self.seq.append((c["app"], json.loads(s).get("type")))
        return c

    def test_a_cold_kernels_first_push_sends_the_feed_before_any_chat_build(self):
        feed_c, chat_c = self._client("feed"), self._client("chat")
        km._push([feed_c, chat_c])
        kinds = [(a, t) for a, t in self.seq]
        first_feed = kinds.index(("feed", "feed"))
        first_build = kinds.index(("build", S1)) if ("build", S1) in kinds else kinds.index(("build", S2))
        self.assertLess(first_feed, first_build, "the feed frame leaves before the first chat page is built: %r" % kinds)
        self.assertEqual(km._wire_stats["feed_first"], 1)
        self.assertEqual(self.feed_calls[0], False, "the early build is the cycle's own, not a connect serve")

    def test_a_connect_push_during_the_first_cycle_builds_the_feed_too(self):
        # the realistic boot: the browser reconnects a moment after the kernel serves, so the first push with a feed pane is the
        # connect push; the connect arm of the cache serves only a warmed build, which a cold kernel has not got
        feed_c = self._client("feed")
        km._push([feed_c], connect=True)
        self.assertEqual(km._wire_stats["feed_first"], 1, "the early pass ran on the connect push")
        self.assertEqual(self.feed_calls[0], False, "and it BUILT (connect False to the cache), rather than serving a warmed build it has not got")
        self.assertIn(("feed", "feed"), self.seq)

    def test_a_warm_kernel_takes_no_extra_step(self):
        feed_c, chat_c = self._client("feed"), self._client("chat")
        km._built_feed[1] = json.loads(json.dumps(FEED))          # a feed already built since start
        with km._PERF_STATS.lock:
            km._PERF_STATS.pusher["cycles"] = 3                    # and later cycles: the built feed alone stands the pass down
        km._push([feed_c, chat_c])
        self.assertEqual(km._wire_stats["feed_first"], 0, "no early pass on a warm kernel")
        self.assertIn(("feed", "feed"), self.seq, "the regular feed section still serves the pane: %r" % self.seq)

    def test_a_later_cycle_with_no_feed_built_yet_still_sends_the_feed_first(self):
        # Re-applied 2026-09-14 (step three): the pusher's first cycle runs before a browser has reconnected, so a guard on
        # cycle zero never held on a real boot; the cold state the shortcut is for is "no feed built yet", whatever the cycle
        # count. Its first cut was reverted the same day (a 131 s first refresh: six redialing panes each built the same cold
        # feed beside the pusher); builds are single-flight across threads now, so the connect pushes serve this build.
        with km._PERF_STATS.lock:
            km._PERF_STATS.pusher["cycles"] = 7
        km._push([self._client("feed"), self._client("chat")])
        self.assertEqual(km._wire_stats["feed_first"], 1, "a cold kernel sends the feed first on any cycle")
        kinds = list(self.seq)
        self.assertLess(kinds.index(("feed", "feed")), kinds.index(("build", S1)), "before the first chat build: %r" % kinds)

    def test_a_connect_push_on_a_later_cycle_of_a_cold_kernel_sends_the_feed_first(self):
        # the realistic boot: the browser reconnects a few seconds in, after the pusher's first cycles ran with no client
        with km._PERF_STATS.lock:
            km._PERF_STATS.pusher["cycles"] = 12
        km._push([self._client("feed")], connect=True)
        self.assertEqual(km._wire_stats["feed_first"], 1)
        self.assertEqual(self.feed_calls[0], False, "and it built, rather than serving a warmed build a cold kernel has not got")

    def test_no_feed_pane_means_no_early_pass(self):
        chat_c = self._client("chat")
        km._push([chat_c])
        self.assertEqual(km._wire_stats["feed_first"], 0)

    # This fork's feed pane takes the feed's own itemId deltas (FEED_DELTA_CAP; _send_feed / _feed_delta, no twin upstream), and
    # every reader of _feed_wire takes [3] as the body minus `now` and [5] as _feed_parts' FOUR parts. Upstream's _feed_first built
    # the tuple from _delta_parts (the view-delta slot's three-part split) with the whole frame as the body: the `ready` serve
    # recorded that split as a cap client's base, the pusher's next _feed_delta raised unpacking it, and a feed pane on a cold
    # kernel heard nothing after its first frame (the pull-in, 2026-09-15; tests/test_feed_focus_served.py is the served twin,
    # 13 tracebacks in its lab before the fix). The three cases below pin the early pass on the fork's path.

    def _delta_client(self):
        """A feed pane that announced FEED_DELTA_CAP: records every frame, decoded and raw."""
        c = {"app": "feed", "alive": True, "sent": {}, "caps": {km.FEED_DELTA_CAP}, "frames": [], "raw": []}
        def send(s, c=c):
            c["raw"].append(s); c["frames"].append(json.loads(s)); self.seq.append((c["app"], json.loads(s).get("type")))
        c["send"] = send
        return c

    def _wire(self, feed):
        """The pusher's wire forms for a build, as the send stage makes them (tests/test_feed_delta.py's _wire)."""
        parts = km._feed_parts(feed); sig = km._feed_sig(parts)
        body = km._LazyWire(lambda: km._feed_body(feed), km._feed_est(parts), "feed_body")
        return km._feed_ms_lazy(body, feed.get("now")), sig, parts

    def _renamed(self):
        feed2 = json.loads(json.dumps(FEED)); feed2["asks"][0]["title"] = "a renamed card"; feed2["buildId"] = 2
        return feed2

    def _one_build(self):
        """_cached_feed as the real one behaves while a build stands: the SAME object on every call, so _push's send stage
        finds the early pass's tuple in _feed_wire and reuses it. The setUp stub copies per call, which makes the send stage
        re-encode the tuple and hid what the early pass left in it (the three cases below passed on the broken shape with it)."""
        src = [json.loads(json.dumps(FEED))]
        km._cached_feed = lambda now, live_map, sig, connect=False: src[0]
        return src

    def test_the_early_frame_puts_a_delta_client_on_the_forks_feed_delta_path(self):
        self._one_build()
        c = self._delta_client()
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            km._push([c], connect=True)
        self.assertEqual(km._wire_stats["feed_first"], 1)
        self.assertNotIn("Traceback", err.getvalue(), err.getvalue())
        w = km._feed_wire
        self.assertEqual(len(w[5]), 4, "the fork's _feed_parts tuple: cards, ledgers, the rest, its json")
        self.assertEqual(set(w[5][0]), {"g1"}); self.assertIsNone(w[5][1], "no ledgers on the early frame")
        self.assertEqual(w[4], km._feed_sig(w[5]), "the signature is the parts' tuple")
        self.assertEqual([f["type"] for f in c["frames"]], ["feed"], "one full frame; the regular section's re-send dedups")
        self.assertEqual(c["raw"][0].count('"now"'), 1, "the body is kept minus `now`, so the clock is spliced in once")
        self.assertIs(c["efeed"], w[5], "the frame the client holds is the delta stream's base")
        ms, sig, parts = self._wire(self._renamed())            # the next send with a change is a delta, not a raise
        km._send_feed(c, self._renamed(), ms, sig, parts)
        self.assertEqual(c["frames"][-1]["type"], "feedDelta")
        self.assertEqual([a["itemId"] for a in c["frames"][-1]["asks"]], ["g1"])

    def test_a_ready_serve_after_the_early_pass_rebases_a_delta_client_on_the_parts(self):
        # the `ready` handshake of a pane that dialled during the cold push serves _feed_wire with no build (_send_feed_now)
        # and records [5] as the client's base: four parts, so the pane's first pusher frame after it is a delta
        self._one_build()
        km._push([self._client("feed")])                       # the early pass ran for a legacy pane; _feed_wire is the cold build's
        self.assertEqual(km._wire_stats["feed_first"], 1)
        c = self._delta_client()
        self.assertTrue(km._send_feed_now(c))
        self.assertIs(c["efeed"], km._feed_wire[5]); self.assertEqual(len(c["efeed"]), 4)
        self.assertEqual(c["frames"][-1]["type"], "feed")
        self.assertGreaterEqual(c["frames"][-1]["now"], int(time.time()) - 5, "stamped with the clock as of the serve")
        ms, sig, parts = self._wire(self._renamed())
        km._send_feed(c, self._renamed(), ms, sig, parts)
        self.assertEqual(c["frames"][-1]["type"], "feedDelta")
        self.assertEqual([a["itemId"] for a in c["frames"][-1]["asks"]], ["g1"])

    def test_the_pushers_next_cycle_sends_a_delta_client_a_delta_not_a_traceback(self):
        # the failure's shape in the lab: every pusher send to the pane after the early frame raised inside _feed_delta
        # (`not enough values to unpack (expected 4, got 3)`), caught per client and written to stderr, so the pane's frames
        # simply stopped. Here the build changes between two pushes and the second must reach the pane as a feedDelta.
        src = self._one_build()
        c = self._delta_client()
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            km._push([c], connect=True)
            src[0] = dict(FEED, asks=[dict(FEED["asks"][0], title="a renamed card"), {"itemId": "g2", "sid": S2, "title": "another"}])
            km._push([c])
        self.assertNotIn("Traceback", err.getvalue(), err.getvalue())
        self.assertEqual([f["type"] for f in c["frames"]], ["feed", "feedDelta"])
        self.assertEqual(sorted(a["itemId"] for a in c["frames"][-1]["asks"]), ["g1", "g2"])

    def test_the_early_pass_precedes_the_chat_section_in_the_source(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        push = src[src.index("def _push(targets, connect=False, live_map=None):"):]
        self.assertLess(push.index("_feed_first(now, live_map, targets, connect)"), push.index("chat_list = _chat_tab_sessions(now, live_map)"))


if __name__ == "__main__":
    unittest.main()
