"""Self-close, deferred to idle (the user 2026-08-15): telling a session "close yourself after you've
done this thing" never worked — an agent could only kill its own process, which romp read as a CRASH
and kept the session visible as dormant. Now `romp end self` records the sid (end-on-idle.json, a
STATE file so the wish survives kernel restarts) and the pusher's sweep gives it the dashboard ×'s
clean death the moment its turn settles — the goodbye delivered first, never mid-own-turn.
SYNTHETIC fixtures only."""
import inspect
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
km = load_source("romp_kernel_endidle", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
SID3 = "33333333-4444-5555-6666-777777777777"


class _FakeBackend:
    def __init__(self):
        self.killed = []

    def kill(self, sid):
        self.killed.append(sid)
        return True


class EndOnIdle(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = {k: getattr(km, k) for k in
                      ("_parse", "_path_of", "_session_working", "_record_death",
                       "_comment_kill_all", "_send_to_app", "_push_soon", "_confirmed_ended")}
        self.saved_state = km.jd.STATE
        km.jd.STATE = Path(self.td.name)
        self.be = _FakeBackend()
        self.saved_backend_for = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._parse = lambda path, sid, now: {"turns": []}
        km._path_of = lambda sid, now=None: "/p"
        km._session_working = lambda turns: False
        self.deaths = []
        km._record_death = lambda sid, now, by: self.deaths.append((sid, by))
        km._comment_kill_all = lambda sid, be: None
        self.sent = []
        km._send_to_app = lambda app, m: self.sent.append((app, m))
        km._push_soon = lambda *a, **k: None
        # the liveness owner's affirmative answer (the #85 honesty gate) — corroborated by default,
        # so each test states only the wedge it is about (**kw: the sweep passes fresh=/scan=;
        # EndOnIdleRealCorroboration below pins what those mean against the real probe)
        km._confirmed_ended = lambda sid, **kw: True

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(km, k, v)
        km.Sessions.backend_for = self.saved_backend_for
        km.jd.STATE = self.saved_state
        self.td.cleanup()

    def test_the_wish_survives_in_state_and_round_trips(self):
        km._end_on_idle_save({SID})
        self.assertEqual(km._end_on_idle_load(), {SID})
        self.assertEqual(json.loads((km.jd.STATE / "end-on-idle.json").read_text()), [SID])

    def test_the_sweep_kills_at_the_turns_settle_with_the_clean_death(self):
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {SID: {"state": ""}})
        self.assertEqual(self.be.killed, [SID])
        self.assertEqual(self.deaths, [(SID, "kill")], "the dashboard ×'s intentional death, never a crash")
        self.assertIn(("chat", {"type": "closed", "id": SID}), self.sent, "the tab closes like the × path")
        self.assertEqual(km._end_on_idle_load(), set(), "the wish is spent")

    def test_an_open_turn_defers_the_kill(self):
        km._session_working = lambda turns: True
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {SID: {"state": ""}})
        self.assertEqual(self.be.killed, [], "the turn it asked from is still open — its end is the event")
        self.assertEqual(km._end_on_idle_load(), {SID}, "the wish stands for the next sweep")

    def test_a_sid_already_dead_retires_its_request_without_a_kill(self):
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {})              # absent AND the owner corroborates → dead by some other path
        self.assertEqual(self.be.killed, [])
        self.assertEqual(self.deaths, [], "no second death record over whatever really happened")
        self.assertEqual(km._end_on_idle_load(), set())

    def test_a_wedged_kill_records_no_death_and_keeps_the_request(self):
        # tmux's kill is fire-and-forget (kill_by_name returns True regardless), and the same wedged
        # server that swallows it also fails the corroborating probe — an uncorroborated death here
        # would stamp a LIVE session dead, kill its comment threads and dismiss its tab on every client
        km._confirmed_ended = lambda sid, **kw: None
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {SID: {"state": ""}})
        self.assertEqual(self.be.killed, [SID], "the kill is still attempted")
        self.assertEqual(self.deaths, [], "no death record without the owner's affirmative answer")
        self.assertEqual(self.sent, [], "no closed broadcast for a death nobody confirmed")
        self.assertEqual(km._end_on_idle_load(), {SID}, "the request stays armed — the next sweep retries")

    def test_a_kill_the_owner_says_did_not_take_keeps_the_request(self):
        km._confirmed_ended = lambda sid, **kw: False   # still listed after the kill — it didn't land
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {SID: {"state": ""}})
        self.assertEqual(self.be.killed, [SID])
        self.assertEqual(self.deaths, [], "the owner says alive — recording a death would be a lie")
        self.assertEqual(self.sent, [])
        self.assertEqual(km._end_on_idle_load(), {SID})

    def test_a_flaky_listing_never_spends_the_request_while_the_owner_says_alive(self):
        # the RAW snapshot collapses any exec error/timeout to [] (the #85 collapse), so absence
        # there alone is one flaky read — spent on it, the user's deferred-end gesture would be
        # discarded silently, no kill ever attempted
        km._confirmed_ended = lambda sid, **kw: False
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {})
        self.assertEqual(self.be.killed, [], "not in the snapshot → nothing to kill this cycle")
        self.assertEqual(self.deaths, [])
        self.assertEqual(km._end_on_idle_load(), {SID}, "the request stands for the next cycle")

    def test_a_failed_probe_on_an_absent_sid_keeps_the_request(self):
        km._confirmed_ended = lambda sid, **kw: None    # cannot confirm either way — stand down
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {})
        self.assertEqual(self.be.killed, [])
        self.assertEqual(self.deaths, [])
        self.assertEqual(km._end_on_idle_load(), {SID})


class EndOnIdleRealCorroboration(unittest.TestCase):
    """The sweep against the REAL _confirmed_ended, under the pusher cycle's pinned liveness
    snapshot (_live_scope, taken at cycle START — see _pusher_cycle). The kill branch's
    precondition is the sid being IN that snapshot, so a post-kill corroboration that reads it
    answers "still running" unconditionally and the clean death (record, closed broadcast, spent
    request) is unreachable — the probe must outrun the snapshot to the owner's fresh answer.
    Owner probes are stubbed to answer "dead"; the lambda-stub tests above pin the gating
    arithmetic, these pin what evidence the probes are allowed to read."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = {k: getattr(km, k) for k in
                      ("_parse", "_path_of", "_session_working", "_record_death",
                       "_comment_kill_all", "_send_to_app", "_push_soon")}
        self.saved_state = km.jd.STATE
        km.jd.STATE = Path(self.td.name)
        self.be = _FakeBackend()
        self.saved_backend_for = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._parse = lambda path, sid, now: {"turns": []}
        km._path_of = lambda sid, now=None: "/p"
        km._session_working = lambda turns: False
        self.deaths = []
        km._record_death = lambda sid, now, by: self.deaths.append((sid, by))
        km._comment_kill_all = lambda sid, be: None
        self.sent = []
        km._send_to_app = lambda app, m: self.sent.append((app, m))
        km._push_soon = lambda *a, **k: None
        # the cycle's pinned snapshot, exactly as _pusher_cycle serves it to every read on this
        # thread — taken at cycle start, i.e. BEFORE any kill this sweep performs
        km._live_scope.snapshot = {SID: {"state": ""}}
        # the owner's fresh answers, both layers dead: the live merge lacks the sid and the
        # identity scan answers WITHOUT it (never None — that is the probe-failure verdict)
        self.saved_live = km.Sessions.live
        km.Sessions.live = staticmethod(lambda: {})
        self.scans = []                                   # one entry per alive_sids fork
        km._TMUX.available = lambda: True                 # instance attrs shadow the class methods —
        km._TMUX.alive_sids = lambda t=3: (self.scans.append(1), set())[1]   # removed in teardown

    def tearDown(self):
        km._live_scope.snapshot = None                    # _pusher_cycle's finally does the same
        km.Sessions.live = self.saved_live
        del km._TMUX.available, km._TMUX.alive_sids
        for k, v in self.saved.items():
            setattr(km, k, v)
        km.Sessions.backend_for = self.saved_backend_for
        km.jd.STATE = self.saved_state
        self.td.cleanup()

    def test_the_post_kill_probe_outruns_the_cycle_snapshot(self):
        km._end_on_idle_save({SID})
        km._end_on_idle_sweep(1000, {SID: {"state": ""}})
        self.assertEqual(self.be.killed, [SID])
        self.assertEqual(self.deaths, [(SID, "kill")],
                         "the pinned snapshot predates the kill — corroborating from it certifies "
                         "'still running' forever and the clean death never lands")
        self.assertIn(("chat", {"type": "closed", "id": SID}), self.sent,
                      "the tab closes like the × path — same cycle, not next kernel boot")
        self.assertEqual(km._end_on_idle_load(), set(), "confirmed same-cycle → the wish is spent")

    def test_one_owner_scan_serves_the_whole_absent_pass(self):
        # the wedge shape: the snapshot collapsed empty, every armed sid reads absent — the
        # corroborating probes must share ONE owner scan (the death sweep's batch idiom), never
        # fork a subprocess per sid per 0.5s cycle
        km._live_scope.snapshot = {}
        km._end_on_idle_save({SID, SID2, SID3})
        km._end_on_idle_sweep(1000, {})
        self.assertEqual(self.be.killed, [], "absent sids are corroborated, never killed")
        self.assertEqual(km._end_on_idle_load(), set(), "the owner confirms all three deaths")
        self.assertEqual(len(self.scans), 1, "one shared scan per pass, not one per sid")

    def test_the_post_kill_probe_never_reuses_the_pass_scan(self):
        # freshness split: the absent branch's claim is cycle-old, so the shared scan serves it —
        # but the post-kill probe's evidence must POSTDATE the kill, so it takes its own. A world
        # the kill mutates makes reuse visible: the pass scan (taken first, for the absent sid)
        # still lists the victim; only a post-kill scan sees it gone.
        world = {SID2}
        km.Sessions.live = staticmethod(lambda: {s: {"state": ""} for s in world})
        km._TMUX.alive_sids = lambda t=3: (self.scans.append(1), set(world))[1]
        self.be.kill = lambda sid: (self.be.killed.append(sid), world.discard(sid), True)[2]
        km._live_scope.snapshot = {SID2: {"state": ""}}
        km._end_on_idle_save({SID, SID2})                # SID sorts first: absent → the pass scan
        km._end_on_idle_sweep(1000, {SID2: {"state": ""}})
        self.assertEqual(self.be.killed, [SID2])
        self.assertEqual(self.deaths, [(SID2, "kill")],
                         "a probe reusing the pre-kill pass scan would still list the victim")
        self.assertEqual(len(self.scans), 2, "the shared pass scan plus the post-kill's own")
        self.assertEqual(km._end_on_idle_load(), set())

    def test_sessions_live_stays_snapshot_free(self):
        # fresh=True's whole contract rests on Sessions.live() never consulting the pusher cycle's
        # pinned snapshot. The tests above stub Sessions.live (they pin the SWEEP's arithmetic), so
        # nothing else would notice a refactor routing it through _live_scope/_tmux_sessions — say,
        # extending the pinned-read CPU win one level down — which would quietly re-open the
        # pre-kill-evidence defect this class exists to keep closed.
        src = inspect.getsource(self.saved_live)
        self.assertNotIn("_live_scope", src, "Sessions.live must read the world, not the cycle pin")
        self.assertNotIn("_tmux_sessions(", src,
                         "_tmux_sessions serves the pinned snapshot when a cycle holds one")


class EndOnIdleWiring(unittest.TestCase):
    def test_the_route_and_spawn_env_wiring_is_pinned(self):
        src = Path(BIN, "romp-kernel").read_text()
        self.assertIn('b.get("when") == "idle"', src, "/end honors the deferral")
        self.assertIn('{"ok": True, "deferred": True}', src)
        self.assertIn("_end_on_idle_sweep(now, tmux)", src, "the sweep rides the pusher's tick jobs")
        sdk = Path(os.path.dirname(BIN), "kernel", "sdk_backend.py").read_text()
        self.assertIn('"ROMP_SID": str(sess.sid)', sdk,
                      "the CLI process carries the session's stable identity for `romp end self`")
        cli = Path(BIN, "romp").read_text()
        self.assertIn('"romp end self: ROMP_SID is not set', cli)


if __name__ == "__main__":
    unittest.main()
