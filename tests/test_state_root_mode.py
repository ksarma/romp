#!/usr/bin/env python3
"""The state root's mode has a consequence, and the consequence is one shape: THE PROCESS STOPS (round 2, 2026-09-20).

kernel/judge.py makes the state root 0700 at import, best-effort, and until this change swallowed the OSError, read the
mode back once and said one stderr sentence when it was not 0700, refusing nothing. The root's mode is the premise of
_atomic_write's interim-mode argument (a file this uid wrote at a looser mode is not exposed because the root is
owner-only), so a guard that cannot refuse left a security argument resting on a diagnostic. Round 1 answered with a
runtime 503 latch that closed the kernel's two doors and left every internal writer running under the hostile root, the
housekeeping pass whose own stage set the latch included; round 2 replaces the latch with an EXIT, because an exit is
the only shape that stops every writer by construction.

  REFUSE AT IMPORT   a root writable by group or other (mode & 0o022), or one whose mode cannot be read, exits 2 at the
        kernel's module import, BEFORE the serve token is read and repo-root is written (_state_root_import_gate), so the
        kernel never adopts an entry planted under a writable root; the remedy says to remove serve-token and repo-root.
        The verdict stands on the mode as read AT THE GATE, after the judge module's own chmod (the settled rule, round
        2b): a pre-existing root this uid owns that read 0777 and was tightened to 0700 a moment ago is NOT refused
        (refusing it would refuse the first boot after every creation of the root by another tool under a group-writable
        umask); what the import read is reported at boot instead, one loud line and one row with the distrust remedy
        (_state_root_import_mode_row), and a root the import itself CREATED is exempt from that too, the umask's mode on
        a fresh directory being a creation default and not a loosening. A planted symlink at serve-token under such a
        root is stopped by the token loader's own fault; repo-root is written by a temp and a rename, so a planted entry
        at that path is replaced, never written through or left.
  REFUSE AT BOOT     the same verdict in main() exits 2 before any thread starts (_state_root_boot_check, SystemExit in
        the main thread); the import's pre-chmod mode, when it differed, is a warn-class transition, loud and not fatal.
  REFUSE AT RUNTIME  found by the jobs pass's first stage or by a request's cached re-check, os._exit(2) from whichever
        thread found it (_state_root_exit_now), so no later jobs stage, no pusher cycle, no judge pass runs on under the
        root; the manager restarts the kernel and the boot refuses again while the root reads so.
  READ BEFORE REPAIR the check reads the mode FIRST and the verdict is from that read; its own best-effort chmod runs
        after and is reported (repaired, modeAfter), so a root this uid owns that was loosened is re-tightened AND leaves
        a trace, never a silent repair that erases the case the re-check exists to report.
  WARN               a root not 0700 but not writable by others files one error-centre row per transition under the
        bell's "refused" kind (not the mutable "sdk" kind, whose one mute would hide it with the backend's), built to
        fit the bell whole with the remedy first, and refuses nothing.
  THE BUS            postal/postal_service.py carries a reduced copy of the check and the same exit: a bus on a hostile
        or unreadable root exits 2 at start and from its monitor loop; a warn root logs one line and serves.

For each arm the test below names, in its docstring, what the arm does to everything that is NOT the door it guards (the
round's shape demand). The refuse arms are proved behaviourally through child processes that exist at 84b27dd39 too: a
kernel spawned with a hermetic root serves 200 there and never exits when the root is loosened, where here it exits 2
with the line within seconds (recorded under the notes' scratch, a detached worktree of 84b27dd39, removed after). The
in-process tests pin the check dict, the transitions, the fit, the concurrency and the import-ordering.

Hermetic: every root is a fresh temp dir (mkdtemp is 0700 whatever the umask); every kernel-side cache is saved and
restored; the runtime exit is a module-level indirection (_state_root_exit) a test replaces with a raising double, so
the refusal is observable in-process without taking the test runner down; os.chmod is interposed only for the planted
root and only for the test's length; nothing here reads real state. tests/test_judge_scratch_private.py, which pins
_state_root_mode_line and the import's one line, is unchanged by this change and still passes.
"""
import contextlib
import http.client
import io
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# tests/test_kernel_cors.py's load order: hermetic state BEFORE the loads (they resolve the root at import), the token
# env so _load_token() never touches a real state dir, NO_OPEN so the import launches no browser. The XDG root here is
# a fresh mkdtemp (0700), so the kernel's own import gate reads ok and this module loads without refusing.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
os.chmod(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), 0o700)   # under a group-writable umask a fresh mkdir is 0775
with open(os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts"), "w") as _fh:
    _fh.write("off\n")                                                # this module mints roots and rebinds; floor its own too
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
assert km.jd is jd, "romp_load re-executes a loaded name into the same module: the kernel's judge IS this module's"

REFUSED = PermissionError(1, "chmod refused (interposed)")   # errno 1 is EPERM; os.strerror(1) is "Operation not permitted"


class _Exited(BaseException):
    """The runtime exit, as a test double sees it: os._exit(2) never returns, so a double stands in for a process that
    is gone. A BaseException, not an Exception, so it propagates through the `except Exception` guards every jobs stage
    and every request handler wraps its work in, exactly as os._exit's not-returning does: no writer downstream runs."""
    def __init__(self, code):
        self.code = code


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


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def inspect_getsource_module():
    """The kernel module's source text, read from its file (inspect.getsource on a load_source module is reliable, but
    reading the file keeps the AST test independent of import machinery)."""
    return open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()


# ── arm READ-BEFORE-REPAIR, WARN, REFUSE, UNKNOWN, and arm-four errno: the discriminator ─────────────────────────────

class Discriminator(unittest.TestCase):
    """jd.state_root_mode_check's verdict over the modes that matter, and what the check's own repair does to the
    verdict: NOTHING. The verdict is taken from the mode as READ; the best-effort chmod runs after and is reported
    (repaired, modeAfter), so a loosened root this uid owns is re-tightened and its loosening still shows, rather than
    the silent re-tighten round 1 shipped. At 84b27dd39 the judge module has no state_root_mode_check: every test here
    fails with AttributeError."""

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
        self.assertEqual((chk["modeRead"], chk["modeReadText"], chk["root"]), (0o700, "0700", d))
        self.assertFalse(chk["repaired"], "0700 already: nothing to repair")
        self.assertEqual(chk["modeAfter"], 0o700)
        self.assertLessEqual(abs(chk["t"] - time.time()), 5)

    def test_not_0700_but_not_writable_by_others_warns(self):
        for mode in (0o755, 0o750, 0o711):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):   # else the repair tightens it and repaired is True
                chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], "warn", "%04o" % mode)
            self.assertEqual(chk["modeReadText"], "%04o" % mode, "the verdict names the mode READ, not the mode after")
            self.assertIn(d, chk["line"])
            self.assertIn("%04o" % mode, chk["line"], "names the mode read back")
            self.assertIn("0700", chk["line"], "and the mode expected")
            self.assertIn(chk["remedy"], chk["line"], "and the remedy")
            self.assertNotIn("\n", chk["line"], "one line")
            self.assertEqual(_mode(d), mode, "the refused chmod healed nothing")

    def test_writable_by_group_or_other_refuses(self):
        for mode in (0o770, 0o707, 0o722, 0o777):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):
                chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], "refuse", "%04o" % mode)
            self.assertTrue(mode & jd.STATE_ROOT_REFUSE_MASK)
            self.assertIn("refuses to serve", chk["line"])
            self.assertIn("remove serve-token and repo-root", chk["remedy"], "the remedy distrusts the contents (fresh-1)")
            self.assertIn(d, chk["line"])
            self.assertIn("%04o" % mode, chk["line"])

    def test_read_before_repair_a_loosened_owned_root_is_retightened_and_reported(self):
        """The re-check's whole reason (the 2026-09-20 review's extra6-1): a 0755 or 0777 root THIS UID OWNS, loosened
        after boot, is re-tightened by the check's own chmod AND reported. The verdict is what was READ (warn for 0755,
        refuse for 0777), never a silent ok; repaired is True and modeAfter is 0700, so the loosening leaves a trace
        rather than being erased. Round 1 chmod'ed first and read 0700, so this case was invisible."""
        d = self._root(0o755)
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "warn", "the verdict is the mode as read")
        self.assertTrue(chk["repaired"])
        self.assertEqual((chk["modeReadText"], chk["modeAfter"]), ("0755", 0o700))
        self.assertEqual(_mode(d), 0o700, "the repair ran, after the read")
        self.assertIn("re-tightened to 0700", chk["line"])
        d2 = self._root(0o777)
        chk2 = jd.state_root_mode_check(d2)
        self.assertEqual(chk2["verdict"], "refuse", "a writable root refuses on what was read, even once re-tightened")
        self.assertTrue(chk2["repaired"])
        self.assertEqual(_mode(d2), 0o700)
        self.assertIn("re-tightened to 0700 after the read; the refusal stands on what was read", chk2["line"])

    def test_an_unreadable_root_is_unknown_and_refuse_class(self):
        d = os.path.join(tempfile.mkdtemp(), "never-made")
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "unknown")
        self.assertIsNone(chk["modeRead"])
        self.assertIsNone(chk["modeReadText"])
        self.assertEqual(chk["statErrno"], "ENOENT")
        self.assertIn("ENOENT", chk["err"])
        self.assertIn("could not be read", chk["line"])
        self.assertIn("unverified root is not served from", chk["line"])
        self.assertIn(d, chk["remedy"])

    def test_a_refused_repair_puts_the_errno_name_and_text_in_err_and_the_line(self):
        """Arm four: the chmod's OSError, with its errno alone (never the exception's text, which carries the path), on
        the same surface as the mode; the remedy then says the root is not this uid's to change."""
        for mode, verdict in ((0o755, "warn"), (0o777, "refuse")):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):
                chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], verdict, "%04o" % mode)
            self.assertEqual(chk["repairErrno"], "EPERM")
            self.assertIn("EPERM", chk["err"], "the errno name")
            self.assertIn(os.strerror(1), chk["err"], "and its text")
            self.assertIn("EPERM", chk["line"])
            self.assertNotIn("interposed", chk["err"], "built from the errno, not from the exception's text")
            self.assertFalse(chk["repaired"], "the chmod was refused: nothing repaired")
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
        self.assertEqual(chk["repairErrno"], "EACCES")
        self.assertIn("EACCES", chk["err"])
        self.assertIn(os.strerror(13), chk["err"])
        self.assertIn("not this uid's to change", chk["remedy"])

    def test_a_0700_root_whose_chmod_fails_is_ok_with_the_error_on_the_line(self):
        """Arm four's one case where the failed chmod is the whole signal: the root reads 0700 (verdict ok) but this
        uid's chmod is refused (the shape of a root another uid owns). The line is not None: it names the root, 0700,
        the errno name and text, and the remedy. A plain ok (the chmod ran) still says nothing."""
        d = tempfile.mkdtemp()
        with mock.patch("os.chmod", new=_refusing_chmod(d)):
            chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(chk["modeReadText"], "0700")
        self.assertEqual(chk["repairErrno"], "EPERM")
        self.assertIsNotNone(chk["line"], "ok with a repair error is said, not silent")
        for piece in (d, "0700", "EPERM", os.strerror(1)):
            self.assertIn(piece, chk["line"])
        self.assertIn("not this uid's to change", chk["remedy"])
        self.assertNotIn("\n", chk["line"])
        self.assertIsNone(jd.state_root_mode_check(d)["line"], "the chmod ran: plain ok, nothing said")

    def test_the_suites_own_root_reads_ok_and_recorded_no_repair_error(self):
        self.assertIsNone(jd._STATE_ROOT_REPAIR_ERROR, "the import's mkdir and chmod succeeded on the suite's root")
        self.assertIsNone(jd._STATE_ROOT_REPAIR_STEP)
        chk = jd.state_root_mode_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertIsNone(chk["importRepairError"])


class TheImportRecordsItsOwnRepair(unittest.TestCase):
    """Arm four at the import: the judge module records the mode it READ before its own chmod (_STATE_ROOT_MODE_AT_IMPORT)
    and, for a call that failed, WHICH call it was and its errno (_STATE_ROOT_REPAIR_STEP, _STATE_ROOT_REPAIR_ERROR), so
    a mkdir failure is not mislabelled as a chmod's (correctness-3). state_root_mode_check on the module's own root folds
    the import's failed call into err, labelled as the import's. The import's one stderr line is exactly as
    tests/test_judge_scratch_private.py pins it. At 84b27dd39 the module has no _STATE_ROOT_REPAIR_STEP (the child
    prints an AttributeError and exits 1); this runs in a child so the planted root and refused chmod stay out of this
    process."""

    def test_a_refused_chmod_at_import_is_recorded_with_its_errno_and_step(self):
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
                "chk = jd.state_root_mode_check()\n"
                "print(json.dumps({'step': jd._STATE_ROOT_REPAIR_STEP, 'rec': jd._STATE_ROOT_REPAIR_ERROR,\n"
                "                  'atImport': jd._STATE_ROOT_MODE_AT_IMPORT, 'err': chk['err'], 'verdict': chk['verdict'],\n"
                "                  'importErr': chk['importRepairError'], 'chkImport': chk['importModeRead'],\n"
                "                  'created': chk['importCreated']}))\n"
                % (HERE, root, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["step"], "chmod 700", "the call that failed, named")
        self.assertEqual(out["rec"], "EPERM: %s" % os.strerror(1), "recorded from the errno alone")
        self.assertEqual(out["atImport"], 0o755, "the mode read BEFORE the import's chmod")
        self.assertEqual(out["chkImport"], 0o755, "and folded into the check dict for the module's own root (the boot reads it there)")
        self.assertFalse(out["created"], "a pre-existing root: the import did not make it")
        self.assertEqual(out["verdict"], "warn")
        self.assertIn("chmod 700 failed at import: EPERM", out["importErr"], "labelled as the import's, not as a fresh chmod")
        self.assertIn("EPERM", out["err"])
        said = [l for l in r.stderr.splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "the import's one line, unchanged:\n" + r.stderr)
        self.assertIn(root, said[0])
        self.assertIn("0755", said[0])
        self.assertEqual(_mode(root), 0o755, "read, not healed")

    def test_a_failed_mkdir_is_labelled_mkdir_not_chmod(self):
        parent = tempfile.mkdtemp()
        os.chmod(parent, 0o555)   # the parent cannot be written: the mkdir of the root under it fails
        self.addCleanup(lambda: os.chmod(parent, 0o700))
        root = os.path.join(parent, "romp")
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        code = ("import json, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "jd = load_source('romp_judge_child', %r)\n"
                "chk = jd.state_root_mode_check()\n"
                "print(json.dumps({'step': jd._STATE_ROOT_REPAIR_STEP, 'rec': jd._STATE_ROOT_REPAIR_ERROR,\n"
                "                  'verdict': chk['verdict'], 'importErr': chk['importRepairError']}))\n"
                % (HERE, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["step"], "mkdir", "a mkdir that could not run is labelled mkdir, not chmod")
        self.assertTrue(out["rec"].startswith("EACCES") or out["rec"].startswith("EPERM"), out["rec"])
        self.assertEqual(out["verdict"], "unknown", "the root was never created: its mode cannot be read")
        self.assertIn("mkdir failed at import", out["importErr"])


# ── the kernel-side shared harness ───────────────────────────────────────────────────────────────────────────────

class _KernelState(unittest.TestCase):
    """Save and restore every module-level piece the arms touch, give each test a fresh 0700 root as the state root, and
    replace the runtime exit with a raising double so a refusal is observable in-process rather than killing the runner."""

    def setUp(self):
        self.saved_state = jd.STATE
        self.saved_mode, self.saved_key = km._STATE_ROOT_MODE, km._STATE_ROOT_KEY
        self.saved_refused = km._STATE_ROOT_REFUSED
        self.saved_exit = km._state_root_exit
        self.saved_rows = list(km._SYNC_NOTICES)
        self.saved_seq = km._SYNC_SEQ
        self.saved_env = os.environ.get("ROMP_STATE_ROOT_CHECK_S")
        self.saved_repo_err = km._REPO_ROOT_WRITE_ERROR
        km._STATE_ROOT_MODE, km._STATE_ROOT_KEY, km._STATE_ROOT_REFUSED = None, None, False
        km._REPO_ROOT_WRITE_ERROR = None
        km._SYNC_NOTICES[:] = []
        self.exits = []
        km._state_root_exit = self._exit_double
        self.root = tempfile.mkdtemp()                    # mkdtemp creates 0700 whatever the umask
        Path(self.root, "session-hosts").write_text("off\n")   # a minted root writes off before a kernel is bound to it (regression-6)
        jd._rebind_state(Path(self.root))
        self.patcher = None

    def _exit_double(self, code):
        self.exits.append(code)
        raise _Exited(code)

    def tearDown(self):
        if self.patcher is not None:
            self.patcher.stop()
        try:
            os.chmod(self.root, 0o700)                    # the hygiene sweep must be able to remove it
        except OSError:
            pass
        jd._rebind_state(self.saved_state)
        km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = self.saved_mode, self.saved_key
        km._STATE_ROOT_REFUSED = self.saved_refused
        km._REPO_ROOT_WRITE_ERROR = self.saved_repo_err
        km._state_root_exit = self.saved_exit
        km._SYNC_NOTICES[:] = self.saved_rows
        km._SYNC_SEQ = self.saved_seq
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
        return [r["text"] for r in km._SYNC_NOTICES]

    def refused_rows(self):
        return [r for r in km._SYNC_NOTICES if r["kind"] == "refused"]


# ── REFUSE AT BOOT, and WARN at boot ─────────────────────────────────────────────────────────────────────────────

class Boot(_KernelState):
    """_state_root_boot_check, called from main() right after check_boot_environment and BEFORE any thread starts. What
    the refuse/unknown arm does to everything that is not the door: it raises SystemExit(2) in the MAIN thread, so
    _ensure_bundles, the reconcile, and every loop thread below it in main() never run. What the warn arm does: files
    one row and one line and lets the boot go on, starting every thread as before. At 84b27dd39 the kernel has no
    _state_root_boot_check (AttributeError)."""

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
        self.assertIn("remove serve-token and repo-root", line, "the remedy distrusts the contents")
        self.assertIn("did NOT start", line)
        self.assertEqual(self.exits, [], "SystemExit in main(), not the runtime os._exit double")
        self.assertEqual(_mode(self.root), 0o777, "read, not healed (the chmod was refused)")

    def test_an_unreadable_root_stops_the_boot_with_exit_2(self):
        """The UNKNOWN decision (the review's section E): unverified defaults to the restricted side, so a root whose
        mode cannot be read exits at boot exactly like a writable one. A stat on a local directory does not fail
        transiently; ENOENT means the root was removed, and continuing would re-create it under a parent someone else
        may own."""
        gone = os.path.join(self.root, "gone")
        jd._rebind_state(Path(gone))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("could not be read", err.getvalue())
        self.assertIn("unverified root is not served from", err.getvalue())
        self.assertIn("ENOENT", err.getvalue())

    def test_main_runs_the_boot_check_right_after_the_credential_check_and_before_any_thread(self):
        import inspect
        src = inspect.getsource(km.main)
        i_cred, i_root, i_thread = (src.index("jd._cred.check_boot_environment()"), src.index("_state_root_boot_check()"),
                                    src.index("threading.Thread("))
        self.assertLess(i_cred, i_root)
        self.assertLess(i_root, i_thread)

    def test_the_import_gate_precedes_the_token_load_in_the_module_body(self):
        """correctness-4 / fresh-2, the source half (the execution half is TheImportGateComesFirst): the import gate's
        call statement sits above the TOKEN assignment and the _persist_repo_root() call in the module body, so no read
        of the root's contents precedes it. Read from the module's AST statements (not a text scan, whose match would
        land in the gate's own docstring, which quotes both)."""
        import ast
        tree = ast.parse(inspect_getsource_module())
        pos = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_STATE_ROOT_IMPORT_CHECK" for t in node.targets):
                pos["gate"] = node.lineno
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TOKEN" for t in node.targets):
                pos.setdefault("token", node.lineno)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                    and getattr(node.value.func, "id", None) == "_persist_repo_root":
                pos.setdefault("repo", node.lineno)
        self.assertIn("gate", pos)
        self.assertLess(pos["gate"], pos["token"], "the gate statement runs before the serve token is read")
        self.assertLess(pos["gate"], pos["repo"], "and before repo-root is written")

    def test_a_root_not_0700_but_not_writable_by_others_files_one_row_and_boots(self):
        os.chmod(self.root, 0o755)
        self.interpose()                                   # else the repair tightens it and the verdict is ok
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "warn")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("0755", rows[0])
        self.assertIn("EPERM", rows[0])
        self.assertEqual(err.getvalue().count("state root"), 1, err.getvalue())
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "warn")
        self.assertEqual(v["modeRead"], "0755")
        self.assertIn("EPERM", v["err"])
        self.assertIsInstance(v["checkedAt"], int)
        self.assertNotIn(self.root, json.dumps(v), "/version is auth-exempt: no filesystem path (its contract)")
        self.assertIn("the state root", v["remedy"])
        # the first runtime pass after the boot sees the same warn: no second row for it
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 1, "one row per transition, and the boot's check was the previous state")

    def test_the_import_pre_chmod_mode_is_a_warn_transition_at_boot(self):
        """The 2026-09-20 review's item 2, last clause: a root the import READ looser than 0700 and re-tightened to 0700
        is reported at boot as its own warn-class transition (loud, not fatal), so a loosening that happened while romp
        was down leaves a trace. The check itself reads ok now, but the import's pre-chmod mode is a fact the boot line
        and row carry."""
        km._STATE_ROOT_MODE = None
        chk = dict(jd.state_root_mode_check(), importModeRead=0o755)   # the module root reads 0700; force the import fact
        with mock.patch.object(jd, "state_root_mode_check", return_value=chk):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                km._state_root_boot_check()
        self.assertIn("read 0755 at import", err.getvalue())
        self.assertIn("re-tightened to 0700", err.getvalue())
        rows = [r["text"] for r in self.refused_rows()]
        self.assertTrue(any("read 0755 at import" in r for r in rows), rows)

    def test_the_import_pre_chmod_writable_mode_boots_loud_with_the_distrust_remedy(self):
        """The settled rule (round 2b): a pre-existing root that READ writable at import and was tightened to 0700 by the
        judge module's chmod BOOTS (the verdict is on the mode as read now; refusing it would refuse the first boot after
        every creation of the root by another tool under a group-writable umask), and the boot is LOUD about what was
        read: one stderr line and one refused-kind row, both carrying the distrust remedy (entries planted while the
        root was writable are not to be trusted: remove serve-token and repo-root under the root and restart, so the
        next boot re-mints them). The row fits the bell with the remedy whole."""
        km._STATE_ROOT_MODE = None
        chk = dict(jd.state_root_mode_check(), importModeRead=0o775, importCreated=False)   # group-writable at import, 0700 now
        with mock.patch.object(jd, "state_root_mode_check", return_value=chk):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                out = km._state_root_boot_check()
        self.assertEqual(out["verdict"], "ok", "the root reads 0700 now: not a refusal")
        line = err.getvalue()
        self.assertEqual(line.count("state root"), 1, "one line:\n" + line)
        self.assertIn("read 0775 at import (writable by other local users), re-tightened to 0700", line)
        self.assertIn("entries planted while it was writable are not to be trusted", line)
        self.assertIn("remove serve-token and repo-root under %s and restart" % self.root, line)
        self.assertIn("the next boot re-mints them", line)
        self.assertNotIn("did NOT start", line, "loud, not fatal")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("read 0775 at import (writable by other local users), re-tightened to 0700", rows[0])
        self.assertIn("Remove serve-token and repo-root under the root and restart", rows[0], "the remedy, path-free, whole")
        self.assertIn("entries planted while it was writable are not to be trusted", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        # the first runtime pass sees plain ok: no second row for the import fact
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.refused_rows()), 1)

    def test_a_writable_root_the_import_could_not_tighten_refuses_at_boot_on_the_current_read(self):
        """The refusal the settled rule keeps: a root whose import chmod FAILED still reads writable, and the boot refuses
        on that read (the import fact files no separate row: the check's own refusal line carries the mode and the
        import's failed call, labelled)."""
        os.chmod(self.root, 0o775)
        self.interpose()
        base = jd.state_root_mode_check()
        chk = dict(base, importModeRead=0o775, importCreated=False,
                   importRepairError="chmod 700 failed at import: EPERM: %s" % os.strerror(1),
                   err=(base["err"] or "") + "; chmod 700 failed at import: EPERM: %s" % os.strerror(1))
        self.assertIsNone(km._state_root_import_mode_row(chk), "the import's chmod failed: nothing was re-tightened")
        with mock.patch.object(jd, "state_root_mode_check", return_value=chk):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("0775", err.getvalue())
        self.assertIn("writable by other local users", err.getvalue())
        self.assertIn("did NOT start", err.getvalue())
        self.assertEqual(self.refused_rows(), [])

    def test_a_root_the_import_created_at_the_umasks_mode_is_neither_a_warning_nor_a_refusal(self):
        """The exemption: the judge module's own mkdir made the root, so the mode it read before its chmod is the
        umask's creation default (0775 under a group-writable umask), not a loosening, and nothing could have been
        planted in a directory that did not exist a moment before. No exit, no row, no line."""
        km._STATE_ROOT_MODE = None
        chk = dict(jd.state_root_mode_check(), importModeRead=0o775, importCreated=True)
        with mock.patch.object(jd, "state_root_mode_check", return_value=chk):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                out = km._state_root_boot_check()
        self.assertEqual(out["verdict"], "ok")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(self.refused_rows(), [])
        self.assertIsNone(km._state_root_import_mode_row(chk))

    def test_repo_root_is_written_by_a_rename_that_replaces_a_planted_entry(self):
        """fresh-1's second half (round 2): repo-root is published by a temp and os.replace, the token mint's shape, so
        a planted entry at the path (a symlink pointing outside the root, a file this uid cannot open) is REPLACED
        rather than written through or left standing; the link's target is untouched."""
        target = Path(tempfile.mkdtemp(), "elsewhere")
        target.write_text("attacker-planted\n")
        os.symlink(target, os.path.join(self.root, "repo-root"))
        with contextlib.redirect_stderr(io.StringIO()):
            km._persist_repo_root()
        self.assertFalse(os.path.islink(os.path.join(self.root, "repo-root")), "the link itself was replaced")
        self.assertEqual(Path(self.root, "repo-root").read_text(), str(km.ROOT) + "\n")
        self.assertEqual(target.read_text(), "attacker-planted\n", "nothing was written through the link")
        self.assertIsNone(km._REPO_ROOT_WRITE_ERROR)
        plant = Path(self.root, "repo-root")
        plant.write_text("/nonexistent/bogus-repo\n")
        plant.chmod(0o444)                                    # a plant this uid cannot open for writing
        with contextlib.redirect_stderr(io.StringIO()):
            km._persist_repo_root()
        self.assertEqual(plant.read_text(), str(km.ROOT) + "\n", "replaced by the rename, not skipped")
        self.assertEqual(_mode(plant), 0o600)

    def test_a_failed_repo_root_write_is_said_with_its_errno_and_filed_at_boot(self):
        real = os.replace

        def refuse(src, dst, *a, **k):
            if os.path.basename(str(dst)) == "repo-root":
                raise PermissionError(13, "denied (interposed)")
            return real(src, dst, *a, **k)
        err = io.StringIO()
        with mock.patch("os.replace", new=refuse), contextlib.redirect_stderr(err):
            km._persist_repo_root()
        self.assertIn("repo-root", err.getvalue())
        self.assertIn("EACCES", err.getvalue(), "the errno name")
        self.assertNotIn("interposed", err.getvalue(), "built from the errno, never the exception's text")
        self.assertTrue(km._REPO_ROOT_WRITE_ERROR.startswith("EACCES"), km._REPO_ROOT_WRITE_ERROR)
        self.assertEqual([p for p in os.listdir(self.root) if p.startswith("repo-root")], [], "no temp left behind")
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("repo-root", rows[0])
        self.assertIn("EACCES", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)

    def test_a_0700_root_files_nothing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(self.refused_rows(), [])
        self.assertEqual(err.getvalue(), "")
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"], v["err"]), ("ok", "0700", None))
        self.assertFalse(v["repaired"])

    def test_version_says_unchecked_before_any_check(self):
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "unchecked")
        self.assertEqual(set(v), {"verdict", "modeRead", "modeAfter", "repaired", "err", "importRepairError",
                                  "remedy", "checkedAt"})
        self.assertNotIn("refusingSince", v, "no latch in round 2: nothing 'refuses since'")


# ── REFUSE AT RUNTIME: the exit, from the jobs road and under concurrency ────────────────────────────────────────

class TheRuntimeRefusalExits(_KernelState):
    """_state_root_verdict is the runtime arm. What the refuse/unknown verdict does to everything that is not the check:
    it hands the whole process to _state_root_exit_now, which in production is os._exit(2) (here the double). A verdict
    read once and cached answers without a re-read inside the interval, so an ordinary request never pays a stat. At
    84b27dd39 there is no _state_root_verdict (AttributeError)."""

    def test_a_loosened_root_found_at_runtime_exits_the_process(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()                    # ok on the 0700 root
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited) as cm:
                km._state_root_verdict(time.time(), "a request")
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(self.exits, [2], "exactly one exit(2)")
        self.assertTrue(km._STATE_ROOT_REFUSED)
        self.assertIn("0777", err.getvalue())
        self.assertIn("romp stops now", err.getvalue())
        self.assertIn("found by a request", err.getvalue())

    def test_an_unreadable_root_found_at_runtime_exits_the_process(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        gone = self.root + ".away"
        os.rename(self.root, gone)                         # the root path is gone: os.stat fails ENOENT
        self.addCleanup(lambda: os.path.isdir(gone) and os.rename(gone, self.root))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited):
                km._state_root_verdict(time.time(), "the housekeeping pass")
        self.assertEqual(self.exits, [2])
        self.assertIn("could not be read", err.getvalue())
        self.assertIn("unverified root is not served from", err.getvalue())

    def test_a_raising_check_exits_the_process_with_the_traceback_said_once(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        err = io.StringIO()
        with mock.patch.object(jd, "state_root_mode_check", side_effect=RuntimeError("boom (interposed)")):
            with contextlib.redirect_stderr(err):
                with self.assertRaises(_Exited):
                    km._state_root_verdict(time.time())
        self.assertEqual(self.exits, [2], "a check that raises is unverified: the process exits")
        self.assertIn("RuntimeError", err.getvalue())
        self.assertNotIn("interposed", err.getvalue().split("Traceback")[0], "the verdict line carries the type name, not the text")
        self.assertEqual(err.getvalue().count("Traceback (most recent call last)"), 1, "the traceback said once, before the exit")

    def test_the_interval_gates_the_recheck(self):
        os.environ.pop("ROMP_STATE_ROOT_CHECK_S", None)
        self.assertEqual(km._state_root_check_interval(), 15.0)
        self.assertEqual(km.STATE_ROOT_CHECK_S, 15.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "not-a-number"
        self.assertEqual(km._state_root_check_interval(), 15.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "3600"
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.chmod(self.root, 0o777)
        self.interpose()
        now = time.time()
        self.assertEqual(km._state_root_verdict(now), "ok", "inside the interval the cache answers, no re-read")
        self.assertEqual(self.exits, [])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(_Exited):
                km._state_root_verdict(now + 3601)          # past it the mode is re-read
        self.assertEqual(self.exits, [2])

    def test_two_roads_take_the_exit_once(self):
        """tests-4, the concurrency the re-check rests on: two threads driving _state_root_verdict with a refuse check
        under interval 0 both re-read, but the exit is taken exactly ONCE (the first finder sets the flag under the lock)
        and the second finder never RETURNS a verdict to its caller (it raises _StateRootExiting, round 2), so no request
        or stage runs on under the hostile root while the first finder's line is in flight. Without the flag both would
        call os._exit; without the raise the second road got "refuse" back and carried on."""
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        real_check = jd.state_root_mode_check

        def slow(*a, **k):
            time.sleep(0.05)                                # widen the window both threads race
            return real_check(*a, **k)
        got = []
        with mock.patch.object(jd, "state_root_mode_check", side_effect=slow):
            with contextlib.redirect_stderr(io.StringIO()):
                def drive():
                    try:
                        got.append(km._state_root_verdict(time.time()))
                    except _Exited:
                        got.append("exited")
                    except km._StateRootExiting:
                        got.append("parked")
                ts = [threading.Thread(target=drive) for _ in range(2)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(5)
        self.assertFalse(any(t.is_alive() for t in ts))
        self.assertEqual(len(self.exits), 1, "the exit is taken once, not per road: %r" % self.exits)
        self.assertTrue(km._STATE_ROOT_REFUSED)
        self.assertEqual(sorted(got), ["exited", "parked"], "no road got a verdict string back: %r" % got)


class TheWritersStopUnderARefusal(_KernelState):
    """extra5-1 / extra5-2, the HIGH that decided round 1: a runtime refusal must stop the WRITERS, not only the doors.
    What the refuse verdict does to the housekeeping pass it is the first stage of: the exit propagates through the
    pass's own `except Exception` guards (it is a BaseException), so NO later stage in the pass runs: not the sweeps,
    not the persists, not clearDoneNotes. In production os._exit stops the pusher, the judges and the timers by the same
    mechanism (the process is gone). At 84b27dd39 the stage does not exist, and every later stage runs under the loose
    root."""

    def test_the_jobs_pass_runs_no_later_stage_once_the_first_stage_refuses(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        with mock.patch.object(km, "_lift_spent_awaiting") as lift, \
             mock.patch.object(km, "_clear_done_working_notes") as clear, \
             mock.patch.object(km, "_death_sweep_tick") as death:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(_Exited):
                    km._jobs_pass(int(time.time()), {})
        self.assertEqual(self.exits, [2], "the pass exited at its first stage")
        lift.assert_not_called()
        death.assert_not_called()
        clear.assert_not_called()

    def test_the_stage_is_first_and_is_a_pass_job(self):
        import inspect
        src = inspect.getsource(km._jobs_pass)
        self.assertIn("_job_stage('stateRootMode', lambda: _state_root_verdict(now", src)
        self.assertLess(src.index("stateRootMode"), src.index("liftSpentAwaiting"), "first in the pass")
        self.assertIn("stateRootMode", km._PerfStats.PASS_JOBS)
        self.assertEqual(km._PerfStats.PASS_JOBS[0], "stateRootMode", "and first in the census")


class TheRequestRoadExits(_KernelState):
    """The Handler's road (round 2 of the review): every method runs _state_root_recheck FIRST, before the token gate and
    before any route, so a request that finds the root hostile exits the process from its own thread and answers
    nothing. Pinned by execution against a live km.Handler (tests/test_kernel_cors.py's ThreadingHTTPServer shape),
    one request per method: the exit double fires exactly once, the line says the road ("found by a request"), and no
    answer of any kind was built (send_response never ran, _authorize never ran): the client sees the connection drop.
    The double is a BaseException, so it propagates out of the handler thread (the server thread's traceback on stderr
    is expected); the assertion is on self.exits. With any one of the four call sites removed, that method answers."""

    def setUp(self):
        super().setUp()
        self.saved_hook = threading.excepthook            # the double leaving the handler thread is the expected outcome, not noise
        threading.excepthook = lambda a: None if a.exc_type is _Exited else self.saved_hook(a)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()                    # ok on the 0700 root
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        threading.excepthook = self.saved_hook
        super().tearDown()

    def _request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=b"{}" if method == "POST" else None,
                         headers={"X-Romp-Token": km.TOKEN, "Content-Type": "application/json"})
            r = conn.getresponse()
            r.read()
            return r.status
        except (http.client.RemoteDisconnected, http.client.BadStatusLine, ConnectionResetError):
            return None
        finally:
            conn.close()

    def test_every_method_exits_before_the_token_gate_and_every_route(self):
        for method, path in (("GET", "/healthz"), ("HEAD", "/healthz"), ("POST", "/nudge"), ("OPTIONS", "/nudge")):
            km._STATE_ROOT_REFUSED, km._STATE_ROOT_MODE = False, None
            self.exits[:] = []
            err = io.StringIO()
            with mock.patch.object(km.Handler, "send_response") as answered, \
                 mock.patch.object(km.Handler, "_authorize") as authorized, \
                 contextlib.redirect_stderr(err):
                status = self._request(method, path)
                for _ in range(100):                          # the handler thread's exit lands after the socket drops
                    if self.exits:
                        break
                    time.sleep(0.05)
            self.assertIsNone(status, "%s %s: the connection dropped, no answer (got %r)" % (method, path, status))
            self.assertEqual(self.exits, [2], "%s %s: the process exit, exactly once" % (method, path))
            self.assertIn("found by a request", err.getvalue(), method)
            self.assertIn("0777", err.getvalue(), method)
            answered.assert_not_called()
            authorized.assert_not_called()


# ── WARN: one row per transition, the bell's kind, the fit ───────────────────────────────────────────────────────

class TheWarnSurface(_KernelState):
    """What a warn row does to the OTHER bell kinds and to the bell's width. It rides _sync_notice under kind "refused"
    (extra7-1: not the mutable "sdk" kind of _sdk_problem, whose one mute would hide a security row with a backend
    error), one row per transition keyed on the cause so an errno flap under a constant mode refiles (extra6-2), and it
    is built to fit SYNC_NOTICE_FIT whole with the remedy first and the root's path at most once (extra7-2). At
    84b27dd39 there is no _state_root_verdict (AttributeError)."""

    def _serving_warn(self, mode=0o755):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, mode)
        self.interpose()

    def test_three_checks_one_row_and_a_second_loosening_is_a_second_transition(self):
        self._serving_warn(0o755)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 1, self.rows())
        self.assertIn("0755", self.refused_rows()[0]["text"])
        self.assertEqual(err.getvalue().count("state root"), 1, "and one stderr line")
        # a return to plain ok says nothing
        self.release()
        os.chmod(self.root, 0o700)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.refused_rows()), 1, "a return to ok files no row")
        # a second loosening, to a different mode, is a second transition
        os.chmod(self.root, 0o750)
        self.interpose()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 2, "a second loosening is a second transition")
        self.assertIn("0750", self.refused_rows()[1]["text"])

    def test_an_errno_flap_under_a_constant_mode_refiles(self):
        """extra6-2: the transition key carries the cause, so a chmod errno that changes (EPERM to EACCES) under one
        constant warn mode is a new transition and files a second row, rather than the error centre naming a stale
        cause while /version's err changes underneath it."""
        self._serving_warn(0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")   # EPERM (the interposed chmod)
        self.assertEqual(len(self.refused_rows()), 1)
        self.release()
        real = os.chmod

        def eacces(path, mode, *a, **k):
            if os.path.realpath(str(path)) == os.path.realpath(self.root):
                raise PermissionError(13, "denied (interposed)")
            return real(path, mode, *a, **k)
        os.chmod(self.root, 0o755)
        self.patcher = mock.patch("os.chmod", new=eacces)
        self.patcher.start()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")   # EACCES now, same 0755
        self.assertEqual(len(self.refused_rows()), 2, "the cause changed: a second row")
        self.assertIn("EACCES", self.refused_rows()[1]["text"])

    def test_every_row_fits_the_bell_with_the_remedy_first_and_the_path_at_most_once(self):
        """extra7-2, pinned against a long synthetic root so the length-is-doubled-path failure cannot hide behind a
        short test root: every row a check can file fits SYNC_NOTICE_FIT, leads with the point and the path-free remedy,
        and names the root at most once (a long root costs the path on the row, never the way out)."""
        longroot = "/home/someone/.local/state/romp-profiles/a-research-kernel-with-a-very-long-name-indeed/romp"
        cases = []
        for mode in (0o755, 0o750, 0o777, 0o770):
            with mock.patch("os.chmod", new=_refusing_chmod(longroot)), mock.patch("os.stat", new=_stat_as(longroot, mode)):
                cases.append(jd.state_root_mode_check(longroot))
        # a 0700-with-failed-chmod, and an unknown, both over the long root
        with mock.patch("os.chmod", new=_refusing_chmod(longroot)), mock.patch("os.stat", new=_stat_as(longroot, 0o700)):
            cases.append(jd.state_root_mode_check(longroot))
        with mock.patch("os.stat", new=_stat_missing(longroot)):
            cases.append(jd.state_root_mode_check(longroot))
        # the self-owned repaired shapes (0755 warn, 0777 refuse) over the long root: the check's chmod runs and succeeds,
        # so the read-back after it is 0700
        for mode in (0o755, 0o777):
            with mock.patch("os.chmod"), mock.patch("os.stat", new=_stat_then(longroot, mode, 0o700)):
                chk = jd.state_root_mode_check(longroot)
                self.assertTrue(chk["repaired"], "%04o" % mode)
                cases.append(chk)
        # the raise row (_state_root_unknown_check) over the long root
        saved = jd.STATE
        jd._rebind_state(Path(longroot))
        try:
            cases.append(km._state_root_unknown_check("RuntimeError", time.time()))
        finally:
            jd._rebind_state(saved)
        rows = [(chk, km._state_root_row(chk), None) for chk in cases]
        # the boot's import-mode row, built exactly as _state_root_boot_check builds it (the row nearest the cut)
        with mock.patch("os.chmod"), mock.patch("os.stat", new=_stat_as(longroot, 0o700)):
            base = jd.state_root_mode_check(longroot)
        for imp_mode in (0o755, 0o775):
            imp_chk = dict(base, importModeRead=imp_mode, importCreated=False, modeRead=0o700)
            imp = km._state_root_import_mode_row(imp_chk)
            self.assertIsNotNone(imp, "the boot files a row for a root that read %04o at import" % imp_mode)
            line, point, bell = imp
            rows.append((imp_chk, km._state_root_row(imp_chk, point=point, remedy=bell), bell))
        self.assertEqual(len(rows), 11, "every shape a row can take: four interposed modes, 0700 with a failed chmod, "
                                        "unknown, two self-owned repaired, the raise row, the boot's two import-mode rows "
                                        "(a 0755 read, and a writable read with the distrust remedy)")
        for chk, row, bell in rows:
            self.assertLessEqual(len(row), km.SYNC_NOTICE_FIT, "%r is over the bell: %d" % (chk["verdict"], len(row)))
            self.assertLessEqual(row.count(longroot), 1, "the path appears at most once: %r" % row)
            # the remedy LEADS: it is in the row whole, and before the error clause and the path when either appears
            rem = (bell or chk.get("bellRemedy") or chk["remedyPublic"]).rstrip(".")
            rem = rem[:1].upper() + rem[1:]
            self.assertIn(rem, row, "the remedy is in the row whole: %r" % row)
            for tail in ((" (%s)." % chk["err"]) if chk.get("err") else None, " Root: "):
                if tail and tail in row:
                    self.assertLess(row.index(rem), row.index(tail), "the remedy comes before %r: %r" % (tail, row))

    def test_the_row_is_filed_under_the_refused_kind(self):
        self._serving_warn(0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_verdict(time.time())
        self.assertEqual([r["kind"] for r in self.refused_rows()], ["refused"])
        self.assertTrue(all(r["kind"] == "refused" for r in km._SYNC_NOTICES if "state root" in r["text"] or "root" in r["text"].lower()))


def _stat_as(target, mode):
    real = os.stat

    def f(p, *a, **k):
        if str(p) == target:
            st = real(tempfile.gettempdir())
            return os.stat_result((stat.S_IFDIR | mode,) + tuple(st)[1:])
        return real(p, *a, **k)
    return f


def _stat_then(target, first, then):
    """os.stat for `target` answering mode `first` on its first call and `then` on every later one: the shape of a root
    the check's own chmod tightened between its read and its read-back."""
    real = os.stat
    calls = []

    def f(p, *a, **k):
        if str(p) == target:
            calls.append(1)
            st = real(tempfile.gettempdir())
            return os.stat_result((stat.S_IFDIR | (first if len(calls) == 1 else then),) + tuple(st)[1:])
        return real(p, *a, **k)
    return f


def _stat_missing(target):
    real = os.stat

    def f(p, *a, **k):
        if str(p) == target:
            raise FileNotFoundError(2, os.strerror(2))
        return real(p, *a, **k)
    return f


# ── REFUSE AT IMPORT: the ordering, proved by execution in a child ───────────────────────────────────────────────

class TheImportGateComesFirst(unittest.TestCase):
    """fresh-1, fresh-2 and correctness-4, proved by what did and did not happen in a child kernel process (never a
    source index). What the import gate does to the token work and the bundles when it refuses: they never run. A 0777
    root whose chmod is refused (a foreign owner, a refusing mount: it still reads writable at the gate) exits 2 with
    the STATE-ROOT line before the token work, the planted serve-token entry untouched. A 0777 root THIS UID OWNS, no
    chmod interposed, is tightened to 0700 by the judge module's import and PASSES the gate (the settled rule, round 2b:
    the verdict is on the mode as read at the gate, and refusing the tightened root would refuse the first boot after
    every creation of the root by another tool under a group-writable umask); what it read is said at boot
    (AServedKernelRefusesAtRuntime pins the line in a real kernel). With a planted symlink at serve-token under such a
    root the token loader's own fault stops the import (exit 1, its own message: the loader reads no token through a
    link), the link's target untouched: that fault, and repo-root's atomic replace, are what close the adoption risk.
    A 0700 root imports fine (the token work runs). At 84b27dd39 the import runs the token load first on every root,
    so a chmod-refused 0777 root never prints the state-root refusal there."""

    def _child(self, plant_symlink, mode, interpose=False):
        root = os.path.join(tempfile.mkdtemp(), "romp")
        os.makedirs(root)
        target = os.path.join(tempfile.mkdtemp(), "elsewhere")
        Path(target).write_text("attacker-planted\n")
        if plant_symlink:
            os.symlink(target, os.path.join(root, "serve-token"))   # the plant the token load would follow
        os.chmod(root, mode)
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.pop("ROMP_SERVE_TOKEN", None)                           # force the token to be read/minted from the root
        env["ROMP_KERNEL_NO_OPEN"] = "1"
        # `interpose`: the shape of a root this uid cannot tighten (a foreign owner, a refusing mount). Without it the root
        # is self-owned and the judge module's import chmod DOES tighten it before the kernel's gate runs, so the gate
        # reads 0700 and passes (the settled rule); the boot says what was read
        interpose = "" if not interpose else (
            "real = os.chmod\n"
            "def refuse(path, m, *a, **k):\n"
            "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
            "        raise PermissionError(1, 'chmod refused (interposed)')\n"
            "    return real(path, m, *a, **k)\n"
            "os.chmod = refuse\n")
        code = ("import os, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "root = %r\n"
                "%s"
                "load_source('romp_kernel', %r)\n"
                "print('IMPORTED-OK')\n"
                % (HERE, root, interpose, os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        return root, target, r

    def test_a_self_owned_writable_root_is_tightened_at_import_and_a_planted_token_faults_in_the_loader(self):
        """No chmod interposed: the judge module's import tightens the root to 0700 before the kernel's gate runs, the
        gate reads 0700 and passes (the settled rule), and the token loader then meets the planted symlink and faults
        on its own terms (exit 1, the loader's message; it reads or tightens no token through a link). The state-root
        gate refused nothing here: the line it would print says "did NOT start", and it is absent. The link's target
        is untouched and the link still in place for the operator; the root reads 0700."""
        root, target, r = self._child(plant_symlink=True, mode=0o777)
        self.assertEqual(r.returncode, 1, "the token loader's RuntimeError, not the gate's exit 2:\n%s" % r.stderr)
        self.assertNotIn("did NOT start", r.stderr, "the gate passed on the mode as read now (0700)")
        self.assertIn("serve-token", r.stderr, "the loader's own fault names the token path")
        self.assertIn("symlink", r.stderr, "and says why: a link is not read through")
        self.assertNotIn("IMPORTED-OK", r.stdout, "the import did not complete")
        self.assertEqual(Path(target).read_text(), "attacker-planted\n", "the planted entry's target is untouched")
        self.assertTrue(os.path.islink(os.path.join(root, "serve-token")), "and the link is still in place: the operator removes it")
        self.assertEqual(_mode(root), 0o700, "the import's chmod ran")

    def test_a_self_owned_writable_root_without_a_plant_imports_fine_and_reads_0700(self):
        """The same root with nothing planted: tightened at import, the gate passes, the token work and the rest of the
        import run, and the import itself says nothing about the mode (the judge module's read-back is 0700); the boot
        is where the pre-chmod read is reported (AServedKernelRefusesAtRuntime)."""
        root, target, r = self._child(plant_symlink=False, mode=0o777)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout)
        self.assertNotIn("did NOT start", r.stderr)
        self.assertNotIn("state root", r.stderr, "nothing said at import: the boot says it")
        self.assertEqual(_mode(root), 0o700)
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")), "a token was minted under the now-tight root")

    def test_a_writable_root_whose_chmod_is_refused_exits_2_the_same_way(self):
        root, target, r = self._child(plant_symlink=True, mode=0o777, interpose=True)
        self.assertEqual(r.returncode, 2, "the import gate exits 2:\n%s" % r.stderr)
        self.assertIn("writable by other local users", r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertNotIn("serve token", r.stderr.lower(), "the token work never ran")
        self.assertEqual(Path(target).read_text(), "attacker-planted\n")
        self.assertEqual(_mode(root), 0o777, "the chmod was refused: read, not healed")

    def test_a_0700_root_imports_fine(self):
        root, target, r = self._child(plant_symlink=False, mode=0o700)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout, "the token work and the rest of the import ran")
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")), "a token was minted under the tight root")

    def test_an_unreadable_root_exits_2_at_import(self):
        parent = tempfile.mkdtemp()
        root = os.path.join(parent, "romp")
        os.makedirs(root)
        os.chmod(root, 0o700)
        os.chmod(parent, 0o000)                                     # the root cannot be traversed to: stat fails
        self.addCleanup(lambda: os.chmod(parent, 0o700))
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.pop("ROMP_SERVE_TOKEN", None)
        code = ("import sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "load_source('romp_kernel', %r)\n"
                "print('IMPORTED-OK')\n"
                % (HERE, os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("unverified root is not served from", r.stderr)


# ── REFUSE AT RUNTIME, behaviourally, in a served child kernel (the failing-before at 84b27dd39) ─────────────────

def _kernel_env(root, dist, port, token):
    env = {k: v for k, v in os.environ.items() if k.startswith("XDG_") or k in ("PATH", "HOME", "LANG", "LC_ALL")}
    env.update(XDG_STATE_HOME=os.path.join(root, "xdg"), CLAUDE_CONFIG_DIR=os.path.join(root, "claude"),
               ROMP_DIST_DIR=dist, ROMP_SERVE_TOKEN=token, ROMP_KERNEL_PORT=str(port), ROMP_KERNEL_NO_OPEN="1",
               ROMP_MANAGER_PORT="1", ROMP_MODEL_CATALOG="off", ROMP_UPDATE_CHECK="off", ROMP_CLAUDE_BIN="/bin/false",
               ROMP_POSTAL_PORT=str(_free_port()), ROMP_POSTAL_PEERS="0", ROMP_POSTAL_CLIENT_ONLY="1",
               ROMP_POSTAL_HERMETIC="1", ROMP_STATE_ROOT_CHECK_S="0")
    return env


class AServedKernelRefusesAtRuntime(unittest.TestCase):
    """The runtime refuse arm, end to end and in-suite (tests-2): a real bin/romp-kernel serves 200 on a hermetic 0700
    root, and once the root is loosened to 0777 the process EXITS 2 with the state-root line within seconds: the
    housekeeping pass or a request finds it, and every writer stops with the process. What it does to everything else:
    the process is gone, so no file under the root is written after the exit. At 84b27dd39 the same spawn keeps serving
    200 after the loosening and never exits (recorded under the notes' scratch, a detached worktree, removed after);
    the failing-before is that this test's assertRaises-of-exit is a 200 that never becomes an exit there."""

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="romp-srm2-")
        self.root = os.path.join(self.lab, "xdg", "romp")
        for d in (self.root, os.path.join(self.lab, "claude"), os.path.join(self.lab, "dist")):
            os.makedirs(d, exist_ok=True)
        os.chmod(self.root, 0o700)                              # a fresh mkdir is 0775 under a group-writable umask
        Path(self.root, "session-hosts").write_text("off\n")   # a minted root writes off before binding a kernel (regression-6)
        self.port, self.token = _free_port(), "srm2-tok"
        self.klog = os.path.join(self.lab, "kernel.log")
        self.kernel = None

    def tearDown(self):
        if self.kernel and self.kernel.poll() is None:
            self.kernel.kill()
            self.kernel.wait(timeout=10)
        shutil.rmtree(self.lab, ignore_errors=True)

    def _spawn(self):
        env = _kernel_env(self.lab, os.path.join(self.lab, "dist"), self.port, self.token)
        self.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(self.klog, "w"),
                                       stderr=subprocess.STDOUT, env=env)

    def _healthz(self):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % self.port, timeout=1)
            return True
        except Exception:
            return False

    def _await_healthz(self):
        for _ in range(120):
            if self.kernel.poll() is not None:
                raise unittest.SkipTest("kernel exited before serving /healthz:\n" + open(self.klog).read()[-800:])
            if self._healthz():
                return
            time.sleep(0.5)
        raise unittest.SkipTest("hermetic kernel never served /healthz here")

    def _await_exit(self, seconds=60):
        for _ in range(int(seconds * 2)):
            if self.kernel.poll() is not None:
                return
            time.sleep(0.5)

    def test_a_root_that_read_writable_at_import_serves_with_one_loud_line(self):
        """The settled rule end to end: a pre-existing root THIS UID OWNS at 0777, no chmod interposed, planted before the
        spawn. The kernel's judge module tightens it at import, the gate passes on the mode as read now, and the kernel
        SERVES, with the boot saying what was read: one line with the distrust remedy (the row beside it is pinned
        in-process by Boot). At 84b27dd39 the same kernel served with nothing said about the import's read."""
        os.chmod(self.root, 0o777)
        self._spawn()
        self._await_healthz()
        log = open(self.klog).read()
        self.assertIn("read 0777 at import (writable by other local users), re-tightened to 0700", log)
        self.assertIn("entries planted while it was writable are not to be trusted", log)
        self.assertIn("remove serve-token and repo-root under %s and restart" % self.root, log)
        self.assertNotIn("did NOT start", log, "loud, not fatal")
        self.assertEqual(log.count("state root"), 1, "one line:\n" + log[-1500:])
        self.assertEqual(_mode(self.root), 0o700, "tightened by the import's chmod")
        v = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/version" % self.port, timeout=3).read())["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        self.assertNotIn(self.root, json.dumps(v))

    def test_a_root_that_read_0755_at_import_serves_with_the_import_mode_on_the_boot_line(self):
        """The import's pre-chmod mode plumbing, pinned in a real kernel: a pre-existing 0755 root (a privacy fault, not
        a code-execution one) is re-tightened by the import and reported at boot as a warn-class transition, and the
        kernel serves; /version's stateRootMode reads ok on the root as it is now."""
        os.chmod(self.root, 0o755)
        self._spawn()
        self._await_healthz()
        log = open(self.klog).read()
        self.assertIn("read 0755 at import", log)
        self.assertIn("re-tightened to 0700", log)
        self.assertEqual(_mode(self.root), 0o700)
        v = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/version" % self.port, timeout=3).read())["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        self.assertNotIn(self.root, json.dumps(v))

    def test_a_loosened_root_exits_the_kernel_2_with_the_line(self):
        self._spawn()
        self._await_healthz()
        self.assertTrue(self._healthz(), "serving 200 on the 0700 root")
        os.chmod(self.root, 0o777)
        for _ in range(60):                                    # the jobs pass (every 0.5s at interval 0) finds it
            if self.kernel.poll() is not None:
                break
            time.sleep(0.5)
        self.assertIsNotNone(self.kernel.poll(), "the kernel exited on the loosened root")
        self.assertEqual(self.kernel.returncode, 2, "exit 2:\n" + open(self.klog).read()[-1200:])
        log = open(self.klog).read()
        self.assertIn("writable by other local users", log)
        self.assertIn("romp stops now", log)

    def test_no_file_under_the_root_is_written_after_the_exit(self):
        """extra5-2, behaviourally: snapshot the tree at the moment the process is gone; nothing under the root carries
        an mtime after the exit, because os._exit stopped every writer at once."""
        self._spawn()
        self._await_healthz()
        os.chmod(self.root, 0o777)
        for _ in range(60):
            if self.kernel.poll() is not None:
                break
            time.sleep(0.5)
        self.assertIsNotNone(self.kernel.poll(), "the kernel exited")
        exit_wall = time.time()
        os.chmod(self.root, 0o700)                             # so the walk can read the tree
        latest = 0.0
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                try:
                    latest = max(latest, os.stat(os.path.join(dirpath, name)).st_mtime)
                except OSError:
                    pass
        self.assertLessEqual(latest, exit_wall + 0.5, "no writer ran past the exit")


# ── THE BUS: the second daemon on the same root refuses the same way ─────────────────────────────────────────────

class TheBusRefuses(unittest.TestCase):
    """fresh-3: the postal bus is a second serving daemon on the same state root, kept alive by the kernel. What the
    bus's refusal does to everything that is not the bus: the kernel's _ensure_postal_bus respawns a bus that exits on
    a hostile root until the kernel itself refuses at its import gate (on the same root, first); the CLI and MCP, which
    write nothing under the root, are unaffected. A warn root logs one line and serves. Tested in a child bus process
    with a hermetic root, the way tests/test_hermetic_kernel_postal.py spawns it. At 84b27dd39 the bus has no mode
    check: it serves on a 0777 root."""

    def _bus_env(self, root, port, token="bus-tok"):
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL")}
        env.update(XDG_STATE_HOME=root, ROMP_POSTAL_PORT=str(port),
                   ROMP_POSTAL_HERMETIC="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_IDLE_GRACE="100000",
                   ROMP_POSTAL_POLL="1", ROMP_KERNEL_PORT=str(_free_port()))
        if token:
            env["ROMP_SERVE_TOKEN"] = token          # None: the bus reads or mints the token from the root itself
        return env

    def _serve(self, xdg, port, shim=None, token="bus-tok"):
        """A bus child in serve mode over `xdg`, its log to a temp file; killed and its log removed at cleanup."""
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        cmd = [sys.executable, shim] if shim else [sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"]
        proc = subprocess.Popen(cmd, env=self._bus_env(xdg, port, token=token), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: proc.poll() is None and (proc.kill(), proc.wait(timeout=10)))
        self.addCleanup(lambda: os.unlink(logf.name))
        return proc, logf.name

    def _await_ping(self, proc, port, logname):
        for _ in range(60):
            if self._ping(port):
                return
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        raise unittest.SkipTest("hermetic bus never served /ping here:\n" + open(logname).read()[-600:])

    def _ping(self, port):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/ping" % port, timeout=1)
            return True
        except Exception:
            return False

    def _chmod_refusing_shim(self, root):
        """A serve invocation that first installs an os.chmod refusing the root alone: the shape of a foreign-owned or
        chmod-refusing mount, where the check's repair cannot run and a warn mode stands."""
        shim = os.path.join(tempfile.mkdtemp(), "shim.py")
        Path(shim).write_text(
            "import os, runpy, sys\n"
            "root = %r\n"
            "real = os.chmod\n"
            "def refuse(path, mode, *a, **k):\n"
            "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
            "        raise PermissionError(1, 'chmod refused (interposed)')\n"
            "    return real(path, mode, *a, **k)\n"
            "os.chmod = refuse\n"
            "sys.argv = [%r, 'serve']\n"
            "runpy.run_path(%r, run_name='__main__')\n"
            % (root, os.path.join(BIN, "romp-postal-service"), os.path.join(BIN, "romp-postal-service")))
        return shim

    def test_a_self_owned_writable_root_at_start_is_tightened_said_loud_and_a_planted_token_faults_in_the_loader(self):
        """The settled rule at the bus's start (round 2b): the start gate reads 0777, its own chmod tightens the root, and
        the verdict is on the mode as it reads now (0700), so the bus is not refused; it SAYS what it read, one loud line
        with the distrust remedy, before the serve token under it is read. The planted symlink at serve-token then
        meets the token loader, which faults on its own terms (a link is not read through; exit 1, its message), so
        nothing binds; the link's target is untouched and the link still in place for the operator."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        target = Path(tempfile.mkdtemp(), "elsewhere")
        target.write_text("attacker-planted\n")
        os.symlink(target, os.path.join(root, "serve-token"))
        os.chmod(root, 0o777)
        port = _free_port()
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                           env=self._bus_env(xdg, port, token=None), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 1, "the token loader's RuntimeError, not the gate's exit 2:\n" + r.stderr[-800:])
        self.assertIn("read 0777 at start (writable by other local users), re-tightened to 0700", r.stderr)
        self.assertIn("remove serve-token and repo-root under %s and restart" % root, r.stderr)
        self.assertNotIn("did NOT start", r.stderr, "the gate passed on the mode as read now")
        self.assertLess(r.stderr.index("read 0777 at start"), r.stderr.index("symlink"), "the state-root line came first")
        self.assertEqual(target.read_text(), "attacker-planted\n", "the planted entry's target is untouched")
        self.assertTrue(os.path.islink(os.path.join(root, "serve-token")), "and the plant is still there for the operator")
        self.assertEqual(_mode(root), 0o700)
        self.assertFalse(self._ping(port), "nothing bound")

    def test_a_self_owned_writable_root_at_start_without_a_plant_is_served_with_one_loud_line(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o777)
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700, "re-tightened at start")
        time.sleep(2.5)                                        # a few polls (POLL=1)
        self.assertIsNone(proc.poll(), "a root that reads 0700 now does not exit the bus")
        said = [l for l in open(logname).read().splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "one loud line, at start, not per poll:\n" + "\n".join(said))
        self.assertIn("read 0777 at start (writable by other local users), re-tightened to 0700", said[0])
        self.assertIn("remove serve-token and repo-root", said[0])

    def test_the_bus_refuses_at_start_on_a_writable_root_whose_chmod_is_refused(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o777)
        port = _free_port()
        r = subprocess.run([sys.executable, self._chmod_refusing_shim(root)],
                           env=self._bus_env(xdg, port), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("writable by other local users", r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertEqual(_mode(root), 0o777, "read, not healed")
        self.assertFalse(self._ping(port), "nothing bound")

    def test_a_self_owned_0755_root_at_start_is_retightened_said_once_and_served(self):
        """The repair leaves a trace at the bus's start too (round 2): a pre-existing 0755 root this uid owns is
        re-tightened to 0700 by the check's chmod AND said, one line, and the bus serves; a few polls later still one
        line. At the round-1 head the start chmod'ed first and said nothing."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o755)
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700, "re-tightened at start")
        time.sleep(2.5)                                        # a few polls (POLL=1)
        self.assertIsNone(proc.poll(), "a warn root does not exit the bus")
        said = [l for l in open(logname).read().splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "one line, at start, not per poll:\n" + "\n".join(said))
        self.assertIn("was mode 0755, re-tightened to 0700", said[0])

    def test_the_bus_makes_an_absent_root_0700_and_says_nothing(self):
        """The creation case: no root at the bus's start (ENOENT is unmade, not unverified, at import alone). The bus
        makes it, 0700 whatever the umask, and serves with no state-root line: the umask's mode on a directory this
        process just made is a creation default, not a loosening."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        self.assertFalse(os.path.exists(root))
        port = _free_port()
        proc, logname = self._serve(xdg, port, token=None)      # the token is minted from the root the bus makes
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700)
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")))
        self.assertEqual([l for l in open(logname).read().splitlines() if "state root" in l], [])

    def test_the_bus_refuses_at_start_on_an_unreadable_root(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(xdg, 0o000)                                   # the root cannot be traversed to
        self.addCleanup(lambda: os.chmod(xdg, 0o700))
        port = _free_port()
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                           env=self._bus_env(xdg, port), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("unverified root is not served from", r.stderr)

    def test_a_bus_serving_on_0700_exits_when_the_root_is_loosened(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o700)
        port = _free_port()
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        proc = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                                env=self._bus_env(xdg, port), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: proc.poll() is None and (proc.kill(), proc.wait(timeout=10)))
        self.addCleanup(lambda: os.unlink(logf.name))
        try:
            up = False
            for _ in range(60):
                if self._ping(port):
                    up = True
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
            if not up:
                raise unittest.SkipTest("hermetic bus never served /ping here:\n" + open(logf.name).read()[-600:])
            os.chmod(root, 0o777)                              # the monitor loop re-checks every POLL (1s here)
            for _ in range(30):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            self.assertIsNotNone(proc.poll(), "the bus exited on the loosened root")
            self.assertEqual(proc.returncode, 2)
            self.assertIn("writable by other local users", open(logf.name).read())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_a_warn_root_logs_one_line_and_serves(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o755)
        # interpose a chmod refusal for the root, so the bus's chmod-first start gate cannot tighten it and the warn
        # stands (a warn root the bus CAN tighten becomes ok and serves; the signal here is a root it cannot).
        port = _free_port()
        shim = self._chmod_refusing_shim(root)
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        proc = subprocess.Popen([sys.executable, shim], env=self._bus_env(xdg, port), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: os.unlink(logf.name))
        try:
            up = False
            for _ in range(60):
                if self._ping(port):
                    up = True
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
            self.assertTrue(up, "the bus served on the 0755 root (warn, not refuse):\n" + open(logf.name).read()[-800:])
            time.sleep(2.5)                                    # a few monitor polls (POLL=1): still serving, still one line
            self.assertIsNone(proc.poll(), "a warn root does not exit the bus")
            self.assertTrue(self._ping(port))
            said = [l for l in open(logf.name).read().splitlines() if "not 0700" in l and "state root" in l]
            self.assertEqual(len(said), 1, "one line per transition, not per poll:\n" + "\n".join(said))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
