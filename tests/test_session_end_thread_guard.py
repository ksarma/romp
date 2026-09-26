#!/usr/bin/env python3
"""tests/conftest.py's session-end thread guard (2026-09-26): at the end of each process's session, the one serial
process or each pytest-xdist worker, a non-daemon thread still running after the guard's cap fails the process's last
test at teardown, named with its target and stack.

Why it exists. A test that leaves a non-daemon thread running keeps its process from exiting. Run serially, the run hung
until CI's job cap cancelled the cell, which was a red cell. Under pytest-xdist the controller kills a worker that has not
exited 10 s after its session and the run passes, so the fork's Linux cells lost that signal when they moved to two
workers (2026-09-25). A worker's stdout goes to /dev/null and its exit status is not read, so the guard reports through
the one thing a worker sends the controller, a test report: the teardown phase's, printed by the controller as `ERROR at
teardown of <the worker's last test>` and counted in the run's exit status.

Pinned by running pytest in a child over synthetic files in a scratch directory outside tests/, with tests/conftest.py
loaded as a plugin (`-p tests.conftest`), serially and under -n 2 (the shape tests/test_served_tests_require.py and
tests/test_tempdir_hygiene.py use). The child's environment is built from a rule (PATH, a fresh HOME and TMPDIR, the
checkout on PYTHONPATH, the locale, PYTHON_GIL and LD_LIBRARY_PATH when this process has them, and the plant's own output
directory), never this process's environment filtered, since collecting the suite writes hundreds of variables at import.
The children run with CI's pytest-timeout flags when pytest-timeout is installed (CI installs it on every cell), so the
guard's exclusion of that plugin's own timer, alive through every test's teardown, is exercised by the green runs.

- A LEAKED non-daemon thread (it waits on an event the scratch conftest sets only at pytest_unconfigure, after the guard
  has run) fails the run, serially and under -n 2, with exactly one error, whose text names the thread, its target and
  a frame of its stack; under -n 2 that text is in the controller's output under a worker's `[gwN]` line, which is how
  the report is shown to have reached the controller. Daemon threads alive at the same moment are not named. Serially,
  an idle ThreadPoolExecutor worker (a pool left open, and an event loop's default executor, the loop never closed) is
  named too, with a label naming both causes: the guard's stricter reading, which the conftest's comment states, and the
  message says such a worker would not have hung a serial run. These runs shorten the guard's cap to LEAK_CAP_S through the scratch conftest, so a leak costs the
  pins seconds and not the full cap.
- Threads that END WITHIN THE CAP (each test starts one that sleeps WITHIN_S and exits) and DAEMON threads that run past
  the session (one per test, released at unconfigure) leave the run green, serially and under -n 2, at the guard's own
  cap. The guard's wait is WITNESSED, not assumed: the scratch conftest records at pytest_sessionfinish, which runs after
  the guard, which plant threads are alive. Every within-cap thread must be gone (the guard joined it; without the guard
  the last test's thread, started milliseconds earlier, is still sleeping) and every daemon thread still alive (it ran
  through the guard and was not waited for or named). And the wait must be a join, which returns when its thread ends,
  not a sleep through the cap: each within-cap thread writes its end time as its last act, and the session must finish
  within half the cap of the process's last one (it finishes milliseconds after; a guard that slept its cap would finish
  nine seconds after).
- The guard runs AFTER THE RUNNER HAS TORN DOWN EVERY FIXTURE. The scratch conftest carries two autouse fixtures, one
  session-scoped and one function-scoped, each starting a non-daemon thread that waits on its own event and is stopped
  and joined only at the fixture's teardown. Every run above stays free of their names and the green runs pass, so a
  thread a fixture stops at teardown is never waited for or named. A guard moved before the runner's teardown (tryfirst,
  or no ordering, since pytest's runner plugin registers before any conftest and pluggy calls later registrations first)
  waits its cap for them and fails the green runs naming them.

- A thread listed while its start() is still running, which Thread.join refuses with a RuntimeError, is read again on
  the guard's next pass rather than raised (JoinRace, in this process under the conftest: a thread never started, which
  join refuses the same way, stands in for it). The pin patches the guard's own binding of threading.enumerate, so no
  other thread's call can take its fake reads; and a test's leaked patch of the process-wide threading.enumerate does
  not hide a live thread from the guard.
- pytest-timeout's timer is matched by a `pytest_timeout` prefix of its name or of its function's module, as
  thread_census matches it, so a plugin release that moves the function into a submodule still leaves it unwaited
  (TimeoutTimerMatch, in this process; CI installs the plugin unpinned). Other timers and threads are still waited for.

Each child-run pin was run with the guard removed from tests/conftest.py and fails there: the leak runs pass (exit 0, no
error) and the green runs' witness finds the within-cap threads alive at sessionfinish. Synthetic fixtures only; no
kernel, no network.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
HAS_XDIST = importlib.util.find_spec("xdist") is not None
# CI's Run pytest flags for pytest-timeout: its timer for the running test is alive through the guard's check
TIMEOUT_FLAGS = ["--timeout=600", "--timeout-method=thread"] if importlib.util.find_spec("pytest_timeout") else []

EXECUTOR_LABEL = "(a ThreadPoolExecutor worker: a pool, or an asyncio loop's default executor, left without shutdown)"
LEAK_CAP_S = 2.0      # the guard's cap in the leak runs: long enough to be a real wait, short enough to cost little
WITHIN_S = 1.0        # a within-cap thread's life after its test: a tenth of the guard's own cap
TESTS = 4             # tests in the plant, each starting its threads: every worker's last test starts some

SHARED = '''\
import threading
RELEASE = threading.Event()     # set by the scratch conftest at pytest_unconfigure, after the guard has run
'''

CONFTEST = '''\
import json, os, sys, threading, time
import pytest
import plant_shared

CAP = {cap!r}                   # None keeps the guard's own cap


def pytest_configure(config):
    if CAP is not None:
        sys.modules["tests.conftest"].THREAD_GUARD_CAP_S = CAP


def pytest_sessionfinish(session):
    # the witness, after the guard (it ran in the last test's teardown): the plant threads alive now, the time, the cap
    alive = sorted(t.name for t in threading.enumerate() if t.name.startswith("plant-"))
    rec = dict(alive=alive, t=time.monotonic(), cap=sys.modules["tests.conftest"].THREAD_GUARD_CAP_S)
    with open(os.path.join(os.environ["PLANT_OUT"], "finish-%d.json" % os.getpid()), "w") as f:
        json.dump(rec, f)


def pytest_unconfigure(config):
    plant_shared.RELEASE.set()  # the leaked and daemon threads end, so the process can exit


def _fixture_thread(tag):
    # a non-daemon thread that only this fixture's teardown ends: alive through the test, stopped and joined when the
    # runner tears the fixture down, which must happen before the guard reads the threads
    stop = threading.Event()
    t = threading.Thread(target=stop.wait, args=(120,), name="plant-fx-" + tag)
    t.start()
    with open(os.path.join(os.environ["PLANT_OUT"], "started-%d-fx-%s.json" % (os.getpid(), tag)), "w") as f:
        json.dump([[t.name, t.daemon]], f)
    yield
    stop.set()
    t.join()


@pytest.fixture(scope="session", autouse=True)
def plant_session_thread():
    yield from _fixture_thread("session")


@pytest.fixture(autouse=True)
def plant_function_thread(request):
    yield from _fixture_thread(request.node.name)
'''

PLANT = '''\
import concurrent.futures, json, os, threading, time
import plant_shared

WITHIN_S = {within!r}
POOL = []


def _within_cap():
    time.sleep(WITHIN_S)                    # ends on its own, inside the guard's cap
    name = threading.current_thread().name
    with open(os.path.join(os.environ["PLANT_OUT"], "ended-%d-%s.json" % (os.getpid(), name)), "w") as f:
        json.dump(time.monotonic(), f)      # its last act: the thread returns right after this write


def _daemon():
    plant_shared.RELEASE.wait(120)          # runs past the session: the guard must neither wait for it nor name it


def _leaked():
    plant_shared.RELEASE.wait(120)          # a non-daemon thread still running when the session ends


def _start(tag, threads):
    for t in threads:
        t.start()
    with open(os.path.join(os.environ["PLANT_OUT"], "started-%d-%s.json" % (os.getpid(), tag)), "w") as f:
        json.dump([[t.name, t.daemon] for t in threads], f)
'''

GREEN_TEST = '''
def test_{i}():
    _start("{i}", [threading.Thread(target=_within_cap, name="plant-within-cap-{i}"),
                   threading.Thread(target=_daemon, name="plant-daemon-{i}", daemon=True)])
'''

DAEMON_TEST = '''
def test_{i}():
    _start("{i}", [threading.Thread(target=_daemon, name="plant-daemon-{i}", daemon=True)])
'''

LEAK_TEST = '''
def test_leak():
    _start("leak", [threading.Thread(target=_leaked, name="plant-leaked")])
'''

POOL_TEST = '''
def test_pool_left_open():
    pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-pool")
    pool.submit(int).result()
    POOL.append(pool)                       # kept referenced and never shut down: its worker idles


def test_event_loop_left_open():
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(loop.run_in_executor(None, int))
    POOL.append(loop)                       # never closed: its default executor's worker idles
'''


class SessionEndThreadGuard(unittest.TestCase):
    def _run(self, plant, *, cap=None, workers=None):
        """pytest in a child over the plant `plant` (PLANT's helpers plus test functions), tests/conftest.py loaded as a
        plugin. Returns (exit status, the child's output, {pid: [[name, daemon]] started}, {pid: {within-cap thread name:
        its end time}}, {pid: {"alive": plant threads alive at pytest_sessionfinish, "t": that time, "cap": the guard's
        cap}}), the times from each process's monotonic clock."""
        d = os.path.realpath(tempfile.mkdtemp(prefix="tg-"))       # resolved: macOS temp dirs sit under a symlink
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        case, out, home, tmp = (os.path.join(d, n) for n in ("case", "out", "home", "tmp"))
        for p in (case, out, home, tmp):
            os.makedirs(p)
        for name, body in (("plant_shared.py", SHARED), ("conftest.py", CONFTEST.format(cap=cap)),
                           ("test_plant.py", PLANT.format(within=WITHIN_S) + plant)):
            with open(os.path.join(case, name), "w") as f:
                f.write(body)
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": home, "TMPDIR": tmp, "PYTHONPATH": REPO,
               "PYTHONDONTWRITEBYTECODE": "1", "PLANT_OUT": out}
        # the locale, the free-threaded build's GIL setting, and the library path setup-python exports on Linux for the
        # interpreter's shared library
        env.update((k, os.environ[k]) for k in ("LANG", "LC_ALL", "LC_CTYPE", "PYTHON_GIL", "LD_LIBRARY_PATH")
                   if k in os.environ)
        argv = [sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-q", "--rootdir", case]
        argv += TIMEOUT_FLAGS + (["-n", str(workers)] if workers is not None else []) + ["test_plant.py"]
        r = subprocess.run(argv, cwd=case, env=env, capture_output=True, text=True, timeout=180)
        started, ended, finish = {}, {}, {}
        for name in sorted(os.listdir(out)):
            with open(os.path.join(out, name)) as f:
                data = json.load(f)
            kind, rest = name[:-len(".json")].split("-", 1)
            pid, _, tag = rest.partition("-")
            if kind == "started":
                started.setdefault(int(pid), []).extend(data)
            elif kind == "ended":
                ended.setdefault(int(pid), {})[tag] = data
            else:
                finish[int(pid)] = data
        return r.returncode, r.stdout + r.stderr, started, ended, finish

    # ── a leaked non-daemon thread fails the run ─────────────────────────────────────────────────────────────────────

    def _assert_leak_reported(self, rc, out, started):
        self.assertIn("plant-leaked", {n for names in started.values() for n, _daemon in names}, "the plant ran:\n" + out)
        self.assertEqual(rc, 1, "a leaked non-daemon thread fails the run:\n" + out)
        self.assertEqual(len(re.findall(r"ERROR at teardown of test_", out)), 1, "one error, at a teardown:\n" + out)
        self.assertRegex(out, r"\n1 error\b|, 1 error\b", out)
        self.assertEqual(out.count("thread 'plant-leaked'"), 1, "the report names the leaked thread once:\n" + out)
        self.assertIn("thread 'plant-leaked' (ident ", out)
        self.assertIn("runs test_plant._leaked\n", out, "the report names the thread's target")
        self.assertIn("in _leaked\n    plant_shared.RELEASE.wait(120)", out,
                      "the report carries the thread's stack, down to the plant's frame")
        self.assertIn("session-end thread guard", out, "the report says what made it")
        self.assertNotIn("plant-daemon", out, "daemon threads alive at the same moment are not named")
        self.assertNotIn("plant-fx-", out, "threads the fixtures stop at teardown are not named")

    def test_a_leaked_non_daemon_thread_fails_a_serial_run_and_the_report_names_it(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + LEAK_TEST + POOL_TEST
        rc, out, started, _ended, _finish = self._run(plant, cap=LEAK_CAP_S)
        self._assert_leak_reported(rc, out, started)
        self.assertIn("thread 'plant-pool_0'", out, "an idle executor worker left open is named too:\n" + out)
        self.assertIn("thread 'asyncio_0'", out, "so is an event loop's default-executor worker, the loop never closed")
        self.assertEqual(out.count(EXECUTOR_LABEL), 2, "both executor workers carry the label that names both causes:\n" + out)
        self.assertIn("unless every thread named is an idle concurrent.futures worker", out,
                      "the message does not claim such a worker would have hung a serial run")
        self.assertIn("after up to %g s for each to end" % LEAK_CAP_S, out, "the cap the scratch conftest set was the one used")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_leaked_non_daemon_thread_fails_the_run_and_the_report_reaches_the_controller(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + LEAK_TEST
        rc, out, started, _ended, finish = self._run(plant, cap=LEAK_CAP_S, workers=2)
        self._assert_leak_reported(rc, out, started)
        self.assertEqual(len(finish), 3, "a controller and two workers each reached pytest_sessionfinish:\n" + out)
        # the error came from a worker (its [gwN] line under the section header) and is printed by the controller, the only
        # process whose output this captures: a worker's own stdout goes to /dev/null
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    # ── threads that end within the cap, and daemon threads, leave the run green ─────────────────────────────────────

    def _assert_green_and_waited(self, rc, out, started, ended, finish):
        self.assertEqual(rc, 0, "threads that end within the cap and daemon threads do not fail the run:\n" + out)
        self.assertIn("%d passed" % TESTS, out, out)
        self.assertNotIn("error", out.lower(), out)
        names = sorted(n for ns in started.values() for n, _daemon in ns if not n.startswith("plant-fx-"))
        expected = ["plant-within-cap-%d" % i for i in range(TESTS)] + ["plant-daemon-%d" % i for i in range(TESTS)]
        self.assertEqual(names, sorted(expected), "the plant started its threads:\n" + out)
        # the fixtures' threads: one per test from the function-scoped fixture, and one in every process that ran tests
        # from the session-scoped one, each stopped only by its fixture's teardown. A guard that ran before the runner's
        # teardown (tryfirst, or no ordering at all, since the runner's plugin registers before any conftest) would wait
        # its cap for them and then fail the run naming them.
        fx = [n for ns in started.values() for n, _daemon in ns if n.startswith("plant-fx-")]
        self.assertEqual(sorted(n for n in fx if n != "plant-fx-session"), ["plant-fx-test_%d" % i for i in range(TESTS)],
                         "the function-scoped fixture started a thread for each test:\n" + out)
        self.assertEqual(fx.count("plant-fx-session"), len(ended), "the session-scoped fixture started a thread in each "
                         "process that ran tests:\n" + out)
        self.assertNotIn("plant-fx-", out, "threads the fixtures stop at teardown are not named")
        for pid, ns in started.items():
            self.assertIn(pid, finish, "the process that started threads reached pytest_sessionfinish:\n" + out)
            for name, daemon in ns:
                if daemon:
                    self.assertIn(name, finish[pid]["alive"], "a daemon thread ran through the guard, neither waited for "
                                                              "nor named")
                else:
                    self.assertNotIn(name, finish[pid]["alive"], "the guard waited for the within-cap thread %s to end "
                                     "before the session finished (without the guard it is still running)" % name)
            # and the wait was a join, returning when the thread ended, not a sleep through the cap: the session finished
            # moments after the process's last within-cap thread ended, far inside the cap
            gap = finish[pid]["t"] - max(ended[pid].values())
            self.assertLess(gap, finish[pid]["cap"] / 2, "the session finished %.2f s after the last within-cap thread "
                            "ended: the guard kept waiting after the thread it waited for had ended" % gap)

    def test_threads_that_end_within_the_cap_and_daemon_threads_leave_a_serial_run_green(self):
        self._assert_green_and_waited(*self._run("".join(GREEN_TEST.format(i=i) for i in range(TESTS))))

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_threads_that_end_within_the_cap_and_daemon_threads_leave_a_two_worker_run_green(self):
        self._assert_green_and_waited(*self._run("".join(GREEN_TEST.format(i=i) for i in range(TESTS)), workers=2))


def _function_in(module):
    """A callable whose __module__ is `module`, standing in for a plugin's function (never called)."""
    def timeout_timer(*_a):
        pass
    timeout_timer.__module__ = module
    return timeout_timer


@unittest.skipUnless("tests.conftest" in sys.modules, "the guard is tests/conftest.py's (pytest-only)")
class TimeoutTimerMatch(unittest.TestCase):
    """pytest-timeout's timer is matched the way tests/conftest.py's thread_census matches it, by a `pytest_timeout`
    PREFIX of the thread's name or of its callable's module, so a release that moves the plugin's function into a
    submodule (CI installs pytest-timeout unpinned) does not make every cell wait the cap and fail on the timer. The
    threads here are built and never started: the match reads only their attributes."""

    def test_the_timer_is_not_guarded_when_its_function_moves_into_a_submodule(self):
        cf = sys.modules["tests.conftest"]
        moved = threading.Timer(600, _function_in("pytest_timeout._core"))
        moved.name = "pytest_timeout tests/test_x.py::test_y"          # the name the plugin gives its timer
        self.assertFalse(cf._guarded_thread(moved), "a submodule's timer, named as the plugin names it, is excluded")
        renamed = threading.Timer(600, _function_in("pytest_timeout._core"))
        self.assertFalse(cf._guarded_thread(renamed), "matched by its function's module alone, whatever its name")
        today = threading.Timer(600, _function_in("pytest_timeout"))
        self.assertFalse(cf._guarded_thread(today), "the plugin's function as it is today")

    def test_other_non_daemon_timers_are_still_guarded(self):
        cf = sys.modules["tests.conftest"]
        self.assertTrue(cf._guarded_thread(threading.Timer(600, _function_in("kernel.kernel"))),
                        "a product timer is waited for")
        self.assertTrue(cf._guarded_thread(threading.Thread(target=_function_in("tests.test_x"), name="plant-timer")),
                        "a plain thread is waited for")


@unittest.skipUnless("tests.conftest" in sys.modules, "the guard is tests/conftest.py's (pytest-only)")
class ThreadReportLabel(unittest.TestCase):
    """The guard's report labels a ProcessPoolExecutor's manager thread, another worker the interpreter wakes at exit.
    Stood in for by a never-started Thread subclass carrying the manager thread's module and name, so no process is
    spawned; the report reads only the thread's type and attributes."""

    def test_a_process_pool_manager_thread_is_labelled(self):
        cf = sys.modules["tests.conftest"]
        manager = type("_ExecutorManagerThread", (threading.Thread,), {"__module__": "concurrent.futures.process"})(
            name="plant-manager")
        report = cf._thread_report(manager, {})
        self.assertIn("runs concurrent.futures.process._ExecutorManagerThread.run (a ProcessPoolExecutor's manager "
                      "thread: a pool left without shutdown)", report)


@unittest.skipUnless("tests.conftest" in sys.modules, "the guard is tests/conftest.py's (pytest-only)")
class JoinRace(unittest.TestCase):
    def test_a_thread_listed_before_its_start_returned_is_read_again_not_raised(self):
        """Thread.join raises RuntimeError on a thread whose start() has not returned yet (threading.enumerate lists it
        from the moment start() puts it in the starting set). The guard passes over it and reads the list again, inside
        the same deadline. Stood in for by a thread never started, which join refuses the same way, listed once."""
        cf = sys.modules["tests.conftest"]
        mid_start = threading.Thread(target=int, name="plant-mid-start")
        reads = [[threading.main_thread(), mid_start], [threading.main_thread()]]
        # the guard's own binding, not threading.enumerate: under xdist other tests' threads are still running, and one of
        # them calling the process-wide function mid-patch would take the fake first read and leave this pin vacuous
        with mock.patch.object(cf, "_enumerate", side_effect=lambda: reads.pop(0) if len(reads) > 1 else reads[0]):
            self.assertEqual(cf.threads_left_at_session_end(5.0), [])
        self.assertEqual(reads, [[threading.main_thread()]], "the guard read the list a second time")

    def test_a_leaked_patch_of_threading_enumerate_does_not_hide_a_thread_from_the_guard(self):
        """The guard binds threading.enumerate at import, as it binds time.monotonic, so a test that patched the
        process-wide function and left the patch in place cannot empty the guard's list."""
        cf = sys.modules["tests.conftest"]
        stop = threading.Event()
        t = threading.Thread(target=stop.wait, args=(60,), name="plant-hidden")
        t.start()
        self.addCleanup(t.join)
        self.addCleanup(stop.set)
        with mock.patch.object(threading, "enumerate", return_value=[threading.main_thread()]):
            left = cf.threads_left_at_session_end(0.2)
        self.assertIn(t, left, "the guard still read the live thread list")


if __name__ == "__main__":
    unittest.main()
