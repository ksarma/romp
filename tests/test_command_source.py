#!/usr/bin/env python3
"""The command kind at the launch seam: sessions, judges and the catalog take the set a configured
credential command prints (kernel/envsource.py), selected by keysource like the reference.

What these pin, in the order a launch meets them:
  CommandSourceLaunch: the set rides every launch and ANTHROPIC_API_KEY only where the session's auth
    says so; a key pick with no key in the set launches without one, loudly, and never with an empty
    variable; one run serves a burst of connects; a connect stamps the credential and the role
    fingerprints; the selector file is the command's $1; the set's ROMP_* names are dropped and said
    once; romp's own entries ride over the set; the reserved per-session names follow the launch
    decision.
  CommandBeatsFileAndStartup: with the command line in service.env a key line in the same file and the
    startup ANTHROPIC_API_KEY are ignored; the startup claim is still popped; the environment door
    selects the command for a foreground manager.
  CommandSourceFailure: a failed run keeps the previous set with one problem line per failure kind;
    a command that never succeeded launches with nothing injected and is never a refusal; a 401 on a
    turn, a launch refused as unauthenticated and the judges' wire invalidate the set once per
    credential; a completed turn on the refused credential re-arms the path; a refusal on a session
    still on the pre-rotation key runs nothing; a connect on a failing command runs it once.
  ModuleReaders: keysource.COMMAND_RESOLVER is wired at import; credential_set, credential_invalidate
    and credential_auth_ok are the seams the judges and the catalog wire to, and no-ops outside the
    command kind.
  JudgesDefaultBilling: the judges' default-billing answer the kernel wires (judge._WORK_KEY_CONFIGURED_FN)
    follows the launch decision under the command kind: a set with a key bills an unpicked session's
    judges on it, a set without one bills them on the login the session launched on, never a refusal;
    the reference, the file kind and a removed source answer from the descriptor without resolving.
  ByteIdenticalOutsideTheCommandKind: with no command selected the file-mode launch is the base's
    (the key injected for a keyed launch, the login environment for a login launch, the command
    source never run, nothing about a credential command in the log).
  NothingLeaks: no fixture value reaches a log line, the problem ring or a record, and os.environ is
    unchanged after every reader.
  HelperSessionsConverge: cycle_key under the command kind compares each live session's connect stamps
    with the credential and role fingerprints a launch would get now: a keyed session on the set's key, a
    helper-billed session (its CLI reported the key while the kernel injected none) on the apiKeyHelper
    output's fingerprint, every session on the role variables; equal reads "current", a difference
    reconnects once, a repeated --cycle-all converges; a helper the kernel cannot fingerprint reconnects
    on every run with the reason; in-flight work still skips; a probe classifies without reconnecting;
    the file kind's compare is the base's.
  KeycycleRouteOnTheCommandKind: POST /keycycle with a real backend under the command kind answers with
    the set's credential fingerprint as keyFp, the source fingerprint as sourceFp, the key-source fields,
    a "refresh" that re-runs the command first, and rows from cycle_key on the cached set.

Synthetic throughout: every value is "romp-test-fixture-" + a uuid assembled at run time, the fake
command is a script in a temp dir, a temp CLAUDE_CONFIG_DIR carries no apiKeyHelper unless a test
writes one, and the env file is a temp file the module points keysource at. conftest pops the three
command variables and floors the selector file per test; the classes below set what they need in
setUp and restore the world after.
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
import uuid
from importlib.machinery import SourceFileLoader
from types import SimpleNamespace
from unittest.mock import patch

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads (they resolve their state root at import time), and a service.env
# path that does not exist, so a bare non-pytest run of this file cannot read the real one either.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ.pop("ROMP_SUPERVISED", None)  # a romp-managed shell inherits it; the file door is the same either way
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_cmdsrc", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
# bin/romp-kernel at IMPORT, like every other kernel-loading test module. Its load re-executes judge.py into
# the one romp_judge module object every module shares (SourceFileLoader.load_module), re-binding
# romp_judge.STATE and GOALDIR. At collection that is harmless: the last loader wins before any test runs. A
# run-time load from a setUpClass re-binds them mid-suite, and a later module's override journal then lands
# under the state root another module minted its goals in (7 deterministic CI failures in the deferral sweep).
# KeycycleRouteOnTheCommandKind takes this one.
_KM_CMDSRC = SourceFileLoader("romp_kernel_cmdsrc", os.path.join(BIN, "romp-kernel")).load_module()
ks = sb._keysrc
# The command source module the backend holds; loaded here only while the backend does not hold one
# (the red run), so the tests fail on behaviour rather than at collection.
es = getattr(sb, "_envsrc", None) or (
    __import__("sys").modules.get("romp_envsource")
    or SourceFileLoader("romp_envsource", os.path.join(ROOT, "kernel", "envsource.py")).load_module())


def fixture_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


OLD_KEY = "sk-ant-TEST-0000"
BOOT_KEY = "sk-ant-TEST-BOOT"
SAVED_VARS = ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ANTHROPIC_API_KEY", "ROMP_API_KEY_REF",
              "ROMP_CREDENTIAL_COMMAND", "ROMP_CREDENTIAL_NAMES", "ROMP_CREDENTIAL_TIMEOUT_S",
              "ROMP_CREDENTIAL_SELECTOR_FILE", "CLAUDE_CONFIG_DIR", "ROMP_EXPECTED_AUTH", "ROMP_SUPERVISED")


def _count(marker):
    """How many times a fixture script appended a line to `marker` (0 for a file no run created)."""
    try:
        with open(marker) as fh:
            return sum(1 for _ in fh)
    except FileNotFoundError:
        return 0


def _result(status):
    """A ResultMessage stand-in on the parent stream: an error carrying `status`, or a completed turn."""
    return SimpleNamespace(is_error=status is not None, api_error_status=status, parent_tool_use_id=None)


class _Lab(unittest.TestCase):
    """A backend whose env file selects the COMMAND kind through the file door: a fake command printing a
    synthetic set (no ANTHROPIC_API_KEY unless a test adds one), a temp CLAUDE_CONFIG_DIR with no
    apiKeyHelper, a selector file path in the lab, and no key line in the file. The startup stash and
    the once-per-process notices are module-global, so each test re-arms them and restores after."""

    BOOT = ""          # what the process environment carried at "startup"
    KEY_LINE = None    # an ANTHROPIC_API_KEY line to write beside the command line (the precedence case)

    def setUp(self):
        self.lab = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.lab, ignore_errors=True)
        self.path = os.path.join(self.lab, "service.env")
        self.state = os.path.join(self.lab, "state")
        os.makedirs(self.state)
        self._before = {v: os.environ.get(v) for v in SAVED_VARS}
        for v in SAVED_VARS:
            os.environ.pop(v, None)
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.lab, "selector")
        self.values = {"ANTHROPIC_LP_API_KEY": fixture_value("lp"), "A_TOKEN": fixture_value("role")}
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.print_set(self.values)
        self._saved = (sb._WORK_KEY, sb._KEY_FILE_CHECKED, sb._FILE_KEY_SEEN_FP, sb._STARTUP_KEY_DISCARD_SAID,
                       sb._fetch_key_fast_org, ks.COMMAND_RESOLVER)
        sb._WORK_KEY = self.BOOT              # the startup claim, already made
        sb._KEY_FILE_CHECKED = True           # the one-shot agreement line is asserted on its own
        sb._FILE_KEY_SEEN_FP = ""
        sb._STARTUP_KEY_DISCARD_SAID = False  # the startup-key notice is armed per test
        sb._fetch_key_fast_org = lambda key: None      # never a real HTTPS GET from a test
        sb._FAST_ORG_VERDICTS.clear()
        self.reset_sources()
        self.logged = []
        self.write_command_env(key=self.KEY_LINE)
        self.before_construct()
        self.be = self.construct()
        import sys
        import types
        self._fake_sdk = "claude_agent_sdk" not in sys.modules and not sb.sdk_importable()
        if self._fake_sdk:                    # _options' in-function import (CI without the venv)
            fake = types.ModuleType("claude_agent_sdk")
            fake.HookMatcher = lambda **kw: kw
            sys.modules["claude_agent_sdk"] = fake

    def tearDown(self):
        import sys
        if self._fake_sdk:
            sys.modules.pop("claude_agent_sdk", None)
        (sb._WORK_KEY, sb._KEY_FILE_CHECKED, sb._FILE_KEY_SEEN_FP, sb._STARTUP_KEY_DISCARD_SAID,
         sb._fetch_key_fast_org, ks.COMMAND_RESOLVER) = self._saved
        sb._FAST_ORG_VERDICTS.clear()
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        self.reset_sources()

    @staticmethod
    def reset_sources():
        ks._CACHE = ((), "")                  # the stat-identity cache and the selection memory are module-global
        ks._AUTHORITATIVE_PATHS.clear()
        ks._ENV_PROVIDER_PATHS.clear()
        es._reset()

    def before_construct(self):
        """A hook a class fills to shape the lab before the backend is constructed (a helper the boot
        should see, a set the first run should print); the base does nothing here."""

    def construct(self):
        # NB `log=` is a keyword: the third positional is `notify`. A line reaches self.logged only
        # through the log wire, which is what the no-leak tests below read.
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def write_command_env(self, key=None, command=True, lines=None):
        """The env file: ROMP_PERF=1, the command line (unless `command` is False), and a key line when
        `key` is given (None writes none; "" writes an empty one)."""
        body = list(lines if lines is not None else ["# romp service environment", "ROMP_PERF=1"])
        if command:
            body.append("%s=%s \"$1\"" % (ks.CMD_VAR, self.cmd))
        if key is not None:
            body.append("%s=%s" % (ks.KEY_VAR, key))
        with open(self.path, "w") as fh:
            fh.write("\n".join(body) + "\n")
        os.chmod(self.path, 0o600)
        ks._CACHE = ((), "")                  # a same-second rewrite in a test can reuse the stat identity

    def print_set(self, values, extra=""):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + (extra + "\n" if extra else "")
                     + "".join("echo '%s=%s'\n" % kv for kv in values.items()))
        os.chmod(self.cmd, 0o700)

    def fail_command(self, body="exit 3"):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + body + "\n")
        os.chmod(self.cmd, 0o700)

    def rerun(self):
        """An operator's invalidation: the next reader runs the command again (the refresh of a later
        stage; here the module's own event)."""
        es.invalidate("test")

    def problems(self):
        return [p["text"] for p in self.be.problems()]

    def source(self):
        return ks.select_source()

    def _sess(self, n=1, **reg):
        return sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n,
                                       "name": "s%d" % n, "cwd": self.lab, **reg})

    def _live(self, auth_live="", auth="", n=1):
        """A LIVE session object the backend owns (a registry entry, no CLI: cycle_key answers "unknown"
        for a sid it does not own), its CLI's billing report set to `auth_live`, its reconnects recorded
        on self.reconnects and self.defers."""
        reg = {"auth": auth} if auth else {}
        s = self._sess(n, **reg)
        sb.write_reg(self.be.state_dir, s.sid, {"sid": s.sid, "name": s.name, "cwd": self.lab, **reg})
        s.auth_live = auth_live
        if not hasattr(self, "reconnects"):
            self.reconnects, self.defers = [], []
        s.request_reconnect = lambda defer=True: (self.reconnects.append(s.sid), self.defers.append(defer))
        self.be.sessions[s.sid] = s
        return s

    def connect(self, s):
        """What a connect does for the stamps: _options on the live session object."""
        return self.be._options(s, dict)

    def _env_for(self, n, auth, **reg):
        if auth:
            reg["auth"] = auth
        return self.be._options(self._sess(n, **reg), dict)["env"]

    def helper(self, body):
        """A fake apiKeyHelper in the lab's CLAUDE_CONFIG_DIR: a settings.json naming a script."""
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        h = os.path.join(self.lab, "helper.sh")
        with open(h, "w") as fh:
            fh.write("#!/bin/sh\n" + body + "\n")
        os.chmod(h, 0o700)
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": h}, fh)
        return h


class CommandSourceLaunch(_Lab):
    def test_the_backend_holds_the_command_source_module_the_tests_read(self):
        self.assertIs(getattr(sb, "_envsrc", None), es, "sdk_backend loads kernel/envsource.py as romp_envsource")
        self.assertEqual(self.source().kind, "command")

    def test_the_set_rides_every_launch_and_the_key_only_where_the_auth_says_so(self):
        env = self._env_for(1, "login")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"])
        self.assertEqual(env["ANTHROPIC_LP_API_KEY"], self.values["ANTHROPIC_LP_API_KEY"])
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertEqual(env["ROMP_SID"], "11111111-2222-3333-4444-000000000001", "romp's own entries ride over the set")
        # the set gains a key: an unpicked session is keyed, a login pick is not
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(self.be.work_key, k)
        self.assertEqual(self._env_for(2, "").get("ANTHROPIC_API_KEY"), k)
        self.assertEqual(self._env_for(3, "key").get("ANTHROPIC_API_KEY"), k)
        env = self._env_for(4, "login")
        self.assertFalse("ANTHROPIC_API_KEY" in env, "removal, never blanking")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"], "the role variables still ride a login launch")
        s = self._sess(5, auth="key")
        self.be._options(s, dict)
        self.assertTrue(s._launched_keyed)
        s = self._sess(6, auth="login")
        self.be._options(s, dict)
        self.assertFalse(s._launched_keyed)

    def test_a_key_pick_with_no_key_in_the_set_launches_without_one_loudly(self):
        env = self._env_for(1, "key")
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present: never an empty variable")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"])
        lines = [t for t in self.problems() if "credential command printed no ANTHROPIC_API_KEY" in t]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("s1", lines[0])
        self.assertIn("the apiKeyHelper or the login bills", lines[0])
        # an unpicked session under a keyless set is not a key pick: launched, and nothing said
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(2, ""), "ANTHROPIC_API_KEY present")
        self.assertEqual(len([t for t in self.problems() if "printed no ANTHROPIC_API_KEY" in t]), 1)

    def test_a_key_pick_with_no_key_in_the_set_still_gets_the_startup_login_tokens(self):
        # the launch above bills the apiKeyHelper or the login. On a box whose login lives in the tokens
        # the backend claimed at boot (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_AUTH_TOKEN) that CLI answered
        # "Not logged in" while the log said the login bills, because only the login branch restored
        # them (review find, 2026-09-07): every launch that injects no key restores them.
        tok = fixture_value("oauth")
        saved = sb._STARTUP_AUTH_ENV
        sb._STARTUP_AUTH_ENV = {"CLAUDE_CODE_OAUTH_TOKEN": tok}
        try:
            env = self._env_for(1, "key")
            self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
            self.assertEqual(env.get("CLAUDE_CODE_OAUTH_TOKEN"), tok, "the startup login tokens ride a keyless key pick")
            self.assertEqual(self._env_for(2, "login").get("CLAUDE_CODE_OAUTH_TOKEN"), tok, "as they ride a login pick")
            self.assertEqual(self._env_for(3, "").get("CLAUDE_CODE_OAUTH_TOKEN"), tok, "and an unpicked session")
            k = fixture_value("key")
            self.values["ANTHROPIC_API_KEY"] = k
            self.print_set(self.values)
            self.rerun()
            env = self._env_for(4, "key")
            self.assertEqual(env.get("ANTHROPIC_API_KEY"), k)
            self.assertFalse("CLAUDE_CODE_OAUTH_TOKEN" in env, "a keyed launch never carries a competing login token")
        finally:
            sb._STARTUP_AUTH_ENV = saved

    def test_one_run_serves_a_burst_of_connects(self):
        self._env_for(1, "login")
        runs = es._runs
        self.assertGreaterEqual(runs, 1)
        for n in range(2, 8):
            self._env_for(n, "login")
            self._env_for(n + 10, "key")
        self.assertEqual(es._runs, runs, "event-keyed: a burst of connects runs the command once")

    def test_a_connect_stamps_the_credential_and_the_role_variables(self):
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        self.assertEqual(s._launched_key_fp, "", "no key injected, no helper configured: nothing to fingerprint")
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values))
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s2 = self._sess(2, auth="key")
        self.be._options(s2, dict)
        self.assertEqual(s2._launched_key_fp, es.fingerprint(k))
        role = dict(self.values)
        role.pop("ANTHROPIC_API_KEY")
        self.assertEqual(s2._launched_set_fp, es.set_fingerprint(role), "the key is not part of the role stamp")
        # a helper-billed launch (nothing injected, a helper configured) is stamped with the helper's output
        h = fixture_value("helper")
        self.helper("echo '%s'" % h)
        s3 = self._sess(3, auth="login")
        self.be._options(s3, dict)
        self.assertEqual(s3._launched_key_fp, es.fingerprint(h))
        self.assertFalse(any(h in m for m in self.logged), "the helper's output is hashed inside envsource")

    def test_the_selector_file_is_the_commands_dollar_one(self):
        with open(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], "w") as fh:
            fh.write("hp\n")
        self.print_set(self.values, extra='echo "PICKED=$1"')
        self.rerun()
        self.assertEqual(self._env_for(1, "login")["PICKED"], "hp")

    def test_dropped_romp_names_are_a_problem_line_by_name_once(self):
        self.print_set({"ROMP_SID": "forged", "A_TOKEN": self.values["A_TOKEN"]})
        self.rerun()
        env = self._env_for(1, "login")
        self.assertEqual(env["ROMP_SID"], "11111111-2222-3333-4444-000000000001",
                         "romp's identity entry, never the command's")
        lines = [t for t in self.problems() if "dropped 1 ROMP_* variable" in t]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("(ROMP_SID)", lines[0])
        self.assertNotIn("forged", lines[0])
        self._env_for(2, "login")
        self.assertEqual(len([t for t in self.problems() if "dropped 1 ROMP_* variable" in t]), 1, "said once per list")

    def test_the_clis_auth_names_are_dropped_with_one_problem_line(self):
        v = fixture_value("auth")
        self.values["ANTHROPIC_AUTH_TOKEN"] = v
        self.values["ANTHROPIC_BASE_URL"] = "https://example.invalid"
        self.print_set(self.values)
        self.rerun()
        env = self._env_for(1, "login")
        self.assertFalse("ANTHROPIC_AUTH_TOKEN" in env, "ANTHROPIC_AUTH_TOKEN present")
        self.assertFalse("ANTHROPIC_BASE_URL" in env, "ANTHROPIC_BASE_URL present")
        self.assertTrue("A_TOKEN" in env, "A_TOKEN absent")
        lines = [t for t in self.problems() if "authentication or endpoint" in t]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("dropped ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL it printed", lines[0])
        self.assertNotIn(v, lines[0])
        self._env_for(2, "login")
        self.assertEqual(len([t for t in self.problems() if "authentication or endpoint" in t]), 1, "said once per distinct list")

    def test_the_set_line_is_change_only(self):
        # the boot verdict is the report of the first set (one "key source: command" line: the set's fingerprint
        # and names); the noter's own line is for a CHANGE, and the first connect on the same set says nothing
        boot = [m for m in self.logged if m.startswith("key source: command")]
        self.assertEqual(len(boot), 1, self.logged)
        self.assertIn("sha256:" + es.set_fingerprint(self.values), boot[0])
        self.assertIn("2 names: ANTHROPIC_LP_API_KEY, A_TOKEN", boot[0])
        self.assertIn("no ANTHROPIC_API_KEY in it", boot[0])
        self._env_for(1, "login")
        for _ in range(3):
            self._env_for(2, "login")
        self.rerun()
        self._env_for(3, "login")
        self.assertEqual([m for m in self.logged if "sessions now launch with the set" in m], [],
                         "the same set again is not said")
        self.values["A_TOKEN"] = fixture_value("rotated")
        self.print_set(self.values)
        self.rerun()
        self._env_for(4, "login")
        said = [m for m in self.logged if "sessions now launch with the set" in m]
        self.assertEqual(len(said), 1, "a changed set is")
        self.assertIn("sha256:" + es.set_fingerprint(self.values), said[0])
        for v in self.values.values():
            self.assertFalse(any(v in m for m in self.logged), "a value in a log line")

    def test_the_reserved_per_session_names_follow_the_launch_decision(self):
        # under runtime retrieval a stored per-session ANTHROPIC_API_KEY always competes with the
        # source; the tokens compete only when the launch is keyed, and under the command kind that is
        # decided after the set is taken: a key pick with no key in the set injects nothing and reserves
        # the key name only
        stored = {"ANTHROPIC_API_KEY": "romp-test-stored-key", "ANTHROPIC_AUTH_TOKEN": "romp-test-stored-token"}
        self._env_for(1, "key", env=dict(stored))
        said = [m for m in self.logged if m.startswith("env (s1): ignoring reserved")]
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("ANTHROPIC_API_KEY", said[0])
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", said[0], "a launch with nothing injected keeps a login token override")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        self.rerun()
        self._env_for(2, "key", env=dict(stored))
        said = [m for m in self.logged if m.startswith("env (s2): ignoring reserved")]
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("ANTHROPIC_AUTH_TOKEN", said[0], "a keyed launch carries no token beside the key it injects")


class CommandBeatsFileAndStartup(_Lab):
    """The command line outranks the same file's key line (keysource: command > op > file), and the
    startup ANTHROPIC_API_KEY is retired as for any selected source."""

    BOOT = BOOT_KEY
    KEY_LINE = OLD_KEY

    def test_a_file_key_line_and_the_startup_claim_are_ignored(self):
        self.assertEqual(self.source().kind, "command")
        self.assertEqual(self.be.work_key, "", "the set has no key: neither the file's line nor the startup key stands in")
        self.assertEqual(sb._WORK_KEY, "", "the startup key is retired for good")
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(1, "key"), "ANTHROPIC_API_KEY present")
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(2, ""), "ANTHROPIC_API_KEY present")
        for m in self.logged:
            self.assertNotIn(OLD_KEY, m)
            self.assertNotIn(BOOT_KEY, m)

    def test_the_startup_key_discard_notice_names_the_command_variable(self):
        sb._WORK_KEY = BOOT_KEY
        sb._STARTUP_KEY_DISCARD_SAID = False
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.be = self.construct()
        text = err.getvalue()
        self.assertIn("the startup key (sha256:%s) is IGNORED" % ks.fingerprint(BOOT_KEY), text)
        self.assertIn("%s selects the command source" % ks.CMD_VAR, text)
        self.assertIn("use that source", text)
        self.assertNotIn(BOOT_KEY, text)
        self.assertNotIn(self.cmd, text, "the command text is never rendered")

    def test_the_commands_key_wins_when_it_prints_one(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(self.be.work_key, k)
        self.assertEqual(self._env_for(1, "key")["ANTHROPIC_API_KEY"], k)
        self.assertEqual(self.be._work_key_and_source(), (k, "command"))
        self.assertEqual(sb.work_api_key(), k, "the module-level reader the judges are wired to agrees")
        self.assertTrue(any("the ANTHROPIC_API_KEY line the credential command printed" in m for m in self.logged),
                        self.logged)
        self.assertFalse(any(k in m or OLD_KEY in m for m in self.logged))

    def test_the_startup_claim_is_still_popped_out_of_the_environment(self):
        sb._WORK_KEY = None
        os.environ["ANTHROPIC_API_KEY"] = BOOT_KEY
        self.assertEqual(sb.work_api_key(), "", "the command kind: the ambient key is claimed and ignored")
        self.assertFalse("ANTHROPIC_API_KEY" in os.environ, "the one-claimer property holds under every kind")


class EnvironmentDoor(_Lab):
    """A foreground manager's ROMP_CREDENTIAL_COMMAND selects the command kind with no line in the file
    (the reference's second door)."""

    def setUp(self):
        super().setUp()
        self.write_command_env(command=False)
        # the base's construction selected the command from the file and mirrored that onto the marker
        # beside it (service.env.source); with the line gone that marker reads as a removed source, by
        # design. This lab never had one.
        try:
            os.unlink(ks.marker_path(self.path))
        except OSError:
            pass
        os.environ[ks.CMD_VAR] = "%s \"$1\"" % self.cmd
        self.reset_sources()
        self.logged.clear()
        self.be = self.construct()

    def test_the_environment_line_selects_the_command_for_a_foreground_manager(self):
        self.assertEqual(self.source().kind, "command")
        env = self._env_for(1, "login")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"])
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertEqual(sb.credential_set(), self.values)


class CommandSourceFailure(_Lab):
    def test_a_failed_run_keeps_the_previous_set_with_one_problem_line_per_episode(self):
        self.assertEqual(self._env_for(1, "login")["A_TOKEN"], self.values["A_TOKEN"])
        w = fixture_value("wrong")
        self.fail_command("echo '%s' >&2\necho 'A_TOKEN=%s'\nexit 3" % (w, w))
        self.rerun()
        env = self._env_for(2, "login")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"], "the previous set stands; a failing command's stdout is never trusted")
        lines = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("exited 3", lines[0])
        self.assertNotIn(" after ", lines[0], "the run's timing is not in the log line")
        self.assertNotIn("stderr", lines[0], "nor its stderr count: both differ per run of the same failure")
        self.assertIn("last successful run (sha256:%s)" % es.set_fingerprint(self.values), lines[0])
        self.assertNotIn(w, lines[0])
        # the same failure again, with another stderr length and its own duration: one line still
        self.fail_command("echo '%s%s' >&2\nsleep 0.15\nexit 3" % (w, w))
        self._env_for(3, "login")
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 1,
                         "the same kind of failure again is not new information, whatever its timing")
        self.fail_command("exit 4")
        self._env_for(4, "login")
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 2,
                         "another exit code is another kind")
        self.fail_command("sleep 30")
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "0.5"
        self._env_for(5, "login")
        lines = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(lines), 3, "a new kind of failure is a new line")
        self.assertIn("timed out after 0.5s", lines[2])
        self.print_set(self.values)
        self._env_for(6, "login")
        self.assertTrue(any(m.startswith("credential command: succeeded again") for m in self.logged), self.logged)
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 3)

    def test_a_first_failure_launches_with_nothing_injected_and_never_refuses(self):
        self.fail_command("exit 7")
        self.reset_sources()
        self.logged.clear()
        self.be = self.construct()
        for n, auth in ((1, "key"), (2, ""), (3, "login")):
            env = self._env_for(n, auth)                       # a launch, not a refusal
            self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present (%s)" % auth)
            self.assertFalse("A_TOKEN" in env, "A_TOKEN present (%s)" % auth)
            self.assertEqual(env["ROMP_SID"], "11111111-2222-3333-4444-%012d" % n)
        failed = [t for t in self.problems() if "credential command" in t and "failed" in t]
        self.assertEqual(len(failed), 1, self.problems())
        self.assertTrue(failed[0].startswith("key source: the credential command failed"),
                        "the boot verdict is the one report of the first run; the connects add no second line")
        self.assertIn("exited 7", failed[0])
        self.assertIn("nothing injected", failed[0])
        self.assertTrue(any("printed no ANTHROPIC_API_KEY" in t for t in self.problems()),
                        "the key pick still says it launched without one")
        self.assertEqual(es.current(self.source())["ok"], False)
        self.assertEqual(es.current(self.source())["exitCode"], 7)
        self.assertEqual(self.be.work_key, "", "the module reader never raises for a failed run")
        self.assertEqual(sb.work_api_key(), "")

    def test_an_authentication_failure_invalidates_the_cached_set(self):
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        runs = es._runs
        self.be._credential_auth_failed(s, "HTTP 401 on a turn")
        self.assertEqual(es._runs, runs, "invalidation runs nothing itself")
        self._env_for(2, "login")
        self.assertEqual(es._runs, runs + 1, "the next launch re-runs the command")
        self.assertTrue(any("reported an authentication failure (HTTP 401 on a turn)" in m for m in self.logged),
                        self.logged)

    def test_a_burst_of_refusals_is_one_command_run(self):
        # a revoked credential: every judge call and every launch reports a refusal, and the store
        # keeps handing back the same set; the first refusal re-runs the command, the rest do not
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        runs = es._runs
        for _ in range(4):
            self.be._credential_auth_failed(s, "HTTP 401 on a turn")
            self.assertFalse(sb.credential_invalidate("judge call refused as unauthenticated (planner)"),
                             "the judges' wire is the same once-per-credential path")
            self._env_for(2, "login")
        self.assertEqual(es._runs, runs + 1, "one run for the burst")
        said = [m for m in self.logged if "reported an authentication failure" in m]
        self.assertEqual(len(said), 1, "said when it fires, not per refusal")
        self.rerun()                                           # the operator's invalidation re-arms the path
        self._env_for(3, "login")
        self.assertEqual(es._runs, runs + 2)
        self.be._credential_auth_failed(s, "HTTP 401 on a turn")
        self._env_for(4, "login")
        self.assertEqual(es._runs, runs + 3, "after an operator's re-run the next refusal fires once more")

    def test_a_completed_turn_on_the_refused_credential_re_arms_the_refusal_path(self):
        # 401, run, same set, a completed turn on that credential, a later 401: the later refusal
        # re-runs the command. Keyed on the launch stamp: a completed turn on a session launched with
        # another credential, or with none (the login), re-arms nothing.
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s = self._sess(1, auth="key")
        self.be._options(s, dict)
        self.assertEqual(s._launched_key_fp, es.fingerprint(k))
        runs = es._runs
        s._ah_note_result(_result(401))
        self._env_for(2, "key")
        self.assertEqual(es._runs, runs + 1, "the first refusal re-runs")
        s._ah_note_result(_result(401))
        self._env_for(3, "key")
        self.assertEqual(es._runs, runs + 1, "the same set again: suppressed")
        login = self._sess(4, auth="login")
        self.be._options(login, dict)
        self.assertEqual(login._launched_key_fp, "", "no key injected, no helper: nothing stamped")
        login._ah_note_result(_result(None))
        s._ah_note_result(_result(500))                        # an error result is not a success
        s._ah_note_result(_result(401))
        self._env_for(5, "key")
        self.assertEqual(es._runs, runs + 1, "a login session's turn and an error result say nothing")
        old = self._sess(6, auth="key")
        self.be._options(old, dict)
        old._launched_key_fp = es.fingerprint(fixture_value("pre-rotation"))
        old._ah_note_result(_result(None))
        s._ah_note_result(_result(401))
        self._env_for(7, "key")
        self.assertEqual(es._runs, runs + 1, "a turn on a credential other than the refused one says nothing")
        self.assertFalse(any("completed a turn on the credential last refused" in m for m in self.logged))
        s._ah_note_result(_result(None))                       # the refused credential completed a turn
        self.assertTrue(any("completed a turn on the credential last refused (sha256:%s)" % es.fingerprint(k) in m
                            for m in self.logged), self.logged)
        s._ah_note_result(_result(401))
        self._env_for(8, "key")
        self.assertEqual(es._runs, runs + 2, "the later refusal is new information: the command runs again")
        # the judges' wire re-arms the same path: a served call ran on the set as a whole
        s._ah_note_result(_result(401))
        self._env_for(9, "key")
        self.assertEqual(es._runs, runs + 2)
        self.assertTrue(sb.credential_auth_ok(""))
        s._ah_note_result(_result(401))
        self._env_for(10, "key")
        self.assertEqual(es._runs, runs + 3)
        self.assertFalse(any(k in m for m in self.logged), "no line carries the key")

    def test_a_sidechain_result_is_not_the_parent_streams_event(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s = self._sess(1, auth="key")
        self.be._options(s, dict)
        runs = es._runs
        side = SimpleNamespace(is_error=True, api_error_status=401, parent_tool_use_id="toolu_01")
        s._ah_note_result(side)
        self._env_for(2, "key")
        self.assertEqual(es._runs, runs, "a subagent's result carries no credential event")

    def test_a_refusal_on_a_session_still_on_the_pre_rotation_key_runs_nothing(self):
        old_k, new_k = fixture_value("old-key"), fixture_value("new-key")
        self.values["ANTHROPIC_API_KEY"] = old_k
        self.print_set(self.values)
        self.rerun()
        old = self._sess(1, auth="key")
        self.be._options(old, dict)
        self.assertEqual(old._launched_key_fp, es.fingerprint(old_k))
        self.values["ANTHROPIC_API_KEY"] = new_k
        self.print_set(self.values)
        self.rerun()                                           # the rotation, re-read
        cur = self._sess(2, auth="key")
        self.be._options(cur, dict)
        self.assertEqual(cur._launched_key_fp, es.fingerprint(new_k))
        runs = es._runs
        self.logged.clear()
        for n in range(5):
            old._ah_note_result(_result(401))
            self._env_for(10 + n, "key")                       # a connect between: nothing to re-run
            cur._ah_note_result(_result(None))
        self.assertEqual(es._runs, runs, "no run: the refused key is not the one the command would be run for")
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [],
                         "neither the refusal line nor the re-arm line, turn after turn")
        cur._ah_note_result(_result(401))
        self._env_for(20, "key")
        self.assertEqual(es._runs, runs + 1)
        said = [m for m in self.logged if "reported an authentication failure" in m]
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("s2 reported", said[0])
        cur._ah_note_result(_result(401))
        old._ah_note_result(_result(401))
        self._env_for(21, "key")
        self.assertEqual(es._runs, runs + 1, "suppressed: the same set, and the stale stamp still says nothing")
        self.assertFalse(any(old_k in m or new_k in m for m in self.logged), "no line carries a key")

    def test_a_launch_refused_as_unauthenticated_invalidates_the_set(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s = self._sess(1, auth="key")
        self.be.spawn("s1", self.lab, sid=s.sid)
        self.be._options(s, dict)
        runs = es._runs
        self.be._record_launch_error(s, RuntimeError("Not logged in. Please run /login"))
        self._env_for(2, "key")
        self.assertEqual(es._runs, runs + 1, "the CLI refused to start for want of a credential: re-read")
        self.assertTrue(any("the CLI refused to start: not authenticated" in m for m in self.logged), self.logged)
        self.be._record_launch_error(s, RuntimeError("some other launch failure"))
        self._env_for(3, "key")
        self.assertEqual(es._runs, runs + 1, "a failure that is not credential-class invalidates nothing")
        self.assertTrue(sb.is_auth_failure_text("API key is invalid"))
        self.assertFalse(sb.is_auth_failure_text("overloaded"))

    def test_a_connect_on_a_failing_command_runs_it_once_not_twice(self):
        # a non-keyed connect takes the set (one run: a failed run is re-run per caller) and stamps the
        # helper's fingerprint from the set it took, so the helper's own read is not a second run
        h = fixture_value("helper")
        self.helper("echo '%s'" % h)
        self._env_for(1, "login")                              # the helper's fingerprint is cached from this connect
        self.fail_command("exit 3")
        self.rerun()
        runs, hruns = es._runs, es.helper_runs()
        s = self._sess(2, auth="login")
        self.be._options(s, dict)
        self.assertEqual(es._runs, runs + 1, "one run per connect on a failing command, not two")
        self.assertEqual(s._launched_key_fp, es.fingerprint(h))
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values), "the previous set stands in")
        self.assertLessEqual(es.helper_runs(), hruns + 1, "at most the one helper run the invalidation costs")
        s2 = self._sess(3, auth="login")
        self.be._options(s2, dict)
        self.assertEqual(es._runs, runs + 2)
        self.assertEqual(es.helper_runs(), hruns + 1, "the failing run kept the set: the helper's entry stands")


class FailingCommandReaders(_Lab):
    """After a failed run the launch re-runs the command (keep-last-good's recovery path) and the other
    readers take the record that stands. Before this every reader re-ran: with a hung store (a 15 s
    timeout per run) each judge call, status read and cycle row waited behind its own run (review find,
    2026-09-07)."""

    def test_the_judges_and_status_readers_take_the_record_that_stands_and_a_connect_re_runs(self):
        s = self._live("", auth="login")
        self.connect(s)
        marker = os.path.join(self.lab, "ran")
        self.fail_command("echo x >> '%s'\nexit 3" % marker)
        self.rerun()
        self.assertEqual(sb.credential_set(), self.values, "the invalidation's one run: a failure on the last good set")
        runs, n = es._runs, _count(marker)
        self.assertEqual(n, 1)
        for _ in range(4):
            self.assertEqual(sb.credential_set(), self.values, "the judges' overlay and the catalog")
            self.assertEqual(sb.work_api_key(), "", "the resolver behind work_api_key: key-billed judge reads")
            self.assertEqual(self.source().resolve(), "")
            self.assertIn("exited 3", self.be.key_source_status()["err"])
            self.assertEqual(self.be.api_health_snapshot()["keySource"]["lastRun"]["ok"], False)
            self.assertEqual(self.be.cycle_key(s.sid), "current", "a cycle's row")
            self.be.work_key_fp()
        self.assertEqual((es._runs, _count(marker)), (runs, n), "no non-launch reader ran the command")
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 1)
        self.connect(self._live("", auth="login", n=2))
        self.assertEqual((es._runs, _count(marker)), (runs + 1, n + 1), "a connect re-runs")
        self.be.refresh_key_source()
        self.assertEqual((es._runs, _count(marker)), (runs + 2, n + 2), "a refresh re-runs")
        self.print_set(self.values)
        self.connect(self._live("", auth="login", n=3))
        self.assertEqual(es._runs, runs + 3, "the connect after the store is back finds it")
        self.assertEqual(self.be.key_source_status()["err"], "", "and every reader is served the recovery")
        self.assertEqual(es._runs, runs + 3)


class MisconfiguredSource(_Lab):
    """A configuration error (an empty command line, a selector file that is not one name, a name outside
    ROMP_CREDENTIAL_NAMES) is decided before the command runs, and nothing but an operator's edit clears
    it. It is not a failed run: with no set from an earlier run a launch is refused with the reason (the
    fail-loudly rule; a misconfigured reference refuses the same way), while an earlier set stands, as
    after a store outage. Before this every launch on such an installation went ahead on the login after
    one problem line (review find, 2026-09-07)."""

    def _rebuild(self):
        self.reset_sources()
        self.logged.clear()
        self.be = self.construct()

    def test_an_empty_command_line_with_no_earlier_set_refuses_the_launches_that_would_bill_it(self):
        self.write_command_env(command=False, lines=["ROMP_PERF=1", "%s=" % ks.CMD_VAR])
        self._rebuild()
        self.assertEqual(self.source().kind, "command")
        for n, auth in ((1, "key"), (2, "")):
            with self.assertRaises(ks.KeySourceError) as cm:
                self._env_for(n, auth)
            self.assertIn("must be one non-empty line", str(cm.exception), auth)
        # an explicit login pick never touches the key source (the base's rule for a broken reference too):
        # it launches, with nothing of the set (which holds nothing) and no key
        env = self._env_for(3, "login")
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("A_TOKEN", env)
        self.assertEqual(es._runs, 0, "nothing ran: the reason was decided before the command")
        snap = es.current(self.source())
        self.assertEqual((snap["ok"], snap["configError"], snap["stale"]), (False, True, False))
        self.assertTrue(any("credential command" in t and "must be one non-empty line" in t for t in self.problems()),
                        self.problems())

    def test_a_selector_problem_with_no_earlier_set_refuses_too_and_names_nothing(self):
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        sel = os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"]
        with open(sel, "w") as fh:
            fh.write("zz")
        self._rebuild()
        with self.assertRaises(ks.KeySourceError) as cm:
            self._env_for(1, "")
        self.assertIn("outside ROMP_CREDENTIAL_NAMES", str(cm.exception))
        self.assertNotIn("zz", str(cm.exception), "the token is never part of the refusal")
        secret = fixture_value("pasted")
        with open(sel, "w") as fh:
            fh.write(secret + " and more\n")                     # not a name: another size, another identity
        with self.assertRaises(ks.KeySourceError) as cm:
            self._env_for(2, "key")
        self.assertIn("not a name", str(cm.exception))
        self.assertNotIn(secret, str(cm.exception) + "\n".join(self.logged) + json.dumps(self.be.problems()))
        self.assertEqual(es._runs, 0)

    def test_a_failed_run_with_no_earlier_set_is_still_a_launch(self):
        # unchanged: the store is down (the command exits 3), which clears on its own
        self.fail_command("exit 3")
        self._rebuild()
        for n, auth in ((1, "key"), (2, ""), (3, "login")):
            env = self._env_for(n, auth)
            self.assertFalse("ANTHROPIC_API_KEY" in env, auth)
        snap = es.current(self.source())
        self.assertEqual((snap["ok"], snap["configError"]), (False, False))

    def test_a_configuration_error_after_a_good_set_stands_on_it(self):
        self.assertEqual(self._env_for(1, "login")["A_TOKEN"], self.values["A_TOKEN"])
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        with open(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], "w") as fh:
            fh.write("zz")                                       # a hand edit: the selector's identity moved
        env = self._env_for(2, "key")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"], "the last good set stands; no refusal")
        self.assertFalse("ANTHROPIC_API_KEY" in env)
        snap = es.current(self.source(), retry_failed=False)
        self.assertEqual((snap["ok"], snap["stale"], snap["configError"]), (False, True, True))
        lines = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("outside ROMP_CREDENTIAL_NAMES", lines[0])


class ModuleReaders(_Lab):
    def test_the_command_resolver_is_wired_at_import_and_never_raises_for_a_failed_run(self):
        self.assertIsNotNone(ks.COMMAND_RESOLVER)
        src = self.source()
        self.assertEqual(src.resolve(), "", "no key in the set")
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(src.resolve(), k)
        self.fail_command("exit 5")
        self.rerun()
        self.assertEqual(src.resolve(), k, "the last good set's key stands")
        self.assertEqual(sb.work_api_key(), k)
        failed = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(failed), 1, "a failed run through the module reader is one problem line")

    def test_credential_set_is_the_whole_set_for_the_judges_and_the_catalog(self):
        self.assertEqual(sb.credential_set(), self.values)
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(sb.credential_set(), self.values, "the key is in it; the judge pops it itself")

    def test_a_swap_to_another_kind_releases_the_resident_set(self):
        # romp keyswap <profile> (or an edit of service.env) moves the selection from the command to a key
        # line: every path here gates on the kind and never reached envsource with the new source, so the
        # last set stayed resident in the kernel's memory for the process's life (review find, 2026-09-07).
        # The launch and the module-level gate tell envsource (release_for), which drops it with no run.
        self._env_for(1, "login")
        self.assertEqual(es._values, self.values)
        self.write_command_env(key=OLD_KEY, command=False)
        self.assertEqual(self.source().kind, "file")
        self.assertEqual(sb.credential_set(), {})
        self.assertEqual(es._values, {}, "the module-level gate released the set")
        self.assertFalse(es._snap["configured"])
        self.write_command_env()
        self.assertEqual(self._env_for(2, "login")["A_TOKEN"], self.values["A_TOKEN"], "the command again: it runs again")
        self.assertEqual((es._runs, es._values), (2, self.values))
        self.write_command_env(key=OLD_KEY, command=False)
        self.assertEqual(self._env_for(3, "key")["ANTHROPIC_API_KEY"], OLD_KEY, "the file kind's launch is the base's")
        self.assertEqual(es._values, {}, "the launch released the set")
        self.assertEqual(es._runs, 2, "and ran nothing")
        self.assertEqual([m for m in self.logged if m.startswith("credential command: failed")], [])

    def test_the_seams_are_no_ops_outside_the_command_kind(self):
        self.assertTrue(sb.credential_invalidate("judge call refused as unauthenticated (planner)"))
        self.assertFalse(sb.credential_invalidate("again"), "once per credential")
        self.assertTrue(sb.credential_auth_ok(""))
        self.write_command_env(key=OLD_KEY, command=False)     # the file kind
        self.reset_sources()
        self.assertEqual(self.source().kind, "file")
        self.assertEqual(sb.credential_set(), {})
        self.assertFalse(sb.credential_invalidate("x"))
        self.assertFalse(sb.credential_auth_ok(""))
        s = self._sess(1, auth="key")
        self.be._options(s, dict)
        self.be._credential_auth_failed(s, "HTTP 401 on a turn")
        self.be._credential_auth_ok(s)
        self.assertEqual(es._runs, 0, "the command never ran under the file kind")
        self.assertEqual([m for m in self.logged if m.startswith("credential command")], [])


class JudgesDefaultBilling(_Lab):
    """The judges' default-billing question (judge._judge_auth for a session without an explicit Billing
    pick: the key when one exists, else the login) is answered by the kernel through _judge_work_key_configured,
    the function _sdk_locked wires as judge._WORK_KEY_CONFIGURED_FN. Under the command kind the answer is
    whether the SET carries ANTHROPIC_API_KEY, the same fact _options launches on: a set without one is a
    helper- or login-billed installation, its unpicked sessions launch on the login, and their judges bill
    the login beside them. The descriptor's `configured` is True for any selected command and is the wrong
    question there. Under the reference, the file kind and a removed source the descriptor answers as
    before, and no billing decision resolves the reference."""

    km = _KM_CMDSRC   # loaded at import (see the module header), never re-executed at run time

    def setUp(self):
        super().setUp()
        self.jd = self.km.jd
        self._wires = (self.jd._WORK_KEY_FN, self.jd._WORK_KEY_CONFIGURED_FN, self.jd._ENV_SET_FN)
        # the three wires _sdk_locked lands, on this lab's backend module
        self.jd._WORK_KEY_FN = sb.work_api_key
        self.jd._WORK_KEY_CONFIGURED_FN = lambda: self.km._judge_work_key_configured(sb)
        self.jd._ENV_SET_FN = sb.credential_set

    def tearDown(self):
        self.jd._WORK_KEY_FN, self.jd._WORK_KEY_CONFIGURED_FN, self.jd._ENV_SET_FN = self._wires
        super().tearDown()

    def test_a_set_without_a_key_bills_the_judges_on_the_login_the_session_launched_on(self):
        source = self.source()
        self.assertEqual(source.kind, "command")
        self.assertTrue(source.configured, "the descriptor alone says configured: not the launch's question")
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(1, ""), "the launch injects no key: the login bills")
        self.assertFalse(self.km._judge_work_key_configured(sb))
        self.assertEqual(self.jd._judge_auth(""), "login")
        env = self.jd._judge_env("triage", self.jd._judge_auth(""))      # never a refusal on a keyless set
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present in a login-billed judge call")
        self.assertEqual(env.get("A_TOKEN"), self.values["A_TOKEN"], "the role variables still ride the call")

    def test_a_set_that_carries_a_key_bills_the_judges_on_it_and_follows_a_rotation(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(self._env_for(1, "").get("ANTHROPIC_API_KEY"), k, "the launch is keyed")
        self.assertTrue(self.km._judge_work_key_configured(sb))
        self.assertEqual(self.jd._judge_auth(""), "key")
        self.assertEqual(self.jd._judge_env("triage", "key").get("ANTHROPIC_API_KEY"), k)
        # the set loses its key: the judges follow the launch, with nothing restarted
        del self.values["ANTHROPIC_API_KEY"]
        self.print_set(self.values)
        self.rerun()
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(2, ""), "the launch injects no key now")
        self.assertEqual(self.jd._judge_auth(""), "login")

    def test_an_explicit_key_pick_on_a_keyless_set_follows_the_launch_instead_of_refusing(self):
        # the launch (_options) goes ahead un-injected with one problem line for such a session; _judge_env
        # raised "No API key source is configured for this judge call" for the same session, and _judge_run
        # latched it auth-down and paused the pass (review find, 2026-09-07): judge and launch disagreed
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(1, "key"), "the launch injects nothing")
        env = self.jd._judge_env("triage", "key")                          # no raise
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present: never an empty variable")
        self.assertEqual(env.get("A_TOKEN"), self.values["A_TOKEN"], "the role variables ride the call")
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(self.jd._judge_env("triage", "key").get("ANTHROPIC_API_KEY"), k, "a set with a key injects it")
        self.assertFalse(any(k in m for m in self.logged), "no value reaches the log")

    def test_a_failed_run_answers_from_the_last_good_set(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        self.assertEqual(self.jd._judge_auth(""), "key")
        self.fail_command()
        self.rerun()
        self.assertEqual(self.jd._judge_auth(""), "key", "the last good set's key stands")
        self.assertEqual(self.jd._judge_env("triage", "key").get("ANTHROPIC_API_KEY"), k)
        self.assertFalse(any(k in m for m in self.logged), "no value reaches the log")

    def test_the_other_kinds_answer_from_the_descriptor_without_resolving(self):
        with patch.object(ks.KeySource, "resolve", side_effect=AssertionError("a billing decision resolved the source")):
            self.write_command_env(command=False, lines=["%s=op://vault/item/field" % ks.REF_VAR])
            self.reset_sources()
            self.assertEqual(self.source().kind, "op")
            self.assertTrue(self.km._judge_work_key_configured(sb), "a reference is a key source until it fails")
            self.assertEqual(self.jd._judge_auth(""), "key")
            self.write_command_env(command=False, key=OLD_KEY)
            self.reset_sources()
            self.assertEqual(self.source().kind, "file")
            self.assertTrue(self.km._judge_work_key_configured(sb))
            self.assertEqual(self.jd._judge_auth(""), "key")
            # the reference removed with nothing in its place: an explicit choice, never permission to
            # bill the login; the call boundary raises the removed-source error, as the base does
            self.write_command_env(command=False, lines=["%s=op://vault/item/field" % ks.REF_VAR])
            self.reset_sources()
            self.source()
            self.write_command_env(command=False)
            self.reset_sources()
            self.assertEqual(self.source().kind, "error")
            self.assertTrue(self.km._judge_work_key_configured(sb))
            self.assertEqual(self.jd._judge_auth(""), "key")
        with self.assertRaises(ks.KeySourceError) as cm:
            self.jd._judge_env("triage", "key")
        self.assertIn("was removed", str(cm.exception))

    def test_the_kernel_wires_the_answer_beside_the_key_claimer(self):
        import inspect
        src = inspect.getsource(self.km._sdk_locked)
        self.assertIn("jd._WORK_KEY_FN = sbmod.work_api_key\n", src)
        self.assertIn("jd._WORK_KEY_CONFIGURED_FN = lambda: _judge_work_key_configured(sbmod)", src)
        self.assertNotIn("work_api_key_source().configured", src, "the descriptor is not the judges' question")


class ByteIdenticalOutsideTheCommandKind(_Lab):
    """With no command selected every launch path is the base's: the key from the file, the login
    environment for a login launch, the command source never run, nothing about it in the log."""

    BOOT = BOOT_KEY

    def setUp(self):
        super().setUp()
        self.write_command_env(key=OLD_KEY, command=False)
        self.reset_sources()
        self.logged.clear()
        sb._WORK_KEY = BOOT_KEY
        self.be = self.construct()

    def test_the_file_mode_launch_is_the_bases(self):
        self.assertEqual(self.source().kind, "file")
        keyed = self._sess(1, auth="key")
        env = self.be._options(keyed, dict)["env"]
        self.assertEqual(env["ANTHROPIC_API_KEY"], OLD_KEY)
        self.assertEqual(keyed._launched_key_fp, ks.fingerprint(OLD_KEY))
        self.assertEqual(keyed._launched_set_fp, "", "no role variables outside the command kind")
        unpicked = self._env_for(2, "")
        self.assertEqual(unpicked["ANTHROPIC_API_KEY"], OLD_KEY, "a configured file source keys an unpicked session")
        login = self._sess(3, auth="login")
        env = self.be._options(login, dict)["env"]
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertEqual(login._launched_key_fp, "")
        self.assertEqual(dict((k, v) for k, v in env.items() if k in sb.AUTH_ENV_NAMES),
                         {k: v for k, v in sb.startup_auth_env().items()},
                         "a login launch restores the startup tokens exactly as the base does")
        self.assertEqual(es._runs, 0, "the command source never runs")
        self.assertEqual([m for m in self.logged if "credential command" in m or "key source: command" in m], [])
        for name in self.values:
            self.assertFalse(name in unpicked, "%s present" % name)

    def test_an_empty_key_under_a_key_pick_is_still_the_bases_refusal(self):
        self.write_command_env(key="", command=False)
        self.reset_sources()
        with self.assertRaises(ks.KeySourceError):
            self._env_for(1, "key")
        self.assertEqual(es._runs, 0)

    def test_the_op_and_file_block_keeps_the_bases_lines(self):
        src = open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read()
        for line in ('launch_keyed = sess.auth == "key" or (sess.auth != "login" and key_source.configured)',
                     'raise _keysrc.KeySourceError("API key billing selected but no API key source is configured")',
                     'kw["env"] = dict(kw["env"], **startup_auth_env())',
                     "work_key, key_src = self._work_key_and_source(key_source)"):
            self.assertIn(line, src, line)
        self.assertEqual(src.count("ANTHROPIC_API_KEY=work_key"), 1, "one injection site for every kind")


class NothingLeaks(_Lab):
    def _blob(self):
        return "\n".join(self.logged) + json.dumps(self.problems()) + json.dumps(es.current(self.source()))

    def test_no_value_reaches_any_surface_whatever_the_command_does(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        loud = "\n".join("echo '%s' >&2" % v for v in self.values.values())
        self.print_set(self.values, extra=loud)                  # every value also on stderr
        self.rerun()
        for n, auth in ((1, "key"), (2, "login"), (3, "")):
            self._env_for(n, auth)
        self.fail_command(loud + "\n" + "\n".join("echo '%s'" % v for v in self.values.values()) + "\nexit 1")
        self.rerun()
        self._env_for(4, "key")
        sb.credential_set()
        sb.work_api_key()
        blob = self._blob()
        for v in list(self.values.values()) + [OLD_KEY, BOOT_KEY]:
            self.assertNotIn(v, blob)
        self.assertNotIn("fixture", blob)
        self.assertNotIn(self.cmd, blob, "the command text is rendered by fingerprint only")
        for name, value in self.values.items():
            self.assertFalse(os.environ.get(name) == value, "a set value reached os.environ under " + name)

    def test_os_environ_is_unchanged_after_every_reader(self):
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        self.rerun()
        before = dict(os.environ)
        src = self.source()
        s = self._sess(1, auth="key")
        readers = (lambda: self.be._options(s, dict),
                   lambda: self.be._options(self._sess(2, auth="login"), dict),
                   lambda: self.be._options(self._sess(3), dict),
                   lambda: self.be.work_key,
                   sb.work_api_key,
                   sb.credential_set,
                   lambda: sb.credential_invalidate("test"),
                   lambda: sb.credential_auth_ok(""),
                   lambda: es.injection(src),
                   lambda: es.take(src),
                   lambda: es.resolve_key(src),
                   lambda: self.be._credential_auth_failed(s, "HTTP 401 on a turn"),
                   lambda: self.be._credential_auth_ok(s),
                   lambda: s._ah_note_result(_result(401)),
                   lambda: s._ah_note_result(_result(None)))
        for i, read in enumerate(readers):
            read()
            self.assertEqual(sorted(os.environ), sorted(before), "the names changed after reader %d" % i)
            for name in self.values:
                # by VALUE: a developer's shell may carry a variable of the same name (never printed here)
                self.assertTrue(os.environ.get(name) == before.get(name), "%s changed after reader %d" % (name, i))
                self.assertFalse(os.environ.get(name) == self.values[name],
                                 "a set value reached os.environ under %s after reader %d" % (name, i))


class HelperSessionsConverge(_Lab):
    """cycle_key under the command kind converges each live session on what a launch would hand it NOW.
    The lab's set carries no ANTHROPIC_API_KEY and a fake apiKeyHelper is configured before the boot: the
    helper-billed installation the convergence exists for. The base's compare (a non-keyed session reads
    "login") made --cycle-all a no-op on such a box."""

    def before_construct(self):
        self.helper_value = fixture_value("helper")
        self.rotate_helper(self.helper_value)

    def rotate_helper(self, value):
        self.helper("echo '%s'" % value)

    def keyswap_lines(self):
        return [m for m in self.logged if m.startswith("keyswap (s1)")]

    def test_a_connect_stamps_the_helpers_fingerprint_when_nothing_is_injected(self):
        s = self._live("key")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "the set carries no key: nothing injected")
        self.assertEqual(kw["env"]["A_TOKEN"], self.values["A_TOKEN"], "the role variables ride the launch")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values))
        self.assertFalse(s._launched_keyed)
        self.assertFalse(any(self.helper_value in m for m in self.logged), "the helper's output is hashed inside envsource")

    def test_a_session_on_the_current_helper_output_is_current_not_reconnected(self):
        s = self._live("key")
        self.connect(s)
        self.assertFalse(s._launched_keyed, "the kernel injected nothing: the set carries no key")
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.assertEqual(self.be.cycle_key(s.sid), "current", "idempotent: a repeated --cycle-all leaves it alone")
        self.assertEqual(self.reconnects, [])

    def test_a_rotation_behind_the_helper_cycles_once_then_reads_current(self):
        s = self._live("key")
        self.connect(s)
        self.rotate_helper(fixture_value("rotated"))
        self.assertEqual(self.be.cycle_key(s.sid), "current", "cached: the kernel has not re-run the helper yet")
        self.be.refresh_key_source()                              # what --cycle does first
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        self.assertEqual(self.reconnects, [s.sid])
        self.assertEqual(self.defers, [False], "immediate-only, like every key cycle")
        lines = self.keyswap_lines()
        self.assertEqual(len(lines), 1, self.logged)
        self.assertIn("apiKeyHelper now prints sha256:", lines[0])
        self.assertNotIn(self.helper_value, lines[0])
        self.connect(s)                                           # the reconnect lands: new stamps
        self.assertEqual(self.be.cycle_key(s.sid), "current", "converged: the second run names nothing")
        self.assertEqual(self.reconnects, [s.sid])

    def test_a_rotation_of_a_role_variable_cycles_a_helper_session_too(self):
        s = self._live("key")
        self.connect(s)
        self.values["ANTHROPIC_LP_API_KEY"] = fixture_value("lp2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        self.assertIn("role variables are now sha256:", self.keyswap_lines()[0])
        self.connect(s)
        self.assertEqual(self.be.cycle_key(s.sid), "current")

    def test_a_login_billed_session_with_role_variables_cycles_on_their_rotation_only(self):
        s = self._live("login", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(s.sid), "current", "the set it launched with is the current one")
        self.rotate_helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "current", "a helper rotation is not its business: its CLI reported the login")
        self.values["A_TOKEN"] = fixture_value("role2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")

    def test_a_login_billed_session_with_no_role_variables_is_left_alone(self):
        # a set with no role variables is the key alone (a run that prints nothing is a failure and the
        # previous set stands, so a set is never empty after a success): a login pick has nothing to
        # converge on, whether or not its CLI has reported yet
        self.print_set({"ANTHROPIC_API_KEY": fixture_value("key")})
        self.rerun()
        s = self._live("login", auth="login")
        self.assertEqual(self.be.cycle_key(s.sid), "login", "nothing to re-present: a reconnect would cost a turn")
        s = self._live("", auth="login", n=2)
        self.assertEqual(self.be.cycle_key(s.sid), "login", "no init yet, nothing injected: nothing in play")
        # a command that never succeeded: an empty set, nothing injected, nothing in play for any pick
        self.fail_command()
        self.reset_sources()
        self.logged.clear()
        self.be = self.construct()
        s = self._live("login", auth="login", n=3)
        self.assertEqual(self.be.cycle_key(s.sid), "login")
        s = self._live("", n=4)
        self.assertEqual(self.be.cycle_key(s.sid), "login")
        self.assertEqual(self.reconnects, [])

    def test_a_helper_the_kernel_cannot_fingerprint_reconnects_on_every_run_with_the_reason(self):
        os.remove(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"))
        self.rerun()                          # the boot fingerprinted the helper; the operator's refresh forgets it
        s = self._live("key")
        self.connect(s)
        self.assertEqual(s._launched_key_fp, "", "no helper the kernel can see")
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        self.assertEqual(self.be.cycle_key(s.sid), "cycling", "nothing to converge on: reconnect, by its rule")
        self.assertEqual(self.reconnects, [s.sid, s.sid])
        line = self.keyswap_lines()[0]
        self.assertIn("could not fingerprint", line)
        self.assertIn("no apiKeyHelper in", line)

    def test_in_flight_work_still_skips_a_helper_session(self):
        s = self._live("key")
        self.connect(s)
        self.rotate_helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        s._bg_tasks["t1"] = {"since": 1}
        self.assertEqual(self.be.cycle_key(s.sid), "working")
        s._bg_tasks.clear()
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(s.sid), "working")
        self.assertEqual(self.reconnects, [], "a reconnect would kill the work: the base's rule")

    def test_an_explicit_login_pick_whose_cli_still_reports_a_key_converges_on_the_helper(self):
        # the pick says login, the CLI says a key (the helper found one anyway): the kernel injects
        # nothing either way, and the helper's fingerprint is what its new process would change
        s = self._live("key", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.rotate_helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")

    def test_a_login_pick_beside_a_set_that_carries_a_key_converges_on_the_helper_not_the_key(self):
        # the set has a key (other sessions inject it); THIS session picked login and its CLI still
        # reported a key, the helper's. Its compare is the helper's fingerprint, never the set's key
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        self.rerun()
        s = self._live("key", auth="login")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "ANTHROPIC_API_KEY present")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")   # the set's key rotates: not this session's concern
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.rotate_helper(fixture_value("rotated"))                # the helper rotates: it is
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        self.assertEqual(self.reconnects, [s.sid])

    def test_a_keyed_session_converges_on_the_sets_key(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s = self._live("key", auth="key")
        kw = self.connect(s)
        self.assertEqual(kw["env"]["ANTHROPIC_API_KEY"], k)
        self.assertEqual(s._launched_key_fp, es.fingerprint(k))
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        self.assertIn("the work key is now sha256:", self.keyswap_lines()[0])
        self.assertNotIn(k, self.keyswap_lines()[0])
        self.connect(s)
        self.assertEqual(self.be.cycle_key(s.sid), "current")

    def test_a_session_launched_on_the_sets_key_moves_when_the_set_loses_it(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        s = self._live("key")                 # no pick: the set's key is injected
        kw = self.connect(s)
        self.assertEqual(kw["env"]["ANTHROPIC_API_KEY"], k)
        self.assertTrue(s._launched_keyed)
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.values.pop("ANTHROPIC_API_KEY")  # the set loses its key: a launch now injects nothing
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        line = self.keyswap_lines()[0]
        self.assertIn("no longer carries ANTHROPIC_API_KEY", line)
        self.assertNotIn(k, line)
        self.connect(s)                       # its new process bills through the helper
        self.assertFalse(s._launched_keyed)
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(self.be.cycle_key(s.sid), "current")

    def test_a_probe_classifies_from_the_cached_set_and_a_stale_expected_source_raises(self):
        s = self._live("key")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(s.sid, probe=True), "current")
        self.rotate_helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        runs, hruns = es._runs, es.helper_runs()
        self.assertEqual(self.be.cycle_key(s.sid, probe=True), "cycle", "a probe classifies; nothing reconnects")
        self.assertEqual(self.reconnects, [])
        self.assertEqual((es._runs, es.helper_runs()), (runs, hruns), "the compare reads the cached set and the cached helper fingerprint")
        with self.assertRaisesRegex(ks.KeySourceError, "source changed"):
            self.be.cycle_key(s.sid, expected_source_fp="stale-source")
        self.assertEqual(self.reconnects, [])
        self.assertEqual(self.be.cycle_key(s.sid, expected_source_fp=self.source().fingerprint()), "cycling")
        self.assertEqual(self.reconnects, [s.sid])
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(s.sid, probe=True), "working")
        idle = self._live("", auth="login", n=2)
        self.print_set({"ANTHROPIC_API_KEY": fixture_value("key")})    # no role variables: the key alone
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(idle.sid, probe=True), "login")

    def test_a_refresh_between_a_connects_read_and_its_helper_fingerprint_leaves_no_stale_entry_current(self):
        # a connect takes the set, then asks for the helper's fingerprint with it; an invalidate that
        # lands between the two (a --refresh, a refusal on another session) must not leave the
        # fingerprint of the connect's pre-refresh overlay stored as the current one. The helper here
        # reads a role variable, so the overlay decides what it prints.
        h = fixture_value("helper")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        es.invalidate("the helper changed")
        role_a, role_b = self.values["A_TOKEN"], fixture_value("role-b")
        real_take = es.take

        def take_then_rotate(source=None, environ=None):
            out = real_take(source, environ)
            self.values["A_TOKEN"] = role_b
            self.print_set(self.values)
            es.invalidate("a refresh landed between the connect's read and its helper fingerprint")
            return out

        s = self._live("key")
        es.take = take_then_rotate
        try:
            self.connect(s)
        finally:
            es.take = real_take
        self.assertEqual(s._launched_key_fp, es.fingerprint("%s-%s" % (h, role_a)),
                         "stamped with what its CLI's helper prints in the environment it launched with")
        hruns = es.helper_runs()
        fp, kind = self.be.credential_fingerprint()
        self.assertEqual((fp, kind), (es.fingerprint("%s-%s" % (h, role_b)), "helper"),
                         "the current fingerprint is of the current set's overlay, not the connect's")
        self.assertEqual(es.helper_runs(), hruns + 1, "the connect's entry was stale: the helper ran again")
        self.assertEqual(self.be.cycle_key(s.sid), "cycling", "the stale stamp is a difference the cycle sees")

    def test_the_file_kind_compare_is_the_bases(self):
        # the command line gone (and the marker the boot wrote beside the file with it): a non-keyed
        # session reads "login" whatever its CLI reported; a keyed one converges on the file key's
        # fingerprint. The command source is never read.
        self.write_command_env(command=False)
        try:
            os.unlink(ks.marker_path(self.path))
        except OSError:
            pass
        self.reset_sources()
        runs = es._runs
        s = self._live("key")
        self.assertEqual(self.be.cycle_key(s.sid), "login")
        self.write_command_env(key=OLD_KEY, command=False)
        s = self._live("key", auth="key")
        s._launched_key_fp = ks.fingerprint("sk-ant-TEST-1111")          # launched on a previous key
        self.assertEqual(self.be.cycle_key(s.sid), "cycling")
        s._launched_key_fp = ks.fingerprint(OLD_KEY)
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.assertEqual(es._runs, runs, "the command source is never read under the file kind")


class KeycycleRouteOnTheCommandKind(_Lab):
    """POST /keycycle over the real kernel handler on loopback with a REAL backend under the command kind
    (tests/test_keyswap.py's KeycycleRoute uses doubles, and pins the reference path). keyFp is the set's
    credential fingerprint, never the command text's; sourceFp is the source's; "refresh" re-runs the
    command before the read and the rows; the rows come from cycle_key on the cached set with no
    request-level resolve; a failed run rides the answer as keyErr and the rows stand on the last good
    set. No value reaches the wire."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.km = _KM_CMDSRC   # loaded at import (see the module header), never re-executed at run time
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def before_construct(self):
        self.helper_value = fixture_value("helper")
        self.helper("echo '%s'" % self.helper_value)

    def _post(self, body):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/keycycle" % self.port, method="POST",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "X-Romp-Token": self.km.TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    def _with(self, body):
        from unittest import mock
        names = {s.name: sid for sid, s in self.be.sessions.items()}
        with mock.patch.object(self.km, "_sdk", lambda: self.be), \
             mock.patch.object(self.km, "_sid_of", lambda w: names.get(str(w), str(w))), \
             mock.patch.object(self.km, "_name_of", lambda sid: getattr(self.be.sessions.get(sid), "name", None)), \
             mock.patch.object(self.km, "_push_soon", lambda: None):
            return self._post(body)

    def _keyed_and_helped(self):
        """A set that carries a key; one session launched on it, one on a login pick whose CLI found the
        helper's key."""
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.rerun()
        keyed = self._live("key", auth="key", n=1)
        self.connect(keyed)
        helped = self._live("key", auth="login", n=2)
        self.connect(helped)
        return k, keyed, helped

    def test_the_answer_reports_the_set_and_the_rows_come_from_the_cached_set(self):
        k, keyed, helped = self._keyed_and_helped()
        source_fp = self.source().fingerprint()
        runs = es._runs
        code, resp = self._with({"sessions": []})
        self.assertEqual(code, 200, resp)
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["keySource"], "command")
        self.assertEqual((resp["keyFp"], resp["keyKind"]), (es.fingerprint(k), "key"))
        self.assertEqual(resp["sourceFp"], source_fp)
        self.assertNotEqual(resp["keyFp"], resp["sourceFp"], "the credential's fingerprint, not the command text's")
        self.assertEqual(resp["setFp"], es.set_fingerprint(self.values))
        self.assertEqual(resp["selector"], "")
        self.assertEqual(resp["keyErr"], "")
        self.assertEqual(resp["launched"], {es.fingerprint(k): 1, es.fingerprint(self.helper_value): 1})
        self.assertEqual(resp["rows"], [])
        self.assertIsNone(resp["refreshed"])
        self.assertEqual(es._runs, runs, "a status read serves the cached set")
        code, resp = self._with({"all": True, "expectedSourceFp": source_fp})
        self.assertEqual(sorted((r["session"], r["status"], r["from"]) for r in resp["rows"]),
                         [("s1", "current", es.fingerprint(k)), ("s2", "current", es.fingerprint(self.helper_value))])
        self.assertEqual(self.reconnects, [])
        self.assertEqual(es._runs, runs, "the rows compare against the cached set: no run, no resolve")
        # the set's key rotates: the refresh re-runs first, the keyed session moves, the helper-billed one stays
        k2 = fixture_value("key2")
        self.values["ANTHROPIC_API_KEY"] = k2
        self.print_set(self.values)
        code, resp = self._with({"all": True, "refresh": True, "expectedSourceFp": source_fp})
        self.assertEqual(code, 200, resp)
        self.assertEqual(resp["refreshed"], {"from": es.fingerprint(k), "to": es.fingerprint(k2), "err": ""})
        self.assertEqual(resp["keyFp"], es.fingerprint(k2))
        self.assertEqual(resp["sourceFp"], source_fp, "the source did not move; its credential did")
        rows = {r["session"]: r for r in resp["rows"]}
        self.assertEqual((rows["s1"]["status"], rows["s1"]["from"]), ("cycling", es.fingerprint(k)))
        self.assertEqual((rows["s2"]["status"], rows["s2"]["from"]), ("current", es.fingerprint(self.helper_value)))
        self.assertEqual(self.reconnects, [keyed.sid])
        self.assertEqual(es._runs, runs + 1, "the refresh is the one run; the read and the rows use it")
        blob = json.dumps(resp)
        for v in (k, k2, self.helper_value) + tuple(self.values.values()):
            self.assertNotIn(v, blob)

    def test_a_stale_expected_source_is_refused_before_any_row(self):
        k, keyed, helped = self._keyed_and_helped()
        code, resp = self._with({"all": True, "expectedSourceFp": "stale-source"})
        self.assertEqual(code, 409)
        self.assertFalse(resp["ok"])
        self.assertIn("source changed", resp["error"])
        self.assertEqual(self.reconnects, [])

    def test_a_failed_run_rides_the_answer_and_the_rows_stand_on_the_last_good_set(self):
        k, keyed, helped = self._keyed_and_helped()
        self.fail_command("echo 'the store is unreachable' >&2; exit 3")
        code, resp = self._with({"sessions": ["s1"], "refresh": True})
        self.assertEqual(code, 200, resp)
        self.assertTrue(resp["ok"], "a failed run is not a failed request: the last good set stands")
        self.assertIn("exited 3", resp["refreshed"]["err"])
        self.assertEqual((resp["refreshed"]["from"], resp["refreshed"]["to"]), (es.fingerprint(k), es.fingerprint(k)))
        self.assertIn("exited 3", resp["keyErr"])
        self.assertEqual(resp["keyFp"], es.fingerprint(k), "the last good set's key")
        self.assertEqual(resp["rows"], [{"session": "s1", "status": "current", "from": es.fingerprint(k)}])
        self.assertEqual(self.reconnects, [])
        self.assertEqual(len([m for m in self.problems() if m.startswith("credential command: failed")]), 1,
                         "one problem line for the episode, however many readers met it")
        blob = json.dumps(resp) + "\n".join(self.logged) + json.dumps(self.be.problems())
        self.assertNotIn("the store is unreachable", blob, "stderr is a byte count, never quoted")
        self.assertNotIn(k, blob)

    def test_a_removed_source_is_the_base_error_answer(self):
        # the command line gone while the marker says a command governed: keysource's removed-source error,
        # answered the way the base answers an invalid reference (ok False, the error note)
        self.write_command_env(command=False)
        self.reset_sources()
        code, resp = self._with({"sessions": []})
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"])
        self.assertIn("credential command was removed", resp["error"])


if __name__ == "__main__":
    unittest.main()
