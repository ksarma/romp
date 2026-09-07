#!/usr/bin/env python3
"""The per-restart CUT LEDGER (T121, 2026-08-27): every restart writes ONE row to
restart-cuts.jsonl naming what it cut — the drain's effect is measurable only if clean restarts
write rows too (an empty cutTurns list is the success metric, not noise). The row joins the
restart-audit tail for WHO asked, counts the persisted kernel watches (which SURVIVE restarts by
construction — they ride as context, not cuts), and its docstring documents the two things the
kernel cannot do: count in-session watchers/Claude-side workflows (invisible here — the kernel
watch primitive is the fix), and un-write the CLI's own interrupted-by-user transcript stamps
(romp never rewrites CLI transcripts; romp's own records already distinguish machine cuts).
Hermetic state; synthetic sids only."""
import json
import os
import signal
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — module import runs boot reconcile against the state root.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = SourceFileLoader("romp_kernel_cuts", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-00000000c001"


class CutRow(unittest.TestCase):
    def test_row_shape_from_a_cutting_drain(self):
        row = km._restart_cut_row({"stopped": 3, "inflight": 2, "unjoined": 1, "reaped": 1,
                                   "cutTurns": [{"sid": SID, "name": "web"}]},
                                  watches_armed=4, audit_reason="kernel-asks-manager-restart-all: self-update",
                                  now=1_781_000_000)
        self.assertEqual(row["t"], 1_781_000_000)
        self.assertEqual(row["cutTurns"], [{"sid": SID, "name": "web"}])
        self.assertEqual((row["stopped"], row["unjoined"], row["reaped"]), (3, 1, 1))
        self.assertEqual(row["watchesArmed"], 4, "persisted watches SURVIVE — context, never cuts")
        self.assertIn("self-update", row["reason"])

    def test_a_clean_drain_still_writes_its_row(self):
        # the success metric: a restart that cut NOTHING is a row with an empty list
        row = km._restart_cut_row({"stopped": 5, "inflight": 0, "unjoined": 0, "reaped": 0,
                                   "cutTurns": []}, now=1)
        self.assertEqual(row["cutTurns"], [])
        row = km._restart_cut_row(None, now=1)   # no backend at all — still a row
        self.assertEqual(row["cutTurns"], [])

    def test_append_is_jsonl_and_never_raises(self):
        km._append_restart_cut(km._restart_cut_row({"cutTurns": []}, now=2))
        km._append_restart_cut(km._restart_cut_row({"cutTurns": [{"sid": SID, "name": "api"}]}, now=3))
        rows = [json.loads(l) for l in km.RESTART_CUTS_FILE.read_text().strip().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["cutTurns"][0]["sid"], SID)
        km.RESTART_CUTS_FILE.unlink()

    def test_reason_joins_the_recent_audit_tail_only(self):
        audit = jd.STATE / "restart-audit.jsonl"
        audit.write_text(json.dumps({"t": 1000, "action": "kernel-asks-manager-restart-all",
                                     "reason": "self-update"}) + "\n")
        self.assertIn("self-update", km._recent_restart_reason(window=90, now=1050))
        self.assertEqual(km._recent_restart_reason(window=90, now=5000), "",
                         "a stale audit row is not this restart's cause")
        audit.unlink()
        self.assertEqual(km._recent_restart_reason(now=1050), "", "no audit → anonymous, honestly")

    def test_a_cutting_drain_counts_mid_shutdown_and_threadless_sessions(self):
        # T143's two undercounts, executed: a session already flagged `ended` with a live in-flight
        # turn IS a cut (its CLI is reaped all the same — the old `not s.ended` clause filtered it
        # out of cutTurns: 10 transcript-verified cuts vs 7 rows), and a constructed-but-never-
        # started session (thread=None) must not crash the whole drain recordless.
        import types as _t
        sbmod = km.sb if hasattr(km, "sb") else None
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")).read()
        self.assertIn("cut = [{\"sid\": s.sid, \"name\": s.name} for s in sessions if s.inflight]", src,
                      "every in-flight session is a cut — ended included (the join, not a filter)")
        self.assertIn("if s.thread is not None:", src,
                      "a threadless session can no longer crash the drain")

    def test_sigterm_handler_writes_the_ledger(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        block = src[src.index("def _graceful_term"):src.index("def main():")]
        self.assertIn("row = _restart_cut_row(res, watches_armed=len(_pr_watches) + len(_watches),",
                      block, "the row counts BOTH persisted watch stores (T143) — and is built in the")
        self.assertIn("finally:", block)
        self.assertIn("_append_restart_cut(row)", block,
                      "…FINALLY block, so a raising drain still writes what it knew (T143: 2 of 18 "
                      "restarts died recordless)")
        self.assertIn('row["drainError"]', block, "an errored drain's row names the error")
        self.assertIn("_drain_and_exit(_recent_restart_reason(), signum=signum", block,
                      "the request on record is read AT SIGNAL TIME, before the drain: a row that lands "
                      "during the drain did not send this signal")
        self.assertIn("reason = _unrequested_signal_reason(signum, be)", block,
                      "a SIGTERM with no request on record leaves its own audit row (2026-09-06: a "
                      "direct signal to the kernel pid had no row anywhere and an empty cut reason)")
        self.assertIn("audit_reason=reason", block)
        self.assertIn("if not _EXIT_ONCE.acquire(blocking=False):", block,
                      "a second SIGTERM mid-drain must not nest a second drain and a second cut row")


class UnrequestedSignal(unittest.TestCase):
    """A SIGTERM nobody asked the manager for (a stray kill, a test that fired a real restart, a
    supervisor stop) used to leave NOTHING: no restart-audit row, an empty cut reason. On 2026-09-06
    such a signal restarted the kernel onto a different python and the two-hour outage that followed
    had no first cause on disk. The handler now records what it can know: the signal, its own and
    its parent's pid, the manager it was told about, whether a manager restart was parked, and that
    no request for it was on record. Sender attribution is out of reach here (a signal.signal handler
    gets no siginfo), so the row says so by what it omits."""

    def setUp(self):
        # Resolved at RUN time, never at import: a later test module's kernel load re-executes the
        # shared judge module and rebinds jd.STATE, so a path captured at class definition points at
        # a state root the code under test no longer writes to (an xdist-only failure otherwise).
        self.AUDIT = jd.STATE / "restart-audit.jsonl"
        for f in (self.AUDIT, km.RESTART_CUTS_FILE):
            if f.exists():
                f.unlink()
        km._EXIT_ONCE = threading.Lock()     # the handler takes it and never gives it back (it exits)
        # no wait for the manager's note by default: the tests that want the wait pass their own
        self._wait = mock.patch.object(km, "SIGNAL_MANAGER_NOTE_WAIT_S", 0)
        self._wait.start()
        # the environment decides whether a manager is thought to exist: default to none (standalone),
        # so a pytest run inside a romp session does not inherit the live manager's pid
        self._env = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items()
                                                 if k != "ROMP_MANAGER_PID"}, clear=True)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._wait.stop()
        for f in (self.AUDIT, km.RESTART_CUTS_FILE):
            if f.exists():
                f.unlink()

    def _rows(self, f):
        return [json.loads(l) for l in f.read_text().strip().splitlines()] if f.exists() else []

    def _dead_pid(self):
        """A pid nothing owns: a child spawned and reaped (never a guess at a number)."""
        p = subprocess.Popen(["true"])
        p.wait()
        return p.pid

    def test_the_row_carries_what_is_knowable(self):
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": "4242"}):
            reason = km._audit_unrequested_signal(signal.SIGTERM, pending=True, now=1_781_000_000)
        self.assertEqual(reason, "signal, not requested through the manager")
        rows = self._rows(self.AUDIT)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["action"], "signal")
        self.assertEqual(row["signal"], "SIGTERM")
        self.assertEqual(row["t"], 1_781_000_000)
        self.assertEqual(row["pid"], os.getpid())
        self.assertEqual(row["ppid"], os.getppid())
        self.assertEqual(row["managerPid"], 4242)
        self.assertIs(row["managerRequested"], False)
        self.assertIs(row["managerStopped"], False)
        self.assertIs(row["managerRestartPending"], True)
        self.assertEqual(row["reason"], reason, "the cut row and the audit row say the same thing")

    def test_no_manager_in_the_environment_is_recorded_as_none(self):
        km._audit_unrequested_signal(signal.SIGTERM, pending=False, now=5)
        row = self._rows(self.AUDIT)[0]
        self.assertIsNone(row["managerPid"], "standalone kernel: no manager to have asked")
        self.assertIs(row["managerRestartPending"], False)

    def test_the_managers_own_kill_row_does_not_hide_who_asked(self):
        # the manager notes every SIGTERM it sends (bin/romp-manager auditSigterm); the requester's row
        # underneath still names WHO, so the cut reason keeps naming the cause, not the messenger
        self.AUDIT.write_text(
            json.dumps({"t": 1000, "action": "kernel-asks-manager-restart-all", "reason": "self-update"}) + "\n"
            + json.dumps({"t": 1001, "action": "manager-sigterm", "kernel": "main", "reason": "restart"}) + "\n")
        self.assertIn("self-update", km._recent_restart_reason(window=90, now=1050))

    def test_the_managers_kill_row_alone_is_still_a_request_on_record(self):
        # a `romp on restart` or a service stop: the manager asked, nobody audited before it; the
        # manager's own row is what keeps this from reading as an unrequested signal
        self.AUDIT.write_text(json.dumps({"t": 1000, "action": "manager-sigterm", "kernel": "main",
                                          "reason": "stop"}) + "\n")
        self.assertEqual(km._recent_restart_reason(window=90, now=1050), "manager-sigterm: stop")
        self.assertEqual(km._recent_restart_reason(window=90, now=5000), "")

    def _fire(self, backend=None):
        """Run the SIGTERM handler in-process: the drain has no backend to stop unless one is given,
        the broadcast is a no-op, and os._exit is caught so the runner survives the handler's
        unconditional exit."""
        with mock.patch.object(km, "_broadcast_restarting", lambda *a, **k: None), \
             mock.patch.object(km, "_sdk_backend", backend), \
             mock.patch.object(km.os, "_exit", side_effect=SystemExit) as ex:
            with self.assertRaises(SystemExit):
                km._graceful_term(signal.SIGTERM, None)
        ex.assert_called_once_with(0)

    def test_the_handler_files_the_row_and_the_cut_reason_when_nothing_asked(self):
        self._fire()
        audit = self._rows(self.AUDIT)
        self.assertEqual([r["action"] for r in audit], ["signal"])
        cuts = self._rows(km.RESTART_CUTS_FILE)
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0]["reason"], "signal, not requested through the manager",
                         "the cut row used to say nothing at all here")
        self.assertEqual(cuts[0]["cutTurns"], [])

    def test_the_handler_leaves_a_requested_restart_alone(self):
        self.AUDIT.write_text(json.dumps({"t": int(__import__("time").time()),
                                          "action": "kernel-asks-manager-restart-all",
                                          "reason": "self-update"}) + "\n")
        self._fire()
        self.assertEqual([r["action"] for r in self._rows(self.AUDIT)], ["kernel-asks-manager-restart-all"],
                         "a request on record is the cause; no signal row is added on top of it")
        self.assertIn("self-update", self._rows(km.RESTART_CUTS_FILE)[0]["reason"])

    def test_a_second_sigterm_mid_drain_does_not_write_a_second_row(self):
        # a service stop signals the kernel, then the manager's shutdownAll signals it again while the
        # first handler drains; the second invocation returns and the first finishes: ONE cut row
        class Nested:
            def drain(inner, timeout):
                km._graceful_term(signal.SIGTERM, None)     # re-entry: must return, not exit
                return {"cutTurns": [{"sid": SID, "name": "web"}], "stopped": 1}
        self._fire(backend=Nested())
        cuts = self._rows(km.RESTART_CUTS_FILE)
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0]["cutTurns"], [{"sid": SID, "name": "web"}],
                         "the FIRST drain's count is the row; the nested call used to write a partial one")

    # ---- the wording: what the handler can honestly say about a signal with no request on record ----

    def test_manager_alive_and_silent_is_the_unrequested_wording(self):
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(os.getpid())}):    # alive: us
            reason = km._unrequested_signal_reason(signal.SIGTERM, wait=0, now=1000)
        self.assertEqual(reason, km.SIGNAL_REASON_UNREQUESTED)
        row = self._rows(self.AUDIT)[0]
        self.assertIs(row["managerStopped"], False)
        self.assertEqual(row["reason"], reason)

    def test_manager_pid_gone_is_the_service_stop_wording(self):
        # SIGTERM to kernel and manager at once, and the manager went first: the kernel can see that
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(self._dead_pid())}):
            reason = km._unrequested_signal_reason(signal.SIGTERM, wait=0, now=1000)
        self.assertEqual(reason, "signal; the manager was stopped too (a service stop or restart)")
        row = self._rows(self.AUDIT)[0]
        self.assertEqual(row["action"], "signal")
        self.assertIs(row["managerStopped"], True)
        self.assertIs(row["managerRequested"], False, "still not a request: nobody asked the manager")

    def test_the_managers_stop_note_landing_after_our_signal_is_the_service_stop_wording(self):
        # the manager writes its note BEFORE it kills, so a note that lands AFTER our signal did not
        # send it: the manager is going down alongside us (node's handler ran after ours)
        audit = self.AUDIT

        def note_lands(_secs):
            with open(audit, "a") as f:
                f.write(json.dumps({"t": 1000, "action": "manager-sigterm", "kernel": "main",
                                    "pid": os.getpid(), "reason": "stop"}) + "\n")
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(os.getpid())}):
            reason = km._unrequested_signal_reason(signal.SIGTERM, wait=5, sleep=note_lands, now=1000)
        self.assertEqual(reason, km.SIGNAL_REASON_MANAGER_STOPPED)
        self.assertEqual([r["action"] for r in self._rows(audit)], ["manager-sigterm", "signal"])

    def test_a_note_about_another_kernel_is_not_ours(self):
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(os.getpid())}):
            self.AUDIT.write_text(json.dumps({"t": 1000, "action": "manager-sigterm", "kernel": "aux",
                                              "pid": os.getpid() + 100000, "reason": "stop"}) + "\n")
            self.assertEqual(km._recent_restart_reason(window=90, now=1000), "",
                             "the manager's note about an aux kernel is not a request on record here")
            reason = km._unrequested_signal_reason(signal.SIGTERM, wait=0, now=1000)
        self.assertEqual(reason, km.SIGNAL_REASON_UNREQUESTED)

    def test_the_handler_end_to_end_for_a_service_stop(self):
        # no sessions to drain, the manager already gone: the cut row says so, in one row each
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(self._dead_pid())}):
            self._fire()
        self.assertEqual([r["action"] for r in self._rows(self.AUDIT)], ["signal"])
        cuts = self._rows(km.RESTART_CUTS_FILE)
        self.assertEqual(cuts[0]["reason"], km.SIGNAL_REASON_MANAGER_STOPPED)

    def test_the_handler_reads_the_request_at_signal_time_not_after_the_drain(self):
        # the manager's note lands DURING the drain (sessions were live): it did not send this signal,
        # so the row says the manager was stopped too, not that the manager asked
        audit = self.AUDIT

        class LateNote:
            def drain(inner, timeout):
                with open(audit, "a") as f:
                    f.write(json.dumps({"t": int(__import__("time").time()), "action": "manager-sigterm",
                                        "kernel": "main", "pid": os.getpid(), "reason": "stop"}) + "\n")
                return {"cutTurns": []}
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(os.getpid())}):
            self._fire(backend=LateNote())
        self.assertEqual(self._rows(km.RESTART_CUTS_FILE)[0]["reason"], km.SIGNAL_REASON_MANAGER_STOPPED)
        self.assertEqual([r["action"] for r in self._rows(audit)], ["manager-sigterm", "signal"])


class RequestOnRecord(unittest.TestCase):
    """_recent_restart_reason: which row of the audit tail explains a SIGTERM arriving now. A row with an
    action is a request; the manager's `manager-sigterm` note is a mechanism note that never outranks a
    request beneath it; a row with no action is skipped, never the answer (main's `romp refresh` writes
    an actionless caller-attribution row, and taking its empty label as the verdict filed every deploy
    as an unrequested signal, review 2026-09-06). Exact row orders, as the writers produce them."""

    REFRESH_CLI_ROW = {"ppid": 4242, "parent": "bash", "sid": "", "name": "", "tty": "/dev/pts/0", "tmux": ""}

    def setUp(self):
        self.AUDIT = jd.STATE / "restart-audit.jsonl"
        if self.AUDIT.exists():
            self.AUDIT.unlink()

    def tearDown(self):
        if self.AUDIT.exists():
            self.AUDIT.unlink()

    def _write(self, *rows):
        self.AUDIT.write_text("".join(json.dumps(r) + "\n" for r in rows))

    def test_a_refresh_from_main_is_a_request_on_record(self):
        # `romp refresh` on main: the CLI's actionless row, then the manager's restart note, then the
        # SIGTERM. The manager's note is what names it; "" here filed a deploy as a stray kill
        self._write(dict(self.REFRESH_CLI_ROW, t=1000),
                    {"t": 1001, "action": "manager-sigterm", "kernel": "main", "pid": os.getpid(), "reason": "restart"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "manager-sigterm: restart")

    def test_a_refresh_that_labels_its_row_is_named_directly(self):
        # the shape a labelled writer produces (an `action: refresh` row): the request wins over the note
        self._write(dict(self.REFRESH_CLI_ROW, t=1000, action="refresh"),
                    {"t": 1001, "action": "manager-sigterm", "kernel": "main", "reason": "restart"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "refresh")

    def test_a_restart_all_the_kernel_asked_for(self):
        self._write({"t": 1000, "action": "kernel-asks-manager-restart-all", "reason": "self-update", "pid": 7},
                    {"t": 1001, "action": "manager-sigterm", "kernel": "main", "reason": "restart"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002),
                         "kernel-asks-manager-restart-all: self-update")

    def test_a_deliberate_stop_outranks_the_managers_stop_note(self):
        # a `down` request row followed by the manager's own stop note, in that order: the stop was
        # deliberate, and the note beneath it must not rewrite it as the manager's doing
        self._write({"t": 1000, "action": "down", "reason": "--now"},
                    {"t": 1001, "action": "manager-sigterm", "kernel": "main", "pid": os.getpid(), "reason": "stop"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "down: --now")

    def test_the_managers_note_alone_answers_when_nothing_else_does(self):
        self._write({"t": 1000, "action": "manager-sigterm", "kernel": "main", "reason": "stop"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "manager-sigterm: stop")

    def test_an_actionless_row_alone_is_not_an_answer(self):
        # a fresh actionless row with nothing else: no verdict in it, so nothing is on record
        self._write(dict(self.REFRESH_CLI_ROW, t=1000))
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "")

    def test_a_genuinely_unrequested_signal_has_nothing_on_record(self):
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "", "no file at all")
        self._write({"t": 100, "action": "kernel-asks-manager-restart-all", "reason": "self-update"},
                    {"t": 101, "action": "manager-sigterm", "kernel": "main", "reason": "restart"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "", "rows from an old restart")

    def test_a_note_aimed_at_another_kernel_pid_is_skipped(self):
        self._write({"t": 1000, "action": "manager-sigterm", "kernel": "aux", "pid": os.getpid() + 100000,
                     "reason": "restart"})
        self.assertEqual(km._recent_restart_reason(window=90, now=1002), "")


class ParentGone(unittest.TestCase):
    """_parent_watch: the manager that spawned the kernel is gone, and the kernel follows it. That exit
    used to be a bare os._exit with nothing in either ledger; now it leaves an audit row (action
    `parent-gone`) and a cut row with the drained turns, like every other exit."""

    def setUp(self):
        self.AUDIT = jd.STATE / "restart-audit.jsonl"
        for f in (self.AUDIT, km.RESTART_CUTS_FILE):
            if f.exists():
                f.unlink()
        km._EXIT_ONCE = threading.Lock()

    def tearDown(self):
        for f in (self.AUDIT, km.RESTART_CUTS_FILE):
            if f.exists():
                f.unlink()

    def _rows(self, f):
        return [json.loads(l) for l in f.read_text().strip().splitlines()] if f.exists() else []

    def test_the_exit_leaves_both_rows(self):
        p = subprocess.Popen(["true"])
        p.wait()                                     # a pid nothing owns
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(p.pid)}), \
             mock.patch.object(km, "_sdk_backend", None), \
             mock.patch.object(km.os, "_exit", side_effect=SystemExit) as ex:
            with self.assertRaises(SystemExit):
                km._parent_watch()
        ex.assert_called_once_with(0)
        audit = self._rows(self.AUDIT)
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]["action"], "parent-gone")
        self.assertEqual(audit[0]["reason"], "the manager exited; the kernel followed it")
        self.assertEqual(audit[0]["managerPid"], p.pid)
        self.assertEqual(audit[0]["pid"], os.getpid())
        cuts = self._rows(km.RESTART_CUTS_FILE)
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0]["reason"], "parent-gone: the manager exited; the kernel followed it")

    def test_standalone_kernel_has_no_parent_to_watch(self):
        env = {k: v for k, v in os.environ.items() if k != "ROMP_MANAGER_PID"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(km.os, "_exit", side_effect=SystemExit) as ex:
            km._parent_watch()
        ex.assert_not_called()
        self.assertFalse(self.AUDIT.exists())

    def test_stands_down_when_the_sigterm_handler_owns_the_exit(self):
        p = subprocess.Popen(["true"])
        p.wait()
        km._EXIT_ONCE.acquire()                      # the handler is mid-drain
        with mock.patch.dict(os.environ, {"ROMP_MANAGER_PID": str(p.pid)}), \
             mock.patch.object(km.os, "_exit", side_effect=SystemExit) as ex:
            km._parent_watch()
        ex.assert_not_called()
        self.assertFalse(self.AUDIT.exists(), "no second row: the handler writes the one that counts")


if __name__ == "__main__":
    unittest.main()
