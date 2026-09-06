"""envsource — a credential set from a configured COMMAND, handed to each child at launch and never
written to the kernel's own environment or to any file.

The file source (keysource.py) reads `ANTHROPIC_API_KEY=` out of the manager's env file. Some
installations forbid a credential in any file. For them this module is the source instead:
`ROMP_CREDENTIAL_COMMAND` (a non-secret shell command, set in the same env file or a systemd
drop-in) is run by the kernel, prints `NAME=VALUE` lines, and the resulting SET is merged into
the launch environment of every session CLI, every judge call and the catalog fetch. Setting the
variable is what selects this mode; unset, nothing here runs and every caller sees an empty set.

Configuration (process environment first, then the same line in the manager's env file, so a
terminal outside the manager tree resolves the same values). Every reader takes an optional
`environ`, and an explicit one stands in for the process ENVIRONMENT only: the env file consulted
after it is still the process's (`ROMP_SERVICE_ENV_FILE`, else the default under `XDG_CONFIG_HOME` or
`HOME`, keysource's rule), so `command({})` is the file's line alone — the probe `romp keyswap` uses
to tell a line set in the shell from one set in the file. A check that must be pure on its inputs
(sdk_backend.key_source_verdict on a hypothetical environ) therefore does not decide its mode through
these readers: it takes the env file's TEXT as an input and reads the line from that (2026-09-06).

* `ROMP_CREDENTIAL_COMMAND` — run as `/bin/sh -c <command> sh <selector>`, so the selector is `$1`.
* `ROMP_CREDENTIAL_SELECTOR_FILE` — a file holding ONE token (a name such as `hp`), passed as `$1`.
  Default `${XDG_CONFIG_HOME:-~/.config}/romp/credential-selector`.
* `ROMP_CREDENTIAL_NAMES` — the comma list of selector names an operator may pick. A token outside
  the list is refused before the command runs.
* `ROMP_CREDENTIAL_TIMEOUT_S` — how long one run may take (default 15; a value that is not a number
  between 0 and 300 is refused with one problem line, and the default holds).

The MODE is pinned when the kernel's backend is constructed (`pin_mode`): a configuration edit
reaches the kernel at its next start, never a running one, so a kernel is never half in one mode.
Which restart that is depends on where the kernel finds the variable. A line ADDED to `service.env`
is read by the next kernel (`romp refresh`), since the kernel reads the file itself. A line REMOVED
from `service.env` under the installed service is still in the manager's environment (systemd
loaded the file into it when the manager started, and every kernel inherits that environment), so
leaving command mode takes a manager restart (`systemctl --user restart romp-manager`, or the
platform's equivalent); `romp refresh` restarts kernels only, and a new kernel inherits the
variable. The same holds for the other values (the selector file, the names, the timeout, the
command's text): they are read live, the environment first, so a service.env line the manager's
environment already carries is shadowed by that copy until the manager restarts, while a line the
environment does not carry is read from the file at once. A terminal's `romp keyswap` never pins.

Output contract: `ANTHROPIC_API_KEY` (optional) is the work key; `ANTHROPIC_LP_API_KEY` the direct-
call key; any other name is a role variable for the sessions' shells. Names starting with `ROMP_`
are dropped (romp owns them), and so are the names the CLI reads as its own authentication or
endpoint (`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`,
`ANTHROPIC_CUSTOM_HEADERS`): a set that carried one would re-route or re-bill every session behind
the one door this module keeps for the key; each drop is one problem line naming the names. The parsing rule is keysource's, generalised to every name: blank
and `#` lines skipped, `NAME=value` (an `export ` prefix is accepted here — romp's own contract for
the command's output, not the env file's), last assignment wins, one layer of matching quotes
stripped; lines are split on newlines only, and a value with a NUL is a bad line, never injected.

Three properties this module holds, the same three keysource.py holds:

* **Values never land in `os.environ`.** They live in one private dict here and leave it through
  exactly one accessor, `injection()`, whose callers merge them into a CHILD's environment.
* **Values never reach a log, a screen or a wire.** Every other function returns names, counts,
  exit codes and fingerprints (`sha256` head, 12 hex). Failure reasons carry counts and exit codes
  only ("exited 3 after 0.4s, stderr 87 bytes") — the command's stdout and stderr bytes are never
  quoted, since a command that echoes a credential to stderr would otherwise leak it into the log.
* **A failed run keeps the previous set, and is not served like a good one.** A successful run is
  cached with no timer: it holds until `invalidate()` (an operator's refresh, a cycle, an
  authentication failure in a judge call or a session) or until the selector file's own stat
  identity changes (a hand edit of a shared mode file is an event). After a failed run the NEXT
  caller re-runs the command — one run per caller — so an installation whose secret store was
  briefly unreachable recovers at the next launch or call without an operator action; between
  runs the previous set stands and the record says `stale`. Concurrent callers coalesce on one
  lock — a boot that revives many sessions runs the command once, not once per session — and a
  caller arriving mid-run takes that run's result, good or bad, rather than running again. Every
  record carries `attempt`, the ordinal of the run or refusal that produced it (the callers that
  coalesced on one run share it), so a reader that holds two records knows which is the newer.

The apiKeyHelper fingerprint lives here too: on an installation whose set carries no work key the
sessions authenticate through Claude Code's own `apiKeyHelper`, and the kernel never sees that
value. To tell whether a running session is on the current credential, `helper_fingerprint()` runs
the configured helper with the same runner — in the environment a session CLI gets (the set's role
variables merged, `ROMP_SID` absent) — and hashes its output inside this function; the bytes never
leave it. The result is cached for the set it ran with, identified by the record's `generation` and
`setSeq` (the second moves when a run hands back a different set under one generation), and an
entry is never written over a newer one.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import selectors
import signal
import subprocess
import tempfile
import threading
import time
from importlib.machinery import SourceFileLoader as _SFL
from pathlib import Path

# The file source's module, loaded the way sdk_backend loads it (one module object under one name),
# for the env-file path both sources share. Its own parser is key-specific; the generalised rule
# below is pinned equal to it by tests/test_envsource.py.
_keysrc = _SFL("romp_keysource", str(Path(__file__).resolve().parent / "keysource.py")).load_module()

COMMAND_VAR = "ROMP_CREDENTIAL_COMMAND"
SELECTOR_FILE_VAR = "ROMP_CREDENTIAL_SELECTOR_FILE"
NAMES_VAR = "ROMP_CREDENTIAL_NAMES"
TIMEOUT_VAR = "ROMP_CREDENTIAL_TIMEOUT_S"
CONFIG_VARS = (COMMAND_VAR, SELECTOR_FILE_VAR, NAMES_VAR, TIMEOUT_VAR)
DEFAULT_TIMEOUT_S = 15.0
MAX_TIMEOUT_S = 300.0                  # a longer deadline is a misconfiguration: the default holds, said once
EXIT_GRACE_S = 0.2                     # after the command exits, how long a pipe a leftover child holds is read

KEY_VAR = "ANTHROPIC_API_KEY"          # the work key, when the set carries one
LP_KEY_VAR = "ANTHROPIC_LP_API_KEY"    # the direct-call key (the catalog fetch)
RESERVED_PREFIX = "ROMP_"              # names romp owns: dropped from any set
AUTH_NAMES = ("ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",      # names the CLI treats as its authentication
              "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS")       # or its endpoint: dropped from any set

NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")                 # the shell-identifier alphabet
SELECTOR_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")     # one token: a name, never a value
TOKEN_RE = re.compile(r"[\x21-\x7e]+\Z")                          # the CLI's helper-output contract

FP_HEX = 12


# ---------------------------------------------------------------------------
# Configuration — the process environment first, then the manager's env file.
# ---------------------------------------------------------------------------

_FILE_CFG: tuple = ((), {})     # (stat identity, parsed lines) of the env file — event-keyed on the file


def service_env_path() -> str:
    """The manager's env file — keysource's answer, so both sources always name one file."""
    return _keysrc.service_env_path()


_EXPORT_RE = re.compile(r"export[ \t]+(.*)\Z", re.S)


def parse_lines(text, allow_export: bool = False) -> tuple[dict, int, int]:
    """Every assignment an env-file body (or a command's stdout) makes: {NAME: value}, plus the count
    of lines that are not `NAME=value` and the count of assignments whose value is empty. Blank and
    `#` lines are skipped, the LAST assignment of a name wins, and one layer of matching quotes is
    stripped — keysource.parse_key's rule for one name, applied to all of them (pinned equal by
    test). An empty value is dropped: for the key that is "no key", for a role variable a var the
    child would see set-but-empty, which for the CLI's own key var means "key mode, no key".

    Lines are split on newlines only (CRLF normalised first) — never str.splitlines(), which also
    splits on \\x0b, \\x0c, \\x1c-\\x1e and the Unicode separators, so a value carrying one of those
    would have been injected truncated. A value with a NUL is a bad line: no environment can carry
    it, and a launch must not die on it. With `allow_export` an `export NAME=value` line is the
    assignment it names — the command-output contract (parse_set); the env file keeps the plain
    form the launchers and systemd read."""
    out: dict = {}
    bad = empty = 0
    for raw in str(text or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if allow_export:
            m = _EXPORT_RE.match(line)
            if m:
                line = m.group(1).strip()
        name, sep, value = line.partition("=")
        name = name.strip()
        if not sep or not NAME_RE.match(name) or "\x00" in value:
            bad += 1
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not value:
            empty += 1
            out.pop(name, None)
            continue
        out[name] = value
    return out, bad, empty


def _file_config() -> dict:
    """The env file's assignments, cached on the file's own stat identity (a rewrite invalidates by
    construction). {} for a missing or unreadable file."""
    global _FILE_CFG
    p = service_env_path()
    try:
        st = os.stat(p)
        ident = (p, st.st_ino, st.st_mtime_ns, st.st_size)
    except OSError:
        _FILE_CFG = ((p, "absent"), {})
        return {}
    if _FILE_CFG[0] == ident:
        return _FILE_CFG[1]
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            vals, _bad, _empty = parse_lines(fh.read())
    except OSError:
        vals = {}
    _FILE_CFG = (ident, vals)
    return vals


def config_value(name: str, environ=None) -> str:
    """One configuration value: the environment's, else the env file's line, else "". An explicit
    `environ` replaces the process environment; the file is the process's either way (the module
    docstring: `command({})` is the file's line alone, and keyswap's mode probe reads it that way)."""
    env = os.environ if environ is None else environ
    v = (env.get(name) or "").strip()
    if v:
        return v
    return (_file_config().get(name) or "").strip()


def command(environ=None) -> str:
    return config_value(COMMAND_VAR, environ)


_MODE_PIN: bool | None = None      # pin_mode()'s verdict for THIS process's environment; None = unpinned (live)


def pin_mode() -> bool:
    """Decide the mode ONCE for this process, from the live configuration, and hold it: the kernel
    calls this at backend construction, so a configuration edit that adds or removes the command
    line cannot flip a running kernel into or out of command mode (its sessions, judges and catalog
    would otherwise change key source mid-life, half of them on each side). The next kernel decides
    afresh: after `romp refresh` for a line added to `service.env`; after a manager restart for a
    line removed from it under the installed service, whose manager environment still carries the
    variable (see the module docstring). Returns the pinned verdict."""
    global _MODE_PIN
    _MODE_PIN = bool(command(None))
    return _MODE_PIN


def configured(environ=None) -> bool:
    """Whether the command source is selected — the ONE mode switch: a non-empty command. For the
    process's own environment the pinned verdict (pin_mode) answers once it exists; an explicit
    environ is a hypothetical (the pure verdict, a test) and is always read as given."""
    if _MODE_PIN is not None and (environ is None or environ is os.environ):
        return _MODE_PIN
    return bool(command(environ))


def selector_path(environ=None) -> str:
    p = config_value(SELECTOR_FILE_VAR, environ)
    if p:
        return os.path.expanduser(p)
    env = os.environ if environ is None else environ
    base = (env.get("XDG_CONFIG_HOME") or "").strip() or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "romp", "credential-selector")


def names(environ=None) -> list:
    """The declared selector names, in order, de-duplicated; [] when none are declared."""
    out: list = []
    for tok in config_value(NAMES_VAR, environ).split(","):
        tok = tok.strip()
        if tok and tok not in out:
            out.append(tok)
    return out


def _timeout_value(environ) -> tuple:
    """(seconds, problem): the configured deadline, or the default with a one-line reason when the
    setting is not a number in (0, MAX_TIMEOUT_S] — junk, zero, negative, inf, nan, or longer than
    a launch should ever wait. The reason names the variable, never its text."""
    raw = config_value(TIMEOUT_VAR, environ)
    if not raw:
        return DEFAULT_TIMEOUT_S, ""
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = math.nan
    if not math.isfinite(v) or v <= 0 or v > MAX_TIMEOUT_S:
        return DEFAULT_TIMEOUT_S, ("%s is not a number of seconds between 0 and %g; the default %gs holds"
                                   % (TIMEOUT_VAR, MAX_TIMEOUT_S, DEFAULT_TIMEOUT_S))
    return v, ""


def timeout_s(environ=None) -> float:
    return _timeout_value(environ)[0]


def timeout_problem(environ=None) -> str:
    """"" when ROMP_CREDENTIAL_TIMEOUT_S is usable (or unset), else the one problem line's text."""
    return _timeout_value(environ)[1]


# ---------------------------------------------------------------------------
# The selector file — one token, read and written atomically.
# ---------------------------------------------------------------------------

def valid_selector(token) -> bool:
    return bool(isinstance(token, str) and SELECTOR_RE.match(token))


def selector_allowed(token: str, environ=None) -> bool:
    """Whether `token` may be selected by `romp keyswap <name>`: a valid token AMONG THE DECLARED
    NAMES. With nothing declared no name may be selected — a selector is only ever rendered by name
    when it is declared, so an undeclared one could be anything, a pasted secret included. The
    token itself is never part of any message built from a refusal."""
    return bool(valid_selector(token) and token in names(environ))


def selector_label(snap: dict) -> str:
    """The one renderable form of the selector in a record: the token when it is declared in
    ROMP_CREDENTIAL_NAMES, else `(undeclared, N chars)` — a length, never the text — else ""."""
    return (snap or {}).get("selector") or (snap or {}).get("selectorNote") or ""


def _selector_ident(environ=None) -> tuple:
    """The selector file's stat identity (path, inode, mtime_ns, size) — part of the cache identity,
    so a hand edit of a shared mode file re-runs the command without anyone calling invalidate()."""
    p = selector_path(environ)
    try:
        st = os.stat(p)
        return (p, st.st_ino, st.st_mtime_ns, st.st_size)
    except OSError:
        return (p, "absent")


def read_selector(path=None, environ=None) -> tuple:
    """(token, error). A missing file is ("", "") — no selector, the command runs with an empty `$1`.
    An unreadable file or one whose content is not a single token is an error; the error carries a
    byte count, never the content (a credential pasted into the selector file must not be echoed)."""
    p = path or selector_path(environ)
    try:
        with open(p, "rb") as fh:
            raw = fh.read(4096)
    except FileNotFoundError:
        return "", ""
    except OSError as e:
        return "", "the selector file could not be read (errno %s)" % getattr(e, "errno", "?")
    tok = raw.decode("utf-8", "replace").strip()
    if not tok:
        return "", ""
    if not valid_selector(tok):
        return "", "the selector file holds something that is not a name (%d bytes)" % len(raw)
    return tok, ""


def write_selector(token: str, path=None, environ=None) -> dict:
    """Write ONE token to the selector file, atomically (mkstemp in the same directory, fsync,
    os.replace), through a symlink so a dotfiles-managed link keeps pointing at its target. The
    directory is created if missing. ValueError for a token that is not a name; OSError on a real
    failure. Returns {"path", "target", "old", "new"} — names, never values."""
    if not valid_selector(token):
        raise ValueError("a selector is one name: letters, digits, '.', '_' or '-', up to 64 characters")
    given = path or selector_path(environ)
    p = os.path.realpath(given) if os.path.islink(given) else given
    old, _err = read_selector(p)
    d = os.path.dirname(p) or "."
    os.makedirs(d, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(p) + ".selector.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(token + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return {"path": given, "target": p, "old": old, "new": token}


# ---------------------------------------------------------------------------
# Fingerprints — the only renderable form of a value.
# ---------------------------------------------------------------------------

def fingerprint(value) -> str:
    """The first 12 hex of the sha256 of a value, "" for none — keysource.fingerprint's rule, so a
    key fingerprinted here and a key fingerprinted there read the same."""
    value = str(value or "")
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8", "replace")).hexdigest()[:FP_HEX]


def set_fingerprint(values) -> str:
    """One fingerprint for a whole set: sha256 over the sorted `NAME=value` lines, "" for an empty
    set. Any change to any name or value changes it; two sets with the same content agree."""
    if not values:
        return ""
    body = "\n".join("%s=%s" % (k, values[k]) for k in sorted(values))
    return hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()[:FP_HEX]


# ---------------------------------------------------------------------------
# The runner.
# ---------------------------------------------------------------------------

class RunResult:
    """One run of a command: exit code, stdout bytes (for the parser only), the LENGTH of stderr,
    the duration and whether it was killed on the deadline. `reason` renders the failure with counts
    and exit codes only."""

    __slots__ = ("returncode", "stdout", "stderr_len", "duration_s", "timed_out", "start_error")

    def __init__(self, returncode, stdout, stderr_len, duration_s, timed_out=False, start_error=None):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr_len = stderr_len
        self.duration_s = duration_s
        self.timed_out = timed_out
        self.start_error = start_error

    @property
    def ok(self) -> bool:
        return self.start_error is None and not self.timed_out and self.returncode == 0

    def reason(self, timeout=None) -> str:
        if self.start_error is not None:
            return "could not start (errno %s)" % (getattr(self.start_error, "errno", None) or "?")
        if self.timed_out:
            return "timed out after %ss (killed with its process group)" % (
                ("%g" % timeout) if timeout is not None else "%.1f" % self.duration_s)
        if self.returncode != 0:
            return "exited %s after %.1fs, stderr %d bytes" % (self.returncode, self.duration_s, self.stderr_len)
        return ""

    def reason_key(self, timeout=None) -> str:
        """The failure's KIND, with nothing that varies from one run of the same failure to the next:
        the exit code, or the timeout, or the start error. `reason` adds the duration and the stderr
        byte count, which change per run, so a change-only log guard comparing it would say the same
        failure again at every run; the guard compares this, and the per-run detail stays in the
        record (api-health's lastRun)."""
        if self.start_error is not None or self.timed_out:
            return self.reason(timeout)
        if self.returncode != 0:
            return "exited %s" % self.returncode
        return ""


def _killpg(p) -> None:
    try:
        os.killpg(p.pid, signal.SIGKILL)         # start_new_session: the child's pid is its pgid
    except (ProcessLookupError, PermissionError):
        pass


def run_command(cmd: str, selector=None, timeout=None, env=None, grace=None) -> RunResult:
    """Run `cmd` through `/bin/sh -c`, with `selector` as `$1` when given, stdin closed, in its own
    session (so a wedged command's children die with it: os.killpg on the deadline). Never raises.

    The deadline is on the PROCESS, not on its pipes: stdout and stderr are read until EOF, or until
    `grace` seconds after the command has exited, whichever comes first. So a command that exits 0
    with a complete set but leaves a child holding stdout (a daemon it forked, a `sleep &` it did not
    disown) is a success, and the leftovers are killed with the group. communicate() would have
    waited for that child's EOF and reported the run timed out. The grace is a fixed window, not a
    quiet period: a leftover that keeps writing cannot hold the read open (this function runs under
    the module lock, so an unbounded read would block every connect), and the overall deadline holds
    in every state, so the call returns by `timeout` seconds whatever the command and its children
    do. Past the deadline with the command still running is a timeout; past it while draining a
    leftover after the command exited is not. A command that hands both pipes back and runs on
    (`exec >/dev/null 2>&1; sleep 30`) ends the read at EOF, and the deadline then holds on the
    wait for its exit: still running at the deadline is the same timeout."""
    timeout = DEFAULT_TIMEOUT_S if timeout is None else float(timeout)
    grace = EXIT_GRACE_S if grace is None else float(grace)
    argv = ["/bin/sh", "-c", str(cmd), "sh"]
    if selector is not None:
        argv.append(str(selector))
    t0 = time.monotonic()
    try:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True, env=env)
    except OSError as e:
        return RunResult(None, b"", 0, time.monotonic() - t0, start_error=e)
    out, err = bytearray(), bytearray()
    sel = selectors.DefaultSelector()
    sel.register(p.stdout, selectors.EVENT_READ, out)
    sel.register(p.stderr, selectors.EVENT_READ, err)
    deadline = t0 + timeout
    exited_at = None
    timed_out = False
    try:
        while sel.get_map():
            now = time.monotonic()
            if exited_at is None and p.poll() is not None:
                exited_at = now
            # the moment reading stops: the deadline, and once the command has exited the END of the
            # grace window if that comes first (a leftover holding a pipe, writing or not)
            stop_at = deadline if exited_at is None else min(deadline, exited_at + grace)
            if now >= stop_at:
                timed_out = exited_at is None    # the command itself overran; a leftover being drained is not that
                break
            for key, _events in sel.select(max(0.0, min(stop_at - now, 0.05))):
                try:
                    data = os.read(key.fd, 65536)
                except OSError:
                    data = b""
                if data:
                    key.data.extend(data)
                else:
                    sel.unregister(key.fileobj)
                    key.fileobj.close()
        if timed_out or sel.get_map():
            _killpg(p)                           # the deadline, or leftovers holding our pipes
        for key in list(sel.get_map().values()):
            sel.unregister(key.fileobj)
            key.fileobj.close()
    finally:
        sel.close()
    if exited_at is None and not timed_out:
        # Both pipes at EOF with the command not seen exited: it released them and ran on. The
        # deadline is on this wait. A fixed wait here misclassified such a run: killed by the
        # fallback below and reported `exited -9`, or a success when it exited within the fallback's
        # window but past the deadline.
        try:
            p.wait(timeout=max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            _killpg(p)
    try:
        p.wait(timeout=5)
    except Exception:
        try:
            p.kill()
            p.wait(timeout=1)
        except Exception:
            pass
    duration = (exited_at if exited_at is not None else time.monotonic()) - t0
    return RunResult(p.returncode, bytes(out), len(err), duration, timed_out=timed_out)


def parse_set(stdout) -> dict:
    """A command's stdout as a set: {"values", "dropped", "droppedAuth", "bad", "empty"} — the
    assignments, the ROMP_* names dropped, the CLI-auth names dropped (AUTH_NAMES; names only), and
    the two counts. `values` is for the injection path alone."""
    text = stdout.decode("utf-8", "replace") if isinstance(stdout, (bytes, bytearray)) else str(stdout or "")
    vals, bad, empty = parse_lines(text, allow_export=True)
    dropped = sorted(k for k in vals if k.startswith(RESERVED_PREFIX))
    dropped_auth = sorted(k for k in vals if k in AUTH_NAMES)
    for k in dropped + dropped_auth:
        del vals[k]
    return {"values": vals, "dropped": dropped, "droppedAuth": dropped_auth, "bad": bad, "empty": empty}


# ---------------------------------------------------------------------------
# The cache — event-keyed, coalesced. One private dict of values; everything else is value-free.
# ---------------------------------------------------------------------------

_lock = threading.Lock()          # serialises runs: a caller arriving mid-run waits and takes the result
_gen = 0                          # bumped by invalidate(); a snapshot is current while its gen matches
_values: dict = {}                # the LAST GOOD set — the one thing here that holds values
_snap: dict | None = None         # the value-free record of the last run (None: never ran)
_snap_selector_ident: tuple = ()  # the selector file's stat identity the record was taken under
_runs = 0                         # command executions, total (tests count coalescing with this)
_attempts = 0                     # _run_locked completions, total — what a waiting caller coalesces on, and
                                  # the record's `attempt`; never rewound (a reader ordering records by it
                                  # may outlive a _reset)
_failures = 0                     # consecutive failed runs
_last_ok_at: float | None = None  # wall-clock time of the last successful run (None: none yet)
_set_seq = 0                      # moves when a run hands back a DIFFERENT set: the set's identity under one generation

_helper_lock = threading.Lock()
_helper: dict = {"gen": -1, "seq": -1, "fp": "", "reason": "", "runs": 0}   # the entry is FOR (gen, seq)


_auth_failed_for: tuple | None = None    # (set fp, helper fp) the last auth-failure invalidation was for
_auth_failed_fps: frozenset = frozenset()  # the fingerprints of that credential: each value of the set, and the helper's


def invalidate(reason: str = "") -> int:
    """Mark the cached set (and the helper fingerprint) stale: the next caller re-runs. Lock-free by
    design — an invalidation must never wait behind a run in progress; a run that was under way when
    the generation moved is stale on completion and the next caller runs again. Returns the new
    generation; `reason` is for the caller's log line. An operator's invalidation (a refresh, a
    cycle, a switch) also re-arms the authentication-failure path below."""
    global _gen, _auth_failed_for, _auth_failed_fps
    _gen += 1
    _auth_failed_for = None
    _auth_failed_fps = frozenset()
    return _gen


def invalidate_for_auth_failure(reason: str = "", fp: str = "") -> bool:
    """An authentication failure where the set (or the helper this module fingerprints) was used:
    invalidate ONCE per credential — keyed on the set and helper fingerprints in force. A second
    refusal while those are unchanged is not new information (the re-run handed back the same set),
    so a revoked credential cannot turn every judge call and every launch into a command run; a
    run that yields a different set, a rotation the helper reports, an operator's invalidate(), or
    a SUCCESS on that credential (credential_auth_ok) re-arms it. Returns whether the generation
    moved. Value-free: fingerprints only.

    `fp` is the fingerprint of the credential that was REFUSED, when the caller knows it (a
    session's launch stamp): a refusal of a credential that is neither a value of the current set
    nor the helper's current output says nothing about the set this module would re-run the
    command for, so it invalidates nothing and is not recorded. That is a session still running on
    the credential from before a rotation, refused on every turn: before this each of its refusals
    invalidated the CURRENT set and each success on the current credential re-armed the path, so an
    uncycled session cost one command run, one helper run and two log lines per turn for as long
    as it was left. "" is a refusal where the caller knows no stamp (a judge call, whose environment
    is the set as a whole; a session launched with nothing to fingerprint) and is keyed on the set
    and helper fingerprints alone, as before."""
    global _gen, _auth_failed_for, _auth_failed_fps
    key = ((_snap or {}).get("setFp") or "", _helper.get("fp") or "")
    if fp and fp not in ({fingerprint(v) for v in _values.values()} | {key[1]}):
        return False                          # not the credential the command would be run for
    if _auth_failed_for == key:
        return False
    _auth_failed_for = key
    _auth_failed_fps = frozenset(fingerprint(v) for v in _values.values()) | {key[1]}
    _auth_failed_fps -= {""}
    _gen += 1
    return True


def credential_auth_ok(fp: str = "") -> bool:
    """A credential this module supplied (or the helper it fingerprints) was ACCEPTED: a session's
    turn completed, a judge call was served, the catalog fetch succeeded. The event that re-arms the
    once-per-credential path above: after a refusal, a re-run that handed back the same set, and then
    a success, a later refusal is new information again (a rotation landed behind the same name
    between the two, and the run that reveals it must happen). Without this the suppression held for
    the life of an unchanged set, and a refusal hours later never re-ran the command. No timer.

    `fp` is the fingerprint of the credential the success was on, when the caller knows it (a
    session's launch stamp, the catalog's direct-call key): a success on a credential OTHER than the
    one refused (a session still running on the set from before a rotation) re-arms nothing, since
    it says nothing about the set the refusal was for. "" is a success on the current set as a whole
    (a judge call, whose environment is the set) and re-arms unconditionally. Returns whether the
    path was re-armed. Value-free: fingerprints only."""
    global _auth_failed_for, _auth_failed_fps
    if _auth_failed_for is None:
        return False
    if fp and fp not in _auth_failed_fps:
        return False
    _auth_failed_for = None
    _auth_failed_fps = frozenset()
    return True


def _empty_snapshot(env_cfg: bool) -> dict:
    return {"configured": env_cfg, "ok": None, "reason": "" if env_cfg else "no %s" % COMMAND_VAR,
            "reasonKey": "" if env_cfg else "no %s" % COMMAND_VAR,
            "at": None, "exitCode": None, "durationS": None, "timedOut": False,
            "names": [], "dropped": [], "droppedAuth": [], "badLines": 0, "emptyValues": 0,
            "setFp": "", "keyFp": "", "hasKey": False, "stale": False,
            "runs": _runs, "failures": _failures, "lastOkAt": _last_ok_at, "generation": _gen,
            "setSeq": _set_seq, "attempt": _attempts, "selector": "", "selectorNote": "", "timeoutProblem": ""}


def _set_values(new: dict) -> None:
    """Under _lock: make `new` the set, moving the set's identity (_set_seq) only when it DIFFERS
    from the set before. Two paths re-run the command without moving the generation (the retry
    after a failed run, a selector-file edit), and either can hand back another set: a caller
    caching something per set (the helper's fingerprint) keys on (generation, setSeq), so a set
    that changed under one generation is not served the old set's entry, and one that did not
    change keeps it. A comparison of values, inside the one function that holds them."""
    global _values, _set_seq
    if new != _values:
        _set_seq += 1
    _values = new


def _run_locked(environ) -> None:
    """Under _lock: run the command once and record the outcome. A failure keeps `_values`."""
    global _snap, _snap_selector_ident, _runs, _attempts, _failures, _last_ok_at
    gen = _gen
    cmd = command(environ)
    snap = _empty_snapshot(configured(environ))
    if not snap["configured"]:
        _set_values({})
        snap["generation"] = gen
        snap["setSeq"] = _set_seq
        _attempts += 1
        snap["attempt"] = _attempts
        _snap = snap
        return
    _snap_selector_ident = _selector_ident(environ)
    sel, sel_err = read_selector(None, environ)
    declared = names(environ)
    if sel and sel in declared:
        snap["selector"] = sel                    # rendered by name only when the name is declared
    elif sel:
        snap["selectorNote"] = "(undeclared, %d chars)" % len(sel)
    reason = sel_err
    if not reason and sel and declared and sel not in declared:
        reason = "the selector file holds a name outside %s" % NAMES_VAR
    if not reason and not cmd:
        # pinned command mode, and the line is gone from the configuration since the kernel started
        reason = ("%s is no longer set — this kernel keeps the mode it started in; `romp refresh` "
                  "restarts it into the configuration as it stands" % COMMAND_VAR)
    reason_key = reason                     # the selector and configuration reasons carry nothing per-run
    if not reason:
        tmo, snap["timeoutProblem"] = _timeout_value(environ)
        r = run_command(cmd, sel, tmo)
        _runs += 1
        snap["runs"] = _runs
        snap["at"] = time.time()
        snap["exitCode"] = r.returncode
        snap["durationS"] = round(r.duration_s, 3)
        snap["timedOut"] = r.timed_out
        reason, reason_key = r.reason(tmo), r.reason_key(tmo)
        if not reason:
            parsed = parse_set(r.stdout)
            snap["dropped"] = parsed["dropped"]
            snap["droppedAuth"] = parsed["droppedAuth"]
            snap["badLines"] = parsed["bad"]
            snap["emptyValues"] = parsed["empty"]
            if not parsed["values"]:
                if not r.stdout.strip():
                    reason = reason_key = "printed nothing"
                elif parsed["bad"]:
                    reason = "printed %d line%s, none NAME=VALUE" % (parsed["bad"], "s" if parsed["bad"] != 1 else "")
                    reason_key = "printed lines, none NAME=VALUE"        # the count is per run
                else:
                    reason = reason_key = "printed no usable NAME=VALUE line"
            else:
                _set_values(parsed["values"])
    if reason:
        _failures += 1
        snap["ok"] = False
        snap["reason"] = reason
        snap["reasonKey"] = reason_key      # the failure's kind: what a change-only log guard compares
        snap["stale"] = bool(_values)       # the previous set stands in
    else:
        _failures = 0
        _last_ok_at = snap["at"]
        snap["ok"] = True
    snap["failures"] = _failures
    snap["lastOkAt"] = _last_ok_at
    snap["names"] = sorted(_values)
    snap["setFp"] = set_fingerprint(_values)
    snap["keyFp"] = fingerprint(_values.get(KEY_VAR, ""))
    snap["hasKey"] = KEY_VAR in _values
    snap["generation"] = gen
    snap["setSeq"] = _set_seq
    _attempts += 1                          # at completion: a caller that read the counter mid-run sees it move
    snap["attempt"] = _attempts             # the record's ordinal: strictly newer than every record before it
    _snap = snap


def _ensure_locked(environ, retry_failed: bool = True) -> None:
    """Under _lock: make the record current. A run happens when there is none, when invalidate()
    moved the generation, when the mode switch changed, when the selector file's stat identity
    changed — and, with `retry_failed`, when the last run failed: a failure is not served like a
    good result, so the next caller runs again (one run per caller; a caller that waited behind a
    run takes that run's result instead, see _fresh)."""
    if _snap is None or _snap.get("generation") != _gen or _snap.get("configured") != configured(environ):
        _run_locked(environ)
        return
    if not _snap.get("configured"):
        return
    if _snap_selector_ident != _selector_ident(environ):
        _run_locked(environ)
        return
    if retry_failed and _snap.get("ok") is False:
        _run_locked(environ)


class _fresh:
    """`with _fresh(environ):` — _lock held and the record current on entry. A caller that waited
    behind another caller's run (the attempt counter moved while it waited) takes that result even
    when it failed: concurrent callers coalesce on one run; only a caller arriving AFTER a failed
    run completed triggers the next one."""

    def __init__(self, environ):
        self.environ = environ

    def __enter__(self):
        attempts0 = _attempts
        _lock.acquire()
        try:
            _ensure_locked(self.environ, retry_failed=(_attempts == attempts0))
        except BaseException:
            _lock.release()
            raise
        return self

    def __exit__(self, *exc):
        _lock.release()
        return False


def current(environ=None) -> dict:
    """The value-free record of the current set, running the command if the cache is stale: ok
    (True/False; None when no command is configured), reason, at, exitCode, durationS, timedOut,
    names (the set's variable names), dropped (ROMP_* names refused), badLines, emptyValues, setFp,
    keyFp (of the set's ANTHROPIC_API_KEY, "" when absent), hasKey, stale (a failed run is standing
    on the previous set), runs, failures, lastOkAt, generation, setSeq (the set's identity within the
    generation: it moves when a run hands back a different set), attempt (the ordinal of the run or
    refusal that produced the record — callers that coalesced on one run share it; a reader holding
    two records orders them by it), selector (the token, when declared), selectorNote ("(undeclared,
    N chars)" otherwise), timeoutProblem. Never a value."""
    with _fresh(environ):
        return dict(_snap)


def injection(environ=None) -> dict:
    """THE value-bearing accessor: a copy of the current set for merging into a CHILD's environment
    (a session CLI's options.env, a judge call's env, the catalog fetch's header). Every other
    function in this module is value-free; nothing calling this may log, store or send what it
    gets. {} when no command is configured or no run has succeeded yet."""
    with _fresh(environ):
        return dict(_values)


def take(environ=None) -> tuple:
    """(record, values) from ONE read under the lock — for a connect that needs both the value-free
    record (to log and stamp) and the set (to inject): read separately, a run could land between
    the two and the key injected would not be the set the log names. The `values` half is
    injection()'s and under its rule. The record's `generation` and `setSeq` are the generation the
    values were served under and the set's identity within it (it moves when a run hands back a
    different set): a caller handing the values to helper_fingerprint() hands both in beside them,
    so the fingerprint is cached for exactly the set it was run with."""
    with _fresh(environ):
        return dict(_snap), dict(_values)


def status(environ=None) -> dict:
    """`current()` plus the configuration, for reports: selectorFile, declaredNames, timeoutS,
    timeoutProblem (also when no run happened). Value-free."""
    out = current(environ)
    out["selectorFile"] = selector_path(environ)
    out["declaredNames"] = names(environ)
    out["timeoutS"], out["timeoutProblem"] = _timeout_value(environ)
    return out


# ---------------------------------------------------------------------------
# The apiKeyHelper fingerprint.
# ---------------------------------------------------------------------------

def claude_config_dir(environ=None) -> str:
    env = os.environ if environ is None else environ
    return (env.get("CLAUDE_CONFIG_DIR") or "").strip() or os.path.expanduser("~/.claude")


HELPER_SETTINGS_FILES = ("settings.json",)    # the ONE user-level settings file Claude Code reads


def helper_command(config_dir=None, environ=None) -> str:
    """The `apiKeyHelper` command Claude Code's USER settings configure ("" for none): `settings.json`
    under $CLAUDE_CONFIG_DIR (default ~/.claude). That is the only user-level settings file Claude
    Code has: a `settings.local.json` is a PROJECT-level layer (a repository's `.claude/`), and one
    placed beside the user file is read by nothing, so it is not consulted here either. Project
    settings (a repository's `.claude/settings.json` and `.claude/settings.local.json`) and managed
    settings are not consulted: the kernel has no project of its own, and what it fingerprints must
    be what every session's CLI resolves at the user level. A command string, never a key."""
    d = config_dir or claude_config_dir(environ)
    cmd = ""
    for name in HELPER_SETTINGS_FILES:
        try:
            with open(os.path.join(d, name), "r", encoding="utf-8") as fh:
                v = json.load(fh).get("apiKeyHelper")
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(v, str) and v.strip():
            cmd = v.strip()
    return cmd


def helper_fingerprint(config_dir=None, environ=None, timeout=None, values=None, generation=None,
                       set_seq=None) -> tuple:
    """(fingerprint, reason) for the credential the configured apiKeyHelper prints right now — the
    helper is run with the same runner and its output hashed HERE; the bytes never leave this
    function. ("", reason) when no helper is configured, it fails, times out, or prints anything
    other than one printable token (the CLI's own contract for helper output). Cached until
    invalidate(); concurrent callers coalesce. The result is stored under the generation current
    when the run STARTED (the way _run_locked does): an invalidate() during the helper run makes
    the result stale on completion, and the next caller runs the helper again, rather than a
    pre-invalidation fingerprint being served as current.

    The helper runs in the environment a session's CLI runs it in: this process's, with the set's
    role variables merged over it (a helper that reads a role variable to pick its store must see
    it) and `ROMP_SID` absent (a kernel started from inside a session's tool shell would otherwise
    hand the helper a session identity no CLI's helper has) — so the fingerprint is of the credential
    the sessions actually bill. `values` is the set a caller already holds (take()'s values half):
    a connect that took the set and then asks for the helper's fingerprint passes it, so the
    command is not run a second time for the same connect (on a failing command, each fresh read
    is a run); None reads the current set. `generation` is the generation those values were served
    under (take()'s record carries it): the run is FOR that generation and is stored under it, so a
    set taken before an invalidate() yields an entry that is already stale, and the next caller
    runs the helper again on the current set. Before this the generation was read here, after the
    overlay was built, so an invalidate() between a connect's take() and this call stored the
    pre-invalidation overlay's fingerprint under the post-invalidation generation, and every caller
    after was served it as current. With `values` given and no generation, the current one (the
    caller did not say); with `values` None, the generation of the set read here.

    `set_seq` is the record's `setSeq` beside that generation: the set's identity WITHIN it. The
    entry is cached for (generation, setSeq), not the generation alone, because the set can change
    under one generation: the retry after a failed run can hand back a rotated role variable, and a
    hand edit of the selector file re-runs the command with no invalidate(). Keyed on the generation
    alone, a connect on the new set was stamped with the OLD overlay's fingerprint, and cycle_key
    read it as current. An unchanged set keeps its entry (a failed run keeps the set, so it moves
    nothing). As with `generation`, absent means the current one.

    The entry is written only when it is not OLDER than the one in the slot. A connect that took the
    set and then waited (its own connect work, the helper lock) can reach here after an invalidate()
    and a later connect stored the current entry; its run is for its own set and it gets that
    fingerprint back (the credential ITS CLI bills), but writing it over the current entry would
    leave the slot naming a fingerprint no current launch gets, and until the next reader healed it
    a refusal on the current one was not "the helper's output" to invalidate_for_auth_failure and
    invalidated nothing."""
    if values is None:
        with _fresh(environ):
            values = dict(_values)
            if generation is None:
                generation = _snap.get("generation")
            if set_seq is None:
                set_seq = _snap.get("setSeq")
    overlay = {k: v for k, v in values.items() if k != KEY_VAR}
    with _helper_lock:
        # the identity this run is FOR: the set's own generation and sequence, so an invalidate
        # between the set's read and here, or during the run, leaves the result stale on completion,
        # and a set that changed under one generation is not served the old set's entry
        key = (_gen if generation is None else int(generation), _set_seq if set_seq is None else int(set_seq))
        if (_helper["gen"], _helper["seq"]) == key:
            return _helper["fp"], _helper["reason"]
        cmd = helper_command(config_dir, environ)
        fp, reason = "", ""
        if not cmd:
            reason = "no apiKeyHelper in %s" % os.path.join(claude_config_dir(environ) if not config_dir else config_dir,
                                                            " or ".join(HELPER_SETTINGS_FILES))
        else:
            tmo = timeout_s(environ) if timeout is None else float(timeout)
            env = dict(os.environ if environ is None else environ)
            env.update(overlay)
            env.pop("ROMP_SID", None)
            r = run_command(cmd, None, tmo, env=env)
            _helper["runs"] += 1
            reason = r.reason(tmo)
            if not reason:
                lines = [ln for ln in r.stdout.decode("utf-8", "replace").splitlines() if ln.strip()]
                if len(lines) != 1:
                    reason = "printed %d non-empty line%s (one token expected)" % (len(lines), "s" if len(lines) != 1 else "")
                elif not TOKEN_RE.match(lines[0].strip()):
                    reason = "printed something that is not a printable token (%d bytes)" % len(lines[0])
                else:
                    fp = fingerprint(lines[0].strip())
        if key >= (_helper["gen"], _helper["seq"]):
            _helper.update({"gen": key[0], "seq": key[1], "fp": fp, "reason": reason})
        return fp, reason


def helper_runs() -> int:
    return _helper["runs"]


def _reset() -> None:
    """Tests only: forget everything, including the counters and the mode pin — except the record
    ordinal (_attempts), which moves forward like the generation does: a reader that orders records
    by `attempt` (the backend's noter) may outlive a reset, and a rewound ordinal would have it take
    every record after the reset for an older one."""
    global _gen, _values, _snap, _snap_selector_ident, _runs, _failures, _last_ok_at, _FILE_CFG, _MODE_PIN
    global _auth_failed_for, _auth_failed_fps, _set_seq
    with _lock, _helper_lock:
        _gen += 1
        _auth_failed_for = None
        _auth_failed_fps = frozenset()
        _values = {}
        _snap = None
        _snap_selector_ident = ()
        _runs = 0
        _failures = 0
        _last_ok_at = None
        _set_seq = 0
        _FILE_CFG = ((), {})
        _MODE_PIN = None
        _helper.update({"gen": -1, "seq": -1, "fp": "", "reason": "", "runs": 0})
