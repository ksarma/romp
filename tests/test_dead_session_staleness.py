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
its link is KNOWN UP (a dialable PEERS row up and the host heard since the link last dropped; a heartbeat
within its TTL vouches as before, having no link, under the bus's legacy singleton scheme alone: in peer mode, the
default, a beat that reaches the bus's table is a local session's filed during a listing blink and its row vouches
for presence alone, round 3 of fork PR #897), so a heard host with no link state (a host the
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
settled the session on the other machine, the reviewer's verifier's finding). Since round 3's eleventh commit a heard
host whose exchange served a CACHED roster, its kernel listing not answering while its presence producer served the last
answered rows, vouches for presence alone (the reviewer's ruling, the road found by its refuters through the real handler
and writer): the exchange carries `presenceAnswered` in both payload builders, both recorders keep it, the writer's rows
carry `answered` (the seventh flag the reader requires) and rule 5 needs an answered listing behind the roster, released
by the next exchange that answers; the reader's reason names the cause (listing unanswered). At the tenth commit such a
host vouched for absence, and a session started there during the blink was presumed closed (the cached roster phase).
Since the fifteenth commit a heard row over a cache is the third state, beside carried and held down, in which a direct
row speaks for nothing about a session started on its host since, so a hub's word about that host stands as a via row
beside the cached row (the reviewer's verifier at the eleventh commit, by execution: the gate folded the hub's answered
word into the cached row, and rule 5 presumed a session the hub named closed while the hub vouched).
Since the twentieth commit the reader gates on the document's version (`v` 2, the version the writer stamps; any other
version, or none, is unparsable whatever its rows carry) and decodes the file's bytes as UTF-8 inside its parse try, so
bytes that are not UTF-8 answer unparsable, said once, rather than raising out of the ladder, and a carried row's values are
coerced, never dropped (the reviewer's ruling on its refuters' corrections). Since the twenty-second commit (the reviewer's
ruling of 14:57Z) one bad byte in the previous file costs the writer one sid, never the document (its previous-read decodes
with replacement for the JSON parse alone and drops a sid that fails the session-id shape), a byte-order mark is read by
both modules, and a previous file the writer cannot read whole marks the mirror, so where rule 5 would fire the ladder
answers carry-lost, cannot-determine, until the bus has heard every host its kernel links to since the mark.
Since the twenty-fourth commit (the reviewer's ruling of 15:45Z) the clear's answer is stated as the design's first-start
answer: a session on a host that no linked host hears now is outside every source after the clear, as on a first start.
Since the twenty-ninth commit (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' finding) rule 5
fires only when a host vouches for absence, none names the sid, no host HEARD in the bus's current process has an
unanswered roster (held down or not, since the thirtieth commit; the twenty-ninth read reachable rows alone) and no
lost-carry mark stands: while a heard row is unanswered the ladder answers listing-unanswered, cannot-determine, since a
session started on that host during its kernel's blink is in no row and its own mail rides the exchange that omits it,
and a down notify after that exchange does not unsend it (until the twenty-ninth commit rule 5 presumed it closed whenever
another row vouched, on four roads the refuters drove through the real builders, handler, writer and reader, and until the
thirtieth once the kernel held that host down, the reviewer's verifier's roads; all now ReaderFollowsTheWriter's roads);
what the arm leaves open and what it costs are pinned there too, each by its named witness (the writer's
_remote_sids_document names them).
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
import time
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
BLINKED = "a11f0001-1111-4222-8333-000000000016"     # a session started on HOST2 while HOST2's kernel listing did not answer: its
#                                                      exchange served the last answered rows, which do not name it
HUB_NAMED = "a11f0001-1111-4222-8333-000000000017"   # a session started on HOST2 during a later blink that the hub, its own exchange
#                                                      with HOST2 answered, names while HOST2's row here is still the cache
BLINK_BEAT = "a11f0001-1111-4222-8333-000000000018"  # a LOCAL session whose beat lands while THIS bus's kernel listing does not answer:
#                                                      the recorder files it as remote presence (the blink), a heartbeat row in peer mode
LEGACY_NAMED = "a11f0001-1111-4222-8333-000000000019"   # a session live on a host this process has not heard yet, named by the
#                                                         whitespace list a bus before 2026-09-22 wrote, beside BLINK_BEAT
VIA_NAMED = "a11f0001-1111-4222-8333-000000000020"   # a session live on the spoke that HOST2, heard, names as its word about the spoke
#                                                      beside BLINK_BEAT (the release's reach in memory)
FAR_LOST = "a11f0001-1111-4222-8333-000000000021"    # a session live on the spoke that HOST2, a hub, names before a lost carry: once
#                                                      HOST2 restarts and names it no more, outside every source after the clear
REMEMBERED = "TESTHOST-remembered"                   # an unattached host the kernel remembers with a tier: the seed's origin-only row
VIA_B_SPOKE = "via:" + HOST2 + "/" + SPOKE           # the key of HOST2's word about the spoke
LEGACY = "legacy:list"                               # the key a whitespace-list mirror is carried under (postal_service.py REMOTE_SIDS_LEGACY)
# THE ROADS (ReaderFollowsTheWriter's second child, round 4 of fork PR #897, the twenty-ninth commit): each road its own
# buses, ours over the root the test prepared and every other machine's over a state root of its own, exchanging through
# the real builders, handlers and folds (the reviewer's round-3 refuters' probe scenarios, ported)
R_US, R_B, R_C, R_HUB, R_F = "TESTHOST-us", "TESTHOST-b", "TESTHOST-c", "TESTHOST-hub", "TESTHOST-f"
R_VIA_B, R_VIA_F = "via:" + R_HUB + "/" + R_B, "via:" + R_HUB + "/" + R_F   # the hub's word about B, and about the far host F
R_HUB2, R_HUB_DECL = "TESTHOST-hub2", "TESTHOST-hub-hostname"   # a second hub; the name the hub declares before our dial
R_VIA_F2, R_VIA_F_DECL = "via:" + R_HUB2 + "/" + R_F, "via:" + R_HUB_DECL + "/" + R_F   # their words about F (the thirty-first commit)
R_G = "TESTHOST-g"                                   # a second far host behind the hub (the thirty-second commit)
R_VIA_G = "via:" + R_HUB + "/" + R_G                 # the hub's word about G
R_HUB_DECL2 = "TESTHOST-hub-hostname2"               # the name the hub declares once its hostname changes (the thirty-third commit)
ROAD_SIDS = {                                        # private synthetic sids, the probe's
    "other": "a11f0001-1111-4222-8333-000000000101",     # a session on B (or on F), live at its host's last answered listing
    "goss": "a11f0001-1111-4222-8333-000000000102",      # a session started on B while our kernel holds B down: the hub names it
    "later": "a11f0001-1111-4222-8333-000000000103",     # a session started on B across our bus's restart: the hub names it
    "nobody": "a11f0001-1111-4222-8333-000000000104",    # a sid nothing names
    "blinked": "a11f0001-1111-4222-8333-000000000106",   # a session started on B during its kernel's blink, in no roster
    "csid": "a11f0001-1111-4222-8333-000000000110",      # C's session
    "hubsid": "a11f0001-1111-4222-8333-000000000111",    # the hub's session
    "new": "a11f0001-1111-4222-8333-000000000114",       # a session started on the hub, or on F, during its kernel's blink
    "web": "a11f0001-1111-4222-8333-000000000201",       # a session on OUR host, the recipient of the new session's mail
    "gsid": "a11f0001-1111-4222-8333-000000000160",      # a session on G, a second far host behind the hub
}

RULE_5 = (True, 5, "no-reachable-host-names-it")               # the ladder's verdicts, (closed, rule, why), as
RULE_4 = (False, 4, "named-by-reachable-host")                 # _presumed_closed_verdict spells them; a fixture
NO_MIRROR = (False, None, "no-mirror")                         # written at a path nothing reads answers NO_MIRROR
UNPARSABLE = (False, None, "mirror-unparsable")
FIRST_START = ("a session on a host that no linked host hears now is outside every source after the clear, as on a first "
               "start")                                          # the reviewer's ruling of 15:45Z, the bound the clearing line states
CLEARED_RULE_5 = ("the judge's rule 5 can presume it closed while a host vouches for absence and no host heard since this "
                  "bus started has an unanswered roster")        # the clearing line's consequence: rule 5's whole condition
#                                                                  (round 4 of fork PR #897, the thirtieth commit, the reviewer's
#                                                                  ruling that every text stating rule 5's condition states the arm)


def LOST(*sources):
    """The cannot-determine verdict for a sid named only by unreachable sources: the reason names each source
    that names it with what makes it unreachable, hand-spelled here as "<key> (<cause>[, <cause>])" with the
    causes in the order not heard, expired, link down, no link state, listing unanswered (round 2 of fork PR #897,
    the reviewer's ruling: the reason names the down host; round 3: the cached roster). The expected text is this
    module's, not the reader's formatter."""
    return (False, None, "named-by-unreachable-host: " + ", ".join(sources))


def NO_VOUCH(*sources):
    """The cannot-determine verdict when no source vouches for a sid's absence: the reason names every source in
    the mirror, sorted by key, each with why it cannot vouch (not heard, expired, link down, no link state: a
    heard host the kernel never reported up, which vouches for presence alone; or listing unanswered: a heard host
    whose last exchange served a cached roster, which vouches for presence alone whatever its link, round 3), in
    the same hand-spelled form; a mirror with no row at all reads "no source" (spelled at that site). Until the
    fifth commit of round 2 this arm's token was no-reachable-host, which would lie when a reachable host exists
    whose link is unknown."""
    return (False, None, "no-host-vouches-absence: " + ", ".join(sources))


def CARRY_LOST(mark):
    """The cannot-determine verdict while the bus's LOST-CARRY MARK stands (round 3 of fork PR #897, the reviewer's ruling of
    14:57Z, the twenty-second commit): a host vouches for absence and none names the sid, but the bus could not read its
    previous file whole, so a session one of its lost rows named is in no row. Hand-spelled here as "carry-lost: <the
    mark's cause> at <its second in UTC, %Y-%m-%dT%H:%M:%SZ>" from the mark as the bus wrote it, {"cause", "at"}; the
    format is this module's, not the reader's formatter."""
    return (False, None, "carry-lost: %s at %s" % (mark["cause"], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mark["at"]))))


def UNANSWERED(*sources):
    """The cannot-determine verdict of the listing-unanswered arm (round 4 of fork PR #897, the reviewer's ruling on its
    round-3 refuters' finding, the twenty-ninth commit, and the thirtieth): a host vouches for absence and none names the
    sid, but the roster of a row HEARD in the bus's current process is unanswered, whatever its link state, held down
    included (the last answered rows its host's exchange served while its kernel listing did not answer), so a session
    started on that host since is in no row; the reason names each such row, sorted by key, with why it cannot vouch, in
    the hand-spelled form of LOST and NO_VOUCH. Until the twenty-ninth commit the reader answered rule 5 here whenever
    another row vouched: residual (3) of the writer's docstring, a live session presumed closed; until the thirtieth it
    did so for a held-down row (that commit's arm read reachable rows alone)."""
    return (False, None, "listing-unanswered: " + ", ".join(sources))


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


def _row(sids, heard=True, expired=False, kind="peer", link_down=False, link_up=False, answered=True, legacy=False):
    """One presence-source row as the bus writes it: the roster it last reported, whether the bus heard
    it in its current process, whether its presence expired, whether the kernel holds its link down (or
    has since it was heard), whether the kernel holds its link up and it was heard since the link last
    dropped, whether the roster is an ANSWERED listing (`answered`: the presenceAnswered the host's exchange
    carried, False while its kernel listing did not answer and the exchange served the last answered rows;
    True for a legacy heartbeat, its own answer; round 3 of fork PR #897), and the writer's two flags the
    reader's verdict reads: `reachable`, heard and not expired and not linkDown (it vouches for the presence
    of the sids it names), and `vouchesAbsence`, heard and not expired and answered and (linkUp, or a heartbeat
    under the bus's legacy singleton scheme, `legacy`, which vouches by its TTL there; in peer mode, the writer's
    default and this fixture's, a heartbeat row vouches for presence alone, round 3 of fork PR #897) (it vouches
    for the absence of a sid it does not name).
    postal_service.py _remote_sids_document computes both; a fixture row restates the rules so the reader is
    held to reading the flags, not recomputing them: a heard, unexpired, link-down row is unreachable, a
    heard, unexpired peer row with no link state (link_up False, the default here: a host the kernel never
    reported up) is reachable and does not vouch for absence, and so is a heard, unexpired row with its link
    up whose roster is a cache (answered False). A row NOT heard can carry link_up True (the kernel's seed of
    a tunnel up at a restart, before any exchange): it vouches for nothing, heard being the first condition
    of both flags."""
    return {"kind": kind, "sids": sorted(sids), "heard": heard, "expired": expired, "linkDown": link_down,
            "linkUp": link_up, "answered": answered, "reachable": heard and not expired and not link_down,
            "vouchesAbsence": heard and not expired and answered and (link_up or (kind == "heartbeat" and legacy)),
            "seenAt": NOW - 5}


def _bus_wrote(hosts, lost=None):
    """Write the mirror in the bus's document shape (postal_service.py _remote_sids_document: v 2 and a
    `hosts` table of rows, and `carryLost`, the lost-carry mark, when `lost` is given). A restatement of the
    writer's shape, held to it by ReaderFollowsTheWriter, whose frame pin reads the real writer's document back
    and asserts these fields."""
    doc = {"v": 2, "busStarted": NOW - 100, "writtenAt": NOW, "hosts": hosts}
    if lost is not None:
        doc["carryLost"] = lost
    _mirror().write_text(json.dumps(doc) + "\n")


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
        # named by a REACHABLE row and by a CARRIED row (round 3 of fork PR #897, the reviewer's ruling, the twentieth
        # commit): rule 4, the reader asking whether ANY row naming the sid is reachable
        _bus_wrote({HOST: _row([DEAD], link_up=True), HOST2: _row([DEAD], heard=False)})
        self.assertEqual(self._verdict(DEAD), RULE_4, "a reachable host names it: rule 4, whatever a carried row's last word "
                         "says (a reader asking whether EVERY row naming it is reachable answers named-by-unreachable-host "
                         "here)")
        # the host that names it is heard but its beat expired (the legacy TTL): unreachable the same way
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], heard=True, expired=True, kind="heartbeat"), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(DEAD), LOST("heartbeat:" + DEAD + " (expired)"), "an expired beat is unreachable, not absent")
        # a live beat in PEER MODE, the bus's default (round 3 of fork PR #897, the reviewer's ruling): the writer withholds
        # its absence vouch, since a beat that reaches the bus's table there is a local session's, filed as remote presence
        # during a listing blink; the reader reads the flag: rule 4 for the sid it names, cannot-determine for one it does
        # not, the reason naming the beat with the literal fact (a reader vouching a heartbeat by its kind answers rule 5)
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], kind="heartbeat")})
        self.assertEqual(self._verdict(DEAD), RULE_4, "the beat's row is reachable: the sid it names is live")
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH("heartbeat:" + DEAD + " (no link state)"),
                         "a peer-mode beat vouches for presence alone: cannot-determine for a sid it does not name, the reason "
                         "naming the beat (until this commit the row vouched by its TTL in both schemes, and a restarted bus "
                         "that had heard no host answered rule 5 here within the beat's TTL)")
        # the same beat under the legacy singleton scheme, where it is a remote session's only presence: it vouches by its TTL
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], kind="heartbeat", legacy=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "legacy keeps TTL vouching (round 1's ruling): rule 5")
        self.assertEqual(self._verdict(DEAD), RULE_4)
        # the blink phantom beside a host the kernel holds down (the refuter's adjacent road): nothing vouches, both named
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], kind="heartbeat"), HOST: _row([], link_down=True)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (link down)", "heartbeat:" + DEAD + " (no link state)"),
                         "a peer-mode beat beside a down host: no source vouches for absence (the TTL vouch let the beat settle "
                         "a sid while the only peer was down)")
        _bus_wrote({"heartbeat:" + DEAD: _row([DEAD], kind="heartbeat"), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "...beside a host with its link up: rule 5; the beat is not a gate on the mirror")
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
        # a host heard with its link known up whose last exchange served a CACHED roster, its kernel listing not answering
        # (round 3 of fork PR #897, the reviewer's ruling): the sids it names were live at its last answered listing, rule
        # 4; a session started there since is in no roster, so it does not vouch for absence, and the reason says why
        _bus_wrote({HOST: _row([DEAD], link_up=True, answered=False)})
        self.assertEqual(self._verdict(DEAD), RULE_4, "the cached roster vouches for the presence of the sids it names")
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (listing unanswered)"),
                         "the only heard host served a cache: its link known up, it does not vouch for absence, and the "
                         "reason says why (a reader gating rule 5 on linkUp, or on a writer that ignores the bit, answers "
                         "rule 5 here: the false settle the reviewer's refuters found; 'no link state' would lie, the link "
                         "is known up)")
        _bus_wrote({HOST: _row([DEAD], link_up=False, answered=False)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (no link state, listing unanswered)"),
                         "both causes hold at once, in the fixed order")
        _bus_wrote({HOST: _row([DEAD], link_up=True, answered=False), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), UNANSWERED(HOST + " (listing unanswered)"),
                         "...beside a host with an answered listing and its link up: RESIDUAL (3), CLOSED HERE by the "
                         "listing-unanswered arm (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' "
                         "finding, the twenty-ninth commit): a session started on the cached host during its blink is in no "
                         "row and its own mail rides the exchange that omits it, so a sid nothing names is cannot-determine, "
                         "the reason naming the cached host; until that commit this rung asserted rule 5 as a design "
                         "property, the disclosed residual (3), a live session presumed closed on the other host's vouch")
        self.assertEqual(self._verdict(DEAD), RULE_4, "...and the sid the cache names stays rule 4's")
        # the arm's conjuncts (the same ruling, and the thirtieth commit): a row HEARD in this bus process that is unanswered,
        # whatever its link state, and nothing else. A cached row the kernel never reported up, beside a vouching host: the
        # arm, both causes named
        _bus_wrote({HOST: _row([DEAD], link_up=False, answered=False), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), UNANSWERED(HOST + " (no link state, listing unanswered)"),
                         "a reachable cached row with no link state holds a sid nothing names too (cost (c)'s row shape)")
        # a HELD-DOWN unanswered row beside a vouching host: the arm too (the thirtieth commit, the reviewer's verifier at the
        # twenty-ninth, by execution): the row is heard in this process and its last exchange here served a cache, so a
        # session started on its host during the blink may have mailed this machine on that exchange, and the kernel's down
        # notify after it (or before it: the host's own dial over its cache while held down) does not unsend the mail
        _bus_wrote({HOST: _row([DEAD], link_down=True, answered=False), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), UNANSWERED(HOST + " (link down, listing unanswered)"),
                         "a held-down unanswered row beside a vouching host: listing-unanswered, both causes named (the "
                         "twenty-ninth commit's arm, keyed on reachable, answered rule 5 here: a live session whose own mail "
                         "rode its host's cached exchange presumed closed once the kernel held that host down, not named as "
                         "a residual; ReaderFollowsTheWriter's cachedThenHeldDown and heldDownDialsCached roads drive it)")
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (link down, listing unanswered)"),
                         "...and the sid it names is held by its last word, the reason saying the row is down and a cache")
        # a CARRIED unanswered row beside a vouching host keeps rule 5: its bit is its last process's, and a carried row
        # holds nothing, since a host never heard again would hold every sid for the file's life; the session whose mail
        # landed on that host's cached exchange in the previous process answers rule 5 here, RESIDUAL (3c), disclosed with
        # its witness (ReaderFollowsTheWriter
        # test_residual_3c_a_session_whose_mail_landed_on_a_cached_exchange_before_this_bus_restarted_answers_rule_5)
        _bus_wrote({HOST: _row([DEAD], heard=False, answered=False), HOST2: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "a carried unanswered row beside a vouching host: rule 5 (an arm "
                         "without the heard conjunct answers listing-unanswered here), residual (3c)")
        self.assertEqual(self._verdict(DEAD), LOST(HOST + " (not heard)"), "...and the sid it names is held by its last word")
        _bus_wrote({HOST: _row([DEAD], heard=False, answered=False), HOST2: _row([], link_down=True, answered=False)})
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (not heard)", HOST2 + " (link down, listing unanswered)"),
                         "a carried row's bit is its last process's: not a cause beside not heard; a held-down row heard in "
                         "this process whose last exchange served a cache reads both causes (until the thirtieth commit its "
                         "bit was dropped as predating the drop, which a dial over the cache while held down refutes)")
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
        # the row-shape documents below carry v 2, so each is unparsable by its rows and not by the version gate
        _mirror().write_text(json.dumps({"v": 2, "hosts": {HOST: {"sids": [DEAD]}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without heard and expired is not a roster row")
        _mirror().write_text(json.dumps({"v": 2, "hosts": {HOST: {"sids": [], "heard": True, "expired": False}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without the link flags is not the shape the bus "
                         "writes since round 2's third commit: never read as reachable by heard alone")
        _mirror().write_text(json.dumps({"v": 2, "hosts": {HOST: {"sids": [], "heard": True, "expired": False,
                                                                  "linkDown": False, "reachable": True}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without linkUp and vouchesAbsence is not the shape the "
                         "bus writes since round 2's fifth commit: never read as vouching for absence by reachable alone")
        _mirror().write_text(json.dumps({"v": 2, "hosts": {HOST: {"sids": [], "heard": True, "expired": False,
                                                                  "linkDown": False, "linkUp": True, "reachable": True,
                                                                  "vouchesAbsence": True}}}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a row without `answered` (round 2's six-flag shape) is not the "
                         "shape the bus writes since round 3's eleventh commit: never read as vouching for absence over a "
                         "roster that may be a cache (a reader accepting six flags answers rule 5 here)")
        _mirror().write_text(json.dumps({"v": 2, "hosts": [DEAD]}))
        self.assertEqual(self._verdict(DEAD), UNPARSABLE)
        # bytes that are not UTF-8 (round 3 of fork PR #897, the reviewer's ruling, the twentieth commit): unparsable, the
        # decode inside the parse's try, never a raise out of the ladder
        _mirror().write_bytes(b"\xff\xfe\n")
        self.assertEqual(self._verdict_caught(DEAD), UNPARSABLE, "two bytes that are not UTF-8: the unparsable arm (a reader "
                         "decoding outside its parse try raises UnicodeDecodeError out of the ladder here)")
        # ...and a document the bus's shape spells with ONE stray byte inside the sid a vouching host names: unparsable, never
        # repaired into another sid
        _bus_wrote({HOST: _row([DEAD], link_up=True)})
        _mirror().write_bytes(_mirror().read_bytes().replace(DEAD.encode(), DEAD[:-1].encode() + b"\xff"))
        self.assertEqual(self._verdict_caught(DEAD), UNPARSABLE, "one stray byte inside the sid HOST names: the unparsable arm "
                         "(a decode with errors='replace' reads HOST as naming another sid, and HOST, vouching for absence, "
                         "answers rule 5 for the sid it named)")
        # ...and a document nested past the JSON parser's depth (found by the twentieth commit's builder, the class of the
        # bytes): RecursionError is not a ValueError, and it lands in the same arm
        _mirror().write_text("[" * 100000 + "\n")
        self.assertEqual(self._verdict_caught(DEAD), UNPARSABLE, "nesting past the parser's depth: the unparsable arm (a reader "
                         "catching ValueError alone raises RecursionError out of the ladder here)")
        # the document's VERSION (the reviewer's ruling, the twentieth commit): v 2 alone, whatever the rows carry; the row
        # would vouch for absence, so a reader without the gate answers rule 5 for a sid it does not name
        for label, v in (("v1", 1), ("no v", None), ("v3", 3), ("the string 2", "2")):
            doc = {"busStarted": NOW - 100, "writtenAt": NOW, "hosts": {HOST: _row([], link_up=True)}}
            if v is not None:
                doc["v"] = v
            _mirror().write_text(json.dumps(doc) + "\n")
            with self.subTest(version=label):
                self.assertEqual(self._verdict(DEAD), UNPARSABLE, "a document at %s whose row spells the seven booleans and "
                                 "vouches: unparsable (a reader that never reads `v` answers rule 5 here)" % label)
        _bus_wrote({HOST: _row([], link_up=True)})
        self.assertEqual(self._verdict(DEAD), RULE_5, "the same row at v 2: rule 5, so the verdicts above are the version's")
        # a BYTE-ORDER MARK before the bus's document (round 3 of fork PR #897, the reviewer's ruling of 14:57Z, the
        # twenty-second commit): read, not refused
        _bus_wrote({HOST: _row([DEAD], link_up=True)})
        _mirror().write_bytes(b"\xef\xbb\xbf" + _mirror().read_bytes())
        self.assertEqual((self._verdict(DEAD), self._verdict(REMOTE)), (RULE_4, RULE_5),
                         "the document behind a byte-order mark is read (a strict utf-8 decode answers mirror-unparsable here)")
        # THE LOST-CARRY MARK (the same ruling): the bus could not read its previous file whole, so a session one of its lost
        # rows named is in no row; while the mark stands a sid nothing names is cannot-determine where rule 5 would fire, and
        # rule 4 and the carried rows still answer
        mark = {"cause": "previous mirror unreadable (JSONDecodeError: Expecting value: line 1 column 1 (char 0))", "at": NOW - 50}
        _bus_wrote({HOST: _row([DEAD], link_up=True), HOST2: _row([CARRIED], heard=False)}, lost=mark)
        self.assertEqual(self._verdict(REMOTE), CARRY_LOST(mark),
                         "a vouching host names nobody, but the mark stands: not established, the reason naming the lost carry, "
                         "its cause and its second (a reader ignoring the mark answers rule 5 here)")
        self.assertEqual(self._verdict(DEAD), RULE_4, "rule 4 still answers: a reachable host names the sid")
        self.assertEqual(self._verdict(CARRIED), LOST(HOST2 + " (not heard)"), "a carried row still holds the sid it names")
        _bus_wrote({HOST: _row([], heard=False)}, lost=mark)
        self.assertEqual(self._verdict(REMOTE), NO_VOUCH(HOST + " (not heard)"),
                         "no host vouches for absence: that arm answers first, the mark or not")
        _bus_wrote({HOST: _row([], link_up=True)})
        self.assertEqual(self._verdict(REMOTE), RULE_5, "the same vouching row with no mark: rule 5, so the verdict above is the "
                         "mark's")
        # THE ORDER of the listing-unanswered arm and the carry-lost arm (round 4 of fork PR #897, the twenty-ninth commit):
        # where both hold, listing-unanswered answers, naming the source whose next answering exchange releases it
        _bus_wrote({HOST: _row([DEAD], link_up=True, answered=False), HOST2: _row([], link_up=True)}, lost=mark)
        self.assertEqual(self._verdict(REMOTE), UNANSWERED(HOST + " (listing unanswered)"),
                         "a reachable unanswered row AND the mark: the listing-unanswered arm answers first, as the Deadness "
                         "comment states (the other order answers carry-lost here, as the reader did before the arm existed)")
        _bus_wrote({HOST: _row([DEAD], link_up=True), HOST2: _row([], link_up=True)}, lost=mark)
        self.assertEqual(self._verdict(REMOTE), CARRY_LOST(mark), "...and once the row answers, the mark answers")
        for label, bad in (("a string", "x"), ("a cause that is not a str", {"cause": 1, "at": NOW}),
                           ("a boolean second", {"cause": "c", "at": True}), ("a float second", {"cause": "c", "at": 1.5}),
                           ("no second", {"cause": "c"}), ("a second past the year 9999", {"cause": "c", "at": 10 ** 20}),
                           ("a second before 1970", {"cause": "c", "at": -1})):
            _bus_wrote({HOST: _row([], link_up=True)}, lost=bad)
            with self.subTest(mark=label):
                self.assertEqual(self._verdict_caught(REMOTE), UNPARSABLE, "a lost-carry mark in a shape the bus does not write: "
                                 "unparsable (a reader skipping the check answers carry-lost or raises here: time.gmtime cannot "
                                 "print a second past its range)")
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
        _mirror().write_text(json.dumps({"v": 2, "hosts": {HOST: {"sids": [DEAD]}}}))
        err2 = io.StringIO()
        with contextlib.redirect_stderr(err2):
            self.assertEqual(self._verdict(DEAD), UNPARSABLE)
        self.assertEqual(len([ln for ln in err2.getvalue().splitlines() if ln.startswith("romp-judge:")]), 1,
                         "a different failure is a different text: said once too")
        # bytes that are not UTF-8 and a document of another version (round 3 of fork PR #897, the reviewer's ruling, the
        # twentieth commit): each lands in the same arm, said once, naming the file and what failed
        for label, write, said in (("bytes", lambda: _mirror().write_bytes(b"\xff\xfe\n"), "UnicodeDecodeError"),
                                   ("version", lambda: _mirror().write_text(json.dumps({"v": 1, "hosts": {}})),
                                    "version is 1, not 2")):
            with self.subTest(failure=label):
                write()
                err3 = io.StringIO()
                with contextlib.redirect_stderr(err3):
                    got = (self._verdict_caught(DEAD), self._verdict_caught(REMOTE))
                self.assertEqual(got, (UNPARSABLE, UNPARSABLE))
                lines = [ln for ln in err3.getvalue().splitlines() if ln.startswith("romp-judge:")]
                self.assertEqual(len(lines), 1, "said once per distinct text: %r" % lines)
                self.assertIn(str(_mirror()), lines[0], "the line names the file")
                self.assertIn(said, lines[0], "the line says what failed")

    def _verdict_caught(self, sid):
        """The verdict, or ("raised", <type>, <text>) when the ladder raises: a reader that raises out of the ladder fails
        the assertion asking for its verdict, by that assertion's message, rather than erroring the test before it."""
        try:
            return self._verdict(sid)
        except Exception as e:
            return ("raised", type(e).__name__, str(e)[:120])


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
    (_bus_wrote) is held to the writer here. The phases, in the order a bus lives them (the five heartbeat
    phases under the LEGACY singleton scheme, ROMP_POSTAL_PEERS=0 set in the child's environment before the
    first write and read back through peers_on, since round 3 of fork PR #897: a heartbeat row vouches for
    absence there alone; the switch is popped before the peer phases, and the peer-mode beat has a phase of
    its own below):
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
      the cached roster  a heard host whose exchange served a CACHED roster vouches for presence alone (round 3 of fork
                    PR #897, the reviewer's ruling; the road its refuters found by execution through the real handler and
                    writer). While a host's kernel listing does not answer, its presence producer serves the last answered
                    rows (the blink honesty of 2026-08-31), and until this round that cache rode the exchange with no sign
                    of it. A tenth restart; the kernel seeds B's link up; B's request is built by the REAL builder
                    (build_exchange_request) under this process's listing state and handed to the real handler as B's (one
                    module plays both buses), so the sender's bit, the request builder, the handler's recorder and the
                    writer are the product's: with B's listing answering, B vouches (rule 4 for its sid, rule 5 for a sid
                    nothing names); with the listing not answering (the seam unset, the kernel route pointed at a loopback
                    port nothing listens on), B's request serves the same rows marked unanswered (`presenceAnswered`
                    False), and B's row is reachable, its link up, and does not vouch: its sid is rule 4's still, and a
                    session started on B during the blink, in no roster, is cannot-determine, the reason naming B with its
                    listing unanswered beside the carried rows (at the tenth commit B vouched for absence over the cache,
                    and rule 5 presumed that session closed); B's next exchange with an answered listing, naming the
                    session, is the event: rule 4 for it, rule 5 again for a sid nothing names. Then the dialer's half the
                    same way: the real handler's response, built while this process's listing does not answer, folded by
                    the real dialer's fold (peer_exchange_apply) as B's word carries the bit False and B vouches for
                    presence alone; the response built once the listing answers releases it. Then the hub's word
                    beside the cached row (the reviewer's verifier at the eleventh commit, by execution through the real
                    builder, handler, writer and reader): B's kernel blinks again and a session starts on B meanwhile; B's
                    dial serves the cache; the hub, notified up and heard through the real fold, its own exchange with B
                    answered, names the session: a heard row over a cache is the third state, beside carried and held
                    down, in which a direct row speaks for nothing about a session started on its host since, so the hub's
                    word stands as a via row beside B's cached row, carrying B's bit as the hub stamped it, and the session
                    is rule 4's (at the eleventh commit the gate read heard and not held down alone, the hub's word folded
                    into the cached row, and the hub, vouching for absence, let rule 5 presume the session closed for one
                    exchange interval of B: a live session presumed closed while another host vouched). An eleventh
                    restart; the kernel seeds every link up; B is heard first, still over the cache (the restarted producer
                    primed from its disk twin), the second hub heard and vouching for absence, the hub not heard: the
                    carried via row stands beside the cached row, so the session is cannot-determine by the hub's last
                    word, never rule 5 (a carry letting the cached row speak drops the row, and the second hub's vouch
                    settles a live session). B's exchange that answers, naming the session, is the event: B speaks, the via
                    row is dropped by the carry, and the hub's next exchange folds;
      the peer-mode beat  a heartbeat row vouches for absence under the legacy singleton scheme alone (round 3 of fork
                    PR #897, the reviewer's ruling on its refuters' finding). In peer mode, the default, the beats that
                    reach the bus's table are LOCAL sessions' beats, filed as remote presence by the real recorder
                    (_record_heartbeat) while this kernel's listing does not answer. A twelfth restart over an emptied
                    mirror (the previous file removed, so the reasons name the beat and the one peer alone), in peer
                    mode (the child's environment carries no switch; read back); the listing does not answer (the seam
                    unset, the kernel route pointed at a loopback port nothing listens on); a local session's beat
                    arrives through the real recorder, which files it and writes: the beat's sid is rule 4's, and a
                    sid nothing names is cannot-determine, the reason naming the beat with no link state (until this
                    commit the row vouched by its TTL in both schemes, and rule 5 presumed every sid nothing named closed
                    within 90 s of the beat, on a bus that had heard no host). B heard with its link up: rule 5 by B's
                    vouch, the beat no gate on the mirror; the kernel's down notify for B: cannot-determine, the reason
                    naming B down and the beat (the blink phantom vouching while a peer's link is down, the refuter's
                    adjacent road; the TTL vouch answered rule 5 here). The same rows under the legacy scheme
                    (ROMP_POSTAL_PEERS=0 set, read back, the writer run again): rule 5, the beat a remote session's only
                    presence there vouching by its TTL whatever B's link; the switch popped and the writer run again:
                    cannot-determine again. Then the listing answers owning nothing (a consumer's read, a bare write):
                    the row and the entry stay, the listing not owning the sid. Then the listing answers naming the
                    beating session: the recorder calls it local, and the writer's ONE RELEASE (the seventeenth commit,
                    the reviewer's ruling) drops the row and forgets the entry, so the sid is in no row and no reason
                    (on a real root rules 1 and 2 own it, its transcript being local; this child's HOME is empty, so the
                    ladder shows the mirror's answer, naming B alone); a blink's bare write after it does not bring the
                    row back (the sixteenth commit had kept the key and the row, refusing a pop in the recorder that left
                    the carry a key to re-file from the file; the writer's own drop leaves it none);
      the release's reach  the release reaches heartbeat rows alone (the reviewer's verifier at the seventeenth commit: a
                    carry with its kind test deleted passed every pin). A thirteenth restart over the whitespace list a bus
                    before 2026-09-22 wrote, naming the beating local session beside a session live on a host this process
                    has not heard yet; the listing answers owning the local session (a consumer's read); B heard with its
                    link up, naming neither. The list is carried whole, so the unheard host's session is cannot-determine
                    by it, while B vouches and a sid nothing names is rule 5's (a carry releasing every row kind that names
                    an owned sid drops the list, and the reader presumes that live session closed on B's word). Then, IN
                    MEMORY (the reviewer's verifier at the eighteenth commit: a writer dropping a heard via row that names an
                    owned sid passed every pin), B's next exchange through the real handler names, as its word about the
                    spoke, the local session beside a session live there, the listing still owning the local session: the
                    via row is written whole, so the spoke's session is rule 4's by it while B vouches (a writer dropping
                    the via row leaves it in no row, and the reader presumes it closed on B's word);
      the mirror's bytes and version  round 3 of fork PR #897, the reviewer's ruling, the twentieth commit. Bytes that are
                    not UTF-8 at the bus's path: the reader answers cannot-determine for every sid, said once naming the file
                    (until the commit its decode sat outside the parse's try and raised out of the ladder); a fourteenth
                    restart's first writes replace them from memory, carrying nothing (until the commit the writer's
                    previous-read raised there too, so every write failed and the file was never replaced), and B names its
                    session, rule 4; since the twenty-second commit the garbage is a file the writer cannot read whole, so
                    the mirror is marked and a sid nothing names is carry-lost while B vouches. One stray byte inside the sid B names in the writer's own document: unparsable,
                    never repaired into another sid (a replacing decode reads B as naming another sid, and B's vouch answers
                    rule 5 for the sid B named; the reader stays strict, the writer's parse alone replacing). A document
                    nested past the JSON parser's depth: unparsable, and B's next exchange replaces it, marked (RecursionError is not a ValueError: until the commit the reader raised it out of
                    the ladder and the writer's previous-read failed every write; found by the commit's builder, the class
                    of the bytes). A hand-written document whose rows carry a non-bool flag, an unhashable busId
                    and an unhashable sid beside a live session's: the reader refuses it, and B's next exchange writes the
                    three rows carried and coerced, the unhashable sid's text dropped as no session id since the
                    twenty-second commit, so each sid they name is cannot-determine by its row while B vouches (until the commit the unhashable values failed every write and the non-bool flag left every later
                    mirror unparsable; a writer DROPPING the row with the non-bool flag answers rule 5 for the sid it named).
                    A document at v 1 and one with no v, whose row names a sid and vouches: the reader refuses both (until the
                    commit `v` was decorative, and they answered rule 4 and rule 5); B's next exchange writes over the one
                    with no v, carrying its roster (the carry reads any version, a carried row vouching for nothing) and
                    stamping v 2;
      one bad byte  the reviewer's verifier at the twentieth commit, and the reviewer's ruling of 14:57Z, clause 1, the
                    twenty-second commit. A heard with its link up beside B, one byte inside the sid B names made a stray
                    byte in the writer's own document, a fifteenth restart, B heard first. The previous-read decodes with
                    replacement for its JSON parse, drops the one sid and carries A's row, so A's live session is held by
                    A's last word while B vouches, and the bus log says once which file and how many (at the twenty-first
                    commit the strict read carried nothing and rule 5 presumed A's session closed until A was heard);
      the byte-order mark  the same ruling, clause 1: the writer's own document behind a byte-order mark is read by the
                    reader (until the commit: unparsable) and, after a sixteenth restart with B heard first, carried by the
                    writer, A's row with it;
      the lost carry  the same ruling, clauses 2 and 3. The writer's own document made not JSON (a stray brace); a
                    seventeenth restart whose seed reads the kernel's list with both links up (the real seed, its transport
                    stubbed), its own writes reading the file and marking the mirror with the cause and the second; B heard
                    first: A's live session, its row lost, and a sid nothing names are carry-lost, cannot-determine, and
                    B's session is rule 4's (at the twenty-first commit both answered rule 5). An eighteenth restart whose
                    seed fails, B and A notified one at a time and heard: the mark stands, carried. A nineteenth restart
                    whose seed reads the list: B heard, A linked and unheard, the mark stands; A heard, the last linked
                    host heard since the mark: cleared, said once in the bus log, and rule 5 answers again. Every seed
                    also reads one remembered unattached host, an origin-only row, which is no link and never heard, so
                    the clearing holds only because such a row does not count (the reviewer's verifier at the
                    twenty-second commit);
      the clearing's bound  the reviewer's verifier at the twenty-second commit, and the reviewer's ruling of 15:45Z
                    (postal_service.py _remote_sids_lost_cleared: a session on a host that no linked host hears now is
                    outside every source after the clear, as on a first start). B, a linked hub beside A, names a session
                    on the spoke, never linked here. With the file intact, a twentieth restart and B heard after its own
                    restart, naming nothing on the spoke: the carried via row names the session, cannot-determine. With
                    the file made not JSON, a twenty-first restart, the same road: the mark clears and the session
                    answers rule 5 (A vouches as well as B, so this phase is the contrast, not the ruled road);
      a mark at second 0  the same verifier: a twenty-second restart over the writer's document with A's row removed and a
                    hand-written mark at second 0; a drift note for A and B heard: the mark stands and A's session is
                    carry-lost (a host with no seenAt read as second 0 cleared it); A heard: cleared;
      as on a first start  the reviewer's ruling of 15:45Z, clause 5, its named witness (the twenty-fourth commit). A
                    twenty-third restart seeded with B alone, the only link; B, a hub, names a session on the spoke; the
                    file made not JSON; a twenty-fourth restart seeded with B alone, whose own writes mark the mirror; B
                    heard after its own restart, no longer hearing the spoke: the mark clears, B's row is the one row
                    and vouches for absence, and the spoke's session answers rule 5. A twenty-fifth restart over no
                    file, a first start seeded with B alone, B heard the same way: the same rows and verdicts;
      legacy shape  the whitespace list a bus before 2026-09-22 wrote, at the bus's path: the reader
                    answers cannot-determine for the sid it does not name AND for the one it does, and
                    says once in the judge's log that the file is not the shape the bus writes; it is
                    never read as an empty roster;
      both classes  the reviewer's ruling of 17:47Z, the twenty-fifth commit, run last, after the control. The class
                    json.loads raises on the nested document is the interpreter's (RecursionError on this box,
                    JSONDecodeError on a CI runner's 3.14t), so the nested phase above derives it from the parse; here
                    json.loads is stubbed to raise each class in turn on the nested document: the last restart's
                    previous-read carries nothing and marks the document with that class in the cause, and the reader
                    answers unparsable, said naming that class.
    THE ROADS, a second child (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' finding, the
    twenty-ninth commit; _roads_over_one_root): each road its own buses, ours over the root the test prepared, every
    other machine's over a state root of its own, exchanging through the real request builder, handler and fold, the
    kernel's notify through the real handler, each kernel listing answering through the seam or not answering, our
    bus writing and the judge reading. The four roads of the refuters' finding (a hub serving its cache beside its own
    vouching word about B; B serving its cache beside C; a far host's cached word through a heard hub; a session's own
    mail riding its host's cached exchange), each rule 5 before the listing-unanswered arm and cannot-determine by it,
    with the arm's release on the source's next answering exchange; the release pins (B_cached, B_older_peer); the
    controls (the A road, a down host beside C, a lone cached host); residual (3a), a far host whose cached roster is
    empty behind a heard hub, whose session still answers rule 5; residual (3b), a far host gone after a cached
    exchange with its hub; and the witnesses of costs (a) and (c). Since the thirtieth commit (the reviewer's verifier
    at the twenty-ninth, by execution) the held-down roads: a host whose cached exchange carried its session's mail
    held down by our kernel after it (by its request, V5, or its response to our dial, V5b; beside C, or beside the
    hub's answered word about it, V21), a held-down host dialing us over its cache with the mail (V1), and a far host's
    cached word through a hub our kernel then holds down (V7), each rule 5 under the twenty-ninth commit's arm and
    cannot-determine by the arm since; residual (3c), a session whose mail landed on a cached exchange before our bus
    restarted, which still answers rule 5; and the witness of cost (f), a host held down after a cached exchange that
    never returns. Since the thirty-first commit (the reviewer's verifier at the thirtieth, by execution) the hub's
    restart: a far host's cached word through a hub, carrying its session's mail here, held on the hub's row across
    the hub's bus restart (W1), beside a second hub's older answered word about the host and then released by our own
    bus's restart, residual (3c)'s far-host face (W2), and across the restart of a hub known here only by the name it
    declares and this bus's fold of it under the alias; each rule 5 at the thirtieth commit at the hub's restart and
    cannot-determine by the arm since, W1 and the declared-name road until the far host answers the restarted hub.
    Since the thirty-second commit (the reviewer's verifier at the thirty-first, by execution) the same hub process's
    silence: the far host answering that hub with an EMPTY listing releases its held word through the hub's dial, our
    dial and the fold of the hub's declared-name row (Z2; held for the bus process's life at the thirty-first); the
    same answer to a RESTARTED hub holds it until our bus restarts, cost (g); residual (3a)'s second face, the far
    host's bus restarted with no twin, whose empty cache the same hub's silence cannot be told from an answer; a
    restarted hub naming another far host first, which releases nothing (Z1); and the far host answering here
    directly while its word is held, its own row consuming the word through the fold (Z3). Since the thirty-third
    commit (the reviewer's verifier at the thirty-second, by execution) the road: the same hub process's omission
    releases a held word only on the road whose roster last named the host, the hub's dial or its answer to our dial,
    so the verifier's R1, the restarted hub's answer to our dial taken before its dial naming F's cached word and
    folded after it, holds the word (rule 5 at the thirty-second), until the hub's next dial omits F, cost (h); our
    dial releases once its answer has named F; the fold of the hub's declared-name row by our dial holds and the hub's
    next dial releases, while the fold by the hub's own dial under a new name releases; a far host with no bus id is
    released the same way (the verifier's green mutant N9); and residual (3d), a roster recorded after a newer one
    from the same source, three faces each still rule 5.
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
        cls.roads = {shape: cls._roads_over_one_root(shape) for shape in ("XDG_STATE_HOME", "ROMP_STATE_DIR")}

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
 collided, ended, decl_named, spoke_kept, spoke_gone, hub_declared, spoke, spoke_declared, hub2, spoke_new, blinked,
 hub_named, blink_beat, legacy_named, via_named, far_lost, remembered) = sys.argv[1:33]
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
os.environ["ROMP_POSTAL_PEERS"] = "0"              # the heartbeat phases run under the LEGACY singleton scheme, where a beat is a
out["schemeAtFirstWrite"] = pm.peers_on()          # remote session's only presence and its row vouches by its TTL (round 3 of fork
pm.HEARTBEATS[remote] = ("web", now)               # PR #897); the first bus process hears one live remote session
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
                            "seenAt": int(time.time()), "presenceAnswered": True}   # the host's listing answered for the roster
    if bus_id:
        bus.PEER_STATE[host]["busId"] = bus_id
    bus._write_remote_sids()
os.environ.pop("ROMP_POSTAL_PEERS", None)          # peer mode, the default, for the peer phases (the child's environment carries no
out["schemeAtPeerPhases"] = pm2.peers_on()         # switch of its own); pm2's heartbeat rows are carried from the next restart on
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
def link_phase(extra=None):                        # the rows with the six flags the link phases pin (the seventh, answered, rides cache_phase), and the verdicts
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
           "acks": [], "bounces": [], "wait": False, "presence": [{"id": s, "name": "api"} for s in sids], "presenceAnswered": True}
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
pm5.peer_exchange_apply(alias, {}, {"presence": [{"id": far_sid, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-x",
                                    "presenceAnswered": True})
out["aliasFolded"] = alias_phase(pm5)              # this bus's own dial landed under the alias: the fold
notify(pm5, alias, False)
out["aliasDownAfterFold"] = alias_phase(pm5)
notify(pm5, alias, True)
out["aliasUpUnheard"] = alias_phase(pm5)
out["aliasRedialStatus"] = far_dials_us(pm5, [far_sid])   # the far bus dials again: canonicalized under the alias, the link up
out["aliasUpHeard"] = alias_phase(pm5)
# THE HUB'S WORD: a fifth restart; host B heard directly and held down, or carried, while a hub gossips a session started on B since
pm6, out["restartMemory5"] = restarted("romp_postal_oneroot_restarted_fifth", pm5)
def gossip(bus, sids, via_bus="bus-b", other=()):  # the hub's exchange landing: one hop of gossip about host B, stamped with B's bus id and
    bus.PEER_STATE[hub] = {"presence": [{"id": s, "name": "api", "via": host_b, "viaBus": via_bus, "viaAnswered": True} for s in sids]   # B's answered
                           + [{"id": s, "name": "api", "via": host_b, "viaBus": "bus-other", "viaAnswered": True} for s in other],       # bit; `other`: sids
                           "epoch": 1, "holds": [], "seenAt": int(time.time()), "presenceAnswered": True}   # on ANOTHER machine the hub calls by B's name
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
def hub_gossip(b_sids, spoke_name, spoke_sids):     # the far hosts' answered bits, as the hub's builder stamps them
    return ([{"id": s, "name": "api", "via": host_b, "viaBus": "bus-b2", "viaAnswered": True} for s in b_sids]
            + [{"id": s, "name": "api", "via": spoke_name, "viaBus": "bus-spoke", "viaAnswered": True} for s in spoke_sids])
def hub_dials_us(bus, b_sids, spoke_name, spoke_sids):     # the dialed side of one exchange, through the real handler
    req = {"host": hub_declared, "epoch": 1, "proto": bus.PEER_PROTO, "busId": "bus-hub", "holds": [], "relays": [],
           "acks": [], "bounces": [], "wait": False, "presence": hub_gossip(b_sids, spoke_name, spoke_sids), "presenceAnswered": True}
    resp, status = bus.peer_exchange_handle(req)
    return status
def our_dial_lands(bus, b_sids, spoke_name, spoke_sids):   # the dialer's half, through the real fold
    bus.peer_exchange_apply(hub, {}, {"epoch": 1, "holds": [], "busId": "bus-hub", "presenceAnswered": True,
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
    bus.peer_exchange_apply(hub2, {}, {"epoch": 1, "holds": [], "busId": "bus-hub2", "presenceAnswered": True,
                                       "presence": [{"id": s, "name": "api", "via": spoke, "viaBus": "bus-spoke", "viaAnswered": True}
                                                    for s in spoke_sids]})
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
# THE CACHED ROSTER: a tenth restart; B is heard with its link up, but its exchange served the last answered rows through a
# kernel blink. One module plays both buses: B's request is built by the REAL builder under this process's listing state and
# handed to the real handler as B's, so the sender's bit, the request builder, the handler's recorder and the writer are the
# product's; then the real handler's response is folded by the real dialer's fold the same way
pm11, out["restartMemory10"] = restarted("romp_postal_oneroot_restarted_tenth", pm10)
pm11.KERNEL_BASE = "http://127.0.0.1:9"           # with the seam unset the listing fetch goes here, where nothing listens: unanswered
def cache_phase(bus, payload):                     # the rows' answered bits, the payload's bit and rows, and the verdicts
    answered = None
    if bus_file.exists():
        try:
            answered = {k: r.get("answered") for k, r in json.loads(bus_file.read_text())["hosts"].items()}   # .get: a writer
        except (ValueError, KeyError, TypeError):                                                              # without it fails a pin by None
            answered = None
    return link_phase({"blinked": verdict(blinked), "answered": answered, "filed": sorted(bus.PEER_STATE),
                       "payloadAnswered": payload.get("presenceAnswered"),
                       "payloadSids": sorted(a.get("id") for a in payload.get("presence") or [])})
def listing_answers(sids):                         # B's kernel listing answers with these sessions (the seam)
    with open(listing, "w") as f:
        f.write(json.dumps([{"id": s, "name": "api"} for s in sids]))
    os.environ["ROMP_SESSIONS_FILE"] = listing
def listing_blinks():                              # B's kernel mid-restart: the listing does not answer
    os.environ.pop("ROMP_SESSIONS_FILE", None)
def b_dials_us(bus):                               # B's request, the real builder's under this process's listing, handed to the real handler as B's
    req = bus.build_exchange_request(host_b, wait=False)
    req["host"], req["busId"] = host_b, "bus-b2"
    resp, status = bus.peer_exchange_handle(req)
    return req, status
notify(pm11, host_b, True)                         # the kernel's seed: B's link up, nothing heard yet
listing_answers([other])
req, out["cacheDialStatus"] = b_dials_us(pm11)
out["cacheAnswered"] = cache_phase(pm11, req)      # B heard with its link up on an answered roster: it vouches
listing_blinks()                                   # B's kernel restarts; a session (blinked) starts on B meanwhile, in no roster yet
req, out["cacheBlinkDialStatus"] = b_dials_us(pm11)
out["cacheBlink"] = cache_phase(pm11, req)         # B's exchange served the cache: presence alone
listing_answers([other, blinked])                  # B's listing answers again, naming the session started during the blink
req, status = b_dials_us(pm11)
out["cacheAnswersAgain"] = cache_phase(pm11, req)  # the event
def b_request(bus, sids):                          # a request of B's, answered, so the handler builds OUR response to it
    return {"host": host_b, "epoch": 1, "proto": bus.PEER_PROTO, "busId": "bus-b2", "holds": [], "relays": [], "acks": [],
            "bounces": [], "wait": False, "presence": [{"id": s, "name": "api"} for s in sids], "presenceAnswered": True}
listing_blinks()                                   # this process's listing does not answer: the response it builds serves the cache
resp, status = pm11.peer_exchange_handle(b_request(pm11, [other, blinked]))
pm11.peer_exchange_apply(host_b, {}, resp)         # folded by the real dialer's fold as B's word (the same module plays B)
out["cacheResponseBlink"] = cache_phase(pm11, resp)
listing_answers([other, blinked])
resp, status = pm11.peer_exchange_handle(b_request(pm11, [other, blinked]))
pm11.peer_exchange_apply(host_b, {}, resp)
out["cacheResponseAnswers"] = cache_phase(pm11, resp)
# THE HUB'S WORD BESIDE THE CACHED ROW (the reviewer's verifier at the eleventh commit): B's kernel blinks again and a session
# (hub_named) starts on B meanwhile; B's dial to us serves the cache; the hub, its own exchange with B answered, names the
# session through the real fold. The cached row speaks for nothing about it, so the hub's word stands as a via row beside it.
# Then the same with the hub NOT heard: an eleventh restart, B heard first over the cache, a second hub vouching for absence.
# B's exchange that answers is the event
def cache_hub_phase(bus, payload):                 # cache_phase plus the verdict for the session the hub names
    got = cache_phase(bus, payload)
    got["hubNamed"] = verdict(hub_named)
    return got
listing_blinks()                                   # B's kernel restarts again; hub_named starts on B meanwhile, in no roster yet
req, out["cacheHubBlinkDialStatus"] = b_dials_us(pm11)
out["cacheHubBlink"] = cache_hub_phase(pm11, req)  # B's exchange served the cache; the hub not heard yet: hub_named in no row
notify(pm11, hub, True)
our_dial_lands(pm11, [other, blinked, hub_named], spoke, [spoke_kept])   # the hub's exchange with B answered: its builder stamps B's bit True
out["cacheHubWord"] = cache_hub_phase(pm11, req)
pm12, out["restartMemory11"] = restarted("romp_postal_oneroot_restarted_eleventh", pm11)
pm12.KERNEL_BASE = "http://127.0.0.1:9"           # the listing still does not answer in the new process
notify(pm12, host_b, True)                         # the kernel's seeds: every link up, nothing heard yet
notify(pm12, hub, True)
notify(pm12, hub2, True)
req, out["cacheHubCarriedDialStatus"] = b_dials_us(pm12)   # B heard first, its exchange still a cache (the disk twin primes the producer)
hub2_gossip(pm12, [spoke_kept])                    # the second hub heard, answered, its link up: it vouches for absence; the hub not heard
out["cacheHubWordCarried"] = cache_hub_phase(pm12, req)
listing_answers([other, blinked, hub_named])       # B's listing answers, naming the session started during the blink
req, status = b_dials_us(pm12)
out["cacheHubWordReleased"] = cache_hub_phase(pm12, req)   # the event: B speaks, the carried via row is dropped
our_dial_lands(pm12, [other, blinked, hub_named], spoke, [spoke_kept])   # the hub heard at last: its word folds
out["cacheHubWordFolds"] = cache_hub_phase(pm12, req)
# THE PEER-MODE BEAT (round 3 of fork PR #897, the reviewer's ruling): a twelfth restart over an EMPTIED mirror (the previous file
# removed, so the reasons name the beat and the one peer alone), in peer mode; this bus's own listing does not answer; a local
# session's beat arrives through the REAL recorder and is filed as remote presence: the blink
bus_file.unlink(missing_ok=True)
pm13, out["restartMemory12"] = restarted("romp_postal_oneroot_restarted_twelfth", pm12)
pm13.KERNEL_BASE = "http://127.0.0.1:9"           # with the seam unset the listing fetch goes here, where nothing listens: unanswered
listing_blinks()
def beat_phase(bus):                               # the seven-flag rows, the verdicts for a sid nothing names and for the beating sid,
    return link_phase({"beat": verdict(blink_beat), "scheme": bus.peers_on(),   # the scheme read back, and whether the key is kept
                       "keyKept": blink_beat in bus.HEARTBEATS})
out["beatRecordedLocal"] = pm13._record_heartbeat(blink_beat, "web")   # False: the listing did not answer; the beat is filed, the mirror written
out["peerBeat"] = beat_phase(pm13)
notify(pm13, host_b, True)
exchange(pm13, host_b, [other], bus_id="bus-b2")   # B heard with its link up: the one source vouching for absence
out["peerBeatBesideUp"] = beat_phase(pm13)
notify(pm13, host_b, False)                        # the kernel holds B's link down: the beat is the only row not held down
out["peerBeatBesideDown"] = beat_phase(pm13)
os.environ["ROMP_POSTAL_PEERS"] = "0"              # the same rows under the legacy singleton scheme: the beat vouches by its TTL
pm13._write_remote_sids()
out["legacyBeatBesideDown"] = beat_phase(pm13)
os.environ.pop("ROMP_POSTAL_PEERS", None)          # peer mode again: the scheme is read at each write, nothing stored on the row
pm13._write_remote_sids()
out["peerBeatAgain"] = beat_phase(pm13)
listing_answers([])                                # the kernel answers owning nothing: a consumer's read, then a bare write
pm13.local_agents_checked()
pm13._write_remote_sids()
out["peerBeatUnowned"] = beat_phase(pm13)          # the row and the entry stay: the listing does not own the sid
listing_answers([blink_beat])                      # the kernel answers: the beating session is local
out["beatConfirmedLocal"] = pm13._record_heartbeat(blink_beat, "web")   # True; the recorder's write releases the row and forgets the entry
out["peerBeatLocal"] = beat_phase(pm13)
listing_blinks()                                   # a blink's bare write after the release: the row does not return
pm13._write_remote_sids()
out["peerBeatLocalBlinkAgain"] = beat_phase(pm13)
# THE RELEASE'S REACH (the reviewer's verifier at the seventeenth commit): the release reaches heartbeat rows alone. A thirteenth
# restart over the whitespace list a bus before 2026-09-22 wrote, naming the local session beside a session live on a host this
# process has not heard yet; this bus's listing answers owning the local session; B heard with its link up, naming neither
bus_file.write_text(blink_beat + "\n" + legacy_named + "\n")
pm14, out["restartMemory13"] = restarted("romp_postal_oneroot_restarted_thirteenth", pm13)
pm14.KERNEL_BASE = "http://127.0.0.1:9"           # the seam decides below; with it unset the fetch goes where nothing listens
listing_answers([blink_beat])                      # this bus's listing answers, owning the local session
out["reachOwned"] = [r.get("id") for r in pm14.local_agents_checked()[0]]   # a consumer's read: the record the release reads
notify(pm14, host_b, True)
exchange(pm14, host_b, [other], bus_id="bus-b2")   # B heard with its link up, answered, naming neither sid of the list
out["releaseReach"] = link_phase({"legacyNamed": verdict(legacy_named), "owned": verdict(blink_beat)})
# THE RELEASE'S REACH IN MEMORY (the reviewer's verifier at the eighteenth commit): B's next exchange, through the real handler,
# names the local session beside a session live on the spoke, as its word about the spoke; the handler's response reads this
# bus's listing, still answering owning the local session, and its recorder writes the mirror
req = {"host": host_b, "epoch": 1, "proto": pm14.PEER_PROTO, "busId": "bus-b2", "holds": [], "relays": [], "acks": [],
       "bounces": [], "wait": False, "presenceAnswered": True,
       "presence": [{"id": other, "name": "api"}] + [{"id": s, "name": "api", "via": spoke, "viaBus": "bus-spoke", "viaAnswered": True}
                                                     for s in (blink_beat, via_named)]}
resp, out["reachMemoryDialStatus"] = pm14.peer_exchange_handle(req)
out["reachMemoryOwned"] = sorted(pm14._local_listing_owned())
out["releaseReachMemory"] = link_phase({"viaNamed": verdict(via_named), "owned": verdict(blink_beat)})
# THE MIRROR'S BYTES AND VERSION (round 3 of fork PR #897, the reviewer's ruling, the twentieth commit): bytes that are not
# UTF-8 at the bus's path, read by the reader and then replaced by a restarted writer; one stray byte inside a sid the vouching
# host names; a hand-written document whose rows carry values of the wrong types, carried by the writer; documents of another
# version, read by the reader and carried by the writer
def caught(sid):                                   # the verdict, or what the ladder raised: a raise fails a pin by its message
    try:
        return verdict(sid)
    except Exception as e:
        return ["raised", type(e).__name__, str(e)[:80]]
def mirror_rows():                                 # link_phase's rows, read from the BYTES: a file that is not UTF-8 is reported
    if not bus_file.exists():                      # by its first bytes rather than crashing the child
        return None
    data = bus_file.read_bytes()
    try:
        doc = json.loads(data.decode("utf-8"))
        return {k: [r["heard"], r["expired"], r["linkDown"], r.get("linkUp"), r["reachable"], r.get("vouchesAbsence"), r["sids"]]
                for k, r in doc["hosts"].items()}
    except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return repr(data[:60])
def mirror_mark():                                 # the document's lost-carry mark, or None (no mark, or no document to hold one)
    try:
        return json.loads(bus_file.read_bytes().decode("utf-8")).get("carryLost")
    except (OSError, ValueError, AttributeError, RecursionError):
        return None
def mirror_phase(**sids):                          # the verdicts for the named sids, the rows, the mark, and the judge's log lines they said
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        got = {name: caught(sid) for name, sid in sids.items()}
    got["hosts"] = mirror_rows()
    got["mark"] = mirror_mark()
    got["log"] = [ln for ln in err.getvalue().splitlines() if ln.startswith("romp-judge:")]
    return got
garbage = b"\x89PNG\r\n\x1a\n\xff\xd8 IHDR tEXt\n"   # bytes no bus wrote, with two safe-id-shaped runs a replacing decode would carry
bus_file.write_bytes(garbage)
out["bytesRead"] = mirror_phase(nobody=dead, other=other)   # the reader first: no write in this state yet
pm15, out["restartMemory14"] = restarted("romp_postal_oneroot_restarted_fourteenth", pm14)
pm15.KERNEL_BASE = "http://127.0.0.1:9"           # no listing fetch reaches anything
notify(pm15, host_b, True)                         # B's link up (the notify writes too), then B heard: the write replaces the garbage
exchange(pm15, host_b, [other], bus_id="bus-b2")
out["bytesWritten"] = mirror_phase(nobody=dead, other=other)
data = bus_file.read_bytes()                       # the writer's own document, one byte inside the sid B names made a stray byte
bus_file.write_bytes(data.replace(other.encode(), other[:-1].encode() + b"\xff"))
out["strayByte"] = mirror_phase(nobody=dead, other=other)
def nested_parse_raises(data):                     # (the class json.loads raises on the document `data` in THIS interpreter,
    depth = len(data) - len(data.lstrip(b"["))     # or None when it returns; the depth of its nesting): the class is the
    try:                                           # interpreter's since 3.14 (the reviewer's ruling of 17:47Z, the twenty-fifth
        json.loads(data.decode("utf-8-sig"))       # commit; tests/test_postal_remote_sids_mirror.py _nested_parse_raises)
    except Exception as e:
        return type(e).__name__, depth
    return None, depth
bus_file.write_text("[" * 100000 + "\n")           # nested past the JSON parser's depth: the class its parse raises, derived here
out["deepParse"] = list(nested_parse_raises(bus_file.read_bytes())) + [sys.version]   # from the bytes both parses read
out["deepRead"] = mirror_phase(nobody=dead, other=other)
exchange(pm15, host_b, [other], bus_id="bus-b2")   # B's next exchange: the write replaces it, carrying nothing
out["deepWritten"] = mirror_phase(nobody=dead, other=other)
bus_file.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
    host_a: {"kind": "peer", "sids": [carried], "heard": True, "expired": "yes", "linkDown": False, "linkUp": True,
             "answered": 1, "reachable": True, "vouchesAbsence": True, "seenAt": 1},     # non-bool flags
    alias: {"kind": "peer", "sids": [far_sid], "heard": True, "expired": False, "linkDown": False, "linkUp": True,
            "answered": True, "reachable": True, "vouchesAbsence": True, "seenAt": 1, "busId": ["bus-far"]},   # an unhashable busId
    "legacy:list": {"kind": "legacy", "sids": [["x"], later], "heard": False, "expired": False, "answered": False,
                    "seenAt": 0}}}) + "\n")        # an unhashable sid beside a live session's
out["foreignRowsRead"] = mirror_phase(carried=carried, farSid=far_sid, later=later, nobody=dead)
exchange(pm15, host_b, [other], bus_id="bus-b2")   # B's next exchange: the write carries the three rows
out["foreignRowsWritten"] = mirror_phase(carried=carried, farSid=far_sid, later=later, nobody=dead, other=other)
vouching = {"kind": "peer", "sids": [carried], "heard": True, "expired": False, "linkDown": False, "linkUp": True,
            "answered": True, "reachable": True, "vouchesAbsence": True, "seenAt": 1}   # a row that names `carried` and vouches
bus_file.write_text(json.dumps({"v": 1, "busStarted": 1, "writtenAt": 1, "hosts": {host_a: vouching}}) + "\n")
out["v1Read"] = mirror_phase(carried=carried, nobody=dead)
bus_file.write_text(json.dumps({"busStarted": 1, "writtenAt": 1, "hosts": {host_a: vouching}}) + "\n")
out["noVRead"] = mirror_phase(carried=carried, nobody=dead)
exchange(pm15, host_b, [other], bus_id="bus-b2")   # the writer over the document with no version: its roster carried, v 2 stamped
out["versionWritten"] = mirror_phase(carried=carried, nobody=dead)
out["versionWritten"]["v"] = json.loads(bus_file.read_text()).get("v")
# ONE BAD BYTE (the reviewer's verifier at the twentieth commit; the reviewer's ruling of 14:57Z, clause 1, the twenty-second
# commit): A heard with its link up beside B; one byte inside the sid B names made a stray byte in the writer's own document; a
# fifteenth restart; B heard first. The previous-read decodes with replacement for its parse and drops the one sid: A's row is
# carried, so A's session is held by A's last word while B vouches, and the bus log says once which file and how many
notify(pm15, host_a, True)
exchange(pm15, host_a, [carried])
out["unreadBefore"] = mirror_phase(carried=carried, other=other)
data = bus_file.read_bytes()
bus_file.write_bytes(data.replace(other.encode(), other[:-1].encode() + b"\xff"))
pm16, out["restartMemory15"] = restarted("romp_postal_oneroot_restarted_fifteenth", pm15)
pm16.KERNEL_BASE = "http://127.0.0.1:9"           # no listing fetch reaches anything
err = io.StringIO()
with contextlib.redirect_stderr(err):
    notify(pm16, host_b, True)                     # B's link up (the notify's write is the first to read the file), then B heard
    exchange(pm16, host_b, [other], bus_id="bus-b2")
out["unreadWritten"] = mirror_phase(carried=carried, other=other, nobody=dead)
out["unreadWritten"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
notify(pm16, host_a, True)
exchange(pm16, host_a, [carried])                  # A heard in the new process: its own row names its session
out["unreadAHeard"] = mirror_phase(carried=carried, other=other, nobody=dead)
# THE BYTE-ORDER MARK (the reviewer's ruling of 14:57Z, clause 1): the writer's own document behind a byte-order mark, read by the
# reader, then a sixteenth restart, B heard first: the file carried
bus_file.write_bytes(b"\xef\xbb\xbf" + bus_file.read_bytes())
out["bomRead"] = mirror_phase(carried=carried, other=other, nobody=dead)
pm17, out["restartMemory16"] = restarted("romp_postal_oneroot_restarted_sixteenth", pm16)
pm17.KERNEL_BASE = "http://127.0.0.1:9"           # no listing fetch reaches anything
err = io.StringIO()
with contextlib.redirect_stderr(err):
    notify(pm17, host_b, True)
    exchange(pm17, host_b, [other], bus_id="bus-b2")
out["bomWritten"] = mirror_phase(carried=carried, other=other, nobody=dead)
out["bomWritten"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
# THE LOST CARRY (the reviewer's ruling of 14:57Z, clause 2): A heard beside B; the writer's own document made not JSON (a stray
# brace); a seventeenth restart whose seed reads the kernel's list, both links up (the REAL seed, its transport stubbed), and whose
# seed writes read the file and mark the mirror; B heard first, A linked and not heard. An eighteenth restart whose seed fails
# (nothing answers), B and A notified one at a time and heard. A nineteenth restart whose seed reads the list; B heard; A heard,
# the last linked host heard since the mark: the event that clears it
def seed(bus, links):                              # the kernel's tunnel list read at the bus's start, every link up, and one
    body = json.dumps({"tunnels": [{"host": h, "busPort": 50002, "status": "up"} for h in links],   # remembered unattached
                       "known": [{"host": remembered, "trust": "trusted"}]}).encode()               # host: an origin-only row, no link
    class Answer:
        def read(self):
            return body
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return False
    real = bus.urllib.request.urlopen
    bus.urllib.request.urlopen = lambda req, timeout=None: Answer()
    try:
        bus._seed_peers_from_kernel()
    finally:
        bus.urllib.request.urlopen = real
    return bus._PEERS_SEEDED[0]
notify(pm17, host_a, True)
exchange(pm17, host_a, [carried])
out["lostBefore"] = mirror_phase(carried=carried, other=other, nobody=dead)
bus_file.write_text(bus_file.read_text().replace('"sids"', '"sids"}', 1))
pm18, out["restartMemory17"] = restarted("romp_postal_oneroot_restarted_seventeenth", pm17)
pm18.KERNEL_BASE = "http://127.0.0.1:9"
out["lostFloor"] = int(time.time())
err = io.StringIO()
with contextlib.redirect_stderr(err):
    out["lostSeeded"] = seed(pm18, [host_a, host_b])   # the seed's own writes read the file: the mark
    exchange(pm18, host_b, [other], bus_id="bus-b2")   # B heard first; A linked and not heard
out["lostCeiling"] = int(time.time())
out["lostWritten"] = mirror_phase(carried=carried, other=other, nobody=dead)
out["lostWritten"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
pm19, out["restartMemory18"] = restarted("romp_postal_oneroot_restarted_eighteenth", pm18)
pm19.KERNEL_BASE = "http://127.0.0.1:9"           # nothing answers there: the real seed fails
pm19._seed_peers_from_kernel()
out["lostUnseeded"] = pm19._PEERS_SEEDED[0]
notify(pm19, host_b, True)                         # the kernel's re-notify, one host at a time, each heard
exchange(pm19, host_b, [other], bus_id="bus-b2")
notify(pm19, host_a, True)
exchange(pm19, host_a, [carried])
out["lostNoSeed"] = mirror_phase(carried=carried, other=other, nobody=dead)
pm20, out["restartMemory19"] = restarted("romp_postal_oneroot_restarted_nineteenth", pm19)
pm20.KERNEL_BASE = "http://127.0.0.1:9"
out["lostReseeded"] = seed(pm20, [host_a, host_b])
exchange(pm20, host_b, [other], bus_id="bus-b2")
out["lostOneHeard"] = mirror_phase(carried=carried, other=other, nobody=dead)
err = io.StringIO()
with contextlib.redirect_stderr(err):
    exchange(pm20, host_a, [carried])              # A heard: the last linked host heard since the mark
out["lostCleared"] = mirror_phase(carried=carried, other=other, nobody=dead)
out["lostCleared"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
out["lostRemembered"] = pm20.PEERS.get(remembered)
# THE CLEARING'S BOUND BESIDE A SECOND LINK (the reviewer's verifier at the twenty-second commit, by execution; the reviewer's
# ruling of 15:45Z: after the clear a session on a host that no linked host hears now is outside every source, as on a first
# start; postal_service.py _remote_sids_lost_cleared): B, a linked hub beside A, gossips a session on the spoke, a far host never
# linked here. The file intact: a twentieth restart, seeded; A heard; B heard after its own restart (a new bus id), gossiping
# nothing about the spoke: the carried via row names the session, cannot-determine. B names it again; the file made not JSON; a
# twenty-first restart, seeded; A heard; B heard after another restart of its own, gossiping nothing about the spoke: the mark
# clears, and the session answers rule 5 (A and B both vouch: the contrast with the intact file, not the ruled road)
def b_gossips(bus, bus_id, spoke_sids):            # B's exchange landing through the real fold: its own session and its word about the spoke
    bus.peer_exchange_apply(host_b, {}, {"epoch": 1, "holds": [], "busId": bus_id, "presenceAnswered": True,
                                         "presence": [{"id": other, "name": "api"}]
                                         + [{"id": s, "name": "api", "via": spoke, "viaBus": "bus-spoke", "viaAnswered": True}
                                            for s in spoke_sids]})
b_gossips(pm20, "bus-b2", [far_lost])
out["boundGossiped"] = mirror_phase(farLost=far_lost, other=other, carried=carried)
pm21, out["restartMemory20"] = restarted("romp_postal_oneroot_restarted_twentieth", pm20)
pm21.KERNEL_BASE = "http://127.0.0.1:9"
out["boundIntactSeeded"] = seed(pm21, [host_a, host_b])
exchange(pm21, host_a, [carried])
b_gossips(pm21, "bus-b3", [])                      # B restarted since: heard, gossiping nothing about the spoke
out["boundIntact"] = mirror_phase(farLost=far_lost, other=other, carried=carried, nobody=dead)
b_gossips(pm21, "bus-b3", [far_lost])              # B has heard the spoke again: its word names the session
out["boundRegossiped"] = mirror_phase(farLost=far_lost, other=other, carried=carried)
bus_file.write_text(bus_file.read_text().replace('"sids"', '"sids"}', 1))
pm22, out["restartMemory21"] = restarted("romp_postal_oneroot_restarted_twenty_first", pm21)
pm22.KERNEL_BASE = "http://127.0.0.1:9"
err = io.StringIO()
with contextlib.redirect_stderr(err):
    out["boundLostSeeded"] = seed(pm22, [host_a, host_b])
    out["boundLostMark"] = mirror_mark()           # the seed's own writes read the file: the mark
    exchange(pm22, host_a, [carried])
    b_gossips(pm22, "bus-b4", [])                  # B restarted again: heard, gossiping nothing about the spoke
out["boundLost"] = mirror_phase(farLost=far_lost, other=other, carried=carried, nobody=dead)
out["boundLost"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
# A MARK AT SECOND 0 (the reviewer's verifier at the twenty-second commit, by execution): the writer's own document with A's row
# removed, as a lost carry leaves it, under a hand-written mark at second 0, which the carry and the reader accept; a
# twenty-second restart, seeded; a drift note filed for A (no exchange landed, no seenAt) and B heard: the mark stands; A heard:
# cleared
doc = json.loads(bus_file.read_text())
doc["hosts"].pop(host_a, None)
doc["carryLost"] = {"cause": "hand-written", "at": 0}
bus_file.write_text(json.dumps(doc) + "\n")
pm23, out["restartMemory22"] = restarted("romp_postal_oneroot_restarted_twenty_second", pm22)
pm23.KERNEL_BASE = "http://127.0.0.1:9"
out["zeroSeeded"] = seed(pm23, [host_a, host_b])
pm23.PEER_STATE[host_a] = {"drift": "proto"}       # _peer_exchange_once's note of a 409: no exchange landed, no seenAt
exchange(pm23, host_b, [other], bus_id="bus-b5")
out["zeroBHeard"] = mirror_phase(carried=carried, other=other, nobody=dead)
exchange(pm23, host_a, [carried])
out["zeroAHeard"] = mirror_phase(carried=carried, other=other, nobody=dead)
# AS ON A FIRST START, THE RULED ROAD (the reviewer's ruling of 15:45Z, clause 5, its named witness): a twenty-third restart seeded
# with B ALONE, the only link (A is no longer linked); B, a hub, gossips a session on the spoke; the file made not JSON; a
# twenty-fourth restart seeded with B alone, whose own writes mark the mirror; B heard after its own restart, no longer hearing
# the spoke: the mark clears, and the spoke's session, outside every source, answers rule 5 while B, the one row, vouches for
# absence. Then a twenty-fifth restart over NO file, a first start seeded with B alone, B heard the same way: the same answer
def link_hosts(bus):                               # the hosts PEERS holds as links (a dialable row: a port)
    return sorted(h for h, p in bus.PEERS.items() if p.get("port"))
pm24, out["restartMemory23"] = restarted("romp_postal_oneroot_restarted_twenty_third", pm23)
pm24.KERNEL_BASE = "http://127.0.0.1:9"
out["oneLinkSeeded"] = seed(pm24, [host_b])
b_gossips(pm24, "bus-b6", [far_lost])
out["oneLinkGossiped"] = mirror_phase(farLost=far_lost, other=other, nobody=dead)
bus_file.write_text(bus_file.read_text().replace('"sids"', '"sids"}', 1))
pm25, out["restartMemory24"] = restarted("romp_postal_oneroot_restarted_twenty_fourth", pm24)
pm25.KERNEL_BASE = "http://127.0.0.1:9"
err = io.StringIO()
with contextlib.redirect_stderr(err):
    out["oneLinkLostSeeded"] = seed(pm25, [host_b])
    out["oneLinkMark"] = mirror_mark()             # the seed's own writes read the file: the mark
    out["oneLinkLinks"] = link_hosts(pm25)
    b_gossips(pm25, "bus-b7", [])                  # B restarted since: heard, no longer hearing the spoke
out["oneLinkCleared"] = mirror_phase(farLost=far_lost, other=other, nobody=dead)
out["oneLinkCleared"]["busLog"] = [ln for ln in err.getvalue().splitlines() if "remote-sids" in ln]
bus_file.unlink()                                  # no previous file: the next process is a first start
pm26, out["restartMemory25"] = restarted("romp_postal_oneroot_restarted_twenty_fifth", pm25)
pm26.KERNEL_BASE = "http://127.0.0.1:9"
out["firstStartSeeded"] = seed(pm26, [host_b])
out["firstStartLinks"] = link_hosts(pm26)
out["firstStartMark"] = mirror_mark()              # the seed's own writes over no file: nothing lost, no mark
b_gossips(pm26, "bus-b8", [])                      # B heard, hearing nothing on the spoke
out["firstStart"] = mirror_phase(farLost=far_lost, other=other, nobody=dead)
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
# BOTH CLASSES, ONE PIN (round 3 of fork PR #897, the reviewer's ruling of 17:47Z, the twenty-fifth commit): json.loads, the json
# module's attribute both modules call, stubbed to raise each class in turn on the nested document; the writer's previous-read
# and the reader over it, each outcome recorded, a raise out of either by its type
def stubbed_loads(cls, real):
    def loads(s, *args, **kwargs):
        text = s.decode("utf-8-sig") if isinstance(s, (bytes, bytearray)) else s
        if text.startswith("[" * 1000):
            raise cls("stubbed: the parse of the nested document raises %s" % cls.__name__)
        return real(s, *args, **kwargs)
    return loads
out["catchBoth"] = {}
for both_cls in (ValueError, RecursionError):
    bus_file.write_text("[" * 100000 + "\n")
    both_real = json.loads
    json.loads = stubbed_loads(both_cls, both_real)
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            try:
                both_rows, both_mark = pm26._remote_sids_previous(bus_file, now)
                both_previous = {"hosts": both_rows, "mark": both_mark}
            except Exception as e:
                both_previous = ["raised", type(e).__name__, str(e)[:80]]
            both_verdict = caught(dead)
    finally:
        json.loads = both_real
    out["catchBoth"][both_cls.__name__] = {"previous": both_previous, "verdict": both_verdict,
                                           "log": [ln for ln in err.getvalue().splitlines() if ln.startswith("romp-judge:")]}
print(json.dumps(out))
""", HERE, BIN, REMOTE, REMOTE2, DEAD, HOST, HOST2, CARRIED, OTHER, ALIAS, DECLARED, FARSID, HUB, GOSSIPED, LATER, COLLIDED,
                              ENDED, DECL_NAMED, SPOKE_KEPT, SPOKE_GONE, HUB_DECLARED, SPOKE, SPOKE_DECLARED, HUB2, SPOKE_NEW, BLINKED,
                              HUB_NAMED, BLINK_BEAT, LEGACY_NAMED, VIA_NAMED, FAR_LOST, REMEMBERED],
                             capture_output=True, text=True, env=full,
                             cwd=str(home), timeout=120)
        assert out.returncode == 0, "%s child failed: %s" % (shape, out.stderr[-2000:])
        got = json.loads(out.stdout.strip().splitlines()[-1])
        got["root"] = str(root)
        return got

    @classmethod
    def _roads_over_one_root(cls, shape):
        """The roads (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' finding, section A, the
        twenty-ninth commit): one fresh interpreter under the root shape given, OUR bus over the root the test prepared and
        every other machine's bus (B, C, a hub, a far host F) over a state root of its own, each a fresh module object
        exchanging with the others through the real request builder (build_exchange_request), the real handler
        (peer_exchange_handle) and the real fold (peer_exchange_apply), the kernel's link notify through the real handler
        (peer_update), each machine's kernel listing answering through the ROMP_SESSIONS_FILE seam or not answering (the
        seam unset, the kernel route pointed at a loopback port nothing listens on), OUR bus writing the mirror and the
        real judge reading it. Each road starts over an emptied bus directory and a fresh module object for our bus, as a
        first start. The roads are the refuters' probe scenarios, ported (the checkpoints' extra5 and refute2 probes),
        and the witnesses of the costs and residuals the writer's docstring names; each step records the verdicts for
        the named sids and our mirror's rows. The source sits as a literal in the argv slot after "-c", as the first
        child's does, for the hosts-on census."""
        td = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, td, ignore_errors=True)
        home = Path(td) / "home"
        home.mkdir()
        others = Path(td) / "others"
        others.mkdir()
        if shape == "XDG_STATE_HOME":
            env = {"XDG_STATE_HOME": str(Path(td) / "xdg")}
            root = Path(td) / "xdg" / "romp"
        else:
            env = {"ROMP_STATE_DIR": str(Path(td) / "state")}
            root = Path(td) / "state"
        root.mkdir(parents=True)
        (root / "session-hosts").write_text("off\n")
        full = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "TMPDIR": str(home),
                "ROMP_KERNEL_NO_OPEN": "1", "PYTHONDONTWRITEBYTECODE": "1", **env}
        out = subprocess.run([sys.executable, "-c", r"""
import json, os, shutil, sys, time
from pathlib import Path
tests_dir, bin_dir, others_root = sys.argv[1:4]
S = json.loads(sys.argv[4])
US, B, C, HUB, F, HUB2, HUB_DECL, G, HUB_DECL2 = sys.argv[5:14]
sys.path.insert(0, tests_dir)
from romp_load import load_source
jd = load_source("romp_judge_roads", os.path.join(bin_dir, "romp-judge"))
now = time.time()
out = {"judgeState": str(jd.STATE), "hostsOff": (jd.STATE / "session-hosts").read_text().strip(),
       "discovered": len(jd.discover(now)) + len(jd.discover(now, window=now)), "roads": {}}
LISTINGS = {}                                      # a machine's label -> the sessions its kernel listing answers with, or None
SEQ = [0]
def load_bus(label, root=None):                    # a bus process: a fresh module object, over `root` or the root the environment names
    SEQ[0] += 1
    saved = os.environ.get("ROMP_STATE_DIR")
    if root is not None:
        os.environ["ROMP_STATE_DIR"] = str(root)
    try:
        bus = load_source("romp_postal_roads_%d" % SEQ[0], os.path.join(bin_dir, "romp-postal-service"))
    finally:
        if root is not None:
            if saved is None:
                os.environ.pop("ROMP_STATE_DIR", None)
            else:
                os.environ["ROMP_STATE_DIR"] = saved
    bus._peer_threads_reconcile = lambda host: None   # the notify's dialer bookkeeping is not under test
    bus.KERNEL_BASE = "http://127.0.0.1:9"        # with the seam unset the listing fetch goes here, where nothing listens
    bus.STATE.mkdir(parents=True, exist_ok=True)
    bus.road_label = label
    LISTINGS.setdefault(label, [])
    return bus
def fresh_us(label="us"):                          # OUR bus as a first start: the bus directory emptied, a fresh module object
    LISTINGS.clear()
    shutil.rmtree(jd.STATE / "postal", ignore_errors=True)
    bus = load_bus(label)
    out.setdefault("busState", str(bus.STATE))
    return bus
def other(road, label):                            # another machine's bus over a state root of its own, session-hosts off in it
    root = Path(others_root) / road / label
    root.mkdir(parents=True)
    (root / "session-hosts").write_text("off\n")
    return load_bus(label, root)
class As:                                          # run a call as the machine `bus`: its listing answering through the seam, or not
    def __init__(self, bus):
        self.bus = bus
    def __enter__(self):
        sids = LISTINGS.get(self.bus.road_label)
        if sids is None:
            os.environ.pop("ROMP_SESSIONS_FILE", None)
        else:
            f = Path(others_root) / ("listing-%s.json" % self.bus.road_label)
            f.write_text(json.dumps([{"id": s, "name": "s" + s[-3:]} for s in sids]))
            os.environ["ROMP_SESSIONS_FILE"] = str(f)
    def __exit__(self, *exc):
        os.environ.pop("ROMP_SESSIONS_FILE", None)
def dial(src, src_name, dst, dst_name, strip_answered=False):   # src's real builder, dst's real handler, src's real fold
    with As(src):
        req = src.build_exchange_request(dst_name, wait=False)
    req["host"] = src_name
    if strip_answered:                             # a payload lacking the field: an older peer's
        req.pop("presenceAnswered", None)
    with As(dst):
        resp, status = dst.peer_exchange_handle(req)
    if status == 200:
        if strip_answered:
            resp.pop("presenceAnswered", None)
        with As(src):
            src.peer_exchange_apply(dst_name, req, resp)
    return [status, req.get("presenceAnswered", "absent"), sorted(a.get("id") for a in req.get("presence") or [] if not a.get("via"))]
def notify(bus, host, up):                         # the kernel's /peer notify, through the real handler, which writes the mirror
    with As(bus):
        return list(bus.peer_update({"host": host, "port": 50002, "up": up}))
def rows(bus):                                     # our mirror's rows: [heard, linkDown, linkUp, answered, reachable, vouchesAbsence, sids]
    p = bus.STATE / "remote-sids"
    if not p.exists():
        return None
    try:
        return {k: [r["heard"], r["linkDown"], r["linkUp"], r["answered"], r["reachable"], r["vouchesAbsence"], r["sids"]]
                for k, r in json.loads(p.read_text())["hosts"].items()}
    except (ValueError, KeyError, TypeError):
        return p.read_text()[:200]
def step(road, name, bus, **sids):
    got = {k: list(jd._presumed_closed_verdict(v, time.time())) for k, v in sids.items()}
    got["rows"] = rows(bus)
    out["roads"].setdefault(road, {})[name] = got
# X_hub_cached_self: the hub's own kernel blinks while its word about B, answered, vouches; a session started on the hub
# during its blink is in no roster, and the hub's exchange serves its cache
road = "hubCachedSelf"
us = fresh_us(); b, hub = other(road, "b"), other(road, "hub")
LISTINGS["b"], LISTINGS["hub"] = [S["other"]], [S["hubsid"]]
notify(us, HUB, True)
dial(b, B, hub, HUB)                               # B's exchange with the hub, answered: the hub learns B's roster
dial(hub, HUB, us, US)                             # the hub dials us, answered, gossiping B's roster
LISTINGS["hub"] = None                             # the hub's kernel blinks; a session (new) starts on the hub meanwhile
out["roads"][road] = {"cachedDial": dial(hub, HUB, us, US)}
step(road, "cached", us, newOnHub=S["new"], hubsid=S["hubsid"], other=S["other"], nobody=S["nobody"])
LISTINGS["hub"] = [S["hubsid"], S["new"]]          # the hub's listing answers again, naming the session: the release
dial(hub, HUB, us, US)
step(road, "answers", us, newOnHub=S["new"], nobody=S["nobody"])
# X_cached_no_hub: B's exchange serves a cache while a session started on B during the blink; no hub names it; C, answered
# and its link up, vouches; B's kernel still not answering at B's next exchange; then it answers
road = "cachedNoHub"
us = fresh_us(); b, c = other(road, "b"), other(road, "c")
LISTINGS["b"], LISTINGS["c"] = [S["other"]], [S["csid"]]
notify(us, B, True); notify(us, C, True)
dial(b, B, us, US); dial(c, C, us, US)
LISTINGS["b"] = None
out["roads"][road] = {"cachedDial": dial(b, B, us, US)}
step(road, "cached", us, blinked=S["blinked"], other=S["other"], nobody=S["nobody"])
dial(b, B, us, US); dial(c, C, us, US)             # B heard over its cache again, C again
step(road, "stillCached", us, blinked=S["blinked"], nobody=S["nobody"])
LISTINGS["b"] = [S["other"], S["blinked"]]         # B's listing answers, naming the session: the release
dial(b, B, us, US)
step(road, "answers", us, blinked=S["blinked"], nobody=S["nobody"])
# X_far_cached_via_hub: a far host F, not held here, blinks; a session starts on F; F's exchange with the hub serves the
# cache; the hub relays F's word to us, its own roster answered; then F answers the hub, and the hub dials us again
road = "farCachedViaHub"
us = fresh_us(); f, hub = other(road, "f"), other(road, "hub")
LISTINGS["f"], LISTINGS["hub"] = [S["other"]], [S["hubsid"]]
notify(us, HUB, True)
dial(f, F, hub, HUB); dial(hub, HUB, us, US)
step(road, "farAnswered", us, other=S["other"], nobody=S["nobody"])
LISTINGS["f"] = None
dial(f, F, hub, HUB); dial(hub, HUB, us, US)
step(road, "farCached", us, newOnFar=S["new"], other=S["other"], nobody=S["nobody"])
LISTINGS["f"] = [S["other"], S["new"]]
dial(f, F, hub, HUB)                               # F's answering exchange with the hub: the first half of the release
step(road, "farAnswersHub", us, newOnFar=S["new"], nobody=S["nobody"])
dial(hub, HUB, us, US)                             # the hub's next exchange here: the second half
step(road, "released", us, newOnFar=S["new"], nobody=S["nobody"])
# X_mail_rides_cached: a session starts on the hub during its blink and mails a session on OUR host; the hub's exchange
# carries the relay beside presenceAnswered False; our handler records the cache, writes the mirror and lands the relay
road = "mailRidesCached"
us = fresh_us(); b, hub = other(road, "b"), other(road, "hub")
LISTINGS["b"], LISTINGS["hub"], LISTINGS["us"] = [S["other"]], [S["hubsid"]], [S["web"]]
notify(us, HUB, True)
with As(hub):
    hub.peer_update({"host": US, "port": 50001, "up": True})
dial(b, B, hub, HUB)                               # the hub hears B, answered
dial(us, US, hub, HUB)                             # we dial the hub: it learns our roster, we fold the hub
LISTINGS["hub"] = None                             # the hub's kernel listing stops answering; the new session starts there
got = {}
with As(hub):
    res = hub.resolve_recipient("s" + S["web"][-3:], S["new"])
    got["resolve"] = [res.get("kind"), res.get("host"), (res.get("agent") or {}).get("id")]
    if res.get("kind") == "relay":
        got["parked"] = hub.outbox_put(res["host"], {"mid": "px-road1", "to": "s" + S["web"][-3:], "toId": S["web"],
                                                     "frm": "s" + S["new"][-3:], "frm_id": S["new"],
                                                     "body": "please take this", "kind": "delegate", "t": int(time.time())})
with As(hub):
    req = hub.build_exchange_request(US, wait=False)
req["host"] = HUB
got["reqAnswered"] = req.get("presenceAnswered", "absent")
got["reqRelays"] = [[m.get("frm_id"), m.get("toId")] for m in req.get("relays") or []]
with As(us):
    resp, got["status"] = us.peer_exchange_handle(req)
got["acks"] = resp.get("acks") if isinstance(resp, dict) else None
out["roads"][road] = got
step(road, "relayLanded", us, newOnHub=S["new"], other=S["other"], hubsid=S["hubsid"], nobody=S["nobody"])
# B_cached: B answered, then its kernel blinks (a session starts on B), then it answers again: the release
road = "bCached"
us = fresh_us(); b = other(road, "b")
LISTINGS["b"] = [S["other"]]
notify(us, B, True)
dial(b, B, us, US)
step(road, "answered", us, other=S["other"], nobody=S["nobody"])
LISTINGS["b"] = None
dial(b, B, us, US)
step(road, "blinkRequest", us, blinked=S["blinked"], other=S["other"], nobody=S["nobody"])
dial(us, US, b, B)                                 # our dial to B: B's response builder, still blinking
step(road, "blinkResponse", us, blinked=S["blinked"], nobody=S["nobody"])
LISTINGS["b"] = [S["other"], S["blinked"]]
dial(b, B, us, US)
step(road, "answersAgain", us, blinked=S["blinked"], nobody=S["nobody"])
# B_older_peer: B's payloads lack the field (an older peer), then B's next request carries it
road = "bOlderPeer"
us = fresh_us(); b = other(road, "b")
LISTINGS["b"] = [S["other"]]
notify(us, B, True)
dial(b, B, us, US, strip_answered=True)
step(road, "olderRequest", us, other=S["other"], nobody=S["nobody"])
dial(us, US, b, B, strip_answered=True)
step(road, "olderResponse", us, other=S["other"], nobody=S["nobody"])
dial(b, B, us, US)
step(road, "newerRequest", us, other=S["other"], nobody=S["nobody"])
# A_down_then_carried (the control): B held down while the hub names a session started on B; then our bus restarts and the
# hub is heard before B
road = "downThenCarried"
us = fresh_us(); b, hub = other(road, "b"), other(road, "hub")
LISTINGS["b"], LISTINGS["hub"] = [S["other"]], [S["hubsid"]]
notify(us, B, True); notify(us, HUB, True)
dial(b, B, us, US); dial(b, B, hub, HUB); dial(hub, HUB, us, US)
step(road, "bothUp", us, other=S["other"], nobody=S["nobody"], goss=S["goss"])
notify(us, B, False)
LISTINGS["b"] = [S["other"], S["goss"]]
dial(b, B, hub, HUB); dial(hub, HUB, us, US)
step(road, "bDownHubNames", us, goss=S["goss"], nobody=S["nobody"])
notify(us, HUB, False)
step(road, "bDownHubDown", us, goss=S["goss"], nobody=S["nobody"])
notify(us, HUB, True)
dial(hub, HUB, us, US)
step(road, "bDownHubBack", us, goss=S["goss"])
notify(us, B, True)
dial(b, B, us, US)
step(road, "bBack", us, goss=S["goss"], nobody=S["nobody"])
dial(hub, HUB, us, US)
step(road, "bBackHubAgain", us, goss=S["goss"])
us = load_bus("us2")                               # our bus restarts over the same root; the kernel seeds both links up
notify(us, B, True); notify(us, HUB, True)
LISTINGS["b"] = [S["other"], S["goss"], S["later"]]
dial(b, B, hub, HUB); dial(hub, HUB, us, US)
step(road, "carriedHubFirst", us, later=S["later"], goss=S["goss"], nobody=S["nobody"])
notify(us, HUB, False)
step(road, "carriedHubDown", us, later=S["later"], nobody=S["nobody"])
notify(us, HUB, True)
dial(hub, HUB, us, US); dial(b, B, us, US)
step(road, "carriedBHeard", us, later=S["later"], nobody=S["nobody"])
# X_down_no_hub (the control): a session starts on B while our kernel holds B down; C vouches
road = "downNoHub"
us = fresh_us(); b, c = other(road, "b"), other(road, "c")
LISTINGS["b"], LISTINGS["c"] = [S["other"]], [S["csid"]]
notify(us, B, True); notify(us, C, True)
dial(b, B, us, US); dial(c, C, us, US)
notify(us, B, False)
step(road, "downBCVouches", us, blinked=S["blinked"], other=S["other"])
# X_cached_alone (the control): B's exchange serves a cache, and no other host vouches
road = "cachedAlone"
us = fresh_us(); b = other(road, "b")
LISTINGS["b"] = [S["other"]]
notify(us, B, True)
dial(b, B, us, US)
LISTINGS["b"] = None
dial(b, B, us, US)
step(road, "cachedBAlone", us, blinked=S["blinked"])
# N_far_empty_cache_via_hub (residual 3a): a far host F behind a heard hub, its kernel not answering since its bus started
# (no twin: an empty cache), so its exchange with the hub carries presenceAnswered False and no session row, and the hub
# gossips no row for F; a session started on F meanwhile. Then the other shape of the sub-case: F's last answered listing
# named nobody, and F blinks
road = "farEmptyCacheViaHub"
us = fresh_us(); f, hub = other(road, "f"), other(road, "hub")
LISTINGS["f"], LISTINGS["hub"] = None, [S["hubsid"]]
notify(us, HUB, True)
out["roads"][road] = {"farDial": dial(f, F, hub, HUB)}
dial(hub, HUB, us, US)
step(road, "emptyCache", us, newOnFar=S["new"], hubsid=S["hubsid"], nobody=S["nobody"])
LISTINGS["f"] = []
out["roads"][road]["farAnsweredDial"] = dial(f, F, hub, HUB)
LISTINGS["f"] = None
out["roads"][road]["farBlinkDial"] = dial(f, F, hub, HUB)
dial(hub, HUB, us, US)
step(road, "answeredNobody", us, newOnFar=S["new"], nobody=S["nobody"])
# X_far_cached_then_gone (residual 3b): F's last exchange with the hub served a cache, then the hub's kernel holds F down for
# good; the hub keeps gossiping F's last word with viaAnswered False
road = "farCachedThenGone"
us = fresh_us(); f, hub = other(road, "f"), other(road, "hub")
LISTINGS["f"], LISTINGS["hub"] = [S["other"]], [S["hubsid"]]
notify(us, HUB, True)
with As(hub):
    hub.peer_update({"host": F, "port": 50003, "up": True})
dial(f, F, hub, HUB)
LISTINGS["f"] = None
dial(f, F, hub, HUB)
with As(hub):
    hub.peer_update({"host": F, "port": 50003, "up": False})
dial(hub, HUB, us, US)
step(road, "farGoneAtHub", us, nobody=S["nobody"], other=S["other"])
dial(hub, HUB, us, US)
step(road, "farGoneAtHub2", us, nobody=S["nobody"], other=S["other"])
# cost (a): a peer lacking the field (an older bus) beside a vouching host, heard here; and an older far host gossiped by a
# heard, newer hub
road = "olderBesideVouching"
us = fresh_us(); b, c = other(road, "b"), other(road, "c")
LISTINGS["b"], LISTINGS["c"] = [S["other"]], [S["csid"]]
notify(us, B, True); notify(us, C, True)
dial(b, B, us, US, strip_answered=True)
dial(c, C, us, US)
step(road, "olderBesideC", us, other=S["other"], nobody=S["nobody"])
road = "olderFarViaHub"
us = fresh_us(); f, hub = other(road, "f"), other(road, "hub")
LISTINGS["f"], LISTINGS["hub"] = [S["other"]], [S["hubsid"]]
notify(us, HUB, True)
dial(f, F, hub, HUB, strip_answered=True)
dial(hub, HUB, us, US)
step(road, "olderFarGossiped", us, other=S["other"], nobody=S["nobody"])
# cost (c): a host the kernel never notified (no link state), its kernel not answering since its bus started, dials in once
# over its cache and falls silent beside C, linked and answered; C's later exchanges; then our bus restarts and C is heard
road = "silentNoLink"
us = fresh_us(); b, c = other(road, "b"), other(road, "c")
LISTINGS["b"], LISTINGS["c"] = None, [S["csid"]]
notify(us, C, True)
dial(c, C, us, US)
out["roads"][road] = {"bDial": dial(b, B, us, US)}
step(road, "dialedOnce", us, nobody=S["nobody"], csid=S["csid"])
dial(c, C, us, US)
step(road, "later1", us, nobody=S["nobody"])
dial(c, C, us, US)
step(road, "later2", us, nobody=S["nobody"])
us = load_bus("us2")                               # our bus restarts; the kernel re-notifies C, and C is heard
notify(us, C, True)
dial(c, C, us, US)
step(road, "restartedCHeard", us, nobody=S["nobody"], csid=S["csid"])
# THE HELD-DOWN ROADS (round 4 of fork PR #897, the thirtieth commit; the reviewer's verifier at the twenty-ninth, by
# execution): a host whose exchange HERE served a cache carrying its session's mail, then held down by our kernel (or held
# down first and dialing us over its cache); the twenty-ninth commit's arm, keyed on reachable, let go at the down notify
def park(src, frm, mid):                           # src's session frm mails OUR session web: src's real resolve and outbox
    with As(src):
        res = src.resolve_recipient("s" + S["web"][-3:], frm)
        got = {"resolve": [res.get("kind"), res.get("host"), (res.get("agent") or {}).get("id")]}
        if res.get("kind") == "relay":
            got["parked"] = src.outbox_put(res["host"], {"mid": mid, "to": "s" + S["web"][-3:], "toId": S["web"],
                                                         "frm": "s" + frm[-3:], "frm_id": frm, "body": "please take this",
                                                         "kind": "delegate", "t": int(time.time())})
    return got
def mail_dial(src, src_name, dst, dst_name):       # src dials dst carrying its parked relays: what the request carried, the acks
    with As(src):
        req = src.build_exchange_request(dst_name, wait=False)
    req["host"] = src_name
    with As(dst):
        resp, status = dst.peer_exchange_handle(req)
    if status == 200:
        with As(src):
            src.peer_exchange_apply(dst_name, req, resp)
    return {"status": status, "reqAnswered": req.get("presenceAnswered", "absent"),
            "reqRelays": [m.get("frm_id") for m in req.get("relays") or []], "acks": resp.get("acks") if isinstance(resp, dict) else None}
def mail_response(dst, dst_name, src, src_name):   # dst (ours) dials src; src's RESPONSE carries its parked relays; dst's real fold
    with As(dst):                                  # lands them (a spy on _relay_in records each landing) and writes the mirror
        req = dst.build_exchange_request(src_name, wait=False)
    req["host"] = dst_name
    with As(src):
        resp, status = src.peer_exchange_handle(req)
    landed = []
    if status == 200:
        real = dst._relay_in
        def spy(host, m, **kw):
            v = real(host, m, **kw)
            landed.append([m.get("frm_id"), v[0]])
            return v
        dst._relay_in = spy
        try:
            with As(dst):
                dst.peer_exchange_apply(src_name, req, resp)
        finally:
            dst._relay_in = real
    return {"status": status, "respAnswered": resp.get("presenceAnswered", "absent"),
            "respRelays": [m.get("frm_id") for m in resp.get("relays") or []], "landed": landed}
def b_and_c_answered(road):                        # B and C linked up and answered, B knowing us as a link (so it relays to us)
    us = fresh_us(); b, c = other(road, "b"), other(road, "c")
    LISTINGS["b"], LISTINGS["c"], LISTINGS["us"] = [S["other"]], [S["csid"]], [S["web"]]
    notify(us, B, True); notify(us, C, True)
    with As(b):
        b.peer_update({"host": US, "port": 50001, "up": True})
    dial(b, B, us, US); dial(c, C, us, US); dial(us, US, b, B)
    return us, b, c
# V5: B's kernel restarts, a session starts on B and mails our session; B's request carries the mail beside its cached
# roster and our handler acks it; then our kernel's supervisor sees no kernel answering through B's tunnel and notifies the
# bus B is down; the up notify alone; B's answering exchange
road = "cachedThenHeldDown"
us, b, c = b_and_c_answered(road)
LISTINGS["b"] = None
out["roads"][road] = {"park": park(b, S["new"], "px-held1")}
out["roads"][road]["landing"] = mail_dial(b, B, us, US)
step(road, "cachedMailLanded", us, newOnB=S["new"], nobody=S["nobody"])
notify(us, B, False)
step(road, "bHeldDown", us, newOnB=S["new"], nobody=S["nobody"], other=S["other"])
notify(us, B, True)
step(road, "bUpNotifyOnly", us, newOnB=S["new"], nobody=S["nobody"])
LISTINGS["b"] = [S["other"], S["new"]]
dial(b, B, us, US)
step(road, "bAnswers", us, newOnB=S["new"], nobody=S["nobody"])
# V5b, the attach topology: only our bus dials B, and B's RESPONSE to our dial carries the mail beside its cached roster
road = "responseThenHeldDown"
us = fresh_us(); b, c = other(road, "b"), other(road, "c")
LISTINGS["b"], LISTINGS["c"], LISTINGS["us"] = [S["other"]], [S["csid"]], [S["web"]]
notify(us, B, True); notify(us, C, True)
dial(us, US, b, B); dial(c, C, us, US)
LISTINGS["b"] = None
out["roads"][road] = {"park": park(b, S["new"], "px-held2")}
out["roads"][road]["landing"] = mail_response(us, US, b, B)
step(road, "cachedMailLanded", us, newOnB=S["new"], nobody=S["nobody"])
notify(us, B, False)
step(road, "bHeldDown", us, newOnB=S["new"], nobody=S["nobody"])
# V1: our kernel holds B down (its tunnel to B's kernel says no kernel) while B's own dial to us stands; B's kernel
# restarts, a session starts on B and mails our session; B dials us over its cache carrying the mail
road = "heldDownDialsCached"
us, b, c = b_and_c_answered(road)
notify(us, B, False)
LISTINGS["b"] = None
out["roads"][road] = {"park": park(b, S["new"], "px-held3")}
out["roads"][road]["landing"] = mail_dial(b, B, us, US)
step(road, "downBDialedCachedMail", us, newOnB=S["new"], nobody=S["nobody"], other=S["other"])
# V7: X_far_cached_via_hub beside C, linked and answered; then our kernel holds the hub down
road = "viaThenHubHeldDown"
us = fresh_us(); f, hub, c = other(road, "f"), other(road, "hub"), other(road, "c")
LISTINGS["f"], LISTINGS["hub"], LISTINGS["c"] = [S["other"]], [S["hubsid"]], [S["csid"]]
notify(us, HUB, True); notify(us, C, True)
dial(c, C, us, US)
dial(f, F, hub, HUB); dial(hub, HUB, us, US)
LISTINGS["f"] = None
dial(f, F, hub, HUB); dial(hub, HUB, us, US)
step(road, "farCached", us, newOnFar=S["new"], nobody=S["nobody"])
notify(us, HUB, False)
step(road, "hubHeldDown", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
# V21: B's cached exchange lands its session's mail beside the hub's answered word about B from before the blink; then B
# held down, the hub's word about B vouching
road = "cachedThenHeldDownHubWord"
us = fresh_us(); b, hub = other(road, "b"), other(road, "hub")
LISTINGS["b"], LISTINGS["hub"], LISTINGS["us"] = [S["other"]], [S["hubsid"]], [S["web"]]
notify(us, B, True); notify(us, HUB, True)
with As(b):
    b.peer_update({"host": US, "port": 50001, "up": True})
dial(b, B, us, US); dial(b, B, hub, HUB); dial(hub, HUB, us, US); dial(us, US, b, B)
LISTINGS["b"] = None
out["roads"][road] = {"park": park(b, S["new"], "px-held4")}
out["roads"][road]["landing"] = mail_dial(b, B, us, US)
dial(hub, HUB, us, US)
step(road, "cachedMailLanded", us, newOnB=S["new"], nobody=S["nobody"])
notify(us, B, False)
step(road, "bHeldDown", us, newOnB=S["new"], nobody=S["nobody"])
# V6, residual (3c): B's cached exchange lands its session's mail; our bus restarts and the kernel re-notifies both links; C
# is heard before B; then B's first exchange in the new process, over its cache, and then answered
road = "cachedThenOurRestart"
us, b, c = b_and_c_answered(road)
LISTINGS["b"] = None
out["roads"][road] = {"park": park(b, S["new"], "px-held5")}
out["roads"][road]["landing"] = mail_dial(b, B, us, US)
step(road, "cachedMailLanded", us, newOnB=S["new"], nobody=S["nobody"])
us = load_bus("us2")                               # our bus restarts over the same root
notify(us, B, True); notify(us, C, True)
dial(c, C, us, US)
step(road, "restartedCHeard", us, newOnB=S["new"], nobody=S["nobody"], other=S["other"])
dial(b, B, us, US)
step(road, "bCachedAfterRestart", us, newOnB=S["new"], nobody=S["nobody"])
LISTINGS["b"] = [S["other"], S["new"]]
dial(b, B, us, US)
step(road, "bAnswersAfterRestart", us, newOnB=S["new"], nobody=S["nobody"])
# cost (f): B's last exchange here served a cache, then our kernel holds B down and B never comes back (its machine went
# away during its kernel's blink); C's later exchanges; then our bus restarts, the kernel re-notifies C, and C is heard
road = "heldDownForGood"
us, b, c = b_and_c_answered(road)
LISTINGS["b"] = None
out["roads"][road] = {"bDial": dial(b, B, us, US)}
notify(us, B, False)
step(road, "heldDown", us, nobody=S["nobody"])
dial(c, C, us, US)
step(road, "later1", us, nobody=S["nobody"])
dial(c, C, us, US)
step(road, "later2", us, nobody=S["nobody"])
us = load_bus("us2")
notify(us, C, True)
dial(c, C, us, US)
step(road, "restartedCHeard", us, nobody=S["nobody"], csid=S["csid"])
# THE HUB'S RESTART (round 4 of fork PR #897, the thirty-first commit; the reviewer's verifier at the thirtieth, by
# execution): F, not linked here, behind the hub; C linked and answered, vouching. F's kernel blinks, a session (new)
# starts on F and mails OUR session through the hub on F's cached exchange; the hub's exchange relays it here beside F's
# cached word; then the hub's BUS restarts (a fresh module over its own root: a new bus id, nothing heard) and its first
# exchange here omits F; F's next exchange with the restarted hub is over its cache; then F's listing answers
def far_behind_hub(road, hub_name):                # F behind the hub, the hub relaying to us under hub_name, C vouching
    us = fresh_us(); f, hub, c = other(road, "f"), other(road, "hub"), other(road, "c")
    LISTINGS["f"], LISTINGS["hub"], LISTINGS["c"], LISTINGS["us"] = [S["other"]], [S["hubsid"]], [S["csid"]], [S["web"]]
    notify(us, HUB, True); notify(us, C, True)
    with As(hub):
        hub.peer_update({"host": US, "port": 50001, "up": True})
        hub.peer_update({"host": F, "port": 50003, "up": True})
    with As(f):
        f.peer_update({"host": HUB, "port": 50002, "up": True})
    dial(c, C, us, US)
    dial(hub, hub_name, us, US)                    # the hub learns our roster from our response
    dial(f, F, hub, HUB)                           # F learns it through the hub's gossip; the hub hears F answered
    dial(hub, hub_name, us, US)                    # the hub gossips F's answered word here
    return us, f, hub, c
def restart_hub(road, hub_name):                   # the hub's bus restarts over its own root and dials us first
    hub = load_bus("hub", Path(others_root) / road / "hub")
    LISTINGS["hub"] = [S["hubsid"]]
    with As(hub):
        hub.peer_update({"host": US, "port": 50001, "up": True})
        hub.peer_update({"host": F, "port": 50003, "up": True})
    return hub, dial(hub, hub_name, us, US)
road = "farCachedHubRestarts"
us, f, hub, c = far_behind_hub(road, HUB)
step(road, "farAnswered", us, newOnFar=S["new"], nobody=S["nobody"])
LISTINGS["f"] = None
out["roads"][road] = {"park": park(f, S["new"], "px-hub1")}
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
out["roads"][road]["landingHere"] = mail_dial(hub, HUB, us, US)
step(road, "relayLanded", us, newOnFar=S["new"], nobody=S["nobody"])
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
step(road, "hubRestarted", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
dial(hub, HUB, us, US)
step(road, "hubRestartedAgain", us, newOnFar=S["new"], nobody=S["nobody"])
dial(us, US, hub, HUB)                             # OUR dial to the restarted hub: its response omits F too
step(road, "ourDialToRestartedHub", us, newOnFar=S["new"], nobody=S["nobody"])
dial(f, F, hub, HUB); dial(hub, HUB, us, US)       # F, still blinking, exchanges with the restarted hub over its cache
step(road, "farCachedAtRestartedHub", us, newOnFar=S["new"], nobody=S["nobody"])
LISTINGS["f"] = [S["other"], S["new"]]
dial(f, F, hub, HUB)                               # F's answering exchange with the restarted hub: the first half
step(road, "farAnswersHub", us, newOnFar=S["new"], nobody=S["nobody"])
dial(hub, HUB, us, US)                             # the hub's next exchange here: the release
step(road, "released", us, newOnFar=S["new"], nobody=S["nobody"])
# a second hub's OLDER answered word about F (before the blink) stands beside the first hub's cached word; the first
# hub's bus restarts; then OUR bus restarts, the kernel re-notifies every link, and C and both hubs are heard
road = "secondHubFirstRestarts"
us, f, hub, c = far_behind_hub(road, HUB)
hub2 = other(road, "hub2")
LISTINGS["hub2"] = []
notify(us, HUB2, True)
with As(f):
    f.peer_update({"host": HUB2, "port": 50004, "up": True})
dial(f, F, hub2, HUB2); dial(hub2, HUB2, us, US)   # F answered, through the second hub too
LISTINGS["f"] = None
out["roads"][road] = {"park": park(f, S["new"], "px-hub2")}
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
out["roads"][road]["landingHere"] = mail_dial(hub, HUB, us, US)
dial(hub2, HUB2, us, US)
step(road, "relayLanded", us, newOnFar=S["new"], nobody=S["nobody"])
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
dial(hub2, HUB2, us, US)
step(road, "hubRestarted", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
us = load_bus("us2")                               # our bus restarts over the same root: the held word was this process's
notify(us, HUB, True); notify(us, HUB2, True); notify(us, C, True)
dial(c, C, us, US); dial(hub, HUB, us, US); dial(hub2, HUB2, us, US)
step(road, "ourBusRestarted", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
# the hub known here only by the name it DECLARES (this bus has not dialed its alias yet): it relays F's cached word and
# the new session's mail; its bus restarts and dials us under that name; then OUR dial to the alias folds it there, and
# the declared-name row is forgotten (_drop_peer_name_dupes); then F answers the restarted hub
road = "declaredHubRestartsThenFolds"
us, f, hub, c = far_behind_hub(road, HUB_DECL)
LISTINGS["f"] = None
out["roads"][road] = {"park": park(f, S["new"], "px-hub3")}
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
out["roads"][road]["landingHere"] = mail_dial(hub, HUB_DECL, us, US)
step(road, "relayLanded", us, newOnFar=S["new"], nobody=S["nobody"])
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB_DECL)
step(road, "hubRestarted", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
out["roads"][road]["foldDial"] = dial(us, US, hub, HUB)
out["roads"][road]["heardAfterFold"] = sorted(h for h, st in us.PEER_STATE.items() if st.get("seenAt"))
step(road, "folded", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
LISTINGS["f"] = [S["other"], S["new"]]
dial(f, F, hub, HUB); dial(us, US, hub, HUB)
step(road, "released", us, newOnFar=S["new"], nobody=S["nobody"])
# THE SAME HUB PROCESS'S SILENCE (round 4 of fork PR #897, the thirty-second commit; the reviewer's verifier at the
# thirty-first, by execution): a hub gossips a far host only through that host's session rows, so F's answer with an
# EMPTY listing reaches here as the hub's roster omitting F. The hub process that named F and now omits it has recorded
# F's next exchange: the release. A restarted hub's omission is not F's word (cost (g))
def held_after_relay(road, hub_name, mid):         # F's cached word and a new session's mail through the hub, landed here
    us, f, hub, c = far_behind_hub(road, hub_name)
    LISTINGS["f"] = None
    out["roads"][road] = {"park": park(f, S["new"], mid)}
    out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
    out["roads"][road]["landingHere"] = mail_dial(hub, hub_name, us, US)
    step(road, "relayLanded", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
    return us, f, hub, c
def held_words(bus, host):                         # the words our bus holds on a hub's row: [far host, sid]
    return sorted([pa.get("via"), pa.get("id")] for pa in (bus.PEER_STATE.get(host) or {}).get("viaHeld") or [])
def roster_via(bus, host):                         # the far hosts' sessions a hub's current roster here names: [far host, sid]
    return sorted([pa.get("via"), pa.get("id")] for pa in (bus.PEER_STATE.get(host) or {}).get("presence") or [] if pa.get("via"))
road = "farAnswersEmptyAtHub"                      # the release through the hub's dial (our handler's recorder)
us, f, hub, c = held_after_relay(road, HUB, "px-hub4")
LISTINGS["f"] = []                                 # F's kernel answers with an EMPTY listing: every session on F has ended
out["roads"][road]["farEmptyDial"] = dial(f, F, hub, HUB)
step(road, "farAnswersHubEmpty", us, newOnFar=S["new"], nobody=S["nobody"])
dial(hub, HUB, us, US)                             # the same hub process dials us: its roster omits F
out["roads"][road]["rosterVia"], out["roads"][road]["heldAfter"] = roster_via(us, HUB), held_words(us, HUB)
step(road, "released", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
def held_stamps(bus, host):                        # [far host, sid, the road whose roster last named it] per held word
    return sorted([pa.get("via"), pa.get("id"), pa.get("hubRoad")] for pa in (bus.PEER_STATE.get(host) or {}).get("viaHeld") or [])
road = "farAnswersEmptyOurDial"                    # ...through our dial (our fold of the hub's response), the road that named F
us, f, hub, c = held_after_relay(road, HUB, "px-hub5")
dial(us, US, hub, HUB)                             # OUR dial while F is still cached: the hub's answer names F's cached word
step(road, "ourDialNamesF", us, newOnFar=S["new"], nobody=S["nobody"])
LISTINGS["f"] = []
dial(f, F, hub, HUB)
dial(us, US, hub, HUB)                             # OUR dial to the same hub process: its response omits F
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "released", us, newOnFar=S["new"], nobody=S["nobody"])
road = "declaredHubSameProcessOmits"               # ...the fold of the hub's declared-name row under the alias, then the hub's dial
us, f, hub, c = held_after_relay(road, HUB_DECL, "px-hub6")
LISTINGS["f"] = []
dial(f, F, hub, HUB)
out["roads"][road]["foldDial"] = dial(us, US, hub, HUB)   # OUR dial to the alias: the same hub process, whose response omits F
out["roads"][road]["heardAfterFold"] = sorted(h for h, st in us.PEER_STATE.items() if st.get("seenAt"))
out["roads"][road]["heldAfter"] = held_stamps(us, HUB)
step(road, "folded", us, newOnFar=S["new"], nobody=S["nobody"])
dial(hub, HUB_DECL, us, US)                        # the hub's next dial, filed under the alias: the road that named F omits it
out["roads"][road]["heldAfterHubDial"] = held_words(us, HUB)
step(road, "hubDialsAfterFold", us, newOnFar=S["new"], nobody=S["nobody"])
road = "declaredHubRenamedOnItsDial"               # ...the fold by the hub's own dial under a new declared name: the same road
us, f, hub, c = held_after_relay(road, HUB_DECL, "px-hub16")
LISTINGS["f"] = []
dial(f, F, hub, HUB)
out["roads"][road]["renameDial"] = dial(hub, HUB_DECL2, us, US)   # the hub's hostname changed: its dial declares the new name
out["roads"][road]["heardAfterFold"] = sorted(h for h, st in us.PEER_STATE.items() if st.get("seenAt"))
out["roads"][road]["heldAfter"] = held_words(us, HUB_DECL2)
step(road, "folded", us, newOnFar=S["new"], nobody=S["nobody"])
road = "farAnswersEmptyAtRestartedHub"             # cost (g): F answers the RESTARTED hub with an empty listing
us, f, hub, c = held_after_relay(road, HUB, "px-hub7")
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
step(road, "hubRestarted", us, newOnFar=S["new"], nobody=S["nobody"])
LISTINGS["f"] = []
out["roads"][road]["farEmptyDial"] = dial(f, F, hub, HUB)
dial(hub, HUB, us, US)
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "farAnsweredEmpty", us, newOnFar=S["new"], nobody=S["nobody"])
dial(us, US, hub, HUB); dial(f, F, hub, HUB); dial(hub, HUB, us, US)
step(road, "later", us, nobody=S["nobody"])
us = load_bus("us2")                               # our bus restarts over the same root: the held word was this process's
notify(us, HUB, True); notify(us, C, True)
dial(c, C, us, US); dial(hub, HUB, us, US)
step(road, "ourBusRestarted", us, newOnFar=S["new"], nobody=S["nobody"])
road = "farBusRestartsNoTwin"                      # residual (3a)'s second face: F's bus restarts during its blink with no twin
us, f, hub, c = held_after_relay(road, HUB, "px-hub8")
out["roads"][road]["twinBefore"] = f._PRESENCE_GOOD_FILE.exists()
f._PRESENCE_GOOD_FILE.unlink()                     # F's disk twin of its last answered listing is gone
f = load_bus("f", Path(others_root) / road / "f")  # F's bus restarts over its own root, its kernel still not answering
with As(f):
    f.peer_update({"host": HUB, "port": 50002, "up": True})
out["roads"][road]["farRestartDial"] = dial(f, F, hub, HUB)
dial(hub, HUB, us, US)                             # the same hub process's roster omits F
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "sameHubOmitsF", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
road = "restartedHubNamesAnotherFarHost"           # G behind the same hub answers the restarted hub before F does
us, f, hub, c = held_after_relay(road, HUB, "px-hub9")
g = other(road, "g")
LISTINGS["g"] = [S["gsid"]]
with As(g):
    g.peer_update({"host": HUB, "port": 50002, "up": True})
with As(hub):
    hub.peer_update({"host": G, "port": 50005, "up": True})
dial(g, G, hub, HUB); dial(hub, HUB, us, US)       # G answered through the hub, beside F's cached word
step(road, "gAnswered", us, newOnFar=S["new"], gsid=S["gsid"])
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
with As(hub):
    hub.peer_update({"host": G, "port": 50005, "up": True})
dial(g, G, hub, HUB)                               # G answers the restarted hub; F has not exchanged with it
dial(hub, HUB, us, US)                             # the restarted hub's roster names G and omits F
out["roads"][road]["rosterVia"], out["roads"][road]["heldAfter"] = roster_via(us, HUB), held_words(us, HUB)
step(road, "restartedHubNamesG", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"], gsid=S["gsid"])
road = "farSpeaksHereWhileHeld"                    # F's word held on the restarted hub's row; then F answers HERE, directly
us, f, hub, c = held_after_relay(road, HUB, "px-hub10")
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
step(road, "hubRestarted", us, newOnFar=S["new"], nobody=S["nobody"])
LISTINGS["f"] = [S["other"], S["new"]]             # F's listing answers, naming the session
notify(us, F, True)                                # our kernel links F directly
with As(f):
    f.peer_update({"host": US, "port": 50001, "up": True})
out["roads"][road]["farDial"] = dial(f, F, us, US)  # F's own answering exchange here
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "farAnswersHere", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
# THE ROAD (round 4 of fork PR #897, the thirty-third commit; the reviewer's verifier at the thirty-second, by execution):
# our bus hears a hub's rosters by two roads, the hub's dial (our handler) and its answer to our dial (our fold), and the
# hub can take its answer to our dial BEFORE its own later dial while our fold of that answer runs AFTER the dial is
# recorded. So the same hub process's omission releases a held word only on the road whose roster last named the host
road = "farWithNoBusId"                            # F from before busId and presenceAnswered: its word through the hub carries no viaBus
us = fresh_us(); f, hub, c = other(road, "f"), other(road, "hub"), other(road, "c")
f.BUS_ID = ""                                      # F's exchanges carry no bus id, so the hub stamps viaBus "" on F's rows
LISTINGS["f"], LISTINGS["hub"], LISTINGS["c"], LISTINGS["us"] = [S["other"]], [S["hubsid"]], [S["csid"]], [S["web"]]
notify(us, HUB, True); notify(us, C, True)
with As(hub):
    hub.peer_update({"host": US, "port": 50001, "up": True})
    hub.peer_update({"host": F, "port": 50003, "up": True})
dial(c, C, us, US)
dial(f, F, hub, HUB, strip_answered=True)          # F's exchange with the hub: its listing answers, the bit absent (an older bus)
dial(hub, HUB, us, US)                             # the hub gossips F's word here: no viaBus, viaAnswered False
out["roads"][road] = {"gossip": sorted([pa.get("via"), pa.get("id"), pa.get("viaBus"), pa.get("viaAnswered")]
                                       for pa in us.PEER_STATE[HUB]["presence"] if pa.get("via"))}
step(road, "farWordHere", us, other=S["other"], nobody=S["nobody"])
LISTINGS["f"] = []                                 # every session on F ends: F's next exchange carries no session row
dial(f, F, hub, HUB, strip_answered=True)
dial(hub, HUB, us, US)                             # the same hub process's dial omits F: the road that named it
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "released", us, other=S["other"], nobody=S["nobody"])
def split_dial(src, src_name, dst, dst_name):      # src's real builder and dst's real handler NOW, so the answer's roster is
    with As(src):                                  # taken now; src's real fold of that answer returned, to run LATER
        req = src.build_exchange_request(dst_name, wait=False)
    req["host"] = src_name
    with As(dst):
        resp, status = dst.peer_exchange_handle(req)
    def fold():
        with As(src):
            src.peer_exchange_apply(dst_name, req, resp)
        return status
    return sorted([pa.get("via"), pa.get("id"), pa.get("viaAnswered")] for pa in resp.get("presence") or [] if pa.get("via")), fold
road = "olderAnswerFoldedLate"                     # the verifier's R1: the restarted hub's answer to our dial, taken before its dial
us, f, hub, c = far_behind_hub(road, HUB)
out["roads"][road] = {}
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
out["roads"][road]["olderAnswerVia"], fold_older = split_dial(us, US, hub, HUB)   # the restarted hub has not heard F
LISTINGS["f"] = None
out["roads"][road]["park"] = park(f, S["new"], "px-hub12")
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)   # F's cached exchange with the restarted hub carries the mail
out["roads"][road]["landingHere"] = mail_dial(hub, HUB, us, US)  # the hub's dial, taken later: F's cached word, and the mail lands
step(road, "newerDialRecorded", us, newOnFar=S["new"], nobody=S["nobody"])
fold_older()                                       # our fold of the OLDER answer runs last: the same process's roster omitting F
out["roads"][road]["heldAfterFold"] = held_stamps(us, HUB)
step(road, "olderAnswerFolded", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
LISTINGS["f"] = []                                 # cost (h): F answers the hub with an EMPTY listing
dial(f, F, hub, HUB)
dial(us, US, hub, HUB); dial(us, US, hub, HUB)     # two of OUR dials: the hub's answers omit F, not on the road that named it
out["roads"][road]["heldAfterOurDials"] = held_stamps(us, HUB)
step(road, "ourDialsOmitF", us, newOnFar=S["new"], nobody=S["nobody"])
dial(hub, HUB, us, US)                             # the hub's next dial omits F: the road that named it, the release
out["roads"][road]["heldAfterHubDial"] = held_words(us, HUB)
step(road, "hubDialOmitsF", us, newOnFar=S["new"], nobody=S["nobody"])
# RESIDUAL (3d): a roster that reaches our bus after a NEWER one from the same source; the latest recorded roster stands
road = "hubDialsOutOfOrder"                        # the same road: two of the hub's dials delivered in the other order
us, f, hub, c = far_behind_hub(road, HUB)
out["roads"][road] = {}
hub, out["roads"][road]["restartDial"] = restart_hub(road, HUB)
with As(hub):
    older = hub.build_exchange_request(US, wait=False)   # the restarted hub's dial built now, before it has heard F
older["host"] = HUB
out["roads"][road]["olderDialVia"] = sorted([pa.get("via"), pa.get("id")] for pa in older.get("presence") or [] if pa.get("via"))
LISTINGS["f"] = None
out["roads"][road]["park"] = park(f, S["new"], "px-hub13")
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
out["roads"][road]["landingHere"] = mail_dial(hub, HUB, us, US)  # the NEWER dial lands first: F's cached word and the mail
step(road, "newerDialRecorded", us, newOnFar=S["new"], nobody=S["nobody"])
with As(us):
    out["roads"][road]["olderDialStatus"] = us.peer_exchange_handle(older)[1]   # the older dial arrives last
out["roads"][road]["heldAfter"] = held_words(us, HUB)
step(road, "olderDialLanded", us, newOnFar=S["new"], nobody=S["nobody"])
road = "olderAnsweredWordFoldedLate"               # the verifier's R2: the hub's older answer names F's ANSWERED word
us, f, hub, c = far_behind_hub(road, HUB)
out["roads"][road] = {}
out["roads"][road]["olderAnswerVia"], fold_older = split_dial(us, US, hub, HUB)
LISTINGS["f"] = None
out["roads"][road]["park"] = park(f, S["new"], "px-hub14")
out["roads"][road]["landingAtHub"] = mail_dial(f, F, hub, HUB)
out["roads"][road]["landingHere"] = mail_dial(hub, HUB, us, US)
step(road, "newerDialRecorded", us, newOnFar=S["new"], nobody=S["nobody"])
fold_older()
step(road, "olderAnswerFolded", us, newOnFar=S["new"], nobody=S["nobody"], other=S["other"])
road = "olderAnsweredRowFoldedLate"                # a peer's own row: B's older answer to our dial folded after B's cached dial
us, b, c = b_and_c_answered(road)
out["roads"][road] = {}
out["roads"][road]["olderAnswer"], fold_older = split_dial(us, US, b, B)
LISTINGS["b"] = None
out["roads"][road]["park"] = park(b, S["new"], "px-b15")
out["roads"][road]["landing"] = mail_dial(b, B, us, US)   # B's dial over its cache carries the new session's mail
step(road, "newerDialRecorded", us, newOnB=S["new"])
fold_older()
step(road, "olderAnswerFolded", us, newOnB=S["new"], other=S["other"])
print(json.dumps(out))
""", HERE, BIN, str(others), json.dumps(ROAD_SIDS), R_US, R_B, R_C, R_HUB, R_F, R_HUB2, R_HUB_DECL, R_G, R_HUB_DECL2],
                             capture_output=True, text=True, env=full, cwd=str(home), timeout=120)
        assert out.returncode == 0, "%s roads child failed: %s" % (shape, out.stderr[-2000:])
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
                self.assertEqual((got["schemeAtFirstWrite"], got["schemeAtPeerPhases"]), (False, True),
                                 "the heartbeat phases ran under the legacy singleton scheme and the peer phases under peer "
                                 "mode, each read back through the bus's own peers_on (MOVED under ROMP_POSTAL_PEERS=0 in "
                                 "round 3 of fork PR #897: a heartbeat row vouches for absence there alone)")
                self.assertEqual(row, {"kind": "heartbeat", "sids": [REMOTE], "heard": True, "expired": False,
                                       "linkDown": False, "linkUp": False, "answered": True, "reachable": True,
                                       "vouchesAbsence": True, "name": "web"},
                                 "the row's fields as the writer spells them, the seven flags among them (a heartbeat under "
                                 "the legacy scheme has no link and vouches for absence by its TTL, and is its own answer): "
                                 "the fixtures' _row restates every one (legacy=True for this row), and the reader requires "
                                 "the seven")

    def test_rule_5_fires_for_a_sid_nothing_knows_once_the_bus_has_written(self):
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertFalse(got["beforeWrite"], "no mirror file yet: cannot determine, conservative")
                self.assertTrue(got["first"]["fire"], "the bus wrote %s; the judge's read must be that file: rule 5 "
                                "presumes a sid nothing knows closed (the heartbeat phases run under the legacy singleton "
                                "scheme, where a beat vouches for absence; MOVED there in round 3 of fork PR #897)" % got["busFile"])

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

    def test_a_heard_link_up_host_whose_exchange_served_a_cache_vouches_for_presence_alone_until_an_exchange_answers(self):
        """Round 3 of fork PR #897, the reviewer's ruling; the road its refuters found by execution through the real handler
        and writer. B is heard with its link up, but its exchange served the last answered rows through a kernel blink: B
        vouches for the presence of the sid it names (rule 4) and not for the absence of one it does not, so a session
        started on B during the blink is cannot-determine, the reason naming B with its listing unanswered, never rule 5
        (at the tenth commit B vouched for absence over the cache, and rule 5 presumed that session closed while its mail
        rode the same exchange). B's next exchange with an answered listing is the event. Both halves: B's request built by
        the real builder and recorded by the real handler, then the real handler's response folded by the real dialer's
        fold. The verdicts are pinned first, then the payloads' bits and the rows."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        # every row of the file on this road, sorted by key as the reason sorts them: the carried hosts and hubs, B, the two
        # carried heartbeats, the hubs' carried words about the spoke (the hub's word about B folded at the ninth restart's end)
        carried = (HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (not heard)", HUB2 + " (not heard)")
        beats = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        vias = (VIA_SPOKE + " (not heard)", VIA_SPOKE2 + " (not heard)")
        blink_reason = NO_VOUCH(*carried, HOST2 + " (listing unanswered)", *beats, *vias)
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                blink = got["cacheBlink"]
                self.assertEqual(self._v(blink, "blinked"), blink_reason,
                                 "THE RULE: a session started on B during the blink is in no roster while B's listing does not "
                                 "answer, and B, its link known up, does not vouch for absence over a cache: cannot-determine, "
                                 "the reason naming B with its listing unanswered beside the carried rows (at the tenth commit "
                                 "this was rule 5, a live session presumed closed while its mail rode the same exchange)")
                self.assertEqual(got["restartMemory10"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the tenth restart is a fresh module object, its memory and its link table empty")
                self.assertEqual((got["cacheDialStatus"], got["cacheBlinkDialStatus"]), (200, 200), "both of B's dials were answered")
                first = got["cacheAnswered"]
                self.assertEqual((first["payloadAnswered"], first["payloadSids"]), (True, [OTHER]),
                                 "the request builder rides the bit beside the rows: B's listing answered")
                self.assertEqual((self._v(first, "other"), self._v(first, "nobody"), self._v(first, "blinked")), (RULE_4, RULE_5, RULE_5),
                                 "B heard with its link up on an answered roster vouches: rule 4 for its sid, rule 5 for a sid nothing "
                                 "names (the session that will start during the blink is not started yet)")
                self.assertEqual((first["hosts"][HOST2], (first["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, True, [OTHER]), True))
                self.assertEqual((blink["payloadAnswered"], blink["payloadSids"]), (False, [OTHER]),
                                 "the blink: B's request serves the last answered rows AND marks them a cache (a builder riding "
                                 "the rows alone leaves this side to read the cache as B's word about what runs there now)")
                self.assertEqual(self._v(blink, "nobody"), blink_reason, "the same for a sid nothing names")
                self.assertEqual(self._v(blink, "other"), RULE_4,
                                 "the cached roster still vouches for the presence of the sid it names: live at the last answered listing")
                self.assertEqual((blink["hosts"][HOST2], (blink["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, False, [OTHER]), False),
                                 "heard, its link up, reachable, its roster unanswered: presence alone (a writer ignoring the bit "
                                 "writes vouchesAbsence True here)")
                self.assertEqual(blink["filed"], [HOST2], "B's row, under its name")
                again = got["cacheAnswersAgain"]
                self.assertEqual((again["payloadAnswered"], again["payloadSids"]), (True, sorted([OTHER, BLINKED])))
                self.assertEqual((self._v(again, "blinked"), self._v(again, "other"), self._v(again, "nobody")), (RULE_4, RULE_4, RULE_5),
                                 "the event: B's next exchange with an answered listing names the session, and a sid nothing names "
                                 "is rule 5's again, on that write and nothing else")
                self.assertEqual((again["hosts"][HOST2], (again["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, True, sorted([OTHER, BLINKED])), True))
                # the dialer's half: the real handler's response, built while this process's listing does not answer, folded
                # by the real dialer's fold as B's word
                rblink = got["cacheResponseBlink"]
                self.assertEqual((rblink["payloadAnswered"], rblink["payloadSids"]), (False, sorted([OTHER, BLINKED])),
                                 "the response builder rides the bit too: the last answered rows, marked a cache")
                self.assertEqual((self._v(rblink, "nobody"), self._v(rblink, "blinked"), self._v(rblink, "other")),
                                 (blink_reason, RULE_4, RULE_4),
                                 "recorded by the dialer's fold: B vouches for presence alone (a fold dropping the bit, or "
                                 "defaulting it to answered, lets rule 5 fire here)")
                self.assertEqual((rblink["hosts"][HOST2], (rblink["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, False, sorted([OTHER, BLINKED])), False))
                ranswers = got["cacheResponseAnswers"]
                self.assertEqual((ranswers["payloadAnswered"], self._v(ranswers, "nobody"), self._v(ranswers, "blinked")),
                                 (True, RULE_5, RULE_4), "the response built once the listing answers releases it")
                self.assertEqual((ranswers["answered"] or {}).get(HOST2), True)

    def test_a_hubs_answered_word_about_a_directly_held_host_stands_beside_that_hosts_cached_row_until_it_answers(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the eleventh commit, by execution through the real builder,
        handler, writer and reader: B is heard with its link up, but its exchange served a cache while a session started on
        B during the blink, and the hub, its own exchange with B answered, names that session. A heard row over a cache is
        the third state, beside carried and held down, in which a direct row speaks for nothing about a session started
        on its host since, so the hub's word stands as a via row beside B's row, carrying B's bit as the hub stamped it,
        and the session is rule 4's (at the eleventh commit the gate read heard and not held down alone, the hub's word
        folded into the cached row, and the hub, vouching for absence, let rule 5 presume the session closed for one
        exchange interval of B: a live session presumed closed while another host vouched). The same with the hub NOT
        heard: after a restart B is heard first, still over the cache, and a second hub vouches for absence; the carried
        via row stands, so the session is cannot-determine by the hub's last word, never rule 5. B's exchange that
        answers, naming the session, is the event: B speaks, the via row is dropped by the carry, and the hub's next
        exchange folds. While B's row is reachable over the cache, a sid nothing names is cannot-determine by the
        listing-unanswered arm, naming B, in both halves (round 4 of fork PR #897, the twenty-ninth commit: until then
        these two asserts pinned rule 5, residual (3), a session started on B during the blink that no hub names
        presumed closed on another host's vouch). The verdicts are pinned first, then the payloads' bits and the rows."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        carried = (HOST + " (not heard)", ALIAS + " (not heard)", HUB + " (not heard)", HUB2 + " (not heard)")
        beats = (self.HB + REMOTE + " (not heard, expired)", self.HB + REMOTE2 + " (not heard)")
        vias = (VIA_SPOKE + " (not heard)", VIA_SPOKE2 + " (not heard)")
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                word = got["cacheHubWord"]
                self.assertEqual(self._v(word, "hubNamed"), RULE_4,
                                 "THE RULE: B's exchange served a cache while a session started on B during the blink, and the hub, "
                                 "its exchange with B answered, names it: the hub's word stands as a via row beside B's cached row, "
                                 "so the session is live on another host, rule 4 (a gate on heard and not held down alone folds the "
                                 "hub's word into the cached row, the session is in no row, and the hub, vouching for absence, lets "
                                 "rule 5 presume it closed: the false settle the reviewer's verifier found at the eleventh commit)")
                self.assertEqual((got["cacheHubBlinkDialStatus"], got["cacheHubCarriedDialStatus"]), (200, 200))
                blink = got["cacheHubBlink"]
                self.assertEqual((blink["payloadAnswered"], blink["payloadSids"]), (False, sorted([OTHER, BLINKED])),
                                 "B's request serves the last answered rows, marked a cache")
                self.assertEqual(self._v(blink, "hubNamed"), NO_VOUCH(*carried, HOST2 + " (listing unanswered)", *beats, *vias),
                                 "before the hub is heard the session is in no row and no source vouches: cannot-determine, the "
                                 "reason naming B with its listing unanswered")
                self.assertEqual((self._v(word, "other"), self._v(word, "blinked"), self._v(word, "nobody")),
                                 (RULE_4, RULE_4, UNANSWERED(HOST2 + " (listing unanswered)")),
                                 "B's cached roster vouches for the presence of the sids it names; the hub, answered and its link up, "
                                 "vouches for absence, but B's row is reachable and unanswered, so a sid nothing names is "
                                 "cannot-determine by the listing-unanswered arm, naming B: RESIDUAL (3), closed by the arm since the "
                                 "twenty-ninth commit (until then rule 5 here, and a session started on B during the blink that no "
                                 "hub names presumed closed on the hub's vouch)")
                self.assertEqual((word["hosts"][HOST2], (word["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, False, sorted([OTHER, BLINKED])), False),
                                 "B's row: heard, its link up, reachable, its roster a cache, vouching for presence alone")
                self.assertEqual((word["hosts"][VIA_B], (word["answered"] or {}).get(VIA_B)),
                                 (L(True, False, False, True, True, True, sorted([OTHER, BLINKED, HUB_NAMED])), True),
                                 "the hub's word about B beside B's row, carrying B's bit as the hub stamped it (B's exchange with "
                                 "the hub answered): heard, the hub's link up, vouching (a writer folding it into the cached row "
                                 "writes no such row)")
                # the carry's half: the hub not heard
                self.assertEqual(got["restartMemory11"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the eleventh restart is a fresh module object, its memory and its link table empty")
                car = got["cacheHubWordCarried"]
                self.assertEqual(self._v(car, "hubNamed"), LOST(VIA_B + " (not heard)"),
                                 "THE CARRY'S HALF: B heard first over the cache, the hub not heard, the second hub vouching for "
                                 "absence: the hub's carried word still names the session, so it is cannot-determine by that word "
                                 "(a carry letting the cached row speak drops the via row, the session is in no row, and the second "
                                 "hub's vouch lets rule 5 presume it closed)")
                self.assertEqual((car["payloadAnswered"], car["payloadSids"]), (False, sorted([OTHER, BLINKED])),
                                 "B's first request in the new process serves the last answered rows, primed from the disk twin, "
                                 "marked a cache")
                self.assertEqual((self._v(car, "other"), self._v(car, "nobody")),
                                 (RULE_4, UNANSWERED(HOST2 + " (listing unanswered)")),
                                 "B's cached roster still vouches for the presence of the sid it names; the second hub vouches for "
                                 "absence, but B's row is reachable and unanswered, so a sid nothing names is cannot-determine by the "
                                 "listing-unanswered arm, naming B: RESIDUAL (3), closed by the arm since the twenty-ninth commit "
                                 "(until then rule 5 here, on the second hub's vouch)")
                self.assertEqual(car["hosts"][HOST2], L(True, False, False, True, True, False, sorted([OTHER, BLINKED])))
                self.assertEqual(car["hosts"][VIA_B], L(False, False, False, True, False, False, sorted([OTHER, BLINKED, HUB_NAMED])),
                                 "the carried via row: not heard, the seed's linkUp, vouching for nothing, the hub's last word kept")
                rel = got["cacheHubWordReleased"]
                self.assertEqual((rel["payloadAnswered"], rel["payloadSids"]), (True, sorted([OTHER, BLINKED, HUB_NAMED])))
                self.assertEqual((self._v(rel, "hubNamed"), self._v(rel, "nobody")), (RULE_4, RULE_5),
                                 "the event: B's exchange with an answered listing names the session, rule 4 by B's own row")
                self.assertNotIn(VIA_B, rel["hosts"],
                                 "the via row is DROPPED by the carry once B speaks on an answered listing (a carry that keeps it "
                                 "leaves the hub's older word naming a sid for the file's life)")
                self.assertEqual((rel["hosts"][HOST2], (rel["answered"] or {}).get(HOST2)),
                                 (L(True, False, False, True, True, True, sorted([OTHER, BLINKED, HUB_NAMED])), True))
                folds = got["cacheHubWordFolds"]
                self.assertNotIn(VIA_B, folds["hosts"], "the hub heard at last: its word folds, B speaks")
                self.assertEqual((self._v(folds, "hubNamed"), self._v(folds, "nobody")), (RULE_4, RULE_5))

    # ── THE ROADS (round 4 of fork PR #897, the reviewer's ruling on its round-3 refuters' finding, section A, the
    # twenty-ninth commit): the second child, _roads_over_one_root. Each verdict is (closed, rule, why); each row is
    # [heard, linkDown, linkUp, answered, reachable, vouchesAbsence, sids] ──

    @staticmethod
    def _road(got, road, step, key):
        return tuple(got["roads"][road][step][key])

    def test_the_roads_ran_over_the_root_the_test_prepared(self):
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual((got["judgeState"], got["busState"]), (got["root"], got["root"] + "/postal"),
                                 "the judge's STATE is the root and OUR bus's is the root plus postal")
                self.assertEqual((got["hostsOff"], got["discovered"]), ("off", 0),
                                 "the child read the session-hosts file the test wrote; an empty HOME, so rules 1 and 2 answer "
                                 "for no sid and every verdict below is the mirror's")

    def test_a_session_started_on_a_hub_during_its_blink_is_cannot_determine_while_its_word_about_another_host_vouches(self):
        """X_hub_cached_self, the first of the four roads (the refuters' scenario, through the real builders, handler, fold,
        writer and reader). The hub, its kernel listing answering, relays B's roster; its kernel then blinks and a session
        starts on the hub, in no roster, and the hub's exchange serves its cache. The hub's row is reachable and
        unanswered, and its word about B, answered, the hub's link up, vouches for absence: until the twenty-ninth commit
        rule 5 presumed the new session closed on that word, the cached host's own gossip. The listing-unanswered arm
        answers cannot-determine, naming the hub's row; the hub's next answering exchange is the release."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "hubCachedSelf", "cached", "newOnHub"), UNANSWERED(R_HUB + " (listing unanswered)"),
                                 "THE RULE: a session started on the hub during its blink, beside the hub's vouching word about "
                                 "B, is cannot-determine, the reason naming the hub's row (until the twenty-ninth commit "
                                 "[true, 5, no-reachable-host-names-it], a live session presumed closed)")
                self.assertEqual(self._road(got, "hubCachedSelf", "cached", "nobody"), UNANSWERED(R_HUB + " (listing unanswered)"))
                self.assertEqual((self._road(got, "hubCachedSelf", "cached", "hubsid"), self._road(got, "hubCachedSelf", "cached", "other")),
                                 (RULE_4, RULE_4), "the cached roster and the hub's word still vouch for the presence of what they name")
                self.assertEqual(got["roads"]["hubCachedSelf"]["cachedDial"], [200, False, [S["hubsid"]]],
                                 "the hub's exchange was answered and carried its last answered rows marked a cache")
                self.assertEqual(got["roads"]["hubCachedSelf"]["cached"]["rows"],
                                 {R_HUB: [True, False, True, False, True, False, [S["hubsid"]]],
                                  R_VIA_B: [True, False, True, True, True, True, [S["other"]]]},
                                 "the hub's row reachable and unanswered; its word about B answered and vouching")
                self.assertEqual((self._road(got, "hubCachedSelf", "answers", "newOnHub"), self._road(got, "hubCachedSelf", "answers", "nobody")),
                                 (RULE_4, RULE_5), "THE RELEASE: the hub's next answering exchange names the session, and a sid "
                                 "nothing names is rule 5's again")

    def test_a_cached_hosts_session_is_cannot_determine_while_another_host_vouches_until_its_listing_answers(self):
        """X_cached_no_hub, the second road, and the named witness of cost (b), a heard peer whose kernel does not answer.
        B's exchange serves a cache while a session starts on B during the blink; no hub names it; C, answered and its
        link up, vouches for absence (until the twenty-ninth commit, rule 5 for B's session on C's word). The arm answers
        cannot-determine, naming B, and holds across B's and C's next exchanges while B's kernel still does not answer (a
        peer whose kernel never answers holds every sid so for as long as it is heard in this bus process: cost (b), on
        the restricted side); B's exchange that answers is the release."""
        S = ROAD_SIDS
        b = UNANSWERED(R_B + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "cachedNoHub", "cached", "blinked"), b,
                                 "THE RULE: a session started on B during its blink, no hub naming it, C vouching: "
                                 "cannot-determine, naming B (until the twenty-ninth commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual((self._road(got, "cachedNoHub", "cached", "nobody"), self._road(got, "cachedNoHub", "cached", "other")),
                                 (b, RULE_4))
                self.assertEqual(got["roads"]["cachedNoHub"]["cached"]["rows"],
                                 {R_B: [True, False, True, False, True, False, [S["other"]]],
                                  R_C: [True, False, True, True, True, True, [S["csid"]]]})
                self.assertEqual((self._road(got, "cachedNoHub", "stillCached", "blinked"), self._road(got, "cachedNoHub", "stillCached", "nobody")),
                                 (b, b), "COST (b): B heard again over its cache, C again: the arm holds while B's kernel does not answer")
                self.assertEqual((self._road(got, "cachedNoHub", "answers", "blinked"), self._road(got, "cachedNoHub", "answers", "nobody")),
                                 (RULE_4, RULE_5), "THE RELEASE: B's exchange that answers names the session; rule 5 again")

    def test_a_far_hosts_cached_word_through_a_heard_hub_holds_its_session_until_the_hub_relays_its_answer(self):
        """X_far_cached_via_hub, the third road. A far host F, not held here, blinks and a session starts there; F's exchange
        with the hub serves its cache; the hub relays F's word, stamped with F's bit, beside its own answered row. The via
        row is reachable (the hub's link) and unanswered, and the hub vouches: until the twenty-ninth commit rule 5 for F's
        session on the hub's word. The release has two halves, F's answering exchange with the hub and then the hub's next
        exchange here, and the first alone releases nothing here."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "farCachedViaHub", "farCached", "newOnFar"), via,
                                 "THE RULE: a session started on F during its blink, the hub vouching: cannot-determine, naming "
                                 "the hub's word about F (until the twenty-ninth commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual((self._road(got, "farCachedViaHub", "farAnswered", "nobody"), self._road(got, "farCachedViaHub", "farCached", "nobody"),
                                  self._road(got, "farCachedViaHub", "farCached", "other")), (RULE_5, via, RULE_4))
                self.assertEqual(got["roads"]["farCachedViaHub"]["farCached"]["rows"],
                                 {R_HUB: [True, False, True, True, True, True, [S["hubsid"]]],
                                  R_VIA_F: [True, False, True, False, True, False, [S["other"]]]},
                                 "the via row carries F's bit as the hub stamped it: reachable by the hub's link, unanswered")
                self.assertEqual(self._road(got, "farCachedViaHub", "farAnswersHub", "newOnFar"), via,
                                 "F's answering exchange with the hub alone: nothing here has changed")
                self.assertEqual((self._road(got, "farCachedViaHub", "released", "newOnFar"), self._road(got, "farCachedViaHub", "released", "nobody")),
                                 (RULE_4, RULE_5), "THE RELEASE: the hub's next exchange here carries F's answer")

    def test_a_sessions_own_mail_rides_its_hosts_cached_exchange_while_its_sid_is_cannot_determine(self):
        """X_mail_rides_cached, the fourth road, end to end. A session starts on the hub during its blink and mails a session
        on OUR host: the hub's resolve names a relay to us, its outbox parks the mail, and its real builder carries the
        relay beside presenceAnswered False; our real handler acks it and writes the mirror. At that moment the sender's
        sid is cannot-determine, naming the hub's row (until the twenty-ninth commit rule 5 while its own mail landed,
        and the courier's tracker of the sender on this machine would settle once the local recipient completed). This is
        THE CONTRAST the writer's and the judge's docstrings state, where the session's mail can have landed, not the
        host's link: a cached host's session reaches the judge through its own mail, on the exchange that omits it,
        whatever the kernel says about that host's link afterwards (the held-down roads below)."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["mailRidesCached"]
                self.assertEqual(self._road(got, "mailRidesCached", "relayLanded", "newOnHub"), UNANSWERED(R_HUB + " (listing unanswered)"),
                                 "THE RULE: the sender's own mail landed here on the hub's cached exchange, and its sid is "
                                 "cannot-determine (until the twenty-ninth commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual((road["resolve"], road["parked"]), (["relay", R_US, S["web"]], True),
                                 "the hub resolved our session as a relay to us and parked the mail")
                self.assertEqual((road["reqAnswered"], road["reqRelays"]), (False, [[S["new"], S["web"]]]),
                                 "the hub's exchange carried the relay beside its cached roster, marked unanswered")
                self.assertEqual((road["status"], road["acks"]), (200, ["px-road1"]), "our handler acked the relay")
                self.assertEqual((self._road(got, "mailRidesCached", "relayLanded", "hubsid"), self._road(got, "mailRidesCached", "relayLanded", "other")),
                                 (RULE_4, RULE_4))

    def test_the_release_is_the_sources_next_answering_exchange(self):
        """The release (the ruling: no new event and no new writer state; the row's bit is replaced by the source's next
        answering exchange, which both recorders record; the population's one piece of writer state since the
        thirty-first commit, a hub's held word, is released by the same event, the hub's word naming the far host
        again, or, for an answer with an empty listing, the same hub process's roster omitting the host: the
        hub-restart and same-process witnesses below). B_cached: B answered, blinked (its request and our dial's
        response each serving the cache), answered again naming the session: rule 5 for a sid nothing names. B_older_peer:
        B's payloads lacking the field, then its request carrying it: rule 5. Both read so before the arm too; a writer
        that kept a row's unanswered bit across an answering exchange reds here."""
        b = NO_VOUCH(R_B + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual((self._road(got, "bCached", "answersAgain", "nobody"), self._road(got, "bCached", "answersAgain", "blinked")),
                                 (RULE_5, RULE_4), "B_cached answersAgain: B's answering exchange releases the row")
                self.assertEqual((self._road(got, "bCached", "answered", "nobody"), self._road(got, "bCached", "blinkRequest", "nobody"),
                                  self._road(got, "bCached", "blinkResponse", "nobody")), (RULE_5, b, b),
                                 "B the only host: over its cache nothing vouches, the no-vouching arm before the new one")
                self.assertEqual(self._road(got, "bOlderPeer", "newerRequest", "nobody"), RULE_5,
                                 "B_older_peer newerRequest: B's first request carrying the field releases the row")
                self.assertEqual((self._road(got, "bOlderPeer", "olderRequest", "nobody"), self._road(got, "bOlderPeer", "olderResponse", "nobody")),
                                 (b, b), "a payload lacking the field reads unanswered")

    def test_the_down_host_and_the_lone_cached_host_answer_as_before_the_arm(self):
        """The controls stay as they are (the ruling): A_down_then_carried (the A road: B held down while the hub names a
        session started on B, then our bus restarted and the hub heard before B), X_down_no_hub (a session started on B
        while our kernel holds B down after B's ANSWERED exchange, C vouching: rule 5, the contrast's other half, since
        such a session can reach this machine only through a roster that names it or on B's next exchange, which
        replaces B's bit; a B held down after a CACHED exchange is the held-down roads' case, held by the arm) and
        X_cached_alone (B's cache with no other host: nothing vouches). Every verdict equals the one the refuters' probe
        recorded before the arm."""
        want = {
            "downThenCarried": {
                "bothUp": {"other": RULE_4, "nobody": RULE_5, "goss": RULE_5},
                "bDownHubNames": {"goss": RULE_4, "nobody": RULE_5},
                "bDownHubDown": {"goss": LOST(R_VIA_B + " (link down)"),
                                 "nobody": NO_VOUCH(R_B + " (link down)", R_HUB + " (link down)", R_VIA_B + " (link down)")},
                "bDownHubBack": {"goss": RULE_4},
                "bBack": {"goss": RULE_4, "nobody": RULE_5},
                "bBackHubAgain": {"goss": RULE_4},
                "carriedHubFirst": {"later": RULE_4, "goss": RULE_4, "nobody": RULE_5},
                "carriedHubDown": {"later": LOST(R_VIA_B + " (link down)"),
                                   "nobody": NO_VOUCH(R_B + " (not heard)", R_HUB + " (link down)", R_VIA_B + " (link down)")},
                "carriedBHeard": {"later": RULE_4, "nobody": RULE_5}},
            "downNoHub": {"downBCVouches": {"blinked": RULE_5, "other": LOST(R_B + " (link down)")}},
            "cachedAlone": {"cachedBAlone": {"blinked": NO_VOUCH(R_B + " (listing unanswered)")}},
        }
        for shape, got in self.roads.items():
            for road, steps in want.items():
                for step, verdicts in steps.items():
                    with self.subTest(shape=shape, road=road, step=step):
                        self.assertEqual({k: self._road(got, road, step, k) for k in verdicts}, verdicts,
                                         "a control: the verdict before the arm")

    def test_residual_3a_a_far_host_whose_cached_roster_is_empty_behind_a_heard_hub_still_answers_rule_5(self):
        """RESIDUAL (3a), disclosed and NOT closed (the ruling; the writer's docstring, residual (3)): a far host F behind a
        heard hub whose cached roster is EMPTY. Its kernel has not answered since its bus started (no twin), or its last
        answered listing named nobody, so its exchange with the hub carries presenceAnswered False and no session row;
        presence_payload stamps a far host's bit only on that host's session rows, so the hub gossips no row about F and
        no via row exists to carry F's bit, and the hub's answered row vouches. A session started on F meanwhile reaches
        the judge through its own mail relayed by the hub and answers rule 5: a false rule 5 left open, until F's
        answering exchange with the hub and the hub's next exchange here. The follow-up is the carrier fix, each heard far
        host's answered bit carried independent of session rows (an exchange-field change outside this fix-tier PR); this
        witness asserts the rule-5 answer, so it turns red when the carrier lands and the disclosure moves with it."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farEmptyCacheViaHub"]
                self.assertEqual((road["farDial"], road["farAnsweredDial"], road["farBlinkDial"]),
                                 ([200, False, []], [200, True, []], [200, False, []]),
                                 "F's exchanges with the hub: no answer and an empty cache; an answered listing naming nobody; "
                                 "then its blink over that empty roster")
                for step in ("emptyCache", "answeredNobody"):
                    self.assertEqual(self._road(got, "farEmptyCacheViaHub", step, "newOnFar"), RULE_5,
                                     "RESIDUAL (3a) HOLDS at %s: a session started on F, whose cached roster is empty, answers "
                                     "rule 5 while the hub vouches (no via row carries F's bit); when this pin reds, the carrier "
                                     "fix has closed the residual and the disclosure moves with it" % step)
                    self.assertEqual(got["roads"]["farEmptyCacheViaHub"][step]["rows"],
                                     {R_HUB: [True, False, True, True, True, True, [S["hubsid"]]]},
                                     "the hub's row alone, answered and vouching: no via row about F at %s" % step)

    def test_residual_3b_a_far_host_gone_after_a_cached_exchange_with_its_hub_holds_every_sid_while_the_hub_gossips_it(self):
        """RESIDUAL (3b) and cost (d), disclosed on the restricted side (the ruling; X_far_cached_then_gone, the second
        refuter's scenario): a far host F whose last exchange with the hub served a cache and that then stops exchanging
        with the hub, here held down by the hub's kernel. presence_payload gossips every PEER_STATE row whatever the hub's
        link state, and a hub never forgets a far host's PEER_STATE (the only pop is _drop_peer_name_dupes), so it keeps
        gossiping F's last word with viaAnswered False. Our via row stays reachable (the hub's link) and unanswered, and
        the arm holds every sid nothing names at cannot-determine, across the hub's exchanges, until F answers the hub
        again and the hub's next exchange reaches here, or this bus holds F directly and F's own answering exchange lands
        here (while F's row speaks), or this bus restarts; since the thirty-first commit the hub's restart is no release
        (the hub-restart witnesses below). No false settle. Until the twenty-ninth commit, rule 5 here."""
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual((self._road(got, "farCachedThenGone", "farGoneAtHub", "nobody"),
                                  self._road(got, "farCachedThenGone", "farGoneAtHub2", "nobody")), (via, via),
                                 "RESIDUAL (3b): the hub's two exchanges gossip F's cached word, and the arm names that via "
                                 "row each time (until the twenty-ninth commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual(self._road(got, "farCachedThenGone", "farGoneAtHub2", "other"), RULE_4,
                                 "the sid F's cached word names stays rule 4's")

    def test_cost_a_a_peer_lacking_the_field_holds_every_sid_beside_a_vouching_host(self):
        """COST (a), on the restricted side (the ruling): a peer lacking the field (an older bus, the project's own
        included) reads unanswered, so heard here, or gossiped by a heard hub, it holds rule 5 at cannot-determine for
        every sid nothing names while another host vouches. Its release is its first exchange that carries the field
        (test_the_release_is_the_sources_next_answering_exchange, B_older_peer)."""
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "olderBesideVouching", "olderBesideC", "nobody"), UNANSWERED(R_B + " (listing unanswered)"),
                                 "an older peer heard here beside C vouching: the arm, naming it")
                self.assertEqual(self._road(got, "olderFarViaHub", "olderFarGossiped", "nobody"), UNANSWERED(R_VIA_F + " (listing unanswered)"),
                                 "an older far host gossiped by a heard, newer hub, which stamps it unanswered: the arm, naming "
                                 "the hub's word about it")
                self.assertEqual((self._road(got, "olderBesideVouching", "olderBesideC", "other"),
                                  self._road(got, "olderFarViaHub", "olderFarGossiped", "other")), (RULE_4, RULE_4))

    def test_cost_c_a_host_with_no_link_state_that_dials_once_over_a_cache_and_falls_silent_holds_every_sid_until_a_restart(self):
        """COST (c), ACCEPTED on the restricted side (the ruling, the second refuter's third cost): a heard row with no link
        state (here a host the kernel never notified) whose last exchange served a cache and that then stops exchanging. A
        peer's presence has no TTL and a row with no link state has no down event, so the arm holds every sid nothing names
        until that host's next answering exchange or this bus's restart, whose carry makes the row not heard; for a host
        that never returns the restart is the only release. B, its kernel not answering since its bus started, dials in
        once over its (empty) cache beside C, linked and answered, and falls silent: the arm names B across C's later
        exchanges; our bus restarts and C is heard: rule 5. Until the twenty-ninth commit rule 5 throughout, since C
        vouched."""
        S = ROAD_SIDS
        b = UNANSWERED(R_B + " (no link state, listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["roads"]["silentNoLink"]["bDial"], [200, False, []], "B's one dial: answered, a cache, no row")
                self.assertEqual([self._road(got, "silentNoLink", step, "nobody") for step in ("dialedOnce", "later1", "later2")],
                                 [b, b, b], "COST (c): the arm names B across C's later exchanges (until the twenty-ninth "
                                 "commit [true, 5, no-reachable-host-names-it] each time)")
                self.assertEqual(got["roads"]["silentNoLink"]["later2"]["rows"][R_B], [True, False, False, False, True, False, []],
                                 "B's row: heard, no link state, unanswered, reachable")
                self.assertEqual(self._road(got, "silentNoLink", "restartedCHeard", "nobody"), RULE_5,
                                 "the restart's carry makes B's row not heard, and C, heard again, vouches: rule 5")
                self.assertEqual(got["roads"]["silentNoLink"]["restartedCHeard"]["rows"][R_B], [False, False, False, False, False, False, []],
                                 "B's row carried, not heard")

    # ── THE HELD-DOWN ROADS (round 4 of fork PR #897, the thirtieth commit; the reviewer's verifier at the twenty-ninth, by
    # execution through the real builders, handler, fold, notify handler, writer and reader): the twenty-ninth commit's arm
    # read `reachable`, so a row whose last exchange here served a cache stopped holding once the kernel held its host
    # down, and a live session whose own mail rode that exchange answered rule 5. The arm reads heard in this process and
    # unanswered, whatever the link ──

    def test_a_session_whose_mail_rode_its_hosts_cached_exchange_stays_cannot_determine_once_the_kernel_holds_that_host_down(self):
        """V5, V5b and V21, the verifier's roads. B and C linked up and answered; B's kernel restarts and a session starts
        on B, mailing our session: B's request (V5), or B's response to our dial (V5b, the attach topology), carries the
        mail beside B's cached roster and our bus lands it. Then the kernel's supervisor sees no kernel answering through
        B's tunnel and notifies the bus that B is down (the event a kernel restart on B produces). B's row is still heard
        in this process and its last exchange here served a cache, so the arm holds, both causes named; the up notify
        alone changes nothing (B's link stays down until B is heard with it up), and B's answering exchange is the release.
        V21 is the same with the hub's answered word about B from before the blink vouching instead of C. Until this
        commit the down notify released the hold: [true, 5, no-reachable-host-names-it] for the sender at bHeldDown, a
        live session presumed closed, while its mail had landed here on the exchange that omitted it."""
        S = ROAD_SIDS
        cached, down = UNANSWERED(R_B + " (listing unanswered)"), UNANSWERED(R_B + " (link down, listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["cachedThenHeldDown"]
                self.assertEqual((road["park"], road["landing"]),
                                 ({"resolve": ["relay", R_US, S["web"]], "parked": True},
                                  {"status": 200, "reqAnswered": False, "reqRelays": [S["new"]], "acks": ["px-held1"]}),
                                 "B's session's mail rode B's cached exchange and our handler acked it")
                self.assertEqual((self._road(got, "cachedThenHeldDown", "cachedMailLanded", "newOnB"),
                                  self._road(got, "cachedThenHeldDown", "cachedMailLanded", "nobody")), (cached, cached))
                self.assertEqual(self._road(got, "cachedThenHeldDown", "bHeldDown", "newOnB"), down,
                                 "THE RULE: the kernel holds B down after the exchange that carried the sender's mail, and the "
                                 "sender is still cannot-determine, the reason naming B down and a cache (until this commit "
                                 "[true, 5, no-reachable-host-names-it], a live session presumed closed)")
                self.assertEqual((self._road(got, "cachedThenHeldDown", "bHeldDown", "nobody"),
                                  self._road(got, "cachedThenHeldDown", "bHeldDown", "other")),
                                 (down, LOST(R_B + " (link down, listing unanswered)")))
                self.assertEqual(road["bHeldDown"]["rows"][R_B], [True, True, False, False, False, False, [S["other"]]],
                                 "B's row: heard, held down, unanswered, not reachable")
                self.assertEqual(self._road(got, "cachedThenHeldDown", "bUpNotifyOnly", "newOnB"), down,
                                 "the up notify alone: B's link stays down until B is heard with it up, and the arm holds")
                self.assertEqual((self._road(got, "cachedThenHeldDown", "bAnswers", "newOnB"),
                                  self._road(got, "cachedThenHeldDown", "bAnswers", "nobody")), (RULE_4, RULE_5),
                                 "THE RELEASE: B's answering exchange names the session; a sid nothing names is rule 5's again")
                road = got["roads"]["responseThenHeldDown"]
                self.assertEqual(road["landing"], {"status": 200, "respAnswered": False, "respRelays": [S["new"]],
                                                   "landed": [[S["new"], "ack"]]},
                                 "V5b: B's response to our dial carried the mail beside its cached roster, and our fold landed it")
                self.assertEqual((self._road(got, "responseThenHeldDown", "cachedMailLanded", "newOnB"),
                                  self._road(got, "responseThenHeldDown", "bHeldDown", "newOnB")), (cached, down),
                                 "V5b: the same verdicts (until this commit rule 5 at bHeldDown)")
                road = got["roads"]["cachedThenHeldDownHubWord"]
                self.assertEqual(road["landing"]["acks"], ["px-held4"])
                self.assertEqual(road["bHeldDown"]["rows"][R_VIA_B], [True, False, True, True, True, True, [S["other"]]],
                                 "V21: the hub's answered word about B from before the blink vouches")
                self.assertEqual((self._road(got, "cachedThenHeldDownHubWord", "cachedMailLanded", "newOnB"),
                                  self._road(got, "cachedThenHeldDownHubWord", "bHeldDown", "newOnB")), (cached, down),
                                 "V21: the hub's word about B vouching, B held down after its cached exchange: the arm (until "
                                 "this commit rule 5 at bHeldDown, on the via row's vouch)")

    def test_a_host_held_down_that_dials_us_over_its_cache_holds_its_sessions_sid_at_cannot_determine(self):
        """V1, the verifier's road: our kernel holds B down (its tunnel to B's kernel says no kernel) while B's own dial to us
        stands (the far side dialing, _link_down's docstring); B's kernel restarts, a session starts on B and mails our
        session, and B dials us over its cache carrying the mail. B's bit postdates the drop, so the row is held down AND
        heard in this process with an unanswered roster: the arm, both causes named. Until this commit rule 5 for the
        sender, and the reason for B's own sid read "(link down)" alone, the cache dropped as predating the drop."""
        S = ROAD_SIDS
        down = UNANSWERED(R_B + " (link down, listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["heldDownDialsCached"]
                self.assertEqual(road["landing"], {"status": 200, "reqAnswered": False, "reqRelays": [S["new"]],
                                                   "acks": ["px-held3"]}, "B, held down, dialed us over its cache with the mail")
                self.assertEqual(self._road(got, "heldDownDialsCached", "downBDialedCachedMail", "newOnB"), down,
                                 "THE RULE: the sender whose mail B carried over its cache while held down is cannot-determine "
                                 "(until this commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual((self._road(got, "heldDownDialsCached", "downBDialedCachedMail", "nobody"),
                                  self._road(got, "heldDownDialsCached", "downBDialedCachedMail", "other")),
                                 (down, LOST(R_B + " (link down, listing unanswered)")))
                self.assertEqual(road["downBDialedCachedMail"]["rows"][R_B], [True, True, False, False, False, False, [S["other"]]])

    def test_a_far_hosts_cached_word_stays_held_once_the_kernel_holds_its_hub_down(self):
        """V7, the verifier's road: the third road's far host F serving its cache through a heard hub, beside C linked and
        answered; then our kernel holds the hub down. The via row about F is still heard in this process (the hub's
        exchange) and unanswered (F's bit as the hub stamped it), so the arm holds, both causes named. Until this commit
        the hub's down notify released it: rule 5 for F's session on C's vouch."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "viaThenHubHeldDown", "farCached", "newOnFar"),
                                 UNANSWERED(R_VIA_F + " (listing unanswered)"))
                self.assertEqual(self._road(got, "viaThenHubHeldDown", "hubHeldDown", "newOnFar"),
                                 UNANSWERED(R_VIA_F + " (link down, listing unanswered)"),
                                 "THE RULE: the hub held down after relaying F's cached word, C vouching: cannot-determine, "
                                 "naming the hub's word about F (until this commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual(self._road(got, "viaThenHubHeldDown", "hubHeldDown", "other"),
                                 LOST(R_VIA_F + " (link down, listing unanswered)"))
                self.assertEqual(got["roads"]["viaThenHubHeldDown"]["hubHeldDown"]["rows"][R_VIA_F],
                                 [True, True, False, False, False, False, [S["other"]]])

    def test_residual_3c_a_session_whose_mail_landed_on_a_cached_exchange_before_this_bus_restarted_answers_rule_5(self):
        """RESIDUAL (3c), disclosed and NOT closed (the thirtieth commit, V6 of the reviewer's verifier at the twenty-ninth):
        B's cached exchange lands its session's mail; our bus restarts; the kernel re-notifies both links and C is heard
        before B. B's row is CARRIED (heard false), and a carried row holds nothing: its bit is its last process's, and a
        hold on it would hold every sid for the file's life for a host never heard again, with no release but that host's
        return. So the sender, in no row, answers rule 5 while C vouches: a false rule 5 left open, from this bus's
        restart until B's first exchange in the new process (over its cache: the arm; answered: rule 4 by B's roster).
        This witness asserts that rule-5 answer, so it turns red when the residual closes and the disclosure moves with
        it; rule 5 there before this commit too."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["cachedThenOurRestart"]
                self.assertEqual(road["landing"]["acks"], ["px-held5"], "the sender's mail landed on B's cached exchange")
                self.assertEqual(self._road(got, "cachedThenOurRestart", "cachedMailLanded", "newOnB"),
                                 UNANSWERED(R_B + " (listing unanswered)"))
                self.assertEqual(self._road(got, "cachedThenOurRestart", "restartedCHeard", "newOnB"), RULE_5,
                                 "RESIDUAL (3c) HOLDS: after this bus's restart B's row is carried and holds nothing, and the "
                                 "sender whose mail landed on B's cached exchange before the restart answers rule 5 while C "
                                 "vouches; when this pin reds, the residual has closed and the disclosure moves with it")
                self.assertEqual(road["restartedCHeard"]["rows"][R_B], [False, False, True, False, False, False, [S["other"]]],
                                 "B's row carried: not heard, the kernel's seed of its link up, its last process's bit")
                self.assertEqual(self._road(got, "cachedThenOurRestart", "bCachedAfterRestart", "newOnB"),
                                 UNANSWERED(R_B + " (listing unanswered)"),
                                 "B's first exchange in the new process, over its cache: the arm holds again")
                self.assertEqual((self._road(got, "cachedThenOurRestart", "bAnswersAfterRestart", "newOnB"),
                                  self._road(got, "cachedThenOurRestart", "bAnswersAfterRestart", "nobody")), (RULE_4, RULE_5),
                                 "B's answering exchange names the session")

    def test_cost_f_a_host_held_down_after_a_cached_exchange_that_never_returns_holds_every_sid_until_a_restart(self):
        """COST (f), on the restricted side (the thirtieth commit): the same shape as cost (c), for a host the kernel holds
        down. B's last exchange here served a cache, then the kernel holds B down and B never returns (its machine went
        away during its kernel's blink). The row stays heard in this process and unanswered, so the arm holds every sid
        nothing names across C's later exchanges, until B's next answering exchange or this bus's restart, whose carry
        makes the row not heard; for a host that never returns the restart is the only release. Until this commit the
        down notify was the release: rule 5 throughout, since C vouched."""
        down = UNANSWERED(R_B + " (link down, listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["roads"]["heldDownForGood"]["bDial"], [200, False, [ROAD_SIDS["other"]]],
                                 "B's last exchange: answered, its cached roster")
                self.assertEqual([self._road(got, "heldDownForGood", step, "nobody") for step in ("heldDown", "later1", "later2")],
                                 [down, down, down], "COST (f): the arm names B across C's later exchanges (until this commit "
                                 "[true, 5, no-reachable-host-names-it] each time)")
                self.assertEqual(self._road(got, "heldDownForGood", "restartedCHeard", "nobody"), RULE_5,
                                 "the restart's carry makes B's row not heard, and C, heard again, vouches: rule 5")

    # ── THE HUB'S RESTART (round 4 of fork PR #897, the thirty-first commit; the reviewer's verifier at the thirtieth, by
    # execution): a RESTARTED hub's silence about a far host is not that host's answer, so a far host's unanswered word
    # stays heard on the hub's row across the restarted hub's exchanges that omit it (postal_service.py _via_held) ──

    def test_a_far_hosts_cached_word_stays_held_when_its_hub_restarts_until_the_far_host_answers(self):
        """W1, the verifier's road: F behind the hub, C linked and answered. F's kernel blinks, a session starts on F and
        mails our session through the hub on F's cached exchange, and the hub relays it here beside F's cached word. Then
        the hub's BUS restarts (a new bus id, its PEER_STATE empty) and dials us before F has exchanged with it: its roster
        omits F. The ruling of 00:27Z allows two releases of the arm, the far host's next answering exchange and this
        bus's restart; until this commit the hub's first exchange after its restart dropped F's word from the hub's row,
        the via row was carried (heard false, out of the arm), and the session whose mail had just landed here answered
        rule 5 on C's vouch. Now the hub's word stays held on its row (heard, its bit False) across the hub's exchanges,
        across F's exchange with the restarted hub over its cache, and across F's answering exchange with the hub until
        the hub relays it here: the release."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        held = [True, False, True, False, True, False, [S["other"]]]
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farCachedHubRestarts"]
                self.assertEqual((road["park"]["resolve"][:2], road["landingHere"]["acks"]), (["relay", R_HUB], ["px-hub1"]),
                                 "the session on F mailed our session through the hub, and our handler acked it")
                self.assertEqual((road["landingAtHub"]["reqAnswered"], road["landingAtHub"]["reqRelays"]), (False, [S["new"]]),
                                 "the mail rode F's CACHED exchange with the hub")
                self.assertEqual(self._road(got, "farCachedHubRestarts", "relayLanded", "newOnFar"), via)
                self.assertEqual(road["restartDial"], [200, True, [S["hubsid"]]],
                                 "the restarted hub's first exchange here: answered, its own roster, nothing about F")
                self.assertEqual(self._road(got, "farCachedHubRestarts", "hubRestarted", "newOnFar"), via,
                                 "THE RULE: the hub's restart is not F's answer; the arm still names the hub's word about F "
                                 "(until the thirty-first commit [true, 5, no-reachable-host-names-it], the session whose mail "
                                 "had just landed presumed closed)")
                self.assertEqual(road["hubRestarted"]["rows"][R_VIA_F], held,
                                 "the held word: heard in this process, unanswered, reachable by the hub's link, F's last "
                                 "roster (until the thirty-first commit carried: not heard, unreachable)")
                self.assertEqual(self._road(got, "farCachedHubRestarts", "hubRestarted", "other"), RULE_4,
                                 "the sid F's cached word names stays rule 4's by the held word")
                self.assertEqual([self._road(got, "farCachedHubRestarts", step, "newOnFar")
                                  for step in ("hubRestartedAgain", "ourDialToRestartedHub", "farCachedAtRestartedHub", "farAnswersHub")],
                                 [via, via, via, via],
                                 "held across the restarted hub's next dial here and our dial to it (both recorders), F's exchange "
                                 "with it over its cache, and F's answering exchange with the hub before the hub relays it here")
                self.assertEqual((self._road(got, "farCachedHubRestarts", "released", "newOnFar"),
                                  self._road(got, "farCachedHubRestarts", "released", "nobody")), (RULE_4, RULE_5),
                                 "THE RELEASE: the hub relays F's answered word, which names the session")

    def test_a_second_hubs_older_answered_word_does_not_release_the_first_hubs_held_word_and_our_restart_does(self):
        """W2, the verifier's second road: a second hub carries F's ANSWERED word from before the blink, beside the first
        hub's cached word, which relays the new session's mail here. The first hub's bus restarts. Until this commit the
        first hub's word was carried out of the arm, and the second hub's older word, vouching and not naming the new
        session, let rule 5 presume it closed. Now the first hub's word is held, and the second hub's older word, which
        is no answering exchange of F's since, releases nothing. The other release the ruling allows, this bus's restart:
        the held word lives in this process's memory, so after our restart the first hub's word is carried (heard false)
        and holds nothing, and the new session answers rule 5 while C vouches: residual (3c), whose far-host face this is,
        a false rule 5 left open until F's first word here in the new process."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["secondHubFirstRestarts"]
                self.assertEqual(road["landingHere"]["acks"], ["px-hub2"], "the new session's mail landed through the first hub")
                self.assertEqual(road["relayLanded"]["rows"][R_VIA_F2], [True, False, True, True, True, True, [S["other"]]],
                                 "the second hub's older word about F: answered, vouching, silent about the new session")
                self.assertEqual(self._road(got, "secondHubFirstRestarts", "relayLanded", "newOnFar"), via)
                self.assertEqual(self._road(got, "secondHubFirstRestarts", "hubRestarted", "newOnFar"), via,
                                 "THE RULE: the first hub's restart releases nothing, and the second hub's older word is no "
                                 "answering exchange of F's (until the thirty-first commit [true, 5, no-reachable-host-names-it])")
                self.assertEqual(road["hubRestarted"]["rows"][R_VIA_F], [True, False, True, False, True, False, [S["other"]]])
                self.assertEqual(self._road(got, "secondHubFirstRestarts", "ourBusRestarted", "newOnFar"), RULE_5,
                                 "RESIDUAL (3c), a far host's face: after this bus's restart the first hub's word is carried and "
                                 "holds nothing; when this pin reds, the residual has closed and the disclosure moves with it")
                self.assertEqual(road["ourBusRestarted"]["rows"][R_VIA_F], [False, False, True, False, False, False, [S["other"]]],
                                 "carried: not heard, the kernel's seed of the hub's link up, the last process's bit")

    def test_a_hub_known_by_its_declared_name_that_restarts_and_then_folds_keeps_the_held_word(self):
        """The fold after a restart: the hub is known here only by the name it declares (this bus has not dialed its alias
        yet) when it relays F's cached word and the new session's mail; its bus restarts and dials us under that name
        (its new bus id matches no row, so it is filed there again); then this bus's own dial to the alias lands with the
        new bus id, and _drop_peer_name_dupes forgets the declared-name row. The held word moves to the alias's row with
        it; dropped with the row, the carry's rename drop (the hub's bus heard under another name) would drop the via row
        too, and the new session would answer rule 5 with no answering exchange of F's (the builder's road at the
        thirty-first commit, by execution through the real builders, handlers, folds, this bus's writer and the reader;
        rule 5 at the thirtieth). The alias's row then carries the word under its key until F answers the restarted hub
        and the hub's word reaches here."""
        S = ROAD_SIDS
        decl = UNANSWERED(R_VIA_F_DECL + " (no link state, listing unanswered)")
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["declaredHubRestartsThenFolds"]
                self.assertEqual(road["landingHere"]["acks"], ["px-hub3"], "the new session's mail landed through the hub")
                self.assertEqual(self._road(got, "declaredHubRestartsThenFolds", "relayLanded", "newOnFar"), decl,
                                 "the hub's word under its declared name, a name the kernel never notified (no link state)")
                self.assertEqual(self._road(got, "declaredHubRestartsThenFolds", "hubRestarted", "newOnFar"), decl,
                                 "held across the restart under the declared name (until the thirty-first commit "
                                 "[true, 5, no-reachable-host-names-it])")
                self.assertEqual(road["heardAfterFold"], [R_C, R_HUB], "the fold forgot the declared-name row")
                self.assertEqual(self._road(got, "declaredHubRestartsThenFolds", "folded", "newOnFar"), via,
                                 "THE RULE: the held word moved to the alias's row with the fold (with it dropped, [true, 5, "
                                 "no-reachable-host-names-it])")
                self.assertNotIn(R_VIA_F_DECL, road["folded"]["rows"], "the declared-name key left with its row")
                self.assertEqual(self._road(got, "declaredHubRestartsThenFolds", "folded", "other"), RULE_4,
                                 "F's cached roster, held, still names the session live at F's last answered listing")
                self.assertEqual((self._road(got, "declaredHubRestartsThenFolds", "released", "newOnFar"),
                                  self._road(got, "declaredHubRestartsThenFolds", "released", "nobody")), (RULE_4, RULE_5),
                                 "THE RELEASE: F answers the restarted hub, and the hub's word reaches here")

    # ── THE SAME HUB PROCESS'S SILENCE (round 4 of fork PR #897, the thirty-second commit; the reviewer's verifier at
    # the thirty-first, by execution): a hub gossips a far host only through that host's session rows, so the far host's
    # answer with an EMPTY listing reaches here as the same hub process's roster omitting it, which releases the held
    # word on the road that last named the host (the thirty-third commit); a restarted hub's omission does not
    # (postal_service.py _via_held) ──

    def test_a_far_hosts_empty_answer_through_the_same_hub_process_releases_its_held_word(self):
        """Z2, the verifier's road at the thirty-first commit: F's cached word and a new session's mail through the hub,
        landed here, so the arm names the hub's word about F; then F's kernel answers with an EMPTY listing, the new
        session and every other on F having ended. The hub stamps a far host's bit only on that host's session rows
        (presence_payload), so its next roster omits F. At the thirty-first commit a held word was released only by the
        hub naming the host again, so F's word stayed held for this bus process's life and every sid on this machine
        stayed cannot-determine. The ruled release is F's next answering exchange, and the same hub process's omission
        is that exchange here: the process that named F and now omits it has recorded F's next exchange, carrying no
        session row. This road files the hub's roster through the hub's dial (our handler), the road that named F; the
        next through our dial (our fold of the hub's response) once our dial's answer has named F, and the one after
        through the fold of a hub known by its declared name (_drop_peer_name_dupes), which holds the word until the
        hub's next dial (the thirty-third commit: the release needs the road that named the host). F's answering
        exchange with the hub alone releases nothing here."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        carried = [False, False, True, False, False, False, [S["other"]]]
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farAnswersEmptyAtHub"]
                self.assertEqual((road["landingAtHub"]["reqAnswered"], road["landingHere"]["acks"]), (False, ["px-hub4"]),
                                 "the new session's mail rode F's CACHED exchange with the hub and landed here")
                self.assertEqual(self._road(got, "farAnswersEmptyAtHub", "relayLanded", "newOnFar"), via)
                self.assertEqual(road["farEmptyDial"], [200, True, []], "F's answering exchange with the hub: an empty listing")
                self.assertEqual(self._road(got, "farAnswersEmptyAtHub", "farAnswersHubEmpty", "newOnFar"), via,
                                 "F's answering exchange with the hub alone: nothing here has changed")
                self.assertEqual((self._road(got, "farAnswersEmptyAtHub", "released", "newOnFar"),
                                  self._road(got, "farAnswersEmptyAtHub", "released", "nobody"),
                                  self._road(got, "farAnswersEmptyAtHub", "released", "other")),
                                 (RULE_5, RULE_5, LOST(R_VIA_F + " (not heard)")),
                                 "THE RELEASE through the hub's dial: the same hub process omits F, F's empty answer (at the "
                                 "thirty-first commit listing-unanswered, naming the held word, for this bus process's life)")
                self.assertEqual((road["rosterVia"], road["heldAfter"]), ([], []),
                                 "the hub's next roster names no far host, and our bus holds no word on the hub's row")
                self.assertEqual(road["released"]["rows"][R_VIA_F], carried,
                                 "the hub's word about F is carried, heard false, as an answered word the hub stops naming is")

    def test_a_far_hosts_empty_answer_releases_its_held_word_through_our_dial_to_the_same_hub_process(self):
        """Z2 through our dial: the same opening; then OUR dial while F is still cached, whose answer names F's cached
        word, so our dial's road is the one that last named F (the thirty-third commit: the same process's omission
        releases a word only on the road that named it); then F's answering exchange with the hub over an empty listing,
        and OUR dial to the same hub process, whose response omits F: our fold of the response (peer_exchange_apply)
        releases the word as our handler does (at the thirty-first commit held, listing-unanswered)."""
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._road(got, "farAnswersEmptyOurDial", "relayLanded", "newOnFar"), via)
                self.assertEqual(self._road(got, "farAnswersEmptyOurDial", "ourDialNamesF", "newOnFar"), via,
                                 "our dial's answer names F's cached word: the arm, as for any current word")
                self.assertEqual((self._road(got, "farAnswersEmptyOurDial", "released", "newOnFar"),
                                  self._road(got, "farAnswersEmptyOurDial", "released", "nobody")), (RULE_5, RULE_5),
                                 "THE RELEASE through our dial: the same hub process's response omits F (at the thirty-first "
                                 "commit listing-unanswered, naming the held word)")
                self.assertEqual(got["roads"]["farAnswersEmptyOurDial"]["heldAfter"], [])

    def test_a_far_hosts_empty_answer_holds_its_word_through_the_fold_and_the_same_hub_processs_next_dial_releases_it(self):
        """Z2 through the fold (named ..._releases_its_held_word_through_the_fold_of_the_same_hub_process until the
        thirty-third commit): the hub is known here only by the name it declares when it relays F's cached word and the
        new session's mail; F answers the hub with an empty listing; then OUR dial to the hub's alias lands with the same
        bus id, and _drop_peer_name_dupes forgets the declared-name row, handing its words to the alias's row. The two
        rows are one hub process, but their rosters came by different roads (the declared-name row's by the hub's dial,
        the alias's by our dial), and the hub may have taken its answer to our dial before its dial, so the hand-over
        releases nothing: the word moves to the alias's row, held, stamped with the hub's dial as the road that named F
        (at the thirty-second commit it was released at the hand-over, rule 5). The hub's next dial, filed under the
        alias, omits F on that road: the release."""
        decl = UNANSWERED(R_VIA_F_DECL + " (no link state, listing unanswered)")
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                fold = got["roads"]["declaredHubSameProcessOmits"]
                self.assertEqual(self._road(got, "declaredHubSameProcessOmits", "relayLanded", "newOnFar"), decl,
                                 "the hub's word under the name it declares")
                self.assertEqual((self._road(got, "declaredHubSameProcessOmits", "folded", "newOnFar"),
                                  self._road(got, "declaredHubSameProcessOmits", "folded", "nobody")), (via, via),
                                 "HELD through the fold: the alias's roster came by our dial, not the road that named F (at the "
                                 "thirty-second commit [true, 5, no-reachable-host-names-it] for the session live on F)")
                self.assertEqual((fold["heardAfterFold"], fold["heldAfter"]), ([R_C, R_HUB], [[R_F, S["other"], "dial"]]),
                                 "our dial to the alias folded the declared-name row away, and the word is held on the alias's "
                                 "row, stamped with the road that named F")
                self.assertEqual((self._road(got, "declaredHubSameProcessOmits", "hubDialsAfterFold", "newOnFar"),
                                  self._road(got, "declaredHubSameProcessOmits", "hubDialsAfterFold", "nobody"),
                                  fold["heldAfterHubDial"]), (RULE_5, RULE_5, []),
                                 "THE RELEASE: the hub's next dial, filed under the alias, omits F on the road that named it")

    def test_a_far_hosts_empty_answer_releases_its_word_through_the_fold_by_the_hubs_own_dial_under_a_new_name(self):
        """Z2 through the other fold (the thirty-third commit): the hub is known here only by the name it declares when it
        relays F's cached word and the new session's mail; F answers the hub with an empty listing; then the hub's
        hostname changes (self_host reads it live, with no restart) and its next dial declares the new name, with the same
        bus id, so _drop_peer_name_dupes forgets the old declared-name row and hands its words to the new one. Both rows'
        rosters came by the hub's dial, the road that named F, and the new one omits F: the release at the hand-over, rule
        5 (a hand-over that released nothing would answer listing-unanswered here, naming the hub's word under the new
        name, until the hub's next dial)."""
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["declaredHubRenamedOnItsDial"]
                self.assertEqual(self._road(got, "declaredHubRenamedOnItsDial", "relayLanded", "newOnFar"),
                                 UNANSWERED(R_VIA_F_DECL + " (no link state, listing unanswered)"))
                self.assertEqual((road["renameDial"][0], road["heardAfterFold"]), (200, [R_C, R_HUB_DECL2]),
                                 "the hub's dial under its new name folded the old declared-name row away")
                self.assertEqual((self._road(got, "declaredHubRenamedOnItsDial", "folded", "newOnFar"),
                                  self._road(got, "declaredHubRenamedOnItsDial", "folded", "nobody"), road["heldAfter"]),
                                 (RULE_5, RULE_5, []),
                                 "THE RELEASE at the hand-over: the new name's roster came by the road that named F and omits it")

    def test_cost_g_a_far_host_that_answers_a_restarted_hub_with_an_empty_listing_holds_every_sid_until_a_restart(self):
        """COST (g), disclosed on the restricted side (the writer's docstring): F's cached word and the new session's mail
        through the hub, landed here; the hub's bus restarts, so F's word is held on the hub's row; then F answers the
        RESTARTED hub with an EMPTY listing. The restarted hub's roster omits a host it has not heard and a host that
        answered with no session in the same way, and no field of the exchange tells the two apart, so the word stays
        held and the arm holds every sid on this machine until the hub names F again or this bus restarts, whose carry
        makes the via row not heard (then rule 5). The follow-up is the carrier fix, each heard far host's answered bit
        carried independent of session rows."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farAnswersEmptyAtRestartedHub"]
                self.assertEqual(road["restartDial"], [200, True, [S["hubsid"]]], "the restarted hub's first exchange here")
                self.assertEqual(self._road(got, "farAnswersEmptyAtRestartedHub", "hubRestarted", "newOnFar"), via)
                self.assertEqual((road["farEmptyDial"], road["heldAfter"]), ([200, True, []], [[R_F, S["other"]]]),
                                 "F answers the restarted hub with an empty listing, and the word stays held on the hub's row")
                self.assertEqual([self._road(got, "farAnswersEmptyAtRestartedHub", step, "nobody") for step in ("farAnsweredEmpty", "later")],
                                 [via, via], "COST (g): the arm names the held word across the restarted hub's later exchanges")
                self.assertEqual((self._road(got, "farAnswersEmptyAtRestartedHub", "ourBusRestarted", "newOnFar"),
                                  self._road(got, "farAnswersEmptyAtRestartedHub", "ourBusRestarted", "nobody")), (RULE_5, RULE_5),
                                 "our bus's restart: the held word was that process's, the via row is carried, and C vouches")

    def test_residual_3a_a_far_hosts_empty_cache_after_its_bus_restarts_releases_its_held_word_and_its_session_answers_rule_5(self):
        """RESIDUAL (3a)'s second face, disclosed and NOT closed (the writer's docstring): F's cached word named a session
        and the new session's mail rode that exchange here; then F's bus restarts during its kernel's blink with its disk
        twin gone, so its next exchange with the SAME hub process serves an empty cache: presenceAnswered False and no
        session row. The hub's roster omits F, which this bus cannot tell from F's answer with an empty listing, the
        release (the previous test), so the word is released, and the new session, live on F, answers rule 5 while the
        hub and C vouch: a false rule 5 left open until F's answering exchange with the hub and the hub's next exchange
        here (at the thirty-first commit the word stayed held, cannot-determine). The follow-up is the carrier fix; this
        witness asserts the rule-5 answer, so it turns red when the carrier lands and the disclosure moves with it."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farBusRestartsNoTwin"]
                self.assertEqual(self._road(got, "farBusRestartsNoTwin", "relayLanded", "newOnFar"),
                                 UNANSWERED(R_VIA_F + " (listing unanswered)"))
                self.assertEqual((road["twinBefore"], road["farRestartDial"]), (True, [200, False, []]),
                                 "F had a disk twin before its restart; after it, F's exchange with the hub serves an empty cache")
                self.assertEqual(self._road(got, "farBusRestartsNoTwin", "sameHubOmitsF", "newOnFar"), RULE_5,
                                 "RESIDUAL (3a) HOLDS: the session live on F, whose empty cache the hub's silence cannot be told from an "
                                 "empty answer, answers rule 5; when this pin reds, the carrier fix has closed the residual and the "
                                 "disclosure moves with it")
                self.assertEqual(road["heldAfter"], [], "the same hub process omits F: the word is released")
                self.assertEqual(road["sameHubOmitsF"]["rows"][R_VIA_F], [False, False, True, False, False, False, [S["other"]]])

    def test_a_restarted_hub_naming_another_far_host_first_releases_nothing(self):
        """Z1, the verifier's road at the thirty-first commit (a mutant that released a held word whenever the hub's
        roster named ANY far host passed every module): G, a second far host behind the same hub, answered through it
        beside F's cached word; the hub's bus restarts; G answers the restarted hub before F exchanges with it, so the
        restarted hub's roster names G and omits F. G's word is no word about F: F's word stays held, the session whose
        mail rode F's cached exchange stays cannot-determine, and the sid F's cached roster names stays rule 4's."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["restartedHubNamesAnotherFarHost"]
                self.assertEqual(self._road(got, "restartedHubNamesAnotherFarHost", "gAnswered", "gsid"), RULE_4)
                self.assertEqual((self._road(got, "restartedHubNamesAnotherFarHost", "restartedHubNamesG", "newOnFar"),
                                  self._road(got, "restartedHubNamesAnotherFarHost", "restartedHubNamesG", "nobody"),
                                  self._road(got, "restartedHubNamesAnotherFarHost", "restartedHubNamesG", "other"),
                                  self._road(got, "restartedHubNamesAnotherFarHost", "restartedHubNamesG", "gsid")),
                                 (via, via, RULE_4, RULE_4),
                                 "THE RULE: the restarted hub naming G releases nothing of F's (a release on any far host named "
                                 "answers [true, 5, no-reachable-host-names-it] for the session live on F)")
                self.assertEqual((road["rosterVia"], road["heldAfter"]), ([[R_G, S["gsid"]]], [[R_F, S["other"]]]),
                                 "the restarted hub's roster names G alone, and F's word stays held on the hub's row")
                self.assertEqual(road["restartedHubNamesG"]["rows"][R_VIA_G], [True, False, True, True, True, True, [S["gsid"]]])

    def test_the_far_hosts_own_answering_row_here_consumes_its_held_word_through_the_fold(self):
        """Z3, the verifier's road at the thirty-first commit (a mutant whose held words never folded into the far host's
        own row passed every module): F's word held on the restarted hub's row; then our kernel links F directly and F's
        own answering exchange lands here, naming the new session. F's row speaks (_direct_row_speaks: heard, its link up,
        its roster answered), so the held word folds into it, as a current word does: the session is rule 4's by F's row
        and a sid nothing names answers rule 5 (with the held word standing as its own via row, cannot-determine). The
        word stays on the hub's row, folded while F's row speaks."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farSpeaksHereWhileHeld"]
                self.assertEqual(self._road(got, "farSpeaksHereWhileHeld", "hubRestarted", "nobody"),
                                 UNANSWERED(R_VIA_F + " (listing unanswered)"))
                self.assertEqual((self._road(got, "farSpeaksHereWhileHeld", "farAnswersHere", "newOnFar"),
                                  self._road(got, "farSpeaksHereWhileHeld", "farAnswersHere", "nobody"),
                                  self._road(got, "farSpeaksHereWhileHeld", "farAnswersHere", "other")), (RULE_4, RULE_5, RULE_4),
                                 "THE FOLD: F's own row speaks for F, so its held word stands as no via row (a writer that never "
                                 "folds a held word answers cannot-determine, listing-unanswered, for the sid nothing names)")
                self.assertEqual((road["farDial"], road["heldAfter"]), ([200, True, sorted([S["other"], S["new"]])], [[R_F, S["other"]]]),
                                 "F's own answering exchange here; the held word still on the hub's row")
                self.assertNotIn(R_VIA_F, road["farAnswersHere"]["rows"], "no via row for the hub's word about F")

    # ── THE ROAD (round 4 of fork PR #897, the thirty-third commit; the reviewer's verifier at the thirty-second, by
    # execution): our bus hears a hub's rosters by two roads, the hub's dial (our handler) and its answer to our dial (our
    # fold), and the hub can take its answer to our dial before its own later dial while our fold of that answer runs
    # after the dial is recorded; so the same hub process's omission releases a held word only on the road whose roster
    # last named the host (postal_service.py _via_held, `hubRoad`) ──

    def test_a_far_host_with_no_bus_id_is_released_by_the_same_hub_processs_omission_on_the_road_that_named_it(self):
        """The verifier's mutant N9 at the thirty-second commit (the release fired only for a far host whose rows carry a
        viaBus) passed every module, since every release road here gossiped a far host with a bus id. F here is a bus from
        before busId and presenceAnswered: its exchanges carry neither, so the hub stamps viaBus "" and viaAnswered False
        on F's rows, and F's word here is unanswered (cost (a)), the arm holding the sid nothing names. F's sessions all
        end; its next exchange carries no session row, and the same hub process's dial, the road that named F, omits F:
        the release, whatever bus id F carries. Rule 5 for the sid nothing names; F's word carried, heard false."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["farWithNoBusId"]
                self.assertEqual(road["gossip"], [[R_F, S["other"], "", False]],
                                 "the hub's gossip about F carries no bus id and F's unanswered bit")
                self.assertEqual((self._road(got, "farWithNoBusId", "farWordHere", "other"),
                                  self._road(got, "farWithNoBusId", "farWordHere", "nobody")), (RULE_4, via))
                self.assertEqual((self._road(got, "farWithNoBusId", "released", "nobody"),
                                  self._road(got, "farWithNoBusId", "released", "other"), road["heldAfter"]),
                                 (RULE_5, LOST(R_VIA_F + " (not heard)"), []),
                                 "THE RELEASE for a far host with no bus id: the same hub process omits F on the road that named "
                                 "it (a release keyed on a viaBus answers listing-unanswered here, the word held)")
                self.assertEqual(road["released"]["rows"][R_VIA_F], [False, False, True, False, False, False, [S["other"]]])

    def test_an_older_answer_folded_after_the_hubs_newer_dial_keeps_the_far_hosts_word_held(self):
        """The verifier's R1 at the thirty-second commit, as a pin: F answered through the hub; the hub's bus restarts;
        OUR dial reaches the restarted hub, which answers at once, before it has heard F, so that answer's roster omits F;
        our fold of it is delayed. Meanwhile F's kernel blinks, a session starts on F and mails our session on F's cached
        exchange with the restarted hub, and the hub's DIAL, taken later, names F's cached word and carries the mail here.
        Then our fold of the OLDER answer runs: the same hub process's roster, omitting F, recorded after the one naming
        it. At the thirty-second commit that omission released F's word, and the session live on F answered [true, 5,
        no-reachable-host-names-it] while the hub and C vouched. The omission came by our dial's road and the naming by
        the hub's dial, whose rosters this bus cannot order against each other, so the word stays held, stamped with the
        road that named it: cannot-determine, naming the hub's word about F."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["olderAnswerFoldedLate"]
                self.assertEqual((road["restartDial"], road["olderAnswerVia"]), ([200, True, [S["hubsid"]]], []),
                                 "the restarted hub's answer to our dial, taken before it heard F, omits F")
                self.assertEqual((road["landingAtHub"]["reqAnswered"], road["landingHere"]["acks"]), (False, ["px-hub12"]),
                                 "the new session's mail rode F's CACHED exchange with the restarted hub and landed here")
                self.assertEqual(self._road(got, "olderAnswerFoldedLate", "newerDialRecorded", "newOnFar"), via)
                self.assertEqual((self._road(got, "olderAnswerFoldedLate", "olderAnswerFolded", "newOnFar"),
                                  self._road(got, "olderAnswerFoldedLate", "olderAnswerFolded", "nobody"),
                                  self._road(got, "olderAnswerFoldedLate", "olderAnswerFolded", "other")), (via, via, RULE_4),
                                 "HELD: the older answer's omission came by our dial's road, and the hub's dial named F (at the "
                                 "thirty-second commit [true, 5, no-reachable-host-names-it] for the session live on F)")
                self.assertEqual(road["heldAfterFold"], [[R_F, S["other"], "dial"]],
                                 "the word held on the hub's row, stamped with the road that named F")

    def test_cost_h_a_far_hosts_word_named_on_the_hubs_dial_stays_held_across_our_dials_until_the_hubs_next_dial_omits_it(self):
        """COST (h), disclosed on the restricted side (the writer's docstring): the road above continues. F answers the
        hub with an EMPTY listing, its sessions all ended; two of OUR dials reach the hub, whose answers omit F, and the
        word stays held, every sid on this machine at cannot-determine, since those omissions came by our dial's road and
        the hub's dial named F; the hub's next dial omits F on that road: the release, rule 5. A hub whose dials stop
        reaching this bus leaves the word held until it names F again, F's own row speaks for F here, or this bus
        restarts."""
        S = ROAD_SIDS
        via = UNANSWERED(R_VIA_F + " (listing unanswered)")
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                road = got["roads"]["olderAnswerFoldedLate"]
                self.assertEqual((self._road(got, "olderAnswerFoldedLate", "ourDialsOmitF", "newOnFar"),
                                  self._road(got, "olderAnswerFoldedLate", "ourDialsOmitF", "nobody"),
                                  road["heldAfterOurDials"]), (via, via, [[R_F, S["other"], "dial"]]),
                                 "COST (h): our dials' answers omit F, not on the road that named it, and the word stays held")
                self.assertEqual((self._road(got, "olderAnswerFoldedLate", "hubDialOmitsF", "newOnFar"),
                                  self._road(got, "olderAnswerFoldedLate", "hubDialOmitsF", "nobody"),
                                  road["heldAfterHubDial"]), (RULE_5, RULE_5, []),
                                 "THE RELEASE: the hub's next dial omits F on the road that named it")

    def test_residual_3d_an_older_roster_recorded_after_a_newer_one_stands_and_its_session_answers_rule_5(self):
        """RESIDUAL (3d), disclosed and NOT closed (the writer's docstring): the latest roster RECORDED here stands, and a
        roster can reach this bus after a newer one from the same source. Three faces, each a session started during
        its host's blink whose mail rode the newer, cached roster here (the arm, cannot-determine), then the older roster
        recorded: (1) by the SAME road, two of the restarted hub's dials delivered in the other order (a hub that links
        this bus under two names dials it from two loops, and a request the hub gave up on can arrive after the next
        one), the older omitting F: the release of F's held word (the road's condition holds), rule 5; (2) the verifier's
        R2 at the thirty-second commit, the hub's older answer to our dial naming F's ANSWERED word folded after the
        hub's dial naming F's cached word: F's word answered, rule 5; (3) the same for a peer's own row, B's older answer
        to our dial folded after B's cached dial: rule 5. Faces (2) and (3) read rule 5 at the round's base as well.
        Closing it needs the source's own order on its rosters, an exchange-field change outside this fix-tier PR; these
        witnesses assert the rule-5 answer, so they turn red when it closes and the disclosure moves with it."""
        S = ROAD_SIDS
        for shape, got in self.roads.items():
            with self.subTest(shape=shape):
                same = got["roads"]["hubDialsOutOfOrder"]
                self.assertEqual((same["olderDialVia"], same["landingHere"]["acks"], same["olderDialStatus"]), ([], ["px-hub13"], 200),
                                 "the older dial, built before the restarted hub heard F, lands after the newer one and its mail")
                self.assertEqual(self._road(got, "hubDialsOutOfOrder", "newerDialRecorded", "newOnFar"),
                                 UNANSWERED(R_VIA_F + " (listing unanswered)"))
                self.assertEqual((self._road(got, "hubDialsOutOfOrder", "olderDialLanded", "newOnFar"), same["heldAfter"]),
                                 (RULE_5, []),
                                 "RESIDUAL (3d), face (1), HOLDS: the older dial's omission, by the road that named F, releases "
                                 "the word; when this pin reds, the source's order has closed the residual")
                word = got["roads"]["olderAnsweredWordFoldedLate"]
                self.assertEqual(word["olderAnswerVia"], [[R_F, S["other"], True]], "the hub's older answer: F's answered word")
                self.assertEqual(self._road(got, "olderAnsweredWordFoldedLate", "newerDialRecorded", "newOnFar"),
                                 UNANSWERED(R_VIA_F + " (listing unanswered)"))
                self.assertEqual((self._road(got, "olderAnsweredWordFoldedLate", "olderAnswerFolded", "newOnFar"),
                                  self._road(got, "olderAnsweredWordFoldedLate", "olderAnswerFolded", "other")), (RULE_5, RULE_4),
                                 "RESIDUAL (3d), face (2), HOLDS: F's older answered word stands, and the session live on F "
                                 "answers rule 5")
                self.assertEqual(got["roads"]["olderAnsweredRowFoldedLate"]["landing"]["acks"], ["px-b15"])
                self.assertEqual(self._road(got, "olderAnsweredRowFoldedLate", "newerDialRecorded", "newOnB"),
                                 UNANSWERED(R_B + " (listing unanswered)"))
                self.assertEqual((self._road(got, "olderAnsweredRowFoldedLate", "olderAnswerFolded", "newOnB"),
                                  self._road(got, "olderAnsweredRowFoldedLate", "olderAnswerFolded", "other")), (RULE_5, RULE_4),
                                 "RESIDUAL (3d), face (3), HOLDS: B's older answered roster stands, and the session live on B "
                                 "answers rule 5")

    def test_a_peer_mode_beat_vouches_for_presence_alone_and_the_legacy_scheme_keeps_its_ttl_vouch(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' finding (the peer-mode beat phase of the class
        docstring): the real recorder files a local session's beat as remote presence while this bus's listing does not
        answer, and in peer mode that row vouches for presence alone, so a restarted bus that has heard no host answers
        cannot-determine for a sid nothing names, not rule 5; the same beat beside a peer the kernel holds down vouches for
        nothing (the blink phantom); under the legacy singleton scheme the same rows vouch by the TTL, as ruled in round 1;
        and the recorder keeps the key once the listing calls the sid local (the refused pop). The verdicts first, then the
        rows, on both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        beat = self.HB + BLINK_BEAT
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory12"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the twelfth restart is a fresh module object, its memory and its link table empty")
                self.assertIs(got["beatRecordedLocal"], False,
                              "the listing did not answer: the beat is recorded, never called local from the client's claim")
                p = got["peerBeat"]
                self.assertIs(p["scheme"], True, "peer mode, read back through the bus's own peers_on")
                self.assertEqual(self._v(p, "nobody"), NO_VOUCH(beat + " (no link state)"),
                                 "THE RULED ROAD: a restarted bus in peer mode with one live local beat and no host heard answers "
                                 "cannot-determine for a sid nothing names, the reason naming the beat (a writer vouching a "
                                 "heartbeat by its TTL whatever the scheme answers (True, 5, no-reachable-host-names-it) here, "
                                 "within 90 s of a local session's beat filed during a listing blink)")
                self.assertEqual(self._v(p, "beat"), RULE_4, "the beating sid is named by a reachable row")
                self.assertEqual(p["hosts"], {beat: L(True, False, False, False, True, False, [BLINK_BEAT])},
                                 "the recorder's own write: one row, heard, reachable, vouching for presence alone")
                up = got["peerBeatBesideUp"]
                self.assertEqual((self._v(up, "nobody"), self._v(up, "beat"), self._v(up, "other")), (RULE_5, RULE_4, RULE_4),
                                 "B heard with its link up vouches: rule 5 for a sid nothing names; the beat is not a gate on the "
                                 "mirror, and its sid stays rule 4's")
                down = got["peerBeatBesideDown"]
                self.assertEqual(self._v(down, "nobody"), NO_VOUCH(HOST2 + " (link down)", beat + " (no link state)"),
                                 "THE BLINK PHANTOM beside a down peer: nothing vouches for absence (the TTL vouch answered rule 5 "
                                 "here while the only peer's link was down, the refuter's adjacent road)")
                self.assertEqual((down["hosts"][beat], down["hosts"][HOST2]),
                                 (L(True, False, False, False, True, False, [BLINK_BEAT]), L(True, False, True, False, False, False, [OTHER])),
                                 "the beat reachable and vouching for presence alone; B held down")
                legacy = got["legacyBeatBesideDown"]
                self.assertIs(legacy["scheme"], False, "the legacy singleton scheme, read back")
                self.assertEqual(self._v(legacy, "nobody"), RULE_5,
                                 "LEGACY KEEPS TTL VOUCHING (round 1's ruling): the beat, a remote session's only presence there, "
                                 "vouches for absence whatever B's link (a writer withholding the vouch in both schemes answers "
                                 "cannot-determine here; one reading the switch inverted vouched in peer mode and not here)")
                self.assertEqual(legacy["hosts"][beat], L(True, False, False, False, True, True, [BLINK_BEAT]))
                again = got["peerBeatAgain"]
                self.assertEqual((again["scheme"], self._v(again, "nobody")),
                                 (True, NO_VOUCH(HOST2 + " (link down)", beat + " (no link state)")),
                                 "the scheme is read at each write and nothing is stored on the row: peer mode again, "
                                 "cannot-determine again")
                unowned = got["peerBeatUnowned"]
                self.assertEqual((unowned["keyKept"], unowned["hosts"][beat], self._v(unowned, "beat")),
                                 (True, L(True, False, False, False, True, False, [BLINK_BEAT]), RULE_4),
                                 "an answered listing that does not own the beating sid releases nothing: the row and the entry stay "
                                 "(a writer dropping a row the listing does not own drops it here)")
                self.assertIs(got["beatConfirmedLocal"], True, "the listing answered naming the session: local")
                local = got["peerBeatLocal"]
                self.assertIs(local["keyKept"], False,
                              "THE RULED RELEASE (the seventeenth commit): the write after a listing this bus read answered and owns "
                              "the sid drops the row and forgets the entry (rules 1 and 2 own that sid); the sixteenth commit kept "
                              "both, refusing a pop in the recorder that left the carry a key to re-file")
                self.assertEqual(local["hosts"], {HOST2: L(True, False, True, False, False, False, [OTHER])},
                                 "the beat's row is gone; B's row, held down, is the whole mirror")
                self.assertEqual(self._v(local, "beat"), NO_VOUCH(HOST2 + " (link down)"),
                                 "the sid is in no row and no reason (on a real root rules 1 and 2 answer for it, its transcript "
                                 "being local; this child's HOME is empty, so the ladder shows the mirror's answer, naming B alone)")
                back = got["peerBeatLocalBlinkAgain"]
                self.assertEqual((back["keyKept"], back["hosts"]), (False, {HOST2: L(True, False, True, False, False, False, [OTHER])}),
                                 "a blink's bare write after the release does not bring the row back: no memory and no file carries "
                                 "it (a writer that dropped the row and kept the key re-emits it here)")

    def test_the_release_reaches_heartbeat_rows_alone_and_a_carried_legacy_list_naming_an_owned_sid_protects_its_other_sid(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the seventeenth commit (the release's reach phase of the class
        docstring): the writer's one release drops a heartbeat row whose sid the answered local listing owns, and nothing
        else. A carried whitespace list naming that sid beside a session on a host this process has not heard yet is carried
        whole, so while B vouches for absence the session is cannot-determine by the list's last word, never rule 5. A carry
        with its kind test deleted passed every earlier pin and answers rule 5 here (the verifier's false rule 5, by
        execution through this writer and this reader). The verdicts first, then the rows, on both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["restartMemory13"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the thirteenth restart is a fresh module object, its memory and its link table empty")
                self.assertEqual(got["reachOwned"], [BLINK_BEAT], "the listing answered, owning the local session")
                reach = got["releaseReach"]
                self.assertEqual(self._v(reach, "legacyNamed"), LOST(LEGACY + " (not heard)"),
                                 "THE RELEASE'S REACH: the list is carried whole, so the session on the unheard host is named by it "
                                 "and cannot-determine (a carry releasing every row kind that names an owned sid drops the list and "
                                 "answers (True, 5, no-reachable-host-names-it) here: a live session presumed closed on B's word)")
                self.assertEqual(self._v(reach, "nobody"), RULE_5,
                                 "B vouches for absence, so the verdict above is the list's protection and not a mirror nobody vouches in")
                self.assertEqual(self._v(reach, "owned"), LOST(LEGACY + " (not heard)"),
                                 "the owned local session is named by the list too (on a real root rules 1 and 2 answer for it first)")
                self.assertEqual(reach["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  LEGACY: L(False, False, False, False, False, False, [BLINK_BEAT, LEGACY_NAMED])},
                                 "B heard, its link up, vouching; the list carried heard=false with both of its sids")

    def test_the_release_reaches_heartbeat_rows_alone_in_memory_and_a_heard_via_row_naming_an_owned_sid_protects_its_other_sid(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the eighteenth commit (the release's reach phase of the class
        docstring, in memory): the writer's one release drops a heartbeat row whose sid the answered local listing owns, and
        no heard row of another kind. A heard hub's word about a far host naming that sid beside a session live there is
        written whole, so while B vouches for absence the far session is rule 4's by the via row, never rule 5. A writer
        dropping the heard via row passed every earlier pin and answers rule 5 here (the verifier's false rule 5, by execution
        through this writer and this reader). The verdicts first, then the rows, on both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(got["reachMemoryDialStatus"], 200, "B's exchange landed through the real handler")
                self.assertEqual(got["reachMemoryOwned"], [BLINK_BEAT], "the listing answered, owning the local session")
                reach = got["releaseReachMemory"]
                self.assertEqual(self._v(reach, "viaNamed"), RULE_4,
                                 "THE RELEASE'S REACH IN MEMORY: B's heard word about the spoke is written whole, so the spoke's "
                                 "session is named by a reachable source (a writer releasing a heard via row that names an owned sid "
                                 "drops the row and answers (True, 5, no-reachable-host-names-it) here: a live session presumed closed "
                                 "on B's word)")
                self.assertEqual(self._v(reach, "nobody"), RULE_5,
                                 "B vouches for absence, so the verdict above is the via row's protection and not a mirror nobody vouches in")
                self.assertEqual(self._v(reach, "owned"), RULE_4,
                                 "the owned local session is named by B's word too (on a real root rules 1 and 2 answer for it first)")
                self.assertEqual(reach["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  "via:" + HOST2 + "/" + SPOKE: L(True, False, False, True, True, True, [BLINK_BEAT, VIA_NAMED]),
                                                  LEGACY: L(False, False, False, False, False, False, [LEGACY_NAMED])},
                                 "B heard, its link up, vouching; its word about the spoke a heard via row with both sids; the carried "
                                 "list keeps the sid no heard row names")

    def test_bytes_that_are_not_utf8_at_the_bus_path_are_unparsable_and_the_next_write_replaces_them(self):
        """Round 3 of fork PR #897, the reviewer's ruling, the twentieth commit (the bytes half of the mirror's bytes and
        version phase of the class docstring): the reader answers cannot-determine for a file that is not UTF-8, said once
        naming the file, and the restarted writer's next write replaces it from memory, carrying nothing; one stray byte
        inside the sid a vouching host names is unparsable, never read as naming another sid. On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                read = got["bytesRead"]
                self.assertEqual((self._v(read, "nobody"), self._v(read, "other")), (UNPARSABLE, UNPARSABLE),
                                 "bytes that are not UTF-8 at the bus's path: the unparsable arm for every sid (a reader decoding "
                                 "outside its parse try raises UnicodeDecodeError out of the ladder, recorded as 'raised')")
                self.assertEqual(len(read["log"]), 1, "said once in the judge's log: %r" % read["log"])
                self.assertIn(got["busFile"], read["log"][0], "the line names the file")
                self.assertIn("UnicodeDecodeError", read["log"][0], "the line says what failed")
                self.assertEqual(got["restartMemory14"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the fourteenth restart is a fresh module object, its memory and its link table empty")
                wrote = got["bytesWritten"]
                self.assertNotEqual(self._v(wrote, "nobody"), RULE_5, "the garbage is no document at v 2 after the replacing "
                                    "decode, a file the writer cannot read whole: a sid nothing names is never rule 5's while the "
                                    "mark stands (the reviewer's ruling of 14:57Z, the twenty-second commit)")
                self.assertIn("UnicodeDecodeError", (wrote["mark"] or {}).get("cause", ""), "the document is marked with the "
                              "cause: %r" % wrote["mark"])
                self.assertEqual((self._v(wrote, "nobody"), self._v(wrote, "other")), (CARRY_LOST(wrote["mark"]), RULE_4),
                                 "the restarted writer replaced the garbage: B names its sid, and a sid nothing names is "
                                 "not established while the mark stands (a previous-read whose decode error passes its catch fails "
                                 "every write, and the reader still meets the garbage)")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER])},
                                 "the garbage carried nothing: B's row alone (a replacing decode handed to the whitespace parser "
                                 "carries IHDR and tEXt as a legacy row)")
                stray = got["strayByte"]
                self.assertEqual((self._v(stray, "other"), self._v(stray, "nobody")), (UNPARSABLE, UNPARSABLE),
                                 "one stray byte inside the sid B names: the unparsable arm (a decode with errors='replace' reads "
                                 "B as naming another sid, and B, vouching, answers (True, 5, no-reachable-host-names-it) for the "
                                 "sid it named)")

    def test_a_document_nested_past_the_parsers_depth_is_unparsable_and_the_next_write_replaces_it(self):
        """Round 3 of fork PR #897, the twentieth commit, found by its builder in the class of the bytes: a document nested past
        the JSON parser's depth raised RecursionError on this box, which is not a ValueError, so the reader raised it out of the
        ladder and the writer's previous-read failed every write. Both parses catch it: the reader answers unparsable, said once,
        and the writer's next write replaces the file, carrying nothing. On both root shapes. THE CLASS IS DERIVED (the
        reviewer's ruling of 17:47Z, the twenty-fifth commit): since 3.14 the parser's depth guard depends on the machine's stack,
        and a CI runner's 3.14t parsed the 100000 levels and raised JSONDecodeError at the end, so the child parses the same
        bytes in the same interpreter (nested_parse_raises) and the line and the mark must name the class that parse raised; a
        parse that returns fails this case, naming the interpreter and the depth. That the product catches both classes is
        pinned once, by test_the_writers_previous_read_and_the_reader_catch_both_classes_a_nested_parse_can_raise. The check
        that the parse raised requires a class name, an identifier, and the line and the mark are read for the class in the
        "(<class>: " slot the product fills from the exception it caught (the reviewer's verifier at the twenty-fifth commit,
        the twenty-sixth): with nested_parse_raises made to return the empty name for a parse that returns, a check reading
        only "not None" passed, and the empty name is found in every line."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                raised, depth, version = got["deepParse"]
                self.assertTrue(isinstance(raised, str) and raised.isidentifier(), "json.loads returned on the document nested "
                                "%d deep on %s (derived %r, not a class name): the case's premise, a file the parse cannot read, "
                                "is gone" % (depth, version, raised))
                read = got["deepRead"]
                self.assertEqual((self._v(read, "nobody"), self._v(read, "other")), (UNPARSABLE, UNPARSABLE),
                                 "nesting past the parser's depth: the unparsable arm for every sid (a reader catching ValueError "
                                 "alone raises RecursionError out of the ladder, recorded as 'raised')")
                self.assertEqual(len(read["log"]), 1, "said once: %r" % read["log"])
                self.assertIn("(%s: " % raised, read["log"][0], "the line says what failed, the class this interpreter's parse "
                              "raised")
                wrote = got["deepWritten"]
                self.assertNotEqual(self._v(wrote, "nobody"), RULE_5, "a file the writer cannot read whole: a sid nothing names "
                                    "is never rule 5's while the mark stands (the twenty-second commit)")
                self.assertIn("(%s: " % raised, (wrote["mark"] or {}).get("cause", ""), "the document is marked with the cause, "
                              "the class this interpreter's parse raised: %r" % wrote["mark"])
                self.assertEqual((self._v(wrote, "nobody"), self._v(wrote, "other")), (CARRY_LOST(wrote["mark"]), RULE_4),
                                 "the writer replaced the file (a previous-read catching ValueError alone fails every write); a sid "
                                 "nothing names is not established while the mark stands")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER])},
                                 "the nested document carried nothing: B's row alone")

    def test_the_writers_previous_read_and_the_reader_catch_both_classes_a_nested_parse_can_raise(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 17:47Z, the twenty-fifth commit (the both classes phase of the
        class docstring): the class json.loads raises on a document nested past its depth is the interpreter's, RecursionError
        on this box and JSONDecodeError, a ValueError, on a CI runner's 3.14t, so the three cases that plant one derive the class
        from the parse, and this test pins, once, that the product catches both. json.loads stubbed to raise each class in turn
        on the nested document: the writer's previous-read (postal_service.py _remote_sids_previous) carries nothing and marks
        the document with that class in the cause, and the reader (judge.py _remote_sids_mirror) answers unparsable, said once
        naming that class. A catch narrowed to ValueError alone lets the stubbed RecursionError out of either, recorded as
        'raised', where on an interpreter that raises JSONDecodeError the three cases stay green. On both root shapes."""
        for shape, got in self.got.items():
            for cls in ("ValueError", "RecursionError"):
                with self.subTest(shape=shape, raised=cls):
                    both = got["catchBoth"][cls]
                    self.assertIsInstance(both["previous"], dict, "the writer's previous-read caught the stubbed %s (a catch "
                                          "narrowed to ValueError alone lets RecursionError out): %r" % (cls, both["previous"]))
                    self.assertEqual(both["previous"]["hosts"], {}, "the nested document carries nothing")
                    self.assertIn("(%s: stubbed" % cls, (both["previous"]["mark"] or {}).get("cause", ""),
                                  "the document is marked with the class in the cause: %r" % both["previous"])
                    self.assertEqual(self._v(both, "verdict"), UNPARSABLE, "the reader answers unparsable (a reader catching "
                                     "ValueError alone raises RecursionError out of the ladder, recorded as 'raised')")
                    self.assertEqual(len(both["log"]), 1, "said once: %r" % both["log"])
                    self.assertIn("(%s: stubbed" % cls, both["log"][0], "the line names the class")

    def test_a_carried_rows_values_of_the_wrong_types_are_coerced_never_dropped(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' corrections, the twentieth commit (the foreign rows
        of the mirror's bytes and version phase): a hand-written document whose rows carry a non-bool flag, an unhashable busId
        and an unhashable sid is refused by the reader, and the writer's next write carries the three rows with their values
        coerced (bool() of each flag, str() of each sid, the busId ignored), so each sid they name is cannot-determine by its
        row while B vouches, never rule 5. The verdicts first, then the rows, on both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._v(got["foreignRowsRead"], "nobody"), UNPARSABLE,
                                 "the hand-written document is not the bus's shape (a row whose flags are not booleans): refused")
                wrote = got["foreignRowsWritten"]
                self.assertEqual(self._v(wrote, "carried"), LOST(HOST + " (not heard, expired)"),
                                 "the row with the non-bool flags is carried, coerced ('yes' reads expired), and holds its sid (a "
                                 "writer that drops it answers (True, 5, no-reachable-host-names-it) here: a live session presumed "
                                 "closed on B's word; one that copies the values leaves the mirror unparsable)")
                self.assertEqual(self._v(wrote, "farSid"), LOST(ALIAS + " (not heard)"),
                                 "the row with the unhashable busId is carried and holds its sid (a carry testing that busId for set "
                                 "membership fails every write, and the reader meets the hand-written document: unparsable)")
                self.assertEqual(self._v(wrote, "later"), LOST(LEGACY + " (not heard)"),
                                 "the list with the unhashable sid is carried and holds the live session's sid (a filter testing "
                                 "that sid for set membership fails every write)")
                self.assertEqual((self._v(wrote, "nobody"), self._v(wrote, "other")), (RULE_5, RULE_4),
                                 "B vouches for absence, so the verdicts above are the carried rows' protection")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  HOST: L(False, True, False, False, False, False, [CARRIED]),
                                                  ALIAS: L(False, False, False, False, False, False, [FARSID]),
                                                  LEGACY: L(False, False, False, False, False, False, [LATER])},
                                 "B heard and vouching; the three rows carried heard=false, their values coerced, and the text of "
                                 "the unhashable value, which is no session id, dropped (the twenty-second commit, the reviewer's "
                                 "ruling of 14:57Z: every carried sid validated)")

    def test_a_document_of_another_version_is_unparsable_and_the_writer_carries_its_roster(self):
        """Round 3 of fork PR #897, the reviewer's ruling, the twentieth commit (the version half of the mirror's bytes and
        version phase): a document at v 1, and one with no v, whose row names a sid and vouches for absence, is refused by the
        reader, said once each; the writer's next write over the one with no v carries its roster, heard=false, and stamps
        v 2, so that sid is cannot-determine by its row while B vouches. On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                for key, v in (("v1Read", 1), ("noVRead", None)):
                    read = got[key]
                    self.assertEqual((self._v(read, "carried"), self._v(read, "nobody")), (UNPARSABLE, UNPARSABLE),
                                     "a document at v %r whose row names the sid and vouches: the unparsable arm (a reader that "
                                     "never reads `v` answers rule 4 and rule 5 here)" % (v,))
                    self.assertEqual(len(read["log"]), 1, "said once: %r" % read["log"])
                    self.assertIn("version is %r, not 2" % (v,), read["log"][0], "the line says the version")
                wrote = got["versionWritten"]
                self.assertEqual(wrote["v"], 2, "the writer stamps v 2")
                self.assertEqual((self._v(wrote, "carried"), self._v(wrote, "nobody")), (LOST(HOST + " (not heard)"), RULE_5),
                                 "the document's roster carried whatever its version: the sid it named is held by the carried "
                                 "row while B vouches (a carry that dropped another version's rows answers rule 5 for it)")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  HOST: L(False, False, False, False, False, False, [CARRIED])},
                                 "B heard and vouching; the row from the document with no v carried heard=false")

    def test_one_bad_byte_in_the_previous_file_costs_one_sid_and_the_carried_row_holds_the_other_hosts_session(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twentieth commit, by execution through this writer and this
        reader, and the reviewer's ruling of 14:57Z, clause 1 (the twenty-second commit): host A is heard with its link up
        beside B; one byte inside the sid B names becomes a stray byte in the writer's own document; the bus restarts and
        hears B first. The previous-read decodes with replacement for its JSON parse, drops the one sid that fails the
        session-id shape and carries every other row, so A's row is carried and A's live session is held by A's last word
        while B vouches, never rule 5; the bus log says once which file and how many. At the twenty-first commit the strict
        read carried nothing and A's session answered (True, 5, no-reachable-host-names-it) here, the road the ruling closed.
        On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                before = got["unreadBefore"]
                self.assertEqual((self._v(before, "carried"), self._v(before, "other")), (RULE_4, RULE_4),
                                 "before the restart A and B are heard, each naming its session")
                self.assertEqual(got["restartMemory15"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the fifteenth restart is a fresh module object, its memory and its link table empty")
                wrote = got["unreadWritten"]
                self.assertEqual(self._v(wrote, "carried"), LOST(HOST + " (not heard)"),
                                 "A's row carried: A's live session, which the new process has not heard, is held by A's last word "
                                 "while B vouches (a strict read carries nothing and answers (True, 5, no-reachable-host-names-it) "
                                 "here: the verifier's road)")
                self.assertEqual((self._v(wrote, "other"), self._v(wrote, "nobody")), (RULE_4, RULE_5),
                                 "B heard, vouching and naming its session; no mark, so a sid nothing names is rule 5's")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  HOST: L(False, False, False, False, False, False, [CARRIED])},
                                 "B's row from memory and A's carried: one bad byte cost one sid, never the document")
                self.assertIsNone(wrote["mark"], "the document was read: no mark")
                said = [ln for ln in wrote["busLog"] if "previous remote-sids mirror" in ln]
                self.assertEqual(len(said), 1, "said once: %r" % wrote["busLog"])
                self.assertIn(got["busFile"], said[0], "the line names the file")
                self.assertIn("1 session id(s) not in the session-id shape and 0 row(s)", said[0], "the line says how many")
                self.assertIn("UnicodeDecodeError", said[0], "the line says the bytes were not UTF-8")
                self.assertEqual([ln for ln in wrote["busLog"] if "not written" in ln or "is unreadable" in ln], [],
                                 "every write landed, and no whole-file line")
                self.assertEqual(self._v(got["unreadAHeard"], "carried"), RULE_4, "A heard in the new process: its own row names it")

    def test_a_byte_order_mark_is_read_by_the_reader_and_carried_by_the_writer(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clause 1 (the twenty-second commit): the writer's own document
        behind a byte-order mark is read by the reader (until the commit: mirror-unparsable, 'Unexpected UTF-8 BOM') and, after a
        sixteenth restart with B heard first, carried by the writer (until the commit the previous-read refused it, carried
        nothing, and A's live session answered (True, 5) while B vouched). On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                read = got["bomRead"]
                self.assertEqual((self._v(read, "carried"), self._v(read, "other"), self._v(read, "nobody")),
                                 (RULE_4, RULE_4, RULE_5), "the reader reads the document behind the mark (a strict utf-8 decode "
                                 "answers mirror-unparsable for all three)")
                self.assertEqual(read["log"], [], "nothing said in the judge's log")
                self.assertEqual(got["restartMemory16"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the sixteenth restart is a fresh module object")
                wrote = got["bomWritten"]
                self.assertEqual((self._v(wrote, "carried"), self._v(wrote, "other"), self._v(wrote, "nobody")),
                                 (LOST(HOST + " (not heard)"), RULE_4, RULE_5),
                                 "A's row carried through the mark: its session held by its last word while B vouches (a "
                                 "previous-read refusing the mark answers (True, 5) for it)")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER]),
                                                  HOST: L(False, False, False, False, False, False, [CARRIED])},
                                 "B's row from memory, A's carried")
                self.assertIsNone(wrote["mark"], "read, so no mark")
                self.assertEqual([ln for ln in wrote["busLog"] if "previous remote-sids mirror" in ln], [], "nothing said")

    def test_a_previous_file_the_bus_cannot_read_whole_marks_the_mirror_until_every_linked_host_is_heard(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clauses 2 and 3 (the twenty-second commit), through this
        writer and this reader. A heard beside B; the writer's own document made not JSON (a stray brace); a seventeenth restart
        whose seed reads the kernel's list with both links up (the real seed, its transport stubbed), whose own writes read the
        file and mark the mirror; B heard first, A linked and not heard. The mark carries the cause and the write's second;
        A's live session, whose row is lost, and a sid nothing names are both NOT ESTABLISHED (at the twenty-first commit both
        answered (True, 5, no-reachable-host-names-it), a false rule 5 under a loud log line, the shape the reviewer refused),
        and B's session is rule 4's. An eighteenth restart whose seed fails: B and A notified one at a time and heard, every
        host PEERS holds heard, and the mark stands (PEERS may not be the kernel's whole list: a clearing without the seed drops
        it here). A nineteenth restart whose seed reads the list: B heard, A linked and not heard, the mark stands (a clearing
        on a single host heard drops it here); A heard, the last linked host heard since the mark: cleared, said once, and rule
        5 answers again. On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                before = got["lostBefore"]
                self.assertEqual((self._v(before, "carried"), self._v(before, "other")), (RULE_4, RULE_4),
                                 "before the restart A and B are heard, each naming its session")
                self.assertEqual(got["restartMemory17"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the seventeenth restart is a fresh module object")
                wrote = got["lostWritten"]
                self.assertEqual([self._v(wrote, "carried")[:2], self._v(wrote, "nobody")[:2]], [(False, None), (False, None)],
                                 "A's live session, its row lost, and a sid nothing names: not established, never rule 5 (at the "
                                 "twenty-first commit both answered (True, 5, no-reachable-host-names-it): %r"
                                 % [wrote["carried"], wrote["nobody"]])
                self.assertTrue(got["lostSeeded"], "the seed read the kernel's list")
                mark = wrote["mark"]
                self.assertIsInstance(mark, dict, "the mirror is marked: %r" % (mark,))
                self.assertEqual(sorted(mark), ["at", "cause"], "the mark's shape")
                self.assertTrue(mark["cause"].startswith("previous mirror unreadable (JSONDecodeError"), "the cause: %r" % mark)
                self.assertTrue(got["lostFloor"] <= mark["at"] <= got["lostCeiling"], "the write's second: %r" % mark)
                self.assertEqual((self._v(wrote, "carried"), self._v(wrote, "nobody")), (CARRY_LOST(mark), CARRY_LOST(mark)),
                                 "A's live session, its row lost, and a sid nothing names: not established while the mark stands "
                                 "(a writer that writes no mark, or a reader that ignores it, answers (True, 5) for both)")
                self.assertEqual(self._v(wrote, "other"), RULE_4, "rule 4 still answers: B names its session")
                self.assertEqual(wrote["hosts"], {HOST2: L(True, False, False, True, True, True, [OTHER])},
                                 "no row carried from the file: B's row alone")
                said = [ln for ln in wrote["busLog"] if "previous remote-sids mirror" in ln]
                self.assertEqual(len(said), 1, "said once: %r" % wrote["busLog"])
                self.assertIn(got["busFile"], said[0], "the line names the file")
                self.assertIn("is unreadable (JSONDecodeError", said[0], "the line says what failed")
                self.assertEqual(got["restartMemory18"], {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True},
                                 "the eighteenth restart is a fresh module object")
                self.assertFalse(got["lostUnseeded"], "the seed failed: nothing answered")
                noseed = got["lostNoSeed"]
                self.assertEqual(noseed["mark"], mark, "carried across a restart, the same cause and second")
                self.assertEqual((self._v(noseed, "carried"), self._v(noseed, "other"), self._v(noseed, "nobody")),
                                 (RULE_4, RULE_4, CARRY_LOST(mark)),
                                 "every host PEERS holds heard, the kernel's list never read: the mark stands (a clearing "
                                 "without the seed answers rule 5 for the sid nothing names)")
                self.assertTrue(got["lostReseeded"], "the nineteenth restart's seed read the list")
                one = got["lostOneHeard"]
                self.assertEqual(one["mark"], mark, "carried across a further restart")
                self.assertEqual((self._v(one, "carried"), self._v(one, "other"), self._v(one, "nobody")),
                                 (LOST(HOST + " (not heard)"), RULE_4, CARRY_LOST(mark)),
                                 "B heard, A linked and not heard since the mark: the mark stands (a clearing on one host heard "
                                 "answers rule 5 for the sid nothing names)")
                cleared = got["lostCleared"]
                self.assertIsNone(cleared["mark"], "A heard, the last linked host heard since the mark: cleared")
                self.assertEqual((self._v(cleared, "carried"), self._v(cleared, "other"), self._v(cleared, "nobody")),
                                 (RULE_4, RULE_4, RULE_5), "rule 5 answers again (a mark never cleared answers carry-lost here)")
                said = [ln for ln in cleared["busLog"] if "lost-carry mark" in ln]
                self.assertEqual(len(said), 1, "the clearing said once: %r" % cleared["busLog"])
                self.assertIn(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mark["at"])), said[0], "naming the mark's second")
                self.assertIn(FIRST_START, said[0], "and stating the ruled bound (the reviewer's ruling of 15:45Z)")
                remembered = got["lostRemembered"] or {}
                self.assertEqual((remembered.get("originOnly"), remembered.get("port")), (True, None),
                                 "the seed applied the kernel's remembered unattached host as an origin-only row, no port, "
                                 "never heard: the clearing above holds only because such a row is no link (the reviewer's "
                                 "verifier at the twenty-second commit: counted as a link, the mark never clears): %r"
                                 % (got["lostRemembered"],))

    def test_a_cleared_mark_does_not_reach_a_far_hosts_session_a_restarted_hub_no_longer_names(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twenty-second commit, by execution, and the reviewer's ruling
        of 15:45Z (postal_service.py _remote_sids_lost_cleared): a session on a host that no linked host hears now is outside
        every source after the clear, as on a first start. This phase is the CONTRAST with the intact file, beside a second
        link, through this writer and this reader, so a clearing rule that reaches the road, or one that widens it, turns it
        red. B, a linked hub beside A, names a session on the spoke, a far host never linked here (rule 4 by B's word). The
        file intact: a twentieth restart, seeded; A heard; B heard after its own restart, gossiping nothing about the spoke:
        the carried via row names the session, named-by-unreachable-host. B names it again (rule 4); the file made not JSON;
        a twenty-first restart, seeded, whose own writes mark the mirror; A heard; B heard after another restart of its own,
        gossiping nothing about the spoke: every linked host heard since the mark, so it clears, and the session, outside
        every source, answers rule 5. A vouches here as well as B, so this rule 5 holds on A's vouch alone (the reviewer's
        verifier at the twenty-third commit): the ruled road, B the only link, is
        test_a_hub_the_only_link_restarted_clears_the_mark_and_its_far_hosts_session_answers_rule_5_as_on_a_first_start. The
        twenty-second commit stated as fact that a hub re-gossips its via rows on its next exchange, which is false for a hub
        that has restarted; no event the bus receives names a far host whose row was lost. On both root shapes."""
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual(self._v(got["boundGossiped"], "farLost"), RULE_4, "B, heard and linked, names the spoke's session")
                self.assertEqual((got["restartMemory20"], got["boundIntactSeeded"]),
                                 ({"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True}, True),
                                 "the twentieth restart is a fresh module object, and its seed read the kernel's list")
                intact = got["boundIntact"]
                self.assertEqual((intact["mark"], self._v(intact, "farLost"), self._v(intact, "carried"), self._v(intact, "other")),
                                 (None, LOST(VIA_B_SPOKE + " (not heard)"), RULE_4, RULE_4),
                                 "the file intact, B heard after its own restart and naming nothing on the spoke: the carried "
                                 "via row names the session, cannot-determine")
                self.assertEqual(self._v(got["boundRegossiped"], "farLost"), RULE_4, "B names the session again")
                self.assertEqual((got["restartMemory21"], got["boundLostSeeded"]),
                                 ({"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True}, True),
                                 "the twenty-first restart is a fresh module object, and its seed read the kernel's list")
                mark = got["boundLostMark"]
                self.assertIsInstance(mark, dict, "the seed's own writes read the file made not JSON and marked the mirror")
                lost = got["boundLost"]
                self.assertEqual((lost["mark"], self._v(lost, "carried"), self._v(lost, "other")), (None, RULE_4, RULE_4),
                                 "A and B heard since the mark: cleared")
                self.assertEqual(self._v(lost, "farLost"), RULE_5,
                                 "AS ON A FIRST START: once the mark clears, the spoke's session, whose via row the lost file "
                                 "held and which no linked host hears now, is outside every source and answers rule 5, where "
                                 "the intact file answers named-by-unreachable-host (a clearing rule that reaches this road "
                                 "turns this red, and the docstrings move with it)")
                said = [ln for ln in lost["busLog"] if "lost-carry mark" in ln]
                self.assertEqual(len(said), 1, "the clearing said once: %r" % lost["busLog"])
                self.assertIn(FIRST_START, said[0], "the clearing line states the ruled bound")
                self.assertIn(CLEARED_RULE_5, said[0], "and its consequence, rule 5's whole condition (until the thirtieth commit "
                              "the line stopped at the vouch and left out the listing-unanswered arm)")

    def test_a_hub_the_only_link_restarted_clears_the_mark_and_its_far_hosts_session_answers_rule_5_as_on_a_first_start(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 15:45Z, clause 5: THE NAMED WITNESS of the ruled road, through
        this writer and this reader (the twenty-fourth commit). A session on a host that no linked host hears now is outside
        every source after the clear, as on a first start. A twenty-third restart seeded with B alone, the ONLY link (the
        remembered unattached host is an origin-only row, no link); B, a hub, names a session on the spoke, a far host never
        linked here (rule 4 by B's word); the file made not JSON; a twenty-fourth restart seeded with B alone, whose own writes
        mark the mirror; B heard after its own restart, no longer hearing the spoke: B, the last linked host, heard since the
        mark, so it clears; B's row is the one row, heard, its link up, vouching for absence; and the spoke's session answers
        rule 5 on B's vouch, as a sid nothing names does. A twenty-fifth restart over NO file, a first start seeded with B
        alone, B heard the same way: the same rows and the same verdicts, so the mirror after the clear knows what a fresh bus
        knows. The two-link phase before this one cannot show the road: A vouches there too (the reviewer's verifier at the
        twenty-third commit). On both root shapes."""
        L = lambda heard, expired, down, up, reach, vouch, sids: [heard, expired, down, up, reach, vouch, sids]
        fresh = {"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True}
        b_alone = {HOST2: L(True, False, False, True, True, True, [OTHER])}
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual((got["restartMemory23"], got["oneLinkSeeded"]), (fresh, True),
                                 "the twenty-third restart is a fresh module object, and its seed read the kernel's list")
                self.assertEqual(self._v(got["oneLinkGossiped"], "farLost"), RULE_4, "B, the only link, names the spoke's session")
                self.assertEqual((got["restartMemory24"], got["oneLinkLostSeeded"]), (fresh, True),
                                 "the twenty-fourth restart is a fresh module object, and its seed read the kernel's list")
                mark = got["oneLinkMark"]
                self.assertIsInstance(mark, dict, "the seed's own writes read the file made not JSON and marked the mirror")
                self.assertTrue(mark["cause"].startswith("previous mirror unreadable (JSONDecodeError"), "the cause: %r" % mark)
                self.assertEqual(got["oneLinkLinks"], [HOST2], "B is the only link PEERS holds (the remembered host has no port)")
                cleared = got["oneLinkCleared"]
                self.assertEqual(cleared["hosts"], b_alone,
                                 "B's row is the one row, heard, its link up, vouching for absence; no row names the spoke's "
                                 "session")
                self.assertEqual((cleared["mark"], self._v(cleared, "farLost"), self._v(cleared, "nobody"), self._v(cleared, "other")),
                                 (None, RULE_5, RULE_5, RULE_4),
                                 "B, the only link, heard since the mark: cleared, and the spoke's session, outside every source, "
                                 "answers rule 5 while B vouches (a mark never cleared answers carry-lost; a hub that does not vouch "
                                 "answers no-host-vouches-absence)")
                said = [ln for ln in cleared["busLog"] if "lost-carry mark" in ln]
                self.assertEqual(len(said), 1, "the clearing said once: %r" % cleared["busLog"])
                self.assertIn(FIRST_START, said[0], "the clearing line states the ruled bound")
                self.assertIn(CLEARED_RULE_5, said[0], "and its consequence, rule 5's whole condition (until the thirtieth commit "
                              "the line stopped at the vouch and left out the listing-unanswered arm)")
                self.assertEqual((got["restartMemory25"], got["firstStartSeeded"], got["firstStartLinks"]), (fresh, True, [HOST2]),
                                 "the twenty-fifth restart is a fresh module object over no file, seeded with B alone")
                self.assertIsNone(got["firstStartMark"], "a first start's seed writes no mark: nothing was lost")
                first = got["firstStart"]
                self.assertEqual((first["hosts"], first["mark"]), (b_alone, None), "a first start writes the same rows, no mark")
                self.assertEqual([self._v(first, k) for k in ("farLost", "nobody", "other")],
                                 [self._v(cleared, k) for k in ("farLost", "nobody", "other")],
                                 "and gives the same verdicts: the mirror after the clear knows what a fresh bus knows")

    def test_a_mark_at_second_0_clears_only_once_every_linked_host_is_heard(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twenty-second commit, by execution through this writer and
        this reader: a mark whose second is 0, which the carry and this reader accept, cleared with no host heard, because the
        clearing read a host with no seenAt as second 0 (a hand-written file, or a clock in the epoch's first second; no bus
        stamps 0). The writer's own document with A's row removed, as a lost carry leaves it, under a mark at second 0; a
        twenty-second restart, seeded; a drift note filed for A, no exchange landed, and B heard: the mark stands, and A's live
        session, in no row, is carry-lost (at the twenty-second commit, (True, 5)); A heard: cleared, rule 4 for it. On both
        root shapes."""
        zero = {"cause": "hand-written", "at": 0}
        for shape, got in self.got.items():
            with self.subTest(shape=shape):
                self.assertEqual((got["restartMemory22"], got["zeroSeeded"]),
                                 ({"heartbeats": 0, "peers": 0, "links": 0, "freshObject": True}, True),
                                 "the twenty-second restart is a fresh module object, and its seed read the kernel's list")
                b_heard = got["zeroBHeard"]
                self.assertEqual((b_heard["mark"], self._v(b_heard, "carried"), self._v(b_heard, "other")),
                                 (zero, CARRY_LOST(zero), RULE_4),
                                 "B heard, A linked with a drift note and no seenAt: the mark at second 0 stands and A's "
                                 "session is carry-lost (read as second 0, A counted as heard and the mark cleared: (True, 5))")
                a_heard = got["zeroAHeard"]
                self.assertEqual((a_heard["mark"], self._v(a_heard, "carried")), (None, RULE_4),
                                 "A heard: every linked host heard since the mark, cleared, and A names its session")

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
