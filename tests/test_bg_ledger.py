#!/usr/bin/env python3
"""The background-launch LEDGER (2026-08-29): launch facts recorded at the CALL moment by PostToolUse
hooks, replacing the transcript scrape as the durable source for SDK sessions. Payload shapes below are
the ones probe-verified against CLI 2.1.221 / sdk 0.2.144 on 2026-08-28 (backgroundTaskId in the Bash
ack; error+is_interrupt on PostToolUseFailure; background_tasks [{id,type,status,description,command}]
on the Stop payload). Synthetic fixtures only."""
import asyncio
import json
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
sb = SourceFileLoader("romp_sdk_backend_ledger", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-000000000031"


class _Backend(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        sb.write_reg(self.d, SID, {"sid": SID, "name": "web", "cwd": "/tmp", "alive": True})
        self.sess = sb.SdkSession(self.be, sb.read_reg(self.d, SID))

    def _ledger(self):
        reg = sb.read_reg(self.d, SID) or {}
        return reg.get("bgLedger") or [], reg.get("bgLedgerEnded") or []

    def _launch_bash(self, tid="task-aa11", tuid="toolu_01AAA"):
        asyncio.run(self.sess._ledger_tool_hook(
            {"tool_name": "Bash", "tool_use_id": tuid,
             "tool_input": {"command": "sleep 40", "description": "campaign timer",
                            "run_in_background": True},
             "tool_response": {"backgroundTaskId": tid, "stdout": "", "stderr": ""}}, tuid, None))


class LaunchRecording(_Backend):
    def test_a_background_bash_launch_lands_with_its_pairing_keys(self):
        self._launch_bash()
        live, ended = self._ledger()
        self.assertEqual(len(live), 1)
        e = live[0]
        self.assertEqual((e["tid"], e["toolUseId"], e["tool"]), ("task-aa11", "toolu_01AAA", "bash"))
        self.assertEqual(e["desc"], "campaign timer")
        self.assertIsNone(e["deadlineEpoch"], "a background shell runs until done — no deadline")
        self.assertEqual(e["procGen"], self.sess.proc_gen, "launches die with their process")
        self.assertEqual(ended, [])

    def test_foreground_bash_is_a_turn_not_a_launch(self):
        asyncio.run(self.sess._ledger_tool_hook(
            {"tool_name": "Bash", "tool_input": {"command": "ls"},
             "tool_response": {"stdout": "x"}}, "toolu_01BBB", None))
        self.assertEqual(self._ledger(), ([], []))

    def test_monitor_records_its_EXACT_deadline_and_persistent_records_none(self):
        asyncio.run(self.sess._ledger_tool_hook(
            {"tool_name": "Monitor", "tool_use_id": "toolu_01CCC",
             "tool_input": {"description": "watching CI", "timeout_ms": 300000, "persistent": False},
             "tool_response": {"task_id": "mon-1"}}, "toolu_01CCC", None))
        asyncio.run(self.sess._ledger_tool_hook(
            {"tool_name": "Monitor", "tool_use_id": "toolu_01DDD",
             "tool_input": {"description": "log tail", "timeout_ms": 300000, "persistent": True},
             "tool_response": {"task_id": "mon-2"}}, "toolu_01DDD", None))
        live, _ = self._ledger()
        timed = next(e for e in live if e["tid"] == "mon-1")
        furn = next(e for e in live if e["tid"] == "mon-2")
        self.assertAlmostEqual(timed["deadlineEpoch"], time.time() + 300, delta=30,
                               msg="the harness kills the watcher THEN — exact, no +120s grace")
        self.assertFalse(timed["persistent"])
        self.assertIsNone(furn["deadlineEpoch"], "a persistent watcher is furniture, not a wait")
        self.assertTrue(furn["persistent"])


class CalledOffAndFailed(_Backend):
    def test_taskstop_is_a_deliberate_call_off_not_a_crash(self):
        self._launch_bash()
        asyncio.run(self.sess._ledger_tool_hook(
            {"tool_name": "TaskStop", "tool_input": {"task_id": "task-aa11"},
             "tool_response": {}}, "toolu_01EEE", None))
        live, ended = self._ledger()
        self.assertEqual(live, [])
        self.assertEqual((ended[-1]["tid"], ended[-1]["why"]), ("task-aa11", "stopped"))

    def test_a_failed_launch_never_phantom_waits(self):
        self._launch_bash(tid="task-bb22", tuid="toolu_01FFF")
        asyncio.run(self.sess._ledger_fail_hook(
            {"tool_name": "Bash", "tool_use_id": "toolu_01FFF", "is_interrupt": False,
             "error": "command not found",
             "tool_input": {"command": "definitely-not-real", "run_in_background": True}},
            "toolu_01FFF", None))
        live, ended = self._ledger()
        self.assertEqual(live, [])
        self.assertEqual(ended[-1]["why"], "launch-failed")

    def test_a_user_interrupt_is_typed_as_one(self):
        self._launch_bash(tid="task-cc33", tuid="toolu_01GGG")
        asyncio.run(self.sess._ledger_fail_hook(
            {"tool_name": "Bash", "tool_use_id": "toolu_01GGG", "is_interrupt": True},
            "toolu_01GGG", None))
        _, ended = self._ledger()
        self.assertEqual(ended[-1]["why"], "interrupted")


class StopReconciler(_Backend):
    def _stop(self, sess, bg):
        asyncio.run(sess._stop_hook({"background_tasks": bg}, None, None))

    def test_a_live_generation_entry_absent_from_the_payload_ended(self):
        self._launch_bash()
        self._stop(self.sess, [])
        live, ended = self._ledger()
        self.assertEqual(live, [])
        self.assertEqual((ended[-1]["tid"], ended[-1]["why"]), ("task-aa11", "gone"))

    def test_a_dead_generation_entry_died_with_its_process(self):
        self._launch_bash()
        fresh = sb.SdkSession(self.be, sb.read_reg(self.d, SID))   # the recycle
        self._stop(fresh, [])
        _, ended = self._ledger()
        self.assertEqual(ended[-1]["why"], "processDied",
                         "background tasks are children of the CLI — its death is theirs")

    def test_a_still_running_entry_survives_and_an_unseen_one_is_adopted(self):
        self._launch_bash()
        self._stop(self.sess, [
            {"id": "task-aa11", "type": "shell", "status": "running",
             "description": "campaign timer", "command": "sleep 40"},
            {"id": "task-zz99", "type": "shell", "status": "running",
             "description": "a launch the hook missed", "command": "tail -f x"}])
        live, ended = self._ledger()
        self.assertEqual({e["tid"] for e in live}, {"task-aa11", "task-zz99"})
        adopted = next(e for e in live if e["tid"] == "task-zz99")
        self.assertEqual(adopted["src"], "stopReconcile", "the reconciler is the safety net, labeled")
        self.assertEqual([w["why"] for w in ended], [])

    def test_every_stop_stamps_the_turn_end_event(self):
        # lastStopAt is the settle event itself, durable in the reg — consumers (the nudge memo
        # re-arm) read a fact, not a transcript-mtime inference (2026-08-29, romp_cards' seam)
        asyncio.run(self.sess._stop_hook({}, None, None))
        reg = sb.read_reg(self.d, SID) or {}
        self.assertAlmostEqual(reg.get("lastStopAt"), time.time(), delta=30)

    def test_absence_of_the_field_reconciles_nothing(self):
        self._launch_bash()
        asyncio.run(self.sess._stop_hook({"transcript_path": "/tmp/x.jsonl"}, None, None))
        live, _ = self._ledger()
        self.assertEqual(len(live), 1, "no payload field, no verdict — never treat absence as empty")


class KernelSeamPrefersTheLedger(unittest.TestCase):
    """_bg_live_norm's source ladder: live lifecycle set (0.5) > launch ledger (0.6) > transcript
    pairing (0.75). The ledger branch applies EXACT deadlines (recorded moment + 5s skew), never the
    scrape's +120s grace."""

    @classmethod
    def setUpClass(cls):
        cls.km = SourceFileLoader("romp_kernel_ledger", os.path.join(BIN, "romp-kernel")).load_module()

    def setUp(self):
        self.km._tmux_sessions_saved = self.km._tmux_sessions
        (self.km.jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.km._tmux_sessions = self.km._tmux_sessions_saved
        try:
            (self.km.jd.STATE / "sdk" / (SID + ".json")).unlink()
        except OSError:
            pass

    def _write_reg(self, **kw):
        (self.km.jd.STATE / "sdk" / (SID + ".json")).write_text(
            json.dumps({"sid": SID, "name": "web", "alive": True, **kw}))

    def test_ledger_present_beats_the_scrape_and_expires_exactly(self):
        now = time.time()
        self._write_reg(bgLedger=[
            {"tid": "t-1", "toolUseId": "toolu_1", "tool": "bash", "desc": "campaign timer",
             "armedAt": int(now) - 30, "deadlineEpoch": None, "persistent": False, "src": "hook"},
            {"tid": "t-2", "toolUseId": "toolu_2", "tool": "monitor", "desc": "expired watcher",
             "armedAt": int(now) - 400, "deadlineEpoch": now - 60, "persistent": False, "src": "hook"}])
        self.km._tmux_sessions = lambda: {SID: {}}   # live session, NO lifecycle set (mid-reattach)
        got = self.km._bg_live_norm(SID, path="/nonexistent-transcript")
        self.assertEqual([g["tid"] for g in got], ["toolu_1"],
                         "the timed-out watcher is gone AT its recorded deadline — no +120s grace; "
                         "and the scrape was never consulted (the path does not exist)")
        self.assertEqual(got[0]["desc"], "campaign timer")

    def test_present_but_empty_ledger_is_authoritative(self):
        self._write_reg(bgLedger=[])
        self.km._tmux_sessions = lambda: {SID: {}}
        self.assertEqual(self.km._bg_live_norm(SID, path="/nonexistent-transcript"), [],
                         "an empty ledger says NO tasks — never fall through to the scrape")

    def test_a_live_lifecycle_set_still_outranks_the_ledger(self):
        self._write_reg(bgLedger=[{"tid": "stale", "toolUseId": "toolu_9", "tool": "bash",
                                   "desc": "stale", "armedAt": 1, "deadlineEpoch": None,
                                   "persistent": False, "src": "hook"}])
        self.km._tmux_sessions = lambda: {SID: {"bgTasks": [
            {"toolUseId": "toolu_live", "desc": "the stream's truth", "since": 100, "type": "shell"}]}}
        got = self.km._bg_live_norm(SID, path=None)
        self.assertEqual([g["tid"] for g in got], ["toolu_live"])


if __name__ == "__main__":
    unittest.main()
