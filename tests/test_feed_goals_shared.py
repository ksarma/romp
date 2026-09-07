"""_feed_goals reads the live store through the shared read-only cache (round-4 plan P1).

The feed's per-session store read (`_feed_goals`) took the writer's loader on its live branch and
re-parsed every store on every build outside a judge pass: the pusher's single largest raw_decode
caller, for stores the timeline and the chat already held in jd.load_goals_shared. The live branch
now reads the shared view. `_feed_goals_view` returns the served store WITH the key a consumer may
memoize under: the served object itself where its identity implies its content (the FrozenStore
from the cache; the pass snapshot's object once any user gesture on it is settled), and a fresh
sentinel where it does not (a rewind hold, a failed punch, the cache switched off, no store file).

The landing gate (the plan's amendment): build_feed must never write into a store it reads. A write
on a shared view raises FrozenStoreError and switches the cache off for the process, which would
turn every builder's shared load back into a plain parse, a regression far larger than P1's saving.
The rich-world build below asserts `off == 0` and `poisoned == 0` afterwards, and a source pin
refuses an assignment into `store`, `nodes[...]` or `status[...]` in the feed's read path.

Synthetic fixtures only: sids private to this module (never the shared 11111111-2222 placeholder,
see CLAUDE.md), invented goal text, the demo names `web`/`api`/`tests`, hostname TESTHOST. Every
test rebinds STATE to a temp dir, so the override journal it appends dies with the test."""
import contextlib
import inspect
import io
import json
import os
import re
import tempfile
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
km = load_source("romp_kernel_feedgoals", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SIDS = ["77777777-1111-4222-8333-44444444440%d" % i for i in range(3)]   # private to this module (synthetic)
SID, SID_B, SID_C = SIDS
NOW = 1781300000
T0 = NOW - 3600


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _user(uuid, parent, t, text):
    return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent, "promptSource": "typed",
            "message": {"role": "user", "content": text}}


def _asst(uuid, parent, t, text):
    return {"type": "assistant", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}}


class _World(unittest.TestCase):
    """A private STATE root per test (the shared cache cleared and its off switch lifted by the
    rebind), a names registry the feed's colour reads resolve through, no rewind holds."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.saved_state, self.saved_names = jd.STATE, km.NAMES
        jd._rebind_state(self.root)
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        jd.NAMES.mkdir(parents=True, exist_ok=True)
        km.NAMES = jd.NAMES
        for sid, name in zip(SIDS, ("web", "api", "tests")):
            (jd.NAMES / sid).write_text("%s\t/proj/TESTHOST/notes-api\t#1EA1EB\twhite\n" % name)
        km._rewind_holds[0] = None                    # the hold map is loaded once per process: start empty here
        km._rewind_kept_memo.clear()
        km._rewind_kept_err.clear()
        km._end_goals_pass()
        self.stats0 = jd.shared_store_stats()
        self.memo0 = dict(km._goals_memo_stats)

    def tearDown(self):
        km._end_goals_pass()
        for sid in SIDS:
            km._user_goal_write.pop(sid, None)
        km._rewind_holds[0] = None
        km._rewind_kept_memo.clear()
        km._rewind_kept_err.clear()
        km.NAMES = self.saved_names
        jd._rebind_state(self.saved_state)
        self.td.cleanup()

    def _delta(self, key):
        return jd.shared_store_stats()[key] - self.stats0[key]

    def _served(self, key):
        return km._goals_memo_stats[key] - self.memo0[key]

    def _mint(self, sid, *texts, t=T0):
        """A store with one top goal per text, published the way the judge publishes."""
        s = {"rompUuid": sid, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": {}, "placements": {}, "status": {}}
        for i, text in enumerate(texts):
            jd.apply_plan(s, "s%d" % (i + 1), t + i, [{"do": "mint", "why": "x", "text": text}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(sid, s)
        return s


class LiveBranch(_World):
    def test_the_live_branch_serves_the_shared_view_by_identity(self):
        self._mint(SID, "Write the login flow")
        self.assertEqual(jd.shared_store_stats()["off"], 0, "the invariant holds with the cache ON")
        loads0 = jd.goal_io_stats()["loads"]
        s1, k1 = km._feed_goals_view(SID)
        s2, k2 = km._feed_goals_view(SID)
        self.assertIsInstance(s1, jd.FrozenStore, "the live branch holds the shared view")
        self.assertIs(s1, s2, "one object per store version across builds")
        self.assertIs(k1, s1, "the key IS the served object where its identity implies its content")
        self.assertIs(k2, k1)
        self.assertEqual(self._delta("miss"), 1)
        self.assertEqual(self._delta("hit"), 1, "the second read is a cache hit")
        self.assertEqual(jd.goal_io_stats()["loads"] - loads0, 0, "no plain load_goals on the live branch")
        self.assertEqual(self._served("live"), 2)
        self.assertEqual(self._served("snap"), 0)
        self.assertEqual(json.dumps(s1, sort_keys=True), json.dumps(jd.load_goals(SID), sort_keys=True),
                         "exactly load_goals' content")
        self.assertIs(km._feed_goals(SID), s1, "_feed_goals is the same read, store only")

    def test_a_store_publish_moves_the_identity_and_the_key(self):
        s = self._mint(SID, "Write the login flow")
        s1, k1 = km._feed_goals_view(SID)
        jd.apply_plan(s, "s2", T0 + 60, [{"do": "mint", "why": "x", "text": "Add the logout route"}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        s2, k2 = km._feed_goals_view(SID)
        self.assertIsNot(s2, s1)
        self.assertIsNot(k2, k1)
        self.assertEqual(len(s2["nodes"]), 2)

    def test_a_journal_append_moves_the_key(self):
        # the override journal is part of the view (load_goals replays it), so an append is a new version
        self._mint(SID, "Write the login flow")
        s1, k1 = km._feed_goals_view(SID)
        jd.append_override(SID, SID + ":g1", "followup", NOW)
        s2, k2 = km._feed_goals_view(SID)
        self.assertIsNot(k2, k1, "a journal append is a new view")
        self.assertTrue(any(e.get("kind") == "reopen" for e in s2["nodes"][SID + ":g1"].get("log") or []),
                        "the replayed gesture is in the served view")

    def test_with_the_cache_off_the_key_is_a_sentinel(self):
        # the invariant is scoped to the cache being ON: off, load_goals answers a private object per
        # call, so no key may claim two reads equal
        self._mint(SID, "Write the login flow")
        jd._SHARED_OFF[0] = True
        try:
            s1, k1 = km._feed_goals_view(SID)
            s2, k2 = km._feed_goals_view(SID)
        finally:
            jd._SHARED_OFF[0] = False
        self.assertNotIsInstance(s1, jd.FrozenStore)
        self.assertIsNot(k1, s1, "a private object is not its own key")
        self.assertIsNot(k1, k2, "sentinels never compare equal")
        self.assertEqual(self._delta("fallback"), 2)

    def test_an_absent_store_answers_a_fresh_store_under_a_sentinel(self):
        s1, k1 = km._feed_goals_view(SID_C)
        s2, k2 = km._feed_goals_view(SID_C)
        self.assertEqual(s1.get("nodes"), {})
        self.assertIsNot(k1, k2)
        self.assertIsNot(k1, s1)


class RewindHold(_World):
    """A hold's view depends on the transcript (the kept chain) as well as the store, so no
    store-identity key can stand for it: the key is a sentinel while the hold is armed."""

    CUT = T0 + 100

    def _held_world(self):
        # gEarly predates the cut; gLate is born after it with a promptUuid the transcript lacks, so
        # the sweep hides it unless the kept chain proves the prompt is on the live branch
        s = self._mint(SID, "Write the login flow", t=T0)
        jd.apply_plan(s, "s2", self.CUT + 10, [{"do": "mint", "why": "x", "text": "Rewrite the ask"}], [],
                      prompt_uuid="p-late")
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        self.tpath = self.root / (SID + ".jsonl")
        recs = [_user("u0", None, T0, "do the thing"), _asst("a0", "u0", T0 + 5, "Done.")]
        self.tpath.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        self.patches = [mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: [
                            {"sid": SID, "path": str(self.tpath), "name": "web", "anchor": SID, "mtime": 0}]),
                        mock.patch.object(km, "_sdk", lambda: None)]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        km._rewind_hold_set(SID, self.CUT, "a0")
        return s

    def test_a_hold_serves_the_filtered_view_under_a_sentinel_that_follows_the_transcript(self):
        self._held_world()
        s1, k1 = km._feed_goals_view(SID)
        self.assertEqual(sorted(s1["nodes"]), [SID + ":g1"], "the post-cut node is hidden by the hold")
        self.assertIsNot(k1, s1, "a held view is not its own key")
        s1b, k1b = km._feed_goals_view(SID)
        self.assertIsNot(k1b, k1, "never equal while the hold stands")
        # the prompt record lands: the late node's promptUuid is now on the kept chain, so the
        # served view changes with NO store change, which is why the key could not be the store
        with self.tpath.open("a") as f:
            f.write(json.dumps(_user("p-late", "a0", self.CUT + 5, "rewritten ask")) + "\n")
        s2, k2 = km._feed_goals_view(SID)
        self.assertEqual(sorted(s2["nodes"]), sorted([SID + ":g1", SID + ":g2"]),
                         "the transcript append spares the node the hold hid")
        self.assertIsNot(k2, k1b)
        self.assertEqual(self._delta("poisoned"), 0, "the hold's view is built without writing the shared store")
        self.assertEqual(jd.shared_store_stats()["off"], 0)

    def test_clearing_the_hold_returns_the_shared_view_and_its_key(self):
        self._held_world()
        km._rewind_hold_clear(SID)
        s1, k1 = km._feed_goals_view(SID)
        self.assertIs(k1, s1)
        self.assertIsInstance(s1, jd.FrozenStore)
        self.assertEqual(len(s1["nodes"]), 2)

    def test_apply_rewind_hold_on_the_shared_view_writes_nothing_into_it(self):
        self._held_world()
        shared = jd.load_goals_shared(SID)
        out = km._apply_rewind_hold(SID, shared)
        self.assertIsNot(out, shared)
        self.assertEqual(sorted(out["nodes"]), [SID + ":g1"])
        self.assertEqual(sorted(shared["nodes"]), sorted([SID + ":g1", SID + ":g2"]), "the shared view is untouched")
        self.assertEqual(self._delta("poisoned"), 0)
        self.assertEqual(jd.shared_store_stats()["off"], 0)


class SnapshotBranch(_World):
    def test_within_a_pass_the_snapshot_object_is_the_key(self):
        self._mint(SID, "Write the login flow")
        km._begin_goals_pass()
        try:
            s1, k1 = km._feed_goals_view(SID)
            s2, k2 = km._feed_goals_view(SID)
        finally:
            km._end_goals_pass()
        self.assertIs(s1, s2)
        self.assertIs(k1, s1)
        self.assertIs(k2, s1)
        self.assertEqual(self._served("snap"), 2)
        self.assertEqual(self._served("live"), 0)
        self.assertNotIsInstance(s1, jd.FrozenStore, "the pass snapshot is the memo's own decode")

    def test_a_settled_punch_makes_the_pass_copy_the_key(self):
        self._mint(SID, "Write the login flow")
        km._begin_goals_pass()
        try:
            s0, k0 = km._feed_goals_view(SID)
            jd.append_override(SID, SID + ":g1", "followup", NOW)
            km._note_user_goal_write(SID)
            s1, k1 = km._feed_goals_view(SID)
            s2, k2 = km._feed_goals_view(SID)
        finally:
            km._end_goals_pass()
        self.assertIsNot(s1, s0, "the gesture is replayed onto a copy")
        self.assertIs(k1, s1, "a settled punch: the copy is the key")
        self.assertIs(k2, s1, "…and stays the key for the rest of the pass")
        self.assertEqual(self._served("punch"), 1)

    def test_a_failed_punch_keeps_the_key_a_sentinel_until_the_replay_succeeds(self):
        self._mint(SID, "Write the login flow")
        km._begin_goals_pass()
        real = jd._replay_overrides
        try:
            jd.append_override(SID, SID + ":g1", "followup", NOW)
            km._note_user_goal_write(SID)
            jd._replay_overrides = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synthetic replay failure"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                s1, k1 = km._feed_goals_view(SID)
                s2, k2 = km._feed_goals_view(SID)
            self.assertIn("feed-goals: user-override replay", err.getvalue())
            self.assertIsNot(k1, s1, "a failed punch retries in place: its identity cannot be the key")
            self.assertIsNot(k1, k2)
            jd._replay_overrides = real
            s3, k3 = km._feed_goals_view(SID)
        finally:
            jd._replay_overrides = real
            km._end_goals_pass()
        self.assertIs(s3, s1, "the retry lands on the same copy")
        self.assertIs(k3, s3, "…and once it succeeds the copy is the key")


class LandingGate(_World):
    """build_feed over a world that exercises the feed's store reads (subtrees, handoffs, origins, a
    serving mirror, seams, blocks with watermarks, cleared and agent-open nodes, diary rows, a hold, a
    punched snapshot, debug rows) writes nothing into a shared view: the cache stays on."""

    def _rich_store(self, sid, peer):
        s = self._mint(sid, "Ship the notes API", "Fix the flaky test")
        g1, g2, g3, g4 = (sid + ":g%d" % i for i in (1, 2, 3, 4))
        n = s["nodes"]
        for nid, text, t in ((g3, "Write the handler", T0 + 20), (g4, "Wire the route", T0 + 25)):
            n[nid] = {"id": nid, "text": text, "parentId": g1, "t": t, "mt": t, "why": "x", "trail": [], "log": []}
        s["seq"] = 4
        self.assertTrue(jd.record_verdict(s, n[g3], "planner", "done", T0 + 40, why="landed", seg="s4"))
        n[g3]["nodeComplete"] = True
        n[g3]["doneWhy"] = "landed"
        self.assertTrue(jd.record_verdict(s, n[g4], "planner", "block", T0 + 60, why="needs a decision", seg="s5"))
        n[g4]["blocked"] = True
        n[g4]["blockWhy"] = "needs a decision"
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(sid, s)
        # the display-only fields the feed reads (diary-owned keys are refused on a guarded node, so they
        # land on the published JSON, by rename, as every real writer publishes)
        path = jd.GOALDIR / (sid + ".json")
        raw = json.loads(path.read_text())
        rn = raw["nodes"]
        rn[g4]["blockCheckT"] = T0 + 70
        rn[g2]["agentTask"] = {"status": "open", "id": "1"}
        rn[g2]["trail"] = ["%s:%d:deadbeef" % (sid, T0)]
        rn[g1].update({"summary": "The API ships.", "summaryAnchor": "a0", "briefParts": [{"id": "b1", "since": T0}],
                       "followupPending": True, "followupAt": T0 + 80,
                       "origin": {"peer": peer, "goalId": peer + ":g1", "peerName": "api"},
                       "handoff": {"peer": peer, "tracked": True, "msgId": "m-1"},
                       "serving": {"goalId": peer + ":g1"}})
        rn[g1]["log"] = (rn[g1].get("log") or []) + [
            {"kind": "block", "src": "nudge", "at": T0 + 90, "ev_t": T0 + 90, "why": "stalled"},
            {"kind": "reopen", "src": "user", "at": T0 + 95, "ev_t": T0 + 95, "why": "replied"}]
        raw["seams"] = [{"segs": ["%s:%d:deadbeef" % (sid, T0)], "t": T0 + 30, "top": g1, "text": "Ship the notes API"}]
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(raw))
        os.replace(tmp, path)
        return raw

    def _transcript(self, sid):
        p = self.root / (sid + ".jsonl")
        recs = [_user("u0", None, T0, "do the thing"), _asst("a0", "u0", T0 + 5, "Done: the handler is written and wired."),
                _user("u1", "a0", T0 + 200, "and the flaky test?"), _asst("a1", "u1", T0 + 210, "Fixed the ordering.")]
        p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        km._parse(str(p), sid, NOW)                  # warm the parse cache: the seam walk needs it
        return str(p)

    def test_build_feed_over_a_rich_world_leaves_the_shared_cache_on(self):
        self._rich_store(SID, SID_B)
        self._rich_store(SID_B, SID)
        self._mint(SID_C, "Quiet goal")
        (jd.STATE / "debug-mode.json").write_text(json.dumps({"on": True}))
        paths = {sid: self._transcript(sid) for sid in (SID, SID_B)}
        paths[SID_C] = str(self.root / "no-such-transcript.jsonl")
        sessions = [{"sid": sid, "name": nm, "path": paths[sid], "anchor": sid, "mtime": 0}
                    for sid, nm in zip(SIDS, ("web", "api", "tests"))]
        tmux = {SID: {"state": "idle", "since": NOW - 50}, SID_B: {"state": "prompt", "since": NOW - 5}}
        with mock.patch.object(km, "_alive_sessions", lambda now, tm: list(sessions)), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: list(sessions)), \
                mock.patch.object(km, "_sdk", lambda: None):
            f1 = km.build_feed(NOW, tmux)                       # live branch, twice
            f2 = km.build_feed(NOW, tmux)
            km._rewind_hold_set(SID_B, T0 + 30, "a0")           # a hold on one session: the filtered view
            f3 = km.build_feed(NOW, tmux)
            km._rewind_hold_clear(SID_B)
            km._begin_goals_pass()                              # a pass in flight, with a user gesture punched
            try:
                jd.append_override(SID, SID + ":g2", "followup", NOW)
                km._note_user_goal_write(SID)
                f4 = km.build_feed(NOW, tmux)
            finally:
                km._end_goals_pass()
        for f in (f1, f2, f3, f4):
            self.assertEqual({a["sid"] for a in f["asks"] if a.get("turnId")}, set(SIDS), "every session rendered cards")
        self.assertEqual(jd.shared_store_stats()["off"], 0, "no build wrote into a shared view")
        self.assertEqual(self._delta("poisoned"), 0)
        self.assertGreaterEqual(self._delta("hit"), len(SIDS), "the second live build served every store from the cache")
        rows = []
        if jd.ERRORS.exists():
            rows = [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()]
        self.assertEqual([r for r in rows if r.get("err") == "frozen-store-write"], [])

    def test_the_feed_read_path_never_writes_into_the_store_it_reads(self):
        # the source pin: no assignment into `store`, `nodes[...]` or `status[...]`, no mutating method on
        # them, no rollup_status or record_verdict (both write) in the functions that hold a served store
        for fn in (km.build_feed, km._apply_rewind_hold):
            src = inspect.getsource(fn)
            self.assertIsNone(re.search(r"\b(store|nodes|status)\[[^\]]+\]\s*=[^=]", src), fn.__name__)
            self.assertIsNone(re.search(r"\bdel\s+(store|nodes|status)\[", src), fn.__name__)
            self.assertIsNone(re.search(r"\b(store|nodes|status)\.(setdefault|update|pop|popitem|clear)\(", src), fn.__name__)
            self.assertNotIn("record_verdict(", src, fn.__name__)
        self.assertNotIn("rollup_status(", inspect.getsource(km.build_feed))
        # _apply_rewind_hold re-rolls the columns on a throwaway deep copy, never on the store it was handed
        hold_src = inspect.getsource(km._apply_rewind_hold)
        self.assertIn("jd.rollup_status(tmp, session_closed=False)", hold_src)
        self.assertNotIn("rollup_status(store", hold_src)

    def test_the_serve_counters_ride_perf(self):
        self._mint(SID, "Write the login flow")
        km._feed_goals_view(SID)
        km._begin_goals_pass()
        try:
            km._feed_goals_view(SID)
        finally:
            km._end_goals_pass()
        snap = km._PERF_STATS.snapshot()["memos"]["goals_snap"]
        self.assertEqual(snap["live"] - self.memo0["live"], 1)
        self.assertEqual(snap["snap"] - self.memo0["snap"], 1)


if __name__ == "__main__":
    unittest.main()
