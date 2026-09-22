#!/usr/bin/env python3
"""No process of a run outlives the run (2026-09-22, the reviewer's ruling on fork PR #813's finding): at the controller's
session end tests/conftest.py reads /proc for every live process whose environment carries one of the run's temp roots
(or a path under one, a ':'-joined value counted per component) or whose cwd is under one, waits for the one event it
can observe (each holder's exit) up to a bound, and if any still hold a root the run is red and each is named with its
pid, parent, command line, the names it holds the root through and the test PHASE current at its spawn
(PYTEST_CURRENT_TEST in the environment it inherited). The phase is a pointer and not the culprit's name: a child a
background thread spawns may carry a later phase, another test's, or none (the fork PR #813 reproduction's bus carried
the guard test on 3.10 and no PYTEST_CURRENT_TEST at all on 3.12), so the witness is the pid and the command line, which
the property gives every time. Keyed on that property, never on a binary's name. The case that wrote this: a real postal
bus started from the peer-notify guard test's revive road with the environment of the test process (another module's
module-level port and client-only, and a third module's sessions-file seam), detached, so the test's end never reached
it; it kept writing into a shared state root every 30 s and turned another module's snapshot test red in one CI cell;
at the same commit the run ended green.

Pinned by execution, each half where it lives: the scan over a stand-in root handed to it alone (a child holding the root
through TMPDIR, through another name, through one component of a ':'-joined value, through its cwd; a sibling path with
the root's name as a prefix is not the root; a child that exited is not reported; a child with no PYTEST_CURRENT_TEST is
reported with an empty phase), the wait (a holder that exits ends it before the bound; one that never exits is reported
at the bound), the roots (the controller's and its recorded children's, recursively), and the run end itself in a child
pytest process: a test that leaves a detached child ends the run red with the process and the phase named and "1 passed"
still in the summary, one that leaves a child carrying no phase ends it red naming the pid and the command line and
saying the phase is unknown, and a test that leaves nothing ends it green with nothing said. Synthetic throughout: the
leaked processes are `sleep`s this module starts and stops by the pid it recorded."""
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

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
Path(os.environ["XDG_STATE_HOME"], "romp").mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # a minted state root reads hosts off (T348)

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
MARKER_ENV = "ROMP_LEAK_CHECK_MARKER"       # set in the child pytest runs below: the Leaker tests run there alone
under_conftest = unittest.skipUnless("tests.conftest" in sys.modules, "the check under test is tests/conftest.py's (pytest-only)")
DEVNULL = subprocess.DEVNULL


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


@under_conftest
class Scanner(unittest.TestCase):
    def setUp(self):
        self.conftest = sys.modules["tests.conftest"]
        self.root = tempfile.mkdtemp()                 # a stand-in root inside the run's root: the scan is handed this one alone
        self.addCleanup(shutil.rmtree, self.root, True)

    def _sleeper(self, cwd=None, drop=(), **env_over):
        env = dict(os.environ)
        for k in drop:
            env.pop(k, None)
        env.update(env_over)
        p = subprocess.Popen(["sleep", "120"], env=env, cwd=cwd, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        self.addCleanup(lambda: (_stop(p.pid), _gone(p.pid)))
        return p

    def _holders(self, roots=None):
        holders, unreadable, ok = self.conftest._processes_holding(roots or [self.root])
        self.assertTrue(ok, "procfs is readable here")
        return holders

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

    def test_a_sibling_path_with_the_roots_name_as_a_prefix_and_the_roots_parent_are_not_the_root(self):
        sib = self.root + "-sibling"
        os.mkdir(sib)
        self.addCleanup(shutil.rmtree, sib, True)
        p = self._sleeper(TMPDIR=sib)
        q = self._sleeper(TMPDIR=os.path.dirname(self.root))
        self.assertEqual([h["pid"] for h in self._holders() if h["pid"] in (p.pid, q.pid)], [],
                         "a match is the root itself or a path under it: the parent and a prefix-sharing sibling are neither")

    def test_the_wait_ends_on_the_exit_event_before_the_bound(self):
        p = self._sleeper(TMPDIR=self.root)
        threading.Timer(0.4, _stop, args=(p.pid,)).start()
        t0 = time.monotonic()
        leaked, _unreadable, ok = self.conftest._leaked_run_processes([self.root], bound_s=10.0)
        took = time.monotonic() - t0
        self.assertTrue(ok)
        self.assertEqual(leaked, [], "the holder exited during the wait, so nothing is reported")
        self.assertLess(took, 5.0, "the wait ended on the exit event, not at the 10 s bound: %.2f s" % took)

    def test_a_holder_that_never_exits_is_reported_when_the_bound_ends(self):
        p = self._sleeper(TMPDIR=self.root)
        t0 = time.monotonic()
        leaked, _unreadable, ok = self.conftest._leaked_run_processes([self.root], bound_s=0.3)
        took = time.monotonic() - t0
        self.assertTrue(ok)
        self.assertEqual([h["pid"] for h in leaked], [p.pid])
        self.assertGreaterEqual(took, 0.3, "the bound was waited out for a holder that never exits")

    def test_nothing_waits_when_nothing_holds(self):
        t0 = time.monotonic()
        leaked, _unreadable, ok = self.conftest._leaked_run_processes([self.root], bound_s=10.0)
        self.assertEqual((leaked, ok), ([], True))
        self.assertLess(time.monotonic() - t0, 3.0, "no holder, no wait")

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


@under_conftest
class RunEnd(unittest.TestCase):
    """The check at a real session end, in a child pytest process running one Leaker test (below) with the marker set."""

    def _child_run(self, test):
        scratch = tempfile.mkdtemp()
        marker = os.path.join(scratch, "pid.txt")
        env = dict(os.environ, **{MARKER_ENV: marker})
        env.pop("PYTEST_CURRENT_TEST", None)
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            "tests/test_run_end_leaked_processes.py::Leaker::" + test],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        pid = int(Path(marker).read_text()) if os.path.exists(marker) else None
        if pid:
            self.addCleanup(lambda: (_stop(pid), _gone(pid)))     # the child run's leak is ours to end before OUR run ends
        return r, pid

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_a_run_that_leaves_a_process_holding_its_root_ends_red_and_names_the_process_and_its_test(self):
        r, pid = self._child_run("test_leaves_a_detached_child")
        out = r.stdout + r.stderr
        self.assertIsNotNone(pid, "the child run's test left its sleeper's pid: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out, "the test itself passed; the run is red for the process it left behind")
        self.assertIn("process(es) of this run still hold its temp root at run end", out)
        self.assertIn("[tests]   pid %d (parent " % pid, out)
        self.assertIn("sleep 120", out)
        self.assertRegex(out, r"holds the root through [^|\n]*\bTMPDIR\b", "the run's TMPDIR, among the floor's other names under the root")
        self.assertIn("spawned during tests/test_run_end_leaked_processes.py::Leaker::test_leaves_a_detached_child (call)", out)
        _stop(pid)
        self.assertTrue(_gone(pid), "the sleeper is stopped by the pid the child recorded")

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_a_process_carrying_no_test_phase_is_still_reported_by_pid_and_command_line(self):
        """The phase is best-effort and the report says so (the fixup of 2026-09-22, the verifier's finding: the fork PR
        #813 reproduction's bus on 3.12 carried no PYTEST_CURRENT_TEST, its spawn falling after the call phase): a child
        spawned with the name removed from its environment is named by pid and command line, the run is red, and the
        phase reads as unknown rather than as any test's."""
        r, pid = self._child_run("test_leaves_a_detached_child_with_no_test_phase")
        out = r.stdout + r.stderr
        self.assertIsNotNone(pid, "the child run's test left its sleeper's pid: " + out)
        self.assertEqual(r.returncode, 1, out)
        self.assertIn("1 passed", out)
        self.assertIn("[tests]   pid %d (parent " % pid, out)
        self.assertIn("sleep 120", out)
        self.assertIn("spawned during no test phase (PYTEST_CURRENT_TEST is not in its environment: spawned between phases, as a "
                      "background thread's child can be, or outside a test)", out)
        self.assertNotIn("spawned during tests/", out, "no phase is guessed for it")
        _stop(pid)
        self.assertTrue(_gone(pid))

    @unittest.skipIf(os.environ.get(MARKER_ENV), "child mode")
    def test_a_run_that_leaves_nothing_ends_green_and_says_nothing(self):
        r, pid = self._child_run("test_leaves_nothing")
        out = r.stdout + r.stderr
        self.assertIsNone(pid)
        self.assertEqual(r.returncode, 0, out)
        self.assertIn("1 passed", out)
        self.assertNotIn("hold its temp root", out)


class Leaker(unittest.TestCase):
    """Run only inside RunEnd's child pytest processes (the marker environment name is set there): one test leaves a
    detached sleeper that inherits the child run's environment (TMPDIR is that run's root), the other leaves nothing."""

    @unittest.skipUnless(os.environ.get(MARKER_ENV), "child mode only: RunEnd runs this in a child pytest process")
    def test_leaves_a_detached_child(self):
        p = subprocess.Popen(["sleep", "120"], start_new_session=True, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        Path(os.environ[MARKER_ENV]).write_text(str(p.pid))

    @unittest.skipUnless(os.environ.get(MARKER_ENV), "child mode only: RunEnd runs this in a child pytest process")
    def test_leaves_a_detached_child_with_no_test_phase(self):
        env = dict(os.environ)
        env.pop("PYTEST_CURRENT_TEST", None)          # what a background thread's spawn between phases inherits
        p = subprocess.Popen(["sleep", "120"], env=env, start_new_session=True, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
        Path(os.environ[MARKER_ENV]).write_text(str(p.pid))

    @unittest.skipUnless(os.environ.get(MARKER_ENV), "child mode only: RunEnd runs this in a child pytest process")
    def test_leaves_nothing(self):
        pass


if __name__ == "__main__":
    unittest.main()
