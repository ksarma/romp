#!/usr/bin/env python3
"""key_source_verdict — the one-shot key-source check at backend construction (2026-09-05), and the
`keySource` block it feeds on /api-health.

The verdict is pure on its inputs (the cli_scope_supported pattern): an environ, the env file's text,
the unit/drop-in/plist texts, the apiKeyHelper command, the command source's value-free first-run
record and two booleans. Every line it returns carries NAMES and fingerprints only. Under test:
  Modes — file vs command from the one switch; sessionKeyPath injected|helper|login.
  FileModeSaysNothingNew — an unset command leaves upstream's log byte for byte: no line for the
    ordinary shapes; a unit credential rings only under a declared auth.
  CommandModeChecks — each check: the first run (ok, failed on the previous set, failed on nothing),
    credential lines in the env file (ignored, the command wins), a startup key (ignored), other
    credential-shaped names in the kernel's environment (informational), credential lines in the
    unit or plist, ExecStart through a shell, login declared while the command prints a key, ROMP_*
    names dropped.
  BothModes — ROMP_EXPECTED_AUTH=key with nothing to inject and no apiKeyHelper rings in command
    mode only (file mode's boot log stays upstream's; its inits report the mismatch).
  Floors — conftest points ROMP_SYSTEMD_DIR, ROMP_LAUNCHD_DIR and CLAUDE_CONFIG_DIR at empty dirs, and
    ROMP_SERVICE_ENV_FILE (both spellings) at a path that does not exist.
  PureOnItsInputs — a hypothetical environ takes its mode from the inputs handed in (its own line, else
    the env-file TEXT), never from the env file this process is configured from: a decoy service.env at
    the default location under a private HOME is not read (2026-09-06).
  UnitParsing — Environment= lines and plist pairs (names only), ExecStart shapes and drop-in
    overrides, the paths _unit_texts reads (bin/romp-service's variables).
  NoValueAnywhere — with fixture values in every input, the verdict's JSON carries none.
  BootAndHealth — the backend runs the verdict once at construction, logs its lines (the problem
    ring for the flagged ones), and api_health_snapshot()["keySource"] carries the documented fields;
    in file mode with nothing declared, no "key source:" line is logged at all. A credential command
    that fails is ONE problem line per failure episode whichever path first runs it — the judges' and
    the catalog's wire (credential_set), a judge's key read (work_api_key), the status report, the
    api-health snapshot, the key cycle — and a later success followed by another failure is a second
    (2026-09-06; before this only the connect, boot and refresh paths said anything). The boot is one
    line per fact: the verdict's line (with the run's detail) is the boot's report of a failure and the
    noter says nothing for it then or for the same failure on the next path (before, two problem lines
    about one failure). The noter orders records by envsource's `attempt`: an older run's record noted
    after a newer one's is ignored, so a thread held between take() and the note cannot say a stale
    failure after the recovery or a stale recovery during a failure. A backend's own readers note on
    that backend; the module-level readers note through the last constructed one, held weakly, so a
    dropped backend is released and receives nothing.

Synthetic throughout: values are "romp-test-fixture-" + a uuid assembled at run time; the fake
command is a script in a temp dir; paths are temp paths.
"""
import gc
import json
import os
import tempfile
import threading
import time
import unittest
import uuid
import weakref
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
_NO_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_ENV
sb = load_source("romp_sdk_backend_ksv", os.path.join(BIN, "romp_sdk_backend.py"))
es = sb._envsrc
ks = sb._keysrc


def fixture_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


def verdict(environ=None, **kw):
    """The pure function on an explicit environ (an empty one unless given) so the developer's shell
    cannot reach it."""
    return sb.key_source_verdict({} if environ is None else environ, **kw)


def texts(v):
    return [ln["text"] for ln in v["lines"]]


def problems(v):
    return [ln["text"] for ln in v["lines"] if ln["problem"]]


CMD = {"ROMP_CREDENTIAL_COMMAND": "credential-cmd --romp \"$1\""}


def ok_snap(**over):
    snap = {"configured": True, "ok": True, "reason": "", "at": 1_700_000_000.5, "exitCode": 0,
            "durationS": 0.412, "timedOut": False, "names": ["ANTHROPIC_LP_API_KEY", "A_TOKEN"],
            "dropped": [], "badLines": 0, "emptyValues": 0, "setFp": "0123456789ab", "keyFp": "",
            "hasKey": False, "stale": False, "runs": 1, "failures": 0, "generation": 0, "selector": "hp"}
    snap.update(over)
    return snap


class Modes(unittest.TestCase):
    def test_the_one_switch_decides_the_mode(self):
        self.assertEqual(verdict()["mode"], "file")
        self.assertEqual(verdict(CMD, snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict({"ROMP_CREDENTIAL_COMMAND": "  "})["mode"], "file", "blank is unset")

    def test_session_key_path(self):
        self.assertEqual(verdict()["sessionKeyPath"], "login")
        self.assertEqual(verdict(helper_command="my-helper")["sessionKeyPath"], "helper")
        self.assertEqual(verdict(work_key_present=True, helper_command="my-helper")["sessionKeyPath"], "injected",
                         "a key to inject outranks a helper: the CLI resolves ANTHROPIC_API_KEY first")
        self.assertEqual(verdict(CMD, snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef"),
                                 work_key_present=True)["sessionKeyPath"], "injected")

    def test_the_shape(self):
        v = verdict(CMD, snapshot=ok_snap(), helper_command="h")
        self.assertEqual(set(v), {"mode", "selector", "sessionKeyPath", "expectedAuth", "helperConfigured",
                                  "execStartShell", "credentialNamesFound", "lastRun", "lines"})
        self.assertEqual(v["selector"], "hp")
        self.assertTrue(v["helperConfigured"])
        self.assertIsNone(v["execStartShell"], "no unit text: unknown")
        self.assertEqual(v["credentialNamesFound"], {"serviceEnv": [], "unit": [], "environment": []})
        self.assertEqual(v["lastRun"], {"ok": True, "at": 1_700_000_000, "reason": "", "exitCode": 0, "durationS": 0.412,
                                        "stale": False, "failures": 0, "lastOkAt": None})
        v = verdict(CMD, snapshot=ok_snap(ok=False, reason="exited 3 after 0.4s, stderr 87 bytes", stale=True,
                                          failures=2, lastOkAt=1_699_999_000.2))
        self.assertEqual(v["lastRun"], {"ok": False, "at": 1_700_000_000, "reason": "exited 3 after 0.4s, stderr 87 bytes",
                                        "exitCode": 0, "durationS": 0.412, "stale": True, "failures": 2,
                                        "lastOkAt": 1_699_999_000}, "a failed run says it stands on the previous set")
        self.assertIsNone(verdict()["lastRun"], "file mode has no command run")
        self.assertEqual(verdict()["selector"], "")
        json.dumps(v)


class FileModeSaysNothingNew(unittest.TestCase):
    def test_the_ordinary_shapes_produce_no_line(self):
        v = fixture_value()
        for kw in (dict(),
                   dict(service_env_text="ANTHROPIC_API_KEY=%s\n" % v),               # the existing check speaks
                   dict(service_env_text="HF_TOKEN=%s\n" % v),
                   dict(environ={"ANTHROPIC_LP_API_KEY": v, "HF_TOKEN": v}),
                   dict(unit_texts=[("unit", "ExecStart=/bin/zsh -lc 'romp-manager up'\n")]),   # a shell ExecStart is file mode's own business
                   dict(unit_texts=[("unit", 'Environment="HF_TOKEN=%s"\n' % v)]),         # undeclared: quiet
                   dict(startup_key_present=True, work_key_present=True)):
            environ = kw.pop("environ", None)
            self.assertEqual(texts(verdict(environ, **kw)), [], kw)

    def test_a_unit_credential_rings_under_a_declaration(self):
        v = fixture_value()
        env = {"ROMP_EXPECTED_AUTH": "login"}
        r = verdict(env, unit_texts=[("the-unit", 'Environment="HF_TOKEN=%s" ROMP_PERF=1\n' % v)])
        self.assertEqual(len(problems(r)), 1)
        self.assertIn("the-unit (HF_TOKEN)", problems(r)[0])
        self.assertIn("ROMP_EXPECTED_AUTH=login", problems(r)[0])
        self.assertNotIn(v, problems(r)[0])
        self.assertEqual(r["credentialNamesFound"]["unit"], ["HF_TOKEN"])
        self.assertEqual(r["expectedAuth"], "login")


class CommandModeChecks(unittest.TestCase):
    def test_a_good_first_run_is_one_informational_line(self):
        r = verdict(CMD, snapshot=ok_snap())
        self.assertEqual(len(r["lines"]), 1)
        self.assertFalse(r["lines"][0]["problem"])
        t = r["lines"][0]["text"]
        self.assertTrue(t.startswith("key source: command (selector hp) — the set is sha256:0123456789ab (2 names: "
                                     "ANTHROPIC_LP_API_KEY, A_TOKEN); no ANTHROPIC_API_KEY in it"), t)
        r = verdict(CMD, snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef", names=["ANTHROPIC_API_KEY"], selector=""))
        t = r["lines"][0]["text"]
        self.assertIn("(1 name: ANTHROPIC_API_KEY)", t)
        self.assertIn("the sessions' key is sha256:abcdefabcdef", t)
        self.assertNotIn("selector", t)

    def test_a_failed_first_run_rings_with_the_reason_and_the_consequence(self):
        r = verdict(CMD, snapshot=ok_snap(ok=False, reason="exited 3 after 0.4s, stderr 87 bytes", names=[], setFp=""))
        self.assertEqual(len(problems(r)), 1)
        self.assertIn("credential command failed — exited 3 after 0.4s, stderr 87 bytes", problems(r)[0])
        self.assertIn("nothing injected", problems(r)[0])
        self.assertIn("romp keyswap --refresh", problems(r)[0])
        self.assertEqual(r["lastRun"]["ok"], False)
        r = verdict(CMD, snapshot=ok_snap(ok=False, reason="timed out after 15s (killed with its process group)", stale=True))
        self.assertIn("last successful run (sha256:0123456789ab)", problems(r)[0])
        self.assertNotIn("nothing injected", problems(r)[0])

    def test_credential_lines_in_the_env_file_are_ignored_and_named(self):
        v = fixture_value()
        r = verdict(CMD, snapshot=ok_snap(), service_env_text="ROMP_PERF=1\nANTHROPIC_API_KEY=%s\nHF_TOKEN='%s'\n" % (v, v))
        line = [t for t in problems(r) if "credential lines" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn(ks.service_env_path(), line[0])
        self.assertIn("ANTHROPIC_API_KEY, HF_TOKEN", line[0])
        self.assertIn("the command wins", line[0])
        self.assertIn("remove them and rotate the values", line[0])
        self.assertNotIn(v, line[0])
        self.assertEqual(r["credentialNamesFound"]["serviceEnv"], ["ANTHROPIC_API_KEY", "HF_TOKEN"])
        r = verdict(CMD, snapshot=ok_snap(), service_env_text="ANTHROPIC_API_KEY=%s\n" % v)
        self.assertIn("credential line —", [t for t in problems(r) if "credential line" in t][0])
        self.assertIn("remove it and rotate the value", [t for t in problems(r) if "credential line" in t][0])

    def test_a_startup_key_is_ignored_and_named(self):
        r = verdict(CMD, snapshot=ok_snap(), startup_key_present=True)
        line = [t for t in problems(r) if "manager's own environment is ignored" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("ANTHROPIC_API_KEY", line[0])
        self.assertIn("rotate it", line[0])
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_API_KEY"])

    def test_other_credential_names_in_the_kernels_environment_are_informational(self):
        v = fixture_value()
        env = dict(CMD, ANTHROPIC_LP_API_KEY=v, HF_TOKEN=v, ROMP_SERVE_TOKEN=v, EMPTY_TOKEN="", NOT_A_SECRET=v)
        r = verdict(env, snapshot=ok_snap())
        info = [ln for ln in r["lines"] if "kernel's own environment" in ln["text"]]
        self.assertEqual(len(info), 1)
        self.assertFalse(info[0]["problem"], "a frozen copy the sessions do not get: worth knowing, not a fault")
        self.assertIn("ANTHROPIC_LP_API_KEY, HF_TOKEN", info[0]["text"])
        self.assertNotIn("ROMP_SERVE_TOKEN", info[0]["text"], "romp's own serve token is exempt")
        self.assertNotIn("EMPTY_TOKEN", info[0]["text"])
        self.assertNotIn(v, info[0]["text"])
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_LP_API_KEY", "HF_TOKEN"])

    def test_credential_lines_in_the_unit_or_plist_ring(self):
        v = fixture_value()
        unit = 'Environment="ANTHROPIC_API_KEY=%s" "ROMP_PERF=1"\n' % v
        plist = ("<key>EnvironmentVariables</key><dict><key>HF_TOKEN</key><string>%s</string>"
                 "<key>ROMP_DIR</key><string>/x</string></dict>" % v)
        r = verdict(CMD, snapshot=ok_snap(), unit_texts=[("a.service", unit), ("b.plist", plist)])
        line = [t for t in problems(r) if "service definition carries" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("a.service (ANTHROPIC_API_KEY); b.plist (HF_TOKEN)", line[0])
        self.assertNotIn(v, line[0])
        self.assertEqual(r["credentialNamesFound"]["unit"], ["ANTHROPIC_API_KEY", "HF_TOKEN"])

    def test_an_exec_start_through_a_shell_rings(self):
        r = verdict(CMD, snapshot=ok_snap(), unit_texts=[("u", "ExecStart=/bin/zsh -lc '%h/.local/bin/romp-manager up'\n")])
        self.assertTrue(r["execStartShell"])
        line = [t for t in problems(r) if "ExecStart runs the manager through a shell" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("freeze until a manager restart", line[0])
        r = verdict(CMD, snapshot=ok_snap(), unit_texts=[("u", "ExecStart=%h/.local/bin/romp-manager up\n")])
        self.assertFalse(r["execStartShell"])
        self.assertEqual([t for t in problems(r) if "through a shell" in t], [])

    def test_login_declared_while_the_command_prints_a_key_rings(self):
        env = dict(CMD, ROMP_EXPECTED_AUTH="login")
        r = verdict(env, snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef"))
        line = [t for t in problems(r) if "ROMP_EXPECTED_AUTH=login while" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("sha256:abcdefabcdef", line[0])
        self.assertIn("bill the key", line[0])
        self.assertEqual([t for t in problems(verdict(env, snapshot=ok_snap())) if "while" in t], [],
                         "no key printed: the declaration holds")

    def test_dropped_romp_names_ring_by_name(self):
        r = verdict(CMD, snapshot=ok_snap(dropped=["ROMP_SID", "ROMP_STATE_DIR"]))
        line = [t for t in problems(r) if "ROMP_* variables" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("(ROMP_SID, ROMP_STATE_DIR)", line[0])
        self.assertIn("dropped from the set", line[0])

    def test_dropped_cli_auth_names_ring_by_name(self):
        r = verdict(CMD, snapshot=ok_snap(droppedAuth=["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"]))
        line = [t for t in problems(r) if "authentication or endpoint" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn("ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL — names the CLI reads", line[0])
        self.assertIn("dropped from the set", line[0])
        r = verdict(CMD, snapshot=ok_snap(droppedAuth=["CLAUDE_CODE_OAUTH_TOKEN"]))
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN — a name the CLI reads", [t for t in problems(r) if "endpoint" in t][0])
        self.assertEqual([t for t in problems(verdict(CMD, snapshot=ok_snap())) if "endpoint" in t], [])

    def test_an_unconfigured_snapshot_in_command_mode_produces_no_run_line(self):
        r = verdict(CMD, snapshot=None)
        self.assertEqual([t for t in texts(r) if "the set is" in t or "failed" in t], [])
        self.assertEqual(r["lastRun"], {"ok": None, "at": None, "reason": "", "exitCode": None, "durationS": None,
                                        "stale": False, "failures": 0, "lastOkAt": None})

    def test_an_undeclared_selector_is_rendered_by_length_and_a_bad_timeout_rings(self):
        r = verdict(CMD, snapshot=ok_snap(selector="", selectorNote="(undeclared, 5 chars)"))
        self.assertEqual(r["selector"], "(undeclared, 5 chars)")
        self.assertIn("key source: command (selector undeclared, 5 chars) — the set is", r["lines"][0]["text"])
        r = verdict(CMD, snapshot=ok_snap(timeoutProblem="ROMP_CREDENTIAL_TIMEOUT_S is not a number of seconds between 0 and 300; the default 15s holds"))
        line = [t for t in problems(r) if "ROMP_CREDENTIAL_TIMEOUT_S" in t]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith("key source: ROMP_CREDENTIAL_TIMEOUT_S is not a number"), line[0])


class BothModes(unittest.TestCase):
    def test_key_declared_with_nothing_to_inject_and_no_helper_rings_in_command_mode_only(self):
        env = dict(CMD, ROMP_EXPECTED_AUTH="key")
        r = verdict(env, snapshot=ok_snap())
        line = [t for t in problems(r) if "names no apiKeyHelper" in t]
        self.assertEqual(len(line), 1, texts(r))
        self.assertIn("ROMP_EXPECTED_AUTH=key", line[0])
        self.assertIn("land on the login", line[0])
        self.assertIn("the credential command prints no ANTHROPIC_API_KEY", line[0])
        self.assertEqual([t for t in problems(verdict(env, helper_command="h", snapshot=ok_snap())) if "apiKeyHelper" in t],
                         [], "a helper answers the declaration")
        self.assertEqual([t for t in problems(verdict(env, work_key_present=True, snapshot=ok_snap())) if "apiKeyHelper" in t],
                         [], "so does a key to inject")
        # file mode: the boot log stays upstream's — every session init already reports the
        # declared-vs-live mismatch, so the verdict adds no line here
        self.assertEqual(texts(verdict({"ROMP_EXPECTED_AUTH": "key"})), [])
        self.assertEqual(texts(verdict({"ROMP_EXPECTED_AUTH": "key"}, helper_command="")), [])

    def test_the_declaration_is_read_from_the_given_environ(self):
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": " Login "})["expectedAuth"], "login")
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": "both"})["expectedAuth"], "")
        self.assertEqual(verdict()["expectedAuth"], "")


class Floors(unittest.TestCase):
    """conftest's floor (2026-09-05): every backend construction reads the unit, the plist and the
    Claude Code settings through these three variables, and no test may read this machine's."""

    def test_the_three_directories_are_floored_to_empty_temp_dirs(self):
        home = os.path.expanduser("~")
        real = {os.path.join(home, ".config", "systemd", "user"), os.path.join(home, "Library", "LaunchAgents"),
                os.path.join(home, ".claude")}
        for var in ("ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR", "CLAUDE_CONFIG_DIR"):
            d = os.environ.get(var) or ""
            self.assertTrue(os.path.basename(d).startswith("floor-"), "%s is not conftest's floor directory" % var)
            self.assertTrue(os.path.isdir(d), "%s does not point at a directory" % var)
            self.assertFalse(os.path.realpath(d) in real, "%s points at this machine's real location" % var)
        self.assertEqual(sb._unit_texts(), [], "no unit, no drop-in, no plist")
        self.assertEqual(es.helper_command(), "", "no settings.json, no apiKeyHelper")
        self.assertEqual(es.claude_config_dir(), os.environ["CLAUDE_CONFIG_DIR"])
        self.assertTrue(os.environ.get("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR"),
                        "the one live test that borrows the user's helper command has a way to the real location")

    def test_the_env_file_is_floored_to_a_path_that_does_not_exist(self):
        # both spellings keysource accepts, one path, absent — so every read is the "no file" case and no
        # test resolves this machine's service.env (its default lives under HOME)
        default = os.path.realpath(os.path.join(os.path.expanduser("~"), ".config", "romp", "service.env"))
        for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
            p = os.environ.get(var) or ""
            self.assertTrue(p, "%s is not floored" % var)
            self.assertFalse(os.path.exists(p), "%s points at a file that exists" % var)
            self.assertNotEqual(os.path.realpath(p), default, "%s points at this machine's default env file" % var)
        self.assertEqual(os.environ["ROMP_SERVICE_ENV_FILE"], os.environ["ROMP_SERVICE_ENV"])
        self.assertEqual(ks.service_env_path(), os.environ["ROMP_SERVICE_ENV_FILE"])
        self.assertEqual(es.command(), "", "no file: no command line read from one")


class PureOnItsInputs(unittest.TestCase):
    """key_source_verdict on a HYPOTHETICAL environ decides its mode from the inputs it is handed — the
    environ's own ROMP_CREDENTIAL_COMMAND, else the line in `service_env_text` — and never from the env
    file this process is configured from. envsource's readers keep the process's file as their fallback
    whatever environ they are given (`es.command({})` is the file's line alone: keyswap's probe for a
    line set in the file rather than the shell), so the verdict does not route a hypothetical through
    them. Proven against a decoy: a service.env at the DEFAULT location under a private HOME, the
    conftest floor lifted for the test, so the decoy is exactly the file this process would read."""

    VARS = ("HOME", "XDG_CONFIG_HOME", "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ROMP_CREDENTIAL_COMMAND")

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in self.VARS}
        es._reset()

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def test_a_decoy_env_file_at_the_default_location_is_not_read_for_a_hypothetical_environ(self):
        os.environ["HOME"] = self.d
        for v in self.VARS[1:]:
            os.environ.pop(v, None)
        decoy = os.path.join(self.d, ".config", "romp", "service.env")
        os.makedirs(os.path.dirname(decoy))
        with open(decoy, "w") as fh:
            fh.write('ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=decoy-command "$1"\n')
        es._reset()
        # the setup, proven: the decoy IS the file this process resolves and reads
        self.assertEqual(ks.service_env_path(), decoy)
        self.assertEqual(es.command(), 'decoy-command "$1"', "the process's own read takes the file's line")
        self.assertEqual(es.command({}), 'decoy-command "$1"',
                         "an explicit environ replaces the environment, not the file: the file-only probe keyswap uses")
        # the property: a hypothetical environ is file mode — the decoy was not consulted
        v = verdict({})
        self.assertEqual(v["mode"], "file")
        self.assertIsNone(v["lastRun"])
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": "key"})["mode"], "file")
        self.assertEqual(verdict({"ROMP_CREDENTIAL_COMMAND": "  "})["mode"], "file", "blank is unset")
        # the inputs decide: the environ's own line, else the env-file TEXT handed in — the boot's rule
        self.assertEqual(verdict(CMD, snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict({}, service_env_text='ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND="x $1"\n',
                                 snapshot=ok_snap())["mode"], "command", "the file's TEXT is an input; the line in it selects")
        self.assertEqual(verdict({}, service_env_text="ROMP_CREDENTIAL_COMMAND=\n")["mode"], "file",
                         "an empty assignment is no command, as in the file itself")
        # the process's own environment (None) keeps the boot's read: its file decides
        self.assertEqual(sb.key_source_verdict(None, snapshot=ok_snap())["mode"], "command")


class UnitParsing(unittest.TestCase):
    def test_environment_lines_and_plist_pairs_names_only(self):
        v = fixture_value()
        text = ('Environment="A_API_KEY=%s" B_TOKEN=%s NOT_ONE=%s\n'
                "Environment=EMPTY_TOKEN=\n"
                "Environment='C_TOKEN=%s'\n"
                "Environment=A_API_KEY=%s\n" % (v, v, v, v, v))
        self.assertEqual(sb._unit_credential_names(text), ["A_API_KEY", "B_TOKEN", "C_TOKEN"])
        plist = ("<key>D_TOKEN</key>\n  <string>%s</string><key>E_API_KEY</key><string></string>"
                 "<key>ROMP_DIR</key><string>/tmp/x</string>" % v)
        self.assertEqual(sb._unit_credential_names(plist), ["D_TOKEN"])
        self.assertEqual(sb._unit_credential_names('Environment="X_TOKEN=%s\n' % v), ["X_TOKEN"],
                         "an unbalanced quote falls back to a plain split, and the name still reads clean")
        self.assertEqual(sb._unit_credential_names(""), [])

    def test_exec_start_shapes(self):
        shell = sb._exec_start_shell
        self.assertIsNone(shell([]))
        self.assertIsNone(shell([("", "[Service]\nType=simple\n")]))
        self.assertTrue(shell(["ExecStart=/bin/zsh -lc 'romp-manager up'\n"]))
        self.assertTrue(shell(["ExecStart=-/usr/bin/bash -c romp-manager\n"]), "a leading prefix character is not the program")
        self.assertTrue(shell(["ExecStart=/usr/bin/env bash -lc 'x'\n"]))
        self.assertTrue(shell(["ExecStart=/usr/bin/env FOO=1 sh -c 'x'\n"]))
        self.assertFalse(shell(["ExecStart=/usr/bin/env node manager.js\n"]))
        self.assertFalse(shell(["ExecStart=%h/.local/bin/romp-manager up\n"]))
        self.assertFalse(shell(["ExecStart=/bin/zsh -lc x\n", "ExecStart=\nExecStart=/usr/bin/romp-manager up\n"]),
                         "a drop-in's reset-and-override wins over the unit")
        self.assertTrue(shell(["ExecStart=/usr/bin/romp-manager up\n", "ExecStart=\nExecStart=/bin/sh -c x\n"]))
        plist = "<key>ProgramArguments</key>\n<array>\n  <string>/bin/zsh</string>\n  <string>-lc</string>\n</array>"
        self.assertTrue(shell([plist]))
        self.assertFalse(shell(["<key>ProgramArguments</key><array><string>/usr/local/bin/romp-manager</string></array>"]))

    def test_unit_texts_reads_the_installers_paths(self):
        d = tempfile.mkdtemp()
        sysd = os.path.join(d, "sysd")
        os.makedirs(os.path.join(sysd, "romp-manager.service.d"))
        with open(os.path.join(sysd, "romp-manager.service"), "w") as fh:
            fh.write("[Service]\nExecStart=/usr/bin/romp-manager up\n")
        with open(os.path.join(sysd, "romp-manager.service.d", "20-b.conf"), "w") as fh:
            fh.write("[Service]\nExecStart=\nExecStart=/bin/zsh -lc x\n")
        with open(os.path.join(sysd, "romp-manager.service.d", "10-a.conf"), "w") as fh:
            fh.write("[Service]\nEnvironment=ROMP_PERF=1\n")
        with open(os.path.join(sysd, "romp-manager.service.d", "notes.txt"), "w") as fh:
            fh.write("not a drop-in\n")
        lag = os.path.join(d, "agents")
        os.makedirs(lag)
        with open(os.path.join(lag, "com.romp.manager.plist"), "w") as fh:
            fh.write("<plist/>")
        got = sb._unit_texts({"ROMP_SYSTEMD_DIR": sysd, "ROMP_LAUNCHD_DIR": lag})
        self.assertEqual([os.path.basename(p) for p, _t in got],
                         ["romp-manager.service", "10-a.conf", "20-b.conf", "com.romp.manager.plist"],
                         "the unit, its .conf drop-ins in sorted order, the plist; nothing else")
        self.assertTrue(sb._exec_start_shell([t for _p, t in got]), "the later drop-in's override is what runs")
        xdg = os.path.join(d, "xdg")
        os.makedirs(os.path.join(xdg, "systemd", "user"))
        with open(os.path.join(xdg, "systemd", "user", "romp-manager.service"), "w") as fh:
            fh.write("[Service]\n")
        got = sb._unit_texts({"XDG_CONFIG_HOME": xdg, "ROMP_LAUNCHD_DIR": os.path.join(d, "absent")})
        self.assertEqual([os.path.basename(p) for p, _t in got], ["romp-manager.service"])
        self.assertEqual(sb._unit_texts({"ROMP_SYSTEMD_DIR": os.path.join(d, "nope"),
                                         "ROMP_LAUNCHD_DIR": os.path.join(d, "nope")}), [])


class NoValueAnywhere(unittest.TestCase):
    def test_fixture_values_in_every_input_reach_no_output(self):
        v = [fixture_value(str(i)) for i in range(6)]
        env = dict(CMD, ANTHROPIC_API_KEY=v[0], ANTHROPIC_LP_API_KEY=v[1], HF_TOKEN=v[2], ROMP_EXPECTED_AUTH="login")
        r = verdict(env, service_env_text="ANTHROPIC_API_KEY=%s\nX_TOKEN=%s\n" % (v[3], v[4]),
                    unit_texts=[("u", 'Environment="Y_API_KEY=%s"\nExecStart=/bin/zsh -lc x\n' % v[5]),
                                ("p", "<key>Z_TOKEN</key><string>%s</string>" % v[5])],
                    helper_command="helper " + v[2],
                    snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef", dropped=["ROMP_X"]),
                    work_key_present=True, startup_key_present=True)
        blob = json.dumps(r)
        for x in v:
            self.assertNotIn(x, blob)
        self.assertNotIn("fixture", blob)
        self.assertGreaterEqual(len(problems(r)), 6, texts(r))


class BootAndHealth(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR", "ROMP_EXPECTED_AUTH",
                                                                         "ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR",
                                                                         "ANTHROPIC_API_KEY")}
        for v in self._before:
            os.environ.pop(v, None)
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.d, "claude")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.d, "selector")
        os.environ["ROMP_SYSTEMD_DIR"] = os.path.join(self.d, "sysd")
        os.environ["ROMP_LAUNCHD_DIR"] = os.path.join(self.d, "agents")
        self._stash, self._checked = sb._WORK_KEY, sb._KEY_FILE_CHECKED
        sb._WORK_KEY, sb._KEY_FILE_CHECKED = "", True
        self._fetch = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None
        es._reset()
        self.logged = []

    def tearDown(self):
        sb._WORK_KEY, sb._KEY_FILE_CHECKED = self._stash, self._checked
        sb._fetch_key_fast_org = self._fetch
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def construct(self):
        return sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def command(self, values, body=""):
        p = os.path.join(self.d, "cmd.sh")
        with open(p, "w") as fh:
            fh.write("#!/bin/sh\n" + (body + "\n" if body else "") + "".join("echo '%s=%s'\n" % kv for kv in values.items()))
        os.chmod(p, 0o700)
        os.environ["ROMP_CREDENTIAL_COMMAND"] = p + ' "$1"'

    def test_file_mode_with_nothing_declared_logs_no_key_source_line(self):
        be = self.construct()
        self.assertEqual([m for m in self.logged if m.startswith("key source:")], [])
        self.assertEqual(be.key_source["mode"], "file")
        self.assertEqual(be.key_source["sessionKeyPath"], "login")
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["mode"], "file")
        self.assertIsNone(snap["lastRun"])
        self.assertEqual(snap["fingerprint"], "")
        self.assertEqual(snap["fingerprintKind"], "")
        self.assertEqual(snap["setFingerprint"], "")
        self.assertEqual(snap["names"], [])
        self.assertEqual(snap["sessionsByFingerprint"], {})
        self.assertEqual(set(snap), {"mode", "selector", "sessionKeyPath", "expectedAuth", "helperConfigured",
                                     "execStartShell", "credentialNamesFound", "lastRun", "fingerprint",
                                     "fingerprintKind", "setFingerprint", "names", "sessionsByFingerprint"})
        self.assertNotIn("lines", snap)
        self.assertEqual(sb.API_HEALTH_SCHEMA, 1, "additive: the schema does not move")

    def test_command_mode_runs_the_verdict_once_at_construction_and_logs_its_lines(self):
        v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": v, "ROMP_SID": "x"})
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        be = self.construct()
        self.assertEqual(es._runs, 1, "the verdict's run is the first run, before any launch")
        heads = [m.split(" — ")[0] for m in self.logged if m.startswith("key source:")]
        self.assertIn("key source: command", heads)
        probs = [p["text"] for p in be.problems()]
        self.assertTrue(any("ROMP_* variable" in t and "(ROMP_SID)" in t for t in probs), probs)
        self.assertTrue(any("names no apiKeyHelper" in t for t in probs), probs)
        self.assertFalse(any(m.startswith("key source: command") for m in probs), "the info line is not a problem")
        self.assertEqual(be.key_source["mode"], "command")
        self.assertEqual(be.key_source["expectedAuth"], "key")
        self.assertEqual(be.key_source["lastRun"]["ok"], True)
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["names"], ["ANTHROPIC_LP_API_KEY"])
        self.assertEqual(snap["setFingerprint"], es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v}))
        self.assertEqual(snap["sessionKeyPath"], "login")
        self.assertNotIn(v, json.dumps(snap))
        self.assertNotIn(v, "\n".join(self.logged))

    def test_the_unit_and_plist_are_read_from_the_installers_paths_at_boot(self):
        v = fixture_value()
        self.command({"A_TOKEN": v})
        os.makedirs(os.environ["ROMP_SYSTEMD_DIR"])
        with open(os.path.join(os.environ["ROMP_SYSTEMD_DIR"], "romp-manager.service"), "w") as fh:
            fh.write("[Service]\nExecStart=/bin/zsh -lc 'romp-manager up'\nEnvironment=\"HF_TOKEN=%s\"\n" % v)
        be = self.construct()
        self.assertTrue(be.key_source["execStartShell"])
        self.assertEqual(be.key_source["credentialNamesFound"]["unit"], ["HF_TOKEN"])
        probs = [p["text"] for p in be.problems()]
        self.assertTrue(any("through a shell" in t for t in probs), probs)
        self.assertTrue(any("service definition carries" in t and "(HF_TOKEN)" in t for t in probs), probs)
        self.assertNotIn(v, json.dumps(probs))

    def test_the_mode_is_pinned_at_construction(self):
        # a service.env edit that removes the line does not flip a running kernel: the sessions it
        # launches, its judges and its catalog fetch stay on one key source until `romp refresh`
        v = fixture_value()
        self.command({"A_TOKEN": v})
        be = self.construct()
        self.assertEqual(be.key_source["mode"], "command")
        os.environ.pop("ROMP_CREDENTIAL_COMMAND")
        self.assertEqual(be.key_source_mode(), "command", "the boot mode holds")
        be.refresh_key_source()
        st = be.key_source_status()
        self.assertEqual(st["source"], "command")
        self.assertIn("ROMP_CREDENTIAL_COMMAND is no longer set", st["err"])
        self.assertTrue(any("ROMP_CREDENTIAL_COMMAND is no longer set" in p["text"] and "romp refresh" in p["text"]
                            for p in be.problems()), [p["text"] for p in be.problems()])
        self.assertEqual(be.api_health_snapshot()["keySource"]["mode"], "command")
        self.assertTrue(be.api_health_snapshot()["keySource"]["lastRun"]["stale"])
        # …and the other way: a kernel that booted in file mode ignores a command that appears later
        es._reset()
        self.logged.clear()
        be = self.construct()
        self.assertEqual(be.key_source["mode"], "file")
        self.command({"A_TOKEN": v})
        self.assertEqual(be.key_source_mode(), "file")
        self.assertEqual(es._runs, 0, "nothing runs in a kernel pinned to file mode")
        self.assertEqual(be.api_health_snapshot()["keySource"]["mode"], "file")

    def construct_with_a_raising_verdict(self):
        """A backend whose boot verdict raises after the command has run (the unit read throws): the
        verdict is a logged problem, not a failed construction."""
        saved = sb._unit_texts
        sb._unit_texts = lambda environ=None: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            be = self.construct()
        finally:
            sb._unit_texts = saved
        self.assertEqual(be.key_source, {"mode": "command", "lines": []})
        self.assertEqual(es._runs, 1, "the command ran before the verdict broke")
        self.assertTrue(any("boot verdict failed" in p["text"] for p in be.problems()), be.problems())
        return be

    def test_a_verdict_that_cannot_be_taken_is_a_logged_problem_not_a_failed_construction(self):
        self.command({"A_TOKEN": fixture_value()})
        be = self.construct_with_a_raising_verdict()
        self.assertEqual(be.api_health_snapshot()["keySource"]["mode"], "command")

    def test_a_verdict_that_cannot_be_taken_leaves_the_run_for_the_next_path_to_say_once(self):
        # the verdict's lines are the boot's report of the first run, and it hands the record to the noter
        # as reported only once they are logged. A verdict that raised logged nothing about the run, so it
        # primes nothing: the guards stay unset, the noter is registered all the same, and the next path to
        # read the set — a module-level reader or one of the backend's own — says the run, once. Were the
        # record handed over before the verdict computed (a natural way to shrink the boot's window), a
        # failing command met at a broken verdict would never be said on any path.
        self.command({"A_TOKEN": fixture_value()})
        self.failing(3)
        be = self.construct_with_a_raising_verdict()
        self.assertEqual(self.about_failure(be), [], "nothing about the run at boot: the verdict never got to it")
        self.assertEqual(be._cred_noted_attempt, -1, "the guards are not primed")
        self.assertIsNone(be._cred_err_said)
        self.assertIs(sb._credential_noter().__self__, be, "the noter is registered whatever the verdict did")
        sb.credential_set()                                   # the judges' and the catalog's wire: the next path
        lines = self.failed_lines(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn("exited 3", lines[0])
        be.api_health_snapshot()
        be.key_source_status()
        sb.credential_set()
        self.assertEqual(len(self.about_failure(be)), 1, "one line for the episode, however many paths met it")
        # and a working set: the next path says the set, once, and nothing before it
        es._reset()
        self.logged.clear()
        v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": v})
        be = self.construct_with_a_raising_verdict()
        fp = es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v})
        self.assertEqual([m for m in self.logged if "sha256:%s" % fp in m], [], "the boot said nothing of the set")
        self.assertEqual(be._cred_fp_said, None)
        be.api_health_snapshot()                              # one of the backend's own readers
        set_lines = [m for m in self.logged if m.startswith("credential command: sessions now launch with the set")]
        self.assertEqual(len(set_lines), 1, self.logged)
        self.assertIn("sha256:%s" % fp, set_lines[0])
        sb.credential_set()
        be.key_source_status()
        self.assertEqual(len([m for m in self.logged if m.startswith("credential command:")]), 1)
        self.assertEqual(es._runs, 1, "a working set is served from the cache: one run for every path")
        self.assertNotIn(v, "\n".join(self.logged) + json.dumps(be.problems()))

    # -- a failed run is one problem line per episode, whichever path first runs the command -------------

    def failing(self, code, body=""):
        """The configured command now exits `code` (its stderr is a fixed line: a byte count, never quoted);
        `body` runs first (a `sleep`, for a run that must still be in flight when something else happens)."""
        with open(os.path.join(self.d, "cmd.sh"), "w") as fh:
            fh.write("#!/bin/sh\n" + (body + "\n" if body else "") + "echo 'the store is unreachable' >&2\nexit %d\n" % code)

    def failed_lines(self, be):
        return [p["text"] for p in be.problems() if p["text"].startswith("credential command: failed")]

    def boot_ok(self):
        """A backend booted on a WORKING command (one run, no failure said), and the store then broken: the
        refusal a judge call reports (credential_invalidate, the judges' wire) makes the cached set stale,
        so the next reader — whichever path — runs the command and meets the failure first."""
        self.v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        be = self.construct()
        self.assertEqual(es._runs, 1)
        self.assertEqual(self.failed_lines(be), [])
        self.failing(3)
        self.assertTrue(sb.credential_invalidate("HTTP 401 on a judge call"))
        self.assertEqual(es._runs, 1, "invalidation runs nothing by itself")
        return be

    def test_a_failure_first_seen_through_the_judges_and_catalogs_wire_is_one_problem_line_per_episode(self):
        be = self.boot_ok()
        vals = sb.credential_set()                       # jd._ENV_SET_FN: a judge envelope, the catalog fetch
        self.assertEqual(es._runs, 2, "the stale set is re-read: the command ran, on this path")
        self.assertEqual(vals, {"ANTHROPIC_LP_API_KEY": self.v}, "a failed run stands on the previous set")
        lines = self.failed_lines(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn("exited 3", lines[0])
        self.assertIn("last successful run (sha256:%s)" % es.set_fingerprint(vals), lines[0])
        # the same failure again, on every path that reads the set: no second line
        sb.credential_set()
        sb.credential_set()
        self.assertEqual(es._runs, 4, "one run per caller after a failure — and one line for all of them")
        self.assertEqual(sb.work_api_key(), "", "a judge's key read: the set carries no ANTHROPIC_API_KEY")
        st = be.key_source_status()
        self.assertIn("exited 3", st["err"])
        health = be.api_health_snapshot()["keySource"]["lastRun"]
        self.assertFalse(health["ok"])
        self.assertTrue(health["stale"])
        self.assertGreaterEqual(es._runs, 7)
        self.assertEqual(len(self.failed_lines(be)), 1, "the episode is one line however many paths met it")
        # the recovery ends the episode: an info line, not a problem
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        self.assertEqual(sb.credential_set(), {"ANTHROPIC_LP_API_KEY": self.v})
        self.assertEqual(len([m for m in self.logged if m.startswith("credential command: succeeded again")]), 1)
        self.assertEqual(len(self.failed_lines(be)), 1)
        # a later failure is a second episode: a second line. The served call re-arms the once-per-credential
        # refusal path (jd._ENV_OK_FN), the next refusal invalidates, the next read meets the new failure
        self.assertTrue(sb.credential_auth_ok(""))
        self.assertTrue(sb.credential_invalidate("HTTP 401 on a judge call"))
        self.failing(4)
        sb.credential_set()
        lines = self.failed_lines(be)
        self.assertEqual(len(lines), 2, be.problems())
        self.assertIn("exited 4", lines[1])
        sb.credential_set()
        self.assertEqual(len(self.failed_lines(be)), 2)
        blob = json.dumps(be.problems()) + "\n".join(self.logged)
        self.assertNotIn(self.v, blob)
        self.assertNotIn("the store is unreachable", blob, "the command's stderr is a byte count, never quoted")

    def test_a_failure_first_seen_by_the_status_report_or_the_health_snapshot_is_said_once(self):
        be = self.boot_ok()
        be.key_source_status()
        self.assertEqual(es._runs, 2)
        self.assertEqual(len(self.failed_lines(be)), 1)
        be.api_health_snapshot()
        be.key_source_status()
        self.assertEqual(len(self.failed_lines(be)), 1)

    def test_a_failure_first_seen_by_the_key_cycle_is_said_once(self):
        be = self.boot_ok()
        sid = "11111111-2222-3333-4444-000000000021"
        reg = {"sid": sid, "name": "web", "cwd": "/tmp", "auth": "login"}
        sb.write_reg(be.state_dir, sid, reg)                 # owned; a live session object, no CLI
        s = sb.SdkSession(be, reg)
        s.auth_live = "login"
        s._launched_set_fp = ""                              # launched with no role variables: the cycle has a reason
        reconnects = []
        s.request_reconnect = lambda defer=True: reconnects.append(defer)
        be.sessions[sid] = s
        self.assertEqual(be.cycle_key(sid), "cycling")
        self.assertEqual(reconnects, [False])
        self.assertEqual(es._runs, 2, "one read of the set for the whole compare")
        self.assertEqual(len(self.failed_lines(be)), 1, be.problems())
        self.assertEqual(be.cycle_key(sid), "cycling")
        self.assertEqual(len(self.failed_lines(be)), 1)

    # -- the boot is one line per fact; the noter orders records; a backend's own readers note on it --------

    def about_failure(self, be):
        """Every problem line about the command having failed, whichever mechanism wrote it."""
        return [p["text"] for p in be.problems() if "credential command" in p["text"] and "failed" in p["text"]]

    def test_a_boot_on_a_failing_command_is_one_problem_line_and_the_episode_is_primed(self):
        # the verdict's line carries the run's detail (duration, stderr bytes); it is the boot's one report,
        # and the noter, handed the record as reported, says nothing at boot and nothing for the same
        # failure on the next path. Before: the noter's line and the verdict's, two entries for one failure.
        self.command({"A_TOKEN": fixture_value()})
        self.failing(3)
        be = self.construct()
        self.assertEqual(es._runs, 1, "one run at boot: the record itself answers whether a key is injected")
        about = self.about_failure(be)
        self.assertEqual(len(about), 1, be.problems())
        self.assertTrue(about[0].startswith("key source: the credential command failed — exited 3 after "), about[0])
        self.assertIn("nothing injected", about[0])
        self.assertEqual(self.failed_lines(be), [], "the noter's line is not a second entry")
        self.assertEqual(be.key_source["sessionKeyPath"], "login")
        self.assertEqual(be.key_source["lastRun"]["ok"], False)
        # the same failure met next on the judges' wire, the status report and a connect: no more entries
        sb.credential_set()
        be.key_source_status()
        be._work_key_and_source()
        self.assertGreaterEqual(es._runs, 4, "each caller after a failed run re-runs")
        self.assertEqual(len(self.about_failure(be)), 1)
        # the recovery ends the episode the boot opened
        v = fixture_value()
        self.command({"A_TOKEN": v})
        self.assertEqual(sb.credential_set(), {"A_TOKEN": v})
        self.assertEqual(len([m for m in self.logged if m.startswith("credential command: succeeded again")]), 1)
        # a failure of another kind after it is a new episode: the noter's one line
        es.invalidate("the store breaks again")
        self.failing(4)
        sb.credential_set()
        lines = self.failed_lines(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn("exited 4", lines[0])
        self.assertEqual(len(self.about_failure(be)), 2, "the boot's and the new episode's")
        self.assertNotIn("the store is unreachable", json.dumps(be.problems()) + "\n".join(self.logged))

    def test_a_working_boot_reports_the_set_once_and_the_noter_speaks_only_on_a_change(self):
        v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": v, "ROMP_SID": "x"})
        be = self.construct()
        fp = es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v})
        set_lines = [m for m in self.logged if "sha256:%s" % fp in m]
        self.assertEqual(len(set_lines), 1, self.logged)
        self.assertTrue(set_lines[0].startswith("key source: command"), set_lines[0])
        dropped = [p["text"] for p in be.problems() if "(ROMP_SID)" in p["text"]]
        self.assertEqual(len(dropped), 1, be.problems())
        self.assertTrue(dropped[0].startswith("key source:"), dropped[0])
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [],
                         "the noter says nothing at boot: the verdict's lines are the report")
        # the same set on every later path is nothing; another set is the noter's change line, once
        sb.credential_set()
        be.key_source_status()
        be.api_health_snapshot()
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [])
        w = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": w, "ROMP_SID": "x"})
        es.invalidate("a rotation")
        sb.credential_set()
        change = [m for m in self.logged if m.startswith("credential command: sessions now launch with the set")]
        self.assertEqual(len(change), 1, self.logged)
        self.assertIn("sha256:%s" % es.set_fingerprint({"ANTHROPIC_LP_API_KEY": w}), change[0])
        self.assertEqual(len([p["text"] for p in be.problems() if "(ROMP_SID)" in p["text"]]), 1,
                         "the same dropped list, primed at boot, is not said again")
        self.assertNotIn(v, "\n".join(self.logged))
        self.assertNotIn(w, "\n".join(self.logged))

    def test_a_reader_during_construction_does_not_double_the_boots_report(self):
        # the kernel starts the model-catalog thread right before it constructs the backend, and that
        # thread's first act is credential_set(): a module-level read whose take() coalesces with the boot
        # verdict's on the command's one run, so both return when the command exits. The noter is
        # registered only AFTER the verdict has logged its lines and primed the guards, so the reader's
        # record reaches either no noter (a plain read; the verdict is the report) or guards already set
        # (nothing said). Registered first, as it was, the reader's note landed ahead of the verdict's
        # lines and the boot said one failure twice (five failing boots gave [1, 2, 2, 2, 1] problem lines;
        # in the kernel's own ordering, reader first, every boot doubled). Several trials, both orderings,
        # a failing set and a working one: the command sleeps so the run is in flight when the second
        # party arrives, whichever that is.
        def boot_with_reader(reader_first):
            es._reset()
            self.logged.clear()
            sb._CREDENTIAL_NOTER = None                       # the kernel's state: no backend yet
            th = threading.Thread(target=sb.credential_set)
            if reader_first:
                th.start()
                time.sleep(0.05)
                be = self.construct()
            else:
                started = []
                def construct():
                    started.append(self.construct())
                ct = threading.Thread(target=construct)
                ct.start()
                time.sleep(0.05)
                th.start()
                ct.join(30)
                be = started[0]
            th.join(30)
            self.assertFalse(th.is_alive(), "the reader returned")
            self.assertEqual(es._runs, 1, "the reader and the verdict coalesced on one run")
            self.assertIs(sb._credential_noter().__self__, be)
            return be
        for trial in range(3):
            for reader_first in (True, False):
                self.command({"A_TOKEN": fixture_value()})
                self.failing(3, body="sleep 0.3")
                be = boot_with_reader(reader_first)
                about = self.about_failure(be)
                self.assertEqual(len(about), 1, (trial, reader_first, be.problems()))
                self.assertTrue(about[0].startswith("key source: the credential command failed"), about[0])
                self.assertEqual(self.failed_lines(be), [], (trial, reader_first, "the noter's line is not a second entry"))
                sb.credential_set()                           # the same failure on the next path: still primed
                be.key_source_status()
                self.assertEqual(len(self.about_failure(be)), 1, (trial, reader_first))
        for reader_first in (True, False):
            v = fixture_value()
            self.command({"ANTHROPIC_LP_API_KEY": v}, body="sleep 0.3")
            be = boot_with_reader(reader_first)
            fp = es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v})
            set_lines = [m for m in self.logged if "sha256:%s" % fp in m]
            self.assertEqual(len(set_lines), 1, (reader_first, self.logged))
            self.assertTrue(set_lines[0].startswith("key source: command"), set_lines[0])
            self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [], reader_first)
            self.assertNotIn(v, "\n".join(self.logged))

    def test_a_record_from_an_older_run_noted_after_a_newer_ones_is_ignored(self):
        # envsource releases its lock when take() returns, before the record reaches the noter, so a thread
        # held between the two hands over a record an intervening run has superseded. The noter orders
        # records by their `attempt`: an older one is ignored, an equal one (callers coalesced on one run)
        # is not. Two threads' interleaving, replayed sequentially with the records they would hold.
        be = self.boot_ok()                                   # a working boot; the command now exits 3, the set stale
        older, _vals = es.take()                              # thread A: the failed run's record, not yet noted
        self.assertFalse(older["ok"])
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        newer, _vals = es.take()                              # thread B: the store is back, its run succeeds…
        self.assertTrue(newer["ok"])
        self.assertGreater(newer["attempt"], older["attempt"])
        be._note_credential_set(newer)                        # …and is noted first
        be._note_credential_set(older)                        # thread A resumes with its stale record
        self.assertEqual(self.failed_lines(be), [], "a failure that predates the recovery is not said after it")
        self.assertEqual([m for m in self.logged if m.startswith("credential command: succeeded again")], [])
        self.assertEqual(be._cred_noted_attempt, newer["attempt"])
        # the guard was not poisoned by the stale record: the next real failure of that kind IS said
        es.invalidate("the store breaks again")
        self.failing(3)
        sb.credential_set()
        self.assertEqual(len(self.failed_lines(be)), 1, be.problems())
        # the other order: a good record from before a failure, noted after it, is not a recovery
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        good, _vals = es.take()                               # thread A: the recovery's record, not yet noted
        self.assertTrue(good["ok"])
        es.invalidate("and breaks once more")
        self.failing(3)
        bad, _vals = es.take()                                # thread B: the failure, noted first
        be._note_credential_set(bad)
        be._note_credential_set(good)
        self.assertEqual([m for m in self.logged if m.startswith("credential command: succeeded again")], [],
                         "a recovery that predates the failure is not said during it")
        self.assertEqual(be._cred_err_said, "exited 3", "the episode stands")
        sb.credential_set()                                   # the same failure again: still the one line
        self.assertEqual(len(self.failed_lines(be)), 1, be.problems())
        # the rule is on the ordinal alone: a record with the SAME ordinal is processed (a copy of the
        # newest record carrying one more fact is said), an older one is dropped whole
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        rec, _vals = es.take()
        be._note_credential_set(rec)
        self.assertEqual(len([m for m in self.logged if m.startswith("credential command: succeeded again")]), 1)
        be._note_credential_set(dict(rec, dropped=["ROMP_X"]))
        be._note_credential_set(dict(older, dropped=["ROMP_Y"]))
        said = [p["text"] for p in be.problems() if "ROMP_* variable" in p["text"]]
        self.assertEqual(len(said), 1, be.problems())
        self.assertIn("(ROMP_X)", said[0])

    def test_a_backends_own_readers_note_on_it_and_a_dropped_backend_receives_no_notes(self):
        # the kernel constructs one backend per process; a test process constructs several. The module-level
        # readers (no backend in hand) note through the LAST constructed; a backend's own readers note on
        # that backend, whichever was constructed last; and the registration is weak, so a dropped backend
        # is released and receives nothing (a strong reference kept it alive until the next construction).
        self.v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        b1 = self.construct()
        b2 = self.construct()
        self.assertEqual(es._runs, 1, "the second boot reads the cached record")
        self.assertIs(sb._credential_noter().__self__, b2, "last constructed: the module-level readers' noter")
        self.failing(3)
        es.invalidate("the store is unreachable")
        b1.key_source_status()                                # b1's own reader meets the failure first
        self.assertEqual(es._runs, 2)
        self.assertEqual(len(self.failed_lines(b1)), 1, "said in the ring of the backend whose reader ran the command")
        self.assertEqual(self.failed_lines(b2), [], "not in the last constructed backend's ring")
        b1.api_health_snapshot()
        b1._work_key_and_source()
        self.assertEqual(len(self.failed_lines(b1)), 1, "one episode, one line, across b1's own paths")
        sb.credential_set()                                   # a module-level reader: the registered backend notes
        self.assertEqual(len(self.failed_lines(b2)), 1, b2.problems())
        self.assertEqual(len(self.failed_lines(b1)), 1)
        ref = weakref.ref(b2)
        del b2
        gc.collect()
        self.assertIsNone(ref(), "the registration does not keep a dropped backend alive")
        self.assertIsNone(sb._credential_noter(), "a dropped backend is not the noter")
        es.invalidate("again")
        self.failing(4)
        runs = es._runs
        vals = sb.credential_set()                            # runs, noted by no one: no live registrant, no error
        self.assertEqual(es._runs, runs + 1)
        self.assertEqual(vals, {"ANTHROPIC_LP_API_KEY": self.v}, "the previous set stands")
        self.assertEqual(len(self.failed_lines(b1)), 1, "b1 is not registered and none of its own readers ran")
        self.assertFalse(any("exited 4" in t for t in self.failed_lines(b1)))
        b3 = self.construct()                                 # the next backend's boot verdict reports what it meets
        self.assertIs(sb._credential_noter().__self__, b3)
        self.assertTrue(any("exited 4" in t for t in self.about_failure(b3)), b3.problems())
        self.assertNotIn(self.v, json.dumps(b1.problems()) + json.dumps(b3.problems()) + "\n".join(self.logged))


if __name__ == "__main__":
    unittest.main()
