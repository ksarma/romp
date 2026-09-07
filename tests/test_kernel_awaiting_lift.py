#!/usr/bin/env python3
"""A goal's ⏳ awaiting stamp is RETIRED once the dispatches it was waiting on return (the user
2026-07-22).

The closer's own lift is bounded to the goals a turn actually WORKED ON (`touched`) — correct for goals
merely riding the menu, but it means a goal the session ABANDONS keeps its stamp forever. Live case: a goal
stamped "waiting on two dispatched investigations" at 12:26; both task-notifications landed by 12:31; the
session went idle at 12:32 and filed its later work under other goals, so no closer pass revisited it. Four
and a half hours later the card still claimed the wait with an empty task list behind it.

_lift_spent_awaiting keys on the EVENT, never a timer: the notification that answered each dispatch is in
the transcript and _scan_bg_tasks already pairs launches to results. It is SELF-SCOPING — it lifts only
when the goal itself dispatched background work by stamp time and all of it came back — so a stamp naming
a CI run, a scheduled check-back or a peer handoff owns no such dispatches, never matches, and keeps its
stamp (those remain the 6h backstop's job, the one case a timer is the only tool for).

Since performance plan 4 (P16) the tick reads in two phases: every rule is decided on the shared
read-only store (jd.load_goals_shared) and written nowhere; the writer's copy (jd.load_goals) is loaded
only when that decision found a lift due, decided on again, and only that second decision is filed. The
LiftGate class counts the two loaders apart.

SYNTHETIC fixtures only: placeholder UUIDs, invented task descriptions.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_awlift", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-999999999999"
BORN, LAUNCH, STAMP, BACK = 100, 200, 300, 400      # goal minted / dispatched / stamped / result landed


def _iso(ep):
    import datetime
    return datetime.datetime.fromtimestamp(ep, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _launch(tid, t):
    """An async Agent dispatch ack — the durable 'this work is now running' record."""
    return {"type": "user", "timestamp": _iso(t), "uuid": "u" + tid, "parentUuid": None,
            "toolUseResult": {"status": "async_launched", "description": "a dispatched investigation"},
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid,
                                                     "content": "launched"}]}}


def _notification(tid, t):
    """The standalone <task-notification> user record that ENDS the wait (the dominant live shape)."""
    body = ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>%s</tool-use-id>\n"
            "<status>completed</status>\n<summary>the investigation finished</summary>\n"
            "</task-notification>" % (tid, tid))
    return {"type": "user", "timestamp": _iso(t), "uuid": "n" + tid, "parentUuid": None,
            "message": {"role": "user", "content": body}}


def _dispatch(tid, t):
    """The assistant tool_use block that DISPATCHED a background agent — the record _seg_of_tool_uses
    resolves a launch's segment from (the ack and the notification alone name no segment)."""
    return {"type": "assistant", "timestamp": _iso(t), "uuid": "d" + tid, "parentUuid": None,
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": tid, "name": "Agent",
                 "input": {"description": "a dispatched investigation", "prompt": "look into it",
                           "run_in_background": True}}]}}


def _monitor(tid, t, timeout_ms=300000):
    """A non-persistent Monitor launch — the watcher shape; expires at t + timeout + grace with no
    terminal record when its CLI dies mid-watch (em._bg_expired)."""
    return {"type": "assistant", "timestamp": _iso(t), "uuid": "m" + tid, "parentUuid": None,
            "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": tid, "name": "Monitor", "input": {"timeout_ms": timeout_ms}}]}}


def _clear_placement_memos():
    """The launch-placement memos key on (sid, tool_use id) and on object identity; the sid and the ids
    repeat across tests, so a positive learned from one test's transcript must not answer the next. The
    shared read-only cache is keyed per store path (a fresh tempdir each test) and compares bytes, so it
    cannot serve a stale store; cleared anyway, with its off switch lifted, so no test starts poisoned."""
    km._task_seg_cache.clear(); km._BG_TOPS_CACHE.clear(); km._PLACEMENT_IDX.clear()
    km.jd._shared_clear()


class AwaitingLift(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in ("_alive_sessions", "_mark_views_dirty")}
        self.saved_jd = (km.jd.STATE, km.jd.GOALDIR)
        km.jd.STATE = td
        km.jd.GOALDIR = td / "goals"
        km.jd.GOALDIR.mkdir(parents=True)
        self.path = str(td / (SID + ".jsonl"))
        km._alive_sessions = lambda now, tmux: [{"sid": SID, "path": self.path}]
        km._mark_views_dirty = lambda *a, **k: None
        km._SESSION_STAMP_CACHE.clear()
        km._lift_seen.clear()          # stores are re-seeded in place under recycled tempdir inodes
        km._bgall_cache.clear()
        km._bgtasks_cache.clear()
        _clear_placement_memos()
        self.gid = SID + ":g1"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(km, k, v)
        km.jd.STATE, km.jd.GOALDIR = self.saved_jd
        km._SESSION_STAMP_CACHE.clear(); km._lift_seen.clear(); km._bgall_cache.clear(); km._bgtasks_cache.clear()
        _clear_placement_memos()
        self.td.cleanup()

    def _transcript(self, recs):
        with open(self.path, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        km._bgall_cache.clear(); km._bgtasks_cache.clear()

    def _seed(self, why="waiting on two dispatched investigations; will act when they return",
              born=BORN, anchor=STAMP, written=None, kind=None):
        """`anchor` is awaitingAt (the audited turn's TRIGGER time); `written` is when the closer actually
        wrote the verdict (its `at`), which defaults to the anchor for the pre-2026-07-27 fixture shape."""
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": False, "trail": [], "t": born, "mt": born,
              "awaitingWhy": why, "awaitingAt": anchor,
              **({"awaitingKind": kind} if kind else {}),
              "log": [{"ev_t": anchor, "src": "closer", "kind": "awaiting", "why": why,
                       **({"awaitKind": kind} if kind else {}),
                       "at": anchor if written is None else written}]}
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))

    def _tick(self, now=BACK + 100):
        km._lift_spent_awaiting(now, {SID: {"state": ""}})

    def _stamp(self):
        nodes = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"]
        return nodes[self.gid].get("awaitingWhy") or None

    # ---- the bug ----
    def test_both_dispatches_returned_lifts_the_stamp(self):
        self._transcript([_launch("t1", LAUNCH), _launch("t2", LAUNCH + 5),
                          _notification("t1", BACK), _notification("t2", BACK + 5)])
        self._seed()
        self.assertIsNotNone(self._stamp(), "precondition: the goal starts stamped")
        self._tick()
        self.assertIsNone(self._stamp(), "every dispatch came back → the wait is over")

    def test_one_still_running_keeps_the_stamp(self):
        self._transcript([_launch("t1", LAUNCH), _launch("t2", LAUNCH + 5),
                          _notification("t1", BACK)])          # t2 never reported
        self._seed()
        self._tick()
        self.assertIsNotNone(self._stamp(), "one dispatch is still out → still genuinely awaiting")

    # ---- kind=job: the watcher is the CARRIER, not the wait (the user 2026-08-15) ----
    def test_a_job_stamps_expired_watcher_does_not_lift_it(self):
        # the observed slurm shape: a watcher armed over an external job dies with a restart (no
        # terminal record, expires past its deadline) — the JOB may still be running, so the stamp
        # stands; the 6h wake is the backstop, per the lift's own design note
        self._transcript([_monitor("t1", LAUNCH)])   # deadline LAUNCH+300s; no terminal record
        self._seed(why="slurm 4821 regenerating the parts; verifies when done", kind="job")
        self._tick(now=LAUNCH + 1000)                # well past deadline + grace → expired
        self.assertIsNotNone(self._stamp(), "a dead watcher is not the external job returning")

    def test_the_same_expired_watcher_lifts_a_kindless_stamp_as_before(self):
        # the legacy trade stands for untyped stamps: expiry counts as returned (the pre-enum rule,
        # 'the awaiting-stamp lift must not wait forever on a dead monitor')
        self._transcript([_monitor("t1", LAUNCH)])
        self._seed(why="watching the long sweep")
        self._tick(now=LAUNCH + 1000)
        self.assertIsNone(self._stamp(), "kindless keeps the pre-enum expiry behavior")

    def test_a_job_stamps_real_terminal_record_still_lifts(self):
        # the watcher genuinely returned and reported — that IS the deciding event, job kind or not
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(why="slurm 4821 regenerating the parts", kind="job")
        self._tick()
        self.assertIsNone(self._stamp(), "a real terminal record ends the wait for every kind")

    # ---- self-scoping: the other awaiting flavors are untouched ----
    def test_a_return_newer_than_the_last_lift_lifts_despite_a_late_reassert(self):
        # the 2026-08-25 audit's watcher shape: assert → lift → the watch re-armed and RETURNED →
        # the closer, auditing a segment cut BEFORE that return, re-asserted seconds after it. The
        # old stand-down read the WRITE time as the epistemic boundary and blocked the lift forever;
        # the discriminator is the EVIDENCE against the last lift — a return newer than the last
        # lift was never ruled on, whatever the re-assert's arrival says.
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        why = "the re-armed watcher; reports when it lands"
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN,
              "awaitingWhy": why, "awaitingAt": STAMP, "log": [
                  {"ev_t": STAMP, "src": "closer", "kind": "awaiting", "why": why, "at": STAMP + 10},
                  {"ev_t": STAMP, "src": "romp", "kind": "awaiting", "lift": True, "at": STAMP + 20},
                  {"ev_t": STAMP, "src": "closer", "kind": "awaiting", "why": why,
                   "at": BACK + 10}]}                 # the live shape: a SAME-ANCHOR re-assert (two closer
        #                                               rows on one ev_t), written AFTER the 400 return
        #                                               its audit segment never saw
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps({
            "rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))
        self._tick()
        self.assertIsNone(self._stamp(),
                          "the return (endT %d) postdates the last lift (%d) — new information lifts"
                          % (BACK, STAMP + 20))

    def test_a_wait_with_no_dispatches_of_its_own_is_untouched(self):
        # a CI run / scheduled check-back / peer handoff: nothing was dispatched, so nothing can be paired
        self._transcript([])
        self._seed(why="waiting on the release pipeline to go green, then will tag")
        self._tick()
        self.assertIsNotNone(self._stamp(), "no dispatches to evidence → the stamp is not ours to lift")

    def test_a_dispatch_launched_after_the_stamp_is_not_owned(self):
        # it cannot be what the stamp was explaining, so its return says nothing about that wait
        self._transcript([_launch("t9", STAMP + 50), _notification("t9", STAMP + 90)])
        self._seed()
        self._tick()
        self.assertIsNotNone(self._stamp(), "only dispatches at/before the stamp can retire it")

    def test_a_dispatch_from_before_the_goal_existed_is_not_owned(self):
        self._transcript([_launch("t0", BORN - 50), _notification("t0", BORN - 10)])
        self._seed()
        self._tick()
        self.assertIsNotNone(self._stamp(), "a task predating the goal is another goal's business")

    # ---- guards ----
    def test_a_dormant_session_is_skipped(self):
        # its tasks died with its CLI; the death notice is the truth there, never a lift
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        km._lift_spent_awaiting(BACK + 100, {})        # no live snapshot for the sid
        self.assertIsNotNone(self._stamp(), "a dormant session is never ruled on here")

    def test_an_unstamped_goal_is_left_alone(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN}
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))
        self._tick()
        self.assertIsNone(self._stamp())

    def test_the_lift_is_recorded_in_the_verdict_log(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        self._tick()
        log = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]["log"]
        self.assertTrue(any(e.get("kind") == "awaiting" and e.get("lift") for e in log),
                        "the retraction is journalled like any other verdict, not a silent field wipe")

    # ---- ownership scoping (the user 2026-07-27): placement is authoritative when the judge has spoken ----
    def test_a_return_placed_under_another_card_never_lifts_this_stamp(self):
        # unrelated returns were lifting CI-wait stamps (one lifted the same minute it was re-asserted):
        # the bare time window claimed every task the session launched in [born, at]
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(why="waiting on the release pipeline to go green, then will tag")
        saved = km._bg_placed_tops
        km._bg_placed_tops = lambda sid, path, tids, store=None: {"t1": SID + ":gOTHER"}
        try:
            self._tick()
        finally:
            km._bg_placed_tops = saved
        self.assertIsNotNone(self._stamp(), "another card's dispatch can never retire this wait")

    def test_the_goals_own_placed_dispatch_still_lifts(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        saved = km._bg_placed_tops
        km._bg_placed_tops = lambda sid, path, tids, store=None: {"t1": self.gid}
        try:
            self._tick()
        finally:
            km._bg_placed_tops = saved
        self.assertIsNone(self._stamp(), "the goal's own thread returned everything → the wait is over")

    def test_a_later_running_dispatch_on_the_same_thread_keeps_the_stamp(self):
        # placed under the same top AFTER the stamp: its flight keeps the wait honest, so no lift
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK), _launch("t2", STAMP + 50)])
        self._seed()
        saved = km._bg_placed_tops
        km._bg_placed_tops = lambda sid, path, tids, store=None: {"t1": self.gid, "t2": self.gid}
        try:
            self._tick()
        finally:
            km._bg_placed_tops = saved
        self.assertIsNotNone(self._stamp(), "the thread's own newer dispatch is still out")

    # ---- rolled-up stamps (the user 2026-07-27): frozen invisible, so retire them on the record ----
    def test_a_rolled_up_stamp_is_lifted_and_only_once(self):
        # the roll-down froze a stamped node under a resolved ancestor — every reader skips rolledUp,
        # so the stamp could neither show nor retire. The sweep lifts it, diary-guarded against re-fire.
        self._transcript([])
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": True,
              "blocked": False, "cleared": False, "rolledUp": True, "trail": [], "t": BORN, "mt": BORN,
              "awaitingWhy": "a wait the roll-down froze", "awaitingAt": STAMP,
              "log": [{"ev_t": STAMP, "src": "closer", "kind": "awaiting",
                       "why": "a wait the roll-down froze", "at": STAMP}]}
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))
        self._tick()
        log = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]["log"]
        self.assertEqual(len([e for e in log if e.get("kind") == "awaiting" and e.get("lift")]), 1,
                         "the frozen stamp is retired, on the record")
        self._tick()
        log2 = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]["log"]
        self.assertEqual(len([e for e in log2 if e.get("kind") == "awaiting" and e.get("lift")]), 1,
                         "diary-guarded: the sweep never re-lifts")

    # ---- the collapsed window (the user 2026-07-27): mint and stamp in the SAME turn ----
    # awaitingAt is the audited turn's TRIGGER, but a turn dispatches partway through, always after it.
    # When that turn also MINTED the goal, born == awaitingAt and [born, awaitingAt] is a single instant:
    # the fallback matched nothing, so this whole path was dead for the goals it exists to serve. The
    # bound is the stamp's WRITE time, which is after every launch the closer could have audited.
    def test_a_same_turn_mint_and_stamp_still_owns_its_mid_turn_dispatch(self):
        self._transcript([_launch("t1", STAMP + 20), _notification("t1", STAMP + 60)])
        self._seed(born=STAMP, anchor=STAMP, written=STAMP + 90)   # one turn: trigger STAMP, closed later
        self.assertIsNotNone(self._stamp(), "precondition: the goal starts stamped")
        self._tick(now=STAMP + 200)
        self.assertIsNone(self._stamp(),
                          "the dispatch was launched inside the very turn the stamp explains → owned, "
                          "and it came back")

    def test_a_same_turn_dispatch_still_running_keeps_the_stamp(self):
        # the widened bound must not lift a wait that is genuinely still out
        self._transcript([_launch("t1", STAMP + 20)])              # never reported
        self._seed(born=STAMP, anchor=STAMP, written=STAMP + 90)
        self._tick(now=STAMP + 200)
        self.assertIsNotNone(self._stamp(), "its own dispatch is still in flight")

    def test_a_dispatch_after_the_stamp_was_written_is_still_not_owned(self):
        # the bound moved to the WRITE time, not to infinity: a launch the closer could not have seen
        # belongs to a later turn and says nothing about this wait
        self._transcript([_launch("t9", STAMP + 150), _notification("t9", STAMP + 180)])
        self._seed(born=STAMP, anchor=STAMP, written=STAMP + 90)
        self._tick(now=STAMP + 300)
        self.assertIsNotNone(self._stamp(), "launched after the stamp was written → a later turn's work")

    def test_written_at_prefers_the_newest_assertion_and_ignores_lifts(self):
        why = "waiting on a dispatched investigation"
        nd = {"awaitingAt": STAMP,
              "log": [{"ev_t": STAMP, "kind": "awaiting", "why": why, "at": STAMP + 10},
                      {"ev_t": STAMP, "kind": "awaiting", "why": why, "at": STAMP + 90},
                      {"ev_t": STAMP, "kind": "awaiting", "lift": True, "at": STAMP + 500},
                      {"ev_t": STAMP, "kind": "done", "at": STAMP + 900}]}
        self.assertEqual(km._stamp_written_at(nd), STAMP + 90,
                         "the newest ASSERTION bounds ownership; a lift retracts a wait, never asserts one")

    def test_written_at_floors_at_the_anchor_for_a_legacy_record(self):
        self.assertEqual(km._stamp_written_at({"awaitingAt": STAMP, "log": []}), STAMP,
                         "no journalled write time → the old anchor bound, unchanged")
        self.assertEqual(km._stamp_written_at({"awaitingAt": STAMP}), STAMP, "no log at all is safe")

    # ---- the lift's EVIDENCE time (the user 2026-08-06): the stamp's anchor, never wall-clock ----
    # The fold reads a node's diary in (ev_t, at) order, and a closer assert carries its audited TURN's
    # trigger — always older than the moment a lift fires. So a lift stamped `now` outranked every assert
    # the closer could still file on that segment, permanently: a session relaunched its watcher seconds
    # after a lift, the closer re-asserted the wait three times over the next two minutes, and the fold
    # discarded all three. The card sat in Working with no awaiting box and no spin (its session idle), its
    # live watcher demoted to a background-process chip, and its nudge exemption gone.
    def test_the_lift_is_stamped_at_the_anchor_not_wall_clock(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        self._tick(now=BACK + 5000)
        log = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]["log"]
        lift = [e for e in log if e.get("kind") == "awaiting" and e.get("lift")][0]
        self.assertEqual(lift["ev_t"], STAMP,
                         "the lift retracts the wait it LOOKED at, so it carries that stamp's anchor")
        self.assertNotEqual(lift["ev_t"], BACK + 5000, "never the tick's wall clock")

    def test_a_closer_reassert_filed_after_the_lift_restores_the_stamp(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        self._tick()
        self.assertIsNone(self._stamp(), "precondition: the returned dispatch lifted the wait")
        # the session relaunches its watcher and the closer, auditing the SAME turn, says the wait is on
        store = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())
        nd = store["nodes"][self.gid]
        again = "the relaunched watcher on the two open PRs; it deploys once they merge"
        self.assertTrue(km.jd.record_verdict(store, nd, "closer", "awaiting", STAMP, why=again),
                        "the closer's re-assert is allowed to land")
        self.assertEqual(km.jd._fold_node(nd)["awaitingWhy"], again,
                         "the newest RULING wins: an assert filed after the lift puts the stamp back")
        self.assertEqual(km._goal_awaiting_stamp(store["nodes"], self.gid), again,
                         "so the card wears its awaiting box again, and keeps its nudge exemption")

    def test_the_lift_still_wins_when_nothing_is_filed_after_it(self):
        # the ordinary case is unchanged: nobody re-asserts, so the retraction stands
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(anchor=STAMP, written=STAMP + 10)
        self._tick()
        store = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())
        nd = store["nodes"][self.gid]
        self.assertIsNone(km.jd._fold_node(nd)["awaitingWhy"], "the wait is over and stays over")
        self.assertIsNone(km._goal_awaiting_stamp(store["nodes"], self.gid))

    def test_running_only_scan_still_hides_returned_tasks(self):
        # the want_all split must not change the existing running-only view
        self._transcript([_launch("t1", LAUNCH), _launch("t2", LAUNCH + 5), _notification("t1", BACK)])
        running = km._scan_bg_tasks(self.path)
        self.assertEqual([t["id"] for t in running], ["t2"])
        every = km._scan_bg_tasks(self.path, want_all=True)
        self.assertEqual(sorted(t["id"] for t in every), ["t1", "t2"])
        self.assertEqual({t["id"]: t["status"] for t in every}["t1"], "completed")

    # ---- a return the stamping judge already saw cannot end the wait (2026-08-16) ----
    def test_scan_records_when_the_result_landed(self):
        # the substrate: endT is the notification record's transcript time, the lift's evidence
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        every = km._scan_bg_tasks(self.path, want_all=True)
        self.assertEqual(int(every[0].get("endT") or 0), BACK)

    def test_returns_the_stamp_already_knew_do_not_lift_it(self):
        # the incident: a stamp about EXTERNAL work (cluster captures due hours later) was written
        # while the goal's only local dispatch had returned HOURS earlier, in a turn the stamping
        # judge had long since audited — the all-returned test was instantly true and the stamp
        # lifted the same minute it was written, whereupon the lift row mooted the nudge-failure
        # evaluation and the card idled in Working with no reviver left. A return that predates the
        # stamp's ANCHOR (the audited turn's trigger) is evidence the judge stamped WITH; only a
        # return past the anchor can be the event the stamp waited on. (Mid-turn and audit-lag
        # returns — after the anchor, before the write — keep lifting, per the tests above.)
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(why="waiting on the four cluster captures landing overnight",
                   anchor=BACK + 80, written=BACK + 100)   # stamped well after the return landed
        self._tick(now=BACK + 500)
        self.assertIsNotNone(self._stamp(),
                             "a pre-anchor return can't end the wait — the 6h wake owns this one")

    def test_a_lift_drops_the_goals_spent_nudge_record(self):
        # the lift is NEW INFORMATION for the escalation ladder: an idle session never produces the
        # genuine turn the ledger's arm-key dedup waits for, so a latched (failed/moot) record would
        # otherwise silence nudges on this goal forever — erase it with the stamp (2026-08-16)
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed()
        km._mark_auto_nudged(self.gid, "SOME-ARM-TURN", 3, at=BACK - 50)
        d = dict(km._auto_nudge_data())
        n = dict(d.get("nudged", {}))
        n[self.gid] = dict(n[self.gid], moot=True)      # the latch the incident carried
        d["nudged"] = n
        km._write_auto_nudge(d)
        self._tick()
        self.assertIsNone(self._stamp(), "precondition: this lift lands")
        self.assertNotIn(self.gid, km._auto_nudge_data().get("nudged", {}),
                         "the lift erases the spent record so the ladder can re-engage")


class RestartReconcile(unittest.TestCase):
    """Restart orphans (the user 2026-08-24): a kernel/backend restart kills tracked subagents and
    workflows WITH the claude process — the terminal record never lands, so the transcript pairing
    shows them running forever and the awaiting-agents stamp orphaned (~16h over an EMPTY registry).
    The reconciliation is event-keyed: the backend's lifecycle set (present-but-empty is
    authoritative) names what is actually alive, and a transcript-"running" task absent from it
    died with its process — its return event IS the backend's (re)spawn. SYNTHETIC fixtures."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in ("_alive_sessions", "_mark_views_dirty", "_sdk_spawned_at")}
        self.saved_jd = (km.jd.STATE, km.jd.GOALDIR)
        km.jd.STATE = td
        km.jd.GOALDIR = td / "goals"
        km.jd.GOALDIR.mkdir(parents=True)
        self.path = str(td / (SID + ".jsonl"))
        km._alive_sessions = lambda now, tmux: [{"sid": SID, "path": self.path}]
        km._mark_views_dirty = lambda *a, **k: None
        km._sdk_spawned_at = lambda sid: self.spawn      # the CLI epoch — the restart moment
        self.spawn = BACK                                # default: the backend respawned after the stamp
        km._SESSION_STAMP_CACHE.clear(); km._lift_seen.clear(); km._bgall_cache.clear(); km._bgtasks_cache.clear()
        _clear_placement_memos()
        self.gid = SID + ":g1"

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(km, k, v)
        km.jd.STATE, km.jd.GOALDIR = self.saved_jd
        km._SESSION_STAMP_CACHE.clear(); km._lift_seen.clear(); km._bgall_cache.clear(); km._bgtasks_cache.clear()
        _clear_placement_memos()
        self.td.cleanup()

    def _transcript(self, recs):
        with open(self.path, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        km._bgall_cache.clear(); km._bgtasks_cache.clear()

    def _seed(self, kind, why="waiting on a dispatched investigation", anchor=STAMP, written=None):
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN,
              "awaitingWhy": why, "awaitingAt": anchor,
              **({"awaitingKind": kind} if kind else {}),
              "log": [{"ev_t": anchor, "src": "closer", "kind": "awaiting", "why": why,
                       **({"awaitKind": kind} if kind else {}), "at": anchor if written is None else written}]}
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))

    def _stamp(self):
        nodes = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"]
        return nodes[self.gid].get("awaitingWhy") or None

    def _tick(self, snap, now=BACK + 100):
        km._lift_spent_awaiting(now, {SID: snap})

    def test_a_task_that_vanished_across_a_restart_retires_the_stamp(self):
        # the DoD case: a bgTasks entry that vanishes across a simulated restart retires the mark.
        # The launch is in the transcript, its notification never lands (killed with the process),
        # and the respawned backend's lifecycle set is PRESENT and does not know the task.
        self._transcript([_launch("t-restart-1", LAUNCH)])
        self._seed("task")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp(), "the vanished task returned AT the respawn — stamp lifted")

    def test_no_lifecycle_set_means_no_reconciliation(self):
        # a tmux CLI (or an SDK gap mid-reattach) carries no set: registry-absent is NOT evidence —
        # the transcript-running task keeps the wait honest exactly as before
        self._transcript([_launch("t-restart-2", LAUNCH)])
        self._seed("task")
        self._tick({"state": ""})
        self.assertIsNotNone(self._stamp(), "no authoritative set -> the old conservative read holds")

    def test_a_live_registry_entry_keeps_the_stamp(self):
        self._transcript([_launch("t-restart-3", LAUNCH)])
        self._seed("agents")
        self._tick({"state": "", "bgTasks": [{"toolUseId": "t-restart-3", "desc": "x", "since": LAUNCH}]})
        self.assertIsNotNone(self._stamp(), "the registry still tracks it — genuinely in flight")

    def test_job_stamps_ignore_the_registry(self):
        # the watcher dying with a restart is the CARRIER going, not the job returning — kind=job
        # keeps requiring a real terminal record (the 2026-08-15 rule survives the reconciliation)
        self._transcript([_launch("t-restart-4", LAUNCH)])
        self._seed("job")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "the slurm job may run on — only its terminal record lifts")

    def test_a_restart_alone_does_not_lift_a_dispatchless_job_stamp(self):
        # a JOB stamp names compute the kernel cannot observe (a CI run, a remote queue). A CLI respawn
        # is the CARRIER dying, not the job ending — yet a routine kernel restart alone lifted a
        # correctly-labelled job stamp that owned nothing (review find on #936, 2026-09-07). The same
        # shape with kind=task DOES lift: an in-harness task died with its process.
        self._transcript([])                              # nothing dispatched anywhere
        self._seed("job", why="slurm 4821 regenerating the parts; verifies when done")
        self.spawn = BACK                                 # the backend respawned AFTER the stamp
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "a restart is not the external job returning")
        self._seed("task", why="the background build finishing")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp(), "an in-harness task stamp: the respawn killed what it watched")

    def test_a_return_before_the_stamp_was_written_is_not_the_world_emptying_after_it(self):
        # the dispatch-less branch measures endings from the stamp's WRITE time, not the audited turn's
        # trigger: a background item that returned mid-turn, before the closer even wrote the stamp,
        # used to lift it within one pusher cycle of its write (review find on #936, 2026-09-07)
        self.spawn = STAMP - 50                           # no respawn after the stamp
        # launched BEFORE the goal was born, so the stamp owns no dispatch and the dispatch-less branch
        # (not the owned-dispatch rule) is what decides
        self._transcript([_launch("t1", BORN - 50), _notification("t1", BACK)])   # returned at BACK…
        self._seed("task", anchor=STAMP, written=BACK + 50)                        # …the stamp written AFTER it
        self._tick({"state": "", "bgTasks": []}, now=BACK + 200)
        self.assertIsNotNone(self._stamp(), "the return predates the stamp's write — not an ending after it")
        self._seed("task", anchor=STAMP, written=STAMP)                         # written BEFORE the return
        self._tick({"state": "", "bgTasks": []}, now=BACK + 200)
        self.assertIsNone(self._stamp(), "a return after the write is the ending the stamp waited on")

    def test_a_dispatchless_agents_stamp_over_an_empty_registry_lifts(self):
        # the live 2026-08-24 shape: a closer misread peer sessions as agents and stamped kind=agents
        # with NO dispatch recorded anywhere; after a restart nothing can ever end that wait
        self._transcript([])
        self._seed("agents", why="workers still building the pieces; merges when they report")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp(), "no dispatch anywhere + empty authoritative set -> orphan, lifted")

    def test_the_dispatchless_lift_respects_the_anchor_and_the_kind(self):
        # (2026-08-25 audit) the respawn is ONE sufficient evidence, not the only one: an agents
        # stamp over a world with NOTHING running anywhere — registry authoritatively empty, no
        # subagents, no raw-running task in the pairing — lifts regardless of the spawn epoch (the
        # misread-peer-as-agents shape: the notification it claims to await can never arrive). A
        # world with a dispatch still RUNNING keeps every stamp, exactly as before.
        self._transcript([_monitor("t1", LAUNCH, timeout_ms=30_000_000)])   # one genuinely-running task
        self._seed("agents")
        self.spawn = STAMP - 50                       # the stamp POSTDATES the last restart
        self._tick({"state": "", "bgTasks": [{"toolUseId": "t1"}]})   # …and the registry agrees it lives
        self.assertIsNotNone(self._stamp(), "something IS running — no lift without its return")
        self._transcript([])
        self._seed("agents")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp(), "nothing running anywhere → the wait can never end; lifted")
        self.spawn = BACK
        self._seed(None)                              # a kindless stamp never matches the agents-orphan rule
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "kindless stamps keep the conservative dispatch-less skip")
        self._seed("agents")
        self._tick({"state": "", "bgTasks": [], "subagents": [{"type": "Task", "since": BACK}]})
        self.assertIsNotNone(self._stamp(), "live subagents ARE the wait — never lifted from under them")


if __name__ == "__main__":
    unittest.main()


class LiftStandsDown(unittest.TestCase):
    """The lift joins the stand-down rule (the 2026-08-19 nudge audit): a writer whose evidence
    predates the diary yields. The lift's evidence is the newest RETURN it can cite; a closer
    assert filed AFTER every citable return means the judge ruled on a fresher world (the session
    re-armed something the ownership window can't see), and lifting anyway produced 2-3 second
    stamp↔lift flaps that reset the nudge ladder (fires 5s after a lift; three first-nudges in 21
    minutes, each answered "still running")."""

    def setUp(self):
        AwaitingLift.setUp(self)

    def tearDown(self):
        AwaitingLift.tearDown(self)

    _transcript = AwaitingLift._transcript
    _seed = AwaitingLift._seed
    _tick = AwaitingLift._tick
    _stamp = AwaitingLift._stamp

    def test_a_reassert_after_a_lift_stands_the_next_lift_down(self):
        # the FLAP: assert → lift → the closer re-asserts AFTER the lift, citing a fresher world —
        # every return this lift could cite preceded the prior lift, so lifting again just flaps
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(written=BACK + 60)
        import json as _json
        gp = km.jd.GOALDIR / (SID + ".json")
        store = _json.loads(gp.read_text())
        nd = store["nodes"][self.gid]
        nd["log"] = [
            {"ev_t": STAMP, "src": "closer", "kind": "awaiting", "why": "w", "at": STAMP},
            {"ev_t": BACK + 10, "src": "romp", "kind": "awaiting", "lift": True, "at": BACK + 10},
            {"ev_t": STAMP, "src": "closer", "kind": "awaiting", "why": nd["awaitingWhy"], "at": BACK + 60},
        ]
        gp.write_text(_json.dumps(store))
        self._tick(now=BACK + 120)
        self.assertIsNotNone(self._stamp(), "a re-assert after a lift means a fresher ruling — yield")

    def test_a_first_stamp_still_lifts_on_audit_lag_returns(self):
        # NO prior lift: the original design holds — a return the judge never saw still lifts,
        # even when the stamp's write time postdates it (the same-turn suite pins depend on this)
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(written=BACK + 60)                    # written after the return, but never lifted before
        self._tick(now=BACK + 120)
        self.assertIsNone(self._stamp(), "first-stamp audit-lag lift preserved")


class LiftGate(unittest.TestCase):
    """The inputs gate in front of the lift's store read (perf plan 2, P6a; 2026-09-07 upstream fold: upstream's
    _sid_inputs_fp / _lift_seen fingerprint adopted over the fork's _LIFT_GATE identity key, with the
    fork's intents layered on: upstream's gate also skips a stamped session whose inputs are unchanged, a
    skip the fork's never made) and the two-phase read behind it (perf plan 4, P16). The ruling reads the
    store, the override journal, the goals-archive (a `restore` row re-inserts a node only when neither
    holds it), the transcript, the postal log and the SDK reg, plus two live facts (the registry's task ids
    and subagent count, and whether each running dispatch's deadline has passed), so a session whose
    fingerprint is unchanged since the last ruling is skipped before the parse, stamped or not. Every
    writer moves an input (rename publishes, journal appends, transcript records), so a lift happens on
    exactly the events it did before.

    Behind the gate, phase 1 PROBES the shared read-only view (jd.load_goals_shared) and decides on it;
    phase 2 loads the WRITER's copy (jd.load_goals) only when that decision found a lift due, decides again
    on the copy, and files that decision. The two loaders are counted apart through wrappers: `_tick`
    returns the WRITER loads a tick took and leaves the probe count in `self.last_probes`. A gated tick is
    zero of both; a stamped session whose dispatch is still out is one probe and zero writer loads on the
    tick that reads it, and gated after that until an input moves; a due lift is one probe and one writer
    load. jd.load_goals_shared hands a read to load_goals when there is no store file, so an absent store
    counts one writer-style load (the fallback, not a lift). In-place rewrites after a tick go through
    save_goals, a journal append, an archive publish, or os.utime (coarse-mtime filesystems in CI)."""

    def setUp(self):
        AwaitingLift.setUp(self)
        self.saved_arch = km.jd.GOALARCHDIR
        km.jd.GOALARCHDIR = Path(self.td.name) / "goals-archive"
        self.calls = []                                  # writer loads (jd.load_goals, fallbacks included)
        self.probes = []                                 # shared probes (jd.load_goals_shared)
        real = km.jd.load_goals
        def counted(fsid):
            self.calls.append(fsid)
            return real(fsid)
        km.jd.load_goals = counted
        self.addCleanup(setattr, km.jd, "load_goals", real)
        real_shared = km.jd.load_goals_shared
        def probed(fsid):
            self.probes.append(fsid)
            return real_shared(fsid)
        km.jd.load_goals_shared = probed
        self.addCleanup(setattr, km.jd, "load_goals_shared", real_shared)
        self.last_probes = 0
        self.stats0 = km.jd.shared_store_stats()

    def tearDown(self):
        # THE POISON CANARY, for every test here: the probe reads the shared view and writes nothing to it,
        # and the frozen store never reaches save_goals (either would switch the cache off and file a row)
        st = km.jd.shared_store_stats()
        self.assertEqual(st["poisoned"] - self.stats0["poisoned"], 0, "no write reached the shared view")
        self.assertEqual(st["off"], 0, "the shared cache is still on")
        km.jd.GOALARCHDIR = self.saved_arch
        AwaitingLift.tearDown(self)

    _transcript = AwaitingLift._transcript
    _seed = AwaitingLift._seed
    _stamp = AwaitingLift._stamp

    def _tick(self, now=BACK + 100, snap=None):
        """One lift tick; returns how many WRITER loads it took and records the probes in last_probes."""
        before, pbefore = len(self.calls), len(self.probes)
        km._lift_spent_awaiting(now, {SID: ({"state": ""} if snap is None else snap)})
        self.last_probes = len(self.probes) - pbefore
        return len(self.calls) - before

    def _lift_rows(self):
        log = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"][self.gid]["log"]
        return [e for e in log if e.get("kind") == "awaiting" and e.get("lift")]

    def _seed_unstamped(self, size=None):
        """An unstamped store, written in place. `size` pads the node's text so the file is exactly that
        many bytes: a same-size rewrite holds st_size still, so only the key's other components can move."""
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN, "log": []}
        store = {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}
        if size is not None:
            pad = size - len(json.dumps(store).encode())
            self.assertGreaterEqual(pad, 0, "the stamped store must be the longer one")
            nd["text"] += " " * pad                      # one ASCII byte per space, inside the JSON string
            self.assertEqual(len(json.dumps(store).encode()), size)
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(store))

    def _stamped_bytes(self):
        """The bytes of a stamped store (the node _stamped_node builds), for a same-size rewrite."""
        return json.dumps({"rompUuid": SID, "seq": 1, "placements": {}, "status": {},
                           "nodes": {self.gid: self._stamped_node()}}).encode()

    def _stamped_node(self, why="waiting on a dispatched investigation"):
        return {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": False,
                "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN,
                "awaitingWhy": why, "awaitingAt": STAMP,
                "log": [{"ev_t": STAMP, "src": "closer", "kind": "awaiting", "why": why, "at": STAMP}]}

    def _returned_dispatch(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])

    # ---- the saving: an unchanged, unstamped session costs stats, not a parse ----
    def test_an_unchanged_unstamped_store_is_probed_once(self):
        self._returned_dispatch()
        self._seed_unstamped()
        skips = km._lift_gate_stats["skip"]
        self.assertEqual(self._tick(), 0, "the first tick has to look, on the shared view: no writer load")
        self.assertEqual(self.last_probes, 1)
        self.assertEqual(self._tick(), 0, "same inputs as the last ruling: no read")
        self.assertEqual(self.last_probes, 0)
        self.assertEqual(self._tick(), 0)
        self.assertEqual(self.last_probes, 0)
        self.assertEqual(km._lift_gate_stats["skip"] - skips, 2, "the /perf counter saw both skips")
        self.assertIn(SID, km._lift_seen, "the entry remembers the inputs it ruled on")

    def test_a_missing_store_is_gated_until_it_appears(self):
        self._returned_dispatch()
        self.assertEqual(self._tick(), 1)               # no file: the shared loader hands the read to
        self.assertEqual(self.last_probes, 1)           #   load_goals, which answers a fresh empty store
        self.assertEqual(self._tick(), 0, "still no file: the absent identity is a stable key")
        self.assertEqual(self.last_probes, 0)
        self._seed()                                     # the store is born stamped (a rename in production)
        self.assertEqual(self._tick(), 1, "the store appeared: probed, a lift is due, one writer load")
        self.assertIsNone(self._stamp(), "…and the lift proceeded exactly as without the gate")

    # ---- every writer moves the key ----
    def test_a_save_goals_publish_reloads(self):
        self._returned_dispatch()
        self._seed_unstamped()
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        store = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())
        store["nodes"][self.gid] = self._stamped_node()
        km.jd.save_goals(SID, store)                     # the closer's publish: a rename, new identity
        self.assertEqual(self._tick(), 1, "the publish moved the store's identity: probed, a lift due, one writer load")
        self.assertEqual(self.last_probes, 1)
        self.assertIsNone(self._stamp(), "the returned dispatch lifts the fresh stamp")

    def test_a_journal_restore_row_reloads_and_lifts(self):
        self._returned_dispatch()
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {}}))
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        # an undo-clear restore rides the journal with its node payload — a stamped node can come back
        # through the replay alone, with the store file untouched
        km.jd.append_restore(SID, {self.gid: self._stamped_node()}, {}, BACK + 50)
        self.assertEqual(self._tick(), 1, "the journal grew: probed, the restored stamp is due, one writer load")
        self.assertEqual(self.last_probes, 1)
        nodes = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"]
        self.assertIn(self.gid, nodes, "the restored node was saved back")
        self.assertIsNone(nodes[self.gid].get("awaitingWhy") or None, "…and its stamp lifted on the return")

    def test_a_journal_block_row_reloads(self):
        self._returned_dispatch()
        self._seed_unstamped()
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        km.jd.append_block(SID, self.gid, "nudge", "a status ask went unanswered", BACK + 50)
        self.assertEqual((self._tick(), self.last_probes), (0, 1),
                         "a block row is a journal append: the key moved, probed again; nothing due")
        self.assertEqual((self._tick(), self.last_probes), (0, 0), "nothing stamped after the replay either: gated again")

    def test_a_journal_override_row_reloads(self):
        self._returned_dispatch()
        self._seed_unstamped()
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        km.jd.append_override(SID, self.gid, "resolve", BACK + 50)   # a user click's journal row
        self.assertEqual((self._tick(), self.last_probes), (0, 1),
                         "a user override is a journal append: the key moved, probed again; nothing due")
        self.assertEqual((self._tick(), self.last_probes), (0, 0), "the replayed resolve stamps nothing: gated again")

    def test_an_archive_change_with_a_restore_row_reloads(self):
        self._returned_dispatch()
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {}}))
        # the node sits in the archive, so the journal's restore row does NOT re-insert it (replay
        # defers to a later re-clear) — the archive's contents decide the replay's outcome
        km.jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {self.gid: self._stamped_node()}, "status": {}})
        km.jd.append_restore(SID, {self.gid: self._stamped_node()}, {}, BACK + 50)
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertIsNotNone(km._lift_seen[SID][2], "the archive's identity is in the fingerprint (the fork's intent)")
        self.assertEqual((self._tick(), self.last_probes), (0, 0), "archive, journal, store unchanged: gated")
        km.jd.save_goal_archive(SID, {"rompUuid": SID, "nodes": {}, "status": {}})
        self.assertEqual(self._tick(), 1, "the archive changed: probed, the restored stamp is due, one writer load")
        nodes = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"]
        self.assertIn(self.gid, nodes, "the restore now re-inserted the node")
        self.assertIsNone(nodes[self.gid].get("awaitingWhy") or None, "…and the lift proceeded")

    def test_a_same_size_in_place_rewrite_reloads(self):
        """st_mtime_ns is in the key: a rewrite that keeps the inode AND the byte count (the store's own
        path opened for writing, stamped bytes exactly as long as the unstamped ones) still moves the
        identity. The utime stands in for the clock on a coarse-mtime filesystem (CI)."""
        self._returned_dispatch()
        stamped = self._stamped_bytes()
        self._seed_unstamped(size=len(stamped))
        gp = km.jd.GOALDIR / (SID + ".json")
        old = gp.stat()
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        gp.write_bytes(stamped)                          # same path, same inode, same byte count
        os.utime(gp, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000))
        new = gp.stat()
        self.assertEqual((new.st_ino, new.st_size), (old.st_ino, old.st_size), "only the mtime moved")
        self.assertEqual(self._tick(), 1, "the mtime alone moved the identity: probed, a lift due, one writer load")
        self.assertIsNone(self._stamp())

    def test_a_same_size_rename_with_the_old_mtime_reloads(self):
        """st_ino is in the key: a rename publish of the same byte count whose mtime is set back to the
        old file's (a restored backup keeps its timestamps; save_goals publishes by rename) still moves
        the identity."""
        self._returned_dispatch()
        stamped = self._stamped_bytes()
        self._seed_unstamped(size=len(stamped))
        gp = km.jd.GOALDIR / (SID + ".json")
        old = gp.stat()
        self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        tmp = gp.with_name(gp.name + ".tmp")
        tmp.write_bytes(stamped)
        tmp.rename(gp)                                   # a new inode under the same path
        os.utime(gp, ns=(old.st_atime_ns, old.st_mtime_ns))
        new = gp.stat()
        self.assertNotEqual(new.st_ino, old.st_ino, "the rename brought a new inode")
        self.assertEqual((new.st_mtime_ns, new.st_size), (old.st_mtime_ns, old.st_size), "only the inode moved")
        self.assertEqual(self._tick(), 1, "the inode alone moved the identity: probed, a lift due, one writer load")
        self.assertIsNone(self._stamp())

    # ---- a stamped store is gated on the same terms (2026-09-07 upstream fold, upstream's gate adopted: the
    #      fork's _LIFT_GATE re-loaded a stamped store every tick; upstream's fingerprint gate skips it
    #      until an input moves, and the return that ends the wait is itself a transcript write), and the
    #      tick that does read it decides on the shared view alone (perf plan 4, P16) ----
    def test_a_stamped_store_with_unchanged_inputs_is_skipped_too(self):
        self._transcript([_launch("t1", LAUNCH)])       # still out: the stamp stands
        self._seed()
        before = dict(km._lift_gate_stats)
        self.assertEqual((self._tick(), self.last_probes), (0, 1),
                         "the first tick has to look: one probe, nothing due, no writer load")
        self.assertIsNotNone(self._stamp())
        self.assertEqual((self._tick(), self.last_probes), (0, 0),
                         "store, journal, transcript and live facts unchanged: same ruling, no read")
        self.assertEqual((self._tick(), self.last_probes), (0, 0))
        self.assertIsNotNone(self._stamp(), "the stamp stands through the skipped ticks")
        after = km._lift_gate_stats
        self.assertEqual(after["load"] - before["load"], 1, "one session-cycle read the store")
        self.assertEqual(after["shared"] - before["shared"], 1, "…answered by the shared cache")
        self.assertEqual(after["writer"] - before["writer"], 0, "…and none loaded the writer's copy")
        self.assertEqual(after["noop"] - before["noop"], 0)
        self.assertIn(SID, km._lift_seen)
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])   # the return lands: an input moved
        self.assertEqual((self._tick(), self.last_probes), (1, 1),
                         "a fingerprint input moved: probed, the lift is due, one writer load")
        self.assertIsNone(self._stamp(), "...and the lift proceeded exactly as without the gate")

    def test_a_due_lift_takes_one_writer_load_and_files_once(self):
        self._returned_dispatch()
        self._seed()
        km._mark_auto_nudged(self.gid, "SOME-ARM-TURN", 3, at=BACK - 50)
        d = dict(km._auto_nudge_data())
        n = dict(d.get("nudged", {}))
        n[self.gid] = dict(n[self.gid], moot=True)      # a spent record the lift erases (2026-08-16)
        d["nudged"] = n
        km._write_auto_nudge(d)
        before = dict(km._lift_gate_stats)
        self.assertEqual(self._tick(), 1, "the probe found the lift due: exactly one writer load")
        self.assertEqual(self.last_probes, 1)
        self.assertIsNone(self._stamp(), "…and it lifted")
        self.assertEqual(len(self._lift_rows()), 1, "one lift row, filed on the writer's copy")
        self.assertNotIn(self.gid, km._auto_nudge_data().get("nudged", {}), "the spent nudge record dropped once")
        after = km._lift_gate_stats
        self.assertEqual((after["writer"] - before["writer"], after["noop"] - before["noop"]), (1, 0))
        self.assertEqual((self._tick(), self.last_probes), (0, 1),
                         "the save moved the key: probed once more, nothing stamped, no writer load")
        self.assertEqual((self._tick(), self.last_probes), (0, 0), "…then gated")
        self.assertEqual(len(self._lift_rows()), 1, "the lift was filed exactly once")

    def test_a_node_keyed_apart_from_its_id_field_still_lifts(self):
        # a decision names the store's node KEY, which phase 2 resolves on the writer's copy; a node whose
        # `id` field disagrees with its key (a hand-edited or migrated store) must not be dropped as a noop
        self._returned_dispatch()
        nd = dict(self._stamped_node(), id=SID + ":renamed")
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))
        before = dict(km._lift_gate_stats)
        self.assertEqual((self._tick(), self.last_probes), (1, 1))
        self.assertIsNone(self._stamp(), "found by key on the writer's copy: lifted")
        self.assertEqual(km._lift_gate_stats["noop"] - before["noop"], 0)

    def test_the_rolled_up_arm_lifts_with_one_writer_load(self):
        self._transcript([])
        nd = {"id": self.gid, "text": "a goal", "parentId": None, "nodeComplete": True,
              "blocked": False, "cleared": False, "rolledUp": True, "trail": [], "t": BORN, "mt": BORN,
              "awaitingWhy": "a wait the roll-down froze", "awaitingAt": STAMP,
              "log": [{"ev_t": STAMP, "src": "closer", "kind": "awaiting",
                       "why": "a wait the roll-down froze", "at": STAMP}]}
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {self.gid: nd}}))
        self.assertEqual((self._tick(), self.last_probes), (1, 1), "the frozen stamp is due: one writer load")
        self.assertEqual(len(self._lift_rows()), 1)
        self.assertEqual((self._tick(), self.last_probes), (0, 1), "diary-guarded: probed, nothing due")
        self.assertEqual((self._tick(), self.last_probes), (0, 0), "…and no candidate, so gated")

    def test_the_peer_superseded_arm_lifts_with_one_writer_load(self):
        self._transcript([])
        self._seed(why="waiting on the peer's answer", kind="peer")   # written at STAMP
        saved = km._peer_answered
        km._peer_answered = lambda sid: (BACK, {})       # the peer replied after the stamp was written
        try:
            self.assertEqual((self._tick(), self.last_probes), (1, 1), "the reply ended the wait: one writer load")
            self.assertIsNone(self._stamp())
            self.assertEqual(len(self._lift_rows()), 1)
            self.assertEqual((self._tick(), self.last_probes), (0, 1))
            self.assertEqual((self._tick(), self.last_probes), (0, 0))
        finally:
            km._peer_answered = saved

    def test_the_empty_registry_arm_lifts_with_one_writer_load(self):
        # the dispatch-less agents stamp over an authoritatively empty lifecycle set (RestartReconcile)
        self._transcript([])
        self._seed(why="workers still building the pieces; merges when they report", kind="agents")
        saved = km._sdk_spawned_at
        km._sdk_spawned_at = lambda sid: BACK             # the backend respawned after the stamp
        try:
            self.assertEqual(self._tick(snap={"state": "", "bgTasks": []}), 1, "the orphan is due: one writer load")
            self.assertEqual(self.last_probes, 1)
            self.assertIsNone(self._stamp())
            self.assertEqual(self._tick(snap={"state": "", "bgTasks": []}), 0)
        finally:
            km._sdk_spawned_at = saved

    def test_a_writer_racing_between_the_probe_and_the_load_costs_a_reload_never_a_wrong_lift(self):
        """Phase 1 decides on the shared view; phase 2 decides AGAIN on the writer's copy and files only
        that. A closer publishing between the two — here, placing the deciding launch under ANOTHER card,
        which makes it not this goal's dispatch — must not have its verdict overridden by the probe's
        stale decision: the writer load decides nothing (`noop`), the stamp stands, and the next tick's
        probe (on the moved store) agrees."""
        # chained through parentUuid: the parse walks the transcript graph from its leaf, so only a chained
        # record reaches a segment (the scan-based fixtures elsewhere in this module need no chain)
        recs = [_dispatch("t1", LAUNCH - 1), _launch("t1", LAUNCH), _notification("t1", BACK)]
        for prev, rec in zip(recs, recs[1:]):
            rec["parentUuid"] = prev["uuid"]
        self._transcript(recs)
        self._seed(why="waiting on the release pipeline to go green, then will tag")
        ps = km._parse(self.path, SID, BACK + 100)
        seg = km._seg_of_tool_uses(ps, {}, ["t1"])["t1"]  # the segment the dispatch resolves to
        other = SID + ":gOTHER"
        real = km.jd.load_goals                          # LiftGate's counting wrapper
        raced = []
        def racing(fsid):
            if not raced:
                raced.append(fsid)
                pub = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())
                pub["nodes"][other] = {"id": other, "text": "another goal", "parentId": None,
                                       "nodeComplete": False, "blocked": False, "cleared": False,
                                       "trail": [], "t": BORN, "mt": BORN, "log": []}
                pub["placements"] = {seg: other}         # the closer places the launch under the other card
                km.jd.save_goals(SID, pub)
            return real(fsid)
        km.jd.load_goals = racing
        before = dict(km._lift_gate_stats)
        self.assertEqual(self._tick(), 1, "the probe (pre-publish) found a lift due: one writer load")
        self.assertEqual(len(raced), 1)
        self.assertIsNotNone(self._stamp(), "the writer's copy places the launch elsewhere: no lift filed")
        self.assertEqual(self._lift_rows(), [], "nothing filed from the stale decision")
        after = km._lift_gate_stats
        self.assertEqual((after["writer"] - before["writer"], after["noop"] - before["noop"]), (1, 1))
        km.jd.load_goals = real
        self.assertEqual((self._tick(), self.last_probes), (0, 1),
                         "the publish moved the key: probed on the moved store, nothing due, no writer load")
        self.assertIsNotNone(self._stamp(), "the other card's dispatch never retires this wait")

    def test_a_dormant_session_is_not_gated_or_recorded(self):
        self._seed_unstamped()
        before = len(self.calls)
        km._lift_spent_awaiting(BACK + 100, {SID: None})     # dormant: no tmux/SDK row for the sid
        self.assertEqual(len(self.calls) - before, 0)
        self.assertNotIn(SID, km._lift_seen, "dormant: skipped before the gate, nothing remembered")

    def test_a_failed_probe_records_no_skip(self):
        import contextlib, io
        self._returned_dispatch()
        self._seed_unstamped()
        probed = km.jd.load_goals_shared
        def boom(fsid):
            self.probes.append(fsid)
            raise RuntimeError("synthetic read failure")
        km.jd.load_goals_shared = boom
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual((self._tick(), self.last_probes), (0, 1))
        self.assertIn("awaiting-lift", err.getvalue(), "the failure is reported, as before")
        self.assertNotIn(SID, km._lift_seen, "an error is never cached as a skip")
        km.jd.load_goals_shared = probed
        self.assertEqual((self._tick(), self.last_probes), (0, 1), "the next tick retries the read")

    # ---- a load that FELL BACK is no better than one that raised ----
    def _read_fails_once(self, target):
        """Patch the two reads of `target` so each raises OSError ONCE (the EMFILE/EIO shape a busy kernel
        meets) and every later read is real: jd._disk_read, the shared loader's descriptor read (of the
        store, or of the journal through _journal_read), which hands the read to load_goals; and
        Path.read_text, load_goals' store read and _replay_overrides' journal read, which swallow the error
        and answer an empty store / skip the journal, `_unread`-marked. Returns the counter of raised
        reads: 2 when the probe met the failure through both loaders."""
        import errno
        real = Path.read_text
        real_disk = km.jd._disk_read
        state = {"fired": 0, "text": 0, "disk": 0}
        def flaky(p, *a, **k):
            if p == target and not state["text"]:
                state["text"] += 1; state["fired"] += 1
                raise OSError(errno.EMFILE, "synthetic: too many open files")
            return real(p, *a, **k)
        def flaky_disk(fd, path_s):
            if path_s == str(target) and not state["disk"]:
                state["disk"] += 1; state["fired"] += 1
                raise OSError(errno.EMFILE, "synthetic: too many open files")
            return real_disk(fd, path_s)
        Path.read_text = flaky
        km.jd._disk_read = flaky_disk
        self.addCleanup(setattr, Path, "read_text", real)
        self.addCleanup(setattr, km.jd, "_disk_read", real_disk)
        return state

    def test_a_swallowed_store_read_failure_is_not_cached_as_nothing_to_lift(self):
        import contextlib, io
        self._returned_dispatch()
        self._seed()                                     # stamped, its dispatch returned: a lift is due
        state = self._read_fails_once(km.jd.GOALDIR / (SID + ".json"))
        with contextlib.redirect_stderr(io.StringIO()):
            # the shared read failed and handed the read to load_goals, whose read failed too and was
            # swallowed: an empty store (one writer-style load, the fallback; no lift is due on it)
            self.assertEqual((self._tick(), self.last_probes), (1, 1))
        self.assertEqual(state["fired"], 2, "both loaders met the failure")
        self.assertIsNotNone(self._stamp(), "tick 1 saw the fallback, not the stamp: no lift yet")
        self.assertNotIn(SID, km._lift_seen, "a fallback answer is not the files' content: no entry")
        self.assertEqual((self._tick(), self.last_probes), (1, 1),
                         "the file reads fine now and is unchanged: probed anyway, the lift is due, one writer load")
        self.assertIsNone(self._stamp(), "…and the stamp lifts one cycle late, not never")

    def test_a_swallowed_journal_read_failure_is_not_cached_as_nothing_to_lift(self):
        import contextlib, io
        self._returned_dispatch()
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": {}, "nodes": {}}))
        km.jd.append_restore(SID, {self.gid: self._stamped_node()}, {}, BACK + 50)
        state = self._read_fails_once(km.jd._overrides_dir() / (SID + ".jsonl"))
        with contextlib.redirect_stderr(io.StringIO()):
            # the shared loader's journal read failed and handed the read to load_goals, whose replay
            # logged history-unreadable and skipped the journal: the node never came back this tick
            self.assertEqual((self._tick(), self.last_probes), (1, 1))
        self.assertEqual(state["fired"], 2, "both loaders met the failure")
        self.assertNotIn(SID, km._lift_seen, "the journal was not read: no entry")
        self.assertEqual((self._tick(), self.last_probes), (1, 1),
                         "the journal reads now, unchanged: probed anyway, the restored stamp is due, one writer load")
        nodes = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())["nodes"]
        self.assertIn(self.gid, nodes, "the restore replayed and the node was saved back")
        self.assertIsNone(nodes[self.gid].get("awaitingWhy") or None, "…with its stamp lifted")

    def test_entries_for_sids_that_left_the_alive_set_are_dropped(self):
        self._seed_unstamped()
        self._tick()
        self.assertIn(SID, km._lift_seen)
        km._alive_sessions = lambda now, tmux: []
        self._tick()
        self.assertNotIn(SID, km._lift_seen, "the sid left the alive set: its entry went with it")

    def test_a_writer_racing_the_probe_costs_one_reload_never_a_wrong_skip(self):
        """The key is stat-ed BEFORE the read. A closer that publishes a stamp while the probe is in flight
        leaves an entry keyed on the pre-write files, so the next tick's key mismatches and the stamp is
        found one cycle late. Keyed after the read, the entry would carry the writer's identity against
        the pre-write store's empty answer, and the fresh stamp would be gated out of sight for good."""
        self._returned_dispatch()
        self._seed_unstamped()
        probed = km.jd.load_goals_shared
        raced = []
        def racing(fsid):
            store = probed(fsid)                        # the real read: the pre-write, unstamped store
            if not raced:
                raced.append(fsid)
                pub = json.loads((km.jd.GOALDIR / (SID + ".json")).read_text())
                pub["nodes"][self.gid] = self._stamped_node()
                km.jd.save_goals(SID, pub)              # the closer publishes under the read: a rename
            return store
        km.jd.load_goals_shared = racing
        self.assertEqual((self._tick(), self.last_probes), (0, 1), "tick 1 probed once and saw nothing to lift")
        self.assertEqual(len(raced), 1)
        self.assertIsNotNone(self._stamp(), "the racing publish's stamp stands after tick 1")
        self.assertIn(SID, km._lift_seen, "the entry is keyed on the pre-write files")
        km.jd.load_goals_shared = probed
        self.assertEqual((self._tick(), self.last_probes), (1, 1), "tick 2: the files moved under the read, so it probes, and the lift is due")
        self.assertIsNone(self._stamp(), "…and lifts the stamp one cycle late, never never")

    def test_perf_reports_the_gate(self):
        self._seed_unstamped()
        self._tick(); self._tick()
        lg = km._PERF_STATS.snapshot()["memos"]["lift_gate"]
        for k in ("skip", "load", "shared", "writer", "noop"):
            self.assertEqual(lg[k], km._lift_gate_stats[k], k)
        self.assertEqual(lg["entries"], len(km._lift_seen))
        self.assertGreaterEqual(lg["skip"], 1)
        self.assertGreaterEqual(lg["shared"], 1, "the probe read the shared view")


class LiftKeepsLiveLedgerRecords(unittest.TestCase):
    """A lift drops only SPENT ledger records (failed/moot/answered latches — the 2026-08-16
    idle-in-Working fix). A LIVE mid-count record is the once-per-stall invariant itself: dropping
    it reset the counter on every stamp↔lift flap and the same arm turn drew fresh first-nudges
    minutes apart while the escalation ladder never engaged."""

    def test_live_records_survive_the_drop(self):
        import tempfile as _tf
        from pathlib import Path as _P
        with _tf.TemporaryDirectory() as td:
            saved = km.jd.STATE
            try:
                km.jd.STATE = _P(td)
                km._write_auto_nudge({"enabled": True, "nudged": {
                    "g-live": {"count": 2, "lastTurnId": "u9"},
                    "g-failed": {"count": 1, "lastTurnId": "u1", "failed": True},
                    "g-moot": {"count": 1, "lastTurnId": "u2", "moot": True},
                    "g-answered": {"count": 1, "lastTurnId": "u3", "answeredAt": 5}}})
                for gid in ("g-live", "g-failed", "g-moot", "g-answered"):
                    km._drop_auto_nudge_rec(gid)
                left = km._auto_nudge_data().get("nudged", {})
                self.assertIn("g-live", left, "mid-episode memory survives — the ladder can escalate")
                self.assertEqual(left["g-live"].get("count"), 2, "…with its count intact")
                for gid in ("g-failed", "g-moot", "g-answered"):
                    self.assertNotIn(gid, left, "spent latches still drop (the 2026-08-16 fix)")
            finally:
                km.jd.STATE = saved


class InHarnessWaitLift(unittest.TestCase):
    """A task/job stamp whose dispatches sit on ANOTHER top lifts when the in-harness world it stood
    over goes EMPTY after the stamp (2026-09-05). The live specimen: the closer stamped a top kind=job
    for a Monitor plus a background command the session itself was running; the planner placed both
    launches on a sibling top, so the stamp owned nothing (`own == []`) and the dispatch-less skip
    kept it — for 17 hours, over an authoritatively empty registry, nothing pending anywhere. The
    agents-kind orphan rule already lifts that shape; task/job now take the same lift, keyed on the
    same authority (the backend's present-and-empty lifecycle set, no live subagents, no armed kernel
    watch) plus the watermark the whole sweep uses: the LAST in-harness item's ending — a terminal
    record, a Monitor's recorded ceiling, the launch ledger's stop tombstone, or the CLI respawn that
    killed everything — must postdate the stamp's anchor. A world already empty when the closer
    stamped is a wait on something the registry cannot see (a CI run): the dead-man's, untouched.

    SYNTHETIC fixtures; a PRIVATE sid (the goal-store fixture rule: load_goals replays the per-sid
    override journal, and the shared placeholder sid's journal is written by other modules)."""

    PSID = "44444444-5555-6666-7777-888888888888"

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in
                      ("_alive_sessions", "_mark_views_dirty", "_sdk_spawned_at", "_bg_placed_tops")}
        self.saved_jd = (km.jd.STATE, km.jd.GOALDIR)
        km.jd.STATE = td
        km.jd.GOALDIR = td / "goals"
        km.jd.GOALDIR.mkdir(parents=True)
        (td / "sdk").mkdir()
        self.path = str(td / (self.PSID + ".jsonl"))
        km._alive_sessions = lambda now, tmux: [{"sid": self.PSID, "path": self.path}]
        km._mark_views_dirty = lambda *a, **k: None
        km._sdk_spawned_at = lambda sid: self.spawn
        self.spawn = STAMP - 50                       # default: the CLI predates the stamp — no respawn story
        self.gid, self.other = self.PSID + ":g1", self.PSID + ":g2"
        # the planner placed every launch on the SIBLING top: this goal owns no dispatch
        km._bg_placed_tops = lambda sid, path, tids, store=None: {t: self.other for t in tids}   # the lift hands its store
        self._saved_watches = list(km._pr_watches)
        km._SESSION_STAMP_CACHE.clear(); km._bgall_cache.clear(); km._bgtasks_cache.clear()

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(km, k, v)
        km._pr_watches[:] = self._saved_watches
        km.jd.STATE, km.jd.GOALDIR = self.saved_jd
        km._SESSION_STAMP_CACHE.clear(); km._bgall_cache.clear(); km._bgtasks_cache.clear()
        try:
            (km.jd._overrides_dir() / (self.PSID + ".jsonl")).unlink()
        except OSError:
            pass
        self.td.cleanup()

    def _transcript(self, recs):
        with open(self.path, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        km._bgall_cache.clear(); km._bgtasks_cache.clear()

    def _seed(self, kind, anchor=STAMP, why="watching the rebuild; will pick the result up when it lands"):
        nd = {"id": self.gid, "text": "rebuild the notes-api index", "parentId": None,
              "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN,
              "awaitingWhy": why, "awaitingAt": anchor,
              **({"awaitingKind": kind} if kind else {}),
              "log": [{"ev_t": anchor, "src": "closer", "kind": "awaiting", "why": why,
                       **({"awaitKind": kind} if kind else {}), "at": anchor}]}
        sib = {"id": self.other, "text": "wire the web session's watcher", "parentId": None,
               "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": BORN, "mt": BORN,
               "log": []}
        (km.jd.GOALDIR / (self.PSID + ".json")).write_text(json.dumps(
            {"rompUuid": self.PSID, "seq": 1, "placements": {}, "status": {},
             "nodes": {self.gid: nd, self.other: sib}}))

    def _reg(self, **fields):
        (km.jd.STATE / "sdk" / (self.PSID + ".json")).write_text(json.dumps(fields))

    def _node(self):
        return json.loads((km.jd.GOALDIR / (self.PSID + ".json")).read_text())["nodes"][self.gid]

    def _stamp(self):
        return self._node().get("awaitingWhy") or None

    def _tick(self, snap, now=BACK + 100):
        km._lift_spent_awaiting(now, {self.PSID: snap} if snap is not None else {})

    def test_a_job_stamp_over_dispatches_placed_elsewhere_lifts_when_the_world_empties_after_it(self):
        # the specimen: the background command returned AFTER the stamp; the registry is present and
        # empty; the goal owns nothing (placed on the sibling) — the wait it described is over
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("job")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp(), "nothing in-harness runs any more, and it ended after the stamp")

    def test_the_lift_is_the_agents_lift_exactly(self):
        # same writer, same row: a romp/awaiting LIFT anchored at the stamp (never wall-clock)
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("task")
        self._tick({"state": "", "bgTasks": []})
        row = [e for e in self._node()["log"] if e.get("kind") == "awaiting"][-1]
        self.assertEqual((row.get("src"), row.get("lift"), row.get("ev_t")), ("romp", True, STAMP))

    def test_a_task_stamp_takes_the_same_lift(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("task")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp())

    def test_one_live_registry_entry_keeps_the_stamp(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK), _launch("t2", LAUNCH + 1)])
        self._seed("job")
        self._tick({"state": "", "bgTasks": [{"toolUseId": "t2", "desc": "x", "since": LAUNCH + 1}]})
        self.assertIsNotNone(self._stamp(), "something is still running in-harness — the wait stands")

    def test_live_subagents_keep_the_stamp(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("task")
        self._tick({"state": "", "bgTasks": [], "subagents": [{"type": "Task", "since": BACK}]})
        self.assertIsNotNone(self._stamp())

    def test_no_authoritative_registry_means_no_move(self):
        # a tmux CLI carries no lifecycle set: registry-absent is not evidence of anything
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("job")
        self._tick({"state": ""})
        self.assertIsNotNone(self._stamp(), "no authoritative source → no move")
        # …and a DORMANT session is skipped outright (its tasks died with its CLI; the death owns it)
        self._seed("job")
        self._tick(None)
        self.assertIsNotNone(self._stamp())

    def test_emptiness_that_predates_the_stamp_is_not_the_waits_ending(self):
        # the closer stamped AFTER the last return, knowing it — the wait is about something the
        # registry cannot see (a CI run); the dead-man owns it, this sweep does not
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("job", anchor=BACK + 100)
        self._tick({"state": "", "bgTasks": []}, now=BACK + 500)
        self.assertIsNotNone(self._stamp(), "the world was already empty when the judge stamped")

    def test_nothing_ever_dispatched_keeps_a_job_stamp(self):
        # a genuinely external job with no in-harness carrier at all: no ending event exists here
        self._transcript([])
        self._seed("job")
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "no item ended after the stamp — nothing to key on")

    def test_a_respawn_after_the_stamp_is_a_sufficient_ending(self):
        # the sibling's launch has no terminal record (killed with the process); the CLI epoch is
        # newer than the stamp, so everything the stamp could have watched died at that moment
        self._transcript([_launch("t1", LAUNCH)])
        self._seed("task")
        self.spawn = STAMP + 50
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp())

    def test_a_ledger_stop_tombstone_after_the_stamp_is_the_ending_event(self):
        # a Monitor called off with TaskStop suppresses its notification — the transcript never
        # learns — but the launch ledger journals the stop; that tombstone is the exact event
        self._transcript([_monitor("m1", LAUNCH, timeout_ms=30_000_000)])
        self._seed("job")
        self._reg(bgLedgerEnded=[{"tid": "m1", "why": "stopped", "at": BACK}])
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNone(self._stamp())
        self._seed("job")
        self._reg(bgLedgerEnded=[{"tid": "m1", "why": "stopped", "at": STAMP - 10}])
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "a stop the judge already knew about is not new information")

    def test_an_armed_kernel_watch_keeps_a_job_stamp(self):
        # a PR watch is the kernel's own carrier of an external wait: its delivery IS the ending
        # event, so the stamp stands while the watch is armed for this session
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed("job")
        km._pr_watches.append({"pr": 7, "repo": "notes-api/notes-api", "sid": self.PSID, "at": LAUNCH,
                               "_next": 0, "_fails": 0, "_busy": False})
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "the kernel is still watching something for this session")

    def test_a_kindless_stamp_keeps_the_conservative_skip(self):
        self._transcript([_launch("t1", LAUNCH), _notification("t1", BACK)])
        self._seed(None)
        self._tick({"state": "", "bgTasks": []})
        self.assertIsNotNone(self._stamp(), "a kindless stamp may be a peer wait — untouched, as before")
