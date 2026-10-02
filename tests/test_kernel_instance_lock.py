#!/usr/bin/env python3
"""The kernel instance lock (2026-10-01): one serving kernel per state root.

A kernel run as __main__ takes an exclusive flock on <state>/kernel.lock right after kernel/kernel.py loads judge.py
(which fixes the state root and creates it), before any import-time write, and holds it until the process exits. The
file's one line names the holder: "<pid> serving", rewritten to "<pid> draining <deadline>" as the first act of
_drain_and_exit. A kernel that finds the lock held waits only for a holder that has announced its drain, bounded by
that deadline; any other holder refuses it with one stderr line and exit 75, having written nothing. The repo-root
record moved from import time into main(), after the bind. An in-process load of the kernel never locks.

The pins, each red on the kernel before the lock for the reason it names:
  1. a serving holder: exit 75 within the bound; stderr names the holder's pid, the lock path and the remedy (a second
     kernel started by hand needs its own state root, ROMP_STATE_DIR);
     both roots keep every path's bytes, mode and mtime and the same set of paths (seeded with files the boot passes
     write, sweep or prune, and serve-token left absent so an import-time mint would show as a new path); no connection
     reached the postal listener; no postal/server.pid;
  2. a draining holder that releases: the waiting line; while the holder holds, the waiting process runs one thread,
     has written nothing and has not taken the lock; once the holder releases, the kernel takes it ("<its pid> serving")
     before the deadline, and then serves, its repo-root record written after the bind, and still runs 2 s after the old
     owner's deadline (a wait that left its timer armed is ended by SIGALRM at that deadline);
  3. a draining holder that keeps the lock past its deadline: exit 75 no earlier than the deadline and less than 5 s
     after it (EXPIRY_SLACK_S), naming the pid, after waiting for it, nothing touched;
  4. a deadline already past when the kernel reads it: refused without waiting;
  5. a pid that is not running in the line (a serving line, a draining line) and an empty file: refused, worded as a
     new owner that has not yet written its line;
  6. in process: the helper's success path over a longer previous line, a non-inheritable descriptor; the drain's
     announcement as the first act of _drain_and_exit, which never raises (a failed one is exactly one line before the
     drain's own); nothing written with no lock held; an in-process load holds no lock; every way out of the wait (the
     lock taken, the deadline reached, a flock that raises) leaves no timer armed and the SIGALRM handler it found in
     place; and each writer of the line (the acquisition over a longer line, the drain's announcement) writes at offset
     0 first and never truncates to 0;
  7. repo-root: an in-process load writes none (read right after this module's load), the one call is main()'s after
     the bind (a source pin; pin 2 executes it);
  8. a kernel still waiting at the drain's deadline names the holder it reads then: with two kernels waiting on a holder
     that releases in time, exactly one serves and the other exits 75 at the deadline naming the kernel that took the
     lock, not the holder that let it go; with the lock still held under the line of a drainer that is gone, the
     refusal is worded as a new owner that has not yet written its line; with the lock passed to a process that
     announced a drain of its own, the refusal names that process as draining until its deadline, not as serving.

Subprocess pins run bin/romp-kernel under sys.executable in a private lab. The environment comes from kernel_env
(tests/test_ship_reship_served.py, the safe lab-kernel recipe: named variables only, the lab's roots, session hosts
floored off, a free kernel port, a postal bus that is never started) with ROMP_STATE_DIR on the lab's state root, no
serve token, and ROMP_POSTAL_PORT on a listener this test owns and counts connections on. Each child leads its own
session, and the group kill plus wait is registered before it is spawned, so every road (pass, fail, the bound) ends
the tree. Pin 8's holder is a plain Python process (sys.executable -I -c, the standard library only) that leads its own
session the same way. All fixtures synthetic."""
import ast
import contextlib
import errno
import fcntl
import json
import os
import re
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
KERNEL = os.path.join(BIN, "romp-kernel")
KERNEL_SRC_PATH = os.path.join(ROOT, "kernel", "kernel.py")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
MODULE_STATE_ROOT = Path(os.environ["XDG_STATE_HOME"]) / "romp"

sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  kernel_env, the lab kernel's environment (the module, not its classes:
#                                   an imported TestCase would be collected here a second time)

km = load_source("romp_kernel_instance_lock", KERNEL)
jd = km.jd
# Read right after the load, before any test runs: the shared judge module's STATE is rebound by every later kernel load
# in this process, and another module's test may write repo-root under whatever root is bound when it runs.
REPO_ROOT_AFTER_LOAD = (MODULE_STATE_ROOT / "repo-root").exists()

EXIT_REFUSED = 75             # the status the spec gives a refused kernel (kernel.py's KERNEL_LOCK_EXIT)
BOUND_S = 30.0                # the most a pin waits for the kernel's verdict: a refusal takes about a second
BOOT_BOUND_S = 120.0          # pin 2's wait for the handed-over kernel to serve: the whole import and boot
RELEASE_DEADLINE_S = 8.0      # pin 2's drain deadline: room for the kernel to reach its lock point on a loaded box (pin 3
#                               relies on 5 s for the same), and short, because pin 2 then waits past it
PAST_DEADLINE_S = 2.0         # how long after the old owner's deadline pin 2 checks the handed-over kernel still runs: a
#                               timer left armed delivers its SIGALRM at the deadline itself
EXPIRY_DEADLINE_S = 5.0       # pin 3's drain deadline: the kernel reaches its lock point (about a second here) well
#                               inside it, so it waits and its timer, not its arrival, decides the refusal
EXPIRY_SLACK_S = 5.0          # pin 3's upper bound: the refusal comes before the deadline plus this (the timer fires at the
#                               deadline, and the refusal is one line and an exit after it)
TWO_WAITERS_DEADLINE_S = 6.0  # pin 8's drain deadline: both kernels reach their lock point (about a second each here)
#                               well inside it, and the one that does not take the lock is refused at it
# Pin 8's holder: takes the lock, writes "<its pid> draining <argv[2]>" as a kernel's drain announcement does, says so on
# stdout, and releases by exiting when its stdin closes. With argv[3] == "fork" a child it forks first keeps the same open
# file, so the lock stays held after the pid the line names has exited. With argv[3] == "handover" the child it forks
# keeps the open file too, and once the holder has exited it announces a drain of its own, "<its pid> draining <argv[4]>",
# and says "announced" on stdout: the lock passed to a process that is draining in turn, without a release between.
HOLDER_SRC = r"""
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

def announce(deadline):
    line = ("%d draining %s\n" % (os.getpid(), deadline)).encode("ascii")
    os.pwrite(fd, line, 0)
    os.ftruncate(fd, len(line))

announce(sys.argv[2])
if sys.argv[3] == "fork" and os.fork() == 0:
    while True:
        time.sleep(3600)
if sys.argv[3] == "handover":
    r, w = os.pipe()
    if os.fork() == 0:
        os.close(w)
        os.read(r, 1)          # end of file once the holder has exited
        announce(sys.argv[4])
        sys.stdout.write("announced\n")
        sys.stdout.flush()
        while True:
            time.sleep(3600)
    os.close(r)
sys.stdout.write("held\n")
sys.stdout.flush()
sys.stdin.read()
"""
WAITING_TEXT = "this kernel waits for its drain until"
HANDOVER_TEXT = "this kernel holds it now"
SERVING_TEXT = "romp-kernel: serving the ported UI at"
# the refusal's remedy: the manager starts no second kernel on one root (bin/romp-manager rootConflict), so the lock keeps
# primaries apart, and the second kernel it can still meet is one started by hand
REMEDY_TEXT = "a second kernel started by hand on this root needs its own state root (set ROMP_STATE_DIR)"
NEW_OWNER_TEXT = "is held by a new owner that has not yet written its line"
PAST_TEXT = "so its drain is past its deadline"


def _snapshot(root):
    """Relative path -> (file type, mode, mtime_ns, bytes or link target) for `root` and everything under it."""
    out = {}

    def one(p):
        st = os.lstat(p)
        if stat.S_ISDIR(st.st_mode):
            body = None
        elif stat.S_ISLNK(st.st_mode):
            body = os.readlink(p)
        else:
            with open(p, "rb") as fh:
                body = fh.read()
        out[os.path.relpath(p, root)] = (stat.S_IFMT(st.st_mode), stat.S_IMODE(st.st_mode), st.st_mtime_ns, body)

    one(root)
    for dp, dns, fns in os.walk(root):
        for n in dns + fns:
            one(os.path.join(dp, n))
    return out


def _snapshot_diff(before, after):
    """The differences between two snapshots, one line each, empty when equal."""
    lines = ["+ %s (new)" % p for p in sorted(set(after) - set(before))]
    lines += ["- %s (gone)" % p for p in sorted(set(before) - set(after))]
    for p in sorted(set(before) & set(after)):
        b, a = before[p], after[p]
        what = [name for name, i in (("type", 0), ("mode", 1), ("mtime", 2), ("bytes", 3)) if b[i] != a[i]]
        if what:
            lines.append("~ %s (%s)" % (p, ", ".join(what)))
    return lines


def _dead_pid():
    """A pid nothing runs under any more: a child that already exited and was reaped."""
    gone = subprocess.Popen(["true"])
    gone.wait()
    return gone.pid


class _Lab(unittest.TestCase):
    """One private lab per test: the state root (xdg/romp), the Claude config dir (claude), a postal listener this test
    owns, and the kernel children, each ended by its group kill registered before the spawn."""
    maxDiff = None

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="kernel-lock-")
        self.addCleanup(shutil.rmtree, self.lab, True)
        self.xdg = os.path.join(self.lab, "xdg")
        self.state = os.path.join(self.xdg, "romp")
        self.claude = os.path.join(self.lab, "claude")
        os.makedirs(self.state)
        os.makedirs(self.claude)
        os.chmod(self.state, 0o700)   # a real root's mode: judge.py's import chmods the root 0700 before the lock point
        self.lock_path = os.path.join(self.state, "kernel.lock")
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(self.listener.close)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(64)
        self.listener.setblocking(False)
        self.port = _lab._free_port()
        self.env = _lab.kernel_env(self.lab, self.claude, os.path.join(self.lab, "dist"), self.port, "unused-token",
                                   ROMP_STATE_DIR=self.state,
                                   ROMP_POSTAL_PORT=str(self.listener.getsockname()[1]))
        # no serve token in the environment: a kernel that minted one at import would leave serve-token as a new path
        self.env.pop("ROMP_SERVE_TOKEN", None)
        self.err = {}

    # the holder: this test process, on a descriptor of its own
    def hold(self, line):
        """Take the lock as its holder and write `line` (newline included, or "" for an empty file); released by
        release() or when the test ends."""
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        self._held = getattr(self, "_held", set())
        self._held.add(fd)
        self.addCleanup(self.release, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.ftruncate(fd, 0)
        os.pwrite(fd, line.encode("ascii"), 0)
        return fd

    def release(self, fd):
        """Close the holder's descriptor once (the release); a second call is a no-op, so the cleanup never closes a
        descriptor number the process has reused since."""
        if fd in self._held:
            self._held.discard(fd)
            os.close(fd)

    def lock_line(self):
        with open(self.lock_path, "rb") as fh:
            return fh.read().split(b"\n", 1)[0].decode("ascii", "replace")

    # the kernel child
    def spawn(self):
        """bin/romp-kernel under sys.executable, leading its own session, stderr on a pipe; its group kill plus wait is
        registered before the spawn."""
        slot = {}

        def end():
            p = slot.get("p")
            if p is None:
                return
            try:
                os.killpg(p.pid, signal.SIGKILL)   # the whole group: the leader and anything it started
            except (ProcessLookupError, PermissionError):
                pass
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass
            if p.stderr is not None:
                p.stderr.close()

        self.addCleanup(end)
        slot["p"] = p = subprocess.Popen([sys.executable, KERNEL], env=self.env, cwd=self.lab, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True)
        self.err[p.pid] = bytearray()
        return p

    def verdict(self, p, bound=BOUND_S):
        """Wait up to `bound` for the child to exit; at the bound kill its group first, then read. (returncode, stderr
        text, the monotonic time the exit was seen, whether the bound killed it)."""
        killed = False
        try:
            _, err = p.communicate(timeout=bound)
        except subprocess.TimeoutExpired:
            killed = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            _, err = p.communicate()
        seen = time.monotonic()
        text = (bytes(self.err.get(p.pid, b"")) + (err or b"")).decode("utf-8", "replace")
        return p.returncode, text, seen, killed

    def read_until(self, p, needle, bound):
        """Read the child's stderr until `needle` appears, the child closes it, or `bound` seconds pass; True when found.
        Everything read is kept in self.err for the messages."""
        buf = self.err[p.pid]
        fd = p.stderr.fileno()
        end = time.monotonic() + bound
        while needle.encode() not in buf:
            left = end - time.monotonic()
            if left <= 0:
                return False
            ready, _, _ = select.select([fd], [], [], left)
            if not ready:
                return False
            chunk = os.read(fd, 65536)
            if not chunk:
                return False
            buf += chunk
        return True

    def stderr_of(self, p):
        return bytes(self.err.get(p.pid, b"")).decode("utf-8", "replace")

    def connections(self):
        """The connections that reached the postal listener (accepted now, so each counts once)."""
        n = 0
        while True:
            try:
                c, _ = self.listener.accept()
            except (BlockingIOError, InterruptedError):
                return n
            c.close()
            n += 1

    def snapshot(self):
        return _snapshot(self.lab)

    def seed(self):
        """Files the boot writes, sweeps or prunes, so a kernel that ran any of it shows in the snapshot: repo-root and
        palette-colors (rewritten at boot), remotes.json (read and re-saved), a checkpoint whose transcript is gone (the
        import-time sweep unlinks it), judge scratch two days old (the boot prune deletes it). serve-token stays absent."""
        Path(self.state, "repo-root").write_text("/nowhere/romp\n")
        Path(self.state, "palette-colors").write_text("#000000\t#ffffff\n")
        Path(self.state, "remotes.json").write_text("{}\n")
        os.makedirs(os.path.join(self.state, "checkpoints"))
        Path(self.state, "checkpoints", "dead.json").write_text(json.dumps({"path": "/nowhere/gone.jsonl"}))
        scratch = os.path.join(self.state, "judge-scratch")
        os.makedirs(scratch)
        proj = os.path.join(self.claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(scratch)))
        os.makedirs(proj)
        old = os.path.join(proj, "11111111-2222-3333-4444-555555555555.jsonl")
        Path(old).write_text("{}\n")
        t = time.time() - 2 * 86400
        os.utime(old, (t, t))
        self.assertFalse(os.path.exists(os.path.join(self.state, "serve-token")))

    def assertNothingWritten(self, before, why):
        self.assertEqual(_snapshot_diff(before, self.snapshot()), [], why)


class SecondKernelIsRefused(_Lab):
    """Pin 1: a live holder that is serving refuses the kernel, which writes nothing."""

    def test_a_serving_holder_refuses_the_kernel_with_exit_75_and_nothing_written(self):
        self.seed()
        self.hold("%d serving\n" % os.getpid())
        before = self.snapshot()
        p = self.spawn()
        code, err, _, killed = self.verdict(p)
        self.assertNothingWritten(before, "the refused kernel changed the roots (killed at the %.0f s bound: %s); its "
                                          "stderr:\n%s" % (BOUND_S, killed, err[-3000:]))
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 within %.0f s (killed at the bound: %s); its "
                                             "stderr:\n%s" % (BOUND_S, killed, err[-3000:]))
        self.assertIn("pid %d" % os.getpid(), err, "the refusal names the holder's pid")
        self.assertIn(self.lock_path, err, "the refusal names the lock's path")
        self.assertIn(REMEDY_TEXT, err, "the refusal names the remedy for a second kernel started by hand")
        self.assertIn("The manager never starts two kernels on one state root", err,
                      "the refusal says the manager is not the road a second kernel took")
        self.assertNotIn("kernels.json", err, "a profile on the primary's root is the manager's to refuse, not this "
                                              "kernel's to explain")
        self.assertIn("this kernel wrote nothing", err)
        self.assertEqual(len([ln for ln in err.splitlines() if ln.startswith("romp-kernel:")]), 1,
                         "one stderr line from the kernel: %r" % err)
        self.assertEqual(self.connections(), 0, "the refused kernel dialled the postal port")
        self.assertFalse(os.path.exists(os.path.join(self.state, "postal", "server.pid")))
        self.assertEqual(self.lock_line(), "%d serving" % os.getpid(), "the holder's line is untouched")


class DrainingHolderIsWaitedFor(_Lab):
    """Pin 2: a holder that announced its drain is waited for, its release hands the lock over, and the kernel that
    took it outlives the old owner's deadline."""

    def test_the_kernel_waits_for_a_draining_holder_and_takes_the_lock_when_it_releases(self):
        deadline = time.time() + RELEASE_DEADLINE_S
        fd = self.hold("%d draining %.3f\n" % (os.getpid(), deadline))
        # a fresh render.js under the lab's ROMP_DIST_DIR: the handed-over kernel finds its bundles current and builds
        # nothing in the checkout (a checkout with the extension's dependencies would otherwise run esbuild there)
        os.makedirs(os.path.join(self.lab, "dist"))
        Path(self.lab, "dist", "render.js").write_text("")
        before = self.snapshot()
        p = self.spawn()
        self.assertTrue(self.read_until(p, WAITING_TEXT, BOUND_S),
                        "no waiting line within %.0f s; stderr:\n%s" % (BOUND_S, self.stderr_of(p)[-3000:]))
        waiting = next(ln for ln in self.stderr_of(p).splitlines() if WAITING_TEXT in ln)
        self.assertIn("pid %d" % os.getpid(), waiting)
        self.assertIn(self.lock_path, waiting)
        self.assertIsNone(p.poll(), "the kernel exited instead of waiting: %r" % self.stderr_of(p))
        if os.path.isdir("/proc/%d/task" % p.pid):
            self.assertEqual(len(os.listdir("/proc/%d/task" % p.pid)), 1,
                             "the waiting kernel runs one thread: its SIGALRM bound interrupts the flock only then")
        self.assertNothingWritten(before, "the waiting kernel wrote under the roots")
        self.assertEqual(self.lock_line(), "%d draining %.3f" % (os.getpid(), deadline),
                         "while the holder holds, the kernel has not taken the lock")
        self.release(fd)                             # the release: the event the kernel waits on
        self.assertTrue(self.read_until(p, HANDOVER_TEXT, BOUND_S),
                        "no handover after the release; stderr:\n%s" % self.stderr_of(p)[-3000:])
        took = time.time()
        self.assertEqual(self.lock_line(), "%d serving" % p.pid, "the kernel holds the lock and says so")
        self.assertLess(took, deadline, "the handover came after the drain's deadline")
        # the rest of the boot, which this pin runs in the plain Python leg: no bundles are needed to serve
        self.assertTrue(self.read_until(p, SERVING_TEXT, BOOT_BOUND_S),
                        "the handed-over kernel never served; stderr:\n%s" % self.stderr_of(p)[-4000:])
        self.assertEqual(Path(self.state, "repo-root").read_text().strip(), os.path.realpath(ROOT),
                         "the repo-root record lands with the bind (pin 7's executed half)")
        self.assertEqual(self.lock_line(), "%d serving" % p.pid)
        # the old owner's deadline passes while the kernel serves: a wait that left its one-shot timer armed delivers
        # SIGALRM at that deadline, and the default handler, back in place, ends the kernel (pin 6's timer half)
        while time.time() < deadline + PAST_DEADLINE_S and p.poll() is None:
            time.sleep(0.2)
        self.assertIsNone(p.poll(), "the handed-over kernel died after the old owner's deadline (returncode %r; -%d is "
                          "SIGALRM); stderr:\n%s" % (p.returncode, signal.SIGALRM, self.stderr_of(p)[-3000:]))


class DrainPastItsDeadline(_Lab):
    """Pins 3 and 4: a drain that outlives its deadline, or a deadline already gone, is refused."""

    def test_a_holder_that_keeps_the_lock_past_its_deadline_is_refused_from_the_deadline_to_5_s_after_it(self):
        deadline = time.time() + EXPIRY_DEADLINE_S
        self.hold("%d draining %.3f\n" % (os.getpid(), deadline))
        before = self.snapshot()
        p = self.spawn()
        code, err, _, killed = self.verdict(p, bound=EXPIRY_DEADLINE_S + BOUND_S)
        exited = time.time()
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertIn(WAITING_TEXT, err, "the kernel did not wait for the drain (one that reached its lock point after "
                                         "the %.0f s deadline refuses at once; its stderr:\n%s)" % (EXPIRY_DEADLINE_S, err))
        self.assertGreaterEqual(exited, deadline, "the kernel gave up before the drain's deadline")
        self.assertLess(exited, deadline + EXPIRY_SLACK_S, "the kernel was refused %.1f s after the drain's deadline, "
                        "past the %.0f s slack" % (exited - deadline, EXPIRY_SLACK_S))
        self.assertIn("pid %d" % os.getpid(), err)
        self.assertIn(PAST_TEXT, err, "the refusal says the drain is past its deadline")
        self.assertIn(REMEDY_TEXT, err)
        self.assertNothingWritten(before, "the refused kernel changed the roots")
        self.assertEqual(self.connections(), 0)

    def test_a_deadline_already_past_is_refused_without_waiting(self):
        self.hold("%d draining %.3f\n" % (os.getpid(), time.time() - 5))
        before = self.snapshot()
        p = self.spawn()
        code, err, _, killed = self.verdict(p)
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertNotIn(WAITING_TEXT, err, "a deadline already past is not waited for")
        self.assertIn("pid %d" % os.getpid(), err)
        self.assertIn("which has passed", err)
        self.assertIn(PAST_TEXT, err)
        self.assertNothingWritten(before, "the refused kernel changed the roots")


class NoOwnerLine(_Lab):
    """Pin 5: a holder whose line names no live owner is a new owner that has not written its line yet."""

    def _refused_as_new_owner(self, line, expect):
        self.hold(line)
        before = self.snapshot()
        p = self.spawn()
        code, err, _, killed = self.verdict(p)
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertIn(NEW_OWNER_TEXT, err)
        self.assertIn(expect, err)
        self.assertIn(self.lock_path, err)
        self.assertIn(REMEDY_TEXT, err)
        self.assertNotIn(WAITING_TEXT, err, "no live owner announced a drain: nothing to wait for")
        self.assertNothingWritten(before, "the refused kernel changed the roots")

    def test_a_serving_line_naming_a_pid_that_is_not_running(self):
        dead = _dead_pid()
        self._refused_as_new_owner("%d serving\n" % dead, "the line still names pid %d, which is not running" % dead)

    def test_a_draining_line_naming_a_pid_that_is_not_running(self):
        dead = _dead_pid()
        self._refused_as_new_owner("%d draining %.3f\n" % (dead, time.time() + 60),
                                   "the line still names pid %d, which is not running" % dead)

    def test_an_empty_file(self):
        self._refused_as_new_owner("", "(the file is empty)")


class TheHolderAtTheDeadline(_Lab):
    """Pin 8: a kernel still waiting when the drain's deadline comes is refused naming the holder it reads then, which
    is the drainer only while the drainer's own line is there and the drainer runs."""

    def holder(self, deadline, fork=False, handover=None):
        """Pin 8's holder (HOLDER_SRC) on this lab's lock with `deadline` in its line, its group kill plus wait registered
        before the spawn; returns once it holds the lock and says so. `handover`: the deadline of the drain its child
        announces once the holder has exited (HOLDER_SRC's handover mode)."""
        slot = {}

        def end():
            h = slot.get("h")
            if h is None:
                return
            try:
                os.killpg(h.pid, signal.SIGKILL)    # the holder and, with fork or handover, the child that keeps the lock
            except (ProcessLookupError, PermissionError):
                pass
            for f in (h.stdin, h.stdout):
                try:
                    f.close()
                except OSError:
                    pass
            try:
                h.wait(timeout=30)
            except subprocess.TimeoutExpired:
                pass

        self.addCleanup(end)
        mode = ["handover", "%.3f" % handover] if handover is not None else ["fork" if fork else "hold"]
        slot["h"] = h = subprocess.Popen(
            [sys.executable, "-I", "-c", HOLDER_SRC, self.lock_path, "%.3f" % deadline] + mode,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")}, cwd=self.lab, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
        ready, _, _ = select.select([h.stdout], [], [], BOUND_S)
        self.assertTrue(ready and h.stdout.readline() == b"held\n", "the holder did not take the lock (exit %r)" % h.poll())
        self.assertEqual(self.lock_line(), "%d draining %.3f" % (h.pid, deadline))
        return h

    def let_go(self, h):
        """The holder's release: its stdin closes, it exits, and it is reaped (a zombie would still read as running)."""
        h.stdin.close()
        h.wait(timeout=BOUND_S)

    def refusal_of(self, err):
        lines = [ln for ln in err.splitlines() if "exits %d" % EXIT_REFUSED in ln]
        self.assertEqual(len(lines), 1, "one refusal line: %r" % err)
        return lines[0]

    def test_of_two_waiting_kernels_the_one_that_does_not_take_the_lock_is_refused_naming_the_one_that_did(self):
        os.makedirs(os.path.join(self.lab, "dist"))        # current bundles, as pin 2: the kernel that takes the lock
        Path(self.lab, "dist", "render.js").write_text("")  # serves without building anything
        deadline = time.time() + TWO_WAITERS_DEADLINE_S
        h = self.holder(deadline)
        a = self.spawn()
        first_env = dict(self.env)
        self.env = dict(self.env, ROMP_KERNEL_PORT=str(_lab._free_port()))   # a port of its own for the second kernel
        b = self.spawn()
        self.env = first_env
        for p in (a, b):
            self.assertTrue(self.read_until(p, WAITING_TEXT, BOUND_S),
                            "kernel %d did not wait; stderr:\n%s" % (p.pid, self.stderr_of(p)[-3000:]))
        self.let_go(h)
        released = time.time()
        winner = None
        end = time.monotonic() + BOUND_S
        while winner is None and time.monotonic() < end:
            winner = next((p for p in (a, b) if self.read_until(p, HANDOVER_TEXT, 0.2)), None)
        self.assertIsNotNone(winner, "neither kernel took the lock after the release; stderr:\n%s\n----\n%s"
                             % (self.stderr_of(a)[-2000:], self.stderr_of(b)[-2000:]))
        loser = b if winner is a else a
        self.assertEqual(self.lock_line(), "%d serving" % winner.pid)
        self.assertLess(released, deadline, "the release came after the deadline: the pin waited too long to release")
        code, err, _, killed = self.verdict(loser, bound=max(0.0, deadline - time.time()) + BOUND_S)
        refused = time.time()
        self.assertEqual(code, EXIT_REFUSED, "the other kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertGreaterEqual(refused, deadline, "the other kernel was refused before the deadline: %s" % err[-2000:])
        self.assertLess(refused, deadline + EXPIRY_SLACK_S, "the other kernel was refused %.1f s after the deadline"
                        % (refused - deadline))
        refusal = self.refusal_of(err)
        self.assertIn("another kernel (pid %d) is serving" % winner.pid, refusal, "the refusal names the kernel that took "
                                                                                   "the lock")
        self.assertIsNone(re.search(r"pid %d\b" % h.pid, refusal), "the refusal names the holder that released: %s"
                          % refusal)
        self.assertNotIn(PAST_TEXT, refusal, "the holder released in time; its drain is not past its deadline")
        self.assertIn(self.lock_path, refusal)
        self.assertIn(REMEDY_TEXT, refusal)
        self.assertNotIn(HANDOVER_TEXT, err)
        self.assertNotIn(SERVING_TEXT, err, "only one kernel serves")
        self.assertTrue(self.read_until(winner, SERVING_TEXT, BOOT_BOUND_S),
                        "the kernel that took the lock never served; stderr:\n%s" % self.stderr_of(winner)[-4000:])
        self.assertIsNone(winner.poll(), "the kernel that took the lock is still serving")
        self.assertEqual(self.lock_line(), "%d serving" % winner.pid)

    def test_a_lock_still_held_under_the_line_of_a_drainer_that_is_gone_is_refused_as_a_new_owner(self):
        # the holder hands its open lock to a child and exits once the kernel waits, so at the deadline the lock is still
        # held under the drainer's own line, naming a pid that is gone: a new owner whose line is not written yet
        deadline = time.time() + EXPIRY_DEADLINE_S
        h = self.holder(deadline, fork=True)
        before = self.snapshot()
        p = self.spawn()
        self.assertTrue(self.read_until(p, WAITING_TEXT, BOUND_S),
                        "the kernel did not wait; stderr:\n%s" % self.stderr_of(p)[-3000:])
        self.let_go(h)
        code, err, _, killed = self.verdict(p, bound=max(0.0, deadline - time.time()) + BOUND_S)
        refused = time.time()
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertGreaterEqual(refused, deadline, "the kernel was refused before the deadline: %s" % err[-2000:])
        self.assertLess(refused, deadline + EXPIRY_SLACK_S)
        refusal = self.refusal_of(err)
        self.assertIn(NEW_OWNER_TEXT, refusal)
        self.assertIn("the line still names pid %d, which is not running" % h.pid, refusal)
        self.assertNotIn(PAST_TEXT, refusal, "the drainer is gone: it did not keep the lock past its deadline")
        self.assertEqual(self.lock_line(), "%d draining %.3f" % (h.pid, deadline), "the kernel wrote no line")
        self.assertNothingWritten(before, "the refused kernel changed the roots")

    def test_a_kernel_that_took_the_lock_and_drains_in_turn_is_named_as_draining_not_serving(self):
        # The lock passes from the drainer the kernel waits on to a process that announces a drain of its own, as a kernel
        # that took the lock after the drainer let go and was then told to stop does. The handover keeps the lock held
        # throughout (the drainer's child inherits its open file), so the waiting kernel cannot take it in between. At the
        # deadline the line read is that process's live draining line, not the drainer's own: the refusal names it as
        # draining until its own deadline, never as serving.
        deadline = time.time() + EXPIRY_DEADLINE_S
        later = deadline + 600.0
        h = self.holder(deadline, handover=later)
        p = self.spawn()
        self.assertTrue(self.read_until(p, WAITING_TEXT, BOUND_S),
                        "the kernel did not wait; stderr:\n%s" % self.stderr_of(p)[-3000:])
        h.stdin.close()                              # the drainer exits, and its child announces its own drain
        ready, _, _ = select.select([h.stdout], [], [], BOUND_S)
        self.assertTrue(ready and h.stdout.readline() == b"announced\n", "the child did not announce its drain")
        h.wait(timeout=BOUND_S)                      # the drainer is gone and reaped
        line = self.lock_line()
        m = re.fullmatch(r"(\d+) draining %s" % re.escape("%.3f" % later), line)
        self.assertIsNotNone(m, "the lock's line is the child's drain: %r" % line)
        drainer = int(m.group(1))
        self.assertNotEqual(drainer, h.pid)
        self.assertLess(time.time(), deadline, "the handover came after the deadline: the pin waited too long")
        before = self.snapshot()
        code, err, _, killed = self.verdict(p, bound=max(0.0, deadline - time.time()) + BOUND_S)
        refused = time.time()
        self.assertEqual(code, EXIT_REFUSED, "the kernel did not exit 75 (killed at the bound: %s); its stderr:\n%s"
                         % (killed, err[-3000:]))
        self.assertGreaterEqual(refused, deadline, "the kernel was refused before the deadline: %s" % err[-2000:])
        self.assertLess(refused, deadline + EXPIRY_SLACK_S)
        refusal = self.refusal_of(err)
        when = datetime.fromtimestamp(later, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertIn("another kernel (pid %d) is draining until %s and holds %s" % (drainer, when, self.lock_path),
                      refusal, "the refusal names the kernel that holds the lock as draining, with its deadline")
        self.assertNotIn("is serving", refusal)
        self.assertNotIn(PAST_TEXT, refusal, "the drainer the kernel waited on let go in time")
        self.assertIsNone(re.search(r"pid %d\b" % h.pid, refusal), "the refusal names the drainer that let go: %s"
                          % refusal)
        self.assertIn(REMEDY_TEXT, refusal)
        self.assertEqual(self.lock_line(), line, "the kernel wrote no line")
        self.assertNothingWritten(before, "the refused kernel changed the roots")


class InProcess(unittest.TestCase):
    """Pin 6 in process: the helper's success path, its refusal to wait with threads running, and no lock held by an
    in-process load. The setUp's check makes each red on a kernel without the lock name that absence."""

    def setUp(self):
        self.assertTrue(hasattr(km, "_kernel_lock_acquire") and hasattr(km, "_KERNEL_LOCK_FD"),
                        "the kernel has no instance lock")
        self.dir = tempfile.mkdtemp(prefix="kernel-lock-inproc-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_the_helper_takes_the_lock_over_a_longer_line_with_a_non_inheritable_descriptor(self):
        path = os.path.join(self.dir, "kernel.lock")
        Path(path).write_text("4242 draining 1759350000.125\nleftover tail of an older writer\n")
        fd, refusal = km._kernel_lock_acquire(Path(path))
        self.addCleanup(os.close, fd)
        self.assertIsNone(refusal)
        self.assertEqual(Path(path).read_text(), "%d serving\n" % os.getpid(), "the whole file is the one line")
        self.assertFalse(os.get_inheritable(fd), "no child the kernel spawns inherits the lock")
        other = os.open(path, os.O_RDWR)
        self.addCleanup(os.close, other)
        with self.assertRaises(BlockingIOError, msg="the lock is held through the returned descriptor"):
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_a_new_lock_file_is_born_owner_only(self):
        path = os.path.join(self.dir, "kernel.lock")
        fd, refusal = km._kernel_lock_acquire(Path(path))
        self.addCleanup(os.close, fd)
        self.assertIsNone(refusal)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode) & 0o077, 0, "the lock file is not readable by others")

    def test_with_threads_running_a_draining_holder_is_refused_rather_than_waited_for(self):
        # the SIGALRM bound needs a single-threaded process (the helper's docstring); with another thread alive the
        # helper refuses at once instead of risking an unbounded wait
        path = os.path.join(self.dir, "kernel.lock")
        held = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, held)
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.pwrite(held, ("%d draining %.3f\n" % (os.getpid(), time.time() + 60)).encode(), 0)
        with mock.patch.object(km.threading, "active_count", return_value=2), \
             mock.patch.object(km, "_kernel_lock_wait", side_effect=AssertionError("waited")):
            fd, refusal = km._kernel_lock_acquire(Path(path))
        self.assertIsNone(fd)
        self.assertIn("already runs 2 threads", refusal)
        self.assertIn("pid %d" % os.getpid(), refusal)

    def test_an_in_process_load_holds_no_lock(self):
        self.assertIsNone(km._KERNEL_LOCK_FD, "only a kernel run as __main__ locks")
        self.assertFalse((MODULE_STATE_ROOT / "kernel.lock").exists(), "the in-process load created no lock file")


class WaitTimer(unittest.TestCase):
    """Pin 6, the wait's timer: every way out of _kernel_lock_wait (the lock taken, the deadline reached, a flock that
    raises) leaves ITIMER_REAL cancelled and the SIGALRM handler it found back in place. A timer left armed delivers
    SIGALRM at the old owner's deadline to the kernel that took the lock and now serves, and the default handler ends
    it; pin 2 runs that kernel past the deadline."""

    def setUp(self):
        self.assertTrue(hasattr(km, "_kernel_lock_wait"), "the kernel has no instance lock")
        self.dir = tempfile.mkdtemp(prefix="kernel-lock-timer-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.fd = os.open(os.path.join(self.dir, "kernel.lock"), os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, self.fd)

    def _wait(self, flock=None):
        """A 30 s wait on this test's free lock, with fcntl.flock replaced by `flock` when one is given: (the wait's
        return, or the exception it raised; the timer and the handler as the wait left them; the handler installed before
        it). The handler installed before the wait is this test's own, so the restore is checked against a handler that
        is not the default; the original handler and a cancelled timer are put back whatever the wait did, so a timer it
        left armed never fires into a later test."""
        def ours(signum, frame):
            pass
        original = signal.signal(signal.SIGALRM, ours)
        try:
            with (mock.patch.object(km.fcntl, "flock", side_effect=flock) if flock is not None
                  else contextlib.nullcontext()):
                try:
                    out = km._kernel_lock_wait(self.fd, 30.0)
                except Exception as e:
                    out = e
            left = signal.getitimer(signal.ITIMER_REAL)
            handler = signal.getsignal(signal.SIGALRM)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, original)
        return out, left, handler, ours

    def assertLeftNothing(self, left, handler, ours):
        self.assertEqual(left, (0.0, 0.0), "the wait left its timer armed: %r" % (left,))
        self.assertIs(handler, ours, "the wait did not put back the SIGALRM handler it found: %r" % (handler,))

    def test_a_wait_that_takes_the_lock_cancels_its_timer_and_restores_the_handler(self):
        out, left, handler, ours = self._wait()
        self.assertIs(out, True, "the free lock is taken: %r" % (out,))
        self.assertLeftNothing(left, handler, ours)

    def test_a_wait_that_reaches_its_deadline_cancels_its_timer_and_restores_the_handler(self):
        # the expiry: SIGALRM raised into the blocking call as the timer's own would be. raise_signal delivers it to this
        # thread and runs the wait's handler before it returns, while the wait's 30 s timer is still armed
        def expire(fd, op):
            signal.raise_signal(signal.SIGALRM)
            raise AssertionError("the wait's SIGALRM handler did not raise out of the flock")
        out, left, handler, ours = self._wait(expire)
        self.assertIs(out, False, "a wait that reached its deadline reads as no lock: %r" % (out,))
        self.assertLeftNothing(left, handler, ours)

    def test_a_flock_that_raises_cancels_the_timer_and_restores_the_handler(self):
        out, left, handler, ours = self._wait(OSError(errno.EIO, "the test's flock error"))
        self.assertIsInstance(out, OSError, "the flock's error propagates: %r" % (out,))
        self.assertEqual(out.errno, errno.EIO)
        self.assertLeftNothing(left, handler, ours)


class LineWriteOrder(unittest.TestCase):
    """Pin 6, the line's rewrites: each writer of the lock's line (the acquisition's serving line, the drain's
    announcement) writes the new line at offset 0 before it truncates, and never truncates the file to 0, so a reader of
    the first line never finds the file empty mid-rewrite (an empty file reads as a new owner, which refuses a kernel
    rather than letting it wait). os.pwrite and os.ftruncate are recorded through mock on km.os, each still doing its
    work."""

    def setUp(self):
        self.assertTrue(hasattr(km, "_kernel_lock_write"), "the kernel has no instance lock")
        self.dir = tempfile.mkdtemp(prefix="kernel-lock-order-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "kernel.lock")

    def _record(self, fn):
        """fn's return and the pwrite and ftruncate calls it made, in order: ("pwrite", fd, offset, data) and
        ("ftruncate", fd, length)."""
        calls = []
        real_pwrite, real_ftruncate = os.pwrite, os.ftruncate

        def pwrite(fd, data, offset):
            calls.append(("pwrite", fd, offset, bytes(data)))
            return real_pwrite(fd, data, offset)

        def ftruncate(fd, length):
            calls.append(("ftruncate", fd, length))
            return real_ftruncate(fd, length)
        with mock.patch.object(km.os, "pwrite", side_effect=pwrite), \
             mock.patch.object(km.os, "ftruncate", side_effect=ftruncate):
            out = fn()
        return out, calls

    def assertWritesBeforeItTruncates(self, calls, fd, line):
        self.assertTrue(calls, "the line was not rewritten")
        self.assertEqual(calls[0][:3], ("pwrite", fd, 0), "the first call writes the new line at offset 0: %r" % calls)
        self.assertEqual(calls[0][3], line.encode("ascii"), "the first write is the whole new line: %r" % calls)
        self.assertNotIn(("ftruncate", fd, 0), calls, "the file was truncated to 0 mid-rewrite: %r" % calls)
        self.assertEqual(Path(self.path).read_text(), line, "the whole file is the new line")

    def test_the_acquisition_writes_its_serving_line_before_it_truncates_a_longer_one(self):
        Path(self.path).write_text("4242 draining 1759350000.125\nleftover tail of an older writer\n")
        (fd, refusal), calls = self._record(lambda: km._kernel_lock_acquire(Path(self.path)))
        self.assertIsNone(refusal)
        self.addCleanup(os.close, fd)
        self.assertWritesBeforeItTruncates(calls, fd, "%d serving\n" % os.getpid())

    def test_the_drain_announcement_writes_its_draining_line_before_it_truncates(self):
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)        # a lock this process holds, as a kernel holds its own
        os.pwrite(fd, ("%d serving\n" % os.getpid()).encode("ascii"), 0)
        with mock.patch.object(km, "_KERNEL_LOCK_FD", fd):
            _, calls = self._record(km._kernel_lock_announce_drain)
        writes = [c for c in calls if c[0] == "pwrite"]
        self.assertTrue(writes, "the drain was not announced: %r" % calls)
        line = writes[0][3].decode("ascii", "replace")
        self.assertRegex(line, r"\A%d draining \d+\.\d{3}\n\Z" % os.getpid())
        self.assertWritesBeforeItTruncates(calls, fd, line)


class RepoRootRecord(unittest.TestCase):
    """Pin 7: the repo-root record is written by main() after the bind, never by an import."""

    def test_an_in_process_load_writes_no_repo_root(self):
        self.assertFalse(REPO_ROOT_AFTER_LOAD, "loading the kernel module wrote repo-root into its state root")

    def test_the_one_repo_root_call_is_mains_after_the_bind(self):
        # A pin on WHERE the call lives: it guards the call staying after the bind in main() and out of module level.
        # The behaviour (the record lands once the kernel serves, and not while it waits) is executed by pin 2,
        # DrainingHolderIsWaitedFor.
        tree = ast.parse(open(KERNEL_SRC_PATH, encoding="utf-8").read())
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_persist_repo_root":
                calls.append(node)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        self.assertEqual([c.lineno for c in calls if not (main.lineno <= c.lineno <= main.end_lineno)], [],
                         "a _persist_repo_root call outside main()")
        self.assertEqual(len(calls), 1, "one call, in main()")
        stmts = [s for s in main.body]
        idx = {}
        for i, s in enumerate(stmts):
            text = ast.unparse(s)
            if "_LoopbackServer(" in text:
                idx.setdefault("bind", i)
            if text.startswith("_persist_serve_port("):
                idx.setdefault("port", i)
            if text == "_persist_repo_root()":
                idx.setdefault("repo", i)
        self.assertEqual(sorted(idx), ["bind", "port", "repo"], "main() binds, records the port, records the repo root")
        self.assertLess(idx["bind"], idx["repo"], "the repo-root record follows the bind")
        self.assertEqual(idx["repo"], idx["port"] + 1, "beside the serve-port record")


class DrainAnnouncement(unittest.TestCase):
    """Pin 6, the drain half: _drain_and_exit's first act rewrites the held lock's line to draining, it never raises,
    and with no lock held it writes nothing. The handler runs in process as tests/test_restart_cuts.py's _fire runs it:
    no backend, os._exit caught."""

    def setUp(self):
        self.assertTrue(hasattr(km, "_KERNEL_LOCK_FD") and hasattr(km, "_kernel_lock_announce_drain"),
                        "the kernel has no instance lock")
        saved = jd.STATE
        MODULE_STATE_ROOT.mkdir(parents=True, exist_ok=True)
        jd._rebind_state(MODULE_STATE_ROOT)          # this module's own root, whatever an earlier test left bound
        self.addCleanup(jd._rebind_state, saved)
        self.dir = tempfile.mkdtemp(prefix="kernel-lock-drain-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, "kernel.lock")

    def _drain(self, fd, first_act=None):
        """Run _drain_and_exit with `fd` as the held lock; `first_act` is called where the drain's next step (ending
        the judges' child) runs, so it reads the world the announcement left. Returns os._exit's mock."""
        def ending(**kw):
            if first_act is not None:
                first_act()
            return None                              # no child to end: the drain joins nothing later
        end = mock.Mock(side_effect=ending)
        with mock.patch.object(km, "_KERNEL_LOCK_FD", fd), \
             mock.patch.object(km, "_sdk_backend", None), \
             mock.patch.object(km._JUDGE_CHILD, "end", end), \
             mock.patch.object(km.os, "_exit", side_effect=SystemExit) as ex:
            with self.assertRaises(SystemExit):
                km._drain_and_exit("the test's drain", what="SIGTERM")
        return ex

    def test_the_first_act_rewrites_the_line_to_draining_with_the_grace_as_its_deadline(self):
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        os.pwrite(fd, ("%d serving\n" % os.getpid()).encode(), 0)
        seen = {}
        t0 = time.time()
        ex = self._drain(fd, first_act=lambda: seen.setdefault("line", Path(self.path).read_text()))
        t1 = time.time()
        ex.assert_called_once_with(0)
        m = re.fullmatch(r"(\d+) draining (\d+\.\d+)\n", seen.get("line", ""))
        self.assertIsNotNone(m, "before the drain's next step the line reads draining: %r" % seen.get("line"))
        self.assertEqual(int(m.group(1)), os.getpid())
        self.assertGreaterEqual(float(m.group(2)), t0 + km.EXIT_GRACE_S - 0.01)
        self.assertLessEqual(float(m.group(2)), t1 + km.EXIT_GRACE_S + 0.01)
        self.assertEqual(Path(self.path).read_text(), seen["line"], "the whole file is the one line")

    def test_a_failed_announcement_is_one_line_and_the_drain_goes_on(self):
        ro = os.open(self.path, os.O_RDONLY | os.O_CREAT, 0o600)   # pwrite through a read-only descriptor raises EBADF
        self.addCleanup(os.close, ro)
        lines = []
        with mock.patch.object(km, "_exit_log", side_effect=lines.append):
            ex = self._drain(ro)
        ex.assert_called_once_with(0)
        drain = [i for i, ln in enumerate(lines) if ln.startswith("romp-kernel: SIGTERM, draining SDK sessions")]
        self.assertTrue(drain, "the drain's own first line: %r" % lines)
        before = lines[:drain[0]]
        self.assertEqual(len(before), 1, "exactly one instance-lock line before the drain's own lines: %r" % before)
        self.assertIn("the instance lock's draining line was not written", before[0])

    def test_with_no_lock_held_the_drain_writes_no_lock_file(self):
        Path(self.path).write_text("4242 serving\n")
        before = _snapshot(self.dir)
        ex = self._drain(None)
        ex.assert_called_once_with(0)
        self.assertEqual(_snapshot_diff(before, _snapshot(self.dir)), [], "nothing written with no lock held")
        self.assertFalse((MODULE_STATE_ROOT / "kernel.lock").exists(), "and no lock file created under the state root")


if __name__ == "__main__":
    unittest.main()
