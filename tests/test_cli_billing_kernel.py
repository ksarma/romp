#!/usr/bin/env python3
"""`romp billing` end to end (the user 2026-09-18, who wanted the CLI to change a session's billing even when that
means restarting its CLI, because only the dashboard could): the REAL bin/romp driven against a hermetic kernel
process that runs the fake Claude CLI (tests/fixtures/fake_claude.py), with poisoned ports (ROMP_MANAGER_PORT=1, its own
kernel port and token, the postal trio from kernel_env), so nothing here reaches the machine's own kernel.

The lab: a signed-in login (an invented account in the lab HOME's .claude.json, the file the kernel's probe reads) and a
configured apiKeyHelper (the lab's Claude settings; read, never run), so both sides are billable. The fake CLI honours the
helper the way the real one does when FAKE_CLI_HONOR_HELPER is set: a launch with the helper in place reports
apiKeySource "apiKeyHelper", a launch whose flag-settings overlay blanks the helper (a login pick) reports "none", so
every session lands on the side romp composed and the walks read the truth. Four sessions in the notes-api world: web
and tests follow the default and run; api carries a login pick and runs; docs follows the default and never runs (no
CLI process: the read answers from its reg).

Cases, in method order (one kernel, one roster; each case leaves the state the next one reads):
  1. the read prints three lines for a follower, a picked session and a dormant one;
  2. `--all-following key` writes the pick on the two live followers, skips the picked one, chips nothing;
  3. `romp billing web login` writes auth/authLogin/authPending into the reg and the session reconnects onto the login;
  4. `romp billing api default` returns the picked session to following the default (its reconnect lands on the key);
  5. `--now` cuts an in-flight turn and the reconnect follows at its settle;
  6. an unknown session exits 1 with the resolver's error, a junk pick exits 1 with the kernel's, misuse exits 2.

This file is deliberately NOT named `_served.py`: CI's extension job runs that suffix with ROMP_SERVED_TESTS_REQUIRE=1,
which turns the SDK-venv skip below into a failure on a runner with no venv (tests/test_session_host_restart.py's rule).
Hermetic: a temp lab, and the class ends its whole process tree, the kernel and every fake CLI it spawned, as a CLASS
CLEANUP (addClassCleanup), which unittest runs after a setUpClass that raised as well as after tearDownClass: the first
runs of this file failed in setUpClass, tearDownClass never ran, and two kernels with their fake CLIs outlived their
deleted labs for half an hour (2026-09-18). The sweep asserts that nothing of the tree survives. Synthetic ids and names
only.
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
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (named runner variables, never the whole environment)
import lab_dist   # noqa: E402
FAKE = os.path.join(HERE, "fixtures", "fake_claude.py")
ROMP = os.path.join(BIN, "romp")
SDKVENV = os.path.expanduser("~/.local/state/romp/sdkvenv")
# the kernel must run on the python the SDK venv was built for (its lib/python3.X names it), not on whatever
# `python3` the test runner's environment puts first
_tags = sorted(p.name for p in Path(SDKVENV, "lib").glob("python3.*")) if os.path.isdir(os.path.join(SDKVENV, "lib")) else []
KERNEL_PYTHON = next((shutil.which(t) for t in _tags if shutil.which(t)), None)
HAVE_SDK = KERNEL_PYTHON is not None


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _dist_for_lab(dest):
    """The lab kernel's dist. With the extension's node_modules present the kernel's boot would rebuild bundles when its
    dist is missing, so the copy comes through the harness lock (tests/lab_dist.py: never a build in the shared checkout);
    without them the kernel's bundle step prints and returns, so an empty directory serves (no dashboard, every route)."""
    if os.path.isdir(os.path.join(ROOT, "vscode-extension", "node_modules")):
        lab_dist.copy_dist(dest)
    else:
        os.makedirs(dest, exist_ok=True)


@unittest.skipUnless(HAVE_SDK, "no SDK venv (or no matching python) on this machine; the lab kernel needs the real SDK client to run the fake CLI")
class BillingVerb(unittest.TestCase):
    NAMES = ("web", "api", "tests", "docs")

    @classmethod
    def setUpClass(cls):
        cls.kernel = None
        cls.lab = tempfile.mkdtemp(prefix="billing-")
        cls.addClassCleanup(cls._sweep)   # runs after a setUpClass that raises too, where tearDownClass would not (the leak's road)
        cls.state = os.path.join(cls.lab, "xdg", "romp")
        cls.claude = os.path.join(cls.lab, "claude")
        cls.home = os.path.join(cls.lab, "home")
        cls.cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states", "timeline"):
            os.makedirs(os.path.join(cls.state, d), exist_ok=True)
        for d in (cls.claude, cls.home, cls.cwd):
            os.makedirs(d, exist_ok=True)
        os.symlink(SDKVENV, os.path.join(cls.state, "sdkvenv"))
        # a signed-in login: the kernel's probe reads ~/.claude.json for the account (an invented uuid and label)
        Path(cls.home, ".claude.json").write_text(json.dumps(
            {"oauthAccount": {"accountUuid": "00000000-0000-4000-8000-000000000000", "emailAddress": "dev@example.com"}}))
        # a configured apiKeyHelper: read by the kernel (key_available) and by the fake CLI (its report), never run
        Path(cls.claude, "settings.json").write_text(json.dumps({"apiKeyHelper": "/bin/true"}))
        cls.sids = {}
        for name in cls.NAMES:
            sid = str(uuid.uuid4())
            cls.sids[name] = sid
            Path(cls.state, "names", sid).write_text("%s\t%s\t#9cd2ff\t#0c1a2e\n" % (name, cls.cwd))
            reg = {"sid": sid, "name": name, "cwd": cls.cwd, "mode": "bypassPermissions", "effort": "high",
                   "lastSid": sid, "alive": True}
            if name == "api":
                reg.update(auth="login", authLogin="")   # its own pick: the machine's login
            Path(cls.state, "sdk", sid + ".json").write_text(json.dumps(reg))
        cls.port, cls.token = _free_port(), "testtok-billing"
        cls.dist = os.path.join(cls.lab, "dist")
        _dist_for_lab(cls.dist)
        cls.fake_log = os.path.join(cls.lab, "fake-cli.log")
        cls.tdir = os.path.join(cls.lab, "transcripts")
        env = _lab.kernel_env(cls.lab, cls.claude, cls.dist, cls.port, cls.token,
                              ROMP_CLAUDE_BIN=FAKE, ROMP_CLI_SCOPE="0", FAKE_CLI_HONOR_HELPER="1",
                              FAKE_CLI_TRANSCRIPT_DIR=cls.tdir, FAKE_CLI_LOG=cls.fake_log,
                              PATH=os.environ.get("PATH", ""), HOME=cls.home)
        for k in ("ROMP_STATE_DIR", "ROMP_API_KEY_CMD", "ANTHROPIC_API_KEY", "ROMP_SDK_SITE"):
            env.pop(k, None)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([KERNEL_PYTHON, os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=env, start_new_session=True)
        deadline = time.time() + 60
        while time.time() < deadline:   # loop-ok: a bounded wait on the kernel serving
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                if cls.kernel.poll() is not None:
                    break
                time.sleep(0.25)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + cls._klog_tail())
        if cls.kernel.poll() is not None:
            raise unittest.SkipTest("hermetic kernel exited at boot: " + cls._klog_tail())
        # three sessions run: one short turn each, so their CLIs launch and their inits land (docs stays dormant)
        for name in ("web", "api", "tests"):
            cls._send(name, "hello sleep=0.2")
        for name in ("web", "api", "tests"):
            cls._wait(lambda n=name: cls._view(n).get("live") and cls._last_state(n) == "waiting",
                      "%s's init to land and its turn to settle" % name, timeout=60)

    @classmethod
    def _klog_tail(cls):
        try:
            return open(cls.klog).read()[-6000:]
        except OSError:
            return "(no kernel log)"

    @classmethod
    def _landed_then_reported(cls, name, side, timeout=90):
        """Wait for `name`'s reconnect to LAND (authPending clears at the landing, the launched stamp names the side), then
        drive one short turn and wait for the CLI's own report of the side: the CLI, the real one and the fake alike,
        emits its init with the first turn, so authLive stays empty from the arm until a turn runs."""
        cls._wait(lambda: not cls._view(name).get("pending") and cls._view(name).get("launched") == side,
                  "%s's reconnect to land on the %s" % (name, side), timeout=timeout)
        cls._send(name, "hello sleep=0.2")
        cls._wait(lambda: cls._view(name).get("live") == side and cls._last_state(name) == "waiting",
                  "%s's init to report the %s" % (name, side), timeout=timeout)

    @classmethod
    def _lab_processes(cls):
        """Every live process of this lab's tree but this one, as (pid, command): a cwd under the lab root (the fake CLIs
        run in the lab's project directory, a deleted one still named in /proc) or the lab root in the environment (the
        kernel, and everything it spawned inherits XDG_STATE_HOME under the root). Another user's process refuses both
        reads and is not this lab's."""
        lab = cls.lab
        out = []
        for p in Path("/proc").glob("[0-9]*"):
            pid = int(p.name)
            if pid == os.getpid():
                continue
            try:
                cwd = os.readlink(str(p / "cwd"))
            except OSError:
                cwd = ""
            hit = cwd == lab or cwd.startswith(lab + os.sep)
            if not hit:
                try:
                    hit = lab.encode() in (p / "environ").read_bytes()
                except OSError:
                    hit = False
            if hit:
                try:
                    cmd = (p / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
                except OSError:
                    cmd = "?"
                out.append((pid, cmd[:160]))
        return out

    @classmethod
    def _sweep(cls):
        """End the lab's whole process tree, then the lab, and assert that nothing of the tree survives. The kernel first:
        it runs in a session of its own (start_new_session), so its group is killed and the process waited on, as
        tests/test_session_host_restart.py's sweep does. Then every process the lab root still names (_lab_processes: the
        fake CLIs the kernel spawned, including the one mid-way through the --now case's 40 s turn; the kernel's death
        does not end them, and a CLI the SDK started in a session of its own is outside the kernel's group), killed by
        pid until none is left or ten seconds pass. Then the lab's files. The assertion is the fails-before for the leak
        this class had (the module docstring): a tree that outlives the class is an error of the class, never silence."""
        k = cls.kernel
        if k is not None and k.poll() is None:
            try:
                os.killpg(k.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                k.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        deadline = time.time() + 10
        survivors = cls._lab_processes()
        while survivors and time.time() < deadline:   # loop-ok: a bounded wait on the kills landing
            for pid, _ in survivors:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            time.sleep(0.2)
            survivors = cls._lab_processes()
        shutil.rmtree(cls.lab, ignore_errors=True)
        assert not survivors, "the lab's process tree outlived the class: %r" % (survivors,)

    @classmethod
    def _wait(cls, pred, what, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:   # loop-ok: a bounded wait on an observable event
            try:
                if pred():
                    return
            except Exception:
                pass
            time.sleep(0.2)
        raise AssertionError("timed out waiting for %s\nkernel log tail: %s" % (what, cls._klog_tail()))

    @classmethod
    def _send(cls, name, text):
        req = urllib.request.Request("http://127.0.0.1:%d/send?token=%s" % (cls.port, cls.token),
                                     data=json.dumps({"id": cls.sids[name], "text": text}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    @classmethod
    def _view(cls, name):
        """GET /billing?target=<name>: the kernel's own read, the truth the CLI prints from."""
        url = "http://127.0.0.1:%d/billing?target=%s&token=%s" % (cls.port, urllib.parse.quote(name, safe=""), cls.token)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode() or "{}")

    @classmethod
    def _reg(cls, name):
        return json.loads(Path(cls.state, "sdk", cls.sids[name] + ".json").read_text())

    @classmethod
    def _states(cls, name):
        p = Path(cls.state, "states", cls.sids[name] + ".jsonl")
        if not p.exists():
            return []
        out = []
        for ln in p.read_text().splitlines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                pass
        return out

    @classmethod
    def _last_state(cls, name):
        rows = [r for r in cls._states(name) if "state" in r]
        return rows[-1]["state"] if rows else ""

    @classmethod
    def _gestures(cls, name):
        return [r["cmdGesture"] for r in cls._states(name) if "cmdGesture" in r]

    @classmethod
    def _romp(cls, *args):
        """The REAL bin/romp, aimed at the lab kernel by the two names every verb reads (the port and the serve token)."""
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": cls.home,
               "ROMP_KERNEL_PORT": str(cls.port), "ROMP_SERVE_TOKEN": cls.token,
               "XDG_STATE_HOME": os.path.join(cls.lab, "xdg"), "XDG_CONFIG_HOME": os.path.join(cls.lab, "config")}
        return subprocess.run(["bash", ROMP, "billing", *args], env=env, capture_output=True, text=True, timeout=120)

    def _lines(self, out):
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = out.stdout.splitlines()
        self.assertEqual(len(lines), 3, out.stdout)
        return lines

    def test_1_the_read_prints_three_lines_for_a_follower_a_picked_and_a_dormant_session(self):
        launched, pick, default = self._lines(self._romp("web"))
        self.assertEqual(launched, "launched: API key; the CLI reports: API key")
        self.assertEqual(pick, "pick: follows the machine default")
        self.assertEqual(default, "machine default: API key (the helper rule)")
        launched, pick, default = self._lines(self._romp("api"))
        self.assertEqual(launched, "launched: login; the CLI reports: login", "the login pick's launch blanked the helper")
        self.assertEqual(pick, "pick: login")
        launched, pick, default = self._lines(self._romp(self.sids["docs"]))   # a dormant session, by id as by name
        self.assertEqual(launched, "launched: no CLI process running")
        self.assertEqual(pick, "pick: follows the machine default")
        self.assertEqual(default, "machine default: API key (the helper rule)")
        self.assertEqual(self._lines(self._romp("docs"))[0], "launched: no CLI process running")

    def test_2_all_following_moves_the_live_followers_and_skips_the_picked_one_without_a_chip(self):
        out = self._romp("--all-following", "key")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: 2 sessions now bill the API key (tests, web); 1 skipped (api): it has its own pick")
        for name in ("tests", "web"):
            reg = self._reg(name)
            self.assertEqual((reg["auth"], reg["authLogin"]), ("key", ""), name)
            self.assertEqual(self._gestures(name), [], "%s: no /auth chip on the walk" % name)
            self.assertEqual(self._romp(name).stdout.splitlines()[1], "pick: API key")
        self.assertEqual(self._reg("api")["auth"], "login", "the picked session keeps its own pick")
        self.assertNotIn("auth", self._reg("docs"), "a dormant follower is not in the walk: it launches on the default")

    def test_3_a_pick_writes_the_reg_and_the_session_reconnects_onto_it(self):
        out = self._romp("web", "login")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "romp billing: web bills the login from now; the session is reconnecting to apply it")
        reg = self._reg("web")
        self.assertEqual((reg["auth"], reg["authLogin"]), ("login", ""))
        self.assertIn("authPending", reg, "set_auth's pending write, cleared by the landing")
        self._landed_then_reported("web", "login")
        self.assertEqual(self._gestures("web"), ["/auth login"], "the dashboard's chip: the CLI's pick is the same op")
        launched, pick, _ = self._lines(self._romp("web"))
        self.assertEqual(launched, "launched: login; the CLI reports: login")
        self.assertEqual(pick, "pick: login")

    def test_4_default_returns_a_picked_session_to_the_machine_default(self):
        out = self._romp("api", "default")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: api follows the machine default again (API key); the session is reconnecting to apply it")
        reg = self._reg("api")
        self.assertEqual((reg["auth"], reg["authLogin"]), ("", ""))
        self._landed_then_reported("api", "key")
        view = self._view("api")
        self.assertIs(view["pick"]["explicit"], False)
        self.assertEqual(self._lines(self._romp("api"))[1], "pick: follows the machine default")
        self.assertEqual(self._gestures("api"), [], "no /auth chip: the session made no pick")

    def test_5_now_cuts_the_in_flight_turn_and_the_reconnect_follows_its_settle(self):
        self._send("tests", "start long sleep=40")
        self._wait(lambda: self._last_state("tests") == "working", "tests to be mid-turn")
        out = self._romp("tests", "login", "--now")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(),
                         "romp billing: the in-flight turn was cut; tests bills the login from now; the session is reconnecting to apply it")
        self._wait(lambda: any('"result":"interrupted"' in p.read_text() for p in Path(self.tdir).glob("*.jsonl")),
                   "the fake CLI's turn to end interrupted")
        self._landed_then_reported("tests", "login", timeout=120)
        self.assertEqual(self._reg("tests")["auth"], "login")

    def test_6_refusals_and_misuse(self):
        out = self._romp("nosuch")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("nosuch", out.stderr)
        self.assertEqual(out.stdout, "")
        out = self._romp("nosuch", "login")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("nosuch", out.stderr)
        out = self._romp("web", "bogus")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertIn("not a billing choice", out.stderr)
        for args in ((), ("--all-following",), ("web", "login", "--later"), ("--now", "web", "login"), ("web", "--now")):
            out = self._romp(*args)
            self.assertEqual(out.returncode, 2, "%r: %s" % (args, out.stderr))
            self.assertTrue(out.stderr.startswith("usage: romp billing "), (args, out.stderr))


if __name__ == "__main__":
    unittest.main()
