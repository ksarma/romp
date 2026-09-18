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
import os
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
        d = km.jd.STATE / "permtest5"
        d.mkdir(parents=True, exist_ok=True)
        target = d / "x.json"
        target.write_text("OLD")
        stale = target.with_name("%s.tmp.%d.%d.%d" % (target.name, os.getpid(), threading.get_ident(),
                                                       km._atomic_seq[0] + 1))
        stale.write_text('{"stale": "left by a killed writer"}')
        os.chmod(stale, 0o644)
        km._atomic_write(target, '{"new": 1}', mode=0o600)
        self.assertEqual(target.read_text(), '{"new": 1}', "published over the leftover, not refused")
        self.assertEqual(_mode(target), 0o600, "the descriptor's mode, not the leftover's 0644")
        self.assertFalse(stale.exists(), "the leftover became the temp and moved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
