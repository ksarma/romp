#!/usr/bin/env python3
"""The kernel's side of the per-session host (stage 4 of #1317, T315; kernel/session_host.py is the host,
the T315 design note is the design): a Transport the SDK client drives over the host's Unix socket, the
same class over an orphan journal file (one consumer path for live attach and for replay after a host
death), the spawn specification the kernel writes for a host, the settings (the session-hosts toggle, on by
default, and the host grace), and the host-lease classification the backend attaches by.

The SDK's `Transport` is documented as unstable; `HostTransport` implements its six methods (connect,
write, read_messages, close, is_ready, end_input) and a test pins the set against the abstract class.
When the SDK is not importable the class still exists, duck-typed, so the pure parts test without it.
"""
from __future__ import annotations
import asyncio
import collections
import json
import os
import re
import time
from pathlib import Path

try:  # the SDK's abstract base when present; a plain object otherwise (the six methods are the contract)
    # From the PUBLIC package (fresh-2, round 1 of the review, 2026-09-18): all three are public exports at the pinned
    # version (session_host.py, SDK_TESTED_VERSION), and until round 1 they were read from the private modules
    # _internal.transport and _errors inside a bare except Exception, the same silent stand-in for a moved private
    # name that the pin exists to make loud. Not added to SDK_INTERNALS on purpose: that check runs in the HOST
    # process at spawn time, after this module has already bound these names in the kernel process, so listing
    # them there would protect nothing here and only make hosts refuse sessions more broadly. The fallback below
    # is for a machine with no SDK at all (the hermetic tests, CI), hence ImportError, not Exception.
    from claude_agent_sdk import Transport as _Base, CLIConnectionError, ProcessError    # type: ignore
except ImportError:  # pragma: no cover - the SDK-less test venv
    class _Base:  # type: ignore
        pass

    class CLIConnectionError(Exception):  # type: ignore
        pass

    class ProcessError(Exception):  # type: ignore
        def __init__(self, message, exit_code=None, stderr=None):
            super().__init__(message)
            self.exit_code = exit_code
            self.stderr = stderr

import importlib.util
import sys
_HERE = Path(__file__).resolve().parent
_ls_spec = importlib.util.spec_from_file_location("romp_loadsource", str(_HERE / "loadsource.py"))
_ls_mod = importlib.util.module_from_spec(_ls_spec)
_ls_spec.loader.exec_module(_ls_mod)
load_source = _ls_mod.load_source
sh = sys.modules.get("romp_session_host") or load_source("romp_session_host", _HERE / "session_host.py")

# ── settings (bare value files under the state directory, like tmux-backend) ─────────────────────
SESSION_HOSTS_SETTING = "session-hosts"            # the toggle: "off" (or 0 / false / no) turns hosts off on this
                                                   # machine; "on", or no file at all, leaves them on (on by default
                                                   # since T348, the user 2026-09-11; off by default before)
SESSION_HOST_GRACE_SETTING = "session-host-grace"  # seconds an unattached idle CLI lives (default 900)
HOST_SCOPE_PREFIX = "romp-host-"
_HOST_SCOPE_RE = re.compile(r"romp-host-([0-9a-fA-F]{1,8})-(\d+)\.scope\Z")
ACK_BATCH = 64            # acknowledge at least every this many records…
ACK_INTERVAL_S = 0.1      # …or this often
SOCKET_WAIT_S = 20.0      # how long a spawn waits for the host's socket before it is a launch failure


def _setting(state_dir, name: str, default: str) -> str:
    try:
        v = (Path(state_dir) / name).read_text().strip()
    except OSError:
        return default
    return v or default


SESSION_HOSTS_ON_WORDS = ("on", "1", "true", "yes")


def session_hosts_read(state_dir) -> "tuple[bool, str]":
    """ONE read of the setting: (on, value). `value` is the file's stripped text, "" with no file. On unless the file
    says otherwise: a machine with no file is on; an empty file (or one holding only whitespace) is the default, on; a
    file saying off, 0, false or no is the toggle; any other word reads as off too. A caller that decides and then logs
    reads once through this, so the decision and the value it names agree (a flip between two reads cannot contradict)."""
    value = _setting(state_dir, SESSION_HOSTS_SETTING, "")
    return (True if not value else value.lower() in SESSION_HOSTS_ON_WORDS), value


def session_hosts_on(state_dir) -> bool:
    """Whether NEW sessions start through a host (session_hosts_read's verdict). Read at each connect, so a flip needs no
    restart: a plain-child session becomes hosted at its next respawn, a new one at once."""
    return session_hosts_read(state_dir)[0]


def session_host_grace_s(state_dir) -> float:
    try:
        v = float(_setting(state_dir, SESSION_HOST_GRACE_SETTING, str(sh.UNATTACHED_GRACE_DEFAULT_S)))
    except ValueError:
        return sh.UNATTACHED_GRACE_DEFAULT_S
    return v if v > 0 else sh.UNATTACHED_GRACE_DEFAULT_S


def host_dir(state_dir, sid: str) -> Path:
    return Path(state_dir) / "hosts" / str(sid)


def host_sock(state_dir, sid: str) -> Path:
    return Path(state_dir) / "hosts" / (str(sid)[:8] + ".sock")


def host_log_mark(state_dir, sid: str) -> int:
    """The size of hosts/<sid>/host.log in bytes, or 0 without one: the watermark the kernel takes right before it
    spawns a host, so every read of what THAT host wrote (host_exit_reason, the untested-version row the refused
    roads file) starts past everything already in the file. The closing check of the review (2026-09-18) replaced
    the previous bound, the last host-started row, with this one: a marker is the host's own claim to have run,
    and a host that died before writing anything (an OOM, a refused transient scope, a python that never got to
    main) left none, so a launch whose host wrote nothing read back to the previous host's marker and carried
    that host's reason and remedy onto the card and into the ledger. The kernel knows when it spawned; that fact
    cannot be absent, and this repo keys on the event rather than on a proxy for it. A byte offset rather than a
    line count so a line a dying host left unterminated stays with that host's run. Nothing truncates host.log
    between the mark and the read: the host appends, the kernel only reads.

    The mark's reach (extra6-1, round 3 of the review, 2026-09-19; corrected in round 4): the two REFUSED-road
    reads named above, and only those. The served road, sdk_backend._file_host_log_rows at the hello and at the
    exit, reads from a LINE position the registry keeps under the host's identity (hostLogPos) and starts at zero
    for an identity it has not seen, never from this mark. Over a host.log that survived a previous launch (a
    stale kernel-held lease keeps the directory) that has two consequences, both pinned as the head's behaviour
    in tests/test_session_host_sdk_pin.py: with no refused launch since, a fresh host that serves files the
    previous host's rows as its own problem rows; after a refused launch, the served road starts past the
    position that launch recorded, which is host.log's WHOLE line count at the refusal
    (sdk_backend._record_refused_launch_position), so a previous host's row that no road had filed (a
    reader-behind, an end-forced) is skipped by every road and VANISHES: no problem row, anywhere. Bounding the
    served road on this mark is the queued served-road change, where that behaviour is fixed, not this one."""
    try:
        return os.stat(host_dir(state_dir, sid) / "host.log").st_size
    except OSError:
        return 0


def host_log_rows(state_dir, sid: str, since: int = 0) -> list:
    """The parsed rows of hosts/<sid>/host.log from byte `since` on (a host_log_mark; 0 is the whole file), in
    order; [] for a missing or unreadable log. A line that is not a JSON object is skipped."""
    try:
        with open(host_dir(state_dir, sid) / "host.log", "rb") as f:
            f.seek(int(since or 0))
            data = f.read()
    except OSError:
        return []
    rows = []
    for ln in data.decode("utf-8", "replace").splitlines():
        try:
            row = json.loads(ln)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def host_exit_reason(state_dir, sid: str, since: int = 0) -> str:
    """What a host that exited before serving its socket said last: the `error` of its final `host-crashed` or
    `cli-spawn-failed` row, for the kernel's launch error; "" when no row says (an unreadable log, a host that
    died without one). `since` is the host_log_mark the kernel took before the spawn: the rows read are the ones
    this host wrote, and a previous host's rows in the same file are never this launch's reason (the closing check
    of the review, 2026-09-18; the round-2 bound at the last host-started row left the no-row case reading the
    previous run, see host_log_mark). Added 2026-09-18 so an SDK pin mismatch (session_host.py,
    SdkInternalsMismatch) reaches the card with both versions and the repin command instead of "see host.log"
    (the box admin's hazard review of the pull-in, 2026-09-16).

    What the text is (correctness-2 and kernel-3, round 1 of the review, 2026-09-18): a host-composed row (the SDK
    mismatch) is carried whole, and its text is the host's own prose (two version strings, a module path, the
    remedy). The generic host-crashed row is not prose the host authored: it is the last line of a Python
    traceback, capped at 200 characters by main(), so it can read "OSError: AF_UNIX path too long" and, in
    principle, whatever an exception message carries. It is carried anyway, because that line is what diagnoses
    a real failure (the path-too-long case was hit on 2026-09-18). The host writes no spec field and no
    environment value to host.log (its module docstring); that is the guarantee, not "prose".

    A cli-spawn-failed row is a bare exception type name, and it stays the first word. When this host also wrote
    an sdk-version-untested row (the SDK imports at a version other than the pin, and its internals resolved), the
    version fact follows as a second statement, in parentheses, for EVERY spawn failure alike, and the remedy is
    not here: it is in the host.sdk-untested problem row the kernel files from the same row on its own
    (sdk_backend.py, _file_sdk_untested_row), once per kernel life per version pair. So the card reads
    "TypeError (this host ran claude-agent-sdk 9.9.9, newer than the 0.2.156 the session host is written against)",
    a failure and a fact beside it, never a diagnosis. Two shapes came before this one (the closing check, ruling on
    fresh-1 of round 2, 2026-09-18): round 1 attached the sentence and "run bin/romp-sdk-setup" to every spawn
    failure after an untested row, so a missing binary was told to reinstall the SDK; round 2 gated it on an
    allowlist of type names (TypeError, AttributeError, ImportError, ModuleNotFoundError), which was wrong in both
    directions at 0.2.156, where _build_command, _find_cli and _check_claude_version run outside connect's try: a
    ValueError from option validation under an untested version reached the user with no version context, while a
    TypeError from a dependency's signature composed the remedy. A type name is not a diagnosis. The fact is
    recorded whenever it holds, the remedy rides with the fact, and no failure is attributed by its type. The
    untested row is the one gate left: the host writes it only when the SDK is importable and the version differs,
    so a machine with no SDK at all (the pipe transport's spawn failing the same arm) keeps the bare type name."""
    rows = host_log_rows(state_dir, sid, since)
    for i in range(len(rows) - 1, -1, -1):
        row = rows[i]
        if row.get("kind") not in ("host-crashed", "cli-spawn-failed") or not row.get("error"):
            continue
        error = str(row["error"])
        if row.get("kind") != "cli-spawn-failed":
            return error
        for prior in reversed(rows[:i]):
            if prior.get("kind") == "sdk-version-untested":
                relation = prior.get("relation")
                return ("%s (this host ran %s %s, %s the %s the session host is written against)"
                        % (error, sh.SDK_DIST, prior.get("installed"),
                           ("%s than" % relation) if relation in ("newer", "older") else "other than",
                           prior.get("tested")))
        return error
    return ""


def host_scope_unit(sid: str, t: int | None = None) -> str:
    """The host's own transient scope on Linux: `romp-host-<sid8>-<t>.scope` (the pid is not known before
    the spawn; the sweep keys on the sid's lease, not on a pid)."""
    return "%s%s-%d" % (HOST_SCOPE_PREFIX, str(sid)[:8], int(t if t is not None else time.time() * 1000))


def host_scope_units(list_lines: list[str], sids) -> dict[str, str]:
    """{unit: sid8} for the host scopes of OUR sessions in a `systemctl --user list-units` listing."""
    sid8 = {str(s)[:8].lower(): str(s) for s in sids if s}
    out = {}
    for ln in list_lines:
        head = ln.strip().split(None, 1)
        if not head:
            continue
        m = _HOST_SCOPE_RE.match(head[0])
        if m and m.group(1).lower() in sid8:
            out[head[0]] = m.group(1).lower()
    return out


# ── the spawn specification ────────────────────────────────────────────────────────────────────
def spawn_spec(opts, sid: str, name: str, state_dir, version: str, grace_s: float) -> dict:
    """The plain-data fields of a ClaudeAgentOptions the host rebuilds it from (sh.SPEC_FIELDS), plus the
    host's own keys. `permission_prompt_tool_name` is set to "stdio" when the kernel has a can_use_tool
    (the SDK client would set it from the callback; the host has no callback). Paths become strings."""
    spec = {}
    for k in sh.SPEC_FIELDS:
        v = getattr(opts, k, None)
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            spec[k] = v
        elif isinstance(v, os.PathLike):
            spec[k] = str(v)
        elif isinstance(v, (list, tuple)):
            spec[k] = [str(x) if isinstance(x, os.PathLike) else x for x in v]
        elif isinstance(v, dict):
            spec[k] = json.loads(json.dumps(v, default=str))
        else:
            spec[k] = str(v)
    if getattr(opts, "can_use_tool", None) and not spec.get("permission_prompt_tool_name"):
        spec["permission_prompt_tool_name"] = "stdio"
    spec.update({"sid": str(sid), "name": str(name), "version": str(version or ""), "state_dir": str(state_dir),
                 "protocol": sh.PROTOCOL_VERSION, "hook_timeout_s": sh.HOOK_TIMEOUT_S,
                 "hook_self_answer_s": sh.HOOK_SELF_ANSWER_S, "unattached_grace_s": float(grace_s)})
    return spec


def write_spawn_spec(state_dir, sid: str, spec: dict) -> Path:
    """`hosts/<sid>/spawn.json`, the directory at 0700 and the file at 0600: the spec carries the
    environment overlay."""
    d = host_dir(state_dir, sid)
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    p = d / "spawn.json"
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(spec, f)
    os.chmod(p, 0o600)
    return p


# ── host-lease classification ──────────────────────────────────────────────────────────────────
def host_lease_state(lease, now: float, start=None) -> str:
    """'attach' when a valid lease is held by a host (holder.kind == 'host'); 'orphan' when a host-held
    lease does not hold (its host or CLI is gone, or its beat is stale) and a journal may need replaying;
    'none' when there is no host lease at all (no lease, or one held by a kernel)."""
    if not isinstance(lease, dict):
        return "none"
    holder = lease.get("holder") if isinstance(lease.get("holder"), dict) else {}
    if holder.get("kind") != "host":
        return "none"
    sb = sys.modules.get("romp_sdk_backend") or load_source("romp_sdk_backend_leases", _HERE / "sdk_backend.py")
    return "attach" if sb.lease_state(lease, now, start) == "valid" else "orphan"


# ── the transport ──────────────────────────────────────────────────────────────────────────────
class HostTransport(_Base):
    """The SDK's Transport over the host's socket (live) or over an orphan journal (replay).

    Live: `connect()` opens the socket, sends `attach` with the acknowledged offset and waits for
    `hello` (a `busy` answer raises CLIConnectionError); `read_messages()` yields every `out` frame's
    record in order, replay then live, acknowledging batches back to the host and to `on_ack`; `write()`
    forwards a line as an `in` frame at once; `end_input()` sends `end` with this transport's grace,
    unless the transport is in DETACH mode, where the kernel is leaving and the host keeps the CLI;
    `close()` sends `detach` in detach mode, else `end` and a bounded wait for the exit frame. `stderr`,
    `fault` and `exit` frames go to their callbacks; an `exit` frame ends the read stream (a non-zero code
    raises ProcessError, as the subprocess transport does).

    Replay (`HostTransport.from_journal`): `read_messages()` yields the journal's records from the offset
    to the end and then ends; `write()` of a control_request synthesizes the success response the Query
    waits on (no CLI is there), every other write is dropped and counted; end_input and close are no-ops.
    The session's receive loop is the same either way, which is the point."""

    def __init__(self, sock_path=None, *, kernel=None, ack=sh.ACK_NONE, end_grace=sh.END_GRACE_DEFAULT_S,
                 on_ack=None, on_hello=None, on_stderr=None, on_exit=None, on_fault=None, journal_dir=None):
        self.sock_path = str(sock_path) if sock_path else None
        self.kernel = dict(kernel or {})
        self.ack_offset = int(ack)
        self.replay_end = None          # the journal's next offset at the attach (the hello's journal.next): records before
        #                                 it are the replay, records from it on are live (T354's spend fold)
        self.result_tags = collections.deque()   # one tag per RESULT record handed over, in order: {"offset", "replay"};
        #                                 the consumer reads the transport through a buffered stream a record ahead, so the
        #                                 transport's current offset is never the handled record's; the tag is
        self.end_grace = float(end_grace)
        self.on_ack, self.on_hello, self.on_stderr, self.on_exit, self.on_fault = on_ack, on_hello, on_stderr, on_exit, on_fault
        self.journal_dir = str(journal_dir) if journal_dir else None
        self.detach_mode = False
        self.hello = None
        self.exit_info = None
        self._reader = None
        self._writer = None
        self._ready = False
        self._closed = False
        self._synth: asyncio.Queue | None = None
        self.dropped_writes = 0
        self._last_ack_sent = self.ack_offset
        self._last_ack_t = 0.0
        self._early: list = []          # frames that arrived with hello, before the reader started
        self._fr = sh.FrameReader()
        self._init_answered = False
        self._my_requests: set = set()  # control_request ids this transport wrote (the Query's initialize first)
        self._hold: list = []           # replayed records held until the initialize's answer has been yielded
        self._init_pending = True       # live mode: the Query's initialize has not been answered yet

    @classmethod
    def from_journal(cls, journal_dir, ack=sh.ACK_NONE, **kw):
        return cls(None, ack=ack, journal_dir=journal_dir, **kw)

    # ── Transport ──
    async def connect(self) -> None:
        if self.journal_dir:
            self._synth = asyncio.Queue()
            self._ready = True
            return
        self._reader, self._writer = await asyncio.open_unix_connection(self.sock_path)
        self._writer.write(sh.encode_frame({"t": "attach", "kernel": self.kernel, "ack": self.ack_offset}))
        await self._writer.drain()
        fr = sh.FrameReader()
        hello = None
        while hello is None:
            chunk = await self._reader.read(65536)
            if not chunk:
                raise CLIConnectionError("the host closed the socket before hello")
            for f in fr.feed(chunk):
                if f.get("t") == "hello":
                    hello = f
                elif f.get("t") == "busy":
                    raise CLIConnectionError("another kernel is attached to this host: %r" % (f.get("kernel"),))
                else:
                    self._early.append(f)
        self.hello = hello
        try:
            self.replay_end = int(((hello or {}).get("journal") or {}).get("next"))
        except (TypeError, ValueError):
            self.replay_end = None
        self._fr = fr
        self._ready = True
        if self.on_hello:
            self.on_hello(hello)

    def is_ready(self) -> bool:
        return self._ready and not self._closed

    async def write(self, data: str) -> None:
        if self.journal_dir:
            await self._synth_write(data)
            return
        if not self._ready or self._closed:
            raise CLIConnectionError("host transport is not ready for writing")
        try:
            obj = json.loads(data)
            if isinstance(obj, dict) and obj.get("type") == "control_request" and obj.get("request_id"):
                self._my_requests.add(str(obj["request_id"]))
        except ValueError:
            pass
        self._writer.write(sh.encode_frame({"t": "in", "data": data.rstrip("\n")}))
        await self._writer.drain()

    async def end_input(self) -> None:
        if self.journal_dir or self._closed or not self._writer:
            return
        if self.detach_mode:
            return          # the kernel is leaving; the host keeps the CLI running
        await self._send({"t": "end", "grace": self.end_grace})

    async def end_and_close(self) -> None:
        """End the host's CLI and leave, from a transport that never ran a Query (the kernel's kill of a
        session with no object, T315): `end` with this transport's grace whatever the initialize gate says
        (close() alone reads an unanswered initialize as a connect that never completed and DETACHES, which
        keeps the CLI: the commit-15 review's first item), a bounded wait for the exit frame, then the socket."""
        if self.journal_dir or self._closed or not self._writer:
            return
        try:
            await self._send({"t": "end", "grace": self.end_grace})
            await self._wait_exit(self.end_grace + 5.0)
        except Exception:
            pass
        self._closed = True
        try:
            self._writer.close()
            await asyncio.wait_for(self._writer.wait_closed(), timeout=2.0)
        except Exception:
            pass

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.journal_dir:
            if self._synth is not None:
                await self._synth.put(None)
            return
        try:
            if self.detach_mode or self._init_pending:
                # a kernel leaving, or a connect that never completed (the initialize unanswered): the host
                # keeps its CLI either way — a failed attach must never END the turn it failed to join
                await self._flush_ack()
                await self._send({"t": "detach"})
            else:
                await self._send({"t": "end", "grace": self.end_grace})
                await self._wait_exit(self.end_grace + 5.0)
        except Exception:
            pass
        try:
            self._writer.close()
            await asyncio.wait_for(self._writer.wait_closed(), timeout=2.0)
        except Exception:
            pass

    def read_messages(self):
        return self._read_journal() if self.journal_dir else self._read_socket()

    # ── live ──
    async def _send(self, frame: dict) -> None:
        self._writer.write(sh.encode_frame(frame))
        await self._writer.drain()

    async def signal(self, sig: str) -> None:
        """An interrupt rung as a host request ('INT' or 'KILL')."""
        await self._send({"t": "signal", "sig": str(sig)})

    async def _flush_ack(self) -> None:
        if self.ack_offset > self._last_ack_sent and self._writer and not self._writer.is_closing():
            await self._send({"t": "ack", "offset": self.ack_offset})
            self._last_ack_sent = self.ack_offset
            self._last_ack_t = time.time()

    async def _wait_exit(self, timeout: float) -> None:
        deadline = time.time() + timeout
        while self.exit_info is None and time.time() < deadline:
            try:
                chunk = await asyncio.wait_for(self._reader.read(65536), timeout=max(0.05, deadline - time.time()))
            except (asyncio.TimeoutError, Exception):
                return
            if not chunk:
                return
            for f in self._fr.feed(chunk):
                self._dispatch_side(f)

    def _dispatch_side(self, f: dict):
        """A non-record frame; returns the record for an `out` frame, else None."""
        t = f.get("t")
        if t == "out":
            return f
        if t == "stderr" and self.on_stderr:
            self.on_stderr(str(f.get("line") or ""))
        elif t == "exit":
            self.exit_info = f
            if self.on_exit:
                self.on_exit(f)
        elif t == "fault" and self.on_fault:
            self.on_fault(f)
        return None

    def _advance(self, out: dict) -> None:
        """Acknowledge one record: acknowledged means RECEIVED by this process (not persisted); the offset moves
        as the record is handed over, and derived state is rebuilt from the transcript and the journal."""
        self.ack_offset = max(self.ack_offset, int(out.get("offset", self.ack_offset)))
        if self.on_ack:
            self.on_ack(self.ack_offset)

    def _take(self, out: dict):
        self._advance(out)
        self._tag(out.get("offset"), out["data"])
        return out["data"]

    def _tag(self, offset, data, replay=None) -> None:
        """A RESULT record's own offset, queued for the spend fold (T354): the consumer pops one per result it handles,
        in order, so it reads the record's position, never the transport's current offset (a buffered reader runs a
        record ahead). `replay` is decided against the hello's journal.next unless the caller knows (an orphan journal
        replays only)."""
        if not isinstance(data, dict) or data.get("type") != "result":
            return
        try:
            off = int(offset)
        except (TypeError, ValueError):
            off = None                                    # a frame with no offset (no host writes one; a protocol change)
        if replay is None:
            replay = off is not None and self.replay_end is not None and off < self.replay_end   # unknown position: live,
            #                                                                                       never a replay that folds nothing
        self.result_tags.append({"offset": off if off is not None else -1, "replay": bool(replay)})

    def _answers_mine(self, data) -> bool:
        if not isinstance(data, dict) or data.get("type") != "control_response":
            return False
        rid = str(((data.get("response") or {}).get("request_id")) or "")
        return rid in self._my_requests

    async def _read_socket(self):
        pending = list(self._early)
        self._early = []
        while True:
            for f in pending:
                out = self._dispatch_side(f)
                if out is not None:
                    # The Query's initialize must be answered AHEAD of a replay: the SDK client connects, starts
                    # its reader and awaits the initialize before anything consumes the message stream, whose
                    # buffer holds 100 records; a replay longer than that would block the reader with the
                    # initialize's answer still behind it (the commit 2-3 review's second finding). So every
                    # record is held until the first answer to a request this transport wrote has been handed
                    # over; then the held records follow, in order, and live delivery resumes.
                    if self._init_pending:
                        if self._answers_mine(out.get("data")):
                            # the answer is handed over first but acknowledged LAST: its offset sits past the
                            # whole held replay, and an ack that jumped there before the held records were
                            # handed over would lose them to every later kernel (the commit 6-7 review's third)
                            self._init_pending = False
                            yield out["data"]
                            held, self._hold = self._hold, []
                            for h in held:
                                yield self._take(h)
                            self._advance(out)
                        else:
                            self._hold.append(out)
                    else:
                        yield self._take(out)
                    if self.ack_offset - self._last_ack_sent >= ACK_BATCH or time.time() - self._last_ack_t >= ACK_INTERVAL_S:
                        await self._flush_ack()
                if self.exit_info is not None:
                    held, self._hold = self._hold, []       # the CLI is gone: whatever was held goes out first
                    for h in held:
                        yield self._take(h)
                    await self._flush_ack()
                    code = self.exit_info.get("code")
                    if code not in (0, None):
                        raise ProcessError("the CLI exited with code %s (%s)" % (code, self.exit_info.get("cause")),
                                           exit_code=code, stderr="see the host's log")
                    return
            pending = []
            try:
                chunk = await self._reader.read(65536)
            except (asyncio.CancelledError, GeneratorExit):
                raise
            except Exception:
                chunk = b""
            if not chunk:
                if self.detach_mode or self._closed:
                    return
                raise CLIConnectionError("the host's socket closed")
            pending = self._fr.feed(chunk)

    # ── replay ──
    async def _synth_write(self, data: str) -> None:
        try:
            obj = json.loads(data)
        except ValueError:
            obj = None
        if isinstance(obj, dict) and obj.get("type") == "control_request":
            req = obj.get("request") if isinstance(obj.get("request"), dict) else {}
            resp = {"commands": [], "hooks_applied": []} if req.get("subtype") == "initialize" else {}
            if req.get("subtype") == "initialize":
                self._init_answered = True
            await self._synth.put({"type": "control_response",
                                   "response": {"subtype": "success", "request_id": obj.get("request_id"), "response": resp}})
        else:
            self.dropped_writes += 1

    async def _read_journal(self):
        # the Query's initialize is answered first (it waits on it), then the journal, then the end
        while True:
            try:
                item = self._synth.get_nowait()
            except asyncio.QueueEmpty:
                break
            if item is None:
                return
            yield item
        for off, rec in sh.read_journal_dir(self.journal_dir, self.ack_offset + 1):
            self.ack_offset = off
            if self.on_ack:
                self.on_ack(off)
            self._tag(off, rec, replay=True)             # an orphan journal's records are all replays
            yield rec
            # answers the Query asked for meanwhile ride between records
            while not self._synth.empty():
                item = self._synth.get_nowait()
                if item is None:
                    return
                yield item
        # the Query writes its initialize right after start(); answer it before ending the stream (the SDK
        # treats the end as the CLI's exit), bounded so a client that never asks still ends
        deadline = time.time() + 5.0
        while not self._init_answered and time.time() < deadline:
            try:
                item = await asyncio.wait_for(self._synth.get(), timeout=max(0.05, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            if item is None:
                return
            yield item
        self.exit_info = {"t": "exit", "code": 0, "cause": "replay-end"}
