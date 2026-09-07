"""build_feed's per-session memo (round-4 plan P2-A): the seam maps, the tree shape and each top
goal's flattened tree are pure functions of a session's parse and goal store, so they are kept per
session across builds and served while every input holds.

The memo may only return what the uncached computation would return NOW, so the tests here pin the
key one input at a time: a transcript append, a store publish, a journal append, a names write, a
working flip, a session-row rename and a changed remembered anchor each miss, and nothing else does.
The bypasses (a live-merge copy, a swallowed exception, an unkeyed store, a build outside the pusher's
names scope) never store. Rows are shared values: the serving fold lands on a copy, the tint is
stamped at serialization, and two builds over unchanged inputs hand back the same row objects. A
differential run over random perturbations checks the memoized build against a fresh one.

Synthetic fixtures only: sids private to this module (never the shared 11111111-2222 placeholder, see
CLAUDE.md), invented goal text, the demo names `web`/`api`/`tests`, hostname TESTHOST. Every test
rebinds STATE to a temp dir, so the journal rows it appends die with the test."""
import json
import os
import random
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_feedsegs", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SIDS = ["88888888-1111-4222-8333-44444444440%d" % i for i in range(3)]   # private to this module (synthetic)
SID, SID_B, SID_C = SIDS
NAMES = ("web", "api", "tests")
NOW = 1781400000
T0 = NOW - 3600


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _user(uuid, parent, t, text):
    return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "typed",
            "message": {"role": "user", "content": text}}


def _asst(uuid, parent, t, text):
    return {"type": "assistant", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}}


def _tops(feed, sid):
    """The goal cards of one session, by itemId."""
    return {a["itemId"]: a for a in feed["asks"] if a.get("sid") == sid and a.get("turnId")}


def _loop_out(feed):
    """What the per-session loop produces, serialized: the cards and the per-session lists. The frame's
    other top-level fields read state outside the loop (the session order file, the SDK notice rows) that
    the first build of a fresh world writes as a side effect, so they are not compared here."""
    return json.dumps({k: feed.get(k) for k in ("asks", "working", "awaiting", "bgServices", "userTodos", "userTodoRows")},
                      sort_keys=True)


class _World(unittest.TestCase):
    """Three sessions with parsed transcripts and goal stores whose trails resolve in the parse (warm
    anchors), one sub per store whose trail does not (a cold anchor), a handoff row (a names read for
    the recipient), a done sub and a blocked top."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.saved_state, self.saved_names = jd.STATE, km.NAMES
        jd._rebind_state(self.root)
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        km.NAMES = jd.NAMES
        for sid, name in zip(SIDS, NAMES):
            self._write_name(sid, name, "#1EA1EB")
        km._rewind_holds[0] = None
        km._rewind_kept_memo.clear()
        km._rewind_kept_err.clear()
        km._end_goals_pass()
        with km._FEED_SEGS_LOCK:
            km._feed_segs_memo.clear()
        km._node_anchor_last.clear()
        self.paths, self.seg_ids, self.tx_n = {}, {}, {}
        for sid in SIDS:
            self._transcript(sid)
        for i, sid in enumerate(SIDS):
            self._publish(sid, self._store_json(sid, SIDS[(i + 1) % 3]))
        self.sessions = [{"sid": sid, "name": nm, "path": self.paths[sid], "anchor": sid, "mtime": 0}
                         for sid, nm in zip(SIDS, NAMES)]
        self.tmux = {sid: {"state": "idle", "since": NOW - 50} for sid in SIDS}
        self.force_working = set()
        orig_working = km._session_working

        def working(turns):
            for sid in self.force_working:
                ps = km._parse_cached(self.paths[sid])
                if ps is not None and turns is ps["turns"]:
                    return True
            return orig_working(turns)
        self.patches = [mock.patch.object(km, "_alive_sessions", lambda now, tm: list(self.sessions)),
                        mock.patch.object(km, "_warm_fleet_bg", lambda now: None),
                        mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: list(self.sessions)),
                        mock.patch.object(km, "_sdk", lambda: None),
                        mock.patch.object(km, "_session_working", working)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.stats0 = dict(km._feed_segs_stats)
        self.poisoned0 = jd.shared_store_stats()["poisoned"]

    def tearDown(self):
        self.assertEqual(jd.shared_store_stats()["poisoned"] - self.poisoned0, 0, "a build wrote into a shared store")
        km._live_scope.names = None
        with km._FEED_SEGS_LOCK:
            km._feed_segs_memo.clear()
        km._node_anchor_last.clear()
        km._end_goals_pass()
        km._rewind_holds[0] = None
        km._rewind_kept_memo.clear()
        km._rewind_kept_err.clear()
        km.NAMES = self.saved_names
        jd._rebind_state(self.saved_state)
        self.td.cleanup()

    # ── fixtures ──
    def _write_name(self, sid, name, color):
        km._atomic_write(jd.NAMES / sid, "%s\t/proj/TESTHOST/notes-api\t%s\twhite\n" % (name, color))

    def _transcript(self, sid):
        p = self.root / (sid + ".jsonl")
        recs = [_user("u0", None, T0, "ship the notes api"), _asst("a0", "u0", T0 + 5, "The handler is written and wired."),
                _user("u1", "a0", T0 + 200, "and the flaky test?"), _asst("a1", "u1", T0 + 210, "It needs an auth decision.")]
        p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        self.paths[sid] = str(p)
        self.tx_n[sid] = 2
        ps = km._parse(str(p), sid, NOW)
        self.seg_ids[sid] = [km._segs_seam(t, {})[0]["id"] for t in ps["turns"]]
        return ps

    def _append_turn(self, sid):
        """One more settled turn on the transcript, parsed into the cache: a new parse object."""
        n = self.tx_n[sid]
        t = T0 + 300 * n
        recs = [_user("u%d" % n, "a%d" % (n - 1), t, "next step %d" % n), _asst("a%d" % n, "u%d" % n, t + 5, "Done with step %d." % n)]
        with open(self.paths[sid], "a") as f:
            f.write("\n".join(json.dumps(r) for r in recs) + "\n")
        self.tx_n[sid] = n + 1
        os.utime(self.paths[sid], (NOW + n, NOW + n))       # a moved stat, whatever the clock's tick
        return km._parse(self.paths[sid], sid, NOW)

    def _store_json(self, sid, peer):
        s0, s1 = self.seg_ids[sid]
        g1, g2, gh, gc, gd = (sid + ":g%d" % i for i in (1, 2, 3, 4, 5))
        nodes = {
            g1: {"id": g1, "text": "Ship the notes API", "parentId": None, "t": T0, "mt": T0 + 50, "why": "x",
                 "trail": [s0], "promptUuid": "u0", "log": []},
            gh: {"id": gh, "text": "delegated to api: review the schema", "parentId": g1, "t": T0 + 10, "mt": T0 + 10,
                 "why": "x", "trail": [], "log": [], "handoff": {"peer": peer, "msgId": "m-1"}},
            gc: {"id": gc, "text": "Wire the route", "parentId": g1, "t": T0 + 20, "mt": T0 + 20, "why": "x",
                 "trail": ["%s:999:nonexistent" % sid], "log": []},
            gd: {"id": gd, "text": "Write the handler", "parentId": g1, "t": T0 + 30, "mt": T0 + 40, "why": "x",
                 "trail": [s1], "nodeComplete": True, "doneWhy": "landed",
                 "log": [{"kind": "done", "src": "planner", "at": T0 + 40, "ev_t": T0 + 40, "why": "landed", "seg": s1}]},
            g2: {"id": g2, "text": "Fix the flaky test", "parentId": None, "t": T0 + 60, "mt": T0 + 70, "why": "x",
                 "trail": [s1], "blocked": True, "blockWhy": "which auth?", "blockCheckT": T0 + 75,
                 "log": [{"kind": "block", "src": "planner", "at": T0 + 70, "ev_t": T0 + 70, "why": "which auth?", "seg": s1}]},
        }
        return {"rompUuid": sid, "seq": 5, "placementsV": jd.PLACEMENTS_V, "nodes": nodes,
                "status": {g1: "working", g2: "blocked"}, "placements": {s0: g1, s1: g2}, "lastNode": g2}

    def _publish(self, sid, raw):
        path = jd.GOALDIR / (sid + ".json")
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(raw))
        os.replace(tmp, path)

    def _republish(self, sid, mutate):
        raw = json.loads((jd.GOALDIR / (sid + ".json")).read_text())
        mutate(raw)
        self._publish(sid, raw)

    def _scope(self):
        km._live_scope.names = km._names_snapshot()

    def _build(self, scoped=True):
        if scoped:
            self._scope()
        else:
            km._live_scope.names = None
        return km.build_feed(NOW, dict(self.tmux))

    def _delta(self, key):
        return km._feed_segs_stats[key] - self.stats0[key]

    def _reset_deltas(self):
        self.stats0 = dict(km._feed_segs_stats)

    def _fresh(self):
        """A build with an empty memo: every session recomputed."""
        with km._FEED_SEGS_LOCK:
            km._feed_segs_memo.clear()
        return self._build()


class Hits(_World):
    def test_two_builds_over_unchanged_inputs_serve_the_same_objects_and_skip_the_walk(self):
        f1 = self._build()
        self.assertEqual(self._delta("miss"), 3)
        e1 = {sid: km._feed_segs_memo[sid] for sid in SIDS}
        with mock.patch.object(km, "_seg_anchors", wraps=km._seg_anchors) as walk:
            f2 = self._build()
            self.assertEqual(walk.call_count, 0, "a hit runs no anchor walk")
        self.assertEqual(self._delta("hit"), 3)
        self.assertEqual(self._delta("miss"), 3)
        for sid in SIDS:
            self.assertIs(km._feed_segs_memo[sid], e1[sid], "the entry stands")
            c1, c2 = _tops(f1, sid), _tops(f2, sid)
            self.assertEqual(sorted(c1), sorted(c2))
            for nid in c1:
                self.assertIsNot(c1[nid]["tree"], c2[nid]["tree"], "each build gets its own tree list")
                for r1, r2 in zip(c1[nid]["tree"], c2[nid]["tree"]):
                    self.assertIs(r1, r2, "…of the same row objects")
        self.assertEqual(_loop_out(f1), _loop_out(f2))
        self.assertEqual(km._feed_segs_report()["entries"], 3)

    def test_a_cold_parse_is_a_stable_key_too(self):
        # a session with no cached parse (ps None): the memo keys on None and hits until the parse lands
        km._parse_cache.pop(self.paths[SID_C], None)
        self._build()
        self._reset_deltas()
        self._build()
        self.assertEqual(self._delta("hit"), 3)
        km._parse(self.paths[SID_C], SID_C, NOW)           # the warm-up lands the parse: a new object, one miss
        self._reset_deltas()
        self._build()
        self.assertEqual((self._delta("hit"), self._delta("miss")), (2, 1))


class KeyInputs(_World):
    """Each input alone moves the key for its session only."""

    def _one_miss(self, sid):
        self.assertEqual(self._delta("miss"), 1, "exactly one session recomputed")
        self.assertEqual(self._delta("hit"), 2, "the other two served from the memo")
        self.assertEqual(self._delta("bypass_live") + self._delta("bypass_degraded") + self._delta("bypass_unkeyed"), 0)

    def test_a_transcript_append_misses_that_session_only(self):
        self._build()
        self._reset_deltas()
        self._append_turn(SID)
        f = self._build()
        self._one_miss(SID)
        rows = {r["id"]: r for r in _tops(f, SID)[SID + ":g1"]["tree"]}
        self.assertIsNotNone(rows[SID + ":g1"]["anchorUuid"], "warm anchors still resolve in the new parse")

    def test_a_store_publish_misses_that_session_only(self):
        self._build()
        self._reset_deltas()
        self._republish(SID_B, lambda raw: raw["nodes"][SID_B + ":g4"].__setitem__("text", "Wire the route (v2)"))
        f = self._build()
        self._one_miss(SID_B)
        rows = {r["id"]: r for r in _tops(f, SID_B)[SID_B + ":g1"]["tree"]}
        self.assertEqual(rows[SID_B + ":g4"]["text"], "Wire the route (v2)")

    def test_a_journal_append_misses_that_session_only(self):
        self._build()
        self._reset_deltas()
        jd.append_override(SID_C, SID_C + ":g2", "followup", NOW - 10)
        f = self._build()
        self._one_miss(SID_C)
        card = _tops(f, SID_C)[SID_C + ":g2"]
        self.assertEqual(card["column"], "working", "the replayed reopen shows: the served view moved")

    def test_a_names_write_misses_every_session_and_the_rows_carry_the_new_colour(self):
        self._build()
        self._reset_deltas()
        self._write_name(SID_B, "api", "#FF8800")          # a colour change: the handoff rows naming api re-tint
        f = self._build()
        self.assertEqual(self._delta("miss"), 3, "every session resolves names through the registry")
        row = next(r for r in _tops(f, SID)[SID + ":g1"]["tree"] if r["kind"] == "handoff")
        self.assertEqual(row["whoColor"], {"bg": "#FF8800", "fg": "#ffffff"})
        self.assertEqual(row["who"], "api")

    def test_a_working_flip_misses_that_session_only(self):
        self._build()
        self._reset_deltas()
        self.force_working.add(SID)
        f = self._build()
        self._one_miss(SID)
        self.assertTrue(all(r["whoWorking"] for r in _tops(f, SID)[SID + ":g1"]["tree"]))
        self.assertFalse(any(r["whoWorking"] for r in _tops(f, SID_B)[SID_B + ":g1"]["tree"]))

    def test_the_session_rows_own_name_misses_that_session_only(self):
        # the row's name is not always the registry's (a live session outside the discover window, an
        # SDK session with no transcript yet), so it is keyed by value on its own
        self._build()
        self._reset_deltas()
        self.sessions[0]["name"] = "web-2"
        f = self._build()
        self._one_miss(SID)
        rows = _tops(f, SID)[SID + ":g1"]["tree"]
        self.assertEqual(next(r for r in rows if r["kind"] == "ask")["who"], "web-2")

    def test_a_changed_remembered_anchor_misses_that_session_only(self):
        # g4's trail names a segment no parse holds, so its row reads the remembered warm anchor
        # (_node_anchor_last); that read is recorded and a changed value misses
        gc = SID + ":g4"
        km._node_anchor_last[gc] = ("p-old", "w-old")
        f1 = self._build()
        row = {r["id"]: r for r in _tops(f1, SID)[SID + ":g1"]["tree"]}[gc]
        self.assertEqual(row["anchorUuid"], "w-old")
        self.assertIn(gc, km._feed_segs_memo[SID].anchor_deps)
        self._reset_deltas()
        self._build()
        self.assertEqual(self._delta("hit"), 3, "unchanged: a hit")
        self._reset_deltas()
        km._node_anchor_last[gc] = ("p-new", "w-new")     # what a chat build with a fresher parse would write
        f2 = self._build()
        self._one_miss(SID)
        row = {r["id"]: r for r in _tops(f2, SID)[SID + ":g1"]["tree"]}[gc]
        self.assertEqual(row["anchorUuid"], "w-new")

    def test_a_hit_re_applies_the_warm_anchors_the_entry_recorded(self):
        g1 = SID + ":g1"
        self._build()
        warm = km._node_anchor_last[g1]
        self.assertIsNotNone(warm[1], "g1's trail resolves in the parse: a warm write")
        km._node_anchor_last[g1] = ("x", "y")             # another builder's write in between
        self._reset_deltas()
        self._build()
        self.assertEqual(self._delta("hit"), 3, "warm nodes are writes, not reads: no dependency, a hit")
        self.assertEqual(km._node_anchor_last[g1], warm, "the hit re-applied what a fresh build would have written")


class TwoGestures(_World):
    """A SECOND user gesture on the same sid within one judge pass (the review's reproduction): the first
    punch copies the snapshot entry, and the second must land on a fresh copy too. Re-punching the first
    copy in place kept its identity, so the memo hit on it and served the pre-gesture rows for the rest
    of the pass."""

    def test_the_second_gesture_in_one_pass_reaches_the_memoized_rows(self):
        g1, g2, g4 = SID + ":g1", SID + ":g2", SID + ":g4"
        self._build()                                    # live branch: the FrozenStore is the key
        km._begin_goals_pass()                           # a judge pass in flight: the snapshot branch
        try:
            self._build()                                # the snapshot object is the key: stored
            jd.append_override(SID, g2, "followup", NOW - 20)    # gesture 1: reopen the blocked top
            km._note_user_goal_write(SID)
            f1 = self._build()                           # copy-on-punch: the copy is a new key
            self.assertEqual(_tops(f1, SID)[g2]["column"], "working", "gesture 1 landed")
            self.assertEqual({r["id"]: r for r in _tops(f1, SID)[g1]["tree"]}[g4]["status"], "open")
            jd.append_override(SID, g4, "resolve", NOW - 10)     # gesture 2, same pass: resolve an open sub
            km._user_goal_write[SID] = km._user_goal_write[SID] + 1.0   # a moved mark, whatever the clock's tick
            self._reset_deltas()
            memoized = self._build()
            self.assertEqual(self._delta("miss"), 1, "the fresh copy is a new key: the session recomputes")
            fresh = self._fresh()
        finally:
            km._end_goals_pass()
        rows_m = {r["id"]: r for r in _tops(memoized, SID)[g1]["tree"]}
        rows_f = {r["id"]: r for r in _tops(fresh, SID)[g1]["tree"]}
        self.assertEqual(rows_f[g4]["status"], "done", "a fresh build shows the second gesture")
        self.assertEqual(rows_m[g4]["status"], "done", "…and so does the memoized one")
        self.assertEqual(_loop_out(memoized), _loop_out(fresh))


class Bypasses(_World):
    def test_live_atoms_bypass_the_memo_and_the_build_equals_the_unmemoized_one(self):
        self._build()
        self._reset_deltas()
        e_before = km._feed_segs_memo[SID]
        real = km._merge_live_atoms
        with mock.patch.object(km, "_merge_live_atoms",
                               lambda session, sid, shown_texts=(): dict(session) if sid == SID else real(session, sid, shown_texts)):
            memoized = self._build()
            self.assertEqual(self._delta("bypass_live"), 1)
            self.assertEqual(self._delta("hit"), 2)
            self.assertIs(km._feed_segs_memo[SID], e_before, "a bypass stores nothing")
            fresh = self._fresh()
        self.assertEqual(_loop_out(memoized), _loop_out(fresh))

    def test_a_swallowed_exception_on_the_miss_build_is_not_memoized(self):
        real = km._seg_anchors
        boom = {"n": 0}

        def failing(atoms):
            boom["n"] += 1
            if boom["n"] == 1:
                raise OSError("synthetic: the first walk fails")
            return real(atoms)
        with mock.patch.object(km, "_seg_anchors", failing):
            f = self._build()
        degraded_sid = next(sid for sid in SIDS if sid not in km._feed_segs_memo)
        self.assertEqual(self._delta("bypass_degraded"), 1)
        self.assertEqual(self._delta("miss"), 2)
        self.assertEqual(len(km._feed_segs_memo), 2, "the degraded session has no entry")
        rows = {r["id"]: r for r in _tops(f, degraded_sid)[degraded_sid + ":g1"]["tree"]}
        self.assertIsNone(rows[degraded_sid + ":g1"]["anchorUuid"], "the degraded build shipped empty anchors")
        self._reset_deltas()
        f2 = self._build()
        self.assertEqual(self._delta("miss"), 1, "the next build recomputes it and stores")
        rows = {r["id"]: r for r in _tops(f2, degraded_sid)[degraded_sid + ":g1"]["tree"]}
        self.assertIsNotNone(rows[degraded_sid + ":g1"]["anchorUuid"], "…and the anchors are back")

    def test_a_held_session_bypasses(self):
        self._build()
        self._reset_deltas()
        km._rewind_hold_set(SID, T0 + 55, "a0")            # hides g2 (born after the cut)
        f = self._build()
        self.assertEqual(self._delta("bypass_unkeyed"), 1)
        self.assertEqual(self._delta("hit"), 2)
        self.assertNotIn(SID + ":g2", _tops(f, SID))
        km._rewind_hold_clear(SID)
        self._reset_deltas()
        self._build()
        self.assertEqual(self._delta("hit"), 3, "the entry survived the hold and serves again")

    def test_an_unscoped_build_reads_the_memo_but_never_fills_it(self):
        self._build()                                    # scoped: fills
        self._reset_deltas()
        f_unscoped = self._build(scoped=False)
        self.assertEqual(self._delta("hit"), 3, "a WS-thread gesture build reads the pusher's entries")
        with km._FEED_SEGS_LOCK:
            km._feed_segs_memo.clear()
        self._reset_deltas()
        f2 = self._build(scoped=False)
        self.assertEqual(self._delta("bypass_unscoped"), 3)
        self.assertEqual(len(km._feed_segs_memo), 0, "…and never fills")
        self.assertEqual(_loop_out(f_unscoped), _loop_out(f2))

    def test_a_session_leaving_the_alive_set_is_evicted(self):
        self._build()
        self.assertEqual(km._feed_segs_report()["entries"], 3)
        self.sessions.pop()                              # tests leaves
        self._reset_deltas()
        self._build()
        self.assertEqual(self._delta("evict"), 1)
        self.assertEqual(sorted(km._feed_segs_memo), sorted([SID, SID_B]))


class SharedRows(_World):
    def test_the_serving_fold_lands_on_a_copy_of_the_memoized_tracker_row(self):
        # SID_B's top gM is a to-do mirror SERVING SID's handoff row g3: the fold re-parents gM's rows under it
        gm, gs, tracker = SID_B + ":g6", SID_B + ":g7", SID + ":g3"

        def add_mirror(raw):
            raw["nodes"][gm] = {"id": gm, "text": "review the schema (mirror)", "parentId": None, "t": T0 + 80,
                                "mt": T0 + 80, "why": "x", "trail": [], "log": [], "serving": {"goalId": tracker}}
            raw["nodes"][gs] = {"id": gs, "text": "check the indexes", "parentId": gm, "t": T0 + 85, "mt": T0 + 85,
                                "why": "x", "trail": [], "log": []}
            raw["status"][gm] = "working"
            raw["seq"] = 7
        self._republish(SID_B, add_mirror)
        f1 = self._build()
        rows1 = {r["id"]: r for r in _tops(f1, SID)[SID + ":g1"]["tree"]}
        self.assertEqual(rows1[tracker]["children"], [gm], "the mirror's root rides the tracker row")
        self.assertIn(gs, rows1, "…with its rows")
        self.assertNotIn(gm, _tops(f1, SID_B), "the mirror stands on no card of its own")
        memo_rows, _w = km._feed_segs_memo[SID].trees[SID + ":g1"]
        memo_tracker = next(r for r in memo_rows if r["id"] == tracker)
        self.assertEqual(memo_tracker["children"], [], "the memoized row is untouched")
        self.assertIsNot(rows1[tracker], memo_tracker, "the served row is a copy")
        self.assertIs(rows1[SID + ":g1"], memo_rows[0], "the rows the fold did not touch are the shared objects")
        snapshot = json.dumps(memo_rows, sort_keys=True)
        f2 = self._build()
        self.assertEqual(json.dumps(km._feed_segs_memo[SID].trees[SID + ":g1"][0], sort_keys=True), snapshot)
        self.assertEqual(_loop_out(f1), _loop_out(f2))

    def test_tints_are_stamped_at_serialization_not_in_the_build(self):
        f = self._build()
        for a in f["asks"]:
            self.assertNotIn("trgb", a)
            for r in a.get("tree") or []:
                self.assertNotIn("trgb", r)
            self.assertIs(km._strip_trgb(a), a)
        body = json.loads(km._feed_body(f))
        self.assertEqual(len(body["asks"]), len(f["asks"]))
        for a in body["asks"]:
            self.assertEqual(a["trgb"], list(km.cm.age_rgb(NOW - a["t"])))
            for r in a.get("tree") or []:
                self.assertEqual(r["trgb"], list(km.cm.age_rgb(NOW - r["last"])))
        cards, _l, _r, _ms = km._feed_parts(f)
        self.assertFalse(any('"trgb"' in s for s in cards.values()), "the delta strings carry no tint")
        for a in f["asks"]:
            self.assertNotIn("trgb", a, "the stamp copied; the built cards are unchanged")

    def test_concurrent_builds_while_sessions_die_do_not_raise(self):
        errors = []

        def builder():
            try:
                km._live_scope.names = km._names_snapshot()
                for _ in range(12):
                    km.build_feed(NOW, dict(self.tmux))
            except Exception as e:                       # noqa: BLE001 — the test collects every failure
                errors.append(repr(e))
            finally:
                km._live_scope.names = None

        def killer():
            for _ in range(2):
                time.sleep(0.02)
                if self.sessions:
                    self.sessions.pop()
        ts = [threading.Thread(target=builder), threading.Thread(target=builder), threading.Thread(target=killer)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual(errors, [])
        self.assertLessEqual(len(km._feed_segs_memo), len(self.sessions) or 1)


class Differential(_World):
    def test_random_perturbations_memoized_equals_fresh(self):
        rng = random.Random(20260907)
        colours = ["#1EA1EB", "#FF8800", "#22AA44", "#AA22AA"]

        def perturb():
            sid = rng.choice(SIDS)
            kind = rng.choice(("transcript", "store", "journal", "names", "working", "hold", "nothing", "anchor",
                               "pass", "gesture"))
            if kind == "transcript":
                self._append_turn(sid)
            elif kind == "store":
                n = rng.randrange(1000)
                self._republish(sid, lambda raw: raw["nodes"][sid + ":g4"].__setitem__("text", "Wire the route %d" % n))
            elif kind == "journal":
                jd.append_override(sid, sid + ":g2", rng.choice(("followup", "resolve")), NOW - rng.randrange(1, 3000))
            elif kind == "names":
                self._write_name(sid, dict(zip(SIDS, NAMES))[sid], rng.choice(colours))
            elif kind == "working":
                (self.force_working.discard if sid in self.force_working else self.force_working.add)(sid)
            elif kind == "hold":
                if km._rewind_hold_get(sid):
                    km._rewind_hold_clear(sid)
                else:
                    km._rewind_hold_set(sid, T0 + 55, "a0")
            elif kind == "anchor":
                km._node_anchor_last[sid + ":g4"] = ("p", "w-%d" % rng.randrange(100))
            elif kind == "pass":                     # a judge pass begins or ends: the snapshot branch comes and goes
                if km._goals_snap[0] is None:
                    km._begin_goals_pass()
                else:
                    km._end_goals_pass()
            elif kind == "gesture":                  # a user gesture, noted as the routes note it: punches a mid-pass snapshot
                jd.append_override(sid, sid + ":g4", rng.choice(("followup", "resolve")), NOW - rng.randrange(1, 3000))
                km._user_goal_write[sid] = max(time.time(), km._user_goal_write.get(sid, 0.0) + 1e-3)
            return kind
        for i in range(200):
            kind = perturb()
            memoized = self._build()
            fresh = self._fresh()
            self.assertEqual(_loop_out(memoized), _loop_out(fresh),
                             "step %d (%s): the memoized build differs from a fresh one" % (i, kind))
        st = km._feed_segs_report()
        self.assertGreater(st["hit"] - self.stats0["hit"], 0, "the run exercised hits")


if __name__ == "__main__":
    unittest.main()
