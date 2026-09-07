#!/usr/bin/env python3
"""key_source_verdict: the one-shot key-source check at backend construction, and the `keySource` block
it feeds on /api-health.

The verdict is pure on its inputs (the cli_scope_supported pattern): the kind keysource selected, an
environ, the env file's text, the unit/drop-in/plist texts, the apiKeyHelper command, the command
source's value-free first-run record and two booleans. Every line it returns carries NAMES and
fingerprints only. Under test:
  Modes: the kind word decides the mode (the backend hands in keysource's live selection; a pure call
    without one derives it from the inputs by keysource's own precedence); sessionKeyPath
    injected|helper|login.
  FileModeSaysNothingNew: the file kind leaves the boot log byte for byte the base's: no line for the
    ordinary shapes; a unit credential rings only under a declared auth.
  CommandKindChecks: each check: the first run (ok, failed on the previous set, failed on nothing), an
    ANTHROPIC_API_KEY copy in the env file, the unit or the plist (ignored, remove and rotate), the
    startup key (ignored by the launch, inherited by tmux panes), other credential-shaped names in the
    env file, the service definition and the kernel's environment (informational: they reach every
    session, the set does not), ExecStart through a shell, login declared while the command prints a
    key, ROMP_* and CLI-auth names dropped, a timeout out of range.
  OpKind: the reference exempts op's own names everywhere, rings on a leftover ANTHROPIC_API_KEY line,
    reports other credential-shaped names as information, and repeats nothing about the startup key
    (that line is the selection's own).
  BothModes: ROMP_EXPECTED_AUTH=key with nothing to inject and no apiKeyHelper rings under the command
    kind only.
  Floors: conftest points ROMP_SYSTEMD_DIR, ROMP_LAUNCHD_DIR and CLAUDE_CONFIG_DIR at empty dirs, and
    ROMP_SERVICE_ENV_FILE (both spellings) at a path that does not exist.
  PureOnItsInputs: a pure call never reads the env file this process is configured from: a decoy
    service.env at the default location under a private HOME is not consulted; the kind comes from the
    inputs, or from the backend.
  UnitParsing: Environment= lines and plist pairs (names only), ExecStart shapes and drop-in overrides,
    the paths _unit_texts reads (bin/romp-service's variables).
  NoValueAnywhere: with fixture values in every input, the verdict's JSON carries none.
  BootAndHealth: the backend runs the verdict once at construction, logs its lines (the problem ring
    for the flagged ones), and api_health_snapshot()["keySource"] carries the documented fields; under
    the file kind with nothing declared, no "key source:" line is logged at all. The selection stays
    live: a command removed from the environment is an error, never a fallback, and a command that
    appears later is taken. A credential command that fails is ONE problem line per failure episode
    whichever path first runs it (the judges' and the catalog's wire, a judge's key read, the status
    report, the api-health snapshot, the key cycle), and a later success followed by another failure is
    a second. The boot is one line per fact: the verdict's line is the boot's report of a failure and
    the noter says nothing for it then or on the next path. The noter orders records by envsource's
    `attempt`. A backend's own readers note on that backend; the module-level readers note through the
    last constructed one, held weakly.

Synthetic throughout: values are "romp-test-fixture-" + a uuid assembled at run time; the fake command
is a script in a temp dir; paths are temp paths; the reference is the documented placeholder.
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
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ.pop("ROMP_SUPERVISED", None)
_NO_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_ENV
sb = SourceFileLoader("romp_sdk_backend_ksv", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
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


def infos(v):
    return [ln["text"] for ln in v["lines"] if not ln["problem"]]


CMD = {"ROMP_CREDENTIAL_COMMAND": "credential-cmd --romp \"$1\""}
CMD_LINE = "ROMP_CREDENTIAL_COMMAND=credential-cmd --romp \"$1\"\n"   # the same selection, in the env file's text
REF = {"ROMP_API_KEY_REF": "op://vault/item/field"}


def ok_snap(**over):
    snap = {"configured": True, "ok": True, "reason": "", "at": 1_700_000_000.5, "exitCode": 0,
            "durationS": 0.412, "timedOut": False, "names": ["ANTHROPIC_LP_API_KEY", "A_TOKEN"],
            "dropped": [], "badLines": 0, "emptyValues": 0, "setFp": "0123456789ab", "keyFp": "",
            "hasKey": False, "stale": False, "runs": 1, "failures": 0, "generation": 0, "selector": "hp"}
    snap.update(over)
    return snap


class Modes(unittest.TestCase):
    def test_the_kind_word_decides_the_mode(self):
        self.assertEqual(verdict()["mode"], "file")
        self.assertEqual(verdict(CMD, snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict(REF)["mode"], "op")
        self.assertEqual(verdict(dict(CMD, **REF))["mode"], "command", "command > op, keysource's precedence")
        self.assertEqual(verdict({"ROMP_CREDENTIAL_COMMAND": "  "})["mode"], "command",
                         "presence selects, as keysource's environment door has it; the text is the run's problem")
        # the backend hands in the live selection, and it wins over anything in the inputs
        self.assertEqual(verdict(CMD, source_kind="file")["mode"], "file")
        self.assertEqual(verdict(source_kind="op")["mode"], "op")
        self.assertEqual(verdict(source_kind="command", snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict(source_kind="environment")["mode"], "file", "the startup key is the file mode's fallback")
        self.assertEqual(verdict(source_kind="none")["mode"], "file")
        self.assertEqual(verdict(source_kind="error")["mode"], "error", "no source can be selected: said as such")

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
        self.assertIsNone(verdict()["lastRun"], "the file kind has no command run")
        self.assertIsNone(verdict(REF)["lastRun"], "nor has the reference")
        self.assertEqual(verdict()["selector"], "")
        json.dumps(v)


class FileModeSaysNothingNew(unittest.TestCase):
    def test_the_ordinary_shapes_produce_no_line(self):
        v = fixture_value()
        for kw in (dict(),
                   dict(service_env_text="ANTHROPIC_API_KEY=%s\n" % v),               # the base's own checks speak
                   dict(service_env_text="HF_TOKEN=%s\n" % v),
                   dict(environ={"ANTHROPIC_LP_API_KEY": v, "HF_TOKEN": v}),
                   dict(unit_texts=[("unit", "ExecStart=/bin/zsh -lc 'romp-manager up'\n")]),   # a shell ExecStart is the file kind's own business
                   dict(unit_texts=[("unit", 'Environment="HF_TOKEN=%s"\n' % v)]),         # undeclared: quiet
                   dict(startup_key_present=True, work_key_present=True),
                   dict(environ={"ROMP_EXPECTED_AUTH": "key"}),
                   dict(environ={"ROMP_EXPECTED_AUTH": "login"}, service_env_text="ANTHROPIC_API_KEY=%s\n" % v)):
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
        r = verdict({"ROMP_EXPECTED_AUTH": "key"}, unit_texts=[("the-unit", 'Environment="HF_TOKEN=%s"\n' % v)])
        self.assertEqual(len(problems(r)), 1, "either declaration: a credential in a unit contradicts it")


class CommandKindChecks(unittest.TestCase):
    def test_a_good_first_run_is_one_informational_line(self):
        r = verdict(CMD, snapshot=ok_snap())
        self.assertEqual(len(r["lines"]), 1)
        self.assertFalse(r["lines"][0]["problem"])
        t = r["lines"][0]["text"]
        self.assertTrue(t.startswith("key source: command (selector hp); the set is sha256:0123456789ab (2 names: "
                                     "ANTHROPIC_LP_API_KEY, A_TOKEN); no ANTHROPIC_API_KEY in it"), t)
        r = verdict(CMD, snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef", names=["ANTHROPIC_API_KEY"], selector=""))
        t = r["lines"][0]["text"]
        self.assertTrue(t.startswith("key source: command; the set is"), t)
        self.assertIn("(1 name: ANTHROPIC_API_KEY)", t)
        self.assertIn("the sessions' key is sha256:abcdefabcdef", t)
        self.assertNotIn("selector", t)

    def test_a_failed_first_run_rings_with_the_reason_and_the_consequence(self):
        r = verdict(CMD, snapshot=ok_snap(ok=False, reason="exited 3 after 0.4s, stderr 87 bytes", names=[], setFp=""))
        self.assertEqual(len(problems(r)), 1)
        self.assertTrue(problems(r)[0].startswith("key source: the credential command failed: exited 3 after 0.4s, stderr 87 bytes."),
                        problems(r)[0])
        self.assertIn("nothing injected", problems(r)[0])
        self.assertIn("until a run succeeds", problems(r)[0])
        self.assertEqual(r["lastRun"]["ok"], False)
        r = verdict(CMD, snapshot=ok_snap(ok=False, reason="timed out after 15s (killed with its process group)", stale=True))
        self.assertIn("last successful run (sha256:0123456789ab)", problems(r)[0])
        self.assertNotIn("nothing injected", problems(r)[0])

    def test_an_api_key_line_in_the_env_file_is_ignored_and_named(self):
        # the shape this happens in: the command line and a key line in ONE file (command > file there; a key
        # line in the file would outrank a command at the environment door, as PureOnItsInputs pins)
        v = fixture_value()
        r = verdict({}, snapshot=ok_snap(), service_env_text="ROMP_PERF=1\n" + CMD_LINE + "ANTHROPIC_API_KEY=%s\nHF_TOKEN='%s'\n" % (v, v))
        self.assertEqual(r["mode"], "command")
        line = [t for t in problems(r) if "ANTHROPIC_API_KEY is set in" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn(ks.service_env_path(), line[0])
        self.assertIn("ROMP_CREDENTIAL_COMMAND governs the key", line[0])
        self.assertIn("ignored", line[0])
        self.assertIn("remove it and rotate the value", line[0])
        self.assertNotIn("HF_TOKEN", line[0], "the other name is not a copy of the key: its own line, below")
        self.assertNotIn(v, line[0])
        self.assertEqual(r["credentialNamesFound"]["serviceEnv"], ["ANTHROPIC_API_KEY", "HF_TOKEN"])
        # the other credential-shaped name in the file: information, not a fault, and it says where it goes
        info = [t for t in infos(r) if "credential-shaped names in %s" % ks.service_env_path() in t]
        self.assertEqual(len(info), 1, texts(r))
        self.assertIn(": HF_TOKEN.", info[0])
        self.assertIn("reach every session's CLI and tool shells", info[0])
        self.assertIn("the command's set does not", info[0])
        self.assertNotIn(v, info[0])
        self.assertEqual(len(problems(r)), 1, "the key copy is the only fault")

    def test_a_startup_key_is_ignored_by_the_launch_and_inherited_by_tmux_panes(self):
        r = verdict(CMD, snapshot=ok_snap(), startup_key_present=True)
        line = [t for t in problems(r) if "manager's own environment" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn("ANTHROPIC_API_KEY", line[0])
        self.assertIn("ignored by the launch", line[0])
        self.assertIn("tmux", line[0])
        self.assertIn("rotate it", line[0])
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_API_KEY"])
        # the same fact seen in a hypothetical environ's own ANTHROPIC_API_KEY: one line, not two
        r = verdict(dict(CMD, ANTHROPIC_API_KEY=fixture_value()), snapshot=ok_snap(), startup_key_present=True)
        self.assertEqual(len([t for t in problems(r) if "manager's own environment" in t]), 1)
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_API_KEY"])

    def test_other_credential_names_in_the_kernels_environment_are_informational(self):
        v = fixture_value()
        env = dict(CMD, ANTHROPIC_LP_API_KEY=v, HF_TOKEN=v, ROMP_SERVE_TOKEN=v, EMPTY_TOKEN="", NOT_A_SECRET=v,
                   OP_SERVICE_ACCOUNT_TOKEN=v)
        r = verdict(env, snapshot=ok_snap())
        info = [ln for ln in r["lines"] if "kernel's own environment" in ln["text"]]
        self.assertEqual(len(info), 1)
        self.assertFalse(info[0]["problem"], "they reach every session already: worth knowing, not a fault")
        self.assertIn("ANTHROPIC_LP_API_KEY, HF_TOKEN, OP_SERVICE_ACCOUNT_TOKEN", info[0]["text"])
        self.assertIn("reach every session's CLI and tool shells; the command's set does not", info[0]["text"])
        self.assertNotIn("ROMP_SERVE_TOKEN", info[0]["text"], "romp's own serve token is exempt")
        self.assertNotIn("EMPTY_TOKEN", info[0]["text"])
        self.assertNotIn(v, info[0]["text"])
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_LP_API_KEY", "HF_TOKEN", "OP_SERVICE_ACCOUNT_TOKEN"],
                         "under the command kind nothing is claimed: op's token reaches the sessions too")
        self.assertEqual(problems(r), [])

    def test_credential_lines_in_the_unit_or_plist(self):
        v = fixture_value()
        unit = 'Environment="ANTHROPIC_API_KEY=%s" "ROMP_PERF=1"\n' % v
        plist = ("<key>EnvironmentVariables</key><dict><key>HF_TOKEN</key><string>%s</string>"
                 "<key>ROMP_DIR</key><string>/x</string></dict>" % v)
        r = verdict(CMD, snapshot=ok_snap(), unit_texts=[("a.service", unit), ("b.plist", plist)])
        line = [t for t in problems(r) if "ANTHROPIC_API_KEY is set in" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn("a.service", line[0])
        self.assertNotIn("b.plist", line[0])
        self.assertNotIn(v, line[0])
        info = [t for t in infos(r) if "credential-shaped names in the service definition" in t]
        self.assertEqual(len(info), 1, texts(r))
        self.assertIn("b.plist (HF_TOKEN)", info[0])
        self.assertNotIn("a.service", info[0])
        self.assertIn("reach every session's CLI and tool shells", info[0])
        self.assertEqual(r["credentialNamesFound"]["unit"], ["ANTHROPIC_API_KEY", "HF_TOKEN"])
        # a key copy in the file AND the unit: one line naming both places
        r = verdict({}, snapshot=ok_snap(), service_env_text=CMD_LINE + "ANTHROPIC_API_KEY=%s\n" % v,
                    unit_texts=[("a.service", unit), ("d.conf", unit)])
        line = [t for t in problems(r) if "ANTHROPIC_API_KEY is set in" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn("%s; a.service; d.conf" % ks.service_env_path(), line[0])

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
        # the remedy is the reference's (_check_env_file_vs_declaration), worded for a command line: a removed
        # or blanked command is an error at every launch in keysource, never a fall-back to the login, so the
        # line never says "remove the line"; the third way out is the one this kind alone has
        self.assertNotIn("remove the line", line[0])
        self.assertIn("Do not remove or blank the ROMP_CREDENTIAL_COMMAND line", line[0])
        self.assertIn("drop ROMP_EXPECTED_AUTH=login", line[0])
        self.assertIn("Login under Billing", line[0])
        self.assertIn("error at every launch", line[0])
        self.assertIn("print no ANTHROPIC_API_KEY", line[0])
        self.assertEqual([t for t in problems(verdict(env, snapshot=ok_snap())) if "while" in t], [],
                         "no key printed: the declaration holds")

    def test_dropped_romp_names_ring_by_name(self):
        r = verdict(CMD, snapshot=ok_snap(dropped=["ROMP_SID", "ROMP_STATE_DIR"]))
        line = [t for t in problems(r) if "ROMP_* variables" in t]
        self.assertEqual(len(line), 1)
        self.assertIn("(ROMP_SID, ROMP_STATE_DIR)", line[0])
        self.assertIn("dropped from the set", line[0])
        r = verdict(CMD, snapshot=ok_snap(dropped=["ROMP_SID"]))
        self.assertEqual(len([t for t in problems(r) if "1 ROMP_* variable (ROMP_SID)" in t]), 1, problems(r))

    def test_dropped_cli_auth_names_ring_by_name(self):
        r = verdict(CMD, snapshot=ok_snap(droppedAuth=["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"]))
        line = [t for t in problems(r) if "authentication or endpoint" in t]
        self.assertEqual(len(line), 1, problems(r))
        self.assertIn("ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, names the CLI reads", line[0])
        self.assertIn("dropped from the set", line[0])
        r = verdict(CMD, snapshot=ok_snap(droppedAuth=["CLAUDE_CODE_OAUTH_TOKEN"]))
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN, a name the CLI reads", [t for t in problems(r) if "endpoint" in t][0])
        self.assertEqual([t for t in problems(verdict(CMD, snapshot=ok_snap())) if "endpoint" in t], [])

    def test_an_unconfigured_snapshot_under_the_command_kind_produces_no_run_line(self):
        r = verdict(CMD, snapshot=None)
        self.assertEqual([t for t in texts(r) if "the set is" in t or "failed" in t], [])
        self.assertEqual(r["lastRun"], {"ok": None, "at": None, "reason": "", "exitCode": None, "durationS": None,
                                        "stale": False, "failures": 0, "lastOkAt": None})

    def test_an_undeclared_selector_is_rendered_by_length_and_a_bad_timeout_rings(self):
        r = verdict(CMD, snapshot=ok_snap(selector="", selectorNote="(undeclared, 5 chars)"))
        self.assertEqual(r["selector"], "(undeclared, 5 chars)")
        self.assertTrue(r["lines"][0]["text"].startswith("key source: command (selector undeclared, 5 chars); the set is"),
                        r["lines"][0]["text"])
        r = verdict(CMD, snapshot=ok_snap(timeoutProblem="ROMP_CREDENTIAL_TIMEOUT_S is not a number of seconds between 0 and 300; the default 15s holds"))
        line = [t for t in problems(r) if "ROMP_CREDENTIAL_TIMEOUT_S" in t]
        self.assertEqual(len(line), 1)
        self.assertTrue(line[0].startswith("key source: ROMP_CREDENTIAL_TIMEOUT_S is not a number"), line[0])


class OpKind(unittest.TestCase):
    """The reference: the built-in default command, with #962's own mechanism (the OP token is claimed for
    the op read and never reaches a session), so op's names are exempt everywhere; a leftover
    ANTHROPIC_API_KEY line is a fault the reference outranks; other credential-shaped names are said, as
    information, by place; the startup key is the selection's own stderr line and is not repeated here."""

    def test_ops_own_names_are_exempt_everywhere(self):
        v = fixture_value()
        env = dict(REF, OP_SERVICE_ACCOUNT_TOKEN=v, OP_SESSION_my_account=v, OP_CONNECT_TOKEN=v)
        r = verdict(env, service_env_text="OP_SERVICE_ACCOUNT_TOKEN=%s\nROMP_API_KEY_REF=op://vault/item/field\n" % v,
                    unit_texts=[("u", 'Environment="OP_SERVICE_ACCOUNT_TOKEN=%s"\n' % v),
                                ("p", "<key>OP_SESSION_x</key><string>%s</string>" % v)])
        self.assertEqual(r["mode"], "op")
        self.assertEqual(texts(r), [])
        self.assertEqual(r["credentialNamesFound"], {"serviceEnv": [], "unit": [], "environment": []},
                         "claimed for the op read: not names that reach a session")
        self.assertIsNone(r["lastRun"])
        self.assertEqual(r["sessionKeyPath"], "login", "a pure call with no key present; the backend says injected")

    def test_a_leftover_api_key_line_is_a_problem_the_reference_outranks(self):
        v = fixture_value()
        r = verdict(REF, service_env_text="ANTHROPIC_API_KEY=%s\nROMP_API_KEY_REF=op://vault/item/field\n" % v)
        self.assertEqual(len(problems(r)), 1, texts(r))
        self.assertIn("ANTHROPIC_API_KEY is set in %s" % ks.service_env_path(), problems(r)[0])
        self.assertIn("ROMP_API_KEY_REF selects the 1Password reference", problems(r)[0])
        self.assertIn("the reference outranks it", problems(r)[0])
        self.assertIn("remove it and rotate the value", problems(r)[0])
        self.assertNotIn(v, problems(r)[0])
        self.assertEqual(r["credentialNamesFound"]["serviceEnv"], ["ANTHROPIC_API_KEY"])
        r = verdict(REF, unit_texts=[("u.service", 'Environment="ANTHROPIC_API_KEY=%s"\n' % v),
                                     ("p.plist", "<key>ANTHROPIC_API_KEY</key><string>%s</string>" % v)])
        self.assertEqual(len(problems(r)), 1, texts(r))
        self.assertIn("u.service; p.plist", problems(r)[0])
        self.assertEqual(infos(r), [])

    def test_other_credential_names_are_information_by_place(self):
        v = fixture_value()
        env = dict(REF, ANTHROPIC_LP_API_KEY=v, HF_TOKEN=v, ROMP_SERVE_TOKEN=v, OP_SERVICE_ACCOUNT_TOKEN=v)
        r = verdict(env, service_env_text="HF_TOKEN=%s\nOP_SERVICE_ACCOUNT_TOKEN=%s\n" % (v, v),
                    unit_texts=[("u", 'Environment="X_TOKEN=%s"\n' % v)])
        self.assertEqual(problems(r), [])
        self.assertEqual(len(infos(r)), 3, texts(r))
        by_place = {"env file": [t for t in infos(r) if ks.service_env_path() in t],
                    "unit": [t for t in infos(r) if "service definition" in t],
                    "environment": [t for t in infos(r) if "kernel's own environment" in t]}
        for place, lines in by_place.items():
            self.assertEqual(len(lines), 1, (place, texts(r)))
            self.assertIn("reach every session's CLI and tool shells", lines[0])
            self.assertNotIn("the command's set", lines[0], "no set under the reference")
            self.assertNotIn(v, lines[0])
            self.assertNotIn("OP_", lines[0])
        self.assertIn(": HF_TOKEN.", by_place["env file"][0])
        self.assertIn("u (X_TOKEN)", by_place["unit"][0])
        self.assertIn(": ANTHROPIC_LP_API_KEY, HF_TOKEN.", by_place["environment"][0])
        self.assertEqual(r["credentialNamesFound"], {"serviceEnv": ["HF_TOKEN"], "unit": ["X_TOKEN"],
                                                     "environment": ["ANTHROPIC_LP_API_KEY", "HF_TOKEN"]})

    def test_the_startup_key_and_the_shell_and_the_declaration_are_not_this_verdicts_lines(self):
        r = verdict(dict(REF, ROMP_EXPECTED_AUTH="login"), startup_key_present=True,
                    unit_texts=[("u", "ExecStart=/bin/zsh -lc 'romp-manager up'\n")])
        self.assertEqual(texts(r), [], "the selection's own stderr line says the startup key; the env-file check the declaration")
        self.assertEqual(r["credentialNamesFound"]["environment"], ["ANTHROPIC_API_KEY"], "the fact is still reported")
        self.assertTrue(r["execStartShell"])
        r = verdict(dict(REF, ROMP_EXPECTED_AUTH="key"), unit_texts=[("u", 'Environment="HF_TOKEN=%s"\n' % fixture_value())])
        self.assertEqual(problems(r), [], "the unit-under-declaration line is the file kind's")
        self.assertEqual(len(infos(r)), 1)


class BothModes(unittest.TestCase):
    def test_key_declared_with_nothing_to_inject_and_no_helper_rings_under_the_command_kind_only(self):
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
        # the file kind: the boot log stays the base's; every session init already reports the
        # declared-vs-live mismatch, so the verdict adds no line here
        self.assertEqual(texts(verdict({"ROMP_EXPECTED_AUTH": "key"})), [])
        self.assertEqual(texts(verdict({"ROMP_EXPECTED_AUTH": "key"}, helper_command="")), [])
        self.assertEqual(texts(verdict(dict(REF, ROMP_EXPECTED_AUTH="key"))), [], "nor under the reference")

    def test_the_declaration_is_read_from_the_given_environ(self):
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": " Login "})["expectedAuth"], "login")
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": "both"})["expectedAuth"], "")
        self.assertEqual(verdict()["expectedAuth"], "")


class Floors(unittest.TestCase):
    """conftest's floor: every backend construction reads the unit, the plist and the Claude Code settings
    through these three variables, and no test may read this machine's."""

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
        # both spellings keysource accepts, one path, absent: every read is the "no file" case and no
        # test resolves this machine's service.env (its default lives under HOME)
        default = os.path.realpath(os.path.join(os.path.expanduser("~"), ".config", "romp", "service.env"))
        for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
            p = os.environ.get(var) or ""
            self.assertTrue(p, "%s is not floored" % var)
            self.assertFalse(os.path.exists(p), "%s points at a file that exists" % var)
            self.assertNotEqual(os.path.realpath(p), default, "%s points at this machine's default env file" % var)
        self.assertEqual(os.environ["ROMP_SERVICE_ENV_FILE"], os.environ["ROMP_SERVICE_ENV"])
        self.assertEqual(ks.service_env_path(), os.environ["ROMP_SERVICE_ENV_FILE"])
        self.assertEqual(ks.read_source().kind, "none", "no file: nothing selected from one")


class PureOnItsInputs(unittest.TestCase):
    """key_source_verdict never reads the env file this process is configured from: the backend hands in
    keysource's live kind, and a pure call without one derives the kind from the environ and the
    `service_env_text` it is handed, by keysource's own precedence. Proven against a decoy: a service.env
    at the DEFAULT location under a private HOME, the conftest floor lifted for the test, so the decoy is
    exactly the file this process would read."""

    VARS = ("HOME", "XDG_CONFIG_HOME", "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ROMP_CREDENTIAL_COMMAND",
            "ROMP_API_KEY_REF")

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in self.VARS}
        self._cache = ks._CACHE
        es._reset()

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        ks._CACHE = self._cache
        es._reset()

    def test_a_decoy_env_file_at_the_default_location_is_not_read(self):
        os.environ["HOME"] = self.d
        for v in self.VARS[1:]:
            os.environ.pop(v, None)
        decoy = os.path.join(self.d, ".config", "romp", "service.env")
        os.makedirs(os.path.dirname(decoy))
        with open(decoy, "w") as fh:
            fh.write('ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=decoy-command "$1"\n')
        ks._CACHE = ((), "")
        # the setup, proven: the decoy IS the file this process resolves and reads
        self.assertEqual(ks.service_env_path(), decoy)
        self.assertEqual(ks.read_source().kind, "command", "the process's own read takes the file's line")
        # the property: a pure call is the file kind; the decoy was not consulted
        v = verdict({})
        self.assertEqual(v["mode"], "file")
        self.assertIsNone(v["lastRun"])
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": "key"})["mode"], "file")
        self.assertEqual(sb.key_source_verdict(None)["mode"], "file",
                         "the process environment as the environ: still only the inputs, never the file")
        # the inputs decide: the env-file TEXT handed in first (the file outranks the environment, as
        # keysource selects), then the environ's own line
        self.assertEqual(verdict(CMD, snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict({}, service_env_text='ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND="x $1"\n',
                                 snapshot=ok_snap())["mode"], "command", "the file's TEXT is an input; the line in it selects")
        self.assertEqual(verdict({}, service_env_text="ROMP_API_KEY_REF=op://vault/item/field\n")["mode"], "op")
        self.assertEqual(verdict(CMD, service_env_text="ANTHROPIC_API_KEY=romp-test-fixture-k\n")["mode"], "file",
                         "a key line in the file outranks an environment command, as select_source has it")
        self.assertEqual(verdict({}, service_env_text="ROMP_CREDENTIAL_COMMAND=\n")["mode"], "command",
                         "an empty assignment is the command kind with an invalid text, as in the file itself")
        # the backend's word wins over every input
        self.assertEqual(sb.key_source_verdict(None, source_kind="command", snapshot=ok_snap())["mode"], "command")
        self.assertEqual(verdict(CMD, source_kind="op")["mode"], "op")


class UnitParsing(unittest.TestCase):
    def test_environment_lines_and_plist_pairs_names_only(self):
        v = fixture_value()
        text = ('Environment="A_API_KEY=%s" B_TOKEN=%s NOT_ONE=%s\n'
                "Environment=EMPTY_TOKEN=\n"
                "Environment='C_TOKEN=%s'\n"
                "Environment=A_API_KEY=%s\n" % (v, v, v, v, v))
        self.assertEqual(sb._unit_credential_names(text), ["A_API_KEY", "B_TOKEN", "C_TOKEN"])
        plist = ("<key>D_TOKEN</key>\n  <string>%s</string><key>E_API_KEY</key><string></string>"
                 "<key>ROMP_DIR</key><string>/nonexistent/x</string>" % v)
        self.assertEqual(sb._unit_credential_names(plist), ["D_TOKEN"])
        self.assertEqual(sb._unit_credential_names('Environment="X_TOKEN=%s\n' % v), ["X_TOKEN"],
                         "an unbalanced quote falls back to a plain split, and the name still reads clean")
        self.assertEqual(sb._unit_credential_names(""), [])

    def test_env_file_text_names_only(self):
        v = fixture_value()
        text = ("# comment\n\nROMP_PERF=1\nANTHROPIC_API_KEY=%s\nHF_TOKEN='%s'\nEMPTY_TOKEN=\nQUOTED_TOKEN=\"\"\n"
                "export X_API_KEY=%s\nANTHROPIC_API_KEY=%s\nnot an assignment\n" % (v, v, v, v))
        self.assertEqual(sb._credential_names_in_env_text(text), ["ANTHROPIC_API_KEY", "HF_TOKEN", "X_API_KEY"])
        self.assertEqual(sb._credential_names_in_env_text(""), [])
        self.assertEqual(sb._credential_names_in_env_text(None), [])

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
        r = verdict(env, service_env_text=CMD_LINE + "ANTHROPIC_API_KEY=%s\nX_TOKEN=%s\n" % (v[3], v[4]),
                    unit_texts=[("u", 'Environment="Y_API_KEY=%s"\nExecStart=/bin/zsh -lc x\n' % v[5]),
                                ("p", "<key>Z_TOKEN</key><string>%s</string>" % v[5])],
                    helper_command="helper " + v[2],
                    snapshot=ok_snap(hasKey=True, keyFp="abcdefabcdef", dropped=["ROMP_X"]),
                    work_key_present=True, startup_key_present=True)
        blob = json.dumps(r)
        for x in v:
            self.assertNotIn(x, blob)
        self.assertNotIn("fixture", blob)
        self.assertGreaterEqual(len(problems(r)), 5, texts(r))
        self.assertGreaterEqual(len(texts(r)), 9, texts(r))
        r = verdict(dict(REF, ANTHROPIC_LP_API_KEY=v[1]),
                    service_env_text="ROMP_API_KEY_REF=op://vault/item/field\nANTHROPIC_API_KEY=%s\nX_TOKEN=%s\n" % (v[3], v[4]),
                    unit_texts=[("u", 'Environment="Y_API_KEY=%s"\n' % v[5])], startup_key_present=True)
        self.assertEqual(r["mode"], "op")
        blob = json.dumps(r)
        for x in v:
            self.assertNotIn(x, blob)
        self.assertEqual(len(problems(r)), 1)
        self.assertEqual(len(infos(r)), 3)


class BootAndHealth(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR", "ROMP_EXPECTED_AUTH",
                                                                         "ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR",
                                                                         "ANTHROPIC_API_KEY", "ROMP_API_KEY_REF")}
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
        self._resolver = ks.COMMAND_RESOLVER
        self.reset_sources()
        self.logged = []

    def tearDown(self):
        sb._WORK_KEY, sb._KEY_FILE_CHECKED = self._stash, self._checked
        sb._fetch_key_fast_org = self._fetch
        ks.COMMAND_RESOLVER = self._resolver
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        self.reset_sources()

    @staticmethod
    def reset_sources():
        ks._CACHE = ((), "")
        ks._AUTHORITATIVE_PATHS.clear()
        ks._ENV_PROVIDER_PATHS.clear()
        es._reset()

    def construct(self):
        return sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def command(self, values, body=""):
        """The environment door: a foreground manager's ROMP_CREDENTIAL_COMMAND naming a fake script that
        prints `values` as NAME=VALUE lines."""
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
        st = be.key_source_status()
        self.assertEqual(st, {"source": "file", "fp": "", "fpKind": "", "err": "", "setFp": "", "selector": "",
                              "launched": {}})
        self.assertEqual(be.refresh_key_source(), {"from": "", "to": "", "err": ""})
        self.assertEqual(es._runs, 0, "nothing ran under the file kind")

    def test_the_reference_kind_runs_op_on_no_status_read(self):
        os.environ["ROMP_API_KEY_REF"] = "op://vault/item/field"
        be = self.construct()
        self.assertEqual(be.key_source["mode"], "op")
        self.assertEqual(be.key_source["sessionKeyPath"], "injected", "the reference is resolved and injected at launch")
        self.assertIsNone(be.key_source["lastRun"])
        # the one line the reference may add here depends on the developer's shell (credential-shaped names
        # in this process's environment, information); nothing else is said
        self.assertEqual([m for m in self.logged if m.startswith("key source:") and "kernel's own environment" not in m], [])
        self.assertEqual([p["text"] for p in be.problems() if p["text"].startswith("key source:")], [])
        self.assertEqual(be.credential_fingerprint(), ("", ""), "a status read never runs op")
        self.assertEqual(be.work_key_fp(), "")
        st = be.key_source_status()
        self.assertEqual((st["source"], st["fp"], st["fpKind"], st["err"]), ("op", "", "", ""))
        self.assertEqual(be.refresh_key_source(), {"from": "", "to": "", "err": ""})
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual((snap["mode"], snap["fingerprint"], snap["fingerprintKind"]), ("op", "", ""))
        self.assertEqual(snap["sessionKeyPath"], "injected")
        self.assertIsNone(snap["lastRun"])
        self.assertEqual(es._runs, 0)
        self.assertEqual(be.role_fingerprint(), "")

    def test_command_kind_runs_the_verdict_once_at_construction_and_logs_its_lines(self):
        v = fixture_value()
        self.command({"ANTHROPIC_LP_API_KEY": v, "ROMP_SID": "x"})
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        be = self.construct()
        self.assertEqual(es._runs, 1, "the verdict's run is the first run, before any launch")
        self.assertTrue(any(m.startswith("key source: command") for m in self.logged), self.logged)
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
        self.assertEqual((snap["fingerprint"], snap["fingerprintKind"]), ("", "login"))
        self.assertEqual(snap["mode"], "command")
        self.assertNotIn(v, json.dumps(snap))
        self.assertNotIn(v, "\n".join(self.logged))
        st = be.key_source_status()
        self.assertEqual((st["source"], st["fpKind"], st["err"], st["setFp"]),
                         ("command", "login", "", es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v})))
        self.assertEqual(be.role_fingerprint(), es.set_fingerprint({"ANTHROPIC_LP_API_KEY": v}))
        self.assertEqual(es._runs, 1, "a working set is served from the cache on every reader")

    def test_the_fingerprints_the_readers_report(self):
        k, h = fixture_value("key"), fixture_value("helper")
        self.command({"ANTHROPIC_API_KEY": k, "A_TOKEN": fixture_value()})
        be = self.construct()
        self.assertEqual(be.credential_fingerprint(), (es.fingerprint(k), "key"))
        self.assertEqual(be.work_key_fp(), es.fingerprint(k))
        self.assertEqual(be.key_source_status()["fp"], es.fingerprint(k))
        self.assertEqual(be.api_health_snapshot()["keySource"]["sessionKeyPath"], "injected")
        self.assertTrue(any("the sessions' key is sha256:%s" % es.fingerprint(k) in m for m in self.logged), self.logged)
        # no key in the set and a helper configured: the helper's output, run and hashed inside envsource
        os.makedirs(os.environ["CLAUDE_CONFIG_DIR"])
        helper = os.path.join(self.d, "helper.sh")
        with open(helper, "w") as fh:
            fh.write("#!/bin/sh\necho '%s'\n" % h)
        os.chmod(helper, 0o700)
        with open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": helper}, fh)
        self.command({"A_TOKEN": fixture_value()})
        r = be.refresh_key_source()
        self.assertEqual(r, {"from": es.fingerprint(k), "to": es.fingerprint(h), "err": ""})
        self.assertEqual(be.credential_fingerprint(), (es.fingerprint(h), "helper"))
        self.assertEqual(be.api_health_snapshot()["keySource"]["sessionKeyPath"], "helper")
        self.assertTrue(any("refreshed" in m and "sha256:%s" % es.fingerprint(h) in m for m in self.logged), self.logged)
        # a helper that prints nothing usable: no fingerprint, and the status says why
        with open(helper, "w") as fh:
            fh.write("#!/bin/sh\nexit 2\n")
        es.invalidate("the helper broke")
        self.assertEqual(be.credential_fingerprint(), ("", ""))
        st = be.key_source_status()
        self.assertEqual(st["fpKind"], "")
        self.assertIn("exited 2", st["err"])
        blob = "\n".join(self.logged) + json.dumps(be.problems()) + json.dumps(be.api_health_snapshot())
        self.assertNotIn(k, blob)
        self.assertNotIn(h, blob)

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
        self.assertTrue(any("credential-shaped names in the service definition" in t and "(HF_TOKEN)" in t
                            for t in self.logged), self.logged)
        self.assertFalse(any("(HF_TOKEN)" in t for t in probs), "another name in the unit is information under the command kind")
        self.assertNotIn(v, json.dumps(probs) + "\n".join(self.logged))

    def test_the_selection_is_live_and_a_removed_command_is_an_error_not_a_fallback(self):
        v = fixture_value()
        self.command({"A_TOKEN": v})
        be = self.construct()
        self.assertEqual(be.key_source["mode"], "command")
        runs = es._runs
        os.environ.pop("ROMP_CREDENTIAL_COMMAND")
        self.assertEqual(be._work_key_source().kind, "error", "the environment's line gone: a removed source, never the login")
        st = be.key_source_status()
        self.assertEqual(st["source"], "error")
        self.assertIn("The credential command was removed", st["err"])
        self.assertEqual((st["fp"], st["fpKind"]), ("", ""))
        r = be.refresh_key_source()
        self.assertIn("The credential command was removed", r["err"])
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["mode"], "error")
        self.assertEqual(snap["lastRun"]["ok"], True, "the boot's record stands in the block")
        self.assertEqual(es._runs, runs, "nothing runs with no command selected")
        self.assertNotIn(v, json.dumps(snap) + json.dumps(st) + "\n".join(self.logged))
        # the other way: a kernel that booted under the file kind takes a command that appears at the
        # environment door later (a foreground manager), live, with no pin at boot
        self.reset_sources()
        self.logged.clear()
        be = self.construct()
        self.assertEqual(be.key_source["mode"], "file")
        self.assertEqual(es._runs, 0)
        self.command({"A_TOKEN": v})
        self.assertEqual(be._work_key_source().kind, "command")
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["mode"], "command")
        self.assertEqual(snap["names"], ["A_TOKEN"])
        self.assertEqual(es._runs, 1, "the live block ran it")

    def test_a_boot_on_a_source_that_cannot_be_selected_says_so(self):
        # a supervised manager whose command rides its environment alone: keysource reads the file only and
        # treats the environment's line as a removed source (the reference's rule); the boot says it once, in
        # the problem ring, instead of every launch failing with nothing in the log to find it by
        self.command({"A_TOKEN": fixture_value()})
        os.environ["ROMP_SUPERVISED"] = "1"
        try:
            be = self.construct()
        finally:
            os.environ.pop("ROMP_SUPERVISED", None)
        self.assertEqual(be.key_source["mode"], "error")
        probs = [p["text"] for p in be.problems()]
        hit = [t for t in probs if t.startswith("key source: ") and "The credential command was removed" in t]
        self.assertEqual(len(hit), 1, probs)
        self.assertEqual(es._runs, 0, "nothing ran")
        self.assertEqual(be.key_source["lines"], [])
        self.assertEqual(be.api_health_snapshot()["keySource"]["mode"], "error")

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
        snap = be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["mode"], "command")
        self.assertEqual(set(snap), {"mode", "selector", "sessionKeyPath", "expectedAuth", "helperConfigured",
                                     "execStartShell", "credentialNamesFound", "lastRun", "fingerprint",
                                     "fingerprintKind", "setFingerprint", "names", "sessionsByFingerprint"},
                         "the block keeps its documented shape whatever the verdict did")

    def test_a_verdict_that_cannot_be_taken_leaves_the_run_for_the_next_path_to_say_once(self):
        # the verdict's lines are the boot's report of the first run, and it hands the record to the noter as
        # reported only once they are logged. A verdict that raised logged nothing about the run, so it primes
        # nothing: the guards stay unset, the noter is registered all the same, and the next path to read the
        # set (a module-level reader or one of the backend's own) says the run, once.
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

    def boot_ok(self, values=None):
        """A backend booted on a WORKING command (one run, no failure said), and the store then broken: the
        refusal a judge call reports (credential_invalidate, the judges' wire) makes the cached set stale,
        so the next reader, whichever path, runs the command and meets the failure first."""
        self.v = fixture_value()
        self.command(values if values is not None else {"ANTHROPIC_LP_API_KEY": self.v})
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
        # the same failure again, on every path that reads the set: no second line, and no second run either.
        # The judges' wire, a judge's key read and the status reads take the record that stands (until
        # 2026-09-07 each of them re-ran the command, so a hung store cost every judge call its timeout);
        # the connect is the reader that re-runs.
        sb.credential_set()
        sb.credential_set()
        self.assertEqual(es._runs, 2, "the judges' wire runs nothing after a failure: the record stands")
        self.assertEqual(sb.work_api_key(), "", "a judge's key read: the set carries no ANTHROPIC_API_KEY")
        st = be.key_source_status()
        self.assertIn("exited 3", st["err"])
        health = be.api_health_snapshot()["keySource"]["lastRun"]
        self.assertFalse(health["ok"])
        self.assertTrue(health["stale"])
        self.assertEqual(es._runs, 2, "nor do the status reads")
        self.assertEqual(len(self.failed_lines(be)), 1, "the episode is one line however many paths met it")
        be._work_key_and_source()
        self.assertEqual(es._runs, 3, "a connect re-runs")
        self.assertEqual(len(self.failed_lines(be)), 1)
        # the recovery ends the episode: an info line, not a problem. The connect finds the store back, and
        # the judges' wire is served the recovered set from it
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        be._work_key_and_source()
        self.assertEqual(es._runs, 4)
        self.assertEqual(sb.credential_set(), {"ANTHROPIC_LP_API_KEY": self.v})
        self.assertEqual(es._runs, 4, "served the recovery, no run of its own")
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
        be.refresh_key_source()
        self.assertEqual(len(self.failed_lines(be)), 1)

    def test_a_failure_first_seen_by_the_key_cycle_is_said_once(self):
        # a keyed session on a set that carries a key: the cycle's compare reads the set once (the failed run
        # stands on the last good set, so the key it compares against is that set's) and says the failure once
        k = fixture_value("key")
        be = self.boot_ok({"ANTHROPIC_API_KEY": k, "A_TOKEN": fixture_value()})
        sid = "11111111-2222-3333-4444-000000000021"
        reg = {"sid": sid, "name": "web", "cwd": self.d, "auth": "key"}
        sb.write_reg(be.state_dir, sid, reg)                 # owned; a live session object, no CLI
        s = sb.SdkSession(be, reg)
        s._launched_key_fp = "000000000000"                  # launched on another key: the cycle has a reason
        reconnects = []
        s.request_reconnect = lambda defer=True: reconnects.append(defer)
        be.sessions[sid] = s
        self.assertEqual(be.cycle_key(sid), "cycling")
        self.assertEqual(reconnects, [False])
        self.assertEqual(es._runs, 2, "one read of the set for the whole compare")
        self.assertEqual(len(self.failed_lines(be)), 1, be.problems())
        self.assertEqual(be.cycle_key(sid), "cycling")
        self.assertEqual(len(self.failed_lines(be)), 1)
        self.assertNotIn(k, json.dumps(be.problems()) + "\n".join(self.logged))

    # -- the boot is one line per fact; the noter orders records; a backend's own readers note on it --------

    def about_failure(self, be):
        """Every problem line about the command having failed, whichever mechanism wrote it."""
        return [p["text"] for p in be.problems() if "credential command" in p["text"] and "failed" in p["text"]]

    def test_a_boot_on_a_failing_command_is_one_problem_line_and_the_episode_is_primed(self):
        # the verdict's line carries the run's detail (duration, stderr bytes); it is the boot's one report,
        # and the noter, handed the record as reported, says nothing at boot and nothing for the same
        # failure on the next path.
        self.command({"A_TOKEN": fixture_value()})
        self.failing(3)
        be = self.construct()
        self.assertEqual(es._runs, 1, "one run at boot: the record itself answers whether a key is injected")
        about = self.about_failure(be)
        self.assertEqual(len(about), 1, be.problems())
        self.assertTrue(about[0].startswith("key source: the credential command failed: exited 3 after "), about[0])
        self.assertIn("nothing injected", about[0])
        self.assertEqual(self.failed_lines(be), [], "the noter's line is not a second entry")
        self.assertEqual(be.key_source["sessionKeyPath"], "login")
        self.assertEqual(be.key_source["lastRun"]["ok"], False)
        # the same failure met next on the judges' wire, the status report and a connect: no more entries.
        # The wire and the status report take the record that stands (no run; until 2026-09-07 every reader
        # re-ran a failing command); the connect re-runs
        sb.credential_set()
        be.key_source_status()
        self.assertEqual(es._runs, 1, "the judges' wire and the status report run nothing after a failure")
        be._work_key_and_source()
        self.assertEqual(es._runs, 2, "the connect re-runs")
        self.assertEqual(len(self.about_failure(be)), 1)
        # the recovery ends the episode the boot opened: found by the connect, served to the judges' wire
        v = fixture_value()
        self.command({"A_TOKEN": v})
        self.assertEqual(sb.credential_set(), {}, "no set from an earlier run stands, and the wire runs nothing")
        be._work_key_and_source()
        self.assertEqual(sb.credential_set(), {"A_TOKEN": v})
        self.assertEqual(es._runs, 3)
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
        # (nothing said). Several trials, both orderings, a failing set and a working one: the command
        # sleeps so the run is in flight when the second party arrives, whichever that is.
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
        src = be._work_key_source()
        older, _vals = es.take(src)                           # thread A: the failed run's record, not yet noted
        self.assertFalse(older["ok"])
        self.command({"ANTHROPIC_LP_API_KEY": self.v})
        newer, _vals = es.take(src)                           # thread B: the store is back, its run succeeds
        self.assertTrue(newer["ok"])
        self.assertGreater(newer["attempt"], older["attempt"])
        be._note_credential_set(newer)                        # and is noted first
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
        good, _vals = es.take(src)                            # thread A: the recovery's record, not yet noted
        self.assertTrue(good["ok"])
        es.invalidate("and breaks once more")
        self.failing(3)
        bad, _vals = es.take(src)                             # thread B: the failure, noted first
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
        rec, _vals = es.take(src)
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
        # is released and receives nothing.
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

    def test_os_environ_is_unchanged_by_every_reader(self):
        self.command({"ANTHROPIC_API_KEY": fixture_value("key"), "A_TOKEN": fixture_value()})
        before = dict(os.environ)
        be = self.construct()
        for read in (be.key_source_status, be.refresh_key_source, be.api_health_snapshot, be.credential_fingerprint,
                     be.role_fingerprint, be.work_key_fp, be._launched_histogram):
            read()
            self.assertEqual(sorted(os.environ), sorted(before), "the names changed after %s" % read.__name__)
            self.assertFalse(any(os.environ.get(n) != before.get(n) for n in os.environ),
                             "a value changed after %s" % read.__name__)


if __name__ == "__main__":
    unittest.main()
