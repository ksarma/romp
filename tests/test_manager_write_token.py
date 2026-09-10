#!/usr/bin/env python3
"""The kernel's requests to the manager's write doors carry the serve token (2026-09-10).

A local process restarted every session on a machine by posting to the manager's control port, which
took POST /restart-all from anything on loopback. The manager now gates its state-changing doors on
X-Romp-Token (bin/romp-manager writeGate), the header the kernel already requires of local daemons, so
every hop the kernel makes to a door presents it: _restart_this_kernel (the dashboard's Restart, the
converge), _run_main_update (the auto converge and the drift Update, both spellings of the door), and
the self-update script's curl, which reads the token at run time and hands it to curl on stdin, never
in argv. Synthetic only: a recording fake manager on an ephemeral loopback port, invented tokens. The
fork's conftest keeps ROMP_MANAGER_PORT poisoned to a dead port; every hop here names the fake's port
explicitly and the teardown restores the poison.
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare unittest run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
# A dead manager port at module level, never popped (an absent value maps to the DEFAULT port in
# _run_main_update: a live manager, if one is running).
os.environ["ROMP_MANAGER_PORT"] = "1"
km = load_source("romp_kernel_manager_token", os.path.join(BIN, "romp-kernel"))


class _RecordingManager(BaseHTTPRequestHandler):
    """A fake manager door: records every POST's path and X-Romp-Token header, answers `answer`."""
    hits = []
    answer = 200

    def do_POST(self):
        type(self).hits.append((self.path, self.headers.get("X-Romp-Token")))
        self.send_response(type(self).answer)
        self.end_headers()
        # the manager's write gate's one-line bodies, so the kernel's report can carry its words
        body = {401: {"ok": False, "error": "serve token required: send it in X-Romp-Token (the serve-token file under "
                                              "the kernel's state root: /x/state/serve-token for the primary kernel)"},
                503: {"ok": False, "error": "the manager cannot read the serve token (/x/state/serve-token: EACCES); "
                                              "state-changing requests are refused until it can"}}
        self.wfile.write(json.dumps(body.get(type(self).answer, {})).encode())

    def log_message(self, *a):
        pass


def _notice_mock(notices, kinds=None):
    """A _sync_notice stand-in with the real signature (text, ok, kind): records (text, ok) on `notices`
    and the kind on `kinds`. The refusal notice files under kind "refused" (review round 2, 2026-09-10)."""
    def side_effect(text, ok=True, kind="sync"):
        notices.append((text, ok))
        if kinds is not None:
            kinds.append(kind)
    return side_effect


class ManagerHopsCarryTheToken(unittest.TestCase):
    def setUp(self):
        _RecordingManager.hits = []
        _RecordingManager.answer = 200
        self.mgr = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingManager)
        self.port = str(self.mgr.server_address[1])
        threading.Thread(target=self.mgr.serve_forever, daemon=True).start()

    def tearDown(self):
        self.mgr.shutdown()
        self.mgr.server_close()
        os.environ["ROMP_MANAGER_PORT"] = "1"

    def _hits(self, n=1):
        deadline = time.time() + 10
        while len(_RecordingManager.hits) < n and time.time() < deadline:
            time.sleep(0.01)
        return _RecordingManager.hits

    def _audit_rows(self):
        try:
            return [json.loads(x) for x in (km.jd.STATE / "restart-audit.jsonl").read_text().splitlines() if x.strip()]
        except OSError:
            return []

    def _clear_audit(self):
        try:
            (km.jd.STATE / "restart-audit.jsonl").unlink()
        except OSError:
            pass

    def test_the_manager_token_is_the_kernels_own_and_follows_the_file(self):
        # the env spelling first (what this module runs under), so the header is the token the kernel
        # itself gates on; with the env spelling gone the file under the state root is read fresh
        self.assertEqual(km._manager_headers(), {"X-Romp-Token": km.TOKEN})
        tokf = km.jd.STATE / "serve-token"
        tokf.parent.mkdir(parents=True, exist_ok=True)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ROMP_SERVE_TOKEN", None)
            tokf.write_text("reminted-file-token\n")
            self.assertEqual(km._manager_token(), "reminted-file-token")
            tokf.unlink()
            self.assertEqual(km._manager_token(), km.TOKEN, "an unreadable file falls back to this kernel's own")

    def test_restart_this_kernel_presents_the_token(self):
        with mock.patch.object(km, "_audit_restart_request", lambda *a, **k: None):
            km._restart_this_kernel("test restart", manager_port=self.port)
        self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])

    def test_run_main_update_presents_the_token_on_both_spellings_of_the_door(self):
        notices = []
        with mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
             mock.patch.object(km, "_checkout_sha", return_value="abcdef12"), \
             mock.patch.object(km, "_audit_restart_request", lambda *a, **k: None), \
             mock.patch.object(km, "_sync_notice", side_effect=_notice_mock(notices)):
            km._run_main_update("restart", immediate=True, manager_port=self.port)
            km._run_main_update("restart", immediate=False, manager_port=self.port)
        self.assertEqual(self._hits(2), [("/restart-all", km.TOKEN), ("/restart-all?when=quiet", km.TOKEN)])
        self.assertEqual([n for n in notices if not n[1]], [], "the manager took both: no failure notice")

    def test_a_refused_converge_hop_is_said_three_ways(self):
        # review round 1 (2026-09-10): the notice used to say only "the manager answered HTTP 401"; it now
        # says what the refusal means and the way out, and the stderr line and the audit row are new
        _RecordingManager.answer = 401
        self._clear_audit()
        notices, kinds, err = [], [], io.StringIO()
        with mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
             mock.patch.object(km, "_checkout_sha", return_value="abcdef12"), \
             mock.patch.object(km, "_sync_notice", side_effect=_notice_mock(notices, kinds)), \
             contextlib.redirect_stderr(err):
            km._run_main_update("restart", immediate=True, manager_port=self.port)
        self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])
        said = [m for m, ok in notices if not ok]
        self.assertEqual(len(said), 1, notices)
        self.assertEqual(kinds, ["refused"], "filed under the bell's refused kind, not the machine-sync one (review round 2)")
        self.assertIn("romp is updated on disk but the restart request failed", said[0])
        self.assertIn("the manager refused (HTTP 401)", said[0])
        self.assertIn("romp refresh", said[0], "and the way out")
        # review round 2 (2026-09-10): the notice used to name where this kernel read its token, and the
        # state-root path is unbounded, so the bell (cut at SYNC_NOTICE_FIT) lost the way out; the source
        # rides the stderr line and the audit row instead
        self.assertNotIn("read from", said[0])
        self.assertLessEqual(len(said[0]), km.SYNC_NOTICE_FIT, "the bell shows the whole notice")
        line = [l for l in err.getvalue().splitlines() if "refused POST /restart-all" in l]
        self.assertEqual(len(line), 1, err.getvalue())
        self.assertIn("HTTP 401", line[0])
        self.assertIn("serve token required", line[0], "the manager's own words ride along")
        self.assertIn("this kernel's token was read from ROMP_SERVE_TOKEN", line[0], "where the token came from (the env spelling here)")
        rows = [r for r in self._audit_rows() if r.get("action") == km._MANAGER_REFUSED_ACTION]
        self.assertEqual(len(rows), 1, self._audit_rows())
        self.assertEqual((rows[0]["status"], rows[0]["door"], rows[0]["reason"]), (401, "/restart-all", "main-converge: restart"))
        self.assertEqual(rows[0]["tokenSrc"], "ROMP_SERVE_TOKEN", "the row carries the source too")
        self.assertNotIn(km.TOKEN, err.getvalue() + json.dumps(rows) + said[0], "never the token itself")

    def test_every_refusal_notice_fits_the_bell_under_a_realistic_state_path(self):
        # review round 2 (2026-09-10): measured under a profile root, the 401 notice ran to 289 characters
        # against the bell's 240, and the remedy sat last, so what the user saw ended mid-way-out (for the
        # converge's 503 the cut landed inside the command). Both heads, both statuses, the FILE spelling
        # of the token under a long state root: every text fits whole, and none carries the path.
        import pathlib
        root = pathlib.Path("/home/someone/.local/state/romp-profiles/research-kernel-with-a-long-name")
        bodies = {401: json.dumps({"ok": False, "error": "serve token required: send it in X-Romp-Token (the serve-token file "
                                                          "under the kernel's state root: %s/serve-token for the primary kernel, "
                                                          "its own stateDir for a kernels.json profile)" % root}).encode(),
                  503: json.dumps({"ok": False, "error": "the manager cannot read the serve token (%s/serve-token: EACCES); "
                                                          "state-changing requests are refused until it can" % root}).encode()}
        notices = []
        with mock.patch.dict(os.environ, {}, clear=False), \
             mock.patch.object(km.jd, "STATE", root), \
             mock.patch.object(km, "_audit_restart_request", lambda *a, **k: None), \
             mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True, **k: notices.append(m)), \
             contextlib.redirect_stderr(io.StringIO()) as err:
            os.environ.pop("ROMP_SERVE_TOKEN", None)
            for head in ("The restart did not happen", "romp is updated on disk but the restart request failed"):
                for status in (401, 503):
                    with self.subTest(head=head, status=status):
                        text = km._report_manager_refusal("/restart-all", status, bodies[status], reason="r", head=head)
                        self.assertTrue(text.startswith(head + ": "), text)
                        self.assertLessEqual(len(text), km.SYNC_NOTICE_FIT, "%d chars: %s" % (len(text), text))
                        self.assertNotIn(str(root), text, "the path is unbounded, so it stays out of the notice")
                        self.assertIn("HTTP %d" % status, text)
                        self.assertIn("romp refresh", text, "the way out is in the text, whole")
                        self.assertTrue(text.endswith("."), text)
        self.assertEqual(len(notices), 4, "one notice per head and status")
        self.assertIn("this kernel's token was read from %s/serve-token" % root, err.getvalue(),
                      "the stderr line carries the file the notice no longer names")

    def test_a_refused_restart_this_kernel_is_said_three_ways_and_returned(self):
        # the /restart handler and the converge share this hop; its answer used to be discarded
        # (`c.getresponse(); c.close()` under `except Exception: pass`), so a 401 or 503 left no line, no
        # notice and no row (review round 1, 2026-09-10)
        for status, tell in ((401, "does not hold the serve token this kernel sent"), (503, "cannot read its own serve-token file")):
            with self.subTest(status=status):
                _RecordingManager.answer = status
                _RecordingManager.hits = []
                self._clear_audit()
                notices, kinds, err = [], [], io.StringIO()
                with mock.patch.object(km, "_sync_notice", side_effect=_notice_mock(notices, kinds)), \
                     contextlib.redirect_stderr(err):
                    refused = km._restart_this_kernel("test restart", manager_port=self.port)
                self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])
                self.assertTrue(refused, "the refusal comes back to the caller")
                self.assertTrue(refused.startswith("The restart did not happen: "), refused)
                self.assertIn("HTTP %d" % status, refused)
                self.assertIn(tell, refused)
                self.assertIn("romp refresh", refused)
                if status == 401:
                    # review round 2 (2026-09-10): the client behind `romp refresh` reads the token file under the
                    # shell's OWN state root (or ROMP_SERVE_TOKEN), not "the manager's own file", so the remedy
                    # names the root that has to match
                    self.assertIn("Run romp refresh from a shell whose state root (ROMP_STATE_DIR or XDG_STATE_HOME) is the manager's", refused)
                    self.assertNotIn("manager's own token file", refused)
                self.assertEqual([m for m, ok in notices if not ok], [refused], "the same text reaches the bell")
                self.assertEqual(kinds, ["refused"], "under the refused kind")
                lines = [l for l in err.getvalue().splitlines() if "refused POST /restart-all" in l]
                self.assertEqual(len(lines), 1, err.getvalue())
                self.assertIn("HTTP %d" % status, lines[0])
                rows = self._audit_rows()
                self.assertEqual([r["action"] for r in rows], ["kernel-asks-manager-restart-all", km._MANAGER_REFUSED_ACTION], rows)
                self.assertEqual((rows[1]["status"], rows[1]["reason"]), (status, "test restart"))

    def test_an_accepted_hop_and_an_unreachable_manager_return_nothing(self):
        with mock.patch.object(km, "_audit_restart_request", lambda *a, **k: None):
            self.assertEqual(km._restart_this_kernel("ok", manager_port=self.port), "")
            self.assertEqual(km._restart_this_kernel("standalone", manager_port="1"), "", "a dead port is not a refusal")
            self.assertEqual(km._restart_this_kernel("none", manager_port=""), "")
        self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])

    def test_the_refusal_row_restarts_no_kernel(self):
        # the cut reader (_recent_restart_audit) walks the ledger for the request behind a SIGTERM; a row
        # that says the manager refused must never be taken for one
        self.assertIn(km._MANAGER_REFUSED_ACTION, km._NO_RESTART_ACTIONS)


class TheRestartHandlerAcksWhatTheManagerSaid(unittest.TestCase):
    """POST /restart (the dashboard's Restart) acked {ok, restarting: true} BEFORE its hop to the manager, so a
    401 or 503 there was an ack for a restart that never happened. The local leg now asks first and the ack
    carries the manager's answer: 200 restarting:true when it took the request, 502 with the refusal text
    when it did not (review round 1, 2026-09-10). The real Handler on an ephemeral port, a recording fake
    manager, no remotes attached (so every scope takes the local leg)."""

    def setUp(self):
        _RecordingManager.hits = []
        _RecordingManager.answer = 200
        self.mgr = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingManager)
        threading.Thread(target=self.mgr.serve_forever, daemon=True).start()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.assertEqual(dict(km._remotes), {}, "no remotes: the local leg is the one under test")
        os.environ["ROMP_MANAGER_PORT"] = str(self.mgr.server_address[1])

    def tearDown(self):
        os.environ["ROMP_MANAGER_PORT"] = "1"
        for s in (self.srv, self.mgr):
            s.shutdown()
            s.server_close()

    def _post(self):
        req = urllib.request.Request("http://127.0.0.1:%d/restart" % self.srv.server_address[1],
                                     data=json.dumps({"fleet": False}).encode(), method="POST",
                                     headers={"X-Romp-Token": km.TOKEN, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_a_refused_hop_answers_502_with_the_refusal_and_an_accepted_one_200(self):
        _RecordingManager.answer = 401
        notices, kinds = [], []
        with mock.patch.object(km, "_sync_notice", side_effect=_notice_mock(notices, kinds)), \
             contextlib.redirect_stderr(io.StringIO()):
            code, ack = self._post()
        self.assertEqual(code, 502, ack)
        self.assertEqual((ack["ok"], ack["restarting"], ack["fleet"]), (False, False, False))
        self.assertIn("HTTP 401", ack["error"])
        self.assertIn("romp refresh", ack["error"])
        self.assertEqual([m for m, ok in notices if not ok], [ack["error"]], "the same refusal reaches the bell")
        self.assertEqual(kinds, ["refused"], "under the refused kind (review round 2, 2026-09-10)")
        self.assertEqual(_RecordingManager.hits, [("/restart-all", km.TOKEN)], "the hop ran BEFORE the ack")
        _RecordingManager.answer = 200
        code, ack = self._post()
        self.assertEqual((code, ack["ok"], ack["restarting"], ack["fleet"]), (200, True, True, False))
        self.assertEqual(len(_RecordingManager.hits), 2)


# A kernel in a SUBPROCESS: the real Handler on an ephemeral port with _graceful_term installed as its
# SIGTERM handler, the way main() installs it. The ack race below cannot be driven in-process: the exit
# path ends in os._exit, which would take the test runner with it. `setup` is source run after the load
# (a fake SDK backend for the drained arm of the exit path; empty for the no-backend arm).
_SUBPROCESS_KERNEL = r"""
import os, signal, sys
sys.path.insert(0, %(tests)r)
from romp_load import load_source
from http.server import ThreadingHTTPServer
BIN = %(bin)r
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_ack_probe", os.path.join(BIN, "romp-kernel"))
%(setup)s
signal.signal(signal.SIGTERM, km._graceful_term)
srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
sys.stdout.write("%%d %%d\n" %% (srv.server_address[1], os.getpid()))
sys.stdout.flush()
srv.serve_forever()
"""


# A fake SDK backend for the subprocess kernel (review round 3, 2026-09-10): its drain sleeps DRAIN_S and
# cuts nothing, so _drain_and_exit takes the drained arm, whose ack wait is what is left of the two-second
# budget after the drain, not the wait's own two seconds. Installed as the module global the exit path reads.
_FAKE_BACKEND_SETUP = r"""
import time
class _Backend:
    def drain(self, budget):
        time.sleep(%(drain)s)
        return {}
km._sdk_backend = _Backend()
"""


class _SignallingManager(BaseHTTPRequestHandler):
    """A fake manager that does what the real one does on POST /restart-all: SIGTERMs the kernel that asked,
    then answers 200. The pause between the two is the real manager's own ordering made wide enough to be
    deterministic: restartAllOrSelf signals its children and json(200) follows in the same tick, and the
    kernel's exit path with no backend to drain takes a few milliseconds, so at HEAD before the marker the
    ack was lost one time in three to five; with the signal 50 ms ahead of the answer it was lost every
    time. `delay` widens the pause (the drained-arm and past-the-budget cases); `killed_at` is when the
    SIGTERM went out, the clock the client's timings are read against. Records every POST."""
    pid = 0
    hits = []
    delay = 0.05
    killed_at = 0.0

    def do_POST(self):
        type(self).hits.append((self.path, self.headers.get("X-Romp-Token")))
        if type(self).pid:
            type(self).killed_at = time.monotonic()
            os.kill(type(self).pid, 15)
        time.sleep(type(self).delay)
        try:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok": true, "restarted": ["main"]}')
        except OSError:
            pass                                    # the kernel left before the answer (the past-the-budget case)

    def log_message(self, *a):
        pass


class TheAckLandsBeforeTheExit(unittest.TestCase):
    """The local leg of POST /restart hops to the manager BEFORE it acks (round 1: the ack says what the manager
    answered), and a manager that takes the request SIGTERMs this kernel before it answers. _graceful_term
    then ran on the main thread while the handler thread was between the manager's 200 and its own _send,
    and with no SDK backend to drain the exit won that race often enough to lose the ack (review round 2,
    2026-09-10: 20 to 50 percent of the time as measured by two refuters); _ask_peer_to_pull then reported
    a kernel that was restarting as one that never acked. The handler now marks the ack in flight before
    the hop and clears it after _send, and _drain_and_exit waits for the mark to clear, bounded. Twenty
    real kernels, each in its own process, each signalled by the fake manager before it answers: every
    ack lands."""
    RUNS = 20

    @classmethod
    def setUpClass(cls):
        cls.state = tempfile.mkdtemp()
        cls.mgr = ThreadingHTTPServer(("127.0.0.1", 0), _SignallingManager)
        threading.Thread(target=cls.mgr.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.mgr.shutdown()
        cls.mgr.server_close()

    def setUp(self):
        _SignallingManager.delay = 0.05
        _SignallingManager.killed_at = 0.0
        self.addCleanup(setattr, _SignallingManager, "delay", 0.05)

    def _kernel(self, n, setup=""):
        env = {k: v for k, v in os.environ.items() if k not in ("ROMP_STATE_DIR", "ROMP_MANAGER_PID")}
        env.update({"XDG_STATE_HOME": self.state, "ROMP_KERNEL_NO_OPEN": "1", "ROMP_SERVE_TOKEN": km.TOKEN,
                    "ROMP_MANAGER_PORT": str(self.mgr.server_address[1])})
        log = open(os.path.join(self.state, "kernel-%d.log" % n), "w")
        proc = subprocess.Popen([sys.executable, "-c", _SUBPROCESS_KERNEL % {"tests": HERE, "bin": BIN, "setup": setup}],
                                env=env, stdout=subprocess.PIPE, stderr=log, text=True)
        self.addCleanup(lambda: (proc.poll() is None and proc.kill(), log.close()))
        first = proc.stdout.readline().strip()
        self.assertTrue(first, "the kernel did not come up; its stderr: %s" % open(log.name).read()[-2000:])
        port, pid = (int(x) for x in first.split())
        return proc, port, pid, log.name

    def test_twenty_kernels_signalled_before_the_answer_all_ack_the_restart(self):
        lost, exits = [], []
        for n in range(self.RUNS):
            proc, port, pid, logname = self._kernel(n)
            _SignallingManager.hits = []
            _SignallingManager.pid = pid
            req = urllib.request.Request("http://127.0.0.1:%d/restart" % port,
                                         data=json.dumps({"fleet": False}).encode(), method="POST",
                                         headers={"X-Romp-Token": km.TOKEN, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    ack = json.loads(r.read())
                if not (r.status == 200 and ack.get("restarting") is True):
                    lost.append((n, r.status, ack))
            except Exception as e:                      # the connection dropped: the kernel exited before its ack
                lost.append((n, type(e).__name__, str(e)[:120]))
            finally:
                _SignallingManager.pid = 0
            try:
                exits.append(proc.wait(timeout=15))
            except subprocess.TimeoutExpired:
                proc.kill()
                exits.append("hung")
            self.assertEqual([h[0] for h in _SignallingManager.hits], ["/restart-all"], "one hop per restart")
            self.assertEqual(_SignallingManager.hits[0][1], km.TOKEN, "with the token")
        self.assertEqual(lost, [], "the ack was lost on %d of %d runs (the kernel exited before writing it)" % (len(lost), self.RUNS))
        self.assertEqual(exits, [0] * self.RUNS, "every kernel left through _graceful_term's os._exit(0)")

    def _restart(self, port):
        req = urllib.request.Request("http://127.0.0.1:%d/restart" % port,
                                     data=json.dumps({"fleet": False}).encode(), method="POST",
                                     headers={"X-Romp-Token": km.TOKEN, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())

    def test_the_drained_arm_waits_for_the_ack_with_what_is_left_of_the_budget(self):
        # Review round 3 (2026-09-10): the twenty-kernel case above drives only the no-backend arm (the wait's
        # own two seconds). With an SDK backend drained, the wait is the budget minus the drain, and a build
        # that skipped it after a drain passed that case while losing every ack the manager answered after
        # the drain. Here the drain takes 0.8 s, the manager answers 1.3 s after its SIGTERM, inside the
        # two-second budget: the ack lands, and the kernel exits 0 once it has.
        proc, port, pid, logname = self._kernel(100, setup=_FAKE_BACKEND_SETUP % {"drain": "0.8"})
        _SignallingManager.hits = []
        _SignallingManager.pid = pid
        _SignallingManager.delay = 1.3
        try:
            status, ack = self._restart(port)
        finally:
            _SignallingManager.pid = 0
        self.assertEqual((status, ack.get("restarting")), (200, True), ack)
        self.assertEqual(proc.wait(timeout=15), 0)
        self.assertEqual([h[0] for h in _SignallingManager.hits], ["/restart-all"])
        self.assertNotIn("ack was still in flight", open(logname).read(), "the ack landed inside the budget")

    def test_an_ack_the_budget_runs_out_on_is_abandoned_at_the_bound_and_said_on_stderr(self):
        # Review round 3 (2026-09-10): a manager that answers past the bound is not waited for (the exit is
        # bounded, at 2.0 s from the SIGTERM with no backend to drain), and the kernel says on stderr that it
        # left with the ack in flight; it used to exit at the bound and write nothing about the ack it
        # abandoned. The connection drops when the kernel exits, so the drop's distance from the SIGTERM is
        # the bound's pin: no earlier than 1.8 s (the wait ran), and under 2.8 s (it is bounded).
        proc, port, pid, logname = self._kernel(101)
        _SignallingManager.hits = []
        _SignallingManager.pid = pid
        _SignallingManager.delay = 2.6
        try:
            with self.assertRaises(Exception):          # RemoteDisconnected or ConnectionResetError: the kernel is gone
                self._restart(port)
            dropped_at = time.monotonic()
        finally:
            _SignallingManager.pid = 0
        self.assertEqual(proc.wait(timeout=15), 0, "the exit is _graceful_term's os._exit(0)")
        since_kill = dropped_at - _SignallingManager.killed_at
        self.assertGreaterEqual(since_kill, 1.8, "the wait ran to its bound before the exit: %.2f s" % since_kill)
        self.assertLess(since_kill, 2.8, "and the bound held: %.2f s" % since_kill)
        self.assertIn("romp-kernel: a /restart ack was still in flight when the drain budget ran out; exiting without it",
                      open(logname).read())


class SelfUpdateScriptCarriesTheToken(unittest.TestCase):
    """The release self-update runs as a detached bash script handed over in argv, so the token is never
    written into it: the script reads it at run time (the env spelling, else the kernel's token file) and
    hands it to curl on stdin as a --config line."""

    def _script(self):
        calls = []
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: calls.append(a)), \
             mock.patch.object(km, "_release_remote", return_value="origin"), \
             mock.patch.dict(km.os.environ, {"ROMP_MANAGER_PORT": "7777"}):
            km._UPDATE_STATE[0] = ""
            self.assertTrue(km._run_update("v9.9.9"))
        km._UPDATE_STATE[0] = ""
        return calls[0][0][2]

    def test_the_token_is_read_at_run_time_and_never_written_into_the_script(self):
        script = self._script()
        self.assertNotIn(km.TOKEN, script, "the script is bash's argv for the update's whole run")
        self.assertIn("${ROMP_SERVE_TOKEN:-$(cat ", script)
        self.assertIn(str(km.jd.STATE / "serve-token"), script)
        self.assertIn("--config -", script)
        self.assertNotIn("-H ", script, "a -H puts the token in curl's argv")
        # the pinned request shape (tests/test_kernel_update.py) is unchanged
        self.assertIn("curl -fsS --max-time 60 -X POST 'http://127.0.0.1:7777/restart-all'", script)

    def _run_leg(self, script, env_token):
        leg = script[script.index("  printf '{\"t\""):script.index("\nelse\n")]   # the restart leg of the success branch
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "bin")
            os.makedirs(fake)
            args, stdin = os.path.join(tmp, "curl-args"), os.path.join(tmp, "curl-stdin")
            with open(os.path.join(fake, "curl"), "w") as f:
                f.write("#!/bin/sh\nprintf '%s ' \"$@\" > \"$T_ARGS\"\ncat > \"$T_STDIN\"\nexit 0\n")
            os.chmod(os.path.join(fake, "curl"), 0o755)
            env = {k: v for k, v in os.environ.items() if k != "ROMP_SERVE_TOKEN"}
            if env_token is not None:
                env["ROMP_SERVE_TOKEN"] = env_token
            env.update({"PATH": fake + os.pathsep + env.get("PATH", ""), "T_ARGS": args, "T_STDIN": stdin})
            r = subprocess.run(["bash", "-c", leg], env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(args) as a, open(stdin) as s:
                return a.read(), s.read()

    def test_the_restart_leg_hands_curl_the_header_on_stdin_from_the_token_file(self):
        script = self._script()
        tokf = km.jd.STATE / "serve-token"
        tokf.parent.mkdir(parents=True, exist_ok=True)
        tokf.write_text("file-token-for-tests\n")
        try:
            args, stdin = self._run_leg(script, env_token=None)
        finally:
            tokf.unlink()
        self.assertEqual(stdin, 'header = "X-Romp-Token: file-token-for-tests"\n')
        self.assertNotIn("file-token-for-tests", args, "never in argv")
        self.assertIn("--config -", args)
        self.assertIn("--max-time 60", args)

    def test_the_env_spelling_wins_and_is_escaped_for_curls_config_syntax(self):
        script = self._script()
        args, stdin = self._run_leg(script, env_token='env"tok\\en')
        self.assertEqual(stdin, 'header = "X-Romp-Token: env\\"tok\\\\en"\n')
        self.assertNotIn('env"tok', args, "never in argv")


if __name__ == "__main__":
    unittest.main()
