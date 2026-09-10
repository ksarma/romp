#!/usr/bin/env python3
"""Every kernel-restart door writes WHO ASKED to restart-audit.jsonl (2026-07-31).

A run of anonymous SIGTERM respawns blinked every dashboard for an hour, and nothing on disk could
name the caller: the CLI path (bin/romp) audits itself, but the HTTP /restart route and the
kernel→manager hop were silent. Now the route records the requester (address/origin/user-agent) and
_restart_this_kernel records its reason, in the SAME file, so one log answers "who restarted the
kernel?" whatever door the request came through.

Synthetic only: the real Handler on an ephemeral port, no manager (ROMP_MANAGER_PORT unset → the
restart itself is a no-op), invented tokens.
"""
import json
import os
import re
import time
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
os.environ["ROMP_MANAGER_PORT"] = "1"   # dead port → _restart_this_kernel audits, then its dial is
#   refused (its except: pass). NEVER pop: pytest imports this module at COLLECTION, so a pop here
#   would erase conftest's suite-wide floor before any test runs — and an ABSENT var is the one
#   unsafe state (_run_main_update maps absent to the DEFAULT port: the live manager).
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
KERNEL_SRC = open(os.path.join(os.path.dirname(BIN), "kernel", "kernel.py")).read()

def _audit_path():
    return jd.STATE / "restart-audit.jsonl"   # at CALL time — peer test modules rebind jd.STATE


def _read_audit():
    try:
        return [json.loads(x) for x in _audit_path().read_text().splitlines() if x.strip()]
    except OSError:
        return []


class RestartAudit(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        try:
            _audit_path().unlink()
        except OSError:
            pass

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def test_http_restart_route_records_the_requester(self):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/restart" % self.port,
            data=json.dumps({"fleet": False}).encode(),
            headers={"X-Romp-Token": km.TOKEN, "Origin": "http://127.0.0.1:9",
                     "User-Agent": "test-agent/1.0", "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
        self.assertTrue(body.get("restarting"))
        # the route ACKS FIRST and audits the manager hop after — poll briefly so the assertion
        # doesn't race the handler thread (CI hit this; the ack/restart order is the designed one)
        recs = []
        for _ in range(200):
            recs = _read_audit()
            if any(r.get("action") == "kernel-asks-manager-restart-all" for r in recs):
                break
            time.sleep(0.01)
        route = [r for r in recs if r.get("action") == "http-restart"]
        self.assertEqual(len(route), 1, "the HTTP door must write exactly one audit line: %r" % recs)
        self.assertEqual(route[0].get("addr"), "127.0.0.1")
        self.assertEqual(route[0].get("origin"), "http://127.0.0.1:9")
        self.assertEqual(route[0].get("ua"), "test-agent/1.0")
        self.assertNotIn("fleet", route[0], "fleet:false is omitted (falsy fields are dropped)")
        # the manager hop audits its reason too — the two lines together tell the order of events
        hop = [r for r in recs if r.get("action") == "kernel-asks-manager-restart-all"]
        self.assertEqual(len(hop), 1, "the kernel→manager hop must record its reason: %r" % recs)
        self.assertIn("http /restart", hop[0].get("reason") or "")

    def test_restart_this_kernel_audits_even_with_no_manager(self):
        km._restart_this_kernel("unit-test reason")
        recs = _read_audit()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["action"], "kernel-asks-manager-restart-all")
        self.assertEqual(recs[0]["reason"], "unit-test reason")
        self.assertEqual(recs[0]["pid"], os.getpid())


class ARefusalConsumesItsRequest(unittest.TestCase):
    """The manager answered a hop 4xx or 5xx (review round 2, 2026-09-10). The request row written before
    the hop (http-restart and kernel-asks-manager-restart-all for the dashboard's Restart, main-converge for
    the converge) stayed live for the 90 s window: the refusal row was walked past, but it did not
    supersede the request beneath it, so a later SIGTERM from another source was attributed to a request
    the manager had refused. The walk now lets a refusal consume the one request it was written for,
    keyed on action and timestamp (two of the three request rows carry no reason), and no more."""
    T = 1_800_000_000

    def setUp(self):
        try:
            _audit_path().unlink()
        except OSError:
            pass

    def _write(self, rows):
        _audit_path().parent.mkdir(parents=True, exist_ok=True)
        with open(_audit_path(), "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    def _http_restart_refused(self, t):
        return [{"t": t, "action": "http-restart", "addr": "127.0.0.1", "ua": "test-agent/1.0"},
                {"t": t, "action": "kernel-asks-manager-restart-all", "reason": "http /restart (local-only)", "pid": os.getpid()},
                {"t": t, "action": km._MANAGER_REFUSED_ACTION, "door": "/restart-all", "status": 401,
                 "reason": "http /restart (local-only)", "tokenSrc": "ROMP_SERVE_TOKEN"}]

    def test_the_three_row_ledger_of_a_refused_dashboard_restart_names_no_request(self):
        self._write(self._http_restart_refused(self.T - 1))
        self.assertIsNone(km._recent_restart_audit(now=self.T, started=self.T - 1000),
                          "the request the manager refused restarted nothing, so a signal now is anonymous")

    def test_a_refused_converge_row_names_no_request(self):
        self._write([{"t": self.T - 2, "action": "main-converge", "tag": "pull", "when": "now", "sha": "abcdef12"},
                     {"t": self.T - 1, "action": km._MANAGER_REFUSED_ACTION, "door": "/restart-all", "status": 503,
                      "reason": "main-converge: pull"}])
        self.assertIsNone(km._recent_restart_audit(now=self.T, started=self.T - 1000))

    def test_a_parked_quiet_converge_under_an_unrelated_refusal_stays_visible(self):
        parked = {"t": self.T - 100, "action": "main-converge", "tag": "pull", "when": "quiet", "sha": "abcdef12"}
        self._write([parked] + self._http_restart_refused(self.T - 1))
        self.assertEqual(km._recent_restart_audit(now=self.T, started=self.T - 1000), parked,
                         "one request per refusal: the older parked request beneath was not the one refused")

    def test_a_managers_note_above_a_refused_request_still_answers(self):
        note = {"t": self.T, "action": "manager-sigterm", "trigger": "restart-all", "pid": os.getpid()}
        self._write(self._http_restart_refused(self.T - 1) + [note])
        self.assertEqual(km._recent_restart_audit(now=self.T, started=self.T - 1000), note)

    def test_two_refusals_consume_two_requests_and_a_third_request_stays(self):
        first = {"t": self.T - 30, "action": "kernel-asks-manager-restart-all", "reason": "self-update", "pid": os.getpid()}
        self._write([first] + self._http_restart_refused(self.T - 20) + self._http_restart_refused(self.T - 1))
        self.assertEqual(km._recent_restart_audit(now=self.T, started=self.T - 1000), first)

    # The far-host apply script's REFUSED branch (review round 3, 2026-09-10): on a peer the apply writes a
    # p2p-update row, hops to that host's manager through the control client, and on the client's exit 3
    # writes a manager-refused-restart-all row over it. The p2p-update action was not among the request
    # rows a refusal consumes, so the far kernel kept the refused request as the live one for the 90 s
    # window, and a SIGTERM from another source there was attributed to a deploy the manager refused.
    def _far_host_refused(self, t):
        return [{"t": t, "action": "p2p-update", "reason": "from abcdef12 to 12abcdef"},
                {"t": t, "action": km._MANAGER_REFUSED_ACTION, "door": "/restart-all", "status": 401,
                 "reason": "p2p-update from abcdef12 to 12abcdef"}]

    def test_a_refused_far_host_apply_names_no_request(self):
        self._write(self._far_host_refused(self.T - 1))
        self.assertIsNone(km._recent_restart_audit(now=self.T, started=self.T - 1000),
                          "the manager on this host refused the deploy's hop: a signal now is anonymous")

    def test_a_parked_quiet_converge_under_a_refused_far_host_apply_stays_visible(self):
        parked = {"t": self.T - 100, "action": "main-converge", "tag": "pull", "when": "quiet", "sha": "abcdef12"}
        self._write([parked] + self._far_host_refused(self.T - 1))
        self.assertEqual(km._recent_restart_audit(now=self.T, started=self.T - 1000), parked)

    def test_a_managers_note_above_a_refused_far_host_apply_still_answers(self):
        note = {"t": self.T, "action": "manager-sigterm", "trigger": "restart-all", "pid": os.getpid()}
        self._write(self._far_host_refused(self.T - 1) + [note])
        self.assertEqual(km._recent_restart_audit(now=self.T, started=self.T - 1000), note)


if __name__ == "__main__":
    unittest.main()
