#!/usr/bin/env python3
"""The state root's mode has a consequence (2026-09-20): the four arms, each with a test that fails at 84b27dd39.

kernel/judge.py makes the state root 0700 at import, best-effort, and until this change swallowed the OSError, read the
mode back once and said one stderr sentence when it was not 0700, refusing nothing. The root's mode is the premise of
_atomic_write's interim-mode argument (a file this uid wrote at a looser mode is not exposed because the root is
owner-only), so a guard that cannot refuse left a security argument resting on a diagnostic. The four arms:

  ONE   a root WRITABLE by group or other (mode & 0o022) refuses to serve: exit 2 at boot, a 503 latch on every request
        but /healthz and /version after it (write access by another local user is the cross-session code-execution road).
  TWO   a root not 0700 but NOT writable by others (0750, 0755, 0711) files one error-centre row, refusing nothing (a
        privacy fault, not a code-execution one).
  THREE the check re-runs on a cadence and before every request, so a root tightened at boot and loosened later is caught,
        and a root tightened again lifts the latch; each transition is said once, never once per pass.
  FOUR  a chmod the repair could not run travels with its errno name and text on every surface.

What fails at 84b27dd39 (this file copied into a detached worktree at that commit and run there: 27 failed, 0 passed).
Discriminator: eight tests raise AttributeError, the judge module has no state_root_mode_check; the ninth
(test_the_suites_own_root_reads_ok_and_recorded_no_repair_error) raises AttributeError on _STATE_ROOT_REPAIR_ERROR.
TheImportRecordsTheRepairError: the child exits 1 on the same AttributeError, and its stderr shows the base's one line,
which carries no errno. Every kernel-side class (Boot, TheRecheckWhileServing, TheJobsRoad, TheIntervalGatesTheRecheck,
TheLatchStandsWhileTheModeIsUnreadable, ARaisingCheckIsCachedAsUnknown, AnOpenWebSocketUnderTheLatch, TheRefusalRefuses,
TheWarnArmFilesOneRowPerTransition) fails in _KernelState.setUp with AttributeError: the kernel module has no
_STATE_ROOT_MODE, so none of their assertions is reached there. The behaviour those assertions pin was shown at
84b27dd39 by a probe outside the suite (a kernel Handler serving on a fresh 0700 root, the root chmod'ed 0777 after the
first request with os.chmod interposed to refuse for it): GET /models answered 200, POST /tick answered 200 and set both
loop wakes, /version carried no stateRootMode; on this branch the same probe answers 503, 503 with neither wake set, and
a /version with the block. Three classes pin the review round of 2026-09-20 against this branch as first written: an
open WebSocket's frame acted under the latch (setConserve wrote conserve-memory.json under the 0777 root), an unknown
verdict lifted the latch with a resumed row reading "mode unreadable again", and a raising check left the cache stale
(each shown by the reviewer's probes, recorded in the notes). tests/test_judge_scratch_private.py::TheStateRootModeIsChecked,
which pins _state_root_mode_line and the import's one line, is unchanged by this change and still passes.

Hermetic: the state root is a fresh temp dir per test (jd._rebind_state), every kernel-side cache is saved and restored,
os.chmod is interposed only for the planted root and only for the test's length, and nothing here reads real state.
"""
import base64
import contextlib
import http.client
import io
import json
import os
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# tests/test_kernel_cors.py's load order: hermetic state BEFORE the loads (they resolve the root at import), the token
# env so _load_token() never touches a real state dir, NO_OPEN so the import launches no browser.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
assert km.jd is jd, "romp_load re-executes a loaded name into the same module: the kernel's judge IS this module's"

REFUSED = PermissionError(1, "chmod refused (interposed)")   # errno 1 is EPERM; os.strerror(1) is "Operation not permitted"


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def _refusing_chmod(root):
    """An os.chmod that raises EPERM for `root` alone and delegates every other path: the shape of a root this uid cannot
    tighten, interposed the way tests/test_judge_scratch_private.py interposes it."""
    real = os.chmod
    rr = os.path.realpath(str(root))

    def refuse(path, mode, *a, **k):
        if os.path.realpath(str(path)) == rr:
            raise PermissionError(REFUSED.errno, REFUSED.strerror)
        return real(path, mode, *a, **k)
    return refuse


def _ws_frame(obj):
    """One masked text frame carrying `obj` as JSON, as a browser sends it (RFC 6455: a client masks every frame)."""
    data = json.dumps(obj).encode()
    mask = os.urandom(4)
    n = len(data)
    hdr = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack("!H", n))
    return hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


def _ws_read_frames(sock, seconds):
    """Every complete text frame the kernel sent on `sock` within `seconds`, decoded as JSON (a server's frames are
    unmasked); frames that are not JSON text are skipped."""
    deadline = time.time() + seconds
    buf, out = b"", []
    while True:
        while len(buf) >= 2:
            op, masked, n, i = buf[0] & 0x0F, buf[1] & 0x80, buf[1] & 0x7F, 2
            if n == 126:
                if len(buf) < 4:
                    break
                n, i = struct.unpack("!H", buf[2:4])[0], 4
            elif n == 127:
                if len(buf) < 10:
                    break
                n, i = struct.unpack("!Q", buf[2:10])[0], 10
            if masked:
                i += 4
            if len(buf) < i + n:
                break
            payload, buf = buf[i:i + n], buf[i + n:]
            if op == 0x1:
                try:
                    out.append(json.loads(payload.decode("utf-8")))
                except Exception:
                    pass
        left = deadline - time.time()
        if left <= 0:
            return out
        sock.settimeout(min(left, 0.25))
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            continue
        if not chunk:
            return out
        buf += chunk


def _wait(pred, seconds=3.0):
    """Poll `pred` until it is true or `seconds` pass; returns its last value."""
    deadline = time.time() + seconds
    while True:
        v = pred()
        if v or time.time() >= deadline:
            return v
        time.sleep(0.02)


class _KernelState(unittest.TestCase):
    """Save and restore every module-level piece the arms touch, and give each test a fresh 0700 root as the state root."""

    def setUp(self):
        self.saved_state = jd.STATE
        self.saved_mode, self.saved_latch = km._STATE_ROOT_MODE, km._STATE_ROOT_REFUSAL
        self.saved_rows = list(km._SDK_BOOT_PROBLEMS)
        self.saved_env = os.environ.get("ROMP_STATE_ROOT_CHECK_S")
        self.saved_wakes = (km._producer_wake.is_set(), km._pusher_wake.is_set())   # POST /tick sets both: restored below
        km._STATE_ROOT_MODE, km._STATE_ROOT_REFUSAL = None, None
        del km._SDK_BOOT_PROBLEMS[:]
        self.root = tempfile.mkdtemp()                    # mkdtemp creates 0700
        jd._rebind_state(Path(self.root))
        self.patcher = None

    def tearDown(self):
        if self.patcher is not None:
            self.patcher.stop()
        try:
            os.chmod(self.root, 0o700)                    # the hygiene sweep must be able to remove it
        except OSError:
            pass
        jd._rebind_state(self.saved_state)
        km._STATE_ROOT_MODE, km._STATE_ROOT_REFUSAL = self.saved_mode, self.saved_latch
        km._SDK_BOOT_PROBLEMS[:] = self.saved_rows
        for ev, was in ((km._producer_wake, self.saved_wakes[0]), (km._pusher_wake, self.saved_wakes[1])):
            (ev.set if was else ev.clear)()
        if self.saved_env is None:
            os.environ.pop("ROMP_STATE_ROOT_CHECK_S", None)
        else:
            os.environ["ROMP_STATE_ROOT_CHECK_S"] = self.saved_env

    def interpose(self):
        """os.chmod refuses the root from here to tearDown (or until release())."""
        self.patcher = mock.patch("os.chmod", new=_refusing_chmod(self.root))
        self.patcher.start()

    def release(self):
        if self.patcher is not None:
            self.patcher.stop()
            self.patcher = None

    def rows(self):
        return [r["text"] for r in km._SDK_BOOT_PROBLEMS]


# ── arm one, two and four: the discriminator ──────────────────────────────────────────────────────────────────────────

class Discriminator(unittest.TestCase):
    """jd.state_root_mode_check's verdicts over the modes that matter. At 84b27dd39 the judge module has no
    state_root_mode_check: every test here fails with AttributeError."""

    def _root(self, mode):
        d = tempfile.mkdtemp()
        os.chmod(d, mode)
        return d

    def test_0700_is_ok_and_says_nothing(self):
        d = tempfile.mkdtemp()
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "ok")
        self.assertIsNone(chk["line"])
        self.assertIsNone(chk["err"])
        self.assertEqual((chk["mode"], chk["modeText"], chk["root"]), (0o700, "0700", d))
        self.assertEqual(chk["remedy"], "chmod 700 %s" % d)
        self.assertLessEqual(abs(chk["t"] - time.time()), 5)

    def test_not_0700_but_not_writable_by_others_warns(self):
        for mode in (0o755, 0o750, 0o711):
            d = self._root(mode)
            chk = jd.state_root_mode_check(d, repair=False)
            self.assertEqual(chk["verdict"], "warn", "%04o" % mode)
            self.assertEqual(chk["modeText"], "%04o" % mode)
            self.assertIn(d, chk["line"], "names the root")
            self.assertIn("%04o" % mode, chk["line"], "names the mode read back")
            self.assertIn("0700", chk["line"], "and the mode expected")
            self.assertIn(chk["remedy"], chk["line"], "and the remedy")
            self.assertNotIn("\n", chk["line"], "one line")
            self.assertEqual(_mode(d), mode, "repair=False: read, not healed")

    def test_writable_by_group_or_other_refuses(self):
        for mode in (0o770, 0o707, 0o722, 0o777):
            d = self._root(mode)
            chk = jd.state_root_mode_check(d, repair=False)
            self.assertEqual(chk["verdict"], "refuse", "%04o" % mode)
            self.assertTrue(mode & jd.STATE_ROOT_REFUSE_MASK)
            self.assertIn("refuses to serve", chk["line"])
            self.assertIn(d, chk["line"]); self.assertIn("%04o" % mode, chk["line"]); self.assertIn(chk["remedy"], chk["line"])

    def test_the_repair_tightens_a_root_this_uid_owns(self):
        """With repair (the default) a 0755 or 0777 root this uid owns is chmod'ed 0700 first and reads ok."""
        for mode in (0o755, 0o777):
            d = self._root(mode)
            chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], "ok", "%04o" % mode)
            self.assertEqual(_mode(d), 0o700)
            self.assertIsNone(chk["err"])

    def test_an_unreadable_root_is_unknown_with_the_errno(self):
        d = os.path.join(tempfile.mkdtemp(), "never-made")
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "unknown")
        self.assertIsNone(chk["mode"]); self.assertIsNone(chk["modeText"])
        self.assertIn("ENOENT", chk["err"]); self.assertIn(os.strerror(2), chk["err"])
        self.assertIn(d, chk["line"]); self.assertIn("could not be checked", chk["line"]); self.assertIn(chk["remedy"], chk["line"])

    def test_a_refused_repair_puts_the_errno_name_and_text_in_err_and_the_line(self):
        """Arm four: the chmod's OSError, with its errno, on the same surface as the mode; and the remedy then says the root
        is not this uid's to change, naming it."""
        for mode, verdict in ((0o755, "warn"), (0o777, "refuse")):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):
                chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], verdict, "%04o" % mode)
            for surface in (chk["err"], chk["line"]):
                self.assertIn("EPERM", surface, "the errno name")
                self.assertIn(os.strerror(1), surface, "and its text")
            self.assertNotIn("interposed", chk["err"], "built from the errno, not from the exception's text")
            self.assertIn("not this uid's to change", chk["remedy"]); self.assertIn(d, chk["remedy"])
            self.assertIn(chk["remedy"], chk["line"])
            self.assertEqual(_mode(d), mode, "the refused chmod changed nothing")

    def test_a_repair_refused_with_eacces_reads_the_same_way(self):
        d = self._root(0o755)
        real = os.chmod

        def eacces(path, mode, *a, **k):
            if os.path.realpath(str(path)) == os.path.realpath(d):
                raise PermissionError(13, "denied (interposed)")
            return real(path, mode, *a, **k)
        with mock.patch("os.chmod", new=eacces):
            chk = jd.state_root_mode_check(d)
        self.assertIn("EACCES", chk["err"]); self.assertIn(os.strerror(13), chk["err"])
        self.assertIn("not this uid's to change", chk["remedy"])

    def test_a_0700_root_whose_chmod_fails_is_ok_with_the_error_on_the_line(self):
        """Arm four's one case where the failed chmod is the whole signal: the root reads 0700 (verdict ok) but this
        uid's chmod is refused (the shape of a root another uid owns). The line is not None: it names the root, 0700,
        the errno name and text, and the remedy. At 84b27dd39: AttributeError (no state_root_mode_check)."""
        d = tempfile.mkdtemp()
        with mock.patch("os.chmod", new=_refusing_chmod(d)):
            chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(chk["modeText"], "0700")
        self.assertIn("EPERM", chk["err"]); self.assertIn(os.strerror(1), chk["err"])
        self.assertIsNotNone(chk["line"], "ok with a repair error is said, not silent")
        for piece in (d, "0700", "EPERM", os.strerror(1), chk["remedy"]):
            self.assertIn(piece, chk["line"])
        self.assertIn("not this uid's to change", chk["remedy"])
        self.assertNotIn("\n", chk["line"])
        # and a plain ok (the chmod ran) still says nothing
        self.assertIsNone(jd.state_root_mode_check(d)["line"])

    def test_the_suites_own_root_reads_ok_and_recorded_no_repair_error(self):
        self.assertIsNone(jd._STATE_ROOT_REPAIR_ERROR, "the import's mkdir and chmod succeeded on the suite's root")
        chk = jd.state_root_mode_check(repair=False)
        self.assertEqual(chk["verdict"], "ok"); self.assertIsNone(chk["err"])


class TheImportRecordsTheRepairError(unittest.TestCase):
    """Arm four at import: a chmod the import could not run is recorded as "ENAME: strerror" (_STATE_ROOT_REPAIR_ERROR) and
    stands in for a check without repair, while the import's one stderr line is exactly as tests/test_judge_scratch_private.py
    pins it. At 84b27dd39 the module has no _STATE_ROOT_REPAIR_ERROR (the child prints an AttributeError and exits 1)."""

    def test_a_refused_chmod_at_import_is_recorded_with_its_errno(self):
        root = os.path.join(tempfile.mkdtemp(), "romp")
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        code = ("import json, os, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "root = %r\n"
                "os.mkdir(root)\n"
                "os.chmod(root, 0o755)\n"
                "real = os.chmod\n"
                "def refuse(path, mode, *a, **k):\n"
                "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
                "        raise PermissionError(1, 'chmod refused (interposed)')\n"
                "    return real(path, mode, *a, **k)\n"
                "os.chmod = refuse\n"
                "jd = load_source('romp_judge_child', %r)\n"
                "chk = jd.state_root_mode_check(repair=False)\n"
                "print(json.dumps({'rec': jd._STATE_ROOT_REPAIR_ERROR, 'err': chk['err'], 'verdict': chk['verdict'],\n"
                "                  'line': chk['line']}))\n"
                % (HERE, root, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["rec"], "EPERM: %s" % os.strerror(1), "recorded from the errno alone")
        self.assertEqual(out["verdict"], "warn")
        self.assertIn("EPERM", out["err"], "a check without repair carries the import's record")
        self.assertIn("EPERM", out["line"])
        said = [l for l in r.stderr.splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "the import's one line, unchanged:\n" + r.stderr)
        self.assertIn(root, said[0]); self.assertIn("0755", said[0])
        self.assertEqual(_mode(root), 0o755, "read, not healed")


# ── arm one and two at boot ──────────────────────────────────────────────────────────────────────────────────────────

class Boot(_KernelState):
    """_state_root_boot_check, called from main() right after check_boot_environment and before any thread. At 84b27dd39
    the kernel has no _state_root_boot_check (AttributeError) and _version_info has no stateRootMode key (KeyError)."""

    def test_a_root_writable_by_others_stops_the_boot_with_exit_2_and_the_line(self):
        os.chmod(self.root, 0o777)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        line = err.getvalue()
        self.assertIn(self.root, line, "names the root")
        self.assertIn("0777", line, "names the mode read back")
        self.assertIn("chmod 700", line, "and the remedy")
        self.assertIn("not this uid's to change", line, "the refused chmod's remedy")
        self.assertIn("EPERM", line, "arm four rides the boot line")
        self.assertIn("did NOT start", line)
        self.assertEqual(self.rows(), [], "the process exits: no row to file")
        self.assertEqual(_mode(self.root), 0o777, "read, not healed (the chmod was refused)")
        self.assertEqual(km._version_info()["stateRootMode"]["verdict"], "refuse", "the check is stored for /version")

    def test_main_runs_the_boot_check_right_after_the_credential_check_and_before_any_thread(self):
        import inspect
        src = inspect.getsource(km.main)
        i_cred, i_root, i_thread = (src.index("jd._cred.check_boot_environment()"), src.index("_state_root_boot_check()"),
                                    src.index("threading.Thread("))
        self.assertLess(i_cred, i_root); self.assertLess(i_root, i_thread)

    def test_a_root_not_0700_but_not_writable_by_others_files_one_row_and_boots(self):
        os.chmod(self.root, 0o755)
        self.interpose()                                   # else the repair tightens it and the verdict is ok
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "warn")
        self.assertEqual(len(self.rows()), 1, self.rows())
        self.assertIn(self.root, self.rows()[0]); self.assertIn("0755", self.rows()[0]); self.assertIn("EPERM", self.rows()[0])
        self.assertEqual(err.getvalue().count("state root"), 1, err.getvalue())
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "warn")
        self.assertEqual(v["mode"], "0755")
        self.assertIn("EPERM", v["err"])
        self.assertIsNone(v["refusingSince"])
        self.assertIsInstance(v["checkedAt"], int)
        self.assertNotIn(self.root, json.dumps(v), "/version is auth-exempt: no filesystem path (its contract)")
        self.assertIn("the state root", v["remedy"])
        # the first runtime pass after the boot sees the same warn: no second row for it
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.rows()), 1, "one row per transition, and the boot's check was the previous state")

    def test_a_0700_root_whose_chmod_fails_files_one_row_and_boots(self):
        """Arm four on the kernel's surfaces for a root that reads 0700 but whose chmod this uid cannot run: the boot
        goes on (verdict ok), one stderr line and one error-centre row carry the errno, /version's err carries it, and
        the runtime re-check files no second row while the state holds; a chmod that works again says nothing, and a
        second refusal is a second transition. At 84b27dd39: AttributeError in setUp (no _STATE_ROOT_MODE)."""
        self.interpose()                                   # mkdtemp made the root 0700; the chmod is refused
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(len(self.rows()), 1, self.rows())
        for piece in (self.root, "0700", "EPERM", os.strerror(1)):
            self.assertIn(piece, self.rows()[0])
        self.assertEqual(err.getvalue().count("state root"), 1, err.getvalue())
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["mode"], v["refusingSince"]), ("ok", "0700", None))
        self.assertIn("EPERM", v["err"])
        self.assertNotIn(self.root, json.dumps(v))
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        with contextlib.redirect_stderr(io.StringIO()):
            for _ in range(3):
                self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.rows()), 1, "one row per transition, not per check")
        self.release()                                     # the chmod runs again: plain ok, nothing said
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.rows()), 1)
        self.assertIsNone(km._STATE_ROOT_MODE["err"])
        self.interpose()                                   # refused again: a second transition, a second row
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.rows()), 2)

    def test_a_0700_root_files_nothing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(self.rows(), [])
        self.assertEqual(err.getvalue(), "")
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["mode"], v["err"], v["refusingSince"]), ("ok", "0700", None, None))

    def test_version_says_unchecked_before_any_check(self):
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "unchecked")
        self.assertEqual(set(v), {"verdict", "mode", "err", "remedy", "checkedAt", "refusingSince"})


# ── arm three: the re-check, on the request road and the jobs road ───────────────────────────────────────────────────

class _Serving(_KernelState):
    """A kernel serving on a hermetic 0700 root: the boot check passed ok, the interval is 0 so every request re-reads."""

    def setUp(self):
        super().setUp()
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def req(self, method, path, body=None, token=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            h = {"X-Romp-Token": km.TOKEN} if token else {}
            if body is not None:
                h["Content-Type"] = "application/json"
            conn.request(method, path, body=body, headers=h)
            r = conn.getresponse()
            raw = r.read()
            return r.status, raw, {k.lower(): v for k, v in r.getheaders()}
        finally:
            conn.close()

    def loosen(self):
        """The root chmod'ed 0777 after boot, with os.chmod interposed so the re-check's repair cannot tighten it."""
        os.chmod(self.root, 0o777)
        self.interpose()

    def tighten(self):
        self.release()
        os.chmod(self.root, 0o700)

    def ws_upgrade(self, path="/ws?app=chat"):
        """One raw WebSocket upgrade with the token: (the HTTP status it answers, the socket, the bytes after the headers)."""
        key = base64.b64encode(os.urandom(16)).decode()
        lines = ["GET %s&token=%s HTTP/1.1" % (path, km.TOKEN), "Host: 127.0.0.1:%d" % self.port, "Upgrade: websocket",
                 "Connection: Upgrade", "Sec-WebSocket-Key: %s" % key, "Sec-WebSocket-Version: 13"]
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        head, _, rest = buf.partition(b"\r\n\r\n")
        return int(head.split(b" ", 2)[1]), s, rest

    def ws_status(self, path="/ws?app=chat"):
        """One raw WebSocket upgrade with the token; the HTTP status it answers."""
        status, s, _ = self.ws_upgrade(path)
        s.close()
        return status


class TheRecheckWhileServing(_Serving):
    """The road that matters: a root loosened AFTER boot is caught by the next request. At 84b27dd39 the gated GET answers
    200 after the chmod (nothing re-reads the mode), and there is no latch, no stateRootMode and no _state_root_verdict."""

    def test_a_root_loosened_after_boot_latches_503_and_a_tightened_root_lifts_it(self):
        self.assertEqual(self.req("GET", "/models")[0], 200, "serving on the 0700 root")
        self.loosen()
        with contextlib.redirect_stderr(io.StringIO()):
            status, raw, h = self.req("GET", "/models")
        self.assertEqual(status, 503)
        self.assertEqual(h.get("content-type"), "application/json")
        body = json.loads(raw)
        self.assertEqual(body["error"], "the state root is writable by other local users")
        self.assertEqual(body["mode"], "0777")
        self.assertIn("chmod 700", body["remedy"])
        self.assertNotIn(self.root, raw.decode(), "the 503 answers before the token gate: no filesystem path in it")
        self.assertIsNotNone(km._STATE_ROOT_REFUSAL)
        # /version and /healthz keep answering, and /version carries the reason
        status, raw, _ = self.req("GET", "/version", token=False)
        self.assertEqual(status, 200)
        v = json.loads(raw)["stateRootMode"]
        self.assertEqual(v["verdict"], "refuse")
        self.assertEqual(v["mode"], "0777")
        self.assertIsInstance(v["refusingSince"], int)
        self.assertNotIn(self.root, raw.decode())
        self.assertEqual(self.req("GET", "/healthz", token=False)[0], 200)
        # the latch was filed once as a problem row, and stays one row over more refused requests
        refused_rows = [r for r in self.rows() if "refuses to serve" in r]
        self.assertEqual(len(refused_rows), 1, self.rows())
        self.assertIn(self.root, refused_rows[0], "the error-centre row names the root")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 503)
            self.assertEqual(self.req("GET", "/sessions")[0], 503)
            self.assertEqual(self.req("GET", "/busy", token=False)[0], 503, "every path but /healthz and /version")
            self.assertEqual(self.req("HEAD", "/file?path=x")[0], 503)
            self.assertEqual(self.ws_status(), 503, "a new /ws upgrade gets the 503 like every other route")
        self.assertEqual(len([r for r in self.rows() if "refuses to serve" in r]), 1, "one row per transition, not per request")
        # tightened again: the next request serves, /version says ok, one "resumed" row
        self.tighten()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 200)
        self.assertIsNone(km._STATE_ROOT_REFUSAL)
        v = json.loads(self.req("GET", "/version", token=False)[1])["stateRootMode"]
        self.assertEqual((v["verdict"], v["mode"], v["refusingSince"]), ("ok", "0700", None))
        resumed = [r for r in self.rows() if "serving resumed" in r]
        self.assertEqual(len(resumed), 1, self.rows())
        self.assertIn("0700", resumed[0])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 200)
        self.assertEqual(len([r for r in self.rows() if "serving resumed" in r]), 1, "said once")

    def test_options_preflight_is_503_under_the_latch(self):
        self.loosen()
        with contextlib.redirect_stderr(io.StringIO()):
            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            try:
                conn.request("OPTIONS", "/tick", headers={"X-Romp-Token": km.TOKEN, "Origin": "vscode-webview://x"})
                self.assertEqual(conn.getresponse().status, 503)
            finally:
                conn.close()


class TheJobsRoad(_KernelState):
    """The cadence road: the jobs pass's `stateRootMode` stage runs _state_root_verdict(now), and the latch flips the same
    way with no request in flight. At 84b27dd39 there is no _state_root_verdict and _jobs_pass has no such stage."""

    def test_the_stage_latches_and_lifts_like_a_request_does(self):
        import inspect
        self.assertIn("_job_stage('stateRootMode', lambda: _state_root_verdict(now))", inspect.getsource(km._jobs_pass))
        self.assertIn("stateRootMode", km._PerfStats.PASS_JOBS)
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            v = km._job_stage('stateRootMode', lambda: km._state_root_verdict(int(time.time())))   # the pass's call, verbatim
        self.assertEqual(v, "refuse")
        self.assertIsNotNone(km._STATE_ROOT_REFUSAL)
        self.assertIn(self.root, km._STATE_ROOT_REFUSAL["line"]); self.assertIn("0777", km._STATE_ROOT_REFUSAL["line"])
        self.assertIn("503", err.getvalue(), "the stderr line says what the latch does")
        self.assertEqual(len([r for r in self.rows() if "refuses to serve" in r]), 1)
        with contextlib.redirect_stderr(io.StringIO()):
            for _ in range(3):
                self.assertEqual(km._state_root_verdict(time.time()), "refuse")
        self.assertEqual(len([r for r in self.rows() if "refuses to serve" in r]), 1, "one row per transition, not per pass")
        self.release()
        os.chmod(self.root, 0o700)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertIsNone(km._STATE_ROOT_REFUSAL)
        self.assertEqual(len([r for r in self.rows() if "serving resumed" in r]), 1)


class TheIntervalGatesTheRecheck(_KernelState):
    """Between two re-reads the cached check stands (STATE_ROOT_CHECK_S, 15 s by default; ROMP_STATE_ROOT_CHECK_S overrides
    it at call time). At 84b27dd39 there is no cadence at all (AttributeError)."""

    def test_default_and_override(self):
        os.environ.pop("ROMP_STATE_ROOT_CHECK_S", None)
        self.assertEqual(km._state_root_check_interval(), 15.0)
        self.assertEqual(km.STATE_ROOT_CHECK_S, 15.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        self.assertEqual(km._state_root_check_interval(), 0.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "not-a-number"
        self.assertEqual(km._state_root_check_interval(), 15.0)

    def test_a_fresh_check_is_served_from_the_cache_until_the_interval_passes(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "3600"
        os.chmod(self.root, 0o777)
        self.interpose()
        now = time.time()
        self.assertEqual(km._state_root_verdict(now), "ok", "inside the interval the cache answers")
        self.assertIsNone(km._STATE_ROOT_REFUSAL)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(now + 3601), "refuse", "past it the mode is re-read")
        self.assertIsNotNone(km._STATE_ROOT_REFUSAL)


class TheLatchStandsWhileTheModeIsUnreadable(_Serving):
    """A verdict the check could not read lifts no latch: with the root latched at 0777 and then renamed away (stat
    ENOENT), the next request is still 503, /version says unknown with refusingSince set, one unknown row says the latch
    stands, and no "serving resumed" row is filed; a mode read back tight lifts it, and the resumed row names that mode.
    At 84b27dd39: AttributeError in setUp (no _STATE_ROOT_MODE). This branch as first written lifted the latch on unknown
    and filed a resumed row reading "mode unreadable again" (the 2026-09-20 review's probe race.refuse_then_unknown)."""

    def test_an_unreadable_root_keeps_the_latch_and_a_mode_read_back_lifts_it(self):
        self.loosen()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 503)
        self.assertIsNotNone(km._STATE_ROOT_REFUSAL)
        away = self.root + ".away"
        os.rename(self.root, away)                        # the root path is gone: os.stat fails ENOENT
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                for _ in range(2):
                    self.assertEqual(self.req("GET", "/models")[0], 503, "unknown lifts nothing")
            self.assertIsNotNone(km._STATE_ROOT_REFUSAL)
            self.assertEqual(km._STATE_ROOT_MODE["verdict"], "unknown")
            unknown_rows = [r for r in self.rows() if "could not be checked" in r]
            self.assertEqual(len(unknown_rows), 1, self.rows())
            self.assertIn("ENOENT", unknown_rows[0]); self.assertIn("latch stands", unknown_rows[0])
            self.assertEqual([r for r in self.rows() if "serving resumed" in r], [])
            v = json.loads(self.req("GET", "/version", token=False)[1])["stateRootMode"]
            self.assertEqual(v["verdict"], "unknown")
            self.assertIsNone(v["mode"])
            self.assertIsInstance(v["refusingSince"], int)
        finally:
            os.rename(away, self.root)
        self.tighten()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 200)
        self.assertIsNone(km._STATE_ROOT_REFUSAL)
        resumed = [r for r in self.rows() if "serving resumed" in r]
        self.assertEqual(len(resumed), 1, self.rows())
        self.assertIn("mode 0700 again", resumed[0], "worded from the mode read back")
        self.assertNotIn("unreadable", resumed[0])


class ARaisingCheckIsCachedAsUnknown(_Serving):
    """A check that raises (not an OSError, which it catches) is cached as an unknown check with the exception's type
    name: the latch stands, one row files, the traceback is said once on the transition and not on every request, and
    /version carries the type name and no exception text. At 84b27dd39: AttributeError in setUp (no _STATE_ROOT_MODE).
    This branch as first written left the cache stale on a raise, so the traceback repeated on every request (the
    2026-09-20 review's probe race.raising_check)."""

    def test_a_raising_check_is_one_unknown_row_and_keeps_the_latch(self):
        self.loosen()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 503)
        n_before = len(self.rows())
        err = io.StringIO()
        with mock.patch.object(jd, "state_root_mode_check", side_effect=RuntimeError("boom (interposed)")):
            with contextlib.redirect_stderr(err):
                for _ in range(3):
                    self.assertEqual(self.req("GET", "/models")[0], 503, "the latch stands")
            self.assertIsNotNone(km._STATE_ROOT_REFUSAL)
            self.assertEqual(km._STATE_ROOT_MODE["verdict"], "unknown", "the cache is refreshed, not left stale")
            self.assertIn("RuntimeError", km._STATE_ROOT_MODE["err"])
            new_rows = self.rows()[n_before:]
            self.assertEqual(len(new_rows), 1, new_rows)
            self.assertIn("RuntimeError", new_rows[0]); self.assertIn("latch stands", new_rows[0]); self.assertIn(self.root, new_rows[0])
            self.assertEqual(err.getvalue().count("Traceback (most recent call last)"), 1, "said once, on the transition")
            v = json.loads(self.req("GET", "/version", token=False)[1])["stateRootMode"]
            self.assertEqual(v["verdict"], "unknown")
            self.assertIn("RuntimeError", v["err"]); self.assertNotIn("interposed", v["err"], "the type name, never the text")
            self.assertIsInstance(v["refusingSince"], int)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 503, "unpatched: the real mode (0777, chmod refused) is re-read")
        self.assertEqual(km._STATE_ROOT_MODE["verdict"], "refuse")
        self.tighten()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("GET", "/models")[0], 200)
        self.assertEqual(len([r for r in self.rows() if "serving resumed" in r]), 1)


class AnOpenWebSocketUnderTheLatch(_Serving):
    """The latch's WebSocket arm: a socket upgraded on the 0700 root stays open, but a frame it sends while the root is
    writable by others runs no op. The frame itself is a re-check road (no HTTP request sets the latch first), the socket
    is answered one stateRootRefused frame per latch episode (the 503 body, no filesystem path) and a second frame under
    the same episode is dropped in silence; the op's write (setConserve writes conserve-memory.json under the root) does
    not happen, and happens again once the root reads tight. At 84b27dd39: AttributeError in setUp (no _STATE_ROOT_MODE).
    This branch as first written let the frame act and wrote the file under the 0777 root while latched (the 2026-09-20
    review's probe ws.existing_client_under_latch)."""

    def test_a_frame_under_the_latch_runs_no_op_and_the_socket_is_told_once(self):
        conserve = Path(self.root) / km.CONSERVE_FILE_NAME
        status, s, _ = self.ws_upgrade("/ws?app=feed")
        self.assertEqual(status, 101)
        try:
            s.sendall(_ws_frame({"type": "setConserve", "enabled": True}))
            self.assertTrue(_wait(conserve.exists), "on the 0700 root the frame acts")
            self.assertEqual(json.loads(conserve.read_text()), {"enabled": True})
            conserve.unlink()
            self.loosen()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                s.sendall(_ws_frame({"type": "setConserve", "enabled": True}))
                frames = _ws_read_frames(s, 1.5)
            refused = [f for f in frames if isinstance(f, dict) and f.get("type") == "stateRootRefused"]
            self.assertEqual(len(refused), 1, frames)
            self.assertEqual(refused[0]["status"], 503)
            self.assertEqual(refused[0]["error"], "the state root is writable by other local users")
            self.assertEqual(refused[0]["mode"], "0777")
            self.assertIn("chmod 700", refused[0]["remedy"])
            self.assertNotIn(self.root, json.dumps(refused[0]), "no filesystem path on the wire")
            self.assertIsNotNone(km._STATE_ROOT_REFUSAL, "the frame set the latch: the WS road re-checks")
            self.assertFalse(conserve.exists(), "the op did not run")
            self.assertEqual(len([r for r in self.rows() if "refuses to serve" in r]), 1)
            with contextlib.redirect_stderr(io.StringIO()):
                s.sendall(_ws_frame({"type": "setConserve", "enabled": True}))
                frames = _ws_read_frames(s, 1.0)
            self.assertEqual([f for f in frames if isinstance(f, dict) and f.get("type") == "stateRootRefused"], [],
                             "told once per episode")
            self.assertFalse(conserve.exists())
            self.assertEqual(self.req("GET", "/models")[0], 503, "and the HTTP road sees the same latch")
            self.tighten()
            with contextlib.redirect_stderr(io.StringIO()):
                s.sendall(_ws_frame({"type": "setConserve", "enabled": True}))
                self.assertTrue(_wait(conserve.exists), "tight again: the same socket's frame acts")
            self.assertIsNone(km._STATE_ROOT_REFUSAL)
            self.assertEqual(json.loads(conserve.read_text()), {"enabled": True})
        finally:
            s.close()


# ── arm one at runtime: the refusal refuses ──────────────────────────────────────────────────────────────────────────

class TheRefusalRefuses(_Serving):
    """Under the latch a POST to a gated route answers 503 and its effect does not happen. POST /tick's effect is the two
    loop wakes (_producer_wake.set(), _pusher_wake.set()), observable in-process. At 84b27dd39 the POST answers 200 and
    both wakes are set with the root at 0777."""

    def test_post_tick_under_the_latch_is_503_and_wakes_nothing(self):
        km._producer_wake.clear(); km._pusher_wake.clear()
        self.assertEqual(self.req("POST", "/tick", body="{}")[0], 200, "the route works on the 0700 root")
        self.assertTrue(km._producer_wake.is_set() and km._pusher_wake.is_set())
        km._producer_wake.clear(); km._pusher_wake.clear()
        self.loosen()
        with contextlib.redirect_stderr(io.StringIO()):
            status, raw, h = self.req("POST", "/tick", body="{}")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(raw)["error"], "the state root is writable by other local users")
        self.assertEqual((h.get("connection") or "").lower(), "close", "the body was never read: the connection closes")
        self.assertFalse(km._producer_wake.is_set(), "the route did not run")
        self.assertFalse(km._pusher_wake.is_set())
        self.tighten()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.req("POST", "/tick", body="{}")[0], 200)
        self.assertTrue(km._producer_wake.is_set() and km._pusher_wake.is_set(), "serving resumed, the effect with it")


# ── arm two at runtime: one row per transition ───────────────────────────────────────────────────────────────────────

class TheWarnArmFilesOneRowPerTransition(_KernelState):
    """Three checks at 0755 file one row, a return to 0700 files none, and a second loosening is a second transition. At
    84b27dd39 there is no _state_root_verdict (AttributeError)."""

    def test_three_checks_one_row(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o755)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.rows()), 1, self.rows())
        self.assertIn("0755", self.rows()[0]); self.assertIn(self.root, self.rows()[0]); self.assertIn("EPERM", self.rows()[0])
        self.assertEqual(err.getvalue().count("state root"), 1, "and one stderr line")
        self.assertIsNone(km._STATE_ROOT_REFUSAL, "warn refuses nothing")
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["mode"]), ("warn", "0755"))
        self.release()
        os.chmod(self.root, 0o700)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.rows()), 1, "a return to ok files no row")
        os.chmod(self.root, 0o750)
        self.interpose()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.rows()), 2, "a second loosening is a second transition")
        self.assertIn("0750", self.rows()[1])

    def test_an_unreadable_root_is_surfaced_like_warn(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        gone = os.path.join(self.root, "gone")
        jd._rebind_state(Path(gone))
        with contextlib.redirect_stderr(io.StringIO()):
            for _ in range(2):
                self.assertEqual(km._state_root_verdict(time.time()), "unknown")
        self.assertEqual(len(self.rows()), 1)
        self.assertIn("ENOENT", self.rows()[0])
        self.assertIsNone(km._STATE_ROOT_REFUSAL)


if __name__ == "__main__":
    unittest.main()
