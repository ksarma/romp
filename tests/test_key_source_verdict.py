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
  BothModes — ROMP_EXPECTED_AUTH=key with nothing to inject and no apiKeyHelper.
  UnitParsing — Environment= lines and plist pairs (names only), ExecStart shapes and drop-in
    overrides, the paths _unit_texts reads (bin/romp-service's variables).
  NoValueAnywhere — with fixture values in every input, the verdict's JSON carries none.
  BootAndHealth — the backend runs the verdict once at construction, logs its lines (the problem
    ring for the flagged ones), and api_health_snapshot()["keySource"] carries the documented fields;
    in file mode with nothing declared, no "key source:" line is logged at all.

Synthetic throughout: values are "romp-test-fixture-" + a uuid assembled at run time; the fake
command is a script in a temp dir; paths are temp paths.
"""
import json
import os
import tempfile
import unittest
import uuid
from importlib.machinery import SourceFileLoader

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
    def test_key_declared_with_nothing_to_inject_and_no_helper_rings(self):
        for env, extra in (({"ROMP_EXPECTED_AUTH": "key"}, ""),
                           (dict(CMD, ROMP_EXPECTED_AUTH="key"), "the credential command prints no ANTHROPIC_API_KEY")):
            r = verdict(env, snapshot=ok_snap() if "ROMP_CREDENTIAL_COMMAND" in env else None)
            line = [t for t in problems(r) if "names no apiKeyHelper" in t]
            self.assertEqual(len(line), 1, (env, texts(r)))
            self.assertIn("ROMP_EXPECTED_AUTH=key", line[0])
            self.assertIn("land on the login", line[0])
            if extra:
                self.assertIn(extra, line[0])
            else:
                self.assertNotIn("credential command", line[0])
            self.assertEqual([t for t in problems(verdict(env, helper_command="h",
                                                          snapshot=ok_snap() if "ROMP_CREDENTIAL_COMMAND" in env else None))
                              if "apiKeyHelper" in t], [], "a helper answers the declaration")
            self.assertEqual([t for t in problems(verdict(env, work_key_present=True,
                                                          snapshot=ok_snap() if "ROMP_CREDENTIAL_COMMAND" in env else None))
                              if "apiKeyHelper" in t], [], "so does a key to inject")

    def test_the_declaration_is_read_from_the_given_environ(self):
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": " Login "})["expectedAuth"], "login")
        self.assertEqual(verdict({"ROMP_EXPECTED_AUTH": "both"})["expectedAuth"], "")
        self.assertEqual(verdict()["expectedAuth"], "")


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

    def test_a_verdict_that_cannot_be_taken_is_a_logged_problem_not_a_failed_construction(self):
        self.command({"A_TOKEN": fixture_value()})
        saved = sb._unit_texts
        sb._unit_texts = lambda environ=None: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            be = self.construct()
        finally:
            sb._unit_texts = saved
        self.assertEqual(be.key_source, {"mode": "command", "lines": []})
        self.assertTrue(any("boot verdict failed" in p["text"] for p in be.problems()))
        self.assertEqual(be.api_health_snapshot()["keySource"]["mode"], "command")


if __name__ == "__main__":
    unittest.main()
