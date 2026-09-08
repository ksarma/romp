#!/usr/bin/env python3
"""The auto-nudge walk's cost with the toggle OFF (performance round 5, 2026-09-08).

Upstream 4a3160e3 and 6275443d (PR #936) made the walk run in wake-only mode when auto-nudge is off,
so the awaiting dead-man for kind=job stamps is reachable. The walk then paid, for every alive session
on every pusher cycle, a writer-style jd.load_goals (a parse plus the journal replay) and the
planner-placement gate's jd.plan_units and jd._segs over every turn, before the wake-only branch decided
anything: 30% of the live kernel's GIL samples on a board with 37 sessions. The fix keeps the walk's
control flow, filings and journal exactly as they were and removes the cost:
  - the decision reads the store through jd.load_goals_shared (one parse per store version for every
    reader); the writer's copy is loaded only where a row is filed (_wake_goal's fresh read, and
    _file_wake_answer, which now loads its own copy instead of taking the walk's store);
  - the planner-placement gate is memoized per session on the identity of the parsed turns, the identity
    of the shared store, and the two files the computation reads beyond them (the sid's episodes log and
    cleared.jsonl); an unchanged session costs a shared read and four stats.
The tests count plan_units / _segs / load_goals / load_goals_shared calls per cycle for the four states
the brief names, pin that the gate re-evaluates on each of its inputs and only on them, and that the
shared view never reaches a writer (the frozen guard's poison counter stays at zero). SYNTHETIC fixtures
only; a PRIVATE sid (the goal-store fixture rule); the same harness shape as test_wake_deadman_toggle."""
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
km = load_source("romp_kernel_nwg", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"     # private to this module (the fixture rule)
NOW = 1_787_900_000
H = 3600
COUNTED = ("plan_units", "segs", "load_goals", "load_goals_shared")


class _FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, sid, body):
        self.sent.append((sid, body))

    def pending_queued(self, sid):
        return []


class _Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in (
            "_alive_sessions", "_wait_for_graph", "_session_flag", "_compacting_now", "_api_error",
            "_session_working", "_interrupt_suppresses_nudge", "_backend_rewind_pending", "_last_state",
            "_session_awaiting", "_turn_romp_injected", "_closer_settled", "_revivers_pending",
            "_pending_ops", "_log_nudge_event", "_push_all", "_mark_views_dirty", "_path_of",
            "_debt_backstop_tick", "_PREV_ALIVE")}
        self.saved_jd = {k: getattr(jd, k) for k in ("STATE", "GOALDIR", "EPIDIR", "parsed_session", "_segs",
                                                     "plan_units", "load_goals", "load_goals_shared")}
        self.saved_backend = km.Sessions.backend_for
        jd.STATE = td
        jd.GOALDIR = td / "goals"; jd.GOALDIR.mkdir(parents=True)
        jd.EPIDIR = td / "episodes"; jd.EPIDIR.mkdir(parents=True)
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear()
        getattr(km, "_NUDGE_GATE_MEMO", {}).clear()
        # the shared cache's switch and poison counter are process-wide (one judge module per worker):
        # another module's deliberate frozen-write test leaves the counter raised, so the writer check
        # below is a DELTA over this test, and the switch is on for the test and restored after it
        self.shared_off_before = jd._SHARED_OFF[0]
        jd._SHARED_OFF[0] = False
        self.poisoned_before = jd.shared_store_stats().get("poisoned", 0)
        self.fb = _FakeBackend()
        km.Sessions.backend_for = lambda sid: self.fb
        km._alive_sessions = lambda now, tmux: [{"sid": SID, "path": "/nonexistent.jsonl"}]
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
        km._path_of = lambda sid, now=None: "/nonexistent.jsonl"
        km._debt_backstop_tick = lambda now: None
        km._PREV_ALIVE = {SID}                       # no death transition pending
        # the counted seams: the stubs answer as test_wake_deadman_toggle's do (no units, no segments)
        # and the two loaders are the real ones, wrapped
        self.calls = dict.fromkeys(COUNTED, 0)
        real_load, real_shared = self.saved_jd["load_goals"], self.saved_jd["load_goals_shared"]

        def _count(name, ret):
            self.calls[name] += 1
            return ret
        jd._segs = lambda tn, store: _count("segs", [])
        jd.plan_units = lambda session, store: _count("plan_units", [])
        jd.load_goals = lambda sid: _count("load_goals", real_load(sid))
        jd.load_goals_shared = lambda sid: _count("load_goals_shared", real_shared(sid))
        self.turns = [{"id": "t1", "ended": True, "end": NOW - 8 * H, "t": NOW - 8 * H - 10, "atoms": []},
                      {"id": "t2", "ended": True, "end": NOW - 7 * H - 100, "t": NOW - 7 * H - 200, "atoms": []}]
        jd.parsed_session = lambda sid, paths, now: {"turns": self.turns}
        self.gid = SID + ":g1"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(km, k, v)
        for k, v in self.saved_jd.items():
            setattr(jd, k, v)
        km.Sessions.backend_for = self.saved_backend
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear()
        getattr(km, "_NUDGE_GATE_MEMO", {}).clear()
        jd._SHARED_OFF[0] = self.shared_off_before
        try:
            (jd._overrides_dir() / (SID + ".jsonl")).unlink()
        except OSError:
            pass
        self.td.cleanup()

    # ── fixtures ──
    def _toggle(self, enabled):
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": enabled, "nudged": {}}))
        km._autonudge_cache.clear()

    def _seed(self, kind="job", age=7 * H, stamped=True):
        """A working top; with `stamped`, carrying a kind=`kind` awaiting stamp `age` old."""
        at = NOW - age
        why = "the index rebuild is still running; picking the result up when it lands"
        top = {"id": self.gid, "text": "rebuild the notes-api index", "parentId": None,
               "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": 100, "mt": 100,
               "log": []}
        if stamped:
            top.update({"awaitingWhy": why, "awaitingAt": at, "awaitingKind": kind})
            top["log"].append({"ev_t": at, "src": "closer", "kind": "awaiting", "why": why,
                               "awaitKind": kind, "at": at})
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps({
            "rompUuid": SID, "seq": 1, "placements": {}, "status": {self.gid: "working"},
            "nodes": {self.gid: top}}))
        km._SESSION_STAMP_CACHE.clear()

    def _tick(self, now=NOW):
        km._auto_nudge_tick(now, {SID: {"state": ""}})

    def _cycle(self, now=NOW):
        """One tick; returns the calls it made, by counted seam."""
        before = dict(self.calls)
        self._tick(now)
        return {k: self.calls[k] - before[k] for k in COUNTED}

    def _node(self):
        return json.loads((jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]

    def _lifts(self):
        return [e for e in self._node().get("log") or [] if e.get("kind") == "awaiting" and e.get("lift")]

    def _wakes(self):
        return [b for _s, b in self.fb.sent if km.AWAITING_BACKSTOP_TEXT in b]

    def assertNoWriterSawTheSharedView(self):
        st = jd.shared_store_stats()
        self.assertEqual((st.get("poisoned", 0) - self.poisoned_before, st.get("off")), (0, 0),
                         "a writer received the shared read-only store (the frozen guard fired)")


class WakeOnlyWalkCost(_Base):
    """The toggle OFF: the four session states the brief names, counted per cycle."""

    def test_i_a_session_with_no_stamp_plans_once_and_never_takes_the_writer_load(self):
        self._toggle(False)
        self._seed(stamped=False)
        c1, c2, c3 = self._cycle(), self._cycle(NOW + 5), self._cycle(NOW + 60)
        self.assertEqual((c1["plan_units"], c1["segs"]), (1, len(self.turns)), "the first cycle computes the gate")
        self.assertEqual((c2["plan_units"], c2["segs"], c3["plan_units"], c3["segs"]), (0, 0, 0, 0),
                         "unchanged parse, store, episodes log and cleared.jsonl: the gate is served from the memo")
        self.assertEqual((c1["load_goals"], c2["load_goals"], c3["load_goals"]), (0, 0, 0),
                         "nothing to file: the writer's loader is never taken")
        self.assertEqual((c1["load_goals_shared"], c2["load_goals_shared"], c3["load_goals_shared"]), (1, 1, 1),
                         "the decision reads the shared view once per cycle")
        self.assertEqual(self.fb.sent, [])
        self.assertNoWriterSawTheSharedView()

    def test_ii_a_stamped_session_whose_dead_man_is_not_due_costs_the_same(self):
        self._toggle(False)
        self._seed(kind="job", age=5 * H)
        c1, c2, c3 = self._cycle(), self._cycle(NOW + 5), self._cycle(NOW + 60)
        self.assertEqual((c1["plan_units"], c2["plan_units"], c3["plan_units"]), (1, 0, 0))
        self.assertEqual((c1["segs"], c2["segs"], c3["segs"]), (len(self.turns), 0, 0))
        self.assertEqual((c1["load_goals"], c2["load_goals"], c3["load_goals"]), (0, 0, 0),
                         "still patient: no fresh read, no lift")
        self.assertEqual((c1["load_goals_shared"], c2["load_goals_shared"], c3["load_goals_shared"]), (1, 1, 1))
        self.assertIsNotNone(self._node().get("awaitingWhy"), "the 6h constant stands")
        self.assertEqual(self._lifts(), [])
        self.assertEqual(self.fb.sent, [])
        self.assertNoWriterSawTheSharedView()

    def test_iii_a_due_dead_man_still_files_its_lift_once_on_the_first_cycle(self):
        self._toggle(False)
        self._seed(kind="job", age=7 * H)
        c1 = self._cycle()
        self.assertEqual(len(self._lifts()), 1, "the lift files on the same cycle it always did")
        row = self._lifts()[-1]
        self.assertEqual((row.get("src"), row.get("ev_t")), ("romp", NOW - 7 * H))
        self.assertIsNone(self._node().get("awaitingWhy"))
        self.assertEqual(c1["plan_units"], 1)
        self.assertEqual(c1["load_goals"], 1, "exactly one writer load: _wake_goal's fresh read, which the lift is filed on")
        self.assertEqual(c1["load_goals_shared"], 1)
        self.assertEqual(self.fb.sent, [], "nudges off: nothing injected")
        c2 = self._cycle(NOW + 5)
        self.assertEqual(c2["plan_units"], 1, "the lift moved the store: a new version is new information, the gate recomputes")
        self.assertEqual(c2["load_goals"], 0, "…and there is nothing left to file")
        c3 = self._cycle(NOW + 60)
        self.assertEqual((c3["plan_units"], c3["segs"], c3["load_goals"]), (0, 0, 0), "steady again")
        self.assertEqual(len(self._lifts()), 1, "once per stamp")
        self.assertNoWriterSawTheSharedView()

    def test_a_fallback_store_is_computed_every_cycle_and_never_memoized(self):
        # no store file: load_goals_shared hands through load_goals' private fresh store, a mutable
        # object with a new identity every call, so the gate runs uncached (plan_bypass) as before
        self._toggle(False)
        c1, c2 = self._cycle(), self._cycle(NOW + 5)
        self.assertEqual((c1["plan_units"], c2["plan_units"]), (1, 1))
        self.assertEqual(self.fb.sent, [])


class TheGateReEvaluatesOnItsInputsOnly(_Base):
    def setUp(self):
        super().setUp()
        self._toggle(False)
        self._seed(stamped=False)
        self._cycle()                                    # the memo is filled

    def test_an_unchanged_world_is_served_from_the_memo(self):
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 0)

    def test_a_new_parse_object_recomputes(self):
        self.turns = [dict(t) for t in self.turns]       # same content, a new object: a new parse version
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1)
        self.assertEqual(self._cycle(NOW + 10)["plan_units"], 0)

    def test_a_store_write_recomputes(self):
        p = jd.GOALDIR / (SID + ".json")
        d = json.loads(p.read_text()); d["seq"] = 2
        p.write_text(json.dumps(d))
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1)
        self.assertEqual(self._cycle(NOW + 10)["plan_units"], 0)

    def test_a_cleared_row_recomputes(self):
        with (jd.STATE / "cleared.jsonl").open("a") as f:
            f.write(json.dumps({"id": SID + ":g9", "op": "clear", "t": NOW}) + "\n")
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1, "plan_units reads cleared.jsonl (_live_anchor_gone)")
        self.assertEqual(self._cycle(NOW + 10)["plan_units"], 0)

    def test_an_episode_boundary_recomputes(self):
        with (jd.EPIDIR / (SID + ".jsonl")).open("a") as f:
            f.write(json.dumps({"head": "11111111-2222-3333-4444-555555555555", "fsid": SID, "t": NOW - 60}) + "\n")
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1, "_placed_key reads the episodes log (episode_floor)")
        self.assertEqual(self._cycle(NOW + 10)["plan_units"], 0)

    def test_a_journal_row_recomputes(self):
        # the override journal is part of the store's version: a replayed row is a new shared object
        jd._overrides_dir().mkdir(parents=True, exist_ok=True)
        with (jd._overrides_dir() / (SID + ".jsonl")).open("a") as f:
            f.write(json.dumps({"op": "noop", "t": NOW}) + "\n")
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1)

    def test_a_wall_clock_move_alone_does_not_recompute(self):
        self.assertEqual(self._cycle(NOW + 5 * H)["plan_units"], 0, "no clock in the key")


class ToggleOnUnchanged(_Base):
    def test_iv_the_check_in_fires_once_and_the_gate_is_memoized_the_same_way(self):
        self._toggle(True)
        self._seed(kind="job", age=7 * H)
        c1, c2, c3 = self._cycle(), self._cycle(NOW + 5), self._cycle(NOW + 60)
        self.assertEqual(len(self._wakes()), 1, "nudges on: today's injected check-in, once per stamp episode")
        self.assertIsNotNone(self._node().get("awaitingWhy"), "the check-in is the action; the stamp stands")
        self.assertEqual(self._lifts(), [])
        self.assertEqual((c1["plan_units"], c2["plan_units"], c3["plan_units"]), (1, 0, 0),
                         "the wake writes the ledger, not the store: the gate memo holds")
        self.assertEqual(c1["load_goals"], 2, "the fire path's two writer reads, as before: _wake_goal's fresh "
                                              "read before the send, and _followup_body's to word the check-in; "
                                              "the walk's own decision read is no longer one of them")
        self.assertEqual((c2["load_goals"], c3["load_goals"]), (0, 0))
        self.assertNoWriterSawTheSharedView()

    def test_iv_an_unstamped_top_with_nudges_on_reads_the_shared_view_for_its_decision(self):
        self._toggle(True)
        self._seed(stamped=False)
        c1 = self._cycle()
        self.assertEqual(c1["load_goals_shared"], 1)
        self.assertNoWriterSawTheSharedView()


class TheWalkGateMemoOnlyServesTheSharedView(_Base):
    def test_the_entry_is_evicted_when_the_session_leaves_the_alive_set(self):
        self._toggle(False)
        self._seed(stamped=False)
        self._cycle()
        self.assertIn(SID, km._NUDGE_GATE_MEMO)
        km._alive_sessions = lambda now, tmux: []
        self._tick(NOW + 5)
        self.assertNotIn(SID, km._NUDGE_GATE_MEMO, "a sid that left the alive set holds no entry")


class FileWakeAnswerLoadsItsOwnCopy(_Base):
    def test_the_answer_row_files_on_a_writer_copy_while_a_frozen_view_is_held(self):
        self._toggle(False)
        self._seed(kind="job", age=5 * H)
        frozen = jd.load_goals_shared(SID)
        self.assertIsInstance(frozen, jd.FrozenStore)
        self.assertTrue(km._file_wake_answer(SID, self.gid, NOW), "the same-why re-assert lands")
        rows = [e for e in self._node()["log"] if e.get("kind") == "awaiting" and e.get("src") == "nudge"]
        self.assertEqual(len(rows), 1)
        self.assertNoWriterSawTheSharedView()


class PerfBlock(_Base):
    def test_the_walk_reports_its_counters_under_memos(self):
        snap = km._PERF_STATS.snapshot()
        self.assertIn("nudge_walk", snap["memos"])
        self.assertEqual(set(snap["memos"]["nudge_walk"]),
                         {"walked", "gated", "loads", "shared", "plan_hit", "plan_miss", "plan_bypass",
                          "deleg_hit", "deleg_miss", "lifted", "evict", "entries"})
        for k, v in snap["memos"]["nudge_walk"].items():
            self.assertIsInstance(v, int, k)

    def test_the_counters_move_with_the_walk(self):
        self._toggle(False)
        self._seed(kind="job", age=7 * H)
        before = dict(km._nudge_walk_stats)
        self._cycle(); self._cycle(NOW + 5); self._cycle(NOW + 60)
        d = {k: km._nudge_walk_stats[k] - before[k] for k in before}
        self.assertEqual(d["walked"], 3)
        self.assertEqual(d["gated"], 0, "every gate passed in this fixture")
        self.assertEqual((d["loads"], d["shared"]), (3, 3), "three shared reads, all answered by the cache")
        self.assertEqual((d["plan_miss"], d["plan_hit"]), (2, 1), "computed on the first cycle and after the lift moved the store")
        self.assertEqual(d["lifted"], 1)


if __name__ == "__main__":
    unittest.main()
