"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import atexit
import os
import shutil
import sys
import tempfile

import pytest

# Every temp path a run creates lives under ONE private root, removed when the run ends (2026-09-06).
# The suite mints thousands of temp directories per run and cleans up almost none of them: 500+
# module preambles `mkdtemp()` a state root that the kernel then stamps with romp/repo-root, and
# per-test mkdtemp/mkstemp calls rarely get a tearDown. Each run left ~5,600 entries in the system
# temp dir, at up to ten a second; by the time it was noticed /tmp held 1.8 million of them, `ls
# /tmp` took ten seconds and anything started from /tmp stalled at import. Rather than chase every
# call site, redirect the process's temp dir: tempfile.tempdir is set directly (gettempdir() caches
# its first answer, and tests/__init__.py has already called it by the time this runs), and TMPDIR
# is exported so every child the tests spawn — kernels, git, `mktemp -d` in a shell — inherits the
# same root. Import-time, not pytest_configure: this module's own XDG floor below and every
# module-level mkdtemp at collection must land inside it. Removed in pytest_unconfigure, which
# under pytest-xdist runs in the controller and in every worker: each imported this file and so
# owns a root of its own (a worker's sits inside the controller's, since it inherits that TMPDIR).
# atexit is the fallback for a normal exit that skipped unconfigure; nothing survives an os._exit
# (pytest-timeout's thread method ends a hung run that way), so a hang leaks one root. The prefix
# is what a stray one looks like in the system temp dir.
# The temp dir this process was handed is recorded before the redirect: a test that must leave
# the root (an AF_UNIX socket path that would not fit sun_path under a nested root) falls back to
# it, and only to it — a literal system path in a `dir=` would bypass the redirect (one did).
os.environ["ROMP_TESTS_SYSTEM_TMPDIR"] = tempfile.gettempdir()
_TMP_ROOT = tempfile.mkdtemp(prefix="romp-tests-")
tempfile.tempdir = _TMP_ROOT
os.environ["TMPDIR"] = _TMP_ROOT


def _remove_tmp_root():
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)


atexit.register(_remove_tmp_root)


def pytest_unconfigure(config):
    _remove_tmp_root()


# No test's git reads the developer's configuration (2026-09-06). Fixture repos are built by `git
# init` + `git commit` in temp dirs, and those commands honoured the developer's global config: a
# global core.hooksPath ran their pre-commit hook (a gitleaks scan) on every seed commit, an LFS
# filter would run on every checkout, and a credential helper or insteadOf rewrite could reach a
# real remote (tests/test_file_github.py pins its own environment for exactly that reason). CI has no
# global git config, so a test that leans on one is already broken there; this makes every run match.
# GIT_CONFIG_GLOBAL is honoured by git >= 2.32; the identity is synthetic, and it is set rather than
# defaulted so a developer's own GIT_AUTHOR_* cannot leak into fixture commits either. The env
# identity outranks `git config user.*` and `-c user.*`, so a test that must pin a particular author
# exports its own GIT_AUTHOR_* / GIT_COMMITTER_* per call; other config keys still yield to `-c`.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_AUTHOR_NAME"] = os.environ["GIT_COMMITTER_NAME"] = "romp tests"
os.environ["GIT_AUTHOR_EMAIL"] = os.environ["GIT_COMMITTER_EMAIL"] = "tests@example.invalid"

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel exports this to its sessions; it outranks the XDG floor

# No test may reach a REAL manager control port (2026-08-27): on a machine running a live romp,
# every shell the manager tree spawns inherits ROMP_MANAGER_PORT, and any test kernel that dials
# "the manager" through the inherited value restarts the ACTUAL deployment — the serve-layer
# restart test's pop-then-restore raced the /restart handler's post-ack env read and took a
# self-hosted instance down mid-suite, repeatedly. POISONED to a dead port, never popped: an
# absent var is the one unsafe state, because _restart_this_kernel treats absent as "no manager"
# but _run_main_update maps absent to the DEFAULT port — the live one — so only a dead value is
# safe against every consumer. Import-time, so collection-time code is floored too.
os.environ["ROMP_MANAGER_PORT"] = "1"

# No test may read the REAL service.env (2026-09-04): sdk_backend.work_api_key now reads the manager
# env file LIVE (kernel/keysource.py) instead of popping os.environ once, so on a machine running a
# live romp every auth test would otherwise resolve the developer's ACTUAL API key — quietly billing
# nothing, but making the key material a test input, putting it one assertion message away from a
# terminal, and making the pinned fixture-key tests pass or fail on whether this box happens to have
# a key configured. Pointed at a path inside the temp state root that is never created, so every read
# is the "no file" case and the startup-pop fallback governs, exactly as before the live source
# existed. Both spellings, because keysource accepts both. Import-time (collection is floored too)
# plus a per-test re-assert below, on the same reasoning as the manager port.
_NO_SERVICE_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_SERVICE_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_SERVICE_ENV


@pytest.fixture(autouse=True)
def _no_real_service_env():
    """Re-asserted, not defaulted: a module-level write in one test file executes during collection
    and would otherwise hold for the whole run. A test that needs its own env file points the vars at
    a temp path in setUp, which runs AFTER this fixture (pytest fills fixtures in the item's setup
    phase, before TestCase.run calls setUp) — so per-test intent still wins."""
    for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
        os.environ[var] = _NO_SERVICE_ENV
    yield


@pytest.fixture(autouse=True)
def _dead_manager_port():
    """The import-time poison above covers collection, but a module-level env write in a test file
    ALSO executes during collection — so one module's write (or pop) would otherwise hold for the
    entire run phase, erasing the floor for every test after it. Re-assert per test: no
    module-level write can outlive collection against this."""
    os.environ["ROMP_MANAGER_PORT"] = "1"
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
# api.anthropic.com on any credential the process carries: the manager-env key
# sdk_backend.work_api_key claimed, else a bare ANTHROPIC_API_KEY, else an ANTHROPIC_AUTH_TOKEN
# bearer. A DEFENSIVE floor: no test reached the network before this line (checked, not assumed —
# the one in-process _sdk() driver, test_kernel_headless_ops' SdkSingleFlight, runs the refresh
# inside the test process with the module loader mocked, and it stopped only because the mocked
# module's work_api_key handed http.client a credential it rejects before a socket opens), but any
# in-process _sdk() call is one exported key away from a real request no test asserts on, on a key
# the test never chose. The kernel-SPAWNING tests floor it in their subprocess env
# (test_gear_select_matrix, test_ship_reship, test_awaiting_box_sync); this floors every test,
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
# Per-test re-assert below, on the same reasoning as the manager-port floor.
os.environ["ROMP_CLI_SCOPE"] = "0"


@pytest.fixture(autouse=True)
def _no_cli_scope():
    os.environ["ROMP_CLI_SCOPE"] = "0"
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
