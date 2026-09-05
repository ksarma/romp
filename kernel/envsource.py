"""envsource — a credential set from a configured COMMAND, handed to each child at launch and never
written to the kernel's own environment or to any file.

The file source (keysource.py) reads `ANTHROPIC_API_KEY=` out of the manager's env file. Some
installations forbid a credential in any file. For them this module is the source instead:
`ROMP_CREDENTIAL_COMMAND` (a non-secret shell command, set in the same env file or unit
environment) is run by the kernel, prints `NAME=VALUE` lines, and the resulting SET is merged into
the launch environment of every session CLI, every judge call and the catalog fetch. Setting the
variable is what selects this mode; unset, nothing here runs and every caller sees an empty set.

Configuration (process environment first, then the same line in the manager's env file, so a
terminal outside the manager tree resolves the same values):

* `ROMP_CREDENTIAL_COMMAND` — run as `/bin/sh -c <command> sh <selector>`, so the selector is `$1`.
* `ROMP_CREDENTIAL_SELECTOR_FILE` — a file holding ONE token (a name such as `hp`), passed as `$1`.
  Default `${XDG_CONFIG_HOME:-~/.config}/romp/credential-selector`.
* `ROMP_CREDENTIAL_NAMES` — the comma list of selector names an operator may pick. A token outside
  the list is refused before the command runs.
* `ROMP_CREDENTIAL_TIMEOUT_S` — how long one run may take (default 15).

Output contract: `ANTHROPIC_API_KEY` (optional) is the work key; `ANTHROPIC_LP_API_KEY` the direct-
call key; any other name is a role variable for the sessions' shells. Names starting with `ROMP_`
are dropped (romp owns them). The parsing rule is keysource's, generalised to every name: blank
and `#` lines skipped, `NAME=value`, last assignment wins, one layer of matching quotes stripped.

Three properties this module holds, the same three keysource.py holds:

* **Values never land in `os.environ`.** They live in one private dict here and leave it through
  exactly one accessor, `injection()`, whose callers merge them into a CHILD's environment.
* **Values never reach a log, a screen or a wire.** Every other function returns names, counts,
  exit codes and fingerprints (`sha256` head, 12 hex). Failure reasons carry counts and exit codes
  only ("exited 3 after 0.4s, stderr 87 bytes") — the command's stdout and stderr bytes are never
  quoted, since a command that echoes a credential to stderr would otherwise leak it into the log.
* **A failed run keeps the previous set.** The cache is event-keyed, with no timer: it holds until
  `invalidate()` (an operator's refresh, a cycle, an authentication failure in a judge call or a
  session). Concurrent callers coalesce on one lock — a boot that revives many sessions runs the
  command once, not once per session — and a caller arriving mid-run takes the fresh result.

The apiKeyHelper fingerprint lives here too: on an installation whose set carries no work key the
sessions authenticate through Claude Code's own `apiKeyHelper`, and the kernel never sees that
value. To tell whether a running session is on the current credential, `helper_fingerprint()` runs
the configured helper with the same runner and hashes its output inside this function; the bytes
never leave it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
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

KEY_VAR = "ANTHROPIC_API_KEY"          # the work key, when the set carries one
LP_KEY_VAR = "ANTHROPIC_LP_API_KEY"    # the direct-call key (the catalog fetch)
RESERVED_PREFIX = "ROMP_"              # names romp owns: dropped from any set

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


def parse_lines(text) -> tuple[dict, int, int]:
    """Every assignment an env-file body (or a command's stdout) makes: {NAME: value}, plus the count
    of lines that are not `NAME=value` and the count of assignments whose value is empty. Blank and
    `#` lines are skipped, the LAST assignment of a name wins, and one layer of matching quotes is
    stripped — keysource.parse_key's rule for one name, applied to all of them (pinned equal by
    test). An empty value is dropped: for the key that is "no key", for a role variable a var the
    child would see set-but-empty, which for the CLI's own key var means "key mode, no key"."""
    out: dict = {}
    bad = empty = 0
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        name = name.strip()
        if not sep or not NAME_RE.match(name):
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
    """One configuration value: the process environment's, else the env file's line, else ""."""
    env = os.environ if environ is None else environ
    v = (env.get(name) or "").strip()
    if v:
        return v
    return (_file_config().get(name) or "").strip()


def command(environ=None) -> str:
    return config_value(COMMAND_VAR, environ)


def configured(environ=None) -> bool:
    """Whether the command source is selected — the ONE mode switch: a non-empty command."""
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


def timeout_s(environ=None) -> float:
    raw = config_value(TIMEOUT_VAR, environ)
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_S
    return v if v > 0 else DEFAULT_TIMEOUT_S


# ---------------------------------------------------------------------------
# The selector file — one token, read and written atomically.
# ---------------------------------------------------------------------------

def valid_selector(token) -> bool:
    return bool(isinstance(token, str) and SELECTOR_RE.match(token))


def selector_allowed(token: str, environ=None) -> bool:
    """Whether `token` may be selected: among the declared names, or anything valid when none are
    declared. The token itself is never part of any message built from a refusal."""
    if not valid_selector(token):
        return False
    declared = names(environ)
    return (token in declared) if declared else True


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


def run_command(cmd: str, selector=None, timeout=None, env=None) -> RunResult:
    """Run `cmd` through `/bin/sh -c`, with `selector` as `$1` when given, stdin closed, in its own
    session (so a wedged command's children die with it: os.killpg on the deadline). Never raises."""
    timeout = DEFAULT_TIMEOUT_S if timeout is None else float(timeout)
    argv = ["/bin/sh", "-c", str(cmd), "sh"]
    if selector is not None:
        argv.append(str(selector))
    t0 = time.monotonic()
    try:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True, env=env)
    except OSError as e:
        return RunResult(None, b"", 0, time.monotonic() - t0, start_error=e)
    timed_out = False
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(p.pid, signal.SIGKILL)     # start_new_session: the child's pid is its pgid
        except (ProcessLookupError, PermissionError):
            pass
        try:
            out, err = p.communicate(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
            out, err = b"", b""
    return RunResult(p.returncode, out or b"", len(err or b""), time.monotonic() - t0, timed_out=timed_out)


def parse_set(stdout) -> dict:
    """A command's stdout as a set: {"values", "dropped", "bad", "empty"} — the assignments, the ROMP_*
    names dropped (names only), and the two counts. `values` is for the injection path alone."""
    text = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else str(stdout or "")
    vals, bad, empty = parse_lines(text)
    dropped = sorted(k for k in vals if k.startswith(RESERVED_PREFIX))
    for k in dropped:
        del vals[k]
    return {"values": vals, "dropped": dropped, "bad": bad, "empty": empty}


# ---------------------------------------------------------------------------
# The cache — event-keyed, coalesced. One private dict of values; everything else is value-free.
# ---------------------------------------------------------------------------

_lock = threading.Lock()          # serialises runs: a caller arriving mid-run waits and takes the result
_gen = 0                          # bumped by invalidate(); a snapshot is current while its gen matches
_values: dict = {}                # the LAST GOOD set — the one thing here that holds values
_snap: dict | None = None         # the value-free record of the last run (None: never ran)
_runs = 0                         # command executions, total (tests count coalescing with this)
_failures = 0                     # consecutive failed runs

_helper_lock = threading.Lock()
_helper: dict = {"gen": -1, "fp": "", "reason": "", "runs": 0}


def invalidate(reason: str = "") -> int:
    """Mark the cached set (and the helper fingerprint) stale: the next caller re-runs. Lock-free by
    design — an invalidation must never wait behind a run in progress; a run that was under way when
    the generation moved is stale on completion and the next caller runs again. Returns the new
    generation; `reason` is for the caller's log line."""
    global _gen
    _gen += 1
    return _gen


def _empty_snapshot(env_cfg: bool) -> dict:
    return {"configured": env_cfg, "ok": None, "reason": "" if env_cfg else "no %s" % COMMAND_VAR,
            "at": None, "exitCode": None, "durationS": None, "timedOut": False,
            "names": [], "dropped": [], "badLines": 0, "emptyValues": 0,
            "setFp": "", "keyFp": "", "hasKey": False, "stale": False,
            "runs": _runs, "failures": _failures, "generation": _gen, "selector": ""}


def _run_locked(environ) -> None:
    """Under _lock: run the command once and record the outcome. A failure keeps `_values`."""
    global _values, _snap, _runs, _failures
    gen = _gen
    cmd = command(environ)
    snap = _empty_snapshot(bool(cmd))
    if not cmd:
        _values = {}
        snap["generation"] = gen
        _snap = snap
        return
    sel, sel_err = read_selector(None, environ)
    snap["selector"] = sel
    reason = sel_err
    if not reason and sel and names(environ) and sel not in names(environ):
        reason = "the selector file holds a name outside %s" % NAMES_VAR
    if not reason:
        tmo = timeout_s(environ)
        r = run_command(cmd, sel, tmo)
        _runs += 1
        snap["runs"] = _runs
        snap["at"] = time.time()
        snap["exitCode"] = r.returncode
        snap["durationS"] = round(r.duration_s, 3)
        snap["timedOut"] = r.timed_out
        reason = r.reason(tmo)
        if not reason:
            parsed = parse_set(r.stdout)
            snap["dropped"] = parsed["dropped"]
            snap["badLines"] = parsed["bad"]
            snap["emptyValues"] = parsed["empty"]
            if not parsed["values"]:
                if not r.stdout.strip():
                    reason = "printed nothing"
                elif parsed["bad"]:
                    reason = "printed %d line%s, none NAME=VALUE" % (parsed["bad"], "s" if parsed["bad"] != 1 else "")
                else:
                    reason = "printed no usable NAME=VALUE line"
            else:
                _values = parsed["values"]
    if reason:
        _failures += 1
        snap["ok"] = False
        snap["reason"] = reason
        snap["stale"] = bool(_values)       # the previous set stands in
    else:
        _failures = 0
        snap["ok"] = True
    snap["failures"] = _failures
    snap["names"] = sorted(_values)
    snap["setFp"] = set_fingerprint(_values)
    snap["keyFp"] = fingerprint(_values.get(KEY_VAR, ""))
    snap["hasKey"] = KEY_VAR in _values
    snap["generation"] = gen
    _snap = snap


def _ensure_locked(environ) -> None:
    if _snap is None or _snap.get("generation") != _gen or _snap.get("configured") != configured(environ):
        _run_locked(environ)


def current(environ=None) -> dict:
    """The value-free record of the current set, running the command if the cache is stale: ok
    (True/False; None when no command is configured), reason, at, exitCode, durationS, timedOut,
    names (the set's variable names), dropped (ROMP_* names refused), badLines, emptyValues, setFp,
    keyFp (of the set's ANTHROPIC_API_KEY, "" when absent), hasKey, stale (a failed run is standing
    on the previous set), runs, failures, generation, selector. Never a value."""
    with _lock:
        _ensure_locked(environ)
        return dict(_snap)


def injection(environ=None) -> dict:
    """THE value-bearing accessor: a copy of the current set for merging into a CHILD's environment
    (a session CLI's options.env, a judge call's env, the catalog fetch's header). Every other
    function in this module is value-free; nothing calling this may log, store or send what it
    gets. {} when no command is configured or no run has succeeded yet."""
    with _lock:
        _ensure_locked(environ)
        return dict(_values)


def status(environ=None) -> dict:
    """`current()` plus the configuration, for reports: command (bool: configured), selectorFile,
    names (declared), timeoutS. Value-free."""
    out = current(environ)
    out["selectorFile"] = selector_path(environ)
    out["declaredNames"] = names(environ)
    out["timeoutS"] = timeout_s(environ)
    return out


# ---------------------------------------------------------------------------
# The apiKeyHelper fingerprint.
# ---------------------------------------------------------------------------

def claude_config_dir(environ=None) -> str:
    env = os.environ if environ is None else environ
    return (env.get("CLAUDE_CONFIG_DIR") or "").strip() or os.path.expanduser("~/.claude")


def helper_command(config_dir=None, environ=None) -> str:
    """The `apiKeyHelper` command Claude Code's settings.json configures ("" for none): the
    user-level file under $CLAUDE_CONFIG_DIR (default ~/.claude). A command string, never a key."""
    d = config_dir or claude_config_dir(environ)
    try:
        with open(os.path.join(d, "settings.json"), "r", encoding="utf-8") as fh:
            v = json.load(fh).get("apiKeyHelper")
    except (OSError, ValueError, AttributeError):
        return ""
    return v.strip() if isinstance(v, str) else ""


def helper_fingerprint(config_dir=None, environ=None, timeout=None) -> tuple:
    """(fingerprint, reason) for the credential the configured apiKeyHelper prints right now — the
    helper is run with the same runner and its output hashed HERE; the bytes never leave this
    function. ("", reason) when no helper is configured, it fails, times out, or prints anything
    other than one printable token (the CLI's own contract for helper output). Cached until
    invalidate(); concurrent callers coalesce."""
    with _helper_lock:
        if _helper["gen"] == _gen:
            return _helper["fp"], _helper["reason"]
        cmd = helper_command(config_dir, environ)
        fp, reason = "", ""
        if not cmd:
            reason = "no apiKeyHelper in %s" % os.path.join(claude_config_dir(environ) if not config_dir else config_dir,
                                                            "settings.json")
        else:
            tmo = timeout_s(environ) if timeout is None else float(timeout)
            r = run_command(cmd, None, tmo)
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
        _helper.update({"gen": _gen, "fp": fp, "reason": reason})
        return fp, reason


def helper_runs() -> int:
    return _helper["runs"]


def _reset() -> None:
    """Tests only: forget everything, including the counters."""
    global _gen, _values, _snap, _runs, _failures, _FILE_CFG
    with _lock, _helper_lock:
        _gen += 1
        _values = {}
        _snap = None
        _runs = 0
        _failures = 0
        _FILE_CFG = ((), {})
        _helper.update({"gen": -1, "fp": "", "reason": "", "runs": 0})
