"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import os
import sys
import tempfile

import pytest

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")   # recorded by tests/__init__.py's hook
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel exports this to its sessions; it outranks the XDG floor


def pytest_sessionfinish(session, exitstatus):
    """Temp-directory hygiene (2026-09-06, see tests/__init__.py): remove every directory this
    process made through tempfile.mkdtemp, this state root included, when the session ends. Runs in
    the controller and in every xdist worker, since each is its own pytest session. The package's
    atexit hook does the same at interpreter exit; both are idempotent."""
    try:
        from tests import remove_made_dirs
    except Exception:
        return
    remove_made_dirs()


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
# A runtime provider can also be selected directly from the manager's environment. Remove its
# inherited reference before module loading, so an auth test cannot resolve a developer's vault
# merely because the isolated service.env is absent. Tests set synthetic references explicitly. The
# credential command (keysource's command kind) is selected by the same door and is removed with its
# tuning variables below (_CREDENTIAL_VARS).
os.environ.pop("ROMP_API_KEY_REF", None)
# Every shell under a romp-managed session inherits ROMP_SUPERVISED=1 from the kernel (the service
# unit exports it), and keysource gives that variable authority: a supervised manager reads the env
# file only and ignores a startup key. Twenty-five tests that stage a startup key went red when the
# suite ran from inside a romp session while CI stayed green (review find, 2026-09-05). The floor is
# the unsupervised case; a test that wants supervision sets the variable itself.
os.environ.pop("ROMP_SUPERVISED", None)


def _reset_keysource_state():
    """keysource remembers which path selected which source for the PROCESS (that is the resurrection
    guard); under one pytest process that memory would leak between test modules. Every loaded copy of
    the module (each SourceFileLoader name is its own module object) is reset."""
    import sys
    for name, m in list(sys.modules.items()):
        if "keysource" in name and hasattr(m, "_AUTHORITATIVE_PATHS"):
            m._AUTHORITATIVE_PATHS.clear()
            getattr(m, "_ENV_PROVIDER_PATHS", set()).clear()
            m._CACHE = ((), "")


def _reset_envsource_state():
    """envsource (the command kind's runtime, kernel/envsource.py) caches the set the last command run
    printed, keyed on the source and the selector file; under one pytest process a set one module's
    fake command printed would otherwise be served to the next module's first read. Every loaded copy
    is reset beside keysource's."""
    import sys
    for name, m in list(sys.modules.items()):
        if "envsource" in name and callable(getattr(m, "_reset", None)) and hasattr(m, "SELECTOR_FILE_VAR"):
            m._reset()


@pytest.fixture(autouse=True)
def _no_real_service_env():
    """Re-asserted, not defaulted: a module-level write in one test file executes during collection
    and would otherwise hold for the whole run. A test that needs its own env file points the vars at
    a temp path in setUp, which runs AFTER this fixture (pytest fills fixtures in the item's setup
    phase, before TestCase.run calls setUp) — so per-test intent still wins."""
    for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
        os.environ[var] = _NO_SERVICE_ENV
    os.environ.pop("ROMP_API_KEY_REF", None)
    os.environ.pop("ROMP_SUPERVISED", None)
    _reset_keysource_state()
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
# Per-test re-assert below, on the same reasoning as the manager-port floor. The per-session limits
# (ROMP_CLI_SCOPE_MEMORY_MAX and the others, sdk_backend.CLI_SCOPE_LIMITS) are floored to unset the same
# way: the kernel hands them to every session's CLI, whose tool shells inherit them, so a suite run from a
# session on a self-hosted romp with limits in service.env would see them at every backend construction
# and in every exact argv pin.
os.environ["ROMP_CLI_SCOPE"] = "0"
_CLI_SCOPE_LIMIT_VARS = ("ROMP_CLI_SCOPE_MEMORY_MAX", "ROMP_CLI_SCOPE_MEMORY_HIGH", "ROMP_CLI_SCOPE_MEMORY_SWAP_MAX",
                         "ROMP_CLI_SCOPE_OOM_SCORE_ADJ")
for _v in _CLI_SCOPE_LIMIT_VARS:
    os.environ.pop(_v, None)


@pytest.fixture(autouse=True)
def _no_cli_scope():
    os.environ["ROMP_CLI_SCOPE"] = "0"
    for v in _CLI_SCOPE_LIMIT_VARS:
        os.environ.pop(v, None)
    yield


# No test may run the REAL credential command: kernel/envsource.py runs the command keysource selects
# (ROMP_CREDENTIAL_COMMAND, an installation's secret-store command) at backend construction and on
# every stale read, and a self-hosted romp's tool shells inherit the manager's environment, variable
# included. Popped, so every test starts with no command source, no names and the default timeout; a
# test that exercises the command source writes its own fake script and builds or sets what it needs
# in setUp (which runs after this fixture). Popped rather than blanked: keysource selects the command
# kind by the variable's PRESENCE at the environment door, as it does the reference, so an empty value
# is an explicit, invalid choice rather than an absent one. Import-time for collection, per-test
# re-assert below, on the same reasoning as the manager-port floor. The env-file floor above already
# keeps the same lines from being read out of the real service.env.
_CREDENTIAL_VARS = ("ROMP_CREDENTIAL_COMMAND", "ROMP_CREDENTIAL_NAMES", "ROMP_CREDENTIAL_TIMEOUT_S")
for _v in _CREDENTIAL_VARS:
    os.environ.pop(_v, None)

# ...and no test may read the REAL selector file: envsource.selector_path defaults to
# ${XDG_CONFIG_HOME:-~/.config}/romp/credential-selector, so a command-source test that wrote its fake
# command and forgot this variable would read this machine's selector file (its token as `$1`, its
# stat identity in the cache key) and pass or fail on what the box had selected. FLOORED to a path
# under the state root that is never created, not popped like the three above: an absent variable is
# the one unsafe state here, since absent means the default. The "no selector" case is the result
# (read_selector() answers ("", ""), the command runs with an empty `$1`), exactly as on a box that
# never ran `romp keyswap <name>`. A test that needs a selector points the variable at a temp path in
# setUp, which runs after the fixture; tests/test_envsource.py's Floor class pins this.
_NO_SELECTOR = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-credential-selector")
os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = _NO_SELECTOR


@pytest.fixture(autouse=True)
def _no_credential_command():
    for var in _CREDENTIAL_VARS:
        os.environ.pop(var, None)
    os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = _NO_SELECTOR
    _reset_envsource_state()
    yield


_SELECTOR_FLOOR_VIOLATION = None   # the refusal below, held for pytest_runtest_setup when this process is an xdist worker


def _selector_floor_violation():
    """The refusal's text when ROMP_CREDENTIAL_SELECTOR_FILE is absent or names a file that exists; None
    while the floor holds."""
    p = os.environ.get("ROMP_CREDENTIAL_SELECTOR_FILE") or ""
    if p and not os.path.exists(p):
        return None
    return ("ROMP_CREDENTIAL_SELECTOR_FILE is %s after collection: a test module popped it, or pointed it at a "
            "real file, at import. Floor it at module level to a path that does not exist, as tests/conftest.py "
            "and tests/test_envsource.py do." % ("absent" if not p else "a path that exists (%s)" % p))


def pytest_collection_finish(session):
    """The import-time half of the selector floor, checked where it can fail: collection runs every test
    module's top level after the floor above, and a module that pops ROMP_CREDENTIAL_SELECTOR_FILE there
    (or points it at a file that exists) undoes the floor for every module collected after it. A later
    module reading the selector at import would read the developer's own selector file, the read the
    floor exists to prevent, before any per-test re-assert runs. Refused here, naming the fix, rather
    than left to pass on what the box has selected.

    Refused two ways, because a pytest-xdist worker cannot refuse here. The controller never collects
    (xdist skips its collection), so this hook runs only in the workers, and a UsageError raised there
    ends the worker before it reports anything: the controller then dies on an internal assertion,
    forty lines that never name the variable or the fix. In a worker the refusal is held instead, and
    every item fails at setup with it (pytest_runtest_setup below), which the controller reports as it
    reports any failure. When nothing is selected (a `-k` that deselects everything) no setup runs, so
    the worker asks for the stop itself: session.shouldfail, the field `-x` sets, which xdist carries
    to the controller at the worker's finish and the controller reports as `Interrupted: <the
    refusal>`, exit status 2 (otherwise the held refusal goes unreported and the run ends `no tests
    ran`, exit status 5, saying nothing). session.items is final by this hook (deselection runs in
    pytest_collection_modifyitems, before it) and the same on every worker, so an empty list means no
    item can run anywhere; a worker the scheduler happens to give no item while others run theirs
    says nothing, since their items carry it. Serially the UsageError stands: one line, nothing runs,
    a `-k` that deselects everything included; `--collect-only` is serial too, xdist leaves it alone.
    tests/test_envsource.py's Floor class pins all three."""
    global _SELECTOR_FLOOR_VIOLATION
    msg = _selector_floor_violation()
    if msg is None:
        return
    if hasattr(session.config, "workerinput"):     # an xdist worker: the message would die with the process
        _SELECTOR_FLOOR_VIOLATION = msg
        if not session.items:                      # nothing will reach pytest_runtest_setup
            session.shouldfail = msg
        return
    raise pytest.UsageError(msg)


def pytest_runtest_setup(item):
    """The worker half of the refusal above when items were selected: every item fails with the message,
    none runs."""
    if _SELECTOR_FLOOR_VIOLATION:
        pytest.fail(_SELECTOR_FLOOR_VIOLATION, pytrace=False)


# No test may reach the machine's REAL tmux server (2026-09-06): keysource.claim_op_env scrubs the tmux
# server's globals the moment romp becomes the op consumer, which any test that configures a reference
# and constructs the SDK backend (or resolves a key) does — and on a developer's box that `tmux
# set-environment -gu` would land on the live server every session runs in. The same private socket
# directory the bats suites use (tests/tmux-private.bash): tmux puts every socket, `-L` ones included,
# under $TMUX_TMPDIR/tmux-<uid>/, and the directory must exist or tmux 3.4 silently falls back to the
# default. No server ever exists there, so a scrub from a test exits with "no server running".
os.environ["TMUX_TMPDIR"] = tempfile.mkdtemp(prefix="romp-tests-tmux-")
os.environ.pop("TMUX", None)
os.environ.pop("ROMP_TMUX_SOCKET", None)


@pytest.fixture(autouse=True)
def _no_live_tmux_server():
    os.environ["TMUX_TMPDIR"] = _TMUX_PRIVATE
    yield


_TMUX_PRIVATE = os.environ["TMUX_TMPDIR"]


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
