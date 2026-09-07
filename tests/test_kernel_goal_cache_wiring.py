"""The kernel side of the shared read-only goal-store cache (performance plan P9 / C1).

kernel/judge.py's load_goals_shared serves one deep-frozen parsed store per file version; this module pins
WHICH kernel sites load through it (the pusher's read-only sites) and which deliberately do not (every
writer, the probe-then-write tick jobs, and the two sites another branch owns), and drives the builders
over synthetic stores to show the cache in effect: each store parsed once per version across builds, the
frozen guard reaching a wired site without taking the frame down, the compaction sweep's eviction, and
one session's failed chat build no longer aborting the whole push. Synthetic fixtures only: placeholder
sids, invented goal text, transcript paths that do not exist (a lane with no transcript still builds)."""
import contextlib
import inspect
import io
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SIDS = ["66666666-1111-4222-8333-44444444440%d" % i for i in range(3)]   # private to this module (synthetic)
NOW = 1781100000
T0 = NOW - 3600

# The pusher-side READ-ONLY sites, wired (kernel.py). Each reads nodes / status / seams / confirming / log
# rows and hands nothing to rollup_status, record_verdict or save_goals (audited 2026-09-06; the deep
# freeze would raise if one did).
WIRED = {"_open_top_goal": 1, "_deferral_sweep_tick": 1, "_session_stamp_read": 1, "_owned_yield_why": 1,
         "_msg_sum_scan_session": 1, "build_feed": 1, "build_session": 2, "build_timeline": 2}
# NOT wired, on purpose. _lift_spent_awaiting and _bg_placed_tops belong to a sibling change (branch
# perf2-lift, the probe-then-write two-phase read); _feed_goals' live path is the feed's main store read
# and stays on the writer's loader until the B5 snapshot memo is replaced (its own change).
UNWIRED = ("_lift_spent_awaiting", "_bg_placed_tops", "_feed_goals")


class WiringPins(unittest.TestCase):
    def test_the_read_only_pusher_sites_load_through_the_shared_cache(self):
        for name, n in WIRED.items():
            src = inspect.getsource(getattr(km, name))
            self.assertEqual(src.count("jd.load_goals_shared("), n, "%s: shared loads" % name)
            self.assertEqual(src.count("jd.load_goals("), 0, "%s: no writer-style load left" % name)

    def test_the_writers_and_the_sibling_branchs_sites_stay_on_load_goals(self):
        for name in UNWIRED:
            src = inspect.getsource(getattr(km, name))
            self.assertEqual(src.count("jd.load_goals_shared("), 0, "%s: not wired" % name)
            self.assertGreaterEqual(src.count("jd.load_goals("), 1, "%s: still the writer's loader" % name)

    def test_the_compaction_sweep_evicts_the_caches_absent_paths(self):
        src = inspect.getsource(km._compact_goal_stores)
        self.assertIn("jd._disk_memo_evict_absent()", src)
        self.assertIn("jd._shared_evict_absent()", src)

    def test_perf_reports_the_cache_beside_the_snapshot_memo(self):
        src = inspect.getsource(km._PerfStats.snapshot)
        self.assertIn('("goals_shared", jd.shared_store_stats)', src, "one (name, report) pair in the memos loop")


class SharedViewInBuilds(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd._rebind_state(Path(self.td.name))         # clears the cache and lifts any earlier off switch
        self.saved = {nm: getattr(km, nm) for nm in ("_timeline_sessions", "_derive_judging")}
        for i, sid in enumerate(SIDS):
            s = {"rompUuid": sid, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {},
                 "placements": {}, "status": {}}
            jd.apply_plan(s, "s1", T0, [{"do": "mint", "why": "x", "text": "Goal %d" % i}], [])
            jd.rollup_status(s, session_closed=False)
            jd.save_goals(sid, s)
        km._timeline_sessions = lambda now, tmux, live_only=False: [
            {"sid": sid, "name": "s%d" % i, "path": os.path.join(self.td.name, "no-such-transcript-%d" % i)}
            for i, sid in enumerate(SIDS)]
        self.stats0 = jd.shared_store_stats()

    def tearDown(self):
        for nm, v in self.saved.items():
            setattr(km, nm, v)
        jd._rebind_state(self.saved_state)
        self.td.cleanup()

    def _delta(self, key):
        return jd.shared_store_stats()[key] - self.stats0[key]

    def _errors(self):
        try:
            return [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()]
        except FileNotFoundError:
            return []

    def test_two_timeline_builds_parse_each_store_once(self):
        fills = []
        o_freeze = jd._freeze_store
        jd._freeze_store = lambda store, fsid=None: (fills.append(1), o_freeze(store, fsid))[1]
        try:
            tl1 = km.build_timeline(NOW, {}, with_bars=True)
            tl2 = km.build_timeline(NOW, {}, with_bars=True)
        finally:
            jd._freeze_store = o_freeze
        self.assertEqual(len(fills), len(SIDS), "one parse per store across two full builds")
        self.assertEqual(self._delta("miss"), len(SIDS))
        self.assertGreaterEqual(self._delta("hit"), len(SIDS), "the second build's loads are all hits")
        self.assertEqual(self._delta("poisoned"), 0, "the build wrote nothing into the shared views")
        self.assertEqual(sorted(l["id"] for l in tl1["sessions"]), sorted(SIDS))
        self.assertEqual(json.dumps(tl1["turns"]), json.dumps(tl2["turns"]), "same inputs, same frame")

    def test_the_store_a_wired_site_works_on_is_the_frozen_shared_view(self):
        seen, raised = [], []

        def spy(sid, caps, goals, t0, out, seg_ends=None):
            seen.append(goals)
            for attempt in (lambda: goals["status"].__setitem__("x", "y"),
                            lambda: goals["nodes"][sid + ":g1"]["log"].append({"kind": "done"}),
                            lambda: goals["nodes"][sid + ":g1"].__setitem__("text", "edited")):
                try:
                    attempt()
                except jd.FrozenStoreError:
                    raised.append(1)
            return self.saved["_derive_judging"](sid, caps, goals, t0, out, seg_ends)
        km._derive_judging = spy
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            tl = km.build_timeline(NOW, {}, with_bars=True)
        self.assertEqual(len(seen), len(SIDS))
        # The FIRST lane holds the shared view and every nested write on it raises; the first raise switches
        # the cache off for the process, so the lanes after it are served private, mutable load_goals stores
        # (the fallback) — their writes land on a throwaway copy and nothing shared is touched.
        self.assertIsInstance(seen[0], jd.FrozenStore, "the wired site holds the shared view")
        self.assertEqual(len(raised), 3, "every nested write on the shared view raised")
        self.assertTrue(all(type(g) is dict for g in seen[1:]), "later lanes take the fallback (private stores)")
        self.assertEqual(len(tl["sessions"]), len(SIDS), "the frame still shipped, every lane in it")
        rows = [r for r in self._errors() if r["err"] == "frozen-store-write"]
        self.assertEqual(len(rows), 1, "one loud row, naming the writing site")
        self.assertIn(os.path.basename(__file__), rows[0]["note"])
        self.assertEqual(jd.shared_store_stats()["off"], 1, "the cache is off for the process")
        self.assertEqual(self._delta("poisoned"), 3)
        self.assertEqual(self._delta("fallback"), len(SIDS) - 1)
        self.assertNotIn("x", seen[0]["status"])         # nothing landed on the shared object
        self.assertEqual(seen[0]["nodes"][seen[0]["rompUuid"] + ":g1"]["text"], "Goal 0")
        self.assertEqual(seen[0]["nodes"][seen[0]["rompUuid"] + ":g1"]["log"], [])
        self.assertEqual(jd.load_goals(SIDS[1])["nodes"][SIDS[1] + ":g1"]["text"], "Goal 1",
                         "a write on a fallback store reached no file")
        # the board keeps rendering: the next build's loads take load_goals (private, mutable) and succeed
        km._derive_judging = self.saved["_derive_judging"]
        km.build_timeline(NOW, {}, with_bars=True)
        self.assertEqual(self._delta("fallback"), 2 * len(SIDS) - 1)

    def test_open_top_goal_reads_the_shared_view_and_answers_after_a_write_attempt(self):
        sid = SIDS[0]
        self.assertEqual(km._open_top_goal(sid), sid + ":g1")
        self.assertEqual(self._delta("miss"), 1)
        self.assertEqual(km._open_top_goal(sid), sid + ":g1")
        self.assertEqual(self._delta("hit"), 1)
        with self.assertRaises(jd.FrozenStoreError):
            jd.load_goals_shared(sid)["status"][sid + ":g1"] = "completed"
        self.assertEqual(km._open_top_goal(sid), sid + ":g1", "still answers with the cache off")
        self.assertEqual(self._delta("fallback"), 1)

    def test_the_compaction_sweep_evicts_a_removed_stores_entry(self):
        for sid in SIDS:
            jd.load_goals_shared(sid)
        self.assertEqual(jd.shared_store_stats()["entries"], len(SIDS))
        os.unlink(jd.GOALDIR / (SIDS[0] + ".json"))
        km._compact_goal_stores()
        self.assertEqual(jd.shared_store_stats()["entries"], len(SIDS) - 1)
        self.assertEqual(self._delta("evict"), 1)


class PushSurvivesOneFailedChatBuild(unittest.TestCase):
    """A chat build that raises used to abort the whole push (the cycle-level "push build:" catch returns
    before the feed and the timeline are built). One session's build now fails alone: its frame is skipped
    this cycle, the other sessions' frames and the timeline still go out, and stderr names it."""
    STUBS = ("NAMES", "_tmux_sessions", "_live_names", "_tab_list_tmux", "_chat_tab_sessions", "build_session",
             "_cached_feed", "_cached_timeline", "build_timeline", "_fleet_view_sig", "_comments_frame",
             "_retry_parked_creates")
    A, B = SIDS[1], SIDS[2]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        names = Path(self.tmp) / "names"
        names.mkdir()
        (names / self.A).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        (names / self.B).write_text("api\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.tx = {}
        for sid in (self.A, self.B):
            self.tx[sid] = Path(self.tmp) / (sid + ".jsonl")
            self.tx[sid].write_text('{"type": "user"}\n')
        self.saved = {nm: getattr(km, nm) for nm in self.STUBS}
        self.saved_state = (km.jd.STATE, dict(km._built_chat), dict(km._prev_chat_events),
                            dict(km._prev_chat_ledger), list(km._last_tab_order))
        km.NAMES = names
        km.jd.STATE = Path(self.tmp) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._tmux_sessions = lambda: {}
        km._live_names = lambda tm: {"web": self.A, "api": self.B}
        km._tab_list_tmux = lambda tmux: dict(tmux)
        km._chat_tab_sessions = lambda now, tmux: [
            {"sid": sid, "name": nm, "path": str(self.tx[sid]), "anchor": sid}
            for sid, nm in ((self.A, "web"), (self.B, "api"))]
        km.build_session = self._build_session
        km._cached_feed = lambda now, tmux, sig, connect=False: {"working": [], "awaiting": [], "now": now}
        km._cached_timeline = lambda now, tmux, sig, connect=False: {"turns": {}, "judging": [], "messages": [],
                                                                      "now": now}
        km.build_timeline = lambda now, tmux, **kw: {"lanes": [], "now": now}
        km._fleet_view_sig = lambda now, tmux: {"probe": 1}
        km._comments_frame = lambda sid, tmux: None
        km._retry_parked_creates = lambda: None
        km._built_chat.clear(); km._prev_chat_events.clear(); km._prev_chat_ledger.clear()
        self.built = []
        self.chat_frames, self.tl_frames = [], []
        self.chat = {"app": "chat", "alive": True, "sent": {}, "send": lambda s: self.chat_frames.append(json.loads(s))}
        self.tl = {"app": "timeline", "alive": True, "sent": {}, "send": lambda s: self.tl_frames.append(json.loads(s))}

    def tearDown(self):
        for nm, v in self.saved.items():
            setattr(km, nm, v)
        st, bc, pe, pl, lo = self.saved_state
        km.jd.STATE = st
        km._built_chat.clear(); km._built_chat.update(bc)
        km._prev_chat_events.clear(); km._prev_chat_events.update(pe)
        km._prev_chat_ledger.clear(); km._prev_chat_ledger.update(pl)
        km._last_tab_order[:] = lo

    def _build_session(self, sid, now, tmux):
        self.built.append(sid)
        if sid == self.A:
            raise RuntimeError("synthetic: this session's chat build fails")
        return {"type": "session", "id": sid, "name": "api", "events": [{"uuid": "e1", "type": "user"}],
                "ledger": None, "status": {"state": "waiting"}, "color": None}

    def test_the_other_sessions_frames_and_the_timeline_still_go_out(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._push([self.chat, self.tl])
        self.assertEqual(sorted(self.built), sorted([self.A, self.B]), "both builds were attempted")
        sessions = [f for f in self.chat_frames if f.get("type") == "session"]
        self.assertEqual([f["id"] for f in sessions], [self.B], "the surviving session's frame went out")
        self.assertIn("bars", [f["type"] for f in self.tl_frames], "the push went on to the timeline")
        self.assertIn("push build: chat %s" % self.A[:8], err.getvalue(), "stderr names the failed build")
        self.assertIn("synthetic: this session's chat build fails", err.getvalue())
        self.assertNotIn(self.A, km._built_chat, "no cache entry for the failed build")
        self.assertIn(self.B, km._built_chat)


if __name__ == "__main__":
    unittest.main()
