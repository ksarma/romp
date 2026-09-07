#!/usr/bin/env python3
"""Hot-swapping the API key the sessions bill, with no kernel restart (the user 2026-09-04).

The manager's `ANTHROPIC_API_KEY` used to be claimed out of `os.environ` once at kernel start, so
changing which org key the sessions billed meant restarting `romp-manager` — cutting every open turn
and killing every subagent. Now:

  * `kernel/keysource.py` reads the `ANTHROPIC_API_KEY=` line of the manager's env file LIVE, and
    `sdk_backend.work_api_key` prefers it, falling back to the startup claim;
  * `_options` therefore injects the CURRENT key into every session it launches or revives;
  * `romp keyswap <name>` — upstream's rewrite of that one line from a sibling file — is REFUSED on
    this fork (the user 2026-09-05: this fork does not write API keys to files; see tests/test_keyswap_refusal.py).
    The file layer below is upstream's module, carried unchanged and no longer called by the CLI;
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
  CommandSourceLaunch / CommandBeatsFileAndStartup / CommandSourceFailure / NothingLeaksInCommandMode
    — the COMMAND source (kernel/envsource.py, 2026-09-05): with ROMP_CREDENTIAL_COMMAND set the
    kernel runs the command and merges the set it prints into every launch (ANTHROPIC_API_KEY only
    where the session's auth says so), the mode wins over a file line and the startup claim, one run
    serves a burst of connects, a failed run keeps the previous set with one problem line per
    episode and never refuses a launch, a refusal is keyed on the session's launch stamp (a session
    still on the key from before a rotation re-runs nothing), and no value reaches a log line, the
    problem ring, the api-health payload or the /keycycle answer.

Synthetic keys only (`sk-ant-TEST-…`; the command-mode values are "romp-test-fixture-" + a uuid,
assembled at run time), synthetic sids, temp paths. No real key material, and the
module points the env-file path at its own temp dir so it can never read the machine's real one.
"""
import io
import json
import os
import stat
import sys
import tempfile
import unittest
import uuid
from romp_load import load_source

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

sb = load_source("romp_sdk_backend_keyswap", os.path.join(BIN, "romp_sdk_backend.py"))
cli = load_source("romp_keyswap_cli", os.path.join(BIN, "romp-keyswap"))
# ONE keysource module object for the whole test, taken off the backend: the kernel, the CLI and
# these tests must be patching and cache-resetting the same module, and a second SourceFileLoader
# call under a different name would quietly give a second copy of it (with its own _CACHE).
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"
es = sb._envsrc


def fixture_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


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

    def test_a_symlinked_env_file_is_written_through_and_stays_a_link(self):
        # a dotfiles-managed service.env is a symlink; os.replace onto the link's own name would swap the link
        # for a plain file and leave its target (what the repo tracks) on the old key (review find, reproduced)
        target_dir = tempfile.mkdtemp()
        target = os.path.join(target_dir, "service.env")
        with open(target, "w") as f:
            f.write("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.chmod(target, 0o600)
        link = os.path.join(self.d, "linked.env")
        os.symlink(target, link)
        res = ks.write_key(NEW_KEY, link)
        self.assertTrue(os.path.islink(link), "the link is still a link")
        self.assertEqual(os.path.realpath(link), os.path.realpath(target))
        self.assertEqual(ks.parse_key(open(target).read()), NEW_KEY, "the TARGET carries the new key")
        self.assertIn("ROMP_PERF=1", open(target).read())
        self.assertEqual(res["path"], link)
        self.assertEqual(os.path.realpath(res["target"]), os.path.realpath(target))
        self.assertEqual(ks.read_key(link), NEW_KEY)

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
        sb._WORK_KEY = self._stash
        sb._KEY_FILE_CHECKED = self._checked
        sb._fetch_key_fast_org = self._fetch
        sb._FAST_ORG_VERDICTS.clear()
        super().tearDown()

    def construct(self):
        # NB `log=` is a keyword: the third positional is `notify`. A line reaches self.logged only
        # through the log wire, which is what the no-leak tests below read.
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def _sess(self, n=1, **reg):
        return sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n,
                                       "name": "s%d" % n, "cwd": "/tmp", **reg})

    def _launch_env(self, n=1, **reg):
        return self.be._options(self._sess(n, auth="key", **reg), dict)["env"]

    def _env_for(self, n, auth, **reg):
        if auth:
            reg["auth"] = auth
        return self.be._options(self._sess(n, **reg), dict)["env"]


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
        self.assertTrue("work_key, key_src = self._work_key_and_source(cred)" in src,
                        "the one call site reads the key through _work_key_and_source, on the connect's own snapshot")

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

    def test_an_empty_key_line_falls_to_login_rather_than_injecting_a_blank(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # `ANTHROPIC_API_KEY=` with nothing after it
        env = self._launch_env(4)
        self.assertFalse("ANTHROPIC_API_KEY" in env, 
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
        with open(self.path, "w") as fh:                # genuinely no assignment, not an empty one
            fh.write("ROMP_PERF=1\n")
        ks._CACHE = ((), "")
        self.assertEqual(self.be.work_key, BOOT_KEY)
        self.assertEqual(self._launch_env(1).get("ANTHROPIC_API_KEY"), BOOT_KEY)

    def test_an_empty_key_line_falls_back_too(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # `ANTHROPIC_API_KEY=` with nothing after it
        self.assertEqual(self.be.work_key, BOOT_KEY)

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
        self.assertFalse("ANTHROPIC_API_KEY" in os.environ, 
                         "an ambient key bills EVERY session — constructing a backend must still strip it")
        self.assertEqual(be.work_key, OLD_KEY, "and the FILE still decides what a launch bills")

    def test_the_agreement_check_is_not_spent_on_a_read_with_nothing_to_compare(self):
        # the one-shot used to be consumed by the FIRST read even when the file had no key line, so a
        # disagreement that appeared later (the line added, quoted differently) was never reported
        import io
        from contextlib import redirect_stderr
        sb._KEY_FILE_CHECKED = False
        with open(self.path, "w") as f:
            f.write("ROMP_PERF=1\n")                                  # no key line yet
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(self.be.work_key, self.BOOT, "the startup claim governs")
        self.assertFalse(sb._KEY_FILE_CHECKED, "nothing to compare: the check is still armed")
        self.assertEqual(err.getvalue(), "")
        with open(self.path, "w") as f:
            f.write("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, NEW_KEY))    # a DIFFERENT key appears in the file
        with redirect_stderr(err):
            self.assertEqual(self.be.work_key, NEW_KEY)
            self.be.work_key                                          # a second read says nothing more
        self.assertTrue(sb._KEY_FILE_CHECKED)
        self.assertEqual(err.getvalue().count("DIFFERENT key"), 1, "said once, when there was something to say")
        self.assertNotIn(NEW_KEY, err.getvalue()); self.assertNotIn(self.BOOT, err.getvalue())

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
        self.defers = getattr(self, "defers", [])
        s.request_reconnect = lambda defer=True: (self.reconnects.append(sid), self.defers.append(defer))
        self.be.sessions[sid] = s
        return s

    def test_a_live_key_billed_session_reconnects(self):
        sid = self.be.spawn("n", "/tmp")
        self._live(sid)
        self.assertEqual(self.be.cycle_key(sid), "cycling")
        self.assertEqual(self.reconnects, [sid],
                         "reconnect is what applies a connect-time option — and resume keeps the history")
        self.assertEqual(self.defers, [False], "immediate-only: a key cycle never arms the end-of-turn reconnect")

    def test_the_defer_flag_rides_the_loop_callback(self):
        # the seam between the kernel-thread request and the loop-side re-check: request_reconnect(defer=False)
        # must schedule _do_request_reconnect WITH defer=False — a call_soon_threadsafe that dropped the argument
        # passed every other test and silently restored the end-of-turn reconnect for key cycles (fourth pass)
        s = self._sess(7, auth="key")
        scheduled = []

        class _Loop:
            def call_soon_threadsafe(self, cb, *args):
                scheduled.append((cb, args))
        s.loop = _Loop()
        s.request_reconnect(defer=False)
        s.request_reconnect()
        self.assertEqual([(cb.__name__, args) for cb, args in scheduled],
                         [("_do_request_reconnect", (False,)), ("_do_request_reconnect", (True,))])
        s.ended = True
        s.request_reconnect(defer=False)
        self.assertEqual(len(scheduled), 2, "an ended session schedules nothing")

    def test_the_loop_side_recheck_drops_a_key_cycle_that_found_the_session_busy(self):
        # the kernel-thread check and the loop callback are two moments; a turn fed in between used to take
        # _do_request_reconnect's else branch and arm the unconditional end-of-turn reconnect (third review pass)
        s = self._sess(7, auth="key")
        s._pending.append("a turn that arrived in between")
        s._do_request_reconnect(defer=False)
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle, "not deferred: dropped")
        self.assertTrue(any("before the reconnect ran" in m for m in self.logged))
        s._do_request_reconnect(defer=True)                             # the settings switches still defer
        self.assertTrue(s._reconnect_when_idle)
        s._reconnect_when_idle = False; s._pending.clear()
        s._subagents["agent-1"] = {"type": "local_agent", "since": 1.0}   # live work registered in between
        s._do_request_reconnect(defer=False)
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)

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

    def test_a_session_with_subagents_or_background_tasks_in_flight_is_skipped_not_cycled(self):
        # a reconnect abandons the CLI process and _drop_live_work retires every subagent and background task
        # inside it — the loss the keyswap exists to avoid, on a session that LOOKS idle (nothing of its own in
        # flight while it waits on a background agent). Named, never cycled under its work (review find).
        sid = self.be.spawn("n", "/tmp")
        s = self._live(sid)
        s._subagents["agent-1"] = {"type": "local_agent", "since": 1.0}
        self.assertEqual(self.be.cycle_key(sid), "working")
        self.assertEqual(self.reconnects, [], "no reconnect while a subagent runs")
        s._subagents.clear()
        s._bg_tasks["toolu_1"] = {"desc": "a long build", "type": "", "since": 2.0}
        self.assertEqual(self.be.cycle_key(sid), "working")
        self.assertEqual(self.reconnects, [], "…nor while a background task runs")
        s._bg_tasks.clear()
        self.assertEqual(self.be.cycle_key(sid), "cycling", "work all back → it cycles")
        self.assertEqual(self.reconnects, [sid])

    def test_a_busy_session_is_skipped_too_so_no_deferred_reconnect_can_kill_work_the_turn_starts_later(self):
        # the settings switches hand a busy session a deferred end-of-turn reconnect that fires unconditionally;
        # a background task the turn launches AFTER this check would die with it. "cycling" therefore means an
        # immediate reconnect of a quiet session, nothing else (second review pass).
        sid = self.be.spawn("n", "/tmp")
        s = self._live(sid)
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(sid), "working")
        s.inflight = 0
        s._pending.append("a queued turn")
        self.assertEqual(self.be.cycle_key(sid), "working")
        s._pending.clear()
        self.assertEqual(self.reconnects, [], "never armed while a turn was in flight or queued")
        self.assertEqual(self.be.cycle_key(sid), "cycling")
        self.assertEqual(self.reconnects, [sid])

    def test_a_session_whose_client_already_launched_on_the_live_key_is_current(self):
        # idempotence: a keyed session that already moved must not be reconnected again on every run, so
        # a repeated --cycle-all leaves it alone (a helper session is the exception: test_keyswap_refusal.py)
        sid = self.be.spawn("n", "/tmp")
        s = self._live(sid)
        s._launched_key_fp = self.be.work_key_fp()
        self.assertEqual(self.be.cycle_key(sid), "current")
        self.assertEqual(self.reconnects, [])
        s._launched_key_fp = "000000000000"                          # launched on some other key
        self.assertEqual(self.be.cycle_key(sid), "cycling")
        self.assertEqual(self.reconnects, [sid])

    def test_a_connect_records_the_fingerprint_of_the_key_it_launched_on(self):
        s = self._sess(9, auth="key")
        self.be._options(s, dict)
        self.assertEqual(s._launched_key_fp, ks.fingerprint(ks.read_key(self.path)))
        s2 = self._sess(8, auth="login")
        self.be._options(s2, dict)
        self.assertEqual(s2._launched_key_fp, "")

    def test_nothing_about_the_session_is_persisted_because_nothing_about_it_changed(self):
        sid = self.be.spawn("n", "/tmp")
        before = json.dumps(sb.read_reg(self.be.state_dir, sid), sort_keys=True)
        self._live(sid)
        self.be.cycle_key(sid)
        self.assertEqual(json.dumps(sb.read_reg(self.be.state_dir, sid), sort_keys=True), before,
                         "which key the BOX uses is not a per-session setting")


class KeyswapCli(_EnvFile):
    """`romp keyswap` — the operator surface. The kernel is stubbed: these tests must never dial a
    real one (a developer box runs a live romp on the same loopback ports).

    Fork shape (the user 2026-09-05): the named form is refused, so upstream's swap-then-cycle cases
    run the bare cycle against a file that stays on OLD_KEY — the fake kernel reports OLD_KEY's
    fingerprint where upstream's reported NEW_KEY's, and the swap assertions became "untouched"."""

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

    def test_a_named_source_is_refused_and_touches_nothing(self):
        # the fork's contract; the wording and the no-read/no-write guarantees are pinned in
        # tests/test_keyswap_refusal.py — this keeps upstream's fixture honest about the outcome
        import io
        import sys
        buf, was = io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            rc, said = self.run_cli("lowprio")
        finally:
            sys.stderr = was
        self.assertEqual(rc, 2)
        self.assertEqual(ks.read_key(self.path), OLD_KEY, "the file is untouched")
        self.assertIn("does not write API keys to files", buf.getvalue())
        self.assertEqual(said, "", "the refusal is the whole answer; nothing is reported on stdout")

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

    def test_even_the_key_already_live_is_refused_by_name(self):
        self.sibling("same", "%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        mtime = os.stat(self.path).st_mtime_ns
        rc, _ = self.run_cli("same")
        self.assertEqual(rc, 2, "the refusal does not depend on what the named file holds")
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime)

    def test_cycle_asks_the_kernel_for_exactly_the_named_sessions(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY),
            "rows": [{"session": "web", "status": "cycling"}, {"session": "api", "status": "dormant"}]}
        rc, said = self.run_cli("--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual(self.posted[0][1:], ("/keycycle", {"sessions": []}), "the read comes first")
        self.assertEqual(self.posted[-1][1], "/keycycle")
        self.assertEqual(self.posted[-1][2], {"sessions": ["web", "api"]})
        self.assertIn("history kept", said)
        self.assertIn("sha256:" + ks.fingerprint(OLD_KEY), said,
                      "the kernel's own fingerprint is how the operator confirms which key it holds")

    def test_cycle_all_asks_for_all_and_never_names_a_session_itself(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": []}
        rc, _ = self.run_cli("--cycle-all")
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": []}, {"all": True}],
                         "the read, then the cycle — and never a session named by the CLI itself")

    def test_a_login_row_in_file_mode_gets_one_hint_about_helper_billed_sessions(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY),
            "rows": [{"session": "web", "status": "login"}, {"session": "api", "status": "cycling"}]}
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("  web            skipped: bills the machine login, not the key", said)
        hint = [ln for ln in said.split("\n") if "billed through the apiKeyHelper" in ln]
        self.assertEqual(len(hint), 1, said)
        self.assertIn("cycle in command mode (set ROMP_CREDENTIAL_COMMAND)", said)
        self.assertIn("romp refresh --quiet", said)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY),
                                     "rows": [{"session": "api", "status": "cycling"}]}
        rc, said = self.run_cli("--cycle-all")
        self.assertNotIn("apiKeyHelper", said, "no login row, no hint")

    def test_the_file_mode_cycles_failure_lines_are_upstreams_byte_for_byte(self):
        # this is the surface upstream ships: what it prints when the cycle cannot run must not drift
        import unittest.mock as mock
        rc, said = self.run_cli("--cycle-all")                     # no kernel (setUp's default)
        self.assertEqual(rc, 1)
        self.assertEqual(said.split("\n")[-3:], [
            "cycle       NOT DONE — no running kernel found (is romp on? `romp status`).",
            "            Nothing was cycled. A session's next launch or revive runs a new process",
            "            anyway; re-run `romp keyswap --cycle…` once romp is up for the running ones."])
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 404"}
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertEqual(said.split("\n")[-3:], [
            "cycle       NOT DONE — the running kernel predates `romp keyswap` (no /keycycle route).",
            "            Take the patch once with `romp refresh` — that restart also gives every",
            "            session a new process — and every cycle after that is restart-free."])
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 503", "detail": "no SDK backend"}
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertEqual(said.split("\n")[-1], "cycle       FAILED — HTTP 503")
        cli._post = lambda u, p, b: {"ok": False}
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(said.split("\n")[-1], "cycle       FAILED — unknown")
        with mock.patch.dict(os.environ, {"ROMP_KERNEL_PORT": "not-a-port"}):
            rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertEqual(said.split("\n")[-1],
                         "cycle       NOT DONE — ROMP_KERNEL_PORT='not-a-port' is not a port; fix the variable and re-run")
        for line in said.split("\n"):
            self.assertFalse(line.startswith("kernel      NOT ASKED"), "the cycle speaks for itself, in upstream's words")

    def test_a_cycle_with_no_kernel_reachable_fails_loudly(self):
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1, "the cycle failed and must exit non-zero")
        self.assertEqual(ks.read_key(self.path), OLD_KEY, "nothing is ever written here")
        self.assertIn("no running kernel", said)

    def test_a_kernel_predating_the_patch_names_the_one_restart_this_needs(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 404"}
        rc, said = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("romp refresh", said)

    def test_the_kernels_fingerprint_is_compared_with_the_files_and_a_mismatch_is_loud(self):
        # the operator procedure used to be "compare the two sha256 lines by eye"; the CLI now asks the kernel
        # (a /keycycle read that names no session) and says MISMATCH when the kernel reads another key — the
        # symptom of a ROMP_SERVICE_ENV_FILE the kernel and this shell resolve differently, an unreadable file,
        # or a startup fallback (the wording is pinned in tests/test_keyswap_refusal.py)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {"ok": True, "keyFp": "deadbeefcafe", "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(self.posted[0][1:], ("/keycycle", {"sessions": []}), "a read: no session named")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", said)
        self.assertIn("sha256:deadbeefcafe", said)
        self.assertIn("reads another service.env:", said)
        # flattened: a path too long for its sentence is rendered on a line of its own (cli._other_file), and
        # a temp directory's length is the environment's, not this test's
        self.assertIn("this shell reads %s." % self.path, " ".join(said.split()), "the other-file cause names this shell's path")
        self.assertNotIn("installed with another env-file path", said, "one direction of the cause; the general form replaced it")
        self.posted.clear()
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(ks.read_key(self.path)), "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertNotIn("MISMATCH", said)
        self.assertIn("kernel      reads sha256:" + ks.fingerprint(ks.read_key(self.path)), said)

    def test_cycle_reads_and_compares_first_and_refuses_to_cycle_on_a_mismatch(self):
        # cycling while the kernel reads another file would re-present the kernel's unchanged key to every
        # named session; the read comes first and a mismatch stops the cycle before any reconnect
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {"ok": True, "keyFp": "deadbeefcafe",
                                                                      "rows": [{"session": "web", "status": "cycling"}]}
        rc, said = self.run_cli("--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", said)
        self.assertIn("NOT DONE", said)
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": []}], "the read only — nothing was cycled")
        self.posted.clear()
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY),
            "rows": [{"session": "web", "status": "working"}, {"session": "api", "status": "current"}]}
        rc, said = self.run_cli("--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": []}, {"sessions": ["web", "api"]}])
        self.assertIn("skipped: a turn, subagents or background tasks are in flight", said)
        self.assertIn("already on this key", said)
        self.assertIn("re-run --cycle web once quiet", said, "the hint names the skipped row only")

    def test_the_probe_itself_honours_the_override_and_refuses_an_unusable_one(self):
        # _kernel() must USE _kernel_urls(): a revert of that one line passed every test (second review pass)
        import io
        import unittest.mock as mock
        from contextlib import redirect_stderr
        cli._kernel = self._kernel_before                            # the real probe, with urlopen stubbed
        seen = []

        def refuse(url, timeout=None):
            seen.append(url)
            raise OSError("refused")
        with mock.patch.object(cli.urllib.request, "urlopen", refuse), \
             mock.patch.dict(os.environ, {"ROMP_KERNEL_PORT": "45678"}):
            self.assertIsNone(cli._kernel())
        self.assertEqual(seen, ["http://127.0.0.1:45678/version"], "the override port, and nothing else, was probed")
        seen.clear()
        with mock.patch.object(cli.urllib.request, "urlopen", refuse), \
             mock.patch.dict(os.environ, {"ROMP_KERNEL_PORT": "not-a-port"}):
            self.assertIsNone(cli._kernel())
            self.assertEqual(seen, [], "an unusable override probes nothing: the defaults are not a fallback")
            # …and every surface says so with a non-zero exit, instead of "kernel not running" and rc 0
            rc, said = self.run_cli()
            self.assertEqual(rc, 1); self.assertIn("NOT ASKED", said); self.assertIn("not a port", said)
            rc, said = self.run_cli("--cycle-all")
            self.assertEqual(rc, 1); self.assertIn("NOT DONE", said)
            self.assertEqual(ks.read_key(self.path), OLD_KEY, "nothing is ever written here")
        self.assertEqual(self.posted, [], "nothing was posted anywhere")

    def test_the_kernel_port_override_is_the_only_port_probed(self):
        # a renumbered second-OS-user instance must never hand its serve token to whatever answers on the
        # primary user's default port (review find): with the override set, that port and nothing else
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ROMP_KERNEL_PORT": "45678"}):
            self.assertEqual(cli._kernel_urls(), ["http://127.0.0.1:45678"])
        with mock.patch.dict(os.environ, {"ROMP_SERVE_PORT": "45679"}, clear=False):
            os.environ.pop("ROMP_KERNEL_PORT", None)
            self.assertEqual(cli._kernel_urls(), ["http://127.0.0.1:45679"])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ROMP_KERNEL_PORT", None); os.environ.pop("ROMP_SERVE_PORT", None)
            self.assertEqual(cli._kernel_urls(), cli.KPORTS)

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


class KeyswapCliCommandMode(unittest.TestCase):
    """`romp keyswap` in COMMAND mode (ROMP_CREDENTIAL_COMMAND set): the report, the named switch, the
    refresh and the cycle, against a fake command whose set depends on `$1` and a fake kernel that
    records what it was asked. The kernel is stubbed: these tests must never dial a real one.

    The fake command prints a different ANTHROPIC_API_KEY per selector name (hp, lp) plus a role
    variable; the values are assembled at run time. The fake kernel answers the way the route does —
    keySource, keyFp, setFp, selector, launched, refreshed — from whatever `self.kernel_view` holds, so
    a test moves the kernel's view to make the two sides agree or disagree."""

    def setUp(self):
        self.lab = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR", "ROMP_SERVICE_ENV_FILE",
                                                                         "ROMP_SERVICE_ENV")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(self.lab, "no-such-service.env")
        os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")     # no settings.json: no helper
        self.selector = os.path.join(self.lab, "selector")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = self.selector
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        self.keys = {"hp": fixture_value("hp"), "lp": fixture_value("lp")}
        self.role = fixture_value("role")
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.command_by_selector()
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.cmd + ' "$1"'
        self.select("hp")
        es._reset()
        self.posted = []
        self._saved = (cli._kernel, cli._post)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((p, b)) or self.kernel_answer(b)
        # the kernel's view: by default it agrees with this shell (its own run of the same command)
        self.kernel_view = {"keySource": "command", "keyFp": self.fp("hp"), "setFp": self.set_fp("hp"),
                            "selector": "hp", "keyErr": "", "launched": {self.fp("hp"): 3}, "rows": []}

    def tearDown(self):
        cli._kernel, cli._post = self._saved
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    # -- the lab --
    def command_by_selector(self, extra=""):
        body = "#!/bin/sh\n%s\ncase \"$1\" in\n" % extra
        for name, value in self.keys.items():
            body += "  %s) echo 'ANTHROPIC_API_KEY=%s' ;;\n" % (name, value)
        body += "esac\necho 'ROLE_TOKEN=%s'\n" % self.role
        with open(self.cmd, "w") as fh:
            fh.write(body)
        os.chmod(self.cmd, 0o700)

    def command(self, body):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + body + "\n")
        os.chmod(self.cmd, 0o700)

    def select(self, token):
        with open(self.selector, "w") as fh:
            fh.write(token + "\n")

    def selected(self):
        try:
            return open(self.selector).read().strip()
        except OSError:
            return None

    def fp(self, name):
        return es.fingerprint(self.keys[name])

    def set_fp(self, name):
        return es.set_fingerprint({"ANTHROPIC_API_KEY": self.keys[name], "ROLE_TOKEN": self.role})

    def kernel_answer(self, body):
        ans = {"ok": True}
        ans.update(self.kernel_view)
        ans["refreshed"] = ({"from": self.kernel_view.get("refreshFrom", ans["keyFp"]), "to": ans["keyFp"], "err": ""}
                            if body.get("refresh") else None)
        return ans

    def run_cli(self, *argv):
        said, buf, was = [], io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            rc = cli.main(list(argv), out=said.append)
        finally:
            sys.stderr = was
        return rc, "\n".join(said), buf.getvalue()

    def assertClean(self, *texts):
        blob = "\n".join(texts)
        for v in list(self.keys.values()) + [self.role]:
            self.assertNotIn(v, blob)
        self.assertNotIn("fixture", blob)

    # -- the bare report --
    def test_the_bare_report_names_the_source_selector_candidates_and_fingerprints(self):
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0, out)
        self.assertEqual(err, "")
        self.assertIn("key source  command (ROMP_CREDENTIAL_COMMAND is set)", out)
        self.assertIn("selector    hp             " + self.selector, out)
        self.assertIn("candidates  hp <- selected, lp", out)
        self.assertIn("set         sha256:%s — 2 names: ANTHROPIC_API_KEY, ROLE_TOKEN" % self.set_fp("hp"), out)
        self.assertIn("live key    sha256:%s   (this shell's run of the command: its ANTHROPIC_API_KEY line)" % self.fp("hp"), out)
        self.assertIn("kernel      reads sha256:%s (its own run); 3 live session(s) on it" % self.fp("hp"), out)
        self.assertNotIn("MISMATCH", out)
        self.assertIn("rotate:     romp keyswap <name>  writes the selector (one of: hp, lp)", out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": []})], "a read that names no session, no refresh")
        self.assertEqual(self.selected(), "hp", "a report writes nothing")
        self.assertClean(out, err)

    def test_the_report_counts_the_live_sessions_still_on_another_fingerprint(self):
        self.kernel_view["launched"] = {self.fp("hp"): 2, self.fp("lp"): 1, "": 1}
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("2 live session(s) on it", out)
        self.assertIn("            1 live session(s) still on sha256:" + self.fp("lp"), out)
        self.assertIn("            1 live session(s) launched with no credential the kernel fingerprinted", out)

    def test_mismatch_when_the_kernel_is_in_file_mode_and_the_line_is_in_this_shell_only(self):
        # the command is in this shell's environment (setUp) and service.env does not carry it: a
        # restarted kernel would not see it either, so the advice is to put it in the file first
        self.kernel_view.update({"keySource": "file", "keyFp": "", "launched": {"": 3}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      reads (none) in FILE mode", out)
        self.assertIn("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in this\n"
                      "            shell's environment only, not in service.env", out)
        self.assertIn("keeps the mode it started in", out)
        self.assertIn("Put the line in service.env, then\n            `romp refresh` restarts the kernels into command mode", out)
        # a drop-in is the other place that survives `romp-service install`; a line added to the unit or the
        # plist by hand does not (the install rewrites both), so the hint never sends the line there
        self.assertIn("A drop-in line reaches them at the manager restart after `systemctl --user\n"
                      "            daemon-reload` instead; not a line added to the unit or the plist by hand, which the\n"
                      "            next `romp-service install` rewrites away.", out)
        self.assertNotIn("a line in the unit's own Environment=", out)
        self.assertNotIn("set in service.env\n", out)

    def test_mismatch_when_the_kernel_is_in_file_mode_and_the_line_is_in_service_env_names_romp_refresh(self):
        # the line was ADDED to service.env after the kernel started: the kernel reads the file at
        # its start, so `romp refresh` is the whole fix; no manager restart is named
        with open(os.environ["ROMP_SERVICE_ENV_FILE"], "w") as fh:
            fh.write("ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=%s \"$1\"\n" % self.cmd)
        os.environ.pop("ROMP_CREDENTIAL_COMMAND")
        es._reset()
        self.kernel_view.update({"keySource": "file", "keyFp": "", "launched": {"": 3}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in\n"
                      "            service.env and was not when the kernel started.", out)
        self.assertIn("A running kernel keeps the mode it\n            started in: `romp refresh` restarts the kernels into command mode", out)
        self.assertIn("so a line added there needs no manager restart)", out)
        # the other-file block that follows, and the restart block after it, name the manager restart for
        # THEIR remedy (a changed ROMP_SERVICE_ENV_FILE in the unit); the advice for the line itself never does
        self.assertNotIn("systemctl", out.split("reads another service.env:")[0], "adding the line is a kernel restart, never a manager restart")
        self.assertIn("reads another service.env:", out)
        self.assertIn("The manager restart is `systemctl --user restart romp-manager` (Linux)", out)
        self.assertNotIn("set in this shell's", out)

    def test_mismatch_when_the_kernels_fingerprint_differs_names_the_two_environments(self):
        self.kernel_view.update({"keyFp": self.fp("lp"), "setFp": self.set_fp("lp"), "launched": {self.fp("lp"): 1}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH    the kernel's run of the command and this shell's disagree on the credential "
                      "fingerprint and the set's fingerprint.", out)
        self.assertIn("service environment", out)
        self.assertIn("a line added to service.env reaches the", out)
        self.assertIn("a line changed or removed there, or one in the", out)
        self.assertIn("next manager restart", out)
        self.assertIn("its next start, `romp refresh`;", out)
        self.assertIn("CLAUDE_CONFIG_DIR", out)
        # the kernel's last run used another selector: the hint is the refresh, not the environment
        self.kernel_view["selector"] = "lp"
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("The kernel's last run used selector lp, this shell's hp: `romp keyswap --refresh`", out)
        self.assertNotIn("CLAUDE_CONFIG_DIR", out)

    def test_no_kernel_is_not_a_failure_of_the_report(self):
        cli._kernel = lambda: None
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("kernel      not running — it runs the command itself when it is", out)
        self.assertEqual(self.posted, [])

    def test_a_helper_billed_set_fingerprints_the_helper(self):
        # no ANTHROPIC_API_KEY in the set: the apiKeyHelper bills, and THIS shell's run of it is the live key
        self.command("echo 'ROLE_TOKEN=%s'" % self.role)
        helper_value = fixture_value("helper")
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        h = os.path.join(self.lab, "helper.sh")
        with open(h, "w") as fh:
            fh.write("#!/bin/sh\necho '%s'\n" % helper_value)
        os.chmod(h, 0o700)
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": h}, fh)
        hfp = es.fingerprint(helper_value)
        self.kernel_view.update({"keyFp": hfp, "setFp": es.set_fingerprint({"ROLE_TOKEN": self.role}),
                                 "launched": {hfp: 2}})
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("live key    sha256:%s   (this shell's run of the apiKeyHelper; the set carries no ANTHROPIC_API_KEY)" % hfp, out)
        self.assertNotIn("MISMATCH", out)
        self.assertNotIn(helper_value, out + err)

    def test_no_key_and_no_helper_reads_as_the_login_billing_not_a_failure(self):
        self.command("echo 'ROLE_TOKEN=%s'" % self.role)
        set_fp = es.set_fingerprint({"ROLE_TOKEN": self.role})
        self.kernel_view.update({"keyFp": "", "keyKind": "login", "setFp": set_fp, "launched": {"": 2}, "keyErr": ""})
        rc, out, err = self.run_cli()
        self.assertIn("live key    (none) — the set carries no ANTHROPIC_API_KEY and no apiKeyHelper in", out)
        self.assertIn("sessions bill the machine login, and a", out)
        self.assertIn("cycle covers the role variables in the set", out)
        self.assertIn("kernel      reads no key (its own run): sessions bill the machine login; a cycle covers the role", out)
        self.assertIn("variables (set sha256:%s); 2 live session(s) launched with no key" % set_fp, out)
        self.assertNotIn("UNAVAILABLE", out)
        self.assertNotIn("MISMATCH", out)
        self.assertNotIn("launched with no credential the kernel fingerprinted", out, "the login rows are the expected rows")
        self.assertEqual(rc, 0, "a login-billed installation is a state, not a failure")
        self.assertClean(out, err)
        # …and the cycle proceeds on that footing
        self.kernel_view["rows"] = [{"session": "web", "status": "cycling", "from": ""}]
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.posted[-1], ("/keycycle", {"all": True}))

    def test_a_local_command_failure_is_loud_and_cycles_nothing(self):
        self.command("echo 'noise: %s' >&2\nexit 3" % self.keys["hp"])
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("live key    UNAVAILABLE — the credential command exited 3 after", out)
        self.assertIn("stderr", out)                        # a byte count, never the bytes
        self.assertClean(out, err)
        self.posted.clear()
        rc, out, err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("cycle       NOT DONE — this shell could not fingerprint the credential", out)
        self.assertEqual(self.posted, [], "nothing was asked of the kernel, nothing cycled")
        self.assertClean(out, err)

    # -- the named switch --
    def test_a_declared_name_writes_the_selector_re_runs_and_asks_the_kernel_to_refresh(self):
        self.kernel_view.update({"keyFp": self.fp("lp"), "setFp": self.set_fp("lp"), "selector": "lp",
                                 "launched": {self.fp("hp"): 3}, "refreshFrom": self.fp("hp")})
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(err, "")
        self.assertEqual(self.selected(), "lp")
        self.assertIn("selector    hp -> lp", out)
        self.assertIn("live key    sha256:%s   (was sha256:%s)" % (self.fp("lp"), self.fp("hp")), out)
        self.assertIn("set         sha256:%s   (was sha256:%s)" % (self.set_fp("lp"), self.set_fp("hp")), out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": [], "refresh": True})],
                         "the kernel is asked to re-run its command now, nothing is cycled")
        self.assertIn("kernel      reads sha256:%s (its own run, re-run now: was sha256:%s); 0 live session(s) on it"
                      % (self.fp("lp"), self.fp("hp")), out)
        self.assertIn("            3 live session(s) still on sha256:" + self.fp("hp"), out)
        self.assertNotIn("MISMATCH", out)
        self.assertClean(out, err)

    def test_an_undeclared_name_is_refused_before_anything_runs_and_never_echoed(self):
        for name in ("nosuch", "sk-ant-TEST-9999", "hp2"):
            rc, out, err = self.run_cli(name)
            self.assertEqual(rc, 2, name)
            self.assertEqual(out, "")
            self.assertIn("not declared in ROMP_CREDENTIAL_NAMES (declared: hp, lp)", err)
            self.assertIn("nothing switched", err)
            self.assertNotIn(name, err, "an undeclared name is never echoed")
        self.assertEqual(es._runs, 0, "the command never ran")
        self.assertEqual(self.posted, [])
        self.assertEqual(self.selected(), "hp")
        self.assertNotEqual(cli.REFUSAL, err, "not the file-mode refusal: this mode has a switch, and it was refused for its name")

    def test_a_name_that_is_not_a_token_is_refused_by_shape_and_never_echoed(self):
        rc, out, err = self.run_cli("bad name!")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("a selector is one name", err)
        self.assertIn("(9 characters given)", err)
        self.assertNotIn("bad name", err)
        self.assertEqual(es._runs, 0)
        self.assertEqual(self.selected(), "hp")

    def test_with_no_names_declared_the_switch_is_refused_and_the_selector_shown_by_length(self):
        os.environ.pop("ROMP_CREDENTIAL_NAMES")
        for name in ("lp", "sk-ant-TEST-9999"):
            rc, out, err = self.run_cli(name)
            self.assertEqual(rc, 2, name)
            self.assertEqual(out, "")
            self.assertIn("declare ROMP_CREDENTIAL_NAMES first", err)
            self.assertIn("nothing switched", err)
            self.assertNotIn(name, err, "the argument is never echoed")
        self.assertEqual(self.selected(), "hp", "nothing written")
        self.assertEqual(es._runs, 0)
        self.kernel_view.update({"selector": "(undeclared, 2 chars)"})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("candidates  none declared (ROMP_CREDENTIAL_NAMES is unset; `romp keyswap <name>` needs it", out)
        self.assertIn("selector    (undeclared, 2 chars) " , out)
        self.assertNotIn("selector    hp", out, "an undeclared token is rendered by length only")
        self.assertNotIn("MISMATCH", out, "both sides render the undeclared selector the same way")

    def test_a_switch_from_an_undeclared_selector_never_echoes_the_old_token(self):
        # the file held a token outside ROMP_CREDENTIAL_NAMES (a refused state: the kernel runs nothing
        # on it); switching to a declared name is a real move, and the old token is shown by length only
        pasted = fixture_value("pasted")
        self.select(pasted)
        self.kernel_view.update({"keyFp": self.fp("lp"), "setFp": self.set_fp("lp"), "selector": "lp",
                                 "launched": {}, "refreshFrom": ""})
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.selected(), "lp")
        self.assertIn("selector    (undeclared, %d chars) -> lp" % len(pasted), out)
        self.assertIn("live key    sha256:%s   (was (none))" % self.fp("lp"), out)
        self.assertNotIn(pasted, out + err)
        self.assertClean(out, err)
        # …and undone, when the command then fails for the new name, the old token goes back unnamed
        self.select(pasted)
        es._reset()
        self.command("echo '%s' >&2; exit 4" % self.keys["lp"])
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertIn("selector    (undeclared, %d chars) -> lp, put back to (undeclared, %d chars)" % (len(pasted), len(pasted)), out)
        self.assertEqual(self.selected(), pasted, "put back as it was")
        self.assertNotIn(pasted, out + err)
        self.assertClean(out, err)

    def test_the_kernel_ask_waits_in_step_with_the_credential_deadline(self):
        # the kernel may run its command (and the apiKeyHelper) before answering: the wait is
        # 10 s plus twice ROMP_CREDENTIAL_TIMEOUT_S, never a flat 30 s cutting a slow store off
        import unittest.mock as mock
        real_post = self._saved[1]                          # setUp stubs cli._post; this is the real one
        seen = []

        def fake_urlopen(req, timeout=None):
            seen.append(timeout)
            raise OSError("refused")
        with mock.patch.object(cli.urllib.request, "urlopen", fake_urlopen):
            real_post("http://127.0.0.1:1", "/keycycle", {})
            os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "45"
            real_post("http://127.0.0.1:1", "/keycycle", {})
        self.assertEqual(seen, [10 + 2 * es.DEFAULT_TIMEOUT_S, 10 + 2 * 45])

    def test_a_switch_that_moves_nothing_is_undone_and_exits_1(self):
        # the command ignores $1: both names print one set, so the switch would change what no launch sees
        self.command("echo 'ANTHROPIC_API_KEY=%s'\necho 'ROLE_TOKEN=%s'" % (self.keys["hp"], self.role))
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertEqual(self.selected(), "hp", "the selector is put back")
        self.assertIn("selector    hp -> lp, put back to hp", out)
        self.assertIn("live key    sha256:%s   (unchanged)" % self.fp("hp"), out)
        self.assertIn("nothing switched: the command printed the same set for lp as for hp", out)
        self.assertIn('`my-cmd "$1"`', out, "the $1 contract, since a bare command never sees the selector")
        self.assertEqual(self.posted, [], "the kernel is not asked to re-run for a switch that moved nothing")
        self.assertClean(out, err)

    def test_a_switch_whose_command_fails_for_the_new_name_is_undone(self):
        self.command("case \"$1\" in hp) echo 'ANTHROPIC_API_KEY=%s' ;; *) echo '%s' >&2; exit 4 ;; esac"
                     % (self.keys["hp"], self.keys["lp"]))
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertEqual(self.selected(), "hp")
        self.assertIn("selector    hp -> lp, put back to hp", out)
        self.assertIn("live key    UNAVAILABLE — the credential command exited 4 after", out)
        self.assertIn("nothing switched: the command failed for lp, so the selector is as it was.", out)
        self.assertEqual(self.posted, [])
        self.assertClean(out, err)

    def test_a_failed_undo_is_said_never_claimed(self):
        # the switch moved nothing and the selector could not be written back: the line says the
        # file now holds the new name, rather than "put back"
        self.command("echo 'ANTHROPIC_API_KEY=%s'\necho 'ROLE_TOKEN=%s'" % (self.keys["hp"], self.role))   # ignores $1
        real_write = es.write_selector
        calls = []

        def failing_second_write(token, path=None, environ=None):
            calls.append(token)
            if len(calls) == 2:
                raise OSError(13, "Permission denied")
            return real_write(token, path, environ)
        es.write_selector = failing_second_write
        try:
            rc, out, err = self.run_cli("lp")
        finally:
            es.write_selector = real_write
        self.assertEqual(rc, 1)
        self.assertEqual(calls, ["lp", "hp"], "the switch, then the attempted undo")
        self.assertIn("selector    hp -> lp, NOT put back (errno 13 writing the selector file), so it still holds lp", out)
        self.assertNotIn("put back to", out)
        self.assertEqual(self.selected(), "lp", "what the line says is what the file holds")
        self.assertClean(out, err)

    def test_an_unreadable_old_selector_is_not_claimed_put_back(self):
        # the file held something that is not a name before the switch: it cannot be restored, and
        # the line says so — never "put back to" something that was never read
        junk = fixture_value("junk") + " with spaces"
        self.select(junk)
        self.command("case \"$1\" in hp) echo 'ANTHROPIC_API_KEY=%s' ;; *) exit 4 ;; esac" % self.keys["hp"])
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertIn("selector    (none) -> lp, NOT put back — the old selector could not be read before the switch", out)
        self.assertIn("so the file now holds lp", out)
        self.assertNotIn("put back to", out)
        self.assertNotIn("so the selector is as it was", out)
        self.assertEqual(self.selected(), "lp")
        self.assertNotIn(junk, out + err)
        self.assertClean(out, err)

    def test_a_switch_from_no_selector_puts_an_empty_file_back_when_it_moves_nothing(self):
        os.unlink(self.selector)
        self.command("echo 'ANTHROPIC_API_KEY=%s'" % self.keys["hp"])            # ignores $1
        rc, out, _err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertIn("selector    (none) -> lp, put back to (none)", out)
        self.assertEqual(es.read_selector(self.selector), ("", ""), "no selector, as before")

    def test_the_name_already_selected_is_nothing_to_switch(self):
        rc, out, _err = self.run_cli("hp")
        self.assertEqual(rc, 0)
        self.assertIn("selector    hp (already selected)", out)
        self.assertIn("romp keyswap --refresh", out)
        self.assertIn("romp keyswap --cycle-all", out)
        self.assertEqual(es._runs, 0, "nothing to compare, so nothing runs")
        self.assertEqual(self.posted, [])

    def test_a_switch_with_no_kernel_says_the_next_start_reads_the_new_selector(self):
        cli._kernel = lambda: None
        rc, out, _err = self.run_cli("lp")
        self.assertEqual(rc, 0)
        self.assertEqual(self.selected(), "lp")
        self.assertIn("kernel      not running — its next start runs the command with the new selector", out)

    def test_a_switch_the_kernel_did_not_follow_is_a_mismatch(self):
        # the kernel re-ran but still reads the OLD credential: it resolves another selector file
        rc, out, _err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertEqual(self.selected(), "lp", "the local switch stands; the kernel side is what is wrong")
        self.assertIn("MISMATCH", out)
        self.assertIn("The kernel's last run used selector hp, this shell's lp", out)

    def test_a_switch_and_a_cycle_on_one_line_switch_then_cycle(self):
        self.kernel_view.update({"keyFp": self.fp("lp"), "setFp": self.set_fp("lp"), "selector": "lp",
                                 "rows": [{"session": "web", "status": "cycling", "from": self.fp("hp")}]})
        rc, out, _err = self.run_cli("lp", "--cycle-all")
        self.assertEqual(rc, 0, out)
        self.assertEqual([b for _p, b in self.posted],
                         [{"sessions": [], "refresh": True}, {"sessions": [], "refresh": True}, {"all": True}])
        self.assertIn("selector    hp -> lp", out)
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % self.fp("hp"), out)

    # -- refresh and cycle --
    def test_refresh_asks_the_kernel_to_re_run_and_prints_before_and_after(self):
        self.kernel_view["refreshFrom"] = self.fp("lp")
        rc, out, _err = self.run_cli("--refresh")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": [], "refresh": True})])
        self.assertIn("kernel      reads sha256:%s (its own run, re-run now: was sha256:%s); 3 live session(s) on it"
                      % (self.fp("hp"), self.fp("lp")), out)
        self.kernel_view.pop("refreshFrom")
        rc, out, _err = self.run_cli("--refresh")
        self.assertIn("(its own run, re-run now: unchanged)", out)

    def test_the_cycle_refreshes_first_then_reports_rows_with_their_launch_fingerprint(self):
        self.kernel_view["rows"] = [{"session": "web", "status": "cycling", "from": self.fp("lp")},
                                    {"session": "api", "status": "current", "from": self.fp("hp")},
                                    {"session": "tests", "status": "working", "from": self.fp("lp")}]
        rc, out, err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0, out)
        self.assertEqual([b for _p, b in self.posted], [{"sessions": [], "refresh": True}, {"all": True}],
                         "the refresh-and-read, then the cycle — never a session named by the CLI itself")
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % self.fp("lp"), out)
        self.assertIn("  api            already on this key — nothing to do", out)
        self.assertIn("  tests          skipped: a turn, subagents or background tasks are in flight", out)
        self.assertIn("            re-run --cycle tests once quiet; sessions already on this key read \"current\"", out)
        self.assertNotIn("helper", out.lower().replace("apikeyhelper", ""), "no helper row, no helper caveat")
        self.assertClean(out, err)

    def test_cycle_names_exactly_the_given_sessions(self):
        rc, _out, _err = self.run_cli("--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual(self.posted[-1], ("/keycycle", {"sessions": ["web", "api"]}))

    def test_the_cycle_stops_on_a_mismatch_before_any_reconnect(self):
        self.kernel_view.update({"keySource": "file", "keyFp": "", "launched": {}})
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", out)
        self.assertIn("cycle       NOT DONE", out)
        self.assertEqual([b for _p, b in self.posted], [{"sessions": [], "refresh": True}], "the read only")
        self.posted.clear()
        self.kernel_view.update({"keySource": "command", "keyFp": self.fp("lp"), "setFp": self.set_fp("lp")})
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", out)
        self.assertEqual(len(self.posted), 1)

    def test_a_kernel_run_that_failed_is_said_and_stops_the_cycle(self):
        self.kernel_view.update({"keyErr": "exited 3 after 0.2s, stderr 40 bytes"})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("the latest run failed — exited 3 after 0.2s, stderr 40 bytes — so it stands on the previous set", out)
        self.kernel_view.update({"keyFp": "", "launched": {}})
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("kernel      UNAVAILABLE — exited 3 after 0.2s, stderr 40 bytes", out)
        self.assertIn("cycle       NOT DONE", out)

    def test_no_value_reaches_stdout_or_stderr_whatever_the_arguments(self):
        loud = "\n".join("echo '%s' >&2" % v for v in list(self.keys.values()) + [self.role])
        self.command_by_selector(extra=loud)                 # every value also on stderr
        for argv in ([], ["lp"], ["hp"], ["nosuch"], ["--refresh"], ["--cycle-all"], ["--cycle", "web"],
                     ["lp", "--cycle-all"], ["--wat"], ["a", "b"]):
            self.select("hp")
            es._reset()
            rc, out, err = self.run_cli(*argv)
            self.assertClean(out, err)
            self.assertNotIn("sk-ant", out + err)
        self.command("echo 'noise' >&2\nexit 3")
        for argv in ([], ["lp"], ["--cycle-all"]):
            es._reset()
            rc, out, err = self.run_cli(*argv)
            self.assertClean(out, err)


class KeycycleRoute(unittest.TestCase):
    """POST /keycycle over the REAL kernel handler on loopback (the HeadlessRoutes pattern). The
    route takes NO key from the caller — not a value, not a path — so the door cannot be used to
    point a session at a key of the caller's choosing; all it does is make live sessions re-read
    the file, and all it returns is a fingerprint."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.km = load_source("romp_kernel_keyswap", os.path.join(BIN, "romp-kernel"))
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
        self.assertEqual(resp["rows"], [{"session": "web", "status": "cycling", "from": ""},
                                        {"session": "api", "status": "login", "from": ""},
                                        {"session": "gone", "status": "dormant", "from": ""}])
        self.assertEqual(resp["keySource"], "file", "a backend without the key-source surface reads as file mode")
        self.assertEqual(resp["keyErr"], "")
        self.assertEqual(resp["launched"], {})
        self.assertIsNone(resp["refreshed"])

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

    def test_an_empty_session_list_is_a_read_of_the_fingerprint_and_cycles_nothing(self):
        from unittest import mock
        fake = self._Fake({"s-web": object()})
        woke = []
        with mock.patch.object(self.km, "_sdk", lambda: fake), \
             mock.patch.object(self.km, "_sid_of", lambda w: "s-" + w), \
             mock.patch.object(self.km, "_name_of", lambda sid: str(sid)[2:]), \
             mock.patch.object(self.km, "_push_soon", lambda: woke.append(1)):
            code, body = self._post({"sessions": []})
            self.assertEqual(code, 200)
            self.assertEqual(body["keyFp"], ks.fingerprint(NEW_KEY))
            self.assertEqual(body["rows"], [])
            self.assertEqual(fake.asked, [], "nothing was cycled")
            self.assertEqual(woke, [], "a read does not wake the dashboard pusher")
            code, body = self._post({"sessions": ["web"]})
            self.assertEqual([r["status"] for r in body["rows"]], ["cycling"])
            self.assertEqual(woke, [1], "a cycle does")

    class _Live:
        def __init__(self, fp):
            self._launched_key_fp = fp

    class _Full(_Fake):
        """A backend with the key-source surface (SdkBackend has it; the _Fake above stands for one
        that does not, so the route's getattr fallbacks are exercised too)."""

        def __init__(self, sessions):
            super().__init__(sessions)
            self.calls = []

        def key_source_status(self):
            self.calls.append("status")
            return {"source": "command", "fp": ks.fingerprint(NEW_KEY), "fpKind": "key", "err": "",
                    "setFp": "0123456789ab", "selector": "hp",
                    "launched": {ks.fingerprint(NEW_KEY): 2, ks.fingerprint(OLD_KEY): 1, "": 1}}

        def refresh_key_source(self):
            self.calls.append("refresh")
            return {"from": ks.fingerprint(OLD_KEY), "to": ks.fingerprint(NEW_KEY), "err": ""}

        def cycle_key(self, sid):
            self.calls.append("cycle " + sid)
            return super().cycle_key(sid)

    def test_the_answer_carries_the_key_source_fields_and_each_rows_launch_fingerprint(self):
        fake = self._Full({"s-web": self._Live(ks.fingerprint(OLD_KEY)), "s-api": self._Live("")})
        code, resp = self._with(fake, {"sessions": ["web", "api", "gone"]})
        self.assertEqual(code, 200)
        self.assertEqual(resp["keySource"], "command")
        self.assertEqual(resp["keyErr"], "")
        self.assertEqual(resp["setFp"], "0123456789ab")
        self.assertEqual(resp["selector"], "hp")
        self.assertEqual(resp["launched"], {ks.fingerprint(NEW_KEY): 2, ks.fingerprint(OLD_KEY): 1, "": 1})
        self.assertEqual([r["from"] for r in resp["rows"]], [ks.fingerprint(OLD_KEY), "", ""],
                         "the fingerprint each live CLI launched on; a dormant one has none")
        self.assertIsNone(resp["refreshed"], "no refresh was asked for")
        self.assertNotIn("refresh", fake.calls)
        self.assertNotIn(NEW_KEY, json.dumps(resp))
        self.assertNotIn(OLD_KEY, json.dumps(resp))

    def test_refresh_re_runs_the_command_first_and_reports_what_moved(self):
        fake = self._Full({"s-web": self._Live(ks.fingerprint(OLD_KEY))})
        code, resp = self._with(fake, {"sessions": ["web"], "refresh": True})
        self.assertEqual(code, 200)
        self.assertEqual(resp["refreshed"], {"from": ks.fingerprint(OLD_KEY), "to": ks.fingerprint(NEW_KEY), "err": ""})
        self.assertEqual(fake.calls[0], "refresh", "the refresh precedes the fingerprint read and every cycle")
        self.assertIn("cycle s-web", fake.calls)
        self.assertLess(fake.calls.index("refresh"), fake.calls.index("cycle s-web"))
        code, resp = self._with(fake, {"sessions": [], "refresh": True})
        self.assertEqual(resp["rows"], [])
        self.assertEqual(resp["refreshed"]["to"], ks.fingerprint(NEW_KEY), "a bare --refresh: no rows, one re-run")

    def test_a_key_error_rides_the_answer(self):
        fake = self._Full({})
        fake.key_source_status = lambda: {"source": "command", "fp": "", "err": "exited 3 after 0.4s, stderr 87 bytes",
                                          "launched": {}}
        code, resp = self._with(fake, {"sessions": []})
        self.assertEqual(resp["keyErr"], "exited 3 after 0.4s, stderr 87 bytes")
        self.assertEqual(resp["keySource"], "command")

    def test_a_sessions_value_that_is_not_a_list_is_a_400(self):
        code, resp = self._with(self._Fake({}), {"sessions": "web"})
        self.assertEqual(code, 400, "a bare string would otherwise iterate its characters")
        self.assertFalse(resp.get("ok"))

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

    def test_the_announcement_names_the_startup_environment_when_the_file_has_no_line(self):
        sb._WORK_KEY = OLD_KEY                                        # the boot claim (restored by tearDown)
        with open(self.path, "w") as f:
            f.write("ROMP_PERF=1\n")                                  # no key line: the startup claim is injected
        self.assertEqual(self._launch_env()[ks.KEY_VAR], OLD_KEY)
        said = [m for m in self.logged if m.startswith("work key:")]
        self.assertEqual(len(said), 1)
        self.assertIn("sha256:" + ks.fingerprint(OLD_KEY), said[0])
        self.assertIn("environment this manager started with", said[0])
        self.assertNotIn("read from", said[0], "never claim the file holds a key it does not")
        self.assertNotIn(OLD_KEY, said[0])

    def test_a_cycle_log_line_carries_the_fingerprint_only(self):
        sid = self.be.spawn("n", "/tmp")
        s = self._sess(8, auth="key")
        s.sid, s.name = sid, "live"
        s.request_reconnect = lambda defer=True: None
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
        self.assertFalse("ANTHROPIC_API_KEY" in os.environ, 
                         "the one-claimer property: an ambient key bills every session")

    def test_the_problem_ring_the_dashboard_reads_never_carries_a_key(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # a key pick with no key: the loudest path
        self._launch_env(1)
        self.write_env(NEW_KEY)
        self._launch_env(2)
        for p in self.be.problems(50):
            self.assertNotIn(NEW_KEY, p["text"])
            self.assertNotIn(OLD_KEY, p["text"])



class _CommandMode(_Backend):
    """A backend in COMMAND mode: a fake command printing a synthetic set (no ANTHROPIC_API_KEY unless
    a test adds one), a temp CLAUDE_CONFIG_DIR with no apiKeyHelper, a selector file path in the lab,
    and an env file with NO key line — the shape the mode exists for. `self.boot_logged` keeps the
    lines of a FIRST construction made while the env file still carried OLD_KEY (the precedence case);
    the backend under test is the second construction, on the keyless file."""

    def setUp(self):
        self.lab = tempfile.mkdtemp()
        self._cmd_before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR",)}
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.lab, "selector")
        self.values = {"ANTHROPIC_LP_API_KEY": fixture_value("lp"), "A_TOKEN": fixture_value("role")}
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.print_set(self.values)
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.cmd + ' "$1"'
        es._reset()
        super().setUp()
        self.boot_logged = list(self.logged)
        self.write_env("", lines=["ROMP_PERF=1"])
        self.logged.clear()
        es._reset()
        self.be = self.construct()

    def tearDown(self):
        super().tearDown()
        for v, was in self._cmd_before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def print_set(self, values, extra=""):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + (extra + "\n" if extra else "")
                     + "".join("echo '%s=%s'\n" % kv for kv in values.items()))
        os.chmod(self.cmd, 0o700)

    def fail_command(self, body="exit 3"):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + body + "\n")
        os.chmod(self.cmd, 0o700)

    def problems(self):
        return [p["text"] for p in self.be.problems()]

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

    def helper_billed(self, n, moved):
        """A live session launched without the set's key whose CLI found one through the helper: the
        shape cycle_key converges on the helper's fingerprint. `moved` collects its reconnects."""
        s = self._sess(n, auth="login")
        self.be.spawn("s%d" % n, "/tmp", sid=s.sid)
        self.be._options(s, dict)
        s.auth_live = "key"
        s.request_reconnect = lambda defer=True: moved.append((s.name, defer))
        self.be.sessions[s.sid] = s
        return s


class CommandSourceLaunch(_CommandMode):
    def test_the_set_rides_every_launch_and_the_key_only_where_the_auth_says_so(self):
        env = self._env_for(1, "login")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"])
        self.assertEqual(env["ANTHROPIC_LP_API_KEY"], self.values["ANTHROPIC_LP_API_KEY"])
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertEqual(env["ROMP_SID"], "11111111-2222-3333-4444-000000000001", "romp's own entries ride over the set")
        # the set gains a key: an unpicked session is keyed (default_auth), a login pick is not
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.work_key, k)
        self.assertEqual(self.be.default_auth({}), "key")
        self.assertEqual(self._env_for(2, "").get("ANTHROPIC_API_KEY"), k)
        self.assertEqual(self._env_for(3, "key").get("ANTHROPIC_API_KEY"), k)
        env = self._env_for(4, "login")
        self.assertFalse("ANTHROPIC_API_KEY" in env, "removal, never blanking")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"], "…but the role variables still ride a login launch")

    def test_a_key_pick_with_no_key_in_the_set_launches_without_one_loudly(self):
        env = self._env_for(1, "key")
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"])
        self.assertTrue(any("credential command printed no ANTHROPIC_API_KEY" in t for t in self.problems()),
                        self.problems())

    def test_one_run_serves_a_burst_of_connects(self):
        self.assertEqual(es._runs, 1, "the boot verdict's first run")
        for n in range(1, 7):
            self._env_for(n, "login")
        self.assertEqual(es._runs, 1, "event-keyed: a burst of connects runs the command once")

    def test_a_connect_stamps_the_credential_and_the_role_variables(self):
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        self.assertEqual(s._launched_key_fp, "", "no key injected, no helper configured: nothing to fingerprint")
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values))
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.be.refresh_key_source()
        s2 = self._sess(2, auth="key")
        self.be._options(s2, dict)
        self.assertEqual(s2._launched_key_fp, es.fingerprint(k))
        role = dict(self.values)
        role.pop("ANTHROPIC_API_KEY")
        self.assertEqual(s2._launched_set_fp, es.set_fingerprint(role), "the key is not part of the role stamp")

    def test_the_selector_file_is_the_commands_dollar_one(self):
        with open(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], "w") as fh:
            fh.write("hp\n")
        self.print_set(self.values, extra='echo "PICKED=$1"')
        self.be.refresh_key_source()
        self.assertEqual(self._env_for(1, "login")["PICKED"], "hp")
        st = self.be.key_source_status()
        self.assertEqual(st["selector"], "(undeclared, 2 chars)", "no ROMP_CREDENTIAL_NAMES: the token is shown by length only")
        self.assertEqual(st["source"], "command")
        self.assertEqual(self.be.api_health_snapshot()["keySource"]["selector"], "(undeclared, 2 chars)")
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        self.be.refresh_key_source()
        self.assertEqual(self.be.key_source_status()["selector"], "hp", "declared: by name")
        self.assertEqual(self.be.api_health_snapshot()["keySource"]["selector"], "hp")

    def test_the_boot_line_names_the_set_by_fingerprint_and_names(self):
        boot = [m for m in self.logged if m.startswith("key source: command")]
        self.assertEqual(len(boot), 1, self.logged)
        self.assertIn("sha256:" + es.set_fingerprint(self.values), boot[0])
        self.assertIn("2 names: ANTHROPIC_LP_API_KEY, A_TOKEN", boot[0])
        self.assertIn("no ANTHROPIC_API_KEY in it", boot[0])
        self.assertEqual(self.be.key_source["mode"], "command")
        self.assertEqual(self.be.key_source["sessionKeyPath"], "login", "no key to inject, no helper configured")

    def test_status_and_refresh_report_fingerprints_and_what_moved(self):
        st = self.be.key_source_status()
        self.assertEqual(st["fp"], "", "no key in the set and no helper: no credential fingerprint")
        self.assertEqual(st["fpKind"], "login", "…the machine login bills, which is a state, not a failure")
        self.assertEqual(st["err"], "")
        self.assertEqual(st["setFp"], es.set_fingerprint(self.values))
        self.assertEqual(st["launched"], {})
        sid = self.be.spawn("n", "/tmp")
        s = self._sess(9, auth="login")
        s.sid = sid
        self.be._options(s, dict)
        self.be.sessions[sid] = s
        self.assertEqual(self.be.key_source_status()["launched"], {"": 1})
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        r = self.be.refresh_key_source()
        self.assertEqual(r, {"from": "", "to": es.fingerprint(k), "err": ""})
        self.assertEqual(self.be.work_key_fp(), es.fingerprint(k))
        self.assertTrue(any("refreshed — the credential fingerprint moved" in m for m in self.logged))
        r = self.be.refresh_key_source()
        self.assertEqual((r["from"], r["to"]), (es.fingerprint(k), es.fingerprint(k)))

    def test_dropped_romp_names_are_a_problem_line_by_name_once(self):
        self.print_set({"ROMP_SID": "forged", "A_TOKEN": self.values["A_TOKEN"]})
        self.be.refresh_key_source()
        lines = [t for t in self.problems() if "dropped 1 ROMP_* variable" in t]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("(ROMP_SID)", lines[0])
        self.assertNotIn("forged", lines[0])
        self.be.refresh_key_source()
        self.assertEqual(len([t for t in self.problems() if "dropped 1 ROMP_* variable" in t]), 1, "said once per list")
        self.assertNotIn("ROMP_SID", self._env_for(1, "login").get("A_TOKEN", ""))
        self.assertEqual(self._env_for(2, "login")["ROMP_SID"], "11111111-2222-3333-4444-000000000002",
                         "romp's identity entry, never the command's")


class CommandBeatsFileAndStartup(_CommandMode):
    """The mode wins: a key line in the env file and a startup ANTHROPIC_API_KEY are IGNORED, each
    said once by the boot verdict, naming the file or the variable — never a value."""

    BOOT = BOOT_KEY

    def test_a_file_line_and_the_startup_claim_are_ignored_and_named_once(self):
        # the FIRST construction ran with OLD_KEY in the env file and BOOT_KEY as the startup claim
        ignored = [m for m in self.boot_logged if "ignored" in m]
        self.assertEqual(len(ignored), 2, self.boot_logged)
        file_line = [m for m in ignored if "credential line" in m][0]
        self.assertIn(self.path, file_line)
        self.assertIn("ANTHROPIC_API_KEY", file_line)
        self.assertIn("the command wins", file_line)
        self.assertIn("rotate the value", file_line)
        env_line = [m for m in ignored if "manager's own environment" in m][0]
        self.assertIn("ANTHROPIC_API_KEY", env_line)
        for m in self.boot_logged:
            self.assertNotIn(OLD_KEY, m)
            self.assertNotIn(BOOT_KEY, m)
        # and the launch used neither: the set has no key, so nothing is injected
        self.assertEqual(self.be.work_key, "")
        self.assertEqual(self.be.default_auth({}), "login")
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(1, "key"), "ANTHROPIC_API_KEY present")
        self.write_env(OLD_KEY)                       # the file gains a line mid-life: still ignored
        self.assertEqual(self.be.work_key, "")
        self.assertFalse("ANTHROPIC_API_KEY" in self._env_for(2, ""), "ANTHROPIC_API_KEY present")

    def test_the_commands_key_wins_when_it_prints_one(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.write_env(OLD_KEY)
        self.be.refresh_key_source()
        self.assertEqual(self.be.work_key, k)
        self.assertEqual(self._env_for(1, "key")["ANTHROPIC_API_KEY"], k)
        self.assertEqual(self.be._work_key_and_source(), (k, "command"))
        self.assertEqual(sb.work_api_key(), k, "the module-level reader the judges are wired to agrees")
        self.assertTrue(any("the ANTHROPIC_API_KEY line the credential command printed" in m for m in self.logged),
                        self.logged)

    def test_the_startup_claim_is_still_popped_out_of_the_environment(self):
        sb._WORK_KEY = None
        os.environ["ANTHROPIC_API_KEY"] = BOOT_KEY
        self.assertEqual(sb.work_api_key(), "", "command mode: the ambient key is claimed and ignored")
        self.assertFalse("ANTHROPIC_API_KEY" in os.environ, "the one-claimer property holds in every mode")


class CommandModeSkipsTheFileWarning(_CommandMode):
    def test_a_key_line_under_a_declared_auth_is_said_once_by_the_verdict_alone(self):
        # file mode's _warn_credential_lines_in_env_file and the verdict would both speak about the
        # same line, and disagree (one says the key would be injected, the other that it is ignored)
        self._exp_before = os.environ.get("ROMP_EXPECTED_AUTH")
        self._said_before = sb._CREDENTIAL_LINE_SAID
        try:
            os.environ["ROMP_EXPECTED_AUTH"] = "key"
            sb._CREDENTIAL_LINE_SAID = False
            self.write_env(OLD_KEY)
            self.logged.clear()
            es._reset()
            self.be = self.construct()
            about_file = [t for t in self.problems() if "carries" in t and "ANTHROPIC_API_KEY" in t]
            self.assertEqual(len(about_file), 1, self.problems())
            self.assertTrue(about_file[0].startswith("key source: "), about_file[0])
            self.assertIn("the command wins", about_file[0])
            self.assertEqual([t for t in self.problems() if t.startswith("auth: ") and "carries" in t], [],
                             "file mode's warning stays quiet in command mode")
            self.assertFalse(sb._CREDENTIAL_LINE_SAID, "…and did not spend its one shot")
            # file mode, same file, same declaration: the file-mode warning speaks and the verdict does not
            os.environ.pop("ROMP_CREDENTIAL_COMMAND")
            es._reset()
            self.logged.clear()
            self.be = self.construct()
            self.assertEqual(len([t for t in self.problems() if t.startswith("auth: ") and "carries" in t]), 1)
            self.assertEqual([t for t in self.problems() if t.startswith("key source: ")], [])
        finally:
            sb._CREDENTIAL_LINE_SAID = self._said_before
            if self._exp_before is None:
                os.environ.pop("ROMP_EXPECTED_AUTH", None)
            else:
                os.environ["ROMP_EXPECTED_AUTH"] = self._exp_before


class CommandSourceFailure(_CommandMode):
    def test_a_failed_run_keeps_the_previous_set_with_one_problem_line_per_episode(self):
        self.assertEqual(self._env_for(1, "login")["A_TOKEN"], self.values["A_TOKEN"])
        w = fixture_value("wrong")
        self.fail_command("echo '%s' >&2\necho 'A_TOKEN=%s'\nexit 3" % (w, w))
        self.be.refresh_key_source()
        env = self._env_for(2, "login")
        self.assertEqual(env["A_TOKEN"], self.values["A_TOKEN"], "the previous set stands; a failing command's stdout is never trusted")
        lines = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("failed — exited 3.", lines[0])
        self.assertNotIn(" after ", lines[0], "the run's timing is not in the log line")
        self.assertNotIn("stderr", lines[0], "nor its stderr count: both differ per run of the same failure")
        self.assertIn("last successful run (sha256:%s)" % es.set_fingerprint(self.values), lines[0])
        self.assertNotIn(w, lines[0])
        last = self.be.api_health_snapshot()["keySource"]["lastRun"]
        self.assertEqual(last["ok"], False)
        self.assertTrue(last["reason"].startswith("exited 3 after "), last["reason"])
        self.assertIn("stderr %d bytes" % (len(w) + 1), last["reason"])
        self.assertNotIn(w, last["reason"])
        self.assertTrue(last["stale"], "api-health says the previous set stands in")
        self.assertGreaterEqual(last["failures"], 1)
        self.assertIsNotNone(last["lastOkAt"], "…and when the set last came from a good run")
        self.assertEqual(last["exitCode"], 3)
        # the same failure again, with another stderr length and its own duration: one line still
        self.fail_command("echo '%s%s' >&2\nsleep 0.15\nexit 3" % (w, w))
        self.be.refresh_key_source()
        self._env_for(3, "login")
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 1,
                         "the same kind of failure again is not new information, whatever its timing")
        last2 = self.be.api_health_snapshot()["keySource"]["lastRun"]
        self.assertNotEqual(last2["reason"], last["reason"], "the per-run detail still moves in api-health")
        self.assertIn("stderr %d bytes" % (2 * len(w) + 1), last2["reason"])
        self.fail_command("exit 4")
        self.be.refresh_key_source()
        self.assertEqual(len([t for t in self.problems() if t.startswith("credential command: failed")]), 2,
                         "another exit code is another kind")
        self.fail_command("sleep 30")
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "0.5"
        self.be.refresh_key_source()
        lines = [t for t in self.problems() if t.startswith("credential command: failed")]
        self.assertEqual(len(lines), 3, "a new kind of failure is a new line")
        self.assertIn("timed out after 0.5s", lines[2])
        st = self.be.key_source_status()
        self.assertIn("timed out", st["err"])
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertTrue(any(m.startswith("credential command: succeeded again") for m in self.logged))
        st = self.be.key_source_status()
        self.assertEqual(st["err"], "", "the run is fine again; no key and no helper is the login, not an error")
        self.assertEqual(st["fpKind"], "login")

    def test_a_first_failure_launches_with_nothing_injected_and_never_refuses(self):
        self.fail_command("exit 7")
        self.logged.clear()
        es._reset()
        self.be = self.construct()
        boot = [t for t in self.problems() if "credential command failed" in t]
        self.assertEqual(len(boot), 1, self.problems())
        self.assertIn("exited 7 after", boot[0])
        self.assertIn("nothing injected", boot[0])
        self.assertIn("romp keyswap --refresh", boot[0])
        env = self._env_for(1, "key")                          # a launch, not a refusal
        self.assertFalse("ANTHROPIC_API_KEY" in env, "ANTHROPIC_API_KEY present")
        self.assertFalse("A_TOKEN" in env, "A_TOKEN present")
        self.assertEqual(env["ROMP_SID"], "11111111-2222-3333-4444-000000000001")
        self.assertEqual(self.be.key_source["lastRun"]["ok"], False)
        self.assertEqual(self.be.key_source["lastRun"]["exitCode"], 7)
        self.assertTrue(any("printed no ANTHROPIC_API_KEY" in t for t in self.problems()),
                        "the key pick still says it launched without one")

    def test_an_authentication_failure_invalidates_the_cached_set(self):
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        runs = es._runs
        self.be._credential_auth_failed(s, "HTTP 401 on a turn")
        self.assertEqual(es._runs, runs, "invalidation runs nothing itself")
        self._env_for(2, "login")
        self.assertEqual(es._runs, runs + 1, "the next launch re-runs the command")
        self.assertTrue(any("reported an authentication failure (HTTP 401 on a turn)" in m for m in self.logged))

    def test_a_burst_of_refusals_is_one_command_run(self):
        # a revoked credential: every judge call and every launch reports a refusal, and the store
        # keeps handing back the same set — the first refusal re-runs the command, the rest do not
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        runs = es._runs
        for _ in range(4):
            self.be._credential_auth_failed(s, "HTTP 401 on a turn")
            self.assertTrue(sb.credential_invalidate("judge call refused as unauthenticated (planner)") is False
                            or es._runs == runs, "the judges' wire is the same once-per-credential path")
            self._env_for(2, "login")
        self.assertEqual(es._runs, runs + 1, "one run for the burst")
        said = [m for m in self.logged if "reported an authentication failure" in m]
        self.assertEqual(len(said), 1, "said when it fires, not per refusal")
        self.be.refresh_key_source()                          # the operator's refresh re-arms the path
        self.assertEqual(es._runs, runs + 2)
        self.be._credential_auth_failed(s, "HTTP 401 on a turn")
        self._env_for(3, "login")
        self.assertEqual(es._runs, runs + 3, "after a refresh the next refusal fires once more")

    def _result(self, status):
        from types import SimpleNamespace
        return SimpleNamespace(is_error=status is not None, api_error_status=status, parent_tool_use_id=None)

    def test_a_completed_turn_on_the_refused_credential_re_arms_the_refusal_path(self):
        # 401, run, same set, a completed turn on that credential, a later 401: the later refusal
        # re-runs the command. Keyed on the launch stamp: a completed turn on a session launched with
        # another credential, or with none (the login), re-arms nothing.
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.be.refresh_key_source()
        s = self._sess(1, auth="key")
        self.be._options(s, dict)
        self.assertEqual(s._launched_key_fp, es.fingerprint(k))
        runs = es._runs
        s._ah_note_result(self._result(401))
        self._env_for(2, "key")
        self.assertEqual(es._runs, runs + 1, "the first refusal re-runs")
        s._ah_note_result(self._result(401))
        self._env_for(3, "key")
        self.assertEqual(es._runs, runs + 1, "the same set again: suppressed")
        login = self._sess(4, auth="login")
        self.be._options(login, dict)
        self.assertEqual(login._launched_key_fp, "", "no key injected, no helper: nothing stamped")
        login._ah_note_result(self._result(None))
        s._ah_note_result(self._result(500))                  # an error result is not a success
        s._ah_note_result(self._result(401))
        self._env_for(5, "key")
        self.assertEqual(es._runs, runs + 1, "a login session's turn and an error result say nothing")
        old = self._sess(6, auth="key")
        self.be._options(old, dict)
        old._launched_key_fp = es.fingerprint(fixture_value("pre-rotation"))
        old._ah_note_result(self._result(None))
        s._ah_note_result(self._result(401))
        self._env_for(7, "key")
        self.assertEqual(es._runs, runs + 1, "a turn on a credential other than the refused one says nothing")
        self.assertFalse(any("completed a turn on the credential last refused" in m for m in self.logged))
        s._ah_note_result(self._result(None))                 # the refused credential completed a turn
        self.assertTrue(any("completed a turn on the credential last refused (sha256:%s)" % es.fingerprint(k) in m
                            for m in self.logged), self.logged)
        s._ah_note_result(self._result(401))
        self._env_for(8, "key")
        self.assertEqual(es._runs, runs + 2, "the later refusal is new information: the command runs again")
        # the judges' wire re-arms the same path: a served call ran on the set as a whole
        s._ah_note_result(self._result(401))
        self._env_for(9, "key")
        self.assertEqual(es._runs, runs + 2)
        self.assertTrue(sb.credential_auth_ok(""))
        s._ah_note_result(self._result(401))
        self._env_for(10, "key")
        self.assertEqual(es._runs, runs + 3)
        self.assertFalse(any(k in m for m in self.logged), "no line carries the key")

    def test_a_refusal_on_a_session_still_on_the_pre_rotation_key_runs_nothing(self):
        # the reproduction: a keyed session launched before a rotation is refused on every turn, and
        # a session on the current key completes turns between. Before this every 401 was forwarded
        # without the session's stamp, so each refusal invalidated the CURRENT set (a command run at
        # the next connect, a log line) and each current-key success re-armed the path (a second log
        # line), for as long as the old session was left uncycled.
        old_k, new_k = fixture_value("old-key"), fixture_value("new-key")
        self.values["ANTHROPIC_API_KEY"] = old_k
        self.print_set(self.values)
        self.be.refresh_key_source()
        old = self._sess(1, auth="key")
        self.be._options(old, dict)
        self.assertEqual(old._launched_key_fp, es.fingerprint(old_k))
        self.values["ANTHROPIC_API_KEY"] = new_k
        self.print_set(self.values)
        self.be.refresh_key_source()                          # the operator's refresh after the rotation
        cur = self._sess(2, auth="key")
        self.be._options(cur, dict)
        self.assertEqual(cur._launched_key_fp, es.fingerprint(new_k))
        runs = es._runs
        self.logged.clear()
        for n in range(5):
            old._ah_note_result(self._result(401))
            self._env_for(10 + n, "key")                      # a connect between: nothing to re-run
            cur._ah_note_result(self._result(None))
        self.assertEqual(es._runs, runs, "no run: the refused key is not the one the command would be run for")
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [],
                         "neither the refusal line nor the re-arm line, turn after turn")
        # a refusal on the CURRENT key still fires, once, and the next connect re-runs
        cur._ah_note_result(self._result(401))
        self._env_for(20, "key")
        self.assertEqual(es._runs, runs + 1)
        said = [m for m in self.logged if "reported an authentication failure" in m]
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("s2 reported", said[0])
        cur._ah_note_result(self._result(401))
        old._ah_note_result(self._result(401))
        self._env_for(21, "key")
        self.assertEqual(es._runs, runs + 1, "suppressed: the same set, and the stale stamp still says nothing")
        # a launch refused as unauthenticated carries the stamp of the set that connect took: it fires
        cur._ah_note_result(self._result(None))               # the current key completed a turn: re-armed
        fresh = self._sess(22, auth="key")
        self.be._options(fresh, dict)
        self.be._credential_auth_failed(fresh, "the CLI refused to start: not authenticated")
        self._env_for(23, "key")
        self.assertEqual(es._runs, runs + 2)
        self.assertFalse(any(old_k in m or new_k in m for m in self.logged), "no line carries a key")

    def test_a_connect_on_a_failing_command_runs_it_once_not_twice(self):
        # a non-keyed connect takes the set (one run: a failed run is re-run per caller) and stamps the
        # helper's fingerprint from the set it took, so the helper's own read is not a second run
        h = fixture_value("helper")
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        helper = os.path.join(self.lab, "helper.sh")
        with open(helper, "w") as fh:
            fh.write("#!/bin/sh\necho '%s'\n" % h)
        os.chmod(helper, 0o700)
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": helper}, fh)
        self.fail_command("exit 3")
        self.be.refresh_key_source()
        runs, hruns = es._runs, es.helper_runs()
        s = self._sess(1, auth="login")
        self.be._options(s, dict)
        self.assertEqual(es._runs, runs + 1, "one run per connect on a failing command, not two")
        self.assertEqual(es.helper_runs(), hruns, "the helper's fingerprint was cached from the refresh")
        self.assertEqual(s._launched_key_fp, es.fingerprint(h))
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values), "the previous set stands in")

    def test_a_connect_after_a_recovery_that_rotated_a_role_variable_stamps_the_new_sets_helper_output(self):
        # the store fails for one run and is back at the next with a rotated role variable: the retry
        # moves no generation. Before this the helper's fingerprint was cached on the generation alone,
        # so the connect on the new set was stamped with the old overlay's fingerprint, and cycle_key
        # read that session as current although its CLI bills through a helper fed the new variable.
        h = fixture_value("helper")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.be.refresh_key_source()
        old_role, moved = self.values["A_TOKEN"], []
        s1 = self.helper_billed(1, moved)
        self.assertEqual(s1._launched_key_fp, es.fingerprint("%s-%s" % (h, old_role)))
        self.assertEqual(self.be.cycle_key(s1.sid), "current")
        self.fail_command("exit 3")
        self.be.refresh_key_source()                          # the store is unreachable: the set stands, stale
        self.assertFalse(self.be.key_source_status()["err"] == "", "the failed run is said")
        gen = es._gen
        new_role = fixture_value("rotated-role")
        self.values["A_TOKEN"] = new_role
        self.print_set(self.values)                           # back, with a rotated role variable
        s2 = self.helper_billed(2, moved)                     # this connect's take() is the recovering run
        self.assertEqual(es._gen, gen, "the recovery moved no generation")
        self.assertEqual(s2._launched_key_fp, es.fingerprint("%s-%s" % (h, new_role)),
                         "stamped with the helper's output for the set it launched with, not the previous set's")
        self.assertEqual(s2._launched_set_fp, es.set_fingerprint(self.values))
        self.assertEqual(self.be.cycle_key(s2.sid), "current")
        self.assertEqual(self.be.cycle_key(s1.sid), "cycling", "the session on the previous set is not current")
        self.assertEqual(moved, [("s1", False)])
        why = [m for m in self.logged if m.startswith("keyswap (s1): reconnecting")]
        self.assertEqual(len(why), 1, self.logged)
        self.assertIn("the apiKeyHelper now prints sha256:%s" % s2._launched_key_fp, why[0])
        self.assertFalse(any(old_role in m or new_role in m or h in m for m in self.logged), "no line carries a value")

    def test_a_connect_whose_take_predates_a_refresh_does_not_hide_a_refusal_on_the_current_helper_output(self):
        # connect X takes the set; before it asks for the helper's fingerprint an operator's refresh
        # lands (the store now hands back a rotated role variable) and connect Y launches on the new
        # set, stamped with the helper's current output. X is stamped with the output for ITS set and
        # the cached entry stays Y's. Before this X's late run overwrote the entry with one for the
        # old generation, and a 401 on Y was then not a refusal of the helper's output as far as the
        # once-per-credential test could see, so it invalidated nothing and the next connect ran
        # nothing.
        import unittest.mock as mock
        h = fixture_value("helper")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.be.refresh_key_source()
        old_role, new_role = self.values["A_TOKEN"], fixture_value("rotated-role")
        real_take, staged = es.take, {}

        def racing_take(environ=None):
            snap, vals = real_take(environ)
            if not staged:                                    # X's take only: Y's own take below passes through
                staged["armed"] = True
                self.values["A_TOKEN"] = new_role
                self.print_set(self.values)
                self.be.refresh_key_source()                  # between X's take and its helper fingerprint
                y = self._sess(2, auth="login")
                self.be._options(y, dict)
                staged["y"] = y
            return snap, vals

        x = self._sess(1, auth="login")
        with mock.patch.object(es, "take", racing_take):
            self.be._options(x, dict)
        y = staged["y"]
        self.assertEqual(x._launched_key_fp, es.fingerprint("%s-%s" % (h, old_role)),
                         "X: the helper's output for the set it launched with")
        self.assertEqual(y._launched_key_fp, es.fingerprint("%s-%s" % (h, new_role)))
        self.assertEqual(es._helper["fp"], y._launched_key_fp, "the cached entry is the current one, not X's older run")
        runs = es._runs
        self.logged.clear()
        self.be._credential_auth_failed(y, "HTTP 401 on a turn")
        self._env_for(3, "login")
        self.assertEqual(es._runs, runs + 1, "a refusal on the current helper output fires: the next connect re-runs")
        self.assertTrue(any("s2 reported an authentication failure" in m for m in self.logged), self.logged)
        self.assertFalse(any(old_role in m or new_role in m or h in m for m in self.logged), "no line carries a value")

    def test_no_key_and_no_helper_is_the_login_not_an_error(self):
        # the set carries role variables only and no apiKeyHelper is configured: the machine login
        # bills, there is nothing to fingerprint, and that is a state, not a failure
        st = self.be.key_source_status()
        self.assertEqual((st["fp"], st["fpKind"], st["err"]), ("", "login", ""))
        self.assertEqual(self.be.credential_fingerprint(), ("", "login"))
        snap = self.be.api_health_snapshot()["keySource"]
        self.assertEqual((snap["fingerprint"], snap["fingerprintKind"], snap["sessionKeyPath"]), ("", "login", "login"))
        # cycle_key converges such a session on the role variables it launched with
        s = self._sess(1, auth="login")
        self.be.spawn("web", "/tmp", sid=s.sid)
        self.be._options(s, dict)
        s.auth_live = "login"
        moved = []
        s.request_reconnect = lambda defer=True: moved.append(defer)
        self.be.sessions[s.sid] = s
        self.assertEqual(self.be.cycle_key(s.sid), "current")
        self.values["A_TOKEN"] = fixture_value("rotated-role")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(s.sid), "cycling", "the role variables moved: that is what the cycle covers")
        self.assertEqual(moved, [False])
        why = [m for m in self.logged if m.startswith("keyswap (s1): reconnecting")]
        self.assertEqual(len(why), 1, self.logged)
        self.assertIn("role variables", why[0])
        self.assertNotIn("helper", why[0].lower(), "no helper is configured: nothing about one is said")

    def test_the_clis_auth_names_are_dropped_with_one_problem_line(self):
        v = fixture_value("auth")
        self.values["ANTHROPIC_AUTH_TOKEN"] = v
        self.values["ANTHROPIC_BASE_URL"] = "https://example.invalid"
        self.print_set(self.values)
        self.be.refresh_key_source()
        env = self._env_for(1, "login")
        self.assertFalse("ANTHROPIC_AUTH_TOKEN" in env, "ANTHROPIC_AUTH_TOKEN present")
        self.assertFalse("ANTHROPIC_BASE_URL" in env, "ANTHROPIC_BASE_URL present")
        self.assertTrue("A_TOKEN" in env, "A_TOKEN absent")
        lines = [t for t in self.problems() if "authentication or endpoint" in t]
        self.assertEqual(len(lines), 1, self.problems())
        self.assertIn("dropped ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL it printed", lines[0])
        self.assertNotIn(v, lines[0])
        self.be.refresh_key_source()
        self._env_for(2, "login")
        self.assertEqual(len([t for t in self.problems() if "authentication or endpoint" in t]), 1, "said once per distinct list")


class NothingLeaksInCommandMode(_CommandMode):
    def _blob(self):
        return "\n".join(self.logged) + json.dumps(self.problems()) + json.dumps(self.be.api_health_snapshot()) \
            + json.dumps(self.be.key_source_status()) + json.dumps(self.be.key_source) + json.dumps(self.be.refresh_key_source())

    def test_no_value_reaches_any_surface_whatever_the_command_does(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        loud = "\n".join("echo '%s' >&2" % v for v in self.values.values())
        self.print_set(self.values, extra=loud)                  # every value also on stderr
        self.be.refresh_key_source()
        for n, auth in ((1, "key"), (2, "login"), (3, "")):
            self._env_for(n, auth)
        self.fail_command(loud + "\n" + "\n".join("echo '%s'" % v for v in self.values.values()) + "\nexit 1")
        self.be.refresh_key_source()
        self._env_for(4, "key")
        blob = self._blob()
        for v in list(self.values.values()) + [OLD_KEY, BOOT_KEY]:
            self.assertNotIn(v, blob)
        self.assertNotIn("fixture", blob)
        for name, value in self.values.items():
            # the VALUES never land in the kernel's own environment (a developer's shell may carry a
            # variable of the same name; the message names nothing, so a failure cannot dump the environ)
            self.assertFalse(os.environ.get(name) == value, "a set value reached os.environ under " + name)

    def test_the_fingerprints_are_the_only_rendered_form(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        self.be.refresh_key_source()
        snap = self.be.api_health_snapshot()["keySource"]
        self.assertEqual(snap["fingerprint"], es.fingerprint(k))
        self.assertEqual(snap["fingerprintKind"], "key")
        self.assertEqual(snap["setFingerprint"], es.set_fingerprint(self.values))
        self.assertEqual(snap["names"], sorted(self.values))
        self.assertEqual(snap["sessionKeyPath"], "injected")
        self.assertEqual(snap["mode"], "command")
        self.assertEqual(snap["lastRun"]["ok"], True)
        self.assertEqual(snap["lastRun"]["exitCode"], 0)
        self.assertNotIn("lines", snap)
        for v in self.values.values():
            self.assertNotIn(v, json.dumps(snap))

if __name__ == "__main__":
    unittest.main()
