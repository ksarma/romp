#!/usr/bin/env python3
"""The kernel-restart test for the per-session host (T315, stage 4 of #1317), end to end through a real kernel
process (no browser: this file is deliberately NOT named `_served.py`, the suffix CI's extension job collects for
the browser-backed page tests and runs with ROMP_SERVED_TESTS_REQUIRE=1, which would turn the SDK-venv skip below
into a failure on a runner that has no venv): a hermetic kernel with the
session-hosts setting ON runs a session whose fake CLI takes twenty seconds over a turn; the kernel is sent
SIGTERM five seconds in (the manager's restart: a drain that now DETACHES); a second kernel boots on the same
state directory, attaches to the live host, and the turn finishes under it: the session settles waiting, the
old kernel's restart-cuts row has an empty cutTurns, the CLI is the same process throughout (one writer), no
continuation notice was queued, and a host.attached row with boot true is on the ledger. A second run with
the setting OFF (a toggled-off machine, since hosts are on by default) pins the plain child's behaviour (the turn is
cut, a notice is queued, a new CLI pid), so the test proves
the difference, not a constant.

Hermetic: a temp state root and Claude config dir, the fake CLI as ROMP_CLAUDE_BIN, no scopes, the SDK venv
symlinked into the temp state root (the kernel looks for it there); skipped where that venv is absent (CI).
Every process the test starts is killed by it. Synthetic ids only. A third case, collected everywhere, pins that a skip
raised in setUp stays a clean skip (its class docstring names the defect).
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid
from pathlib import Path
from unittest.mock import patch

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (named runner variables, never the whole environment)
# the checkout's ONE build of the bundles, copied under the harness lock (tests/lab_dist.py); never a lock-free copy of
# the shared checkout's dist by hand (the pull-in's review round 1, 2026-09-16)
import lab_dist
FAKE = os.path.join(HERE, "fixtures", "fake_claude.py")
SDKVENV = os.path.expanduser("~/.local/state/romp/sdkvenv")
# the kernel must run on the python the SDK venv was built for (its lib/python3.X names it), not on whatever
# `python3` the test runner's environment puts first
_tags = sorted(p.name for p in Path(SDKVENV, "lib").glob("python3.*")) if os.path.isdir(os.path.join(SDKVENV, "lib")) else []
KERNEL_PYTHON = next((shutil.which(t) for t in _tags if shutil.which(t)), None)
HAVE_SDK = KERNEL_PYTHON is not None


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@unittest.skipUnless(HAVE_SDK, "no SDK venv (or no matching python) on this machine; the served host test needs the real SDK client in the kernel")
class ServedRestart(unittest.TestCase):
    def setUp(self):
        # every attribute the sweep reads exists BEFORE the cleanup that reads them is registered: setUp can end early with a
        # skip (lab_dist.copy_dist raises unittest.SkipTest by design on a checkout without the extension's node_modules) or
        # an error, and unittest runs the registered cleanups either way, on the instance as setUp left it (the pull-in's
        # review round 2, 2026-09-16: the cleanup ran before self.kernels existed and every skipped case was also an error)
        self.kernels = []
        self.klogs = []
        self.sid = str(uuid.uuid4())
        self.lab = tempfile.mkdtemp(prefix="host-served-")
        self.state = os.path.join(self.lab, "xdg", "romp")
        self.addCleanup(self._sweep)
        self.claude = os.path.join(self.lab, "claude")
        self.cwd = os.path.join(self.lab, "proj")
        for d in ("names", "sdk", "states", "timeline"):
            os.makedirs(os.path.join(self.state, d), exist_ok=True)
        os.makedirs(self.cwd, exist_ok=True)
        self._lab_sdkvenv()
        Path(self.state, "names", self.sid).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % self.cwd)
        Path(self.state, "sdk", self.sid + ".json").write_text(json.dumps(
            {"sid": self.sid, "name": "web", "cwd": self.cwd, "mode": "bypassPermissions", "effort": "high", "lastSid": self.sid, "alive": True}))
        self.port, self.token = _free_port(), "testtok-host"
        self.dist = os.path.join(self.lab, "dist")
        lab_dist.copy_dist(self.dist)   # a lab copy under the harness lock: the kernel must never rebuild bundles in the shared checkout
        self.fake_log = os.path.join(self.lab, "fake-cli.log")

    def _lab_sdkvenv(self):
        """The lab's sdkvenv: a real directory tree of the lab's own (pyvenv.cfg copied; lib/python3.X/site-packages made
        0700 at every level) whose site-packages ENTRIES link to the live venv's packages. Through the round-4 tree of fork
        PR 874 the lab put one symlink at <state>/sdkvenv pointing at the live venv, and the kernel's guarded reader
        refuses a symlink at any component under the state root (a symlinked sdkvenv is the planted-venv shape it
        quarantines, tests/test_state_root_mode.py TheGuardedReadersQuarantine), so the kernel found no SDK and every
        session crashed at its import (round 4d, 2026-09-21; the case had skipped on this box until the extension's
        node_modules existed, and skips on CI, which has no SDK venv). The guard judges the directory it puts on sys.path,
        which is the lab's; what Python imports through the entries inside it is not a read of the state root, and a copy
        of the live site-packages (about 280 MB) per case is not a lab."""
        venv = os.path.join(self.state, "sdkvenv")
        os.mkdir(venv, 0o700)
        cfg = os.path.join(SDKVENV, "pyvenv.cfg")
        if os.path.isfile(cfg):
            shutil.copyfile(cfg, os.path.join(venv, "pyvenv.cfg"))
        lib = os.path.join(venv, "lib")
        os.mkdir(lib, 0o700)
        for tag in _tags:
            live = os.path.join(SDKVENV, "lib", tag, "site-packages")
            if not os.path.isdir(live):
                continue
            os.mkdir(os.path.join(lib, tag), 0o700)
            site = os.path.join(lib, tag, "site-packages")
            os.mkdir(site, 0o700)
            for entry in os.listdir(live):
                os.symlink(os.path.join(live, entry), os.path.join(site, entry))
        for d in (venv, lib):
            os.chmod(d, 0o700)                       # the mkdir's mode is masked by the umask; the guard wants no group or other write

    def _sweep(self):
        """Kill what the case started and remove its lab. Runs on the instance as setUp left it, whole or not (a skip or an
        error partway through setUp), so every attribute read here has a default and a lease that cannot be read is no lease."""
        lab = getattr(self, "lab", None)
        lease = None
        if getattr(self, "state", None) and getattr(self, "sid", None):
            try:
                lease = self._lease()
            except (OSError, ValueError):   # a lease mid-write, or gone between the exists and the read
                lease = None
        for pid in ((lease or {}).get("pid"), ((lease or {}).get("holder") or {}).get("pid")):
            if isinstance(pid, int):
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        for k in getattr(self, "kernels", ()):
            if k.poll() is None:
                try:
                    os.killpg(k.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                k.wait(timeout=10)
        if not lab:
            return
        # whatever the hosts left: every process whose environment carries this lab's state root
        for p in Path("/proc").glob("[0-9]*"):
            try:
                env = (p / "environ").read_bytes()
            except OSError:
                continue
            if lab.encode() in env and int(p.name) != os.getpid():
                try:
                    os.kill(int(p.name), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        shutil.rmtree(lab, ignore_errors=True)

    def _env(self):
        env = _lab.kernel_env(self.lab, self.claude, self.dist, self.port, self.token,
                              ROMP_CLAUDE_BIN=FAKE, ROMP_CLI_SCOPE="0",
                              FAKE_CLI_TRANSCRIPT_DIR=os.path.join(self.lab, "transcripts"), FAKE_CLI_LOG=self.fake_log,
                              PATH=os.environ.get("PATH", ""), HOME=os.environ.get("HOME", ""))
        for k in ("ROMP_STATE_DIR", "ROMP_API_KEY_CMD", "ANTHROPIC_API_KEY", "ROMP_SDK_SITE"):
            env.pop(k, None)
        return env

    def _start_kernel(self):
        log = os.path.join(self.lab, "kernel-%d.log" % (len(self.kernels) + 1))
        k = subprocess.Popen([KERNEL_PYTHON, os.path.join(BIN, "romp-kernel")], stdout=open(log, "w"), stderr=subprocess.STDOUT,
                             env=self._env(), start_new_session=True)
        self.kernels.append(k); self.klogs.append(log)
        deadline = time.time() + 60
        while time.time() < deadline:   # loop-ok: a bounded wait on the kernel serving
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % self.port, timeout=1)
                return k
            except Exception:
                if k.poll() is not None:
                    break
                time.sleep(0.25)
        raise unittest.SkipTest("hermetic kernel never served /healthz here: " + open(log).read()[-800:])

    def _send(self, text):
        req = urllib.request.Request("http://127.0.0.1:%d/send?token=%s" % (self.port, self.token),
                                     data=json.dumps({"id": self.sid, "text": text}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def _state(self):
        p = Path(self.state, "states", self.sid + ".jsonl")
        last = None
        if p.exists():
            for ln in p.read_text().splitlines():
                try:
                    row = json.loads(ln)
                except ValueError:
                    continue
                if "state" in row:
                    last = row["state"]
        return last

    def _lease(self):
        p = Path(self.state, "leases", self.sid + ".json")
        return json.loads(p.read_text()) if p.exists() else None

    def _events(self, kind):
        p = Path(self.state, "session-events.jsonl")
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip() and json.loads(l).get("kind") == kind] if p.exists() else []

    def _cuts(self):
        p = Path(self.state, "restart-cuts.jsonl")
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def _wait(self, pred, timeout, what):
        deadline = time.time() + timeout
        while time.time() < deadline:   # loop-ok: a bounded wait on an observable event
            if pred():
                return
            time.sleep(0.25)
        tails = "\n".join("--- %s:\n%s" % (l, open(l).read()[-2500:]) for l in self.klogs)
        self.fail("timed out waiting for %s\n%s" % (what, tails))

    def _run(self, hosts_on: bool):
        Path(self.state, "session-hosts").write_text("on" if hosts_on else "off")
        self._start_kernel()
        self.assertTrue(self._send("start long sleep=20").get("ok"), "the send was accepted")
        self._wait(lambda: self._state() == "working", 60, "the turn to start (working)")
        if hosts_on:
            self._wait(lambda: (self._lease() or {}).get("holder", {}).get("kind") == "host", 30, "a host-held lease")
        else:
            self._wait(lambda: self._lease() is not None, 30, "a kernel-held lease")
        lease1 = self._lease()
        time.sleep(3.0)                                    # five seconds in, the restart
        k1 = self.kernels[-1]
        os.kill(k1.pid, signal.SIGTERM)                    # _graceful_term: the drain
        k1.wait(timeout=30)
        cuts = [r for r in self._cuts() if r.get("pid") == k1.pid and "cutTurns" in r]
        self.assertEqual(len(cuts), 1, "the old kernel filed its restart-cuts row: %r" % self._cuts())
        self._start_kernel()
        self._wait(lambda: self._state() == "waiting", 60, "the turn to finish under the second kernel (waiting)")
        reg = json.loads(Path(self.state, "sdk", self.sid + ".json").read_text())
        queued = [t for t in (reg.get("queue") or []) if isinstance(t, str)]
        return lease1, cuts[0], queued

    def test_with_hosts_on_the_turn_survives_the_restart_and_with_hosts_off_it_is_cut(self):
        lease1, cut, queued = self._run(hosts_on=True)
        self.assertEqual(cut["cutTurns"], [], "an attached session is detached, not cut: %r" % cut)
        lease2 = self._lease()
        self.assertIsNotNone(lease2, "the host still holds the lease after the turn")
        self.assertEqual((lease2["pid"], lease2["holder"]["pid"]), (lease1["pid"], lease1["holder"]["pid"]), "the same CLI and host: one writer")
        att = self._events("host.attached")
        self.assertEqual([a["boot"] for a in att], [False, True], "spawn-time attach, then the boot attach: %r" % att)
        self.assertGreater(att[1]["replayFrom"], 0, "the boot attach replayed from the acknowledged offset")
        self.assertFalse(any("restart" in t.lower() and "cut" in t.lower() for t in queued), "no continuation notice: %r" % queued)
        transcript = list(Path(self.lab, "transcripts").glob("*.jsonl"))
        self.assertEqual(len(transcript), 1, "one transcript stand-in, one writer")
        results = [json.loads(l) for l in transcript[0].read_text().splitlines() if '"type":"result"' in l]
        self.assertEqual([r["result"] for r in results], ["done"], "one result, the turn's normal completion: the restart neither cut nor interrupted it")

    def test_control_with_hosts_off_the_restart_cuts_the_turn(self):
        lease1, cut, queued = self._run(hosts_on=False)
        self.assertEqual([c["sid"] for c in cut["cutTurns"]], [self.sid], "the toggled-off machine: the turn is cut")
        # the continuation notice reached the CLI (the fake logs every stdin line): a user message naming the restart
        fed = [json.loads(l) for l in Path(self.fake_log).read_text().splitlines() if l.strip()]
        users = [m for m in fed if m.get("type") == "user"]
        texts = [c if isinstance(c := (m.get("message") or {}).get("content"), str) else json.dumps(c) for m in users]
        self.assertTrue(any("restart" in t.lower() for t in texts), "the second kernel fed the continuation notice: %r" % texts[-3:])
        lease2 = self._lease()
        self.assertIsNotNone(lease2, "the resumed session holds a fresh kernel lease")
        self.assertNotEqual(lease2["pid"], lease1["pid"], "a NEW CLI process: the old one was cut and reaped")
        self.assertNotEqual((lease2.get("holder") or {}).get("kind"), "host")
        self.assertEqual(self._events("host.attached"), [], "no host, no attach")


class ASkipInSetUpStaysASkip(unittest.TestCase):
    """A cleanup registered before its attributes existed made every skip an error (the pull-in's review round 2,
    2026-09-16). ServedRestart.setUp registered _sweep right after the lab was minted and set self.kernels last, after
    lab_dist.copy_dist, which raises unittest.SkipTest by design on a checkout without the extension's node_modules;
    unittest runs the cleanups after a skipped setUp too, so _sweep read self.kernels on an instance that had none and each
    skipped case was ALSO reported as an error (2 skipped, 2 errors). The pin runs ONE case of the served class through a
    unittest result object with the copy stubbed to skip and the class's SDK gate lifted for that run, so it reaches setUp
    whatever this machine has: one skip carrying the stub's reason, no error, no failure, and the lab removed. Collected
    everywhere: it needs no SDK venv, no node_modules and starts no kernel."""

    def test_a_skip_raised_in_setup_leaves_the_case_a_clean_skip(self):
        reason = "the pin's stand-in for a checkout without the extension's node_modules"

        def refuse(dest):
            raise unittest.SkipTest(reason)
        case = ServedRestart("test_with_hosts_on_the_turn_survives_the_restart_and_with_hosts_off_it_is_cut")
        result = unittest.TestResult()
        with patch.object(lab_dist, "copy_dist", refuse), \
                patch.object(ServedRestart, "__unittest_skip__", False, create=True), \
                patch.object(ServedRestart, "__unittest_skip_why__", "", create=True):
            unittest.TestSuite([case]).run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertEqual([why for _t, why in result.skipped], [reason], "the run reached setUp and the stub skipped it")
        self.assertEqual(result.errors, [], "the cleanup ran clean on the half-built instance:\n" + "\n".join(tb for _t, tb in result.errors))
        self.assertEqual(result.failures, [])
        self.assertFalse(os.path.exists(case.lab), "the sweep reached its end and removed the lab")


if __name__ == "__main__":
    unittest.main()
