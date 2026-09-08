#!/usr/bin/env python3
"""The pusher's minimum interval between cycle starts, and the watched-tab exemption (perf round 5,
decision 3, 2026-09-08).

Round 4 made the builders three to five times cheaper and the process line did not move: the pusher was
wall-saturated, so cheaper cycles became twice as many cycles. PUSH_MIN_INTERVAL_S bounds the cycle
START rate; the one exemption is a wake whose cause is a change to the live tail of a chat tab a
connected client is watching (streamed text, an echo), which runs its cycle at once. The wake carries
its cause: _pusher_wake_live(sid) records the sid before it sets the event, and the loop reads the set
after it clears the event, so the exemption keys on the event and on the client's own word (its active
tab), never on a guess.

The real `_pusher` loop runs here on a fake clock and a fake wake event: no sleeps, every wake placed at
an exact time with an exact cause, and `_pusher_cycle` replaced by a stand-in that records each start and
moves the clock by the cycle's duration. Times are binary fractions (multiples of 1/8 s) so every sum is
exact. Synthetic sids only.
"""
import inspect
import os
import random
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ.pop("ROMP_PUSH_MIN_INTERVAL", None)      # the default constant is under test; the override has its own test
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_cadence", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_cadence", os.path.join(BIN, "romp_sdk_backend.py"))

WATCHED = "11111111-2222-3333-4444-555555555555"     # the tab a connected chat client is looking at
OTHER = "11111111-2222-3333-4444-666666666666"       # a session nobody is looking at
CYCLE = 0.25                                         # the stand-in cycle's duration


class _Stop(Exception):
    """Raised by the fake wake when a wait would move the clock past the run's horizon: the loop is
    `while True`, and stopping inside a wait leaves the counters covering completed waits only."""


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FakeWake:
    """A threading.Event stand-in for the pusher loop, driven by a schedule of wakes on the fake clock.
    A wake is (t, kind, sid): kind "plain" is a set() with no cause (a poke, a drive op, a dirty mark);
    "live" is _pusher_wake_live(sid), the cause recorded then the flag set, in that order. wait(timeout)
    first fires every wake already due (one that arrived while the cycle ran), answers True at once when
    the flag is set, else moves the clock to the next wake inside the timeout and fires it (True), else
    moves the clock by the timeout (False)."""

    def __init__(self, kernel, clock, schedule, until):
        self.km, self.clock, self.until = kernel, clock, until
        self.schedule = sorted(schedule, key=lambda w: w[0])
        self.flag = False
        self.fired = []

    def _fire(self, w):
        _t, kind, sid = w
        if kind == "live":
            self.km._note_live_wake(sid)
        self.km._PERF_STATS.wake()                  # what _CountedEvent.set counts
        self.flag = True
        self.fired.append(w)

    def _fire_due(self):
        while self.schedule and self.schedule[0][0] <= self.clock.t:
            self._fire(self.schedule.pop(0))

    def _advance(self, t):
        if t > self.until:
            raise _Stop()
        self.clock.t = t

    def wait(self, timeout):
        self._fire_due()
        if self.flag:
            return True
        if self.schedule and self.schedule[0][0] <= self.clock.t + timeout:
            self._advance(self.schedule[0][0])
            self._fire_due()
            return True
        self._advance(self.clock.t + timeout)
        return False

    def clear(self):
        self.flag = False

    def is_set(self):
        return self.flag


def run_loop(kernel, schedule, until, cycle_s=CYCLE, watched=(WATCHED,), durations=None):
    """Run the REAL kernel._pusher on the fake clock until `until`; return (cycle start times, the
    pusher counters). `durations`: per-cycle durations, else `cycle_s` for every cycle. `watched`: the
    active tab of each connected chat client for the run."""
    clock = FakeClock()
    wake = FakeWake(kernel, clock, schedule, until)
    starts = []

    def cycle():
        d = durations[len(starts)] if durations else cycle_s
        starts.append(clock.t)
        kernel._PERF_STATS.cycle(d, 0.0)
        clock.t += d

    kernel._PERF_STATS.reset()
    kernel._take_live_wake_sids()                     # start with an empty register
    with kernel._clients_lock:
        saved_clients = list(kernel._clients)
        kernel._clients[:] = [{"app": "chat", "active": s, "alive": True} for s in watched]
    saved_cycle = kernel._pusher_cycle
    kernel._pusher_cycle = cycle
    try:
        kernel._pusher(clock=clock, wake=wake)
    except _Stop:
        pass
    finally:
        kernel._pusher_cycle = saved_cycle
        with kernel._clients_lock:
            kernel._clients[:] = saved_clients
        kernel._take_live_wake_sids()                 # leave the register empty for the next test
    return starts, kernel._PERF_STATS.snapshot()["pusher"], wake


class MinimumInterval(unittest.TestCase):
    """Cycle starts are at least PUSH_MIN_INTERVAL_S apart unless a watched tab's live tail woke the loop."""

    def setUp(self):
        self.assertEqual(km.PUSH_MIN_INTERVAL_S, 1.0, "the default bound; every time below assumes it")
        self.assertEqual(km.PUSH_BACKSTOP_S, 0.5)

    def counters(self, p, **want):
        got = {k: p[k] for k in want}
        for k in ("held_ms",):
            if k in got:
                self.assertAlmostEqual(got.pop(k), want.pop(k), places=6, msg=k)
        self.assertEqual(got, want)

    def test_two_plain_wakes_run_their_cycles_one_interval_apart(self):
        # cycle 0 runs 0 to 0.25; wakes at 0.375 and 0.5 both land inside the interval; the one cycle
        # they get starts at 1.0 (1.0 s after cycle 0 began), not at 0.375
        starts, p, _ = run_loop(km, [(0.375, "plain", None), (0.5, "plain", None)], until=1.5)
        self.assertEqual(starts, [0.0, 1.0])
        self.counters(p, cycles=2, wakes=2, wakes_live=0, wakes_event=1, wakes_backstop=0,
                      held=1, held_ms=625.0, exempt=0)        # due at 0.375, ran at 1.0

    def test_a_watched_tab_live_wake_runs_its_cycle_at_once(self):
        starts, p, _ = run_loop(km, [(0.375, "live", WATCHED)], until=1.0)
        self.assertEqual(starts, [0.0, 0.375], "the chat pane the user is looking at is as live as before")
        self.counters(p, cycles=2, wakes=1, wakes_live=1, wakes_event=1, wakes_backstop=0,
                      held=0, held_ms=0.0, exempt=1)

    def test_a_live_wake_for_a_tab_nobody_watches_is_held(self):
        starts, p, _ = run_loop(km, [(0.375, "live", OTHER)], until=1.5)
        self.assertEqual(starts, [0.0, 1.0])
        self.counters(p, wakes_live=1, held=1, held_ms=625.0, exempt=0)

    def test_a_watched_tab_wake_is_held_when_no_chat_client_is_connected(self):
        # the exemption reads the CLIENTS at the moment of the decision: the same wake with nobody
        # watching that tab is an ordinary wake
        starts, p, _ = run_loop(km, [(0.375, "live", WATCHED)], until=1.5, watched=())
        self.assertEqual(starts, [0.0, 1.0])
        self.counters(p, wakes_live=1, held=1, exempt=0)

    def test_wakes_during_a_hold_coalesce_into_the_one_held_cycle(self):
        sched = [(0.375, "plain", None), (0.5, "plain", None), (0.625, "live", OTHER), (0.875, "plain", None)]
        starts, p, wake = run_loop(km, sched, until=1.5)
        self.assertEqual(starts, [0.0, 1.0], "four wakes inside the interval, one cycle for all of them")
        self.assertEqual(len(wake.fired), 4, "every wake was delivered before the held cycle ran")
        self.assertEqual(km._take_live_wake_sids(), frozenset(), "nothing left unread: the cycle served it")
        self.counters(p, cycles=2, wakes=4, wakes_live=1, wakes_event=1, wakes_backstop=0,
                      held=1, held_ms=625.0, exempt=0)

    def test_a_watched_tab_wake_during_a_hold_ends_the_hold(self):
        # a plain wake at 0.375 starts the hold; the watched tab's tail changes at 0.75: the cycle runs
        # then, not at 1.0. The cycle counts as held (it was delayed 0.375 s) AND exempt (it ran inside
        # the interval on the exemption), as the counters' definitions say
        starts, p, _ = run_loop(km, [(0.375, "plain", None), (0.75, "live", WATCHED)], until=1.2)
        self.assertEqual(starts, [0.0, 0.75])
        self.counters(p, cycles=2, wakes=2, wakes_live=1, wakes_event=1, held=1, held_ms=375.0, exempt=1)

    def test_the_backstop_alone_runs_at_most_one_cycle_per_interval(self):
        # no wakes at all: the 0.5 s backstop ends each wait at cycle end + 0.5 (0.75), and the interval
        # holds the next start to 1.0; cycles at 0, 1, 2, 3 instead of 0, 0.75, 1.5, 2.25
        starts, p, _ = run_loop(km, [], until=3.6)
        self.assertEqual(starts, [0.0, 1.0, 2.0, 3.0])
        self.counters(p, cycles=4, wakes=0, wakes_event=0, wakes_backstop=3, held=3, held_ms=750.0, exempt=0)

    def test_a_cycle_longer_than_the_interval_is_never_held_and_exempts_nothing(self):
        # cycle 0 runs 1.5 s; the watched tab's wake at 1.625 is past the deadline, so it is an ordinary
        # wake: no hold to skip, so `exempt` stays exact (it counts bypasses, not watched-tab wakes)
        starts, p, _ = run_loop(km, [(1.625, "live", WATCHED)], until=2.5, cycle_s=1.5)
        self.assertEqual(starts, [0.0, 1.625])
        self.counters(p, wakes_live=1, wakes_event=1, held=0, held_ms=0.0, exempt=0)

    def test_interval_zero_is_the_loop_as_it_was(self):
        saved = km.PUSH_MIN_INTERVAL_S
        km.PUSH_MIN_INTERVAL_S = 0.0
        try:
            starts, p, _ = run_loop(km, [(0.375, "plain", None), (0.5, "plain", None)], until=1.2)
        finally:
            km.PUSH_MIN_INTERVAL_S = saved
        # cycle 1 starts on the first wake; the second wake lands during cycle 1 and starts cycle 2 the
        # moment it ends: three cycles in 0.875 s, the pre-interval loop
        self.assertEqual(starts, [0.0, 0.375, 0.625])
        self.counters(p, cycles=3, wakes=2, wakes_event=2, wakes_backstop=0, held=0, held_ms=0.0, exempt=0)

    def test_sixty_seconds_of_synthetic_wakes(self):
        """A seeded minute of wakes at about the live rate (one set() per second, half of them live-tail,
        a tenth of those for the watched tab) with cycle durations spread around the live p50: every gap
        between cycle starts shorter than the interval is an exempt cycle and there are exactly `exempt`
        of them; the same minute with no chat client connected has no short gap at all; and the bound
        yields fewer cycles than the loop without it."""
        rng = random.Random(20260908)
        sched = []
        t = 0.0
        while t < 60.0:
            t += rng.expovariate(1.0)
            kind = "live" if rng.random() < 0.5 else "plain"
            sid = (WATCHED if rng.random() < 0.1 else OTHER) if kind == "live" else None
            sched.append((t, kind, sid))
        durations = [min(6.0, rng.lognormvariate(-0.18, 0.55)) for _ in range(2000)]   # median 0.84 s, p90 ~1.7 s

        starts, p, _ = run_loop(km, list(sched), until=60.0, durations=durations)
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        short = [g for g in gaps if g < km.PUSH_MIN_INTERVAL_S - 1e-9]
        self.assertEqual(len(short), p["exempt"], "a gap inside the interval is an exempt cycle, and only that")
        self.assertGreater(p["exempt"], 0, "the seed produced watched-tab wakes inside the interval")
        self.assertGreater(p["held"], 0)
        self.assertLessEqual(p["held_ms"], p["held"] * km.PUSH_MIN_INTERVAL_S * 1000.0 + 1e-6,
                             "no hold is longer than the interval")

        starts0, p0, _ = run_loop(km, list(sched), until=60.0, durations=durations, watched=())
        self.assertEqual([g for g in zip(starts0, starts0[1:]) if g[1] - g[0] < km.PUSH_MIN_INTERVAL_S - 1e-9], [],
                         "with no chat client connected every gap is at least the interval")
        self.assertEqual(p0["exempt"], 0)

        saved = km.PUSH_MIN_INTERVAL_S
        km.PUSH_MIN_INTERVAL_S = 0.0
        try:
            starts_free, p_free, _ = run_loop(km, list(sched), until=60.0, durations=durations)
        finally:
            km.PUSH_MIN_INTERVAL_S = saved
        self.assertGreater(len(starts_free), len(starts), "the bound runs fewer cycles for the same wakes")
        self.assertEqual(p_free["held"], 0)


class EnvOverride(unittest.TestCase):
    def test_romp_push_min_interval_sets_the_constant(self):
        os.environ["ROMP_PUSH_MIN_INTERVAL"] = "2.5"
        try:
            km2 = load_source("romp_kernel_cadence_env", os.path.join(BIN, "romp-kernel"))
        finally:
            os.environ.pop("ROMP_PUSH_MIN_INTERVAL", None)
        self.assertEqual(km2.PUSH_MIN_INTERVAL_S, 2.5)
        self.assertEqual(km.PUSH_MIN_INTERVAL_S, 1.0, "the default copy is untouched")
        starts, p, _ = run_loop(km2, [(0.375, "plain", None)], until=3.0)
        self.assertEqual(starts, [0.0, 2.5], "the loop reads the overridden bound")
        self.assertEqual(p["held"], 1)


class WakeCause(unittest.TestCase):
    """How a wake carries its cause, and who records one."""

    def setUp(self):
        km._take_live_wake_sids()
        km._pusher_wake.clear()

    def tearDown(self):
        km._take_live_wake_sids()
        km._pusher_wake.clear()

    def test_a_live_wake_records_the_sid_then_sets_the_event(self):
        before = km._PERF_STATS.snapshot()["pusher"]
        km._pusher_wake_live(WATCHED)
        km._pusher_wake_live(OTHER)
        km._pusher_wake_live(WATCHED)                 # a burst for one sid is one entry
        self.assertTrue(km._pusher_wake.is_set())
        after = km._PERF_STATS.snapshot()["pusher"]
        self.assertEqual(after["wakes"] - before["wakes"], 3, "a live wake is a wake: the set() counts as before")
        self.assertEqual(after["wakes_live"] - before["wakes_live"], 3)
        self.assertEqual(km._take_live_wake_sids(), frozenset({WATCHED, OTHER}))
        self.assertEqual(km._take_live_wake_sids(), frozenset(), "the take clears")

    def test_a_plain_wake_records_nothing(self):
        km._push_soon()
        km._mark_views_dirty()
        km._wake_kernel()
        self.assertTrue(km._pusher_wake.is_set())
        self.assertEqual(km._take_live_wake_sids(), frozenset())

    def test_watched_sids_are_the_active_tabs_of_alive_ready_chat_clients(self):
        with km._clients_lock:
            saved = list(km._clients)
            km._clients[:] = [
                {"app": "chat", "active": WATCHED, "alive": True},
                {"app": "chat", "active": OTHER, "alive": False},          # a dead socket watches nothing
                {"app": "chat", "active": "11111111-2222-3333-4444-777777777777", "ready": False},   # behind the ready gate
                {"app": "feed", "active": "11111111-2222-3333-4444-888888888888"},                   # not a chat client
                {"app": "chat", "alive": True},                             # no active tab yet
            ]
        try:
            self.assertEqual(km._watched_sids(), {WATCHED})
            self.assertTrue(km._live_wake_watched(frozenset({OTHER, WATCHED})))
            self.assertFalse(km._live_wake_watched(frozenset({OTHER})))
            self.assertFalse(km._live_wake_watched(frozenset()))
        finally:
            with km._clients_lock:
                km._clients[:] = saved

    def test_the_tmux_echo_is_a_live_wake_for_its_sid(self):
        saved = km._sdk
        km._sdk = lambda: None                        # no SDK backend owns the sid: the tmux echo path
        try:
            km._optimistic_echo(OTHER, "a typed message")
        finally:
            km._sdk = saved
            with km._tmux_echo_lock:
                km._tmux_echo.pop(OTHER, None)
        self.assertTrue(km._pusher_wake.is_set())
        self.assertEqual(km._take_live_wake_sids(), frozenset({OTHER}))

    def test_the_kernel_hands_the_sdk_backend_the_cause_carrying_wake(self):
        with open(os.path.join(BIN, "romp-kernel")) as f:
            src = f.read()
        i = src.index("_sdk_backend = sbmod.SdkBackend(")
        self.assertIn("push_live=_pusher_wake_live", src[i:i + 600])
        self.assertIn("push=_pusher_wake.set", src[i:i + 600], "the plain wake stays for everything else")


class SdkBackendSites(unittest.TestCase):
    """The SDK backend's live-tail sites wake with the sid; its other sites wake plainly."""

    def bare(self):
        be = sb.SdkBackend.__new__(sb.SdkBackend)
        be._log = lambda m: None
        be.plain, be.live = [], []
        be._push_cb = lambda: be.plain.append(True)
        be._push_live_cb = be.live.append
        return be

    def test_wake_push_live_calls_the_cause_carrying_callback(self):
        be = self.bare()
        be._wake_push_live(WATCHED)
        self.assertEqual((be.live, be.plain), ([WATCHED], []))

    def test_without_the_callback_it_falls_back_to_the_plain_wake(self):
        be = self.bare()
        be._push_live_cb = None                        # an older kernel that wired only `push`
        be._wake_push_live(WATCHED)
        self.assertEqual((be.live, be.plain), ([], [True]))
        del be._push_live_cb                           # a bare backend a test built without the attribute
        be._wake_push_live(WATCHED)
        self.assertEqual(be.plain, [True, True])

    def test_a_failing_callback_still_wakes(self):
        be = self.bare()
        said = []
        be._log = said.append

        def boom(sid):
            raise RuntimeError("no")
        be._push_live_cb = boom
        be._wake_push_live(WATCHED)
        self.assertEqual(be.plain, [True], "the cause is lost, the wake is not")
        self.assertEqual(len(said), 1)

    def test_the_constructor_takes_and_stores_push_live(self):
        params = inspect.signature(sb.SdkBackend.__init__).parameters
        self.assertIn("push_live", params)
        self.assertIsNone(params["push_live"].default)
        init = inspect.getsource(sb.SdkBackend.__init__)
        self.assertIn("self._push_live_cb = push_live", init)

    def test_every_live_tail_site_carries_its_sid(self):
        # the sites that follow a change to ONE sid's live tail (_stash_live / _touch_live): a streamed
        # atom, the send echo, an unqueued echo, a dismissed echo, the dropped-echo flags, a command chip
        live_sites = {"_forward": "sess.sid", "send": "sid", "unqueue": "sid", "dismiss_echo": "sid",
                      "_mark_dropped_echoes": "sid", "_ack_cmd_chip": "sid"}
        for name, arg in live_sites.items():
            src = inspect.getsource(getattr(sb.SdkBackend, name))
            self.assertIn("self._wake_push_live(%s)" % arg, src, name)
            self.assertNotIn("self._wake_push()", src, "%s: a live-tail site must not wake without its cause" % name)
        # the sites that wake for something other than a tail change keep the plain wake
        for name in ("set_fast", "set_env"):
            src = inspect.getsource(getattr(sb.SdkBackend, name))
            self.assertIn("self._wake_push()", src, name)
            self.assertNotIn("_wake_push_live(", src, name)


if __name__ == "__main__":
    unittest.main()
