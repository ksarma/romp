#!/usr/bin/env python3
"""run_propagate reads through the shared read-only store cache and loads a writer only for the
sender it is about to write; _drain_undiscovered and run_propagate's absent-store sweep answer their
two predicates from a memo keyed on file identity (2026-09-06: every store read at most once per pass;
2026-09-07: the reads moved to load_goals_shared). Before: every pass loaded each recipient, loaded the
sender again per ref BEFORE checking whether its tracker was already done (it was, for every live ref),
loaded every sender a third time in the sender loop, and both triage sweeps parsed every ABSENT store to
evaluate one predicate each, about 168 of 455 loads per pass on the kernel where this was measured.
With one load per sid, that load was still a parse (about 2 ms per store per pass) that decided, for
every live ref, not to write. Pinned here:

- every read that decides whether to write is one load_goals_shared per distinct sid per pass (the
  recipient scan, the per-ref done check, _ref_goal, the sender loop's tracker walk): zero plain
  loads for an idle pass; a writer load (load_goals) is taken only when the view says a tracker is
  open under a complete recipient goal or has a reply, exactly once per such sender, and the write
  predicate is re-derived on the writer's node (a completion published between the view read and the
  writer load is not recorded twice); the object rollup_status and save_goals receive IS the writer
  load, never the view, and a pass over every write shape leaves the shared cache on (no poisoning);
- one publish per dirty sender (rev advances by exactly one for two refs) carrying the rollup over
  every verdict it holds, the CAS discipline intact under a kernel-side write between two refs, a
  failed publish leaving the file untouched for the retry, and an absent sender's publish settled (or
  not) by _presumed_closed; a store this pass published is read again through the shared cache; a
  raise mid-loop publishes the senders already reached and re-raises, and one sender's failed publish
  does not stop the others (the first failure is the pass's error, raised once the rest are out);
- a recipient whose goals file does not parse is quarantined aside by load_goals (upstream #1019, the
  2026-09-08 fold) and both loaders then answer the legitimate fresh store, once (`corrupt` advances by
  one for the shared loader's hand-off, the path then reads as absent), its refs skipped;
- the absent-store memo: an unchanged store is evaluated once across both sweeps and across passes; a
  changed goals file, a changed override journal and a changed archive each re-evaluate; the identity
  is taken before the read, in the sweep's own read and in run_propagate's (a view an earlier ref took
  feeds the memo under the identity taken before that shared read); the key is the full path;
  entries for vanished stores are evicted; a store read that RAISES is answered None and never
  memoized, a store loaded without its unreadable override journal (`_unread`) is answered but never
  memoized, a store whose files moved under the read (a publish, or load_goals' quarantine of an
  unparseable file) is answered but never memoized under the stale identity; the one documented
  exception (same-size in-place rewrite with the mtime put back) is pinned as such.

SYNTHETIC fixtures only. Private synthetic sids: load_goals replays the per-sid override journal, and
node ids collide across test modules under the shared placeholder (CLAUDE.md, goal-store fixtures);
every test runs under its own _rebind_state root, so its journal and memo entries die with it."""
import contextlib
import errno
import io
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
SENDER2 = "a4a4a4a4-0006-4000-8000-000000000006"  # a second sender, discovered on demand (name "tests")
MID = "msg-propagate-0001"
MID2 = "msg-propagate-0002"
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
        self._poisoned0 = jd.shared_store_stats()["poisoned"]

    def tearDown(self):
        # The frozen-store canary, BEFORE the rebind: a reader that wrote to a shared view switched the
        # cache off for the process (and _rebind_state lifts that switch, which would hide the poison
        # from the next test). Every pass in this module must leave the cache on and the counter still.
        try:
            self.assertEqual(jd.shared_store_stats()["poisoned"], self._poisoned0,
                             "a run_propagate site wrote to a shared read-only view")
            self.assertFalse(jd._SHARED_OFF[0], "the shared cache was switched off during the test")
        finally:
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
        """Run fn with load_goals (plain, the writer's loader) and load_goals_shared counted per sid, every
        object the plain loader returned kept; restore after. Returns (fn's result, plain counts, plain
        objects by sid, shared counts). A shared call that falls back to load_goals (no store file, the
        cache off) counts under BOTH, as goal_io_stats counts it."""
        counts, shared, objs, orig, orig_shared = Counter(), Counter(), {}, jd.load_goals, jd.load_goals_shared

        def spy(fsid):
            counts[fsid] += 1
            st = orig(fsid)
            objs.setdefault(fsid, []).append(st)
            return st

        def spy_shared(fsid):
            shared[fsid] += 1
            return orig_shared(fsid)
        jd.load_goals, jd.load_goals_shared = spy, spy_shared
        try:
            out = fn()
        finally:
            jd.load_goals, jd.load_goals_shared = orig, orig_shared
        return out, counts, objs, shared

    def _io(self):
        s = jd.goal_io_stats()
        return s["absent_hits"], s["absent_misses"], s["writes"]

    def _sids(self, *extra):
        return {f for f, _p, _a, _n in self.sessions} | set(extra)


class LoadOncePerPass(World):
    """The per-pass dicts: one shared read per distinct sid across every read site of run_propagate,
    and a writer load only for a sender the view says has something to write."""

    def test_a_done_ref_costs_no_plain_load(self):
        # THE COMMON LIVE SHAPE: every ref already done. The done check reads the shared view, so an
        # idle pass takes NO writer load at all, whichever order discover lists them in — even when the
        # ref check runs BEFORE the sender's own recipient turn (discover order recipient-first).
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID, done=True)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        for order in ((RECIP, SENDER), (SENDER, RECIP)):
            self.sessions = [(s, "/dev/null", None, n) for s, n in zip(order, ("api", "web"))]
            n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
            self.assertEqual(n, 0, "already done: idempotent")
            self.assertEqual(dict(counts), {}, "discover order %r: no plain load anywhere in an idle pass" % (order,))
            self.assertEqual(dict(shared), {SENDER: 1, RECIP: 1},
                             "one shared read per sid: the scan, the per-ref check and the sender walk share it")

    def test_the_view_decides_and_the_writer_load_receives_the_verdict(self):
        # SENDER is scanned as a recipient (it is discovered, one shared read) and then walked as a
        # sender whose quiet tracker has a reply: the view says due, so the loop takes ONE writer load,
        # and the object rollup_status mutates IS that writer load — never the frozen view.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID, quiet=True)]})
        self._publish(RECIP, {})
        self._reply(RECIP, SENDER, T + 500)
        rolled, orig_roll = [], jd.rollup_status

        def spy_roll(store, closed, now=None):
            rolled.append(store)
            return orig_roll(store, closed, now=now)
        jd.rollup_status = spy_roll
        try:
            n, counts, objs, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        finally:
            jd.rollup_status = orig_roll
        self.assertEqual(n, 1)
        self.assertEqual((shared[SENDER], counts[SENDER]), (1, 1), "the scan's shared read, then the one writer load")
        self.assertEqual((shared[RECIP], counts[RECIP]), (1, 0), "the recipient is only ever read")
        self.assertEqual(len(rolled), 1)
        self.assertIs(rolled[0], objs[SENDER][0], "the sender loop rolled up the writer load")
        self.assertNotIsInstance(rolled[0], jd.FrozenDict, "and not the shared view")
        self.assertTrue(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"])

    def test_a_dirty_ref_takes_one_writer_load_and_publishes_once(self):
        # An open tracker under a COMPLETE recipient goal: the view says open, the pass takes exactly
        # one writer load of the sender, publishes once (rev +1, one write; the CAS base is the writer
        # load's), and the sender loop's later read of the published version is a shared fill.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        r0, (_h, _m, w0) = _rev(SENDER), self._io()
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 1)
        self.assertEqual(dict(counts), {SENDER: 1}, "one writer load, for the sender written")
        self.assertEqual(dict(shared), {SENDER: 2, RECIP: 1},
                         "the scan's view, then the sender loop's read of the version this pass published")
        self.assertEqual(_rev(SENDER), r0 + 1)
        self.assertEqual(self._io()[2], w0 + 1, "exactly one write")
        self.assertTrue(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"])

    def test_a_completion_published_between_the_view_and_the_writer_load_is_not_recorded_twice(self):
        # The re-check on the writer's node: the view said open; before the writer load returns, a
        # concurrent writer (a peer kernel's propagate, the same shape) publishes the tracker done.
        # The pass records no second done event and publishes nothing of its own.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        orig, fired = jd.load_goals, []

        def complete_under_the_load(fsid):
            if fsid == SENDER and not fired:
                fired.append(1)
                k = orig(SENDER)
                jd.record_verdict(k, k["nodes"][SENDER + ":t1"], "courier", "done", T + 700, why="done by a peer kernel")
                jd._mark_node_done(k, SENDER + ":t1", "done by a peer kernel", T + 700, src="courier")
                jd.rollup_status(k, False)
                jd.save_goals(SENDER, k)
            return orig(fsid)
        jd.load_goals = complete_under_the_load
        try:
            _h, _m, w0 = self._io()
            n = jd.run_propagate(now=T + 900)
        finally:
            jd.load_goals = orig
        self.assertEqual(fired, [1], "the view said open, so the writer load was taken")
        self.assertEqual(n, 0, "the writer's node was already done: nothing recorded")
        self.assertEqual(self._io()[2], w0 + 1, "the concurrent publish is the only write")
        log = jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["log"]
        self.assertEqual([e["why"] for e in log if e.get("src") == "courier" and e.get("kind") == "done"],
                         ["done by a peer kernel"], "one done event, the concurrent writer's")

    def test_the_sender_loop_loads_the_writer_only_for_a_due_tracker(self):
        # Quiet and cross-host trackers complete on the recipient's reply. With no reply the walk over
        # the view finds nothing due and takes no writer load; with a reply, one.
        self._publish(SENDER, {t["id"]: t for t in (_tracker(SENDER, 1, RECIP, MID, quiet=True),
                                                    _tracker(SENDER, 2, "otherbox:api", MID2))})
        self._publish(RECIP, {})
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual((n, counts[SENDER], shared[SENDER]), (0, 0, 1), "nothing due: the view alone")
        self._reply(RECIP, SENDER, T + 500)                              # the quiet tracker's recipient replied
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual((n, counts[SENDER]), (1, 1), "one due tracker: one writer load")
        got = jd.load_goals(SENDER)["nodes"]
        self.assertTrue(got[SENDER + ":t1"]["nodeComplete"])
        self.assertFalse(got[SENDER + ":t2"]["nodeComplete"], "the cross-host tracker has no reply yet")
        self.assertIn("quiet-filed", [e["why"] for e in got[SENDER + ":t1"]["log"] if e.get("src") == "courier"][-1])
        self._reply("peer:otherbox:api", SENDER, T + 600)                # the cross-host peer, relay-keyed
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 902))
        self.assertEqual((n, counts[SENDER]), (1, 1))
        got = jd.load_goals(SENDER)["nodes"]
        self.assertTrue(got[SENDER + ":t2"]["nodeComplete"])
        self.assertIn("cross-host", [e["why"] for e in got[SENDER + ":t2"]["log"] if e.get("src") == "courier"][-1])
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 903))
        self.assertEqual((n, counts[SENDER], shared[SENDER]), (0, 0, 1), "settled: back to the view alone")

    def test_a_pass_over_every_write_shape_leaves_the_shared_cache_on(self):
        # The frozen-store canary over one pass that writes through every branch: a dirty ref (t1), a
        # dismissed-linked recipient (t2), a quiet tracker with a reply (t3), a cross-host tracker
        # with a reply (t4), and an absent sender the sweep found (DEAD's quiet tracker). A write to
        # a shared view would raise FrozenStoreError, file a row and switch the cache off; none does.
        # (World.tearDown asserts the same for every test in the module; this one exercises the
        # branches together.)
        g6 = _node(RECIP + ":g6", "the delegated work the user dismissed",
                   links=[{"peer": SENDER, "goalId": SENDER + ":t2", "msgId": MID2}])
        jd.record_verdict({"nodes": {g6["id"]: g6}}, g6, "user", "clear", T + 200, why="dismissed")   # the flag is
        #                                                                     diary-derived: a clear event, not a literal
        self._publish(SENDER, {t["id"]: t for t in (_tracker(SENDER, 1, RECIP, MID),
                                                    _tracker(SENDER, 2, RECIP, MID2),
                                                    _tracker(SENDER, 3, RECIP, "msg-propagate-0003", quiet=True),
                                                    _tracker(SENDER, 4, "otherbox:api", "msg-propagate-0004"))})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, "msg-propagate-0005", quiet=True)]})
        self._reply(RECIP, SENDER, T + 500)
        self._reply("peer:otherbox:api", SENDER, T + 600)
        self._reply(RECIP, DEAD, T + 500)
        p0 = jd.shared_store_stats()["poisoned"]
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 5)
        self.assertEqual(dict(counts), {SENDER: 2, DEAD: 1},
                         "one writer load per publish: SENDER's in the recipient loop (t1), then the sender loop's "
                         "on the version that publish left (t2-t4); DEAD's once; the recipient is never loaded")
        self.assertEqual(jd.shared_store_stats()["poisoned"], p0)
        self.assertFalse(jd._SHARED_OFF[0])
        snd = jd.load_goals(SENDER)["nodes"]
        self.assertTrue(all(snd[SENDER + ":t%d" % k]["nodeComplete"] for k in (1, 2, 3, 4)))
        self.assertIn("dismissed", [e["why"] for e in snd[SENDER + ":t2"]["log"] if e.get("src") == "courier"][-1])
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual((n, dict(counts)), (0, {DEAD: 1}),
                         "the next pass: SENDER (discovered) is a view; DEAD's publish moved its identity, so the "
                         "sweep's memo missed once and re-read it (the sweep's miss is a writer load)")
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 902))
        self.assertEqual((n, dict(counts)), (0, {}), "and then idle: views and memo hits only")

    def test_a_recipient_whose_store_does_not_parse_is_quarantined_once_and_fresh_on_both_loaders(self):
        # Upstream #1019 (steer 1 of the 2026-09-08 fold) superseded the fork's `_unread` == "store" fallback
        # and the shared cache's per-version memo of it: a goals file that exists and does not parse is moved
        # aside by load_goals (one sidecar, one store-quarantined row, one stderr line) and the legitimate
        # fresh store is the answer on both loaders. The shared loader hands the bytes to load_goals (counter
        # `corrupt`, once) and caches nothing; the path then reads as absent. Propagate finds no complete
        # recipient goal in the fresh store, skips its refs and leaves the sender untouched (no writer load
        # of the sender, no publish).
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        gp = jd.GOALDIR / (RECIP + ".json")
        gp.write_text("{not json")
        r0, c0 = _rev(SENDER), jd.shared_store_stats()["corrupt"]
        with contextlib.redirect_stderr(io.StringIO()):
            a = jd.load_goals_shared(RECIP)
        self.assertEqual((type(a), a["nodes"], a.get("_unread")), (dict, {}, None),
                         "the shared loader's answer: load_goals' fresh store, private, unmarked")
        self.assertFalse(gp.exists(), "the corrupt file was moved aside")
        self.assertEqual(len(list(jd.GOALDIR.glob(RECIP + ".json.corrupt-*"))), 1)
        rows = [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()]
        self.assertEqual([r["fsid"] for r in rows if r["err"] == "store-quarantined"], [RECIP], "one row, load_goals' own")
        b = jd.load_goals(RECIP)
        self.assertEqual((b["nodes"], b.get("_unread")), ({}, None), "the writer's loader: the same fresh store (absent path)")
        c1 = jd.shared_store_stats()["corrupt"]
        self.assertEqual(c1, c0 + 1, "the bytes were handed to load_goals once")
        for now in (T + 900, T + 901):
            n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=now))
            self.assertEqual((n, counts[SENDER], shared[RECIP]), (0, 0, 1),
                             "nothing to propagate, no writer load of the sender; the recipient's one shared read "
                             "(absent now: handed to load_goals for the fresh store)")
        self.assertEqual(jd.shared_store_stats()["corrupt"], c1, "two passes over the absent path: no second hand-off")
        self.assertEqual(len(list(jd.GOALDIR.glob(RECIP + ".json.corrupt-*"))), 1, "quarantined once, never per pass")
        self.assertEqual(_rev(SENDER), r0, "the sender was not published")
        self.assertFalse(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"])

    def test_two_dirty_refs_to_one_sender_publish_once(self):
        self._publish(SENDER, {t["id"]: t for t in (_tracker(SENDER, 1, RECIP, MID),
                                                    _tracker(SENDER, 2, RECIP, MID2))})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, links=[{"peer": SENDER, "goalId": SENDER + ":t2", "msgId": MID2}])
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        r0, (_h, _m, w0) = _rev(SENDER), self._io()
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 2)
        # one WRITER load for both refs (the second ref reads the writer object through _peek), and the
        # sender loop (SENDER is discovered) reads the version the recipient loop published through the
        # shared cache — a saved object is never kept, and a read is never a plain load. Only a pass
        # that completed something pays the second shared read; an idle pass reads each sid once.
        self.assertEqual((counts[SENDER], shared[SENDER]), (1, 2))
        self.assertEqual((counts[RECIP], shared[RECIP]), (0, 1))
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

    def _two_senders_one_recipient(self):
        """SENDER and SENDER2 each delegated one step to RECIP, which completed both; RECIP's g5 (SENDER's ref)
        is reached before g6 (SENDER2's) in the recipient loop. Returns the two senders' revisions."""
        self.sessions.append((SENDER2, "/dev/null", None, "tests"))
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        self._publish(SENDER2, {t["id"]: t for t in [_tracker(SENDER2, 1, RECIP, MID2)]})
        g5 = _complete(RECIP, 5, origin={"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, origin={"peer": SENDER2, "goalId": SENDER2 + ":t1", "msgId": MID2})
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        return _rev(SENDER), _rev(SENDER2)

    def test_a_raise_mid_loop_publishes_the_verdicts_already_reached_and_re_raises(self):
        # The deferred single publish must not turn one ref's trip into the loss of every verdict the pass
        # recorded before it (review find, 2026-09-08; the per-ref save it replaced had persisted each as it
        # was reached): the senders reached before the raise are published, the error is re-raised, and the
        # sender whose ref raised (its object half-applied) is left for the next pass to re-derive.
        r1, r2 = self._two_senders_one_recipient()
        orig = jd._presumed_closed

        def tripping(sid, now):
            if sid == SENDER2:
                raise RuntimeError("synthetic: the second sender's rollup input trips")
            return orig(sid, now)
        jd._presumed_closed = tripping
        try:
            with self.assertRaises(RuntimeError):
                jd.run_propagate(now=T + 900)
        finally:
            jd._presumed_closed = orig
        self.assertEqual(_rev(SENDER), r1 + 1, "the verdict reached before the raise is on disk")
        self.assertTrue(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"])
        self.assertEqual(_rev(SENDER2), r2, "the sender whose ref raised is not published: half-applied is no verdict")
        self.assertFalse(jd.load_goals(SENDER2)["nodes"][SENDER2 + ":t1"]["nodeComplete"])
        self.assertEqual(jd.run_propagate(now=T + 901), 1, "the next pass re-derives the one left, and only it")
        self.assertEqual((_rev(SENDER), _rev(SENDER2)), (r1 + 1, r2 + 1))

    def test_one_senders_failed_publish_does_not_stop_the_other_senders(self):
        # Every dirty sender is published whatever happened to the one before it; the first failed publish is
        # the pass's error, raised once the rest are out (review find, 2026-09-08).
        r1, r2 = self._two_senders_one_recipient()
        orig_save = jd.save_goals

        def failing(fsid, store):
            if fsid == SENDER:
                raise RuntimeError("disk full")
            return orig_save(fsid, store)
        jd.save_goals = failing
        try:
            with self.assertRaises(RuntimeError):
                jd.run_propagate(now=T + 900)
        finally:
            jd.save_goals = orig_save
        self.assertEqual(_rev(SENDER), r1, "the failed publish left its file untouched")
        self.assertEqual(_rev(SENDER2), r2 + 1, "the other sender's publish still landed")
        self.assertTrue(jd.load_goals(SENDER2)["nodes"][SENDER2 + ":t1"]["nodeComplete"])

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
        # (the sender loop's shared read of the version the recipient loop published); a new pass
        # starts with empty dicts either way, so the failed publish's pop is not observable from here.
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
        n, counts, objs, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        self.assertEqual(n, 1)
        self.assertEqual((counts[DEAD], shared[DEAD]), (1, 1),
                         "the sweep answered from the memo; the loop's view said due, then one writer load")
        self.assertEqual(_rev(DEAD), r0 + 1)
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 901))
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

    def test_a_dismissed_recipients_lookup_reuses_the_passes_store_and_archive_reads(self):
        # The sender loop's dismissed-recipient lookup (_ref_goal) reads the recipient's store and archive
        # through the pass's own dicts: the recipient scan already read both, so the lookup costs no load.
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})   # linked, not quiet
        rn = {"id": RECIP + ":g5", "text": "Verify the staged refs", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": True, "trail": [], "t": T, "mt": T, "log": [],
              "origin": {"peer": SENDER, "goalId": SENDER + ":t1", "msgId": MID}}
        jd.save_goals(RECIP, _store(RECIP, {rn["id"]: rn}))     # the dismissed shape: cleared, not complete; a
        #                                                          plain dict (GuardedNode refuses `cleared`), no rollup
        self._reply(RECIP, SENDER, T + 500)
        arch, orig_arch = Counter(), jd.load_goal_archive

        def arch_spy(fsid):
            arch[fsid] += 1
            return orig_arch(fsid)
        jd.load_goal_archive = arch_spy
        try:
            n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        finally:
            jd.load_goal_archive = orig_arch
        self.assertEqual(n, 1)
        self.assertTrue(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"],
                        "the dismissed recipient's reply ended the tracker")
        # the fork's read/write split: the recipient is only ever a view, and the sender's one plain
        # load is the writer load its due tracker earns; the lookup itself costs no read of either kind
        self.assertEqual(dict(shared), {SENDER: 1, RECIP: 1}, "the lookup reused the recipient scan's shared read")
        self.assertEqual(dict(counts), {SENDER: 1}, "one writer load, for the sender written; the recipient is never loaded")
        self.assertEqual(dict(arch), {SENDER: 1, RECIP: 1}, "...and its archive read")

    def test_a_recipient_node_the_sender_loop_completes_still_reads_as_dismissed_to_a_later_sender(self):
        # _ref_goal's map is a SNAPSHOT (shallow copies of the recipient's nodes at first use), not a live
        # view of the shared object the sender loop mutates. A synthetic shape isolates it: api's node g1 is
        # both a dismissed recipient goal for tests' tracker AND a quiet tracker of its own onto a third
        # peer. web's sender turn builds the map (g1 dismissed), api's turn completes g1 on the shared
        # object, tests' turn must still read the dismissal, or its tracker never ends.
        self.sessions = [(SENDER, "/dev/null", None, "web"), (RECIP, "/dev/null", None, "api"),
                         (DEAD2, "/dev/null", None, "tests")]
        self._publish(SENDER, {t["id"]: t for t in [_tracker(SENDER, 1, RECIP, MID)]})
        g1 = {"id": RECIP + ":g1", "text": "the delegated work", "parentId": None, "nodeComplete": False,
              "blocked": False, "cleared": True, "trail": [], "t": T, "mt": T, "log": [],
              "origin": {"peer": DEAD2, "goalId": DEAD2 + ":t1", "msgId": MID2},
              "handoff": {"peer": DEAD3, "msgId": "msg-propagate-0003", "quiet": True}}
        jd.save_goals(RECIP, _store(RECIP, {g1["id"]: g1}))
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID2)]})
        self._reply(DEAD3, RECIP, T + 500, mid="r-onward")
        self._reply(RECIP, DEAD2, T + 500, mid="r-back")
        n = jd.run_propagate(now=T + 900)
        self.assertTrue(jd.load_goals(RECIP)["nodes"][RECIP + ":g1"]["nodeComplete"], "api's onward handoff ended")
        t1 = jd.load_goals(DEAD2)["nodes"][DEAD2 + ":t1"]
        self.assertTrue(t1["nodeComplete"], "tests' tracker ended on the reply: the map still said dismissed")
        self.assertIn("dismissed", t1.get("doneWhy") or "")
        self.assertEqual(n, 2)
        self.assertFalse(jd.load_goals(SENDER)["nodes"][SENDER + ":t1"]["nodeComplete"],
                         "web's live linked recipient (no node joins MID) still defers to the back-link")

    def test_a_back_link_completion_on_an_absent_sender_is_settled_when_the_bus_knows_no_such_session(self):
        # The recipient loop's per-ref rollup runs with _presumed_closed (once per sender per pass): a dead
        # sender's back-link completion is SETTLED once the bus knows no live session by that sid, and left
        # confirming while closedness cannot be determined. The tracker is the store's focus (lastNode), so
        # only a closed session settles it.
        def _focused(sid, k, mid):
            t = _tracker(sid, k, RECIP, mid)
            st = jd.load_goals(sid) if (jd.GOALDIR / (sid + ".json")).exists() else _store(sid, {})
            st["nodes"][t["id"]] = t
            st["lastNode"] = t["id"]
            jd.rollup_status(st, False)
            jd.save_goals(sid, st)
        _focused(DEAD, 1, MID)
        _focused(DEAD2, 1, MID2)
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        g6 = _complete(RECIP, 6, origin={"peer": DEAD2, "goalId": DEAD2 + ":t1", "msgId": MID2})
        self._publish(RECIP, {g5["id"]: g5, g6["id"]: g6})
        self.assertEqual(jd.run_propagate(now=T + 900), 2)
        for sid in (DEAD, DEAD2):
            got = jd.load_goals(sid)
            self.assertTrue(got["nodes"][sid + ":t1"]["nodeComplete"])
            self.assertEqual(got["status"][sid + ":t1"], "working", "no mirror: not determinable, not settled")
            self.assertIn(sid + ":t1", got.get("confirming") or [])
        (jd.STATE / "remote-sids").write_text("")          # the bus has spoken: no live session anywhere by the sid
        mid7 = "msg-propagate-0007"
        _focused(DEAD, 2, mid7)
        g7 = _complete(RECIP, 7, origin={"peer": DEAD, "goalId": DEAD + ":t2", "msgId": mid7})
        st = jd.load_goals(RECIP)
        st["nodes"][g7["id"]] = g7
        jd.rollup_status(st, False)
        jd.save_goals(RECIP, st)
        self.assertEqual(jd.run_propagate(now=T + 901), 1)
        got = jd.load_goals(DEAD)
        self.assertTrue(got["nodes"][DEAD + ":t2"]["nodeComplete"])
        self.assertEqual(got["status"][DEAD + ":t2"], "completed", "rolled up with the settled closedness")
        self.assertNotIn(DEAD + ":t2", got.get("confirming") or [])


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
        _r, counts, _o, shared = self._pass(T + 900)
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 1, DEAD2: 1, DEAD3: 1},
                         "each absent store parsed once: the sweep's read serves the sender loop and the drain")
        self.assertEqual(self._io()[:2], (h0 + 3, m0 + 3), "three misses (propagate), three hits (the drain)")
        self.assertEqual(self.visits, [DEAD3])
        _r, counts, _o, shared = self._pass(T + 901)
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 0, DEAD2: 0, DEAD3: 0},
                         "unchanged: no plain load anywhere")
        self.assertEqual({s: shared[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 0, DEAD2: 1, DEAD3: 0},
                         "the open tracker's sender-loop walk reads the view")
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
        # The recipient loop's _peek reads an absent sender through the shared cache (a complete
        # recipient goal refs a tracker of its that is already done) and leaves the VIEW for the
        # sweep, which evaluates the predicates on it under the identity _peek took before the read,
        # then re-takes the identity and memoizes only when it still stands (the post-load identity
        # re-check, upstream #1019's fold, 2026-09-08). A publish landing between that stat and the
        # read is caught by the re-check: nothing memoized, one extra miss next pass; before the
        # re-check the entry paired the OLD identity with the old content and healed at the next
        # miss. A stat taken only AFTER the read would memoize the post-publish identity against
        # pre-publish flags and serve it as a hit.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, done=True)]})
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        p, k0 = str(jd.GOALDIR / (DEAD + ".json")), jd._store_identity(DEAD)
        orig, orig_shared, fired, plain = jd.load_goals, jd.load_goals_shared, [], []

        def publish_under_the_read(fsid):
            st = orig_shared(fsid)                      # the pre-publish content (the view)
            if fsid == DEAD and not fired:
                fired.append(1)
                new = orig(DEAD)
                new["nodes"][DEAD + ":t2"] = _tracker(DEAD, 2, RECIP, MID2, quiet=True)
                jd.rollup_status(new, False)
                jd.save_goals(DEAD, new)                # the identity moves while the read is in flight
            return st

        def counted_plain(fsid):
            plain.append(fsid)
            return orig(fsid)
        jd.load_goals_shared, jd.load_goals = publish_under_the_read, counted_plain
        try:
            self.assertEqual(jd.run_propagate(now=T + 900), 0, "the ref's tracker was already done")
        finally:
            jd.load_goals_shared, jd.load_goals = orig_shared, orig
        self.assertEqual(fired, [1], "_peek's shared read, not the sweep, performed the read")
        self.assertEqual([f for f in plain if f == DEAD], [],
                         "no plain load of DEAD anywhere: the sweep evaluated the view (the test's own publish reads "
                         "through the unpatched loader)")
        k1 = jd._store_identity(DEAD)
        self.assertNotEqual(k1, k0)
        self.assertNotIn(p, jd._ABSENT_FLAGS,
                         "the identity taken BEFORE the read no longer stands after it: nothing memoized from the view")
        h, m, _w = self._io()
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual((n, counts[DEAD], shared[DEAD]), (0, 0, 1), "the next pass: the view again, no plain load")
        self.assertEqual(self._io()[:2], (h, m + 1), "read again under the new identity; never a stale hit")
        self.assertEqual(jd._ABSENT_FLAGS[p], (k1, (True, True)), "re-evaluated on the published content, from the view")

    def test_a_view_evaluated_by_the_sweep_never_enters_the_writer_dict(self):
        # The memo reads the view (a frozen shared object) for its two predicates; the sender loop then
        # finds the open tracker due and takes a WRITER load for the write. The frozen view is never
        # what save_goals receives (it would refuse it with a row and the cache would be off).
        self._publish(DEAD, {t["id"]: t for t in (_tracker(DEAD, 1, RECIP, MID, done=True),
                                                  _tracker(DEAD, 2, RECIP, MID2, quiet=True))})
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        self._reply(RECIP, DEAD, T + 500)
        saved, orig_save = [], jd.save_goals

        def spy_save(fsid, store):
            saved.append((fsid, isinstance(store, jd.FrozenDict), isinstance(store.get("nodes"), jd.FrozenDict)))
            return orig_save(fsid, store)
        jd.save_goals = spy_save
        try:
            h, m, _w = self._io()
            n, counts, objs, shared = self._counting(lambda: jd.run_propagate(now=T + 900))
        finally:
            jd.save_goals = orig_save
        self.assertEqual(n, 1)
        self.assertEqual((shared[DEAD], counts[DEAD]), (1, 1), "the ref's view, then the sender loop's writer load")
        self.assertEqual(self._io()[:2], (h, m + 1), "the sweep evaluated the view: one miss, no load of its own")
        self.assertEqual(saved, [(DEAD, False, False)], "the object saved is the writer load, not the frozen view")
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t2"]["nodeComplete"])

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
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 901))
        self.assertEqual(n, 1, "swept and completed the next pass")
        self.assertEqual(counts[DEAD], 1, "the miss's read served the sender loop")
        self.assertEqual(self._io()[:2], (h, m + 1))
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        n, counts, _o, shared = self._counting(lambda: jd.run_propagate(now=T + 902))
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
        _r, counts, _o, shared = self._counting(lambda: jd._drain_undiscovered(T + 901, self._sids()))
        self.assertEqual({s: counts[s] for s in (DEAD, DEAD2, DEAD3)}, {DEAD: 0, DEAD2: 1, DEAD3: 0})
        self.assertEqual(self._io()[:2], (h + 2, m + 1))
        self.assertEqual(self.visits, [])

    def test_the_drain_distills_a_stuck_store_found_by_the_shared_sweep(self):
        jd._distill_session = self._distill                  # the real distiller: transcript-less settle
        self._owed(DEAD3)
        self.sessions = []
        h, m, _w = self._io()
        _n, counts, _o, shared = self._counting(lambda: (jd.run_propagate(now=T + 900), jd.run_distill(now=T + 900)))
        self.assertEqual(self._io()[:2], (h + 1, m + 1), "propagate's miss, the drain's hit")
        nd = jd.load_goals(DEAD3)["nodes"][DEAD3 + ":g1"]
        self.assertEqual(nd.get("summary"), "", "no transcript anywhere: the sentinel ends the spinner")
        _n, counts, _o, shared = self._counting(lambda: jd.run_distill(now=T + 901))
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

    # Each component of the identity is load-bearing on its own: the tests above change two at once
    # (a publish is a new inode AND a new mtime, usually a new size), so a key missing one component
    # still passes them. One test per component, isolating it with an in-place rewrite or os.utime,
    # which no romp writer does.
    def test_a_size_only_change_is_a_miss(self):
        self._plain(DEAD2)
        self.assertEqual(jd._absent_store_flags(DEAD2), (False, False))
        p = jd.GOALDIR / (DEAD2 + ".json")
        k0, st0 = jd._store_identity(DEAD2), os.stat(p)
        t1 = _tracker(DEAD2, 1, RECIP, MID, quiet=True)
        with open(p, "r+b") as f:                        # in place: the same inode
            f.truncate()
            f.write(json.dumps(_store(DEAD2, {t1["id"]: t1})).encode())
        os.utime(p, ns=(st0.st_atime_ns, st0.st_mtime_ns))
        st1 = os.stat(p)
        self.assertEqual((st1.st_ino, st1.st_mtime_ns), (st0.st_ino, st0.st_mtime_ns), "same inode, same mtime_ns")
        self.assertNotEqual(st1.st_size, st0.st_size, "only the size moved")
        self.assertNotEqual(jd._store_identity(DEAD2), k0, "the key moved with it")
        h, m, _w = self._io()
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False), "a miss: the new bytes' open tracker")
        self.assertEqual(self._io()[:2], (h, m + 1))

    def test_an_mtime_only_change_is_a_miss(self):
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        p = jd.GOALDIR / (DEAD2 + ".json")
        k0, st0 = jd._store_identity(DEAD2), os.stat(p)
        raw = p.read_bytes()
        self.assertEqual(raw.count(b'"nodeComplete": false'), 1)
        with open(p, "r+b") as f:
            f.write(raw.replace(b'"nodeComplete": false', b'"nodeComplete": true '))   # the same byte length
        os.utime(p, ns=(st0.st_atime_ns, st0.st_mtime_ns + 1_000_000_000))
        st1 = os.stat(p)
        self.assertEqual((st1.st_ino, st1.st_size), (st0.st_ino, st0.st_size), "same inode, same size")
        self.assertNotEqual(st1.st_mtime_ns, st0.st_mtime_ns, "only the mtime moved")
        self.assertNotEqual(jd._store_identity(DEAD2), k0, "the key moved with it")
        h, m, _w = self._io()
        self.assertFalse(jd._absent_store_flags(DEAD2)[0], "a miss: the tracker now reads complete")
        self.assertEqual(self._io()[:2], (h, m + 1))

    def test_an_inode_only_change_is_a_miss(self):
        self._publish(DEAD2, {t["id"]: t for t in [_tracker(DEAD2, 1, RECIP, MID, quiet=True)]})
        self.assertEqual(jd._absent_store_flags(DEAD2), (True, False))
        p = jd.GOALDIR / (DEAD2 + ".json")
        k0, st0 = jd._store_identity(DEAD2), os.stat(p)
        raw = p.read_bytes()
        tmp = jd.GOALDIR / (DEAD2 + ".json.tmp")
        tmp.write_bytes(raw.replace(b'"nodeComplete": false', b'"nodeComplete": true '))   # the same byte length
        os.utime(tmp, ns=(st0.st_atime_ns, st0.st_mtime_ns))
        os.rename(tmp, p)                                # a publish whose clock did not move
        st1 = os.stat(p)
        self.assertEqual((st1.st_mtime_ns, st1.st_size), (st0.st_mtime_ns, st0.st_size), "same mtime_ns, same size")
        self.assertNotEqual(st1.st_ino, st0.st_ino, "only the inode moved")
        self.assertNotEqual(jd._store_identity(DEAD2), k0, "the key moved with it")
        h, m, _w = self._io()
        self.assertFalse(jd._absent_store_flags(DEAD2)[0], "a miss: the tracker now reads complete")
        self.assertEqual(self._io()[:2], (h, m + 1))

    def test_run_propagates_sweep_evicts_a_vanished_store(self):
        # run_propagate's own sweep evicts too, not only _drain_undiscovered's
        self._plain(DEAD)
        self._plain(DEAD2)
        jd.run_propagate(now=T + 900)
        p_dead = str(jd.GOALDIR / (DEAD + ".json"))
        self.assertIn(p_dead, jd._ABSENT_FLAGS)
        (jd.GOALDIR / (DEAD + ".json")).unlink()
        jd.run_propagate(now=T + 901)
        self.assertNotIn(p_dead, jd._ABSENT_FLAGS, "gone from run_propagate's glob: evicted by its sweep")
        self.assertIn(str(jd.GOALDIR / (DEAD2 + ".json")), jd._ABSENT_FLAGS)

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

    # ---- a load that answered less than the files hold is no better than one that raised ----
    def _read_fails_once(self, target):
        """Patch Path.read_text so the first read of `target` raises OSError and every later read is
        real: the store or journal exists and could not be read (the awaiting-lift gate's tests use the
        same shape). load_goals RAISES a store-file failure (upstream #1019; before the 2026-09-08 fold
        it answered an empty store marked `_unread`); _replay_overrides logs and skips the journal and
        marks the object `_unread`. The store's fd readers (load_goals_shared, _disk_rev) never call
        read_text, so only the writer's loader sees the fault. Returns the counter of raised reads."""
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

    def test_a_store_read_fault_raises_out_of_the_load_and_is_not_memoized(self):
        # load_goals raises on a store file it cannot read (upstream #1019, steer 1 of the 2026-09-08 fold:
        # there is no fallback store to answer from), so the caller skips the store this pass (None), as
        # the sweeps always did, and no entry is written: nothing on disk changes before the next read
        # succeeds, so an entry would be a hit saying "nothing open" for a store holding an open tracker,
        # until its next write.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, quiet=True)]})
        p, k0 = str(jd.GOALDIR / (DEAD + ".json")), jd._store_identity(DEAD)
        state = self._read_fails_once(jd.GOALDIR / (DEAD + ".json"))
        h, m, _w = self._io()
        self.assertIsNone(jd._absent_store_flags(DEAD), "the raise: skipped this pass")
        self.assertEqual(state["fired"], 1)
        self.assertNotIn(p, jd._ABSENT_FLAGS, "a store that did not read is never memoized")
        self.assertEqual(jd._store_identity(DEAD), k0, "nothing on disk moved: the key alone could not tell")
        self.assertEqual(jd._absent_store_flags(DEAD), (True, False), "the next call re-reads the file")
        self.assertEqual(self._io()[:2], (h, m + 2), "two misses, no stale hit")
        self.assertEqual(jd._ABSENT_FLAGS[p], (k0, (True, False)))

    def test_a_quarantined_store_is_not_memoized_under_the_corrupt_files_identity(self):
        # load_goals moves an unparseable store aside and answers the legitimate fresh store (upstream
        # #1019). The key was taken before the read and names the corrupt file, which is gone by the time
        # the answer is in hand; the identity re-taken after the read differs, so nothing is memoized under
        # it. The next call takes the absent identity and memoizes the fresh store's answer there.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID, quiet=True)]})
        p = jd.GOALDIR / (DEAD + ".json")
        p.write_text("{not json")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(jd._absent_store_flags(DEAD), (False, False), "the fresh store's answer, this pass")
        self.assertFalse(p.exists(), "the corrupt file was moved aside")
        self.assertEqual(len(list(jd.GOALDIR.glob(DEAD + ".json.corrupt-*"))), 1)
        self.assertNotIn(str(p), jd._ABSENT_FLAGS, "never memoized under the identity of a file that is gone")
        self.assertEqual(jd._absent_store_flags(DEAD), (False, False))
        self.assertIsNone(jd._ABSENT_FLAGS[str(p)][0][1], "memoized under the absent identity")

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

    def test_run_propagate_files_a_row_for_a_sender_whose_read_raises_and_completes_it_the_next_pass(self):
        # The raise through run_propagate's own read (upstream #1019; before the 2026-09-08 fold the writer
        # load answered an empty `_unread` store with no tracker to mark): a complete recipient goal refs an
        # absent sender's open tracker; the view (_peek, the shared loader's fd read) says open, then _get's
        # writer load of the sender raises (the store file fails once). The recipient's pass-crash row names
        # the sender, the ref waits, and the sweep evaluates the VIEW the ref took (the file's truth, read
        # before the fault) and memoizes it under the identity taken before that read. The next pass reads
        # the file at the ref and completes the tracker.
        self._publish(DEAD, {t["id"]: t for t in [_tracker(DEAD, 1, RECIP, MID)]})
        g5 = _complete(RECIP, 5, origin={"peer": DEAD, "goalId": DEAD + ":t1", "msgId": MID})
        self._publish(RECIP, {g5["id"]: g5})
        p = str(jd.GOALDIR / (DEAD + ".json"))
        state = self._read_fails_once(jd.GOALDIR / (DEAD + ".json"))
        self.assertEqual(jd.run_propagate(now=T + 900), 0, "the sender's writer load raised: nothing to complete this pass")
        self.assertEqual(state["fired"], 1)
        rows = [json.loads(l) for l in jd.ERRORS.read_text().splitlines() if l.strip()] if jd.ERRORS.exists() else []
        crash = [r for r in rows if r["err"] == "pass-crash"]
        self.assertEqual([(r["judge"], r["fsid"]) for r in crash], [("propagate", RECIP)], "the recipient's row, once")
        self.assertIn(DEAD[:8], crash[0]["note"], "...naming the sender whose store raised")
        self.assertEqual([r["err"] for r in rows if r["err"] != "pass-crash"], [],
                         "no store-unreadable row: a fault met inside a pass is the pass's row, not the boundary's")
        self.assertFalse(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])
        self.assertEqual(jd._ABSENT_FLAGS[p][1], (True, False),
                         "the view the ref took read the file before the fault: its truth, memoized by the sweep")
        self.assertEqual(jd.run_propagate(now=T + 901), 1, "the next pass reads the file at the ref and completes it")
        self.assertTrue(jd.load_goals(DEAD)["nodes"][DEAD + ":t1"]["nodeComplete"])

    def test_rebind_clears_the_memo(self):
        self._plain(DEAD)
        jd._absent_store_flags(DEAD)
        self.assertTrue(jd._ABSENT_FLAGS)
        jd._rebind_state(Path(self.td.name))
        self.assertEqual(jd._ABSENT_FLAGS, {})


if __name__ == "__main__":
    unittest.main()
