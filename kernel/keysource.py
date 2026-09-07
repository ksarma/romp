"""Live API-key configuration, separate from credential retrieval.

The design, in five rules:

* A SOURCE is configuration, not a secret: a static key line, or a 1Password reference
  (``ROMP_API_KEY_REF=op://vault/item/field``) that names where the key lives. Everything that
  needs to KNOW about the key — the Billing picker, status displays, ``romp keyswap``'s listing and
  identity checks — reads the source. Only resolve() ever runs ``op read``, at the moment a Claude
  session launches, an API-key-billed judge call is made, or the model catalog refreshes; the value
  is handed to that one operation and never written to disk or cached for a later one.
* A selected source is AUTHORITATIVE. A file that once carried a key line or a reference keeps
  governing this process: emptying it, removing the line, or making it unreadable is an error the
  operation reports, never permission to fall back to the key the manager started with or to a
  login. That is what makes ``romp keyswap`` a swap — nothing an operator removed can come back.
* Supervised managers (``ROMP_SUPERVISED=1``: the systemd/launchd service) read the FILE only. The
  manager process keeps the environment it started with across every kernel restart, so a key it
  inherited would otherwise resurrect after the operator removed it from the file. A startup key
  the kernel therefore ignores is said once on the log wire (sdk_backend.work_api_key_source).
* ``op``'s OWN credential (a service-account token, a session token) is the one secret that must
  reach the kernel's environment for headless use — and nothing else: claim_op_env() takes those
  names out of os.environ at startup and resolve() hands them back to the ``op read`` subprocess
  alone, so no Claude session, judge child or tmux launch inherits a vault-wide credential. The
  tmux SERVER is scrubbed of the same names — and of a stale ``ANTHROPIC_API_KEY`` — whenever romp
  becomes the op consumer, not only at kernel start (2026-09-06: a keyswap to a reference with no
  restart left both in the server's globals, and every new pane billed the old key).
* An op source selected from the FILE is remembered on disk (``service.env.source``, beside the file),
  so a supervised restart after the reference line vanished still refuses to fall to a login
  (2026-09-06: the memory was process-local and a kernel restart forgot it).
* A COMMAND (``ROMP_CREDENTIAL_COMMAND=<shell command>``, printing ``NAME=VALUE`` lines) is the general
  runtime source, and the reference is its built-in default: a command line outranks a reference, which
  outranks a key line, at the file door and the environment door alike. This module selects the kind,
  remembers it (the marker holds the word ``command``), writes it in a profile swap and reserves the
  same names for it. Running the command, holding the set it prints and injecting the values per child
  belong to the kernel's command source, reached only through COMMAND_RESOLVER, so this module never
  loads it and the set never enters os.environ. Nothing is claimed or scrubbed for a command: it runs
  with the kernel's own environment and may itself call ``op`` with a credential it finds there.

Legacy environment/file keys and Claude login remain supported without 1Password.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from dataclasses import dataclass, field

KEY_VAR = "ANTHROPIC_API_KEY"
REF_VAR = "ROMP_API_KEY_REF"
# The command kind: a configured command that prints NAME=VALUE lines. Selected by the same two doors as
# the reference and outranking it. The text is configuration, not a secret, but it is rendered by
# fingerprint only (an operator's command may embed a path or an account name).
CMD_VAR = "ROMP_CREDENTIAL_COMMAND"
CMD_MAX_BYTES = 4096
RUNTIME_KINDS = ("op", "command")         # the kinds that retrieve at runtime and are remembered on the marker
# resolve() for the command kind: a callable taking the KeySource and returning the set's ANTHROPIC_API_KEY
# ("" when the set carries none). The kernel wires it at import; unwired, resolve() raises. A hook rather
# than an import: the command source loads this module for service_env_path, and this module must never
# load it back.
COMMAND_RESOLVER = None
OP_TIMEOUT = 15
# The environment names the 1Password CLI authenticates from. Claimed out of the kernel's environment
# once (claim_op_env) and given back to the `op read` subprocess only (resolve): a service-account
# token reads every field the account can see, and a child that inherits it — a Claude session's
# Bash, a judge call, a subagent — could print it with `env`. OP_SESSION_<account> is the name shape
# `op signin` exports; anything with that prefix is treated the same way.
OP_ENV_NAMES = ("OP_SERVICE_ACCOUNT_TOKEN", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN", "OP_ACCOUNT")
OP_ENV_PREFIX = "OP_SESSION_"
_OP_ENV: dict[str, str] = {}
_OP_CLAIM_SAID = False
_TMUX_SCRUBBED: set = set()      # names already unset from the tmux server's globals by this process
# The sibling file that remembers, across kernel restarts, that the env file's source was a runtime one:
# `service.env.source` (sibling_path), containing the kind word (`op` or `command`) and never a value.
SOURCE_MARKER = "source"


def is_op_env_name(name: str) -> bool:
    return name in OP_ENV_NAMES or name.startswith(OP_ENV_PREFIX)


def is_tmux_scrub_name(name: str) -> bool:
    """The ONE list of names romp removes from a tmux server's globals and a tmux launch's client env
    while it is the op consumer: op's credential names, and ANTHROPIC_API_KEY — the key the manager
    started with, which a keyswap to a reference retired but the tmux server still carried, so every new
    pane billed it (review find, 2026-09-06). A pane without it falls to Claude Code's own auth (login or
    apiKeyHelper). Never applied on a box with no reference: static-key panes rely on the inheritance."""
    return is_op_env_name(name) or name == KEY_VAR


def op_consumer() -> bool:
    """Is romp itself the one running `op`? Only while the op kind is the selected source: a 1Password
    reference in the manager's environment with no credential command beside it, or a reference (or an
    unreadable file) as the env file's source. A command outranks a reference wherever the two meet, and
    a command may itself run `op` with the credential it finds in its environment, so nothing is claimed
    for it. A box whose SESSIONS fetch their key through Claude Code's apiKeyHelper calling `op` needs
    op's credential in every session's environment, and romp then leaves it alone."""
    file_kind = read_source().kind if os.path.exists(service_env_path()) else "none"
    if file_kind == "command":
        return False
    if REF_VAR in os.environ and CMD_VAR not in os.environ:
        return True
    return file_kind in ("op", "error")


def claim_op_env() -> dict[str, str]:
    """Take op's credential names out of os.environ and return the running stash — but only while romp
    is the op consumer (see op_consumer): otherwise the environment is left exactly as found, since a
    session-side helper may need it. Idempotent and cheap; a value that appears later is claimed too. The
    claimed NAMES (never values) are said once on the log wire so a helper that stops working has a
    line to be found by."""
    global _OP_CLAIM_SAID
    if not op_consumer():
        return _OP_ENV
    names = [k for k in os.environ if is_op_env_name(k)]
    for k in names:
        _OP_ENV[k] = os.environ.pop(k)
    if names and not _OP_CLAIM_SAID:
        _OP_CLAIM_SAID = True
        import sys
        sys.stderr.write("op credentials claimed from the environment for `op read`: %s — sessions, judge "
                         "calls and tmux launches will not see them\n" % ", ".join(sorted(names)))
    # The tmux server the manager started carries the same environment the kernel did, and every pane
    # inherits the SERVER's globals: scrub it of what was just claimed, plus the manager's startup
    # ANTHROPIC_API_KEY. Here, not only in kernel main() — a `romp keyswap` to a reference on a box that
    # started without one makes romp the op consumer mid-run, and the first claim after it is the moment
    # the server still holds the token (review find, 2026-09-06). Once per name per process; best effort.
    pending = (set(_OP_ENV) | {KEY_VAR}) - _TMUX_SCRUBBED
    if pending:
        tmux_unset_global(pending, os.environ.get("ROMP_TMUX_SOCKET", ""))
        _TMUX_SCRUBBED.update(pending)
    return _OP_ENV


def strip_op_env(env: dict) -> dict:
    """The same names removed from a child environment built before the claim (a standalone judge, a
    kernel that spawned a tmux launch before its backend existed) — while romp is the op consumer; a
    helper box keeps its environment. Returns `env` for chaining."""
    if _OP_ENV or op_consumer():
        for k in [k for k in env if is_op_env_name(k)]:
            env.pop(k, None)
    return env


def strip_tmux_env(env: dict) -> dict:
    """The environment a tmux launch (`romp new -t`, `romp resume --detach`) is spawned with: op's
    credential (strip_op_env) and, while romp is the op consumer, ANTHROPIC_API_KEY as well — the pane
    must not bill the key the manager started with once a reference governs (is_tmux_scrub_name). A box
    with no reference keeps both, as before. Returns `env` for chaining."""
    strip_op_env(env)
    if _OP_ENV or op_consumer():
        env.pop(KEY_VAR, None)
    return env


def tmux_unset_global(names, socket: str = "") -> list:
    """Remove credential names from a tmux SERVER's global environment — the environment every new
    pane inherits, which the manager-started server carried from service.env (review find, 2026-09-05:
    a tmux session's `exec claude` saw the token although the launching client had been scrubbed). The
    names are filtered through is_tmux_scrub_name, the one list. Best effort: no tmux, no server, an old
    tmux → nothing happens. Returns the commands run, for tests."""
    ran = []
    for name in sorted(set(n for n in names if is_tmux_scrub_name(n))):
        cmd = ["tmux"] + (["-L", socket] if socket else []) + ["set-environment", "-gu", name]
        try:
            _TMUX_RUN(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      timeout=5, check=False)
            ran.append(cmd)
        except Exception:      # best effort by contract: a scrub that cannot run must never fail a launch
            pass
    return ran


# Bound at import, not looked up per call: every suite here fakes `op read` by patching subprocess.run,
# and the tmux scrub that claim_op_env now runs would otherwise register as a credential retrieval (or
# raise the fake's "unexpected retrieval"). Tests that want to see the scrub patch THIS name.
_TMUX_RUN = subprocess.run


def runtime_reserved_names(auth: str, source, keyed=None) -> tuple:
    """The credential names a per-session environment may NOT carry while runtime retrieval governs.
    A per-session ANTHROPIC_API_KEY always competes with the selected source. A KEYED launch (an explicit
    key pick, or no pick with a configured source) must carry no token beside the key it resolves either;
    a LOGIN session's own token override bills the account the user chose for it and never touches the
    key source, so it stays (review find, 2026-09-05). One rule for the doors, the launch and the fork.
    The command kind is a runtime source like the reference. `keyed` may be passed explicitly: under the
    command kind the launch decides it after taking the set, since a key pick whose set carries no
    ANTHROPIC_API_KEY injects nothing and then reserves the key name only."""
    if source is None or source.kind not in ("op", "command", "error"):
        return ()
    if keyed is None:
        keyed = auth == "key" or (auth != "login" and source.configured)
    return ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN") if keyed else ("ANTHROPIC_API_KEY",)

# Cache file configuration only. ctime/mode also invalidate permission changes; a formerly
# readable credential must not survive a chmod merely because its content did not change.
_CACHE: tuple = ((), "")
_AUTHORITATIVE_PATHS: dict[str, str] = {}
_ENV_PROVIDER_PATHS: dict[str, str] = {}      # path -> the runtime kind a foreground environment selected


class KeySourceError(RuntimeError):
    """A credential failure whose message is safe for user-visible logs."""


@dataclass(frozen=True)
class KeySource:
    kind: str
    value: str = field(default="", repr=False)
    error: str = ""

    @property
    def configured(self) -> bool:
        # An invalid provider remains an explicit choice, never permission to use a login.
        return self.kind in ("op", "command", "error") or bool(self.value)

    def validate(self) -> None:
        if self.kind == "error":
            raise KeySourceError(self.error or "Cannot read the configured API key source")
        if self.kind == "op":
            parts = self.value[5:].split("/") if self.value.startswith("op://") else []
            if (len(parts) not in (3, 4) or not all(parts)
                    or any(c in self.value for c in ("\r", "\n", "\0"))):
                raise KeySourceError("ROMP_API_KEY_REF must be an op://vault/item/[section/]field reference")
        elif self.kind == "command":
            # One line the shell can run; the text itself is never echoed (see the module comment on CMD_VAR).
            if (not self.value.strip() or any(c in self.value for c in ("\r", "\n", "\0"))
                    or len(self.value.encode("utf-8", "replace")) > CMD_MAX_BYTES):
                raise KeySourceError("%s must be one non-empty line of at most %d bytes" % (CMD_VAR, CMD_MAX_BYTES))
        elif self.kind not in ("file", "environment", "none"):
            raise KeySourceError("Unknown API key source")
        elif any(c in self.value for c in ("\r", "\n", "\0")):
            raise KeySourceError("API keys must be a single line")

    def fingerprint(self) -> str:
        """Configuration identity; for op this hashes the reference, never retrieves its value, and for a
        command it hashes the command text, never the set the command prints."""
        if self.kind == "op":
            return fingerprint("op:" + self.value)
        if self.kind == "command":
            return fingerprint("command:" + self.value)
        if self.kind == "error":
            return ""
        return fingerprint(self.value)

    def resolve(self) -> str:
        self.validate()
        if self.kind == "command":
            # The kernel's command source answers from the set it holds: the last good set's key, or ""
            # when the set carries none (a helper- or login-billed installation). A failed run is never
            # raised here; the source keeps the last good set and says so on its own line.
            if COMMAND_RESOLVER is None:
                raise KeySourceError("the credential command is resolved by the kernel's command source")
            return COMMAND_RESOLVER(self)
        if self.kind != "op":
            return self.value
        # op authenticates from the credential names claimed at startup; they ride into THIS subprocess
        # and no other (see claim_op_env). The rest of the environment is a whitelist, not a copy
        # (review find, 2026-09-06: the copy carried ROMP_SERVE_TOKEN — full control of every session —
        # and the manager's startup ANTHROPIC_API_KEY into a third-party binary). op needs HOME and the
        # XDG_* names to find `~/.config/op` and the desktop app's socket, PATH to run, TMPDIR/LANG/LC_*/
        # TERM for ordinary CLI behaviour, USER/LOGNAME for its account defaults; nothing else of romp's.
        op_env = op_subprocess_env()
        try:
            result = subprocess.run(
                ["op", "read", "--no-newline", self.value], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=OP_TIMEOUT,
                check=False, env=op_env,
            )
        except FileNotFoundError:
            raise KeySourceError("1Password CLI (op) is not on the manager's PATH") from None
        except subprocess.TimeoutExpired:
            raise KeySourceError("1Password credential retrieval timed out; check op authentication") from None
        except OSError:
            raise KeySourceError("Cannot run 1Password CLI; check the manager's op installation") from None
        if result.returncode:
            # Neither subprocess stderr nor its exception repr is safe to log.
            raise KeySourceError("1Password credential retrieval failed; check op authentication and vault access")
        try:
            value = result.stdout.decode("utf-8")
        except UnicodeError:
            raise KeySourceError("1Password returned an invalid API key") from None
        if not value or len(value) > 16384 or any(c.isspace() or c == "\0" for c in value):
            raise KeySourceError("1Password returned an empty or invalid API key")
        return value


OP_ENV_PASSTHROUGH = ("PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "TERM")
OP_ENV_PASSTHROUGH_PREFIXES = ("LC_", "XDG_")


def op_subprocess_env() -> dict:
    """The environment the `op read` subprocess gets and nothing more: the passthrough names above, op's
    own credential names — the claimed stash, plus any still in os.environ (a caller resolving a
    reference on a box where romp never became the consumer) — and no romp variable of any kind."""
    env = {k: v for k, v in os.environ.items()
           if k in OP_ENV_PASSTHROUGH or k.startswith(OP_ENV_PASSTHROUGH_PREFIXES) or is_op_env_name(k)}
    env.update(claim_op_env())
    return env


def service_env_path() -> str:
    """The path of the env file the manager is configured from.

    `ROMP_SERVICE_ENV_FILE` is the name the installer and the macOS launcher already use
    (`bin/romp-service`, `bin/romp-node-launch`), so it is the primary; `ROMP_SERVICE_ENV` is
    accepted as an alias. Default `${XDG_CONFIG_HOME:-~/.config}/romp/service.env` — the same
    expression those two scripts compute, so all three always name one file.
    """
    for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
        p = (os.environ.get(var) or "").strip()
        if p:
            return os.path.expanduser(p)
    base = (os.environ.get("XDG_CONFIG_HOME") or "").strip() or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "romp", "service.env")


def sibling_path(name: str, path: str | None = None) -> str:
    """The candidate file a keyswap reads from. A bare name (`highprio`) means the sibling
    `service.env.<name>` beside the live file — the convention that keeps candidate files together
    with mode 0600 (a private parent directory needs 0700). Anything with a separator, or an explicit
    path, is taken as given."""
    name = str(name or "").strip()
    if not name:
        return ""
    if os.sep in name or name.startswith("~"):
        return os.path.expanduser(name)
    return (path or service_env_path()) + "." + name


def _assignments(text: str) -> dict[str, str]:
    """Read literal env assignments; never execute or expand the file's contents."""
    out = {}
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name.strip() not in (KEY_VAR, REF_VAR, CMD_VAR):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]     # systemd strips one layer; without this the CLI gets the quotes
        out[name.strip()] = value
    return out


def _garbled(values: dict) -> str:
    """The name of a key/reference line that did not decode as UTF-8 (the read replaces bad bytes with
    U+FFFD, which no real key contains) — "" when both are clean. A garbled key must fail HERE, with a
    readable note, not at the API as an unexplained invalid-key error."""
    for name in (CMD_VAR, REF_VAR, KEY_VAR):
        if "\ufffd" in values.get(name, ""):
            return name
    return ""


def parse_key(text: str) -> str:
    return _assignments(text).get(KEY_VAR, "")


def parse_source(text: str) -> KeySource:
    """command > op > file: an explicit command overrides the built-in default command (the reference),
    which overrides a static key line."""
    values = _assignments(text)
    bad = _garbled(values)
    if bad:
        return KeySource("error", error="the %s line in the API key source configuration is not valid UTF-8" % bad)
    if CMD_VAR in values:
        return KeySource("command", values[CMD_VAR])
    if REF_VAR in values:
        return KeySource("op", values[REF_VAR])
    if KEY_VAR in values:
        return KeySource("file", values[KEY_VAR])
    return KeySource("none")


def read_source(path: str | None = None) -> KeySource:
    """Read configuration only. Read errors remain errors, never an absent credential."""
    global _CACHE
    p = path or service_env_path()
    try:
        st = os.stat(p)
        ident = (p, st.st_ino, st.st_mtime_ns, st.st_ctime_ns, st.st_size, st.st_mode)
    except FileNotFoundError:
        _CACHE = ((p, "absent"), KeySource("none"))
        return _CACHE[1]
    except OSError:
        return KeySource("error", error="Cannot read the API key source configuration")
    if _CACHE[0] == ident:
        return _CACHE[1]
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:   # a stray byte in a comment is not an outage
            source = parse_source(fh.read())
    except OSError:
        return KeySource("error", error="Cannot read the API key source configuration")
    _CACHE = (ident, source)
    return source


def select_source(startup_key: str = "") -> KeySource:
    """Choose a source without fetching it; only a never-configured file permits env fallback.

    Track the path, not one global flag, so isolated kernels/tests with different config roots
    cannot change each other's source policy. An unreadable file is always an error. Once an op
    reference has been selected from a file or the environment, deleting it is an error until a new
    source is configured. A previously selected file stays authoritative over the environment.
    Supervised services always use the file: their manager may still hold an old assignment across
    kernel restarts, so inherited credentials cannot establish a fallback for a fresh kernel.
    """
    path = service_env_path()
    source = read_source(path)
    if source.kind != "none":
        if source.kind != "error":
            if _AUTHORITATIVE_PATHS.get(path) != source.kind:      # a transition: mirror it to disk once
                remember_file_source(path, source.kind)
            _AUTHORITATIVE_PATHS[path] = source.kind
        return source
    # The runtime memory is DURABLE (2026-09-06): a supervised kernel restart forgot the process-local
    # entry, and with the reference line gone from the file and none in the manager's environment every
    # session without an explicit pick launched on the login — the silent fallback this module exists
    # to end. The marker beside the file holds the kind word (`op` or `command`) until a static source
    # is selected or written. The command kind walks the same doors as the reference, ahead of it.
    previous = _AUTHORITATIVE_PATHS.get(path)
    if not previous:
        marker = read_marker(path)
        previous = marker if marker in RUNTIME_KINDS else None
    if previous in RUNTIME_KINDS:
        return KeySource("error", error=_removed_error(previous))
    if previous:
        return KeySource("file")
    if os.environ.get("ROMP_SUPERVISED") == "1":
        for kind, var in (("command", CMD_VAR), ("op", REF_VAR)):
            if var in os.environ:
                _AUTHORITATIVE_PATHS[path] = kind
                return KeySource("error", error=_removed_error(kind))
        _AUTHORITATIVE_PATHS[path] = "file"
        return KeySource("file")
    for kind, var in (("command", CMD_VAR), ("op", REF_VAR)):
        if var in os.environ:
            _ENV_PROVIDER_PATHS[path] = kind
            return KeySource(kind, os.environ[var].strip())
    if path in _ENV_PROVIDER_PATHS:
        return KeySource("error", error=_removed_error(_ENV_PROVIDER_PATHS[path], "from the environment"))
    return KeySource("environment", startup_key) if startup_key else source


_REMOVED_WHAT = {"op": "The 1Password reference", "command": "The credential command"}


def _removed_error(kind: str, where: str = "") -> str:
    """The one removal message per runtime kind: what was removed and from where, never a value."""
    return "%s was removed%s; configure an API key source explicitly" % (_REMOVED_WHAT[kind], " " + where if where else "")


def marker_path(path: str | None = None) -> str:
    """`service.env.source` beside the env file: the durable memory that the file's selected source was a
    runtime one. Holds the kind word, `op` or `command` (never a reference, a command or a value); absent
    otherwise."""
    return sibling_path(SOURCE_MARKER, path)


def read_marker(path: str | None = None) -> str:
    try:
        with open(marker_path(path), "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(16).strip()
    except OSError:
        return ""


def remember_file_source(path: str | None, kind: str) -> None:
    """Mirror a source selected from (or written to) the env file onto the marker: a runtime kind (`op`,
    `command`) writes its word, any other kind removes the file, so an operator's intentional switch to
    a static key is not an error at the next restart. Atomic, 0600, same directory, like write_source.
    Best effort: a read-only config directory must not fail the selection; the process-local memory
    still governs this process."""
    mp = marker_path(path)
    try:
        if kind not in RUNTIME_KINDS:
            if os.path.lexists(mp):
                os.unlink(mp)
            return
        if read_marker(path) == kind:
            return
        d = os.path.dirname(mp) or "."
        fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(mp) + ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(kind + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, mp)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError:
        pass


def read_key(path: str | None = None) -> str:
    """Legacy file reader. Provider references are never interpreted as raw keys."""
    source = read_source(path)
    return source.value if source.kind == "file" else ""


def fingerprint(key: str) -> str:
    """The ONLY renderable form of a key: first 12 hex of its sha256, "" for no key. Same value in
    the kernel log and in `romp keyswap`'s output, so an operator can check that the kernel reads
    the key they just wrote without either side ever printing it."""
    key = str(key or "")
    if not key:
        return ""
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()[:12]


def write_source(source: KeySource, path: str | None = None) -> dict:
    """Atomically select a source, removing competing key/reference assignments.

    Every other line survives byte for byte, in place — the file also carries things like
    `ROMP_PERF=1` and `ROMP_EXPECTED_AUTH`, and a rewrite that dropped them would change the
    manager's behaviour on its next start for reasons nobody would connect to a key swap. The
    key line keeps its POSITION (last assignment replaced in place, any earlier duplicate
    removed so the file cannot disagree with itself); a file with no such line gets one appended.

    Written to a temp file in the same directory, created 0600 with O_EXCL, then `os.replace` —
    so no reader ever sees a half-written file and the key is never briefly world-readable. The
    mode is the original file's, narrowed to 0600 if it granted group or other any access at all;
    a new file is 0600.

    A SYMLINKED env file is written THROUGH (2026-09-04): a dotfiles-managed `service.env` is a link,
    and an `os.replace` onto the link's own name would swap the link for a plain file and leave its
    target — what the operator's repo tracks and what a re-link would restore — on the old key.

    Returns {"path", "old", "new", "mode", "tightened", "lines", "target"} — `old`/`new` are source
    descriptors, so the caller can report their identities without resolving provider credentials;
    `target` is the file actually rewritten (the link's target, else `path`). Raises OSError on a real
    failure (the caller reports it).
    """
    source.validate()
    if source.kind not in ("op", "command", "file", "environment"):
        raise KeySourceError("Select an API key, a 1Password reference or a credential command")
    given = path or service_env_path()
    p = os.path.realpath(given) if os.path.islink(given) else given
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        existed = True
    except FileNotFoundError:
        body, existed = "", False
    old = parse_source(body)
    lines = body.splitlines()
    trailing_nl = (not body) or body.endswith("\n")
    # Which physical lines assign a source (a key, a reference or a command): the LAST one is rewritten
    # in place, earlier ones drop. Every competing kind goes, or the higher-ranking line left behind
    # would keep governing and the swap would change nothing.
    hits = [i for i, raw in enumerate(lines)
            if raw.strip() and not raw.strip().startswith("#")
            and raw.strip().partition("=")[1]
            and raw.strip().partition("=")[0].strip() in (KEY_VAR, REF_VAR, CMD_VAR)]
    new_line = "%s=%s" % ({"op": REF_VAR, "command": CMD_VAR}.get(source.kind, KEY_VAR), source.value)
    if hits:
        lines[hits[-1]] = new_line
        for i in reversed(hits[:-1]):
            del lines[i]
    else:
        lines.append(new_line)
        trailing_nl = True
    out = "\n".join(lines) + ("\n" if trailing_nl else "")
    mode, tightened = 0o600, False
    if existed:
        try:
            mode = os.stat(p).st_mode & 0o777
            if mode & 0o077:            # never leave a key group- or world-readable
                mode, tightened = 0o600, True
        except OSError:
            mode = 0o600
    d = os.path.dirname(p) or "."
    # mkstemp: same directory (so the rename is atomic — a cross-filesystem one is a copy), a name
    # nothing can collide with, and 0600 from the moment the file exists, so the key is never
    # briefly readable by anyone else.
    fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(p) + ".keyswap.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(out)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, p)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    # The durable runtime memory follows the write: a swap to a reference or a command arms it with the
    # kind word, a swap to a static key clears it, so the marker never outlives the choice it records
    # (select_source consults it).
    remember_file_source(given, source.kind if source.kind in RUNTIME_KINDS else "file")
    return {"path": given, "old": old, "new": source, "mode": mode, "tightened": tightened,
            "lines": len(lines), "target": p}


def write_key(key: str, path: str | None = None) -> dict:
    """Compatibility API for callers explicitly writing a legacy static key."""
    result = write_source(KeySource("file", key), path)
    return dict(result, old=result["old"].value if result["old"].kind == "file" else "", new=key)
