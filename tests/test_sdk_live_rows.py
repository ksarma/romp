#!/usr/bin/env python3
"""live_sessions is guarded PER SESSION (2026-08-31): the row loop used to run unguarded under the
kernel merge's single try, so ONE session's snapshot() exception silently dropped EVERY SDK session
from an otherwise-successful listing — and absence from a listing reads as death downstream (the
postal bus refused sends to live peers over exactly this class of gap). One bad row now keeps its
other sessions listed, and the failing session itself stays visible as a minimal waiting row.
Synthetic; hermetic state."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend_liverows", os.path.join(BIN, "romp_sdk_backend.py"))

SID_A = "11111111-2222-3333-4444-aaaaaaaaaaaa"
SID_B = "11111111-2222-3333-4444-bbbbbbbbbbbb"


class LiveRowsGuard(unittest.TestCase):
    def setUp(self):
        self.be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        for sid, name in ((SID_A, "web"), (SID_B, "api")):
            sb.write_reg(self.be.state_dir, sid,
                         {"sid": sid, "name": name, "alive": True, "model": "opus"})

    def test_one_bad_snapshot_never_hides_the_others(self):
        broken = mock.Mock()
        broken.thread.is_alive.return_value = True
        broken.snapshot.side_effect = RuntimeError("mid-reconnect blink")
        self.be.sessions[SID_A] = broken
        out = self.be.live_sessions()
        self.assertEqual(set(out), {SID_A, SID_B},
                         "the whole point: a bad row keeps the OTHER sessions listed")
        self.assertEqual(out[SID_A]["state"], "waiting",
                         "the failing session stays visible as a minimal row — absent reads as dead")
        self.assertEqual(out[SID_B]["state"], "waiting", "the dormant sibling's real row")
        self.assertEqual(out[SID_B]["model"], "Opus")

    def test_a_sidless_reg_dict_is_not_fatal(self):
        # list_regs injects the filename as sid for a reg missing the field; either way the
        # loop must survive it and keep the real sessions listed
        sb.write_reg(self.be.state_dir, "nosid", {"alive": True})
        out = self.be.live_sessions()
        self.assertIn(SID_A, out)
        self.assertIn(SID_B, out)


class ListingCompleteness(unittest.TestCase):
    """The scan's completeness contract (2026-08-31, the listing-blink source class): a reg the scan
    has ever seen drops out only by being GENUINELY GONE. A transiently unreadable file serves its
    last good cached row (loudly); a failed RMW read never guts the reg; the alive flips hold the
    same lock as the mirror RMWs, so a snapshot race can't undo them. Synthetic; hermetic."""

    SID = "11111111-2222-3333-4444-cccccccccccc"

    def setUp(self):
        self.be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        sb.write_reg(self.be.state_dir, self.SID,
                     {"sid": self.SID, "name": "web", "alive": True})
        self.path = sb._reg_path(self.be.state_dir, self.SID)

    def test_a_transiently_unreadable_reg_serves_its_last_good_row(self):
        warm = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        self.assertIn(self.SID, warm, "cache warmed")
        good = self.path.read_bytes()
        self.path.write_bytes(b"{ torn")          # the class of transient the invariant covers
        rows = {r["sid"]: r for r in sb.list_regs(self.be.state_dir)}
        self.assertIn(self.SID, rows, "absence reads as death downstream — serve the last good row")
        self.assertTrue(rows[self.SID].get("alive"))
        self.path.write_bytes(good)               # healed → the fresh read replaces the cached row
        self.assertIn(self.SID, {r["sid"] for r in sb.list_regs(self.be.state_dir)})

    def test_an_unreadable_reg_never_seen_is_skipped_loudly_not_served(self):
        p2 = sb._reg_path(self.be.state_dir, "dddddddd-2222-3333-4444-cccccccccccc")
        p2.write_bytes(b"not json")
        sids = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        self.assertNotIn("dddddddd-2222-3333-4444-cccccccccccc", sids,
                         "no prior good row exists — nothing honest to serve")

    def test_a_failed_rmw_read_skips_the_write_rather_than_gutting(self):
        saved = sb.read_reg
        try:
            sb.read_reg = lambda state_dir, sid: None      # the read fails; the FILE stands
            self.be._update_reg(self.SID, queue=["x"])
        finally:
            sb.read_reg = saved
        reg = sb.read_reg(self.be.state_dir, self.SID)
        self.assertTrue(reg.get("alive"), "a gutted reg (no alive) vanishes from every listing")
        self.assertNotIn("queue", reg, "the mirror update was skipped, not applied to a bare reg")

    def test_a_failed_enumeration_serves_every_last_good_row(self):
        # the WHOLE-LISTING twin (review find 2026-09-01): the scandir arm returned [] on a
        # transient OSError — every session ruled dead at once, under the very contract above
        warm = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        self.assertIn(self.SID, warm, "cache warmed")
        saved = sb.os.scandir
        sb.os.scandir = lambda d: (_ for _ in ()).throw(OSError("transient scan fault"))
        try:
            rows = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        finally:
            sb.os.scandir = saved
            for k in [k for k in sb._REG_SERVE_WARNED if str(k).startswith("\x00scan")]:
                sb._REG_SERVE_WARNED.discard(k)
        self.assertIn(self.SID, rows, "a transient enumeration failure must not blank the listing")
        self.assertIn(self.SID, {r["sid"] for r in sb.list_regs(self.be.state_dir)}, "healed scan is live")

    def test_a_missing_dir_is_empty_truth_never_another_roots_rows(self):
        # scandir RAISES FileNotFoundError on a missing sdk/ dir — it does not yield [] — so the
        # transient-fault arm above misread "not created yet" as a failed scan and served the
        # module cache's rows: a process holding backends over SEVERAL state roots (this suite)
        # listed one root's sessions under another. A missing dir took its regs with it: the
        # honest answer is [], and the last-good contract is untouched for real faults.
        warm = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        self.assertIn(self.SID, warm, "cache warmed from this root")
        fresh = tempfile.mkdtemp()                # a state root whose sdk/ dir does not exist yet
        self.assertEqual(sb.list_regs(fresh), [],
                         "a never-written root lists empty — never another root's cached rows")

    def test_a_healed_stat_blip_unlatches_the_incident_log(self):
        # review find 2026-09-01: the once-per-incident latch only cleared on the re-READ path, but
        # a healed stat blip takes the cache-hit path (unchanged file) — the latch stuck and every
        # later incident for that reg logged nothing
        sb.list_regs(self.be.state_dir)                    # warm + healthy
        sb._REG_SERVE_WARNED.add(str(self.path))           # as if a stat blip just logged
        sb.list_regs(self.be.state_dir)                    # healthy CACHE-HIT scan (file untouched)
        self.assertNotIn(str(self.path), sb._REG_SERVE_WARNED,
                         "the cache-hit path must clear the latch too")

    def test_a_missing_reg_still_mints_the_bare_mirror(self):
        sid2 = "eeeeeeee-2222-3333-4444-cccccccccccc"
        self.be._update_reg(sid2, queue=["x"])
        reg = sb.read_reg(self.be.state_dir, sid2)
        self.assertEqual(reg.get("queue"), ["x"], "no file at all = the pre-create mirror case, unchanged")

    def test_a_flip_on_an_unreadable_reg_uses_the_last_good_row(self):
        # kill on a transiently unreadable reg must still land alive=False (review find: the silent
        # no-op left a killed session listed alive until an unrelated write healed it) — the scan's
        # cached row is the RMW base, so the flip both lands AND repairs the file
        self.assertIn(self.SID, {r["sid"] for r in sb.list_regs(self.be.state_dir)})  # cache warm
        self.path.write_bytes(b"{ torn")
        self.be.kill(self.SID)
        reg = sb.read_reg(self.be.state_dir, self.SID)
        self.assertIsNotNone(reg, "the flip rewrote a whole readable reg from the cached base")
        self.assertFalse(reg.get("alive"))
        self.assertEqual(reg.get("name"), "web", "the cached base carried the full row, not a gut")

    def test_a_reg_that_is_a_json_list_is_a_failed_read_never_a_raise(self):
        # a body that is valid JSON but not an object (a list, a string, null) reached setdefault and RAISED
        # out of the scan; the kernel's live merge caught that around the WHOLE SDK half, so one such file
        # dropped every SDK row from the live map, and by-name resolution of every other live SDK session
        # answered "no live session named" (review round 6, 2026-09-09). It takes the torn-body arm: an
        # uncached one is skipped, loudly and once per incident; a cached one serves its last good row.
        sid2 = "dddddddd-2222-3333-4444-cccccccccccc"
        p2 = sb._reg_path(self.be.state_dir, sid2)
        p2.write_bytes(json.dumps([1, 2]).encode())
        err = io.StringIO()
        with redirect_stderr(err):
            rows = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
            again = {r["sid"] for r in sb.list_regs(self.be.state_dir)}
        self.assertEqual((rows, again), ({self.SID}, {self.SID}),
                         "the good row is returned and the list-bodied one skipped, on every scan")
        lines = [ln for ln in err.getvalue().splitlines() if "list_regs: read failed for %s.json" % sid2 in ln]
        self.assertEqual(len(lines), 1, "one line per incident, not per scan: %r" % err.getvalue())
        self.assertIn("(ValueError)", lines[0])
        self.assertIn("no prior row to serve", lines[0])
        # seen readable first: the last good row is served, exactly as for a torn body
        sb.write_reg(self.be.state_dir, sid2, {"sid": sid2, "name": "api", "alive": True})
        self.assertIn(sid2, {r["sid"] for r in sb.list_regs(self.be.state_dir)}, "cache warmed")
        p2.write_bytes(b"null")
        served = {r["sid"]: r for r in sb.list_regs(self.be.state_dir)}
        self.assertIn(sid2, served, "absence reads as death downstream: the last good row is served")
        self.assertEqual(served[sid2].get("name"), "api")

    def test_a_backend_builds_with_a_json_list_reg_on_disk(self):
        # SdkBackend.__init__ walks list_regs for the stale-awaiting heal; the raise above made a first build
        # fail, and the kernel then records "no SDK backend" for the process lifetime (review round 6)
        root = Path(tempfile.mkdtemp())
        sb.write_reg(root, self.SID, {"sid": self.SID, "name": "web", "alive": True})
        sb._reg_path(root, "dddddddd-2222-3333-4444-cccccccccccc").write_bytes(b"[1, 2]")
        with redirect_stderr(io.StringIO()):
            be = sb.SdkBackend(root, "/bin/true", lambda *a, **k: None)
        self.assertEqual(set(be.live_sessions()), {self.SID},
                         "the good session is listed; the broken file hides nothing and stops nothing")

    def test_read_reg_answers_none_for_a_non_object_body_so_a_write_skips_not_raises(self):
        # read_reg handed a list through as parsed: owns() memoized True for it, and _update_reg's
        # reg.update raised instead of skipping the write the unreadable-reg guard promises (review round 6)
        self.path.write_bytes(b"[1, 2]")
        self.assertIsNone(sb.read_reg(self.be.state_dir, self.SID))
        self.assertIsNone(sb.read_reg_for_rmw(self.be.state_dir, self.SID), "exists but will not read, never {}")
        err = io.StringIO()
        with redirect_stderr(err):
            self.be._update_reg(self.SID, queue=["x"])        # raised AttributeError before
        self.assertEqual(self.path.read_bytes(), b"[1, 2]", "the write was skipped and the file left for a person")
        self.assertIn("skipping a queue write", err.getvalue())
        self.assertFalse(self.be.owns(self.SID), "a record that will not read is no positive answer")
        self.assertNotIn(self.SID, self.be._owns_memo, "and is not memoized as one")

    def test_the_alive_flip_never_loses_to_an_rmw_snapshot(self):
        import threading
        stop = threading.Event()

        def storm():
            while not stop.is_set():
                self.be._update_reg(self.SID, queue=[])

        t = threading.Thread(target=storm)
        t.start()
        try:
            for _ in range(25):
                self.be.kill(self.SID)
                reg = sb.read_reg(self.be.state_dir, self.SID)
                self.assertFalse(reg.get("alive"),
                                 "kill's alive=False must be immediately durable under RMW traffic")
                self.be.resume("web", self.SID)
                reg = sb.read_reg(self.be.state_dir, self.SID)
                self.assertTrue(reg.get("alive"),
                                "resume's alive=True must be immediately durable under RMW traffic")
        finally:
            stop.set()
            t.join()


class FaultServeRootScope(unittest.TestCase):
    """The whole-listing fault serve is ROOT-SCOPED: _REG_CACHE is a module global keyed by
    absolute reg path and shared by every backend in the process, so the OSError arm's 'serve every
    last good row' handed a PermissionError on ONE root the cached rows of every OTHER root — the
    same cross-root session resurrection the missing-dir arm closed, still open for every
    non-FileNotFoundError enumeration fault (PermissionError, EMFILE, transient I/O). The last-good
    purpose is untouched: a fault on this root still serves THIS root's cached rows. Synthetic;
    hermetic roots."""

    SID_A = "aaaaaaaa-2222-3333-4444-555555555555"
    SID_B = "bbbbbbbb-2222-3333-4444-555555555555"

    def setUp(self):
        self.root_a, self.root_b = tempfile.mkdtemp(), tempfile.mkdtemp()
        sb.write_reg(self.root_a, self.SID_A, {"sid": self.SID_A, "name": "web", "alive": True})
        sb.write_reg(self.root_b, self.SID_B, {"sid": self.SID_B, "name": "api", "alive": True})

    def tearDown(self):
        for k in [k for k in sb._REG_SERVE_WARNED if str(k).startswith("\x00scan")]:
            sb._REG_SERVE_WARNED.discard(k)

    def test_a_fault_on_one_root_serves_only_that_roots_rows(self):
        self.assertIn(self.SID_A, {r["sid"] for r in sb.list_regs(self.root_a)}, "cache warm: A")
        self.assertIn(self.SID_B, {r["sid"] for r in sb.list_regs(self.root_b)}, "cache warm: B")
        saved = sb.os.scandir
        sdk_a = os.path.join(self.root_a, "sdk")

        def faulty(p):
            if str(p) == sdk_a:
                raise PermissionError("mode bits blinked")   # any non-FileNotFoundError fault
            return saved(p)

        sb.os.scandir = faulty
        try:
            rows = {r["sid"] for r in sb.list_regs(self.root_a)}
        finally:
            sb.os.scandir = saved
        self.assertIn(self.SID_A, rows, "this root's last good rows still serve through the fault")
        self.assertNotIn(self.SID_B, rows, "another root's cached rows never resurrect here")
        self.assertEqual({r["sid"] for r in sb.list_regs(self.root_a)}, {self.SID_A},
                         "the healed scan is the fresh truth again")


if __name__ == "__main__":
    unittest.main()
