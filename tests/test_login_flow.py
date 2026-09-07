#!/usr/bin/env python3
"""The in-dashboard LOGIN flow (T157, the user 2026-08-28: an expired login stalls everything when
they're on the phone over Tailscale — the dashboard becomes the login surface). The kernel drives
the CLI's PTY login: spawn → gates (trust dialog, method picker) → parse the code=true OAuth URL
out of its OSC-8 wrapping → stream to the dashboard → PASS the user's code straight to the PTY.
HOUSE RULE UNDER TEST: the code and tokens exist nowhere but the PTY write and the CLI's own
store — never logged, never in state files (the secrecy pin scans for the fake code after a full
flow). All against a MOCKED login PTY (never a real account); hermetic state; synthetic values."""
import hashlib
import json
import os
import stat
import tempfile
import time
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)

# the MOCK login CLI: reproduces the probed 2.1.221 transcript shape (trust gate → REPL hints →
# /login → method picker → OSC-8-wrapped code=true URL → paste prompt → verdict). It records a
# SHA-256 of the code it received (proof of arrival without the code existing anywhere readable).
_MOCK_DIR = tempfile.mkdtemp()
_MOCK = os.path.join(_MOCK_DIR, "claude")
_MARKER = os.path.join(_MOCK_DIR, "code-sha.txt")
with open(_MOCK, "w") as f:
    f.write('''#!/usr/bin/env python3
import sys, os, hashlib
def say(s):
    sys.stdout.write(s); sys.stdout.flush()
say("Do you trust this folder?\\n1. Yes, I trust this folder\\n")
line = sys.stdin.readline()
say("Welcome back! Tips for getting started\\n> Try \\"how do I log an error?\\"\\n")
line = sys.stdin.readline()          # /login
if "/login" not in line:
    say("Not logged in\\n"); sys.exit(1)
say("Select login method:\\n1. Claude account with subscription\\n2. Anthropic Console account\\n")
line = sys.stdin.readline()          # option 1
url = "https://claude.com/cai/oauth/authorize?code=true&client_id=x&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Foauth%2Fcode%2Fcallback&state=SYNTH"
say("Browser didn't open? Use the url below to sign in\\n")
say("\\x1b]8;id=1;" + url + "\\x1b\\\\\\\\" + url + "\\x1b]8;;\\x1b\\\\\\\\\\n")
say("Paste code here if prompted >\\n")
code = sys.stdin.readline().strip()
open(@@MARKER@@, "w").write(hashlib.sha256(code.encode()).hexdigest())
if code == "SYNTH-GOOD-CODE":
    say("Logged in as Test User (test@example.invalid)\\n")
else:
    say("Invalid code. Login error.\\n")
'''.replace("@@MARKER@@", repr(_MARKER)))
os.chmod(_MOCK, os.stat(_MOCK).st_mode | stat.S_IEXEC)
os.environ["ROMP_CLAUDE_BIN"] = _MOCK

load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_login", os.path.join(BIN, "romp-kernel"))
jd = km.jd


def _wait_state(want, seconds=15):
    t0 = time.time()
    while time.time() - t0 < seconds:
        st = km._login_state()
        if st["state"] == want:
            return st
        time.sleep(0.1)
    return km._login_state()


class LoginFlow(unittest.TestCase):
    def setUp(self):
        km._login_cancel()
        try:
            os.unlink(_MARKER)
        except OSError:
            pass

    def tearDown(self):
        km._login_cancel()

    def test_full_flow_url_code_done_and_the_secrecy_pin(self):
        self.assertEqual(km._login_start(), "")
        st = _wait_state("url")
        self.assertEqual(st["state"], "url", "the driver walked the gates to the URL: %r" % st)
        self.assertTrue(st["url"].startswith("https://claude.com/cai/oauth/authorize?code=true"),
                        "the code=true URL, parsed clean out of the OSC-8 wrapping: %r" % st["url"])
        self.assertNotIn("\x1b", st["url"], "no terminal escapes survive into the link")
        self.assertEqual(km._login_code("SYNTH-GOOD-CODE"), "")
        st = _wait_state("done")
        self.assertEqual(st["state"], "done", "success surfaces truthfully: %r" % st)
        self.assertEqual(open(_MARKER).read(),
                         hashlib.sha256(b"SYNTH-GOOD-CODE").hexdigest(),
                         "the code reached the PTY intact (proved by hash, never by value)")
        # THE SECRECY PIN: the code exists NOWHERE in romp's state or this kernel module's world
        for root, _, files in os.walk(str(jd.STATE)):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    body = open(p, "rb").read()
                except OSError:
                    continue
                self.assertNotIn(b"SYNTH-GOOD-CODE", body,
                                 "the code leaked into state file %s — the pass-through rule broke" % p)

    def test_a_bad_code_fails_loudly_and_honestly(self):
        self.assertEqual(km._login_start(), "")
        _wait_state("url")
        self.assertEqual(km._login_code("SYNTH-BAD-CODE"), "")
        st = _wait_state("error")
        self.assertEqual(st["state"], "error")
        self.assertIn("start", st["err"].lower(), "the copy names the retry, never the code: %r" % st["err"])
        self.assertNotIn("SYNTH-BAD-CODE", st["err"])

    def test_one_flow_at_a_time_and_cancel(self):
        self.assertEqual(km._login_start(), "")
        _wait_state("url")
        self.assertNotEqual(km._login_start(), "", "a second start refuses while one runs")
        km._login_cancel()
        self.assertEqual(km._login_state()["state"], "", "cancel clears the flow")
        self.assertEqual(km._login_start(), "", "…and a fresh start is allowed after")
        km._login_cancel()

    def test_code_without_a_flow_refuses(self):
        self.assertNotEqual(km._login_code("SYNTH-ORPHAN"), "")

    def test_stale_flow_self_reaps_via_state_read(self):
        self.assertEqual(km._login_start(), "")
        _wait_state("url")
        with km._login_lock:
            km._login_flow["t"] = time.time() - km.LOGIN_FLOW_TIMEOUT_S - 1
        st = km._login_state()
        self.assertEqual(st["state"], "error")
        self.assertIn("timed out", st["err"])

    def test_ops_payload_and_gear_wiring(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        for pin in ('msg.get("type") == "loginStart"', 'msg.get("type") == "loginCode"',
                    'msg.get("type") == "loginCancel"', '"login": _login_state(),',
                    '"acctLabel": _claude_account_label(),'):
            self.assertIn(pin, src)
        gear = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "gear.js")).read()
        for pin in ("loginStart", "loginCode", "rs-login-input", "rs-login-url", "v.acctLabel"):
            self.assertIn(pin, gear)
        feed = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "feed.ts")).read()
        self.assertIn('loginBtn.style.display = (showApiErr && authErr) ? "" : "none";', feed,
                      "the auth-expired card offers the fix, not just the problem")


if __name__ == "__main__":
    unittest.main()
