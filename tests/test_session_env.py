#!/usr/bin/env python3
"""Per-session env vars, spawn-time slice (the user 2026-08-17): two SDK sessions in the SAME
directory can run with different environments. Before this, env came only from directory-scoped
.claude/settings*.json — every session in the repo got it, and it outlived the session.

The mechanics under test:
  * `env_request_error` is the ONE validator both doors share (the /new handler mirrors it): a
    payload is a dict of NAME→string-value pairs, names matching [A-Za-z_][A-Za-z0-9_]*; anything
    else is named loudly, never skipped.
  * spawn() persists the dict in the session's reg (`env`) — the same home model/effort live in —
    and refuses a bad payload outright rather than writing a poisoned reg.
  * flag_settings_path folds a non-empty env into the per-sid settings payload beside ultracode /
    fastMode, and the return-""-when-no-keys contract stands.
  * _options threads the session's env into that file at EVERY connect — the file is rewritten on
    each use, so reconnects re-assert the reg's env by construction (pinned by tampering the file
    between two _options calls).
  * set_env mirrors set_effort's shape (persist + reconnect to apply; env is connect-time), minus
    the badge/chip machinery that belongs to the not-yet-built UI slice; an UNCHANGED re-assert
    (the `romp new --env` re-brief on a standing session, or the fresh-spawn echo) skips the
    reconnect — the asked-for env is already in force or already queued.
  * fork() inherits the parent's env like model/auth — it is that conversation, continued elsewhere.

Synthetic fixtures only: FEATURE_FLAG=1 shapes, placeholder sids — never credential-shaped values
(the gitleaks scanner reads this repo too).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = SourceFileLoader("romp_sdk_backend_env", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

PARENT = "11111111-2222-3333-4444-555555555555"
CHILD = "66666666-7777-8888-9999-aaaaaaaaaaaa"
ENV = {"FEATURE_FLAG": "1", "UI_THEME": "dark"}


class _Backend(unittest.TestCase):
    """Base: a backend on a temp state dir, no real CLI, no real key claim."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._stash_before = sb._WORK_KEY
        sb._WORK_KEY = ""                          # never claim a real key from this process's env
        self._fetch_before = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None  # the fast-org probe is a real HTTPS GET — never from a test
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        sb._WORK_KEY = self._stash_before
        sb._fetch_key_fast_org = self._fetch_before

    def _reg(self, sid):
        return sb.read_reg(self.be.state_dir, sid)

    def _sess(self, sid):
        return sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))


class EnvRequestError(unittest.TestCase):
    """The shared validator: loud and specific, never a silent skip."""

    def test_valid_payloads_pass(self):
        self.assertEqual(sb.env_request_error({"FEATURE_FLAG": "1"}), "")
        self.assertEqual(sb.env_request_error({"_UNDER": "x", "A9": ""}), "",
                         "an empty VALUE is meaningful — explicitly setting empty")
        self.assertEqual(sb.env_request_error({}), "", "an empty dict is a valid (vacuous) payload")

    def test_a_non_dict_is_named(self):
        for bad in ("FEATURE_FLAG=1", ["FEATURE_FLAG"], 7, None):
            err = sb.env_request_error(bad)
            self.assertIn("env", err)
            self.assertTrue(err, "a non-object payload must be refused, not coerced")

    def test_a_bad_name_is_named(self):
        for bad in ("9BAD", "", "BAD-NAME", "BAD NAME", "über"):
            err = sb.env_request_error({bad: "1"})
            self.assertIn("[A-Za-z_][A-Za-z0-9_]*", err,
                          "the error must teach the alphabet, not just refuse: %r" % bad)

    def test_a_non_string_value_is_named(self):
        for bad in (1, None, True, {"nested": "no"}):
            err = sb.env_request_error({"FEATURE_FLAG": bad})
            self.assertIn("FEATURE_FLAG", err,
                          "the offending NAME must be in the error (fail loudly): %r" % (bad,))


class FlagSettingsEnv(unittest.TestCase):
    """flag_settings_path folds env in beside ultracode/fastMode; the ""-when-empty contract stands."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _read(self, p):
        return json.loads(Path(p).read_text())

    def test_env_alone_writes_the_file(self):
        p = sb.flag_settings_path(self.d, PARENT, env=ENV)
        self.assertTrue(p)
        self.assertEqual(self._read(p), {"env": ENV})

    def test_env_rides_beside_the_boolean_keys(self):
        p = sb.flag_settings_path(self.d, PARENT, ultracode=True, fast=True, env=ENV)
        got = self._read(p)
        self.assertEqual(got["env"], ENV)
        self.assertTrue(got["ultracode"] and got["fastMode"],
                        "env must merge INTO the payload, not replace the keys already riding it")

    def test_no_keys_still_returns_empty(self):
        self.assertEqual(sb.flag_settings_path(self.d, PARENT), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=None), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env={}), "",
                         "an empty env adds no key — the no-keys contract is the common case")


class SpawnEnv(_Backend):
    def test_spawn_persists_the_env_in_the_reg(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertEqual(self._reg(sid).get("env"), ENV)

    def test_spawn_without_env_writes_no_key(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertNotIn("env", self._reg(sid))

    def test_spawn_refuses_a_bad_payload_loudly(self):
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"9BAD": "1"})
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"FEATURE_FLAG": 1})


class OptionsThreadsEnv(_Backend):
    """_options → flag_settings_path(env=…): the file the CLI launches with carries the reg's env."""

    def setUp(self):
        super().setUp()
        # ClaudeAgentOptions is a parameter (a dict stands in) and the in-function import only needs
        # HookMatcher — stub the module when the real dependency is absent (CI without the venv).
        import sys
        import types
        self._fake_sdk = "claude_agent_sdk" not in sys.modules and not sb.sdk_importable()
        if self._fake_sdk:
            fake = types.ModuleType("claude_agent_sdk")
            fake.HookMatcher = lambda **kw: kw
            sys.modules["claude_agent_sdk"] = fake

    def tearDown(self):
        import sys
        if self._fake_sdk:
            sys.modules.pop("claude_agent_sdk", None)
        super().tearDown()

    def _options_kw(self, sess):
        return self.be._options(sess, dict)

    def test_the_settings_file_carries_the_regs_env(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        kw = self._options_kw(self._sess(sid))
        self.assertIn("settings", kw)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV)

    def test_no_env_and_no_flags_means_no_settings_file(self):
        sid = self.be.spawn("web", "/tmp")
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw,
                         "the return-\"\"-when-no-keys contract: a plain session launches without "
                         "a flag-settings file at all")

    def test_every_connect_rewrites_the_file_so_reconnects_reassert(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)
        p = self._options_kw(s)["settings"]
        Path(p).write_text('{"env": {"TAMPERED": "yes"}}')   # drift the file behind romp's back
        p2 = self._options_kw(s)["settings"]
        self.assertEqual(p2, p)
        self.assertEqual(json.loads(Path(p2).read_text())["env"], ENV,
                         "the file is rewritten from the session on EVERY use — a reconnect "
                         "re-asserts the env by construction, never trusts what's on disk")


class SetEnv(_Backend):
    """set_env: set_effort's persist+reconnect shape, minus the UI slice's badge/chip machinery."""

    def _live(self, sid):
        s = self._sess(sid)
        s.request_reconnect = lambda: self.reconnects.append(1)
        self.reconnects = []
        self.be.sessions[sid] = s
        return s

    def test_a_change_persists_and_reconnects(self):
        sid = self.be.spawn("web", "/tmp")
        s = self._live(sid)
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV)
        self.assertEqual(s.env_vars, ENV)
        self.assertTrue(self.reconnects, "env is connect-time — the reconnect is what applies it")

    def test_an_unchanged_reassert_skips_the_reconnect(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, dict(ENV)))
        self.assertFalse(self.reconnects,
                         "same env = nothing to apply: the fresh-spawn echo and the nightly "
                         "re-brief must not churn the CLI process")

    def test_replace_not_merge(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, {"FEATURE_FLAG": "0"}))
        self.assertEqual(self._reg(sid)["env"], {"FEATURE_FLAG": "0"},
                         "the payload IS the session's per-session env — names not re-asserted drop")

    def test_refuses_junk_and_unknown_sids(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        self.assertEqual(self._reg(sid)["env"], ENV, "a refused payload must not half-apply")
        self.assertFalse(self.be.set_env(CHILD, ENV), "no reg, no session — refuse, don't mint")

    def test_a_dormant_session_persists_without_a_live_object(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV,
                         "the next connect reads the reg — persistence alone is a full apply "
                         "for a session with no live client")


class ForkInheritsEnv(_Backend):
    def test_a_fork_carries_the_parents_env(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV,
                             "it is that conversation, continued elsewhere — env inherits like "
                             "model/auth do")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_a_fork_of_an_env_less_parent_stays_env_less(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
        try:
            self.be.spawn("parent", self.d, sid=PARENT)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertNotIn("env", self._reg(CHILD))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)


class DrivePlumbing(unittest.TestCase):
    """The /new door rides the same park/drain path as the other per-session switches (source pins,
    the test_session_auth.DrivePlumbing pattern)."""

    def test_the_op_is_routed_parked_and_replayed(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("def _set_env_or_park(be, sid, value):", src)
        self.assertIn('_park_op(sid, ("env", value))', src)
        self.assertIn('elif op[0] == "env":', src)
        self.assertIn("be.set_env(sid, op[1])", src)
        self.assertIn('("model", "effort", "fast", "env")', src,
                       "a repeat env pick REPLACES the earlier parked one in place, like model/effort")

    def test_the_create_path_passes_env_through(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('def _create_sdk_session(nm, cwd, auth="", env=None):', src)


if __name__ == "__main__":
    unittest.main()
