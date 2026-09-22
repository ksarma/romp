#!/usr/bin/env python3
"""The postal bus's presence mirror (the bus's STATE/remote-sids, <state root>/postal/remote-sids), the
file kernel/judge's dead-session ladder reads for rules 4 and 5 (_presumed_closed_verdict). Since fork PR
#897's round 2 the mirror is a document, one row per PRESENCE SOURCE with the roster it last reported and
whether THIS bus process can vouch for it (postal_service.py _remote_sids_document): `heard` (a heartbeat or
exchange arrived in this process), `expired` (a legacy heartbeat past HEARTBEAT_TTL), `linkDown` (the kernel
holds its link down, or has since it was heard), `reachable` (heard and not expired and not linkDown, the
writer's flag and the one the reader's verdict reads), `sids`. The reader presumes a sid closed only when a
reachable source exists and none names it. Two roads to a false settle closed here, at the writer:
  (1) a bus restarted from empty memory wrote its first mirror from that memory, naming nobody: every key
      the previous file named that this process has not heard is CARRIED FORWARD, its roster kept, heard
      false, until its heartbeat or exchange arrives (the event);
  (2) an expired legacy heartbeat was PRUNED, so a stalled peer past the TTL removed a live session's
      sid: the row stays, marked expired, until the next beat (the event).
And the kernel's link state gates reachability (round 2 of fork PR #897, the reviewer's ruling): a session
started on a host after its last heard roster is in no roster, so a host counted reachable while its link
is down would let rule 5 presume that session closed; a host that is down cannot vouch for absence. The
kernel's down notify (peer_update, the /peer route) writes the mirror itself, the host unreachable at once
with its roster kept; the host is reachable again on its first heartbeat or exchange heard with the link
up, not on the up notify (the exchange replaces the PEER_STATE row and with it the mark the down notify
set: _link_down). A far host gossiped through a hub is gated by the hub's link; a source the kernel never
notified (no dialable PEERS row: never notified, or an origin-only trust row, or a legacy heartbeat) has
no link state and is gated by heard and the TTL alone. The gate reaches a peer's row under the name it is
filed under, and the kernel notifies the ALIAS it dials: the dialer's fold files there, the dialed side's
handler files a far bus under the name it DECLARES until a row under a dialable name carries its busId
(_canon_peer_name), so before this bus's own dial has folded the peer, a far bus heard only through its
dials to us has no link state and the alias's down notify does not reach it. That is a DISCLOSED RESIDUAL
of round 2 (a verifier's probe; no event ties the two names before the fold), and its witness is the test
named for the alias's link and the declared name below: it pins the road by execution, the fold that ends
it, and the restart at which the road is reached again, so a closure or a widening turns it red. Both
recorders write the mirror after the busId fold (the fourth commit), so the fold's own write has one row
per bus.
Pinned here, by writing through the real writer and reading the file back: the document's shape; one
source per heartbeat with its own TTL; a peer's own rows under its name and its gossip under the far host
it speaks for, with gossip about a directly held host folded (the direct row speaks); a PEER_STATE row no
exchange produced is not a source; the carry-forward across a restart and its release per host; the fold
of a carried row for a bus heard under its other name; the whitespace list of the shape until 2026-09-22
carried as one legacy source and pruned as heard sources name its sids; a file of neither shape carrying
nothing; a write failure said once in the bus log; the link gate at the notify and at the two exchange
recorders, the hub's link for a far host, the sources with no link state, and the declared-name road with
the fold that ends it.
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
HOST, HUB, FAR = "TESTHOST", "TESTHOST-hub", "TESTHOST-far"
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
                                                 "linkDown": False, "reachable": True, "seenAt": int(self.now),
                                                 "name": "web"})
        self.assertEqual(doc["hosts"][HOST], {"kind": "peer", "sids": [B], "heard": True, "expired": False,
                                              "linkDown": False, "reachable": True, "seenAt": int(self.now - 5),
                                              "busId": "bus-1"})
        self.assertTrue(self.path.read_text().endswith("}\n"), "one document, newline-terminated")

    def test_each_heartbeat_is_its_own_source_with_its_own_ttl(self):
        pm.HEARTBEATS[A] = ("web", self.now - pm.HEARTBEAT_TTL - 1)   # past the TTL by the recorded time
        pm.HEARTBEATS[B] = ("api", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, True, [A]), HB + B: (True, False, [B])},
                         "the expired beat's row stays, marked expired, roster kept: unreachable, not absent (the shape "
                         "until 2026-09-22 pruned it, the second road of fork PR #897's round 1)")

    def test_a_peers_own_rows_under_its_name_and_its_gossip_under_the_far_host(self):
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), FAR: (True, False, [B])})
        row = self._doc()["hosts"][FAR]
        self.assertEqual((row["kind"], row["via"]), ("via", HUB), "gossip is keyed by the host it is about, the hub named")
        # a hub that restarted and has not heard the far host yet gossips nothing about it: the far host's row
        # is carried from the previous file, unreachable, instead of its sids vanishing (the road one hop out)
        self._peer(HUB, [{"id": A, "name": "web"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), FAR: (False, False, [B])})

    def test_gossip_about_a_directly_held_host_is_folded_the_direct_row_speaks(self):
        pm.PEERS[FAR] = {"port": 1, "up": True, "at": int(self.now)}          # the kernel's table: a direct link
        self._peer(HUB, [{"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [C])},
                         "the far host's own word about its sessions, not the hub's gossip (_via_duplicate)")
        # the direct host not yet heard in this process: the gossip is still folded, its row carried
        self._restart()
        self._peer(HUB, [{"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (False, False, [C])},
                         "a directly held host speaks for itself, heard or carried; the hub's gossip about it is not a source")

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
        """Round 2 of fork PR #897, the reviewer's ruling: a host that is down cannot vouch for absence."""
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, False, True, [B])},
                         "heard, its link never reported down: reachable")
        self._notify(HOST, up=False)                       # the kernel's down notify; no other write follows it
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, True, False, [B])},
                         "the notify's own write: the host is marked link-down and unreachable at once, its roster kept "
                         "(a writer gating on heard alone leaves it reachable; one that waits for the next tick leaves the "
                         "file as it was; one that drops the roster loses the sid the host last named)")
        self._notify(HOST, up=True)                        # the link is back; nothing heard from the host since it dropped
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]),
                         "the up notify alone is not the event: the roster is the one heard before the link dropped, "
                         "and says nothing about a session started there since")
        self._peer(HOST, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}])   # its exchange arrives with the link up
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, C]),
                         "heard with the link up: reachable, on the roster that exchange reported")

    def test_the_two_exchange_recorders_clear_the_mark_and_an_exchange_heard_while_down_counts_once_the_link_is_up(self):
        """The mark the down notify sets lives on the PEER_STATE row, and both recorders replace that row: the dialer's
        fold (peer_exchange_apply, the path a re-dial after the up notify runs) and the dialed side's handler
        (peer_exchange_handle: the far side may dial us while OUR kernel holds the link to it down). An exchange
        heard while the link is down is heard, and its host is reachable the moment the link is up: what the ruling
        gates is a roster from before the drop, and this one is not."""
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self._notify(HOST, up=True)
        pm.peer_exchange_apply(HOST, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": []})
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]),
                         "the dialer's fold replaced the row (the mark with it) and wrote: reachable")
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self._local_listing_answered_empty()
        resp, status = pm.peer_exchange_handle(self._exchange_request(HOST, [{"id": B, "name": "api"}, {"id": D, "name": "web"}]))
        self.assertEqual(status, 200, resp)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B, D]),
                         "heard while the kernel holds the link down: the roster is fresh, the row still unreachable "
                         "(the link, not the roster, is what is down)")
        self._notify(HOST, up=True)
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, D]),
                         "the link is up and the host was heard since it dropped: reachable on the up notify's own write")

    def test_the_alias_link_does_not_reach_a_row_a_far_bus_filed_under_its_declared_name_before_the_fold(self):
        """The WITNESS of a disclosed residual (round 2 of fork PR #897, a verifier's probe), pinned as the road stands so
        a closure or a widening turns it red and retires the disclosure with it. The kernel notifies the ALIAS it dials
        (PEERS[alias]); the dialed side's handler files a far bus under the name it DECLARES unless a PEER_STATE row
        under a dialable name already carries its busId (_canon_peer_name). Before this bus's own dial has folded the
        peer under the alias (a restarted bus whose seeded row has no token yet; a dial the far side refuses while its
        dial to us lands), the far bus's row sits under its declared hostname, which has no PEERS row and no link
        state: heard alone gates it, so the alias's down notify leaves it reachable, and a sid nothing names would be
        rule 5's with this host as the only reachable one. No event ties the two names before the fold: the far bus's
        exchange carries its hostname and busId, the kernel's notify the alias and port, and PEERS never learns a
        busId. The fold (peer_exchange_apply under the alias with the busId) is the event that brings the row under
        the gate, and its own write already has one row per bus (both recorders write after the fold, the fourth
        commit). The road is reached again at every bus restart the far side dials into first: the carried alias row
        is the same bus by busId and gives way to the heard row under the declared name."""
        alias, declared = "TESTHOST-c-alias", "TESTHOST-c-hostname"   # the kernel dials the alias; the far bus declares its hostname
        self._local_listing_answered_empty()
        self._notify(alias, up=True)                        # the kernel's link is up; this bus has not dialed yet
        self._far_dials_us(declared, [{"id": B, "name": "api"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "no row under a dialable name carries the busId: filed as declared")
        self.assertEqual(self._reach(), {declared: (True, False, False, True, [B])})
        self._notify(alias, up=False)
        self.assertEqual((pm.PEERS[alias]["up"], (pm.PEER_STATE.get(declared) or {}).get("linkDown")), (False, None),
                         "the kernel holds the alias down; the declared row carries no mark (the notify marks PEER_STATE[alias])")
        self.assertEqual(self._reach(), {declared: (True, False, False, True, [B])},
                         "THE RESIDUAL, as disclosed: the row under the declared name has no link state, so the alias's "
                         "down notify does not reach it and it stays reachable (a closure of this road, or a writer "
                         "gating a heard row on some other alias's link, turns this pin red: retire the disclosure with it)")
        # the fold: this bus's own dial lands under the alias with the busId, the event that brings the row under the gate
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-c"})
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "the declared row is the same bus (busId), dropped by the fold")
        self.assertEqual(self._reach(), {alias: (True, False, False, True, [B])},
                         "the fold's own write has one row per bus, under the alias: the recorder writes AFTER the busId "
                         "fold (a recorder writing before it leaves the declared row in the file, heard and reachable, "
                         "until the next write)")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "canonicalized: a row under a dialable name carries the busId now")
        self._notify(alias, up=False)
        self.assertEqual(self._reach(), {alias: (True, False, True, False, [B, C])},
                         "the control: folded under the alias, the row is gated by the alias's link")
        # the road again at a restart: empty memory, the file carrying the alias row, the kernel seeding the alias down
        # (a tunnel down at start), the far side dialing in before this bus's own dial (which a down link never makes)
        self._restart()
        pm.PEERS.clear()
        self._notify(alias, up=False)
        self.assertEqual(self._reach(), {alias: (False, False, True, False, [B, C])},
                         "carried from the previous file, not heard, the seeded link down: unreachable")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "memory empty: nothing to canonicalize to, filed as declared")
        self.assertEqual(self._reach(), {declared: (True, False, False, True, [B, C])},
                         "the same road at the restart: the carried alias row gives way to the heard row (same busId), "
                         "which has no link state while the kernel holds the alias down; this bus's dial, when the link "
                         "comes up and the token arrives, folds it back under the alias")
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "epoch": 1,
                                           "holds": [], "busId": "bus-c"})
        self.assertEqual(self._reach(), {alias: (True, False, False, True, [B, C])}, "folded again: one row, under the alias")

    def test_a_far_host_gossiped_through_a_hub_is_gated_by_the_hubs_link(self):
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, False, True, [B])})
        self._notify(HUB, up=False)
        self.assertEqual(self._reach(), {HUB: (True, False, True, False, [A]), FAR: (True, False, True, False, [B])},
                         "the far host is reached through the hub: a hub the kernel holds down cannot carry fresh word "
                         "about it, so its row is link-down with the hub's, roster kept")
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, False, True, [B])},
                         "the hub's exchange with its link up: both reachable again")

    def test_a_source_the_kernel_never_notified_has_no_link_state_and_is_gated_by_heard_alone(self):
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
                         "each gated by heard (and the TTL) alone")
        # a down notify for a host this process has not heard: its carried row is unreachable already (heard false),
        # and now also says the kernel holds its link down
        self._restart()
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (False, False, True, False, [B]),
                         "carried from the previous file, heard false, link-down true: unreachable, roster kept")
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]))

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
