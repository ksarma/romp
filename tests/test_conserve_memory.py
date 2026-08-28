#!/usr/bin/env python3
"""Conserve-memory (T148, user-directed): a session with an OPEN TAB keeps its claude process for
as long as the tab is open — the de-facto behavior, now stated — and the CONSERVE option (default
OFF) closes the process of a session that is IDLE and tab-open on NO connected viewer. Closes are
CLEAN: the reg stays alive, queue/transcript persist, and the ordinary on-demand _ensure (a tab
click, a send, a scheduled wake — PR 769's lane) revives. Event-first keying with two bounded
windows: the 30s viewer-disconnect lease (a reload never mass-closes) and the 60s hide-grace (a
lens flick never churns). Hermetic state; synthetic sids."""
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel_conserve", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_conserve", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-00000000e148"


class Flag(unittest.TestCase):
    def test_default_off_round_trip_and_junk(self):
        try:
            (jd.STATE / km.CONSERVE_FILE_NAME).unlink()
        except OSError:
            pass
        self.assertFalse(km._conserve_on(), "keep-alive is the default — conserve is the OPTION")
        km._set_conserve(True)
        self.assertTrue(km._conserve_on())
        km._set_conserve(False)
        self.assertFalse(km._conserve_on())
        (jd.STATE / km.CONSERVE_FILE_NAME).write_text("junk")
        self.assertFalse(km._conserve_on(), "junk reads as off, never raises")
        (jd.STATE / km.CONSERVE_FILE_NAME).unlink()

    def test_op_and_payload_wiring(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn('msg.get("type") == "setConserve"', src, "the gear's toggle rides the kernel channel")
        self.assertIn('"conserveMemory": _conserve_on(),', src, "…and /version reflects the kernel truth")
        self.assertIn("_conserve_tick(now)", src, "the sweep rides the supervisor pass")
        gear = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "gear.js")).read()
        self.assertIn("setConserve", gear)
        self.assertIn("v.conserveMemory", gear)


class BackendClose(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sb.write_reg(Path(self.d), SID, {"sid": SID, "name": "bg", "cwd": "/tmp", "alive": True})
        self.s = sb.SdkSession(self.be, sb.read_reg(Path(self.d), SID))
        self.s.thread = threading.Thread(target=lambda: time.sleep(0.3), daemon=True)
        self.s.thread.start()
        self.be.sessions[SID] = self.s

    def test_close_is_clean_and_revivable(self):
        self.assertIn(SID, self.be.running_sids())
        self.assertTrue(self.be.conserve_idle(SID))
        self.assertTrue(self.be.conserve_close(SID))
        self.assertNotIn(SID, self.be.running_sids())
        reg = sb.read_reg(Path(self.d), SID)
        self.assertTrue(reg.get("alive"), "the reg stays ALIVE — dormant, not killed; _ensure revives on demand")

    def test_never_closes_a_timer_armed_session(self):
        # the T148/769 seam, executed: ensure_scheduled revives any timer-armed threadless session
        # every producer pass — if conserve closed one, the pair would loop close/revive forever
        # (one respawn per sweep, the exact churn the user feared). The reg's sessionCrons is the
        # SAME record ensure_scheduled reads, so conserve refusing on it can never drift from 769.
        reg = sb.read_reg(Path(self.d), SID)
        reg["sessionCrons"] = {"gen": 1, "crons": [{"id": "c1", "schedule": "0 * * * *"}]}
        sb.write_reg(Path(self.d), SID, reg)
        self.assertFalse(self.be.conserve_idle(SID), "armed timers pin the process — its CLI is the scheduler")
        self.assertFalse(self.be.conserve_close(SID))
        reg.pop("sessionCrons")
        sb.write_reg(Path(self.d), SID, reg)
        self.assertTrue(self.be.conserve_idle(SID), "…and disarming the timers frees it")

    def test_never_closes_work(self):
        self.s.inflight = 1
        self.assertFalse(self.be.conserve_idle(SID))
        self.assertFalse(self.be.conserve_close(SID), "an in-flight turn stands the close down")
        self.s.inflight = 0
        self.s._pending.append("queued prompt")
        self.assertFalse(self.be.conserve_close(SID), "a queued prompt stands it down too")


class Tick(unittest.TestCase):
    """The sweep's decision matrix, executed with a stubbed backend + client roster."""

    class _FakeBe:
        def __init__(self):
            self.running = ["s-open", "s-hidden", "s-busy", "s-fresh"]
            self.idle = {"s-open": True, "s-hidden": True, "s-busy": False, "s-fresh": True}
            # the FADED fact rides the snapshot rows (T155): everyone idled since t=0 except
            # s-fresh, which settled moments ago — inside the hour, never closed
            self.since = {"s-open": "1", "s-hidden": "1", "s-busy": "1", "s-fresh": "999"}
            self.closed = []
        def running_sids(self): return list(self.running)
        def live_sessions(self):
            return {sid: {"state": "waiting", "since": self.since.get(sid, "1")} for sid in self.running}
        def conserve_idle(self, sid): return self.idle.get(sid, False)
        def conserve_close(self, sid):
            self.closed.append(sid); self.running.remove(sid); return True

    def setUp(self):
        km._set_conserve(True)
        self.be = self._FakeBe()
        self._saved = (km._sdk, km._views_client, km._view_visible)
        km._sdk = lambda: self.be
        km._views_client = lambda: {"active": "all", "tags": [], "actives": {}}
        km._view_visible = lambda vc, sid, surface=None: sid == "s-open"   # only s-open is on the strip
        km._conserve_hidden_at.clear()
        with km._clients_lock:
            self._clients_before = list(km._clients)
            km._clients[:] = [{"app": "chat", "wid": "w1", "send": lambda m: None, "alive": True}]
        km._conserve_last_viewer[0] = 0.0

    def tearDown(self):
        km._sdk, km._views_client, km._view_visible = self._saved
        with km._clients_lock:
            km._clients[:] = self._clients_before
        km._set_conserve(False)
        km._conserve_hidden_at.clear()

    def test_matrix_open_stays_hidden_faded_closes_after_grace_busy_and_fresh_stay(self):
        # ticks run past the FADED hour (sessions idled since t~0) — s-fresh alone is inside it
        t0 = 5000.0
        self.be.since["s-fresh"] = str(t0 - 60)   # settled a minute before the tick — inside the hour
        km._conserve_tick(t0)
        self.assertEqual(self.be.closed, [], "first sight of hidden+faded starts the grace, closes nothing")
        km._conserve_tick(t0 + km.CONSERVE_HIDE_GRACE_S + 1)
        self.assertEqual(self.be.closed, ["s-hidden"],
                         "hidden+faded closes after the grace; the open tab, the busy one, and the "
                         "fresh-idle one all stay (T155: the hour IS the churn hysteresis)")

    def test_a_fresh_idle_session_never_closes_inside_the_hour(self):
        self.be.since["s-hidden"] = "999999"                   # settled moments before the tick
        self.be.since["s-fresh"] = "999999"
        km._conserve_tick(1000000.0)
        km._conserve_tick(1000000.0 + km.CONSERVE_HIDE_GRACE_S + 1)
        self.assertEqual(self.be.closed, [], "inside the faded hour nothing closes — no churn, ever")
        self.be.since["s-hidden"] = "1"                        # …and once faded, it goes
        km._conserve_tick(1000000.0 + 2 * km.CONSERVE_HIDE_GRACE_S + 2)
        km._conserve_tick(1000000.0 + 3 * km.CONSERVE_HIDE_GRACE_S + 3)
        self.assertEqual(self.be.closed, ["s-hidden"])

    def test_a_reshow_cancels_the_grace(self):
        km._conserve_tick(1000.0)
        km._view_visible = lambda vc, sid, surface=None: sid in ("s-open", "s-hidden")   # re-shown — the EVENT
        km._conserve_tick(1000.0 + km.CONSERVE_HIDE_GRACE_S + 1)
        self.assertEqual(self.be.closed, [], "the re-show event cancels the pending close")

    def test_viewer_disconnect_lease_holds_then_releases(self):
        # tick times sit past the faded hour for the since="1" rows; s-fresh settled a minute before
        t0 = 10000.0
        self.be.since["s-fresh"] = str(t0 - 60)
        with km._clients_lock:
            km._clients[:] = []                                  # every viewer gone (a reload)
        km._conserve_last_viewer[0] = t0
        km._conserve_tick(t0 + 5)
        self.assertEqual(self.be.closed, [], "within the lease nothing moves — a reload never mass-closes")
        km._conserve_tick(t0 + km.CONSERVE_VIEWER_LEASE_S + 1)
        km._conserve_tick(t0 + km.CONSERVE_VIEWER_LEASE_S + km.CONSERVE_HIDE_GRACE_S + 2)
        self.assertIn("s-hidden", self.be.closed, "past the lease, no viewer = no open tabs; faded closes after grace")
        self.assertIn("s-open", self.be.closed, "…including the one that WAS on the strip (no viewer sees it)")
        self.assertNotIn("s-busy", self.be.closed, "work is never closed")
        self.assertNotIn("s-fresh", self.be.closed, "…and fresh-idle stays even with no viewer (the hour holds)")

    def test_off_means_untouched(self):
        km._set_conserve(False)
        km._conserve_tick(1000.0)
        km._conserve_tick(9999.0)
        self.assertEqual(self.be.closed, [], "conserve OFF = today's behavior exactly: nothing closes, ever")


if __name__ == "__main__":
    unittest.main()
