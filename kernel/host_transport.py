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
import errno
import fcntl
import json
import os
import re
import stat
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


class HostDirRefused(OSError):
    """A `hosts/` or `hosts/<sid>/` the kernel will not write under: a symlink, not a directory, another uid's, or
    group/world-accessible, found by write_spawn_spec's two directory guards (sh.hosts_dir, sh.owner_only_dir) or by
    open_host_dirs' descriptor checks; or, since round 5 of the review (kernel-2, 2026-09-20), a symlink standing at
    `spawn.json` or `host.stderr` under a verified `hosts/<sid>/`, refused by the file-level O_NOFOLLOW open
    (_open_file_nofollow), with `file` naming it: through round 4 those two opens raised a bare OSError (ELOOP), so a
    link planted at either name escaped this class, with no problem row, no remedy, and the launch error composed over a
    stale stderr tail. The text is the reason with the path; sdk_backend._host_transport_for files it as a problem row
    with the remedy (worded per shape, a directory's or a file's) and refuses the launch (round 4 of the review,
    2026-09-20). Built from ONE text argument, always, so `errno` is None on every instance. What write_spawn_spec's
    wrap of the two path-taking helpers files under this class (round 7 of the review, 2026-09-20, correcting round
    5's `errno is None` key, which threw every directory-shape refusal pathlib's mkdir raises before the helper's own
    lstat out of the class): a refusal the helper decided (a single-argument OSError: a symlink to a directory, a
    foreign uid, a directory that stays loose) and an errno of the SHAPE CLASS from either helper, EEXIST (a regular
    file, a FIFO, a dangling symlink or a symlink to a file standing at hosts/ or hosts/<sid>/, which mkdir(exist_ok=True)
    re-raises because the name is taken by something that is not a directory), ENOTDIR (a component that is not a
    directory: a state root that is itself a plain file, or hosts/ re-pointed to a file between the two helpers),
    ELOOP (a symlink loop) and ENOENT (hosts/ re-pointed to a dangling link between the two helpers, the reading the
    descent already gives ENOENT: "does not exist"); every other errno (ENOSPC, EROFS, EACCES, EPERM, EMFILE) is a
    filesystem failure and propagates as the OSError it is, with its errno, to the launch error. Since the fork PR that
    follows #814 (2026-09-21, the journal-reads change) the two write opens ask the readers' shape question before
    anything is opened (_open_host_file_for_write), so a directory, a FIFO or a socket OF OURS standing at spawn.json or
    host.stderr is refused under this class too, naming the file and its kind (`kind` set beside `file`) with nothing
    opened, where through #814 a FIFO at either name blocked the open inside the kernel's event loop until a reader
    appeared and a directory was EISDIR out of it."""

    file = None                                  # the file name when the refusal names an entry at a file's name under hosts/<sid>/
    kind = None                                  # the entry's kind ("directory", "FIFO", "socket") when a non-regular entry of ours is refused


class HostDirAbsent(HostDirRefused):
    """The descent met NO ENTRY at `hosts/` or at `<sid>` (the open's ENOENT), told from every other refusal because
    on the READ roads it is an answer and not a fault: no host directory means no host held the session (the connect
    road's leftover trigger and _host_lease_applies, the orphan road, the served road, since the round-7 second addendum
    of the review, 2026-09-20, which moved those reads onto descriptors). A subclass, so every site that catches
    HostDirRefused sees what it saw before (the spawn road's helpers make both directories before its descent, so an
    absence there stays the fault it is, filed with the directory remedy; the removal road logs it as not cleared);
    open_host_dirs_if_present turns this one refusal into None and lets every other propagate. Built from one text
    argument like its parent, so `errno` is None and the shape class stays an errno set on the helpers' side alone."""


class HostFileForeign(HostDirRefused):
    """An ENTRY under a verified `hosts/<sid>/` whose owner is not this process's euid, of ANY kind (a regular file, a
    symlink, a directory, a FIFO, a socket), found by the fstatat of the name under the directory's descriptor before
    anything is opened (_stat_name, which host_file_exists and read_host_file share) and, on the read, by the fstat of
    the descriptor the open returned: the round-7 fourth addendum of the review (2026-09-20, the reviewer's ruling of
    19:12Z), the owner question moved ahead of the open by the fifth (the same day; through the fourth a peer's UNIX
    socket at the name never reached read_host_file's fstat, since open(2) answers ENXIO for a socket before it returns
    a descriptor, and two of the three read roads swallowed that OSError with no row). The
    read descent verifies the two DIRECTORIES as this uid's and does not check their mode (open_host_dirs_if_present
    says why), so a `<sid>/` of ours left group- or world-writable admits an entry a peer planted at identity.json or
    host.log; through the third addendum such a file was read as ours. Now the reader checks the owner of the entry at
    the name and of the object it opened, never of a path (a path stat would reopen the re-point window the descent
    closes), and a foreign owner is an
    ANSWER on the read roads, the way an absent component is (HostDirAbsent): the road files one row naming the file,
    its directory and the owning uid (sdk_backend._refused_directory_row, the file remedy worded for the owner) and
    answers as it does for an absent file (None from read_host_file's caller, False from host_file_exists's). On the
    SPAWN road (the round-7 seventh addendum, 2026-09-20: host_log_mark before the spawn, _open_host_log on the refused
    arms, through the same _stat_name and the same post-open fstat) it is a refusal of the launch at the mark, filed the
    way every refusal of that road is and starting no process (sdk_backend._refuse_host_directory), and on a refused arm
    one row and the absent file's answers for the arm's three reads (sdk_backend._refused_launch_log: no reason, no
    untested row, no position). A
    subclass of HostDirRefused, so every catcher of the parent class sees what it saw before, and a road that catches
    the parent alone files the row and stops, the refusal's arm. `file` names the entry, `uid` its owner; the directory
    is in the text, as on every refusal of this class (and not on an attribute: tests/test_hosts_path_census.py reads a
    store of a hosts path onto an attribute named for a path as a store on a receiver it cannot type, and every read of
    that name in the three files went tainted with it at this addendum's first cut, 65 unlisted terminals and 143
    escapes). Built from one text argument like its siblings, so `errno` is None."""

    file = None
    uid = None


_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def _open_dir_nofollow(name, what: str, shown: Path, dir_fd=None, private: bool = True, loose=None, modes=None) -> int:
    """One component of the descent: `name` opened O_DIRECTORY|O_NOFOLLOW (relative to `dir_fd` when given), then
    fstat'd and refused unless it is a directory this uid owns and, with `private` (the spawn road's writes), one with no
    group or other bits, the shape the create road (sh.owner_only_dir) guarantees. Returns the descriptor. A symlink at
    the name fails the open itself, so no check ever runs on a link's behalf; `shown` is the path the refusal names.
    `private` is False on the removal road (remove_host_dir): a loose hosts/ of ours is hosts_dir's repair on the next
    launch, not a reason to leave a dead host's directory standing, and what the removal must not do is follow a link or
    touch another uid's directory. `loose`, a list, with `private` False (the read roads' descent, _descend): the mode
    is still READ, from the same fstat, and a directory with group or other bits is recorded on it as
    (`what`, `shown`, the mode) for the caller to file as a row and go on (the round-7 fourth addendum, 2026-09-20: the
    read roads report a loose directory of ours and neither refuse it, which would deny every session's first connect
    on an install whose hosts/ was made at the umask, nor repair it, which is the spawn road's helpers' job; the order
    here is read, record, proceed, and this function changes no mode on any road). `modes`, a list: EVERY component
    admitted is recorded on it the same way, loose or not (the round-7 fifth addendum, 2026-09-20: the caller files a
    loose row once per observed mode of the directory, whoever observes it, and a mode that changes between two
    observations is a transition it files, which takes the tight observations as well as the loose ones to tell apart;
    THE RULE is stated at sdk_backend._file_loose_directory_rows)."""
    try:
        fd = os.open(name, _DIR_FLAGS, dir_fd=dir_fd)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.ENOTDIR):
            # the refusal is the open's; the lstat after it only words the reason (Linux answers ENOTDIR, not ELOOP,
            # for a symlink under O_DIRECTORY|O_NOFOLLOW, the directory check running first in its open)
            try:
                is_link = stat.S_ISLNK(os.lstat(name, dir_fd=dir_fd).st_mode)
            except OSError:
                is_link = False
            raise HostDirRefused("%s %s %s" % (what, shown, "is a symlink, not a directory" if is_link else "is not a directory")) from None
        if e.errno == errno.ENOENT:
            raise HostDirAbsent("%s %s does not exist" % (what, shown)) from None
        raise
    try:
        st = os.fstat(fd)
        if not stat.S_ISDIR(st.st_mode):
            raise HostDirRefused("%s %s is not a directory" % (what, shown))
        if st.st_uid != os.geteuid():
            raise HostDirRefused("%s %s belongs to uid %d, not to us (uid %d)" % (what, shown, st.st_uid, os.geteuid()))
        if st.st_mode & 0o077:
            if private:
                raise HostDirRefused("%s %s is group/world-accessible (mode %04o)" % (what, shown, stat.S_IMODE(st.st_mode)))
            if loose is not None:
                loose.append((what, shown, stat.S_IMODE(st.st_mode)))
        if modes is not None:
            modes.append((what, shown, stat.S_IMODE(st.st_mode)))
    except BaseException:
        os.close(fd)
        raise
    return fd


class HostDirs:
    """Descriptors on `<state>/hosts/` (`hosts`) and `hosts/<sid>/` (`dir`), the kernel's handle on the two directories
    it writes under on a host's spawn road, opened by open_host_dirs and closed by close() or the `with` exit. Every
    WRITE and refused-road READ the kernel makes under them takes a NAME relative to one of these descriptors (dir_fd),
    so no component of the path can be re-pointed under it: a descriptor names an inode, not a path (round 4 of the
    review, 2026-09-20: through round 3 the launcher opened hosts/<sid>/host.stderr by path before Popen, and a
    hosts/ swapped for a symlink after the spec was written had that file, carrying the host's traceback with the
    absolute state root in it, written into the link's target). The spawn wait's poll of the published socket takes the
    NAME under `hosts` too (host_sock_present; the round-7 second addendum, 2026-09-20, which also moved the connect
    road's, the orphan road's and the served road's reads onto the descriptors of open_host_dirs_if_present). What
    still takes a PATH after the wait is the connect itself, HostTransport.connect's asyncio.open_unix_connection: a
    Unix socket is connected by a path in its address and no descriptor-relative form exists for it, so a hosts/
    re-pointed between the poll and the connect is connected through the link (a connect, no write). That site is
    named a PERMANENT residual at its line and in the PR's record (the round-7 fourth addendum, 2026-09-20: connect(2)
    has no dir_fd form, and the descriptor-relative spellings are a different mechanism), under the same precondition
    every residual here shares: a state root that is not 0700 while a session starts, and for the connect one a peer
    can WRITE, since the swap of hosts/ is a rename in the root. The journal reads were reachable under a weaker one
    through #814 (a group-writable hosts/, or a loose hosts/<sid>/ of ours, under a root the peer can traverse) and take
    the descent since the fork PR that follows it (journal_segments and read_journal_dir: the listing is a scandir off
    this `dir` descriptor, each file the owner question by name under it through the one reader; the design is stated
    at read_journal_dir). Stated precisely (the round-7 fifth addendum, 2026-09-20): under a root that is 0700
    before any peer held a descriptor inside it, neither is reachable; a peer who obtained a directory descriptor on a
    loose <sid>/ while the root was traversable keeps creating entries there until a spawn tightens that directory
    (the permission check of a create through a held descriptor is the directory's own mode, not an ancestor's, so
    tightening the root afterwards closes nothing the peer already holds). On this deployment the root reads
    0700 because kernel/judge.py chmods it at import, best-effort (the OSError swallowed, the mode read back once and
    reported on stderr when it is not 0700), and nothing re-checks or guards it afterwards (extra6-1, round 5 of the
    review, 2026-09-20: an attempt at startup, not a standing property of the box). `path` is `hosts/<sid>/` as the
    caller names it, for the wording of a refusal at a file under it (_open_file_nofollow). `loose` (the round-7 fourth
    addendum, 2026-09-20): on the read roads' descent, each component whose mode has group or other bits, as
    (what, path, mode) tuples read from the descent's own fstat, for the caller to file as a row before it reads on
    (sdk_backend._file_loose_directory_rows); empty on the spawn road, whose descent refuses such a directory. `modes`
    (the fifth addendum): every component admitted, loose or not, the same tuples, so that caller can tell a mode that
    changed between two descents of one connect episode from one it has already filed.
    THE DESIGN, in one sentence (the fifth addendum, the half of the reviewer's deferral condition that IS met): the
    owner check is available on a held descriptor at EVERY read site under hosts/<sid>/, as the fstat of the opened
    descriptor for a read (read_host_file) and as the fstatat of the name under this `dir` descriptor for an existence
    question or a question asked before an open (_stat_name, host_file_exists), so a sixth read site written tomorrow
    has the check at hand in both forms and needs no path stat; that availability, not any one reader, is why the
    read roads can answer the owner question without reopening the window the descent closes. The spawn road's
    host.log readers take this object and ask through the same two forms since the round-7 seventh addendum
    (2026-09-20; host_log_mark by the name, _open_host_log by the name and then the descriptor), where through the sixth
    they took the bare `dir` descriptor and asked nothing, the one class of kernel read under hosts/<sid>/ the design
    sentence above did not yet cover."""

    def __init__(self, hosts: int, dir: int, path=None, loose=(), modes=()):
        self.hosts, self.dir, self.path, self.loose, self.modes = hosts, dir, path, tuple(loose), tuple(modes)

    def close(self) -> None:
        for name in ("hosts", "dir"):
            fd = getattr(self, name)
            if fd is not None:
                setattr(self, name, None)
                try:
                    os.close(fd)
                except OSError:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def open_host_dirs(state_dir, sid: str) -> HostDirs:
    """The descent to `hosts/<sid>/`: `hosts/` opened O_DIRECTORY|O_NOFOLLOW off the state root and verified (a directory,
    this uid's, no group or other bits), then `<sid>` opened the same way relative to that descriptor and verified the
    same way. Follows no symlink at either component: a link at hosts/ or at hosts/<sid>/ fails its open (Linux answers
    ENOTDIR under O_DIRECTORY|O_NOFOLLOW, ELOOP elsewhere; _open_dir_nofollow handles both and an lstat after the refusal
    words it as a symlink) and is refused, a foreign or loose directory is refused by the fstat of the object opened, and nothing is refused
    or accepted on a path's say-so. Raises HostDirRefused with the reason and the path. The state root's own ancestors
    are the operator's (a symlinked ~/.local/state is followed as ever): the guard is against a re-point INSIDE the
    root, where hosts/ lives. The caller holds the descriptors for as long as its writes and reads under the directory
    run (sdk_backend._host_transport_for keeps them across the spawn wait, so its reads of host.stderr's size and
    host.log go to the directory the spec was written in, whatever hosts/ names by then; the host.log readers take this
    object and ask the owner question of the entry at the name since the round-7 seventh addendum, 2026-09-20) and
    closes them after."""
    return _descend(state_dir, sid, private=True)


def _descend(state_dir, sid: str, private: bool) -> HostDirs:
    """The two opens of the descent, shared by the spawn road (open_host_dirs, `private`: the mode is a condition) and
    the read roads (open_host_dirs_if_present, the mode is not): `hosts/` by path off the state root, then `<sid>` by
    name under it, each O_DIRECTORY|O_NOFOLLOW and fstat-verified by _open_dir_nofollow."""
    hosts_path = Path(state_dir) / "hosts"
    loose = []          # the read roads' record of a loose component (what, path, mode); the spawn road refuses one instead
    modes = []          # every component admitted, the same tuples (the loose rows' once-per-observed-mode latch reads it)
    hfd = _open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path, private=private, loose=loose, modes=modes)
    try:
        dfd = _open_dir_nofollow(str(sid), "host directory", hosts_path / str(sid), dir_fd=hfd, private=private, loose=loose, modes=modes)
    except BaseException:
        os.close(hfd)
        raise
    return HostDirs(hfd, dfd, hosts_path / str(sid), loose, modes)


def open_host_dirs_if_present(state_dir, sid: str):
    """The READ roads' descent (the round-7 second addendum of the review, 2026-09-20): the same two O_DIRECTORY|O_NOFOLLOW
    opens and fstat checks as open_host_dirs, and None instead of a refusal when `hosts/` or `<sid>` has no entry
    (HostDirAbsent), because on these roads an absent directory is the ordinary answer: no host held the session
    (_host_lease_applies and the leftover trigger of the connect road), nothing to replay (the orphan road), no log yet
    (the served road, at a hello before the host's first row). Every other refusal propagates as HostDirRefused with the
    reason and the path, for the caller to file as a problem row: a link at either component (the open's ENOTDIR under
    O_DIRECTORY|O_NOFOLLOW on Linux, ELOOP elsewhere; nothing behind the link is ever opened), a non-directory, or a
    directory another uid owns (the fstat of the object opened). Through round 7 those reads took a PATH (`(hdir /
    "identity.json").exists()`, `hdir.exists()`, `(hdir / "identity.json").read_text()`, `p.read_text()` for host.log,
    `sock.exists()` for the poll), so a hosts/ swapped for a symlink to a peer's directory was read through the link: the
    peer's identity.json vouched for a hostAck, the peer's host.log rows were filed as this session's problem rows, and a
    peer's leftover directory entered the orphan road. Now each of those reads takes a NAME relative to the descriptor
    this returns (host_file_exists, read_host_file, host_sock_present), and a swap is refused with a row.
    THE MODE IS NOT A CONDITION HERE (private=False, the removal road's position and its reason: what a read must not do
    is follow a link or read another uid's directory; a loose hosts/ of ours is hosts_dir's repair on the launch that
    follows), and for a reason of the read roads' own: they run BEFORE the spawn road's two helpers, which are where a
    loose hosts/ of ours is tightened, and hosts/ on every install from before 2026-09-19 reads 0775 under the live
    umask until the first spawn after that repair lands. A read descent that required 0700 would refuse every session's
    first connect on such an install at the leftover trigger, before the road that repairs the mode could run. So the
    spawn road's precondition is ported in its two parts that guard a READ (a directory at each component, this uid's,
    reached through no link) and not in the third (no group or other bits), which guards a write against a peer in the
    group creating names beside ours; a peer's entry at `<sid>` under a loose hosts/ of ours is still refused here by
    the uid check, and a link there by the O_NOFOLLOW open. The caller closes the descriptors (a `with`, or close()).
    WHAT THE MODE'S ABSENCE FROM THE CONDITION ADMITS, AND THE TWO ANSWERS (the round-7 fourth addendum, 2026-09-20,
    the reviewer's ruling of 19:12Z, replacing the third addendum's bare departure): a `<sid>/` of ours that is group- or
    world-writable admits an ENTRY a peer planted at identity.json or host.log, which the two readers below read as ours
    through the third addendum when it was a file. (1) The readers ask the OWNER QUESTION of the entry at the name
    before anything is opened (_stat_name: a fstatat of the name under the `<sid>` descriptor with no link followed,
    shared by host_file_exists and read_host_file since the fifth addendum, 2026-09-20), and read_host_file asks it
    again of the descriptor its O_NOFOLLOW|O_NONBLOCK open returned; an entry of ANY kind whose st_uid is not this euid
    raises HostFileForeign, which the read roads file as one row naming the file, the directory and the owning uid and
    then answer as they do for an absent file (None, False); a non-regular entry of ours (a directory, a FIFO, a
    socket) is answered None or False with nothing opened. The check is on the descriptor or the name under it, never
    on a path: a path stat would reopen the re-point window the descent closes. (The fourth addendum asked the owner
    question of the opened descriptor only, and a peer's socket at the name never reached it: open(2) answers ENXIO for
    a socket before it returns a descriptor, and the orphan and served roads swallowed the OSError with no row.)
    (2) The mode is READ, from the fstat the descent already makes, and a loose component is recorded on
    the returned HostDirs (`loose`: what, path, mode; `modes`: every component) for the caller to FILE
    (sdk_backend._file_loose_directory_rows, kind host.directory-loose, the mode in octal, the remedy naming the spawn
    road's repair) once per observed mode of the directory, whoever observes it, so a stable loose directory is one row
    however many descents, sessions or roads observe it and a mode that changes between two observations is a row naming
    the new mode (THE RULE at sdk_backend._file_loose_directory_rows, the reviewer's ruling of 2026-09-21 07:19Z; the
    fifth addendum filed once per connect episode, the fourth once per descent), and then proceed. The read
    roads neither refuse on the mode (the denial of service above) nor repair
    it: a read road stays a read road, the chmod belongs to the spawn road's helpers (sh.hosts_dir, sh.owner_only_dir),
    and the order here is read, record, proceed, never repair-before-reading. Pinned in tests/test_host_transport.py
    (ReadDescent, BackendHostRules): the mode is unchanged after every read road, by stat before and after; the answer
    for every kind of entry a peer can put at the name, on each read road and from each reader, cell by cell from one
    table (SHAPE_TABLE there)."""
    try:
        return _descend(state_dir, sid, private=False)
    except HostDirAbsent:
        return None


def _stat_name(name: str, dirs: HostDirs):
    """THE OWNER QUESTION, asked of the entry at `hosts/<sid>/<name>` before anything is opened: a stat by NAME relative
    to the verified `<sid>` descriptor with no symlink followed (fstatat with AT_SYMLINK_NOFOLLOW), so nothing outside
    the directory is consulted, no path is, and what it reports is the entry itself, whatever its kind. Shared by
    host_file_exists and read_host_file since the round-7 fifth addendum of the review (2026-09-20). The answers: no
    entry at the name (ENOENT), None; an entry ANOTHER UID owns, of ANY kind (a regular file, a symlink, a directory, a
    FIFO, a socket), HostFileForeign naming the entry, the directory and the uid; a SYMLINK of ours, the file-shape
    HostDirRefused (`file` set, the wording _open_file_nofollow gives a link at spawn.json or host.stderr); anything
    else of ours, the stat result, for the caller to read the kind from (S_ISREG decides whether it is the file); the
    spawn road's host.log readers ask it too since the seventh addendum (host_log_mark reads the size off the answer,
    _open_host_log asks through _open_host_file). Any
    other OSError of the stat (EACCES on a `<sid>/` of ours with no search bit, EIO) propagates as itself: a fault of
    the directory, not a shape at the name (what each read road does with it: host_file_exists's docstring, the round-7
    sixth addendum). Why the question is asked here and not of an opened descriptor alone:
    through the fourth addendum read_host_file's owner check was the fstat of the descriptor its open returned, and a
    UNIX socket a peer planted at the name never reached it, because open(2) answers ENXIO for a socket before any
    descriptor exists; the orphan and served roads catch OSError around their read, so the peer's socket at
    identity.json or host.log was answered absent with no owner row on those two roads while the lease-applies road
    (host_file_exists, already a stat by name) filed one for the same plant (the fourth addendum's two verifiers)."""
    try:
        st = os.stat(name, dir_fd=dirs.dir, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if st.st_uid != os.geteuid():
        raise _foreign(name, dirs, st.st_uid)
    if stat.S_ISLNK(st.st_mode):
        e = HostDirRefused("%s in host directory %s is a symlink, not a regular file" % (name, dirs.path))
        e.file = name
        raise e
    return st


def host_file_exists(name: str, dirs: HostDirs) -> bool:
    """Whether a regular file OF OURS stands at `hosts/<sid>/<name>`: the owner question (_stat_name) and then S_ISREG of
    what it returned. The connect road's read of identity.json's existence (_host_lease_applies; the round-7 second
    addendum). The answers, by the kind of entry, from the one table tests/test_host_transport.py pins cell by cell
    (SHAPE_TABLE, the same table read_host_file answers): no entry, False; a regular file of ours, True; an entry
    another uid owns, of any kind, HostFileForeign (the road files one row and answers as for an absent file); a
    symlink of ours, the file-shape HostDirRefused (`file` set; through the third addendum a link answered False here
    with no row); a directory, a FIFO or a socket of ours, False, nothing opened (an existence question reads no byte,
    takes no descriptor and cannot block on a FIFO). A device node is outside the table: making one needs a privilege no
    peer here has, and it would take the non-regular arm like a FIFO. Both readers resolve the name under the held
    `<sid>` descriptor and never through a path, which is what keeps the re-point window the descent closed closed.
    A FAULT OF THE DIRECTORY IS NOT A SHAPE AND IS NOT ANSWERED HERE (the round-7 sixth addendum, 2026-09-20, disclosing a
    cell the fifth changed without saying so): a `<sid>/` of ours with no search bit (0600: the descent's
    O_RDONLY|O_DIRECTORY open needs the read bit, which it has; the fstatat of a name under it needs the search bit, which
    it lacks) raises the stat's PermissionError, errno EACCES, out of this reader, and the lease-applies road, which has
    no OSError arm, raises it on to the connect loop, whose handler records it as the session's launch error and ends the
    connect (SdkSession._amain's except; the kernel log carries the traceback). That is the answer this PR's base gave:
    there the existence read was Path.exists() by path, and pathlib re-raises every errno but ENOENT, ENOTDIR, EBADF and
    ELOOP, so the same directory raised the same PermissionError out of _host_lease_applies. The second through fourth
    addenda answered False here through an `except OSError` arm around the stat, a silent answer to a fault where the
    repo's rule is to surface one, and said nothing of it; the fifth addendum's _stat_name dropped the arm and said
    nothing either. No romp code path makes such a directory (the helpers make 0700). The orphan and served roads answer
    the same fault through the OSError arms they have had since the base (read_host_file's docstring). Pinned in
    tests/test_host_transport.py (ReadDescent: the fault from both readers with nothing opened; BackendHostRules: out of
    the lease-applies road, and what the other two roads' arms do with it)."""
    st = _stat_name(name, dirs)
    return st is not None and stat.S_ISREG(st.st_mode)


def _foreign(name: str, dirs: HostDirs, uid: int) -> HostFileForeign:
    e = HostFileForeign("%s in host directory %s belongs to uid %d, not to us (uid %d)" % (name, dirs.path, uid, os.geteuid()))
    e.file, e.uid = name, uid
    return e


def _open_host_file(name: str, dirs: HostDirs):
    """`hosts/<sid>/<name>` opened for reading through the descent: a binary file object at the file's start, or None when
    no regular file of ours stands at the name. THE ONE READER every kernel read of a file under `hosts/<sid>/` goes
    through (the round-7 seventh addendum of the review, 2026-09-20): read_host_file for the orphan road's identity.json
    and the served road's host.log (the second addendum), and _open_host_log for the spawn road's host.log (host_log_rows
    and host_exit_reason on its refused arms, sdk_backend._record_refused_launch_position beside them), which through the
    sixth addendum opened the name under the held descriptor with no owner question asked, so the PR record's lead
    sentence, that every kernel read of identity.json and host.log under hosts/ asks the owner question before opening,
    was false for those readers. Two checks and the open between them (the round-7 fifth addendum, 2026-09-20,
    correcting the fourth).
    FIRST THE OWNER QUESTION, BEFORE ANY OPEN (_stat_name, a stat by NAME under the verified `<sid>` descriptor with no
    link followed): an entry another uid owns, of any kind, raises HostFileForeign; a symlink of ours raises the
    file-shape refusal; no entry, or a directory, a FIFO or a socket of ours, is None here with NOTHING OPENED. That
    is the table host_file_exists answers, and it is why a socket at the name no longer depends on the open failing:
    through the fourth addendum the owner check was the fstat of the descriptor the open returned, and open(2) answers
    ENXIO for a UNIX socket before it returns one, so a peer's socket at identity.json or host.log raised a bare OSError
    the orphan and served roads swallowed with no owner row, while the lease-applies road filed one for the same plant;
    a FIFO of ours, opened O_NONBLOCK so as not to block, was answered by that fstat; now neither is opened at all (and
    a FIFO at host.log, which the spawn road's opener took with neither the stat nor O_NONBLOCK through the sixth
    addendum, blocked that open until a writer appeared).
    THEN THE OPEN, by NAME under the same descriptor with O_NOFOLLOW|O_NONBLOCK (_open_file_nofollow), AND THE FSTAT OF
    THE DESCRIPTOR IT RETURNED, which asks the owner question again of the object actually held and reads its kind: the
    authoritative check, since the entry can change between the stat and the open, deciding the same way (another
    uid's, HostFileForeign, closed unread; not a regular file, None). What the open itself can answer after the stat
    said a regular file of ours, each mapped to the same table: ENOENT, the entry is gone, None; ELOOP, a link stands
    there now, the file-shape refusal _open_file_nofollow raises; ENXIO, a socket stands there now, the owner question
    asked once more by name (a peer's socket is its row) and then None, the socket's answer; every other errno (EACCES
    on a file of ours with no read bit, EMFILE, EIO) propagates as the fault it is, because the class is for the shapes
    an entry can take and not for every failure of the open, and the OSError arms of this reader's callers, the orphan
    road (raw None), the served road (return), and on the spawn road host_log_rows ([]) and
    _record_refused_launch_position (return), arms from before this PR, are where a fault is answered, each re-raising
    the refusal class ahead of its arm, since HostDirRefused is an OSError and a refusal answered as absent would be a
    silent read; the lease-applies road, host_file_exists's caller, has no such arm, and a fault of the directory
    propagates out of it to the connect loop (host_file_exists's docstring; the round-7 sixth addendum, 2026-09-20).
    Every check is on the held descriptor or on the name under it, never on a path (a path stat would reopen the
    re-point window the descent closes); the census (tests/test_hosts_path_census.py, CONVERTED) holds both stats
    by-descriptor. The caller closes the file (a `with`)."""
    st = _stat_name(name, dirs)
    if st is None or not stat.S_ISREG(st.st_mode):
        return None
    try:
        fd = _open_file_nofollow(name, os.O_RDONLY | os.O_NONBLOCK, dirs)
    except FileNotFoundError:
        return None
    except OSError as e:
        if e.errno == errno.ENXIO:
            _stat_name(name, dirs)
            return None
        raise
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid():
            raise _foreign(name, dirs, st.st_uid)
    except BaseException:
        os.close(fd)
        raise
    if not stat.S_ISREG(st.st_mode):
        os.close(fd)
        return None
    return os.fdopen(fd, "rb")


def read_host_file(name: str, dirs: HostDirs):
    """The bytes of `hosts/<sid>/<name>` read whole through the descent (_open_host_file, above: the owner question of the
    entry at the name, the O_NOFOLLOW|O_NONBLOCK open by name under the held `<sid>` descriptor, the fstat of the
    descriptor it returned), or None when no regular file of ours stands at the name. The read roads' one file read (the
    round-7 second addendum of the review, 2026-09-20): identity.json on the orphan road, host.log on the served road.
    The answers, kind by kind and owner by owner, are the table tests/test_host_transport.py pins cell by cell
    (SHAPE_TABLE), the same table host_file_exists answers for an existence question and the spawn road's host.log
    readers answer since the seventh addendum (host_log_mark, host_log_rows, host_exit_reason)."""
    f = _open_host_file(name, dirs)
    if f is None:
        return None
    with f:
        return f.read()


_SEGMENT_RE = re.compile(r"\Ajournal-([0-9]+)\.jsonl\Z")      # sh.Journal's segment names: journal-<firstoffset>.jsonl


def journal_segments(dirs: HostDirs, refused=None) -> list:
    """The orphan journal's segments OF OURS under the verified `hosts/<sid>/`, as (first offset, name) in first-offset
    order, listed OFF THE HELD DESCRIPTOR: os.scandir(dirs.dir) reads the directory the descent verified and nothing a
    path names by then; each entry whose NAME has a segment's shape (_SEGMENT_RE) is put the owner question by name
    under the same descriptor (_stat_name) and decided from the readers' table: a regular file of ours is a segment;
    no entry (gone since the listing), or a directory, a FIFO or a socket of ours, is not one, skipped with nothing
    opened; an entry ANOTHER UID owns, of any kind, is HostFileForeign, handed to `refused` for its row and skipped, so
    the road proceeds as with no such segment (the answer a foreign identity.json gets on the same roads); a SYMLINK of
    ours is the file-shape refusal, raised, so the road that asked is refused as it is by a link at identity.json (the
    lease-applies road answers False after the row; the orphan road replays nothing). With `refused` None a foreign
    entry raises too: a caller with no row to file gets the refusal, never a silent skip. THE CLOSE DISCIPLINE of the
    listing: os.scandir on a descriptor duplicates it for fdopendir and rewinds the duplicate before closedir, so the
    held descriptor stays open and a second listing on it starts at the directory's beginning; the `with` closes the
    iterator whatever the body raises. The census (tests/test_hosts_path_census.py) holds the scandir and the stat
    by-descriptor. The lease-applies road's journal question (sdk_backend._host_lease_applies) is this list's truth;
    read_journal_dir below reads the segments it names, and THE DESIGN of both is stated there."""
    names = []
    with os.scandir(dirs.dir) as it:
        for entry in it:
            names.append(entry.name)
    out = []
    for name in sorted(names):
        m = _SEGMENT_RE.match(name)
        if m is None:
            continue
        try:
            st = _stat_name(name, dirs)
        except HostFileForeign as e:
            if refused is None:
                raise
            refused(e)
            continue
        if st is None or not stat.S_ISREG(st.st_mode):
            continue
        out.append((int(m.group(1)), name))
    out.sort()
    return out


def read_journal_dir(dirs: HostDirs, offset: int = 0, refused=None):
    """Read an ORPHAN journal (its host is gone) under the verified `hosts/<sid>/` from `offset` to the end without an
    index, through the descent's descriptor: segments in first-offset order (journal_segments), each record numbered
    from its segment's first offset, so acknowledged-and-deleted early segments cost nothing but the records they held;
    a gap marker's record is skipped and the offsets gaps.json names are skipped in the numbering. Yields
    (offset, record).

    THE DESIGN (the fork PR that follows #814, 2026-09-21, building the item "the journal reads descend by descriptor"
    of the general notes' small-asks file, filed by #814's round-7 fourth addendum and placed NEXT by the reviewer on
    2026-09-20). THE POPULATION it converts, derived by the census (tests/test_hosts_path_census.py) at #814's head and
    listed there under the follow-up role, five by-path reads under hosts/<sid>/ and no other in the three modules
    that mint such a path: this function's predecessor in kernel/session_host.py (its glob over the directory, its read
    of gaps.json by the directory's path, its open of each segment by the path the glob yielded) and the two journal
    globs in kernel/sdk_backend.py (_host_lease_applies, whether a host held the session, asked with hosts off;
    _host_orphan_recover, whether a tail stands past the acknowledged offset). The host process never called the
    predecessor: the host reads its journal through sh.Journal.read_from, off the in-memory index of the segments it
    wrote itself under a directory sh.owner_only_dir verified (0700, its own uid), and lists the directory for nothing
    (tests/test_session_host.py pins both by execution and by structure), so the host side has no caller to convert and
    asks no owner question of its own directory.
    THE MECHANISM. The caller hands the HostDirs its read descent holds (open_host_dirs_if_present: hosts/ and <sid>
    each opened O_DIRECTORY|O_NOFOLLOW and fstat-verified a directory of this uid), never a path. The listing is a
    scandir OFF THE <sid> DESCRIPTOR with a name match on the segment shape (journal_segments), so a `<sid>/` renamed
    away and a link put in its place after the descent lists the directory the descent verified and not the link's
    target: a descriptor names an inode, a path names whatever stands there now. Each file is then put the owner
    question by NAME under the same descriptor and opened by name under it, through the one reader every kernel read
    of a file under hosts/<sid>/ goes through (_open_host_file: the fstatat before any open, the O_NOFOLLOW|O_NONBLOCK
    open, the fstat of the descriptor it returned, deciding the same way): gaps.json through read_host_file, each
    segment through _open_host_file. The answers, from the readers' table (SHAPE_TABLE in tests/test_host_transport.py),
    file by file: a regular file of ours is read; no entry, or a directory, a FIFO or a socket of ours, is not the file,
    skipped with nothing opened; an entry ANOTHER UID owns, of any kind, is HostFileForeign, handed to `refused` for its
    one row (the kernel files host.directory-refused naming the file, its directory and the owning uid, once per connect
    episode per observed state, sdk_backend._refused_directory_row) and skipped as absent, the road proceeding as it
    does for a foreign identity.json (a foreign gaps.json: the numbering proceeds as with none); a SYMLINK of ours is
    the file-shape refusal, RAISED, and the road that asked is refused as it is by a link at identity.json (the
    lease-applies road answers False after the row; the orphan road's tail check replays nothing; the replay transport
    files the row and ends the stream). The question is asked of the name under the descriptor and of the object
    opened, never of a path: a path stat would reopen the window the descent closes.
    WHAT IT CLOSES: the two roads the item names, both under #814's weaker precondition (a group-writable hosts/, or a
    loose hosts/<sid>/ of ours, under a state root the peer can traverse; not a peer-writable root). A re-point of
    `<sid>` landing between a read road's descent and its listing, which the globs took through the link; and a
    journal file a peer planted under a loose `<sid>/` of ours, which the predecessor read with no owner check. WHAT
    REMAINS by path under hosts/: the connect to the published socket (HostTransport.connect), permanent while the
    transport is a Unix socket (connect(2) has no dir_fd form), and the sites the census lists under its other roles
    (the two directory helpers before the spawn road's descent, the descent's own first open, the host's own writes).
    `refused` None: a foreign entry raises, so a caller with no row to file gets the refusal and never a silent skip.
    CALLERS: the orphan road's tail check (journal_has_tail) and the replay transport (HostTransport._read_journal),
    which BORROWS the descriptor for the replay's life; the road that opened it closes it after the replay
    (sdk_backend._host_orphan_recover). The lease-applies road takes the listing alone (journal_segments)."""
    segs = journal_segments(dirs, refused)
    if not segs:
        return
    gaps = set()
    try:
        raw = read_host_file("gaps.json", dirs)
    except HostFileForeign as e:
        if refused is None:
            raise
        refused(e)                                  # a peer's gaps.json: its row, and the numbering proceeds as with none
        raw = None
    if raw is not None:
        try:
            gaps = set(json.loads(raw))
        except Exception:                           # a malformed gaps.json of ours: no gaps, as the predecessor read it
            gaps = set()
    for first, name in segs:
        try:
            fh = _open_host_file(name, dirs)
        except HostFileForeign as e:                # a peer's entry swapped onto the name since the listing
            if refused is None:
                raise
            refused(e)
            continue
        if fh is None:                              # gone, or not a regular file of ours, since the listing
            continue
        n = first
        while n in gaps:                            # an unrecorded gap at the segment's head
            n += 1
        with fh:
            for line in fh:
                if n >= offset:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        rec = None
                    if rec is not None and rec.get("type") != sh.GAP_TYPE:
                        yield n, rec
                n += 1
                while n in gaps:                    # an unrecorded gap between two records on disk: the numbering skips it
                    n += 1


def journal_has_tail(dirs: HostDirs, offset: int, refused=None) -> bool:
    """Whether a record stands at or past `offset` in the orphan journal under `dirs` (read_journal_dir's first answer;
    the orphan road's tail check, sdk_backend._host_orphan_recover). The generator is closed after its first answer,
    so a segment it opened is closed before the caller reads on."""
    gen = read_journal_dir(dirs, offset, refused)
    try:
        return next(gen, None) is not None
    finally:
        gen.close()


def host_sock_present(dirs: HostDirs, name: str) -> bool:
    """Whether an entry stands at the published socket's NAME (`host_sock(...).name`, `<sid8>.sock`) in the verified
    `hosts/`: a stat by name relative to the `hosts` descriptor, no symlink followed. The spawn wait's poll
    (_host_transport_for; the round-7 second addendum, 2026-09-20: through round 7 it was `sock.exists()`, by PATH, so a
    hosts/ re-pointed during the wait was polled through the link and a peer's entry at the name ended the wait). The
    question is existence, as the poll asked it by path: the spawn road unlinks the name under this descriptor before
    it spawns, and the host publishes by renaming its bound socket onto it; what stands there is connected to next, by
    path (HostTransport.connect, the one site left on a path), and a non-socket fails that connect loudly."""
    try:
        os.stat(name, dir_fd=dirs.hosts, follow_symlinks=False)
    except OSError:
        return False
    return True


def _open_file_nofollow(name: str, flags: int, dirs: HostDirs) -> int:
    """A file under the verified `hosts/<sid>/` opened by NAME relative to its descriptor with O_NOFOLLOW (and
    O_CLOEXEC), mode 0600 when created: the one open every kernel open of a file under hosts/<sid>/ goes through, for
    the readers (_open_host_file) and, since the fork PR that follows #814 (2026-09-21), for the two write opens of the
    spawn road through _open_host_file_for_write, spawn.json (write_spawn_spec) and host.stderr (host_stderr_open),
    which through #814 called this directly with no shape question before it and no O_NONBLOCK on it. A symlink standing at the name fails the open with ELOOP and is refused under
    HostDirRefused, naming the file and the directory, with `file` set (kernel-2, round 5 of the review, 2026-09-20:
    through round 4 the ELOOP surfaced as a bare OSError, outside the class the two call sites catch, so a planted link
    got no problem row and no remedy and _record_launch_error composed the card over a stale stderr tail). Any other
    OSError (a full disk, a permission error such as EACCES on a file of ours with no write bit) propagates as itself
    with its errno: the class is for the shape the descent refuses, not for every failure of the open (a directory at
    the name, EISDIR out of here through #814, no longer reaches this open on either side: the shape question before
    it answers the kind). Nothing is followed and nothing is written on the refused road: O_NOFOLLOW fails the open
    before any descriptor exists."""
    try:
        return os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600, dir_fd=dirs.dir)
    except OSError as e:
        if e.errno == errno.ELOOP:
            e2 = HostDirRefused("%s in host directory %s is a symlink, not a regular file" % (name, dirs.path))
            e2.file = name
            raise e2 from None
        raise


_KIND_WORDS = ((stat.S_ISDIR, "directory"), (stat.S_ISFIFO, "FIFO"), (stat.S_ISSOCK, "socket"),
               (stat.S_ISCHR, "character device"), (stat.S_ISBLK, "block device"), (stat.S_ISLNK, "symlink"))


def _kind_word(mode: int) -> str:
    for test, word in _KIND_WORDS:
        if test(mode):
            return word
    return "special file"


def _not_regular(name: str, dirs: HostDirs, mode: int) -> HostDirRefused:
    """The refusal for a non-regular entry OF OURS at a file's name on the write side, naming the file and its kind
    (`file` and `kind` set, no `uid`): the fork PR that follows #814 (2026-09-21). The read side answers the same entry
    None with nothing opened, because a read of what is not the file has nothing to read; a WRITE would create or
    append to it (a FIFO's open blocking until a reader appears, a directory's failing EISDIR after the fact), so the
    write side refuses it before any open, as it refuses a link, and the spawn road files the row with a remedy naming
    the kind (sdk_backend._refused_directory_row)."""
    kind = _kind_word(mode)
    e = HostDirRefused("%s in host directory %s is a %s, not a regular file" % (name, dirs.path, kind))
    e.file, e.kind = name, kind
    return e


def _open_host_file_for_write(name: str, flags: int, dirs: HostDirs) -> int:
    """`hosts/<sid>/<name>` opened for WRITING through the descent, the one opener the spawn road's two writes share
    (host_stderr_open, write_spawn_spec; the fork PR that follows #814, 2026-09-21, building the small-asks item on the
    two O_WRONLY opens): the readers' shape question first, then the open with O_NONBLOCK, then the fstat of the
    descriptor the open returned, then the mode. Returns the descriptor, at 0600, blocking, or raises with nothing
    opened. Through #814 both writes called _open_file_nofollow directly: O_NOFOLLOW refused a link, and nothing else
    was asked, so a FIFO a peer planted at host.stderr or spawn.json under a <sid>/ of ours while it was loose (a
    tightened directory keeps every entry planted before) BLOCKED the open until a reader opened the other end, inside
    the kernel's event loop, since the spawn road's helpers are synchronous calls in it (driven by the drives verifier
    of #814's final body pass: blocked 2 s, released by a reader end); a directory at the name was EISDIR out of the
    open, a bare launch error with no row.
    FIRST THE SHAPE QUESTION, BEFORE ANY OPEN (_stat_name, the readers' fstatat of the name under the held `<sid>`
    descriptor with no link followed): no entry, and the open below creates the file (O_CREAT, the caller's flag); a
    regular file of ours, and the open below opens it; an entry ANOTHER UID owns, of any kind, HostFileForeign, the owner
    row and the launch refused as the read roads refuse a foreign identity.json (the row names the file, the directory
    and the owning uid); a SYMLINK of ours, the file-shape refusal _stat_name raises (the same words the open's ELOOP
    arm gives a link swapped in after the stat); a directory, a FIFO or a socket of ours, the refusal naming the kind
    (_not_regular), nothing opened, so a FIFO never blocks and a directory never reaches EISDIR.
    THEN THE OPEN, by name under the same descriptor with O_NOFOLLOW (_open_file_nofollow) AND O_NONBLOCK, so a FIFO
    swapped onto the name between the stat and the open cannot block it: with no reader the open ends with ENXIO (a
    socket at the name answers ENXIO too), which asks the shape question once more by name (a peer's entry is its row,
    a non-regular entry of ours is the kind refusal) instead of standing as a bare errno; no entry, or a regular file
    of ours, by then means the object the open met is gone again, and the open's own errno stands, since there is no
    kind to name; with a reader the open returns a descriptor the
    fstat below refuses. THEN THE FSTAT OF THE DESCRIPTOR, the authoritative check since the entry can change between
    the stat and the open, deciding the same way (another uid's, HostFileForeign, closed unwritten; not a regular file,
    the kind refusal, closed unwritten). A caller's O_TRUNC is taken off the open and applied AFTER these checks
    (os.ftruncate on the verified descriptor), so a peer's file swapped onto spawn.json between the stat and the open
    is refused with its bytes intact, where O_TRUNC on the open itself would have emptied it before the fstat ran (a
    directory swapped in answers the open's EISDIR, which asks the shape question again like ENXIO and refuses by
    kind). O_NONBLOCK is then cleared off the descriptor (fcntl F_SETFL): on a regular
    file the flag changes no write, and this descriptor outlives the function as the host's stderr or as spawn.json's
    writer, so it leaves here exactly as #814 returned it. THE MODE LAST, on the descriptor (os.fchmod 0600, kernel-1
    of round 5 of #814's review: O_CREAT's mode applies only to a file this open creates, and a file a previous launch
    left kept its birth mode), after the truncation and before the caller's first write, so the mode is tightened
    while the file is still empty (PR 789's pin, SpawnSpec); a raising fchmod, or any raise after the open, closes the
    descriptor first. Every other
    OSError of the open (ENOSPC, EROFS, EMFILE, EACCES on a file of ours with no write bit) propagates as itself with
    its errno, the launch error's road (sdk_backend._spawn_road_failed). Every question is asked of the name under the
    held descriptor or of the descriptor itself, never of a path (a path stat would reopen the window the descent
    closes); the census (tests/test_hosts_path_census.py) holds every syscall here by-descriptor. Pinned cell by cell
    in tests/test_host_transport.py (WriteOpens: the shape table at both names, the FIFO drive with a bounded join, the
    swap inside the open)."""
    st = _stat_name(name, dirs)
    if st is not None and not stat.S_ISREG(st.st_mode):
        raise _not_regular(name, dirs, st.st_mode)
    try:
        # O_TRUNC is taken OFF the open and applied after the checks (os.ftruncate on the verified descriptor): with it on
        # the open, a peer's regular file swapped onto spawn.json between the stat and the open was truncated before the
        # fstat below refused it, a write onto a file that is not ours
        fd = _open_file_nofollow(name, (flags & ~os.O_TRUNC) | os.O_NONBLOCK, dirs)
    except OSError as e:
        if e.errno in (errno.ENXIO, errno.EISDIR):  # a FIFO with no reader, a socket or a directory swapped onto the name since the stat
            st = _stat_name(name, dirs)             # a peer's: HostFileForeign out of here; a non-regular entry of ours: the kind
            if st is not None and not stat.S_ISREG(st.st_mode):
                raise _not_regular(name, dirs, st.st_mode) from None
            # no entry, or a regular file of ours, by now: the object the open met is gone again and there is no kind
            # to name, so the open's own errno stands (the review fix-up of this PR, on the drives verifier's nit:
            # through the PR's first commit this arm named a regular file of ours a special file)
        raise
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid():
            raise _foreign(name, dirs, st.st_uid)
        if not stat.S_ISREG(st.st_mode):
            raise _not_regular(name, dirs, st.st_mode)
        if flags & os.O_TRUNC:                      # the caller's truncation, on the verified descriptor, before the mode and the write
            os.ftruncate(fd, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) & ~os.O_NONBLOCK)
        os.fchmod(fd, 0o600)
    except BaseException:
        os.close(fd)
        raise
    return fd


def host_stderr_open(dirs: HostDirs) -> int:
    """`hosts/<sid>/host.stderr` opened for the host's stderr through the descent: O_WRONLY|O_CREAT|O_APPEND|O_NOFOLLOW at
    0600, relative to the session directory's descriptor, so the file is created in the directory the kernel verified
    and never through a link at any component. Append, so a previous launch's bytes stay where they are and the kernel's
    watermark (host_stderr_size before the spawn) tells this launch's bytes from them. The caller passes the descriptor
    to Popen as the child's stderr and closes its own copy after the spawn. The mode is set on the descriptor after the
    open (os.fchmod, kernel-1 of round 5 of the review, 2026-09-20): O_CREAT's 0600 applies only to a file this open
    creates, and a host.stderr a previous launch left (a stale kernel-held lease keeps the directory) kept whatever mode
    it was born with, 0664 under the 002 umask every launch before round 4 opened it at, while spawn.json two lines
    away in write_spawn_spec paid the same fchmod for the same reason; a raising fchmod closes the descriptor and
    propagates. A symlink at the name is refused under HostDirRefused (_open_file_nofollow, kernel-2 of the same
    round), the class the launcher's call site already catches. Since the fork PR that follows #814 (2026-09-21) the
    open goes through _open_host_file_for_write: the shape question of the entry at the name before anything is opened
    (a peer's entry of any kind, the owner row and the launch refused; a directory, a FIFO or a socket of ours, a
    refusal naming the kind, nothing opened), O_NONBLOCK on the open and the fstat of the descriptor after it, so a
    FIFO at the name no longer blocks the spawn road inside the event loop."""
    return _open_host_file_for_write("host.stderr", os.O_WRONLY | os.O_CREAT | os.O_APPEND, dirs)


def host_stderr_size(dirs: HostDirs) -> int:
    """host.stderr's size in bytes through the descent (a stat relative to the session directory's descriptor, no
    symlink followed), 0 when there is no such file: the watermark the kernel takes beside host_log_mark before it
    spawns, and reads again at a refusal to say whether THIS launch's host wrote to the file (kernel-1 and
    correctness-1, round 4 of the review, 2026-09-20: the file is append-only and a refused launch clears nothing, so
    a spawn-wait message naming host.stderr for a launch that wrote nothing sent the operator to a previous launch's
    traceback)."""
    try:
        return os.stat("host.stderr", dir_fd=dirs.dir, follow_symlinks=False).st_size
    except OSError:
        return 0


def _rmtree_at(dir_fd: int, name: str) -> None:
    """The tree at `name` under the directory descriptor `dir_fd` removed by descriptors alone: the entry opened
    O_DIRECTORY|O_NOFOLLOW relative to dir_fd (a symlink at the entry fails the open: nothing under a link is ever
    walked), its entries read off the descriptor, each subdirectory taken the same way and every other entry (a symlink
    among them, as an entry) unlinked relative to it, then the directory itself removed relative to dir_fd. The shape
    shutil.rmtree takes on a platform with dir_fd support, written out because rmtree's own dir_fd parameter is 3.11's and
    CI runs 3.10. An entry the listing named that is gone by the time the walk reaches it (a live host still writing and
    rotating its journal beside this walk) is skipped, the ignore_errors semantics of the rmtree this replaced
    (kernel-3, round 5 of the review, 2026-09-20: through round 4 that FileNotFoundError climbed out of the walk to
    remove_host_dir's already-absent arm, which reported the directory cleared with it still standing and its remaining
    entries in it). The skip weakens no refusal: HostDirRefused is built from one text argument and is never a
    FileNotFoundError, and a link or a foreign directory still fails the O_NOFOLLOW open or the fstat above it."""
    fd = os.open(name, _DIR_FLAGS, dir_fd=dir_fd)
    try:
        st = os.fstat(fd)
        if st.st_uid != os.geteuid():               # another uid's directory under ours: not ours to empty
            raise HostDirRefused("directory %s belongs to uid %d, not to us (uid %d)" % (name, st.st_uid, os.geteuid()))
        with os.scandir(fd) as it:
            entries = list(it)
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    _rmtree_at(fd, e.name)
                else:
                    os.unlink(e.name, dir_fd=fd)
            except FileNotFoundError:               # gone since the listing: nothing to remove, the walk goes on
                continue
    finally:
        os.close(fd)
    os.rmdir(name, dir_fd=dir_fd)


def remove_host_dir(state_dir, sid: str, log=None) -> bool:
    """`hosts/<sid>/` cleared through the descent, for the two roads that clear a host's directory (sdk_backend's
    _host_orphan_recover, before the spawn that follows a recovery, and _host_ended, after an end the kernel asked for):
    `hosts/` opened O_DIRECTORY|O_NOFOLLOW off the state root and verified (a directory, this uid's; its mode is not a
    condition here, see _open_dir_nofollow), then the tree under `<sid>` removed by descriptors (_rmtree_at, which refuses
    a `<sid>` that is a link or another uid's), so no component is followed as a link. True
    when the directory is gone afterwards (already absent counts); False when `hosts/` was refused or a removal failed,
    and `log`, when given, is told why. A refusal at `hosts/` or at `<sid>` deletes nothing (the open fails before the
    walk); a refusal DEEPER stops the walk with the entries scandir had already yielded (ours, under our verified
    `<sid>/`) unlinked and the foreign object and everything below it untouched, so a nested refusal is not "deletes
    nothing" (round 5 of the review, 2026-09-20, the docs lens: a two-pass walk would be, and is not taken here).
    Round 4 of the review
    (2026-09-20): these roads ran shutil.rmtree on a path with errors ignored, and with `hosts/` swapped for a symlink to
    a peer's directory the leftover arm of the connect road (a `hosts/<sid>/` seen through the link, no lease) deleted
    the peer's `<sid>/` through it, a write onto a target of the peer's choosing on the road every session start takes.
    The reads that arm makes before this call take the descent since the round-7 second addendum (the directory's
    existence through open_host_dirs_if_present, identity.json through read_host_file), and so does the journal's tail
    since the fork PR that follows #814 (journal_has_tail and read_journal_dir off the same descriptor; the design is
    stated at read_journal_dir)."""
    hosts_path = Path(state_dir) / "hosts"
    try:
        hfd = _open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path, private=False)
    except HostDirRefused as e:
        if log is not None:
            log("host directory hosts/%s not cleared: %s" % (sid, e))
        return False
    try:
        _rmtree_at(hfd, str(sid))
    except FileNotFoundError:
        # the arm for a hosts/<sid>/ already absent (the open of <sid> itself, or its trailing rmdir after a concurrent
        # removal), decided by a stat of the entry off the verified hosts/ descriptor and not by the exception alone
        # (kernel-3, round 5 of the review, 2026-09-20: through round 4 this arm also caught a FileNotFoundError raised
        # INSIDE the walk and reported "cleared" with the directory standing; the walk now skips a vanished entry
        # itself, so what reaches here with <sid> still on disk is logged and reported as not cleared)
        try:
            os.stat(str(sid), dir_fd=hfd, follow_symlinks=False)
        except FileNotFoundError:
            return True
        except OSError:
            pass
        if log is not None:
            log("host directory hosts/%s not cleared: an entry was reported missing during the walk, and the directory still stands" % sid)
        return False
    except HostDirRefused as e:
        if log is not None:
            log("host directory hosts/%s not cleared: %s" % (sid, e))
        return False
    except OSError as e:
        if log is not None:
            log("host directory hosts/%s not cleared: %s: %s" % (sid, type(e).__name__, getattr(e, "strerror", "") or ""))
        return False
    finally:
        os.close(hfd)
    return True


def _open_host_log(dirs: HostDirs):
    """`hosts/<sid>/host.log` for reading on the spawn road, through the one reader (_open_host_file): the owner question
    asked of the entry at the name under the held `<sid>` descriptor (`dirs`, the HostDirs open_host_dirs returned, which
    sdk_backend._host_transport_for holds across the spawn wait so every read goes to the directory the spec was written
    in and not through whatever hosts/ names by then), then the O_NOFOLLOW|O_NONBLOCK open by name and the fstat of the
    descriptor it returned. A regular file of ours, the file object at its start; no entry, or a directory, a FIFO or a
    socket of ours at the name, None with nothing opened (a FIFO's open blocked here through the sixth addendum: no
    O_NONBLOCK and no stat before it); an entry another uid owns, of any kind, HostFileForeign; a symlink of ours, the
    file-shape HostDirRefused. Round 4 of the review (2026-09-20) gave this open the descriptor (through round 3 it
    opened a path, so a hosts/ re-pointed after the spec was written was read through the link); the round-7 seventh
    addendum (2026-09-20) gave it the owner question, which the read roads' reader had since the fourth and this one
    lacked: a host.log a peer planted while `<sid>/` was loose (sh.owner_only_dir tightens the directory on the spawn
    road and keeps every entry in it) was read as this host's, its `error` the card's reason and its rows this launch's.
    The by-path arm this took with no descriptor (dir_fd None; unreachable, held so by the census's forwarding pin) is
    gone with the signature: every caller holds the descent, and a reader handed none is a TypeError, not a path."""
    return _open_host_file("host.log", dirs)


def host_log_mark(dirs: HostDirs) -> int:
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
    served road on this mark is the queued served-road change, where that behaviour is fixed, not this one.

    `dirs` (round 4 of the review, 2026-09-20, as the session directory's descriptor; the round-7 seventh addendum, the
    HostDirs open_host_dirs returned): the descent sdk_backend._host_transport_for holds across the spawn wait; the size
    is read from the fstatat of the NAME under its `<sid>` descriptor, never through a path a re-pointed hosts/ could
    redirect. THE OWNER QUESTION (the seventh addendum, 2026-09-20) is that same stat, the read roads' _stat_name: the
    size of a regular file of ours; 0 for no entry and for a directory, a FIFO or a socket of ours (no file, so the mark
    is the start); HostFileForeign for an entry another uid owns, of any kind, and the file-shape refusal for a symlink
    of ours, both RAISED to the caller, which refuses the launch before any process starts (a watermark taken on a file
    that is not this host's would bound this launch's reads to a peer's bytes). Through the sixth addendum the stat
    asked no owner question and a peer's host.log at the name answered its size. A fault of the stat (EIO; EACCES cannot
    reach a directory this road verified 0700 and ours) is 0, the arm this has had since it was written; the refusal
    class, an OSError too, is re-raised ahead of it and is not among what that arm swallows."""
    try:
        st = _stat_name("host.log", dirs)
    except HostDirRefused:
        raise
    except OSError:
        return 0
    return st.st_size if st is not None and stat.S_ISREG(st.st_mode) else 0


def host_log_rows(dirs: HostDirs, since: int = 0) -> list:
    """The parsed rows of hosts/<sid>/host.log from byte `since` on (a host_log_mark; 0 is the whole file), in
    order; [] for a missing or unreadable log, and for a directory, a FIFO or a socket of ours at the name (nothing
    opened). A line that is not a JSON object is skipped. `dirs`: the HostDirs the spawn road holds (open_host_dirs); the
    file is opened by name relative to its `<sid>` descriptor through _open_host_log, which asks the owner question (the
    round-7 seventh addendum, 2026-09-20): an entry another uid owns raises HostFileForeign and a symlink of ours the
    file-shape refusal, out of this function, for the caller to file as a row (sdk_backend._refused_launch_log), where
    through the sixth addendum a peer's rows were this launch's. The OSError arm below answers a FAULT (EMFILE, EIO) with
    [], as it has since it was written; the refusal class, an OSError too, is re-raised ahead of it."""
    try:
        f = _open_host_log(dirs)
        if f is None:
            return []
        with f:
            f.seek(int(since or 0))
            data = f.read()
    except HostDirRefused:
        raise
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


def host_exit_reason(dirs: HostDirs, since: int = 0) -> str:
    """What a host that exited before serving its socket said last: the `error` of its final `host-crashed` or
    `cli-spawn-failed` row, for the kernel's launch error; "" when no row says (an unreadable log, a host that
    died without one). `since` is the host_log_mark the kernel took before the spawn: the rows read are the ones
    this host wrote, and a previous host's rows in the same file are never this launch's reason (the closing check
    of the review, 2026-09-18; the round-2 bound at the last host-started row left the no-row case reading the
    previous run, see host_log_mark). Added 2026-09-18 so an SDK pin mismatch (session_host.py,
    SdkInternalsMismatch) reaches the card with both versions and the repin command instead of "see host.log"
    (the box admin's hazard review of the pull-in, 2026-09-16).

    What the text is (correctness-2 and kernel-3, round 1 of the review, 2026-09-18; the generic row restated at
    round 4, kernel-3 and extra8-1, 2026-09-20): a host-composed row (the SDK mismatch) is carried whole, and its text
    is the host's own prose (two version strings, a module path, the remedy, and the cause's type and message bounded
    at SDK_CAUSE_CAP characters). The generic host-crashed row carries the exception's class name as `error`, its errno
    as `errno` when the exception is an OSError with an integer errno, and the failing frame as `at`, never the text
    (session_host.py main(): an OSError's text carries the path it failed on, a spec field). This function returns the
    `error` field alone, so for that row the card reads the bare class name (`OSError`) and the errno and the frame
    stay in host.log; the diagnosis of a socket failure is the host's socket-bind-failed row beside it (step, the error
    class, errno, pathLen, limit, at). Through round 2 of the socket-mode fix the generic row carried the traceback's
    last line and could read "OSError: AF_UNIX path too long"; it no longer can. The host writes no spec field and no
    environment value to host.log (its module docstring); that is the guarantee, not "prose".

    `dirs` (round 4, 2026-09-20, as the session directory's descriptor; the round-7 seventh addendum, the HostDirs the
    spawn road holds): the rows are read by name relative to its `<sid>` descriptor (host_log_rows), the owner question
    asked first, so a host.log another uid owns at the name is HostFileForeign out of this function and never a reason.

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
    rows = host_log_rows(dirs, since)
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


HELPER_SHAPE_ERRNOS = (errno.EEXIST, errno.ENOTDIR, errno.ELOOP, errno.ENOENT)
# The errnos of the two directory helpers (sh.hosts_dir, sh.owner_only_dir) that mean the directory's SHAPE is wrong,
# the class write_spawn_spec's wrap files as HostDirRefused with the directory remedy (round 7 of the review, 2026-09-20;
# the round-6 rulings, C). Keyed on the errno, never on how the shape was planted: EEXIST is pathlib's mkdir(exist_ok=True)
# re-raising for a name taken by a non-directory (a regular file, a FIFO, a dangling symlink, a symlink to a file, at
# hosts/ or at hosts/<sid>/), ENOTDIR a component that is not a directory (a plain-file state root, which only the
# operator can cause and which the same remedy fits; or hosts/ re-pointed to a file between the helpers, which a peer
# can), ELOOP a symlink loop met by a helper's mkdir (hosts/ re-pointed between the helpers to a link that names itself;
# a self-loop already standing AT hosts/ when the first helper runs is EEXIST instead, since os.mkdir reports the name
# taken and pathlib's is_dir() swallows the ELOOP of the stat that follows), and ENOENT a missing component, which between
# the two helpers is hosts/ re-pointed to a DANGLING link, a peer's one-syscall plant, or a dangling target under the
# second helper's chmod, and which the descent's own open already files as "does not exist"; it joins the class for both
# reasons. EEXIST is also what the second helper's mkdir meets when hosts/ was re-pointed to a directory already holding
# <sid> as a non-directory (nothing is made or chmodded there). Outside the set, an errno is a filesystem failure and stays the launch error with its
# errno: ENOSPC and EROFS (only the machine causes them), EACCES and EPERM (a peer CAN cause these too, with hosts/
# re-pointed to a directory this uid cannot write or, at the chmod leg, to an object it does not own; by the round-6
# ruling they pass through unchanged, so that road reads the errno's text with the path, no remedy, no refusal row).


def helper_shape_refusal(e: OSError, state_dir, sid: str) -> str:
    """The sentence for a shape errno one of the two helpers raised: the component the errno's filename names, in the
    nouns the helpers' own refusals use (`state root`, `hosts directory`, `host directory`; a directory above the root
    that the create road's parents=True mkdir met, or any other path, is named as what it is), then what the errno says
    of it. An errno with no filename is read as the second helper's directory, the only helper syscall that raises one
    without it in this tree's Python. Through round 7 every component but hosts/ read `host directory`, so a state
    root that was a dangling symlink was refused as `host directory <root> is not a directory`: pathlib's mkdir with
    parents=True meets the root by path on the way up and re-raises EEXIST with the root as the filename (the round-7
    addendum, 2026-09-20)."""
    root = Path(state_dir)
    hosts_path = root / "hosts"
    leaf = host_dir(state_dir, sid)
    failed = Path(e.filename) if getattr(e, "filename", None) else leaf
    if failed == hosts_path:
        what = "hosts directory"
    elif failed == leaf:
        what = "host directory"
    elif failed == root:
        what = "state root"
    elif failed in root.parents:
        what = "directory above the state root"
    else:
        what = "directory"
    if e.errno == errno.EEXIST:
        why = "is not a directory"
    elif e.errno == errno.ENOTDIR:
        why = "is not a directory, or a directory above it is not"
    elif e.errno == errno.ELOOP:
        why = "is not a directory (a symlink loop)"
    else:
        why = "does not exist (a component is missing, or a symlink there dangles)"
    return "%s %s %s" % (what, failed, why)


def write_spawn_spec(state_dir, sid: str, spec: dict) -> Path:
    """`hosts/<sid>/spawn.json`, the directory at 0700 and the file at 0600: the spec carries the
    environment overlay, minus the credential-shaped names of it as the kernel's split_spawn_secrets draws
    them (spawn_env_secret_names: the three login names whatever their value, and a non-empty value under a
    name ending _API_KEY or _TOKEN or one of 1Password's, in any letter case), moved to the host's process
    environment before this write; a name of another shape stays in the file with its value, as it was (a
    non-string value included, which the host's SDK transport cannot spawn from; pre-existing, named in the
    kernel's split_spawn_secrets). The shape is
    spelled out here because this sentence once claimed every credential-shaped name (review round 1's
    addendum, 2026-09-18): a password, a client secret or a private key under a name of another shape would
    be written, and the shape is deliberately not widened to catch them, since no such name has a road into
    the overlay today and a legitimate TOKEN_BUDGET or PRIVATE_KEY_PATH would be moved out of the file for
    nothing. A credential never lives in a file, the fork's rule, and the box admin's hazard review of the
    pull-in, 2026-09-16, found the first cut moving the three login names alone.
    `hosts/` itself is made 0700 first (sh.hosts_dir: this is the road that creates it on
    a fresh state root, and until 2026-09-19 the mkdir with parents=True left it at the umask's mode; the
    host's control socket is bound in that directory, so its mode is the one guard on the socket's temp name).
    Then `hosts/<sid>/` through the same helper (sh.owner_only_dir, the shape hosts_dir is): born 0700 by its
    mkdir's own mode, lstat'd, refused as a symlink or another uid's, a loose one tightened and read back. Until
    the fix's round 2 (2026-09-19) this line was a bare mkdir and a chmod never read back, so a symlink planted
    at `hosts/<sid>/` was followed and the spec written through it while `hosts/` one line above was checked.
    Either helper raises (OSError) for a directory that is a symlink, belongs to another uid, or stays loose
    after its chmod, and this spawn then fails before a spec is written: the failure surfaces as the launch
    error, naming the directory, never as a host started over a directory we do not own (the review of the
    socket-mode fix, 2026-09-19). The residual the helper's docstring states (a re-point between its read-back
    and a path-taking open) is closed for this write since round 4 of the review: the open below takes a name
    relative to a held descriptor, not a path, and a link swapped in after the read-back fails it (the paragraph
    on the open, below). WHAT STILL TAKES A PATH (correctness-2 and extra5-1, round 5 of the review; restated to the
    code's window at round 7, correctness-2 and extra6-2, and counted from the code at the round-7 addendum,
    2026-09-20): the two directory helpers themselves. Each of sh.hosts_dir (hosts/) and sh.owner_only_dir
    (hosts/<sid>/) makes and checks its directory by PATH in up to FIVE syscalls: its mkdir; on an existing directory,
    the stat pathlib.Path.mkdir makes after the failed os.mkdir to decide whether EEXIST re-raises (`if not exist_ok or
    not self.is_dir(): raise`; a stat, so it follows a link standing there); its lstat; and, only when that lstat read
    a loose directory of ours, its chmod and the read-back lstat (recorded at the addendum by interposing the four os
    calls: a fresh directory, mkdir and lstat; an existing 0700 one, mkdir, stat, lstat; an existing loose one, mkdir,
    stat, lstat, chmod, lstat). hosts_dir also stats the root by path before its helper (`root.exists()`, the
    create-road decision). So the window runs from hosts_dir's first syscall to owner_only_dir's read-back, INSIDE each
    helper as much as between them, and a re-point of hosts/ or of the <sid> leaf landing anywhere in it is followed by
    the syscalls after it. What each landing does, by execution at round 7 and its addendum: a link swapped in at
    EITHER component between its helper's lstat (which read a loose directory of ours; hosts/ is loose on every install
    from before 2026-09-19, 0775 under the live umask, so the first spawn after this lands takes that chmod on hosts/
    for real) and its chmod is followed by that chmod onto whatever the link names, any object this uid owns anywhere,
    a regular file included, and on a file 0700 is a LOOSENING (a 0400 file outside the state root read 0700 after,
    driven at hosts/ and at the <sid> leaf); the read-back then refuses, its lstat reading the link itself, under the
    words "stays group/world-accessible". The same chmod onto an object this uid does NOT own ends with EPERM, outside
    the class: the launch error with errno 1, the target's mode unchanged (a root-owned 0644 file read 0644 after);
    onto a target that dangles, with ENOENT, refused under the class as "does not exist". A hosts/ re-pointed between
    the two helpers to a directory gets an empty 0700 <sid>/ of ours made inside it (or a loose <sid>/ of ours already
    there tightened), no content, and the descent below then refuses the link; when that directory already holds <sid>
    as a NON-directory (a regular file, a dangling link, a link to a file) the second helper's mkdir ends with EEXIST,
    refused under the class as "host directory ... is not a directory", nothing made and nothing chmodded (the link's
    0400 target read 0400 after). A hosts/ re-pointed between them to a DANGLING link, a regular file, a link to itself
    or a directory this uid cannot write never reaches the descent: the second helper's mkdir ends with ENOENT, ENOTDIR,
    ELOOP or EACCES, and the wrap below files the first three under the class and lets EACCES through as the launch
    error with its errno. Under the same precondition as every residual here (a state root a peer can write while a
    session starts); closing it means making hosts/<sid>/ with mkdir and fchmod relative to a verified descriptor on
    hosts/, its own change.
    The file's mode is set on the descriptor BEFORE the write (os.fchmod): a
    pre-existing file keeps its old mode through O_CREAT|O_TRUNC, and the trailing chmod this had until
    2026-09-18 tightened it only after the overlay was already in it (PR 789, review round 1, the same
    write-then-tighten window the reg and the parked-ops mirror lost). fchmod is exact under any umask. The published
    inode is rewritten in place (O_TRUNC on the path; no temp, no os.replace, unlike write_reg), so the tightening is
    not retroactive for a descriptor another uid opened while the file sat at its old looser mode: it reads the new
    overlay through it. The 0700 directory above, and the 0700 state root above that, close that road today (review
    round 2, 2026-09-19). A raising fchmod closes the descriptor before the error propagates (round 2 too: os.fdopen
    was the only close).
    THE OPEN TAKES NO PATH (round 4 of the review, 2026-09-20): once both directories are made and checked, the file is
    opened by NAME relative to a descriptor on hosts/<sid>/ reached by open_host_dirs (hosts/ opened O_DIRECTORY|O_NOFOLLOW
    off the root and verified by fstat, then <sid> the same way relative to it), with O_NOFOLLOW on the file too. So
    the residual the two helpers' docstrings state for a path-taking open, a hosts/ or hosts/<sid>/ re-pointed between
    the helper's read-back and the open, is closed for this write: a link swapped in at either component fails the
    open (ENOTDIR on Linux under O_DIRECTORY|O_NOFOLLOW, ELOOP elsewhere; the descent handles both) and the spawn is
    refused with the reason (HostDirRefused, which the kernel files as a problem row
    with the remedy). A symlink standing at spawn.json itself fails that O_NOFOLLOW open and is refused under the same
    class, naming the file (_open_file_nofollow; kernel-2, round 5 of the review, 2026-09-20: through round 4 it was a
    bare OSError outside the class). What the wrap around the two helpers files under the class (round 7 of the
    review, 2026-09-20, the round-6 rulings' C): a refusal a helper decided (a single-argument OSError, errno None: a
    symlink to a directory, another uid's, stays loose), in the helper's own words; and an errno of HELPER_SHAPE_ERRNOS
    (EEXIST, ENOTDIR, ELOOP, ENOENT; the comment above the set says what each is and why), worded by
    helper_shape_refusal. Every other errno (a full disk, a read-only filesystem, an unwritable target) propagates as
    the OSError it is, errno and all, to the kernel's launch error. Two earlier keys were each wrong on one side:
    round 4 folded every OSError into the class (a full disk got the directory remedy), round 5 keyed on `errno is
    None` (a regular file, a FIFO, a dangling link or a link to a file at either directory got "[Errno 17] File exists"
    with no row and no remedy, since pathlib's mkdir(exist_ok=True) re-raises before the helper's lstat runs)."""
    try:
        sh.hosts_dir(state_dir)
        sh.owner_only_dir(host_dir(state_dir, sid), "host directory")
    except OSError as e:
        if e.errno is None:                          # a refusal the helper decided, in its own words
            raise HostDirRefused(str(e)) from e
        if e.errno not in HELPER_SHAPE_ERRNOS:       # a filesystem failure (a full disk, a read-only or unwritable target)
            raise
        raise HostDirRefused(helper_shape_refusal(e, state_dir, sid)) from e
    p = host_dir(state_dir, sid) / "spawn.json"
    with open_host_dirs(state_dir, sid) as dirs:
        # the one write opener since the fork PR that follows #814 (2026-09-21; _open_host_file_for_write): the shape
        # question of the entry at spawn.json before anything is opened (a peer's entry of any kind is the owner row and
        # the launch refused; a directory, a FIFO or a socket of ours is a refusal naming the kind, nothing opened, where
        # through #814 a FIFO blocked this open inside the event loop until a reader appeared), then the open with
        # O_NONBLOCK, the fstat of the descriptor, and the fchmod that was here, with the same close-and-reraise
        fd = _open_host_file_for_write("spawn.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, dirs)
        with os.fdopen(fd, "w") as f:
            json.dump(spec, f)
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
                 on_ack=None, on_hello=None, on_stderr=None, on_exit=None, on_fault=None, journal_dirs=None, on_refused=None):
        self.sock_path = str(sock_path) if sock_path else None
        # replay mode holds the read descent's HostDirs on the orphan's hosts/<sid>/ (the fork PR that follows #814,
        # 2026-09-21; a directory PATH through #814): the records are read by name under its descriptor
        # (read_journal_dir), and `on_refused` files the kernel's row for an entry the reader refuses (a peer's file,
        # skipped; a link of ours, which ends the replay). `journal_dir` stays the replay FLAG every mode check below and
        # the spend fold's orphan test in sdk_backend read (`if self.journal_dir`), now the directory's path as the descent
        # names it, for wording alone: nothing opens it. The descriptor is BORROWED: the road that opened it closes it
        # after the replay.
        self.journal_dirs = journal_dirs
        self.on_refused = on_refused
        self.kernel = dict(kernel or {})
        self.ack_offset = int(ack)
        self.replay_end = None          # the journal's next offset at the attach (the hello's journal.next): records before
        #                                 it are the replay, records from it on are live (T354's spend fold)
        self.result_tags = collections.deque()   # one tag per RESULT record handed over, in order: {"offset", "replay"};
        #                                 the consumer reads the transport through a buffered stream a record ahead, so the
        #                                 transport's current offset is never the handled record's; the tag is
        self.end_grace = float(end_grace)
        self.on_ack, self.on_hello, self.on_stderr, self.on_exit, self.on_fault = on_ack, on_hello, on_stderr, on_exit, on_fault
        self.journal_dir = str(journal_dirs.path) if journal_dirs is not None else None
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
    def from_journal(cls, dirs, ack=sh.ACK_NONE, **kw):
        """The replay transport over the orphan journal under `dirs`, the HostDirs the caller's read descent holds
        (host_transport.open_host_dirs_if_present); `on_refused` in `kw` takes the reader's refusals (read_journal_dir);
        with none given a refusal is raised out of read_messages, never a silent end of the stream (_read_journal).
        The caller keeps the descriptor open through the replay and closes it after."""
        return cls(None, ack=ack, journal_dirs=dirs, **kw)

    # ── Transport ──
    async def connect(self) -> None:
        if self.journal_dir:
            self._synth = asyncio.Queue()
            self._ready = True
            return
        # PERMANENT RESIDUAL, closed as an open item (the round-7 fourth addendum of the review, 2026-09-20, the reviewer's
        # ruling of 19:12Z; the second addendum moved the kernel's other reads under hosts/ onto descriptors): a Unix
        # socket is connected by the PATH in its address, and connect(2) has no dir_fd form, so this one read of hosts/
        # stays by path on its three roads (the attach by lease, the first connect after the spawn wait, the end by
        # lease) for as long as the transport is a Unix socket. The descriptor-relative spellings (a connect through
        # /proc/self/fd/<hosts fd>/<name>, or a chdir on the descriptor) are a different mechanism, not this one made
        # relative, and none is queued. What a re-point of hosts/ between the poll and this line gets: a connect through
        # the link, no write; the peer's server then holds the attach frame (the kernel's identity and an offset) and
        # can answer hello. Its precondition is a state root a peer can WRITE: the swap of hosts/ is a rename in the
        # root, and the spawn road's helpers have tightened hosts/ itself to 0700 before the unlink, the spawn and the
        # poll, so a peer's entry at the published name inside our hosts/ is not constructible by then.
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
        # The journal by descriptor (the fork PR that follows #814, 2026-09-21; the design is stated at read_journal_dir):
        # the segments are listed off the <sid> descriptor the orphan road's descent holds and handed here
        # (from_journal), and gaps.json and each segment are opened by name under it through the one reader, the owner
        # question asked of each. Through #814 this site read UNCONVERTED, one of the item's five: sh.read_journal_dir
        # listed the segments with a glob over the directory PATH and opened each file by the path the glob yielded, so
        # a re-point of <sid> landing between the road's descent and this read was read through the link and a journal
        # file a peer planted under a loose <sid>/ of ours was replayed with no owner check. Now a peer's file is its
        # row (on_refused, the kernel's) and skipped, and a link of ours at a segment or at gaps.json ends the replay
        # after the row: the stream then ends as it does at the journal's end (the Query's initialize answered below,
        # then the replay-end exit), never a raise out of the read loop for a shape at a name. WITH NO on_refused the
        # refusal is RAISED out of the read loop instead, as read_journal_dir raises with `refused` None: a caller with
        # no row to file gets the refusal, never a silent end (the review fix-up of this PR, on the drives verifier's
        # finding: through the PR's first commit this arm swallowed it, and a foreign segment beside ours ended the
        # stream replay-end with none of our records replayed, since the listing raises before the first record).
        try:
            for off, rec in read_journal_dir(self.journal_dirs, self.ack_offset + 1, self.on_refused):
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
        except HostDirRefused as e:                          # a link of ours at a segment or at gaps.json: the rest is not replayed
            if self.on_refused is None:                      # no row to file: the refusal itself, out of read_messages
                raise
            self.on_refused(e)
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
