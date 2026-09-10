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
             mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True: notices.append((m, ok))):
            km._run_main_update("restart", immediate=True, manager_port=self.port)
            km._run_main_update("restart", immediate=False, manager_port=self.port)
        self.assertEqual(self._hits(2), [("/restart-all", km.TOKEN), ("/restart-all?when=quiet", km.TOKEN)])
        self.assertEqual([n for n in notices if not n[1]], [], "the manager took both: no failure notice")

    def test_a_refused_converge_hop_is_said_three_ways(self):
        # review round 1 (2026-09-10): the notice used to say only "the manager answered HTTP 401"; it now
        # says what the refusal means and the way out, and the stderr line and the audit row are new
        _RecordingManager.answer = 401
        self._clear_audit()
        notices, err = [], io.StringIO()
        with mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
             mock.patch.object(km, "_checkout_sha", return_value="abcdef12"), \
             mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True: notices.append((m, ok))), \
             contextlib.redirect_stderr(err):
            km._run_main_update("restart", immediate=True, manager_port=self.port)
        self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])
        said = [m for m, ok in notices if not ok]
        self.assertEqual(len(said), 1, notices)
        self.assertIn("romp is updated on disk but the restart request failed", said[0])
        self.assertIn("the manager refused it (HTTP 401)", said[0])
        self.assertIn("ROMP_SERVE_TOKEN", said[0], "names where this kernel's token came from (the env spelling here)")
        self.assertIn("romp refresh", said[0], "and the way out")
        self.assertLessEqual(len(said[0]), km.SYNC_NOTICE_FIT + 60, "close to the bell's cut; the point comes first")
        line = [l for l in err.getvalue().splitlines() if "refused POST /restart-all" in l]
        self.assertEqual(len(line), 1, err.getvalue())
        self.assertIn("HTTP 401", line[0])
        self.assertIn("serve token required", line[0], "the manager's own words ride along")
        self.assertIn(str(km.jd.STATE / "serve-token"), line[0])
        rows = [r for r in self._audit_rows() if r.get("action") == km._MANAGER_REFUSED_ACTION]
        self.assertEqual(len(rows), 1, self._audit_rows())
        self.assertEqual((rows[0]["status"], rows[0]["door"], rows[0]["reason"]), (401, "/restart-all", "main-converge: restart"))
        self.assertNotIn(km.TOKEN, err.getvalue() + json.dumps(rows) + said[0], "never the token itself")

    def test_a_refused_restart_this_kernel_is_said_three_ways_and_returned(self):
        # the /restart handler and the converge share this hop; its answer used to be discarded
        # (`c.getresponse(); c.close()` under `except Exception: pass`), so a 401 or 503 left no line, no
        # notice and no row (review round 1, 2026-09-10)
        for status, tell in ((401, "does not hold the serve token this kernel sent"), (503, "cannot read its own serve-token file")):
            with self.subTest(status=status):
                _RecordingManager.answer = status
                _RecordingManager.hits = []
                self._clear_audit()
                notices, err = [], io.StringIO()
                with mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True: notices.append((m, ok))), \
                     contextlib.redirect_stderr(err):
                    refused = km._restart_this_kernel("test restart", manager_port=self.port)
                self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])
                self.assertTrue(refused, "the refusal comes back to the caller")
                self.assertTrue(refused.startswith("The restart did not happen: "), refused)
                self.assertIn("HTTP %d" % status, refused)
                self.assertIn(tell, refused)
                self.assertIn("romp refresh", refused)
                self.assertEqual([m for m, ok in notices if not ok], [refused], "the same text reaches the bell")
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
        notices = []
        with mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True: notices.append((m, ok))), \
             contextlib.redirect_stderr(io.StringIO()):
            code, ack = self._post()
        self.assertEqual(code, 502, ack)
        self.assertEqual((ack["ok"], ack["restarting"], ack["fleet"]), (False, False, False))
        self.assertIn("HTTP 401", ack["error"])
        self.assertIn("romp refresh", ack["error"])
        self.assertEqual([m for m, ok in notices if not ok], [ack["error"]], "the same refusal reaches the bell")
        self.assertEqual(_RecordingManager.hits, [("/restart-all", km.TOKEN)], "the hop ran BEFORE the ack")
        _RecordingManager.answer = 200
        code, ack = self._post()
        self.assertEqual((code, ack["ok"], ack["restarting"], ack["fleet"]), (200, True, True, False))
        self.assertEqual(len(_RecordingManager.hits), 2)


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
