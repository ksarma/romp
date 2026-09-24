"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import atexit
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import tempfile
import threading
import time

import pytest
from _pytest._code.code import ReprExceptionInfo, ReprFileLocation, ReprTracebackNative

# Temp-directory hygiene, the child-process half (2026-09-06): every temp path a run creates lives
# under ONE private `romp-tests-*` root, removed when the run ends. The root, the redirect of
# tempfile.tempdir and TMPDIR into it and the owner marker the kernel's sweep reads are the tests
# PACKAGE's (tests/__init__.py, whose comments have the leak's history and the marker's): the
# package imports before this file under pytest and before the module under `python -m unittest
# tests.test_x`, so a bare run has the same root as a pytest run (until 2026-09-14 this file minted
# it, and a bare run had no root, no redirect and no marker). This file keeps the pytest side: the
# removal at run end with a survivor named, below. Imported, not looked up with a default: a conftest
# running without the package has no root to remove and should say so (tests/test_env_value_redaction.py's
# child runs load a COPY of this file from a scratch dir, with the checkout on PYTHONPATH for this line).
# This module's own XDG floor below and every module-level mkdtemp at collection land inside the root
# because the package redirected before either ran.
# The two removals compose without overlap: pytest_sessionfinish runs the hook's sweep, whose scope
# is gettempdir() and so the inside of the root; pytest_unconfigure then removes the root whole
# (whatever the sweep could not see), the package's romp-tests-state-* dir included, which sits
# inside it. Under pytest-xdist both hooks run in the controller and in every worker: each imported
# the package and this file and so owns a root of its own, and a worker's sits BESIDE the controller's
# in the system temp dir the package recorded (ROMP_TESTS_SYSTEM_TMPDIR, a setdefault the worker
# inherits), never inside it: beside whenever that recorded dir exists, differs from the handed dir and
# is its parent; otherwise inside the handed dir, as before, and the PrivateTempRoot pin in
# tests/test_tempdir_hygiene.py reds on that shape (2026-09-21; nested until then, and each level cost 20 bytes of the AF_UNIX
# socket path budget, which put the deepest hosts-on lab's socket at the budget exactly under a 17-byte
# TMPDIR under -n: the package's comment has the arithmetic). Each process removes its own root; the
# controller's removal below also takes the root of any worker that died without its hooks (the
# package lists each child's pid and root in `romp-tests-children` inside the parent's root, and xdist
# tears the workers down before the controller's unconfigure runs), so a killed worker leaks nothing.
# The atexit registrations (the package's and this file's) are silent fallbacks for a normal exit
# that skipped the hooks, each a no-op on what the other removed; nothing runs after an os._exit
# (pytest-timeout's thread method ends a hung run that way), so a hang leaves its root, marked, as a
# top-level entry in the system temp dir, for the kernel's sweep.
import tests as _tests  # noqa: E402  the package; its import is what minted the root this file removes
_TMP_ROOT = _tests.TMP_ROOT
TEST_ROOT_OWNER_MARKER = _tests.TEST_ROOT_OWNER_MARKER   # tests/test_test_root_sweep.py pins it against the kernel's


def _remove_run_dirs(report=False):
    """Remove the root (the package state dir is inside it), after the roots of its DEAD children (an xdist worker
    that died without its own removal; the package lists them inside this root). A survivor is named on stderr when
    asked, a dead child's as much as this root: rmtree with ignore_errors swallows a child still writing under the
    root or a 000-mode directory a test left behind, and the run would otherwise end green with the root standing.
    Only unconfigure asks; the atexit fallback stays silent so it neither repeats the notice nor contradicts it."""
    survivors = _tests.remove_dead_children(_TMP_ROOT)
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)
    if report:
        for root in [_TMP_ROOT] + survivors:
            if os.path.isdir(root):
                print("[tests] not removed at run end: %s" % root, file=sys.stderr)


atexit.register(_remove_run_dirs)


# Run-end process check (2026-09-22, the reviewer's ruling on fork PR #813's finding; its reads widened and its unread
# classes named 2026-09-24, round 2 of fork PR #894's review): the check names a process whose environment, cwd, open
# files or argv hold a path under the run's roots. A test that starts a process and does not stop it leaves one that
# holds the run's temp root: a real postal bus started from the peer-notify guard test's revive road (a detached child,
# its own session, so the test's end never reached it) kept writing into a shared state root every 30 s and turned
# another module's snapshot test red in one CI cell, and orphan test kernels have outlived whole sweeps by days; the
# kernel's dead-root sweep reaps roots, never processes. So the controller's session end reads /proc for every live
# process and judges it by four reads: its environment (a value that is one of this run's roots or a path under one, a
# ':'-joined value counted per component; the block the process was STARTED with, which is what a child inherits), its
# cwd, the targets of its open file descriptors (/proc/<pid>/fd) and its argv (each argument, the part after an
# argument's first '=', and each ':'-joined component of either). Each root is compared by its spelling, folded as a
# value is (below), and by its realpath: /proc resolves a cwd and a descriptor's target, so under a symlinked TMPDIR a
# cwd in the root reads as the realpath (a trailing " (deleted)" the kernel adds once the target is removed is dropped);
# a TMPDIR spelled with a leading '//' leaves it in the root's spelling (tempfile folds every other doubled separator
# and dot segment, and keeps exactly two leading separators), and the values the run's processes inherit are spelled the
# same way. An environment value and an argument are read folded (_lexical): a doubled separator and a '.' or '..'
# segment are folded as os.path.normpath folds them, so <system>//<root name>/x and <root>/./x are read as the paths
# they name; the fold is lexical, so a '..' after a symlink is folded as if the symlink were a directory, and such a
# value is named when its folded spelling is under a root though its real path is not (the safe side). A relative value
# or argument (one not starting with '/') is read as the path it names from the process's cwd as /proc reads it (joined
# to the cwd, then folded) when it carries the name of a root's directory, so <root name>/x from the root's parent is
# read as <root>/x: from a cwd outside every root a relative path reaches under one only by naming that root's
# directory, and a process whose cwd is under a root holds it through the cwd (a relative value without a root's name is
# then not among the names it is reported through; its cwd is). If any remain the run is RED
# and each is named: pid, parent, command line, what it holds the root through (the environment names, "cwd", "fd",
# "argv"), and the test PHASE current when it was spawned (PYTEST_CURRENT_TEST, inherited from the test process's
# environment at the spawn). That phase is a pointer, not the culprit's name: a thread's spawn inherits the phase
# current when it spawns, so a child a background thread spawns may carry a later phase, another test's, or none (the
# reproduction's bus carried the guard test on 3.10 and no PYTEST_CURRENT_TEST at all on 3.12, its spawn falling after
# the call phase ended); the witness is the pid and the command line. A holder with no PYTEST_CURRENT_TEST is reported
# as that: its phase is unknown, because it was spawned while no phase was set or was given an environment built
# without the name. Keyed on that PROPERTY and never on a binary's name: a bus, a kernel, a session host, a mock ssh's
# sleep are all the same leak.
# The roots are the controller's and every root listed in its `romp-tests-children`: since 2026-09-24 a nested process
# (an xdist worker, a nested pytest, any child of the run that imports the tests package handed a root as its TMPDIR
# together with the run's ROMP_TESTS_SYSTEM_TMPDIR, as a child given a copy of its parent's environment is) lists itself
# at mint time in the root of every process above it, the run's first included (tests/__init__.py, the lineage), so the
# list the controller reads names every nested root of the run, at any depth, after the processes between have removed
# their own roots; until then a nested root was listed only in its parent's root, which an xdist worker removes at its
# unconfigure and a nested pytest before its caller's test returns, and a process two levels down held a root no
# surviving list named (correctness-1). A child handed a root as its TMPDIR without that name (an environment built with
# TMPDIR alone) does not nest: it mints its root inside the handed root and lists itself nowhere, and is read all the
# same, since its root is a path under a run root. The workers themselves skip the check, and are gone when it runs
# (xdist's DSession tears its nodes down in its own sessionfinish, which precedes this trylast one; a worker that
# lingered would be reported by its command line, a visible red and not a silent miss). Events over heuristics: a child
# a test signalled and did not wait for is legitimately EXITING at session end, so the check waits for the one event it
# can observe, the pid's exit, and reports whatever still holds a root when the wait ends. A bound remains because a
# process that never exits has no event to wait for; LEAK_EXIT_BOUND_S is longer than a signalled child takes to exit
# on the box (the leaked bus of the reproduction was gone within a second of its SIGTERM). The wait starts only when a
# holder is seen or a process is listed as not judged (below), so a run with neither pays nothing for it, and a run that
# leaves only a listed process waits for that process's exit, up to the whole bound, and stays green. Before the scan
# the controller joins its live non-daemon threads other than the main one within the same bound, so a process such a
# thread starts after its test returned is seen. A thread that ends costs the run only the time until it ends (the
# interpreter would join it at exit anyway); one that ends only through threading's exit hooks, which run at
# interpreter exit after this check, is waited the whole bound and reported as still running: the worker of an idle
# concurrent.futures pool a test never shut down (an unclosed event loop's default executor is one), whose witness is
# tests/test_run_end_leaked_processes.py's idle-pool case. The join never waits on a daemon thread (a server thread
# left running would make every run pay the bound). The check never kills: the pid it names is the
# developer's to stop (a bus by its server.pid), and a kill from here would be a destructive action on a report the
# developer has not read.
# What the check does not read, each named with its reason (tests/README.md has the same list):
#   * a process whose environment, cwd, open files and argv carry no path under a root, as one handed a built
#     environment with its cwd elsewhere and no file open in the root: the check keys on holding a root, and such a
#     process holds none (a per-run cgroup, or a walk of the process tree from the controller, would see it);
#     tests/test_run_end_leaked_processes.py's residual probe is the witness, unnamed at the run end;
#   * a path spelled through a symlink outside the root, in an environment value or an argument, absolute or relative:
#     the spelling is compared, folded lexically and never resolved (the kernel resolves a cwd and a descriptor, so
#     those two are read under a symlink);
#   * a relative value or argument as the process used it from an earlier cwd: it is read from the cwd the process has
#     at the scan, so one that changed directory after it used the value is read from the later cwd;
#   * a path inside a longer string, as code text in an argument (python -c "open('<root>/x')") or an option inside an
#     environment value; a Unix socket bound under a root, whose descriptor reads socket:[inode]; a file mapped with no
#     descriptor left open (/proc/<pid>/maps is not read); an environment the process changed after it started;
#   * a process that is not nested and whose root lies outside every run root (one handed a TMPDIR that is no root
#     mints inside that dir; tests/__init__.py, the lineage);
#   * a process whose environment cannot be read: another user's, or one of this user's that made itself non-dumpable
#     (ssh-agent, gpg-agent and op do; a setuid program is the same), whose cwd and descriptors are unreadable too. One
#     of this user's that started after the controller and shares its cgroup is listed by pid and command line as not
#     judged (waited for like a holder first), whether or not a holder was found, and does not change the exit status;
#     that condition cannot tell this run's process from another run's in the same cgroup (a sibling test's child run
#     under pytest-xdist, a second run started from the same shell), which is listed too; the rest (other users', and
#     this user's started before the run or in another cgroup, as a peer session's agent is) are a count, printed with
#     any report;
#   * a process started after the scan: by a non-daemon thread still running when the join's bound ran out, by a
#     daemon thread, or by any process outside this one. The threads of the first two kinds are reported by count and
#     name, with the statement that a process they start after the scan is not seen.
# The added reads' cost on a clean run, measured on the box (2026-09-24, the scan over one root, the median of 15 rounds
# interleaved with 951479a14's scan): about 780 processes, 150 of them this user's and readable with 1,800 to 2,300
# descriptors open; the scan took 67 ms on 3.12 and 71 ms on 3.10 against 39 ms, the descriptor and argv reads 20 to 23
# ms of the difference. The fold of environment values and arguments (_lexical), measured later the same day on a busier
# box (41 rounds, the median of each round's paired difference, about 910 processes at a load of 38 on 60 cores): the
# scan took 104 ms on 3.12 and 109 ms on 3.10 against 951479a14's 51 and 50 ms, the fold 6 and 10 ms of that, for about
# 330 values folded per scan, 311 of them a leading '//' that a ':' split leaves of a URL. The relative read, measured
# later again (two runs of 41 rounds on each interpreter, the median of each round's paired difference against the scan
# before it, which walked every relative component up its parents unjoined; 970 to 1,080 processes at a load of 27 to
# 38): the scan took 5 to 11 ms less on 3.12 and on 3.10, at 143 to 251 ms, since a scan meets 19,000 to 23,000 relative
# components, none of them carried a root's name, and one that carries none is now passed over without that walk. A
# clean run scans once, and its join waits for nothing when no non-daemon thread is running.
# A platform without procfs says so once, runs no check and leaves the exit status alone.
# tests/test_run_end_leaked_processes.py pins the scan, the wait, the join, the roots and the red run end by execution.
LEAK_EXIT_BOUND_S = 5.0
LEAK_EXIT_BOUND_ENV = "ROMP_TESTS_LEAK_EXIT_BOUND_S"


def _leak_exit_bound():
    """LEAK_EXIT_BOUND_S, unless ROMP_TESTS_LEAK_EXIT_BOUND_S holds a finite number of seconds that is not negative. Only
    tests/test_run_end_leaked_processes.py's child runs set it: their holders never exit, so each run would otherwise
    wait the whole bound. Anything else there is the default."""
    try:
        v = float(os.environ.get(LEAK_EXIT_BOUND_ENV, ""))
    except ValueError:
        return LEAK_EXIT_BOUND_S
    return v if math.isfinite(v) and v >= 0 else LEAK_EXIT_BOUND_S


def _run_roots(root=None, depth=3):
    """This run's temp roots: `root` (the controller's by default) and every root listed in `<root>/romp-tests-children`,
    which since 2026-09-24 names every nested root of the run at any depth (tests/__init__.py, the lineage). A listed
    root's own list is read too, recursively to `depth`, while it stands: that reaches a nested process whose parent's
    marker carried no lineage. A line that is not a record is passed over."""
    root = root or _TMP_ROOT
    roots = [root]
    try:
        with open(os.path.join(root, _tests.TEST_ROOT_CHILDREN), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return roots
    for line in lines:
        try:
            child = json.loads(line)["root"]
        except (ValueError, KeyError, TypeError):
            continue
        if depth > 0 and isinstance(child, str) and child not in roots:
            roots += [r for r in _run_roots(child, depth - 1) if r not in roots]
    return roots


_DELETED = " (deleted)"


def _spellings(roots):
    """Each root by its spelling folded (_lexical; a trailing separator dropped) and by its realpath, as one set. The
    folded spelling stands in for the raw one, which is the same string unless it has a doubled separator or a '.' or
    '..' segment, and then matches nothing: every path compared with the set is folded (an environment value, an
    argument) or read from /proc, which spells a cwd and a descriptor's target without either."""
    out = set()
    for r in roots:
        if r:
            r = r.rstrip(os.sep) or os.sep
            out.add(_lexical(r))
            out.add(os.path.realpath(r))
    return out


def _lexical(path):
    """`path` with a doubled separator, a '.' segment and a '..' segment folded as os.path.normpath folds them, and a
    leading '//' read as '/' (normpath keeps two leading separators; Linux gives them no other meaning). Lexical: a '..'
    after a symlink is folded as if the symlink were a directory. A path with no '//' and no '.' or '..' segment is
    returned as is (a hidden directory's '/.' is no segment, and most values carry one)."""
    if not ("//" in path or "/./" in path or "/../" in path or path.endswith(("/.", "/.."))):
        return path
    path = os.path.normpath(path)
    return "/" + path.lstrip("/") if path.startswith("//") else path


def _under(path, roots):
    """Whether `path` is one of `roots` (a set of spellings) or a path under one: the path or an ancestor of it is a root,
    so a sibling that shares a root's name as a prefix is not."""
    while path:
        if path in roots:
            return True
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent
    return False


def _link(path):
    """A /proc link's target without the " (deleted)" the kernel appends once the target is removed; "" when unreadable."""
    try:
        target = os.readlink(path)
    except OSError:
        return ""
    return target[:-len(_DELETED)] if target.endswith(_DELETED) else target


def _proc_stat(pid):
    """(state, ppid, start time in clock ticks since boot) from /proc/<pid>/stat. The comm field is in parentheses and may
    hold spaces or a ')', so the fields are counted from the LAST ')'. Raises OSError, ValueError or IndexError."""
    with open("/proc/%d/stat" % pid, "rb") as fh:
        stat = fh.read()
    tail = stat[stat.rindex(b")") + 1:].split()
    return tail[0].decode("ascii", "replace"), int(tail[1]), int(tail[19])


def _proc_read(pid, name):
    try:
        with open("/proc/%d/%s" % (pid, name), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _proc_argv(pid):
    return [a.decode("utf-8", "replace") for a in (_proc_read(pid, "cmdline") or b"").split(b"\0") if a]


def _names_path(part, cwd, roots, names):
    """Whether `part`, an environment value's or an argument's ':'-joined component, names a path under a root. An
    absolute one is read folded (_lexical). A relative one is read as the path it names from `cwd`, the process's cwd as
    /proc reads it (joined to it, then folded), and only when it carries one of `names`, the last component of each
    spelling of a root: from a cwd outside every root a relative path reaches under one only by naming that root's own
    directory (a '..' step from outside a root stays outside it, and a named step enters one only as the root itself),
    and a process whose cwd is under a root holds it through its cwd. An unreadable cwd ("") leaves the part relative,
    and a relative path is under no root."""
    if part.startswith(os.sep):
        return _under(_lexical(part), roots)
    if not any(n in part for n in names):
        return False
    return _under(_lexical(os.path.join(cwd, part)), roots)


def _argv_holds(argv, roots, cwd, names):
    """Whether an argument, the part after an argument's first '=', or a ':'-joined component of either names a path
    under a root (_names_path: an absolute one read folded, a relative one from the process's cwd)."""
    for arg in argv:
        for part in (arg, arg.partition("=")[2]):
            if part and any(_names_path(c, cwd, roots, names) for c in part.split(os.pathsep)):
                return True
    return False


def _fds_hold(pid, roots):
    """Whether one of the process's open file descriptors points under a root (/proc/<pid>/fd, the kernel's resolved
    targets; a socket or a pipe reads socket:[inode] or pipe:[inode] and is under nothing)."""
    try:
        fds = os.listdir("/proc/%d/fd" % pid)
    except OSError:
        return False
    return any(_under(_link("/proc/%d/fd/%s" % (pid, fd)), roots) for fd in fds)


def _processes_holding(roots, skip_pids=(), pids=None):
    """(holders, unjudged, procfs read): every live process (not this one, not a zombie, not in `skip_pids`) whose
    environment carries a value that is one of `roots` or a path under one (a ':'-joined value counted per component),
    whose cwd is under one, one of whose open file descriptors points under one, or one of whose arguments is under one
    (_argv_holds); each root by its folded spelling and its realpath (_spellings), each environment value and argument
    read folded (_lexical: a doubled separator and a '.' or '..' segment), a relative one from the process's cwd when it
    carries a root's directory name (_names_path). Each holder is a dict: pid, ppid, cmd, via (the environment names,
    then "cwd", "fd", "argv"), cwd, test (the PYTEST_CURRENT_TEST in its environment, the test phase current at its
    spawn, or "" when it carries none). The environment read is the one the process was STARTED
    with (/proc shows the initial block, not later putenv calls), which is what a child inherits.
    `unjudged` holds the processes whose environment could not be read, which are judged by nothing: "listed", this
    user's (the owner of /proc/<pid>, readable when the environment is not) that started after this process (the stat
    start time) and share its cgroup, each a dict of pid, ppid and cmd; "other", the count of the rest, another user's
    and this user's started before this process or in another cgroup. The third value is False where there is no
    procfs to read. `pids` stands in for the listing of /proc (tests/test_run_end_leaked_processes.py scans its own
    children alone, since the count of the rest moves with the box)."""
    spell = _spellings(roots)
    names = {os.path.basename(s) for s in spell}
    me = os.getpid()
    holders, listed, other = [], [], 0
    try:
        listing = [int(d) for d in os.listdir("/proc") if d.isdigit()]
    except OSError:
        return holders, {"listed": listed, "other": other}, False
    try:
        my_start = _proc_stat(me)[2]
    except (OSError, ValueError, IndexError):
        my_start = None
    my_cgroup, my_uid = _proc_read(me, "cgroup"), os.getuid()
    for pid in (listing if pids is None else pids):
        if pid == me or pid in skip_pids:
            continue
        try:
            state, ppid, start = _proc_stat(pid)
        except (OSError, ValueError, IndexError):
            continue                        # gone between the listing and the read
        if state == "Z":
            continue                        # exited, not yet reaped: holds nothing
        try:
            with open("/proc/%d/environ" % pid, "rb") as fh:
                raw = fh.read()
        except PermissionError:
            try:
                uid = os.stat("/proc/%d" % pid).st_uid
            except OSError:
                continue
            if (uid == my_uid and my_start is not None and start > my_start and my_cgroup is not None
                    and _proc_read(pid, "cgroup") == my_cgroup):
                listed.append({"pid": pid, "ppid": ppid, "cmd": " ".join(_proc_argv(pid))})
            else:
                other += 1
            continue
        except OSError:
            continue
        env = {}
        for item in raw.split(b"\0"):
            k, sep, v = item.partition(b"=")
            if sep:
                env[k.decode("utf-8", "replace")] = v.decode("utf-8", "replace")
        cwd = _link("/proc/%d/cwd" % pid)
        via = sorted(k for k, v in env.items()
                     if any(_names_path(part, cwd, spell, names) for part in v.split(os.pathsep)))
        if _under(cwd, spell):
            via.append("cwd")
        if _fds_hold(pid, spell):
            via.append("fd")
        argv = _proc_argv(pid)
        if _argv_holds(argv, spell, cwd, names):
            via.append("argv")
        if not via:
            continue
        holders.append({"pid": pid, "ppid": ppid, "cmd": " ".join(argv), "via": via, "cwd": cwd,
                        "test": env.get("PYTEST_CURRENT_TEST", "")})
    return holders, {"listed": listed, "other": other}, True


def _pid_present(pid):
    try:
        with open("/proc/%d/stat" % pid, "rb") as fh:
            stat = fh.read()
        return stat[stat.rindex(b")") + 1:].split()[0] != b"Z"
    except (OSError, ValueError, IndexError):
        return False


def _leaked_run_processes(roots, bound_s=LEAK_EXIT_BOUND_S, pids=None):
    """(holders still present, unjudged, procfs read): the processes holding `roots` after every holder seen first, and
    every process first listed as not judged, has been given until `bound_s` to exit (the event waited for is the pid's
    exit; the wait ends the moment the last one is gone). Nothing waits when nothing holds and nothing is listed.
    `pids` is _processes_holding's stand-in listing, handed to both scans (tests/test_run_end_leaked_processes.py times
    the wait over its own children alone: a process another test lists would be waited for too)."""
    holders, unjudged, ok = _processes_holding(roots, pids=pids)
    if not ok or not (holders or unjudged["listed"]):
        return holders, unjudged, ok
    deadline = time.monotonic() + bound_s
    pending = {h["pid"] for h in holders + unjudged["listed"]}
    while pending and time.monotonic() < deadline:
        pending = {pid for pid in pending if _pid_present(pid)}
        if pending:
            time.sleep(0.05)
    return _processes_holding(roots, pids=pids)


def _join_live_threads(bound_s, among=None):
    """Join this process's live non-daemon threads, other than the main one and the caller, until `bound_s` has passed
    (a thread one of them starts meanwhile is joined too), never waiting on a daemon thread. Returns every such thread
    still alive afterwards, daemon or not: a process one of them starts after the scan that follows is not seen.
    `among` stands in for threading.enumerate() (tests/test_run_end_leaked_processes.py hands in stand-in threads)."""
    pool = threading.enumerate if among is None else (lambda: list(among))
    skip = (threading.current_thread(), threading.main_thread())
    deadline = time.monotonic() + bound_s
    while True:
        pending = [t for t in pool() if t not in skip and not t.daemon and t.is_alive()]
        left = deadline - time.monotonic()
        if not pending or left <= 0:
            break
        pending[0].join(left)
    return [t for t in pool() if t not in skip and t.is_alive()]


def _say_at_run_end(session, text):
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if tr is not None:
        tr.ensure_newline()
        for line in text.splitlines():
            tr.write_line(line)
    else:
        print(text, file=sys.stderr)


PHASE_UNKNOWN = ("the phase at its spawn is unknown, since PYTEST_CURRENT_TEST is not in its environment, because it was "
                 "spawned while no phase was set (between phases or outside a test, as a background thread's late child "
                 "can be) or was given an environment built without it (by the test or by an ancestor process)")


def _report_leaked_run_processes(session):
    """The controller's run-end check (the comment above LEAK_EXIT_BOUND_S): join the live non-daemon threads, then name
    every process of the run that still holds one of its roots and make the run red; list this user's unreadable
    processes of the run as not judged, count the other unreadable ones, and name the threads still running."""
    bound = _leak_exit_bound()
    left = _join_live_threads(bound)
    leaked, unjudged, ok = _leaked_run_processes(_run_roots(), bound)
    if not ok:
        _say_at_run_end(session, "[tests] the run-end process check reads /proc and did not run on this platform")
        return
    lines = []
    if leaked:
        lines.append("[tests] %d process(es) of this run still hold its temp root at run end, %g s after the run finished "
                     "waiting for them to exit: a test started them and did not stop them; the run is red." % (len(leaked), bound))
        for h in leaked:
            lines.append("[tests]   pid %d (parent %d): %s | holds the root through %s | %s" % (
                h["pid"], h["ppid"], h["cmd"][:240] or "(no command line)", ", ".join(h["via"]),
                "spawned during %s" % h["test"] if h["test"] else PHASE_UNKNOWN))
    if unjudged["listed"]:
        lines.append("[tests] %d process(es) of this user started during this run, in its cgroup, could not be read and were "
                     "not judged: their environment, cwd and open files are unreadable (a process that made itself "
                     "non-dumpable, or one running a setuid program); they do not change the exit status." % len(unjudged["listed"]))
        for u in unjudged["listed"]:
            lines.append("[tests]   pid %d (parent %d): %s | not judged" % (u["pid"], u["ppid"], u["cmd"][:240] or "(no command line)"))
    if lines:
        lines.append("[tests] %d other process(es) could not be read and were not judged: another user's, or this user's "
                     "started before this run or in another cgroup." % unjudged["other"])
    if left:
        names = ["%s%s" % (t.name, " (daemon)" if t.daemon else "") for t in left]
        lines.append("[tests] %d thread(s) of this process were still running when the run-end check read /proc: %s. A process "
                     "one of them starts after that read is not seen (the check waited up to %g s for the non-daemon ones "
                     "and never waits for a daemon thread)." % (len(left), ", ".join(names[:12]) + (
                         ", and %d more" % (len(names) - 12) if len(names) > 12 else ""), bound))
    if lines:
        _say_at_run_end(session, "\n".join(lines))
    if leaked:
        session.exitstatus = max(int(session.exitstatus or 0), 1)


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """The in-process half (tests/__init__.py): remove every directory this process made through
    tempfile.mkdtemp inside the root, this module's state root included, when the session ends. Runs
    in the controller and in every xdist worker, since each is its own pytest session, and last, after
    pytest's own runner sessionfinish has performed the deferred teardown an interrupted run leaves
    behind, so nothing is swept from under a fixture still closing. The package's atexit hook does the
    same at interpreter exit; both are idempotent, and pytest_unconfigure below takes the root itself
    afterwards. Then, in the controller alone (a worker's roots are among the controller's), the run-end
    process check above: a process of the run that still holds one of its roots makes the run red."""
    try:
        from tests import remove_made_dirs
    except Exception:
        return
    remove_made_dirs()
    if not hasattr(session.config, "workerinput"):
        _report_leaked_run_processes(session)


def pytest_unconfigure(config):
    _remove_run_dirs(report=True)


def pytest_configure(config):
    """One warning filter, registered here so every run and every xdist worker carries it (2026-09-16):
    claude_agent_sdk.types.CanUseToolShadowedWarning, a UserWarning subclass the SDK emits when a client is
    built with can_use_tool set beside a permission mode or an allowed_tools entry that auto-approves a tool
    before the callback is consulted. tests/test_host_transport.py and tests/test_session_host.py put romp's
    SDK venv on sys.path and drive that path; under pytest-xdist the worker ships the warning to the
    controller, whose venv has no claude_agent_sdk, and xdist's unserialize_warning_message imports the
    warning's module to rebuild it: ModuleNotFoundError, the node goes down, the run ends in INTERNALERROR
    (before this every -n run needed -p no:warnings). Matched on the MESSAGE PREFIX with the base category,
    never on the class: pytest parses each filterwarnings entry every time it applies them (configure,
    collection, each test), and an entry naming a class it cannot import is dropped with a
    PytestConfigWarning, which is every worker until the emitting module inserts the venv path, the
    controller always and CI always. A module-level warnings.filterwarnings in the emitting module does not
    hold either: pytest wraps collection and each test in catch_warnings, which restores the filter list on
    exit. addinivalue_line appends to the ini list, so an ini file added later merges with this line. Both
    of the SDK's message forms ("...: permission_mode ..." and "... for: <tools>") start with the prefix."""
    config.addinivalue_line("filterwarnings", "ignore:can_use_tool will not be invoked:UserWarning")


# No test's git reads the developer's configuration (2026-09-06). Fixture repos are built by `git
# init` + `git commit` in temp dirs, and those commands honoured the developer's global config: a
# global core.hooksPath ran their pre-commit hook on every seed commit, an LFS filter would run on
# every checkout, and a credential helper or insteadOf rewrite could reach a real remote
# (tests/test_file_github.py pins its own environment for exactly that reason). CI has no global git
# config, so a test that leans on one is already broken there; this makes every run match.
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
# the postal bus port likewise (2026-09-11): a machine whose bus runs on a named port hands ROMP_POSTAL_PORT to every
# session's shell, and a test run from one would carry the machine's name into every lab and in-process kernel; the
# bus refuses its fixed port under a test unless the port is the run's own, which the marker beside a port says
os.environ.pop("ROMP_POSTAL_PORT", None)
# the rest of the postal trio and the three call-time seams likewise (2026-09-23, the verifier's finding on round 2 of
# fork PR #894): a session's shell can carry any of them, and _module_env_restored and _shared_state_restored (below)
# compare each watched name with the value the module or the test found. The postal modules put peers and client-only
# back with a pop in their tearDowns rather than a restore, so from a shell carrying ROMP_POSTAL_PEERS or
# ROMP_POSTAL_CLIENT_ONLY a run ended those modules with the name unset and went red where a clean shell's run was
# green.
# Popped here with the seams, every run starts every watched name unset, as CI's does, and both checks read the same run
# whatever the shell carries (every name of MODULE_WATCHED_ENV_NAMES is popped by these lines or the port's above; the
# hermetic module holds each watched name among this file's import-time pops and runs both checks from a shell carrying
# every one). They come before the hermetic marker below, so upstream's floor of client-only "1" (their PR 1848, which
# fork PR #875 folds), placed right after the marker, still sets it for the run (the hermetic module's import probe
# under that floor reds when a pop follows the marker).
os.environ.pop("ROMP_POSTAL_PEERS", None)
os.environ.pop("ROMP_POSTAL_CLIENT_ONLY", None)
os.environ.pop("ROMP_POSTAL_HOST", None)
os.environ.pop("ROMP_SESSIONS_FILE", None)
os.environ.pop("ROMP_SERVE_TOKEN", None)
os.environ["ROMP_POSTAL_HERMETIC"] = "1"
os.environ["ROMP_CKPT_FIRST_DOC_KB"] = "0"   # the young-session floor is off for the suite's small fixtures (a document under 1 MB of
#                                                pre-cut bytes is never written live); the floor's own test sets it. A plain assignment: an
#                                                exported value in the shell (64, say) would red every checkpoint fixture (1721 round two);
#                                                tests/__init__.py carries the same line for the unittest runner
# No test spawns a per-session HOST by omission (2026-09-11, T348): hosts are on by default now, so a backend built over
# a state dir with no `session-hosts` file starts a real bin/romp-session-host for any session it connects. The root the
# runner floors carries the toggle set to off from the start, re-asserted per test below (a test that deletes or rewrites
# it gets it back); the deliberate hosts-on tests write `on` into their OWN state roots and are unaffected.
# THE BELT'S REACH: it covers this one root and nothing else. A test that mints its own temp state root (a bare
# tempfile.mkdtemp() handed to SdkBackend, a lab kernel's xdg root) stands outside it and MUST write `off` into
# `<its root>/session-hosts` itself unless it means to run a host, or the first connect it drives spawns a real
# bin/romp-session-host on the developer's box (tests/test_cut_turn_tree_kill.py did, 2026-09-11). The rule for test
# authors is in CLAUDE.md under Testing.
_SESSION_HOSTS_OFF = os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts")


def _floor_session_hosts_off():
    try:
        os.makedirs(os.path.dirname(_SESSION_HOSTS_OFF), exist_ok=True)
        if not os.path.exists(_SESSION_HOSTS_OFF) or open(_SESSION_HOSTS_OFF).read().strip().lower() != "off":
            with open(_SESSION_HOSTS_OFF, "w") as f:
                f.write("off\n")
    except OSError:
        pass


_floor_session_hosts_off()

# No test may resolve the REAL ~/.claude (2026-09-08): the judge module and the event model compute
# their projects root at IMPORT from CLAUDE_CONFIG_DIR (default ~/.claude), the kernel and the SDK
# backend read the same variable at call time for the task store and transcripts, and a test that
# touched a per-session project dir without patching jd.PROJECTS wrote thirty synthetic-sid
# directories under a developer's real ~/.claude/projects. Floored like the state root: a fresh
# directory inside the run's private temp root, set (not defaulted: a developer's own export must
# not reach a test either) before any test module loads, and re-asserted per test below so a
# module-level pop or write in one test file cannot erase it for the run. A test that needs its own
# Claude root sets the variable in setUp, after the fixture, exactly as the ones that do already do.
# The location the run was handed is saved FIRST, before the floor replaces it: the one opt-in live
# test that borrows the operator's apiKeyHelper command from their own settings
# (tests/test_session_move_live.py) reads it through ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR. Captured
# after the floor it would name the run's empty temp dir, and that test would skip as "no auth"
# while its skip message still named the borrow. setdefault, so an xdist worker keeps the
# controller's value rather than re-reading an environment the controller has already floored.
os.environ.setdefault("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
                      os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))
_CLAUDE_CONFIG = tempfile.mkdtemp(prefix="romp-tests-claude-")
os.environ["CLAUDE_CONFIG_DIR"] = _CLAUDE_CONFIG


# No test may reach a REAL manager control port (2026-08-27): on a machine running a live romp,
# every shell the manager tree spawns inherits ROMP_MANAGER_PORT, and any test kernel that dials
# "the manager" through the inherited value restarts the ACTUAL deployment — the serve-layer
# restart test's pop-then-restore raced the /restart handler's post-ack env read and took a
# self-hosted instance down mid-suite, repeatedly. POISONED to a dead port, never popped. Every
# consumer in kernel/ treats an absent or empty variable as "no manager" since 2026-09-10
# (_manager_port: _manager_kernels, _run_main_update, _restart_this_kernel and _run_update; before that
# _run_main_update, and for one review round the banner's registry read, mapped absent to the DEFAULT
# port, the live one, and a probe run with the variable absent restarted every session on a development
# box through the drift door); bin/romp-manager still falls back to 7432 on absent or empty (its status,
# down, restart-all and ensure verbs, which `romp down` and the remote update script dial through), and
# vscode-extension/src/extension.ts defaults to 7432 too, one more reason the floor stays: a dead value
# is the one state safe against every consumer, present and future. Import-time, so collection-time code
# is floored too.
os.environ["ROMP_MANAGER_PORT"] = "1"
# The kernel's port, both spellings, for the same reason: kernel/kernel.py resolves PORT from
# ROMP_KERNEL_PORT at import and postal/postal_service.py builds KERNEL_BASE from it at import, bin/romp
# reads it in every kernel subcommand and hooks/romp-wake.sh at every wake, and bin/romp-manager reads
# ROMP_SERVE_PORT first; each maps an absent variable to the DEFAULT port, the live kernel's, so a test
# that dials "the kernel" through an inherited or absent value reaches the developer's own. A test that
# starts a kernel of its own passes the port it picked, as the ones that do already do.
os.environ["ROMP_KERNEL_PORT"] = "1"
os.environ["ROMP_SERVE_PORT"] = "1"

# No test may read the REAL service.env (2026-09-04; the reason changed on 2026-09-08): the kernel's boot
# check (kernel/credentials.py) reads the manager env file for retired provider lines, so on a machine whose
# file still carries one every kernel-loading test would refuse to start. Pointed at a path inside the temp
# state root that is never created, so every read is the "no file" case. Both spellings, because the
# path resolver accepts both. Import-time (collection is floored too) plus a per-test re-assert below, on
# the same reasoning as the manager port.
_NO_SERVICE_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_SERVICE_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_SERVICE_ENV
# No test starts with a CREDENTIAL the developer's shell configured (2026-09-08). Every session shell under
# a romp-managed manager inherits the manager's environment: the retired provider names (which the boot
# check now refuses outright), ROMP_EXPECTED_AUTH (the box-wide auth declaration), the login tokens
# sdk_backend.startup_auth_env claims, and the 1Password CLI's own names. A test that constructs a backend
# or asks default_auth would otherwise read the DEVELOPER'S configuration: 73 tests across eight modules
# went red on a box running a key command while CI, which exports none of these, stayed green (the
# manager's full run, 2026-09-08). Popped at import so module-level loads see the clean baseline, and
# re-asserted per test below; a test that wants a credential sets a synthetic one itself in setUp, which
# runs after the fixture. The list is the code's own (tests/test_key_source_floor.py pins it against
# credentials.FLOOR_ENV_NAMES / FLOOR_ENV_PREFIXES and sdk_backend.AUTH_ENV_NAMES).
KEY_SOURCE_ENV_NAMES = (
    "ROMP_API_KEY_CMD", "ROMP_API_KEY_REF", "ANTHROPIC_API_KEY",          # credentials.RETIRED_VARS
    "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",                     # credentials.LOGIN_TOKEN_VARS
    "ROMP_EXPECTED_AUTH",                                                  # the auth declaration
    "OP_SERVICE_ACCOUNT_TOKEN", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN", "OP_ACCOUNT",   # credentials.OP_ENV_NAMES
)
KEY_SOURCE_ENV_PREFIXES = ("OP_SESSION_",)                                # credentials.OP_ENV_PREFIX


def _scrub_key_source_env():
    for name in KEY_SOURCE_ENV_NAMES:
        os.environ.pop(name, None)
    for name in [k for k in os.environ if k.startswith(KEY_SOURCE_ENV_PREFIXES)]:
        os.environ.pop(name, None)


_scrub_key_source_env()
# Every shell under a romp-managed session inherits ROMP_SUPERVISED=1 from the kernel (the service
# unit exports it). The variable used to give the retired key-source module authority over a startup key;
# it is still popped so a test's world is the unsupervised baseline (review find, 2026-09-05), and a test
# that wants supervision sets the variable itself.
os.environ.pop("ROMP_SUPERVISED", None)


# No test may read the box's REAL managed settings (2026-09-08): credentials.py reads
# /etc/claude-code/managed-settings.json (or the macOS path) as the top of Claude Code's precedence, so a
# test asserting "no helper" would lie on a box whose administrator set one there. Every loaded copy of the
# module is pointed at a path inside the temp state root that is never created; a test that wants a managed
# file stubs managed_settings_path itself in setUp, after this fixture.
_NO_MANAGED_SETTINGS = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-managed-settings.json")


def _reset_credential_state():
    """credentials.py memoizes the helper's value in process memory for its TTL; under one pytest process
    that memo would leak between test modules. Every loaded copy of the module is reset, and its managed
    settings path floored (above)."""
    import sys
    for name, m in list(sys.modules.items()):
        if "credentials" in name and hasattr(m, "forget_helper_key"):
            m.forget_helper_key()
            m.managed_settings_path = lambda: _NO_MANAGED_SETTINGS


@pytest.fixture(autouse=True)
def _no_real_service_env():
    """Re-asserted, not defaulted: a module-level write in one test file executes during collection
    and would otherwise hold for the whole run. A test that needs its own env file points the vars at
    a temp path in setUp, which runs AFTER this fixture (pytest fills fixtures in the item's setup
    phase, before TestCase.run calls setUp) — so per-test intent still wins."""
    for var in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV"):
        os.environ[var] = _NO_SERVICE_ENV
    _scrub_key_source_env()
    os.environ.pop("ROMP_SUPERVISED", None)
    _reset_credential_state()
    yield


@pytest.fixture(autouse=True)
def _no_real_claude_config():
    os.environ["CLAUDE_CONFIG_DIR"] = _CLAUDE_CONFIG
    yield


@pytest.fixture(autouse=True)
def _hosts_off_in_the_floored_root():
    """The floored state root reads hosts OFF before every test (T348): the file is re-written when a test removed or
    changed it, so no later test spawns a real host by omission."""
    _floor_session_hosts_off()
    yield


@pytest.fixture(autouse=True)
def _dead_manager_port():
    """The import-time poison above covers collection, but a module-level env write in a test file
    ALSO executes during collection — so one module's write (or pop) would otherwise hold for the
    entire run phase, erasing the floor for every test after it. Re-assert per test: no
    module-level write can outlive collection against this. The kernel's port, both spellings, is
    re-asserted the same way; a test that needs a port of its own sets it in setUp or passes it
    to the process it starts. The postal bus port is re-asserted UNSET the same way (2026-09-22): the
    import-time pop above held only until a module wrote the port at collection, and with the run's
    marker beside it that name licensed a stray revive's child to bind a real bus from inside another
    module's test (fork PR #813's CI); a test that wants a bus port of its own sets it in setUp, after
    this, beside the kernel's BUS_PORT if it loaded the kernel in-process (tests/test_kernel_tunnels.py)."""
    os.environ["ROMP_MANAGER_PORT"] = "1"
    os.environ["ROMP_KERNEL_PORT"] = "1"
    os.environ["ROMP_SERVE_PORT"] = "1"
    os.environ.pop("ROMP_POSTAL_PORT", None)
    yield


# No in-process kernel of the run dials the machine's fixed bus port (2026-09-23, the reviewer's ruling of round 1 on fork
# PR #894). A kernel a test module loads IN-PROCESS (load_source of bin/romp-kernel under a name that starts romp_kernel)
# reads its BUS_PORT from ROMP_POSTAL_PORT at import, and the fixture above pops that name before every test (this file
# pops it at import too), so every such kernel of a whole run read 25302, the machine's fixed bus port: a spy over one full
# serial run recorded the tests whose kernel's bus calls (a peer notify at a detach or a trust change, the GET /peers
# behind the routes that list remotes) dialled it, which on a box whose own bus listens there reach that bus; where
# nothing listens, as on CI, a refused notify kicked the revive into a real romp-postal-service ensure. A dead port cannot
# be EXPORTED instead: the bus's fixed-port refusal licenses a port equal to the child's import-time ROMP_POSTAL_PORT
# beside ROMP_POSTAL_HERMETIC, which this file sets, so an exported port would license a revive's child to bind a real bus
# on it. So every loaded kernel module's BUS_PORT is set to DEAD_BUS_PORT before each test and put back after it. A refused
# call then kicks the revive on every box, not only where nothing listens, so the tests whose notify is refused stub the
# revive themselves (_revive_postal_bus, put back by a cleanup); the peer-notify guard test in tests/test_kernel.py and the
# tunnels module's _PostalTrio exercise the revive road and keep their own handling (the guard waits the revive out under
# a scoped fake of subprocess.run; the trio patches BUS_PORT to a port of the test's own and stubs _ensure_postal_bus).
# The same spy found the postal service loaded in-process (load_source of bin/romp-postal-service under a name that starts
# romp_postal) dialling the fixed port too, through its client's BASE, which it builds from the same popped name at
# import: tests/test_postal_relay_honesty.py's three set_working tests, whose tool call beats the bus first. So every
# loaded postal module's BASE points at DEAD_BUS_PORT for each test as well, put back after it; a postal module that
# serves binds PORT, which this leaves alone.
# What this does not reach, each for its reason: a kernel or postal module loaded under another module name (the fixture
# finds the modules by name); one a test loads or re-loads during the test (setUp or the body run after this fixture, and
# a load_source re-executes the module and reads the port again); and a bus call made outside the window this fixture
# holds the dead port for, which opens at its setup, inside the test's own setup, and closes at its teardown. Outside
# that window a loaded module has its import-time port, 25302, back: setUpModule, setUpClass, a module- or class-scoped
# fixture, tearDownClass and tearDownModule run before this per-test fixture is set up or after it is torn down, and a
# thread that outlives its test reads the port put back at the teardown (the verifier's finding on round 2 of fork PR
# #894; tests/test_hermetic_kernel_postal.py's test_the_dead_bus_port_holds_for_each_test_and_comes_back_after_it reads
# the port in a probe module's setUpModule, module-scoped fixture, setUpClass, tearDownClass and tearDownModule and in a
# thread after its test, and each reads the import-time port). The pin (the same module, the affected modules run with
# a connect and spawn spy in both orders) and the spy's full serial run, which records a connect from any phase and from
# any thread, are what show that none of those dials the fixed port today.
DEAD_BUS_PORT = 1


def _loaded_kernels():
    """The kernel modules this process has loaded in-process: every module whose name starts romp_kernel and that has a
    BUS_PORT, the port its bus calls dial."""
    return [m for name, m in list(sys.modules.items()) if name.startswith("romp_kernel") and hasattr(m, "BUS_PORT")]


def _loaded_postal_clients():
    """The postal service modules this process has loaded in-process: every module whose name starts romp_postal and
    that has the client's BASE (the bus URL its _http dials) and the HOST it is built from."""
    return [m for name, m in list(sys.modules.items()) if name.startswith("romp_postal") and hasattr(m, "BASE") and hasattr(m, "HOST")]


@pytest.fixture(autouse=True)
def _dead_bus_port():
    saved = [(m, m.BUS_PORT) for m in _loaded_kernels()]
    saved_base = [(m, m.BASE) for m in _loaded_postal_clients()]
    for m, _port in saved:
        m.BUS_PORT = DEAD_BUS_PORT
    for m, _base in saved_base:
        m.BASE = "http://%s:%d" % (m.HOST, DEAD_BUS_PORT)
    yield
    for m, port in saved:
        m.BUS_PORT = port
    for m, base in saved_base:
        m.BASE = base


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
# api.anthropic.com on the credential the kernel resolves: the apiKeyHelper Claude Code's settings
# name (kernel/credentials.py helper_key, run in-process), else a claimed ANTHROPIC_AUTH_TOKEN
# bearer. A DEFENSIVE floor: no test reached the network before this line (checked, not assumed —
# the one in-process _sdk() driver, test_kernel_headless_ops' SdkSingleFlight, runs the refresh
# inside the test process with the module loader mocked, and it stopped only because the mocked
# module handed http.client a credential it rejects before a socket opens), but any
# in-process _sdk() call is one exported key away from a real request no test asserts on, on a key
# the test never chose. The kernel-SPAWNING tests floor it in their subprocess env
# (test_gear_select_matrix_served, test_ship_reship_served, test_awaiting_box_sync_served); this floors every test,
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
                         "ROMP_CLI_SCOPE_OOM_SCORE_ADJ",
                         # the kernel's marker for a systemd that refuses OOMPolicy= on a scope: sent to every
                         # session's CLI ("1" or ""), so a tool shell inherits it like the limits
                         "ROMP_CLI_SCOPE_OOM_POLICY_REJECTED")
for _v in _CLI_SCOPE_LIMIT_VARS:
    os.environ.pop(_v, None)


@pytest.fixture(autouse=True)
def _no_cli_scope():
    os.environ["ROMP_CLI_SCOPE"] = "0"
    for v in _CLI_SCOPE_LIMIT_VARS:
        os.environ.pop(v, None)
    # The CLI-binary floor above, re-asserted per test for the same reason as the scope's: a test module's module-level
    # write executes at COLLECTION and would hold for every test after it. tests/test_login_flow.py once set its mock CLI
    # that way, so every lab kernel of a whole run (kernel_env passes ROMP_CLAUDE_BIN through) ran its judges against a
    # login mock, which answered the planner with junk; the coerce floor minted goals, the auto-nudge fired into sessions
    # no CLI could run, and the nudge walk read those parked nudges as the user's queued input for the rest of both
    # boots (tests/test_fold_checkpoints_served.py, one red only under a whole suite, 2026-09-16). A module that needs
    # its own binary sets it in setUp and restores it in tearDown (tests/test_kernel_env_floor.py pins both halves).
    os.environ["ROMP_CLAUDE_BIN"] = "/bin/false"
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


# No test may leave the shared judge or a call-time environment seam changed (2026-09-09). kernel.py
# loads the judge as load_source("romp_judge", ...) (kernel/loadsource.py), which re-executes
# into the module object already in sys.modules under that name, so every kernel-loading test
# module's km.jd is ONE process-wide object. A test that rebinds jd.STATE to a temp dir and removes
# that dir in tearDown without restoring the prior value leaves every later STATE reader in the
# process pointing at a removed directory: a FileNotFoundError on restart-audit.jsonl or
# timeline-views.json, or a silent empty read where the writer swallows OSError. The postal seams
# have the same shape: postal_service reads the sessions-file seam (ROMP_SESSIONS_FILE) and the
# bus-name seam (ROMP_POSTAL_HOST, the machine name the bus answers as) from os.environ at call time,
# so a test that leaves either changed hands its value to every later test in the process and every
# child they spawn: a sessions file with one live row kept a leaked bus from ever autostopping, and a
# test's TESTHOST reached a later test's probe subprocess (the reviewer's finding on fork PR #894,
# round 1). No module writes either at import (the census in tests/test_hermetic_kernel_postal.py
# forbids it), so this fixture names such a leftover in any run, whenever the value a test leaves
# differs from the one it found (a leftover equal to what an earlier test had already set is no change
# here, and the developer's shell never sets one: this file pops each at import); the postal modules
# set both per test and put them back by cleanups, and tests/test_postal_self_host.py's
# _HostnameSeams pops and restores the bus name, so each is quiet here. Neither shows when the victim runs
# alone, and the serial order of the whole suite passes only because a test that loads a kernel
# between the cause and the victim re-executes judge.py and rebinds the roots; any other order (a
# subset, another scheduler) fails a module that did nothing wrong. This fixture names the cause
# instead: it snapshots the shared judge's STATE and PROJECTS and the watched environment names
# before each test and fails the test that changed one and did not restore it, or left a path that
# was a directory pointing at nothing. Transition-based on purpose: a module-level preamble runs at
# collection, before any snapshot, and is not seen; a test that changes and restores is quiet; and a
# test that merely runs under another test's leftover is not blamed for it. A test that loads a
# kernel (or the judge itself) re-executes judge.py into the shared module, which rebinds every root
# from the environment as it stands at that moment: that is the loader's reset, made from values
# other modules' import-time writes decide, not a directory the test made and removed, so the path
# check compares no values for that test (the re-execution recreates every function object, which is
# how it is told apart from an assignment). Only the values: judge.py creates STATE at import, so a
# STATE that is not a directory after a reload is the test's own doing and is still named, and the
# environment names are still checked. Values of the environment names are never printed (one of
# them is a credential), only the kind of change.
_SHARED_JUDGE_PATHS = ("STATE", "PROJECTS")
_SEAM_ENV_NAMES = ("ROMP_SESSIONS_FILE", "ROMP_SERVE_TOKEN", "ROMP_POSTAL_HOST")


def _shared_judge_paths():
    """({name: (path text or None, is a directory)}, marker) for the shared judge's watched globals,
    the marker being a function object judge.py defines (a re-execution replaces it); ({}, None) when
    no module has loaded the judge under its shared name yet."""
    jd = sys.modules.get("romp_judge")
    if jd is None:
        return {}, None
    out = {}
    for name in _SHARED_JUDGE_PATHS:
        p = getattr(jd, name, None)
        text = None if p is None else str(p)
        out[name] = (text, text is not None and os.path.isdir(text))
    return out, vars(jd).get("_rebind_state")


@pytest.fixture(autouse=True)
def _shared_state_restored(request):
    paths_before, marker_before = _shared_judge_paths()
    env_before = {name: os.environ.get(name) for name in _SEAM_ENV_NAMES}
    yield
    paths_after, marker_after = _shared_judge_paths()
    left = []
    if marker_after is marker_before:      # not re-executed: whatever differs, this test assigned
        for name, (text0, isdir0) in paths_before.items():
            text1, isdir1 = paths_after.get(name, (None, False))
            if text1 != text0:
                left.append("romp_judge.%s changed from %s to %s" % (name, text0, text1))
            elif isdir0 and not isdir1:
                left.append("romp_judge.%s %s was a directory and is gone" % (name, text0))
    else:                                  # re-executed: the loader bound the roots, and created STATE
        text1, isdir1 = paths_after.get("STATE", (None, False))
        if text1 is not None and not isdir1:
            left.append("romp_judge.STATE %s is not a directory after the test reloaded the judge" % text1)
    for name in _SEAM_ENV_NAMES:
        v0, v1 = env_before[name], os.environ.get(name)
        if v0 == v1:
            continue
        if v1 is None:
            left.append("%s was set and is now unset" % name)
        elif v0 is None:
            left.append("%s was unset and is now set" % name)
        else:
            left.append("%s was changed" % name)
    if left:
        pytest.fail("%s left shared state changed after its teardown: %s. Save the prior value before "
                    "changing it and put it back at the end of the test; for a path, before removing the "
                    "directory it named." % (request.node.nodeid, "; ".join(left)), pytrace=False)


def restore_env(name, prior):
    """Put the environment name back the way a test found it: `prior` is the os.environ.get(name) taken before
    the test changed it, None meaning unset. A tearDown that pops the name instead leaves a later module in the
    process without the value its own import set; this is the restore the fixture above expects."""
    if prior is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = prior


# No module leaves a watched environment name changed after its own teardown (2026-09-23, the reviewer's ruling of round
# 1 on fork PR #894). The census in tests/test_hermetic_kernel_postal.py reads what executes at IMPORT, and
# _shared_state_restored above is per test, its snapshot taken after the module's setUpModule, its classes' setUpClass
# and its module- and class-scoped fixtures have run, so a seam written there with no restore reached every test
# scheduled after it in the process, and every child those tests spawned, and no test failed. This fixture takes its
# snapshot before any of those run (an autouse module-scoped fixture of this file is set up before the module's own
# setUpModule, which pytest runs as a module-scoped autouse fixture registered on the module, after the ones registered
# here, and before every class-scoped setup) and fails, naming the module, when a watched name differs after the
# module's teardown (its tearDownModule, tearDownClass and fixtures have run by then). What it names is a write made in
# the module's own setup, tests or teardown that the module leaves behind for later modules; one made and put back inside
# the module is quiet. What it does not read, each for its reason: a write made at import, during collection (the
# census reads that); a write by a session- or package-scoped fixture whose setup runs before this snapshot, which
# reaches every later module, since the fixture's teardown runs at the end of the session or package, after every
# module's check. Which check reads such a fixture's write turns on when its setup runs against the two snapshots, not
# on which test first uses it. A fixture a test requests by name (in its signature, in the signature of a fixture it
# requests, or as autouse) is set up before the test's module- and function-scoped fixtures, highest scope first: when
# the first of the module's tests to be set up requests it (an autouse one always does), before this snapshot and every
# per-test snapshot of _shared_state_restored, so neither check reads it; when a later test is the first to, after this
# snapshot and before that test's, so this check names the module and the per-test check does not. The first test to be
# set up need not be the module's first. A test counts as set up once its module-scoped fixtures are set up, this one
# before the module's own; a test pytest ends before that point sets up none of them, so a fixture requested by name by
# the first test that is set up is read by neither check, however many tests before it were ended. Ended before that
# point: a test a skip or skipif mark skips, or an xfail mark with run=False ends (pytest's skipping plugin ends it in
# its setup hook before any fixture is set up; under --runxfail an xfail mark ends nothing, and the test is set up), and
# a test that requests a session- or package-scoped fixture whose setup skips or raises (by name, through a fixture it
# requests, by a usefixtures mark, or as autouse, which ends every test the fixture reaches), since pytest sets a test's
# fixtures up highest scope first. Set up: a test skipped in its body, in a module-, class- or function-scoped fixture,
# in setUpClass, or by one of unittest's skip decorators. Each case of the three sentences before this one is a plant in
# test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows (the verifier's
# finding on round 2 of fork PR #894, where this text had counted a skip in a session or package fixture as set up). A
# fixture requested at run time (request.getfixturevalue) is set up where the call runs: in a test's body or in a
# function-scoped fixture the test requests by name, after that test's per-test snapshot, so both checks read it, the
# per-test one naming the test; in a module-scoped fixture, after this snapshot and before the test's, so only this
# check does (the verifier's plants on round 2 of fork PR #894, run by tests/test_hermetic_kernel_postal.py; the tree
# has no fixture scoped above module, which that module holds at none). Also unread: a write by a plugin's own hook or
# fixture outside the module's setup; and any name the list in the docstring leaves out. Every watched name is popped at
# this file's import, before collection (the lines above), so nothing the developer's shell carries reaches the check,
# and it reads the same run on every box.
MODULE_WATCHED_ENV_NAMES = _SEAM_ENV_NAMES + ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PORT")
MODULE_ENV_FLOORS = {"ROMP_POSTAL_PORT": None}


@pytest.fixture(scope="module", autouse=True)
def _module_env_restored(request):
    """Fail naming the module when a watched name differs after the module's teardown from its value before the module's
    setUpModule, setUpClass and module- and class-scoped fixtures ran (a fixture scoped above module that the first of
    the module's tests to be set up requests by name has run by then: the comment above says which requests each check
    reads, and which tests are not set up). The watched names, MODULE_WATCHED_ENV_NAMES: the seams
    _shared_state_restored watches per test (_SEAM_ENV_NAMES: the sessions file, the serve token and the bus name) and
    the postal trio (peers, client-only and the port). Not watched: PYTEST_CURRENT_TEST, which pytest writes for every
    phase, and every name this file re-asserts before every test (the dead ports, the service-env, claude-config,
    catalog, scope and CLI-binary floors, ROMP_SUPERVISED and the credential names), whose write here would read as a
    change on the module in whose first test to be set up it ran. The one trio leg this file re-asserts,
    ROMP_POSTAL_PORT (popped before every test), is watched against the value that re-assert gives it, unset
    (MODULE_ENV_FLOORS), rather than against the snapshot: a port a module leaves set after its teardown reaches the
    next module's setUpModule, setUpClass and module fixtures, and every child they spawn, before that module's first
    test to be set up pops it. Every name outside the list is outside this check: a diff of the whole environment reds
    on the runner's own writes."""
    before = {name: os.environ.get(name) for name in MODULE_WATCHED_ENV_NAMES}
    yield
    left = []
    for name in MODULE_WATCHED_ENV_NAMES:
        v0 = MODULE_ENV_FLOORS[name] if name in MODULE_ENV_FLOORS else before[name]
        v1 = os.environ.get(name)
        if v0 == v1:
            continue
        if v1 is None:
            left.append("%s was set and is now unset" % name)
        elif v0 is None:
            left.append("%s was unset and is now set" % name)
        else:
            left.append("%s was changed" % name)
    if left:
        pytest.fail("module %s left the environment changed after its teardown: %s. A write the module does not put back "
                    "(in setUpModule, setUpClass, a module- or class-scoped fixture, or a test) holds for every test "
                    "scheduled after the module and every child they spawn: save the prior value and put it back in the "
                    "matching teardown, or set it per test in setUp with a cleanup." % (request.node.nodeid, "; ".join(left)),
                    pytrace=False)


# No test report may carry a process-environment VALUE, or a credential-shaped token (2026-09-05). A
# test that renders an env mapping in an assertion (assertNotIn on os.environ, on a _judge_env() copy
# of it, on a launch env) prints the whole mapping when it fails, and on a developer's box that
# mapping holds live credentials. Assertions that test membership and name the key are the fix; this
# hook is the safety net for an assertion still written the other way. Two nets, applied to every
# report's text (the longrepr and the captured-output sections) whatever the outcome, and to
# collection reports:
#   * every value seen in this process's environment, 16 characters or longer, is replaced with one
#     marker, and so is each whitespace-separated chunk of such a value that is 16 characters or
#     longer (pprint renders a value with spaces as adjacent literals on separate lines, so a
#     whole-value replace misses the pieces), and so is each piece of such a value that pytest or
#     unittest left beside a cut (`'<head>...<tail>'`, `[N chars]`: a failed `==` keeps 12 and 13
#     characters of each operand, so most of a 30-character value showed on the assert line and in
#     the short summary, 2026-09-07). Values are noted the moment they are WRITTEN into
#     os.environ (the mutation path is wrapped below: a plain assignment, update, setdefault,
#     os.putenv, os.environb, mock.patch.dict), and sampled at import, around each test and at
#     report time as well, for values that entered by another route (inherited from the parent
#     process, written by a C extension). Exempt, and never when the name is credential-shaped: a
#     path-valued variable by NAME (the shell's, this conftest's own dirs, the interpreter and
#     workspace paths GitHub Actions exports); a variable whose value is public by NAME (the ones
#     GitHub Actions exports to describe the run: the server URLs, the sha, the ref, the workflow
#     and job names, the repository and the actor, each of which a CI failure report was showing as
#     the marker, 2026-09-07; and the synthetic git identity this conftest sets at import); a name
#     family that is never a credential (XDG_*, and pytest's own PYTEST_*: PYTEST_CURRENT_TEST holds
#     the running test's node id and is written for every phase of every test, so noting it grew the
#     set by one value per test, slowed every report's scrub in step and made the node id of every
#     test already run a target in later reports); and any value that IS a path this machine has
#     (one absolute path that exists, or a PATH-style list of them), because a traceback quotes the
#     interpreter's prefix on every frame and a developer's shell names it under any variable (a
#     pyenv root, a conda prefix).
#   * credential-shaped tokens by PATTERN (tests/credential_patterns.py: the public key prefixes, and
#     a long token in a value position), whatever their provenance: a token that never touched the
#     environment (read from a file, printed by a child) is caught by this one.
# A report the hook leaves alone keeps pytest's own object and rendering. One it changes is rebuilt
# from the scrubbed text as a native-style traceback with its crash location kept (its message
# scrubbed too), so the short test summary still ends in the assertion message, junitxml keeps its
# message and xdist carries it to the controller; that report loses colour and source highlighting,
# nothing else (_redacted_longrepr).
ENV_VALUE_MIN_LEN = 16
ENV_VALUE_REDACTED = "[REDACTED-ENV-VALUE]"
_ENV_VALUE_PATH_NAMES = frozenset((
    "PWD", "OLDPWD", "HOME", "PATH", "TMPDIR", "SHELL", "VIRTUAL_ENV", "PYTHONPATH", "LS_COLORS",
    "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV", "ROMP_DIR", "ROMP_STATE_DIR", "ROMP_CLAUDE_BIN",
    "ROMP_SYSTEMD_DIR", "ROMP_LAUNCHD_DIR", "CLAUDE_CONFIG_DIR", "ROMP_TESTS_SYSTEM_TMPDIR",
    # the Claude settings dir conftest saved ahead of its CLAUDE_CONFIG_DIR floor (above), for the live
    # move test: a path a failure report may quote, like CLAUDE_CONFIG_DIR beside it
    "ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR",
    # GitHub Actions: the runner's workspace and tool cache, and the interpreter prefix setup-python
    # exports under six names (every stdlib and site-packages frame of a CI traceback is under it)
    "GITHUB_WORKSPACE", "RUNNER_WORKSPACE", "RUNNER_TEMP", "RUNNER_TOOL_CACHE", "pythonLocation",
    "Python_ROOT_DIR", "Python2_ROOT_DIR", "Python3_ROOT_DIR", "LD_LIBRARY_PATH", "PKG_CONFIG_PATH"))
# Public by name, so never a value a report must hide. GitHub Actions describes the run in these (its
# secrets are GITHUB_TOKEN, ACTIONS_RUNTIME_TOKEN and ACTIONS_ID_TOKEN_REQUEST_TOKEN, credential-shaped
# names this set is never consulted for); without them a CI failure read `assert '[REDACTED-ENV-VALUE]'
# == 'x'` where a test compared the ref, the repository or the actor. Listed by name rather than by the
# GITHUB_ prefix so that a token GitHub adds under a name this list does not know still qualifies. The
# GIT_* names are the synthetic identity this conftest writes at import (`romp tests`,
# `tests@example.invalid`), under which every fixture commit is made.
_ENV_VALUE_PUBLIC_NAMES = frozenset((
    "GITHUB_SERVER_URL", "GITHUB_API_URL", "GITHUB_GRAPHQL_URL", "GITHUB_SHA", "GITHUB_REF", "GITHUB_REF_NAME",
    "GITHUB_HEAD_REF", "GITHUB_BASE_REF", "GITHUB_EVENT_NAME", "GITHUB_WORKFLOW", "GITHUB_WORKFLOW_REF",
    "GITHUB_WORKFLOW_SHA", "GITHUB_JOB", "GITHUB_ACTION", "GITHUB_ACTION_REF", "GITHUB_ACTION_REPOSITORY",
    "GITHUB_REPOSITORY", "GITHUB_REPOSITORY_OWNER", "GITHUB_ACTOR", "GITHUB_TRIGGERING_ACTOR", "RUNNER_NAME",
    "RUNNER_ARCH",
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"))
_ENV_VALUE_EXEMPT_PREFIXES = ("XDG_", "PYTEST_")   # never a credential: the XDG base dirs, pytest's bookkeeping
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


def _is_existing_path(value: str) -> bool:
    """Whether `value` is a path this machine has: one absolute path that exists, or a PATH-style list
    of them (every non-empty os.pathsep chunk). No token is an absolute path that exists, so this
    exempts no token; a path that does not exist is a value like any other."""
    chunks = [c for c in value.split(os.pathsep) if c]
    return bool(chunks) and all(os.path.isabs(c) and os.path.exists(c) for c in chunks)


def env_value_qualifies(name: str, value: str) -> bool:
    """Whether one environment entry's value is one a report must not show: ENV_VALUE_MIN_LEN
    characters or more, unless the name is exempt (a path-valued variable by name, a variable whose
    value is public by name, or a name family that is never a credential) or the value is a path this
    machine has; a credential-shaped name is never exempt. The one rule, for the sampler and for the
    write hook."""
    if len(value) < ENV_VALUE_MIN_LEN:
        return False
    if _credential_shaped(name):
        return True
    if name in _ENV_VALUE_PATH_NAMES or name in _ENV_VALUE_PUBLIC_NAMES or name.startswith(_ENV_VALUE_EXEMPT_PREFIXES):
        return False
    return not _is_existing_path(value)


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


# A piece of a value beside a cut pytest or unittest made: a maximal run of ENV_CUT_FRAGMENT_MIN_LEN or
# more token characters that abuts `...` or `[N chars]` on at least one side (the marker before it, the
# marker after it, or a quote on one side and the marker on the other). pytest renders a failed `==` at
# default verbosity with each operand cut to 12 and 13 characters around `...` (`'abcdefghijkl...rstuvwxyzabcd'`
# for a 30-character value), its saferepr of a local or a `+  where` operand keeps 117 on each side,
# the short summary cuts the message at the terminal's width with `...` appended, a long explanation
# is cut at 640 characters the same way, and unittest shortens a container repr with `[N chars]`; none
# of those pieces is the whole value or a whitespace chunk of it, so the replace above left them
# standing (2026-09-07). A candidate is replaced only when it is a substring of a noted value: exact,
# never a guess from its shape (the pattern net's fragment rule does that for tokens of no known
# provenance). Two alternatives so each maximal run is tried once from its start, which keeps the pass
# linear on a long run that reaches no cut.
ENV_CUT_FRAGMENT_MIN_LEN = 8
_ENV_CUT_FRAG_RE = re.compile(
    r"(?:(?<=\.\.\.)|(?<=chars\]))[A-Za-z0-9_\-]{%d,}"                                  # after a cut
    r"|(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{%d,}(?=\.\.\.|\[\d+ chars\])"                    # before one
    % (ENV_CUT_FRAGMENT_MIN_LEN, ENV_CUT_FRAGMENT_MIN_LEN))


def redact_env_values(text: str, values) -> str:
    """`text` with every occurrence of every value replaced by ENV_VALUE_REDACTED, longest first (a
    value that contains another is replaced whole), then every whitespace-separated chunk of a
    value that is ENV_VALUE_MIN_LEN characters or more (pprint renders a long value with spaces as
    adjacent string literals on separate lines, so the token half of `Authorization: Bearer <token>`
    survived a whole-value replace, and unittest's shortened repr shows a differing tail on its own),
    and then every piece of a value left beside a cut (_ENV_CUT_FRAG_RE: a run of token characters
    against `...` or `[N chars]` that is a substring of a value)."""
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
    if not parts:
        return text

    def cut_piece(m):
        frag = m.group(0)
        return ENV_VALUE_REDACTED if any(frag in v for v in parts) else frag
    return _ENV_CUT_FRAG_RE.sub(cut_piece, text)


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


def _redact_crash_message(message: str) -> str:
    """A crash message scrubbed as the report body renders it. pytest writes the message's lines under
    the `E` marker (`E   ` + line), and the pattern net's rules for a failed comparison's diff lines
    and quoted elements are keyed on that marker; the bare message (`  - <token>` after the diff's
    header) is a rendering the rules do not know, so it is scrubbed marked and unwrapped. Under CI
    pytest prints the whole message, every line, in the short test summary."""
    marked = "\n".join("E   " + line for line in message.split("\n"))
    return "\n".join(line[4:] if line.startswith("E   ") else line
                     for line in redact_report_text(marked).split("\n"))


def _redacted_longrepr(lr, text: str):
    """The scrubbed `text` of a longrepr as a longrepr again. A failure's keeps its crash location
    (pytest's own ReprFileLocation, the message scrubbed too) over a native-style traceback whose one
    entry is the text: the short test summary ends in reprcrash.message, junitxml's message attribute
    reads it, and xdist serializes a longrepr with a traceback and a crash structurally, where a plain
    str showed the traceback's first line in the summary instead (`def test_x():`, or `self = <Case
    testMethod=...>`). pytest renders a native entry as is, so that report loses colour and source
    highlighting and nothing else. A longrepr with no crash location (a collection error's) becomes
    the plain text."""
    crash = getattr(lr, "reprcrash", None)
    if crash is None:
        return text
    return ReprExceptionInfo(reprtraceback=ReprTracebackNative([text + "\n"]),
                             reprcrash=ReprFileLocation(crash.path, crash.lineno, _redact_crash_message(crash.message)))


def _redact_report(rep) -> None:
    """Every text a report carries, whatever its outcome: the longrepr (a failure's text; a skip's is
    a (path, line, reason) tuple, whose reason is the text) and the captured-output sections (which
    -rA and -rP print for passed tests too). A longrepr the nets leave unchanged keeps pytest's own
    object and rendering; one they change is rebuilt by _redacted_longrepr."""
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
            rep.longrepr = _redacted_longrepr(lr, red)
    if getattr(rep, "sections", None):
        rep.sections = [(name, redact_report_text(content)) for name, content in rep.sections]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # ONE implementation per hook per module: a second `def` of this name would silently replace this one
    # (it did, for an afternoon on 2026-09-10, and every report printed its values again). Anything else
    # that shapes a test report joins here: the served-tests switch first (its message quotes the skip's
    # reason), the redaction last, so whatever any step wrote is read for values before it is printed.
    outcome = yield
    rep = outcome.get_result()
    _require_served_test_ran(item, rep)
    _redact_report(rep)


@pytest.hookimpl(hookwrapper=True)
def pytest_collectreport(report):
    """A collection error (an import-time exception whose message names a value) is a report too.
    Redacted BEFORE the other implementations see it: the terminal reporter files it from here."""
    _redact_report(report)
    yield


# ── thread census (T282) ──────────────────────────────────────────────────────────────────────────────
# A test that starts a real kernel loop, a backend pump or a fake server must end it before its module ends: a
# daemon thread that outlives its module runs against whatever the shared modules (the judge, the event model)
# are bound to by then. These two helpers are the pin every such module carries, and the module-boundary
# tracer reads the same census, so a leak is named by the module that made it.
def thread_census():
    """The live non-main threads as stable descriptors: the target's qualified name when the thread has one,
    else its name; pytest-timeout's own watchdog thread excluded. Sorted, so two censuses compare directly."""
    import threading
    out = []
    for t in threading.enumerate():
        if t is threading.main_thread():
            continue
        target = getattr(t, "_target", None)
        mod = (getattr(target, "__module__", "") or "") if target is not None else ""
        if t.name.startswith("pytest_timeout") or mod.startswith("pytest_timeout"):
            continue
        out.append("%s.%s" % (mod, getattr(target, "__qualname__", None) or repr(target)) if target is not None else t.name)
    return sorted(out)


def wait_for_census(before, timeout=5.0):
    """The threads alive now that were NOT in `before`, once that set is empty or at the deadline: a module's pin is
    "nothing this module started outlives it", so a thread from an EARLIER module that happens to end during this one
    cannot fail it, and a thread this module started has a moment (20 ms polls, up to `timeout`) to reach its exit
    after join(timeout) returned. Returns the sorted leftovers; a clean module gets []."""
    import collections
    import time
    deadline = time.monotonic() + timeout
    base = collections.Counter(before)
    while True:
        extra = sorted((collections.Counter(thread_census()) - base).elements())   # by COUNT: a second thread of a
        if not extra or time.monotonic() >= deadline:                              # kind already present is a leftover
            return extra
        time.sleep(0.02)


# Browser-backed served-page tests fail loudly where they must run (T308, 2026-09-10). tests/test_*_browser.py and
# tests/test_*_served.py boot a hermetic kernel and drive the real dashboard pages in playwright's Chromium; on a machine
# without the extension's node deps or a browser they skip, and say why. CI's Python matrix jobs are such machines, so a
# served-page regression never turned them red (the deep-link landing pin, T307, red on main while CI stayed green). The
# extension job installs that browser and runs these files with ROMP_SERVED_TESTS_REQUIRE=1: any skip in them (a class
# setUp that finds no deps, a driver that exits 3 for a missing browser, a kernel that never served) is reported as a
# FAILURE carrying the skip's own reason, the stance the pane bench takes with ROMP_UI_BENCH_REQUIRE. One exception a
# test can claim for itself: a skip whose reason begins with "optional:" stays a skip, for a leg the runner has declared
# it does not carry (the pane-hiding test drives three engines and CI installs one; ROMP_SERVED_TESTS_ENGINES names the
# installed ones, and that test says "optional:" for the others). Off (the default) nothing changes: contributors and
# the Python matrix jobs skip as before. Pinned by tests/test_served_tests_require.py.
_SERVED_TESTS_REQUIRE = os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1"


def _is_served_test_file(item) -> bool:
    name = os.path.basename(str(getattr(item, "path", None) or item.fspath))
    return name.startswith("test_") and (name.endswith("_browser.py") or name.endswith("_served.py"))


def _require_served_test_ran(item, rep) -> None:
    """Under ROMP_SERVED_TESTS_REQUIRE=1, a skip in a browser-backed served-page test file is reported as a
    failure carrying the skip's own reason; an `optional:` skip stays a skip. Called from the one
    pytest_runtest_makereport above. No-op with the switch off."""
    if not _SERVED_TESTS_REQUIRE:
        return
    if rep.skipped and _is_served_test_file(item):
        lr = rep.longrepr
        reason = lr[2] if isinstance(lr, tuple) and len(lr) == 3 else str(lr)
        if re.match(r"^(Skipped: )?optional:", reason):
            return
        rep.outcome = "failed"
        rep.longrepr = ("ROMP_SERVED_TESTS_REQUIRE=1: a browser-backed test skipped (at %s) where it must run: %s"
                        % (rep.when, reason))
