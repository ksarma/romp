#!/usr/bin/env python3
"""The fork's keyswap contract (the user 2026-09-05): this fork does not write API keys to files.

Upstream's `romp keyswap <name>` rewrites the `ANTHROPIC_API_KEY=` line of the manager's env file
from a sibling file (`service.env.<name>`). tests/test_keyswap.py carries upstream's tests for the
parts the fork keeps — the live read, the bare report, `--cycle`. This file pins what the fork changes:

  NamedSwapRefused — `romp keyswap <name>` exits 2 with one fixed message, before the file is read or
    a kernel is dialed; no flag lets it through; the bare report's guidance names the cycle, never a
    file to create; the CLI carries no call that writes the key.
  HelperSessionsCycle — `SdkBackend.cycle_key` reconnects a session the kernel handed NO key but whose
    CLI reported one at init (apiKeySource: the apiKeyHelper) — status "helper" — because a new
    process is the only way a rotated key reaches it. Upstream reads such a session as login-billed
    and skips it, which made `--cycle-all` a no-op on a box whose every session bills through the
    helper. There is no fingerprint to converge on, so a repeated cycle reconnects it again.
  EnvFileCredentialWarning — at backend construction, a credential-shaped line in the env file
    (`ANTHROPIC_API_KEY`, any `*_API_KEY`, any `*_TOKEN`, with a non-empty value) under a declared
    `ROMP_EXPECTED_AUTH` is said once, loudly (the problem ring), naming the file and the variable
    NAME — never the value. Undeclared, nothing is said.

Synthetic keys (`sk-ant-TEST-…`), synthetic sids, temp paths only. The env-file path is pointed at a
temp dir before the loads so nothing here can read the machine's real one.
"""
import io
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_keyswap_refusal", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
cli = SourceFileLoader("romp_keyswap_cli_refusal", os.path.join(BIN, "romp-keyswap")).load_module()
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"

OLD_KEY = "sk-ant-TEST-0000"
NEW_KEY = "sk-ant-TEST-1111"
SID = "11111111-2222-3333-4444-555555555501"


class _Env(unittest.TestCase):
    """A temp env file at the path every reader resolves, the declaration cleared, the one-shot reset."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "service.env")
        self._before = {v: os.environ.get(v) for v in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV",
                                                       "ROMP_EXPECTED_AUTH", "ANTHROPIC_API_KEY")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self._said = sb._CREDENTIAL_LINE_SAID
        sb._CREDENTIAL_LINE_SAID = False
        ks._CACHE = ((), "")

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        sb._CREDENTIAL_LINE_SAID = self._said
        ks._CACHE = ((), "")

    def write_env(self, body):
        with open(self.path, "w") as fh:
            fh.write(body)
        os.chmod(self.path, 0o600)
        ks._CACHE = ((), "")

    def sibling(self, name, body):
        with open(self.path + "." + name, "w") as fh:
            fh.write(body)
        os.chmod(self.path + "." + name, 0o600)


class NamedSwapRefused(_Env):
    def setUp(self):
        super().setUp()
        self.write_env("ROMP_PERF=1\n%s=%s\nROMP_EXPECTED_AUTH=key\n" % (ks.KEY_VAR, OLD_KEY))
        self.sibling("lowprio", "%s=%s\n" % (ks.KEY_VAR, NEW_KEY))
        self.posted, self.dialed = [], []
        self._saved = (cli._kernel, cli._post, ks.write_key)
        cli._kernel = lambda: self.dialed.append(1) or None
        cli._post = lambda u, p, b: self.posted.append((p, b)) or {"ok": True, "keyFp": "", "rows": []}

        def never(*a, **k):
            raise AssertionError("write_key must not be reached from the CLI")
        ks.write_key = never

    def tearDown(self):
        cli._kernel, cli._post, ks.write_key = self._saved
        super().tearDown()

    def run_cli(self, *argv):
        said, buf, was = [], io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            rc = cli.main(list(argv), out=said.append)
        finally:
            sys.stderr = was
        return rc, "\n".join(said), buf.getvalue()

    def test_a_named_source_exits_2_with_the_fixed_message_before_reading_anything(self):
        mtime = os.stat(self.path).st_mtime_ns
        rc, out, err = self.run_cli("lowprio")
        self.assertEqual(rc, 2)
        self.assertEqual(err, cli.REFUSAL, "one fixed message, so a reword is a deliberate edit")
        self.assertEqual(out, "", "nothing on stdout: the refusal is the whole answer")
        self.assertEqual(ks.read_key(self.path), OLD_KEY)
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime, "the file is not even rewritten in place")
        self.assertEqual(self.dialed, [], "no kernel is dialed for a refused request")
        self.assertEqual(self.posted, [])

    def test_the_message_says_where_keys_live_and_what_to_run_instead(self):
        m = cli.REFUSAL
        self.assertIn("does not write API keys to files", m, "a policy the code can stand behind, not a claim about one box")
        self.assertNotIn("this installation", m)
        self.assertIn("apiKeyHelper", m)
        self.assertIn("manager's\n             environment", m)
        self.assertIn("romp keyswap --cycle-all", m)
        self.assertIn("romp refresh", m)
        self.assertNotIn("service.env.", m, "never a sibling-file recipe")
        for key in (OLD_KEY, NEW_KEY):
            self.assertNotIn(key, m)

    def test_a_missing_or_keyless_source_is_refused_the_same_way(self):
        # the refusal does not depend on the filesystem: an unknown name, a file with no key line and a
        # real candidate all get the same answer, and none of upstream's per-case messages
        self.sibling("empty", "ROMP_PERF=1\n")
        for name in ("nosuch", "empty", "lowprio"):
            rc, out, err = self.run_cli(name)
            self.assertEqual(rc, 2, name)
            self.assertEqual(err, cli.REFUSAL, name)
            self.assertNotIn("no such key file", err)
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_a_name_with_a_cycle_is_refused_with_it_and_nothing_cycles(self):
        for argv in (["lowprio", "--cycle-all"], ["lowprio", "--cycle", "web"], ["--cycle-all", "lowprio"]):
            rc, _out, err = self.run_cli(*argv)
            self.assertEqual(rc, 2, argv)
            self.assertEqual(err, cli.REFUSAL, argv)
        self.assertEqual(self.posted, [], "the name made it a swap request; no reconnect rides along")

    def test_an_explicit_path_is_refused_too(self):
        rc, _out, err = self.run_cli(os.path.join(self.d, "other.env"))
        self.assertEqual(rc, 2)
        self.assertEqual(err, cli.REFUSAL)

    def test_the_bare_report_points_at_the_cycle_and_never_at_a_file_to_create(self):
        os.unlink(self.path + ".lowprio")
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("candidates  none (this fork does not write API keys to files; the named swap is disabled)", out)
        self.assertNotIn("this installation", out)
        self.assertIn("romp keyswap --cycle-all", out)
        self.assertNotIn("swap with:", out)
        self.assertNotIn("chmod 600", out, "upstream's line told the operator to create one file per key")
        self.assertNotIn("keep one file per key", out)
        self.assertNotIn(OLD_KEY, out)

    def test_a_cycle_with_no_kernel_does_not_claim_a_swap_happened(self):
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("no running kernel", out)
        self.assertNotIn("already swapped", out, "nothing is ever swapped here")
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 404"}
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("romp refresh", out)
        self.assertNotIn("already swapped", out)

    def test_the_cycle_explanations_know_the_helper_status(self):
        text = cli._explain("helper")
        self.assertIn("apiKeyHelper", text)
        self.assertIn("once per rotation", text)
        self.assertIn("reconnects on every run that names it", text, "honest: it never reads \"current\"")
        self.assertNotEqual(cli._explain("helper"), "helper", "an unexplained status prints its raw word")

    def test_the_re_run_hint_names_the_skipped_rows_and_does_not_promise_current_for_helper_rows(self):
        # cycle_key returns "helper" on every run (no fingerprint to converge on), so "re-run the same
        # --cycle; sessions already moved read current" was false for a helper-billed box: every re-run
        # reconnected every quiet helper session again. The hint now names only the skipped rows.
        cli._kernel = lambda: "http://127.0.0.1:29855"
        rows = [{"session": "web", "status": "working"}, {"session": "api", "status": "helper"},
                {"session": "tests", "status": "working"}]
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": rows}   # the compare step passes
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("re-run --cycle web,tests once quiet", out, "the skipped rows, by name")
        self.assertIn("Name only those", out)
        self.assertIn("helper-billed one reconnects again on every run that names it", out)
        self.assertNotIn("re-run the same --cycle", out)
        self.assertNotIn("sessions already moved read", out)
        # no working row → no re-run hint at all (the helper row's own text still says it re-runs the helper)
        rows[:] = [{"session": "api", "status": "helper"}]
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertNotIn("re-run --cycle", out)
        self.assertNotIn("Name only those", out)

    def test_a_second_positional_is_counted_never_echoed(self):
        # a key value typed where a name was expected must not reach stderr
        rc, out, err = self.run_cli("lowprio", "sk-ant-TEST-9999")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("one source at a time (2 positional arguments given)", err)
        self.assertNotIn("sk-ant-TEST-9999", err)
        self.assertNotIn("lowprio", err)
        self.assertEqual(cli.parse_args(["a", "b", "c"])[3], "one source at a time (3 positional arguments given)")

    def test_the_cli_carries_no_call_that_writes_the_key(self):
        # no escape hatch: not a flag, not a dead branch — the only writer of the key line is upstream's
        # module function, and nothing under bin/ or cli/ calls it
        for rel in ("cli/keyswap.py", "bin/romp-keyswap", "bin/romp"):
            src = open(os.path.join(ROOT, rel)).read()
            self.assertNotIn("write_key(", src, rel)


class _Backend(_Env):
    """A backend on a keyless manager: the env file carries no key line, the startup claim is empty,
    so every unpicked session launches on the login and the CLI's apiKeyHelper supplies the key."""

    def setUp(self):
        super().setUp()
        self.write_env("ROMP_PERF=1\nROMP_EXPECTED_AUTH=key\n")
        self.state = tempfile.mkdtemp()
        self._stash, self._checked = sb._WORK_KEY, sb._KEY_FILE_CHECKED
        sb._WORK_KEY = ""
        sb._KEY_FILE_CHECKED = True
        self._fetch = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None
        sb._FAST_ORG_VERDICTS.clear()
        self.logged = []
        self.be = self.construct()

    def construct(self):
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def tearDown(self):
        sb._WORK_KEY, sb._KEY_FILE_CHECKED = self._stash, self._checked
        sb._fetch_key_fast_org = self._fetch
        sb._FAST_ORG_VERDICTS.clear()
        super().tearDown()

    def _live(self, auth_live, auth=""):
        # cycle_key answers "unknown" for a sid the backend does not own, so the registry entry comes
        # first (spawn), then the live session object the way upstream's CycleReconnects builds it
        self.be.sessions.pop(SID, None)
        if not self.be.owns(SID):
            self.be.spawn("web", "/tmp", sid=SID, auth=auth)
        reg = {"sid": SID, "name": "web", "cwd": "/tmp"}
        if auth:
            reg["auth"] = auth
        s = sb.SdkSession(self.be, reg)
        s.auth_live = auth_live
        self.reconnects, self.defers = [], []
        s.request_reconnect = lambda defer=True: (self.reconnects.append(SID), self.defers.append(defer))
        self.be.sessions[SID] = s
        return s


class HelperSessionsCycle(_Backend):
    def test_a_session_the_cli_reported_keyed_is_reconnected_though_the_kernel_handed_it_no_key(self):
        s = self._live("key")
        self.assertEqual(s.effective_auth(), "login", "the kernel injects nothing: no key anywhere it reads")
        self.assertEqual(self.be.cycle_key(SID), "helper")
        self.assertEqual(self.reconnects, [SID])
        self.assertEqual(self.defers, [False], "immediate-only, like every key cycle")
        line = [m for m in self.logged if m.startswith("keyswap (web)")]
        self.assertEqual(len(line), 1)
        self.assertIn("credential helper", line[0])
        self.assertNotIn("sha256", line[0], "there is no key fingerprint to print for a helper session")

    def test_a_session_the_cli_reported_on_the_login_is_left_alone_as_before(self):
        self._live("login")
        self.assertEqual(self.be.cycle_key(SID), "login")
        self._live("")
        self.assertEqual(self.be.cycle_key(SID), "login", "no init yet: nothing says a key is in play")
        self.assertEqual(self.reconnects, [])

    def test_in_flight_work_still_skips_a_helper_session(self):
        s = self._live("key")
        s._bg_tasks["t1"] = {"since": 1}
        self.assertEqual(self.be.cycle_key(SID), "working")
        s._bg_tasks.clear()
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(SID), "working")
        self.assertEqual(self.reconnects, [], "a reconnect would kill the work — the same rule as upstream's")

    def test_a_repeated_cycle_reconnects_it_again_since_there_is_nothing_to_converge_on(self):
        self._live("key")
        self.assertEqual(self.be.cycle_key(SID), "helper")
        self.assertEqual(self.be.cycle_key(SID), "helper", "no fingerprint → never \"current\"; run it once per rotation")
        self.assertEqual(self.reconnects, [SID, SID])

    def test_an_explicit_login_pick_whose_cli_still_reports_a_key_is_cycled(self):
        # the pick says login, the CLI says a key (the helper found one anyway): the kernel injects
        # nothing either way, and a new process is what re-runs the helper — so it cycles
        self._live("key", auth="login")
        self.assertEqual(self.be.cycle_key(SID), "helper")

    def test_the_kernel_injected_path_is_unchanged(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        s = self._live("key", auth="key")
        s._launched_key_fp = ks.fingerprint(NEW_KEY)          # launched on a previous key
        self.assertEqual(self.be.cycle_key(SID), "cycling", "upstream's arm, untouched")
        s._launched_key_fp = ks.fingerprint(OLD_KEY)
        self.assertEqual(self.be.cycle_key(SID), "current")


class EnvFileCredentialWarning(_Backend):
    def _problems(self):
        return [p["text"] for p in self.be.problems()]

    def _warned(self):
        return [t for t in self._problems() if "credential line" in t]

    def test_login_declared_and_a_key_line_fires_once_naming_the_file_and_the_variable_not_the_value(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.logged.clear()
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1, self._problems())
        self.assertIn(self.path, lines[0])
        self.assertIn(ks.KEY_VAR, lines[0])
        self.assertIn("ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertIn("does not write API keys to files", lines[0])
        self.assertNotIn("this installation", lines[0], "a fork policy, not a claim about one box")
        self.assertIn("would be injected at launch", lines[0], "ANTHROPIC_API_KEY is the variable the launch injects")
        self.assertIn("Billing pick", lines[0], "…so its line names the billing consequence")
        self.assertNotIn(OLD_KEY, lines[0])
        self.assertTrue(any(OLD_KEY not in m for m in self.logged))
        self.assertFalse(any(OLD_KEY in m for m in self.logged), "no log line carries the value")
        # once per process: a re-constructed backend (the WS handler's lazy build, tests) says nothing new
        be2 = self.construct()
        self.assertEqual([p["text"] for p in be2.problems() if "credential line" in p["text"]], [])

    def test_key_declared_fires_too_the_apikeyhelper_shape(self):
        self.write_env("ROMP_PERF=1\n%s=%s\nROMP_EXPECTED_AUTH=key\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1, self._problems())
        self.assertIn("ROMP_EXPECTED_AUTH=key", lines[0])
        self.assertIn("apiKeyHelper", lines[0])
        self.assertNotIn(OLD_KEY, lines[0])

    def test_undeclared_is_quiet_upstreams_ordinary_file_key_box(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        self.assertEqual(self._warned(), [])
        self.assertEqual(sb._warn_credential_lines_in_env_file(self.be._log), [])
        self.assertFalse(sb._CREDENTIAL_LINE_SAID, "a quiet pass does not spend the one shot")

    def test_a_declaration_over_a_file_with_no_credential_is_quiet(self):
        self.write_env("ROMP_PERF=1\nROMP_EXPECTED_AUTH=login\nROMP_DIR=/tmp/x\n")
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        self.assertEqual(self._warned(), [])
        self.assertFalse(sb._CREDENTIAL_LINE_SAID)

    def test_which_lines_count(self):
        # each empty-value line is followed by a comment line on purpose: compiled to bytecode, this
        # literal holds real newlines, and a secret scanner's generic rule would otherwise read
        # `EMPTY_TOKEN=` + newline + the next NAME= as a key and its value (the repo's own
        # gitleaks check scans the working tree, __pycache__ included)
        self.write_env("# a comment\n\nFOO_API_KEY=abc\nBAR_TOKEN='xyz'\nNOT_A_SECRET=1\n"
                       "BAR_TOKEN=again\nTOKEN_PREFIX_X=1\nQUOTED_API_KEY=\"\"\n# an empty value\n"
                       "EMPTY_TOKEN=\n# is not a credential\n")
        self.assertEqual(sb._credential_names_in_env_file(self.path), ["FOO_API_KEY", "BAR_TOKEN"])
        self.assertEqual(sb._credential_names_in_env_file(os.path.join(self.d, "absent.env")), [])
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn("FOO_API_KEY, BAR_TOKEN", lines[0])
        self.assertIn("credential lines", lines[0])
        for value in ("abc", "xyz", "again"):
            self.assertNotIn("=" + value, lines[0])
        # neither is the variable the launch injects, so the line makes no billing claim about them
        self.assertIn("FOO_API_KEY, BAR_TOKEN: a credential in a file contradicts the declared auth model", lines[0])
        self.assertNotIn("Billing pick", lines[0])
        self.assertNotIn("injected", lines[0])
        self.assertNotIn("apiKeyHelper", lines[0])

    def test_a_mixed_file_names_the_billing_consequence_for_the_key_and_the_plain_line_for_the_rest(self):
        self.write_env("%s=%s\nHF_TOKEN=abc\nROMP_SERVE_TOKEN=xyz\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn("ANTHROPIC_API_KEY would be injected at launch: the sessions' key reaches Claude Code through its apiKeyHelper", lines[0])
        self.assertIn("HF_TOKEN, ROMP_SERVE_TOKEN: a credential in a file contradicts the declared auth model", lines[0])
        self.assertIn("remove the lines and rotate the values, since they reached a file", lines[0])
        for value in (OLD_KEY, "abc", "xyz"):
            self.assertNotIn(value, lines[0])

    def test_the_check_reads_the_installers_variable_for_the_path(self):
        other = os.path.join(self.d, "elsewhere.env")
        with open(other, "w") as fh:
            fh.write("%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_SERVICE_ENV_FILE"] = other
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn(other, lines[0])


if __name__ == "__main__":
    unittest.main()
