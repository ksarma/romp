"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import atexit
import importlib.util
import os
import shutil
import sys
import tempfile

import pytest

# Temp-directory hygiene, the child-process half (2026-09-06): every temp path a run creates lives
# under ONE private root, removed when the run ends. tests/__init__.py's mkdtemp hook (the other
# half; its comment has the leak's history) records and removes what THIS process mints through
# tempfile.mkdtemp, but a test's children — kernels, git, `mktemp -d` in a shell — and mkstemp or
# os.mkdir paths are outside its sight (a full run left ~5,600 of those per run at up to ten a
# second). So the process's temp dir is redirected: tempfile.tempdir is set directly (gettempdir()
# caches its first answer, and tests/__init__.py has already called it by the time this runs), and
# TMPDIR is exported so every child inherits the same root. Import-time, not pytest_configure: this
# module's own XDG floor below and every module-level mkdtemp at collection must land inside it.
# The two removals compose without overlap: pytest_sessionfinish runs the hook's sweep, whose scope
# is gettempdir() and so the inside of this root; pytest_unconfigure then removes the root whole
# (whatever the sweep could not see) and tests/__init__.py's romp-tests-state-* dir — the package
# imports first, so that dir and this root were minted before the redirect and are the two things a
# run puts outside the root; the hook recorded both but skips them as outside its scope. Under
# pytest-xdist both hooks run in the controller and in every worker: each imported this file and so
# owns a root of its own (a worker's sits inside the controller's, since it inherits that TMPDIR).
# The atexit registrations are silent fallbacks for a normal exit that skipped the hooks, each a
# no-op on what the other removed; nothing runs after an os._exit (pytest-timeout's thread method
# ends a hung run that way), so a hang leaves two top-level entries in the system temp dir, this
# root and that state dir, both under the romp-tests- prefix.
# The system temp dir — the one the RUN was handed, before any redirect — is recorded once, by the
# first conftest to import: an xdist worker inherits the controller's record along with its TMPDIR
# (setdefault, not an assignment: a worker's own gettempdir() is the controller's root, and
# recording that put the worker's fallback one level deeper than a socket path can bear under a
# long TMPDIR — four socket tests failed at bind under -n 2, 2026-09-06). A test that must leave
# the root (an AF_UNIX socket path that would not fit sun_path under a nested root) falls back to
# it, and only to it — a literal system path in a `dir=` would bypass the redirect (one did).
os.environ.setdefault("ROMP_TESTS_SYSTEM_TMPDIR", tempfile.gettempdir())
_TMP_ROOT = tempfile.mkdtemp(prefix="romp-tests-")
tempfile.tempdir = _TMP_ROOT
os.environ["TMPDIR"] = _TMP_ROOT
_PACKAGE_STATE_DIR = getattr(sys.modules.get("tests"), "STATE_DIR", None)


def _remove_run_dirs(report=False):
    """Remove the root and the package state dir. A survivor is named on stderr when asked: rmtree
    with ignore_errors swallows a child still writing under the root or a 000-mode directory a test
    left behind, and the run would otherwise end green with the root standing. Only unconfigure
    asks; the atexit fallback stays silent so it neither repeats the notice nor contradicts it."""
    for d in (_TMP_ROOT, _PACKAGE_STATE_DIR):
        if d:
            shutil.rmtree(d, ignore_errors=True)
            if report and os.path.isdir(d):
                print("[tests] not removed at run end: %s" % d, file=sys.stderr)


atexit.register(_remove_run_dirs)


def pytest_sessionfinish(session, exitstatus):
    """The in-process half (tests/__init__.py): remove every directory this process made through
    tempfile.mkdtemp inside the root, this module's state root included. The package's atexit hook
    does the same at interpreter exit; both are idempotent, and pytest_unconfigure below takes the
    root itself afterwards."""
    try:
        from tests import remove_made_dirs
    except Exception:
        return
    remove_made_dirs()


def pytest_unconfigure(config):
    _remove_run_dirs(report=True)


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

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")   # inside the root; the hook records it
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


# No test may run the REAL credential command (2026-09-05): kernel/envsource.py runs
# ROMP_CREDENTIAL_COMMAND — an installation's secret-store command — at backend construction and on every
# stale read, and a self-hosted romp's tool shells inherit the manager's environment, variable
# included. Popped, so every test starts in file mode with no command, no names and the default
# timeout; a test that exercises the command source writes its own fake script and sets the
# variables in setUp (which runs after this fixture). Import-time for collection, per-test re-assert
# below, on the same reasoning as the manager-port floor. The env-file floor above already keeps the
# same lines from being read out of the real service.env.
_CREDENTIAL_VARS = ("ROMP_CREDENTIAL_COMMAND", "ROMP_CREDENTIAL_NAMES", "ROMP_CREDENTIAL_TIMEOUT_S")
for _v in _CREDENTIAL_VARS:
    os.environ.pop(_v, None)

# ...and no test may read the REAL selector file (2026-09-06): envsource.selector_path defaults to
# ${XDG_CONFIG_HOME:-~/.config}/romp/credential-selector, so a command-mode test that wrote its fake
# command and forgot this variable read this machine's mode file — its token as `$1`, its stat
# identity in the cache key — and passed or failed on what the box had selected. FLOORED to a path
# under the state root that is never created, not popped like the three above: an absent variable is
# the one unsafe state here, since absent means the default. The "no selector" case is the result —
# read_selector() answers ("", ""), the command runs with an empty `$1` — exactly as on a box that
# never ran `romp keyswap <name>`. A test that needs a selector points the variable at a temp path in
# setUp, which runs after the fixture; tests/test_envsource.py's Floor class pins this.
_NO_SELECTOR = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-credential-selector")
os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = _NO_SELECTOR


@pytest.fixture(autouse=True)
def _no_credential_command():
    for var in _CREDENTIAL_VARS:
        os.environ.pop(var, None)
    os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = _NO_SELECTOR
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
    (or points it at a file that exists) undoes the floor for every module collected after it — a
    later module reading the selector at import would read the developer's own mode file, the read the
    floor exists to prevent, before any per-test re-assert runs. Refused here, naming the fix, rather
    than left to pass on what the box has selected (2026-09-06: tests/test_envsource.py popped it at
    import, from before the floor existed).

    Refused two ways, because a pytest-xdist worker cannot refuse here. The controller never collects
    (xdist skips its collection), so this hook runs only in the workers, and a UsageError raised there
    ends the worker before it reports anything: the controller then died on an internal assertion,
    forty lines that never named the variable or the fix (2026-09-06, under `-n 8`). In a worker the
    refusal is held instead, and every item fails at setup with it (pytest_runtest_setup below), which
    the controller reports as it reports any failure. When nothing is selected (a `-k` that deselects
    everything) no setup runs, so the worker asks for the stop itself: session.shouldfail, the field
    `-x` sets, which xdist carries to the controller at the worker's finish and the controller reports
    as `Interrupted: <the refusal>`, exit status 2 (2026-09-06: the held refusal went unreported and
    the run ended `no tests ran`, exit status 5, saying nothing). session.items is final by this hook
    (deselection runs in pytest_collection_modifyitems, before it) and the same on every worker, so an
    empty list means no item can run anywhere; a worker the scheduler happens to give no item while
    others run theirs says nothing, since their items carry it. Serially the UsageError stands: one line,
    nothing runs, a `-k` that deselects everything included; `--collect-only` is serial too, xdist
    leaves it alone. tests/test_envsource.py's Floor class pins all three."""
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


# No test may read the REAL service unit, launchd plist or Claude Code settings (2026-09-05):
# constructing the SDK backend takes the key-source verdict (sdk_backend.key_source_verdict), which
# reads the systemd unit and its drop-ins, the launchd plist and $CLAUDE_CONFIG_DIR/settings*.json —
# so every backend construction in the suite would otherwise read this machine's unit and the
# developer's own apiKeyHelper setting (and envsource.helper_fingerprint could RUN that helper). The
# three are floored to empty temp dirs under the state root: no unit, no plist, no settings. The one
# test that deliberately borrows the user's own apiKeyHelper command (the opt-in live move test)
# reads the pre-floor location through ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR, set here once. Import-time
# plus a per-test re-assert, on the same reasoning as the manager-port floor; a test that needs its
# own dirs points the vars at temp paths in setUp, which runs after the fixture.
_EMPTY_DIRS = {
    "ROMP_SYSTEMD_DIR": os.path.join(os.environ["XDG_STATE_HOME"], "floor-systemd-user"),
    "ROMP_LAUNCHD_DIR": os.path.join(os.environ["XDG_STATE_HOME"], "floor-launch-agents"),
    "CLAUDE_CONFIG_DIR": os.path.join(os.environ["XDG_STATE_HOME"], "floor-claude-config"),
}
os.environ.setdefault("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
                      os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))
for _v, _d in _EMPTY_DIRS.items():
    os.makedirs(_d, exist_ok=True)
    os.environ[_v] = _d


@pytest.fixture(autouse=True)
def _no_real_unit_or_settings():
    for var, d in _EMPTY_DIRS.items():
        os.environ[var] = d
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


# No test report may carry a process-environment VALUE, or a credential-shaped token (2026-09-05). A
# test that renders an env mapping in an assertion (assertNotIn on os.environ, on a _judge_env() copy
# of it, on a launch env) prints the whole mapping when it fails, and on a developer's box that
# mapping holds live credentials; the assertion rules below are the fix, this hook is the safety net
# for the next test nobody remembered to write that way. Two nets, applied to every report's text
# (the longrepr and the captured-output sections) whatever the outcome, and to collection reports:
#   * every value seen in this process's environment, 16 characters or longer, is replaced with one
#     marker, and so is each whitespace-separated chunk of such a value that is 16 characters or
#     longer (pprint renders a value with spaces as adjacent literals on separate lines, so a
#     whole-value replace misses the pieces). Values are noted the moment they are WRITTEN into
#     os.environ (the mutation path is wrapped below: a plain assignment, update, setdefault,
#     os.putenv, os.environb, mock.patch.dict), and sampled at import, around each test and at
#     report time as well, for values that entered by another route (inherited from the parent
#     process, written by a C extension). Path-valued shell variables a traceback quotes
#     legitimately (the cwd, the state root) are exempt by NAME, and never when the name is
#     credential-shaped.
#   * credential-shaped tokens by PATTERN (tests/credential_patterns.py: the public key prefixes, and
#     a long token in a value position), whatever their provenance: a token that never touched the
#     environment (read from a file, printed by a child) is caught by this one.
# A report the hook changes becomes plain text (no colour); one it leaves alone keeps pytest's own
# rendering.
ENV_VALUE_MIN_LEN = 16
ENV_VALUE_REDACTED = "[REDACTED-ENV-VALUE]"
_ENV_VALUE_PATH_NAMES = frozenset((
    "PWD", "OLDPWD", "HOME", "PATH", "TMPDIR", "SHELL", "VIRTUAL_ENV", "PYTHONPATH", "LS_COLORS",
    "XDG_STATE_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR",
    "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ROMP_DIR", "ROMP_STATE_DIR", "ROMP_CLAUDE_BIN",
    "ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR", "CLAUDE_CONFIG_DIR", "ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
    "ROMP_CREDENTIAL_SELECTOR_FILE"))
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


def env_value_qualifies(name: str, value: str) -> bool:
    """Whether one environment entry's value is one a report must not show: ENV_VALUE_MIN_LEN
    characters or more, unless the name is a path-valued shell variable that is not credential-shaped.
    The one rule, for the sampler and for the write hook."""
    if len(value) < ENV_VALUE_MIN_LEN:
        return False
    return not (name in _ENV_VALUE_PATH_NAMES and not _credential_shaped(name))


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


def redact_env_values(text: str, values) -> str:
    """`text` with every occurrence of every value replaced by ENV_VALUE_REDACTED, longest first (a
    value that contains another is replaced whole), and then every whitespace-separated chunk of a
    value that is ENV_VALUE_MIN_LEN characters or more: pprint renders a long value with spaces as
    adjacent string literals on separate lines, so the token half of `Authorization: Bearer <token>`
    survived a whole-value replace, and unittest's shortened repr shows a differing tail on its own."""
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
    return text


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


def _redact_report(rep) -> None:
    """Every text a report carries, whatever its outcome: the longrepr (a failure's text; a skip's is
    a (path, line, reason) tuple, whose reason is the text) and the captured-output sections (which
    -rA and -rP print for passed tests too). A longrepr the nets leave unchanged keeps pytest's own
    object and rendering."""
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
            rep.longrepr = red
    if getattr(rep, "sections", None):
        rep.sections = [(name, redact_report_text(content)) for name, content in rep.sections]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    _redact_report(outcome.get_result())


@pytest.hookimpl(hookwrapper=True)
def pytest_collectreport(report):
    """A collection error (an import-time exception whose message names a value) is a report too.
    Redacted BEFORE the other implementations see it: the terminal reporter files it from here."""
    _redact_report(report)
    yield
