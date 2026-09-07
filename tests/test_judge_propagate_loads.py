#!/usr/bin/env python3
"""run_propagate and _drain_undiscovered read each goal store at most once per pass, and the two
absent-store predicates are memoized across passes on file identity (2026-09-06, the judge-pass
performance batch, item J4). Before: every pass loaded each recipient, loaded the sender again per
ref BEFORE checking whether its tracker was already done (it was, for every live ref), loaded every
sender a third time in the sender loop, and both triage sweeps parsed every ABSENT store to evaluate
one predicate each — about 168 of 455 loads per pass. Pinned here:

- one load_goals per distinct sid per pass across the recipient scan, the per-ref done check,
  _ref_goal and the sender loop; the same object serves the recipient scan and the sender loop;
- one publish per dirty sender (rev advances by exactly one for two refs) carrying the rollup over
  every verdict it holds, the CAS discipline intact under a kernel-side write between two refs, a
  failed publish leaving the file untouched for the retry, and an absent sender's publish settled (or
  not) by _presumed_closed;
- the absent-store memo: an unchanged store is evaluated once across both sweeps and across passes; a
  changed goals file, a changed override journal and a changed archive each re-evaluate; the identity
  is taken before the read, in the sweep's own read and in run_propagate's; the key is the full path;
  entries for vanished stores are evicted; a load that FELL BACK (`_unread`: the store file or the
  journal did not read) is answered but never memoized; the one documented exception (same-size
  in-place rewrite with the mtime put back) is pinned as such.

SYNTHETIC fixtures only. Private synthetic sids: load_goals replays the per-sid override journal, and
node ids collide across test modules under the shared placeholder (CLAUDE.md, goal-store fixtures);
every test runs under its own _rebind_state root, so its journal and memo entries die with it."""
import errno
import json
import os
import shutil
import tempfile
import unittest
from collections import Counter
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))

SENDER = "a4a4a4a4-0001-4000-8000-000000000001"   # discovered, name "web"
RECIP = "a4a4a4a4-0002-4000-8000-000000000002"    # discovered, name "api"
DEAD = "a4a4a4a4-0003-4000-8000-000000000003"     # absent: no discover entry
DEAD2 = "a4a4a4a4-0004-4000-8000-000000000004"
DEAD3 = "a4a4a4a4-0005-4000-8000-000000000005"
MID = "msg-j4-0001"
MID2 = "msg-j4-0002"
T = 1_787_600_000


def _node(nid, text, parent=None, t=T, **kw):
    base = {"id": nid, "text": text, "parentId": parent, "nodeComplete": False,
            "blocked": False, "cleared": False, "trail": [], "t": t, "mt": t, "log": []}
    base.update(kw)
    return jd.GuardedNode(base)


def _store(sid, nodes):
    return {"rompUuid": sid, "seq": 0, "placementsV": jd.PLACEMENTS_V, "nodes": dict(nodes),
            "placements": {}, "status": {}}


def _tracker(sid, k, peer, mid, quiet=False, done=False):
    h = {"peer": peer, "msgId": mid}
    if quiet:
        h["quiet"] = True
    nd = _node("%s:t%d" % (sid, k), "delegated to a peer: step %d" % k, handoff=h)
    if done:
        jd.record_verdict({"nodes": {nd["id"]: nd}}, nd, "courier", "done", T + 1, why="done earlier")
    return nd


def _complete(sid, k, **ref):
    """A COMPLETE recipient goal carrying an origin (or links) ref back to a sender's tracker."""
    nd = _node("%s:g%d" % (sid, k), "the delegated work, step %d" % k, **ref)
    jd.record_verdict({"nodes": {nd["id"]: nd}}, nd, "closer", "done", T + 100, why="shipped step %d" % k)
    return nd


def _rev(sid):
    return int(json.loads((jd.GOALDIR / (sid + ".json")).read_text()).get("rev") or 0)


class World(unittest.TestCase):
    def setUp(self):
        self._state = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))          # private root: journal, archive and memo all scoped
        self._disc = jd.discover
        self.sessions = [(SENDER, "/dev/null", None, "web"), (RECIP, "/dev/null", None, "api")]
        jd.discover = lambda now, window=None, forks=True: list(self.sessions)
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        jd.MESSAGES.write_text("")

    def tearDown(self):
        jd.discover = self._disc
        jd._rebind_state(self._state)
        self.td.cleanup()

    # ── fixtures ──
    def _publish(self, sid, nodes):
        st = _store(sid, nodes)
        jd.rollup_status(st, False)
        jd.save_goals(sid, st)

    def _reply(self, frm, to, at, mid="r1"):
        with jd.MESSAGES.open("a") as f:
            f.write(json.dumps({"t": at, "ev": "sent", "id": mid, "from_id": frm, "to_id": to,
                                "kind": "coordinate", "body": "done; nothing else owed"}) + "\n")

    def _counting(self, fn):
        """Run fn with load_goals counted per sid and every returned object kept; restore after."""
        counts, objs, orig = Counter(), {}, jd.load_goals

        def spy(fsid):
            counts[fsid] += 1
            st = orig(fsid)
            objs.setdefault(fsid, []).append(st)
            return st
        jd.load_goals = spy
        try:
            out = fn()
        finally:
            jd.load_goals = orig
        return out, counts, objs

    def _io(self):
        s = jd.goal_io_stats()
        return s["absent_hits"], s["absent_misses"], s["writes"]

    def _sids(self, *extra):
        return {f for f, _p, _a, _n in self.sessions} | set(extra)


class LoadOncePerPass(World):
    """The per-pass dict: one load per distinct sid across every site of run_propagate."""

    def test_a_done_ref_costs_the_sender_no_second_load(self):
        # THE COMMON LIVE SHAPE: every ref already done. The done check reads the shared object, so
        # the sender is loaded once whichever order discover lists them in — even when the ref check
        # runs BEFORE the sender's own recipient turn (discover order recipient-first).
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID, done=True)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        for order in ((RECIP, SENDER), (SENDER, RECIP)):
            self.sessions = [(s, "/dev/null", None, n) for s, n in zip(order, ("api", "web"))]
            n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 900))
            self.assertEqual(n, 0, "already done: idempotent")
            self.assertEqual(dict(counts), {SENDER: 1, RECIP: 1},
                             "one load per sid, discover order %r: the per-ref check took no load" % (order,))

    def test_the_same_object_serves_the_recipient_scan_and_the_sender_loop(self):
        # SENDER is scanned as a recipient (it is discovered) and then walked as a sender whose quiet
        # tracker has a reply: one load, and the object the sender loop mutates IS the scan's object.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID, quiet=True)]})
        self._publish(RECIP, {})
        self._reply(RECIP, SENDER, T + 500)
        rolled, orig_roll = [], jd.rollup_status

        def spy_roll(store, closed, now=None):
            rolled.append(store)
            return orig_roll(store, closed, now=now)
        jd.rollup_status = spy_roll
        try:
            n, counts, objs = self._counting(lambda: jd.run_propagate(now=T + 900))
        finally:
            jd.rollup_status = orig_roll
        self.assertEqual(n, 1)
        self.assertEqual(counts[SENDER], 1, "scan + sender loop: one load")
        self.assertEqual(len(rolled), 1)
        self.assertIs(rolled[0], objs[SENDER][0], "the sender loop rolled up the scan's own object")
        self.assertTrue(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"])

    def test_two_dirty_refs_to_one_sender_publish_once(self):
        self._publish(SENDER, {t["id"]: t for t in (_tracker(SENDER, 1, RECIP, MID),
                                                    _tracker(SENDER, 2, RECIP, MID2))})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, links=[{"peer": SENDER, "goalId": SENDER + ":t2", "msgId": MID2}])
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        r0, (_h, _m, w0) = _rev(SENDER), self._io()
        n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 2)
        # one load per FILE VERSION: the recipient loop's publish made a new one, and the sender loop
        # (SENDER is discovered) must read it fresh for its own CAS base — a saved object is never
        # kept. Only a pass that completed something pays this; an idle pass loads each sid once.
        self.assertEqual(counts[SENDER], 2)
        self.assertEqual(_rev(SENDER), r0 + 1, "two verdicts, one publish")
        self.assertEqual(self._io()[2], w0 + 1, "exactly one write")
        got = jd.load_goals(SENDER)
        snd = got["nodes"]
        self.assertTrue(snd[SENDER + ":t1"]["nodeComplete"] and snd[SENDER + ":t2"]["nodeComplete"])
        # the one publish carried the rollup over BOTH verdicts: the saved status is exactly what a
        # fresh rollup of the saved store derives (a rollup run only after the first ref would have
        # published t2 still working)
        saved = dict(got["status"])
        self.assertEqual(saved, {SENDER + ":t1": "completed", SENDER + ":t2": "completed"})
        jd.rollup_status(got, False)
        self.assertEqual(got["status"], saved)

    def test_two_refs_to_one_tracker_record_one_done_event(self):
        # The second ref reads the flag record_verdict materialized on the shared object: no
        # duplicate diary row, no second publish.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, links=[{"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID}])
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        r0 = _rev(SENDER)
        self.assertEqual(jd.run_propagate(now=T + 900), 1)
        self.assertEqual(_rev(SENDER), r0 + 1)
        log = jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["log"]
        self.assertEqual([e["kind"] for e in log if e.get("src") == "courier"], ["done"])

    def test_a_kernel_side_write_between_two_refs_survives_the_single_publish(self):
        # The CAS discipline under the deferred publish: the nudge tick blocks a third node and
        # publishes between the two refs' verdicts; the pass's one save rebases (union of logs),
        # the two publishes carry distinct revisions, and the saved object carried a fresh base.
        self._publish(SENDER, {t["id"]: t for t in (_tracker(SENDER, 1, RECIP, MID),
                                                    _tracker(SENDER, 2, RECIP, MID2),
                                                    _node(SENDER + ":g3", "an unrelated open ask"))})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, links=[{"peer": SENDER, "goalId": SENDER + ":t2", "msgId": MID2}])
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        saves, orig_save, orig_mark, fired = [], jd.save_goals, jd._mark_node_done, []

        def spy_save(fsid, store):
            had_base = "_baseRev" in store
            orig_save(fsid, store)
            saves.append((fsid, had_base, _rev(fsid)))

        def kernel_write_then_mark(store, nid, why, t, src="planner"):
            if not fired:                                # between the first and the second ref
                fired.append(1)
                k = jd.load_goals(SENDER)
                jd.append_block(SENDER, SENDER + ":g3", "nudge", "owed a decision", T + 600)
                jd.record_verdict(k, k["nodes"][SENDER + ":g3"], "nudge", "block", T + 600, why="owed a decision")
                jd.rollup_status(k, False)
                jd.save_goals(SENDER, k)
            return orig_mark(store, nid, why, t, src=src)
        jd.save_goals, jd._mark_node_done = spy_save, kernel_write_then_mark
        try:
            n = jd.run_propagate(now=T + 900)
        finally:
            jd.save_goals, jd._mark_node_done = orig_save, orig_mark
        self.assertEqual(n, 2)
        self.assertEqual([s[0] for s in saves], [SENDER, SENDER], "the kernel's publish, then the pass's one")
        self.assertTrue(all(s[1] for s in saves), "both saved objects carried a CAS base")
        self.assertEqual(saves[1][2], saves[0][2] + 1, "no two publishes share a revision")
        nodes = jd.load_goals(SENDER)["nodes"]
        self.assertTrue(nodes[SENDER + ":t1"]["nodeComplete"] and nodes[SENDER + ":t2"]["nodeComplete"])
        self.assertTrue(nodes[SENDER + ":g3"]["blocked"], "the kernel-side block survived the pass's publish")

    def test_a_failed_publish_drops_the_object_and_the_next_pass_retries_from_a_fresh_load(self):
        # An ABSENT sender with a quiet tracker whose reply has arrived: the sweep memoizes the
        # store's flags from the unmutated read, the sender loop marks the tracker done, and the
        # publish raises. Pinned: the memo describes the FILE, not the failed object (still "open
        # tracker", and a hit, since the file never changed), and the retry publishes once. That a
        # saved object leaves `loaded` is pinned by test_two_dirty_refs_to_one_sender_publish_once
        # (the sender loop's fresh load after the recipient loop's publish); a new pass starts with
        # an empty dict either way, so the failed publish's pop is not observable from here.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, quiet=True)]})
        self._reply(RECIP, DEAD, T + 500)
        r0, orig_save = _rev(DEAD), jd.save_goals

        def failing(fsid, store):
            if fsid == DEAD:
                raise RuntimeError("disk full")
            return orig_save(fsid, store)
        jd.save_goals = failing
        try:
            with self.assertRaises(RuntimeError):
                jd.run_propagate(now=T + 900)
        finally:
            jd.save_goals = orig_save
        self.assertEqual(_rev(DEAD), r0, "nothing published")
        self.assertFalse(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        h0, m0, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD), (True, False), "the memo describes the FILE, not the failed object")
        self.assertEqual(self._io()[:2], (h0 + 1, m0), "and it is a hit: the file never changed")
        n, counts, objs = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 1)
        self.assertEqual(counts[DEAD], 1, "the sender loop's fresh load; the sweep answered from the memo")
        self.assertEqual(_rev(DEAD), r0 + 1)
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual((n, counts[DEAD]), (0, 1), "identity moved: one miss, and no sender-loop load")

    def test_an_absent_senders_single_publish_carries_the_settled_rollup(self):
        # The deferred publish carries the rollup the sender loop ran with _presumed_closed. With the
        # tracker as the store's focus (lastNode), only a closed session settles it. Nothing knows the
        # sid and no remote-sids mirror exists: closedness cannot be determined, so the saved status
        # stays working (done, confirming). Once the bus has spoken (an empty mirror: no live session
        # anywhere answers to the sid), the same shape saves completed.
        def _focused_tracker(sid, mid):
            t1 = _tracker(sid, 1, RECIP, mid, quiet=True)
            st = _store(sid, {t1["id"]: t1})
            st["lastNode"] = t1["id"]
            jd.rollup_status(st, False)
            jd.save_goals(sid, st)
            self._reply(RECIP, sid, T + 500, mid="reply-" + mid)
        _focused_tracker(DEAD2, MID2)
        self.assertEqual(jd.run_propagate(now=T + 900), 1)
        got = jd.load_goals(DEAD2)
        self.assertTrue(got["nodes"][DEAD2 + ":t1"]["nodeComplete"])
        self.assertEqual(got["status"][DEAD2 + ":t1"], "working", "no mirror: not determinable, not settled")
        self.assertIn(DEAD2 + ":t1", got.get("confirming") or [])
        _focused_tracker(DEAD, MID)
        (jd.STATE / "remote-sids").write_text("")
        self.assertEqual(jd.run_propagate(now=T + 901), 1)
        got = jd.load_goals(DEAD)
        self.assertTrue(got["nodes"][DEAD + ":t1"]["nodeComplete"])
        self.assertEqual(got["status"][DEAD + ":t1"], "completed", "the bus knows no such live session: settled")
        self.assertNotIn(DEAD + ":t1", got.get("confirming") or [])


class AbsentStoreMemo(World):
    """_absent_store_flags: exact per file version, shared by both sweeps, evicted with the store."""

    def setUp(self):
        super().setUp()
        self._distill = jd._distill_session
        self.visits = []
        jd._distill_session = lambda sid, path, now: (self.visits.append(sid), 0)[1]   # owed stays owed

    def tearDown(self):
        jd._distill_session = self._distill
        super().tearDown()

    def _plain(self, sid):
        self._publish(sid, {sid + ":g1": _node(sid + ":g1", "ordinary open work")})

    def _owed(self, sid):
        g = _node(sid + ":g1", "an old finished ask")
        jd.record_verdict({"nodes": {g["id"]: g}}, g, "closer", "done", T + 100, why="finished long ago")
        self._publish(sid, {g["id"]: g})              # completed top, summary None → owes a distill

    def _pass(self, now):
        return self._counting(lambda: (jd.run_propagate(now=now),
                                       jd._drain_undiscovered(now, self._sids())))

    def test_an_unchanged_store_is_evaluated_once_across_both_sweeps_and_passes(self):
        self._plain(DEAD)
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        self._owed(DEAD3)
        h0, m0, _w = self._io()
        _r, counts, _o = self._pass(T + 900)
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 1, DEAD2: 1, DEAD3: 1},
                         "each absent store parsed once: the sweep's read serves the sender loop and the drain")
        self.assertEqual(self._io()[:2], (h0 + 3, m0 + 3), "three misses (propagate), three hits (the drain)")
        self.assertEqual(self.visits, [DEAD3])
        _r, counts, _o = self._pass(T + 901)
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 0, DEAD2: 1, DEAD3: 0},
                         "unchanged: no parse but the open tracker's sender-loop walk")
        self.assertEqual(self._io()[:2], (h0 + 9, m0 + 3), "six hits, no miss")
        self.assertEqual(self.visits, [DEAD3, DEAD3], "the drain still finds the owed store, from the memo")

    def test_a_changed_goals_file_journal_or_archive_each_re_evaluate(self):
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        k0 = jd._store_identity(DEAD2)
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        self.assertEqual(self._io()[:2], (h + 1, m), "unchanged triple: a hit")
        # (1) the JOURNAL alone: a user resolve journaled with no store save — load_goals replays it,
        # so the tracker is complete on the next load and the memo must say so
        jd.append_override(DEAD2, DEAD2 + ":t1", "resolve", T + 200)
        k1 = jd._store_identity(DEAD2)
        self.assertNotEqual(k1, k0)
        self.assertEqual(k1[1], k0[1], "the goals file itself did not move")
        self.assertEqual(jd._absent_store_flags(DEAD2), (False, True),
                         "the journaled resolve closed the tracker; a completed top with no summary owes a distill")
        self.assertEqual(self._io()[:2], (h + 1, m + 1))
        # (2) the GOALS FILE: a publish that opens a second tracker
        st = jd.load_goals(DEAD2)
        st["nodes"][DEAD2 + ":t2"] = _tracker(DEAD2, 2, RECIP, MID2, quiet=True)
        jd.rollup_status(st, False)
        jd.save_goals(DEAD2, st)
        k2 = jd._store_identity(DEAD2)
        self.assertNotEqual(k2[1], k1[1])
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, True))
        self.assertEqual(self._io()[:2], (h + 1, m + 2))
        # (3) the ARCHIVE: a cleared subtree parked beside the store
        jd.save_goal_archive(DEAD2, {"rompUuid": DEAD2, "nodes": {}, "status": {}})
        k3 = jd._store_identity(DEAD2)
        self.assertIsNone(k2[3])
        self.assertIsNotNone(k3[3])
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, True))
        self.assertEqual(self._io()[:2], (h + 1, m + 3), "a new archive file is a miss")
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, True))
        self.assertEqual(self._io()[:2], (h + 2, m + 3), "and the unchanged triple hits again")

    def test_the_identity_is_taken_before_the_read(self):
        # A publish landing between the identity stat and the load pairs the OLD identity with the
        # NEW content: one extra miss next pass, never a stale hit.
        self._plain(DEAD2)
        orig = jd.load_goals
        fired = []

        def publish_then_load(fsid):
            if fsid == DEAD2 and not fired:
                fired.append(1)
                st = orig(DEAD2)
                st["nodes"][DEAD2 + ":t1"] = _tracker(DEAD2, 1, RECIP, MID, quiet=True)
                jd.rollup_status(st, False)
                jd.save_goals(DEAD2, st)
            return orig(fsid)
        jd.load_goals = publish_then_load
        try:
            self.assertEqual(jd._absent_store_flags(DEAD2), (True, False), "the read saw the new content")
        finally:
            jd.load_goals = orig
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        self.assertEqual(self._io()[:2], (h, m + 1), "the stale-identity entry misses; it is never served")
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        self.assertEqual(self._io()[:2], (h + 1, m + 1))

    def test_run_propagates_own_read_takes_the_identity_before_the_read_too(self):
        # The recipient loop's _get reads an absent sender (a complete recipient goal refs a tracker
        # of its that is already done) and leaves the object for the sweep, which memoizes it under
        # the identity _get took. A publish landing between _get's stat and its read must pair the
        # OLD identity with the old content, one extra miss next pass; stat AFTER the read would
        # memoize the post-publish identity against pre-publish flags and serve it as a hit.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, done=True)]})
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        p, k0 = str(jd.GOALDIR / (DEAD + ".json")), jd._store_identity(DEAD)
        orig, fired = jd.load_goals, []

        def publish_under_the_read(fsid):
            st = orig(fsid)                             # the pre-publish content
            if fsid == DEAD and not fired:
                fired.append(1)
                new = orig(DEAD)
                new["nodes"][DEAD + ":t2"] = _tracker(DEAD, 2, RECIP, MID2, quiet=True)
                jd.rollup_status(new, False)
                jd.save_goals(DEAD, new)                # the identity moves while the read is in flight
            return st
        jd.load_goals = publish_under_the_read
        try:
            self.assertEqual(jd.run_propagate(now=T + 900), 0, "the ref's tracker was already done")
        finally:
            jd.load_goals = orig
        self.assertEqual(fired, [1], "_get, not the sweep, performed the read")
        k1 = jd._store_identity(DEAD)
        self.assertNotEqual(k1, k0)
        self.assertEqual(jd._ABSENT_FLAGS[p], (k0, (False, True)),
                         "memoized under the identity taken BEFORE the read, with the content that read saw")
        h, m, _w = self._io()
        n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual((n, counts[DEAD]), (0, 1))
        self.assertEqual(self._io()[:2], (h, m + 1), "the stale-identity entry misses; it is never served")
        self.assertEqual(jd._ABSENT_FLAGS[p], (k1, (True, True)), "re-evaluated on the published content")

    def test_a_dead_sender_that_gains_a_tracker_is_swept_the_next_pass(self):
        self._plain(DEAD)
        jd.run_propagate(now=T + 900)
        self.assertEqual(jd._absent_store_flags(DEAD), (False, False))
        # the courier's ext: planting shape: a write to the dead store opens a tracker (identity moves)
        st = jd.load_goals(DEAD)
        st["nodes"][DEAD + ":t1"] = _tracker(DEAD, 1, RECIP, MID, quiet=True)
        jd.rollup_status(st, False)
        jd.save_goals(DEAD, st)
        self._reply(RECIP, DEAD, T + 500)
        h, m, _w = self._io()
        n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual(n, 1, "swept and completed the next pass")
        self.assertEqual(counts[DEAD], 1, "the miss's read served the sender loop")
        self.assertEqual(self._io()[:2], (h, m + 1))
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        n, counts, _o = self._counting(lambda: jd.run_propagate(now=T + 902))
        self.assertEqual((n, counts[DEAD]), (0, 1), "the publish moved the identity: one re-evaluation")
        self.assertEqual(jd._absent_store_flags(DEAD), (False, True),
                         "no open tracker; the completed top now owes the drain a distill")

    def test_the_drain_re_evaluates_only_changed_absent_stores(self):
        for sid in (DEAD, DEAD2, DEAD3):
            self._plain(sid)
        jd._drain_undiscovered(T + 900, self._sids())
        st = jd.load_goals(DEAD2)
        st["nodes"][DEAD2 + ":g2"] = _node(DEAD2 + ":g2", "more open work")
        jd.rollup_status(st, False)
        jd.save_goals(DEAD2, st)
        h, m, _w = self._io()
        _r, counts, _o = self._counting(lambda: jd._drain_undiscovered(T + 901, self._sids()))
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 0, DEAD2: 1, DEAD3: 0})
        self.assertEqual(self._io()[:2], (h + 2, m + 1))
        self.assertEqual(self.visits, [])

    def test_the_drain_distills_a_stuck_store_found_by_the_shared_sweep(self):
        jd._distill_session = self._distill                  # the real distiller: transcript-less settle
        self._owed(DEAD3)
        self.sessions = []
        h, m, _w = self._io()
        _n, counts, _o = self._counting(lambda: (jd.run_propagate(now=T + 900), jd.run_distill(now=T + 900)))
        self.assertEqual(self._io()[:2], (h + 1, m + 1), "propagate's miss, the drain's hit")
        nd = jd.load_goals(DEAD3)["nodes"][DEAD3 + ":g1"]
        self.assertEqual(nd.get("summary"), "", "no transcript anywhere: the sentinel ends the spinner")
        _n, counts, _o = self._counting(lambda: jd.run_distill(now=T + 901))
        self.assertEqual(counts[DEAD3], 1, "the settle moved the identity: one re-evaluation")
        self.assertEqual(jd._absent_store_flags(DEAD3), (False, False), "self-retired")

    def test_a_vanished_store_is_evicted_and_the_key_is_the_full_path(self):
        self._plain(DEAD)
        self._plain(DEAD2)
        jd._drain_undiscovered(T + 900, self._sids())
        p_dead = str(jd.GOALDIR / (DEAD + ".json"))
        self.assertIn(p_dead, jd._ABSENT_FLAGS)
        (jd.GOALDIR / (DEAD + ".json")).unlink()
        jd._drain_undiscovered(T + 901, self._sids())
        self.assertNotIn(p_dead, jd._ABSENT_FLAGS, "gone from the glob: evicted at the next sweep")
        self.assertIn(str(jd.GOALDIR / (DEAD2 + ".json")), jd._ABSENT_FLAGS)
        # a bare GOALDIR reassignment (no _rebind_state): the same file bytes under another root,
        # mtime preserved, never hit the old root's entry, and the old entry is evicted by the sweep
        other = Path(self.td.name) / "other"
        (other / "goals").mkdir(parents=True)
        shutil.copy2(jd.GOALDIR / (DEAD2 + ".json"), other / "goals" / (DEAD2 + ".json"))
        saved = jd.GOALDIR, jd.GOALARCHDIR
        jd.GOALDIR, jd.GOALARCHDIR = other / "goals", other / "goals-archive"
        try:
            h, m, _w = self._io()
            self.assertEqual(jd._absent_store_flags(DEAD2), (False, False))
            self.assertEqual(self._io()[:2], (h, m + 1), "a different path is a different key")
            self.assertEqual(jd._store_identity(DEAD2)[0], str(other / "goals" / (DEAD2 + ".json")))
            jd._drain_undiscovered(T + 902, self._sids())
            self.assertEqual(set(jd._ABSENT_FLAGS), {str(other / "goals" / (DEAD2 + ".json"))},
                             "the old root's entries are gone from the new root's glob")
        finally:
            jd.GOALDIR, jd.GOALARCHDIR = saved

    def test_a_same_size_in_place_rewrite_with_the_mtime_put_back_is_the_documented_exception(self):
        # No romp writer does this: every publish is a tmp+rename (new inode, new mtime) and the
        # journal only grows. The identity key cannot see it, so the memo serves the previous answer;
        # pinned so the blind spot is a known, named exception rather than a surprise. A publish of
        # different size is seen.
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        p = jd.GOALDIR / (DEAD2 + ".json")
        k0, st0 = jd._store_identity(DEAD2), os.stat(p)
        raw = p.read_bytes()
        self.assertEqual(raw.count(b'"nodeComplete": false'), 1)
        edited = raw.replace(b'"nodeComplete": false', b'"nodeComplete": true ')   # same byte length
        self.assertEqual(len(edited), len(raw))
        with open(p, "r+b") as f:
            f.write(edited)
        os.utime(p, ns=(st0.st_atime_ns, st0.st_mtime_ns))
        self.assertEqual(jd._store_identity(DEAD2), k0, "same inode, mtime and size: the key cannot tell")
        self.assertFalse(jd._open_handoff_flag(jd.load_goals(DEAD2)), "a fresh evaluation would say closed")
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False), "the memo serves the previous answer (the known exception)")
        self.assertEqual(self._io()[:2], (h + 1, m))
        st = jd.load_goals(DEAD2)
        st["nodes"][DEAD2 + ":g9"] = _node(DEAD2 + ":g9", "a publish of another size")
        jd.save_goals(DEAD2, st)
        self.assertNotEqual(jd._store_identity(DEAD2), k0)
        self.assertEqual(jd._absent_store_flags(DEAD2), (False, False))
        self.assertEqual(self._io()[:2], (h + 1, m + 1))

    def test_a_load_failure_is_not_memoized(self):
        self._plain(DEAD)
        orig = jd.load_goals
        jd.load_goals = lambda fsid: (_ for _ in ()).throw(OSError("unreadable")) if fsid == DEAD else orig(fsid)
        try:
            self.assertIsNone(jd._absent_store_flags(DEAD), "the caller skips the store this pass")
        finally:
            jd.load_goals = orig
        self.assertNotIn(str(jd.GOALDIR / (DEAD + ".json")), jd._ABSENT_FLAGS)
        self.assertEqual(jd._absent_store_flags(DEAD), (False, False), "retried on the next call")

    # ---- a load that FELL BACK is no better than one that raised ----
    def _read_fails_once(self, target):
        """Patch Path.read_text so the first read of `target` raises OSError and every later read is
        real (the awaiting-lift gate's tests use the same shape). load_goals swallows a store-file
        failure into a fresh EMPTY store; _replay_overrides logs and skips the journal; both mark
        the object `_unread`. Returns the counter of raised reads."""
        real = Path.read_text
        state = {"fired": 0}

        def flaky(p, *a, **k):
            if p == target and not state["fired"]:
                state["fired"] += 1
                raise OSError(errno.EMFILE, "synthetic: too many open files")
            return real(p, *a, **k)
        Path.read_text = flaky
        self.addCleanup(setattr, Path, "read_text", real)
        return state

    def test_a_swallowed_store_read_failure_is_answered_but_not_memoized(self):
        # load_goals does not raise on a store file it cannot read: it answers a fresh empty store,
        # marked `_unread`. That store's (False, False) serves this pass (the sweeps skip the store,
        # as they always did) but no entry is written: nothing on disk changes before the next read
        # succeeds, so an entry would be a hit saying "nothing open" for a store holding an open
        # tracker, until its next write. (The raise above is the other shape; the memo must cover both.)
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, quiet=True)]})
        p, k0 = str(jd.GOALDIR / (DEAD + ".json")), jd._store_identity(DEAD)
        state = self._read_fails_once(jd.GOALDIR / (DEAD + ".json"))
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD), (False, False), "the fallback's answer, this pass only")
        self.assertEqual(state["fired"], 1)
        self.assertNotIn(p, jd._ABSENT_FLAGS, "an unread store is never memoized")
        self.assertEqual(jd._store_identity(DEAD), k0, "nothing on disk moved: the key alone could not tell")
        self.assertEqual(jd._absent_store_flags(DEAD), (True, False), "the next call re-reads the file")
        self.assertEqual(self._io()[:2], (h, m + 2), "two misses, no stale hit")
        self.assertEqual(jd._ABSENT_FLAGS[p], (k0, (True, False)))

    def test_a_skipped_journal_replay_is_answered_but_not_memoized(self):
        # The store file reads; the override journal does not. _replay_overrides logs, skips it and
        # marks the object `_unread`, so the un-replayed store still shows a tracker the user
        # resolved. That answer serves this pass only; the next call replays and re-evaluates. An
        # entry would have pinned the un-resolved tracker: the journal's identity does not move when
        # it becomes readable again.
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        jd.append_override(DEAD2, DEAD2 + ":t1", "resolve", T + 200)
        self.assertEqual(jd._owed_distill_flag(jd.load_goals(DEAD2)), True, "replayed: the resolve closed the tracker")
        p, k0 = str(jd.GOALDIR / (DEAD2 + ".json")), jd._store_identity(DEAD2)
        state = self._read_fails_once(jd._overrides_dir() / (DEAD2 + ".jsonl"))
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False), "un-replayed: this pass only")
        self.assertEqual(state["fired"], 1)
        self.assertNotIn(p, jd._ABSENT_FLAGS, "a store whose journal was skipped is never memoized")
        self.assertEqual(jd._store_identity(DEAD2), k0)
        self.assertEqual(jd._absent_store_flags(DEAD2), (False, True), "the next call replays the journal")
        self.assertEqual(self._io()[:2], (h, m + 2), "two misses, no stale hit")
        self.assertEqual(jd._ABSENT_FLAGS[p], (k0, (False, True)))

    def test_run_propagate_does_not_memoize_a_sender_whose_read_fell_back(self):
        # The same mark through run_propagate's own read: a complete recipient goal refs an absent
        # sender's open tracker; _get reads the sender (the store file fails once: an empty `_unread`
        # object with no tracker to mark) and leaves it for the sweep, which must not memoize it. The
        # next pass reads the real file and completes the tracker.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID)]})
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        p = str(jd.GOALDIR / (DEAD + ".json"))
        state = self._read_fails_once(jd.GOALDIR / (DEAD + ".json"))
        self.assertEqual(jd.run_propagate(now=T + 900), 0, "the fallback holds no tracker to complete")
        self.assertEqual(state["fired"], 1)
        self.assertNotIn(p, jd._ABSENT_FLAGS)
        self.assertFalse(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        self.assertEqual(jd.run_propagate(now=T + 901), 1, "the next pass reads the file and completes it")
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])

    def test_rebind_clears_the_memo(self):
        self._plain(DEAD)
        jd._absent_store_flags(DEAD)
        self.assertTrue(jd._ABSENT_FLAGS)
        jd._rebind_state(Path(self.td.name))
        self.assertEqual(jd._ABSENT_FLAGS, {})


if __name__ == "__main__":
    unittest.main()
