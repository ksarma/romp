#!/usr/bin/env python3
"""tests/lab_ports.py executed (2026-10-02): the served labs' ports are distinct and held, and a kernel is ready only once
it has proved its port its own.

The defect it closes: two back-to-back draw-and-release draws can return one port, and a /healthz wait that accepts any
answer reads another kernel's answer as its own kernel's (a federated lab's hub, handed its remote's port, was called ready
on the remote's answer and its check-in got the remote's 403). The module docstring of tests/lab_ports.py has the account.

  DistinctDraws    a forced draw that returns a port the process already holds is drawn again, and a draw that returns
                   one every time raises at MAX_DRAWS; kernel_env's postal port is reserved under its lab and is never the
                   lab kernel's serve port, under the same forcing; release frees an owner and the owners under it.
  HeldPorts        (Linux) while a port is reserved no bind to port 0 is given it, plain, SO_REUSEADDR or SO_REUSEPORT;
                   a server binding with SO_REUSEADDR, as the kernel's does, binds and serves on it; a plain bind is refused.
  OwnershipProof   wait_owned against a stand-in /healthz server and a stand-in process: proved only by the stand-in's
                   own pid in X-Romp-Boot with the state root's serve-port record naming the port; another process's
                   answer is waited past and named when the process exits; an earlier kernel's record proves nothing; a
                   record naming another port, a port not reserved here and an environment with no state root are
                   refused; a kernel from another checkout that writes no record is held to the pid proof alone.
  BareName         the tests package registers lab_ports under its bare name, as it does lab_dist, so a served module
                   that imports it before putting tests/ on sys.path imports it collected alone too.
  TwoRealKernels   (Linux) a real kernel on a reserved port proves it; a second real kernel handed the same port is
                   refused with the first kernel's pid named, exits nonzero and writes no record. The lab dist holds one
                   empty render.js stamped newer than every source, so neither kernel's boot build runs node or npm in
                   the checkout (no page is loaded); each kernel is killed and reaped by a cleanup registered before it
                   starts, and the labs' ports are released after.

Synthetic: invented tokens and placeholder state; the kernels run in temporary labs with session hosts off (kernel_env).
"""
import errno
import http.server
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
sys.path.insert(0, HERE)
import lab_ports                                    # noqa: E402
import test_ship_reship_served as _lab              # noqa: E402  kernel_env (the module, so its classes are not collected here)

LINUX = sys.platform.startswith("linux")


class _Proc:
    """A stand-in for a Popen: a pid, an argv, and a poll() that answers None for `alive` calls and then `rc`."""

    def __init__(self, pid, args=None, alive=10 ** 6, rc=1):
        self.pid, self.args, self._alive, self._rc, self.polls = pid, args or ["/elsewhere/bin/romp-kernel"], alive, rc, 0

    def poll(self):
        self.polls += 1
        return None if self.polls <= self._alive else self._rc


class _Server(http.server.HTTPServer):
    """The stand-in's server, with no reverse lookup of its own address at the bind (HTTPServer.server_bind calls
    socket.getfqdn, which holds a macOS runner about 36 seconds per server; kernel/kernel.py's _LoopbackServer says so)."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


class _Healthz(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        srv = self.server
        self.send_response(srv.status)
        if srv.boot is not None:
            self.send_header("X-Romp-Boot", srv.boot)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


class _Owned(unittest.TestCase):
    """A lab of this test's own: an owner path, released on the way out."""

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="labports-")
        self.addCleanup(shutil.rmtree, self.lab, True)
        self.addCleanup(lab_ports.release, self.lab)

    def _root(self, record=None):
        """A stand-in state root under the lab (XDG_STATE_HOME/romp), with a serve-port record when `record` is given."""
        xdg = tempfile.mkdtemp(dir=self.lab)
        os.makedirs(os.path.join(xdg, "romp"))
        if record is not None:
            with open(os.path.join(xdg, "romp", "serve-port"), "w") as f:
                f.write("%d\n" % record)
        return xdg

    def _serve(self, port, boot, status=200):
        """A stand-in /healthz on `port` answering `status` with X-Romp-Boot `boot` (None: no header); stopped by cleanups
        registered before its thread starts."""
        srv = _Server(("127.0.0.1", port), _Healthz)
        srv.boot, srv.status = boot, status
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True, name="labports-standin").start()
        return srv


class DistinctDraws(_Owned):
    def test_a_draw_returning_a_held_port_is_drawn_again(self):
        first = lab_ports.reserve(self.lab)
        real, calls = lab_ports._draw, []

        def forced():
            calls.append(1)
            if len(calls) == 1:
                return socket.socket(), first   # the system handed out the held port again
            return real()
        with mock.patch.object(lab_ports, "_draw", forced):
            second = lab_ports.reserve(self.lab)
        self.assertNotEqual(second, first, "the second reservation is a port of its own")
        self.assertEqual(len(calls), 2, "the held port was refused and drawn again once")
        self.assertEqual(lab_ports.held(self.lab), sorted([first, second]))

    def test_a_draw_that_only_returns_held_ports_gives_up_at_the_bound(self):
        first = lab_ports.reserve(self.lab)
        calls = []

        def forced():
            calls.append(1)
            return socket.socket(), first
        with mock.patch.object(lab_ports, "_draw", forced):
            with self.assertRaisesRegex(RuntimeError, "%d draws" % lab_ports.MAX_DRAWS):
                lab_ports.reserve(self.lab)
        self.assertEqual(len(calls), lab_ports.MAX_DRAWS)
        self.assertEqual(lab_ports.held(self.lab), [first])

    def test_release_frees_the_owner_and_the_owners_under_it_and_nothing_else(self):
        sub = os.path.join(self.lab, "hub")
        sibling = self.lab + "-sibling"   # shares the lab's spelling as a prefix, is not under it
        self.addCleanup(lab_ports.release, sibling)
        mine, under, beside = lab_ports.reserve(self.lab), lab_ports.reserve(sub), lab_ports.reserve(sibling)
        self.assertEqual(lab_ports.release(""), 0, "a falsy owner frees nothing")
        self.assertEqual(lab_ports.release(None), 0)
        self.assertEqual(lab_ports.release(self.lab), 2)
        self.assertNotIn(mine, lab_ports.held())
        self.assertNotIn(under, lab_ports.held())
        self.assertEqual(lab_ports.held(sibling), [beside], "a sibling lab's reservation survives")
        with self.assertRaises(ValueError):
            lab_ports.reserve("")

    def test_kernel_envs_postal_port_is_reserved_under_its_lab_and_never_the_serve_port(self):
        serve = lab_ports.reserve(self.lab)
        real, calls = lab_ports._draw, []

        def forced():
            calls.append(1)
            if len(calls) == 1:
                return socket.socket(), serve   # the postal draw handed the serve port back
            return real()
        kernel_lab = os.path.join(self.lab, "testhost")
        with mock.patch.object(lab_ports, "_draw", forced):
            env = _lab.kernel_env(kernel_lab, os.path.join(kernel_lab, "claude"), os.path.join(self.lab, "dist"), serve, "tok")
        postal = int(env["ROMP_POSTAL_PORT"])
        self.assertNotEqual(postal, serve)
        self.assertEqual(int(env["ROMP_KERNEL_PORT"]), serve)
        self.assertEqual(lab_ports.held(kernel_lab), [postal], "the postal port is held under the kernel's own lab")
        lab_ports.release(self.lab)
        self.assertEqual(lab_ports.held(self.lab), [], "releasing the lab frees its kernels' postal ports too")


@unittest.skipUnless(LINUX, "reservations hold a socket on Linux only (the module docstring says why)")
class HeldPorts(_Owned):
    HELD = 200
    DRAWS = 3000

    def test_no_bind_to_port_zero_is_given_a_held_port(self):
        held = {lab_ports.reserve(self.lab) for _ in range(self.HELD)}
        self.assertEqual(len(held), self.HELD)
        hits = {}
        for name, opt in (("plain", None), ("SO_REUSEADDR", socket.SO_REUSEADDR), ("SO_REUSEPORT", socket.SO_REUSEPORT)):
            n = 0
            for _ in range(self.DRAWS):
                s = socket.socket()
                try:
                    if opt is not None:
                        s.setsockopt(socket.SOL_SOCKET, opt, 1)
                    s.bind(("127.0.0.1", 0))
                    n += s.getsockname()[1] in held
                finally:
                    s.close()
            hits[name] = n
        # without the hold, DRAWS draws over a range of about 28,000 ports would land on one of HELD ports about 21 times
        self.assertEqual(hits, {"plain": 0, "SO_REUSEADDR": 0, "SO_REUSEPORT": 0})

    def test_a_reuseaddr_server_binds_a_reserved_port_and_a_plain_bind_is_refused(self):
        port = lab_ports.reserve(self.lab)
        s = socket.socket()
        try:
            with self.assertRaises(OSError) as cm:
                s.bind(("127.0.0.1", port))
            self.assertEqual(cm.exception.errno, errno.EADDRINUSE)
        finally:
            s.close()
        self._serve(port, "1.1")
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=5) as r:
            self.assertEqual((r.status, r.headers.get("X-Romp-Boot")), (200, "1.1"))


class OwnershipProof(_Owned):
    PID = 4242424   # a stand-in pid: no real process is signalled

    def _env(self, port, xdg):
        return {"ROMP_KERNEL_PORT": str(port), "XDG_STATE_HOME": xdg}

    def test_its_own_pid_and_record_prove_the_port(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, "%d.1700000000" % self.PID)
        self.assertIsNone(lab_ports.wait_owned(_Proc(self.PID), self._env(port, self._root(record=port)), tries=20, pause=0.05))

    def test_another_kernels_answer_is_waited_past_and_named_when_the_process_exits(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, "777.1700000000")
        proc = _Proc(self.PID, alive=3, rc=1)
        why = lab_ports.wait_owned(proc, self._env(port, self._root(record=port)), tries=20, pause=0.05)
        self.assertIsNotNone(why, "another kernel's answer never proves the port")
        self.assertIn("exited (rc 1)", why)
        self.assertIn("'777.1700000000'", why, "the reason names the kernel that answered")
        self.assertEqual(proc.polls, 4, "three tries waited past the foreign answer, the fourth saw the exit")

    def test_an_earlier_kernels_record_with_a_foreign_answer_is_refused(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, "777.1700000000")   # the record names the port, as a restarted lab's earlier kernel left it
        why = lab_ports.wait_owned(_Proc(self.PID), self._env(port, self._root(record=port)), tries=3, pause=0.05)
        self.assertRegex(why or "", r"never proved port %d its own in 3 tries; the port answered as X-Romp-Boot '777\." % port)

    def test_a_record_naming_another_port_is_refused_at_once(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, "%d.1" % self.PID)
        why = lab_ports.wait_owned(_Proc(self.PID), self._env(port, self._root(record=port + 1)), tries=20, pause=0.05)
        self.assertRegex(why or "", r"answers on port %d but its state root .* records serve-port %d" % (port, port + 1))

    def test_an_exited_process_is_reported_with_its_rc(self):
        port = lab_ports.reserve(self.lab)
        why = lab_ports.wait_owned(_Proc(self.PID, alive=0, rc=3), self._env(port, self._root()), tries=20, pause=0.05)
        self.assertEqual(why, "kernel pid %d exited (rc 3) before it proved port %d its own" % (self.PID, port))

    def test_an_http_error_answer_is_foreign(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, None, status=403)
        why = lab_ports.wait_owned(_Proc(self.PID, alive=2), self._env(port, self._root()), tries=20, pause=0.05)
        self.assertIn("an HTTP 403 with X-Romp-Boot None", why or "")

    def test_a_port_not_reserved_here_and_an_env_with_no_state_root_are_refused(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        loose = s.getsockname()[1]
        s.close()
        if loose in lab_ports.held():
            self.skipTest("the probe's port is held by this process")
        with self.assertRaisesRegex(AssertionError, "was not reserved through lab_ports.reserve"):
            lab_ports.wait_owned(_Proc(self.PID), self._env(loose, self._root()))
        port = lab_ports.reserve(self.lab)
        with self.assertRaisesRegex(AssertionError, "names no state root"):
            lab_ports.wait_owned(_Proc(self.PID), {"ROMP_KERNEL_PORT": str(port), "XDG_STATE_HOME": ""})

    def test_the_state_root_follows_the_kernels_rule(self):
        self.assertEqual(lab_ports.state_root({"ROMP_STATE_DIR": "/s", "XDG_STATE_HOME": "/x"}), "/s")
        self.assertEqual(lab_ports.state_root({"ROMP_STATE_DIR": "", "XDG_STATE_HOME": "/x"}), os.path.join("/x", "romp"))
        self.assertIsNone(lab_ports.state_root({"HOME": "/h"}))

    def test_a_missing_record_is_waived_for_another_checkouts_kernel_only(self):
        port = lab_ports.reserve(self.lab)
        self._serve(port, "%d.1" % self.PID)
        other = _Proc(self.PID, args=["/elsewhere/old-checkout/bin/romp-kernel"])
        self.assertIsNone(lab_ports.wait_owned(other, self._env(port, self._root()), tries=20, pause=0.05),
                          "a kernel from before the serve-port record is held to the pid proof alone")
        this = _Proc(self.PID, args=[os.path.join(BIN, "romp-kernel")])
        why = lab_ports.wait_owned(this, self._env(port, self._root()), tries=20, pause=0.05)
        self.assertRegex(why or "", r"records serve-port None", "this checkout's kernel always owes the record")


class BareName(unittest.TestCase):
    def test_the_tests_package_registers_the_bare_name(self):
        """A served module imports lab_ports at its top, before it puts tests/ on sys.path; under pytest and under
        `python -m unittest tests.test_x` the modules are members of the tests package, so the bare name resolves only
        because tests/__init__.py registers it (the shape of lab_dist's registration there). Without it a served module
        collected alone fails at its import, and a whole run passes only when an earlier module happened to put tests/ on
        sys.path. A child interpreter with tests/ off its path imports the package and then the bare name."""
        child = ("import os, sys\n"
                 "here = os.path.realpath(sys.argv[1])\n"
                 "sys.path[:] = [p for p in sys.path if os.path.realpath(p or '.') != here]\n"
                 "import tests\n"
                 "import lab_ports\n"
                 "print(os.path.realpath(lab_ports.__file__))\n"
                 "print(lab_ports is sys.modules['tests.lab_ports'])\n")
        p = subprocess.run([sys.executable, "-c", child, HERE], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-1500:])
        self.assertEqual(p.stdout.split(), [os.path.join(HERE, "lab_ports.py"), "True"])


@unittest.skipUnless(LINUX, "the real-kernel composition runs where the served labs run")
class TwoRealKernels(_Owned):
    def _kernel_lab(self, name):
        lab = os.path.join(self.lab, name)
        dist = os.path.join(lab, "dist")
        os.makedirs(dist)
        os.makedirs(os.path.join(lab, "claude"))
        render = os.path.join(dist, "render.js")
        with open(render, "w") as f:
            f.write("")
        later = time.time() + 10 * 365 * 86400   # newer than every bundle input: the kernel's boot build stands down
        os.utime(render, (later, later))
        return lab, dist

    def _start(self, name, port, procs):
        lab, dist = self._kernel_lab(name)
        env = _lab.kernel_env(lab, os.path.join(lab, "claude"), dist, port, "testtok-labports-" + name)
        log = open(os.path.join(self.lab, name + "-kernel.log"), "w")
        self.addCleanup(log.close)
        procs.append(subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=log, stderr=subprocess.STDOUT, env=env))
        return procs[-1], env

    def _reap(self, procs):
        for p in procs:
            if p.poll() is None:
                p.kill()
            p.wait()

    def _log(self, name):
        with open(os.path.join(self.lab, name + "-kernel.log")) as f:
            return f.read()[-1500:]

    def test_a_second_kernel_handed_the_first_ones_port_is_refused_with_the_first_named(self):
        procs = []
        self.addCleanup(self._reap, procs)   # before either kernel starts: every exit path ends both
        port = lab_ports.reserve(self.lab)
        a, env_a = self._start("a", port, procs)
        why = lab_ports.wait_owned(a, env_a)
        self.assertIsNone(why, "kernel a proves its reserved port: %s\n%s" % (why, self._log("a")))
        b, env_b = self._start("b", port, procs)
        why = lab_ports.wait_owned(b, env_b)
        self.assertIsNotNone(why, "kernel b, handed a's port, is never ready:\n%s" % self._log("b"))
        self.assertRegex(why, r"^kernel pid %d exited \(rc [1-9]\d*\) before it proved port %d its own; the port answered "
                              r"as X-Romp-Boot '%d\.\d+', not kernel pid %d$" % (b.pid, port, a.pid, b.pid))
        self.assertFalse(os.path.exists(os.path.join(lab_ports.state_root(env_b), "serve-port")), "b recorded no port")
        self.assertIsNone(a.poll(), "kernel a still serves")


if __name__ == "__main__":
    unittest.main()
