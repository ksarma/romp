"""The served labs' kernel ports, and the proof that the kernel answering on one is the lab's own (2026-10-02).

WHY. Every served lab used to draw its kernels' ports by drawing and releasing: bind a socket to port 0, read the port
the system chose, close the socket. Nothing remembers a port once its socket is closed, so two draws in a row can return
the same one (16 equal pairs in 200,000 back-to-back draws, measured on Linux), and no lab checked. A federated lab drew
its remote's port and its hub's port that way. When the two were equal the hub could not bind, its /healthz wait was
answered by the remote and called the hub ready, and the lab's /checkin to the hub reached the remote instead, whose 403
errored the class at setup with a message naming neither cause (tests/test_federated_cutfloor_served.py on CI,
2026-10-01). The same draws could give a one-kernel lab a postal port equal to its serve port (kernel_env's), and between
a draw and the kernel's bind any other process on the machine could draw the released port again.

THE DOOR. Every served module that boots a kernel takes its ports here and waits for its kernel here:
  reserve(owner)   A port that no live reservation of this process holds. On Linux the drawing socket (SO_REUSEADDR,
                   bound, never listening) stays open until the port is released. While it is open, no bind to port 0
                   anywhere on the machine is given that port (plain, SO_REUSEADDR or SO_REUSEPORT; measured), and a
                   server that binds with SO_REUSEADDR, as the kernel's HTTPServer does, still binds and listens on it.
                   A consumer that binds WITHOUT SO_REUSEADDR is refused (EADDRINUSE), so hand a reserved port only to a
                   kernel, or to a field nothing binds (the postal port of a client-only kernel, a check-in's busPort).
                   A draw that returns a port this process already holds is drawn again, up to MAX_DRAWS times.
                   Off Linux (macOS and BSD bind an address another socket holds only under SO_REUSEPORT) the socket is
                   closed at once, and this process's table alone keeps its ports distinct.
  release(owner)   Frees the ports `owner` holds and those of every owner under it as a path: a lab and its sub-labs,
                   since kernel_env reserves a kernel's postal port under that kernel's own lab directory. Call it after
                   the lab's kernels are killed and reaped, never before, or a port could be handed out again while a
                   kernel still serves on it. A falsy owner frees nothing (a teardown after a setup that never made its
                   lab). A port never released stays held until the process exits and its socket closes with it.
  wait_owned(proc, env, tries=120, pause=0.5)
                   The readiness wait for the kernel `proc`, started with the environment `env` (the exact mapping
                   handed to Popen). Returns None once the kernel has proved the port env["ROMP_KERNEL_PORT"] its own;
                   otherwise a sentence saying why not, for the caller's skip or failure. Proved means two things.
                   GET /healthz on the port answered 200 with an X-Romp-Boot whose pid is proc.pid (the header is the
                   kernel's process identity, "<pid>.<start>", kernel/kernel.py _BOOT_ID). And the state root `env`
                   names records that port in its serve-port file (written right after the kernel's bind and before it
                   serves, kernel/kernel.py _persist_serve_port, so the answer on the port is never ahead of the
                   record). An answer from any other process is noted and waited past. The kernel exiting ends the
                   wait, and the reason names the answerer when one was seen. The record is read only once the pid has
                   matched, so a record left by an earlier kernel on the same state root (a lab that restarts its
                   kernel) neither proves nor refuses anything. A kernel from ANOTHER checkout (a mixed-build lab's
                   older remote or hub, tests/test_federated_capability_corners_served.py) that writes no record
                   (kernels before 2026-09-08) is held to the pid proof alone; this checkout's kernel always owes the
                   record. Each try costs at most one second of probe plus `pause` of sleep, the shape of the
                   hand-written loops this replaced (tests/test_federated_linkdrop_served.py's hub_restart_bound_s
                   counts on it). Raises AssertionError when the port was not reserved by this process (a port drawn
                   some other way) or when `env` names no state root of its own.

tests/test_lab_ports_census.py holds every served module to this door (no draw and release, no hand-written /healthz
wait, every kernel spawn proved, every reserving module releasing); tests/test_lab_ports.py executes the door, against
stand-ins and against two real kernels handed one port. Synthetic throughout: no real session data.
"""
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

LINUX = sys.platform.startswith("linux")
MAX_DRAWS = 64        # draws per reserve() before it gives up on finding a port this process does not hold
_HERE = os.path.dirname(os.path.realpath(__file__))
KERNEL = os.path.join(os.path.dirname(_HERE), "bin", "romp-kernel")   # this checkout's kernel: it always owes the record
_LOCK = threading.Lock()
_HELD = {}            # port -> (the drawing socket, or None off Linux, its owner)


def _draw():
    """One draw: a socket bound to a port the system picks, and that port. The tests force this primitive."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if LINUX:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        return s, s.getsockname()[1]
    except BaseException:
        s.close()
        raise


def _owner(owner):
    if not owner:
        raise ValueError("a reservation names its owner (the lab directory that releases it), not %r" % (owner,))
    return str(owner)


def reserve(owner):
    """A port no live reservation of this process holds, held for `owner` until release(owner) (see the module's
    docstring for what holding means on Linux and elsewhere)."""
    owner = _owner(owner)
    with _LOCK:
        for _ in range(MAX_DRAWS):
            s, port = _draw()
            if port in _HELD:
                s.close()
                continue
            if not LINUX:
                s.close()
                s = None
            _HELD[port] = (s, owner)
            return port
    raise RuntimeError("lab_ports.reserve: every one of %d draws returned a port this process already holds" % MAX_DRAWS)


def release(owner):
    """Free the ports `owner` holds and those of every owner under it as a path; the number freed. A falsy owner frees
    nothing."""
    if not owner:
        return 0
    owner = str(owner)
    under = owner.rstrip(os.sep) + os.sep
    freed = 0
    with _LOCK:
        for port, (s, held_by) in list(_HELD.items()):
            if held_by == owner or held_by.startswith(under):
                if s is not None:
                    s.close()
                del _HELD[port]
                freed += 1
    return freed


def held(owner=None):
    """The ports held, sorted: all of this process's, or those of `owner` and the owners under it."""
    with _LOCK:
        if owner is None:
            return sorted(_HELD)
        owner = str(owner)
        under = owner.rstrip(os.sep) + os.sep
        return sorted(p for p, (_, k) in _HELD.items() if k == owner or k.startswith(under))


def state_root(env):
    """The state root a kernel started with `env` uses: ROMP_STATE_DIR, else <XDG_STATE_HOME>/romp (kernel/judge.py
    STATE, with `or` for an empty value as there). None when env names neither: such a kernel would use the real root."""
    if env.get("ROMP_STATE_DIR"):
        return env["ROMP_STATE_DIR"]
    if env.get("XDG_STATE_HOME"):
        return os.path.join(env["XDG_STATE_HOME"], "romp")
    return None


def _record(state):
    """The port the state root's serve-port file names, or None (absent or unreadable)."""
    try:
        with open(os.path.join(state, "serve-port")) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _boot_pid(boot):
    """The pid in an X-Romp-Boot value ("<pid>.<start>"), or None."""
    try:
        return int(str(boot).split(".", 1)[0])
    except ValueError:
        return None


def _this_checkout(proc):
    """Does `proc` run this checkout's kernel? Read from its argv: any element that resolves to bin/romp-kernel here."""
    args = proc.args if isinstance(proc.args, (list, tuple)) else [proc.args]
    mine = os.path.realpath(KERNEL)
    return any(os.path.realpath(os.fspath(a)) == mine for a in args if isinstance(a, (str, bytes, os.PathLike)))


def wait_owned(proc, env, tries=120, pause=0.5):
    """None once the kernel `proc` proved the port in env["ROMP_KERNEL_PORT"] its own; else the reason, a sentence (the
    module's docstring states the proof)."""
    port = int(env["ROMP_KERNEL_PORT"])
    with _LOCK:
        mine = port in _HELD
    if not mine:
        raise AssertionError("port %d was not reserved through lab_ports.reserve in this process: a port drawn any "
                             "other way can be drawn again before the kernel binds it" % port)
    state = state_root(env)
    if state is None:
        raise AssertionError("the kernel's environment names no state root of its own (ROMP_STATE_DIR or "
                             "XDG_STATE_HOME): it would read and write the real one")
    seen = None   # the last answer on the port from anything other than this kernel
    for _ in range(tries):
        rc = proc.poll()
        if rc is not None:
            return "kernel pid %d exited (rc %s) before it proved port %d its own%s" % (
                proc.pid, rc, port, "; the port answered as %s" % seen if seen else "")
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=1) as r:
                boot = r.headers.get("X-Romp-Boot")
        except urllib.error.HTTPError as e:
            seen = "an HTTP %d with X-Romp-Boot %r" % (e.code, e.headers.get("X-Romp-Boot"))
            e.close()
            time.sleep(pause)
            continue
        except Exception:
            time.sleep(pause)
            continue
        if _boot_pid(boot) != proc.pid:
            seen = "X-Romp-Boot %r, not kernel pid %d" % (boot, proc.pid)
            time.sleep(pause)
            continue
        rec = _record(state)
        if rec == port or (rec is None and not _this_checkout(proc)):
            return None
        return "kernel pid %d answers on port %d but its state root %s records serve-port %r: the environment " \
               "handed to wait_owned is not the one the kernel runs with" % (proc.pid, port, state, rec)
    return "kernel pid %d never proved port %d its own in %d tries%s" % (
        proc.pid, port, tries, "; the port answered as %s" % seen if seen else "")
