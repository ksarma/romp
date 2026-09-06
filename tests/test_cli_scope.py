#!/usr/bin/env python3
"""Per-session transient systemd scopes (2026-09-05). Under the systemd user service every process
the service tree starts shares the service's cgroup, and KillMode=control-group (deliberately kept)
empties it on `systemctl --user restart romp-manager` — sessions' tmux jobs died with it. The fix
spawns each session's CLI through bin/romp-cli-scope (exec-in-place `systemd-run --scope`), decided
ONCE per backend by cli_scope_supported and applied in _options.

Under test here, with NO real systemd-run ever invoked (which/run are injected; conftest floors
ROMP_CLI_SCOPE=0 for every backend construction):
  * the cli_scope_supported truth table and the exact probe argv;
  * the backend caches one verdict at construction, and _options honours it: cli_path becomes the
    wrapper and ROMP_CLI_REAL carries the real CLI when on; both untouched when off;
  * a missing or non-executable wrapper degrades loudly (a problem line, once) to the direct path;
  * the wrapper's fallback notice (a failed pre-flight, the CLI run directly; its `fallback:` form)
    is logged the moment it arrives, as a problem naming the session, since on that path the CLI
    starts and nothing else would ever read it; its `refused:` line (ROMP_CLI_REAL unset, exit 127)
    is only buffered — no CLI started, and the launch-error path reports it.
Synthetic fixtures only: placeholder sid, /bin/true as the CLI.
"""
import os
import subprocess
import sys
import tempfile
import types
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_CLI_SCOPE"] = "0"   # the conftest floor, re-asserted for a bare unittest run
sb = SourceFileLoader("romp_sdk_backend_cli_scope", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
PROBE = ["systemd-run", "--user", "--scope", "--quiet", "--collect", "--", "true"]


def _which(found=True):
    return lambda name: ("/usr/bin/" + name) if found else None


class _Run:
    """A recording stand-in for subprocess.run: returns a fixed result, or raises."""

    def __init__(self, returncode=0, stderr=b"", raise_=None):
        self.calls = []
        self.rc, self.stderr, self.raise_ = returncode, stderr, raise_

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        if self.raise_:
            raise self.raise_
        return subprocess.CompletedProcess(argv, self.rc, stdout=b"", stderr=self.stderr)


class Supported(unittest.TestCase):
    """cli_scope_supported's truth table, on injected inputs."""

    def test_unsupervised_is_off_without_probing(self):
        run = _Run()
        self.assertFalse(sb.cli_scope_supported({}, which=_which(), platform="linux", run=run))
        self.assertEqual(run.calls, [], "no probe when the switch is off")

    def test_explicit_off_under_supervision(self):
        run = _Run()
        self.assertFalse(sb.cli_scope_supported({"ROMP_SUPERVISED": "1", "ROMP_CLI_SCOPE": "0"},
                                                which=_which(), platform="linux", run=run))
        self.assertEqual(run.calls, [])

    def test_supervised_without_systemd_run_is_off(self):
        run = _Run()
        logged = []
        self.assertFalse(sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(False), platform="linux", run=run,
                                                log=logged.append))
        self.assertEqual(run.calls, [], "nothing to probe with")
        self.assertEqual(len(logged), 1)
        self.assertTrue(logged[0].startswith("cli scope: off — "), logged)
        self.assertIn("systemd-run", logged[0])

    def test_supervised_with_a_failing_probe_is_off(self):
        run = _Run(returncode=1, stderr=b"Failed to start transient scope unit: Access denied\n")
        logged = []
        self.assertFalse(sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(), platform="linux", run=run,
                                                log=logged.append))
        self.assertEqual(len(run.calls), 1)
        self.assertTrue(logged[0].startswith("cli scope: off — "), logged)
        self.assertIn("Access denied", logged[0], "the probe's stderr is the reason the user reads")

    def test_a_probe_that_raises_is_off(self):
        for exc in (subprocess.TimeoutExpired(PROBE, 10), OSError("boom")):
            run = _Run(raise_=exc)
            logged = []
            self.assertFalse(sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(), platform="linux", run=run,
                                                    log=logged.append))
            self.assertTrue(logged[0].startswith("cli scope: off — "), logged)

    def test_supervised_with_a_passing_probe_is_on(self):
        run = _Run()
        logged = []
        self.assertTrue(sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(), platform="linux", run=run,
                                               log=logged.append))
        self.assertEqual(len(logged), 1)
        self.assertTrue(logged[0].startswith("cli scope: on — "), logged)

    def test_explicit_on_outside_supervision_probes_and_turns_on(self):
        run = _Run()
        self.assertTrue(sb.cli_scope_supported({"ROMP_CLI_SCOPE": "1"}, which=_which(), platform="linux", run=run))
        self.assertEqual(len(run.calls), 1)

    def test_the_probe_argv_is_exact_and_bounded(self):
        run = _Run()
        sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(), platform="linux", run=run)
        argv, kw = run.calls[0]
        self.assertEqual(argv, PROBE)
        self.assertEqual(sb.CLI_SCOPE_PROBE, PROBE)
        self.assertEqual(kw.get("timeout"), sb.CLI_SCOPE_PROBE_TIMEOUT)
        self.assertGreater(sb.CLI_SCOPE_PROBE_TIMEOUT, 0)
        self.assertLessEqual(sb.CLI_SCOPE_PROBE_TIMEOUT, 10)

    def test_an_empty_switch_value_is_not_on(self):
        run = _Run()
        self.assertFalse(sb.cli_scope_supported({"ROMP_CLI_SCOPE": ""}, which=_which(), platform="linux", run=run))
        self.assertEqual(run.calls, [])

    def test_no_log_callback_is_fine(self):
        self.assertTrue(sb.cli_scope_supported({"ROMP_CLI_SCOPE": "1"}, which=_which(), platform="linux", run=_Run()))

    def test_not_linux_is_off_before_which_or_probe(self):
        # the macOS launchd plist sets ROMP_SUPERVISED=1 too; scopes are a systemd feature, so the
        # verdict there is off with a reason that says so — not "systemd-run is not on PATH"
        for plat in ("darwin", "freebsd13", "win32"):
            run = _Run()
            which_calls = []
            logged = []
            ok = sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=lambda n: which_calls.append(n),
                                        run=run, log=logged.append, platform=plat)
            self.assertFalse(ok, plat)
            self.assertEqual(which_calls, [], "no PATH lookup off Linux")
            self.assertEqual(run.calls, [], "no probe off Linux")
            self.assertEqual(len(logged), 1)
            self.assertTrue(logged[0].startswith("cli scope: off — not Linux"), logged)
            self.assertNotIn("PATH", logged[0])

    def test_linux_variants_pass_the_platform_check(self):
        for plat in ("linux", "linux2"):
            self.assertTrue(sb.cli_scope_supported({"ROMP_SUPERVISED": "1"}, which=_which(), run=_Run(),
                                                   platform=plat), plat)

    def test_the_switch_off_reasons_win_over_the_platform(self):
        # off Linux, an explicit 0 or an unsupervised run still reports ITS reason, not the platform's
        logged = []
        sb.cli_scope_supported({"ROMP_SUPERVISED": "1", "ROMP_CLI_SCOPE": "0"}, which=_which(), run=_Run(),
                               log=logged.append, platform="darwin")
        self.assertIn("ROMP_CLI_SCOPE=0", logged[0])

    def test_the_platform_defaults_to_this_process(self):
        # no injected platform → sys.platform; on Linux that is the on path, elsewhere the off one
        run = _Run()
        ok = sb.cli_scope_supported({"ROMP_CLI_SCOPE": "1"}, which=_which(), run=run)
        self.assertEqual(ok, sys.platform.startswith("linux"))


class _Backend(unittest.TestCase):
    """A backend on a temp state dir, no real CLI, no real key claim, no SDK dependency."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._stash_before = sb._WORK_KEY
        sb._WORK_KEY = ""
        self._fetch_before = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None
        self._fake_sdk = "claude_agent_sdk" not in sys.modules and not sb.sdk_importable()
        if self._fake_sdk:
            fake = types.ModuleType("claude_agent_sdk")
            fake.HookMatcher = lambda **kw: kw
            sys.modules["claude_agent_sdk"] = fake
        self.logged = []
        # A backend whose verdict is ON exports ROMP_CLI_REAL into os.environ (the SDK's version probe
        # needs it there). Tests that turn the verdict on restore the variable themselves; this snapshot
        # is the backstop, so no test in these classes can leak it into the rest of the pytest process.
        self._real_before = os.environ.get("ROMP_CLI_REAL")
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logged.append)

    def tearDown(self):
        sb._WORK_KEY = self._stash_before
        sb._fetch_key_fast_org = self._fetch_before
        if self._fake_sdk:
            sys.modules.pop("claude_agent_sdk", None)
        if self._real_before is None:
            os.environ.pop("ROMP_CLI_REAL", None)
        else:
            os.environ["ROMP_CLI_REAL"] = self._real_before

    def _sess(self):
        return sb.SdkSession(self.be, {"sid": SID, "name": "web", "cwd": self.d, "mode": "acceptEdits"})

    def _kw(self):
        return self.be._options(self._sess(), dict)


class ConstructionVerdict(_Backend):
    """One verdict per backend, at construction."""

    def test_the_test_floor_leaves_the_scope_off(self):
        self.assertFalse(self.be.cli_scope)
        self.assertTrue(any(m.startswith("cli scope: off — ") for m in self.logged), self.logged)

    def test_the_verdict_is_taken_once_and_cached(self):
        calls = []
        before = sb.cli_scope_supported
        real_before = os.environ.pop("ROMP_CLI_REAL", None)   # an ON verdict exports it — restore below
        sb.cli_scope_supported = lambda **kw: calls.append(kw) or True
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        finally:
            sb.cli_scope_supported = before
            os.environ.pop("ROMP_CLI_REAL", None)
            if real_before is not None:
                os.environ["ROMP_CLI_REAL"] = real_before
        self.assertEqual(len(calls), 1)
        self.assertIn("log", calls[0])
        self.assertTrue(be.cli_scope)

    # The SDK's per-connect version check runs `[cli_path, "-v"]` with the KERNEL's os.environ, not
    # options.env (claude_agent_sdk 0.2.132), so with the verdict on the wrapper must find ROMP_CLI_REAL
    # in the process environment too — or the probe exits 127 and the version warning is silently off.
    def test_on_exports_the_real_cli_into_the_kernels_environment(self):
        before = os.environ.pop("ROMP_CLI_REAL", None)
        saved = sb.cli_scope_supported
        sb.cli_scope_supported = lambda **kw: True
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
            self.assertTrue(be.cli_scope)
            self.assertEqual(os.environ.get("ROMP_CLI_REAL"), "/bin/true")
        finally:
            sb.cli_scope_supported = saved
            os.environ.pop("ROMP_CLI_REAL", None)
            if before is not None:
                os.environ["ROMP_CLI_REAL"] = before

    def test_off_leaves_the_kernels_environment_alone(self):
        before = os.environ.pop("ROMP_CLI_REAL", None)
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)   # the test floor: off
            self.assertFalse(be.cli_scope)
            self.assertNotIn("ROMP_CLI_REAL", os.environ)
        finally:
            if before is not None:
                os.environ["ROMP_CLI_REAL"] = before


class OptionsWiring(_Backend):
    """_options routes the spawn through the wrapper exactly when the verdict is on."""

    def test_off_leaves_cli_path_and_env_untouched(self):
        self.be.cli_scope = False
        kw = self._kw()
        self.assertEqual(kw["cli_path"], "/bin/true")
        self.assertNotIn("ROMP_CLI_REAL", kw["env"])

    def test_on_spawns_the_wrapper_with_the_real_cli_in_the_env(self):
        self.be.cli_scope = True
        kw = self._kw()
        self.assertEqual(kw["cli_path"], sb.cli_scope_wrapper())
        self.assertEqual(kw["env"]["ROMP_CLI_REAL"], "/bin/true")
        # the identity vars the CLI relied on are still there — the overlay is additive
        self.assertEqual(kw["env"]["ROMP_SID"], SID)
        self.assertEqual(kw["env"]["ROMP_SESSION_NAME"], "web")

    def test_the_wrapper_is_the_repos_executable(self):
        w = sb.cli_scope_wrapper()
        self.assertTrue(os.path.isabs(w))
        self.assertEqual(os.path.realpath(w), os.path.realpath(os.path.join(BIN, "romp-cli-scope")))
        self.assertTrue(os.access(w, os.X_OK), "bin/romp-cli-scope must be executable in the checkout")

    def test_a_missing_wrapper_falls_back_loudly_once(self):
        self.be.cli_scope = True
        before = sb.cli_scope_wrapper
        sb.cli_scope_wrapper = lambda: os.path.join(self.d, "no-such-wrapper")
        problems = []
        self.be._log = lambda m, problem=None: problems.append((m, problem))
        try:
            kw1 = self._kw()
            kw2 = self._kw()
        finally:
            sb.cli_scope_wrapper = before
        for kw in (kw1, kw2):
            self.assertEqual(kw["cli_path"], "/bin/true", "the session still starts, on the direct path")
            self.assertNotIn("ROMP_CLI_REAL", kw["env"])
        loud = [(m, p) for m, p in problems if "no-such-wrapper" in m]
        self.assertEqual(len(loud), 1, "reported once per backend, as a problem: %r" % (problems,))
        self.assertTrue(loud[0][1])

    def test_a_non_executable_wrapper_falls_back_too(self):
        self.be.cli_scope = True
        p = os.path.join(self.d, "romp-cli-scope")
        with open(p, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(p, 0o644)
        before = sb.cli_scope_wrapper
        sb.cli_scope_wrapper = lambda: p
        try:
            kw = self._kw()
        finally:
            sb.cli_scope_wrapper = before
        self.assertEqual(kw["cli_path"], "/bin/true")


class FallbackNotice(_Backend):
    """bin/romp-cli-scope writes one stderr line, starting `romp-cli-scope: fallback:`, when it runs
    the CLI directly after a failed pre-flight. The CLI then STARTS, so _record_launch_error never
    drains the stderr tail and the line was never read (2026-09-05): the boot verdict kept saying
    scopes were on while the session's work sat in the service cgroup. _on_cli_stderr now logs that
    line at once, as a problem naming the session; every other line is still only buffered — the
    wrapper's `romp-cli-scope: refused:` line included, since on that path no CLI started and the
    launch-error card reports it from the tail."""

    NOTICE = ("romp-cli-scope: fallback: systemd-run cannot start a transient scope (Failed to connect to bus: "
              "No such file or directory) — running the CLI directly, outside a scope; a service restart will "
              "take its background work down")
    REFUSAL = ("romp-cli-scope: refused: ROMP_CLI_REAL is unset or empty; it must name the real claude CLI, "
               "and this wrapper does not guess one")

    def _capture(self):
        problems = []
        self.be._log = lambda m, problem=None: problems.append((m, problem))
        return problems

    def test_the_notice_is_logged_once_as_a_problem_naming_the_session(self):
        problems = self._capture()
        sess = self._sess()
        sess._on_cli_stderr(self.NOTICE + "\n")
        self.assertEqual(len(problems), 1, problems)
        m, p = problems[0]
        self.assertTrue(p, "a problem line — the error center shows it, not only the log file")
        self.assertIn("web", m, "the session's name")
        self.assertIn(SID[:8], m, "and its sid")
        self.assertIn(self.NOTICE, m, "the wrapper's own reason, verbatim")
        self.assertEqual(sess.stderr_tail(), self.NOTICE, "buffered too, like any other line")

    def test_an_ordinary_line_is_only_buffered(self):
        problems = self._capture()
        sess = self._sess()
        sess._on_cli_stderr("some CLI chatter\n")
        # the prefix mid-line is not the wrapper speaking (a shell naming the wrapper's path, say)
        sess._on_cli_stderr("sh: /x/bin/romp-cli-scope: Permission denied\n")
        self.assertEqual(problems, [], "nothing logged per line — a chatty CLI must not drown the log")
        self.assertEqual(sess.stderr_tail().splitlines(),
                         ["some CLI chatter", "sh: /x/bin/romp-cli-scope: Permission denied"])

    def test_the_refusal_line_is_not_logged_as_a_fallback(self):
        # the wrapper's other line (ROMP_CLI_REAL unset, exit 127): no CLI started, so nothing ran
        # outside a scope, and the launch fails — _record_launch_error reports the line from the
        # stderr tail. Logging it here too reported the one event twice, the first time as a CLI
        # "started outside a scope" when none had started.
        problems = self._capture()
        sess = self._sess()
        sess._on_cli_stderr(self.REFUSAL + "\n")
        self.assertEqual(problems, [], "left to the launch-error path")
        self.assertEqual(sess.stderr_tail(), self.REFUSAL, "buffered: the launch-error card reads it from here")

    def test_the_generic_prefix_alone_is_not_a_fallback(self):
        # only the fallback FORM is logged: a line with the wrapper's prefix and neither second word
        # (a future third message, say) is buffered and nothing more, rather than misreported
        problems = self._capture()
        self._sess()._on_cli_stderr(sb.CLI_SCOPE_NOTICE_PREFIX + " something else entirely\n")
        self.assertEqual(problems, [])

    def test_the_prefixes_are_what_the_wrapper_writes(self):
        # the constants and the script agree: every stderr line the wrapper writes starts with the
        # generic prefix, exactly one in the fallback form and exactly one in the refusal form
        with open(os.path.join(BIN, "romp-cli-scope")) as f:
            src = f.read()
        lines = [ln for ln in src.splitlines() if ">&2" in ln and "echo" in ln]
        self.assertEqual(len(lines), 2, "the refusal and the fallback: %r" % (lines,))
        for ln in lines:
            self.assertIn('"%s ' % sb.CLI_SCOPE_NOTICE_PREFIX, ln, ln)
        self.assertEqual(sum('"%s ' % sb.CLI_SCOPE_FALLBACK_PREFIX in ln for ln in lines), 1, lines)
        self.assertEqual(sum('"%s ' % sb.CLI_SCOPE_REFUSAL_PREFIX in ln for ln in lines), 1, lines)
        # both forms are instances of the generic prefix, so "every line starts with it" still holds,
        # and neither is a prefix of the other
        for p in (sb.CLI_SCOPE_FALLBACK_PREFIX, sb.CLI_SCOPE_REFUSAL_PREFIX):
            self.assertTrue(p.startswith(sb.CLI_SCOPE_NOTICE_PREFIX + " "), p)
        self.assertFalse(sb.CLI_SCOPE_FALLBACK_PREFIX.startswith(sb.CLI_SCOPE_REFUSAL_PREFIX))
        self.assertFalse(sb.CLI_SCOPE_REFUSAL_PREFIX.startswith(sb.CLI_SCOPE_FALLBACK_PREFIX))
        # and the fixtures above are what the script writes, word for word up to the reason
        self.assertTrue(self.NOTICE.startswith(sb.CLI_SCOPE_FALLBACK_PREFIX + " systemd-run cannot start"))
        self.assertIn(self.REFUSAL.split(";")[0], src)


if __name__ == "__main__":
    unittest.main()
