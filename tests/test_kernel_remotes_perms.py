#!/usr/bin/env python3
"""remotes.json is a CREDENTIAL STORE — every attached-host row carries that host's serve token (fetched
over ssh at attach), which authorizes control of that machine's kernel through the tunnel. It must be
0600: at the default 0644 any other local user could lift a remote's token and drive that machine, which
would defeat the loopback token gate for the federation case (found in the pre-release sweep, 2026-07-22).

Also pins the general rule: _atomic_write sets `mode` on the TEMP's descriptor before the first write (os.fchmod,
exact under any umask), so a credential file's text never exists at a wider mode (PR 789, review round 1,
2026-09-18: the first cut's exclusive create at the mode refused a leftover temp and clipped the mode by the umask).

Synthetic only — hermetic temp STATE, placeholder host/token.
"""
import ast
import errno
import os
import re
import stat
import tempfile
import threading
import unittest
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def _open_fds():
    """The process's open descriptors as a set (Linux: /proc/self/fd), or None where that view does not exist."""
    try:
        return set(os.listdir("/proc/self/fd"))
    except OSError:
        return None


def _fd_probes(case):
    """The failure-path probes (review round 2 of PR 789, 2026-09-19): os.open recorded (the descriptor it returned)
    and performed; os.fchmod raising EPERM, the error an inode this uid does not own returns and the shape a filesystem
    that refuses fchmod after a successful open takes; os.close recorded and performed. Undone at cleanup."""
    opened, closed = [], []
    real_open, real_close = os.open, os.close

    def open_probe(*a, **k):
        fd = real_open(*a, **k)
        opened.append(fd)
        return fd

    def fchmod_refused(fd, mode):
        raise PermissionError(errno.EPERM, "fchmod refused (interposed)")

    def close_probe(fd):
        closed.append(fd)
        return real_close(fd)
    for name, probe in (("open", open_probe), ("fchmod", fchmod_refused), ("close", close_probe)):
        patch = mock.patch.object(os, name, probe)
        patch.start()
        case.addCleanup(patch.stop)
    return opened, closed


class _PinnedSeq:
    """A stand-in for km._atomic_seq that yields one value. The writer's `_atomic_seq[0] += 1` reads item 0 and writes
    it back, so __getitem__ returns the pin and __setitem__ drops the increment: while the stand-in is in place every
    call names its temp with this sequence number, and a writer on another thread still gets its own name from
    threading.get_ident() (review round 2 of PR 789, 2026-09-19)."""

    def __init__(self, n):
        self.n = n

    def __getitem__(self, i):
        return self.n

    def __setitem__(self, i, v):
        pass


def _mode_bearing_callers(source):
    """Every `_atomic_write(...)` call in `source` that carries a mode (the `mode=` keyword, or a third positional
    argument), by enclosing function (nested defs joined with a dot; "<module>" for a call at the top level), in source
    order. Reads CALLS, not lines: a mode on the third line of a wrapped call counts, a line that merely contains the
    word does not (review round 2 of PR 789, 2026-09-19, replacing the grep the docstring offered)."""
    out, stack = [], []

    class Walk(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            stack.append(node.name)
            self.generic_visit(node)
            stack.pop()
        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            f = node.func
            name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
            if name == "_atomic_write" and (any(k.arg == "mode" for k in node.keywords) or len(node.args) >= 3):
                out.append(".".join(stack) or "<module>")
            self.generic_visit(node)
    Walk().visit(ast.parse(source))
    return out


class RemotesFilePermissions(unittest.TestCase):
    def setUp(self):
        # the kernel module is ONE object per process for every test file that loads it under this
        # name (a peer file's km IS this km), so the row planted here leaves with the test: under
        # xdist a whole-map reader elsewhere (test_kernel_trust's PairsSnapshot) found it (2026-09-02)
        saved = dict(km._remotes)
        self.addCleanup(lambda: (km._remotes.clear(), km._remotes.update(saved)))
        km._remotes.clear()
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": 8801,
                                   "bus_port": 8802, "token": "REMOTE-SECRET-TOKEN", "proc": None,
                                   "status": "up", "detail": "", "sids": [], "trust": "directed"}

    def test_save_writes_0600(self):
        km._remotes_save()
        self.assertTrue(km.REMOTES_FILE.exists())
        self.assertEqual(_mode(km.REMOTES_FILE), 0o600,
                         "remotes.json holds remote serve tokens — it must not be group/world readable")

    def test_save_tightens_an_existing_world_readable_file(self):
        km._remotes_save()
        os.chmod(km.REMOTES_FILE, 0o644)          # simulate a file written before the fix
        km._remotes_save()
        self.assertEqual(_mode(km.REMOTES_FILE), 0o600, "a re-save must re-tighten the mode")

    def test_load_heals_a_stale_world_readable_file(self):
        km._remotes_save()
        os.chmod(km.REMOTES_FILE, 0o644)          # a file left over from before the fix
        km._remotes_load()
        self.assertEqual(_mode(km.REMOTES_FILE), 0o600,
                         "loading an old 0644 remotes.json must heal it, not keep leaking tokens")

    def test_the_token_really_is_in_there(self):
        # guard the premise: if rows ever stop carrying tokens this test's reason to exist changes
        km._remotes_save()
        self.assertIn("REMOTE-SECRET-TOKEN", km.REMOTES_FILE.read_text())


class AtomicWriteMode(unittest.TestCase):
    def test_mode_applied_and_default_unchanged(self):
        d = km.jd.STATE / "permtest"
        d.mkdir(parents=True, exist_ok=True)
        secret, plain = d / "secret.json", d / "plain.json"
        km._atomic_write(secret, "{}", mode=0o600)
        km._atomic_write(plain, "{}")
        self.assertEqual(_mode(secret), 0o600)
        self.assertNotEqual(_mode(plain), 0o600, "no mode → umask default, unchanged behavior")

    def test_no_temp_files_left_behind(self):
        d = km.jd.STATE / "permtest2"
        d.mkdir(parents=True, exist_ok=True)
        km._atomic_write(d / "x.json", "{}", mode=0o600)
        self.assertEqual([p.name for p in d.glob("*.tmp.*")], [])

    def _probes(self):
        """os.fchmod recorded WITH the file's size at that moment (0 means before the first write) and performed;
        os.chmod recorded and NOT performed, so a chmod-after road leaves the file at the umask's mode and a case
        reads the descriptor's mode and nothing else."""
        fchmods, chmods = [], []
        real_fchmod = os.fchmod

        def fchmod_probe(fd, mode):
            fchmods.append((mode, os.fstat(fd).st_size))
            return real_fchmod(fd, mode)

        def chmod_probe(path, mode, *a, **k):
            chmods.append((str(path), mode))
        for name, probe in (("fchmod", fchmod_probe), ("chmod", chmod_probe)):
            patch = mock.patch.object(os, name, probe)
            patch.start()
            self.addCleanup(patch.stop)
        return fchmods, chmods

    def test_the_mode_is_set_on_the_descriptor_before_the_first_write_never_by_a_chmod_on_a_path(self):
        # The mode goes onto the temp's DESCRIPTOR (os.fchmod) before the first write. Until 2026-09-18 it was a
        # chmod on the path after write_text: a window with the text at the umask's mode (PR 776's review round,
        # kernel-1 and extra5-2, deferred to their own fix). os.fchmod is recorded with the file's size at that
        # moment, so "before the first write" is executed rather than read off the source, and os.chmod is not
        # performed, so the old order reads as the umask's 0644 (PR 789, review round 1, 2026-09-18).
        d = km.jd.STATE / "permtest3"
        d.mkdir(parents=True, exist_ok=True)
        secret = d / "secret.json"
        self.addCleanup(os.umask, os.umask(0o022))
        fchmods, chmods = self._probes()
        km._atomic_write(secret, "{}", mode=0o600)
        self.assertEqual(_mode(secret), 0o600, "0600 from the descriptor, not from a chmod after the write")
        self.assertEqual(fchmods, [(0o600, 0)], "one fchmod, on the descriptor, while the temp is still empty")
        self.assertEqual(chmods, [], "no chmod on any path: nothing tightens after the write")
        self.assertEqual(secret.read_text(), "{}")

    def test_the_requested_mode_is_published_exactly_under_a_permissive_and_a_restrictive_umask(self):
        # The refuter's case from PR 789's review round 1 (tests-2): the one guard against a mode regression in the
        # helper. No other test hands it a mode but 0600, so a helper that hardcoded 0600 was green across the
        # suite. A group-bit mode under a permissive umask, the same mode under a restrictive one, and an owner-only
        # mode under the restrictive one, each published exactly as requested: the mode is set on the descriptor,
        # which the umask does not touch (the refuter ran the middle leg against the first cut's exclusive create
        # and got 0600, the clipping round 1 removed; a chmod-after road would also publish the exact mode, so
        # os.chmod is interposed and not performed, as above, and that road reads as the umask's mode instead).
        # os.umask is process-global: changed around each call alone, restored on cleanup.
        d = km.jd.STATE / "permtest4"
        d.mkdir(parents=True, exist_ok=True)
        self.addCleanup(os.umask, os.umask(0o022))
        fchmods, chmods = self._probes()
        got = []
        for umask, mode in ((0o002, 0o640), (0o077, 0o640), (0o077, 0o600)):
            target = d / ("mode%o-umask%o.json" % (mode, umask))
            os.umask(umask)
            try:
                km._atomic_write(target, "{}", mode=mode)
            finally:
                os.umask(0o022)
            got.append(_mode(target))
        self.assertEqual(got, [0o640, 0o640, 0o600], "the requested mode, exactly, under both umasks")
        self.assertEqual([m for m, _size in fchmods], [0o640, 0o640, 0o600], "each from its own fchmod")
        self.assertEqual(chmods, [])

    def test_a_leftover_temp_at_the_same_name_is_overwritten_and_published_at_the_mode(self):
        # PR 789's first cut opened the temp O_EXCL, so a temp left by a killed writer at the exact next name (the
        # same pid, thread ident and sequence: unreachable in practice, but a behaviour change) turned the publish
        # into FileExistsError where this road had always overwritten it. Round 1 (2026-09-18) went back to O_TRUNC
        # with the mode set on the descriptor, which also re-modes the leftover's inode (O_TRUNC keeps its 0644
        # until the fchmod), so the publish is never the leftover's mode either.
        # Review round 2 (2026-09-19, fresh-4): until then this case PREDICTED the next temp name from km._atomic_seq
        # read outside km._atomic_lock, so any other _atomic_write in the process between that read and the call moved
        # the sequence on and the planted file was never the temp (a refuter's background writer turned the case red in
        # four calls; the suite has no such thread today, so the flake was latent). The sequence is pinned with a
        # stand-in for the one call, the way the registry twin in tests/test_sdk_backend.py stubs uuid4: the name is
        # controlled, not predicted, and the case still proves the overwrite and the re-mode.
        d = km.jd.STATE / "permtest5"
        d.mkdir(parents=True, exist_ok=True)
        target = d / "x.json"
        target.write_text("OLD")
        stale = target.with_name("%s.tmp.%d.%d.%d" % (target.name, os.getpid(), threading.get_ident(), 7))
        stale.write_text('{"stale": "left by a killed writer"}')
        os.chmod(stale, 0o644)
        with mock.patch.object(km, "_atomic_seq", _PinnedSeq(7)):
            km._atomic_write(target, '{"new": 1}', mode=0o600)
        self.assertEqual(target.read_text(), '{"new": 1}', "published over the leftover, not refused")
        self.assertEqual(_mode(target), 0o600, "the descriptor's mode, not the leftover's 0644")
        self.assertFalse(stale.exists(), "the leftover became the temp and moved")

    def test_a_raising_fchmod_closes_the_descriptor_and_leaves_no_temp(self):
        # Review round 2 of PR 789 (2026-09-19): round 1 put the fchmod between os.open and os.fdopen with nothing closing
        # the descriptor when it raised (EPERM on an inode this uid does not own, ENOTSUP on a filesystem that refuses
        # fchmod after a successful open); os.fdopen was the only close, so every failure leaked one descriptor, and
        # _save_pending_ops swallows the error and re-saves on every park or delivery, so there the leak was unbounded.
        # The two precedents the docstring cites (cli/perf_export.py write_file, the Codex registry lock) close the fd
        # on that road; this pins that the copy does too: the descriptor os.open returned reaches os.close (a real
        # close, recorded), the process holds no new descriptor afterwards, the temp is gone and nothing is published.
        d = km.jd.STATE / "permtest6"
        d.mkdir(parents=True, exist_ok=True)
        target = d / "x.json"
        opened, closed = _fd_probes(self)
        before = _open_fds()
        with self.assertRaises(PermissionError):
            km._atomic_write(target, "{}", mode=0o600)
        self.assertEqual(len(opened), 1, "one descriptor, the temp's")
        self.assertEqual(closed, opened, "closed on the failure road")
        if before is not None:
            self.assertEqual(_open_fds(), before, "no descriptor leaked")
        self.assertEqual([p.name for p in d.glob("*.tmp.*")], [], "the temp is removed")
        self.assertFalse(target.exists(), "nothing published")


class TheModeBearingCallerList(unittest.TestCase):
    """_atomic_write's docstring names every caller that passes a mode, and the list is maintained by hand. Until review
    round 2 of PR 789 (2026-09-19) the docstring offered `grep -n "_atomic_write(.*mode" kernel/` as the list's source
    of truth; that grep misses the parked-ops mirror (its mode= sits on the third line of a wrapped call) and matches
    two lines with no mode in the call, so the recipe written to stop the list drifting silently omitted the caller the
    PR is named after. The list is re-derived here from the CALLS (an ast walk over kernel/kernel.py), and the case
    fails when the docstring's line drifts from them."""

    SOURCE = os.path.join(BIN, "romp-kernel")

    def _walked(self):
        with open(self.SOURCE, encoding="utf-8") as f:
            return _mode_bearing_callers(f.read())

    def _listed(self):
        m = re.search(r"Mode-bearing callers, by enclosing function: ([^.]+)\.", km._atomic_write.__doc__ or "")
        self.assertIsNotNone(m, "the docstring carries the machine-readable line this case reads")
        return [n.strip() for n in m.group(1).split(",")]

    def test_the_docstrings_list_equals_the_ast_walk(self):
        listed, walked = self._listed(), self._walked()
        self.assertEqual(len(set(listed)), len(listed), "no caller named twice")
        self.assertEqual(sorted(listed), sorted(set(walked)),
                         "the docstring's caller list drifted from the calls in kernel/kernel.py: update the line")

    def test_the_walk_finds_the_wrapped_mirror_call_the_grep_missed(self):
        self.assertIn("_save_pending_ops", self._walked(), "the parked-ops mirror: mode= on the third line of a wrapped call")

    def test_the_walk_reads_calls_not_lines(self):
        src = ("def wrapped():\n"
               "    _atomic_write(p,\n"
               "                  text,\n"
               "                  mode=0o600)\n"
               "def positional():\n"
               "    _atomic_write(p, text, 0o600)\n"
               "def forwards(mode):\n"
               "    _atomic_write(p, text, mode=mode)\n"
               "def no_mode():\n"
               "    _atomic_write(p, json.dumps({'mode': m}))   # the word on the line, no mode in the call\n"
               "def outer():\n"
               "    def inner():\n"
               "        km._atomic_write(p, text, mode=0o600)\n")
        self.assertEqual(_mode_bearing_callers(src), ["wrapped", "positional", "forwards", "outer.inner"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
