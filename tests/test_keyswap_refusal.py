#!/usr/bin/env python3
"""The fork's keyswap contract (the user 2026-09-05): this fork does not write API keys to files.

Upstream's `romp keyswap <name>` rewrites the `ANTHROPIC_API_KEY=` line of the manager's env file
from a sibling file (`service.env.<name>`). tests/test_keyswap.py carries upstream's tests for the
parts the fork keeps — the live read, the bare report, `--cycle`. This file pins what the fork changes:

  NamedSwapRefused — in FILE mode `romp keyswap <name>` exits 2 with one fixed message, before the file
    is read or a kernel is dialed; no flag lets it through; the bare report's guidance names the cycle,
    never a file to create; the CLI carries no call that writes the key. (In COMMAND mode the same
    argument selects a declared credential by writing the selector file — a name, never a key — which
    tests/test_keyswap.py's KeyswapCliCommandMode pins.)
  HelperSessionsConverge — in COMMAND mode (ROMP_CREDENTIAL_COMMAND set; kernel/envsource.py) a
    session the kernel handed NO key but whose CLI reported one at init (apiKeySource: the
    apiKeyHelper) is stamped at connect with the fingerprint of the helper's output (envsource runs
    the configured helper and hashes inside), and `SdkBackend.cycle_key` converges on it: the same
    fingerprint reads "current", a rotation behind the helper reads "cycling" once and "current"
    after; a refusal on a session still stamped with the pre-rotation output re-runs neither the
    command nor the helper; a refresh landing between a connect's read of the set and its helper
    fingerprint leaves that fingerprint stored stale, not served as current. This replaces the fork's earlier always-reconnect "helper" outcome (2026-09-05, the same
    day): upstream reads such a session as login-billed and skips it, which made `--cycle-all` a
    no-op on a box whose every session bills through the helper; the always-reconnect answer fixed
    that but churned every quiet helper session on every run. In FILE mode the compare is upstream's
    (a non-keyed session reads "login"). The role variables the set injects converge the same way.
  EnvFileCredentialWarning — at backend construction, a credential-shaped line in the env file
    (`ANTHROPIC_API_KEY`, any `*_API_KEY`, any `*_TOKEN`, with a non-empty value) under a declared
    `ROMP_EXPECTED_AUTH` is said once, loudly (the problem ring), naming the file and the variable
    NAME — never the value. Undeclared, nothing is said.

Synthetic keys (`sk-ant-TEST-…`), synthetic sids, temp paths only; the command-mode values are
assembled at run time ("romp-test-fixture-" + a uuid) and the fake command and helper are scripts
written into a temp dir. The env-file path is pointed at a temp dir before the loads so nothing here
can read the machine's real one; conftest keeps ROMP_CREDENTIAL_* unset until a test sets them.
"""
import io
import json
import os
import sys
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
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_keyswap_refusal", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
cli = SourceFileLoader("romp_keyswap_cli_refusal", os.path.join(BIN, "romp-keyswap")).load_module()
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"
es = sb._envsrc


def fixture_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


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
        self.assertIn("skips sessions billed through the apiKeyHelper", m,
                      "honest about file mode: a non-keyed session reads as the login there and is not cycled")
        self.assertIn("--cycle-all in command mode (set ROMP_CREDENTIAL_COMMAND", m)
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
        self.assertIn("key-billed sessions reconnect", out, "the file-mode cycle reaches key-billed sessions")
        self.assertIn("they cycle in command mode", out, "…helper-billed ones are named as cycling in command mode")
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

    def test_the_helper_status_word_is_gone_from_the_cli(self):
        # cycle_key's always-reconnect "helper" outcome was replaced by fingerprint convergence (kernel
        # side: HelperSessionsConverge below), so the CLI has no explanation for it: an unexplained
        # status prints its raw word, and no row text promises a reconnect on every run
        self.assertEqual(cli._explain("helper"), "helper")
        src = open(os.path.join(ROOT, "cli", "keyswap.py")).read()
        self.assertNotIn("reconnects on every run", src)
        self.assertNotIn("once per rotation", src)
        self.assertIn("apiKeyHelper", cli._explain("cycling") + cli.REFUSAL, "the helper is still named where it bills")

    def test_the_re_run_hint_names_the_skipped_rows_and_promises_current(self):
        # every status converges now (a session already moved reads "current" on the re-run), so the
        # hint names only the rows skipped for in-flight work and says exactly that
        cli._kernel = lambda: "http://127.0.0.1:29855"
        rows = [{"session": "web", "status": "working"}, {"session": "api", "status": "current"},
                {"session": "tests", "status": "working"}]
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": rows}   # the compare step passes
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("re-run --cycle web,tests once quiet; sessions already on this key read \"current\"", out)
        self.assertNotIn("helper-billed", out)
        self.assertNotIn("Name only those", out)
        rows[:] = [{"session": "api", "status": "current"}]
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertNotIn("re-run --cycle", out, "no skipped row, no hint")

    def test_a_cycling_row_carries_the_fingerprint_its_client_launched_on(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        fp = ks.fingerprint(NEW_KEY)                       # a fingerprint taken at run time, not a literal
        rows = [{"session": "web", "status": "cycling", "from": fp},
                {"session": "api", "status": "cycling", "from": ""}]
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": rows}
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % fp, out)
        self.assertIn("  api            reconnecting now — history kept\n", out + "\n")

    def test_refresh_in_file_mode_is_a_re_read_and_the_report_says_so(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY), "keySource": "file", "rows": [],
            "refreshed": {"from": "deadbeefcafe", "to": ks.fingerprint(OLD_KEY), "err": ""}}
        rc, out, _err = self.run_cli("--refresh")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": [], "refresh": True})])
        self.assertIn("kernel      reads sha256:%s (re-read now: was sha256:deadbeefcafe)" % ks.fingerprint(OLD_KEY), out)
        self.assertNotIn("MISMATCH", out)

    def test_a_kernel_in_command_mode_under_a_file_mode_shell_is_a_mismatch(self):
        # the kernel's environment carries ROMP_CREDENTIAL_COMMAND and this shell's (and service.env) do
        # not: the report says which side is which and what makes them agree
        cli._kernel = lambda: "http://127.0.0.1:29855"
        fp = ks.fingerprint(NEW_KEY)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": fp, "keySource": "command", "rows": []}
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      reads sha256:%s in COMMAND mode" % fp, out)
        self.assertIn("MISMATCH    the kernel is in command mode and this shell is not: the kernel pinned command mode when it", out)
        self.assertIn("this shell reads no ROMP_CREDENTIAL_COMMAND now. The kernel got the line from one of:", out)
        # the /keycycle answer cannot say WHERE the kernel got the line (the manager's environment, a
        # service.env line removed since the kernel started, another service.env, or the shell that ran
        # `romp up` all read the same), so the report asserts no cause: it lists the places, each with
        # its remedy
        self.assertNotIn("the kernel's environment carries", out, "a cause to check, not a fact")
        # the manager's environment is TWO causes with two remedies: a service.env line the manager loaded
        # goes at the restart, which re-reads the file; a line in the unit, a drop-in or the profile a
        # shell-wrapped ExecStart sources is re-applied by a restart, so it is removed where it is first
        self.assertIn("- service.env as the manager loaded it at its start, which every kernel inherits: the line is", out)
        self.assertIn("gone from the file this shell reads, so restart the manager (the restart re-reads the file);", out)
        self.assertIn("`romp refresh` alone keeps the mode", out)
        self.assertIn("- the unit's Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources (Linux), or the", out)
        self.assertIn("plist's EnvironmentVariables (macOS): a manager restart re-applies these, so remove the line there", out)
        self.assertIn("first, reload the definition, then restart the manager. Linux: `systemctl --user daemon-reload`", out)
        self.assertIn("after editing a unit or a drop-in, then the restart. macOS: `launchctl kickstart -k` restarts the", out)
        self.assertNotIn("the unit's Environment=, or service.env as the manager loaded it", out,
                         "one cause with one remedy would send a unit line's owner to a restart that re-applies it")
        # the macOS form of that cause: the plist's EnvironmentVariables are part of the loaded job definition,
        # which `launchctl kickstart -k` restarts without re-reading the plist, so the job is booted out and
        # bootstrapped again. The label and the plist path are bin/romp-service's own (LABEL, LAUNCHD_DIR)
        self.assertIn("job as loaded and does not re-read the plist, so reload it: `launchctl bootout", out)
        self.assertIn("gui/$(id -u)/com.romp.manager`, then `launchctl bootstrap gui/$(id -u)", out)
        self.assertIn("~/Library/LaunchAgents/com.romp.manager.plist`. `romp-service install` does that on macOS (it", out)
        svc = open(os.path.join(BIN, "romp-service"), encoding="utf-8").read()
        self.assertIn('LABEL="com.romp.manager"', svc)
        self.assertIn('LAUNCHD_DIR="${ROMP_LAUNCHD_DIR:-$HOME/Library/LaunchAgents}"', svc)
        self.assertIn('PLIST="$LAUNCHD_DIR/$LABEL.plist"', svc)
        # `romp-service install` is named for what it does per platform: on macOS a plist rewrite and a
        # reload of the job (bootout, bootstrap), on Linux a unit rewrite and a systemd reload with no restart
        # of a running manager (daemon-reload, enable --now)
        self.assertIn("rewrites the plist and reloads the job); on Linux it rewrites the unit and reloads systemd and", out)
        self.assertIn("leaves a running manager as it is, so restart it after", out)
        self.assertIn('"$LAUNCHCTL" bootout "gui/$(id -u)/$LABEL"', svc)
        self.assertIn('"$LAUNCHCTL" bootstrap "gui/$(id -u)" "$PLIST"', svc)
        self.assertIn("systemctl --user daemon-reload\n            systemctl --user enable --now romp-manager.service", svc)
        self.assertNotIn("systemctl --user restart", svc.split("case \"${1:-status}\" in")[1].split("uninstall)")[0],
                         "install restarts no running manager on Linux")
        # the kernel may read ANOTHER service.env: kernel/keysource.py resolves the path from ROMP_SERVICE_ENV_FILE
        # wherever the kernel's environment sets it (the installer's unit or plist line is one source; a drop-in,
        # a profile or the shell that ran `romp up` are others), the answer carries no path, and this shell's is
        # named, with the places to look per platform
        self.assertIn("- another service.env: the kernel resolves the path from ROMP_SERVICE_ENV_FILE wherever its", out)
        self.assertIn("environment sets it (the installer's line in the unit or the plist for a non-default path, a", out)
        self.assertIn("drop-in, the profile a shell-wrapped ExecStart sources, the shell that ran `romp up`), so it may", out)
        self.assertIn("read a file other than this shell's (%s):" % self.path, out)
        self.assertIn("run this command with the same ROMP_SERVICE_ENV_FILE, or look for the variable in the unit and", out)
        self.assertIn("its drop-ins on Linux, the plist on macOS", out)
        self.assertNotIn("the installer carries", out, "the installer is one source of the variable, not the cause")
        self.assertNotIn("check the unit for that variable", out, "the unit is the Linux place; the plist is the macOS one")
        self.assertEqual(ks.service_env_path(), self.path, "the CLI names the path the kernel's own resolver gives this environment")
        self.assertIn("- service.env, edited since the kernel read it at its start: `romp refresh`", out)
        self.assertIn("- the shell that ran `romp up`, which exported it: stop that `romp up`; start it from a shell without the line", out)
        # the manager restart is named by the commands that restart one; `romp-service install` appears once,
        # for what it does per platform, never as the restart
        self.assertIn("The manager restart is `systemctl --user restart romp-manager`, or on macOS `launchctl kickstart -k", out)
        self.assertIn("gui/$(id -u)/com.romp.manager`", out)
        self.assertEqual(out.count("romp-service install"), 1)
        self.assertNotIn("`romp refresh` restarts the kernels into file mode", out)
        self.assertIn("put the line back in service.env instead", out)
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("cycle       NOT DONE", out)

    def test_a_kernel_in_file_mode_under_a_file_that_carries_the_line_names_the_other_file_cause(self):
        # the file this shell reads carries ROMP_CREDENTIAL_COMMAND and the kernel is in file mode. The
        # first cause is a line added since the kernel started, and `romp refresh` is the whole fix; the
        # second is that the kernel reads ANOTHER service.env (its environment sets ROMP_SERVICE_ENV_FILE to
        # another path, through the installer's unit or plist line or any other source), which no kernel
        # restart mends, so the block names it with this shell's path and the places to look per platform.
        # Called at the block: the report's header would run the command
        self.write_env("ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=romp-test-fixture-cmd \"$1\"\n")
        cli.es._reset()
        said = []
        try:
            rc = cli._mode_mismatch({"keySource": "file", "keyFp": ""}, "command", said.append)
        finally:
            cli.es._reset()
        out = "\n".join(said)
        self.assertEqual(rc, 1)
        self.assertIn("kernel      reads (none) in FILE mode", out)
        self.assertIn("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in service.env", out)
        self.assertIn("there needs no manager restart). Until then the kernel injects no set.", out)
        self.assertIn("If the kernel is still in file mode after `romp refresh`, it reads another service.env: its environment", out)
        self.assertIn("sets ROMP_SERVICE_ENV_FILE (the installer's line in the unit or the plist, a drop-in, a profile, or the", out)
        self.assertIn("shell that ran `romp up`), and this shell reads %s." % self.path, out)
        self.assertIn("Run this command with the same ROMP_SERVICE_ENV_FILE, or look for the variable in the unit and its", out)
        self.assertIn("drop-ins on Linux, the plist on macOS.", out)
        self.assertNotIn("the installer carries", out)
        self.assertNotIn("systemctl", out, "adding the line is never a manager restart")
        self.assertNotIn("set in this shell's", out)

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


class HelpAndDocsAgree(unittest.TestCase):
    """`romp help`'s keyswap row, docs/reference.md's command table and the two READMEs spell the SAME
    invocation — one form, so an operator reading any of them types what the others describe."""

    FORM = "romp keyswap [<name>] [--refresh] [--cycle <session,…>|--cycle-all]"

    def _read(self, rel):
        return open(os.path.join(ROOT, rel), encoding="utf-8").read()

    def test_the_help_row_spells_the_whole_form(self):
        self.assertIn('_romp_cmd "%s" romp-keyswap' % self.FORM, self._read("bin/romp"))

    def test_the_reference_table_and_the_readmes_spell_the_same_form(self):
        escaped = self.FORM.replace("|", "\\|")                    # a table cell escapes the pipe
        for rel in ("docs/reference.md", "cli/README.md", "bin/README.md"):
            text = self._read(rel)
            if rel == "bin/README.md":
                continue                                           # its row names the binary, not the invocation
            self.assertIn("`%s`" % escaped, text, rel)
        self.assertIn("`romp keyswap <name>`", self._read("bin/README.md"))

    def test_every_restart_advice_about_a_unit_or_plist_line_names_the_reload(self):
        # a unit Environment= line or a plist EnvironmentVariables pair is part of the loaded service
        # definition, which a manager restart re-applies; advice that says "restart" about one and not
        # "reload" sends the reader to a restart that changes nothing. Two paragraphs of the reference did
        # (the `romp refresh --quiet` paragraph and the keyswap section's list of places named a bare
        # restart), so the property is pinned over every paragraph rather than the two that were fixed
        import re
        ref = self._read("docs/reference.md")
        hits = [p for p in re.split(r"\n\s*\n", ref) if re.search(r"Environment=|EnvironmentVariables", p) and "restart" in p]
        self.assertGreaterEqual(len(hits), 3, "the paragraphs this covers")
        for p in hits:
            self.assertIn("reload", p, p[:160])
        # the same for the CLI's three hints about such a line: the mode MISMATCH under a command-mode kernel,
        # the one under a shell whose environment alone carries the line, and the fingerprint MISMATCH's causes
        src = self._read("cli/keyswap.py")
        for phrase in ("the unit's Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources (Linux), or the",
                       "a line in the unit's own Environment= or the plist's EnvironmentVariables",
                       "a line changed or removed there, or one in the unit, at the"):
            self.assertIn(phrase, src, phrase)
        for phrase in ("first, reload the definition, then restart the manager.",
                       "reaches them at the manager restart that follows a reload of the definition",
                       "plist line reaches that restart only once the definition is reloaded: daemon-reload on Linux,"):
            self.assertIn(phrase, src, phrase)
        self.assertNotIn("reaches them at the next manager restart (`systemctl --user restart romp-manager`)", src)

    def test_the_docs_show_the_command_mode_report_with_placeholder_fingerprints(self):
        ref = self._read("docs/reference.md")
        for line in ("key source  command (ROMP_CREDENTIAL_COMMAND is set)", "candidates  hp <- selected, lp",
                     "selector    hp -> lp", "re-run --cycle tests once quiet; sessions already on this key read \"current\""):
            self.assertIn(line, ref)
        import re
        for fp in re.findall(r"sha256:([0-9a-f]{12})", ref):
            # a placeholder fingerprint repeats a short pattern (low entropy): never something that reads
            # as a real digest, so the scanner that guards this repo has nothing to flag
            self.assertLessEqual(len(set(fp)), 6, fp)
        self.assertIn("#installing-without-keys-on-disk", self._read("docs/install.md"))


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


class _CommandMode(_Backend):
    """The backend of _Backend (a keyless manager, the login or the apiKeyHelper bills) in COMMAND
    mode: a fake command printing a synthetic set with no ANTHROPIC_API_KEY, and a fake apiKeyHelper
    in a temp CLAUDE_CONFIG_DIR — the helper-billed installation the convergence exists for."""

    def setUp(self):
        self.lab = tempfile.mkdtemp()
        self._cmd_before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR",)}
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.lab, "selector")
        self.values = {"ANTHROPIC_LP_API_KEY": fixture_value("lp"), "A_TOKEN": fixture_value("role")}
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.print_set(self.values)
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.cmd + ' "$1"'
        self.helper_value = fixture_value("helper")
        self.helper(self.helper_value)
        es._reset()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for v, was in self._cmd_before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def print_set(self, values):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + "".join("echo '%s=%s'\n" % kv for kv in values.items()))
        os.chmod(self.cmd, 0o700)

    def helper(self, value):
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        h = os.path.join(self.lab, "helper.sh")
        with open(h, "w") as fh:
            fh.write("#!/bin/sh\necho '%s'\n" % value)
        os.chmod(h, 0o700)
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": h}, fh)

    def connect(self, s):
        """What a connect does for the stamps: _options on the live session object."""
        import sys
        import types
        fake = None
        if "claude_agent_sdk" not in sys.modules and not sb.sdk_importable():
            fake = types.ModuleType("claude_agent_sdk")
            fake.HookMatcher = lambda **kw: kw
            sys.modules["claude_agent_sdk"] = fake
        try:
            return self.be._options(s, dict)
        finally:
            if fake is not None:
                sys.modules.pop("claude_agent_sdk", None)


class HelperSessionsConverge(_CommandMode):
    def test_a_connect_stamps_the_helpers_fingerprint_when_nothing_is_injected(self):
        s = self._live("key")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "the set carries no key: nothing injected")
        self.assertEqual(kw["env"]["A_TOKEN"], self.values["A_TOKEN"], "the role variables ride the launch")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values))
        self.assertFalse(s._launched_keyed)

    def test_a_session_on_the_current_helper_output_is_current_not_reconnected(self):
        s = self._live("key")
        self.connect(s)
        self.assertEqual(s.effective_auth(), "login", "the kernel injects nothing: no key anywhere it reads")
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.assertEqual(self.be.cycle_key(SID), "current", "idempotent: a repeated --cycle-all leaves it alone")
        self.assertEqual(self.reconnects, [])

    def test_a_rotation_behind_the_helper_cycles_once_then_reads_current(self):
        s = self._live("key")
        self.connect(s)
        self.helper(fixture_value("rotated"))
        self.assertEqual(self.be.cycle_key(SID), "current", "cached: the kernel has not re-run the helper yet")
        self.be.refresh_key_source()                              # what --cycle does first
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.reconnects, [SID])
        self.assertEqual(self.defers, [False], "immediate-only, like every key cycle")
        line = [m for m in self.logged if m.startswith("keyswap (web)")]
        self.assertEqual(len(line), 1)
        self.assertIn("apiKeyHelper now prints sha256:", line[0])
        self.assertNotIn(self.helper_value, line[0])
        self.connect(s)                                           # the reconnect lands: new stamps
        self.assertEqual(self.be.cycle_key(SID), "current", "converged — the second run names nothing")
        self.assertEqual(self.reconnects, [SID])

    def test_a_rotation_of_a_role_variable_cycles_a_helper_session_too(self):
        s = self._live("key")
        self.connect(s)
        self.values["ANTHROPIC_LP_API_KEY"] = fixture_value("lp2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        line = [m for m in self.logged if m.startswith("keyswap (web)")][0]
        self.assertIn("role variables are now sha256:", line)
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")

    def test_a_login_billed_session_with_role_variables_cycles_on_their_rotation_only(self):
        s = self._live("login", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current", "the set it launched with is the current one")
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "current", "a helper rotation is not its business: its CLI reported the login")
        self.values["A_TOKEN"] = fixture_value("role2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")

    def test_a_login_billed_session_with_no_role_variables_is_left_alone(self):
        self.print_set({})                    # the command prints nothing usable → an empty set
        es._reset()
        os.environ["ROMP_CREDENTIAL_COMMAND"] = "true"
        self._live("login", auth="login")
        self.assertEqual(self.be.cycle_key(SID), "login", "nothing to re-present: a reconnect would cost a turn")
        self._live("")
        self.assertEqual(self.be.cycle_key(SID), "login", "no init yet, nothing injected: nothing in play")
        self.assertEqual(self.reconnects, [])

    def test_a_helper_the_kernel_cannot_fingerprint_reconnects_on_every_run_with_the_reason(self):
        os.remove(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"))
        es._reset()
        s = self._live("key")
        self.connect(s)
        self.assertEqual(s._launched_key_fp, "", "no helper the kernel can see")
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.be.cycle_key(SID), "cycling", "nothing to converge on: the old behaviour, by its rule")
        self.assertEqual(self.reconnects, [SID, SID])
        line = [m for m in self.logged if m.startswith("keyswap (web)")][0]
        self.assertIn("could not fingerprint", line)
        self.assertIn("no apiKeyHelper in", line)

    def test_in_flight_work_still_skips_a_helper_session(self):
        s = self._live("key")
        self.connect(s)
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        s._bg_tasks["t1"] = {"since": 1}
        self.assertEqual(self.be.cycle_key(SID), "working")
        s._bg_tasks.clear()
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(SID), "working")
        self.assertEqual(self.reconnects, [], "a reconnect would kill the work — the same rule as upstream's")

    def test_an_explicit_login_pick_whose_cli_still_reports_a_key_converges_on_the_helper(self):
        # the pick says login, the CLI says a key (the helper found one anyway): the kernel injects
        # nothing either way, and the helper's fingerprint is what its new process would change
        s = self._live("key", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")

    def test_a_login_pick_beside_a_set_that_carries_a_key_converges_on_the_helper_not_the_key(self):
        # the set has a key (other sessions inject it); THIS session picked login and its CLI still
        # reported a key — the helper's. Its compare is the helper's fingerprint, never the set's key
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        es._reset()
        s = self._live("key", auth="login")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "ANTHROPIC_API_KEY present")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")   # the set's key rotates: not this session's concern
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.helper(fixture_value("rotated"))                       # the helper rotates: it is
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.reconnects, [SID])

    def test_a_keyed_session_converges_on_the_sets_key(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        es._reset()
        s = self._live("key", auth="key")
        kw = self.connect(s)
        self.assertEqual(kw["env"]["ANTHROPIC_API_KEY"], k)
        self.assertEqual(s._launched_key_fp, es.fingerprint(k))
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertIn("the work key is now sha256:", [m for m in self.logged if m.startswith("keyswap (web)")][0])
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")

    def _sessions(self, *ns):
        return [sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n, "name": "s%d" % n, "cwd": "/tmp"})
                for n in ns]

    @staticmethod
    def _result(status):
        from types import SimpleNamespace
        return SimpleNamespace(is_error=status is not None, api_error_status=status, parent_tool_use_id=None)

    def test_a_refusal_on_a_session_still_on_the_pre_rotation_helper_output_runs_nothing(self):
        # the reproduction on the helper-billed box: a session stamped with the helper's output from
        # before a rotation behind the helper is refused on every turn, and a session on the current
        # output completes turns between. Before this every 401 was forwarded without the session's
        # stamp, so each refusal invalidated the current set (a command run AND a helper run at the
        # next connect, a log line) and each success re-armed the path (a second log line), for as
        # long as the old session was left uncycled.
        old, cur = self._sessions(1, 2)
        self.connect(old)
        self.assertEqual(old._launched_key_fp, es.fingerprint(self.helper_value))
        rotated = fixture_value("rotated")
        self.helper(rotated)
        self.be.refresh_key_source()                              # what --cycle does first
        self.connect(cur)
        self.assertEqual(cur._launched_key_fp, es.fingerprint(rotated))
        runs, hruns = es._runs, es.helper_runs()
        self.logged.clear()
        for n in range(5):
            old._ah_note_result(self._result(401))
            self.connect(self._sessions(10 + n)[0])               # a connect between: nothing to re-run
            cur._ah_note_result(self._result(None))
        self.assertEqual((es._runs, es.helper_runs()), (runs, hruns), "no command run and no helper run for the burst")
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [],
                         "neither the refusal line nor the re-arm line, turn after turn")
        cur._ah_note_result(self._result(401))                    # the current output refused: fires once
        self.connect(self._sessions(20)[0])
        self.assertEqual((es._runs, es.helper_runs()), (runs + 1, hruns + 1))
        self.assertEqual(len([m for m in self.logged if "reported an authentication failure" in m]), 1, self.logged)
        self.assertFalse(any(self.helper_value in m or rotated in m for m in self.logged), "no line carries a value")

    def test_a_refresh_between_a_connects_read_and_its_helper_fingerprint_leaves_no_stale_entry_current(self):
        # a connect takes the set, then asks for the helper's fingerprint with it; an invalidate that
        # lands between the two (a --refresh, a refusal on another session) must not leave the
        # fingerprint of the connect's pre-refresh overlay stored as the current one. The helper here
        # reads a role variable, so the overlay decides what it prints.
        h = fixture_value("helper")
        hp = os.path.join(self.lab, "helper.sh")
        with open(hp, "w") as fh:
            fh.write('#!/bin/sh\necho "%s-${A_TOKEN:-none}"\n' % h)
        os.chmod(hp, 0o700)
        with open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": hp}, fh)
        es.invalidate("the helper changed")
        role_a, role_b = self.values["A_TOKEN"], fixture_value("role-b")
        real_take = es.take

        def take_then_rotate(environ=None):
            out = real_take(environ)
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

    def test_the_helper_status_word_is_gone(self):
        src = open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read()
        self.assertNotIn('return "helper"', src, "the always-reconnect outcome was replaced by convergence")
        self.assertNotIn("helper = True", src)

    def test_the_file_mode_compare_is_upstreams(self):
        # FILE mode (the command unset): a non-keyed session reads "login" whatever its CLI reported;
        # a keyed one converges on the file key's fingerprint — upstream's arm, untouched
        os.environ.pop("ROMP_CREDENTIAL_COMMAND")
        es._reset()
        self._live("key")
        self.assertEqual(self.be.cycle_key(SID), "login")
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        s = self._live("key", auth="key")
        s._launched_key_fp = ks.fingerprint(NEW_KEY)          # launched on a previous key
        self.assertEqual(self.be.cycle_key(SID), "cycling")
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
