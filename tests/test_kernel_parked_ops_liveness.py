#!/usr/bin/env python3
"""Parked ops deliver on the SETTLE event, independent of the judge pass (2026-09-03).

The kernel parks a user's input while its session is busy, compacting, or limit-held, and delivers the
queue FIFO once the session is quiet (_apply_pending_ops). Until this change the ONLY caller of that
function was the tail of the judge producer's pass, after an untimed join on the judge tiers — so every
parked op in every session waited for the judges to finish. A judge pass can run for hours: one session's
closer sweep, alarm-killed turn after turn, held a pass for 6h22m, and a typed /clear parked mid-turn sat
as a queued chip the whole time until the user cancelled it. The drain now rides the pusher cycle, woken
by the backends' turn-end poke (_wake_kernel), by /tick, by every queue mutation, and by its own 0.5 s
backstop; the producer never touches it.

THE PRODUCER UNDER TEST IS A REAL KERNEL LOOP, and it is ended on every exit path (2026-09-21). The delivery
test starts km._producer against judge tiers stuck on a gate. Two things went wrong with the way it used to end it:
  1. The boot hold. Kernel commit 3421c94d0 (2026-09-11) put a bounded wait for the boot's attachDone in front of the
     producer's FIRST pass (BOOT_JUDGE_HOLD_S, 8 s; _wait_boot_attached). This module predates the hold (2026-09-03)
     and proves nothing about it. The defect is a CONDITION, not a frequency: _BOOT_ATTACHED (kernel/kernel.py:30789,
     set at :30860) is a one-way, process-wide latch, never cleared, and this test patches km._sdk to lambda: None, so
     it can never latch it itself; the test passes if and only if something earlier in the same interpreter already
     latched it, and fails otherwise, the 8 s hold outlasting its 5 s poll, on "a judge pass is in flight". Alone
     serially: always red. The module serially: green (its alphabetically first test's km._pusher_cycle() reaches _sdk()
     through _turn_notify_tick and _alive_sessions and builds a real SdkBackend whose boot reconcile latches it as a
     side effect). The module under -n 9: red. A full -n 10 sweep: a prior latcher in the target's worker is likely but
     not guaranteed: five full sweeps checked on 2026-09-21 did not fire it (those for 853, 862 twice and 887, and 781's
     at c7e51ae47) and one did (box 2's control at 65f1895f6). An isolated-level certainty and a sweep-level flake at the
     same time, decided by which tests ran before it in that worker's process; never in CI (serial). The red-before
     measurement is the single test alone, serially. setUp neutralises the hold with the stub tests/test_judges_process.py
     uses (a lambda returning True), here as one of setUp's patchers, each stopped by a cleanup registered as it starts
     (unittest skips tearDown when setUp raises, and runs the cleanups), so every road restores it.
  2. The stop on the tail. The stop seam, the gate release and the join were the body's LAST lines, so the failed
     assertion skipped them, the with-block's eleven patches were undone on the way out while the producer was still in
     its hold, and a live, fully unpatched judge loop ran for the rest of the worker's life, wherever that failure fired;
     whether a given sweep carried it is read from that sweep's pytest log (the target's failure line is in it, or it is
     not: the contamination disclosure is conditional on that line). tearDown only CLEARED the
     stop flag, and only once the producer was already dead. The T282 census named the leaked thread (the ERROR beside
     the FAILED) but could not stop it. The blast radius has TWO FIGURES with different meanings (romp-manager's probe,
     2026-09-21). REACH: the leaked loop's 3 s backstop (_producer_wake.wait(3)) runs _compact_goal_stores() over
     jd.GOALDIR, and km.jd is the ONE process-wide judge module (kernel/kernel.py:52, jd = load_source("romp_judge",
     ...): one object per interpreter) that 141 callers among the test modules rebind, through jd._rebind_state(), onto their own roots, so the loop follows
     jd.GOALDIR to wherever the LATEST rebind put it: any of those 141 scheduled after the failure in the same worker.
     VISIBLE SET: 13 modules save stores with cleared roots and 18 assert on the archive; that is where a wrong result
     would surface, a spurious pass or a spurious failure in a module that did nothing wrong, and the spurious pass is
     the dangerous direction. 13 is not the exposure; 141 is the reach. Whether the leaked loop produced flakes in
     earlier sweeps was not determined.
     Now everything a failed assertion must not skip is a CLEANUP registered BEFORE the producer starts: the stop (the
     seam first, the gate second, a bounded join), then the pass's stubs, then the census; unittest runs cleanups after
     tearDown, LIFO, on every exit path, so the producer ends under its stubs and the census reads the threads last.
     test_a_body_that_fails_before_its_tail_leaves_no_producer_behind proves both shapes by execution.

SYNTHETIC fixtures only: a placeholder uuid, invented texts.
"""
import contextlib
import inspect
import io
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from unittest import mock
from romp_load import load_source

from tests.conftest import thread_census, wait_for_census

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_parkedlive", os.path.join(BIN, "romp-kernel"))

# The ACCOUNT gate is a separate axis (tests/test_kernel_limit_queue.py); pinned off so the real
# machine's usage.json can never make these tests park for a reason none of them is about.
km._limit_hold = lambda sid, usage=None: None

SID = "11111111-2222-3333-4444-555555555555"

# Every pusher-cycle job except the drain, quieted so a cycle run here does exactly one thing.
_OTHER_JOBS = ("_push_all", "_lift_spent_awaiting", "_death_sweep_tick", "_end_on_idle_sweep",
               "_deferral_sweep_tick", "_auto_nudge_tick", "_interrupt_block_tick", "_auto_pause_on_limit",
               "_usage_poll_tick", "_auto_pause_on_spend_limit", "_auto_resume_retry",
               "_auto_resume_session_retry", "_auto_retry_tick", "_idle_queue_drive_tick",
               "_clear_done_working_notes")


class _FakeBackend:
    """A backend that cannot forward its own sends (the ABC's default), so a send parks while the turn is open."""

    def __init__(self):
        self.calls = []
        self.open = True

    def busy(self, sid):
        return self.open

    def forwards_sends(self):
        return False

    def send(self, sid, text):
        self.calls.append(("send", text))
        self.open = True                  # as SdkBackend.send: the turn is pending under the lock before send() returns
        return True

    def set_model(self, sid, value):
        self.calls.append(("model", value))
        return True

    def turn_seq(self, sid):
        return 0


class DeliveryRidesTheSettle(unittest.TestCase):
    _CENSUS_WAIT_S = 5.0                 # wait_for_census's bound; a nested case that leaks on purpose shortens it

    def setUp(self):
        self._census0 = thread_census()
        # The T282 pin is a CLEANUP registered first, so it runs LAST: unittest runs tearDown, then the cleanups LIFO, so
        # every stop a body registers (the producer's, in _pass_in_flight) has run before the census reads the threads.
        self.addCleanup(self._census_check)
        self.be = _FakeBackend()
        # Each patcher's stop is a cleanup registered AS IT STARTS (2026-09-22): unittest does not run tearDown when setUp
        # raises, but it runs the cleanups, so a failure inside this loop unwinds exactly the patchers that started and
        # leaves km unpatched; a stop list walked in tearDown left every patcher installed on that road, process-wide.
        for p in self._patchers():
            p.start()
            self.addCleanup(p.stop)
        km._pending_ops.clear()
        km._moving.clear()
        km._drain_hold.clear()
        km._pusher_wake.clear()
        km._producer_wake.clear()

    def _patchers(self):
        """setUp's patchers, in the order they start (a nested case overrides this to plant a failure among them)."""
        return [
            mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: self.be)),
            mock.patch.object(km, "_compacting_now", lambda sid, **k: False),
            mock.patch.object(km, "_mark_compacting", lambda sid: None),
            mock.patch.object(km, "_names_snapshot", lambda: {}),
            mock.patch.object(km, "_live_map", lambda: {SID: {"state": "waiting", "backend": "sdk"}}),
            # The boot hold (kernel 3421c94d0): the producer's FIRST pass waits up to BOOT_JUDGE_HOLD_S for attachDone,
            # which nothing in this module fires (km._sdk is stubbed: the one side-effect latcher is gone). Released with
            # the stub tests/test_judges_process.py uses (a lambda returning True), here as one of setUp's patchers, each
            # stopped by a cleanup registered as it starts, so it is restored on every road (a setUp that raises included:
            # unittest skips tearDown then and runs the cleanups); the hold is a boot-time gate on the first pass,
            # orthogonal to everything asserted here. The 5 s poll for the pass below stays as it was.
            mock.patch.object(km, "_wait_boot_attached", lambda timeout=None: True),
        ] + [mock.patch.object(km, name, lambda *a, **k: None) for name in _OTHER_JOBS]

    def tearDown(self):
        km._pending_ops.clear()
        km._moving.clear()
        km._drain_hold.clear()
        producer = getattr(self, "producer", None)
        if producer is None or not producer.is_alive():
            km._LOOPS_STOP.clear()       # a producer still alive keeps the stop set until its cleanup (_end_producer) joins it

    def _census_check(self):
        self.assertEqual(wait_for_census(self._census0, timeout=self._CENSUS_WAIT_S), [],
                         "no thread of this test outlives it (T282)")

    @staticmethod
    def _pass_stubs():
        """What a pass touches besides its tiers and the drain, quieted: no goal-store compaction, no SdkBackend build
        (_sdk), no goals snapshot, no evidence frame, no recovery re-arm. These outlive the producer's end, so the pass
        that completes once the gate opens completes under them and never runs the real functions."""
        return [
            mock.patch.object(km, "_retry_paused_on", lambda: False),
            mock.patch.object(km, "_episode_boundary_tick", lambda now: None),
            mock.patch.object(km, "_begin_goals_pass", lambda: None),
            mock.patch.object(km, "_end_goals_pass", lambda: None),
            mock.patch.object(km, "_compact_goal_stores", lambda: 0),
            mock.patch.object(km, "_sdk", lambda: None),
            mock.patch.object(km.jd, "begin_pass_frame", lambda: False),
            mock.patch.object(km.jd, "end_pass_frame", lambda f: None),
            mock.patch.object(km.jd, "consume_judge_recovery", lambda: False),
        ]

    @classmethod
    def _pass_patches(cls, gate, apply):
        """The eleven patches a stuck pass runs under: the tiers block on `gate` (judge.run_pass resolves _run_tier at call
        time, so the stub is the tier threads' target), the drain is `apply`, and the pass's other work is stubbed."""
        return [mock.patch.object(km.jd, "_run_tier", lambda fn, name, acc, before=None: gate.wait()),
                mock.patch.object(km, "_apply_pending_ops", apply)] + cls._pass_stubs()

    def _end_producer(self):
        """End the producer under test: the stop seam FIRST, the gate SECOND (the stuck tiers return, the pass completes
        under its stubs, the loop ends at its next turn of the wheel), the wake, then a bounded join; the flag is cleared
        once the producer is dead. Guarded for a producer never started (its ident is None: the body failed between the
        cleanup's registration and the start). Idempotent: the body's tail calls it and the cleanup calls it again."""
        producer = getattr(self, "producer", None)
        km._LOOPS_STOP.set()
        self.gate.set()
        km._producer_wake.set()
        if producer is not None and producer.ident is not None:
            producer.join(10)
        if producer is None or not producer.is_alive():
            km._LOOPS_STOP.clear()

    def _pass_in_flight(self, ran_on):
        """Start the producer against tiers stuck on self.gate and return once its pass is in flight, with `ran_on`
        recording the thread each drain ran on. Everything a failed assertion must not skip is a CLEANUP registered
        before the start; they run LIFO: the producer's end first, then the pass's stubs come off, then setUp's census."""
        self.gate = threading.Event()        # the judge tiers block here: a closer sweep that never returns
        real_apply = km._apply_pending_ops

        def counting_apply():
            ran_on.append(threading.current_thread().name)
            return real_apply()

        for p in self._pass_patches(self.gate, counting_apply):
            p.start()
            self.addCleanup(p.stop)
        self.producer = threading.Thread(target=km._producer, name="producer-under-test", daemon=True)
        self.addCleanup(self._end_producer)  # registered BEFORE the start: it runs wherever the body fails (T282)
        self.producer.start()
        deadline = time.time() + 5
        while time.time() < deadline and not any(t.name == "triage" for t in threading.enumerate()):
            time.sleep(0.01)
        self.assertTrue(any(t.name == "triage" for t in threading.enumerate()),
                        "a judge pass is in flight, stuck on its tiers")
        return self.producer

    def test_parked_op_delivers_on_settle_while_a_judge_pass_is_stuck(self):
        ran_on = []                          # the threads that ran the drain
        producer = self._pass_in_flight(ran_on)
        # a typed slash command lands while the turn is open → parked (the standing rule)
        km._send_or_park(self.be, SID, "/frobnicate now")
        self.assertEqual(km._pending_ops[SID], [("command", "/frobnicate now", None)])
        self.assertEqual(self.be.calls, [])
        # the turn SETTLES: the backend pokes the kernel exactly as its ResultMessage path does. (On a
        # tree without _wake_kernel the poke is what the backends did before — both wakes by hand — so
        # this test reaches the delivery assertion there and fails on the bug, not on a missing name.)
        self.be.open = False
        km._pusher_wake.clear()
        poke = getattr(km, "_wake_kernel", None) or (lambda: (km._producer_wake.set(), km._pusher_wake.set()))
        poke()
        self.assertTrue(km._pusher_wake.is_set(), "the settle wakes the thread that delivers")
        self.assertTrue(km._producer_wake.is_set(), "…and the judges, as before")
        km._pusher_cycle()                           # ONE pusher cycle, while the judge pass is still stuck
        self.assertFalse(self.gate.is_set())
        self.assertTrue(producer.is_alive())
        self.assertEqual(self.be.calls, [("send", "/frobnicate now")], "delivered alone, as a fresh prompt")
        self.assertNotIn(SID, km._pending_ops)
        self.assertEqual(ran_on, [threading.current_thread().name],
                         "the drain ran on this cycle and never on the producer")
        self._end_producer()                         # the same end the cleanup holds; here it is also what is asserted
        self.assertFalse(producer.is_alive(), "the producer ended on the stop seam once its pass finished")

    def test_a_set_up_that_raises_after_the_third_patcher_leaves_no_patcher_installed(self):
        """The patchers' restore, run rather than read (2026-09-22). Each patcher's stop is a cleanup registered as it
        starts, and unittest runs the cleanups when setUp raises (it skips tearDown then), so a failure inside the loop
        unwinds exactly the patchers that started. A nested case with this class's setUp whose FOURTH patcher raises on
        start is run here, under this test's own patches: its run records the planted error alone, and every attribute
        setUp patches reads the same object before and after the run (the first three restored, the rest never
        installed). Before this the stops lived in tearDown and that road left all of them installed for the rest of the
        worker."""
        names = ("_compacting_now", "_mark_compacting", "_names_snapshot", "_live_map", "_wait_boot_attached") + _OTHER_JOBS
        before = {n: getattr(km, n) for n in names}
        before["Sessions.backend_for"] = getattr(km.Sessions, "backend_for")
        started = []

        class _Raiser:
            def start(self):
                raise RuntimeError("planted: the fourth patcher fails to start")

            def stop(self):
                started.append("stopped a patcher that never started")

        class _SetUpRaises(DeliveryRidesTheSettle):
            def _patchers(self):
                ps = super()._patchers()
                ps.insert(3, _Raiser())
                return ps

            def test_body(self):
                self.fail("never reached: setUp raised")

        res = unittest.TestResult()
        _SetUpRaises("test_body").run(res)
        self.assertEqual(len(res.errors), 1, "the planted error and nothing beside it: %r" % (res.errors,))
        self.assertIn("planted: the fourth patcher", res.errors[0][1])
        self.assertEqual(res.failures, [])
        self.assertEqual(started, [], "a stop is registered only for a patcher that started")
        after = {n: getattr(km, n) for n in names}
        after["Sessions.backend_for"] = getattr(km.Sessions, "backend_for")
        self.assertEqual(after, before, "every attribute setUp patches reads as it did before the nested run")

    def test_a_body_that_fails_before_its_tail_leaves_no_producer_behind(self):
        """Both stop shapes, run rather than read. A nested case with this class's shape starts the producer the same way
        and fails right after the pass is in flight: the cleanup registered before the start ends the producer, the T282
        census in the nested case's own cleanup reads clean (one failure, the planted one, and nothing beside it), and no
        producer or tier thread is alive afterwards. A second nested case has the pre-fix shape, the stop only on the
        body's tail: the same failure leaves the producer and its two tier threads wedged on the gate, the census names
        them (the teardown ERROR beside the FAILED wherever the condition in the module docstring fired: the test alone
        serially every time, a full sweep only when no earlier test in the target's worker had latched _BOOT_ATTACHED;
        the free-running case is in the red-before log, the single test alone serially), and this test ends them by a
        cleanup registered before the nested case runs. Both nested cases run under the pass's stubs held by this test,
        so the pass that completes when the gate opens never runs the real _compact_goal_stores or _sdk() inside this
        suite."""
        for p in self._pass_stubs():
            p.start()
            self.addCleanup(p.stop)
        census0 = thread_census()            # leftovers() below is a census DIFFERENCE against this, as wait_for_census reads one
        tail = None                          # the pre-fix case, bound below once its class exists; end_tail_producer reads it late

        def end_tail_producer():
            """End what the pre-fix shape leaves behind: the stop seam first, the gate second (the stuck tiers return and
            the pass completes under this test's stubs), the wake, a bounded join, the flag cleared once the producer is
            dead. Guarded for a producer never started (the body failed before the pre-fix case ran, or its start never
            came). Idempotent: this body's tail calls it, and the cleanup calls it again."""
            producer = getattr(tail, "producer", None)
            km._LOOPS_STOP.set()
            if getattr(tail, "gate", None) is not None:
                tail.gate.set()
            km._producer_wake.set()
            if producer is not None and producer.ident is not None:
                producer.join(10)
            if producer is None or not producer.is_alive():
                km._LOOPS_STOP.clear()

        # Registered BEFORE the pre-fix case runs (tail.run below), the shape this module requires of every start: an
        # assertion that fails between cannot leak the producer the pre-fix case leaves (planted, verified: a self.fail
        # after tail.run(res) with the end only on this body's tail left the producer and its tiers behind).
        self.addCleanup(end_tail_producer)

        class _Fixed(DeliveryRidesTheSettle):
            def test_fails(self):
                self._pass_in_flight([])
                self.fail("planted: the body fails before its tail")

        class _TailOnly(DeliveryRidesTheSettle):
            _CENSUS_WAIT_S = 0.5             # the leftovers are wedged and will not go away: the census need not wait long

            def test_fails(self):
                self.gate = gate = threading.Event()
                with contextlib.ExitStack() as patches:            # the pre-fix shape: the stubs on a with, the stop on the tail
                    for p in self._pass_patches(gate, km._apply_pending_ops):
                        patches.enter_context(p)
                    self.producer = threading.Thread(target=km._producer, name="producer-under-test", daemon=True)
                    self.producer.start()
                    deadline = time.time() + 5
                    while time.time() < deadline and not any(t.name == "triage" for t in threading.enumerate()):
                        time.sleep(0.01)
                    self.assertTrue(any(t.name == "triage" for t in threading.enumerate()))
                    self.fail("planted: the body fails before its tail")
                    km._LOOPS_STOP.set(); gate.set(); km._producer_wake.set(); self.producer.join(5)   # never reached

        def leftovers(timeout=0.0):
            """The threads alive now that were not at this test's start, by count: the Counter difference
            tests/conftest.py's wait_for_census reads (polled up to `timeout` for a thread still reaching its exit), as
            descriptors (the target's module.qualname), never absolute thread names."""
            return wait_for_census(census0, timeout=timeout)

        fixed, res = _Fixed("test_fails"), unittest.TestResult()
        fixed.run(res)
        self.assertEqual(len(res.failures), 1, "the planted failure and nothing beside it: %r" % (res.failures,))
        self.assertIn("planted", res.failures[0][1])
        self.assertEqual(res.errors, [], res.errors)
        self.assertFalse(fixed.producer.is_alive(), "the cleanup registered before the start ended the producer")
        self.assertEqual(leftovers(timeout=5.0), [], "no producer or tier thread outlives the failed body")
        self.assertFalse(km._LOOPS_STOP.is_set(), "the flag is cleared once the producer is dead")

        tail, res = _TailOnly("test_fails"), unittest.TestResult()
        tail.run(res)
        texts = [tb for _case, tb in res.failures + res.errors]
        self.assertEqual(len(texts), 2, "the planted failure AND the census naming the leak: %r" % (texts,))
        self.assertTrue(any("planted" in t for t in texts), texts)
        self.assertTrue(any("T282" in t and "romp_kernel_parkedlive._producer" in t for t in texts),
                        "the pre-fix shape leaks: the census names the producer and cannot stop it: %r" % (texts,))
        self.assertTrue(tail.producer.is_alive(), "wedged on the gate, alive after its test ended")
        left = leftovers()
        self.assertIn("romp_kernel_parkedlive._producer", left, left)
        self.assertEqual(len(left), 3, "the producer and its two tier threads, wedged on the gate: %r" % (left,))
        end_tail_producer()                  # the same end the cleanup holds; here it is also what is asserted
        self.assertFalse(tail.producer.is_alive(), "the stop seam, the gate and a bounded join ended what the pre-fix shape left")
        self.assertEqual(leftovers(timeout=5.0), [], "the tiers returned with the gate and the pass completed under the stubs")
        self.assertFalse(km._LOOPS_STOP.is_set(), "the flag is cleared once the producer is dead")

    def test_two_parks_drain_one_per_settle_in_park_order(self):
        self.assertTrue(km._send_or_park(self.be, SID, "one", echo="human"))   # cannot forward: a send parks mid-turn
        self.assertTrue(km._compact_or_park(self.be, SID), "the compact parks behind it (queued)")
        self.assertEqual([op[0] for op in km._pending_ops[SID]], ["send", "compact"])
        self.be.open = False                                                    # settle #1
        km._pusher_cycle()
        self.assertEqual(self.be.calls, [("send", "one")], "the send fired; the compact waits for ITS turn to end")
        self.assertEqual([op[0] for op in km._pending_ops[SID]], ["compact"])
        self.assertNotIn(SID, km._drain_hold, "send() closed the busy gate before it returned: nothing to hold for")
        self.assertTrue(self.be.open, "the delivered send's turn is in flight")
        km._pusher_cycle()
        self.assertEqual(self.be.calls, [("send", "one")], "nothing fires into an open turn")
        self.be.open = False                                                    # settle #2
        km._pusher_cycle()
        self.assertEqual(self.be.calls, [("send", "one"), ("send", "/compact")])
        self.assertNotIn(SID, km._pending_ops)
        self.assertNotIn(SID, km._drain_hold, "an authoritative busy() needs no hold between deliveries")

    def test_a_backend_that_cannot_say_busy_still_holds_for_the_fallback_window(self):
        # a backend with NO busy() at all (a test fake, a future backend): nothing can ever observe its gate
        # close, so the prompt hold arms and only its clock fallback (_PROMPT_HOLD_S) releases it —
        # the op behind never fires back-to-back into a turn that may be opening
        class _Mute(_FakeBackend):
            def busy(self, sid):
                return None
        self.be = _Mute()
        with mock.patch.object(km, "_working_now", lambda sid: True):             # the turn is open: both park
            km._send_or_park(self.be, SID, "one", echo="human")
            km._compact_or_park(self.be, SID)
        self.assertEqual([op[0] for op in km._pending_ops[SID]], ["send", "compact"])
        with mock.patch.object(km, "_PROMPT_HOLD_S", 3600.0):
            km._pusher_cycle()                                                    # the cached parse reads idle
            self.assertEqual(self.be.calls, [("send", "one")], "the send fired")
            self.assertIn(SID, km._drain_hold, "…and the sid is held while its prompt lands")
            km._pusher_cycle()                                                    # back-to-back, as a wake would
            self.assertEqual(self.be.calls, [("send", "one")], "the compact does NOT fire into the opening turn")
        far = time.monotonic() + 7200.0                                           # the fallback window passed
        with mock.patch.object(km.time, "monotonic", lambda: far), redirect_stderr(io.StringIO()):
            km._pusher_cycle()
        self.assertEqual(self.be.calls, [("send", "one"), ("send", "/compact")])

    def test_a_dead_sessions_queue_drop_takes_its_hold_with_it(self):
        # the hold check precedes delivery, so a hold present when send() raises can only have been armed
        # DURING the delivery (a concurrent writer — the move thread's re-park); the drop must not leave it behind
        class _Dead(_FakeBackend):
            def send(self, sid, text):
                km._hold_drain(sid, 60.0)
                raise RuntimeError("the session is gone")
        self.be = _Dead()
        self.be.open = False
        km._pending_ops[SID] = [("send", "one", "human")]
        with redirect_stderr(io.StringIO()):
            km._apply_pending_ops()
        self.assertNotIn(SID, km._pending_ops, "a dead session's queue is dropped")
        self.assertNotIn(SID, km._drain_hold, "…and its hold with it")

    def test_wake_kernel_sets_both_events_and_is_the_backends_poke(self):
        km._producer_wake.clear()
        km._pusher_wake.clear()
        km._wake_kernel()
        self.assertTrue(km._producer_wake.is_set() and km._pusher_wake.is_set())
        src = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
        self.assertEqual(src.count("poke=_wake_kernel"), 2, "both backend constructors (SDK + Codex) poke the kernel")
        self.assertNotIn("poke=_producer_wake.set", src, "no backend pokes only the judges anymore")

    def test_delivery_moved_from_the_producer_to_the_pusher_cycle(self):
        self.assertNotIn("_apply_pending_ops()", inspect.getsource(km._producer), "the judge pass no longer gates delivery")
        src = inspect.getsource(km._pusher_cycle_jobs)
        self.assertIn("_apply_pending_ops()", src, "the pusher cycle delivers the parked queue")
        self.assertLess(src.index("_apply_pending_ops()"), src.index("_push_all("),
                        "delivery precedes the push, so the delivered op's echo and retired chip ride it")

    def test_drain_does_not_wake_the_pusher_when_nothing_changed(self):
        self.be.open = False
        d = tempfile.mkdtemp()
        km._pending_ops[SID] = [("cwd", d, km._MOVE_BUSY_RETRIES, 0)]    # waits on turn_seq: nothing to do yet
        km._pusher_wake.clear()
        km._apply_pending_ops()
        self.assertEqual(km._pending_ops[SID], [("cwd", d, km._MOVE_BUSY_RETRIES, 0)], "still parked")
        self.assertFalse(km._pusher_wake.is_set(),
                         "a cycle that delivered nothing must not re-wake the thread it runs on (a hot loop)")
        km._pending_ops[SID] = [("model", "opus")]
        km._apply_pending_ops()
        self.assertEqual(self.be.calls, [("model", "opus")])
        self.assertTrue(km._pusher_wake.is_set(), "a real delivery wakes the push that retires the chip")

    def test_a_cycle_resolves_a_held_sids_path_once(self):
        # review find on #904: the drain's gates each resolved a held sid's transcript path (a discover
        # fingerprint) every cycle; inside a cycle the resolution is memoized on the cycle's scope, and a
        # caller outside a cycle (a WS handler) still resolves fresh
        calls = []
        with mock.patch.object(km, "_sessions", lambda now: (calls.append(1), [])[1]):
            km._path_of(SID)
            km._path_of(SID)
            self.assertEqual(len(calls), 2, "outside a cycle every ask resolves fresh")
            calls.clear()
            km._live_scope.paths = {}
            try:
                km._path_of(SID)
                km._path_of(SID)
            finally:
                km._live_scope.paths = None
            self.assertEqual(len(calls), 1, "inside a cycle the second ask is the memo")
        km._pusher_cycle()
        self.assertIsNone(getattr(km._live_scope, "paths", None), "the memo ends with the cycle")

    def test_cancel_parked_logs_sid_and_kind_only(self):
        km._pending_ops[SID] = [("send", "a private sentence", "human")]
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertIsNone(km._cancel_parked(SID, 0, ""))
        line = buf.getvalue()
        self.assertIn(SID, line)
        self.assertIn("send", line)
        self.assertNotIn("a private sentence", line, "the body is user text — never logged")
        self.assertNotIn(SID, km._pending_ops)


if __name__ == "__main__":
    unittest.main()
