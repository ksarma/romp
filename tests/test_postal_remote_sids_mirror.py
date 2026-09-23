#!/usr/bin/env python3
"""The postal bus's presence mirror (the bus's STATE/remote-sids, <state root>/postal/remote-sids), the
file kernel/judge's dead-session ladder reads for rules 4 and 5 (_presumed_closed_verdict). Since fork PR
#897's round 2 the mirror is a document, one row per PRESENCE SOURCE with the roster it last reported and
whether THIS bus process can vouch for it (postal_service.py _remote_sids_document): `heard` (a heartbeat or
exchange arrived in this process), `expired` (a legacy heartbeat past HEARTBEAT_TTL), `linkDown` (the kernel
holds its link down, or has since it was heard), `linkUp` (the kernel holds its link up and it was heard since
the link last dropped), `reachable` (heard and not expired and not linkDown: the source vouches for the
PRESENCE of the sids it names, rule 4), `vouchesAbsence` (heard and not expired and linkUp, or a legacy
heartbeat within its TTL: the source vouches for the ABSENCE of a sid it does not name, rule 5's
precondition), `sids`. The reader presumes a sid closed only when a source vouches for absence and none names
it. Two roads to a false settle closed here, at the writer:
  (1) a bus restarted from empty memory wrote its first mirror from that memory, naming nobody: every key
      the previous file named that this process has not heard is CARRIED FORWARD, its roster kept, heard
      false, until its heartbeat or exchange arrives (the event);
  (2) an expired legacy heartbeat was PRUNED, so a stalled peer past the TTL removed a live session's
      sid: the row stays, marked expired, until the next beat (the event).
And the kernel's link state decides what a source vouches for (round 2 of fork PR #897, the reviewer's
ruling): a session started on a host after its last heard roster is in no roster, so a host counted as
vouching for absence while its link is down, or while the kernel has never reported it up, would let rule 5
presume that session closed. A heard source vouches for presence whatever its link state, as long as it is
not held down; it vouches for absence only when its link is KNOWN UP. The kernel's down notify (peer_update,
the /peer route) writes the mirror itself, the host unreachable at once with its roster kept; the host is
reachable again on its first heartbeat or exchange heard with the link up, not on the up notify (the exchange
replaces the PEER_STATE row and with it the mark the down notify set: _link_down), and vouches for absence
from that exchange (_link_up: PEERS up and heard since). A far host gossiped through a hub follows the hub's
link; a source with no link state (no dialable PEERS row: never notified, an origin-only trust row, or a name
the kernel does not dial) vouches for presence alone; a legacy heartbeat has no link and vouches by its TTL.
The gate reaches a peer's row under the name it is filed under, and the kernel notifies the ALIAS it dials:
the dialer's fold files there, the dialed side's handler files a far bus under the name it DECLARES until a
row under a dialable name carries its busId (_canon_peer_name), so before this bus's own dial has folded the
peer, a far bus heard only through its dials to us has no link state: it vouches for the presence of the
sids it names and for nothing else, and the alias's down notify has nothing to withdraw from it. The fold is
the event that files the row where the alias's link reaches it (the declared-name test below runs the road
through the real handler, the real notify handler and the real fold; until the fifth commit that row vouched
for absence by heard alone, the road the fourth commit disclosed). Both recorders write the mirror after the
busId fold (the fourth commit), so the fold's own write has one row per bus.
Pinned here, by writing through the real writer and reading the file back: the document's shape; one
source per heartbeat with its own TTL; a peer's own rows under its name and its gossip as a via row under
via:<hub>/<far>; the hub's word about a directly held host, folded into that host's own row only while the row
is heard and not held down, matched by bus id, or by name when the row carries no different known bus id (the
direct row speaks, and a session the gossip names that the row's older roster does not is in no row until the
host's next exchange: the disclosed window and its event), standing beside a held-down or a carried direct row
otherwise, carried like any key, and dropped by the carry once the direct host speaks again or the hub's current
word about it folds (round 3 of fork PR #897, the reviewer's ruling: never discard a heard source's word); a name
match yielding to a known different bus id (another machine the hub calls by that name, found by the reviewer's
verifier, or the far bus restarted under a new id, in either ordering of who hears it first, leaving no via row
behind once the ids agree); a PEER_STATE row no exchange produced is not a source; the carry-forward across a restart and its release per host; the kernel's
seed of a carried host's link up at a restart, which vouches for nothing until the host is heard; the fold
of a carried row for a bus heard under its other name; the whitespace list of the shape until 2026-09-22
carried as one legacy source and pruned as heard sources name its sids; a file of neither shape carrying
nothing; a write failure said once in the bus log; the two flags at the notify and at the two exchange
recorders, the hub's link for a far host (a hub with no link state included), the sources with no link
state vouching for presence alone, and the declared-name road with the fold that ends it.
tests/test_dead_session_staleness.py ReaderFollowsTheWriter
runs this writer and the judge's reader together over one root; tests/test_postal_bus_lifetime.py
MonitorTick pins the poll's write. SYNTHETIC fixtures only: private synthetic sids, hostname TESTHOST."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source
from tests.conftest import restore_env

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the load (the module resolves its state root at import time); `session-hosts` off in
# the minted root, the repo rule for a test that builds its own state root
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
_ROOT = Path(os.environ["XDG_STATE_HOME"]) / "romp"
_ROOT.mkdir(parents=True, exist_ok=True)
(_ROOT / "session-hosts").write_text("off\n")
pm = load_source("romp_postal_mirror", os.path.join(BIN, "romp-postal-service"))

A = "a5a5a5a5-0001-4000-8000-000000000001"   # private synthetic sids, never the shared placeholder
B = "a5a5a5a5-0002-4000-8000-000000000002"
C = "a5a5a5a5-0003-4000-8000-000000000003"
D = "a5a5a5a5-0004-4000-8000-000000000004"
E = "a5a5a5a5-0005-4000-8000-000000000005"
HOST, HUB, FAR = "TESTHOST", "TESTHOST-hub", "TESTHOST-far"
FAR_ALIAS = "TESTHOST-far-alias"               # the name the kernel dials the far host by when the hub knows it as FAR
VIA = "via:"                                   # the key of a hub's word about a far host, via:<hub>/<far> (pm.REMOTE_SIDS_VIA)
VIA_FAR = VIA + HUB + "/" + FAR
HB = "heartbeat:"                              # the key of a legacy heartbeat's row (pm.REMOTE_SIDS_HEARTBEAT)
LEGACY = "legacy:list"                         # the key a whitespace-list mirror is carried under (pm.REMOTE_SIDS_LEGACY)


class Mirror(unittest.TestCase):
    def setUp(self):
        pm.STATE.mkdir(parents=True, exist_ok=True)
        self.path = pm.STATE / "remote-sids"
        self.path.unlink(missing_ok=True)
        saved = (dict(pm.HEARTBEATS), dict(pm.PEER_STATE), dict(pm.PEERS))
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear(); pm.PEERS.clear()

        def restore():
            for d, v in zip((pm.HEARTBEATS, pm.PEER_STATE, pm.PEERS), saved):
                d.clear(); d.update(v)
            self.path.unlink(missing_ok=True)
        self.addCleanup(restore)
        reconcile = pm._peer_threads_reconcile
        pm._peer_threads_reconcile = lambda host: None    # the notify's dialer bookkeeping is not under test: an up
        self.addCleanup(setattr, pm, "_peer_threads_reconcile", reconcile)   # notify would dial a loopback port nothing listens on
        self.now = pm.time.time()

    def _rows(self):
        """key -> (heard, expired, sids) from the file, or the raw text when it is not a document (so a writer
        of another shape fails a pin by its message rather than by an exception)."""
        text = self.path.read_text()
        try:
            return {k: (r["heard"], r["expired"], r["sids"]) for k, r in json.loads(text)["hosts"].items()}
        except (ValueError, KeyError, TypeError):
            return text

    def _doc(self):
        return json.loads(self.path.read_text())

    def _reach(self):
        """key -> (heard, expired, linkDown, reachable, sids): the row's four flags, the last the reader's. The two link
        flags are read with .get, so a writer that spells neither fails a pin by its message (None where a bool is
        due) rather than by an exception."""
        return {k: (r["heard"], r["expired"], r.get("linkDown"), r.get("reachable"), r["sids"])
                for k, r in json.loads(self.path.read_text())["hosts"].items()}

    def _vouch(self):
        """key -> (reachable, linkUp, vouchesAbsence): what the row vouches for, presence (rule 4) and absence (rule
        5's precondition), and the known-up link the second turns on. Read with .get, so a writer missing a flag
        fails a pin by None where a bool is due rather than by an exception."""
        return {k: (r.get("reachable"), r.get("linkUp"), r.get("vouchesAbsence"))
                for k, r in json.loads(self.path.read_text())["hosts"].items()}

    def _notify(self, host, up, port=50002):
        """The kernel's /peer notify for a tunnel transition, through the real handler (peer_update), which writes
        the mirror itself; nothing else writes between the notify and the read that follows it."""
        payload, status = pm.peer_update({"host": host, "port": port, "up": up})
        self.assertEqual(status, 200, payload)

    def _exchange_request(self, host, presence):
        return {"host": host, "epoch": 1, "proto": pm.PEER_PROTO, "presence": presence, "holds": [],
                "relays": [], "acks": [], "bounces": [], "wait": False}

    def _peer(self, host, presence, seen_ago=5, bus_id=None):
        st = {"presence": presence, "epoch": 1, "holds": [], "seenAt": int(self.now - seen_ago)}
        if bus_id:
            st["busId"] = bus_id
        pm.PEER_STATE[host] = st

    def _restart(self):
        """A restarted bus process's memory: nothing heard yet, the file still on disk."""
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear()

    def _local_listing_answered_empty(self):
        """The local sessions listing the dialed side's handler gossips in its response presence, answered and
        empty, through the ROMP_SESSIONS_FILE seam; put back as found."""
        seam = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        seam.write("[]"); seam.close()
        self.addCleanup(os.unlink, seam.name)
        self.addCleanup(restore_env, "ROMP_SESSIONS_FILE", os.environ.get("ROMP_SESSIONS_FILE"))
        os.environ["ROMP_SESSIONS_FILE"] = seam.name

    def _far_dials_us(self, declared, presence, bus_id):
        """The dialed side of one exchange, through the real handler: the far bus declares `declared` and `bus_id`."""
        req = dict(self._exchange_request(declared, presence), busId=bus_id)
        resp, status = pm.peer_exchange_handle(req)
        self.assertEqual(status, 200, resp)

    def test_the_document_shape(self):
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}], bus_id="bus-1")
        pm._write_remote_sids()
        doc = self._doc()
        self.assertEqual(sorted(doc), ["busStarted", "hosts", "v", "writtenAt"])
        self.assertEqual((doc["v"], doc["busStarted"]), (2, pm.BUS_EPOCH), "the writing process's boot second")
        self.assertIsInstance(doc["writtenAt"], int)
        self.assertEqual(doc["hosts"][HB + A], {"kind": "heartbeat", "sids": [A], "heard": True, "expired": False,
                                                 "linkDown": False, "linkUp": False, "reachable": True,
                                                 "vouchesAbsence": True, "seenAt": int(self.now), "name": "web"},
                         "a legacy heartbeat has no link and vouches for absence by its TTL alone")
        self.assertEqual(doc["hosts"][HOST], {"kind": "peer", "sids": [B], "heard": True, "expired": False,
                                              "linkDown": False, "linkUp": False, "reachable": True,
                                              "vouchesAbsence": False, "seenAt": int(self.now - 5), "busId": "bus-1"},
                         "a heard peer the kernel never notified: no link state, so it vouches for presence alone")
        self.assertTrue(self.path.read_text().endswith("}\n"), "one document, newline-terminated")

    def test_each_heartbeat_is_its_own_source_with_its_own_ttl(self):
        pm.HEARTBEATS[A] = ("web", self.now - pm.HEARTBEAT_TTL - 1)   # past the TTL by the recorded time
        pm.HEARTBEATS[B] = ("api", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, True, [A]), HB + B: (True, False, [B])},
                         "the expired beat's row stays, marked expired, roster kept: unreachable, not absent (the shape "
                         "until 2026-09-22 pruned it, the second road of fork PR #897's round 1)")

    def test_a_peers_own_rows_under_its_name_and_its_gossip_as_a_via_row_under_the_hub_and_the_far_host(self):
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), VIA_FAR: (True, False, [B])})
        row = self._doc()["hosts"][VIA_FAR]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, FAR, "far-bus"),
                         "the hub's word about the far host, keyed by both names under a colon no host name carries (so the "
                         "far host's own row, if any, stands beside it): the hub in via, the far host and its bus id on the row")
        # a hub that restarted and has not heard the far host yet gossips nothing about it: the via row is carried
        # from the previous file, unreachable, instead of its sids vanishing (the road one hop out)
        self._peer(HUB, [{"id": A, "name": "web"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), VIA_FAR: (False, False, [B])})

    def test_a_hubs_word_about_a_directly_held_host_folds_only_while_that_host_is_heard_and_not_held_down(self):
        """The ruled condition (round 3 of fork PR #897, the reviewer's ruling): the gossip folds into the far host's own
        row only when that row is heard in this process and the kernel does not hold its link down, matched by EITHER
        identity, the name the hub uses for the host or the bus id it stamps on the gossip (the row may sit under the
        alias the kernel dials). Until this round the writer folded it whenever the far host had a dialable PEERS row
        or a heard row, whatever that row's state (_via_duplicate, the display fold), and the second half of this test
        asserted the fold with the direct row CARRIED: the regression round 2 found by execution. The fold's residual
        is witnessed here, disclosed as a bound with the event that closes it, not closed by a timer."""
        self._notify(FAR, up=True)                                            # the kernel's table: a direct link, up
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")       # heard in this process
        self._peer(HUB, [{"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"},
                         {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [C])},
                         "heard and not held down: the far host's own word about its sessions, and no via row. THE RESIDUAL, "
                         "disclosed as a bound: the hub names a session on the far host (B) that the far host's older roster "
                         "does not, and that sid is in no row at this write, a window of one exchange interval of the far "
                         "host, closed by its next exchange (the event), not by a timer")
        self._peer(FAR, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], bus_id="far-bus")   # the event
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [B, C])},
                         "the far host's next exchange names it")
        # by name alone: a hub that predates viaBus stamps none, and the row under that name speaks
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [B, C])},
                         "matched by name: folded (a writer folding by bus id alone writes a via row here)")
        # by bus id alone: the far host's row sits under the alias the kernel dials; the hub knows it by another name and
        # stamps the bus id (the notify below writes the mirror itself, so the gossip and the alias row are in place first)
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR, "viaBus": "far-bus"}])
        pm.PEER_STATE.pop(FAR)
        pm.PEERS.pop(FAR)
        self._peer(FAR_ALIAS, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], bus_id="far-bus")
        self._notify(FAR_ALIAS, up=True)
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR_ALIAS: (True, False, [B, C])},
                         "matched by bus id: the row under the alias speaks, folded (a writer folding by name alone writes a "
                         "via row under via:<hub>/<far> beside it); the row under the old name is gone, its bus heard under "
                         "the alias")
        # the negative that flipped: the direct row CARRIED after a restart speaks for nothing, and the hub's word stands
        self._restart()
        pm.PEERS.clear()
        self._notify(FAR_ALIAS, up=True)                  # the kernel's seed: PEERS up for a host this process has not heard
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR_ALIAS: (False, False, [B, C]), VIA_FAR: (True, False, [D])},
                         "carried: the far host's last roster still protects B and C, unreachable, and the hub's word about a "
                         "session started there since (D) stands as a via row (until this round the gossip was folded because "
                         "a dialable PEERS row existed, D was in no row, and a vouching hub let rule 5 presume it closed: the "
                         "regression round 2 found)")

    def test_a_hubs_word_about_a_directly_held_host_stands_while_it_is_down_or_carried_and_yields_when_it_speaks_again(self):
        """Round 3 of fork PR #897, the reviewer's ruling: never discard a heard source's word. The far host is heard
        directly, then the kernel holds its link down while the hub, up and heard, names a session started on it since:
        that sid must be named, by the hub's row, so the reader answers rule 4 while the hub vouches and never rule 5
        (a writer folding the gossip whatever the direct row's state left it in no row, and the hub, vouching for
        absence, let rule 5 presume it closed). The same with the direct row carried after a restart, the carried via
        row persisting like any carried row. The far host's exchange arriving with its link up is the event that ends
        the via row: dropped by the carry, the direct row speaks. The composition with the reader's verdicts is
        tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the hub's word phase)."""
        gossip = lambda *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus"} for s in sids]
        self._notify(FAR, up=True)
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C))
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HUB: (True, True, True), FAR: (True, True, True)},
                         "both heard with their links up: the gossip folds, the direct row speaks")
        self._notify(FAR, up=False)                        # the kernel holds the far host's link down
        self.assertEqual(self._reach()[FAR], (True, False, True, False, [C]), "held down: unreachable, its last roster kept")
        self._peer(HUB, gossip(C, D))                      # the hub's next exchange: a session started on the far host since
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, True, False, [C]),
                                         VIA_FAR: (True, False, False, True, [C, D])},
                         "THE RULE: the direct row is held down, so it speaks for nothing new, and the hub's word stands beside "
                         "it as a via row naming the new session (D): the reader answers rule 4 for D by the hub's row (a "
                         "writer folding the gossip whatever the direct row's state, the display fold, leaves D in no row here, "
                         "and the hub vouching for absence lets rule 5 presume it closed; a writer adding the gossip to the "
                         "direct row credits the far host with a word it did not give, and D is then held down with it)")
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the via row follows the hub's link: known up, heard")
        row = self._doc()["hosts"][VIA_FAR]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, FAR, "far-bus"))
        self._notify(HUB, up=False)                        # the hub's link down too: its word follows it
        self.assertEqual((self._reach()[VIA_FAR], self._vouch()[VIA_FAR]),
                         ((True, False, True, False, [C, D]), (False, False, False)),
                         "a hub the kernel holds down carries no fresh word: the via row is link-down with it, roster kept")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C, D))
        pm._write_remote_sids()
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the hub heard again with its link up")
        # the same road with the direct row CARRIED: a restart from this state; the first poll's write carries every row
        self._restart()
        pm.PEERS.clear()
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), FAR: (False, False, False, False, [C]),
                                         VIA_FAR: (False, False, False, False, [C, D])},
                         "a carried via row persists heard=false like any carried row: the hub's last word about the far host "
                         "still names D (a carry that lets the CARRIED direct row speak drops it here, and D is in no row)")
        self._notify(FAR, up=True)                         # the kernel's seed: both links up, nothing heard yet
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C, D, E))                   # the hub heard first: a further session on the far host
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (False, False, False, False, [C]),
                                         VIA_FAR: (True, False, False, True, [C, D, E])},
                         "carried: the far host's last roster, not heard, still protects C; the hub's word names D and E (a "
                         "writer folding on the seeded PEERS row leaves them in no row while the hub vouches: rule 5, the "
                         "regression; a writer keying the via row by the far host's name overwrites the carried row and "
                         "loses C, the far host's own last word)")
        self.assertEqual(self._vouch()[FAR], (False, True, False), "the seed: linkUp and not heard, vouching for nothing")
        self._peer(FAR, [{"id": C, "name": "tests"}, {"id": D, "name": "api"}, {"id": E, "name": "api"}], bus_id="far-bus")
        pm._write_remote_sids()                            # the event: the far host's exchange arrives with its link up
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, False, True, [C, D, E])},
                         "the direct row speaks again: the gossip folds and the via row is DROPPED by the carry (a writer that "
                         "carries it leaves the hub's older word naming D and E for the file's life, heard=false, and each "
                         "would be cannot-determine by that row once the far host no longer names it)")
        self._peer(HUB, gossip(C, D, E))                   # the hub's next exchange: folded, the direct row still speaks
        pm._write_remote_sids()
        self.assertEqual(sorted(self._reach()), sorted([HUB, FAR]), "no via row while the far host speaks for itself")

    def test_a_name_match_yields_to_a_known_different_bus_id(self):
        """Round 3 of fork PR #897, found by the reviewer's verifier by execution: the direct row under a name is heard
        with its link up and carries one bus id; a hub the kernel holds up gossips a session on a DIFFERENT machine it
        calls by the same name, stamping that machine's bus id. Until the eighth commit _direct_row_speaks matched by
        name OR by bus id, so the hub's word folded into a row that is another bus: the session was in no row, and the
        direct row and the hub, both vouching for absence, let rule 5 presume it closed for as long as the direct row
        was heard and not held down (not a one-interval window: no exchange of the direct row ever names a session on
        the other machine). The rule: both ids known and different, the row does not speak, and the hub's word stands
        as a via row beside it. A row with no bus id, or a gossip with no viaBus, still matches by name, and the hub's
        earlier word under the key is dropped when its current word folds. The composition with the reader's verdicts
        is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the name collision step of the hub's word
        phase)."""
        X = "TESTHOST-x"
        via_x = VIA + HUB + "/" + X
        self._notify(X, up=True)
        self._peer(X, [{"id": C, "name": "tests"}], bus_id="bus-1")
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X, "viaBus": "bus-2"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [C]),
                                         via_x: (True, False, False, True, [E])},
                         "THE RULE: the row under the hub's name for the host carries bus-1 and the gossip stamps bus-2, so the "
                         "row is another bus and does not speak for a session started on the machine the hub means; the hub's "
                         "word stands as a via row beside it, and E is rule 4's by that row (a writer matching by name whatever "
                         "the ids folds it into the bus-1 row, E is in no row, and two vouching sources let rule 5 presume it "
                         "closed for as long as that row is heard and up)")
        self.assertEqual(self._vouch(), {HUB: (True, True, True), X: (True, True, True), via_x: (True, True, True)},
                         "both direct rows vouch for absence; the via row follows the hub's link")
        row = self._doc()["hosts"][via_x]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, X, "bus-2"))
        # a gossip with no viaBus (a hub that predates the field) matches by name, and the hub's current word about the
        # host folding drops its earlier word under the same key (the hub knows one machine by that name)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), X: (True, False, [C])},
                         "no viaBus: matched by name and folded; the via row of the hub's earlier word is dropped, not carried")
        # a row with no bus id (an exchange that carried none) matches by name too
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X, "viaBus": "bus-2"}])
        self._peer(X, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), X: (True, False, [C])},
                         "no busId on the row: matched by name and folded (a writer refusing every name match once a viaBus is "
                         "stamped writes a via row here)")

    def test_a_far_bus_restarted_under_a_hub_parts_the_ids_until_both_sides_hear_it_and_leaves_no_via_row_behind(self):
        """A bus id is minted per process (BUS_ID), so a far bus restart gives the direct row and the hub's gossip
        different ids until the first exchange with the restarted bus reaches each side, and by the rule above the row
        does not speak for that interval: the hub's word stands as a via row, the conservative side. Both orderings.
        The hub hears the restarted bus first: its gossip stamps the new id against our row's old one, the via row
        stands until our own exchange lands with the new id, then the gossip folds and the via row is dropped by the
        gate. We hear it first: our row carries the new id against the hub's last gossip's old one, the via row stands
        until the hub's exchange with the restarted bus, whose gossip then stamps the new id and folds; the via row of
        the hub's earlier word, stamped with the old id, is dropped because the hub's current word about that host
        folded at this write (`folded`): a carry keyed on the ids alone carries it heard=false for the file's life,
        since the old id never returns, and a session that then ends on the far host is cannot-determine by that
        row's last word where rule 5 is due (the linger the ruling's drop clause forbids, shown by execution on a
        scratch copy with the clause alone)."""
        gossip = lambda via_bus, *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": via_bus} for s in sids]
        roster = lambda *sids: [{"id": s, "name": "api"} for s in sids]
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)
        self._peer(FAR, roster(C, D), bus_id="old")
        self._peer(HUB, gossip("old", C, D))
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the same id on both sides: folded")
        # ordering one: the hub hears the restarted bus first
        self._peer(HUB, gossip("new", C, D))
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (True, False, False, True, [C, D]),
                         "the hub stamps the new id and our row still carries the old: by the ids another bus, so the hub's "
                         "word stands as a via row (a writer matching by name folds it, and there is no via row)")
        self.assertEqual(self._doc()["hosts"].get(VIA_FAR, {}).get("viaBus"), "new")
        self._peer(FAR, roster(C, D), bus_id="new")                  # our exchange with the restarted bus
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the ids agree: folded, and the via row is dropped by the gate")
        # ordering two: we hear the restarted bus first (a second restart, a further id)
        self._peer(FAR, roster(C, D), bus_id="newer")
        pm._write_remote_sids()
        self.assertEqual((self._reach().get(VIA_FAR), self._doc()["hosts"].get(VIA_FAR, {}).get("viaBus")),
                         ((True, False, False, True, [C, D]), "new"),
                         "our row carries the newer id and the hub's last gossip the one before: the hub's word stands as a via "
                         "row, stamped with the id the hub knows")
        self._peer(HUB, gossip("newer", C, D))                       # the hub's exchange with the restarted bus
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]),
                         "the hub's current word about the far host folds, and its earlier word under the same key, stamped with "
                         "an id our row no longer carries, is DROPPED (a carry keyed on the ids alone carries it heard=false for "
                         "the file's life: the old id never returns)")
        self._peer(FAR, roster(C), bus_id="newer")                   # D ends on the far host
        self._peer(HUB, gossip("newer", C))
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), FAR: (True, False, [C])},
                         "D is in no row and both sources vouch: rule 5 is the reader's answer (a lingering via row would hold D "
                         "at cannot-determine by the hub's stale word)")
        # the hub not heard across the interval: the via row of its stale word is carried like any key, and dropped when
        # the hub is heard again with the new id
        self._peer(FAR, roster(C), bus_id="newest")
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (True, False, False, True, [C]), "a third restart heard here first: the via row again")
        self._restart()
        pm.PEERS.clear()
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)
        self._peer(FAR, roster(C), bus_id="newest")
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (False, False, False, False, [C]),
                         "the hub not heard in this process: its stale word is carried, unreachable, like any carried row (the "
                         "ids do not agree and nothing of the hub's folded at this write)")
        self._peer(HUB, gossip("newest", C))
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the hub heard with the new id: folded, the carried via row dropped")

    def test_a_peer_state_row_no_exchange_produced_is_not_a_source(self):
        pm.PEER_STATE[HOST] = {"drift": "proto"}       # the setdefault shape a refusal or drift note leaves
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {}, "no seenAt: nothing was heard from it")

    def test_a_restart_carries_every_host_it_has_not_heard_as_unreachable_and_releases_each_on_its_event(self):
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (True, False, [B]), HUB: (True, False, [C])})
        self._restart()
        pm._write_remote_sids()                        # the first poll's write, before any beat or exchange
        self.assertEqual(self._rows(), {HB + A: (False, False, [A]), HOST: (False, False, [B]), HUB: (False, False, [C])},
                         "a restarted bus writes a first mirror whose hosts are all unreachable, rosters kept (the "
                         "shape until 2026-09-22 wrote an empty list, the first road of fork PR #897's round 1)")
        self._peer(HOST, [{"id": D, "name": "api"}])   # one exchange lands: that host, and only that host, is heard
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (False, False, [A]), HOST: (True, False, [D]), HUB: (False, False, [C])},
                         "per host: the heard host's fresh roster; the others still carried")
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (True, False, [D]), HUB: (True, False, [C])})

    def test_the_kernels_seed_of_a_carried_hosts_link_up_at_a_restart_vouches_for_nothing_until_the_host_is_heard(self):
        """The primary restart road (round 2 of fork PR #897, a verifier's finding at the fifth commit: a writer computing
        vouchesAbsence from the link alone, heard dropped, survived every pin of the five modules and reopened the first
        road of round 1 by execution). A restarted bus starts with an empty peer table, and the kernel seeds it from
        /tunnels (_seed_peers_from_kernel) or re-notifies every tunnel up on its next supervisor pass, through peer_update,
        BEFORE any exchange arrives: a host carried from the previous file, not heard by this process, has PEERS up and no
        mark, so linkUp is True. Its roster is the previous process's last word, not this one's, and the row vouches for
        nothing: unreachable (not heard), and not vouching for absence, so a sid it does not name stays unsettled (a writer
        vouching for absence by the link alone says True here, and a session started on that host since the previous file
        is presumed closed on the restarted bus's first write). The host's exchange is the event: heard with the link up,
        both flags. The composition with the reader's verdicts is tests/test_dead_session_staleness.py
        ReaderFollowsTheWriter (the seeded phase)."""
        self._peer(HOST, [{"id": B, "name": "api"}])
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self._restart()
        pm.PEERS.clear()                                    # a fresh process: the link table empty until the seed
        self._notify(HOST, up=True)                         # the seed (or the re-notify): PEERS up, nothing heard, no mark
        self.assertEqual(self._reach()[HOST], (False, False, False, False, [B]),
                         "carried from the previous file and not heard: unreachable, its roster kept, the link neither down "
                         "nor marked")
        self.assertEqual(self._vouch()[HOST], (False, True, False),
                         "THE SEED: the kernel holds the link up (linkUp) and this process has heard nothing over it, so the row "
                         "vouches for neither presence nor absence (a writer vouching for absence by the link alone says "
                         "(False, True, True) here, and a sid started on that host since the previous file would be rule 5's)")
        self.assertEqual(self._vouch()[HUB], (False, False, False), "the host the seed did not name: not heard, no link state")
        self._peer(HOST, [{"id": D, "name": "api"}])        # the event: the host's exchange arrives with the link up
        pm._write_remote_sids()
        self.assertEqual((self._reach()[HOST], self._vouch()[HOST]), ((True, False, False, True, [D]), (True, True, True)),
                         "heard with the link up: reachable and vouching for absence, on this exchange and nothing else")
        self.assertEqual(self._vouch()[HUB], (False, False, False), "the other carried host still waits for its own event")

    def test_a_carried_row_for_a_bus_heard_under_its_other_name_is_dropped(self):
        self._peer("TESTHOST-selfname", [{"id": A, "name": "web"}], bus_id="bus-1")
        pm._write_remote_sids()
        self._restart()
        self._peer(HOST, [{"id": A, "name": "web"}], bus_id="bus-1")     # the same bus, under its dialable alias
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HOST: (True, False, [A])},
                         "one row per bus: the stale name's carried row is the same bus (busId), heard under its alias")

    def test_a_whitespace_list_is_carried_as_the_legacy_source_until_heard_sources_name_its_sids(self):
        self.path.write_text(A + "\n" + B + "\n")     # what a bus before 2026-09-22 wrote: live remote sids then
        pm.HEARTBEATS[A] = ("web", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), LEGACY: (False, False, [B])},
                         "the old list's sids this process has not heard are carried, unreachable; the one it heard "
                         "is its own source now")
        pm.HEARTBEATS[B] = ("api", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HB + B: (True, False, [B])},
                         "every sid heard: the legacy source is gone")

    def test_a_file_of_neither_shape_carries_nothing(self):
        for text in ("[1, 2]\n", '{"hosts": 3}\n', '{"hosts": {"TESTHOST": "x"}}\n', "\x00\x01\n"):
            with self.subTest(text=text):
                self.path.write_text(text)
                pm.HEARTBEATS[A] = ("web", self.now)
                pm._write_remote_sids()
                self.assertEqual(self._rows(), {HB + A: (True, False, [A])}, "rewritten as a document from memory alone")

    def test_the_kernels_down_notify_makes_a_heard_host_unreachable_at_once_and_its_next_exchange_with_the_link_up_reachable(self):
        """Round 2 of fork PR #897, the reviewer's ruling: a host that is down cannot vouch for absence, and neither
        can one whose link the kernel has never reported up. HOST is heard here BEFORE any notify, so it vouches for
        presence alone until the kernel's up notify lands and the host is heard since (the fifth commit)."""
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, False, True, [B])},
                         "heard, its link never reported down: reachable")
        self.assertEqual(self._vouch(), {HB + A: (True, False, True), HOST: (True, False, False)},
                         "the beat vouches for absence by its TTL; the heard host with no link state vouches for presence "
                         "alone (a writer computing vouchesAbsence as reachable says True here)")
        self._notify(HOST, up=False)                       # the kernel's down notify; no other write follows it
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, True, False, [B])},
                         "the notify's own write: the host is marked link-down and unreachable at once, its roster kept "
                         "(a writer gating on heard alone leaves it reachable; one that waits for the next tick leaves the "
                         "file as it was; one that drops the roster loses the sid the host last named)")
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)                        # the link is back; nothing heard from the host since it dropped
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]),
                         "the up notify alone is not the event: the roster is the one heard before the link dropped, "
                         "and says nothing about a session started there since")
        self.assertEqual(self._vouch()[HOST], (False, False, False),
                         "PEERS says up and the mark stands: linkUp False (a writer reading PEERS alone says True)")
        self._peer(HOST, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}])   # its exchange arrives with the link up
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, C]),
                         "heard with the link up: reachable, on the roster that exchange reported")
        self.assertEqual(self._vouch()[HOST], (True, True, True),
                         "the link known up and the host heard since it dropped: it vouches for absence too")

    def test_the_two_exchange_recorders_clear_the_mark_and_an_exchange_heard_while_down_counts_once_the_link_is_up(self):
        """The mark the down notify sets lives on the PEER_STATE row, and both recorders replace that row: the dialer's
        fold (peer_exchange_apply, the path a re-dial after the up notify runs) and the dialed side's handler
        (peer_exchange_handle: the far side may dial us while OUR kernel holds the link to it down). An exchange
        heard while the link is down is heard, and its host is reachable the moment the link is up: what the ruling
        gates is a roster from before the drop, and this one is not."""
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._vouch()[HOST], (True, True, True), "notified up, then heard: vouches for presence and absence")
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)
        pm.peer_exchange_apply(HOST, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": []})
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]),
                         "the dialer's fold replaced the row (the mark with it) and wrote: reachable")
        self.assertEqual(self._vouch()[HOST], (True, True, True), "...and, PEERS up, vouching for absence again")
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._local_listing_answered_empty()
        resp, status = pm.peer_exchange_handle(self._exchange_request(HOST, [{"id": B, "name": "api"}, {"id": D, "name": "web"}]))
        self.assertEqual(status, 200, resp)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B, D]),
                         "heard while the kernel holds the link down: the roster is fresh, the row still unreachable "
                         "(the link, not the roster, is what is down)")
        self.assertEqual(self._vouch()[HOST], (False, False, False), "the link is down: it vouches for nothing yet")
        self._notify(HOST, up=True)
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, D]),
                         "the link is up and the host was heard since it dropped: reachable on the up notify's own write")
        self.assertEqual(self._vouch()[HOST], (True, True, True),
                         "both hold, the link up and the host heard since the drop: it vouches for absence on that write")

    def test_a_row_a_far_bus_filed_under_its_declared_name_before_the_fold_vouches_for_presence_alone(self):
        """The ruled closure of the road the fourth commit disclosed (round 2 of fork PR #897, the reviewer's ruling: a
        source vouches for a sid's ABSENCE only when its link is known up; every heard source still vouches for
        PRESENCE). The kernel notifies the ALIAS it dials (PEERS[alias]); the dialed side's handler files a far bus
        under the name it DECLARES unless a PEER_STATE row under a dialable name already carries its busId
        (_canon_peer_name). Before this bus's own dial has folded the peer under the alias (a restarted bus whose
        seeded row has no token yet; a dial the far side refuses while its dial to us lands), the far bus's row sits
        under its declared hostname, which has no PEERS row and no link state: it is reachable, so the sid it names is
        rule 4's, and it does not vouch for absence, so a sid it does not name is not settled either way, whether the
        alias is up or down (until the fifth commit heard alone made it vouch, and a sid nothing named was rule 5's
        with this host as the only reachable one). The fold (peer_exchange_apply under the alias with the busId) is
        the event that files the row where the alias's link reaches it: linkUp and vouching for absence on the fold's
        own write, link-down and unreachable on the alias's down notify, and neither on the up notify alone until the
        host is heard since. The road is reached again at every bus restart the far side dials into first: the
        carried alias row is the same bus by busId and gives way to the heard row under the declared name, which
        vouches for presence alone until this bus's dial folds it back."""
        alias, declared = "TESTHOST-c-alias", "TESTHOST-c-hostname"   # the kernel dials the alias; the far bus declares its hostname
        self._local_listing_answered_empty()
        self._notify(alias, up=True)                        # the kernel's link is up; this bus has not dialed yet
        self._far_dials_us(declared, [{"id": B, "name": "api"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "no row under a dialable name carries the busId: filed as declared")
        self.assertEqual(self._reach(), {declared: (True, False, False, True, [B])})
        self.assertEqual(self._vouch(), {declared: (True, False, False)},
                         "THE RULE: the row under the declared name is heard and not held down, so it vouches for the "
                         "presence of the sid it names (reachable); the kernel dials no such name, so its link is unknown "
                         "(linkUp False, the alias's up notify does not reach it) and it does not vouch for absence (a "
                         "writer computing vouchesAbsence as reachable says True here: the disclosed road, reopened)")
        self._notify(alias, up=False)
        self.assertEqual((pm.PEERS[alias]["up"], (pm.PEER_STATE.get(declared) or {}).get("linkDown")), (False, None),
                         "the kernel holds the alias down; the declared row carries no mark (the notify marks PEER_STATE[alias])")
        self.assertEqual((self._reach(), self._vouch()), ({declared: (True, False, False, True, [B])}, {declared: (True, False, False)}),
                         "the alias down changes nothing for a row with no link state of its own: the sid it names stays "
                         "protected (rule 4), and a sid it does not name is not settled either way (it never vouched for "
                         "absence, so the down notify has nothing to withdraw)")
        # the fold: this bus's own dial lands under the alias with the busId, the event that files the row under the alias
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-c"})
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "the declared row is the same bus (busId), dropped by the fold")
        self.assertEqual(self._reach(), {alias: (True, False, False, True, [B])},
                         "the fold's own write has one row per bus, under the alias: the recorder writes AFTER the busId "
                         "fold (a recorder writing before it leaves the declared row in the file, heard and reachable, "
                         "until the next write)")
        self.assertEqual(self._vouch(), {alias: (True, True, True)},
                         "under the alias the kernel holds up, heard on this exchange: the row vouches for absence now")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "canonicalized: a row under a dialable name carries the busId now")
        self.assertEqual(self._vouch(), {alias: (True, True, True)})
        self._notify(alias, up=False)
        self.assertEqual((self._reach(), self._vouch()), ({alias: (True, False, True, False, [B, C])}, {alias: (False, False, False)}),
                         "folded under the alias, the row follows the alias's link: down, so unreachable and vouching for nothing")
        self._notify(alias, up=True)
        self.assertEqual(self._vouch(), {alias: (False, False, False)},
                         "the up notify alone leaves the mark: no vouching until the host is heard since the drop")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual((sorted(pm.PEER_STATE), self._vouch()), ([alias], {alias: (True, True, True)}),
                         "heard again (the far bus's dial, canonicalized under the alias) with the link up: both hold")
        # the road again at a restart: empty memory, the file carrying the alias row, the kernel seeding the alias down
        # (a tunnel down at start), the far side dialing in before this bus's own dial (which a down link never makes)
        self._restart()
        pm.PEERS.clear()
        self._notify(alias, up=False)
        self.assertEqual((self._reach(), self._vouch()), ({alias: (False, False, True, False, [B, C])}, {alias: (False, False, False)}),
                         "carried from the previous file, not heard, the seeded link down: unreachable")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "memory empty: nothing to canonicalize to, filed as declared")
        self.assertEqual((self._reach(), self._vouch()), ({declared: (True, False, False, True, [B, C])}, {declared: (True, False, False)}),
                         "the same road at the restart: the carried alias row gives way to the heard row (same busId), "
                         "which has no link state while the kernel holds the alias down: presence alone, until this bus's "
                         "dial, when the link comes up and the token arrives, folds it back under the alias")
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "epoch": 1,
                                           "holds": [], "busId": "bus-c"})
        self.assertEqual((self._reach(), self._vouch()), ({alias: (True, False, False, True, [B, C])}, {alias: (True, True, True)}),
                         "folded again: one row, under the alias, vouching for absence")

    def test_a_far_host_gossiped_through_a_hub_follows_the_hubs_link(self):
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])})
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)},
                         "the hub's link is known up and the hub heard: the far host vouches for absence by the hub's link "
                         "(a via row has no link of its own)")
        self._notify(HUB, up=False)
        self.assertEqual(self._reach(), {HUB: (True, False, True, False, [A]), VIA_FAR: (True, False, True, False, [B])},
                         "the far host is reached through the hub: a hub the kernel holds down cannot carry fresh word "
                         "about it, so its row is link-down with the hub's, roster kept")
        self.assertEqual(self._vouch(), {HUB: (False, False, False), VIA_FAR: (False, False, False)})
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])},
                         "the hub's exchange with its link up: both reachable again")
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)}, "...and both vouching for absence")

    def test_a_far_host_gossiped_through_a_hub_the_kernel_never_notified_vouches_for_presence_alone(self):
        self.assertEqual(pm.PEERS, {}, "no notify has landed: the hub has no link state")
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])},
                         "heard, not held down: both vouch for the presence of the sids they name")
        self.assertEqual(self._vouch(), {HUB: (True, False, False), VIA_FAR: (True, False, False)},
                         "a hub with no link state vouches for absence for nobody, and neither does the far host it "
                         "gossips (a via row vouching by its own presence, not the hub's link, says True here)")
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)},
                         "the hub notified up and heard since: both vouch for absence")

    def test_a_source_the_kernel_never_notified_has_no_link_state_and_vouches_for_presence_alone(self):
        self.assertEqual(pm.PEERS, {}, "no notify has landed")
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])      # heard, and the kernel never notified it
        pm.peer_update({"host": FAR, "trust": "directed", "originOnly": True})   # a tier for a host with no tunnel
        self._peer(FAR, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(pm.PEERS[FAR]["port"], None, "origin-only: no port, nothing to dial")
        self.assertFalse(pm.PEERS[FAR]["up"], "the row spells up False, and that is not a link held down")
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, False, True, [B]),
                                         FAR: (True, False, False, True, [C])},
                         "no dialable PEERS row: never notified, origin-only, or a heartbeat key no row can match; "
                         "each heard and not held down, so each vouches for the presence of the sids it names")
        self.assertEqual(self._vouch(), {HB + A: (True, False, True), HOST: (True, False, False), FAR: (True, False, False)},
                         "the beat vouches for absence by its TTL, having no link; the never-notified host and the "
                         "origin-only host have no link state and vouch for presence alone (a writer requiring a link of "
                         "a heartbeat says False for the beat; one vouching by heard alone says True for the hosts)")
        # a down notify for a host this process has not heard: its carried row is unreachable already (heard false),
        # and now also says the kernel holds its link down
        self._restart()
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (False, False, True, False, [B]),
                         "carried from the previous file, heard false, link-down true: unreachable, roster kept")
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]))
        self.assertEqual(self._vouch()[HOST], (True, True, True), "notified up and heard since: it vouches for absence now")

    def test_a_write_failure_is_said_once_in_the_bus_log(self):
        state = pm.STATE
        blocker = tempfile.NamedTemporaryFile(dir=str(state), delete=False)
        blocker.close()
        self.addCleanup(os.unlink, blocker.name)
        pm.STATE = Path(blocker.name) / "under-a-file"   # no directory can exist here: every write fails
        self.addCleanup(setattr, pm, "STATE", state)
        pm._REMOTE_SIDS_SAID.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            pm._write_remote_sids()
            pm._write_remote_sids()
        lines = [ln for ln in err.getvalue().splitlines() if "remote-sids mirror was not written" in ln]
        self.assertEqual(len(lines), 1, "said once per distinct text, never swallowed: %r" % err.getvalue())
        self.assertIn("the judge reads the previous one", lines[0])


if __name__ == "__main__":
    unittest.main()
