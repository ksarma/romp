#!/usr/bin/env python3
"""Fold ruling A condition 7 as the reviewer ruled it on 2026-09-19, after jobs stage 1 (fork PR 784): with the auto-nudge
toggle off, the walk makes AT MOST ONE shared goal-store load per alive session per pass; EXACTLY ONE on a pass whose look
RUNS; ZERO on a pass whose look is SKIPPED. Stage 1 made the wake-only look record a memo row and skip on the ten-file key,
and the first wording of its amendment kept the ceiling (at most one) and dropped the floor; the ruling restored the floor,
so this pin holds both.

The shared load is the walk's one decision read, `jd.load_goals_shared_or_fault(sid)` in `_auto_nudge_session`, the read
ruling A counted (its wording: every alive session walked wake-only with exactly one load_goals_shared_or_fault and zero
plain load_goals in the decision path). Two witnesses count it. By execution: a recorder stands in for the name the walk
resolves at call time (`km.jd.load_goals_shared_or_fault`, the kernel's own judge instance), records each call with the
function that made it, and calls through to the real loader, so nothing about the shared cache is stubbed. By the served
counter: `memos.nudgeWalk.loads`, bumped at that one call site, must move by the same amount per pass. A skipped look
repeats its verdict and writes nothing (the wake-only memo of PR 784), so it needs no data: the recorder sees no call.

The placement gate's post-derivation currency re-read (`_nudge_placement_gate`, upstream's since the 2026-09-09 fold) is
the one other caller of the shared loader on the walk's road: one call per DERIVED session, none when the gate is served
or the look skipped. Ruling A listed it as open (to be offered upstream, never edited here), so it is counted apart and
named, never folded into the walk's count: a pass whose looks run with the gate served (the ledger moved, the tenth keyed
file) takes exactly one loader call per session in total; a pass whose looks derive (the first pass, a moved transcript)
takes the walk's one plus the gate's one. The floor is a look that runs to its decision read: a look the state gates end
earlier (a working session's, say) runs, records and takes none, which the ceiling allows and a case here shows.

Red in both directions, each mutation landed on kernel/kernel.py and reverted: a load creeping into the skip path (a shared
read in the gated look before it consults the memo) reds the skip pass; the load disappearing from the run path (the walk
reusing a stale snapshot instead of reading) reds the run pass. The assertion texts are in the commit message.

Drives the real pass (_auto_nudge_tick) over two alive sessions with real transcript files and real goal stores, on the
suite's fake clock (the pass takes `now`). SYNTHETIC fixtures only; a PRIVATE synthetic sid pair (the goal-store fixture
rule), their override journals cleaned in the teardown; the state root rebound through jd._rebind_state and `off` written
into its session-hosts."""
import inspect
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
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_c7pin", os.path.join(BIN, "romp-kernel"))
jd = km.jd                                        # the kernel's OWN judge instance: the recorder must land where the walk reads it

SID_A = "c7c0a001-5e55-4a11-8b22-000000000001"   # private to this module (the goal-store fixture rule): a plain working top
SID_B = "c7c0a001-5e55-4a11-8b22-000000000002"   # a stamped top whose dead-man is an hour away (the wake-only branch's other road)
SIDS = (SID_A, SID_B)
NOW = 1_787_900_000
H = 3600
WALK = "_auto_nudge_session"          # the walk's decision read: the caller condition 7 counts
GATE = "_nudge_placement_gate"        # the placement gate's currency re-read on a derive: counted apart


class _FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, sid, body):
        self.sent.append((sid, body))

    def pending_queued(self, sid):
        return []


class _WalkHarness(unittest.TestCase):
    """The real pass over two synthetic sessions, the toggle off, every seam it moves put back by a cleanup registered
    before the first rebind (unittest skips tearDown when setUp raises and runs the cleanups regardless)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)                  # cleanups run last in, first out: the seams go back, then the dir
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in (
            "_alive_sessions", "_wait_for_graph", "_session_flag", "_compacting_now", "_api_error",
            "_session_working", "_interrupt_suppresses_nudge", "_backend_rewind_pending", "_last_state",
            "_session_awaiting", "_turn_romp_injected", "_closer_settled", "_revivers_pending",
            "_pending_ops", "_log_nudge_event", "_push_all", "_mark_views_dirty", "_path_of",
            "_debt_backstop_tick", "_PREV_ALIVE")}
        self.saved_jd = {k: getattr(jd, k) for k in ("parsed_session", "_segs", "plan_units", "load_goals",
                                                     "load_goals_shared_or_fault")}
        self.saved_state = jd.STATE
        self.saved_backend = km.Sessions.backend_for
        self.shared_off_before = jd._SHARED_OFF[0]
        self.walk_stats = {k: (dict(v) if isinstance(v, dict) else v) for k, v in km._NUDGE_WALK_STATS.items()}
        self.gate_stats = dict(km._NUDGE_GATE_STATS)
        self.seen = dict(km._TICK_SEEN)
        self.first = ({k: (list(v) if isinstance(v, list) else v) for k, v in km._NUDGE_WALK_FIRST.items()},
                      km._NUDGE_WALK_FIRST_OPEN[0])
        self.addCleanup(self._restore)
        jd._rebind_state(td)                              # STATE and every dir derived from it, never jd.STATE alone
        jd.GOALDIR.mkdir(parents=True)
        jd.EPIDIR.mkdir(parents=True)
        (td / "session-hosts").write_text("off")          # a root this test minted: no session host may start under it
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear(); jd._SHARED_OFF[0] = False      # the shared cache is on for the test and restored after it
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        km._TICK_SEEN.clear()
        for k, v in list(km._NUDGE_WALK_STATS.items()):
            km._NUDGE_WALK_STATS[k] = {} if isinstance(v, dict) else 0
        km._NUDGE_WALK_FIRST_OPEN[0] = False
        self.fb = _FakeBackend()
        km.Sessions.backend_for = lambda sid: self.fb
        km._wait_for_graph = lambda now, sids: {}
        km._session_flag = lambda sid, flag: False
        km._compacting_now = lambda sid: False
        km._api_error = lambda path: None
        km._session_working = lambda turns: False
        km._interrupt_suppresses_nudge = lambda turns, sid="", **k: False
        km._backend_rewind_pending = lambda sid: False
        km._last_state = lambda sid: ("", 0)
        km._session_awaiting = lambda *a, **k: None
        km._turn_romp_injected = lambda tn: False
        km._closer_settled = lambda *a: True
        km._revivers_pending = lambda *a, **k: ""
        km._pending_ops = {}
        km._log_nudge_event = lambda *a, **k: None
        km._push_all = lambda *a, **k: None
        km._mark_views_dirty = lambda *a, **k: None
        km._debt_backstop_tick = lambda now: None
        km._PREV_ALIVE = set(SIDS)                        # no death transition pending
        # the sessions: real transcript files under the state root (the memo's first keyed file; a missing one never skips)
        self.rows = {}
        for i, sid in enumerate(SIDS):
            p = td / (sid + ".jsonl")
            p.write_text(json.dumps({"type": "user", "uuid": sid[:8], "timestamp": "2026-09-10T00:00:00Z",
                                     "message": {"role": "user", "content": "x"}}) + "\n")
            os.utime(p, (NOW - H, NOW - H))
            self.rows[sid] = {"sid": sid, "path": str(p), "name": ("web", "api")[i], "mtime": NOW - H - 100 * i}
        km._alive_sessions = lambda now, live: [self.rows[s] for s in SIDS]
        km._path_of = lambda sid, now=None: self.rows[sid]["path"] if sid in self.rows else ""
        # the parse: fixture turns recorded in the parse cache under a per-sid generation key, as parsed_session records a
        # parse (the gate keys its memo on that key while the cached turns object is the one the walk holds; a re-parse
        # moves the key, so the gate derives again and pays its currency re-read)
        self.turns = {sid: [{"id": "t1", "ended": True, "end": NOW - 8 * H, "t": NOW - 8 * H - 10, "atoms": []},
                            {"id": "t2", "ended": True, "end": NOW - 7 * H - 100, "t": NOW - 7 * H - 200, "atoms": []}]
                      for sid in SIDS}
        self.parse_gen = dict.fromkeys(SIDS, 0)
        self.parsed = []

        def _parsed(sid, paths, now):
            self.parsed.append(sid)
            sess = {"turns": self.turns[sid]}
            jd._PARSE_CACHE[sid] = (("fixture", self.parse_gen[sid]), sess)
            return sess
        jd.parsed_session = _parsed
        jd._segs = lambda tn, store: []
        jd.plan_units = lambda session, store, lazy_text=None: []
        # the witnesses by execution: recorders on the names the walk resolves at call time, each calling through
        real_shared, real_writer = self.saved_jd["load_goals_shared_or_fault"], self.saved_jd["load_goals"]
        self.calls, self.writer = [], []

        def _shared(sid):
            self.calls.append((sid, inspect.currentframe().f_back.f_code.co_name))
            return real_shared(sid)

        def _load(sid):
            self.writer.append(sid)
            return real_writer(sid)
        jd.load_goals_shared_or_fault = _shared
        jd.load_goals = _load
        self._toggle(False)
        self._seed(SID_A, stamped=False)
        self._seed(SID_B, stamped=True, age=5 * H)

    def _restore(self):
        journals = [jd._overrides_dir() / (sid + ".jsonl") for sid in SIDS]   # under this test's root, resolved before the rebind back
        for k, v in self.saved.items():
            setattr(km, k, v)
        for k, v in self.saved_jd.items():
            setattr(jd, k, v)
        km.Sessions.backend_for = self.saved_backend
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear(); jd._SHARED_OFF[0] = self.shared_off_before
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        km._NUDGE_WALK_STATS.clear(); km._NUDGE_WALK_STATS.update(self.walk_stats)
        km._NUDGE_GATE_STATS.clear(); km._NUDGE_GATE_STATS.update(self.gate_stats)
        km._TICK_SEEN.clear(); km._TICK_SEEN.update(self.seen)
        first, open_ = self.first
        for k, v in first.items():
            if isinstance(v, list):
                km._NUDGE_WALK_FIRST[k][:] = v
            else:
                km._NUDGE_WALK_FIRST[k] = v
        km._NUDGE_WALK_FIRST_OPEN[0] = open_
        for j in journals:
            try:
                j.unlink()
            except OSError:
                pass
        jd._rebind_state(self.saved_state)               # the root goes back the way it was found (the parse entries go with it)

    def _toggle(self, enabled):
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": enabled, "nudged": {}}))
        km._autonudge_cache.clear()

    def _seed(self, sid, stamped, age=5 * H):
        """A working top under `sid`; with `stamped`, carrying a kind=job awaiting stamp `age` old."""
        gid = sid + ":g1"
        at = NOW - age
        why = "the index rebuild is still running; picking the result up when it lands"
        top = {"id": gid, "text": "rebuild the notes-api index", "parentId": None,
               "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": 100, "mt": 100, "log": []}
        if stamped:
            top.update({"awaitingWhy": why, "awaitingAt": at, "awaitingKind": "job"})
            top["log"].append({"ev_t": at, "src": "closer", "kind": "awaiting", "why": why, "awaitKind": "job", "at": at})
        (jd.GOALDIR / (sid + ".json")).write_text(json.dumps({
            "rompUuid": sid, "seq": 1, "placements": {}, "status": {gid: "working"}, "nodes": {gid: top}}))
        km._SESSION_STAMP_CACHE.clear()

    KEYS = ("looks", "parses", "skippedParses", "wakeOnly", "loads")

    def _pass(self, now):
        """One pass over the two sessions: the walk's counter deltas, the placement gate's (served, derived) deltas, and the
        shared-loader calls by caller and sid (`walk`: the decision read; `gateReads`: the gate's currency re-read; `others`:
        any third caller, expected none), the writer loads, and the sids parsed."""
        before = {k: km._NUDGE_WALK_STATS[k] for k in self.KEYS}
        gate0 = dict(km._NUDGE_GATE_STATS)
        self.calls.clear(); self.writer.clear(); self.parsed.clear()
        km._auto_nudge_tick(now, {sid: {"state": ""} for sid in SIDS})
        d = {k: km._NUDGE_WALK_STATS[k] - before[k] for k in self.KEYS}
        d["gate"] = tuple(km._NUDGE_GATE_STATS[k] - gate0[k] for k in ("served", "derived"))
        d["walk"] = {sid: sum(1 for s, c in self.calls if (s, c) == (sid, WALK)) for sid in SIDS}
        d["gateReads"] = {sid: sum(1 for s, c in self.calls if (s, c) == (sid, GATE)) for sid in SIDS}
        d["others"] = [(s[-4:], c) for s, c in self.calls if c not in (WALK, GATE)]
        d["shared"] = len(self.calls)
        d["writer"] = len(self.writer)
        d["parsedSids"] = sorted(self.parsed)
        return d

    def _row(self, sid):
        return km._TICK_SEEN.get(("auto-nudge", sid))


class OneSharedLoadPerAliveSessionPerPass(_WalkHarness):
    def test_exactly_one_on_a_run_and_zero_on_a_skip_by_execution_and_by_the_served_counter(self):
        # (a) the first pass: no memo on record, so every look runs, and every placement gate derives
        p1 = self._pass(NOW)
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"], p1["wakeOnly"]), (2, 2, 0, 2), p1)
        self.assertEqual(p1["walk"], {SID_A: 1, SID_B: 1},
                         "exactly one shared load per alive session on a pass whose look runs (condition 7's floor on a run)")
        self.assertEqual(p1["loads"], 2, "memos.nudgeWalk.loads moves by the walk's loads: one per look that ran")
        self.assertEqual((p1["gateReads"], p1["gate"]), ({SID_A: 1, SID_B: 1}, (0, 2)),
                         "the one other caller is the placement gate's currency re-read, once per derived session (upstream's; "
                         "ruling A's open item, counted apart)")
        self.assertEqual(p1["writer"], 0, "zero plain load_goals in the decision path (the third caller check is in the loop below)")
        for sid in SIDS:
            self.assertIsNotNone(self._row(sid), "a wake-mode memo row stands for %s" % sid[-4:])
        # (b) nothing changed: every look skips, and a skipped look repeats its verdict and needs no data
        p2 = self._pass(NOW + 5)
        self.assertEqual(p2["shared"], 0,
                         "a skipped look takes no shared load: zero per alive session on a pass whose look is skipped (condition 7's floor on a skip)")
        self.assertEqual((p2["looks"], p2["skippedParses"], p2["parses"]), (2, 2, 0), p2)
        self.assertEqual((p2["walk"], p2["gateReads"], p2["loads"], p2["writer"]),
                         ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0, 0), "and the counter does not move")
        # (a) again with the gate SERVED: the ledger is the tenth keyed file, so its move re-evaluates every session once while
        # the parse and the store stand, and the pass takes exactly one loader call per session in total
        os.utime(jd.STATE / "auto-nudge.json", (NOW + 8, NOW + 8))
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["looks"], p3["parses"], p3["skippedParses"]), (2, 2, 0), p3)
        self.assertEqual(p3["walk"], {SID_A: 1, SID_B: 1},
                         "exactly one shared load per alive session on a pass whose look runs (condition 7's floor on a run)")
        self.assertEqual((p3["gateReads"], p3["gate"]), ({SID_A: 0, SID_B: 0}, (2, 0)), "the gate is served: no currency re-read")
        self.assertEqual((p3["shared"], p3["loads"], p3["writer"]), (2, 2, 0),
                         "one loader call per session in total, the counter moves by the same two, no writer load")
        # (b) again
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["skippedParses"], p4["shared"], p4["loads"]), (2, 0, 0),
                         "a skipped look takes no shared load: zero per alive session on a pass whose look is skipped (condition 7's floor on a skip)")
        # one session's transcript moves: its look runs and derives (the parse key moved), the other's skips; per session
        pa = Path(self.rows[SID_A]["path"])
        pa.write_text(pa.read_text() + json.dumps({"type": "user", "uuid": "aaaaaaaa", "timestamp": "2026-09-10T00:01:00Z",
                                                   "message": {"role": "user", "content": "y"}}) + "\n")
        os.utime(pa, (NOW + 18, NOW + 18))
        self.parse_gen[SID_A] += 1
        p5 = self._pass(NOW + 20)
        self.assertEqual((p5["parsedSids"], p5["parses"], p5["skippedParses"]), ([SID_A], 1, 1), p5)
        self.assertEqual(p5["walk"], {SID_A: 1, SID_B: 0}, "per session: one for the look that ran, none for the one that skipped")
        self.assertEqual((p5["gateReads"], p5["gate"]), ({SID_A: 1, SID_B: 0}, (0, 1)), "the moved parse derives once, with its re-read")
        self.assertEqual((p5["loads"], p5["writer"]), (1, 0))
        for name, p in (("p1", p1), ("p2", p2), ("p3", p3), ("p4", p4), ("p5", p5)):
            for sid in SIDS:
                self.assertLessEqual(p["walk"][sid], 1, "%s %s: at most one shared load per alive session per pass (condition 7's ceiling)" % (name, sid[-4:]))
            self.assertEqual(p["others"], [], "%s: the decision read and the gate's re-read are the only callers" % name)
        self.assertEqual(self.fb.sent, [], "nudges off: nothing injected")
        served = km._PERF_STATS.snapshot()["memos"]["nudgeWalk"]
        self.assertEqual(served["loads"], km._NUDGE_WALK_STATS["loads"], "served under memos.nudgeWalk.loads")
        self.assertEqual(served["loads"], 5, "the five loads the five passes made, cumulative")

    def test_a_look_the_state_gates_end_before_its_store_read_takes_no_load(self):
        """The floor is a look that runs to its decision read. A look the state gates end earlier (here `working`: the
        session is still working by the event model) runs, parses, records a file-keyed row and takes no shared load at
        all; the ceiling holds and the counter stays. Its verdict is journaled as a walk gate, a write into the ledger that
        moves every session's key once, so the skip comes on the third pass, with no load on the second either."""
        km._session_working = lambda turns: True
        p1 = self._pass(NOW)
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"]), (2, 2, 0), p1)
        self.assertEqual((p1["shared"], p1["loads"], p1["writer"]), (0, 0, 0), "the gates ended both looks before the store read: no load")
        for sid in SIDS:
            self.assertEqual(self._row(sid)[-1], "working", "the verdict recorded, file-keyed, for %s" % sid[-4:])
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["looks"], p2["parses"], p2["skippedParses"]), (2, 2, 0),
                         "the first pass journaled each verdict as a walk gate (_put_walk_gate, a write-on-change into the ledger, the "
                         "tenth keyed file), so the second pass re-evaluates every session once")
        self.assertEqual((p2["shared"], p2["loads"]), (0, 0), "and takes no load either")
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["skippedParses"], p3["shared"], p3["loads"]), (2, 0, 0), "the gate rows stand: skipped, and still no load")


class TheCountersOneSite(unittest.TestCase):
    def test_the_walk_has_one_shared_load_site_and_the_counter_is_bumped_beside_it(self):
        """A census over the look's own source (the gate decorator unwraps): one shared load, the counter bumped on the line
        after it so the two cannot drift, and the gate around the look reads no store (a skipped look needs no data)."""
        lines = inspect.getsource(km._auto_nudge_session).splitlines()
        at = [i for i, ln in enumerate(lines) if "jd.load_goals_shared_or_fault(" in ln]
        self.assertEqual(len(at), 1, "one shared load in the walk's look: a second call site is a second load per look (condition 7's ceiling)")
        bump = [i for i, ln in enumerate(lines) if '_NUDGE_WALK_STATS["loads"] += 1' in ln]
        self.assertEqual(len(bump), 1, "the counter is bumped once")
        self.assertEqual(bump[0], at[0] + 1, "on the line after the load")
        gated = inspect.getsource(km._nudge_look_gated)
        self.assertNotIn("load_goals", gated, "the gate around the look reads no store: a skipped look takes none")
        self.assertIn("loads", km._NUDGE_WALK_STATS, "the counter is a key of the served block")


if __name__ == "__main__":
    unittest.main()
