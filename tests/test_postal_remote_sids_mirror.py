#!/usr/bin/env python3
"""The postal bus's presence mirror (the bus's STATE/remote-sids, <state root>/postal/remote-sids), the
file kernel/judge's dead-session ladder reads for rules 4 and 5 (_presumed_closed_verdict). Since fork PR
#897's round 2 the mirror is a document, one row per PRESENCE SOURCE with the roster it last reported and
whether THIS bus process can vouch for it (postal_service.py _remote_sids_document): `heard` (a heartbeat or
exchange arrived in this process), `expired` (a legacy heartbeat past HEARTBEAT_TTL), `sids`. The reader
counts a source reachable when heard and not expired, and presumes a sid closed only when a reachable
source exists and none names it. Two roads to a false settle closed here, at the writer:
  (1) a bus restarted from empty memory wrote its first mirror from that memory, naming nobody: every key
      the previous file named that this process has not heard is CARRIED FORWARD, its roster kept, heard
      false, until its heartbeat or exchange arrives (the event);
  (2) an expired legacy heartbeat was PRUNED, so a stalled peer past the TTL removed a live session's
      sid: the row stays, marked expired, until the next beat (the event).
Pinned here, by writing through the real writer and reading the file back: the document's shape; one
source per heartbeat with its own TTL; a peer's own rows under its name and its gossip under the far host
it speaks for, with gossip about a directly held host folded (the direct row speaks); a PEER_STATE row no
exchange produced is not a source; the carry-forward across a restart and its release per host; the fold
of a carried row for a bus heard under its other name; the whitespace list of the shape until 2026-09-22
carried as one legacy source and pruned as heard sources name its sids; a file of neither shape carrying
nothing; a write failure said once in the bus log. tests/test_dead_session_staleness.py ReaderFollowsTheWriter
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

    def _peer(self, host, presence, seen_ago=5, bus_id=None):
        st = {"presence": presence, "epoch": 1, "holds": [], "seenAt": int(self.now - seen_ago)}
        if bus_id:
            st["busId"] = bus_id
        pm.PEER_STATE[host] = st

    def _restart(self):
        """A restarted bus process's memory: nothing heard yet, the file still on disk."""
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear()

    def test_the_document_shape(self):
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}], bus_id="bus-1")
        pm._write_remote_sids()
        doc = self._doc()
        self.assertEqual(sorted(doc), ["busStarted", "hosts", "v", "writtenAt"])
        self.assertEqual((doc["v"], doc["busStarted"]), (2, pm.BUS_EPOCH), "the writing process's boot second")
        self.assertIsInstance(doc["writtenAt"], int)
        self.assertEqual(doc["hosts"][HB + A], {"kind": "heartbeat", "sids": [A], "heard": True, "expired": False,
                                                 "seenAt": int(self.now), "name": "web"})
        self.assertEqual(doc["hosts"][HOST], {"kind": "peer", "sids": [B], "heard": True, "expired": False,
                                              "seenAt": int(self.now - 5), "busId": "bus-1"})
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
