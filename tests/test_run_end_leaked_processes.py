#!/usr/bin/env python3
"""The run-end process check names a process whose environment, cwd, open files or argv hold a path under the run's roots
(2026-09-22, the reviewer's ruling on fork PR #813's finding; its reads widened and its unread classes named 2026-09-24,
round 2 of fork PR #894's review). At the controller's session end tests/conftest.py joins its live non-daemon threads,
then reads /proc for every live process whose environment carries one of the run's temp roots (or a path under one, a
':'-joined value counted per component), whose cwd is under one, one of whose open file descriptors points under one, or
one of whose arguments is under one, each root compared by its folded spelling and by its realpath, each value and
argument read folded and a relative one from the process's cwd; it waits for the one event it can observe (each holder's
exit) up to a bound, and if any still hold a root the run is red and each is named with its pid, parent, command line,
what it holds the root through and the test PHASE current at its spawn (PYTEST_CURRENT_TEST in the environment it
inherited), or, when that name is not in its environment, a sentence saying the phase is unknown and why. The phase is a
pointer and not the culprit's name: a child a background thread spawns may carry a later phase, another test's, or none
(the fork PR #813 reproduction's bus carried the guard test on 3.10 and no PYTEST_CURRENT_TEST at all on 3.12), so the
witness is the pid and the command line. Keyed on that property, never on a binary's name. The case that wrote this: a
real postal bus started from the peer-notify guard test's revive road with the environment of the test process,
detached, so the test's end never reached it; it kept writing into a shared state root every 30 s and turned another
module's snapshot test red in one CI cell; at the same commit the run ended green. The classes the check does not read
are listed, each with its reason, in the comment above LEAK_EXIT_BOUND_S in tests/conftest.py.

Pinned by execution, each half where it lives. Scanner, over a stand-in root handed to the scan alone: a child holding
the root through TMPDIR, through another name, through one component of a ':'-joined value, through its cwd, through an
open file, through an argument; a root handed through a symlink met by its realpath at a cwd and at a descriptor, and a
value spelled through a symlink outside the root not met (a named unread class); a value or argument spelled with a
doubled separator, a '.' or '..' segment or a leading '//' met as the path it names, a '..' out of the root not met, and
a '..' after a symlink named (the lexical fold's safe side); a relative value or argument met as the path it names from
the child's cwd when it carries the root's name (a root handed as a symlink by its own name and by its target's), not
met where it folds out of the root or names a path elsewhere from that cwd, and one that carries no root's name not read
(the cwd under the root is then the hold); a path inside a longer argument not met (another); a sibling path with the
root's name as a prefix is not the root; a child that exited is not reported; a child with no PYTEST_CURRENT_TEST is
reported with an empty phase; the wait (a holder that exits ends it before the bound; one that never exits is reported
at the bound; each timed over this test's own children, since the wait covers every listed process and a sibling test's
may be listed); this user's unreadable process of the run listed as not judged, and one that started before the scanning
process or sits in another cgroup counted instead, and one that exits during the wait not listed; the thread join (every
non-daemon thread joined, one started during the join too, a daemon thread never waited on, one that outlives the bound
returned); the bound the child runs name; the roots (the controller's and its recorded children's, the lineage a nested
process records itself in, and a dead nested root that two lists name returned once when it resists removal). RunEnd, in
child pytest processes (the procfs cases skip where there is no /proc): a test that leaves a detached child ends the run
red with the process and the phase named and "1 passed" still in the summary, and a child in the root by its cwd alone
is named beside it (the two controls); a child the test gave a built environment during its call phase is named by pid
and command line with the phase stated as unknown; a process leaked two nested pytest runs down, and one leaked by a
nested run a worker started (where pytest-xdist is installed), is the outermost run's finding; holders through an open
file, an argument and a cwd under a symlinked TMPDIR are named, and so is a child holding only values of a root spelled
with a leading '//' through a symlink, met by the root's folded spelling alone; a process holding no path under a root
is not (the residual's witness); a non-dumpable process of the run is listed as not judged and leaves the exit status; a
process a non-daemon thread starts after its test returned is named, and a daemon thread still running is reported; an
idle pool a test left is waited the whole bound and reported as still running (the join's named cost, timed up to the
check's first read of /proc); without procfs the check says so once and leaves the exit status alone, and Scanner's
roots test, which reads no /proc, runs there; a test that leaves nothing ends the run green. The child runs set
ROMP_TESTS_LEAK_EXIT_BOUND_S so a holder that never exits costs a fraction of a second rather than the whole bound; one
run keeps the default, and a holder that exits inside it ends that run green. Guard holds the pytest guard: Scanner
skips under `python -m unittest` after tests.conftest was imported, and runs under pytest. Synthetic throughout: the
leaked processes are `sleep`s and Python sleepers this module starts and stops by the pid it recorded."""
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
Path(os.environ["XDG_STATE_HOME"], "romp").mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # a minted state root reads hosts off (T348)

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
MARKER_ENV = "ROMP_LEAK_CHECK_MARKER"       # set in the child pytest runs below to a scratch dir: the Leaker tests run there alone
BOUND_ENV = "ROMP_TESTS_LEAK_EXIT_BOUND_S"  # conftest's LEAK_EXIT_BOUND_ENV, spelled here so the module runs against a conftest without it
THIS = "tests/test_run_end_leaked_processes.py"
DEVNULL = subprocess.DEVNULL
XDIST_ENV = ("PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "PYTEST_XDIST_TESTRUNUID")
HAS_XDIST = importlib.util.find_spec("xdist") is not None
procfs = unittest.skipUnless(os.path.isdir("/proc"), "the run-end check reads /proc")
child_mode = unittest.skipUnless(os.environ.get(MARKER_ENV), "child mode only: RunEnd runs this in a child pytest process")
PHASE_UNKNOWN = ("the phase at its spawn is unknown, since PYTEST_CURRENT_TEST is not in its environment, because it was "
                 "spawned while no phase was set (between phases or outside a test, as a background thread's late child "
                 "can be) or was given an environment built without it (by the test or by an ancestor process)")


def _under_pytest(case):
    """Skip unless this test runs under pytest, read at TEST time: PYTEST_CURRENT_TEST is set during each pytest phase and
    unset at import, under pytest too, so a module-level check would skip under pytest as well. Until round 2 of fork PR
    #894's review this was a module-level `"tests.conftest" in sys.modules`, true under `python -m unittest` whenever
    another module had imported from tests.conftest first, and Scanner then failed on the missing name."""
    if "PYTEST_CURRENT_TEST" not in os.environ:
        case.skipTest("the check under test is tests/conftest.py's, which pytest runs")


def _gone(pid, bound=15.0):
    """True once `pid` has exited (no /proc entry, or a zombie awaiting its reaper) within `bound` seconds."""
    deadline = time.monotonic() + bound
    while time.monotonic() < deadline:
        try:
            with open("/proc/%d/stat" % pid, "rb") as fh:
                st = fh.read()
            if st[st.rindex(b")") + 1:].split()[0] == b"Z":
                return True
        except (OSError, ValueError, IndexError):
            return True
        time.sleep(0.02)
    return False


def _stop(pid):
    """SIGKILL a pid this module recorded and, when it is our child, reap it."""
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass              # a detached grandchild is init's to reap


def _built_env():
    """An environment built with no path of any root in it: PATH alone."""
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def _under_dir(path, root):
    """Whether `path` is `root` or a path under it, both already resolved."""
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


NON_DUMPABLE = ("import ctypes, sys, time; assert ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0) == 0; "
                "open(sys.argv[1], 'w').close(); time.sleep(float(sys.argv[2]) if sys.argv[2:] else 120)")
#                PR_SET_DUMPABLE 0, then the ready file, then a sleep (120 s, or the seconds given)


class _FakeThread:
    """A stand-in for a thread in the join's pool: `ends` is whether a join ends it; a join of a daemon is a failure.
    `starts`, a (pool, thread) pair, is a thread this one starts while it is being joined: it joins `pool` then."""

    def __init__(self, name, daemon, ends, starts=None):
        self.name, self.daemon, self.ends, self.starts, self.alive, self.joins = name, daemon, ends, starts, True, []

    def is_alive(self):
        return self.alive

    def join(self, timeout=None):
        self.joins.append(timeout)
        if self.daemon:
            raise AssertionError("the join waited on a daemon thread")
        if self.starts:
            pool, started = self.starts
            pool.append(started)
        if self.ends:
            self.alive = False
        else:
            time.sleep(timeout)       # a thread that outlives any join: the call blocks for its whole timeout


class Scanner(unittest.TestCase):
    def setUp(self):
        _under_pytest(self)
        self.conftest = sys.modules["tests.conftest"]
        self.root = tempfile.mkdtemp()                 # a stand-in root inside the run's root: the scan is handed this one alone
        self.addCleanup(shutil.rmtree, self.root, True)

    def _sleeper(self, cwd=None, drop=(), env=None, argv=("sleep", "120"), stdout=DEVNULL, **env_over):
        if env is None:
            env = dict(os.environ)
            for k in drop:
                env.pop(k, None)
            env.update(env_over)
        p = subprocess.Popen(list(argv), env=env, cwd=cwd, stdin=DEVNULL, stdout=stdout, stderr=DEVNULL)
        self.addCleanup(lambda: (_stop(p.pid), _gone(p.pid)))
        return p

    def _scan(self, roots=None):
        scan = self.conftest._processes_holding(roots or [self.root])
        self.assertTrue(scan[2], "procfs is readable here")
        return scan

    def _holders(self, roots=None):
        return self._scan(roots)[0]

    @procfs
    def test_a_child_holding_the_root_is_reported_with_the_test_phase_at_its_spawn_or_none_and_not_once_it_has_exited(self):
        p = self._sleeper(TMPDIR=self.root)
        mine = [h for h in self._holders() if h["pid"] == p.pid]
        self.assertEqual(len(mine), 1, "the child holding the stand-in root through TMPDIR is reported")
        self.assertEqual(mine[0]["via"], ["TMPDIR"])
        self.assertEqual(mine[0]["ppid"], os.getpid())
        self.assertIn("sleep 120", mine[0]["cmd"])
        self.assertEqual(mine[0]["test"], os.environ["PYTEST_CURRENT_TEST"], "the test phase current at its spawn, from the environment it inherited")
        self.assertEqual([h for h in self._holders() if h["pid"] != p.pid], [], "nothing else holds a stand-in root nobody else was handed")
        q = self._sleeper(TMPDIR=self.root, drop=("PYTEST_CURRENT_TEST",))
        theirs = [h for h in self._holders() if h["pid"] == q.pid]
        self.assertEqual(len(theirs), 1, "a child carrying no phase is reported all the same: the property is the root, not the name")
        self.assertEqual(theirs[0]["test"], "", "...with an empty phase, never a guess")
        _stop(p.pid)
        _stop(q.pid)
        self.assertTrue(_gone(p.pid) and _gone(q.pid))
        self.assertEqual(self._holders(), [], "a child that exited holds nothing")

    @procfs
    def test_a_path_under_the_root_in_any_name_a_colon_joined_component_or_the_cwd_counts(self):
        p1 = self._sleeper(XDG_STATE_HOME=os.path.join(self.root, "romp-tests-state-x"))
        p2 = self._sleeper(PATH=os.path.join(self.root, "bin") + os.pathsep + os.environ.get("PATH", ""))
        sub = os.path.join(self.root, "cwd")
        os.mkdir(sub)
        p3 = self._sleeper(cwd=sub)
        by = {h["pid"]: h for h in self._holders()}
        self.assertEqual(by[p1.pid]["via"], ["XDG_STATE_HOME"], "a state root under the run root")
        self.assertEqual(by[p2.pid]["via"], ["PATH"], "one component of a colon-joined value")
        self.assertEqual(by[p3.pid]["via"], ["cwd"], "a working directory under the root")
        self.assertEqual(by[p3.pid]["cwd"], sub)
        gone = os.path.join(self.root, "gone")
        os.mkdir(gone)
        p4 = self._sleeper(env=_built_env(), cwd=gone)
        os.rmdir(gone)                                 # /proc now reads the cwd as "<gone> (deleted)"
        self.assertEqual([h["via"] for h in self._holders([gone]) if h["pid"] == p4.pid], [["cwd"]],
                         "a cwd that IS a removed root still counts: the kernel's ' (deleted)' suffix is dropped")

    @procfs
    def test_an_open_file_or_an_argument_under_the_root_counts_and_a_path_inside_a_longer_argument_does_not(self):
        """extra5-1 at the scan: a child given a built environment and the cwd /, holding the root only through its stdout
        (a file open under it) or only through an argument (whole, or after an option's '='), is reported through "fd" or
        "argv"; one whose argument carries the path inside code text is not: a path inside a longer string is one of the
        classes the check names as unread."""
        with open(os.path.join(self.root, "log"), "w") as log:
            p_fd = self._sleeper(env=_built_env(), cwd="/", stdout=log)
        sleeper = [sys.executable, "-c", "import time; time.sleep(120)"]
        p_arg = self._sleeper(env=_built_env(), cwd="/", argv=sleeper + [os.path.join(self.root, "state")])
        p_opt = self._sleeper(env=_built_env(), cwd="/", argv=sleeper + ["--state=" + os.path.join(self.root, "state")])
        p_list = self._sleeper(env=_built_env(), cwd="/", argv=sleeper + ["/nonexistent" + os.pathsep + os.path.join(self.root, "bin")])
        p_code = self._sleeper(env=_built_env(), cwd="/", argv=sleeper + ["open(%r)" % os.path.join(self.root, "x")])
        by = {h["pid"]: h for h in self._holders()}
        self.assertIn(p_fd.pid, by, "a file open under the root is a hold")
        self.assertIn(p_arg.pid, by, "an argument under the root is a hold")
        self.assertIn(p_opt.pid, by, "the part after an option's '=' under the root is a hold")
        self.assertIn(p_list.pid, by, "one component of a ':'-joined argument under the root is a hold")
        self.assertEqual(by[p_fd.pid]["via"], ["fd"], "a file open under the root, nothing else")
        self.assertEqual(by[p_arg.pid]["via"], ["argv"], "an argument that is a path under the root")
        self.assertEqual(by[p_opt.pid]["via"], ["argv"], "the part after an option's '='")
        self.assertEqual(by[p_list.pid]["via"], ["argv"], "one component of a ':'-joined argument")
        self.assertNotIn(p_code.pid, by, "a path inside code text is not read (a named unread class)")

    @procfs
    def test_a_root_handed_through_a_symlink_is_met_by_its_realpath_and_a_value_spelled_through_an_outside_symlink_is_not(self):
        """extra5-1's symlinked case at the scan: the root handed is a symlink's spelling; /proc resolves a cwd and a
        descriptor, and both are met because each root is compared by its realpath too. The unread class beside it: an
        environment value spelled through a symlink OUTSIDE the root is compared as spelled, never resolved, so it is not
        met, while a cwd reached through that symlink is (the kernel resolves it)."""
        real = os.path.join(self.root, "real")
        os.mkdir(real)
        link = os.path.join(self.root, "link")
        os.symlink(real, link)
        os.mkdir(os.path.join(link, "sub"))
        with open(os.path.join(link, "log"), "w") as log:
            p_fd = self._sleeper(env=_built_env(), cwd="/", stdout=log)
        p_cwd = self._sleeper(env=_built_env(), cwd=os.path.join(link, "sub"))
        by = {h["pid"]: h for h in self._holders([link])}
        self.assertIn(p_cwd.pid, by, "a cwd under the root handed as a symlink is a hold")
        self.assertIn(p_fd.pid, by, "a file open under it is a hold")
        self.assertEqual(by[p_cwd.pid]["via"], ["cwd"], "the cwd, which /proc reads as the realpath, under the root handed as a symlink")
        self.assertEqual(by[p_cwd.pid]["cwd"], os.path.join(real, "sub"))
        self.assertEqual(by[p_fd.pid]["via"], ["fd"], "a descriptor's target, resolved the same way")
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)
        into = os.path.join(outside, "into")
        os.symlink(os.path.join(real, "sub"), into)
        p_val = self._sleeper(env=dict(_built_env(), XDG_STATE_HOME=os.path.join(into, "x")), cwd="/")
        p_via = self._sleeper(env=_built_env(), cwd=into)
        by = {h["pid"]: h for h in self._holders([real])}
        self.assertIn(p_via.pid, by, "a cwd reached through a symlink outside the root is a hold")
        self.assertNotIn(p_val.pid, by, "a value spelled through a symlink outside the root is compared as spelled (a named unread class)")
        self.assertEqual(by[p_via.pid]["via"], ["cwd"], "a cwd reached through that symlink is resolved by the kernel, and met")

    @procfs
    def test_a_path_spelled_with_a_doubled_separator_or_a_dot_segment_is_read_as_the_path_it_names(self):
        """Round 2 of fork PR #894's review: an environment value or an argument naming a path under the root with a
        doubled separator, a '.' segment, a '..' segment that comes back into the root, or a leading '//' is read as the
        path it names (conftest folds each with _lexical before the comparison), in a ':'-joined component and after an
        option's '=' as well; a '..' out of the root, inside the value or at its end, folds to a path outside it and is
        not a hold; and a '..' after a symlink in the root folds lexically, so that value is named though its real path
        lies outside the root (the safe side the conftest comment states). Each child has a built environment and the
        cwd /, so the spelling is its only hold."""
        parent, name = os.path.split(self.root)
        sleeper = [sys.executable, "-c", "import time; time.sleep(120)"]

        def env_child(value, var="XDG_STATE_HOME"):
            return self._sleeper(env=dict(_built_env(), **{var: value}), cwd="/")

        def argv_child(arg):
            return self._sleeper(env=_built_env(), cwd="/", argv=sleeper + [arg])

        met = {
            "a doubled separator": env_child(parent + "//" + name + "/x"),
            "a '.' segment": env_child(parent + "/./" + name + "/x"),
            "a '..' segment back into the root": env_child(parent + "/elsewhere/../" + name + "/x"),
            "a leading '//'": env_child("/" + self.root),
            "a doubled separator in a ':'-joined component": env_child(
                "/usr/share" + os.pathsep + parent + "//" + name + "/share", var="XDG_DATA_DIRS"),
            "a '.' segment in an argument": argv_child(parent + "/./" + name + "/argv"),
            "a doubled separator after an option's '='": argv_child("--state=" + parent + "//" + name + "/s"),
        }
        out_of_root = env_child(self.root + "/../outside-x")
        roots_parent = env_child(self.root + "/..")
        outside = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outside, True)
        link = os.path.join(self.root, "out-link")
        os.symlink(outside, link)
        safe_side = env_child(os.path.join(link, "..", "x"))
        by = {h["pid"]: h for h in self._holders()}
        for what, p in met.items():
            self.assertIn(p.pid, by, "a path under the root spelled with %s is a hold" % what)
        self.assertEqual(by[met["a doubled separator"].pid]["via"], ["XDG_STATE_HOME"])
        self.assertEqual(by[met["a doubled separator in a ':'-joined component"].pid]["via"], ["XDG_DATA_DIRS"])
        self.assertEqual(by[met["a '.' segment in an argument"].pid]["via"], ["argv"])
        self.assertEqual(by[met["a doubled separator after an option's '='"].pid]["via"], ["argv"])
        self.assertNotIn(out_of_root.pid, by, "a '..' out of the root folds to a path outside it")
        self.assertNotIn(roots_parent.pid, by, "a trailing '..' folds to the root's parent")
        self.assertFalse(_under_dir(os.path.realpath(os.path.join(link, "..", "x")), os.path.realpath(self.root)),
                         "the safe-side value's real path is outside the root")
        self.assertIn(safe_side.pid, by, "a '..' after a symlink folds lexically, so the value is named (the safe side)")

    @procfs
    def test_a_relative_path_is_read_from_the_process_cwd_when_it_carries_a_roots_name(self):
        """Round 2 of fork PR #894's review: an environment value or an argument that is a RELATIVE path naming a path
        under the root from the process's cwd is read as that path (conftest joins it to the cwd /proc reads, then folds
        it): the root's name with a tail and alone, from the root's parent; with a '.' or a '..' segment; in a
        ':'-joined component and after an option's '='; and a path relative to another directory that climbs out of it
        with '..'. A root handed as a symlink is met through its own name and through its target's. Not met: a relative
        value that folds out of the root, the same value read from a cwd from which it names a path elsewhere, and a
        sibling whose name has the root's as a prefix. A relative value that carries no root's name is not read, so a
        process whose cwd is under the root is named through its cwd alone. Each child has a built environment, so its
        spelling is its only hold, the child whose cwd is under the root aside."""
        parent, name = os.path.split(self.root)
        sleeper = [sys.executable, "-c", "import time; time.sleep(120)"]

        def env_child(value, cwd=parent, var="XDG_STATE_HOME"):
            return self._sleeper(env=dict(_built_env(), **{var: value}), cwd=cwd)

        def argv_child(arg, cwd=parent):
            return self._sleeper(env=_built_env(), cwd=cwd, argv=sleeper + [arg])

        met = {
            "the root's name and a tail": env_child(name + "/x"),
            "the root's name alone": env_child(name),
            "a '.' segment first": env_child("./" + name + "/x"),
            "a '..' segment back into the root": env_child("elsewhere/../" + name + "/x"),
            "a ':'-joined component": env_child("/usr/share" + os.pathsep + name + "/share", var="XDG_DATA_DIRS"),
            "an argument": argv_child(name + "/argv"),
            "the part after an option's '='": argv_child("--state=" + name + "/s"),
            "a path relative to another directory": argv_child(os.path.relpath(os.path.join(self.root, "argv"), ROOT),
                                                               cwd=ROOT),
        }
        out_of_root = env_child(name + "/../outside-x")
        elsewhere = env_child(name + "/x", cwd="/")
        sib = self.root + "-sibling"
        os.mkdir(sib)
        self.addCleanup(shutil.rmtree, sib, True)
        sibling = env_child(name + "-sibling/x")
        sub = os.path.join(self.root, "sub")
        os.mkdir(sub)
        in_root = self._sleeper(env=dict(_built_env(), XDG_STATE_HOME="x", XDG_DATA_DIRS="../y"), cwd=sub,
                                argv=sleeper + ["z"])
        by = {h["pid"]: h for h in self._holders()}
        for what, p in met.items():
            self.assertIn(p.pid, by, "a relative path under the root from the cwd, spelled as %s, is a hold" % what)
        self.assertEqual(by[met["the root's name and a tail"].pid]["via"], ["XDG_STATE_HOME"])
        self.assertEqual(by[met["a ':'-joined component"].pid]["via"], ["XDG_DATA_DIRS"])
        self.assertEqual(by[met["an argument"].pid]["via"], ["argv"])
        self.assertEqual(by[met["a path relative to another directory"].pid]["via"], ["argv"])
        self.assertNotIn(out_of_root.pid, by, "a relative '..' out of the root folds to a path outside it")
        self.assertNotIn(elsewhere.pid, by, "read from the cwd /, the same value names /<root name>/x")
        self.assertNotIn(sibling.pid, by, "a sibling whose name has the root's as a prefix is not the root")
        self.assertEqual(by[in_root.pid]["via"], ["cwd"],
                         "relative values and an argument that carry no root's name are not read: the cwd is the hold")
        real = os.path.join(self.root, "real")
        os.mkdir(real)
        link = os.path.join(self.root, "link")
        os.symlink(real, link)
        link_named = env_child("link/x", cwd=self.root)
        target_named = env_child("real/x", cwd=self.root)
        by = {h["pid"]: h for h in self._holders([link])}
        self.assertEqual(by.get(link_named.pid, {}).get("via"), ["XDG_STATE_HOME"],
                         "a root handed as a symlink: a relative value naming the symlink is a hold")
        self.assertEqual(by.get(target_named.pid, {}).get("via"), ["XDG_STATE_HOME"],
                         "and one naming its target's directory")

    @procfs
    def test_a_sibling_path_with_the_roots_name_as_a_prefix_and_the_roots_parent_are_not_the_root(self):
        sib = self.root + "-sibling"
        os.mkdir(sib)
        self.addCleanup(shutil.rmtree, sib, True)
        p = self._sleeper(TMPDIR=sib)
        q = self._sleeper(TMPDIR=os.path.dirname(self.root))
        self.assertEqual([h["pid"] for h in self._holders() if h["pid"] in (p.pid, q.pid)], [],
                         "a match is the root itself or a path under it: the parent and a prefix-sharing sibling are neither")

    # The wait's timings below scan this test's own children alone (`pids`): the wait also covers every process listed as
    # not judged, and a scan of every process lists another test's non-dumpable child when one is alive in this cgroup
    # (under pytest-xdist a sibling worker's), so a timing over the whole listing would depend on what the other tests
    # are doing at that moment.
    @procfs
    def test_the_wait_ends_on_the_exit_event_before_the_bound(self):
        p = self._sleeper(TMPDIR=self.root)
        threading.Timer(0.4, _stop, args=(p.pid,)).start()
        t0 = time.monotonic()
        leaked, _unjudged, ok = self.conftest._leaked_run_processes([self.root], bound_s=10.0, pids=[p.pid])
        took = time.monotonic() - t0
        self.assertTrue(ok)
        self.assertEqual(leaked, [], "the holder exited during the wait, so nothing is reported")
        self.assertLess(took, 5.0, "the wait ended on the exit event, not at the 10 s bound: %.2f s" % took)

    @procfs
    def test_a_holder_that_never_exits_is_reported_when_the_bound_ends(self):
        p = self._sleeper(TMPDIR=self.root)
        t0 = time.monotonic()
        leaked, unjudged, ok = self.conftest._leaked_run_processes([self.root], bound_s=0.3, pids=[p.pid])
        took = time.monotonic() - t0
        self.assertTrue(ok)
        self.assertEqual([h["pid"] for h in leaked], [p.pid])
        self.assertEqual(unjudged["listed"], [], "the wait read this test's own child alone")
        self.assertGreaterEqual(took, 0.3, "the bound was waited out for a holder that never exits")

    @procfs
    def test_nothing_waits_when_nothing_holds(self):
        q = self._sleeper(env=_built_env(), cwd="/")          # a live process that holds nothing and is readable
        t0 = time.monotonic()
        leaked, unjudged, ok = self.conftest._leaked_run_processes([self.root], bound_s=10.0, pids=[q.pid])
        self.assertEqual((leaked, unjudged["listed"], ok), ([], [], True))
        self.assertLess(time.monotonic() - t0, 3.0, "no holder, nothing listed, no wait")

    def _non_dumpable(self, *sleep):
        """A child that made itself non-dumpable, holding the stand-in root in its environment, once its ready file says
        the prctl took effect and its environment is unreadable."""
        ready = os.path.join(tempfile.mkdtemp(), "ready")
        p = self._sleeper(argv=[sys.executable, "-c", NON_DUMPABLE, ready] + list(sleep), TMPDIR=self.root)
        deadline = time.monotonic() + 30
        while not os.path.exists(ready):                    # loop-ok: bounded wait for the child's own ready file
            self.assertIsNone(p.poll(), "the non-dumpable child ended before it was ready")
            self.assertLess(time.monotonic(), deadline, "the non-dumpable child never said it was ready")
            time.sleep(0.02)
        with self.assertRaises(PermissionError, msg="its environment is unreadable: the case under test"):
            open("/proc/%d/environ" % p.pid, "rb").close()
        return p

    @procfs
    def test_a_listed_process_is_waited_for_like_a_holder_and_one_that_exits_is_not_listed(self):
        """The wait covers a process listed as not judged as it covers a holder: one that is exiting at session end (here
        a non-dumpable child that sleeps a second) is not listed once it has gone."""
        p = self._non_dumpable("1.0")
        self.assertIn(p.pid, [u["pid"] for u in self._scan()[1]["listed"]], "listed before the wait")
        t0 = time.monotonic()
        _leaked, unjudged, ok = self.conftest._leaked_run_processes([self.root], bound_s=15.0, pids=[p.pid])
        self.assertLess(time.monotonic() - t0, 5.0,
                        "the wait ended on its exit, a second after it was ready, not at the 15 s bound")
        self.assertTrue(ok)
        self.assertNotIn(p.pid, [u["pid"] for u in unjudged["listed"]], "gone by the end of the wait, so not listed")

    def test_the_bound_is_the_default_unless_the_child_runs_name_a_finite_number_of_seconds(self):
        self.assertEqual(BOUND_ENV, self.conftest.LEAK_EXIT_BOUND_ENV, "this module spells conftest's name")
        for value, want in (("0.2", 0.2), ("0", 0.0), ("", 5.0), ("x", 5.0), ("-1", 5.0), ("nan", 5.0), ("inf", 5.0)):
            with mock.patch.dict(os.environ, {BOUND_ENV: value}):
                self.assertEqual(self.conftest._leak_exit_bound(), want, repr(value))
        with mock.patch.dict(os.environ):
            os.environ.pop(BOUND_ENV, None)
            self.assertEqual(self.conftest._leak_exit_bound(), self.conftest.LEAK_EXIT_BOUND_S)

    @procfs
    def test_this_users_unreadable_process_started_after_the_scanner_in_its_cgroup_is_listed_not_judged(self):
        """extra5-2 at the scan: this user's process whose environment cannot be read (a child that made itself
        non-dumpable, as ssh-agent, gpg-agent and op do), started after the scanning process and in its cgroup, is listed
        by pid and command line as not judged, never counted as another user's; one of this user's that started BEFORE the
        scanning process, or sits in another cgroup (a peer session's agent), is counted instead. Each condition is planted
        false at the scan's own reads."""
        p = self._non_dumpable()
        holders, unjudged, _ok = self.conftest._processes_holding([self.root], pids=[p.pid])   # this child alone: the box's count moves
        self.assertEqual(holders, [], "an unreadable process is judged by nothing")
        self.assertEqual(unjudged["other"], 0, "and not counted as another user's")
        self.assertEqual([u["pid"] for u in unjudged["listed"]], [p.pid], "listed as not judged: %r" % (unjudged,))
        self.assertEqual(unjudged["listed"][0]["ppid"], os.getpid())
        self.assertIn("prctl(4, 0, 0, 0, 0)", unjudged["listed"][0]["cmd"], "by its command line")
        self.assertIn(p.pid, [u["pid"] for u in self._scan()[1]["listed"]], "and so in a scan of every process")
        real_read, real_stat, me = self.conftest._proc_read, self.conftest._proc_stat, os.getpid()
        with mock.patch.object(self.conftest, "_proc_read",
                               lambda pid, name: b"0::/elsewhere\n" if (pid == p.pid and name == "cgroup") else real_read(pid, name)):
            _h, elsewhere, _ok = self.conftest._processes_holding([self.root], pids=[p.pid])
        self.assertEqual(elsewhere, {"listed": [], "other": 1}, "in another cgroup: counted, not listed")
        with mock.patch.object(self.conftest, "_proc_stat",
                               lambda pid: real_stat(pid)[:2] + (10 ** 12,) if pid == me else real_stat(pid)):
            _h, older, _ok = self.conftest._processes_holding([self.root], pids=[p.pid])
        self.assertEqual(older, {"listed": [], "other": 1}, "started before the scanning process: counted, not listed")

    def test_the_join_waits_for_a_non_daemon_thread_never_for_a_daemon_one_and_returns_what_outlives_the_bound(self):
        """extra5-3's join, over stand-in threads (the pool is handed in, so no thread of this process is waited on): a
        non-daemon thread a join ends is joined and gone; a daemon thread is never joined and is returned; every
        non-daemon thread is joined, not the first alone; a thread one of them starts while it is being joined is joined
        too; a non-daemon thread that outlives the bound is joined for the bound and returned."""
        ends = _FakeThread("ends", daemon=False, ends=True)
        daemon = _FakeThread("server", daemon=True, ends=False)
        t0 = time.monotonic()
        left = self.conftest._join_live_threads(10.0, among=[ends, daemon])
        self.assertLess(time.monotonic() - t0, 3.0, "nothing waited on the daemon thread")
        self.assertEqual(left, [daemon], "the daemon thread is returned, the joined one is not")
        self.assertEqual((len(ends.joins), daemon.joins), (1, []))
        self.assertGreater(ends.joins[0], 9.0, "joined within the bound")
        first = _FakeThread("first", daemon=False, ends=True)
        second = _FakeThread("second", daemon=False, ends=True)
        left = self.conftest._join_live_threads(10.0, among=[first, second])
        self.assertEqual(left, [], "both non-daemon threads were joined, the second as well as the first")
        self.assertEqual((len(first.joins), len(second.joins)), (1, 1))
        pool = []
        started = _FakeThread("started-during-the-join", daemon=False, ends=True)
        pool.append(_FakeThread("starter", daemon=False, ends=True, starts=(pool, started)))
        left = self.conftest._join_live_threads(10.0, among=pool)
        self.assertEqual(left, [], "the thread started while the join ran was joined too: %r" % ([t.name for t in left],))
        self.assertEqual(len(started.joins), 1)
        stays = _FakeThread("stays", daemon=False, ends=False)
        t0 = time.monotonic()
        left = self.conftest._join_live_threads(0.3, among=[stays])
        took = time.monotonic() - t0
        self.assertEqual(left, [stays], "a non-daemon thread still alive when the bound ran out is returned")
        self.assertGreaterEqual(took, 0.25, "it was given the bound")
        self.assertLess(took, 3.0, "and no more")

    def test_the_run_roots_are_the_controllers_and_its_recorded_childrens_recursively(self):
        pkg = sys.modules["tests"]
        root, child, grandchild = tempfile.mkdtemp(), tempfile.mkdtemp(), tempfile.mkdtemp()
        Path(root, pkg.TEST_ROOT_CHILDREN).write_text(json.dumps({"pid": 1, "root": child}) + "\nnot a record\n" + json.dumps({"pid": 2}) + "\n")
        Path(child, pkg.TEST_ROOT_CHILDREN).write_text(json.dumps({"pid": 1, "root": grandchild}) + "\n")
        self.assertEqual(self.conftest._run_roots(root), [root, child, grandchild])
        self.assertEqual(self.conftest._run_roots(grandchild), [grandchild], "no children file: the root alone")
        live = self.conftest._run_roots()
        self.assertEqual(live[0], self.conftest._TMP_ROOT, "the live list starts with this run's own root")
        self.assertEqual(os.path.realpath(tempfile.gettempdir()), os.path.realpath(live[0]))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root reads a 000-mode directory, so nothing resists removal")
    def test_a_dead_nested_root_that_resists_removal_is_named_once_though_two_lists_name_it(self):
        """The lineage lists a nested root in every root above it, so a parent's removal meets a dead grandchild's root
        twice (through the child's list and its own): one that resists removal (a 000-mode directory inside) is returned
        once."""
        pkg = sys.modules["tests"]
        system = tempfile.mkdtemp()
        top = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        mid = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        low = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        locked = os.path.join(low, "locked")
        os.mkdir(locked)
        os.mkdir(os.path.join(locked, "inside"))
        os.chmod(locked, 0)
        self.addCleanup(shutil.rmtree, system, True)
        self.addCleanup(os.chmod, locked, 0o700)
        dead = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True, check=True)
        pid = int(dead.stdout)                         # exited and reaped: dead
        Path(top, pkg.TEST_ROOT_CHILDREN).write_text("".join(json.dumps({"pid": pid, "root": r}) + "\n" for r in (mid, low)))
        Path(mid, pkg.TEST_ROOT_CHILDREN).write_text(json.dumps({"pid": pid, "root": low}) + "\n")
        self.assertEqual(pkg.remove_dead_children(top, system), [low])
        self.assertFalse(os.path.isdir(mid), "the dead child's root is removed")

    def test_a_nested_process_records_its_root_in_every_root_above_it(self):
        """correctness-1's recording, on synthetic roots and then on this process: the lineage of a process handed a root
        is the lineage that root's owner marker records, then the root; a marker with none, or none readable, makes the
        root alone the lineage; this process is listed in every root of its own lineage. RunEnd's two nested cases pin
        what it is for, at a real run end."""
        pkg = sys.modules["tests"]
        system = tempfile.mkdtemp()
        first = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        worker = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        pkg.write_owner_marker(first, [])
        pkg.write_owner_marker(worker, pkg.root_lineage(first))
        self.assertEqual(pkg.root_lineage(first), [first])
        self.assertEqual(pkg.root_lineage(worker), [first, worker], "a nested process under the worker lists itself in both roots")
        self.assertEqual(pkg.root_lineage(None), [], "a run's first process has no lineage")
        bare = tempfile.mkdtemp(prefix="romp-tests-", dir=system)
        self.assertEqual(pkg.root_lineage(bare), [bare], "no marker: the parent alone")
        Path(bare, pkg.TEST_ROOT_OWNER_MARKER).write_text(json.dumps({"pid": 1, "lineage": "not a list"}))
        self.assertEqual(pkg.root_lineage(bare), [bare], "a lineage that is not a list of roots: the parent alone")
        self.assertEqual(pkg.LINEAGE, pkg.root_lineage(pkg.PARENT_ROOT), "this process's lineage, read at its import")
        for above in pkg.LINEAGE:
            with open(os.path.join(above, pkg.TEST_ROOT_CHILDREN), encoding="utf-8") as fh:
                listed = [json.loads(line) for line in fh.read().splitlines()]
            self.assertIn({"pid": os.getpid(), "root": pkg.TMP_ROOT}, listed, "listed in %s" % above)


# A thread that outlives its test, as a plugin of ONE child run: in the test's call phase a non-daemon thread starts that
# spawns a detached sleeper half a second later, when the test has returned, and a daemon thread starts that waits for ever.
# Written for the child run at run time and loaded there with -p: the threads belong to the child run's process, as the
# scenario under test, and a test module must never leave a thread running in its own process
# (tests/test_thread_stop_census.py holds every thread a test module starts to a stop on every exit path).
LATE_THREAD_PLUGIN = '''\
import os, subprocess, threading, time


def _late():
    time.sleep(0.5)
    p = subprocess.Popen(["sleep", "120"], start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    with open(os.path.join(os.environ["ROMP_LEAK_CHECK_MARKER"], "pid-late"), "w") as fh:
        fh.write(str(p.pid))


def pytest_runtest_call(item):
    threading.Thread(target=_late, name="leaker-late-spawner").start()
    threading.Thread(target=threading.Event().wait, name="leaker-lingering-daemon", daemon=True).start()
'''

# An idle pool a test left, as a plugin of ONE child run (loaded the same way): in the test's call phase a one-worker
# concurrent.futures pool runs one task and is kept, never shut down, so its worker is a live non-daemon thread that only
# threading's exit hooks end. The plugin's sessionfinish, which runs before conftest's trylast one, notes the time and
# wraps conftest's _processes_holding to note the time of its first call, the check's first read of /proc; its
# unconfigure writes the seconds between the two to the marker dir: the join's time, and nothing the check does after
# that read (the wait after it covers every process listed as not judged, and another run's in the cgroup may be
# listed).
IDLE_POOL_PLUGIN = '''\
import concurrent.futures, os, sys, time

_POOLS, _AT = [], {}


def pytest_runtest_call(item):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="leaker-idle-pool")
    pool.submit(int).result()
    _POOLS.append(pool)


def pytest_sessionfinish(session, exitstatus):
    _AT["finish"] = time.monotonic()
    conftest = sys.modules["tests.conftest"]
    scan = conftest._processes_holding

    def first_read_noted(*a, **k):
        _AT.setdefault("read", time.monotonic())
        return scan(*a, **k)
    conftest._processes_holding = first_read_noted


def pytest_unconfigure(config):
    with open(os.path.join(os.environ["ROMP_LEAK_CHECK_MARKER"], "join-seconds"), "w") as fh:
        fh.write(repr(_AT["read"] - _AT["finish"]) if "read" in _AT else "no read of /proc")
'''

# A platform without procfs, simulated for one child run: /proc is absent to os.path.isdir, os.listdir, os.readlink,
# os.stat and open. Written as that run's sitecustomize at run time.
NO_PROCFS_SITECUSTOMIZE = '''\
import builtins, functools, io, os


def _proc(p):
    try:
        p = os.fsdecode(p)
    except TypeError:
        return False
    return p == "/proc" or p.startswith("/proc/")


def _refusing(real):
    # a partial, not a function: a function stored as a class attribute binds (3.10's pathlib keeps os.stat on a class)
    def call(*a, **k):
        if a and not isinstance(a[0], int) and _proc(a[0]):
            raise FileNotFoundError(2, "No such file or directory", a[0])
        return real(*a, **k)
    return functools.partial(call)


_isdir = os.path.isdir
os.path.isdir = functools.partial(lambda p: False if _proc(p) else _isdir(p))
os.listdir, os.readlink, os.stat = _refusing(os.listdir), _refusing(os.readlink), _refusing(os.stat)
builtins.open = io.open = _refusing(builtins.open)
'''


class Guard(unittest.TestCase):
    """fresh-3's pin, unguarded so that it runs under both runners: Scanner skips under `python -m unittest` although
    tests.conftest was imported before it (the base's guard ran it there, and it failed on the missing
    PYTEST_CURRENT_TEST), and runs under pytest (a guard read at import would skip it there too)."""

    def test_scanner_skips_under_unittest_after_conftest_was_imported_and_runs_under_pytest(self):
        env = dict(os.environ)
        for k in ("PYTEST_CURRENT_TEST",) + XDIST_ENV:
            env.pop(k, None)
        u = subprocess.run([sys.executable, "-c", "import sys, unittest, tests.conftest; sys.argv[1:] = ["
                            "'tests.test_run_end_leaked_processes.Scanner']; unittest.main(module=None)"],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        self.assertRegex(u.stderr, r"\nOK \(skipped=\d+\)\n", u.stderr)
        t = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            THIS + "::Scanner::test_the_run_roots_are_the_controllers_and_its_recorded_childrens_recursively"],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(t.returncode, 0, t.stdout + t.stderr)
        self.assertIn("1 passed", t.stdout, "Scanner runs under pytest: " + t.stdout)
        self.assertNotIn("skipped", t.stdout)


class RunEnd(unittest.TestCase):
    """The check at a real session end, in a child pytest process running one Leaker test (below) with the marker set."""

    def setUp(self):
        _under_pytest(self)

    def _child_run(self, test, env_over=None, drop=(), args=(), bound="0.2", also=()):
        """(completed run, {label: pid}, marker dir) for one child pytest run of Leaker::`test` (and the `also` node ids of
        this module), its marker a fresh scratch dir; every pid the run's processes recorded is stopped by this test's
        cleanup. `bound` is the child's leak-exit bound (None: the default); `args` go before the node ids."""
        scratch = tempfile.mkdtemp()
        env = dict(os.environ, **{MARKER_ENV: scratch})
        for k in ("PYTEST_CURRENT_TEST",) + XDIST_ENV + tuple(drop):
            env.pop(k, None)
        if bound is not None:
            env[BOUND_ENV] = bound
        env.update(env_over or {})
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + list(args)
                           + [THIS + "::Leaker::" + test] + [THIS + "::" + a for a in also],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        pids = {}
        for name in os.listdir(scratch):
            if name.startswith("pid-"):
                pids[name[4:]] = int(Path(scratch, name).read_text())
        for pid in pids.values():
            self.addCleanup(lambda pid=pid: (_stop(pid), _gone(pid)))     # the child run's leaks are ours to end before OUR run ends
        return r, pids, scratch

    def _line(self, out, pid):
        """The one report line naming `pid`, or a failure quoting the output."""
        lines = [line for line in out.splitlines() if line.startswith("[tests]   pid %d (parent " % pid)]
        self.assertEqual(len(lines), 1, "one report line names pid %d:\n%s" % (pid, out))
        return lines[0]

    @procfs
    def test_a_run_that_leaves_a_process_holding_its_root_ends_red_and_names_the_process_and_its_test(self):
        """The two controls, red at every head: a detached child inheriting the test's environment (named with the test's
        phase), and one given a built environment whose cwd is in the root (named through cwd)."""
        r, pids, _ = self._child_run("test_leaves_the_two_controls")
        out = r.stdout + r.stderr
        self.assertEqual(sorted(pids), ["cwd", "env"], "the child run's test left its sleepers' pids: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out, "the test itself passed; the run is red for the processes it left behind")
        self.assertIn("process(es) of this run still hold its temp root at run end", out)
        env_line = self._line(out, pids["env"])
        self.assertIn("sleep 120", env_line)
        self.assertRegex(env_line, r"holds the root through [^|]*\bTMPDIR\b", "the run's TMPDIR, among the floor's other names under the root")
        self.assertIn("spawned during " + THIS + "::Leaker::test_leaves_the_two_controls (call)", env_line)
        self.assertIn("| holds the root through cwd |", self._line(out, pids["cwd"]))

    def _named_nowhere(self, out, pid):
        """No holder line in `out`, and no report line names `pid`. Not "nothing said": the child run may list another
        run's non-dumpable process in its cgroup (under pytest-xdist a sibling test's child run) as not judged, a line
        the scheduling decides and these pins do not claim (the comment above LEAK_EXIT_BOUND_S names the class)."""
        self.assertNotIn("hold its temp root", out, "no holder line")
        self.assertEqual([line for line in out.splitlines() if line.startswith("[tests]   pid %d " % pid)], [],
                         "no report line names pid %d:\n%s" % (pid, out))

    @procfs
    def test_a_holder_that_exits_within_the_default_bound_ends_the_run_green(self):
        """The wait at a real run end, with the default bound (no ROMP_TESTS_LEAK_EXIT_BOUND_S): a detached child that holds
        the root and exits a second and a half after its spawn is seen, waited for, gone, and the run ends green with
        no holder line and no line naming it. Under a zero bound the same child is named: the contrast that shows the
        default is the bound that applied (Scanner pins that the wait ends on the exit and not at the bound)."""
        r, pids, _ = self._child_run("test_leaves_a_child_that_exits_soon", bound=None)
        out = r.stdout + r.stderr
        self.assertIn("child", pids, out)
        self.assertEqual(r.returncode, 0, out)
        self._named_nowhere(out, pids["child"])
        r, pids, _ = self._child_run("test_leaves_a_child_that_exits_soon", bound="0")
        out = r.stdout + r.stderr
        self.assertEqual(r.returncode, 1, out)
        self._line(out, pids["child"])

    @procfs
    def test_a_process_carrying_no_test_phase_is_still_reported_by_pid_and_command_line(self):
        """extra5-4: a detached child the test spawns during its CALL phase with an environment it built without
        PYTEST_CURRENT_TEST (Leaker's test_leaves_a_detached_child_with_no_test_phase) is named by pid and command line,
        the run is red, and the phase is stated as unknown in one sentence giving the two causes the check cannot tell
        apart, never as any test's."""
        r, pids, _ = self._child_run("test_leaves_a_detached_child_with_no_test_phase")
        out = r.stdout + r.stderr
        self.assertIn("child", pids, "the child run's test left its sleeper's pid: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out)
        line = self._line(out, pids["child"])
        self.assertIn("sleep 120", line)
        self.assertTrue(line.endswith("| " + PHASE_UNKNOWN), line)
        self.assertNotIn("spawned during", out, "no phase is guessed for it")

    @procfs
    def test_a_process_leaked_two_nested_runs_down_is_the_outermost_runs_finding(self):
        """correctness-1, serially: the child run's test runs a nested pytest, whose test runs another nested pytest that
        leaves a detached sleeper. Each nested run has removed its own root, and the list in it, before the outermost
        run's check reads; the sleeper holds only the innermost run's roots, which the outermost run reads because the
        innermost process listed itself in the outermost run's root at mint time (tests/__init__.py, the lineage)."""
        r, pids, scratch = self._child_run("test_runs_a_nested_run_that_runs_a_nested_leaker")
        out = r.stdout + r.stderr
        self.assertIn("child", pids, "the innermost run left its sleeper's pid: " + out)
        outer = json.loads(Path(scratch, "outer.json").read_text())
        self.assertEqual(outer["standing"], [], "each nested root was gone before the outermost run's check: %r" % (outer,))
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out)
        line = self._line(out, pids["child"])
        self.assertRegex(line, r"holds the root through [^|]*\bTMPDIR\b", "the innermost run's TMPDIR")
        self.assertIn("spawned during " + THIS + "::Leaker::test_leaves_a_detached_child (call)", line)
        self.assertEqual(len(outer["listed"]), 2, "the outermost run's list names both nested roots: %r" % (outer,))

    @procfs
    @unittest.skipUnless(HAS_XDIST, "pytest-xdist is not installed (CI's case; the serial nested case holds the same recording)")
    def test_a_process_leaked_by_a_nested_run_a_worker_started_is_the_controllers_finding(self):
        """correctness-1 under xdist: the child run is `-n 1`; its worker's test runs a nested pytest that leaves a detached
        sleeper. The worker removes its root at its unconfigure, before the controller's check."""
        r, pids, _ = self._child_run("test_runs_a_nested_leaker", args=("-n", "1"))
        out = r.stdout + r.stderr
        self.assertIn("child", pids, "the nested run left its sleeper's pid: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out)
        self.assertRegex(self._line(out, pids["child"]), r"holds the root through [^|]*\bTMPDIR\b")

    @procfs
    def test_holders_through_an_open_file_an_argument_or_a_cwd_under_a_symlinked_tmpdir_are_named(self):
        """extra5-1 at a real run end: the child run is handed a TMPDIR that is a symlink, so its root is spelled through
        it. Four detached children: one inheriting the environment (the control, TMPDIR as spelled), and three given a
        built environment and holding the root only through a file open in it, only through an argument, or only through
        a cwd in it (which /proc reads as the realpath)."""
        scratch = tempfile.mkdtemp()
        real = os.path.join(scratch, "real")
        os.mkdir(real)
        link = os.path.join(scratch, "link")
        os.symlink(real, link)
        r, pids, _ = self._child_run("test_leaves_holders_through_a_file_an_argument_and_a_cwd",
                                     env_over={"TMPDIR": link}, drop=("ROMP_TESTS_SYSTEM_TMPDIR",))
        out = r.stdout + r.stderr
        self.assertEqual(sorted(pids), ["argv", "cwd", "env", "fd"], "the child run's test left its sleepers' pids: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertRegex(self._line(out, pids["env"]), r"holds the root through [^|]*\bTMPDIR\b", "the control")
        self.assertIn("| holds the root through fd |", self._line(out, pids["fd"]))
        self.assertIn("| holds the root through argv |", self._line(out, pids["argv"]))
        self.assertIn("| holds the root through cwd |", self._line(out, pids["cwd"]))

    @procfs
    def test_a_root_spelled_with_a_leading_double_separator_through_a_symlink_is_read_by_its_folded_spelling(self):
        """The root's folded spelling at a real run end (conftest's _spellings): the child run is handed a TMPDIR
        spelled with a leading '//' through a symlink. tempfile keeps exactly two leading separators, so the child run's
        root is spelled that way, and so is every value of it a detached child inherits. Those values are read folded
        (one leading '/'); the root's raw spelling keeps two, and its realpath goes through the symlink's target, so
        only the root's folded spelling meets them. The child's cwd and descriptors are outside the root: the values are
        its only hold."""
        scratch = tempfile.mkdtemp()
        real = os.path.join(scratch, "real")
        os.mkdir(real)
        link = os.path.join(scratch, "link")
        os.symlink(real, link)
        r, pids, marker = self._child_run("test_leaves_a_detached_child_and_records_the_root",
                                          env_over={"TMPDIR": "/" + link}, drop=("ROMP_TESTS_SYSTEM_TMPDIR",))
        out = r.stdout + r.stderr
        self.assertIn("child", pids, out)
        root = Path(marker, "root").read_text()
        self.assertEqual(os.path.dirname(root), "/" + link, "the child run's root keeps the leading '//': " + root)
        self.assertEqual(os.path.dirname(os.path.realpath(root)), os.path.realpath(real), "its realpath: the target's")
        self.assertEqual(r.returncode, 1, out)
        line = self._line(out, pids["child"])
        self.assertRegex(line, r"holds the root through [^|]*\bTMPDIR\b", "the inherited TMPDIR, read folded")
        self.assertNotRegex(line, r"holds the root through [^|]*\b(cwd|fd|argv)\b", "the values are its only hold")

    @procfs
    def test_a_process_holding_no_path_under_a_root_is_not_seen_the_residuals_witness(self):
        """The class the check names as unread, by execution: a detached child given a built environment, the cwd /, and
        nothing open in the root outlives the run, and the run ends green with no holder line and no line naming it. The
        comment above LEAK_EXIT_BOUND_S names this test as that class's witness."""
        r, pids, _ = self._child_run("test_leaves_a_process_holding_no_path_under_a_root")
        out = r.stdout + r.stderr
        self.assertIn("residual", pids, out)
        self.assertEqual(r.returncode, 0, out)
        self._named_nowhere(out, pids["residual"])
        self.assertFalse(_gone(pids["residual"], bound=0.2), "the process outlived the run")

    @procfs
    def test_a_non_dumpable_process_of_the_run_is_listed_as_not_judged_and_leaves_the_exit_status(self):
        """extra5-2 at a real run end: the child run's test leaves a detached child that made itself non-dumpable, and
        nothing else. It is listed by pid and command line as not judged though no holder was found, beside the count of
        the other unreadable processes, and the run stays green."""
        r, pids, _ = self._child_run("test_leaves_a_non_dumpable_child")
        out = r.stdout + r.stderr
        self.assertIn("child", pids, out)
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("1 passed", out)
        self.assertNotIn("hold its temp root", out, "no holder was found")
        self.assertIn("process(es) of this user started during this run, in its cgroup, could not be read and were not judged", out)
        line = self._line(out, pids["child"])
        self.assertIn("prctl(4, 0, 0, 0, 0)", line)
        self.assertTrue(line.endswith("| not judged"), line)
        self.assertRegex(out, r"\[tests\] \d+ other process\(es\) could not be read and were not judged: another user's, or this "
                              r"user's started before this run or in another cgroup\.")

    @procfs
    def test_a_process_a_non_daemon_thread_starts_after_its_test_returned_is_named_and_a_daemon_thread_is_reported(self):
        """extra5-3 at a real run end: a plugin of the child run (LATE_THREAD_PLUGIN) starts, in the test's call phase, a
        non-daemon thread that spawns a detached sleeper half a second later, when the test has returned, and a daemon thread
        that never ends. The check joins the first before it reads /proc, so the sleeper is named (with its phase unknown:
        no phase was set when it spawned); it does not wait for the daemon thread, and reports it."""
        plugdir = tempfile.mkdtemp()
        Path(plugdir, "romp_late_thread_plugin.py").write_text(LATE_THREAD_PLUGIN)
        pythonpath = os.pathsep.join([plugdir] + [p for p in [os.environ.get("PYTHONPATH")] if p])
        r, pids, _ = self._child_run("test_leaves_nothing", env_over={"PYTHONPATH": pythonpath}, bound="1.5",
                                     args=("-p", "romp_late_thread_plugin"))
        out = r.stdout + r.stderr
        self.assertIn("late", pids, "the late thread recorded its sleeper: " + out)
        self.assertEqual(r.returncode, 1, out)
        line = self._line(out, pids["late"])
        self.assertIn("sleep 120", line)
        self.assertTrue(line.endswith("| " + PHASE_UNKNOWN), line)
        threads = [t for t in out.splitlines() if "thread(s) of this process were still running" in t]
        self.assertEqual(len(threads), 1, out)
        self.assertIn("leaker-lingering-daemon (daemon)", threads[0])
        self.assertNotIn("leaker-late-spawner", threads[0], "the non-daemon thread was joined")
        self.assertIn("A process one of them starts after that read is not seen", threads[0])

    @procfs
    def test_an_idle_pool_a_test_left_is_waited_the_whole_bound_and_reported_as_still_running(self):
        """The join's cost the comment above LEAK_EXIT_BOUND_S names, by execution: a plugin of the child run
        (IDLE_POOL_PLUGIN) leaves an idle concurrent.futures pool, whose worker is a non-daemon thread that only
        threading's exit hooks end, and those run at interpreter exit, after the check. The run leaves no process and
        ends green, but the check's join waits the whole bound for the worker and names it as still running. The time
        is the join's alone: from the plugin's sessionfinish to the check's first read of /proc, so the wait after that
        read, which another run's process listed as not judged would lengthen, is not in it."""
        plugdir = tempfile.mkdtemp()
        Path(plugdir, "romp_idle_pool_plugin.py").write_text(IDLE_POOL_PLUGIN)
        pythonpath = os.pathsep.join([plugdir] + [p for p in [os.environ.get("PYTHONPATH")] if p])
        r, pids, scratch = self._child_run("test_leaves_nothing", env_over={"PYTHONPATH": pythonpath}, bound="0.5",
                                           args=("-p", "romp_idle_pool_plugin"))
        out = r.stdout + r.stderr
        self.assertEqual((pids, r.returncode), ({}, 0), out)
        self.assertNotIn("hold its temp root", out)
        threads = [t for t in out.splitlines() if "thread(s) of this process were still running" in t]
        self.assertEqual(len(threads), 1, out)
        self.assertIn("read /proc: leaker-idle-pool_0. A process", threads[0],
                      "the idle worker, a non-daemon thread, alone")
        noted = Path(scratch, "join-seconds").read_text()
        self.assertNotEqual(noted, "no read of /proc", out)
        took = float(noted)
        self.assertGreaterEqual(took, 0.45, "the join waited the whole 0.5 s bound for the idle worker before the "
                                            "check read /proc: %.2f s" % took)

    def test_without_procfs_the_check_says_so_once_and_leaves_the_exit_status_alone(self):
        """tests-3's branch, the only one a platform without procfs runs: under a sitecustomize that hides /proc
        (NO_PROCFS_SITECUSTOMIZE), a run whose test leaves a detached child prints the notice once and exits 0. The same
        run holds the skips to the tests that read /proc: Scanner's roots test, which reads none, runs and passes there."""
        stub = tempfile.mkdtemp()
        Path(stub, "sitecustomize.py").write_text(NO_PROCFS_SITECUSTOMIZE)
        pythonpath = os.pathsep.join([stub] + [p for p in [os.environ.get("PYTHONPATH")] if p])
        r, pids, _ = self._child_run("test_leaves_a_detached_child", env_over={"PYTHONPATH": pythonpath},
                                     also=("Scanner::test_the_run_roots_are_the_controllers_and_its_recorded_childrens_recursively",))
        out = r.stdout + r.stderr
        self.assertIn("child", pids, out)
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("2 passed", out, "the leaking test and the roots test, neither skipped")
        self.assertNotIn("skipped", out)
        self.assertEqual(out.count("[tests] the run-end process check reads /proc and did not run on this platform"), 1, out)
        self.assertEqual(out.count("[tests]"), 1, "the notice and nothing else: " + out)

    def test_a_run_that_leaves_nothing_ends_green_and_says_nothing(self):
        r, pids, _ = self._child_run("test_leaves_nothing")
        out = r.stdout + r.stderr
        self.assertEqual(pids, {})
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("1 passed", out)
        self.assertNotIn("hold its temp root", out)


def _record(label, pid):
    """A Leaker test's record of a process it left: `pid-<label>` in the marker dir, one file per process."""
    Path(os.environ[MARKER_ENV], "pid-" + label).write_text(str(pid))


def _detached(argv=("sleep", "120"), **kw):
    for k in ("stdin", "stdout", "stderr"):
        kw.setdefault(k, DEVNULL)
    return subprocess.Popen(list(argv), start_new_session=True, **kw)


def _nested_run(test):
    """Run Leaker::`test` in a nested pytest process with this process's environment (its phase and xdist names dropped:
    a nested run is its own run) and return what it printed."""
    env = dict(os.environ)
    for k in ("PYTEST_CURRENT_TEST",) + XDIST_ENV:
        env.pop(k, None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", THIS + "::Leaker::" + test],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    return r.stdout + r.stderr


class Leaker(unittest.TestCase):
    """Run only inside RunEnd's child pytest processes (the marker environment name is set there): each test leaves what
    its name says and records each process it leaves in the marker dir."""

    @child_mode
    def test_leaves_a_detached_child(self):
        _record("child", _detached().pid)

    @child_mode
    def test_leaves_a_detached_child_and_records_the_root(self):
        Path(os.environ[MARKER_ENV], "root").write_text(tempfile.gettempdir())
        _record("child", _detached().pid)

    @child_mode
    def test_leaves_a_child_that_exits_soon(self):
        _record("child", _detached(["sleep", "1.5"]).pid)

    @child_mode
    def test_leaves_the_two_controls(self):
        _record("env", _detached().pid)
        cwd = os.path.join(tempfile.gettempdir(), "cwd-control")
        os.mkdir(cwd)
        _record("cwd", _detached(env=_built_env(), cwd=cwd).pid)

    @child_mode
    def test_leaves_a_detached_child_with_no_test_phase(self):
        env = dict(os.environ)
        env.pop("PYTEST_CURRENT_TEST", None)          # an environment the test built without the name, in its call phase
        _record("child", _detached(env=env).pid)

    @child_mode
    def test_leaves_holders_through_a_file_an_argument_and_a_cwd(self):
        root = tempfile.gettempdir()
        _record("env", _detached().pid)
        with open(os.path.join(root, "fd-holder.log"), "w") as log:
            _record("fd", _detached(env=_built_env(), cwd="/", stdout=log).pid)
        _record("argv", _detached([sys.executable, "-c", "import time; time.sleep(120)", os.path.join(root, "argv-holder")],
                                  env=_built_env(), cwd="/").pid)
        cwd = os.path.join(root, "cwd-holder")
        os.mkdir(cwd)
        _record("cwd", _detached(env=_built_env(), cwd=cwd).pid)

    @child_mode
    def test_leaves_a_process_holding_no_path_under_a_root(self):
        _record("residual", _detached(env=_built_env(), cwd="/").pid)

    @child_mode
    def test_leaves_a_non_dumpable_child(self):
        ready = os.path.join(os.environ[MARKER_ENV], "ready")
        p = _detached([sys.executable, "-c", NON_DUMPABLE, ready])
        _record("child", p.pid)
        deadline = time.monotonic() + 30
        while not os.path.exists(ready):                    # loop-ok: bounded wait for the child's own ready file
            self.assertIsNone(p.poll(), "the non-dumpable child ended before it was ready")
            self.assertLess(time.monotonic(), deadline, "the non-dumpable child never said it was ready")
            time.sleep(0.02)

    @child_mode
    def test_runs_a_nested_leaker(self):
        Path(os.environ[MARKER_ENV], "nested-inner.out").write_text(_nested_run("test_leaves_a_detached_child"))

    @child_mode
    def test_runs_a_nested_run_that_runs_a_nested_leaker(self):
        Path(os.environ[MARKER_ENV], "nested-middle.out").write_text(_nested_run("test_runs_a_nested_leaker"))
        pkg = sys.modules["tests"]
        with open(os.path.join(pkg.TMP_ROOT, pkg.TEST_ROOT_CHILDREN), encoding="utf-8") as fh:
            listed = [json.loads(line)["root"] for line in fh.read().splitlines()]
        Path(os.environ[MARKER_ENV], "outer.json").write_text(json.dumps(
            {"listed": listed, "standing": [r for r in listed if os.path.isdir(r)]}))

    @child_mode
    def test_leaves_nothing(self):
        pass


if __name__ == "__main__":
    unittest.main()
