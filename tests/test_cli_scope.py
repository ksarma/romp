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
    once-per-backend read, the _options overlay (vetted values down explicitly, refused ones down
    empty), the /api-health fields, and the wrapper's third stderr form (`ignored:`), logged at
    arrival and counted apart from the fallbacks.
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
                          "memoryMax": None, "memoryHigh": None, "memorySwapMax": None, "oomScoreAdj": None},
                         "the test floor: off, nothing fell back, no limits")
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
        self.assertEqual(sb.cli_scope_limits({}, log=log), ({}, {}))
        self.assertEqual(sb.cli_scope_limits({v: "" for v in LIMIT_VARS}, log=log), ({}, {}),
                         "empty is unset — what the kernel sends down for a refused one")
        self.assertEqual(rows, [])

    def test_every_valid_size_is_in_force_under_its_api_key(self):
        for v in SIZE_OK:
            env = {"ROMP_CLI_SCOPE_MEMORY_MAX": v, "ROMP_CLI_SCOPE_MEMORY_HIGH": v, "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX": v}
            in_force, rejected = sb.cli_scope_limits(env)
            self.assertEqual(in_force, {"memoryMax": v, "memoryHigh": v, "memorySwapMax": v}, v)
            self.assertEqual(rejected, {}, v)

    def test_every_bad_size_is_refused_and_logged_as_a_problem_naming_the_variable_and_the_rule(self):
        for v in SIZE_BAD:
            rows, log = self._log()
            in_force, rejected = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_HIGH": v}, log=log)
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
            in_force, rejected = sb.cli_scope_limits({"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v})
            self.assertEqual((in_force, rejected), ({"oomScoreAdj": v}, {}), v)
        for v in ADJ_BAD:
            rows, log = self._log()
            in_force, rejected = sb.cli_scope_limits({"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v}, log=log)
            self.assertEqual((in_force, rejected), ({}, {"ROMP_CLI_SCOPE_OOM_SCORE_ADJ": v}), v)
            self.assertIn("-1000..1000", rows[0][0], v)
            self.assertIn("no leading zero", rows[0][0], v)

    def test_a_refused_value_leaves_the_others_in_force(self):
        rows, log = self._log()
        in_force, rejected = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "abc", "ROMP_CLI_SCOPE_MEMORY_HIGH": "12G",
                                                  "ROMP_CLI_SCOPE_OOM_SCORE_ADJ": "500"}, log=log)
        self.assertEqual(in_force, {"memoryHigh": "12G", "oomScoreAdj": "500"})
        self.assertEqual(rejected, {"ROMP_CLI_SCOPE_MEMORY_MAX": "abc"})
        self.assertEqual([p for _m, p in rows], [True, False], "one problem, then the in-force line")
        self.assertIn("in force", rows[1][0])
        self.assertIn("memoryHigh=12G", rows[1][0])
        self.assertIn("oomScoreAdj=500", rows[1][0])

    def test_with_the_scopes_off_the_in_force_line_says_the_limits_apply_to_nothing(self):
        rows, log = self._log()
        in_force, _ = sb.cli_scope_limits({"ROMP_CLI_SCOPE_MEMORY_MAX": "16G"}, log=log, scope_on=False)
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

    def test_options_hands_every_variable_down_explicitly_when_on(self):
        self.be.cli_scope = True
        self.be.cli_scope_limits = {"memoryMax": "16G", "oomScoreAdj": "500"}
        self.be.cli_scope_rejected = {"ROMP_CLI_SCOPE_MEMORY_HIGH": "abc"}
        env = self._kw()["env"]
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_MAX"], "16G")
        self.assertEqual(env["ROMP_CLI_SCOPE_OOM_SCORE_ADJ"], "500")
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_HIGH"], "", "refused: down empty, so the wrapper reads it as unset")
        self.assertEqual(env["ROMP_CLI_SCOPE_MEMORY_SWAP_MAX"], "", "unset: down empty too")
        self.assertEqual(env["ROMP_CLI_REAL"], "/bin/true", "the rest of the overlay is unchanged")

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
        json.dumps(snap)
        # scopes off: nothing is in force, however the variables read; the refusal still shows
        self.be.cli_scope = False
        snap = self.be.api_health_snapshot()["cliScope"]
        for key in ("memoryMax", "memoryHigh", "memorySwapMax", "oomScoreAdj"):
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


if __name__ == "__main__":
    unittest.main()
