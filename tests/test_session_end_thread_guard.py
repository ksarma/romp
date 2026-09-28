#!/usr/bin/env python3
"""tests/conftest.py's session-end thread guard (2026-09-26): at the end of each process's session, the one serial
process or each pytest-xdist worker, a guarded thread still running after the guard's cap fails the process's last test
at teardown, named with its target and stack. Guarded: every non-daemon thread, and every thread in concurrent.futures'
exit-join tables (tests/conftest.py's EXIT_JOIN_TABLES) whatever its daemon flag.

Why it exists. A non-daemon thread still running when the interpreter exits keeps its process from exiting. So does a
concurrent.futures thread still running a task, whatever its daemon flag: the interpreter's exit hooks for
concurrent.futures join every thread in their tables, and a pool started from a daemon thread has daemon workers, since
a thread takes its daemon flag from the thread that creates it. Run serially, the run hangs until the thread ends or
CI's job cap cancels the cell, which is a red cell. Under pytest-xdist the controller kills a worker still alive when
the run ends and the run passes, so the fork's Linux cells lost that signal when they moved to two workers (2026-09-25).
Two kinds of thread the guard names do not keep the process from exiting, and the guard fails on them too: an idle
concurrent.futures worker and a thread stopped only after the check (tests/conftest.py's comment on the guard says why).
A worker's stdout goes to /dev/null and its exit status is not read, so the guard fails the run through a test report,
the teardown phase's, which a worker sends the controller and the controller prints as `ERROR at teardown of <the
worker's last test>` and counts in the run's exit status. tests/conftest.py keeps that report an error naming the
threads when pytest's skipping plugin would make it an xfail (an xfail-marked last test) or its unittest plugin would
put a TestCase's second stored error in its place. The guard writes the same text to stderr too, a second channel that
no report hook can change; a worker's stderr is the controller's.

Pinned by running pytest in a child over synthetic files in a scratch directory outside tests/, with tests/conftest.py
loaded as a plugin (`-p tests.conftest`), serially and under -n 2 (the shape tests/test_served_tests_require.py and
tests/test_tempdir_hygiene.py use). The child's environment is built from a rule (PATH, a fresh HOME and TMPDIR, the
checkout on PYTHONPATH with bytecode writing off (PYTHONDONTWRITEBYTECODE), the locale, PYTHON_GIL and LD_LIBRARY_PATH
when this process has them, the plant's own output directory, and any variable a pin adds), never this process's
environment filtered, since collecting the suite writes variables of its own at import (among them the floors in
tests/__init__.py and tests/conftest.py).
The children run with CI's pytest-timeout flags when pytest-timeout is installed (CI installs it on every cell), so the
guard's exclusion of that plugin's own timer, alive through every test's teardown, is exercised by the green runs.

- A LEAKED non-daemon thread (it waits on an event the scratch conftest sets only at pytest_unconfigure, after the guard
  has run) fails the run, serially and under -n 2, with exactly one error, whose text names the thread, its target and a
  frame of its stack; under -n 2 that text is in the controller's output under a worker's `[gwN]` line, which is how the
  report is shown to have reached the controller. Stderr, the second channel, names the thread once too, with the same
  frame. Plain daemon threads (no concurrent.futures thread among them) alive at the same moment are not named. The
  leaked thread is stopped only after the check, so these pins also witness that such a thread fails the guard
  although the process exits: it is still alive at pytest_sessionfinish, the scratch conftest's stop writes a release
  marker, and every process that ran tests then writes its atexit marker, which the interpreter runs only after joining
  its non-daemon threads and the threads concurrent.futures' exit hooks join (a worker killed by xdist's controller
  writes none). Serially the plant also leaves four ThreadPoolExecutor workers: an
  IDLE one in each of a pool left open and an event loop's default executor, the loop never closed, and a BUSY one,
  running a task, in each of a pool shut down with wait=False and a closed loop's default executor. All four are named
  with the label naming both causes, and each busy worker's report block, the one carrying its task's frame, carries the
  running-task cause. These runs shorten the guard's cap to LEAK_CAP_S through the scratch conftest, so a leak costs the
  pins seconds and not the full cap.
- A TESTCASE'S SECOND ERROR IN THE TEARDOWN REPORT. The process's last test is a unittest TestCase whose body fails and
  whose cleanup fails, with a leaked non-daemon thread. pytest's unittest plugin reports the cleanup's error at teardown
  in place of the guard's (the premise, checked: the teardown report carries it), and tests/conftest.py adds the
  guard's text after that error, so the report names the thread once, with its target and stack, after the cleanup's
  error, and stderr names it once too, serially and under -n 2, where the worker's text reaches the controller's stderr
  naming the worker.
- AN XFAIL-MARKED LAST TEST. pytest's skipping plugin makes the teardown error of an xfail-marked test an xfail, which
  would leave the run green. A leaked non-daemon thread after an xfail-marked last test fails the run with one error,
  at that test's teardown, naming the thread in the report and on stderr, whether the marked body fails (xfailed) or
  passes (xpassed), serially, and with a failing body under -n 2; the body's own outcome is still the one the mark
  gives it.
- A VALUE THE REPORT MASKS IS MASKED ON STDERR TOO. The leaked thread's name carries a synthetic value that only the
  child's environment holds, under a credential-shaped variable name, so the report's redaction masks it. Neither
  channel carries the raw value, and stderr names the thread by the masked name the report prints, serially and under
  -n 2: CI's logs are public, so the stderr copy goes through the report's redaction. So does the guard's text that
  tests/conftest.py adds after a TestCase's second error (the two-error shape above, serially), and so does the stderr
  header, which names the last test by its node id (a test whose parametrize id is that value, serially). The pattern
  net reaches stderr the same way: a pytest.fail raised with a traceback inside the guard's call (a Thread subclass's
  join) carries a credential-shaped token, in no environment, on a `- <token>` line; the report prints the message
  under pytest's `E` marker, where the net's diff-line rule masks it, and stderr, which prints it bare, masks it too
  (serially).
- IDLE EXECUTOR WORKERS ALONE (the pool left open and the loop never closed, no other guarded thread) fail the run,
  serially and under -n 2, and the process exits: every process that ran tests writes its atexit marker. The message's
  wording, that such a worker lets the process exit, is pinned by its text; the markers are the executed evidence.
- A BUSY WORKER OF A POOL A DAEMON THREAD STARTED (the daemon thread starts a ThreadPoolExecutor, submits a task that
  runs until the scratch conftest's stop and EXIT_HOLD_S past it, and shuts the pool down with wait=False) fails the
  run, serially and under -n 2, with exactly one error naming the worker, whose own daemon flag the plant records as
  True, with the label's running-task cause and its task's frame; the daemon thread that started the pool, still
  running, is not named. The run also witnesses the premise: the worker is alive at pytest_sessionfinish, and the
  process's atexit marker follows the task's end, written as its last act EXIT_HOLD_S after the stop, so the interpreter
  joined that daemon thread before it ran its atexit handlers. Every process that ran tests exits.
- An IDLE WORKER OF A POOL A DAEMON THREAD STARTED (the pool left open) behaves as the idle-worker pins above say: it
  fails the run, serially and under -n 2, named with the label, and every process that ran tests exits (its atexit
  marker).
- A MISSING EXIT-JOIN TABLE fails the run loudly: with the scratch conftest deleting concurrent.futures.thread's
  _threads_queues for the session (put back at pytest_sessionfinish, after the guard), a serial run of one plain test
  fails with exactly one error naming concurrent.futures.thread._threads_queues, and stderr names it too; the same with
  concurrent.futures.process's _threads_wakeups (the module loaded by the scratch conftest). In this process
  (ExitJoinTables): each EXIT_JOIN_TABLES attribute exists on this Python and is a global its module's exit hook reads;
  the two hooks are the only ones the standard library registers with threading._register_atexit, derived from its
  source (a premise pin, which reads no guard); and a live daemon thread in either table (the busy worker of a pool a
  daemon thread started, and a stand-in for a ProcessPoolExecutor's manager thread) is returned by the guard while a
  plain daemon thread beside it is not. The tables are read again after every pass: a busy worker started, by a worker
  of a pool a daemon thread started, after the guard's first read is returned. A read that raises RuntimeError, as
  iterating a WeakKeyDictionary does on 3.10 to 3.13 when another thread inserts into it, is read again (a stand-in
  table raises on its first read, and the pin drives the guard's clock, so no real time passes), up to the guard's one
  deadline: a table that changes during every read ends the guard at its deadline, failing it by the table's name and
  naming the non-daemon thread still alive beside it, but not a plain daemon thread (a stand-in that adds to itself
  during every read, with the process-wide time.monotonic frozen, the guard run under a backstop whose firing is the
  defect of a retry with no bound, or one bounded on that frozen clock). The same failure in a child run (a stand-in
  table whose every read raises, in place for the session, beside a leaked non-daemon thread) fails the run with one
  error whose report prints the table's failure once, with no exception chain: raised inside the handler of the table's
  own failure, it would print that one first, under "During handling of the above exception". Stderr prints it once too.
- Threads that END WITHIN THE CAP (each test starts one that sleeps WITHIN_S and exits) and plain DAEMON threads that
  run past the session (one per test, released at unconfigure) leave the run green, serially and under -n 2, at the
  guard's own cap. The guard's wait is WITNESSED, not assumed: the scratch conftest records at pytest_sessionfinish,
  which runs after the guard, which plant threads are alive. Every within-cap thread must be gone (the guard joined it;
  without the guard the last test's thread, started milliseconds earlier, is still sleeping) and every plain daemon
  thread still alive (it ran through the guard and was not waited for or named). And the wait must be a join, which
  returns when its thread ends, not a sleep through the cap: each within-cap thread writes its end time as its last act,
  and the session must finish within half the cap of the process's last one (it finishes milliseconds after; a guard
  that slept its cap would finish nine seconds after).
- The guard runs AFTER THE RUNNER HAS TORN DOWN EVERY FIXTURE. The scratch conftest carries two autouse fixtures, one
  session-scoped and one function-scoped, each starting a non-daemon thread that waits on its own event and is stopped
  and joined only at the fixture's teardown. Every run above stays free of their names and the green runs pass, so a
  thread a fixture stops at teardown is never waited for or named. A guard moved before the runner's teardown (its
  check before the wrapper's yield, or a plain implementation marked tryfirst or not ordered, since pytest's runner
  plugin registers before any conftest and pluggy calls later registrations first) waits its cap for them and fails the
  green runs naming them. A last test whose own fixture fails at teardown is checked too, after the runner's error: the
  report names the leaked thread after the fixture's error, unmarked serially, and under an xfail mark serially and
  under -n 2, where pytest's skipping plugin would otherwise make that error an xfail and leave the run green.

- A thread listed while its start() is still running, which Thread.join refuses with a RuntimeError, is read again on
  the guard's next pass rather than raised (JoinRace, in this process under the conftest: a thread never started, which
  join refuses the same way, stands in for it). The pin patches the guard's own binding of threading.enumerate, so no
  other thread's call can take its fake reads; and a test's leaked patch of the process-wide threading.enumerate does
  not hide a live thread from the guard.
- The guard's wait, in this process (JoinRace). Every thread is joined against one shared deadline: on a fake clock,
  three threads that never end cost at most the cap, not three times it. The thread list is read again after every
  pass, so a thread started as another exits (its start tied to the guard's first read) is waited for, and is returned
  when it runs past the cap. Run off the main thread, the guard waits for neither the main thread nor the thread running
  the check. A test's leaked patch of the process-wide time.monotonic, a clock that jumps, does not move the deadline.
- The guard leaves out any thread whose name starts with `pytest_timeout`, or whose target's module, or a Timer's
  function's module, starts with it. The exclusion exists for pytest-timeout's timer for the running test; a prefix and
  not an exact module means a plugin release that moves the function into a submodule still leaves it unwaited
  (TimeoutTimerMatch, in this process; CI installs the plugin unpinned). Each of the three matches is pinned alone.
  Other timers and threads are still waited for, among them near misses that start like the prefix (a thread named
  pytest-worker, Timers whose functions are in pytest_asyncio and pytest_testmon).

Each child-run pin was run with the guard removed from tests/conftest.py and fails there: the leak, idle-worker,
daemon-started-pool, missing-table, xfail (the fixture-teardown one under xfail among them), redaction, stderr-header
and table-changing runs pass (exit 0, no error), the green runs' witness finds the within-cap threads alive at
sessionfinish, and the two-error runs (the redaction one among them) and the unmarked fixture-teardown run, red on the
TestCase's or the fixture's own errors, find no thread named in the report. The fixture-teardown runs also fail with
the guard as it was before it ran after a failing teardown of the runner, on the same outcomes. The two-error runs also fail with the guard
as it was before it wrote to stderr, on the same missing name.
The pins for the exit-join tables, as this file has them, were run serially on 3.12 against the guard as it was before
it read the tables, when it waited for non-daemon threads only, and every one that reads the guard fails there. Of the
child runs, the four daemon-started-pool runs (busy and idle, serially and under -n 2) and each missing-table run exit 0
with no error, and the table-changing run, whose leaked thread fails that guard as a leak, finds no table's failure in
its report. In this process (ExitJoinTables): test_the_guard_reads_the_tables_the_exit_hooks_join fails on the missing
EXIT_JOIN_TABLES (AttributeError); the pins of the daemon-started pool's worker and of the process pool's table fail
with the guard returning an empty list; the re-read pin (test_the_tables_are_read_again_after_every_pass) fails with a
KeyError on 'w2' at its unpack line, since that guard skips the daemon W1 and returns at once, before W1's task records
W2; the retry pin (test_a_table_read_that_meets_a_concurrent_insert_is_read_again) fails at its assertion with an empty
list; and the deadline pin fails because the guard returns its non-daemon plant at the cap instead of failing. The one
that passes there is test_they_are_the_only_exit_hooks_the_standard_library_registers, a premise pin: it reads no guard,
only the standard library's source against the class's own TABLES, so no change to the guard can turn it red.
Synthetic fixtures only; no kernel, no network.
"""
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
import unittest
from unittest import mock

from tests.thread_ends import join_started

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
HAS_XDIST = importlib.util.find_spec("xdist") is not None
# CI's Run pytest flags for pytest-timeout: its timer for the running test is alive through the guard's check
TIMEOUT_FLAGS = ["--timeout=600", "--timeout-method=thread"] if importlib.util.find_spec("pytest_timeout") else []

EXECUTOR_LABEL = ("(a ThreadPoolExecutor worker, of a pool or an asyncio loop's default executor: idle in one left without "
                  "shutdown, or running a task, which shutdown(wait=False) and loop.close() do not end; its stack shows which)")
RUNNING_TASK_CAUSE = "or running a task, which shutdown(wait=False) and loop.close() do not end"
# the message's clauses on exit, serially and under pytest-xdist, with the two kinds of named thread that let a process exit
EXIT_CLAUSES = ("A named thread still running when the interpreter exits keeps the process from exiting: run serially, the "
                "run hangs until the thread ends or the job cap cancels it; under pytest-xdist the controller kills a worker "
                "still alive when the run ends, and the run would pass without this report. Two kinds of named thread let the "
                "process exit and fail this guard all the same: an idle concurrent.futures worker, which the interpreter wakes "
                "at exit, and a thread stopped only after this check (a config cleanup, pytest_sessionfinish or "
                "pytest_unconfigure).")
LEAK_CAP_S = 2.0      # the guard's cap in the leak runs: long enough to be a real wait, short enough to cost little
# _run joins the child's stdout, where the test reports print, and its stderr, the guard's second channel, at this line
STDERR_LINE = "\n---- the child's stderr ----\n"
EXIT_HOLD_S = 1.0     # how long the busy worker of a daemon-started pool runs on after the stop, before its end record
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
DROP = {drop!r}                 # (module, attribute) deleted for the session, or None
_DROPPED = []


def _mark(kind):
    # a marker for this process, KIND-PID.json, holding its monotonic time
    with open(os.path.join(os.environ["PLANT_OUT"], "%s-%d.json" % (kind, os.getpid())), "w") as f:
        json.dump(time.monotonic(), f)


def pytest_configure(config):
    if CAP is not None:
        sys.modules["tests.conftest"].THREAD_GUARD_CAP_S = CAP
    if DROP is not None:            # a Python without that exit-join table, for the session
        import importlib
        mod = importlib.import_module(DROP[0])
        _DROPPED.append((mod, DROP[1], getattr(mod, DROP[1])))
        delattr(mod, DROP[1])
    # the interpreter runs atexit handlers only after it has joined every non-daemon thread and every thread
    # concurrent.futures' exit hooks join, so this marker says the process got past those joins: one still held by a
    # thread, or killed by xdist's controller, writes none
    atexit.register(_mark, "atexit")


def pytest_sessionfinish(session):
    # the witness, after the guard (it ran in the last test's teardown): the plant threads alive now, the time, the cap
    alive = sorted(t.name for t in threading.enumerate() if t.name.startswith("plant-"))
    rec = dict(alive=alive, t=time.monotonic(), cap=sys.modules["tests.conftest"].THREAD_GUARD_CAP_S)
    with open(os.path.join(os.environ["PLANT_OUT"], "finish-%d.json" % os.getpid()), "w") as f:
        json.dump(rec, f)
    for mod, attr, value in _DROPPED:   # put back after the guard, so the exit hook finds its table
        setattr(mod, attr, value)


def pytest_unconfigure(config):
    plant_shared.RELEASE.set()  # the leaked, busy and daemon threads end, so the process can exit
    _mark("release")            # the stop ran, after the guard had run (in the leak runs it had failed the run on the
                                # leaked thread)


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
EXIT_HOLD_S = {hold!r}
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


def _busy_daemon_pool_task():
    plant_shared.RELEASE.wait(120)          # a task still running at the check, in a pool a daemon thread started
    time.sleep(EXIT_HOLD_S)                 # and on past the stop, so the process's exit must wait for it
    name = threading.current_thread().name
    with open(os.path.join(os.environ["PLANT_OUT"], "ended-%d-%s.json" % (os.getpid(), name)), "w") as f:
        json.dump(time.monotonic(), f)      # its last act: the worker's task returns right after this write


def _daemon_starts_pool(busy, ready):
    # runs on a daemon thread, so the pool's worker is a daemon thread too: it takes its flag from the thread creating it
    prefix = "plant-dpool-busy" if busy else "plant-dpool-idle"
    pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix=prefix)
    if busy:
        pool.submit(_busy_daemon_pool_task)
        pool.shutdown(wait=False)           # does not end the running task: its worker runs on
    else:
        pool.submit(int).result()
        POOL.append(pool)                   # kept referenced and never shut down: its worker idles
    _record(prefix, [t for t in threading.enumerate() if t.name.startswith(prefix + "_")])
    ready.set()
    plant_shared.RELEASE.wait(120)          # a plain daemon thread running past the session: never named


def _record(tag, threads):
    with open(os.path.join(os.environ["PLANT_OUT"], "started-%d-%s.json" % (os.getpid(), tag)), "w") as f:
        json.dump([[t.name, t.daemon] for t in threads], f)


def _start(tag, threads):
    for t in threads:
        t.start()
    _record(tag, threads)
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

DAEMON_POOL_TEST = '''
def test_daemon_thread_starts_a_{kind}_pool():
    ready = threading.Event()
    _start("dspawner-{kind}", [threading.Thread(target=_daemon_starts_pool, args=({busy}, ready),
                                                name="plant-dspawner-{kind}", daemon=True)])
    assert ready.wait(60)
'''
DAEMON_BUSY_TEST = DAEMON_POOL_TEST.format(kind="busy", busy=True)
DAEMON_IDLE_TEST = DAEMON_POOL_TEST.format(kind="idle", busy=False)

PLAIN_TEST = '''
def test_plain():
    _start("plain", [])                     # records that this process ran a test
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

# a unittest TestCase whose body fails and whose cleanup fails: pytest's unittest plugin reports the body's failure at
# the call and puts the cleanup's error into the teardown report, in place of the guard's, and tests/conftest.py adds
# the guard's text after it
TWO_ERRORS_TEST = '''
import unittest


class TwoErrors(unittest.TestCase):
    def test_body_and_cleanup_fail(self):
        _start("two-errors", [threading.Thread(target=_leaked, name="plant-leaked")])
        self.addCleanup(self._cleanup_fails)
        raise AssertionError("plant: the body failed")

    def _cleanup_fails(self):
        raise RuntimeError("plant: the cleanup failed")
'''

# a leaked thread named with the value of ENV_NAMED_VAR, a variable only the child's environment holds (_run's env_extra):
# its name is credential-shaped, so the report's redaction masks that value wherever the report prints it
ENV_NAMED_VAR = "PLANT_API_KEY"
ENV_NAMED_TEST = '''
def test_leak_named_by_an_env_value():
    _start("env-named", [threading.Thread(target=_leaked, name="plant-leaked-" + os.environ[%r])])
''' % ENV_NAMED_VAR
# a leaked thread in a test whose node id carries that value: the guard's stderr header names the test by its node id
ENV_NAMED_ID_TEST = '''
import pytest


@pytest.mark.parametrize("n", [0], ids=[os.environ[%r]])
def test_leak_with_an_env_value_in_its_id(n):
    _start("env-id", [threading.Thread(target=_leaked, name="plant-leaked")])
''' % ENV_NAMED_VAR
# the TestCase whose body and cleanup both fail, its leaked thread named the same way: the guard's text is added to the
# report after the cleanup's error, and is redacted there too
TWO_ERRORS_ENV_NAMED_TEST = TWO_ERRORS_TEST.replace('name="plant-leaked"',
                                                    'name="plant-leaked-" + os.environ[%r]' % ENV_NAMED_VAR)

# a leaked thread whose join, which the guard calls, fails through pytest.fail with a traceback and a line shaped as a
# failed comparison's diff line, a sign and then a credential-shaped token that is in no environment: the report prints
# the message under pytest's `E` marker, where the pattern net's diff-line rule masks the token. The token is built at
# run time, in two halves, so no credential-shaped literal sits in this file or in the plant's source
FAILS_IN_JOIN_TEST = '''
import pytest


class _FailsInJoin(threading.Thread):
    def join(self, timeout=None):
        pytest.fail("plant: a join that fails\\n- " + "abcdefghijklmnopqrstuvwx" + "0123456789", pytrace=True)


def test_leak_whose_join_fails():
    _start("fails-in-join", [_FailsInJoin(target=_leaked, name="plant-leaked")])
'''

# appended to the scratch conftest: concurrent.futures.thread's exit-join table replaced for the session by a stand-in
# whose every read raises the RuntimeError a concurrent insert raises, as a table another thread adds to without pause
# would, and put back at pytest_sessionfinish, after the guard; any insert is passed on to the real table
TABLE_KEEPS_CHANGING = '''

import concurrent.futures.thread as _cft
_REAL_TABLE = _cft._threads_queues


class _ChangesDuringEveryRead:
    def __iter__(self):
        walked = {object(): None}
        it = iter(walked)
        next(it)
        walked[object()] = None     # an insert mid-walk: the walk's next step raises RuntimeError
        return it

    def __setitem__(self, key, value):
        _REAL_TABLE[key] = value


_plant_configure, _plant_sessionfinish = pytest_configure, pytest_sessionfinish


def pytest_configure(config):
    _plant_configure(config)
    _cft._threads_queues = _ChangesDuringEveryRead()


def pytest_sessionfinish(session):
    _cft._threads_queues = _REAL_TABLE
    _plant_sessionfinish(session)
'''

# an xfail-marked last test that leaks a non-daemon thread, its body failing as the mark expects or passing: pytest's
# skipping plugin makes the teardown error of an xfail-marked test an xfail
XFAIL_BODY_FAILS_TEST = '''
import pytest


@pytest.mark.xfail(reason="plant: the body is expected to fail")
def test_leak_under_xfail_body_fails():
    _start("xfail-fails", [threading.Thread(target=_leaked, name="plant-leaked")])
    raise AssertionError("plant: the body failed, as its xfail mark expects")
'''

XFAIL_BODY_PASSES_TEST = '''
import pytest


@pytest.mark.xfail(reason="plant: the body is expected to fail")
def test_leak_under_xfail_body_passes():
    _start("xfail-passes", [threading.Thread(target=_leaked, name="plant-leaked")])
'''

# a last test whose own fixture raises at teardown, with a leaked non-daemon thread: the runner's teardown raises before
# the guard runs, and under an xfail mark pytest's skipping plugin makes that error an xfail
FIXTURE_TEARDOWN_FAILS = '''
import pytest


@pytest.fixture
def fails_at_teardown():
    yield
    raise RuntimeError("plant: the fixture's teardown failed")

'''
FIXTURE_TEARDOWN_FAILS_TEST = FIXTURE_TEARDOWN_FAILS + '''
def test_leak_fixture_teardown_fails(fails_at_teardown):
    _start("fixture-teardown-fails", [threading.Thread(target=_leaked, name="plant-leaked")])
'''
FIXTURE_TEARDOWN_FAILS_XFAIL_TEST = FIXTURE_TEARDOWN_FAILS + '''
@pytest.mark.xfail(reason="plant: the body is expected to fail")
def test_leak_fixture_teardown_fails_under_xfail(fails_at_teardown):
    _start("fixture-teardown-fails-xfail", [threading.Thread(target=_leaked, name="plant-leaked")])
    raise AssertionError("plant: the body failed, as its xfail mark expects")
'''


class SessionEndThreadGuard(unittest.TestCase):
    def _run(self, plant, *, cap=None, workers=None, drop=None, env_extra=None, conftest_extra=""):
        """pytest in a child over the plant `plant` (PLANT's helpers plus test functions), tests/conftest.py loaded as a
        plugin. Returns (exit status, the child's output (its stdout, STDERR_LINE, then its stderr; _channels splits
        them), {pid: [[name, daemon]] started}, {pid: {within-cap thread name:
        its end time}}, {pid: {"alive": plant threads alive at pytest_sessionfinish, "t": that time, "cap": the guard's
        cap}}, {"release": {pid: time of the scratch conftest's stop at pytest_unconfigure}, "atexit": {pid: time of the
        process's atexit handler}}), the times from each process's monotonic clock. `drop`, a (module, attribute) pair,
        is deleted by the scratch conftest for the session. `env_extra` adds variables to the child's environment, and
        `conftest_extra` is code appended to the scratch conftest."""
        d = os.path.realpath(tempfile.mkdtemp(prefix="tg-"))       # resolved: macOS temp dirs sit under a symlink
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        case, out, home, tmp = (os.path.join(d, n) for n in ("case", "out", "home", "tmp"))
        for p in (case, out, home, tmp):
            os.makedirs(p)
        for name, body in (("plant_shared.py", SHARED),
                           ("conftest.py", CONFTEST.format(cap=cap, drop=drop) + conftest_extra),
                           ("test_plant.py", PLANT.format(within=WITHIN_S, hold=EXIT_HOLD_S) + plant)):
            with open(os.path.join(case, name), "w") as f:
                f.write(body)
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": home, "TMPDIR": tmp, "PYTHONPATH": REPO,
               "PYTHONDONTWRITEBYTECODE": "1", "PLANT_OUT": out}
        # the locale, the free-threaded build's GIL setting, and the library path setup-python exports on Linux for the
        # interpreter's shared library
        env.update((k, os.environ[k]) for k in ("LANG", "LC_ALL", "LC_CTYPE", "PYTHON_GIL", "LD_LIBRARY_PATH")
                   if k in os.environ)
        env.update(env_extra or {})
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
        return r.returncode, r.stdout + STDERR_LINE + r.stderr, started, ended, finish, marks

    @staticmethod
    def _channels(out):
        """The child's output (_run) split into its stdout, where the test reports print, and its stderr, where the
        guard writes its failure a second time."""
        report, sep, err = out.partition(STDERR_LINE)
        assert sep, "the output carries _run's stderr line"
        return report, err

    # -- a leaked non-daemon thread fails the run ---------------------------------------------------------------------

    def _assert_leak_reported(self, rc, out, started, finish, marks):
        report, err = self._channels(out)
        self.assertIn("plant-leaked", {n for names in started.values() for n, _daemon in names}, "the plant ran:\n" + out)
        self.assertEqual(rc, 1, "a leaked non-daemon thread fails the run:\n" + out)
        self.assertEqual(len(re.findall(r"ERROR at teardown of test_", out)), 1, "one error, at a teardown:\n" + out)
        self.assertRegex(out, r"\n1 error\b|, 1 error\b", out)
        self.assertEqual(report.count("thread 'plant-leaked'"), 1, "the report names the leaked thread once:\n" + out)
        self.assertIn("thread 'plant-leaked' (ident ", report)
        self.assertIn("runs test_plant._leaked\n", report, "the report names the thread's target")
        self.assertIn("in _leaked\n    plant_shared.RELEASE.wait(120)", report,
                      "the report carries the thread's stack, down to the plant's frame")
        self.assertIn("session-end thread guard", report, "the report says what made it")
        # the second channel: the same text on stderr, which reaches the output serially and from a worker
        self.assertEqual(err.count("thread 'plant-leaked'"), 1, "stderr names the leaked thread once too:\n" + out)
        self.assertIn("in _leaked\n    plant_shared.RELEASE.wait(120)", err, "stderr carries the thread's stack too")
        self.assertNotIn("plant-daemon", out, "plain daemon threads alive at the same moment are not named")
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
                         "only after joining its non-daemon threads and the threads concurrent.futures' exit hooks join); "
                         "these processes are missing one:\n" + out)
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
        report, _err = self._channels(out)
        self.assertIn("thread 'plant-pool_0'", report, "an idle executor worker left open is named too:\n" + out)
        self.assertIn("thread 'plant-busy-pool_0'", report, "so is a busy worker of a pool shut down with wait=False:\n"
                      + out)
        self.assertEqual(report.count("thread 'asyncio_0'"), 2, "so are an event loop's default-executor workers, idle "
                         "in a loop never closed and busy in a closed one (each executor numbers its workers from 0):\n"
                         + out)
        # a busy worker's block is keyed on its task's frame: its name alone cannot tell the closed loop's worker from
        # the open loop's. Each in its own subTest, and both before any other label check, so each one's outcome is
        # reported whatever the other's.
        blocks = self._report_blocks(report)
        for task, which in (("_busy_pool_task", "a pool shut down with wait=False"),
                            ("_busy_loop_task", "a closed event loop's default executor")):
            with self.subTest(task=task):
                mine = [b for b in blocks if "in %s\n" % task in b]
                self.assertEqual(len(mine), 1, "one report block carries the %s frame:\n%s" % (task, out))
                self.assertIn(RUNNING_TASK_CAUSE, mine[0].split("\n", 1)[0], "the label of the busy worker of %s names "
                              "the running-task cause:\n%s" % (which, mine[0]))
        self.assertEqual(report.count(EXECUTOR_LABEL), 4, "the four executor workers carry the label that names both "
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
        # the error came from a worker (its [gwN] line under the section header) and is printed by the controller: a
        # worker's own stdout goes to /dev/null (its stderr is the controller's, the second channel checked above)
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    # -- a TestCase's own second error takes the teardown report, and the guard's text follows it ----------------------

    def _assert_two_errors_name_the_thread(self, rc, out, started, marks):
        """The process's last test is a unittest TestCase whose body fails and whose cleanup fails, with a thread left
        running. pytest's unittest plugin puts the cleanup's error into the teardown report in place of the guard's (the
        premise, checked first: the teardown report carries the cleanup's error), tests/conftest.py adds the guard's text
        after that error, so the report names the thread once, with its target and stack, and so does the guard's
        second channel, stderr. Returns (the report, stderr)."""
        report, err = self._channels(out)
        self.assertIn("plant-leaked", {n for names in started.values() for n, _daemon in names},
                      "the plant ran:\n" + out)
        self.assertEqual(rc, 1, "the run fails:\n" + out)
        self.assertIn("AssertionError: plant: the body failed", report, "the body's failure is reported:\n" + out)
        self.assertEqual(len(re.findall(r"ERROR at teardown of TwoErrors\.test_body_and_cleanup_fail", report)), 1,
                         "one error, at the TestCase's teardown:\n" + out)
        self.assertIn("RuntimeError: plant: the cleanup failed", report, "the premise: the teardown report carries the "
                      "cleanup's error:\n" + out)
        self.assertEqual(report.count("thread 'plant-leaked' (ident "), 1, "the teardown report names the thread once, "
                         "after the cleanup's error that took the guard's place:\n" + out)
        self.assertLess(report.index("RuntimeError: plant: the cleanup failed"), report.index("thread 'plant-leaked' ("),
                        "the guard's text follows the cleanup's error:\n" + out)
        self.assertIn("runs test_plant._leaked\n", report, "the report names the thread's target:\n" + out)
        self.assertIn("in _leaked\n    plant_shared.RELEASE.wait(120)", report, "the report carries the thread's stack, "
                      "down to the plant's frame:\n" + out)
        self.assertEqual(err.count("thread 'plant-leaked' (ident "), 1, "stderr, the guard's second channel, names the "
                         "thread once too:\n" + out)
        self.assertIn("runs test_plant._leaked\n", err, "stderr names the thread's target:\n" + out)
        self.assertIn("in _leaked\n    plant_shared.RELEASE.wait(120)", err, "stderr carries the thread's stack, down "
                      "to the plant's frame:\n" + out)
        self.assertIn("the session-end thread guard] the teardown of "
                      "test_plant.py::TwoErrors::test_body_and_cleanup_fail", err,
                      "stderr says what wrote it and which teardown it failed:\n" + out)
        self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                         "every process that ran tests exited once the scratch conftest's stop released the thread:\n"
                         + out)
        return report, err

    def test_a_testcases_second_error_in_the_teardown_report_leaves_the_thread_named_in_it_and_on_stderr_serially(self):
        rc, out, started, _ended, _finish, marks = self._run(TWO_ERRORS_TEST, cap=LEAK_CAP_S)
        _report, err = self._assert_two_errors_name_the_thread(rc, out, started, marks)
        self.assertNotIn("pytest-xdist worker", err, "a serial run names no worker")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_testcases_second_error_leaves_the_thread_named_in_the_report_and_on_stderr(self):
        rc, out, started, _ended, _finish, marks = self._run(TWO_ERRORS_TEST, cap=LEAK_CAP_S, workers=2)
        _report, err = self._assert_two_errors_name_the_thread(rc, out, started, marks)
        self.assertRegex(err, r"this process's last test \(pytest-xdist worker gw\d+\)", "the worker's text reached "
                         "the controller's stderr, naming the worker:\n" + out)

    # -- an xfail-marked last test: the guard's error stays an error ---------------------------------------------------

    def test_a_leak_after_an_xfail_marked_last_test_fails_a_serial_run(self):
        """pytest's skipping plugin makes the teardown error of an xfail-marked test an xfail, which would leave the run
        green; tests/conftest.py keeps the guard's error an error. Whether the marked body fails (xfailed) or passes
        (xpassed), a leaked non-daemon thread fails the run with one error, at the test's teardown, whose report names
        the thread, and the body's own outcome is still the one the mark gives it."""
        for plant, body in ((XFAIL_BODY_FAILS_TEST, "xfailed"), (XFAIL_BODY_PASSES_TEST, "xpassed")):
            with self.subTest(body=body):
                rc, out, started, _ended, finish, marks = self._run(plant, cap=LEAK_CAP_S)
                self._assert_leak_reported(rc, out, started, finish, marks)
                self.assertRegex(out, r"\b1 %s\b" % body, "the body's own outcome is still reported:\n" + out)
                self.assertNotRegex(out, r"\b2 %s\b" % body, "the teardown is not reported as the body is:\n" + out)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_leak_after_an_xfail_marked_last_test_fails_the_run(self):
        rc, out, started, _ended, finish, marks = self._run(XFAIL_BODY_FAILS_TEST, cap=LEAK_CAP_S, workers=2)
        self._assert_leak_reported(rc, out, started, finish, marks)
        self.assertRegex(out, r"\b1 xfailed\b", "the body's own outcome is still reported:\n" + out)
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    # -- a last test whose own teardown fails: the guard still runs, after the runner's error -------------------------

    def _assert_fixture_teardown_error_and_leak_reported(self, rc, out, started, finish, marks):
        """The last test's fixture raised at teardown, before the guard ran: the teardown report carries the fixture's
        error, the guard's text after it (the leak's assertions: one error, the thread named once in the report and on
        stderr)."""
        self._assert_leak_reported(rc, out, started, finish, marks)
        report, _err = self._channels(out)
        self.assertIn("RuntimeError: plant: the fixture's teardown failed", report, "the premise: the teardown report "
                      "carries the fixture's error:\n" + out)
        self.assertLess(report.index("RuntimeError: plant: the fixture's teardown failed"),
                        report.index("thread 'plant-leaked' ("), "the guard's text follows the fixture's error:\n" + out)

    def test_a_last_test_whose_fixture_fails_at_teardown_is_still_checked_serially(self):
        """The runner's teardown of the last test raises (its fixture's teardown fails) before the guard runs; the guard
        runs all the same, after it. Unmarked, the run was red already on the fixture's error, and the report now names
        the leaked thread too. Under an xfail mark pytest's skipping plugin makes the fixture's error an xfail, so a guard
        that did not run there left the run green with the thread unnamed on either channel."""
        for plant, body in ((FIXTURE_TEARDOWN_FAILS_TEST, None), (FIXTURE_TEARDOWN_FAILS_XFAIL_TEST, "xfailed")):
            with self.subTest(xfail=body is not None):
                rc, out, started, _ended, finish, marks = self._run(plant, cap=LEAK_CAP_S)
                self._assert_fixture_teardown_error_and_leak_reported(rc, out, started, finish, marks)
                if body is not None:
                    self.assertRegex(out, r"\b1 %s\b" % body, "the body's own outcome is still reported:\n" + out)
                    self.assertNotRegex(out, r"\b2 %s\b" % body, "the teardown is not reported as the body is:\n" + out)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_last_test_whose_fixture_fails_at_teardown_under_xfail_is_still_checked(self):
        rc, out, started, _ended, finish, marks = self._run(FIXTURE_TEARDOWN_FAILS_XFAIL_TEST, cap=LEAK_CAP_S, workers=2)
        self._assert_fixture_teardown_error_and_leak_reported(rc, out, started, finish, marks)
        self.assertRegex(out, r"\b1 xfailed\b", "the body's own outcome is still reported:\n" + out)
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    # -- a value the report masks is masked on stderr too --------------------------------------------------------------

    @staticmethod
    def _env_value():
        """The synthetic value the child holds as ENV_NAMED_VAR, built at run time so no credential-shaped literal sits in
        this file (the secret scan reads it too)."""
        return "plantval" + "-" + "q" * 14

    def _assert_env_value_masked_on_both_channels(self, rc, out):
        """The leaked thread's name carries the synthetic env value, which the report's redaction masks: the raw value is
        on neither channel, and the thread's masked name is on stderr once, as it is in the report. Returns stderr."""
        value = self._env_value()
        report, err = self._channels(out)
        self.assertEqual(rc, 1, "the leaked thread fails the run:\n" + out)
        self.assertNotIn(value, report, "the report carries the raw value:\n" + out)
        self.assertNotIn(value, err, "stderr carries the raw value the report masks:\n" + out)
        names = re.findall(r"thread '(plant-leaked-[^'\n]*)' \(ident ", report)
        self.assertEqual(len(names), 1, "the report names the leaked thread once:\n" + out)
        masked = names[0]
        self.assertIn(sys.modules["tests.conftest"].ENV_VALUE_REDACTED, masked, "the report masks the value in the "
                      "thread's name:\n" + out)
        self.assertEqual(err.count("thread '%s' (ident " % masked), 1, "stderr names the thread with the masked name the "
                         "report prints:\n" + out)
        return err

    @unittest.skipUnless("tests.conftest" in sys.modules, "reads the redaction's marker from tests/conftest.py")
    def test_a_value_the_report_masks_is_masked_on_stderr_in_a_serial_run(self):
        rc, out, _started, _ended, _finish, _marks = self._run(ENV_NAMED_TEST, cap=LEAK_CAP_S,
                                                               env_extra={ENV_NAMED_VAR: self._env_value()})
        self._assert_env_value_masked_on_both_channels(rc, out)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    @unittest.skipUnless("tests.conftest" in sys.modules, "reads the redaction's marker from tests/conftest.py")
    def test_under_two_workers_a_value_the_report_masks_is_masked_on_the_controllers_stderr(self):
        rc, out, _started, _ended, _finish, _marks = self._run(ENV_NAMED_TEST, cap=LEAK_CAP_S, workers=2,
                                                               env_extra={ENV_NAMED_VAR: self._env_value()})
        err = self._assert_env_value_masked_on_both_channels(rc, out)
        self.assertRegex(err, r"this process's last test \(pytest-xdist worker gw\d+\)", "the worker's text reached "
                         "the controller's stderr:\n" + out)

    @unittest.skipUnless("tests.conftest" in sys.modules, "reads the redaction's marker from tests/conftest.py")
    def test_a_value_in_the_last_tests_node_id_is_masked_in_the_stderr_header(self):
        """Everything the guard writes to stderr goes through the redaction, its header too, which names the process's
        last test by its node id. (The report's own headline and short summary print the node id as pytest renders it;
        that is the report's redaction, which scrubs a report's text and not its node id, and is not checked here.)"""
        value = self._env_value()
        rc, out, _started, _ended, _finish, _marks = self._run(ENV_NAMED_ID_TEST, cap=LEAK_CAP_S,
                                                               env_extra={ENV_NAMED_VAR: value})
        _report, err = self._channels(out)
        self.assertEqual(rc, 1, "the leaked thread fails the run:\n" + out)
        self.assertEqual(err.count("thread 'plant-leaked' (ident "), 1, "stderr names the leaked thread:\n" + out)
        self.assertNotIn(value, err, "stderr carries the raw value in the last test's node id:\n" + out)
        self.assertIn("the session-end thread guard] the teardown of test_plant.py::test_leak_with_an_env_value_in_its_id"
                      "[%s], this process's last test" % sys.modules["tests.conftest"].ENV_VALUE_REDACTED, err,
                      "the stderr header names the test by its masked node id:\n" + out)

    @unittest.skipUnless("tests.conftest" in sys.modules, "reads the redaction's marker from tests/conftest.py")
    def test_a_value_the_report_masks_is_masked_in_the_guards_text_after_a_testcases_second_error(self):
        rc, out, _started, _ended, _finish, _marks = self._run(TWO_ERRORS_ENV_NAMED_TEST, cap=LEAK_CAP_S,
                                                               env_extra={ENV_NAMED_VAR: self._env_value()})
        self._assert_env_value_masked_on_both_channels(rc, out)
        report, _err = self._channels(out)
        self.assertLess(report.index("RuntimeError: plant: the cleanup failed"), report.index("thread 'plant-leaked-"),
                        "the masked name is in the guard's text, added after the cleanup's error:\n" + out)

    @unittest.skipUnless("tests.conftest" in sys.modules, "reads the redaction's marker from tests/conftest.py")
    def test_a_token_the_report_masks_on_its_marked_diff_line_is_masked_on_stderr_too(self):
        """A pytest.fail with a traceback raised inside the guard's call (a Thread subclass's join) fails the guard,
        and its message goes to stderr as the guard's failure. The report prints that message under pytest's `E`
        marker, and the pattern net's rule for a failed comparison's diff lines is keyed on that marker, so a
        credential-shaped token on a `- <token>` line is masked there. Stderr prints the message without the marker,
        so it is scrubbed marked too, as the report's crash message is: the token, which no environment holds, is on
        neither channel."""
        token = "abcdefghijklmnopqrstuvwx" + "0123456789"
        rc, out, _started, _ended, _finish, _marks = self._run(FAILS_IN_JOIN_TEST, cap=LEAK_CAP_S)
        report, err = self._channels(out)
        self.assertEqual(rc, 1, "the join's failure fails the run:\n" + out)
        self.assertIn("plant: a join that fails", report, "the report carries the join's failure:\n" + out)
        self.assertIn("plant: a join that fails", err, "stderr carries the join's failure:\n" + out)
        self.assertNotIn(token, report, "the premise: the report masks the token on its marked diff line:\n" + out)
        self.assertNotIn(token, err, "stderr carries the token the report masks:\n" + out)
        self.assertIn("- " + sys.modules["tests.conftest"].CREDENTIAL_REDACTED, err, "stderr masks the token on its "
                      "diff line:\n" + out)

    # -- idle executor workers alone fail the run, and the process exits ----------------------------------------------

    def _assert_idle_workers_fail_and_the_process_exits(self, rc, out, started, marks):
        self.assertEqual(rc, 1, "idle executor workers alone fail the run:\n" + out)
        self.assertIn("thread 'plant-pool_0'", out, "the idle worker of the pool left open is named:\n" + out)
        self.assertIn("thread 'asyncio_0'", out, "the idle worker of the event loop never closed is named:\n" + out)
        self.assertNotIn("plant-fx-", out, "threads the fixtures stop at teardown are not named")
        self.assertTrue(started, "the plant's tests recorded the processes that ran them:\n" + out)
        self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                         "every process that ran tests exited: its atexit handler, which the interpreter runs only after "
                         "joining its non-daemon threads and the threads concurrent.futures' exit hooks join, wrote its "
                         "marker; these processes wrote none:\n" + out)
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

    # -- the worker of a pool a daemon thread started is guarded: concurrent.futures' exit hook joins it ---------------

    def _assert_daemon_pool_worker_reported(self, rc, out, started, marks, kind):
        """What the busy and the idle runs share. The pool's worker, plant-dpool-<kind>_0, was a daemon thread (the plant
        records its flag), and the run fails with exactly one error, naming that worker once with the executor label; the
        daemon thread that started the pool and the plain daemon threads beside it are not named; every process that ran
        tests exits. Returns the worker's report block."""
        worker, spawner = "plant-dpool-%s_0" % kind, "plant-dspawner-%s" % kind
        flags = {n: daemon for names in started.values() for n, daemon in names}
        self.assertIs(flags.get(spawner), True, "the thread that started the pool was a daemon thread:\n" + out)
        self.assertIs(flags.get(worker), True, "the pool's worker was a daemon thread, its flag taken from the daemon "
                      "thread that created it:\n" + out)
        self.assertEqual(rc, 1, "the %s worker of a pool a daemon thread started fails the run:\n%s" % (kind, out))
        self.assertEqual(len(re.findall(r"ERROR at teardown of test_", out)), 1, "one error, at a teardown:\n" + out)
        self.assertRegex(out, r"\n1 error\b|, 1 error\b", out)
        report, _err = self._channels(out)
        self.assertEqual(report.count("thread '%s'" % worker), 1, "the report names the worker once:\n" + out)
        mine = [b for b in self._report_blocks(report) if b.startswith("thread '%s' " % worker)]
        self.assertEqual(len(mine), 1, "one report block is the worker's:\n" + out)
        self.assertIn(EXECUTOR_LABEL, mine[0].split("\n", 1)[0], "the worker carries the executor label:\n" + mine[0])
        self.assertNotIn(spawner, out, "the daemon thread that started the pool, still running, is not named")
        self.assertNotIn("plant-daemon", out, "plain daemon threads alive at the same moment are not named")
        self.assertNotIn("plant-fx-", out, "threads the fixtures stop at teardown are not named")
        self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                         "every process that ran tests exited: its atexit handler wrote its marker; these processes wrote "
                         "none:\n" + out)
        return mine[0]

    def _assert_daemon_pool_busy_worker_reported(self, rc, out, started, ended, finish, marks):
        worker = "plant-dpool-busy_0"
        block = self._assert_daemon_pool_worker_reported(rc, out, started, marks, "busy")
        self.assertIn("in _busy_daemon_pool_task\n", block, "the worker's block carries its task's frame:\n" + block)
        self.assertIn(RUNNING_TASK_CAUSE, block.split("\n", 1)[0], "and the label's running-task cause:\n" + block)
        # the premise, executed: the interpreter joins this daemon thread at exit, so the process waits for its task
        owner = [pid for pid, names in started.items() if worker in {n for n, _daemon in names}]
        self.assertEqual(len(owner), 1, "one process started the worker:\n" + out)
        pid = owner[0]
        self.assertIn(worker, finish.get(pid, {}).get("alive", []), "the worker was still running at "
                      "pytest_sessionfinish, after the guard:\n" + out)
        self.assertIn(worker, ended.get(pid, {}), "the worker's task wrote its end record, EXIT_HOLD_S after the stop: "
                      "the process did not exit before its daemon worker ended:\n" + out)
        self.assertGreaterEqual(ended[pid][worker] - marks["release"][pid], EXIT_HOLD_S / 2,
                                "the task ended EXIT_HOLD_S after the scratch conftest's stop")
        self.assertGreaterEqual(marks["atexit"][pid], ended[pid][worker],
                                "the process's atexit handler ran after its daemon worker's task ended: the interpreter "
                                "joined that daemon thread before it ran its atexit handlers")

    def test_a_busy_worker_of_a_pool_a_daemon_thread_started_fails_a_serial_run(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + DAEMON_BUSY_TEST
        rc, out, started, ended, finish, marks = self._run(plant, cap=LEAK_CAP_S)
        self._assert_daemon_pool_busy_worker_reported(rc, out, started, ended, finish, marks)

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_a_busy_worker_of_a_pool_a_daemon_thread_started_fails_the_run(self):
        plant = "".join(DAEMON_TEST.format(i=i) for i in range(TESTS)) + DAEMON_BUSY_TEST
        rc, out, started, ended, finish, marks = self._run(plant, cap=LEAK_CAP_S, workers=2)
        self._assert_daemon_pool_busy_worker_reported(rc, out, started, ended, finish, marks)
        self.assertEqual(len(finish), 3, "a controller and two workers each reached pytest_sessionfinish:\n" + out)
        self.assertRegex(out, r"ERROR at teardown of test_\w+ _+\n\[gw\d+\] ", "the report came from a worker:\n" + out)

    def test_an_idle_worker_of_a_pool_a_daemon_thread_started_fails_a_serial_run_and_the_process_exits(self):
        rc, out, started, _ended, _finish, marks = self._run(DAEMON_IDLE_TEST, cap=LEAK_CAP_S)
        self._assert_daemon_pool_worker_reported(rc, out, started, marks, "idle")

    @unittest.skipUnless(HAS_XDIST, "pytest-xdist not installed")
    def test_under_two_workers_an_idle_worker_of_a_pool_a_daemon_thread_started_fails_the_run_and_each_worker_exits(self):
        rc, out, started, _ended, _finish, marks = self._run(DAEMON_IDLE_TEST, cap=LEAK_CAP_S, workers=2)
        self._assert_daemon_pool_worker_reported(rc, out, started, marks, "idle")

    # -- a missing exit-join table fails the run, naming it -------------------------------------------------------------

    def test_a_missing_exit_join_table_fails_a_serial_run_naming_the_attribute(self):
        for module, attr in (("concurrent.futures.thread", "_threads_queues"),
                             ("concurrent.futures.process", "_threads_wakeups")):
            with self.subTest(table="%s.%s" % (module, attr)):
                rc, out, started, _ended, _finish, marks = self._run(PLAIN_TEST, drop=(module, attr))
                self.assertTrue(started, "the plant's test ran:\n" + out)
                self.assertEqual(rc, 1, "a missing %s.%s fails the run:\n%s" % (module, attr, out))
                self.assertEqual(len(re.findall(r"ERROR at teardown of test_plain", out)), 1, "one error, at the "
                                 "teardown of the process's last test:\n" + out)
                report, err = self._channels(out)
                for channel, text in (("the report", report), ("stderr", err)):
                    self.assertIn("session-end thread guard cannot read %s.%s on this Python" % (module, attr), text,
                                  "%s names the missing attribute:\n%s" % (channel, out))
                self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                                 "the process exited once the scratch conftest put the table back:\n" + out)

    def test_a_table_that_changes_during_every_read_fails_a_serial_run_and_the_report_prints_that_failure_once(self):
        """The guard's failure for a table it could not read by its deadline, with a non-daemon thread still alive, prints
        once in the report: the guard raises it outside the handler of the table's own failure, so pytest does not print
        that one before it as its context ("During handling of the above exception")."""
        rc, out, started, _ended, _finish, marks = self._run(LEAK_TEST, cap=LEAK_CAP_S,
                                                             conftest_extra=TABLE_KEEPS_CHANGING)
        report, err = self._channels(out)
        table = "could not read concurrent.futures.thread._threads_queues before its deadline"
        self.assertTrue(started, "the plant's test ran:\n" + out)
        self.assertEqual(rc, 1, "the table's failure fails the run:\n" + out)
        self.assertEqual(len(re.findall(r"ERROR at teardown of test_leak", report)), 1, "one error, at the teardown of "
                         "the process's last test:\n" + out)
        self.assertEqual(report.count(table), 1, "the report prints the table's failure once:\n" + out)
        self.assertNotIn("During handling of the above exception", report, "the report prints no exception chain:\n"
                         + out)
        self.assertEqual(report.count("thread 'plant-leaked' (ident "), 1, "the report names the non-daemon thread "
                         "still alive once:\n" + out)
        self.assertEqual(err.count(table), 1, "stderr prints the table's failure once:\n" + out)
        self.assertEqual(sorted(pid for pid in started if pid not in marks["atexit"]), [],
                         "the process exited once the scratch conftest put the table back and released the thread:\n"
                         + out)

    # -- threads that end within the cap, and plain daemon threads, leave the run green -------------------------------

    def _assert_green_and_waited(self, rc, out, started, ended, finish, _marks):
        self.assertEqual(rc, 0, "threads that end within the cap and plain daemon threads do not fail the run:\n" + out)
        self.assertIn("%d passed" % TESTS, out, out)
        self.assertNotIn("error", out.lower(), out)
        names = sorted(n for ns in started.values() for n, _daemon in ns if not n.startswith("plant-fx-"))
        expected = ["plant-within-cap-%d" % i for i in range(TESTS)] + ["plant-daemon-%d" % i for i in range(TESTS)]
        self.assertEqual(names, sorted(expected), "the plant started its threads:\n" + out)
        # the fixtures' threads: one per test from the function-scoped fixture, and one in every process that ran tests
        # from the session-scoped one, each stopped only by its fixture's teardown. A guard that ran before the runner's
        # teardown (its check before the wrapper's yield, or a plain implementation marked tryfirst or not ordered, since
        # the runner's plugin registers before any conftest) would wait its cap for them and then fail the run naming them.
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
                    self.assertIn(name, finish[pid]["alive"], "a plain daemon thread ran through the guard, neither "
                                                              "waited for nor named")
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
    shutdown, or one shut down with wait=False while a task still runs. Stood in for by a never-started Thread subclass
    carrying the manager thread's module and name, so no process is spawned; the label is chosen from the thread's type
    alone, and the manager thread's stack reads the same idle or busy, so the label's text is what a pin can check."""

    def test_a_process_pool_manager_thread_is_labelled(self):
        cf = sys.modules["tests.conftest"]
        manager = type("_ExecutorManagerThread", (threading.Thread,), {"__module__": "concurrent.futures.process"})(
            name="plant-manager")
        report = cf._thread_report(manager, {})
        self.assertIn("runs concurrent.futures.process._ExecutorManagerThread.run (a ProcessPoolExecutor's manager "
                      "thread: a pool left without shutdown, or one shut down with wait=False while a task still runs; its "
                      "stack reads the same either way)", report)


@unittest.skipUnless("tests.conftest" in sys.modules, "the guard is tests/conftest.py's (pytest-only)")
class ExitJoinTables(unittest.TestCase):
    """The guard reads concurrent.futures' exit-join tables (tests/conftest.py's EXIT_JOIN_TABLES) and waits for every
    thread in them, whatever its daemon flag, as the interpreter's exit hooks do. In this process: the two tables exist on
    this Python and are what their modules' exit hooks read; the two hooks are the only ones the standard library
    registers with threading._register_atexit; a live daemon thread in either table is returned by the guard while a
    plain daemon thread beside it is not; the tables are read again after every pass; and a read that meets a concurrent
    insert is read again, up to the guard's one deadline, where a table that changed during every read fails the guard
    by name, naming too the non-daemon threads still alive."""

    TABLES = (("concurrent.futures.thread", "_threads_queues"), ("concurrent.futures.process", "_threads_wakeups"))

    def test_the_guard_reads_the_tables_the_exit_hooks_join(self):
        import concurrent.futures.process   # noqa: F401  loaded, so both modules are in sys.modules below
        import concurrent.futures.thread    # noqa: F401
        cf = sys.modules["tests.conftest"]
        self.assertEqual(cf.EXIT_JOIN_TABLES, self.TABLES)
        for module, attr in self.TABLES:
            with self.subTest(table="%s.%s" % (module, attr)):
                mod = sys.modules[module]
                self.assertTrue(hasattr(mod, attr), "%s.%s exists on this Python" % (module, attr))
                self.assertIn(attr, mod._python_exit.__code__.co_names, "%s's exit hook reads its table as the global "
                              "%s" % (module, attr))

    def test_they_are_the_only_exit_hooks_the_standard_library_registers(self):
        """Derived from the standard library's source on this Python: every module outside its test packages, idlelib and
        site-packages whose code calls _register_atexit (threading's own definition of it excluded). A premise pin: it
        reads no guard, only the source against TABLES, so no change to the guard can turn it red."""
        root = sysconfig.get_paths()["stdlib"]
        skip = {"test", "tests", "idlelib", "site-packages", "dist-packages", "__pycache__"}
        call = re.compile(r"^(?![ \t]*def\b)[^#\n]*\b_register_atexit\(", re.M)
        found, read = set(), 0
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in skip]
            for f in files:
                if not f.endswith(".py"):
                    continue
                with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                read += 1
                if "_register_atexit(" in text and call.search(text):
                    mod = os.path.relpath(os.path.join(d, f), root)[:-len(".py")].replace(os.sep, ".")
                    found.add(mod[:-len(".__init__")] if mod.endswith(".__init__") else mod)
        self.assertGreater(read, 100, "the walk read the standard library under %s" % root)
        self.assertEqual(found, {module for module, _attr in self.TABLES})

    def _returned_alone(self, thread, plain):
        """The guard's result at a short cap over a list of the main thread, `thread` and `plain` (a daemon thread in no
        table), through the guard's own binding of threading.enumerate."""
        cf = sys.modules["tests.conftest"]
        with mock.patch.object(cf, "_enumerate", return_value=[threading.main_thread(), thread, plain]):
            return cf.threads_left_at_session_end(0.2)

    def test_a_daemon_threads_pool_worker_is_returned_and_a_plain_daemon_thread_is_not(self):
        """A pool started from a daemon thread: its worker, a daemon thread, is in concurrent.futures.thread's table."""
        import concurrent.futures
        stop, ready, box = threading.Event(), threading.Event(), {}

        def spawner():
            pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-inproc-dpool")
            pool.submit(stop.wait, 60)
            pool.shutdown(wait=False)
            box["worker"] = [t for t in threading.enumerate() if t.name.startswith("plant-inproc-dpool_")]
            ready.set()
            stop.wait(60)

        spawn = threading.Thread(target=spawner, name="plant-inproc-dspawner", daemon=True)
        threads = [spawn]                   # the worker joins the list once it is known
        self.addCleanup(join_started, stop, threads, 60)
        spawn.start()
        self.assertTrue(ready.wait(30))
        threads.extend(box["worker"])
        worker, = box["worker"]
        self.assertTrue(worker.daemon, "the worker took the daemon flag of the thread that created it")
        self.assertEqual(self._returned_alone(worker, spawn), [worker], "the guard returned the busy daemon worker, which "
                         "concurrent.futures' exit hook joins, and not the plain daemon thread that started its pool")

    def test_a_daemon_thread_in_the_process_pool_table_is_returned_and_a_plain_daemon_thread_is_not(self):
        """A ProcessPoolExecutor started from a daemon thread has a daemon manager thread, which the process module's exit
        hook joins. Stood in for by a live daemon thread entered in concurrent.futures.process's own table, with a wakeup
        the hook can call, and taken out again at cleanup; no process is spawned."""
        import concurrent.futures.process as cfp
        stop = threading.Event()

        class Wakeup:                   # the exit hook calls wakeup() on each entry before it joins the thread
            def wakeup(self):
                stop.set()

        manager = threading.Thread(target=stop.wait, args=(60,), name="plant-inproc-manager", daemon=True)
        plain = threading.Thread(target=stop.wait, args=(60,), name="plant-inproc-plain", daemon=True)
        self.addCleanup(join_started, stop, (manager, plain), 60)
        for t in (manager, plain):
            t.start()
        cfp._threads_wakeups[manager] = Wakeup()
        self.addCleanup(cfp._threads_wakeups.pop, manager, None)
        self.assertEqual(self._returned_alone(manager, plain), [manager], "the guard returned the daemon thread in "
                         "concurrent.futures.process's table, and not the plain daemon thread")

    def test_the_tables_are_read_again_after_every_pass(self):
        """The guard reads the exit-join tables again after every pass, as it reads the thread list, so a busy worker
        that enters a table after the guard's first read is waited for too. A daemon thread starts a pool whose worker
        W1, a daemon thread in concurrent.futures.thread's table, runs a task that waits for the guard's first read of the
        thread list, then starts a second pool from W1 with a task that runs on, and ends; W1 ends with it, within the
        cap. The second pool's worker W2 takes W1's daemon flag and enters the table only after the guard's first read,
        so a guard that read the tables once would skip it, and at exit the process would wait for it unreported. At a
        2 s cap the guard returns W2. A spy on the guard's own binding of threading.enumerate hands it only the main
        thread and the plant's threads."""
        import concurrent.futures
        cf = sys.modules["tests.conftest"]
        real_enumerate = cf._enumerate
        stop, first_read, ready, box = threading.Event(), threading.Event(), threading.Event(), {}

        def first_task():
            first_read.wait(60)
            pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-inproc-reread-w2")
            pool.submit(stop.wait, 60)
            pool.shutdown(wait=False)
            box["w2"] = [t for t in real_enumerate() if t.name.startswith("plant-inproc-reread-w2_")]

        def spawner():
            pool = concurrent.futures.ThreadPoolExecutor(1, thread_name_prefix="plant-inproc-reread-w1")
            pool.submit(first_task)
            pool.shutdown(wait=False)
            box["w1"] = [t for t in real_enumerate() if t.name.startswith("plant-inproc-reread-w1_")]
            ready.set()
            stop.wait(60)

        def spy():
            main = threading.main_thread()
            listed = [t for t in real_enumerate() if t is main or t.name.startswith("plant-inproc-reread-")]
            first_read.set()                    # W1's task goes on only once the guard has read the list
            return listed

        spawn = threading.Thread(target=spawner, name="plant-inproc-reread-spawner", daemon=True)
        threads = [spawn]                       # the workers join the list once they are known
        self.addCleanup(join_started, stop, threads, 60)
        self.addCleanup(first_read.set)
        spawn.start()
        self.assertTrue(ready.wait(30))
        threads.extend(box["w1"])
        with mock.patch.object(cf, "_enumerate", side_effect=spy):
            left = cf.threads_left_at_session_end(2.0)
        threads.extend(box.get("w2", []))
        w2, = box["w2"]
        self.assertTrue(w2.daemon, "the second worker took the daemon flag of the worker that created it")
        self.assertEqual(left, [w2], "the guard did not return the busy worker that entered concurrent.futures.thread's "
                         "table after its first read (a guard that reads the tables once is one way this happens)")

    def test_a_table_read_that_meets_a_concurrent_insert_is_read_again(self):
        """On 3.10 to 3.13 iterating a WeakKeyDictionary walks the live dict, so a pool started while the guard reads
        concurrent.futures.thread's table raises RuntimeError ("dictionary changed size during iteration"), and the guard
        reads the table again. (On 3.14 the iteration walks a copy and does not raise.) Stood in for, on every Python, by
        a table whose first iteration raises that error and whose later ones yield a live daemon thread: the guard
        returns that thread, after exactly one retry. The stand-in passes any insert on to the real table, so a pool
        another thread starts while it is in place is still recorded where the exit hook reads. The pin drives the
        guard's clock (its own binding, _monotonic) from the stand-in's reads: it reads 0 until the table's second read,
        so the deadline is the cap and the retry after the first read falls before it, and then the deadline itself, so
        the guard returns the thread it found without joining it. No real time passes on the guard's clock, so the pin
        does not depend on the cap or on how long the machine takes to reach the retry."""
        import concurrent.futures.thread as cft
        cf = sys.modules["tests.conftest"]
        real_table = cft._threads_queues
        stop = threading.Event()
        worker = threading.Thread(target=stop.wait, args=(60,), name="plant-inproc-retry", daemon=True)
        self.addCleanup(join_started, stop, (worker,), 60)
        worker.start()
        reads = []
        cap = 0.2

        class ChangesOnFirstRead:
            def __iter__(self):
                reads.append(len(reads) + 1)
                if len(reads) == 1:
                    raise RuntimeError("dictionary changed size during iteration")
                return iter([worker])

            def __setitem__(self, key, value):
                real_table[key] = value

        with mock.patch.object(cft, "_threads_queues", ChangesOnFirstRead()), \
                mock.patch.object(cf, "_enumerate", return_value=[threading.main_thread(), worker]), \
                mock.patch.object(cf, "_monotonic", new=lambda: 0.0 if len(reads) < 2 else cap):
            left = cf.threads_left_at_session_end(cap)
        self.assertEqual(left, [worker], "the guard returned the daemon thread its second read of the table found")
        self.assertEqual(reads, [1, 2], "the guard read the table again once, after the read that raised")

    def test_a_table_that_changes_during_every_read_ends_the_guard_at_its_deadline_naming_the_table_and_threads(self):
        """A table another thread adds to without pause changes during every read, so every read raises RuntimeError.
        The guard reads it again only until its one deadline and then fails naming the table: it does not retry a read
        after the deadline. The failure also names each non-daemon thread still alive, which holds the process at exit
        whatever the table lists (a plant listed beside a plain daemon thread, which is not named). Stood in for, on
        every Python, by a table whose every iteration walks a real dict and adds to it mid-walk, as another thread
        inserting forever would, so each read raises the error a real concurrent insert raises. The process-wide
        time.monotonic is frozen for the call, as a test's leaked patch could leave it: the retry's bound is on the
        guard's own clock, so the guard still ends. The guard runs on a helper thread under a BACKSTOP: a guard whose
        retry has no bound, or is bounded on a clock that does not move, never ends here, so the pin fails when the
        helper is still running backstop_s (20 s) after the call, and that backstop firing IS the defect, not a timing
        flake. Once the backstop has fired the stand-in holds still, so such a guard ends and leaves no thread
        spinning. The stand-in passes any insert on to the real table, as the retry pin's does."""
        import concurrent.futures.thread as cft
        cf = sys.modules["tests.conftest"]
        real_table = cft._threads_queues
        cap, backstop_s = 1.0, 20.0
        holds_still = threading.Event()     # set once the backstop has fired, and at cleanup
        stop = threading.Event()
        left_alive = threading.Thread(target=stop.wait, args=(60,), name="plant-inproc-left-at-table-failure")
        plain = threading.Thread(target=stop.wait, args=(60,), name="plant-inproc-plain-daemon", daemon=True)
        self.addCleanup(join_started, stop, (left_alive, plain), 60)
        left_alive.start()
        plain.start()
        reads = [0]
        got = {}

        class ChangesDuringEveryRead:
            def __iter__(self):
                reads[0] += 1
                if holds_still.is_set():
                    return iter(())
                walked = {object(): None}
                it = iter(walked)
                next(it)
                walked[object()] = None     # an insert mid-walk, as another thread's would be
                return it                   # its next step raises RuntimeError (the dict changed size mid-walk)

            def __setitem__(self, key, value):
                real_table[key] = value

        def run_guard():
            t0 = time.perf_counter()
            try:
                got["left"] = cf.threads_left_at_session_end(cap)
            except BaseException as e:      # pytest.fail raises a BaseException; reported below, on the test's thread
                got["error"] = e
            got["elapsed"] = time.perf_counter() - t0

        helper = threading.Thread(target=run_guard, name="plant-inproc-changing-guard", daemon=True)
        self.addCleanup(join_started, holds_still, (helper,), 30)
        with mock.patch.object(cft, "_threads_queues", ChangesDuringEveryRead()), \
                mock.patch.object(cf, "_enumerate", return_value=[threading.main_thread(), left_alive, plain]), \
                mock.patch.object(time, "monotonic", return_value=0.0):
            helper.start()
            helper.join(backstop_s)
            ended = not helper.is_alive()
            holds_still.set()               # a guard still reading now reads a table that holds still, and ends
            helper.join(30)
        self.assertTrue(ended, "BACKSTOP: the guard had not ended %g s after the call, at a %g s cap: it went on "
                        "reading a table that changed during every read (%d reads) past its deadline. This backstop "
                        "firing is the defect the pin exists for" % (backstop_s, cap, reads[0]))
        err = got.get("error")
        self.assertIsNotNone(err, "the guard returned %r instead of failing on a table it could not read by its "
                             "deadline" % (got.get("left"),))
        self.assertEqual(type(err).__name__, "Failed", "the guard failed through pytest.fail: %r" % (err,))
        self.assertIn("could not read concurrent.futures.thread._threads_queues before its deadline", str(err),
                      "the failure names the table")
        self.assertIn("every read of it on the guard's last pass raised RuntimeError", str(err),
                      "the failure says the table changed during every read")
        self.assertIn("thread 'plant-inproc-left-at-table-failure'", str(err),
                      "the failure names the non-daemon thread still alive, which needs no table to be guarded")
        self.assertNotIn("plant-inproc-plain-daemon", str(err), "a plain daemon thread, in no table, is not named")
        self.assertGreaterEqual(got["elapsed"], cap * 0.9, "the guard failed %.2f s into a %g s cap: it gave up before "
                                "its deadline" % (got["elapsed"], cap))
        self.assertLess(got["elapsed"], cap + 3.0, "the guard failed %.2f s into a %g s cap: it read on past its "
                        "deadline" % (got["elapsed"], cap))
        self.assertGreaterEqual(reads[0], 2, "the guard read the table again after a read that raised")


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
        so a process that leaks several threads pays at most the cap, not the cap per thread. On a fake clock: the
        guard's own clock binding reads it, and three listed threads, never started, each advance it by the whole timeout
        they are joined for, as a join on a thread that never ends does. Joined for the full cap each, they would spend
        three times the cap. This pin checks the upper bound only: a guard that did not wait at all would pass it. That
        the guard waits is pinned by other pins, among them the green runs' witness and the monotonic pin below."""
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
        only then lets the parent go, so the first list holds the parent and not the child. Of each list it reads, the
        spy hands the guard only the main thread, the parent and the child, so the guard waits for no other thread in
        the process, such as another test's thread still running in the same worker. With `child_ends_on_second_read`,
        the spy's second read, again once it has read the list, lets the child end; otherwise the child runs on until
        the test's cleanup lets it go, or for 5 s. Returns (the guard's result, the parent, the child)."""
        cf = sys.modules["tests.conftest"]
        real_enumerate = cf._enumerate
        first_read, child_may_end = threading.Event(), threading.Event()

        def child_body():
            child_may_end.wait(5)               # ends once let go, or after 5 s: past the second pin's 1 s cap

        child = threading.Thread(target=child_body, name="plant-chain-child")

        def parent():
            first_read.wait(60)
            child.start()                       # start() returns once the child runs, before the parent ends

        par = threading.Thread(target=parent, name="plant-chain-parent")
        reads = []

        def spy():
            main = threading.main_thread()
            listed = [t for t in real_enumerate() if t is main or t is par or t is child]
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
        waited for too. The child here is let go at the guard's second read of the list; without that read it would run
        on, for up to 5 s, after the guard returned."""
        left, par, child = self._chain(5.0, child_ends_on_second_read=True)
        self.assertFalse(child.is_alive(), "the guard returned while the child its parent started as it exited was still "
                         "running: it did not wait for that child, which only a second read of the thread list finds")
        self.assertNotIn(child, left)
        self.assertNotIn(par, left)

    def test_a_thread_started_as_another_exits_is_returned_while_it_runs_past_the_cap(self):
        """The same chain with a child that runs on: at a short cap the guard returns the child, which only a second read
        of the thread list can find, and not its parent, which has ended."""
        left, par, child = self._chain(1.0, child_ends_on_second_read=False)
        self.assertIn(child, left, "the guard did not return the chain's child, the thread its parent starts as it exits, "
                      "which only a second read of the thread list finds (a guard that reads the list once is one way "
                      "this happens)")
        self.assertTrue(child.is_alive())
        self.assertNotIn(par, left)

    def test_off_the_main_thread_neither_the_main_thread_nor_the_checking_thread_is_waited_for(self):
        """The guard leaves out the main thread and the thread running the check. Every other pin runs the guard on the
        main thread, where the two are one object; here a NON-daemon helper thread runs it (a daemon one, in no
        concurrent.futures table, would be left out as a daemon whatever either clause said, so dropping a clause would go
        unseen) over a thread list of exactly those two. Waiting for either would take the whole cap: the main thread is
        blocked joining the helper, and a thread's join on itself raises the RuntimeError the guard passes over as a
        thread caught mid-start."""
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
        self.assertNotIn(t, left, "the guard returned a thread that ends within its cap: it did not wait for the thread (a "
                         "leaked patch of time.monotonic that moved its deadline is one way this happens)")
        self.assertFalse(t.is_alive(), "the guard waited for the thread to end")


if __name__ == "__main__":
    unittest.main()
