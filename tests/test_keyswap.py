#!/usr/bin/env python3
"""Hot-swapping the API key the sessions bill, with no kernel restart (the user 2026-09-04).

The manager's `ANTHROPIC_API_KEY` used to be claimed out of `os.environ` once at kernel start, so
changing which org key the sessions billed meant restarting `romp-manager` — cutting every open turn
and killing every subagent. Now:

  * `kernel/keysource.py` reads the `ANTHROPIC_API_KEY=` line of the manager's env file LIVE, and
    `sdk_backend.work_api_key` prefers it, falling back to the startup claim;
  * `_options` therefore injects the CURRENT key into every session it launches or revives;
  * `romp keyswap <name>` rewrites only that one line, atomically, from a sibling file;
  * `--cycle`/`--cycle-all` reconnect running sessions through `SdkBackend.cycle_key` so they
    re-present the new key with their conversations intact.

What these tests pin, in the order the feature is used:
  KeySourceParsing / AtomicRewrite — the file layer: last assignment wins, one layer of quotes is
    stripped (systemd does), every other line survives byte for byte, mode never widens past 0600.
  LiveSpawnEnv — the point of the whole thing: change the file, and the NEXT launch's env carries
    the new key with no restart and no re-construction of the backend.
  StartupFallback — a box whose key does not ride the file behaves exactly as before.
  CycleReconnects — the apply half for already-running sessions.
  NothingLeaksTheKey — no key value in any log line, any printed line, or any wire payload; the
    only rendered form anywhere is the sha256 head.

Synthetic keys only (`sk-ant-TEST-…`), synthetic sids, temp paths. No real key material, and the
module points the env-file path at its own temp dir so it can never read the machine's real one.
"""
import json
import os
import stat
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads (they resolve their state root at import time), and a service.env
# path that does not exist — so a bare non-pytest run of this file cannot read the real one either.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_keyswap", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
cli = SourceFileLoader("romp_keyswap_cli", os.path.join(BIN, "romp-keyswap")).load_module()
# ONE keysource module object for the whole test, taken off the backend: the kernel, the CLI and
# these tests must be patching and cache-resetting the same module, and a second SourceFileLoader
# call under a different name would quietly give a second copy of it (with its own _CACHE).
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"

OLD_KEY = "sk-ant-TEST-0000"
NEW_KEY = "sk-ant-TEST-1111"
BOOT_KEY = "sk-ant-TEST-BOOT"


class _EnvFile(unittest.TestCase):
    """A temp service.env with the shape the real one has: the key line between other settings."""

    OTHER_LINES = ["# romp service environment", "ROMP_PERF=1", "ROMP_EXPECTED_AUTH=key"]

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "service.env")
        self._before = {v: os.environ.get(v) for v in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV",
                                                       "ANTHROPIC_API_KEY")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.write_env(OLD_KEY)
        ks._CACHE = ((), "")          # the stat-identity cache is module-global

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        ks._CACHE = ((), "")

    def write_env(self, key, lines=None, mode=0o600, path=None):
        lines = list(self.OTHER_LINES if lines is None else lines)
        lines.insert(2, "%s=%s" % (ks.KEY_VAR, key))
        p = path or self.path
        with open(p, "w") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(p, mode)
        ks._CACHE = ((), "")          # a same-second rewrite in a test can reuse the stat identity
        return p

    def sibling(self, name, body):
        p = self.path + "." + name
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, 0o600)
        return p


class KeySourceParsing(_EnvFile):
    def test_it_reads_the_key_line_and_ignores_everything_else(self):
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_the_last_assignment_wins_like_systemd_and_export(self):
        with open(self.path, "a") as fh:
            fh.write("%s=%s\n" % (ks.KEY_VAR, NEW_KEY))
        ks._CACHE = ((), "")
        self.assertEqual(ks.read_key(self.path), NEW_KEY,
                         "a repeated EnvironmentFile assignment overrides — read what the service gets")

    def test_one_layer_of_quotes_is_stripped(self):
        for q in ('"', "'"):
            self.write_env("%s%s%s" % (q, NEW_KEY, q))
            self.assertEqual(ks.read_key(self.path), NEW_KEY,
                             "systemd strips it; without this the CLI is handed the quotes too")

    def test_comments_blank_lines_and_other_vars_are_not_the_key(self):
        with open(self.path, "w") as fh:
            fh.write("\n# %s=sk-ant-TEST-COMMENTED\n\nROMP_PERF=1\nOTHER_API_KEY=x\n" % ks.KEY_VAR)
        ks._CACHE = ((), "")
        self.assertEqual(ks.read_key(self.path), "")

    def test_every_failure_reads_as_no_key_never_an_exception(self):
        self.assertEqual(ks.read_key(os.path.join(self.d, "nope.env")), "")
        self.assertEqual(ks.read_key(self.d), "", "a directory is not a key file")

    def test_a_rewrite_invalidates_the_cache_by_the_files_own_identity(self):
        self.assertEqual(ks.read_key(self.path), OLD_KEY)
        ks.write_key(NEW_KEY, self.path)
        self.assertEqual(ks.read_key(self.path), NEW_KEY,
                         "the cache is keyed on (inode, mtime_ns, size) — a rename invalidates it")

    def test_the_path_comes_from_the_installers_own_variable(self):
        os.environ["ROMP_SERVICE_ENV_FILE"] = "/tmp/from-installer.env"
        os.environ["ROMP_SERVICE_ENV"] = "/tmp/from-alias.env"
        self.assertEqual(ks.service_env_path(), "/tmp/from-installer.env",
                         "ROMP_SERVICE_ENV_FILE is the name bin/romp-service already uses")
        os.environ.pop("ROMP_SERVICE_ENV_FILE")
        self.assertEqual(ks.service_env_path(), "/tmp/from-alias.env")
        os.environ.pop("ROMP_SERVICE_ENV")
        os.environ["XDG_CONFIG_HOME"] = "/tmp/cfg"
        try:
            self.assertEqual(ks.service_env_path(), "/tmp/cfg/romp/service.env")
        finally:
            os.environ.pop("XDG_CONFIG_HOME", None)

    def test_a_bare_name_means_the_sibling_file_and_a_path_is_taken_as_given(self):
        self.assertEqual(ks.sibling_path("lowprio", self.path), self.path + ".lowprio")
        self.assertEqual(ks.sibling_path("/etc/other.env", self.path), "/etc/other.env")


class AtomicRewrite(_EnvFile):
    def test_only_the_key_line_changes_and_it_keeps_its_position(self):
        before = open(self.path).read().splitlines()
        res = ks.write_key(NEW_KEY, self.path)
        after = open(self.path).read().splitlines()
        self.assertEqual(res["old"], OLD_KEY)
        self.assertEqual(len(before), len(after))
        for i, (b, a) in enumerate(zip(before, after)):
            if b.startswith(ks.KEY_VAR + "="):
                self.assertEqual(a, "%s=%s" % (ks.KEY_VAR, NEW_KEY))
            else:
                self.assertEqual(a, b, "line %d changed — every other setting must survive" % i)
        self.assertIn("ROMP_PERF=1", after)
        self.assertIn("ROMP_EXPECTED_AUTH=key", after)

    def test_the_mode_stays_600_and_a_loose_one_is_tightened(self):
        ks.write_key(NEW_KEY, self.path)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.write_env(OLD_KEY, mode=0o644)
        res = ks.write_key(NEW_KEY, self.path)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertTrue(res["tightened"], "a key must never be left group- or world-readable")

    def test_it_leaves_no_temp_file_behind(self):
        ks.write_key(NEW_KEY, self.path)
        self.assertEqual(sorted(os.listdir(self.d)), ["service.env"],
                         "temp file + rename: nothing else may be left in the directory")

    def test_a_duplicate_key_line_is_collapsed_so_the_file_cannot_disagree_with_itself(self):
        with open(self.path, "a") as fh:
            fh.write("%s=sk-ant-TEST-STALE\n" % ks.KEY_VAR)
        ks.write_key(NEW_KEY, self.path)
        body = open(self.path).read()
        self.assertEqual(body.count(ks.KEY_VAR + "="), 1)
        self.assertEqual(ks.read_key(self.path), NEW_KEY)

    def test_a_file_with_no_key_line_gets_one_appended(self):
        with open(self.path, "w") as fh:
            fh.write("ROMP_PERF=1\n")
        ks.write_key(NEW_KEY, self.path)
        self.assertEqual(open(self.path).read(), "ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, NEW_KEY))

    def test_a_missing_file_is_created_0600(self):
        p = os.path.join(self.d, "fresh.env")
        ks.write_key(NEW_KEY, p)
        self.assertEqual(ks.read_key(p), NEW_KEY)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)


class _Backend(_EnvFile):
    """A backend whose key source is the temp env file. The startup stash is module-global and
    once-per-process, so each test re-arms it explicitly and restores the world after."""

    BOOT = ""          # what the process environment carried at "startup"

    def setUp(self):
        super().setUp()
        self.state = tempfile.mkdtemp()
        self._stash = sb._WORK_KEY
        self._checked = sb._KEY_FILE_CHECKED
        sb._WORK_KEY = self.BOOT              # the startup claim, already made
        sb._KEY_FILE_CHECKED = True           # the one-shot agreement line is asserted on its own
        self._fetch = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None      # never a real HTTPS GET from a test
        sb._FAST_ORG_VERDICTS.clear()
        self.logged = []
        # NB `log=` is a keyword: the third positional is `notify`. A line reaches self.logged only
        # through the log wire, which is what the no-leak tests below read.
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                log=lambda m: self.logged.append(str(m)))
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
        sb._WORK_KEY = self._stash
        sb._KEY_FILE_CHECKED = self._checked
        sb._fetch_key_fast_org = self._fetch
        sb._FAST_ORG_VERDICTS.clear()
        super().tearDown()

    def _sess(self, n=1, **reg):
        return sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n,
                                       "name": "s%d" % n, "cwd": "/tmp", **reg})

    def _launch_env(self, n=1, **reg):
        return self.be._options(self._sess(n, auth="key", **reg), dict)["env"]


class LiveSpawnEnv(_Backend):
    """The whole point: a session launched (or revived) AFTER the file changed carries the new key,
    with no kernel restart and no re-construction of the backend."""

    def test_the_spawn_env_carries_the_key_the_file_holds_now(self):
        self.assertEqual(self._launch_env(1).get("ANTHROPIC_API_KEY"), OLD_KEY)
        self.write_env(NEW_KEY)                       # the swap, mid-life of one backend object
        self.assertEqual(self._launch_env(2).get("ANTHROPIC_API_KEY"), NEW_KEY,
                         "the key is read per launch — this is what removes the restart")
        self.assertEqual(self.be.work_key, NEW_KEY)

    def test_a_revive_reads_it_too_because_both_go_through_one_seam(self):
        # resume + connect build their options through _options, the same call the tests above make;
        # pin that there is no second place a key could be frozen.
        src = open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read()
        self.assertEqual(src.count("ANTHROPIC_API_KEY=work_key"), 1,
                         "one injection site only — a second would need its own live read")
        self.assertIn("work_key = self.work_key", src)

    def test_the_key_is_read_once_per_connect_so_a_launch_cannot_straddle_a_swap(self):
        reads = []
        orig = ks.read_key

        def counting(path=None):
            reads.append(path)
            return orig(path)

        ks.read_key = counting
        try:
            self.be._options(self._sess(3, auth="key"), dict)
        finally:
            ks.read_key = orig
        self.assertEqual(len(reads), 1, "two reads could return two different keys")

    def test_an_emptied_file_falls_to_login_rather_than_injecting_a_blank(self):
        self.write_env("", lines=["ROMP_PERF=1"])
        env = self._launch_env(4)
        self.assertNotIn("ANTHROPIC_API_KEY", env,
                         "an empty var reads as key-mode-without-a-key to the CLI — removal, never blanking")
        texts = [p["text"] for p in self.be.problems(10)]
        self.assertTrue(any("carries none" in t for t in texts),
                        "a key session with no key to inject is a logged problem, not a silent fall")

    def test_the_live_key_reaches_the_has_a_key_bool_and_the_auth_default(self):
        self.assertEqual(self.be.default_auth({}), "key")
        self.write_env("", lines=["ROMP_PERF=1"])
        self.assertEqual(self.be.default_auth({}), "login")
        self.assertFalse(self.be.work_key)

    def test_an_explicit_pin_still_stands_up_a_keyless_manager(self):
        self.be.work_key = ""
        self.assertEqual(self.be.work_key, "")
        self.assertEqual(self.be.default_auth({}), "login")


class StartupFallback(_Backend):
    """A box whose key does NOT ride the env file — an apiKeyHelper machine, a foreground `romp up`
    from a shell that exported one — must behave exactly as it did before the live source existed."""

    BOOT = BOOT_KEY

    def test_a_file_with_no_key_line_falls_back_to_the_startup_claim(self):
        self.write_env("", lines=["ROMP_PERF=1"])
        self.assertEqual(self.be.work_key, BOOT_KEY)
        self.assertEqual(self._launch_env(1).get("ANTHROPIC_API_KEY"), BOOT_KEY)

    def test_a_missing_file_falls_back_too(self):
        os.unlink(self.path)
        ks._CACHE = ((), "")
        self.assertEqual(self.be.work_key, BOOT_KEY)

    def test_the_file_wins_when_it_has_a_line(self):
        self.assertEqual(self.be.work_key, OLD_KEY,
                         "the file is the live source; the startup claim is only the fallback")

    def test_the_ambient_key_is_still_claimed_out_of_the_environment(self):
        sb._WORK_KEY = None
        os.environ["ANTHROPIC_API_KEY"] = BOOT_KEY
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ,
                         "an ambient key bills EVERY session — constructing a backend must still strip it")
        self.assertEqual(be.work_key, OLD_KEY, "and the FILE still decides what a launch bills")

    def test_a_disagreement_between_the_file_and_the_startup_env_is_said_once(self):
        sb._KEY_FILE_CHECKED = False
        sb._WORK_KEY = BOOT_KEY
        import io
        import sys
        buf, was = io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            sb.work_api_key()
            sb.work_api_key()
        finally:
            sys.stderr = was
        said = buf.getvalue()
        self.assertEqual(said.count("DIFFERENT key"), 1, "a configuration fact, said once")
        self.assertNotIn(OLD_KEY, said)
        self.assertNotIn(BOOT_KEY, said)
        self.assertIn(ks.fingerprint(OLD_KEY), said)


class CycleReconnects(_Backend):
    """The apply half for sessions already running: the key rides the launch environment, so a live
    CLI keeps the key it started with until a reconnect re-presents the current one."""

    def _live(self, sid, auth="key"):
        s = self._sess(7, auth=auth)
        s.sid = sid
        s.name = "live"
        self.reconnects = getattr(self, "reconnects", [])
        s.request_reconnect = lambda: self.reconnects.append(sid)
        self.be.sessions[sid] = s
        return s

    def test_a_live_key_billed_session_reconnects(self):
        sid = self.be.spawn("n", "/tmp")
        self._live(sid)
        self.assertEqual(self.be.cycle_key(sid), "cycling")
        self.assertEqual(self.reconnects, [sid],
                         "reconnect is what applies a connect-time option — and resume keeps the history")

    def test_a_login_billed_session_is_left_alone(self):
        sid = self.be.spawn("n", "/tmp", auth="login")
        self._live(sid, auth="login")
        self.assertEqual(self.be.cycle_key(sid), "login")
        self.assertEqual(getattr(self, "reconnects", []), [],
                         "the key is not injected there — a reconnect would cost a turn for nothing")

    def test_a_dormant_session_needs_nothing_and_an_unknown_one_says_so(self):
        sid = self.be.spawn("n", "/tmp")
        self.assertEqual(self.be.cycle_key(sid), "dormant",
                         "no live CLI — its next launch reads the new key anyway")
        self.assertEqual(self.be.cycle_key("11111111-2222-3333-4444-999999999999"), "unknown")

    def test_nothing_about_the_session_is_persisted_because_nothing_about_it_changed(self):
        sid = self.be.spawn("n", "/tmp")
        before = json.dumps(sb.read_reg(self.be.state_dir, sid), sort_keys=True)
        self._live(sid)
        self.be.cycle_key(sid)
        self.assertEqual(json.dumps(sb.read_reg(self.be.state_dir, sid), sort_keys=True), before,
                         "which key the BOX uses is not a per-session setting")


class KeyswapCli(_EnvFile):
    """`romp keyswap` — the operator surface. The kernel is stubbed: these tests must never dial a
    real one (a developer box runs a live romp on the same loopback ports)."""

    def setUp(self):
        super().setUp()
        self.out = []
        self.posted = []
        self._kernel_before, self._post_before = cli._kernel, cli._post
        cli._kernel = lambda: None            # default: no kernel, so nothing reaches the network
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {"ok": True, "keyFp": "abc123abc123",
                                                                      "rows": []}
        self.sibling("lowprio", "%s=%s\n" % (ks.KEY_VAR, NEW_KEY))

    def tearDown(self):
        cli._kernel, cli._post = self._kernel_before, self._post_before
        super().tearDown()

    def run_cli(self, *argv):
        self.out = []
        rc = cli.main(list(argv), out=self.out.append)
        return rc, "\n".join(self.out)

    def test_a_named_source_rewrites_the_line_and_reports_both_fingerprints(self):
        rc, said = self.run_cli("lowprio")
        self.assertEqual(rc, 0)
        self.assertEqual(ks.read_key(self.path), NEW_KEY)
        self.assertIn("sha256:" + ks.fingerprint(OLD_KEY), said)
        self.assertIn("sha256:" + ks.fingerprint(NEW_KEY), said)
        self.assertIn("no manager restart needed", said)

    def test_the_bare_command_reports_and_changes_nothing(self):
        rc, said = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertEqual(ks.read_key(self.path), OLD_KEY, "a swap is asked for by name")
        self.assertIn("sha256:" + ks.fingerprint(OLD_KEY), said)
        self.assertIn("lowprio", said, "the candidates it could swap to")

    def test_it_refuses_a_source_with_no_key_line_and_touches_nothing(self):
        self.sibling("empty", "ROMP_PERF=1\n")
        rc, _ = self.run_cli("empty")
        self.assertEqual(rc, 2)
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_it_refuses_a_missing_source_and_touches_nothing(self):
        rc, _ = self.run_cli("nosuch")
        self.assertEqual(rc, 2)
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_swapping_to_the_key_already_live_rewrites_nothing(self):
        self.sibling("same", "%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        mtime = os.stat(self.path).st_mtime_ns
        rc, said = self.run_cli("same")
        self.assertEqual(rc, 0)
        self.assertIn("already this key", said)
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime)

    def test_cycle_asks_the_kernel_for_exactly_the_named_sessions(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(NEW_KEY),
            "rows": [{"session": "web", "status": "cycling"}, {"session": "api", "status": "dormant"}]}
        rc, said = self.run_cli("lowprio", "--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual(self.posted[0][1], "/keycycle")
        self.assertEqual(self.posted[0][2], {"sessions": ["web", "api"]})
        self.assertIn("history kept", said)
        self.assertIn("sha256:" + ks.fingerprint(NEW_KEY), said,
                      "the kernel's own fingerprint is how the operator confirms it re-read the file")

    def test_cycle_all_asks_for_all_and_never_names_a_session_itself(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        rc, _ = self.run_cli("lowprio", "--cycle-all")
        self.assertEqual(self.posted[0][2], {"all": True})

    def test_the_swap_still_lands_when_no_kernel_is_reachable(self):
        rc, said = self.run_cli("lowprio", "--cycle-all")
        self.assertEqual(rc, 1, "the cycle failed and must exit non-zero")
        self.assertEqual(ks.read_key(self.path), NEW_KEY, "…but the file swap already happened")
        self.assertIn("no running kernel", said)

    def test_a_kernel_predating_the_patch_names_the_one_restart_this_needs(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 404"}
        rc, said = self.run_cli("lowprio", "--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("romp refresh", said)

    def test_junk_options_are_refused_rather_than_read_as_a_source_name(self):
        self.assertEqual(self.run_cli("--wat")[0], 2)
        self.assertEqual(self.run_cli("lowprio", "extra")[0], 2)
        self.assertEqual(self.run_cli("lowprio", "--cycle")[0], 2)
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_no_printed_line_ever_carries_a_key_value(self):
        import io
        import sys
        self.sibling("same", "%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        cli._kernel = lambda: "http://127.0.0.1:29855"
        for argv in ([], ["lowprio"], ["same"], ["nosuch"], ["lowprio", "--cycle-all"], ["--wat"]):
            buf, was = io.StringIO(), sys.stderr
            sys.stderr = buf
            said = []
            try:
                cli.main(list(argv), out=said.append)
            finally:
                sys.stderr = was
            whole = "\n".join(said) + buf.getvalue()
            for key in (OLD_KEY, NEW_KEY):
                self.assertNotIn(key, whole, "`romp keyswap %s` printed a key" % " ".join(argv))

    def test_the_cli_and_the_kernel_read_the_key_through_the_same_module(self):
        src = open(os.path.join(ROOT, "cli", "keyswap.py")).read()
        self.assertIn('"kernel" / "keysource.py"', src.replace("'", '"'),
                      "writer and reader must not carry two copies of the path or the parse rules")


class KeycycleRoute(unittest.TestCase):
    """POST /keycycle over the REAL kernel handler on loopback (the HeadlessRoutes pattern). The
    route takes NO key from the caller — not a value, not a path — so the door cannot be used to
    point a session at a key of the caller's choosing; all it does is make live sessions re-read
    the file, and all it returns is a fingerprint."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.km = SourceFileLoader("romp_kernel_keyswap", os.path.join(BIN, "romp-kernel")).load_module()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    class _Fake:
        """Just the surface the route uses."""

        def __init__(self, sessions):
            self.sessions = sessions
            self.asked = []

        def work_key_fp(self):
            return ks.fingerprint(NEW_KEY)

        def cycle_key(self, sid):
            self.asked.append(sid)
            return {"s-web": "cycling", "s-api": "login"}.get(sid, "dormant")

    def _post(self, body):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/keycycle" % self.port, method="POST",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "X-Romp-Token": self.km.TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    def _with(self, fake, body):
        from unittest import mock
        with mock.patch.object(self.km, "_sdk", lambda: fake), \
             mock.patch.object(self.km, "_sid_of", lambda w: "s-" + w), \
             mock.patch.object(self.km, "_name_of", lambda sid: str(sid)[2:]), \
             mock.patch.object(self.km, "_push_soon", lambda: None):
            return self._post(body)

    def test_it_cycles_exactly_the_named_sessions_and_reports_each(self):
        fake = self._Fake({})
        code, resp = self._with(fake, {"sessions": ["web", "api", "gone"]})
        self.assertEqual(code, 200)
        self.assertEqual(fake.asked, ["s-web", "s-api", "s-gone"])
        self.assertEqual(resp["rows"], [{"session": "web", "status": "cycling"},
                                        {"session": "api", "status": "login"},
                                        {"session": "gone", "status": "dormant"}])

    def test_all_covers_every_live_session_and_no_dormant_one(self):
        fake = self._Fake({"s-web": object(), "s-api": object()})
        code, resp = self._with(fake, {"all": True})
        self.assertEqual(sorted(fake.asked), ["s-api", "s-web"],
                         "dormant sessions need nothing — their next launch reads the file")

    def test_the_answer_carries_a_fingerprint_and_never_a_key(self):
        code, resp = self._with(self._Fake({}), {"sessions": ["web"]})
        self.assertEqual(resp["keyFp"], ks.fingerprint(NEW_KEY))
        self.assertNotIn(NEW_KEY, json.dumps(resp))

    def test_a_session_that_raises_is_reported_not_fatal(self):
        fake = self._Fake({})
        fake.cycle_key = lambda sid: (_ for _ in ()).throw(RuntimeError("boom"))
        code, resp = self._with(fake, {"sessions": ["web", "api"]})
        self.assertEqual(code, 200)
        self.assertEqual(len(resp["rows"]), 2, "one bad session must not abandon the rest")
        self.assertIn("boom", resp["rows"][0]["status"])

    def test_the_route_needs_the_serve_token(self):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/keycycle" % self.port, method="POST",
                                     data=b"{}", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                self.fail("an untokened caller reached the route (status %s)" % r.status)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)


class NothingLeaksTheKey(_Backend):
    """No key value in any log line, printed line, or wire payload. The fingerprint is the only
    rendered form — the same rule the browser side has always had for the key (2026-08-08)."""

    def test_no_log_line_from_a_keyed_launch_contains_the_key(self):
        self._launch_env(1)
        self.write_env(NEW_KEY)
        self._launch_env(2)
        for line in self.logged + [p["text"] for p in self.be.problems(50)]:
            self.assertNotIn(OLD_KEY, line)
            self.assertNotIn(NEW_KEY, line)

    def test_the_change_is_announced_by_fingerprint_and_only_when_it_changes(self):
        self._launch_env(1)
        first = [l for l in self.logged if "work key" in l]
        self.assertEqual(len(first), 1)
        self.assertIn(ks.fingerprint(OLD_KEY), first[0])
        self._launch_env(2)
        self.assertEqual(len([l for l in self.logged if "work key" in l]), 1,
                         "change-only — an ordinary connect must not log the key at all")
        self.write_env(NEW_KEY)
        self._launch_env(3)
        said = [l for l in self.logged if "work key" in l]
        self.assertEqual(len(said), 2)
        self.assertIn(ks.fingerprint(NEW_KEY), said[1])

    def test_a_cycle_log_line_carries_the_fingerprint_only(self):
        sid = self.be.spawn("n", "/tmp")
        s = self._sess(8, auth="key")
        s.sid, s.name = sid, "live"
        s.request_reconnect = lambda: None
        self.be.sessions[sid] = s
        self.be.cycle_key(sid)
        line = [l for l in self.logged if "keyswap" in l][0]
        self.assertNotIn(OLD_KEY, line)
        self.assertIn(ks.fingerprint(OLD_KEY), line)

    def test_a_fingerprint_is_twelve_hex_and_says_nothing_about_an_absent_key(self):
        fp = ks.fingerprint(OLD_KEY)
        self.assertEqual(len(fp), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in fp))
        self.assertNotIn(fp, OLD_KEY)
        self.assertEqual(ks.fingerprint(""), "")

    def test_the_key_never_lands_back_in_the_kernels_own_environment(self):
        self.be.work_key
        self._launch_env(1)
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ,
                         "the one-claimer property: an ambient key bills every session")

    def test_the_problem_ring_the_dashboard_reads_never_carries_a_key(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # a key pick with no key: the loudest path
        self._launch_env(1)
        self.write_env(NEW_KEY)
        self._launch_env(2)
        for p in self.be.problems(50):
            self.assertNotIn(NEW_KEY, p["text"])
            self.assertNotIn(OLD_KEY, p["text"])


if __name__ == "__main__":
    unittest.main()
