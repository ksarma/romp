#!/usr/bin/env python3
"""A dissolved container's rolled-up child reads as its own diary, and settles nothing it never earned
(review 2026-09-06). rollup_status's roll-down folds a resolved top's open children into an eventless
display cache (nodeComplete plus the rolledUp marker); _materialize_from_log and record_verdict both skip
a rolledUp node, because an ANCESTOR's resolution owns those flags. Umbrella dissolution (T101) re-parented
such a child to top level without dropping the marker, so the promoted top kept a done flag nothing ever
re-derived: is_complete read it, the settle branch never found settledDone (the settle row it appended
never materialized), and every rollup appended one more settle row plus one more seam. One live node
reached LOG_CAP (64 settle rows, logTrunc) with its store's seams at cap, republishing about 1 MB per pass.

Pins: (1) the dissolving rollup drops the marker and the child's own diary rules (no row: open; a
rolled-away block: blocked), with no settle row, no seam and no churn on later rollups; (2) a promoted
child with its OWN done verdict settles exactly once; (3) a child re-parented under a still-resolved solid
ancestor is re-folded by the same rollup's roll-down; (4) a store already published with the stale marker
heals on its next rollup (one publish) and then goes quiet. SYNTHETIC fixtures only; a private synthetic
sid (goal-store tests never share the placeholder sid)."""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = SourceFileLoader("romp_judge_dissolve_rolledup", os.path.join(BIN, "romp-judge")).load_module()

SID = "d1550001-1111-4222-8333-000000000001"    # private synthetic sid, never the shared placeholder
T = 1781100000
UMB, CHILD, OTHER, TOP = (SID + ":g%d" % i for i in (1, 2, 3, 4))


def _row(kind, ev, src="closer", why=None):
    return {"ev_t": ev, "src": src, "kind": kind, **({"why": why} if why else {}), "at": ev}


def _node(nid, text, parent, t=T, **kw):
    nd = {"id": nid, "text": text, "parentId": parent, "nodeComplete": False, "blocked": False,
          "cleared": False, "trail": [], "t": t, "mt": t, "log": []}
    nd.update(kw)
    return nd


def _rolled(nid, text, parent, log=None):
    """A child the roll-down folded: display-cache done plus the marker, no done verdict of its own."""
    return _node(nid, text, parent, nodeComplete=True, rolledUp=True, log=list(log or []))


def _settles(nd):
    return [e for e in (nd.get("log") or []) if e.get("kind") == "settle"]


class _Base(unittest.TestCase):
    def setUp(self):
        self._saved = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))

    def tearDown(self):
        try:
            (jd._overrides_dir() / (SID + ".jsonl")).unlink()
        except OSError:
            pass
        jd._rebind_state(self._saved)
        self.td.cleanup()

    def _store(self, nodes):
        st = {"rompUuid": SID, "seq": len(nodes) + 1, "placements": {}, "status": {},
              "placementsV": jd.PLACEMENTS_V, "lastNode": OTHER, "nodes": {}}
        for nd in nodes:
            st["nodes"][nd["id"]] = nd
        st["nodes"][OTHER] = _node(OTHER, "tests for the api", None, t=T + 10)   # the focus: unrelated, open
        return jd._guard_nodes(st)

    def _umbrella_world(self, child_log=None):
        """The live shape: a closer-ruled-done container over one child the roll-down folded."""
        return self._store([
            _node(UMB, "round of notes-api work", None, umbrella=True, nodeComplete=True,
                  log=[_row("done", T, why="the round shipped")]),
            _rolled(CHILD, "add the web pane", UMB, child_log)])


class DissolutionDropsTheMarker(_Base):
    def test_the_promoted_child_reads_its_own_diary_and_settles_nothing(self):
        st = self._umbrella_world()
        jd.rollup_status(st, True)
        c = st["nodes"][CHILD]
        self.assertNotIn(UMB, st["nodes"], "premise: the container dissolved")
        self.assertIsNone(c.get("parentId"), "premise: the child is a top now")
        self.assertNotIn("rolledUp", c, "the marker leaves with the container whose resolution it mirrored")
        self.assertFalse(c.get("nodeComplete"), "no verdict of its own: its diary says open")
        self.assertEqual(st["status"][CHILD], "working")
        self.assertEqual(_settles(c), [], "nothing completed, so nothing settles: no settle row")
        self.assertEqual(st.get("seams") or [], [], "and no seam")
        self.assertNotIn("settledDone", c)
        before = jd._store_content(st)
        jd.rollup_status(st, True)
        self.assertEqual(jd._store_content(st), before, "a second rollup changes nothing")

    def test_a_rolled_away_block_resurfaces_on_the_promoted_child(self):
        st = self._umbrella_world(child_log=[_row("block", T - 5, why="which pane layout?")])
        jd.rollup_status(st, True)
        c = st["nodes"][CHILD]
        self.assertNotIn("rolledUp", c)
        self.assertTrue(c.get("blocked"), "its own diary rules: the block the roll-down hid is back")
        self.assertEqual(st["status"][CHILD], "blocked")
        self.assertEqual(_settles(c), [])

    def test_a_promoted_child_with_its_own_done_verdict_settles_exactly_once(self):
        # the roll-down never marks a child that is already complete, so this child carries no marker:
        # the legitimately-done sibling settles ONCE (one row, one seam, settledDone) and then holds
        st = self._store([
            _node(UMB, "round of notes-api work", None, umbrella=True),
            _node(CHILD, "add the web pane", UMB, nodeComplete=True,
                  log=[_row("done", T, why="the pane shipped")])])
        jd.rollup_status(st, True)
        jd.rollup_status(st, True)
        c = st["nodes"][CHILD]
        self.assertIsNone(c.get("parentId"))
        self.assertEqual(st["status"][CHILD], "completed")
        self.assertTrue(c.get("settledDone"), "the settle row materialized on the promoted top")
        self.assertEqual(len(_settles(c)), 1, "one settle row across two rollups")
        self.assertEqual(len(st.get("seams") or []), 1, "one seam across two rollups")
        before = jd._store_content(st)
        jd.rollup_status(st, True)
        self.assertEqual(jd._store_content(st), before)

    def test_a_child_under_a_still_resolved_solid_ancestor_is_refolded_by_the_same_rollup(self):
        # nested: a solid done top over a container over a folded child. The child re-parents to the
        # top, whose own roll-down re-derives the cache in this very rollup (the marker is a mirror of
        # the nearest resolved ancestor, and that ancestor still stands)
        st = self._store([
            _node(TOP, "ship the notes-api release", None, nodeComplete=True,
                  log=[_row("done", T, why="released")]),
            _node(UMB, "round of notes-api work", TOP, umbrella=True, nodeComplete=True, rolledUp=True),
            _rolled(CHILD, "add the web pane", UMB)])
        jd.rollup_status(st, True)
        c = st["nodes"][CHILD]
        self.assertEqual(c.get("parentId"), TOP, "re-parented to the first solid ancestor")
        self.assertTrue(c.get("rolledUp") and c.get("nodeComplete"),
                        "the resolved ancestor still stands over it: the roll-down re-folds it")
        self.assertEqual(_settles(c), [], "a sub never settles")
        self.assertEqual(len(_settles(st["nodes"][TOP])), 1, "the top settles once")


class StaleMarkerHeals(_Base):
    def test_a_store_published_with_the_stale_marker_heals_on_its_next_rollup_then_goes_quiet(self):
        # the shape HEAD left on disk: the container already gone, the child a top still wearing the
        # marker, its diary holding the settle rows earlier rollups appended, seams stamped alongside
        spam = [_row("settle", T + 10, src="romp") for _ in range(3)]
        st = self._store([_rolled(CHILD, "add the web pane", None, spam)])
        st["seams"] = [{"t": T + 100 + i, "top": CHILD, "text": "add the web pane", "segs": []}
                       for i in range(3)]
        jd.save_goals(SID, st)
        rev0 = jd._disk_rev(SID)
        s1 = jd.load_goals(SID)
        jd.rollup_status(s1, True)
        jd.save_goals(SID, s1)                                   # the heal is one publish
        c = s1["nodes"][CHILD]
        self.assertNotIn("rolledUp", c, "a top has no ancestor to mirror: the marker is dropped")
        self.assertFalse(c.get("nodeComplete"), "its own diary has no done row")
        self.assertEqual(s1["status"][CHILD], "working")
        self.assertEqual(len(_settles(c)), 3, "no settle row appended")
        self.assertEqual(len(s1["seams"]), 3, "no seam appended")
        rev1 = jd._disk_rev(SID)
        self.assertGreater(rev1, rev0, "the heal is a real change: one publish")
        s2 = jd.load_goals(SID)
        jd.rollup_status(s2, True)
        jd.save_goals(SID, s2)
        self.assertEqual(jd._disk_rev(SID), rev1, "then the store is quiet: no republish per pass")


if __name__ == "__main__":
    unittest.main()
