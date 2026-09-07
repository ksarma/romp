#!/usr/bin/env python3
"""Three identity memos on the distiller's and grouper's read paths (P2 of the judge perf plan, first
commit, 2026-09-07), each pinned against the function it memoizes:

- _distill_due_t builds a parent -> children map per call; _distill_session now builds one per store
  (_kids_map) and hands it through _done_owed. Pure over the nodes, so the answer must not depend on
  who built the map.
- _live_prompt_since scanned every session's whole states log every pass; it is memoized on the file's
  (ino, mtime_ns, size).
- _view_cleared replayed cleared.jsonl at each of eight call sites; same memo, same key.

The two file memos are exact because both files are APPEND-ONLY logs (every kernel writer opens them
"a"): no two versions share a size, so the identity moves on every write. The one write an identity memo
cannot see is a rewrite in place of equal size within one mtime tick, which no writer of these files
does; the tests below cover the rewrite that lands in a later tick (the shape a test fixture produces)
and the changed, unchanged, absent and unreadable cases against the unmemoized scan.

PRIVATE synthetic sid, invented text; nothing here mints goals through the store loader."""
import json
import os
import shutil
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_identity_memos", os.path.join(BIN, "romp-judge"))

SID = "cccccccc-1111-2222-3333-444444444444"      # a private synthetic sid, never the shared placeholder
T0 = 1781100000


def _rewrite_same_size_later_tick(path, text):
    """Rewrite `path` in place with `text` of the SAME size and move its mtime one second on, the shape a
    fixture's write_text produces when the tick has moved: same inode, same size, new mtime."""
    st = os.stat(path)
    Path(path).write_text(text)
    assert os.stat(path).st_size == st.st_size, "the rewrite must keep the size for this case to mean anything"
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


class _Memos(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self._saved_state = jd.STATE
        jd._rebind_state(self.td)
        jd.STATESDIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        jd._rebind_state(self._saved_state)
        shutil.rmtree(self.td, ignore_errors=True)

    def _count(self, name):
        """Patch the unmemoized scan `name` with a counting wrapper; returns the counter list."""
        real = getattr(jd, name)
        calls = []

        def counted(path):
            calls.append(path)
            return real(path)
        setattr(jd, name, counted)
        self.addCleanup(setattr, jd, name, real)
        return calls


class KidsMap(_Memos):
    """_distill_due_t and _done_owed answer the same with a caller-built map as with their own."""

    def _store(self):
        def nd(nid, parent, **kw):
            d = {"id": nid, "parentId": parent, "text": "step %s" % nid, "t": T0, "mt": T0 + 10, "log": []}
            d.update(kw)
            return d
        g = lambda n: "%s:g%d" % (SID, n)
        nodes = {
            g(1): nd(g(1), None, settledAt=T0 + 400, summary="done", distilledMt=T0 + 300),
            g(2): nd(g(2), g(1), log=[{"kind": "done", "ev_t": T0 + 200, "at": T0 + 201}]),
            g(3): nd(g(3), g(1), blocked=True,
                     log=[{"kind": "block", "ev_t": T0 + 150, "at": T0 + 150},
                          {"kind": "done", "ev_t": T0 + 300, "at": T0 + 305}]),
            g(4): nd(g(4), g(3), blocked=True, log=[{"kind": "block", "ev_t": T0 + 250, "at": T0 + 250}]),
            g(5): nd(g(5), None, settledAt=None, summary=None),                    # no events: the mt fallback
            g(6): nd(g(6), g(5), log=[{"kind": "block", "ev_t": T0 + 50, "at": T0 + 50}]),   # blocked flag unset
            g(7): nd(g(7), None, summary="s", distilledMt=T0 + 10,
                     log=[{"kind": "settle", "ev_t": T0 + 10, "at": T0 + 10}]),
        }
        return {"rompUuid": SID, "nodes": nodes, "status": {g(1): "completed", g(5): "working", g(7): "completed"}}

    def test_kids_map_is_the_inline_build(self):
        store = self._store()
        inline = {}
        for x, d in store["nodes"].items():
            inline.setdefault(d.get("parentId"), []).append(x)
        self.assertEqual(jd._kids_map(store["nodes"]), inline)

    def test_due_t_and_done_owed_agree_with_and_without_a_caller_map(self):
        store = self._store()
        kids = jd._kids_map(store["nodes"])
        for nid in store["nodes"]:
            for blocked in (False, True):
                self.assertEqual(jd._distill_due_t(store, nid, blocked, kids),
                                 jd._distill_due_t(store, nid, blocked), (nid, blocked))
        for nid in [n for n, d in store["nodes"].items() if d["parentId"] is None]:
            self.assertEqual(jd._done_owed(store, nid, kids), jd._done_owed(store, nid), nid)
        # the values themselves, so the fixture is known to exercise every branch: subtree done, subtree
        # still-blocked blocks, the mt and settledAt fallbacks
        g = lambda n: "%s:g%d" % (SID, n)
        self.assertEqual(jd._distill_due_t(store, g(1), False, kids), T0 + 300, "newest done in the subtree")
        self.assertEqual(jd._distill_due_t(store, g(1), True, kids), T0 + 250, "newest block among STILL-blocked nodes")
        self.assertEqual(jd._distill_due_t(store, g(5), False, kids), T0 + 10, "no done event, no settledAt: mt")
        self.assertEqual(jd._distill_due_t(store, g(5), True, kids), T0 + 10, "g6's block does not count: it is not blocked now")
        self.assertTrue(jd._done_owed(store, g(5), kids), "no summary: owed")
        self.assertFalse(jd._done_owed(store, g(7), kids), "the stamp matches a settle event and no newer done exists")


class LivePromptSince(_Memos):
    def _rows(self, *rows):
        return "\n".join(json.dumps(r) for r in rows) + "\n"

    def test_changed_unchanged_absent_and_the_later_tick_rewrite_agree_with_the_scan(self):
        p = jd.STATESDIR / (SID + ".jsonl")
        self.assertIsNone(jd._live_prompt_since(SID), "no states file: None, no entry")
        self.assertNotIn(str(p), jd._LIVE_PROMPT_MEMO)
        p.write_text(self._rows({"t": T0 + 10, "state": "working"}, {"t": T0 + 50, "state": "picker"},
                                {"t": T0 + 60, "state": "permission"}))
        calls = self._count("_live_prompt_since_scan")
        self.assertEqual(jd._live_prompt_since(SID), jd._live_prompt_since_scan(p))
        self.assertEqual(jd._live_prompt_since(SID), T0 + 50, "the run's start")
        self.assertEqual(len(calls), 2, "one scan for the memo fill, one for the comparison; the second call was a hit")
        with open(p, "a") as f:                                          # the kernel's shape: a row appended
            f.write(json.dumps({"t": T0 + 90, "state": "idle"}) + "\n")
        self.assertEqual(jd._live_prompt_since(SID), jd._live_prompt_since_scan(p))
        self.assertIsNone(jd._live_prompt_since(SID), "left the prompt: no episode")
        self.assertEqual(len(calls), 4, "the append moved the identity: one scan, then a hit")
        # a same-size rewrite in place that lands in a later mtime tick (a fixture's write_text): the mtime
        # moves, the memo misses, the new content is served. Same byte count, and the trailing row now
        # re-enters a prompt run at T0 + 91, so the answer changes with the content
        _rewrite_same_size_later_tick(p, self._rows({"t": T0 + 10, "state": "working"}, {"t": T0 + 50, "state": "picker"},
                                                    {"t": T0 + 60, "state": "permission"}, {"t": T0 + 91, "state": "pick"}))
        self.assertEqual(jd._live_prompt_since(SID), jd._live_prompt_since_scan(p), "a later-tick rewrite is seen")
        self.assertIsNone(jd._live_prompt_since(SID), '"pick" is not a prompt state: the control case')
        _rewrite_same_size_later_tick(p, self._rows({"t": T0 + 10, "state": "worki"}, {"t": T0 + 50, "state": "picker"},
                                                    {"t": T0 + 60, "state": "permission"}, {"t": T0 + 91, "state": "picker"}))
        self.assertEqual(jd._live_prompt_since(SID), jd._live_prompt_since_scan(p))
        self.assertEqual(jd._live_prompt_since(SID), T0 + 50,
                         "picker, permission, picker is ONE run: the rewritten tail re-opened the episode at its start")
        p.unlink()
        self.assertIsNone(jd._live_prompt_since(SID))
        self.assertNotIn(str(p), jd._LIVE_PROMPT_MEMO, "an absent file drops its entry")

    @unittest.skipIf(os.geteuid() == 0, "root reads a mode-000 file")
    def test_an_unreadable_file_answers_none_and_is_not_memoized(self):
        p = jd.STATESDIR / (SID + ".jsonl")
        p.write_text(self._rows({"t": T0 + 50, "state": "picker"}))
        os.chmod(p, 0)
        try:
            self.assertIsNone(jd._live_prompt_since(SID))
            self.assertNotIn(str(p), jd._LIVE_PROMPT_MEMO)
        finally:
            os.chmod(p, 0o644)
        self.assertEqual(jd._live_prompt_since(SID), T0 + 50, "readable again: the real answer, no stale None")


class ViewCleared(_Memos):
    def test_changed_unchanged_absent_and_the_later_tick_rewrite_agree_with_the_scan(self):
        p = jd.STATE / "cleared.jsonl"
        self.assertEqual(jd._view_cleared(), frozenset(), "no file: empty")
        a, b = SID + ":g1", SID + ":g2"
        p.write_text(json.dumps({"id": a, "t": T0, "op": "clear"}) + "\n")
        calls = self._count("_view_cleared_scan")
        self.assertEqual(jd._view_cleared(), jd._view_cleared_scan(p))
        self.assertEqual(jd._view_cleared(), {a})
        self.assertEqual(len(calls), 2, "the second call was a hit")
        with open(p, "a") as f:                                          # the kernel's shape: rows appended
            f.write(json.dumps({"id": b, "t": T0 + 1, "op": "clear"}) + "\n")
            f.write(json.dumps({"id": a, "t": T0 + 2, "op": "undo"}) + "\n")
        self.assertEqual(jd._view_cleared(), jd._view_cleared_scan(p))
        self.assertEqual(jd._view_cleared(), {b}, "undo removes, newest wins")
        self.assertEqual(len(calls), 4)
        # a same-size rewrite in place landing in a later tick: seen
        text = p.read_text().replace('"op": "undo"', '"op": "redo"')      # same length; "redo" is not an undo
        _rewrite_same_size_later_tick(p, text)
        self.assertEqual(jd._view_cleared(), jd._view_cleared_scan(p))
        self.assertEqual(jd._view_cleared(), {a, b})
        p.unlink()
        self.assertEqual(jd._view_cleared(), frozenset())
        self.assertNotIn(str(p), jd._VIEW_CLEARED_MEMO)

    def test_the_answer_is_immutable_and_a_rebind_starts_empty(self):
        p = jd.STATE / "cleared.jsonl"
        p.write_text(json.dumps({"id": SID + ":g1", "t": T0, "op": "clear"}) + "\n")
        vc = jd._view_cleared()
        with self.assertRaises(AttributeError):
            vc.add("x")                                                  # a caller mutating the shared memo fails loudly
        self.assertIn(str(p), jd._VIEW_CLEARED_MEMO)
        other = Path(tempfile.mkdtemp())
        try:
            jd._rebind_state(other)
            self.assertEqual(jd._VIEW_CLEARED_MEMO, {})
            self.assertEqual(jd._LIVE_PROMPT_MEMO, {})
            self.assertEqual(jd._view_cleared(), frozenset(), "the new root has no cleared.jsonl")
        finally:
            jd._rebind_state(self.td)
            shutil.rmtree(other, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
