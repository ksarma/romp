"""Timeline ships in TWO messages so the lanes paint before the heavy bars (the user 2026-06-25, who found startup
still slow and wanted everything else loaded with the bars loaded after).

build_timeline(with_bars=False) builds only the LANES SKELETON (sessions/status, no turns/judging/messages/
nudges); _push sends it as {type:"data"} FIRST, then the cached full build's detail rides a {type:"bars"}
message. Profiling drove this: the timeline was 551ms/1940KB and ~95% of that is bars+judging, so the
skeleton is tiny and lands immediately. (The dead `tokens` field — nothing reads it — was dropped too.)

Since 2026-09-06 the skeleton build runs only on the cold live-first connect. A warm push PROJECTS the
skeleton from the cached full build (_timeline_skeleton), serializes the frame once per cycle and dedups it
on the lanes minus the clock (_skeleton_sig) — see SkeletonFromCache below.
"""
import inspect
import json
import os
import time
import unittest
from importlib.machinery import SourceFileLoader
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()


class BuildGating(unittest.TestCase):
    def test_build_timeline_gates_the_heavy_fields_on_with_bars(self):
        src = inspect.getsource(km.build_timeline)
        self.assertIn("with_bars=True", src, "the skeleton/bars switch")
        self.assertIn("if not with_bars:", src, "skeleton skips the per-segment bar dicts")
        self.assertIn("if with_bars:", src, "turns[sid] + judging + messages are gated")
        self.assertNotIn('"tokens"', src, "the dead token field is GONE from the payload (2026-07-07 audit)")
        self.assertNotIn('"nudges"', src, "…and so is the never-rendered nudges array")

    def test_the_host_shim_routes_a_bars_message_to_applyBars(self):
        boot = km._TIMELINE_BOOT
        self.assertIn('m.type==="bars"', boot)
        self.assertIn("panel.applyBars(m)", boot)

    def test_the_host_shim_wraps_its_listener_through_the_page_collector_when_there_is_one(self):
        # The page's performance collector (ui/webview/perf-telemetry.ts) is published on window.__rompPerf by
        # federation.js, which the timeline page loads before this boot (test_browser_owned_order pins the
        # order). Wrapped, the frames the boot dispatches are timed by type like every pane's, so the view's
        # hover/activeChat/revealEvent/models handling is not left inside federation's fed:<type> bracket
        # (2026-09-06); without a collector the plain listener is registered.
        boot = km._TIMELINE_BOOT
        self.assertIn("var onFrame=function(ev){var m=ev.data;if(!m||!panel)return;", boot)
        self.assertIn('window.addEventListener("message",(window.__rompPerf&&window.__rompPerf.wrapFrameHandler)'
                      "?window.__rompPerf.wrapFrameHandler(onFrame):onFrame);", boot)
        self.assertEqual(boot.count('addEventListener("message"'), 1, "one listener, the wrapped one")

    def test_the_lanes_skeleton_does_not_parse_any_transcript(self):
        # cold-start speed (the user 2026-06-26): a fresh kernel (the refresh button = POST /restart) re-parses
        # every transcript (~1.3s). The lanes don't need it — derive them from tmux + goals + the transcript
        # mtime. Only the {type:"bars"} build (with_bars=True) does the real parse.
        calls = {"parse": 0}
        o_ts, o_parse = km._timeline_sessions, km._parse
        km._timeline_sessions = lambda now, tmux, live_only=False: [{"sid": "S", "name": "n", "path": "/no/such/transcript"}]
        km._parse = lambda path, sid, now: (calls.__setitem__("parse", calls["parse"] + 1), {"turns": []})[1]
        try:
            km.build_timeline(0, {}, with_bars=False)
            self.assertEqual(calls["parse"], 0, "the lanes skeleton must NOT parse a transcript")
            km.build_timeline(0, {}, with_bars=True)
            self.assertGreater(calls["parse"], 0, "the bars build DOES parse")
        finally:
            km._timeline_sessions, km._parse = o_ts, o_parse


class TimelinePageLoader(unittest.TestCase):
    """The timeline pane no longer carries the full-pane _pane_spin("host") overlay (the user 2026-06-26): it
    hid the instant #host got its first child — the .romp-tl-wrap on TimelinePanel construction, BEFORE any
    bars — leaving an empty bar gap. The view owns the bars-area loader now (_drawBarsLoader, gated on
    _barsLoaded), so the spinner stays until the deferred {type:"bars"} payload renders."""

    def test_timeline_page_drops_the_full_pane_spin_but_keeps_the_host(self):
        page = km._timeline_page()
        self.assertIn("<div id=host>", page, "the timeline still mounts into #host")
        self.assertNotIn("id=pane-spin", page, "no full-pane _pane_spin overlay (it hid before the bars)")

    def test_other_panes_keep_their_pane_spin(self):
        # the chat/feed/fleet loaders are unaffected — only the timeline's was dropped
        self.assertIn("id=pane-spin", km._pane_spin("content"))


class PushSplit(unittest.TestCase):
    def test_push_ships_the_lanes_skeleton_before_the_bars(self):
        sent, builds = [], []
        client = {"app": "timeline", "send": sent.append, "sent": {}, "alive": True}
        SKEL = {"type": "timeline", "sessions": [{"id": "S"}], "turns": {}, "judging": [],
                "messages": [], "now": 1, "usage": {}}
        FULL = {"type": "timeline", "sessions": [{"id": "S"}], "turns": {"S": [{"id": "b1"}]},
                "judging": [{"k": "planner"}], "messages": [{"m": 1}], "now": 1}
        o_bt, o_ct, o_tmux, o_sig = (km.build_timeline, km._cached_timeline,
                                     km._tmux_sessions, km._fleet_view_sig)
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: (
            builds.append(with_bars) or (FULL if with_bars else SKEL))
        km._cached_timeline = lambda now, tmux, sig, connect=False: FULL
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        try:
            km._push([client])
        finally:
            (km.build_timeline, km._cached_timeline,
             km._tmux_sessions, km._fleet_view_sig) = o_bt, o_ct, o_tmux, o_sig
        msgs = [json.loads(s) for s in sent]
        types = [m["type"] for m in msgs]
        self.assertIn("data", types)
        self.assertIn("bars", types)
        self.assertLess(types.index("data"), types.index("bars"), "lanes skeleton ships BEFORE the bars")
        skel = msgs[types.index("data")]["data"]
        self.assertEqual(skel["turns"], {}, "the {type:data} message is the lanes skeleton — no bars")
        bars = msgs[types.index("bars")]
        self.assertEqual(bars["turns"], {"S": [{"id": "b1"}]}, "the heavy bars ride the {type:bars} message")
        for k in ("judging", "messages"):
            self.assertIn(k, bars, "the whole time-plotted detail rides the bars message")
        self.assertEqual(builds, [], "a warm push builds no skeleton: the lanes are projected from the cache")
        self.assertEqual(skel["sessions"], FULL["sessions"], "…and they are the cached build's lanes")


class SkeletonFromCache(unittest.TestCase):
    """The warm-path skeleton is a PROJECTION of the cached full build (2026-09-06). Every pusher cycle
    used to run build_timeline(with_bars=False) — no parse, but the same per-lane derivation the cached
    full build had just done — and then sent the resulting frame to every timeline client unconditionally,
    because the clock inside `data` defeated the dedup. A hit now serves the last rebuild's lanes
    byte-for-byte, so a lane moves only when the timeline rebuilds: on a view-sig change, on
    _mark_views_dirty, or at the 5 s bucket."""

    FULL = {"type": "timeline", "now": 1,
            "sessions": [{"id": "S", "name": "web", "state": "working", "context": 10,
                          "compactions": [{"t": 5}]}],
            "turns": {"S": [{"id": "b1"}]}, "judging": [{"k": "planner"}], "messages": [{"m": 1}],
            "views": {"active": "all"}, "usage": {"five": {"pct": 3}}}

    class _Clock:
        """km's `time` with a settable skew on time() — so two pushes can carry different clocks without
        sleeping, and everything else (monotonic, sleep) passes through."""
        def __init__(self, real):
            self._real, self.skew = real, 0.0

        def __getattr__(self, name):
            return getattr(self._real, name)

        def time(self):
            return self._real.time() + self.skew

    def setUp(self):
        self.saved = (km.build_timeline, km._cached_timeline, km._tmux_sessions, km._fleet_view_sig, km.time)
        self.saved_built, self.saved_dirty, self.saved_wire = list(km._built_timeline), km._views_dirty[0], km._bars_wire
        self.builds = []
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: (
            self.builds.append((with_bars, live_only)) or self.rebuilt())
        km._cached_timeline = lambda now, tmux, sig, connect=False: self.FULL
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        self.clock = km.time = self._Clock(time)

    def tearDown(self):
        (km.build_timeline, km._cached_timeline, km._tmux_sessions, km._fleet_view_sig, km.time) = self.saved
        km._built_timeline[:] = self.saved_built
        km._views_dirty[0] = self.saved_dirty
        km._bars_wire = self.saved_wire

    def rebuilt(self):
        return dict(self.FULL, now=2, sessions=[dict(self.FULL["sessions"][0], state="ready")])

    @staticmethod
    def _client():
        frames = []
        return {"app": "timeline", "send": frames.append, "sent": {}, "alive": True}, frames

    @staticmethod
    def _data_frames(frames):
        return [json.loads(f) for f in frames if json.loads(f)["type"] == "data"]

    def test_two_pushes_over_an_unchanged_cache_build_nothing_and_resend_no_lanes(self):
        c, frames = self._client()
        km._push([c])
        first = list(frames)
        self.clock.skew = 7.0                       # a later second AND a later 5 s bucket: only the clock moved
        km._push([c])
        self.assertEqual(self.builds, [], "a warm push runs no build_timeline at all — no skeleton build")
        data = self._data_frames(first)
        self.assertEqual(len(data), 1, "the first push ships the lanes frame")
        self.assertEqual(data[0]["data"]["sessions"], self.FULL["sessions"], "…as the cached build's lanes")
        self.assertEqual(data[0]["data"]["turns"], {})
        self.assertEqual(data[0]["data"]["judging"], [])
        self.assertEqual(data[0]["data"]["messages"], [])
        self.assertEqual(data[0]["data"]["usage"], self.FULL["usage"], "usage rides the projected skeleton")
        second = frames[len(first):]
        self.assertEqual(sum(len(f) for f in second if json.loads(f)["type"] == "data"), 0,
                         "the second push sent zero bytes on the lanes slot: the frame dedups with `now` removed")
        self.assertEqual(self.FULL["turns"], {"S": [{"id": "b1"}]}, "the cached build itself is never mutated")
        self.assertEqual(self.FULL["now"], 1)

    def test_the_skeleton_sig_ignores_the_clock_and_keys_the_lanes(self):
        skel = km._timeline_skeleton(self.FULL, 100)
        self.assertEqual(skel["now"], 100)
        self.assertEqual(km._skeleton_sig(skel), km._skeleton_sig(km._timeline_skeleton(self.FULL, 200)),
                         "the same lanes at a later clock compare equal")
        self.assertNotEqual(km._skeleton_sig(skel), km._skeleton_sig(km._timeline_skeleton(self.rebuilt(), 100)),
                            "a lane state change compares different")
        self.assertIsNot(skel, self.FULL)
        self.assertEqual(self.FULL["turns"], {"S": [{"id": "b1"}]}, "a projection is a copy, not a mutation")

    def test_a_dirty_mark_between_two_pushes_rebuilds_and_ships_the_new_lanes(self):
        km._cached_timeline = self.saved[1]             # the real cache, warmed with FULL under the stubbed sig
        km._built_timeline[:] = [("sig",), self.FULL, time.time(), time.time()]
        km._views_dirty[0] = 0.0
        km._bars_wire = None
        c, frames = self._client()
        km._push([c])
        self.assertEqual(self.builds, [], "an unchanged sig on a warm cache is a hit")
        n = len(frames)
        km._mark_views_dirty()                          # an optimistic kernel-side mutation: the deciding event
        km._push([c])
        self.assertEqual(self.builds, [(True, False)], "the dirty mark rebuilt the FULL timeline, once, and no skeleton")
        data = self._data_frames(frames[n:])
        self.assertEqual(len(data), 1, "the rebuilt lanes ship")
        self.assertEqual(data[0]["data"]["sessions"][0]["state"], "ready", "…carrying the rebuild's state")

    def test_the_skeleton_carries_the_cached_builds_compactions(self):
        # The built skeleton set session = {"turns": []}, so its `compactions` was always [] and the
        # timeline never drew a compaction marker; the projection carries the full build's list, which
        # comes from the fresh parse (the authoritative source). The stub below is the OLD skeleton's
        # shape (no compactions), so a push that built a skeleton would ship [] here.
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: (
            self.rebuilt() if with_bars else dict(self.FULL, turns={}, judging=[], messages=[],
                                                  sessions=[dict(self.FULL["sessions"][0], compactions=[])]))
        c, frames = self._client()
        km._push([c])
        lane = self._data_frames(frames)[0]["data"]["sessions"][0]
        self.assertEqual(lane["compactions"], [{"t": 5}])

    def test_the_view_sig_keys_every_row_field_the_lanes_read(self):
        # The sig read `ctx`, which no liveness row carries (rows write `context`), so a context-% change
        # never busted the cache; the other fields were never keyed. With the skeleton projected from the
        # cache, each of these must bust it or the lane holds the old value until the bucket.
        sig = self.saved[3]
        row = {"state": "working", "model": "m", "effort": "high", "mode": "", "fast": "on", "since": 100,
               "context": 10, "fastReason": "", "modelPending": False, "interrupting": False,
               "subagents": [], "bgTasks": []}
        base = sig(1000, {"S": dict(row)})
        self.assertEqual(base, sig(1000, {"S": dict(row)}), "stable on identical rows")
        for k, v in (("context", 20), ("fastReason", "cooldown"), ("modelPending", True), ("interrupting", True),
                     ("subagents", [{"type": "Explore", "since": 90}]),
                     ("bgTasks", [{"toolUseId": "t1", "desc": "watch the build", "since": 90}])):
            self.assertNotEqual(base, sig(1000, {"S": {**row, k: v}}), "%s must bust the view sig" % k)
        self.assertEqual(sig(1000, {"S": {**row, "bgTasks": [{"toolUseId": "t1", "lastTool": "Read"}]}}),
                         sig(1000, {"S": {**row, "bgTasks": [{"toolUseId": "t1", "lastTool": "Grep"}]}}),
                         "a task's progress fields are not a lane fact: keyed on the task ids only")
        self.assertEqual(base, sig(1000, {"S": {**row, "snapT": 123456.0}}), "the snapshot's clock stays out")

    def test_the_view_sig_stats_usage_and_the_views_blob(self):
        sig = self.saved[3]
        st = km.jd.STATE
        st.mkdir(parents=True, exist_ok=True)
        usage, views = st / "usage.json", km._views_path()
        for f in (usage, views):
            if f.exists():
                f.unlink()
        try:
            base = sig(1000, {})
            usage.write_text(json.dumps({"five_hour": {"pct": 12}}))
            with_usage = sig(1000, {})
            self.assertNotEqual(base, with_usage, "a usage.json write busts the sig: the lanes frame carries the usage bars")
            views.write_text(json.dumps({"active": "all", "tags": []}))
            self.assertNotEqual(with_usage, sig(1000, {}), "a timeline-views.json write busts the sig: the views blob rides every frame")
        finally:
            for f in (usage, views):
                if f.exists():
                    f.unlink()

    def test_the_skeleton_build_loads_a_store_for_a_dead_lane_only(self):
        # The one skeleton build left (the cold live-first connect) reads the goal store only where it uses
        # it: a DEAD lane's blocked badge. A live lane's load bought nothing; the full build still loads for
        # every lane (its seams and judging marks read the store).
        loads = []
        o_ts, o_lg = km._timeline_sessions, km.jd.load_goals
        km.build_timeline = self.saved[0]
        km._timeline_sessions = lambda now, tmux, live_only=False: [
            {"sid": "D", "name": "d", "path": "/no/such/transcript-d"},
            {"sid": "L", "name": "l", "path": "/no/such/transcript-l"}]
        km.jd.load_goals = lambda sid: (loads.append(sid), {"status": {"g1": "blocked"}} if sid == "D" else {"status": {}})[1]
        live = {"L": {"state": "waiting", "since": 0, "model": "", "effort": "", "context": None,
                      "compactPct": None, "color": None, "mode": ""}}
        try:
            lanes = {l["id"]: l for l in km.build_timeline(1000, live, with_bars=False)["sessions"]}
            self.assertEqual(lanes["D"]["state"], "needsInput", "the dead lane still reads its blocked badge")
            self.assertEqual(loads, ["D"], "the skeleton loaded the dead lane's store and nothing else")
            del loads[:]
            km.build_timeline(1000, live, with_bars=True)
            self.assertEqual(sorted(loads), ["D", "L"], "the full build keeps its load for every lane")
        finally:
            km._timeline_sessions, km.jd.load_goals = o_ts, o_lg

    def test_a_steady_push_of_an_unchanged_timeline_sends_no_bars_and_a_rebuilt_one_sends_a_slotted_delta(self):
        """The pusher hands _send_slot the same bars object while the cached timeline's identity holds (_bars_wire),
        so a delta client's unchanged cycle runs no per-entry compare and sends nothing. When the timeline is
        rebuilt the bars cross as a delta frame that goes through _client_send: the slot key is on the client
        while it goes (what the drop log and the bench harness read), where a bare send left it unset."""
        sent = []
        client = {"app": "timeline", "sent": {}, "alive": True, "delta": True}
        client["send"] = lambda s: sent.append((client.get("curSlot"), json.loads(s)))
        SKEL = {"type": "timeline", "sessions": [{"id": "S"}], "turns": {}, "judging": [],
                "messages": [], "now": 1, "usage": {}}
        FULL1 = {"type": "timeline", "sessions": [{"id": "S"}], "turns": {"S": [{"id": "b1"}]},
                 "judging": [], "messages": [], "now": 1}
        FULL2 = {"type": "timeline", "sessions": [{"id": "S"}], "turns": {"S": [{"id": "b1"}, {"id": "b2"}]},
                 "judging": [], "messages": [], "now": 2}
        holder = {"tl": FULL1}
        calls = []
        o_bt, o_ct, o_tmux, o_sig, o_frac, o_order, o_wire = (km.build_timeline, km._cached_timeline, km._tmux_sessions,
                                                             km._fleet_view_sig, km._DELTA_MAX_FRACTION, km._client_order,
                                                             km._bars_wire)
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: (holder["tl"] if with_bars else SKEL)
        km._cached_timeline = lambda now, tmux, sig, connect=False: holder["tl"]
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        km._DELTA_MAX_FRACTION = 10.0         # synthetic payloads are tiny: the size guard would send the whole instead
        km._client_order = lambda *a: calls.append(1) or o_order(*a)
        try:
            km._push([client])                # the skeleton and the keyed full bars
            km._push([client])                # the same timeline object: the same bars object
            n_sent, n_calls = len(sent), len(calls)
            km._push([client])
            self.assertEqual(len(sent), n_sent, "an unchanged timeline sends no bars frame")
            self.assertEqual(len(calls), n_calls, "…and runs no per-entry compare to find that out")
            holder["tl"] = FULL2              # a rebuild: a new timeline object with one more bar
            km._push([client])
        finally:
            (km.build_timeline, km._cached_timeline, km._tmux_sessions, km._fleet_view_sig, km._DELTA_MAX_FRACTION,
             km._client_order, km._bars_wire) = o_bt, o_ct, o_tmux, o_sig, o_frac, o_order, o_wire
        bars = [(k, m) for k, m in sent if m["type"] in ("bars", "delta")]
        self.assertEqual([m["type"] for _k, m in bars], ["bars", "delta"])
        self.assertEqual([k for k, _m in bars], [("timelinebars",), ("timelinebars",)],
                         "both bars frames went with the slot key on the client")
        self.assertEqual(set(bars[1][1]["coll"]["turns"]["set"]), {"S\u001fb2"}, "one bar crosses")


class DeadLaneWindow(unittest.TestCase):
    """Dead lanes default to a 12h window and the FIRST cold paint reads no dead session at all (the user
    2026-06-26: "rarely looking at 48h"; "get the main UI up with the live sessions first, dead in background")."""

    def test_dead_lanes_limited_to_12h_live_only_drops_them_all(self):
        now = 1_000_000
        o_alive, o_sessions, o_ordered = km._alive_sessions, km._sessions, km._ordered
        km._alive_sessions = lambda now, tmux: [{"sid": "LIVE", "name": "l", "path": "/l", "mtime": now}]
        km._sessions = lambda now: [
            {"sid": "LIVE", "name": "l", "path": "/l", "mtime": now},
            {"sid": "RECENT", "name": "r", "path": "/r", "mtime": now - 6 * 3600},    # dead, within 12h
            {"sid": "OLD", "name": "o", "path": "/o", "mtime": now - 30 * 3600},      # dead, beyond 12h
        ]
        km._ordered = lambda lst: lst
        try:
            lanes = {s["sid"] for s in km._timeline_sessions(now, {})}
            self.assertEqual(lanes, {"LIVE", "RECENT"}, "a dead lane >12h old is dropped")
            live = {s["sid"] for s in km._timeline_sessions(now, {}, live_only=True)}
            self.assertEqual(live, {"LIVE"}, "live_only drops every dead lane (cold-start first paint)")
        finally:
            km._alive_sessions, km._sessions, km._ordered = o_alive, o_sessions, o_ordered

    def test_cold_connect_builds_live_only_and_wakes_the_producer_for_the_rest(self):
        calls, sent = [], []
        client = {"app": "timeline", "send": sent.append, "sent": {}, "alive": True}
        SK = {"type": "timeline", "sessions": [], "turns": {}, "judging": [], "messages": [],
              "now": 1, "usage": {}}
        FB = {"type": "timeline", "sessions": [], "turns": {"S": []}, "judging": [],
              "messages": [], "now": 1}
        o_bt, o_tmux, o_sig = km.build_timeline, km._tmux_sessions, km._fleet_view_sig
        o_built = list(km._built_timeline)
        km.build_timeline = lambda now, tmux, with_bars=True, live_only=False: (
            calls.append(("bars" if with_bars else "skel", live_only)) or (FB if with_bars else SK))
        km._tmux_sessions = lambda: {}
        km._fleet_view_sig = lambda now, tmux: ("sig",)
        km._built_timeline[0], km._built_timeline[1], km._built_timeline[2] = None, None, 0.0   # cold cache
        km._producer_wake.clear()
        try:
            km._push([client], connect=True)
        finally:
            km.build_timeline, km._tmux_sessions, km._fleet_view_sig = o_bt, o_tmux, o_sig
            km._built_timeline[:] = o_built
        self.assertIn(("skel", True), calls, "cold connect: the lanes skeleton is built LIVE-ONLY")
        self.assertIn(("bars", True), calls, "cold connect: the bars are built LIVE-ONLY (no dead reads)")
        self.assertTrue(km._producer_wake.is_set(), "the full live+dead build is warmed in the background")


if __name__ == "__main__":
    unittest.main()
