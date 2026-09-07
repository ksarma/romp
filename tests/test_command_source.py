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
  ByteIdenticalOutsideTheCommandKind: with no command selected the file-mode launch is the base's
    (the key injected for a keyed launch, the login environment for a login launch, the command
    source never run, nothing about a credential command in the log).
  NothingLeaks: no fixture value reaches a log line, the problem ring or a record, and os.environ is
    unchanged after every reader.

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
        self._env_for(1, "login")
        said = [m for m in self.logged if m.startswith("credential command: sessions now launch with the set")]
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("sha256:" + es.set_fingerprint(self.values), said[0])
        self.assertIn("2 names: ANTHROPIC_LP_API_KEY, A_TOKEN", said[0])
        self.assertIn("no ANTHROPIC_API_KEY in it", said[0])
        for _ in range(3):
            self._env_for(2, "login")
        self.rerun()
        self._env_for(3, "login")
        self.assertEqual(len([m for m in self.logged if "sessions now launch with the set" in m]), 1, "the same set again is not said")
        self.values["A_TOKEN"] = fixture_value("rotated")
        self.print_set(self.values)
        self.rerun()
        self._env_for(4, "login")
        self.assertEqual(len([m for m in self.logged if "sessions now launch with the set" in m]), 2, "a changed set is")
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
        failed = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(failed), 1, self.problems())
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


if __name__ == "__main__":
    unittest.main()
