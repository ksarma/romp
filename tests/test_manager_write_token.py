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
import os
import subprocess
import tempfile
import threading
import time
import unittest
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
        self.wfile.write(b"{}")

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

    def test_a_refused_hop_is_reported_not_swallowed(self):
        _RecordingManager.answer = 401
        notices = []
        with mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
             mock.patch.object(km, "_checkout_sha", return_value="abcdef12"), \
             mock.patch.object(km, "_audit_restart_request", lambda *a, **k: None), \
             mock.patch.object(km, "_sync_notice", side_effect=lambda m, ok=True: notices.append((m, ok))):
            km._run_main_update("restart", immediate=True, manager_port=self.port)
        self.assertEqual(self._hits(), [("/restart-all", km.TOKEN)])
        self.assertTrue(any("HTTP 401" in m and not ok for m, ok in notices), notices)


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
