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

    PLAIN_TOP_TEXT = "ship the notes-api tests"      # the second top's text (`plain`): what its status nudge quotes

    def _seed(self, kind="job", age=7 * H, stamped=True, delegated=False, peers=None, sid=None, plain=False):
        """A working top; with `stamped`, carrying a kind=`kind` awaiting stamp `age` old (naming `peers` when given); with
        `delegated`, its only open leaf is a courier handoff (the all-delegated shape). `sid` seeds another session's store.
        With `plain`, a second top (g2, PLAIN_TOP_TEXT) stands beside the first: plain, working, unstamped, the top the status
        nudge is for (the todo stand-down tests, jobs stage 1 round 2)."""
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
        status = {gid: "working"}
        if plain:
            g2 = sid + ":g2"
            nodes[g2] = {"id": g2, "text": self.PLAIN_TOP_TEXT, "parentId": None, "nodeComplete": False, "blocked": False,
                         "cleared": False, "trail": [], "t": 200, "mt": 200, "log": []}
            status[g2] = "working"
        (jd.GOALDIR / (sid + ".json")).write_text(json.dumps({
            "rompUuid": sid, "seq": 1, "placements": {}, "status": status, "nodes": nodes}))
        km._SESSION_STAMP_CACHE.clear()

    def _todos_on(self):
        """The user-todos feature switch, on (its own file, never the store): _open_user_todos reads [] with it off."""
        (jd.STATE / km.USER_TODOS_SWITCH_FILE).write_text(json.dumps({"enabled": True}))

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

    def test_a_patient_stamped_top_and_a_delegated_top_note_no_unbounded_release_with_nudges_on(self):
        """The retirement's claim in the mode the round-1 tests did not run (kernel-2): with the gear on the same two tops note
        nothing unbounded either. A symmetry pin beside the gear-off pair above, not a staleness guard (see the due twin in
        WakeOnlyLooksSkipOnTheKey for that)."""
        self._toggle(True)
        self._seed(kind="job", age=5 * H)
        self._tick()
        self.assertEqual((self._by(), self.fb.sent), ({}, []), "the stamped top notes its dead-man instant alone")
        (jd.GOALDIR / (SID + ".json")).unlink(); km._SESSION_STAMP_CACHE.clear(); jd._shared_clear()
        self._seed(stamped=False, delegated=True)
        self._tick(NOW + 5)
        self.assertEqual((self._by(), self.fb.sent), ({}, []), "the delegated top notes nothing: pure over the store")
        self.assertEqual(km._auto_nudge_data()["walkGates"][self.gid]["gate"], "all-delegated")

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

    def test_the_status_nudge_stood_down_behind_an_open_user_todo_notes_todoStandDown_with_nudges_on(self):
        """Round 1 of jobs stage 1, HIGH (fresh-1): the goal loop's stand-down exit reads STATE/user-todos.json, a file outside
        the memo's ten, and noted nothing; until the stage the stampedWait and allDelegated notes covered it for a session with
        such a top beside a plain one. The exit notes todoStandDown, so the look records an unbounded row and the pass after the
        todo's dismissal fires the held status nudge (the end-to-end pair in WakeOnlyLooksSkipOnTheKey). Gear ON: the stand-down
        sits below `if wake_only: continue`, so the wake-only road never reaches it."""
        self._toggle(True)
        self._todos_on()
        self._seed(stamped=False)                                # a plain working top, the status nudge's own
        km._add_user_todo(SID, "which index shape do you want")
        self._tick()
        self.assertEqual(self.fb.sent, [], "the open todo explains the idle: the status nudge stands down")
        self.assertEqual(self._by(), {"todoStandDown": 1}, "the todo store is not a keyed file: the exit notes its leg")

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

    def test_a_corroborated_dormant_death_files_the_block_as_a_fire_with_no_note_and_a_faulted_block_write_stays_unbounded(self):
        """Review round 1 (kernel-1): the dormantOwner note sat above the corroboration check, so a corroborated death that filed
        the block and reported a fire also counted an unbounded note. The note sits below the fire now, on both declining exits:
        the uncorroborated death (the test above) and a corroborated one whose block write faulted, which moves no file and must
        not latch a skippable row (moving the note inside the uncorroborated branch alone would have opened that hole)."""
        self._toggle(False)
        self._seed(kind="job", age=7 * H)
        store = jd.load_goals(SID)
        stamp = km._goal_awaiting_stamp_full(store["nodes"], self.gid)
        nudged = {}
        km._NUDGE_HORIZON.notes = []
        try:
            with mock.patch.object(km, "_dead_wait_corroborated", return_value=True), \
                    mock.patch.object(jd, "record_verdict", side_effect=OSError(5, "Input/output error")):
                fired = km._wake_goal(SID, self.gid, stamp, nudged, self.turns, store, NOW, self.turns[-1], {}, True)
            self.assertFalse(fired, "the block's write faulted: nothing filed")
            self.assertEqual(km._NUDGE_HORIZON.notes, [None], "a decline with no file moved: unbounded")
            self.assertEqual(self._by(), {"dormantOwner": 1})
            self.assertFalse(self._node().get("blocked"))
            km._NUDGE_HORIZON.notes = []
            with mock.patch.object(km, "_dead_wait_corroborated", return_value=True):
                fired = km._wake_goal(SID, self.gid, stamp, nudged, self.turns, store, NOW + 5, self.turns[-1], {}, True)
            self.assertTrue(fired, "the corroborated death files the block: a fire")
            self.assertEqual(km._NUDGE_HORIZON.notes, [], "and counts no note")
            self.assertEqual(self._by(), {"dormantOwner": 1}, "unchanged by the fire")
            self.assertTrue(self._node().get("blocked"))
            self.assertEqual(nudged[self.gid].get("deadWait"), True, "the once-per-episode record")
        finally:
            km._NUDGE_HORIZON.notes = None


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

    def test_a_due_dead_man_with_nudges_on_wakes_on_the_first_pass_at_its_instant_after_skipping(self):
        """The gear-ON twin of the due test above, and the load-bearing pin of review round 1 (tests-1, regression-1, kernel-2):
        with the toggle on a stamped top records a bounded row for the first time since the stampedWait note retired, so the
        dead-man instant _wake_goal notes is the only bound on the gear-ON skip. A mutant that notes the instant on the wake-only
        road alone (`if wake_only:` around the note) leaves the rest of the nudge, wake and awaiting suites green while the
        check-in wake never fires; this test fails under it twice over: the first row's flip reads -1.0 where the instant
        belongs, and at the instant the pass skips, (0, 0) != (1, 1). The byte-identity twin below cannot fail for that defect:
        a skip against a full pass over an unchanged world records the same row whether or not the instant was noted."""
        self._toggle(True)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)                          # due at NOW + 1 h
        due = NOW - 5 * H + km.AWAITING_DEADMAN_SECS
        p1 = self._pass()
        self.assertEqual((p1["parses"], p1["wakeOnly"], self.fb.sent), (1, 0, []), "a full look, not due")
        st = km._session_files_stat(self.rows[SID])
        self.assertEqual((self._row(SID)[len(st)], self._row(SID)[-2]), ("full", due), "the full-mode row carries the dead-man instant")
        for t in (NOW + 5, NOW + 1800, due - 1):
            d = self._pass(t)
            self.assertEqual((d["parses"], d["skippedParses"], d["writer"]), (0, 1, 0), "before the instant: skipped, nothing filed (%d)" % (t - NOW))
        self.assertEqual(self.fb.sent, [])
        d = self._pass(due)
        self.assertEqual((d["parses"], d["clockDue"]), (1, 1), "at the instant the look evaluates")
        self.assertEqual(d["writer"], 2, "the fire path's two writer reads: the wake's fresh re-read and the check-in's wording")
        self.assertEqual(len(self._wakes()), 1, "the check-in wake goes out on the first pass at or after its instant")
        self.assertEqual(self._lifts(), [], "nudges on: a wake, not a lift")
        self.assertIsNotNone(self._node().get("awaitingWhy"), "the stamp stands")
        rec = self._ledger_rec()
        self.assertEqual((rec.get("wake"), rec.get("anchor"), rec.get("at")), (True, NOW - 5 * H, due), "the ledger holds the wake record")
        self.assertEqual(self._row(SID)[-2], due, "a look that fires records no row: the pre-fire row stands, its instant past")
        d = self._pass(due + 5)
        self.assertEqual((d["parses"], d["writer"], len(self._wakes())), (1, 0, 1), "the ledger moved: one re-evaluation, the wake in flight, no second fire")
        d = self._pass(due + 10)
        self.assertEqual((d["parses"], d["skippedParses"]), (0, 1), "steady again")

    def test_a_skipping_pass_with_nudges_on_leaves_every_output_byte_identical_to_a_full_pass(self):
        """The gear-ON twin of the byte-identity proof, filed as a LOW regression pin (review round 1: tests-1, regression-1,
        kernel-2). It cannot catch a staleness defect: a skip and a full pass over a STATIC world record the same row whether or
        not a leg noted the input that could move, so an unnoted gear-ON exit passes it while a due wake never fires (the
        refuters proved this by injecting one). What it does pin: with the toggle on a stamped top and a delegated top skip at
        all (the stampedWait and allDelegated notes retired: at the base every gear-on pass over them parsed), and the skip
        writes nothing a full evaluation would. The plain working top stays out of this world: with the gear on it takes the
        status nudge, a fire that records no row. The load-bearing gear-ON pin is the due twin above."""
        self._toggle(True)
        self.alive = [SID2, SID3]
        self._seed(kind="job", age=5 * H, sid=SID2); self._seed(stamped=False, delegated=True, sid=SID3)
        self._pass(); self._pass(NOW + 5)                          # the delegated top's gate write moves the ledger: two settling passes
        ledger = jd.STATE / "auto-nudge.json"
        def world():
            return {sid: self._store_bytes(sid) for sid in self.alive} | {"ledger": ledger.read_bytes()}
        def rows():
            return {k: tuple(v) for k, v in km._TICK_SEEN.items() if k[0] == "auto-nudge"}
        w2, r2 = world(), rows()
        self.assertEqual(len(r2), 2, "the memo settled for both")
        st = km._session_files_stat(self.rows[SID2])
        self.assertEqual({r2[("auto-nudge", sid)][len(st)] for sid in self.alive}, {"full"}, "full-mode rows")
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "no stampedWait, no allDelegated with the gear on either")
        # the rows' instants are deliberately NOT asserted here: the due twin above pins the stamped top's dead-man instant, and
        # this test is the equivalence pin alone, so it stays green under the mutant that test catches (its blindness stated)
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"], p3["looks"]), (0, 2, 2), "the skipping pass")
        self.assertEqual(world(), w2, "a skip writes nothing"); self.assertEqual(rows(), r2, "and the rows stand")
        km._nudge_memos_forget()                                     # the full road over the same world, as before stage 1
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["parses"], p4["skippedParses"], p4["looks"]), (2, 0, 2), "the full pass")
        self.assertEqual(world(), w2, "the full evaluation writes nothing new either: byte-identical")
        self.assertEqual(rows(), r2, "and records the same rows: same key, same mode, same instants, same verdicts")
        self.assertEqual({k for k in self.KEYS if p3[k] != p4[k]}, {"parses", "skippedParses"}, "%r vs %r" % (p3, p4))
        self.assertEqual((p3["shared"], p4["shared"]), (0, 2), "zero shared loads on the skipping pass, one per session on the full one")
        self.assertEqual(self.fb.sent, [])

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

    # ── the user-todo stand-down under the memo (review round 1 of jobs stage 1, HIGH) ──

    def _status_nudge_fires_on_the_pass_after_the_todo_is_dismissed(self):
        """Gear ON, the user-todos switch on, one open todo on the session: the passes before the dismissal parse every time
        (the row is unbounded under todoStandDown) and send nothing; the dashboard's dismiss route (_resolve_user_todo, which
        writes the todo store and its lifecycle log and moves none of the ten keyed files) is followed by ONE status nudge for
        the plain top on the very next pass. At the round-1 head the same world recorded a bounded row after the first pass and
        skipped past the dismissal: the nudge was held until the next box-wide keyed event (a postal, cleared or ledger row
        anywhere on the box) or, on a stamped session, the wake's dead-man instant, about six hours."""
        self._toggle(True)
        self._todos_on()
        self.alive = [SID]
        tid = km._add_user_todo(SID, "which index shape do you want")
        by0 = dict(km._NUDGE_WALK_STATS["unboundedBy"])
        p1 = self._pass()
        self.assertEqual((p1["parses"], self.fb.sent), (1, []), "the first pass evaluates and stands the status nudge down")
        self.assertIsNone(self._row(SID)[-2], "the row is unbounded: the todo store is outside the key")
        self.assertEqual(km._NUDGE_WALK_STATS["unboundedBy"].get("todoStandDown", 0) - by0.get("todoStandDown", 0), 1)
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["parses"], p2["skippedParses"], self.fb.sent), (1, 0, []), "still open: the look evaluates again, no skip")
        self.assertTrue(km._resolve_user_todo(SID, tid, "dismissed"), "the dashboard's dismiss route")
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"]), (1, 0), "the pass right after the dismissal evaluates")
        self.assertEqual(len(self.fb.sent), 1, "and fires the held status nudge, once")
        sid, body = self.fb.sent[0]
        self.assertEqual(sid, SID)
        self.assertIn(self.PLAIN_TOP_TEXT, body, "for the plain top")
        self.assertNotIn(km.AWAITING_BACKSTOP_TEXT, body, "a status nudge, not a wake")
        self.assertEqual(self._lifts(), [])
        p4 = self._pass(NOW + 15)
        self.assertEqual(len(self.fb.sent), 1, "once per genuine stall: the next pass re-fires nothing")

    def test_a_stamped_top_beside_a_plain_top_fires_the_plain_tops_status_nudge_on_the_pass_after_the_todo_is_dismissed(self):
        self._seed(kind="job", age=5 * H, plain=True)              # the stamped top's dead-man is an hour away
        self._status_nudge_fires_on_the_pass_after_the_todo_is_dismissed()
        self.assertIsNotNone(self._node().get("awaitingWhy"), "the stamped top's wait stands: not due")

    def test_a_delegated_top_beside_a_plain_top_fires_the_plain_tops_status_nudge_on_the_pass_after_the_todo_is_dismissed(self):
        self._seed(stamped=False, delegated=True, plain=True)
        self._status_nudge_fires_on_the_pass_after_the_todo_is_dismissed()
        self.assertEqual(km._auto_nudge_data()["walkGates"][self.gid]["gate"], "all-delegated", "the delegated top's gate is journaled")

    def test_a_plain_top_alone_fires_its_status_nudge_on_the_pass_after_the_todo_is_dismissed(self):
        """The pre-existing case the note also closes: with the plain top alone the base recorded a bounded row on the first pass
        (no stamped or delegated top ever noted stampedWait or allDelegated for it), skipped from the second, and never fired
        after the dismissal until a keyed file moved. The same note fixes it."""
        self._seed(stamped=False)
        p = jd.GOALDIR / (SID + ".json"); store = json.loads(p.read_text())
        store["nodes"][self.gid]["text"] = self.PLAIN_TOP_TEXT      # the one top is the plain one the nudge quotes
        p.write_text(json.dumps(store)); km._SESSION_STAMP_CACHE.clear()
        self._status_nudge_fires_on_the_pass_after_the_todo_is_dismissed()

    # ── the wake's ledger writes under the memo (review finds on jobs stage 1) ──

    def _wake_record(self, sid, anchor, fired_at, enabled=False):
        """An in-flight wake record for `sid`'s top, as the nudges-on fire wrote it, in a ledger with the toggle `enabled` (off
        unless said): {wake, anchor, count, lastTurnId, armAtoms, at} with no answeredAt, failed or moot."""
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": enabled, "nudged": {
            sid + ":g1": {"wake": True, "anchor": anchor, "count": 1, "lastTurnId": "t2", "armAtoms": 0, "at": fired_at}}}))
        km._autonudge_cache.clear()

    def _ledger_rec(self):
        return dict(km._auto_nudge_data().get("nudged", {}).get(self.gid) or {})

    def _in_flight_exit_between_the_fire_and_the_response(self, enabled, mode):
        """Review round 1 (tests-2): the exit every in-flight wake takes on each pass between its fire and its response
        (_nudge_response_ready's not-ready answer while the arm turn stands unchanged) went from an always-unbounded look to a
        skippable row, and the three in-flight tests below stub the answer to ready. Pinned by execution in three assertions,
        with the real _nudge_response_ready: (1) the unchanged arm turn records a bounded row and the next pass skips; (2) an
        append to the transcript FILE alone releases the row under missBy.transcript, but the parse (a fixture here) did not grow,
        so the pass re-records the same not-ready exit; (3) growing the parse too, the arm turn past its armed atoms with no
        visible nudge segment, moves the row's bound onto the lost-send instant (the fire time plus LOST_SEND_DEADMAN_SECS), a
        clock note, not a None note. Run with the gear off (mode `wake`) and on (mode `full`): the exit is newly skippable in
        both toggle states."""
        self._toggle(enabled)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        self._wake_record(SID, NOW - 5 * H, NOW - 3600, enabled=enabled)
        st = km._session_files_stat(self.rows[SID])
        def tail():
            return tuple(self._row(SID)[len(st):])
        def miss_transcript():
            return (km._tick_seen_report()["byJob"].get("auto-nudge") or {}).get("missBy", {}).get("transcript", 0)
        p1 = self._pass()
        self.assertEqual(p1["parses"], 1)
        self.assertEqual(tail(), (mode, -1.0, None), "(1) the not-ready exit records a bounded row: the response is the transcript's, a keyed file")
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "no None note on this exit")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["parses"], p2["skippedParses"]), (0, 1), "(1) the next pass skips")
        with open(self.paths[SID], "a") as f:                       # (2) the transcript file grows; the parse fixture does not
            f.write(json.dumps({"type": "assistant", "uuid": "a1", "timestamp": "2026-09-10T00:01:00Z",
                                "message": {"role": "assistant", "content": "still running the rebuild"}}) + "\n")
        m0 = miss_transcript()
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["parses"], p3["skippedParses"]), (1, 0), "(2) the transcript's stat releases the row")
        self.assertEqual(miss_transcript() - m0, 1, "(2) named as the transcript's position")
        self.assertEqual(tail(), (mode, -1.0, None), "(2) the parse did not grow: the same not-ready exit is re-recorded, still bounded")
        self.assertFalse(self._node().get("blocked"), "(2) no outcome leg ran: nothing escalated")
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["parses"], p4["skippedParses"]), (0, 1), "(2) and the pass after it skips again")
        self.turns[-1]["atoms"] = [{"t": NOW - 3000, "type": "assistant"}]   # (3) the arm turn grew past its armed atoms (0)
        self._reparse()
        with open(self.paths[SID], "a") as f:                       # and the file moves with it, as a real transcript would
            f.write(json.dumps({"type": "assistant", "uuid": "a2", "timestamp": "2026-09-10T00:02:00Z",
                                "message": {"role": "assistant", "content": "the rebuild finished"}}) + "\n")
        p5 = self._pass(NOW + 20)
        self.assertEqual((p5["parses"], p5["skippedParses"]), (1, 0), "(3) the key moved: the look evaluates")
        self.assertEqual(self._row(SID)[-2], NOW - 3600 + km.LOST_SEND_DEADMAN_SECS,
                         "(3) past the armed atoms with no visible nudge segment and no turn ended after the fire: the lost-send instant bounds the row")
        self.assertEqual(self._row(SID)[len(st)], mode)
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "(3) a clock note, not a None note")
        p6 = self._pass(NOW + 25)
        self.assertEqual((p6["parses"], p6["skippedParses"]), (0, 1), "(3) the instant is ahead: skipped")
        self.assertEqual((self.fb.sent, self._lifts()), ([], []), "nothing sent, nothing lifted across the six passes")
        self.assertFalse(self._node().get("blocked"))

    def test_an_in_flight_wake_between_its_fire_and_its_response_is_bounded_by_the_transcript_with_the_gear_off(self):
        self._in_flight_exit_between_the_fire_and_the_response(False, "wake")

    def test_an_in_flight_wake_between_its_fire_and_its_response_is_bounded_by_the_transcript_with_the_gear_on(self):
        self._in_flight_exit_between_the_fire_and_the_response(True, "full")

    def test_a_refused_answered_wake_record_notes_refusedWrite_and_the_healed_pass_lands_it(self):
        """Review find: the answered leg of _wake_goal discarded _put_nudged's verdict. A refused record (an unproved ledger
        snapshot: the writer refuses without raising) left answeredAt unrecorded, and with the stampedWait note retired the
        look recorded a bounded row, so the write was never retried until a keyed file moved and the answer stayed unfiled
        for as long. The leg notes refusedWrite: the row is unbounded, the next pass evaluates, the healed writer lands the
        record and the answer files. The filing itself needs no note: a landed ledger write moved the tenth keyed file."""
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        self._wake_record(SID, NOW - 5 * H, NOW - 3600)
        real_put = km._put_nudged; puts = []
        def refusing_once(gid, rec):
            puts.append(dict(rec))
            return False if len(puts) == 1 else real_put(gid, rec)
        real_file = km._file_wake_answer; filings = []
        def landing_nothing_once(sid, gid, now):
            filings.append(now)                       # the same fault episode: the filing's own load or row refused too
            return False if len(filings) == 1 else real_file(sid, gid, now)
        with mock.patch.object(km, "_nudge_response_ready", return_value=(True, {"id": "seg-1", "t": NOW - 1800})), \
                mock.patch.object(km, "_put_nudged", refusing_once), mock.patch.object(km, "_file_wake_answer", landing_nothing_once):
            p1 = self._pass()
            self.assertEqual((p1["parses"], len(puts), filings), (1, 1, [NOW]), "the answered leg ran: one refused record, one filing that landed nothing")
            self.assertNotIn("answeredAt", self._ledger_rec(), "the refused record did not land")
            self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {"refusedWrite": 1}, "the refused write is noted")
            self.assertIsNone(self._row(SID)[-2], "the row is unbounded: the next look must retry")
            p2 = self._pass(NOW + 5)
            self.assertEqual((p2["parses"], p2["skippedParses"], len(puts)), (1, 0, 2), "the next pass evaluates and retries the record")
            self.assertEqual(self._ledger_rec().get("answeredAt"), NOW - 1800, "the healed writer lands answeredAt")
            self.assertEqual(len(filings), 2, "and the answer files")
            rows = [e for e in self._node()["log"] if e.get("kind") == "awaiting" and e.get("src") == "nudge"]
            self.assertEqual(len(rows), 1, "the same-why re-assert landed on the store")
            p3 = self._pass(NOW + 10)
            self.assertEqual(p3["parses"], 1, "the ledger and the store moved under the look: one re-evaluation")
            self.assertEqual(self._row(SID)[-2], NOW - 1800 + km.AWAITING_DEADMAN_SECS, "measured from the answer: the next dead-man is the row's instant")
            p4 = self._pass(NOW + 15)
            self.assertEqual((p4["parses"], p4["skippedParses"]), (0, 1), "steady again")
        self.assertEqual(self.fb.sent, []); self.assertEqual(self._lifts(), [])

    def test_a_refused_moot_stamp_notes_refusedWrite_and_the_healed_pass_lands_it(self):
        """Review find: _mark_nudge_failed's moot path discarded _write_auto_nudge's verdict and returned "moot" anyway. Unlike
        the failed path it writes no store row, so a refused stamp moved no keyed file and the wake's look recorded a bounded
        row: the stamp lived in memory for one pass and the record stayed in flight until an unrelated file moved. The writer's
        site notes refusedWrite: the row is unbounded and the next pass lands the stamp. Bookkeeping (the judge already ruled),
        but a write the next look must retry."""
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        self._wake_record(SID, NOW - 5 * H, NOW - 3600)
        p = jd.GOALDIR / (SID + ".json"); store = json.loads(p.read_text())
        store["nodes"][self.gid]["log"].append({"ev_t": NOW - 2000, "src": "unblocker", "kind": "unblock", "at": NOW - 1800,
                                                "why": "the user answered the question in passing"})   # a real ruling filed after the wake
        p.write_text(json.dumps(store)); km._SESSION_STAMP_CACHE.clear()
        real_write = km._write_auto_nudge; refused = []
        def refusing_the_moot_once(d):
            if not refused and ((d.get("nudged") or {}).get(self.gid) or {}).get("moot"):
                refused.append(dict(d["nudged"][self.gid]))
                return False                          # the unproved-snapshot refusal, as _ledger_write_proved gives it
            return real_write(d)
        with mock.patch.object(km, "_nudge_response_ready", return_value=(True, None)), \
                mock.patch.object(km, "_write_auto_nudge", refusing_the_moot_once):
            p1 = self._pass()
            self.assertEqual((p1["parses"], len(refused)), (1, 1), "the moot ruling's write was refused")
            self.assertNotIn("moot", self._ledger_rec(), "the stamp did not land")
            self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {"refusedWrite": 1}, "the refused write is noted")
            self.assertIsNone(self._row(SID)[-2], "the row is unbounded: the next look must retry")
            p2 = self._pass(NOW + 5)
            self.assertEqual((p2["parses"], p2["skippedParses"]), (1, 0), "the next pass evaluates")
            self.assertTrue(self._ledger_rec().get("moot"), "and the healed writer lands the moot stamp")
            self.assertEqual(len(refused), 1)
            p3 = self._pass(NOW + 10)
            self.assertEqual(p3["parses"], 1, "the ledger moved: one re-evaluation, the anti-loop rule on the moot record")
            p4 = self._pass(NOW + 15)
            self.assertEqual((p4["parses"], p4["skippedParses"]), (0, 1), "steady again")
        self.assertEqual([e for e in self._node()["log"] if e.get("kind") == "block"], [], "moot, not failed: no block")
        self.assertEqual(self.fb.sent, []); self.assertEqual(self._lifts(), [])

    def test_a_refused_failed_stamp_needs_no_note_because_its_look_reports_a_fire_and_records_nothing(self):
        """The failed path beside the moot one carries no note, and the pin says why: _wake_goal reports "failed" as a fire, the
        look returns True, and a look that fires records no memo (a fire moves files), so a refused failed stamp is retried by the
        next look whether or not the block row landed. Here neither the stamp nor the block lands (the same fault episode) and
        the next pass evaluates on the absent row; the healed writer lands both. Moot differs because its look returns False."""
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        self._wake_record(SID, NOW - 5 * H, NOW - 3600)
        real_write = km._write_auto_nudge; refused = []
        def refusing_the_failed_once(d):
            if not refused and ((d.get("nudged") or {}).get(self.gid) or {}).get("failed"):
                refused.append(dict(d["nudged"][self.gid]))
                return False
            return real_write(d)
        real_rv = jd.record_verdict; blocks = []
        def refusing_the_block_once(store, nd, src, kind, *a, **k):
            if (src, kind) == ("nudge", "block"):
                blocks.append(kind)
                if len(blocks) == 1:
                    return False                      # the same fault episode: the row refused, no save, no store move
            return real_rv(store, nd, src, kind, *a, **k)
        with mock.patch.object(km, "_nudge_response_ready", return_value=(True, None)), \
                mock.patch.object(km, "_write_auto_nudge", refusing_the_failed_once), mock.patch.object(jd, "record_verdict", refusing_the_block_once):
            p1 = self._pass()
            self.assertEqual((p1["parses"], len(refused), len(blocks)), (1, 1, 1), "the failed stamp and its block were both refused")
            self.assertNotIn("failed", self._ledger_rec()); self.assertFalse(self._node().get("blocked"))
            self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "no note on this path")
            self.assertIsNone(self._row(SID), "the look reported a fire: no memo row, so nothing to skip on")
            p2 = self._pass(NOW + 5)
            self.assertEqual((p2["parses"], p2["skippedParses"]), (1, 0), "the next pass evaluates on the absent row")
            self.assertTrue(self._ledger_rec().get("failed"), "the healed writer lands the failed stamp")
            self.assertEqual([e["src"] for e in self._node()["log"] if e.get("kind") == "block"], ["nudge"], "and the block lands")
            self.assertTrue(self._node().get("blocked"))
        self.assertEqual(self.fb.sent, [], "gear off: the escalation is a filing, never a message")

    def _judge_writes_between_the_stat_and_the_look(self, change):
        """The writer's re-read in _wake_goal finds a store a concurrent judge pass saved after this pass's stat: `change` edits
        the loaded store, the save lands, and the fresh copy is what the look reads. Once, for SID."""
        real = jd.load_goals; judged = []
        def loading(sid):
            store = real(sid)
            if sid == SID and not judged:
                judged.append(sid)
                change(store)
                jd.rollup_status(store, False); jd.save_goals(sid, store); km._SESSION_STAMP_CACHE.clear()
                return real(sid)
            return store
        jd.load_goals = loading
        return judged

    def test_a_stamp_re_anchored_under_the_due_look_lifts_nothing_and_the_moved_store_releases_the_row(self):
        """Review find: the `_sn is None` exit of the wake-only lift (the fresh store carries the wait, but not at THIS anchor: a
        judge re-asserted it between the pass's stat and the look's re-read) was covered by the retired stampedWait note and had
        no pin. It lifts nothing and notes no leg: the save that moved the anchor is a store write the pass's stat predates, so
        the next pass misses on the store position, evaluates the new stamp and notes its dead-man."""
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        due = NOW - 5 * H + km.AWAITING_DEADMAN_SECS
        self._pass(); self._pass(NOW + 5)
        def re_anchor(store):
            n = store["nodes"][self.gid]
            ok = jd.record_verdict(store, n, "closer", "awaiting", due - 60, why="the index landed; the deploy it queued is still running",
                                   await_kind="job")
            if not ok:
                raise AssertionError("the fixture's re-assert was refused")
        judged = self._judge_writes_between_the_stat_and_the_look(re_anchor)
        d = self._pass(due)
        self.assertEqual((d["parses"], d["clockDue"], judged), (1, 1, [SID]), "the due look evaluated and took the writer's re-read")
        self.assertEqual(self._lifts(), [], "the fresh store carries the wait at a new anchor: nothing lifted")
        self.assertEqual(self._node()["awaitingAt"], due - 60, "the re-anchored stamp stands")
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "the exit notes no leg: the store that moved is a keyed file")
        self.assertEqual(self._row(SID)[-2], -1.0, "bounded by the key alone")
        miss0 = (km._tick_seen_report()["byJob"].get("auto-nudge") or {}).get("missBy", {}).get("store", 0)
        d = self._pass(due + 5)
        self.assertEqual((d["parses"], d["skippedParses"]), (1, 0), "the store moved under the look: the next pass evaluates")
        self.assertEqual(km._tick_seen_report()["byJob"]["auto-nudge"]["missBy"].get("store", 0) - miss0, 1, "named as the store's position")
        self.assertEqual(self._row(SID)[-2], due - 60 + km.AWAITING_DEADMAN_SECS, "the new stamp's dead-man is the row's instant")
        d = self._pass(due + 10)
        self.assertEqual((d["parses"], d["skippedParses"]), (0, 1), "steady again")
        self.assertEqual(self._lifts(), []); self.assertEqual(self.fb.sent, [])

    def test_a_stamp_lifted_under_the_due_look_lifts_nothing_more_and_the_moved_store_releases_the_row(self):
        """The sibling exit three lines above it: the fresh store no longer carries the wait at all (a judge lifted it between the
        stat and the re-read). No second lift, no note, and the judge's save releases the row the same way."""
        self._toggle(False)
        self.alive = [SID]
        self._seed(kind="job", age=5 * H)
        due = NOW - 5 * H + km.AWAITING_DEADMAN_SECS
        self._pass(); self._pass(NOW + 5)
        def lift(store):
            n = store["nodes"][self.gid]
            if not jd.record_verdict(store, n, "closer", "awaiting", due - 60, lift=True, end_ev=due - 60):
                raise AssertionError("the fixture's lift was refused")
        judged = self._judge_writes_between_the_stat_and_the_look(lift)
        d = self._pass(due)
        self.assertEqual((d["parses"], d["clockDue"], judged), (1, 1, [SID]))
        self.assertEqual([e["src"] for e in self._lifts()], ["closer"], "the judge's lift stands alone: the wake filed nothing on it")
        self.assertIsNone(self._node().get("awaitingWhy"))
        self.assertEqual(dict(km._NUDGE_WALK_STATS["unboundedBy"]), {}, "no leg noted: the store that moved is a keyed file")
        self.assertEqual(self._row(SID)[-2], -1.0)
        d = self._pass(due + 5)
        self.assertEqual((d["parses"], d["skippedParses"]), (1, 0), "the store moved under the look: the next pass evaluates the unstamped top")
        d = self._pass(due + 10)
        self.assertEqual((d["parses"], d["skippedParses"]), (0, 1), "steady again")
        self.assertEqual(len(self._lifts()), 1); self.assertEqual(self.fb.sent, [])


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
