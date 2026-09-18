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
  - the planner-placement gate is memoized per session (_nudge_placement_gate, upstream's since the
    2026-09-09 fold, ruling A of slice 3) on the parse cache's key for the session, the identity of the
    shared view object, and the two files the derivation reads beyond them (the sid's episodes log and
    cleared.jsonl, the second the fork's term); an unchanged session costs one shared read and two stats.
    A derivation costs a SECOND shared read: the gate re-reads the shared loader afterwards and caches only
    when the view it derived from is still the current one (upstream's currency check; ruling A lists that
    re-read as open, to be offered upstream, never edited here), so a derive cycle reads the view twice and
    a served cycle once. The delegated-work check keeps its own memo (_nudge_deleg_memo) beside the gate's,
    and the pass evicts both for a sid that leaves the alive set.
The tests count plan_units / _segs / load_goals / load_goals_shared calls per cycle for the four states
the brief names, pin that the gate re-evaluates on each of its inputs and only on them, and that the
shared view never reaches a writer (the frozen guard's poison counter stays at zero). SYNTHETIC fixtures
only; a PRIVATE sid (the goal-store fixture rule); the same harness shape as test_wake_deadman_toggle.

RETIRED (ruling A, slice 3, 2026-09-09): the fork's end-of-walk stale-pin sweep and its four tests
(test_a_gated_session_keeps_its_pin_while_the_parse_is_the_caches_current_one,
test_a_gated_sessions_pin_is_released_when_the_walk_re_parses_it,
test_a_pin_is_released_when_another_reader_re_parsed_a_session_gated_before_its_parse,
test_nothing_cached_is_the_stale_pin_too). Upstream's gate keys on the parse cache's own key rather than
holding the turns object, so a re-parsed transcript misses on its next visit and no stale pin exists; the
fork's plan_hit / plan_miss / plan_bypass / stale counters retired with the sweep (the gate's own pair is
memos.nudgeGate: served / derived)."""
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

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
PEER = "77777777-8888-9999-aaaa-cccccccccccc"    # a local peer the stamped wait can name (WakeGoalUnkeyedExitsNoteTheirLegs)
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
        self.addCleanup(self.td.cleanup)                  # cleanups run last in, first out: the seams go back, then the dir
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
        self.shared_off_before = jd._SHARED_OFF[0]
        # The seams above go back through a cleanup, not tearDown: unittest skips tearDown when setUp raises and runs
        # the cleanups regardless, so a setUp that fails after the rebind below cannot leave jd.STATE naming this
        # test's directory for every later test in the process (conftest's shared-state guard). The 3.10 CI leg of
        # 2026-09-16 turned one KeyError in this setUp into fifteen guard errors that way.
        self.addCleanup(self._restore)
        jd.STATE = td
        jd.GOALDIR = td / "goals"; jd.GOALDIR.mkdir(parents=True)
        jd.EPIDIR = td / "episodes"; jd.EPIDIR.mkdir(parents=True)
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear()
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        # the shared cache's switch and poison counter are process-wide (one judge module per worker):
        # another module's deliberate frozen-write test leaves the counter raised, so the writer check
        # below is a DELTA over this test, and the switch is on for the test and restored after it
        # (saved with the other seams above)
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
        jd.plan_units = lambda session, store, lazy_text=None: _count("plan_units", [])   # lazy_text: upstream's keys-alone call (T396)
        jd.load_goals = lambda sid: _count("load_goals", real_load(sid))
        jd.load_goals_shared = lambda sid: _count("load_goals_shared", real_shared(sid))
        self.turns = [{"id": "t1", "ended": True, "end": NOW - 8 * H, "t": NOW - 8 * H - 10, "atoms": []},
                      {"id": "t2", "ended": True, "end": NOW - 7 * H - 100, "t": NOW - 7 * H - 200, "atoms": []}]

        self.parse_gen = 0                          # bumped by _reparse: the parse cache's key for the sid

        def _parsed(sid, paths, now):
            # as the real function records its parse, (fileset key, session) in jd._PARSE_CACHE: the gate
            # keys its memo on that key (upstream's _nudge_placement_gate), and only while the cached
            # session's turns object is the one the walk holds; a re-parse moves the key (_reparse below)
            sess = {"turns": self.turns}
            jd._PARSE_CACHE[sid] = (("fixture", self.parse_gen), sess)
            return sess
        jd.parsed_session = _parsed
        # the store's own drop, never _PARSE_CACHE.pop(SID, None): the store is an OrderedDict subclass whose slots
        # are (fsid, cut, leaf) tuples, and a bare sid is not a key of its own. Python 3.11+ answers that pop with
        # the default and drops nothing; 3.10's OrderedDict.pop dispatches to the overridden __contains__ and
        # __getitem__ (which read the bare sid as the newest slot) and then to the inherited __delitem__, which
        # raises KeyError on it (the 3.10 CI leg, 2026-09-16)
        jd.parse_cache_drop(SID)
        self.gid = SID + ":g1"

    def _restore(self):
        """Every process-wide seam setUp moved goes back the way it was found: a cleanup registered in setUp before
        the first rebind, so it runs whether setUp finished or not; the temp dir's own cleanup runs after it."""
        journal = jd._overrides_dir() / (SID + ".jsonl")     # under the test's STATE, resolved before it is restored
        for k, v in self.saved.items():
            setattr(km, k, v)
        for k, v in self.saved_jd.items():
            setattr(jd, k, v)
        km.Sessions.backend_for = self.saved_backend
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear()
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        jd.parse_cache_drop(SID)                              # the store's own drop (see setUp)
        jd._SHARED_OFF[0] = self.shared_off_before
        try:
            journal.unlink()
        except OSError:
            pass

    # ── fixtures ──
    def _toggle(self, enabled):
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": enabled, "nudged": {}}))
        km._autonudge_cache.clear()

    def _seed(self, kind="job", age=7 * H, stamped=True, delegated=False, peers=None, sid=None):
        """A working top; with `stamped`, carrying a kind=`kind` awaiting stamp `age` old (naming `peers` when given); with
        `delegated`, its only open leaf is a courier handoff (the all-delegated shape). `sid` seeds another session's store."""
        sid = sid or SID
        gid = sid + ":g1"
        at = NOW - age
        why = "the index rebuild is still running; picking the result up when it lands"
        top = {"id": gid, "text": "rebuild the notes-api index", "parentId": None,
               "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": 100, "mt": 100,
               "log": []}
        if stamped:
            top.update({"awaitingWhy": why, "awaitingAt": at, "awaitingKind": kind})
            if peers:
                top["awaitingPeers"] = list(peers)
            top["log"].append({"ev_t": at, "src": "closer", "kind": "awaiting", "why": why,
                               "awaitKind": kind, "at": at, **({"awaitPeers": list(peers)} if peers else {})})
        nodes = {gid: top}
        if delegated:
            kid = gid + "c"
            nodes[kid] = {"id": kid, "text": "web session: wire the watcher", "parentId": gid,
                          "nodeComplete": False, "blocked": False, "cleared": False, "trail": [],
                          "t": 100, "mt": 100, "log": [],
                          "handoff": {"to": "web", "msgId": "11111111-2222-3333-4444-000000000001"}}
        (jd.GOALDIR / (sid + ".json")).write_text(json.dumps({
            "rompUuid": sid, "seq": 1, "placements": {}, "status": {gid: "working"}, "nodes": nodes}))
        km._SESSION_STAMP_CACHE.clear()

    def _reparse(self):
        """The transcript re-parsed: the same content as a new turns object under a new parse-cache key,
        the way parsed_session records a changed transcript."""
        self.turns = [dict(t) for t in self.turns]
        self.parse_gen += 1

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
        self.assertEqual((c1["load_goals_shared"], c2["load_goals_shared"], c3["load_goals_shared"]), (2, 1, 1),
                         "the decision reads the shared view once per cycle; the derive cycle reads it a second "
                         "time in _nudge_placement_gate's post-derivation currency re-read (upstream's, since the "
                         "2026-09-09 fold)")
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
        self.assertEqual((c1["load_goals_shared"], c2["load_goals_shared"], c3["load_goals_shared"]), (2, 1, 1),
                         "one decision read per cycle, plus the gate's currency re-read on the derive cycle")
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
        self.assertEqual(c1["load_goals_shared"], 2, "the decision read plus the gate's currency re-read after it derived")
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
        # object that could change under an entry, so the gate derives every cycle and caches nothing
        # (_nudge_placement_gate's currency re-read never finds the fresh object to be the loader's
        # current view). The call counts alone cannot tell this from an identity memo that merely
        # misses on a fresh object each cycle (review 2026-09-08): the gate's served / derived pair and
        # the memo's occupancy are what pin the branch (re-aimed at upstream's gate, ruling A, slice 3).
        self._toggle(False)
        before = dict(km._NUDGE_GATE_STATS)
        c1, c2 = self._cycle(), self._cycle(NOW + 5)
        self.assertEqual((c1["plan_units"], c2["plan_units"]), (1, 1))
        d = {k: km._NUDGE_GATE_STATS[k] - before[k] for k in before}
        self.assertEqual((d["derived"], d["served"]), (2, 0),
                         "computed uncached both cycles: neither memoized nor served")
        self.assertNotIn(SID, km._nudge_gate_memo, "no entry holds a private mutable store")
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
        self._reparse()                                  # same content, re-parsed: a new object under a new cache key
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1, "the gate keys on the parse cache's key")
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
        self.assertEqual(self._cycle(NOW + 5)["plan_units"], 1,
                         "plan_units reads cleared.jsonl (_live_anchor_gone): _nudge_placement_gate keys its stat "
                         "beside the episodes log's (the fork's term, ruling A condition 1)")
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
        self.assertEqual(c1["load_goals_shared"], 2, "the decision read, and the gate's currency re-read after it derived")
        self.assertNoWriterSawTheSharedView()


class TheWalkGateMemoOnlyServesTheSharedView(_Base):
    def test_the_entry_is_evicted_when_the_session_leaves_the_alive_set(self):
        self._toggle(False)
        self._seed(stamped=False)
        self._cycle()
        self.assertIn(SID, km._nudge_gate_memo)
        self.assertIn(SID, km._nudge_deleg_memo, "the unstamped top's delegated-work check filled the second memo")
        km._alive_sessions = lambda now, live_map: []
        self._tick(NOW + 5)
        self.assertNotIn(SID, km._nudge_gate_memo, "a sid that left the alive set holds no entry")
        self.assertNotIn(SID, km._nudge_deleg_memo, "in either memo")
        # the walk's own counters (the fork's memos.nudge_walk row, its evict count among them) retired with the
        # 2026-09-15 pull-in for upstream's memos.nudgeWalk (the parse gate's counters, tests/test_nudge_walk_parse_gate.py)


class WakeGoalUnkeyedExitsNoteTheirLegs(_Base):
    """Jobs stage 1 (2026-09-18): the walk noted None under `stampedWait` after every stamped top and under `allDelegated`
    after every delegated top, so those looks could never record a skippable memo whatever the files did (191 unbounded
    looks per 120 s on one box). Both notes are retired: every ending of a stamped wait is a keyed file (the store, the
    postal log, the ledger) or the dead-man instant _wake_goal notes, and the delegated check is pure over the store, whose
    handoff nodes and the postal log both move when a peer returns. The exits of _wake_goal that read no file name their
    own legs instead, so no ladder input goes stale under a memo: `freshFault` (the writer's re-read raised), `refusedWrite`
    (the lift's row, or the wake's ledger record, refused), `peerAlive` (the awaited peers' liveness is the live map),
    `dormantOwner` (the holder's death corroboration reads the registry row). Each test reads memos.nudgeWalk.unboundedBy
    over one tick; the fixtures are the module's, with the toggle off unless the leg is a nudges-on one."""

    def setUp(self):
        super().setUp()
        self._stats_saved = {k: (dict(v) if isinstance(v, dict) else v) for k, v in km._NUDGE_WALK_STATS.items()}
        for k, v in list(km._NUDGE_WALK_STATS.items()):
            km._NUDGE_WALK_STATS[k] = {} if isinstance(v, dict) else 0
        self._seen_saved = dict(km._TICK_SEEN)
        km._TICK_SEEN.clear()
        self.addCleanup(self._restore_walk)

    def _restore_walk(self):
        km._NUDGE_WALK_STATS.update(self._stats_saved)
        km._TICK_SEEN.clear(); km._TICK_SEEN.update(self._seen_saved)

    def _by(self):
        return dict(km._NUDGE_WALK_STATS.get("unboundedBy") or {})

    def test_a_patient_stamped_top_notes_no_unbounded_release(self):
        self._toggle(False)
        self._seed(kind="job", age=5 * H)                        # not due: the dead-man's instant is the look's clock note
        self._tick()
        self.assertEqual(self._by(), {}, "the stamped top noted its dead-man instant and nothing else: no stampedWait")
        self.assertEqual(self._lifts(), []); self.assertEqual(self.fb.sent, [])

    def test_an_all_delegated_top_notes_no_unbounded_release(self):
        self._toggle(False)
        self._seed(stamped=False, delegated=True)
        self._tick()
        self.assertEqual(self._by(), {}, "the delegated check is pure over the store, a keyed file: no allDelegated")
        self.assertEqual(km._auto_nudge_data()["walkGates"][self.gid]["gate"], "all-delegated", "the gate is journaled as before")

    def test_a_fresh_read_fault_on_the_due_lift_notes_freshFault_and_the_healed_pass_lifts(self):
        self._toggle(False)
        self._seed(kind="job", age=7 * H)                        # due
        real = jd.load_goals; calls = [0]
        def failing_once(sid):
            calls[0] += 1
            if calls[0] == 1:
                raise OSError(5, "Input/output error")
            return real(sid)
        jd.load_goals = failing_once
        self._tick()
        self.assertEqual(self._lifts(), [], "the re-read raised: nothing filed off stale evidence")
        self.assertEqual(self._by(), {"freshFault": 1}, "the fault heals with no file write, so the look says it is unbounded")
        self._tick(NOW + 5)
        self.assertEqual(len(self._lifts()), 1, "the healed pass files the lift")
        self.assertEqual(self.fb.sent, [])

    def test_a_refused_lift_row_notes_refusedWrite(self):
        self._toggle(False)
        self._seed(kind="job", age=7 * H)
        with mock.patch.object(jd, "record_verdict", return_value=False):
            self._tick()
        self.assertEqual(self._lifts(), [])
        self.assertEqual(self._by(), {"refusedWrite": 1}, "a refused row writes no file: the next look must retry")

    def test_a_refused_wake_record_notes_refusedWrite_with_nudges_on(self):
        self._toggle(True)
        self._seed(kind="job", age=7 * H)
        with mock.patch.object(km, "_put_nudged", side_effect=OSError(28, "No space left on device")):
            self._tick()
        self.assertEqual(self.fb.sent, [], "nothing sent whose record did not land")
        self.assertEqual(self._by(), {"refusedWrite": 1})

    def test_a_wait_on_live_local_peers_notes_peerAlive(self):
        self._toggle(False)
        self._seed(kind="peer", age=7 * H, peers=[PEER])
        km._auto_nudge_tick(NOW, {SID: {"state": ""}, PEER: {"state": ""}})
        self.assertEqual(self._lifts(), [], "every ending is an observable event: no wake, no lift")
        self.assertEqual(self._by(), {"peerAlive": 1}, "the peers' liveness is in memory, not a keyed file")

    def test_a_dormant_holder_notes_dormantOwner(self):
        # unreachable from the pass today (the alive set is a subset of the live map), pinned at the function so a
        # caller that hands _wake_goal a holder absent from the map can never latch a skippable memo on the registry's word
        self._toggle(False)
        self._seed(kind="job", age=7 * H)
        store = jd.load_goals(SID)
        stamp = km._goal_awaiting_stamp_full(store["nodes"], self.gid)
        km._NUDGE_HORIZON.notes = []
        try:
            with mock.patch.object(km, "_dead_wait_corroborated", return_value=None):
                fired = km._wake_goal(SID, self.gid, stamp, {}, self.turns, store, NOW, self.turns[-1], {}, True)
            self.assertFalse(fired)
            self.assertEqual(km._NUDGE_HORIZON.notes, [None])
        finally:
            km._NUDGE_HORIZON.notes = None
        self.assertEqual(self._by(), {"dormantOwner": 1})


SID2 = "77777777-8888-9999-aaaa-dddddddddddd"    # a second alive session for the skip tests (private to this module)
SID3 = "77777777-8888-9999-aaaa-eeeeeeeeeeee"    # a third, the delegated top of the byte-identity proof


class WakeOnlyLooksSkipOnTheKey(_Base):
    """Jobs stage 1 (2026-09-18): with the auto-nudge gear off, a wake-only look neither skipped nor recorded, so every alive
    session paid the state gates, a parse-cache lookup, the awaiting probe, a shared store view and a goal walk on every
    jobs pass (looks equal to parses, 7353 per 120 s on one box). The wake-only look now records a row under its own mode
    tag, keyed on the same ten files as the full look, and skips while the key stands and no noted instant has come. The
    tests drive the real pass (_auto_nudge_tick) over real transcript files with the toggle off: the second pass skips
    every session and parses nothing (and takes no shared load, so fold ruling A condition 7's exactly-one shared load per
    alive session becomes at most one, zero on a skip); a keyed file of one session releases that session alone; the
    postal log's stat releases a stamped top and a delegated top (the release the design names, since a peer's reply,
    bounce, recall or return is a row of that log); the dead-man still fires on the first pass at or after its instant; a
    skipping pass leaves the goal stores, the ledger and the memo rows byte-identical to a full pass over the same world;
    the boot's first pass with no memo on record parses every session as it always did."""

    def setUp(self):
        super().setUp()
        td = Path(self.td.name)
        self.paths = {}
        for sid in (SID, SID2, SID3):
            p = td / (sid + ".jsonl")
            p.write_text(json.dumps({"type": "user", "uuid": sid[:8], "timestamp": "2026-09-10T00:00:00Z",
                                     "message": {"role": "user", "content": "x"}}) + "\n")
            os.utime(p, (NOW - 3600, NOW - 3600))
            self.paths[sid] = str(p)
        self.rows = {SID: {"sid": SID, "path": self.paths[SID], "name": "web", "mtime": NOW - 3600},
                     SID2: {"sid": SID2, "path": self.paths[SID2], "name": "api", "mtime": NOW - 3700},
                     SID3: {"sid": SID3, "path": self.paths[SID3], "name": "tests", "mtime": NOW - 3800}}
        self.alive = [SID, SID2]
        km._alive_sessions = lambda now, live: [self.rows[s] for s in self.alive]
        real_parsed = jd.parsed_session; self.parsed = []
        jd.parsed_session = lambda sid, paths, now: (self.parsed.append(sid), real_parsed(sid, paths, now))[1]
        self._stats_saved = {k: (dict(v) if isinstance(v, dict) else v) for k, v in km._NUDGE_WALK_STATS.items()}
        for k, v in list(km._NUDGE_WALK_STATS.items()):
            km._NUDGE_WALK_STATS[k] = {} if isinstance(v, dict) else 0
        self._seen_saved = dict(km._TICK_SEEN)
        km._TICK_SEEN.clear()
        self._first_saved = ({k: (list(v) if isinstance(v, list) else v) for k, v in km._NUDGE_WALK_FIRST.items()}, km._NUDGE_WALK_FIRST_OPEN[0])
        km._NUDGE_WALK_FIRST_OPEN[0] = False
        self.addCleanup(self._restore_walk)

    def _restore_walk(self):
        km._NUDGE_WALK_STATS.update(self._stats_saved)
        km._TICK_SEEN.clear(); km._TICK_SEEN.update(self._seen_saved)
        first, open_ = self._first_saved
        for k, v in first.items():
            if isinstance(v, list):
                km._NUDGE_WALK_FIRST[k][:] = v
            else:
                km._NUDGE_WALK_FIRST[k] = v
        km._NUDGE_WALK_FIRST_OPEN[0] = open_
        for sid in (SID2, SID3):
            jd.parse_cache_drop(sid)                              # the real parses of the other two sessions (the harness drops SID's)
            try:
                (jd._overrides_dir() / (sid + ".jsonl")).unlink()
            except OSError:
                pass

    KEYS = ("looks", "parses", "skippedParses", "wakeOnly", "wakeOnlyRecorded", "clockDue", "unbounded")

    def _pass(self, now=NOW):
        """One pass over the alive sessions with the toggle as set: the walk's counter deltas, the shared loads, the writer loads
        and the sids parsed."""
        before = {k: km._NUDGE_WALK_STATS[k] for k in self.KEYS}
        c0 = dict(self.calls); self.parsed.clear()
        km._auto_nudge_tick(now, {s: {"state": ""} for s in self.alive})
        d = {k: km._NUDGE_WALK_STATS[k] - before[k] for k in self.KEYS}
        d["shared"] = self.calls["load_goals_shared"] - c0["load_goals_shared"]
        d["writer"] = self.calls["load_goals"] - c0["load_goals"]
        d["parsedSids"] = list(self.parsed)
        return d

    def _row(self, sid):
        return km._TICK_SEEN.get(("auto-nudge", sid))

    def _store_bytes(self, sid):
        return (jd.GOALDIR / (sid + ".json")).read_bytes()

    def test_the_second_pass_with_the_gear_off_skips_every_session_and_parses_nothing(self):
        self._toggle(False)
        self._seed(stamped=False)                                  # a plain working top
        self._seed(kind="job", age=5 * H, sid=SID2)                # a stamped top whose dead-man is an hour away
        p1 = self._pass()
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"], p1["wakeOnly"]), (2, 2, 0, 2), p1)
        self.assertEqual(sorted(p1["parsedSids"]), sorted([SID, SID2]))
        self.assertGreater(p1["shared"], 0, "the first pass reads the shared view")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["looks"], p2["skippedParses"]), (2, 2), "the second pass skips every session: skippedParses equals looks")
        self.assertEqual((p2["parses"], p2["parsedSids"]), (0, []), "and parses nothing")
        self.assertEqual((p2["shared"], p2["writer"]), (0, 0), "a skip takes no shared load and no writer load (ruling A condition 7: at most one)")
        self.assertEqual(p2["wakeOnly"], 2, "still counted as wake-only looks")
        st = km._session_files_stat(self.rows[SID])
        for sid, flip in ((SID, -1.0), (SID2, NOW - 5 * H + km.AWAITING_DEADMAN_SECS)):
            row = self._row(sid)
            self.assertIsNotNone(row, sid)
            self.assertEqual((row[len(st)], row[-2]), ("wake", flip), "%s: the wake mode tag and the leg's instant" % sid[-4:])
        self.assertEqual(self.fb.sent, []); self.assertEqual(self._lifts(), [])

    def test_a_ten_file_key_change_on_one_session_releases_only_that_session(self):
        self._toggle(False)
        self._seed(stamped=False); self._seed(kind="job", age=5 * H, sid=SID2)
        self._pass(); self._pass(NOW + 5)
        states = jd.STATE / "states" / (SID + ".jsonl")            # the state log, the second keyed file, of SID alone
        states.parent.mkdir(parents=True, exist_ok=True)
        states.write_text(json.dumps({"state": "waiting", "t": NOW}) + "\n")
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"], p3["parsedSids"]), (1, 1, [SID]), "the moved session parses; the other skips")
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["parses"], p4["skippedParses"]), (0, 2), "and the pass after it skips both again")

    def test_the_postal_log_stat_releases_a_stamped_top_and_a_delegated_top(self):
        self._toggle(False)
        self._seed(kind="job", age=5 * H)                          # a stamped top: no None note of its own since stage 1
        self._seed(stamped=False, delegated=True, sid=SID2)        # an all-delegated top: its release is the store and the postal log
        p1 = self._pass()
        self.assertEqual(p1["parses"], 2)
        self.assertEqual(km._auto_nudge_data()["walkGates"][SID2 + ":g1"]["gate"], "all-delegated")
        p2 = self._pass(NOW + 5)                                   # the gate write moved the ledger, one file for the box: both re-evaluate once
        self.assertEqual((p2["parses"], p2["skippedParses"]), (2, 0), p2)
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"]), (0, 2), "the stamped and the delegated top both skip while the files stand")
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "no stampedWait, no allDelegated")
        log = jd.STATE / "timeline" / "messages.jsonl"             # a peer's reply, bounce, recall or return is a row of this log
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as f:
            f.write(json.dumps({"id": "11111111-2222-3333-4444-000000000002", "t": NOW + 12, "from": SID2, "to": SID,
                                "kind": "coordinate", "text": "the watcher is wired"}) + "\n")
        miss0 = (km._tick_seen_report()["byJob"].get("auto-nudge") or {}).get("missBy", {}).get("messages", 0)
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["parses"], p4["skippedParses"], sorted(p4["parsedSids"])), (2, 0, sorted([SID, SID2])),
                         "the postal log's stat releases both tops")
        self.assertEqual((km._tick_seen_report()["byJob"]["auto-nudge"]["missBy"].get("messages", 0)) - miss0, 2, "named as the postal log's position")
        p5 = self._pass(NOW + 20)
        self.assertEqual((p5["parses"], p5["skippedParses"]), (0, 2))

    def test_a_due_dead_man_lifts_on_the_first_pass_at_its_instant_after_skipping(self):
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)                          # due at NOW + 1 h
        due = NOW - 5 * H + km.AWAITING_DEADMAN_SECS
        self.assertEqual(self._pass()["parses"], 1)
        for t in (NOW + 5, NOW + 1800, due - 1):
            d = self._pass(t)
            self.assertEqual((d["parses"], d["skippedParses"], d["writer"]), (0, 1, 0), "before the instant: skipped, nothing filed (%d)" % (t - NOW))
        self.assertEqual(self._lifts(), [])
        d = self._pass(due)
        self.assertEqual((d["parses"], d["clockDue"], d["writer"]), (1, 1, 1), "at the instant the look evaluates and takes the writer's load")
        self.assertEqual(len(self._lifts()), 1, "the lift files on the first pass at or after its instant, as before")
        self.assertIsNone(self._node().get("awaitingWhy"))
        d = self._pass(due + 5)
        self.assertEqual((d["parses"], d["writer"]), (1, 0), "the lift moved the store: one re-evaluation, nothing more to file")
        d = self._pass(due + 10)
        self.assertEqual((d["parses"], d["skippedParses"]), (0, 1), "steady again")
        self.assertEqual(len(self._lifts()), 1); self.assertEqual(self.fb.sent, [])

    def test_a_fresh_read_fault_on_the_due_look_leaves_the_row_unbounded_and_the_next_pass_lifts(self):
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        due = NOW - 5 * H + km.AWAITING_DEADMAN_SECS
        self._pass(); self._pass(NOW + 5)
        real = jd.load_goals; calls = [0]
        def failing_once(sid):
            calls[0] += 1
            if calls[0] == 1:
                raise OSError(5, "Input/output error")
            return real(sid)
        jd.load_goals = failing_once
        d = self._pass(due)
        self.assertEqual((d["parses"], self._lifts()), (1, []), "the due look evaluated; the faulted re-read filed nothing")
        self.assertIsNone(self._row(SID)[-2], "the row is unbounded (freshFault): the next look must evaluate")
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {"freshFault": 1})
        d = self._pass(due + 5)
        self.assertEqual((d["parses"], d["skippedParses"], len(self._lifts())), (1, 0, 1), "the healed pass lifts")

    def test_an_all_delegated_top_skips_while_the_store_stands_and_evaluates_when_it_moves(self):
        self._toggle(False)
        self.alive = [SID]
        self._seed(stamped=False, delegated=True)
        self._pass(); self._pass(NOW + 5)                           # the gate write, then the re-evaluation it costs
        d = self._pass(NOW + 10)
        self.assertEqual((d["parses"], d["skippedParses"]), (0, 1), "the delegated top skips while the store stands")
        self.assertEqual(self._row(SID)[-2], -1.0, "no clock leg: bounded by the key alone")
        p = jd.GOALDIR / (SID + ".json"); store = json.loads(p.read_text())
        store["nodes"][self.gid + "c"]["nodeComplete"] = True      # the peer's return: the courier completes the handoff node
        p.write_text(json.dumps(store)); km._SESSION_STAMP_CACHE.clear()
        d = self._pass(NOW + 15)
        self.assertEqual(d["parses"], 1, "the store moved: the look evaluates")
        self.assertNotIn(self.gid, km._auto_nudge_data().get("walkGates", {}), "the walk reached the goal: its gate is popped")
        self.assertNotIn("allDelegated", km._NUDGE_WALK_STATS["unboundedBy"])

    def test_a_skipping_pass_leaves_every_output_byte_identical_to_a_full_pass(self):
        """The invariant the frames rest on: a skip writes nothing, and a full evaluation over the same world writes nothing new.
        Three sessions (a plain top, a stamped top, a delegated top), the gear off. After the memo settles, one pass that skips
        every look and one pass over the same world with the memo forgotten (the road as it ran before stage 1) leave the goal
        stores, the ledger and the walk's memo rows byte-identical; the placement gate is not consulted on a skip and is served
        on the full pass; the walk's counters differ only in the parse and skip tallies."""
        self._toggle(False)
        self.alive = [SID, SID2, SID3]
        self._seed(stamped=False); self._seed(kind="job", age=5 * H, sid=SID2); self._seed(stamped=False, delegated=True, sid=SID3)
        self._pass(); self._pass(NOW + 5)
        ledger = jd.STATE / "auto-nudge.json"
        def world():
            return {sid: self._store_bytes(sid) for sid in self.alive} | {"ledger": ledger.read_bytes()}
        def rows():
            return {k: tuple(v) for k, v in km._TICK_SEEN.items() if k[0] == "auto-nudge"}
        w2, r2 = world(), rows()
        self.assertEqual(len(r2), 3, "the memo settled for all three")
        gate0 = dict(km._NUDGE_GATE_STATS)
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"], p3["looks"]), (0, 3, 3), "the skipping pass")
        self.assertEqual(world(), w2, "a skip writes nothing: stores and ledger byte-identical")
        self.assertEqual(rows(), r2, "and the rows stand")
        self.assertEqual(dict(km._NUDGE_GATE_STATS), gate0, "the placement gate is not consulted on a skip")
        km._nudge_memos_forget()                                     # the full road over the same world, as before stage 1
        gate0 = dict(km._NUDGE_GATE_STATS)
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["parses"], p4["skippedParses"], p4["looks"]), (3, 0, 3), "the full pass")
        self.assertEqual(world(), w2, "the full evaluation writes nothing new either: byte-identical")
        self.assertEqual(rows(), r2, "and records the same rows: same key, same mode, same instants, same verdicts")
        self.assertEqual(km._NUDGE_GATE_STATS["served"] - gate0["served"], 3, "the full pass serves the placement gate once per session")
        differ = {k for k in self.KEYS if p3[k] != p4[k]}
        self.assertEqual(differ, {"parses", "skippedParses", "wakeOnlyRecorded"},
                         "the counters differ only in what the skip is and the rows it did not need to record: %r vs %r" % (p3, p4))
        self.assertEqual((p3["shared"], p4["shared"]), (0, 3), "zero shared loads on the skipping pass, one per session on the full one")
        self.assertEqual(self.fb.sent, [])

    def test_the_wake_mode_rows_recorded_are_counted_under_memos_nudgeWalk(self):
        """Jobs stage 1: `wakeOnlyRecorded` counts the memo rows wake-only looks recorded, beside `wakeOnly` (the looks) and
        `skippedParses`; with the gear off on a quiet board the rows rise to the alive count and then hold while every look skips."""
        self._toggle(False)
        self._seed(stamped=False); self._seed(kind="job", age=5 * H, sid=SID2)
        p1 = self._pass()
        self.assertEqual((p1["wakeOnly"], p1["wakeOnlyRecorded"]), (2, 2), "the first pass records a wake-mode row per session")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["wakeOnly"], p2["skippedParses"], p2["wakeOnlyRecorded"]), (2, 2, 0), "a skip records nothing")
        self.assertIn("wakeOnlyRecorded", km._PERF_STATS.snapshot()["memos"]["nudgeWalk"], "served under memos.nudgeWalk")
        self._toggle(True)                                       # the ledger moved: every session re-evaluates, in full mode
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["wakeOnly"], p3["wakeOnlyRecorded"]), (2, 0, 0), "full-mode rows are not counted here")
        st = km._session_files_stat(self.rows[SID2])
        self.assertEqual(self._row(SID2)[len(st)], "full", "the stamped top's full look recorded under its own tag")
        self.assertEqual(len(self.fb.sent), 1, "the plain top took the full road's status nudge (r True: no row for it)")

    def test_the_boot_pass_parses_every_session_once_with_no_memo_on_record_and_skips_on_a_persisted_one(self):
        self._toggle(False)
        self._seed(stamped=False); self._seed(kind="job", age=5 * H, sid=SID2)
        km._NUDGE_WALK_FIRST["skipped"][:] = []; km._NUDGE_WALK_FIRST["parsed"][:] = []; km._NUDGE_WALK_FIRST["deferred"] = 0
        km._NUDGE_WALK_FIRST_OPEN[0] = True
        p1 = self._pass()
        self.assertEqual((p1["parses"], p1["skippedParses"]), (2, 0), "no memo on record: the boot's first pass parses every session, as before")
        self.assertEqual((sorted(km._NUDGE_WALK_FIRST["parsed"]), km._NUDGE_WALK_FIRST["skipped"]), (sorted([SID[:8], SID2[:8]]), []))
        self.assertTrue(km._persist_tick_seen(force=True), "the rows persist with the tick memo")
        km._TICK_SEEN.clear()
        self.assertGreaterEqual(km._load_tick_seen(), 2, "and the next kernel loads them")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["parses"], p2["skippedParses"]), (0, 2), "a boot over a persisted wake-mode memo skips the unchanged sessions")
        self.assertEqual(sorted(km._NUDGE_WALK_FIRST["skipped"]), sorted([SID[:8], SID2[:8]]), "and the boot row says which")


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


if __name__ == "__main__":
    unittest.main()
