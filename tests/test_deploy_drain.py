#!/usr/bin/env python3
"""The deploy-drain hold (T121 part 1, 2026-08-27): while a quiet deploy restart is PARKED at the
manager, the kernel holds NEW turn starts so /busy falls to 0 on its own turn-end events — before
this, kernels kept starting queued turns and a busy box only ever "drained" via the manager's
backstop cut. The hold is a LEASE (refreshed by the parked poll, self-expiring when the holder
dies) and RUNTIME-ONLY (a fresh boot starts clear by construction — the manager-approved
stale-flag guard); arming is visible once per episode and a long hold escalates to the problems
ring. Mid-turn forwards keep flowing so the in-flight turn can finish; queued prompts persist —
that IS the checkpoint. Hermetic state; synthetic sids only."""
import os
import tempfile
import time
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
sb = load_source("romp_sdk_backend_drainhold", os.path.join(BIN, "romp_sdk_backend.py"))


def _backend(d=None):
    return sb.SdkBackend(d or tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)


class DrainLease(unittest.TestCase):
    def test_a_fresh_backend_never_holds(self):
        # boot-clear BY CONSTRUCTION: the lease is runtime-only, so the restart it served can never
        # leave a standing flag behind — the manager-approved stale-drain guard
        self.assertFalse(_backend().drain_holding())

    def test_refresh_arms_and_expiry_releases(self):
        be = _backend()
        be.DRAIN_HOLD_TTL = 0.15
        be.refresh_drain_hold()
        self.assertTrue(be.drain_holding(), "the parked poll's refresh arms the hold")
        time.sleep(0.25)
        self.assertFalse(be.drain_holding(),
                         "the lease dies by itself when the holder stops refreshing — no off-switch to forget")

    def test_expiry_wakes_held_inputs(self):
        be = _backend()
        be.DRAIN_HOLD_TTL = 0.1
        woken = []
        be._wake_all_inputs = lambda: woken.append(1)
        be.refresh_drain_hold()
        time.sleep(0.9)   # the wake timer fires at TTL + 0.5s
        self.assertTrue(woken, "the lease-end timer nudges every input generator — a held fresh "
                               "turn starts without waiting for another event")

    def test_arming_is_visible_and_a_long_hold_rings(self):
        logs = []
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=logs.append)
        be.refresh_drain_hold()
        self.assertTrue(any("deploy restart parked" in str(l) for l in logs),
                        "arming says so once — a draining box never reads as a hung one")
        be._drain_hold_since = time.time() - be.DRAIN_LOUD_S - 1
        be.refresh_drain_hold()
        self.assertTrue(any("still parked" in str(l) for l in logs),
                        "a hold outliving the loud bound escalates rather than reading as idle sessions")

    def test_the_turn_start_gate_holds_fresh_starts_only(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")).read()
        self.assertIn("blocked = blocked or (self.inflight == 0 and self.backend.drain_holding())", src,
                      "the inputs() gate holds NEW turn starts while draining; mid-turn forwards "
                      "(inflight > 0) keep flowing so the in-flight turn can finish")

    def test_the_kernel_route_and_the_deploy_paths_ride_the_gate(self):
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        # T224 split the gate into branches so a REFUSED drain can be counted and said loudly; the
        # arm still sits under the explicit-token check and nowhere else
        self.assertIn('if q.get("drain", [""])[0] == "1":\n                        if self._write_token_ok(q):\n'
                      '                            be.refresh_drain_hold()', ksrc,
                      "/busy?drain=1 refreshes the lease in the same round-trip that reads the count — "
                      "but the arm is a WRITE, gated on an explicit token (the behavioral pins live "
                      "in tests/test_kernel_auth_hardening.py::BusyDrainWriteGate); the READ stays exempt")
        self.assertIn('json.dumps({"busy": n, "draining": draining})', ksrc,
                      "the payload says when the box is draining — glanceable, never mysterious")
        self.assertIn("'http://127.0.0.1:%d/restart-all'", ksrc,
                      "the self-update deploy cuts IMMEDIATELY (T160, reversing the T121 quiet "
                      "default: parked windows cost minutes per push) — the quiet gate stays for "
                      "explicit `romp refresh --quiet`")
        self.assertNotIn("/restart-all?when=quiet'", ksrc,
                         "no kernel-side deploy path defaults to the quiet window any more")
        msrc = open(os.path.join(BIN, "romp-manager")).read()
        self.assertIn("fetchBusy(KERNEL_PORT, cb, '/busy?drain=1')", msrc,
                      "the manager's PARKED poll is the lease's refresher")


class GoingDownHold(unittest.TestCase):
    """`romp down`'s quiesce (2026-09-06) rides the same lease: quiesce(ttl) extends the hold to cover
    the wait plus the stop that follows and flags the create doors closed (quiescing); a deploy poll
    landing inside it must never SHORTEN it; the cancel releases and wakes; and it stays a lease —
    no stop, and the kernel carries on by itself."""

    def test_a_fresh_backend_is_not_quiescing(self):
        self.assertFalse(_backend().quiescing())
        self.assertEqual(_backend().inflight_names(), [])

    def test_quiesce_arms_both_the_turn_hold_and_the_create_gate_for_the_ttl(self):
        be = _backend()
        be.quiesce(0.3)
        self.assertTrue(be.drain_holding(), "new turn starts hold — the same gate inputs() consults")
        self.assertTrue(be.quiescing(), "…and the create doors read closed")
        time.sleep(0.45)
        self.assertFalse(be.quiescing(), "a lease, not a latch: with no stop the kernel carries on")
        self.assertFalse(be.drain_holding())

    def test_a_deploy_poll_inside_a_quiesce_never_shortens_the_hold(self):
        be = _backend()
        be.DRAIN_HOLD_TTL = 0.1
        be.quiesce(5)
        be.refresh_drain_hold()
        self.assertGreater(be._drain_hold_until, time.time() + 4,
                           "the 12s lease refresh extends a hold, it never cuts a longer one back")

    def test_a_deploy_poll_inside_a_quiesce_does_not_ring_a_stale_clock(self):
        # refresh_drain_hold's "still parked" escalation clocks from _drain_hold_since; a quiesce that
        # opened the episode must start that clock, or the first deploy poll inside it reads a 0.0
        # stamp as a hold minutes old and rings the problems ring for nothing
        logs = []
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=logs.append)
        be.quiesce(5)
        be.refresh_drain_hold()
        self.assertFalse(any("still parked" in str(l) for l in logs), logs)

    def test_cancel_releases_at_once_and_wakes_the_held_inputs(self):
        be = _backend()
        woken = []
        be._wake_all_inputs = lambda: woken.append(1)
        be.quiesce(30)
        be.cancel_quiesce()
        self.assertFalse(be.quiescing())
        self.assertFalse(be.drain_holding())
        self.assertTrue(woken, "held fresh turns start now, not at the lapsed lease's timer")

    def test_arming_and_canceling_are_visible(self):
        logs = []
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=logs.append)
        be.quiesce(3)
        self.assertTrue(any("going down" in str(l) for l in logs), logs)
        be.cancel_quiesce()
        self.assertTrue(any("canceled" in str(l) for l in logs), logs)
        n = len(logs)
        be.cancel_quiesce()
        self.assertEqual(len(logs), n, "a cancel with nothing to cancel says nothing")

    def test_the_kernel_doors_ride_the_gate(self):
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn('if u.path == "/down":', ksrc)
        import re
        self.assertEqual(len(re.findall(r"^\s*if _going_down\(\):", ksrc, re.M)), 1,
                         "POST /new refuses on the shared helper")
        self.assertEqual(len(re.findall(r"^\s*elif _going_down\(\):", ksrc, re.M)), 1,
                         "so does the WS createSession op")


if __name__ == "__main__":
    unittest.main()
