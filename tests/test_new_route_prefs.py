#!/usr/bin/env python3
"""POST /new's per-spawn model/effort (the user 2026-08-14): applied via the park-aware setters on
CREATE and on the idempotent existing:true open (a nightly re-brief re-asserts them), echoed in the
response so a caller can be loud when ignored; absent keys touch nothing.

Drives the REAL Handler over HTTP (the test_kernel_ws_auth.py pattern). Synthetic only — placeholder
UUIDs, temp dirs, no session state touched (the setters are recorded, never executed).
"""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "66666666-7777-8888-9999-000000000000"


class NewRoutePrefs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.calls = []
        self._saved = (km._live_names, km._tmux_sessions, km._set_model_or_park,
                       km._set_effort_or_park, km.Sessions.backend_for,
                       km._sdk_ready, km._create_sdk_session, km._push_soon)
        km._tmux_sessions = lambda: []
        km._set_model_or_park = lambda be, sid, v: self.calls.append(("model", sid, v))
        km._set_effort_or_park = lambda be, sid, v: self.calls.append(("effort", sid, v))
        km.Sessions.backend_for = staticmethod(lambda sid: object())
        km._push_soon = lambda: None

    def tearDown(self):
        (km._live_names, km._tmux_sessions, km._set_model_or_park,
         km._set_effort_or_park, km.Sessions.backend_for,
         km._sdk_ready, km._create_sdk_session, km._push_soon) = self._saved

    def _post(self, body):
        req = urllib.request.Request("http://127.0.0.1:%d/new" % self.port,
                                     data=json.dumps(body).encode(),
                                     headers={"X-Romp-Token": os.environ["ROMP_SERVE_TOKEN"],
                                              "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def test_existing_open_reasserts_model_and_effort_and_echoes_them(self):
        km._live_names = lambda *_: {"opt": SID}
        r = self._post({"name": "opt", "dir": self.dir,
                        "model": "claude-fable-5", "effort": "ultracode"})
        self.assertTrue(r["ok"])
        self.assertTrue(r["existing"])
        self.assertEqual(r.get("model"), "claude-fable-5")
        self.assertEqual(r.get("effort"), "ultracode")
        self.assertIn(("model", SID, "claude-fable-5"), self.calls)
        self.assertIn(("effort", SID, "ultracode"), self.calls)

    def test_existing_open_without_prefs_touches_nothing(self):
        km._live_names = lambda *_: {"opt": SID}
        r = self._post({"name": "opt", "dir": self.dir})
        self.assertTrue(r["ok"])
        self.assertNotIn("model", r)
        self.assertNotIn("effort", r)
        self.assertEqual(self.calls, [])

    def test_fresh_sdk_create_applies_both_and_echoes_them(self):
        km._live_names = lambda *_: {}
        km._sdk_ready = lambda: True
        km._create_sdk_session = lambda nm, cwd, auth="", env=None: SID2
        r = self._post({"name": "opt", "dir": self.dir,
                        "model": "claude-fable-5", "effort": "ultracode"})
        self.assertTrue(r["ok"])
        self.assertEqual(r.get("model"), "claude-fable-5")
        self.assertEqual(r.get("effort"), "ultracode")
        self.assertIn(("model", SID2, "claude-fable-5"), self.calls)
        self.assertIn(("effort", SID2, "ultracode"), self.calls)

    def test_model_alone_applies_and_echoes_only_model(self):
        km._live_names = lambda *_: {"opt": SID}
        r = self._post({"name": "opt", "dir": self.dir, "model": "claude-fable-5"})
        self.assertTrue(r["ok"])
        self.assertEqual(r.get("model"), "claude-fable-5")
        self.assertNotIn("effort", r)
        self.assertEqual(self.calls, [("model", SID, "claude-fable-5")])


class NewRouteEnv(unittest.TestCase):
    """POST /new's per-spawn "env" (the user 2026-08-17), the spawn-time slice: validated server-side
    (a bad name refuses the WHOLE request with a 400 — fail-loudly, never a silent skip), born into
    the SDK spawn so the eager connect already carries it, re-asserted through the park-aware
    set_env on the idempotent existing:true open, and echoed back like model/effort. SDK-only: the
    payload rides the per-sid flag-settings file, which a tmux session's CLI never reads — asked of
    a tmux session or the tmux backend, /new says so instead of pretending. Synthetic values only
    (FEATURE_FLAG=1 shapes, never anything credential-shaped — gitleaks reads this repo too)."""

    class _SdkBe:
        """A backend double WITH the set_env capability (the SDK shape)."""

        def set_env(self, sid, env):
            return True

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.calls = []
        self.created = []
        self.spawns = []
        self._saved = (km._live_names, km._tmux_sessions, km._set_env_or_park,
                       km.Sessions.backend_for, km._sdk_ready, km._create_sdk_session,
                       km._push_soon, km._spawn_session)
        km._tmux_sessions = lambda: []
        km._live_names = lambda *_: {}
        km._set_env_or_park = lambda be, sid, v: self.calls.append(("env", sid, v))
        km.Sessions.backend_for = staticmethod(lambda sid: self._SdkBe())
        km._sdk_ready = lambda: True
        km._create_sdk_session = (lambda nm, cwd, auth="", env=None:
                                  (self.created.append((nm, auth, env)), SID2)[1])
        km._push_soon = lambda: None
        km._spawn_session = lambda nm, cwd=None: self.spawns.append(nm)

    def tearDown(self):
        (km._live_names, km._tmux_sessions, km._set_env_or_park,
         km.Sessions.backend_for, km._sdk_ready, km._create_sdk_session,
         km._push_soon, km._spawn_session) = self._saved

    def _post(self, body):
        req = urllib.request.Request("http://127.0.0.1:%d/new" % self.port,
                                     data=json.dumps(body).encode(),
                                     headers={"X-Romp-Token": os.environ["ROMP_SERVE_TOKEN"],
                                              "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_a_bad_name_refuses_the_whole_request(self):
        for env in ({"9BAD": "1"}, {"BAD-NAME": "1"}, {"": "1"}):
            code, body = self._post({"name": "opt", "dir": self.dir, "env": env})
            self.assertEqual(code, 400, "bad env name %r must 400, not spawn" % env)
            self.assertFalse(body["ok"])
            self.assertIn("[A-Za-z_][A-Za-z0-9_]*", body["error"],
                          "the error teaches the alphabet, not just refuses")
        self.assertEqual(self.created, [], "nothing may be created on a refused request")
        self.assertEqual(self.calls, [])

    def test_a_non_object_or_non_string_value_refuses(self):
        code, body = self._post({"name": "opt", "dir": self.dir, "env": "FEATURE_FLAG=1"})
        self.assertEqual(code, 400)
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {"FEATURE_FLAG": 1}})
        self.assertEqual(code, 400)
        self.assertIn("FEATURE_FLAG", body["error"], "the offender is named — fail loudly")

    def test_falsy_junk_env_refuses_not_swallowed(self):
        # `or None` used to collapse ALL falsy values to "not asked": a script serializing env as
        # false/0/"" got an acked spawn silently missing its env — 0 skipped while 1 400'd
        for junk in (False, 0, "", []):
            code, body = self._post({"name": "opt", "dir": self.dir, "env": junk})
            self.assertEqual(code, 400, "falsy junk %r must 400, not spawn env-less" % (junk,))
            self.assertFalse(body["ok"])
            self.assertIn("env", body["error"], "the refusal names the offending key")
        self.assertEqual(self.created, [], "nothing may be created on a refused request")
        self.assertEqual(self.calls, [])

    def test_null_env_still_means_not_asked(self):
        code, body = self._post({"name": "opt", "dir": self.dir, "env": None})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(self.created, [("opt", "", None)], "null = absent, the don't-touch contract")
        self.assertNotIn("env", body)
        self.assertEqual(self.calls, [])

    def test_a_nul_byte_in_a_value_refuses(self):
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {"X": "a\x00b"}})
        self.assertEqual(code, 400, "a NUL value is unfulfillable by any process environment")
        self.assertFalse(body["ok"])
        self.assertIn("X", body["error"], "the offender is named — fail loudly")
        self.assertIn("NUL", body["error"])
        self.assertEqual(self.created, [])
        self.assertEqual(self.calls, [])

    def test_env_is_born_into_the_spawn_and_echoed(self):
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {"FEATURE_FLAG": "1"}})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(self.created, [("opt", "", {"FEATURE_FLAG": "1"})],
                         "the reg must be born with the env — BEFORE the eager connect, "
                         "not patched in behind it")
        self.assertEqual(body.get("env"), {"FEATURE_FLAG": "1"},
                         "the echo is the ack the CLI is loud about missing")
        self.assertIn(("env", SID2, {"FEATURE_FLAG": "1"}), self.calls,
                      "the prefs pass re-asserts (set_env's unchanged-skip makes it free)")

    def test_no_env_asked_none_threaded(self):
        code, body = self._post({"name": "opt", "dir": self.dir})
        self.assertEqual(code, 200)
        self.assertEqual(self.created, [("opt", "", None)])
        self.assertNotIn("env", body)
        self.assertEqual(self.calls, [], "nothing asked, nothing re-asserted")

    def test_existing_session_reasserts_through_set_env(self):
        km._live_names = lambda *_: {"opt": SID}
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {"FEATURE_FLAG": "1"}})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"] and body["existing"])
        self.assertEqual(self.calls, [("env", SID, {"FEATURE_FLAG": "1"})],
                         "re-asserted if <name> already runs — the model/effort contract")
        self.assertEqual(body.get("env"), {"FEATURE_FLAG": "1"})

    def test_an_explicit_empty_env_clears_a_running_session(self):
        # the clear-all door: {} is the replace-not-merge contract's limiting case (a re-run
        # declares the FULL env, and the empty declaration is "none") — before this, a spawn-time
        # debugging var could never be removed from a running session, only overwritten
        km._live_names = lambda *_: {"opt": SID}
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {}})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"] and body["existing"])
        self.assertEqual(self.calls, [("env", SID, {})],
                         "an explicit {} must reach set_env, which clears by replacing")
        self.assertEqual(body.get("env"), {}, "the clear ask is echoed like any other env ask")

    def test_an_explicit_empty_env_on_a_fresh_spawn_is_vacuous_but_echoed(self):
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {}})
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(self.created, [("opt", "", {})],
                         "spawn's own `if env:` makes the empty declaration naturally vacuous")
        self.assertEqual(body.get("env"), {})

    def test_an_existing_tmux_session_refuses_loudly(self):
        km._live_names = lambda *_: {"opt": SID}
        km.Sessions.backend_for = staticmethod(lambda sid: object())   # no set_env — the tmux shape
        code, body = self._post({"name": "opt", "dir": self.dir, "env": {"FEATURE_FLAG": "1"}})
        self.assertEqual(code, 200)
        self.assertFalse(body["ok"], "a session that can't take the env must say so, not drop it")
        self.assertIn("SDK", body["error"])

    def test_the_tmux_backend_refuses_env_outright(self):
        code, body = self._post({"name": "term1", "dir": self.dir,
                                 "backend": "tmux", "env": {"FEATURE_FLAG": "1"}})
        self.assertEqual(code, 200)
        self.assertFalse(body["ok"], "no tmux spawn, no env silently dropped")
        self.assertIn("SDK", body["error"])
        time.sleep(0.2)                       # the tmux spawn is threaded — give a regression a beat
        self.assertEqual(self.spawns, [], "the refusal must come BEFORE the spawn thread starts")


if __name__ == "__main__":
    unittest.main()
