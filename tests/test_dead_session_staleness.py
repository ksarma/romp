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
flag, and the two cannot-determine reasons that turn on a source's state name the sources and what makes
each unreachable (the fourth commit). Since the fifth commit the rule is two-sided (the reviewer's ruling): a
heard host that is not held down vouches for the PRESENCE of the sids it names (`reachable`, rule 4), and a
host vouches for the ABSENCE of a sid it does not name (`vouchesAbsence`, rule 5's precondition) only when
its link is KNOWN UP (a dialable PEERS row up and the host heard since the link last dropped; a legacy
heartbeat within its TTL vouches as before, having no link), so a heard host with no link state (a host the
kernel never notified, a far bus filed under the hostname it declares before this bus's own dial folds it
under the alias the kernel dials) answers cannot-determine for a sid it does not name, as a down host does.
Since round 3 a hub's word about a host this bus also holds directly is never discarded (the reviewer's ruling):
it folds into that host's own row only while the row is heard and not held down, matched by bus id or by a name
the row carries no different known bus id under, and stands as a via row (via:<hub>/<far>) beside a held-down or
a carried direct row, or a row that is another bus by the ids (another machine the hub calls by that name, or the
far bus restarted under a new id one side has not heard), so a session the hub names on that host is rule 4's
while the hub vouches and never rule 5's, and the via row is dropped once the host speaks again or the hub's
current word about it folds (the hub's word phase; at round 2's head the fold applied whatever the direct row's
state, and rule 5 settled that session; at the seventh commit a name match folded whatever the ids, and rule 5
settled the session on the other machine, the reviewer's verifier's finding).
The fixtures here write the bus's document shape (_bus_wrote) and every test that writes one
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
FARSID = "a11f0001-1111-4222-8333-000000000007"   # the sid a far bus names when it dials us under its declared hostname
ALIAS, DECLARED = "TESTHOST-alias", "TESTHOST-hostname"   # the name the kernel dials a far bus by, and the one it declares
GOSSIPED = "a11f0001-1111-4222-8333-000000000008"  # a session started on HOST2 while the kernel holds its link down: the hub names it
LATER = "a11f0001-1111-4222-8333-000000000009"    # a session started on HOST2 across a bus restart: the hub names it before HOST2 is heard
COLLIDED = "a11f0001-1111-4222-8333-000000000010"  # a session on ANOTHER machine the hub calls by HOST2's name (its own bus id): the name collision
HUB = "TESTHOST-hub"                              # a hub peered with HOST2 too, gossiping HOST2's sessions to us
VIA_B = "via:" + HUB + "/" + HOST2                # the key of the hub's word about HOST2 (postal_service.py REMOTE_SIDS_VIA)
ENDED = "a11f0001-1111-4222-8333-000000000011"    # a session started on HOST2 while its link was held down, named by the hub, ended
#                                                   across a bus restart: HOST2 heard first afterwards does not name it
DECL_NAMED = "a11f0001-1111-4222-8333-000000000012"   # a session on HOST2 the hub named while filed under the hostname it declares,
#                                                       ended before this bus's own dial folded the hub under its alias
SPOKE_KEPT = "a11f0001-1111-4222-8333-000000000013"   # a session on a far host nobody holds directly (the spoke), gossiped by the
#                                                       hub under both of its names for the spoke
SPOKE_GONE = "a11f0001-1111-4222-8333-000000000014"   # a spoke session that ended across the hub's rename of the spoke
HUB_DECLARED = "TESTHOST-hub-hostname"            # the hostname the hub declares when its own dial lands here before ours
SPOKE, SPOKE_DECLARED = "TESTHOST-spoke", "TESTHOST-spoke-hostname"   # the far host the hub gossips, and the name the spoke
#                                                                       declared to the hub before the hub's own dial folded it
VIA_B_DECLARED = "via:" + HUB_DECLARED + "/" + HOST2                  # the hub's word about HOST2 under the hub's declared name
VIA_SPOKE, VIA_SPOKE_DECLARED = "via:" + HUB + "/" + SPOKE, "via:" + HUB + "/" + SPOKE_DECLARED
VIA_SPOKE_UNDER_DECLARED = "via:" + HUB_DECLARED + "/" + SPOKE_DECLARED   # the hub's first word about the spoke, under both first names
HUB2 = "TESTHOST-hub2"                            # a second hub peered with the spoke too, whose roster of the spoke is older than the hub's
VIA_SPOKE2 = "via:" + HUB2 + "/" + SPOKE          # the second hub's word about the spoke, its own row under its own key
SPOKE_NEW = "a11f0001-1111-4222-8333-000000000015"   # a session started on the spoke since the second hub's roster of it, named by the
#                                                      hub alone; it ends across a bus restart, before the hub is heard again

RULE_5 = (True, 5, "no-reachable-host-names-it")               # the ladder's verdicts, (closed, rule, why), as
RULE_4 = (False, 4, "named-by-reachable-host")                 # _presumed_closed_verdict spells them; a fixture
NO_MIRROR = (False, None, "no-mirror")                         # written at a path nothing reads answers NO_MIRROR
UNPARSABLE = (False, None, "mirror-unparsable")


def LOST(*sources):
    """The cannot-determine verdict for a sid named only by unreachable sources: the reason names each source
    that names it with what makes it unreachable, hand-spelled here as "<key> (<cause>[, <cause>])" with the
    causes in the order not heard, expired, link down, no link state (round 2 of fork PR #897, the reviewer's
    ruling: the reason names the down host). The expected text is this module's, not the reader's formatter."""
    return (False, None, "named-by-unreachable-host: " + ", ".join(sources))


def NO_VOUCH(*sources):
    """The cannot-determine verdict when no source vouches for a sid's absence: the reason names every source in
    the mirror, sorted by key, each with why it cannot vouch (not heard, expired, link down, or no link state: a
    heard host the kernel never reported up, which vouches for presence alone), in the same hand-spelled form; a
    mirror with no row at all reads "no source" (spelled at that site). Until the fifth commit of round 2 this
    arm's token was no-reachable-host, which would lie when a reachable host exists whose link is unknown."""
    return (False, None, "no-host-vouches-absence: " + ", ".join(sources))


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


def _row(sids, heard=True, expired=False, kind="peer", link_down=False, link_up=False):
    """One presence-source row as the bus writes it: the roster it last reported, whether the bus heard
    it in its current process, whether its presence expired, whether the kernel holds its link down (or
    has since it was heard), whether the kernel holds its link up and it was heard since the link last
    dropped, and the writer's two flags the reader's verdict reads: `reachable`, heard and not expired and
    not linkDown (it vouches for the presence of the sids it names), and `vouchesAbsence`, heard and not
    expired and (linkUp, or a legacy heartbeat, which vouches by its TTL) (it vouches for the absence of a
    sid it does not name). postal_service.py _remote_sids_document computes both; a fixture row restates
    the rules so the reader is held to reading the flags, not recomputing them: a heard, unexpired,
    link-down row is unreachable, and a heard, unexpired peer row with no link state (link_up False, the
    default here: a host the kernel never reported up) is reachable and does not vouch for absence. A row
    NOT heard can carry link_up True (the kernel's seed of a tunnel up at a restart, before any exchange):
    it vouches for nothing, heard being the first condition of both flags."""
    return {"kind": kind, "sids": sorted(sids), "heard": heard, "expired": expired, "linkDown": link_down,
            "linkUp": link_up, "reachable": heard and not expired and not link_down,
            "vouchesAbsence": heard and not expired and (link_up or kind == "heartbeat"), "seenAt": NOW - 5}


def _bus_wrote(hosts):
    """Write the mirror in the bus's document shape (postal_service.py _remote_sids_document: v 2 and a
    `hosts` table of rows). A restatement of the writer's shape, held to it by ReaderFollowsTheWriter,
    whose frame pin reads the real writer's document back and asserts these fields."""
    _mirror().write_text(json.dumps({"v": 2, "busStarted": NOW - 100, "writtenAt": NOW, "hosts": hosts}) + "\n")


def _bus_hears_nobody_remote():
    """One host naming no session, heard with its link known up, so it vouches for absence: rule 5's premise
    (the bus has spoken and knows no remote sid)."""
    _bus_wrote({HOST: _row([], link_up=True)})


def _bus_hears(*sids):
    """One host naming the sids, heard with its link up: live on another host, rule 4."""
    _bus_wrote({HOST: _row(sids, link_up=True)})


def _bus_lost(*sids):
    """The host that last named the sids is unreachable (not heard since the bus started, or expired);
    another host, heard with its link up, names nobody and vouches for absence, so the only reason for a
    False is the lost host's roster."""
    _bus_wrote({HOST: _row(sids, heard=False), HOST2: _row([], link_up=True)})


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
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (not heard)"),
                         "named only by an unreachable host: cannot determine, the reason naming the host and why")
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
        self.assertEqual(self._verdict(DEAD), NO_VOUCH(HOST + " (not heard)", HOST2 + " (not heard)"),
                         "no host vouches for absence: cannot determine, every source named with why")
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
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (not heard)"),
                         "a host the bus cannot reach protects the roster it last reported; the reason names it")
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...and the reachable host settles a sid neither names")
        # the host that names it is heard but its beat expired (the legacy TTL): unreachable the same way
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], heard=True, expired=True, kind="heartbeat"), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(DEAD), LOST("heartbeat:" + DEAD + " (expired)"), "an expired beat is unreachable, not absent")
        # the host that names it is heard, not expired, and the kernel holds its link down (round 2 of fork PR #897,
        # the reviewer's ruling): unreachable the same way; the reader reads the writer's `reachable`, not heard
        _bus_wrote({HOST: _row([DEAD], link_down=True), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (link down)"),
                         "a host whose link the kernel holds down cannot vouch: its last word stands, and the reason "
                         "names the down host (a reader recomputing heard and not expired answers rule 4 here)")
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...and the host with its link up settles a sid neither names")
        # a host heard with NO link state (the fifth commit, the reviewer's ruling: a source vouches for absence only
        # when its link is known up): it vouches for the presence of the sid it names and for nothing else
        _bus_wrote({HOST: _row([DEAD], heard=True, expired=False, link_down=False, link_up=False)})
        self.assertEqual(self._verdict(DEAD), RULE_4, "heard and not held down: the sid it names is live on another host")
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (no link state)"),
                         "the only heard host has no link state (the kernel never reported it up: never notified, or a "
                         "far bus filed under the hostname it declares before the fold): it does not vouch for absence, "
                         "and the reason says so (a reader gating rule 5 on `reachable` answers rule 5 here, the road the "
                         "fourth commit disclosed; the old token no-reachable-host would lie, a reachable host exists)")
        _bus_wrote({HOST: _row([DEAD], link_up=False), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...beside a host with its link known up, a sid neither names is "
                         "rule 5's: the host with no link state is not a gate on the mirror")
        self.assertEqual(self._verdict(DEAD), RULE_4, "...and the sid it names stays rule 4's")
        _bus_wrote({HOST: _row([DEAD], link_down=True)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (link down)"),
                         "the only heard host is down: nothing can vouch for absence, and the reason names the down host "
                         "(a reader recomputing heard and not expired answers rule 5 here)")
        # a host carried from before the restart AND held down by the kernel (the notify for a host not heard yet):
        # both causes, in the reason's fixed order
        _bus_wrote({HOST: _row([DEAD], heard=False, link_down=True)})
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (not heard, link down)"), "every cause, not heard first")
        _bus_wrote({HOST: _row([DEAD], heard=True, expired=False, link_down=False, link_up=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "the same host with its link known up: rule 5")
        # the kernel's seed of a link up at a restart, the host not heard yet (a verifier's finding at round 2's fifth
        # commit): the link alone vouches for nothing; the reader reads the writer's vouchesAbsence, False, not linkUp
        _bus_wrote({HOST: _row([DEAD], heard=False, link_up=True)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (not heard)"),
                         "a carried host whose link the kernel seeded up: not heard, so it vouches for nothing and a sid it "
                         "does not name is cannot-determine (a reader gating rule 5 on linkUp answers rule 5 here)")
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (not heard)"), "...and the sid it names is held by its last word")
        # no host vouches for absence at all (a bus that has heard nobody since it started): cannot determine
        _bus_wrote({HOST: _row([], heard=False), HOST2: _row([REMOTE], heard=False)})
        self.assertEqual(self._verdict(DEAD), NO_VOUCH(HOST + " (not heard)", HOST2 + " (not heard)"))
        self.assertEqual(self._verdict(REMOTE), LOST(HOST2 + " (not heard)"))
        # the reason sorts the sources by key, not by the order the file lists them: the second-listed host first
        _bus_wrote({HOST2: _row([DEAD], heard=False), HOST: _row([], link_down=True)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (link down)", HOST2 + " (not heard)"),
                         "sorted by key (a reader taking the file's order names the second-listed host first)")
        self.assertEqual(self._verdict(DEAD), LOST(HOST2 + " (not heard)"), "only the sources that name the sid")
        _bus_wrote({})
        self.assertEqual(self._verdict(DEAD), NO_VOUCH("no source"), "a document with no host is not a host that "
                         "names nobody; the reason says there is no source")
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
        _mirror().write_text(json.dumps({"hosts": {HOST: {"sids": [], "heard": True, "expired": False, "linkDown": False,
                                                          "reachable": True}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without linkUp and vouchesAbsence is not the shape the "
                         "bus writes since round 2's fifth commit: never read as vouching for absence by reachable alone")
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
    (_bus_wrote) is held to the writer here. Thirteen phases, in the order a bus lives them:
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
                    every earlier phase's verdict pins hold under that writer. Since the fifth commit the
                    kernel's up notify for a host precedes its exchange in this phase and the next, as in the
                    real bus, where the kernel notifies a tunnel before the bus dials it: a host heard with no
                    link state vouches for presence alone, so rule 5 needs a host the kernel holds up;
      link held down  the kernel's link state decides what a source vouches for (round 2 of fork PR #897,
                    the reviewer's ruling: a session started on a host after its last heard roster is in no
                    roster, so a host counted as vouching for absence while its link is down would let rule
                    5 presume it closed; a host that is down cannot vouch for absence). After a third restart
                    the kernel's up notify for host B, before any exchange (the seed from /tunnels, or the
                    re-notify, as every restarted bus's kernel does), reaches B's carried row: linkUp and not
                    heard, it vouches for nothing, so B's sid is held by its last word and a sid nothing names
                    is cannot-determine (a writer vouching for absence by the link alone lets rule 5 settle it
                    on the restarted bus's first write: the primary restart road, a verifier's finding at the
                    fifth commit, pinned since the sixth); B's exchange then makes it the one source vouching
                    for absence; the kernel's down notify for B, through the real handler (peer_update), writes
                    the mirror itself: B's sid is cannot-determine by B's last word (not rule 4: a host the
                    bus cannot vouch for makes no positive determination) and a sid nothing names is
                    cannot-determine, no host vouches for absence, where a gate on heard alone answers rule
                    5. The up notify alone changes nothing (B's roster is the one from before the drop); B's
                    exchange arriving with the link up is the event: rule 4 and rule 5 answer again. Then B
                    down beside host A heard, a host the kernel never notified (no link state): A is
                    reachable, so B's sid stays protected and A's own sids would be rule 4's, but A does not
                    vouch for absence, so a sid nothing names is cannot-determine, the reason naming A with
                    no link state and B with its link down (until the fifth commit this was rule 5's, heard
                    alone making A vouch);
      the alias road  a far bus filed under the hostname it DECLARES before this bus's own dial has folded
                    it under the alias the kernel dials (the road the fourth commit disclosed, closed by the
                    ruling). After a fourth restart the kernel notifies the alias up and the far bus dials us
                    through the real handler (peer_exchange_handle), declaring its hostname and busId and
                    naming its sid: the row is filed under the declared name, which has no link state, so
                    the sid it names is rule 4's and a sid nothing names is cannot-determine, the reason
                    naming the declared row with no link state beside the carried rows (a gate on
                    `reachable` answers rule 5 here: the false settle). The alias's down notify changes
                    neither verdict (the row has no link state of its own to withdraw). The fold, the alias
                    notified up and this bus's own exchange landing under it with the busId
                    (peer_exchange_apply), files the row under the alias: rule 5 and rule 4. The alias's down
                    notify then holds both sids at cannot-determine (link down); the up notify alone changes
                    nothing; the far bus's next dial, canonicalized under the alias with the link up, is the
                    event: rule 5 and rule 4 again;
      the hub's word  a hub's gossip about a host this bus also holds directly is never discarded (round 3 of
                    fork PR #897, the reviewer's ruling). After a fifth restart host B is heard with its link up
                    and a hub, notified up and heard, gossips B's roster: the gossip folds into B's row, which
                    speaks (rule 4 for B's sid, rule 5 for a sid nothing names). The kernel's down notify for B,
                    then the hub's next exchange naming a session started on B since: that sid is named by the
                    hub's row, via:<hub>/<B>, beside B's held-down row, so it is rule 4's while the hub vouches
                    (at round 2's head the gossip was folded because B had a dialable PEERS row, the sid was in no
                    row, and the hub, vouching for absence, let rule 5 presume it closed: the false settle, a
                    regression from round 1's head, which named every gossiped sid). The hub's down notify holds
                    both sids at cannot-determine (the via row follows the hub's link); the hub heard again with
                    its link up restores rule 4; B's exchange with its link up is the event that ends the via
                    row: dropped by the carry, B speaks (rule 4 by B's own row). Then the same road with B's row
                    CARRIED: a sixth restart, the kernel seeding B's link up, the hub heard before B naming a
                    session started on B across the restart: rule 4 by the hub's row while B's carried word holds
                    its own sids; B's exchange drops the via row, and the hub's next exchange folds again. Then
                    B's bus RESTARTS under a new bus id (a bus id is minted per process), in the ordering in which
                    this bus hears the restarted bus before the hub does: B's exchange carries the new id while the
                    hub's last gossip stamps the old, so by the ids the row is another bus and the hub's word stands
                    as a via row (rule 4 for every sid by either row); the hub's exchange with the restarted bus
                    stamps the new id and folds, and the via row of the hub's earlier word, stamped with the old id,
                    is dropped because the hub's current word about B folded (a carry keyed on the ids alone leaves
                    it for the file's life); a session then ending on B is rule 5's, not cannot-determine by that
                    stale row. Last the NAME COLLISION the reviewer's verifier found at the seventh commit: B heard
                    with its link up, and the hub, up and heard, names a session on ANOTHER machine it calls by B's
                    name, stamping that machine's bus id: both ids known and different, B's row does not speak for
                    it, the hub's word stands as a via row beside B's row, and the session is rule 4's (a name match
                    whatever the ids folded it into B's row, it was in no row, and B and the hub, both vouching for
                    absence, let rule 5 presume it closed for as long as B was heard and up);
      the gate alone  the carry's drop of a carried via row once the direct host speaks again, reached with
                    the hub NOT heard (round 3 of fork PR #897, the reviewer's verifier: every earlier pin of that
                    drop had the hub heard in the same process, so its gossip folded and the folded-key drop removed
                    the row first, and a carry keyed on the folded key alone passed every pin). B held down while the
                    hub names a session started on B since; a seventh restart; the kernel seeds both links up; B is
                    heard with its link up BEFORE the hub: the via row is dropped at that write by the gate, and the
                    session, ended on B across the restart, is rule 5's while B vouches (a carry keyed on the folded
                    key alone carries the hub's older word heard=false until the hub's next exchange, for the file's
                    life if the hub never returns, and the sid is cannot-determine by that row); a further exchange
                    of B's, then the hub heard at last, its word folding: no via row;
      the hub's two names  a via key carries the hub's name and the hub's name for the far host, and either
                    changes with no restart on either side (the reviewer's verifier, by execution through the real
                    handler and the real fold). An eighth restart; the hub dials us FIRST under the hostname it
                    declares (peer_exchange_handle files it there, no dialable row carrying its busId yet),
                    gossiping B, carried here, and a spoke nobody holds directly under the name the spoke declared
                    to the hub: every gossiped sid rule 4's by the declared rows, which have no link state, so a sid
                    nothing names is cannot-determine. Our own dial lands under the alias the kernel dials
                    (peer_exchange_apply, the busId fold): the hub's word is written under via:<alias>/<far>, and its
                    rows under the declared name, its own and both via rows, are dropped together, the hub's bus
                    heard under another name; a session the hub named under the declared name and no longer names
                    is rule 5's (at the eighth commit the via row under the declared name was carried by key,
                    heard=false, and that sid cannot-determine by it for the file's life). Then the hub's own fold
                    of the spoke under the alias IT dials changes the `via` label it stamps with the same viaBus: its
                    word moves to via:<hub>/<alias>, the row under the old name is dropped by the pair (the hub's
                    current word names that bus under another name), and a spoke session that ended across the
                    rename is rule 5's;
      two hubs, and a carried hub's bus id  the two identity drops with the fixture every real bus presents, a bus
                    id on the hub's row (BUS_ID; the reviewer's verifier: every carried-hub fixture until this phase had
                    none, so a carry reading a carried row's bus id alone as the hub heard under another name, and one
                    dropping a carried via row on ANY hub's current word about the far bus, passed every pin). The hub
                    names a session started on the spoke since; a second hub, peered with the spoke too and its roster
                    of it older, names the spoke's other session alone: rule 4 for both by the hubs' rows. A ninth
                    restart; the kernel seeds every link up; B is heard with its link up BEFORE either hub: B vouches
                    for absence, the hub's row is carried with its bus id and its word about the spoke with it, so both
                    spoke sessions are cannot-determine, named by the carried via rows (the first carry drops them at
                    the restarted bus's first write, and rule 5 presumes two live sessions closed on B's word); the
                    second hub heard again, naming the one it knows: the first hub's carried word stands, the pair the
                    carry drops by being (hub, bus id), so the session it alone names stays cannot-determine (the second
                    carry drops it, and rule 5 presumes that session closed on the word of a hub that never heard of
                    it); the hub heard at last, naming the one that remains: the session that ended across the restart
                    is rule 5's by the hub's own current word, the event;
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
(tests_dir, bin_dir, remote, remote2, dead, host_a, host_b, carried, other, alias, declared, far_sid, hub, gossiped, later,
 collided, ended, decl_named, spoke_kept, spoke_gone, hub_declared, spoke, spoke_declared, hub2, spoke_new) = sys.argv[1:26]
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
def exchange(bus, host, sids, bus_id=""):          # one exchange landing: what peer_exchange_handle/apply record, then write
    bus.PEER_STATE[host] = {"presence": [{"id": s, "name": "api"} for s in sids], "epoch": 1, "holds": [],
                            "seenAt": int(time.time())}
    if bus_id:
        bus.PEER_STATE[host]["busId"] = bus_id
    bus._write_remote_sids()
exchange(pm2, host_a, [carried])                   # host A's exchange names its sid in the running bus
out["peerHeard"] = peer_phase()
def notify(bus, host, up):                         # the kernel's /peer notify, through the real handler, which writes the mirror itself
    return list(bus.peer_update({"host": host, "port": 50002, "up": up}))
def restarted(name, previous):                     # a further bus process over the same root: a fresh module object, memory empty,
    bus = load_source(name, os.path.join(bin_dir, "romp-postal-service"))   # PEERS empty (no notify has landed yet)
    bus._peer_threads_reconcile = lambda host: None   # the notify's dialer bookkeeping is not under test (an up notify would dial a loopback port nothing listens on)
    return bus, {"heartbeats": len(bus.HEARTBEATS), "peers": len(bus.PEER_STATE), "links": len(bus.PEERS), "freshObject": bus is not previous}
pm3, out["restartMemory2"] = restarted("romp_postal_oneroot_restarted_twice", pm2)
notify(pm3, host_b, True)                          # the kernel notifies B's tunnel up before the bus dials it (as in the real bus):
exchange(pm3, host_b, [other])                     # B heard FIRST with its link known up, the new process's first write, nothing from A yet
out["otherHeardFirst"] = peer_phase()
notify(pm3, host_a, True)                          # A's tunnel up, then A's exchange arrives in the new process, its roster unchanged
exchange(pm3, host_a, [carried])
out["carriedHeard"] = peer_phase()
exchange(pm3, host_a, [])                          # A's next exchange no longer names the sid: it ended there
out["carriedHostNamesNobody"] = peer_phase()
def link_phase(extra=None):                        # the rows with their six flags, and the verdicts (the link held down phase and the alias road)
    rows = None
    if bus_file.exists():
        text = bus_file.read_text()
        try:
            rows = {k: [r["heard"], r["expired"], r["linkDown"], r.get("linkUp"), r["reachable"], r.get("vouchesAbsence"), r["sids"]]
                    for k, r in json.loads(text)["hosts"].items()}   # .get: a writer missing a flag fails a pin by None
        except (ValueError, KeyError, TypeError):
            rows = text
    got = {"hosts": rows, "other": verdict(other), "nobody": verdict(dead)}
    if extra is not None:
        got.update(extra)
    return got
pm4, out["restartMemory3"] = restarted("romp_postal_oneroot_restarted_thrice", pm3)
notify(pm4, host_b, True)                          # B's tunnel up before any exchange (the kernel's seed, or its re-notify):
out["seededUpUnheard"] = link_phase()              # B's carried row has linkUp and is not heard, so it vouches for nothing
exchange(pm4, host_b, [other])                     # then B heard: the one source vouching for absence (every other row carried)
out["linkHeard"] = link_phase()
out["linkDownNotify"] = notify(pm4, host_b, False)
out["linkDown"] = link_phase()                     # nothing wrote between the notify and this read
out["linkUpNotify"] = notify(pm4, host_b, True)
out["linkUpUnheard"] = link_phase()                # the link is back; B has not been heard since it dropped
exchange(pm4, host_b, [other])                     # B's exchange with the link up: the event
out["linkUpHeard"] = link_phase()
notify(pm4, host_b, False)
exchange(pm4, host_a, [])                          # A heard beside the down host; the kernel never notified A: no link state
out["heardBesideDown"] = link_phase()
# THE ALIAS ROAD: a fourth restart; the kernel notifies the ALIAS it dials, the far bus dials us declaring its hostname
pm5, out["restartMemory4"] = restarted("romp_postal_oneroot_restarted_fourth", pm4)
listing = os.path.join(os.environ["HOME"], "sessions.json")   # the dialed side's handler gossips the local listing in its
with open(listing, "w") as f:                                  # response: answered and empty, through the ROMP_SESSIONS_FILE seam
    f.write("[]")
os.environ["ROMP_SESSIONS_FILE"] = listing
def far_dials_us(bus, sids):                       # the dialed side of one exchange, through the real handler
    req = {"host": declared, "epoch": 1, "proto": bus.PEER_PROTO, "busId": "bus-x", "holds": [], "relays": [],
           "acks": [], "bounces": [], "wait": False, "presence": [{"id": s, "name": "api"} for s in sids]}
    resp, status = bus.peer_exchange_handle(req)
    return status
def alias_phase(bus):
    return link_phase({"far": verdict(far_sid), "filed": sorted(bus.PEER_STATE)})
out["aliasUpNotify"] = notify(pm5, alias, True)
out["aliasDialStatus"] = far_dials_us(pm5, [far_sid])
out["aliasDeclared"] = alias_phase(pm5)            # filed under the declared name: no link state
notify(pm5, alias, False)
out["aliasDownBeforeFold"] = alias_phase(pm5)      # the alias down does not reach the declared row
notify(pm5, alias, True)
pm5.peer_exchange_apply(alias, {}, {"presence": [{"id": far_sid, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-x"})
out["aliasFolded"] = alias_phase(pm5)              # this bus's own dial landed under the alias: the fold
notify(pm5, alias, False)
out["aliasDownAfterFold"] = alias_phase(pm5)
notify(pm5, alias, True)
out["aliasUpUnheard"] = alias_phase(pm5)
out["aliasRedialStatus"] = far_dials_us(pm5, [far_sid])   # the far bus dials again: canonicalized under the alias, the link up
out["aliasUpHeard"] = alias_phase(pm5)
# THE HUB'S WORD: a fifth restart; host B heard directly and held down, or carried, while a hub gossips a session started on B since
pm6, out["restartMemory5"] = restarted("romp_postal_oneroot_restarted_fifth", pm5)
def gossip(bus, sids, via_bus="bus-b", other=()):  # the hub's exchange landing: one hop of gossip about host B, stamped with B's bus id;
    bus.PEER_STATE[hub] = {"presence": [{"id": s, "name": "api", "via": host_b, "viaBus": via_bus} for s in sids]   # `other`: sids on ANOTHER
                           + [{"id": s, "name": "api", "via": host_b, "viaBus": "bus-other"} for s in other],       # machine the hub calls by B's name
                           "epoch": 1, "holds": [], "seenAt": int(time.time())}
    bus._write_remote_sids()
def hub_phase():
    return link_phase({"gossiped": verdict(gossiped), "later": verdict(later), "collided": verdict(collided)})
notify(pm6, host_b, True)
exchange(pm6, host_b, [other], bus_id="bus-b")     # B heard with its link up, naming its own sid
notify(pm6, hub, True)
gossip(pm6, [other])                               # the hub, up and heard, gossips B's roster as B reported it: folded, B speaks
out["hubBUp"] = hub_phase()
notify(pm6, host_b, False)                         # the kernel holds B's link down
gossip(pm6, [other, gossiped])                     # the hub's next exchange names a session started on B since B's last exchange
out["hubBDown"] = hub_phase()
notify(pm6, hub, False)                            # the hub's link down too: its word follows its link
out["hubBothDown"] = hub_phase()
notify(pm6, hub, True)
gossip(pm6, [other, gossiped])                     # the hub heard again with its link up
out["hubUpBDown"] = hub_phase()
notify(pm6, host_b, True)
exchange(pm6, host_b, [other, gossiped], bus_id="bus-b")   # B's exchange with the link up: the event, B speaks again
out["hubBBack"] = hub_phase()
# the same road with B's row CARRIED: a sixth restart, the kernel seeding B's link up, the hub heard before B
pm7, out["restartMemory6"] = restarted("romp_postal_oneroot_restarted_sixth", pm6)
notify(pm7, host_b, True)                          # the seed: PEERS up for a host the new process has not heard
notify(pm7, hub, True)
gossip(pm7, [other, gossiped, later])              # the hub's exchange lands first, naming a session started on B across the restart
out["hubBCarried"] = hub_phase()
exchange(pm7, host_b, [other, gossiped, later], bus_id="bus-b")   # B heard with the link up: the via row is dropped, B speaks
out["hubBCarriedThenHeard"] = hub_phase()
gossip(pm7, [other, gossiped, later])              # the hub's next exchange: folded, B still speaks
out["hubBHeardHubAgain"] = hub_phase()
# B'S BUS RESTARTS under a new id, heard here before the hub hears it: the hub's last gossip still stamps the old id
exchange(pm7, host_b, [other, gossiped, later], bus_id="bus-b2")
out["hubRestartHeardHereFirst"] = hub_phase()
gossip(pm7, [other, gossiped, later], via_bus="bus-b2")   # the hub's exchange with the restarted bus: its gossip stamps the new id
out["hubRestartHubCaughtUp"] = hub_phase()
exchange(pm7, host_b, [other, gossiped], bus_id="bus-b2")   # a session ends on B: both sources name the two that remain
gossip(pm7, [other, gossiped], via_bus="bus-b2")
out["hubRestartSidEnded"] = hub_phase()
# THE NAME COLLISION: the hub also names a session on ANOTHER machine it calls by B's name, stamping that machine's bus id
gossip(pm7, [other, gossiped], via_bus="bus-b2", other=[collided])
out["hubNameCollision"] = hub_phase()
# THE GATE ALONE: B held down while the hub names a session started on B since; a seventh restart; B heard with its link
# up BEFORE the hub is heard, so nothing of the hub's folds and only the carry's gate can drop the carried via row
def names_phase(bus):
    return link_phase({"ended": verdict(ended), "declNamed": verdict(decl_named), "spokeKept": verdict(spoke_kept),
                       "spokeGone": verdict(spoke_gone), "filed": sorted(bus.PEER_STATE)})
notify(pm7, host_b, False)
gossip(pm7, [other, gossiped, ended], via_bus="bus-b2")   # the hub's next exchange: a session started on B while B is held down
out["gateBDown"] = names_phase(pm7)
pm8, out["restartMemory7"] = restarted("romp_postal_oneroot_restarted_seventh", pm7)
notify(pm8, host_b, True)                          # the kernel's seeds: both links up, nothing heard yet
notify(pm8, hub, True)
out["gateCarried"] = names_phase(pm8)
exchange(pm8, host_b, [other, gossiped], bus_id="bus-b2")   # B heard with its link up, the hub NOT heard: `ended` ended across the restart
out["gateBHeardFirst"] = names_phase(pm8)
exchange(pm8, host_b, [other, gossiped], bus_id="bus-b2")   # a further exchange of B's, the hub still silent
out["gateBAgain"] = names_phase(pm8)
gossip(pm8, [other, gossiped], via_bus="bus-b2")            # the hub heard at last: its word folds
out["gateHubHeard"] = names_phase(pm8)
# THE HUB'S TWO NAMES: an eighth restart; the hub dials us FIRST under the hostname it declares, gossiping B (carried here)
# and a spoke nobody holds directly under the name the spoke declared to it; then our own dial lands under the alias the
# kernel dials (the fold); then the hub's own fold of the spoke changes the name it stamps
pm9, out["restartMemory8"] = restarted("romp_postal_oneroot_restarted_eighth", pm8)
notify(pm9, host_b, True)
notify(pm9, hub, True)
def hub_gossip(b_sids, spoke_name, spoke_sids):
    return ([{"id": s, "name": "api", "via": host_b, "viaBus": "bus-b2"} for s in b_sids]
            + [{"id": s, "name": "api", "via": spoke_name, "viaBus": "bus-spoke"} for s in spoke_sids])
def hub_dials_us(bus, b_sids, spoke_name, spoke_sids):     # the dialed side of one exchange, through the real handler
    req = {"host": hub_declared, "epoch": 1, "proto": bus.PEER_PROTO, "busId": "bus-hub", "holds": [], "relays": [],
           "acks": [], "bounces": [], "wait": False, "presence": hub_gossip(b_sids, spoke_name, spoke_sids)}
    resp, status = bus.peer_exchange_handle(req)
    return status
def our_dial_lands(bus, b_sids, spoke_name, spoke_sids):   # the dialer's half, through the real fold
    bus.peer_exchange_apply(hub, {}, {"epoch": 1, "holds": [], "busId": "bus-hub",
                                      "presence": hub_gossip(b_sids, spoke_name, spoke_sids)})
out["namesDialStatus"] = hub_dials_us(pm9, [other, gossiped, decl_named], spoke_declared, [spoke_kept, spoke_gone])
out["namesDeclared"] = names_phase(pm9)            # the hub under its declared name, no link state; B carried; the spoke under the hub's first name for it
our_dial_lands(pm9, [other, gossiped], spoke_declared, [spoke_kept, spoke_gone])   # the fold; decl_named ended on B
out["namesFolded"] = names_phase(pm9)
our_dial_lands(pm9, [other, gossiped], spoke, [spoke_kept])   # the hub's own fold of the spoke under the alias it dials; spoke_gone ended
out["namesSpokeRenamed"] = names_phase(pm9)
our_dial_lands(pm9, [other, gossiped], spoke, [spoke_kept])
out["namesSettled"] = names_phase(pm9)
# TWO HUBS, AND A CARRIED HUB'S BUS ID: the hub names a session started on the spoke since; a second hub, peered with the
# spoke too and its roster of it older, names the other spoke session alone; a ninth restart; the kernel seeds every link
# up; B is heard with its link up BEFORE either hub, then the second hub, then the hub
def hubs_phase(bus):
    ids = {}
    if bus_file.exists():
        try:
            ids = {k: r.get("busId") for k, r in json.loads(bus_file.read_text())["hosts"].items() if r.get("busId")}
        except (ValueError, KeyError, TypeError):
            ids = None
    return link_phase({"spokeKept": verdict(spoke_kept), "spokeNew": verdict(spoke_new), "filed": sorted(bus.PEER_STATE),
                       "busIds": ids})
def hub2_gossip(bus, spoke_sids):                  # the second hub's exchange landing through the real fold, its own bus id
    bus.peer_exchange_apply(hub2, {}, {"epoch": 1, "holds": [], "busId": "bus-hub2",
                                       "presence": [{"id": s, "name": "api", "via": spoke, "viaBus": "bus-spoke"} for s in spoke_sids]})
our_dial_lands(pm9, [other, gossiped], spoke, [spoke_kept, spoke_new])   # the hub's next exchange: a session started on the spoke since
notify(pm9, hub2, True)
hub2_gossip(pm9, [spoke_kept])                     # the second hub's roster of the spoke is older: it names the one it knows
out["twoHubs"] = hubs_phase(pm9)
pm10, out["restartMemory9"] = restarted("romp_postal_oneroot_restarted_ninth", pm9)
notify(pm10, host_b, True)                         # the kernel's seeds: every link up, nothing heard yet
notify(pm10, hub, True)
notify(pm10, hub2, True)
out["hubsCarried"] = hubs_phase(pm10)
exchange(pm10, host_b, [other, gossiped], bus_id="bus-b2")   # B heard with its link up, neither hub heard: B vouches for absence
out["hubsBHeardFirst"] = hubs_phase(pm10)
hub2_gossip(pm10, [spoke_kept])                    # the second hub heard again, naming the one it knows; the hub not heard
out["hubsSecondHeard"] = hubs_phase(pm10)
our_dial_lands(pm10, [other, gossiped], spoke, [spoke_kept])   # the hub heard at last: spoke_new ended across the restart
out["hubsFirstHeard"] = hubs_phase(pm10)
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
""", HERE, BIN, REMOTE, REMOTE2, DEAD, HOST, HOST2, CARRIED, OTHER, ALIAS, DECLARED, FARSID, HUB, GOSSIPED, LATER, COLLIDED,
                              ENDED, DECL_NAMED, SPOKE_KEPT, SPOKE_GONE, HUB_DECLARED, SPOKE, SPOKE_DECLARED, HUB2, SPOKE_NEW],
                             capture_output=True, text=True, env=full,
                             cwd=str(home), timeout=120)
        assert out.returncode == 0, "%s child failed: %s" % (shape, out.stderr[-2000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        got["root"] = str(root)
        return got

    HB = "heartbeat:"       # the bus keys a legacy heartbeat's row heartbeat:<sid> (postal_service.py REMOTE_SIDS_HEARTBEAT)

    @staticmethod
    def _v(phase, key):
        """A recorded verdict, (closed, rule, why), as the RULE_5 and RULE_4 constants and the LOST and
        NO_VOUCH helpers spell them (the reason of the two cannot-determine arms names the sources)."""
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
                                       "linkDown": False, "linkUp": False, "reachable": True, "vouchesAbsence": True,
                                       "name": "web"},
                                 "the row's fields as the writer spells them, the six flags among them (a legacy heartbeat "
                                 "has no link and vouches for absence by its TTL): the fixtures' _row restates every one, "
                                 "and the reader requires the six")

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
                self.assertEqual(got["restartMemory2"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the second restart is a fresh module object too, its memory and its link table empty")
                first = got["otherHeardFirst"]
                self.assertEqual(self._v(first, "carried"), LOST(HOST + " (not heard)"),
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

    def test_the_kernels_seed_of_a_carried_hosts_link_up_at_a_restart_settles_nothing_until_the_host_is_heard(self):
        """The primary restart road, with the verdicts (round 2 of fork PR #897, a verifier's finding at the fifth commit:
        a writer computing vouchesAbsence from the link alone, heard dropped, survived every pin of the five modules while
        reopening the first road of round 1 by execution). A restarted bus's kernel seeds or re-notifies a tunnel UP
        (_seed_peers_from_kernel, peer_update) before any exchange arrives, so a host carried from the previous file has
        PEERS up and no mark: linkUp True, heard False. Its roster is the previous process's last word, and the row must
        vouch for nothing: the sid it names is held by that word (cannot-determine, not heard), and a sid nothing names is
        cannot-determine too, no host vouching for absence; under the link-alone writer the carried row vouches and rule 5
        presumes a session started on that host since the previous file closed, on the restarted bus's first write. The
        verdict pins first, the document after; the phase after this one (linkHeard) is the event."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                seeded = got["seededUpUnheard"]
                self.assertEqual(self._v(seeded, "nobody"),
                                 NO_VOUCH(HOST + " (not heard)", HOST2 + " (not heard)",
                                          self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)"),
                                 "THE SEED: the kernel holds B's link up and the new process has heard nothing over it; every "
                                 "row is carried and none vouches for absence, so a sid nothing names is cannot-determine, the "
                                 "reason naming every source as not heard (a writer vouching for absence by the link alone "
                                 "answers rule 5 here: a session started on B since the previous file, presumed closed on the "
                                 "restarted bus's first write)")
                self.assertEqual(self._v(seeded, "other"), LOST(HOST2 + " (not heard)"),
                                 "B's carried word holds its sid: not heard, so not rule 4's either")
                self.assertEqual(seeded["hosts"][HOST2], L(False, False, False, True, False, False, [OTHER]),
                                 "carried, not heard, PEERS up and no mark: linkUp, and neither reachable nor vouching")
                self.assertEqual(seeded["hosts"][HOST], L(False, False, False, False, False, False, []),
                                 "the host the seed did not name: not heard, no link state")

    def test_a_host_the_kernel_holds_down_cannot_vouch_until_heard_with_the_link_up(self):
        """Round 2 of fork PR #897, the reviewer's ruling: the kernel's link state decides what a source vouches for. The
        verdict and its reason at every step, then the document, so a writer gating on heard alone reds at a verdict."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory3"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the third restart is a fresh module object, its memory and its link table empty")
                heard = got["linkHeard"]
                self.assertEqual(self._v(heard, "other"), RULE_4, "notified up, then heard: rule 4")
                self.assertEqual(self._v(heard, "nobody"), RULE_5, "one host with its link known up names nobody unknown: rule 5")
                self.assertEqual(heard["hosts"][HOST2], L(True, False, False, True, True, True, [OTHER]),
                                 "PEERS up and heard since: linkUp, reachable, vouching for absence")
                self.assertEqual(got["linkDownNotify"], [{"ok": True, "up": 0}, 200], "the handler took the down notify")
                down = got["linkDown"]
                down_host = LOST(HOST2 + " (link down)")
                # every row of the file at this point, sorted by key as the reason sorts them: the two peer hosts
                # carried from the second restart's process, then the two heartbeats carried since the first
                none_vouches = NO_VOUCH(HOST + " (not heard)", HOST2 + " (link down)",
                                        self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
                self.assertEqual(self._v(down, "other"), down_host,
                                 "the host that names it is heard but the kernel holds its link down: its last word "
                                 "stands and rule 4 does not fire (a host the bus cannot vouch for makes no positive "
                                 "determination), and the reason names the down host; a gate on heard alone answers "
                                 "rule 4 here")
                self.assertEqual(self._v(down, "nobody"), none_vouches,
                                 "the only heard host is down: nothing can vouch for absence, cannot-determine, the "
                                 "reason naming every source and why it cannot vouch; a gate on heard alone "
                                 "presumes a session started there since the drop closed, rule 5")
                self.assertEqual(down["hosts"][HOST2], L(True, False, True, False, False, False, [OTHER]),
                                 "marked link-down by the notify's own write, nothing else having written: unreachable, "
                                 "roster kept (a writer waiting for the next tick leaves the row reachable here)")
                unheard = got["linkUpUnheard"]
                self.assertEqual(got["linkUpNotify"], [{"ok": True, "up": 1}, 200])
                self.assertEqual((self._v(unheard, "other"), self._v(unheard, "nobody")), (down_host, none_vouches),
                                 "the up notify alone is not the event: the roster is the one heard before the link "
                                 "dropped and says nothing about a session started there since")
                self.assertEqual(unheard["hosts"][HOST2], L(True, False, True, False, False, False, [OTHER]),
                                 "PEERS says up and the mark stands: neither linkUp nor vouching (a writer reading PEERS "
                                 "alone for linkUp says True here)")
                up = got["linkUpHeard"]
                self.assertEqual((self._v(up, "other"), self._v(up, "nobody")), (RULE_4, RULE_5),
                                 "its exchange arriving with the link up is the event: reachable, rule 4 and rule 5 again")
                self.assertEqual(up["hosts"][HOST2], L(True, False, False, True, True, True, [OTHER]))

    def test_a_heard_host_with_no_link_state_beside_a_down_host_vouches_for_presence_alone(self):
        """The fifth commit's flip of the link phase's last step (the reviewer's ruling: a source vouches for absence only
        when its link is known up). Host B down, host A heard beside it, a host the kernel never notified: A is reachable,
        so its own sids would be rule 4's and B's sid stays held by B's last word, but A does not vouch for absence, so a
        sid nothing names is cannot-determine, the reason naming A with no link state and B with its link down. Until
        this commit heard alone made A vouch and the sid was rule 5's. The verdict pins first, the document after."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                beside = got["heardBesideDown"]
                self.assertEqual(self._v(beside, "nobody"),
                                 NO_VOUCH(HOST + " (no link state)", HOST2 + " (link down)",
                                          self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)"),
                                 "a host the kernel never notified is heard beside the down one: reachable, so its own sids "
                                 "would be rule 4's, but with no link state it does not vouch for absence, and a sid nothing "
                                 "names is cannot-determine, the reason naming it with no link state and the down host "
                                 "(until the fifth commit heard alone made it vouch and this was rule 5's; a reader gating "
                                 "rule 5 on `reachable` answers rule 5 here)")
                self.assertEqual(self._v(beside, "other"), LOST(HOST2 + " (link down)"),
                                 "the down host's last word still protects its sid")
                self.assertEqual((beside["hosts"][HOST], beside["hosts"][HOST2]),
                                 (L(True, False, False, False, True, False, []), L(True, False, True, False, False, False, [OTHER])),
                                 "no link state for the never-notified host: reachable, not vouching; the down host's row "
                                 "as the notify left it")

    def test_a_far_bus_under_its_declared_name_vouches_for_presence_alone_until_the_fold(self):
        """The alias road (the fourth commit's disclosed residual, closed by the reviewer's ruling: a source vouches for
        a sid's absence only when its link is known up). The kernel notifies the ALIAS it dials; the far bus dials us
        declaring its hostname and busId, and the handler files it under the declared name, which has no link state,
        until this bus's own dial folds it under the alias (_canon_peer_name). The verdict and its reason at every
        step, then the document, so a reader gating rule 5 on `reachable` reds at the first verdict pin: the false
        settle, rule 5 True for a sid nothing names with the declared row as the only reachable one."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        # every row of the file on this road, sorted by key as the reason sorts them: the peer hosts carried from the
        # third restart's process, the far bus's row under the name it is filed under, then the two carried heartbeats
        carried = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        declared_only = NO_VOUCH(HOST + " (not heard)", DECLARED + " (no link state)", HOST2 + " (not heard)", *carried)
        alias_down = NO_VOUCH(HOST + " (not heard)", ALIAS + " (link down)", HOST2 + " (not heard)", *carried)
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory4"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the fourth restart is a fresh module object, its memory and its link table empty")
                self.assertEqual((got["aliasUpNotify"], got["aliasDialStatus"]), ([{"ok": True, "up": 1}, 200], 200),
                                 "the kernel's up notify for the alias landed, and the far bus's dial was answered")
                first = got["aliasDeclared"]
                self.assertEqual(first["filed"], [DECLARED], "no row under a dialable name carries the busId: filed as declared")
                self.assertEqual(self._v(first, "far"), RULE_4,
                                 "the far bus is heard and not held down: the sid it names is live on another host")
                self.assertEqual(self._v(first, "nobody"), declared_only,
                                 "THE RULE: the declared row has no link state (the kernel dials the alias, not this name), "
                                 "so it vouches for presence alone and a sid nothing names is cannot-determine, the reason "
                                 "naming it with no link state beside the carried rows (a reader gating rule 5 on `reachable` "
                                 "answers rule 5 here, the false settle the fourth commit disclosed)")
                self.assertEqual(first["hosts"][DECLARED], L(True, False, False, False, True, False, [FARSID]),
                                 "heard, not held down, no link state: reachable and not vouching")
                self.assertNotIn(ALIAS, first["hosts"], "the alias has a PEERS row and no exchange: not a source")
                before = got["aliasDownBeforeFold"]
                self.assertEqual((self._v(before, "far"), self._v(before, "nobody")), (RULE_4, declared_only),
                                 "the alias's down notify does not reach a row filed under another name, and has nothing to "
                                 "withdraw from it: the sid it names stays protected, a sid it does not name stays unsettled")
                self.assertEqual(before["hosts"][DECLARED], L(True, False, False, False, True, False, [FARSID]))
                folded = got["aliasFolded"]
                self.assertEqual(folded["filed"], [ALIAS], "the fold: this bus's own dial landed under the alias with the "
                                 "busId, and the declared row is the same bus, dropped")
                self.assertEqual((self._v(folded, "far"), self._v(folded, "nobody")), (RULE_4, RULE_5),
                                 "under the alias the kernel holds up, heard on the fold's own exchange: it vouches for "
                                 "absence, and a sid nothing names is rule 5's")
                self.assertEqual(folded["hosts"][ALIAS], L(True, False, False, True, True, True, [FARSID]))
                self.assertNotIn(DECLARED, folded["hosts"], "one row per bus on the fold's own write")
                down = got["aliasDownAfterFold"]
                self.assertEqual((self._v(down, "far"), self._v(down, "nobody")), (LOST(ALIAS + " (link down)"), alias_down),
                                 "folded under the alias, the row follows the alias's link: down, so its sid is held by its "
                                 "last word and a sid nothing names is cannot-determine, the reason naming the down alias")
                self.assertEqual(down["hosts"][ALIAS], L(True, False, True, False, False, False, [FARSID]))
                unheard = got["aliasUpUnheard"]
                self.assertEqual((self._v(unheard, "far"), self._v(unheard, "nobody")), (LOST(ALIAS + " (link down)"), alias_down),
                                 "the up notify alone is not the event")
                self.assertEqual(got["aliasRedialStatus"], 200)
                again = got["aliasUpHeard"]
                self.assertEqual(again["filed"], [ALIAS], "the far bus's next dial is canonicalized under the alias")
                self.assertEqual((self._v(again, "far"), self._v(again, "nobody")), (RULE_4, RULE_5),
                                 "heard with the link up: the event; rule 4 and rule 5 again")
                self.assertEqual(again["hosts"][ALIAS], L(True, False, False, True, True, True, [FARSID]))

    def test_a_hubs_word_about_a_directly_held_host_stands_while_that_host_is_down_or_carried(self):
        """Round 3 of fork PR #897, the reviewer's ruling: never discard a heard source's word. Host B is heard directly;
        the kernel holds its link down; the hub, up and heard, names a session started on B since. That sid is named by
        the hub's row (via:<hub>/<B>) beside B's held-down row: rule 4 while the hub vouches, never rule 5 (a writer
        folding the gossip whatever B's row's state, the display fold, leaves the sid in no row, and the hub vouching for
        absence lets rule 5 presume it closed: the false settle round 2 found, a regression from round 1's head). The
        same with B's row carried after a restart; B's exchange with its link up ends the via row. The verdict and its
        reason at every step, then the document, so a writer adding the gossip to B's own row (crediting a host with a
        word it did not give) reds at the verdict, cannot-determine by B's down row instead of rule 4."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        # every row of the file on this road, sorted by key as the reason sorts them: the carried peer hosts, the alias
        # carried from the fourth restart's process, the hub, host B, the two carried heartbeats, the hub's word about B
        carried = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory5"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the fifth restart is a fresh module object, its memory and its link table empty")
                up = got["hubBUp"]
                self.assertEqual((self._v(up, "other"), self._v(up, "gossiped"), self._v(up, "nobody")), (RULE_4, RULE_5, RULE_5),
                                 "B heard with its link up and the hub gossiping B's roster as B reported it: the gossip folds "
                                 "and B speaks; a session not yet started is rule 5's")
                self.assertNotIn(VIA_B, up["hosts"], "B heard and not held down: no via row, its own row speaks")
                down = got["hubBDown"]
                self.assertEqual(self._v(down, "gossiped"), RULE_4,
                                 "THE RULE: the kernel holds B's link down, and the hub, up and heard, names a session started on "
                                 "B since B's last exchange: the hub's row names it, so it is live on another host, rule 4 (a "
                                 "writer folding the gossip because B has a dialable PEERS row, whatever B's row's state, leaves "
                                 "it in no row, and with the hub vouching for absence rule 5 presumes it closed: the false settle "
                                 "round 2 found; at round 1's head the gossip was named)")
                self.assertEqual(self._v(down, "other"), RULE_4, "B's own sid: named by the hub's row too, so rule 4 while B is down")
                self.assertEqual(self._v(down, "nobody"), RULE_5, "the hub vouches for absence: a sid nothing names is rule 5's")
                self.assertEqual(down["hosts"][HOST2], L(True, False, True, False, False, False, [OTHER]),
                                 "B's row as the notify left it: held down, its last roster kept")
                self.assertEqual(down["hosts"][VIA_B], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED])),
                                 "the hub's word about B, under the colon key beside B's own row, following the hub's link: heard, "
                                 "known up, vouching (a writer adding the gossip to B's row writes no such row)")
                both = got["hubBothDown"]
                self.assertEqual(self._v(both, "gossiped"), LOST(VIA_B + " (link down)"),
                                 "the hub down too: its word follows its link, so the sid is held by that word, cannot-determine")
                self.assertEqual(self._v(both, "other"), LOST(HOST2 + " (link down)", VIA_B + " (link down)"))
                self.assertEqual(self._v(both, "nobody"),
                                 NO_VOUCH(HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (link down)", HOST2 + " (link down)",
                                          *carried, VIA_B + " (link down)"),
                                 "no source vouches: the reason names every row, the hub's word about B among them")
                self.assertEqual(both["hosts"][VIA_B], L(True, False, True, False, False, False, sorted([OTHER, GOSSIPED])))
                again = got["hubUpBDown"]
                self.assertEqual((self._v(again, "gossiped"), self._v(again, "nobody")), (RULE_4, RULE_5),
                                 "the hub heard again with its link up: its word vouches again")
                back = got["hubBBack"]
                self.assertEqual((self._v(back, "gossiped"), self._v(back, "other"), self._v(back, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "B's exchange arriving with its link up is the event: B speaks for itself, rule 4 by its own row")
                self.assertNotIn(VIA_B, back["hosts"],
                                 "the via row is DROPPED by the carry once B speaks again (a writer that carries it leaves the "
                                 "hub's older word about B naming a sid for the file's life)")
                self.assertEqual(back["hosts"][HOST2], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED])))
                # the same road with B's row carried
                self.assertEqual(got["restartMemory6"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True})
                car = got["hubBCarried"]
                self.assertEqual(self._v(car, "later"), RULE_4,
                                 "B carried and the kernel's seed holding its link up; the hub heard first names a session "
                                 "started on B across the restart: rule 4 by the hub's row (a writer folding on the seeded "
                                 "PEERS row leaves it in no row while the hub vouches: rule 5, the regression)")
                self.assertEqual((self._v(car, "gossiped"), self._v(car, "other"), self._v(car, "nobody")), (RULE_4, RULE_4, RULE_5))
                self.assertEqual(car["hosts"][HOST2], L(False, False, False, True, False, False, sorted([OTHER, GOSSIPED])),
                                 "B's carried row: not heard, the seed's linkUp, vouching for nothing, its last roster kept (a "
                                 "writer keying the via row by B's name overwrites it here)")
                self.assertEqual(car["hosts"][VIA_B], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED, LATER])))
                heard = got["hubBCarriedThenHeard"]
                self.assertEqual((self._v(heard, "later"), self._v(heard, "nobody")), (RULE_4, RULE_5),
                                 "B heard with its link up: rule 4 by B's own row")
                self.assertNotIn(VIA_B, heard["hosts"], "dropped by the carry: B speaks")
                self.assertEqual(heard["hosts"][HOST2], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED, LATER])))
                folded = got["hubBHeardHubAgain"]
                self.assertNotIn(VIA_B, folded["hosts"], "the hub's next exchange folds: B still speaks")
                self.assertEqual((self._v(folded, "later"), self._v(folded, "nobody")), (RULE_4, RULE_5))

    def test_a_name_match_yields_to_a_known_different_bus_id(self):
        """Round 3 of fork PR #897, the reviewer's verifier's finding at the seventh commit, by execution: host B is heard
        with its link up under one bus id, and the hub, up and heard, names a session on ANOTHER machine it calls by
        B's name, stamping that machine's bus id. A writer matching by name whatever the ids folds the hub's word into
        B's row: the session is in no row, and B and the hub, both vouching for absence, let rule 5 presume it closed
        for as long as B is heard and up (no exchange of B's ever names it). The rule: both ids known and different, B's
        row does not speak, the hub's word stands as a via row beside it, and the session is rule 4's while the hub
        vouches. The verdict is pinned first, so the writer that folds by name reds on the false settle itself."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                col = got["hubNameCollision"]
                self.assertEqual(self._v(col, "collided"), RULE_4,
                                 "THE RULE: B heard and up under its bus id, and the hub naming a session on another machine it calls "
                                 "by B's name under that machine's bus id: both ids known and different, so B's row does not speak "
                                 "for it; the hub's row names it, rule 4 while the hub vouches (a writer matching by name whatever the "
                                 "ids leaves it in no row, and with B and the hub both vouching for absence rule 5 presumes it closed "
                                 "for as long as B is heard and up: the reviewer's verifier's finding)")
                self.assertEqual((self._v(col, "gossiped"), self._v(col, "other"), self._v(col, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "B's own sids by B's row; a sid nothing names is rule 5's")
                self.assertEqual(col["hosts"].get(VIA_B), L(True, False, False, True, True, True, [COLLIDED]),
                                 "the hub's word about the other machine, under the colon key beside B's row, naming the session "
                                 "there alone (B's own sids folded into B's row by the shared id)")
                self.assertEqual(col["hosts"][HOST2], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED])),
                                 "B's row as B reported it: the gossip about the other machine is not added to it")

    def test_a_far_bus_restarted_under_a_hub_leaves_no_via_row_behind_once_the_hub_hears_it(self):
        """The companion the rule above needs (a bus id is minted per process, so a restart parts the two ids): B's bus
        restarted under a new id and heard here before the hub heard it, so the hub's last gossip stamps the old id
        against B's new one and by the ids the row is another bus; the hub's word stands as a via row for that interval
        (every sid rule 4's by one row or the other, the conservative side). Once the hub's exchange with the restarted
        bus stamps the new id and folds, the via row of its earlier word, stamped with the old id, is dropped because
        the hub's current word about B folded at that write (a carry keyed on the ids alone leaves it heard=false for
        the file's life, the old id never returning, and a session that then ends on B is cannot-determine by that
        stale row where rule 5 is due: shown by execution on a scratch copy with the clause alone)."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                first = got["hubRestartHeardHereFirst"]
                self.assertEqual((self._v(first, "later"), self._v(first, "other"), self._v(first, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "B's exchange carries the new id and the hub's last gossip stamps the old: every sid is named by "
                                 "a reachable row, and a sid nothing names is rule 5's")
                self.assertEqual(first["hosts"].get(VIA_B), L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED, LATER])),
                                 "by the ids another bus: the hub's word stands as a via row beside B's row (a writer matching by "
                                 "name whatever the ids folds it, and there is no via row)")
                self.assertEqual(first["hosts"][HOST2], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED, LATER])))
                caught = got["hubRestartHubCaughtUp"]
                self.assertNotIn(VIA_B, caught["hosts"],
                                 "the hub's gossip stamps the new id and folds, and the via row of its earlier word, stamped with the "
                                 "old id, is DROPPED (a carry keyed on the ids alone leaves it heard=false for the file's life: the "
                                 "old id never returns)")
                self.assertEqual((self._v(caught, "later"), self._v(caught, "nobody")), (RULE_4, RULE_5))
                ended = got["hubRestartSidEnded"]
                self.assertEqual(self._v(ended, "later"), RULE_5,
                                 "a session that ended on B after the restart: in no row, and B and the hub both vouch for absence, "
                                 "rule 5 (a lingering via row of the hub's stale word holds it at cannot-determine, named by an "
                                 "unreachable source)")
                self.assertEqual((self._v(ended, "gossiped"), self._v(ended, "nobody")), (RULE_4, RULE_5))

    def test_the_direct_host_heard_again_before_the_hub_drops_the_carried_via_row(self):
        """The ruled event on its own (round 3 of fork PR #897, the reviewer's verifier): every earlier pin of the drop
        had the hub heard in the same process, so its gossip folded and the folded-key drop removed the row before the
        carry's gate was reached; a carry keyed on the folded key alone passed both changed modules. Here B is held down
        while the hub names a session started on B since, this bus restarts, and B is heard with its link up BEFORE the
        hub is heard: the via row is dropped by the gate alone, and the session, ended on B across the restart, is rule
        5's while B vouches (a carry keyed on the folded key alone carries the hub's older word heard=false until the
        hub's next exchange, for the file's life if the hub never returns, and the sid is cannot-determine by that row:
        the linger the ruling's drop clause forbids). The verdict is pinned first, so that writer reds on the linger."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        carried = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                down = got["gateBDown"]
                self.assertEqual((self._v(down, "ended"), self._v(down, "other"), self._v(down, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "B held down and the hub, up and heard, naming a session started on B since: rule 4 by the hub's row")
                self.assertEqual(down["hosts"][VIA_B], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED, ENDED])))
                self.assertEqual(got["restartMemory7"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the seventh restart is a fresh module object, its memory and its link table empty")
                car = got["gateCarried"]
                self.assertEqual(self._v(car, "ended"), LOST(VIA_B + " (not heard)"),
                                 "carried: held by the hub's last word, which nothing has superseded")
                self.assertEqual(self._v(car, "nobody"),
                                 NO_VOUCH(HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (not heard)", HOST2 + " (not heard)",
                                          *carried, VIA_B + " (not heard)"),
                                 "the first write after the restart: every row carried, the seeds' linkUp vouching for nothing")
                self.assertEqual(car["hosts"][VIA_B], L(False, False, False, True, False, False, sorted([OTHER, GOSSIPED, ENDED])))
                self.assertEqual(car["hosts"][HOST2], L(False, False, False, True, False, False, sorted([OTHER, GOSSIPED])))
                first = got["gateBHeardFirst"]
                self.assertEqual(self._v(first, "ended"), RULE_5,
                                 "THE RULE: B heard with its link up and the hub NOT heard in this process, so nothing of the hub's "
                                 "folded at this write and only the carry's gate can drop the carried via row: it is dropped, and the "
                                 "session that ended on B across the restart is in no row while B vouches, rule 5 (a carry keyed on "
                                 "the folded key alone carries the hub's older word heard=false until the hub's next exchange, for "
                                 "the file's life if the hub never returns, and the sid is cannot-determine by that row)")
                self.assertNotIn(VIA_B, first["hosts"], "dropped by the gate: B speaks for itself again")
                self.assertEqual(first["hosts"][HOST2], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED])))
                self.assertEqual(first["hosts"][HUB], L(False, False, False, True, False, False, []),
                                 "the hub carried, not heard: nothing of its word folded at this write")
                self.assertEqual((self._v(first, "other"), self._v(first, "nobody")), (RULE_4, RULE_5))
                again = got["gateBAgain"]
                self.assertNotIn(VIA_B, again["hosts"], "a further exchange of B's: nothing brings the row back")
                self.assertEqual(self._v(again, "ended"), RULE_5)
                heard = got["gateHubHeard"]
                self.assertNotIn(VIA_B, heard["hosts"], "the hub heard at last: its word folds, no via row")
                self.assertEqual((self._v(heard, "ended"), self._v(heard, "other"), self._v(heard, "nobody")), (RULE_5, RULE_4, RULE_5))

    def test_a_hubs_word_follows_the_hub_to_the_alias_and_its_earlier_word_under_the_declared_name_is_dropped(self):
        """The first name axis of a via key (round 3 of fork PR #897, the reviewer's verifier, by execution through the
        real inbound handler and the real fold): the hub dials us first under the hostname it declares and is filed
        there; our own dial lands under the alias the kernel dials and the busId fold drops the declared row. The hub's
        word is written under via:<alias>/<far>, and its earlier word under via:<declared>/<far>, carried by key alone,
        named a session that ended between the two heard=false for the file's life, cannot-determine where rule 5 was
        due (at the eighth commit). The rule: the hub's bus heard under another name drops its rows under the old name
        together, its own and its via rows. The verdict is pinned first, so a carry by key alone reds on the linger."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        carried = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory8"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True})
                self.assertEqual(got["namesDialStatus"], 200, "the hub's inbound dial landed")
                decl = got["namesDeclared"]
                self.assertEqual(decl["filed"], [HUB_DECLARED], "the hub's own dial landed first: filed under the hostname it declares")
                self.assertEqual((self._v(decl, "declNamed"), self._v(decl, "other"), self._v(decl, "spokeKept"), self._v(decl, "spokeGone")),
                                 (RULE_4, RULE_4, RULE_4, RULE_4), "every gossiped sid is named by the hub's rows under its declared name")
                self.assertEqual(self._v(decl, "nobody"),
                                 NO_VOUCH(HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (not heard)",
                                          HUB_DECLARED + " (no link state)", HOST2 + " (not heard)", *carried,
                                          VIA_SPOKE_UNDER_DECLARED + " (no link state)",
                                          VIA_B_DECLARED + " (no link state)"),
                                 "no source vouches: the hub under its declared name has no link state, and its via rows follow it")
                self.assertEqual(decl["hosts"][VIA_B_DECLARED], L(True, False, False, False, True, False, sorted([OTHER, GOSSIPED, DECL_NAMED])),
                                 "the hub's word about B under the hub's declared name: reachable, vouching for absence by no link")
                fold = got["namesFolded"]
                self.assertEqual(fold["filed"], [HUB], "the fold: this bus's own dial landed under the alias, the declared row left PEER_STATE")
                self.assertEqual(self._v(fold, "declNamed"), RULE_5,
                                 "THE RULE: the hub's bus is heard under the alias, so its row under the declared name is dropped (the "
                                 "busId fold) and its word under via:<declared>/<B> with it, by the same test; its current word stands "
                                 "under via:<alias>/<B> and no longer names the session that ended on B, so that sid is in no row while "
                                 "the hub vouches, rule 5 (a carry keyed on the via key alone carries the declared name's word "
                                 "heard=false for the file's life, and the sid is cannot-determine by it: the eighth commit's answer)")
                self.assertNotIn(VIA_B_DECLARED, fold["hosts"], "the hub's earlier word under its declared name is gone")
                self.assertNotIn(HUB_DECLARED, fold["hosts"], "and the hub's own row under that name with it")
                self.assertEqual(fold["hosts"][VIA_B], L(True, False, False, True, True, True, sorted([OTHER, GOSSIPED])),
                                 "the hub's current word about B under the alias, following the alias's link: known up, vouching")
                self.assertEqual((self._v(fold, "other"), self._v(fold, "spokeKept"), self._v(fold, "spokeGone"), self._v(fold, "nobody")),
                                 (RULE_4, RULE_4, RULE_4, RULE_5))

    def test_a_hubs_word_follows_its_own_name_for_the_far_host_and_its_earlier_word_under_the_old_name_is_dropped(self):
        """The second name axis of a via key (round 3 of fork PR #897, the reviewer's verifier, by execution): the hub's
        own fold of the spoke under the alias it dials changes the `via` label it stamps while the viaBus stays. The
        hub's word is written under via:<hub>/<alias>, and its earlier word under via:<hub>/<declared>, carried by key
        alone, named a spoke session that ended across the rename heard=false for the file's life (the same at the sixth
        commit, whose via rows were keyed by the far name). The rule: a carried via row whose (hub, viaBus) pair the hub's
        current gossip names under another far name is dropped. The verdict is pinned first."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                fold = got["namesFolded"]
                self.assertEqual(fold["hosts"][VIA_SPOKE_DECLARED], L(True, False, False, True, True, True, sorted([SPOKE_KEPT, SPOKE_GONE])),
                                 "the hub's word about the spoke under the name the spoke declared to it, following the hub's link")
                ren = got["namesSpokeRenamed"]
                self.assertEqual(self._v(ren, "spokeGone"), RULE_5,
                                 "THE RULE: the hub now calls the spoke by the alias it dials, the same viaBus, and names the one session "
                                 "left there: its earlier word under the old name is dropped by the pair, and the spoke session that "
                                 "ended across the rename is in no row while the hub vouches, rule 5 (a carry keyed on the via key alone "
                                 "carries the old name's row heard=false for the file's life, and the sid is cannot-determine by it)")
                self.assertNotIn(VIA_SPOKE_DECLARED, ren["hosts"], "the hub's word under its old name for the spoke is gone")
                self.assertEqual(ren["hosts"][VIA_SPOKE], L(True, False, False, True, True, True, [SPOKE_KEPT]),
                                 "the hub's current word about the spoke under the alias it dials")
                self.assertEqual((self._v(ren, "spokeKept"), self._v(ren, "other"), self._v(ren, "nobody")), (RULE_4, RULE_4, RULE_5))
                settled = got["namesSettled"]
                self.assertNotIn(VIA_SPOKE_DECLARED, settled["hosts"], "and it stays gone at the hub's next exchange")
                self.assertEqual(self._v(settled, "spokeGone"), RULE_5)

    def test_a_carried_hubs_word_about_a_far_host_stands_while_its_bus_is_heard_under_no_other_name(self):
        """The identity drop's negative with the fixture every real bus presents, a bus id on the hub's row (round 3 of
        fork PR #897, the reviewer's verifier: every carried-hub fixture until this phase had none, so a carry reading a
        carried row's bus id ALONE as the hub heard under another name passed every pin, and by execution presumed two
        live spoke sessions closed on B's word). A ninth restart; the kernel seeds every link up; B is heard with its
        link up before either hub: the hub is carried, its bus id on its row, and its word about the spoke with it, so
        both spoke sessions are cannot-determine while B vouches for absence, never rule 5. The hub heard at last is the
        event that settles the session that ended across the restart. The verdict is pinned first."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        carried = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory9"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the ninth restart is a fresh module object, its memory and its link table empty")
                car = got["hubsCarried"]
                self.assertEqual((self._v(car, "spokeNew"), self._v(car, "spokeKept")),
                                 (LOST(VIA_SPOKE + " (not heard)"), LOST(VIA_SPOKE + " (not heard)", VIA_SPOKE2 + " (not heard)")),
                                 "the first write after the restart: both spoke sessions held by the hubs' carried words")
                self.assertEqual(self._v(car, "nobody"),
                                 NO_VOUCH(HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (not heard)", HUB2 + " (not heard)",
                                          HOST2 + " (not heard)", *carried, VIA_SPOKE + " (not heard)", VIA_B + " (not heard)",
                                          VIA_SPOKE2 + " (not heard)"),
                                 "every row carried, the hubs' via rows among them; the seeds' linkUp vouches for nothing")
                self.assertEqual((car["busIds"] or {}).get(HUB), "bus-hub", "the carried hub's row keeps its bus id, as every real bus's does")
                self.assertEqual(car["hosts"].get(VIA_SPOKE), L(False, False, False, True, False, False, sorted([SPOKE_KEPT, SPOKE_NEW])))
                first = got["hubsBHeardFirst"]
                self.assertEqual(self._v(first, "spokeNew"), LOST(VIA_SPOKE + " (not heard)"),
                                 "THE RULE: B heard with its link up vouches for absence, and the hub is carried with its bus id on its "
                                 "row, heard under no name in this process, so its word about the spoke is carried with it and the "
                                 "session it alone names is cannot-determine (a carry reading a carried row's bus id alone as the hub "
                                 "heard under another name dropped the via row at the first write, that session was in no row, and "
                                 "rule 5 presumed it closed on B's word: a live session on a host B never gossiped)")
                self.assertEqual(self._v(first, "spokeKept"), LOST(VIA_SPOKE + " (not heard)", VIA_SPOKE2 + " (not heard)"),
                                 "the same for the session both hubs name")
                self.assertEqual((self._v(first, "other"), self._v(first, "nobody")), (RULE_4, RULE_5), "B speaks and vouches")
                self.assertNotIn(VIA_B, first["hosts"], "the hub's word about B is dropped by the gate: B speaks for itself again")
                self.assertEqual(first["hosts"].get(VIA_SPOKE), L(False, False, False, True, False, False, sorted([SPOKE_KEPT, SPOKE_NEW])),
                                 "the hub's word about the spoke, a host nobody holds, is carried: the gate reaches no direct row")
                self.assertEqual(first["hosts"].get(HUB), L(False, False, False, True, False, False, []))
                self.assertEqual((first["busIds"] or {}).get(HUB), "bus-hub")
                last = got["hubsFirstHeard"]
                self.assertEqual((self._v(last, "spokeNew"), self._v(last, "spokeKept")), (RULE_5, RULE_4),
                                 "the event: the hub heard at last names the one session left on the spoke, and the one that ended "
                                 "across the restart is in no row while three sources vouch, rule 5")
                self.assertEqual(last["hosts"].get(VIA_SPOKE), L(True, False, False, True, True, True, [SPOKE_KEPT]))
                self.assertNotIn(VIA_B, last["hosts"], "the hub's word about B folds: B is heard and up")

    def test_a_hubs_current_word_about_a_far_bus_drops_its_own_earlier_word_alone_and_no_other_hubs(self):
        """The pair the carry drops a via row by is (hub, far bus id), not the far bus id alone (round 3 of fork PR #897,
        the reviewer's verifier: a carry dropping a carried via row on ANY heard hub's word about the far bus passed every
        pin, every fixture having one hub, and by execution presumed a live spoke session closed on the second hub's word).
        Two hubs name the spoke, the second's roster of it older; after the ninth restart the second hub is heard again
        before the first: the first hub's carried word stands and the session it alone names stays cannot-determine while
        the second hub vouches for absence. The verdict is pinned first."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                two = got["twoHubs"]
                self.assertEqual(two["filed"], [HUB, HUB2], "both hubs heard, each under its name")
                self.assertEqual((self._v(two, "spokeNew"), self._v(two, "spokeKept"), self._v(two, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "the hub names a session started on the spoke since; the second hub names the older roster")
                self.assertEqual(two["hosts"].get(VIA_SPOKE), L(True, False, False, True, True, True, sorted([SPOKE_KEPT, SPOKE_NEW])))
                self.assertEqual(two["hosts"].get(VIA_SPOKE2), L(True, False, False, True, True, True, [SPOKE_KEPT]),
                                 "one via row per hub, each under its own key and following its own link")
                self.assertEqual(((two["busIds"] or {}).get(HUB), (two["busIds"] or {}).get(HUB2)), ("bus-hub", "bus-hub2"))
                second = got["hubsSecondHeard"]
                self.assertEqual(self._v(second, "spokeNew"), LOST(VIA_SPOKE + " (not heard)"),
                                 "THE RULE: the second hub, heard again with its link up, names the spoke's bus and vouches for absence, "
                                 "but the pair the carry drops by is (hub, bus id), so its current word supersedes its own earlier word "
                                 "alone: the first hub's carried word stands and the session it alone names is cannot-determine (a carry "
                                 "dropping a carried via row on any hub's current word about the far bus dropped it here, that session "
                                 "was in no row, and rule 5 presumed it closed on the word of a hub that never heard of it)")
                self.assertEqual((self._v(second, "spokeKept"), self._v(second, "other"), self._v(second, "nobody")), (RULE_4, RULE_4, RULE_5))
                self.assertEqual(second["hosts"].get(VIA_SPOKE), L(False, False, False, True, False, False, sorted([SPOKE_KEPT, SPOKE_NEW])),
                                 "the first hub's word, carried")
                self.assertEqual(second["hosts"].get(VIA_SPOKE2), L(True, False, False, True, True, True, [SPOKE_KEPT]),
                                 "the second hub's current word, under its own key")
                self.assertEqual(second["hosts"].get(HUB), L(False, False, False, True, False, False, []), "the first hub not heard")
                last = got["hubsFirstHeard"]
                self.assertEqual(self._v(last, "spokeNew"), RULE_5, "the first hub's own current word is the event")
                self.assertEqual(last["hosts"].get(VIA_SPOKE), L(True, False, False, True, True, True, [SPOKE_KEPT]))

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
