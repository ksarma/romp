#!/usr/bin/env python3
"""Sessions with armed timers keep a live CLI process (the user 2026-08-28: CronCreate crons and
ScheduleWakeup wakeups never fired on sessions romp had left dormant — a wakeup armed for 26 minutes
out missed across 21 hours, and agents built host-crontab workarounds).

The mechanism, established by binary recon + live probes (2026-08-28): session-scoped timers (default
CronCreate, ALL ScheduleWakeups, /loop ticks) live only in the CLI process's memory; the CLI's own
scheduler fires them fine on a live IDLE process (jitter up to half the interval on recurring crons),
and a resumed process re-hydrates its timer set — but a DORMANT session has no process at the due
moment, and session-scoped timers have no CLI-side catch-up. Romp's job is therefore exactly one
thing: never leave a timer-armed session without a process. Three pieces, pinned here:

1. The Stop hook persists the payload's `session_crons` (the armed set, handed to romp at every turn
   end) into the session reg — including [] when the last timer is cancelled.
2. SdkBackend.ensure_scheduled() reconnects any alive, timer-armed session with no running thread —
   idempotent, with a 120s per-sid retry floor so a spawn-crashing session can't become a storm.
3. The kernel's producer calls the sweep every pass.

Romp never fires a timer itself (no double-fire risk). Synthetic fixtures only."""
import asyncio
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = SourceFileLoader("romp_sdk_backend_sched", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-000000000021"


class _Backend(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)

    def _reg(self, sid=SID, **kw):
        sb.write_reg(self.d, sid, {"sid": sid, "name": "timers", "cwd": "/tmp", "alive": True, **kw})
        return sb.read_reg(self.d, sid)


class StopHookRecordsTheArmedSet(_Backend):
    CRONS = [{"id": "aaaa1111", "schedule": "50 * * * *", "prompt": "Reply with exactly: tick",
              "kind": "cron", "recurring": True}]

    def _sess(self):
        self._reg()
        return sb.SdkSession(self.be, sb.read_reg(self.d, SID))

    def test_session_crons_land_in_the_reg(self):
        s = self._sess()
        asyncio.run(s._stop_hook({"session_crons": self.CRONS}, None, None))
        rec = (sb.read_reg(self.d, SID) or {}).get("sessionCrons")
        self.assertEqual(len(rec), 1)
        armed = rec[0].pop("armedAt")
        self.assertAlmostEqual(armed, time.time(), delta=30, msg="first-seen arm time rides the entry")
        self.assertEqual(rec, [{"id": "aaaa1111", "cron": "50 * * * *",
                                "prompt": "Reply with exactly: tick", "kind": "cron", "recurring": True}])

    def test_a_lost_future_one_shot_survives_the_rewrite(self):
        # a recycled process's payload lacks the wakeup it lost; the record must outlive the rewrite
        # while its due is still ahead — deliver_lost_wakeups needs it at due time
        s = self._sess()
        due = time.localtime(time.time() + 600)
        shot = {"id": "dddd4444", "schedule": "%d %d * * *" % (due[4], due[3]),
                "prompt": "Reply with exactly: wake", "kind": "loop", "recurring": False}
        asyncio.run(s._stop_hook({"session_crons": [shot]}, None, None))
        asyncio.run(s._stop_hook({"session_crons": []}, None, None))   # the fresh process knows nothing
        rec = (sb.read_reg(self.d, SID) or {}).get("sessionCrons")
        self.assertEqual([c["id"] for c in rec], ["dddd4444"],
                         "erasing it here was how the fix's first draft lost the wakeup pre-due")

    def test_a_fired_one_shot_still_drops(self):
        # a genuinely FIRED one-shot is always past due at its own turn's Stop hook (armed 17:08,
        # due 17:13, fired 17:13, hook ~17:13:30) — strict-future keep means it drops here, so the
        # sweep can never double-fire it. Plant the record with its arm time BEFORE the (past) due.
        past = time.localtime(time.time() - 120)
        rec = {"id": "eeee5555", "cron": "%d %d * * *" % (past[4], past[3]),
               "prompt": "p", "kind": "loop", "recurring": False, "armedAt": int(time.time() - 600)}
        self._reg(sessionCrons=[rec], sessionCronsAt=int(time.time() - 600))
        s = sb.SdkSession(self.be, sb.read_reg(self.d, SID))
        asyncio.run(s._stop_hook({"session_crons": []}, None, None))
        self.assertEqual((sb.read_reg(self.d, SID) or {}).get("sessionCrons"), [])

    def test_cancelling_the_last_timer_clears_the_record(self):
        s = self._sess()
        asyncio.run(s._stop_hook({"session_crons": self.CRONS}, None, None))
        asyncio.run(s._stop_hook({"session_crons": []}, None, None))
        self.assertEqual((sb.read_reg(self.d, SID) or {}).get("sessionCrons"), [],
                         "a stale armed set would keep reviving a session with nothing to fire")

    def test_a_payload_without_the_field_changes_nothing(self):
        s = self._sess()
        asyncio.run(s._stop_hook({"session_crons": self.CRONS}, None, None))
        asyncio.run(s._stop_hook({"transcript_path": "/tmp/x.jsonl"}, None, None))
        self.assertTrue((sb.read_reg(self.d, SID) or {}).get("sessionCrons"),
                        "absence of the field is not a cancellation")


class SweepKeepsTimerArmedSessionsAlive(_Backend):
    CRONS = [{"id": "bbbb2222", "cron": "5 * * * *", "prompt": "p", "kind": "loop", "recurring": False}]

    def test_a_dormant_timer_armed_session_is_revived(self):
        self._reg(sessionCrons=self.CRONS)
        ensured = []
        self.be._ensure = lambda sid, on_boot_settled=None: ensured.append(sid) or True
        self.assertEqual(self.be.ensure_scheduled(), 1)
        self.assertEqual(ensured, [SID])
        self.assertTrue(any("armed timer" in m for m in self.logs), "revivals are logged, never silent")

    def test_sessions_without_timers_stay_lazy(self):
        self._reg()                                     # alive, no sessionCrons
        self.be._ensure = lambda sid, on_boot_settled=None: self.fail("must not touch a timer-less session")
        self.assertEqual(self.be.ensure_scheduled(), 0)

    def test_dead_and_thread_regs_are_skipped(self):
        self._reg(sessionCrons=self.CRONS, alive=False)
        other = "11111111-2222-3333-4444-000000000022"
        self._reg(sid=other, sessionCrons=self.CRONS, threadOf=SID)
        self.be._ensure = lambda sid, on_boot_settled=None: self.fail("dead/thread regs are not sessions to revive")
        self.assertEqual(self.be.ensure_scheduled(), 0)

    def test_the_retry_floor_bounds_a_spawn_storm(self):
        self._reg(sessionCrons=self.CRONS)
        ensured = []
        self.be._ensure = lambda sid, on_boot_settled=None: ensured.append(sid) or True
        self.be.ensure_scheduled()
        self.be.ensure_scheduled()                      # a moment later — the CLI died instantly
        self.assertEqual(len(ensured), 1,
                         "the producer sweeps every ~3s; without the floor a spawn-crashing "
                         "session becomes a spawn storm")

    def test_a_running_session_is_left_alone(self):
        self._reg(sessionCrons=self.CRONS)

        class T:
            def is_alive(self):
                return True

        class S:
            thread = T()
        self.be.sessions[SID] = S()
        self.be._ensure = lambda sid, on_boot_settled=None: self.fail("already running — nothing to do")
        self.assertEqual(self.be.ensure_scheduled(), 0)


class WakeupDueEpoch(unittest.TestCase):
    """The one shape romp self-fires: ScheduleWakeup's '<min> <hour> * * *' one-shot, local time."""

    def test_same_day_due(self):
        armed = time.mktime((2026, 8, 28, 17, 8, 0, 0, 0, -1))
        due = sb.wakeup_due_epoch("13 17 * * *", armed)
        self.assertEqual(time.localtime(due)[3:5], (17, 13))
        self.assertLess(due - armed, 3600)

    def test_midnight_wrap(self):
        armed = time.mktime((2026, 8, 28, 23, 50, 0, 0, 0, -1))
        due = sb.wakeup_due_epoch("5 0 * * *", armed)
        self.assertGreater(due, armed, "00:05 armed at 23:50 is TOMORROW, not 24h ago")
        self.assertLess(due - armed, 3600)

    def test_anything_else_is_not_ours_to_fire(self):
        armed = time.time()
        for cron in ("*/5 * * * *", "50 * * * *", "5 0 1 * *", "5 0 * * 1", "junk", "", None):
            self.assertIsNone(sb.wakeup_due_epoch(cron, armed), repr(cron))


class LostWakeupDelivery(_Backend):
    """A process recycle loses ScheduleWakeup arms (verified live 2026-08-28: kill + revive kept the
    recurring cron, dropped the pending wakeup). The reg record outlives the process; a one-shot past
    due by the grace and STILL recorded had no process to fire it — romp delivers its own prompt."""

    def _shot(self, due_offset, armed_offset=-600, recurring=False):
        now = time.time()
        due = time.localtime(now + due_offset)
        return ({"id": "cccc3333", "cron": "%d %d * * *" % (due[4], due[3]),
                 "prompt": "Reply with exactly: wakeup-fired", "kind": "", "recurring": recurring},
                now + armed_offset)

    def test_past_due_unfired_one_shot_is_delivered_and_stripped(self):
        shot, armed = self._shot(due_offset=-300)
        self._reg(sessionCrons=[shot], sessionCronsAt=armed)
        sent = []
        self.be.send = lambda sid, text: sent.append((sid, text)) or True
        self.assertEqual(self.be.deliver_lost_wakeups(), 1)
        self.assertEqual(sent, [(SID, "Reply with exactly: wakeup-fired")])
        self.assertEqual((sb.read_reg(self.d, SID) or {}).get("sessionCrons"), [],
                         "stripped BEFORE delivery — the next pass must never double-deliver")
        self.assertTrue(any("no process to fire it" in m for m in self.logs))

    def test_not_yet_due_stays_armed_and_undelivered(self):
        shot, armed = self._shot(due_offset=+600)
        self._reg(sessionCrons=[shot], sessionCronsAt=armed)
        self.be.send = lambda sid, text: self.fail("not due — the CLI scheduler still owns it")
        self.assertEqual(self.be.deliver_lost_wakeups(), 0)
        self.assertTrue((sb.read_reg(self.d, SID) or {}).get("sessionCrons"))

    def test_the_grace_covers_a_genuine_fire_settling(self):
        shot, armed = self._shot(due_offset=-30)       # due 30s ago — inside the 90s grace
        self._reg(sessionCrons=[shot], sessionCronsAt=armed)
        self.be.send = lambda sid, text: self.fail("a genuine fire's Stop hook gets time to erase the record")
        self.assertEqual(self.be.deliver_lost_wakeups(), 0)

    def test_recurring_crons_are_never_self_fired(self):
        shot, armed = self._shot(due_offset=-300, recurring=True)
        self._reg(sessionCrons=[shot], sessionCronsAt=armed)
        self.be.send = lambda sid, text: self.fail("recurring = keep-alive only; the CLI fires those")
        self.assertEqual(self.be.deliver_lost_wakeups(), 0)

    def test_a_mid_turn_session_is_left_alone(self):
        shot, armed = self._shot(due_offset=-300)
        self._reg(sessionCrons=[shot], sessionCronsAt=armed)

        class T:
            def is_alive(self):
                return True

        class S:
            thread = T()
            inflight = 1
        self.be.sessions[SID] = S()
        self.be.send = lambda sid, text: self.fail("mid-turn: a genuine fire may be settling")
        self.assertEqual(self.be.deliver_lost_wakeups(), 0)


class ProducerRunsTheSweep(unittest.TestCase):
    def test_the_producer_calls_ensure_scheduled(self):
        with open(os.path.join(BIN, "romp-kernel")) as f:
            src = f.read()
        self.assertIn("ensure_scheduled()", src, "the sweep must run with no dashboard connected")
        self.assertIn("deliver_lost_wakeups()", src, "orphaned one-shots fire from the same pass")
        self.assertIn('sys.stderr.write("scheduled-sweep: %s\\n"', src,
                      "guarded — a sweep failure must never kill the producer cycle")


if __name__ == "__main__":
    unittest.main()
