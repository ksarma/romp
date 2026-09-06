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
    is logged the moment it arrives and counted, since on that path the CLI starts and nothing else
    would ever read it; its `refused:` line (ROMP_CLI_REAL unset, exit 127) is only buffered — no
    CLI started, and the launch-error path reports it;
  * the per-session limits (2026-09-06; cli_scope_limits, CLI_SCOPE_LIMITS): the size and
    oom_score_adj rules, agreement with the wrapper's own shell rules on one shared corpus, the
    once-per-backend read, the _options overlay (vetted values down as themselves, refused ones down
    empty, unset ones not sent), the /api-health fields, and the wrapper's third stderr form
    (`ignored:`), logged at arrival and counted apart from the fallbacks;
  * the boot probe (_cli_scope_settle, on a scripted runner): the property probe scope with the
    wrapper's retry chain and the deciding failure quoted, the memory-controller check inside a probe
    scope, the adjustment write in a throwaway child — what each refuses lands in `rejected`, the
    controller verdict rides /api-health as memoryControllerDelegated, and no probe runs with the
    scopes off, without a runner, or for a limit that is not set.
Synthetic fixtures only: placeholder sid, /bin/true as the CLI.
"""
import json
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
for _v in ("ROMP_CLI_SCOPE_MEMORY_MAX", "ROMP_CLI_SCOPE_MEMORY_HIGH", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX",
           "ROMP_CLI_SCOPE_OOM_SCORE_ADJ"):
    os.environ.pop(_v, None)         # and the limits floor (the same reasoning: tool shells inherit them)
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
    line at once, as a problem naming the session, and the backend counts it for /api-health; every
    other line is still only buffered — the wrapper's `romp-cli-scope: refused:` line included, since
    on that path no CLI started and the launch-error card reports it from the tail."""

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
        self.assertEqual(self.be.cli_scope_fallbacks, 1)
        self.assertIsNotNone(self.be.cli_scope_fallback_at)

    def test_an_ordinary_line_is_only_buffered(self):
        problems = self._capture()
        sess = self._sess()
        sess._on_cli_stderr("some CLI chatter\n")
        # the prefix mid-line is not the wrapper speaking (a shell naming the wrapper's path, say)
        sess._on_cli_stderr("sh: /x/bin/romp-cli-scope: Permission denied\n")
        self.assertEqual(problems, [], "nothing logged per line — a chatty CLI must not drown the log")
        self.assertEqual(self.be.cli_scope_fallbacks, 0)
        self.assertIsNone(self.be.cli_scope_fallback_at)
        self.assertEqual(sess.stderr_tail().splitlines(),
                         ["some CLI chatter", "sh: /x/bin/romp-cli-scope: Permission denied"])

    def test_the_refusal_line_is_not_counted_as_a_fallback(self):
        # the wrapper's other line (ROMP_CLI_REAL unset, exit 127): no CLI started, so nothing ran
        # outside a scope, and the launch fails — _record_launch_error reports the line from the
        # stderr tail. Counting and logging it here too reported the one event twice, the first time
        # as a CLI "started outside a scope" when none had started.
        problems = self._capture()
        sess = self._sess()
        sess._on_cli_stderr(self.REFUSAL + "\n")
        self.assertEqual(problems, [], "left to the launch-error path")
        self.assertEqual(self.be.cli_scope_fallbacks, 0)
        self.assertIsNone(self.be.cli_scope_fallback_at)
        self.assertEqual(sess.stderr_tail(), self.REFUSAL, "buffered: the launch-error card reads it from here")
        self.assertEqual(self.be.api_health_snapshot()["cliScope"]["fallbacks"], 0)

    def test_the_generic_prefix_alone_is_not_a_fallback(self):
        # only the fallback FORM counts: a line with the wrapper's prefix and neither second word (a
        # future third message, say) is buffered and nothing more, rather than miscounted
        problems = self._capture()
        self._sess()._on_cli_stderr(sb.CLI_SCOPE_NOTICE_PREFIX + " something else entirely\n")
        self.assertEqual(problems, [])
        self.assertEqual(self.be.cli_scope_fallbacks, 0)

    def test_the_snapshot_reports_the_verdict_and_the_fallbacks(self):
        self.assertEqual(self.be.api_health_snapshot()["cliScope"],
                         {"on": False, "fallbacks": 0, "lastFallbackAt": None, "limitsIgnored": 0, "rejected": [],
                          "memoryControllerDelegated": None,
                          "memoryMax": None, "memoryHigh": None, "memorySwapMax": None, "oomScoreAdj": None},
                         "the test floor: off, nothing fell back, no limits, no probe")
        self._capture()
        sess = self._sess()
        sess._on_cli_stderr(self.NOTICE + "\n")
        sess._on_cli_stderr(self.NOTICE + "\n")
        snap = self.be.api_health_snapshot()["cliScope"]
        self.assertEqual(snap["fallbacks"], 2)
        self.assertIsInstance(snap["lastFallbackAt"], int)
        self.assertGreater(snap["lastFallbackAt"], 0)
        self.be.cli_scope = True
        self.assertTrue(self.be.api_health_snapshot()["cliScope"]["on"])

    def test_the_prefixes_are_what_the_wrapper_writes(self):
        # the constants and the script agree: every stderr line the wrapper writes starts with the
        # generic prefix, exactly one in the fallback form and exactly one in the refusal form
        with open(os.path.join(BIN, "romp-cli-scope")) as f:
            src = f.read()
        lines = [ln for ln in src.splitlines() if ">&2" in ln and "echo" in ln]
        self.assertEqual(len(lines), 3, "the refusal, the fallback and the ignored form: %r" % (lines,))
        for ln in lines:
            self.assertIn('"%s ' % sb.CLI_SCOPE_NOTICE_PREFIX, ln, ln)
        self.assertEqual(sum('"%s ' % sb.CLI_SCOPE_FALLBACK_PREFIX in ln for ln in lines), 1, lines)
        self.assertEqual(sum('"%s ' % sb.CLI_SCOPE_REFUSAL_PREFIX in ln for ln in lines), 1, lines)
        self.assertEqual(sum('"%s ' % sb.CLI_SCOPE_IGNORED_PREFIX in ln for ln in lines), 1, lines)
        # all three forms are instances of the generic prefix, so "every line starts with it" still
        # holds, and none is a prefix of another
        forms = (sb.CLI_SCOPE_FALLBACK_PREFIX, sb.CLI_SCOPE_REFUSAL_PREFIX, sb.CLI_SCOPE_IGNORED_PREFIX)
        for p in forms:
            self.assertTrue(p.startswith(sb.CLI_SCOPE_NOTICE_PREFIX + " "), p)
            for q in forms:
                if p != q:
                    self.assertFalse(p.startswith(q), (p, q))
        # and the fixtures above are what the script writes, word for word up to the reason
        self.assertTrue(self.NOTICE.startswith(sb.CLI_SCOPE_FALLBACK_PREFIX + " systemd-run cannot start"))
        self.assertIn(self.REFUSAL.split(";")[0], src)


# ---- the per-session limits (2026-09-06) ----

# One corpus for both rule-holders: the kernel's regexes (cli_scope_limits) and the wrapper's shell
# functions (size_ok, adj_ok) must give the same verdict on every value, or a value the kernel accepts
# and hands down is refused at launch (or the reverse: never reported at boot, refused per launch).
SIZE_OK = ["16G", "8192M", "1024", "0", "1T", "5K", "infinity", "016M", "12345678901234567890"]
SIZE_BAD = ["16g", "abc", "16 G", "16GB", "1.5G", "-1", "G", "50%", "Infinity", "16GG", " 16G", "16G\n",
            "1_000", "infinity ", "K16", "0x10", "\u0663M", "\uff11\uff10M"]   # other scripts' digits: not [0-9]
ADJ_OK = ["500", "-1000", "0", "1000", "-1", "-0", "999"]
ADJ_BAD = ["1001", "-1001", "+5", "5x", "--5", "-", "1e3", "5 ", "10000", "-10000", "abc", "5\n", "1 000",
           "0100", "-0100", "01000", "00", "\uff15\uff10\uff10"]   # leading zeros (octal to Linux); other digits
LIMIT_VARS = ("ROMP_CLI_SCOPE_MEMORY_MAX", "ROMP_CLI_SCOPE_MEMORY_HIGH", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX",
              "ROMP_CLI_SCOPE_OOM_SCORE_ADJ")
IGNORED = ("romp-cli-scope: ignored: ROMP_CLI_SCOPE_MEMORY_MAX is not a size (digits with an optional K, M, G or T "
           "suffix, or infinity) — the CLI runs in its scope without it")


def _wrapper_verdicts(fn, values):
    """Run the wrapper's own `fn` (size_ok / adj_ok), lifted verbatim out of bin/romp-cli-scope, over
    `values` under sh: a list of True/False. The script execs, so it cannot be sourced; the function
    bodies are cut from `\nNAME() {` to the first line that is exactly `}`."""
    with open(os.path.join(BIN, "romp-cli-scope")) as f:
        src = f.read()

    def body(name):
        i = src.index("\n%s() {" % name)
        j = src.index("\n}\n", i)
        return src[i:j + 3]
    script = (body("size_ok") + body("adj_ok")
              + '\nfor v in "$@"; do if %s "$v"; then echo ok; else echo bad; fi; done\n' % fn)
    r = subprocess.run(["sh", "-s", "--"] + list(values), input=script, capture_output=True, text=True, timeout=30)
    out = r.stdout.split("\n")[:-1]
    assert r.returncode == 0 and len(out) == len(values), (r.returncode, r.stderr, out)
    return [o == "ok" for o in out]


class LimitRules(unittest.TestCase):
    """cli_scope_limits: the size and adjustment rules, what is in force and what is refused, the log."""

    def _log(self):
        rows = []
        return rows, (lambda m, problem=False: rows.append((m, bool(problem))))

    def test_nothing_set_is_nothing(self):
        rows, log = self._log()
        self.assertEqual(sb.cli_scope_limits({}, log=log), ({}, {}, None))
        self.assertEqual(sb.cli_scope_limits({v: "" for v in LIMIT_VARS}, log=log), ({}, {}, None),
                         "empty is unset — what the kernel sends down for a refused one")
        self.assertEqual(rows, [])

    def test_every_valid_size_is_in_force_under_its_api_key(self):
        for v in SIZE_OK:
            env = {"ROMP_CLI_SCOPE_MEMORY_MAX": v, "ROMP_CLI_SCOPE_MEMORY_HIGH": v, "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX": v}
            in_force, rejected, delegated = sb.cli_scope_limits(env)
            self.assertEqual(in_force, {"memoryMax": v, "memoryHigh": v, "memorySwapMax": v}, v)
            self.assertIsNone(delegated, "no runner, no probe")
            self.assertEqual(rejected, {}, v)

    def test_every_bad_size_is_refused_and_logged_as_a_problem_naming_the_variable_and_the_rule(self):
        for v in SIZE_BAD:
            rows, log = self._log()
            in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_HIGH": v}, log=log)
            self.assertEqual(in_force, {}, v)
            self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_HIGH": v}, v)
            self.assertEqual(len(rows), 1, (v, rows))
            m, problem = rows[0]
            self.assertTrue(problem, v)
            self.assertIn("ROMP_CLI_SCOPE_MEMORY_HIGH", m)
            self.assertIn("not a size", m)
            self.assertIn("K, M, G or T", m, "the rule, so the fix is in the line")
            self.assertIn("without that limit", m, "and what happens meanwhile")

    def test_the_adjustment_rule(self):
        for v in ADJ_OK:
            in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v})
            self.assertEqual((in_force, rejected), ({"oomScoreAdj": v}, {}), v)
        for v in ADJ_BAD:
            rows, log = self._log()
            in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v}, log=log)
            self.assertEqual((in_force, rejected), ({}, {"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v}), v)
            self.assertIn("-1000..1000", rows[0][0], v)
            self.assertIn("no leading zero", rows[0][0], v)

    def test_a_refused_value_leaves_the_others_in_force(self):
        rows, log = self._log()
        in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "abc", "ROMP_CLI_SCOPE_MEMORY_HIGH": "12G",
                                                     "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "500"}, log=log)
        self.assertEqual(in_force, {"memoryHigh": "12G", "oomScoreAdj": "500"})
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"})
        self.assertEqual([p for _m, p in rows], [True, False], "one problem, then the in-force line")
        self.assertIn("in force", rows[1][0])
        self.assertIn("memoryHigh=12G", rows[1][0])
        self.assertIn("oomScoreAdj=500", rows[1][0])

    def test_with_the_scopes_off_the_in_force_line_says_the_limits_apply_to_nothing(self):
        rows, log = self._log()
        in_force, _, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "16G"}, log=log, scope_on=False)
        self.assertEqual(in_force, {"memoryMax": "16G"}, "still read, for the report")
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0][1], "not a problem: a setting, idle")
        self.assertIn("apply to nothing", rows[0][0])
        self.assertIn("scopes are off", rows[0][0])

    def test_no_log_callback_is_fine(self):
        self.assertEqual(sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"})[1], {"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"})

    def test_the_table_names_the_four_variables_once_each(self):
        self.assertEqual(tuple(row[0] for row in sb.CLI_SCOPE_LIMITS), LIMIT_VARS)
        self.assertEqual(len({row[1] for row in sb.CLI_SCOPE_LIMITS}), 4, "distinct api keys")

    def test_the_wrapper_agrees_with_the_kernel_on_every_size(self):
        values = SIZE_OK + SIZE_BAD
        expected = [sb._cli_scope_size_ok(v) for v in values]
        self.assertEqual(expected, [True] * len(SIZE_OK) + [False] * len(SIZE_BAD), "the corpus is what it claims")
        got = _wrapper_verdicts("size_ok", values)
        self.assertEqual(dict(zip(values, got)), dict(zip(values, expected)))

    def test_the_wrapper_agrees_with_the_kernel_on_every_adjustment(self):
        values = ADJ_OK + ADJ_BAD
        expected = [sb._cli_scope_adj_ok(v) for v in values]
        self.assertEqual(expected, [True] * len(ADJ_OK) + [False] * len(ADJ_BAD), "the corpus is what it claims")
        got = _wrapper_verdicts("adj_ok", values)
        self.assertEqual(dict(zip(values, got)), dict(zip(values, expected)))


class LimitsOnTheBackend(_Backend):
    """Read once at construction from the manager's environment; handed down by _options; reported by
    api_health_snapshot; the wrapper's `ignored:` line logged at arrival and counted."""

    def _construct(self, **env):
        saved = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            return sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logged.append)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_the_default_backend_has_no_limits(self):
        self.assertEqual(self.be.cli_scope_limits, {})
        self.assertEqual(self.be.cli_scope_rejected, {})
        self.assertEqual(self.be.cli_scope_ignored, 0)
        self.assertIsNone(self.be.cli_scope_memory_delegated, "no memory limit set, so no probe, so no verdict")

    def test_the_limits_are_read_once_at_construction(self):
        be = self._construct(ROMP_CLI_SCOPE_MEMORY_MAX="16G", ROMP_CLI_SCOPE_MEMORY_HIGH="", ROMP_CLI_SCOPE_OOM_SCORE_ADJ="500")
        self.assertEqual(be.cli_scope_limits, {"memoryMax": "16G", "oomScoreAdj": "500"})
        self.assertEqual(be.cli_scope_rejected, {})
        # the test floor keeps the scope off, so the boot line says the limits are idle
        self.assertTrue(any("apply to nothing" in m for m in self.logged), self.logged)
        # the environment changed after construction: the backend's view does not
        before = os.environ.get("ROMP_CLI_SCOPE_MEMORY_MAX")
        os.environ["ROMP_CLI_SCOPE_MEMORY_MAX"] = "1G"
        try:
            self.assertEqual(be.cli_scope_limits["memoryMax"], "16G")
        finally:
            if before is None:
                os.environ.pop("ROMP_CLI_SCOPE_MEMORY_MAX", None)
            else:
                os.environ["ROMP_CLI_SCOPE_MEMORY_MAX"] = before

    def test_a_refused_value_is_recorded_and_the_rest_stand(self):
        be = self._construct(ROMP_CLI_SCOPE_MEMORY_MAX="lots", ROMP_CLI_SCOPE_MEMORY_SWAP_MAX="0")
        self.assertEqual(be.cli_scope_limits, {"memorySwapMax": "0"})
        self.assertEqual(be.cli_scope_rejected, {"ROMP_CLI_SCOPE_MEMORY_MAX": "lots"})
        self.assertTrue(any("ROMP_CLI_SCOPE_MEMORY_MAX" in m and "not a size" in m for m in self.logged), self.logged)

    def test_options_hands_down_the_set_and_the_refused_variables_and_not_the_unset_ones(self):
        # a vetted value as itself; a refused one EMPTY (it masks the manager environment's bad value,
        # which the SDK's spawn would otherwise inherit); an unset one not at all — there is nothing to
        # mask, and a review found all four names set-empty in every session's tool shell (2026-09-06),
        # where an install with nothing configured must look exactly as it did before the limits existed
        self.be.cli_scope = True
        self.be.cli_scope_limits = {"memoryMax": "16G", "oomScoreAdj": "500"}
        self.be.cli_scope_rejected = {"ROMP_CLI_SCOPE_MEMORY_HIGH": "abc"}
        env = self._kw()["env"]
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_MAX"], "16G")
        self.assertEqual(env["ROMP_CLI_SCOPE_OOM_SCORE_ADJ"], "500")
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_HIGH"], "", "refused: down empty, so the wrapper reads it as unset")
        self.assertNotIn("ROMP_CLI_SCOPE_MEMORY_SWAP_MAX", env, "unset: not sent")
        self.assertEqual(env["ROMP_CLI_REAL"], "/bin/true", "the rest of the overlay is unchanged")

    def test_options_sends_none_of_the_four_when_none_is_set(self):
        # the unset path is what an install with nothing configured runs: identical to the overlay
        # before the limits existed
        self.be.cli_scope = True
        self.assertEqual((self.be.cli_scope_limits, self.be.cli_scope_rejected), ({}, {}))
        env = self._kw()["env"]
        for v in LIMIT_VARS:
            self.assertNotIn(v, env, v)
        self.assertEqual(set(env), {"ROMP_SID", "ROMP_SESSION_NAME", "ROMP_CLI_REAL"} | ({"PATH"} if "PATH" in env else set()),
                         "the overlay carries the identity, the real CLI, and nothing about limits")

    def test_a_value_the_box_refused_goes_down_empty_like_one_the_rule_refused(self):
        # rejected by the boot probe (systemd or the oom_score_adj floor): the manager environment still
        # holds the value, and the wrapper must not try it again on every launch
        self.be.cli_scope = True
        self.be.cli_scope_limits = {"memoryHigh": "12G"}
        self.be.cli_scope_rejected = {"ROMP_CLI_SCOPE_MEMORY_MAX": "16G", "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "0"}
        env = self._kw()["env"]
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_HIGH"], "12G")
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_MAX"], "")
        self.assertEqual(env["ROMP_CLI_SCOPE_OOM_SCORE_ADJ"], "")
        self.assertNotIn("ROMP_CLI_SCOPE_MEMORY_SWAP_MAX", env)

    def test_options_sends_nothing_when_off_or_when_the_wrapper_is_missing(self):
        self.be.cli_scope_limits = {"memoryMax": "16G"}
        self.be.cli_scope = False
        for v in LIMIT_VARS:
            self.assertNotIn(v, self._kw()["env"], v)
        self.be.cli_scope = True
        before = sb.cli_scope_wrapper
        sb.cli_scope_wrapper = lambda: os.path.join(self.d, "no-such-wrapper")
        self.be._log = lambda m, problem=None: None
        try:
            env = self._kw()["env"]
        finally:
            sb.cli_scope_wrapper = before
        for v in LIMIT_VARS:
            self.assertNotIn(v, env, "no wrapper, no scope, nothing for a limit to apply to")

    def test_the_snapshot_reports_the_values_in_force_and_the_refused_names(self):
        self.be.cli_scope_limits = {"memoryMax": "16G", "memoryHigh": "12G", "oomScoreAdj": "500"}
        self.be.cli_scope_rejected = {"ROMP_CLI_SCOPE_MEMORY_SWAP_MAX": "some"}
        self.be.cli_scope = True
        snap = self.be.api_health_snapshot()["cliScope"]
        self.assertEqual(snap["memoryMax"], "16G")
        self.assertEqual(snap["memoryHigh"], "12G")
        self.assertIsNone(snap["memorySwapMax"], "refused: not in force")
        self.assertEqual(snap["oomScoreAdj"], 500, "an integer, as JSON should carry it")
        self.assertEqual(snap["rejected"], ["ROMP_CLI_SCOPE_MEMORY_SWAP_MAX"])
        self.assertEqual(snap["limitsIgnored"], 0)
        self.assertIsNone(snap["memoryControllerDelegated"], "not settled (no probe ran on this backend)")
        json.dumps(snap)
        # the boot probe's verdict on the memory controller rides as it was settled, either way
        for verdict in (True, False):
            self.be.cli_scope_memory_delegated = verdict
            snap = self.be.api_health_snapshot()["cliScope"]
            self.assertIs(snap["memoryControllerDelegated"], verdict)
            self.assertEqual(snap["memoryMax"], "16G", "set and held by systemd: still reported; the flag says whether it applies")
            json.dumps(snap)
        # scopes off: nothing is in force, however the variables read; the refusal still shows
        self.be.cli_scope = False
        snap = self.be.api_health_snapshot()["cliScope"]
        for key in ("memoryMax", "memoryHigh", "memorySwapMax", "oomScoreAdj", "memoryControllerDelegated"):
            self.assertIsNone(snap[key], key)
        self.assertEqual(snap["rejected"], ["ROMP_CLI_SCOPE_MEMORY_SWAP_MAX"])

    def test_the_ignored_line_is_logged_at_once_and_counted_apart_from_the_fallbacks(self):
        problems = []
        self.be._log = lambda m, problem=None: problems.append((m, problem))
        sess = self._sess()
        sess._on_cli_stderr(IGNORED + "\n")
        self.assertEqual(len(problems), 1, problems)
        m, p = problems[0]
        self.assertTrue(p, "a problem line: the CLI starts, so nothing else would ever read it")
        self.assertIn("web", m)
        self.assertIn(SID[:8], m)
        self.assertIn("without a per-session limit", m)
        self.assertIn(IGNORED, m, "the wrapper's own line, verbatim")
        self.assertEqual(sess.stderr_tail(), IGNORED, "buffered too")
        self.assertEqual(self.be.cli_scope_ignored, 1)
        self.assertEqual(self.be.cli_scope_fallbacks, 0, "not a fallback: the scope is there")
        self.assertIsNone(self.be.cli_scope_fallback_at)
        snap = self.be.api_health_snapshot()["cliScope"]
        self.assertEqual((snap["limitsIgnored"], snap["fallbacks"]), (1, 0))

    def test_the_fixture_is_what_the_wrapper_writes(self):
        with open(os.path.join(BIN, "romp-cli-scope")) as f:
            src = f.read()
        self.assertTrue(IGNORED.startswith(sb.CLI_SCOPE_IGNORED_PREFIX + " ROMP_CLI_SCOPE_MEMORY_MAX is not a size"))
        self.assertIn('"romp-cli-scope: ignored: $1 — the CLI runs in its scope without it"', src)
        self.assertIn('is not a size (digits with an optional K, M, G or T suffix, or infinity)', src)

    def test_the_backend_settles_the_limits_against_this_box_when_the_scopes_are_on(self):
        # the wiring end to end: the verdict on, two values set, and subprocess.run answering as a box
        # whose systemd takes the properties, whose user manager lacks the memory controller, and whose
        # oom_score_adj floor is above the value asked for. The scripted runner stands in for
        # subprocess.run for the constructor only, and answers only the probe argvs.
        real_run = subprocess.run
        runs = _Runs((0, b""),                                             # the property probe scope
                     (1, b""),                                             # no memory.max in its cgroup
                     (1, b"sh: 1: cannot create /proc/self/oom_score_adj: Permission denied\n"),
                     passthrough=real_run)
        saved = sb.cli_scope_supported
        sb.cli_scope_supported = lambda **kw: True
        real_before = os.environ.pop("ROMP_CLI_REAL", None)
        env = {"ROMP_CLI_SCOPE_MEMORY_MAX": "16G", "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "0"}
        os.environ.update(env)
        sb.subprocess.run = runs
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logged.append)
        finally:
            sb.subprocess.run = real_run
            sb.cli_scope_supported = saved
            for k in env:
                os.environ.pop(k, None)
            os.environ.pop("ROMP_CLI_REAL", None)
            if real_before is not None:
                os.environ["ROMP_CLI_REAL"] = real_before
        self.assertEqual([c[0] for c in runs.calls], ["systemd-run", "systemd-run", "sh"], runs.calls)
        self.assertTrue(be.cli_scope)
        self.assertEqual(be.cli_scope_limits, {"memoryMax": "16G"})
        self.assertEqual(be.cli_scope_rejected, {"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "0"})
        self.assertIs(be.cli_scope_memory_delegated, False)
        problems = [m for m in self.logged if m.startswith("cli scope:") and ("not delegated" in m or "cannot be written" in m)]
        self.assertEqual(len(problems), 2, self.logged)
        snap = be.api_health_snapshot()["cliScope"]
        self.assertEqual((snap["memoryMax"], snap["oomScoreAdj"], snap["rejected"], snap["memoryControllerDelegated"]),
                         ("16G", None, ["ROMP_CLI_SCOPE_OOM_SCORE_ADJ"], False))
        # and _options hands the refused adjustment down empty, the size as itself, the unset two not at all
        sess = sb.SdkSession(be, {"sid": SID, "name": "web", "cwd": self.d, "mode": "acceptEdits"})
        env = be._options(sess, dict)["env"]
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_MAX"], "16G")
        self.assertEqual(env["ROMP_CLI_SCOPE_OOM_SCORE_ADJ"], "")
        self.assertNotIn("ROMP_CLI_SCOPE_MEMORY_HIGH", env)
        self.assertNotIn("ROMP_CLI_SCOPE_MEMORY_SWAP_MAX", env)

    def test_with_the_scopes_off_the_backend_runs_no_probe_however_the_limits_read(self):
        real_run = subprocess.run
        runs = _Runs(passthrough=real_run)
        sb.subprocess.run = runs
        try:
            be = self._construct(ROMP_CLI_SCOPE_MEMORY_MAX="16G", ROMP_CLI_SCOPE_OOM_SCORE_ADJ="0")
        finally:
            sb.subprocess.run = real_run
        self.assertFalse(be.cli_scope, "the test floor")
        self.assertEqual([c for c in runs.calls if c[0] in ("systemd-run", "sh")], [], "nothing probed")
        self.assertEqual(be.cli_scope_limits, {"memoryMax": "16G", "oomScoreAdj": "0"}, "read, for the report")
        self.assertIsNone(be.cli_scope_memory_delegated)


class _Runs:
    """A scripted stand-in for subprocess.run: `script` items are (returncode, stderr bytes) or an
    exception to raise, consumed one per call; a call past the script's end passes (0, b""). Records
    every (argv, kwargs). With `passthrough`, argvs that are not a probe's (systemd-run, sh) go to it."""

    def __init__(self, *script, passthrough=None):
        self.script, self.calls, self.kws, self.passthrough = list(script), [], [], passthrough

    def __call__(self, argv, **kw):
        argv = list(argv)
        if self.passthrough is not None and argv[0] not in ("systemd-run", "sh"):
            return self.passthrough(argv, **kw)
        self.calls.append(argv)
        self.kws.append(kw)
        item = self.script.pop(0) if self.script else (0, b"")
        if isinstance(item, BaseException):
            raise item
        rc, err = item
        return subprocess.CompletedProcess(argv, rc, stdout=b"", stderr=err)


PROPS = ["-p", "MemoryMax=16G", "-p", "MemorySwapMax=0", "-p", "OOMPolicy=continue"]
PROPS_PROBE = PROBE[:-2] + PROPS + ["--", "true"]
DELEGATION_PROBE = PROBE[:-2] + PROPS + ["--", "sh", "-c", 'test -e "/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.max"']
ADJ_PROBE = ["sh", "-c", 'echo "$1" > /proc/self/oom_score_adj', "sh", "500"]
BOTH = {"ROMP_CLI_SCOPE_MEMORY_MAX": "16G", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX": "0", "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "500"}


class LimitsSettledAtBoot(unittest.TestCase):
    """cli_scope_limits with a runner: the wrapper's own steps run once at the kernel's start, against
    this box, so a value the syntax passes but the box refuses (OOMPolicy= on scopes before systemd 253;
    an adjustment below the inherited oom_score_adj floor) lands in `rejected` once instead of being
    refused on every launch — one `ignored:` line and one problem each — while the boot log and
    /api-health called it in force. A user manager without the memory controller, which takes the
    properties and applies nothing, is caught inside a probe scope and reported."""

    def _log(self):
        rows = []
        return rows, (lambda m, problem=False: rows.append((m, bool(problem))))

    def test_a_box_that_takes_everything_probes_three_times_and_refuses_nothing(self):
        rows, log = self._log()
        runs = _Runs()
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, DELEGATION_PROBE, ADJ_PROBE])
        self.assertEqual(in_force, {"memoryMax": "16G", "memorySwapMax": "0", "oomScoreAdj": "500"})
        self.assertEqual(rejected, {})
        self.assertIs(delegated, True)
        self.assertEqual([p for _m, p in rows], [False], "one line, the in-force one, no problem")
        self.assertIn("in force", rows[0][0])
        for kw in runs.kws:
            self.assertEqual(kw.get("timeout"), sb.CLI_SCOPE_PROBE_TIMEOUT, "every probe is bounded")
            self.assertEqual(kw.get("stdout"), subprocess.DEVNULL)
            self.assertEqual(kw.get("stderr"), subprocess.PIPE)

    def test_the_property_words_are_the_wrappers_own(self):
        # the probe must start the scope a session would get: run the real wrapper under a fake
        # systemd-run that records its argv and compare the `-p` words of its pre-flight
        d = tempfile.mkdtemp()
        fake = os.path.join(d, "systemd-run")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\nprintf "%s\\n" "$@" > "$FAKE_LOG"\nexit 0\n')
        os.chmod(fake, 0o755)
        env = dict(os.environ, PATH=d + ":" + os.environ.get("PATH", ""), FAKE_LOG=os.path.join(d, "argv"),
                   ROMP_CLI_REAL="/bin/true", ROMP_SID=SID, ROMP_CLI_SCOPE_MEMORY_MAX="16G",
                   ROMP_CLI_SCOPE_MEMORY_HIGH="12G", ROMP_CLI_SCOPE_MEMORY_SWAP_MAX="0")
        env.pop("ROMP_CLI_SCOPE", None)
        env.pop("ROMP_CLI_SCOPE_OOM_SCORE_ADJ", None)
        r = subprocess.run([os.path.join(BIN, "romp-cli-scope")], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(d, "argv")) as f:
            argv = f.read().split("\n")[:-1]
        words = argv[argv.index("-p"):argv.index("--")]
        self.assertEqual(words, sb._cli_scope_props({"memoryMax": "16G", "memoryHigh": "12G", "memorySwapMax": "0"}))
        self.assertEqual(sb._cli_scope_props({"memorySwapMax": "0", "oomScoreAdj": "500"}),
                         ["-p", "MemorySwapMax=0", "-p", "OOMPolicy=continue"], "the adjustment is no property")
        self.assertEqual(sb._cli_scope_props({"oomScoreAdj": "500"}), [])

    def test_properties_systemd_rejects_twice_land_in_rejected_quoting_the_deciding_failure(self):
        # the wrapper's chain: with the properties (fails), bare (passes), with them again (fails) — the
        # SECOND failure decides and is quoted; the first may have been a passing fault, as here
        rows, log = self._log()
        runs = _Runs((1, b"Failed to connect to bus: Connection timed out\n"),
                     (0, b""),
                     (1, b"Failed to start transient scope unit: Unknown assignment: OOMPolicy=continue\nmore\n"))
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, PROBE, PROPS_PROBE, ADJ_PROBE], "no controller check for a rejected scope")
        self.assertEqual(in_force, {"oomScoreAdj": "500"}, "the adjustment stands: it is no systemd property")
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_MAX": "16G", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX": "0"})
        self.assertIsNone(delegated)
        self.assertEqual([p for _m, p in rows], [True, False])
        m = rows[0][0]
        self.assertIn("rejected the per-session memory limits", m)
        self.assertIn("-p MemoryMax=16G -p MemorySwapMax=0 -p OOMPolicy=continue", m, "the words it refused")
        self.assertIn("Unknown assignment", m, "the deciding failure")
        self.assertNotIn("Connection timed out", m, "not the first, which passed on retry")
        self.assertNotIn("more", m.split("Unknown assignment")[1][:40], "systemd-run's first stderr line only")
        self.assertIn("systemd 253", m, "the likely cause, so the fix is in the line")
        self.assertIn("in force — oomScoreAdj=500", rows[1][0])

    def test_a_rejection_that_does_not_name_oompolicy_gets_no_systemd_253_hint(self):
        # a size the rule passes and systemd refuses (out of range): the line quotes systemd and adds
        # nothing about scope OOMPolicy= support, which is not the cause
        rows, log = self._log()
        runs = _Runs((1, b"Failed to parse MemoryMax=99999999999999999999T: Numerical result out of range\n"),
                     (0, b""),
                     (1, b"Failed to parse MemoryMax=99999999999999999999T: Numerical result out of range\n"))
        _in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "99999999999999999999T"}, log=log, run=runs)
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_MAX": "99999999999999999999T"})
        self.assertIn("Numerical result out of range", rows[0][0])
        self.assertNotIn("253", rows[0][0])

    def test_a_passing_fault_on_the_first_try_costs_nothing(self):
        rows, log = self._log()
        runs = _Runs((1, b"Failed to connect to bus: Connection timed out\n"), (0, b""), (0, b""), (0, b""), (0, b""))
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, PROBE, PROPS_PROBE, DELEGATION_PROBE, ADJ_PROBE])
        self.assertEqual(rejected, {})
        self.assertEqual(len(in_force), 3)
        self.assertIs(delegated, True)
        self.assertEqual([p for _m, p in rows], [False])

    def test_a_probe_that_raises_is_a_failed_try(self):
        rows, log = self._log()
        runs = _Runs(subprocess.TimeoutExpired(PROPS_PROBE, 10), (0, b""),
                     (1, b"Failed to start transient scope unit: Unknown assignment: OOMPolicy=continue\n"))
        in_force, rejected, _ = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, PROBE, PROPS_PROBE, ADJ_PROBE])
        self.assertEqual(sorted(rejected), ["ROMP_CLI_SCOPE_MEMORY_MAX", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX"])
        self.assertIn("Unknown assignment", rows[0][0])

    def test_a_bare_scope_failing_too_settles_nothing_and_says_so_without_a_problem(self):
        # the bus went away between the scope verdict and here: the wrapper reports per launch (its
        # fallback line, a problem each), so this is one plain line and the values stand as read
        rows, log = self._log()
        runs = _Runs((1, b"Failed to connect to bus: No such file or directory\n"),
                     (1, b"Failed to connect to bus: No such file or directory\n"))
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, PROBE, ADJ_PROBE])
        self.assertEqual(rejected, {})
        self.assertEqual(len(in_force), 3)
        self.assertIsNone(delegated)
        self.assertEqual([p for _m, p in rows], [False, False])
        self.assertIn("could not be settled", rows[0][0])
        self.assertIn("No such file or directory", rows[0][0])
        self.assertIn("in force", rows[1][0])

    def test_a_user_manager_without_the_memory_controller_is_a_problem_and_a_false_verdict(self):
        # systemd took the properties (the first probe passed), and the probe scope's cgroup has no
        # memory.max: the values stay set (systemd holds them; /api-health shows them with the flag),
        # the in-force line says they apply to nothing, and the problem line names the check to run
        rows, log = self._log()
        runs = _Runs((0, b""), (1, b""), (0, b""))
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, DELEGATION_PROBE, ADJ_PROBE])
        self.assertEqual(rejected, {})
        self.assertEqual(len(in_force), 3)
        self.assertIs(delegated, False)
        self.assertEqual([p for _m, p in rows], [True, False])
        self.assertIn("memory controller is not delegated", rows[0][0])
        self.assertIn("applies nothing", rows[0][0])
        self.assertIn("DelegateControllers", rows[0][0])
        self.assertIn("apply to nothing until the memory controller is delegated", rows[1][0])
        self.assertNotIn("in force", rows[1][0])

    def test_a_controller_check_that_cannot_run_leaves_the_verdict_unsettled(self):
        rows, log = self._log()
        runs = _Runs((0, b""), OSError("boom"), (0, b""))
        _in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(rejected, {})
        self.assertIsNone(delegated)
        self.assertEqual([p for _m, p in rows], [False, False])
        self.assertIn("could not run", rows[0][0])
        self.assertIn("boom", rows[0][0])

    def test_an_adjustment_below_the_floor_lands_in_rejected_and_the_memory_limits_stand(self):
        rows, log = self._log()
        runs = _Runs((0, b""), (0, b""), (1, b"sh: 1: cannot create /proc/self/oom_score_adj: Permission denied\n"))
        in_force, rejected, delegated = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(runs.calls, [PROPS_PROBE, DELEGATION_PROBE, ADJ_PROBE])
        self.assertEqual(in_force, {"memoryMax": "16G", "memorySwapMax": "0"})
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "500"})
        self.assertIs(delegated, True)
        self.assertEqual([p for _m, p in rows], [True, False])
        m = rows[0][0]
        self.assertIn("ROMP_CLI_SCOPE_OOM_SCORE_ADJ=500", m)
        self.assertIn("user manager's own oom_score_adj", m, "the floor, named")
        self.assertIn("privilege", m)
        self.assertIn("without it", m)
        self.assertIn("in force — memoryMax=16G memorySwapMax=0", rows[1][0])

    def test_an_adjustment_check_that_cannot_run_leaves_the_value_standing(self):
        rows, log = self._log()
        runs = _Runs((0, b""), (0, b""), OSError("no sh"))
        in_force, rejected, _ = sb.cli_scope_limits(BOTH, log=log, run=runs)
        self.assertEqual(rejected, {})
        self.assertEqual(in_force["oomScoreAdj"], "500")
        self.assertEqual([p for _m, p in rows], [False, False])
        self.assertIn("oom_score_adj check could not run", rows[0][0])
        self.assertIn("no sh", rows[0][0])

    def test_the_adjustment_alone_probes_only_the_write(self):
        rows, log = self._log()
        runs = _Runs()
        in_force, rejected, delegated = sb.cli_scope_limits({"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "500"}, log=log, run=runs)
        self.assertEqual(runs.calls, [ADJ_PROBE], "no scope is started for a limit that is no property")
        self.assertEqual((in_force, rejected, delegated), ({"oomScoreAdj": "500"}, {}, None))

    def test_a_memory_limit_alone_probes_no_write(self):
        runs = _Runs()
        in_force, rejected, delegated = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_HIGH": "12G"}, run=runs)
        self.assertEqual(runs.calls, [PROBE[:-2] + ["-p", "MemoryHigh=12G", "-p", "OOMPolicy=continue", "--", "true"],
                                      PROBE[:-2] + ["-p", "MemoryHigh=12G", "-p", "OOMPolicy=continue", "--"] + sb.CLI_SCOPE_MEMORY_PROBE_CMD])
        self.assertEqual((in_force, rejected, delegated), ({"memoryHigh": "12G"}, {}, True))

    def test_no_probe_without_a_runner_with_the_scopes_off_or_with_nothing_set(self):
        runs = _Runs()
        self.assertEqual(sb.cli_scope_limits(BOTH)[2], None)
        self.assertEqual(sb.cli_scope_limits(BOTH, run=runs, scope_on=False)[2], None)
        self.assertEqual(sb.cli_scope_limits({}, run=runs)[2], None)
        self.assertEqual(sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"}, run=runs), ({}, {"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"}, None),
                         "a value its rule refused never reaches a probe")
        self.assertEqual(runs.calls, [])

    def test_a_rule_refusal_and_a_box_refusal_share_rejected(self):
        rows, log = self._log()
        runs = _Runs((0, b""), (0, b""), (1, b"Permission denied\n"))
        in_force, rejected, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "16G", "ROMP_CLI_SCOPE_MEMORY_HIGH": "lots",
                                                     "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "0"}, log=log, run=runs)
        self.assertEqual(in_force, {"memoryMax": "16G"})
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_HIGH": "lots", "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "0"})
        self.assertEqual([p for _m, p in rows], [True, True, False], "two problems, then the in-force line last")
        self.assertIn("in force", rows[2][0])

    def test_the_probe_commands_are_what_the_docs_and_the_wrapper_describe(self):
        # the controller check reads the cgroup v2 path the docs tell a user to read by hand, and the
        # adjustment write is the wrapper's own (`echo` into /proc/self/oom_score_adj), in a child
        self.assertEqual(sb.CLI_SCOPE_MEMORY_PROBE_CMD[:2], ["sh", "-c"])
        self.assertIn('/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)/memory.max', sb.CLI_SCOPE_MEMORY_PROBE_CMD[2])
        self.assertEqual(sb.CLI_SCOPE_ADJ_PROBE_CMD, ["sh", "-c", 'echo "$1" > /proc/self/oom_score_adj', "sh"])
        with open(os.path.join(BIN, "romp-cli-scope")) as f:
            src = f.read()
        self.assertIn('echo "$adj" > /proc/self/oom_score_adj', src)
        # and the write really is refused below the floor / accepted at it, on this box — the child
        # keeps its own /proc/self, so this process's value is untouched either way
        if os.path.exists("/proc/self/oom_score_adj") and os.getuid() != 0:
            with open("/proc/self/oom_score_adj") as f:
                cur = int(f.read().strip())
            if cur > -1000:
                rc, _err = sb._cli_scope_probe(subprocess.run, sb.CLI_SCOPE_ADJ_PROBE_CMD + ["-1000"])
                self.assertEqual(rc, 1, "below every floor: refused")
            rc, err = sb._cli_scope_probe(subprocess.run, sb.CLI_SCOPE_ADJ_PROBE_CMD + [str(cur)])
            self.assertEqual((rc, err), (0, ""), "the inherited value itself is always writable")
            with open("/proc/self/oom_score_adj") as f:
                self.assertEqual(int(f.read().strip()), cur)


if __name__ == "__main__":
    unittest.main()
