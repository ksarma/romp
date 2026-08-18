#!/usr/bin/env python3
"""Idle-queue drive — self-scheduled work must wake an idle SDK session (the user 2026-08-18).

The bug, hit twice in one day: under the SDK backend, a session's own scheduled work — a recurring
Monitor, a cron firing, a background task's completion notice — can only ENQUEUE into the CLI's queue
(the transcript's queue-operation records). Nothing drives an idle session's queue into a turn: an
overnight 15-minute Monitor stacked 33 on-time <task-notification> enqueues with no dequeue while the
session ran zero turns, until the next human message hours later. Verified against a live transcript:
the CLI starts turns from idle for background-AGENT completion notifications (their enqueue is dequeued
within milliseconds and lands as a user record), but Monitor/cron/bash notifications only ever enqueue
— they are never dequeued and never reach the model at all, so a driven turn must carry the queued
texts itself.

The fix under test, in three parts:
  * kernel._undelivered_wake_tail: the transcript's trailing unconsumed enqueues — enqueues with NO
    later dequeue/remove/user/assistant record ("enqueues newer than the last dequeue/turn"). The
    parse rides the normal push cadence; the parse IS the event.
  * kernel._idle_queue_drive_tick: the pusher-cycle job that finds idle SDK sessions with a wake
    signal in that tail and hands them to the backend. Kernel-side gates: the global retry pause,
    per-session retry suppression, an API-error block (the auto-retry tick owns those).
  * SdkBackend.drive_idle_queue: gates (open turn, compaction, ended/cut sessions), a per-watermark
    latch (one drive per newest-enqueue, persisted so a kernel restart can't re-fire), and delivery —
    reconnect-if-dormant via _ensure with boot-reconcile's stagger, then enqueue() of the CLI's OWN
    queued texts verbatim (no synthetic prompt), the exact channel boot-reconcile's restored queues
    ride.

Synthetic transcripts only: placeholder uuids, invented notification text, TESTHOST.
"""
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_idledrain", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_idledrain", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
SRC = open(os.path.join(BIN, "romp-kernel")).read()

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "11111111-2222-3333-4444-666666666666"
TS = "2026-08-18T06:%02d:%02d.000Z"


def _wrap(n=0, tid="b1111111a"):
    """A synthetic Monitor task-notification, the shape the CLI enqueues (invented text)."""
    return ("<task-notification>\n<task-id>%s</task-id>\n<summary>Monitor event: \"nightly check\"</summary>"
            "\n<event>[tick %d] heartbeat</event>\n</task-notification>" % (tid, n))


def _qop(op, content=None, ts=TS % (14, 0)):
    o = {"type": "queue-operation", "operation": op, "sessionId": SID, "timestamp": ts}
    if content is not None:
        o["content"] = content
    return o


def _urec(text="status?", meta=False, ts=TS % (7, 0)):
    o = {"type": "user", "uuid": "22222222-2222-3333-4444-555555555555", "timestamp": ts,
         "message": {"role": "user", "content": text}}
    if meta:
        o["isMeta"] = True
    return o


def _arec(text="done.", ts=TS % (7, 30), api_error=False):
    o = {"type": "assistant", "uuid": "33333333-2222-3333-4444-555555555555", "timestamp": ts,
         "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}
    if api_error:
        o["isApiErrorMessage"] = True
        o["apiErrorStatus"] = 500
        o["error"] = "server_error"
    return o


def _write_tx(path, recs):
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def _turn(ts_u=TS % (7, 0), ts_a=TS % (7, 30)):
    """One completed turn: a user record and its assistant reply."""
    return [_urec(ts=ts_u), _arec(ts=ts_a)]


def _backlog(count=3, minute0=14):
    """`count` Monitor enqueues, the overnight shape (enqueue records, no dequeue)."""
    return [_qop("enqueue", _wrap(i), ts=TS % (minute0 + i, 9)) for i in range(count)]


class WakeTail(unittest.TestCase):
    """kernel._undelivered_wake_tail — the trailing unconsumed enqueues, from the transcript's own
    queue-operation records (the authoritative queue; the display fold _pending_queued is untouched)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.tx = os.path.join(self.dir, SID + ".jsonl")

    def _tail(self, recs):
        _write_tx(self.tx, recs)
        return km._undelivered_wake_tail(self.tx)

    def test_overnight_backlog_is_the_tail(self):
        entries, mark = self._tail(_turn() + _backlog(33))
        self.assertEqual(len(entries), 33, "every undelivered enqueue after the last turn is the tail")
        self.assertTrue(all(e["wrapper"] for e in entries), "task-notifications are wake signals")
        self.assertEqual([e["text"] for e in entries], [_wrap(i) for i in range(33)], "texts verbatim, in order")
        self.assertIsNotNone(mark, "the newest enqueue is the watermark")
        self.assertEqual(mark[0], entries[-1]["pos"], "watermark = the newest enqueue's position")

    def test_consumed_enqueues_are_not_a_tail(self):
        entries, mark = self._tail(_turn() + [_qop("enqueue", _wrap()), _qop("dequeue")])
        self.assertEqual((entries, mark), ([], None), "a dequeue means the CLI consumed the queue")
        entries, mark = self._tail(_turn() + [_qop("enqueue", _wrap()), _qop("remove", _wrap())])
        self.assertEqual((entries, mark), ([], None), "a remove means the CLI discarded it — its call")

    def test_a_turn_after_the_enqueue_clears_it(self):
        entries, mark = self._tail(_turn() + [_qop("enqueue", _wrap())] + [_urec(ts=TS % (15, 0))])
        self.assertEqual((entries, mark), ([], None), "a later user record: the session was awake after it")
        entries, mark = self._tail(_turn() + [_qop("enqueue", _wrap())] + [_arec(ts=TS % (15, 0))])
        self.assertEqual((entries, mark), ([], None), "a later assistant record: same")

    def test_meta_records_do_not_eat_wake_signals(self):
        entries, _ = self._tail(_turn() + [_qop("enqueue", _wrap())] + [_urec(meta=True, ts=TS % (15, 0))])
        self.assertEqual(len(entries), 1, "an isMeta record is CLI bookkeeping, not the session being awake")

    def test_non_wrapper_content_is_in_the_tail_but_not_a_wake_signal(self):
        entries, mark = self._tail(_turn() + [_qop("enqueue", "a queued plain message")])
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["wrapper"], "a plain queued message is the CLI's own to deliver")
        self.assertIsNotNone(mark)

    def test_contentless_enqueues_are_not_wake_signals(self):
        entries, _ = self._tail(_turn() + [_qop("enqueue")])
        self.assertTrue(all(not e["wrapper"] for e in entries), "no content, nothing to deliver")


class FakeDriveBackend:
    """Records what the tick hands over; owns() by a fixed sid set."""

    def __init__(self, owned):
        self.owned = set(owned)
        self.calls = []

    def owns(self, sid):
        return sid in self.owned

    def drive_idle_queue(self, cands):
        self.calls.append(cands)


class DriveTick(unittest.TestCase):
    """kernel._idle_queue_drive_tick — kernel-side gates, then hand off to the backend."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.tx = os.path.join(self.dir, SID + ".jsonl")
        _write_tx(self.tx, _turn() + _backlog(3))
        self.fb = FakeDriveBackend({SID})
        self.alive = [{"sid": SID, "path": self.tx, "name": "web"}]

    def tearDown(self):
        km._set_retry_paused(False)
        km._clear_session_retry_suppress(SID)

    def _tick(self):
        with mock.patch.object(km, "_sdk", lambda: self.fb), \
             mock.patch.object(km, "_alive_sessions", lambda now, tmux: self.alive):
            km._idle_queue_drive_tick(int(time.time()), {SID: {}})

    def test_wake_signals_reach_the_backend(self):
        self._tick()
        self.assertEqual(len(self.fb.calls), 1, "one batch per tick")
        (cand,) = self.fb.calls[0]
        self.assertEqual(cand["sid"], SID)
        self.assertEqual(len(cand["entries"]), 3)
        self.assertIsNotNone(cand["mark"])

    def test_the_global_pause_stands_down(self):
        km._set_retry_paused(True)
        self._tick()
        self.assertEqual(self.fb.calls, [], "the global pause stops all self-driving")

    def test_a_retry_suppressed_session_stands_down(self):
        km._suppress_session_retry(SID)
        self._tick()
        self.assertEqual(self.fb.calls, [], "the user interrupted this thread's storm — hands off")

    def test_an_api_error_blocked_session_stands_down(self):
        _write_tx(self.tx, _turn() + [_arec(ts=TS % (8, 0), api_error=True)] + _backlog(3))
        self._tick()
        self.assertEqual(self.fb.calls, [], "an API-error block is the auto-retry tick's to clear")

    def test_a_tail_without_wake_signals_does_not_drive(self):
        _write_tx(self.tx, _turn() + [_qop("enqueue", "a queued plain message")])
        self._tick()
        self.assertEqual(self.fb.calls, [], "a bare queued message is the CLI's own to deliver")

    def test_sessions_of_other_backends_are_skipped(self):
        self.fb.owned = set()
        self._tick()
        self.assertEqual(self.fb.calls, [], "tmux CLIs are interactive — they deliver their own queue")

    def test_the_pusher_cycle_runs_the_tick(self):
        # (now, tmux) — the cycle's ONE liveness snapshot, not a per-job fresh read (2026-08-10 CPU fix)
        self.assertIn("_idle_queue_drive_tick(now, tmux)", SRC,
                      "the pusher cycle drives queued wake signals server-side — unattended, no client needed")


class FakeLive:
    """A live, connected, idle SdkSession as drive_idle_queue sees one (duck-typed)."""

    def __init__(self, name="web"):
        self.name = name
        self.sid = SID
        self.ended = False
        self.inflight = 0
        self._compacting = False
        self._clearing = False
        self._rewind_to = ""
        self._rewind_armed = False
        self.sent = []
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._stop.wait, daemon=True)
        self.thread.start()

    def enqueue(self, text):
        self.sent.append(text)

    def close(self):
        self._stop.set()


def _ent(pos, text, wrapper=True, ts=TS % (14, 0)):
    return {"pos": pos, "ts": ts, "text": text, "wrapper": wrapper}


class DriveDelivery(unittest.TestCase):
    """SdkBackend.drive_idle_queue — gates, the watermark latch, delivery, loudness."""

    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.logs = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                log=self.logs.append)
        sb.write_reg(self.state, SID, {"sid": SID, "name": "web", "alive": True})
        self.tx = str(self.state / (SID + ".jsonl"))
        self.fakes = []

    def tearDown(self):
        for f in self.fakes:
            f.close()

    def _live(self, **kw):
        s = FakeLive()
        for k, v in kw.items():
            setattr(s, k, v)
        self.fakes.append(s)
        self.be.sessions[SID] = s
        return s

    def _cand(self, entries=None, mark=None, sid=SID):
        entries = entries if entries is not None else [_ent(10, _wrap(0)), _ent(11, _wrap(1))]
        return {"sid": sid, "path": self.tx, "entries": entries,
                "mark": mark or (entries[-1]["pos"], entries[-1]["ts"])}

    def _problems(self):
        return [p["text"] for p in self.be.problems()]

    def test_cron_shape_live_idle_session_gets_the_backlog(self):
        s = self._live()
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(s.sent, [_wrap(0) + "\n\n" + _wrap(1)],
                         "one driven turn carrying the CLI's own queued texts verbatim, in order")
        self.assertTrue(any("idle-queue drive" in str(m) and "web" in str(m) for m in self.logs),
                        "each drive logs one kernel-log line naming the session")
        self.assertFalse(any("idle-queue drive" in p for p in self._problems()),
                         "a normal drive is not a problem")

    def test_an_open_turn_stands_down_without_burning_the_watermark(self):
        s = self._live(inflight=1)
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(s.sent, [], "never mid-turn")
        s.inflight = 0
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(len(s.sent), 1, "the stand-down did not latch — the backlog still delivers")

    def test_compacting_and_clearing_stand_down(self):
        s = self._live(_compacting=True)
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(s.sent, [])
        s._compacting, s._clearing = False, True
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(s.sent, [])

    def test_an_ended_session_never_revives(self):
        sb.write_reg(self.state, SID, {"sid": SID, "name": "web", "alive": False})
        ensured = []
        with mock.patch.object(self.be, "_ensure", lambda sid, **kw: ensured.append(sid)):
            self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(ensured, [], "the user ended this session — housekeeping must not revive it")

    def test_a_cut_turn_stands_down(self):
        sb.append_state(self.state, SID, "working")   # the tail a kernel-death cut leaves
        ensured = []
        with mock.patch.object(self.be, "_ensure", lambda sid, **kw: ensured.append(sid)):
            self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(ensured, [], "a cut turn is the boot/crash resume machinery's recovery")

    def test_one_drive_per_watermark(self):
        s = self._live()
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(len(s.sent), 1, "the same watermark never drives twice")

    def test_a_newer_enqueue_rearms_and_delivers_only_the_new(self):
        s = self._live()
        self.be.drive_idle_queue([self._cand()], wait=True)
        entries = [_ent(10, _wrap(0)), _ent(11, _wrap(1)), _ent(12, _wrap(2), ts=TS % (15, 0))]
        self.be.drive_idle_queue([self._cand(entries=entries)], wait=True)
        self.assertEqual(len(s.sent), 2, "a newer enqueue is new information — one more drive")
        self.assertEqual(s.sent[1], _wrap(2), "already-driven texts are not re-sent")

    def test_the_watermark_survives_a_kernel_restart(self):
        s = self._live()
        self.be.drive_idle_queue([self._cand()], wait=True)
        be2 = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        s2 = FakeLive()
        self.fakes.append(s2)
        be2.sessions[SID] = s2
        be2.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(s2.sent, [], "the latch is persisted — a restart cannot re-fire a driven backlog")

    def test_a_dormant_session_is_reconnected_and_delivered(self):
        cbs = []

        def fake_ensure(sid, on_boot_settled=None):
            cbs.append(on_boot_settled)
            if on_boot_settled:
                on_boot_settled()
            return self._live()

        with mock.patch.object(self.be, "_ensure", fake_ensure):
            self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertEqual(len(self.fakes), 1)
        self.assertEqual(len(self.fakes[0].sent), 1, "reconnect-if-dormant, then deliver")
        self.assertTrue(cbs and cbs[0] is not None, "the spawn holds a stagger slot until the CLI proves up")

    def test_dormant_spawns_are_staggered_like_boot_resume(self):
        sb.write_reg(self.state, SID2, {"sid": SID2, "name": "api", "alive": True})
        self.be._drive_sem = threading.Semaphore(1)
        old_slot = sb.BOOT_RESUME_SLOT_S
        sb.BOOT_RESUME_SLOT_S = 0.05
        try:
            def fake_ensure(sid, on_boot_settled=None):
                return self._live()          # never fires the callback: the CLI never proves up

            with mock.patch.object(self.be, "_ensure", fake_ensure):
                self.be.drive_idle_queue(
                    [self._cand(), self._cand(entries=[_ent(10, _wrap(9))], sid=SID2)], wait=True)
        finally:
            sb.BOOT_RESUME_SLOT_S = old_slot
        self.assertEqual(len(self.fakes), 2, "the backstop is loud but the sweep continues")
        self.assertTrue(any("backstop" in p for p in self._problems()),
                        "an expired stagger slot says so where the user looks")

    def test_a_refused_reconnect_is_problem_ring_loud(self):
        with mock.patch.object(self.be, "_ensure", lambda sid, **kw: None):
            self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertTrue(any("idle-queue drive" in p for p in self._problems()),
                        "a drive failure is never silent")

    def test_a_failed_send_is_problem_ring_loud(self):
        s = self._live()
        s.enqueue = mock.Mock(side_effect=RuntimeError("stream gone"))
        self.be.drive_idle_queue([self._cand()], wait=True)
        self.assertTrue(any("idle-queue drive" in p for p in self._problems()))

    def test_boot_parity_the_drive_rides_the_persisted_queue_channel(self):
        """The drive delivers via enqueue() — the same channel boot-reconcile restores through — so a
        kernel death between the drive and the CLI taking the turn loses nothing: the text is in the
        reg's persisted queue and the next boot re-delivers it, exactly as for any queued message."""
        reg = sb.read_reg(self.state, SID)
        real = sb.SdkSession(self.be, reg)            # never started: enqueue works, nothing spawns
        with mock.patch.object(self.be, "_ensure", lambda sid, **kw: real):
            self.be.drive_idle_queue([self._cand()], wait=True)
        q = (sb.read_reg(self.state, SID) or {}).get("queue") or []
        self.assertEqual(q, [_wrap(0) + "\n\n" + _wrap(1)],
                         "the driven text persists like any queued message until the CLI takes it")


class OvernightShape(unittest.TestCase):
    """The exact bug, end to end through the kernel tick and a real backend: an idle session, a
    Monitor's overnight enqueue backlog, no external input — a turn is driven, once, with the backlog."""

    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=lambda m: None)
        sb.write_reg(self.state, SID, {"sid": SID, "name": "web", "alive": True})
        self.tx = str(self.state / (SID + ".jsonl"))
        _write_tx(self.tx, _turn() + _backlog(33))
        self.alive = [{"sid": SID, "path": self.tx, "name": "web"}]
        self.fake = FakeLive()

    def tearDown(self):
        self.fake.close()

    def test_the_overnight_backlog_drives_one_turn(self):
        with mock.patch.object(self.be, "_ensure", lambda sid, **kw: self.fake), \
             mock.patch.object(km, "_sdk", lambda: self.be), \
             mock.patch.object(km, "_alive_sessions", lambda now, tmux: self.alive):
            km._idle_queue_drive_tick(int(time.time()), {SID: {}})
            # the drive runs on a worker thread from the tick — wait for it (bounded)
            for _ in range(100):
                if self.fake.sent:
                    break
                time.sleep(0.02)
            km._idle_queue_drive_tick(int(time.time()), {SID: {}})   # the same parse again: latched
            time.sleep(0.1)
        self.assertEqual(len(self.fake.sent), 1, "one driven turn, not one per notification, not zero")
        for i in range(33):
            self.assertIn(_wrap(i), self.fake.sent[0], "the whole backlog is delivered")


if __name__ == "__main__":
    unittest.main()
