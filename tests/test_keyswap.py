#!/usr/bin/env python3
"""Hot-swapping the API key the sessions bill, with no kernel restart (the user 2026-09-04).

The manager's `ANTHROPIC_API_KEY` used to be claimed out of `os.environ` once at kernel start, so
changing which org key the sessions billed meant restarting `romp-manager` — cutting every open turn
and killing every subagent. Now:

  * `kernel/keysource.py` reads the configured API key source LIVE; a startup environment key
    remains supported only until a file or runtime source takes over;
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
  KeyswapCliCommandMode: `romp keyswap` under the COMMAND kind (kernel/envsource.py): the report runs
    the command in this shell and compares fingerprints with the kernel's run, `<name>` writes the
    one-token selector after checking it against ROMP_CREDENTIAL_NAMES and confirms the fingerprint
    moved (undone when nothing moved), --refresh makes the kernel re-run now, and a cycle re-runs first
    and reconnects only the sessions whose launch fingerprint differs; a MISMATCH names the cause when
    the kernel and this shell resolve different kinds, sources or fingerprints. The command-mode values
    are "romp-test-fixture-" + a uuid, assembled at run time; no value reaches stdout or stderr.

Synthetic keys only (`sk-ant-TEST-…`), synthetic sids, temp paths. No real key material, and the
module points the env-file path at its own temp dir so it can never read the machine's real one.
"""
import io
import json
import os
import shutil
import stat
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
# Hermetic state BEFORE the loads (they resolve their state root at import time), and a service.env
# path that does not exist — so a bare non-pytest run of this file cannot read the real one either.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ.pop("ROMP_SUPERVISED", None)  # a romp-managed shell inherits it; these tests stage the unsupervised startup-key case
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = SourceFileLoader("romp_sdk_backend_keyswap", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
cli = SourceFileLoader("romp_keyswap_cli", os.path.join(BIN, "romp-keyswap")).load_module()
# ONE keysource module object for the whole test, taken off the backend: the kernel, the CLI and
# these tests must be patching and cache-resetting the same module, and a second SourceFileLoader
# call under a different name would quietly give a second copy of it (with its own _CACHE).
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"
es = sb._envsrc
assert es is cli.es, "the CLI and the kernel must run the credential command through one module"


def fixture_value(tag=""):
    """A synthetic credential value, assembled at run time so no fixture literal is credential-shaped."""
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
                                                       "ANTHROPIC_API_KEY", "ROMP_API_KEY_REF",
                                                       "ROMP_CREDENTIAL_COMMAND")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ROMP_API_KEY_REF", None)
        os.environ.pop("ROMP_CREDENTIAL_COMMAND", None)
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

    def test_a_command_profile_replaces_the_key_line_in_place_and_a_key_replaces_it_back(self):
        # A profile may select a credential command (ROMP_CREDENTIAL_COMMAND=) the way it selects a
        # reference: the one source line is rewritten in place, every other line survives, and a later
        # swap to a key removes the command line (it would otherwise keep outranking the key).
        cmd = 'test-credential-helper "$1"'
        before = open(self.path).read().splitlines()
        res = ks.write_source(ks.KeySource("command", cmd), self.path)
        after = open(self.path).read().splitlines()
        self.assertEqual((res["old"].kind, res["old"].value), ("file", OLD_KEY))
        self.assertEqual(len(before), len(after))
        for b, a in zip(before, after):
            self.assertEqual(a, "%s=%s" % (ks.CMD_VAR, cmd) if b.startswith(ks.KEY_VAR + "=") else b)
        self.assertEqual(ks.read_source(self.path), ks.KeySource("command", cmd))
        self.assertEqual(ks.read_key(self.path), "", "a command is not a raw key")
        self.assertEqual(open(ks.marker_path(self.path)).read(), "command\n")
        ks.write_key(NEW_KEY, self.path)
        body = open(self.path).read()
        self.assertNotIn(ks.CMD_VAR, body, "a key selected over a command removes the command line")
        self.assertEqual(ks.read_key(self.path), NEW_KEY)
        self.assertFalse(os.path.exists(ks.marker_path(self.path)), "the marker follows the choice")


class _Backend(_EnvFile):
    """A backend whose key source is the temp env file. The startup stash is module-global and
    once-per-process, so each test re-arms it explicitly and restores the world after."""

    BOOT = ""          # what the process environment carried at "startup"

    def setUp(self):
        super().setUp()
        self.state = tempfile.mkdtemp()
        self._stash = sb._WORK_KEY
        self._checked = sb._KEY_FILE_CHECKED
        self._seen_fp = sb._FILE_KEY_SEEN_FP
        sb._WORK_KEY = self.BOOT              # the startup claim, already made
        sb._KEY_FILE_CHECKED = True           # the one-shot agreement line is asserted on its own
        sb._FILE_KEY_SEEN_FP = ""             # the key-line-gone notice is armed per test, asserted on its own
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
        sb._FILE_KEY_SEEN_FP = self._seen_fp
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
        self.assertIn("work_key, key_src = self._work_key_and_source(key_source)", src)

    def test_the_key_is_read_once_per_connect_so_a_launch_cannot_straddle_a_swap(self):
        reads = []
        orig = ks.read_source

        def counting(path=None):
            reads.append(path)
            return orig(path)

        ks.read_source = counting
        try:
            self.be._options(self._sess(3, auth="key"), dict)
        finally:
            ks.read_source = orig
        self.assertEqual(len(reads), 1, "two reads could return two different keys")

    def test_an_empty_key_line_refuses_an_explicit_key_launch(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # `ANTHROPIC_API_KEY=` with nothing after it
        with self.assertRaisesRegex(ks.KeySourceError, "no API key source"):
            self._launch_env(4)

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

    def test_removing_a_previously_selected_file_key_does_not_restore_the_startup_key(self):
        with open(self.path, "w") as fh:                # genuinely no assignment, not an empty one
            fh.write("ROMP_PERF=1\n")
        ks._CACHE = ((), "")
        self.assertEqual(self.be.work_key, "")
        with self.assertRaises(ks.KeySourceError):
            self._launch_env(1)

    def test_an_empty_key_line_does_not_restore_the_startup_key(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # `ANTHROPIC_API_KEY=` with nothing after it
        self.assertEqual(self.be.work_key, "")

    def test_a_removed_file_does_not_restore_the_startup_key(self):
        os.unlink(self.path)
        ks._CACHE = ((), "")
        self.assertEqual(self.be.work_key, "")

    def test_a_never_configured_file_permits_a_shell_environment_key(self):
        # A foreground installation that has never selected a file remains supported.
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path + ".never-created"
        sb._WORK_KEY = BOOT_KEY
        self.assertEqual(self.be.work_key, BOOT_KEY)
        self.assertEqual(self._launch_env(1).get("ANTHROPIC_API_KEY"), BOOT_KEY)

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

    def test_the_agreement_check_is_not_spent_on_a_read_with_nothing_to_compare(self):
        # the one-shot used to be consumed by the FIRST read even when the file had no key line, so a
        # disagreement that appeared later (the line added, quoted differently) was never reported
        import io
        from contextlib import redirect_stderr
        sb._KEY_FILE_CHECKED = False
        # This test starts before any file source has been selected.
        ks._AUTHORITATIVE_PATHS.pop(self.path, None)
        sb._WORK_KEY = self.BOOT
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


class KeyLineGone(_Backend):
    """Review find (2026-09-06): the file stays authoritative when its static key line is removed
    mid-run — correct — but nothing said so, and every session without an explicit Billing pick had
    silently started billing the login."""

    BOOT = ""

    def test_removing_the_static_key_line_mid_run_is_said_once_with_fingerprints_only(self):
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(self.be.work_key, OLD_KEY)
            self.assertEqual(err.getvalue(), "", "a configured file has nothing to say")
            with open(self.path, "w") as f:
                f.write("ROMP_PERF=1\n")                                 # the line is deleted
            ks._CACHE = ((), "")
            self.assertEqual(self.be.work_key, "", "the file stays authoritative: no startup key comes back")
            self.be.work_key; self.be.work_key                          # later reads say nothing more
        said = err.getvalue()
        self.assertEqual(said.count("is GONE"), 1, said)
        self.assertIn("sha256:" + ks.fingerprint(OLD_KEY), said)
        self.assertIn(self.path, said)
        self.assertIn("launch on the login", said)
        self.assertNotIn(OLD_KEY, said, "fingerprints only")
        # the line coming back re-arms the notice: a second removal is a second event
        self.write_env(NEW_KEY)
        with redirect_stderr(err):
            self.assertEqual(self.be.work_key, NEW_KEY)
            with open(self.path, "w") as f:
                f.write("ROMP_PERF=1\n")
            ks._CACHE = ((), "")
            self.assertEqual(self.be.work_key, "")
        self.assertEqual(err.getvalue().count("is GONE"), 2)
        self.assertIn("sha256:" + ks.fingerprint(NEW_KEY), err.getvalue())

    def test_a_file_that_never_had_a_line_says_nothing(self):
        import io
        from contextlib import redirect_stderr
        with open(self.path, "w") as f:
            f.write("ROMP_PERF=1\n")
        ks._CACHE = ((), "")
        sb._FILE_KEY_SEEN_FP = ""            # setUp's backend construction saw the fixture's line; this process did not
        err = io.StringIO()
        with redirect_stderr(err):
            self.be.work_key
        self.assertEqual(err.getvalue(), "")


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
        # idempotence: the operator re-runs --cycle-all until every session reads "current"; a session that
        # already moved must not be reconnected again on every run
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
    real one (a developer box runs a live romp on the same loopback ports)."""

    def setUp(self):
        super().setUp()
        from unittest import mock
        # Listing and selecting sources never resolve credentials, even when a provider profile
        # is present. Only the stubbed kernel may do so; no test can invoke a real op session.
        resolver = mock.patch.object(ks.KeySource, "resolve", side_effect=AssertionError("CLI resolved a secret"))
        resolver.start()
        self.addCleanup(resolver.stop)
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

    def test_the_durable_op_marker_is_not_listed_as_a_candidate(self):
        ks.remember_file_source(self.path, "op")
        self.assertTrue(os.path.exists(ks.marker_path(self.path)))
        rc, said = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("lowprio", said)
        self.assertNotIn(ks.SOURCE_MARKER + " ", said.replace("key source", ""), "the memory file is not a profile")
        self.assertNotIn("(no key source)", said)

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
        self.assertEqual(self.posted[0][1:], ("/keycycle", {"sessions": []}), "the read comes first")
        self.assertEqual(self.posted[-1][1], "/keycycle")
        self.assertEqual(self.posted[-1][2], {"sessions": ["web", "api"],
                                             "expectedSourceFp": ks.fingerprint(NEW_KEY)})
        self.assertIn("history kept", said)
        self.assertIn("sha256:" + ks.fingerprint(NEW_KEY), said,
                      "the kernel's own fingerprint is how the operator confirms it re-read the file")

    def test_cycle_all_asks_for_all_and_never_names_a_session_itself(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(NEW_KEY), "rows": []}
        rc, _ = self.run_cli("lowprio", "--cycle-all")
        self.assertEqual([b for _u, _p, b in self.posted],
                         [{"sessions": []}, {"all": True, "expectedSourceFp": ks.fingerprint(NEW_KEY)}],
                         "the read, then the cycle — and never a session named by the CLI itself")

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

    def test_the_kernels_fingerprint_is_compared_with_the_files_and_a_mismatch_is_loud(self):
        # the operator procedure used to be "compare the two sha256 lines by eye"; the CLI now asks the kernel
        # (a /keycycle read that names no session) and says MISMATCH when the kernel reads another key — the
        # symptom of a path the kernel's environment does not carry, an unreadable file, or a startup fallback
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {"ok": True, "keyFp": "deadbeefcafe", "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(self.posted[0][1:], ("/keycycle", {"sessions": []}), "a read: no session named")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", said)
        self.assertIn("sha256:deadbeefcafe", said)
        self.posted.clear()
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(ks.read_key(self.path)), "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertNotIn("MISMATCH", said)
        self.assertIn("kernel      reads sha256:" + ks.fingerprint(ks.read_key(self.path)), said)
        # after a swap the same check runs against the NEW key
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(NEW_KEY), "rows": []}
        rc, said = self.run_cli("lowprio")
        self.assertEqual(rc, 0); self.assertNotIn("MISMATCH", said)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": []}
        rc, said = self.run_cli("lowprio")                             # already swapped; the kernel still on the old
        self.assertEqual(rc, 1); self.assertIn("MISMATCH", said)

    def test_cycle_reads_and_compares_first_and_refuses_to_cycle_on_a_mismatch(self):
        # cycling while the kernel reads another file would re-present the kernel's unchanged key to every
        # named session; the read comes first and a mismatch stops the cycle before any reconnect
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {"ok": True, "keyFp": "deadbeefcafe",
                                                                      "rows": [{"session": "web", "status": "cycling"}]}
        rc, said = self.run_cli("lowprio", "--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", said)
        self.assertIn("NOT DONE", said)
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": []}], "the read only — nothing was cycled")
        self.posted.clear()
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(NEW_KEY),
            "rows": [{"session": "web", "status": "working"}, {"session": "api", "status": "current"}]}
        rc, said = self.run_cli("lowprio", "--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual([b for _u, _p, b in self.posted],
                         [{"sessions": []}, {"sessions": ["web", "api"], "expectedSourceFp": ks.fingerprint(NEW_KEY)}])
        self.assertIn("skipped: a turn, subagents or background tasks are in flight", said)
        self.assertIn("already on this key", said)
        self.assertIn("re-run --cycle for the skipped sessions", said)

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
            rc, said = self.run_cli("lowprio")
            self.assertEqual(rc, 1); self.assertIn("NOT ASKED", said)
            self.assertEqual(ks.read_key(self.path), NEW_KEY, "the file swap itself still landed")
            rc, said = self.run_cli("lowprio", "--cycle-all")
            self.assertEqual(rc, 1); self.assertIn("NOT DONE", said)
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


    def test_reference_profiles_are_listed_without_resolving_or_revealing_them(self):
        ref = "op://test-vault/test-item/api-key"
        self.sibling("vault", "ROMP_API_KEY_REF=%s\n" % ref)
        before = open(self.path).read()
        rc, said = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("vault", said)
        self.assertIn("1Password reference", said)
        self.assertIn(ks.KeySource("op", ref).fingerprint(), said)
        self.assertNotIn(ref, said)
        self.assertEqual(open(self.path).read(), before)

    def test_selecting_a_reference_copies_only_the_reference_and_preserves_other_settings(self):
        ref = "op://test-vault/test-item/api-key"
        # A stale literal key in a profile must not be copied alongside its selected provider.
        self.sibling("vault", "ANTHROPIC_API_KEY=%s\nROMP_API_KEY_REF=%s\n" % (NEW_KEY, ref))
        rc, said = self.run_cli("vault")
        self.assertEqual(rc, 0)
        body = open(self.path).read()
        self.assertIn("ROMP_API_KEY_REF=" + ref, body)
        self.assertNotIn("ANTHROPIC_API_KEY=", body)
        self.assertNotIn(OLD_KEY, body)
        self.assertNotIn(NEW_KEY, body)
        self.assertEqual(ks.read_source(self.path), ks.KeySource("op", ref))
        for line in self.OTHER_LINES:
            self.assertIn(line, body)
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertEqual(sorted(os.listdir(self.d)),
                         ["service.env", "service.env.lowprio", "service.env.source", "service.env.vault"],
                         "no temp file left; `.source` is the durable op memory a reference selection writes")
        self.assertIn("no key was copied to disk", said)
        self.assertNotIn(ref, said)

    def test_selecting_a_legacy_key_removes_the_reference(self):
        ks.write_source(ks.KeySource("op", "op://test-vault/test-item/api-key"), self.path)
        rc, _ = self.run_cli("lowprio")
        self.assertEqual(rc, 0)
        self.assertEqual(ks.read_key(self.path), NEW_KEY)
        self.assertNotIn("ROMP_API_KEY_REF=", open(self.path).read())

    def test_selecting_the_current_reference_removes_a_leftover_plaintext_key(self):
        ref = "op://test-vault/test-item/api-key"
        self.sibling("vault", "ROMP_API_KEY_REF=%s\n" % ref)
        with open(self.path, "a") as fh:
            fh.write("ROMP_API_KEY_REF=%s\n" % ref)
        rc, _ = self.run_cli("vault")
        self.assertEqual(rc, 0)
        self.assertNotIn("ANTHROPIC_API_KEY=", open(self.path).read())
        self.assertEqual(ks.read_source(self.path), ks.KeySource("op", ref))

    def test_selecting_a_command_profile_writes_the_line_and_never_prints_the_command(self):
        # The profile mechanism is the reference's: a sibling file carrying a ROMP_CREDENTIAL_COMMAND= line
        # selects the command kind, its stale key and reference lines are not copied, and the command
        # text is never printed (a fingerprint stands for it).
        cmd = 'test-credential-helper "$1" --format=env'
        self.sibling("helper", "ANTHROPIC_API_KEY=%s\nROMP_API_KEY_REF=op://test-vault/test-item/api-key\n"
                               "ROMP_CREDENTIAL_COMMAND=%s\n" % (NEW_KEY, cmd))
        rc, said = self.run_cli("helper")
        self.assertEqual(rc, 0)
        body = open(self.path).read()
        self.assertIn("ROMP_CREDENTIAL_COMMAND=" + cmd, body)
        self.assertNotIn("ANTHROPIC_API_KEY=", body)
        self.assertNotIn("ROMP_API_KEY_REF=", body)
        self.assertEqual(ks.read_source(self.path), ks.KeySource("command", cmd))
        for line in self.OTHER_LINES:
            self.assertIn(line, body)
        self.assertEqual(open(ks.marker_path(self.path)).read(), "command\n")
        for hidden in (cmd, NEW_KEY, OLD_KEY):
            self.assertNotIn(hidden, said)
        self.assertIn("no manager restart needed", said)

    def test_changing_references_takes_effect_in_the_same_file(self):
        first = "op://test-vault/first/api-key"
        second = "op://test-vault/second/api-key"
        ks.write_source(ks.KeySource("op", first), self.path)
        self.sibling("second", "ROMP_API_KEY_REF=%s\n" % second)
        rc, _ = self.run_cli("second")
        self.assertEqual(rc, 0)
        self.assertEqual(ks.read_source(self.path), ks.KeySource("op", second))
        self.assertNotIn(first, open(self.path).read())

    def test_invalid_reference_profiles_refuse_to_fall_back_to_a_legacy_key(self):
        import io
        from contextlib import redirect_stderr
        before = open(self.path).read()
        for ref in ("", "not-an-op-reference", "op://"):
            self.sibling("invalid", "ANTHROPIC_API_KEY=%s\nROMP_API_KEY_REF=%s\n" % (NEW_KEY, ref))
            errors = io.StringIO()
            with redirect_stderr(errors):
                rc, said = self.run_cli("invalid")
            self.assertEqual(rc, 2)
            self.assertIn("invalid key source", errors.getvalue())
            self.assertEqual(open(self.path).read(), before)
            self.assertNotIn(NEW_KEY, errors.getvalue() + said)

    def test_invalid_live_reference_is_an_error_even_when_the_kernel_is_down(self):
        with open(self.path, "w") as fh:
            fh.write("ROMP_API_KEY_REF=\n")
        rc, said = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("configuration invalid", said)
        self.assertEqual(self.posted, [])

    def test_reference_cycle_compares_configuration_and_allows_rotation_behind_the_same_reference(self):
        ref = "op://test-vault/test-item/api-key"
        source = ks.KeySource("op", ref)
        ks.write_source(source, self.path)
        self.sibling("vault", "ROMP_API_KEY_REF=%s\n" % ref)
        mtime = os.stat(self.path).st_mtime_ns
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "sourceFp": source.fingerprint(), "keyFp": ks.fingerprint(NEW_KEY),
            "rows": [{"session": "web", "status": "cycling"}]}
        rc, said = self.run_cli("vault", "--cycle", "web")
        self.assertEqual(rc, 0)
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime)
        self.assertEqual([b for _, _, b in self.posted],
                         [{"sessions": []}, {"sessions": ["web"], "expectedSourceFp": source.fingerprint()}])
        self.assertIn("1Password reference matches", said)
        self.assertIn("reconnecting now", said)
        self.assertNotIn(ref, json.dumps(self.posted) + said)
        self.assertNotIn(NEW_KEY, json.dumps(self.posted) + said)

    def test_reference_cycle_refuses_old_kernels_and_mismatched_sources(self):
        ref = "op://test-vault/test-item/api-key"
        self.sibling("vault", "ROMP_API_KEY_REF=%s\n" % ref)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        for fields, expected in (({}, "romp refresh"), ({"sourceFp": "op:wrong-source"}, "MISMATCH")):
            self.posted.clear()
            cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
                "ok": True, "keyFp": ks.fingerprint(NEW_KEY), "rows": [], **fields}
            rc, said = self.run_cli("vault", "--cycle-all")
            self.assertEqual(rc, 1)
            self.assertIn(expected, said)
            self.assertIn("NOT DONE", said)
            self.assertEqual([b for _, _, b in self.posted], [{"sessions": []}])

    def test_provider_failure_is_reported_without_reverting_the_selected_reference(self):
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        self.sibling("vault", "ROMP_API_KEY_REF=%s\n" % source.value)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": False, "error": "1Password runtime key retrieval failed"}
        rc, said = self.run_cli("vault", "--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", said)
        self.assertIn("retrieval failed", said)
        self.assertEqual(ks.read_source(self.path), source)
        self.assertNotIn(OLD_KEY, open(self.path).read())
        self.assertEqual([b for _, _, b in self.posted], [{"sessions": []}])

    def test_a_provider_error_during_reconnect_exits_nonzero(self):
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        ks.write_source(source, self.path)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "sourceFp": source.fingerprint(),
            "rows": ([{"session": "web", "status": "error: 1Password runtime key retrieval failed"}]
                     if b.get("sessions") else [])}
        rc, said = self.run_cli("--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("retrieval failed", said)


    def test_a_changed_source_in_the_cycle_response_is_not_reported_as_success(self):
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        changed = ks.KeySource("op", "op://test-vault/other-item/api-key")
        ks.write_source(source, self.path)
        cli._kernel = lambda: "http://127.0.0.1:29855"

        def respond(url, path, body):
            self.posted.append((url, path, body))
            if "expectedSourceFp" in body:
                ks.write_source(changed, self.path)
                return {"ok": True, "sourceFp": changed.fingerprint(), "rows": []}
            return {"ok": True, "sourceFp": source.fingerprint(), "rows": []}

        cli._post = respond
        rc, said = self.run_cli("--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("source changed during the request", said)
        self.assertEqual(self.posted[-1][2]["expectedSourceFp"], source.fingerprint())

    def test_refresh_re_reads_and_notes_it_on_the_kernel_line(self):
        # --refresh under a key line or a reference is a plain re-read (nothing cached to re-run); the kernel
        # line says what it was before when it moved, "unchanged" when it did not
        cli._kernel = lambda: "http://127.0.0.1:29855"
        live = ks.fingerprint(OLD_KEY)
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": live, "sourceFp": live, "keySource": "file", "rows": [],
            "refreshed": ({"from": "deadbeefcafe", "to": live, "err": ""} if b.get("refresh") else None)}
        rc, said = self.run_cli("--refresh")
        self.assertEqual(rc, 0, said)
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": [], "refresh": True}])
        self.assertIn("kernel      reads sha256:%s (re-read now: was sha256:deadbeefcafe)" % live, said)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": live, "sourceFp": live, "keySource": "file", "rows": [],
                                     "refreshed": {"from": live, "to": live, "err": ""}}
        rc, said = self.run_cli("--refresh")
        self.assertEqual(rc, 0, said)
        self.assertIn("kernel      reads sha256:%s (re-read now: unchanged)" % live, said)
        # under the reference a status read fingerprints nothing (it never runs op), so the note says only
        # that the kernel re-read its configuration
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        ks.write_source(source, self.path)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": "", "sourceFp": source.fingerprint(), "keySource": "op",
                                     "rows": [], "refreshed": {"from": "", "to": "", "err": ""}}
        rc, said = self.run_cli("--refresh")
        self.assertEqual(rc, 0, said)
        self.assertIn("kernel      source %s (re-read now)" % source.fingerprint(), said)
        self.assertIn("1Password reference matches", said)

    def test_a_cycling_row_carries_the_fingerprint_its_cli_launched_on(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        live = ks.fingerprint(NEW_KEY)
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": live, "sourceFp": live, "keySource": "file",
            "rows": ([{"session": "web", "status": "cycling", "from": ks.fingerprint(OLD_KEY)},
                      {"session": "api", "status": "current", "from": live},
                      {"session": "tests", "status": "cycling", "from": ""}] if b.get("all") else [])}
        rc, said = self.run_cli("lowprio", "--cycle-all")
        self.assertEqual(rc, 0, said)
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % ks.fingerprint(OLD_KEY), said)
        self.assertIn("  api            already on this key — nothing to do", said)
        self.assertNotIn("nothing to do (from", said, "the tail rides cycling rows only")
        self.assertIn("  tests          reconnecting now — history kept\n", said + "\n")   # no stamp, no tail
        self.assertNotIn(OLD_KEY, said)
        self.assertNotIn(NEW_KEY, said)

    def test_a_kernel_on_another_kind_is_a_mode_mismatch_and_stops_a_cycle(self):
        # the kernel selects its source live from ITS service.env and environment; this shell's file says a key
        # line, the kernel answers a credential command: the words name both, the causes and no fingerprint compare
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": "abc123abc123", "sourceFp": "0123456789ab", "keySource": "command",
            "keyKind": "key", "rows": [{"session": "web", "status": "cycling"}]}
        rc, said = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      key source: a credential command (ROMP_CREDENTIAL_COMMAND); reads sha256:abc123abc123", said)
        self.assertIn("MISMATCH    the kernel's key source is a credential command (ROMP_CREDENTIAL_COMMAND);\n"
                      "            this shell's is an API key line (ANTHROPIC_API_KEY).", said)
        self.assertIn("reads another service.env:", said)
        self.assertIn("the kernel's environment carries ROMP_CREDENTIAL_COMMAND (a foreground manager started from a shell", said)
        self.assertNotIn("this shell's environment carries", said, "this shell's source is the file's; no environment bullet for it")
        self.assertNotIn("the kernel is not reading this file's key source", said, "the mode words, not the fingerprint words")
        self.posted.clear()
        rc, said = self.run_cli("--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH", said)
        self.assertIn("cycle       NOT DONE", said)
        self.assertEqual([b for _u, _p, b in self.posted], [{"sessions": []}], "the read only; nothing was cycled")
        # a reference in the file against a kernel on a key line: the same words, the reference named by its word
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        ks.write_source(source, self.path)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": "abc123abc123", "sourceFp": "abc123abc123", "keySource": "file", "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("this shell's is a 1Password reference (ROMP_API_KEY_REF)", said)
        # an answer without keySource (an older kernel) takes the source compare as before
        cli._post = lambda u, p, b: {"ok": True, "keyFp": "", "sourceFp": source.fingerprint(), "rows": []}
        rc, said = self.run_cli()
        self.assertEqual(rc, 0, said)
        self.assertNotIn("MISMATCH", said)

    def test_a_command_profile_is_compared_by_its_source_fingerprint(self):
        # selecting a service.env.<name> that carries a ROMP_CREDENTIAL_COMMAND line (the reference's profile
        # mechanism) is then checked against the kernel like a reference: by source identity, never by key
        value = fixture_value("profile")
        script = os.path.join(self.d, "cred.sh")
        with open(script, "w") as fh:
            fh.write("#!/bin/sh\necho 'ANTHROPIC_API_KEY=%s'\n" % value)
        os.chmod(script, 0o700)
        cmd = script + ' "$1"'
        self.sibling("helper", "ROMP_CREDENTIAL_COMMAND=%s\n" % cmd)
        new = ks.KeySource("command", cmd)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((u, p, b)) or {
            "ok": True, "keyFp": "abc123abc123", "sourceFp": new.fingerprint(), "keySource": "command", "keyKind": "key",
            "rows": [{"session": "web", "status": "cycling", "from": "deadbeefcafe"}] if b.get("all") else []}
        rc, said = self.run_cli("helper", "--cycle-all")
        self.assertEqual(rc, 0, said)
        self.assertEqual(ks.read_source(self.path), new)
        self.assertIn("credential command %s" % new.fingerprint(), said)
        self.assertIn("the credential command matches", said)
        self.assertIn("no key was copied to disk", said)
        self.assertEqual([b for _u, _p, b in self.posted],
                         [{"sessions": []}, {"all": True, "expectedSourceFp": new.fingerprint()}])
        self.assertIn("(from sha256:deadbeefcafe)", said)
        self.assertNotIn(cmd, said)
        # the file now selects the command, so <name> would be a selector for it (the command arm); the bare
        # report is the compare, and a kernel on another command text is a source MISMATCH
        cli._post = lambda u, p, b: {"ok": True, "keyFp": "abc123abc123", "sourceFp": "0123456789ab", "keySource": "command", "rows": []}
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.d, "selector")
        rc, said = self.run_cli()
        self.assertEqual(rc, 1, said)
        self.assertIn("MISMATCH    the kernel runs another command", said)
        self.assertIn("key source  command sha256:%s   (ROMP_CREDENTIAL_COMMAND in %s)" % (new.fingerprint(), self.path), said)
        self.assertNotIn(cmd, said)
        self.assertNotIn(value, said)

    def test_a_second_positional_is_counted_never_echoed(self):
        import io
        import sys
        buf, was = io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            rc, _said = self.run_cli("lowprio", NEW_KEY)
        finally:
            sys.stderr = was
        self.assertEqual(rc, 2)
        self.assertIn("one source at a time (2 positional arguments given)", buf.getvalue())
        self.assertNotIn(NEW_KEY, buf.getvalue(), "a key typed where a name was expected never reaches stderr")
        self.assertEqual(ks.read_key(self.path), OLD_KEY)


class KeyswapCliCommandMode(unittest.TestCase):
    """`romp keyswap` under the COMMAND kind (a ROMP_CREDENTIAL_COMMAND line in service.env, or the variable in
    this shell's environment): the report, the named switch, the refresh and the cycle, against a fake command
    whose set depends on `$1` and a fake kernel that records what it was asked. The kernel is stubbed: these
    tests must never dial a real one, and KeySource.resolve is patched to fail, since the CLI never resolves.

    The fake command prints a different ANTHROPIC_API_KEY per selector name (hp, lp) plus a role variable; the
    values are assembled at run time. The fake kernel answers the way the route does (keySource, sourceFp,
    keyFp, keyKind, setFp, selector, launched, refreshed, rows) from whatever `self.kernel_view` holds, so a
    test moves the kernel's view to make the two sides agree or disagree."""

    SAVED = es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR", "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV",
                              "ROMP_API_KEY_REF", "ANTHROPIC_API_KEY")

    def setUp(self):
        from unittest import mock
        self.lab = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in self.SAVED}
        for v in ("ROMP_API_KEY_REF", "ANTHROPIC_API_KEY"):
            os.environ.pop(v, None)
        # absent by default: the command rides this shell's environment (the door a foreground manager has);
        # the file-door tests write the line into this path instead
        self.path = os.path.join(self.lab, "service.env")
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")     # no settings.json: no helper
        self.selector = os.path.join(self.lab, "selector")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = self.selector
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        self.keys = {"hp": fixture_value("hp"), "lp": fixture_value("lp")}
        self.role = fixture_value("role")
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.command_by_selector()
        self.command_text = self.cmd + ' "$1"'
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.command_text
        self.select("hp")
        es._reset()
        ks._CACHE = ((), "")
        resolver = mock.patch.object(ks.KeySource, "resolve", side_effect=AssertionError("CLI resolved a secret"))
        resolver.start()
        self.addCleanup(resolver.stop)
        self.posted = []
        self._saved = (cli._kernel, cli._post)
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((p, b)) or self.kernel_answer(b)
        # the kernel's view: by default it agrees with this shell (its own run of the same command)
        self.kernel_view = {"keySource": "command", "sourceFp": self.source_fp(), "keyFp": self.fp("hp"),
                            "keyKind": "key", "setFp": self.set_fp("hp"), "selector": "hp", "keyErr": "",
                            "launched": {self.fp("hp"): 3}, "rows": []}

    def tearDown(self):
        cli._kernel, cli._post = self._saved
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()
        ks._CACHE = ((), "")
        shutil.rmtree(self.lab, ignore_errors=True)

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

    def line_in_file(self, extra_lines=()):
        """Move the command from this shell's environment into service.env (the file door)."""
        with open(self.path, "w") as fh:
            fh.write("".join(l + "\n" for l in extra_lines) + "ROMP_CREDENTIAL_COMMAND=%s\n" % self.command_text)
        os.chmod(self.path, 0o600)
        os.environ.pop("ROMP_CREDENTIAL_COMMAND", None)
        es._reset()
        ks._CACHE = ((), "")

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

    def source_fp(self, text=None):
        return ks.KeySource("command", self.command_text if text is None else text).fingerprint()

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
        self.assertNotIn(self.command_text, blob, "the command text is rendered by fingerprint only")

    # -- the bare report --
    def test_the_bare_report_names_the_source_selector_candidates_and_fingerprints(self):
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0, out)
        self.assertEqual(err, "")
        self.assertIn("key source  command sha256:%s   (ROMP_CREDENTIAL_COMMAND in this shell's environment" % self.source_fp(), out)
        self.assertIn("selector    hp             " + self.selector, out)
        self.assertIn("candidates  hp <- selected, lp", out)
        self.assertIn("set         sha256:%s (2 names: ANTHROPIC_API_KEY, ROLE_TOKEN)" % self.set_fp("hp"), out)
        self.assertIn("live key    sha256:%s   (this shell's run of the command: its ANTHROPIC_API_KEY line)" % self.fp("hp"), out)
        self.assertIn("kernel      reads sha256:%s (its own run); 3 live session(s) on it" % self.fp("hp"), out)
        self.assertNotIn("MISMATCH", out)
        self.assertIn("rotate:     romp keyswap <name>  writes the selector (one of: hp, lp)", out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": []})], "a read that names no session, no refresh")
        self.assertEqual(self.selected(), "hp", "a report writes nothing")
        self.assertEqual(ks.read_source(self.path).kind, "none", "nothing was written to the env file")
        self.assertClean(out, err)

    def test_a_command_line_in_service_env_selects_the_arm_through_the_file_door(self):
        # the same line in the file (the door every manager has, supervised included): the arm is the same,
        # the header names the file, and a key line beside it is ignored (command > reference > key)
        self.line_in_file(["ROMP_PERF=1", "ANTHROPIC_API_KEY=%s" % OLD_KEY])
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0, out)
        self.assertIn("key source  command sha256:%s   (ROMP_CREDENTIAL_COMMAND in %s)" % (self.source_fp(), self.path), out)
        self.assertIn("live key    sha256:%s" % self.fp("hp"), out)
        self.assertNotIn("sha256:" + ks.fingerprint(OLD_KEY), out, "the key line is not the source and is not shown")
        self.assertNotIn(OLD_KEY, out + err)
        self.assertNotIn("MISMATCH", out)
        self.assertEqual(open(self.path).read().count("ROMP_CREDENTIAL_COMMAND="), 1, "the report rewrites nothing")
        self.assertClean(out, err)

    def test_the_report_counts_the_live_sessions_still_on_another_fingerprint(self):
        self.kernel_view["launched"] = {self.fp("hp"): 2, self.fp("lp"): 1, "": 1}
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("2 live session(s) on it", out)
        self.assertIn("            1 live session(s) still on sha256:" + self.fp("lp"), out)
        self.assertIn("            1 live session(s) launched with no credential the kernel fingerprinted", out)

    def test_mismatch_when_the_kernel_selects_another_kind_names_the_live_selection_causes(self):
        # the kernel selects its source live from ITS service.env and environment; this shell's command rides
        # its environment alone, which a supervised manager never reads
        self.kernel_view.update({"keySource": "file", "keyFp": "", "launched": {"": 3}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      key source: an API key line (ANTHROPIC_API_KEY)", out)
        self.assertIn("MISMATCH    the kernel's key source is an API key line (ANTHROPIC_API_KEY);\n"
                      "            this shell's is a credential command (ROMP_CREDENTIAL_COMMAND).", out)
        self.assertIn("selects its source live", out)
        self.assertIn("reads another service.env:", out)
        self.assertIn("this shell reads %s." % self.path, " ".join(out.split()), "the other-file cause names this shell's path")
        self.assertIn("this shell's environment carries ROMP_CREDENTIAL_COMMAND and the kernel does not read it", out)
        self.assertIn("a supervised manager (the login service) reads service.env only", out)
        self.assertIn("Put the line in service.env", out)
        self.assertIn("run this again", out)
        for gone in ("pinned", "keeps the mode it started in", "daemon-reload", "kickstart", "launchctl"):
            self.assertNotIn(gone, out, "the pinned-mode paragraphs and the restart block are gone with the pin")
        self.assertEqual(self.posted, [("/keycycle", {"sessions": []})])
        # the reference is named by its word; and the environment bullet is not offered when this shell's
        # command comes from the file, which every manager reads
        self.kernel_view.update({"keySource": "op"})
        self.line_in_file()
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      key source: a 1Password reference (ROMP_API_KEY_REF)", out)
        self.assertIn("the kernel's environment carries ROMP_API_KEY_REF (a foreground manager started from a shell", out)
        self.assertNotIn("this shell's environment carries", out)
        self.assertIn("reads another service.env:", out)
        # an older kernel answers without keySource: named as such, with the restart that brings it here
        del self.kernel_view["keySource"]
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("the kernel predates the credential command: `romp refresh` restarts it on this code", out)

    def test_an_alias_only_shell_is_told_the_installer_reads_the_primary_name(self):
        # bin/romp-service resolves its SERVICE_ENV_FILE from ROMP_SERVICE_ENV_FILE only, so a shell whose path
        # rides the alias ROMP_SERVICE_ENV would bake the DEFAULT path into the unit or the plist: the other-file
        # hint says so and names the export that makes the install remedy work, and never claims the installer
        # reads the alias. A shell with the primary name set gets no alias lines.
        self.kernel_view.update({"keySource": "file", "keyFp": "", "launched": {"": 3}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertFalse(cli._path_alias(), "ROMP_SERVICE_ENV_FILE is set: not an alias-only shell")
        self.assertNotIn("does not read: export ROMP_SERVICE_ENV_FILE", out)
        os.environ.pop("ROMP_SERVICE_ENV_FILE")
        self.assertTrue(cli._path_alias())
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        flat = " ".join(out.split())
        self.assertIn("this shell reads %s." % self.path, flat)
        self.assertIn("This shell set the path under the alias ROMP_SERVICE_ENV, which `romp-service install` "
                      "does not read: export ROMP_SERVICE_ENV_FILE with this shell's path (or prefix the install "
                      "command with it) before installing from this shell.", flat)
        for false_claim in ("which the installer reads too", "resolves the alias", "writes into the unit"):
            self.assertNotIn(false_claim, flat)
        # the alias lines follow the remedy they qualify, and every line fits the report's width under the
        # caller's pad; only a path, which is never broken, may run past it
        lines = cli._other_file(self.path, 14, alias=True)
        self.assertEqual(len(lines) - len(cli._other_file(self.path, 14)), 3)
        self.assertTrue(lines[-4].startswith("`romp-service install` from this shell."), lines[-4])
        self.assertTrue(lines[-3].startswith("This shell set the path under the alias"), lines[-3])
        for path in (self.path, "/" + "p" * 120 + "/service.env"):
            for line in cli._other_file(path, 14, alias=True):
                if path not in line:
                    self.assertLessEqual(14 + len(line), cli.WIDTH, line)

    def test_mismatch_when_the_kernel_runs_another_command_text(self):
        # the kernel's sourceFp is the hash of the command text it selected: another text is another source,
        # and the credential compare is not attempted (nothing to compare)
        self.kernel_view.update({"sourceFp": self.source_fp("other-cmd \"$1\""), "keyFp": self.fp("lp"),
                                 "setFp": self.set_fp("lp"), "launched": {self.fp("lp"): 1}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH    the kernel runs another command: its source is sha256:%s, this shell's sha256:%s."
                      % (self.source_fp("other-cmd \"$1\""), self.source_fp()), out)
        self.assertIn("reads another service.env:", out)
        self.assertIn("this shell's environment carries a ROMP_CREDENTIAL_COMMAND that is not the line the kernel", out)
        self.assertNotIn("disagree on the credential fingerprint", out)
        self.assertNotIn("other-cmd", out, "the kernel's command text is not known here and no text is printed")
        self.line_in_file()
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("the kernel's environment carries another ROMP_CREDENTIAL_COMMAND (a foreground manager", out)
        self.assertNotIn("this shell's environment carries", out)

    def test_mismatch_when_the_kernels_fingerprint_differs_names_the_two_environments(self):
        self.kernel_view.update({"keyFp": self.fp("lp"), "setFp": self.set_fp("lp"), "launched": {self.fp("lp"): 1}})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH    the kernel's run of the command and this shell's disagree on the credential "
                      "fingerprint and the set's fingerprint.", out)
        self.assertIn("ROMP_CREDENTIAL_NAMES, ROMP_CREDENTIAL_SELECTOR_FILE or ROMP_CREDENTIAL_TIMEOUT_S", out)
        self.assertIn("a manager's environment holds the copy loaded at its start", out)
        self.assertIn("different selector files", out)
        self.assertIn("CLAUDE_CONFIG_DIR", out)
        self.assertIn("the command's output depends on its environment", out)
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
        self.assertIn("kernel      not running; it runs the command itself when it is", out)
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
        self.kernel_view.update({"keyFp": hfp, "keyKind": "helper", "setFp": es.set_fingerprint({"ROLE_TOKEN": self.role}),
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
        self.assertIn("live key    (none): the set carries no ANTHROPIC_API_KEY and no apiKeyHelper in", out)
        self.assertIn("sessions bill the machine login, and a", out)
        self.assertIn("cycle covers the role variables in the set", out)
        self.assertIn("kernel      reads no key (its own run): sessions bill the machine login; a cycle covers the role", out)
        self.assertIn("variables (set sha256:%s); 2 live session(s) launched with no key" % set_fp, out)
        self.assertNotIn("UNAVAILABLE", out)
        self.assertNotIn("MISMATCH", out)
        self.assertNotIn("launched with no credential the kernel fingerprinted", out, "the login rows are the expected rows")
        self.assertEqual(rc, 0, "a login-billed installation is a state, not a failure")
        self.assertClean(out, err)
        # ...and the cycle proceeds on that footing, guarded by the source fingerprint like every cycle
        self.kernel_view["rows"] = [{"session": "web", "status": "cycling", "from": ""}]
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.posted[-1], ("/keycycle", {"all": True, "expectedSourceFp": self.source_fp()}))

    def test_a_local_command_failure_is_loud_and_cycles_nothing(self):
        self.command("echo 'noise: %s' >&2\nexit 3" % self.keys["hp"])
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("live key    UNAVAILABLE: the credential command exited 3 after", out)
        self.assertIn("stderr", out)                        # a byte count, never the bytes
        self.assertClean(out, err)
        self.posted.clear()
        rc, out, err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("cycle       NOT DONE: this shell could not fingerprint the credential", out)
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
        self.assertEqual(ks.read_source(self.path).kind, "none", "a switch writes the selector, never the env file")
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

    def test_a_name_that_is_not_a_token_is_refused_by_shape_and_never_echoed(self):
        # a path is not a selector either: under a credential command <name> is a name for the command, and
        # the sibling-profile selection of the other kinds does not run here
        for arg, n in (("bad name!", 9), ("/nonexistent/service.env.lowprio", 32), ("../x", 4)):
            rc, out, err = self.run_cli(arg)
            self.assertEqual(rc, 2, arg)
            self.assertEqual(out, "")
            self.assertIn("a selector is one name", err)
            self.assertIn("(%d characters given)" % n, err)
            self.assertIn("<name> is a selector for the command, not a profile", err)
            self.assertNotIn(arg, err)
        self.assertEqual(es._runs, 0)
        self.assertEqual(self.selected(), "hp")
        self.assertEqual(ks.read_source(self.path).kind, "none")

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
        self.assertIn("selector    (undeclared, 2 chars) ", out)
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
        # ...and undone, when the command then fails for the new name, the old token goes back unnamed
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
        self.assertIn("live key    UNAVAILABLE: the credential command exited 4 after", out)
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
        # the line says so, never "put back to" something that was never read
        junk = fixture_value("junk") + " with spaces"
        self.select(junk)
        self.command("case \"$1\" in hp) echo 'ANTHROPIC_API_KEY=%s' ;; *) exit 4 ;; esac" % self.keys["hp"])
        rc, out, err = self.run_cli("lp")
        self.assertEqual(rc, 1)
        self.assertIn("selector    (none) -> lp, NOT put back: the old selector could not be read before the switch", out)
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

    def test_a_switch_with_no_kernel_says_the_next_read_runs_the_new_selector(self):
        cli._kernel = lambda: None
        rc, out, _err = self.run_cli("lp")
        self.assertEqual(rc, 0)
        self.assertEqual(self.selected(), "lp")
        self.assertIn("kernel      not running; its first read runs the command with the new selector", out)

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
                         [{"sessions": [], "refresh": True}, {"sessions": [], "refresh": True},
                          {"all": True, "expectedSourceFp": self.source_fp()}])
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
        self.assertEqual([b for _p, b in self.posted],
                         [{"sessions": [], "refresh": True}, {"all": True, "expectedSourceFp": self.source_fp()}],
                         "the refresh-and-read, then the cycle, and never a session named by the CLI itself")
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % self.fp("lp"), out)
        self.assertIn("  api            already on this key — nothing to do", out)
        self.assertIn("  tests          skipped: a turn, subagents or background tasks are in flight", out)
        self.assertIn("            re-run --cycle for the skipped sessions once those are quiet", out)
        self.assertClean(out, err)

    def test_cycle_names_exactly_the_given_sessions(self):
        rc, _out, _err = self.run_cli("--cycle", "web,api")
        self.assertEqual(rc, 0)
        self.assertEqual(self.posted[-1], ("/keycycle", {"sessions": ["web", "api"], "expectedSourceFp": self.source_fp()}))

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

    def test_a_source_change_during_the_cycle_is_not_reported_as_success(self):
        # the kernel re-selected another source between the read and the cycle (a swap landing mid-request):
        # the answer's sourceFp differs from the one this shell compared against, and the rows are not trusted
        def respond(url, path, body):
            self.posted.append((path, body))
            ans = self.kernel_answer(body)
            if "expectedSourceFp" in body:
                ans["sourceFp"] = self.source_fp("swapped-cmd")
                ans["rows"] = [{"session": "web", "status": "cycling", "from": self.fp("hp")}]
            return ans
        cli._post = respond
        rc, out, _err = self.run_cli("--cycle", "web")
        self.assertEqual(rc, 1)
        self.assertIn("source changed during the request", out)
        self.assertNotIn("reconnecting now", out)
        self.assertEqual(self.posted[-1][1]["expectedSourceFp"], self.source_fp())

    def test_a_kernel_run_that_failed_is_said_and_stops_the_cycle(self):
        self.kernel_view.update({"keyErr": "exited 3 after 0.2s, stderr 40 bytes"})
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("the latest run failed (exited 3 after 0.2s, stderr 40 bytes), so it stands on the previous set", out)
        self.kernel_view.update({"keyFp": "", "launched": {}})
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("kernel      UNAVAILABLE: exited 3 after 0.2s, stderr 40 bytes", out)
        self.assertIn("cycle       NOT DONE", out)

    def test_no_value_reaches_stdout_or_stderr_whatever_the_arguments(self):
        loud = "\n".join("echo '%s' >&2" % v for v in list(self.keys.values()) + [self.role])
        self.command_by_selector(extra=loud)                 # every value also on stderr
        for argv in ([], ["lp"], ["hp"], ["nosuch"], ["--refresh"], ["--cycle-all"], ["--cycle", "web"],
                     ["lp", "--cycle-all"], ["--wat"], ["a", "b"], [self.keys["hp"]], [self.command_text]):
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

    def test_the_cli_decides_the_arm_without_the_kernels_selector(self):
        # keysource.select_source remembers a runtime selection on disk (service.env.source) and in memory;
        # those writes are the kernel's, so the CLI reads the file and this shell's environment instead
        src = open(os.path.join(ROOT, "cli", "keyswap.py")).read()
        self.assertNotIn("select_source(", src)
        self.assertNotIn(ks.marker_path(self.path)[len(self.path):].lstrip("."), os.listdir(self.lab),
                         "no marker was written by a report")


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
        self.assertEqual(resp["rows"], [{"session": "web", "status": "cycling", "from": ""},
                                        {"session": "api", "status": "login", "from": ""},
                                        {"session": "gone", "status": "dormant", "from": ""}])
        self.assertEqual(resp["keySource"], "file", "a backend without the key-source surface reads as the file kind")
        self.assertEqual(resp["keyKind"], "")
        self.assertEqual(resp["keyErr"], "")
        self.assertEqual(resp["setFp"], "")
        self.assertEqual(resp["selector"], "")
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
        fake.cycle_key = lambda sid: (_ for _ in ()).throw(RuntimeError("boom " + NEW_KEY))
        code, resp = self._with(fake, {"sessions": ["web", "api"]})
        self.assertEqual(code, 200)
        self.assertEqual(len(resp["rows"]), 2, "one bad session must not abandon the rest")
        self.assertEqual(resp["rows"][0]["status"], "error: API credential source failed")
        self.assertNotIn(NEW_KEY, json.dumps(resp))

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
        self.assertEqual(resp["keyKind"], "key")
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
        self.assertLess(fake.calls.index("refresh"), fake.calls.index("status"))
        self.assertLess(fake.calls.index("refresh"), fake.calls.index("cycle s-web"))
        code, resp = self._with(fake, {"sessions": [], "refresh": True})
        self.assertEqual(resp["rows"], [])
        self.assertEqual(resp["refreshed"]["to"], ks.fingerprint(NEW_KEY), "a bare --refresh: no rows, one re-run")

    def test_a_refresh_that_raises_is_reported_in_the_refreshed_block_not_fatal(self):
        fake = self._Full({})
        fake.refresh_key_source = lambda: (_ for _ in ()).throw(RuntimeError("boom " + NEW_KEY))
        code, resp = self._with(fake, {"sessions": [], "refresh": True})
        self.assertEqual(code, 200)
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["refreshed"], {"from": "", "to": "", "err": "API credential source failed"})
        self.assertNotIn(NEW_KEY, json.dumps(resp))

    def test_a_key_error_rides_the_answer(self):
        fake = self._Full({})
        fake.key_source_status = lambda: {"source": "command", "fp": "", "err": "exited 3 after 0.4s, stderr 87 bytes",
                                          "launched": {}}
        code, resp = self._with(fake, {"sessions": []})
        self.assertEqual(resp["keyErr"], "exited 3 after 0.4s, stderr 87 bytes")
        self.assertEqual(resp["keySource"], "command")
        self.assertEqual(resp["keyKind"], "")

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


    def _provider_backend(self, source):
        """Exercise real cycle_key with an inert session and a synthetic provider descriptor."""
        import threading
        from types import SimpleNamespace
        scheduled = []
        session = SimpleNamespace(
            name="web", effective_auth=lambda key=None: "key", _sub_lock=threading.Lock(),
            _subagents={}, _bg_tasks={}, inflight=0, _pending=[],
            _launched_key_fp=ks.fingerprint(OLD_KEY),
            request_reconnect=lambda defer=True: scheduled.append(defer),
        )
        backend = SimpleNamespace(sessions={"s-web": session}, _log=lambda message: None)
        backend.owns = lambda sid: sid in backend.sessions
        backend._work_key_source = lambda: source
        backend._work_key_and_source = lambda selected=None: ((selected or source).resolve(), source.kind)
        backend.cycle_key = lambda sid, **kwargs: sb.SdkBackend.cycle_key(backend, sid, **kwargs)
        return backend, scheduled

    def test_provider_status_returns_source_identity_without_retrieving_a_key(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        backend, scheduled = self._provider_backend(source)
        with mock.patch.object(ks.KeySource, "resolve", side_effect=AssertionError("status retrieved a secret")) as resolve:
            code, resp = self._with(backend, {"sessions": []})
        self.assertEqual(code, 200)
        self.assertTrue(resp["ok"])
        self.assertEqual(resp["sourceFp"], source.fingerprint())
        self.assertEqual(resp["keyFp"], "")
        self.assertEqual(resp["rows"], [])
        self.assertEqual(scheduled, [])
        resolve.assert_not_called()
        self.assertNotIn(source.value, json.dumps(resp))
        self.assertEqual(resp["keySource"], "op", "the selected kind, read from the source when the backend has no status surface")
        self.assertEqual(resp["keyKind"], "")
        self.assertEqual(resp["launched"], {})
        self.assertIsNone(resp["refreshed"])

    def test_invalid_provider_configuration_stops_the_route_before_retrieval_or_reconnect(self):
        from unittest import mock
        backend, scheduled = self._provider_backend(ks.KeySource("op", ""))
        with mock.patch.object(ks.KeySource, "resolve", side_effect=AssertionError("invalid source resolved")) as resolve:
            code, resp = self._with(backend, {"sessions": ["web"]})
        self.assertEqual(code, 200)
        self.assertFalse(resp["ok"])
        self.assertIn("ROMP_API_KEY_REF", resp["error"])
        self.assertEqual(scheduled, [])
        resolve.assert_not_called()

    def test_a_stale_expected_source_is_rejected_before_any_provider_or_reconnect(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        backend, scheduled = self._provider_backend(source)
        with mock.patch.object(ks.KeySource, "resolve", side_effect=AssertionError("stale source resolved")) as resolve:
            code, resp = self._with(backend, {"sessions": ["web"], "expectedSourceFp": "stale-source"})
        self.assertEqual(code, 409)
        self.assertFalse(resp["ok"])
        self.assertIn("source changed", resp["error"])
        self.assertEqual(scheduled, [])
        resolve.assert_not_called()

    def test_a_source_change_during_provider_retrieval_does_not_schedule_reconnect(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        changed = ks.KeySource("op", "op://test-vault/other-item/api-key")
        backend, scheduled = self._provider_backend(source)
        selected = [source]
        backend._work_key_source = lambda: selected[0]

        def resolve_and_change():
            selected[0] = changed
            return NEW_KEY

        with mock.patch.object(ks.KeySource, "resolve", side_effect=resolve_and_change) as resolve:
            code, resp = self._with(backend, {"sessions": ["web"], "expectedSourceFp": source.fingerprint()})
        self.assertEqual(code, 200)
        self.assertIn("source changed during retrieval", resp["rows"][0]["status"])
        self.assertEqual(scheduled, [])
        resolve.assert_called_once_with()
        self.assertNotIn(NEW_KEY, json.dumps(resp))

    def test_a_rotated_key_behind_the_same_reference_reconnects_the_session(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        backend, scheduled = self._provider_backend(source)
        with mock.patch.object(ks.KeySource, "resolve", return_value=NEW_KEY) as resolve:
            code, resp = self._with(backend, {"sessions": ["web"]})
        self.assertEqual(code, 200)
        self.assertEqual(resp["sourceFp"], source.fingerprint())
        self.assertEqual(resp["rows"], [{"session": "web", "status": "cycling", "from": ks.fingerprint(OLD_KEY)}])
        self.assertEqual(scheduled, [False])
        resolve.assert_called_once_with()
        self.assertNotIn(NEW_KEY, json.dumps(resp))

    def test_provider_failure_does_not_reconnect_a_live_session(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        backend, scheduled = self._provider_backend(source)
        with mock.patch.object(ks.KeySource, "resolve", side_effect=ks.KeySourceError("1Password credential retrieval failed")):
            code, resp = self._with(backend, {"sessions": ["web"]})
        self.assertEqual(code, 200)
        self.assertEqual(resp["rows"], [{"session": "web", "status": "error: 1Password credential retrieval failed",
                                        "from": ks.fingerprint(OLD_KEY)}])
        self.assertEqual(scheduled, [])

    def test_the_cli_reports_provider_failure_from_the_real_route_as_nonzero(self):
        from unittest import mock
        source = ks.KeySource("op", "op://test-vault/test-item/api-key")
        backend, scheduled = self._provider_backend(source)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "service.env")
            ks.write_source(source, path)
            said = []
            with mock.patch.dict(os.environ, {"ROMP_SERVICE_ENV_FILE": path}), \
                 mock.patch.object(cli, "_kernel", lambda: "http://127.0.0.1:%d" % self.port), \
                 mock.patch.object(cli, "_token", lambda: self.km.TOKEN), \
                 mock.patch.object(self.km, "_sdk", lambda: backend), \
                 mock.patch.object(self.km, "_sid_of", lambda name: "s-" + name), \
                 mock.patch.object(self.km, "_name_of", lambda sid: str(sid)[2:]), \
                 mock.patch.object(self.km, "_push_soon", lambda: None), \
                 mock.patch.object(ks.KeySource, "resolve", side_effect=ks.KeySourceError("1Password credential retrieval failed")) as resolve:
                rc = cli.main(["--cycle", "web"], out=said.append)
            self.assertEqual(rc, 1)
            self.assertIn("1Password credential retrieval failed", "\n".join(said))
            self.assertEqual(scheduled, [])
            resolve.assert_called_once_with()
            self.assertEqual(ks.read_source(path), source)


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
        ks._AUTHORITATIVE_PATHS.pop(self.path, None)
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
        self.assertNotIn("ANTHROPIC_API_KEY", os.environ,
                         "the one-claimer property: an ambient key bills every session")

    def test_the_problem_ring_the_dashboard_reads_never_carries_a_key(self):
        self.write_env("", lines=["ROMP_PERF=1"])       # a key pick with no key: the loudest path
        with self.assertRaises(ks.KeySourceError):
            self._launch_env(1)
        self.write_env(NEW_KEY)
        self._launch_env(2)
        for p in self.be.problems(50):
            self.assertNotIn(NEW_KEY, p["text"])
            self.assertNotIn(OLD_KEY, p["text"])


if __name__ == "__main__":
    unittest.main()
