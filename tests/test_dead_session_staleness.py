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
Since 2026-09-22 also the mirror's ONE home and its MEANING: rule 5's read and the bus's write meet
on the same file over one state root (ReaderFollowsTheWriter, by execution, under both root shapes).
From the ladder's birth the judge read STATE/remote-sids while the bus wrote STATE/postal/remote-sids,
so rule 5 never fired; the fixtures here wrote the judge's dead path themselves and hid it. Arming the
rule opened two roads to a false settle (fork PR #897, round 1): a bus restarted from empty memory
wrote a first mirror naming nobody, and an expired legacy heartbeat was pruned from the file; the
mirror now says per host whether the bus has heard it in its current process and whether its presence
expired, rule 5 fires only when a REACHABLE host exists and none names the sid, and a sid only an
unreachable host names, a mirror with no reachable host, or a mirror of another shape (a whitespace
list from an older bus) answers cannot-determine, as the dead rule did. Since round 2's third commit
the kernel's link state gates reachability too: a host whose link the kernel holds down cannot vouch
for absence, so it is unreachable from the down notify (which writes the mirror) until its next beat or
exchange arrives with the link up; the writer computes `reachable` per row and the reader reads that
flag. The fixtures here write the bus's document shape (_bus_wrote) and every test that writes one
asserts the ladder's verdict, the rule that answered and its reason, so a fixture at a path nothing
reads turns its test red. SYNTHETIC fixtures only; private synthetic sids; hostname TESTHOST."""
import contextlib
import io
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
REMOTE2 = "a11f0001-1111-4222-8333-000000000004"  # a second remote session, on a host that stays reachable
HOST, HOST2 = "TESTHOST", "TESTHOST2"             # synthetic peer hosts (path-safe names, as the bus keys them)
CARRIED = "a11f0001-1111-4222-8333-000000000005"  # the sid HOST last named before its bus restarted (a peer row)
OTHER = "a11f0001-1111-4222-8333-000000000006"    # the sid HOST2 names: the first host the restarted bus hears

RULE_5 = (True, 5, "no-reachable-host-names-it")               # the ladder's verdicts, (closed, rule, why), as
RULE_4 = (False, 4, "named-by-reachable-host")                 # _presumed_closed_verdict spells them; a fixture
LOST = (False, None, "named-by-unreachable-host")              # written at a path nothing reads answers NO_MIRROR
NO_REACHABLE = (False, None, "no-reachable-host")
NO_MIRROR = (False, None, "no-mirror")
UNPARSABLE = (False, None, "mirror-unparsable")


def _mirror():
    """The deadness mirror where the BUS writes it: the bus's STATE is the judge's plus `postal`
    (postal_service.py _write_remote_sids), and _presumed_closed reads it there. Until 2026-09-22
    these fixtures wrote jd.STATE / "remote-sids", the judge's own read path, which nothing in the
    product wrote; the ladder tests passed against a restatement of the dead path. This helper is
    held to the READER's path by PresumedClosed.test_the_deadness_ladder and DeadSenderSweep's
    test_a_dead_senders_quiet_tracker_closes_on_the_reply_and_settles, each of which reds by its
    verdict assertion when the helper spells another path (the reader then answers no-mirror); the
    reader is held to the WRITER's path and shape by ReaderFollowsTheWriter below, which runs both
    over one root. The helper exists so the fixtures have one spelling to hold."""
    d = jd.STATE / "postal"
    d.mkdir(parents=True, exist_ok=True)
    return d / "remote-sids"


def _row(sids, heard=True, expired=False, kind="peer", link_down=False):
    """One presence-source row as the bus writes it: the roster it last reported, whether the bus heard
    it in its current process, whether its presence expired, whether the kernel holds its link down (or
    has since it was heard), and `reachable`, the writer's flag the reader's verdict reads: heard and not
    expired and not linkDown (postal_service.py _remote_sids_document computes it; a fixture row restates
    the rule so the reader is held to reading the flag, not recomputing it: a heard, unexpired, link-down
    row is unreachable)."""
    return {"kind": kind, "sids": sorted(sids), "heard": heard, "expired": expired, "linkDown": link_down,
            "reachable": heard and not expired and not link_down, "seenAt": NOW - 5}


def _bus_wrote(hosts):
    """Write the mirror in the bus's document shape (postal_service.py _remote_sids_document: v 2 and a
    `hosts` table of rows). A restatement of the writer's shape, held to it by ReaderFollowsTheWriter,
    whose frame pin reads the real writer's document back and asserts these fields."""
    _mirror().write_text(json.dumps({"v": 2, "busStarted": NOW - 100, "writtenAt": NOW, "hosts": hosts}) + "\n")


def _bus_hears_nobody_remote():
    """One reachable host naming no session: rule 5's premise (the bus has spoken and knows no remote sid)."""
    _bus_wrote({HOST: _row([])})


def _bus_hears(*sids):
    """One reachable host naming the sids: live on another host, rule 4."""
    _bus_wrote({HOST: _row(sids)})


def _bus_lost(*sids):
    """The host that last named the sids is unreachable (not heard since the bus started, or expired);
    another host is reachable and names nobody, so the only reason for a False is the lost host's roster."""
    _bus_wrote({HOST: _row(sids, heard=False), HOST2: _row([])})


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

    def _verdict(self, sid):
        """(closed, rule, why): the ladder's verdict for the sid, so a test can assert WHICH rule answered
        and why, not only the boolean, which is the same False under rule 4 and under cannot-determine."""
        v = jd._presumed_closed_verdict(sid, NOW)
        return (v.closed, v.rule, v.why)


class DeadSenderSweep(World):
    def test_a_dead_senders_quiet_tracker_closes_on_the_reply_and_settles(self):
        _bus_hears_nobody_remote()   # the bus has spoken: a reachable host, and it knows no remote session
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        nd = st["nodes"][DEAD + ":g1"]
        self.assertTrue(nd.get("nodeComplete"), "the reply is the event; the sweep is its only writer")
        self.assertEqual(self._verdict(DEAD), RULE_5, "the fixture was read: rule 5 answered for the dead "
                         "sender (a fixture at a path the reader does not read answers no-mirror instead)")
        self.assertEqual(st["status"].get(DEAD + ":g1"), "completed",
                         "a dead determination settles the top: the card leaves Working")

    def test_a_live_remote_mirror_closes_but_never_presumes_settled(self):
        _bus_hears(DEAD)             # the bus says: alive on another host it can reach
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        self.assertTrue(st["nodes"][DEAD + ":g1"].get("nodeComplete"))
        self.assertEqual(self._verdict(DEAD), RULE_4, "the fixture was read: the False below is rule 4's, "
                         "not cannot-determine's (which holds the same status for another reason)")
        self.assertNotEqual(st["status"].get(DEAD + ":g1"), "completed",
                            "a live remote session's mirror store is never premature-settled")

    def test_a_remote_session_the_bus_lost_is_never_presumed_settled(self):
        # The two roads of fork PR #897's round 1 in one shape: the host that last named the sid has not been
        # heard since the bus started (a restart from empty memory), or its beat expired; either way the
        # bus carries its last roster as unreachable, and another host being reachable does not settle it
        _bus_lost(DEAD)
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        self.assertTrue(st["nodes"][DEAD + ":g1"].get("nodeComplete"), "the reply still closes the tracker")
        self.assertEqual(self._verdict(DEAD), LOST, "named only by an unreachable host: cannot determine")
        self.assertNotEqual(st["status"].get(DEAD + ":g1"), "completed",
                            "a sid its host last named is never presumed closed while that host is unreachable")

    def test_a_bus_that_has_heard_no_host_settles_nothing(self):
        # a restarted bus's first mirror: every host carried from the previous file, none heard yet
        _bus_wrote({HOST: _row([], heard=False), HOST2: _row([REMOTE], heard=False)})
        self._dead_sender()
        self._reply(T0 + 500)
        jd.run_propagate(now=NOW)
        st = jd.load_goals(DEAD)
        self.assertTrue(st["nodes"][DEAD + ":g1"].get("nodeComplete"))
        self.assertEqual(self._verdict(DEAD), NO_REACHABLE, "no reachable host: cannot determine")
        self.assertNotEqual(st["status"].get(DEAD + ":g1"), "completed",
                            "a mirror written before the bus heard anyone settles nothing")

    def test_no_reply_leaves_the_tracker_open(self):
        _bus_hears_nobody_remote()
        self._dead_sender()
        jd.run_propagate(now=NOW)
        self.assertEqual(self._verdict(DEAD), RULE_5, "the fixture was read: rule 5 answers for the sid")
        self.assertFalse(jd.load_goals(DEAD)["nodes"][DEAD + ":g1"].get("nodeComplete"),
                         "no report-back event: nothing moves")


class PresumedClosed(World):
    def test_the_deadness_ladder(self):
        self.assertEqual(self._verdict(EXT), (True, 3, "ext"), "ext: is closed by construction")
        # absent everywhere, a reachable host names nobody: dead
        _bus_hears_nobody_remote()
        self.assertEqual(self._verdict(DEAD), RULE_5)
        # a reachable host names it: live on another host, not closed
        _bus_hears(DEAD)
        self.assertEqual(self._verdict(DEAD), RULE_4)
        # only an unreachable host names it (not heard since the bus started): its last word stands
        _bus_lost(DEAD)
        self.assertEqual(self._verdict(DEAD), LOST, "a host the bus cannot reach protects the roster it last reported")
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...and the reachable host settles a sid neither names")
        # the host that names it is heard but its beat expired (the legacy TTL): unreachable the same way
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], heard=True, expired=True, kind="heartbeat"), HOST2: _row([])})
        self.assertEqual(self._verdict(DEAD), LOST, "an expired beat is unreachable, not absent")
        # the host that names it is heard, not expired, and the kernel holds its link down (round 2 of fork PR #897,
        # the reviewer's ruling): unreachable the same way; the reader reads the writer's `reachable`, not heard
        _bus_wrote({HOST: _row([DEAD], link_down=True), HOST2: _row([])})
        self.assertEqual(self._verdict(DEAD), LOST, "a host whose link the kernel holds down cannot vouch: its last "
                         "word stands (a reader recomputing heard and not expired answers rule 4 here)")
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...and the reachable host settles a sid neither names")
        _bus_wrote({HOST: _row([DEAD], link_down=True)})
        self.assertEqual(self._verdict(REMOTE), NO_REACHABLE, "the only heard host is down: nothing can vouch for "
                         "absence (a reader recomputing heard and not expired answers rule 5 here)")
        _bus_wrote({HOST: _row([DEAD], heard=True, expired=False, link_down=False)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "the same host with its link up: rule 5")
        # no reachable host at all (a bus that has heard nobody since it started): cannot determine
        _bus_wrote({HOST: _row([], heard=False), HOST2: _row([REMOTE], heard=False)})
        self.assertEqual(self._verdict(DEAD), NO_REACHABLE)
        self.assertEqual(self._verdict(REMOTE), LOST)
        _bus_wrote({})
        self.assertEqual(self._verdict(DEAD), NO_REACHABLE, "a document with no host is not a host that names nobody")
        # a mirror of another shape (the whitespace list a bus before 2026-09-22 wrote): not an empty roster
        _mirror().write_text("")
        self.assertEqual(self._verdict(DEAD), UNPARSABLE)
        _mirror().write_text(DEAD + "\n")
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a legacy list naming the sid is not read as rule 4 either")
        _mirror().write_text(json.dumps({"hosts": {HOST: {"sids": [DEAD]}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without heard and expired is not a roster row")
        _mirror().write_text(json.dumps({"hosts": {HOST: {"sids": [], "heard": True, "expired": False}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without the link flags is not the shape the bus "
                         "writes since round 2's third commit: never read as reachable by heard alone")
        _mirror().write_text(json.dumps({"hosts": [DEAD]}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE)
        # no mirror file at all: cannot determine, conservative
        _mirror().unlink()
        self.assertEqual(self._verdict(DEAD), NO_MIRROR)
        self.assertFalse(jd._presumed_closed(DEAD, NOW), "_presumed_closed is the verdict's closed alone")

    def test_a_mirror_of_another_shape_is_said_once_in_the_judges_log(self):
        # A reader that cannot parse the mirror says so in the judge's log and answers cannot-determine; it
        # never reads the file as an empty roster (which, with a reachable host, would settle every sid).
        jd._SAID_ONCE.clear()                       # the once-per-text set is process-wide; this test owns its lines
        _mirror().write_text(DEAD + "\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            first = self._verdict(DEAD)
            again = self._verdict(REMOTE)
        self.assertEqual((first, again), (UNPARSABLE, UNPARSABLE))
        lines = [ln for ln in err.getvalue().splitlines() if ln.startswith("romp-judge:")]
        self.assertEqual(len(lines), 1, "said once per distinct text, not per call: %r" % lines)
        self.assertIn(str(_mirror()), lines[0], "the line names the file")
        self.assertIn("not the shape the bus writes", lines[0])
        self.assertIn("cannot-determine", lines[0])
        _mirror().write_text(json.dumps({"hosts": {HOST: {"sids": [DEAD]}}}))
        err2 = io.StringIO()
        with contextlib.redirect_stderr(err2):
            self.assertEqual(self._verdict(DEAD), UNPARSABLE)
        self.assertEqual(len([ln for ln in err2.getvalue().splitlines() if ln.startswith("romp-judge:")]), 1,
                         "a different failure is a different text: said once too")


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
        _bus_hears_nobody_remote()
        jd.run_propagate(now=NOW)
        self.assertEqual(self._verdict(DEAD), RULE_5, "the fixture was read: rule 5 answers for the sender")
        nd = jd.load_goals(DEAD)["nodes"][DEAD + ":g1"]
        self.assertTrue(nd.get("nodeComplete"), "the join formed across the relay's re-stamped id")
        self.assertIn("dismissed", nd.get("doneWhy") or "")


class ReaderFollowsTheWriter(unittest.TestCase):
    """Rule 5's read and the bus's write meet on ONE file with ONE meaning (2026-09-22). The bus writes
    the deadness mirror at its STATE, the romp state root plus `postal`; the judge's STATE is the root
    itself, and from the ladder's birth (2026-08-28) its read was STATE/remote-sids, a path nothing
    wrote: the read raised OSError on every call, rule 5 never fired, every sid reaching it answered
    cannot-determine. Conservative, so nothing settled early; a dead sender's card only took longer to
    settle. Pinned by EXECUTION, not by spelling: the real writer (_write_remote_sids) and the real
    reader (_presumed_closed) run in one fresh interpreter over one temp root, under each of the two
    root shapes the constants bind from (XDG_STATE_HOME, and ROMP_STATE_DIR, which outranks it), and the
    bus's document is read back and its rows asserted, so the fixtures' restatement of the shape
    (_bus_wrote) is held to the writer here. Seven phases, in the order a bus lives them:
      first write   one live remote heartbeat; a sid nothing knows is presumed closed (rule 5), the
                    heartbeating one is not (rule 4);
      restart       a second bus process over the same root (a fresh module object: empty HEARTBEATS and
                    PEER_STATE, as after a real restart) writes its first mirror before any beat arrives,
                    the write _monitor_tick's first poll makes; the host it has not heard is carried from
                    the previous file as unreachable, so the sid it last named is not presumed closed and
                    a sid nothing knows is cannot-determine (no reachable host), the first road of fork PR
                    #897's round 1, which at the round's head settled both;
      heard again   the beat arrives in the new process: rule 5 and rule 4 answer as at the first write;
      expired       the beat's recorded time driven past HEARTBEAT_TTL (no sleeping): the row stays,
                    marked expired, unreachable; its sid is not presumed closed, the second road, which
                    at the round's head pruned the sid and settled it;
      beside a live beat  a second host's live beat: rule 5 fires for a sid nothing knows, rule 4 holds
                    the live one, and the expired one is still protected by its host's last word;
      another host heard first  peer mode's rows, a host under its name with the roster its exchange
                    reported: an exchange from host A naming its sid lands, the bus restarts a second time,
                    and an exchange from host B, naming B's sid alone, is the new process's first write. A
                    is carried unreachable and its last word holds its sid at cannot-determine; B's sid is
                    rule 4's; a sid nothing names is rule 5's. A's exchange arriving makes it reachable
                    (rule 4), and A's next exchange without the sid lets rule 5 presume it closed. The one
                    composition in which the carry-forward changes the VERDICT rather than the file alone
                    (round 2 of fork PR #897, a verifier's finding): a writer that carried nothing leaves
                    A's sid to rule 5 here, True, a live session settled because its bus restarted, while
                    every earlier phase's verdict pins hold under that writer;
      link held down  the kernel's link state gates reachability (round 2 of fork PR #897, the reviewer's
                    ruling: a session started on a host after its last heard roster is in no roster, so a
                    host counted reachable while its link is down would let rule 5 presume it closed; a host
                    that is down cannot vouch for absence). After a third restart host B's exchange makes it
                    the one reachable source; the kernel's down notify for B, through the real handler
                    (peer_update), writes the mirror itself: B's sid is cannot-determine by B's last word
                    (not rule 4: a host the bus cannot vouch for makes no positive determination) and a sid
                    nothing names is cannot-determine, no reachable host, where a gate on heard alone answers
                    rule 5. The up notify alone changes nothing (B's roster is the one from before the drop);
                    B's exchange arriving with the link up is the event: rule 4 and rule 5 answer again. Then
                    B down beside host A heard, a host the kernel never notified (no link state: heard
                    alone): A is reachable, B's sid stays protected, and a sid nothing names is rule 5's (the
                    down host protects the sids it last named, it is not a gate on the mirror, as a carried
                    host is not);
      legacy shape  the whitespace list a bus before 2026-09-22 wrote, at the bus's path: the reader
                    answers cannot-determine for the sid it does not name AND for the one it does, and
                    says once in the judge's log that the file is not the shape the bus writes; it is
                    never read as an empty roster.
    The control isolates the old path: with the bus's file removed and a line at STATE/remote-sids, the
    judge's read path until 2026-09-22, the reader answers cannot-determine, so the read MOVED to the
    bus's file rather than widening to both, and a reverted read fails this pin by its own message. The
    proof that the rule itself was sound, and only its path dead, is the same control run at the base of
    the first commit on this branch, where the bytes at the old path answered True, the only way rule 5
    could fire then; the message of the review fix-up commit of 2026-09-22 on this branch records that run
    (6 failed, 4 passed; the control red on True is not false). It is not asserted here, where it can no
    longer hold. The bus's file is removed FIRST: this control's first form left it in place and asserted
    True, which held because the bus's file was read, not the old path's (a pin true for a reason other
    than its message). The root carries `session-hosts` off, the repo rule for a test that mints its own
    state root, and the child reads that file back through the judge's STATE, so the root the test
    prepared is the root both modules bound."""

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
        # floor does not arm, so the environment above is the whole of it). The phases the class docstring
        # names, each recording the bus's document (`hosts`: key -> (heard, expired, sids), or the raw text when
        # the file is not a document, so a writer of another shape fails the frame pin by its message rather
        # than crashing the child) and the reader's answers. Each restart is a further load of the bus module
        # under a private name: a fresh module object over the same root, its memory empty, as a restarted
        # process's is. A missing bus file is reported, not raised, so a moved writer fails the pins by their
        # own messages. The source sits as a literal in the argv slot after "-c": the shape the hosts-on census
        # (tests/test_tempdir_hygiene.py, HarnessSocketBudget's ledger) reads as a child Python's source, parsing
        # the literal as a nested module, where the child's read of the session-hosts toggle is a read; a
        # module-level name bound to the same text is not followed into the child, and the whole text stood
        # unaccounted (the sweep red of 2026-09-22).
        out = subprocess.run([sys.executable, "-c", r"""
import contextlib, io, json, os, sys, time
tests_dir, bin_dir, remote, remote2, dead, host_a, host_b, carried, other = sys.argv[1:10]
sys.path.insert(0, tests_dir)
from romp_load import load_source
pm = load_source("romp_postal_oneroot", os.path.join(bin_dir, "romp-postal-service"))
jd = load_source("romp_judge_oneroot", os.path.join(bin_dir, "romp-judge"))
now = time.time()
bus_file = pm.STATE / "remote-sids"
def ask(sid):
    return jd._presumed_closed(sid, now)
def hosts():
    if not bus_file.exists():
        return None
    text = bus_file.read_text()
    try:
        return {k: [r["heard"], r["expired"], r["sids"]] for k, r in json.loads(text)["hosts"].items()}
    except (ValueError, KeyError, TypeError):
        return text
def phase():
    return {"hosts": hosts(), "fire": ask(dead), "named": ask(remote), "named2": ask(remote2)}
out = {"busState": str(pm.STATE), "judgeState": str(jd.STATE), "busFile": str(bus_file),
       "hostsOff": (jd.STATE / "session-hosts").read_text().strip(),
       "discovered": len(jd.discover(now)) + len(jd.discover(now, window=now)),
       "beforeWrite": ask(dead)}
pm.STATE.mkdir(parents=True, exist_ok=True)
pm.HEARTBEATS[remote] = ("web", now)               # the first bus process hears one live remote session
pm._write_remote_sids()
out["first"] = phase()
out["firstRow"] = json.loads(bus_file.read_text())["hosts"].get("heartbeat:" + remote) if bus_file.exists() else None
pm2 = load_source("romp_postal_oneroot_restarted", os.path.join(bin_dir, "romp-postal-service"))
out["restartMemory"] = {"heartbeats": len(pm2.HEARTBEATS), "peers": len(pm2.PEER_STATE),
                        "sameFile": str(pm2.STATE / "remote-sids") == str(bus_file), "freshObject": pm2 is not pm}
pm2._write_remote_sids()                           # the first poll's write, before any beat arrives
out["restarted"] = phase()
pm2.HEARTBEATS[remote] = ("web", time.time())      # the beat arrives in the new process
pm2._write_remote_sids()
out["heardAgain"] = phase()
pm2.HEARTBEATS[remote] = ("web", time.time() - pm2.HEARTBEAT_TTL - 1)   # the recorded time, past the TTL
pm2._write_remote_sids()
out["expired"] = phase()
pm2.HEARTBEATS[remote2] = ("api", time.time())     # a second host's live beat beside the expired one
pm2._write_remote_sids()
out["besideLive"] = phase()
def verdict(sid):
    return list(jd._presumed_closed_verdict(sid, now))          # [closed, rule, why]: the verdict and its reason
def peer_phase():
    return {"hosts": hosts(), "carried": verdict(carried), "other": verdict(other), "nobody": verdict(dead)}
def exchange(bus, host, sids):                     # one exchange landing: what peer_exchange_handle/apply record, then write
    bus.PEER_STATE[host] = {"presence": [{"id": s, "name": "api"} for s in sids], "epoch": 1, "holds": [],
                            "seenAt": int(time.time())}
    bus._write_remote_sids()
exchange(pm2, host_a, [carried])                   # host A's exchange names its sid in the running bus
out["peerHeard"] = peer_phase()
pm3 = load_source("romp_postal_oneroot_restarted_twice", os.path.join(bin_dir, "romp-postal-service"))
out["restartMemory2"] = {"heartbeats": len(pm3.HEARTBEATS), "peers": len(pm3.PEER_STATE), "freshObject": pm3 is not pm2}
exchange(pm3, host_b, [other])                     # host B is heard FIRST: the new process's first write, nothing from A yet
out["otherHeardFirst"] = peer_phase()
exchange(pm3, host_a, [carried])                   # A's exchange arrives in the new process, its roster unchanged
out["carriedHeard"] = peer_phase()
exchange(pm3, host_a, [])                          # A's next exchange no longer names the sid: it ended there
out["carriedHostNamesNobody"] = peer_phase()
def link_phase():                                  # the rows with their link flags, and the verdicts (the link held down phase)
    rows = None
    if bus_file.exists():
        text = bus_file.read_text()
        try:
            rows = {k: [r["heard"], r["expired"], r["linkDown"], r["reachable"], r["sids"]] for k, r in json.loads(text)["hosts"].items()}
        except (ValueError, KeyError, TypeError):
            rows = text
    return {"hosts": rows, "other": verdict(other), "nobody": verdict(dead)}
pm4 = load_source("romp_postal_oneroot_restarted_thrice", os.path.join(bin_dir, "romp-postal-service"))
pm4._peer_threads_reconcile = lambda host: None    # the notify's dialer bookkeeping is not under test (an up notify would dial a loopback port nothing listens on)
out["restartMemory3"] = {"heartbeats": len(pm4.HEARTBEATS), "peers": len(pm4.PEER_STATE), "links": len(pm4.PEERS), "freshObject": pm4 is not pm3}
exchange(pm4, host_b, [other])                     # B heard: the one reachable source (every other row carried, unreachable)
out["linkHeard"] = link_phase()
def notify(host, up):                              # the kernel's /peer notify, through the real handler, which writes the mirror itself
    return list(pm4.peer_update({"host": host, "port": 50002, "up": up}))
out["linkDownNotify"] = notify(host_b, False)
out["linkDown"] = link_phase()                     # nothing wrote between the notify and this read
out["linkUpNotify"] = notify(host_b, True)
out["linkUpUnheard"] = link_phase()                # the link is back; B has not been heard since it dropped
exchange(pm4, host_b, [other])                     # B's exchange with the link up: the event
out["linkUpHeard"] = link_phase()
notify(host_b, False)
exchange(pm4, host_a, [])                          # A heard beside the down host; the kernel never notified A: no link state
out["heardBesideDown"] = link_phase()
bus_file.write_text(remote + "\n")                 # the shape a bus before 2026-09-22 wrote
err = io.StringIO()
with contextlib.redirect_stderr(err):
    legacy = {"fire": ask(dead), "named": ask(remote), "fireAgain": ask(dead)}
legacy["log"] = err.getvalue()
out["legacy"] = legacy
bus_file.unlink(missing_ok=True)
out["busFileGoneForControl"] = not bus_file.exists()
old_path = jd.STATE / "remote-sids"
old_path.write_text(remote + "\n")
out["oldPath"] = str(old_path)
out["oldPathText"] = old_path.read_text()
out["controlOldPathOnly"] = ask(dead)
print(json.dumps(out))
""", HERE, BIN, REMOTE, REMOTE2, DEAD, HOST, HOST2, CARRIED, OTHER], capture_output=True, text=True, env=full,
                             cwd=str(home), timeout=120)
        assert out.returncode == 0, "%s child failed: %s" % (shape, out.stderr[-2000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        got["root"] = str(root)
        return got

    HB = "heartbeat:"       # the bus keys a legacy heartbeat's row heartbeat:<sid> (postal_service.py REMOTE_SIDS_HEARTBEAT)

    @staticmethod
    def _v(phase, key):
        """A recorded verdict, (closed, rule, why), as the RULE_5 / RULE_4 / LOST constants spell them."""
        return tuple(phase[key])

    def test_both_modules_bound_the_one_root_the_test_prepared(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["judgeState"], got["root"], "the judge's STATE is the root")
                self.assertEqual(got["busState"], got["root"] + "/postal", "the bus's STATE is the root plus postal")
                self.assertEqual(got["hostsOff"], "off", "the child read the session-hosts file the test wrote")
                self.assertEqual(got["discovered"], 0, "an empty HOME: rules 1 and 2 have no session to answer for")
                self.assertEqual(got["first"]["hosts"], {self.HB + REMOTE: [True, False, [REMOTE]]},
                                 "the writer's document at %s: one row per presence source, the heartbeating sid's "
                                 "row heard and not expired (the fixtures' _bus_wrote restates this shape)" % got["busFile"])
                row = dict(got["firstRow"] or {})
                self.assertIsInstance(row.pop("seenAt", None), int, "seenAt, the beat's time")
                self.assertEqual(row, {"kind": "heartbeat", "sids": [REMOTE], "heard": True, "expired": False,
                                       "linkDown": False, "reachable": True, "name": "web"},
                                 "the row's fields as the writer spells them, the four flags among them: the fixtures' "
                                 "_row restates every one, and the reader requires the four")

    def test_rule_5_fires_for_a_sid_nothing_knows_once_the_bus_has_written(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertFalse(got["beforeWrite"], "no mirror file yet: cannot determine, conservative")
                self.assertTrue(got["first"]["fire"], "the bus wrote %s; the judge's read must be that file: rule 5 "
                                "presumes a sid nothing knows closed" % got["busFile"])

    def test_rule_4_holds_the_sid_the_bus_names_open(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertTrue(got["first"]["fire"], "rule 5 fired in this run, so the False below is rule 4's, "
                                "not cannot-determine's")
                self.assertFalse(got["first"]["named"], "live on another host: never presumed settled")

    def test_a_restarted_bus_carries_the_host_it_has_not_heard_as_unreachable(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory"], {"heartbeats": 0, "peers": 0, "sameFile": True, "freshObject": True},
                                 "the restart is a fresh module object over the same root, its memory empty")
                self.assertEqual(got["restarted"]["hosts"], {self.HB + REMOTE: [False, False, [REMOTE]]},
                                 "the first mirror of a restarted bus carries the host the previous file named, "
                                 "its last roster kept, heard=false: unreachable, not absent")
                self.assertFalse(got["restarted"]["named"], "the sid its host last named is not presumed closed "
                                 "while the new bus process has not heard that host (the first road of fork PR #897's "
                                 "round 1: a first write from empty memory settled it)")
                self.assertFalse(got["restarted"]["fire"], "no reachable host yet: a sid nothing knows is "
                                 "cannot-determine, as the dead rule answered")
                self.assertEqual(got["heardAgain"]["hosts"], {self.HB + REMOTE: [True, False, [REMOTE]]},
                                 "the beat arriving in the new process is the event that makes the host reachable")
                self.assertTrue(got["heardAgain"]["fire"], "rule 5 fires again once a host is reachable")
                self.assertFalse(got["heardAgain"]["named"], "rule 4 holds the live sid")

    def test_an_expired_beat_stays_in_the_mirror_as_unreachable(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["expired"]["hosts"], {self.HB + REMOTE: [True, True, [REMOTE]]},
                                 "past HEARTBEAT_TTL the row stays, marked expired, its roster kept (the shape "
                                 "before this change pruned it)")
                self.assertFalse(got["expired"]["named"], "a sid whose beat expired is not presumed closed on no "
                                 "new information (the second road of fork PR #897's round 1)")
                self.assertFalse(got["expired"]["fire"], "the only host is unreachable: cannot determine")
                self.assertEqual(got["besideLive"]["hosts"], {self.HB + REMOTE: [True, True, [REMOTE]],
                                                              self.HB + REMOTE2: [True, False, [REMOTE2]]},
                                 "a second host's live beat beside the expired one")
                self.assertTrue(got["besideLive"]["fire"], "a reachable host that names neither: rule 5 fires for "
                                "a sid nothing knows")
                self.assertFalse(got["besideLive"]["named2"], "rule 4 holds the live sid")
                self.assertFalse(got["besideLive"]["named"], "the expired host's last word still protects its sid")

    def test_another_host_heard_first_after_a_restart_does_not_settle_the_carried_hosts_sid(self):
        """The composition in which the carry-forward changes the VERDICT, not only the file (round 2 of fork PR
        #897, a verifier's finding: the phases above reach each restart with one host, so a writer that carried
        nothing passed every verdict pin there and was red only at the document pins). Host A, a peer, names a
        sid; the bus restarts; host B is heard first. Without the carry-forward B's row is the whole mirror, B
        is reachable and names only its own sid, and rule 5 presumes A's sid closed: a live session settled
        because its bus restarted. With it A's row is carried unreachable and its last word holds the sid at
        cannot-determine until A is heard; A's next exchange without the sid is the event that lets rule 5
        answer. The verdict and its reason at every step, then the document."""
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._v(got["peerHeard"], "carried"), RULE_4,
                                 "before the restart the peer host names its sid: live on another host")
                self.assertEqual(got["restartMemory2"], {"heartbeats": 0, "peers": 0, "freshObject": True},
                                 "the second restart is a fresh module object too, its memory empty")
                first = got["otherHeardFirst"]
                self.assertEqual(self._v(first, "carried"), LOST,
                                 "another host was heard first, reachable, naming its own sid alone; the host that last "
                                 "named this sid has not been heard by the new process, so its carried word stands: "
                                 "cannot-determine (a writer carrying nothing leaves this sid to rule 5, True, a live "
                                 "session settled because its bus restarted)")
                self.assertEqual(self._v(first, "other"), RULE_4, "the heard host's own sid: rule 4")
                self.assertEqual(self._v(first, "nobody"), RULE_5,
                                 "a reachable host exists and no row names this sid: rule 5 answers beside the carried "
                                 "host; the carried row protects its own sids, it is not a gate on the mirror")
                self.assertEqual(first["hosts"], {self.HB + REMOTE: [False, True, [REMOTE]],
                                                  self.HB + REMOTE2: [False, False, [REMOTE2]],
                                                  HOST: [False, False, [CARRIED]], HOST2: [True, False, [OTHER]]},
                                 "the document: every row of the previous file carried, heard false, its marks kept, "
                                 "beside the heard host's row")
                heard = got["carriedHeard"]
                self.assertEqual(self._v(heard, "carried"), RULE_4,
                                 "the carried host's exchange arriving in the new process is the event that makes it "
                                 "reachable: its sid is rule 4's")
                self.assertEqual(heard["hosts"][HOST], [True, False, [CARRIED]], "heard, the roster it reported")
                gone = got["carriedHostNamesNobody"]
                self.assertEqual(self._v(gone, "carried"), RULE_5,
                                 "the host that named the sid, reachable, no longer names it, and no unreachable host "
                                 "does: rule 5 presumes it closed, on that exchange and nothing else")
                self.assertEqual(self._v(gone, "other"), RULE_4, "the other host's sid stays rule 4's")
                self.assertEqual(gone["hosts"][HOST], [True, False, []], "heard, naming nobody")

    def test_a_host_the_kernel_holds_down_cannot_vouch_until_heard_with_the_link_up(self):
        """Round 2 of fork PR #897, the reviewer's ruling: the kernel's link state gates reachability. The verdict and
        its reason at every step, then the document, so a writer gating on heard alone reds at a verdict."""
        L = lambda heard, expired, down, reach, sids: [heard, expired, down, reach, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory3"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the third restart is a fresh module object, its memory and its link table empty")
                heard = got["linkHeard"]
                self.assertEqual(self._v(heard, "other"), RULE_4, "heard, its link never reported down: rule 4")
                self.assertEqual(self._v(heard, "nobody"), RULE_5, "one reachable host names nobody unknown: rule 5")
                self.assertEqual(got["linkDownNotify"], [{"ok": True, "up": 0}, 200], "the handler took the down notify")
                down = got["linkDown"]
                self.assertEqual(self._v(down, "other"), LOST,
                                 "the host that names it is heard but the kernel holds its link down: its last word "
                                 "stands and rule 4 does not fire (a host the bus cannot vouch for makes no positive "
                                 "determination); a gate on heard alone answers rule 4 here")
                self.assertEqual(self._v(down, "nobody"), NO_REACHABLE,
                                 "the only heard host is down: nothing can vouch for absence, cannot-determine; a gate "
                                 "on heard alone presumes a session started there since the drop closed, rule 5")
                self.assertEqual(down["hosts"][HOST2], L(True, False, True, False, [OTHER]),
                                 "marked link-down by the notify's own write, nothing else having written: unreachable, "
                                 "roster kept (a writer waiting for the next tick leaves the row reachable here)")
                unheard = got["linkUpUnheard"]
                self.assertEqual(got["linkUpNotify"], [{"ok": True, "up": 1}, 200])
                self.assertEqual((self._v(unheard, "other"), self._v(unheard, "nobody")), (LOST, NO_REACHABLE),
                                 "the up notify alone is not the event: the roster is the one heard before the link "
                                 "dropped and says nothing about a session started there since")
                self.assertEqual(unheard["hosts"][HOST2], L(True, False, True, False, [OTHER]))
                up = got["linkUpHeard"]
                self.assertEqual((self._v(up, "other"), self._v(up, "nobody")), (RULE_4, RULE_5),
                                 "its exchange arriving with the link up is the event: reachable, rule 4 and rule 5 again")
                self.assertEqual(up["hosts"][HOST2], L(True, False, False, True, [OTHER]))
                beside = got["heardBesideDown"]
                self.assertEqual(self._v(beside, "other"), LOST, "the down host's last word still protects its sid")
                self.assertEqual(self._v(beside, "nobody"), RULE_5,
                                 "a host the kernel never notified is heard beside the down one: reachable on heard alone, "
                                 "and a sid nothing names is rule 5's (the down host protects the sids it last named; it "
                                 "is not a gate on the mirror, as a carried host is not)")
                self.assertEqual((beside["hosts"][HOST], beside["hosts"][HOST2]),
                                 (L(True, False, False, True, []), L(True, False, True, False, [OTHER])),
                                 "no link state for the never-notified host; the down host's row as the notify left it")

    def test_a_mirror_of_the_legacy_shape_is_cannot_determine_and_said_once(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                leg = got["legacy"]
                self.assertFalse(leg["fire"], "a whitespace list at %s is not read as an empty roster: the sid it "
                                 "does not name is cannot-determine" % got["busFile"])
                self.assertFalse(leg["named"], "nor as a roster: the sid it names is cannot-determine too")
                lines = [ln for ln in leg["log"].splitlines() if ln.startswith("romp-judge:")]
                self.assertEqual(len(lines), 1, "the judge says once, in its log, that the file is not the shape "
                                 "the bus writes: %r" % lines)
                self.assertIn(got["busFile"], lines[0], "the line names the file")
                self.assertIn("not the shape the bus writes", lines[0])

    def test_the_control_the_old_path_alone_is_no_longer_read(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertTrue(got["busFileGoneForControl"], "the control isolates the old path: the "
                                "bus's file %s is removed before the old path is written" % got["busFile"])
                self.assertEqual(got["oldPathText"], REMOTE + "\n", "the writer's line sits at %s, the "
                                 "judge's read path until 2026-09-22" % got["oldPath"])
                self.assertFalse(got["controlOldPathOnly"], "with only the old path populated the judge "
                                 "answers cannot-determine: the read moved to the bus's file and no longer "
                                 "reaches %s (at the base the same bytes there answered True)" % got["oldPath"])


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
