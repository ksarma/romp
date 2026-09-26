"""unittest-side twin of conftest.py's state floor (2026-08-12): `python -m unittest tests.test_x`
imports this package first, so the floor lands before any test module loads bin/romp-* — which
resolve their state root at import time. conftest.py covers only pytest; without this, a bare
unittest run operated on the REAL ~/.local/state/romp (tests/test_kernel.py overwrote the real
remotes.json that way today). Does NOT cover `cd tests && python -m unittest test_x`, where the
per-module preambles are the floor (tests/test_state_isolation_order.py enforces them). A direct
`python3 tests/test_x.py` reaches this package through the module's own `from romp_load import
load_source` (tests/romp_load.py's bootstrap, 2026-09-14), so it has this floor from that import on;
the module's preamble stays its first line of defence and follows the import.
Since 2026-09-14 the run's private temp root, the TMPDIR redirect into it and the owner marker the
kernel's sweep reads live here too (below), for the same reason: they were conftest.py's, so a bare
run had none of them."""
import atexit
import json
import os
import shutil
import sys
import tempfile
import time

# Temp-directory hygiene, the in-process half (2026-09-06): the suite used to leak every directory it
# made. This floor and conftest.py's each minted a state root per process and never removed it (two
# per pytest process: eighteen for a `pytest -n 8` run), and about three hundred test modules call
# tempfile.mkdtemp with no cleanup of their own. On a developer machine that ran the suite many times
# a day that left about 1.9 million directories under the system temp directory, enough that listing
# it took minutes and tens of gigabytes of memory, and the out-of-memory kills that followed took a
# running romp kernel down. The fix is at the source: every tempfile.mkdtemp call made in THIS
# process is recorded, and everything recorded is removed at interpreter exit (and, under pytest, at
# session end; see conftest.py). Only directories this process created, and only under the process
# temp dir, are ever removed: tempfile.gettempdir(), which is the private per-run root minted below
# under every entry point that imports this package. tempfile.TemporaryDirectory goes through the
# same mkdtemp and cleans itself first, so the exit sweep finds nothing of it.
# What this hook cannot see is the other half, the root's: directories made by CHILD processes
# (kernels, git, a shell's `mktemp -d`), files from mkstemp, and os.mkdir paths. Those land in the
# root because TMPDIR points there, and the root is removed whole at exit (and, under pytest, at
# run end by conftest.py, which names a survivor).
_MADE_DIRS = []
_REAL_MKDTEMP = tempfile.mkdtemp


def _tracked_mkdtemp(*a, **k):
    p = _REAL_MKDTEMP(*a, **k)
    _MADE_DIRS.append(p)
    return p


_tracked_mkdtemp.romp_tracked = True          # tests/test_tempdir_hygiene.py asserts the hook is installed
if not getattr(tempfile.mkdtemp, "romp_tracked", False):
    tempfile.mkdtemp = _tracked_mkdtemp


def remove_made_dirs():
    """Remove every directory this process minted through tempfile.mkdtemp. Idempotent; registered
    with atexit here and called again from conftest's pytest_sessionfinish."""
    root = os.path.realpath(tempfile.gettempdir())
    for p in reversed(list(_MADE_DIRS)):
        try:
            rp = os.path.realpath(p)
            if rp != root and rp.startswith(root + os.sep) and os.path.isdir(rp) and not os.path.islink(p):
                shutil.rmtree(rp, ignore_errors=True)
        except Exception:
            pass
    _MADE_DIRS.clear()


# The private temp root, the child-process half (2026-09-06, in conftest.py until 2026-09-14): every
# temp path a run creates lives under ONE `romp-tests-*` root, removed when the run ends. The hook
# above records and removes what THIS process mints through tempfile.mkdtemp, but a test's children
# — kernels, git, `mktemp -d` in a shell — and mkstemp or os.mkdir paths are outside its sight (a
# full run left ~5,600 of those per run at up to ten a second). So the process's temp dir is
# redirected: tempfile.tempdir is set directly (gettempdir() caches its first answer, and the line
# recording the system temp dir has just called it), and TMPDIR is exported so every child inherits
# the same root. Import-time, and in this package rather than conftest.py: the package is the first
# thing BOTH entry points import (pytest imports it before conftest.py; `python -m unittest
# tests.test_x` imports it before the module), so the root, the redirect and the marker below are in
# place for a bare run too. While these were conftest.py's, a bare run had no redirect and no marker:
# every child's `mktemp -d`, every mkstemp file and (once killed mid-run, with the hook's exit sweep
# never reached) every tracked directory and the romp-tests-state-* dir landed loose in the system
# temp dir, and with no marker the kernel's sweep had to refuse them, so a shared machine
# accumulated thousands of them from runs that were killed (2026-09-14).
# The root itself is minted with the REAL mkdtemp: it is not the hook's to remove (the hook's scope
# is the inside of the root), so it is not recorded. The state dir below is minted AFTER the redirect,
# through the hook, and so sits INSIDE the root; nothing a run makes sits outside it.
# Under pytest-xdist this runs in the controller and in every worker: each imported this package and
# so owns a root of its own. The system temp dir — the one the RUN was handed, before any redirect — is
# recorded once, by the first process to import this package (setdefault, not an assignment: a worker
# inherits the controller's record along with its TMPDIR). A test that must leave the root (an AF_UNIX
# socket path built to an exact length) falls back to it, and only to it — a literal system path in a
# `dir=` would bypass the redirect (one did).
# BESIDE, NOT INSIDE (2026-09-21): a process handed a `romp-tests-*` root as its temp dir — an xdist
# worker, a nested pytest, any child of a run that imports this package — mints its own root in the
# recorded system dir, beside its parent's, never inside it: beside whenever the recorded system dir
# exists, differs from the handed dir and is the handed dir's own parent (parent_root below); otherwise
# inside the handed dir, as before 2026-09-21 (a record gone or unwritable falls back to inside too, and
# tests/test_tempdir_hygiene.py PrivateTempRoot's every-root-directly-under-it pin reds on that shape,
# so a run that fell back says so). Until then a worker's root nested inside
# the controller's, and each level cost 20 bytes (`/romp-tests-XXXXXXXX`) of the AF_UNIX path budget:
# the deepest hosts-on lab (tests/test_session_host_restart.py, `host-served-XXXXXXXX/xdg/romp` plus the
# host's `hosts/<sid8>.sock`) came to TMPDIR + 90 bytes under -n and TMPDIR + 70 alone, so at a 17-byte
# TMPDIR the socket path was 107 = SOCK_PATH_MAX exactly: at 18 bytes that lab's test (ServedRestart)
# overflowed under xdist and passed alone, and the TMPDIR + 72 shapes (tests/test_session_host.py
# HostProcess, test_host_transport EndToEnd and AttachStandDown: a bare mkdtemp root, `tmp` + tail)
# overflowed from a 36-byte TMPDIR under -n; 76 sweep logs read the red as a flake. Beside, every process is
# one level under the handed dir whatever the worker count, and the bound is TMPDIR + 70 <= 107 (a
# 37-byte TMPDIR; tests/test_tempdir_hygiene.py HarnessSocketBudget derives it from the roots the
# harness makes and the tests' own lab shapes). A nested process appends its pid and root to
# `<parent root>/romp-tests-children`, and the parent's removal (remove_tmp_root below, conftest's
# _remove_run_dirs) takes the root of any listed child whose owner is DEAD before its own, so a worker
# that died without its hooks (SIGKILL, an OOM kill, a crashed node) is cleaned by its parent as the
# nesting cleaned it before; a live child keeps its root and removes it itself. The name stays the
# same 19 bytes: the whole gain is the level. The mint is in a function so the pin can exercise the
# placement by execution on synthetic paths.
TEST_ROOT_PREFIX = "romp-tests-"                     # the kernel's sdk_backend.TEST_ROOT_PREFIX agrees
TEST_ROOT_CHILDREN = "romp-tests-children"           # inside a root: one JSON line {"pid", "root"} per child that minted beside it


def parent_root(handed, system):
    """The `romp-tests-*` root a NESTED process was handed as its temp dir, or None for a run's first process. Nested
    means: the handed dir is a root by name, it sits DIRECTLY under the recorded system dir (realpath of its parent is
    the realpath of `system`), and that system dir exists to mint in. The placement test is on the parent, not the name
    alone (the review of 2026-09-21): the package's own `romp-tests-state-*` dir and conftest's `romp-tests-claude-*`
    are `romp-tests-*` by name too, and sit INSIDE a root, so a process handed one of those as its TMPDIR mints inside
    it, as any first process does. Pure on its arguments; the module applies it to what this process was handed."""
    try:
        if (os.path.basename(handed).startswith(TEST_ROOT_PREFIX) and os.path.isdir(system)
                and os.path.realpath(os.path.dirname(os.path.abspath(handed))) == os.path.realpath(system)):
            return handed
    except OSError:
        pass
    return None


def mint_root(handed, system):
    """(root, parent): a private root minted with the REAL mkdtemp — in `system`, beside the parent's, when `handed`
    is a parent's root; in `handed` itself for a first process. A record that cannot be minted in (gone, unwritable)
    falls back to inside, as before 2026-09-21: an import must never fail on it."""
    parent = parent_root(handed, system)
    if parent:
        try:
            return _REAL_MKDTEMP(prefix=TEST_ROOT_PREFIX, dir=system), parent
        except OSError:
            pass
    return _REAL_MKDTEMP(prefix=TEST_ROOT_PREFIX, dir=handed), None


_HANDED = tempfile.gettempdir()                      # what THIS process was handed: the system dir, or a parent's root
os.environ.setdefault("ROMP_TESTS_SYSTEM_TMPDIR", _HANDED)
SYSTEM_TMPDIR = os.environ["ROMP_TESTS_SYSTEM_TMPDIR"]
TMP_ROOT, PARENT_ROOT = mint_root(_HANDED, SYSTEM_TMPDIR)
tempfile.tempdir = TMP_ROOT
os.environ["TMPDIR"] = TMP_ROOT

# Owner marker (2026-09-10): a run that dies without reaching any removal below — pytest-timeout's
# os._exit, a kernel restart cutting the tool shell, the cut-turn reaper's kill — leaves its root
# standing, and on a shared machine those roots piled into millions of files that the next boot's
# /tmp cleanup spent 39 minutes deleting. Nothing in this process can run after such a death, so the
# removal has to come from outside: the kernel's boot reconcile sweeps `romp-tests-*` roots under the
# system temp dir whose owner is dead (sdk_backend.sweep_dead_test_roots). This marker is what it
# reads — the owning pid, written at mint time so it is there for the whole life of the root. A root
# WITHOUT a marker is not touched (the sweep cannot tell a foreign directory from a pre-marker one).
# One marker per root: the package state dir sits inside the root now and goes with it.
TEST_ROOT_OWNER_MARKER = "romp-tests-owner.json"     # the kernel's sdk_backend.TEST_ROOT_OWNER_MARKER agrees


def write_owner_marker(d):
    if not d:
        return
    try:
        with open(os.path.join(d, TEST_ROOT_OWNER_MARKER), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": os.getpid(), "started": time.time(),
                                 "argv": [os.path.basename(a) for a in sys.argv[:3]]}))
    except OSError:
        pass                                 # a root we cannot write into is one we cannot leak into either


write_owner_marker(TMP_ROOT)


def _pid_alive(pid):
    """Is the owner of a listed child root still running? On Linux `/proc/<pid>/stat` decides, and a ZOMBIE (state Z:
    exited, not yet reaped by its parent) is DEAD here — a worker xdist has not collected yet, or a child whose parent
    never waits, owns nothing any more and its root is for the taking, where signal 0 would still call it alive. Where
    there is no procfs, or the stat file cannot be read (a race with the exit), the kernel's rule (sdk_backend._pid_alive):
    signal 0, and only "no such process" means dead. A pid that is not a number is left alone (alive)."""
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return True
    try:
        with open("/proc/%d/stat" % pid, "rb") as fh:
            stat = fh.read()
        # the comm field is in parentheses and may hold spaces or a ')': the state is the first field after the LAST ')'
        state = stat[stat.rindex(b")") + 1:].split()[0]
        if state == b"Z":
            return False
        return True
    except (OSError, ValueError, IndexError):
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def record_child_root(parent, root):
    """One line into `<parent>/romp-tests-children`: a nested process tells its parent where it minted, so the parent
    can remove the root of a child that died without its own removal. O_APPEND and one short line per child, so
    concurrent workers never interleave; a parent root already gone is nothing to tell."""
    if not parent or not root:
        return
    try:
        with open(os.path.join(parent, TEST_ROOT_CHILDREN), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"pid": os.getpid(), "root": root}) + "\n")
    except OSError:
        pass


def remove_dead_children(root, system=None, depth=3):
    """Remove every root listed in `<root>/romp-tests-children` whose owner is DEAD, each after its own dead children;
    return the paths of the dead ones still standing afterwards. A listed root whose owner is alive is left to that
    owner (it removes its own at exit); a line not ours by shape — no `romp-tests-*` basename, a symlink, not directly
    under the recorded system dir — is left alone too. Never raises."""
    system = os.path.realpath(system or SYSTEM_TMPDIR)
    survivors = []
    try:
        with open(os.path.join(root, TEST_ROOT_CHILDREN), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return survivors
    for line in lines:
        try:
            rec = json.loads(line)
            child, pid = rec["root"], int(rec["pid"])
            if (not os.path.basename(child).startswith(TEST_ROOT_PREFIX) or os.path.islink(child)
                    or not os.path.isdir(child) or os.path.realpath(os.path.dirname(child)) != system):
                continue
            if _pid_alive(pid):
                continue
            if depth > 0:
                survivors += remove_dead_children(child, system, depth - 1)
            shutil.rmtree(child, ignore_errors=True)
            if os.path.isdir(child):
                survivors.append(child)
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return survivors


record_child_root(PARENT_ROOT, TMP_ROOT)


def remove_tmp_root():
    """Remove the root whole, whatever the hook's sweep could not see, after the roots of its dead children (beside
    it, listed inside it). Idempotent and silent: under pytest, conftest's pytest_unconfigure does the same first and
    names a survivor; this is the exit fallback for a bare run and for a pytest exit that skipped the hooks."""
    remove_dead_children(TMP_ROOT)
    shutil.rmtree(TMP_ROOT, ignore_errors=True)


# atexit runs the last registration first: the root's removal is registered BEFORE the sweep's, so at
# exit the sweep runs first (every tracked directory, all inside the root) and the root goes after it,
# whole. Nothing runs after an os._exit (pytest-timeout's thread method ends a hung run that way, and a
# kill is the same), so such a run leaves its root, marked, as a top-level entry in the system temp dir
# for the kernel's sweep (one per process that died that way: a controller's and its workers' stand
# beside each other there).
atexit.register(remove_tmp_root)
atexit.register(remove_made_dirs)

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp(prefix="romp-tests-state-")
# Minted after the redirect above, through the hook: inside the root, recorded, removed by the sweep
# at exit and with the root either way. conftest.py reads STATE_DIR for its own pins.
STATE_DIR = os.environ["XDG_STATE_HOME"]
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
# No unittest run may reach a REAL manager or kernel either: the same three ports conftest.py poisons
# for pytest (its comment has the readers and the incident). Set to a dead port, never popped: every
# reader maps an absent variable to the default port, which on a machine running romp is the live one.
os.environ["ROMP_MANAGER_PORT"] = "1"
os.environ["ROMP_KERNEL_PORT"] = "1"
os.environ["ROMP_SERVE_PORT"] = "1"
os.environ["ROMP_CKPT_FIRST_DOC_KB"] = "0"   # the young-session floor off for the fixtures, the twin of conftest.py's line (1721 round two): a
#                                                bare unittest run gave 113 failures with every checkpoint shape skipped young without it

# `from romp_load import load_source` in a test module (tests/romp_load.py): under pytest and
# `python -m unittest tests.test_x` the test modules are imported as members of this package, so the
# bare name resolves only because it is registered here; a direct script run finds the file on
# sys.path itself, and that bare module is what imports THIS package (its bootstrap, 2026-09-14), so
# the setdefault keeps it and the package-relative import below is a second object. Nothing rides on
# which one a test holds: load_source shares through sys.modules, not through the module.
from . import romp_load as _romp_load  # noqa: E402
sys.modules.setdefault("romp_load", _romp_load)

# `import lab_dist` in the served-lab modules (tests/lab_dist.py, the one owner of the vscode-extension/dist
# build) resolves the same way, for the same reason.
from . import lab_dist as _lab_dist  # noqa: E402
sys.modules.setdefault("lab_dist", _lab_dist)

# `import lab_dist_stub` in the two real-tree pins (tests/lab_dist_stub.py, the node preload standing in for the bare
# packages a checkout without the extension's node_modules lacks) resolves the same way.
from . import lab_dist_stub as _lab_dist_stub  # noqa: E402
sys.modules.setdefault("lab_dist_stub", _lab_dist_stub)

# `from fs_clock import move_ctime` in a test module (tests/fs_clock.py, 2026-09-12): the shared force-until-moved ctime
# helper the memo tests and the thread mail-off test import, registered under its bare name like romp_load above
from . import fs_clock as _fs_clock  # noqa: E402
sys.modules.setdefault("fs_clock", _fs_clock)
# `from git_fixture import git, init_repo` (tests/git_fixture.py, T299): the throwaway-repo fixtures' one git
# runner, registered the same way for the same reason.
from . import git_fixture as _git_fixture  # noqa: E402
sys.modules.setdefault("git_fixture", _git_fixture)
# `from env_ring_census import census` (tests/env_ring_census.py, review round 6 of the env-pick door, 2026-09-19): the
# ring-keyed census of the problem ring's doors that tests/test_session_env.py pins, registered the same way.
from . import env_ring_census as _env_ring_census  # noqa: E402
sys.modules.setdefault("env_ring_census", _env_ring_census)
