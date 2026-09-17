"""_feed_goals_keyed reads the live store through the shared read-only cache (round-4 plan P1).

The feed's per-session store read (`_feed_goals`) took the writer's loader on its live branch and
re-parsed every store on every build outside a judge pass: the pusher's single largest raw_decode
caller, for stores the timeline and the chat already held in jd.load_goals_shared. The live branch
now reads the shared view (jd.load_goals_shared_or_fault). `_feed_goals_keyed` returns the served
store WITH the version key the feed's memo names it under (upstream #1789's contract): while a judge
pass is mid-flight, the pass-snapshot entry's key, the (ino, mtime_ns, size) the store was decoded
from beside the pass memo's count of byte changes the stat did not show (_goals_snap_key), unchanged
across a copy-on-punch; outside a pass, None (the live file, whose identity the memo stats for
itself); on a read fault, (None, None). The shared cache's own identity stays the live branch's
guarantee, testable as `s1 is s2` across builds and against jd.load_goals_shared.

Retired pins (the 2026-09-17 catch-up fold, R5): the object-identity key (`k1 is s1`, the served
object standing for its content) and the sentinel key (a fresh object per read under a rewind hold,
a failed punch, the cache switched off or an absent store) retire with twin upstream #1789's version
key and tests/test_feed_session_memo.py, which pins what the feed memo derives from that key. Every
case below is re-aimed at the version-key contract, none retired; the read's earlier fork-only name
retires with twin `_feed_goals_keyed`.

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
        s1, k1 = km._feed_goals_keyed(SID)
        s2, k2 = km._feed_goals_keyed(SID)
        self.assertIsInstance(s1, jd.FrozenStore, "the live branch holds the shared view")
        self.assertIs(s1, s2, "one object per store version across builds")
        self.assertIsNone(k1, "a live read is keyed None: the memo stats the live file's identity for itself")
        self.assertIsNone(k2)
        self.assertEqual(self._delta("miss"), 1)
        self.assertEqual(self._delta("hit"), 1, "the second read is a cache hit")
        self.assertEqual(jd.goal_io_stats()["loads"] - loads0, 0, "no plain load_goals on the live branch")
        self.assertIs(s1, jd.load_goals_shared(SID), "the cache's own object: its identity is the guarantee")
        self.assertEqual(self._served("live"), 2)
        self.assertEqual(self._served("snap"), 0)
        self.assertEqual(json.dumps(s1, sort_keys=True), json.dumps(jd.load_goals(SID), sort_keys=True),
                         "exactly load_goals' content")
        self.assertIs(km._feed_goals(SID), s1, "_feed_goals is the same read, store only")

    def test_a_store_publish_moves_the_identity(self):
        s = self._mint(SID, "Write the login flow")
        s1, k1 = km._feed_goals_keyed(SID)
        jd.apply_plan(s, "s2", T0 + 60, [{"do": "mint", "why": "x", "text": "Add the logout route"}], [])
        jd.rollup_status(s, session_closed=False)
        jd.save_goals(SID, s)
        s2, k2 = km._feed_goals_keyed(SID)
        self.assertIsNot(s2, s1, "a new store version is a new shared object")
        self.assertIs(s2, jd.load_goals_shared(SID))
        self.assertEqual((k1, k2), (None, None), "live reads stay keyed None: the version moves in the memo's own stat")
        self.assertEqual(len(s2["nodes"]), 2)

    def test_a_journal_append_moves_the_identity(self):
        # the override journal is part of the view (load_goals replays it), so an append is a new version
        self._mint(SID, "Write the login flow")
        s1, k1 = km._feed_goals_keyed(SID)
        jd.append_override(SID, SID + ":g1", "followup", NOW)
        s2, k2 = km._feed_goals_keyed(SID)
        self.assertIsNot(s2, s1, "a journal append is a new view")
        self.assertIs(s2, jd.load_goals_shared(SID))
        self.assertEqual((k1, k2), (None, None))
        self.assertTrue(any(e.get("kind") == "reopen" for e in s2["nodes"][SID + ":g1"].get("log") or []),
                        "the replayed gesture is in the served view")

    def test_with_the_cache_off_the_live_read_is_a_private_object_per_call(self):
        # the shared identity is scoped to the cache being ON: off, load_goals answers a private object per
        # call; the key stays None either way (the memo never keyed on the served object)
        self._mint(SID, "Write the login flow")
        jd._SHARED_OFF[0] = True
        try:
            s1, k1 = km._feed_goals_keyed(SID)
            s2, k2 = km._feed_goals_keyed(SID)
        finally:
            jd._SHARED_OFF[0] = False
        self.assertNotIsInstance(s1, jd.FrozenStore)
        self.assertIsNot(s1, s2, "a private object per call")
        self.assertEqual((k1, k2), (None, None))
        self.assertEqual(self._delta("fallback"), 2)

    def test_an_absent_store_answers_a_fresh_store_keyed_none(self):
        s1, k1 = km._feed_goals_keyed(SID_C)
        s2, k2 = km._feed_goals_keyed(SID_C)
        self.assertEqual(s1.get("nodes"), {})
        self.assertIsNot(s1, s2, "nothing to share: load_goals' fresh store, private per call")
        self.assertEqual((k1, k2), (None, None))
        self.assertEqual(self._delta("absent"), 2)

    def test_a_read_fault_answers_none_none(self):
        # the store path exists and does not read (a directory in the file's place: EISDIR at the read), so
        # the shared boundary files one store-unreadable row per episode and answers (None, exc); the feed's
        # read answers (None, None) and build_feed renders that session without goal-derived content
        jd._STORE_FAULTS.pop(SID_C, None)
        (jd.GOALDIR / (SID_C + ".json")).mkdir()
        s1, k1 = km._feed_goals_keyed(SID_C)
        s2, k2 = km._feed_goals_keyed(SID_C)
        self.assertEqual((s1, k1, s2, k2), (None, None, None, None))
        self.assertEqual(self._served("live"), 2, "a fault is the live branch's answer")
        rows = [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()]
        self.assertEqual([r.get("err") for r in rows if r.get("fsid") == SID_C], ["store-unreadable"],
                         "filed once per fault episode")


class RewindHold(_World):
    """A hold's view depends on the transcript (the kept chain) as well as the store. The read's key
    does not carry that: a live read is keyed None under a hold as without one, and the feed memo's
    own components (the hold's record, the transcript) name what the view depends on."""

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

    def test_a_hold_serves_the_filtered_view_that_follows_the_transcript(self):
        self._held_world()
        s1, k1 = km._feed_goals_keyed(SID)
        self.assertEqual(sorted(s1["nodes"]), [SID + ":g1"], "the post-cut node is hidden by the hold")
        self.assertIsNot(s1, jd.load_goals_shared(SID), "the held view is a filtered copy, never the shared object")
        self.assertIsNone(k1, "a live read under a hold is keyed None like any live read")
        s1b, k1b = km._feed_goals_keyed(SID)
        self.assertIsNone(k1b)
        # the prompt record lands: the late node's promptUuid is now on the kept chain, so the
        # served view changes with NO store change (the memo's hold and transcript components carry that)
        with self.tpath.open("a") as f:
            f.write(json.dumps(_user("p-late", "a0", self.CUT + 5, "rewritten ask")) + "\n")
        s2, k2 = km._feed_goals_keyed(SID)
        self.assertEqual(sorted(s2["nodes"]), sorted([SID + ":g1", SID + ":g2"]),
                         "the transcript append spares the node the hold hid")
        self.assertIsNone(k2)
        self.assertEqual(self._delta("poisoned"), 0, "the hold's view is built without writing the shared store")
        self.assertEqual(jd.shared_store_stats()["off"], 0)

    def test_clearing_the_hold_returns_the_shared_view(self):
        self._held_world()
        km._rewind_hold_clear(SID)
        s1, k1 = km._feed_goals_keyed(SID)
        self.assertIsInstance(s1, jd.FrozenStore)
        self.assertIs(s1, jd.load_goals_shared(SID), "the cache's own object again")
        self.assertIsNone(k1)
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
    def test_within_a_pass_the_snapshot_serves_under_its_version_key(self):
        self._mint(SID, "Write the login flow")
        st = os.stat(jd.GOALDIR / (SID + ".json"))
        km._begin_goals_pass()
        try:
            vk = km._goals_snap_key[0].get(SID)          # the pass's own record, read while the pass stands
            s1, k1 = km._feed_goals_keyed(SID)
            s2, k2 = km._feed_goals_keyed(SID)
        finally:
            km._end_goals_pass()
        self.assertIs(s1, s2, "one snapshot entry for the pass")
        self.assertIsNotNone(vk)
        self.assertEqual(k1, vk, "the key is the snapshot entry's version, not the served object")
        self.assertEqual(k2, vk)
        self.assertEqual(vk[0], (st.st_ino, st.st_mtime_ns, st.st_size),
                         "the (ino, mtime_ns, size) the entry was decoded from")
        self.assertIsInstance(vk[1], int)                # the pass memo's count of byte changes the stat did not show
        self.assertEqual(self._served("snap"), 2)
        self.assertEqual(self._served("live"), 0)
        self.assertNotIsInstance(s1, jd.FrozenStore, "the pass snapshot is the memo's own decode")

    def test_a_punch_lands_on_a_copy_under_the_same_version_key(self):
        self._mint(SID, "Write the login flow")
        km._begin_goals_pass()
        try:
            s0, k0 = km._feed_goals_keyed(SID)
            jd.append_override(SID, SID + ":g1", "followup", NOW)
            km._note_user_goal_write(SID)
            s1, k1 = km._feed_goals_keyed(SID)
            s2, k2 = km._feed_goals_keyed(SID)
        finally:
            km._end_goals_pass()
        self.assertIsNot(s1, s0, "the gesture is replayed onto a copy")
        self.assertIsNotNone(k0)
        self.assertEqual(k1, k0, "the copy renders the same store version: a punch does not move the key")
        self.assertEqual(k2, k0)
        self.assertIs(s2, s1, "no further gesture: the copy stands")
        self.assertEqual(self._served("punch"), 1)

    def test_a_second_gesture_in_the_same_pass_mints_a_fresh_copy_under_the_same_key(self):
        # an object this read has served is a fixed value, so a second gesture must never re-punch the first
        # copy in place (review 2026-09-07: it did, and the memo served the pre-gesture rows for the rest of
        # the pass); the version key does not move (the file did not change): the gesture mark and the punch
        # record, both feed-memo components, carry the gesture (tests/test_feed_session_memo.py)
        self._mint(SID, "Write the login flow")
        g1 = SID + ":g1"
        km._begin_goals_pass()
        try:
            vk = km._goals_snap_key[0].get(SID)
            jd.append_override(SID, g1, "followup", NOW)
            km._note_user_goal_write(SID)
            s1, k1 = km._feed_goals_keyed(SID)
            jd.append_override(SID, g1, "resolve", NOW + 1)
            km._user_goal_write[SID] = km._user_goal_write[SID] + 1.0   # a moved mark, whatever the clock's tick
            s2, k2 = km._feed_goals_keyed(SID)
            s3, k3 = km._feed_goals_keyed(SID)
        finally:
            km._end_goals_pass()
        self.assertIsNotNone(vk)
        self.assertEqual((k1, k2, k3), (vk, vk, vk), "one store version for the pass, whatever the gestures")
        self.assertIsNot(s2, s1, "the second gesture lands on a fresh copy")
        self.assertTrue(s2["nodes"][g1].get("nodeComplete"), "the resolve is in the served view")
        self.assertFalse(s1["nodes"][g1].get("nodeComplete"), "the first copy is untouched: a fixed value")
        self.assertIs(s3, s2, "no further gesture: the second copy stands")
        self.assertEqual(self._served("punch"), 1, "the counter says how many sids were copied this pass")

    def test_a_failed_punch_retries_on_a_fresh_copy_under_the_same_version_key(self):
        self._mint(SID, "Write the login flow")
        km._begin_goals_pass()
        real = jd._replay_overrides
        try:
            vk = km._goals_snap_key[0].get(SID)
            jd.append_override(SID, SID + ":g1", "followup", NOW)
            km._note_user_goal_write(SID)
            jd._replay_overrides = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("synthetic replay failure"))
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                s1, k1 = km._feed_goals_keyed(SID)
                s2, k2 = km._feed_goals_keyed(SID)
            self.assertIn("feed-goals: user-override replay", err.getvalue())
            self.assertIsNot(s2, s1, "a failed punch retries on a fresh copy, never in place on a served object")
            self.assertEqual((k1, k2), (vk, vk), "the key names the store version, which a failed replay did not move")
            jd._replay_overrides = real
            s3, k3 = km._feed_goals_keyed(SID)
        finally:
            jd._replay_overrides = real
            km._end_goals_pass()
        self.assertIsNot(s3, s1, "the retry lands on a fresh copy (the failed attempt's copy may have been read)")
        self.assertIsNot(s3, s2)
        self.assertEqual(k3, vk)
        self.assertTrue(any(e.get("kind") == "reopen" for e in s3["nodes"][SID + ":g1"].get("log") or []))


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
        for fn in (km.build_feed, km._feed_session_entry, km._apply_rewind_hold):
            src = inspect.getsource(fn)
            self.assertIsNone(re.search(r"\b(store|nodes|status)\[[^\]]+\]\s*=[^=]", src), fn.__name__)
            self.assertIsNone(re.search(r"\bdel\s+(store|nodes|status)\[", src), fn.__name__)
            self.assertIsNone(re.search(r"\b(store|nodes|status)\.(setdefault|update|pop|popitem|clear)\(", src), fn.__name__)
            self.assertNotIn("record_verdict(", src, fn.__name__)
        self.assertNotIn("rollup_status(", inspect.getsource(km.build_feed))
        self.assertNotIn("rollup_status(", inspect.getsource(km._feed_session_entry))
        # _apply_rewind_hold re-rolls the columns on a throwaway deep copy, never on the store it was handed
        hold_src = inspect.getsource(km._apply_rewind_hold)
        self.assertIn("jd.rollup_status(tmp, session_closed=False)", hold_src)
        self.assertNotIn("rollup_status(store", hold_src)

    def test_the_serve_counters_ride_perf(self):
        self._mint(SID, "Write the login flow")
        km._feed_goals_keyed(SID)
        km._begin_goals_pass()
        try:
            km._feed_goals_keyed(SID)
        finally:
            km._end_goals_pass()
        # memos.pass: upstream's name for the pass memo since the memos bundle's review (#1059; the
        # 2026-09-08 fold took the rename, kernel-code DECISIONS 2)
        snap = km._PERF_STATS.snapshot()["memos"]["pass"]
        self.assertEqual(snap["live"] - self.memo0["live"], 1)
        self.assertEqual(snap["snap"] - self.memo0["snap"], 1)


if __name__ == "__main__":
    unittest.main()
