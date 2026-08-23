#!/usr/bin/env python3
"""A DORMANT session's stamped-awaiting Working card converts to a procedural block (the user
2026-08-22): the CLI died while a judged wait still stood, so nothing that could answer it is
running — yet a live awaiting stamp exempted the card from the whole ladder (wake, nudge, staller)
and it sat "paused" in Working forever (two live cards measured at 79 hours). The conversion is
event-triggered (the death transition; a boot catch-up sweep), once per stamp episode, stands down
for restart cuts (the resume machinery owns those), and its why is a recognized procedural block.
SYNTHETIC fixtures only (placeholder UUIDs, invented text)."""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
jd = SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

STAMP_T = 1781100000
_N = [0]


def _fresh_sid():
    """A distinct sid per test: the goals-store cache is mtime-keyed, and same-second reseeds of one
    sid would hand a later test the previous test's mutated store object."""
    _N[0] += 1
    return "11111111-2222-3333-4444-5555555555%02d" % _N[0]


SID = ""
GID = ""


def _seed_store(awaiting=True):
    store = jd.load_goals(SID)
    nd = {"id": GID, "text": "delegate the batch and report", "parentId": None,
          "nodeComplete": False, "blocked": False, "cleared": False, "t": STAMP_T - 100,
          "mt": STAMP_T, "trail": [], "doneWhy": "",
          "log": [{"ev_t": STAMP_T, "src": "closer", "kind": "awaiting",
                   "why": "both workers' report-backs", "at": STAMP_T}]}
    if awaiting:
        nd["awaitingWhy"] = "both workers' report-backs"
        nd["awaitingAt"] = STAMP_T
        nd["awaitingKind"] = "peer"
    store["nodes"][GID] = jd.GuardedNode(nd)
    store["status"] = {GID: "working"}
    jd.save_goals(SID, store)
    return store


def _write_state(state, t):
    d = jd.STATE / "states"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / (SID + ".jsonl"), "w") as f:
        f.write(json.dumps({"state": state, "t": t}) + "\n")


class _HermeticDeadWait(unittest.TestCase):
    def setUp(self):
        global SID, GID
        SID = _fresh_sid()
        GID = SID + ":g1"
        km._PREV_ALIVE = None
        self.nudged = {}
        # hermetic liveness: never read whether THIS box has tmux (the corroboration the sweep now
        # does before converting would otherwise shell out); an authoritative empty owner scan is
        # the corroborated-dead world these tests were written in
        km._TMUX.available = lambda: True
        km._TMUX.alive_sids = lambda t=3: set()

    def tearDown(self):
        for nm in ("available", "alive_sids"):
            km._TMUX.__dict__.pop(nm, None)   # instance attrs shadow the class methods; drop them
        for d in (jd.GOALDIR, jd.STATE / "states", jd.SDKDIR, jd.STATE / "gone"):
            if d.is_dir():
                for f in d.glob("*"):
                    f.unlink()
        p = jd.STATE / "auto-nudge.json"
        if p.exists():
            p.unlink()


class DeadWaitBlock(_HermeticDeadWait):
    def test_dormant_stamped_card_converts_to_a_recognized_procedural_block(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        fired = km._dead_wait_block(SID, GID, STAMP_T, "both workers' report-backs", self.nudged, STAMP_T + 900)
        self.assertTrue(fired)
        store = jd.load_goals(SID)
        nd = store["nodes"][GID]
        self.assertTrue(nd.get("blocked"), "the card lands in the terminal the ladder promises: blocked")
        self.assertTrue(str(nd.get("blockWhy") or "").startswith(jd.DEAD_WAIT_WHY_PREFIX))
        self.assertIn("both workers' report-backs", nd.get("blockWhy") or "",
                      "the brief names WHAT died with the session")
        self.assertTrue(jd.procedural_block_why(nd.get("blockWhy")),
                        "a dead wait is romp bookkeeping — the briefer must not invent a decision")
        # the evidence time is the newest recorded event (the settle), never wall-clock now
        blk = [e for e in nd.get("log", []) if e.get("kind") == "block"][-1]
        self.assertEqual(blk.get("ev_t"), STAMP_T + 50)

    def test_an_open_turn_last_state_stands_down_for_the_resume_machinery(self):
        _seed_store()
        _write_state("working", STAMP_T + 50)   # a restart CUT — the resume nudge owns this card
        self.assertFalse(km._dead_wait_block(SID, GID, STAMP_T, "w", self.nudged, STAMP_T + 900))
        self.assertFalse(jd.load_goals(SID)["nodes"][GID].get("blocked"))

    def test_once_per_stamp_episode_and_a_new_anchor_rearms(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        self.assertTrue(km._dead_wait_block(SID, GID, STAMP_T, "w", self.nudged, STAMP_T + 900))
        self.assertFalse(km._dead_wait_block(SID, GID, STAMP_T, "w", self.nudged, STAMP_T + 950),
                         "same episode never converts twice")
        # a genuinely NEW stamp episode (newer anchor) re-arms — but the fresh-store guard still
        # refuses while the card sits blocked, so no double-block either
        self.assertFalse(km._dead_wait_block(SID, GID, STAMP_T + 100, "w", self.nudged, STAMP_T + 990))

    def test_a_lifted_stamp_or_resolved_card_stands_down(self):
        _seed_store(awaiting=False)             # no live stamp on the fresh read
        _write_state("idle", STAMP_T + 50)
        self.assertFalse(km._dead_wait_block(SID, GID, STAMP_T, "w", self.nudged, STAMP_T + 900))

    def test_boot_catchup_sweep_converts_dormant_stores_and_spares_alive_ones(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._PREV_ALIVE = None                   # first tick after boot
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)
        self.assertTrue(jd.load_goals(SID)["nodes"][GID].get("blocked"), "boot catch-up found the dead wait")
        # …and an ALIVE session is never swept: reseed and list it as alive
        self.tearDown(); self.setUp()
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._PREV_ALIVE = None
        km._dead_wait_sweep({SID}, self.nudged, STAMP_T + 900)
        self.assertFalse(jd.load_goals(SID)["nodes"][GID].get("blocked"))

    def test_death_transition_triggers_between_ticks(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._PREV_ALIVE = {SID}                  # was alive last tick…
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)   # …gone this tick: the death event
        self.assertTrue(jd.load_goals(SID)["nodes"][GID].get("blocked"))

    def test_wake_goal_routes_its_dormant_branch_here(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("return _dead_wait_block(sid, gid, at, why, nudged, now)", src)
        self.assertIn("_dead_wait_sweep(alive_ids, nudged, now)", src)


class DeadWaitCorroboration(_HermeticDeadWait):
    """The sweep's trigger — absence from a RAW liveness listing — inherits every collapse that
    listing has (tmux list error/timeout empties the map for a cycle; a swallowed SDK live-merge
    exception does the same to the merged half), and the block it files is irreversible bookkeeping
    on the user's board with nothing to lift it when the listing returns. So absence alone NEVER
    files: the death is corroborated with the liveness OWNER first (the SDK reg's alive bit / a
    standing death record / the owner scan), and an unconfirmable candidate stands down for the
    cycle with its transition kept armed — the _confirmed_ended doctrine the kill paths follow."""

    def _blocked(self):
        return bool(jd.load_goals(SID)["nodes"][GID].get("blocked"))

    def test_a_raw_listing_collapse_alone_never_files(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._TMUX.alive_sids = lambda t=3: {SID}   # the OWNER answers alive — the raw listing blinked
        km._PREV_ALIVE = {SID}
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)   # empty alive set: the collapse shape
        self.assertFalse(self._blocked(), "an owner-corroborated ALIVE session must never convert")
        self.assertIn(SID, km._PREV_ALIVE, "the death transition stays armed for a genuine later death")

    def test_probe_failure_stands_down_and_the_next_tick_retries(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._TMUX.alive_sids = lambda t=3: None    # a REAL probe failure — cannot confirm either way
        km._PREV_ALIVE = {SID}
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)
        self.assertFalse(self._blocked(), "unconfirmed is never dead — nothing files")
        self.assertIn(SID, km._PREV_ALIVE, "the candidate is kept, not spent")
        km._TMUX.alive_sids = lambda t=3: set()   # the probe recovers and corroborates the death…
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 950)
        self.assertTrue(self._blocked(), "…and the retried tick converts")

    def test_sdk_reg_alive_bit_outranks_the_merged_maps_absence(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps({"alive": True}))
        km._PREV_ALIVE = {SID}
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)   # the swallowed SDK-merge shape
        self.assertFalse(self._blocked(),
                         "alive:True is live/revivable/crash-looped — the resume contract owns it")
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 950)
        self.assertTrue(self._blocked(), "alive:False is the owner's durable answer — it converts")

    def test_a_standing_death_record_corroborates_without_a_probe(self):
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        gone = jd.STATE / "gone"
        gone.mkdir(parents=True, exist_ok=True)
        (gone / (SID + ".json")).write_text(json.dumps({"t": STAMP_T + 60, "by": "gone"}))
        km._TMUX.alive_sids = lambda t=3: None    # even with the probe down…
        km._PREV_ALIVE = {SID}
        km._dead_wait_sweep(set(), self.nudged, STAMP_T + 900)
        self.assertTrue(self._blocked(), "…a death a corroborated writer already stamped answers")

    def test_wake_goal_headless_branch_stands_down_for_file_derived_sessions(self):
        # a no-tmux box's _alive_sessions falls back to FILE-derived sessions, which reach
        # _wake_goal absent from the merged map while genuinely ALIVE — no owner here can answer
        # for a reg-less one, so nothing may file
        _seed_store()
        _write_state("idle", STAMP_T + 50)
        km._TMUX.available = lambda: False
        store = jd.load_goals(SID)
        fired = km._wake_goal(SID, GID, (STAMP_T, "w"), self.nudged, [], store,
                              STAMP_T + 900, {}, {})
        self.assertFalse(fired)
        self.assertFalse(self._blocked(), "a reg-less file-derived session has no owner to ask")
        # …but a genuinely ENDED SDK session still converts on the same box: the reg answers
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps({"alive": False}))
        fired = km._wake_goal(SID, GID, (STAMP_T, "w"), self.nudged, [], store,
                              STAMP_T + 950, {}, {})
        self.assertTrue(fired)
        self.assertTrue(self._blocked())


if __name__ == "__main__":
    unittest.main()
