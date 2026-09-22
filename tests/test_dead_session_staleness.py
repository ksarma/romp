#!/usr/bin/env python3
"""Cards on dead sessions must still move (the user 2026-08-28: a board audit found 18 of 23
working/blocked cards stale, every one on a dead / ext: / remote-mirror sid). Three roots, each
pinned: (1) the quiet reply sweep walked only DISCOVERED sessions as senders, so a dead sender's
trackers were never swept again — absent stores holding open trackers now join the walk, and the
recipient's reply (the event) closes them with the sweep as its only writer; (2) settle derived
closed=False from mere registry absence — _presumed_closed now determines deadness from everything
the kernel knows (windowed parse, windowless transcript, ext:-by-construction, the bus's federated
remote-sids mirror), with a LIVE REMOTE session's mirror store never presumed settled; (3) relayed
mail minted DIFFERENT ids on the two sides, so the delegation link never formed — deliver() stamps
the sender-side originMid on the receiving row and every join seam accepts either id. Plus the
plant-time dedupe of byte-identical same-peer mirrors (the ext mailer's same-minute twins).
Since 2026-09-22 also the mirror's ONE home: rule 5's read and the bus's write meet on the same
file over one state root (ReaderFollowsTheWriter, by execution, under both root shapes). From the
ladder's birth the judge read STATE/remote-sids while the bus wrote STATE/postal/remote-sids, so
rule 5 never fired; the fixtures here wrote the judge's dead path themselves and hid it.
SYNTHETIC fixtures only; private synthetic sids; hostname TESTHOST."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_deadstale", os.path.join(BIN, "romp-judge"))

NOW = 1_788_300_000
T0 = NOW - 3600
DEAD = "a11f0001-1111-4222-8333-000000000001"   # private synthetic sids — never the shared placeholder
RCP = "a11f0001-1111-4222-8333-000000000002"
EXT = "ext:vault-warning-mailer"
MID = "1788299000.000001_1.TESTHOST"
REMOTE = "a11f0001-1111-4222-8333-000000000003"   # a sid live on ANOTHER host: the bus hears its heartbeat


def _mirror():
    """The deadness mirror where the BUS writes it: the bus's STATE is the judge's plus `postal`
    (postal_service.py _write_remote_sids), and _presumed_closed reads it there. Until 2026-09-22
    these fixtures wrote jd.STATE / "remote-sids", the judge's own read path, which nothing in the
    product wrote; the ladder tests passed against a restatement of the dead path. This spelling is
    held to the writer's by ReaderFollowsTheWriter below, which runs the real writer and the real
    reader over one root; the helper exists so the fixtures have one spelling to hold."""
    d = jd.STATE / "postal"
    d.mkdir(parents=True, exist_ok=True)
    return d / "remote-sids"


def _node(nid, text, parent, t=T0, **kw):
    base = {"id": nid, "text": text, "parentId": parent, "nodeComplete": False,
            "blocked": False, "cleared": False, "trail": [], "t": t, "mt": t, "log": []}
    base.update(kw)
    return base


class World(unittest.TestCase):
    def setUp(self):
        self._disc = jd.discover
        self.td = tempfile.TemporaryDirectory()
        self._msgs = jd.MESSAGES
        jd.MESSAGES = Path(self.td.name) / "messages.jsonl"
        jd.MESSAGES.write_text("")
        # only the RECIPIENT is discovered; the sender is dead by construction
        jd.discover = lambda now, window=None, forks=True: [(RCP, "/dev/null", None, "api")]

    def tearDown(self):
        jd.discover = self._disc
        jd.MESSAGES = self._msgs
        for sid in (DEAD, RCP, EXT):
            for d in (jd.GOALDIR, jd.GOALARCHDIR):
                try:
                    (d / (sid + ".json")).unlink()
                except OSError:
                    pass
            try:
                (jd._overrides_dir() / (sid + ".jsonl")).unlink()
            except OSError:
                pass
        try:
            _mirror().unlink()
        except OSError:
            pass
        self.td.cleanup()

    def _dead_sender(self, sid=DEAD):
        # lastNode = the tracker: the settle gate holds only the ACTIVE FOCUS top, so the
        # dead-vs-remote distinction is visible exactly there (a focusless store settles anyway)
        st = {"rompUuid": sid, "seq": 2, "lastNode": sid + ":g1", "nodes":
              {sid + ":g1": _node(sid + ":g1", "↪ delegated to api: verify refs", None,
                                  handoff={"peer": RCP, "msgId": MID, "quiet": True})},
              "placements": {}, "status": {}}
        jd.save_goals(sid, st)

    def _reply(self, at):
        jd.MESSAGES.write_text(json.dumps(
            {"t": at, "ev": "sent", "id": "r1", "from_id": RCP, "to_id": DEAD,
             "kind": "coordinate", "body": "verified; drift zero"}) + "\n")


class DeadSenderSweep(World):
    def test_a_dead_senders_quiet_tracker_closes_on_the_reply_and_settles(self):
        _mirror().write_text("")     # the bus has spoken: no remote sessions
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        nd = st["nodes"][DEAD + ":g1"]
        self.assertTrue(nd.get("nodeComplete"), "the reply is the event; the sweep is its only writer")
        self.assertEqual(st["status"].get(DEAD + ":g1"), "completed",
                         "a dead determination settles the top — the card leaves Working")

    def test_a_live_remote_mirror_closes_but_never_presumes_settled(self):
        _mirror().write_text(DEAD + "\n")   # the bus says: alive on another host
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        self.assertTrue(st["nodes"][DEAD + ":g1"].get("nodeComplete"))
        self.assertNotEqual(st["status"].get(DEAD + ":g1"), "completed",
                            "a live remote session's mirror store is never premature-settled")

    def test_no_reply_leaves_the_tracker_open(self):
        _mirror().write_text("")
        self._dead_sender()
        jd.run_propagate(now=NOW)
        self.assertFalse(jd.load_goals(DEAD)["nodes"][DEAD + ":g1"].get("nodeComplete"),
                         "no report-back event → nothing moves")


class PresumedClosed(World):
    def test_the_deadness_ladder(self):
        self.assertTrue(jd._presumed_closed(EXT, NOW), "ext: is closed by construction")
        # absent everywhere + the bus has spoken (empty mirror) → dead
        _mirror().write_text("")
        self.assertTrue(jd._presumed_closed(DEAD, NOW))
        # the bus lists it as remote-live → not closed
        _mirror().write_text(DEAD + "\n")
        self.assertFalse(jd._presumed_closed(DEAD, NOW))
        # no mirror file at all → cannot determine → conservative
        _mirror().unlink()
        self.assertFalse(jd._presumed_closed(DEAD, NOW))


class OriginMidJoin(World):
    def test_postal_row_carries_the_origin_mid(self):
        jd.MESSAGES.write_text(json.dumps(
            {"t": T0, "ev": "sent", "id": "local-9", "from": "web", "from_id": DEAD,
             "to_id": RCP, "kind": "delegate", "body": "do the thing",
             "originMid": MID}) + "\n")
        self.assertEqual(jd._postal_row("local-9")[5], MID)

    def test_the_dismissal_join_accepts_the_origin_mid(self):
        # a LINKED (non-quiet) tracker whose recipient carries only the RELAYED local mid: the
        # recipient's origin.originMid is the sender-side id, and the dismissed-recipient ending
        # must join on it (pre-fix, the differing ids meant no join and the mirror sat forever)
        st = {"rompUuid": DEAD, "seq": 2, "nodes":
              {DEAD + ":g1": _node(DEAD + ":g1", "↪ delegated to api: verify refs", None,
                                   handoff={"peer": RCP, "msgId": MID})},
              "placements": {}, "status": {}}
        jd.save_goals(DEAD, st)
        rn = _node(RCP + ":g5", "Verify the refs", None, cleared=True,
                   origin={"peer": DEAD, "goalId": DEAD + ":g1", "msgId": "local-9",
                           "originMid": MID})
        jd.save_goals(RCP, {"rompUuid": RCP, "nodes": {RCP + ":g5": rn},
                            "placements": {}, "status": {}})
        self._reply(T0 + 500)
        _mirror().write_text("")
        jd.run_propagate(now=NOW)
        nd = jd.load_goals(DEAD)["nodes"][DEAD + ":g1"]
        self.assertTrue(nd.get("nodeComplete"), "the join formed across the relay's re-stamped id")
        self.assertIn("dismissed", nd.get("doneWhy") or "")


class ReaderFollowsTheWriter(unittest.TestCase):
    """Rule 5's read and the bus's write meet on ONE file (2026-09-22). The bus writes the deadness
    mirror at its STATE, the romp state root plus `postal`; the judge's STATE is the root itself, and
    from the ladder's birth (2026-08-28) its read was STATE/remote-sids, a path nothing wrote: the
    read raised OSError on every call, rule 5 never fired, every sid reaching it answered
    cannot-determine. Conservative, so nothing settled early; a dead sender's card only took longer
    to settle. Pinned by EXECUTION, not by spelling: the real writer (_write_remote_sids) and the
    real reader (_presumed_closed) run in one fresh interpreter over one temp root, under each of
    the two root shapes the constants bind from (XDG_STATE_HOME, and ROMP_STATE_DIR, which outranks
    it), and a sid nothing knows is presumed closed once the bus has written. The control isolates
    the old path: with the bus's file removed and the same line at STATE/remote-sids, the judge's
    read path until 2026-09-22, the reader answers cannot-determine, so the read MOVED to the bus's
    file rather than widening to both, and a reverted read fails this pin by its own message. The
    proof that the rule itself was sound, and only its path dead, is the same control run at the
    base: there the bytes at the old path answered True, the only way rule 5 could fire then. That
    run is recorded in the fix-up's red-before log for this change (the fire and rule-4 pins red
    under both root shapes, this control red on `True is not false`, the frame green); it is not
    asserted here, where it can no longer hold. The bus's file is removed FIRST: this control's
    first form left it in place and asserted True, which held because the bus's file was read, not
    the old path's (a pin true for a reason other than its message; the fix-up of 2026-09-22). The
    root carries `session-hosts` off, the repo rule for a test that mints its own state root, and
    the child reads that file back through the judge's STATE, so the root the test prepared is the
    root both modules bound."""

    @classmethod
    def setUpClass(cls):
        cls.got = {shape: cls._over_one_root(shape) for shape in ("XDG_STATE_HOME", "ROMP_STATE_DIR")}

    @classmethod
    def _over_one_root(cls, shape):
        td = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, td, ignore_errors=True)
        home = Path(td) / "home"
        home.mkdir()
        if shape == "XDG_STATE_HOME":
            env = {"XDG_STATE_HOME": str(Path(td) / "xdg")}
            root = Path(td) / "xdg" / "romp"
        else:
            env = {"ROMP_STATE_DIR": str(Path(td) / "state")}
            root = Path(td) / "state"
        root.mkdir(parents=True)
        (root / "session-hosts").write_text("off\n")
        # built from a rule, never the inherited environment: a live kernel exports ROMP_STATE_DIR to its
        # sessions and hundreds of test modules rebind XDG_STATE_HOME at import (tests/README.md)
        full = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "TMPDIR": str(home),
                "ROMP_KERNEL_NO_OPEN": "1", "PYTHONDONTWRITEBYTECODE": "1", **env}
        # The child: the bus and the judge loaded into ONE fresh interpreter under the root shape set above, so
        # both STATE constants bind at import exactly as in production (a `-c` program: romp_load's direct-run
        # floor does not arm, so the environment above is the whole of it). The bus's writer is given one live
        # remote heartbeat and called; the judge's reader is asked about a sid nothing knows (rule 5) and about
        # the heartbeating one (rule 4), before and after the write; then the control, isolated: the bus's file
        # removed, the writer's line for that sid put at the judge's read path until 2026-09-22
        # (STATE/remote-sids), and the reader asked again, so the answer can come from nothing but that old
        # path. A missing bus file is reported, not raised, so a moved writer fails the pins by their own
        # messages. The source sits as a literal in the argv slot after "-c": the shape the hosts-on census
        # (tests/test_tempdir_hygiene.py, HarnessSocketBudget's ledger) reads as a child Python's source, parsing
        # the literal as a nested module, where the child's read of the session-hosts toggle is a read; a
        # module-level name bound to the same text is not followed into the child, and the whole text stood
        # unaccounted (the sweep red of 2026-09-22).
        out = subprocess.run([sys.executable, "-c", r"""
import json, os, sys, time
tests_dir, bin_dir, remote, dead = sys.argv[1:5]
sys.path.insert(0, tests_dir)
from romp_load import load_source
pm = load_source("romp_postal_oneroot", os.path.join(bin_dir, "romp-postal-service"))
jd = load_source("romp_judge_oneroot", os.path.join(bin_dir, "romp-judge"))
now = time.time()
out = {"busState": str(pm.STATE), "judgeState": str(jd.STATE),
       "hostsOff": (jd.STATE / "session-hosts").read_text().strip(),
       "discovered": len(jd.discover(now)) + len(jd.discover(now, window=now)),
       "beforeWrite": jd._presumed_closed(dead, now)}
pm.STATE.mkdir(parents=True, exist_ok=True)
pm.HEARTBEATS[remote] = ("web", now)
pm._write_remote_sids()
bus_file = pm.STATE / "remote-sids"
out["busFile"] = str(bus_file)
out["busFileText"] = bus_file.read_text() if bus_file.exists() else None
out["fire"] = jd._presumed_closed(dead, now)
out["named"] = jd._presumed_closed(remote, now)
bus_file.unlink(missing_ok=True)
out["busFileGoneForControl"] = not bus_file.exists()
old_path = jd.STATE / "remote-sids"
old_path.write_text(remote + "\n")
out["oldPath"] = str(old_path)
out["oldPathText"] = old_path.read_text()
out["controlOldPathOnly"] = jd._presumed_closed(dead, now)
print(json.dumps(out))
""", HERE, BIN, REMOTE, DEAD], capture_output=True, text=True, env=full, cwd=str(home), timeout=120)
        assert out.returncode == 0, "%s child failed: %s" % (shape, out.stderr[-2000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        got["root"] = str(root)
        return got

    def test_both_modules_bound_the_one_root_the_test_prepared(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["judgeState"], got["root"], "the judge's STATE is the root")
                self.assertEqual(got["busState"], got["root"] + "/postal", "the bus's STATE is the root plus postal")
                self.assertEqual(got["hostsOff"], "off", "the child read the session-hosts file the test wrote")
                self.assertEqual(got["discovered"], 0, "an empty HOME: rules 1 and 2 have no session to answer for")
                self.assertEqual(got["busFileText"], REMOTE + "\n", "the writer wrote the heartbeating sid")

    def test_rule_5_fires_for_a_sid_nothing_knows_once_the_bus_has_written(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertFalse(got["beforeWrite"], "no mirror file yet: cannot determine, conservative")
                self.assertTrue(got["fire"], "the bus wrote %s; the judge's read must be that file: rule 5 "
                                "presumes a sid nothing knows closed" % got["busFile"])

    def test_rule_4_holds_the_sid_the_bus_names_open(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertTrue(got["fire"], "rule 5 fired in this run, so the False below is rule 4's, "
                                "not cannot-determine's")
                self.assertFalse(got["named"], "live on another host: never presumed settled")

    def test_the_control_the_old_path_alone_is_no_longer_read(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertTrue(got["busFileGoneForControl"], "the control isolates the old path: the "
                                "bus's file %s is removed before the old path is written" % got["busFile"])
                self.assertEqual(got["oldPathText"], REMOTE + "\n", "the writer's line sits at %s, the "
                                 "judge's read path until 2026-09-22" % got["oldPath"])
                self.assertFalse(got["controlOldPathOnly"], "with only the old path populated the judge "
                                 "answers cannot-determine: the read moved to the bus's file and no longer "
                                 "reaches %s (at the base the same bytes there answered True; that run is "
                                 "the round's red-before log)" % got["oldPath"])


class PlantDedupe(unittest.TestCase):
    def test_byte_identical_open_twins_reuse_the_node(self):
        st = {"rompUuid": DEAD, "seq": 0, "nodes": {}, "placements": {}, "status": {}}
        a = jd._plant_handoff_track(st, None, "check the vault warning", RCP, "api", T0, MID)
        b = jd._plant_handoff_track(st, None, "check the vault warning", RCP, "api", T0 + 30,
                                    "1788299030.000002_2.TESTHOST")
        self.assertEqual(a, b, "same peer + same text while OPEN → one mirror, not twins")
        c = jd._plant_handoff_track(st, None, "a different errand", RCP, "api", T0 + 60,
                                    "1788299060.000003_3.TESTHOST")
        self.assertNotEqual(a, c, "different work still plants its own mirror")

    def test_twins_with_differing_recorded_bodies_stay_apart(self):
        # The label is the judge's RENDERING, which can collapse two REAL dispatches into one
        # string — so the reuse also checks the messages' recorded bodies (the authoritative
        # postal rows). Differing bodies are two dispatches, each keeping its own tracker (the
        # fan-out contract, test_chain_rooted_minting); the ext mailer's same-minute twins carry
        # the SAME body and still fold.
        msgs, mid2 = jd.MESSAGES, "1788299030.000002_2.TESTHOST"
        with tempfile.TemporaryDirectory() as td:
            jd.MESSAGES = Path(td) / "messages.jsonl"
            jd.MESSAGES.write_text("\n".join(json.dumps(r) for r in [
                {"t": T0, "ev": "sent", "id": MID, "from": "web", "from_id": DEAD,
                 "to_id": RCP, "kind": "delegate", "body": "check the vault warning in the deploy log"},
                {"t": T0 + 30, "ev": "sent", "id": mid2, "from": "web", "from_id": DEAD,
                 "to_id": RCP, "kind": "delegate", "body": "check the vault warning in the backup job"}]) + "\n")
            try:
                st = {"rompUuid": DEAD, "seq": 0, "nodes": {}, "placements": {}, "status": {}}
                a = jd._plant_handoff_track(st, None, "check the vault warning", RCP, "api", T0, MID)
                b = jd._plant_handoff_track(st, None, "check the vault warning", RCP, "api", T0 + 30, mid2)
                self.assertNotEqual(a, b, "one judged label over two recorded bodies is two dispatches")
            finally:
                jd.MESSAGES = msgs


if __name__ == "__main__":
    unittest.main()
