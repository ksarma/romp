"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import atexit
import collections
import importlib.util
import os
import re
import shutil
import sys
import tempfile

import pytest
from _pytest._code.code import ReprExceptionInfo, ReprFileLocation, ReprTracebackNative

# Temp-directory hygiene, the child-process half (2026-09-06): every temp path a run creates lives
# under ONE private `romp-tests-*` root, removed when the run ends. The root, the redirect of
# tempfile.tempdir and TMPDIR into it and the owner marker the kernel's sweep reads are the tests
# PACKAGE's (tests/__init__.py, whose comments have the leak's history and the marker's): the
# package imports before this file under pytest and before the module under `python -m unittest
# tests.test_x`, so a bare run has the same root as a pytest run (until 2026-09-14 this file minted
# it, and a bare run had no root, no redirect and no marker). This file keeps the pytest side: the
# removal at run end with a survivor named, below. Imported, not looked up with a default: a conftest
# running without the package has no root to remove and should say so (tests/test_env_value_redaction.py's
# child runs load a COPY of this file from a scratch dir, with the checkout on PYTHONPATH for this line).
# This module's own XDG floor below and every module-level mkdtemp at collection land inside the root
# because the package redirected before either ran.
# The two removals compose without overlap: pytest_sessionfinish runs the hook's sweep, whose scope
# is gettempdir() and so the inside of the root; pytest_unconfigure then removes the root whole
# (whatever the sweep could not see), the package's romp-tests-state-* dir included, which sits
# inside it. Under pytest-xdist both hooks run in the controller and in every worker: each imported
# the package and this file and so owns a root of its own (a worker's sits inside the controller's,
# since it inherits that TMPDIR; the package records the system temp dir the run was handed with a
# setdefault, so a worker keeps the controller's record — ROMP_TESTS_SYSTEM_TMPDIR — rather than
# naming the controller's root, one level too deep for a socket path under a long TMPDIR).
# The atexit registrations (the package's and this file's) are silent fallbacks for a normal exit
# that skipped the hooks, each a no-op on what the other removed; nothing runs after an os._exit
# (pytest-timeout's thread method ends a hung run that way), so a hang leaves ONE top-level entry
# in the system temp dir, the root with its marker, for the kernel's sweep.
import tests as _tests  # noqa: E402  the package; its import is what minted the root this file removes
_TMP_ROOT = _tests.TMP_ROOT
TEST_ROOT_OWNER_MARKER = _tests.TEST_ROOT_OWNER_MARKER   # tests/test_test_root_sweep.py pins it against the kernel's


def _remove_run_dirs(report=False):
    """Remove the root (the package state dir is inside it). A survivor is named on stderr when asked:
    rmtree with ignore_errors swallows a child still writing under the root or a 000-mode directory a
    test left behind, and the run would otherwise end green with the root standing. Only unconfigure
    asks; the atexit fallback stays silent so it neither repeats the notice nor contradicts it."""
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)
    if report and os.path.isdir(_TMP_ROOT):
        print("[tests] not removed at run end: %s" % _TMP_ROOT, file=sys.stderr)


atexit.register(_remove_run_dirs)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """The in-process half (tests/__init__.py): remove every directory this process made through
    tempfile.mkdtemp inside the root, this module's state root included, when the session ends. Runs
    in the controller and in every xdist worker, since each is its own pytest session, and last, after
    pytest's own runner sessionfinish has performed the deferred teardown an interrupted run leaves
    behind, so nothing is swept from under a fixture still closing. The package's atexit hook does the
    same at interpreter exit; both are idempotent, and pytest_unconfigure below takes the root itself
    afterwards."""
    try:
        from tests import remove_made_dirs
    except Exception:
        return
    remove_made_dirs()


def pytest_unconfigure(config):
    _remove_run_dirs(report=True)


def pytest_configure(config):
    """One warning filter, registered here so every run and every xdist worker carries it (2026-09-16):
    claude_agent_sdk.types.CanUseToolShadowedWarning, a UserWarning subclass the SDK emits when a client is
    built with can_use_tool set beside a permission mode or an allowed_tools entry that auto-approves a tool
    before the callback is consulted. tests/test_host_transport.py and tests/test_session_host.py put romp's
    SDK venv on sys.path and drive that path; under pytest-xdist the worker ships the warning to the
    controller, whose venv has no claude_agent_sdk, and xdist's unserialize_warning_message imports the
    warning's module to rebuild it: ModuleNotFoundError, the node goes down, the run ends in INTERNALERROR
    (before this every -n run needed -p no:warnings). Matched on the MESSAGE PREFIX with the base category,
    never on the class: pytest parses each filterwarnings entry every time it applies them (configure,
    collection, each test), and an entry naming a class it cannot import is dropped with a
    PytestConfigWarning, which is every worker until the emitting module inserts the venv path, the
    controller always and CI always. A module-level warnings.filterwarnings in the emitting module does not
    hold either: pytest wraps collection and each test in catch_warnings, which restores the filter list on
    exit. addinivalue_line appends to the ini list, so an ini file added later merges with this line. Both
    of the SDK's message forms ("...: permission_mode ..." and "... for: <tools>") start with the prefix."""
    config.addinivalue_line("filterwarnings", "ignore:can_use_tool will not be invoked:UserWarning")


# No test's git reads the developer's configuration (2026-09-06). Fixture repos are built by `git
# init` + `git commit` in temp dirs, and those commands honoured the developer's global config: a
# global core.hooksPath ran their pre-commit hook on every seed commit, an LFS filter would run on
# every checkout, and a credential helper or insteadOf rewrite could reach a real remote
# (tests/test_file_github.py pins its own environment for exactly that reason). CI has no global git
# config, so a test that leans on one is already broken there; this makes every run match.
# GIT_CONFIG_GLOBAL is honoured by git >= 2.32; the identity is synthetic, and it is set rather than
# defaulted so a developer's own GIT_AUTHOR_* cannot leak into fixture commits either. The env
# identity outranks `git config user.*` and `-c user.*`, so a test that must pin a particular author
# exports its own GIT_AUTHOR_* / GIT_COMMITTER_* per call; other config keys still yield to `-c`.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_AUTHOR_NAME"] = os.environ["GIT_COMMITTER_NAME"] = "romp tests"
os.environ["GIT_AUTHOR_EMAIL"] = os.environ["GIT_COMMITTER_EMAIL"] = "tests@example.invalid"

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")   # inside the root; the hook records it
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel exports this to its sessions; it outranks the XDG floor
# the postal bus port likewise (2026-09-11): a machine whose bus runs on a named port hands ROMP_POSTAL_PORT to every
# session's shell, and a test run from one would carry the machine's name into every lab and in-process kernel; the
# bus refuses its fixed port under a test unless the port is the run's own, which the marker beside a port says
os.environ.pop("ROMP_POSTAL_PORT", None)
os.environ["ROMP_POSTAL_HERMETIC"] = "1"
os.environ["ROMP_CKPT_FIRST_DOC_KB"] = "0"   # the young-session floor is off for the suite's small fixtures (a document under 1 MB of
#                                                pre-cut bytes is never written live); the floor's own test sets it. A plain assignment: an
#                                                exported value in the shell (64, say) would red every checkpoint fixture (1721 round two);
#                                                tests/__init__.py carries the same line for the unittest runner
# No test spawns a per-session HOST by omission (2026-09-11, T348): hosts are on by default now, so a backend built over
# a state dir with no `session-hosts` file starts a real bin/romp-session-host for any session it connects. The root the
# runner floors carries the toggle set to off from the start, re-asserted per test below (a test that deletes or rewrites
# it gets it back); the deliberate hosts-on tests write `on` into their OWN state roots and are unaffected.
# THE BELT'S REACH: it covers this one root and nothing else. A test that mints its own temp state root (a bare
# tempfile.mkdtemp() handed to SdkBackend, a lab kernel's xdg root) stands outside it and MUST write `off` into
# `<its root>/session-hosts` itself unless it means to run a host, or the first connect it drives spawns a real
# bin/romp-session-host on the developer's box (tests/test_cut_turn_tree_kill.py did, 2026-09-11). The rule for test
# authors is in CLAUDE.md under Testing.
_SESSION_HOSTS_OFF = os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts")


def _floor_session_hosts_off():
    try:
        os.makedirs(os.path.dirname(_SESSION_HOSTS_OFF), exist_ok=True)
        if not os.path.exists(_SESSION_HOSTS_OFF) or open(_SESSION_HOSTS_OFF).read().strip().lower() != "off":
            with open(_SESSION_HOSTS_OFF, "w") as f:
                f.write("off\n")
    except OSError:
        pass


_floor_session_hosts_off()

# No test may resolve the REAL ~/.claude (2026-09-08): the judge module and the event model compute
# their projects root at IMPORT from CLAUDE_CONFIG_DIR (default ~/.claude), the kernel and the SDK
# backend read the same variable at call time for the task store and transcripts, and a test that
# touched a per-session project dir without patching jd.PROJECTS wrote thirty synthetic-sid
# directories under a developer's real ~/.claude/projects. Floored like the state root: a fresh
# directory inside the run's private temp root, set (not defaulted: a developer's own export must
# not reach a test either) before any test module loads, and re-asserted per test below so a
# module-level pop or write in one test file cannot erase it for the run. A test that needs its own
# Claude root sets the variable in setUp, after the fixture, exactly as the ones that do already do.
# The location the run was handed is saved FIRST, before the floor replaces it: the one opt-in live
# test that borrows the operator's apiKeyHelper command from their own settings
# (tests/test_session_move_live.py) reads it through ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR. Captured
# after the floor it would name the run's empty temp dir, and that test would skip as "no auth"
# while its skip message still named the borrow. setdefault, so an xdist worker keeps the
# controller's value rather than re-reading an environment the controller has already floored.
os.environ.setdefault("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
                      os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))
_CLAUDE_CONFIG = tempfile.mkdtemp(prefix="romp-tests-claude-")
os.environ["CLAUDE_CONFIG_DIR"] = _CLAUDE_CONFIG


# No test may reach a REAL manager control port (2026-08-27): on a machine running a live romp,
# every shell the manager tree spawns inherits ROMP_MANAGER_PORT, and any test kernel that dials
# "the manager" through the inherited value restarts the ACTUAL deployment — the serve-layer
# restart test's pop-then-restore raced the /restart handler's post-ack env read and took a
# self-hosted instance down mid-suite, repeatedly. POISONED to a dead port, never popped. Every
# consumer in kernel/ treats an absent or empty variable as "no manager" since 2026-09-10
# (_manager_port: _manager_kernels, _run_main_update, _restart_this_kernel and _run_update; before that
# _run_main_update, and for one review round the banner's registry read, mapped absent to the DEFAULT
# port, the live one, and a probe run with the variable absent restarted every session on a development
# box through the drift door); bin/romp-manager still falls back to 7432 on absent or empty (its status,
# down, restart-all and ensure verbs, which `romp down` and the remote update script dial through), and
# vscode-extension/src/extension.ts defaults to 7432 too, one more reason the floor stays: a dead value
# is the one state safe against every consumer, present and future. Import-time, so collection-time code
# is floored too.
os.environ["ROMP_MANAGER_PORT"] = "1"
# The kernel's port, both spellings, for the same reason: kernel/kernel.py resolves PORT from
# ROMP_KERNEL_PORT at import and postal/postal_service.py builds KERNEL_BASE from it at import, bin/romp
# reads it in every kernel subcommand and hooks/romp-wake.sh at every wake, and bin/romp-manager reads
# ROMP_SERVE_PORT first; each maps an absent variable to the DEFAULT port, the live kernel's, so a test
# that dials "the kernel" through an inherited or absent value reaches the developer's own. A test that
# starts a kernel of its own passes the port it picked, as the ones that do already do.
os.environ["ROMP_KERNEL_PORT"] = "1"
os.environ["ROMP_SERVE_PORT"] = "1"

# No test may read the REAL service.env (2026-09-04; the reason changed on 2026-09-08): the kernel's boot
# check (kernel/credentials.py) reads the manager env file for retired provider lines, so on a machine whose
# file still carries one every kernel-loading test would refuse to start. Pointed at a path inside the temp
# state root that is never created, so every read is the "no file" case. Both spellings, because the
# path resolver accepts both. Import-time (collection is floored too) plus a per-test re-assert below, on
# the same reasoning as the manager port.
_NO_SERVICE_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_SERVICE_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_SERVICE_ENV
# No test starts with a CREDENTIAL the developer's shell configured (2026-09-08). Every session shell under
# a romp-managed manager inherits the manager's environment: the retired provider names (which the boot
# check now refuses outright), ROMP_EXPECTED_AUTH (the box-wide auth declaration), the login tokens
# sdk_backend.startup_auth_env claims, and the 1Password CLI's own names. A test that constructs a backend
# or asks default_auth would otherwise read the DEVELOPER'S configuration: 73 tests across eight modules
# went red on a box running a key command while CI, which exports none of these, stayed green (the
# manager's full run, 2026-09-08). Popped at import so module-level loads see the clean baseline, and
# re-asserted per test below; a test that wants a credential sets a synthetic one itself in setUp, which
# runs after the fixture. The list is the code's own (tests/test_key_source_floor.py pins it against
# credentials.FLOOR_ENV_NAMES / FLOOR_ENV_PREFIXES and sdk_backend.AUTH_ENV_NAMES).
KEY_SOURCE_ENV_NAMES = (
    "ROMP_API_KEY_CMD", "ROMP_API_KEY_REF", "ANTHROPIC_API_KEY",          # credentials.RETIRED_VARS
    "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",                     # credentials.LOGIN_TOKEN_VARS
    "ROMP_EXPECTED_AUTH",                                                  # the auth declaration
    "OP_SERVICE_ACCOUNT_TOKEN", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN", "OP_ACCOUNT",   # credentials.OP_ENV_NAMES
)
KEY_SOURCE_ENV_PREFIXES = ("OP_SESSION_",)                                # credentials.OP_ENV_PREFIX


def _scrub_key_source_env():
    for name in KEY_SOURCE_ENV_NAMES:
        os.environ.pop(name, None)
    for name in [k for k in os.environ if k.startswith(KEY_SOURCE_ENV_PREFIXES)]:
        os.environ.pop(name, None)


_scrub_key_source_env()
# Every shell under a romp-managed session inherits ROMP_SUPERVISED=1 from the kernel (the service
# unit exports it). The variable used to give the retired key-source module authority over a startup key;
# it is still popped so a test's world is the unsupervised baseline (review find, 2026-09-05), and a test
# that wants supervision sets the variable itself.
os.environ.pop("ROMP_SUPERVISED", None)


# No test may read the box's REAL managed settings (2026-09-08): credentials.py reads
# /etc/claude-code/managed-settings.json (or the macOS path) as the top of Claude Code's precedence, so a
# test asserting "no helper" would lie on a box whose administrator set one there. Every loaded copy of the
# module is pointed at a path inside the temp state root that is never created; a test that wants a managed
# file stubs managed_settings_path itself in setUp, after this fixture.
_NO_MANAGED_SETTINGS = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-managed-settings.json")


def _reset_credential_state():
    """credentials.py memoizes the helper's value in process memory for its TTL; under one pytest process
    that memo would leak between test modules. Every loaded copy of the module is reset, and its managed
    settings path floored (above)."""
    import sys
    for name, m in list(sys.modules.items()):
        if "credentials" in name and hasattr(m, "forget_helper_key"):
            m.forget_helper_key()
            m.managed_settings_path = lambda: _NO_MANAGED_SETTINGS


@pytest.fixture(autouse=True)
def _no_real_service_env():
    """Re-asserted, not defaulted: a module-level write in one test file executes during collection
    and would otherwise hold for the whole run. A test that needs its own env file points the vars at
    a temp path in setUp, which runs AFTER this fixture (pytest fills fixtures in the item's setup
    phase, before TestCase.run calls setUp) — so per-test intent still wins."""
    for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
        os.environ[var] = _NO_SERVICE_ENV
    _scrub_key_source_env()
    os.environ.pop("ROMP_SUPERVISED", None)
    _reset_credential_state()
    yield


@pytest.fixture(autouse=True)
def _no_real_claude_config():
    os.environ["CLAUDE_CONFIG_DIR"] = _CLAUDE_CONFIG
    yield


@pytest.fixture(autouse=True)
def _hosts_off_in_the_floored_root():
    """The floored state root reads hosts OFF before every test (T348): the file is re-written when a test removed or
    changed it, so no later test spawns a real host by omission."""
    _floor_session_hosts_off()
    yield


@pytest.fixture(autouse=True)
def _dead_manager_port():
    """The import-time poison above covers collection, but a module-level env write in a test file
    ALSO executes during collection — so one module's write (or pop) would otherwise hold for the
    entire run phase, erasing the floor for every test after it. Re-assert per test: no
    module-level write can outlive collection against this. The kernel's port, both spellings, is
    re-asserted the same way; a test that needs a port of its own sets it in setUp or passes it
    to the process it starts."""
    os.environ["ROMP_MANAGER_PORT"] = "1"
    os.environ["ROMP_KERNEL_PORT"] = "1"
    os.environ["ROMP_SERVE_PORT"] = "1"
    yield


# No test may reach the REAL `claude` CLI (2026-08-12): _judge_claude_bin honors ROMP_CLAUDE_BIN
# first, so this floors every judge call a test forgot to stub at /bin/false — empty stdout, the
# dead-CLI row, byte-for-byte what a claude-less CI runner produces. Found when an unstubbed
# _judge_run in the kernel suite exec'd the live CLI on a dev machine: run alone it made a real
# (billed!) model call and passed; in the full suite the process env's key had already been claimed
# by an sdk-backend construction, the live CLI refused "Not logged in", and the judge-auth latch
# that refusal now correctly feeds floored the synthetic session's cards — 25 stays-in-Working
# tests red locally, green on CI, purely machine-dependent. Tests that assert _judge_claude_bin's
# own resolution pop this var themselves (test_judge.py), as they always had to.
os.environ["ROMP_CLAUDE_BIN"] = "/bin/false"

# No test kernel may fetch the Models API (2026-09-02): the kernel's lazy _sdk() build (_sdk_locked)
# fires the T222 catalog refresh, `_refresh_model_catalog("boot")` — an async GET to
# api.anthropic.com on the credential the kernel resolves: the apiKeyHelper Claude Code's settings
# name (kernel/credentials.py helper_key, run in-process), else a claimed ANTHROPIC_AUTH_TOKEN
# bearer. A DEFENSIVE floor: no test reached the network before this line (checked, not assumed —
# the one in-process _sdk() driver, test_kernel_headless_ops' SdkSingleFlight, runs the refresh
# inside the test process with the module loader mocked, and it stopped only because the mocked
# module handed http.client a credential it rejects before a socket opens), but any
# in-process _sdk() call is one exported key away from a real request no test asserts on, on a key
# the test never chose. The kernel-SPAWNING tests floor it in their subprocess env
# (test_gear_select_matrix_served, test_ship_reship_served, test_awaiting_box_sync_served); this floors every test,
# whatever the developer's shell exports.
# Set, not setdefault: "off" is the only value the switch recognises, so no outer intent is being
# overridden. The catalog suite unsets the var inside its own tests — FetchAndFallback pops it in
# setUp to drive the fetch against a local fake server; StalenessEvent and ModelsRoute set it in
# setUp and pop it in tearDown — leaving it absent for every test after that module in a serial
# run; hence the per-test re-assert below, on the same reasoning as the manager-port one
# (tests/test_model_catalog_floor.py pins both). Those pops still win inside their own tests:
# pytest fills every fixture, autouse included, in the item's setup phase, before runtest hands
# the case to TestCase.run(), which is what calls setUp.
os.environ["ROMP_MODEL_CATALOG"] = "off"


@pytest.fixture(autouse=True)
def _no_model_catalog_fetch():
    os.environ["ROMP_MODEL_CATALOG"] = "off"
    yield


# No test may reach the REAL `systemd-run` (2026-09-05): constructing the SDK backend decides once
# whether to spawn CLIs inside per-session transient scopes (sdk_backend.cli_scope_supported), and
# that verdict defaults to ON under the supervised service — ROMP_SUPERVISED=1 is inherited by every
# tool shell of a session running on a self-hosted romp, so a suite run from one would probe the
# live user manager at every backend construction and route every _options() through the wrapper.
# Floored to the explicit off value; the truth-table tests pass their own environ and are unaffected.
# Per-test re-assert below, on the same reasoning as the manager-port floor. The per-session limits
# (ROMP_CLI_SCOPE_MEMORY_MAX and the others, sdk_backend.CLI_SCOPE_LIMITS) are floored to unset the same
# way: the kernel hands them to every session's CLI, whose tool shells inherit them, so a suite run from a
# session on a self-hosted romp with limits in service.env would see them at every backend construction
# and in every exact argv pin.
os.environ["ROMP_CLI_SCOPE"] = "0"
_CLI_SCOPE_LIMIT_VARS = ("ROMP_CLI_SCOPE_MEMORY_MAX", "ROMP_CLI_SCOPE_MEMORY_HIGH", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX",
                         "ROMP_CLI_SCOPE_OOM_SCORE_ADJ",
                         # the kernel's marker for a systemd that refuses OOMPolicy= on a scope: sent to every
                         # session's CLI ("1" or ""), so a tool shell inherits it like the limits
                         "ROMP_CLI_SCOPE_OOM_POLICY_REJECTED")
for _v in _CLI_SCOPE_LIMIT_VARS:
    os.environ.pop(_v, None)


@pytest.fixture(autouse=True)
def _no_cli_scope():
    os.environ["ROMP_CLI_SCOPE"] = "0"
    for v in _CLI_SCOPE_LIMIT_VARS:
        os.environ.pop(v, None)
    # The CLI-binary floor above, re-asserted per test for the same reason as the scope's: a test module's module-level
    # write executes at COLLECTION and would hold for every test after it. tests/test_login_flow.py once set its mock CLI
    # that way, so every lab kernel of a whole run (kernel_env passes ROMP_CLAUDE_BIN through) ran its judges against a
    # login mock, which answered the planner with junk; the coerce floor minted goals, the auto-nudge fired into sessions
    # no CLI could run, and the nudge walk read those parked nudges as the user's queued input for the rest of both
    # boots (tests/test_fold_checkpoints_served.py, one red only under a whole suite, 2026-09-16). A module that needs
    # its own binary sets it in setUp and restores it in tearDown (tests/test_kernel_env_floor.py pins both halves).
    os.environ["ROMP_CLAUDE_BIN"] = "/bin/false"
    yield


@pytest.fixture(autouse=True)
def _stub_place_llm(monkeypatch):
    """Card-first placer floor (2026-07-08): every loaded romp-judge instance gets a no-op place_llm so
    no test can reach a real `claude -p` subprocess through _card_route_subs (a plan test whose mocked
    sub lands on a card with open sub-goals would otherwise fire the real second call). Placer tests
    override jd.place_llm in-body; monkeypatch restores whatever was there after each test."""
    seen = set()
    for m in list(sys.modules.values()):
        for j in (m, getattr(m, "jd", None)):
            if j is not None and id(j) not in seen and getattr(j, "_card_route_subs", None) is not None:
                seen.add(id(j))
                monkeypatch.setattr(j, "place_llm", lambda *a, **k: "")
    yield


# No test may leave the shared judge or a call-time environment seam changed (2026-09-09). kernel.py
# loads the judge as load_source("romp_judge", ...) (kernel/loadsource.py), which re-executes
# into the module object already in sys.modules under that name, so every kernel-loading test
# module's km.jd is ONE process-wide object. A test that rebinds jd.STATE to a temp dir and removes
# that dir in tearDown without restoring the prior value leaves every later STATE reader in the
# process pointing at a removed directory: a FileNotFoundError on restart-audit.jsonl or
# timeline-views.json, or a silent empty read where the writer swallows OSError. The postal
# sessions-file seam has the same shape: postal_service reads ROMP_SESSIONS_FILE from os.environ at
# call time, so a tearDown that pops it instead of restoring the prior value leaves a later module,
# which set the seam once at import, resolving no local sessions. Neither shows when the victim runs
# alone, and the serial order of the whole suite passes only because a test that loads a kernel
# between the cause and the victim re-executes judge.py and rebinds the roots; any other order (a
# subset, another scheduler) fails a module that did nothing wrong. This fixture names the cause
# instead: it snapshots the shared judge's STATE and PROJECTS and the watched environment names
# before each test and fails the test that changed one and did not restore it, or left a path that
# was a directory pointing at nothing. Transition-based on purpose: a module-level preamble runs at
# collection, before any snapshot, and is not seen; a test that changes and restores is quiet; and a
# test that merely runs under another test's leftover is not blamed for it. A test that loads a
# kernel (or the judge itself) re-executes judge.py into the shared module, which rebinds every root
# from the environment as it stands at that moment: that is the loader's reset, made from values
# other modules' import-time writes decide, not a directory the test made and removed, so the path
# check compares no values for that test (the re-execution recreates every function object, which is
# how it is told apart from an assignment). Only the values: judge.py creates STATE at import, so a
# STATE that is not a directory after a reload is the test's own doing and is still named, and the
# environment names are still checked. Values of the environment names are never printed (one of
# them is a credential), only the kind of change.
_SHARED_JUDGE_PATHS = ("STATE", "PROJECTS")
_SEAM_ENV_NAMES = ("ROMP_SESSIONS_FILE", "ROMP_SERVE_TOKEN")


def _shared_judge_paths():
    """({name: (path text or None, is a directory)}, marker) for the shared judge's watched globals,
    the marker being a function object judge.py defines (a re-execution replaces it); ({}, None) when
    no module has loaded the judge under its shared name yet."""
    jd = sys.modules.get("romp_judge")
    if jd is None:
        return {}, None
    out = {}
    for name in _SHARED_JUDGE_PATHS:
        p = getattr(jd, name, None)
        text = None if p is None else str(p)
        out[name] = (text, text is not None and os.path.isdir(text))
    return out, vars(jd).get("_rebind_state")


@pytest.fixture(autouse=True)
def _shared_state_restored(request):
    paths_before, marker_before = _shared_judge_paths()
    env_before = {name: os.environ.get(name) for name in _SEAM_ENV_NAMES}
    yield
    paths_after, marker_after = _shared_judge_paths()
    left = []
    if marker_after is marker_before:      # not re-executed: whatever differs, this test assigned
        for name, (text0, isdir0) in paths_before.items():
            text1, isdir1 = paths_after.get(name, (None, False))
            if text1 != text0:
                left.append("romp_judge.%s changed from %s to %s" % (name, text0, text1))
            elif isdir0 and not isdir1:
                left.append("romp_judge.%s %s was a directory and is gone" % (name, text0))
    else:                                  # re-executed: the loader bound the roots, and created STATE
        text1, isdir1 = paths_after.get("STATE", (None, False))
        if text1 is not None and not isdir1:
            left.append("romp_judge.STATE %s is not a directory after the test reloaded the judge" % text1)
    for name in _SEAM_ENV_NAMES:
        v0, v1 = env_before[name], os.environ.get(name)
        if v0 == v1:
            continue
        if v1 is None:
            left.append("%s was set and is now unset" % name)
        elif v0 is None:
            left.append("%s was unset and is now set" % name)
        else:
            left.append("%s was changed" % name)
    if left:
        pytest.fail("%s left shared state changed after its teardown: %s. Save the prior value before "
                    "changing it and put it back at the end of the test; for a path, before removing the "
                    "directory it named." % (request.node.nodeid, "; ".join(left)), pytrace=False)


def restore_env(name, prior):
    """Put the environment name back the way a test found it: `prior` is the os.environ.get(name) taken before
    the test changed it, None meaning unset. A tearDown that pops the name instead leaves a later module in the
    process without the value its own import set; this is the restore the fixture above expects."""
    if prior is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = prior


# No test may leave the kernel's backend singleton changed, or over a directory that is gone, and the test
# that did it is the one named (2026-09-19). kernel.py builds its SdkBackend lazily: the first km._sdk() call
# constructs it over jd.STATE as it stands at that moment and caches it in km._sdk_backend for the life of
# the process (_sdk_locked), and every later reader in the worker (the chat signature's fork component, the
# registry readers, the restart routes) takes that one object. A test that points jd.STATE at a sandbox and
# reaches km._sdk(), through a card build or a route, builds the singleton over its sandbox; a tearDown that
# restores jd.STATE and removes the sandbox without touching the singleton leaves every later test's backend
# over a removed directory. Its fork_children then stats a registry that is gone, answers {} on the OSError
# and scans no registry, so a derivation counting registry stats read 0 against 39 in a module that did
# nothing wrong (tests/test_kernel_delta_send.py after tests/test_kernel.py::ViewBuilder, 2026-09-19); the
# module alone passes, and a kernel load between cause and victim hides it, since re-executing kernel.py
# resets the singleton.
#
# THE POPULATION, measured at this branch's base (2026-09-19): six classes in five modules leaked the
# singleton. ViewBuilder (tests/test_kernel.py), CostWeighting (tests/test_token_usage.py),
# BuildSessionDiffRows (tests/test_kernel_patch_rows.py), FeedWarmResolveBumpsTheLedgerRevision
# (tests/test_ledger_anchors.py), and SharedViewInBuilds and PushSurvivesOneFailedChatBuild
# (tests/test_kernel_goal_cache_wiring.py), each fixed in a commit of its own on this branch with one shape
# (ViewBuilder's before this fixture; the other four after it, one per module, found by the review round
# that ran the modules alone): save km._sdk_backend beside the saved jd.STATE and put it back where jd.STATE
# is restored, before the directory goes. The count comes from running every module ALONE with this fixture
# on, over a population that is a union, every set saved beside the list with the script that derives it:
# the 237 modules a census plugin (a scratch pytest plugin over two full -n 4 runs) saw take a road to a
# root change (a jd.STATE assignment, a jd._rebind_state call, a singleton construction, or a singleton that
# changed), the 94 that load the kernel under its shared name, the 272 whose text assigns jd.STATE or calls
# _rebind_state in process (the private-kernel modules among them included: the private name isolates the
# kernel's globals and not jd's, so they move the shared jd.STATE, and their own singletons are outside this
# fixture by the stated limit below), and the 316 the first sweep ran; 364 modules in all. The first sweep,
# over its 316 at the base, found these 4 modules red and 1 unrelated pre-existing red
# (tests/test_sdk_rate_limit_usage.py: an unrestored ROMP_SERVE_TOKEN setdefault that
# _shared_state_restored's environment check names, identical with this fixture off and byte-identical at
# the base); at this head every one of the 364 is green alone except that one. The full-suite census saw
# none of the five: an earlier first builder in every worker made their builds cache hits. A green suite run
# is therefore no evidence a module is clean; the module-alone sweep is the measurement, and the review
# round that found the four ran the modules that way.
# THE ROAD EACH FIGURE WAS TAKEN ON, since the two families came from opposite roads. Every module-alone
# figure above (the 316-module first sweep, the 364-module sweep and "every one of the 364 is green alone",
# and the per-module triage counts behind them) was taken module alone, on the missing road, which is CI's:
# the test venv's interpreter has no claude_agent_sdk, and a module run alone does not import
# tests/test_host_transport.py; that module is the one exception in the union, since it puts the venv on
# sys.path itself. Every full-run figure above (the two full -n 4 census runs and their 237-module set, and
# "the full-suite census saw none of the five") was taken on the SDK-importable road: when claude_agent_sdk
# is not importable, tests/test_host_transport.py puts the box's SDK venv on sys.path at import, and every
# xdist worker imports every collected module, so a full run here takes that road; CI never does (its install
# has no SDK), and the green CI run at the round-3 head is the missing-road full-suite datum. The figures in
# this fixture's own tests (tests/test_sdk_singleton_ratchet.py) carry no inherited road: each scratch head
# forces its road.
#
# THE TRANSITION MODEL. The fixtures below read the singleton at fixed moments and judge what changed
# between two reads, never the after value on its own: an absolute read of the after value (the first form
# of this fixture) failed every test that merely INHERITED a singleton over a removed directory, each with
# a false accusation and a remedy it could not act on, and buried the one cause under the tests that
# followed it in the worker (one cause and 193 inheritors on the first full run). Three windows:
#   * the test: a function-scoped autouse fixture reads before the test and after its own teardown
#     (unittest's tearDown runs inside the call phase, and the test's requested fixtures tear down before
#     this one, so their restores are seen) and fails the test whose own transition made the bad state;
#   * the class and module boundaries: a class-scoped and a module-scoped autouse fixture read at the
#     scope's start (before setUpClass or setUpModule) and at its end (after tearDownClass or
#     tearDownModule; pytest reports a failure there as an ERROR at the scope's last test) and fail the
#     scope whose setup or teardown made the bad state, naming the boundary;
#   * the setup before a test: a singleton found over a gone directory that no verdict has named yet was
#     made by something that escaped every window (import-time code, or a leak from before the fixture
#     was armed) and is reported ONCE per worker, at the first test that meets it, worded as inherited,
#     with no remedy addressed to that test; every later test that inherits the same object is quiet.
#     The report is computed at the setup and raised after the test's own teardown, beside its own verdict
#     if it has one, so the test runs and its own transition is still judged (the first form failed the
#     setup, and one test per worker lost its run whenever a leak escaped every window). The same report,
#     at the worker's FIRST test window only, covers a real backend over a directory that stands but is not
#     jd.STATE AS THE MODULE BOUNDARY'S START READ RECORDED IT, and only when that backend IS the object that read
#     found (_SDK_MODULE_START, compared by identity, never by state_dir or class). The premise holds at that
#     START READ, not at the window: when the module boundary reads, only import-time code and any fixture of a
#     scope wider than the function has run (pytest collects every module before the first test runs; a session-
#     or package-scoped fixture sets up before the module boundary's start read, and setUpModule, setUpClass and
#     a module- or class-scoped fixture after it, the order a scratch run showed), so the identity term and the
#     start read's reference make the window's report a statement about that read: a singleton the start read
#     saw over a root other than the jd.STATE it recorded is import-time code's or such a fixture's build over a
#     root that is not the run's, or its move of jd.STATE after the build, left in place (the wording names both
#     causes and both shapes), while one the start read did NOT see was installed by the module's or a class's
#     own setup and is left unnamed here, so the boundary that brackets the install judges it, names the scope
#     and prints the sandbox remedy; and a jd.STATE the window finds moved from the start read's is a scope
#     setup's move for its tests (K.One's shape), not a leak, so the window's own jd.STATE is never the reference
#     (compared against it, the kernel's own import-time build over the run root got the report, blaming import-time
#     code for a build or a move that did not happen, whenever setUpModule or setUpClass moved jd.STATE for its
#     tests). Before the identity term the report fired on the setup's object too, blamed import-time code, gave
#     no remedy, and its naming silenced the boundary that would have been right. A missing module start read
#     refuses the report. Later windows do not apply that test: a legitimate first build followed by a STATE move
#     the judge fixture names leaves the same picture, and a test window or a boundary made it, where it was
#     judged. STATED LIMIT: the first window consumes the flag whether or not it takes the report, so an
#     import-time (or wider-scoped fixture's) build over a kept root whose worker's first window belongs to a
#     class that swapped the singleton out around its tests (K.Two's shape: saved, reset, put back) is met, as
#     that object, only at a later window, where the report is not taken, and the leak goes unreported (the
#     fixture's tests pin it as behaviour, S7, beside S6, the same leak with no swapping class, reported). The
#     closure would record the candidate at the worker's first module start read (a real object over a root
#     other than that read's jd.STATE) and raise it at the first window whose before object is that object,
#     with the wording's "before any test in this worker has run" reworded; not taken here.
# Two module-level lists of STRONG references (identity membership; strong so an id is never reused by a
# later object) keep the two kinds of naming apart. Every object a VERDICT names (a test's own, a boundary's)
# goes on _SDK_NAMED, the list the boundary's quiet-on-a-named-object rule consults. Every object the
# INHERITED report named goes on _SDK_REPORTED, and the report is silent on an object in either list, which
# is what makes "once" work (under xdist, once per worker process). The boundary never consults
# _SDK_REPORTED: an inherited report says what a test did NOT do, not what its scope did, so a class or
# module setup that completes a leak (builds, restores jd.STATE and removes the root before any test) yields
# two error lines for one leak, the inherited gone report on the scope's first test and the boundary
# verdict, naming the scope with the sandbox remedy, on its last. With one list the report's naming silenced
# the boundary and the leak was never attributed to the scope.
#
# WHAT ONE READ RECORDS (_sdk_read): the value in the shared kernel's slot (vars(km)["_sdk_backend"]),
# the marker (the function object kernel.py defines as _sdk_locked; a re-execution replaces it; None when
# no module has loaded the kernel under its shared name), the value's state_dir as text, os.path.isdir
# of it (a regular file at the path is False, on purpose: a backend over a file is as gone as one over
# nothing), and km.jd.STATE as text, the reference root. Only the kernel loaded under its SHARED name is
# read: a kernel a module loads under a private name (load_source under romp_kernel_<x>) has an
# _sdk_backend of its own, so a lazy build under a rebound state through that handle lands there and the
# shared singleton stays untouched (the browser-driven served modules load their kernels this way); the
# private name isolates the kernel's globals and NOT jd's, since judge.py loads under its shared name
# even when the kernel is private, so a test that assigns jd.STATE through a private kernel handle is
# moving the shared judge state (_shared_state_restored's concern, not this one's). A private kernel's own
# dangling singleton is outside this fixture, a stated limit, and what it leaves unprotected is this fixture's
# own defect class on a private name: a private-name kernel's dangling backend over a removed directory that
# a sibling file reads and gets the silent empty-registry answer this fixture exists to stop. It is live
# today: romp_kernel_mc is loaded by three files (tests/test_kernel_interrupt_machine_cut.py,
# tests/test_kernel_msgcaption.py and tests/test_model_catalog.py), the first file's _FeedHarness leaves its
# backend over a removed TemporaryDirectory, and two of the three read the dangling object, the machine-cut
# file's own later tests and the caption file's timeline builds (build_timeline's fork_children, the reader
# the incident above names); measured 2026-09-19 over the three files in one run, 90 of 108 teardowns end
# with that one object over a removed root (33, 5 and 52 by file) and the catalog file reads it zero times;
# eight private names are shared by two or three files each. The blocker, and the order: the same rule
# looped over every sys.modules name starting with romp_kernel (round 1's proposed fix) is the arm that would
# cover it, and the loop cannot land here because the private-kernel harnesses carry 90 or more pre-existing
# teardown leaks (the 90 above are one name's; the round-1 refuters counted 574 would-fail outcomes over the
# 18 files that share a private name), so their save-and-restore product code lands first, then the
# ratchet's private-kernel arm.
#
# THE JUDGMENT (_sdk_judge), same marker: the same object is a pass, unless its state_dir text differs
# between the two reads, the test having REPOINTED the singleton it found (the readers hold the object and
# read its state_dir on every registry scan, so a repoint to a root that stands moves every later test's
# registry root as surely as a rebuild over it: named with the changed wording, both sides rendered from the
# reads' recorded text since the live attribute shows the after path on both, the gone clause when the new
# path is not a directory, and a remedy of its own, _SDK_REMEDY_C, put the state_dir back), or its
# directory was present at the before read and is not at the after read, the test having removed the
# directory under the singleton it found. A removal never changes the text, so the two are disjoint and the
# text comparison comes first. A different value is a leak, with TWO allowances derived from the transition,
# never from a list of test names. (1) None before and, after, the kernel's own class (type module romp_sdk_backend,
# qualname SdkBackend: NOT isinstance, which a shared-name reload of sdk_backend.py breaks, since
# load_source re-executes into the same module name and the class object changes while a backend built
# before the reload keeps the old one; 11 test modules load romp_sdk_backend under the shared name) whose
# state_dir equals jd.STATE AT THE TEST'S START and is a directory: the worker's lazy first build of the
# singleton under the root the test inherited, the kernel's own design, leaving nothing dangling. The
# reference is the inherited root because it is the one value the test could not have made, and equality
# proves the build used it: a real backend's state_dir IS the root it was built over, by construction
# (kernel.py's _sdk_locked constructs sbmod.SdkBackend(jd.STATE, ...) and SdkBackend.__init__ stores
# Path(state_dir)), so no wrapper on the build is needed to learn the build root (the census's wrapper on
# _sdk_locked in the module dict changes the marker function's identity and is not a shape for a
# production fixture). jd.STATE AFTER the test would admit a first build over a sandbox the test left
# jd.STATE pointed at (the singleton agrees with the state it moved); requiring both before and after
# would refuse a legitimate first build followed by a STATE move the judge fixture already names. WHICH
# test performs the first build is a property of the run (the xdist scheduler, the subset selected, the
# module order), not of the test: the census that found ViewBuilder saw three first builders across four
# workers, a different test on each, so a name list could never be right. A look-alike over that same
# root (a test's class named SdkBackend, a SimpleNamespace, a MagicMock) is refused: installed as the
# worker's first value it would be inherited by every later test, and the class check is what refuses
# it. A value that is not the kernel's class is rendered without the gone clause: the clause says a
# state_dir is NO LONGER a directory, true of the kernel's own class alone (its state_dir is the directory
# it was built over), and false of a MagicMock's attribute or a SimpleNamespace's string, which never was
# one; so the clause on a changed value is gated on the class check as well as on isdir. (2) None before
# and False after: the kernel's own unavailable outcome (_sdk_locked's except branch
# sets False when the backend cannot be built), which the test did not choose. Everything else is a leak:
# a test that installs a fake or a rebuilt backend and puts back the OBJECT it found is quiet; one that
# puts back an equal backend (the same state_dir, another object) is not, because the readers hold the
# object, its threads and its registry state, not its path, and its message says so. A reference root
# that cannot be read (km.jd.STATE unreadable) grants no allowance: the fixture fails and says so (not
# constructible today, since the kernel always binds jd; unverified defaults to the restricted side).
#
# THE REMEDY, one per road (the message shape is "<who> <clause>. Fix: <remedy>"). The sandbox road, when
# the value left is the kernel's own class over a root that is not the reference or is not a directory:
# save km._sdk_backend before moving jd.STATE and put it back where jd.STATE is restored, before the
# directory is removed (setUp and tearDown, or setUpClass and tearDownClass when the class moves it). The
# object road, everything else (a None, a False, a fake, a rebuild over the same root): put back the
# object the test found, None or False included, not an equal one. The repoint road, the same object with
# its state_dir text changed: put the singleton's state_dir back where it was found. The first form printed
# the sandbox remedy on every road, so a test that left a None was told to save the singleton before a
# sandbox that did not exist.
#
# MARKER CHANGED (_sdk_judge_reload): the test re-executed kernel.py into the one module object (a
# different function in the slot), loaded the shared kernel for the first time in this worker (None, then
# a function), or popped it from sys.modules (a function, then None: the read gives None). The before
# value is stale by construction (the re-executed module's slot started at None), so only what the test
# LEFT is judged: None or False pass; the kernel's own class over jd.STATE with that directory present is
# the lazy build over the loader's root and passes; the kernel's class anywhere else is a build over a
# root the test made, named with the re-execution wording (and the gone clause when its directory is not
# one); anything else is a value the test left. The reference on this road is jd.STATE at the AFTER read:
# the reload re-bound STATE from the environment as it stands, which other modules' import-time writes
# decide, so the root the test inherited is stale here. A None marker before is a first load, never an
# exemption: a test that loads the shared kernel itself and then leaves the singleton over a sandbox it
# keeps is FirstBuildOverAKeptSandbox's leak by another road, and the first form of this fixture let it
# through (it compared nothing when the marker changed, and the surviving gone check misses a directory
# that stands). Stated limit: a test that reloads, moves jd.STATE, builds and LEAVES jd.STATE moved passes
# this fixture, since the singleton agrees with jd.STATE as left; that is a STATE leak, and
# _shared_state_restored's reload branch shares the limit by design (it compares no values after a
# re-execution). No test does this today.
#
# THE BOUNDARY (_sdk_judge_scope): with S = the scope's start read, L = the last read anywhere before the
# end and E = the end read: E the same object as L with its state_dir text changed is the teardown
# repointing the singleton its last test left, and E the same object as L with its directory present at L
# and gone at E is the teardown removing the directory under it, both named before the quiet rules and even
# when the object was already named, because the state got worse inside the teardown; E the object S found
# is a restore, a pass, unless the state_dir text S recorded is not E's (put back repointed) or S saw its
# directory and E does not; E the object L left and already named is a pass (the test that made it was
# judged); otherwise S -> E is judged as a test transition with S's jd.STATE as the
# reference (the scope's own setUpClass moved jd.STATE, a test built under it, allowed at its own window
# because it inherited that root, and the scope did not put the singleton back: the scope is the author);
# and E different from both S and L is the teardown itself installing a value, judged the same way.
# Before that S -> E judgment the boundary yields to the tests' own windows: the function fixture records
# every test window that changed the slot (_SDK_WINDOWS: the before and after values and the reference the
# window was judged against; cleared at each module end, since no later scope starts before that read),
# and when the first such window inside the scope started from the value S found, the last left the value
# E holds, and that last window's reference is S's jd.STATE, every step from S to E was a test's, judged
# where it happened, and the boundary returns None. Without it a test's accused reset to None or False (a
# value _sdk_name skips, so the named rule cannot cover it) or an allowed lazy rebuild after an accused
# reset was re-attributed to the class and module boundary, sending the reader to a tearDownClass or
# tearDownModule that does not exist; in the rebuild shape the boundary's verdict landed as an ERROR on
# the innocent test that made the allowed rebuild (2026-09-19). K.One is the counter-case: its build's
# reference is the class root setUpClass moved jd.STATE to, not S's, so the class stays the author. The
# module end runs after the class end, so a class-end verdict names the object and the module end is
# quiet on it. Cost: four dict lookups (the kernel module, its slot, its marker, its jd), two getattr and
# one isdir per read; two reads per test, two per class and two per module, plus one list scan per
# boundary over the module's changing windows (a handful in any module: net changes of the slot are rare).
_SdkRead = collections.namedtuple("_SdkRead", "be marker sd isdir jd_state")
_SdkWindow = collections.namedtuple("_SdkWindow", "seq before after ref")
_SDK_LAST = _SdkRead(None, None, None, None, None)     # the last read anywhere in this worker (the boundary's L)
_SDK_READS = 0                                         # reads so far in this worker; a scope keeps the count at its start read
_SDK_WINDOWS = []                                      # the test windows that changed the slot since the module started
_SDK_FIRST_WINDOW = True                               # no test window has run yet in this worker; the kept-root report is taken
                                                       # at this window only, and only for the module start read's object, against
                                                       # the jd.STATE that read recorded (at that read only import-time code and
                                                       # any fixture of a scope wider than the function has run)
_SDK_MODULE_START = None                               # the current module boundary's start read (_SdkRead): the first-window
                                                       # kept-root report's object and reference root
_SDK_NAMED = []                                        # strong references to every object a verdict named (a test's own, a boundary's)
_SDK_REPORTED = []                                     # strong references to every object the inherited report named
_SDK_REAL = ("romp_sdk_backend", "SdkBackend")
_SDK_GONE = ", whose state_dir is no longer a directory"
_SDK_REMEDY_A = ("A test that reaches km._sdk() under a sandboxed jd.STATE builds the kernel's backend singleton over the "
                 "sandbox and every later test's backend reads that root: save km._sdk_backend before moving jd.STATE and "
                 "put it back where jd.STATE is restored, before the directory is removed (setUp and tearDown, or "
                 "setUpClass and tearDownClass when the class moves it).")
_SDK_REMEDY_B = ("Put back the object the test found, None or False included, not an equal one: the kernel's readers hold "
                 "the object, its threads and its registry state, and a None makes the next reader rebuild over whatever "
                 "jd.STATE is at that moment.")
_SDK_REMEDY_C = ("Put back the singleton's state_dir where it was found: the kernel's readers hold the object and read its "
                 "state_dir on every registry scan, so a moved state_dir moves every later test's registry root.")
_SDK_LIVE = object()                                   # _sdk_singleton_text: render the live state_dir attribute


def _sdk_read():
    """One read of the kernel's backend singleton under its shared name: (value, marker, state_dir text, isdir,
    jd.STATE text), every field None when the kernel is not loaded as romp_kernel; recorded as the worker's last
    read."""
    global _SDK_LAST, _SDK_READS
    km = sys.modules.get("romp_kernel")
    if km is None:
        rec = _SdkRead(None, None, None, None, None)
    else:
        d = vars(km)
        be = d.get("_sdk_backend")
        sd = None
        if be is not None and be is not False:
            p = getattr(be, "state_dir", None)
            sd = None if p is None else str(p)
        jd_state = getattr(d.get("jd"), "STATE", None)
        rec = _SdkRead(be, d.get("_sdk_locked"), sd, None if sd is None else os.path.isdir(sd),
                       None if jd_state is None else str(jd_state))
    _SDK_READS += 1
    _SDK_LAST = rec
    return rec


def _sdk_is_real(be):
    """The kernel's own class, by module and qualname: load_source re-executes sdk_backend.py into the same module
    name, so an isinstance against the class loaded now would refuse a backend built before a shared-name reload."""
    t = type(be)
    return (t.__module__, t.__qualname__) == _SDK_REAL


def _sdk_named(be):
    """Whether a verdict (a test's own, a boundary's) has named the object: the boundary's quiet rule reads this alone."""
    return any(x is be for x in _SDK_NAMED)


def _sdk_name(be):
    if be is not None and be is not False and not _sdk_named(be):
        _SDK_NAMED.append(be)


def _sdk_reported(be):
    """Whether the inherited report has named the object; with _sdk_named, that report's once-per-worker rule."""
    return any(x is be for x in _SDK_REPORTED)


def _sdk_report(be):
    if be is not None and be is not False and not _sdk_reported(be):
        _SDK_REPORTED.append(be)


def _sdk_singleton_text(be, sd=_SDK_LIVE):
    """The value as "<class> over <state_dir>", None and False said in words. `sd` is the state_dir text to render: the
    live attribute by default, or a read's recorded text, since the same object's state_dir can have been repointed
    between two reads and the live attribute would then show the after path on both sides of the transition."""
    if be is None:
        return "None (not built)"
    if be is False:
        return "False (the build failed)"
    state_dir = getattr(be, "state_dir", None) if sd is _SDK_LIVE else sd
    t = type(be)
    name = "SdkBackend" if _sdk_is_real(be) else "%s.%s" % (t.__module__, t.__qualname__)
    return "%s over %s" % (name, "no state_dir" if state_dir is None else state_dir)


_SDK_INHERITED_TAIL = ("This test did not make it: %s, outside every window the singleton fixtures judge; reported once per "
                       "worker, at the first test that meets it, after that test's own teardown (so the test runs and its own "
                       "transition is judged too), and the tests after it that inherit the same object are not accused.")


def _sdk_inherited(before, start):
    """The once-per-worker report on a singleton state no window made, or None: a real backend over a directory that is
    gone, at any test; or, with `start` (the module boundary's start read, passed only at the worker's FIRST test window
    AND when the object is the one that read found, else None), a real backend over a directory other than jd.STATE AS
    THAT READ RECORDED IT, which only import-time code or a fixture of a scope wider than the function could have made:
    at the start read nothing else has run, and the identity term with the start read's reference make the window's
    report a statement about that read (jd.STATE at the window itself may have been moved since by setUpModule,
    setUpClass or a module- or class-scoped fixture, which is no leak; compared against the window's jd.STATE, a
    legitimate import-time build over the run root got the report whenever a scope setup moved jd.STATE for its tests);
    an object the start read did not see was installed by the module's or a class's own setup, which that scope's
    boundary judges. Silent on an object either list has named (_sdk_named, _sdk_reported)."""
    be = before.be
    if not _sdk_is_real(be) or _sdk_named(be) or _sdk_reported(be):
        return None
    if before.isdir is False:
        return ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that no longer exists: %s. %s"
                % (_sdk_singleton_text(be),
                   _SDK_INHERITED_TAIL % "an earlier test, a class or module setup or teardown, or import-time code did"))
    if start is not None and before.sd != start.jd_state:
        return ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that is not jd.STATE, before "
                "any test in this worker has run: %s, jd.STATE %s at this module's start read. %s"
                % (_sdk_singleton_text(be), start.jd_state,
                   _SDK_INHERITED_TAIL % "import-time code did, or a session- or package-scoped fixture did (one that set up "
                   "before this module's own reads), building the singleton over a root that is not the run's, or moving "
                   "jd.STATE after the build and leaving it there"))
    return None


def _sdk_remedy(after, ref):
    """The sandbox road's remedy when the value left is the kernel's own class over a root that is not the reference
    or is not a directory; the object road's otherwise."""
    if _sdk_is_real(after.be) and (after.sd != ref or not after.isdir):
        return _SDK_REMEDY_A
    return _SDK_REMEDY_B


def _sdk_repointed_text(head, be, before, after):
    """The clause for the same object whose state_dir text changed between two reads, both sides from the recorded text
    (the live attribute shows the after path on both), the gone clause when the new path is not a directory."""
    return "%s: before %s, after %s%s" % (head, _sdk_singleton_text(be, before.sd), _sdk_singleton_text(be, after.sd),
                                          _SDK_GONE if after.isdir is False and _sdk_is_real(be) else "")


def _sdk_judge(before, after, ref):
    """The transition from one read to another, judged as a test's: None for a pass, else (clause, remedy) for
    the caller to frame as "<who> <clause>. Fix: <remedy>". `ref` is the root the lazy-first-build allowance
    compares the after value's state_dir with."""
    be0, be1 = before.be, after.be
    if after.marker is not before.marker:
        return _sdk_judge_reload(before, after)
    if be1 is be0:
        if before.sd != after.sd:              # the same object, repointed: the readers hold the object and read its state_dir
            return (_sdk_repointed_text("left the kernel's backend singleton (km._sdk_backend) changed after its teardown",
                                        be1, before, after), _SDK_REMEDY_C)
        if before.isdir and after.isdir is False:
            return ("left the kernel's backend singleton (km._sdk_backend) over a directory it removed: %s%s"
                    % (_sdk_singleton_text(be1), _SDK_GONE), _sdk_remedy(after, ref))
        return None
    unreadable = ""
    if be0 is None:
        if be1 is False:                       # the kernel's own unavailable outcome
            return None
        if _sdk_is_real(be1) and after.isdir:
            if ref is None:
                unreadable = "; the reference root (km.jd.STATE) was unreadable, so the lazy first build could not be allowed"
            elif after.sd == ref:
                return None                    # the lazy first build over the root the test inherited
    if _sdk_is_real(be0) and _sdk_is_real(be1) and before.sd == after.sd and after.isdir:
        after_text = "another SdkBackend over the same directory (the readers hold the object, not the path)"
    else:
        after_text = _sdk_singleton_text(be1) + (_SDK_GONE if after.isdir is False and _sdk_is_real(be1) else "")
    return ("left the kernel's backend singleton (km._sdk_backend) changed after its teardown: before %s, after %s%s"
            % (_sdk_singleton_text(be0), after_text, unreadable), _sdk_remedy(after, ref))


def _sdk_judge_reload(before, after):
    """The changed-marker road (a re-execution, a first load, or a popped kernel inside the test): the after value
    alone, judged against jd.STATE as the reload re-bound it (the after read); see the comment above for why the
    before value and the before reference are stale here."""
    be1 = after.be
    if be1 is None or be1 is False:
        return None
    head = ("re-executed the kernel (or loaded it for the first time) and left the kernel's backend singleton "
            "(km._sdk_backend) ")
    if not _sdk_is_real(be1):
        return (head + "as a value that is not the kernel's build: %s" % _sdk_singleton_text(be1), _SDK_REMEDY_B)
    ref = after.jd_state
    if ref is None:
        return (head + "over %s while the reference root (km.jd.STATE) was unreadable, so the lazy build could not be "
                "allowed" % _sdk_singleton_text(be1), _SDK_REMEDY_A)
    if after.sd == ref:
        if after.isdir:
            return None
        return (head + "over jd.STATE, which is no longer a directory: %s%s" % (_sdk_singleton_text(be1), _SDK_GONE),
                _SDK_REMEDY_A)
    return (head + "over a root that is not jd.STATE: %s, jd.STATE %s%s"
            % (_sdk_singleton_text(be1), ref, _SDK_GONE if after.isdir is False else ""), _SDK_REMEDY_A)


def _sdk_judge_scope(start, last, end, windows):
    """The class or module boundary's verdict from its start read, the last read before its end, its end read, and the
    test windows inside the scope that changed the slot (oldest first)."""
    if end.be is last.be:
        if last.sd != end.sd:                  # the teardown repointed the singleton its last test left: named before the quiet rules
            return (_sdk_repointed_text("left the kernel's backend singleton (km._sdk_backend) changed after its teardown",
                                        end.be, last, end), _SDK_REMEDY_C)
        if last.isdir and end.isdir is False:
            return ("left the kernel's backend singleton (km._sdk_backend) over a directory it removed: %s%s"
                    % (_sdk_singleton_text(end.be), _SDK_GONE), _sdk_remedy(end, start.jd_state))
        if end.be is start.be or _sdk_named(end.be):
            return None
        if windows and windows[0].before is start.be and windows[-1].after is end.be and windows[-1].ref == start.jd_state:
            return None                    # the tests made the change, each judged at its own window: the boundary did nothing
        return _sdk_judge(start, end, start.jd_state)
    if end.be is start.be:
        if start.sd != end.sd:
            return (_sdk_repointed_text("put back the kernel's backend singleton (km._sdk_backend) it found with its state_dir "
                                        "repointed", end.be, start, end), _SDK_REMEDY_C)
        if start.isdir and end.isdir is False:
            return ("put back the kernel's backend singleton (km._sdk_backend) it found, whose directory is gone: %s%s"
                    % (_sdk_singleton_text(end.be), _SDK_GONE), _sdk_remedy(end, start.jd_state))
        return None
    return _sdk_judge(start, end, start.jd_state)


@pytest.fixture(autouse=True)
def _sdk_singleton_restored(request):
    global _SDK_FIRST_WINDOW
    before = _sdk_read()
    # The kept-root report at the first window is taken only for the object the module's own start read found (identity)
    # and against the jd.STATE that read recorded: a value installed after that read is the module's or a class's own
    # setup, judged at that scope's boundary, and a jd.STATE moved after it is a scope setup's move for its tests.
    first = _SDK_FIRST_WINDOW and _SDK_MODULE_START is not None and before.be is _SDK_MODULE_START.be
    inherited = _sdk_inherited(before, _SDK_MODULE_START if first else None)
    _SDK_FIRST_WINDOW = False
    if inherited is not None:
        _sdk_report(before.be)             # reported now, so the tests after this one that inherit the object are quiet
    yield
    after = _sdk_read()
    verdict = _sdk_judge(before, after, before.jd_state)     # the root the test inherited: the one value it could not have made
    if after.be is not before.be:
        _SDK_WINDOWS.append(_SdkWindow(_SDK_READS, before.be, after.be,
                                       after.jd_state if after.marker is not before.marker else before.jd_state))
    if verdict is None and inherited is None:
        return
    lines = []
    if inherited is not None:
        lines.append("%s %s" % (request.node.nodeid, inherited))
    if verdict is not None:
        _sdk_name(after.be)
        lines.append("%s %s. Fix: %s" % (request.node.nodeid, verdict[0], verdict[1]))
    pytest.fail("\n".join(lines), pytrace=False)


def _sdk_boundary(request, start, reads_at_start):
    last = _SDK_LAST
    end = _sdk_read()
    windows = [w for w in _SDK_WINDOWS if w.seq > reads_at_start]
    verdict = _sdk_judge_scope(start, last, end, windows)
    if verdict is None:
        return
    _sdk_name(end.be)
    pytest.fail("%s's class or module boundary (tearDownClass, tearDownModule or a class- or module-scoped fixture) %s. "
                "Fix: %s" % (request.node.nodeid, verdict[0], verdict[1]), pytrace=False)


@pytest.fixture(autouse=True, scope="class")
def _sdk_singleton_class_boundary(request):
    start = _sdk_read()
    reads_at_start = _SDK_READS
    yield
    _sdk_boundary(request, start, reads_at_start)


@pytest.fixture(autouse=True, scope="module")
def _sdk_singleton_module_boundary(request):
    global _SDK_MODULE_START
    start = _sdk_read()
    _SDK_MODULE_START = start              # the first-window report's object and reference root (_sdk_singleton_restored)
    reads_at_start = _SDK_READS
    yield
    try:
        _sdk_boundary(request, start, reads_at_start)
    finally:
        del _SDK_WINDOWS[:]                # no later scope starts before this read, so no boundary selects these again


# No test report may carry a process-environment VALUE, or a credential-shaped token (2026-09-05). A
# test that renders an env mapping in an assertion (assertNotIn on os.environ, on a _judge_env() copy
# of it, on a launch env) prints the whole mapping when it fails, and on a developer's box that
# mapping holds live credentials. Assertions that test membership and name the key are the fix; this
# hook is the safety net for an assertion still written the other way. Two nets, applied to every
# report's text (the longrepr and the captured-output sections) whatever the outcome, and to
# collection reports:
#   * every value seen in this process's environment, 16 characters or longer, is replaced with one
#     marker, and so is each whitespace-separated chunk of such a value that is 16 characters or
#     longer (pprint renders a value with spaces as adjacent literals on separate lines, so a
#     whole-value replace misses the pieces), and so is each piece of such a value that pytest or
#     unittest left beside a cut (`'<head>...<tail>'`, `[N chars]`: a failed `==` keeps 12 and 13
#     characters of each operand, so most of a 30-character value showed on the assert line and in
#     the short summary, 2026-09-07). Values are noted the moment they are WRITTEN into
#     os.environ (the mutation path is wrapped below: a plain assignment, update, setdefault,
#     os.putenv, os.environb, mock.patch.dict), and sampled at import, around each test and at
#     report time as well, for values that entered by another route (inherited from the parent
#     process, written by a C extension). Exempt, and never when the name is credential-shaped: a
#     path-valued variable by NAME (the shell's, this conftest's own dirs, the interpreter and
#     workspace paths GitHub Actions exports); a variable whose value is public by NAME (the ones
#     GitHub Actions exports to describe the run: the server URLs, the sha, the ref, the workflow
#     and job names, the repository and the actor, each of which a CI failure report was showing as
#     the marker, 2026-09-07; and the synthetic git identity this conftest sets at import); a name
#     family that is never a credential (XDG_*, and pytest's own PYTEST_*: PYTEST_CURRENT_TEST holds
#     the running test's node id and is written for every phase of every test, so noting it grew the
#     set by one value per test, slowed every report's scrub in step and made the node id of every
#     test already run a target in later reports); and any value that IS a path this machine has
#     (one absolute path that exists, or a PATH-style list of them), because a traceback quotes the
#     interpreter's prefix on every frame and a developer's shell names it under any variable (a
#     pyenv root, a conda prefix).
#   * credential-shaped tokens by PATTERN (tests/credential_patterns.py: the public key prefixes, and
#     a long token in a value position), whatever their provenance: a token that never touched the
#     environment (read from a file, printed by a child) is caught by this one.
# A report the hook leaves alone keeps pytest's own object and rendering. One it changes is rebuilt
# from the scrubbed text as a native-style traceback with its crash location kept (its message
# scrubbed too), so the short test summary still ends in the assertion message, junitxml keeps its
# message and xdist carries it to the controller; that report loses colour and source highlighting,
# nothing else (_redacted_longrepr).
ENV_VALUE_MIN_LEN = 16
ENV_VALUE_REDACTED = "[REDACTED-ENV-VALUE]"
_ENV_VALUE_PATH_NAMES = frozenset((
    "PWD", "OLDPWD", "HOME", "PATH", "TMPDIR", "SHELL", "VIRTUAL_ENV", "PYTHONPATH", "LS_COLORS",
    "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ROMP_DIR", "ROMP_STATE_DIR", "ROMP_CLAUDE_BIN",
    "ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR", "CLAUDE_CONFIG_DIR", "ROMP_TESTS_SYSTEM_TMPDIR",
    # the Claude settings dir conftest saved ahead of its CLAUDE_CONFIG_DIR floor (above), for the live
    # move test: a path a failure report may quote, like CLAUDE_CONFIG_DIR beside it
    "ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
    # GitHub Actions: the runner's workspace and tool cache, and the interpreter prefix setup-python
    # exports under six names (every stdlib and site-packages frame of a CI traceback is under it)
    "GITHUB_WORKSPACE", "RUNNER_WORKSPACE", "RUNNER_TEMP", "RUNNER_TOOL_CACHE", "pythonLocation",
    "Python_ROOT_DIR", "Python2_ROOT_DIR", "Python3_ROOT_DIR", "LD_LIBRARY_PATH", "PKG_CONFIG_PATH"))
# Public by name, so never a value a report must hide. GitHub Actions describes the run in these (its
# secrets are GITHUB_TOKEN, ACTIONS_RUNTIME_TOKEN and ACTIONS_ID_TOKEN_REQUEST_TOKEN, credential-shaped
# names this set is never consulted for); without them a CI failure read `assert '[REDACTED-ENV-VALUE]'
# == 'x'` where a test compared the ref, the repository or the actor. Listed by name rather than by the
# GITHUB_ prefix so that a token GitHub adds under a name this list does not know still qualifies. The
# GIT_* names are the synthetic identity this conftest writes at import (`romp tests`,
# `tests@example.invalid`), under which every fixture commit is made.
_ENV_VALUE_PUBLIC_NAMES = frozenset((
    "GITHUB_SERVER_URL", "GITHUB_API_URL", "GITHUB_GRAPHQL_URL", "GITHUB_SHA", "GITHUB_REF", "GITHUB_REF_NAME",
    "GITHUB_HEAD_REF", "GITHUB_BASE_REF", "GITHUB_EVENT_NAME", "GITHUB_WORKFLOW", "GITHUB_WORKFLOW_REF",
    "GITHUB_WORKFLOW_SHA", "GITHUB_JOB", "GITHUB_ACTION", "GITHUB_ACTION_REF", "GITHUB_ACTION_REPOSITORY",
    "GITHUB_REPOSITORY", "GITHUB_REPOSITORY_OWNER", "GITHUB_ACTOR", "GITHUB_TRIGGERING_ACTOR", "RUNNER_NAME",
    "RUNNER_ARCH",
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"))
_ENV_VALUE_EXEMPT_PREFIXES = ("XDG_", "PYTEST_")   # never a credential: the XDG base dirs, pytest's bookkeeping
_ENV_VALUES_SEEN: set = set()


def _load_credential_patterns():
    """tests/credential_patterns.py, by path beside this file (a subprocess run against a copy of the
    conftest carries a copy of it too). A missing module is an error, never a silent net less."""
    p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "credential_patterns.py")
    spec = importlib.util.spec_from_file_location("romp_tests_credential_patterns", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_credpat = _load_credential_patterns()
CREDENTIAL_REDACTED = _credpat.REDACTED


def _credential_shaped(name: str) -> bool:
    n = name.upper()
    return (n == "ANTHROPIC_API_KEY" or n.endswith("_API_KEY") or n.endswith("_TOKEN") or n.startswith("ANTHROPIC_")
            or "SECRET" in n or "PASSWORD" in n or "APIKEY" in n)


def _is_existing_path(value: str) -> bool:
    """Whether `value` is a path this machine has: one absolute path that exists, or a PATH-style list
    of them (every non-empty os.pathsep chunk). No token is an absolute path that exists, so this
    exempts no token; a path that does not exist is a value like any other."""
    chunks = [c for c in value.split(os.pathsep) if c]
    return bool(chunks) and all(os.path.isabs(c) and os.path.exists(c) for c in chunks)


def env_value_qualifies(name: str, value: str) -> bool:
    """Whether one environment entry's value is one a report must not show: ENV_VALUE_MIN_LEN
    characters or more, unless the name is exempt (a path-valued variable by name, a variable whose
    value is public by name, or a name family that is never a credential) or the value is a path this
    machine has; a credential-shaped name is never exempt. The one rule, for the sampler and for the
    write hook."""
    if len(value) < ENV_VALUE_MIN_LEN:
        return False
    if _credential_shaped(name):
        return True
    if name in _ENV_VALUE_PATH_NAMES or name in _ENV_VALUE_PUBLIC_NAMES or name.startswith(_ENV_VALUE_EXEMPT_PREFIXES):
        return False
    return not _is_existing_path(value)


def env_values_to_redact(environ=None) -> set:
    """The values of `environ` (the process environment by default) a report must not show."""
    env = os.environ if environ is None else environ
    return {value for name, value in env.items() if env_value_qualifies(name, value)}


def note_env_value(name, value) -> bool:
    """Note one value at the moment it is written into the environment (the hook below). Bytes
    (os.environb, os.putenv) are decoded the way os.environ decodes them. Returns whether the value
    qualified; anything that is not a name and a string value does not."""
    if isinstance(name, bytes):
        name = os.fsdecode(name)
    if isinstance(value, bytes):
        value = os.fsdecode(value)
    if not isinstance(name, str) or not isinstance(value, str):
        return False
    if not env_value_qualifies(name, value):
        return False
    _ENV_VALUES_SEEN.add(value)
    return True


def _install_env_write_hook() -> None:
    """Wrap the one method every os.environ write goes through and os.putenv beside it. A plain
    assignment, update, setdefault, mock.patch.dict (an update) and os.environb all reach
    _Environ.__setitem__; os.putenv is the module global that method calls and the path that writes
    to the process without touching the mapping. Idempotent: a second import stacks no wrapper."""
    if getattr(os._Environ.__setitem__, "_romp_notes_values", False):
        return
    orig_setitem = os._Environ.__setitem__
    orig_putenv = os.putenv

    def setitem(self, key, value):
        note_env_value(key, value)
        return orig_setitem(self, key, value)

    def putenv(key, value):
        note_env_value(key, value)
        return orig_putenv(key, value)

    setitem._romp_notes_values = putenv._romp_notes_values = True
    os._Environ.__setitem__ = setitem
    os.putenv = putenv


_install_env_write_hook()


# A piece of a value beside a cut pytest or unittest made: a maximal run of ENV_CUT_FRAGMENT_MIN_LEN or
# more token characters that abuts `...` or `[N chars]` on at least one side (the marker before it, the
# marker after it, or a quote on one side and the marker on the other). pytest renders a failed `==` at
# default verbosity with each operand cut to 12 and 13 characters around `...` (`'abcdefghijkl...rstuvwxyzabcd'`
# for a 30-character value), its saferepr of a local or a `+  where` operand keeps 117 on each side,
# the short summary cuts the message at the terminal's width with `...` appended, a long explanation
# is cut at 640 characters the same way, and unittest shortens a container repr with `[N chars]`; none
# of those pieces is the whole value or a whitespace chunk of it, so the replace above left them
# standing (2026-09-07). A candidate is replaced only when it is a substring of a noted value: exact,
# never a guess from its shape (the pattern net's fragment rule does that for tokens of no known
# provenance). Two alternatives so each maximal run is tried once from its start, which keeps the pass
# linear on a long run that reaches no cut.
ENV_CUT_FRAGMENT_MIN_LEN = 8
_ENV_CUT_FRAG_RE = re.compile(
    r"(?:(?<=\.\.\.)|(?<=chars\]))[A-Za-z0-9_\-]{%d,}"                                  # after a cut
    r"|(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{%d,}(?=\.\.\.|\[\d+ chars\])"                    # before one
    % (ENV_CUT_FRAGMENT_MIN_LEN, ENV_CUT_FRAGMENT_MIN_LEN))


def redact_env_values(text: str, values) -> str:
    """`text` with every occurrence of every value replaced by ENV_VALUE_REDACTED, longest first (a
    value that contains another is replaced whole), then every whitespace-separated chunk of a
    value that is ENV_VALUE_MIN_LEN characters or more (pprint renders a long value with spaces as
    adjacent string literals on separate lines, so the token half of `Authorization: Bearer <token>`
    survived a whole-value replace, and unittest's shortened repr shows a differing tail on its own),
    and then every piece of a value left beside a cut (_ENV_CUT_FRAG_RE: a run of token characters
    against `...` or `[N chars]` that is a substring of a value)."""
    parts = set()
    for v in values:
        if not v:
            continue
        parts.add(v)
        chunks = v.split()
        if len(chunks) > 1:
            parts.update(c for c in chunks if len(c) >= ENV_VALUE_MIN_LEN)
    for v in sorted(parts, key=len, reverse=True):
        text = text.replace(v, ENV_VALUE_REDACTED)
    if not parts:
        return text

    def cut_piece(m):
        frag = m.group(0)
        return ENV_VALUE_REDACTED if any(frag in v for v in parts) else frag
    return _ENV_CUT_FRAG_RE.sub(cut_piece, text)


def redact_credential_tokens(text):
    """The pattern net: credential-shaped tokens, whatever their provenance (tests/credential_patterns.py)."""
    return _credpat.scrub(text)


def redact_report_text(text: str, values=None) -> str:
    """Both nets over one report string: the environment's values (and their chunks), then the
    credential-shaped tokens. `values` defaults to everything noted so far."""
    return redact_credential_tokens(redact_env_values(text, _ENV_VALUES_SEEN if values is None else values))


def _note_env_values():
    _ENV_VALUES_SEEN.update(env_values_to_redact())


_note_env_values()


@pytest.fixture(autouse=True)
def _remember_env_values():
    """The sampling half. A value a test writes itself is noted at the write (note_env_value), so one
    present only between these samples is redacted too; the samples at every test's setup and
    teardown, and at report time, are for values that entered the environment by a route the write
    hook does not see (inherited from the parent process before this file loaded, written by a C
    extension)."""
    _note_env_values()
    yield
    _note_env_values()


def _redact_crash_message(message: str) -> str:
    """A crash message scrubbed as the report body renders it. pytest writes the message's lines under
    the `E` marker (`E   ` + line), and the pattern net's rules for a failed comparison's diff lines
    and quoted elements are keyed on that marker; the bare message (`  - <token>` after the diff's
    header) is a rendering the rules do not know, so it is scrubbed marked and unwrapped. Under CI
    pytest prints the whole message, every line, in the short test summary."""
    marked = "\n".join("E   " + line for line in message.split("\n"))
    return "\n".join(line[4:] if line.startswith("E   ") else line
                     for line in redact_report_text(marked).split("\n"))


def _redacted_longrepr(lr, text: str):
    """The scrubbed `text` of a longrepr as a longrepr again. A failure's keeps its crash location
    (pytest's own ReprFileLocation, the message scrubbed too) over a native-style traceback whose one
    entry is the text: the short test summary ends in reprcrash.message, junitxml's message attribute
    reads it, and xdist serializes a longrepr with a traceback and a crash structurally, where a plain
    str showed the traceback's first line in the summary instead (`def test_x():`, or `self = <Case
    testMethod=...>`). pytest renders a native entry as is, so that report loses colour and source
    highlighting and nothing else. A longrepr with no crash location (a collection error's) becomes
    the plain text."""
    crash = getattr(lr, "reprcrash", None)
    if crash is None:
        return text
    return ReprExceptionInfo(reprtraceback=ReprTracebackNative([text + "\n"]),
                             reprcrash=ReprFileLocation(crash.path, crash.lineno, _redact_crash_message(crash.message)))


def _redact_report(rep) -> None:
    """Every text a report carries, whatever its outcome: the longrepr (a failure's text; a skip's is
    a (path, line, reason) tuple, whose reason is the text) and the captured-output sections (which
    -rA and -rP print for passed tests too). A longrepr the nets leave unchanged keeps pytest's own
    object and rendering; one they change is rebuilt by _redacted_longrepr."""
    _note_env_values()
    lr = getattr(rep, "longrepr", None)
    if isinstance(lr, tuple) and len(lr) == 3 and isinstance(lr[2], str):
        red = redact_report_text(lr[2])
        if red != lr[2]:
            rep.longrepr = (lr[0], lr[1], red)
    elif lr is not None:
        text = str(lr)
        red = redact_report_text(text)
        if red != text:
            rep.longrepr = _redacted_longrepr(lr, red)
    if getattr(rep, "sections", None):
        rep.sections = [(name, redact_report_text(content)) for name, content in rep.sections]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # ONE implementation per hook per module: a second `def` of this name would silently replace this one
    # (it did, for an afternoon on 2026-09-10, and every report printed its values again). Anything else
    # that shapes a test report joins here: the served-tests switch first (its message quotes the skip's
    # reason), the redaction last, so whatever any step wrote is read for values before it is printed.
    outcome = yield
    rep = outcome.get_result()
    _require_served_test_ran(item, rep)
    _redact_report(rep)


@pytest.hookimpl(hookwrapper=True)
def pytest_collectreport(report):
    """A collection error (an import-time exception whose message names a value) is a report too.
    Redacted BEFORE the other implementations see it: the terminal reporter files it from here."""
    _redact_report(report)
    yield


# ── thread census (T282) ──────────────────────────────────────────────────────────────────────────────
# A test that starts a real kernel loop, a backend pump or a fake server must end it before its module ends: a
# daemon thread that outlives its module runs against whatever the shared modules (the judge, the event model)
# are bound to by then. These two helpers are the pin every such module carries, and the module-boundary
# tracer reads the same census, so a leak is named by the module that made it.
def thread_census():
    """The live non-main threads as stable descriptors: the target's qualified name when the thread has one,
    else its name; pytest-timeout's own watchdog thread excluded. Sorted, so two censuses compare directly."""
    import threading
    out = []
    for t in threading.enumerate():
        if t is threading.main_thread():
            continue
        target = getattr(t, "_target", None)
        mod = (getattr(target, "__module__", "") or "") if target is not None else ""
        if t.name.startswith("pytest_timeout") or mod.startswith("pytest_timeout"):
            continue
        out.append("%s.%s" % (mod, getattr(target, "__qualname__", None) or repr(target)) if target is not None else t.name)
    return sorted(out)


def wait_for_census(before, timeout=5.0):
    """The threads alive now that were NOT in `before`, once that set is empty or at the deadline: a module's pin is
    "nothing this module started outlives it", so a thread from an EARLIER module that happens to end during this one
    cannot fail it, and a thread this module started has a moment (20 ms polls, up to `timeout`) to reach its exit
    after join(timeout) returned. Returns the sorted leftovers; a clean module gets []."""
    import collections
    import time
    deadline = time.monotonic() + timeout
    base = collections.Counter(before)
    while True:
        extra = sorted((collections.Counter(thread_census()) - base).elements())   # by COUNT: a second thread of a
        if not extra or time.monotonic() >= deadline:                              # kind already present is a leftover
            return extra
        time.sleep(0.02)


# Browser-backed served-page tests fail loudly where they must run (T308, 2026-09-10). tests/test_*_browser.py and
# tests/test_*_served.py boot a hermetic kernel and drive the real dashboard pages in playwright's Chromium; on a machine
# without the extension's node deps or a browser they skip, and say why. CI's Python matrix jobs are such machines, so a
# served-page regression never turned them red (the deep-link landing pin, T307, red on main while CI stayed green). The
# extension job installs that browser and runs these files with ROMP_SERVED_TESTS_REQUIRE=1: any skip in them (a class
# setUp that finds no deps, a driver that exits 3 for a missing browser, a kernel that never served) is reported as a
# FAILURE carrying the skip's own reason, the stance the pane bench takes with ROMP_UI_BENCH_REQUIRE. One exception a
# test can claim for itself: a skip whose reason begins with "optional:" stays a skip, for a leg the runner has declared
# it does not carry (the pane-hiding test drives three engines and CI installs one; ROMP_SERVED_TESTS_ENGINES names the
# installed ones, and that test says "optional:" for the others). Off (the default) nothing changes: contributors and
# the Python matrix jobs skip as before. Pinned by tests/test_served_tests_require.py.
_SERVED_TESTS_REQUIRE = os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1"


def _is_served_test_file(item) -> bool:
    name = os.path.basename(str(getattr(item, "path", None) or item.fspath))
    return name.startswith("test_") and (name.endswith("_browser.py") or name.endswith("_served.py"))


def _require_served_test_ran(item, rep) -> None:
    """Under ROMP_SERVED_TESTS_REQUIRE=1, a skip in a browser-backed served-page test file is reported as a
    failure carrying the skip's own reason; an `optional:` skip stays a skip. Called from the one
    pytest_runtest_makereport above. No-op with the switch off."""
    if not _SERVED_TESTS_REQUIRE:
        return
    if rep.skipped and _is_served_test_file(item):
        lr = rep.longrepr
        reason = lr[2] if isinstance(lr, tuple) and len(lr) == 3 else str(lr)
        if re.match(r"^(Skipped: )?optional:", reason):
            return
        rep.outcome = "failed"
        rep.longrepr = ("ROMP_SERVED_TESTS_REQUIRE=1: a browser-backed test skipped (at %s) where it must run: %s"
                        % (rep.when, reason))
