#!/usr/bin/env python3
"""romp holds no API key (the user 2026-09-08): Claude Code's own credential resolution is the only key path.

kernel/credentials.py is the whole of romp's contact with API credentials, and this module pins it:
  * the settings reader follows Claude Code's precedence (managed, project local, project, user) and reads
    the empty string as "helper disabled", a null as "not defined here";
  * the in-process helper run follows the CLI's contract (one line on stdout, exit 0) and its TTL memo,
    never sees the kernel's own environment, runs in a session of its own, and when the bound cuts it leaves
    no process of its group running (a process that left the group is the stated exception); the run's Popen
    block closes the pipe and attempts the shell's reap on its ways out, and the roads where it does not (a
    KeyboardInterrupt before the block is entered, or one that finds the quarter second spent or lands in that
    wait) or where it waits without a bound on a running shell are planted as stated;
  * the boot check stops the kernel on any retired provider line, the marker, or a key in the kernel's
    environment, naming variables and files only;
  * the judges launch keyless for a key-billed call (the first pass after boot like every later one) and
    pass the helper suppression for a login-billed one;
  * the kernel's own catalog credential comes from the helper, and main() runs the boot check first.

Synthetic values throughout: the fixture helper prints a string no validator would take for a key."""
import inspect
import json
import os
import select
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from romp_load import load_source
from fs_clock import move_ctime   # noqa: E402  the shared test helper, on the path the line above put there
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their roots at import time, and only pytest runs conftest's
# floors (a bare unittest or script run otherwise reads and writes REAL state and REAL settings).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]
for _n in ("ANTHROPIC_API_KEY", "ROMP_API_KEY_CMD", "ROMP_API_KEY_REF", "ANTHROPIC_AUTH_TOKEN",
           "CLAUDE_CODE_OAUTH_TOKEN", "ROMP_EXPECTED_AUTH", "CLAUDE_CODE_API_KEY_HELPER_TTL_MS"):
    os.environ.pop(_n, None)
cred = load_source("romp_credentials", os.path.join(ROOT, "kernel", "credentials.py"))
sb = load_source("romp_sdk_backend_cred", os.path.join(BIN, "romp_sdk_backend.py"))
jd = load_source("romp_judge_cred", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_cred", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
HELPER_OUT = "synthetic-helper-output-1"          # not key-shaped on purpose: nothing may mistake it for one


def _helper_script(d, name="helper.sh", out=HELPER_OUT, body=None):
    """A fixture helper: touches a marker each run (so runs are countable) and prints `out`."""
    p = Path(d) / name
    marker = Path(d) / (name + ".ran")
    p.write_text(body or "#!/bin/sh\nprintf '.' >> '%s'\necho '%s'\n" % (marker, out))
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return str(p), marker


def _runs(marker):
    try:
        return len(marker.read_text())
    except OSError:
        return 0


def _proc(pid):
    """/proc/<pid>/stat as (state, ppid, pgrp, session, starttime), or None when no process has the pid (it was
    reaped) or the platform has no /proc."""
    try:
        with open("/proc/%d/stat" % pid) as f:
            s = f.read()
    except OSError:
        return None
    rest = s[s.rindex(")") + 2:].split()
    return rest[0], int(rest[1]), int(rest[2]), int(rest[3]), rest[19]


# The /proc states of a process that has exited and not yet gone from /proc: 'Z', a zombie whose parent has not
# reaped it, and 'X', dead with its parent's reaping wait under way.
_ENDED_STATES = ("Z", "X")


def _runs_now(st):
    """Whether the _proc() reading `st` is of a process that runs: there is one, and it is in neither ended state."""
    return st is not None and st[0] not in _ENDED_STATES


def _still_running(pid, wait_s=1.0):
    """Whether `pid` still runs once its exit has been waited for, up to wait_s: a ceiling only a process that is left
    pays, far longer than a process SIGKILLed before the call returned takes to exit, and shorter than what the hung
    helpers here have left to sleep, so one the kill missed is still running at the ceiling. On Linux the exit is an
    event, the pidfd turning readable, and /proc/<pid>/stat then says one of three things, each ended because each is
    shown not to run: nothing (reaped); a zombie ('Z': exited, its parent not yet reaping it); or 'X' (dead, its
    parent's reaping wait under way). 'X' is brief but not rare: of reads taken as soon as the pidfd turned readable
    after SIGKILL to a process the user manager reaps, about 2% showed it. Without pidfd_open, os.kill(pid, 0) is
    polled and a pid no process has is ended."""
    if hasattr(os, "pidfd_open"):
        try:
            fd = os.pidfd_open(pid)
        except ProcessLookupError:
            return False
        except OSError:
            fd = None                           # a kernel without pidfd_open: the poll below
        if fd is not None:
            try:
                select.select([fd], [], [], wait_s)
            finally:
                os.close(fd)
            return _runs_now(_proc(pid))
    deadline = time.monotonic() + wait_s
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        if time.monotonic() >= deadline:
            return True
        time.sleep(0.05)


def _recorded(test, pidfile):
    """The (role, pid) lines the helper's processes wrote to `pidfile`, read right after the call. Each one /proc shows
    running is ended when the test ends, by SIGKILL to its pid after /proc/<pid>/stat shows the same start time, so a
    red run leaves nothing behind and a reused pid is never signalled."""
    try:
        recs = [(ln.split()[0], int(ln.split()[1])) for ln in Path(pidfile).read_text().splitlines() if ln.strip()]
    except OSError:
        recs = []
    starts = {pid: st[4] for _role, pid in recs for st in [_proc(pid)] if _runs_now(st)}

    def end_the_left():
        for pid, start in starts.items():
            st = _proc(pid)
            if _runs_now(st) and st[4] == start:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    test.addCleanup(end_the_left)
    return recs


def _left(recs):
    """The recorded processes still running after the exit wait, each with what /proc/<pid>/stat shows of it."""
    return [(role, pid, _proc(pid)) for role, pid in recs if _still_running(pid)]


def _seen_popen():
    """A subprocess.Popen that keeps every instance it makes, so a test reads the run's own Popen after the call (its
    returncode says whether run_helper reaped the shell it started), and the list it keeps them in."""
    seen = []

    class SeenPopen(subprocess.Popen):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            seen.append(self)
    return SeenPopen, seen


# The child process each exit road runs in (_EXIT_ROADS), so that no SIGINT is ever sent, and no KeyboardInterrupt ever
# raised, inside the test's own process. argv: the credentials.py to load, the road, the command, the bound, the file
# the helper's processes write 'role pid' lines to, and how many lines mean the helper is up. The road says what the
# child injects: an exception raised from the run's communicate (during the wait, once the helper is up, or during the
# drain), a SIGINT to its own main thread (once the helper is up, or once the shell has exited, and in either case once
# the main thread waits in the run's communicate, at its selector's first select; or 0.3 s into the drain, from a timer
# the os.killpg spy starts), a KeyboardInterrupt raised from the os.killpg spy (before the signal, or just after it),
# from the fallback p.kill(), from Popen.__enter__ (once the helper is up) or from Popen.__exit__'s wait, or, from the
# os.killpg spy before the signal, a BaseException of the test's own or a PermissionError (with the fallback's os.kill
# of the shell refused as well). A road named sigint-then-... sends the SIGINT as sigint-wait-running does and then
# raises a second KeyboardInterrupt from the os.killpg spy. It keeps the run's Popen and prints what it saw as JSON,
# with the time from the first SIGINT and from the first injected KeyboardInterrupt where the row times from them, and
# with the shell's /proc state read right after the call: the child is the shell's parent, so a shell the call did not
# reap is still there, a zombie or running, and one it reaped is gone.
_EXIT_ROAD_CHILD = r'''
import errno, importlib.util, json, os, select, signal, subprocess, sys, threading, time
if not hasattr(os, "pidfd_open"):
    print(json.dumps({"skip": "no os.pidfd_open"}))
    sys.exit(0)
signal.signal(signal.SIGINT, signal.default_int_handler)
spec = importlib.util.spec_from_file_location("romp_credentials_exit_road_child", sys.argv[1])
cred = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cred)
road, cmd, bound, pids, up = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6])
seen, started, in_select, killpg_calls, sent, refused = [], threading.Event(), threading.Event(), [], [], []
injected = []                  # when the child raises ki-in-enter's or ki-in-exit's first KeyboardInterrupt


class Cut(BaseException):
    pass


class KeyedSelector(subprocess._PopenSelector):
    # The event each SIGINT meant for the run's wait keys on: the main thread inside communicate, at its selector's
    # select. The event is set before the select is made, so a SIGINT sent once it is set lands inside communicate's
    # try, and communicate's own KeyboardInterrupt handler meets it. Keyed on the pids the helper wrote, a SIGINT could
    # land inside Popen() before the block under CPU contention; keyed on an event set when communicate is called, in
    # communicate before its try.
    def select(self, timeout=None):
        if threading.current_thread() is threading.main_thread():
            in_select.set()
        return super().select(timeout)


subprocess._PopenSelector = KeyedSelector


def helper_up():
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if len(open(pids).read().splitlines()) >= up:
                return True
        except OSError:
            pass
        time.sleep(0.01)
    return False


def interrupt():
    sent.append(time.monotonic())
    signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)


class SeenPopen(subprocess.Popen):
    calls = 0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        seen.append(self)
        started.set()

    def __enter__(self):
        if road == "ki-in-enter":
            helper_up()
            injected.append(time.monotonic())
            raise KeyboardInterrupt()
        return super().__enter__()

    def _wait(self, timeout):
        if road == "ki-in-exit" and killpg_calls:
            raise KeyboardInterrupt()
        return super()._wait(timeout)

    def communicate(self, *a, **kw):
        SeenPopen.calls += 1
        if SeenPopen.calls == 1 and road in ("cut-wait", "oserror-wait", "fnf-wait"):
            helper_up()
            raise {"cut-wait": Cut, "oserror-wait": OSError, "fnf-wait": FileNotFoundError}[road]()
        if SeenPopen.calls == 2 and road == "cut-drain":
            raise Cut()
        return super().communicate(*a, **kw)

    def kill(self):
        if road == "ki-fallback":
            raise KeyboardInterrupt()
        return super().kill()


subprocess.Popen = SeenPopen
real_killpg, real_kill = os.killpg, os.kill


def killpg(pgid, sig):
    killpg_calls.append([pgid, int(sig)])
    if road in ("ki-at-kill", "ki-in-exit", "sigint-then-ki-at-kill"):
        if road == "ki-in-exit":
            injected.append(time.monotonic())
        raise KeyboardInterrupt()
    if road == "cut-at-kill":
        raise Cut()
    if road == "refused-kill":
        raise PermissionError(errno.EPERM, "refused by the test")
    r = real_killpg(pgid, sig)
    if road in ("ki-after-kill", "sigint-then-ki-after-kill"):
        raise KeyboardInterrupt()
    if road == "sigint-drain":
        t = threading.Timer(0.3, interrupt)
        t.daemon = True
        t.start()
    return r


def kill(pid, sig):
    if road == "refused-kill" and seen and pid == seen[0].pid:
        refused.append(pid)
        raise PermissionError(errno.EPERM, "refused by the test")
    return real_kill(pid, sig)


os.killpg = killpg
os.kill = kill


def interrupt_once_up_and_in_the_wait():
    if helper_up() and in_select.wait(10):
        interrupt()


def interrupt_once_the_shell_has_exited_and_in_the_wait():
    if not started.wait(10):
        return
    fd = os.pidfd_open(seen[0].pid)
    try:
        if select.select([fd], [], [], 10)[0] and in_select.wait(10):
            interrupt()
    finally:
        os.close(fd)


if road in ("sigint-wait-running", "sigint-then-ki-after-kill", "sigint-then-ki-at-kill"):
    threading.Thread(target=interrupt_once_up_and_in_the_wait, daemon=True).start()
elif road == "sigint-wait-exited":
    threading.Thread(target=interrupt_once_the_shell_has_exited_and_in_the_wait, daemon=True).start()
t0 = time.monotonic()
try:
    outcome = "returned: " + cred.run_helper(cmd, timeout_s=bound)
except KeyboardInterrupt:
    outcome = "KeyboardInterrupt"
except Cut:
    outcome = "Cut"
except cred.CredentialError as e:
    outcome = str(e)
t1 = time.monotonic()
elapsed = t1 - t0
signal.signal(signal.SIGINT, signal.SIG_IGN)       # a SIGINT that comes after the call lands nowhere
p = seen[0] if seen else None
state = None
if p is not None:
    try:
        with open("/proc/%d/stat" % p.pid) as f:
            s = f.read()
        state = s[s.rindex(")") + 2:].split()[0]
    except OSError:
        state = None
print(json.dumps({"outcome": outcome, "elapsed": round(elapsed, 3), "sent": len(sent),
                  "from_sigint": round(t1 - sent[0], 3) if sent else None,
                  "from_injection": round(t1 - injected[0], 3) if injected else None, "killpg": killpg_calls,
                  "kill_refused": len(refused), "shell": p.pid if p else None,
                  "returncode": p.returncode if p else None,
                  "stdout_closed": bool(p and p.stdout is not None and p.stdout.closed), "shell_state": state}))
'''

# The ways out of run_helper once its shell has started, each run in a child process (_EXIT_ROAD_CHILD). A row is: the
# road, the helper's shape (HelperTimeoutEndsTheGroup._exit_shape), the bound, the call's outcome, the number of
# os.killpg calls, the run's returncode, the recorded processes left running, and the window the call's elapsed time
# falls in (None: not checked; a window whose third item is "from the SIGINT" counts from the first SIGINT the child
# sent, one whose third item is "from the injection" from the child's raising the row's first KeyboardInterrupt, and any
# other from the call's start). The rows through ki-at-kill leave the block through Popen.__exit__ and its close
# and wait: on each the run's stdout is closed when the call ends, and the shell is reaped (the returncode set and
# /proc without it) on every one but ki-at-kill, where a KeyboardInterrupt lands before os.killpg: the shell still
# runs there, and the window's floor shows the quarter-second wait for it that Popen.__exit__ makes before the
# interrupt goes on, its ceiling that the wait is bounded (the shell would run for 30 s). After a SIGINT during the
# wait, communicate has spent that quarter second and Popen.__exit__ makes no wait, so the sigint-wait rows find the
# shell reaped by communicate's own wait, by the drain, or, with a holder of stdout outside the group, by the drain's
# p.kill() fallback alone: that row is the fallback's pin. The rows from cut-at-kill on are the roads run_helper's
# docstring names where the close does not happen or the wait is unbounded or absent.
_EXIT_ROADS = (
    # The run finishes: the key, or a CredentialError after it.
    ("finished", "the key", 5, "returned: " + HELPER_OUT, 0, 0, [], None),
    ("finished", "exit 1", 5, "apiKeyHelper failed (non-zero exit)", 0, 1, [], None),
    ("finished", "exit 127", 5, "apiKeyHelper is not on the manager's PATH (exit 127)", 0, 127, [], None),
    ("finished", "two lines", 5, "apiKeyHelper printed an empty or invalid key (one line on stdout, exit 0)", 0, 0, [],
     None),
    ("finished", "not UTF-8", 5, "apiKeyHelper printed bytes that are not a key", 0, 0, [], None),
    # The run is cut: the bound, an exception during the wait (a BaseException of the test's own, which goes on
    # unchanged, and the two OSError words), and an exception during the drain that is not an Exception, which skips
    # the fallback and leaves the reap to Popen.__exit__'s wait.
    ("bound", "a hung tree", 1, "apiKeyHelper timed out after 1 s", 1, -signal.SIGKILL, [], (1.0, 2.0)),
    ("cut-wait", "a hung tree", 5, "Cut", 1, -signal.SIGKILL, [], None),
    ("oserror-wait", "a hung tree", 5, "apiKeyHelper could not be run", 1, -signal.SIGKILL, [], None),
    ("fnf-wait", "a hung tree", 5, "apiKeyHelper could not run: /bin/sh is not available", 1, -signal.SIGKILL, [],
     None),
    ("cut-drain", "a hung tree", 1, "Cut", 1, -signal.SIGKILL, [], (1.0, 2.0)),
    # A KeyboardInterrupt: during the wait with the shell running (the group is ended; with a holder of stdout outside
    # the group the drain runs out 2 s on, communicate's quarter second before it, and the p.kill() fallback is the
    # shell's only reap) or exited (communicate reaps it, no group is signalled and the sleep runs on, as with
    # subprocess.run before), during the drain, just after os.killpg, during the fallback, and before os.killpg.
    ("sigint-wait-running", "a hung tree", 10, "KeyboardInterrupt", 1, -signal.SIGKILL, [], (0.0, 3.0)),
    ("sigint-wait-running", "a holder of stdout outside the group", 10, "KeyboardInterrupt", 1, -signal.SIGKILL,
     ["holder"], (2.2, 3.0, "from the SIGINT")),
    ("sigint-wait-exited", "a shell that exited, its sleep holding stdout", 10, "KeyboardInterrupt", 0, 0, ["sleep"],
     (0.0, 3.0)),
    ("sigint-drain", "a holder of stdout outside the group", 1, "KeyboardInterrupt", 1, -signal.SIGKILL, ["holder"],
     (1.2, 2.5)),
    ("ki-after-kill", "a hung tree", 1, "KeyboardInterrupt", 1, -signal.SIGKILL, [], (1.0, 2.0)),
    ("ki-fallback", "a holder of stdout outside the group", 1, "KeyboardInterrupt", 1, -signal.SIGKILL, ["holder"],
     (2.9, 4.0)),
    ("ki-at-kill", "a hung lone shell", 1, "KeyboardInterrupt", 1, None, ["shell"], (1.2, 2.5)),
    # A kill that never signals the running shell: an exception other than KeyboardInterrupt raised from os.killpg
    # before it signals, or os.killpg and the fallback's os.kill of the shell both refused. Popen.__exit__'s wait has
    # no bound there and lasts until the shell exits on its own, 4 s in, past the bound and the drain (1 s and 2 s).
    ("cut-at-kill", "a lone shell that ends after 4 s", 1, "Cut", 1, 0, [], (3.9, 5.0)),
    ("refused-kill", "a lone shell that ends after 4 s", 1, "apiKeyHelper timed out after 1 s", 1, 0, [], (3.9, 5.0)),
    # A KeyboardInterrupt that gets no wait for the shell. One raised from Popen.__enter__, after the shell has started
    # and before the block is entered, never reaches Popen.__exit__: the pipe stays open and the shell runs on. One
    # raised from Popen.__exit__'s quarter-second wait (after a first raised from os.killpg before the signal) ends
    # that wait, and the shell runs on. And after a SIGINT in communicate while the shell runs has spent the quarter
    # second, a second one just after os.killpg leaves the shell it signalled unreaped, and one before os.killpg leaves
    # the shell running; the window shows that nothing waits after communicate's quarter second. The first two rows time
    # from the event each measures, the KeyboardInterrupt raised from Popen.__enter__ and the one raised from os.killpg
    # (when the bound has fired), so the spawn and a late wake past the bound stay out of the window, and a
    # quarter-second wait after the injection would still read past the ceiling.
    ("ki-in-enter", "a hung lone shell", 5, "KeyboardInterrupt", 0, None, ["shell"], (0.0, 0.25, "from the injection")),
    ("ki-in-exit", "a hung lone shell", 1, "KeyboardInterrupt", 1, None, ["shell"], (0.0, 0.2, "from the injection")),
    ("sigint-then-ki-after-kill", "a hung tree", 10, "KeyboardInterrupt", 1, None, [], (0.2, 0.45, "from the SIGINT")),
    ("sigint-then-ki-at-kill", "a hung lone shell", 10, "KeyboardInterrupt", 1, None, ["shell"],
     (0.2, 0.45, "from the SIGINT")),
)


class _Settings(unittest.TestCase):
    """A temp cwd with its own .claude/, a temp CLAUDE_CONFIG_DIR, a temp managed file: every settings file
    Claude Code reads, all synthetic, none of them real."""

    def setUp(self):
        self.cwd = tempfile.mkdtemp()
        self.cfg = tempfile.mkdtemp()
        self._cfg_before = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = self.cfg
        self.managed = os.path.join(tempfile.mkdtemp(), "managed-settings.json")
        self._managed_before = cred.managed_settings_path
        cred.managed_settings_path = lambda: self.managed
        cred.forget_helper_key()
        self._mtimes = {}

    def tearDown(self):
        cred.managed_settings_path = self._managed_before
        cred.forget_helper_key()
        if self._cfg_before is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = self._cfg_before

    def _write(self, which, d):
        p = {"managed": self.managed,
             "local": os.path.join(self.cwd, ".claude", "settings.local.json"),
             "project": os.path.join(self.cwd, ".claude", "settings.json"),
             "user": os.path.join(self.cfg, "settings.json")}[which]
        os.makedirs(os.path.dirname(p), exist_ok=True)
        Path(p).write_text(json.dumps(d) if not isinstance(d, str) else d)
        # The settings memo keys on the file's stat, and two writes of one path within one clock tick at the
        # same byte length would be one identity to it. No person edits that fast; a test does (the failure
        # loop below rewrites h0.sh..h3.sh), so every write here gets an mtime strictly after the last one's.
        t = max(os.stat(p).st_mtime_ns, self._mtimes.get(p, 0) + 1)
        os.utime(p, ns=(t, t))
        self._mtimes[p] = t
        return p


class SettingsPrecedence(_Settings):
    def test_the_files_and_their_order_are_claude_codes(self):
        files = cred.settings_files(self.cwd)
        self.assertEqual(files, [self.managed,
                                 os.path.join(os.path.realpath(self.cwd), ".claude", "settings.local.json"),
                                 os.path.join(os.path.realpath(self.cwd), ".claude", "settings.json"),
                                 os.path.join(self.cfg, "settings.json")])

    def test_no_file_defines_the_helper(self):
        self.assertIsNone(cred.api_key_helper(self.cwd))
        self.assertFalse(cred.key_available())
        self.assertEqual(cred.helper_key(), "", "no helper: an empty answer, and the caller says so")

    def test_the_user_file_defines_it_and_each_higher_layer_overrides(self):
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/u/helper.sh")
        self._write("project", {"apiKeyHelper": "/p/helper.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/p/helper.sh")
        self._write("local", {"apiKeyHelper": "/l/helper.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/l/helper.sh")
        self._write("managed", {"apiKeyHelper": "/m/helper.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/m/helper.sh")
        self.assertTrue(cred.key_available())

    def test_an_empty_string_disables_and_a_null_falls_through(self):
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self._write("local", {"apiKeyHelper": ""})
        self.assertEqual(cred.api_key_helper(self.cwd), "", "the CLI's disable value, the one a login launch writes")
        self.assertTrue(cred.key_available(), "the box's key side is the operator's helper, whatever a project says")
        self.assertTrue(cred.project_helper_differs(self.cwd), "and that project would resolve differently")
        self._write("local", {"apiKeyHelper": None})
        self.assertEqual(cred.api_key_helper(self.cwd), "/u/helper.sh", "null is not defined here: the CLI reads on")
        self.assertFalse(cred.project_helper_differs(self.cwd))

    def test_helper_source_names_the_operator_file_that_defines_it(self):
        self.assertIsNone(cred.helper_source())
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual(cred.helper_source(), "user")
        self._write("managed", {"apiKeyHelper": "/m/helper.sh"})
        self.assertEqual(cred.helper_source(), "managed", "managed outranks user, and no per-session layer can disable it")
        self._write("managed", {"apiKeyHelper": ""})
        self.assertIsNone(cred.helper_source(), "a managed disable is no helper at all")
        self._write("project", {"apiKeyHelper": "/p/helper.sh"})
        self.assertIsNone(cred.helper_source(), "a project's helper is not the operator's")
        self.assertEqual(cred.settings_files("/nonexistent/one", operator_only=True),
                         cred.settings_files("/nonexistent/two", operator_only=True), "cwd-independent")

    def test_the_kernel_acts_only_on_the_operators_helper(self):
        """The kernel reads a project's settings to know what the CLI will do, but never RUNS a helper a
        repository checked in (review 2026-09-08): its own calls use the managed or user helper only."""
        proj_script, proj_marker = _helper_script(tempfile.mkdtemp(), out="synthetic-project-output")
        self._write("project", {"apiKeyHelper": proj_script})
        self.assertEqual(cred.api_key_helper(self.cwd), proj_script, "the CLI would run it for that project")
        self.assertFalse(cred.key_available(), "but it is not the box's key side")
        self.assertEqual(cred.helper_key(), "", "and the kernel does not run it")
        self.assertEqual(_runs(proj_marker), 0)
        self.assertEqual(cred.settings_files(self.cwd, operator_only=True),
                         [self.managed, os.path.join(self.cfg, "settings.json")])
        user_script, user_marker = _helper_script(tempfile.mkdtemp(), out="synthetic-user-output")
        self._write("user", {"apiKeyHelper": user_script})
        self.assertEqual(cred.helper_key(), "synthetic-user-output", "the operator's helper is the one that runs")
        self.assertEqual((_runs(user_marker), _runs(proj_marker)), (1, 0))
        self.assertTrue(cred.project_helper_differs(self.cwd))

    def test_a_file_without_the_key_is_skipped_and_a_broken_file_is_loud(self):
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self._write("project", {"permissions": {}})
        self.assertEqual(cred.api_key_helper(self.cwd), "/u/helper.sh")
        p = self._write("local", "{not json")
        with self.assertRaisesRegex(cred.CredentialError, "not valid JSON") as cm:
            cred.api_key_helper(self.cwd)
        self.assertIn(p, str(cm.exception), "the path, so the user can fix the file")


class SettingsReadCache(_Settings):
    """helper_source and api_key_helper run per push from the kernel's pusher thread and per auth check from the
    SDK backend; before the memo each call opened and parsed the user and the managed file (~57 opens a second
    of each, measured on a live box). The memo is keyed on the file's stat, so a change is still seen at once,
    an absent file is still None, and a broken file is still loud on every call."""

    def _opens(self, path, fn, n):
        """How many times n calls of fn() open `path`: the module's open, wrapped and counted."""
        real_open, count = open, [0]

        def counting_open(file, *a, **kw):
            if os.fspath(file) == path:
                count[0] += 1
            return real_open(file, *a, **kw)
        with patch.object(cred, "open", counting_open, create=True):
            out = [fn() for _ in range(n)]
        return count[0], out

    def test_repeated_reads_of_an_unchanged_file_open_it_once(self):
        p = self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        opens, out = self._opens(p, cred.helper_source, 20)
        self.assertEqual(out, ["user"] * 20)
        self.assertEqual(opens, 1, "one parse, then a stat per call: the pusher thread asks tens of times a second")
        opens, out = self._opens(p, lambda: cred.api_key_helper(self.cwd), 20)
        self.assertEqual((opens, out), (0, ["/u/helper.sh"] * 20), "every reader shares the one parse")

    def test_a_changed_file_is_seen_at_the_next_call(self):
        p = self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/u/helper.sh")
        # the same byte length on purpose: only the mtime tells the two apart (_write sets it strictly later,
        # so the test does not ride the clock's grain)
        self._write("user", {"apiKeyHelper": "/u/second.sh"})
        self.assertEqual(cred.api_key_helper(self.cwd), "/u/second.sh", "hot reload: a changed helper counts at once")
        opens, out = self._opens(p, lambda: cred.api_key_helper(self.cwd), 20)
        self.assertEqual((opens, out), (0, ["/u/second.sh"] * 20), "and the new parse is the one memoized")
        self._write("user", {"permissions": {}})
        self.assertIsNone(cred.helper_source(), "a helper removed from the file is gone at the next call")

    def test_an_absent_managed_file_stays_none_and_a_created_one_is_seen(self):
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual([cred.helper_source() for _ in range(3)], ["user"] * 3)
        self._write("managed", {"apiKeyHelper": "/m/helper.sh"})
        self.assertEqual(cred.helper_source(), "managed", "a file that appears counts at the next call")
        os.remove(self.managed)
        self.assertEqual(cred.helper_source(), "user", "and one removed is gone at the next call")
        self._write("managed", {"apiKeyHelper": "/m/helper.sh"})
        self.assertEqual(cred.helper_source(), "managed", "back again: no stale absence memoized either")

    def test_a_broken_file_is_loud_on_every_call_and_never_memoized(self):
        p = self._write("user", "{not json")
        with self.assertRaisesRegex(cred.CredentialError, "not valid JSON"):
            cred.helper_source()
        opens, _ = self._opens(p, lambda: self.assertRaises(cred.CredentialError, cred.helper_source), 3)
        self.assertEqual(opens, 3, "nothing loud is memoized: each call reads the file and refuses again")
        os.remove(p)
        os.makedirs(p)                    # a directory where the file should be: not readable as a file
        for _ in range(3):
            with self.assertRaisesRegex(cred.CredentialError, "cannot be read"):
                cred.helper_source()
        os.rmdir(p)
        self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual(cred.helper_source(), "user", "fixed: read again at the next call")

    def test_a_file_made_unreadable_is_loud_at_the_next_call(self):
        """A chmod leaves mtime and size alone; the memo keys on ctime too, so the loud path is taken rather than
        the old parse served."""
        if os.geteuid() == 0:
            self.skipTest("root reads a mode-000 file")
        p = self._write("user", {"apiKeyHelper": "/u/helper.sh"})
        self.assertEqual(cred.helper_source(), "user")
        # Kernels before multigrain timestamps (Linux 6.13) stamp ctime with the coarse tick, so a chmod a few
        # microseconds after the write lands on the write's tick and IS the memo's identity still (the old parse
        # served, no CredentialError). Move the ctime first, forced until the clock ticked (fs_clock), so the
        # mode-000 stat below is one the memo has not seen: the event, not the clock's grain.
        move_ctime(p)
        os.chmod(p, 0)
        try:
            with self.assertRaisesRegex(cred.CredentialError, "cannot be read"):
                cred.helper_source()
        finally:
            os.chmod(p, 0o644)     # a memo hit here serves the correct old parse anyway: no wait needed
        self.assertEqual(cred.helper_source(), "user", "readable again: read again")


class HelperRun(_Settings):
    def test_the_helper_runs_once_per_ttl_and_the_value_stays_in_memory(self):
        script, marker = _helper_script(tempfile.mkdtemp())
        self._write("user", {"apiKeyHelper": script})
        self.assertEqual(cred.helper_key(now=1000.0), HELPER_OUT)
        self.assertEqual(cred.helper_key(now=1000.0 + 299.0), HELPER_OUT)
        self.assertEqual(_runs(marker), 1, "within the TTL the memo answers")
        self.assertEqual(cred.helper_key(now=1000.0 + 301.0), HELPER_OUT)
        self.assertEqual(_runs(marker), 2, "past the TTL (five minutes by default) the helper runs again")
        cred.forget_helper_key()
        cred.helper_key(now=1000.0 + 302.0)
        self.assertEqual(_runs(marker), 3)

    def test_the_value_is_held_only_within_the_ttl(self):
        """romp holds no key material beyond what one call needs (the user): the memo clears at expiry on its
        own, a failed re-run leaves nothing behind, and a helper removed from the settings takes its value."""
        script, marker = _helper_script(tempfile.mkdtemp())
        self._write("user", {"apiKeyHelper": script})
        with patch.dict(os.environ, {"CLAUDE_CODE_API_KEY_HELPER_TTL_MS": "150"}):
            self.assertEqual(cred.helper_key(), HELPER_OUT)
            self.assertEqual(cred._HELPER_MEMO["value"], HELPER_OUT, "held within the TTL")
            time.sleep(0.5)
            self.assertEqual(cred._HELPER_MEMO["value"], "", "cleared at expiry with nobody asking")
        self.assertEqual(cred.helper_key(now=0.0), HELPER_OUT)
        script2, _ = _helper_script(tempfile.mkdtemp(), "h.sh", body="#!/bin/sh\nexit 1\n")
        self._write("user", {"apiKeyHelper": script2})
        with self.assertRaises(cred.CredentialError):
            cred.helper_key(now=1.0)
        self.assertEqual(cred._HELPER_MEMO["value"], "", "a failed run leaves no value behind")
        self._write("user", {"apiKeyHelper": script})
        self.assertEqual(cred.helper_key(now=2.0), HELPER_OUT)
        self._write("user", {"permissions": {}})
        self.assertEqual(cred.helper_key(now=3.0), "", "the helper is gone")
        self.assertEqual(cred._HELPER_MEMO["value"], "", "and so is its value")

    def test_the_ttl_is_the_clis_variable_in_milliseconds(self):
        script, marker = _helper_script(tempfile.mkdtemp())
        self._write("user", {"apiKeyHelper": script})
        with patch.dict(os.environ, {"CLAUDE_CODE_API_KEY_HELPER_TTL_MS": "1000"}):
            cred.helper_key(now=0.0)
            cred.helper_key(now=0.9)
            self.assertEqual(_runs(marker), 1)
            cred.helper_key(now=1.1)
            self.assertEqual(_runs(marker), 2)

    def test_a_changed_helper_runs_at_once(self):
        d = tempfile.mkdtemp()
        s1, m1 = _helper_script(d, "one.sh", "synthetic-one")
        s2, m2 = _helper_script(d, "two.sh", "synthetic-two")
        self._write("user", {"apiKeyHelper": s1})
        self.assertEqual(cred.helper_key(now=0.0), "synthetic-one")
        self._write("user", {"apiKeyHelper": s2})
        self.assertEqual(cred.helper_key(now=1.0), "synthetic-two", "the memo is keyed on the command")

    def test_the_helper_never_sees_the_kernels_environment(self):
        d = tempfile.mkdtemp()
        script, _ = _helper_script(d, body="#!/bin/sh\necho \"x${ROMP_SERVE_TOKEN}${ROMP_SECRET_PROBE}\"\n")
        self._write("user", {"apiKeyHelper": script})
        with patch.dict(os.environ, {"ROMP_SECRET_PROBE": "leaked"}):
            self.assertEqual(cred.helper_key(), "x", "a whitelist: PATH, HOME, the config dir and the like")

    def test_failures_are_static_words(self):
        d = tempfile.mkdtemp()
        cases = [("#!/bin/sh\nexit 1\n", "failed \\(non-zero exit\\)"),
                 ("#!/bin/sh\nexit 0\n", "empty or invalid key"),
                 ("#!/bin/sh\necho a\necho b\n", "empty or invalid key"),
                 ("#!/bin/sh\nexec no-such-command-romp-test\n", "not on the manager's PATH \\(exit 127\\)")]
        for i, (body, pattern) in enumerate(cases):
            script, _ = _helper_script(d, "h%d.sh" % i, body=body)
            self._write("user", {"apiKeyHelper": script})
            cred.forget_helper_key()
            with self.assertRaisesRegex(cred.CredentialError, pattern):
                cred.helper_key()

    def test_a_timeout_is_a_static_word_too(self):
        # The script records its own pid, and its sleep records the sleep's (an inner sh that writes its pid and then
        # execs the sleep in its place), so the test can tell both are gone: before run_helper killed the helper's
        # process group, the timeout ended the shell that ran the script and left the script and its sleep running.
        d = tempfile.mkdtemp()
        pids = os.path.join(d, "pids")
        script, _ = _helper_script(d, body="#!/bin/sh\necho script $$ >> %s\n"
                                           "/bin/sh -c 'echo sleep $$ >> \"$0\"; exec sleep 5' %s\necho late\n"
                                           % (shlex.quote(pids), shlex.quote(pids)))
        self._write("user", {"apiKeyHelper": script})
        with patch.object(cred, "HELPER_TIMEOUT_S", 1):
            with self.assertRaisesRegex(cred.CredentialError, "timed out"):
                cred.helper_key()
        recs = _recorded(self, pids)
        self.assertEqual(sorted(role for role, _pid in recs), ["script", "sleep"], "both were up before the bound")
        self.assertEqual(_left(recs), [], "the timeout leaves neither the script nor its sleep running")

    def test_a_line_longer_than_the_pipe_buffer_is_read_while_it_is_written(self):
        # A helper that prints more than a pipe holds (65536 bytes by default on Linux) blocks in its write until the
        # reader drains the pipe. run_helper reads while it waits, so the over-long line comes back at once and is
        # refused for what it is; a run that waited for the exit before it read would hang to the bound and then say
        # "timed out" instead. The bound here is small, so such a regression fails in seconds.
        n = 200000
        cmd = " ".join(shlex.quote(a) for a in (sys.executable, "-c", "import sys; sys.stdout.write('x' * %d)" % n))
        t0 = time.monotonic()
        with self.assertRaises(cred.CredentialError) as cm:
            cred.run_helper(cmd, timeout_s=5)
        elapsed = time.monotonic() - t0
        self.assertGreater(n, 65536)
        self.assertEqual(str(cm.exception), "apiKeyHelper printed an empty or invalid key (one line on stdout, exit 0)")
        self.assertLess(elapsed, 2.5, "read while it was written, well within the 5 s bound")


@unittest.skipUnless(os.path.isdir("/proc/self"), "reads the helper's processes from /proc")
class HelperTimeoutEndsTheGroup(_Settings):
    """run_helper starts the helper's shell in a session of its own, and a run the bound cuts ends with SIGKILL to that
    session's process group, then a bounded drain of the pipe that reaps the shell. Before, subprocess.run's timeout
    killed the shell alone, and under dash (Debian's and Ubuntu's /bin/sh, which forks even a lone command) the hung
    command and everything it forked ran on with the helper's environment, one more each time helper_key asked again.
    The helpers are synthetic: each process writes 'role pid' to a temp file, and the test reads /proc for each."""

    def _pids(self):
        return os.path.join(tempfile.mkdtemp(), "pids")

    def _tree_cmd(self, pids):
        """A hung command: the shell forks a child sh, which forks a sleep (the grandchild); every one holds stdout."""
        q = shlex.quote(pids)
        return ("echo shell $$ >> %s; /bin/sh -c 'echo child $$ >> \"$0\"; sleep 30 & echo grandchild $! >> \"$0\"; "
                "wait' %s & wait" % (q, q))

    def test_a_hung_tree_is_ended_whole_within_the_bound_and_its_shell_reaped(self):
        pids = self._pids()
        cmd = self._tree_cmd(pids)
        SeenPopen, seen = _seen_popen()
        t0 = time.monotonic()
        with patch.object(subprocess, "Popen", SeenPopen):
            with self.assertRaises(cred.CredentialError) as cm:
                cred.run_helper(cmd, timeout_s=1)
        elapsed = time.monotonic() - t0
        recs = _recorded(self, pids)
        self.assertEqual(str(cm.exception), "apiKeyHelper timed out after 1 s")
        self.assertLess(elapsed, 1 + 1.0, "the call raises within the bound and a small margin")
        self.assertEqual(sorted(role for role, _pid in recs), ["child", "grandchild", "shell"],
                         "the tree was up before the bound")
        self.assertEqual(_left(recs), [], "no process of the tree is left running")
        mine = [p for p in seen if p.args == cmd]
        self.assertEqual(len(mine), 1, "one Popen for the run")
        self.assertEqual(mine[0].pid, dict((r, p) for r, p in recs)["shell"])
        self.assertEqual(mine[0].returncode, -signal.SIGKILL,
                         "the call reaped the shell it started, ended by the group's SIGKILL")

    def test_the_helper_runs_in_a_session_and_process_group_of_its_own(self):
        # the shell reads its own /proc/self/stat (fields 1, 5 and 6: pid, process group, session) and prints them as
        # the key; a run in the kernel's session, or in a group of its own inside it, is red here
        out = cred.run_helper('read -r s < /proc/self/stat; set -- $s; echo "$1:$5:$6"', timeout_s=5)
        pid, pgrp, sid = (int(x) for x in out.split(":"))
        self.assertEqual((pgrp, sid), (pid, pid), "the shell leads its own session and its own group")
        self.assertNotEqual(sid, os.getsid(0), "not the caller's session")
        self.assertNotEqual(pgrp, os.getpgrp(), "not the caller's group")

    def test_each_ask_of_a_hung_operator_helper_leaves_no_process(self):
        # helper_key asks again on every call while the helper keeps failing (a failed run is not memoized): three asks,
        # each cut by the bound, each leaving nothing of the run it made
        pids = self._pids()
        q = shlex.quote(pids)
        script, _ = _helper_script(tempfile.mkdtemp(), body="#!/bin/sh\necho script $$ >> %s\nsleep 30 &\n"
                                                             "echo sleep $! >> %s\nwait\n" % (q, q))
        self._write("user", {"apiKeyHelper": script})
        SeenPopen, seen = _seen_popen()
        with patch.object(cred, "HELPER_TIMEOUT_S", 1):
            for ask in range(3):
                t0 = time.monotonic()
                with patch.object(subprocess, "Popen", SeenPopen):
                    with self.assertRaises(cred.CredentialError) as cm:
                        cred.helper_key()
                elapsed = time.monotonic() - t0
                recs = _recorded(self, pids)
                self.assertEqual(str(cm.exception), "apiKeyHelper timed out after 1 s", "ask %d" % ask)
                self.assertLess(elapsed, 1 + 1.0, "ask %d" % ask)
                self.assertEqual(len(recs), 2 * (ask + 1),
                                 "ask %d: the script and its sleep were up before the bound" % ask)
                self.assertEqual(_left(recs), [], "ask %d leaves no process" % ask)
                mine = [p for p in seen if p.args == script]
                self.assertEqual(len(mine), ask + 1)
                self.assertEqual(mine[-1].returncode, -signal.SIGKILL, "ask %d: the shell reaped" % ask)
                self.assertEqual(cred._HELPER_MEMO["value"], "", "a failed run leaves no value behind")

    def test_a_hung_token_command_leaves_no_process(self):
        # the environment road through logins.token_value, handed a copy of the runner kernel/sdk_backend.py and
        # kernel/judge.py hand it (run_helper labelled "the token command" at the module's bound); the next test drives
        # the judges' own caller
        self.assertIs(sb._cred, cred, "the SDK backend's credentials module is this one")
        state = Path(tempfile.mkdtemp())
        pids = self._pids()
        rec = {"id": sb._logins.mint_id(), "label": "Hung", "tokenCmd": self._tree_cmd(pids),
               "addedAt": int(time.time()) - 86400}
        sb._logins.write_record(state, rec)
        t0 = time.monotonic()
        with patch.object(cred, "HELPER_TIMEOUT_S", 1):
            with self.assertRaises(cred.CredentialError) as cm:
                sb._logins.token_value(state, rec["id"], lambda c: sb._cred.run_helper(c, label="the token command"))
        elapsed = time.monotonic() - t0
        recs = _recorded(self, pids)
        self.assertEqual(str(cm.exception), "the token command timed out after 1 s")
        self.assertLess(elapsed, 1 + 1.0)
        self.assertEqual(sorted(role for role, _pid in recs), ["child", "grandchild", "shell"],
                         "the tree was up before the bound")
        self.assertEqual(_left(recs), [], "no process of the token command is left running")

    def test_a_hung_token_command_through_the_judges_caller_leaves_no_process(self):
        # The judges' own road, executed: a judge call billed to a stored login ('login:<id>') runs the record's token
        # command in kernel/judge.py's _judge_env, which hands logins.token_value its runner. The record lives under the
        # judge's state root, rebound for this test to a private temp root (jd._rebind_state repoints every directory
        # derived from it; the root's session-hosts file says off, as for any state root a test mints).
        self.assertIs(jd._cred, cred, "the judge's credentials module is this one")
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\n")
        saved = jd.STATE
        jd._rebind_state(root)
        self.addCleanup(jd._rebind_state, saved)
        pids = self._pids()
        rec = {"id": jd._logins.mint_id(), "label": "Hung", "tokenCmd": self._tree_cmd(pids),
               "addedAt": int(time.time()) - 86400}
        jd._logins.write_record(jd.STATE, rec)
        t0 = time.monotonic()
        with patch.object(cred, "HELPER_TIMEOUT_S", 1):
            with self.assertRaises(cred.CredentialError) as cm:
                jd._judge_env("triage", "login:" + rec["id"])
        elapsed = time.monotonic() - t0
        recs = _recorded(self, pids)
        self.assertEqual(str(cm.exception), "the token command timed out after 1 s")
        self.assertLess(elapsed, 1 + 1.0)
        self.assertEqual(sorted(role for role, _pid in recs), ["child", "grandchild", "shell"],
                         "the tree was up before the bound")
        self.assertEqual(_left(recs), [], "no process of the token command is left running")

    def test_a_process_that_left_the_group_holding_stdout_is_not_reached_and_costs_the_drain(self):
        # The stated limit, planted: a process that moves to a session of its own (os.setsid, as a daemonizing helper
        # does) is outside the group the kill reaches, so it runs on; it still holds stdout, so the drain waits its
        # whole bound (HELPER_DRAIN_S) for an end of the pipe that does not come, and the call raises that much later.
        # Unbounded, the drain would wait for this process to exit, 30 s here.
        # Two more clauses of this road are pinned here. When the drain runs out, the shell is still reaped: the group's
        # SIGKILL has already ended it, the p.kill() fallback's poll reaps it first (Popen.send_signal polls before it
        # signals, so nothing is sent), and on this road, the bound, Popen.__exit__'s wait would reap it without the
        # fallback, so the returncode below holds with the fallback removed too. This test is therefore not the
        # fallback's pin: the sigint-wait-running row of _EXIT_ROADS with a holder of stdout outside the group is, since
        # after communicate's quarter second Popen.__exit__ makes no wait. And the run closes its end of the pipe
        # (Popen.__exit__ does), so the escaped process's next write to stdout, made after the call returned (on a
        # SIGUSR1 from the test), fails with EPIPE; with that end left open, the write would land in the pipe's buffer
        # and succeed.
        pids = self._pids()
        wrote = os.path.join(os.path.dirname(pids), "wrote")
        code = ("import errno, os, signal, sys\n"
                "signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGUSR1})\n"
                "os.setsid()\n"
                "open(sys.argv[1], 'a').write('escaped %d\\n' % os.getpid())\n"
                "if signal.sigtimedwait({signal.SIGUSR1}, 30) is not None:\n"
                "    try:\n"
                "        os.write(1, b'late\\n')\n"
                "        r = 'wrote'\n"
                "    except OSError as e:\n"
                "        r = errno.errorcode.get(e.errno, str(e.errno))\n"
                "    open(sys.argv[2], 'w').write(r)\n")
        cmd = "%s & echo shell $$ >> %s; wait" % (
            " ".join(shlex.quote(a) for a in (sys.executable, "-c", code, pids, wrote)), shlex.quote(pids))
        SeenPopen, seen = _seen_popen()
        t0 = time.monotonic()
        with patch.object(subprocess, "Popen", SeenPopen):
            with self.assertRaises(cred.CredentialError) as cm:
                cred.run_helper(cmd, timeout_s=2)
        elapsed = time.monotonic() - t0
        recs = dict((role, pid) for role, pid in _recorded(self, pids))
        self.assertEqual(str(cm.exception), "apiKeyHelper timed out after 2 s")
        self.assertEqual(sorted(recs), ["escaped", "shell"], "both were up before the bound")
        self.assertGreaterEqual(elapsed, 2 + cred.HELPER_DRAIN_S - 0.1, "the drain waited its bound")
        self.assertLess(elapsed, 2 + cred.HELPER_DRAIN_S + 1.0, "and no longer: the drain is bounded")
        self.assertFalse(_still_running(recs["shell"], 0), "the shell was in the group")
        mine = [p for p in seen if p.args == cmd]
        self.assertEqual(len(mine), 1, "one Popen for the run")
        self.assertEqual(mine[0].pid, recs["shell"])
        self.assertEqual(mine[0].returncode, -signal.SIGKILL, "the shell the group's SIGKILL ended is reaped")
        self.assertIsNone(_proc(recs["shell"]), "no zombie of the shell is left")
        st = _proc(recs["escaped"])
        self.assertTrue(_runs_now(st), "the process that left the group runs on: %r" % (st,))
        self.assertEqual((st[2], st[3]), (recs["escaped"], recs["escaped"]), "in a session and a group of its own")
        os.kill(recs["escaped"], signal.SIGUSR1)
        self.assertFalse(_still_running(recs["escaped"], 10), "the escaped process made its write and exited")
        self.assertEqual(Path(wrote).read_text(), "EPIPE", "its write fails: the run closed its end of the pipe")

    def test_the_group_is_signalled_while_its_shell_is_still_unreaped(self):
        # The order that keeps the group's id from reuse: the shell's pid is the group's id, and while the shell is
        # unreaped (running, or a zombie) no new process can take that pid, nor a new group that id, so os.killpg
        # reaches only the helper's group. A spy on os.killpg reads, at the call, the run's returncode and whether /proc
        # still has the shell: (None, True). Two shapes, since each wrong order shows in a different one. A hung lone
        # member (the shell execs a sleep) is red when the shell is reaped first (p.kill() and p.wait() before the
        # kill). A shell that exits at once after starting a holder of stdout in a session of its own leaves the run
        # waiting on the pipe with the shell a zombie at the bound, so a mere poll before the kill reaps it and frees
        # the id: red there, and green in the first shape, where the shell still runs and the poll reaps nothing.
        real_killpg = os.killpg
        holder = ("import os, sys, time; os.setsid(); open(sys.argv[1], 'a').write('holder %d\\n' % os.getpid()); "
                  "time.sleep(30)")
        for shape in ("a hung lone member", "a shell that exited, a holder of stdout outside the group"):
            with self.subTest(shape=shape):
                pids = self._pids()
                if shape == "a hung lone member":
                    bound, roles = 1, ["shell"]
                    cmd = "echo shell $$ >> %s; exec sleep 30" % shlex.quote(pids)
                else:
                    bound, roles = 2, ["holder", "shell"]
                    cmd = "%s & echo shell $$ >> %s" % (
                        " ".join(shlex.quote(a) for a in (sys.executable, "-c", holder, pids)), shlex.quote(pids))
                SeenPopen, seen = _seen_popen()
                at_kill = []

                def spy(pgid, sig, seen=seen, at_kill=at_kill):
                    mine = [p for p in seen if p.pid == pgid]
                    at_kill.append((mine[0].returncode if mine else "not the run's shell",
                                    os.path.exists("/proc/%d" % pgid)))
                    return real_killpg(pgid, sig)
                with patch.object(subprocess, "Popen", SeenPopen), patch.object(os, "killpg", spy):
                    with self.assertRaises(cred.CredentialError) as cm:
                        cred.run_helper(cmd, timeout_s=bound)
                recs = _recorded(self, pids)
                self.assertEqual(str(cm.exception), "apiKeyHelper timed out after %d s" % bound)
                self.assertEqual(sorted(role for role, _pid in recs), roles, "up before the bound")
                self.assertEqual(at_kill, [(None, True)], "at the kill, the shell is unreaped and /proc still has it")

    def _exit_shape(self, shape, pids):
        """One of _EXIT_ROADS' helper shapes: its command, how many 'role pid' lines mean it is up, and its roles."""
        q = shlex.quote(pids)
        holder = ("import os, sys, time; os.setsid(); open(sys.argv[1], 'a').write('holder %d\\n' % os.getpid()); "
                  "time.sleep(30)")
        return {
            "the key": ("echo %s" % HELPER_OUT, 0, []),
            "exit 1": ("exit 1", 0, []),
            "exit 127": ("exec no-such-command-romp-test", 0, []),
            "two lines": ("echo a; echo b", 0, []),
            "not UTF-8": ("printf '\\377\\n'", 0, []),
            "a hung tree": (self._tree_cmd(pids), 3, ["child", "grandchild", "shell"]),
            "a hung lone shell": ("echo shell $$ >> %s; exec sleep 30" % q, 1, ["shell"]),
            "a lone shell that ends after 4 s": ("echo shell $$ >> %s; exec sleep 4" % q, 1, ["shell"]),
            "a shell that exited, its sleep holding stdout": (
                "sleep 30 & echo sleep $! >> %s; echo shell $$ >> %s" % (q, q), 2, ["shell", "sleep"]),
            "a holder of stdout outside the group": (
                "%s & echo shell $$ >> %s; wait" % (
                    " ".join(shlex.quote(a) for a in (sys.executable, "-c", holder, pids)), q), 2, ["holder", "shell"]),
        }[shape]

    # The roads of _EXIT_ROADS each test runs, keyed by the test's name: _check_exit_roads runs the group of the test
    # that calls it, and test_every_road_of_the_exit_road_table_is_run_by_a_test holds the groups to the table, so a row
    # added under a road no group names, or a group naming a road the table lacks, is red there instead of never run.
    _ROAD_GROUPS = {
        "test_every_finished_run_leaves_its_pipe_closed_and_its_shell_reaped": ("finished",),
        "test_every_cut_run_leaves_its_pipe_closed_and_its_shell_reaped": (
            "bound", "cut-wait", "oserror-wait", "fnf-wait", "cut-drain"),
        "test_a_first_keyboard_interrupt_in_the_block_leaves_the_pipe_closed_and_the_reap_attempted": (
            "sigint-wait-running", "sigint-wait-exited", "sigint-drain", "ki-after-kill", "ki-fallback", "ki-at-kill"),
        "test_a_kill_that_never_signals_the_running_shell_leaves_an_unbounded_wait_on_it": (
            "cut-at-kill", "refused-kill"),
        "test_a_keyboard_interrupt_before_the_block_or_a_second_one_leaves_the_shell_not_waited_for": (
            "ki-in-enter", "ki-in-exit", "sigint-then-ki-after-kill", "sigint-then-ki-at-kill"),
    }

    def _check_exit_roads(self):
        """Run each row of _EXIT_ROADS whose road is in the calling test's group (_ROAD_GROUPS) in a child process and
        compare what the call left with the row: the outcome, the pipe closed (open on ki-in-enter alone, which never
        enters the block), the returncode, the shell reaped, the os.killpg calls, the SIGINT sent where the road sends
        one, the fallback's os.kill refused where the road refuses it, the recorded processes left running, and the
        elapsed time's window."""
        roads = self._ROAD_GROUPS[self._testMethodName]
        rows = [row for row in _EXIT_ROADS if row[0] in roads]
        self.assertEqual(sorted({row[0] for row in rows}), sorted(roads), "every road named has its rows")
        for road, shape, bound, outcome, kills, rc, left, window in rows:
            with self.subTest(road=road, shape=shape):
                pids = self._pids()
                cmd, up, roles = self._exit_shape(shape, pids)
                child = [sys.executable, "-c", _EXIT_ROAD_CHILD, os.path.join(ROOT, "kernel", "credentials.py"), road,
                         cmd, str(bound), pids, str(up)]
                r = subprocess.run(child, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=90)
                recs = dict(_recorded(self, pids))
                self.assertEqual(r.returncode, 0, r.stderr[-2000:])
                got = json.loads(r.stdout.strip().splitlines()[-1])
                if "skip" in got:
                    self.skipTest(got["skip"])
                self.assertEqual(sorted(recs), roles, "the helper was up before the call ended")
                t = {("from the SIGINT",): got["from_sigint"], ("from the injection",): got.get("from_injection"),
                     (): got["elapsed"]}[tuple(window[2:])] if window is not None else None
                seen = {"outcome": got["outcome"],
                        "stdout closed": got["stdout_closed"],
                        "returncode": got["returncode"],
                        "the shell reaped": got["shell_state"] is None,
                        "the run's shell is the recorded one": got["shell"] == recs.get("shell", got["shell"]),
                        "os.killpg calls": len(got["killpg"]),
                        "SIGINT sent": got["sent"],
                        "os.kill refused": got["kill_refused"],
                        "left running": sorted(role for role, pid in recs.items()
                                               if (_runs_now(_proc(pid)) if role in left else _still_running(pid))),
                        "elapsed in its window": window is None or (t is not None and window[0] <= t < window[1])}
                want = {"outcome": outcome,
                        "stdout closed": road != "ki-in-enter",
                        "returncode": rc,
                        "the shell reaped": rc is not None,
                        "the run's shell is the recorded one": True,
                        "os.killpg calls": kills,
                        "SIGINT sent": 1 if road.startswith("sigint-") else 0,
                        "os.kill refused": 1 if road == "refused-kill" else 0,
                        "left running": sorted(left),
                        "elapsed in its window": True}
                self.assertEqual(seen, want, json.dumps(got))

    # The rows of _EXIT_ROADS through ki-at-kill, in three tests by kind: each way out of the run's block they drive
    # closes the run's stdout and attempts the shell's reap, as subprocess.run's Popen.__exit__ did: run_helper runs
    # inside the Popen's own context manager, whose __exit__ closes the pipe and reaps the shell, the wait bounded by a
    # quarter second on KeyboardInterrupt. Among the KeyboardInterrupt roads: the bound fires, a holder outside the
    # group keeps the drain waiting, and SIGINT lands during the drain (with the close after the kill, in the same
    # finally, the interrupt went on out of the kill and left the pipe open); a SIGINT during the wait with the shell
    # running and a holder outside the group, where the drain runs out and Popen.__exit__ makes no wait, so the
    # p.kill() fallback is the shell's only reap (red with the fallback removed: the shell left a zombie); and an
    # interrupt that lands before os.killpg, which leaves the shell running and shows the wait for it bounded.
    def test_every_finished_run_leaves_its_pipe_closed_and_its_shell_reaped(self):
        self._check_exit_roads()

    def test_every_cut_run_leaves_its_pipe_closed_and_its_shell_reaped(self):
        self._check_exit_roads()

    def test_a_first_keyboard_interrupt_in_the_block_leaves_the_pipe_closed_and_the_reap_attempted(self):
        self._check_exit_roads()

    # The roads run_helper's docstring states as limits of that property, the rows of _EXIT_ROADS from cut-at-kill on,
    # in two tests. Where the kill never signals the running shell (an exception other than KeyboardInterrupt from
    # os.killpg before the signal, or os.killpg and the fallback's os.kill both refused), Popen.__exit__'s wait has no
    # bound and the call ends only when the shell does. A KeyboardInterrupt gets no wait for the shell when it lands
    # before the block is entered (the pipe stays open too), inside Popen.__exit__'s quarter-second wait, or after a
    # first one in communicate has spent that quarter second.
    def test_a_kill_that_never_signals_the_running_shell_leaves_an_unbounded_wait_on_it(self):
        self._check_exit_roads()

    def test_a_keyboard_interrupt_before_the_block_or_a_second_one_leaves_the_shell_not_waited_for(self):
        self._check_exit_roads()

    def test_every_road_of_the_exit_road_table_is_run_by_a_test(self):
        # The reverse of the check _check_exit_roads makes (every road a test names has rows): every road of _EXIT_ROADS
        # is in the group of a test, by set equality, no road is in two groups, and each test a group is keyed by calls
        # _check_exit_roads, run here with _check_exit_roads replaced by a recorder.
        named = [road for roads in self._ROAD_GROUPS.values() for road in roads]
        self.assertEqual(sorted(set(named)), sorted(named), "no road is in two groups")
        self.assertEqual(sorted({row[0] for row in _EXIT_ROADS}), sorted(named),
                         "the roads of _EXIT_ROADS are the roads the groups name")
        called = []

        def record(case):
            called.append(case._testMethodName)
        with patch.object(HelperTimeoutEndsTheGroup, "_check_exit_roads", record):
            for name in self._ROAD_GROUPS:
                getattr(HelperTimeoutEndsTheGroup(name), name)()
        self.assertEqual(called, list(self._ROAD_GROUPS), "each test a group is keyed by runs its group")

    def test_a_daemonizing_helper_is_not_reached_and_costs_nothing(self):
        # The stated limit's other face, planted: a helper that daemonizes (forks twice, takes a session of its own and
        # points its stdio at /dev/null) leaves the group and holds no stdout, so the kill does not reach it and the
        # drain does not wait for it: the call raises at the bound and the daemon runs on. The sleep the shell forks
        # after it stays in the group and is ended.
        pids = self._pids()
        code = ("import os, sys, time\nif os.fork(): os._exit(0)\nos.setsid()\nif os.fork(): os._exit(0)\n"
                "n = os.open(os.devnull, os.O_RDWR)\nfor k in (0, 1, 2): os.dup2(n, k)\n"
                "open(sys.argv[1], 'a').write('daemon %d\\n' % os.getpid())\ntime.sleep(30)\n")
        q = shlex.quote(pids)
        cmd = "%s; echo shell $$ >> %s; sleep 30 & echo sleep $! >> %s; wait" % (
            " ".join(shlex.quote(a) for a in (sys.executable, "-c", code, pids)), q, q)
        t0 = time.monotonic()
        with self.assertRaises(cred.CredentialError) as cm:
            cred.run_helper(cmd, timeout_s=2)
        elapsed = time.monotonic() - t0
        recs = dict((role, pid) for role, pid in _recorded(self, pids))
        self.assertEqual(str(cm.exception), "apiKeyHelper timed out after 2 s")
        self.assertEqual(sorted(recs), ["daemon", "shell", "sleep"], "all three were up before the bound")
        self.assertLess(elapsed, 2 + 1.0, "the drain had nothing to wait for")
        self.assertFalse(_still_running(recs["shell"], 0), "the shell was in the group")
        self.assertFalse(_still_running(recs["sleep"]), "and so was its sleep")
        st = _proc(recs["daemon"])
        self.assertTrue(_runs_now(st), "the daemon runs on: %r" % (st,))
        self.assertEqual(st[3], st[2], "in a session of its own")
        self.assertNotEqual(st[3], recs["shell"], "not the helper's")

    def test_a_finished_run_kills_nothing(self):
        # The finished roads, planted: a helper that exits, with a key or without one, while a process it started runs
        # on without stdout, leaves that process running, as run_helper always has; only a run that does not finish is
        # killed.
        for tail, outcome in (("echo synthetic-helper-output-2", "synthetic-helper-output-2"),
                              ("exit 1", "apiKeyHelper failed (non-zero exit)")):
            with self.subTest(tail=tail):
                pids = self._pids()
                cmd = "sleep 30 >/dev/null 2>&1 & echo background $! >> %s; %s" % (shlex.quote(pids), tail)
                try:
                    got = cred.run_helper(cmd, timeout_s=5)
                except cred.CredentialError as e:
                    got = str(e)
                recs = _recorded(self, pids)
                self.assertEqual(got, outcome)
                self.assertEqual([role for role, pid in recs if _still_running(pid, 0)], ["background"], "it runs on")


class BootCheck(unittest.TestCase):
    """A retired provider line, the marker, or a key in the kernel's environment stops the kernel; the message
    names files and variables and never a value."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "service.env")

    def _file(self, text):
        Path(self.p).write_text(text)

    def test_a_clean_file_with_the_declaration_starts(self):
        self._file("ROMP_EXPECTED_AUTH=key\nROMP_SERVE_PORT=29855\n# a comment\n")
        cred.check_boot_environment(self.p, environ={})
        cred.check_boot_environment(os.path.join(self.d, "absent.env"), environ={})

    def test_each_retired_line_stops_the_kernel_without_saying_the_value(self):
        for line in ("ROMP_API_KEY_CMD=op read op://vault/item/field",
                     "ROMP_API_KEY_REF=op://vault/item/field",
                     "ANTHROPIC_API_KEY=synthetic-value-never-printed",
                     "export ANTHROPIC_API_KEY='synthetic-value-never-printed'",
                     "ANTHROPIC_API_KEY="):
            self._file("ROMP_EXPECTED_AUTH=key\n%s\n" % line)
            with self.assertRaises(RuntimeError) as cm:
                cred.check_boot_environment(self.p, environ={})
            msg = str(cm.exception)
            self.assertIn(self.p, msg)
            self.assertIn(line.split("=")[0].replace("export ", ""), msg)
            self.assertNotIn("synthetic-value", msg, "names and files, never a value")
            self.assertNotIn("op://", msg)
            self.assertIn("did NOT start", msg)
            self.assertIn("apiKeyHelper", msg)
            self.assertIn("ROMP_EXPECTED_AUTH=key", msg)

    def test_the_1password_names_are_refused_in_the_file_and_the_environment(self):
        """The retired reference kind read the 1Password CLI's token beside it; romp no longer runs op, and a
        token left in service.env would ride into every session and the tmux server (review 2026-09-08)."""
        self._file("ROMP_EXPECTED_AUTH=key\nOP_SERVICE_ACCOUNT_TOKEN=synthetic-value-never-printed\nOP_SESSION_acct=synthetic-2\n")
        with self.assertRaises(RuntimeError) as cm:
            cred.check_boot_environment(self.p, environ={})
        msg = str(cm.exception)
        self.assertIn("OP_SERVICE_ACCOUNT_TOKEN, OP_SESSION_acct", msg)
        self.assertIn("no longer runs op", msg)
        self.assertNotIn("synthetic", msg)
        self._file("ROMP_EXPECTED_AUTH=key\n")
        with self.assertRaises(RuntimeError) as cm:
            cred.check_boot_environment(self.p, environ={"OP_CONNECT_TOKEN": "synthetic-value-never-printed"})
        self.assertIn("the manager's environment carries OP_CONNECT_TOKEN", str(cm.exception))
        cred.check_boot_environment(self.p, environ={"OPENAI_API_KEY": "not ours", "OPTION": "x"})   # the prefix is exact

    def test_the_marker_alone_stops_the_kernel(self):
        self._file("ROMP_EXPECTED_AUTH=key\n")
        Path(self.p + ".source").write_text("command\n")
        with self.assertRaisesRegex(RuntimeError, "retired provider marker"):
            cred.check_boot_environment(self.p, environ={})

    def test_a_retired_name_in_the_kernels_environment_stops_it(self):
        self._file("ROMP_EXPECTED_AUTH=key\n")
        for name in cred.RETIRED_VARS:
            with self.assertRaises(RuntimeError) as cm:
                cred.check_boot_environment(self.p, environ={name: "synthetic-value-never-printed"})
            self.assertIn("the manager's environment carries " + name, str(cm.exception))
            self.assertNotIn("synthetic-value", str(cm.exception))

    def test_an_unreadable_file_is_its_own_loud_failure(self):
        os.makedirs(self.p)          # a directory where the file should be: not readable as a file
        with self.assertRaisesRegex(RuntimeError, "cannot read the service environment file"):
            cred.check_boot_environment(self.p, environ={})

    def test_the_floor_names_cover_every_retired_and_login_name(self):
        for n in ("ROMP_API_KEY_CMD", "ROMP_API_KEY_REF", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                  "CLAUDE_CODE_OAUTH_TOKEN", "ROMP_EXPECTED_AUTH", "OP_SERVICE_ACCOUNT_TOKEN"):
            self.assertIn(n, cred.FLOOR_ENV_NAMES)
        self.assertEqual(cred.FLOOR_ENV_PREFIXES, ("OP_SESSION_",))


class LoginPickSuppressesTheHelper(unittest.TestCase):
    """The per-session settings layer is how a login pick keeps billing the login on a helper box."""

    def test_the_flag_settings_file_carries_the_disable_value_for_a_login_launch(self):
        d = tempfile.mkdtemp()
        p = sb.flag_settings_path(d, SID, no_helper=True)
        self.assertTrue(p, "a login launch always has a settings file")
        self.assertEqual(json.loads(Path(p).read_text()), {"apiKeyHelper": ""})
        self.assertEqual(sb.flag_settings_path(d, SID + "1"), "", "a plain key launch needs no file")
        p2 = sb.flag_settings_path(d, SID + "2", fast=True)
        self.assertNotIn("apiKeyHelper", json.loads(Path(p2).read_text()), "a key launch never disables the helper")

    def test_a_credential_name_in_a_session_env_is_always_refused(self):
        for auth in ("", "login", "key"):
            for name in sb.AUTH_ENV_NAMES:
                err = sb.env_request_error({name: "synthetic"}, auth)
                self.assertIn(name, err)
                self.assertIn("Claude Code's own", err)
        self.assertEqual(sb.env_request_error({"FOO": "bar"}, "key"), "")


class JudgesRunOnClaudeCodesOwnCredential(unittest.TestCase):
    def setUp(self):
        self._login_before = jd._LOGIN_AUTH_ENV_FN
        jd._LOGIN_AUTH_ENV_FN = None
        jd._auth_cache[:] = [None, {}]
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        for p in (jd.JUDGE_AUTH, jd.SDKDIR / (SID + ".json"), jd.STATE / "retry-paused.json"):
            try:
                p.unlink()
            except OSError:
                pass
        self._cfg_before = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
        jd._judge_ctx.paused = False

    def tearDown(self):
        jd._LOGIN_AUTH_ENV_FN = self._login_before
        os.environ["CLAUDE_CONFIG_DIR"] = self._cfg_before

    def _reg(self, auth):
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps({"sid": SID, "auth": auth}))

    def test_a_key_billed_call_injects_nothing_even_with_a_key_in_the_ambient_environment(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "synthetic-ambient", "ANTHROPIC_AUTH_TOKEN": "synthetic-bearer",
                                     "OP_SERVICE_ACCOUNT_TOKEN": "synthetic-op", "OP_SESSION_acct": "synthetic-op2"}):
            env = jd._judge_env("triage", "key")
        for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
                  "OP_SERVICE_ACCOUNT_TOKEN", "OP_SESSION_acct"):
            self.assertNotIn(k, env, k)
        self.assertEqual(env.get("ROMP_SUMMARIZING"), "1", "the rest of the env contract is untouched")

    def test_a_login_billed_call_gets_the_login_tokens_and_the_helper_suppression(self):
        jd._LOGIN_AUTH_ENV_FN = lambda: {"CLAUDE_CODE_OAUTH_TOKEN": "synthetic-login-token"}
        env = jd._judge_env("triage", "login")
        self.assertEqual(env.get("CLAUDE_CODE_OAUTH_TOKEN"), "synthetic-login-token")
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        cmd = jd._judge_cmd("sonnet", "SYS", None, auth="login")
        i = cmd.index("--settings")
        self.assertEqual(json.loads(cmd[i + 1]), {"apiKeyHelper": ""},
                         "the helper outranks the login in the CLI's precedence: disabled for this one call")
        self.assertNotIn("--settings", jd._judge_cmd("sonnet", "SYS", None, auth="key"))
        self.assertNotIn("--settings", jd._judge_cmd("sonnet", "SYS", None))

    def test_the_default_billing_follows_the_helper(self):
        self.assertEqual(jd._judge_auth(SID), "login", "no helper anywhere: the login")
        Path(os.environ["CLAUDE_CONFIG_DIR"], "settings.json").write_text(json.dumps({"apiKeyHelper": "/h.sh"}))
        self.assertEqual(jd._judge_auth(SID), "key", "a helper in Claude Code's settings: the key, read not run")
        self._reg("login")
        jd._auth_cache[:] = [None, {}]
        self.assertEqual(jd._judge_auth(SID), "login", "an explicit pick wins")

    def test_the_first_pass_after_boot_runs_keyless_and_latches_nothing(self):
        """The boot artifact the maintainers saw on 2026-09-08: the first pass after a restart failed 42 calls
        with a remembered-provider error before the second ran clean. There is no remembered anything now."""
        self._reg("key")
        jd._judge_ctx.fsid = SID
        seen = []

        def fake_run(cmd, input=None, env=None, **kw):
            seen.append((cmd, env))
            return SimpleNamespace(stdout=json.dumps({"result": "ok", "usage": {}, "duration_ms": 3}),
                                   stderr="", returncode=0)
        with patch.object(jd, "_judge_engine", return_value="claude"), \
                patch.object(jd.subprocess, "run", side_effect=fake_run):
            out1 = jd._judge_run("sonnet", "SYS", "u", judge="planner", tier="triage")
            out2 = jd._judge_run("sonnet", "SYS", "u", judge="closer", tier="triage")
        self.assertEqual((out1, out2), ("ok", "ok"))
        self.assertEqual(len(seen), 2)
        for cmd, env in seen:
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertNotIn("--settings", cmd, "a key-billed call: the child resolves the helper itself")
        self.assertEqual(jd._auth_down_map(), {}, "the first call after boot is not an auth failure")
        self.assertFalse(jd._judge_ctx.paused)


class KernelSide(unittest.TestCase):
    def setUp(self):
        self._cfg_before = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
        km.jd._cred.forget_helper_key()

    def tearDown(self):
        os.environ["CLAUDE_CONFIG_DIR"] = self._cfg_before
        km.jd._cred.forget_helper_key()

    def test_the_catalog_credential_is_the_helpers_key_or_nothing(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
            self.assertIsNone(km._models_api_credential(), "no helper, no bearer: the refresh serves the cache and says so")
            script, marker = _helper_script(tempfile.mkdtemp())
            Path(os.environ["CLAUDE_CONFIG_DIR"], "settings.json").write_text(json.dumps({"apiKeyHelper": script}))
            self.assertEqual(km._models_api_credential(), ("x-api-key", HELPER_OUT))
            self.assertEqual(_runs(marker), 1)

    def test_main_runs_the_boot_check_before_anything_spawns(self):
        src = inspect.getsource(km.main)
        self.assertIn("jd._cred.check_boot_environment()", src)
        self.assertLess(src.index("jd._cred.check_boot_environment()"), src.index("_ensure_bundles()"))

    def test_the_kernels_env_validator_refuses_a_credential_name_for_every_pick(self):
        fn = km._env_error                      # the kernel-side twin of sdk_backend.env_request_error
        for auth in ("", "login", "key"):
            err = fn({"ANTHROPIC_API_KEY": "synthetic"}, auth)
            self.assertIn("ANTHROPIC_API_KEY", err)
            self.assertEqual(err, sb.env_request_error({"ANTHROPIC_API_KEY": "synthetic"}, auth), "lockstep")

    def test_no_kernel_module_reads_the_retired_provider_module(self):
        for mod in (km, jd, sb):
            self.assertFalse(hasattr(mod, "_keysrc"), mod.__name__)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "kernel", "keysource.py")))


if __name__ == "__main__":
    unittest.main()
