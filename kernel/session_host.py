#!/usr/bin/env python3
"""romp-session-host: the per-session process that owns one Claude Code CLI (stage 4 of the
restart-surviving sessions program, T315; design: the T315 design note, the T295 report section 2a).

The kernel used to be the CLI's parent: its pipes were the CLI's stdio, so a kernel restart ended
every turn. The host takes the parent's place. It spawns the CLI from a SPAWN SPECIFICATION the kernel
writes (`spawn.json`: the plain-data fields of the SDK's ClaudeAgentOptions), through the SDK's own
SubprocessCLITransport when the SDK is importable (so the command line and the environment are the
SDK's, byte for byte), reads the CLI's stdout WITHOUT PAUSE and appends every message to an append-only
JOURNAL (through a writer task, so a slow disk never pauses the reader), serves one Unix socket the kernel
attaches to, holds the stage 1 LEASE as the holder, tracks every OPEN control request (a permission, a hook
callback) until a kernel's answer, the CLI's cancel or, for a hook parked with no kernel attached, its own
neutral answer before the CLI's deadline, relays stderr, and ends the CLI by closing its stdin and waiting.
A kernel that attaches after a restart replays the journal from the offset it last acknowledged, receives
every still-open request again, and sends its own initialize, which the CLI accepts as a replacement of its
hook table (the T303 probe).

The socket protocol is newline-delimited JSON frames, field `t` naming the frame:
  kernel → host: attach {kernel:{pid,start,version}, ack:N}, in {data}, ack {offset}, signal {sig},
                 end {grace}, detach, ping
  host → kernel: hello {host, cli:{pid, start, fsid, spawnedAt, login}, journal:{next}, parked:[ids]}, out {offset, data}, stderr {line},
                 exit {code, signal, cause}, fault {kind, text}, busy {kernel}, pong
One kernel is attached at a time. Connection loss without `detach` is a kernel death to the host; a
`detach` is not (the host keeps running). An unattached host whose CLI is idle past the grace ends it.

Secrets: the spec carries the environment overlay (a key helper command, PATH additions), so nothing
from the spec or any environment value is ever written to host.log, the journal or a frame.

Sibling modules are reached the kernel's way (kernel/loadsource.py under stable names); the lease
helpers come from sdk_backend, which imports without the SDK and runs nothing at import.
"""
from __future__ import annotations
import asyncio
import errno
import importlib
import importlib.metadata
import json
import os
import re
import signal
import socket
import stat
import sys
import time
import traceback
from pathlib import Path

# ── protocol constants ──────────────────────────────────────────────────────────────────────────
PROTOCOL_VERSION = 1
LEASE_HEARTBEAT_S = 3.0          # the stage 1 cadence (sdk_backend.LEASE_HEARTBEAT_S; pinned equal by a test)


def _load_state_root_mode():
    """kernel/state_root_mode.py under its fixed module name, THE SAME FILE the kernel's judge and the bus load (one
    implementation; a copy already in sys.modules under that name is reused). A loader, not a copy of the predicate:
    tests/test_state_root_mode.py's OneText pins that this file defines none of its functions."""
    import importlib.util
    name = "romp_state_root_mode"
    mod = sys.modules.get(name)
    if mod is not None:
        return mod
    path = Path(__file__).resolve().parent / "state_root_mode.py"
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


_srm = _load_state_root_mode()


def state_root_gate(root, where, log=None, stop=None):
    """THE STATE ROOT'S CHECK IN THE SESSION HOST (round 3 of the state-root review, extra8-3: this process is on by
    default, writes its lease under the root every LEASE_HEARTBEAT_S and is built to outlive the kernel, so the kernel's
    exit 2 on a hostile root stopped nothing here until round 4). The one implementation, kernel/state_root_mode.py:
    the root is READ, judged by the discriminator (an other write bit, or a group write bit under a group that is not
    the owner's private group, refuses; a lookup that fails refuses with its own remedy; a path that is not a directory
    refuses with ENOTDIR; an unreadable root is unknown, refuse-class), THEN repaired best-effort. At `where` "start" a
    pre-existing root that held entries and read writable by another local user is refused whatever the chmod did
    (the import-read rule, in the kernel's words). A refuse or unknown verdict: the full line on stderr (this uid's
    surface), one host.log row through `log` (kind "state-root-refused": the errno name and the verdict, never a
    path), and `stop(2)` (os._exit by default: no drain, no further write, the same shape as the kernel's runtime
    exit; the CLI child loses its stdin and ends). Returns the check dict otherwise; a warn root (0755, or 0775 under
    the private group) is re-tightened and said once on stderr."""
    chk = _srm.check(root, list_entries=(where == "start"))
    verdict, line = chk["verdict"], chk["line"]
    if where == "start" and verdict != "unknown" and chk["modeRead"] is not None and not chk["notDirectory"]:
        empty = chk["entries"] is not None and len(chk["entries"]) == 0
        ref = _srm.import_read_refusal(root, chk["modeRead"], (chk["uid"], chk["gid"]), "start",
                                       repair_error=chk["repairError"], empty=empty)
        if ref is not None:
            verdict, line = "refuse", ref["line"]
    if verdict in ("refuse", "unknown"):
        try:
            sys.stderr.write("romp-session-host: %s. The host stops now (exit 2; found at %s).\n" % (line, where))
            sys.stderr.flush()
        except Exception:
            pass
        if log is not None:
            try:
                log("state-root-refused", verdict=verdict, where=where, errno=chk.get("statErrno") or chk.get("repairErrno") or "")
            except Exception:
                pass
        (stop or os._exit)(2)
        return chk
    if line and where == "start":
        try:
            sys.stderr.write("romp-session-host: %s\n" % line)
        except Exception:
            pass
    return chk
HOOK_TIMEOUT_S = 540.0           # what the kernel registers on every hook matcher (inside the CLI's 600 s default)
HOOK_SELF_ANSWER_S = 480.0       # a parked hook is answered by the host after this much parking, unattached
END_GRACE_DEFAULT_S = 120.0      # `end` without a grace: the long bound (conserve_close, request_reconnect)
END_GRACE_KILL_S = 5.0           # the kernel's kill: `end` with this bound
UNATTACHED_GRACE_DEFAULT_S = 900.0   # an idle CLI with no kernel attached for this long is ended (a setting)
JOURNAL_SEGMENT_BYTES = 64 * 1024 * 1024
READER_BEHIND_RECORDS = 5000     # records read but not yet on disk before the host says so
ACK_NONE = -1
EXIT_FLUSH_S = 2.0               # how long the exiting host waits for an attached kernel to take its last frames
GAP_TYPE = "romp-journal-gap"     # a record the journal could not write: a marker keeps the numbering, readers skip it
END_SENTINEL = object()          # on the stdin pump: close the CLI's stdin after everything queued before it

# ── the SDK the host's private imports are written against ──────────────────────────────────────
# _spawn drives the SDK's SubprocessCLITransport, a PRIVATE class (claude_agent_sdk._internal), and reads its
# _process attribute; neither is part of the SDK's public surface, so any release may move or rename them.
# Until 2026-09-18 bin/romp-sdk-setup upgraded the package unpinned while this module imported the internals
# with no check, so a release that moved one would have failed every hosted session launch with the install
# step none the wiser (the box admin's hazard review of the pull-in, 2026-09-16). This constant is the ONE
# declaration of the version those imports were verified against: bin/romp-sdk-setup reads it (a sed over
# this line) and installs exactly that version, and sdk_internals() below compares the version the host imports
# (installed_sdk_version) to it before the import. Bumping it is a deliberate act: install the new version, run
# the host tests on it, then move the number. Format: the bare version string, double-quoted, on this one line.
SDK_TESTED_VERSION = "0.2.156"
SDK_DIST = "claude-agent-sdk"                 # the distribution name importlib.metadata and pip know
SDK_PACKAGE = "claude_agent_sdk"              # the import name; a ModuleNotFoundError naming a module under it is the SDK's own
SDK_REPIN_COMMAND = "bin/romp-sdk-setup"      # what installs the tested version
# (module, name) for every private SDK name this module reaches at import; the check resolves each one
SDK_INTERNALS = (("claude_agent_sdk._internal.transport.subprocess_cli", "SubprocessCLITransport"),)
ERROR_CHAIN_CAP = 5                           # chained type names a row carries at most (a chain is short; a cycle is not)


def error_chain(e: "BaseException | None") -> str:
    """The type names behind `e`, comma-joined: its `__cause__` (an explicit `raise ... from`) or, when the context is
    not suppressed, its `__context__`, followed the way the traceback module prints a chain, at most ERROR_CHAIN_CAP
    deep. Type names only, never a message (a message could carry a line of the CLI's output or a path). "" for a
    bare exception. The SDK's connect() wraps every failure inside it as CLIConnectionError from the original (its
    subprocess_cli, verified at 0.2.156), so a drifted call inside connect reaches the host as a connection error
    whose cause is the TypeError, and a missing binary as one whose cause is the FileNotFoundError; the
    cli-spawn-failed row carries this chain (`causes`) so a reader of host.log, or of the host.spawn-failed row the
    kernel files from it, sees what the wrap hid. A recorded fact only: nothing reads the chain to decide what a
    failure means (the closing check of the review, 2026-09-18, retired the type-name allowlist that did; a
    type name is not a diagnosis, and the SDK's own option validation raises ValueError under drift as readily as
    a dependency raises TypeError under none)."""
    names, seen = [], {id(e)}
    while e is not None and len(names) < ERROR_CHAIN_CAP:
        nxt = e.__cause__ if e.__cause__ is not None else (None if e.__suppress_context__ else e.__context__)
        if nxt is None or id(nxt) in seen:
            break
        seen.add(id(nxt))
        names.append(type(nxt).__name__)
        e = nxt
    return ",".join(names)


class SdkInternalsMismatch(RuntimeError):
    """A private name the host drives is gone: on another version than the tested one a mismatch (sdk_mismatch_text),
    on the tested version itself a broken install (sdk_broken_install_text; tests-2, round 1 of the review,
    2026-09-18). Raised out of the spawn and carried whole into the host-crashed record and the kernel's launch
    error: the text is the host's own (two version strings, a module path, the remedy, and the bounded type and
    message of the import error behind it), never a spec field or an environment value."""


SDK_CAUSE_CAP = 200                          # the cause's type and message appended to a mismatch text, bounded to this many
#                                              characters: the host-composed row's cap. The generic host-crashed row carries the
#                                              class, the errno and the frame, never text (main()), so no cap applies to it.


def installed_sdk_version() -> "str | None":
    """The version of the claude-agent-sdk this process imports: the package's own `__version__` when the import
    gives one, else its distribution metadata, else None (importable, but a source checkout with neither).

    The module first, the metadata second (the closing check of the review, 2026-09-18): the pin exists to know
    WHICH CODE IS RUNNING, and importlib.metadata describes what was installed, which is not always the same
    thing. A copy of the package ahead of the tested site on sys.path with no dist-info of its own (a checkout on
    PYTHONPATH, a vendored tree) imports at ITS version while the metadata still reports the tested one, so a
    metadata-only read said "tested", took the direct import road, and a moved internal died as a bare
    AttributeError with no version anywhere. The imported module is the authoritative source; the metadata is the
    reconstruction, kept for a package that exports no `__version__`. An import that fails here is not reported
    here: the internals import that follows raises the same error onto its own road."""
    try:
        mod = importlib.import_module(SDK_PACKAGE)
    except Exception:                    # sdk_internals imports the same package next and raises there, as before
        mod = None
    v = getattr(mod, "__version__", None) if mod is not None else None
    if isinstance(v, str) and v:
        return v
    try:
        return importlib.metadata.version(SDK_DIST)
    except importlib.metadata.PackageNotFoundError:
        return None


def sdk_mismatch_text(installed, missing: str, cause: "BaseException | None" = None) -> str:
    """The loud verdict for another version whose private name `missing` is gone. `cause` is the import error behind
    it, appended as its bounded type and message (fresh-1, round 1 of the review, 2026-09-18): before that the verdict
    replaced the error, so the fact that named the real trouble (which module was missing) reached no log, no stderr
    and no card."""
    text = ("%s %s is installed, but the session host is written against %s and this version has no %s; "
            "run %s to install the tested version"
            % (SDK_DIST, installed or "(version unknown: no package metadata)", SDK_TESTED_VERSION, missing, SDK_REPIN_COMMAND))
    if cause is not None:
        text += " (%s)" % ("%s: %s" % (type(cause).__name__, cause))[:SDK_CAUSE_CAP]
    return text


def sdk_broken_install_text(installed, missing: str) -> str:
    """The verdict for the TESTED version missing a private name the host reads: the install is broken, not the
    version (tests-2, round 1 of the review, 2026-09-18: the `_process` guard used to claim a mismatch about a
    matching version and offer a repin that pip reports as already satisfied, a remedy that changes nothing). The
    remedy here is a rebuild of the venv: remove it, then run the setup script, which builds it afresh."""
    return ("%s %s is installed, the version the session host is written against, but %s is missing: the install is "
            "broken (a partial or edited SDK venv), not the version; remove the SDK venv under the state directory "
            "and run %s to rebuild it"
            % (SDK_DIST, installed or "(version unknown: no package metadata)", missing, SDK_REPIN_COMMAND))


def _version_relation(installed, tested) -> str:
    """'newer' or 'older' by the dotted numeric parts, 'different' when either does not parse that way."""
    def key(v):
        parts = []
        for piece in str(v or "").split("."):
            digits = ""
            for ch in piece:
                if not ch.isdigit():
                    break
                digits += ch
            if not digits:
                return None
            parts.append(int(digits))
        return tuple(parts) or None
    a, b = key(installed), key(tested)
    if a is None or b is None or a == b:
        return "different"
    return "newer" if a > b else "older"


def sdk_internals(installed=None, log=None) -> dict:
    """The private SDK names in SDK_INTERNALS, resolved, by name. `installed` is the installed version (read from
    the package metadata when None); `log` is the host's log(kind, **fields), or None.

    The tested version imports directly, as before the check existed: a failure there is a broken install and
    surfaces as the raw ImportError. Any other version resolves each name inside a try, and a name that is gone
    raises SdkInternalsMismatch naming the installed version, the tested one and the repin command (never a
    degraded transport: the pipe transport is for machines with no SDK at all, and a host that ran on it here
    would hide the very breakage this exists to show). A version whose internals still resolve proceeds with one
    log row saying it is newer or older than the tested one, so a working-by-luck machine is visible.

    "Gone" is an AttributeError (the module is there, the name is not) or a ModuleNotFoundError naming the SDK's
    own module path. Any other ImportError from inside the private module is re-raised whole onto the generic
    cli-spawn-failed road (fresh-1, round 1 of the review, 2026-09-18): until then every ImportError became a
    confident "this version has no <name>", so a broken dependency chain (the leaf's own `import anyio` failing)
    was reported as drift and its real cause dropped. The verdict that does fire carries the cause's bounded
    type and message (sdk_mismatch_text), so the fact that names the trouble travels either way."""
    if installed is None:
        installed = installed_sdk_version()
    if installed == SDK_TESTED_VERSION:
        return {name: getattr(importlib.import_module(mod), name) for mod, name in SDK_INTERNALS}
    found = {}
    for mod, name in SDK_INTERNALS:
        try:
            found[name] = getattr(importlib.import_module(mod), name)
        except AttributeError as e:
            raise SdkInternalsMismatch(sdk_mismatch_text(installed, mod + "." + name, cause=e)) from e
        except ModuleNotFoundError as e:
            if not str(getattr(e, "name", "") or "").startswith(SDK_PACKAGE):
                raise                       # a missing third-party module, not a moved internal: the real error, whole
            raise SdkInternalsMismatch(sdk_mismatch_text(installed, mod + "." + name, cause=e)) from e
    if log is not None:
        log("sdk-version-untested", installed=installed or "unknown", tested=SDK_TESTED_VERSION,
            relation=_version_relation(installed, SDK_TESTED_VERSION))
    return found


# The neutral answer the host gives a parked hook callback when no kernel returned in time, PER EVENT
# KIND: the empty output, which is what romp's own hook callbacks return when they have nothing to say
# (no `decision`, no `permissionDecision`, so the CLI applies its normal flow). Kept as a table, not a
# single assumed object, so a future PreToolUse hook gets its own entry (an empty output there is also
# neutral: the CLI falls through to the permission flow). A test pins that every event the kernel's
# _options registers has a row here.
HOOK_NEUTRAL_OUTPUT = {
    "Stop": {},
    "UserPromptSubmit": {},
    "SubagentStart": {},
    "SubagentStop": {},
    "PostToolUse": {},
    "PostToolUseFailure": {},
    "PreToolUse": {},
}

# The ClaudeAgentOptions fields the spawn specification carries: every plain-data field the SDK's
# SubprocessCLITransport reads to build the command line and the environment. The kernel writes exactly
# these; a test compares the list against the fields `_build_command` and `connect` reference.
SPEC_FIELDS = ("cli_path", "cwd", "env", "permission_mode", "permission_prompt_tool_name", "resume",
               "session_id", "resume_session_at", "fork_session", "extra_args", "settings", "mcp_servers",
               "system_prompt", "model", "effort", "include_partial_messages", "enable_file_checkpointing",
               "max_buffer_size", "setting_sources", "add_dirs", "allowed_tools", "disallowed_tools",
               "max_turns", "continue_conversation", "fallback_model", "thinking", "max_thinking_tokens")
# Spec keys that are the host's own, not option fields
SPEC_HOST_KEYS = ("sid", "name", "version", "hook_timeout_s", "hook_self_answer_s", "unattached_grace_s",
                  "state_dir", "protocol", "reader_behind_records",
                  "login")    # the IDENTIFIER of the stored login the launch bills ("" = the machine's own), echoed in the
#                               hello's cli.login so an attaching kernel stamps the login the launch USED, not the one
#                               today's availability would pick (2026-09-14); never a token, key or other credential value
# Testing seams the spec may carry (never set by the kernel): a delay per journal write, an offset whose
# write raises. They exist so the reader-behind fault and the journal-fault path can be driven in a test.
SPEC_TEST_KEYS = ("_test_journal_delay_s", "_test_journal_fault_at", "_test_journal_gap_fault")


def encode_frame(obj: dict) -> bytes:
    """One frame: compact JSON plus a newline."""
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")


class FrameReader:
    """Newline-delimited JSON frames out of arbitrary byte chunks. A line that is not JSON is dropped
    with a note (the peer is ours; a corrupt line is a bug, never a protocol branch)."""

    def __init__(self, on_bad=None):
        self._buf = b""
        self._on_bad = on_bad

    def feed(self, chunk: bytes):
        self._buf += chunk
        out = []
        while True:
            nl = self._buf.find(b"\n")
            if nl < 0:
                break
            line, self._buf = self._buf[:nl], self._buf[nl + 1:]
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                if self._on_bad:
                    self._on_bad(len(line))
                continue
            if isinstance(obj, dict):
                out.append(obj)
        return out


# ── the journal ─────────────────────────────────────────────────────────────────────────────────
def _segment_first(name: str):
    """The first offset a segment file name carries (`journal-<firstoffset>.jsonl`), or None."""
    stem = name[:-len(".jsonl")] if name.endswith(".jsonl") else name
    if not stem.startswith("journal-"):
        return None
    tail = stem[len("journal-"):]
    return int(tail) if tail.isdigit() else None


class Journal:
    """Append-only record of every message the CLI emitted, one JSON object per line, in SEGMENTS named by
    the offset of their FIRST record (`journal-<firstoffset>.jsonl`) under the host directory. A record's
    OFFSET is its ordinal since the CLI started, global across segments; the file names carry the
    numbering, so a reader that finds only later segments (earlier ones acknowledged and deleted) still
    numbers every record right. The in-memory index maps an offset to (segment, byte position) so a reader
    can start anywhere. A new segment starts at a turn boundary (a `result` record) once the current one
    exceeds `segment_bytes`; a segment whose last record has been ACKNOWLEDGED and that is not the current
    one is deleted at the next turn boundary."""

    def __init__(self, directory, segment_bytes=JOURNAL_SEGMENT_BYTES, root=None):
        # the guarded reader over the state root (the host passes it; the host directory is <root>/hosts/<sid>), or over the
        # journal directory itself when no root is named (a bare Journal in a test): a segment replaced by a symlink or a
        # foreign-owned file while the root was writable is quarantined and read as absent
        self._gr = _srm.Reader(lambda: Path(root) if root is not None else Path(directory), who="session-host")
        # the host's own creator of hosts/<sid>/ (the kernel's write_spawn_spec is the other), so the same owner-only
        # shape: a symlink or a foreign directory standing at the path is refused before the first segment is opened
        # (the review of the socket-mode fix, round 2, 2026-09-19: the bare mkdir here followed a planted symlink and
        # wrote the journal through it). A refusal raises out of SessionHost's constructor, so main() never runs a host
        # over a directory it does not own. What the kernel that launched the host sees is the exit code (1) and the
        # traceback on the host's captured stderr (hosts/<sid>/host.stderr), not the OSError itself: no host.log row
        # exists for a refusal here, since the constructor is what opens the directory (round 3, 2026-09-19).
        self.dir = owner_only_dir(directory, "host directory")
        self.segment_bytes = int(segment_bytes)
        self.next_offset = 0
        self.acked = ACK_NONE
        self._index: list[tuple[int, int]] = []       # offset -> (segment first offset, byte position)
        self._seg_last: dict[int, int] = {}           # segment first offset -> last offset in it
        self.gaps: set = set()                        # offsets with no bytes on disk (a double write failure)
        self._seg = 0
        self._fh = None
        self._pos = 0
        self._open_segment(0)

    def _path(self, seg: int) -> Path:
        return self.dir / ("journal-%d.jsonl" % seg)

    def _open_segment(self, first: int) -> None:
        if self._fh is not None:
            self._fh.close()
        self._seg = first
        # UNBUFFERED: a write that fails leaves nothing pending in a buffer to land later at a stale position
        # (a buffered handle keeps the bytes of a failed flush and writes them on the next one; the commit-5
        # review's finding a)
        self._fh = _srm.open_private(self._path(first), "ab", buffering=0)   # born 0600 under any umask (round 4f), the open by path as before
        self._pos = self._fh.tell()

    def append(self, record: dict) -> int:
        """Append one record; returns its offset. Written straight to the file (unbuffered), so a kernel that
        attaches reads what the host wrote. Raises on a write failure, and then NOTHING has moved: the
        segment is truncated back to the last good position and no index, position or offset changed; the
        caller decides (the writer task notes a gap)."""
        line = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
        off = self.next_offset
        try:
            written = 0
            while written < len(line):          # loop-ok: a raw write may be partial; bounded by the line's length
                n = self._fh.write(line[written:])
                if not n:
                    raise OSError("short write to the journal")
                written += n
        except Exception:
            try:
                os.ftruncate(self._fh.fileno(), self._pos)
                self._fh.seek(self._pos)
            except Exception:
                # the segment cannot be put back (a partial write that will not truncate): its byte positions are
                # unreliable from here, so it is left behind and a fresh segment starts at this offset (finding 11)
                try:
                    self._open_segment(off)
                except Exception:
                    pass
            raise
        self._index.append((self._seg, self._pos))
        self._seg_last[self._seg] = off
        self._pos += len(line)
        self.next_offset = off + 1
        if record.get("type") == "result":
            self._turn_boundary()
        return off

    def note_gap(self, off: int) -> None:
        """A record whose write failed twice (the record and its gap marker): the index gains a ZERO-LENGTH
        entry at the current position and the offset advances, so index and offsets stay in lockstep (a
        reader skips the entry; the commit-5 review's finding b)."""
        if off != self.next_offset:
            return
        self._index.append((self._seg, self._pos))
        self._seg_last[self._seg] = off
        self.gaps.add(off)
        self.next_offset = off + 1
        self._persist_gaps()

    def _persist_gaps(self) -> None:
        """gaps.json for the ORPHAN reader (which has no index): written to a temp name and renamed over, never
        in place. On the very full disk that made the gap an in-place rewrite truncates first and then fails,
        erasing the record the reader needs (the commit-8 review's item 2); a rename either lands the new file
        whole or leaves the old one standing."""
        tmp = self.dir / "gaps.json.tmp"
        try:
            with _srm.open_private(tmp, "wb") as f:
                f.write(json.dumps(sorted(self.gaps)).encode("utf-8"))
            os.replace(tmp, self.dir / "gaps.json")
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _turn_boundary(self) -> None:
        # rotate when the current segment is past its size; drop segments the kernel has fully acknowledged
        if self._pos >= self.segment_bytes:
            self._open_segment(self.next_offset)
        for seg in sorted(self._seg_last):
            if seg == self._seg:
                continue
            if self._seg_last[seg] <= self.acked:
                try:
                    os.unlink(self._path(seg))
                except OSError:
                    pass
                self._seg_last.pop(seg, None)

    def ack(self, offset: int) -> None:
        if offset > self.acked:
            self.acked = min(int(offset), self.next_offset - 1)

    def segments(self) -> list[int]:
        """The first offsets of the segments still on disk, in order (the current one included, records or not)."""
        return sorted(set(self._seg_last) | {self._seg})

    def read_from(self, offset: int, end: int | None = None):
        """Yield (offset, record) for every record from `offset` up to `end` (exclusive; the live count when
        None), by the index: each record is read at its recorded position, so a gap (an unrecorded one, a
        zero-length index entry, or a written gap marker) is skipped without disturbing the numbering. A
        record whose segment was deleted (acknowledged long ago) is skipped too."""
        offset = max(0, int(offset))
        stop = self.next_offset if end is None else min(int(end), self.next_offset)
        fh, cur_seg = None, None
        try:
            while offset < stop:
                if offset in self.gaps:
                    offset += 1
                    continue
                seg, pos = self._index[offset]
                if seg != cur_seg:
                    if fh is not None:
                        fh.close()
                    cur_seg = seg
                    try:
                        fh = self._gr.open(self._path(seg), "rb")
                    except OSError:
                        fh = None
                if fh is None:
                    offset += 1
                    continue
                fh.seek(pos)
                line = fh.readline()
                try:
                    rec = json.loads(line) if line.strip() else None
                except ValueError:
                    rec = None
                if rec is not None and rec.get("type") != GAP_TYPE:
                    yield offset, rec
                offset += 1
        finally:
            if fh is not None:
                fh.close()

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


# THE ORPHAN READER LIVES IN THE KERNEL'S MODULE (kernel/host_transport.py, read_journal_dir and journal_segments) since
# the fork PR that follows #814 (2026-09-21, the item "the journal reads descend by descriptor" of the general notes'
# small-asks file). Through #814 `read_journal_dir(directory, offset)` stood here and read by PATH, three of the item's
# five sites: a glob over the directory for the segments, gaps.json by the directory's path, each segment by the path
# the glob yielded; a `<sid>/` re-pointed between the kernel's descent and those reads was read through the link, and
# a journal file a peer planted under a loose `<sid>/` of the kernel's uid was read with no owner check. The rewrite
# takes the <sid> DESCRIPTOR the kernel's read descent holds, lists off it and opens each file by name under it through
# the one reader every kernel read under hosts/<sid>/ goes through (the owner question before the open, the
# O_NOFOLLOW|O_NONBLOCK open, the fstat of the descriptor), which is why it moved: that reader and the refusal classes
# it answers with are the kernel's, and this module, the host's, imports nothing of the kernel's. THE HOST NEVER CALLED
# THE PREDECESSOR: the host reads its own journal through Journal.read_from, off the in-memory index of the segments it
# wrote itself under a directory owner_only_dir verified (0700, its own uid; Journal.__init__), and lists its directory
# for nothing, so the host side had no caller to convert and asks no owner question of its own directory
# (tests/test_session_host.py pins both, by execution and by structure). The design in full is stated at
# host_transport.read_journal_dir.


# ── open control requests ───────────────────────────────────────────────────────────────────────
class Parked:
    """EVERY control request the CLI sent that nobody has answered yet, attached or not: a kernel's
    control_response retires it, the CLI's cancel drops it, and a hook parked while no kernel is attached
    is answered by the host itself after `self_answer_s`. On attach the open ids ride `hello` and their
    records are sent again (whatever the acknowledged offset says: a request delivered live to a kernel that
    then died was received, never answered). `answered` remembers ids already answered, so a late duplicate
    answer is dropped. `unattached_since` marks when a request began waiting with no kernel."""

    def __init__(self, self_answer_s=HOOK_SELF_ANSWER_S):
        self.self_answer_s = float(self_answer_s)
        self.open: dict[str, dict] = {}        # request id -> {kind, offset, t, callback_id, event, record, unattached_since}
        self.answered: set[str] = set()

    def park(self, request: dict, offset: int, now: float, attached: bool) -> None:
        rid = str(request.get("request_id") or "")
        req = request.get("request") if isinstance(request.get("request"), dict) else {}
        if not rid or rid in self.answered:
            return
        self.open[rid] = {"kind": str(req.get("subtype") or ""), "offset": offset, "t": now,
                          "callback_id": req.get("callback_id"), "tool_use_id": req.get("tool_use_id"),
                          "event": _hook_event_of(req), "record": request,
                          "unattached_since": None if attached else now}

    def detached(self, now: float) -> None:
        """The kernel left: every open request starts its unattended clock now (if not already running)."""
        for v in self.open.values():
            if v.get("unattached_since") is None:
                v["unattached_since"] = now

    def attached(self) -> None:
        for v in self.open.values():
            v["unattached_since"] = None

    def cancel(self, rid: str) -> bool:
        return self.open.pop(str(rid), None) is not None

    def answer(self, rid: str) -> bool:
        """A response reached the CLI for `rid`: True when it was open (first answer), False when it was
        already answered or never parked (a dead kernel's leftover, dropped by the caller)."""
        rid = str(rid)
        self.open.pop(rid, None)
        if rid in self.answered:
            return False
        self.answered.add(rid)
        return True

    def due_hooks(self, now: float) -> list[str]:
        """The hook callbacks that have waited `self_answer_s` or longer with no kernel attached, oldest first."""
        due = [(v["unattached_since"], rid) for rid, v in self.open.items()
               if v["kind"] == "hook_callback" and v.get("unattached_since") is not None
               and now - v["unattached_since"] >= self.self_answer_s]
        return [rid for _, rid in sorted(due)]

    def ids(self) -> list[str]:
        return sorted(self.open, key=lambda r: self.open[r]["offset"])

    def records(self) -> list[tuple[int, dict]]:
        """The open requests' journal offsets and records, in offset order (re-sent on attach)."""
        return sorted(((v["offset"], v["record"]) for v in self.open.values()), key=lambda x: x[0])


def _hook_event_of(req: dict) -> str:
    inp = req.get("input") if isinstance(req.get("input"), dict) else {}
    return str(inp.get("hook_event_name") or "")


def neutral_hook_response(request_id: str, event: str) -> dict:
    """The control_response frame the host writes for a parked hook it answers itself."""
    return {"type": "control_response",
            "response": {"subtype": "success", "request_id": request_id,
                         "response": dict(HOOK_NEUTRAL_OUTPUT.get(event, {}))}}


# ── the spawn specification ─────────────────────────────────────────────────────────────────────
def spec_to_options(spec: dict, stderr_cb):
    """A ClaudeAgentOptions from the spec's plain-data fields, plus the host's stderr relay. Only the
    SDK's fields; the host's own keys (SPEC_HOST_KEYS, SPEC_TEST_KEYS) are left out. Requires the SDK."""
    from claude_agent_sdk import ClaudeAgentOptions
    kw = {k: spec[k] for k in SPEC_FIELDS if k in spec and spec[k] is not None}
    kw["stderr"] = stderr_cb
    return ClaudeAgentOptions(**kw)


class PipeCliTransport:
    """The host's built-in transport for a CLI when the SDK is NOT importable: the hermetic tests and
    CI, which install no SDK. Same duck-typed surface as the SDK's SubprocessCLITransport (connect,
    read_messages, write, end_input, close, pid); the command line carries the stream-json flags and
    the spec's permission tool and resume fields only. A real install always has the SDK (the kernel
    refuses SDK sessions without it), so this never drives a real CLI; it drives the fake one."""

    def __init__(self, spec: dict, stderr_cb):
        self.spec = spec
        self._stderr_cb = stderr_cb
        self.proc = None
        self._stderr_task = None

    @property
    def pid(self):
        return self.proc.pid if self.proc else None

    def _argv(self) -> list[str]:
        s = self.spec
        argv = [str(s["cli_path"]), "--output-format", "stream-json", "--verbose", "--input-format", "stream-json"]
        if s.get("permission_prompt_tool_name"):
            argv += ["--permission-prompt-tool", str(s["permission_prompt_tool_name"])]
        if s.get("permission_mode"):
            argv += ["--permission-mode", str(s["permission_mode"])]
        if s.get("resume"):
            argv.append("--resume=%s" % s["resume"])
        if s.get("session_id"):
            argv.append("--session-id=%s" % s["session_id"])
        for flag, value in (s.get("extra_args") or {}).items():
            argv.append("--%s" % flag if value is None else "--%s=%s" % (flag, value))
        return argv

    async def connect(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["CLAUDE_CODE_ENTRYPOINT"] = "sdk-py"
        env.update({str(k): str(v) for k, v in (self.spec.get("env") or {}).items()})
        if self.spec.get("cwd"):
            env["PWD"] = str(self.spec["cwd"])
        self.proc = await asyncio.create_subprocess_exec(
            *self._argv(), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, cwd=self.spec.get("cwd") or None, env=env,
            limit=int(self.spec.get("max_buffer_size") or 100 * 1024 * 1024))
        self._stderr_task = asyncio.ensure_future(self._relay_stderr())

    async def _relay_stderr(self):
        try:
            while True:
                line = await self.proc.stderr.readline()
                if not line:
                    return
                self._stderr_cb(line.decode("utf-8", "replace").rstrip("\n"))
        except Exception:
            return

    async def read_messages(self):
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj
        await self.proc.wait()

    async def write(self, data: str) -> None:
        self.proc.stdin.write(data.encode("utf-8"))
        await self.proc.stdin.drain()

    async def end_input(self) -> None:
        try:
            self.proc.stdin.close()
        except Exception:
            pass

    async def close(self) -> None:
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.kill()
            except ProcessLookupError:
                pass
            await self.proc.wait()

    @property
    def returncode(self):
        return self.proc.returncode if self.proc else None


# The AF_UNIX path budget. sun_path is 108 bytes on Linux and 104 on macOS, and CPython's bind and connect refuse a
# path that does not fit with its terminating NUL ("AF_UNIX path too long", socketmodule's getsockaddrarg), so the
# longest path either side can use is one byte less. A published socket path over this is one the kernel can never
# connect to, and _prepare_socket checks the PUBLISHED path against it before the CLI is spawned and so before any
# lease exists (round 3 of this fix; the check sat in _serve_socket, after the lease, through round 2): the bind's own
# check was the only enforcement of the budget on that path while the bind took the published name, and it moved onto
# the temp name when the temp got a name of its own, so at a published path of exactly 108 bytes the temp bound, the
# rename published an unreachable socket and the host logged socket-ready and kept its lease and its CLI, where the
# code before failed the bind loudly (the review of this fix, 2026-09-19). tests/test_session_host.py SocketBudget
# derives the number by binding throwaway sockets at the lengths around it, so this is a measured limit, not an
# assumed one.
SOCK_PATH_MAX = 103 if sys.platform == "darwin" else 107

_TEMP_DIGITS = "0123456789abcdefghijklmnopqrstuv"        # base 32 as int(s, 32) reads it back
_TEMP_NAME = re.compile(r"^([0-9a-v]{5})[0-9a-v]{4}\.tmp$")


def _b32(n: int, width: int) -> str:
    digits = []
    while n:
        n, r = divmod(n, 32)
        digits.append(_TEMP_DIGITS[r])
    return "".join(reversed(digits)).rjust(width, "0")


def sock_names(sid: str) -> tuple[str, str]:
    """The control socket's two file names under `hosts/`: the published `<sid8>.sock` (the name the kernel's host_sock
    builds) and a fresh WRITER-UNIQUE temp it is bound at first: this process's pid in five base-32 digits (pid_max is
    2^22 on Linux, four digits and a bit), 20 random bits in four more, then `.tmp`. Unique to the writer as write_reg's
    and write_lease's temps are (kernel/sdk_backend.py), so the rename can only ever publish the socket this host bound:
    the fixed `<sid8>.tmp` of the first cut was the shared-name hazard (the review of this fix, 2026-09-19: a second
    host for the sid unlinking and rebinding that name between the first host's bind and its rename made the first
    publish, and report ready on, a socket it never created). Exactly the published name's length, 13 bytes for the
    uuid sids the kernel mints (host_sock takes the first 8 characters), because the published path is what the socket
    path budget (SOCK_PATH_MAX) is spent on: under the test harness's deepest hosts-on root it sits at TMPDIR + 70 bytes
    (one `romp-tests-*` level per process since 2026-09-21; two under xdist before, which put `hosts/<sid8>.sock` at 107
    exactly under a 17-byte TMPDIR — tests/test_tempdir_hygiene.py HarnessSocketBudget derives the figure), so wherever
    the published path fits the budget exactly a temp longer than it would fail the bind where the published name fits.
    A sid shorter
    than 8 characters is not a shape the kernel produces: its temp is longer than its published name, and a temp over
    the budget fails the bind loudly (socket-bind-failed) rather than publishing anything. tests/test_session_host.py
    SocketMode pins the form, the length and the uniqueness."""
    rnd = int.from_bytes(os.urandom(3), "big") >> 4
    return sid[:8] + ".sock", _b32(os.getpid(), 5) + _b32(rnd, 4) + ".tmp"


def temp_owner_pid(name: str) -> int | None:
    """The pid a socket temp name (sock_names) embeds, or None for any other name: the stale-temp sweep
    (_sweep_stale_temps, run from _prepare_socket) unlinks a temp only when its owner is gone, and touches no name
    whose form this code did not mint."""
    m = _TEMP_NAME.match(name)
    return int(m.group(1), 32) if m else None


def owner_only_dir(path, what: str = "directory", parents: bool = False) -> Path:
    """`path` as a directory made owner-only (0700), REFUSED when it is not ours, and kept so; returns it. The one shape
    for every directory under `hosts/` this code creates: `hosts/` itself (hosts_dir) and each session's `hosts/<sid>/`
    (the kernel's write_spawn_spec in kernel/host_transport.py, and Journal.__init__, the host's own creator of the same
    directory). Round 1 of the socket-mode fix (2026-09-19) installed these checks on `hosts/` alone and left
    `hosts/<sid>/`, made one line below by the same function with a bare mkdir and a chmod never read back, on the old
    shape, so a symlink planted there was followed and the spec, host.log and the journal were written through it; the
    review's round 2 asked for one helper both directories go through, not a second copy. The checks are
    kernel/judge.py's _ensure_judge_scratch, taken whole: the mkdir carries the mode, so a fresh directory is born 0700
    under any umask (never made by the umask of whichever process got there first); lstat, not stat, so a symlink
    planted at the path is refused instead of passing every check on behalf of its target; a directory another uid owns
    is refused; a loose one we own is tightened (every install before 2026-09-19 made `hosts/` at the umask's mode, 0775
    under the 002 the live host runs at: ours, so a repair, not a guess), and the mode is read back, so a tighten that
    did not take raises instead of returning. `parents` is False unless the caller says otherwise, because an
    intermediate directory mkdir creates takes the umask's mode, the very shape this closes: hosts_dir makes `hosts/`
    before anything below it is made. `what` names the directory in the refusals (`hosts directory`, `host directory`),
    each of which carries the path, so a launch error or a traceback says which directory it was.
    WHAT THIS CLOSES, AND WHAT IT DOES NOT (the review's round 2, from its refuters): the static shape, a symlink, a
    foreign directory or a loose one standing at the path when the call runs. Not a re-point between the chmod's read-back
    and the caller's open: a race-free version needs directory-descriptor-relative calls (mkdirat, openat, fchmod on the
    descriptor), and the files written below these directories take paths. The reachable cases are narrow: an
    attacker-owned target raises PermissionError at the chmod before any write, so what lands content is that TOCTOU
    flip or a target the operator already owns, and either needs a state root that is not 0700 while a session starts.
    On this deployment the root reads 0700 because kernel/judge.py chmods it at import, best-effort (the OSError
    swallowed, the mode read back once and reported on stderr when it is not 0700), and nothing re-checks or guards it
    afterwards (extra6-1, round 5 of the review, 2026-09-20: an attempt at startup, not a standing property of the
    box). tests/test_judge_scratch_private.py OwnerOnlyParity runs this and the judge copy over one
    table of setups and holds their outcomes equal."""
    d = Path(path)
    d.mkdir(mode=0o700, parents=parents, exist_ok=True)
    st = os.lstat(d)                            # lstat, not stat: a symlink planted in our place would
    if not stat.S_ISDIR(st.st_mode):            # otherwise pass every check below on behalf of its target
        raise OSError("%s %s is not a directory" % (what, d))
    if st.st_uid != os.geteuid():
        raise OSError("%s %s belongs to uid %d, not to us (uid %d)" % (what, d, st.st_uid, os.geteuid()))
    if st.st_mode & 0o077:                      # ours, but loose: an install from before the fix, a stray umask
        os.chmod(d, 0o700)                      # we own it, so tightening is a repair, not a guess
        if os.lstat(d).st_mode & 0o077:
            raise OSError("%s %s stays group/world-accessible" % (what, d))
    return d


def hosts_dir(state_dir) -> Path:
    """`<state>/hosts/`, made owner-only (0700), REFUSED when it is not ours, and kept so (owner_only_dir): the directory
    that holds every host's control socket, the temp name each socket is bound at (`_serve_socket`), and the per-session
    `hosts/<sid>/` directories. Both creators go through here (the kernel's write_spawn_spec in kernel/host_transport.py,
    whose mkdir of `hosts/<sid>/` with parents=True used to leave `hosts/` itself at the umask's mode, and the host's own
    constructor, before its journal opens a segment under `hosts/<sid>/` and before host.log or identity.json is written,
    then again in _prepare_socket on run()'s road, before its CLI is spawned), so the mode is set by code, not by the
    umask of the process that happened to create it (the review of this fix, 2026-09-19: the first cut named the judge
    precedent and took half of it, a stat through a symlink and a chmod never read back). Loud on every refusal: the
    host's constructor raises with nothing written, so the process exits 1 with the traceback on its captured stderr and
    no host.log row (round 3, kernel-2); the host's prelude logs socket-bind-failed (step hosts-dir) and exits with no CLI
    started and no lease written; and the kernel's spawn fails before it writes a spec. Pinned by tests/test_host_transport.py
    SpawnSpec.test_hosts_is_owner_only_by_code_and_a_loose_one_is_tightened and
    SpawnSpec.test_a_symlink_at_hosts_or_a_tighten_that_does_not_take_fails_the_spawn (the kernel's road, under a 000
    umask) and tests/test_session_host.py HostsDir, SocketMode.test_hosts_is_owner_only_once_the_host_binds and
    HostProcess.test_a_real_host_leaves_hosts_owner_only (the host's road, in-process and as a real process). The
    parents=True is for the state root, which every install has (kernel/judge.py makes it 0700 at import: a mkdir, then
    a chmod read back); nothing is made below `hosts/` until this has returned.
    THE ROOT'S MODE WHEN THIS CALL MAKES IT (kernel-7, round 5 of the review, 2026-09-19; fixed at round 6): pathlib's
    Path.mkdir applies `mode` to the leaf alone and makes each missing parent with its default 0777 masked by the process
    umask, so a state root that is not on disk when this runs is born at the umask's mode (0775 under 002, 0755 under 022,
    0700 under 077, 0777 under 000) while `hosts/` below it is 0700 in every case. The root matters: it is the parent of
    `hosts/` (owner-only by this code) and of the registry and the parked-ops files (owner-only since fork PR #789), and
    its traverse bit is what stands between a peer uid and any of them. THE FIX, the create road only: whether the root is
    on disk is read BEFORE the mkdir, and when it was not, the root this call made is tightened to 0700 by a chmod the
    line after `hosts/` is made, then READ BACK, and a read-back that is not 0700 is refused with the mode read and the
    one-step remedy. The read and the chmod (round 6, corrected at round 4 of the review, kernel-4, 2026-09-20): the root
    is read by lstat first, owner_only_dir's shape (a link or a non-directory at the path refused, a foreign uid refused),
    then OPENED with O_DIRECTORY|O_NOFOLLOW, read again by fstat on that descriptor (the same directory and uid refusals,
    decided on the object the chmod will act on), tightened by fchmod on the descriptor, and read back by fstat on it. So
    a link present at the lstat is refused there, and a link swapped in between the lstat and the open fails the open
    (ENOTDIR on Linux under O_DIRECTORY|O_NOFOLLOW, ELOOP elsewhere; both are refusals here) and is refused with the
    reason: no mode reaches anything a link points at. Through round 6 the chmod took the
    path, so a link swapped in after the lstat had whatever it pointed at (a directory or a file of ours) tightened to
    0700 before the read-back refused, and a foreign target raised EPERM at the chmod; the uid check never read the
    swapped target, since it had decided on the pre-swap root. A live symlink at the root's path, pointing at a
    directory, is a root on disk to this call: exists() follows it, `hosts/` is made under its target, and the target
    is never read back or tightened. Only
    the root is touched: the ancestors the parents mkdir made on the way (an XDG parent such as `~/.local/state`, which
    romp does not own) keep the umask's mode, and a root already on disk, at whatever mode, is left as it is (its mode is
    the creator's business, kernel/judge.py's for every install's root; this call never reads or repairs it). Between the
    parents mkdir and the fchmod the root holds `hosts/` alone, itself 0700 from its own mkdir, so nothing under the root
    is readable by a peer uid during that stretch. What the root itself grants in that stretch depends on the umask
    (extra5-1, round 4 of the review, 2026-09-20): under 000 (0777, every uid) and 002 (0775, the group; the umask the
    live host runs at) it carries the write bit for the peer class, which on a non-sticky directory is create, rename
    and unlink of any name in it, so the exposure is a SWAP of `hosts/` (a peer renaming `hosts/` out and putting a
    symlink in its place), which is the TOCTOU residual owner_only_dir's docstring states for a state root that is not
    0700; this stretch supplies that condition. Under 022 and 077 the peer class has no write bit there. The
    create-only scope does not protect against a world-writable non-sticky state root, because the parent governs
    creating and deleting entries: another user can rename or replace `hosts/` regardless of its 0700; the socket
    inside is safe, the directory holding it is not. What narrows that swap on the roads that write: the kernel's
    spawn road opens everything under `hosts/` through descriptors (kernel/host_transport.py open_host_dirs), and the
    host re-reads `hosts/` by lstat just before its bind (_serve_socket). Where the create
    road reaches: kernel/judge.py's import is the road every install's root takes, and it is a different creator; the kernel
    writes the spawn specification in a process that made that root at import, and the host's two calls here (its
    constructor and _prepare_socket) run over the specification's state_dir, so on the roads this code runs today the root
    is on disk before this call and the create road is a caller's over a root no romp tool has made (a test's fresh root, a
    host run by hand over one). tests/test_session_host.py StateRootByHostsDir pins the fix: the root reads 0700 under the
    runner's umask, 002, 022, 077 and 000 when this call made it, with `hosts/` 0700 and the ancestor made on the way at
    the umask's mode; a root pre-existing at 0755 or 0777 stays as planted with `hosts/` 0700 below it; a live symlink at
    the root's path takes the pre-existing road, one swapped in after the exists() read is refused at the lstat with its
    target's MODE untouched (an empty hosts/ of ours, 0700, is made through the link by the parents mkdir before the
    lstat refuses), and one swapped in between the lstat and the open is refused at the open with its target's mode
    unchanged; a root another uid owns is refused before any mode is set, whether the lstat or the descriptor's fstat
    reads the uid; the read-back is an fstat on the descriptor, so a stat or an lstat by path that disagrees is inert;
    and the refusal fires when the read-back disagrees."""
    root = Path(state_dir)
    made_root = not root.exists()               # the create road, decided before the mkdir: a root already on disk is left as it is
    d = owner_only_dir(root / "hosts", "hosts directory", parents=True)
    if made_root:
        st = os.lstat(root)                     # lstat, as owner_only_dir: a symlink swapped in would otherwise be tightened
        if not stat.S_ISDIR(st.st_mode):        # on behalf of its target
            raise OSError("state root %s is not a directory" % root)
        if st.st_uid != os.geteuid():
            raise OSError("state root %s belongs to uid %d, not to us (uid %d)" % (root, st.st_uid, os.geteuid()))
        # the chmod goes through a descriptor (kernel-4, round 4 of the review, 2026-09-20): opened O_DIRECTORY|O_NOFOLLOW
        # right after the lstat, so a link swapped in between fails the open (ENOTDIR on Linux, ELOOP elsewhere) and is
        # refused before any mode reaches what it points at, where a chmod by path tightened the link's target and refused only at the
        # read-back; the fstat repeats the directory and uid checks on the object the fchmod acts on, and the read-back
        # is an fstat on the same descriptor, never a stat by path
        try:
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as e:
            if e.errno == errno.ELOOP:
                raise OSError("state root %s is a symlink, not a directory (swapped in after it was made)" % root) from None
            if e.errno == errno.ENOTDIR:
                raise OSError("state root %s is not a directory (replaced after it was made)" % root) from None
            raise
        try:
            st = os.fstat(fd)
            if not stat.S_ISDIR(st.st_mode):
                raise OSError("state root %s is not a directory" % root)
            if st.st_uid != os.geteuid():
                raise OSError("state root %s belongs to uid %d, not to us (uid %d)" % (root, st.st_uid, os.geteuid()))
            os.fchmod(fd, 0o700)                # born at the umask's mode by the parents mkdir above; ours, so a repair
            mode = stat.S_IMODE(os.fstat(fd).st_mode)
        finally:
            os.close(fd)
        if mode != 0o700:                       # read back, never assumed
            raise OSError("state root %s reads mode %04o after its chmod to 0700: run chmod 700 on it, then start again" % (root, mode))
    return d


def sdk_importable() -> bool:
    import importlib.util
    return importlib.util.find_spec("claude_agent_sdk") is not None


def _cli_alive(transport) -> bool:
    """Whether the transport's CLI process is still running (None when unknown)."""
    proc = getattr(transport, "_process", None) or getattr(transport, "proc", None)
    rc = getattr(proc, "returncode", None) if proc is not None else None
    return proc is not None and rc is None


# ── the host ────────────────────────────────────────────────────────────────────────────────────
class SpecUnreadable(OSError):
    """The spawn spec could not be read: absent, or refused and quarantined by the guarded reader (its line is on
    stderr). main() answers it with one sentence and exit 2; every other OSError out of the constructor (the directory
    helpers' refusals below) raises out with its traceback, exit 1."""


class SessionHost:
    """One host process: see the module docstring. Constructed from the spec path; `run()` is the
    whole life."""

    def __init__(self, spec_path, lease_api=None, now=None):
        self.spec_path = Path(spec_path)
        # the spec lives at <root>/hosts/<sid>/spawn.json, so the root is three parents up (main() gates that root
        # before constructing the host)
        root = self.spec_path.parent.parent.parent
        # `hosts/` and `hosts/<sid>/` ours and 0700 FIRST, on the layout the path implies, through the two helpers the
        # kernel's write_spawn_spec makes them with (fork PR 814): a symlink, a non-directory or another uid's directory
        # at either raises out of the constructor with nothing read and nothing written (main() never runs a host over a
        # hosts/ that is not ours; the process exits 1 with the traceback on its captured stderr, hosts/<sid>/host.stderr,
        # and no host.log row exists for it, which the kernel's spawn-wait message says), and a LOOSE directory of ours is
        # tightened, the repair 814 owes every install from before 2026-09-19 whose hosts/ was made at the umask's mode.
        # Review round 3 of 814 (2026-09-19, kernel-2): through its round 2 the host's first check of hosts/ ran at the
        # socket road, after host.log, identity.json and a journal segment were written through a planted symlink and a
        # real CLI had spawned. The order matters against the guarded reader below (fork PR 874): the reader judges every
        # component from the root down by ownership, symlink and the discriminator and QUARANTINES what fails, so a
        # hosts/ left at 0777 by an old install would be quarantined whole (every session's socket and journal with it)
        # where 814's helper tightens it; the helpers run first and the reader then sees the shape they guarantee, and
        # what the helpers do not judge (the spec FILE: a symlink or a foreign-owned spawn.json planted while the root
        # was writable) the reader quarantines, and the host does not start (SpecUnreadable, exit 2). _prepare_socket
        # calls hosts_dir again on run()'s road, so a hosts/ re-pointed between here and the socket road is still refused
        # with a row (step hosts-dir).
        hosts_dir(root)
        owner_only_dir(self.spec_path.parent, "host directory")
        self._gr = _srm.Reader(lambda: root, who="session-host")
        try:
            with self._gr.open(self.spec_path) as f:
                self.spec = json.load(f)
        except OSError as e:
            raise SpecUnreadable(e.errno, e.strerror or str(e), str(self.spec_path)) from e
        self.sid = str(self.spec["sid"])
        self.name = str(self.spec.get("name") or self.sid[:8])
        self.state_dir = Path(self.spec["state_dir"])
        self._gr = _srm.Reader(lambda: self.state_dir, who="session-host")   # the spec's root from here on
        self.dir = self.spec_path.parent
        self.sock_path, self.sock_tmp = (self.state_dir / "hosts" / n for n in sock_names(self.sid))
        self.log_path = self.dir / "host.log"
        if self.state_dir != root:
            # a spec naming another root (a host run by hand over one; the kernel writes the spec under the root it
            # names): that root is gated first, exit 2 on refuse or unknown with the remedy on stderr and one host.log row,
            # before anything is made under it, then made ours the way the path's root was (814's hosts_dir: `hosts/`
            # 0700 under it, the socket's and the lease's directory)
            state_root_gate(self.state_dir, "start", log=self.log)
            hosts_dir(self.state_dir)
        self.journal = Journal(self.dir, root=self.state_dir)
        self.parked = Parked(float(self.spec.get("hook_self_answer_s") or HOOK_SELF_ANSWER_S))
        self.grace_s = float(self.spec.get("unattached_grace_s") or UNATTACHED_GRACE_DEFAULT_S)
        self.reader_behind_records = int(self.spec.get("reader_behind_records") or READER_BEHIND_RECORDS)
        self.version = str(self.spec.get("version") or "")
        self.now = now or time.time
        self.lease_api = lease_api or _lease_api()
        self.transport = None
        self.cli_pid = None
        self.cli_start = None
        self.cli_spawned_at = None      # the CLI's spawn time, set ONCE in _spawn: the lease and the hello carry it as the CLI's
        #                                 epoch (before 2026-09-14 the lease stamped the beat's time under the same name)
        self.fsid = str(self.spec.get("resume") or self.spec.get("session_id") or "")
        self.attached = None            # the attached kernel's writer, or None
        self.kernel = None
        self.inflight = 0               # user messages fed minus results seen (the idle judgement)
        self.idle_since = self.now()
        self.exit_info = None
        self.ending = None              # (deadline, cause) once `end` was requested
        self._replaying = False
        self._replay_end = 0
        self._live_backlog: list[tuple[int, dict]] = []
        self._server = None
        self._stop = None
        self._read_count = 0            # records read off the CLI (the writer task journals them in order)
        self._unwritten: dict = {}      # offset -> record read but not yet on disk (sent from memory on an attach)
        self._journal_gap_offsets: set = set()   # offsets whose record never reached the journal (a gap marker or nothing)
        self._journal_q: asyncio.Queue | None = None
        self._journal_faults = 0
        self._reader_behind_noted = False
        self._stdin_q: asyncio.Queue | None = None   # the kernel's `in` lines, written by their own task

    # ── host.log: never a spec field, never an environment value ──
    def log(self, kind: str, **fields) -> None:
        row = {"t": round(self.now(), 3), "kind": str(kind)}
        for k, v in fields.items():
            if v is None:
                continue
            row[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
        try:
            with _srm.open_private(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
        except Exception:
            pass

    @staticmethod
    def _where(e: BaseException) -> str:
        """The failing frame of an exception, never its text (it could carry a line of the CLI's output)."""
        tb = traceback.extract_tb(e.__traceback__)
        return "%s:%d:%s" % (os.path.basename(tb[-1].filename), tb[-1].lineno, tb[-1].name) if tb else "?"

    # ── lease ──
    def _write_lease(self) -> None:
        if self.cli_pid is None or self.cli_start is None:
            return
        lease = {"sid": self.sid, "fsid": self.fsid or self.sid, "name": self.name, "pid": int(self.cli_pid),
                 "start": self.cli_start, "holder": {"pid": os.getpid(), "start": self.lease_api["proc_start"](os.getpid()) or "",
                                                     "kind": "host"},
                 "version": self.version, "spawnedAt": self.cli_spawned_at, "t": self.now()}
        try:
            self.lease_api["write_lease"](self.state_dir, lease)
        except Exception as e:
            self.log("lease-write-failed", error=type(e).__name__)

    async def _beat(self) -> None:
        while self.exit_info is None:
            await asyncio.sleep(LEASE_HEARTBEAT_S)
            state_root_gate(self.state_dir, "beat", log=self.log)   # read before repair; a hostile root exits 2 here, every beat
            self._write_lease()

    def _cli_gone(self) -> bool:
        """Whether the CLI this host spawned is CONFIRMED gone: its pid no longer names a process with the start time
        recorded at the spawn (lease_api's proc_start, the identity the lease carries and the kernel's lease_state reads;
        a pid the kernel has since reused reads as gone too, by its different start). With no CLI identity recorded
        there was no CLI and no lease of ours (_write_lease writes none without it), and the two methods test that
        identity with the SAME predicate, `is None` on both fields: until review round 3 (2026-09-19) this one read
        `not self.cli_start`, which agreed with _write_lease's `is None` only because sdk_backend.proc_start never
        answers an empty string, an invariant stated at neither site; a start of "" now writes a lease AND reads as
        present here, so the lease-kept arm never removes a lease _write_lease wrote for a CLI whose identity still
        matches (pinned by tests/test_session_host.py SocketMode's no-identity case). Never the transport's word: see
        run()'s failure arm, the one caller (the review of the socket-mode fix, round 2, 2026-09-19)."""
        if self.cli_pid is None or self.cli_start is None:
            return True
        return self.lease_api["proc_start"](self.cli_pid) != self.cli_start

    # ── the CLI ──
    def _on_stderr(self, line: str) -> None:
        if self.attached is not None:
            self._send(self.attached, {"t": "stderr", "line": line})

    async def _spawn(self) -> None:
        if sdk_importable():
            # the private class, through the version check (SDK_TESTED_VERSION above): a mismatch raises out of
            # run() into the host-crashed record instead of an AttributeError with no version in it
            SubprocessCLITransport = sdk_internals(log=self.log)["SubprocessCLITransport"]

            async def _no_prompt():
                if False:
                    yield {}
            self.transport = SubprocessCLITransport(prompt=_no_prompt(), options=spec_to_options(self.spec, self._on_stderr))
            await self.transport.connect()
            proc = getattr(self.transport, "_process", None)    # the second private name the host reads, set by connect
            if proc is None:
                try:
                    await self.transport.close()
                except Exception:
                    pass
                # split as sdk_internals splits (tests-2, round 1 of the review, 2026-09-18): at the tested version the
                # install is broken and the remedy is a rebuild; at another version the name moved and the remedy is the
                # repin. Before the split the tested version was told it mismatched itself and offered a no-op repin.
                installed = installed_sdk_version()
                missing = SDK_INTERNALS[0][0] + ".SubprocessCLITransport._process"
                raise SdkInternalsMismatch(sdk_broken_install_text(installed, missing) if installed == SDK_TESTED_VERSION
                                           else sdk_mismatch_text(installed, missing))
            self.cli_pid = proc.pid
            self.log("cli-spawned", transport="sdk", cliPid=self.cli_pid)
        else:
            self.transport = PipeCliTransport(self.spec, self._on_stderr)
            await self.transport.connect()
            self.cli_pid = self.transport.pid
            self.log("cli-spawned", transport="pipe-fallback", cliPid=self.cli_pid)
        self.cli_start = self.lease_api["proc_start"](self.cli_pid)
        self.cli_spawned_at = int(self.now())
        self._write_lease()

    async def _read_cli(self) -> None:
        """The stdout reader: never pauses for the disk (the writer task journals), never dies on one
        record's handling (a fault is a host.log row, the reading goes on). The stream's end is the CLI's
        exit; nothing else is."""
        try:
            async for msg in self.transport.read_messages():
                off = self._read_count
                self._read_count = off + 1
                try:
                    self._unwritten[off] = msg
                    self._journal_q.put_nowait((off, msg))
                    self._track(msg, off)
                    if self._read_count - self.journal.next_offset > self.reader_behind_records and not self._reader_behind_noted:
                        self._reader_behind_noted = True
                        self.log("reader-behind", read=self._read_count, journaled=self.journal.next_offset)
                        if self.attached is not None:
                            self._send(self.attached, {"t": "fault", "kind": "reader-behind", "text": "the journal lags the CLI's output"})
                    if self.attached is not None:
                        if self._replaying and off >= self._replay_end:
                            self._live_backlog.append((off, msg))
                        elif not self._replaying:
                            self._send(self.attached, {"t": "out", "offset": off, "data": msg})
                except Exception as e:
                    self.log("record-handling-failed", offset=off, error=type(e).__name__, at=self._where(e))
        except Exception as e:
            self.log("cli-stream-ended", error=type(e).__name__, at=self._where(e))
        cause = self.ending[1] if self.ending is not None else "died"
        code = getattr(getattr(self.transport, "_process", None), "returncode", None)
        if code is None:
            code = getattr(self.transport, "returncode", None)
        await self._journal_q.put(None)           # the writer drains what it has, then stops
        self.exit_info = {"t": "exit", "code": code, "signal": None, "cause": cause}
        self.log("cli-exited", code=code, cause=cause)
        if self._stop is not None:
            self._stop.set()

    async def _journal_writer(self) -> None:
        """The one writer of the journal, off the reader's path. A write that raises (a full disk, a bad
        descriptor) is a `journal-write-failed` row and a fault frame, and the reading and the live
        forwarding go on: a journal fault is never the CLI's death. A record read but not yet written sits in
        `_unwritten` until it lands, so an attach can send it from memory instead of waiting for the disk."""
        delay = float(self.spec.get("_test_journal_delay_s") or 0)
        fault_at = self.spec.get("_test_journal_fault_at")
        gap_fault = bool(self.spec.get("_test_journal_gap_fault"))
        while True:
            item = await self._journal_q.get()
            if item is None:
                return
            off, msg = item
            if delay:
                await asyncio.sleep(delay)
            try:
                if fault_at is not None and int(fault_at) == off:
                    raise OSError(28, "test seam: the journal write fails at offset %d" % off)
                got = self.journal.append(msg)
                if got != off:
                    self.log("journal-offset-drift", expected=off, got=got)
            except Exception as e:
                self._journal_faults += 1
                self.log("journal-write-failed", offset=off, error=type(e).__name__, at=self._where(e))
                self._journal_gap_offsets.add(off)
                if self.attached is not None:
                    self._send(self.attached, {"t": "fault", "kind": "journal-write-failed", "text": type(e).__name__})
                # keep the numbering with a gap marker (readers skip it): the record is lost to replay, the live
                # kernel already has it; a marker that fails too becomes a zero-length index entry, so index and
                # offsets stay in lockstep and no later replay can trip over the hole
                try:
                    if gap_fault:
                        raise OSError(28, "test seam: the gap marker write fails too")
                    self.journal.append({"type": GAP_TYPE, "offset": off, "error": type(e).__name__})
                except Exception as e2:
                    self.log("journal-gap-unrecorded", offset=off, error=type(e2).__name__)
                    self.journal.note_gap(off)
            finally:
                self._unwritten.pop(off, None)

    def _track(self, msg: dict, off: int) -> None:
        """Bookkeeping per message: the fsid from the init, the turn count, open requests."""
        mt = msg.get("type")
        if mt == "system" and msg.get("subtype") == "init" and msg.get("session_id"):
            if str(msg["session_id"]) != self.fsid:
                self.fsid = str(msg["session_id"])
                self._write_lease()
        elif mt == "result":
            self.inflight = max(0, self.inflight - 1)
            if self.inflight == 0:
                self.idle_since = self.now()
        elif mt == "control_request":
            self.parked.park(msg, off, self.now(), attached=self.attached is not None)
            self.log("request-open", requestId=str(msg.get("request_id") or ""),
                     subtype=str((msg.get("request") or {}).get("subtype") or ""), attached=self.attached is not None)
        elif mt == "control_cancel_request":
            if self.parked.cancel(str(msg.get("request_id") or "")):
                self.log("request-cancelled", requestId=str(msg.get("request_id") or ""))

    async def _self_answer_loop(self) -> None:
        while self.exit_info is None:
            await asyncio.sleep(1.0)
            if self.attached is not None:
                continue
            for rid in self.parked.due_hooks(self.now()):
                entry = self.parked.open.get(rid) or {}
                event = entry.get("event") or ""
                frame = neutral_hook_response(rid, event)
                try:
                    await self.transport.write(json.dumps(frame) + "\n")
                except Exception as e:
                    self.log("self-answer-failed", requestId=rid, error=type(e).__name__)
                    continue
                since = entry.get("unattached_since") or self.now()
                self.parked.answer(rid)
                self.log("hook-self-answered", requestId=rid, event=event, callbackId=str(entry.get("callback_id") or ""),
                         toolUseId=str(entry.get("tool_use_id") or ""), parkedS=round(self.now() - float(since), 1))

    async def _grace_loop(self) -> None:
        while self.exit_info is None:
            await asyncio.sleep(1.0)
            now = self.now()
            if self.ending is not None:
                if now >= self.ending[0]:
                    self.ending = (float("inf"), "end-forced")
                    self.log("end-forced", cliPid=self.cli_pid)
                    try:
                        os.kill(int(self.cli_pid), signal.SIGKILL)
                    except (ProcessLookupError, TypeError):
                        pass
                continue
            if self.attached is None and self.inflight == 0 and now - self.idle_since >= self.grace_s:
                self.log("unattached-grace-expired", idleS=round(now - self.idle_since, 1))
                await self._end(END_GRACE_DEFAULT_S, "eof-grace")

    async def _end(self, grace: float, cause: str) -> None:
        """Graceful end: close the CLI's stdin (through the stdin pump, so every line queued before it is
        written first: an answer followed by a kill must reach the CLI) and let the CLI finish. A second end
        with a shorter grace pulls the deadline in; a longer one never pushes it out."""
        deadline = self.now() + float(grace)
        if self.ending is not None:
            if deadline < self.ending[0]:
                self.ending = (deadline, self.ending[1])
                self.log("end-grace-shortened", graceS=float(grace))
            return
        self.ending = (deadline, cause)
        self.log("end-requested", cause=cause, graceS=float(grace))
        self._stdin_q.put_nowait(END_SENTINEL)

    # ── the socket ──
    def _send(self, writer, frame: dict) -> None:
        try:
            writer.write(encode_frame(frame))
        except Exception:
            pass

    async def _flush(self, writer, timeout: float = EXIT_FLUSH_S) -> None:
        """Bounded drain of a writer: the tail of `out` frames and the exit frame must reach a slow kernel."""
        try:
            await asyncio.wait_for(writer.drain(), timeout=timeout)
        except Exception:
            pass

    async def _on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """One kernel connection. Frames are dispatched as they arrive; `in` lines go to the stdin pump
        (their own task), so a `signal` or an `end` behind a large `in` is acted on at once even when the
        CLI's stdin pipe is full."""
        fr = FrameReader()
        attached_here = False
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                for frame in fr.feed(chunk):
                    t = frame.get("t")
                    if t == "attach":
                        if self.attached is not None and self.attached is not writer:
                            self._send(writer, {"t": "busy", "kernel": self.kernel})
                            continue
                        attached_here = True
                        await self._attach(writer, frame)
                    elif t == "ping":
                        self._send(writer, {"t": "pong"})
                    elif not attached_here:
                        self._send(writer, {"t": "fault", "kind": "not-attached", "text": "attach first"})
                    elif t == "in":
                        self._queue_in(str(frame.get("data") or ""))
                    elif t == "ack":
                        try:
                            self.journal.ack(int(frame.get("offset")))
                        except (TypeError, ValueError):
                            pass
                    elif t == "signal":
                        sig = {"INT": signal.SIGINT, "KILL": signal.SIGKILL, "TERM": signal.SIGTERM}.get(str(frame.get("sig") or "").upper())
                        if sig is not None and self.cli_pid:
                            try:
                                os.kill(int(self.cli_pid), sig)
                                self.log("signalled", sig=str(frame.get("sig")))
                            except ProcessLookupError:
                                pass
                    elif t == "end":
                        g = frame.get("grace")
                        await self._end(float(g) if g is not None else END_GRACE_DEFAULT_S, "end")
                    elif t == "detach":
                        self.log("detached", kernelPid=(self.kernel or {}).get("pid"))
                        self._detach(writer)
                        attached_here = False
                        return
        except (ConnectionResetError, asyncio.IncompleteReadError, BrokenPipeError):
            pass
        except Exception as e:
            # a fault in the host's own handling of this kernel (never the CLI's): say so on the socket and in the
            # log, close this connection, keep the host and its CLI (the commit-5 review's finding b)
            self.log("client-loop-failed", error=type(e).__name__, at=self._where(e))
            self._send(writer, {"t": "fault", "kind": "host-fault", "text": "%s at %s" % (type(e).__name__, self._where(e))})
        finally:
            if attached_here and self.attached is writer:
                self.log("kernel-lost", kernelPid=(self.kernel or {}).get("pid"))
                self._detach(writer)
            try:
                writer.close()
            except Exception:
                pass

    def _detach(self, writer) -> None:
        if self.attached is writer:
            self.attached = None
            self.kernel = None
            self.parked.detached(self.now())
            self.idle_since = self.now() if self.inflight == 0 else self.idle_since

    async def _attach(self, writer, frame: dict) -> None:
        self.kernel = frame.get("kernel") if isinstance(frame.get("kernel"), dict) else {}
        try:
            ack = int(frame.get("ack", ACK_NONE))
        except (TypeError, ValueError):
            ack = ACK_NONE
        # Attached FIRST, so every record the reader takes from here on goes to the live backlog; the replay
        # covers the records read before this moment: from the journal as far as the writer has landed them,
        # from memory (`_unwritten`) for the rest. No settle wait, nothing dropped, no record twice (the
        # commit-5 review's finding c).
        self.attached = writer
        self._replaying = True
        self._live_backlog = []
        read_at_attach = self._read_count
        self._replay_end = read_at_attach
        self.parked.attached()
        self.log("attached", kernelPid=self.kernel.get("pid"), ack=ack, next=read_at_attach)
        self._send(writer, {"t": "hello", "protocol": PROTOCOL_VERSION,
                            "host": {"pid": os.getpid(), "start": self.lease_api["proc_start"](os.getpid()) or "", "version": self.version},
                            "cli": {"pid": self.cli_pid, "start": self.cli_start, "fsid": self.fsid,
                                    "spawnedAt": self.cli_spawned_at,                 # the CLI's epoch, the kernel's reg copies it
                                    "login": str(self.spec.get("login") or "")},       # the login identifier the launch billed
                            "journal": {"next": read_at_attach}, "parked": self.parked.ids(),
                            "inflight": self.inflight,      # the open turns, so an attaching kernel knows it is mid-turn
                            "exited": self.exit_info is not None})
        # each offset is resolved at ITS moment: from memory while unwritten, from the journal once landed, so
        # a record the writer lands during a drain yield is never between two snapshots (finding 4 of the
        # commit 6-7 review); a gap (a failed write) yields nothing and the parked table covers a request there
        if self.spec.get("_test_socket_small_buffers"):
            # a test seam: tiny send buffers, so the replay's drain below actually WAITS on a kernel that is not
            # reading yet and the writer lands records during that wait (the shape that lost records to a replay
            # built from two snapshots; the commit-8 review's item 9)
            sock = writer.transport.get_extra_info("socket")
            if sock is not None:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8192)
            writer.transport.set_write_buffer_limits(high=4096)
        n = 0
        for off in range(max(ack + 1, 0), read_at_attach):
            rec = self._unwritten.get(off)
            if rec is None:
                rec = next((r for _, r in self.journal.read_from(off, off + 1)), None)
            if rec is not None:
                self._send(writer, {"t": "out", "offset": off, "data": rec})
            n += 1
            if n % 200 == 0:
                await writer.drain()
        # every request still open is sent again FROM THE TABLE, whatever the acknowledged offset says and
        # whether or not its journal write landed: a kernel that received it and died never answered, and the
        # new kernel's Query must see it to answer it (findings 4 and e)
        for off, rec in self.parked.records():
            if off <= ack or off in self._journal_gap_offsets:
                self._send(writer, {"t": "out", "offset": off, "data": rec})
        for off, rec in self._live_backlog:
            self._send(writer, {"t": "out", "offset": off, "data": rec})
        self._live_backlog = []
        self._replaying = False
        if self.exit_info is not None:
            self._send(writer, self.exit_info)
        await writer.drain()

    def _queue_in(self, data: str) -> None:
        """One line from the kernel for the CLI's stdin: bookkeeping now, the write on the stdin pump. A user
        message opens a turn; a control_response for a request already answered is dropped."""
        try:
            obj = json.loads(data)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            if obj.get("type") == "user":
                self.inflight += 1
            elif obj.get("type") == "control_response":
                rid = str(((obj.get("response") or {}).get("request_id")) or "")
                if rid in self.parked.answered:
                    self.log("late-answer-dropped", requestId=rid)
                    return
                self.parked.answer(rid)
        self._stdin_q.put_nowait(data if data.endswith("\n") else data + "\n")

    async def _stdin_pump(self) -> None:
        """The one writer of the CLI's stdin: a full pipe blocks this task alone, never the socket reader. The
        end sentinel closes stdin in its turn, after every line queued ahead of it."""
        while True:
            data = await self._stdin_q.get()
            if data is None:
                return
            if data is END_SENTINEL:
                try:
                    await self.transport.end_input()
                except Exception as e:
                    self.log("end-input-failed", error=type(e).__name__)
                continue
            try:
                await self.transport.write(data)
            except Exception as e:
                self.log("write-failed", error=type(e).__name__)
                if self.attached is not None:
                    self._send(self.attached, {"t": "fault", "kind": "write-failed", "text": type(e).__name__})

    # ── life ──
    def _sweep_stale_temps(self) -> None:
        """Socket temps (sock_names) whose owner is gone, unlinked: a host killed between its bind and its rename leaves
        one (a bind that fails unlinks its own). A temp whose pid is alive is another host's, mid-bind, and is left alone,
        as is any name whose form this code did not mint; a signal-0 probe is the liveness test, and a pid the kernel has
        since reused keeps its dead owner's temp until that pid is gone too (one owner-only file in a 0700 directory, the
        leftover class a killed host's published socket already was). The first cut unlinked a fixed temp name here, which
        is what made the name shared (the review of this fix, 2026-09-19). The cost is PROPORTIONAL TO THE ENTRIES IN
        `hosts/`, not a constant: the glob reads the whole directory, and measured cold through the real launcher it took
        39 us at 0 entries, 76 us at 100, 380 us median at 800, and 2.5 ms at 200 stale temps (the review's round 3; the
        live root held 18 entries that day). That is why the sweep runs from _prepare_socket, BEFORE the CLI is spawned
        and the lease written, and not between the lease and the bind, where the code through round 2 ran it: the
        interval the kernel's lease-keyed attach roads race holds no directory read now. There is no per-launch cap on
        the sweep (the reviewer's ruling, 2026-09-19): the cost is stated as proportional and kept out of that interval."""
        for p in self.sock_path.parent.glob("*.tmp"):
            pid = temp_owner_pid(p.name)
            if pid is None or pid == os.getpid():
                continue
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                try:
                    p.unlink()
                except OSError:
                    pass
            except OSError:                          # a live process of another uid: not ours to judge
                pass

    def _socket_failed(self, step: str, e: OSError) -> None:
        """The one row both halves of the socket road write on a refusal (_prepare_socket's steps hosts-dir, budget and
        prelude; _serve_socket's bind-hosts, bind, chmod and rename): the step, the error class, its errno, the published path's byte
        length and the limit, and the failing frame. Never the error's text, which carries the path: host.log carries no
        spec field (the review of this fix, 2026-09-19)."""
        self.log("socket-bind-failed", step=step, error=type(e).__name__, errno=e.errno,
                 pathLen=len(os.fsencode(str(self.sock_path))), limit=SOCK_PATH_MAX, at=self._where(e))

    def _prepare_socket(self) -> None:
        """Everything the socket road needs that is not the bind itself, run from run() BEFORE the CLI is spawned and so
        before any lease exists (round 3 of this fix, the reviewer's ruling of 2026-09-19; through round 2 these steps ran
        inside _serve_socket, after _spawn had written the lease). In order: `hosts/` made ours and 0700 (hosts_dir: a
        symlink, a foreign owner or a tighten that does not take is refused, step hosts-dir), the published path's LENGTH
        checked in bytes against SOCK_PATH_MAX (step budget; the module comment there says why the check is ours and not
        the bind's), a dead host's published socket unlinked and stale temps swept (_sweep_stale_temps, step prelude).
        None of these reads the lease or needs the CLI's identity, and nothing in the kernel waits on the lease appearing
        before them (shown by execution in that round, not by reading), so they cost the lease-to-socket interval nothing
        once moved here: after _spawn's lease write only one lstat of hosts/ (the bind-hosts guard, round 4 of the
        review), the bind, the chmod by path and the rename run (_serve_socket).
        The trade is that the lease appears later in absolute terms by these steps' cost, which lengthens the interval
        from host-started to the lease, the one a kernel reading a foreign host's state mid-start falls into (a
        recovered orphan and a second host; queued as its own change). A refusal here is the socket-bind-failed row
        naming the step and an OSError out of run() with NOTHING started: no CLI, no lease, no transport to close; run()
        closes the journal and main() logs host-crashed, so the kernel's spawn wait reads an exit."""
        step = "hosts-dir"
        try:
            hosts_dir(self.state_dir)                   # `hosts/` 0700 and ours before anything is bound in it
            step = "budget"
            if len(os.fsencode(str(self.sock_path))) > SOCK_PATH_MAX:   # the published path is what the kernel connects to
                raise OSError(errno.ENAMETOOLONG, "AF_UNIX path too long")
            step = "prelude"
            try:
                self.sock_path.unlink()                 # a dead host's published socket
            except OSError:
                pass
            self._sweep_stale_temps()
        except OSError as e:
            self._socket_failed(step, e)
            raise

    async def _serve_socket(self) -> None:
        """Serve `hosts/<sid8>.sock` owner-only from the moment the path exists, or fail loudly and serve nothing: one
        lstat of `hosts/`, the bind, the chmod and the rename, and nothing else (round 3 moved every other step of the
        road to _prepare_socket, which run() calls before the CLI is spawned). THE LSTAT AT THE BIND (extra6-1, round 4 of
        the review, 2026-09-20): round 3's move put the CLI's whole start between the prelude's last look at `hosts/` and
        the bind (about 1.1 s on the production road against 0.4 ms through round 2, both by strace in round 4's
        review), so a `hosts/` re-pointed during the spawn was followed by the bind where round 2 refused it. The guard
        sits at the bind again: `hosts/`, the directory the temp is bound in and the published path's parent (one
        directory, one read), is lstat'd immediately before start_unix_server and refused as a symlink (ELOOP), not a
        directory (ENOTDIR), another uid's or group/world-accessible (EPERM), step `bind-hosts`, before anything is bound.
        It costs one lstat (about two microseconds, measured in that round) inside the lease-to-socket interval. What
        remains between this lstat and the bind is the bind's own window, a re-point landing in those microseconds is
        followed; and the guard narrows the band in which the HOST refuses, not the reach of a re-point after the
        publish, which needs a state root that is not 0700 and is stated at owner_only_dir. asyncio.start_unix_server binds and listens at the umask's mode, and
        until 2026-09-18 the chmod to 0600 came one line after the bind, so the published path stood at the umask's mode
        for the gap (PR 789's round 1, finding fresh-5: the last member of the create-then-tighten class that PR closed
        for the kernel's credential files; behind the owner-only state root, the one guard then, so a window, not a live
        hole). The bind takes a writer-unique temp name beside the published one (sock_names: the pid and random digits,
        the published name's length); the temp is tightened by PATH (fchmod on the listening descriptor is a no-op for a
        bound AF_UNIX socket on Linux, verified 2026-09-18: the descriptor is the socket, not the file); os.rename then
        moves it onto the published path, which is therefore born 0600. A connect through the new name reaches the same
        listening socket (AF_UNIX resolves a path to its inode), so the kernel keeps connecting to the one documented
        path (docs/reference.md) and no process-wide umask moves. During its brief life at the umask's mode (0775 under
        the 002 the live host runs at, measured 2026-09-19; 0755 under 022) the temp has ONE guard, the mode of the
        directory it is bound in: `hosts/` is owner-only BY CODE (hosts_dir, called from _prepare_socket and by the
        kernel's write_spawn_spec, 0700 whatever the umask, a symlink or a foreign owner refused, an existing loose one
        tightened and the tighten read back), so nothing outside the uid can reach the temp's name. The umask is not a
        guard and the first cut's claim that it was one was false for the umask we run: 002 leaves the group write bit,
        the permission an AF_UNIX connect needs (the review of this fix, 2026-09-19; pinned by tests/test_session_host.py
        SocketMode's umask cases, which stat the temp at its chmod). The published path never exists at a loose mode.
        This method runs AFTER _spawn has written the lease, so the four steps here are the whole of the lease-to-socket
        interval the kernel's lease-keyed attach roads race (measured cold through the real launcher in round 3; the
        prelude's directory read, proportional to the entries in `hosts/`, sat in that interval through round 2). Every
        failure here is loud and leaves nothing: the socket-bind-failed row naming the step (_socket_failed), the bound
        socket closed and its temp unlinked, then run()'s failure arm ends the CLI, drops the lease once that CLI is
        confirmed gone (kept, with a lease-kept row, while it is not: that arm says why) and main() logs host-crashed, so
        the kernel's spawn wait reads an exit, not a socket. Cleanup of the published path is unchanged: asyncio's
        Server.close never unlinks a path on 3.12, and 3.13's cleanup compares the bound path's inode and finds the temp
        gone, so run()'s own unlink stays the one."""
        step, server = "bind-hosts", None
        try:
            st = os.lstat(self.sock_path.parent)        # hosts/: the temp's directory and the published path's parent
            if stat.S_ISLNK(st.st_mode):
                raise OSError(errno.ELOOP, "hosts directory is a symlink at the bind")
            if not stat.S_ISDIR(st.st_mode):
                raise OSError(errno.ENOTDIR, "hosts directory is not a directory at the bind")
            if st.st_uid != os.geteuid():
                raise OSError(errno.EPERM, "hosts directory belongs to another uid at the bind")
            if st.st_mode & 0o077:
                raise OSError(errno.EPERM, "hosts directory is group/world-accessible at the bind")
            step = "bind"
            server = await asyncio.start_unix_server(self._on_client, path=str(self.sock_tmp))
            step = "chmod"
            os.chmod(self.sock_tmp, 0o600)
            step = "rename"
            os.rename(self.sock_tmp, self.sock_path)
        except OSError as e:
            if server is not None:
                server.close()
            try:
                self.sock_tmp.unlink()
            except OSError:
                pass
            self._socket_failed(step, e)
            raise
        self._server = server
        self.log("socket-ready", sock=self.sock_path.name, tmp=self.sock_tmp.name, pathLen=len(os.fsencode(str(self.sock_path))))

    async def run(self) -> int:
        """The whole life, in this order: the host-started row and identity.json; the socket road's prelude
        (_prepare_socket: the directory, the budget, a dead socket, stale temps, none of which needs the CLI or the
        lease); the CLI (_spawn, which writes the lease at its end); the socket (_serve_socket: an lstat of hosts/, bind,
        chmod, rename, the only steps after the lease); then the tasks until the CLI is gone. The directory work came before the CLI in
        round 3 of the socket-mode fix (the reviewer's ruling, 2026-09-19): through round 2 it ran after the lease and
        made up most of the lease-to-socket interval the kernel's lease-keyed attach roads race. Two failure arms, one
        per half of the road: a prelude refusal has started nothing (no CLI, no lease, no transport), so it closes the
        journal and raises; a refusal after the spawn ends the CLI and decides the lease by the CLI's confirmed exit."""
        self._stop = asyncio.Event()
        self._journal_q = asyncio.Queue()
        self._stdin_q = asyncio.Queue()
        self.log("host-started", hostPid=os.getpid())
        try:                                            # the identity hostAck is keyed by, for a reader with no hello
            _srm.write_text(self.dir / "identity.json", json.dumps({"pid": os.getpid(), "start": self.lease_api["proc_start"](os.getpid()) or ""}))
        except OSError:
            pass
        # the directory first, the CLI second, the socket third. A refusal of the prelude starts nothing: no CLI was
        # spawned, so there is no transport to close and no lease was ever written, none to remove or keep (the
        # lease-kept logic below is for the steps after the spawn); the row is written, the journal is closed, and
        # main() logs host-crashed, so the kernel's spawn wait reads an exit.
        try:
            self._prepare_socket()
        except OSError:
            self.journal.close()
            raise
        # the CLI before the socket: a kernel that finds the socket finds a CLI behind it (an attach before the spawn
        # would report no CLI pid and fail its first write)
        try:
            await self._spawn()
        except SdkInternalsMismatch:
            raise           # its text is the host's own and names the remedy: main's host-crashed record carries it whole
        except Exception as e:
            # the type name, plus the chained type names behind it when there are any (error_chain; fresh-1, round 2 of
            # the review, 2026-09-18): the SDK wraps a drifted call and a missing binary alike as a connection error,
            # and the chain records which was behind it for whoever reads the row. Never a message.
            chain = error_chain(e)
            self.log("cli-spawn-failed", error=type(e).__name__, **({"causes": chain} if chain else {}))
            self.exit_info = {"t": "exit", "code": None, "signal": None, "cause": "spawn-failed", "error": type(e).__name__}
            return 1
        try:
            await self._serve_socket()
        except OSError:
            # a host that could not publish its socket serves nothing: the CLI it spawned is ended with it, and the lease
            # goes ONLY once that CLI is confirmed gone. Reached from the bind, the chmod and the rename alone since round 3
            # (a prelude refusal exits above, before any CLI or lease exists). The kernel's spawn wait reads the exit (code
            # 1, main()'s host-crashed after the socket-bind-failed row); what its orphan road then does depends on the
            # lease (the review of this fix, 2026-09-19: at a published path over the budget the first cut logged
            # socket-ready and kept both the lease and the CLI, and nothing could ever connect; round 1 then removed the
            # lease as soon as transport.close() RETURNED, and a returning close is not proof the CLI is gone). The lease
            # is the one thing the kernel's orphan road waits on: with it removed and the CLI alive, the next connect finds
            # a lease-less leftover, waits for nothing, and starts a SECOND CLI on the same transcript. So the exit is
            # confirmed by pid and start-time identity (_cli_gone, the lease's own reader) and never by the transport: the
            # SDK transport has no returncode attribute at all, so this module's _cli_alive returns False, meaning gone,
            # for a live SDK CLI, in exactly the case that matters here. Unconfirmed, the lease stays and a lease-kept row
            # says so (the kind and the CLI's pid, nothing else): the kernel reads that lease as an orphan's and waits
            # for the CLI to finish, as it did before this fix, with no bound on that wait (the reviewer queued the bound
            # as a change of its own). That lease-kept row IS the operator's handle (kernel-5's clause, round 5 of the
            # review, 2026-09-19). Its fields, read by execution from the row this arm writes: t, kind ("lease-kept") and
            # cliPid, and tests/test_session_host.py SocketMode's kept-lease case pins the set as exactly those three. The
            # row names the pid to end, and ending that pid is the recovery: over the kept lease the kernel's connect
            # road waits and spawns nothing while the pid the lease names lives, and spawns once after it is gone
            # (KeptLease, on the real backend). So the one state on this road that needs a human to clear is visible,
            # with the pid, to the human who clears it. NOTHING ELSE CLEARS IT (kernel-5 as filed in round 3 of the
            # review; its Fix line applied in round 5's second addendum, 2026-09-19): the kept lease clears on the CLI's
            # exit alone, and the operator's recovery is to end the CLI pid this row names. Derived from the callers of
            # kernel/sdk_backend.py's remove_lease, the one function in the tree that unlinks a lease file: this arm's
            # call above, gated on _cli_gone; run()'s exit below, after the CLI is gone; the kernel's orphan road
            # (_host_orphan_recover), after its wait for the lease's pid and start to be gone; the boot census's orphan
            # reap and its dead-lease sweep (lease_census), which SPARE this shape while the CLI lives, since a host-held
            # lease whose holder is gone and whose CLI is alive is "host-gone-finishing", owned and not reaped, at its
            # two predicates `why == "holder-gone" and holder.kind == "host"`, so a kernel restart is not a backstop; and
            # _lease_close, the kernel-held lease's closer, which the connect loop's finally skips for a hosted session
            # and the shutdown drain reaches only for a session it reaps. Two roads a reader might take for backstops
            # are not: the shutdown drain (drain) reaps only a session whose thread is still alive at its bound and is
            # not detached (every session with a host or a host intent is latched detached), and this session's thread
            # ended on its launch error, so the drain reaps nothing for it and closes no lease; kill(sid) with a session
            # object calls shutdown(), which touches no lease, and with none ends a host through its lease only when
            # host_lease_state reads "attach", where this lease reads "orphan" (its holder is gone), so it returns having
            # done nothing. Once the CLI has exited, the next connect's orphan road or the next boot's dead-lease sweep
            # removes the lease. The residual predates this change: on the base a bind or chmod failure raised out of
            # run() with the lease as it was and the CLI running, with no removal at all, and the census's sparing
            # branch is older than this change too (it cites T315, the per-session hosts' arrival).
            try:
                await self.transport.close()
            except Exception:
                pass
            if self._cli_gone():
                try:
                    self.lease_api["remove_lease"](self.state_dir, self.sid)
                except Exception:
                    pass
            else:
                self.log("lease-kept", cliPid=self.cli_pid)
            self.journal.close()
            raise
        tasks = [asyncio.ensure_future(self._journal_writer()), asyncio.ensure_future(self._read_cli()),
                 asyncio.ensure_future(self._beat()), asyncio.ensure_future(self._self_answer_loop()),
                 asyncio.ensure_future(self._grace_loop()), asyncio.ensure_future(self._stdin_pump())]
        await self._stop.wait()
        # the CLI is gone: the writer drains, then an attached kernel gets the tail and the exit frame, drained
        try:
            await asyncio.wait_for(tasks[0], timeout=EXIT_FLUSH_S)
        except Exception:
            pass
        if self.attached is not None:
            self._send(self.attached, self.exit_info)
            await self._flush(self.attached)
        await self._stdin_q.put(None)
        for t in tasks:
            t.cancel()
        try:
            await self.transport.close()          # the pipes and the process object, before the loop closes
        except Exception:
            pass
        try:
            self.lease_api["remove_lease"](self.state_dir, self.sid)
        except Exception:
            pass
        self.journal.close()
        self._server.close()
        try:
            self.sock_path.unlink()
        except OSError:
            pass
        self.log("host-exited")
        return 0


def _lease_api() -> dict:
    """The stage 1 lease helpers from kernel/sdk_backend.py, loaded the kernel's way (a file-path load under
    a stable module name; the kernel's own copy when this runs inside the kernel)."""
    import importlib.util
    here = Path(__file__).resolve().parent
    sb = sys.modules.get("romp_sdk_backend")
    if sb is None:
        spec = importlib.util.spec_from_file_location("romp_loadsource", str(here / "loadsource.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        sb = mod.load_source("romp_sdk_backend_hostside", here / "sdk_backend.py")
    return {"write_lease": sb.write_lease, "remove_lease": sb.remove_lease, "proc_start": sb.proc_start}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        sys.stderr.write("usage: romp-session-host <spawn.json>\n")
        return 2
    # THE GATE FIRST, before anything under the root is read, the spec included: the spec lives at <root>/hosts/<sid>/spawn.json,
    # so the root and this host's log are known from its path alone
    spec_path = Path(argv[0])
    root, log_path = spec_path.parent.parent.parent, spec_path.parent / "host.log"

    def early_log(kind, **fields):
        row = {"t": round(time.time(), 3), "kind": str(kind)}
        row.update({k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in fields.items() if v is not None})
        try:
            # the shared module's creator, as SessionHost.log's: the one row this road writes (state-root-refused) is born
            # 0600 under any umask (round 4f's review); the path is argv-derived, seeded in the census as Path(argv[0])
            with _srm.open_private(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")
        except Exception:
            pass
    state_root_gate(root, "start", log=early_log)            # exit 2 on refuse or unknown, before the spec is read
    try:
        host = SessionHost(argv[0])                          # a spec naming another root: the constructor gates that root too, before the CLI
    except SpecUnreadable as e:
        # the spec could not be read: absent, or refused and quarantined by the guarded reader (its line is on stderr).
        # Any other OSError out of the constructor is a directory helper's refusal (hosts/ or hosts/<sid>/ a symlink, a
        # non-directory or another uid's; fork PR 814) and raises out with its traceback, exit 1: the shape the kernel's
        # spawn-wait message reads off host.stderr
        sys.stderr.write("romp-session-host: cannot read the spawn spec %s (%s); the host did NOT start (exit 2)\n"
                         % (argv[0], _srm.errno_text(e)))
        return 2
    try:
        return asyncio.run(host.run())
    except SdkInternalsMismatch as e:
        # whole, not the class, errno and frame the arm below logs: the text is the host's own (two version strings, a
        # module path, the repin command), and the kernel's launch error reads this row (host_transport.py,
        # host_exit_reason), so the card names the versions and the command instead of "see host.log"
        host.log("host-crashed", error=str(e))
        sys.stderr.write("romp-session-host: %s\n" % e)
        return 1
    except Exception as e:
        # the class, the errno and the failing frame, never the text: an OSError's text carries the path it failed on, a
        # spec field (the state root), and host.log carries no spec field (the review of this fix, 2026-09-19, which found
        # the bind-failure road writing the root's absolute path here through this row). The errno came back in round 3
        # (fresh-1: the base carried it and the redaction dropped it), guarded twice: the exception must be an OSError and
        # its errno an int, because a two-argument OSError(path, text) puts the PATH in .errno, and log() passes a str
        # through, so a typed guard alone would reopen the leak this row closed. A non-OSError's .errno, whatever it
        # holds, is never read.
        err_no = e.errno if isinstance(e, OSError) and isinstance(e.errno, int) else None
        host.log("host-crashed", error=type(e).__name__, errno=err_no, at=SessionHost._where(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
