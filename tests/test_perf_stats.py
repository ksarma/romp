#!/usr/bin/env python3
"""The kernel's always-on performance counters (`_PerfStats`, GET /perf, `romp perf`) and the runtime
switch for the romp-perf stderr log (POST /perf {"log": bool}).

Before this the only instrumentation was `_perf()`, gated on ROMP_PERF at process start, so turning it
on meant a kernel restart; and nothing reported rates, so an optimization was checked with a hand-run
profiler. The collector counts pusher cycles and wakes, cycle durations (a ring for percentiles),
per-stage time, build cache hits, bytes sent per slot kind, goal-store I/O, judge passes and HTTP
requests per path, with a lock and dict increments on the hot paths and no formatting until a read.

Drives the REAL Handler over HTTP (the test_color_route.py pattern). Synthetic fixtures only:
placeholder UUIDs, invented names."""
import inspect
import io
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel_perf", os.path.join(BIN, "romp-kernel")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
# A PRIVATE synthetic sid for the goal-store tests: load_goals replays the per-sid override journal,
# and node ids collide across test modules under the shared placeholder (CLAUDE.md, goal-store fixtures).
GOAL_SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
TOP_KEYS = {"now", "since", "uptime_s", "log", "process", "pusher", "stages_ms", "builds", "sends",
            "goals", "judge", "http"}


class Collector(unittest.TestCase):
    """_PerfStats on its own: every writer lands where the docstring says, and the read-time work
    (percentiles, the goals read, the process reads) produces the documented shape."""

    def setUp(self):
        self.st = km._PerfStats()

    def test_snapshot_has_the_documented_shape_and_starts_at_zero(self):
        snap = self.st.snapshot()
        self.assertEqual(set(snap), TOP_KEYS)
        self.assertEqual(snap["pusher"]["cycles"], 0)
        self.assertEqual(snap["pusher"]["cycle_ms_p50"], 0.0)
        self.assertEqual(snap["pusher"]["ring_n"], 0)
        self.assertEqual(set(snap["stages_ms"]), set(km._PerfStats.STAGES))
        self.assertEqual(set(snap["builds"]), {"chat", "feed", "timeline"})
        self.assertEqual(set(snap["sends"]), {"full", "delta", "deduped"})
        self.assertEqual(snap["judge"]["ms_mean"], 0.0, "no passes: the mean is 0, not a division error")
        self.assertEqual(set(snap["goals"]), {"loads", "saves", "writes"}, "read through jd.goal_io_stats")
        for k in ("rss_kb", "threads", "cpu_s", "pid"):
            self.assertIn(k, snap["process"])
        self.assertGreater(snap["process"]["threads"], 0)
        self.assertGreaterEqual(snap["process"]["rss_kb"], 0)
        self.assertGreaterEqual(snap["uptime_s"], 0)
        json.dumps(snap)                                     # the whole thing serializes as-is

    def test_pusher_counters(self):
        self.st.wake(); self.st.wake(); self.st.wake()
        self.st.wake_kind(True); self.st.wake_kind(False); self.st.wake_kind(False)
        self.st.cycle(0.010); self.st.cycle(0.030); self.st.cycle(0.020)
        p = self.st.snapshot()["pusher"]
        self.assertEqual(p["wakes"], 3)
        self.assertEqual((p["wakes_event"], p["wakes_backstop"]), (1, 2))
        self.assertEqual(p["cycles"], 3)
        self.assertAlmostEqual(p["cycle_ms_sum"], 60.0)
        self.assertAlmostEqual(p["cycle_ms_max"], 30.0)
        self.assertAlmostEqual(p["cycle_ms_last"], 20.0)
        self.assertEqual(p["ring_n"], 3)

    def test_ring_percentiles_come_from_the_last_256_cycles(self):
        for i in range(300):                                 # 0..299 ms; the ring keeps 44..299
            self.st.cycle(i / 1000.0)
        p = self.st.snapshot()["pusher"]
        self.assertEqual(p["ring_n"], 256)
        self.assertEqual(p["cycles"], 300, "the count is lifetime; only the percentile window is bounded")
        self.assertAlmostEqual(p["cycle_ms_p50"], 44 + 128)  # sorted ring[int(0.5 * 256)]
        self.assertAlmostEqual(p["cycle_ms_p90"], 44 + 230)  # sorted ring[int(0.9 * 256)]
        self.assertAlmostEqual(p["cycle_ms_max"], 299.0)

    def test_stages_builds_judge(self):
        self.st.stage("push.chat", 0.5); self.st.stage("push.chat", 0.25); self.st.stage("jobs", 0.1)
        self.st.build("chat", True); self.st.build("chat", False, 0.040); self.st.build("feed", False, 1.0)
        self.st.judge_pass(2.0); self.st.judge_pass(4.0)
        snap = self.st.snapshot()
        self.assertAlmostEqual(snap["stages_ms"]["push.chat"], 750.0)
        self.assertAlmostEqual(snap["stages_ms"]["jobs"], 100.0)
        self.assertEqual(snap["builds"]["chat"], {"cached": 1, "built": 1, "ms": 40.0})
        self.assertEqual(snap["builds"]["feed"]["built"], 1)
        self.assertEqual(snap["builds"]["timeline"], {"cached": 0, "built": 0, "ms": 0.0})
        self.assertEqual(snap["judge"]["passes"], 2)
        self.assertAlmostEqual(snap["judge"]["ms_last"], 4000.0)
        self.assertAlmostEqual(snap["judge"]["ms_mean"], 3000.0)

    def test_sends_classify_by_kind_and_slot_name(self):
        self.st.send(("chat", SID), "full", 1000)            # a tuple dedup key: the slot is its first element
        self.st.send(("chat", SID), "full", 500)
        self.st.send(("chat", SID), "deduped", 1000)
        self.st.send("feed", "delta", 20)                    # a bare string key (the feed's own delta path)
        s = self.st.snapshot()["sends"]
        self.assertEqual(s["full"], {"chat": {"count": 2, "bytes": 1500}})
        self.assertEqual(s["deduped"], {"chat": {"count": 1, "bytes": 1000}})
        self.assertEqual(s["delta"], {"feed": {"count": 1, "bytes": 20}})

    def test_send_slots_are_capped(self):
        for i in range(40):
            self.st.send(("slot%d" % i,), "full", 1)
        d = self.st.snapshot()["sends"]["full"]
        self.assertEqual(len(d), km._PerfStats.SLOTS + 1)
        self.assertEqual(d["other"]["count"], 40 - km._PerfStats.SLOTS)

    def test_http_paths_are_capped_and_ws_is_counted_not_timed(self):
        for i in range(100):
            self.st.http_request("/scan/%d" % i, 0.001)
        self.st.http_request("/ws", None)
        h = self.st.snapshot()["http"]
        self.assertEqual(len(h), km._PerfStats.HTTP_PATHS + 1, "64 paths plus the fold")
        self.assertEqual(h["other"]["count"], 100 - km._PerfStats.HTTP_PATHS + 1,
                         "the 36 paths past the cap and /ws, which arrived after it")
        self.st2 = km._PerfStats()
        self.st2.http_request("/ws", None); self.st2.http_request("/tick", 0.002)
        h = self.st2.snapshot()["http"]
        self.assertEqual(h["/ws"], {"count": 1, "ms": 0.0}, "a socket's lifetime is not a request time")
        self.assertEqual(h["/tick"]["count"], 1)
        self.assertAlmostEqual(h["/tick"]["ms"], 2.0)

    def test_reset_starts_over_and_moves_since(self):
        self.st.cycle(0.1); self.st.http_request("/x", 0.1)
        before = self.st.snapshot()["since"]
        time.sleep(0.01)
        self.st.reset()
        snap = self.st.snapshot()
        self.assertEqual(snap["pusher"]["cycles"], 0)
        self.assertEqual(snap["http"], {})
        self.assertGreater(snap["since"], before)

    def test_writers_are_thread_safe(self):
        def hammer():
            for _ in range(2000):
                self.st.wake(); self.st.send(("chat", SID), "full", 1); self.st.http_request("/p", 0.0)
        ts = [threading.Thread(target=hammer) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        snap = self.st.snapshot()
        self.assertEqual(snap["pusher"]["wakes"], 16000)
        self.assertEqual(snap["sends"]["full"]["chat"]["count"], 16000)
        self.assertEqual(snap["http"]["/p"]["count"], 16000)


class WakeCounting(unittest.TestCase):
    """_pusher_wake is a threading.Event whose set() counts: every existing call site — including the
    bound-method callbacks the backends hold — counts a wake without being touched."""

    def test_the_pusher_wake_counts_sets(self):
        self.assertIsInstance(km._pusher_wake, threading.Event)
        self.assertIsInstance(km._pusher_wake, km._CountedEvent)
        was_set = km._pusher_wake.is_set()
        before = km._PERF_STATS.snapshot()["pusher"]["wakes"]
        km._pusher_wake.set()
        cb = km._pusher_wake.set                             # the shape the backends are handed (push=_pusher_wake.set)
        cb()
        self.assertTrue(km._pusher_wake.is_set())
        self.assertEqual(km._PERF_STATS.snapshot()["pusher"]["wakes"], before + 2)
        if not was_set:
            km._pusher_wake.clear()

    def test_wake_helpers_still_set_the_event(self):
        km._pusher_wake.clear()
        km._push_soon()
        self.assertTrue(km._pusher_wake.is_set())
        km._pusher_wake.clear()


class PerfLogToggle(unittest.TestCase):
    """_perf() writes only when the switch is on, and the switch flips at runtime."""

    def setUp(self):
        self.saved = km._PERF
        km._set_perf_log(False)

    def tearDown(self):
        km._set_perf_log(self.saved)

    def test_off_writes_nothing_on_writes_one_line(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "")
        self.assertTrue(km._set_perf_log(True))
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "romp-perf probe a=1 b=2\n")
        km._set_perf_log(False)
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "", "off again: nothing")

    def test_the_off_path_reads_one_module_global(self):
        src = inspect.getsource(km._perf)
        self.assertIn("if not _PERF:\n        return", src, "the hot path stays a name lookup and a return")


class GoalIoCounters(unittest.TestCase):
    """judge.load_goals / save_goals count calls and disk writes; the kernel reads them via goal_io_stats."""

    def setUp(self):
        self.jd = km.jd
        self.jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._clean)

    def _clean(self):
        for p in (self.jd.GOALDIR / (GOAL_SID + ".json"), self.jd.STATE / "overrides" / (GOAL_SID + ".jsonl")):
            try:
                p.unlink()
            except OSError:
                pass

    def test_loads_saves_and_writes(self):
        before = self.jd.goal_io_stats()
        store = self.jd.load_goals(GOAL_SID)                 # no file yet: a fresh store, still one load
        after = self.jd.goal_io_stats()
        self.assertEqual(after["loads"], before["loads"] + 1)
        self.jd.save_goals(GOAL_SID, store)                  # the first publish writes the file
        after = self.jd.goal_io_stats()
        self.assertEqual(after["saves"], before["saves"] + 1)
        self.assertEqual(after["writes"], before["writes"] + 1)
        store = self.jd.load_goals(GOAL_SID)
        self.jd.save_goals(GOAL_SID, store)                  # byte-identical: a save, not a write
        after2 = self.jd.goal_io_stats()
        self.assertEqual(after2["saves"], after["saves"] + 1)
        self.assertEqual(after2["writes"], after["writes"], "the no-op republish skip is visible as saves without writes")
        self.assertEqual(km._PERF_STATS.snapshot()["goals"], after2, "the kernel's snapshot carries the judge counters")

    def test_the_getter_returns_a_copy(self):
        d = self.jd.goal_io_stats()
        d["loads"] = -1
        self.assertNotEqual(self.jd.goal_io_stats()["loads"], -1)


class PusherRecords(unittest.TestCase):
    """The pusher's seams record into _PERF_STATS: a cycle lands in the ring, the cached and rebuilt
    feed/timeline paths count, a send counts as full then deduped."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        names = Path(self.td.name) / "names"
        names.mkdir()
        self.saved = (km.NAMES, km._tmux_sessions, km._pusher_cycle_jobs, list(km._built_feed),
                      list(km._built_timeline), km.build_feed, km.build_timeline, km._needs_you_count,
                      km._feed_notifications, km._badge_push, km._views_dirty[0])
        km.NAMES = names
        km._tmux_sessions = lambda: {}
        self.addCleanup(self._restore)
        self.addCleanup(self.td.cleanup)

    def _restore(self):
        (km.NAMES, km._tmux_sessions, km._pusher_cycle_jobs, bf, bt, km.build_feed, km.build_timeline,
         km._needs_you_count, km._feed_notifications, km._badge_push, vd) = self.saved
        km._built_feed[:] = bf
        km._built_timeline[:] = bt
        km._views_dirty[0] = vd

    def test_a_cycle_is_counted_and_timed(self):
        km._pusher_cycle_jobs = lambda now, tmux, any_client: time.sleep(0.005)
        before = km._PERF_STATS.snapshot()["pusher"]
        km._pusher_cycle()
        after = km._PERF_STATS.snapshot()["pusher"]
        self.assertEqual(after["cycles"], before["cycles"] + 1)
        self.assertGreaterEqual(after["cycle_ms_last"], 5.0)
        self.assertEqual(after["ring_n"], min(before["ring_n"] + 1, km._PerfStats.RING))

    def test_a_raising_cycle_is_still_counted(self):
        km._pusher_cycle_jobs = lambda now, tmux, any_client: (_ for _ in ()).throw(RuntimeError("job died"))
        before = km._PERF_STATS.snapshot()["pusher"]["cycles"]
        with self.assertRaises(RuntimeError):
            km._pusher_cycle()
        self.assertEqual(km._PERF_STATS.snapshot()["pusher"]["cycles"], before + 1)

    def test_feed_and_timeline_builds_count_cached_and_rebuilt(self):
        km.build_feed = lambda now, tmux: {"working": [], "items": []}
        km.build_timeline = lambda now, tmux, **kw: {"turns": [], "judging": [], "messages": [], "now": now}
        km._needs_you_count = lambda feed: 0
        km._feed_notifications = lambda feed: []
        km._badge_push = lambda n: None
        km._views_dirty[0] = 0.0
        km._built_feed[:] = [None, None, 0.0, 0.0]
        km._built_timeline[:] = [None, None, 0.0, 0.0]
        b0 = km._PERF_STATS.snapshot()["builds"]
        now = int(time.time())
        km._cached_feed(now, {}, "sig-a")                    # nothing warmed: a rebuild
        km._cached_feed(now, {}, "sig-a")                    # unchanged sig: served from the cache
        km._cached_timeline(now, {}, "sig-a")
        km._cached_timeline(now, {}, "sig-a", connect=True)  # a connecting page never rebuilds
        b1 = km._PERF_STATS.snapshot()["builds"]
        self.assertEqual(b1["feed"]["built"] - b0["feed"]["built"], 1)
        self.assertEqual(b1["feed"]["cached"] - b0["feed"]["cached"], 1)
        self.assertGreaterEqual(b1["feed"]["ms"], b0["feed"]["ms"])
        self.assertEqual(b1["timeline"]["built"] - b0["timeline"]["built"], 1)
        self.assertEqual(b1["timeline"]["cached"] - b0["timeline"]["cached"], 1)

    def test_a_send_counts_full_then_deduped(self):
        sent = []
        c = {"app": "chat", "alive": True, "send": sent.append, "sent": {}}
        s0 = km._PERF_STATS.snapshot()["sends"]
        km._send_client(c, ("working", SID), {"type": "working", "names": ["web"]})
        km._send_client(c, ("working", SID), {"type": "working", "names": ["web"]})
        s1 = km._PERF_STATS.snapshot()["sends"]
        self.assertEqual(len(sent), 1, "the second identical frame was deduped")
        self.assertEqual(s1["full"]["working"]["count"] - s0["full"].get("working", {}).get("count", 0), 1)
        self.assertEqual(s1["full"]["working"]["bytes"] - s0["full"].get("working", {}).get("bytes", 0), len(sent[0]))
        self.assertEqual(s1["deduped"]["working"]["count"] - s0["deduped"].get("working", {}).get("count", 0), 1)

    def test_the_stage_seams_are_wired(self):
        # The stage timers sit at seams a stubbed _push cannot reach without the whole client machinery, so
        # their presence is pinned in the source, beside the behavioural tests above for the collector itself.
        push = inspect.getsource(km._push)
        for stage in ("push.chat", "push.feed", "push.timeline", "push.send"):
            self.assertIn('_PERF_STATS.stage("%s"' % stage, push)
        self.assertLess(push.index('stage("push.chat"'), push.index('stage("push.feed"'))
        self.assertLess(push.index('stage("push.feed"'), push.index('stage("push.timeline"'))
        self.assertLess(push.index('stage("push.timeline"'), push.index('stage("push.send"'))
        jobs = inspect.getsource(km._pusher_cycle_jobs)
        self.assertIn('_PERF_STATS.stage("push", _t_push)', jobs)
        self.assertIn('_PERF_STATS.stage("jobs", (time.monotonic() - _t_jobs) - _t_push)', jobs)
        self.assertIn("_PERF_STATS.judge_pass(", inspect.getsource(km._producer))
        loop = inspect.getsource(km._pusher)
        self.assertIn("_woke = _pusher_wake.wait(0.5)", loop)
        self.assertIn("_PERF_STATS.wake_kind(_woke)", loop)
        self.assertIn('_PERF_STATS.build("chat", True)', push)
        self.assertIn('_PERF_STATS.build("chat", False, _dt)', push)


class PerfRoutes(unittest.TestCase):
    """GET /perf and POST /perf through the real Handler: token-gated, the documented shape, the toggle."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.saved_log = km._PERF
        km._set_perf_log(False)

    def tearDown(self):
        km._set_perf_log(self.saved_log)

    def _req(self, method, path, body=None, token=True):
        headers = {"Content-Type": "application/json"}
        if token:
            # km.TOKEN, not os.environ: under xdist every worker imports every test module at
            # collection, and a later module's import-time ROMP_SERVE_TOKEN write changes the env
            # after this module's kernel captured its token (the test_kernel_attach_on_behalf pattern)
            headers["X-Romp-Token"] = km.TOKEN
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if raw.startswith(("{", "[")) else raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return e.code, (json.loads(raw) if raw.startswith(("{", "[")) else raw)

    def test_get_perf_serves_the_snapshot(self):
        st, snap = self._req("GET", "/perf")
        self.assertEqual(st, 200)
        self.assertEqual(set(snap), TOP_KEYS)
        self.assertIs(snap["log"], False)
        self.assertEqual(snap["process"]["pid"], os.getpid())
        st, snap2 = self._req("GET", "/perf?x=1")
        self.assertEqual(st, 200)
        self.assertGreaterEqual(snap2["http"]["/perf"]["count"], 1, "the request itself is counted, query stripped")
        self.assertNotIn("/perf?x=1", snap2["http"])

    def test_get_perf_requires_the_token(self):
        st, body = self._req("GET", "/perf", token=False)
        self.assertEqual(st, 403)
        self.assertNotIn("cycles", str(body))

    def test_post_perf_requires_the_token(self):
        st, body = self._req("POST", "/perf", {"log": True}, token=False)
        self.assertEqual(st, 403)
        self.assertFalse(km._PERF, "a refused POST flips nothing")

    def test_post_perf_flips_the_log_and_perf_emits_only_after(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "", "off before the POST")
        with redirect_stderr(io.StringIO()):                 # the route's own "log on" notice goes to stderr
            st, r = self._req("POST", "/perf", {"log": True})
        self.assertEqual((st, r), (200, {"ok": True, "log": True}))
        self.assertTrue(km._PERF)
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "romp-perf probe n=1\n", "on after the POST, no restart")
        st, snap = self._req("GET", "/perf")
        self.assertIs(snap["log"], True, "the snapshot reports the switch")
        with redirect_stderr(io.StringIO()):
            st, r = self._req("POST", "/perf", {"log": False})
        self.assertEqual((st, r), (200, {"ok": True, "log": False}))
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "")

    def test_post_perf_refuses_a_malformed_body(self):
        for body in ({}, {"log": "yes"}, {"log": 1}, [], "log"):
            st, r = self._req("POST", "/perf", body)
            self.assertEqual(st, 400, body)
            self.assertFalse(r["ok"])
        self.assertFalse(km._PERF)

    def test_the_routes_sit_after_the_gate_in_the_source(self):
        get = inspect.getsource(km.Handler.do_GET)
        gate = "ok, self._set_cookie, why = self._authorize(q)"
        self.assertEqual(get.count(gate), 1)
        self.assertGreater(get.index('p == "/perf"'), get.index(gate))
        post = inspect.getsource(km.Handler.do_POST)
        self.assertEqual(post.count(gate), 1)
        self.assertGreater(post.index('u.path == "/perf"'), post.index(gate))

    def test_every_request_is_timed_per_path(self):
        before = km._PERF_STATS.snapshot()["http"].get("/version", {"count": 0, "ms": 0.0})
        self._req("GET", "/version?probe=1", token=False)   # an exempt route counts too
        self._req("GET", "/version", token=False)
        after = km._PERF_STATS.snapshot()["http"]["/version"]
        self.assertEqual(after["count"], before["count"] + 2)
        self.assertGreater(after["ms"], before["ms"])


if __name__ == "__main__":
    unittest.main()
