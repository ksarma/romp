#!/usr/bin/env python3
"""kernel/judge.py binds ONE module-level `_top_of`: the closer helpers' body, "the top-level ancestor of nid
(cycle-safe)", which returns the last id its parent walk reached. Upstream's T319 origin rule (romp-on/romp#1367,
2026-09-10) added a second definition above `_demote_session_mints` that returned None when the parent chain
dead-ended; Python binds the later definition, so that first body never ran and every T319 caller has always seen the
id-returning one. The fork removed the dead first definition in the stage 1 pull-in of upstream 14f1548a9 (the kernel
area's review round 1, item 5; the ledger entry upstream/2026-09-16-judge-top-of-double-definition.md) and this module
makes the callers' behaviour on a DEAD-ENDED chain explicit: the top of a node whose ancestor a rewind swept is the
last id reached, the dangling parent id, never None. The guarded callers read that id as no top (`nodes.get(top) or
{}`); `_demote_session_mints` dereferences it and fails loudly.

Synthetic fixtures only: a PRIVATE synthetic sid (never the shared placeholder, per the goal-store fixture rule), an
invented project, no store file and no journal (tearDown clears this sid's override journal all the same)."""
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_top_of", os.path.join(BIN, "romp-judge"))

SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeee1"     # this module's PRIVATE synthetic sid
T0 = 1781100000


def gid(n):
    return SID + ":g%d" % n


GHOST = gid(0)                                   # a parent id no node carries: the node a rewind swept


def node(n, text, parent=None, **extra):
    nd = {"id": gid(n), "text": text, "parentId": parent, "nodeComplete": False, "cleared": False,
          "t": T0 + n, "promptUuid": "u%d" % n}
    nd.update(extra)
    return nd


def make_store(*nodes):
    return {"rompUuid": SID, "seq": len(nodes), "placements": {}, "nodes": {nd["id"]: nd for nd in nodes}}


class _Base(unittest.TestCase):
    def tearDown(self):
        # the goal-store fixture rule: this sid's override journal never outlives the module
        try:
            os.remove(str(jd._overrides_dir() / (SID + ".jsonl")))
        except FileNotFoundError:
            pass

    def _forest(self, **tops):
        """Three chains in one store: ROOTED (g3 under g2 under the top g1), DEAD-ENDED (g5 under g4, whose parent
        GHOST is no node), and a two-node CYCLE (g6 and g7). `tops` adds fields to g1 and g4, the highest surviving
        node of each of the first two chains, so a case can give both the same fields and vary the chain alone."""
        return make_store(
            node(1, "Add retries to the notes-api client", **tops),
            node(2, "Wrote the retry loop", parent=gid(1)),
            node(3, "Ran the retry tests", parent=gid(2)),
            node(4, "Rename the widget colours", parent=GHOST, **tops),
            node(5, "Listed the colour tokens", parent=gid(4)),
            node(6, "Cycle head", parent=gid(7)),
            node(7, "Cycle tail", parent=gid(6)),
        )


class TopOf(_Base):
    def test_the_module_defines_top_of_once_the_id_returning_body(self):
        with open(os.path.join(os.path.dirname(HERE), "kernel", "judge.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("\ndef _top_of("), 1, "one definition: the None-returning first body is gone")
        self.assertEqual(jd._top_of.__doc__, "The top-level ancestor of nid (cycle-safe).")

    def test_a_top_is_its_own_top_and_a_rooted_chain_walks_to_it(self):
        nodes = self._forest()["nodes"]
        self.assertEqual(jd._top_of(nodes, gid(1)), gid(1))
        self.assertEqual(jd._top_of(nodes, gid(2)), gid(1))
        self.assertEqual(jd._top_of(nodes, gid(3)), gid(1))

    def test_a_dead_ended_chain_returns_the_last_id_reached_never_none(self):
        nodes = self._forest()["nodes"]
        self.assertNotIn(GHOST, nodes)
        for nid in (gid(4), gid(5)):
            top = jd._top_of(nodes, nid)
            self.assertIsNotNone(top, "the retired first body's contract: never this one's")
            self.assertEqual(top, GHOST, "the dangling parent id, the last id the walk reached")
            self.assertNotIn(top, nodes)
        self.assertEqual(jd._top_of(nodes, gid(9)), gid(9), "an id no node carries is its own top")

    def test_a_cycle_closes_the_walk_without_hanging(self):
        nodes = self._forest()["nodes"]
        self.assertEqual(jd._top_of(nodes, gid(6)), gid(6), "the walk stops at the first id it revisits")
        self.assertEqual(jd._top_of(nodes, gid(7)), gid(7))


class T319CallersOnADeadEndedChain(_Base):
    """The origin rule's callers, each given the rooted chain and the dead-ended chain with the same fields on the
    chain's highest surviving node; only the chain differs."""

    def test_the_delegator_is_read_from_the_top_so_a_dead_ended_chain_has_none(self):
        store = self._forest(origin={"peer": "web"})
        self.assertEqual(jd._delegator_of(store, gid(3)), "web", "rooted: the top's courier-planted origin")
        self.assertIsNone(jd._delegator_of(store, gid(5)), "dead-ended: the top is the ghost, which has no origin")
        self.assertIsNone(jd._delegator_of(store, gid(4)), "the node's OWN origin is never the top's")

    def test_a_block_under_a_dead_ended_chain_stays_the_users_own(self):
        store = self._forest(origin={"peer": "web"})
        handoff = {"peer": "web", "t": T0 + 50}
        store["nodes"][gid(3)]["handoff"] = dict(handoff)
        store["nodes"][gid(5)]["handoff"] = dict(handoff)
        why = "which colour should the widget use?"
        self.assertEqual(jd.block_addressee_via(store, store["nodes"][gid(3)], why), ("web", "ask"),
                         "rooted under a delegated top: the block waits on the peer the handoff names")
        self.assertEqual(jd.block_addressee_via(store, store["nodes"][gid(5)], why), (None, None),
                         "dead-ended: no delegator, so the block is the user's own decision")

    def test_a_split_under_a_dead_ended_chain_still_promotes_the_step_and_borrows_no_anchor(self):
        store = self._forest(askAnchor="human", askAnchorRecord={"kind": "typed"}, promptMsgId="m1")
        op = [{"do": "split", "goal": 1, "why": "a drifted tangent"}]
        self.assertEqual(jd.apply_group(store, [{"id": gid(3)}], list(op), T0 + 500), 1)
        g3 = store["nodes"][gid(3)]
        self.assertIsNone(g3["parentId"])
        self.assertEqual((g3.get("askAnchor"), g3.get("promptMsgId")), ("human", "m1"),
                         "rooted: the human top's verdict comes along with the promoted step")
        self.assertEqual(jd.apply_group(store, [{"id": gid(5)}], list(op), T0 + 500), 1)
        g5 = store["nodes"][gid(5)]
        self.assertIsNone(g5["parentId"], "the step still becomes a card of its own")
        self.assertNotIn("askAnchor", g5, "dead-ended: the ghost has no verdict to borrow")
        self.assertNotIn("promptMsgId", g5)

    def test_a_process_mint_placed_under_a_dead_ended_chain_fails_loudly(self):
        """The one T319 caller that does not guard the result. A seam tail (or a target, or a recorded placement)
        naming a node under a dead-ended chain hands `parent` the dangling id, and the process mint's nest
        dereferences it: a KeyError naming the ghost, the pass's loud failure. The retired first body would have
        answered None here and the mint would have nested under the nearest open top or the reply's own ask, or
        filed nothing; the fork keeps upstream's arm and records the choice in the ledger entry."""
        store = self._forest()
        menu = [{"id": nid} for nid in store["nodes"]]
        mint = {"do": "mint", "why": "a nightly review round", "text": "Guard review of the widget colours"}
        seg = {"id": "s1", "trigger": None, "atoms": [], "seamOf": {"top": gid(3), "text": "..."}}
        got = jd._demote_session_mints([dict(mint)], seg, store, menu, None, False)
        self.assertEqual(got, [{"do": "sub", "why": "a nightly review round", "parentId": gid(1),
                                "text": "Guard review of the widget colours",
                                "born": {"kind": "session", "via": "work", "why": "a nightly review round",
                                         "parentText": "Add retries to the notes-api client"}}],
                         "rooted: the step nests under the seam's own top")
        seg = {"id": "s1", "trigger": None, "atoms": [], "seamOf": {"top": gid(5), "text": "..."}}
        with self.assertRaises(KeyError) as cm:
            jd._demote_session_mints([dict(mint)], seg, store, menu, None, False)
        self.assertIn(GHOST, str(cm.exception), "it fails on the dangling id itself")


if __name__ == "__main__":
    unittest.main()
