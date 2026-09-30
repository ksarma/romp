"""Global test isolation (2026-07-07): point XDG_STATE_HOME at a fresh temp dir BEFORE any test module
loads bin/romp-judge or bin/romp-kernel — both resolve their state root at import time. Without this,
any test that skips its own rebind writes into the REAL ~/.local/state/romp (the diary guard's
judge-errors.jsonl lines from legacy-flag fixtures made that visible). conftest.py imports before every
test module, so this is a suite-wide floor; per-class _rebind_state/tempdir isolation still layers on
top exactly as before."""
import ast
import atexit
import collections
import concurrent.futures.thread    # the session-end thread guard reads its exit-join table (EXIT_JOIN_TABLES)
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
import traceback

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
# One process is passed over, by identity and never by its name, and only while the check reads the premise of the
# pass-over as holding (2026-09-27, round 2 of fork PR #894's review, and the reviewer's closing check of it): the
# controller's own multiprocessing resource tracker, the pid the controller's multiprocessing.resource_tracker records
# for its tracker, while that pid is the controller's child (_own_resource_tracker). The stdlib starts the tracker on
# demand (a spawn-context ProcessPoolExecutor starts it, as tests/test_session_env.py's census pool class does in its
# setUpClass); the tracker ignores SIGINT and SIGTERM and exits when the last write end of its pipe closes. In a serial
# run it holds the run's temp root through the environment it inherited (a serial run of that class was red on it before
# the pass-over); under pytest-xdist it is a worker's and exits with the worker. The premise is that it exits with the
# controller, which the check reads as: no /proc/<pid>/fd table the check can read, other than the controller's and the
# tracker's, holds its pipe (_tracker_kept). A process whose descriptors cannot be read, a thread's descriptor table
# that /proc/<pid>/fd does not show, and a descriptor in flight are not read for it (below). A child forked through
# multiprocessing's fork context keeps the controller's write end and a spawn-context worker is handed one, on every
# version; a raw os.fork child keeps it on 3.12 and earlier, and on 3.13 and 3.14 before the gh-146313 releases, which
# close a raw fork's copy in the child. Any of them keeps the tracker from exiting on its own while it holds the pipe.
# On 3.12.9 and earlier, on 3.13.0 to 3.13.2, on 3.13.14 and later 3.13 releases, on 3.14.5 and later 3.14 releases and
# on 3.15 from 3.15.0b1, a process that still holds the pipe when the controller exits keeps the tracker running after
# the controller has gone. On 3.12.10 and later 3.12 releases, on 3.13.3 to 3.13.13 and on 3.14.0 to 3.14.4, the
# controller's exit waits for the tracker instead: ResourceTracker.__del__, run as the controller's interpreter shuts
# down, closes the controller's write end and waits for the tracker to exit with a blocking waitpid, so the controller
# does not exit until no other process holds the pipe, and the tracker exits before the controller does. With the
# pass-over by identity alone, a serial run whose test left a raw fork's child holding
# the pipe ended green and silent, since such a child need hold no path under a root (its environment is the block the
# controller started with, before the run minted its roots). The pipe is read from /proc: the one whose write end the
# controller's record holds (its descriptor, read at /proc/<pid>/fd), when the tracker holds a descriptor on it too (the
# end it reads from); then every other process's /proc/<pid>/fd table that can be read is read for it (_pipe_holders).
# A process found holding it leaves the tracker judged like any process, so named when it holds a root, as it does in a
# serial run, with that process's pid on its line; so does a pipe that cannot be read, or a tracker that holds no
# descriptor on it, with the reason on its line. The premise is read before the wait, which then waits for the exit of
# each process holding the pipe as it waits for a holder's, and read again after the wait, where it decides, so a child
# that exits at session end does not get the tracker named. Where the premise cannot be read, the check's own scope
# decides. Without procfs the check runs nothing (below), so nothing is passed over and nothing is named. With procfs
# and the pipe unreadable, the tracker is judged like any process, so named when it holds a root: within its scope the
# check names every readable process that holds a root, the pass-over is an exception to that, and an exception applies
# only where its premise is shown (a red there is a visible false refusal; a pass-over on a premise nobody read would be
# the silent miss the premise exists to prevent). A tracker whose own /proc entries refuse reads (a non-dumpable
# process's environment, cwd and descriptors refuse them together, so its pipe is unread too) is listed by pid as not
# judged, with the reason on its line, leaving the exit status alone, when it meets the condition under which any
# unreadable process is listed: this user's, started after the controller, in its cgroup (below). Outside that
# condition, as when it has moved into another cgroup, it is neither listed nor counted: the check keeps no count from
# its scan of the tracker alone, and its main scan passes over the tracker.
# A process whose descriptors cannot be read (another user's, or one of this user's that made itself non-dumpable) is
# not read for the pipe, as it is not read for a root, and it never makes the run red: a non-dumpable child that keeps
# the pipe leaves the tracker passed over, and is itself listed as not judged when it is this user's, started during the
# run, in its cgroup (below). A process holding a write end is judged for a root in its own right, and so is a second
# tracker a test starts itself. tests/test_run_end_leaked_processes.py pins the pass-over; the premise (a forked child
# that keeps the pipe past the run's end, one that exits during the wait, a pipe the check cannot read, a tracker whose
# environment, cwd and descriptors cannot be read, a record naming a child of the controller that holds no descriptor on
# the pipe); the unread class's witness (a non-dumpable forked child that keeps the pipe); a run without procfs that
# started the tracker; the second tracker; and a record naming a process that is not the controller's child.
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
# on the box (the leaked bus of the reproduction was gone within a second of its SIGTERM). The wait starts when a holder
# is seen, when a process is listed as not judged (below), or when a process other than the controller and the tracker
# is found holding the tracker's pipe (above), so a run with none of the three pays nothing for it, and a run that
# leaves only a listed process waits for that process's exit, up to the whole bound, and stays green. The tracker
# (above) is never waited for, listed or not: it does not exit on its own while the controller holds its pipe (it
# ignores SIGINT and SIGTERM). Before the scan
# the controller joins its live non-daemon threads other than the main one within the same bound, so a process such a
# thread starts after its test returned is seen. A thread that ends costs the run only the time until it ends (the
# interpreter would join it at exit anyway); one that ends only through threading's exit hooks, which run at
# interpreter exit after this check, is waited the whole bound: the worker of an idle concurrent.futures pool a test
# never shut down (an unclosed event loop's default executor is one), whose witness is
# tests/test_run_end_leaked_processes.py's idle-pool case. The join never waits on a daemon thread (a server thread
# left running would make every run pay the bound), and a thread whose own join raises is waited on no more
# (_join_live_threads). The check names no thread (since fork PR #894's landing merge with
# the fork's main, which brought fork PR #922's session-end thread guard, below): the guard names, at the teardown of
# each process's last test, each thread it guards still alive at its cap (every non-daemon thread and every
# concurrent.futures thread, pytest-timeout's timer aside), so a leaked thread is reported once, by the guard, and a
# leaked process once, by this check. The idle worker above is
# one: in a serial run the guard waits its cap for it and fails the run naming it, and this join then waits the bound
# for it again before the scan. A daemon thread outside concurrent.futures' tables is named by neither (the guard's
# comment says why). The check never kills: the pid it names is the
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
#     any report of a holder or a listed process. The controller's own resource tracker is the exception to the wait
#     and the count: when its premise is unshown it is listed under the same condition but never waited for, and
#     outside the condition it is neither listed nor counted (above);
#   * a thread's descriptor table that /proc/<pid>/fd does not show: the check reads a process's descriptors, for the
#     tracker's pipe and for a root, at /proc/<pid>/fd, the table of its leading thread, so a table a thread made its
#     own (unshare(CLONE_FILES)) and the live threads' table of a process whose leading thread has exited, both
#     readable at /proc/<pid>/task/<tid>/fd, are not read: a child that keeps the tracker's pipe in either leaves the
#     tracker passed over, and a process whose leading thread has exited reads as a zombie and is skipped, neither
#     judged nor listed nor counted;
#   * a thread's cwd that /proc/<pid>/cwd does not show: the check reads a process's cwd at /proc/<pid>/cwd, its
#     leading thread's, so when a thread other than the leading one calls unshare(CLONE_FS) and then changes
#     directory to a path under a root, its cwd, readable at /proc/<pid>/task/<tid>/cwd, is not read: a process that
#     holds a root through that cwd alone is not named;
#   * a descriptor on the tracker's pipe in flight: the pipe is read from /proc/<pid>/fd tables only, so a write end
#     queued in a unix socket and not yet received, which is in no process's table once its sender has closed its own
#     copy, keeps the tracker from exiting on its own while it is queued, unseen, and the tracker is passed over;
#   * a process started after the scan: by a non-daemon thread still running when the join's bound ran out, by a
#     daemon thread, or by any process outside this one. The check names no thread (above): a thread of the first kind
#     that was alive at the teardown of the process's last test is named by the session-end thread guard, which
#     fails the run, and a daemon thread outside concurrent.futures' tables is named by neither.
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
            continue                        # exited, not yet reaped, or its leading thread exited: not read
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


def _own_resource_tracker():
    """The controller's own multiprocessing resource tracker by identity (the comment above LEAK_EXIT_BOUND_S): (pid, fd),
    the pid its multiprocessing.resource_tracker records for its tracker, when that pid is this process's child, and the
    descriptor that record writes to, the write end of the pipe the tracker reads from. None when this process never
    imported that module (it started no tracker), when the record holds no pid, or when the pid is not this process's
    child (a process forked from another can inherit its parent's record). Identity alone passes nothing over: the run
    end passes the tracker over only while it reads the premise of the pass-over as holding (_tracker_kept, which names
    what it does not read for it, and _run_end_holders)."""
    rt = sys.modules.get("multiprocessing.resource_tracker")
    record = getattr(rt, "_resource_tracker", None)
    pid = getattr(record, "_pid", None)
    if not isinstance(pid, int):
        return None
    try:
        ppid = _proc_stat(pid)[1]
    except (OSError, ValueError, IndexError):
        return None
    return (pid, getattr(record, "_fd", None)) if ppid == os.getpid() else None


def _pipe_holders(link, skip):
    """The live processes, other than those in `skip`, one of whose open file descriptors reads `link` (a pipe as /proc
    spells it, pipe:[<inode>]), read from /proc/<pid>/fd as _fds_hold reads a descriptor. Raises OSError where /proc
    cannot be listed. A process whose descriptors cannot be read (another user's, one of this user's that made itself
    non-dumpable, a zombie) is not among them: the pipe is read where the check reads (the comment above
    LEAK_EXIT_BOUND_S names that class)."""
    out = []
    for pid in [int(d) for d in os.listdir("/proc") if d.isdigit()]:
        if pid in skip:
            continue
        try:
            fds = os.listdir("/proc/%d/fd" % pid)
        except OSError:
            continue
        if any(_link("/proc/%d/fd/%s" % (pid, fd)) == link for fd in fds):
            out.append(pid)
    return out


TRACKER_KEPT_LABEL = "the process the controller's resource tracker record names, not passed over: "
TRACKER_PIPE_UNREAD = "the pipe it reads from could not be read"
TRACKER_NOT_ON_PIPE = "it holds no descriptor on the pipe the controller's record writes to"


def _tracker_kept(tracker):
    """(why, others) for the controller's own resource tracker, `tracker` as _own_resource_tracker returns it. `why` is
    "" when the check reads the premise of the pass-over as holding (the tracker exits with the controller): no
    /proc/<pid>/fd table it can read, other than the controller's and the tracker's, holds the pipe the tracker reads
    from. A process whose descriptors cannot be read, a thread's descriptor table that /proc/<pid>/fd does not show, and
    a descriptor in flight in a unix socket are not read for it (the comment above LEAK_EXIT_BOUND_S names each).
    Otherwise `why` is the reason it is not passed over, which its report line carries, and `others` lists the processes
    found holding that pipe. The pipe is read from /proc: the one the controller's record writes to (its descriptor,
    read at /proc/<pid>/fd), when the tracker holds a descriptor on it too, the end it reads from; then every other
    process's /proc/<pid>/fd table that can be read is read for it (_pipe_holders). A pipe that cannot be read, or a
    tracker holding no descriptor on it, leaves the premise unshown, and the tracker is judged like any process (the
    comment above LEAK_EXIT_BOUND_S says why)."""
    pid, fd = tracker
    me = os.getpid()
    try:
        link = os.readlink("/proc/%d/fd/%d" % (me, fd))
        theirs = {_link("/proc/%d/fd/%s" % (pid, n)) for n in os.listdir("/proc/%d/fd" % pid)}
        others = _pipe_holders(link, (me, pid)) if link in theirs else None
    except (OSError, TypeError):                 # TypeError: a record holding no descriptor
        return TRACKER_PIPE_UNREAD, []
    if others is None:
        return TRACKER_NOT_ON_PIPE, []
    if not others:
        return "", []
    who = ("pid %d also holds" % others[0]) if len(others) == 1 else (
        "pids %s also hold" % ", ".join(str(p) for p in others))
    return ("%s the pipe it reads from, so the tracker exits with the controller only if no other holder of that pipe "
            "is left when the controller exits" % who), others


def _run_end_holders(roots, bound_s):
    """_leaked_run_processes over `roots` for the run end, the controller's own resource tracker (_own_resource_tracker)
    passed over only while the premise of the pass-over reads as holding (_tracker_kept, which names what is not read
    for it). The premise is read twice: before the wait, for the processes other than the controller and the tracker
    that hold its pipe, whose exits the wait then waits for as it waits for a holder's; and after the wait, where it
    decides. A tracker whose premise does not read as holding is scanned alone, and both halves of that scan are kept,
    each with the reason on its line: it is named when it holds a root, and listed by pid as not judged when its
    environment cannot be read (its own /proc entries refusing reads, as a non-dumpable process's environment, cwd and
    descriptors do together, which leaves its pipe unread too) and it meets the condition under which
    _processes_holding lists an unreadable process (this user's, started after the controller, in its cgroup). That
    scan's count of the unreadable processes outside that condition is not kept, and the main scan passes over the
    tracker, so a tracker outside that condition is neither listed nor counted. The tracker is never waited for: it
    does not exit on its own while the controller holds its pipe (it ignores SIGINT and SIGTERM)."""
    tracker = _own_resource_tracker()
    if tracker is None:
        return _leaked_run_processes(roots, bound_s)
    _why, others = _tracker_kept(tracker)
    leaked, unjudged, ok = _leaked_run_processes(roots, bound_s, skip_pids=(tracker[0],), wait_for=others)
    why = _tracker_kept(tracker)[0] if ok else ""
    if why:
        held, alone, _ok = _processes_holding(roots, pids=[tracker[0]])
        leaked = leaked + [dict(h, kept=why) for h in held]
        unjudged = dict(unjudged, listed=unjudged["listed"] + [dict(u, kept=why) for u in alone["listed"]])
    return leaked, unjudged, ok


def _leaked_run_processes(roots, bound_s=LEAK_EXIT_BOUND_S, pids=None, skip_pids=(), wait_for=()):
    """(holders still present, unjudged, procfs read): the processes holding `roots` after every holder seen first, and
    every process first listed as not judged, has been given until `bound_s` to exit (the event waited for is the pid's
    exit; the wait ends the moment the last one is gone). Nothing waits when nothing holds, nothing is listed and
    `wait_for` is empty. `pids` is _processes_holding's stand-in listing, handed to both scans
    (tests/test_run_end_leaked_processes.py times the wait over its own children alone: a process another test lists
    would be waited for too); `skip_pids` is passed over by both scans; `wait_for` names more pids whose exit the wait
    waits for, holders or not (the run end hands in the controller's resource tracker as `skip_pids` and the processes
    holding its pipe as `wait_for`, _run_end_holders)."""
    holders, unjudged, ok = _processes_holding(roots, skip_pids=skip_pids, pids=pids)
    if not ok or not (holders or unjudged["listed"] or wait_for):
        return holders, unjudged, ok
    deadline = time.monotonic() + bound_s
    pending = {h["pid"] for h in holders + unjudged["listed"]} | set(wait_for)
    while pending and time.monotonic() < deadline:
        pending = {pid for pid in pending if _pid_present(pid)}
        if pending:
            time.sleep(0.05)
    return _processes_holding(roots, skip_pids=skip_pids, pids=pids)


def _join_live_threads(bound_s, among=None):
    """Join this process's live non-daemon threads, other than the main one and the caller, until `bound_s` has passed
    (a thread one of them starts meanwhile is joined too), never waiting on a daemon thread. Returns every such thread
    still alive afterwards, daemon or not: a process one of them starts after the scan that follows is not seen. A join
    that raises (a Thread subclass's own join; a live thread has started, so the stdlib's join refuses none of them) is
    not waited on again and leaves its thread among those returned: the run-end check then goes on, where the exception
    would have ended pytest_sessionfinish, and the session with it, before the run's report printed (the session-end
    thread guard, which calls the same join at the process's last test, has already failed that test's teardown on it,
    and fork PR #922's tests plant such a join). `among` stands in for threading.enumerate()
    (tests/test_run_end_leaked_processes.py hands in stand-in threads)."""
    pool = threading.enumerate if among is None else (lambda: list(among))
    skip = [threading.current_thread(), threading.main_thread()]
    deadline = time.monotonic() + bound_s
    while True:
        pending = [t for t in pool() if t not in skip and not t.daemon and t.is_alive()]
        left = deadline - time.monotonic()
        if not pending or left <= 0:
            break
        try:
            pending[0].join(left)
        except KeyboardInterrupt:
            raise
        except BaseException:       # pytest.fail's exception is a BaseException: waited on no more, still returned
            skip.append(pending[0])
    return [t for t in pool() if t not in skip[:2] and t.is_alive()]


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
    every process of the run that still holds one of its roots, the controller's own resource tracker passed over only
    while its premise reads as holding and named with the reason when it does not (_run_end_holders), and make the
    run red; list this user's unreadable processes of the run (started after the controller, in its cgroup) as not
    judged, the tracker among them, with the reason, when its premise is unshown, its environment cannot be read and it
    meets that condition; and count the other unreadable ones, the tracker never among them. It names no thread: the
    session-end thread guard (below) names, at the teardown of each process's last test, each thread it guards still
    alive at its cap (every non-daemon thread and every concurrent.futures thread, pytest-timeout's timer aside), so a
    leaked thread is reported once, by the guard, and a leaked process once, here (the hundredth round-2 commit of fork PR #894, at its landing merge with the fork's main,
    which brought fork PR #922's guard; the comment above LEAK_EXIT_BOUND_S)."""
    bound = _leak_exit_bound()
    _join_live_threads(bound)
    leaked, unjudged, ok = _run_end_holders(_run_roots(), bound)
    if not ok:
        _say_at_run_end(session, "[tests] the run-end process check reads /proc and did not run on this platform")
        return
    lines = []
    if leaked:
        lines.append("[tests] %d process(es) of this run still hold its temp root at run end, %g s after the run finished "
                     "waiting for them to exit: a test started them and did not stop them; the run is red." % (len(leaked), bound))
        for h in leaked:
            lines.append("[tests]   pid %d (parent %d): %s | holds the root through %s | %s%s" % (
                h["pid"], h["ppid"], h["cmd"][:240] or "(no command line)", ", ".join(h["via"]),
                "spawned during %s" % h["test"] if h["test"] else PHASE_UNKNOWN,
                " | " + TRACKER_KEPT_LABEL + h["kept"] if h.get("kept") else ""))
    if unjudged["listed"]:
        lines.append("[tests] %d process(es) of this user started during this run, in its cgroup, could not be read and were "
                     "not judged: their environment, cwd and open files are unreadable (a process that made itself "
                     "non-dumpable, or one running a setuid program); they do not change the exit status." % len(unjudged["listed"]))
        for u in unjudged["listed"]:
            lines.append("[tests]   pid %d (parent %d): %s | not judged%s" % (
                u["pid"], u["ppid"], u["cmd"][:240] or "(no command line)",
                " | " + TRACKER_KEPT_LABEL + u["kept"] if u.get("kept") else ""))
    if lines:
        lines.append("[tests] %d other process(es) could not be read and were not judged: another user's, or this user's "
                     "started before this run or in another cgroup." % unjudged["other"])
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
    process check above: a process of the run that still holds one of its roots, the controller's own resource
    tracker aside while no /proc/<pid>/fd table the check can read, other than the controller's and the tracker's,
    holds the tracker's pipe (the comment above names what is not read for it), makes the run red."""
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
    controller, whose venv on a box has no claude_agent_sdk, and xdist's unserialize_warning_message imports the
    warning's module to rebuild it: ModuleNotFoundError, the node goes down, the run ends in INTERNALERROR
    (before this every -n run needed -p no:warnings). Matched on the MESSAGE PREFIX with the base category,
    never on the class: pytest parses each filterwarnings entry every time it applies them (configure,
    collection, each test), and an entry naming a class it cannot import is dropped with a
    PytestConfigWarning, which is: every xdist worker whose interpreter has no SDK, which on a box is every
    worker, until the emitting module inserts the venv path; a controller whose interpreter has no SDK,
    which on a box is every controller; and the CI steps that install
    no SDK, today the served-pages job's served-page pytest step, which loads this conftest (the Python matrix
    cells' interpreter, the five Linux cells and the two macOS cells on a weekly or dispatch run, imports the class
    since the SDK install step, in the controller and, on the Linux cells' two workers since batch 917, in each
    worker, since the package is installed in that interpreter rather than added to the path at import). A
    module-level warnings.filterwarnings in the emitting module does not
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
# Popped here with the seams, every run starts each watched name where CI's run starts it, whatever the shell carries:
# unset, but for client-only, which upstream's floor right after the hermetic marker below sets to "1" for the run (their
# PR 1848, in this file since the merge of main that brought fork PR #875). So both checks read the same run (every name
# of MODULE_WATCHED_ENV_NAMES is popped by these lines or the port's above; the hermetic module holds each watched name
# among this file's import-time pops and runs both checks from a shell carrying every one). The pops come before the
# marker, so that floor still sets client-only for the run (the hermetic module's import probe under that floor reds
# when a pop of client-only follows the floor line).
os.environ.pop("ROMP_POSTAL_PEERS", None)
os.environ.pop("ROMP_POSTAL_CLIENT_ONLY", None)
os.environ.pop("ROMP_POSTAL_HOST", None)
os.environ.pop("ROMP_SESSIONS_FILE", None)
os.environ.pop("ROMP_SERVE_TOKEN", None)
os.environ["ROMP_POSTAL_HERMETIC"] = "1"
os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"   # no in-process kernel of the run owns a bus: its ensure and its revive start none (2026-09-18: a revive
#                                                on a daemon thread outran a test's environment restore and left a real bus detached on the box, whose
#                                                port record under the shared state root redirected a later module's dial); a lab sets its own trio
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
    os.environ["ROMP_POSTAL_CLIENT_ONLY"] = "1"   # re-floored per test: each test starts at "1" whatever ran before it (1848's floor, 2026-09-18)
    yield


# No in-process kernel of the run dials the machine's fixed bus port (2026-09-23, the reviewer's ruling of round 1 on fork
# PR #894). A kernel a test module loads IN-PROCESS (load_source of bin/romp-kernel under a name that starts romp_kernel)
# reads its BUS_PORT from ROMP_POSTAL_PORT at import, and the fixture above pops that name before every test (this file
# pops it at import too), so every such kernel of a whole run read 25302, the machine's fixed bus port: a spy over one full
# serial run recorded the tests whose kernel's bus calls (a peer notify at a detach or a trust change, the GET /peers
# behind the routes that list remotes) dialled it, which on a box whose own bus listens there reach that bus; where
# nothing listens, as on CI, a refused notify kicked the revive into a real romp-postal-service ensure (before the merge
# of main that brought fork PR #875: under the client-only floor above, an in-process kernel's revive returns before its
# ensure unless that kernel ensured a bus of its own, _BUS_ENSURED). A dead port cannot
# be EXPORTED instead: the bus's fixed-port refusal licenses a port equal to the child's import-time ROMP_POSTAL_PORT
# beside ROMP_POSTAL_HERMETIC, which this file sets, so an exported port would license a revive's child to bind a real bus
# on it. So every loaded kernel module's BUS_PORT is set to DEAD_BUS_PORT before each test and put back after it. A refused
# call then kicks the revive on every box, not only where nothing listens; under the client-only floor the revive returns
# before its ensure while the kernel has ensured no bus of its own, and the tests whose notify is refused stub the revive
# themselves as well (_revive_postal_bus, put back by a cleanup), which holds whatever that flag reads; the peer-notify
# guard test in tests/test_kernel.py and the tunnels module's _PostalTrio exercise the revive road and keep their own
# handling (the guard holds _BUS_ENSURED False and waits the revive out under a scoped fake of subprocess.run, asserting
# the fake answered no postal-service call; the trio patches BUS_PORT to a port of the test's own and stubs
# _ensure_postal_bus).
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
_SEAM_ENV_NAMES = ("ROMP_SESSIONS_FILE", "ROMP_SERVE_TOKEN", "ROMP_POSTAL_HOST")


def _shared_judge_paths():
    """({name: (path text or None, is a directory)}, marker) for the shared judge's watched globals,
    STATE and PROJECTS, each read by getattr with its own literal name (the conftest reader of
    tests/test_hermetic_kernel_postal.py admits getattr only with a name it proves to be one fixed
    string, and a name taken from a loop over a tuple is not one); the marker being a function object
    judge.py defines (a re-execution replaces it); ({}, None) when no module has loaded the judge
    under its shared name yet."""
    jd = sys.modules.get("romp_judge")
    if jd is None:
        return {}, None
    out = {}
    for name, p in (("STATE", getattr(jd, "STATE", None)), ("PROJECTS", getattr(jd, "PROJECTS", None))):
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
# the first test that is set up is read by neither check, however many tests before it were ended. That rule decides
# every route; the two lists below name the routes planted, not every route there is. Ended before that point: a test a
# skip or skipif mark skips, or an xfail mark with run=False ends (pytest's skipping plugin ends it in its setup hook
# before any fixture is set up; under --runxfail an xfail mark ends nothing, and the test is set up); a test that
# requests a session- or package-scoped fixture whose setup skips or raises (by name, through a fixture it requests, by
# a usefixtures mark, or as autouse, which ends every test the fixture reaches), since pytest sets a test's fixtures up
# highest scope first; and a test a hook skips before pytest's runner sets its fixtures up, as a conftest's
# pytest_runtest_setup does when it runs before the runner's (a plain one does). Set up: a test skipped in its body, in
# a module-, class- or function-scoped fixture (setUpModule, which pytest runs as a module-scoped fixture, included), in
# setUpClass, by one of unittest's skip decorators, or by a conftest's pytest_runtest_setup that runs after the runner's
# (one marked trylast does). Each route either list names, and the rule's own case, is a plant in
# test_a_write_by_a_fixture_scoped_above_module_is_named_by_each_check_whose_snapshot_its_setup_follows (the verifier's
# findings on round 2 of fork PR #894, where this text had counted a skip in a session or package fixture as set up, and
# then left a conftest's hook out of the lists). A
# fixture requested at run time (request.getfixturevalue) is set up where the call runs: in a test's body or in a
# function-scoped fixture the test requests by name, after that test's per-test snapshot, so both checks read it, the
# per-test one naming the test; in a module-scoped fixture, after this snapshot and before the test's, so only this
# check does (the verifier's plants on round 2 of fork PR #894, run by tests/test_hermetic_kernel_postal.py; the tree
# has no fixture scoped above module, which that module holds at none). Also unread: a write by a plugin's own hook or
# fixture outside the module's setup; and any name the list in the docstring leaves out. Every watched name is popped at
# this file's import, before collection (the lines above), so nothing the developer's shell carries reaches the check,
# and it reads the same run on every box.
MODULE_WATCHED_ENV_NAMES = _SEAM_ENV_NAMES + ("ROMP_POSTAL_PEERS", "ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PORT")
MODULE_ENV_FLOORS = {"ROMP_POSTAL_PORT": None, "ROMP_POSTAL_CLIENT_ONLY": "1"}


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
    change on the module in whose first test to be set up it ran. The two trio legs this file re-asserts,
    ROMP_POSTAL_PORT (popped before every test) and ROMP_POSTAL_CLIENT_ONLY (set to "1" before every test since the
    merge of main that brought fork PR #875), are watched against the value that re-assert gives each, unset and "1"
    (MODULE_ENV_FLOORS), rather than against the snapshot: a value a module leaves after its teardown reaches the next
    module's setUpModule, setUpClass and module fixtures, and every child they spawn, before that module's first test
    to be set up re-asserts it; and against the snapshot, the re-assert's own write would read as a change on the next
    module (a module that left client-only unset had the module after it named). Every name outside the list is outside
    this check: a diff of the whole environment reds on the runner's own writes."""
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


# No test may leave the kernel's backend singleton changed, or over a directory that is gone, and the test
# that did it is the one named (2026-09-19). kernel.py builds its SdkBackend lazily: the first km._sdk() call
# constructs it over jd.STATE as it stands at that moment and caches it in km._sdk_backend for the life of
# the process (_sdk_locked), and every later reader in the worker (the chat signature's fork component, the
# registry readers, the restart routes) takes that one object. A test that points jd.STATE at a sandbox and
# reaches km._sdk(), through a card build or a route, builds the singleton over its sandbox; a tearDown that
# restores jd.STATE and removes the sandbox without touching the singleton leaves every later test's backend
# over a removed directory. Its fork_children then stats a registry that is gone, answers {} on the OSError
# and scans no registry, so a derivation counting registry stats read 0 against 39 in a module that did
# nothing wrong (tests/test_kernel_delta_send.py after tests/test_kernel.py::ViewBuilder, 2026-09-19); the
# module alone passes, and a kernel load between cause and victim hides it, since re-executing kernel.py
# resets the singleton.
#
# THE POPULATION, measured at this branch's base (2026-09-19): six classes in five modules leaked the
# singleton. ViewBuilder (tests/test_kernel.py), CostWeighting (tests/test_token_usage.py),
# BuildSessionDiffRows (tests/test_kernel_patch_rows.py), FeedWarmResolveBumpsTheLedgerRevision
# (tests/test_ledger_anchors.py), and SharedViewInBuilds and PushSurvivesOneFailedChatBuild
# (tests/test_kernel_goal_cache_wiring.py), each fixed in a commit of its own on this branch with one shape
# (ViewBuilder's before this fixture; the other four after it, one per module, found by the review round
# that ran the modules alone): save km._sdk_backend beside the saved jd.STATE and put it back where jd.STATE
# is restored, before the directory goes. The count comes from running every module ALONE with this fixture
# on, over a population that is a union, every set saved beside the list with the script that derives it:
# the 237 modules a census plugin (a scratch pytest plugin over two full -n 4 runs) saw take a road to a
# root change (a jd.STATE assignment, a jd._rebind_state call, a singleton construction, or a singleton that
# changed), the 94 that load the kernel under its shared name, the 272 whose text assigns jd.STATE or calls
# _rebind_state in process (the private-kernel modules among them included: the private name isolates the
# kernel's globals and not jd's, so they move the shared jd.STATE, and their own singletons are outside this
# fixture by the stated limit below), and the 316 the first sweep ran; 364 modules in all. The first sweep,
# over its 316 at the base, found these 4 modules red and 1 unrelated pre-existing red
# (tests/test_sdk_rate_limit_usage.py: an unrestored ROMP_SERVE_TOKEN setdefault that
# _shared_state_restored's environment check names, identical with this fixture off and byte-identical at
# the base); the sweep repeated over all 364 after the fixes (2026-09-19) was green alone except that one. The
# full-suite census saw
# none of the five: an earlier first builder in every worker made their builds cache hits. A green suite run
# is therefore no evidence a module is clean; the module-alone sweep is the measurement, and the review
# round that found the four ran the modules that way.
# THE ROAD EACH FIGURE WAS TAKEN ON, since the two families came from opposite roads. Every module-alone
# figure above (the 316-module first sweep, the 364-module sweep repeated after the fixes, and the per-module
# triage counts behind them) was taken on the missing road, each module alone on a box venv without the SDK:
# the test venv's interpreter has no claude_agent_sdk, and a module run alone does not import
# tests/test_host_transport.py; that module is the one exception in the union, since it puts the venv on
# sys.path itself. Every full-run figure above (the two full -n 4 census runs and their 237-module set, and
# "the full-suite census saw none of the five") was taken on the SDK-importable road: when claude_agent_sdk
# is not importable, tests/test_host_transport.py puts the box's SDK venv on sys.path at import, and every
# xdist worker imports every collected module, so a full run here takes that road. CI's Python cells take
# the importable road since #872 installed the SDK in each, so no CI run of the suite is a missing-road
# datum. The figures in this fixture's own tests (tests/test_sdk_singleton_ratchet.py) carry no inherited
# road: each scratch head forces its road.
#
# THE TRANSITION MODEL. The fixtures below read the singleton at fixed moments and judge what changed
# between two reads, never the after value on its own: an absolute read of the after value (the first form
# of this fixture) failed every test that merely INHERITED a singleton over a removed directory, each with
# a false accusation and a remedy it could not act on, and buried the one cause under the tests that
# followed it in the worker: one cause and 193 inheritors on the first full run, a full run here and so on the
# SDK-importable road, THE ROAD EACH FIGURE WAS TAKEN ON above. Three windows:
#   * the test: a function-scoped autouse fixture reads before the test and after its own teardown
#     (unittest's tearDown runs inside the call phase, and the test's requested fixtures tear down before
#     this one, so their restores are seen) and fails the test whose own transition made the bad state;
#   * the class and module boundaries: a class-scoped and a module-scoped autouse fixture read at the
#     scope's start (before setUpClass or setUpModule) and at its end (after tearDownClass or
#     tearDownModule; pytest reports a failure there as an ERROR at the scope's last test) and fail the
#     scope whose setup or teardown made the bad state, naming the boundary;
#   * the setup before a test: a singleton found over a gone directory that no verdict has named yet was
#     made by something that escaped every window (import-time code, or a leak from before the fixture
#     was armed) and is reported ONCE per worker, at the first test that meets it, worded as inherited,
#     with no remedy addressed to that test; every later test that inherits the same object is quiet.
#     The report is computed at the setup and raised after the test's own teardown, beside its own verdict
#     if it has one, so the test runs and its own transition is still judged (the first form failed the
#     setup, and one test per worker lost its run whenever a leak escaped every window). The same report,
#     at the worker's FIRST test window only, covers a real backend over a directory that stands but is not
#     jd.STATE AS THE MODULE BOUNDARY'S START READ RECORDED IT, and only when that backend IS the object that read
#     found (_SDK_MODULE_START, compared by identity, never by state_dir or class). The premise holds at that
#     START READ, not at the window: when the module boundary reads, only import-time code and any fixture of a
#     scope wider than the function has run (pytest collects every module before the first test runs; a session-
#     or package-scoped fixture sets up before the module boundary's start read, and setUpModule, setUpClass and
#     a module- or class-scoped fixture after it, the order a scratch run showed), so the identity term and the
#     start read's reference make the window's report a statement about that read: a singleton the start read
#     saw over a root other than the jd.STATE it recorded is import-time code's or such a fixture's build over a
#     root that is not the run's, or its move of jd.STATE after the build, left in place (the wording names both
#     causes and both shapes), while one the start read did NOT see was installed by the module's or a class's
#     own setup and is left unnamed here, so the boundary that brackets the install judges it, names the scope
#     and prints the sandbox remedy; and a jd.STATE the window finds moved from the start read's is a scope
#     setup's move for its tests (K.One's shape), not a leak, so the window's own jd.STATE is never the reference
#     (compared against it, the kernel's own import-time build over the run root got the report, blaming import-time
#     code for a build or a move that did not happen, whenever setUpModule or setUpClass moved jd.STATE for its
#     tests). Before the identity term the report fired on the setup's object too, blamed import-time code, gave
#     no remedy, and its naming silenced the boundary that would have been right. A missing module start read
#     refuses the report. Later windows do not apply that test: a legitimate first build followed by a STATE move
#     the judge fixture names leaves the same picture, and a test window or a boundary made it, where it was
#     judged. The first window spends the flag whether or not it takes the report, and never defers it: a
#     report deferred to a later window would fire where a test body has run, with its premise sentence
#     ("before any test in this worker has run") false, a wrong attribution in place of a silence. THE REFUSAL
#     (_sdk_swapped): when the slot at the worker's first window does not hold the object the module start read
#     found (the identity term fails), and that read's object is a real backend over a directory that stands and
#     is not the jd.STATE it recorded (an import-time or wider-scoped fixture's build over a kept root, met first
#     by a class that swapped the singleton out around its tests, K.Two's shape: saved, reset, put back), the
#     window raises a refusal in the report's place, at the moment the flag is spent: the leak is named from the
#     start read's fields (the object, its root and jd.STATE at that read, recorded before the swap), the slot's
#     value at the window is said, the swap is attributed to a module or class setup between the two reads
#     without naming it, no test is accused and no scope is named, since which test will start under the object,
#     and whether it is put back, cannot be said there, and the cause family is the kept-root report's. A start
#     read's object over the run root is no leak and gets no refusal. One over a gone directory is refused too,
#     under the gone wording and with the cause family narrowed to what could have run before the start read,
#     whatever its root: the swapping scope may never put the object back, and then no window starts under it,
#     the gone report never fires, and the scope's boundary verdict names the swap and not the object's origin
#     (S10); when the scope does put it back, the test that then starts under the object carries the gone report
#     as well, two lines on two items each saying what the other does not (S9), the completes-a-leak pattern
#     below, and that report names the object as the one this worker's first window refused to attribute, the
#     link keyed on the object and not on its rendered path, which a repoint between the two reads changes (S9B).
#     The boundary verdict of a scope that found the refused object and ended on another value carries a clause of
#     its own with the same key (_sdk_found_refused, on the start-to-end judgment alone, the road whose rendered
#     before value IS the object the scope found): in S10 One's verdict on the swap, beside the refusal in One.a's
#     one teardown, says the object it found is the one the refusal named; in S10B setUpModule repoints the object
#     between the module start read and One's reads, so the refusal renders the root the start read recorded and the
#     verdict the live one, two paths for one object, and the clause is still there, keyed on the object. The refusal
#     marks nothing on _SDK_REPORTED: no later window takes the kept-root report, and a mark would silence that later
#     gone report; the fixture records the refused object on _SDK_REFUSED instead, the list both links read. The
#     fixture's tests pin it, every case whose outer class reads the refusal's line or a link clause, present or
#     absent, through one of that module's named copies of these texts, by a reference in the class, in a
#     module-defined base other than _NestedRun, or in a function that module defines as a statement of its own
#     level or under a module-level if or try, referenced from there, directly or through other such functions,
#     each reference a name resolved in the scope it is read in to the module's declaration, so a local spelled
#     like one is none, the names derived there from this file's texts by refusal_text_names,
#     a roster derived from the classes and held equal to them both ways by
#     TheCaseRostersNameEveryCase in tests/test_sdk_singleton_ratchet.py, whose failure names the ids missing here
#     and the ids here with no class
#     (S7, beside S6, the same leak with no swapping class, reported as inherited; S7B, the refusal as the first
#     window's and no later one's; S8, the run-root shape, no refusal; S9 and S10, the gone shape, the object put back
#     and not, each pair linked at the object; S11, the refusal's roots from the start read's recorded fields; S12, a
#     real object in the slot at the window; S13, the named-object guard; S9B and S10B, each pair with the object
#     repointed between its two lines, linked at the object; S14, a second gone object after the refusal, its report
#     without the link clause; S10C, the refused object found by a class whose verdicts render other objects, its
#     verdicts without the boundary's clause; M, verdicts with no refusal in the run, none with the clause; E, a gone
#     report on an import-time leak with no refusal before it, its link clause absent; U and V, the same read on a
#     leak a setUpClass or a setUpModule completed; T, a first window whose start read saw None over a setUpClass
#     build, no refusal; S15, a test's own verdict on the refused object without the clause and the module end's
#     start-to-end verdict with it; and S16, the scope that found the refused object ending on the reload road, its
#     verdict without the clause).
# Three module-level lists of STRONG references (identity membership; strong so an id is never reused by a
# later object) keep the kinds of naming apart. Every object a VERDICT names (a test's own, a boundary's)
# goes on _SDK_NAMED, the list the boundary's quiet-on-a-named-object rule consults. Every object the
# INHERITED report named goes on _SDK_REPORTED, and the report is silent on an object in either list, which
# is what makes "once" work (under xdist, once per worker process). Every object the first window's REFUSAL
# named goes on _SDK_REFUSED, which silences nothing: the gone report on an object it holds, and the start-to-end
# boundary verdict of a scope that found one, say it is the object the refusal named, so the two lines are linked
# at the object, by identity (a gone object of another scope's making after the refusal carries no such clause,
# S14; a boundary verdict on a found object no refusal named carries none, S10C, M). THE RULE, which both links
# follow and any later one must: ANY PAIR OF LINES NAMING ONE OBJECT IS LINKABLE BY IDENTITY, NEVER BY A RENDERED
# PATH. A rendered path is not an identity: one object renders two paths when a repoint falls between the two
# lines' reads (S9B, S10B), and two objects render one path when one is rebuilt over the other's directory; so a
# link is membership on a list of strong references (_sdk_refused), read on the object the linked line RENDERS
# (the gone report's own object; the start-to-end verdict's before value, the object the scope found), and a
# third pair, should one arise (a test's own verdict naming the refused object, say), is linked the same way,
# never by matching text. The boundary never consults
# _SDK_REPORTED: an inherited report says what a test did NOT do, not what its scope did, so a class or
# module setup that completes a leak (builds, restores jd.STATE and removes the root before any test) yields
# two error lines for one leak, the inherited gone report on the scope's first test and the boundary
# verdict, naming the scope with the sandbox remedy, on its last. With one list the report's naming silenced
# the boundary and the leak was never attributed to the scope.
#
# WHAT ONE READ RECORDS (_sdk_read): the value in the shared kernel's slot (vars(km)["_sdk_backend"]),
# the marker (the function object kernel.py defines as _sdk_locked; a re-execution replaces it; None when
# no module has loaded the kernel under its shared name), the value's state_dir as text, os.path.isdir
# of it (a regular file at the path is False, on purpose: a backend over a file is as gone as one over
# nothing), and km.jd.STATE as text, the reference root. Only the kernel loaded under its SHARED name is
# read: a kernel a module loads under a private name (load_source under romp_kernel_<x>) has an
# _sdk_backend of its own, so a lazy build under a rebound state through that handle lands there and the
# shared singleton stays untouched (the browser-driven served modules load their kernels this way); the
# private name isolates the kernel's globals and NOT jd's, since judge.py loads under its shared name
# even when the kernel is private, so a test that assigns jd.STATE through a private kernel handle is
# moving the shared judge state (_shared_state_restored's concern, not this one's). A private kernel's own
# dangling singleton is outside this fixture, a stated limit, and what it leaves unprotected is this fixture's
# own defect class on a private name: a private-name kernel's dangling backend over a removed directory that
# a sibling file reads and gets the silent empty-registry answer this fixture exists to stop. It is live
# today: romp_kernel_mc is loaded by three files (tests/test_kernel_interrupt_machine_cut.py,
# tests/test_kernel_msgcaption.py and tests/test_model_catalog.py), the first file's _FeedHarness leaves its
# backend over a removed TemporaryDirectory, and two of the three read the dangling object, the machine-cut
# file's own later tests and the caption file's timeline builds (build_timeline's fork_children, the reader
# the incident above names); measured 2026-09-19 over the three files in one run, on the missing road (none of
# the three is tests/test_host_transport.py), 90 of 108 teardowns end with that one object over a removed root
# (33, 5 and 52 by file) and the catalog file reads it zero times;
# nine private names are shared by two or three files each. The blocker, and the order: the same rule
# looped over every sys.modules name starting with romp_kernel (round 1's proposed fix) is the arm that would
# cover it, and the loop cannot land here because the private-kernel harnesses carry 90 or more pre-existing
# teardown leaks (the 90 above are one name's, on the missing road; the round-1 refuters counted 574 would-fail
# outcomes over the 18 files that then shared a private name, their count, its road not recorded: a teardown's leaving a
# dangling backend does not depend on the road, since SdkBackend constructs on both), so their save-and-restore
# product code lands first, then the
# ratchet's private-kernel arm.
#
# THE JUDGMENT (_sdk_judge), same marker: the same object is a pass, unless its state_dir text differs
# between the two reads, the test having REPOINTED the singleton it found (the readers hold the object and
# read its state_dir on every registry scan, so a repoint to a root that stands moves every later test's
# registry root as surely as a rebuild over it: named with the changed wording, both sides rendered from the
# reads' recorded text since the live attribute shows the after path on both, the gone clause when the new
# path is not a directory, and a remedy of its own, _SDK_REMEDY_C, put the state_dir back), or its
# directory was present at the before read and is not at the after read, the test having removed the
# directory under the singleton it found. A removal never changes the text, so the two are disjoint and the
# text comparison comes first. A different value is a leak, with TWO allowances derived from the transition,
# never from a list of test names. (1) None before and, after, the kernel's own class (type module romp_sdk_backend,
# qualname SdkBackend: NOT isinstance, which a shared-name reload of sdk_backend.py breaks, since
# load_source re-executes into the same module name and the class object changes while a backend built
# before the reload keeps the old one; 11 test modules load romp_sdk_backend under the shared name) whose
# state_dir equals jd.STATE AT THE TEST'S START and is a directory: the worker's lazy first build of the
# singleton under the root the test inherited, the kernel's own design, leaving nothing dangling. The
# reference is the inherited root because it is the one value the test could not have made, and equality
# proves the build used it: a real backend's state_dir IS the root it was built over, by construction
# (kernel.py's _sdk_locked constructs sbmod.SdkBackend(jd.STATE, ...) and SdkBackend.__init__ stores
# Path(state_dir)), so no wrapper on the build is needed to learn the build root (the census's wrapper on
# _sdk_locked in the module dict changes the marker function's identity and is not a shape for a
# production fixture). jd.STATE AFTER the test would admit a first build over a sandbox the test left
# jd.STATE pointed at (the singleton agrees with the state it moved); requiring both before and after
# would refuse a legitimate first build followed by a STATE move the judge fixture already names. WHICH
# test performs the first build is a property of the run (the xdist scheduler, the subset selected, the
# module order), not of the test: the census that found ViewBuilder saw three first builders across four
# workers, a different test on each, so a name list could never be right. A look-alike over that same
# root (a test's class named SdkBackend, a SimpleNamespace, a MagicMock) is refused: installed as the
# worker's first value it would be inherited by every later test, and the class check is what refuses
# it. A value that is not the kernel's class is rendered without the gone clause: the clause says a
# state_dir is NO LONGER a directory, true of the kernel's own class alone (its state_dir is the directory
# it was built over), and false of a MagicMock's attribute or a SimpleNamespace's string, which never was
# one; so the clause on a changed value is gated on the class check as well as on isdir. (2) None before
# and False after: the kernel's own unavailable outcome (_sdk_locked's except branch
# sets False when the backend cannot be built), which the test did not choose. Everything else is a leak:
# a test that installs a fake or a rebuilt backend and puts back the OBJECT it found is quiet; one that
# puts back an equal backend (the same state_dir, another object) is not, because the readers hold the
# object, its threads and its registry state, not its path, and its message says so. A reference root
# that cannot be read (km.jd.STATE unreadable) grants no allowance: the fixture fails and says so (not
# constructible today, since the kernel always binds jd; unverified defaults to the restricted side).
#
# THE REMEDY, one per road (the message shape is "<who> <clause>. Fix: <remedy>"). The sandbox road, when
# the value left is the kernel's own class over a root that is not the reference or is not a directory:
# save km._sdk_backend before moving jd.STATE and put it back where jd.STATE is restored, before the
# directory is removed (setUp and tearDown, or setUpClass and tearDownClass when the class moves it). The
# object road, everything else (a None, a False, a fake, a rebuild over the same root): put back the
# object the test found, None or False included, not an equal one. The repoint road, the same object with
# its state_dir text changed: put the singleton's state_dir back where it was found. The first form printed
# the sandbox remedy on every road, so a test that left a None was told to save the singleton before a
# sandbox that did not exist.
#
# MARKER CHANGED (_sdk_judge_reload): the test re-executed kernel.py into the one module object (a
# different function in the slot), loaded the shared kernel for the first time in this worker (None, then
# a function), or popped it from sys.modules (a function, then None: the read gives None). The before
# value is stale by construction (the re-executed module's slot started at None), so only what the test
# LEFT is judged: None or False pass; the kernel's own class over jd.STATE with that directory present is
# the lazy build over the loader's root and passes; the kernel's class anywhere else is a build over a
# root the test made, named with the re-execution wording (and the gone clause when its directory is not
# one); anything else is a value the test left. The reference on this road is jd.STATE at the AFTER read:
# the reload re-bound STATE from the environment as it stands, which other modules' import-time writes
# decide, so the root the test inherited is stale here. A None marker before is a first load, never an
# exemption: a test that loads the shared kernel itself and then leaves the singleton over a sandbox it
# keeps is FirstBuildOverAKeptSandbox's leak by another road, and the first form of this fixture let it
# through (it compared nothing when the marker changed, and the surviving gone check misses a directory
# that stands). Stated limit: a test that reloads, moves jd.STATE, builds and LEAVES jd.STATE moved passes
# this fixture, since the singleton agrees with jd.STATE as left; that is a STATE leak, and
# _shared_state_restored's reload branch shares the limit by design (it compares no values after a
# re-execution). No test does this today.
#
# THE BOUNDARY (_sdk_judge_scope): with S = the scope's start read, L = the last read anywhere before the
# end and E = the end read: E the same object as L with its state_dir text changed is the teardown
# repointing the singleton its last test left, and E the same object as L with its directory present at L
# and gone at E is the teardown removing the directory under it, both named before the quiet rules and even
# when the object was already named, because the state got worse inside the teardown; E the object S found
# is a restore, a pass, unless the state_dir text S recorded is not E's (put back repointed) or S saw its
# directory and E does not; E the object L left and already named is a pass (the test that made it was
# judged); otherwise S -> E is judged as a test transition with S's jd.STATE as the
# reference (the scope's own setUpClass moved jd.STATE, a test built under it, allowed at its own window
# because it inherited that root, and the scope did not put the singleton back: the scope is the author);
# and E different from both S and L is the teardown itself installing a value, judged the same way. The
# S -> E judgment alone carries the link clause to the first window's refusal (_sdk_found_refused): its before
# value is the object S found, the object the clause names; the other roads render other objects or end on the
# found one, and carry none. Before that S -> E judgment the boundary yields to the tests' own windows: the
# function fixture records
# every test window that changed the slot (_SDK_WINDOWS: the before and after values and the reference the
# window was judged against; cleared at each module end, since no later scope starts before that read),
# and when the first such window inside the scope started from the value S found, the last left the value
# E holds, and that last window's reference is S's jd.STATE, every step from S to E was a test's, judged
# where it happened, and the boundary returns None. Without it a test's accused reset to None or False (a
# value _sdk_name skips, so the named rule cannot cover it) or an allowed lazy rebuild after an accused
# reset was re-attributed to the class and module boundary, sending the reader to a tearDownClass or
# tearDownModule that does not exist; in the rebuild shape the boundary's verdict landed as an ERROR on
# the innocent test that made the allowed rebuild (2026-09-19). K.One is the counter-case: its build's
# reference is the class root setUpClass moved jd.STATE to, not S's, so the class stays the author. The
# module end runs after the class end, so a class-end verdict names the object and the module end is
# quiet on it. Cost: four dict lookups (the kernel module, its slot, its marker, its jd), two getattr and
# one isdir per read; two reads per test, two per class and two per module, plus one list scan per
# boundary over the module's changing windows (a handful in any module: net changes of the slot are rare).
_SdkRead = collections.namedtuple("_SdkRead", "be marker sd isdir jd_state")
_SdkWindow = collections.namedtuple("_SdkWindow", "seq before after ref")
_SDK_LAST = _SdkRead(None, None, None, None, None)     # the last read anywhere in this worker (the boundary's L)
_SDK_READS = 0                                         # reads so far in this worker; a scope keeps the count at its start read
_SDK_WINDOWS = []                                      # the test windows that changed the slot since the module started
_SDK_FIRST_WINDOW = True                               # no test window has run yet in this worker; the kept-root report is taken
                                                       # at this window only, and only for the module start read's object, against
                                                       # the jd.STATE that read recorded (at that read only import-time code and
                                                       # any fixture of a scope wider than the function has run); when the slot
                                                       # does not hold that object here, the refusal (_sdk_swapped) is consulted
                                                       # in its place and taken under its own guards (a real backend neither list
                                                       # has named, over a directory that is gone or that stands and is not the
                                                       # jd.STATE that read recorded), and the flag is spent either way, never
                                                       # deferred
_SDK_MODULE_START = None                               # the current module boundary's start read (_SdkRead): the first-window
                                                       # kept-root report's object and reference root
_SDK_NAMED = []                                        # strong references to every object a verdict named (a test's own, a boundary's)
_SDK_REPORTED = []                                     # strong references to every object the inherited report named
_SDK_REFUSED = []                                      # strong references to every object the first window's refusal named:
                                                       # the gone report's (_sdk_inherited) and the start-to-end
                                                       # boundary verdict's (_sdk_found_refused) link to that line, by
                                                       # identity; silences nothing
_SDK_REAL = ("romp_sdk_backend", "SdkBackend")
_SDK_GONE = ", whose state_dir is no longer a directory"
_SDK_REMEDY_A = ("A test that reaches km._sdk() under a sandboxed jd.STATE builds the kernel's backend singleton over the "
                 "sandbox and every later test's backend reads that root: save km._sdk_backend before moving jd.STATE and "
                 "put it back where jd.STATE is restored, before the directory is removed (setUp and tearDown, or "
                 "setUpClass and tearDownClass when the class moves it).")
_SDK_REMEDY_B = ("Put back the object the test found, None or False included, not an equal one: the kernel's readers hold "
                 "the object, its threads and its registry state, and a None makes the next reader rebuild over whatever "
                 "jd.STATE is at that moment.")
_SDK_REMEDY_C = ("Put back the singleton's state_dir where it was found: the kernel's readers hold the object and read its "
                 "state_dir on every registry scan, so a moved state_dir moves every later test's registry root.")
_SDK_LIVE = object()                                   # _sdk_singleton_text: render the live state_dir attribute


def _sdk_read():
    """One read of the kernel's backend singleton under its shared name: (value, marker, state_dir text, isdir,
    jd.STATE text), every field None when the kernel is not loaded as romp_kernel; recorded as the worker's last
    read."""
    global _SDK_LAST, _SDK_READS
    km = sys.modules.get("romp_kernel")
    if km is None:
        rec = _SdkRead(None, None, None, None, None)
    else:
        d = vars(km)
        be = d.get("_sdk_backend")
        sd = None
        if be is not None and be is not False:
            p = getattr(be, "state_dir", None)
            sd = None if p is None else str(p)
        jd_state = getattr(d.get("jd"), "STATE", None)
        rec = _SdkRead(be, d.get("_sdk_locked"), sd, None if sd is None else os.path.isdir(sd),
                       None if jd_state is None else str(jd_state))
    _SDK_READS += 1
    _SDK_LAST = rec
    return rec


def _sdk_is_real(be):
    """The kernel's own class, by module and qualname: load_source re-executes sdk_backend.py into the same module
    name, so an isinstance against the class loaded now would refuse a backend built before a shared-name reload."""
    t = type(be)
    return (t.__module__, t.__qualname__) == _SDK_REAL


def _sdk_named(be):
    """Whether a verdict (a test's own, a boundary's) has named the object: the boundary's quiet rule reads this alone."""
    return any(x is be for x in _SDK_NAMED)


def _sdk_name(be):
    if be is not None and be is not False and not _sdk_named(be):
        _SDK_NAMED.append(be)


def _sdk_reported(be):
    """Whether the inherited report has named the object; with _sdk_named, that report's once-per-worker rule."""
    return any(x is be for x in _SDK_REPORTED)


def _sdk_report(be):
    if be is not None and be is not False and not _sdk_reported(be):
        _SDK_REPORTED.append(be)


def _sdk_refused(be):
    """Whether the first window's refusal named the object: the gone report's and the start-to-end boundary verdict's
    link clauses read this, by identity, never by a rendered path (THE RULE in the comment above: a repoint between two
    reads renders two paths for one object), each on the object its own line renders."""
    return any(x is be for x in _SDK_REFUSED)


def _sdk_refuse(be):
    if be is not None and be is not False and not _sdk_refused(be):
        _SDK_REFUSED.append(be)


def _sdk_singleton_text(be, sd=_SDK_LIVE):
    """The value as "<class> over <state_dir>", None and False said in words. `sd` is the state_dir text to render: the
    live attribute by default, or a read's recorded text, since the same object's state_dir can have been repointed
    between two reads and the live attribute would then show the after path on both sides of the transition."""
    if be is None:
        return "None (not built)"
    if be is False:
        return "False (the build failed)"
    state_dir = getattr(be, "state_dir", None) if sd is _SDK_LIVE else sd
    t = type(be)
    name = "SdkBackend" if _sdk_is_real(be) else "%s.%s" % (t.__module__, t.__qualname__)
    return "%s over %s" % (name, "no state_dir" if state_dir is None else state_dir)


_SDK_INHERITED_TAIL = ("This test did not make it: %s, outside every window the singleton fixtures judge; reported once per "
                       "worker, at the first test that meets it, after that test's own teardown (so the test runs and its own "
                       "transition is judged too), and the tests after it that inherit the same object are not accused.")


def _sdk_inherited(before, start):
    """The once-per-worker report on a singleton state no window made, or None: a real backend over a directory that is
    gone, at any test; or, with `start` (the module boundary's start read, passed only at the worker's FIRST test window
    AND when the object is the one that read found, else None), a real backend over a directory other than jd.STATE AS
    THAT READ RECORDED IT, which only import-time code or a fixture of a scope wider than the function could have made:
    at the start read nothing else has run, and the identity term with the start read's reference make the window's
    report a statement about that read (jd.STATE at the window itself may have been moved since by setUpModule,
    setUpClass or a module- or class-scoped fixture, which is no leak; compared against the window's jd.STATE, a
    legitimate import-time build over the run root got the report whenever a scope setup moved jd.STATE for its tests);
    an object the start read did not see was installed by the module's or a class's own setup, which that scope's
    boundary judges. Silent on an object either list has named (_sdk_named, _sdk_reported). A gone report on an object
    the worker's first window REFUSED (_sdk_refused: _sdk_swapped's object, recorded by the fixture when the refusal is
    taken) opens its tail by saying it is that object, so the two lines are linked at the object and not at the rendered
    path, which is no identity and which a repoint between the two reads changes (S9, S9B); membership is by identity, so a
    gone report on an object no refusal named carries no clause whatever refusal the worker took before it (S14)."""
    be = before.be
    if not _sdk_is_real(be) or _sdk_named(be) or _sdk_reported(be):
        return None
    if before.isdir is False:
        link = (("It is the object this worker's first test window refused to attribute: that refusal names its origin, "
                 "this line the test that lives under it. ") if _sdk_refused(be) else "")
        return ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that no longer exists: %s. %s%s"
                % (_sdk_singleton_text(be), link,
                   _SDK_INHERITED_TAIL % "an earlier test, a class or module setup or teardown, or import-time code did"))
    if start is not None and before.sd != start.jd_state:
        return ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that is not jd.STATE, before "
                "any test in this worker has run: %s, jd.STATE %s at this module's start read. %s"
                % (_sdk_singleton_text(be), start.jd_state,
                   _SDK_INHERITED_TAIL % "import-time code did, or a session- or package-scoped fixture did (one that set up "
                   "before this module's own reads), building the singleton over a root that is not the run's, or moving "
                   "jd.STATE after the build and leaving it there"))
    return None


_SDK_SWAPPED_HEAD = ("opens the worker's first test window, and this module's start read had found the kernel's backend singleton "
                     "(km._sdk_backend) over a directory that is not jd.STATE, before any test in this worker has run")
_SDK_SWAPPED_GONE_HEAD = ("opens the worker's first test window, and this module's start read had found the kernel's backend singleton "
                          "(km._sdk_backend) over a directory that no longer exists, before any test in this worker has run")


def _sdk_swapped(start, before):
    """The first window's refusal, or None: consulted only at the worker's FIRST test window and only when the kept-root
    report's identity term fails there (the slot does not hold the object the module boundary's start read found). Taken
    when that start read (`start`) found a real backend in a state no test made, over a directory that stands and is not
    jd.STATE as that read recorded it (the kept-root picture) or over a directory that is gone, which at that read only
    import-time code or a fixture of a scope wider than the function could have made; the slot's value at the window
    (`before`) is what a module or class setup (setUpModule, setUpClass, or a module- or class-scoped fixture, the
    actors between the two reads) swapped in. The leak is named from the start read's fields, both objects rendered from
    the reads' recorded state_dir: the start read's because the live attribute may have been repointed since (S11, a
    class that repoints the object before swapping it out), the window's for one convention, since nothing runs between
    the before read and this render, so its recorded text and the live attribute agree by construction and no run can
    tell them apart (annotated at the call, not a cell); no test is accused and no scope is named, because which test
    will start under the object, and whether it is put back, cannot be said at this window, and the premise sentence,
    true here, would be false at any later one (the flag is spent with this line, never deferred: a deferred report
    would fire where a test body has run, a wrong attribution in place of a silence). Two heads, the inherited report's
    two shapes: the kept-root wording and cause family for the standing directory, the gone wording with the cause
    family narrowed to what could have run before the start read for the gone one, whatever its root. The gone shape is
    refused here rather than left to the gone report because the swapping scope may never put the object back, and then
    no window starts under it, the gone report never fires, and the scope's boundary verdict names the swap and not the
    object's origin; when the scope does put it back, the later test that starts under the object carries the gone
    report as well, two lines each saying what the other does not, and the later line says it is the object this window
    refused, keyed on the object (the rendered path is not an identity, and a repoint between the two reads changes it;
    S9B). Silent when the start read's object stands over jd.STATE as it recorded it (no leak); on an object a verdict
    has named (_sdk_named, reachable: a class or module scope that touches the singleton and then skips or errors before
    any function window runs files a naming verdict while the flag is still armed, the boundary fixture reading at the
    scope's first item and the flag spent only in the function fixture; S13, a module pair); and, as a belt, on one the
    inherited report has named (_sdk_reported, empty at this window by construction: the one site that fills that list,
    the function fixture's report line, runs after this refusal is computed in the same first window, and no earlier
    window exists in the worker). The refusal marks nothing on _SDK_REPORTED: no later window takes the kept-root
    report, so a mark would change nothing there, and it would silence that later gone report; the fixture records its
    object on _SDK_REFUSED instead, the list the gone report's link clause reads, as does the boundary's: the scope
    that found the refused object and ended on another value says, on its start-to-end verdict, that the object it
    found is the one this window refused, the same key (_sdk_found_refused; S10, S10B). This function stays pure, text
    or None, as _sdk_inherited is."""
    be = start.be
    if not _sdk_is_real(be) or _sdk_named(be) or _sdk_reported(be):
        return None
    if start.isdir is False:
        head, cause = _SDK_SWAPPED_GONE_HEAD, ("building the singleton over a directory since removed, or removing the directory "
                                               "it was built over")
    elif start.sd == start.jd_state:
        return None
    else:
        head, cause = _SDK_SWAPPED_HEAD, ("building the singleton over a root that is not the run's, or moving jd.STATE after the "
                                          "build and leaving it there")
    return ("%s: %s, jd.STATE %s at that read. The slot does not hold that object at this window (it holds %s): a module or "
            "class setup that ran between the two reads (setUpModule, setUpClass, or a module- or class-scoped fixture) swapped "
            "it out, so this test does not start under it, and which test will, or whether it is put back, cannot be said here; "
            "no test is accused and no scope is named. Import-time code did, or a session- or package-scoped fixture did (one "
            "that set up before this module's own reads), %s; a swap left in place is judged at its own scope's end."
            % (head, _sdk_singleton_text(be, start.sd), start.jd_state,
               _sdk_singleton_text(before.be, before.sd),   # the recorded text for one convention: the before read and this
               cause))                                       # render are one fixture call with no test code between, so the live
                                                             # attribute agrees with it by construction; no run can tell them apart


def _sdk_remedy(after, ref):
    """The sandbox road's remedy when the value left is the kernel's own class over a root that is not the reference
    or is not a directory; the object road's otherwise."""
    if _sdk_is_real(after.be) and (after.sd != ref or not after.isdir):
        return _SDK_REMEDY_A
    return _SDK_REMEDY_B


def _sdk_repointed_text(head, be, before, after):
    """The clause for the same object whose state_dir text changed between two reads, both sides from the recorded text
    (the live attribute shows the after path on both), the gone clause when the new path is not a directory."""
    return "%s: before %s, after %s%s" % (head, _sdk_singleton_text(be, before.sd), _sdk_singleton_text(be, after.sd),
                                          _SDK_GONE if after.isdir is False and _sdk_is_real(be) else "")


def _sdk_judge(before, after, ref):
    """The transition from one read to another, judged as a test's: None for a pass, else (clause, remedy) for
    the caller to frame as "<who> <clause>. Fix: <remedy>". `ref` is the root the lazy-first-build allowance
    compares the after value's state_dir with."""
    be0, be1 = before.be, after.be
    if after.marker is not before.marker:
        return _sdk_judge_reload(before, after)
    if be1 is be0:
        if before.sd != after.sd:              # the same object, repointed: the readers hold the object and read its state_dir
            return (_sdk_repointed_text("left the kernel's backend singleton (km._sdk_backend) changed after its teardown",
                                        be1, before, after), _SDK_REMEDY_C)
        if before.isdir and after.isdir is False:
            return ("left the kernel's backend singleton (km._sdk_backend) over a directory it removed: %s%s"
                    % (_sdk_singleton_text(be1), _SDK_GONE), _sdk_remedy(after, ref))
        return None
    unreadable = ""
    if be0 is None:
        if be1 is False:                       # the kernel's own unavailable outcome
            return None
        if _sdk_is_real(be1) and after.isdir:
            if ref is None:
                unreadable = "; the reference root (km.jd.STATE) was unreadable, so the lazy first build could not be allowed"
            elif after.sd == ref:
                return None                    # the lazy first build over the root the test inherited
    if _sdk_is_real(be0) and _sdk_is_real(be1) and before.sd == after.sd and after.isdir:
        after_text = "another SdkBackend over the same directory (the readers hold the object, not the path)"
    else:
        after_text = _sdk_singleton_text(be1) + (_SDK_GONE if after.isdir is False and _sdk_is_real(be1) else "")
    return ("left the kernel's backend singleton (km._sdk_backend) changed after its teardown: before %s, after %s%s"
            % (_sdk_singleton_text(be0), after_text, unreadable), _sdk_remedy(after, ref))


def _sdk_judge_reload(before, after):
    """The changed-marker road (a re-execution, a first load, or a popped kernel inside the test): the after value
    alone, judged against jd.STATE as the reload re-bound it (the after read); see the comment above for why the
    before value and the before reference are stale here."""
    be1 = after.be
    if be1 is None or be1 is False:
        return None
    head = ("re-executed the kernel (or loaded it for the first time) and left the kernel's backend singleton "
            "(km._sdk_backend) ")
    if not _sdk_is_real(be1):
        return (head + "as a value that is not the kernel's build: %s" % _sdk_singleton_text(be1), _SDK_REMEDY_B)
    ref = after.jd_state
    if ref is None:
        return (head + "over %s while the reference root (km.jd.STATE) was unreadable, so the lazy build could not be "
                "allowed" % _sdk_singleton_text(be1), _SDK_REMEDY_A)
    if after.sd == ref:
        if after.isdir:
            return None
        return (head + "over jd.STATE, which is no longer a directory: %s%s" % (_sdk_singleton_text(be1), _SDK_GONE),
                _SDK_REMEDY_A)
    return (head + "over a root that is not jd.STATE: %s, jd.STATE %s%s"
            % (_sdk_singleton_text(be1), ref, _SDK_GONE if after.isdir is False else ""), _SDK_REMEDY_A)


# The start-to-end boundary verdict's link to the first window's refusal. No period at the end: _sdk_boundary frames the
# verdict as "%s. Fix: %s", and a period inside made ".. Fix:" on the line, which the outer tests' boundary() reader
# accepted (S10 pins the single period).
_SDK_FOUND_REFUSED = ("The object this scope found is the object this worker's first test window refused to attribute: "
                      "that refusal names its origin, this line the scope at whose end the slot no longer held it, and the "
                      "value it held")


def _sdk_found_refused(verdict, start, end):
    """The start-to-end boundary verdict with its link clause when the object the scope found (`start.be`, the verdict's
    rendered before value) is one the worker's first window refused to attribute (_sdk_refused: membership by identity
    on _SDK_REFUSED, never a rendered path), else the verdict as given. The refusal named the object's origin and no
    scope; the verdict names the scope at whose end the slot no longer held the object, and the value it held then; so
    the two lines name one object and the clause links them AT THE OBJECT (S10, the swap never undone, the verdict
    beside the refusal in One.a's one teardown; S10B, the object repointed by setUpModule between the module start read
    and the class's reads, two paths for one object, the clause still there). The tail says only what this road always
    knows: it is reached when the scope ends on a value that is not the one it found, whether the scope's own setup
    swapped the object out (S10's One) or a test inside it did and the scope's end merely found the slot changed (S15's
    module end, after Two.a reset the slot: a tail naming the scope as the one that swapped the object out was false
    there). Keyed on the object THIS ROAD RENDERS: the start-to-end judgment renders the found object as its before
    value, so the clause is true of the line it rides; a verdict on a found object no refusal named carries none
    (S10C's Two, with a refusal standing in the worker; M, with none). Off the changed-marker road: the reload judgment
    renders the after value alone and no before, so a clause there would name an object the line does not show (S16:
    the scope that found the refused object ends on a re-execution and a build over a sandbox, and its reload verdict
    carries no clause; with the term dropped it would, derive: boundary-link-marker-term-dropped)."""
    if verdict is None or end.marker is not start.marker or not _sdk_refused(start.be):
        return verdict
    return ("%s. %s" % (verdict[0], _SDK_FOUND_REFUSED), verdict[1])


def _sdk_judge_scope(start, last, end, windows):
    """The class or module boundary's verdict from its start read, the last read before its end, its end read, and the
    test windows inside the scope that changed the slot (oldest first). Five roads render a verdict. The last-object
    roads (the teardown repointed, or removed the directory under, the object its last test left) render that object,
    the last read's; the put-back roads (the scope ends on the object it found, repointed or over a gone directory)
    render the found object on both sides; the start-to-end judgment (_sdk_judge from the start read to the end read,
    one call site, reached when the scope ends on a value that is neither its last test's nor the one it found, or on
    its last test's value that no window chain and no verdict accounts for) renders the found object as its before
    value and the value left as its after. The link clause to the first window's refusal (_sdk_found_refused) rides
    the start-to-end judgment ALONE, keyed on the object it renders as before, the one the scope found. The four other
    roads carry no clause: the last-object roads render the object the last test left, the found one only when no test
    changed the slot (S10C's One finds the refused object, swaps it out, its test builds and its teardown repoints the
    build: the verdict renders the build alone, and a clause keyed on the found object would name one the line does not
    show; a scope whose tests leave the found object and whose teardown repoints it renders the found object, and there
    the tail would be false too, the teardown having repointed the object rather than left the slot without it), and
    the put-back roads render the found object but end on it, so the clause's tail, the scope at whose end the slot no
    longer held it, would be false there. A later case that needs a clause on one of them keys it on the object THAT
    road renders, never on start.be (THE RULE in the design comment: identity on the rendered object, never a rendered
    path). Never inside _sdk_judge, which is the function fixture's road too: a clause there would ride every
    test-window verdict whose before value is the refused object (S15's Two.a, which starts under the refused object
    and resets the slot: its own verdict carries no clause, and the module end's start-to-end verdict on the same
    change does; the cell boundary-link-in-judge moves the clause there and S15 reds)."""
    if end.be is last.be:
        if last.sd != end.sd:                  # the teardown repointed the singleton its last test left: named before the quiet rules
            return (_sdk_repointed_text("left the kernel's backend singleton (km._sdk_backend) changed after its teardown",
                                        end.be, last, end), _SDK_REMEDY_C)
        if last.isdir and end.isdir is False:
            return ("left the kernel's backend singleton (km._sdk_backend) over a directory it removed: %s%s"
                    % (_sdk_singleton_text(end.be), _SDK_GONE), _sdk_remedy(end, start.jd_state))
        if end.be is start.be or _sdk_named(end.be):
            return None
        if windows and windows[0].before is start.be and windows[-1].after is end.be and windows[-1].ref == start.jd_state:
            return None                    # the tests made the change, each judged at its own window: the boundary did nothing
    elif end.be is start.be:
        if start.sd != end.sd:
            return (_sdk_repointed_text("put back the kernel's backend singleton (km._sdk_backend) it found with its state_dir "
                                        "repointed", end.be, start, end), _SDK_REMEDY_C)
        if start.isdir and end.isdir is False:
            return ("put back the kernel's backend singleton (km._sdk_backend) it found, whose directory is gone: %s%s"
                    % (_sdk_singleton_text(end.be), _SDK_GONE), _sdk_remedy(end, start.jd_state))
        return None
    # The one start-to-end call site, the link clause's road (the first block falls through to it).
    return _sdk_found_refused(_sdk_judge(start, end, start.jd_state), start, end)


@pytest.fixture(autouse=True)
def _sdk_singleton_restored(request):
    global _SDK_FIRST_WINDOW
    before = _sdk_read()
    # The kept-root report at the first window is taken only for the object the module's own start read found (identity)
    # and against the jd.STATE that read recorded: a value installed after that read is the module's or a class's own
    # setup, judged at that scope's boundary, and a jd.STATE moved after it is a scope setup's move for its tests.
    first = _SDK_FIRST_WINDOW and _SDK_MODULE_START is not None and before.be is _SDK_MODULE_START.be
    inherited = _sdk_inherited(before, _SDK_MODULE_START if first else None)
    # The identity term failed at the worker's first window: the refusal, or None, from the start read's fields (the object
    # the report would have named, if the slot still held it). The flag is spent with it, never kept for a later window:
    # the report's premise sentence holds at this window alone.
    swapped = None
    if _SDK_FIRST_WINDOW and _SDK_MODULE_START is not None and not first:
        swapped = _sdk_swapped(_SDK_MODULE_START, before)
        if swapped is not None:
            _sdk_refuse(_SDK_MODULE_START.be)   # the object the refusal names, recorded at the moment the refusal is
                                                # taken, so the later gone report on the same object, or the
                                                # start-to-end verdict of the scope that found it, can say it is that
                                                # object (never _SDK_REPORTED, which would silence that report)
    _SDK_FIRST_WINDOW = False
    if inherited is not None:
        _sdk_report(before.be)             # reported now, so the tests after this one that inherit the object are quiet
    yield
    after = _sdk_read()
    verdict = _sdk_judge(before, after, before.jd_state)     # the root the test inherited: the one value it could not have made
    if after.be is not before.be:
        _SDK_WINDOWS.append(_SdkWindow(_SDK_READS, before.be, after.be,
                                       after.jd_state if after.marker is not before.marker else before.jd_state))
    if verdict is None and inherited is None and swapped is None:
        return
    lines = []
    if inherited is not None:
        lines.append("%s %s" % (request.node.nodeid, inherited))
    if swapped is not None:
        lines.append("%s %s" % (request.node.nodeid, swapped))
    if verdict is not None:
        _sdk_name(after.be)
        lines.append("%s %s. Fix: %s" % (request.node.nodeid, verdict[0], verdict[1]))
    pytest.fail("\n".join(lines), pytrace=False)


def _sdk_boundary(request, start, reads_at_start):
    last = _SDK_LAST
    end = _sdk_read()
    windows = [w for w in _SDK_WINDOWS if w.seq > reads_at_start]
    verdict = _sdk_judge_scope(start, last, end, windows)
    if verdict is None:
        return
    _sdk_name(end.be)
    pytest.fail("%s's class or module boundary (tearDownClass, tearDownModule or a class- or module-scoped fixture) %s. "
                "Fix: %s" % (request.node.nodeid, verdict[0], verdict[1]), pytrace=False)


@pytest.fixture(autouse=True, scope="class")
def _sdk_singleton_class_boundary(request):
    start = _sdk_read()
    reads_at_start = _SDK_READS
    yield
    _sdk_boundary(request, start, reads_at_start)


@pytest.fixture(autouse=True, scope="module")
def _sdk_singleton_module_boundary(request):
    global _SDK_MODULE_START
    start = _sdk_read()
    _SDK_MODULE_START = start              # the first-window report's object and reference root (_sdk_singleton_restored)
    reads_at_start = _SDK_READS
    yield
    try:
        _sdk_boundary(request, start, reads_at_start)
    finally:
        del _SDK_WINDOWS[:]                # no later scope starts before this read, so no boundary selects these again


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


def env_sparing_texts(env, texts) -> dict:
    """`env` (a mapping) without every entry whose value the env-value net above would rewrite one of `texts` with in a
    pytest started under it: an entry that qualifies (env_value_qualifies) and whose value alone makes redact_env_values
    change the text. For a test that asserts a literal in a child pytest's report: an inherited value whose whole text,
    or a whitespace-separated chunk of ENV_VALUE_MIN_LEN or more characters of it, appears in that literal made the
    child's report show ENV_VALUE_REDACTED in its place and the test red on a correct verdict (round 6's ruling B on the
    SDK switch cases, 2026-09-25: sudo's SUDO_COMMAND and GNU make's MAKEFLAGS carry a command line's assignment of
    the switch, and SUDO_COMMAND carries an interpreter named by its path). Keyed on the net's own two functions, not a
    copy of their rule. Returns a new dict; `env` is not changed."""
    return {name: value for name, value in env.items()
            if not (env_value_qualifies(name, value) and any(redact_env_values(t, (value,)) != t for t in texts))}


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
    # that shapes a test report joins here: the session-end thread guard's failure first (it marks a report
    # failed, and the served-tests switch and the never-skips belt act on skips only), the served-tests switch
    # next, then the never-skips belt (each message quotes the skip's reason), the redaction last, so whatever
    # any step wrote is read for values before it is printed.
    outcome = yield
    rep = outcome.get_result()
    _guard_failure_into_report(item, call, rep)
    _require_served_test_ran(item, rep)
    _require_never_skip_ran(item, rep)
    _redact_report(rep)


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    """The never-skips belt's collection half: a module-level skip (pytest.importorskip, or
    pytest.skip(allow_module_level=True)) produces a skipped CollectReport and no items, so the item hook
    above never sees it. The same flip here, on the report as it is made, turns it into a collection error,
    and pytest stops the run red ("1 error during collection"). Redaction follows in pytest_collectreport."""
    outcome = yield
    _require_never_skip_collected(collector, outcome.get_result())


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


# -- session-end thread guard (2026-09-26) -----------------------------------------------------------------------------
# A NON-DAEMON thread still running when the interpreter exits keeps its process from exiting, because the interpreter
# joins every non-daemon thread at shutdown. So does a concurrent.futures thread still running a task, WHATEVER ITS
# DAEMON FLAG: before that join the interpreter calls concurrent.futures' exit hooks, which join every thread in their
# tables (EXIT_JOIN_TABLES below), and a thread takes its daemon flag from the thread that creates it, so a pool started
# from a daemon thread has daemon workers that the hooks join all the same. Run serially, the run then hangs until the
# thread ends or CI's job cap cancels the cell, and a cancelled cell is red. Under pytest-xdist the run passes: the
# controller kills a worker still alive when the run ends, and the run's status comes from the test reports alone, so
# the fork's Linux cells lost the signal when they moved to two workers (2026-09-25). Two kinds of thread the guard
# names do not keep the process from exiting, and the guard fails on them too: an idle concurrent.futures worker and a
# thread stopped only after the check (both below). This guard restores the signal in every process that runs tests, the
# one serial process or each worker. When the process's LAST test tears down (nextitem is None), after the runner has
# finished tearing down every scope, session ones included (this implementation is a wrapper whose check follows its
# yield, so it runs after the runner's own pytest_runtest_teardown; after one that raised, only when the runner left no
# fixture for pytest to tear down later, as pytest_runtest_teardown's docstring says), each guarded thread still alive,
# every non-daemon thread and every thread in those tables, is given until one shared deadline to end, and
# the threads still alive at the deadline fail that teardown, each named with its target and its stack. Not waited for:
# daemon threads outside those tables (the interpreter's shutdown joins none of them; an atexit handler may join one,
# and the guard does not read atexit handlers), the main thread, the thread running this check, and any thread whose
# name starts with pytest_timeout, or whose target's module, or a Timer's function's module, starts with pytest_timeout.
# That exclusion exists for pytest-timeout's timer for the running test, a non-daemon threading.Timer that the plugin
# cancels and joins only after the test's protocol returns, so under CI's --timeout-method=thread it is always alive
# here.
# HOW THE REPORT REACHES THE CONTROLLER: by two channels. The first is the teardown phase's test report. A worker sends
# every test report to the controller over xdist's channel, this one included; the controller prints it as `ERROR at
# teardown of <that test>` and counts it in the run's exit status. It is the channel that fails the run, since a
# worker's exit status is not read, and a print to a worker's stdout would not be seen: that stdout goes to /dev/null.
# Two of pytest's own plugins change that report after the guard has failed the teardown: its skipping plugin makes the
# error of an xfail-marked test an xfail, which leaves the run green, and its unittest plugin puts a TestCase's second
# stored error (a body and a cleanup that both fail) into the report in place of the guard's, which then names no
# thread. So the guard records its failure in the item's stash, and this file's one pytest_runtest_makereport
# hookwrapper, which runs outside both plugins' report hooks (the order, and why it holds, are in the docstring of
# _guard_failure_into_report), marks that teardown report failed and, when it carries another outcome
# (the TestCase's error or skip, or a fixture's teardown error or skip the runner raised before the guard ran, which
# that teardown then raises), adds the guard's text after that outcome (_guard_failure_into_report); the wrapper then
# redacts the report as it redacts every report. The second is stderr: the guard writes the same text there
# (_guard_failure_to_stderr), through the same redaction, and no report hook can change it. A worker's stderr is the
# controller's, so the text reaches the log serially and under xdist; a line from the terminal reporter at session
# finish would not, since in a worker the reporter writes to that /dev/null stdout. Run serially, both print before the
# interpreter exits (stderr at the check, the error in the run's summary), so a serial cell that then hangs at exit on a
# thread still running (until the thread ends or the cap cancels the cell) names the thread in its log; an idle
# concurrent.futures worker or a thread stopped only after the check lets the process exit after the error. The test the
# error names is the process's last, where the check runs, not necessarily the one that started the thread; the thread's
# target and stack say where it came from.
# THE CAP, 10 s, from the census of 2026-09-26 on the fork's main (the full suite on 3.12 at -n 2, twice, and at -n 4;
# every third test module, 314 of 940, serially, twice each on 3.12 and on 3.14t with the GIL off). No non-daemon thread
# but pytest-timeout's timer was alive at any session end, so no exit latency could be measured there (that census read
# non-daemon threads only). The tests' own joins measured it instead: the longest time from a stop to a thread's end was
# 5.03 s, a daemon thread's end under the product's 5 s wait for a session host's hello. The longest join of a
# non-daemon thread, 2.98 s, was not an exit: it was a concurrency test's hammer threads joined as they finished their
# work, so it bounds no exit latency. The cap is about twice 5.03 s and exactly twice tests/test_thread_stop_census.py's
# BOUND_S (5 s, the longest wait that census reads as bounded). A run that leaves no thread pays nothing, since a join
# returns the moment its thread ends; a run that leaks one pays the cap once per process, then fails. A last test whose
# own teardown fails or skips (a fixture's teardown raised, and the runner went on to tear down the rest) is checked
# too, after the runner's teardown: the report carries that outcome with the guard's text after it, and under an xfail
# mark, which would make that error an xfail, stays an error. A teardown the runner stopped partway with fixtures of a
# wider scope still set up (a fixture whose node is not the session's raised, at teardown, a BaseException that is
# neither an Exception nor one of pytest's outcomes: asyncio.CancelledError or SystemExit, say) is not checked: the
# stopped node's remaining fixtures are never torn down, and those of wider scopes, and their threads, stay up until
# pytest_sessionfinish. When that node is the session's, nothing is left on the runner's stack and the guard runs.
# AFTER THE CHECK, which runs at the last test's teardown. A thread STARTED after it, in a pytest_sessionfinish or
# pytest_unconfigure hook or an atexit handler, is not checked. A thread STOPPED only after it, by a config.add_cleanup
# callback, pytest_sessionfinish or pytest_unconfigure, is checked and fails the guard, although the process would exit:
# the guard cannot tell a thread a later hook will stop from one nothing stops. The witness is the leak pins in
# tests/test_session_end_thread_guard.py: their leaked thread is released at pytest_unconfigure, the run fails, the stop
# writes a release marker, and every process that ran tests then writes its atexit marker, which the interpreter runs
# only after concurrent.futures' exit hooks and its join of the non-daemon threads have returned. Nothing in tests/
# starts or stops a thread there today: its pytest_sessionfinish and pytest_unconfigure hooks and its atexit handlers
# only remove directories, and it registers no config cleanup.
# concurrent.futures THREADS fail the guard for either of two causes. A ThreadPoolExecutor's worker (of a pool, or of an
# asyncio event loop's default executor) or a ProcessPoolExecutor's manager thread may be IDLE, in a pool left without
# shutdown or a loop never closed: no join ends it, but the interpreter wakes it at exit (threading._register_atexit),
# so it would not have hung a serial run or kept an xdist worker from exiting, and failing on it is the stricter
# reading. Or it may be BUSY, with a task still running (in the worker, or in the manager thread's pool), which
# shutdown(wait=False) and loop.close() (it shuts its default executor down with wait=False) do not end: at exit the
# process waits for that task like any other thread still running. Either cause holds for a thread of either daemon
# flag, since the exit hooks wake and join daemon ones too: the guard reads the hooks' tables (EXIT_JOIN_TABLES) and
# waits for every thread in them, and a loaded concurrent.futures module without its table fails the guard, naming the
# attribute, rather than leaving its daemon threads unread. A table whose every read raises until the deadline (another
# thread adding to it without pause) fails the guard by the table's name, and that failure names the non-daemon threads
# still alive, which need no table; the daemon threads the table would list go unnamed. The report's label names both
# causes, idle and busy; a ThreadPoolExecutor worker's stack shows which, and a manager thread's stack reads the same
# either way. A process that leaves one pays the cap once. No non-daemon one was left at a session end on main (the
# census above, which read non-daemon threads only). CI, running this guard at an earlier head of the pull request that
# made it read those tables, named one thread: an idle default-executor worker, a daemon thread, left by
# tests/test_session_move.py's fixture loops, which the same pull request fixes (that module's loop cleanup, _end_loop,
# now ends it). A run of the full suite on 2026-09-28 at that pull request's head after its merge of the fork's main
# that day (3.12, two workers, the Run pytest step's flags, -p no:anyio among them; the served-page tests skipped, the
# extension's node deps absent; the Claude Agent SDK, which CI's Python cells install since that merge, not installed)
# left none of either flag: the guard named no thread there.
THREAD_GUARD_CAP_S = 10.0
_monotonic = time.monotonic   # bound at import: a test's leaked patch of time.monotonic cannot move the guard's deadline
_enumerate = threading.enumerate    # bound at import too: a test's leaked patch of threading.enumerate cannot empty the
                                    # guard's list, and a test that patches this name reaches the guard alone
# The tables concurrent.futures' exit hooks join, as (module, attribute). The two hooks are the only functions the
# standard library registers with threading._register_atexit (3.10 to 3.14), which threading._shutdown calls before it
# joins the non-daemon threads; each joins every thread in its module's table, whatever the thread's daemon flag. The
# guard reads each table by its literal module and attribute names (_exit_join_table_reads), and an assertion there ties
# the LABELS (the pair written beside each read) to this tuple, so a label cannot drift from it; a read's own literal is
# tied to its label by execution, in tests/test_session_end_thread_guard.py's ExitJoinTables (a stand-in table put under
# each pair is the one the guard reads), not by the assertion.
EXIT_JOIN_TABLES = (("concurrent.futures.thread", "_threads_queues"),      # ThreadPoolExecutor workers
                    ("concurrent.futures.process", "_threads_wakeups"))    # ProcessPoolExecutor manager threads
# The guard's failure, in the stash of the item whose teardown it failed, for _guard_failure_into_report.
_GUARD_FAILURE = pytest.StashKey()


def _exit_join_table_reads():
    """((module, attribute), the module or None, its table or None) for each exit-join table, in EXIT_JOIN_TABLES' order:
    each module read from sys.modules by its literal name and each table read from that module by getattr with its
    literal name, since the conftest reader of tests/test_hermetic_kernel_postal.py admits getattr only with a name it
    proves to be one fixed string, and a name taken from a loop over EXIT_JOIN_TABLES is not one (the reviewer's ruling
    of 2026-09-29 09:01Z on round 2 of fork PR #894). The assertion ties those reads to
    EXIT_JOIN_TABLES, which tests/test_session_end_thread_guard.py pins: the pairs the reads are labelled with, each
    written beside its read, must equal it, or an AssertionError names both (the check also runs once when this file is
    imported, below). tests/test_session_end_thread_guard.py's ExitJoinTables ties each label to its read by execution:
    a stand-in table put under each EXIT_JOIN_TABLES pair is the one the guard reads."""
    thread_module = sys.modules.get("concurrent.futures.thread")
    process_module = sys.modules.get("concurrent.futures.process")
    reads = ((("concurrent.futures.thread", "_threads_queues"), thread_module,
              getattr(thread_module, "_threads_queues", None)),
             (("concurrent.futures.process", "_threads_wakeups"), process_module,
              getattr(process_module, "_threads_wakeups", None)))
    if tuple(names for names, _module, _table in reads) != EXIT_JOIN_TABLES:
        raise AssertionError("tests/conftest.py's session-end thread guard reads the exit-join tables %r by their literal "
                             "names, and EXIT_JOIN_TABLES is %r: the two name different tables. Point both at the same "
                             "tables (tests/test_session_end_thread_guard.py pins EXIT_JOIN_TABLES)."
                             % (tuple(names for names, _module, _table in reads), EXIT_JOIN_TABLES))
    return reads


_exit_join_table_reads()     # the tie, checked at import too: a drift fails the run before its first test


class _ExitJoinTableKeptChanging(pytest.fail.Exception):
    """_exit_joined_threads' failure for a table whose every read raised RuntimeError until the deadline passed. It is a
    pytest.fail failure, so any caller fails the same way; threads_left_at_session_end catches it to add the non-daemon
    threads still alive, which are guarded whatever the table lists."""


def _exit_joined_threads(deadline):
    """The threads concurrent.futures' exit hooks will join, whatever their daemon flags: every thread in the table of
    each EXIT_JOIN_TABLES module that is loaded, each module and table read by its literal names
    (_exit_join_table_reads, whose assertion ties the LABELS beside each read to EXIT_JOIN_TABLES, while
    tests/test_session_end_thread_guard.py's ExitJoinTables ties each read to its label by execution). This file imports
    concurrent.futures.thread, so its table is always read; a process that never loaded concurrent.futures.process has
    no ProcessPoolExecutor. A loaded module without its table fails the guard, naming the attribute, rather than leaving
    unguarded the daemon threads that table would list. A read that raises RuntimeError (another thread added to the
    table while it was read) is retried at once, until a read succeeds or `deadline`, a time on the guard's clock
    (_monotonic), passes; a read that raises after that fails the guard, naming the table (_ExitJoinTableKeptChanging),
    so no read is retried after the deadline. A read already running at the deadline finishes, and a table read first
    after it is read once. A table keeps a thread that has ended until the thread object is collected; the guard asks it
    only about listed threads, which are alive."""
    joined = set()
    for (module, attr), mod, table in _exit_join_table_reads():
        if mod is None:
            continue
        if table is None:
            pytest.fail("tests/conftest.py's session-end thread guard cannot read %s.%s on this Python (%s): "
                        "that table lists the threads concurrent.futures' exit hook joins at exit whatever their "
                        "daemon flag, and without it the guard cannot tell which daemon threads hold the process at "
                        "exit. Find where this Python keeps the table and point EXIT_JOIN_TABLES at it."
                        % (module, attr, sys.version.split()[0]), pytrace=False)
        while True:
            try:
                joined.update(table)    # a WeakKeyDictionary: iterating it yields its threads
                break
            except RuntimeError:        # another thread added to the table while it was read: read it again,
                if _monotonic() >= deadline:    # up to the deadline
                    raise _ExitJoinTableKeptChanging(
                        "tests/conftest.py's session-end thread guard could not read %s.%s before its deadline: every "
                        "read of it on the guard's last pass raised RuntimeError, as iterating the table does when "
                        "another thread adds to it mid-read, until the deadline passed. Without the table the guard "
                        "cannot tell which daemon threads hold the process at exit. Something in this process was "
                        "still adding to the table, starting concurrent.futures threads, at the end of its session."
                        % (module, attr), pytrace=False) from None
    return joined


def _pytest_timeout_timer(t):
    """Whether the guard takes `t` for pytest-timeout's: a thread whose name starts with `pytest_timeout` (the plugin names
    its timer `pytest_timeout <nodeid>`), or whose callable's module starts with it (a Timer keeps its callable as
    `function`, a Thread as `_target`). Any such thread matches, not only the running test's timer, which is the thread
    this exclusion exists for: it is alive through the check. A prefix and not an exact module, because CI installs the
    plugin unpinned: a release that moved its function into a submodule would otherwise fail every cell on the timer."""
    fn = getattr(t, "function", None) or getattr(t, "_target", None)
    mod = (getattr(fn, "__module__", None) or "") if fn is not None else ""
    return t.name.startswith("pytest_timeout") or mod.startswith("pytest_timeout")


def _guarded_thread(t, joined_at_exit=None):
    """Whether the session-end guard waits for `t`: a non-daemon thread, or a daemon thread in `joined_at_exit` (the
    threads concurrent.futures' exit hooks join; when it is not given, _exit_joined_threads is read here, its deadline
    THREAD_GUARD_CAP_S from the call), other than the main thread and the thread running the check, and not one
    _pytest_timeout_timer matches (a `pytest_timeout` prefix of its name or of its callable's module)."""
    if t is threading.main_thread() or t is threading.current_thread() or _pytest_timeout_timer(t):
        return False
    if not t.daemon:
        return True
    if joined_at_exit is None:
        joined_at_exit = _exit_joined_threads(_monotonic() + THREAD_GUARD_CAP_S)
    return t in joined_at_exit


def threads_left_at_session_end(cap_s):
    """The guarded threads (_guarded_thread: every non-daemon thread, and every thread concurrent.futures' exit hooks
    join whatever its daemon flag) still alive once each has had until one deadline, cap_s from the call, to end. Each
    is joined in turn for the time remaining, and the thread list and the exit-join tables are read again after every
    pass, so a thread that starts another as it exits is waited for too. Starts no thread. Every wait is a join, which
    returns when its thread ends, except for two busy loops, each of which stops at its first check after the deadline:
    past the deadline the guard finishes a read or a join already running and reads the thread list and each exit-join
    table once more at most, then returns or fails. For a thread caught mid-start, which join refuses, the list is read again
    at once until that start() returns; that loop spins only while every listed guarded thread is mid-start, since a
    live one's join blocks the pass instead. For a read of an exit-join table that raises RuntimeError (another thread
    added to the table mid-read), the table is read again at once until a read succeeds; a read that raises after the
    deadline fails the guard, naming the table (_exit_joined_threads) and each non-daemon thread of that pass's list
    still alive, with its stack, since those are guarded whatever the table lists. Returns [] when none is left. A
    loaded concurrent.futures module without its exit-join table fails the guard (_exit_joined_threads)."""
    deadline = _monotonic() + cap_s
    while True:
        listed = _enumerate()
        # after the list: a listed worker whose pool's submit returned is in the table
        try:
            joined, kept_changing = _exit_joined_threads(deadline), None
        except _ExitJoinTableKeptChanging as failure:
            joined, kept_changing = None, failure.msg
        # failed outside the except block: inside it, the report would print the table's failure a second time, as this
        # failure's context, under "During handling of the above exception"
        if kept_changing is not None:
            alive = [t for t in listed if t.is_alive() and _guarded_thread(t, frozenset())]    # the non-daemon ones
            frames = sys._current_frames()
            pytest.fail("%s\n\n%s" % (kept_changing, (
                "The non-daemon threads still alive then, which hold the process at exit whatever the table lists:"
                "\n\n" + "\n".join(_thread_report(t, frames) for t in alive)) if alive
                else "No non-daemon thread was alive then."), pytrace=False)
        left = [t for t in listed if _guarded_thread(t, joined)]
        if not left or _monotonic() >= deadline:
            return left
        for t in left:
            try:
                t.join(max(0.0, deadline - _monotonic()))
            except RuntimeError:   # listed while another thread's start() was still running: the next pass reads it again
                pass


def _thread_report(t, frames):
    """One thread for the guard's failure: its name, ident, what it runs and its stack from `frames`
    (sys._current_frames())."""
    target = getattr(t, "_target", None) or getattr(t, "function", None)    # a Timer keeps its callable as `function`
    if target is not None:
        runs = "%s.%s" % (getattr(target, "__module__", None) or "?", getattr(target, "__qualname__", None) or repr(target))
    else:
        runs = "%s.%s.run" % (type(t).__module__, type(t).__qualname__)     # a Thread subclass's own run()
    if runs.startswith("concurrent.futures.thread."):
        runs += (" (a ThreadPoolExecutor worker, of a pool or an asyncio loop's default executor: idle in one left without"
                 " shutdown, or running a task, which shutdown(wait=False) and loop.close() do not end; its stack shows which)")
    elif runs.startswith("concurrent.futures.process."):
        runs += (" (a ProcessPoolExecutor's manager thread: a pool left without shutdown, or one shut down with wait=False"
                 " while a task still runs; its stack reads the same either way)")
    frame = frames.get(t.ident)
    stack = "".join(traceback.format_stack(frame)) if frame is not None else "  (no stack: the thread ended as it was read)\n"
    return "thread %r (ident %s) runs %s\n%s" % (t.name, t.ident, runs, stack)


def _guard_failure_into_report(item, call, rep):
    """The guard's failure kept in its teardown report, for this file's one pytest_runtest_makereport hookwrapper. That
    wrapper runs outside the report hooks of pytest's skipping and unittest plugins and reads the report as they leave
    it (the unittest plugin's is not a wrapper, and every wrapper runs around the implementations that are not; the
    skipping plugin's is a wrapper marked, as this one is, neither tryfirst nor trylast, pluggy calls the later
    registered of two such wrappers first, and this file registers after that plugin). Pytest's tmpdir plugin's report
    wrapper, marked tryfirst, runs outside this one; it reads the report, recording whether the phase passed, and
    changes nothing in it. The skipping and unittest hooks change the report of a teardown the guard failed: pytest's
    skipping plugin makes the error of an xfail-marked test an xfail, which leaves the run green, and its unittest
    plugin puts a TestCase's second stored error (a body and a cleanup that both fail) into the report in place of the
    guard's, which then names no thread. So a teardown report whose item's stash holds the guard's failure
    (pytest_runtest_teardown records it there) is marked failed, and loses the skipping plugin's wasxfail (pytest's
    session counts a failed report toward the run's exit status only without one), and when the outcome it carries is
    not the guard's error, the guard's text is added after that outcome. That is the unittest case (a TestCase's second
    error, or a skip, in the guard's place), and also a teardown whose runner raised first (a fixture's teardown failed
    or skipped): pytest_runtest_teardown runs the guard after that, when the runner went on to tear down every fixture,
    and raises it again, so it is the one the report carries. The wrapper redacts the report after this step, so the
    added text goes through the same redaction as the rest of the report and the guard's stderr copy."""
    if call.when != "teardown":
        return
    failure = item.stash.get(_GUARD_FAILURE, None)
    if failure is None:
        return
    rep.outcome = "failed"
    if hasattr(rep, "wasxfail"):
        del rep.wasxfail
    if call.excinfo is not None and call.excinfo.value is failure:
        return                                          # the report's error is the guard's own
    lr = rep.longrepr
    parts = [] if lr is None else [lr[2] if isinstance(lr, tuple) and len(lr) == 3 else str(lr)]
    parts += ["[tests/conftest.py, the session-end thread guard] this teardown also failed the guard. The outcome "
              "above is the one this report carries (a fixture's teardown that failed or skipped, or an outcome "
              "pytest's unittest plugin put in the guard's place); the guard's error follows.", str(failure)]
    # _redacted_longrepr keeps the crash location of the error the report carries, which the short summary's line
    # reads; the text it is handed is redacted by the wrapper's next step
    rep.longrepr = _redacted_longrepr(lr, "\n\n".join(parts))


def _redact_as_exconly(failure):
    """The failure's text, str(failure), scrubbed as the report prints a failure raised with a traceback: pytest renders
    that exception as its exconly does, the type name, a colon and the message (`Failed: <message>` for a pytest.fail
    failure), on the first line of its error under the `E` marker, and in the report's crash message, which the short
    test summary prints. The colon puts the message's first word in the pattern net's value position (after `: `), so a
    token that leads such a failure's message is masked in the report, and the bare message leaves it at the start of a
    line, where, with more text after it, no rule reads it as a value. So the rendering is scrubbed as the stderr copy
    is (as it stands, then under the marker, _redact_crash_message), and the type name and colon are taken off again.
    When the scrub changed them (an environment value or a token in the type name), the scrubbed rendering is returned
    whole, type name included. A failure raised with pytrace=False is scrubbed the same way here, but the report prints
    it differently: its error is the bare message, and _redact_report rebuilds the crash message only when the report's
    text changed, so the report prints a leading token raw and only the stderr copy masks it. That gap is
    _redact_report's."""
    message = str(failure)
    excinfo = pytest.ExceptionInfo.from_exc_info((type(failure), failure, failure.__traceback__))
    rendered = excinfo.exconly(tryshort=True)
    stype, sep, _rest = rendered.partition(": ")
    if not message or not sep:      # an empty message renders as the type name alone, with no colon
        return message
    prefix = stype + sep
    scrubbed = _redact_crash_message(redact_report_text(prefix + message))
    return scrubbed[len(prefix):] if scrubbed.startswith(prefix) else scrubbed


def _guard_failure_to_stderr(item, failure):
    """The guard's second channel: its failure's text, written to stderr, which no report hook can change (the first,
    the teardown's report, is kept failed and naming the threads by _guard_failure_into_report). The capture plugin
    captures stderr during a teardown, so it is suspended for the write, which then reaches this process's own stderr.
    Under pytest-xdist that is the controller's stderr: execnet, xdist's transport, points a worker's stdout at
    /dev/null but, outside Windows, does not redirect its stderr (on Windows it moves sys.stderr to a copy of the
    controller's). Everything written goes through the teardown report's redaction, in the order _redact_report applies
    it (_note_env_values, then redact_report_text), three ways. The failure's text is scrubbed first as pytest's exconly
    renders it, the type name, a colon and the message (_redact_as_exconly): for a failure raised with a traceback, the
    report prints that rendering on the first line of its error and in its crash message, where the colon puts the
    message's first word in the pattern net's value position and the report masks a token there, and stderr prints the
    message without the type name. (For a failure raised with pytrace=False the report prints a leading token raw and
    this copy masks it; _redact_as_exconly's docstring says why.) Then the whole write, the header with its node id and
    worker name included, is scrubbed as it stands, and then again with each line under pytest's `E` marker
    (_redact_crash_message): the report prints a failure raised with a traceback (a pytest.fail inside the guard's call,
    from a Thread subclass's join, say) under that marker, where the pattern net's rules for a failed comparison's diff
    lines apply, and stderr prints it bare. CI's logs are public, and a value the report masks (a thread named with an
    environment value, say) must not reach them raw here. One window is left: this copy is scrubbed with the values
    noted at the guard's check, and the report later, at report time, so a value that enters the environment between the
    two (written by a thread still running then, say, which is a thread the guard names) is masked in the report and
    printed raw here."""
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    _note_env_values()
    text = ("\n[tests/conftest.py, the session-end thread guard] the teardown of %s, this process's last test%s, fails "
            "with the error below. It is written to stderr as well as to that teardown's report, as a second channel "
            "that no report hook can change.\n%s\n"
            % (item.nodeid, " (pytest-xdist worker %s)" % worker if worker else "", _redact_as_exconly(failure)))
    # the whole write, nothing below writes any other text: scrubbed as it stands and then marked, as the report's crash
    # message is (_redact_crash_message), since the report prints a message with a traceback under pytest's `E` marker
    text = _redact_crash_message(redact_report_text(text))
    capman = item.config.pluginmanager.getplugin("capturemanager")
    if capman is None:                          # -p no:capture: nothing captures stderr
        sys.stderr.write(text)
        sys.stderr.flush()
        return
    with capman.global_and_fixture_disabled():
        sys.stderr.write(text)
        sys.stderr.flush()


@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtest_teardown(item, nextitem):
    """The session-end thread guard (above): at the process's last test only, once the runner has finished tearing
    down every scope, the guarded threads still alive at THREAD_GUARD_CAP_S fail this teardown, each named with its
    stack. Every failure of the guard takes two channels: this teardown's report, which this file's
    pytest_runtest_makereport keeps failed and naming the threads from the failure recorded here in the item's stash
    (_guard_failure_into_report), and the same text on stderr (_guard_failure_to_stderr). A wrapper, so the guard runs
    after the runner's teardown (trylast: the innermost wrapper, around the runner's own implementation and inside the
    capture plugin's). When that teardown raised, the guard runs only if the runner's stack of set-up nodes
    (item.session._setupstate.stack) is empty, so that no fixture is left for pytest to tear down after this check. The
    runner collects an Exception or one of pytest's outcomes (pytest.fail's, pytest.skip's) raised by a fixture's
    teardown, goes on to tear down the rest, and raises it (several as one group) once the stack is empty: that error or
    skip stays the one this teardown raises, and the report step adds the guard's text after it; under an xfail mark
    the skipping plugin would otherwise make that error an xfail, and a guard that did not run there left the run green
    with the threads unnamed. A BaseException that is neither (asyncio.CancelledError, SystemExit) stops the runner at
    the node whose finalizer raised it: that node's remaining finalizers never run, and the nodes of wider scopes stay
    on the stack, their fixtures set up and their threads running, until pytest_sessionfinish tears them down after
    this check. Then the error is raised again without the check, as it is on KeyboardInterrupt or pytest.exit, which
    end the session at once: a thread such a run leaks goes unnamed, and under an xfail mark, which makes that error an
    xfail, the run passes. When that node is the session's, the last on the stack, the stack is empty and the guard
    runs: nothing is left for pytest_sessionfinish, and a thread of a fixture whose finalizer never ran is still running
    at exit."""
    try:
        result = yield
    except (KeyboardInterrupt, pytest.exit.Exception):
        raise
    except BaseException:           # pytest.fail and pytest.skip raise BaseExceptions, not Exceptions
        # checked only when the runner's teardown finished: a fixture of a wider scope still set up keeps its threads
        if nextitem is None and not item.session._setupstate.stack:
            _guard_into_both_channels(item)
        raise
    if nextitem is None:
        failure = _guard_into_both_channels(item)
        if failure is not None:
            raise failure
    return result


def _guard_into_both_channels(item):
    """Runs the guard for pytest_runtest_teardown. Its failure, when it fails, is recorded in the item's stash for the
    report step (_guard_failure_into_report), written to stderr (_guard_failure_to_stderr), and returned; None when it
    passes."""
    try:
        _session_end_thread_guard(item)
    except pytest.fail.Exception as failure:
        item.stash[_GUARD_FAILURE] = failure
        _guard_failure_to_stderr(item, failure)
        return failure
    return None


def _session_end_thread_guard(item):
    """The check itself, for pytest_runtest_teardown: fails, through pytest.fail, naming each guarded thread still
    alive at THREAD_GUARD_CAP_S with its stack; a table it cannot read fails it too (_exit_joined_threads)."""
    left = threads_left_at_session_end(THREAD_GUARD_CAP_S)
    if not left:
        return
    frames = sys._current_frames()
    pytest.fail("threads still running at the end of this process's session, after up to %g s for each to end "
                "(tests/conftest.py, the session-end thread guard): non-daemon threads, and concurrent.futures "
                "threads of either daemon flag, which its exit hooks join. A thread a test starts must end before the "
                "test does. A named thread still running when the interpreter exits keeps the process from exiting: "
                "run serially, the run hangs until the thread ends or the job cap cancels it; under pytest-xdist the "
                "controller kills a worker still alive when the run ends, and the run would pass without this report. "
                "Two kinds of named thread let the process exit and fail this guard all the same: an idle "
                "concurrent.futures worker, which the interpreter wakes at exit, and a thread stopped only after this "
                "check (a config cleanup, pytest_sessionfinish or pytest_unconfigure). %s is this process's last test, "
                "where the check runs, and not necessarily the one that started a thread; each thread's target and "
                "stack say where it came from."
                "\n\n%s" % (THREAD_GUARD_CAP_S, item.nodeid, "\n".join(_thread_report(t, frames) for t in left)),
                pytrace=False)


# Browser-backed served-page tests fail loudly where they must run (T308, 2026-09-10). tests/test_*_browser.py and
# tests/test_*_served.py boot a hermetic kernel and drive the real dashboard pages in playwright's Chromium; on a machine
# without the extension's node deps or a browser they skip, and say why. CI's Python matrix jobs are such machines, so a
# served-page regression never turned them red (the deep-link landing pin, T307, red on main while CI stayed green). The
# served-pages job installs that browser and runs these files with ROMP_SERVED_TESTS_REQUIRE=1: any skip in them (a class
# setUp that finds no deps, a driver that exits 3 for a missing browser, a kernel that never served) is reported as a
# FAILURE carrying the skip's own reason, the stance the pane bench takes with ROMP_UI_BENCH_REQUIRE. One exception a
# test can claim for itself: a skip whose reason begins with "optional:" stays a skip, for a leg the runner has declared
# it does not carry (the pane-hiding test drives three engines and CI installs one; ROMP_SERVED_TESTS_ENGINES names the
# installed ones, and that test says "optional:" for the others). Off (the default) nothing changes: contributors and
# the Python matrix jobs skip as before. Pinned by tests/test_served_tests_require.py.
_SERVED_TESTS_REQUIRE = os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1"


def _node_file(node) -> str:
    """The basename of the file a collected node (an item, a module collector) came from."""
    return os.path.basename(str(getattr(node, "path", None) or node.fspath))


def _skip_reason(rep) -> str:
    """The text of a skipped report: the reason of its (path, line, reason) longrepr; an xfail's declared
    reason (its longrepr is the traceback of the failure the xfail absorbed); else the longrepr's text."""
    lr = rep.longrepr
    if isinstance(lr, tuple) and len(lr) == 3:
        return lr[2]
    if getattr(rep, "wasxfail", None):
        return "xfail: %s" % rep.wasxfail
    return str(lr)


def _fail_skipped_report(rep, longrepr) -> None:
    """The one flip every belt uses: a skipped report (a TestReport or a CollectReport) becomes a failed one
    carrying `longrepr`. An xfail's `wasxfail` attribute is removed first, and by hasattr, not truthiness: a bare
    @pytest.mark.xfail sets it to "". pytest's session counts a failed report toward the exit status only when the
    report has no `wasxfail` (Session.pytest_runtest_logreport), so a flipped xfail that kept it printed FAILED and
    exited 0. The served switch did exactly that until the flip was shared here (2026-09-21): its caller flipped
    the outcome without the delete while the never-skips belt beside it deleted, so the two belts disagreed on
    the one report shape the shared _skip_reason has a branch for. Callers compute the skip's reason BEFORE this
    call: _skip_reason reads wasxfail. A caller's exemption (the served switch's `optional:` skips) returns before
    reaching here, so an exempt skip keeps its report untouched. Pinned by execution, each on an xfail that is a
    file's ONLY skip, so the exit status is the assertion and no sibling skip carries it: in
    tests/test_served_tests_require.py the xfail-alone case and its bare twin, in tests/test_ci_sdk_pin.py NeverSkips'
    xfail-only case and its bare twin (BARE_XFAIL_ONLY). The bare twins pin the hasattr: a bare xfail's wasxfail is
    empty, so a delete by truthiness kept it and the run printed FAILED and exited 0, while both reasoned cases passed
    (review round 4, 2026-09-23)."""
    if hasattr(rep, "wasxfail"):
        del rep.wasxfail
    rep.outcome = "failed"
    rep.longrepr = longrepr


def _is_served_test_file(item) -> bool:
    name = _node_file(item)
    return name.startswith("test_") and (name.endswith("_browser.py") or name.endswith("_served.py"))


def _require_served_test_ran(item, rep) -> None:
    """Under ROMP_SERVED_TESTS_REQUIRE=1, a skip in a browser-backed served-page test file is reported as a
    failure carrying the skip's own reason; an `optional:` skip stays a skip. Called from the one
    pytest_runtest_makereport above. No-op with the switch off."""
    if not _SERVED_TESTS_REQUIRE:
        return
    if rep.skipped and _is_served_test_file(item):
        reason = _skip_reason(rep)
        if re.match(r"^(Skipped: )?optional:", reason):
            return
        _fail_skipped_report(rep, "ROMP_SERVED_TESTS_REQUIRE=1: a browser-backed test skipped (at %s) where it must run: %s"
                             % (rep.when, reason))


# A file listed here declares that every one of its tests checks something on every road, so a skip outcome in it,
# from any spelling (pytest.mark.skipif, unittest.skipIf, self.skipTest, SkipTest raised in setUpClass, a module-level
# pytest.importorskip or pytest.skip(allow_module_level=True); an xfail too, which pytest records as a skipped
# outcome), at collection, at setup or in the test body, is reported as a FAILURE carrying the skip's own reason.
# Always on, no switch: no road of tests/test_ci_sdk_pin.py is a skip (on an interpreter without the SDK its
# InstalledVersion test asserts the pin's form and warns; where the run requires the SDK it fails), so a skip there is
# a pin reporting green having checked nothing. The property is read from the report, in the worker under xdist and in
# the one process serially, so nothing depends on which test ran last or on which spelling an edit used.
# 2026-09-20: the guard before this was a five-name list of unittest spellings inside the module, which
# pytest.mark.skipif and a module-level pytest.importorskip passed, and which a module-level skip removed from the run
# entirely (the guard never ran). Proved by execution in tests/test_ci_sdk_pin.py's NeverSkips. What a report cannot
# show is a test that was never collected: a method renamed off the test_ prefix, deleted or fenced behind an if files
# nothing to flip, so NeverSkips pins, in a child pytest --collect-only -q, that pytest's collector lists the ONE test
# the belt exists for, InstalledVersion's, by node id; its in-process case pins only the method's name against
# unittest's loader, which is not the collector (UnitTestCase.collect drops a class or method whose __test__ is False,
# which the loader never reads); those census cases cover that one test, not the module. The literal below is checked
# against the tree (2026-09-21; before this a copy renamed test_ci_sdk_pin_v2.py ran with the belt inert, a skip in it
# a plain skip and every test green): NeverSkips asserts its own module's basename is in the tuple as written, and
# tests/test_served_tests_require.py, outside the guarded module, asserts every entry names a file under tests/, so
# a rename reds in both and a deletion reds there; both read it through never_skip_files_as_written below. The
# residual, stated for what it is: the census lives in the module it guards, so a road that changes what a run
# collects without touching the file files no report, takes the census with it or acts on the run where the
# census's child may not see it, and the run stays green. The road is a class, and no list closes it: anything that changes what the run collects,
# among them a collect_ignore or collect_ignore_glob, a collection hook in a conftest or plugin (pytest_ignore_collect,
# pytest_collection_modifyitems), an ini file's test-file pattern, testpaths or addopts, PYTEST_ADDOPTS, --ignore or
# --ignore-glob, -k, -m or --deselect, and a module-level __test__ = False. As read on 2026-09-24: none of these is on
# ci.yml's Run pytest line (no path, no -k, no --ignore) or in its env (no PYTEST_ADDOPTS), and those two are held
# since round 5's ruling C: tests/test_ci_sdk_pin.py's run_pytest_status refuses a word on that line outside its option
# allowlist and a key of its merged env outside its env allowlist; no conftest in the tree sets collect_ignore or
# collect_ignore_glob or defines a collection hook (this file, the only one, implements two reporting hooks,
# pytest_make_collect_report and pytest_collectreport, which drop nothing); and the repo has no pytest.ini,
# .pytest.ini, pytest.toml, .pytest.toml, pyproject.toml, setup.cfg or tox.ini. Of the rest of that read,
# tests/test_thread_stop_census.py's test_the_population_is_what_pytest_collects_under_tests holds pytest.ini,
# setup.cfg, tox.ini and pyproject.toml absent at the repository root and in tests/ itself; nothing pins the conftest
# read, .pytest.ini, pytest.toml or .pytest.toml, or any of the seven in a directory below those two.
_NEVER_SKIP_FILES = ("test_ci_sdk_pin.py",)


def never_skip_files_as_written(path=None) -> tuple:
    """The tuple assigned to _NEVER_SKIP_FILES above, read from THIS FILE'S TEXT with ast.literal_eval rather than
    returned from the name: the two checks that consume it (NeverSkips' membership case in tests/test_ci_sdk_pin.py,
    the existence case in tests/test_served_tests_require.py) are about the literal a reader sees and the belt keys
    on, whichever conftest object their process loaded. A missing assignment, or one whose value is not a literal
    tuple (a name, a call, a comprehension, a list), is an AssertionError that says so and names the line, never an
    AttributeError from a walk over elts; `path` exists so those refusals can be run against a scratch file
    (tests/test_served_tests_require.py), and defaults to this file."""
    path = os.path.realpath(path or __file__)
    where = os.path.join(os.path.basename(os.path.dirname(path)), os.path.basename(path))   # tests/conftest.py
    with open(path) as f:
        tree = ast.parse(f.read(), path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_NEVER_SKIP_FILES" for t in node.targets):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                raise AssertionError("%s:%d: _NEVER_SKIP_FILES is not a literal tuple (a %s)"
                                     % (where, node.lineno, type(node.value).__name__))
            if not isinstance(value, tuple):
                raise AssertionError("%s:%d: _NEVER_SKIP_FILES is a literal %s, not a tuple"
                                     % (where, node.lineno, type(value).__name__))
            return value
    raise AssertionError("%s assigns no _NEVER_SKIP_FILES at module level" % where)


def _never_skip_longrepr(name, where, reason) -> str:
    return ("never-skips: %s skipped (at %s) where every test checks something on every road (tests/conftest.py, "
            "_NEVER_SKIP_FILES): %s" % (name, where, reason))


def _require_never_skip_ran(item, rep) -> None:
    """A skipped report for a test in a _NEVER_SKIP_FILES file is a failure carrying the skip's reason. Called
    from the one pytest_runtest_makereport above; always on. The flip is _fail_skipped_report's, which removes an
    xfail's `wasxfail` so the failure counts toward the exit status."""
    if rep.skipped and _node_file(item) in _NEVER_SKIP_FILES:
        reason = _skip_reason(rep)
        _fail_skipped_report(rep, _never_skip_longrepr(_node_file(item), rep.when, reason))


def _require_never_skip_collected(collector, rep) -> None:
    """The collection half (pytest_make_collect_report above): a skipped CollectReport for a _NEVER_SKIP_FILES
    module, which a module-level skip produces in place of any items, becomes a failed one, a collection error."""
    if rep.skipped and _node_file(collector) in _NEVER_SKIP_FILES:
        reason = _skip_reason(rep)
        _fail_skipped_report(rep, _never_skip_longrepr(_node_file(collector), "collection", reason))
