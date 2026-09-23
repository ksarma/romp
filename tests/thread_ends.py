"""The one cleanup shape for ending a list of threads a test started (T282; round 2 of PR 891's review, 2026-09-22).

A cleanup registered BEFORE a start loop (`self.addCleanup(...)` then `for t in ts: t.start()`) runs on every exit path,
including the one where the body failed between two starts, and Thread.join raises RuntimeError ("cannot join thread
before it is started") on a thread never started: an unguarded list join there turns the one failure into a failure and
a cleanup error. This helper is that guard, written once: it sets the release the threads wait on (when there is one),
then joins only the threads whose `ident` is not None, i.e. the ones that started (ident stays set after a thread ends,
so a finished thread is joined and returns at once). Every cleanup REGISTRATION in tests/test_*.py that joins a list of
threads (addCleanup, addClassCleanup, addfinalizer, addModuleCleanup, or a registrar handed in as a parameter whose name says
cleanup) goes through it: tests/test_thread_stop_census.py pins that (list_join_cleanups), reads a cleanup that calls it as
the stop of the threads it is handed, and runs a nested case whose planted failure between two starts reds when the guard is
stripped. The pin covers registrations, the constructs unittest runs on every exit path; a tearDown or tearDownClass that
joins a list of threads inline is outside it and named rather than read: tests/test_heartbeat_thread.py's tearDown (:70)
and tests/test_ws_liveness.py's tearDown (:116) join self.threads inline.

Only the standard library is imported here: the module is imported into test modules above their state preamble.
"""


def join_started(release, threads, timeout):
    """Set `release` (a threading.Event, or None when the threads wait on nothing the test holds), then join, with
    `timeout` seconds each, every thread in `threads` that was started. A thread never started (ident None) is skipped,
    not joined: the body may have failed before its start."""
    if release is not None:
        release.set()
    for t in threads:
        if t.ident is not None:
            t.join(timeout)
