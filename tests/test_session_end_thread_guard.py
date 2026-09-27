#!/usr/bin/env python3
"""tests/conftest.py's session-end thread guard (2026-09-26): at the end of each process's session, the one serial
process or each pytest-xdist worker, a non-daemon thread still running after the guard's cap fails the process's last
test at teardown, named with its target and stack.

Why it exists. A non-daemon thread still running when the interpreter exits keeps its process from exiting. Run serially,
the run hangs until the thread ends or CI's job cap cancels the cell, which is a red cell. Under pytest-xdist the
controller kills a worker still alive when the run ends and the run passes, so the fork's Linux cells lost that signal
when they moved to two workers (2026-09-25). Two kinds of thread the guard names do not keep the process from exiting,
and the guard fails on them too: an idle concurrent.futures worker and a thread stopped only after the check
(tests/conftest.py's comment on the guard says why). A worker's stdout goes to /dev/null and its exit status is not
read, so the guard reports through the one thing a worker sends the controller, a test report: the teardown phase's,
printed by the controller as `ERROR at teardown of <the worker's last test>` and counted in the run's exit status.

Pinned by running pytest in a child over synthetic files in a scratch directory outside tests/, with tests/conftest.py
loaded as a plugin (`-p tests.conftest`), serially and under -n 2 (the shape tests/test_served_tests_require.py and
tests/test_tempdir_hygiene.py use). The child's environment is built from a rule (PATH, a fresh HOME and TMPDIR, the
checkout on PYTHONPATH with bytecode writing off (PYTHONDONTWRITEBYTECODE), the locale, PYTHON_GIL and LD_LIBRARY_PATH
when this process has them, and the plant's own output directory), never this process's environment filtered, since
collecting the suite writes hundreds of variables at import.
The children run with CI's pytest-timeout flags when pytest-timeout is installed (CI installs it on every cell), so the
guard's exclusion of that plugin's own timer, alive through every test's teardown, is exercised by the green runs.

- A LEAKED non-daemon thread (it waits on an event the scratch conftest sets only at pytest_unconfigure, after the guard
  has run) fails the run, serially and under -n 2, with exactly one error, whose text names the thread, its target and
  a frame of its stack; under -n 2 that text is in the controller's output under a worker's `[gwN]` line, which is how
  the report is shown to have reached the controller. Daemon threads alive at the same moment are not named. The leaked
  thread is stopped only after the check, so these pins also witness that such a thread fails the guard although the
  process exits: it is still alive at pytest_sessionfinish, the scratch conftest's stop writes a release marker, and
  every process that ran tests then writes its atexit marker, which the interpreter runs only after joining its
  non-daemon threads (a worker killed by xdist's controller writes none). Serially the plant also leaves four
  ThreadPoolExecutor workers: an IDLE one in each of a pool left open and an event loop's default executor, the loop
  never closed, and a BUSY one, running a task, in each of a pool shut down with wait=False and a closed loop's default
  executor. All four are named with the label naming both causes, and each busy worker's report block, the one carrying
  its task's frame, carries the running-task cause. These runs shorten the guard's cap to LEAK_CAP_S through the scratch
  conftest, so a leak costs the pins seconds and not the full cap.
- IDLE EXECUTOR WORKERS ALONE (the pool left open and the loop never closed, no other guarded thread) fail the run,
  serially and under -n 2, and the process exits: every process that ran tests writes its atexit marker. The message's
  wording, that such a worker lets the process exit, is pinned by its text; the markers are the executed evidence.
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
- The guard's wait, in this process (JoinRace). Every thread is joined against one shared deadline: on a fake clock,
  three threads that never end cost the cap once, not three times. The thread list is read again after every pass, so
  a thread started as another exits (its start tied to the guard's first read) is waited for, and is returned when it
  runs past the cap. Run off the main thread, the guard waits for neither the main thread nor the thread running the
  check. A test's leaked patch of the process-wide time.monotonic, a clock that jumps, does not move the deadline.
- The guard leaves out any thread whose name starts with `pytest_timeout`, or whose target's module, or a Timer's
  function's module, starts with it. The exclusion exists for pytest-timeout's timer for the running test; a prefix and
  not an exact module means a plugin release that moves the function into a submodule still leaves it unwaited
  (TimeoutTimerMatch, in this process; CI installs the plugin unpinned). Each of the three matches is pinned alone.
  Other timers and threads are still waited for, among them near misses that start like the prefix (a thread named
  pytest-worker, Timers whose functions are in pytest_asyncio and pytest_testmon).

Each child-run pin was run with the guard removed from tests/conftest.py and fails there: the leak and idle-worker runs
pass (exit 0, no error) and the green runs' witness finds the within-cap threads alive at sessionfinish. Synthetic
fixtures only; no kernel, no network.
"""
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
HAS_XDIST = importlib.util.find_spec("xdist") is not None
# CI's Run pytest flags for pytest-timeout: its timer for the running test is alive through the guard's check
TIMEOUT_FLAGS = ["--timeout=600", "--timeout-method=thread"] if importlib.util.find_spec("pytest_timeout") else []

EXECUTOR_LABEL = ("(a ThreadPoolExecutor worker, of a pool or an asyncio loop's default executor: idle in one left without "
                  "shutdown, or running a task, which shutdown(wait=False) and loop.close() do not end; its stack shows which)")
RUNNING_TASK_CAUSE = "or running a task, which shutdown(wait=False) and loop.close() do not end"
# the message's clauses on exit, serially and under pytest-xdist, with the two kinds of named thread that let a process exit
EXIT_CLAUSES = ("A thread still running when the interpreter exits keeps the process from exiting: run serially, the run hangs "
                "until the thread ends or the job cap cancels it; under pytest-xdist the controller kills a worker still alive "
                "when the run ends, and the run would pass without this report. Two kinds of named thread let the process exit "
                "and fail this guard all the same: an idle concurrent.futures worker, which the interpreter wakes at exit, and "
                "a thread stopped only after this check (a config cleanup, pytest_sessionfinish or pytest_unconfigure).")
LEAK_CAP_S = 2.0      # the guard's cap in the leak runs: long enough to be a real wait, short enough to cost little
WITHIN_S = 1.0        # a within-cap thread's life after its test: a tenth of the guard's own cap
TESTS = 4             # tests in the plant, each starting its threads: every worker's last test starts some

SHARED = '''\
import threading
RELEASE = threading.Event()     # set by the scratch conftest at pytest_unconfigure, after the guard has run
'''

CONFTEST = '''\
import atexit, json, os, sys, threading, time
import pytest
import plant_shared

CAP = {cap!r}                   # None keeps the guard's own cap


def _mark(kind):
    # a marker for this process, KIND-PID.json, holding its monotonic time
    with open(os.path.join(os.environ["PLANT_OUT"], "%s-%d.json" % (kind, os.getpid())), "w") as f:
        json.dump(time.monotonic(), f)


def pytest_configure(config):
    if CAP is not None:
        sys.modules["tests.conftest"].THREAD_GUARD_CAP_S = CAP
    # the interpreter runs atexit handlers only after it has joined every non-daemon thread, so this marker says the
    # process got past that join: one still held by a thread, or killed by xdist's controller, writes none
    atexit.register(_mark, "atexit")


def pytest_sessionfinish(session):
    # the witness, after the guard (it ran in the last test's teardown): the plant threads alive now, the time, the cap
    alive = sorted(t.name for t in threading.enumerate() if t.name.startswith("plant-"))
    rec = dict(alive=alive, t=time.monotonic(), cap=sys.modules["tests.conftest"].THREAD_GUARD_CAP_S)
    with open(os.path.join(os.environ["PLANT_OUT"], "finish-%d.json" % os.getpid()), "w") as f:
        json.dump(rec, f)


def pytest_unconfigure(config):
    plant_shared.RELEASE.set()  # the leaked, busy and daemon threads end, so the process can exit
    _mark("release")            # the stop ran, after the guard had failed the run on the leaked thread


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


def _busy_pool_task():
    plant_shared.RELEASE.wait(120)          # a task still running at the check, in a pool shut down with wait=False


def _busy_loop_task():
    plant_shared.RELEASE.wait(120)          # a task still running at the check, in a closed event loop's default executor


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
    _start("pool", [])                      # records that this process ran a test
    pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-pool")
    pool.submit(int).result()
    POOL.append(pool)                       # kept referenced and never shut down: its worker idles


def test_event_loop_left_open():
    _start("loop", [])
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_until_complete(loop.run_in_executor(None, int))
    POOL.append(loop)                       # never closed: its default executor's worker idles
'''

BUSY_TEST = '''
def test_busy_pool_shut_down_without_wait():
    pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-busy-pool")
    pool.submit(_busy_pool_task)
    pool.shutdown(wait=False)               # does not end the running task: its worker runs on


def test_busy_worker_of_a_closed_event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    loop.run_in_executor(None, _busy_loop_task)
    loop.close()                            # shuts its default executor down with wait=False: the worker runs on
'''


class SessionEndThreadGuard(unittest.TestCase):
    def _run(self, plant, *, cap=None, workers=None):
        """pytest in a child over the plant `plant` (PLANT's helpers plus test functions), tests/conftest.py loaded as a
        plugin. Returns (exit status, the child's output, {pid: [[name, daemon]] started}, {pid: {within-cap thread name:
        its end time}}, {pid: {"alive": plant threads alive at pytest_sessionfinish, "t": that time, "cap": the guard's
        cap}}, {"release": {pid: time of the scratch conftest's stop at pytest_unconfigure}, "atexit": {pid: time of the
        process's atexit handler}}), the times from each process's monotonic clock."""
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
        started, ended, finish, marks = {}, {}, {}, {"release": {}, "atexit": {}}
        for name in sorted(os.listdir(out)):
            with open(os.path.join(out, name)) as f:
                data = json.load(f)
            kind, rest = name[:-len(".json")].split("-", 1)
            pid, _, tag = rest.partition("-")
            if kind == "started":
                started.setdefault(int(pid), []).extend(data)
            elif kind == "ended":
                ended.setdefault(int(pid), {})[tag] = data
            elif kind == "finish":
                finish[int(pid)] = data
            elif kind in marks:
                marks[kind][int(pid)] = data
            else:
                raise AssertionError("a record of no known kind in the plant's output: " + name)
        return r.returncode, r.stdout + r.stderr, started, ended, finish, marks

    # ── a leaked non-daemon thread fails the run ─────────────────────────────────────────────────────────────────────

    def _assert_leak_reported(self, rc, out, started, finish, marks):
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
        # the leaked thread is stopped only after the check, so the run also witnesses that such a thread fails the guard
        # although the process exits
        leaker = [pid for pid, names in started.items() if "plant-leaked" in {n for n, _daemon in names}]
        self.assertEqual(len(leaker), 1, "one process started the leaked thread:\n" + out)
        self.assertIn("plant-leaked", finish.get(leaker[0], {}).get("alive", []),
                      "the leaked thread was still running at pytest_sessionfinish, after the guard:\n" + out)
        missing = {pid: [kind for kind in ("release", "atexit") if pid not in marks[kind]] for pid in started}
        self.assertEqual({pid: kinds for pid, kinds in missing.items() if kinds}, {},
                         "every process that ran tests wrote a release marker (the scratch conftest's stop at "
                         "pytest_unconfigure ran) and an atexit marker (it exited: the interpreter runs atexit handlers "
                         "only after joining its non-daemon threads); these processes are missing one:\n" + out)
        for pid in started:
            self.assertGreaterEqual(marks["atexit"][pid], marks["release"][pid],
                                    "process %d's atexit marker follows its release marker" % pid)

    @staticmethod
    def _report_blocks(out):
        """The guard's report split into one block per thread, each from its `thread '<name>' (ident N) runs` line to the
        next such line (the last one runs on to the end of the output)."""
        return re.split(r"\n(?=thread '[^'\n]*' \(ident \d+\) runs )", out)[1:]

    def test_a_leaked_non_daemon_thread_fails_a_serial_run_and_the_report_names_it(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + LEAK_TEST + POOL_TEST + BUSY_TEST
        rc, out, started, _ended, finish, marks = self._run(plant, cap=LEAK_CAP_S)
        self._assert_leak_reported(rc, out, started, finish, marks)
        self.assertIn("thread 'plant-pool_0'", out, "an idle executor worker left open is named too:\n" + out)
        self.assertIn("thread 'plant-busy-pool_0'", out, "so is a busy worker of a pool shut down with wait=False:\n" + out)
        self.assertEqual(out.count("thread 'asyncio_0'"), 2, "so are an event loop's default-executor workers, idle in a "
                         "loop never closed and busy in a closed one (each executor numbers its workers from 0):\n" + out)
        # a busy worker's block is keyed on its task's frame: its name alone cannot tell the closed loop's worker from
        # the open loop's. Each in its own subTest, and both before any other label check, so each one's outcome is
        # reported whatever the other's.
        blocks = self._report_blocks(out)
        for task, which in (("_busy_pool_task", "a pool shut down with wait=False"),
                            ("_busy_loop_task", "a closed event loop's default executor")):
            with self.subTest(task=task):
                mine = [b for b in blocks if "in %s\n" % task in b]
                self.assertEqual(len(mine), 1, "one report block carries the %s frame:\n%s" % (task, out))
                self.assertIn(RUNNING_TASK_CAUSE, mine[0].split("\n", 1)[0], "the label of the busy worker of %s names "
                              "the running-task cause:\n%s" % (which, mine[0]))
        self.assertEqual(out.count(EXECUTOR_LABEL), 4, "the four executor workers carry the label that names both "
                         "causes:\n" + out)
        self.assertIn(EXIT_CLAUSES, out, "the message states the exit clauses with the idle-worker and stopped-later "
                      "exceptions (a wording check):\n" + out)
        self.assertIn("after up to %g s for each to end" % LEAK_CAP_S, out, "the cap the scratch conftest set was the one used")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_leaked_non_daemon_thread_fails_the_run_and_the_report_reaches_the_controller(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + LEAK_TEST
        rc, out, started, _ended, finish, marks = self._run(plant, cap=LEAK_CAP_S, workers=2)
        self._assert_leak_reported(rc, out, started, finish, marks)
        self.assertEqual(len(finish), 3, "a controller and two workers each reached pytest_sessionfinish:\n" + out)
        # the error came from a worker (its [gwN] line under the section header) and is printed by the controller, the only
        # process whose output this captures: a worker's own stdout goes to /dev/null
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    # ── idle executor workers alone fail the run, and the process exits ──────────────────────────────────────────────

    def _assert_idle_workers_fail_and_the_process_exits(self, rc, out, started, marks):
        self.assertEqual(rc, 1, "idle executor workers alone fail the run:\n" + out)
        self.assertIn("thread 'plant-pool_0'", out, "the idle worker of the pool left open is named:\n" + out)
        self.assertIn("thread 'asyncio_0'", out, "the idle worker of the event loop never closed is named:\n" + out)
        self.assertNotIn("plant-fx-", out, "threads the fixtures stop at teardown are not named")
        self.assertTrue(started, "the plant's tests recorded the processes that ran them:\n" + out)
        self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                         "every process that ran tests exited: its atexit handler, which the interpreter runs only after "
                         "joining its non-daemon threads, wrote its marker; these processes wrote none:\n" + out)
        self.assertIn(EXIT_CLAUSES, out, "a WORDING check: the message says an idle concurrent.futures worker lets the "
                      "process exit, serially and under pytest-xdist; the atexit markers above are the executed evidence "
                      "that it does:\n" + out)

    def test_idle_executor_workers_alone_fail_a_serial_run_and_the_process_exits(self):
        rc, out, started, _ended, _finish, marks = self._run(POOL_TEST, cap=LEAK_CAP_S)
        self._assert_idle_workers_fail_and_the_process_exits(rc, out, started, marks)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_idle_executor_workers_alone_fail_the_run_and_each_worker_exits(self):
        rc, out, started, _ended, _finish, marks = self._run(POOL_TEST, cap=LEAK_CAP_S, workers=2)
        self._assert_idle_workers_fail_and_the_process_exits(rc, out, started, marks)

    # ── threads that end within the cap, and daemon threads, leave the run green ─────────────────────────────────────

    def _assert_green_and_waited(self, rc, out, started, ended, finish, _marks):
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
    """The guard leaves out a thread whose name, or whose callable's module (a Thread's target, a Timer's function),
    starts with `pytest_timeout`. The exclusion exists for pytest-timeout's timer; a PREFIX means a release that moves
    the plugin's function into a submodule (CI installs pytest-timeout unpinned) does not make every cell wait the cap
    and fail on the timer. Each of the three matches is pinned on a thread that only it matches (the name, a Thread's
    target, a Timer's function), and the prefix's boundary on near misses that start like it and are still waited for.
    The threads here are built and never started: the match reads only their attributes."""

    def test_the_timer_is_not_guarded_when_its_function_moves_into_a_submodule(self):
        cf = sys.modules["tests.conftest"]
        moved = threading.Timer(600, _function_in("pytest_timeout._core"))
        moved.name = "pytest_timeout tests/test_x.py::test_y"          # the name the plugin gives its timer
        self.assertFalse(cf._guarded_thread(moved), "a timer whose function moved into a submodule of pytest_timeout "
                         "is excluded")
        renamed = threading.Timer(600, _function_in("pytest_timeout._core"))
        self.assertFalse(cf._guarded_thread(renamed), "matched by its function's module alone, whatever its name")
        today = threading.Timer(600, _function_in("pytest_timeout"))
        self.assertFalse(cf._guarded_thread(today), "the plugin's function as it is today")

    def test_a_timer_named_as_the_plugin_names_its_timer_is_not_guarded_whatever_its_function(self):
        cf = sys.modules["tests.conftest"]
        named = threading.Timer(600, _function_in("some_other_pkg.core"))
        named.name = "pytest_timeout tests/test_x.py::test_y"
        self.assertFalse(cf._guarded_thread(named), "a thread whose name starts with pytest_timeout is excluded by its "
                         "name alone: its function's module is some_other_pkg.core")

    def test_a_thread_whose_target_is_the_plugins_is_not_guarded_whatever_its_name(self):
        cf = sys.modules["tests.conftest"]
        t = threading.Thread(target=_function_in("pytest_timeout._core"), name="plant-timeout-target")
        self.assertFalse(cf._guarded_thread(t), "a Thread whose target's module starts with pytest_timeout is excluded by "
                         "its target alone: its name is plant-timeout-target and it has no Timer function")

    def test_other_non_daemon_timers_are_still_guarded(self):
        cf = sys.modules["tests.conftest"]
        self.assertTrue(cf._guarded_thread(threading.Timer(600, _function_in("kernel.kernel"))),
                        "a product timer is waited for")
        self.assertTrue(cf._guarded_thread(threading.Thread(target=_function_in("tests.test_x"), name="plant-timer")),
                        "a plain thread is waited for")
        # the prefix's boundary: each of these starts like the plugin's name and is not it, so each is waited for. A bare
        # `pytest` prefix would leave out all three, and so excuse a real leak; a prefix cut to `pytest_t` would leave out
        # the third.
        near_misses = (
            ("a thread named pytest-worker", threading.Thread(target=_function_in("tests.test_x"), name="pytest-worker")),
            ("a Timer whose function is another plugin's, pytest_asyncio",
             threading.Timer(600, _function_in("pytest_asyncio.plugin"))),
            ("a Timer whose function's module shares more of the prefix, pytest_testmon",
             threading.Timer(600, _function_in("pytest_testmon.testmon_core"))),
        )
        for what, t in near_misses:
            with self.subTest(near_miss=what):
                self.assertTrue(cf._guarded_thread(t), "%s is waited for: the prefix is pytest_timeout" % what)


@unittest.skipUnless("tests.conftest" in sys.modules, "the guard is tests/conftest.py's (pytest-only)")
class ThreadReportLabel(unittest.TestCase):
    """The guard's report labels a ProcessPoolExecutor's manager thread with both of its causes: a pool left without
    shutdown (the thread idles, and the interpreter wakes it at exit), or one shut down with wait=False while a task still
    runs. Stood in for by a never-started Thread subclass carrying the manager thread's module and name, so no process is
    spawned; the label is chosen from the thread's type alone, and the manager thread's stack reads the same idle or busy,
    so the label's text is what a pin can check."""

    def test_a_process_pool_manager_thread_is_labelled(self):
        cf = sys.modules["tests.conftest"]
        manager = type("_ExecutorManagerThread", (threading.Thread,), {"__module__": "concurrent.futures.process"})(
            name="plant-manager")
        report = cf._thread_report(manager, {})
        self.assertIn("runs concurrent.futures.process._ExecutorManagerThread.run (a ProcessPoolExecutor's manager "
                      "thread: a pool left without shutdown, or one shut down with wait=False while a task still runs; its "
                      "stack reads the same either way)", report)


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
        with mock.patch.object(cf, "_enumerate",
                               side_effect=lambda: reads.pop(0) if len(reads) > 1 else reads[0]) as enumerate_spy:
            self.assertEqual(cf.threads_left_at_session_end(5.0), [])
        self.assertGreaterEqual(enumerate_spy.call_count, 2, "the guard read the thread list again after its pass over "
                                "the thread it could not join")

    def test_every_thread_is_joined_against_one_shared_deadline(self):
        """The guard gives every thread until ONE deadline, cap_s from the call, joining each for the time left before it,
        so a process that leaks several threads pays the cap once. On a fake clock: the guard's own clock binding reads
        it, and three listed threads, never started, each advance it by the whole timeout they are joined for, as a join
        on a thread that never ends does. Joined for the full cap each, they would spend three times the cap."""
        cf = sys.modules["tests.conftest"]
        clock = [0.0]

        class NeverEnds(threading.Thread):
            def join(self, timeout=None):
                clock[0] += timeout             # the join times out: its whole timeout passes

        plants = [NeverEnds(name="plant-never-ends-%d" % i) for i in range(3)]
        cap = 10.0
        with mock.patch.object(cf, "_enumerate", return_value=[threading.main_thread()] + plants), \
                mock.patch.object(cf, "_monotonic", new=lambda: clock[0]):
            left = cf.threads_left_at_session_end(cap)
        self.assertEqual(left, plants, "the three threads still running at the deadline are returned")
        self.assertLessEqual(clock[0], cap, "the guard's joins spent %g s of the fake clock against a %g s cap: each join "
                             "must take only the time left before the one deadline" % (clock[0], cap))

    def _chain(self, cap_s, child_ends_on_second_read):
        """Runs the guard at cap `cap_s` over a parent thread that starts a non-daemon child as it exits. The child's start
        is tied to the guard's first read of the thread list: a spy on the guard's own binding reads the real list and
        only then lets the parent go, so the first list holds the parent and not the child. With
        `child_ends_on_second_read`, the spy's second read, again once it has read the list, lets the child end;
        otherwise the child runs on until the test's cleanup. Returns (the guard's result, the parent, the child)."""
        cf = sys.modules["tests.conftest"]
        real_enumerate = cf._enumerate
        first_read, child_may_end = threading.Event(), threading.Event()
        child = threading.Thread(target=child_may_end.wait, args=(60,), name="plant-chain-child")

        def parent():
            first_read.wait(60)
            child.start()                       # start() returns once the child runs, before the parent ends

        par = threading.Thread(target=parent, name="plant-chain-parent")
        reads = []

        def spy():
            listed = real_enumerate()
            reads.append(listed)
            if len(reads) == 1:
                first_read.set()
            elif child_ends_on_second_read:
                child_may_end.set()
            return listed

        self.addCleanup(lambda: child.join(60) if child.is_alive() else None)
        self.addCleanup(par.join, 60)
        self.addCleanup(child_may_end.set)
        self.addCleanup(first_read.set)
        par.start()
        with mock.patch.object(cf, "_enumerate", side_effect=spy):
            left = cf.threads_left_at_session_end(cap_s)
        return left, par, child

    def test_a_thread_started_as_another_exits_is_waited_for(self):
        """The guard reads the thread list again after every pass, so a thread started by one it was waiting for is
        waited for too. The child here ends only once the guard has read the list a second time."""
        left, par, child = self._chain(5.0, child_ends_on_second_read=True)
        self.assertFalse(child.is_alive(), "the guard returned while the child its parent started as it exited was still "
                         "running: the guard did not read the thread list again")
        self.assertNotIn(child, left)
        self.assertNotIn(par, left)

    def test_a_thread_started_as_another_exits_is_returned_while_it_runs_past_the_cap(self):
        """The same chain with a child that runs on: at a short cap the guard returns the child, which only a second read
        of the thread list can find, and not its parent, which has ended."""
        left, par, child = self._chain(2.0, child_ends_on_second_read=False)
        self.assertIn(child, left, "the child started as its parent exited is returned: the guard read the list again")
        self.assertTrue(child.is_alive())
        self.assertNotIn(par, left)

    def test_off_the_main_thread_neither_the_main_thread_nor_the_checking_thread_is_waited_for(self):
        """The guard leaves out the main thread and the thread running the check. Every other pin runs the guard on the
        main thread, where the two are one object; here a NON-daemon helper thread runs it (a daemon one is left out as a
        daemon before either clause is read) over a thread list of exactly those two. Waiting for either would take the
        whole cap: the main thread is blocked joining the helper, and a thread's join on itself raises the RuntimeError
        the guard passes over as a thread caught mid-start."""
        cf = sys.modules["tests.conftest"]
        cap = 2.0
        got = {}

        def check():
            try:
                with mock.patch.object(cf, "_enumerate",
                                       return_value=[threading.main_thread(), threading.current_thread()]):
                    t0 = time.perf_counter()
                    got["left"] = cf.threads_left_at_session_end(cap)
                    got["elapsed"] = time.perf_counter() - t0
            except BaseException as e:          # reported below, on the test's own thread
                got["error"] = repr(e)

        helper = threading.Thread(target=check, name="plant-checker", daemon=False)
        helper.start()
        helper.join(60)
        self.assertFalse(helper.is_alive(), "the helper running the guard ended")
        self.assertNotIn("error", got, got.get("error"))
        self.assertEqual([t.name for t in got["left"]], [], "neither the main thread nor the thread running the check "
                         "is returned")
        self.assertLess(got["elapsed"], cap / 2, "the guard took %.2f s of a %g s cap: it waited for the main thread or "
                        "for itself" % (got["elapsed"], cap))

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

    def test_a_leaked_patch_of_time_monotonic_does_not_move_the_guards_deadline(self):
        """The guard binds time.monotonic at import, so a test that patched the process-wide function with a clock that
        jumps, and left the patch in place, cannot bring the guard's deadline forward: a thread that ends within the cap
        is still waited for, and not returned."""
        cf = sys.modules["tests.conftest"]
        t = threading.Thread(target=time.sleep, args=(0.3,), name="plant-ends-soon")
        t.start()
        self.addCleanup(t.join)
        with mock.patch.object(time, "monotonic", side_effect=itertools.count(0, 1e6)):
            left = cf.threads_left_at_session_end(5.0)
        self.assertNotIn(t, left, "the guard returned a thread that ends within its cap: the patched clock moved its "
                         "deadline")
        self.assertFalse(t.is_alive(), "the guard waited for the thread to end")


if __name__ == "__main__":
    unittest.main()
