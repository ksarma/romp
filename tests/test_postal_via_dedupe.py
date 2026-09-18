#!/usr/bin/env python3
"""A box that is DIRECTLY peered must never also present — or route — as "reachable via relay"
(the user 2026-08-12). The name test alone missed it: the same machine wears different ssh
aliases on different hosts, so the hub gossips the spoke under a name the receiver doesn't
recognize as its own direct peer. Identity now rides the gossip as the far bus's own id
(fleet_presence viaBus) — the thing the exchange already proves, immune to nickname drift — and
one shared test (_via_duplicate: bus id first, name for hubs that predate the field) folds the
duplicates everywhere gossip is consumed: the popover rows (via_reach), addressing (peer_route —
where the duplicate read as a FALSE ambiguity, or worse picked the relay hop a direct link
already covers), and the agent list (the doubled '[remote]' rows).

Synthetic hosts, ids, and bus ids throughout; hermetic state dir; no sockets.

Under pytest-xdist over the whole tests/ directory (-n 4) PeerRoutePrefersDirect's
test_resolve_recipient_lands_direct_with_no_ambiguity_error is red ('error' != 'relay') while this module alone is
green (8 passed), and so is this module beside tests/test_sdk_backend.py under -n 4. The leaked global is the
environment: tests/test_kernel_tunnels.py set ROMP_POSTAL_PEERS=0 at module level (until 2026-09-18, when the value
moved into that module's per-test setUp and tearDown after the kernel's remote-identity absorb case went red the same
way in 5 of 6 full runs), every xdist worker imports every collected module before it runs a test, and the service's
peers_on() reads the variable at call time, so resolve_recipient consults no peer route and answers an error where the
relay is expected (diagnosed 2026-09-16; reproduced with no xdist by running that module before this one in one pytest
process). Judge a red here by the
module alone: `python3 -m pytest tests/test_postal_via_dedupe.py -q`. The postal modules that set ROMP_POSTAL_PEERS=1
in setUp never saw the leak; since 2026-09-16 this one pins the variable itself too (_Seeded.setUp sets it to 1 and
tearDown restores what it found), so the red above is the fails-before and the case reads the peer route whatever an
earlier module left.
"""
import os
import tempfile
import time
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_viadedupe", os.path.join(BIN, "romp-postal-service"))

WEB_ID = "11111111-1111-1111-1111-111111111111"
HUB_ID = "22222222-2222-2222-2222-222222222222"
FAR_ID = "33333333-3333-3333-3333-333333333333"


class _Seeded(unittest.TestCase):
    """The user's shape: a spoke peered directly under OUR alias, and a hub that gossips the same
    box under ITS OWN name for it (names differ; bus ids agree)."""

    def setUp(self):
        self._peers, self._pstate = dict(pm.PEERS), dict(pm.PEER_STATE)
        # the peer route is gated by peers_on(), read per call: pin it on here, whatever an earlier module in the
        # same process left (tests/test_kernel_tunnels.py set 0 at module level until 2026-09-18; the header says why), restored below
        self._peers_env = os.environ.get("ROMP_POSTAL_PEERS")
        os.environ["ROMP_POSTAL_PEERS"] = "1"
        pm.PEERS.clear()
        pm.PEER_STATE.clear()
        now = int(time.time())
        # hub FIRST in insertion order, so consumers meet the gossiped duplicate before the
        # direct row — the ordering that would have hidden a keep-the-first bug
        pm.PEERS["hub"] = {"port": 12, "up": True}
        pm.PEER_STATE["hub"] = {"busId": "bus-HHHH", "seenAt": now, "presence": [
            {"name": "hubapp", "id": HUB_ID},
            # the SAME box we peer with directly, under the hub's different nickname for it
            {"name": "web", "id": WEB_ID, "via": "spoke-other-name", "viaBus": "bus-AAAA"},
            # a genuine far spoke: no direct link here — must keep presenting via relay
            {"name": "farapp", "id": FAR_ID, "via": "farbox", "viaBus": "bus-FFFF"},
        ]}
        pm.PEERS["spokealias"] = {"port": 11, "up": True, "trust": "trusted"}
        pm.PEER_STATE["spokealias"] = {"busId": "bus-AAAA", "seenAt": now, "presence": [
            {"name": "web", "id": WEB_ID},
        ]}

    def tearDown(self):
        pm.PEERS.clear()
        pm.PEERS.update(self._peers)
        pm.PEER_STATE.clear()
        pm.PEER_STATE.update(self._pstate)
        if self._peers_env is None:
            os.environ.pop("ROMP_POSTAL_PEERS", None)
        else:
            os.environ["ROMP_POSTAL_PEERS"] = self._peers_env


class ViaReachFolds(_Seeded):
    def test_a_directly_peered_box_never_shows_as_via_relay(self):
        rows = {r["host"]: r for r in pm.via_reach()}
        self.assertNotIn("spoke-other-name", rows,
                         "the hub's nickname differs, but the bus id proves it is our direct peer")
        self.assertNotIn("spokealias", rows)

    def test_a_genuine_far_spoke_still_presents(self):
        rows = {r["host"]: r for r in pm.via_reach()}
        self.assertIn("farbox", rows, "no direct link exists — via relay is real reach")
        self.assertEqual(rows["farbox"]["via"], "hub")

    def test_an_old_hub_without_the_id_still_folds_matching_names(self):
        # a hub that predates viaBus: the name path keeps today's behavior
        pm.PEER_STATE["hub"]["presence"].append({"name": "web2", "id": FAR_ID, "via": "spokealias"})
        rows = {r["host"]: r for r in pm.via_reach()}
        self.assertNotIn("spokealias", rows)


class PeerRoutePrefersDirect(_Seeded):
    def test_no_false_ambiguity_and_the_direct_link_carries_the_mail(self):
        host, agent = pm.peer_route("web")
        self.assertEqual(host, "spokealias", "one candidate, and it is the direct peer — never the hub")
        self.assertEqual(agent.get("id"), WEB_ID)
        self.assertFalse(agent.get("via"), "the chosen row is the direct one")

    def test_two_hubs_gossiping_one_session_is_one_candidate(self):
        pm.PEERS["hub2"] = {"port": 13, "up": True}
        pm.PEER_STATE["hub2"] = {"busId": "bus-JJJJ", "seenAt": int(time.time()), "presence": [
            {"name": "farapp", "id": FAR_ID, "via": "farbox-alias", "viaBus": "bus-FFFF"},
        ]}
        host, agent = pm.peer_route("farapp")
        self.assertIsNotNone(host, "one session seen along two relay paths is ONE candidate, not two")
        self.assertEqual(agent.get("id"), FAR_ID)

    def test_resolve_recipient_lands_direct_with_no_ambiguity_error(self):
        pm.local_agents, saved = (lambda threads=False: []), pm.local_agents
        try:
            r = pm.resolve_recipient("web", frm_id=HUB_ID)
        finally:
            pm.local_agents = saved
        self.assertEqual(r.get("kind"), "relay")
        self.assertEqual(r.get("host"), "spokealias")


class GossipCarriesIdentity(_Seeded):
    def test_fleet_presence_rides_the_far_bus_id_on_via_rows(self):
        pm.local_agents, saved = (lambda threads=False: []), pm.local_agents
        try:
            rows = pm.fleet_presence("asker")
        finally:
            pm.local_agents = saved
        gossiped = [r for r in rows if r.get("via")]
        self.assertTrue(gossiped)
        for r in gossiped:
            self.assertIn("viaBus", r)
        by_via = {r["via"]: r for r in gossiped}
        self.assertEqual(by_via["spokealias"]["viaBus"], "bus-AAAA")

    def test_the_agents_list_wiring_folds_duplicates_too(self):
        # the /agents handler is inline — pin its wiring; the folding behavior itself is
        # exercised through via_reach/peer_route above (same _via_duplicate)
        with open(os.path.join(BIN, "romp-postal-service")) as f:
            src = f.read()
        self.assertIn("if _via_duplicate(pa, direct_bus):", src)
        self.assertIn("if sid and sid in listed:", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
