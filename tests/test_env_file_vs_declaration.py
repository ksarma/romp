#!/usr/bin/env python3
"""The env file's API key source against ROMP_EXPECTED_AUTH, checked once at kernel start.

A `service.env` that selects a key source — an `ANTHROPIC_API_KEY=` line with a value, or a
`ROMP_API_KEY_REF=` line — while `ROMP_EXPECTED_AUTH=login` is in force sends every session without
an explicit Billing pick to the key (effective_auth and default_auth answer "key" whenever a source is
configured). Before this check the first sign was _note_auth_source's per-init line, after a launch had
billed the wrong account. What these tests pin (sdk_backend._check_env_file_vs_declaration):

  * =login over a key line, or over a reference line, is one problem-ring line naming the file and the
    variable — never a value — said once per process (a re-constructed backend says nothing new);
  * =key is never a contradiction: a key source in the file lands the sessions keyed, as declared;
  * the remedy is worded per shape: a valued key line may be removed; a reference line must not be
    (a removed reference is a durable error in keysource), so that shape is told to drop the
    declaration or to pick Login under Billing;
  * a ROMP_CREDENTIAL_COMMAND= line is the boot verdict's to weigh (key_source_verdict), since only the
    set the command prints says whether a key is billed; its line carries the reference's remedy worded
    for a command: never remove or blank the line to get the login (both are errors at every launch);
  * undeclared is quiet, as is a declaration over a file that selects no source, whatever else the
    file carries (another service's token beside a reference is the documented shape), and so is a
    file keysource reports as an error (garbled, unreadable): the launch reports that itself;
  * a remembered gear Billing pick makes the declaration inert here too (_declared_auth);
  * the sentence describes what the code does: default_auth answers "key" under the flagged shape.

Synthetic keys (`sk-ant-TEST-…`), a synthetic reference, temp paths. The env-file path is pointed at
a temp dir before the loads so nothing here can read the machine's real one.
"""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_env_file_vs_declaration",
                      os.path.join(BIN, "romp_sdk_backend.py")).load_module()
ks = sb._keysrc

KEY = "sk-ant-TEST-0000"
REF = "op://test-vault/test-item/api-key"


class _Env(unittest.TestCase):
    """A temp env file at the path every reader resolves, the declaration cleared, the one-shot reset."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "service.env")
        self._before = {v: os.environ.get(v) for v in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV",
                                                       "ROMP_EXPECTED_AUTH", "ANTHROPIC_API_KEY",
                                                       "ROMP_API_KEY_REF", "ROMP_CREDENTIAL_COMMAND",
                                                       "ROMP_CREDENTIAL_SELECTOR_FILE")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        for v in ("ROMP_EXPECTED_AUTH", "ANTHROPIC_API_KEY", "ROMP_API_KEY_REF", "ROMP_CREDENTIAL_COMMAND"):
            os.environ.pop(v, None)
        # a command-line test's fake command gets an empty `$1`: never this machine's selector file
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.d, "selector")
        self._checked = sb._ENV_FILE_AUTH_CHECKED
        sb._ENV_FILE_AUTH_CHECKED = False
        ks._CACHE = ((), "")          # the stat-identity cache is module-global
        sb._envsrc._reset()           # so is the command source's event-keyed cache

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        sb._ENV_FILE_AUTH_CHECKED = self._checked
        ks._CACHE = ((), "")
        ks._AUTHORITATIVE_PATHS.pop(self.path, None)
        sb._envsrc._reset()

    def write_env(self, body, path=None):
        p = path or self.path
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, 0o600)
        ks._CACHE = ((), "")          # a same-second rewrite in a test can reuse the stat identity
        return p


class _Backend(_Env):
    """A backend on a manager whose environment carried no key at startup, so the env file is the only
    place a key source can come from. The startup stash is module-global; each test re-arms it."""

    def setUp(self):
        super().setUp()
        self.state = tempfile.mkdtemp()
        self._stash = sb._WORK_KEY
        self._file_checked = sb._KEY_FILE_CHECKED
        self._seen_fp = sb._FILE_KEY_SEEN_FP
        sb._WORK_KEY = ""                     # the startup claim, already made, found nothing
        sb._KEY_FILE_CHECKED = True           # the startup-vs-file line is asserted in tests/test_keyswap.py
        sb._FILE_KEY_SEEN_FP = ""
        self._fetch = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None      # never a real HTTPS GET from a test
        sb._FAST_ORG_VERDICTS.clear()
        self.logged = []

    def tearDown(self):
        sb._WORK_KEY = self._stash
        sb._KEY_FILE_CHECKED = self._file_checked
        sb._FILE_KEY_SEEN_FP = self._seen_fp
        sb._fetch_key_fast_org = self._fetch
        sb._FAST_ORG_VERDICTS.clear()
        super().tearDown()

    def construct(self):
        # `log=` is a keyword: the third positional is `notify`. A line reaches self.logged only through
        # the log wire, which is what the no-value assertions read.
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    @staticmethod
    def flagged(be):
        return [p["text"] for p in be.problems() if "while ROMP_EXPECTED_AUTH=" in p["text"]]


class EnvFileVsDeclaration(_Backend):
    def test_login_declared_over_a_key_line_is_one_line_naming_the_file_and_the_variable(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()
        lines = self.flagged(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn(self.path, lines[0])
        self.assertIn(ks.KEY_VAR, lines[0])
        self.assertIn("ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertIn("Billing pick", lines[0], "the line says what happens to billing and why")
        # the remedy for a VALUED key line: removing it is right (the file stays authoritative and the
        # sessions land on the login), or the declaration goes
        self.assertIn("remove the %s line" % ks.KEY_VAR, lines[0])
        self.assertIn("drop ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertNotIn("Do not remove", lines[0])
        self.assertFalse(any(KEY in m for m in self.logged), "no log line carries the value")
        self.assertTrue(sb._ENV_FILE_AUTH_CHECKED)
        # once per process: a re-constructed backend (the WS handler's lazy build, tests) says nothing new
        self.assertEqual(self.flagged(self.construct()), [])
        self.assertEqual(sb._check_env_file_vs_declaration(be._log, self.state), "")

    def test_login_declared_over_a_reference_line_names_the_reference_variable(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.REF_VAR, REF))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()
        lines = self.flagged(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn(ks.REF_VAR, lines[0])
        self.assertNotIn(ks.KEY_VAR, lines[0])
        self.assertFalse(any(REF in m for m in self.logged), "names, never values: the reference included")
        # The remedy for a REFERENCE line must not be "remove the line": keysource treats a removed
        # reference as an error at every launch until a source is configured again (select_source, and
        # the source marker remembers it across restarts), so an operator following that advice gets a
        # launch failure on every session without a Billing pick instead of the login the declaration
        # wants. The two fixes the code supports are dropping the declaration, or the Billing pick of
        # Login, which outranks the declaration (_declared_auth) with the reference kept.
        self.assertNotIn("remove the line", lines[0])
        self.assertIn("Do not remove the %s line" % ks.REF_VAR, lines[0])
        self.assertIn("drop ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertIn("Login under Billing", lines[0])
        self.assertIn("error at every launch", lines[0])

    def test_login_declared_over_a_command_line_is_the_verdicts_line_and_carries_the_same_remedy(self):
        """A `ROMP_CREDENTIAL_COMMAND=` line is the third shape the file can select, and this check leaves it
        to the boot verdict (key_source_verdict): whether its sessions bill a key is the SET's fact, known
        only once the command has run (a command that prints no ANTHROPIC_API_KEY satisfies the declaration),
        so the verdict says the line from the first run's record, at boot, before anything launches. That
        line carries the reference's remedy worded for a command: a removed OR blanked command line is an
        error at every launch (keysource: an empty line is still the command kind and an empty command is
        invalid; a removed line is remembered on the marker), never a fall-back to the login, so the operator
        drops the declaration, has the command print no key, or picks Login under Billing."""
        cmd = os.path.join(self.d, "cmd.sh")
        with open(cmd, "w") as fh:
            fh.write("#!/bin/sh\necho '%s=%s'\n" % (ks.KEY_VAR, KEY))
        os.chmod(cmd, 0o700)
        self.write_env("ROMP_PERF=1\n%s=%s \"$1\"\n" % (ks.CMD_VAR, cmd))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        self.assertEqual(ks.read_source(self.path).kind, "command", "the shape under test")
        # this check: quiet, the one-shot unspent; the command kind's line is the verdict's
        said = []
        log = lambda m, problem=None: said.append((str(m), problem))
        self.assertEqual(sb._check_env_file_vs_declaration(log, self.state), "")
        self.assertEqual(said, [])
        self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)
        # the backend's boot: one problem line, from the command's first run
        be = self.construct()
        self.assertEqual(self.flagged(be), [], "the file check says nothing for this shape")
        lines = [p["text"] for p in be.problems() if "ROMP_EXPECTED_AUTH=login while" in p["text"]]
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn(ks.CMD_VAR, lines[0])
        self.assertIn("sha256:" + ks.fingerprint(KEY), lines[0], "the key by fingerprint")
        self.assertFalse(any(KEY in m for m in self.logged), "no log line carries the value")
        self.assertFalse(any(cmd in m for m in self.logged), "nor the command's text: it may name an account")
        self.assertEqual(be.default_auth({}), "key", "the sentence describes what the code does")
        # the remedy: the reference's, worded for a command line, plus the one this kind alone has
        self.assertNotIn("remove the line", lines[0])
        self.assertIn("Do not remove or blank the %s line" % ks.CMD_VAR, lines[0])
        self.assertIn("drop ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertIn("Login under Billing", lines[0])
        self.assertIn("error at every launch", lines[0])
        self.assertIn("print no %s" % ks.KEY_VAR, lines[0])
        # the facts the wording rests on, in keysource: a blanked line is still the command kind and is
        # invalid; a removed line is remembered on the marker and the selection is an error, not the login
        self.write_env("ROMP_PERF=1\n%s=\n" % ks.CMD_VAR)
        blank = ks.read_source(self.path)
        self.assertEqual((blank.kind, blank.configured), ("command", True))
        with self.assertRaises(ks.KeySourceError):
            blank.validate()
        self.write_env("ROMP_PERF=1\n")
        self.assertEqual(ks.read_marker(self.path), "command")
        removed = ks.select_source()
        self.assertEqual(removed.kind, "error")
        self.assertIn("was removed", removed.error)

    def test_the_direct_call_returns_the_variable_it_named_and_files_a_problem(self):
        self.write_env("%s=%s\n" % (ks.REF_VAR, REF))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        said = []
        log = lambda m, problem=None: said.append((str(m), problem))
        self.assertEqual(sb._check_env_file_vs_declaration(log, self.state), ks.REF_VAR)
        self.assertEqual([p for _, p in said], [True], "a problem-ring line, not a plain log line")
        self.assertEqual(sb._check_env_file_vs_declaration(log, self.state), "")
        self.assertEqual(len(said), 1)

    def test_the_sentence_describes_what_the_code_does(self):
        self.write_env("%s=%s\n" % (ks.KEY_VAR, KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()
        self.assertEqual(len(self.flagged(be)), 1)
        self.assertEqual(be.default_auth({}), "key", "a session without an explicit pick launches keyed")

    def test_key_declared_over_a_key_source_is_quiet(self):
        for body in ("%s=%s\n" % (ks.KEY_VAR, KEY), "%s=%s\n" % (ks.REF_VAR, REF)):
            self.write_env(body)
            os.environ["ROMP_EXPECTED_AUTH"] = "key"
            be = self.construct()
            self.assertEqual(self.flagged(be), [], "the sessions land keyed, as declared: %r" % body)
            self.assertFalse(sb._ENV_FILE_AUTH_CHECKED, "a quiet pass does not spend the one shot")

    def test_undeclared_is_quiet(self):
        self.write_env("%s=%s\n" % (ks.KEY_VAR, KEY))
        be = self.construct()
        self.assertEqual(self.flagged(be), [])
        self.assertEqual(sb._check_env_file_vs_declaration(be._log, self.state), "")
        self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)

    def test_login_declared_over_a_file_that_selects_no_source_is_quiet(self):
        # Other services' credentials are the installer's invited shape for this file, and the 1Password
        # service-account token beside a reference is the documented one; none of them is what a launch
        # injects as the sessions' key, so none contradicts the declaration. An EMPTY key line selects
        # nothing either (keysource: a file source with no value is not configured).
        self.write_env("ROMP_PERF=1\nROMP_DIR=/nonexistent/x\nHF_TOKEN=x\nOP_SERVICE_ACCOUNT_TOKEN=x\n"
                       "FOO_API_KEY=x\n%s=\n" % ks.KEY_VAR)
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()
        self.assertEqual(self.flagged(be), [], be.problems())
        self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)

    def test_login_declared_over_a_source_keysource_reports_as_an_error_is_quiet(self):
        """A garbled or unreadable file is an error-kind source (keysource.read_source), which the launch
        itself reports (KeySource.validate raises there). Nothing here weighs it against the declaration:
        the check stays silent, spends no one-shot, and never raises into the backend's constructor."""
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        # a reference line that is not valid UTF-8: parse_source reports it, never a source it selects
        with open(self.path, "wb") as fh:
            fh.write(b"ROMP_PERF=1\n" + ks.REF_VAR.encode() + b"=op://\xff\xfe/item/field\n")
        os.chmod(self.path, 0o600)
        ks._CACHE = ((), "")
        self.assertEqual(ks.read_source(self.path).kind, "error", "the shape under test")
        be = self.construct()
        self.assertEqual(self.flagged(be), [], be.problems())
        self.assertFalse(sb._ENV_FILE_AUTH_CHECKED, "a quiet pass does not spend the one shot")
        said = []
        log = lambda m, problem=None: said.append((str(m), problem))
        self.assertEqual(sb._check_env_file_vs_declaration(log, self.state), "")
        self.assertEqual(said, [])
        if os.geteuid() == 0:
            return                            # root reads a 000 file: the unreadable shape cannot be built
        # an unreadable file: the other way read_source reports an error
        self.write_env("%s=%s\n" % (ks.KEY_VAR, KEY))
        os.chmod(self.path, 0)
        try:
            ks._CACHE = ((), "")
            self.assertEqual(ks.read_source(self.path).kind, "error", "the shape under test")
            self.assertEqual(sb._check_env_file_vs_declaration(log, self.state), "")
            self.assertEqual(said, [])
            self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)
            self.assertEqual(self.flagged(self.construct()), [])
        finally:
            os.chmod(self.path, 0o600)

    def test_a_missing_file_is_quiet(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()                 # no file was ever written at self.path
        self.assertEqual(self.flagged(be), [])
        self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)

    def test_a_remembered_billing_pick_makes_the_declaration_inert_here_too(self):
        # Q3: set_auth's durable trace (the remembered auth default) is the pick event; from then on the
        # env declaration is stale doctrine and _note_auth_source judges against the pick. Under a login
        # pick every spawn is seeded auth=login, so the file's key wins for nobody: nothing to say.
        for pick in ("login", "key"):
            self.write_env("%s=%s\n" % (ks.KEY_VAR, KEY))
            os.environ["ROMP_EXPECTED_AUTH"] = "login"
            sb.write_sdk_default(Path(self.state), auth=pick)
            be = self.construct()
            self.assertEqual(self.flagged(be), [], "pick=%s: %r" % (pick, be.problems()))
            self.assertFalse(sb._ENV_FILE_AUTH_CHECKED)
            self.assertEqual(sb._declared_auth(Path(self.state)), (pick, "pick"))

    def test_the_check_reads_the_installers_path_variable(self):
        other = self.write_env("%s=%s\n" % (ks.KEY_VAR, KEY), path=os.path.join(self.d, "elsewhere.env"))
        os.environ["ROMP_SERVICE_ENV_FILE"] = other
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        be = self.construct()
        lines = self.flagged(be)
        self.assertEqual(len(lines), 1, be.problems())
        self.assertIn(other, lines[0])


if __name__ == "__main__":
    unittest.main()
