"""keysource — where the manager's API key comes from, read LIVE instead of once at startup.

The manager runs as a login service and gets its environment from `service.env`
(`~/.config/romp/service.env`; systemd reads it via `EnvironmentFile=-`, the macOS login
agent's launcher parses it before exec). Until 2026-09-04 the kernel claimed
`ANTHROPIC_API_KEY` out of its own process environment ONCE at startup, so changing which
key the sessions bill meant restarting the manager — which cuts every session's turn and
kills every subagent. This module is the live source instead: every place that needs the key
re-reads the FILE, so an edit takes effect on the next session connect with no restart.

Three properties this module exists to hold:

* **The value never lands in the kernel's own environment.** It is read, handed to one
  session's launch environment, and dropped. Nothing here writes `os.environ`.
* **The value never reaches a log, a screen or a wire.** `fingerprint()` is the only thing
  callers may print: the first 12 hex of the sha256 of the exact value. Enough to say
  "the key changed" or "both sides agree", useless to anyone who reads it.
* **A read never raises and never blocks a launch.** A missing file, a file with no
  `ANTHROPIC_API_KEY=` line, a permission error — all read as "" so the caller falls back
  to whatever the process environment carried at startup, which is exactly the old
  behaviour. The feature can only ADD a key source, never take one away.

Parsing follows the same line-by-line rule the two launchers use (never sourced, so a
malformed line is skipped rather than executed): blank and `#` lines ignored, `NAME=value`
otherwise, and the LAST assignment wins — that is what both systemd and a repeated `export`
do, so what this module reads is what the service would actually have got. One layer of
matching surrounding quotes is stripped, because systemd strips it and a quoted value would
otherwise be handed to the CLI with the quotes still on.
"""
from __future__ import annotations

import hashlib
import os
import tempfile

KEY_VAR = "ANTHROPIC_API_KEY"

# (stat identity, parsed value) for the last file read — an EVENT-keyed cache, not a timed one:
# the identity is the file's own (inode, mtime_ns, size), so a rewrite invalidates it by
# construction and a swap is picked up on the very next read. Without it, `work_key` (read per
# push through the kernel's has-a-key bool) would parse the file thousands of times a minute.
_CACHE: tuple = ((), "")


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
    `service.env.<name>` beside the live file — the convention that keeps every candidate in one
    0600 directory. Anything with a separator, or an explicit path, is taken as given."""
    name = str(name or "").strip()
    if not name:
        return ""
    if os.sep in name or name.startswith("~"):
        return os.path.expanduser(name)
    return (path or service_env_path()) + "." + name


def parse_key(text: str) -> str:
    """The value the LAST `ANTHROPIC_API_KEY=` assignment in an env-file body would set — "" when
    the body has none. Last wins, matching systemd and a repeated `export`."""
    out = ""
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.partition("=")
        if not sep or name.strip() != KEY_VAR:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]     # systemd strips one layer; without this the CLI gets the quotes
        out = value
    return out


def read_key(path: str | None = None) -> str:
    """The key the env file currently sets, or "" for every failure — missing file, no such line,
    unreadable, undecodable. Cached on the file's own stat identity (see _CACHE)."""
    global _CACHE
    p = path or service_env_path()
    try:
        st = os.stat(p)
        ident = (p, st.st_ino, st.st_mtime_ns, st.st_size)
    except OSError:
        _CACHE = ((p, "absent"), "")
        return ""
    if _CACHE[0] == ident:
        return _CACHE[1]
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            key = parse_key(fh.read())
    except OSError:
        key = ""
    _CACHE = (ident, key)
    return key


def fingerprint(key: str) -> str:
    """The ONLY renderable form of a key: first 12 hex of its sha256, "" for no key. Same value in
    the kernel log and in `romp keyswap`'s output, so an operator can check that the kernel reads
    the key they just wrote without either side ever printing it."""
    key = str(key or "")
    if not key:
        return ""
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()[:12]


def write_key(key: str, path: str | None = None) -> dict:
    """Rewrite ONLY the `ANTHROPIC_API_KEY=` line of the env file, atomically.

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

    Returns {"path", "old", "new", "mode", "tightened", "lines", "target"} — `old`/`new` are the raw
    values, for the caller to fingerprint; `target` is the file actually rewritten (the link's target,
    else `path`). Raises OSError on a real failure (the caller reports it).
    """
    given = path or service_env_path()
    p = os.path.realpath(given) if os.path.islink(given) else given
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        existed = True
    except FileNotFoundError:
        body, existed = "", False
    old = parse_key(body)
    lines = body.splitlines()
    trailing_nl = (not body) or body.endswith("\n")
    # Which physical lines assign the key: the LAST one is rewritten in place, earlier ones drop.
    hits = [i for i, raw in enumerate(lines)
            if raw.strip() and not raw.strip().startswith("#")
            and raw.strip().partition("=")[1] and raw.strip().partition("=")[0].strip() == KEY_VAR]
    new_line = "%s=%s" % (KEY_VAR, key)
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
    return {"path": given, "old": old, "new": key, "mode": mode, "tightened": tightened,
            "lines": len(lines), "target": p}
